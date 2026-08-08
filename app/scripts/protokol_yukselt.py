"""İnceleme CSV'lerini v1 protokolünden v2'ye taşır.

İlgili: data/gold/ANNOTATION_GUIDE.md §3.1, §11 (protokol tanımı)
        scripts/report_iaa.py (`protokol` sütununu okuyan taraf)
        scripts/to_review_csv.py (üreteç)

Kullanım:
    # 1) HİÇ dokunulmamış dosyaya protokol damgası vur (yerinde)
    python3 -m scripts.protokol_yukselt --damgala data/gold/review/round1_A.csv

    # 2) v1'de verilmiş AÇIK kararları aynı satır kümesine sahip v2 dosyasına taşı
    python3 -m scripts.protokol_yukselt --tasi \\
        --kaynak data/gold/review/round0_kalibrasyon_A.csv \\
        --hedef  data/gold/review/round0_kalibrasyon_v2_A.csv

## Neden ayrı bir araç

`to_review_csv.py` yeniden koşulamaz: `has_annotations()` dolu dosyayı korur ve
üstelik yeniden üretim satır SIRASINI değiştirebilir. Fleiss κ için dört
dosyanın satır kümesi birebir aynı kalmak zorundadır. Bu araç satır kümesine
DOKUNMAZ; yalnız `protokol` sütununu ekler ya da açık kararları kopyalar.

## Taşınan ve taşınmayan

Taşınan: `verdict`, `gold_value`, `note` — **hücre doluysa**. Açık bir işaret
her iki protokolde de aynı şeyi söyler ("ok" onaydır, "fix" düzeltmedir), o
yüzden kayıpsız taşınır.

Taşınmayan: **boş hücreler.** v1'de boş = `ok` (onay), v2'de boş = karar
verilmedi. Bu ikisi aynı şey değildir; boşluğu "onay" olarak taşımak, tam
olarak kılavuzun kaldırdığı çapalama artefaktını geri getirirdi
(ANNOTATION_GUIDE §3.1: gold.v1 modele çapalandığında 0,677, kör protokolde
0,536). Kaç boş hücrenin düştüğü rapor edilir — sessiz kayıp yok.

## Silme yok

Her yazma öncesi `<dosya>.yedek-v1` üretilir (varsa üzerine yazılmaz, sıra
numarası eklenir). CLAUDE.md "silme yok" kuralı burada da geçerlidir.
"""

from __future__ import annotations

import argparse
import csv
import shutil
import sys
from pathlib import Path
from typing import Optional

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from scripts.gold_schema import PROTOCOL_COLUMN, PROTOCOL_V2
from scripts.to_review_csv import (
    CSV_DELIMITER,
    CSV_ENCODING,
    CSV_LINETERMINATOR,
)

# v1'de anotatörün elle doldurduğu sütunlar. Yalnız bunlar taşınır; snippet ve
# model çıktısı üreteçten gelir, kopyalanmaz.
KARAR_SUTUNLARI = ("verdict", "gold_value", "note")


def _clean(value: Optional[str]) -> str:
    return (value or "").strip()


def _oku(path: Path) -> tuple[list[str], list[dict]]:
    """Başlık + satırlar. `read_review_csv`'den farkı: başlığı da döndürür."""
    with path.open("r", encoding=CSV_ENCODING, newline="") as handle:
        reader = csv.DictReader(handle, delimiter=CSV_DELIMITER)
        header = list(reader.fieldnames or [])
        rows = list(reader)
    if "doc_id" not in header or "field" not in header:
        raise ValueError(f"{path}: inceleme CSV'si değil (doc_id/field yok)")
    return header, rows


def _yedekle(path: Path) -> Path:
    """`<dosya>.yedek-v1` üretir; varsa numaralandırır. Üzerine YAZMAZ."""
    hedef = path.with_suffix(path.suffix + ".yedek-v1")
    sira = 2
    while hedef.exists():
        hedef = path.with_suffix(f"{path.suffix}.yedek-v1-{sira}")
        sira += 1
    shutil.copy2(path, hedef)
    return hedef


