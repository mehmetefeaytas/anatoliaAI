"""Gümüş etiket partisini METİN HACMİNE göre dengeli kümelere böler.

İlgili: scripts/silver_parti_hazirla.py (partiyi üretir)

Belge sayısına göre bölmek yanıltıcıdır: korpusta 1 KB'lik kampanya sayfası da
50 KB'lik ücret tarifesi de var. Eşit sayıda belge alan iki küme, on kat farklı
metin okuyabilir. Bölme **karakter** üzerinden yapılır (en büyük parça önce —
"longest processing time first"), böylece kümeler dengeli kalır.

Kullanım:
    .venv/bin/python -m scripts.silver_parti_bol --kume 10 \\
        --parti data/silver/round1_parti.jsonl --out-dir data/silver/parca
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


def bol(kayitlar: list[dict], kume: int) -> list[list[dict]]:
    """En büyük belgeyi her seferinde en hafif kümeye koyar."""
    kutular: list[list[dict]] = [[] for _ in range(kume)]
    agirlik = [0] * kume
    for k in sorted(kayitlar, key=lambda r: -r["metin_karakter"]):
        i = agirlik.index(min(agirlik))
        kutular[i].append(k)
        agirlik[i] += k["metin_karakter"]
    return kutular


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--parti", default="data/silver/round1_parti.jsonl")
    ap.add_argument("--out-dir", default="data/silver/parca")
    ap.add_argument("--kume", type=int, default=10)
    ap.add_argument("--atla", default="",
                    help="virgülle ayrık doc_id listesi (pilotta bitenler)")
    args = ap.parse_args(argv)

    atla = {d.strip() for d in args.atla.split(",") if d.strip()}
    kayitlar = [
        json.loads(s)
        for s in (_ROOT / args.parti).read_text(encoding="utf-8").splitlines() if s
    ]
    kayitlar = [k for k in kayitlar if k["doc_id"] not in atla]

    hedef = _ROOT / args.out_dir
    hedef.mkdir(parents=True, exist_ok=True)

    for i, kutu in enumerate(bol(kayitlar, args.kume), 1):
        yol = hedef / f"kume_{i:02d}.jsonl"
        with yol.open("w", encoding="utf-8") as fh:
            for k in kutu:
                fh.write(json.dumps(k, ensure_ascii=False) + "\n")
        alan = sum(len(k["alanlar"]) for k in kutu)
        kar = sum(k["metin_karakter"] for k in kutu)
        print(f"  {yol.name}  belge={len(kutu):3d}  hucre={alan:4d}  "
              f"metin={kar/1024:6.0f} KB")

    print(f"\ntoplam belge={len(kayitlar)}  "
          f"hucre={sum(len(k['alanlar']) for k in kayitlar)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
