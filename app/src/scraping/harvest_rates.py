"""Beşinci toplama turu — KÂR PAYI ORANI.

Kullanım:
    python -m src.scraping.harvest_rates --raw-dir data/raw
    python -m src.scraping.harvest_rates --only albaraka --max-requests 40
    python -m src.scraping.harvest_rates --dry-run          # yalnız kapsam raporu

## Neden ayrı bir tur

Aylık kâr payı oranı HTML'de YOKTUR: ürün sayfalarında yalnızca "Aylık Kâr Oranı"
ETİKETİ bulunur, değer istemci-taraflı hesaplama aracının arkasındadır. Ölçüm
(2026-08-03, 1684 belge): `kar_payi_orani` yalnızca 73 belgede var ve finansman
ürün sayfalarının hiçbirinde sayısal değer yok. Oysa şartnamenin manşet örneği
tam olarak bu alanı istiyor.

Bu tur oranı kaynağından (bankanın hesaplama ucundan) alır ve
`data/raw/<banka>/rates/quotes.jsonl` altına provenance'lı yazar.

Çıktı, kampanya/ürün metinleriyle KARIŞTIRILMAZ: ayrı küme (`rates/`), ayrı şema
(`RateQuote`). Karşılaştırma motoru bunu yapısal alan olarak kullanır; RAG metni
olarak değil.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Optional

from .collector import utc_now_iso
from .config import load_banks
from .fetcher import DEFAULT_USER_AGENT, RateLimiter, StaticFetcher
from .rates import (
    KIND_FINANCING,
    KIND_PROFIT_SHARE,
    RateGrid,
    adapter_for,
    available_slugs,
    quotes_to_jsonl,
)
from .robots import RobotsCache

RATES_SUBDIR = "rates"
QUOTES_FILE = "quotes.jsonl"
REPORT_NAME = "_rates_report.md"


def harvest_rates(config_path: str, raw_dir: str, *,
                  only: Optional[set[str]] = None,
                  grid: Optional[RateGrid] = None,
                  delay_s: float = 3.0, ignore_robots: bool = False,
                  dry_run: bool = False,
                  user_agent: str = DEFAULT_USER_AGENT) -> dict[str, Any]:
    """Adaptörü olan bankalardan oran toplar, rapor sözlüğü döner."""
    banks = load_banks(config_path)
    grid = grid or RateGrid()
    targets = [b for b in banks
               if adapter_for(b.slug) and (not only or b.slug in only)]

    fetcher = StaticFetcher(user_agent=user_agent, limiter=RateLimiter(delay_s))
    robots = RobotsCache(user_agent=user_agent, ignore=ignore_robots)

    summary: dict[str, Any] = {
        "started_at": utc_now_iso(), "raw_dir": raw_dir, "dry_run": dry_run,
        "delay_s": delay_s, "ignore_robots": ignore_robots,
        "adapter_slugs": available_slugs(),
        "banks_without_adapter": sorted(b.slug for b in banks
                                        if not adapter_for(b.slug)),
        "grid": {
            "financing_amounts": list(grid.financing_amounts),
            "financing_terms": list(grid.financing_terms),
            "deposit_amounts": list(grid.deposit_amounts),
            "deposit_term_days": list(grid.deposit_term_days),
            "max_requests": grid.max_requests,
        },
        "banks": {},
    }

    try:
        for bank in targets:
            cls = adapter_for(bank.slug)
            print(f"[{bank.slug}] oran toplaniyor (adaptor={cls.__name__})...",
                  flush=True)
            adapter = cls(fetcher, robots=robots)
            if dry_run:
                summary["banks"][bank.slug] = {
                    "name": bank.name, "dry_run": True,
                    "kinds": list(cls.kinds), "quotes": 0,
                }
                continue
            quotes = adapter.quotes(grid)
            written = 0
            if quotes:
                target = Path(raw_dir) / bank.slug / RATES_SUBDIR
                target.mkdir(parents=True, exist_ok=True)
                path = target / QUOTES_FILE
                path.write_text(quotes_to_jsonl(quotes), encoding="utf-8")
                (target / f"{QUOTES_FILE}.meta.json").write_text(
                    json.dumps({
                        "bank_slug": bank.slug,
                        "record_count": len(quotes),
                        "collected_at": utc_now_iso(),
                        "collection_method": "rate-round",
                        "requests": adapter.requests,
                        "grid": summary["grid"],
                    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
                written = len(quotes)

            fin = [q for q in quotes if q.kind == KIND_FINANCING]
            dep = [q for q in quotes if q.kind == KIND_PROFIT_SHARE]
            rates = [q.monthly_rate for q in fin if q.monthly_rate is not None]
            summary["banks"][bank.slug] = {
                "name": bank.name,
                "quotes": written,
                "financing": len(fin),
                "deposit": len(dep),
                "products": sorted({q.product_name for q in fin if q.product_name}),
                "monthly_rate_min": min(rates) if rates else None,
                "monthly_rate_max": max(rates) if rates else None,
                "requests": adapter.requests,
                "failures": adapter.failures,
                "notes": adapter.notes,
            }
            print(f"[{bank.slug}] {written} kayit "
                  f"({len(fin)} finansman, {len(dep)} katilma), "
                  f"{adapter.requests} istek, {len(adapter.failures)} basarisiz",
                  flush=True)
    finally:
        fetcher.close()

    summary["finished_at"] = utc_now_iso()
    summary["total_quotes"] = sum(b.get("quotes", 0)
                                  for b in summary["banks"].values())
    return summary


def render_report(summary: dict[str, Any]) -> str:
    """Oran turunun markdown raporu."""
    lines = [
        "# Kâr Payı Oranı Toplama Raporu",
        "",
        "> Otomatik üretildi: `python -m src.scraping.harvest_rates`. "
        "Elle düzenlemeyin — yeniden koşuda üzerine yazılır.",
        "",
        f"- **Başlangıç:** {summary.get('started_at')}",
        f"- **Bitiş:** {summary.get('finished_at')}",
        f"- **Domain başına gecikme:** {summary.get('delay_s')} sn (CLAUDE.md §14)",
        f"- **robots.txt uyumu:** "
        f"{'DEVRE DIŞI' if summary.get('ignore_robots') else 'AÇIK (varsayılan)'}",
        f"- **Toplam oran kaydı:** {summary.get('total_quotes', 0)}",
        "",
        "## Neden bu tur var",
        "",
        "Aylık kâr payı oranı HTML'de yok; değer istemci-taraflı hesaplama "
        "aracının arkasında. Ürün sayfalarında yalnızca *etiket* bulunuyor. "
        "Bu tur oranı bankanın hesaplama ucundan alır.",
        "",
        "## Banka Bazında",
        "",
        "| Banka | Kayıt | Finansman | Katılma | Aylık oran aralığı | İstek | Başarısız |",
        "|---|---:|---:|---:|---|---:|---:|",
    ]
    for slug, b in summary.get("banks", {}).items():
        lo, hi = b.get("monthly_rate_min"), b.get("monthly_rate_max")
        rng = f"%{lo}–%{hi}" if lo is not None and hi is not None else "—"
        if lo is not None and lo == hi:
            rng = f"%{lo}"
        lines.append(
            f"| `{slug}` | {b.get('quotes', 0)} | {b.get('financing', 0)} | "
            f"{b.get('deposit', 0)} | {rng} | {b.get('requests', 0)} | "
            f"{len(b.get('failures') or [])} |")

    lines += ["", "## Kapsanan ürünler", ""]
    any_products = False
    for slug, b in summary.get("banks", {}).items():
        for name in b.get("products") or []:
            any_products = True
            lines.append(f"- **{slug}** — {name}")
    if not any_products:
        lines.append("Ürün kaydı yok.")

    missing = summary.get("banks_without_adapter") or []
    lines += ["", "## Adaptörü olmayan bankalar", ""]
    if missing:
        lines += [
            "Bu bankalarda oran, parametreli bir JSON ucundan alınamıyor. "
            "Kuveyt Türk için hesaplama aracını tarayıcıyla sürmek gerekir "
            "(ayrı adaptör); diğerlerinde ya hesaplama aracı yok ya oran "
            "istemci-taraflı sabit.",
            "",
        ]
        lines += [f"- `{s}`" for s in missing]
    else:
        lines.append("Yok.")

    lines += ["", "## Başarısız istekler", ""]
    any_fail = False
    for slug, b in summary.get("banks", {}).items():
        for f in (b.get("failures") or [])[:40]:
            any_fail = True
            lines.append(f"- **{slug}** `{f['url'][:120]}` — {f['reason']} "
                         f"{f.get('detail', '')}".rstrip())
    if not any_fail:
        lines.append("Başarısız istek yok.")

    lines += ["", "## Notlar", ""]
    any_note = False
    for slug, b in summary.get("banks", {}).items():
        for n in b.get("notes") or []:
            any_note = True
            lines.append(f"- **{slug}** — {n}")
    if not any_note:
        lines.append("Not yok.")
    lines.append("")
    return "\n".join(lines)


def main(argv: Optional[list[str]] = None) -> int:
    ap = argparse.ArgumentParser(
        description="Anatolia AI — kâr payı oranı toplama (5. tur)")
    ap.add_argument("--config", default="config/banks.yaml")
    ap.add_argument("--raw-dir", default="data/raw")
    ap.add_argument("--only", default="", help="virgülle ayrılmış slug filtresi")
    ap.add_argument("--delay", type=float, default=3.0)
    ap.add_argument("--ignore-robots", action="store_true")
    ap.add_argument("--max-requests", type=int, default=200,
                    help="banka başına azami istek (emniyet supabı)")
    ap.add_argument("--dry-run", action="store_true",
                    help="istek atmadan yalnız kapsam raporu")
    ap.add_argument("--json-out", default="")
    args = ap.parse_args(argv)

    only = {s.strip() for s in args.only.split(",") if s.strip()}
    grid = RateGrid(max_requests=args.max_requests)
    summary = harvest_rates(args.config, args.raw_dir, only=only or None,
                            grid=grid, delay_s=args.delay,
                            ignore_robots=args.ignore_robots,
                            dry_run=args.dry_run)

    report_path = Path(args.raw_dir) / REPORT_NAME
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(render_report(summary), encoding="utf-8")
    if args.json_out:
        Path(args.json_out).write_text(
            json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\nToplam {summary['total_quotes']} oran kaydi. Rapor: {report_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
