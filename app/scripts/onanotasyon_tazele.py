"""İnceleme CSV'sindeki ön-anotasyonu BUGÜNKÜ çıkarıcıyla tazeler.

İlgili: scripts/to_review_csv.py (CSV üreteci — sütun anlamları oradan)
        scripts/xlsx_to_review_csv.py, scripts/kalibrasyon_hakemlik.py
        data/gold/review/_kalibrasyon-sonucu.md (bayatlığın ölçümü)

## Neden gerekli

Kalibrasyon turunda ölçüldü: CSV'lerdeki `model_value` üretildiği günün
çıkarıcısına ait ve çıkarıcı O GÜNDEN BERİ DÜZELDİ. Somut örnek —
`albaraka--detay-vade-farksiz-kampanyasi · kampanya_suresi`: CSV
`2026-01-01` (başlangıç) diyor, bugünkü kural `2026-12-31` (bitiş) veriyor.
Dört anotatör de bu satırı düzeltti; dördü de **zaten düzeltilmiş** bir hatayı
düzeltti.

Ölçülen bayatlık (`campaign_type` hariç — onu kural çıkarıcısı üretmiyor):

    round0 kalibrasyon   16/260  %6
    round1_A             22/600  %3,7
    round1_main_C        47/483  %9,7
    round1_main_D        39/482  %8,1
    round2_zor_vaka      29/492  %5,9

İki maliyeti var. Birincisi boşa emek. İkincisi daha sinsi: anotatör satırı
`ok` bırakırsa gold'a **anotatörün hiç görmediği** güncel değer girer
(`build_gold` model değerini güncel ön-anotasyondan okur).

## Satır kümesine DOKUNULMAZ

CSV'ler `belge × 13 alan` yapısındadır (12 çıkarım alanı + `campaign_type`);
satır kümesi modelin ne ürettiğine DEĞİL bu yapıya bağlıdır. Bu araç yalnız
`model_value`, `model_conf`, `confidence_source`, `snippet` sütunlarını
günceller. Fleiss κ dört dosyanın birebir aynı satır kümesini şart koşuyor
(`_atama.md`) ve `to_review_csv`'yi yeniden koşmak sırayı değiştirebilirdi.

## `campaign_type`'a DOKUNULMAZ

O alanı kural çıkarıcısı değil sınıflandırıcı üretiyor
(`confidence_source=classifier`). `extract_all` ile tazelemek onu sessizce
siler.

## Anote edilmiş dosyayı REDDEDER

`--zorla` verilmedikçe içinde karar olan dosyaya dokunmaz: anotatör gördüğü
değere karar verdi, altından değeri değiştirmek o kararı anlamsız kılar.

## Kullanım

    .venv/bin/python -m scripts.onanotasyon_tazele --kuru \\
        data/gold/review/round1_A.csv

    .venv/bin/python -m scripts.onanotasyon_tazele \\
        --degisim-raporu data/gold/review/_tazeleme.md \\
        data/gold/review/round1_A.csv data/gold/review/round1_B.csv

Çıkış kodu: 0 tazelendi · 1 dosya/metin yok · 2 dosyada karar var (`--zorla`).
"""

from __future__ import annotations

import argparse
import csv
import shutil
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from scripts.gold_schema import format_gold_value
from scripts.to_review_csv import (
    CSV_DELIMITER,
    CSV_ENCODING,
    CSV_LINETERMINATOR,
)
from src.extraction.rules.extract import extract_all

#: Belge metinlerinin bulunduğu dizin.
BELGE_DIZINI = _ROOT / "data" / "gold" / "review" / "belgeler"

#: Kural çıkarıcısının ÜRETMEDİĞİ alanlar — tazelemede atlanır.
ATLANAN_ALANLAR = frozenset({"campaign_type"})

#: Bu araçla güncellenen sütunlar. `gold_value`/`verdict`/`note` ASLA.
MODEL_SUTUNLARI = ("model_value", "model_conf", "confidence_source", "snippet")


def _oku(yol: Path) -> tuple[list[str], list[dict]]:
    with yol.open(encoding=CSV_ENCODING, newline="") as fh:
        r = csv.DictReader(fh, delimiter=CSV_DELIMITER)
        baslik = [(h or "").lstrip("﻿") for h in (r.fieldnames or [])]
        satirlar = [{(k or "").lstrip("﻿"): (v or "") for k, v in s.items()}
                    for s in r]
    return baslik, satirlar


def _kararli(satirlar: list[dict]) -> int:
    return sum(1 for s in satirlar
               if (s.get("verdict") or "").strip()
               or (s.get("gold_value") or "").strip())


def _yedekle(yol: Path) -> Path:
    hedef = yol.with_suffix(yol.suffix + ".yedek-tazeleme")
    n = 2
    while hedef.exists():
        hedef = yol.with_suffix(f"{yol.suffix}.yedek-tazeleme{n}")
        n += 1
    shutil.copy2(yol, hedef)
    return hedef


