"""Ödül, finansman değildir — ve bağlaç yasağı NİÇİN reddedildi.

İlgili: ../src/extraction/rules/tutar.py (`_ODUL_SAGI_RE`)
        ../data/gold/review/_hakem-turu-05-finansman-tutari-round1.md §4.5

## Ölçülen hata (HAKEM-05'in bulduğu tek gerçek MODEL hatası)

`turkiye-finans--kampanyalar-yakininizi-davet-edin`: *"%0 kâr paylı 50.000
TL'ye varan İhtiyaç Finansmanı **ve 11.000 TL'ye varan bonus** fırsatından
yararlanmalarını sağlayın."* → `finansman_tutari = 11.000 TL`.

11.000 TL bir **bonustur**; kılavuz onu `odul_miktari`ya yazar. Gold'un
hücreyi boş bırakması doğru okumaydı — 23 sapmanın 22'sinde gold yanlıştı,
bu birinde MODEL yanlıştı ve o da kapatıldı.

## Bu dosya ikinci bir şeyi de korur: REDDEDİLEN öneri

HAKEM-05 iki düzeltme önerdi. Birincisi (tetikleyici ile tutar arasındaki
boşlukta `ve|ile|ayrıca` yasağı) **ölçülüp reddedildi**: canlı korpusta
`finansman_tutari` taşıyan 78 alanın 21'ini düşürüyordu ve düşürdükleri
meşruydu — *"ödeme seçeneği **ile** 200.000 TL'ye kadar"* tam olarak S1
kılavuz kararıyla (anotatör, 2026-08-21) doldurulan dört hücrenin kaynağı.
Yasak konsa o kararı geri almış olurduk.

Aşağıdaki `MESRU_*` vakaları o reddi teste bağlıyor: biri bir gün bağlaç
yasağını yeniden eklemeye kalkarsa bu testler kırılır ve gerekçeyi okur.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.extraction.rules.extract import extract_all

#: Ödül olduğu için DÜŞMESİ gereken tutarlar (canlı korpustan, 2/78).
ODUL_VAKALARI = (
    ("bonus", "Yeni müşterilere sunulan %0 kâr paylı 50.000 TL'ye varan "
              "İhtiyaç Finansmanı ve 11.000 TL'ye varan bonus fırsatından "
              "yararlanmalarını sağlayın."),
    ("altın puan", "Konut finansmanı ile 1.000 TL değerinde Altın Puan "
                   "kazanabilirsiniz."),
    ("iade", "Taşıt finansmanı kampanyasında 2.500 TL iade kazanın."),
    ("hediye", "İhtiyaç finansmanı başvurusuna 750 TL hediye çeki."),
)

#: BAĞLAÇ TAŞIYAN ama MEŞRU tutarlar — bağlaç yasağının kurbanları olurdu.
MESRU_BAGLACLI = (
    ("ile / S1 kararı",
     "Alışveriş Finansmanı ödeme seçeneği ile 200.000 TL'ye kadar olan "
     "alışverişlerinizde vade farksız taksit.", 200000.0),
    ("ile / mağaza",
     "Alışveriş finansmanı ile Hepsiburada'da 30.000 TL'ye kadar "
     "harcamalarınızı taksitlendirin.", 30000.0),
)

#: Ödül sözcüğü GEÇMEYEN, düz tavan ifadeleri — dokunulmamalı.
MESRU_TAVAN = (
    ("azami tutar",
     "Konut finansmanında azami finansman tutarı 1.250.000 TL olarak "
     "uygulanır.", 1250000.0),
    ("kadar",
     "50.000 TL'ye kadar vade farksız ihtiyaç finansmanı imkânı.", 50000.0),
)


def _tutar(metin):
    return [f.canonical_value for f in extract_all(metin)
            if f.field_name == "finansman_tutari"]


class TestOdulDusuruluyor(unittest.TestCase):
    def test_odul_adi_tasiyan_tutar_finansman_sayilmaz(self) -> None:
        for ad, metin in ODUL_VAKALARI:
            with self.subTest(odul=ad):
                self.assertEqual(
                    _tutar(metin), [],
                    f"«{ad}» ödülü finansman tutarı olarak çıkarılıyor")


class TestBaglacYasagiReddedildi(unittest.TestCase):
    """Bağlaç yasağı ölçülüp reddedildi; bu testler reddi çitliyor."""

    def test_baglacli_mesru_tutar_korunur(self) -> None:
        for ad, metin, beklenen in MESRU_BAGLACLI:
            with self.subTest(vaka=ad):
                bulunan = _tutar(metin)
                self.assertTrue(
                    bulunan,
                    "bağlaç yasağı geri gelmiş: meşru tutar düşüyor — "
                    "gerekçe tutar.py'deki «BAĞLAÇ YASAĞI DENENDİ VE "
                    "ÖLÇÜMLE REDDEDİLDİ» notunda")
                self.assertEqual(bulunan[0]["value"], beklenen)

    def test_duz_tavan_ifadeleri_korunur(self) -> None:
        for ad, metin, beklenen in MESRU_TAVAN:
            with self.subTest(vaka=ad):
                bulunan = _tutar(metin)
                self.assertTrue(bulunan, ad)
                self.assertEqual(bulunan[0]["value"], beklenen)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
