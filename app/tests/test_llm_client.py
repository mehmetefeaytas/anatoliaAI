"""LLM katmanı testleri — SAHTE TAŞIMA (transport) ile, ağsız/GPU'suz koşar.

İlgili: ../src/extraction/llm/clients.py (yetenek pazarlığı)
        ../src/extraction/llm/parse.py, confidence.py, extractor.py
        CLAUDE.md §19 (modülerlik: her katman bağımsız test edilebilir)

Buradaki hiçbir test localhost'a bağlanmaz. `VLLMClient(transport=...)` ile
sahte bir `(url, payload, timeout) -> dict` fonksiyonu enjekte edilir; böylece
pazarlık mantığı, ayrıştırma patolojileri, logprob->güven eşlemesi ve katı mod
CI'da ve internetsiz makinede de koşar. LLM'in GERÇEKTEN çalıştığının kanıtı
`notebooks/00_vllm_smoke.ipynb`'dir; bu dosya davranışın SÖZLEŞMESİNİ korur.
"""

from __future__ import annotations

import json
import logging
import math
import os
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.extraction.llm.clients import (
    STRUCTURED_MODES,
    LLMHTTPError,
    LLMTransportError,
    OllamaClient,
    VLLMClient,
)
from src.extraction.llm.confidence import (
    SOURCE_LOGPROB,
    SOURCE_SELF_REPORTED,
    field_confidences,
    find_value_span,
    token_offsets,
)
from src.extraction.llm.extractor import (
    LLMExtractionError,
    LLMExtractor,
    NullLLMExtractor,
    default_extractor,
)
from src.extraction.llm.parse import parse_llm_json
from src.extraction.llm.schema import (
    EXTRACTION_FIELDS,
    guided_json_schema,
)
from src.extraction.reconcile import reconcile
from src.schemas import Extractor

# Hata yolları BİLEREK loglanır; test çıktısını kirletmesin diye susturulur.
# Loglamanın gerçekten olduğu `test_hata_loglanir` içinde ayrıca doğrulanır.
_EXTRACTOR_LOGGER = "src.extraction.llm.extractor"
logging.getLogger(_EXTRACTOR_LOGGER).setLevel(logging.CRITICAL)


# --------------------------------------------------------------------------- #
# Sahte taşıma
# --------------------------------------------------------------------------- #
def detect_mode(payload: dict) -> str:
    """İstek gövdesinden hangi yapılandırılmış-çıktı modunun kullanıldığını okur."""
    if "response_format" in payload:
        return "json_schema"
    if "structured_outputs" in payload:
        return "structured_outputs"
    if "guided_json" in payload:
        return "guided_json"
    return "prompt_only"


class FakeVLLMTransport:
    """Belirli modları destekleyen, gerisine HTTP 400 dönen sahte vLLM."""

    def __init__(self, supported=("json_schema",), content: str = "{}",
                 logprobs=None, contents=None):
        self.supported = set(supported)
        self.content = content
        # contents: sıralı yanıt listesi (onarım denemesi testleri için)
        self.contents = list(contents) if contents else None
        self.logprobs = logprobs
        self.payloads: list[dict] = []

    def __call__(self, url: str, payload: dict, timeout: float) -> dict:
        self.payloads.append(payload)
        mode = detect_mode(payload)
        if mode not in self.supported:
            raise LLMHTTPError(400, f"unknown parameter for mode {mode}", url)
        if payload.get("max_tokens") == 1:
            # Pazarlık probu — sıradaki gerçek yanıtı tüketmez.
            return {"choices": [{"message": {"content": "{"}}]}
        if self.contents:
            content = self.contents.pop(0)
        else:
            content = self.content
        choice = {"message": {"role": "assistant", "content": content}}
        if self.logprobs is not None:
            choice["logprobs"] = {"content": [
                {"token": t, "logprob": lp} for t, lp in self.logprobs]}
        return {"choices": [choice]}

    @property
    def modes_tried(self) -> list[str]:
        return [detect_mode(p) for p in self.payloads]


def dead_transport(url: str, payload: dict, timeout: float) -> dict:
    """Servis hiç ayakta değil."""
    raise LLMTransportError(f"{url} ulasilamadi: Connection refused")


SCHEMA = guided_json_schema(["vade_ay"])


