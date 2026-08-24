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


class TestGenisletilmisAileListesi(unittest.TestCase):
    """2026-08-24 ölçümüyle eklenen üç aile ve ELENEN geniş desenler.

    Kural %13,2 çok ürünlü buluyordu, EVREN'in bağımsız denetimi %18 demişti.
    Üç DAR desen eklendiğinde oran %18,0 oldu — iki bağımsız yöntem aynı
    sayıya vardı. Geniş desenler ölçülüp elendi (hepsi eklenince %32,5).
    """

    def test_fatura_talimati_ailesi_TANINIR(self):
        """`#761` vakası: 'her bir fatura talimatı için 200 TL iade'."""
        from src.chatbot.structured import _cok_urunlu_mu
        metin = ("Konut Finansmanı'nda 5 puan indirim ve her bir fatura "
                 "talimatı için 200 TL iade fırsatı.")
        self.assertTrue(_cok_urunlu_mu(metin))

    def test_sigorta_ve_doviz_aileleri_TANINIR(self):
        from src.chatbot.structured import _AILE_IZLERI
        for ad in ("Fatura/Ödeme Talimatı", "Sigorta/Tekafül",
                   "Döviz/Kıymetli Maden"):
            with self.subTest(ad=ad):
                self.assertIn(ad, _AILE_IZLERI)

    def test_GENIS_desenler_DISTA(self):
        """Ölçülüp elendi: 'pos' tek başına korpusun %23,2'sinde geçiyor ve
        altı adayın tamamı eklenince oran EVREN ölçümünün iki katına çıkıyordu.
        """
        from src.chatbot.structured import _AILE_IZLERI
        birlesik = " ".join(_AILE_IZLERI.values()).lower()
        for kacinilan in ("\\bpos\\b", "üye işyeri", "havale", "maaş müşteri"):
            with self.subTest(kacinilan=kacinilan):
                self.assertNotIn(kacinilan, birlesik)

    def test_tek_aile_cok_urunlu_YAPMAZ(self):
        """Yeni desenler yanlış pozitif üretmemeli: yalnız fatura geçen bir
        belge tek ailedir."""
        from src.chatbot.structured import _cok_urunlu_mu
        self.assertFalse(_cok_urunlu_mu(
            "Fatura ödeme işlemlerinizde geçerli kampanya."))

    def test_dokuz_aile(self):
        from src.chatbot.structured import _AILE_IZLERI
        self.assertEqual(len(_AILE_IZLERI), 9)


if __name__ == "__main__":
    unittest.main()
