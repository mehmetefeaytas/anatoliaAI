"""Oransal tahsis ücreti — TABAN ADLA ANILIYORSA hesap YOK.

İlgili: ../src/extraction/rules/extract.py (`_ucret_degeri`, `_ADLA_TABAN_RE`)
        ../data/gold/ANNOTATION_GUIDE.md §4.13/5
        ../tests/test_tahsis_yuzde_hesap.py (bu kuralın ÖNCEKİ hâli)

## Ölçülmüş gerekçe — ve bir çelişkinin çözümü

`_ADLA_TABAN_RE` yolu 2026-08-07'de bilerek eklendi: mentörlük bulgusu
"yüzdeli ifadelerde hesaplama yapmıyor" idi ve o gün ölçülen alternatif
(oranı `{"rate": X}` yazmak) gold F1'ini 0,400'den 0,333'e düşürmüştü.

Kılavuz §4.13/5 iki gün SONRA (2026-08-09) tersini yazdı:

    "Hesaplamayın. Finansman tutarı aynı belgede geçse bile çarpmak
     çıkarım değil TÜRETMEDİR."
    `tahsis_ucreti` -> `unclear` + `#oransal_ucret`
    `masraf_durumu` -> `{"has_fee": true, "amount": null}`

2026-08-15 ölçümü kılavuzu haklı çıkardı. 436 inceleme belgesinde altı belge,
metinde HİÇ GEÇMEYEN bir TL değeri üretiyordu:

    50 TL   =  10.000 TL × %0,50   (kuveyt-turk bireysel finansman formu)
    625 TL  = 125.000 TL × %0,50   (turkiye-finans, dört belge)

`turkiye-finans--ihtiyac-finansmani` vakası kararı tek başına veriyor:
"Tahsis ücreti vergiler hariç finansman tutarının %0,50'si" cümlesi,
belgenin BAŞKA bir yerindeki 125.000 TL ile çarpılıyordu. Oysa o sayı
finansman tutarı bile değil, bir VADE EŞİĞİ:

    "...125.000 TL'ye kadar olması durumunda 24 ayı, 250.000 TL'den fazla
     olması durumunda 12 ayı aşamaz."

Yani yanlış tabanla yapılmış bir hesap — çifte uydurma, CLAUDE.md §19 ihlali.

## Bedeli ölçüldü: SIFIR

    gold.v2 (strict)   mikro-F1 0,452 · makro 0,556 · yapısal 0,646 ·
                       halüsinasyon 0,059     -> hepsi DEĞİŞMEDİ
    gold.v1 (strict)   tahsis_ucreti F1 0,667 -> DEĞİŞMEDİ (o TP metinde
                       birebir yazılı bir tutardan geliyor, hesaptan değil)

Yani 2026-08-07 ölçümünün korumaya çalıştığı TP bu yoldan gelmiyordu.

## Bitişik taban KALIR

"100.000 TL'nin %2,5'i" ifadesinde her iki işlenen de aynı cümlededir;
sonuç belirsiz değildir ve kılavuzun yasakladığı "belgenin başka yerinden
taban devşirme" durumu yoktur.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.extraction.rules.extract import extract_all, extract_tahsis_ucreti


def _tahsis(alanlar):
    for f in alanlar:
        if f.field_name == "tahsis_ucreti":
            return f
    return None


class AdlaAnilanTabanHesaplanmaz(unittest.TestCase):
    def test_finansman_tutarinin_yuzdesi_DEGER_URETMEZ(self) -> None:
        """Kılavuz §4.13/5'in birebir vakası."""
        metin = ("Kredi Tutarı 125.000 TL. Tahsis ücreti vergiler hariç "
                 "finansman tutarının %0,50'si olarak alınır.")
        self.assertIsNone(_tahsis(extract_all(metin)),
                          "taban adla anılıyor; çarpım TÜRETMEDİR")

    def test_binde_ifadesi_de_URETMEZ(self) -> None:
        metin = ("Finansman tutarı 200.000 TL'dir. Tahsis ücreti finansman "
                 "tutarının binde 5'i kadardır.")
        self.assertIsNone(_tahsis(extract_all(metin)))

    def test_YANLIS_TABAN_vakasi_artik_deger_uretmiyor(self) -> None:
        """Ölçülmüş en kötü vaka: taban bir VADE EŞİĞİYDİ, tutar değil.

        Bu metin 625 TL üretiyordu ve 625 sayısı metinde hiç geçmiyor.
        """
        metin = ("Kullandırılacak finansman tutarının 125.000 TL'ye kadar "
                 "olması durumunda vade 24 ayı aşamaz. Tahsis ücreti vergiler "
                 "hariç finansman tutarının %0,50'si kadardır.")
        alan = _tahsis(extract_all(metin))
        self.assertIsNone(alan, f"uydurma değer geri geldi: "
                                f"{alan.canonical_value if alan else None}")
        self.assertNotIn("625", metin, "test metni bozulmuş — 625 metinde olmamalı")


class BitisikTabanKORUNUR(unittest.TestCase):
    """NEGATİF TUZAK: bu yol kaldırılırsa meşru bir hesap kaybolur."""

    def test_bitisik_taban_HESAPLANMAYA_devam_eder(self) -> None:
        alan = _tahsis(extract_all("Tahsis ücreti 100.000 TL'nin %2,5'i kadardır."))
        self.assertIsNotNone(alan, "bitişik taban meşrudur, kaldırılamaz")
        self.assertEqual(alan.canonical_value, {"value": 2500.0, "currency": "TRY"})

    def test_bitisik_taban_uzerinden_kalibi(self) -> None:
        alan = _tahsis(extract_all(
            "Tahsis ücreti, 100.000 TL üzerinden %1 olarak alınır."))
        self.assertIsNotNone(alan)
        self.assertEqual(alan.canonical_value, {"value": 1000.0, "currency": "TRY"})

    def test_duz_TL_tutari_etkilenmez(self) -> None:
        alan = extract_tahsis_ucreti("Tahsis ücreti 500 TL'dir.")
        self.assertIsNotNone(alan)
        self.assertEqual(alan.canonical_value, {"value": 500.0, "currency": "TRY"})


class KorpusDegismezi(unittest.TestCase):
    """İnceleme korpusunda metinde geçmeyen TL değeri KALMAMALI."""

    def test_hicbir_belge_hesaplanmis_tahsis_ucreti_uretmiyor(self) -> None:
        kok = Path(__file__).resolve().parents[1] / "data/gold/review/belgeler"
        if not kok.is_dir():
            self.skipTest("inceleme belgeleri yok")
        hesapli = []
        for yol in sorted(kok.glob("*.txt")):
            alan = _tahsis(extract_all(yol.read_text(encoding="utf-8")))
            if alan and "[hesap:" in (alan.source_span or ""):
                hesapli.append(yol.stem)
        self.assertEqual(hesapli, [],
                         f"metinde geçmeyen tutar üreten belgeler: {hesapli[:5]}")


if __name__ == "__main__":
    unittest.main()
