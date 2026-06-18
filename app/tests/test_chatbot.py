"""Dalga 3 testleri: chatbot router + yapısal sorgu + RAG (offline)."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.db.repository import Repository  # noqa: E402
from src.extraction.reconcile import build_campaign  # noqa: E402
from src.chatbot.router import route  # noqa: E402
from src.chatbot.bot import Chatbot  # noqa: E402


def seed(repo):
    data = [
        ("kuveyt-turk", "Konut finansmanında kâr payı oranı %1,89, 120 ay vade.", "Konut Finansmanı"),
        ("albaraka", "Konut finansmanı kâr payı oranı %2,49, 96 ay vade.", "Konut Finansmanı"),
        ("turkiye-finans", "Taşıt finansmanı kâr payı %1,99, 48 ay vade, masrafsız.", "Taşıt Finansmanı"),
    ]
    for slug, text, ctype in data:
        repo.insert_campaign(build_campaign(text, bank_slug=slug, campaign_type=ctype))


class TestRouter(unittest.TestCase):
    def test_superlative_is_structured(self):
        r = route("Hangi bankada en düşük kâr payı var?")
        self.assertEqual(r.handler, "structured")
        self.assertEqual(r.field, "kar_payi_orani")
        self.assertEqual(r.intent, "lowest")

    def test_filter_is_structured(self):
        r = route("36 ay ve üzeri vade veren konut finansmanları")
        self.assertEqual(r.handler, "structured")
        self.assertEqual(r.filters.get("campaign_type"), "Konut Finansmanı")

    def test_descriptive_is_rag(self):
        r = route("Konut finansmanı için gerekli belgeler nelerdir?")
        self.assertEqual(r.handler, "rag")


class TestChatbotEndToEnd(unittest.TestCase):
    def setUp(self):
        self.repo = Repository(":memory:")
        seed(self.repo)
        self.bot = Chatbot(self.repo)

    def tearDown(self):
        self.repo.close()

    def test_lowest_rate(self):
        a = self.bot.ask("Hangi bankada en düşük kâr payı oranı var?")
        self.assertEqual(a.handler, "structured")
        self.assertIn("kuveyt-turk".replace("-", ""), a.text.lower().replace("-", "").replace(" ", ""))

    def test_highest_term(self):
        a = self.bot.ask("En uzun vade hangi bankada?")
        self.assertEqual(a.handler, "structured")
        self.assertIn("120", a.text)

    def test_rag_fallback(self):
        a = self.bot.ask("Taşıt finansmanı koşulları nelerdir?")
        self.assertEqual(a.handler, "rag")
        self.assertTrue(len(a.sources) >= 1)


if __name__ == "__main__":
    unittest.main()
