"""Şartname "Senaryo 2" kıyas kalıbı — çok boyutlu madde listesi + gerekçe.

İlgili: ../src/chatbot/structured.py (`_phrase_iki_banka_kiyasi`, `_kiyas_maddesi`,
        `_bildirme_eki`, `_kiyas_ailesi_sec`)
        ../src/chatbot/bot.py (`_KIYAS_KAPSAM_NOTU` bastırma)
        raw/teknofest/2026-teknofest-tyda-sartname-2-senaryo.pdf s.13

## Bu testlerin varlık sebebi — ÖLÇÜLDÜ (2026-08-16, `data/demo.db`, LLM kapalı)

Şartname s.13 chatbot çıktısını ÖRNEKLE yazılı olarak veriyor:

    Kullanıcı: A Bankası mı daha avantajlı, C Bankası mı?
    Chatbot: Bu iki kampanya farklı avantajlar sunmaktadır.
        • Kâr payı oranı açısından C Bankası daha avantajlıdır çünkü oran %1,87'dir.
        • Vade açısından A Bankası daha avantajlıdır çünkü 120 ay vade sunmaktadır.
        • Masraf avantajı açısından A Bankası öne çıkmaktadır çünkü 50.000 TL'ye
          kadar dosya masrafı alınmamaktadır.
        • Ek ödül açısından ise C Bankası 5.000 TL alışveriş kartı vermektedir.

Bu senaryo KARŞILANMIYORDU. "Kuveyt Türk mü daha avantajlı, Albaraka mı?"
sorusu tek boyuta düşüyor, yalnız `kar_payi_orani` listeliyor ve diğer üç
boyutu kullanıcıya SORU olarak geri veriyordu. Açık, "çünkü" bağlacı değil
KIYAS KAPSAMIydı — ve Fonksiyonellik (%20) ölçütünün "benzer ürünlerin
karşılaştırılabilmesi" maddesine doğrudan giriyordu.

## Testlerin ASIL işi: kalıbın uydurmaya dönüşmediğini kanıtlamak

Çok boyutlu bir kıyas, kazanan ilan etme baskısı yaratır. Aşağıdaki testler
tam da bunu engeller:

  * kıyaslanabilir değeri olmayan boyut MADDE BASMAZ (uydurma kazanan yok),
  * tek bankada değer varsa kazanan İLAN EDİLMEZ ("…açısından ise …"),
  * beraberlik kazanana ÇEVRİLMEZ ("…iki kampanya eşittir…"),
  * kıyas tek ürün ailesi içinde kalır ve bunu SÖYLER (CLAUDE.md §17).
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.chatbot.bot import Chatbot
from src.chatbot.router import BANK_DISPLAY, route
from src.chatbot.structured import _bildirme_eki, answer
from src.db.repository import Repository
from src.extraction.reconcile import build_campaign

#: Şartname s.12'deki A ve C bankası konut finansmanı kampanya metinleri.
#: Kurgu metin YAZILMADI — kıyas kalıbı şartmenin KENDİ örneğiyle sınanır.
SARTNAME_A = (
    "Yeni ev sahibi olmak isteyen müşterilerimize özel %1,89 kâr payı oranı "
    "ile 120 ay vadeye kadar konut finansmanı fırsatı sunulmaktadır. Kampanya "
    "kapsamında 50.000 TL'ye kadar dosya masrafı alınmamaktadır. Kampanya "
    "31 Aralık 2026 tarihine kadar geçerlidir."
)
SARTNAME_C = (
    "Yeni konut alımlarına özel %1,87 kâr payı oranı ile 96 ay vadeli konut "
    "finansmanı fırsatı. Kampanya kapsamında 5.000 TL değerinde alışveriş "
    "çeki verilmektedir."
)

SORU = "Kuveyt Türk mü daha avantajlı, Albaraka mı?"


def _depo(*kampanyalar: tuple[str, str, str]) -> Repository:
    """Bellek içi depo. Banka ADLARI da yazılır — teslim edilen `data/demo.db`
    doğru yazılmış adı taşıyor ve cevap ekranda slug göstermemeli."""
    repo = Repository(":memory:")
    for slug, metin, tur in kampanyalar:
        repo.upsert_bank(BANK_DISPLAY.get(slug, slug), slug)
        repo.insert_campaign(
            build_campaign(metin, bank_slug=slug, campaign_type=tur))
    return repo


def _cevap(repo: Repository, soru: str = SORU) -> str:
    return answer(repo, route(soru)).text


class TestBildirmeEki(unittest.TestCase):
    """Sayının OKUNUŞUNA göre ek — şartname "oran %1,87'dir" yazıyor."""

    def test_sartnamedeki_iki_oran(self) -> None:
        """Şartname iki oranı da ekiyle yazıyor: %1,87'dir ve %1,89'dur."""
        self.assertEqual("%1,87" + _bildirme_eki("%1,87"), "%1,87'dir")
        self.assertEqual("%1,89" + _bildirme_eki("%1,89"), "%1,89'dur")

    def test_buyuk_unlu_uyumu_ve_sertlesme(self) -> None:
        for deger, beklenen in [
            ("%0", "'dır"),        # sıfır
            ("%2,3", "'tür"),      # üç      — sertleşme
            ("%2,4", "'tür"),      # dört    — sertleşme
            ("%2,5", "'tir"),      # beş     — sertleşme
            ("%2,6", "'dır"),      # altı
            ("%2,9", "'dur"),      # dokuz
            ("%10", "'dur"),       # on
            ("%40", "'tır"),       # kırk    — sertleşme
            ("%60", "'tır"),       # altmış  — sertleşme
            ("%90", "'dır"),       # doksan
            ("%100", "'dür"),      # yüz
            ("%1000", "'dir"),     # bin
        ]:
            with self.subTest(deger=deger):
                self.assertEqual(_bildirme_eki(deger), beklenen)

    def test_para_birimi(self) -> None:
        self.assertEqual("5.000 TL" + _bildirme_eki("5.000 TL"), "5.000 TL'dir")

    def test_karar_veremeyince_bos_doner(self) -> None:
        """Yanlış ek üretmektense ek üretmemek dürüsttür."""
        self.assertEqual(_bildirme_eki("masrafsız"), "")
        self.assertEqual(_bildirme_eki(""), "")


class TestSartnameKalibi(unittest.TestCase):
    """Şartmenin kendi örneğiyle: kalıp birebir tutuyor mu."""

    def setUp(self) -> None:
        self.metin = _cevap(_depo(
            ("kuveyt-turk", SARTNAME_A, "Konut Finansmanı"),
            ("albaraka", SARTNAME_C, "Konut Finansmanı")))

    def test_giris_cumlesi(self) -> None:
        self.assertIn("Bu iki kampanya farklı avantajlar sunmaktadır",
                      self.metin)

    def test_kar_payi_maddesi_sartname_kalibinda(self) -> None:
        """Şartname: "Kâr payı oranı açısından C Bankası daha avantajlıdır
        çünkü oran %1,87'dir." — düşük oran kazanır, gerekçe oranın kendisi."""
        self.assertIn("Kâr payı oranı açısından **Albaraka Türk** daha "
                      "avantajlıdır çünkü oran %1,87'dir.", self.metin)

    def test_cunku_oncesinde_virgul_YOK(self) -> None:
        """Şartname "avantajlıdır çünkü" yazıyor — araya virgül koymuyor."""
        self.assertNotIn(", çünkü", self.metin)
        self.assertIn("avantajlıdır çünkü", self.metin)

    def test_vade_gerekcesi_sayi_degil_CUMLE(self) -> None:
        """Şartname: "…çünkü 120 ay vade sunmaktadır." — çıplak sayı değil."""
        self.assertIn("Vade açısından **Kuveyt Türk** daha avantajlıdır çünkü "
                      "120 ay vade sunmaktadır.", self.metin)

    def test_masraf_gerekcesi_KOSUL_metnidir(self) -> None:
        """Masrafta gerekçe sayı değil koşuldur; yüklem de şartnamedeki gibi."""
        self.assertIn("Masraf avantajı açısından", self.metin)
        self.assertIn("dosya masrafı", self.metin)

    def test_ek_odul_maddesi_kazanan_ILAN_ETMEZ(self) -> None:
        """Şartname son maddede kazanan ilan etmiyor: "…açısından ise …".

        C Bankası'nda 5.000 TL alışveriş çeki var, A Bankası'nda karşılığı yok;
        kıyas edilecek ikinci değer olmadan "daha avantajlı" denemez.
        """
        self.assertIn("Ek ödül açısından ise **Albaraka Türk**", self.metin)
        self.assertNotIn("Ek ödül açısından **", self.metin)

    def test_turkce_sayi_bicimi(self) -> None:
        """Binlik `.`, ondalık `,` — İngilizce biçim sızmamalı."""
        self.assertIn("5.000 TL", self.metin)
        self.assertIn("%1,87", self.metin)
        self.assertNotIn("5000 TL", self.metin)
        self.assertNotIn("1.87", self.metin)

    def test_dort_boyut_da_madde_uretir(self) -> None:
        """Kâr payı + vade + masraf + ek ödül — şartmenin dört maddesi."""
        for etiket in ("Kâr payı oranı açısından", "Vade açısından",
                       "Masraf avantajı açısından", "Ek ödül açısından"):
            with self.subTest(etiket=etiket):
                self.assertIn(etiket, self.metin)


