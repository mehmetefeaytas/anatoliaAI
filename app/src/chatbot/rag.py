"""RAG katmanı — açıklama/koşul soruları için.

İlgili: ../../decisions/hibrit-chatbot-text-to-sql-rag.md
        ../../concepts/web-scraping.md (içerik kaynağı), CLAUDE.md §5, §7

İki retriever:
- KeywordRetriever: TF-örtüşme tabanlı, sıfır bağımlılık, offline fallback.
- VectorRetriever: bge-m3 + pgvector (üretim). Embedding modeli yoksa
  KeywordRetriever kullanılır.

Üretim cevabı yerel LLM ile sentezlenir; LLM yoksa en alakalı pasajlar
"alıntı (extractive)" olarak döndürülür — yine kaynağa dayalı, halüsinasyonsuz.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

from ..db.repository import Repository


@dataclass
class RagAnswer:
    text: str
    passages: list[dict]   # [{"bank","source_url","text","score"}]


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-zçğıöşü0-9]+", (text or "").lower())


class KeywordRetriever:
    """Basit kelime-örtüşme (Jaccard-benzeri) retriever — offline."""

    def __init__(self, repo: Repository):
        self.repo = repo
        self._docs = repo.all_campaigns()

    def retrieve(self, query: str, k: int = 3) -> list[dict]:
        qtok = set(_tokenize(query))
        scored = []
        for d in self._docs:
            dtok = set(_tokenize(d.get("raw_text", "")))
            if not dtok:
                continue
            overlap = len(qtok & dtok)
            if overlap == 0:
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


def answer(repo: Repository, question: str, llm=None, retriever=None) -> RagAnswer:
    """Soru için pasaj getirir; LLM varsa sentezler, yoksa alıntılar."""
    retriever = retriever or KeywordRetriever(repo)
    passages = retriever.retrieve(question)
    if not passages:
        return RagAnswer("İlgili bir kampanya metni bulunamadı.", [])

    if llm is not None and getattr(llm, "available", False):
        context = "\n---\n".join(f"[{p['bank']}] {p['text']}" for p in passages)
        try:
            resp = llm.client.generate_json(
                "Sadece verilen bağlamdan, kaynağa dayalı, kısa Türkçe cevap ver. "
                "Bağlamda yoksa 'bilgi bulunamadı' de. Çıktı: {\"cevap\": \"...\"}",
                f"Bağlam:\n{context}\n\nSoru: {question}",
                {"type": "object", "properties": {"cevap": {"type": "string"}}},
            )
            return RagAnswer(resp.get("cevap", ""), passages)
        except Exception:
            pass

    # LLM yok → extractive: en alakalı pasajı kaynağıyla döndür
    top = passages[0]
    text = f"İlgili kampanya ({top['bank']}): {top['text']}"
    return RagAnswer(text, passages)
