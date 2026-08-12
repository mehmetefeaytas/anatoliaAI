"""Chatbot yapısal yolu — banka tekilleştirme, ürün ailesi kapısı, sıra yönü.

İlgili: src/chatbot/structured.py
        src/comparison/compare.py (`yon_zorla`, `tekil_banka_urun`, `turlere_ayir`)
        src/api/main.py (`/compare?per_bank=best` — parite tarafı)
        tests/test_api_compare_per_bank.py (aynı kuralın panel tarafı)

## Bu testin varlık sebebi

`/compare` ucu 2026-08-09'da "banka başına bir satır" kuralını aldı. Chatbot'un
yapısal yolu almadı ve `rank()` çıktısını olduğu gibi bastı. Tarayıcıda görülen
sonuç:

    vade (uygun kampanyalar):
      Kuveyt Türk: 120 ay        <- aynı banka
      Kuveyt Türk: 120 ay        <- aynı değer
      ...                        <- toplam 232 satır

Ölçüldü (`data/demo.db`, 16 yapısal soru, 2026-08-10):

    banka tekrarı olan soru   6/16  ->  0/16
    en kötü tekrar             232  ->  1
    en uzun cevap (karakter) 17008  ->  1490

Aynı yolda iki kusur daha vardı ve ikisi de burada kilitleniyor:

  * **Ürün ailesi kapısı yoktu.** 16 sorunun 12'sinde cevap birden fazla ürün
    ailesinden besleniyordu; en kötü hâlde 9 aile tek listede sıralanıyordu.
    Bir kredi kartı kampanyası ile bir konut finansmanı birbirinin alternatifi
    değildir (bkz. `compare.turlere_ayir`).
  * **Sıra yönü uygulanmıyordu.** `vade_ay` alanı doğal olarak "uzun iyi"
    sıralanır; "en düşük vade" sorusuna sıralamanın tepesi, yani **en uzun**
    vade basılıyordu ("en düşük vade: Ziraat Katılım (360 ay)").

`ComparePariteKapisi` mantığın ayrışmasını engeller: aynı veri üzerinde
`/compare?per_bank=best` ile chatbot'un kullandığı ortak fonksiyon **aynı**
satırları üretmek zorundadır.
"""

from __future__ import annotations

import re
import sys
import tempfile
import unittest
from collections import Counter
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

# fastapi yardımcı içinde import ediliyordu: modül yüklenir ama test HATA
# verir, atlanmaz. Koruma yalnız `ComparePariteKapisi`na konur — `_DepoluTest`
# aile testleri saf Python'la koşar ve bağımlılıksız koşuda KOŞMAYA DEVAM
# ETMELİ. Desen: `test_api_startup.py:37-41`.
try:  # pragma: no cover - ortama bağlı
    import fastapi  # noqa: F401
    FASTAPI_VAR = True
except ModuleNotFoundError:  # pragma: no cover
    FASTAPI_VAR = False

from src.chatbot import structured
from src.chatbot.router import Route
from src.comparison.compare import rank, tekil_banka_urun
from src.db.repository import Repository
from src.extraction.reconcile import build_campaign

#: Liste satırı: "- Kuveyt Türk: %1,89  _(+2 kampanya daha)_"
_SATIR = re.compile(r"^-\s(.+?):\s")


def bloklar(metin: str) -> list[list[str]]:
    """Cevabı gösterim bloklarına böler; her blok TEK bir kıyas listesidir.

    `**Başlık**` satırı yeni blok açar. Kullanıcı tek liste hâlinde ne
    görüyorsa blok odur; tekrar denetimi blok İÇİNDE yapılır çünkü aynı
    bankanın iki farklı ürün ailesinde görünmesi tekrar değildir.
    """
    out: list[list[str]] = []
    cur: list[str] = []
    for satir in metin.split("\n"):
        if satir.startswith("**"):
            out.append(cur)
            cur = []
            continue
        m = _SATIR.match(satir)
        if m:
            cur.append(m.group(1))
    out.append(cur)
    return [b for b in out if b]


