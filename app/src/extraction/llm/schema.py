"""LLM çıkarımı için guided_json şeması.

İlgili: ../../../decisions/ner-fine-tune-yerine-kural-few-shot.md (kural + few-shot LLM)
        CLAUDE.md §19 (LLM çıktısı her zaman guided_json / şema ile zorunlu)

Bu JSON Schema, vLLM `guided_json` / Outlines / Ollama format kısıtı olarak
kullanılır. LLM serbest metin DÖNDÜRMEZ; yalnızca bu şemaya uyan JSON döndürür.
Her alan için değer + güven + kaynak parçası istenir; alan yoksa null.
"""

from __future__ import annotations

# Çıkarılacak alanlar (bkz. CLAUDE.md §9 veri modeli)
EXTRACTION_FIELDS = [
    "kar_payi_orani",
    "finansman_tutari",
    "vade_ay",
    "taksit_sayisi",
    "tahsis_ucreti",
    "masraf_durumu",
    "odul_miktari",
    "indirim_orani",
    "alisveris_puani",
    "kampanya_suresi",
    "kampanya_kosullari",
    "hedef_kitle",
]


def _field_obj() -> dict:
    """Tek alan için şema parçası: değer + güven + kaynak."""
    return {
        "type": ["object", "null"],
        "properties": {
            "value": {"type": ["string", "number", "object", "null"]},
            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
            "source_span": {"type": ["string", "null"]},
        },
        "required": ["value", "confidence"],
        "additionalProperties": False,
    }


def guided_json_schema() -> dict:
    """vLLM `guided_json`'a verilecek tam JSON Schema."""
    return {
        "type": "object",
        "properties": {name: _field_obj() for name in EXTRACTION_FIELDS},
        "additionalProperties": False,
    }


# Few-shot prompt iskeleti — kuralların kaçırdığı ÖRTÜK ifadeler için.
SYSTEM_PROMPT = """Sen katılım bankacılığı kampanya metinlerinden finansal bilgi \
çıkaran bir asistansın. SADECE verilen şemaya uyan JSON döndür. \
Kurallar:
- Bilgi metinde AÇIKÇA yoksa o alanı null bırak. ASLA değer UYDURMA.
- 'masrafsız/ücretsiz' = masraf 0 demektir (bilgi yok değil).
- Oranı yüzde olarak decimal ver (%2,05 -> 2.05). Aralık ise {"min":x,"max":y}.
- Para için {"value": sayı, "currency": "TRY"}.
- Vade her zaman AY cinsinden tamsayı.
- Her bulduğun alana 'source_span' (metindeki ilgili parça) ekle.
- Emin değilsen confidence değerini düşür."""

FEWSHOT = [
    {
        "text": "İlk 6 ay ödemesiz, sonrasında %1,89 kâr payı ile 120 aya varan konut finansmanı.",
        "json": {
            "kar_payi_orani": {"value": 1.89, "confidence": 0.9,
                               "source_span": "%1,89 kâr payı"},
            "vade_ay": {"value": 120, "confidence": 0.85,
                        "source_span": "120 aya varan"},
            "kampanya_kosullari": {"value": "İlk 6 ay ödemesiz", "confidence": 0.8,
                                   "source_span": "İlk 6 ay ödemesiz"},
        },
    }
]