# --------------------------------------------------------------------------- #
# 1. Yetenek pazarlığı
# --------------------------------------------------------------------------- #
class TestNegotiation(unittest.TestCase):

    def test_json_schema_tercih_edilir(self):
        """Her mod desteklense bile OpenAI standardı (en dayanıklı) seçilir."""
        t = FakeVLLMTransport(supported=STRUCTURED_MODES)
        c = VLLMClient(transport=t)
        self.assertEqual(c.negotiate(SCHEMA), "json_schema")
        self.assertEqual(t.modes_tried, ["json_schema"])

    def test_structured_outputs_a_dusulur(self):
        t = FakeVLLMTransport(supported=("structured_outputs", "guided_json"))
        c = VLLMClient(transport=t)
        self.assertEqual(c.negotiate(SCHEMA), "structured_outputs")
        self.assertEqual(t.modes_tried, ["json_schema", "structured_outputs"])

    def test_guided_json_a_dusulur(self):
        """Eski vLLM: yalnız `guided_json` tanınır."""
        t = FakeVLLMTransport(supported=("guided_json",))
        c = VLLMClient(transport=t)
        self.assertEqual(c.negotiate(SCHEMA), "guided_json")
        self.assertEqual(t.modes_tried,
                         ["json_schema", "structured_outputs", "guided_json"])

    def test_prompt_only_son_care(self):
        """Hiçbir kısıt biçimi yoksa şema prompt'a gömülür."""
        t = FakeVLLMTransport(supported=("prompt_only",))
        c = VLLMClient(transport=t)
        self.assertEqual(c.negotiate(SCHEMA), "prompt_only")
        last = t.payloads[-1]
        self.assertNotIn("guided_json", last)
        self.assertNotIn("response_format", last)
        self.assertIn("JSON Schema", last["messages"][0]["content"])

    def test_pazarlik_cachelenir(self):
        """Pazarlık bir kez yapılır; sonraki çağrılar yeniden denemez."""
        t = FakeVLLMTransport(supported=("guided_json",), content='{}')
        c = VLLMClient(transport=t)
        c.negotiate(SCHEMA)
        n_after_negotiation = len(t.payloads)
        c.generate("s", "u", SCHEMA)
        c.generate("s", "u", SCHEMA)
        # 2 gerçek çağrı eklendi, ek pazarlık YOK.
        self.assertEqual(len(t.payloads), n_after_negotiation + 2)
        self.assertEqual(t.modes_tried[-2:], ["guided_json", "guided_json"])

    def test_servis_kapaliysa_hemen_yukselir(self):
        """Taşıma hatasında 4 mod boşuna denenmez; durum netçe bildirilir."""
        c = VLLMClient(transport=dead_transport)
        with self.assertRaises(LLMTransportError):
            c.negotiate(SCHEMA)
        self.assertEqual(c.structured_mode, None)
        self.assertEqual(c.negotiation_log, [("json_schema", "servise ulasilamadi")])

    def test_hicbir_mod_kabul_edilmezse_http_hatasi(self):
        t = FakeVLLMTransport(supported=())
        c = VLLMClient(transport=t)
        with self.assertRaises(LLMHTTPError):
            c.negotiate(SCHEMA)
        self.assertEqual(len(t.modes_tried), len(STRUCTURED_MODES))

    def test_logprob_ve_thinking_kapali_istenir(self):
        t = FakeVLLMTransport(supported=STRUCTURED_MODES)
        c = VLLMClient(transport=t)
        c.generate("s", "u", SCHEMA)
        p = t.payloads[-1]
        self.assertTrue(p["logprobs"])
        self.assertEqual(p["top_logprobs"], 1)
        # Kısıtlı decoding ile <think> çakışır -> kapalı.
        self.assertEqual(p["chat_template_kwargs"], {"enable_thinking": False})

    def test_json_schema_strict_bayragi(self):
        t = FakeVLLMTransport(supported=("json_schema",))
        c = VLLMClient(transport=t)
        c.generate("s", "u", SCHEMA)
        rf = t.payloads[-1]["response_format"]
        self.assertEqual(rf["type"], "json_schema")
        self.assertTrue(rf["json_schema"]["strict"])


