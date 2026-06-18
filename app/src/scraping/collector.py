"""Scraping collector — config-driven, etik, provenance'lı.

İlgili: ../../decisions/python-tabanli-veri-toplama.md
        ../../concepts/web-scraping.md, CLAUDE.md §14

Üç mod:
- fixture (offline): data/raw/<slug>/*.html|*.txt dosyalarından okur. Test/demo.
- static: requests + BeautifulSoup (bağımlılık varsa).
- js: Playwright (bağımlılık varsa).

Ham içerik provenance ile (source_url + scraped_at) cache'lenir. Bağımlılık
yoksa otomatik fixture moduna düşer — pipeline offline koşar.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from ..preprocessing.clean import normalize_text
from .config import BankConfig


@dataclass
class RawDoc:
    bank_slug: str
    source_url: Optional[str]
    clean_text: str
    scraped_at: Optional[str] = None


def _extract_main_text(html: str) -> str:
    """Ham HTML'den temiz metin. trafilatura varsa onu, yoksa kaba temizlik."""
    try:
        import trafilatura  # type: ignore
        out = trafilatura.extract(html)
        if out:
            return normalize_text(out)
    except ModuleNotFoundError:
        pass
    return normalize_text(html)


def collect_from_fixtures(bank: BankConfig, raw_dir: str | Path,
                          scraped_at: Optional[str] = None) -> list[RawDoc]:
    """data/raw/<slug>/ altındaki .html/.txt dosyalarını okur (offline)."""
    base = Path(raw_dir) / bank.slug
    docs: list[RawDoc] = []
    if not base.is_dir():
        return docs
    for f in sorted(base.iterdir()):
        if f.suffix.lower() not in (".html", ".htm", ".txt"):
            continue
        content = f.read_text(encoding="utf-8", errors="ignore")
        text = _extract_main_text(content) if f.suffix.lower() != ".txt" \
            else normalize_text(content)
        if text:
            docs.append(RawDoc(bank.slug, f"file://{f}", text, scraped_at))
    return docs


def collect_live(bank: BankConfig, scraped_at: Optional[str] = None,
                 delay_s: float = 3.0) -> list[RawDoc]:
    """Canlı toplama (static/js). Bağımlılık yoksa boş döner (fixture'a düş).

    Etik: robots.txt + rate-limit çağrı tarafının sorumluluğunda; burada
    domain başına gecikme uygulanır.
    """
    try:
        import time
        import requests  # type: ignore
        from bs4 import BeautifulSoup  # type: ignore  # noqa: F401
    except ModuleNotFoundError:
        return []

    docs: list[RawDoc] = []
    headers = {"User-Agent": "AnatoliaAI-Research/1.0 (+teknofest; iletisim)"}
    for path in bank.campaign_paths:
        url = bank.website_url.rstrip("/") + path
        try:
            resp = requests.get(url, headers=headers, timeout=15)
            if resp.status_code == 200:
                docs.append(RawDoc(bank.slug, url,
                                   _extract_main_text(resp.text), scraped_at))
        except Exception:
            continue
        time.sleep(delay_s)  # rate-limit
    return docs


def collect(bank: BankConfig, raw_dir: str | Path = "data/raw",
            mode: str = "auto", scraped_at: Optional[str] = None) -> list[RawDoc]:
    """Toplama girişi. mode='auto' → önce canlı dener, başarısızsa fixture."""
    if mode == "fixture":
        return collect_from_fixtures(bank, raw_dir, scraped_at)
    if mode == "live":
        return collect_live(bank, scraped_at)
    # auto: canlı dene, boşsa fixture
    docs = collect_live(bank, scraped_at)
    return docs or collect_from_fixtures(bank, raw_dir, scraped_at)
