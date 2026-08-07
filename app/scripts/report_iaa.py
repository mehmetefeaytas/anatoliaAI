"""Anotatörler arası uyum raporu — iki (ya da daha çok) CSV -> kappa + uyuşmazlık.

İlgili: eval/iaa.py (istatistik çekirdeği)
        data/gold/ANNOTATION_GUIDE.md §7 (önceden ilan edilmiş eşik politikası)

Kullanım:
    # Çift anotasyon alt kümesi (2 anotatör -> Cohen's kappa)
    python3 -m scripts.report_iaa data/gold/review/round1_A.csv \\
                                  data/gold/review/round1_B.csv

    # Kalibrasyon turu (4 anotatör -> Fleiss' kappa)
    python3 -m scripts.report_iaa data/gold/review/round0_kalibrasyon_*.csv

## İki ayrı uyum, iki ayrı soru

**1) Karar uyumu (verdict).** Anotatörler aynı satırda aynı KARARI mı verdi
(ok / fix / absent / unclear)? Kategoriktir -> Cohen / Fleiss. Kılavuzun net
olup olmadığını ölçer.

**2) Değer uyumu.** `fix` diyenler AYNI değeri mi yazdı? Bunu kategorik ölçmek
yanıltıcıdır: `%1,89` yerine `%1,90` yazan biri "tamamen anlaşmazlık" sayılır
ve kappa gerçekte olduğundan kötü çıkar. Sayısal alanlarda Krippendorff `ratio`
kullanılır — fark büyüklüğe oranlanır, 1,89 vs 1,90 neredeyse uyum sayılır.

İkisi birlikte raporlanır; sadece birine bakmak yanlış yerde kılavuz revize
ettirir.

## Protokol duyarlılığı (v1 / v2)

Boş `verdict` hücresinin anlamı protokole göre DEĞİŞİR:

    v1  boş = `ok` ("model doğru")            -> gold modelin çıktısına çapalanır
    v2  boş = karar verilmedi                 -> κ hesabından ÇIKARILIR

Protokol satırdaki `protokol` sütunundan okunur; sütun yoksa dosya **v1**
sayılır. Böylece eski CSV'lerin yorumu değişmez — geriye dönük hiçbir karar
kaybolmaz — ama yeni paketlerde "bakılmamış satır" uyuma katılmaz.

Bu ayrım kozmetik değil: v1'de bakılmamış satırlar hem gold'a hem κ'ya "tam
uyum" olarak girer ve ikisini de olduğundan iyi gösterir (ANNOTATION_GUIDE §11).
"""

from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Optional

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from eval.iaa import (
    cohen_kappa,
    fleiss_kappa_from_labels,
    interpret_kappa,
    krippendorff_alpha,
)
from scripts.build_gold import infer_annotator, read_review_csv
from scripts.gold_schema import (
    NUMERIC_FIELDS,
    parse_gold_value,
)

ABSENT_TOKEN = "__YOK__"
DEFAULT_REPORT = "data/gold/iaa_report.md"

PROTOCOL_COLUMN = "protokol"
PROTOCOL_V1 = "v1"
PROTOCOL_V2 = "v2"


def _clean(value: Optional[str]) -> str:
    return (value or "").strip()


def row_protocol(row: dict) -> str:
    """Satırın anotasyon protokolü. Sütun yoksa **v1** (geriye dönük uyum)."""
    value = _clean(row.get(PROTOCOL_COLUMN)).casefold()
    return PROTOCOL_V2 if value == PROTOCOL_V2 else PROTOCOL_V1


