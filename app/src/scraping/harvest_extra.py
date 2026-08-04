"""Üçüncü ve dördüncü toplama turları — ARŞİV (süresi dolmuş) + BELGE (PDF).

Kullanım:
    python -m src.scraping.harvest_extra --round all   --config config/banks.yaml
    python -m src.scraping.harvest_extra --round archive --only kuveyt-turk
    python -m src.scraping.harvest_extra --round docs    --only turkiye-emlak-katilim

## Neden ayrı turlar

**Arşiv turu (`archive/`):** Bankalar süresi dolmuş kampanyaları ayrı sayfalarda
tutuyor (Kuveyt Türk `/kampanyalar/kampanya-arsivi`, Türkiye Finans
`biten-kampanyalar.aspx`). Bu belgeler `suresi_dolmus_kampanya` kuralı ve
zaman-koşullu çelişki tespiti için **elle işaretlemeye gerek olmayan** doğrulama
verisidir (CLAUDE.md §6, §18-2). Aktif kampanyalarla AYNI klasöre konmaz —
karışırsa süresi geçmiş kampanya aktif sanılır (§17 adil kıyas).

**Belge turu (`docs/`):** Ücret/komisyon tarifeleri ve ürün bilgi formları HTML
tablo değil **PDF**. Kesin tahsis ücreti ve masraf oranları orada; "masrafsız"
diyen kampanya ile tarifedeki ücretin çelişmesi §18-2'nin tam hedefidir.

Getirme, robots.txt uyumu, rate-limit ve provenance mantığı kampanya turuyla
AYNIDIR; farklar keşif fonksiyonu, çıktı klasörü ve arşivde `campaign_status`.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Optional

from .collector import (
    ARCHIVE_SUBDIR,
    DOCS_SUBDIR,
    STATUS_EXPIRED,
    collect_documents,
    collect_live,
    save_docs,
    utc_now_iso,
)
from .config import load_banks
from .discover import discover_archive
from .fetcher import BrowserFetcher, FetcherBundle, RateLimiter, StaticFetcher
from .robots import DEFAULT_USER_AGENT, RobotsCache

ROUND_ARCHIVE = "archive"
ROUND_DOCS = "docs"
REPORT_NAME = "_extra_report.md"


def harvest_extra(config_path: str, raw_dir: str, *,
                  rounds: tuple[str, ...] = (ROUND_ARCHIVE, ROUND_DOCS),
                  only: Optional[set[str]] = None,
                  max_docs: Optional[int] = None,
                  delay_s: float = 3.0,
                  ignore_robots: bool = False,
                  user_agent: str = DEFAULT_USER_AGENT) -> dict[str, Any]:
    """Arşiv ve/veya belge turlarını koşar, rapor sözlüğü döner."""
    banks = load_banks(config_path)
    targets = [b for b in banks if not only or b.slug in only]

    limiter = RateLimiter(delay_s)
    bundle = FetcherBundle(
        static=StaticFetcher(user_agent=user_agent, limiter=limiter),
        browser=BrowserFetcher(user_agent=user_agent, limiter=limiter))
    robots = RobotsCache(user_agent=user_agent, ignore=ignore_robots)

    summary: dict[str, Any] = {
        "started_at": utc_now_iso(), "raw_dir": raw_dir,
        "rounds": list(rounds), "ignore_robots": ignore_robots,
        "delay_s": delay_s, "user_agent": user_agent, "banks": {},
    }
    try:
        for bank in targets:
            entry: dict[str, Any] = {"name": bank.name,
                                     "scrape_mode": bank.scrape_mode}

            if ROUND_ARCHIVE in rounds:
                print(f"[{bank.slug}] arsiv (suresi dolmus) turu...", flush=True)
                diag: dict[str, Any] = {}
                docs = collect_live(
                    bank, bundle=bundle, robots=robots,
                    max_docs=max_docs or bank.max_archive_docs, report=diag,
                    discover_fn=discover_archive,
                    campaign_status=STATUS_EXPIRED)
                written = save_docs(docs, raw_dir, subdir=ARCHIVE_SUBDIR) if docs else []
                entry["archive"] = {
                    "docs": len(docs), "files_written": len(written),
                    "discovered": diag.get("discovered", 0),
                    "bytes": sum(Path(p).stat().st_size for p in written),
                    "blocked": diag.get("blocked", []),
                    "notes": diag.get("notes", []),
                }
                print(f"[{bank.slug}] arsiv: {len(docs)} belge", flush=True)

            if ROUND_DOCS in rounds:
                print(f"[{bank.slug}] belge (PDF) turu...", flush=True)
                diag = {}
                docs = collect_documents(
                    bank, bundle=bundle, robots=robots,
                    max_docs=max_docs or bank.max_document_docs, report=diag)
                written = save_docs(docs, raw_dir, subdir=DOCS_SUBDIR) if docs else []
                entry["docs"] = {
                    "docs": len(docs), "files_written": len(written),
                    "discovered": diag.get("doc_discovered", 0),
                    "bytes": sum(Path(p).stat().st_size for p in written),
                    "pages": sum(d.pdf_pages or 0 for d in docs),
                    "blocked": diag.get("blocked", []),
                    "notes": diag.get("notes", []),
                }
                print(f"[{bank.slug}] belge: {len(docs)} PDF, "
                      f"{entry['docs']['pages']} sayfa", flush=True)

            summary["banks"][bank.slug] = entry
    finally:
        bundle.close()

    summary["finished_at"] = utc_now_iso()
    summary["total_archive_docs"] = sum(
        b.get("archive", {}).get("docs", 0) for b in summary["banks"].values())
    summary["total_pdf_docs"] = sum(
        b.get("docs", {}).get("docs", 0) for b in summary["banks"].values())
    return summary


def render_report(summary: dict[str, Any]) -> str:
    """Arşiv + belge turlarının markdown raporu."""
    lines = [
        "# Ek Toplama Turları Raporu (Arşiv + PDF Belge)",
        "",
        "> Otomatik üretildi: `python -m src.scraping.harvest_extra`. "
        "Elle düzenlemeyin — yeniden koşuda üzerine yazılır.",
        "",
        f"- **Başlangıç:** {summary.get('started_at')}",
        f"- **Bitiş:** {summary.get('finished_at')}",
        f"- **Turlar:** {', '.join(summary.get('rounds') or [])}",
        f"- **Domain başına gecikme:** {summary.get('delay_s')} sn (CLAUDE.md §14)",
        f"- **robots.txt uyumu:** "
        f"{'DEVRE DIŞI' if summary.get('ignore_robots') else 'AÇIK (varsayılan)'}",
        f"- **Arşiv belgesi:** {summary.get('total_archive_docs', 0)}",
        f"- **PDF belgesi:** {summary.get('total_pdf_docs', 0)}",
        "",
        "## Arşiv Turu — Süresi Dolmuş Kampanyalar",
        "",
        "`campaign_status: expired` etiketiyle `data/raw/<banka>/archive/` altına "
        "yazılır. Aktif kampanyalarla karışmaması `discover.DEFAULT_ARCHIVE_PATTERNS` "
        "ile garanti edilir (aktif turda exclude, arşiv turunda include).",
        "",
        "| Banka | Keşif | Belge | Boyut |",
        "|---|---:|---:|---:|",
    ]
    for slug, b in summary.get("banks", {}).items():
        a = b.get("archive")
        if not a:
            continue
        lines.append(f"| `{slug}` | {a.get('discovered', 0)} | {a.get('docs', 0)} | "
                     f"{a.get('bytes', 0) / 1024:.0f} KB |")

    lines += ["", "## Belge Turu — PDF Ücret Tarifeleri / Bilgi Formları", "",
              "| Banka | Keşif | PDF | Sayfa | Boyut |", "|---|---:|---:|---:|---:|"]
    for slug, b in summary.get("banks", {}).items():
        d = b.get("docs")
        if not d:
            continue
        lines.append(f"| `{slug}` | {d.get('discovered', 0)} | {d.get('docs', 0)} | "
                     f"{d.get('pages', 0)} | {d.get('bytes', 0) / 1024:.0f} KB |")

    blocked_any = False
    lines += ["", "## Engellenen / Başarısız", ""]
    for slug, b in summary.get("banks", {}).items():
        for round_name in ("archive", "docs"):
            for item in (b.get(round_name) or {}).get("blocked") or []:
                blocked_any = True
                lines.append(f"- **{slug}/{round_name}** `{item['url']}` — "
                             f"{item['reason']} {item.get('detail', '')}".rstrip())
    if not blocked_any:
        lines.append("Engellenen URL yok.")

    notes_any = False
    lines += ["", "## Notlar", ""]
    for slug, b in summary.get("banks", {}).items():
        for round_name in ("archive", "docs"):
            for note in (b.get(round_name) or {}).get("notes") or []:
                notes_any = True
                lines.append(f"- **{slug}/{round_name}** — {note}")
    if not notes_any:
        lines.append("Not yok.")
    lines.append("")
    return "\n".join(lines)


def main(argv: Optional[list[str]] = None) -> int:
    ap = argparse.ArgumentParser(
        description="Anatolia AI — arşiv (süresi dolmuş) + PDF belge toplama")
    ap.add_argument("--config", default="config/banks.yaml")
    ap.add_argument("--raw-dir", default="data/raw")
    ap.add_argument("--round", default="all",
                    choices=["all", ROUND_ARCHIVE, ROUND_DOCS])
    ap.add_argument("--only", default="", help="virgülle ayrılmış slug filtresi")
    ap.add_argument("--max-docs", type=int, default=None,
                    help="tur başına azami belge (banks.yaml'i ezer)")
    ap.add_argument("--delay", type=float, default=3.0)
    ap.add_argument("--ignore-robots", action="store_true")
    ap.add_argument("--json-out", default="")
    args = ap.parse_args(argv)

    rounds = (ROUND_ARCHIVE, ROUND_DOCS) if args.round == "all" else (args.round,)
    only = {s.strip() for s in args.only.split(",") if s.strip()}
    summary = harvest_extra(args.config, args.raw_dir, rounds=rounds,
                            only=only or None, max_docs=args.max_docs,
                            delay_s=args.delay, ignore_robots=args.ignore_robots)

    report_path = Path(args.raw_dir) / REPORT_NAME
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(render_report(summary), encoding="utf-8")
    if args.json_out:
        Path(args.json_out).write_text(
            json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\nArsiv: {summary['total_archive_docs']} belge, "
          f"PDF: {summary['total_pdf_docs']} belge. Rapor: {report_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
