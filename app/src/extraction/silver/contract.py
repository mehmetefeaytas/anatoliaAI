"""Gümüş (silver) etiket üretiminin G/Ç sözleşmesi.

İlgili: ./consensus.py, ./prompts.py, ../../../scripts/build_silver.py
        CLAUDE.md §4 (fine-tune YALNIZ 8-sınıf sınıflandırma için)
        CLAUDE.md §19 (halüsinasyon yasağı: bilgi yoksa null)

## Neden dosya tabanlı bir sözleşme var

Etiketleyici model **repoya konamaz**. Şartname §5.10 açık kaynak olmayan
bağımlılığı yasaklıyor ve §8 paylaşılan veri kümelerinin Apache-2.0 ile
lisanslanmasını zorunlu kılıyor. Bu yüzden mimari şöyle bölündü:

    belgeler/*.txt  ──►  [ETİKETLEYİCİ]  ──►  proposals.jsonl
                                                    │
    belgeler/*.txt  ──►  [DENETLEYİCİ]   ──►  verdicts.jsonl
                                                    │
                         [consensus.py]  ◄──────────┘  (repoda, offline)
                                │
                                ▼
                          silver.jsonl + queue.jsonl

Köşeli parantezdeki iki adım **takılabilir**: bugün harici bir asistan
oturumunda üretilir, yarın yerel bir model (vLLM/Ollama) aynı JSONL'i üretir.
Repodaki kod bu iki dosyayı **tüketir**, üretmez — dolayısıyla teslim edilen
sistemde hiçbir ücretli bağımlılık yoktur ve jüri yerel modelle aynı hattı
tekrar üretebilir.

Prompt şablonları `prompts.py`'de repoda durur: etiketin nasıl üretildiği
yeniden üretilebilir olmalı, yoksa veri setinin kökeni savunulamaz.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Iterable, Iterator, Optional

# Kanıt karşılaştırmasında yalnız boşluk ve büyük/küçük harf normalize edilir.
# Daha agresif normalizasyon (diakritik katlama, noktalama atma) kanıt
# kontrolünü anlamsızlaştırır: amaç metinde GERÇEKTEN geçen bir alıntı olup
# olmadığını ölçmek, benzer bir şey olup olmadığını değil.
_WS_RE = re.compile(r"\s+")

# Kanıt çok kısaysa "verbatim" olması bir şey kanıtlamaz: "TL" her belgede
# geçer. Eşik ölçümle değil muhakemeyle konuldu; taksonomi ipuçlarının en
# kısası ("kart") 4 karakter, ona yer bırakacak şekilde 12 seçildi.
MIN_EVIDENCE_CHARS = 12


def _norm(text: str) -> str:
    return _WS_RE.sub(" ", text).strip().casefold()


def evidence_is_verbatim(document_text: str, evidence: str) -> bool:
    """Kanıt, belgede birebir (boşluk/kasa toleranslı) geçiyor mu?

    Bu, LLM'e güvenmeyen **deterministik** halüsinasyon kapısıdır: model
    etiketi uydurabilir, ama uydurduğu alıntı belgede bulunmaz. Kapı bedava
    çalışır ve modelin kendi beyanına bakmaz.
    """
    if not evidence or len(evidence.strip()) < MIN_EVIDENCE_CHARS:
        return False
    return _norm(evidence) in _norm(document_text)


@dataclass(frozen=True)
class LabelProposal:
    """Etiketleyicinin bir belge için önerisi."""

    doc_id: str
    label: Optional[str]
    evidence: str
    confidence: float
    labeler: str  # ör. "opus-5", "qwen3-8b-awq", "rule"

    def to_json(self) -> dict[str, Any]:
        return {
            "doc_id": self.doc_id,
            "label": self.label,
            "evidence": self.evidence,
            "confidence": self.confidence,
            "labeler": self.labeler,
        }

    @staticmethod
    def from_json(item: dict[str, Any]) -> "LabelProposal":
        missing = {"doc_id", "label", "evidence"} - set(item)
        if missing:
            raise ValueError(
                f"proposal kaydında zorunlu alan eksik: {sorted(missing)}. "
                f"Gelen anahtarlar: {sorted(item)}")
        conf = item.get("confidence", 0.0)
        return LabelProposal(
            doc_id=str(item["doc_id"]),
            label=item["label"] if item["label"] else None,
            evidence=str(item.get("evidence") or ""),
            confidence=float(conf) if conf is not None else 0.0,
            labeler=str(item.get("labeler") or "bilinmiyor"),
        )


@dataclass(frozen=True)
class VerifyVerdict:
    """Denetleyicinin kararı.

    `own_label` KASITLI olarak ayrı bir alan: denetleyici yalnız "onaylıyorum"
    demek yerine **kendi bağımsız etiketini** vermek zorunda. Aksi hâlde
    denetleyici lastik damgaya döner (bilinen başarısızlık kipi) ve iki oy
    aslında tek oy olur. Prompt de bu sırayı zorlar: önce kendi etiketini
    söyler, sonra kanıta bakar.
    """

    doc_id: str
    own_label: Optional[str]
    evidence_supports: bool
    reason: str
    verifier: str

    def to_json(self) -> dict[str, Any]:
        return {
            "doc_id": self.doc_id,
            "own_label": self.own_label,
            "evidence_supports": self.evidence_supports,
            "reason": self.reason,
            "verifier": self.verifier,
        }

    @staticmethod
    def from_json(item: dict[str, Any]) -> "VerifyVerdict":
        if "doc_id" not in item:
            raise ValueError(f"verdict kaydında doc_id yok: {sorted(item)}")
        if "evidence_supports" not in item:
            raise ValueError(
                f"verdict kaydında evidence_supports yok (doc_id="
                f"{item['doc_id']!r}). Denetleyici kanıt hakkında karar "
                f"vermek ZORUNDA; eksik bırakmak sessizce onay sayılamaz.")
        return VerifyVerdict(
            doc_id=str(item["doc_id"]),
            own_label=item.get("own_label") or None,
            evidence_supports=bool(item["evidence_supports"]),
            reason=str(item.get("reason") or ""),
            verifier=str(item.get("verifier") or "bilinmiyor"),
        )


def read_jsonl(path: str) -> Iterator[dict[str, Any]]:
    """JSONL oku; bozuk satırı SESSİZCE atlamaz, satır numarasıyla patlar."""
    with open(path, encoding="utf-8") as fh:
        for lineno, line in enumerate(fh, 1):
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{lineno} geçerli JSON değil: {exc}") from exc


def write_jsonl(path: str, items: Iterable[dict[str, Any]]) -> int:
    n = 0
    with open(path, "w", encoding="utf-8") as fh:
        for item in items:
            fh.write(json.dumps(item, ensure_ascii=False) + "\n")
            n += 1
    return n


def load_proposals(path: str) -> dict[str, LabelProposal]:
    """doc_id -> proposal. Aynı doc_id iki kez gelirse patlar (sessiz üzerine
    yazma, etiket kaynağını izlenemez kılar)."""
    out: dict[str, LabelProposal] = {}
    for item in read_jsonl(path):
        p = LabelProposal.from_json(item)
        if p.doc_id in out:
            raise ValueError(f"{path}: doc_id iki kez geçiyor: {p.doc_id!r}")
        out[p.doc_id] = p
    return out


def load_verdicts(path: str) -> dict[str, VerifyVerdict]:
    out: dict[str, VerifyVerdict] = {}
    for item in read_jsonl(path):
        v = VerifyVerdict.from_json(item)
        if v.doc_id in out:
            raise ValueError(f"{path}: doc_id iki kez geçiyor: {v.doc_id!r}")
        out[v.doc_id] = v
    return out
