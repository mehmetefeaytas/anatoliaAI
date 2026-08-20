"""Tanınmayan banka adı → açık abstention (jüri bulgusu, Fonksiyonellik %20).

İlgili: ../src/chatbot/safety.py (`olasi_taniminayan_banka_adi`, `GATE_UNKNOWN_BANK`)
        ../src/chatbot/bot.py (`Chatbot.ask` — KAPI 5b, `_bilinmeyen_banka_yaniti`)
        ../src/chatbot/router.py (`_detect_filters` — `detect_banks` boşsa
        `filters["banks"]` hiç kurulmuyordu)
        CLAUDE.md §19, §21 ("Eksik bilgiyi doldurmak için değer uydurmak")

## Ölçülen hata (canlı `/chat` isteğiyle tekrar üretildi, 2026-08-20)

Kullanıcı "XYZ Bankası'nın konut finansmanı oranı ne?" gibi VERİ SETİNDE
OLMAYAN bir banka sorduğunda sistem "veri yok" demek yerine İLGİSİZ gerçek
bir bankanın (ör. Ziraat Katılım, Türkiye Emlak Katılım) belgesini KAYNAK
GÖSTEREREK döndürüyordu. Kök neden: `detect_banks()` hiçbir slug bulamadığı
için `router._detect_filters()` `filters["banks"]` anahtarını HİÇ
KURMUYORDU — "banka söylenmedi" (ör. "hangi bankada en düşük oran?") ile
"söylenen banka tanınmadı" (ör. "XYZ Bankası'nın oranı ne?") AYNI ŞEYMİŞ
gibi davranılıyor, ikinci durumda da süzgeçsiz aramaya düşülüyordu.

Bu ağırdır çünkü kaynaklı döndüğü için cevap DOĞRU GÖRÜNÜR — kanıtsız bir
halüsinasyondan daha tehlikelidir, çünkü projenin "kaynaksız iddia yok"
iddiasını sessizce delip geçer.

Bu dosya iki şeyi kilitler:

  1. Uydurma banka adları → `handler="safety"`, `bilinmeyen_banka` kapısı
     ateşlenir, cevap TANINAN bankaları LİSTELER (yol gösterme —
     "çıktıların anlaşılır olması").
  2. KARŞI-ÖRNEK: bilinen bankaların eşadları ("Kuveyt Türk", "KT",
     "Kuveytturk") ve tamamen JENERİK sorular ("hangi bankada", "en
     avantajlı katılım bankası hangisi") bu kapıdan HİÇ etkilenmez.
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.chatbot import safety
from src.chatbot.bot import Chatbot
from src.chatbot.router import BANK_DISPLAY
from src.db.repository import Repository
from src.extraction.reconcile import build_campaign

SEED = [
    ("kuveyt-turk", "Konut finansmanında kâr payı oranı %1,89, 120 ay vade.",
     "Konut Finansmanı"),
    ("albaraka", "Konut finansmanı kâr payı oranı %2,49, 96 ay vade.",
     "Konut Finansmanı"),
]

#: Jüri raporunda ve bu görevde birebir verilen üç uydurma banka adı.
UYDURMA_BANKA_SORULARI = [
    "XYZ Bankası'nın konut finansmanı oranı ne?",
    "Anadolu Katılım Bankası'nın kâr payı oranı nedir?",
    "Falcon Katılım Bank'ın konut finansmanı oranı nedir?",
]

#: Bilinen bankaların MEŞRU eşadları — bu kapı bunları BOZMAMALI.
MESRU_VARYANT_SORULARI = [
    "Kuveyt Türk'ün konut finansmanı oranı ne?",
    "KT'nin konut finansmanı oranı ne?",
    "Kuveytturk'ün konut finansmanı oranı ne?",
    "Ziraat Katılım Bankası'nın oranı nedir?",   # tam formel ad, "Bankası" ekli
]

#: Banka hiç ANILMAMIŞ, tamamen JENERİK sorular — abstention TETİKLENMEMELİ.
JENERIK_SORULAR = [
    "Hangi bankada en düşük kâr payı oranı var?",
    "En avantajlı katılım bankası hangisi?",
    "Türkiye'deki hangi banka daha avantajlı?",
    "Hangi katılım bankasının vadesi daha uzun?",
]


def _repo() -> Repository:
    repo = Repository(":memory:")
    for slug, text, ctype in SEED:
        repo.insert_campaign(build_campaign(text, bank_slug=slug,
                                            campaign_type=ctype))
    return repo


class TestSaflikBirimTesti(unittest.TestCase):
    """`safety.olasi_taniminayan_banka_adi` — bot/repo'dan bağımsız."""

    def test_uydurma_adlar_tespit_edilir(self):
        for soru in UYDURMA_BANKA_SORULARI:
            with self.subTest(soru=soru):
                self.assertTrue(safety.olasi_taniminayan_banka_adi(soru))

    def test_mesru_varyantlar_tetiklemez(self):
        for soru in MESRU_VARYANT_SORULARI:
            with self.subTest(soru=soru):
                self.assertFalse(safety.olasi_taniminayan_banka_adi(soru))

    def test_jenerik_sorular_tetiklemez(self):
        for soru in JENERIK_SORULAR:
            with self.subTest(soru=soru):
                self.assertFalse(safety.olasi_taniminayan_banka_adi(soru))

    def test_kt_artik_taninan_bir_alias(self):
        """Görev açıkça 'KT' varyantının çalışmaya devam etmesini istiyor."""
        self.assertEqual(safety.detect_banks("KT'nin oranı ne?"),
                         ["kuveyt-turk"])


