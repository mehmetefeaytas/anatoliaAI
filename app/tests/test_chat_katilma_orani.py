"""Katılma hesabı oranı yolu — soru tanıma, iki büyüklük, süzgeçler, kaynak.

İlgili: ../src/chatbot/katilma_orani.py
        ../scripts/tkbb_guncel_hasat.py (veriyi üreten hasat)

Bu testler AĞSIZDIR: kayıtlar doğrudan enjekte edilir. Sebep, hasat ucunun
(TKBB Veri Peteği) her koşumda erişilebilir olmasına GÜVENİLMEMESİ — testin
kırmızıya dönmesi kodun bozulduğu anlamına gelmeli, ağın koptuğu anlamına
gelmemeli.
"""

from __future__ import annotations

import json
import unittest

from src.chatbot.katilma_orani import (
    katilma_cevabi,
    katilma_sorusu_mu,
    kayitlari_yukle,
)


def _k(slug: str, ad: str, oran: float, *, ay: int = 1, para: str = "TRY",
       buyukluk: str = "getiri") -> dict:
    return {"bank_slug": slug, "bank_name": ad, "kind": "katilma",
            "rapor": "dagitilan_kar_payi" if buyukluk == "getiri"
                     else "kar_paylasim",
            "buyukluk": buyukluk, "product_name": "Katılma Hesabı",
            "currency": para, "term_months": ay, "period_date": "2026-08-24",
            "annual_rate": oran, "source_url": "https://tkbb.org.tr/x",
            "collected_at": "2026-08-24T00:00:00+00:00",
            "method": "tkbb-veripetegi"}


ORNEK = (
    _k("tom-katilim", "T.O.M. Katılım Bankası A.Ş.", 42.79),
    _k("hayat-finans", "Hayat Finans Katılım Bankası A.Ş.", 41.28, ay=6),
    _k("albaraka", "Albaraka Türk Katılım Bankası A.Ş.", 40.85, ay=12),
    _k("albaraka", "Albaraka Türk Katılım Bankası A.Ş.", 31.35, ay=1),
    _k("albaraka", "Albaraka Türk Katılım Bankası A.Ş.", 0.93, ay=1,
       para="USD"),
    _k("turkiye-finans", "Türkiye Finans Katılım Bankası A.Ş.", 98.0,
       buyukluk="pay"),
    _k("albaraka", "Albaraka Türk Katılım Bankası A.Ş.", 90.0,
       buyukluk="pay"),
)


class TestSoruTanima(unittest.TestCase):
    def test_katilma_orani_sorusu_taninir(self):
        for s in ("Katılım hesabında en iyi kar payı oranını hangi banka veriyor",
                  "katılma hesabı getirisi en yüksek hangi bankada",
                  "vadeli hesap kâr payı oranları"):
            with self.subTest(s=s):
                self.assertTrue(katilma_sorusu_mu(s))

    def test_alan_sorusu_CALINMAZ(self):
        """Ürün/alan soruları yapısal sorgu yoluna gitmek ZORUNDA.

        Hesap izi olmadan bu yol devreye girerse "konut finansmanı kâr payı
        oranı" gibi sorular kaynaklı DEĞER yerine katılma sıralaması alır.
        """
        for s in ("Hangi bankada en düşük konut finansmanı var",
                  "Kuveyt Türk kâr payı oranı nedir",
                  "taşıt finansmanı oranları"):
            with self.subTest(s=s):
                self.assertFalse(katilma_sorusu_mu(s))

    def test_oran_izi_olmadan_taninmaz(self):
        """"Katılma hesabı ne demek" bir TANIM sorusudur; terminoloji yolunun."""
        self.assertFalse(katilma_sorusu_mu("katılma hesabı ne demek"))
        self.assertFalse(katilma_sorusu_mu("katılım hesabı nedir"))

    def test_bos_soru(self):
        for s in (None, "", "   "):
            self.assertFalse(katilma_sorusu_mu(s))


class TestIkiBuyukluk(unittest.TestCase):
    def test_varsayilan_getiridir(self):
        c = katilma_cevabi("katılma hesabı en iyi kâr payı oranı",
                           kayitlar=ORNEK)
        self.assertIn("gerçekleşen yıllık getiri", c)
        self.assertIn("T.O.M.", c)
        self.assertIn("42.79", c)

    def test_paylasim_sorulursa_pay_siralanir(self):
        c = katilma_cevabi("katılma hesabı paylaşım oranı en yüksek",
                           kayitlar=ORNEK)
        self.assertIn("katılımcıya düşen pay", c)
        self.assertIn("Türkiye Finans", c)
        self.assertIn("98.00", c)

    def test_pay_cevabinda_bolusum_uyarisi_var(self):
        """%90'lık bir pay, %42'lik getiriyle karıştırılmamalı."""
        c = katilma_cevabi("katılma hesabı kâra katılma oranı",
                           kayitlar=ORNEK)
        self.assertIn("bölüşüm", c)
        self.assertIn("kazancın kendisi değildir", c)

    def test_getiri_ve_pay_ayni_tabloda_YARISMAZ(self):
        """Ölçülmüş tuzak: pay sayısal olarak getiriden büyüktür."""
        c = katilma_cevabi("katılma hesabı en iyi kâr payı oranı",
                           kayitlar=ORNEK)
        self.assertNotIn("98.00", c)   # pay satırı getiri tablosuna giremez
        self.assertNotIn("90.00", c)


