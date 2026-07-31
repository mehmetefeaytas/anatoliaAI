"""Korpus üzerinde çelişki taraması — ölçüm ve jüri demosu için CLI.

Kullanım:

    python3 -m src.comparison.scan                       # data/raw, özet
    python3 -m src.comparison.scan --detail              # her çelişkiyi kanıtıyla
    python3 -m src.comparison.scan --json out.json       # makine-okur çıktı
    python3 -m src.comparison.scan --as-of 2026-07-30    # zaman bağımlı kural

Neden ayrı bir modül: `pipeline.py` DB + LLM + scraper zincirini kurar; çelişki
ölçümü bunların hiçbirine ihtiyaç duymaz. Bu tarayıcı yalnız `data/raw` altındaki
temiz metinleri ve kural katmanını kullanır — saf stdlib, offline, saniyeler içinde
849 belge.

`scraped_at` her belgenin `.meta.json` yan dosyasından okunur; yoksa `--as-of`
kullanılır. Böylece "süresi dolmuş ama yayında" kuralı belgenin GERÇEK toplanma
tarihine göre değerlendirilir, tarama gününe göre değil (yeniden-üretilebilirlik).
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Optional

from ..extraction.rules.extract import extract_all
from ..preprocessing.clean import normalize_text
from ..schemas import Campaign
from .contradiction import Contradiction, detect, detect_across, group_by_product


def load_corpus(raw_dir: str | Path) -> list[tuple[Campaign, Optional[str], str]]:
    """data/raw altındaki her `.txt` için (Campaign, scraped_at, göreli yol).

    `.txt` dosyaları toplayıcının yazdığı TEMİZ METİNDİR (ham HTML `.html`
    dosyasında durur). Provenance yan dosyadan (`<ad>.txt.meta.json`) okunur.
    """
    base = Path(raw_dir)
    out: list[tuple[Campaign, Optional[str], str]] = []
    for path in sorted(base.rglob("*.txt")):
        meta: dict = {}
        sidecar = Path(str(path) + ".meta.json")
        if sidecar.exists():
            try:
                meta = json.loads(sidecar.read_text(encoding="utf-8"))
            except (ValueError, OSError):
                meta = {}
        text = normalize_text(path.read_text(encoding="utf-8", errors="ignore"))
        if not text:
            continue
        rel = path.relative_to(base)
        out.append((
            Campaign(
                bank_slug=meta.get("bank_slug") or rel.parts[0],
                raw_text=text,
                source_url=meta.get("source_url"),
                fields=extract_all(text),
            ),
            meta.get("scraped_at"),
            str(rel),
        ))
    return out


def scan(raw_dir: str | Path = "data/raw",
         as_of: Optional[str] = None) -> tuple[list[tuple[str, Contradiction]], dict]:
    """Korpusu tarar; (yol, çelişki) çiftleri ve istatistik döndürür."""
    corpus = load_corpus(raw_dir)
    found: list[tuple[str, Contradiction]] = []
    for campaign, scraped_at, rel in corpus:
        for con in detect(campaign, as_of=scraped_at or as_of):
            found.append((rel, con))

    campaigns = [c for c, _, _ in corpus]
    for con in detect_across(campaigns):
        found.append((con.match_key or "-", con))

    groups = group_by_product(campaigns)
    stats = {
        "belge": len(corpus),
        "banka": len({c.bank_slug for c in campaigns}),
        "eslesen_urun_grubu": len(groups),
        "eslesen_grup_icindeki_belge": sum(len(v) for v in groups.values()),
        "celiski": len(found),
        "tur_dagilimi": dict(Counter(c.kind for _, c in found)),
        "kapsam_dagilimi": dict(Counter(c.scope for _, c in found)),
    }
    return found, stats


def _print_report(found: list[tuple[str, Contradiction]], stats: dict,
                  detail: bool) -> None:
    print("=" * 72)
    print("ÇELİŞKİ TARAMASI")
    print("=" * 72)
    for k, v in stats.items():
        print(f"  {k:32s}: {v}")
    print()
    if not found:
        print("  Çelişki bulunamadı.")
        return
    for rel, con in sorted(found, key=lambda x: (x[1].kind, x[0])):
        print(f"[{con.scope}] {con.kind}  ({rel})")
        print(f"    {con.detail}")
        if detail:
            for e in con.evidence:
                print(f"      · {e.bank_slug} | {e.field_name} = {e.value!r}")
                if e.source_url:
                    print(f"        {e.source_url}")
                if e.source_span:
                    print(f"        …{e.source_span}…")
        print()


def main(argv: Optional[list[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Korpus çelişki taraması")
    ap.add_argument("--raw-dir", default="data/raw")
    ap.add_argument("--as-of", default=None,
                    help="Belgenin scraped_at'i yoksa kullanılacak ISO tarih")
    ap.add_argument("--detail", action="store_true", help="Kanıtları da yazdır")
    ap.add_argument("--json", dest="json_out", default=None)
    args = ap.parse_args(argv)

    found, stats = scan(args.raw_dir, as_of=args.as_of)
    _print_report(found, stats, args.detail)
    if args.json_out:
        payload = {"stats": stats,
                   "contradictions": [dict(source=rel, **con.to_dict())
                                      for rel, con in found]}
        Path(args.json_out).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"JSON yazıldı: {args.json_out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