class _DepoluTest(unittest.TestCase):
    """Bellek içi depo + `structured.answer` kısayolu."""

    def setUp(self):
        self.repo = Repository(":memory:")
        self.tohumla()

    def tearDown(self):
        self.repo.close()

    def tohumla(self) -> None:
        raise NotImplementedError

    def ekle(self, slug: str, metin: str, tur: str) -> None:
        self.repo.insert_campaign(
            build_campaign(metin, bank_slug=slug, campaign_type=tur))

    def cevap(self, field: str, intent: str = "list",
              filters: dict | None = None) -> structured.StructuredAnswer:
        return structured.answer(
            self.repo, Route("structured", field, intent, filters or {}))


# --------------------------------------------------------------------------- #
# 1. Banka başına tekilleştirme
# --------------------------------------------------------------------------- #

class BankaTekrariYok(_DepoluTest):
    """Aynı banka, aynı ürün ailesi → listede TEK satır."""

    def tohumla(self):
        for oran in ("1,89", "2,49", "3,19", "4,09"):
            self.ekle("kuveyt-turk",
                      f"Konut finansmanında kâr payı oranı %{oran}, 36 ay vade.",
                      "Konut Finansmanı")

    def test_ayni_banka_tek_kez_gecer(self):
        a = self.cevap("kar_payi_orani")
        for blok in bloklar(a.text):
            tekrar = Counter(blok).most_common(1)[0]
            self.assertEqual(tekrar[1], 1,
                             f"{tekrar[0]} blok içinde {tekrar[1]} kez geçti")

    def test_kalan_satir_ailenin_EN_IYISIDIR(self):
        """`kar_payi_orani` düşük-iyi: en düşük oran kalır."""
        a = self.cevap("kar_payi_orani")
        self.assertEqual([x.value for x in a.rows], [1.89])

    def test_elenen_kampanyalar_SAYILIYOR(self):
        a = self.cevap("kar_payi_orani")
        self.assertEqual(a.rows[0].other_count, 3)

    def test_elenen_sayisi_METINDE_gorunur(self):
        """`/compare`'in "+N kampanya daha" rozetinin sohbet karşılığı."""
        self.assertIn("+3 kampanya daha", self.cevap("kar_payi_orani").text)

    def test_hicbir_sey_elenmediyse_rozet_YOK(self):
        repo = Repository(":memory:")
        repo.insert_campaign(build_campaign(
            "Konut finansmanında kâr payı oranı %1,89, 36 ay vade.",
            bank_slug="kuveyt-turk", campaign_type="Konut Finansmanı"))
        metin = structured.answer(
            repo, Route("structured", "kar_payi_orani", "list", {})).text
        repo.close()
        self.assertNotIn("kampanya daha", metin)


class AyriUrunAileleriKorunur(_DepoluTest):
    """Tekilleştirme `(banka, tür)` bazında — yalnız banka bazında DEĞİL."""

    def tohumla(self):
        self.ekle("kuveyt-turk",
                  "Konut finansmanında kâr payı oranı %1,89, 36 ay vade.",
                  "Konut Finansmanı")
        self.ekle("kuveyt-turk",
                  "Konut finansmanında kâr payı oranı %2,49, 36 ay vade.",
                  "Konut Finansmanı")
        self.ekle("kuveyt-turk",
                  "Taşıt finansmanında kâr payı oranı %3,19, 36 ay vade.",
                  "Taşıt Finansmanı")

    def test_ayni_bankanin_iki_ailesi_AYRI_kalir(self):
        a = self.cevap("kar_payi_orani")
        self.assertEqual(sorted(x.campaign_type for x in a.rows),
                         ["Konut Finansmanı", "Taşıt Finansmanı"])

    def test_her_aile_kendi_en_iyisini_tutar(self):
        deger = {x.campaign_type: x.value for x in self.cevap("kar_payi_orani").rows}
        self.assertEqual(deger["Konut Finansmanı"], 1.89)
        self.assertEqual(deger["Taşıt Finansmanı"], 3.19)

    def test_other_count_aile_ICINDE_sayilir(self):
        sayi = {x.campaign_type: x.other_count
                for x in self.cevap("kar_payi_orani").rows}
        self.assertEqual(sayi["Konut Finansmanı"], 1)
        self.assertEqual(sayi["Taşıt Finansmanı"], 0)


# --------------------------------------------------------------------------- #
# 2. Ürün ailesi (kampanya türü) kapısı
# --------------------------------------------------------------------------- #

