"""Devralma kuralı — YENİ sorunun kendi sinyali her zaman kazanır.

İlgili: ../src/chatbot/router.py (`_devral`, `_TUR_SOZCUK_DESENLERI`)
        ../src/chatbot/bot.py (ask(question, context))
        test_chat_baglam.py (bağlam kanalının izin listesi ve enjeksiyon yüzeyi)

## Neden ayrı bir dosya

`test_chat_baglam.py` bağlamın TAŞINABİLİRLİĞİNİ ve güvenliğini kapıda tutar:
kanala ne girebilir, hangi kapı bağlamla açılamaz. Buradaki testler farklı bir
şeyi kapıda tutar: bağlamın ne zaman KULLANILMAYACAĞINI.

Kusur tarayıcıda görüldü. Üç turluk bir taşıt oturumunun ardından:

    — "Yeni müşterilere verilen EV finansman tutarı ne kadar?"
    — "önceki sorudan: kampanya türü Taşıt Finansmanı / asgari vade 36 ay /
       Vakıf Katılım → Taşıt Finansmanı — finansman tutarı …"

Kullanıcı EV sordu, sistem TAŞIT cevapladı. Sebep iki taneydi:

  1. Yalın "ev" hiçbir kampanya türü ipucuna eşlenmiyordu (`_FOLDED_TYPE_MAP`
     içinde "ev alım" vardı, yalın "ev" yoktu).
  2. Devralma ölçütü "alan + niyet"ti; niyeti olmayan ama süzgeci olan soru
     "eksik" sayılıyor ve üç ayrı turdan üç süzgeç birden yapışıyordu.

Aşağıdaki ölçüm 12 diyalog / 29 turluk temsilî küme üzerinde koştu
(`data/demo.db`): çelişkili devralma 4 → 0, gereksiz devralma 8 → 0. Aynı
kümede meşru devralmalar (özne ve kalıp) korundu.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.chatbot.bot import Chatbot
from src.chatbot.router import ChatContext, baglam_birlestir, route
from src.db.repository import Repository
from src.extraction.reconcile import build_campaign

SEED = [
    ("kuveyt-turk", "Konut finansmanında kâr payı oranı %1,79, 120 ay vade, "
                    "finansman tutarı 1.250.000 TL.", "Konut Finansmanı"),
    ("albaraka", "Konut finansmanı kâr payı oranı %2,49, 96 ay vade, "
                 "finansman tutarı 900.000 TL.", "Konut Finansmanı"),
    ("vakif-katilim", "Taşıt finansmanı kâr payı %1,99, 48 ay vade, "
                      "finansman tutarı 400.000 TL.", "Taşıt Finansmanı"),
    ("turkiye-finans", "Taşıt finansmanında 36 ay vade, finansman tutarı "
                       "500.000 TL, masrafsız.", "Taşıt Finansmanı"),
]


def seed(repo: Repository) -> None:
    for slug, text, ctype in SEED:
        repo.insert_campaign(build_campaign(text, bank_slug=slug,
                                            campaign_type=ctype))


class TestTurIpucu(unittest.TestCase):
    """Günlük kelimeler ürün ailesine eşlenir — "ev" dâhil."""

    def test_yalin_ev_konut_finansmanina_eslenir(self) -> None:
        for soru in ("Ev finansman tutarı ne kadar?",
                     "Evim için en yüksek finansman tutarı nedir?",
                     "Ev kredisinde vade en fazla kaç ay?",
                     "Evden ev alırken kâr payı oranı nedir?",
                     "Mesken alımında finansman tutarı ne kadar?"):
            with self.subTest(soru=soru):
                self.assertEqual(route(soru).filters.get("campaign_type"),
                                 "Konut Finansmanı")

    def test_ev_ALT_DIZE_olarak_eslesmez(self) -> None:
        """"evrak", "seviye", "güvence" Konut Finansmanı değildir.

        Bu, kuralın en kolay bozulacağı yer: "ev" ipucunu alt dize olarak
        eklemek, katlanmış metinde onlarca sözcüğün içine düşer.
        """
        for soru in ("Gerekli evraklar neler?",
                     "Kâr payı seviyesi nedir?",
                     "Güvence bedeli ne kadar?",
                     "Devlet destekli kampanya var mı?"):
            with self.subTest(soru=soru):
                self.assertIsNone(
                    route(soru).filters.get("campaign_type"),
                    "tür ipucu sözcüğün İÇİNDEN çıkarılmış")

    def test_daha_belirgin_tur_once_gelir(self) -> None:
        """"taşıt evrakları" Taşıt'tır; yalın "ev" deseni hiç denenmez."""
        self.assertEqual(
            route("Taşıt finansmanı evrakları için tahsis ücreti ne kadar?")
            .filters.get("campaign_type"), "Taşıt Finansmanı")


