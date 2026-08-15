"""Kör hakem kararlarını A/B uyuşmazlıklarına uygular — YALNIZ gold için.

İlgili: scripts/kalibrasyon_hakemlik.py (round0'ın kural tabanlı hakemliği)
        scripts/report_iaa.py (κ — hakemlikten ETKİLENMEMELİ)
        data/gold/review/_kalibrasyon-sonucu.md §8 (emsal: öncesi/sonrası ayrı)

## ⛔ κ üzerindeki etkisi — okunmadan koşulmaz

Cohen κ **bağımsız iki yargının** örtüşmesini ölçer. Bu betik uyuşmazlıkları
uzlaştırır, yani uyumu yapay olarak yükseltir. Hakemlik sonrası hesaplanan κ
**manşet κ değildir** ve onun yerine geçemez.

Round0 emsali (`_kalibrasyon-sonucu.md`): Fleiss κ hakemlik öncesi **0,051**,
sonrası **0,268**; ikisi de yayımlandı, biri diğerinin yerine konmadı. Aynı
kural burada da geçerlidir — manşet κ = **0,274** (hakemlik öncesi) olarak
kalır.

Hakemliğin meşru amacı **gold kalitesidir**: 53 uyuşmazlık çözülmezse o
hücreler `build_gold` tarafından `needs_adjudication` işaretlenir ve gold'a
girmez. Üçüncü bir göz onları kurtarır.

## Karar kuralı

Hakem, A ve B'nin kararlarını GÖRMEDEN aynı hücreye baktı. Üç sonuç olabilir:

  hakem == A  ->  B, A'ya çekilir      (A haklı)
  hakem == B  ->  A, B'ye çekilir      (B haklı)
  hakem ikisinden de farklı  ->  **HİÇBİRİNE DOKUNULMAZ**

Üçüncü durumda betiğin kendi kararını dayatması, hakemi anotatör yerine koymak
olurdu. O hücreler insan hakemliğine bırakılır ve raporda listelenir.

`unclear` kararı da uygulanmaz: metrik dışı bir etiketi iki tarafa birden
yazmak uyuşmazlığı çözmez, gizler.

## Silme yok

Yazmadan önce `<dosya>.yedek-hakemlik-round1` alınır (varsa sıra numarası
eklenir). Her değişiklik `_hakemlik-degisim-round1.md`'ye tek tek yazılır.

Kullanım:
    .venv/bin/python -m scripts.hakemlik_uygula --kuru     # ne olacağını gör
    .venv/bin/python -m scripts.hakemlik_uygula
"""

from __future__ import annotations

import argparse
import csv
import json
import shutil
import sys
from collections import Counter
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from scripts.gold_schema import parse_gold_value
from scripts.report_iaa import row_value_token, row_verdict
from scripts.to_review_csv import (
    CSV_DELIMITER,
    CSV_ENCODING,
    CSV_LINETERMINATOR,
)

KARAR_SUTUNLARI = ("gold_value", "verdict", "note")
VARSAYILAN_RAPOR = "data/gold/review/_hakemlik-degisim-round1.md"


def _oku(yol: Path) -> tuple[list[str], list[dict]]:
    with yol.open(encoding=CSV_ENCODING, newline="") as fh:
        okuyucu = csv.DictReader(fh, delimiter=CSV_DELIMITER)
        baslik = [(h or "").lstrip("﻿") for h in (okuyucu.fieldnames or [])]
        return baslik, [{(k or "").lstrip("﻿"): (v or "") for k, v in r.items()}
                        for r in okuyucu]


def _yedekle(yol: Path) -> Path:
    hedef = yol.with_suffix(yol.suffix + ".yedek-hakemlik-round1")
    n = 2
    while hedef.exists():
        hedef = yol.with_suffix(f"{yol.suffix}.yedek-hakemlik-round1{n}")
        n += 1
    shutil.copy2(yol, hedef)
    return hedef


def _kanonik(alan: str, jeton):
    """Karşılaştırma için değeri kanonikleştirir (`150000` == `{value:150000}`)."""
    if jeton is None or jeton == "__YOK__":
        return jeton
    try:
        return json.dumps(_duzle(parse_gold_value(alan, jeton)), sort_keys=True,
                          ensure_ascii=False)
    except Exception:
        return jeton


def _duzle(d):
    if isinstance(d, bool):
        return d
    if isinstance(d, float) and d.is_integer():
        return int(d)
    if isinstance(d, dict):
        return {k: _duzle(v) for k, v in d.items()}
    if isinstance(d, list):
        return [_duzle(v) for v in d]
    return d


def _hakem_satiri(hakem: dict, ornek: dict) -> dict:
    """Hakem kararını, jeton karşılaştırması için CSV satırı biçimine sokar."""
    satir = dict(ornek)
    satir["verdict"] = (hakem.get("verdict") or "").strip().casefold()
    satir["gold_value"] = (hakem.get("gold_value") or "").strip()
    return satir