class TestSuzgecler(unittest.TestCase):
    def test_vade_suzgeci(self):
        c = katilma_cevabi("katılma hesabı 6 ay kâr payı oranı",
                           kayitlar=ORNEK)
        self.assertIn("6 ay vade", c)
        self.assertIn("Hayat Finans", c)
        self.assertNotIn("42.79", c)   # 1 aylık TOM satırı elenmiş olmalı

    def test_para_birimi_suzgeci(self):
        c = katilma_cevabi("katılma hesabı dolar kâr payı oranı",
                           kayitlar=ORNEK)
        self.assertIn("dolar", c)
        self.assertIn("0.93", c)
        self.assertNotIn("42.79", c)

    def test_banka_basina_en_iyi_satir_ve_vade_YAZILIR(self):
        """Vade gizlenirse farklı vadeler aynı kolonda kıyaslanmış olurdu."""
        c = katilma_cevabi("katılma hesabı en iyi kâr payı oranı",
                           kayitlar=ORNEK)
        # Albaraka iki TL getiri satırı taşıyor (31,35 ve 40,85) → yalnız en iyisi
        self.assertIn("40.85", c)
        self.assertNotIn("31.35", c)
        self.assertIn("| 12 ay |", c)


class TestKaynakVeYokluk(unittest.TestCase):
    def test_kaynak_satiri_KOSULSUZ(self):
        c = katilma_cevabi("katılma hesabı kâr payı oranı", kayitlar=ORNEK)
        self.assertIn("_Kaynak:_", c)
        self.assertIn("TKBB", c)

    def test_donem_ve_garanti_uyarisi_basilir(self):
        c = katilma_cevabi("katılma hesabı kâr payı oranı", kayitlar=ORNEK)
        self.assertIn("2026-08-24", c)
        self.assertIn("garanti edilemez", c)

    def test_veri_yoksa_None(self):
        self.assertIsNone(katilma_cevabi("katılma hesabı kâr payı oranı",
                                         kayitlar=()))

    def test_eslesen_kayit_yoksa_None(self):
        """Altın sorulur, altın verisi yoktur → uydurma yerine None."""
        self.assertIsNone(katilma_cevabi("katılma hesabı altın kâr payı oranı",
                                         kayitlar=ORNEK))

    def test_alan_sorusuna_None(self):
        self.assertIsNone(katilma_cevabi("Hangi bankada en düşük konut "
                                         "finansmanı var", kayitlar=ORNEK))


class TestYukleyici(unittest.TestCase):
    def test_bozuk_satir_dosyayi_iptal_ETMEZ(self):
        """Tek satırlık bozulma tüm bankayı görünmez yapmamalı."""
        import pathlib
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            p = pathlib.Path(d) / "albaraka" / "rates"
            p.mkdir(parents=True)
            (p / "tkbb-guncel.jsonl").write_text(
                json.dumps(ORNEK[0], ensure_ascii=False) + "\n"
                "{bozuk json\n"
                + json.dumps(ORNEK[1], ensure_ascii=False) + "\n",
                encoding="utf-8")
            k = kayitlari_yukle(pathlib.Path(d))
        self.assertEqual(len(k), 2)

    def test_dizin_yoksa_bos_demet(self):
        import pathlib
        self.assertEqual(kayitlari_yukle(pathlib.Path("/olmayan/dizin/xyz")), ())


class TestBotEntegrasyonu(unittest.TestCase):
    def test_bot_katilma_handlerina_yonlendirir(self):
        import pathlib

        from src.chatbot.bot import Chatbot
        from src.db.repository import Repository
        db = pathlib.Path("data/demo.db")
        if not db.exists():
            self.skipTest("data/demo.db yok")
        bot = Chatbot(Repository(str(db)))
        a = bot.ask("Katılım hesabında en iyi kar payı oranını hangi banka veriyor")
        self.assertEqual(a.handler, "katilma_orani")
        self.assertIn("Katılma hesabı", a.text)
        self.assertIn("TKBB", a.text)

    def test_bot_terminolojiyi_BOZMAZ(self):
        import pathlib

        from src.chatbot.bot import Chatbot
        from src.db.repository import Repository
        db = pathlib.Path("data/demo.db")
        if not db.exists():
            self.skipTest("data/demo.db yok")
        bot = Chatbot(Repository(str(db)))
        self.assertEqual(bot.ask("Murabaha ne demek").handler, "terminoloji")


