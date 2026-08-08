"""Oran tablosundan gelen her değerin KANITI olmalı.

İlgili: src/extraction/rules/extract.py (`_ORAN_TABLOSU_BASLIK_RE`,
        `parse_rate_table`, `extract_from_rate_table`)
        docs/rapor/genel-denetim.md §"B" (span=[0,0] bulgusu)

## Bu testin varlık sebebi

Başlık deseni bir zamanlar İKİ KOPYAydı ve kopyalar ayrışmıştı:
`parse_rate_table` "payı"yı opsiyonel sayıyor ("Vade Kar Oranı" da tablo),
`extract_from_rate_table` ise zorunlu tutuyordu. Tablo ayrışıyor, değer
üretiliyor, ama ikinci arama tutmadığı için konum `(0, 0)`a düşüyordu:
`raw_value` boş, `span` yok, güven yine 0,95.

Ölçüldü: 70 `kar_payi_orani` kaydının **26'sı (%37)** böyleydi. Değerler
YANLIŞ değildi — yalnız KANITSIZdı, bu yüzden hiçbir doğruluk metriği bunu
göstermiyordu. Projenin en özgün iddiası ("her değer bir karakter aralığına
bağlıdır") tam olarak burada tutmuyordu.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.extraction.rules.extract import (
    _ORAN_TABLOSU_BASLIK_RE,
    extract_from_rate_table,
    parse_rate_table,
)

# Üç gerçek başlık varyantı. İkincisi ve üçüncüsü eski katı desene TAKILMIYORDU.
TABLOLAR = {
    "kar_payi_orani_baslik": (
        "Vade Kâr Payı Oranı Tahsis Ücreti Aylık Maliyet "
        "3 4,09% 0,50% 5,63% 12 4,05% 0,50% 5,37% 36 3,89% 0,50% 5,10%"),
    "payi_YOK_baslik": (
        "Vade Kar Oranı Tahsis Ücreti Aylık Maliyet "
        "3 4,09% 0,50% 5,63% 12 4,05% 0,50% 5,37% 36 3,89% 0,50% 5,10%"),
    "paylasim_baslik": (
        "Vade Kâr Paylaşım Oranı Tahsis Ücreti Aylık Maliyet "
        "3 4,09% 0,50% 5,63% 12 4,05% 0,50% 5,37% 36 3,89% 0,50% 5,10%"),
}


class TekDogrulukKaynagi(unittest.TestCase):

    def test_ayristiran_desen_konumu_da_verir(self):
        """`parse_rate_table` satır döndürdüyse başlık BULUNMUŞ olmalı."""
        for ad, metin in TABLOLAR.items():
            with self.subTest(ad=ad):
                self.assertTrue(parse_rate_table(metin),
                                "tablo ayrışmalıydı")
                self.assertIsNotNone(
                    _ORAN_TABLOSU_BASLIK_RE.search(metin),
                    "tablo ayrıştı ama başlık bulunamadı — iki desen ayrışmış")


class HerDegerinKanitiVar(unittest.TestCase):

    def test_uc_baslik_varyantinda_da_span_uretilir(self):
        for ad, metin in TABLOLAR.items():
            with self.subTest(ad=ad):
                alanlar = {f.field_name: f for f in extract_from_rate_table(metin)}
                self.assertIn("kar_payi_orani", alanlar)
                f = alanlar["kar_payi_orani"]
                self.assertGreater(
                    f.span_end, f.span_start,
                    f"{ad}: span=(0,0) — değer var, kanıt yok")
                self.assertTrue(
                    (f.raw_value or "").strip(),
                    f"{ad}: raw_value boş — değer var, kanıt yok")

    def test_span_gercekten_metne_isaret_ediyor(self):
        metin = TABLOLAR["payi_YOK_baslik"]
        f = {x.field_name: x for x in extract_from_rate_table(metin)}["kar_payi_orani"]
        self.assertEqual(metin[f.span_start:f.span_end], f.raw_value,
                         "span ile raw_value uyuşmuyor")

    def test_tablo_yoksa_hic_alan_uretilmez(self):
        self.assertEqual(extract_from_rate_table("kampanya metni, tablo yok"), [])

    def test_deger_dogru_araliga_cozulur(self):
        f = {x.field_name: x
             for x in extract_from_rate_table(TABLOLAR["paylasim_baslik"])}
        self.assertEqual(f["kar_payi_orani"].canonical_value,
                         {"min": 3.89, "max": 4.09})


if __name__ == "__main__":
    unittest.main()