class TestKendiSinyaliKazanir(unittest.TestCase):
    """KURAL 1 — kendi başına yeterli soru HİÇBİR ŞEY devralmaz."""

    #: Kusurun görüldüğü oturumun bağlamı: üç ayrı turdan üç süzgeç.
    TASIT = ChatContext(field="kar_payi_orani", intent="list",
                        filters={"campaign_type": "Taşıt Finansmanı",
                                 "vade_ay_min": 36,
                                 "banks": ["vakif-katilim"]},
                        subject_banks=["vakif-katilim"])

    def test_ev_sorusu_tasit_baglamini_ezer(self) -> None:
        r = route("Yeni müşterilere verilen EV finansman tutarı ne kadar?",
                  self.TASIT)
        self.assertEqual(r.handler, "structured")
        self.assertEqual(r.field, "finansman_tutari")
        self.assertEqual(r.filters.get("campaign_type"), "Konut Finansmanı")
        self.assertNotIn("vade_ay_min", r.filters)
        self.assertNotIn("banks", r.filters)
        self.assertEqual(r.inherited, [], "kendi yeterli soru devraldı")

    def test_alan_ve_suzgec_yeterlidir_niyet_sart_degil(self) -> None:
        """Ölçüt "alan + niyet" değil, "alan + (niyet ya da süzgeç)".

        Eski ölçüt bu soruyu eksik sayıyor ve önceki turun vade eşiğini
        yapıştırıyordu.
        """
        r = route("Vakıf Katılım'ın taşıt kâr payı oranı nedir?", self.TASIT)
        self.assertEqual(r.inherited, [])
        self.assertNotIn("vade_ay_min", r.filters)

    def test_niyetli_soru_da_devralmaz(self) -> None:
        r = route("Araba almak için en yüksek finansman tutarı ne kadar?",
                  ChatContext(field="kar_payi_orani", intent="lowest",
                              filters={"campaign_type": "Konut Finansmanı"}))
        self.assertEqual(r.filters.get("campaign_type"), "Taşıt Finansmanı")
        self.assertEqual(r.inherited, [])


