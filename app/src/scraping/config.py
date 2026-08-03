"""banks.yaml yükleyici — pyyaml varsa onu, yoksa şemaya özel mini-parser.

İlgili: ../../decisions/bddk-listesi-veri-kaynagi-kapsami.md

Mini-parser yalnız banks.yaml'in bilinen yapısını destekler (banka listesi: skaler
alanlar + campaign_paths nested listesi). Üretimde pyyaml kullanılır.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field, fields
from pathlib import Path
from typing import Optional


@dataclass
class BankConfig:
    """Tek bir bankanın toplama tarifi.

    `scrape_mode` artık gerçekten dispatch edilir (collector/fetcher):
    static → requests+bs4, js → Playwright, manual → yalnız data/raw fixture.
    """

    slug: str
    name: str
    website_url: str
    scrape_mode: str = "static"
    campaign_paths: list[str] = field(default_factory=list)
    bddk_active: bool = True
    # Keşif (iki aşamalı gezinme) ayarları — bkz. scraping/discover.py
    sitemap_urls: list[str] = field(default_factory=list)
    detail_patterns: list[str] = field(default_factory=list)
    exclude_patterns: list[str] = field(default_factory=list)
    # ÜRÜN keşfi — kampanya keşfinden AYRI tutulur (2. toplama turu).
    # Kâr payı oranı / vade / tahsis ücreti kampanya sayfasında değil, ürün
    # sayfasındadır ("avantajlı oranlarla" deyip ürüne link verirler).
    # Boşsa `sitemap_urls` / varsayılan desenler kullanılır.
    product_paths: list[str] = field(default_factory=list)
    product_sitemap_urls: list[str] = field(default_factory=list)
    product_patterns: list[str] = field(default_factory=list)
    product_exclude_patterns: list[str] = field(default_factory=list)
    max_product_docs: int = 80
    # ARŞİV keşfi — SÜRESİ DOLMUŞ kampanyalar (3. toplama turu).
    # Bankalar biten kampanyaları ayrı sayfada tutuyor (Kuveyt Türk
    # /kampanyalar/kampanya-arsivi, Türkiye Finans biten-kampanyalar.aspx).
    # Bunlar `suresi_dolmus_kampanya` kuralı ve zaman-koşullu çelişki tespiti için
    # ELLE İŞARETLEMEYE GEREK OLMAYAN doğrulama verisidir (CLAUDE.md §6, §18-2).
    archive_paths: list[str] = field(default_factory=list)
    archive_patterns: list[str] = field(default_factory=list)
    max_archive_docs: int = 60
    # BELGE (PDF) keşfi — ücret tarifeleri + ürün bilgi formları (4. toplama turu).
    # Ücret/komisyon tarifeleri HTML tablo DEĞİL PDF olarak yayımlanıyor; kesin
    # tahsis ücreti / masraf oranları oradadır (2026-08-03 tarayıcı doğrulaması).
    document_paths: list[str] = field(default_factory=list)
    document_patterns: list[str] = field(default_factory=list)
    # PDF'lerin durduğu ek alan adları (ör. asset.emlakkatilim.com.tr).
    # `extra_hosts`ten AYRI: o kampanya kataloğu için, bu yalnızca belge indirme.
    document_hosts: list[str] = field(default_factory=list)
    max_document_docs: int = 40
    # Bankanın kampanyalarını AYRI alan adında yayımladığı durumlar
    # (ör. TOM Bank → tombankhadi.com). Keşifte bu alanlar da "aynı site" sayılır.
    extra_hosts: list[str] = field(default_factory=list)
    max_docs: int = 40
    notes: str = ""


# banks.yaml'de tanınan liste alanları (mini-parser için)
_LIST_KEYS = ("campaign_paths", "sitemap_urls", "detail_patterns", "exclude_patterns",
              "extra_hosts", "product_paths", "product_sitemap_urls",
              "product_patterns", "product_exclude_patterns",
              "archive_paths", "archive_patterns",
              "document_paths", "document_patterns", "document_hosts")
# int'e çevrilmesi gereken alanlar (mini-parser YAML tip çıkarımı yapmaz)
_INT_KEYS = ("max_docs", "max_product_docs", "max_archive_docs", "max_document_docs")
# BankConfig'de karşılığı olmayan anahtarlar sessizce yok sayılır (ileri uyumluluk)
_KNOWN_KEYS = {f.name for f in fields(BankConfig)}


def load_banks(path: str | Path) -> list[BankConfig]:
    text = Path(path).read_text(encoding="utf-8")
    data = _parse(text)
    out: list[BankConfig] = []
    for raw in data.get("banks", []) or []:
        clean = {k: v for k, v in raw.items() if k in _KNOWN_KEYS}
        for key in _INT_KEYS:
            if key in clean:
                clean[key] = int(clean[key])
        out.append(BankConfig(**clean))
    return out


def _parse(text: str) -> dict:
    try:
        import yaml  # type: ignore
        return yaml.safe_load(text)
    except ModuleNotFoundError:
        return _mini_parse(text)


def _coerce(v: str):
    v = v.strip()
    if v.lower() in ("true", "false"):
        return v.lower() == "true"
    # tırnaklı değerler (regex desenleri '\.pdf$' gibi) tırnaksızlaştırılır
    if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
        return v[1:-1]
    if re.fullmatch(r"-?\d+", v):
        return int(v)
    return v


def _mini_parse(text: str) -> dict:
    """banks.yaml'in bilinen yapısı için minimal ayrıştırıcı.

    Desteklenen: 'banks:' altında '- key: val' blokları ve _LIST_KEYS içindeki
    her anahtar için nested '- item' listeleri. Yorumlar (#) ve boş satırlar atlanır.

    NOT: liste öğesi ':' içerebilir (URL'ler), bu yüzden liste-öğesi tespiti
    aktif liste anahtarına göre yapılır, ':' varlığına göre değil.
    """
    banks: list[dict] = []
    cur: Optional[dict] = None
    list_key: Optional[str] = None
    for raw in text.splitlines():
        line = raw.split("#", 1)[0].rstrip() if not _in_quotes_hash(raw) else raw.rstrip()
        if not line.strip():
            continue
        stripped = line.strip()
        indent = len(line) - len(line.lstrip())

        if stripped == "banks:":
            continue
        # yeni banka bloğu başlangıcı: "- slug: ..." (en dış girinti)
        if stripped.startswith("- ") and indent <= 2 and ":" in stripped \
                and list_key is None:
            cur = {}
            banks.append(cur)
            k, _, v = stripped[2:].partition(":")
            cur[k.strip()] = _coerce(v)
            continue
        # aktif bir liste anahtarı varsa "- item" o listeye girer
        if stripped.startswith("- ") and list_key is not None and cur is not None:
            cur.setdefault(list_key, []).append(_coerce(stripped[2:]))
            continue
        # key: value (banka alanı)
        if ":" in stripped and cur is not None:
            k, _, v = stripped.partition(":")
            k = k.strip()
            if k in _LIST_KEYS and not v.strip():
                list_key = k
                cur[k] = []
            else:
                list_key = None
                cur[k] = _coerce(v)
    return {"banks": banks}


def _in_quotes_hash(raw: str) -> bool:
    """'#' karakteri tırnak içindeyse yorum başlangıcı sayılmaz."""
    stripped = raw.strip()
    if "#" not in stripped:
        return False
    before = stripped.split("#", 1)[0]
    return before.count("'") % 2 == 1 or before.count('"') % 2 == 1
