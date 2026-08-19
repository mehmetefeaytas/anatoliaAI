"""Alan alt kümesi üzerinde mikro/makro F1 — yayımlanan kesit iddialarının kanıtı.

## Neden bu dosya var

`run_eval` iki kesit yayımlıyor: 12 alanın tamamı ve `kampanya_kosullari`
hariç "yapısal" kesit. Ama karşılaştırma raporlarında başka kesitler de
geçiyor — örneğin harici bir korpusla ORTAK olan 5 alan
(`docs/rapor/capraz-degerlendirme.md`). O sayıyı elle hesaplamak, kanıtı
olmayan bir iddia bırakır; bu araç kesiti `per_field.csv`'den yeniden üretir.

Girdi olarak bir koşum dizini alır, yani yeni bir çıkarım koşmaz: aynı
raporun içindeki sayıları toplar. Böylece kesit ile manşet sayı **aynı
koşumdan** gelir ve ikisi ayrışamaz.

## Kullanım

    python -m eval.alan_kesiti eval/reports/20260819-115438
    python -m eval.alan_kesiti eval/reports/20260819-115438 --kesit ortak5
    python -m eval.alan_kesiti <dizin> --alanlar vade_ay,taksit_sayisi

Destek (`tp + fn`) sıfır olan alan makro ortalamaya GİRMEZ: F1'i tanımsızdır
ve 0,0 saymak "motor bu alanda başarısız" gibi yanlış bir izlenim yaratır
(aynı gerekçe `eval/esikler.json` `_esigi_olmayan_alanlar` notunda).
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

# Adlandırılmış kesitler. Yeni bir karşılaştırma raporu yazıldığında kesit
# BURAYA eklenir; raporun içine gömülü elle hesap bırakılmaz.
KESITLER: dict[str, tuple[str, ...]] = {
    # Harici karşılaştırma korpusuyla ortak olan alanlar
    # (bkz. docs/rapor/capraz-degerlendirme.md).
    "ortak5": (
        "kar_payi_orani",
        "vade_ay",
        "odul_miktari",
        "finansman_tutari",
        "taksit_sayisi",
    ),
    # Serbest metin alanı hariç — `run_eval`'in "yapısal" kesitiyle aynı küme.
    "yapisal": (
        "kar_payi_orani",
        "finansman_tutari",
        "vade_ay",
        "taksit_sayisi",
        "tahsis_ucreti",
        "masraf_durumu",
        "odul_miktari",
        "indirim_orani",
        "alisveris_puani",
        "kampanya_suresi",
        "hedef_kitle",
    ),
}


def _prf(tp: int, fp: int, fn: int) -> tuple[float, float, float]:
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    f = 2 * p * r / (p + r) if p + r else 0.0
    return p, r, f


def kesit_oku(rapor_dizini: Path, alanlar: tuple[str, ...],
              matcher: str = "strict", scope: str = "all") -> dict:
    """`per_field.csv`'den bir alan alt kümesini toplar."""
    yol = rapor_dizini / "per_field.csv"
    if not yol.exists():
        raise SystemExit(f"per_field.csv bulunamadı: {yol}")

    satirlar = []
    with open(yol, encoding="utf-8") as fh:
        for row in csv.DictReader(fh, delimiter=";"):
            if row["matcher"] != matcher or row["scope"] != scope:
                continue
            if row["field"] not in alanlar:
                continue
            satirlar.append(row)

    bulunan = {r["field"] for r in satirlar}
    eksik = [a for a in alanlar if a not in bulunan]

    tp = fp = fn = 0
    f1ler: list[float] = []
    per_alan = []
    for r in satirlar:
        a_tp, a_fp, a_fn = int(r["tp"]), int(r["fp"]), int(r["fn"])
        tp += a_tp
        fp += a_fp
        fn += a_fn
        destek = a_tp + a_fn
        _, _, a_f1 = _prf(a_tp, a_fp, a_fn)
        per_alan.append((r["field"], a_f1, destek))
        # Destek yoksa makro ortalamaya girmez (bkz. modül başlığı).
        if destek:
            f1ler.append(a_f1)

    p, r_, f = _prf(tp, fp, fn)
    return {
        "alanlar": per_alan,
        "eksik": eksik,
        "mikro_precision": p,
        "mikro_recall": r_,
        "mikro_f1": f,
        "makro_f1": sum(f1ler) / len(f1ler) if f1ler else 0.0,
        "makro_paydasi": len(f1ler),
        "tp": tp,
        "fp": fp,
        "fn": fn,
    }


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Alan alt kümesi üzerinde mikro/makro F1")
    ap.add_argument("rapor", help="eval koşum dizini (per_field.csv içeren)")
    ap.add_argument("--kesit", choices=sorted(KESITLER), default="ortak5",
                    help="adlandırılmış kesit (öntanımlı: ortak5)")
    ap.add_argument("--alanlar", help="virgülle ayrık alan listesi; --kesit'i ezer")
    ap.add_argument("--matcher", default="strict", choices=["strict", "tolerant"])
    ap.add_argument("--scope", default="all", choices=["all", "hard", "easy"])
    a = ap.parse_args()

    if a.alanlar:
        alanlar = tuple(x.strip() for x in a.alanlar.split(",") if x.strip())
        etiket = "elle"
    else:
        alanlar = KESITLER[a.kesit]
        etiket = a.kesit

    s = kesit_oku(Path(a.rapor), alanlar, a.matcher, a.scope)

    print(f"Kesit `{etiket}` · {len(alanlar)} alan · "
          f"matcher={a.matcher} scope={a.scope}")
    print(f"Kaynak: {a.rapor}/per_field.csv")
    print()
    print(f"{'alan':<20}{'F1':>8}{'destek':>8}")
    print("-" * 36)
    for ad, f1, destek in s["alanlar"]:
        isaret = "" if destek else "   <- destek 0, makroya girmedi"
        print(f"{ad:<20}{f1:>8.3f}{destek:>8}{isaret}")
    print("-" * 36)
    print(f"{'MİKRO':<20}{s['mikro_f1']:>8.3f}"
          f"   (P {s['mikro_precision']:.3f} / R {s['mikro_recall']:.3f} · "
          f"TP {s['tp']} / FP {s['fp']} / FN {s['fn']})")
    print(f"{'MAKRO':<20}{s['makro_f1']:>8.3f}"
          f"   ({s['makro_paydasi']} alan üzerinden)")

    if s["eksik"]:
        print()
        print("UYARI — raporda bulunmayan alanlar: " + ", ".join(s["eksik"]))
        print("Kesit tanımı ile koşumun alan kümesi ayrışmış olabilir.")
        sys.exit(1)


if __name__ == "__main__":
    main()
