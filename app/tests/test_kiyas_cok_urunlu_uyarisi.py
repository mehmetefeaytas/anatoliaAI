"""Çok ürünlü belgeden gelen kıyas satırı İŞARETLENİR.

İlgili: ../src/chatbot/structured.py (`_cok_urunlu_mu`, `_cok_urunlu_uyarisi`)
        decisions/urun-baglami-alan-duzeyinde-tasinmali.md

## Ölçülmüş hata

Kullanıcı raporu (2026-08-24): konut finansmanı kıyasında *"Ek ödül: Kuveyt
Türk 200 TL"* satırı çıktı. O 200 TL aslında **"her bir fatura talimatı için
200 TL iade"** — belge `#761` bir akademisyen paketi ve konut, kart, fatura
avantajlarını BİRLİKTE içeriyor. Belgeye tek ürün ailesi atanıyor ve o
belgeden çıkarılan tüm alanlar o aileye ait sayılıyor.

## Neden İŞARET, neden DIŞLAMA değil

`#761` gerçekten konut finansmanına değiniyor (*"Konut Finansmanı'nda
tanımlanmış 5 puan indirim"*), yani belgeyi kıyastan atmak bilgi kaybıdır.
Doğru davranış, alan atamasının belirsiz olduğunu SÖYLEMEK — bu modülün
kuralı zaten şu: kıyaslanamayan/belirsiz boyut sessizce geçmez.

## Ölçülen kapsam SINIRI

Kural tabanlı tespit (aile adı deseni sayımı) korpusta %9 çok ürünlü buluyor;
EVREN ile yapılan 45 belgelik denetim %18 diyor. Yani kural EVREN'in yarısını
yakalıyor — desen listesi 6 aile içeriyor, korpusta 8 aile var. Bu bir
BAŞLANGIÇ, tam çözüm değil ve sınırı burada yazılı.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.chatbot.structured import _cok_urunlu_mu, _cok_urunlu_uyarisi

KONUT = ("Konut finansmanı kampanyası. Konut finansmanında kâr payı oranı "
         "%1,89. Tahsis ücreti 750 TL.")
PAKET = ("Akademisyenlere Özel Avantaj Paketi. Konut Finansmanı Avantajları: "
         "Konut finansmanında 5 puan indirim. Kredi kartı ile her fatura "
         "talimatına 200 TL iade. Kredi kartı aidatı yok.")


class TespitTest(unittest.TestCase):

    def test_tek_urunlu_belge_isaretlenmez(self):
        self.assertFalse(_cok_urunlu_mu(KONUT))

    def test_cok_urunlu_paket_isaretlenir(self):
        self.assertTrue(_cok_urunlu_mu(PAKET))

    def test_bos_metin_patlamaz(self):
        self.assertFalse(_cok_urunlu_mu(""))
        self.assertFalse(_cok_urunlu_mu(None))

    def test_ayni_ailenin_tekrari_cok_urunlu_YAPMAZ(self):
        metin = "Konut finansmanı. Konut finansmanı. Konut finansmanı avantajı."
        self.assertFalse(_cok_urunlu_mu(metin))


class UyariTest(unittest.TestCase):

    def test_isaretli_kimlik_varsa_uyari_verir(self):
        u = _cok_urunlu_uyarisi([761])
        self.assertIsNotNone(u)
        self.assertIn("761", u)
        self.assertIn("çok ürünlü", u.lower())

    def test_bos_listede_uyari_YOK(self):
        self.assertIsNone(_cok_urunlu_uyarisi([]))

    def test_uyari_DISLAMA_demez(self):
        """Belge kıyastan atılmıyor; yalnız belirsizlik söyleniyor."""
        u = _cok_urunlu_uyarisi([761, 1827])
        self.assertNotIn("dışlan", u.lower())
        self.assertIn("761", u)
        self.assertIn("1827", u)


if __name__ == "__main__":
    unittest.main()
