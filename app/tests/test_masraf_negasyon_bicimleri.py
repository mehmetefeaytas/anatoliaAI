"""Masraf negasyonu: `-mAmAktAdIr` biçimi de negasyondur.

İlgili: ../src/normalization/normalize.py (`NEGATION_RE`, `normalize_fee_status`),
        ../src/extraction/rules/extract.py (`extract_tahsis_ucreti` ikinci tüketici),
        ./test_masraf_alan_disi.py (kardeş kapı — KESİNLİK tarafı)

## Bu testlerin varlık sebebi — ÖLÇÜLDÜ (2026-08-12)

`data/gold/ANNOTATION_GUIDE.md`'nin `masraf_durumu` bölümü "**NEGASYON
KRİTİK**" başlığı altında negasyonun bilgi eksikliği OLMADIĞINI söylüyor:
masraf sıfırdır, `absent` yazılmaz. `NEGATION_RE` bu sözleşmeyi Türkçenin
`-mAz` ve `-mIyor` biçimleri için tutuyordu:

    "ücret alınmaz"        -> {'has_fee': False, 'amount': 0.0}   ✓
    "ücret alınmıyor"      -> {'has_fee': False, 'amount': 0.0}   ✓

Ama resmî bankacılık metninin baskın biçimi olan **`-mAmAktAdIr`** desende
YOKTU; yalnız tek bir fiil (`bulunmamaktadır`) elle listelenmişti:

    "hesap işletim ücreti alınmamaktadır"     -> None   ✗
    "dosya masrafı tahsil edilmemektedir"     -> None   ✗
    "komisyon ücreti yansıtılmamaktadır"      -> None   ✗

Üçü de metinde AÇIKÇA "masraf sıfır" diyor ve sessizce düşüyordu.

## Kapsam — korpusta ölçüldü, gold'a göre değil

1.780 belgelik ham korpusta, masraf/ücret ismiyle aynı cümlede
`-mAmAktAdIr` taşıyan **35 belge** var. Örnekler:

    "İşlem ücreti alınmamaktadır."
    "Bankamızda hiçbir hesaptan Hesap İşletim Ücreti alınmamaktadır."
    "Sağlam Business Finansman sahiplerinden herhangi bir kart ücreti
     alınmamaktadır."

## DÜRÜSTLÜK NOTU — bu düzeltme gold metriğini HAREKET ETTİRMEZ

Ölçüldü (aday desen gold'da kuru koşturuldu): `masraf_durumu` uydurma 2 -> 2,
TP 6 -> 6; `tahsis_ucreti` 0 -> 0. 48 kayıtlık gold bu biçimi ilgili span'da
içermiyor. Yani kazanç **ürün düzeyinde** (35 belgenin masraf durumu artık
doğru okunuyor, bileşik sıralamaya ve çelişki tespitine doğru veri gidiyor),
**metrik düzeyinde değil**. Metriği hareket ettirmediği için değersiz demek
yanlış olurdu; gold'un 48 kayıtla korpusun tamamını temsil etmediğini
söylemek doğru olur.

## Neden fiil-çapalı, neden `\\w*mamaktadır` değil

Genel sonek deseni `tahsis_ucreti` yolunda da tüketiliyor
(`extract.py:1126`) ve orada tetikleyiciden sonraki 60 karakterlik
cümlecikte eşleşen HERHANGİ bir `-mAmAktAdIr` fiili ücreti sıfır yapardı
("... ile birlikte kullanılmamaktadır" gibi ilgisiz bir yüklem dâhil).
Mevcut desen de fiilleri tek tek sayıyor; aynı özgüllük korundu.
"""

from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.normalization.normalize import NEGATION_RE, normalize_fee_status


class MAmAktAdIrBicimiNegasyondur(unittest.TestCase):
    """Resmî bankacılık negasyonu da masrafı SIFIR yapar."""

    KORPUS_BICIMLERI = (
        "hesap işletim ücreti alınmamaktadır",
        "dosya masrafı tahsil edilmemektedir",
        "komisyon ücreti yansıtılmamaktadır",
        "İşlem ücreti alınmamaktadır",
        "herhangi bir kart ücreti alınmamaktadır",
    )

    def test_korpus_bicimleri_sifir_masraf_verir(self) -> None:
        for metin in self.KORPUS_BICIMLERI:
            with self.subTest(metin=metin):
                sonuc = normalize_fee_status(metin)
                self.assertIsNotNone(
                    sonuc, f"negasyon tanınmadı, sessizce düştü: {metin!r}")
                self.assertIs(
                    sonuc["has_fee"], False,
                    f"negasyon 'masraf var' diye okundu: {metin!r}")
                self.assertEqual(sonuc["amount"], 0.0)

    def test_ONCEDEN_CALISAN_bicimler_GERILEMEDI(self) -> None:
        """`-mAz` / `-mIyor` / sıfat biçimleri bozulmadı."""
        for metin in ("masrafsız", "ücretsiz", "ücret alınmaz",
                      "masraf yoktur", "ücret alınmıyor",
                      "ücret tahsil edilmez", "masraf bulunmamaktadır"):
            with self.subTest(metin=metin):
                sonuc = normalize_fee_status(metin)
                self.assertIsNotNone(sonuc, f"gerileme: {metin!r}")
                self.assertIs(sonuc["has_fee"], False)


class DesenAsiriGENISLEMEDI(unittest.TestCase):
    """Fiil çapası korundu — ilgisiz yüklem ücreti sıfırlamaz."""

    def test_ilgisiz_mamaktadir_fiili_negasyon_SAYILMAZ(self) -> None:
        """`extract_tahsis_ucreti` bu deseni cümlecikte arıyor; geniş
        bir sonek deseni ilgisiz yüklemi negasyon sayardı."""
        for metin in ("kampanya diğer kampanyalarla birlikte "
                      "kullanılmamaktadır",
                      "şubelerimizde satılmamaktadır"):
            with self.subTest(metin=metin):
                self.assertIsNone(
                    re.search(NEGATION_RE, metin, re.IGNORECASE),
                    f"desen ilgisiz yüklemi negasyon saydı: {metin!r}")

    def test_ucret_ismi_YOKSA_hala_bilgi_yok(self) -> None:
        """Negasyon tek başına masraf iddiası değildir — kanıt gerekir."""
        self.assertIsNone(normalize_fee_status("alınmamaktadır"))
        self.assertIsNone(normalize_fee_status("tahsil edilmez"))


class PozitifUcretBOZULMADI(unittest.TestCase):
    """Negasyon genişlemesi 'ücret var' tarafını yemedi."""

    def test_tutarli_ucret_hala_pozitif(self) -> None:
        s = normalize_fee_status("tahsis ücreti 500 TL")
        self.assertIsNotNone(s)
        self.assertIs(s["has_fee"], True)
        self.assertEqual(s["amount"], 500.0)

    def test_oranli_ucret_hala_pozitif_tutar_uydurulmaz(self) -> None:
        s = normalize_fee_status("tahsis ücreti %0,5")
        self.assertIsNotNone(s)
        self.assertIs(s["has_fee"], True)
        self.assertIsNone(s["amount"], "oran TL tutarına çevrilmiş")

    def test_ciplak_isim_hala_KANIT_DEGIL(self) -> None:
        self.assertIsNone(normalize_fee_status("Ücret Tarifesi"))


if __name__ == "__main__":
    unittest.main()