def uygula(a_yolu: Path, b_yolu: Path, hakem_yolu: Path,
           kuru: bool = False) -> dict:
    a_baslik, a_satirlar = _oku(a_yolu)
    b_baslik, b_satirlar = _oku(b_yolu)
    A = {(r["doc_id"].strip(), r["field"].strip()): r for r in a_satirlar}
    B = {(r["doc_id"].strip(), r["field"].strip()): r for r in b_satirlar}

    hakemler = {}
    for s in hakem_yolu.read_text(encoding="utf-8").splitlines():
        if s.strip():
            h = json.loads(s)
            hakemler[(h["doc_id"].strip(), h["field"].strip())] = h

    rapor = {"a": str(a_yolu), "b": str(b_yolu),
             "hakem_karar": len(hakemler),
             "degisiklik": [], "dokunulmayan": [], "unclear_atlanan": [],
             "yedek": []}

    for anahtar, hakem in sorted(hakemler.items()):
        if anahtar not in A or anahtar not in B:
            continue
        sa, sb = A[anahtar], B[anahtar]
        va, vb = row_verdict(sa), row_verdict(sb)
        if not va or not vb or va == vb:
            continue

        hv = (hakem.get("verdict") or "").strip().casefold()
        if hv == "unclear":
            rapor["unclear_atlanan"].append(
                {"anahtar": anahtar, "A": va, "B": vb,
                 "not": (hakem.get("note") or "")[:120]})
            continue

        alan = anahtar[1]
        h_satir = _hakem_satiri(hakem, sa)
        h_jeton = _kanonik(alan, row_value_token(h_satir))
        a_jeton = _kanonik(alan, row_value_token(sa))
        b_jeton = _kanonik(alan, row_value_token(sb))

        # Hem KARAR hem SONUÇ örtüşmeli: `ok` ile `fix` aynı değeri üretse bile
        # farklı kararlardır ve κ'yı etkileyen şey karardır.
        a_uyar = (hv == va) and (h_jeton == a_jeton)
        b_uyar = (hv == vb) and (h_jeton == b_jeton)

        if a_uyar and not b_uyar:
            kazanan, kaybeden, kaynak, hedef = "A", "B", sa, sb
        elif b_uyar and not a_uyar:
            kazanan, kaybeden, kaynak, hedef = "B", "A", sb, sa
        else:
            rapor["dokunulmayan"].append(
                {"anahtar": anahtar, "A": va, "B": vb, "hakem": hv,
                 "sebep": "hakem ikisiyle de ortusmedi" if not (a_uyar or b_uyar)
                          else "hakem ikisiyle de ortustu (beklenmedik)",
                 "not": (hakem.get("note") or "")[:120]})
            continue

        eski = {s: hedef.get(s, "") for s in KARAR_SUTUNLARI}
        for sutun in ("gold_value", "verdict"):
            hedef[sutun] = kaynak.get(sutun, "")
        onceki_not = (hedef.get("note") or "").strip()
        damga = f"#hakemlik-round1 {kaybeden}->{kazanan} (kor hakem onayi)"
        hedef["note"] = f"{onceki_not} | {damga}" if onceki_not else damga

        rapor["degisiklik"].append({
            "anahtar": anahtar, "kazanan": kazanan, "kaybeden": kaybeden,
            "eski": eski, "yeni": {s: hedef.get(s, "") for s in KARAR_SUTUNLARI},
            "hakem_not": (hakem.get("note") or "")[:160]})

    if not kuru and rapor["degisiklik"]:
        for yol, baslik, satirlar in ((a_yolu, a_baslik, a_satirlar),
                                      (b_yolu, b_baslik, b_satirlar)):
            rapor["yedek"].append(str(_yedekle(yol)))
            with yol.open("w", encoding=CSV_ENCODING, newline="") as fh:
                y = csv.DictWriter(fh, fieldnames=baslik, delimiter=CSV_DELIMITER,
                                   lineterminator=CSV_LINETERMINATOR)
                y.writeheader()
                y.writerows(satirlar)
    return rapor