class TestTekGerekce(unittest.TestCase):
    """Bir turda ya ÖZNE ya KALIP devralınır; ikisi birden değil."""

    def test_yeni_alan_yalniz_ozneyi_devralir(self) -> None:
        """"Peki vade?" → önceki CEVABIN öznesi; önceki SORUNUN kapsamı değil.

        Yeni bir alan yeni bir sorudur: eski sorunun tür/vade süzgeci onun
        kapsamı değildir.
        """
        ctx = ChatContext(field="kar_payi_orani", intent="lowest",
                          filters={"campaign_type": "Konut Finansmanı",
                                   "vade_ay_min": 48},
                          subject_banks=["kuveyt-turk"])
        r = route("Peki vade?", ctx)
        self.assertEqual(r.field, "vade_ay")
        self.assertEqual(r.filters.get("banks"), ["kuveyt-turk"])
        self.assertNotIn("campaign_type", r.filters)
        self.assertNotIn("vade_ay_min", r.filters)
        self.assertEqual([d["kind"] for d in r.inherited], ["subject_banks"])

    def test_kalip_devralmada_kapsam_birlikte_tasinir(self) -> None:
        """"Peki ya Albaraka?" aynı sorudur; kapsamı da aynıdır."""
        ctx = ChatContext(field="kar_payi_orani", intent="lowest",
                          filters={"campaign_type": "Konut Finansmanı"})
        r = route("Peki ya Albaraka?", ctx)
        self.assertEqual(r.field, "kar_payi_orani")
        self.assertEqual(r.intent, "lowest")
        self.assertEqual(r.filters.get("campaign_type"), "Konut Finansmanı")
        self.assertEqual(r.filters.get("banks"), ["albaraka"])
        self.assertNotIn("subject_banks", [d["kind"] for d in r.inherited])

    def test_ozne_ve_suzgec_ayni_turda_karismaz(self) -> None:
        for soru in ("Peki vade?", "Peki tahsis ücreti?", "Peki ya Albaraka?"):
            with self.subTest(soru=soru):
                ctx = ChatContext(field="kar_payi_orani", intent="lowest",
                                  filters={"campaign_type": "Konut Finansmanı",
                                           "vade_ay_min": 48},
                                  subject_banks=["kuveyt-turk"])
                kinds = {d["kind"] for d in route(soru, ctx).inherited}
                self.assertFalse(
                    kinds & {"subject_banks"} and
                    {k for k in kinds if k.startswith("filter:")},
                    f"iki ayrı gerekçe karıştı: {kinds}")

    def test_ozne_yalniz_SON_turdan_gelir(self) -> None:
        """"Peki vade?" = "az önce söylediğin bankanın vadesi".

        Süzgeçler altı turluk pencereden birleşir; özne birleşmez. Son cevabın
        öznesi yoksa, kullanıcının o turda hiç anmadığı eski bir banka
        devralınmaz.
        """
        eski = {"field": "kar_payi_orani", "intent": "lowest", "filters": {},
                "subject_banks": ["vakif-katilim"]}
        son = {"field": "finansman_tutari", "intent": "list",
               "filters": {"campaign_type": "Konut Finansmanı"},
               "subject_banks": []}
        birlesik = baglam_birlestir([son, eski])
        self.assertEqual(birlesik.subject_banks, [])
        self.assertEqual(birlesik.filters.get("campaign_type"),
                         "Konut Finansmanı", "süzgeç penceresi daralmış")
        self.assertEqual(route("Peki vade?", birlesik).filters.get("banks"),
                         None)

    def test_son_turun_oznesi_devralinir(self) -> None:
        son = {"field": "kar_payi_orani", "intent": "lowest", "filters": {},
               "subject_banks": ["kuveyt-turk"]}
        birlesik = baglam_birlestir([son, {}])
        self.assertEqual(birlesik.subject_banks, ["kuveyt-turk"])
        self.assertEqual(route("Peki vade?", birlesik).filters.get("banks"),
                         ["kuveyt-turk"])

    def test_devralma_gorunur_kalir(self) -> None:
        """Devralınan her boyut Türkçe etiketiyle taşınır (arayüz rozeti)."""
        ctx = ChatContext(field="kar_payi_orani", intent="lowest",
                          subject_banks=["kuveyt-turk"])
        for d in route("Peki vade?", ctx).inherited:
            self.assertTrue(d.get("label"), f"etiketsiz devralma: {d}")


class TestUctanUcaDevralma(unittest.TestCase):
    """Tarayıcıda görülen akışın kendisi — dört tur."""

    def setUp(self) -> None:
        self.repo = Repository(":memory:")
        seed(self.repo)
        self.bot = Chatbot(self.repo)

    def tearDown(self) -> None:
        self.repo.close()

    def _konus(self, sorular: list[str]) -> list:
        gecmis: list[dict] = []
        cevaplar = []
        for s in sorular:
            a = self.bot.ask(s, baglam_birlestir(list(gecmis)))
            gecmis.insert(0, a.context)
            cevaplar.append(a)
        return cevaplar

    def test_tasit_oturumunun_ardindan_ev_sorusu(self) -> None:
        cevaplar = self._konus([
            "Taşıt finansmanında en yüksek finansman tutarı hangi bankada?",
            "36 ay ve üzeri vade veren taşıt kampanyaları",
            "Vakıf Katılım'ın taşıt kâr payı oranı nedir?",
            "Yeni müşterilere verilen EV finansman tutarı ne kadar?",
        ])
        son = cevaplar[-1]
        self.assertEqual(son.handler, "structured")
        self.assertEqual(son.field, "finansman_tutari")
        self.assertEqual(son.inherited, [])
        self.assertIn("Konut", son.text)
        self.assertNotIn("Taşıt", son.text)
        self.assertNotIn("vakif", son.text)

    def test_mesru_takip_sorusu_hala_calisir(self) -> None:
        """Kural sıkılaştı ama "Peki vade?" akışı kırılmadı."""
        cevaplar = self._konus([
            "Konut finansmanında en düşük kâr payı oranı hangi bankada?",
            "Peki vade?",
        ])
        self.assertEqual(cevaplar[1].handler, "structured")
        self.assertEqual(cevaplar[1].field, "vade_ay")
        self.assertIn("120", cevaplar[1].text)
        self.assertTrue(cevaplar[1].inherited)


if __name__ == "__main__":
    unittest.main()
