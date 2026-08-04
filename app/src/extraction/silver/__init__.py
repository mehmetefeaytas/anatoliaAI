"""Gümüş (silver) etiket hattı — 8-sınıf sınıflandırıcı eğitim verisi.

Kapsam dışı (katılım olmayan) banka sayfalarından otomatik etiket üretir:
etiketleyici → denetleyici → kural katmanı ile üç oylu uzlaşma.

Bu paket **etiketleyici modeli içermez**; JSONL sözleşmesi üzerinden çalışır
(gerekçe: `contract.py` başlığı). Böylece teslim edilen sistemde ücretli
bağımlılık olmaz ve hat yerel modelle tekrar üretilebilir.
"""

from .consensus import (
    CONF_HIGH,
    CONF_MEDIUM,
    STATUS_QUEUE,
    STATUS_REJECT,
    STATUS_SILVER,
    SilverRecord,
    class_balance_warnings,
    decide,
    score_against_gold,
    summarize,
)
from .contract import (
    LabelProposal,
    VerifyVerdict,
    evidence_is_verbatim,
    load_proposals,
    load_verdicts,
    read_jsonl,
    write_jsonl,
)
from .prompts import (
    LABELER_SYSTEM,
    VERIFIER_SYSTEM,
    labeler_user_prompt,
    verifier_user_prompt,
)

__all__ = [
    "CONF_HIGH", "CONF_MEDIUM",
    "STATUS_QUEUE", "STATUS_REJECT", "STATUS_SILVER",
    "SilverRecord", "class_balance_warnings", "decide", "score_against_gold",
    "summarize",
    "LabelProposal", "VerifyVerdict", "evidence_is_verbatim",
    "load_proposals", "load_verdicts", "read_jsonl", "write_jsonl",
    "LABELER_SYSTEM", "VERIFIER_SYSTEM",
    "labeler_user_prompt", "verifier_user_prompt",
]
