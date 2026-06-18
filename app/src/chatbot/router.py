"""Soru router'ı — sayısal/karşılaştırmalı mı, açıklama mı?

İlgili: ../../decisions/hibrit-chatbot-text-to-sql-rag.md
        CLAUDE.md §5

Sayısal/karşılaştırmalı sorular → yapısal sorgu (text-to-SQL benzeri).
Koşul/açıklama soruları → RAG. Router anahtar-kelime + alan eşleme ile çalışır;
LLM gerektirmez (offline). Belirsizse 'rag'a düşer (güvenli varsayılan).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

# Soru içindeki ifade → alan adı
_FIELD_KEYWORDS = {
    "kar_payi_orani": ["kâr payı", "kar payı", "getiri oran", "kâr oran", "oran"],
    "vade_ay": ["vade", "ödeme süresi", "kaç ay", "kaç yıl", "ay vade"],
    "finansman_tutari": ["tutar", "limit", "ne kadar finansman", "kredi tutar"],
    "tahsis_ucreti": ["tahsis", "dosya masraf"],
    "masraf_durumu": ["masraf", "ücret", "masrafsız", "ücretsiz"],
    "taksit_sayisi": ["taksit"],
}

# Karşılaştırma/agregasyon niyeti
_SUPERLATIVE_LOW = ["en düşük", "en az", "en ucuz", "en avantajlı", "minimum"]
_SUPERLATIVE_HIGH = ["en yüksek", "en fazla", "en uzun", "en çok", "maksimum", "en büyük"]
_LIST_INTENT = ["hangi banka", "hangi bankalar", "listele", "göster", "var mı",
                "veren", "sunan", "olanlar"]


@dataclass
class Route:
    handler: str                 # 'structured' | 'rag'
    field: Optional[str]         # ilgili alan (structured ise)
    intent: Optional[str]        # 'lowest' | 'highest' | 'list' | 'filter'
    filters: dict                # ör. {"vade_ay_min": 36, "campaign_type": "Konut Finansmanı"}


def route(question: str) -> Route:
    q = question.lower()

    field = _detect_field(q)
    intent = _detect_intent(q)
    filters = _detect_filters(q)

    # sayısal/karşılaştırmalı sinyal varsa yapısal sorgu
    if field and (intent or filters):
        return Route("structured", field, intent or "list", filters)
    # sadece superlatif + alan
    if field and intent in ("lowest", "highest"):
        return Route("structured", field, intent, filters)
    # aksi halde RAG (açıklama/koşul soruları)
    return Route("rag", field, intent, filters)


def _detect_field(q: str) -> Optional[str]:
    for fname, kws in _FIELD_KEYWORDS.items():
        if any(kw in q for kw in kws):
            return fname
    return None


def _detect_intent(q: str) -> Optional[str]:
    if any(s in q for s in _SUPERLATIVE_LOW):
        return "lowest"
    if any(s in q for s in _SUPERLATIVE_HIGH):
        return "highest"
    if any(s in q for s in _LIST_INTENT):
        return "list"
    return None


def _detect_filters(q: str) -> dict:
    filters: dict = {}
    # "36 ay" gibi vade filtresi: "X ay veren/üzeri"
    m = re.search(r"(\d{1,3})\s*ay", q)
    if m and ("veren" in q or "üzeri" in q or "ve üzeri" in q or "en az" in q):
        filters["vade_ay_min"] = int(m.group(1))
    # kampanya türü filtresi
    type_map = {
        "konut": "Konut Finansmanı", "taşıt": "Taşıt Finansmanı",
        "tasit": "Taşıt Finansmanı", "ihtiyaç": "İhtiyaç Finansmanı",
        "kart": "Kart", "yatırım": "Yatırım Ürünü",
    }
    for kw, label in type_map.items():
        if kw in q:
            filters["campaign_type"] = label
            break
    return filters
