"""Çok alanlı TEK-BANKA sorgusunda alan sessizce düşmemeli (jüri bulgusu).

İlgili: ../src/chatbot/router.py (`_detect_fields`, `Route.fields`)
        ../src/chatbot/structured.py (`_cok_alanli_tek_banka_cevabi`)
        ../src/chatbot/bot.py (`Chatbot.ask`)
        raw/teknofest/2026-teknofest-tyda-sartname-2-senaryo.pdf s.11–12
        (Örnek Temsili Senaryo-1 — "Kâr Payı Oranı" VE "Vade" sütunları
        aynı tabloda birlikte isteniyor)
        CLAUDE.md §19, §21

## Ölçülen hata (canlı `/chat` isteğiyle tekrar üretildi, 2026-08-20)

"Kuveyt Türk'ün konut finansmanı ORANI VE VADESİ nedir?" sorusunda yalnız
oran dönüyordu, vade hiçbir uyarı olmadan cevaptan KAYBOLUYORDU. Kök neden:
`router._detect_field` (tekil) soru sözlüğündeki İLK eşleşende dururdu —
"vade" sözcüğü sorguda geçse bile hiç ARANMIYORDU. Şartname s.12 tablosu
tam bu kalıbı istiyor: banka × ürün başına Kâr Payı Oranı VE Vade
sütunlarının BİRLİKTE dönmesi (Senaryo 1, s.12).

Bu dosya şartnamenin s.12 tablosundaki iki bankanın (A Bankası, B Bankası)
metinlerini GERÇEK bir banka slug'ına (`kuveyt-turk`, `albaraka`) yükleyip
"oranı ve vadesi" sorusunu iki referans soru olarak kilitler:

    A Bankası metni → Kâr Payı Oranı %1,89, Vade 120 ay (s.12)
    B Bankası metni → Kâr Payı Oranı %1,95, Vade 120 ay (s.12)

Ayrıca: istenen alanlardan biri BULUNAMAZSA sessizce düşmemeli, "bulunamadı"
diye adı geçmeli (halüsinasyon yasağının simetriği — CLAUDE.md §21).
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.chatbot.bot import Chatbot
from src.chatbot.router import route
from src.db.repository import Repository
from src.extraction.reconcile import build_campaign

# --------------------------------------------------------------------------- #
# Şartname s.11 — A Bankası ve B Bankası kampanya metinleri BİREBİR
# (bkz. tests/test_sartname_vade_kalibi.py — aynı metinler, extraction
# katmanında zaten kilitli; burada CHAT KATMANINDA sınanıyor)
# --------------------------------------------------------------------------- #
A_BANKASI_METNI = (
    "Yeni ev sahibi olmak isteyen müşterilerimize özel %1,89 kâr payı oranı "
    "ile 120 aya kadar konut finansmanı fırsatı sunulmaktadır. Kampanya "
    "kapsamında 50.000 TL'ye kadar dosya masrafı alınmamaktadır. Kampanya "
    "31 Aralık 2026 tarihine kadar geçerlidir."
)
B_BANKASI_METNI = (
    "Konut finansmanında avantajlı ödeme seçenekleri. %1,95 kâr payı oranı "
    "ile 120 ay vadeye kadar finansman imkanı sunulmaktadır. Kampanya "
    "kapsamında ekspertiz ücreti banka tarafından karşılanmaktadır."
)

#: Şartname s.12 tablosu — A Bankası = kuveyt-turk, B Bankası = albaraka
#: (fiktif "A/B Bankası" adları veri setinde yok; gerçek bir banka slug'ına
#: yüklenmeden `detect_banks()` bunları tanımaz ve soru abstain ederdi —
#: bkz. tests/test_bilinmeyen_banka_abstention.py).
SARTNAME_S12_REFERANS_SORULARI = [
    ("kuveyt-turk", A_BANKASI_METNI, "Kuveyt Türk", 1.89, 120,
     "Kuveyt Türk'ün konut finansmanı oranı ve vadesi nedir?"),
    ("albaraka", B_BANKASI_METNI, "Albaraka Türk", 1.95, 120,
     "Albaraka'nın konut finansmanı oranı ve vadesi nedir?"),
]


def _repo_kur() -> Repository:
    repo = Repository(":memory:")
    for slug, metin, _ad, _oran, _vade, _soru in SARTNAME_S12_REFERANS_SORULARI:
        repo.insert_campaign(build_campaign(metin, bank_slug=slug,
                                            campaign_type="Konut Finansmanı"))
    return repo


class TestRouterCokAlanTespitEder(unittest.TestCase):
    """Birim seviyesi: `route()` artık HER İKİ alanı da görüyor mu."""

    def test_oran_ve_vade_ikisi_de_tespit_edilir(self):
        r = route("Kuveyt Türk'ün konut finansmanı oranı ve vadesi nedir?")
        self.assertEqual("structured", r.handler)
        self.assertIn("kar_payi_orani", r.fields)
        self.assertIn("vade_ay", r.fields)
        self.assertEqual(2, len(r.fields))

    def test_tek_alanli_soru_hala_tek_elemanli(self):
        """Geriye dönük uyum: yalnız bir alan söylenmişse `fields` tek
        elemanlıdır — eski (tek-alanlı) davranış bozulmamalı."""
        r = route("Kuveyt Türk'ün konut finansmanı oranı nedir?")
        self.assertEqual(["kar_payi_orani"], r.fields)

    def test_field_hala_ILK_alani_tasir(self):
        """`Route.field` (tekil) geriye dönük uyum için birincil alanı
        taşımaya devam etmeli — `route()`'un başka hiçbir çağıranı
        kırılmasın."""
        r = route("Kuveyt Türk'ün konut finansmanı oranı ve vadesi nedir?")
        self.assertEqual("kar_payi_orani", r.field)


class TestSartnameS12IkiReferansSorusu(unittest.TestCase):
    """Şartname s.12 Senaryo 1 — iki referans soru KİLİTLİ.

    Her ikisi de tam sohbet yolundan (`Chatbot.ask`) geçer; yalnız
    `structured.answer()` değil, güvenlik kapıları da dahil UÇTAN UCA
    sınanır.
    """

    def setUp(self):
        self.repo = _repo_kur()
        self.addCleanup(self.repo.close)
        self.bot = Chatbot(self.repo)

    def test_her_iki_referans_soru_ORAN_VE_VADE_dondurur(self):
        for slug, _metin, ad, oran, vade, soru in SARTNAME_S12_REFERANS_SORULARI:
            with self.subTest(banka=ad):
                cevap = self.bot.ask(soru)
                self.assertEqual("structured", cevap.handler)
                oran_metni = str(oran).replace(".", ",")
                self.assertIn(f"%{oran_metni}", cevap.text,
                             f"{ad}: kâr payı oranı cevapta yok — s.12 "
                             f"beklentisi %{oran_metni}")
                self.assertIn(f"{vade} ay", cevap.text,
                             f"{ad}: vade cevapta yok — HATA 2 (jüri "
                             f"bulgusu): alan sessizce düştü")

    def test_vade_SESSIZCE_DUSMEDI(self):
        """Asıl jüri bulgusunun birebir karşılığı: eski kodda `vade` hiçbir
        uyarı olmadan cevaptan kaybolurdu. Artık ya değeriyle ya da açıkça
        'bulunamadı' diye anılır — ikisi de kabul, SESSİZLİK kabul DEĞİL."""
        cevap = self.bot.ask(SARTNAME_S12_REFERANS_SORULARI[0][-1])
        self.assertTrue("vade" in cevap.text.lower(),
                        "vade alanı cevap metninde hiç anılmıyor")


class TestEksikAlanSessizceDusMezBulunamadiDenir(unittest.TestCase):
    """İstenen alanlardan biri o banka/üründe HİÇ yoksa 'bulunamadı' denir."""

    def setUp(self):
        # Yalnız ORAN taşıyan, VADE'si hiç geçmeyen bir metin — s.12'nin
        # "A Bankası" metninden farklı olarak vade tetikleyicisi YOK.
        self.repo = Repository(":memory:")
        self.addCleanup(self.repo.close)
        self.repo.insert_campaign(build_campaign(
            "Konut finansmanında özel %2,10 kâr payı oranı sunulmaktadır.",
            bank_slug="kuveyt-turk", campaign_type="Konut Finansmanı"))
        self.bot = Chatbot(self.repo)

    def test_bulunamayan_alan_bulunamadi_der_SESSIZCE_DUSMEZ(self):
        cevap = self.bot.ask(
            "Kuveyt Türk'ün konut finansmanı oranı ve vadesi nedir?")
        self.assertEqual("structured", cevap.handler)
        self.assertIn("%2,1", cevap.text)
        self.assertIn("bulunamadı", cevap.text.lower(),
                     "vade verisi yokken sessizce düştü, 'bulunamadı' "
                     "denmedi")


if __name__ == "__main__":
    unittest.main()
