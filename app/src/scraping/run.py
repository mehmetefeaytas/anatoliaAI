"""CLI: scraping + tam pipeline çalıştırma.

Kullanım:
    python -m src.scraping.run --config config/banks.yaml --mode fixture --db data.db
"""

from __future__ import annotations

import argparse

from ..db.repository import Repository
from ..pipeline import run_pipeline


def main() -> None:
    ap = argparse.ArgumentParser(description="Anatolia AI scraping + pipeline")
    ap.add_argument("--config", default="config/banks.yaml")
    ap.add_argument("--mode", choices=["auto", "live", "fixture"], default="auto",
                    help="auto: canlı dene, boşsa fixture; fixture: offline")
    ap.add_argument("--raw-dir", default="data/raw")
    ap.add_argument("--db", default=":memory:", help="SQLite yolu (kalıcı için dosya)")
    args = ap.parse_args()

    repo = Repository(args.db)
    res = run_pipeline(repo, args.config, raw_dir=args.raw_dir, mode=args.mode)
    print(f"Kaydedilen kampanya: {res.campaigns_stored}")
    print(f"Tespit edilen çelişki: {len(res.contradictions)}")
    for c in res.contradictions:
        print(f"  - [{c['bank']}] {c['kind']}: {c['detail']}")


if __name__ == "__main__":
    main()
