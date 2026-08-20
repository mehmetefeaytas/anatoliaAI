"""84 soruluk chatbot sınavının bıraktığı YEDİ kusur — her biri ayrı sınıfta.

İlgili: ../src/chatbot/safety.py     (KUSUR 1 — bileşik banka adı)
        ../src/chatbot/router.py     (KUSUR 1–6 — koşul/alan/tür/aile/katalog)
        ../src/chatbot/structured.py (KUSUR 2,4,7 — süzgeç, aile kıyası, etiket)
        ../src/chatbot/bot.py        (KUSUR 5 — banka kataloğu)
        ../src/extraction/rules/synonyms.py (KUSUR 3 — tür ipucu sözlüğü)
        CLAUDE.md §12 (katılma hesabı), §17 (adil kıyas), §19, §21

## Sınav

84 soru (kolay/orta/zor/tuzak, her kademede 21) canlı `/chat` üzerinden
koşturuldu; 74'ü geçti. Bu dosya kalan yedi kusurun HER BİRİ için hem POZİTİF
(kusur kapandı) hem KARŞI-ÖRNEK (kapatırken başka bir şey bozulmadı) testi
tutar. Karşı-örnekler isteğe bağlı değil: yedi düzeltmenin altısı bir
sözlüğü/deseni GENİŞLETİYOR ve genişletmenin bedeli her zaman yanlış
pozitiftir.

Testler mümkün olduğunca ROUTER düzeyinde (deterministik, deposuz) kurulur;
uçtan uca doğrulama gereken yerlerde bellekteki küçük bir depo tohumlanır.
Gerçek korpus (`data/demo.db`) BURADA kullanılmaz — testin bir veri
anlık görüntüsüne bağlanması, kusurun kendisinden daha kırılgan olurdu.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.chatbot import safety, structured
from src.chatbot.bot import Chatbot
from src.chatbot.router import (
    BANK_DISPLAY,
    KOSUL_COK_KOSULLU,
    KOSUL_MASRAF_YOK,
    KOSUL_SIFIR_ORAN,
    route,
)
from src.comparison.compare import BILINMEYEN_TUR
from src.db.repository import Repository
from src.extraction.reconcile import build_campaign
from src.extraction.rules.synonyms import TYPE_HINTS

# --------------------------------------------------------------------------- #
# Ortak tohum — küçük ve okunur; her sınıf ihtiyacı kadarını kullanır.
# --------------------------------------------------------------------------- #

SEED: list[tuple[str, str, str | None]] = [
    ("kuveyt-turk", "Konut finansmanında kâr payı oranı %1,89, 120 ay vade. "
                    "Dosya masrafı alınmaz.", "Konut Finansmanı"),
    ("albaraka", "Konut finansmanı kâr payı oranı %2,49, 96 ay vade.",
     "Konut Finansmanı"),
    ("turkiye-finans", "Taşıt finansmanında kâr payı oranı %2,95, 48 ay vade.",
     "Taşıt Finansmanı"),
    ("vakif-katilim", "Taşıt finansmanı kâr payı oranı %3,10, 36 ay vade.",
     "Taşıt Finansmanı"),
    ("ziraat-katilim", "Taşıt finansmanı kâr payı oranı %3,50, 24 ay vade.",
     "Taşıt Finansmanı"),
    # Kredi kartında vade farksız (kâr payı oranı %0) kampanya.
    ("tom-katilim", "Kredi kartı taksitlerinde kâr payı oranı %0, 12 ay vade.",
     "Kart"),
    ("turkiye-emlak-katilim",
     "Kredi kartı kampanyasında kâr payı oranı %0, 6 ay vade.", "Kart"),
    ("dunya-katilim", "Kredi kartında kâr payı oranı %2,75, 6 ay vade.",
     "Kart"),
    # Türü BİLİNMEYEN belge (campaign_type=None) — KUSUR 7 için.
    ("hayat-finans", "Kâr payı oranı %4,15, 18 ay vade.", None),
]


def _depo() -> Repository:
    repo = Repository(":memory:")
    for slug, metin, tur in SEED:
        repo.insert_campaign(build_campaign(metin, bank_slug=slug,
                                            campaign_type=tur))
    return repo


class _BotluTest(unittest.TestCase):
    """Tohumlanmış depo + chatbot; alt sınıflar `self.sor()` kullanır."""

    def setUp(self):
        self.repo = _depo()
        self.addCleanup(self.repo.close)
        self.bot = Chatbot(self.repo)

    def sor(self, soru: str):
        return self.bot.ask(soru)


# =========================================================================== #
# KUSUR 1 — konvansiyonel banka sorusu katılım bankası verisiyle cevaplanıyor
# =========================================================================== #

class Kusur1BilesikBankaAdi(unittest.TestCase):
    """"Akbank konut kredisi faizi ne?" → çekimserlik, veri DEĞİL.

    Ölçülen kusur: cevap `handler=structured` ile Kuveyt Türk ve Türkiye
    Finans'ın konut oranlarını KAYNAK GÖSTEREREK basıyordu. Kapı ateşlenmiyordu
    çünkü tek deseni "büyük harfli ad + AYRI banka sözcüğü"ydü ("XYZ Bankası")
    ve "Akbank" tek sözcük.
    """

    #: Korpusta OLMAYAN, bileşik yazılmış banka adları.
    TANINMAYAN = [
        "Akbank konut kredisi faizi ne?",
        "akbank konut kredisi faizi ne?",        # tamamen küçük harf
        "Denizbank masraf alıyor mu?",
        "Vakıfbank kâr payı oranı nedir?",       # Vakıf KATILIM ile karışmamalı
        "Garantibank vadesi kaç ay?",
    ]

    #: Eski desenin zaten yakaladıkları — bozulmamalı.
    ESKI_DESEN = [
        "XYZ Bankası konut finansmanı oranı ne?",
        "Anadolu Katılım Bankası'nın vadesi kaç ay?",
        "Falcon Katılım Bank masraf alıyor mu?",
        "Garanti Bankası kâr payı oranı nedir?",
    ]

    #: KARŞI-ÖRNEK — meşru varyantlar ve banka adı GEÇMEYEN genel sorular.
    KARSI_ORNEK = [
        "Kuveyt Türk'ün konut finansmanı kâr payı oranı nedir?",
        "KT'nin konut finansmanı oranı ne?",
        "Kuveytturk'ün vadesi kaç ay?",
        "T.O.M. Katılım'ın taksit sayısı nedir?",
        "Emlak Katılım kampanya koşulları neler?",
        "Tombank masraf alıyor mu?",             # tombank.com.tr — meşru varyant
        "Albarakabank oranı ne?",                # gerçek bankanın bileşiği
        "Hangi bankada en düşük oran var?",
        "En avantajlı konut finansmanı hangisi?",
        "Hangi bankalar var?",
        "Katılım Bankacılığı nedir?",            # büyük harfli ama JENERİK
        "Hangi bankada faiz yok?",
    ]

    def test_bilesik_taninmayan_ad_kapiyi_acar(self):
        for soru in self.TANINMAYAN:
            with self.subTest(soru=soru):
                self.assertTrue(safety.olasi_taniminayan_banka_adi(soru))

    def test_eski_desen_bozulmadi(self):
        for soru in self.ESKI_DESEN:
            with self.subTest(soru=soru):
                self.assertTrue(safety.olasi_taniminayan_banka_adi(soru))

    def test_karsi_ornek_kapiyi_acmaz(self):
        for soru in self.KARSI_ORNEK:
            with self.subTest(soru=soru):
                self.assertFalse(safety.olasi_taniminayan_banka_adi(soru))

    def test_jenerik_sozcuk_bilesik_sayilmaz(self):
        """"banka…" ile BAŞLAYAN her biçim jeneriktir, özel ad değil."""
        for sozcuk in ("banka", "bankasi", "bankaciligi", "bankacilik",
                       "bankamiz", "bankalar", "bank"):
            with self.subTest(sozcuk=sozcuk):
                self.assertFalse(safety._bilesik_banka_adi(sozcuk))

    def test_tombank_taninan_banka(self):
        self.assertEqual(safety.detect_banks("Tombank masraf alıyor mu?"),
                         ["tom-katilim"])


class Kusur1UctanUca(_BotluTest):
    """Akbank sorusu artık `safety` yolundan, banka LİSTESİYLE dönüyor."""

    def test_akbank_cekimser_kalir_ve_bankalari_listeler(self):
        cevap = self.sor("Akbank konut kredisi faizi ne?")
        self.assertEqual(cevap.handler, "safety")
        self.assertIn(safety.GATE_UNKNOWN_BANK, cevap.gates)
        self.assertEqual(cevap.sources, [])
        # Kaynaklı YANLIŞ cevabın izi kalmamalı: korpus bankalarının DEĞERİ
        # geçmemeli. Adları geçebilir — "tanıdığım bankalar" listesi bu.
        self.assertNotIn("%1,89", cevap.text)
        for ad in BANK_DISPLAY.values():
            self.assertIn(ad, cevap.text)

    def test_garanti_bankasi_cevabi_bozulmadi(self):
        """Görev bunu açıkça koruyor: garanti ilkesi notu + çekimserlik."""
        cevap = self.sor("Garanti Bankası kâr payı oranı nedir?")
        self.assertEqual(cevap.handler, "safety")
        self.assertIn(safety.GATE_UNKNOWN_BANK, cevap.gates)
        self.assertIn("garanti", cevap.text.lower())

    def test_mesru_banka_sorusu_hala_veri_dondurur(self):
        cevap = self.sor("Kuveyt Türk'ün konut finansmanı kâr payı oranı nedir?")
        self.assertEqual(cevap.handler, "structured")
        self.assertTrue(cevap.sources)


# =========================================================================== #
# KUSUR 2 — değer/koşul süzgeçleri sessizce yok sayılıyor
# =========================================================================== #

class Kusur2DegerKosulu(unittest.TestCase):
    """Router koşulu TANIR, süzgece çevirir ve alanını zorlar."""

    def test_sifir_oran_kosulu(self):
        for soru in ("%0 kâr payı olan kampanya var mı?",
                     "Sıfır kâr payı veren banka var mı?",
                     "Kâr payı oranı sıfır olan kampanya hangisi?"):
            with self.subTest(soru=soru):
                r = route(soru)
                self.assertEqual(r.kosul, KOSUL_SIFIR_ORAN)
                self.assertIs(r.filters.get("kar_payi_sifir"), True)
                self.assertEqual(r.field, "kar_payi_orani")

    def test_vade_farksiz_domain_karsiligi_kar_payi_sifir(self):
        """«Vade farksız» = kâr payı oranı %0 (CLAUDE.md §12 — vade farkı)."""
        for soru in ("Vade farksız taksit veren banka hangisi?",
                     "Taksit farkı olmayan kampanya var mı?",
                     "Vade farkı yok diyen banka hangisi?"):
            with self.subTest(soru=soru):
                r = route(soru)
                self.assertEqual(r.kosul, KOSUL_SIFIR_ORAN)
                # Soruda "vade"/"taksit" sözcüğü geçse bile alan koşulun
                # taşıyıcısıdır: sorulan şey vade SÜRESİ değil.
                self.assertEqual(r.field, "kar_payi_orani")

    def test_masraf_yok_kosulu(self):
        for soru in ("Dosya masrafı almayan bankalar hangileri?",
                     "Masrafsız konut finansmanı veren bankalar?",
                     "Ücret almayan banka var mı?"):
            with self.subTest(soru=soru):
                r = route(soru)
                self.assertEqual(r.kosul, KOSUL_MASRAF_YOK)
                self.assertIs(r.filters.get("masraf_yok"), True)
                self.assertEqual(r.field, "masraf_durumu")

    def test_iki_kosullu_soru_desteklenmedigini_bildirir(self):
        r = route("Kâr payı düşük ama masrafı yüksek olan banka var mı?")
        self.assertEqual(r.kosul, KOSUL_COK_KOSULLU)
        # Uygulanacak bir süzgeç YOK — uydurma bir daraltma yapılmaz.
        self.assertNotIn("kar_payi_sifir", r.filters)
        self.assertNotIn("masraf_yok", r.filters)

    def test_karsi_ornek_kosulsuz_sorular(self):
        """Sıradan sorular koşul ÜRETMEZ — aşırı tetikleme yok."""
        for soru in ("Hangi bankada en düşük kâr payı oranı var?",
                     "%10 indirim veren kampanya var mı?",
                     "Kâr payı oranı %0,5 olan banka hangisi?",
                     "Ziraat Katılım'da masraf alınıyor mu?",
                     "Türkiye Emlak Katılım'da dosya masrafı var mı?",
                     "36 ay ve üzeri vade veren bankalar hangileri?",
                     "Kuveyt Türk konut finansmanı oranı ve vadesi ne?"):
            with self.subTest(soru=soru):
                self.assertIsNone(route(soru).kosul)

    def test_sifir_deseni_ondalikli_orani_yakalamaz(self):
        """"%0,5" ve "%05" SIFIR DEĞİLDİR — desen rakam/ayıraç görürse susar."""
        for soru in ("%0,5 kâr payı veren banka?", "%05 oran var mı?",
                     "%0.9 oranlı kampanya?"):
            with self.subTest(soru=soru):
                self.assertIsNone(route(soru).kosul)


class Kusur2SuzgecUygulanir(unittest.TestCase):
    """Süzgeç GERÇEKTEN süzer; sıfır olmayan değer listeye girmez."""

    def test_sifir_oran_suzgeci(self):
        self.assertTrue(structured._sifir_oran_mi(0))
        self.assertTrue(structured._sifir_oran_mi(0.0))
        self.assertTrue(structured._sifir_oran_mi({"min": 0, "max": 0}))
        self.assertFalse(structured._sifir_oran_mi(3.99))
        self.assertFalse(structured._sifir_oran_mi(None))
        self.assertFalse(structured._sifir_oran_mi(False))
        # ARALIK sıfır sayılmaz: alt sınırı sıfır olan aralık "%0 kâr payı"
        # değildir (CLAUDE.md §17 — doğrudan kıyaslanamaz).
        self.assertFalse(structured._sifir_oran_mi({"min": 0, "max": 2.5}))

    def test_masraf_yok_suzgeci(self):
        self.assertTrue(structured._masraf_yok_mu({"has_fee": False}))
        self.assertTrue(structured._masraf_yok_mu({"value": 0,
                                                   "currency": "TRY"}))
        self.assertFalse(structured._masraf_yok_mu({"has_fee": True,
                                                    "amount": 1000}))
        # "Ücret var, tutarı bilinmiyor" SIFIR SAYILMAZ.
        self.assertFalse(structured._masraf_yok_mu({"has_fee": True,
                                                    "amount": None}))


class Kusur2UctanUca(_BotluTest):
    """Cevap koşulu SÖYLER; sıfır olmayan oran listede görünmez."""

    def test_sifir_oran_cevabi_yalniz_sifirlari_gosterir(self):
        cevap = self.sor("%0 kâr payı olan kampanya var mı?")
        self.assertEqual(cevap.handler, "structured")
        self.assertIn("Koşul UYGULANDI", cevap.text)
        self.assertIn("%0", cevap.text)
        for olmayan in ("%1,89", "%2,49", "%2,95", "%3,10", "%2,75"):
            self.assertNotIn(olmayan, cevap.text)

    def test_vade_farksiz_cevabi_eslemeyi_soyler(self):
        cevap = self.sor("Vade farksız taksit veren banka hangisi?")
        self.assertIn("Koşul UYGULANDI", cevap.text)
        self.assertIn("kâr payı oranı %0", cevap.text)

    def test_iki_kosullu_soru_desteklenmedigini_yazar(self):
        cevap = self.sor("Kâr payı düşük ama masrafı yüksek olan banka var mı?")
        self.assertIn("desteklemiyorum", cevap.text)
        # Koşul sessizce DÜŞMEDİ: cevap dağılım sunduğunu söylüyor.
        self.assertIn("DAĞILIM", cevap.text)


# =========================================================================== #
# KUSUR 3 — "katılma hesabı" yanlış ürün ailesine gidiyor
# =========================================================================== #

class Kusur3TurSozlugu(unittest.TestCase):
    """Katılma hesabı bir YATIRIM ÜRÜNÜ (CLAUDE.md §12, şartname §5.5)."""

    YATIRIM_SORULARI = [
        "En kârlı katılma hesabı hangi bankada?",
        "Katılım fonu veren banka hangisi?",
        "Altın hesabı olan bankalar hangileri?",
    ]

    def test_katilma_hesabi_yatirim_urunu(self):
        for soru in self.YATIRIM_SORULARI:
            with self.subTest(soru=soru):
                self.assertEqual(route(soru).filters.get("campaign_type"),
                                 "Yatırım Ürünü")

    def test_iki_sozluk_AYRISMIYOR(self):
        """Router sözlüğü ile `synonyms.TYPE_HINTS` aynı ifadeye aynı etiket.

        İki sözlük paralel yaşıyor ve KUSUR 3 tam bu ayrışmadan doğdu: çıkarım
        katmanı "katılma hesabı" → Yatırım Ürünü eşlemesini biliyordu, router
        bilmiyordu. Bu test ortak ifade kümesini kilitler.
        """
        from src.chatbot import router as R
        hint_etiketi: dict[str, str] = {}
        for etiket, ipuclari in TYPE_HINTS.items():
            for ipucu in ipuclari:
                hint_etiketi.setdefault(R._F(ipucu), etiket)
        ortak = 0
        for ipucu, etiket in R._FOLDED_TYPE_MAP.items():
            beklenen = hint_etiketi.get(ipucu)
            if beklenen is None:
                continue                     # yalnız router'da olan ipucu
            ortak += 1
            self.assertEqual(
                etiket, beklenen,
                f"'{ipucu}' iki sözlükte FARKLI etiket taşıyor: "
                f"router={etiket!r}, TYPE_HINTS={beklenen!r}")
        self.assertGreater(ortak, 5, "ortak ifade kümesi beklenmedik biçimde "
                                     "küçüldü — testin kendisi anlamsızlaştı")

    def test_katilma_hesabi_her_iki_sozlukte_yatirim(self):
        from src.chatbot import router as R
        self.assertEqual(R._FOLDED_TYPE_MAP[R._F("katılma hesabı")],
                         "Yatırım Ürünü")
        self.assertIn("katılma hesabı", TYPE_HINTS["Yatırım Ürünü"])

    def test_karsi_ornek_diger_aileler_bozulmadi(self):
        for soru, beklenen in (
            ("Konut finansmanı oranı nedir?", "Konut Finansmanı"),
            ("Taşıt finansmanı vadesi kaç ay?", "Taşıt Finansmanı"),
            ("İhtiyaç finansmanı tahsis ücreti ne kadar?",
             "İhtiyaç Finansmanı"),
            ("Kredi kartı taksit sayısı nedir?", "Kart"),
            ("Ev almak istiyorum, hangi banka en mantıklı?",
             "Konut Finansmanı"),
            ("Araba alacağım, en iyi taşıt finansmanı kimde?",
             "Taşıt Finansmanı"),
        ):
            with self.subTest(soru=soru):
                self.assertEqual(route(soru).filters.get("campaign_type"),
                                 beklenen)


# =========================================================================== #
# KUSUR 4 — ürün ailesi kıyası sessizce tek tarafa iniyor
# =========================================================================== #

class Kusur4AileKiyasi(unittest.TestCase):
    """Soru İKİ AİLEYİ kıyaslıyorsa süzgeç tek aileye İNMEZ."""

    def test_iki_aile_tanindi_ve_tur_suzgeci_dusuruldu(self):
        r = route("Hangisi daha avantajlı, konut mu taşıt finansmanı mı?")
        self.assertEqual(r.aile_kiyasi,
                         ["Konut Finansmanı", "Taşıt Finansmanı"])
        # Tür süzgeci DÜŞÜRÜLDÜ: cevap iki ailenin İKİSİNİ de gösterecek.
        self.assertNotIn("campaign_type", r.filters)

    def test_varyantlar(self):
        for soru in ("Konut finansmanı mı taşıt finansmanı mı daha avantajlı?",
                     "Kredi kartı mı ihtiyaç finansmanı mı daha uygun?",
                     "Konut finansmanı ile taşıt finansmanını karşılaştır"):
            with self.subTest(soru=soru):
                self.assertEqual(len(route(soru).aile_kiyasi), 2)

    def test_karsi_ornek_tek_aile_cok_ipucu(self):
        """Aynı aileyi iki isimle anan soru AİLE KIYASI DEĞİLDİR."""
        for soru in ("Araba alacağım, en iyi taşıt finansmanı kimde?",
                     "Ev almak istiyorum, en uygun konut finansmanı hangisi?",
                     "Otomobil için en iyi araç finansmanı hangi bankada?"):
            with self.subTest(soru=soru):
                self.assertEqual(route(soru).aile_kiyasi, [])

    def test_karsi_ornek_kiyas_niyeti_olmayan_soru(self):
        """İki aile geçse de KIYAS istenmiyorsa kapı kapalı."""
        r = route("Konut finansmanı ve taşıt finansmanı kampanyalarını listele")
        self.assertEqual(r.aile_kiyasi, [])

    def test_karsi_ornek_iki_banka_kiyasi_bozulmadi(self):
        r = route("Kuveyt Türk mü avantajlı Ziraat Katılım mı?")
        self.assertEqual(r.aile_kiyasi, [])
        self.assertEqual(len(r.filters.get("banks") or []), 2)


class Kusur4UctanUca(_BotluTest):
    """Cevap `_AILE_NOTU`'nu BASAR ve her ailenin kazananını gösterir."""

    def test_aile_kiyasi_cevabi(self):
        cevap = self.sor("Hangisi daha avantajlı, konut mu taşıt finansmanı mı?")
        self.assertEqual(cevap.handler, "structured")
        self.assertIn("ALTERNATİFİ DEĞİLDİR", cevap.text)
        self.assertIn("Konut Finansmanı", cevap.text)
        self.assertIn("Taşıt Finansmanı", cevap.text)
        self.assertIn("birbirinin alternatifi değildir", cevap.text)
        self.assertTrue(cevap.sources, "kaynaksız gövde KAPI 5'te silinirdi")


