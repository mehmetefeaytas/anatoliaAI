"""Şartname §5.2 ve §5.5 terminoloji kapsamı testleri.

## Neden bu dosya var

Şartname iki maddede **isim isim** ne beklendiğini sayıyor; jüri bunları
tek tek kontrol edebilir. 31 Temmuz 2026 denetiminde iki boşluk bulundu:

**§5.5 — Katılım Bankacılığı Terminolojisine Uyum.** Beş kavram sayılıyor:
kâr payı oranı · finansman maliyeti · katılım fonu · masrafsız finansman ·
avantajlı finansman. Bunlardan **finansman maliyeti** ve **katılım fonu**
yalnızca LLM prompt'unda (`llm/schema.py:241,244`) tanımlıydı — yani LLM
kapalıyken (offline varsayılanımız) sistem o iki kavramı hiç bilmiyordu.
Korpus ölçümü: `katılım fonu` **173**, `finansman maliyeti` **53** belgede
geçiyor.

**§5.2 — Metin Analizi Yeteneği.** Dört ifade biçimi sayılıyor; üçünde
**sayı yoktur**: "avantajlı kâr payı fırsatı", "özel oranlı finansman",
"düşük maliyetli finansman". Bunlardan oran üretmek halüsinasyondur.
Korpusta 54 belge nitel iddia taşıyor ve **45'inde hiç sayısal oran yok** —
naif bir sistem ya sayı uydurur ya belgeyi sessizce düşürür.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.extraction.ner.classifier import RuleHintClassifier  # noqa: E402
from src.extraction.rules.extract import extract_all  # noqa: E402
from src.extraction.rules.synonyms import (  # noqa: E402
    TERMINOLOGY_5_5,
    qualitative_rate_claim,
    terminology_hits,
)
from src.preprocessing.clean import normalize_text, tr_fold_ascii  # noqa: E402


def _kat(metin: str) -> str:
    return tr_fold_ascii(normalize_text(metin))


class TestSartname55Terminoloji(unittest.TestCase):
    """Şartnamenin saydığı beş kavramın hepsi tanımlı olmalı."""

    def test_bes_kavramin_hepsi_tanimli(self) -> None:
        beklenen = {"kar_payi_orani", "finansman_maliyeti", "katilim_fonu",
                    "masrafsiz_finansman", "avantajli_finansman"}
        self.assertEqual(set(TERMINOLOGY_5_5), beklenen)

    def test_her_kavramin_tanimi_ve_birimi_var(self) -> None:
        for kavram, bilgi in TERMINOLOGY_5_5.items():
            with self.subTest(kavram=kavram):
                self.assertTrue(bilgi.get("tanim", "").strip())
                self.assertTrue(bilgi.get("birim", "").strip())

    def test_finansman_maliyeti_taniniyor(self) -> None:
        for metin in ("Toplam finansman maliyeti 45.000 TL'dir.",
                      "Yıllık Maliyet Oranı %82,32",
                      "toplam geri ödeme tutarı"):
            with self.subTest(metin=metin):
                self.assertIn("finansman_maliyeti", terminology_hits(_kat(metin)))

    def test_katilim_fonu_taniniyor(self) -> None:
        for metin in ("Katılım Fonu hesabınızı açın",
                      "katılma hesabı avantajları",
                      "kâr-zarar paylaşımı esasına göre"):
            with self.subTest(metin=metin):
                self.assertIn("katilim_fonu", terminology_hits(_kat(metin)))

    def test_finansman_maliyeti_kar_payi_ile_karistirilmaz(self) -> None:
        """İkisi farklı büyüklük: biri tutar (TL), biri oran (%).

        Aynı alana yazmak karşılaştırmayı sessizce bozar — şartnamenin
        tanımı da bunları ayrı tarif ediyor.
        """
        self.assertNotEqual(TERMINOLOGY_5_5["finansman_maliyeti"]["birim"],
                            TERMINOLOGY_5_5["kar_payi_orani"]["birim"])
        self.assertIn("karistirma", TERMINOLOGY_5_5["finansman_maliyeti"])

    def test_ilgisiz_metin_kavram_uretmez(self) -> None:
        self.assertEqual(terminology_hits(_kat("Mağazalarda %15 indirim")), {})


class TestSartname52NitelIddialar(unittest.TestCase):
    """Sayı içermeyen oran iddiaları tanınmalı ama SAYIYA ÇEVRİLMEMELİ."""

    # Şartname §5.2'nin birebir saydığı dört biçimden sayısal olmayan üçü
    SARTNAME_ORNEKLERI = [
        "avantajlı kâr payı fırsatı",
        "özel oranlı finansman",
        "düşük maliyetli finansman",
    ]

    def test_sartnamenin_uc_ornegi_de_taniniyor(self) -> None:
        for metin in self.SARTNAME_ORNEKLERI:
            with self.subTest(metin=metin):
                self.assertIsNotNone(
                    qualitative_rate_claim(_kat(metin)),
                    f"§5.2'nin saydığı {metin!r} tanınmadı")

    def test_nitel_iddia_sayisal_oran_URETMEZ(self) -> None:
        """En kritik değişmez: sayı yoksa uydurulmaz (CLAUDE.md §19)."""
        for metin in self.SARTNAME_ORNEKLERI:
            with self.subTest(metin=metin):
                oranlar = [a for a in extract_all(normalize_text(metin))
                           if a.field_name == "kar_payi_orani"]
                self.assertEqual(
                    oranlar, [],
                    f"{metin!r} sayısal oran üretti — halüsinasyon")

    def test_sayisal_ifade_hala_cikariliyor(self) -> None:
        """§5.2'nin dördüncü biçimi sayısaldır ve çıkarılmaya devam etmeli."""
        alanlar = extract_all(normalize_text("%2,05 kâr payı oranı ile finansman"))
        oranlar = [a for a in alanlar if a.field_name == "kar_payi_orani"]
        self.assertTrue(oranlar, "sayısal oran çıkarımı bozuldu")
        self.assertEqual(oranlar[0].canonical_value, 2.05)

    def test_nitel_ve_sayisal_birlikte(self) -> None:
        """İddia sayıyı bastırmamalı: ikisi bir aradaysa sayı kazanır."""
        metin = normalize_text("Avantajlı kâr payı fırsatı: %1,89 oranla")
        self.assertIsNotNone(qualitative_rate_claim(tr_fold_ascii(metin)))
        oranlar = [a for a in extract_all(metin)
                   if a.field_name == "kar_payi_orani"]
        self.assertTrue(oranlar, "nitel iddia sayısal çıkarımı engelledi")

    def test_ilgisiz_metin_iddia_uretmez(self) -> None:
        self.assertIsNone(qualitative_rate_claim(_kat("Kampanya 31.12.2026'ya kadar")))

    def test_sozcuk_siniri_uygulaniyor(self) -> None:
        """Alt-dize eşleşmesi bu projede korpusun %48'ini bozmuştu."""
        self.assertIsNone(qualitative_rate_claim(_kat("dezavantajlıoranlar")))