class TurKapisi(_DepoluTest):
    """Kıyas ürün ailesi İÇİNDE yapılır — CLAUDE.md §17'nin aile karşılığı."""

    def tohumla(self):
        self.ekle("kuveyt-turk",
                  "Konut finansmanında kâr payı oranı %1,89, 36 ay vade.",
                  "Konut Finansmanı")
        self.ekle("albaraka",
                  "Konut finansmanı kâr payı oranı %2,49, 36 ay vade.",
                  "Konut Finansmanı")
        self.ekle("turkiye-finans",
                  "Taşıt finansmanında kâr payı oranı %3,19, 36 ay vade.",
                  "Taşıt Finansmanı")
        self.ekle("vakif-katilim",
                  "Taşıt finansmanında kâr payı oranı %2,95, 36 ay vade.",
                  "Taşıt Finansmanı")

    def _blok_turleri(self, rows) -> list[set]:
        """Gösterilen satırların ardışık aile öbekleri."""
        obekler: list[set] = []
        for x in rows:
            if obekler and x.campaign_type in obekler[-1]:
                continue
            obekler.append({x.campaign_type})
        return obekler

    def test_liste_cevabi_aileye_gore_bloklanir(self):
        metin = self.cevap("kar_payi_orani").text
        self.assertIn("**Konut Finansmanı**", metin)
        self.assertIn("**Taşıt Finansmanı**", metin)

    def test_hicbir_blok_iki_aile_KARISTIRMAZ(self):
        a = self.cevap("kar_payi_orani")
        gorulen: list[str] = []
        for x in a.rows:
            if not gorulen or gorulen[-1] != x.campaign_type:
                gorulen.append(x.campaign_type)
        self.assertEqual(len(gorulen), len(set(gorulen)),
                         "bir aile bloğu bölünmüş — satırlar karışmış")

    def test_superlatif_AILE_BASINA_kazanan_verir(self):
        metin = self.cevap("kar_payi_orani", intent="lowest").text
        self.assertIn("Konut Finansmanı", metin)
        self.assertIn("Taşıt Finansmanı", metin)
        # Fikstürde banka ADI yok, slug var; şablon `bank_name or bank`.
        self.assertIn("kuveyt-turk", metin)
        self.assertIn("vakif-katilim", metin)

    def test_superlatif_AILELER_ARASI_tek_kazanan_ILAN_ETMEZ(self):
        """%1,89 konutun en iyisidir; taşıtın en iyisi %2,95'tir.

        Tek kazanan ilan etmek, konut finansmanını taşıt finansmanına
        yeğlemek olurdu — bu iki ürün birbirinin alternatifi değildir.
        """
        a = self.cevap("kar_payi_orani", intent="lowest")
        self.assertEqual(len(a.rows), 2)
        self.assertEqual({x.bank for x in a.rows},
                         {"kuveyt-turk", "vakif-katilim"})

    def test_kullanici_aileyi_SOYLERSE_tek_cumle_doner(self):
        """Tür verildiğinde soru zaten iyi tanımlı; gruplama gereksiz.

        Bu dal ayrıca sözelleştirmenin çalıştığı tek dal (`bot._sozellestir`
        yalnız tek satırlık şablonu LLM'e verir), o yüzden satır sayısı
        davranışsal olarak önemlidir.
        """
        a = self.cevap("kar_payi_orani", intent="lowest",
                       filters={"campaign_type": "Konut Finansmanı"})
        self.assertNotIn("\n", a.text)
        self.assertIn("kuveyt-turk", a.text)

    def test_gosterilmeyen_aileler_GIZLENMEZ_sayilir(self):
        """Dört aileden üçü listelenir, kalanlar adıyla duyurulur."""
        for tur, slug in (("Kart", "ziraat-katilim"),
                          ("İhtiyaç Finansmanı", "turkiye-emlak-katilim")):
            self.ekle(slug, "Kâr payı oranı %5,50, 36 ay vade.", tur)
        metin = self.cevap("kar_payi_orani").text
        self.assertIn("diğer ürün aileleri", metin)


class TuruBilinmeyenBelgeElenmez(_DepoluTest):
    """Türü boş belge kendi grubunda kalır — sınıflandırılmış aileye girmez."""

    def tohumla(self):
        self.ekle("kuveyt-turk",
                  "Konut finansmanında kâr payı oranı %1,89, 36 ay vade.",
                  "Konut Finansmanı")
        self.repo.insert_campaign(build_campaign(
            "Kâr payı oranı %2,49, 36 ay vade.", bank_slug="albaraka"))

    def test_bilinmeyen_tur_kendi_grubunda_gorunur(self):
        from src.comparison.compare import BILINMEYEN_TUR
        self.assertIn(BILINMEYEN_TUR, self.cevap("kar_payi_orani").text)


