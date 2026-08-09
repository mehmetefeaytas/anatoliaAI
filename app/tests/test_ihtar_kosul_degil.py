"""Genel yasal ihtar `kampanya_kosullari` DEĞİLDİR — üreten tarafta da.

İlgili: src/extraction/rules/ihtar.py (tek doğruluk kaynağı)
        src/extraction/rules/extract.py (`extract_kampanya_kosullari`)
        scripts/kalibrasyon_hakemlik.py (`kosul-ihtar` kuralı)

## Bu testin varlık sebebi

Kural önce YALNIZ anotasyon tarafında uygulandı (18 hücre temizlendi), çıkarıcı
ise cümleyi üretmeye devam etti. Ölçüldü (2026-08-09): 20 kalibrasyon
belgesinin **5'inde** model değeri ihtar cümlesi taşıyor, gold taşımıyordu —
model o satırlarda YAPAY olarak yanlış görünüyordu. `data/demo.db` genelinde
aynı sızıntı 1774 belgenin **248'indeydi**.

Asıl risk desenin iki kopya hâlinde yaşaması: bir taraf güncellenir, öteki
kalır ve hata sessizce geri gelir. `test_desen_tek_kaynak` tam olarak bunu
kapıda tutar.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.extraction.rules.extract import extract_kampanya_kosullari
from src.extraction.rules.ihtar import IHTAR_RE, ihtar_ayikla, ihtar_mi

# Gerçek korpustan alınmış ihtar varyantları (her kampanyada birebir tekrarlanır).
IHTARLAR = (
    "Bankamız uygun görmediği başvuruları reddetme, kampanya koşullarını "
    "değiştirme, kampanyayı durdurma hakkını saklı tutar",
    "Banka kampanya şartlarında değişiklik yapma ve/veya kampanyayı durdurma "
    "yetkisine sahiptir",
    "Bu metin yalnızca bilgilendirme amaçlıdır",
)

GERCEK_KOSUL = ("Kampanyadan yararlanmak için asgari 3 işlem yapılması "
                "gerekmektedir")


class DesenTanir(unittest.TestCase):

    def test_ihtar_varyantlari_taninir(self) -> None:
        for c in IHTARLAR:
            with self.subTest(c=c[:40]):
                self.assertTrue(ihtar_mi(c))

    def test_gercek_kosul_ihtar_sayilmaz(self) -> None:
        self.assertFalse(ihtar_mi(GERCEK_KOSUL))

    def test_ayiklama_sirayi_korur(self) -> None:
        self.assertEqual(
            ihtar_ayikla([GERCEK_KOSUL, IHTARLAR[0], "Yalnızca yeni müşteriler"]),
            [GERCEK_KOSUL, "Yalnızca yeni müşteriler"])


class CikariciUretmez(unittest.TestCase):

    def test_sadece_ihtar_varsa_alan_uretilmez(self) -> None:
        """Geriye koşul kalmıyorsa alan HİÇ üretilmez — boş liste yazılmaz."""
        for c in IHTARLAR:
            with self.subTest(c=c[:40]):
                metin = (f"Kâr payı oranı %1,89. {c}. "
                         "Kampanya 31.12.2026 tarihine kadar geçerlidir.")
                self.assertIsNone(extract_kampanya_kosullari(metin))

    def test_gercek_kosul_ihtarla_birlikte_gelirse_korunur(self) -> None:
        metin = (f"{GERCEK_KOSUL}. {IHTARLAR[0]}. "
                 "Kampanya 31.12.2026 tarihine kadar geçerlidir.")
        f = extract_kampanya_kosullari(metin)
        self.assertIsNotNone(f)
        self.assertTrue(any("asgari" in s for s in f.canonical_value))
        for s in f.canonical_value:
            self.assertFalse(ihtar_mi(s), f"ihtar koşul sayıldı: {s}")

    def test_ihtar_dipnot_olarak_gelirse_de_elenir(self) -> None:
        """Dipnot yolu (`extract_dipnotlar`) da aynı süzgeçten geçer."""
        metin = ("Kampanyaya katılabilirsiniz. "
                 "*Banka kampanya şartlarında değişiklik yapma ve/veya "
                 "kampanyayı durdurma hakkını saklı tutar")
        self.assertIsNone(extract_kampanya_kosullari(metin))


class TekKaynak(unittest.TestCase):
    """Desen iki yerde YAŞAYAMAZ; kopyalar zamanla ayrışır ve hata geri gelir."""

    def test_desen_tek_kaynak(self) -> None:
        from scripts.kalibrasyon_hakemlik import _IHTAR

        self.assertEqual(
            _IHTAR.pattern, IHTAR_RE.pattern,
            "Anotasyon (`kalibrasyon_hakemlik._IHTAR`) ve çıkarım "
            "(`ihtar.IHTAR_RE`) desenleri AYRIŞTI. Tek kaynak "
            "src/extraction/rules/ihtar.py'dir; hakemlik betiği oradan "
            "import etmelidir.")


if __name__ == "__main__":
    unittest.main()
