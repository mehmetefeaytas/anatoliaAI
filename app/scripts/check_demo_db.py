"""Demo DB korpusla güncel mi? — sessiz bayatlamaya karşı kapı.

İlgili: build_demo_db.py, ../src/pipeline.py, ../docs/rapor/rag-terim-kapsama.md

## Neden var — gerçekleşmiş bir vaka

`data/demo.db` **31 Temmuz'da** kuruldu (849 belge). Korpus **3 Ağustos'ta**
1761 belgeye çıktı ve `docs/` bölümü (sözleşme + tarife) o gün eklendi.
Arada geçen bir haftada:

- chatbot, dashboard ve RAG korpusun **%48'ini** hiç görmedi,
- fıkhî terim yoğunluğu en yüksek bölümün **tamamı** erişilemez kaldı,
- hiçbir yerde uyarı çıkmadı, hiçbir test kırılmadı.

Fark ancak terim kapsaması elle ölçülünce görüldü. Bu betik o boşluğu
kapatır: DB'deki kampanya sayısı ile korpustaki belge sayısı ayrışırsa
**gürültülü** biçimde başarısız olur.

## Neden dosya zaman damgası DEĞİL

`mtime` klon/checkout sonrası yeniden yazılır ve git zaman bilgisini
korumaz. Belge SAYISI ise hem sağlam hem de tam olarak yaşanan hatayı
yakalar (849 ≠ 1761).

## Kullanım

    python -m scripts.check_demo_db                     # varsayılan yollar
    python -m scripts.check_demo_db --db data/demo.db --raw-dir data/raw
    python -m scripts.check_demo_db --tolerans 5        # N belgelik sapmayı hoş gör

Çıkış kodları: 0 güncel · 1 BAYAT · 2 DB yok / okunamıyor.

CI'da `lint` işine eklenebilir. `data/demo.db` git'te izlenmediği için CI'da
tipik olarak kod 2 döner — bu yüzden CI'da `--db-yoksa-gec` ile koşulmalı.
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

KOK = Path(__file__).resolve().parents[1]
if str(KOK) not in sys.path:
    sys.path.insert(0, str(KOK))

VARSAYILAN_DB = "data/demo.db"
VARSAYILAN_RAW = "data/raw"
CORPUS_SUFFIX = ".txt"


def korpus_belge_sayisi(raw_dir: str) -> int:
    """`collect_corpus` ile AYNI ölçütü kullanır: özyinelemeli `.txt`.

    Ölçüt burada elle tekrarlanıyor çünkü bu betiğin işi pipeline'ı
    doğrulamak; pipeline'ı import edip ona sormak, denetlenen şeyle
    denetleyeni aynı kaynağa bağlardı.
    """
    return sum(1 for p in Path(raw_dir).rglob(f"*{CORPUS_SUFFIX}") if p.is_file())


def db_kampanya_sayisi(db: str) -> int:
    conn = sqlite3.connect(db)
    try:
        return conn.execute("SELECT COUNT(*) FROM campaigns").fetchone()[0]
    finally:
        conn.close()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="python -m scripts.check_demo_db",
        description="Demo DB korpusla güncel mi? Bayatsa gürültülü başarısız olur.")
    ap.add_argument("--db", default=VARSAYILAN_DB)
    ap.add_argument("--raw-dir", default=VARSAYILAN_RAW)
    ap.add_argument("--tolerans", type=int, default=0,
                    help="hoş görülen belge farkı (varsayılan 0)")
    ap.add_argument("--db-yoksa-gec", action="store_true",
                    help="DB dosyası yoksa 2 yerine 0 dön (CI için)")
    args = ap.parse_args(argv)

    if not Path(args.db).is_file():
        if args.db_yoksa_gec:
            print(f"DB yok, atlanıyor: {args.db}")
            return 0
        print(f"HATA: DB bulunamadı: {args.db}\n"
              f"  Kurmak için: python -m scripts.build_demo_db --out {args.db}",
              file=sys.stderr)
        return 2
    if not Path(args.raw_dir).is_dir():
        print(f"HATA: korpus dizini yok: {args.raw_dir}", file=sys.stderr)
        return 2

    try:
        db_n = db_kampanya_sayisi(args.db)
    except sqlite3.Error as e:
        print(f"HATA: DB okunamadı ({args.db}): {e}", file=sys.stderr)
        return 2
    korpus_n = korpus_belge_sayisi(args.raw_dir)
    fark = korpus_n - db_n

    print(f"DB kampanya   : {db_n}")
    print(f"korpus belge  : {korpus_n}")
    print(f"fark          : {fark:+d}")

    if abs(fark) <= args.tolerans:
        print("\nGÜNCEL.")
        return 0

    print(f"\nBAYAT: DB korpusun {abs(fark)} belgesini {'görmüyor' if fark > 0 else 'fazladan taşıyor'}.",
          file=sys.stderr)
    if fark > 0:
        print("  Chatbot, dashboard ve RAG bu belgeleri hiç görmez — sessizce.",
              file=sys.stderr)
    print(f"  Düzeltme: python -m scripts.build_demo_db --out {args.db} --force",
          file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
