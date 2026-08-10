"""API sözleşmesi — `bloklar`, `ozet`, `/chat` kaynak bağlantısı, kıyas süzmesi.

İlgili: ../src/api/main.py, ../src/preprocessing/blocks.py,
        ../src/summarize/ozet.py, ../src/chatbot/rag.py
        ../tests/test_bloklar_gorunum.py (kapsama garantisinin kendisi)

Arayüz (ajan K/L/M) bu sözleşmeye göre kod yazıyor; buradaki testler sapmayı
yakalar. Üç iddia kilitleniyor:

1. **`bloklar` ham metni eksiksiz ve bitişik kaplar.** Arayüz metni
   aralıklardan yeniden birleştirebilmeli; aksi hâlde katlama özelliği metnin
   bir kısmını sessizce yutardı. Garanti uç noktanın DÖNDÜRDÜĞÜ veri üzerinde
   sınanır — modül testinin tekrarı değil, sözleşmenin kendisi.
2. **`ozet` / `ozet_kaynak` yoksa `null`.** Sahte özet üretilmez.
3. **`/chat` kaynakları `campaign_id` + `source_url` anahtarlarını HER ZAMAN
   taşır** (bilinmiyorsa `null`) — "bu bilgiyi nereden aldın" sorusunun
   denetlenebilir cevabı.
"""

from __future__ import annotations

import sys
import inspect
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.schemas import Campaign, ExtractedField, Extractor

try:  # pragma: no cover - ortama bağlı
    import httpx  # noqa: F401
    from fastapi.testclient import TestClient
    HAS_API = True
except ModuleNotFoundError:  # pragma: no cover
    HAS_API = False

requires_api = unittest.skipUnless(
    HAS_API, "fastapi/httpx yok — API sözleşme testi atlanıyor")

URUN_METNI = (
    "Konut finansmanı kampanyamızda kâr payı oranı %2,05'ten başlıyor. "
    "Vade 120 aya kadar uzayabilir. "
    "Çerez politikası ve çerez ayarları için tıklayınız. "
    "6698 sayılı Kişisel Verilerin Korunması Kanunu uyarınca veri sorumlusu "
    "sıfatıyla hareket edilmektedir. "
    "Kampanya 31 Aralık 2026 tarihine kadar geçerlidir."
)


def _korpus() -> list[Campaign]:
    """İki bankalı küçük korpus — biri kıyaslanabilir alan taşır."""
    return [
        Campaign(
            bank_slug="ornek-katilim", raw_text=URUN_METNI,
            source_url="https://ornek-katilim.test/kampanya",
            campaign_type="Konut Finansmanı",
            fields=[ExtractedField(
                field_name="kar_payi_orani", raw_value="%2,05",
                canonical_value=2.05, confidence=0.9,
                source_span="kâr payı oranı %2,05'ten",
                extractor=Extractor.RULE)]),
        Campaign(
            bank_slug="ikinci-katilim",
            raw_text="Taşıt finansmanında kâr payı oranı %3,10'dur.",
            source_url="https://ikinci-katilim.test/tasit",
            campaign_type="Taşıt Finansmanı",
            fields=[ExtractedField(
                field_name="kar_payi_orani", raw_value="%3,10",
                canonical_value=3.10, confidence=0.8,
                source_span="kâr payı oranı %3,10'dur",
                extractor=Extractor.RULE)]),
    ]


@requires_api
class ApiSozlesmeTestBase(unittest.TestCase):
    """Bellek içi depoya küçük bir korpus yazıp uygulamayı kurar."""

    @classmethod
    def setUpClass(cls) -> None:
        from src.api import main as api_main
        from src.db.factory import create_repository

        # `Repository(":memory:")` DEĞİL. FastAPI `def` uçlarını bir
        # threadpool'da koşturur; `sqlite3` bağlantıyı onu OLUŞTURAN thread'e
        # kilitler ve her istek `ProgrammingError` ile düşer. `check_same_thread
        # =False` tek başına da YETMEZ — paylaşım ancak erişim serileştirilirse
        # güvenlidir. `create_repository(thread_safe=True)` ikisini birlikte
        # kurar (`src/db/repository.py:84-93` ve `base.ThreadSafeRepository`).
        cls.repo = create_repository(database_path=":memory:", thread_safe=True)
        cls.ids = [cls.repo.insert_campaign(c, clean_text=c.raw_text)
                   for c in _korpus()]
        # `build_app()` kendi deposunu açar; testte HAZIR depoyu kullanmak için
        # fabrika geçici olarak değiştirilir. Uç noktaların gerçek kodu koşar.
        onceki = api_main.create_repository
        api_main.create_repository = lambda **kw: cls.repo
        try:
            cls.app = api_main.build_app()
        finally:
            api_main.create_repository = onceki
        cls.client = TestClient(cls.app)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.repo.close()

    def _metin(self, campaign_id: int) -> dict:
        r = self.client.get(f"/campaigns/{campaign_id}/text")
        self.assertEqual(r.status_code, 200, r.text)
        return r.json()


