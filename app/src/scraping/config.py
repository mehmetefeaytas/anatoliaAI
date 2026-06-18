"""banks.yaml yükleyici — pyyaml varsa onu, yoksa şemaya özel mini-parser.

İlgili: ../../decisions/bddk-listesi-veri-kaynagi-kapsami.md

Mini-parser yalnız banks.yaml'in bilinen yapısını destekler (banka listesi: skaler
alanlar + campaign_paths nested listesi). Üretimde pyyaml kullanılır.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class BankConfig:
    slug: str
    name: str
    website_url: str
    scrape_mode: str = "static"
    campaign_paths: list[str] = field(default_factory=list)
    bddk_active: bool = True


def load_banks(path: str | Path) -> list[BankConfig]:
    text = Path(path).read_text(encoding="utf-8")
    data = _parse(text)
    return [BankConfig(**b) for b in data.get("banks", [])]


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
    return v


def _mini_parse(text: str) -> dict:
    """banks.yaml'in bilinen yapısı için minimal ayrıştırıcı.

    Desteklenen: 'banks:' altında '- key: val' blokları ve 'campaign_paths:'
    nested '- item' listeleri. Yorumlar (#) ve boş satırlar atlanır.
    """
    banks: list[dict] = []
    cur: Optional[dict] = None
    in_paths = False
    for raw in text.splitlines():
        line = raw.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        stripped = line.strip()
        indent = len(line) - len(line.lstrip())

        if stripped == "banks:":
            continue
        # yeni banka bloğu başlangıcı: "- slug: ..."
        if stripped.startswith("- ") and ":" in stripped and indent <= 2:
            cur = {}
            banks.append(cur)
            in_paths = False
            k, _, v = stripped[2:].partition(":")
            cur[k.strip()] = _coerce(v)
            continue
        # campaign_paths listesi öğesi: "- /path"
        if stripped.startswith("- ") and ":" not in stripped:
            if cur is not None and in_paths:
                cur.setdefault("campaign_paths", []).append(_coerce(stripped[2:]))
            continue
        # key: value (banka alanı)
        if ":" in stripped and cur is not None:
            k, _, v = stripped.partition(":")
            k = k.strip()
            if k == "campaign_paths":
                in_paths = True
                cur["campaign_paths"] = []
            else:
                in_paths = False
                cur[k] = _coerce(v)
    return {"banks": banks}