class TestUydurmaYok(unittest.TestCase):
    """Kalıp, olmayan bir kıyası VAR gibi göstermemeli."""

    def test_beraberlik_kazanana_cevrilmez(self) -> None:
        metin = _cevap(_depo(
            ("kuveyt-turk", "Konut finansmanında %2,50 kâr payı oranı ile "
                            "120 ay vadeye kadar imkân sunulmaktadır.",
             "Konut Finansmanı"),
            ("albaraka", "Konut finansmanında %2,50 kâr payı oranı ile "
                         "120 ay vadeye kadar imkân sunulmaktadır.",
             "Konut Finansmanı")))
        self.assertIn("iki kampanya eşittir çünkü her ikisi de", metin)
        self.assertNotIn("daha avantajlıdır", metin)

    def test_kiyaslanamayan_boyut_MADDE_BASMAZ(self) -> None:
        """Aralık değer kıyas dışıdır; o boyutta kazanan uydurulmaz."""
        metin = _cevap(_depo(
            ("kuveyt-turk", "Konut finansmanında kâr payı oranı %1,99–%2,49 "
                            "arasında, 120 ay vadeye kadar.", "Konut Finansmanı"),
            ("albaraka", "Konut finansmanında kâr payı oranı %2,10–%2,60 "
                         "arasında, 96 ay vadeye kadar.", "Konut Finansmanı")))
        self.assertNotIn("Kâr payı oranı açısından", metin)
        self.assertIn("Vade açısından", metin)

    def test_tek_bankali_boyutta_kazanan_ilan_edilmez(self) -> None:
        metin = _cevap(_depo(
            ("kuveyt-turk", "Konut finansmanında %1,89 kâr payı oranı ile "
                            "120 ay vadeye kadar imkân sunulmaktadır.",
             "Konut Finansmanı"),
            ("albaraka", "Konut finansmanında 96 ay vadeli finansman.",
             "Konut Finansmanı")))
        self.assertIn("Kâr payı oranı açısından ise **Kuveyt Türk**", metin)