class TestSartname54Siniflandirma(unittest.TestCase):
    """§5.4'ün sekiz kampanya türü."""

    SEKIZ_TUR = ("Finansman", "İhtiyaç Finansmanı", "Konut Finansmanı",
                 "Taşıt Finansmanı", "Kart", "Alışveriş Puanı",
                 "Yeni Müşteri", "Yatırım Ürünü")

    def test_katilim_fonu_yatirim_urunu_olarak_siniflanir(self) -> None:
        """§5.5'in 'katılım fonu' kavramı §5.4'ün 'Yatırım Ürünü' türüdür."""
        tur, _ = RuleHintClassifier().classify(
            normalize_text("Katılım Fonu hesabı ile birikimlerinizi değerlendirin"))
        self.assertEqual(tur, "Yatırım Ürünü")

    def test_sekiz_turun_hepsi_uretilebiliyor(self) -> None:
        clf = RuleHintClassifier()
        ornekler = {
            "Konut Finansmanı": "konut finansmanı kampanyası",
            "Taşıt Finansmanı": "taşıt finansmanı fırsatı",
            "İhtiyaç Finansmanı": "ihtiyaç finansmanı",
            "Kart": "kredi kartı kampanyası",
            "Alışveriş Puanı": "alışveriş puanı kazanın",
            "Yeni Müşteri": "yeni müşterilere özel hoş geldin",
            "Yatırım Ürünü": "katılma hesabı ve altın hesabı",
            "Finansman": "finansman imkânı",
        }
        for beklenen, metin in ornekler.items():
            with self.subTest(tur=beklenen):
                tur, _ = clf.classify(normalize_text(metin))
                self.assertEqual(tur, beklenen)

    def test_sekiz_tur_listesi_sartnameyle_ayni(self) -> None:
        from src.extraction.rules.synonyms import TYPE_HINTS
        self.assertEqual(set(TYPE_HINTS), set(self.SEKIZ_TUR))


if __name__ == "__main__":
    unittest.main()
