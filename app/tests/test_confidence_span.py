"""Güven skoru + kaynak offset (span) regresyon testleri.

İlgili: ../../decisions/daraltilmis-yenilikcilik-hedefleri.md (hedef #1)
        ../src/extraction/rules/confidence.py
        CLAUDE.md §18, şartname §7 "Model Başarısı" (%30)

İki tasarım zaafı kapatıldı:

Z1 — `source_span` yalnızca bir ±40 karakterlik metin parçasıydı; dashboard'daki
     kaynak vurgulaması için orijinal metinde güvenilir biçimde bulunamıyordu.
     Artık `span_start`/`span_end` karakter offset'leri var ve `verify_span()`
     ile kendi kendini denetliyor.

Z2 — `confidence` her kural çıkarımında sabit 0.95'ti. Sabit skor kalibre
     edilemez (ECE tek bin'e düşer), abstain eşiği ayrım yapamaz ve jüriye
     savunulamaz. Artık tetikleyici yakınlığı + makullük + belirsizlikten
     hesaplanıyor.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.extraction.rules import confidence as C
from src.extraction.rules.extract import extract_all, extract_kar_payi


class TestSpanOffsetleri(unittest.TestCase):
    """Z1: vurgulanan yer gerçekten raporlanan değeri göstermeli."""

    METIN = (
        "Konut Finansmanı Kampanyası. Kuveyt Türk konut finansmanında kâr payı "
        "oranı %1,89'dan başlayan oranlarla, 120 aya kadar vade imkânı. "
        "Tahsis ücreti 750 TL. Kampanya 31.12.2026 tarihine kadar geçerlidir."
    )

    def test_tum_alanlarin_offsetleri_dogrulanir(self):
        fields = extract_all(self.METIN)
        self.assertGreater(len(fields), 0, "hiç alan çıkmadı")
        for f in fields:
            self.assertTrue(
                f.verify_span(self.METIN),
                f"{f.field_name}: offset {f.span_start}-{f.span_end} "
                f"metinde {self.METIN[f.span_start:f.span_end]!r} gösteriyor "
                f"ama raw_value {f.raw_value!r}",
            )

    def test_offsetler_dogru_degeri_isaret_eder(self):
        by_name = {f.field_name: f for f in extract_all(self.METIN)}
        self.assertEqual(
            self.METIN[by_name["kar_payi_orani"].span_start:
                       by_name["kar_payi_orani"].span_end],
            "%1,89",
        )
        self.assertEqual(
            self.METIN[by_name["kampanya_suresi"].span_start:
                       by_name["kampanya_suresi"].span_end],
            "31.12.2026",
        )

    def test_verify_span_yanlis_offseti_reddeder(self):
        f = extract_kar_payi(self.METIN)
        f.span_start = 0            # kasıtlı bozma
        self.assertFalse(f.verify_span(self.METIN))

    def test_offset_yoksa_verify_false(self):
        f = extract_kar_payi(self.METIN)
        f.span_start = f.span_end = None
        self.assertFalse(f.verify_span(self.METIN))


class TestGuvenSkoru(unittest.TestCase):
    """Z2: skor sabit değil, ayrım yapıyor."""

    def test_sabit_degil(self):
        skorlar = {
            extract_kar_payi("kâr payı oranı %2,05").confidence,
            extract_kar_payi("kâr payı oranı %890,5").confidence,
            extract_kar_payi("kâr payı oranı %1,99 - %2,49").confidence,
        }
        self.assertGreater(len(skorlar), 1, "güven hâlâ sabit görünüyor")

    def test_makul_disi_deger_guveni_dusurur(self):
        iyi = extract_kar_payi("kâr payı oranı %2,05").confidence
        kotu = extract_kar_payi("kâr payı oranı %890,5").confidence
        self.assertLess(kotu, iyi - 0.2, "makul dışı değer cezalandırılmadı")

    def test_aralik_nokta_degerden_daha_az_kesin(self):
        nokta = extract_kar_payi("kâr payı oranı %2,05").confidence
        aralik = extract_kar_payi("kâr payı oranı %1,99 - %2,49").confidence
        self.assertLess(aralik, nokta)

    def test_belirsizlik_guveni_dusurur(self):
        tek = extract_kar_payi("kâr payı oranı %1,89").confidence
        cok = extract_kar_payi(
            "kâr payı oranı %1,89 veya kâr payı oranı %2,45 "
            "ya da kâr payı oranı %3,10"
        ).confidence
        self.assertLess(cok, tek)

    def test_normalize_edilemeyen_deger_sifir_guven(self):
        skor, gerekce = C.score("kar_payi_orani", None)
        self.assertEqual(skor, 0.0)
        self.assertIn("normalize", gerekce)

    def test_skor_sinirlar_icinde(self):
        for canon in [1.89, 890.5, {"min": 1.0, "max": 2.0}, 0.0]:
            for dist in [None, 0, 10, 200]:
                s, _ = C.score("kar_payi_orani", canon, trigger_distance=dist)
                self.assertGreaterEqual(s, C.FLOOR)
                self.assertLessEqual(s, C.CEIL)

    def test_confidence_source_isaretlenir(self):
        f = extract_kar_payi("kâr payı oranı %2,05")
        self.assertEqual(f.confidence_source, "rule_heuristic")


class TestMakulluk(unittest.TestCase):
    """Aralık kontrolü hem min hem max'a bakmalı."""

    def test_aralikta_max_disarideysa_makul_degil(self):
        # {min: 1.89, max: 120.0} — bozuk aralık; yalnız min'e bakılsa
        # "makul" görünürdü.
        self.assertIs(
            C.is_plausible("kar_payi_orani", {"min": 1.89, "max": 120.0}),
            False,
        )

    def test_gecerli_aralik_makul(self):
        self.assertIs(
            C.is_plausible("kar_payi_orani", {"min": 1.99, "max": 2.49}),
            True,
        )

    def test_aralik_tanimsiz_alanda_karar_yok(self):
        self.assertIsNone(C.is_plausible("kampanya_suresi", "2026-12-31"))
        self.assertIsNone(C.is_plausible("masraf_durumu", {"has_fee": False}))


class TestAralikYanlisPozitifi(unittest.TestCase):
    """REGRESYON: 'ile' bağlacı aralık ayırıcı sanılıyordu.

    "kâr payı oranı %1,89 ile 120 aya kadar vade" ifadesindeki 'ile' bağlaçtır.
    Sistem bunu {min: 1.89, max: 120.0} diye okuyup bir VADEYİ oran üst sınırı
    olarak karşılaştırma tablosuna yazıyordu.
    """

    def test_birim_sozcugu_araligi_iptal_eder(self):
        for text in ["kâr payı oranı %1,89 ile 36 ay vade",
                     "kâr payı oranı %1,89 ile 120 aya kadar",
                     "kâr payı oranı %1,89 ile 12 taksit"]:
            self.assertEqual(extract_kar_payi(text).canonical_value, 1.89, text)

    def test_gercek_araliklar_korunur(self):
        for text in ["kâr payı oranı %1,99 - %2,49 arasında",
                     "kâr payı oranı %1,99 ile %2,49 arasında",
                     "kâr payı oranı %1,99 ila 2,49 arasında"]:
            self.assertEqual(
                extract_kar_payi(text).canonical_value,
                {"min": 1.99, "max": 2.49}, text,
            )


if __name__ == "__main__":
    unittest.main()
