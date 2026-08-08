"""κ hazırlık tablosu — hangi dosya ne kadar dolu, κ hangi gruptan çıkar.

İlgili: scripts/report_iaa.py (κ'yı hesaplayan) · scripts/lint_review_csv.py
        (biçim kapısı) · data/gold/review/_atama.md (paket planı)

Kullanım:
    python3 -m scripts.kappa_durum
    python3 -m scripts.kappa_durum 'data/gold/review/round1_*.csv'

## Neden ayrı bir araç

`lint_review_csv` biçimi denetler, `report_iaa` κ'yı hesaplar. İkisi de tek
soruyu cevaplamıyor: **κ ölçmeye daha ne kadar var?** κ için iki koşul birden
gerekir ve ikisi de sessizce bozulabilir:

  1. En az iki dosya AYNI `(doc_id, field)` kümesini taşımalı — ayrık kümelere
     bakan anotatörlerden κ ÇIKMAZ (gold.v2'de tam olarak bu oldu: dört
     anotatör, 48 benzersiz belge, sıfır örtüşme, κ tanımsız).
  2. O ortak satırlarda ikisinin de AÇIK kararı olmalı.

Bu araç ikisini birden gösterir ve "kaç satır kaldı" sorusuna tek sayı verir.

## v1 dosyalarındaki sessiz risk

v1'de boş hücre onaydır. Anotatör bir soruna NOT düşüp `verdict` sütununu
atlarsa, satır "model doğru" sayılır — notun içeriği bunun tersini söylese
bile. Bu satırlar ayrıca sayılır; kapatılmaları anotatörün birkaç dakikasıdır,
kapatılmazlarsa gold'a modelin değeri girer.
"""

from __future__ import annotations

import argparse
import glob
import sys
from collections import defaultdict
from pathlib import Path
from typing import Optional

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from scripts.build_gold import infer_annotator, read_review_csv
from scripts.gold_schema import PROTOCOL_V2, row_protocol

DEFAULT_GLOB = "data/gold/review/round*.csv"

# κ için en az bu kadar ortak KARARLI satır olmalı. Altında kappa oynak olur:
# tek satırlık değişim üçüncü haneyi değil, ikinci haneyi kaydırır.
MIN_ORTAK_KARAR = 30


def _clean(value: Optional[str]) -> str:
    return (value or "").strip()


def _acik_karar(row: dict) -> bool:
    """Anotatörün AÇIK işareti. Protokolden bağımsızdır."""
    return bool(_clean(row.get("verdict")) or _clean(row.get("gold_value")))


def dosya_ozeti(path: str) -> dict:
    rows = read_review_csv(path)
    protokol = row_protocol(rows[0]) if rows else "v1"
    kararli = [r for r in rows if _acik_karar(r)]
    # v1'e özgü risk: not var, karar yok -> sessizce "model doğru".
    not_var_karar_yok = [r for r in rows
                         if _clean(r.get("note")) and not _acik_karar(r)]
    return {
        "path": path,
        "ad": Path(path).name,
        "anotator": infer_annotator(path),
        "protokol": protokol,
        "satir": len(rows),
        "belge": len({_clean(r.get("doc_id")) for r in rows}),
        "kararli": len(kararli),
        "not_var_karar_yok": len(not_var_karar_yok),
        "anahtarlar": {(_clean(r.get("doc_id")), _clean(r.get("field")))
                       for r in rows},
        "kararli_anahtarlar": {(_clean(r.get("doc_id")), _clean(r.get("field")))
                               for r in kararli},
    }


