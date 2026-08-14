"""Çıktı token sınırı + kapanmamış dizge onarımı.

İlgili: src/extraction/llm/clients.py (`num_predict`, `stop`)
        src/extraction/llm/parse.py (`_kapanmamis_dizgeyi_onar`)
        docs/rapor/ozet-uretimi.md

## Bu testin varlık sebebi — ölçülmüş tek kök neden, iki farklı yüz

Ollama'nın çıktı token sınırı varsayılan olarak SINIRSIZDIR. Özet üretiminde
(`qwen2.5:7b-instruct`) model geçerli bir özet yazıp JSON'u kapatmadan
`<tool_call>` üretiyor ve ardından çöp döngüsüne giriyordu. Bu tek arıza iki
ayrı hata olarak görünüyordu:

    döngü zaman aşımına kadar sürerse -> LLMTransportError (180 sn)
    bağlam dolup çıktı kesilirse      -> LLMError "kesik yanit"

Ölçüldü: 10 belgenin 4'ü düşüyordu, belge başına 44 sn. `num_predict=512` +
`stop=["<tool_call>"]` + dar sınırlayıcı onarımı sonrası **20/20 başarılı,
belge başına 6,9 sn** (6,4 kat hızlanma, %0 hata).
"""

from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from unittest import mock

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.extraction.llm.clients import OllamaClient, VLLMClient
from src.extraction.llm.extractor import CIKARIM_NUM_PREDICT, LLMExtractor
from src.extraction.llm.parse import parse_llm_json

SEMA = {"type": "object", "properties": {"ozet": {"type": "string"}},
        "required": ["ozet"]}


def _istemci(**kw) -> OllamaClient:
    return OllamaClient(transport=lambda *a, **k: {}, **kw)


class CiktiSiniri(unittest.TestCase):

    def test_num_predict_payloada_giriyor(self):
        p = _istemci().build_payload("s", "u", SEMA)
        self.assertIn("num_predict", p["options"],
                      "sınırsız üretim ölçülmüş bir donma sebebidir")
        self.assertEqual(p["options"]["num_predict"], 512)

    def test_tool_call_kacisi_durduruluyor(self):
        p = _istemci().build_payload("s", "u", SEMA)
        self.assertIn("<tool_call>", p["options"]["stop"])

    def test_ortamdan_ayarlanabilir(self):
        self.assertEqual(_istemci(num_predict=128).build_payload(
            "s", "u", SEMA)["options"]["num_predict"], 128)

    def test_mevcut_secenekler_korundu(self):
        p = _istemci().build_payload("s", "u", SEMA)
        self.assertEqual(p["options"]["num_ctx"], 8192)
        self.assertIn("temperature", p["options"])