# --------------------------------------------------------------------------- #
# 2. Ayrıştırma patolojileri
# --------------------------------------------------------------------------- #
class TestParse(unittest.TestCase):

    def test_markdown_citli_json(self):
        obj, err = parse_llm_json('```json\n{"vade_ay": 36}\n```')
        self.assertIsNone(err)
        self.assertEqual(obj, {"vade_ay": 36})

    def test_think_onekli(self):
        raw = '<think>Metinde 36 ay geçiyor, emin miyim?</think>\n{"vade_ay": 36}'
        obj, err = parse_llm_json(raw)
        self.assertIsNone(err)
        self.assertEqual(obj, {"vade_ay": 36})

    def test_kapanmamis_think_bloguyla_kesik_yanit(self):
        obj, err = parse_llm_json("<think>düşünüyorum ve cevap gelmedi")
        self.assertIsNone(obj)
        self.assertIn("icerik kalmadi", err)

    def test_kesik_json(self):
        obj, err = parse_llm_json('{"vade_ay": {"value": 36, "confi')
        self.assertIsNone(obj)
        self.assertIn("kapanmamis", err)

    def test_cift_json_ilki_alinir(self):
        """Regex ile birleşip patlayan klasik vaka: iki nesne peş peşe."""
        obj, err = parse_llm_json('{"vade_ay": 36}\n{"vade_ay": 48}')
        self.assertIsNone(err)
        self.assertEqual(obj, {"vade_ay": 36})

    def test_ic_ice_nesne_dogru_kapanir(self):
        raw = '{"a": {"b": {"c": 1}}, "d": 2} kuyruk metni'
        obj, err = parse_llm_json(raw)
        self.assertIsNone(err)
        self.assertEqual(obj, {"a": {"b": {"c": 1}}, "d": 2})

    def test_sondaki_virgul_temizlenir(self):
        obj, err = parse_llm_json('{"vade_ay": 36, "taksit_sayisi": 12,}')
        self.assertIsNone(err)
        self.assertEqual(obj, {"vade_ay": 36, "taksit_sayisi": 12})

    def test_tek_tirnak_donusumu(self):
        obj, err = parse_llm_json("{'vade_ay': 36}")
        self.assertIsNone(err)
        self.assertEqual(obj, {"vade_ay": 36})

    def test_liste_donerse_ilk_eleman(self):
        obj, err = parse_llm_json('[{"vade_ay": 36}, {"vade_ay": 48}]')
        self.assertIsNone(err)
        self.assertEqual(obj, {"vade_ay": 36})

    def test_string_icindeki_susluler_sayilmaz(self):
        raw = '{"kampanya_kosullari": ["şu {parantez} metinde geçiyor"]}'
        obj, err = parse_llm_json(raw)
        self.assertIsNone(err)
        self.assertEqual(obj["kampanya_kosullari"], ["şu {parantez} metinde geçiyor"])

    def test_bos_ve_json_suz_yanit(self):
        self.assertIsNone(parse_llm_json("")[0])
        self.assertIsNone(parse_llm_json(None)[0])
        obj, err = parse_llm_json("Üzgünüm, bu metinde bilgi bulamadım.")
        self.assertIsNone(obj)
        self.assertIn("JSON nesnesi yok", err)


# --------------------------------------------------------------------------- #
# 3. Logprob -> güven eşlemesi
# --------------------------------------------------------------------------- #
# Token'lar bilerek elle bölündü: "36" tek başına bir token olsun ki değerin
# karakter aralığıyla yalnız o örtüşsün ve beklenen skor kesin hesaplanabilsin.
_JSON_HEAD = '{"vade_ay": {"value": '
_JSON_TAIL = ', "confidence": 0.9, "source_span": "36 ay"}}'
_LOGPROBS = [(_JSON_HEAD, -0.001), ("36", math.log(0.5)), (_JSON_TAIL, -0.001)]


class TestConfidence(unittest.TestCase):

    def test_token_offsetleri_metni_yeniden_kurar(self):
        text, spans = token_offsets(
            [{"token": t, "logprob": lp} for t, lp in _LOGPROBS])
        self.assertEqual(text, _JSON_HEAD + "36" + _JSON_TAIL)
        self.assertEqual(text[spans[1][0]:spans[1][1]], "36")

    def test_value_araligi_bulunur(self):
        text = _JSON_HEAD + "36" + _JSON_TAIL
        span = find_value_span(text, "vade_ay")
        self.assertEqual(text[span[0]:span[1]], "36")

    def test_null_alanda_value_araligi_yok(self):
        self.assertIsNone(find_value_span('{"vade_ay": null}', "vade_ay"))

    def test_logprob_ortalamasi_olasiliga_cevrilir(self):
        lp = [{"token": t, "logprob": v} for t, v in _LOGPROBS]
        conf = field_confidences(lp, EXTRACTION_FIELDS)
        self.assertAlmostEqual(conf["vade_ay"], 0.5, places=6)

    def test_logprob_yoksa_bos_sozluk(self):
        self.assertEqual(field_confidences([], EXTRACTION_FIELDS), {})