# --------------------------------------------------------------------------- #
# 3. Sıralama yönü
# --------------------------------------------------------------------------- #

class SiralamaYonu(_DepoluTest):
    """`vade_ay` doğal olarak "uzun iyi"dir; "en düşük" bunu TERSİNE çevirir."""

    def tohumla(self):
        for slug, ay in (("kuveyt-turk", 120), ("albaraka", 36),
                         ("turkiye-finans", 60)):
            self.ekle(slug,
                      f"Konut finansmanında kâr payı oranı %2,10, {ay} ay vade.",
                      "Konut Finansmanı")

    def test_en_yuksek_vade_EN_UZUN_olani_verir(self):
        a = self.cevap("vade_ay", intent="highest")
        self.assertIn("120", a.text)
        self.assertEqual(a.rows[0].bank, "kuveyt-turk")

    def test_en_dusuk_vade_EN_KISA_olani_verir(self):
        """Kusur buydu: "en düşük vade" sorusuna en UZUN vade basılıyordu."""
        a = self.cevap("vade_ay", intent="lowest")
        self.assertIn("36", a.text)
        self.assertEqual(a.rows[0].bank, "albaraka")
        self.assertNotIn("120", a.text)


# --------------------------------------------------------------------------- #
# 4. `/compare` ile parite
# --------------------------------------------------------------------------- #

@unittest.skipUnless(FASTAPI_VAR, "fastapi kurulu değil — API testi atlanıyor")
class ComparePariteKapisi(unittest.TestCase):
    """Panel ile sohbet AYNI tekilleştirmeyi uygulamak zorundadır.

    Bu depoda "aynı karar iki yerde yaşıyor" hatası defalarca tekrarlandı
    (`ihtar.py` belge süzmesi, oran tablosu başlık deseni, göç listesi
    paritesi). Kural artık `compare.tekil_banka_urun()` içinde TEK yerde;
    bu test `/compare?per_bank=best` çıktısının ondan ayrışmadığını kilitler.
    """

    ALAN = "kar_payi_orani"

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.path = str(Path(self._tmp.name) / "api.db")
        repo = Repository(self.path)
        veri = [
            ("kuveyt-turk", "1,89", "Konut Finansmanı"),
            ("kuveyt-turk", "2,49", "Konut Finansmanı"),
            ("kuveyt-turk", "3,19", "Taşıt Finansmanı"),
            ("albaraka", "2,95", "Konut Finansmanı"),
            ("albaraka", "4,09", "Konut Finansmanı"),
            ("turkiye-finans", "3,50", "Taşıt Finansmanı"),
        ]
        for slug, oran, tur in veri:
            repo.insert_campaign(build_campaign(
                f"Finansmanda kâr payı oranı %{oran}, 36 ay vade.",
                bank_slug=slug, campaign_type=tur))
        self.ilgili = {s for s, _, _ in veri}
        repo.close()

    def tearDown(self):
        self._tmp.cleanup()

    def _uctan(self) -> list[tuple]:
        from fastapi.testclient import TestClient

        from src.api import main as api_main
        onceki = api_main.DB_PATH
        api_main.DB_PATH = self.path
        try:
            app = api_main.build_app()
        finally:
            api_main.DB_PATH = onceki
        r = TestClient(app).get("/compare", params={"field": self.ALAN})
        self.assertEqual(r.status_code, 200, r.text)
        return [(x["bank"], x["campaign_type"], x["value"], x["other_count"])
                for x in r.json() if x["bank"] in self.ilgili]

    def _ortak_fonksiyondan(self) -> list[tuple]:
        repo = Repository(self.path)
        try:
            rows = repo.query_fields(self.ALAN)
        finally:
            repo.close()
        tekil = tekil_banka_urun(rank(rows, self.ALAN))
        return [(x.bank, x.campaign_type, x.value, x.other_count)
                for x in tekil if x.bank in self.ilgili]

    def test_ayni_satirlar_ayni_sirada(self):
        self.assertEqual(self._uctan(), self._ortak_fonksiyondan())


if __name__ == "__main__":
    unittest.main()
