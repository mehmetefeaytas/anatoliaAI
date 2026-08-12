"""Masraf TUTARI için açık para birimi şart — madde numarası tutar değildir.

İlgili: ../src/normalization/normalize.py (`normalize_fee_status`),
        ../src/extraction/rules/extract.py (`extract_tahsis_ucreti` — kardeş
        alanda bu kapı ZATEN vardı: "AÇIK PARA BİRİMİ ŞART")

## Bu testlerin varlık sebebi — ÖLÇÜLDÜ (2026-08-12, `data/raw`, 1.780 belge)

`normalize_fee_status` tutarı `normalize_money(text)` ile alıyordu ve o
fonksiyon pencerede bulduğu ÇIPLAK sayıyı TL sayıyor. Korpusta
`masraf_durumu` pozitif tutar üreten 30 belge tarandı:

    span'da açık para birimi VAR : 16   (meşru)
    span'da açık para birimi YOK : 14   (14'ünün 14'ü sayı DEĞİL, kod/tarih/vade)

Ondördünün tamamı parasal olmayan sayılardı:

    "Yönetici Ortağın Ücreti Madde 23-"                 -> 23,00 TL  (madde no)
    "masraflarınızı 12 aya kadar taksitlendirerek"      -> 12,00 TL  (vade)
    "ÜCRETLERİN GEÇERLİLİK SÜRESİ: 31 Aralık"           -> 31,00 TL  (tarih)
    "4784 Otoyol ve Köprü Ücretleri 4789 NAKLİYAT"      -> 4.789,00 TL (MCC kodu)
    "...başlıklı 17. maddede"                           -> 17,00 TL  (madde no)
    "değişiklikleri 30 gün önce"                        -> 30,00 TL  (ihbar süresi)
    "Tahsis edilen limit 3 ay içerisinde"               ->  3,00 TL  (vade)

Alan bileşik avantaj skorunda 0,20 ağırlıkla kullanılıyor
(`comparison/compare.py:697`), yani "23 TL masraf" gibi bir değer ekranda
neredeyse masrafsız okunuyordu.

## Neden gold bunu göstermiyor

Gold'un 48 kaydında `masraf_durumu` için POZİTİF tutar HİÇ yok: beş kayıt
`{has_fee: False, amount: 0.0}`, bir kayıt `{has_fee: True, amount: None}`.
Yani bu kusur gold metriğinde görünmez ve kapı hiçbir gold TP'sini
düşüremez — kazanç korpus/ürün düzeyindedir.

## Korpus düzeyinde ölçülen TAKAS (before/after, 1.780 belge)

Kapı körlemesine kazanç değil, ölçülmüş bir takastır:

    uydurma tutar elendi ([True, X] -> alan yok)     : 20 belge
    bozuk tutar None'a düştü (has_fee KORUNDU)       : 15 belge
    GERÇEK tutar None'a düştü                        :  1 belge

Tek gerçek kayıp: `albaraka/products/konut-finansmani` belgesinde "Ücretler
Toplamı 28.076,27" — tutar gerçek ama yanında para birimi işareti YOK.
Sonuç `{has_fee: True, amount: None}` oldu, yani "ücret vardır, tutarını
iddia etmiyoruz". Bu, projenin kendi doktrininin öngördüğü dürüst
başarısızlık biçimidir (CLAUDE.md §19: bilgi yoksa `null`, uydurma yok) —
28.076,27'yi tutmak için 20 uydurma tutarı kabul etmek gerekirdi.

Ayrıca o belge bir HESAPLAMA (calculator) sayfasıdır ("Aylık Taksit Tutarı",
"Ödeme Planı", "Hemen Başvur"): sayı, ilan edilmiş bir kampanya ücreti değil,
varsayımsal bir finansman için widget çıktısıdır — `ASGARI_GUVEN` kapısının
`finansman_tutari`'nda zaten dışladığı artefakt sınıfı.

## Kardeş alanda kapı zaten vardı

`extract_tahsis_ucreti` aynı tuzağı yaşamış ve çözmüş; kodda yorumu duruyor
("AÇIK PARA BİRİMİ ŞART"). `masraf_durumu` o taramadan atlanmıştı — Faz 1'in
tespit ettiği "aynı kavramı ölçen iki desen ayrışmış" sınıfının bir örneği.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.normalization.normalize import normalize_fee_status


class CiplakSayiTutarDEGIL(unittest.TestCase):
    """Para birimi işareti yoksa TL tutarı üretilmez."""

    KORPUS_VAKALARI = (
        "Yönetici Ortağın Ücreti Madde 23-",
        "ÜCRETLERİN GEÇERLİLİK SÜRESİ: 31 Aralık",
        "4784 Otoyol ve Köprü Ücretleri 4789 NAKLİYAT SERVİSLERİ",
        "ücret, komisyon ve masraflarda meydana gelecek değişiklikleri 30",
    )

    def test_parasal_olmayan_sayi_tutar_olmaz(self) -> None:
        for metin in self.KORPUS_VAKALARI:
            with self.subTest(metin=metin):
                sonuc = normalize_fee_status(metin)
                tutar = None if sonuc is None else sonuc.get("amount")
                self.assertIsNone(
                    tutar,
                    f"parasal olmayan sayı TL tutarı sanıldı: {metin!r} "
                    f"-> {tutar!r}")


class ACIKPARABIRIMIVarsaTutarURETILIR(unittest.TestCase):
    """Kapı meşru tutarı ELEMEZ — kazancın ön koşulu."""

    def test_TL_isareti_olan_tutar_okunur(self) -> None:
        for metin, beklenen in (
            ("tahsis ücreti 500 TL", 500.0),
            ("dosya masrafı 1.500,00 TL", 1500.0),
            ("Tahsis Ücreti 30.000,00 ₺ 12 Ay 1,69%", 30000.0),
        ):
            with self.subTest(metin=metin):
                sonuc = normalize_fee_status(metin)
                self.assertIsNotNone(sonuc, f"tutar kayboldu: {metin!r}")
                self.assertIs(sonuc["has_fee"], True)
                self.assertEqual(sonuc["amount"], beklenen)


class DIGERYOLLARBOZULMADI(unittest.TestCase):
    """Negasyon, oran ve tahsil fiili yolları etkilenmedi."""

    def test_negasyon_hala_sifir(self) -> None:
        for metin in ("masrafsız", "ücret alınmaz", "ücret alınmamaktadır"):
            with self.subTest(metin=metin):
                s = normalize_fee_status(metin)
                self.assertIsNotNone(s)
                self.assertIs(s["has_fee"], False)
                self.assertEqual(s["amount"], 0.0)

    def test_oran_hala_tutarsiz_pozitif(self) -> None:
        s = normalize_fee_status("tahsis ücreti %0,5")
        self.assertIsNotNone(s)
        self.assertIs(s["has_fee"], True)
        self.assertIsNone(s["amount"])

    def test_tahsil_fiili_hala_pozitif(self) -> None:
        """Tutar bilinmiyor ama ücret ALINDIĞI yazıyor — bilgi kaybı olmasın."""
        s = normalize_fee_status("hesap işletim ücreti tahsil edilir")
        self.assertIsNotNone(s, "tahsil fiili yolu kayboldu")
        self.assertIs(s["has_fee"], True)
        self.assertIsNone(s["amount"])

    def test_ciplak_isim_hala_bilgi_yok(self) -> None:
        self.assertIsNone(normalize_fee_status("Ücret Tarifesi"))


if __name__ == "__main__":
    unittest.main()