# --------------------------------------------------------------------------- #
# 4. Çıkarıcı: güven kaynağı, onarım, katı mod, sayaçlar
# --------------------------------------------------------------------------- #
GOOD_JSON = json.dumps({
    "vade_ay": {"value": 36, "confidence": 0.9, "source_span": "36 ay"},
    "kar_payi_orani": {"value": None, "confidence": 0.0, "source_span": None},
}, ensure_ascii=False)

TEXT = "İhtiyaç finansmanında 36 ay vade imkânı."


def make_extractor(**kw) -> tuple[LLMExtractor, FakeVLLMTransport]:
    t = FakeVLLMTransport(supported=("json_schema",), **kw)
    return LLMExtractor(VLLMClient(transport=t)), t


class TestExtractor(unittest.TestCase):

    def test_logprob_varsa_guven_kaynagi_logprob(self):
        ex, _ = make_extractor(
            content=_JSON_HEAD + "36" + _JSON_TAIL, logprobs=_LOGPROBS)
        fields = ex.extract(TEXT, ["vade_ay"])
        self.assertEqual(len(fields), 1)
        f = fields[0]
        self.assertEqual(f.confidence_source, SOURCE_LOGPROB)
        self.assertAlmostEqual(f.confidence, 0.5, places=6)
        self.assertIs(f.extractor, Extractor.LLM)

    def test_logprob_yoksa_kendi_bildirdigi_guven(self):
        ex, _ = make_extractor(content=GOOD_JSON)
        f = ex.extract(TEXT, ["vade_ay"])[0]
        self.assertEqual(f.confidence_source, SOURCE_SELF_REPORTED)
        self.assertAlmostEqual(f.confidence, 0.9, places=6)

    def test_null_alan_uretilmez(self):
        """Halüsinasyon yasağı: value=null olan alan ExtractedField'a dönmez."""
        ex, _ = make_extractor(content=GOOD_JSON)
        names = [f.field_name for f in ex.extract(TEXT)]
        self.assertEqual(names, ["vade_ay"])

    def test_source_span_offseti_dogrulanabilir(self):
        ex, _ = make_extractor(content=GOOD_JSON)
        f = ex.extract(TEXT, ["vade_ay"])[0]
        self.assertTrue(f.verify_span(TEXT))

    def test_uydurulmus_span_offset_uretmez(self):
        """Model kendi cümlesini yazdıysa yanlış yeri vurgulamaktansa hiç vurgulama."""
        bad = json.dumps({"vade_ay": {"value": 36, "confidence": 0.9,
                                      "source_span": "metinde olmayan ifade"}})
        ex, _ = make_extractor(content=bad)
        f = ex.extract(TEXT, ["vade_ay"])[0]
        self.assertIsNone(f.span_start)
        self.assertFalse(f.verify_span(TEXT))

    def test_onarim_denemesi_bir_kez(self):
        """İlk yanıt bozuk, ikinci sağlam -> retries=1 ve sonuç BAŞARILI."""
        t = FakeVLLMTransport(supported=("json_schema",),
                              contents=["{bozuk json", GOOD_JSON])
        ex = LLMExtractor(VLLMClient(transport=t))
        res = ex.call(TEXT, ["vade_ay"])
        self.assertIsNone(res.error)
        self.assertEqual(res.retries, 1)
        self.assertEqual(ex.stats["parse_error"], 1)
        self.assertEqual(ex.stats["ok"], 1)
        # Onarım prompt'u modele hatayı SÖYLEDİ mi?
        self.assertIn("ÖNCEKİ YANITIN GEÇERSİZDİ",
                      t.payloads[-1]["messages"][1]["content"])

    def test_onarim_da_basarisizsa_hata_dondurulur(self):
        t = FakeVLLMTransport(supported=("json_schema",),
                              contents=["{bozuk", "yine bozuk"])
        ex = LLMExtractor(VLLMClient(transport=t))
        res = ex.call(TEXT, ["vade_ay"])
        self.assertIsNotNone(res.error)
        self.assertIn("parse_error", res.error)
        self.assertEqual(ex.stats["parse_error"], 2)
        self.assertEqual(ex.stats["ok"], 0)

    def test_sema_ihlali_sayilir_ve_atilir(self):
        content = json.dumps({
            "vade_ay": {"value": 36, "confidence": 0.9, "source_span": "36 ay"},
            "uydurma_alan": {"value": 1, "confidence": 1.0, "source_span": None},
        })
        ex, _ = make_extractor(content=content)
        names = [f.field_name for f in ex.extract(TEXT)]
        self.assertEqual(names, ["vade_ay"])
        self.assertEqual(ex.stats["schema_violation"], 1)

    def test_http_hatasi_sayaci_ve_sessiz_dusme(self):
        """Hoşgörülü mod: boş liste döner AMA hata kayıt altında."""
        ex = LLMExtractor(VLLMClient(transport=FakeVLLMTransport(supported=())))
        self.assertEqual(ex.extract(TEXT), [])
        self.assertEqual(ex.stats["http_error"], 1)
        self.assertIsNotNone(ex.last_result.error)

    def test_strict_mod_exception_yukseltir(self):
        """LLM_STRICT=1 -> sahte 'hibrit=kural-only' satırı imkânsız."""
        with mock.patch.dict(os.environ, {"LLM_STRICT": "1"}):
            ex = LLMExtractor(VLLMClient(transport=dead_transport))
            self.assertTrue(ex.strict)
            with self.assertRaises(LLMExtractionError):
                ex.extract(TEXT)

    def test_strict_mod_argumanla_da_acilir(self):
        ex = LLMExtractor(VLLMClient(transport=FakeVLLMTransport(supported=())),
                          strict=True)
        with self.assertRaises(LLMExtractionError):
            ex.extract(TEXT)

    def test_null_extractor_calisir(self):
        ex = NullLLMExtractor()
        self.assertFalse(ex.available)
        self.assertEqual(ex.extract("herhangi bir metin"), [])
        self.assertIsNone(ex.call("metin").error)
        self.assertEqual(ex.stats["calls"], 0)

    def test_default_extractor_backend_yoksa_null(self):
        with mock.patch.dict(os.environ, {"LLM_BACKEND": "", "LLM_STRICT": ""}):
            self.assertIsInstance(default_extractor(), NullLLMExtractor)

    def test_default_extractor_strict_bilinmeyen_backend_yukseltir(self):
        with mock.patch.dict(os.environ, {"LLM_BACKEND": "openai", "LLM_STRICT": "1"}):
            with self.assertRaises(LLMExtractionError):
                default_extractor()

    def test_hata_loglanir(self):
        """Sessiz yutma yok: hata + ham çıktı loga düşer."""
        ex, _ = make_extractor(content="Üzgünüm, JSON üretemedim.")
        with self.assertLogs(_EXTRACTOR_LOGGER, level="WARNING") as cm:
            with mock.patch.object(
                    logging.getLogger(_EXTRACTOR_LOGGER), "level", logging.WARNING):
                ex.extract(TEXT, ["vade_ay"])
        self.assertTrue(any("ayristirilamadi" in line for line in cm.output))
        self.assertTrue(any("Üzgünüm" in line for line in cm.output))

    def test_summary_raporlanabilir(self):
        ex, _ = make_extractor(content=GOOD_JSON)
        ex.extract(TEXT, ["vade_ay"])
        s = ex.summary()
        self.assertEqual(s["structured_mode"], "json_schema")
        self.assertEqual(s["client"], "VLLMClient")
        self.assertEqual(s["ok"], 1)


