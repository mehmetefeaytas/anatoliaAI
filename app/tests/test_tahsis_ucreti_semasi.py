"""`tahsis_ucreti` PARA tiplidir; oran biçimi üretilmez ve uydurulmaz.

İlgili: src/extraction/rules/extract.py (`extract_from_rate_table`,
        `extract_tahsis_ucreti`, `_TAHSIS_KOLON_RE`, `_ONCEKI_TUTAR_RE`)
        scripts/gold_schema.py (`MONEY_FIELDS`)
        data/gold/ANNOTATION_GUIDE.md §5 (oransal ücret kuralı)

## Bu testin varlık sebebi (ölçüm, 2026-08-09)

`scripts/lint_review_csv` round1 dosyalarında 10 hata veriyordu; **9'u**
`tahsis_ucreti: … {'rate': 0.5} geldi`. Kaynak `extract_from_rate_table`ti:
Türkiye Finans maliyet tablolarında ücret gerçekten ORAN olarak yazılı
("Tahsis Ücreti … %0,50") ama alan para tipli.

`data/demo.db` (1774 belge) üzerinde ölçülen üç ayrı defekt:

1. Oran biçimli 19 değer şema dışıydı; `compare._scalar` zaten hiçbirini
   sıralamıyordu ("oran biçimli ücret — TL ile kıyaslanamaz"), yani değer
   yalnız hataya mal oluyordu.
2. Bu 19 değerin **4'ü** tabloda HİÇ OLMAYAN bir kolondan geliyordu
   (%3,80 ve %8,07 "Aylık/Yıllık Maliyet Oranı", %0,00 ise kolon yok) —
   halüsinasyon.
3. Oran alan işgal ettiği için tekil çıkarıcı susuyordu; serbest bırakılınca
   ortaya çıkan "500 TL tahsis ücreti, 3.000 TL ipotek tesis ücreti"
   cümlesinde ileri pencere YANLIŞ KALEMİN tutarını (3.000) okuyordu.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from scripts.gold_schema import validate_canonical
from src.extraction.rules.extract import (
    extract_all,
    extract_from_rate_table,
    extract_tahsis_ucreti,
    extract_taksit,
    parse_rate_table,
)

# Türkiye Finans biçimi — "Tahsis Ücreti" kolonu GERÇEKTEN var, değeri oran.
TABLO_KOLONLU = (
    "Vade Kâr Payı Oranı Tahsis Ücreti Yıllık Maliyet Oranı "
    "3 4,09% 0,50% 5,63% 12 4,05% 0,50% 5,37% 36 3,89% 0,50% 5,10%")

# Kuveyt Türk biçimi — tahsis kolonu YOK; oradaki yüzde "Aylık Maliyet Oranı".
TABLO_KOLONSUZ = (
    "Vade Aylık Kar Oranı Taksit Tutarı Toplam Masraflar Aylık Maliyet Oranı "
    "12 4,52% 8,07% 96,86%")


def _alanlar(fields):
    return {f.field_name: f.canonical_value for f in fields}


class OranAlanaYazilmaz(unittest.TestCase):

    def test_oran_tablosu_tahsis_ucreti_uretmez(self) -> None:
        self.assertNotIn("tahsis_ucreti", _alanlar(
            extract_from_rate_table(TABLO_KOLONLU)))

    def test_oran_masraf_durumuna_yazilir(self) -> None:
        """Bilgi kaybolmaz: ücret VAR, TL tutarı YOK (ANNOTATION_GUIDE §5)."""
        self.assertEqual(
            _alanlar(extract_from_rate_table(TABLO_KOLONLU))["masraf_durumu"],
            {"has_fee": True, "amount": None})

    def test_tablodan_gelen_her_deger_semaya_uyar(self) -> None:
        for f in extract_from_rate_table(TABLO_KOLONLU):
            with self.subTest(alan=f.field_name):
                self.assertIsNone(
                    validate_canonical(f.field_name, f.canonical_value))


class OlmayanKolondanDegerDevsirilmez(unittest.TestCase):
    """Kolon başlıkta adlandırılmıyorsa ücret YOKTUR — komşu kolon okunmaz."""

    def test_kolonsuz_tabloda_ucret_satiri_bos(self) -> None:
        for satir in parse_rate_table(TABLO_KOLONSUZ):
            self.assertIsNone(satir.tahsis_ucreti)

    def test_kolonsuz_tabloda_masraf_durumu_da_uretilmez(self) -> None:
        self.assertNotIn("masraf_durumu",
                         _alanlar(extract_from_rate_table(TABLO_KOLONSUZ)))

    def test_kolonlu_tabloda_oran_okunur(self) -> None:
        oranlar = {r.tahsis_ucreti for r in parse_rate_table(TABLO_KOLONLU)}
        self.assertEqual(oranlar, {0.5})


class TabloMasrafDurumuYedektir(unittest.TestCase):
    """Tekil çıkarıcı TL tutarını biliyorsa onunki kazanır — bilgi kaybı olmaz."""

    def test_metindeki_tutar_tabloyu_yener(self) -> None:
        metin = TABLO_KOLONLU + " Dosya masrafı 750 TL olarak tahsil edilir."
        self.assertEqual(_alanlar(extract_all(metin))["masraf_durumu"],
                         {"has_fee": True, "amount": 750.0})

    def test_tekil_cikarici_susarsa_tablo_devreye_girer(self) -> None:
        self.assertEqual(_alanlar(extract_all(TABLO_KOLONLU))["masraf_durumu"],
                         {"has_fee": True, "amount": None})


class SoldakiTutarKazanir(unittest.TestCase):
    """"500 TL tahsis ücreti" — tutar tetikleyicinin SOLUNDA olabilir."""

    METIN = ("Alınacak ücretler: 60 ay vadede 500 TL tahsis ücreti, "
             "3.000 TL ipotek tesis ücreti, 16.500 TL Ekspertiz ücretidir")

    def test_yanlis_kalemin_tutari_alinmaz(self) -> None:
        f = extract_tahsis_ucreti(self.METIN)
        self.assertEqual(f.canonical_value, {"value": 500.0, "currency": "TRY"})

    def test_kanit_tutari_gosterir(self) -> None:
        f = extract_tahsis_ucreti(self.METIN)
        self.assertEqual(self.METIN[f.span_start:f.span_end], f.raw_value)
        self.assertIn("500 TL", f.raw_value)

    def test_sagdaki_tutar_biciminde_gerileme_yok(self) -> None:
        f = extract_tahsis_ucreti("Tahsis ücreti 500 TL olarak alınır.")
        self.assertEqual(f.canonical_value, {"value": 500.0, "currency": "TRY"})

    def test_negasyon_hala_sifir(self) -> None:
        f = extract_tahsis_ucreti("1.000 TL tahsis ücreti alınmaz.")
        self.assertEqual(f.canonical_value, {"value": 0.0, "currency": "TRY"})


class TaksitSayisiPozitiftir(unittest.TestCase):
    """Zaman damgası taksit sayısı DEĞİLDİR; '0 taksit' diye bir şey yok."""

    def test_zaman_damgasi_taksit_sayilmaz(self) -> None:
        metin = ("Ücret tahsil edilir. 02.01.2026 00:00:00 Taksitli Ticari "
                 "Taşıt Finansmanı Finansman Oranı")
        self.assertIsNone(extract_taksit(metin))

    def test_gercek_taksit_ilk_gecersizden_sonra_da_bulunur(self) -> None:
        metin = ("02.01.2026 00:00:00 Taksitli Ticari Finansman. "
                 "Vade farksız 6 taksit imkânı.")
        self.assertEqual(extract_taksit(metin).canonical_value, 6)

    def test_uzun_sayinin_son_uc_hanesi_taksit_sanilmaz(self) -> None:
        self.assertIsNone(extract_taksit("Belge kodu MSTS.0026.59 TAKSİTLENDİRME"))


if __name__ == "__main__":
    unittest.main()
