"""İkinci toplama turu — ÜRÜN sayfaları.

Kullanım:
    python -m src.scraping.harvest_products --config config/banks.yaml \
        --raw-dir data/raw [--only kuveyt-turk,albaraka] [--max-docs 40]

## Neden ayrı bir tur

İlk tur `/kampanyalar` sayfalarından 292 belge topladı, ama ölçüm şunu
gösterdi: **yalnızca 11 belgede (%3,8) `kar_payi_orani` var.** Oysa
şartnamenin manşet örneği tam da bunu istiyor:

    A Bankası | Konut finansmanı | %1,89 | 120 ay | Dosya masrafı yok

Sebep: kampanya sayfaları genelde "avantajlı oranlarla" deyip ürün
sayfasına link verir. Kâr payı oranı, vade ve tahsis ücreti **ürün
sayfalarında** yaşar (konut/taşıt/ihtiyaç finansmanı, katılma hesabı,
ürün ve hizmet ücret tarifeleri).

Getirme, robots.txt uyumu, rate-limit, provenance ve tekilleştirme mantığı
kampanya turuyla AYNIDIR (`collect_live` yeniden kullanılır); tek fark
keşif fonksiyonu (`discover_products`) ve çıktı klasörü (`products/`).
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Optional

from .collector import (
    PRODUCTS_SUBDIR,
    collect_live,
    save_docs,
    utc_now_iso,
)
from .config import load_banks
from .discover import discover_products
from .fetcher import BrowserFetcher, FetcherBundle, RateLimiter, StaticFetcher
from .harvest import DEFAULT_USER_AGENT
from .robots import RobotsCache


def harvest_products(config_path: str, raw_dir: str, *,
                     only: Optional[set[str]] = None,
                     max_docs: Optional[int] = None,
                     delay_s: float = 3.0,
                     ignore_robots: bool = False,
                     user_agent: str = DEFAULT_USER_AGENT) -> dict[str, Any]:
    """Tüm bankaların ÜRÜN sayfalarını toplar, rapor sözlüğü döner."""
    banks = load_banks(config_path)
    targets = [b for b in banks if not only or b.slug in only]

    limiter = RateLimiter(delay_s)
    bundle = FetcherBundle(
        static=StaticFetcher(user_agent=user_agent, limiter=limiter),
        browser=BrowserFetcher(user_agent=user_agent, limiter=limiter))
    robots = RobotsCache(user_agent=user_agent, ignore=ignore_robots)

    summary: dict[str, Any] = {
        "started_at": utc_now_iso(), "raw_dir": raw_dir, "tur": "urun",
        "ignore_robots": ignore_robots, "delay_s": delay_s,
        "user_agent": user_agent, "banks": {},
    }
    try:
        for bank in targets:
            print(f"[{bank.slug}] urun sayfalari toplaniyor "
                  f"(mod={bank.scrape_mode})...", flush=True)
            diag: dict[str, Any] = {}
            docs = collect_live(bank, bundle=bundle, robots=robots,
                                max_docs=max_docs or 40, report=diag,
                                discover_fn=discover_products)
            written = save_docs(docs, raw_dir, subdir=PRODUCTS_SUBDIR) \
                if docs else []
            diag.update({
                "name": bank.name,
                "scrape_mode": bank.scrape_mode,
                "docs": len(docs),
                "files_written": len(written),
                "bytes": sum(Path(p).stat().st_size for p in written),
                "robots": robots.policy_for(bank.website_url).summary(),
            })
            summary["banks"][bank.slug] = diag
            print(f"[{bank.slug}] {len(docs)} urun sayfasi, "
                  f"{len(diag.get('blocked', []))} basarisiz", flush=True)
    finally:
        bundle.close()

    summary["finished_at"] = utc_now_iso()
    summary["total_docs"] = sum(b.get("docs", 0)
                                for b in summary["banks"].values())
    return summary


def field_coverage(raw_dir: str) -> tuple[int, dict[str, int]]:
    """Korpustaki alan kapsamını ölçer.

    Bu turun başarı ölçütü belge sayısı DEĞİL, kâr payı/vade içeren belge
    sayısıdır — bu yüzden ölçüm koşunun parçası.
    """
    import collections
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from src.extraction.rules.extract import extract_all
    from src.preprocessing.clean import normalize_text

    sayac: collections.Counter = collections.Counter()
    n = 0
    for f in Path(raw_dir).rglob("*.txt"):
        if f.name.endswith(".meta.json"):
            continue
        n += 1
        metin = normalize_text(f.read_text(encoding="utf-8", errors="replace"))
        for alan in extract_all(metin):
            sayac[alan.field_name] += 1
    return n, dict(sayac)


def main(argv: Optional[list[str]] = None) -> int:
    ap = argparse.ArgumentParser(
        description="Ürün sayfası toplama turu (kâr payı / vade / tahsis ücreti)")
    ap.add_argument("--config", default="config/banks.yaml")
    ap.add_argument("--raw-dir", default="data/raw")
    ap.add_argument("--only", default=None,
                    help="virgülle ayrılmış banka slug listesi")
    ap.add_argument("--max-docs", type=int, default=40)
    ap.add_argument("--delay", type=float, default=3.0)
    ap.add_argument("--ignore-robots", action="store_true",
                    help="robots.txt'i yok say (VARSAYILAN KAPALI; "
                         "CLAUDE.md §14 uyumu taahhut ediyor)")
    ap.add_argument("--out", default="data/raw/_products_report.json")
    args = ap.parse_args(argv)

    once_n, once = field_coverage(args.raw_dir)
    print(f"ONCE: {once_n} belge · kar_payi_orani={once.get('kar_payi_orani',0)}"
          f" · vade_ay={once.get('vade_ay',0)}\n")

    only = set(args.only.split(",")) if args.only else None
    summary = harvest_products(args.config, args.raw_dir, only=only,
                               max_docs=args.max_docs, delay_s=args.delay,
                               ignore_robots=args.ignore_robots)

    sonra_n, sonra = field_coverage(args.raw_dir)
    summary["field_coverage"] = {"before": once, "after": sonra,
                                 "docs_before": once_n, "docs_after": sonra_n}

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(summary, ensure_ascii=False, indent=2),
                   encoding="utf-8")

    print(f"\n{'='*58}\nSONUC\n{'='*58}")
    print(f"belge      : {once_n} -> {sonra_n}")
    for alan in ("kar_payi_orani", "vade_ay", "tahsis_ucreti",
                 "finansman_tutari"):
        a, b = once.get(alan, 0), sonra.get(alan, 0)
        ok = "  <-- HEDEF" if alan == "kar_payi_orani" else ""
        print(f"{alan:18}: {a} -> {b}{ok}")
    print(f"\nRapor: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
