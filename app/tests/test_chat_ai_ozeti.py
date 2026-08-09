"""Chatbot kaynaklarında «AI Özeti» — uzun ham metin ekrana dökülmez.

İlgili: ../src/chatbot/rag.py, ../src/api/main.py,
        ../web/app/components/ChatPanel.tsx, ../src/summarize/ozet.py

## Bu testin varlık sebebi

Chatbot'a tek bir soru sorulduğunda kaynak tablosuna **4.000+ karakterlik ham
kampanya metni** basılıyordu — üç satır boyunca, ekran okunmaz hâlde. İki yerden
geliyordu:

1. `rag.answer()` LLM kapalıyken `f"İlgili kampanya ({bank}): {top['text']}"`
   döndürüyordu ve `text` belgenin TAMAMIYDI.
2. `KeywordRetriever.retrieve()` pasaja `raw_text`'i koyuyordu; arayüz de onu
   olduğu gibi hücreye basıyordu.

Ölçüldü (`data/demo.db`, 2026-08-09): 1774 belge, ortalama 4.744 karakter,
1005 belge (%57) 2.000 karakterin üzerinde, en uzunu 178.825 karakter. Aynı
depoda 1073 belgenin (%60) özeti hazır ve ortalaması 259 karakter.

## Kilitlenen dört iddia

1. Pasajlar `ozet` anahtarını **her zaman** taşır (yoksa `None`).
2. Özet varsa çıkarımsal cevap onu basar, ham metnin tamamını basmaz.
3. **Özet yoksa uydurulmaz**: cevap «AI Özeti» diye bir şey sunmaz, gösterdiği
   parçanın özet OLMADIĞINI açıkça söyler ve metni kırpar.
4. `/chat` yanıtındaki her kaynak kaydında `ozet` anahtarı vardır.

Üçüncüsü en kritiği: `src/summarize/ozet.py` kural tabanlı sahte özeti
yasaklıyor ve bu ekranın o yasağı delen bir arka kapı olmaması gerekiyor.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.chatbot import rag
from src.db.repository import Repository
from src.extraction.reconcile import build_campaign

_KOK = Path(__file__).resolve().parents[1]

#: Gerçekçi biçimde uzun bir belge: kırpmanın gerçekten iş yaptığını görmek
#: için `rag.ALINTI_KARAKTER`'ın kat kat üstünde olmalı.
UZUN_METIN = (
    "Konut finansmanı kampanyamızda kâr payı oranı %1,89'dan başlıyor ve "
    "vade 120 aya kadar uzayabilir. "
    + ("Kampanya koşulları şubelerimizden öğrenilebilir. " * 120)
)

OZET_METNI = ("Konut finansmanı kampanyası: kâr payı oranı %1,89'dan başlıyor, "
              "vade en çok 120 ay.")


class RagOzetTestBase(unittest.TestCase):
    """Tek belgelik depo: biri özetli, biri özetsiz iki senaryo kurulur."""

    def setUp(self) -> None:
        self.repo = Repository(":memory:")
        self.cid = self.repo.insert_campaign(
            build_campaign(UZUN_METIN, bank_slug="ornek-katilim",
                           campaign_type="Konut Finansmanı"))

    def tearDown(self) -> None:
        self.repo.close()

    def _pasaj(self) -> dict:
        r = rag.KeywordRetriever(self.repo)
        pasajlar = r.retrieve("Konut finansmanı koşulları nelerdir?")
        self.assertTrue(pasajlar, "korpus kuruldu ama pasaj dönmedi")
        return pasajlar[0]


class TestKisaAlinti(unittest.TestCase):
    """Kırpma sözcük ortasından kesmez ve kırpıldığını gösterir."""

    def test_kisa_metin_dokunulmadan_doner(self) -> None:
        self.assertEqual(rag.kisa_alinti("Kâr payı oranı %1,89."),
                         "Kâr payı oranı %1,89.")

    def test_uzun_metin_kirpilir_ve_isaretlenir(self) -> None:
        out = rag.kisa_alinti(UZUN_METIN)
        self.assertLessEqual(len(out), rag.ALINTI_KARAKTER + 1)
        self.assertTrue(out.endswith("…"))

    def test_sozcuk_ortasindan_kesmez(self) -> None:
        out = rag.kisa_alinti(UZUN_METIN).rstrip("…")
        self.assertTrue(UZUN_METIN.startswith(out),
                        "kırpılan parça metnin başlangıcı değil")
        # Kesim noktası bir sözcük sınırı olmalı.
        self.assertEqual(UZUN_METIN[len(out):len(out) + 1], " ")

    def test_bosluksuz_devasa_sozcuk_cokmez(self) -> None:
        out = rag.kisa_alinti("a" * 5000)
        self.assertLessEqual(len(out), rag.ALINTI_KARAKTER + 1)


class TestPasajOzetTasir(RagOzetTestBase):
    """Pasaj sözleşmesi: `ozet` anahtarı HER ZAMAN var."""

    def test_ozet_yoksa_none(self) -> None:
        p = self._pasaj()
        self.assertIn("ozet", p, "pasaj `ozet` anahtarını taşımıyor")
        self.assertIsNone(p["ozet"])

    def test_ozet_varsa_tasinir(self) -> None:
        self.repo.set_ozet({self.cid: OZET_METNI})
        self.assertEqual(self._pasaj()["ozet"], OZET_METNI)

    def test_bos_ozet_none_olur(self) -> None:
        """Boş dize «özet var» sayılmaz: arayüzde boş kutu çıkardı."""
        self.repo.set_ozet({self.cid: "   "})
        self.assertIsNone(self._pasaj()["ozet"])

    def test_ham_metin_hala_tam(self) -> None:
        """Özet EKLENİR, ham metnin yerine GEÇMEZ: denetim tam metne bakar."""
        self.repo.set_ozet({self.cid: OZET_METNI})
        self.assertEqual(self._pasaj()["text"], UZUN_METIN)


class TestCikarimsalCevap(RagOzetTestBase):
    """LLM kapalıyken cevap gövdesi — asıl kusurun bulunduğu yer."""

    def _cevap(self) -> str:
        return rag.answer(self.repo, "Konut finansmanı koşulları nelerdir?").text

    def test_ozet_varsa_ai_ozeti_basilir(self) -> None:
        self.repo.set_ozet({self.cid: OZET_METNI})
        metin = self._cevap()
        self.assertIn("AI Özeti", metin)
        self.assertIn(OZET_METNI, metin)

    def test_ozet_varsa_ham_metin_dokulmez(self) -> None:
        self.repo.set_ozet({self.cid: OZET_METNI})
        metin = self._cevap()
        self.assertNotIn(UZUN_METIN, metin)
        self.assertLess(len(metin), len(UZUN_METIN) // 4,
                        "cevap hâlâ belge boyunda")

    def test_ozet_yoksa_uydurulmaz(self) -> None:
        """Kırpılmış ham metin «AI Özeti» diye SUNULMAZ."""
        metin = self._cevap()
        self.assertNotIn("AI Özeti:", metin)
        self.assertIn("AI Özeti üretilmedi", metin)
        self.assertIn("özet değil", metin)

    def test_ozet_yoksa_metin_kirpilir(self) -> None:
        metin = self._cevap()
        self.assertNotIn(UZUN_METIN, metin)
        # Cevap kutusu bir belge görüntüleyicisi değil: kırpma gerçek olmalı.
        self.assertLess(len(metin), len(UZUN_METIN) // 4)
        self.assertIn("…", metin)

    def test_kaynak_hala_tam_metni_tasir(self) -> None:
        """Kısaltma denetlenebilirliği azaltmaz: pasajda tam metin durur."""
        a = rag.answer(self.repo, "Konut finansmanı koşulları nelerdir?")
        self.assertEqual(a.passages[0]["text"], UZUN_METIN)

    def test_banka_adi_yoksa_none_basilmaz(self) -> None:
        """Eski f-string `bank=None` iken ekrana 'None' yazardı."""
        metin = rag._cikarimsal_cevap({"bank": None, "text": "Kısa metin.",
                                       "ozet": None})
        self.assertNotIn("None", metin)


class TestArayuzEtiketi(unittest.TestCase):
    """`ChatPanel.tsx` — etiket «AI Özeti», ham metne erişim korunur."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.tsx = (_KOK / "web" / "app" / "components" / "ChatPanel.tsx"
                   ).read_text(encoding="utf-8")
        cls.css = (_KOK / "web" / "app" / "styles" / "components.css"
                   ).read_text(encoding="utf-8")

    def test_ai_ozeti_etiketi_var(self) -> None:
        self.assertIn("AI Özeti", self.tsx)

    def test_llm_ozeti_etiketi_kalmadi(self) -> None:
        """Kullanıcıya dönük etiket «LLM Özeti» değil «AI Özeti»."""
        for yasak in ("LLM Özeti", "LLM özeti"):
            self.assertNotIn(yasak, self.tsx)

    def test_ozetsiz_durum_adlandirilmis(self) -> None:
        self.assertIn("AI Özeti yok", self.tsx)
        self.assertIn("AI Özeti üretilmedi", self.tsx)

    def test_ham_metin_katlanir_kutuda_erisilebilir(self) -> None:
        """Kısaltma erişimi öldürmemeli: tam metin `<details>` içinde durur."""
        self.assertIn("<details", self.tsx)
        self.assertIn("Ham metnin tamamı", self.tsx)

    def test_yeni_siniflarin_css_karsiligi_var(self) -> None:
        """`scripts.css_sinif_denetimi` ile aynı kural, burada da kilitli."""
        for sinif in ("kaynak-govde", "kaynak-ozet", "kaynak-ozet-yok",
                      "kaynak-onizleme", "kaynak-ham", "kaynak-ham-govde"):
            with self.subTest(sinif=sinif):
                self.assertIn(f".{sinif}", self.css)