def row_verdict(row: dict) -> Optional[str]:
    """Satırın normalize edilmiş kararı.

    Boş hücrenin anlamı protokole bağlıdır (ANNOTATION_GUIDE §3.1, §11):

      v1: boş = `ok` ("modelin çıktısını onaylıyorum")
      v2: boş = KARAR VERİLMEDİ -> `None`, uyum hesabına girmez

    Her iki protokolde de boş `verdict` + dolu `gold_value` = `fix`; anotatör
    düzeltmeyi yazıp karar sütununu atlamıştır, o düzeltme çöpe atılmaz.
    """
    verdict = _clean(row.get("verdict")).casefold()
    if verdict:
        return verdict
    if _clean(row.get("gold_value")):
        return "fix"
    return None if row_protocol(row) == PROTOCOL_V2 else "ok"


def row_value_token(row: dict) -> Optional[str]:
    """Satırın ima ettiği GOLD DEĞERİ, karşılaştırılabilir bir jetona indirger.

    `unclear` -> None (eksik değer; Krippendorff bunu doğal eler).
    `absent`  -> ABSENT_TOKEN (kendi başına bir kategori; "yok" da bir karardır).
    Karar verilmemiş satır (v2, boş) -> None.
    """
    verdict = row_verdict(row)
    if verdict is None or verdict == "unclear":
        return None
    if verdict == "absent":
        return ABSENT_TOKEN
    if verdict == "fix":
        return _clean(row.get("gold_value")) or None
    model = _clean(row.get("model_value"))
    # Model değer üretmediği satırda `ok` = "kontrol ettim, yok".
    return model if model else ABSENT_TOKEN


def numeric_value(field: str, token: Optional[str]) -> Optional[float]:
    """Jetondan `ratio` ölçeği için sayı çıkarır; çıkmıyorsa None.

    Aralık (`{"min":…, "max":…}`) ORTA NOKTASIYLA temsil edilir: aralığı tümden
    atmak, zor-vaka satırlarını sayısal uyumdan silmek olurdu — oysa uyumun en
    kritik olduğu yer tam orası.
    """
    if token is None or token == ABSENT_TOKEN:
        return None
    try:
        value = parse_gold_value(field, token)
    except Exception:
        return None

    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, dict):
        if {"min", "max"} <= set(value):
            return (float(value["min"]) + float(value["max"])) / 2.0
        if "value" in value and isinstance(value["value"], (int, float)):
            return float(value["value"])
    return None


# --------------------------------------------------------------------------- #
# Hizalama
# --------------------------------------------------------------------------- #
def align(csv_paths: list[str]) -> tuple[list[str], dict[tuple[str, str], dict[str, dict]]]:
    """CSV'leri `(doc_id, field)` anahtarında hizalar.

    Returns:
        (anotatör adları, {(doc_id, field): {anotatör: satır}})
    """
    annotators: list[str] = []
    table: dict[tuple[str, str], dict[str, dict]] = defaultdict(dict)

    for path in csv_paths:
        name = infer_annotator(path)
        if name in annotators:
            name = f"{name}#{annotators.count(name) + 1}"
        annotators.append(name)
        for row in read_review_csv(path):
            key = (_clean(row.get("doc_id")), _clean(row.get("field")))
            table[key][name] = row

    # Yalnızca EN AZ İKİ anotatörün gördüğü satırlar uyum ölçebilir.
    shared = {key: value for key, value in table.items() if len(value) >= 2}
    return annotators, shared


def file_protocols(csv_paths: list[str]) -> dict[str, str]:
    """Dosya -> protokol (`v1` | `v2`). Dosyanın İLK satırı belirler."""
    out: dict[str, str] = {}
    for path in csv_paths:
        rows = read_review_csv(path)
        out[str(path)] = row_protocol(rows[0]) if rows else PROTOCOL_V1
    return out


