"""Tahmin üreticisi testleri — tek kaynak ve offline dürüstlüğü.

İlgili: ../eval/predictors.py

En kritik test `TestTekKaynak.test_run_eval_ve_ablation_ayni_tahmini_alir`:
iki harness'ın SESSİZCE ayrışması tam olarak bu modülün önlemek için var
olduğu hatadır (eski `run_eval` `is not None`, `ablation` `is_present`
kullanıyordu ve sayıları kıyaslanamazdı).

İkinci kritik test `TestOfflineDurustlugu`: LLM yokken sahte bir
"hibrit = kural" satırı üretilmediğini kilitler.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from eval.predictors import (
    CONFIG_HIBRIT,
    CONFIG_HIBRIT_VERIFY,
    CONFIG_KURAL,
    CONFIG_LLM,
    CONFIG_NAMES,
    DEFAULT_VERIFY_THRESHOLD,
    PredictorError,
    build_all,
    build_predictor,
    field_values,
    is_present,
    offline_llm,
)
from src.extraction.llm.extractor import LLMExtractor
from src.schemas import ExtractedField, Extractor

METIN = ("Konut finansmanında kâr payı oranı %1,89, 120 aya kadar vade. "
         "Tahsis ücreti 500 TL.")


def _field(name: str, value, conf: float = 0.9,
           extractor: Extractor = Extractor.RULE) -> ExtractedField:
    return ExtractedField(field_name=name, raw_value=str(value),
                          canonical_value=value, confidence=conf,
                          source_span=None, extractor=extractor)


class StubClient:
    """Sabit JSON döndüren sahte LLM istemcisi (ağ YOK)."""

    def __init__(self, payload: dict):
        self.payload = payload
        self.calls: list[tuple[str, list]] = []

    def generate_json(self, system: str, user: str, schema: dict) -> dict:
        self.calls.append((user, sorted(schema.get("properties", {}))))
        return dict(self.payload)


class TestMevcudiyetSemantigi(unittest.TestCase):
    """`is_present` / `field_values` — TEK tanım noktası."""

    def test_deger_varsa_present(self):
        self.assertTrue(is_present(_field("vade_ay", 120)))

    def test_none_present_degil(self):
        self.assertFalse(is_present(_field("vade_ay", None)))

    def test_sifir_present_sayilir(self):
        """0 geçerli bir değerdir ("masrafsız" -> amount 0). `None` ile
        karıştırılmamalı — bu ayrım halüsinasyon iddiasının temeli."""
        self.assertTrue(is_present(_field("tahsis_ucreti", 0)))

    def test_bos_liste_present_sayilir(self):
        """`[]` `None` değildir; şema semantiği bunu ayırır."""
        self.assertTrue(is_present(_field("hedef_kitle", [])))

    def test_field_values_none_alanlari_eler(self):
        fields = [_field("vade_ay", 120), _field("kar_payi_orani", None)]
        self.assertEqual(field_values(fields), {"vade_ay": 120})

    def test_tekrarli_alanda_yuksek_guven_kazanir(self):
        """Sıraya bağlı ölçüm olmasın: "sözlükte son yazan kazanır" DEĞİL."""
        fields = [_field("vade_ay", 36, conf=0.4), _field("vade_ay", 120, conf=0.9)]
        self.assertEqual(field_values(fields), {"vade_ay": 120})

    def test_tekrarli_alanda_sira_onemsiz(self):
        a = [_field("vade_ay", 120, conf=0.9), _field("vade_ay", 36, conf=0.4)]
        b = [_field("vade_ay", 36, conf=0.4), _field("vade_ay", 120, conf=0.9)]
        self.assertEqual(field_values(a), field_values(b))

    def test_bos_liste_bos_sozluk(self):
        self.assertEqual(field_values([]), {})


class TestKuralKonfigi(unittest.TestCase):
    """`kural` — LLM'e hiç dokunmaz, offline'da tam ölçülür."""

    def test_her_zaman_kullanilabilir(self):
        predictor = build_predictor(CONFIG_KURAL)
        self.assertTrue(predictor.available)
        self.assertIsNone(predictor.unavailable_reason)

    def test_tahmin_uretir(self):
        preds = build_predictor(CONFIG_KURAL).predict(METIN)
        self.assertEqual(preds.get("vade_ay"), 120)
        self.assertAlmostEqual(preds.get("kar_payi_orani"), 1.89)

    def test_llm_verilse_bile_kullanmaz(self):
        client = StubClient({"vade_ay": {"value": 999}})
        llm = LLMExtractor(client)
        build_predictor(CONFIG_KURAL, llm=llm).predict(METIN)
        self.assertEqual(client.calls, [], "kural konfigi LLM'i çağırmamalı")

    def test_hicbir_deger_none_degil(self):
        """Halüsinasyon yasağının eval tarafındaki karşılığı."""
        preds = build_predictor(CONFIG_KURAL).predict(METIN)
        self.assertTrue(all(v is not None for v in preds.values()))


class TestOfflineDurustlugu(unittest.TestCase):
    """LLM yoksa sahte satır ÜRETİLMEZ — kol açıkça "ölçülmedi" der."""

    LLM_GEREKTIREN = (CONFIG_LLM, CONFIG_HIBRIT, CONFIG_HIBRIT_VERIFY)

    def test_llm_yoksa_kullanilamaz(self):
        for config in self.LLM_GEREKTIREN:
            with self.subTest(config=config):
                predictor = build_predictor(config, llm=offline_llm())
                self.assertFalse(predictor.available)

    def test_gerekce_turkce_ve_yol_gosterici(self):
        predictor = build_predictor(CONFIG_HIBRIT, llm=offline_llm())
        reason = predictor.unavailable_reason or ""
        self.assertIn("ÖLÇÜLMEDİ", reason)
        self.assertIn("LLM_BACKEND", reason)

    def test_kullanilamaz_konfig_cagrilinca_hata(self):
        """Sessizce boş sonuç döndürmek "hibrit = 0" satırı üretirdi."""
        predictor = build_predictor(CONFIG_HIBRIT, llm=offline_llm())
        with self.assertRaises(PredictorError):
            predictor.predict(METIN)

    def test_kural_offline_etkilenmez(self):
        self.assertTrue(build_predictor(CONFIG_KURAL, llm=offline_llm()).available)


class TestLLMliKonfigler(unittest.TestCase):
    """LLM varken kollar gerçekten farklı davranıyor mu?"""

    def test_llm_konfigi_kullanilabilir(self):
        llm = LLMExtractor(StubClient({}))
        self.assertTrue(build_predictor(CONFIG_LLM, llm=llm).available)

    def test_hibrit_kural_degerini_korur(self):
        """Kural birincildir: LLM farklı bir değer önerse bile kural kazanır."""
        client = StubClient({"vade_ay": {"value": 999, "confidence": 0.99}})
        llm = LLMExtractor(client)
        preds = build_predictor(CONFIG_HIBRIT, llm=llm).predict(METIN)
        self.assertEqual(preds["vade_ay"], 120)

    def test_hibrit_eksik_alani_llm_ile_doldurur(self):
        client = StubClient({"hedef_kitle": {"value": ["yeni_musteri"],
                                             "confidence": 0.8}})
        llm = LLMExtractor(client)
        kural = build_predictor(CONFIG_KURAL).predict(METIN)
        hibrit = build_predictor(CONFIG_HIBRIT, llm=llm).predict(METIN)
        self.assertNotIn("hedef_kitle", kural)
        self.assertEqual(hibrit.get("hedef_kitle"), ["yeni_musteri"])

    def test_hibrit_verify_esigi_aciklamaya_yazilir(self):
        llm = LLMExtractor(StubClient({}))
        predictor = build_predictor(CONFIG_HIBRIT_VERIFY, llm=llm,
                                    verify_threshold=0.6)
        self.assertIn("0.6", predictor.description)

    def test_hibrit_verify_dusuk_guvenli_alani_da_sorar(self):
        """`verify_low_conf` kolunun GERÇEKTEN farklı davrandığının kanıtı.

        Eşik 1.0 -> tüm kural alanları düşük güvenli sayılır ve LLM'e sorulur.
        `hibrit` yalnız EKSİK alanları sorar; `hibrit-verify` daha fazlasını.
        """
        client_a = StubClient({})
        client_b = StubClient({})
        build_predictor(CONFIG_HIBRIT, llm=LLMExtractor(client_a)).predict(METIN)
        build_predictor(CONFIG_HIBRIT_VERIFY, llm=LLMExtractor(client_b),
                        verify_threshold=1.0).predict(METIN)
        sorulan_hibrit = set(client_a.calls[0][1])
        sorulan_verify = set(client_b.calls[0][1])
        self.assertTrue(sorulan_verify > sorulan_hibrit,
                        "hibrit-verify daha çok alan sormalıydı — kol ölü demektir")

    def test_verify_esigi_varsayilani(self):
        self.assertAlmostEqual(DEFAULT_VERIFY_THRESHOLD, 0.75)


class TestTekKaynak(unittest.TestCase):
    """En kritik değişmez: TÜM harness'lar AYNI tahmin kümesini alır."""

    def test_run_eval_ve_ablation_ayni_tahmini_alir(self):
        """İki harness aynı `Predictor.predict` üzerinden geçer.

        Eski kodda `run_eval` `preds[name] is not None`, `ablation`
        `f.is_present` süzgeci kullanıyordu; ikisi bugün aynı sonucu veriyordu
        ama bu bir TESADÜFtü. Bu test tesadüfü sözleşmeye çevirir.
        """
        from eval.ablation import score_all as ablation_score
        from eval.matchers import strict_match
        from eval.run_eval import score_all as run_eval_score
        from scripts.gold_schema import GoldRecord

        self.assertIs(ablation_score, run_eval_score,
                      "iki harness AYNI puanlama çekirdeğini kullanmalı")

        predictor = build_predictor(CONFIG_KURAL)
        record = GoldRecord(id="t1", text=METIN, fields={"vade_ay": 120})
        a = run_eval_score([record], predictor, strict_match)
        b = ablation_score([record], predictor, strict_match)
        self.assertEqual(a[0].per_field["vade_ay"].tp,
                         b[0].per_field["vade_ay"].tp)

    def test_predict_ve_fields_tutarli(self):
        predictor = build_predictor(CONFIG_KURAL)
        fields = predictor.fields(METIN)
        self.assertEqual(predictor.predict(METIN), field_values(fields))

    def test_deterministik(self):
        predictor = build_predictor(CONFIG_KURAL)
        self.assertEqual(predictor.predict(METIN), predictor.predict(METIN))


