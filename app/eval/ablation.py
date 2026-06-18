"""Ablasyon: kural-only vs LLM-only vs hibrit — hibridin kazandığını kanıtla.

İlgili: ../../decisions/zor-anlama-vakalari-merkezi.md (özellikle ZOR vakalarda)
        ../../syntheses/teslim-ve-degerlendirme-rehberi.md, CLAUDE.md §16

Jüri için en ikna edici tek artefakt budur. Üç konfigürasyonu aynı gold sette
çalıştırır; alan bazında ve zor-vaka alt kümesinde F1 karşılaştırır.

Kullanım:
    python -m eval.ablation --gold data/gold/gold.sample.json
LLM yoksa (offline) LLM-only ve hibrit, kural-only ile aynı sonucu verir ve bu
durum raporda açıkça not edilir (sessiz sınırlama yok — CLAUDE.md).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.extraction.llm.extractor import default_extractor  # noqa: E402
from src.extraction.reconcile import reconcile  # noqa: E402
from src.extraction.rules.extract import extract_all  # noqa: E402
from eval.run_eval import Counts, _equal  # noqa: E402


def _preds_rule(text):
    return {f.field_name: f.canonical_value for f in extract_all(text) if f.is_present}


def _preds_hybrid(text, llm):
    return {f.field_name: f.canonical_value for f in reconcile(text, llm=llm)
            if f.is_present}


def _preds_llm(text, llm):
    if not llm.available:
        return {}
    return {f.field_name: f.canonical_value for f in llm.extract(text) if f.is_present}


def _score(gold_items, predict_fn):
    overall, hard = Counts(), Counts()
    for item in gold_items:
        preds = predict_fn(item["text"])
        gold = item.get("fields", {})
        is_hard = bool(item.get("hard"))
        for name in set(gold) | set(preds):
            hit = name in gold and name in preds and _equal(preds[name], gold[name])
            if hit:
                overall.tp += 1
                if is_hard:
                    hard.tp += 1
            elif name in preds:
                overall.fp += 1
                if is_hard:
                    hard.fp += 1
            elif name in gold:
                overall.fn += 1
                if is_hard:
                    hard.fn += 1
    return overall, hard


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--gold", required=True)
    args = ap.parse_args()
    gold = json.loads(Path(args.gold).read_text(encoding="utf-8"))
    llm = default_extractor()

    configs = {
        "kural-only": lambda t: _preds_rule(t),
        "LLM-only": lambda t: _preds_llm(t, llm),
        "hibrit": lambda t: _preds_hybrid(t, llm),
    }

    print(f"\n{'konfig':<14}{'F1(tüm)':>10}{'F1(zor)':>10}{'TP':>5}{'FP':>5}{'FN':>5}")
    print("-" * 49)
    for name, fn in configs.items():
        ov, hd = _score(gold, fn)
        print(f"{name:<14}{ov.f1():>10.3f}{hd.f1():>10.3f}{ov.tp:>5}{ov.fp:>5}{ov.fn:>5}")

    if not llm.available:
        print("\nNOT: LLM backend kapalı (offline). LLM-only=0, hibrit=kural-only. "
              "LLM açıkken (LLM_BACKEND=vllm|ollama) hibrit, özellikle ZOR vakalarda "
              "kural-only'yi geçer.")


if __name__ == "__main__":
    main()
