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

from ..preprocessing.clean import tr_fold_ascii
from .safety import INTEREST_FIELD_HINT, detect_banks, mentions_interest_term

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

# Kullanıcı sorusu ALL-CAPS veya diakritiksiz gelebilir ("EN DÜŞÜK KÂR PAYI",
# "en dusuk kar payi"). Eşleşme tr_fold_ascii üzerinden yapılır; anahtar
# kelimeler de modül yüklenirken aynı forma indirgenir.
_F = tr_fold_ascii
_FOLDED_FIELD_KEYWORDS = {k: [_F(v) for v in vals]
                          for k, vals in _FIELD_KEYWORDS.items()}
_FOLDED_SUP_LOW = [_F(s) for s in _SUPERLATIVE_LOW]
_FOLDED_SUP_HIGH = [_F(s) for s in _SUPERLATIVE_HIGH]
_FOLDED_LIST_INTENT = [_F(s) for s in _LIST_INTENT]

# Kampanya türü filtresi: soru içindeki ipucu → 8 sınıftan biri
_FOLDED_TYPE_MAP = {_F(k): v for k, v in {
    "konut": "Konut Finansmanı", "taşıt": "Taşıt Finansmanı",
    "ihtiyaç": "İhtiyaç Finansmanı", "kart": "Kart",
    "yatırım": "Yatırım Ürünü",
}.items()}


@dataclass
class Route:
    handler: str                 # 'structured' | 'rag'
    field: Optional[str]         # ilgili alan (structured ise)
    intent: Optional[str]        # 'lowest' | 'highest' | 'list' | 'filter'
    filters: dict                # ör. {"vade_ay_min": 36, "campaign_type": "Konut
                                 #      Finansmanı", "banks": ["kuveyt-turk"]}


def route(question: str) -> Route:
    q = tr_fold_ascii(question)

    field = _detect_field(q)
    intent = _detect_intent(q)
    filters = _detect_filters(q)

    # Terminoloji kapısı (girdi tarafı): kullanıcı konvansiyonel terimi
    # kullandıysa ("faiz en düşük hangi bankada?") soru REDDEDİLMEZ, doğru
    # alana (kâr payı oranı) yönlendirilir. Kendi alan sözlüğü zaten "oran"ı
    # yakalıyor; bu yedek, oran kelimesi hiç geçmeyen soruları kurtarır.
    # Sözcük sınırlı ve 'faizsiz' muaf — bkz. safety.mentions_interest_term.
    if field is None and mentions_interest_term(question):
        field = INTEREST_FIELD_HINT

    # sayısal/karşılaştırmalı sinyal varsa yapısal sorgu
    if field and (intent or filters):
        return Route("structured", field, intent or "list", filters)
    # sadece superlatif + alan
    if field and intent in ("lowest", "highest"):
        return Route("structured", field, intent, filters)
    # aksi halde RAG (açıklama/koşul soruları)
    return Route("rag", field, intent, filters)


def _detect_field(q: str) -> Optional[str]:
    for fname, kws in _FOLDED_FIELD_KEYWORDS.items():
        if any(kw in q for kw in kws):
            return fname
    return None


def _detect_intent(q: str) -> Optional[str]:
    if any(s in q for s in _FOLDED_SUP_LOW):
        return "lowest"
    if any(s in q for s in _FOLDED_SUP_HIGH):
        return "highest"
    if any(s in q for s in _FOLDED_LIST_INTENT):
        return "list"
    return None


def _detect_filters(q: str) -> dict:
    filters: dict = {}
    # "36 ay" gibi vade filtresi: "X ay veren/üzeri"
    m = re.search(r"(\d{1,3})\s*ay", q)
    # q katlanmış (ascii) geldiği için eşik sözcükleri de katlanmış yazılır.
    if m and any(s in q for s in ("veren", "uzeri", "ve uzeri", "en az")):
        filters["vade_ay_min"] = int(m.group(1))
    # kampanya türü filtresi
    for kw, label in _FOLDED_TYPE_MAP.items():
        if kw in q:
            filters["campaign_type"] = label
            break
    # banka filtresi — "Ziraat Katılım'ın konut kâr payı oranı nedir?" sorusu
    # BAŞKA bankaların satırlarıyla cevaplanmamalı. Banka verimizde yoksa
    # sonuç boş kalır ve çekimserlik kapısı (KAPI 5) devreye girer.
    # q zaten katlanmış; tr_fold_ascii idempotenttir, tekrar katlamak zararsız.
    banks = detect_banks(q)
    if banks:
        filters["banks"] = banks
    return filters
