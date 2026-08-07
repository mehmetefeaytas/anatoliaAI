"""Blok düzeyinde içerik/çerçeve ayrımı — öncelik sırası ve sınır davranışı.

İlgili: ../src/preprocessing/blocks.py, ../docs/rapor/boilerplate-kapsam.md

Bu modülün tamamı tek bir öncelik sırasını korumak için var:

    alan-dışılık > sayısal değer > tekrar > alan sözcüğü

Sıra sekiz kombinasyona karşı sınandı ve her adımı bir ölçüm dayattı. Testler
o ölçümleri sabitliyor — özellikle iki tanesini:

  * KVKK bloğundaki "ücretsiz" bir `masraf_durumu` tetikleyicisidir; alan-dışı
    sinyali değeri EZMEZSE o blok kurtulur ve halüsinasyon geri gelir.
  * Menü satırları tam olarak alan sözcüklerinden oluşur ("Konut Finansmanı
    Taşıt Finansmanı..."); alan SÖZCÜĞÜ tekrarı ezerse menüler kurtulur.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.preprocessing import blocks as B


def _karar(metin: str, cerceve=None, terimler=None):
    return B.kararlar(metin, cerceve, terimler=terimler)


class TestAlanDisiSinyali(unittest.TestCase):
    """Tek başına siler; yanlış pozitifi doğrudan içerik kaybıdır."""

    def test_kvkk_ve_cerez_kaliplari_yakalanir(self) -> None:
        for m in ("Çerez Aydınlatma Metni'ni inceleyebilirsiniz.",
                  "6698 sayılı Kişisel Verilerin Korunması Kanunu uyarınca.",
                  "Zorunlu çerezler sistemlerimizde kapatılamaz.",
                  "Veri sorumlusu sıfatıyla hareket edilmektedir.",
                  "Gizlilik politikası için tıklayınız.",
                  "Analitik çerezler ziyaret istatistiklerini toplar."):
            self.assertGreater(B.anti_skoru(m), 0, m)

    def test_siradan_urun_cumlesi_alan_disi_SAYILMAZ(self) -> None:
        """Bu sinyal tekrar kanıtı aranmadan sildiği için kesin olmalı."""
        for m in ("Konut finansmanında kâr payı oranı %2,05'ten başlıyor.",
                  "Kişisel bankacılık ürünlerimizi inceleyin.",
                  "Verilerinizi şubemizden güncelleyebilirsiniz.",
                  "Kampanya koşulları için şubelerimize danışınız.",
                  "Politikamız gereği başvurular 3 gün içinde sonuçlanır."):
            self.assertEqual(B.anti_skoru(m), 0, m)


class TestOncelikSirasi(unittest.TestCase):
    def test_alan_disi_DEGERI_ezer(self) -> None:
        """KVKK'daki 'ücretsiz' korunursa halüsinasyon geri gelir."""
        m = ("Kişisel verilerinizin işlenmesi hakkında talebiniz 30 gün "
             "içinde ücretsiz olarak sonuçlandırılır.")
        k = _karar(m)[0]
        self.assertFalse(k.tut)
        self.assertEqual(k.gerekce, "alan_disi")

    def test_sayisal_deger_TEKRARI_ezer(self) -> None:
        """Şablonlaşmış ama değer taşıyan cümle korunmalı."""
        m = "Kâr payı oranı %2,05'tir."
        cerceve = {B.cumle_anahtari(m)}
        k = _karar(m, cerceve)[0]
        self.assertTrue(k.tut)
        self.assertEqual(k.gerekce, "sayisal_deger")

    def test_tekrar_ALAN_SOZCUGUNU_ezer(self) -> None:
        """Menüler tam olarak alan sözcüklerinden oluşur; kurtulmamalılar."""
        m = "Konut Finansmanı Taşıt Finansmanı İhtiyaç Finansmanı Kampanyalar"
        self.assertGreater(B.deger_skoru(m), 0, "alan sözcüğü taşımalı")
        k = _karar(m, {B.cumle_anahtari(m)})[0]
        self.assertFalse(k.tut)
        self.assertEqual(k.gerekce, "tekrar")

    def test_alan_sozcugu_tekrar_YOKKEN_korur(self) -> None:
        m = "Konut finansmanı başvurunuz şubemizce değerlendirilecektir."
        k = _karar(m, set())[0]
        self.assertTrue(k.tut)

    def test_hicbir_sinyal_yoksa_KORUNUR(self) -> None:
        """Çerçeve olduğunu ispatlayamıyorsak silmeyiz."""
        k = _karar("Bu cümle hiçbir sinyal taşımıyor efendim.", set())[0]
        self.assertTrue(k.tut)
        self.assertEqual(k.gerekce, "sinyal_yok")