class TestUydurmaBankaAbstentionEder(unittest.TestCase):
    """Tam uçtan uca: `Chatbot.ask()` uydurma banka adında ABSTAIN eder."""

    def setUp(self):
        self.repo = _repo()
        self.addCleanup(self.repo.close)
        self.bot = Chatbot(self.repo)

    def test_uc_uydurma_banka_da_abstain_eder(self):
        for soru in UYDURMA_BANKA_SORULARI:
            with self.subTest(soru=soru):
                cevap = self.bot.ask(soru)
                self.assertEqual("safety", cevap.handler)
                self.assertIn(safety.GATE_UNKNOWN_BANK, cevap.gates)
                self.assertTrue(cevap.safety_report.abstained)

    def test_ilgisiz_gercek_banka_kaynak_gostermez(self):
        """Asıl jüri bulgusu: cevap İLGİSİZ gerçek bir bankayı KAYNAK
        GÖSTEREREK dönmemeli. Kaynak listesi tamamen BOŞ olmalı."""
        cevap = self.bot.ask(UYDURMA_BANKA_SORULARI[0])
        self.assertEqual([], cevap.sources)
        # Cevap metninde seed edilmiş GERÇEK bankaların adı da GEÇMEMELİ —
        # geçseydi, "ilgisiz bankanın verisini gösterme" iddiası çürürdü.
        self.assertNotIn("%1,89", cevap.text)
        self.assertNotIn("%2,49", cevap.text)

    def test_cevap_taninan_bankalari_listeler(self):
        """Rubrik: 'çıktıların anlaşılır olması' — kullanıcıya yol gösterir."""
        cevap = self.bot.ask(UYDURMA_BANKA_SORULARI[0])
        for ad in BANK_DISPLAY.values():
            with self.subTest(banka=ad):
                self.assertIn(ad, cevap.text)

    def test_tkbb_gibi_otorite_kaynagi_listeye_SIZMAZ(self):
        """`repo.all_banks()` yerine `router.BANK_DISPLAY` kullanılmasının
        gerekçesi: `all_banks()` korpusun otorite kaynaklarını da (TKBB gibi)
        döner ve bunlar SORULABİLİR bankalar DEĞİLDİR (bkz.
        `api/routers/katalog.py::banks()` docstring'i)."""
        cevap = self.bot.ask(UYDURMA_BANKA_SORULARI[0])
        self.assertNotIn("Birliği", cevap.text)


class TestMesruVaryantlarBozulmadi(unittest.TestCase):
    """Karşı-örnek: bilinen banka eşadları bu kapıdan ETKİLENMEMELİ."""

    def setUp(self):
        self.repo = _repo()
        self.addCleanup(self.repo.close)
        self.bot = Chatbot(self.repo)

    def test_varyantlar_abstain_ETMEZ(self):
        for soru in MESRU_VARYANT_SORULARI:
            with self.subTest(soru=soru):
                cevap = self.bot.ask(soru)
                self.assertNotIn(safety.GATE_UNKNOWN_BANK, cevap.gates)

    def test_kuveyt_turk_esadlari_ayni_cevabi_verir(self):
        """'Kuveyt Türk', 'KT', 'Kuveytturk' AYNI bankaya, AYNI oranla
        cevap vermeli — kısaltma yüzünden farklı (ya da boş) bir cevap
        gelirse eşad tanıma bozulmuş demektir. (Test deposu bankayı özel
        bir görünen adla kaydetmiyor, satır slug'ı taşır — burada sınanan
        eşadların AYNI SLUG'A çözüldüğü, ekran adının biçimi değil.)"""
        cevaplar = {soru: self.bot.ask(soru).text
                   for soru in MESRU_VARYANT_SORULARI[:3]}
        ilk = next(iter(cevaplar.values()))
        for soru, metin in cevaplar.items():
            with self.subTest(soru=soru):
                self.assertIn("kuveyt-turk", metin)
                self.assertIn("1,89", metin)
                self.assertEqual(ilk, metin,
                                 "eşadlar aynı bankaya çözülmüyor — "
                                 f"'{soru}' farklı bir cevap üretti")


class TestJenerikSorularBozulmadi(unittest.TestCase):
    """Karşı-örnek: banka hiç anılmayan jenerik sorular eski davranışını
    korumalı — bu kapı yüzünden yanlışlıkla abstain ETMEMELİ."""

    def setUp(self):
        self.repo = _repo()
        self.addCleanup(self.repo.close)
        self.bot = Chatbot(self.repo)

    def test_jenerik_sorular_abstain_ETMEZ(self):
        for soru in JENERIK_SORULAR:
            with self.subTest(soru=soru):
                cevap = self.bot.ask(soru)
                self.assertNotIn(safety.GATE_UNKNOWN_BANK, cevap.gates)


if __name__ == "__main__":
    unittest.main()
