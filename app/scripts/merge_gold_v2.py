"""gold.v2 parçalarını birleştirir ve kanıt bütünlüğünü DOĞRULAR.

İlgili: sample_gold_v2.py, gold_schema.py, ../docs/rapor/gold-genisletme.md

## Birleştirme değil, KAPI

Bu betiğin işi dört anotasyon parçasını uç uca eklemek değil; ölçüm setine
girecek her kaydın **kanıtlı** olduğunu mekanik olarak ispatlamaktır. Üç
kapı vardır ve hiçbiri atlanamaz:

1. **Şema** — `gold_schema.validate_gold`. Kanonik biçim bozuksa
   `run_eval` sessizce yanlış eşleştirir.
2. **Kanıt** — `field_spans` içindeki her alıntı, kaydın `text`inde
   **birebir** geçmeli. Geçmiyorsa değer uydurulmuş ya da parafraz
   edilmiştir; ikisi de gold'u zehirler. Bu, kör anotasyon protokolünün
   tek mekanik korumasıdır.
3. **Ayrıklık** — `content_hash` tekil olmalı ve gold.v1 ile kesişmemeli.
   Aynı belgeyi iki kez ölçmek n'i şişirir, bilgi eklemez.

Kapılardan biri düşerse betik yazmaz ve **gürültülü** başarısız olur.
"Kısmen geçerli gold" diye bir şey yoktur.

## Kanıt kapısının gevşetilmiş hâli — ve neden

Alıntı, metinde birebir aranır. Bulunamazsa **boşluk sadeleştirilmiş**
biçimde bir kez daha aranır (`\\s+` -> tek boşluk). Sebep: anotatör
metinden kopyalarken satır sonu/çift boşluk kaybı olabiliyor ve bu bir
uydurma değil, kopyalama gürültüsüdür. Bunun ötesinde esneme YOKTUR —
büyük/küçük harf katlaması ya da kısmi eşleşme kabul edilmez.

## Kullanım

    python -m scripts.merge_gold_v2
    python -m scripts.merge_gold_v2 --parca-dir data/gold/parca --out data/gold/gold.v2.json

Çıkış kodları: 0 yazıldı · 1 kapı düştü (yazılmadı) · 2 girdi yok.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

KOK = Path(__file__).resolve().parents[1]
if str(KOK) not in sys.path:
    sys.path.insert(0, str(KOK))

from scripts.gold_schema import record_from_dict, validate_gold

VARSAYILAN_PARCA = "data/gold/parca"
VARSAYILAN_OUT = "data/gold/gold.v2.json"
VARSAYILAN_V1 = "data/gold/gold.v1.json"

_BOSLUK = re.compile(r"\s+")


def _sadelestir(s: str) -> str:
    return _BOSLUK.sub(" ", s).strip()


def kanit_kapisi(kayitlar: list[dict]) -> list[str]:
    """Her `field_spans` alıntısı belgede birebir geçiyor mu?"""
    hatalar: list[str] = []
    for k in kayitlar:
        metin = k.get("text") or ""
        sade = _sadelestir(metin)
        for alan, alinti in (k.get("field_spans") or {}).items():
            if not isinstance(alinti, str) or not alinti.strip():
                hatalar.append(f"{k.get('id')} / {alan}: alıntı boş")
                continue
            if alinti in metin or _sadelestir(alinti) in sade:
                continue
            hatalar.append(
                f"{k.get('id')} / {alan}: alıntı metinde YOK -> "
                f"{alinti[:80]!r}")
        # Değeri olan ama kanıtı olmayan alanlar da kusurdur.
        for alan in (k.get("fields") or {}):
            if alan not in (k.get("field_spans") or {}):
                hatalar.append(f"{k.get('id')} / {alan}: değer var, kanıt YOK")
    return hatalar


def ayriklik_kapisi(kayitlar: list[dict], v1_yolu: str) -> list[str]:
    hatalar: list[str] = []
    sayac = Counter(k.get("content_hash") for k in kayitlar)
    for h, n in sayac.items():
        if n > 1:
            hatalar.append(f"content_hash {h!r} {n} kez geçiyor (parçalar çakışmış)")
    p = Path(v1_yolu)
    if p.is_file():
        v1 = {x.get("content_hash") for x in json.loads(p.read_text(encoding="utf-8"))}
        for k in kayitlar:
            if k.get("content_hash") in v1:
                hatalar.append(f"{k.get('id')}: gold.v1 ile AYNI belge")
    return hatalar


def ozet(kayitlar: list[dict]) -> str:
    alan = Counter()
    yok = Counter()
    belirsiz = 0
    zor = 0
    tur = Counter()
    banka = Counter()
    for k in kayitlar:
        tur[str(k.get("campaign_type"))] += 1
        banka[str(k.get("bank_slug"))] += 1
        zor += bool(k.get("hard"))
        for a in (k.get("fields") or {}):
            alan[a] += 1
        for a in (k.get("absent_fields") or []):
            yok[a] += 1
        karar = set(k.get("fields") or {}) | set(k.get("absent_fields") or [])
        belirsiz += len(set(k.get("notes") or {}) - karar)
    s = [f"kayıt: {len(kayitlar)} | zor vaka: {zor} | belirsiz alan: {belirsiz}",
         "", "alan doluluk (değer / yok):"]
    for a in sorted(set(alan) | set(yok)):
        s.append(f"  {a:<22} {alan[a]:>3} / {yok[a]:>3}")
    s += ["", "tür: " + ", ".join(f"{k}={v}" for k, v in sorted(tur.items()))]
    s += ["banka: " + ", ".join(f"{k}={v}" for k, v in sorted(banka.items()))]
    return "\n".join(s)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="python -m scripts.merge_gold_v2",
        description="gold.v2 parçalarını birleştir + kanıt/şema/ayrıklık kapıları.")
    ap.add_argument("--parca-dir", default=VARSAYILAN_PARCA)
    ap.add_argument("--desen", default="etiket-*.json")
    ap.add_argument("--out", default=VARSAYILAN_OUT)
    ap.add_argument("--v1", default=VARSAYILAN_V1)
    args = ap.parse_args(argv)

    yollar = sorted(Path(args.parca_dir).glob(args.desen))
    if not yollar:
        print(f"HATA: parça bulunamadı: {args.parca_dir}/{args.desen}",
              file=sys.stderr)
        return 2

    kayitlar: list[dict] = []
    for y in yollar:
        veri = json.loads(y.read_text(encoding="utf-8"))
        print(f"  {y.name}: {len(veri)} kayıt")
        kayitlar.extend(veri)

    hatalar: list[str] = []
    try:
        hatalar += validate_gold([record_from_dict(k) for k in kayitlar])
    except (ValueError, KeyError, TypeError) as e:
        hatalar.append(f"şema okunamadı: {e}")
    hatalar += kanit_kapisi(kayitlar)
    hatalar += ayriklik_kapisi(kayitlar, args.v1)

    if hatalar:
        print(f"\nKAPI DÜŞTÜ — {len(hatalar)} bulgu, DOSYA YAZILMADI:\n",
              file=sys.stderr)
        for h in hatalar[:40]:
            print(f"  - {h}", file=sys.stderr)
        if len(hatalar) > 40:
            print(f"  ... ve {len(hatalar) - 40} tane daha", file=sys.stderr)
        return 1

    Path(args.out).write_text(
        json.dumps(kayitlar, ensure_ascii=False, indent=2), encoding="utf-8")
    print("\n" + ozet(kayitlar))
    print(f"\nYazıldı: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