try:  # pragma: no cover - ortama bağlı
    import httpx  # noqa: F401
    from fastapi.testclient import TestClient
    HAS_API = True
except ModuleNotFoundError:  # pragma: no cover
    HAS_API = False


@unittest.skipUnless(HAS_API, "fastapi/httpx yok — API sözleşme testi atlanıyor")
class TestChatUcuOzetSozlesmesi(unittest.TestCase):
    """`POST /chat` — her kaynak kaydında `ozet` anahtarı bulunur."""

    @classmethod
    def setUpClass(cls) -> None:
        from src.api import main as api_main
        from src.db.factory import create_repository

        # `Repository(":memory:")` DEĞİL: FastAPI `def` uçlarını threadpool'da
        # koşturur ve sqlite bağlantısı onu oluşturan thread'e kilitlidir
        # (gerekçe `tests/test_api_sozlesme.py` içinde uzun uzun yazılı).
        cls.repo = create_repository(database_path=":memory:", thread_safe=True)
        cls.cid = cls.repo.insert_campaign(
            build_campaign(UZUN_METIN, bank_slug="ornek-katilim",
                           campaign_type="Konut Finansmanı"),
            clean_text=UZUN_METIN)
        cls.repo.set_ozet({cls.cid: OZET_METNI})
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

    def _sources(self, soru: str) -> tuple[dict, list]:
        r = self.client.post("/chat", json={"question": soru})
        self.assertEqual(r.status_code, 200, r.text)
        veri = r.json()
        return veri, veri["sources"]

    def test_rag_yolunda_ozet_anahtari_var(self) -> None:
        veri, sources = self._sources("Konut finansmanı koşulları nelerdir?")
        self.assertEqual(veri["handler"], "rag")
        self.assertTrue(sources)
        for s in sources:
            self.assertIn("ozet", s)

    def test_rag_yolunda_ozet_gercekten_doner(self) -> None:
        _, sources = self._sources("Konut finansmanı koşulları nelerdir?")
        self.assertEqual(sources[0]["ozet"], OZET_METNI)

    def test_yapisal_yolda_ozet_anahtari_null(self) -> None:
        """Dar kanıt penceresi zaten kısa: orada özet YOK ve bu doğru cevap."""
        _, sources = self._sources("En düşük kâr payı oranı hangi bankada?")
        self.assertTrue(sources)
        for s in sources:
            self.assertIn("ozet", s)
            self.assertIsNone(s["ozet"])

    def test_cevap_govdesi_belge_boyunda_degil(self) -> None:
        veri, _ = self._sources("Konut finansmanı koşulları nelerdir?")
        self.assertLess(len(veri["answer"]), len(UZUN_METIN) // 4)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