# =========================================================================== #
# KUSUR 5 — RAG'a düşüp alakasız belge getiren üç soru
# =========================================================================== #

class Kusur5KatalogSorusu(unittest.TestCase):
    def test_katalog_sorusu_tanindi(self):
        for soru in ("Hangi bankalar var?", "Hangi bankalar mevcut?",
                     "Banka listesi", "Tanıdığın bankalar hangileri?",
                     "Kaç banka var?"):
            with self.subTest(soru=soru):
                r = route(soru)
                self.assertEqual(r.handler, "katalog")
                self.assertTrue(r.katalog)

    def test_karsi_ornek_alan_sorusu_katalog_degil(self):
        """"Hangi banka…" ile başlayan ALAN sorusu kataloga DÜŞMEZ."""
        for soru in ("Hangi bankada en düşük kâr payı oranı var?",
                     "Hangi bankalar 36 ay vade veriyor?",
                     "Hangi bankalar kart kampanyası sunuyor?",
                     "Hangi banka en uygun konut finansmanı veriyor",
                     "Dosya masrafı almayan bankalar hangileri?"):
            with self.subTest(soru=soru):
                self.assertNotEqual(route(soru).handler, "katalog")


class Kusur5OlumsuzListeleme(unittest.TestCase):
    def test_olumsuz_yuklem_niyet_uretir(self):
        for soru in ("Dosya masrafı almayan bankalar hangileri?",
                     "Ücret almayan banka var mı?"):
            with self.subTest(soru=soru):
                r = route(soru)
                self.assertEqual(r.handler, "structured")
                self.assertEqual(r.intent, "list")

    def test_olumsuzluk_kosula_da_cevrildi(self):
        """Yalnız niyeti tanımak YANILTICI olurdu — koşul da uygulanmalı."""
        r = route("Dosya masrafı almayan bankalar hangileri?")
        self.assertEqual(r.kosul, KOSUL_MASRAF_YOK)


