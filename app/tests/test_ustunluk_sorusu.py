"""ÜSTÜNLÜK sorusu — "en iyi / en uygun X hangi bankada?"

İlgili: ../src/chatbot/router.py (`_USTUNLUK_ISARETLERI`, `_ustunluk_niyeti`,
        `_URUN_ADI_TUTAR_RE`, `Route.ustunluk`)
        ../src/chatbot/structured.py (`_phrase_ustunluk_kiyasi`,
        `_avantaj_satirlari`, `_ustunluk_ailesi_sec`, `_ustunluk_basligi`)
        ../src/comparison/compare.py (`rank_advantageous_by_type`)
        ../src/chatbot/bot.py (`_kapsam_notu`)

## Bu testlerin varlık sebebi — ÖLÇÜLDÜ (2026-08-20, canlı sistem)

Jürinin gördüğü yüzeyde dört soru şu şekilde davranıyordu:

    "Hangi bankada en düşük konut finansmanı var"   -> structured/finansman_tutari
    "Bana en iyi ev finansmanı veren banka hangisi" -> RAG, alan None
    "Hangi banka en uygun konut finansmanı veriyor" -> RAG, alan None
    "En avantajlı ev finansmanı hangi bankada"      -> structured/finansman_tutari

Ekranda sonuç: TEK bankanın (Dünya Katılım) üç belgesi, üç pasajın ikisi
**İhtiyaç Finansmanı** — oysa soru KONUT'tu — ve değer kolonu boş.

## ÖLÇÜLMÜŞ TUZAK — bu dosyanın kilitlediği asıl şey

"en iyi"yi `_SUPERLATIVE_LOW`'a naif eklemek soruyu şu cevaba çeviriyordu:
`structured / finansman_tutari / lowest` -> "en düşük finansman tutarı:
Türkiye Emlak Katılım (100 TL)". Yani ikinci hata birinci hatanın birebir
aynısına dönüşüyordu. Sebep: `_FOLDED_SUP_FIELD_KEYWORDS` "finansman"ı
`finansman_tutari`'na eşliyor, ama "konut **finansmanı**"nda o sözcük ÜRÜN
ADININ parçasıdır, tutar talebi değil.

"En iyi" bir YÖN değil ÇOK BOYUTLU bir üstünlüktür; doğru hedef
`comparison.rank_advantageous_by_type()`.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.chatbot.bot import _VARSAYIM_NOTU_KALIBI, Chatbot, _kapsam_notu
from src.chatbot.router import BANK_DISPLAY, VARSAYILAN_KIYAS_ALANI, route
from src.chatbot.structured import answer
from src.db.repository import Repository
from src.extraction.reconcile import build_campaign

#: Dört bankalık konut finansmanı ailesi. `MIN_GROUP_SIZE = 3` olduğu için
#: bileşik sıralamanın GERÇEKTEN koşabildiği en küçük anlamlı popülasyon bu.
KONUT = [
    ("ziraat-katilim",
     "Konut finansmanında %2,89 kâr payı oranı ile 120 ay vadeye kadar "
     "finansman. Dosya masrafı alınmamaktadır."),
    ("albaraka",
     "Konut finansmanı kampanyasında %3,49 kâr payı oranı ile 180 ay vade "
     "sunulmaktadır. Dosya masrafı alınmamaktadır."),
    ("kuveyt-turk",
     "Konut finansmanında %3,99 kâr payı oranı, 96 ay vade ve 5.000 TL "
     "değerinde alışveriş çeki hediye."),
    ("vakif-katilim",
     "Konut finansmanı: %4,19 kâr payı oranı, 60 ay vade, 1.500 TL dosya "
     "masrafı alınır."),
]

#: Aynı bankaların İHTİYAÇ finansmanı kampanyaları. Kusurun kalbi buydu:
#: konut sorusuna ihtiyaç belgesi dönüyordu. Bu satırlar cevaba GİRMEMELİ.
IHTIYAC = [
    ("dunya-katilim",
     "İhtiyaç finansmanında %1,09 kâr payı oranı ile 36 ay vade."),
    ("hayat-finans",
     "İhtiyaç finansmanı %1,19 kâr payı oranı, 24 ay vade, masrafsız."),
    ("tom-katilim",
     "İhtiyaç finansmanı %1,29 kâr payı oranı ile 12 ay vade."),
]

#: Kusurun ölçüldüğü dört soru — hepsi aynı şeyi soruyor.
DORT_SORU = [
    "Hangi bankada en düşük konut finansmanı var",
    "Bana en iyi ev finansmanı veren banka hangisi",
    "Hangi banka en uygun konut finansmanı veriyor",
    "En avantajlı ev finansmanı hangi bankada",
]


def _depo() -> Repository:
    repo = Repository(":memory:")
    for slug, metin in KONUT:
        repo.upsert_bank(BANK_DISPLAY.get(slug, slug), slug)
        repo.insert_campaign(build_campaign(metin, bank_slug=slug,
                                            campaign_type="Konut Finansmanı"))
    for slug, metin in IHTIYAC:
        repo.upsert_bank(BANK_DISPLAY.get(slug, slug), slug)
        repo.insert_campaign(build_campaign(metin, bank_slug=slug,
                                            campaign_type="İhtiyaç Finansmanı"))
    return repo


class TestRouterUstunlukNiyeti(unittest.TestCase):
    """Dört sorunun dördü de yapısal ÜSTÜNLÜK dalına gitmeli."""

    def test_dort_soru_da_yapisal_ustunluk(self) -> None:
        for soru in DORT_SORU:
            with self.subTest(soru=soru):
                r = route(soru)
                self.assertEqual(r.handler, "structured")
                self.assertTrue(r.ustunluk,
                                "üstünlük bayrağı taşınmazsa cevap tek "
                                "boyutlu listeye düşer")
                self.assertTrue(r.alan_varsayildi)
                self.assertEqual(r.filters.get("campaign_type"),
                                 "Konut Finansmanı")

    def test_TUZAK_alan_finansman_tutarina_DUSMEZ(self) -> None:
        """Ölçülmüş tuzak: "konut finansmanı" bir tutar talebi DEĞİLDİR."""
        for soru in DORT_SORU:
            with self.subTest(soru=soru):
                self.assertEqual(route(soru).field, VARSAYILAN_KIYAS_ALANI)

    def test_yalin_finansman_sorusu_TUTAR_olarak_kalir(self) -> None:
        """Muafiyet dar: sözcük ürün adının parçası DEĞİLSE eşleme sürer."""
        r = route("Araba alımında en yüksek finansman kimde var?")
        self.assertEqual(r.field, "finansman_tutari")
        self.assertFalse(r.ustunluk)

    def test_KARSI_ORNEK_tek_bankali_soru_kiyasa_CEVRILMEZ(self) -> None:
        """Çıplak "hangisi" tek bankalı soruyu bankalar arası kıyas YAPMAZ.

        "Albaraka'nın en iyi kampanyası hangisi" iki üstünlük sinyalini birden
        taşır ("en iyi" + "hangisi") ama bir bankalar arası soru değildir:
        cevabı üstünlük dalına vermek, kullanıcının hiç sormadığı bankaları
        "daha avantajlı" diye ilan etmek olurdu.
        """
        r = route("Albaraka'nın en iyi kampanyası hangisi")
        self.assertFalse(r.ustunluk)
        self.assertEqual(r.filters.get("banks"), ["albaraka"])

    def test_karsi_ornek_en_uygun_da_ayni(self) -> None:
        for soru in ("Kuveyt Türk'ün en uygun konut finansmanı hangisi",
                     "Ziraat Katılım'da en iyi kampanya hangisi"):
            with self.subTest(soru=soru):
                self.assertFalse(route(soru).ustunluk)

    def test_ALAN_SOYLENMISSE_ustunluk_dali_calismaz(self) -> None:
        """Kullanıcının SÖYLEDİĞİ her zaman kazanır."""
        r = route("Hangi banka en uygun vadeyi veriyor")
        self.assertEqual(r.field, "vade_ay")
        self.assertFalse(r.ustunluk)

    def test_aciklama_sorusu_RAGDE_kalir(self) -> None:
        """Ürün adı geçen ama sıralama istemeyen soru yapısal yola GİTMEZ."""
        r = route("Taşıt finansmanı kampanyasına kimler başvurabilir?")
        self.assertEqual(r.handler, "rag")
        self.assertFalse(r.ustunluk)

    def test_iki_bankali_kiyas_dali_DEGISMEDI(self) -> None:
        """Adı geçen iki banka hâlâ karşı karşıya kıyas dalına gider."""
        r = route("Kuveyt Türk mü daha avantajlı, Albaraka mı?")
        self.assertFalse(r.ustunluk,
                         "iki bankalı soru bileşik skora değil, karşı karşıya "
                         "kıyasa gitmeli (daha dar ve daha kesin bir soru)")


class TestUstunlukCevabi(unittest.TestCase):
    """Cevap çok boyutlu, gerekçeli ve TÜR İÇİNDE olmalı."""

    def setUp(self) -> None:
        self.depo = _depo()
        self.addCleanup(self.depo.close)

    def _metin(self, soru: str) -> str:
        return answer(self.depo, route(soru)).text

    def test_en_avantajli_ilan_edilir(self) -> None:
        metin = self._metin(DORT_SORU[1])
        self.assertIn("Konut Finansmanı — en avantajlı:", metin)

    def test_her_boyut_CUNKU_ile_gerekcelendirilir(self) -> None:
        metin = self._metin(DORT_SORU[1])
        maddeler = [s for s in metin.splitlines() if s.startswith("- ")]
        self.assertGreaterEqual(len(maddeler), 2,
                                "tek maddelik bir 'çok boyutlu' cevap yok")
        gerekceli = [m for m in maddeler if "çünkü" in m]
        self.assertTrue(gerekceli, "hiçbir maddede 'çünkü' yok")
        for madde in maddeler:
            # Şartname s.13'ün son maddesi ("Ek ödül açısından ise C Bankası
            # … vermektedir") kazanan İLAN ETMEZ ve gerekçe de vermez: o
            # boyutta kıyas edilecek ikinci değer YOKTUR. Uydurma gerekçe
            # üretmek yerine tek taraflı bilgi verilir — kalıbın kendisi
            # `structured._boyut_bilgisi`'nde gerekçeli.
            self.assertTrue("çünkü" in madde or "açısından ise" in madde,
                            f"ne gerekçe ne tek-taraflı kalıp: {madde!r}")

    def test_kar_payi_kazanani_dogru_bankadir(self) -> None:
        """%2,89 en düşük orandır; kazanan Ziraat Katılım olmak zorunda."""
        metin = self._metin(DORT_SORU[2])
        satir = next(s for s in metin.splitlines()
                     if s.startswith("- Kâr payı oranı"))
        self.assertIn("Ziraat Katılım", satir)
        self.assertIn("%2,89", satir)

    def test_vade_kazanani_FARKLI_banka_olabilir(self) -> None:
        """Çok boyutluluğun anlamı: her boyutun kazananı ayrı olabilir."""
        metin = self._metin(DORT_SORU[2])
        satir = next(s for s in metin.splitlines() if s.startswith("- Vade"))
        self.assertIn("Albaraka", satir)
        self.assertIn("180 ay", satir)

    def test_URUN_AILESI_ICINDE_kalir_ve_SOYLER(self) -> None:
        metin = self._metin(DORT_SORU[3])
        self.assertIn("ürün ailesi içinde yapıldı", metin)
        self.assertNotIn("İhtiyaç Finansmanı", metin,
                         "konut sorusuna ihtiyaç finansmanı karışmamalı — "
                         "kusurun kalbi tam buydu")

    def test_YANLIS_AILEDEN_banka_kaynak_gosterilmez(self) -> None:
        rows = answer(self.depo, route(DORT_SORU[1])).rows
        aileler = {x.campaign_type for x in rows}
        self.assertEqual(aileler, {"Konut Finansmanı"})
        for x in rows:
            self.assertNotIn(x.bank, {"dunya-katilim", "hayat-finans",
                                      "tom-katilim"})

    def test_kaynaklarda_UC_FARKLI_banka(self) -> None:
        """Tek bankanın belgeleriyle cevaplanan bir kıyas, kıyas değildir."""
        for soru in DORT_SORU:
            with self.subTest(soru=soru):
                rows = answer(self.depo, route(soru)).rows
                self.assertGreaterEqual(len({x.bank for x in rows}), 3)

    def test_agirliklar_GORUNUR(self) -> None:
        """Bileşik skor kara kutu olamaz: ağırlıklar cevapta yazar."""
        metin = self._metin(DORT_SORU[0])
        self.assertIn("Ağırlıklar:", metin)
        self.assertIn("kâr payı oranı %40", metin)

    def test_varsayim_SOYLENIR(self) -> None:
        metin = self._metin(DORT_SORU[0])
        self.assertIn("Alan söylenmediği için", metin)

    def test_cok_boyutlu_bayragi_tasinir(self) -> None:
        """`bot.py` tek alanlı kapsam notunu bu bayrakla bastırır."""
        self.assertTrue(answer(self.depo, route(DORT_SORU[1])).cok_boyutlu)

    def test_kucuk_grup_SESSIZ_dusmez(self) -> None:
        """`MIN_GROUP_SIZE` yetmezse SEBEP yazılır, madde listesi yine gelir."""
        repo = Repository(":memory:")
        self.addCleanup(repo.close)
        for slug, metin in KONUT[:2]:
            repo.upsert_bank(BANK_DISPLAY.get(slug, slug), slug)
            repo.insert_campaign(
                build_campaign(metin, bank_slug=slug,
                               campaign_type="Konut Finansmanı"))
        metin = answer(repo, route(DORT_SORU[1])).text
        self.assertIn("YAPILMADI", metin)
        self.assertIn("en az 3", metin)
        self.assertIn("çünkü", metin, "boyut boyut kıyas yine üretilmeli")


class TestUctanUcaUstunluk(unittest.TestCase):
    """Kapılar + sözelleştirme kapalı yol: kullanıcının gördüğü metin."""

    def setUp(self) -> None:
        self.depo = _depo()
        self.addCleanup(self.depo.close)
        self.bot = Chatbot(self.depo)

    def test_dort_soru_da_cok_boyutlu_cevap_uretir(self) -> None:
        for soru in DORT_SORU:
            with self.subTest(soru=soru):
                a = self.bot.ask(soru)
                self.assertEqual(a.handler, "structured")
                self.assertIn("en avantajlı", a.text)
                self.assertGreaterEqual(
                    len({s["bank"] for s in a.sources}), 3)

    def test_tek_alanli_kapsam_notu_BASTIRILIR(self) -> None:
        """"Kıyas kâr payı oranı üzerindendir" notu burada YANLIŞ olurdu."""
        a = self.bot.ask(DORT_SORU[1])
        self.assertNotIn("«Daha avantajlı» tek bir sayıya indirgenemez",
                         a.text)


class TestKapsamNotuAlanFarkindaligi(unittest.TestCase):
    """Gevşek eşlemeyle seçilen alan KENDİ ADIYLA duyurulmalı."""

    def test_varsayilan_kiyas_alaninda_uzun_not(self) -> None:
        self.assertIn("kâr payı oranı", _kapsam_notu(VARSAYILAN_KIYAS_ALANI))

    def test_baska_alanda_O_ALANIN_adi_yazar(self) -> None:
        """`_KIYAS_KAPSAM_NOTU` burada basılırsa cevap YANLIŞ bilgi verir."""
        not_ = _kapsam_notu("finansman_tutari")
        self.assertIn("finansman tutarı", not_)
        self.assertEqual(
            not_, _VARSAYIM_NOTU_KALIBI.format(etiket="finansman tutarı"))

    def test_gevsek_esleme_dalinda_varsayim_gorunur(self) -> None:
        """Ölçülen kusur: varsayım yapılıyor ama kullanıcıya söylenmiyordu."""
        self.assertTrue(
            route("Araba alımında en yüksek finansman kimde var?")
            .alan_varsayildi)


if __name__ == "__main__":
    unittest.main()