# --------------------------------------------------------------------------- #
# 5. Şema sözleşmesi
# --------------------------------------------------------------------------- #
class TestSchema(unittest.TestCase):

    def test_type_union_kullanilmaz(self):
        """xgrammar uyumu: hiçbir yerde {"type": [...]} olmamalı."""
        blob = json.dumps(guided_json_schema())

        def walk(node):
            if isinstance(node, dict):
                if isinstance(node.get("type"), list):
                    self.fail(f"type-union bulundu: {node}")
                for v in node.values():
                    walk(v)
            elif isinstance(node, list):
                for v in node:
                    walk(v)

        walk(json.loads(blob))

    def test_ust_seviye_required_tum_alanlar(self):
        s = guided_json_schema()
        self.assertEqual(s["required"], EXTRACTION_FIELDS)
        self.assertFalse(s["additionalProperties"])

    def test_alt_kume_semasi_daralir(self):
        s = guided_json_schema(["vade_ay", "kar_payi_orani"])
        self.assertEqual(sorted(s["properties"]), ["kar_payi_orani", "vade_ay"])
        self.assertEqual(sorted(s["required"]), ["kar_payi_orani", "vade_ay"])

    def test_alan_tipleri_kanonik_bicimi_dayatir(self):
        props = guided_json_schema()["properties"]

        def value_schema(name):
            # anyOf[field_obj, null] -> field_obj.properties.value
            return props[name]["anyOf"][0]["properties"]["value"]["anyOf"][0]

        self.assertEqual(value_schema("vade_ay")["type"], "integer")
        self.assertEqual(
            value_schema("finansman_tutari")["properties"]["currency"]["enum"], ["TRY"])
        self.assertEqual(
            sorted(value_schema("masraf_durumu")["required"]), ["amount", "has_fee"])
        self.assertEqual(value_schema("hedef_kitle")["type"], "array")


