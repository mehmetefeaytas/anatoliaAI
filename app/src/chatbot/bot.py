"""Hibrit chatbot orkestrasyonu — router → yapısal sorgu / RAG.

İlgili: ../../decisions/hibrit-chatbot-text-to-sql-rag.md
        ../../entities/chatbot.md, CLAUDE.md §5
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from ..db.repository import Repository
from . import rag, structured
from .router import route


@dataclass
class ChatAnswer:
    text: str
    handler: str           # 'structured' | 'rag'
    field: Optional[str]
    sources: list          # kaynak satırları / pasajlar (açıklanabilirlik)


class Chatbot:
    """Tek giriş noktası: ask(question) → ChatAnswer."""

    def __init__(self, repo: Repository, llm=None):
        self.repo = repo
        self.llm = llm

    def ask(self, question: str) -> ChatAnswer:
        r = route(question)
        if r.handler == "structured" and r.field:
            ans = structured.answer(self.repo, r)
            sources = [{"bank": x.bank, "value": x.value, "source_span": x.source_span}
                       for x in ans.rows]
            return ChatAnswer(ans.text, "structured", r.field, sources)
        # rag
        ans = rag.answer(self.repo, question, llm=self.llm)
        return ChatAnswer(ans.text, "rag", r.field, ans.passages)