def _s(slug, ad, seg, oran, *, ay=1, para="TRY"):
    """Segment kaydı (bankanın kendi yayınından)."""
    return {"bank_slug": slug, "bank_name": ad, "kind": "katilma",
            "buyukluk": "pay", "segment": seg, "currency": para,
            "term_months": ay, "term_label": f"{ay} Aylık",
            "annual_rate": oran, "bank_share": 100 - oran,
            "toplam": 100.0, "toplam_tutarsiz": False,
            "source_url": "https://www.kuveytturk.com.tr/x",
            "method": "banka-pdf"}


SEGMENTLER = (
    _s("kuveyt-turk", None, "Klasik Hesabı", 85.0),
    _s("kuveyt-turk", None, "Gümüş Hesabı", 87.0),
    _s("kuveyt-turk", None, "Platin+ Hesabı", 94.0),
    _s("kuveyt-turk", None, "Klasik Hesabı", 75.0, ay=12),
)


class TestSegmentAyrimi(unittest.TestCase):
    """Merkezî veri tek oran veriyor, banka segment bazında farklı oran uyguluyor.

    Ölçüldü (2026-08-24): TKBB Kuveyt Türk TL paylaşımını 92/93/95/95 diye
    yayınlıyor; bankanın PDF'i Klasik için 85/86/88/88. Yani Klasik hesap
    müşterisi merkezî veride görünmeyen bir orana tabi.
    """

    def test_segment_sorusu_taninir(self):
        from src.chatbot.katilma_orani import segment_sorusu_mu
        for s in ("katılma hesabı platin segment paylaşım oranı",
                  "kuveyt türk klasik hesap katılma oranı",
                  "gümüş hesap kâr paylaşımı"):
            with self.subTest(s=s):
                self.assertTrue(segment_sorusu_mu(s))

    def test_segment_izi_olmayan_soru(self):
        from src.chatbot.katilma_orani import segment_sorusu_mu
        self.assertFalse(segment_sorusu_mu(
            "katılma hesabında en iyi kâr payı oranı"))

    def test_segment_cevabi_AYNI_VADEDE_kiyaslar(self):
        """Vade söylenmemişse tek vadeye inilmeli: farklı vadeler yan yana
        gelirse fark segmentten mi vadeden mi geldiği anlaşılmaz (§17)."""
        from src.chatbot.katilma_orani import _segment_cevabi
        c = _segment_cevabi("katılma hesabı segment paylaşım oranı",
                            kayitlar=SEGMENTLER)
        self.assertIn("1 ay vade", c)
        self.assertIn("85.00", c)
        self.assertIn("94.00", c)
        self.assertNotIn("75.00", c)   # 12 aylık satır aynı tabloya girmemeli

    def test_segment_cevabi_bolusum_uyarisi_tasir(self):
        from src.chatbot.katilma_orani import _segment_cevabi
        c = _segment_cevabi("platin segment oranı", kayitlar=SEGMENTLER)
        self.assertIn("bölüşüm", c)
        self.assertIn("_Kaynak:_", c)

    def test_slug_yerine_OKUNABILIR_ad(self):
        """Banka PDF'i `bank_name` taşımıyor; cevapta slug basılmamalı."""
        from src.chatbot.katilma_orani import _segment_cevabi
        c = _segment_cevabi("platin segment oranı", kayitlar=SEGMENTLER)
        self.assertIn("Kuveyt Türk", c)
        self.assertNotIn("kuveyt-turk", c)

    def test_segment_verisi_yoksa_None(self):
        from src.chatbot.katilma_orani import _segment_cevabi
        self.assertIsNone(_segment_cevabi("platin segment oranı", kayitlar=()))

    def test_KAYNAK_tutarsizligi_gosterilir(self):
        """PDF'te pay+banka payı 110 eden bir satır var; gizlenmez (§4)."""
        from src.chatbot.katilma_orani import _segment_cevabi
        bozuk = dict(SEGMENTLER[0])
        bozuk.update({"annual_rate": 91.0, "bank_share": 19.0,
                      "toplam": 110.0, "toplam_tutarsiz": True})
        c = _segment_cevabi("segment oranı", kayitlar=(bozuk,))
        self.assertIn("tutarsız", c.lower())
        self.assertIn("110", c)

    def test_ana_cevapta_segment_UYARISI(self):
        """Uyarı olmadan cevap, küçük bakiyeli kullanıcıya erişemeyeceği bir
        oranı vaat ediyordu."""
        import pathlib

        from src.chatbot.katilma_orani import katilma_cevabi
        if not list(pathlib.Path("data/raw").glob(
                "*/rates/kt-paylasim-pdf.jsonl")):
            self.skipTest("segment verisi yok")
        c = katilma_cevabi("katılma hesabında en iyi kâr payı oranı")
        self.assertIn("tek temsili", c)
        self.assertIn("segment", c.lower())


if __name__ == "__main__":
    unittest.main()