def tazele(yol: Path, belge_dizini: Path = BELGE_DIZINI,
           kuru: bool = False, zorla: bool = False) -> dict:
    """Bir CSV'nin model sütunlarını günceller; değişimleri kaydeder."""
    baslik, satirlar = _oku(yol)
    kararli = _kararli(satirlar)
    rapor = {
        "dosya": str(yol), "satir": len(satirlar), "kararli": kararli,
        "degisimler": [], "metni_yok": [], "atlanan": 0, "yedek": None,
        "reddedildi": False,
    }
    if kararli and not zorla:
        rapor["reddedildi"] = True
        return rapor

    # Belge başına bir kez çıkarım: 90 belgede alan başına koşmak 12 kat pahalı.
    guncel: dict[str, dict] = {}
    for doc in sorted({s.get("doc_id", "") for s in satirlar}):
        p = belge_dizini / f"{doc}.txt"
        if not p.exists():
            rapor["metni_yok"].append(doc)
            continue
        guncel[doc] = {f.field_name: f
                       for f in extract_all(p.read_text(encoding="utf-8"))}

    for s in satirlar:
        alan = (s.get("field") or "").strip()
        doc = (s.get("doc_id") or "").strip()
        if alan in ATLANAN_ALANLAR:
            rapor["atlanan"] += 1
            continue
        if doc not in guncel:
            continue

        f = guncel[doc].get(alan)
        if f is None:
            yeni = {"model_value": "", "model_conf": "",
                    "confidence_source": "", "snippet": s.get("snippet", "")}
        else:
            conf = getattr(f, "confidence", None)
            yeni = {
                "model_value": format_gold_value(alan, f.canonical_value),
                "model_conf": f"{float(conf):.2f}" if conf is not None else "",
                "confidence_source": getattr(f, "confidence_source", "") or "",
                "snippet": s.get("snippet", ""),
            }

        eski_deger = (s.get("model_value") or "").strip()
        if eski_deger == yeni["model_value"]:
            continue
        rapor["degisimler"].append({
            "dosya": yol.name, "doc_id": doc, "field": alan,
            "eski": eski_deger or "(boş)",
            "yeni": yeni["model_value"] or "(boş)",
        })
        for sutun in MODEL_SUTUNLARI:
            if sutun in s:
                s[sutun] = yeni[sutun]

    if not kuru and rapor["degisimler"]:
        rapor["yedek"] = str(_yedekle(yol))
        with yol.open("w", encoding=CSV_ENCODING, newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=baslik, delimiter=CSV_DELIMITER,
                               lineterminator=CSV_LINETERMINATOR)
            w.writeheader()
            w.writerows(satirlar)
    return rapor


def rapor_yaz(raporlar: list[dict]) -> str:
    s = ["# Ön-anotasyon Tazeleme — Değişim Kaydı", "",
         "> `scripts/onanotasyon_tazele.py` üretti. Model sütunları bugünkü",
         "> çıkarıcıya göre güncellendi; satır kümesi ve anotatör sütunları",
         "> DEĞİŞMEDİ. Geri alma: `*.yedek-tazeleme`.", "",
         "| Dosya | satır | tazelenen | metni bulunamayan belge |",
         "|---|---:|---:|---:|"]
    for r in raporlar:
        s.append(f"| `{Path(r['dosya']).name}` | {r['satir']} | "
                 f"{len(r['degisimler'])} | {len(r['metni_yok'])} |")
    s += ["", "## Değişen hücreler", "",
          "| Dosya | Belge | Alan | eski -> yeni |", "|---|---|---|---|"]
    for r in raporlar:
        for d in r["degisimler"]:
            s.append(f"| `{d['dosya']}` | `{d['doc_id']}` | `{d['field']}` | "
                     f"`{d['eski']}` -> `{d['yeni']}` |")
    return "\n".join(s) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("csv", nargs="+")
    ap.add_argument("--belgeler", default=str(BELGE_DIZINI))
    ap.add_argument("--kuru", action="store_true", help="yazmadan dene")
    ap.add_argument("--zorla", action="store_true",
                    help="içinde karar olan dosyayı da tazele (DİKKAT)")
    ap.add_argument("--degisim-raporu", default=None)
    a = ap.parse_args(argv)

    raporlar, kod = [], 0
    for ham in a.csv:
        yol = Path(ham)
        if not yol.exists():
            print(f"HATA: dosya yok: {yol}", file=sys.stderr)
            return 1
        r = tazele(yol, Path(a.belgeler), kuru=a.kuru, zorla=a.zorla)
        raporlar.append(r)
        if r["reddedildi"]:
            print(f"  {yol.name:<24}REDDEDİLDİ — {r['kararli']} satırda karar "
                  "var. Tazelemek o kararları anlamsız kılar (--zorla).",
                  file=sys.stderr)
            kod = 2
            continue
        print(f"  {yol.name:<24}satır {r['satir']:>4} · "
              f"tazelenen {len(r['degisimler']):>4} · "
              f"atlanan(campaign_type) {r['atlanan']:>3}"
              + (f" · metni yok {len(r['metni_yok'])}" if r["metni_yok"] else ""))

    if a.degisim_raporu and not a.kuru:
        Path(a.degisim_raporu).write_text(rapor_yaz(raporlar), encoding="utf-8")
        print(f"değişim kaydı: {a.degisim_raporu}")
    if a.kuru:
        print("(kuru koşu — dosyalar YAZILMADI)")
    return kod


if __name__ == "__main__":
    raise SystemExit(main())
