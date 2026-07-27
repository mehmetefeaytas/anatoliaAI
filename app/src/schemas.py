"""Çekirdek veri şemaları.

Deterministik katman için stdlib dataclass kullanılır (sıfır bağımlılık, hemen
test edilebilir). LLM katmanı (`guided_json`) Pydantic'e bu şemalardan türetilir.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class Extractor(str, Enum):
    """Bir alanı hangi katmanın çıkardığı."""

    RULE = "rule"
    NER = "ner"
    LLM = "llm"


@dataclass
class ExtractedField:
    """Tek bir çıkarılmış alan.

    canonical_value: normalize edilmiş değer (oran→float, para→dict, vade→int...).
    raw_value: kaynak metindeki ham ifade.
    confidence: [0, 1] güven skoru.
    source_span: değerin geçtiği metin parçası (insan okuru için).
    span_start/span_end: `raw_value`'nun kaynak metindeki KARAKTER OFFSET'leri.

    Neden hem metin hem offset: `source_span` bir ±40 karakterlik pencere
    metnidir ve orijinal metinde güvenilir biçimde geri bulunamaz (aynı pencere
    iki kez geçebilir, `.strip()` kenarları kaybeder). Dashboard'daki kaynak
    vurgulaması (yenilikçilik hedefi #1, CLAUDE.md §18) kesin offset ister.
    Offset'ler yoksa `None` — geriye uyumlu.

    confidence_source: skorun nereden geldiği ('rule_heuristic' | 'logprob' |
    'self_reported' | 'constant'). Kalibrasyon (ECE) hesaplanırken farklı
    kaynakların karıştırılmaması için gerekli.
    """

    field_name: str
    raw_value: Optional[str]
    canonical_value: Any
    confidence: float
    source_span: Optional[str]
    extractor: Extractor = Extractor.RULE
    span_start: Optional[int] = None
    span_end: Optional[int] = None
    confidence_source: str = "constant"

    @property
    def is_present(self) -> bool:
        """Alan gerçekten bulundu mu (halüsinasyon değil)."""
        return self.canonical_value is not None

    def verify_span(self, text: str) -> bool:
        """Offset'lerin gerçekten `raw_value`'yu gösterdiğini doğrular.

        Açıklanabilirlik iddiasının kendi kendini denetlemesi: vurgulanan yer
        ile raporlanan değer uyuşmuyorsa UI yanlış yeri boyar. Eval bu kontrolü
        tüm çıktılar üzerinde koşturur.
        """
        if self.span_start is None or self.span_end is None:
            return False
        if not (0 <= self.span_start <= self.span_end <= len(text)):
            return False
        return text[self.span_start:self.span_end] == (self.raw_value or "")


# 8 kampanya türü — sınıflandırma etiketleri (bkz. ../concepts/kampanya-turleri.md)
CAMPAIGN_TYPES = [
    "Finansman",
    "İhtiyaç Finansmanı",
    "Konut Finansmanı",
    "Taşıt Finansmanı",
    "Kart",
    "Alışveriş Puanı",
    "Yeni Müşteri",
    "Yatırım Ürünü",
]


@dataclass
class Campaign:
    """Tek bir kampanya kaydı ve çıkarılmış alanları."""

    bank_slug: str
    raw_text: str
    source_url: Optional[str] = None
    campaign_type: Optional[str] = None
    fields: list[ExtractedField] = field(default_factory=list)

    def get(self, field_name: str) -> Optional[ExtractedField]:
        for f in self.fields:
            if f.field_name == field_name:
                return f
        return None