class Kusur5HedefKitle(unittest.TestCase):
    def test_hedef_kitle_alani_tanindi(self):
        for soru in ("Türkiye Finans hedef kitlesi kim?",
                     "Bu kampanya kime yönelik?",
                     "Kimler için geçerli bu kampanya?"):
            with self.subTest(soru=soru):
                self.assertEqual(route(soru).field, "hedef_kitle")

    def test_hedef_kitle_kodlari_turkceye_cevrilir(self):
        metin = structured._fmt_value("hedef_kitle",
                                      ["yeni_musteri", "belirli_segment"])
        self.assertIn("yeni müşteri", metin)
        self.assertIn("belirli müşteri segmenti", metin)
        self.assertNotIn("belirli_segment", metin)

    def test_tanimayan_kod_UYDURULMAZ(self):
        self.assertIn("bilinmeyen_kod",
                      structured._fmt_value("hedef_kitle", ["bilinmeyen_kod"]))


class Kusur5UctanUca(_BotluTest):
    def test_hangi_bankalar_var_katalog_cevabi(self):
        cevap = self.sor("Hangi bankalar var?")
        self.assertEqual(cevap.handler, "katalog")
        # Tohumdaki dokuz bankanın hepsi adıyla geçmeli.
        for slug, _m, _t in SEED:
            self.assertIn(BANK_DISPLAY[slug], cevap.text)
        self.assertIn("belge", cevap.text)
        # Çekimserlik kapısı bu cevabı SİLMEMELİ.
        self.assertNotIn("bulamadım", cevap.text)

    def test_katalog_otorite_kaynagini_BANKA_SAYMAZ(self):
        """TKBB gibi otorite kaynakları banka listesine GİRMEZ."""
        self.repo.upsert_bank("Türkiye Katılım Bankaları Birliği", "tkbb")
        cevap = self.sor("Hangi bankalar var?")
        self.assertNotIn("Katılım Bankaları Birliği", cevap.text)