class TestKayit(unittest.TestCase):
    """Konfig kayıt defteri."""

    def test_bilinmeyen_konfig_hata(self):
        with self.assertRaises(PredictorError):
            build_predictor("kural-only")     # eski ad; sessizce kabul EDİLMEMELİ

    def test_tum_konfigler_kurulabiliyor(self):
        llm = LLMExtractor(StubClient({}))
        for config in CONFIG_NAMES:
            with self.subTest(config=config):
                self.assertEqual(build_predictor(config, llm=llm).name, config)

    def test_build_all_tek_llm_ornegi_paylasir(self):
        """Tek örnek: `llm.stats` tüm kollar üzerinden toplanabilsin."""
        llm = LLMExtractor(StubClient({}))
        predictors = build_all([CONFIG_LLM, CONFIG_HIBRIT], llm=llm)
        self.assertEqual(len(predictors), 2)
        self.assertTrue(all(p.available for p in predictors))

    def test_build_all_offline_hepsini_isaretler(self):
        predictors = build_all(list(CONFIG_NAMES), llm=offline_llm())
        by_name = {p.name: p for p in predictors}
        self.assertTrue(by_name[CONFIG_KURAL].available)
        self.assertFalse(by_name[CONFIG_HIBRIT].available)

    def test_aciklamalar_turkce_ve_dolu(self):
        llm = LLMExtractor(StubClient({}))
        for config in CONFIG_NAMES:
            with self.subTest(config=config):
                self.assertTrue(build_predictor(config, llm=llm).description)


if __name__ == "__main__":
    unittest.main()