# --------------------------------------------------------------------------- #
# 6. Ollama
# --------------------------------------------------------------------------- #
class TestOllama(unittest.TestCase):

    def test_keep_alive_ve_num_ctx_gonderilir(self):
        calls = []

        def transport(url, payload, timeout):
            calls.append(payload)
            return {"message": {"content": GOOD_JSON}}

        c = OllamaClient(transport=transport, keep_alive="30m", num_ctx=8192)
        resp = c.generate("s", "u", SCHEMA)
        p = calls[0]
        self.assertEqual(p["keep_alive"], "30m")
        self.assertEqual(p["options"]["num_ctx"], 8192)
        self.assertEqual(p["format"], SCHEMA)
        # Ollama logprob vermez -> güven modelin kendi bildirdiğinden gelir.
        self.assertEqual(resp.logprobs, [])
        ex = LLMExtractor(c)
        self.assertEqual(ex.extract(TEXT, ["vade_ay"])[0].confidence_source,
                         SOURCE_SELF_REPORTED)


# --------------------------------------------------------------------------- #
# 7. Uzlaştırma: doğrulama modu
# --------------------------------------------------------------------------- #
class StubExtractor(LLMExtractor):
    """LLM'e HANGİ alanların sorulduğunu kaydeden sahte çıkarıcı."""

    def __init__(self, fields=None):
        super().__init__(client=object())      # available=True olsun
        self._fields = fields or []
        self.asked: list[list[str]] = []

    def extract(self, text, missing=None):
        self.asked.append(list(missing or []))
        return list(self._fields)


class TestReconcileVerify(unittest.TestCase):

    TEXT = "Konut finansmanında kâr payı oranı %1,89, 120 aya kadar vade."

    def test_varsayilan_davranis_degismedi(self):
        """verify_low_conf=0.0 -> yalnız EKSİK alanlar sorulur (eski davranış)."""
        stub = StubExtractor()
        reconcile(self.TEXT, llm=stub)
        asked = set(stub.asked[0])
        rule_found = {f.field_name for f in reconcile(self.TEXT)}
        self.assertFalse(asked & rule_found)

    def test_dusuk_guvenli_kural_alanlari_da_sorulur(self):
        stub = StubExtractor()
        reconcile(self.TEXT, llm=stub, verify_low_conf=1.0)  # hepsi eşiğin altında
        asked = set(stub.asked[0])
        rule_found = {f.field_name for f in reconcile(self.TEXT)}
        self.assertTrue(rule_found.issubset(asked))

    def test_dogrulama_modunda_llm_kurali_duzeltebilir(self):
        from src.schemas import ExtractedField

        better = ExtractedField(
            field_name="kar_payi_orani", raw_value="%2,49", canonical_value=2.49,
            confidence=0.97, source_span="%2,49", extractor=Extractor.LLM,
            confidence_source=SOURCE_LOGPROB)
        stub = StubExtractor([better])
        out = {f.field_name: f for f in
               reconcile(self.TEXT, llm=stub, verify_low_conf=1.0)}
        self.assertIs(out["kar_payi_orani"].extractor, Extractor.LLM)

    def test_dogrulama_kapaliyken_llm_kurali_ezemez(self):
        from src.schemas import ExtractedField

        better = ExtractedField(
            field_name="kar_payi_orani", raw_value="%2,49", canonical_value=2.49,
            confidence=0.99, source_span="%2,49", extractor=Extractor.LLM)
        stub = StubExtractor([better])
        out = {f.field_name: f for f in reconcile(self.TEXT, llm=stub)}
        self.assertIs(out["kar_payi_orani"].extractor, Extractor.RULE)


if __name__ == "__main__":
    unittest.main()