def compute(csv_paths: list[str]) -> dict[str, Any]:
    """Kappa/alpha değerlerini ve uyuşmazlık listesini hesaplar."""
    annotators, shared = align(csv_paths)
    keys = sorted(shared)

    verdict_units = [[shared[k].get(a) for a in annotators] for k in keys]
    verdict_units = [[row_verdict(r) if r is not None else None for r in unit]
                     for unit in verdict_units]

    value_units = [[shared[k].get(a) for a in annotators] for k in keys]
    value_units = [[row_value_token(r) if r is not None else None for r in unit]
                   for unit in value_units]

    # Sayısal alanlar -> ratio ölçeği.
    ratio_units: list[list[Optional[float]]] = []
    for key, unit in zip(keys, value_units, strict=False):
        field = key[1]
        if field not in NUMERIC_FIELDS:
            continue
        numbers = [numeric_value(field, token) for token in unit]
        if sum(1 for n in numbers if n is not None) >= 2:
            ratio_units.append(numbers)

    if len(annotators) == 2:
        verdict_kappa = cohen_kappa([u[0] for u in verdict_units],
                                    [u[1] for u in verdict_units])
        verdict_metric = "Cohen's kappa"
    else:
        verdict_kappa = fleiss_kappa_from_labels(verdict_units)
        verdict_metric = "Fleiss' kappa"

    # Uyuşmazlık listesi: kararlar ya da değerler ayrışan satırlar.
    disagreements = []
    for key, v_unit, val_unit in zip(keys, verdict_units, value_units, strict=False):
        present_v = [x for x in v_unit if x is not None]
        present_val = [x for x in val_unit if x is not None]
        if len(set(present_v)) > 1 or len(set(present_val)) > 1:
            disagreements.append({
                "doc_id": key[0],
                "field": key[1],
                "verdicts": dict(zip(annotators, v_unit, strict=False)),
                "values": dict(zip(annotators, val_unit, strict=False)),
            })

    protocols = file_protocols(csv_paths)
    # v2'de boş hücre karar değildir; kaç karar-yeri boş kaldığı raporlanır,
    # yoksa "hiç uyuşmazlık yok" ile "kimse bakmamış" ayırt edilemez.
    undecided = sum(1 for unit in verdict_units for v in unit if v is None)

    return {
        "annotators": annotators,
        "protocols": protocols,
        "mixed_protocols": len(set(protocols.values())) > 1,
        "undecided_cells": undecided,
        "shared_rows": len(keys),
        "verdict_metric": verdict_metric,
        "verdict_kappa": verdict_kappa,
        "value_alpha_nominal": krippendorff_alpha(value_units, "nominal"),
        "value_alpha_ratio": (krippendorff_alpha(ratio_units, "ratio")
                              if ratio_units else float("nan")),
        "ratio_units": len(ratio_units),
        "disagreements": disagreements,
        "files": list(csv_paths),
    }


# --------------------------------------------------------------------------- #
# Rapor
# --------------------------------------------------------------------------- #
def _fmt(value: float) -> str:
    return "ölçülemedi" if value != value else f"{value:.3f}"


