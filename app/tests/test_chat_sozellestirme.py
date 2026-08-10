"""Yapısal cevabın LLM ile sözelleştirilmesi — DOĞRULAMA KAPISI.

İlgili: ../src/chatbot/bot.py (`_sozellestir`, `_sozellestirme_gecerli`)

## Bu testlerin varlık sebebi

Sözelleştirme, proje boyunca korunan tek şeyi — olgunun kaynağa birebir
bağlılığını — riske atabilecek TEK katmandır. Şablon cevap

    "en düşük kâr payı oranı: **Kuveyt Türk** (%1,79)."

akıcı bir cümleye çevrilirken model sayıyı yuvarlarsa, banka ekler ya da
"yaklaşık" gibi olmayan bir niteleme uydurursa, ekrandaki cevap ARTIK
kaynağa dayanmıyordur — üstelik daha inandırıcı göründüğü için daha
tehlikelidir.

Bu yüzden LLM çıktısı basılmadan önce programatik olarak denetlenir ve
denetim başarısızsa ŞABLON basılır. Aşağıdaki testler kapıyı hem temiz hem
KASITLI BOZUK çıktılarla sürer; ayrıca sıralamayı kilitler: güvenlik
feragatnamesi sözelleştirmeden SONRA eklenir, yani yutulamaz.

Testler ağ İSTEMEZ: `client` yerine sahte bir nesne geçirilir.
"""

from __future__ import annotations

import os
import sys
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.chatbot.bot import Chatbot, _sozellestirme_gecerli, sayilari_ayikla
from src.db.repository import Repository
from src.extraction.reconcile import build_campaign

SABLON = "en düşük kâr payı oranı: **Kuveyt Türk** (%1,79)."


class SahteIstemci:
    """`generate_json` sözleşmesini karşılayan, ağ kullanmayan istemci."""

    def __init__(self, cevap: str | None = None, hata: Exception | None = None):
        self.cevap = cevap
        self.hata = hata
        self.cagri = 0
        #: Son çağrıda modele giden istem — sıralama testi bunu okur.
        self.son_user = ""

    def generate_json(self, system: str, user: str, schema: dict) -> dict:
        self.cagri += 1
        self.son_user = user
        if self.hata is not None:
            raise self.hata
        return {"cevap": self.cevap}


class SahteLLM:
    def __init__(self, istemci: SahteIstemci | None):
        self.client = istemci

    @property
    def available(self) -> bool:
        return self.client is not None


class TestSayiAyiklama(unittest.TestCase):
    def test_cumle_sonu_noktasi_ondalik_sanilmaz(self) -> None:
        self.assertEqual(sayilari_ayikla("(%1,79)."), ["1,79"])

    def test_tr_binlik_ayirici_korunur(self) -> None:
        self.assertEqual(sayilari_ayikla("1.500,00 TRY masraf"), ["1.500,00"])


class TestDogrulamaKapisi(unittest.TestCase):
    """Kapı, saf bir fonksiyon olarak — LLM'siz."""

    def test_temiz_yeniden_ifade_gecer(self) -> None:
        aday = "Kuveyt Türk, %1,79 ile en düşük kâr payı oranını sunuyor."
        self.assertIsNone(_sozellestirme_gecerli(SABLON, aday))

    def test_yuvarlanan_sayi_reddedilir(self) -> None:
        aday = "Kuveyt Türk yaklaşık %1,8 ile en düşük kâr payı oranına sahip."
        self.assertIsNotNone(_sozellestirme_gecerli(SABLON, aday))

    def test_uydurulan_sayi_reddedilir(self) -> None:
        aday = ("Kuveyt Türk %1,79 kâr payı oranıyla 120 ay vade sunuyor.")
        gerekce = _sozellestirme_gecerli(SABLON, aday)
        self.assertIsNotNone(gerekce)
        self.assertIn("120", gerekce)

    def test_kaybolan_sayi_reddedilir(self) -> None:
        aday = "En düşük kâr payı oranı Kuveyt Türk'te."
        self.assertIsNotNone(_sozellestirme_gecerli(SABLON, aday))

    def test_eklenen_banka_reddedilir(self) -> None:
        aday = ("Kuveyt Türk %1,79 ile en düşük; Albaraka Türk de yakın bir "
                "oran sunuyor.")
        gerekce = _sozellestirme_gecerli(SABLON, aday)
        self.assertIsNotNone(gerekce)
        self.assertIn("albaraka", gerekce)

    def test_kaybolan_banka_reddedilir(self) -> None:
        aday = "En düşük kâr payı oranı %1,79 olarak görünüyor."
        self.assertIsNotNone(_sozellestirme_gecerli(SABLON, aday))

    def test_bos_cikti_reddedilir(self) -> None:
        for kotu in ("", "   ", None):
            with self.subTest(kotu=kotu):
                self.assertIsNotNone(_sozellestirme_gecerli(SABLON, kotu))

    def test_asiri_uzun_cikti_reddedilir(self) -> None:
        aday = "Kuveyt Türk %1,79 ile en düşük. " * 40
        self.assertIsNotNone(_sozellestirme_gecerli(SABLON, aday))