def _yaz(path: Path, header: list[str], rows: list[dict]) -> None:
    with path.open("w", encoding=CSV_ENCODING, newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=header,
                                delimiter=CSV_DELIMITER,
                                lineterminator=CSV_LINETERMINATOR,
                                extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _acik_karar(row: dict) -> bool:
    """Satırda anotatörün AÇIK bir işareti var mı?"""
    return any(_clean(row.get(col)) for col in KARAR_SUTUNLARI)


def _anahtar(row: dict) -> tuple[str, str]:
    return _clean(row.get("doc_id")), _clean(row.get("field"))


# --------------------------------------------------------------------------- #
# Mod 1 — damgalama
# --------------------------------------------------------------------------- #
def damgala(path: Path, *, zorla: bool = False) -> dict:
    """Dokunulmamış dosyaya `protokol=v2` sütunu ekler (yerinde).

    Dolu dosyada varsayılan olarak DURUR: boş hücrelerin anlamı değişeceği için
    yapılmış işin yorumu sessizce kayar. Bilerek yapılıyorsa `--zorla`.
    """
    header, rows = _oku(path)

    if PROTOCOL_COLUMN in header:
        mevcut = {_clean(r.get(PROTOCOL_COLUMN)).casefold() for r in rows}
        return {"dosya": str(path), "durum": "zaten-v2" if mevcut == {PROTOCOL_V2}
                else "protokol-sutunu-var", "satir": len(rows), "yedek": None}

    dolu = sum(1 for r in rows if _acik_karar(r))
    if dolu and not zorla:
        return {"dosya": str(path), "durum": "atlandi-dolu", "satir": len(rows),
                "acik_karar": dolu, "yedek": None}

    yedek = _yedekle(path)
    for row in rows:
        row[PROTOCOL_COLUMN] = PROTOCOL_V2
    _yaz(path, header + [PROTOCOL_COLUMN], rows)
    return {"dosya": str(path), "durum": "damgalandi", "satir": len(rows),
            "acik_karar": dolu, "yedek": str(yedek)}


# --------------------------------------------------------------------------- #
# Mod 2 — taşıma
# --------------------------------------------------------------------------- #
def tasi(kaynak: Path, hedef: Path) -> dict:
    """v1 kaynaktaki AÇIK kararları, aynı satır kümesine sahip v2 hedefe taşır."""
    k_header, k_rows = _oku(kaynak)
    h_header, h_rows = _oku(hedef)

    k_keys = {_anahtar(r) for r in k_rows}
    h_keys = {_anahtar(r) for r in h_rows}
    if k_keys != h_keys:
        raise ValueError(
            f"satır kümeleri farklı — taşıma reddedildi. "
            f"yalnız kaynakta: {len(k_keys - h_keys)}, "
            f"yalnız hedefte: {len(h_keys - k_keys)}. "
            f"Aynı (doc_id, field) kümesi olmadan κ birimleri hizalanmaz.")

    kaynak_karar = {_anahtar(r): r for r in k_rows if _acik_karar(r)}
    # Hedefte zaten iş varsa üzerine yazma — anotatörün yeni kararı kazanır.
    hedefte_dolu = sum(1 for r in h_rows if _acik_karar(r))

    tasinan = 0
    catisma = 0
    for row in h_rows:
        src = kaynak_karar.get(_anahtar(row))
        if src is None:
            continue
        if _acik_karar(row):
            catisma += 1
            continue
        for col in KARAR_SUTUNLARI:
            if col in h_header:
                row[col] = src.get(col, "")
        tasinan += 1

    header = h_header if PROTOCOL_COLUMN in h_header else h_header + [PROTOCOL_COLUMN]
    for row in h_rows:
        row[PROTOCOL_COLUMN] = PROTOCOL_V2

    yedek = _yedekle(hedef)
    _yaz(hedef, header, h_rows)

    return {
        "kaynak": str(kaynak),
        "hedef": str(hedef),
        "satir": len(h_rows),
        "kaynakta_acik_karar": len(kaynak_karar),
        "tasinan": tasinan,
        "catisma": catisma,
        "hedefte_onceden_dolu": hedefte_dolu,
        # v1'de boş = "ok" sayılırdı; v2'de sayılmaz. Kaç karar yerinin
        # yeniden bakılmayı beklediği burada görünür.
        "dusen_ortuk_onay": len(k_rows) - len(kaynak_karar),
        "yedek": str(yedek),
    }


# --------------------------------------------------------------------------- #
def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="İnceleme CSV'lerini v2 protokolüne taşır.")
    mod = parser.add_mutually_exclusive_group(required=True)
    mod.add_argument("--damgala", nargs="+", metavar="CSV",
                     help="dokunulmamış dosyalara protokol=v2 sütunu ekler")
    mod.add_argument("--tasi", action="store_true",
                     help="--kaynak'taki açık kararları --hedef'e taşır")
    parser.add_argument("--kaynak", metavar="CSV")
    parser.add_argument("--hedef", metavar="CSV")
    parser.add_argument("--zorla", action="store_true",
                        help="damgalamada dolu dosyayı da işle (dikkat: boş "
                             "hücrelerin anlamı değişir)")
    args = parser.parse_args(argv)

    if args.damgala:
        for raw in args.damgala:
            sonuc = damgala(Path(raw), zorla=args.zorla)
            print(f"{Path(raw).name:<34} {sonuc['durum']:<18} "
                  f"satir={sonuc['satir']:<5} yedek={sonuc.get('yedek') or '-'}")
            if sonuc["durum"] == "atlandi-dolu":
                print(f"  ! {sonuc['acik_karar']} satırda açık karar var. "
                      f"Boş hücrelerin anlamı değişeceği için durdum; "
                      f"kararları taşımak için `--tasi` kullanın.")
        return 0

    if not (args.kaynak and args.hedef):
        parser.error("--tasi için --kaynak ve --hedef gerekli")

    sonuc = tasi(Path(args.kaynak), Path(args.hedef))
    print(f"kaynak                : {sonuc['kaynak']}")
    print(f"hedef                 : {sonuc['hedef']}")
    print(f"satır                 : {sonuc['satir']}")
    print(f"kaynakta açık karar   : {sonuc['kaynakta_acik_karar']}")
    print(f"taşınan               : {sonuc['tasinan']}")
    if sonuc["catisma"]:
        print(f"çatışma (hedef kazandı): {sonuc['catisma']}")
    print(f"düşen örtük onay      : {sonuc['dusen_ortuk_onay']}  "
          f"(v1'de boş = 'ok' sayılırdı; v2'de yeniden bakılacak)")
    print(f"yedek                 : {sonuc['yedek']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
