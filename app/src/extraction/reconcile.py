"""Uzlaştırma (reconciliation) — 3 katmanı tek alan kümesinde birleştirir.

İlgili: ../../decisions/ner-fine-tune-yerine-kural-few-shot.md (kurallar BİRİNCİL)
        ../../syntheses/teknik-cozum-mimarisi.md
        CLAUDE.md §3

Kural: kural çıktısı varsa onu tercih et → boşlukları LLM ile doldur → her alana
confidence + source_span. Alan hiçbir katmanda yoksa üretilmez (null + uydurma yok).
"""

from __future__ import annotations

from typing import Optional

from ..schemas import Campaign, ExtractedField, Extractor
from .llm.extractor import LLMExtractor, NullLLMExtractor
from .llm.schema import EXTRACTION_FIELDS
from .rules.extract import extract_all as rule_extract

# Katman önceliği: kural > ner > llm (eşit güvende kural kazanır)
_PRIORITY = {Extractor.RULE: 3, Extractor.NER: 2, Extractor.LLM: 1}


def reconcile(text: str, llm: Optional[LLMExtractor] = None) -> list[ExtractedField]:
    """Kural + (varsa) LLM çıktısını birleştirir.

    1) Kuralları çalıştır (birincil).
    2) Eksik alanları belirle, LLM'e yalnız onları sor.
    3) Aynı alan birden çok katmanda varsa öncelik + güvene göre seç.
    """
    llm = llm or NullLLMExtractor()

    by_field: dict[str, ExtractedField] = {}
    for f in rule_extract(text):
        if f.is_present:
            by_field[f.field_name] = f

    missing = [name for name in EXTRACTION_FIELDS if name not in by_field]
    if missing and llm.available:
        for f in llm.extract(text, missing):
            if not f.is_present:
                continue
            cur = by_field.get(f.field_name)
            if cur is None or _wins(f, cur):
                by_field[f.field_name] = f

    return list(by_field.values())


def _wins(new: ExtractedField, cur: ExtractedField) -> bool:
    """Yeni alan mevcut olanı geçer mi? Önce katman önceliği, sonra güven."""
    pn, pc = _PRIORITY[new.extractor], _PRIORITY[cur.extractor]
    if pn != pc:
        return pn > pc
    return new.confidence > cur.confidence


def build_campaign(text: str, bank_slug: str, source_url: Optional[str] = None,
                   llm: Optional[LLMExtractor] = None,
                   campaign_type: Optional[str] = None) -> Campaign:
    """Metinden tam Campaign nesnesi üretir (çıkarım + uzlaştırma)."""
    fields = reconcile(text, llm=llm)
    return Campaign(
        bank_slug=bank_slug,
        raw_text=text,
        source_url=source_url,
        campaign_type=campaign_type,
        fields=fields,
    )
