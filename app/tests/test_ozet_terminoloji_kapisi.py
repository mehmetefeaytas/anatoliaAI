"""Özet terminoloji kapısı — konvansiyonel banka terimi ekrana BASILMAZ.

İlgili: ../src/summarize/ozet.py (`_terminoloji_ihlali`, `SEBEP_TERMINOLOJI`)
        CLAUDE.md §12 (katılım bankacılığı terminolojisi %30'un kalbi)

## Bu kapı niçin var — ölçülmüş asimetri

`SISTEM_PROMPT` iki kural koyuyor: (1) yalnız Türk alfabesi, (2) konvansiyonel
bankacılık terimi kullanma. Birincinin bir KAPISI vardı (`turkce_alfabede_mi`),
ikincinin yoktu. İstemin kendi yorumu bu boşluğu adlandırıyordu:
"Yönergedeki bu cümle KAPININ YERİNE GEÇMEZ, onu tamamlar."

Ölçüldü (2026-08-20, `data/demo.db`, 2.455 özet): 25 özet "kapitalizm
bankacılığı" / "faiz bankacılığı" diyordu, 9'u bankayı "Kâr Payı Bankası X"
diye adlandırıyordu, 7'sinde çıplak "faiz" geçiyordu — hepsi kullanıcıya
"AI Özeti" etiketiyle gösteriliyordu.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

KOK = Path(__file__).resolve().parents[1]
if str(KOK) not in sys.path:
    sys.path.insert(0, str(KOK))

from src.summarize.ozet import (
    SEBEP_TERMINOLOJI,
    _terminoloji_ihlali,
)


class TestKapiIhlaliYAKALIYOR(unittest.TestCase):
    """KAPI 1 — gerçek korpustan ölçülmüş ihlaller reddedilmeli."""

    def test_kapitalizm_bankaciligi(self):
        self.assertEqual(
            "kapitalizm bankacılığı",
            _terminoloji_ihlali(
                "Kapitalizm bankacılığı tarafından sunulan konut finansmanı "
                "hakkında bilgi veren belge."))

    def test_kar_payi_bankasi_adlandirmasi(self):
        self.assertEqual(
            "kâr payı bankası",
            _terminoloji_ihlali(
                "Bu anlaşma, Kâr Payı Bankası Kuveyt Türk Katılım Bankası ile "
                "Rehin Verenler arasında düzenlenmiştir."))

    def test_ciplak_faiz(self):
        self.assertEqual("faiz", _terminoloji_ihlali(
            "Bu kampanyada faiz oranı yüzde 2 olarak uygulanır."))

    def test_faiz_bankaciligi(self):
        self.assertEqual("faiz bankacılığı", _terminoloji_ihlali(
            "Faiz bankacılığı ürünlerine benzer bir yapı sunulmaktadır."))


class TestKapiMESRU_KULLANIMA_DOKUNMUYOR(unittest.TestCase):
    """KAPI 2 — karşı-örnekler. Kapı gerçek özetleri düşürmemeli.

    Bu sınıf olmadan kapı sessizce her şeyi eleyebilir ve "0 ihlal" raporu
    kapının çalıştığı sanılır — oysa kapsam çökmüş olur.
    """

    MESRU = (
        "Katılım bankası faizsiz finansman sunar.",
        "Faiz dışı gelirler bu dönemde artmıştır.",
        "Kuveyt Türk konut finansmanı kâr payı oranı %1,89, vade 120 ay.",
        "Kampanya kapsamında dosya masrafı alınmamaktadır.",
        "Katılma hesabı kâr ve zarara ortaklık esasına dayanır.",
        "Murabaha yöntemiyle taşıt finansmanı sağlanır.",
        "Tahsis ücreti 500 TL olarak belirlenmiştir.",
    )

    def test_mesru_ozetler_gecer(self):
        for ozet in self.MESRU:
            with self.subTest(ozet=ozet[:40]):
                self.assertIsNone(_terminoloji_ihlali(ozet))

    def test_faizsiz_ozel_olarak_muaf(self):
        """`faizsiz` katılım bankacılığının KENDİ terimidir."""
        self.assertIsNone(_terminoloji_ihlali("Tamamen faizsiz bir üründür."))

    def test_faiz_disi_muaf(self):
        self.assertIsNone(_terminoloji_ihlali("Faiz dışı denge iyileşti."))


class TestSebepKoduYAYIMLANIYOR(unittest.TestCase):
    """KAPI 3 — düşen özetin sebebi sayılabilir olmalı.

    Kapı sessiz düşmemeli: toplu raporlar "kaç özet terminolojiden düştü"
    sorusunu cevaplayabilsin. Alfabe kapısında bu zaten böyleydi.
    """

    def test_sebep_kodu_tanimli(self):
        self.assertEqual("terminoloji_ihlali", SEBEP_TERMINOLOJI)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