class TestAdilKiyasKorunuyor(unittest.TestCase):
    """CLAUDE.md §17 — kıyas ürün ailesi İÇİNDE kalır ve bunu söyler."""

    def test_aile_soylenir_ve_aileler_arasi_kiyas_yapilmaz(self) -> None:
        metin = _cevap(_depo(
            ("kuveyt-turk", "Konut finansmanında %1,89 kâr payı oranı ile "
                            "120 ay vadeye kadar.", "Konut Finansmanı"),
            ("albaraka", "Konut finansmanında %2,49 kâr payı oranı ile "
                         "96 ay vadeye kadar.", "Konut Finansmanı"),
            ("kuveyt-turk", "Taşıt finansmanında %3,10 kâr payı oranı ile "
                            "48 ay vadeye kadar.", "Taşıt Finansmanı"),
            ("albaraka", "Taşıt finansmanında %2,80 kâr payı oranı ile "
                         "36 ay vadeye kadar.", "Taşıt Finansmanı")))
        self.assertIn("ürün ailesi içinde yapıldı", metin)
        self.assertIn("Aynı bankalar şu ailelerde de karşılaştırılabilir",
                      metin)

    def test_tek_banka_sorusu_bu_daldan_GECMEZ(self) -> None:
        """Kıyas kalıbı yalnız iki+ banka adı geçtiğinde devreye girer."""
        repo = _depo(("kuveyt-turk", SARTNAME_A, "Konut Finansmanı"))
        metin = _cevap(repo, "Kuveyt Türk'ün konut finansmanı oranı ne?")
        self.assertNotIn("farklı avantajlar sunmaktadır", metin)

    def test_ustunluk_sorusu_bu_daldan_GECMEZ(self) -> None:
        """"En düşük kâr payı" sorusu alanı SÖYLÜYOR; eski şablon korunur."""
        repo = _depo(("kuveyt-turk", SARTNAME_A, "Konut Finansmanı"),
                     ("albaraka", SARTNAME_C, "Konut Finansmanı"))
        metin = _cevap(repo, "En düşük kâr payı oranı hangi bankada?")
        self.assertNotIn("farklı avantajlar sunmaktadır", metin)
        self.assertIn("en düşük kâr payı oranı", metin)