class TestUctanUca(unittest.TestCase):
    def setUp(self) -> None:
        self.repo = Repository(":memory:")
        for slug, text in [
            ("kuveyt-turk", "Konut finansmanında kâr payı oranı %1,79."),
            ("albaraka", "Konut finansmanı kâr payı oranı %2,49."),
        ]:
            self.repo.insert_campaign(
                build_campaign(text, bank_slug=slug,
                               campaign_type="Konut Finansmanı"))

    def tearDown(self) -> None:
        self.repo.close()

    def _sor(self, llm) -> object:
        bot = Chatbot(self.repo, llm=llm)
        return bot.ask("Hangi bankada en düşük kâr payı oranı var?")

    def test_llm_yokken_sablon_aynen_surer(self) -> None:
        a = self._sor(None)
        self.assertFalse(a.verbalize["attempted"])
        self.assertIn("en düşük kâr payı oranı", a.text)

    def test_temiz_cikti_uygulanir(self) -> None:
        istemci = SahteIstemci(
            "Kuveyt Türk, %1,79 ile en düşük kâr payı oranını sunan banka.")
        a = self._sor(SahteLLM(istemci))
        self.assertTrue(a.verbalize["applied"])
        self.assertIn("sunan banka", a.text)
        self.assertEqual(istemci.cagri, 1)

    def test_bozuk_cikti_sablona_duser(self) -> None:
        """Kasıtlı bozuk çıktı: uydurulmuş oran + eklenmiş banka."""
        a = self._sor(SahteLLM(SahteIstemci(
            "Kuveyt Türk %1,50 ile en düşük, Albaraka Türk %2,10 ile ikinci.")))
        self.assertTrue(a.verbalize["attempted"])
        self.assertFalse(a.verbalize["applied"])
        self.assertIn("1,79", a.text)
        self.assertNotIn("1,50", a.text)

    def test_zaman_asiminda_sablona_duser(self) -> None:
        """Yavaş LLM cevabı GECİKTİREMEZ — süre dolunca şablon basılır."""
        class Yavas(SahteIstemci):
            def generate_json(self, system, user, schema):
                time.sleep(2.0)
                return {"cevap": "gecikmiş"}

        eski = os.environ.get("CHAT_SOZELLESTIRME_SANIYE")
        os.environ["CHAT_SOZELLESTIRME_SANIYE"] = "0.2"
        try:
            a = self._sor(SahteLLM(Yavas()))
        finally:
            if eski is None:
                os.environ.pop("CHAT_SOZELLESTIRME_SANIYE", None)
            else:
                os.environ["CHAT_SOZELLESTIRME_SANIYE"] = eski
        self.assertFalse(a.verbalize["applied"])
        self.assertEqual(a.verbalize["reason"], "zaman aşımı")
        self.assertIn("1,79", a.text)

    def test_anahtar_kapaliyken_hic_denenmez(self) -> None:
        istemci = SahteIstemci("her neyse")
        os.environ["CHAT_SOZELLESTIRME"] = "0"
        try:
            a = self._sor(SahteLLM(istemci))
        finally:
            os.environ.pop("CHAT_SOZELLESTIRME", None)
        self.assertFalse(a.verbalize["attempted"])
        self.assertEqual(istemci.cagri, 0)

    def test_liste_cevabi_sozellestirilmez(self) -> None:
        """Çok satırlı liste paragrafa çevrilirse kıyas işlevini kaybeder."""
        istemci = SahteIstemci("her neyse")
        bot = Chatbot(self.repo, llm=SahteLLM(istemci))
        a = bot.ask("Konut finansmanı kâr payı oranlarını listele")
        self.assertEqual(a.handler, "structured")
        self.assertFalse(a.verbalize["attempted"])
        self.assertEqual(istemci.cagri, 0)

    def test_llm_hatasi_sablona_duser(self) -> None:
        a = self._sor(SahteLLM(SahteIstemci(hata=RuntimeError("bağlantı yok"))))
        self.assertFalse(a.verbalize["applied"])
        self.assertIn("1,79", a.text)

    def test_feragatname_sozellestirmeden_SONRA_eklenir(self) -> None:
        """Sözelleştirme güvenlik notunu YUTAMAZ.

        LLM'e giden metin, `guard_output` notları eklemeden önceki çıplak
        gövdedir; notlar sonradan eklenir. Bu sıra bozulursa oran içeren bir
        cevap garanti feragatnamesi olmadan ekrana çıkabilirdi.
        """
        istemci = SahteIstemci(
            "Kuveyt Türk, %1,79 ile en düşük kâr payı oranını sunuyor.")
        a = self._sor(SahteLLM(istemci))
        self.assertTrue(a.verbalize["applied"])
        self.assertIn("garanti", a.text.lower())
        # LLM'e giden metinde feragatname YOKTU:
        self.assertNotIn("garanti", istemci.son_user.lower())

    def test_llm_yasak_terim_uretse_bile_post_filtre_yakalar(self) -> None:
        """Sözelleştirme KAPI 1'i atlatamaz.

        Kapı, sayı ve banka kümesi bozulmadığı için bu çıktıyı geçirir; ama
        `sanitize_output` yasak terimi yeniden yazar.
        """
        a = self._sor(SahteLLM(SahteIstemci(
            "Kuveyt Türk %1,79 faiz oranıyla en düşük seçenek.")))
        self.assertTrue(a.verbalize["applied"])
        self.assertNotIn("faiz oranı", a.text)
        self.assertTrue(a.safety_report.violations)


if __name__ == "__main__":
    unittest.main()