# =========================================================================== #
# KUSUR 6 — yanlış alan eşlemesi ("indirim oranı" → kâr payı oranı)
# =========================================================================== #

class Kusur6AlanEslemesi(unittest.TestCase):
    def test_indirim_orani_kendi_alanina_gider(self):
        r = route("Albaraka indirim oranı nedir?")
        self.assertEqual(r.field, "indirim_orani")
        # Genel "oran" yedeği bastırıldı: `kar_payi_orani` LİSTEDE OLMAMALI,
        # yoksa çok-alanlı dal kullanıcının sormadığı alanı da basar.
        self.assertNotIn("kar_payi_orani", r.fields)

    def test_diger_alanlar_da_taniniyor(self):
        for soru, alan in (
            ("Kuveyt Türk ödül miktarı ne kadar?", "odul_miktari"),
            ("Vakıf Katılım alışveriş puanı veriyor mu?", "alisveris_puani"),
            ("Türkiye Finans hedef kitlesi kim?", "hedef_kitle"),
        ):
            with self.subTest(soru=soru):
                self.assertEqual(route(soru).field, alan)

    def test_karsi_ornek_kar_payi_orani_bozulmadi(self):
        for soru in ("Kuveyt Türk'ün konut finansmanı kâr payı oranı nedir?",
                     "Dünya Katılım kâr payı oranı kaç?",
                     "Hangi bankada en düşük kâr payı oranı var?",
                     "Albaraka'nın taşıt finansmanı oranı ne?",
                     "Getiri oranı en yüksek banka hangisi?"):
            with self.subTest(soru=soru):
                self.assertEqual(route(soru).field, "kar_payi_orani")

    def test_kullanicinin_SOYLEDIGI_iki_alan_dusmez(self):
        """"indirim oranı VE kâr payı oranı" — bastırma burada ÇALIŞMAZ."""
        alanlar = route("Albaraka'nın indirim oranı ve kâr payı oranı ne?").fields
        self.assertIn("indirim_orani", alanlar)
        self.assertIn("kar_payi_orani", alanlar)