class TestKapsamKapisi(unittest.TestCase):
    """Adı geçen banka, o alanda satırı yok diye SESSİZCE DÜŞMEZ.

    Şartmenin s.12 tablosu B ve C bankalarını eksik hücrelerine rağmen satır
    olarak gösteriyor. `compare.rank(kapsam=...)` mekanizmasını chatbot yoluna
    bağlayan tel budur; bağlanmadan önce "Kuveyt Türk ve Ziraat Katılım konut
    finansmanını karşılaştır" sorusunda alanı olmayan banka hiç yokmuş gibi
    görünüyordu.
    """

    def _alan_yok_depo(self) -> Repository:
        """Bir bankada kâr payı VAR, diğerinde aynı ailede YOK."""
        return _depo(
            ("kuveyt-turk", "Konut finansmanında %1,89 kâr payı oranı ile "
                            "120 ay vadeye kadar imkân sunulmaktadır.",
             "Konut Finansmanı"),
            ("ziraat-katilim", "Konut finansmanında 120 ay vadeye kadar "
                               "ödeme kolaylığı sunulmaktadır.",
             "Konut Finansmanı"))

    def test_alani_olmayan_banka_LISTEDE_kalir(self) -> None:
        metin = _cevap(
            self._alan_yok_depo(),
            "Kuveyt Türk ile Ziraat Katılım konut finansmanı kâr payı "
            "oranını karşılaştır")
        self.assertIn("Ziraat Katılım", metin)
        self.assertIn("bu alan belirtilmemiş", metin)

    def test_deger_yoksa_ekranda_Belirtilmemis_yazar(self) -> None:
        """Ham `None` basılmaz; jeton arayüzdeki `BELIRTILMEMIS` ile aynıdır."""
        metin = _cevap(
            self._alan_yok_depo(),
            "Kuveyt Türk ile Ziraat Katılım konut finansmanı kâr payı "
            "oranını karşılaştır")
        self.assertIn("Belirtilmemiş", metin)
        self.assertNotIn("None", metin)

    def test_alani_olmayan_banka_KAZANAN_ILAN_EDILMEZ(self) -> None:
        """Değeri olmayan satır sıralamaya girmez; uydurma kazanan çıkmaz."""
        metin = _cevap(self._alan_yok_depo(),
                       "Kuveyt Türk mü daha avantajlı, Ziraat Katılım mı?")
        self.assertNotIn("Kâr payı oranı açısından **Ziraat Katılım**", metin)

    def test_kiyaslanamayan_boyut_SESSIZCE_dusmez(self) -> None:
        """Çok boyutlu cevapta madde basılmayan boyut adıyla duyurulur."""
        metin = _cevap(self._alan_yok_depo(),
                       "Kuveyt Türk mü daha avantajlı, Ziraat Katılım mı?")
        self.assertIn("kıyaslanamayan boyut", metin)
        self.assertIn("kâr payı oranı", metin)

    def test_banka_sayilmamissa_kapsam_ACILMAZ(self) -> None:
        """"En düşük kâr payı hangi bankada?" cevabı şişirilmez.

        Kapsam o dalda açılsaydı cevap, alanda hiç verisi olmayan onlarca
        (banka × aile) çiftiyle dolardı; soru zaten "kim kazanıyor"dur.
        """
        metin = _cevap(self._alan_yok_depo(),
                       "En düşük kâr payı oranı hangi bankada?")
        self.assertNotIn("Belirtilmemiş", metin)
        self.assertIn("Kuveyt Türk", metin)


class TestKapsamNotu(unittest.TestCase):
    """Tek alanlı kapsam notu çok boyutlu cevabın altında YANLIŞ olurdu."""

    def test_cok_boyutlu_cevapta_tek_alan_notu_BASTIRILIR(self) -> None:
        repo = _depo(("kuveyt-turk", SARTNAME_A, "Konut Finansmanı"),
                     ("albaraka", SARTNAME_C, "Konut Finansmanı"))
        metin = Chatbot(repo, llm=None).ask(SORU).text
        self.assertNotIn("Yukarıdaki kıyas **kâr payı oranı** üzerindendir",
                         metin)
        self.assertIn("Bu iki kampanya farklı avantajlar sunmaktadır", metin)

    def test_tek_alanli_cevapta_not_KORUNUR(self) -> None:
        """Tek banka adı geçince çok boyutlu dala GİRİLMEZ; not yerinde kalır.

        Kıyas için iki taraf gerekir; tek bankada "farklı avantajlar
        sunmaktadır" demek olmayan bir kıyas iddia etmek olurdu.
        """
        repo = _depo(("kuveyt-turk", SARTNAME_A, "Konut Finansmanı"))
        metin = Chatbot(repo, llm=None).ask("Kuveyt Türk daha avantajlı mı?").text
        self.assertNotIn("farklı avantajlar sunmaktadır", metin)
        self.assertIn("Yukarıdaki kıyas **kâr payı oranı** üzerindendir", metin)


if __name__ == "__main__":
    unittest.main()
