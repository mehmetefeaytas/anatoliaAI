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

## Kanıt kapısı NEREDE tanımlı — ve neden burada değil

Kapının kendisi `gold_schema.span_supports` / `fabrication_errors` /
`uncovered_fields` içindedir, bu dosyada değil. Sebep ölçüldü (2026-08-10):
kapı burada yaşarken `gold_schema.GoldRecord` `field_spans` anahtarını
tanımlamıyordu ve `build_gold.py` onu üretmiyordu. İki gold hattı sessizce
ayrıştı — gold.v2'nin 112/112 alanı kanıtlıyken gold.v1'in **0/65**'i
kanıtlıydı; v1 hattının çıktısı bu kapıdan her alanda düşerdi.

Kapı şemaya taşındığında ayrışma yapısal olarak imkânsızlaştı: `build_gold`
zaten `gold_schema`yı içe aktarıyor, dolayısıyla aynı tanımı kullanmaktan
kaçamaz.

## Bu betikte kapı GEVŞEMEZ

`merge_gold_v2` hattı (dört anotatörün elle yazdığı alıntılar) hem uydurmayı
hem kanıtsızlığı ÖLÜMCÜL sayar; davranış değişmedi. `build_gold` hattı
kanıtsızlığı sayar ve raporlar, ölümcül saymaz (bkz. o dosyanın başlığı) —
çünkü orada kanıtın kaynağı anotatörün kalemi değil, çıkarıcının kaydettiği
konumdur ve `fix` kararlarında böyle bir kayıt YOKTUR. Uydurma her iki
hatta da ölümcüldür.

## Kullanım

    python -m scripts.merge_gold_v2
    python -m scripts.merge_gold_v2 --parca-dir data/gold/parca --out data/gold/gold.v2.json

Çıkış kodları: 0 yazıldı · 1 kapı düştü (yazılmadı) · 2 girdi yok.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

KOK = Path(__file__).resolve().parents[1]
if str(KOK) not in sys.path:
    sys.path.insert(0, str(KOK))

from scripts.gold_schema import (
    GoldRecord,
    fabrication_errors,
    record_from_dict,
    uncovered_fields,
    validate_gold,
)

VARSAYILAN_PARCA = "data/gold/parca"
VARSAYILAN_OUT = "data/gold/gold.v2.json"
VARSAYILAN_V1 = "data/gold/gold.v1.json"


def kanit_kapisi(kayitlar: list[GoldRecord]) -> list[str]:
    """Bu hatta kanıt kapısı iki kusuru da ölümcül sayar.

    Ayrımı yine de koruruz: uydurma "yakalandı", kanıtsızlık "eksik". İkisi
    aynı listeye girse bile mesajları ayrı okunur, yoksa anotatöre neyi
    düzelteceği anlaşılmaz — biri alıntıyı düzeltmeli, diğeri alıntı YAZMALI.
    """
    hatalar = list(fabrication_errors(kayitlar))
    hatalar += [f"{kimlik} / {alan}: değer var, kanıt YOK"
                for kimlik, alan in uncovered_fields(kayitlar)]
    return hatalar


def ayriklik_kapisi(kayitlar: list[dict], v1_yolu: str) -> list[str]:
    hatalar: list[str] = []
    sayac = Counter(k.get("content_hash") for k in kayitlar)
    for h, n in sayac.items():
        if n > 1:
            hatalar.append(f"content_hash {h!r} {n} kez geçiyor (parçalar çakışmış)")
    p = Path(v1_yolu)
    if p.is_file():
        v1_kayitlar = json.loads(p.read_text(encoding="utf-8"))
        # `content_hash` ÜZERİNDEN KARŞILAŞTIRMA YAPILMAZ — kapı böyle kördü.
        #
        # Ölçüldü (2026-08-08): gold.v2'nin 48/48 kaydında
        # `content_hash == sha256(text)`, gold.v1'in ise **0/20**'sinde. v1
        # hash'i başka bir şeyden (muhtemelen ham HTML) türetilmiş. İki hash
        # uzayı karşılaştırılamaz olduğu için kapı YAPISAL OLARAK her zaman
        # "kesişim yok" döndürüyordu.
        #
        # Gerçekte iki belge örtüşüyordu — aynı `id`, **bayt bayt aynı**
        # `text` (`kuveyt-turk--leasing-…` 1822 krk,
        # `albaraka--tasit-finansmani-togg-finansmani` 2528 krk) — ve sessizce
        # geçti. Sonuç: ölçüm seti 20+48=68 diye raporlandı, gerçekte **66**
        # tekil belge.
        #
        # Bu, projede ikinci kez görülen "anahtar uzayı ayrıştı, kapı sessizce
        # geçti" kusurudur; ilki gold `id` kuralının `abs(hash(url))`e
        # kaymasıydı (bkz. `sample_gold_v2._korpus_kimlikleri`). Bu yüzden
        # karşılaştırma artık **içeriğin kendisi** üzerinden yapılıyor:
        # metin türetilmiş bir anahtar değil, belgenin ta kendisidir.
        v1_metin = {x.get("text") for x in v1_kayitlar if x.get("text")}
        v1_id = {x.get("id") for x in v1_kayitlar if x.get("id")}
        for k in kayitlar:
            if k.get("text") in v1_metin:
                hatalar.append(
                    f"{k.get('id')}: gold.v1 ile AYNI belge (metin birebir)")
            elif k.get("id") in v1_id:
                # Metin farklı ama kimlik aynı: aynı sayfanın iki çekimi.
                # Ayrı bir hata sınıfı — n'i şişirmez ama bağımsızlık varsayımını
                # zedeler (aynı sayfa iki kez ölçüme girer).
                hatalar.append(
                    f"{k.get('id')}: gold.v1 ile AYNI KİMLİK (metin farklı — "
                    "aynı sayfanın iki çekimi olabilir)")
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
        sema_kayitlari = [record_from_dict(k) for k in kayitlar]
    except (ValueError, KeyError, TypeError) as e:
        hatalar.append(f"şema okunamadı: {e}")
        sema_kayitlari = []
    else:
        hatalar += validate_gold(sema_kayitlari)
        hatalar += kanit_kapisi(sema_kayitlari)
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