class Kusur6UctanUca(_BotluTest):
    def test_indirim_sorusu_kar_payi_basligiyla_donmez(self):
        cevap = self.sor("Albaraka indirim oranı nedir?")
        self.assertEqual(cevap.field, "indirim_orani")
        self.assertIn("indirim oranı", cevap.text)


# =========================================================================== #
# KUSUR 7 — kullanıcıya "Sınıflandırılamadı" diye ürün ailesi gösteriliyor
# =========================================================================== #

class Kusur7BilinmeyenAileEtiketi(unittest.TestCase):
    def test_etiket_cevrilir(self):
        self.assertEqual(structured._aile_adi(BILINMEYEN_TUR),
                         structured.AILE_BELIRLENEMEDI)
        self.assertEqual(structured._aile_adi("Konut Finansmanı"),
                         "Konut Finansmanı")

    def test_bilinmeyen_kova_SONA_alinir(self):
        gruplar = [(BILINMEYEN_TUR, []), ("Kart", []), ("Konut Finansmanı", [])]
        sirali = structured._aileleri_sirala(gruplar)
        self.assertEqual(sirali[-1][0], BILINMEYEN_TUR)
        # Adlandırılmış ailelerin SIRASI korunur (`turlere_ayir` kurdu).
        self.assertEqual([t for t, _g in sirali[:-1]],
                         ["Kart", "Konut Finansmanı"])

    def _satir(self, **ek):
        from src.comparison.compare import RankRow
        varsayilan = dict(bank="albaraka", bank_name="Albaraka Türk",
                          campaign_id=1, campaign_type=None, value=2.49,
                          sort_key=2.49, comparable=True, note=None,
                          source_span=None, other_count=0)
        varsayilan.update(ek)
        return RankRow(**varsayilan)

    def test_baslikta_kayit_sayisi_yazilir(self):
        baslik = structured._aile_basligi(BILINMEYEN_TUR,
                                          [self._satir(other_count=3)])
        self.assertIn(structured.AILE_BELIRLENEMEDI, baslik)
        self.assertIn("4 kampanya", baslik)      # 1 + other_count

    def test_adlandirilmis_ailede_sayi_YAZILMAZ(self):
        self.assertEqual(structured._aile_basligi("Kart", []), "Kart")

    def test_liste_blogu_etiketi_ve_sayimi_basar(self):
        """Grup BLOK olarak gösterildiğinde de dürüst etiket + sayım."""
        metin, gosterilen = structured._phrase_list_by_type("kar_payi_orani", [
            ("Konut Finansmanı", [self._satir(campaign_type="Konut Finansmanı",
                                              bank="kuveyt-turk",
                                              bank_name="Kuveyt Türk")]),
            (BILINMEYEN_TUR, [self._satir(other_count=1)]),
        ])
        self.assertNotIn(BILINMEYEN_TUR, metin)
        self.assertIn(f"{structured.AILE_BELIRLENEMEDI} (2 kampanya)", metin)
        # Grup GİZLENMEDİ: satırı da basıldı.
        self.assertIn("Albaraka Türk", metin)
        self.assertEqual(len(gosterilen), 2)


