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
from ..preprocessing.clean import tr_fold

# En az kaç ANLAMLI sözcük örtüşmesi bir pasajı "kanıt" saymaya yeter.
# 1 örtüşme yetersizdir: "Helal gıda alışverişinde puan veren kampanya var mı?"
# sorusu yalnızca 'kampanya' üzerinden konut finansmanı metnini getiriyordu ve
# alakasız pasajı "ilgili kampanya" diye sunuyordu — sessiz halüsinasyon.
# Eşiğin altındaysa hiç pasaj döndürülmez; çekimserlik kapısı (safety KAPI 5)
# dürüstçe "verimde yok" der.
MIN_OVERLAP = 2

# Soru kalıbı sözcükleri: örtüşme sayımında sinyal değil gürültüdür.
_STOPWORDS = frozenset("""
bir bu şu o ve ile için mi mı mu mü var yok ne nedir nelerdir hangi hangisi
kaç daha en de da den dan te ta ten tan olan olarak göre gibi ama veya her
tüm ben sen siz bana beni bize nasıl niye neden misin misiniz mısın mısınız
kadar sonra önce çok az ki ise ancak yani hem ya
""".split())


@dataclass
class RagAnswer:
    text: str
    passages: list[dict]   # [{"bank","source_url","text","score"}]


def _tokenize(text: str) -> list[str]:
    """TR-doğru katlama + durak sözcük ayıklaması.

    `str.lower()` KULLANILMAZ: Türkçede hatalıdır ('TAŞIT'.lower() -> 'taşit',
    'İ'.lower() -> 'i' + U+0307 birleşen nokta). Bu retriever'da eskiden
    `.lower()` vardı ve ALL-CAPS banka başlıklarını sessizce kaçırıyordu
    (bkz. preprocessing/clean.tr_fold docstring'i).
    """
    toks = re.findall(r"[a-zçğıöşü0-9]+", tr_fold(text or ""))
    return [t for t in toks if t not in _STOPWORDS]


class KeywordRetriever:
    """Basit kelime-örtüşme (Jaccard-benzeri) retriever — offline."""

    def __init__(self, repo: Repository, min_overlap: int = MIN_OVERLAP):
        self.repo = repo
        self.min_overlap = min_overlap
        self._docs = repo.all_campaigns()

    def retrieve(self, query: str, k: int = 3) -> list[dict]:
        qtok = set(_tokenize(query))
        scored = []
        for d in self._docs:
            dtok = set(_tokenize(d.get("raw_text", "")))
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