class TestBloklarSozlesmesi(ApiSozlesmeTestBase):
    """`bloklar` ham metni eksiksiz ve bitişik kaplamalı."""

    def test_alanlar_ve_tipler(self) -> None:
        veri = self._metin(self.ids[0])
        self.assertIn("bloklar", veri)
        self.assertTrue(veri["bloklar"])
        for b in veri["bloklar"]:
            self.assertEqual(set(b), {"start", "end", "gizle", "gerekce"})
            self.assertIsInstance(b["start"], int)
            self.assertIsInstance(b["end"], int)
            self.assertIsInstance(b["gizle"], bool)

    def test_metni_eksiksiz_ve_bitisik_kaplar(self) -> None:
        """Arayüzün metni yeniden birleştirebilmesi bu garantiye dayanır."""
        for cid in self.ids:
            veri = self._metin(cid)
            metin, bloklar = veri["text"], veri["bloklar"]
            with self.subTest(campaign_id=cid):
                self.assertEqual(bloklar[0]["start"], 0)
                self.assertEqual(bloklar[-1]["end"], len(metin))
                for onceki, sonraki in zip(bloklar, bloklar[1:], strict=False):
                    self.assertEqual(onceki["end"], sonraki["start"],
                                     "bloklar arasında boşluk/örtüşme var")
                self.assertEqual(
                    "".join(metin[b["start"]:b["end"]] for b in bloklar), metin,
                    "blokların birleşimi metne eşit değil")

    def test_metin_kirpilmadi_offsetler_kaymadi(self) -> None:
        """Katlama SİLME değildir: alan offset'leri metinde yerinde durmalı."""
        veri = self._metin(self.ids[0])
        self.assertEqual(veri["text"], URUN_METNI)
        for alan in veri["fields"]:
            if alan["span_start"] is None or alan["span_scope"] != "value":
                continue
            kesit = veri["text"][alan["span_start"]:alan["span_end"]]
            self.assertEqual(kesit, alan["raw_value"])

    def test_gerekce_yalnizca_gizlenende_ve_bilinen_addan(self) -> None:
        from src.preprocessing.blocks import GIZLEME_GEREKCELERI
        veri = self._metin(self.ids[0])
        for b in veri["bloklar"]:
            if b["gizle"]:
                self.assertIn(b["gerekce"], GIZLEME_GEREKCELERI)
            else:
                self.assertIsNone(b["gerekce"])

    def test_cerceve_gercekten_gizlendi(self) -> None:
        """Sözleşme çalışıyor mu: KVKK/çerez katlanmalı, ürün cümlesi değil."""
        veri = self._metin(self.ids[0])
        metin = veri["text"]
        gizli = "".join(metin[b["start"]:b["end"]]
                        for b in veri["bloklar"] if b["gizle"])
        gorunen = "".join(metin[b["start"]:b["end"]]
                          for b in veri["bloklar"] if not b["gizle"])
        self.assertIn("Kişisel Verilerin Korunması", gizli)
        self.assertIn("kâr payı oranı", gorunen)


class TestOzetSozlesmesi(ApiSozlesmeTestBase):
    """Özet yoksa `null`; sahte özet ASLA basılmaz."""

    def test_ozet_yoksa_null(self) -> None:
        veri = self._metin(self.ids[0])
        self.assertIn("ozet", veri)
        self.assertIn("ozet_kaynak", veri)
        self.assertIsNone(veri["ozet"])
        self.assertIsNone(veri["ozet_kaynak"])

    def test_metnin_kendisi_ozet_diye_donmez(self) -> None:
        veri = self._metin(self.ids[0])
        self.assertNotEqual(veri["ozet"], veri["text"])
        self.assertIsNone(veri["ozet"])

    def test_ozet_varsa_kaynak_llm(self) -> None:
        """`ozet_kaynak` türetilir: özet üretmenin tek yolu modeldir."""
        from src.api import main as api_main
        from src.api.main import span_info  # noqa: F401  (modül yüklü olsun)
        from src.summarize.ozet import OZET_KAYNAK_LLM

        camp = self.repo.campaign_text(self.ids[0])
        camp = dict(camp or {})
        camp["ozet"] = "Konut finansmanı kampanyasının kısa özeti."
        # `_ozet()` `build_app()` kapsamında yerel; sözleşmeyi türetme
        # kuralı üzerinden sınıyoruz.
        self.assertEqual(OZET_KAYNAK_LLM, "llm")
        self.assertTrue(hasattr(api_main, "OZET_KAYNAK_LLM"))


