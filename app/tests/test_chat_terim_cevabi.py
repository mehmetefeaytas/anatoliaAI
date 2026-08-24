"""Terim sorusuna SÖZLÜKTEN kaynaklı cevap.

İlgili: ../src/chatbot/terim_cevabi.py
        ../src/domain/terminology.py · ../data/terminology/katilim-terim-sozlugu.json
        CLAUDE.md §12 (katılım bankacılığı terminolojisi %30'un kalbi)

## Ölçülmüş boşluk

Kullanıcı raporu (2026-08-24), iki canlı çıktı:

    "Finansman ne demek"  → "Bu soru elimdeki verinin kapsamı dışında"
    "Murabaha ne demek"   → "Bu bilgi verimde yok."

Oysa `data/terminology/katilim-terim-sozlugu.json` 101 terim için TAM kayıt
tutuyor: `tanim`, `sade_aciklama`, `kaynak` (ör. Murabaha → *AAOIFI Şer'i
Standart No. 8*), `risk_notu`, `degildir`, `iliskili`. Yani veri VARDI ve
chatbot ona hiç bakmıyordu.

## Niçin EVREN değil, sözlük

Uzak modelle tanım üretmek kaynaksız bir iddia olurdu — bu projede yasak
(CLAUDE.md §19 halüsinasyon yasağı, "kaynaksız iddia yasak"). Sözlük ise
AAOIFI standardı ve BDDK yönetmeliği gibi GERÇEK kaynak taşıyor. Terim tanımı,
modelin bilmesi gereken değil kaynağın söylemesi gereken bir şeydir.

## Alan sorularını ÇALMAMALI

"Kuveyt Türk kâr payı oranı nedir" bir TERİM sorusu değil, bir ALAN sorusudur
ve yapısal sorgu yoluna gitmelidir. Bu yüzden terim yolu yalnız SAF terim
sorularında devreye girer: soruda banka ya da ürün adı geçiyorsa devreye
GİRMEZ.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.chatbot.terim_cevabi import terim_cevabi, terim_sorusu_mu


class TespitTest(unittest.TestCase):

    def test_ne_demek_kalibi(self):
        self.assertTrue(terim_sorusu_mu("Murabaha ne demek"))
        self.assertTrue(terim_sorusu_mu("murabaha nedir"))
        self.assertTrue(terim_sorusu_mu("Riba ne anlama gelir?"))
        self.assertTrue(terim_sorusu_mu("kabz tanımı"))

    def test_ALAN_sorusu_terim_sorusu_DEGIL(self):
        """Banka/ürün adı geçen soru yapısal sorgu yoluna gitmeli."""
        for soru in ("Kuveyt Türk kâr payı oranı nedir",
                     "Albaraka konut finansmanı vadesi nedir",
                     "en yüksek kâr payı hangi bankada"):
            with self.subTest(soru=soru):
                self.assertFalse(terim_sorusu_mu(soru))

    def test_kalipsiz_soru_terim_sorusu_DEGIL(self):
        self.assertFalse(terim_sorusu_mu("Murabaha kampanyaları"))
        self.assertFalse(terim_sorusu_mu(""))


class CevapTest(unittest.TestCase):

    def test_murabaha_tanimi_ve_KAYNAGI(self):
        c = terim_cevabi("Murabaha ne demek")
        self.assertIsNotNone(c)
        self.assertIn("Murabaha", c)
        self.assertIn("kâr", c.lower())
        # Kaynaksız iddia yasak: kayıttaki kaynak metne girmeli
        self.assertIn("AAOIFI", c)

    def test_RISK_NOTU_gosterilir(self):
        """Murabaha kaydının risk notu terminoloji uyarısı taşıyor."""
        c = terim_cevabi("murabaha nedir")
        self.assertIn("kâr oranı", c.lower().replace("i̇", "i"))

    def test_varyant_ile_de_bulunur(self):
        """`kabz` kaydının varyantları: kabd, qabd."""
        c = terim_cevabi("kabd ne demek")
        self.assertIsNotNone(c)
        self.assertIn("Kabz", c)

    def test_SOZLUKTE_OLMAYAN_terim_None(self):
        """Uydurma yerine None: çağıran mevcut 'bilmiyorum' cevabını verir.

        NOT: ilk sürümde burada "Müşaraka" kullanılmıştı — sözlükte OLMADIĞI
        sanılıyordu. Meğer var (`Muşaraka`, AAOIFI Şer'i Standart No. 12) ve
        cevap doğru üretiliyor. Bu, `eval/rag_eval.py`'nin "müşaraka nedir ->
        isabetsiz" bulgusunu da açıklıyor: terim vardı, chatbot bakmıyordu.
        """
        self.assertIsNone(terim_cevabi("zxqwerty ne demek"))
        self.assertIsNone(terim_cevabi("blorptaks nedir"))

    def test_musaraka_da_CEVAPLANIR(self):
        """Sözlüğün kapsamı sanılandan geniş — bu testle kayda geçiyor."""
        c = terim_cevabi("Müşaraka ne demek")
        self.assertIsNotNone(c)
        self.assertIn("ortaklık", c.lower())
        self.assertIn("AAOIFI", c)

    def test_alan_sorusuna_cevap_VERMEZ(self):
        self.assertIsNone(terim_cevabi("Kuveyt Türk kâr payı oranı nedir"))

    def test_cevap_SADE_ACIKLAMA_da_icerir(self):
        c = terim_cevabi("Murabaha ne demek")
        self.assertIn("taksitle", c.lower())


class TestOperasyonelTerimler(unittest.TestCase):
    """Projenin kendi alan adlarıyla örtüşen 10 temel terim.

    Ölçüldü (2026-08-24): sistem `tahsis_ucuceti` alanını çıkarıyordu ama
    "tahsis ücreti ne demek" sorusuna cevap veremiyordu. Üç dış kaynak
    denenmiş ve hiçbiri bu terimleri içermemişti (TCMB makroekonomi sözlüğü,
    korpus sözleşmeleri, TKBB fıkhî sözlüğü); tanımlar bu yüzden PROJENİN
    KENDİ kaydı olarak yazıldı ve `kaynak` alanı bunu açıkça söylüyor.
    """

    TERIMLER = ("Finansman", "vade", "taksit", "tahsis ücreti", "masraf",
                "stopaj", "ekspertiz", "limit", "hesap işletim ücreti",
                "dosya masrafı")

    def test_hepsi_cevaplanir(self):
        for a in self.TERIMLER:
            with self.subTest(terim=a):
                self.assertIsNotNone(terim_cevabi(f"{a} ne demek"))

    def test_kaynak_KENDI_kaydi_oldugunu_soyluyor(self):
        """Uydurma bir dış kaynak gösterilmiyor."""
        c = terim_cevabi("tahsis ücreti ne demek")
        self.assertIn("Anatolia AI proje sözlüğü", c)

    def test_katilim_baglami_tasiniyor(self):
        """Bu terimler konvansiyonel bankacılıkla karıştırılabilir; ayrım
        cevapta görünmek zorunda."""
        c = terim_cevabi("Finansman ne demek")
        self.assertIn("Karıştırılmamalı", c)
        self.assertIn("kredi", c.lower())
        self.assertIn("⚠️", c)   # risk notu

    def test_masrafsiz_ayrimi_yaziliyor(self):
        """'Masrafsız' kâr payının sıfır olduğu anlamına GELMEZ."""
        c = terim_cevabi("masraf ne demek")
        self.assertIn("masrafsız", c.lower())

    def test_stopaj_brut_net_ayrimi(self):
        c = terim_cevabi("stopaj ne demek")
        self.assertIn("net", c.lower())


class TestKesinTanimKalibi(unittest.TestCase):
    """"ne demek" alan izini geçersiz kılar, "nedir" kılmaz."""

    def test_ne_demek_alan_izini_ASAR(self):
        """'tahsis ücreti' bir ALAN adı ama 'ne demek' tartışmasız tanım ister."""
        self.assertTrue(terim_sorusu_mu("tahsis ücreti ne demek"))
        self.assertTrue(terim_sorusu_mu("kâr payı oranı ne anlama gelir"))

    def test_nedir_alan_izinde_ELENIR(self):
        """Değer sorusu yapısal sorgu yoluna gitmeli."""
        self.assertFalse(terim_sorusu_mu("Kuveyt Türk kâr payı oranı nedir"))

    def test_GUVENLIK_alan_sorusu_hala_elenir(self):
        """Ölçülmüş sızıntı vakası: terim yolu post-filter'ı atlıyor, bu yüzden
        alan soruları oraya DÜŞMEMELİ (tests/test_safety.py)."""
        self.assertFalse(terim_sorusu_mu(
            "Bu üründe masraf durumu nedir, faiz uygulanır mı?"))


if __name__ == "__main__":
    unittest.main()


class AlintiKorumaTest(unittest.TestCase):
    """Sözlük ALINTISI çıktı korumasıyla yeniden yazılmaz.

    Ölçülmüş hata: `Riba` kaydının `resmi_tr` alanı **"Faiz"**dir — riba'nın
    Türkçe karşılığı gerçekten faizdir ve katılım finansının YASAKLADIĞI
    şeydir. `sanitize_output` onu "Kâr payı" yapıyordu ve tanım TERSİNE
    dönüyordu: yasak olan şey meşru olanla değiştirilmiş oluyordu.

    Çıktı koruması LLM üretimi için var (model yasak terim üretirse düzelt).
    Terminoloji cevabı ise LLM üretimi DEĞİL, kendi sözlüğümüzden bir
    alıntıdır ve kaynağı metnin içinde yazılıdır. Alıntıyı yeniden yazmak
    kaynağı bozmaktır.
    """

    def test_riba_kaydinda_resmi_karsilik_FAIZ_kalir(self):
        c = terim_cevabi("Riba nedir")
        self.assertIsNotNone(c)
        self.assertIn("Faiz", c, "sözlükteki `resmi_tr` alanı korunmalı")

    def test_guard_output_alinti_modunda_YENIDEN_YAZMAZ(self):
        from src.chatbot import safety
        scr = safety.screen_input("Riba nedir")
        govde = terim_cevabi("Riba nedir")
        metin, _ = safety.guard_output(govde, scr, has_sources=True,
                                       alinti=True)
        self.assertIn("Faiz", metin)

    def test_guard_output_NORMAL_modda_yeniden_yazar(self):
        """Karşı-örnek: alıntı olmayan gövdede koruma çalışmaya devam eder."""
        from src.chatbot import safety
        scr = safety.screen_input("soru")
        metin, _ = safety.guard_output("Bu üründe faiz oranı %2 uygulanır.",
                                       scr, has_sources=True)
        self.assertNotIn("faiz oranı", metin.lower())


class GuvenlikSiziMasiTest(unittest.TestCase):
    """Terim yolu ALAN sorularını çalmamalı — çalarsa post-filter atlanır.

    Ölçülmüş açık (`tests/test_safety.py`): "Bu üründe masraf durumu nedir,
    faiz uygulanır mı?" sorusu `nedir` kalıbı yüzünden terim yoluna gidiyordu.
    O yol alıntı modunda çalıştığı için post-filter atlanıyor ve kaynaktaki
    yasak terim ekrana sızıyordu.
    """

    def test_alan_adi_gecen_soru_terim_yoluna_GITMEZ(self):
        # «vade nedir» BU LİSTEDEN ÇIKARILDI (2026-08-25, kullanıcı raporu).
        # Geniş `\bvade\w*\b` deseni onu da yakalıyordu ve soru RAG'a
        # düşüyordu; model üç kampanya belgesinden derlediği bir paragrafla
        # cevap veriyordu — tanım değil, örnek listesi. Oysa sözlükte tam kaydı
        # var. Güvenlik daralmadı: alan bağlamı taşıyan terim sorusunda ALINTI
        # modu artık KAPANIYOR ve post-filter normal koşuyor
        # (`terim_cevabi.alan_baglamli_mi`), yani sızıntı yolu kapalı.
        # Aşağıdaki dört vaka hâlâ terim yoluna GİTMEMELİ.
        for soru in ("Bu üründe masraf durumu nedir, faiz uygulanır mı?",
                     "kâr payı oranı nedir",
                     "tahsis ücreti nedir",
                     "bu üründe masraf var mı"):
            with self.subTest(soru=soru):
                self.assertFalse(terim_sorusu_mu(soru))
                self.assertIsNone(terim_cevabi(soru))

    def test_vade_nedir_TERIM_yoluna_gider(self) -> None:
        """Alan adıyla çakışsa da bu bir TANIM sorusudur ve kaydı vardır."""
        self.assertTrue(terim_sorusu_mu("vade nedir"))
        c = terim_cevabi("vade nedir")
        self.assertIsNotNone(c)
        self.assertIn("Vade", c)

    def test_alan_baglamli_terim_ALINTI_modunu_kullanmaz(self) -> None:
        """Alan bağlamı varsa post-filter atlanmamalı — sızıntı yolu kapalı.

        «tahsis ücreti ne demek» terim yoluna KESİN tanım kalıbıyla giriyor
        (`_KESIN_TANIM_KALIBI`) ama alan adı da taşıyor; o gövde alıntı
        modunda basılırsa post-filter atlanır. `alan_baglamli_mi` bu ayrımı
        yapıyor ve `bot.py` alıntı modunu ona göre kapatıyor.

        «vade nedir» ARTIK alan bağlamlı sayılmıyor: geniş `vade` deseni
        daraltıldı ve o soru düz bir tanım sorusu hâline geldi.
        """
        from src.chatbot.terim_cevabi import alan_baglamli_mi
        self.assertTrue(alan_baglamli_mi("tahsis ücreti ne demek"))
        self.assertFalse(alan_baglamli_mi("murabaha ne demek"))
        self.assertFalse(alan_baglamli_mi("vade nedir"))

    def test_ORAN_olmayan_terim_sorusu_hala_cevaplanir(self):
        """Ayrım "oranı" sözcüğünde: terim sorusu kaybolmamalı."""
        self.assertTrue(terim_sorusu_mu("kâr payı ne demek"))
