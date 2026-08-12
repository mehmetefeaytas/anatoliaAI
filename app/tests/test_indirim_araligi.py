"""İndirim oranı bir ARALIK olabilir: "%10 ila %50 arasında indirim".

İlgili: ../src/extraction/rules/extract.py (`extract_indirim_orani`)
        ./test_kar_payi_etiket_varyanti.py (aynı sınıftan tutarsızlık)

## Bu testlerin varlık sebebi — ÖLÇÜLDÜ (2026-08-12, gold.v2)

`indirim_orani` F1 0,000 idi. Gold'da alan yalnız **2 kayıtta** dolu ve
birinde aralık isteniyor:

    Hayat Finans GastroClub
      metin  "...kategorilerinde %10 ila %50 arasında indirimlerden..."
      gold   {"min": 10.0, "max": 50.0}
      önce   10.0            <- kampanyanın en iyi tarafı sessizce düşüyordu

`extract_kar_payi` "ile|ila"yı zaten aralık ayırıcı sayıyordu; bu desen o
taramadan atlanmıştı. Aynı sınıftan tutarsızlık `_KAR_PAYI_ETIKET`'te de
vardı (8003bae).

## Neden bozuk aralık tek değere düşer

"%50 ile %10 arasında" gibi ters yazımda `{min: 50, max: 10}` üretmek kıyas
tablosuna ters bir aralık yazardı. Üst sınır alttan küçükse aralık kurulmaz,
tek değere düşülür — uydurma yerine eldeki kanıt.

## Kapsam dışı kalan kaçırma

Gold'un ikinci kaydı (Vakıf Katılım TROY) kural katmanıyla ÇÖZÜLEMEZ:
başlık "TROY Kredi Kartı ile %50'si Bizden!" diyor ve "indirim" sözcüğü
hiç geçmiyor; anotatör anlamdan çıkarmış. Kural katmanı tetikleyicisiz
değer üretmemelidir (aynı disiplin: `extract_vade` tetikleyici şartı,
975af3c). Bu vaka LLM katmanının işidir.

## Ölçülen sonuç

    indirim_orani F1  0,000 -> 0,400
"""

from __future__ import annotations

import unittest

from src.extraction.rules.extract import extract_indirim_orani


def _deger(metin: str):
    f = extract_indirim_orani(metin)
    return f.canonical_value if f else None


class TestAralik(unittest.TestCase):

    def test_ila_araligi_yakalanir(self):
        self.assertEqual(
            _deger("kategorilerinde %10 ila %50 arasında indirimlerden "
                   "faydalanın"),
            {"min": 10.0, "max": 50.0})

    def test_ayiricilar(self):
        for ayirac in ("ila", "ile", "-", "–"):
            with self.subTest(ayirac=ayirac):
                self.assertEqual(
                    _deger(f"%10 {ayirac} %50 arasında indirim"),
                    {"min": 10.0, "max": 50.0})

    def test_bozuk_aralik_tek_degere_duser(self):
        """Üst sınır alttan küçükse aralık KURULMAZ."""
        self.assertEqual(_deger("%50 ile %10 arasında indirim"), 50.0)


class TestTekDegerBozulmadi(unittest.TestCase):
    """Aralık desteği eklendi diye tek değerli yollar düşmemeli."""

    ORNEKLER = {
        "değer önce": ("%20 indirim fırsatı", 20.0),
        "etiket önce": ("indirim oranı %15", 15.0),
        "varan kalıbı": ("%25'e varan indirim", 25.0),
    }

    def test_tek_deger(self):
        for ad, (metin, beklenen) in self.ORNEKLER.items():
            with self.subTest(vaka=ad):
                self.assertEqual(_deger(metin), beklenen)

    def test_puan_kapisi_korundu(self):
        # "%5 puan iadesi" bir indirim değil `alisveris_puani`'dır.
        self.assertIsNone(_deger("%5 puan iadesi indirim"))


if __name__ == "__main__":                                # pragma: no cover
    unittest.main()
