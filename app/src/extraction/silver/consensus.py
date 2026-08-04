"""Üç oylu uzlaşma: kural + etiketleyici + denetleyici.

İlgili: ./contract.py, ./prompts.py, ../ner/classifier.py

## Neden üç oy

Tek bir LLM etiketi ölçülmemiş bir iddiadır. Üç bağımsız oy, hiçbiri
mükemmel olmadan kullanışlı bir güven kademesi verir:

1. **kural** — `RuleHintClassifier`, anahtar kelime. Zayıf ama TAM bağımsız
   (LLM'i hiç görmez) ve bedava. Bu yüzden **veto hakkı yok**: kural
   katmanının kendi ölçülmüş hatası var (sözcük sınırı düzeltmesinden önce
   korpusun %48'ini sahte Konut Finansmanı yapıyordu). Yalnızca güveni
   yükseltir.
2. **etiketleyici** — belgeyi okur, etiket + **birebir alıntı** üretir.
3. **denetleyici** — kendi etiketini bağımsız verir, sonra alıntıyı yargılar.

Kademeler bilinçli olarak muhafazakâr: şüphe varsa `queue`. İnsan kuyruğu
küçük kalmalı ama BOŞ olmamalı — boş kuyruk, uzlaşmanın çok gevşek olduğunun
işaretidir.

## Halüsinasyon kapısı LLM'den ÖNCE çalışır

`evidence_is_verbatim` deterministiktir. Model etiketi uydurabilir ama
alıntıyı uyduramaz — uydurursa belgede bulunmaz ve kayıt `reject` olur.
Bu, projenin `source_span` ilkesinin (CLAUDE.md §3) gümüş veriye taşınmış
hâlidir.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Any, Optional

from ...schemas import CAMPAIGN_TYPES
from .contract import LabelProposal, VerifyVerdict, evidence_is_verbatim

STATUS_SILVER = "silver"      # eğitime girer
STATUS_QUEUE = "queue"        # insan hakemliğine düşer
STATUS_REJECT = "reject"      # atılır (halüsinasyon / taksonomi dışı)

CONF_HIGH = "yuksek"          # üç oy da aynı
CONF_MEDIUM = "orta"          # iki LLM oyu aynı, kural ayrı ya da sessiz

# Gerekçe kodları — rapor ve hata ayıklama sabitleri (serbest metin değil).
R_TAXONOMY = "taksonomi_disi"
R_NO_EVIDENCE = "kanit_dogrulanmadi"
R_UNVERIFIED = "denetlenmedi"
R_EVIDENCE_WEAK = "kanit_desteklemiyor"
R_LABELS_DIVERGE = "etiketler_ayristi"
R_UNANIMOUS = "uc_oy_ayni"
R_LLM_AGREE = "iki_llm_ayni"


@dataclass(frozen=True)
class SilverRecord:
    doc_id: str
    label: Optional[str]
    status: str
    confidence: str
    reason: str
    evidence: str
    rule_label: Optional[str]
    llm_label: Optional[str]
    verifier_label: Optional[str]
    labeler: str
    verifier: str

    def to_json(self) -> dict[str, Any]:
        return {
            "doc_id": self.doc_id,
            "label": self.label,
            "status": self.status,
            "confidence": self.confidence,
            "reason": self.reason,
            "evidence": self.evidence,
            "votes": {
                "rule": self.rule_label,
                "labeler": self.llm_label,
                "verifier": self.verifier_label,
            },
            "labeler": self.labeler,
            "verifier": self.verifier,
        }


def decide(document_text: str,
           proposal: LabelProposal,
           verdict: Optional[VerifyVerdict],
           rule_label: Optional[str]) -> SilverRecord:
    """Bir belge için uzlaşma kararı.

    Sıra önemlidir: mekanik kapılar (taksonomi, kanıt) LLM oylarından ÖNCE
    çalışır, çünkü onlar modelin beyanına bakmaz.
    """
    def _rec(label: Optional[str], status: str, conf: str,
             reason: str) -> SilverRecord:
        return SilverRecord(
            doc_id=proposal.doc_id, label=label, status=status,
            confidence=conf, reason=reason, evidence=proposal.evidence,
            rule_label=rule_label, llm_label=proposal.label,
            verifier_label=verdict.own_label if verdict else None,
            labeler=proposal.labeler,
            verifier=verdict.verifier if verdict else "",
        )

    # 1) Taksonomi dışı etiket asla geçmez (8 sınıf sabit, CLAUDE.md §12).
    if proposal.label not in CAMPAIGN_TYPES:
        return _rec(None, STATUS_REJECT, "", R_TAXONOMY)

    # 2) Deterministik halüsinasyon kapısı.
    if not evidence_is_verbatim(document_text, proposal.evidence):
        return _rec(None, STATUS_REJECT, "", R_NO_EVIDENCE)

    # 3) Denetlenmemiş kayıt gümüş sayılmaz — tek oy, oy değildir.
    if verdict is None:
        return _rec(proposal.label, STATUS_QUEUE, "", R_UNVERIFIED)

    # 4) Denetleyici alıntıyı yetersiz buluyorsa insana gider.
    if not verdict.evidence_supports:
        return _rec(proposal.label, STATUS_QUEUE, "", R_EVIDENCE_WEAK)

    # 5) İki LLM ayrışıyorsa karar insanın.
    if verdict.own_label != proposal.label:
        return _rec(proposal.label, STATUS_QUEUE, "", R_LABELS_DIVERGE)

    # 6-7) İki LLM aynı; kural katmanı yalnız güveni yükseltir.
    if rule_label == proposal.label:
        return _rec(proposal.label, STATUS_SILVER, CONF_HIGH, R_UNANIMOUS)
    return _rec(proposal.label, STATUS_SILVER, CONF_MEDIUM, R_LLM_AGREE)


def summarize(records: list[SilverRecord]) -> dict[str, Any]:
    """CLI raporu için sayımlar."""
    status = Counter(r.status for r in records)
    return {
        "toplam": len(records),
        "durum": dict(status),
        "guven": dict(Counter(r.confidence for r in records if r.confidence)),
        "gerekce": dict(Counter(r.reason for r in records)),
        "sinif_dagilimi": dict(Counter(
            r.label for r in records if r.status == STATUS_SILVER and r.label)),
    }


def class_balance_warnings(records: list[SilverRecord],
                           min_per_class: int) -> list[str]:
    """Fine-tune için sınıf dengesi uyarıları.

    CLAUDE.md §4: "dengeli 150-300 örnek". Dengesiz bir gümüş küme,
    sınıflandırıcıyı çoğunluk sınıfına ezberletir; bu yüzden eksik sınıflar
    SESSİZ kalmamalı.
    """
    silver = [r for r in records if r.status == STATUS_SILVER and r.label]
    counts = Counter(r.label for r in silver)
    out: list[str] = []
    for label in CAMPAIGN_TYPES:
        n = counts.get(label, 0)
        if n < min_per_class:
            out.append(f"{label}: {n}/{min_per_class} — eksik")
    return out


def score_against_gold(records: list[SilverRecord],
                       gold: dict[str, str]) -> dict[str, Any]:
    """Gümüş etiketleri insan gold'una karşı ölç.

    Ölçülmemiş gümüş veri, kaynağı belirsiz veriden iyi değildir. Bu fonksiyon
    raporda kullanılacak tek savunulabilir sayıyı üretir: "otomatik etiketleyici
    insan etiketiyle %N örtüşüyor". Yalnızca gold'da KARŞILIĞI OLAN belgeler
    sayılır; kapsam da ayrıca raporlanır ki yüksek yüzde küçük örneklemi
    gizlemesin.
    """
    overlap = [(r, gold[r.doc_id]) for r in records if r.doc_id in gold]
    scored = [(r, g) for r, g in overlap if r.status == STATUS_SILVER]
    hit = sum(1 for r, g in scored if r.label == g)
    mismatches = [
        {"doc_id": r.doc_id, "silver": r.label, "gold": g,
         "confidence": r.confidence}
        for r, g in scored if r.label != g
    ]
    return {
        "gold_kesisimi": len(overlap),
        "gumus_olarak_puanlanan": len(scored),
        "ortusen": hit,
        "ortusme_orani": round(hit / len(scored), 4) if scored else None,
        "uyusmazliklar": mismatches,
    }