def render(rapor: dict) -> str:
    d = rapor["degisiklik"]
    kazanan = Counter(x["kazanan"] for x in d)
    alan = Counter(x["anahtar"][1] for x in d)

    s = ["# Round1 Hakemlik Değişim Kaydı", "",
         "> `scripts/hakemlik_uygula.py` üretti. Kör hakem A ve B'nin "
         "kararlarını GÖRMEDEN aynı hücrelere baktı; kararı hangi anotatörle "
         "örtüştüyse diğeri ona çekildi.", "",
         "## ⛔ κ üzerindeki etkisi", "",
         "Manşet κ = **0,274** (hakemlik ÖNCESİ, `iaa_report_round1.md`) "
         "olarak kalır. Bu dosyadan sonra hesaplanan κ, bağımsız uyum değil "
         "**üçüncü göz sonrası gold tutarlılığıdır**; ikisi ayrı raporlanır "
         "(round0 emsali: `_kalibrasyon-sonucu.md` §8, 0,051 → 0,268).", "",
         "## Sayılar", "",
         f"- Hakem kararı: **{rapor['hakem_karar']}**",
         f"- Uygulanan değişiklik: **{len(d)}**",
         f"  - A haklı (B düzeltildi): **{kazanan.get('A', 0)}**",
         f"  - B haklı (A düzeltildi): **{kazanan.get('B', 0)}**",
         f"- Dokunulmayan (hakem ikisiyle de örtüşmedi): "
         f"**{len(rapor['dokunulmayan'])}**",
         f"- `unclear` olduğu için atlanan: **{len(rapor['unclear_atlanan'])}**", ""]

    if alan:
        s += ["### Alan dağılımı", "", "| Alan | Değişiklik |", "|---|---:|"]
        s += [f"| `{f}` | {n} |" for f, n in alan.most_common()]
        s.append("")

    if d:
        s += ["## Uygulanan değişiklikler", "",
              "| Belge | Alan | Haklı | Eski karar | Yeni karar | Hakem gerekçesi |",
              "|---|---|---|---|---|---|"]
        for x in d:
            doc, f = x["anahtar"]
            e, y = x["eski"], x["yeni"]
            s.append(
                f"| `{doc[:42]}` | `{f}` | {x['kazanan']} | "
                f"{e['verdict'] or '(bos)'} `{e['gold_value'][:22]}` | "
                f"{y['verdict']} `{y['gold_value'][:22]}` | "
                f"{x['hakem_not'][:90]} |")
        s.append("")

    if rapor["dokunulmayan"]:
        s += ["## Dokunulmayan — insan hakemliğine kalır", "",
              "Hakem üçüncü bir cevap verdi. Betiğin kendi kararını dayatması "
              "hakemi anotatör yerine koymak olurdu.", "",
              "| Belge | Alan | A | B | Hakem | Gerekçe |", "|---|---|---|---|---|---|"]
        for x in rapor["dokunulmayan"]:
            doc, f = x["anahtar"]
            s.append(f"| `{doc[:38]}` | `{f}` | {x['A']} | {x['B']} | "
                     f"{x['hakem']} | {x['not'][:70]} |")
        s.append("")

    if rapor["unclear_atlanan"]:
        s += ["## Hakem `unclear` dedi — atlandı", "",
              "| Belge | Alan | A | B | Gerekçe |", "|---|---|---|---|---|"]
        for x in rapor["unclear_atlanan"]:
            doc, f = x["anahtar"]
            s.append(f"| `{doc[:38]}` | `{f}` | {x['A']} | {x['B']} | "
                     f"{x['not'][:70]} |")
        s.append("")

    if rapor["yedek"]:
        s += ["## Geri alma", "",
              "```bash"] + [f"cp {y} {y.rsplit('.yedek', 1)[0]}"
                            for y in rapor["yedek"]] + ["```", ""]
    return "\n".join(s)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--a", default="data/gold/review/round1_A.csv")
    ap.add_argument("--b", default="data/gold/review/round1_B.csv")
    ap.add_argument("--hakem", default="data/gold/review/_hakem_kararlari.jsonl")
    ap.add_argument("--rapor", default=VARSAYILAN_RAPOR)
    ap.add_argument("--kuru", action="store_true", help="yazmadan dene")
    args = ap.parse_args(argv)

    rapor = uygula(_ROOT / args.a, _ROOT / args.b, _ROOT / args.hakem,
                   kuru=args.kuru)
    kazanan = Counter(x["kazanan"] for x in rapor["degisiklik"])
    print(f"hakem karari        : {rapor['hakem_karar']}")
    print(f"UYGULANAN degisiklik: {len(rapor['degisiklik'])}")
    print(f"  A hakli (B duzeldi): {kazanan.get('A', 0)}")
    print(f"  B hakli (A duzeldi): {kazanan.get('B', 0)}")
    print(f"dokunulmayan        : {len(rapor['dokunulmayan'])}")
    print(f"unclear atlanan     : {len(rapor['unclear_atlanan'])}")

    if not args.kuru:
        (_ROOT / args.rapor).write_text(render(rapor), encoding="utf-8")
        print(f"rapor: {args.rapor}")
        for y in rapor["yedek"]:
            print(f"yedek: {Path(y).name}")
    else:
        print("(kuru koşu — dosya YAZILMADI)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
