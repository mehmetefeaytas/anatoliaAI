"""Gümüş etiket hattı CLI'si — hazırla / birleştir / puanla.

İlgili: ../src/extraction/silver/  ·  CLAUDE.md §4 (fine-tune yalnız 8-sınıf)

## Üç adım

    # 1) Etiketlenecek partiyi ve prompt'ları çıkar
    python3 -m scripts.build_silver prepare \\
        --docs data/raw-classic --out data/silver/batch.jsonl

    # 2) (repo DIŞI) etiketleyici + denetleyici JSONL'leri üret
    #    -> data/silver/proposals.jsonl, data/silver/verdicts.jsonl
    #    Bugün harici bir asistan oturumu, yarın yerel vLLM/Ollama. Sözleşme
    #    aynı; repodaki kod değişmez (bkz. src/extraction/silver/contract.py).

    # 3) Üç oylu uzlaşma + rapor
    python3 -m scripts.build_silver merge \\
        --docs data/raw-classic \\
        --proposals data/silver/proposals.jsonl \\
        --verdicts data/silver/verdicts.jsonl \\
        --out-dir data/silver

    # 4) Gold varsa etiketleyicinin insanla örtüşmesini ölç
    python3 -m scripts.build_silver score \\
        --silver data/silver/silver.jsonl --gold data/gold/gold.v1.json

Adım 2 kasıtlı olarak repo dışındadır: ücretli/harici model teslim edilen
sisteme bağımlılık olarak giremez (şartname §5.10, §8).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.extraction.ner.classifier import RuleHintClassifier
from src.extraction.silver import (
    LABELER_SYSTEM,
    STATUS_QUEUE,
    STATUS_REJECT,
    STATUS_SILVER,
    VERIFIER_SYSTEM,
    class_balance_warnings,
    decide,
    labeler_user_prompt,
    load_proposals,
    load_verdicts,
    read_jsonl,
    score_against_gold,
    summarize,
    verifier_user_prompt,
    write_jsonl,
)

# Fine-tune için sınıf başına hedef. CLAUDE.md §4 "dengeli 150-300 örnek"
# diyor; 8 sınıfa bölününce sınıf başına ~20-40 eder. Alt sınır seçildi.
MIN_PER_CLASS = 20


def _iter_docs(docs_dir: str) -> list[tuple[str, str]]:
    """(doc_id, metin) çiftleri. doc_id = '<banka>--<dosya>' (korpus kuralı)."""
    out: list[tuple[str, str]] = []
    for bank in sorted(os.listdir(docs_dir)):
        bdir = os.path.join(docs_dir, bank)
        if not os.path.isdir(bdir):
            continue
        for root, _dirs, files in os.walk(bdir):
            for fn in sorted(files):
                if not fn.endswith(".txt"):
                    continue
                path = os.path.join(root, fn)
                with open(path, encoding="utf-8") as fh:
                    text = fh.read()
                out.append((f"{bank}--{fn[:-4]}", text))
    return out


def cmd_prepare(args: argparse.Namespace) -> int:
    docs = _iter_docs(args.docs)
    if not docs:
        print(f"HATA: {args.docs} altında .txt belge bulunamadı.")
        return 2
    os.makedirs(os.path.dirname(os.path.abspath(args.out)) or ".", exist_ok=True)
    n = write_jsonl(args.out, (
        {"doc_id": did, "prompt": labeler_user_prompt(did, text)}
        for did, text in docs
    ))
    base = os.path.dirname(os.path.abspath(args.out))
    for name, content in (("labeler_system.txt", LABELER_SYSTEM),
                          ("verifier_system.txt", VERIFIER_SYSTEM)):
        with open(os.path.join(base, name), "w", encoding="utf-8") as fh:
            fh.write(content + "\n")
    print(f"{n} belge -> {args.out}")
    print(f"sistem prompt'ları -> {base}/labeler_system.txt, "
          f"{base}/verifier_system.txt")
    print("\nSonraki adım (repo DIŞI): proposals.jsonl + verdicts.jsonl üret.")
    return 0


def cmd_prepare_verify(args: argparse.Namespace) -> int:
    """Denetleyici partisini çıkar — öneriler ÜRETİLDİKTEN sonra koşulur.

    Denetleyici prompt'u öneriyi içermek zorunda (alıntıyı yargılayacak), o
    yüzden `prepare`ten ayrı bir adım. Ayrışma bilgisi burada doğuyor.
    """
    texts = dict(_iter_docs(args.docs))
    proposals = load_proposals(args.proposals)
    eksik = sorted(set(proposals) - set(texts))
    if eksik:
        print(f"HATA: {len(eksik)} proposal belge kümesinde yok, ör: {eksik[:3]}")
        return 2
    # Kanıt kapısını burada da uygula: uydurulmuş alıntı için denetleyici
    # çalıştırmak boşa harcanan bir tur. Kapı deterministik, ücretsiz ve
    # LLM'den önce gelir.
    atlanan = 0
    items = []
    for doc_id, p in proposals.items():
        if not p.label:
            atlanan += 1
            continue
        items.append({
            "doc_id": doc_id,
            "prompt": verifier_user_prompt(doc_id, texts[doc_id], p.label,
                                           p.evidence),
        })
    os.makedirs(os.path.dirname(os.path.abspath(args.out)) or ".", exist_ok=True)
    n = write_jsonl(args.out, items)
    print(f"{n} denetim isteği -> {args.out}")
    if atlanan:
        print(f"{atlanan} öneri label=null olduğu için denetime girmedi.")
    return 0


def cmd_merge(args: argparse.Namespace) -> int:
    texts = dict(_iter_docs(args.docs))
    proposals = load_proposals(args.proposals)
    verdicts = load_verdicts(args.verdicts) if args.verdicts else {}

    bilinmeyen = sorted(set(proposals) - set(texts))
    if bilinmeyen:
        # Sessizce atlamak, etiketin hangi belgeye ait olduğunu izlenemez kılar.
        print(f"HATA: {len(bilinmeyen)} proposal belge kümesinde yok, "
              f"ör: {bilinmeyen[:3]}")
        return 2

    rule = RuleHintClassifier()
    records = []
    for doc_id, prop in proposals.items():
        rule_label, _conf = rule.classify(texts[doc_id])
        records.append(decide(texts[doc_id], prop,
                              verdicts.get(doc_id), rule_label))

    os.makedirs(args.out_dir, exist_ok=True)
    paths = {
        STATUS_SILVER: os.path.join(args.out_dir, "silver.jsonl"),
        STATUS_QUEUE: os.path.join(args.out_dir, "queue.jsonl"),
        STATUS_REJECT: os.path.join(args.out_dir, "rejected.jsonl"),
    }
    for status, path in paths.items():
        write_jsonl(path, (r.to_json() for r in records if r.status == status))

    rapor = summarize(records)
    eksik = class_balance_warnings(records, MIN_PER_CLASS)
    rapor["sinif_dengesi_uyarilari"] = eksik
    with open(os.path.join(args.out_dir, "silver_report.json"), "w",
              encoding="utf-8") as fh:
        json.dump(rapor, fh, ensure_ascii=False, indent=2)

    print(json.dumps(rapor, ensure_ascii=False, indent=2))
    if not any(r.status == STATUS_QUEUE for r in records):
        # Boş kuyruk iyi haber değil: uzlaşma hiçbir şeyi yakalamıyor olabilir.
        print("\nUYARI: insan kuyruğu BOŞ. İki LLM hiç ayrışmadıysa "
              "denetleyici bağımsız çalışmıyor olabilir (lastik damga).")
    if eksik:
        print("\nSınıf dengesi eksikleri (fine-tune için):")
        for line in eksik:
            print(f"  - {line}")
    return 0


def _load_gold_types(path: str) -> dict[str, str]:
    """gold.v1.json içinden doc_id -> campaign_type."""
    from scripts.gold_schema import load_gold
    out: dict[str, str] = {}
    for rec in load_gold(path):
        val = rec.fields.get("campaign_type")
        if isinstance(val, str) and val:
            out[rec.doc_id] = val
    return out


def cmd_score(args: argparse.Namespace) -> int:
    if not os.path.exists(args.gold):
        print(f"HATA: gold bulunamadı: {args.gold}\n"
              "Gümüş etiketler gold DERLENDİKTEN sonra ölçülebilir; "
              "ölçülmemiş gümüş veri raporda savunulamaz.")
        return 2
    gold = _load_gold_types(args.gold)
    if not gold:
        print("HATA: gold içinde campaign_type taşıyan kayıt yok.")
        return 2

    from src.extraction.silver import SilverRecord
    records: list[SilverRecord] = []
    for item in read_jsonl(args.silver):
        votes = item.get("votes") or {}
        records.append(SilverRecord(
            doc_id=item["doc_id"], label=item.get("label"),
            status=item.get("status", STATUS_SILVER),
            confidence=item.get("confidence", ""),
            reason=item.get("reason", ""), evidence=item.get("evidence", ""),
            rule_label=votes.get("rule"), llm_label=votes.get("labeler"),
            verifier_label=votes.get("verifier"),
            labeler=item.get("labeler", ""), verifier=item.get("verifier", ""),
        ))

    sonuc = score_against_gold(records, gold)
    print(json.dumps(sonuc, ensure_ascii=False, indent=2))
    if sonuc["gumus_olarak_puanlanan"] < 20:
        print("\nUYARI: kesişim 20'nin altında — bu oran istatistiksel "
              "olarak zayıf, raporda örneklem boyutuyla birlikte verilmeli.")
    return 0


def main(argv: Optional[list[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Gümüş etiket hattı")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("prepare", help="etiketlenecek partiyi çıkar")
    p.add_argument("--docs", default="data/raw-classic")
    p.add_argument("--out", default="data/silver/batch.jsonl")
    p.set_defaults(fn=cmd_prepare)

    pv = sub.add_parser("prepare-verify", help="denetleyici partisini çıkar")
    pv.add_argument("--docs", default="data/raw-classic")
    pv.add_argument("--proposals", default="data/silver/proposals.jsonl")
    pv.add_argument("--out", default="data/silver/verify_batch.jsonl")
    pv.set_defaults(fn=cmd_prepare_verify)

    m = sub.add_parser("merge", help="üç oylu uzlaşma")
    m.add_argument("--docs", default="data/raw-classic")
    m.add_argument("--proposals", default="data/silver/proposals.jsonl")
    m.add_argument("--verdicts", default="data/silver/verdicts.jsonl")
    m.add_argument("--out-dir", default="data/silver")
    m.set_defaults(fn=cmd_merge)

    s = sub.add_parser("score", help="gold'a karşı ölç")
    s.add_argument("--silver", default="data/silver/silver.jsonl")
    s.add_argument("--gold", default="data/gold/gold.v1.json")
    s.set_defaults(fn=cmd_score)

    args = ap.parse_args(argv)
    return int(args.fn(args))


if __name__ == "__main__":
    raise SystemExit(main())