def render(result: dict) -> str:
    status, action = interpret_kappa(result["verdict_kappa"])
    lines = [
        "# Anotatörler Arası Uyum (IAA) Raporu",
        "",
        "> `scripts/report_iaa.py` üretti. Eşik politikası anotasyon "
        "BAŞLAMADAN ilan edilmiştir (ANNOTATION_GUIDE.md §7); sayılara bakıp "
        "eşik değiştirmek yasaktır.",
        "",
        f"- Anotatörler: {', '.join(result['annotators'])}",
        f"- Ortak anote edilmiş satır: **{result['shared_rows']}**",
        f"- Karar bulunmayan hücre (boş/eksik): **{result['undecided_cells']}**",
        "",
        "## Protokol künyesi",
        "",
        "| Dosya | Protokol | Boş hücrenin anlamı |",
        "|---|---|---|",
    ]
    for path, protocol in sorted(result["protocols"].items()):
        meaning = ("karar verilmedi — metrik dışı" if protocol == PROTOCOL_V2
                   else "`ok` (onay) — modele çapalı")
        lines.append(f"| `{path}` | **{protocol}** | {meaning} |")
    lines.append("")
    if result["mixed_protocols"]:
        lines += [
            "> ⚠️ **UYARI — protokoller karışık.** v1 ve v2 dosyaları aynı κ "
            "koşusunda birleştirildi. v1'de bakılmamış satır 'onay' sayıldığı "
            "için uyum OLDUĞUNDAN İYİ çıkar. Bu sayı jüriye tek başına "
            "sunulamaz (ANNOTATION_GUIDE.md §11).",
            "",
        ]

    lines += [
        "## Sonuçlar",
        "",
        "| Ölçüt | Neyi ölçer | Değer |",
        "|---|---|---:|",
        f"| {result['verdict_metric']} (karar) | Aynı satırda aynı kararı mı "
        f"verdiler (ok/fix/absent/unclear) | **{_fmt(result['verdict_kappa'])}** |",
        f"| Krippendorff α (nominal) | Ortaya çıkan gold DEĞERİ birebir aynı mı "
        f"| {_fmt(result['value_alpha_nominal'])} |",
        f"| Krippendorff α (ratio) | Sayısal alanlarda değer yakınlığı "
        f"({result['ratio_units']} birim) | {_fmt(result['value_alpha_ratio'])} |",
        "",
        "## Karar (önceden ilan edilmiş eşik)",
        "",
        f"- **Durum: `{status}`**",
        f"- Yapılacak: {action}",
        "",
        "| Eşik | Karar |",
        "|---|---|",
        "| κ ≥ 0,80 | kabul |",
        "| 0,67 ≤ κ < 0,80 | notla kabul |",
        "| κ < 0,67 | zorunlu hakemlik + kılavuz revizyonu |",
        "",
    ]

    disagreements = result["disagreements"]
    lines += [f"## Uyuşmazlıklar ({len(disagreements)})", ""]
    if disagreements:
        lines += ["Kalibrasyon toplantısında sırayla konuşulacak liste.", "",
                  "| Belge | Alan | Kararlar | Değerler |", "|---|---|---|---|"]
        for item in disagreements[:300]:
            verdicts = ", ".join(f"{k}={v}" for k, v in item["verdicts"].items()
                                 if v is not None)
            values = ", ".join(f"{k}={v!r}" for k, v in item["values"].items()
                               if v is not None)
            lines.append(f"| `{item['doc_id']}` | `{item['field']}` | {verdicts} "
                         f"| {values} |")
        if len(disagreements) > 300:
            lines.append(f"\n_… ve {len(disagreements) - 300} tane daha._")
    else:
        lines.append("_Tam uyum._")

    return "\n".join(lines) + "\n"


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="İki ya da daha çok anotatör CSV'sini karşılaştırır.")
    parser.add_argument("csv", nargs="+", help="doldurulmuş inceleme CSV'leri")
    parser.add_argument("--out", default=DEFAULT_REPORT)
    args = parser.parse_args(argv)

    if len(args.csv) < 2:
        parser.error("uyum ölçmek için en az iki CSV gerekli")

    result = compute(args.csv)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(render(result), encoding="utf-8")

    status, action = interpret_kappa(result["verdict_kappa"])
    protocols = "+".join(sorted(set(result["protocols"].values())))
    print(f"protokol            : {protocols}")
    if result["mixed_protocols"]:
        print("UYARI: v1 ve v2 karıştırıldı — uyum olduğundan İYİ çıkar "
              "(ANNOTATION_GUIDE.md §11)")
    print(f"ortak satır         : {result['shared_rows']}")
    print(f"karar bulunmayan    : {result['undecided_cells']}")
    print(f"{result['verdict_metric']:<20}: {_fmt(result['verdict_kappa'])}")
    print(f"Krippendorff nominal: {_fmt(result['value_alpha_nominal'])}")
    print(f"Krippendorff ratio  : {_fmt(result['value_alpha_ratio'])}")
    print(f"uyuşmazlık          : {len(result['disagreements'])}")
    print(f"DURUM: {status} — {action}")
    print(f"rapor: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
