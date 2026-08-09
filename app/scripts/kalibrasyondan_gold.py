"""Kalibrasyondan gold'a NE girer — (b) seçeneğinin ÖLÇÜMÜ.

İlgili: scripts/report_iaa.py (κ çekirdeği — DEĞİŞTİRİLMEZ)
        scripts/build_gold.py (derleyici — DEĞİŞTİRİLMEZ)
        scripts/protokol_yukselt.py (v1 -> v2 taşıma)
        data/gold/review/_kalibrasyon-sonucu.md §6

## Soru

(b) seçeneği: gold yalnız **insanın gerçekten karar verdiği** satırlardan
oluşsun. Bu betik karar VERMEZ, yalnız o alt kümenin boyunu ve κ'sını ölçer.

## Neden `.yedek-hakemlik` okunuyor

Güncel `round0_kalibrasyon_*.csv` dosyalarında `verdict` hücresinin dolu olması
"insan karar verdi" DEMEK DEĞİLDİR: `kalibrasyon_hakemlik.py` `bos-ok` kuralıyla
boş hücrelere `ok` YAZDI (A'da 199, B'de 136, C'de 3, D'de 134 hücre —
`_kalibrasyon-sonucu.md` §8). O dosyada "dolu verdict" sayarsak insan kararını
betiğin yazdığıyla karıştırırız ve (b) seçeneği anlamsızlaşır.

`.yedek-hakemlik` kopyaları hakemlik ÖNCESİ durumdur ve insan kararını taşır;
sayıları `_kalibrasyon-sonucu.md` §6 tablosuyla birebir uyuşur (A 79, B 89,
C 260, D 260). Ölçüm oradan yapılır, karşılaştırma için güncel dosya da
raporlanır.

Kullanım:
    python3 -m scripts.kalibrasyondan_gold
    python3 -m scripts.kalibrasyondan_gold --esik 3     # en az 3 anotatör
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Optional

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from eval.iaa import fleiss_kappa_from_labels, krippendorff_alpha
from scripts.build_gold import read_review_csv
from scripts.report_iaa import row_value_token, row_verdict

ANOTATORLER = "ABCD"
_TABAN = "data/gold/review/round0_kalibrasyon_"
INSAN_SONEK = ".csv.yedek-hakemlik"
GUNCEL_SONEK = ".csv"


def yollar(sonek: str) -> dict[str, Path]:
    return {a: _ROOT / (_TABAN + a + sonek) for a in ANOTATORLER}


def yukle(sonek: str) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {}
    for a, p in yollar(sonek).items():
        if p.exists():
            out[a] = read_review_csv(str(p))
    return out


def acik_karar(row: dict) -> bool:
    """İnsanın AÇIK kararı var mı — `verdict` hücresi elle doldurulmuş mu.

    Dolu `gold_value` + boş `verdict` de açık karardır: anotatör düzeltmeyi
    yazmış, karar sütununu atlamıştır (`build_gold` bunu `fix` sayar). O
    düzeltmeyi "karar verilmedi" saymak, elle girilmiş en değerli veriyi
    ölçümden düşürmek olurdu.
    """
    return bool((row.get("verdict") or "").strip()
                or (row.get("gold_value") or "").strip())


def hizala(dosyalar: dict[str, list[dict]]) -> dict[tuple[str, str], dict[str, dict]]:
    tablo: dict[tuple[str, str], dict[str, dict]] = defaultdict(dict)
    for a, rows in dosyalar.items():
        for r in rows:
            anahtar = ((r.get("doc_id") or "").strip(), (r.get("field") or "").strip())
            tablo[anahtar][a] = r
    return tablo


def olc(sonek: str, esik: int, etiket: str) -> dict:
    dosyalar = yukle(sonek)
    tablo = hizala(dosyalar)
    anahtarlar = sorted(tablo)

    sayim = {k: sum(1 for r in tablo[k].values() if acik_karar(r)) for k in anahtarlar}
    dagilim = Counter(sayim.values())
    alt_kume = [k for k in anahtarlar if sayim[k] >= esik]

    # κ: yalnız alt küme, yalnız AÇIK karar veren anotatörlerin etiketiyle.
    verdict_birim, deger_birim = [], []
    for k in alt_kume:
        v_row, d_row = [], []
        for a in ANOTATORLER:
            r = tablo[k].get(a)
            if r is None or not acik_karar(r):
                v_row.append(None)
                d_row.append(None)
            else:
                v_row.append(row_verdict(r))
                d_row.append(row_value_token(r))
        verdict_birim.append(v_row)
        deger_birim.append(d_row)

    return {
        "etiket": etiket,
        "sonek": sonek,
        "dosya": sorted(dosyalar),
        "ortak_satir": len(anahtarlar),
        "acik_karar_per_anotator": {a: sum(1 for r in rows if acik_karar(r))
                                    for a, rows in sorted(dosyalar.items())},
        "dagilim": dict(sorted(dagilim.items())),
        "esik": esik,
        "alt_kume": len(alt_kume),
        "belge": len({k[0] for k in alt_kume}),
        "alan": len({k[1] for k in alt_kume}),
        "alan_dagilimi": dict(Counter(k[1] for k in alt_kume).most_common()),
        "kappa": (fleiss_kappa_from_labels(verdict_birim) if verdict_birim
                  else float("nan")),
        "alpha_nominal": (krippendorff_alpha(deger_birim, "nominal") if deger_birim
                          else float("nan")),
    }


def olc_melez(esik: int) -> dict:
    """MASKE insan kararından, ETİKET hakemlik sonrası dosyadan.

    (b) için karar-ilgili sayı budur: "yalnız insanın baktığı satırları al, ama
    iki kılavuz kuralı (`bos-ok`, `absent-ok`) uygulanmış etiketlerle ölç."
    Ham insan κ'sı bu iki kuralı içermez ve `absent` yanlış kullanımının
    cezasını taşır; güncel dosya ise insanın BAKMADIĞI satırları da içerir.
    Melez ölçüm ikisinin de kusurunu dışarıda bırakır.
    """
    insan = hizala(yukle(INSAN_SONEK))
    guncel = hizala(yukle(GUNCEL_SONEK))

    verdict_birim, deger_birim, alt_kume = [], [], []
    for k in sorted(insan):
        bakan = [a for a in ANOTATORLER
                 if (r := insan[k].get(a)) is not None and acik_karar(r)]
        if len(bakan) < esik:
            continue
        alt_kume.append(k)
        v_row, d_row = [], []
        for a in ANOTATORLER:
            r = guncel.get(k, {}).get(a)
            if a not in bakan or r is None:
                v_row.append(None)
                d_row.append(None)
            else:
                v_row.append(row_verdict(r))
                d_row.append(row_value_token(r))
        verdict_birim.append(v_row)
        deger_birim.append(d_row)

    return {
        "etiket": f"MELEZ — insan maskesi (>={esik}) + hakemlik sonrası etiket",
        "sonek": f"{INSAN_SONEK} (maske) + {GUNCEL_SONEK} (etiket)",
        "esik": esik,
        "alt_kume": len(alt_kume),
        "belge": len({k[0] for k in alt_kume}),
        "alan": len({k[1] for k in alt_kume}),
        "alan_dagilimi": dict(Counter(k[1] for k in alt_kume).most_common()),
        "ortak_satir": len(insan),
        "acik_karar_per_anotator": {},
        "dagilim": {},
        "kappa": (fleiss_kappa_from_labels(verdict_birim) if verdict_birim
                  else float("nan")),
        "alpha_nominal": (krippendorff_alpha(deger_birim, "nominal") if deger_birim
                          else float("nan")),
    }


def _f(x: float) -> str:
    return "ölçülemedi" if x != x else f"{x:.3f}"


def yaz(sonuc: dict) -> None:
    print(f"\n=== {sonuc['etiket']} ===")
    print(f"kaynak sonek      : {sonuc['sonek']}")
    print(f"ortak satır       : {sonuc['ortak_satir']}")
    if sonuc["acik_karar_per_anotator"]:
        print("açık karar (anotatör başına):",
              ", ".join(f"{a}={n}" for a, n in sonuc["acik_karar_per_anotator"].items()))
    if sonuc["dagilim"]:
        print("kaç anotatör karar vermiş -> satır:",
              ", ".join(f"{k}→{v}" for k, v in sonuc["dagilim"].items()))
    print(f"eşik >={sonuc['esik']}         : {sonuc['alt_kume']} satır "
          f"({sonuc['belge']} belge · {sonuc['alan']} alan)")
    print(f"Fleiss κ          : {_f(sonuc['kappa'])}")
    print(f"Krippendorff α    : {_f(sonuc['alpha_nominal'])}")


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="(b) seçeneği: insanın karar verdiği alt kümeyi ÖLÇER "
                    "(karar vermez).")
    parser.add_argument("--esik", type=int, default=2,
                        help="en az kaç anotatörün açık kararı olsun (varsayılan 2)")
    args = parser.parse_args(argv)

    insan = olc(INSAN_SONEK, args.esik,
                "İNSAN KARARI (hakemlik öncesi, .yedek-hakemlik)")
    yaz(insan)
    for esik in (3, 4):
        alt = olc(INSAN_SONEK, esik, "")
        print(f"   eşik >={esik}: {alt['alt_kume']} satır · {alt['belge']} belge · "
              f"kappa={_f(alt['kappa'])}")

    for esik in (2, 3, 4):
        melez = olc_melez(esik)
        yaz(melez)

    guncel = olc(GUNCEL_SONEK, args.esik,
                 "GÜNCEL DOSYA (hakemlik SONRASI — betik yazdı)")
    yaz(guncel)
    print("\nUYARI: Güncel dosyadaki 'dolu verdict' insan kararı DEĞİL: `bos-ok` "
          "kuralı boş hücrelere `ok` yazdı. (b) için üstteki ölçüm geçerlidir.")

    print(f"\n--- alan dağılımı (insan kararı, eşik >={args.esik}) ---")
    for alan, n in insan["alan_dagilimi"].items():
        print(f"  {n:4d}  {alan}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