def gruplar(ozetler: list[dict]) -> list[dict]:
    """κ üretebilecek dosya grupları.

    Anahtar **(satır kümesi, protokol)** ikilisidir. Satır kümesi aynı olsa
    bile v1 ve v2 dosyaları aynı κ koşusuna giremez: v1'de bakılmamış satır
    "onay" sayılır ve dört anotatör de dokunmadıysa **tam uyum** üretir — uyum
    olduğundan iyi çıkar (ANNOTATION_GUIDE.md §11).
    """
    by_key: dict[tuple[frozenset, str], list[dict]] = defaultdict(list)
    for ozet in ozetler:
        by_key[(frozenset(ozet["anahtarlar"]), ozet["protokol"])].append(ozet)

    out = []
    for (anahtarlar, _protokol), uyeler in by_key.items():
        ortak_kararli = set(anahtarlar)
        for uye in uyeler:
            ortak_kararli &= uye["kararli_anahtarlar"]
        out.append({
            "uyeler": uyeler,
            "satir": len(anahtarlar),
            "ortak_kararli": len(ortak_kararli) if len(uyeler) >= 2 else 0,
            "kappa_mumkun": len(uyeler) >= 2 and len(ortak_kararli) >= MIN_ORTAK_KARAR,
        })
    return sorted(out, key=lambda g: -g["satir"])


def render(ozetler: list[dict]) -> str:
    satirlar = ["", "DOSYA DURUMU", "-" * 78,
                f"{'dosya':<32}{'prot':<6}{'satır':>7}{'kararlı':>9}"
                f"{'kalan':>8}{'not/kararsız':>14}"]
    for o in ozetler:
        kalan = o["satir"] - o["kararli"]
        satirlar.append(
            f"{o['ad']:<32}{o['protokol']:<6}{o['satir']:>7}{o['kararli']:>9}"
            f"{kalan:>8}{o['not_var_karar_yok']:>14}")

    satirlar += ["", "κ GRUPLARI (aynı satır kümesini paylaşanlar)", "-" * 78]
    for grup in gruplar(ozetler):
        adlar = ", ".join(u["anotator"] for u in grup["uyeler"])
        if len(grup["uyeler"]) < 2:
            satirlar.append(
                f"  [tek]  {adlar:<28} {grup['satir']} satır — κ ÇIKMAZ "
                f"(örtüşen ikinci anotatör yok)")
            continue
        durum = "HAZIR" if grup["kappa_mumkun"] else "beklemede"
        eksik = max(0, MIN_ORTAK_KARAR - grup["ortak_kararli"])
        ek = "" if grup["kappa_mumkun"] else f" — en az {eksik} ortak karar daha"
        satirlar.append(
            f"  [{durum:<9}] {adlar:<28} {grup['satir']} satır · "
            f"ortak kararlı {grup['ortak_kararli']}{ek}")

    riskli = [o for o in ozetler
              if o["protokol"] != PROTOCOL_V2 and o["not_var_karar_yok"]]
    if riskli:
        satirlar += ["", "UYARI — v1 dosyasında not var, karar yok", "-" * 78,
                     "Bu satırlar `verdict` boş olduğu için 'model doğru'",
                     "sayılır; not içeriği tersini söylese bile gold'a modelin",
                     "değeri girer. Kapatılması gerekir."]
        for o in riskli:
            satirlar.append(f"  {o['ad']:<32}{o['not_var_karar_yok']:>5} satır")

    hazir = [g for g in gruplar(ozetler) if g["kappa_mumkun"]]
    satirlar += ["", f"κ ölçülebilir grup: {len(hazir)}", ""]
    if hazir:
        ilk = hazir[0]
        dosyalar = " ".join(u["path"] for u in ilk["uyeler"])
        satirlar.append(f"  .venv/bin/python -m scripts.report_iaa {dosyalar}")
        satirlar.append("")
    return "\n".join(satirlar)


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="κ hazırlık tablosu: hangi dosya ne kadar dolu, κ nereden çıkar.")
    parser.add_argument("desen", nargs="?", default=DEFAULT_GLOB,
                        help=f"CSV glob deseni (varsayılan: {DEFAULT_GLOB})")
    args = parser.parse_args(argv)

    paths = sorted(glob.glob(args.desen))
    if not paths:
        print(f"eşleşen dosya yok: {args.desen}", file=sys.stderr)
        return 1

    print(render([dosya_ozeti(p) for p in paths]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