class Kusur7UctanUca(_BotluTest):
    #: Listeleme niyeti taşıyan, süzgeçsiz soru — dokuz tohum kaydının hepsi
    #: havuza girer ve türü boş belge kendi kovasına düşer.
    LISTE_SORUSU = "Kâr payı oranını listele"

    def test_cevapta_siniflandirilamadi_GECMEZ_ama_grup_GIZLENMEZ(self):
        cevap = self.sor(self.LISTE_SORUSU)
        self.assertNotIn(BILINMEYEN_TUR, cevap.text)
        # Kova görünür: adı + kaç banka taşıdığı yazılı (`_AZAMI_TUR` kotasını
        # aşan aileler "diğer ürün aileleri" satırında sayılır).
        self.assertIn(structured.AILE_BELIRLENEMEDI, cevap.text)

    def test_bilinmeyen_kova_ADLANDIRILMIS_ailelerden_SONRA(self):
        metin = self.sor(self.LISTE_SORUSU).text
        for aile in ("Konut Finansmanı", "Taşıt Finansmanı", "Kart"):
            self.assertLess(metin.index(aile),
                            metin.index(structured.AILE_BELIRLENEMEDI),
                            f"{aile} bilinmeyen kovadan SONRA geliyor")


if __name__ == "__main__":            # pragma: no cover
    unittest.main()


