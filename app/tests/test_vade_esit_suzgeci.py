"""«6 ay vadeli» — sessizce düşen vade koşulunun testi.

İlgili: ../src/chatbot/router.py (`_detect_filters`, `vade_ay_esit`)
        ../src/chatbot/structured.py (`_vade_suzgec_notu`, süzgeç uygulama)

## Ölçülen kusur (jüri 3. turu, 21 Ağustos 2026)

Jüri sistemi canlı ayağa kaldırıp sordu: *"6 ay vadeli ve %0 kâr paylı kampanya
var mı?"* Sistem yalnız kâr payı koşulunu uyguladı, **vade koşulundan hiç
bahsetmedi**. Kök neden `_detect_filters`teki tetikleyici listesiydi: "veren",
"üzeri", "en az" vardı, **"vadeli" yoktu**. Aynı soru "en az 6 ay vade veren…"
diye sorulduğunda mekanizma doğru çalışıyordu — yani mantık değil, sözcük
listesi eksikti.

## Bu dosya üç şeyi korur

1. **Koşul ARTIK YAKALANIYOR** — "N ay vadeli" çekimi süzgece dönüşüyor.
2. **DOĞRU anlamla yakalanıyor.** `vade_ay_min` ">=" demektir; "6 ay vadeli"
   isteyene 12 ay vadeli kampanyayı vermek, düşürülen koşulun yerine YANLIŞ
   bir koşul koymak olurdu. Bu yüzden ayrı bir eşitlik süzgeci var.
3. **Süzgeç GÖRÜNÜR.** Sessizce uygulanan süzgeç, sessizce düşürülenin daha
   kibar hâlidir: küme daralır, kullanıcı sebebini bilmez.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.chatbot.router import BANK_DISPLAY, route
from src.chatbot.structured import answer
from src.db.repository import Repository
from src.extraction.reconcile import build_campaign

#: Üç banka, üç ayrı vade. Metinler kâr payı oranı da taşıyor ki cevap
#: yolu (oran listesi) gerçekten çalışsın.
KAMPANYALAR = (
    ("kuveyt-turk", "Katılma hesabı 6 ay vade ile açılır. Kâr payı oranı %2,05."),
    ("albaraka", "Katılma hesabı 12 ay vade ile açılır. Kâr payı oranı %3,10."),
    ("vakif-katilim", "Katılma hesabı 24 ay vade ile açılır. Kâr payı oranı %4,00."),
)


def _depo() -> Repository:
    repo = Repository(":memory:")
    for slug, metin in KAMPANYALAR:
        repo.upsert_bank(BANK_DISPLAY.get(slug, slug), slug)
        repo.insert_campaign(build_campaign(metin, bank_slug=slug,
                                            campaign_type="Yatırım Ürünü"))
    return repo


class TestYonlendirme(unittest.TestCase):
    def test_vadeli_cekimi_suzgece_donusur(self) -> None:
        r = route("6 ay vadeli ve %0 kâr paylı kampanya var mı")
        self.assertEqual(r.filters.get("vade_ay_esit"), 6,
                         "vade koşulu sessizce düşüyor")
        self.assertIsNone(r.filters.get("vade_ay_min"),
                          "«vadeli» ASGARİ okunmamalı")

    def test_asgari_okumasi_onceliklidir(self) -> None:
        """"en az 6 ay vadeli" hem «en az» hem «vadeli» taşır — asgaridir."""
        r = route("en az 6 ay vadeli kampanyalar")
        self.assertEqual(r.filters.get("vade_ay_min"), 6)
        self.assertIsNone(r.filters.get("vade_ay_esit"))

    def test_eski_davranis_korundu(self) -> None:
        for soru, beklenen in (
                ("36 ay ve üzeri vade veren konut finansmanı", 36),
                ("en az 12 ay vade veren kampanyalar", 12)):
            with self.subTest(soru=soru):
                self.assertEqual(route(soru).filters.get("vade_ay_min"),
                                 beklenen)

    def test_vade_gecmeyen_soru_suzgec_kurmaz(self) -> None:
        r = route("%0 kâr paylı kampanya var mı")
        self.assertIsNone(r.filters.get("vade_ay_esit"))
        self.assertIsNone(r.filters.get("vade_ay_min"))


class TestYilBirimi(unittest.TestCase):
    """4. tur bulgusu: desen yalnız `ay` görüyordu, "3 yıl" düşüyordu.

    Kusur 3. turda kapatılan "6 ay vadeli" hatasının İKİZİ: mekanizma doğru,
    sözcük listesi dar. Çıkarım katmanı "yıl"ı zaten çeviriyordu; router
    aynı standarda getirilmemişti.
    """

    def test_yil_aya_cevrilir(self) -> None:
        for soru, beklenen in (("3 yıl vadeli kampanya var mı", 36),
                               ("5 sene vadeli finansman", 60),
                               ("1 yıl vadeli katılma hesabı", 12)):
            with self.subTest(soru=soru):
                self.assertEqual(route(soru).filters.get("vade_ay_esit"),
                                 beklenen)

    def test_yil_asgari_okumasi(self) -> None:
        self.assertEqual(
            route("en az 2 yıl vade veren konut finansmanı")
            .filters.get("vade_ay_min"), 24)

    def test_ay_birimi_bozulmadi(self) -> None:
        self.assertEqual(route("6 ay vadeli kampanya")
                         .filters.get("vade_ay_esit"), 6)
        self.assertEqual(route("36 ay ve üzeri vade veren")
                         .filters.get("vade_ay_min"), 36)

    def test_takvim_yili_tuzagina_dusmez(self) -> None:
        """"2026 yılı" bir SÜRE değil TARİH — 2026×12=24.312 ay olamaz.

        Aynı tuzak `extraction.rules.vade._takvim_yili`'de ölçülmüş ve
        orada 10 kayıt bozuyordu.
        """
        for soru in ("2026 yılı kampanyaları", "2025 yılı sonuna kadar"):
            with self.subTest(soru=soru):
                f = route(soru).filters
                self.assertIsNone(f.get("vade_ay_esit"))
                self.assertIsNone(f.get("vade_ay_min"))

    def test_absurt_yil_reddedilir(self) -> None:
        """80 yıl vadeli finansman diye bir şey yok — süzgeç kurulmaz."""
        f = route("80 yıl vadeli finansman").filters
        self.assertIsNone(f.get("vade_ay_esit"))
        self.assertIsNone(f.get("vade_ay_min"))


class TestSuzgecUygulaniyor(unittest.TestCase):
    """Süzgeç kurulup uygulanmazsa hiçbir şey değişmez."""

    def setUp(self) -> None:
        self.repo = _depo()

    def _satir_sayisi(self, soru: str) -> int:
        r = route(soru)
        return len(answer(self.repo, r).rows)

    def test_tam_vade_suzuyor(self) -> None:
        hepsi = self._satir_sayisi("kâr payı oranı en yüksek hangi bankada")
        alti = self._satir_sayisi("6 ay vadeli kampanyalarda kâr payı oranı "
                                  "en yüksek hangi bankada")
        self.assertEqual(hepsi, 3)
        self.assertEqual(alti, 1, "eşitlik süzgeci uygulanmıyor")

    def test_asgari_vade_daha_genis_kume_verir(self) -> None:
        """Aynı sayı, iki farklı anlam: 12 eşitlik 1, asgari 2 kampanya."""
        esit = self._satir_sayisi("12 ay vadeli kampanyalarda kâr payı oranı "
                                  "en yüksek hangi bankada")
        asgari = self._satir_sayisi("en az 12 ay vade veren kampanyalarda kâr "
                                    "payı oranı en yüksek hangi bankada")
        self.assertEqual(esit, 1)
        self.assertEqual(asgari, 2)

    def test_karsiligi_olmayan_vade_bos_kume(self) -> None:
        self.assertEqual(
            self._satir_sayisi("7 ay vadeli kampanyalarda kâr payı oranı en "
                               "yüksek hangi bankada"), 0)


class TestSuzgecGorunur(unittest.TestCase):
    """Süzgeç uygulandıysa cevap onu SÖYLEMELİ."""

    def test_tam_vade_notu_cevapta(self) -> None:
        repo = _depo()
        r = route("6 ay vadeli kampanyalarda kâr payı oranı en yüksek hangi "
                  "bankada")
        metin = answer(repo, r).text
        self.assertIn("tam 6 ay vade", metin)
        self.assertIn("en az 6 ay", metin,
                      "kullanıcıya daha geniş kümeyi nasıl isteyeceği "
                      "söylenmeli")

    def test_asgari_vade_notu_cevapta(self) -> None:
        repo = _depo()
        r = route("en az 12 ay vade veren kampanyalarda kâr payı oranı en "
                  "yüksek hangi bankada")
        self.assertIn("12 ay ve üzeri vade", answer(repo, r).text)

    def test_vade_yoksa_not_yok(self) -> None:
        repo = _depo()
        r = route("kâr payı oranı en yüksek hangi bankada")
        self.assertNotIn("Süzgeç UYGULANDI", answer(repo, r).text)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