class CikarimButcesiAyri(unittest.TestCase):
    """Çıkarım yolu, özet yolunun tavanını PAYLAŞMAZ.

    512 özet işinin ölçülmüş sayısıdır (yukarıdaki sınıf). Çıkarım için
    yetersiz olduğu 2026-08-14'te ölçüldü (gold.v2'nin 48 belgesinin tamamı,
    bütçe 4096'ya açılıp `eval_count` okunarak): ihtiyaç ortanca 390, en çok
    955 token; belgelerin 12/48'i 512'yi aşıyordu — yani her dört belgeden
    biri JSON'u kapatamadan kesiliyordu. Ablasyonun `num_predict=2048` ile
    ELLE koşulmak zorunda kalmasının sebebi buydu.

    Buradaki testler iki yönlüdür: çıkarımın bütçesi büyümüş OLMALI, özet
    yolunun paylaşılan nesnesi ise dokunulmamış KALMALI.
    """

    def _yakalayan_istemci(self, kayit: list):
        def transport(url, payload, timeout):
            kayit.append(payload)
            return {"message": {"content": '{"vade_ay": null}'}}
        return OllamaClient(transport=transport)

    def test_cikarim_512den_buyuk_butce_gonderiyor(self):
        kayit: list = []
        LLMExtractor(self._yakalayan_istemci(kayit), strict=False).call("metin")
        self.assertGreater(kayit[0]["options"]["num_predict"], 512,
                           "512 ölçülerek çıkarımın yarısını kesiyor")
        self.assertEqual(kayit[0]["options"]["num_predict"],
                         CIKARIM_NUM_PREDICT)

    def test_paylasilan_istemci_DEGISMEDEN_kaliyor(self):
        """Özet yolu `llm.client`'ı doğrudan kullanır; tavanı gevşememeli."""
        kayit: list = []
        istemci = self._yakalayan_istemci(kayit)
        LLMExtractor(istemci, strict=False).call("metin")
        self.assertEqual(istemci.num_predict, 512)
        self.assertEqual(
            istemci.build_payload("s", "u", SEMA)["options"]["num_predict"], 512)

    def test_ortamdan_ezilebilir(self):
        kayit: list = []
        with mock.patch.dict(os.environ, {"LLM_EXTRACT_NUM_PREDICT": "999"}):
            LLMExtractor(self._yakalayan_istemci(kayit), strict=False).call("m")
        self.assertEqual(kayit[0]["options"]["num_predict"], 999)

    def test_butceyle_desteklemeyen_istemci_yine_calisiyor(self):
        """Protokol yalnız `generate_json` zorunlu kılar — sahte istemciler düşmesin."""
        class Sade:
            def generate_json(self, system, user, schema):
                return {"vade_ay": None}

        sonuc = LLMExtractor(Sade(), strict=False).call("metin")
        self.assertIsNone(sonuc.error)

    def test_pazarlik_PAYLASILAN_nesnede_onbelleklenir(self):
        """Kopya sığdır: pazarlık kopyada yapılırsa sonuç geri dönmez.

        O zaman paylaşılan istemci her çağrıda yeniden pazarlık eder ve
        `LLMExtractor.structured_mode` `None` raporlar — rapor "hangi modda
        koştuk" sorusunu cevaplayamaz. Bu test o regresyonu tutar.
        """
        cagri: list = []

        def transport(url, payload, timeout):
            cagri.append(payload)
            return {"choices": [{"message": {"content": '{"vade_ay": null}'}}]}

        istemci = VLLMClient(transport=transport)
        cikarici = LLMExtractor(istemci, strict=False)
        cikarici.call("metin")
        self.assertEqual(istemci.structured_mode, "json_schema",
                         "pazarlık sonucu paylaşılan nesneye yazılmalı")
        self.assertEqual(cikarici.structured_mode, "json_schema")

        n = len(cagri)
        cikarici.call("ikinci metin")
        self.assertEqual(len(cagri) - n, 1,
                         "ikinci çağrı yeniden pazarlık etmemeli")

    def test_vllm_butcesi_de_uygulaniyor(self):
        cagri: list = []

        def transport(url, payload, timeout):
            cagri.append(payload)
            return {"choices": [{"message": {"content": '{"vade_ay": null}'}}]}

        istemci = VLLMClient(transport=transport)
        LLMExtractor(istemci, strict=False).call("metin")
        # cagri[0] pazarlığın 1 token'lık ping'i; asıl çağrı sonuncusu.
        self.assertEqual(cagri[-1]["max_tokens"], CIKARIM_NUM_PREDICT)


class KapanmamisDizgeOnarimi(unittest.TestCase):
    """Onarım YALNIZ sınırlayıcıya dokunur; içerik üretmez."""

    def test_kapanis_tirnagi_dusmus_ozet_kurtarilir(self):
        obj, err = parse_llm_json('{"ozet": "maksimum kazanım 300 TL\'dir.}')
        self.assertIsNone(err)
        self.assertEqual(obj["ozet"], "maksimum kazanım 300 TL'dir.")

    def test_ikinci_alanda_da_calisir(self):
        obj, _ = parse_llm_json('{"ozet": "a", "not": "b}')
        self.assertEqual(obj, {"ozet": "a", "not": "b"})

    def test_nesne_KAPANMAMISSA_onarilmaz(self):
        """Model `}` yazmadıysa cevabını bitirmemiştir — kesik metin kabul edilmez."""
        obj, err = parse_llm_json('{"ozet": "yarım kalmış cümle')
        self.assertIsNone(obj)
        self.assertIn("kesik", err)

    def test_ic_ice_yapida_onarilmaz(self):
        """Açık dizgede `{`/`}` varsa neyin kesildiği belirsizdir."""
        obj, _ = parse_llm_json('{"a": "x", "b": {"c": "y}')
        self.assertIsNone(obj)

    def test_zaten_gecerli_json_bozulmaz(self):
        for ham, beklenen in (('{"ozet": "tam."}', {"ozet": "tam."}),
                              ('{"ozet": 5}', {"ozet": 5}),
                              ('{"a": {"b": "c"}}', {"a": {"b": "c"}})):
            with self.subTest(ham=ham):
                obj, err = parse_llm_json(ham)
                self.assertIsNone(err)
                self.assertEqual(obj, beklenen)

    def test_bos_ve_JSONsuz_girdi_yine_reddedilir(self):
        for ham in ("", "   ", "JSON yok burada", "}"):
            with self.subTest(ham=ham):
                self.assertIsNone(parse_llm_json(ham)[0])


if __name__ == "__main__":
    unittest.main()