# =========================================================================== #
# Koşul KAMPANYA üzerinden çözülür — alan bazlı süzme YANLIŞ olurdu
# =========================================================================== #

class Kusur2KosulKampanyaBazli(_BotluTest):
    """"Vade farksız" koşulu VADE sütununda 0 ay aramaz.

    `query_fields()` satırlarında `field_name` yoktur; koşulu satır değerine
    körlemesine uygulamak, "kâr payı %0" ölçütünü vade/ödül sütunlarına da
    dayatırdı ve kimsenin sormadığı bir soruyu (0 ay vade) cevaplardı.
    Çözüm: koşulu sağlayan KAMPANYA kimlikleri çıkarılır.
    """

    def test_tek_bankada_kosul_diger_alanlari_da_daraltir(self):
        cevap = self.sor("T.O.M. Katılım'da vade farksız taksitte vade kaç ay?")
        self.assertIn("Koşul UYGULANDI", cevap.text)
        # Kâr payı %0 olan T.O.M. kampanyasının vadesi 12 ay — 0 ay DEĞİL.
        self.assertIn("12 ay", cevap.text)
        self.assertNotIn("0 ay", cevap.text)

    def test_kullanicinin_soyledigi_ikinci_alan_dusmez(self):
        r = route("Masrafsız derken tahsis ücreti de yok mu?")
        self.assertEqual(r.field, "masraf_durumu")     # koşulun taşıyıcısı
        self.assertIn("tahsis_ucreti", r.fields)       # sessizce DÜŞMEZ


