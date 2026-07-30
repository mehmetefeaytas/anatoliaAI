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

from eval.iaa import (  # noqa: E402
    cohen_kappa,
    fleiss_kappa_from_labels,
    interpret_kappa,
    krippendorff_alpha,
)
from scripts.build_gold import infer_annotator, read_review_csv  # noqa: E402
from scripts.gold_schema import (  # noqa: E402
    CAMPAIGN_TYPE_KEY,
    NUMERIC_FIELDS,
    parse_gold_value,
)

ABSENT_TOKEN = "__YOK__"
DEFAULT_REPORT = "data/gold/iaa_report.md"


def _clean(value: Optional[str]) -> str:
    return (value or "").strip()


def row_verdict(row: dict) -> str:
    """Satırın normalize edilmiş kararı. Boş = `ok` (kılavuz §3)."""
    verdict = _clean(row.get("verdict")).casefold()
    if not verdict:
        return "fix" if _clean(row.get("gold_value")) else "ok"
    return verdict


def row_value_token(row: dict) -> Optional[str]:
    """Satırın ima ettiği GOLD DEĞERİ, karşılaştırılabilir bir jetona indirger.

    `unclear` -> None (eksik değer; Krippendorff bunu doğal eler).
    `absent`  -> ABSENT_TOKEN (kendi başına bir kategori; "yok" da bir karardır).
    """
    verdict = row_verdict(row)
    if verdict == "unclear":
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
    for key, unit in zip(keys, value_units):
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
    for key, v_unit, val_unit in zip(keys, verdict_units, value_units):
        present_v = [x for x in v_unit if x is not None]
        present_val = [x for x in val_unit if x is not None]
        if len(set(present_v)) > 1 or len(set(present_val)) > 1:
            disagreements.append({
                "doc_id": key[0],
                "field": key[1],
                "verdicts": dict(zip(annotators, v_unit)),
                "values": dict(zip(annotators, val_unit)),
            })

    return {
        "annotators": annotators,
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
        "",
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
    print(f"ortak satır         : {result['shared_rows']}")
    print(f"{result['verdict_metric']:<20}: {_fmt(result['verdict_kappa'])}")
    print(f"Krippendorff nominal: {_fmt(result['value_alpha_nominal'])}")
    print(f"Krippendorff ratio  : {_fmt(result['value_alpha_ratio'])}")
    print(f"uyuşmazlık          : {len(result['disagreements'])}")
    print(f"DURUM: {status} — {action}")
    print(f"rapor: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