class TestBolgeYayilimi(unittest.TestCase):
    """İşaret cümlelerce önce geçebilir; karar tek cümleye bakarak verilemez."""

    def test_isaretten_sonraki_cumleler_de_silinir(self) -> None:
        m = ("Çerez Aydınlatma Metni. Bunlar tarayıcınızda saklanır. "
             "Talebiniz 30 gün içinde ücretsiz sonuçlandırılır.")
        kr = _karar(m)
        self.assertTrue(all(not k.tut for k in kr), [k.gerekce for k in kr])
        self.assertTrue(any(k.bolge for k in kr))

    def test_guclu_alan_degeri_bolgeyi_SONDURUR(self) -> None:
        m = ("Çerez Politikası hakkında bilgi. Bir ara cümle. "
             "Konut finansmanı kâr payı oranı %2,05 ve vade 120 ay, "
             "tahsis ücreti 500 TL.")
        kr = _karar(m)
        self.assertTrue(kr[-1].tut, "güçlü ürün cümlesi bölgede boğuldu")

    def test_yayilim_sonsuz_DEGIL(self) -> None:
        m = "Çerez Politikası. " + " ".join(
            f"Alakasız cümle {i}." for i in range(B.YAYILIM_BLOK + 3))
        kr = _karar(m)
        self.assertTrue(kr[-1].tut, "yayılım belgenin sonuna kadar sürdü")


class TestSinirDavranisi(unittest.TestCase):
    def test_blok_CUMLE_duzeyinde(self) -> None:
        """2 cümlelik blokta içerik/KVKK sınırındaki gerçek cümle ölüyordu."""
        self.assertEqual(B.BLOK_CUMLE, 1)

    def test_urun_cumlesi_komsu_cerez_cumlesinden_etkilenmez(self) -> None:
        """Ölçülen gerçek vaka: bu cümle 2'li blokta siliniyordu."""
        m = ("Yeni açılan TL Katılma Hesapları yüksek paylaşım oranları "
             "üzerinden kâr dağıtacaktır. "
             "Sitemizde çerezler kullanıyoruz.")
        kr = _karar(m)
        self.assertTrue(kr[0].tut, "gerçek ürün cümlesi komşusuyla gitti")
        self.assertFalse(kr[1].tut)

    def test_vadesi_gibi_ekli_bicimler_deger_sayilir(self) -> None:
        """`keyword_pattern` kısa anahtarı iki taraftan sınırlıyor ve 'vade'
        anahtarı 'vadesi'yi kaçırıyordu — ölçümde yakalandı."""
        self.assertGreater(B.deger_skoru("vadesi yenilenen hesaplar"), 0)
        self.assertGreater(B.deger_skoru("paylaşım oranları üzerinden"), 0)


class TestCerceveCumleleri(unittest.TestCase):
    def test_esik_altinda_cerceve_sayilmaz(self) -> None:
        m = "Bu cümle iki belgede geçiyor efendim."
        self.assertEqual(B.cerceve_cumleler([m, m], min_docs=3), set())

    def test_esikte_cerceve_sayilir(self) -> None:
        m = "Bu cümle üç belgede geçiyor efendim."
        self.assertIn(B.cumle_anahtari(m),
                      B.cerceve_cumleler([m, m, m], min_docs=3))

    def test_cok_kisa_cumle_cerceve_sayilmaz(self) -> None:
        """'Detaylı Bilgi' her yerde geçer ama içeriğin parçası olabilir."""
        self.assertEqual(
            B.cerceve_cumleler(["Detaylı Bilgi."] * 5, min_docs=3), set())

    def test_ayni_belgede_tekrar_DF_sismez(self) -> None:
        m = "Aynı cümle aynı belgede iki kez geçiyor efendim."
        self.assertEqual(B.cerceve_cumleler([m + " " + m], min_docs=2), set())


class TestTemizle(unittest.TestCase):
    def test_kararlar_denetlenebilir_doner(self) -> None:
        metin, kr = B.temizle("Çerez Politikası. Kâr payı oranı %2,05'tir.")
        self.assertIn("2,05", metin)
        self.assertNotIn("Çerez Politikası", metin)
        d = kr[0].as_dict()
        for alan in ("bas", "son", "tut", "gerekce", "anti", "deger", "tekrar"):
            self.assertIn(alan, d)

    def test_bos_metin(self) -> None:
        self.assertEqual(B.temizle(""), ("", []))

    def test_hicbir_sey_silinmezse_metin_korunur(self) -> None:
        m = "Konut finansmanı kâr payı oranı %2,05'tir."
        self.assertIn("%2,05", B.temizle(m, set())[0])


if __name__ == "__main__":
    unittest.main()