class MasrafTahsisAyrimi(_BotluTest):
    """"Masrafsız derken tahsis ücreti de yok mu?" — ayrım SÖYLENİR.

    Bu soru sınavda geçmiş sayılıyordu ama cevabı alakasız bir belgeydi.
    Koşul süzgeci onu doğru alana taşıdı; not ise sorunun KENDİSİNİ
    cevaplıyor: iki alan ayrıdır ve biri ötekini garanti etmez
    (CLAUDE.md §18-2).
    """

    def test_iki_alan_birlikte_sorulunca_ayrim_yazilir(self):
        cevap = self.sor("Masrafsız derken tahsis ücreti de yok mu?")
        self.assertIn("GARANTİ ETMEZ", cevap.text)
        self.assertIn("AYRI iki alan", cevap.text)

    def test_karsi_ornek_tek_alan_sorulunca_not_YOK(self):
        for soru in ("Ziraat Katılım'da masraf alınıyor mu?",
                     "En düşük tahsis ücreti hangi bankada?"):
            with self.subTest(soru=soru):
                self.assertNotIn("GARANTİ ETMEZ", self.sor(soru).text)

    def test_karsi_ornek_tek_obekten_iki_alan(self):
        """"dosya masrafı" / "tahsis ücreti" TEK öbektir — not basılmaz.

        `Route.fields` her iki alanı taşır (öbek ikisini birden tetikliyor)
        ama kullanıcı iki alanı AYRI ayrı anmamıştır.
        """
        for soru in ("Türkiye Emlak Katılım'da dosya masrafı var mı?",
                     "En düşük tahsis ücreti hangi bankada?",
                     "Vakıf Katılım ihtiyaç finansmanı tahsis ücreti ne kadar?"):
            with self.subTest(soru=soru):
                self.assertFalse(route(soru).masraf_tahsis_ayrimi)

    def test_dosya_masrafi_sorusu_IKI_ALANI_da_gosterir(self):
        """Not basılmasa da iki alanlı cevap KORUNUR (sınavda geçiyordu)."""
        cevap = self.sor("Kuveyt Türk'te dosya masrafı var mı?")
        self.assertIn("tahsis ücreti", cevap.text)
        self.assertIn("masraf durumu", cevap.text)
