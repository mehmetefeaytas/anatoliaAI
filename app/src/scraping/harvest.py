"""Gerçek veri toplama CLI'ı — 10 banka, provenance'lı, robots.txt uyumlu.

İlgili: CLAUDE.md §14, ../../decisions/python-tabanli-veri-toplama.md

Kullanım:
    python -m src.scraping.harvest --config config/banks.yaml --raw-dir data/raw
    python -m src.scraping.harvest --banks adil-katilim,tom-katilim --max-docs 20
    python -m src.scraping.harvest --ignore-robots      # VARSAYILAN KAPALI

Çıktı:
    data/raw/<slug>/live/<slug>.html + .txt + .txt.meta.json
    data/raw/<slug>/manual/            (engellenenler elle buraya konur)
    data/raw/_collection_report.md
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Optional

from .collector import (
    MANUAL_SUBDIR,
    METHOD_MANUAL,
    collect_from_fixtures,
    collect_live,
    ensure_manual_dirs,
    save_docs,
    utc_now_iso,
)
from .config import load_banks
from .fetcher import BrowserFetcher, FetcherBundle, RateLimiter, StaticFetcher
from .robots import DEFAULT_USER_AGENT, RobotsCache

REPORT_NAME = "_collection_report.md"


def harvest(config_path: str, raw_dir: str, *, only: Optional[set[str]] = None,
            max_docs: Optional[int] = None, delay_s: float = 3.0,
            ignore_robots: bool = False,
            user_agent: str = DEFAULT_USER_AGENT,
            timeout_s: float = 25.0) -> dict[str, Any]:
    """Tüm bankaları gezer, belgeleri diske yazar, rapor sözlüğü döner.

    `timeout_s`: istek başına zaman aşımı. Varsayılan 25 sn bazı alan adları
    için YETMİYOR — ölçüm (2026-08-04): vakifkart.com.tr HTTP 200 dönüyor ama
    yanıt süresi **29-31 saniye**. Varsayılanla o alan sessizce zaman aşımına
    düşüp hiç belge üretmiyordu. Yükseltmek bir bayrağa bağlandı, varsayılan
    değiştirilmedi: uzun zaman aşımını her bankaya dayatmak yavaş/ölü
    sayfalarda hasadı gereksiz uzatır.
    """
    banks = load_banks(config_path)
    ensure_manual_dirs(banks, raw_dir)
    targets = [b for b in banks if not only or b.slug in only]

    limiter = RateLimiter(delay_s)
    bundle = FetcherBundle(
        static=StaticFetcher(user_agent=user_agent, limiter=limiter,
                             timeout=timeout_s),
        browser=BrowserFetcher(user_agent=user_agent, limiter=limiter,
                               timeout_ms=int(timeout_s * 1000)))
    robots = RobotsCache(user_agent=user_agent, ignore=ignore_robots)

    summary: dict[str, Any] = {
        "started_at": utc_now_iso(), "raw_dir": raw_dir,
        "ignore_robots": ignore_robots, "delay_s": delay_s,
        "user_agent": user_agent, "banks": {},
    }
    try:
        for bank in targets:
            print(f"[{bank.slug}] mod={bank.scrape_mode} toplaniyor...", flush=True)
            diag: dict[str, Any] = {}
            docs = collect_live(bank, bundle=bundle, robots=robots,
                                max_docs=max_docs or bank.max_docs, report=diag)
            written = save_docs(docs, raw_dir) if docs else []
            manual_docs = collect_from_fixtures(
                bank, raw_dir, recursive=True)
            manual_count = sum(1 for d in manual_docs
                               if d.collection_method == METHOD_MANUAL)
            diag.update({
                "name": bank.name, "scrape_mode": bank.scrape_mode,
                "website_url": bank.website_url,
                "docs": len(docs),
                "methods": sorted({d.collection_method for d in docs}),
                "files_written": len(written),
                "bytes": sum(Path(p).stat().st_size for p in written),
                "manual_docs": manual_count,
                "robots": robots.policy_for(bank.website_url).summary(),
            })
            summary["banks"][bank.slug] = diag
            print(f"[{bank.slug}] {len(docs)} belge, {len(diag.get('blocked', []))} "
                  f"basarisiz URL", flush=True)
    finally:
        bundle.close()

    summary["finished_at"] = utc_now_iso()
    summary["total_docs"] = sum(b.get("docs", 0) for b in summary["banks"].values())
    return summary


def render_report(summary: dict[str, Any]) -> str:
    """Toplama raporunu markdown olarak üretir."""
    lines: list[str] = [
        "# Ham Veri Toplama Raporu",
        "",
        "> Otomatik üretildi: `python -m src.scraping.harvest`. "
        "Elle düzenlemeyin — yeniden koşuda üzerine yazılır.",
        "",
        f"- **Başlangıç:** {summary.get('started_at')}",
        f"- **Bitiş:** {summary.get('finished_at')}",
        f"- **User-Agent:** `{summary.get('user_agent')}`",
        f"- **Domain başına gecikme:** {summary.get('delay_s')} sn (CLAUDE.md §14)",
        f"- **robots.txt uyumu:** "
        f"{'DEVRE DIŞI (--ignore-robots)' if summary.get('ignore_robots') else 'AÇIK (varsayılan)'}",
        f"- **Toplam belge:** {summary.get('total_docs', 0)}",
        "",
        "## Banka Bazında Özet",
        "",
        "| Banka | Mod | Belge | Yöntem | Manuel | Boyut | Keşif (sitemap/liste) | Başarısız URL |",
        "|---|---|---:|---|---:|---:|---|---:|",
    ]
    for slug, b in summary.get("banks", {}).items():
        size_kb = b.get("bytes", 0) / 1024
        methods = ", ".join(b.get("methods") or []) or "—"
        lines.append(
            f"| `{slug}` | {b.get('scrape_mode')} | {b.get('docs', 0)} | {methods} | "
            f"{b.get('manual_docs', 0)} | {size_kb:.0f} KB | "
            f"{b.get('from_sitemap', 0)}/{b.get('from_listing', 0)} | "
            f"{len(b.get('blocked') or [])} |")

    total_mb = sum(b.get("bytes", 0) for b in summary.get("banks", {}).values()) / 1048576
    lines += [
        "", "## Depolama Notu", "",
        f"Toplam ham veri: **{total_mb:.0f} MB** — bunun neredeyse tamamı `.html` "
        "dosyalarıdır (`.txt` + `.meta.json` birlikte ~2 MB).",
        "",
        "`.html` cache'i CLAUDE.md §14 (provenance) gereği tutulur ve metin çıkarımı "
        "iyileştiğinde yeniden-çıkarıma imkân verir. Depo boyutu sorun olursa "
        "`data/raw/*/live/*.html` `.gitignore`'a alınabilir: `.txt` + `content_hash` "
        "provenance'ı korumaya yeter, ancak yeniden-çıkarım için tekrar toplama gerekir.",
        "",
        "## robots.txt Durumu", ""]
    for slug, b in summary.get("banks", {}).items():
        lines.append(f"- **{slug}** — {b.get('robots', 'bilinmiyor')}")

    blocked_any = False
    lines += ["", "## Engellenen / Başarısız URL'ler", "",
              "Bu URL'ler otomatik alınamadı. Şartname §5.1 manuel toplamaya izin",
              f"veriyor: sayfaları elle kaydedip `data/raw/<banka>/{MANUAL_SUBDIR}/`",
              "altına koyun (yanına `.meta.json` provenance dosyası ekleyin).", ""]
    for slug, b in summary.get("banks", {}).items():
        blocked = b.get("blocked") or []
        if not blocked:
            continue
        blocked_any = True
        lines += [f"### {slug} ({len(blocked)})", ""]
        for item in blocked[:40]:
            lines.append(f"- `{item['url']}` — **{item['reason']}** {item.get('detail', '')}".rstrip())
        if len(blocked) > 40:
            lines.append(f"- … ve {len(blocked) - 40} URL daha")
        lines.append("")
    if not blocked_any:
        lines += ["Engellenen URL yok.", ""]

    notes_any = False
    lines += ["## Notlar", ""]
    for slug, b in summary.get("banks", {}).items():
        for note in (b.get("notes") or []):
            notes_any = True
            lines.append(f"- **{slug}** — {note}")
    if not notes_any:
        lines.append("Not yok.")
    lines.append("")
    return "\n".join(lines)


def main(argv: Optional[list[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Anatolia AI — gerçek kampanya verisi toplama")
    ap.add_argument("--config", default="config/banks.yaml")
    ap.add_argument("--raw-dir", default="data/raw")
    ap.add_argument("--banks", default="", help="virgülle ayrılmış slug filtresi")
    ap.add_argument("--max-docs", type=int, default=None,
                    help="banka başına azami belge (banks.yaml'i ezer)")
    ap.add_argument("--timeout", type=float, default=25.0,
                    help="istek basina zaman asimi (sn). vakifkart.com.tr 29-31 sn "
                         "yanit veriyor; o alan icin --timeout 45 gerekir.")
    ap.add_argument("--delay", type=float, default=3.0,
                    help="domain başına saniye (CLAUDE.md §14: 2–5)")
    ap.add_argument("--ignore-robots", action="store_true",
                    help="robots.txt denetimini KAPAT (varsayılan: kapalı değil, uyumlu)")
    ap.add_argument("--json-out", default="", help="ham özeti JSON olarak yaz")
    args = ap.parse_args(argv)

    only = {s.strip() for s in args.banks.split(",") if s.strip()}
    summary = harvest(args.config, args.raw_dir, only=only or None,
                      max_docs=args.max_docs, delay_s=args.delay,
                      timeout_s=args.timeout,
                      ignore_robots=args.ignore_robots)

    report_path = Path(args.raw_dir) / REPORT_NAME
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(render_report(summary), encoding="utf-8")
    if args.json_out:
        Path(args.json_out).write_text(
            json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\nToplam {summary['total_docs']} belge. Rapor: {report_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
