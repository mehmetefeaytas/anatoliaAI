"""Yedekten özetleri geri yükler — `build_demo_db` onları silmeden önce/sonra.

İlgili: scripts/build_demo_db.py (DB'yi yeniden kurar, `ozet`i BİLMEZ)
        scripts/build_summaries.py (özetleri ÜRETİR, ~4 saat)
        src/summarize/ozet.py (sahte özet yasağı)

## Bu betiğin varlık sebebi

`build_demo_db --force` DB'yi sıfırdan kurar ve `campaigns.ozet` sütununu boş
bırakır: o betik özetleri hiç bilmez. Özetler ise yerel modelle üretiliyor ve
1751 belge için ölçülen süre ~4 saat.

2026-08-10'da DB bir kez yeniden kuruldu ve özetler geçici bir betikle geri
yüklendi. Geçici betik depoda kalmadı, yani bir sonraki `--force` aynı 4 saati
yeniden yakacaktı. Kalıcı hâli budur.

## Anahtar neden içerik hash'i

İlk yedek `source_url` ile anahtarlanmıştı ve **97 mükerrer** çıktı: aynı URL
birden çok kampanya kaydında geçiyor (aynı sayfanın `live/` ve `archive/`
kopyaları, bölüm tekrarları). Belirsiz eşleşme, bir belgeye BAŞKA belgenin
özetini yazma riskidir — ve o özet ekranda "AI özeti" etiketiyle görünür.

Anahtar `sha256(raw_text)`: aynı metin zaten aynı özeti hak eder, yani
mükerrerlerde de doğru sonuç verir. `source_url` yalnızca ikinci anahtardır ve
İKİSİ BİRDEN tuttuğunda yazılır — tek anahtara düşen kayıt YAZILMAZ, sayılır.

## Uydurma yok

Eşleşmeyen kayıt için özet ÜRETİLMEZ ve tahmin edilmez; sayılır ve raporlanır.
Eksik özet, belgenin kendisiyle ilgili bir eksiklik değildir (`ozet.py`).

## Kullanım

    # 1) Yeniden kurmadan ÖNCE yedekle
    .venv/bin/python -m scripts.ozet_geri_yukle --yedekle \\
        --db data/demo.db --yedek data/ozet-yedegi.json

    # 2) build_demo_db --force ...

    # 3) Geri yükle
    .venv/bin/python -m scripts.ozet_geri_yukle \\
        --db data/demo.db --yedek data/ozet-yedegi.json

    # yazmadan dene
    .venv/bin/python -m scripts.ozet_geri_yukle --kuru --db ... --yedek ...

Çıkış kodu: 0 tamam · 1 dosya yok · 2 hiçbir kayıt eşleşmedi (şüpheli).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import sys
from pathlib import Path


def _hash(metin: str) -> str:
    return hashlib.sha256((metin or "").encode("utf-8")).hexdigest()


def yedekle(db: Path, hedef: Path) -> dict:
    """Özetleri `(metin_hash, source_url, ozet)` üçlüsü olarak dışa alır."""
    conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        kayit = [
            {"metin_hash": _hash(r["raw_text"]),
             "source_url": r["source_url"],
             "ozet": r["ozet"]}
            for r in conn.execute(
                "SELECT raw_text, source_url, ozet FROM campaigns "
                "WHERE ozet IS NOT NULL AND TRIM(ozet) <> ''")
        ]
    finally:
        conn.close()
    hedef.write_text(json.dumps(kayit, ensure_ascii=False, indent=1),
                     encoding="utf-8")
    return {"yedeklenen": len(kayit),
            "tekil_hash": len({k["metin_hash"] for k in kayit}),
            "dosya": str(hedef)}


def geri_yukle(db: Path, yedek: Path, kuru: bool = False) -> dict:
    """Yedeği DB'ye yazar. İKİ anahtar da tutmalı; yoksa yazılmaz."""
    kayitlar = json.loads(yedek.read_text(encoding="utf-8"))
    # (hash, url) -> özet. Tek anahtarla eşleşme BİLEREK desteklenmiyor:
    # belirsiz eşleşme, bir belgeye başka belgenin özetini yazmaktır.
    indeks = {(k["metin_hash"], k["source_url"]): k["ozet"] for k in kayitlar}

    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    rapor = {"yedekteki": len(kayitlar), "eslesen": 0, "eslesmeyen": 0,
             "zaten_dolu": 0, "yazilan": 0}
    try:
        yazilacak = []
        for r in conn.execute(
                "SELECT id, raw_text, source_url, ozet FROM campaigns"):
            ozet = indeks.get((_hash(r["raw_text"]), r["source_url"]))
            if ozet is None:
                continue
            rapor["eslesen"] += 1
            if (r["ozet"] or "").strip():
                rapor["zaten_dolu"] += 1
                continue
            yazilacak.append((ozet, r["id"]))
        rapor["eslesmeyen"] = len(kayitlar) - rapor["eslesen"]
        if not kuru and yazilacak:
            conn.executemany("UPDATE campaigns SET ozet=? WHERE id=?", yazilacak)
            conn.commit()
            rapor["yazilan"] = len(yazilacak)
    finally:
        conn.close()
    return rapor


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--db", default="data/demo.db")
    ap.add_argument("--yedek", default="data/ozet-yedegi.json")
    ap.add_argument("--yedekle", action="store_true",
                    help="DB'den yedek AL (geri yükleme yapma)")
    ap.add_argument("--kuru", action="store_true", help="yazmadan dene")
    a = ap.parse_args(argv)

    db, yedek = Path(a.db), Path(a.yedek)
    if not db.exists():
        print(f"HATA: veri tabanı yok: {db}", file=sys.stderr)
        return 1

    if a.yedekle:
        r = yedekle(db, yedek)
        print(f"yedeklenen özet : {r['yedeklenen']}")
        print(f"tekil metin_hash: {r['tekil_hash']}")
        print(f"dosya           : {r['dosya']}")
        return 0

    if not yedek.exists():
        print(f"HATA: yedek yok: {yedek}", file=sys.stderr)
        return 1

    r = geri_yukle(db, yedek, kuru=a.kuru)
    print(f"yedekteki özet  : {r['yedekteki']}")
    print(f"eşleşen         : {r['eslesen']}")
    print(f"eşleşmeyen      : {r['eslesmeyen']}"
          + ("   <- özet UYDURULMAZ, kayıp raporlanır" if r["eslesmeyen"] else ""))
    print(f"zaten dolu      : {r['zaten_dolu']}")
    print(f"yazılan         : {r['yazilan']}" + ("  (kuru koşu)" if a.kuru else ""))
    if r["eslesen"] == 0 and r["yedekteki"] > 0:
        print("UYARI: hiçbir kayıt eşleşmedi — yedek bu DB'ye ait olmayabilir.",
              file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
