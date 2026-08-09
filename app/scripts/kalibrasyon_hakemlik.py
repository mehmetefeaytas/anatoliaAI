"""Kalibrasyon CSV'lerine kılavuz kaynaklı hakemlik kurallarını uygular.

İlgili: data/gold/ANNOTATION_GUIDE.md §3.1, §3.3 (kuralların kaynağı)
        data/gold/review/_kalibrasyon-sonucu.md (neden gerekti — ölçüm)
        scripts/report_iaa.py (κ'yı okuyan taraf)
        scripts/lint_review_csv.py (uygulamadan sonra koşulacak kapı)

## Bu araç anotatör kararını DEĞİŞTİRİR

Bu yüzden üç şey zorunlu ve hiçbiri seçenek değil:

1. **Kurallar önceden ilan edilir** ve kılavuzdan türer — koşu anında
   uydurulmaz. Aşağıdaki `KURALLAR` sözlüğü tek kaynaktır.
2. **Her değişen hücre kayda geçer** (`--degisim-raporu`): dosya, `doc_id`,
   alan, sütun, eski değer, yeni değer, hangi kural. Sayı değil, satır satır.
3. **Yazmadan önce yedek** alınır. CLAUDE.md "silme yok".

## Kurallar

### `bos-ok` — boş karar, boş değer -> `ok`

v1 protokolünde boş hücre zaten `ok` OKUNUYOR (`report_iaa.row_verdict`), bu
kural onu diske YAZAR. Tek etkisi v2'ye taşındığında kararın korunmasıdır;
κ'ya katkısı yoktur.

**Dolu `gold_value` olan satıra DOKUNMAZ.** Boş `verdict` + dolu `gold_value`
her iki protokolde de `fix` demektir: anotatör düzeltmeyi yazıp karar sütununu
atlamıştır. Ona `ok` yazmak, ölçülmüş bir düzeltmeyi onaya çevirirdi — B'de
39 satır böyledir ve ikisi arasındaki fark gerçek (ör. `kampanya_suresi`
model `2026-01-01`, anotatör `01.01.2026 - 31.12.2026`).

### `absent-ok` — model bir şey ÜRETMEDİYSE `absent` -> `ok`

`ANNOTATION_GUIDE.md` §3.1 tablosu: `model_value` boşken doğru karar `ok`'tur
("kontrol ettim, bu alan belgede yok") ve gold'a `absent_fields` girer.
`absent` ise §3.3'e göre **modelin ÜRETTİĞİ bir değeri reddetmek** içindir ve
halüsinasyon (FP) olarak ölçülür.

Model hiçbir şey üretmediğinde `absent` yazmak, olmayan bir halüsinasyonu
işaretlemektir. İki etiket aynı gold değerini ürettiği için sonuç değişmez ama
κ çöker: dört anotatör aynı şeyi söyleyip farklı kelime kullanır.

**`model_value` DOLU olan `absent`'e dokunmaz** — o meşru bir halüsinasyon
iddiasıdır ve projenin ölçtüğü en değerli sinyaldir (dört dosyada 37 satır).

## Kullanım

    .venv/bin/python -m scripts.kalibrasyon_hakemlik --kuru \\
        data/gold/review/round0_kalibrasyon_[ABCD].csv

    .venv/bin/python -m scripts.kalibrasyon_hakemlik \\
        --degisim-raporu data/gold/review/_hakemlik-degisim.md \\
        data/gold/review/round0_kalibrasyon_[ABCD].csv

Çıkış kodu: 0 uygulandı · 1 dosya okunamadı.
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

from scripts.to_review_csv import (
    CSV_DELIMITER,
    CSV_ENCODING,
    CSV_LINETERMINATOR,
)

#: Kural adı -> (açıklama, koşul). Koşul `(verdict, gold_value, model_value)`
#: üçlüsünü alır ve satırın `ok`'a çevrilip çevrilmeyeceğini söyler.
#: Değerler ÇAĞRIDAN ÖNCE kırpılmış ve `casefold` edilmiş `verdict` ile gelir.
KURALLAR = {
    "bos-ok": (
        "boş karar + boş değer -> ok (v1'de zaten öyle okunuyordu)",
        lambda verdict, gold, model: not verdict and not gold,
    ),
    "absent-ok": (
        "model bir şey üretmediyse absent -> ok (kılavuz §3.1/§3.3)",
        lambda verdict, gold, model: verdict == "absent" and not model,
    ),
}

VARSAYILAN_KURALLAR = tuple(KURALLAR)


def _oku(yol: Path) -> tuple[list[str], list[dict]]:
    with yol.open(encoding=CSV_ENCODING, newline="") as fh:
        r = csv.DictReader(fh, delimiter=CSV_DELIMITER)
        baslik = [(h or "").lstrip("﻿") for h in (r.fieldnames or [])]
        satirlar = [{(k or "").lstrip("﻿"): (v or "") for k, v in s.items()}
                    for s in r]
    return baslik, satirlar


def _yedekle(yol: Path) -> Path:
    hedef = yol.with_suffix(yol.suffix + ".yedek-hakemlik")
    n = 2
    while hedef.exists():
        hedef = yol.with_suffix(f"{yol.suffix}.yedek-hakemlik{n}")
        n += 1
    shutil.copy2(yol, hedef)
    return hedef


def uygula(yol: Path, kurallar: tuple[str, ...] = VARSAYILAN_KURALLAR,
           kuru: bool = False) -> dict:
    """Kuralları bir dosyaya uygular; değişen her hücreyi kaydeder."""
    bilinmeyen = [k for k in kurallar if k not in KURALLAR]
    if bilinmeyen:
        raise ValueError(f"bilinmeyen kural: {', '.join(bilinmeyen)}")

    baslik, satirlar = _oku(yol)
    degisimler: list[dict] = []
    korunan = {"dolu_gold_value": 0, "mesru_absent": 0}

    for s in satirlar:
        verdict = (s.get("verdict") or "").strip().casefold()
        gold = (s.get("gold_value") or "").strip()
        model = (s.get("model_value") or "").strip()

        # Korunanları önce say: raporda "dokunmadım"ın da sayısı olmalı.
        if not verdict and gold:
            korunan["dolu_gold_value"] += 1
        if verdict == "absent" and model:
            korunan["mesru_absent"] += 1

        for ad in kurallar:
            _, kosul = KURALLAR[ad]
            if not kosul(verdict, gold, model):
                continue
            eski = (s.get("verdict") or "").strip()
            if eski.casefold() == "ok":
                continue
            degisimler.append({
                "dosya": yol.name,
                "doc_id": s.get("doc_id", ""),
                "field": s.get("field", ""),
                "sutun": "verdict",
                "eski": eski,
                "yeni": "ok",
                "kural": ad,
            })
            s["verdict"] = "ok"
            break

    yedek = None
    if not kuru and degisimler:
        yedek = str(_yedekle(yol))
        with yol.open("w", encoding=CSV_ENCODING, newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=baslik, delimiter=CSV_DELIMITER,
                               lineterminator=CSV_LINETERMINATOR)
            w.writeheader()
            w.writerows(satirlar)

    return {
        "dosya": str(yol),
        "satir": len(satirlar),
        "degisimler": degisimler,
        "korunan": korunan,
        "yedek": yedek,
    }


def rapor_yaz(raporlar: list[dict], kurallar: tuple[str, ...]) -> str:
    """Değişim kaydını markdown olarak üretir (satır satır, sayı değil)."""
    satirlar = [
        "# Kalibrasyon Hakemlik — Değişim Kaydı",
        "",
        "> `scripts/kalibrasyon_hakemlik.py` üretti. Her değişen hücre burada.",
        "> Geri almak için `.yedek-hakemlik` kopyaları duruyor (silme yok).",
        "",
        "## Uygulanan kurallar",
        "",
    ]
    for ad in kurallar:
        satirlar.append(f"- **`{ad}`** — {KURALLAR[ad][0]}")
    satirlar += ["", "## Özet", "",
                 "| Dosya | satır | değişen | korunan: dolu gold_value | "
                 "korunan: meşru absent |", "|---|---:|---:|---:|---:|"]
    for r in raporlar:
        satirlar.append(
            f"| `{Path(r['dosya']).name}` | {r['satir']} | "
            f"{len(r['degisimler'])} | {r['korunan']['dolu_gold_value']} | "
            f"{r['korunan']['mesru_absent']} |")

    satirlar += ["", "## Değişen hücreler", ""]
    for ad in kurallar:
        ilgili = [d for r in raporlar for d in r["degisimler"] if d["kural"] == ad]
        satirlar += [f"### `{ad}` ({len(ilgili)} hücre)", ""]
        if not ilgili:
            satirlar += ["_yok_", ""]
            continue
        satirlar += ["| Dosya | Belge | Alan | eski -> yeni |", "|---|---|---|---|"]
        for d in ilgili:
            eski = d["eski"] or "(boş)"
            satirlar.append(
                f"| `{d['dosya']}` | `{d['doc_id']}` | `{d['field']}` | "
                f"`{eski}` -> `{d['yeni']}` |")
        satirlar.append("")
    return "\n".join(satirlar) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("csv", nargs="+", help="inceleme CSV'leri")
    ap.add_argument("--kural", action="append", choices=list(KURALLAR),
                    help="uygulanacak kural (yinelenebilir; öntanım: hepsi)")
    ap.add_argument("--kuru", action="store_true", help="yazmadan dene")
    ap.add_argument("--degisim-raporu", default=None,
                    help="değişim kaydının yazılacağı markdown dosyası")
    a = ap.parse_args(argv)

    kurallar = tuple(a.kural) if a.kural else VARSAYILAN_KURALLAR
    raporlar = []
    for ham in a.csv:
        yol = Path(ham)
        if not yol.exists():
            print(f"HATA: dosya yok: {yol}", file=sys.stderr)
            return 1
        raporlar.append(uygula(yol, kurallar, kuru=a.kuru))

    for r in raporlar:
        print(f"  {Path(r['dosya']).name:<34}"
              f"değişen {len(r['degisimler']):>4} · "
              f"korunan(dolu gold) {r['korunan']['dolu_gold_value']:>3} · "
              f"korunan(meşru absent) {r['korunan']['mesru_absent']:>3}")
    toplam = sum(len(r["degisimler"]) for r in raporlar)
    print(f"\ntoplam değişen hücre: {toplam}")

    if a.degisim_raporu and not a.kuru:
        Path(a.degisim_raporu).write_text(rapor_yaz(raporlar, kurallar),
                                          encoding="utf-8")
        print(f"değişim kaydı: {a.degisim_raporu}")
    if a.kuru:
        print("(kuru koşu — dosyalar YAZILMADI)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
