"""Değerlendirme harness'i — alan bazında precision / recall / F1.

İlgili: ../../decisions/zor-anlama-vakalari-merkezi.md (zor-vaka alt kümesi + ablasyon)
        ../../syntheses/teslim-ve-degerlendirme-rehberi.md

Kullanım:
    python -m eval.run_eval --gold data/gold/gold.json

Gold formatı (JSON liste):
    [
      {"text": "...", "fields": {"kar_payi_orani": 1.99, "vade_ay": 120}, "hard": true},
      ...
    ]
canonical_value gold ile karşılaştırılır. 'hard' alt kümesi ayrıca raporlanır.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path

# paket import'u (python -m eval.run_eval ile app/ kökünden çalışır)
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.extraction.rules.extract import extract_all  # noqa: E402


@dataclass
class Counts:
    tp: int = 0
    fp: int = 0
    fn: int = 0

    def precision(self) -> float:
        d = self.tp + self.fp
        return self.tp / d if d else 0.0

    def recall(self) -> float:
        d = self.tp + self.fn
        return self.tp / d if d else 0.0

    def f1(self) -> float:
        p, r = self.precision(), self.recall()
        return 2 * p * r / (p + r) if (p + r) else 0.0


def _equal(pred, gold) -> bool:
    """canonical eşitlik — sayılarda küçük tolerans, dict/aralıkta alan-alan."""
    if isinstance(gold, (int, float)) and isinstance(pred, (int, float)):
        return abs(float(pred) - float(gold)) < 1e-6
    return pred == gold


def evaluate(gold_items: list[dict]) -> dict:
    per_field: dict[str, Counts] = {}
    per_field_hard: dict[str, Counts] = {}

    for item in gold_items:
        text = item["text"]
        gold_fields = item.get("fields", {})
        is_hard = bool(item.get("hard", False))
        preds = {f.field_name: f.canonical_value for f in extract_all(text)}

        names = set(gold_fields) | set(preds)
        for name in names:
            c = per_field.setdefault(name, Counts())
            ch = per_field_hard.setdefault(name, Counts()) if is_hard else None
            g_has = name in gold_fields
            p_has = name in preds and preds[name] is not None

            if g_has and p_has and _equal(preds[name], gold_fields[name]):
                c.tp += 1
                if ch:
                    ch.tp += 1
            elif p_has and not (g_has and _equal(preds[name], gold_fields[name])):
                c.fp += 1
                if ch:
                    ch.fp += 1
            elif g_has and not p_has:
                c.fn += 1
                if ch:
                    ch.fn += 1

    return {"overall": per_field, "hard": per_field_hard}


def _print_table(title: str, table: dict[str, Counts]) -> None:
    print(f"\n=== {title} ===")
    print(f"{'alan':<22}{'P':>7}{'R':>7}{'F1':>7}{'TP':>5}{'FP':>5}{'FN':>5}")
    tps = fps = fns = 0
    for name, c in sorted(table.items()):
        print(f"{name:<22}{c.precision():>7.2f}{c.recall():>7.2f}{c.f1():>7.2f}"
              f"{c.tp:>5}{c.fp:>5}{c.fn:>5}")
        tps += c.tp; fps += c.fp; fns += c.fn
    micro = Counts(tps, fps, fns)
    print(f"{'MICRO':<22}{micro.precision():>7.2f}{micro.recall():>7.2f}{micro.f1():>7.2f}"
          f"{micro.tp:>5}{micro.fp:>5}{micro.fn:>5}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--gold", required=True, help="gold JSON dosyası")
    args = ap.parse_args()

    gold_items = json.loads(Path(args.gold).read_text(encoding="utf-8"))
    res = evaluate(gold_items)
    _print_table("KURAL KATMANI — TÜM VAKALAR", res["overall"])
    if any(c.tp + c.fp + c.fn for c in res["hard"].values()):
        _print_table("KURAL KATMANI — ZOR VAKALAR", res["hard"])


if __name__ == "__main__":
    main()
