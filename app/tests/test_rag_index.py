"""RAG ters dizini (inverted index) eşdeğerlik testleri.

`KeywordRetriever` 31 Tem'de ön-hesaplanmış ters dizine geçti (soru başına tüm
korpusu tokenize etmek yerine). Bir hız optimizasyonunun tek kabul kriteri var:
**sonuçlar değişmeyecek.** Bu dosya o kriteri kilitler — dizinsiz referans
uygulama (eski kodun birebir kopyası) ile dizinli üretim kodu aynı korpusta,
aynı sorularla karşılaştırılır: sıralama, skor, pasaj sayısı, eşik davranışı.

İlgili: src/chatbot/rag.py, tests/test_safety.py (KAPI 5 kanıt eşiği)
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.chatbot import rag  # noqa: E402
from src.chatbot.bot import Chatbot  # noqa: E402
from src.chatbot.structured import _apply_filters  # noqa: E402
from src.db.repository import Repository  # noqa: E402
from src.extraction.reconcile import build_campaign  # noqa: E402


# Farklı uzunlukta, farklı bankalardan, eşit-skor üretebilecek tekrarlı
# metinler içeren korpus — tie-break sırasını da sınamak için.
CORPUS = [
    ("kuveyt-turk", ("Konut finansmanında kâr payı oranı %1,89, 120 ay vade. "
                     "Tahsis ücreti alınmaz."), "Konut Finansmanı"),
    ("albaraka", "Konut finansmanı kâr payı oranı %2,49, 96 ay vade.",
     "Konut Finansmanı"),
    ("turkiye-finans", "Taşıt finansmanı kâr payı %1,99, 48 ay vade, masrafsız.",
     "Taşıt Finansmanı"),
    ("ziraat-katilim", "TAŞIT FİNANSMANI KAMPANYASI: 36 ay vade, %2,10 kâr payı.",
     "Taşıt Finansmanı"),
    ("vakif-katilim", ("Yeni müşterilere özel alışveriş puanı kampanyası. "
                       "Kampanya 31 Aralık 2026 tarihine kadar geçerlidir."),
     "Alışveriş Puanı"),
    ("turkiye-emlak-katilim", "İhtiyaç finansmanı 24 ay vade ile sunulmaktadır.",
     "İhtiyaç Finansmanı"),
    # Aynı metnin iki bankada tekrarı: eşit skor üretir, tie-break sınanır.
    ("hayat-finans", "Konut finansmanı kâr payı oranı %2,49, 96 ay vade.",
     "Konut Finansmanı"),
    ("tom-katilim", "", "Kart"),  # boş metin: dizine hiç girmemeli
]

QUESTIONS = [
    "Taşıt finansmanı kampanyasına kimler başvurabilir?",
    "Kampanya hangi tarihe kadar geçerli?",
    "Konut finansmanı kâr payı oranı nedir?",
    "Masrafsız kampanyaların koşulları neler?",
    "Yeni müşteri olmanın avantajı nedir?",
    "Helal gıda alışverişinde puan veren kampanya var mı?",  # eşiğin altında
    "Vade kaç ay?",
    "kâr payı",
    "",                                                       # boş soru
    "xyzzy plugh",                                            # hiç eşleşmeyen
    "TAŞIT FİNANSMANI VADE KÂR PAYI",                         # ALL-CAPS
]


def seed(repo: Repository) -> None:
    for slug, text, ctype in CORPUS:
        if not text:
            # build_campaign boş metni reddedebilir; boş belgeyi doğrudan
            # yazıyoruz ki "dizine girmeyen belge" yolu gerçekten sınansın.
            repo.upsert_bank(slug, slug)
            repo.conn.execute(
                "INSERT INTO campaigns(bank_id, raw_text, clean_text, "
                "source_url, scraped_at, campaign_type) VALUES "
                "((SELECT id FROM banks WHERE slug=?), '', '', NULL, NULL, ?)",
                (slug, ctype))
            repo.conn.commit()
            continue
        repo.insert_campaign(build_campaign(text, bank_slug=slug,
                                            campaign_type=ctype))


class UnindexedRetriever:
    """Dizin ÖNCESİ referans uygulama — eski `KeywordRetriever.retrieve`.

    Bilerek birebir kopya: optimizasyonun doğruluk referansı budur. Üretim
    kodu değişse de bu sınıf değişmez.
    """

    def __init__(self, repo: Repository, min_overlap: int = rag.MIN_OVERLAP):
        self.repo = repo
        self.min_overlap = min_overlap
        self._docs = repo.all_campaigns()

    def retrieve(self, query: str, k: int = 3) -> list[dict]:
        qtok = set(rag._tokenize(query))
        scored = []
        for d in self._docs:
            dtok = set(rag._tokenize(d.get("raw_text", "")))
            if not dtok:
                continue
            overlap = len(qtok & dtok)
            if overlap < self.min_overlap:
                continue
            score = overlap / (len(qtok) ** 0.5 + 1)
            scored.append({
                "bank": d.get("bank_name") or d.get("bank"),
                "source_url": d.get("source_url"),
                "text": d.get("raw_text"),
                "score": round(score, 3),
            })
        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:k]


class TestIndexEquivalence(unittest.TestCase):
    """Dizinli ve dizinsiz retriever BİREBİR aynı sonucu vermeli."""

    @classmethod
    def setUpClass(cls):
        cls.repo = Repository(":memory:")
        seed(cls.repo)
        cls.indexed = rag.KeywordRetriever(cls.repo)
        cls.reference = UnindexedRetriever(cls.repo)

    @classmethod
    def tearDownClass(cls):
        cls.repo.close()

    def test_same_results_for_every_question(self):
        for q in QUESTIONS:
            with self.subTest(soru=q):
                self.assertEqual(self.indexed.retrieve(q),
                                 self.reference.retrieve(q))

    def test_same_results_for_every_k(self):
        for k in (1, 2, 3, 5, 20):
            for q in QUESTIONS:
                with self.subTest(soru=q, k=k):
                    self.assertEqual(self.indexed.retrieve(q, k=k),
                                     self.reference.retrieve(q, k=k))

    def test_same_results_for_every_threshold(self):
        """min_overlap=0 dahil: eşiksiz yol da eşdeğer kalmalı."""
        for thr in (0, 1, 2, 3, 5):
            idx = rag.KeywordRetriever(self.repo, min_overlap=thr)
            ref = UnindexedRetriever(self.repo, min_overlap=thr)
            for q in QUESTIONS:
                with self.subTest(soru=q, esik=thr):
                    self.assertEqual(idx.retrieve(q, k=10), ref.retrieve(q, k=10))

    def test_tie_order_is_corpus_order(self):
        """Eşit skorlu iki belge korpus sırasını korur (kararlı sıralama)."""
        q = "Konut finansmanı kâr payı oranı nedir?"
        banks = [p["bank"] for p in self.indexed.retrieve(q, k=10)]
        self.assertEqual(banks, [p["bank"] for p in self.reference.retrieve(q, k=10)])

    def test_empty_document_never_retrieved(self):
        for q in QUESTIONS:
            for p in self.indexed.retrieve(q, k=10):
                self.assertNotEqual(p["text"], "")


class TestIndexInvariants(unittest.TestCase):
    def setUp(self):
        self.repo = Repository(":memory:")
        seed(self.repo)

    def tearDown(self):
        self.repo.close()

    def test_threshold_still_blocks_weak_overlap(self):
        """MIN_OVERLAP=2 davranışı korunuyor (sessiz halüsinasyon koruması)."""
        r = rag.KeywordRetriever(self.repo)
        self.assertEqual(
            r.retrieve("Helal gıda alışverişinde puan veren kampanya var mı?"), [])

    def test_index_is_built_once_not_per_query(self):
        """`retrieve` depoya gitmemeli — dizin kurulumda hazırlanır."""
        r = rag.KeywordRetriever(self.repo)
        calls = []
        original = self.repo.all_campaigns
        self.repo.all_campaigns = lambda: (calls.append(1), original())[1]
        for q in QUESTIONS:
            r.retrieve(q)
        self.assertEqual(calls, [], "retrieve() korpusu yeniden okudu")

    def test_reindex_picks_up_new_documents(self):
        r = rag.KeywordRetriever(self.repo)
        before = r.document_count
        repo2_text = "Karz-ı hasen kampanyası koşulları burada açıklanmıştır."
        self.repo.insert_campaign(build_campaign(repo2_text, bank_slug="adil-katilim",
                                                 campaign_type="Finansman"))
        self.assertEqual(r.document_count, before)   # dizin fotoğraf
        r.reindex()
        self.assertEqual(r.document_count, before + 1)


class TestChatbotReusesIndex(unittest.TestCase):
    """Chatbot dizini bot ömrü boyunca BİR kez kurmalı."""

    def setUp(self):
        self.repo = Repository(":memory:")
        seed(self.repo)

    def tearDown(self):
        self.repo.close()

    def test_retriever_is_shared_across_questions(self):
        bot = Chatbot(self.repo)
        first = bot._ensure_retriever()
        for q in QUESTIONS:
            bot.ask(q)
        self.assertIs(bot._ensure_retriever(), first)

    def test_index_built_eagerly_when_repo_has_data(self):
        """Veri hazırsa maliyet açılışta ödenir, ilk soruda değil."""
        bot = Chatbot(self.repo)
        self.assertIsNotNone(bot._retriever)

    def test_index_deferred_when_repo_is_empty(self):
        """Boş depoyla kurulan bot bayat (stale) dizin tutmamalı."""
        empty = Repository(":memory:")
        try:
            bot = Chatbot(empty)
            self.assertIsNone(bot._retriever)
            seed(empty)
            a = bot.ask("Taşıt finansmanı kampanyasına kimler başvurabilir?")
            self.assertEqual(a.handler, "rag")
            self.assertTrue(a.sources, "sonradan doldurulan depo görülmedi")
        finally:
            empty.close()

    def test_answers_match_fresh_retriever_per_question(self):
        """Dizin paylaşımı yanıtları değiştirmemeli."""
        shared = Chatbot(self.repo)
        for q in QUESTIONS:
            with self.subTest(soru=q):
                fresh = Chatbot(self.repo)
                fresh._retriever = None          # her soruda yeni dizin kur
                self.assertEqual(shared.ask(q).text, fresh.ask(q).text)


class TestStructuredVadeFilter(unittest.TestCase):
    """vade_ay_min filtresi N+1 sorgudan toplu sorguya geçti — sonuç aynı."""

    def setUp(self):
        self.repo = Repository(":memory:")
        seed(self.repo)

    def tearDown(self):
        self.repo.close()

    def _reference_filter(self, rows: list[dict], vmin: int) -> list[dict]:
        """Eski N+1 uygulaması — doğruluk referansı."""
        return [r for r in rows
                if isinstance(self.repo.field_value(r["campaign_id"], "vade_ay"),
                              (int, float))
                and self.repo.field_value(r["campaign_id"], "vade_ay") >= vmin]

    def test_batched_filter_matches_per_row_lookup(self):
        rows = self.repo.query_fields("kar_payi_orani")
        for vmin in (0, 12, 24, 36, 48, 96, 120, 999):
            with self.subTest(vade_ay_min=vmin):
                self.assertEqual(
                    _apply_filters(self.repo, rows, {"vade_ay_min": vmin}),
                    self._reference_filter(rows, vmin))


if __name__ == "__main__":
    unittest.main()