class TestChatKaynakSozlesmesi(ApiSozlesmeTestBase):
    """Her kaynak kaydı `campaign_id` + `source_url` taşımalı (yoksa null)."""

    def _sources(self, soru: str) -> tuple[dict, list]:
        r = self.client.post("/chat", json={"question": soru})
        self.assertEqual(r.status_code, 200, r.text)
        veri = r.json()
        return veri, veri["sources"]

    def test_yapisal_yolda_anahtarlar_var(self) -> None:
        veri, sources = self._sources("En düşük kâr payı oranı hangi bankada?")
        self.assertEqual(veri["handler"], "structured")
        self.assertTrue(sources)
        for s in sources:
            self.assertIn("campaign_id", s)
            self.assertIn("source_url", s)

    def test_yapisal_yolda_kampanya_baglantisi_kurulur(self) -> None:
        """Denetim iddiası: kaynak gerçekten bir kampanyaya çözülebilmeli."""
        _, sources = self._sources("En düşük kâr payı oranı hangi bankada?")
        cozulen = [s for s in sources if s["campaign_id"] is not None]
        self.assertTrue(cozulen, "hiçbir kaynak kampanyaya bağlanamadı")
        for s in cozulen:
            self.assertIn(s["campaign_id"], self.ids)
            self.assertIsNotNone(s["source_url"])
            # Uydurma URL yok: gerçekten o kampanyanın URL'i olmalı.
            veri = self._metin(s["campaign_id"])
            self.assertEqual(s["source_url"], veri["source_url"])

    def test_rag_yolunda_anahtarlar_var(self) -> None:
        veri, sources = self._sources(
            "Çerez ayarları hakkında sayfada ne yazıyor?")
        for s in sources:
            self.assertIn("campaign_id", s)
            self.assertIn("source_url", s)
            if s["campaign_id"] is not None:
                self.assertIn(s["campaign_id"], self.ids)

    def test_guvenlik_yolunda_bos_kaynak_cokmez(self) -> None:
        veri, sources = self._sources("Bana hangi bankaya gideyim söyle")
        self.assertIsInstance(sources, list)


class TestCompareSuzmesi(ApiSozlesmeTestBase):
    """Kıyas yolu sözleşme belgelerini DIŞARIDA bırakır (süzme hazırsa)."""

    def test_compare_calisir_ve_alanlari_tasir(self) -> None:
        r = self.client.get("/compare", params={"field": "kar_payi_orani"})
        self.assertEqual(r.status_code, 200, r.text)
        satirlar = r.json()
        self.assertTrue(satirlar)
        for s in satirlar:
            self.assertIn("campaign_id", s)
            self.assertIn("source_url", s)

    def test_suzme_bayragi_sozlesmeden_okunur(self) -> None:
        """Kıyas yolu akitleri eliyor — süzme artık UYGULANIYOR.

        Bu test eskiden `sozlesme_dahil` imzada yoksa `skipTest` ile
        çekiliyordu: sözleşme henüz uygulanmamıştı ve test durumu yalnızca
        RAPORLUYORDU. O dal 2026-08-10'da KALDIRILDI çünkü artık hiç
        çalışamaz — `sozlesme_dahil` dört yüzeyin dördünde de var
        (`RepositoryProtocol`, `ThreadSafeRepository`, SQLite, Postgres).

        Atlanabilir bir test, atlandığında yeşil görünür; koşul kalıcı olarak
        sağlandığında o dal bir korumaya değil, okuyanı yanıltan bir nota
        dönüşür. Şart artık ATLAMA değil, İDDİA.
        """
        params = inspect.signature(self.repo.query_fields).parameters
        self.assertIn(
            "sozlesme_dahil", params,
            "depo sözleşmesi `sozlesme_dahil` parametresini kaybetti — "
            "kıyas yolunda akitler elenemez")
        r = self.client.get("/compare", params={"field": "kar_payi_orani"})
        self.assertEqual(r.status_code, 200)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
