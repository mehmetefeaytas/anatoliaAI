"""Gold dosyalarının bütünlük tanığını denetler: sidecar + eşik künyesi.

İlgili: scripts/kanit_zinciri.py (gold kaydı -> ham arşiv provenance'ı)
        eval/esikler.json, eval/esikler-round1.json (regresyon kapıları)
        tests/test_gold_butunluk.py

## Neden bu betik var

"Gold dondurulmuştur" cümlesi bir iddiadır ve iddianın koşulabilir bir
tanığı olmalıdır. Tanık iki yerde duruyordu:

    data/gold/<ad>.json.sha256   kardeş dosya (shasum -c biçimi)
    eval/esikler*.json           `gold_sha256` künyesi

Ama **hiçbiri denetlenmiyordu**. `scripts/kanit_zinciri.py` gold kaydının
metnini ham arşive kadar izler — başka bir soruyu, provenance'ı yanıtlar;
gold dosyasının kendi baytlarına bakmaz.

Sonucu 20-21 Ağustos 2026'da gerçekleşti: `gold.round1.json.sha256`
`d6cb8018` commit'inde DOĞRUYDU (`dc0e45d8`), sonra üç hakemlik commit'i
gold'u değiştirirken sidecar güncellenmedi:

    c5100ddb  HAKEM-05 uygulandi          gold -> 6f76ced0
    6056a2e8  S1 kilavuz karari           gold -> b7e75948
    4c8fcfa3  Juri 4 bulgulari            gold -> e9c24391  (guncel)

Üçü de kasıtlı, gerekçesi commit mesajında yazılı kararlardı — dondurma
gizlice bozulmadı, **tanık güncellenmedi**. Fark şudur: `shasum -c`
koşan biri FAILED görür ve tüm ölçüm anlatısı bir kalemde şüpheye düşer.
Kaybedilen şey doğruluk değil, doğruluğun gösterilebilirliğidir.

## Neyi doğrular

1. Sidecar'ı olan her gold dosyasının sha256'sı sidecar ile **tutuyor**.
2. Sidecar içindeki dosya adı gerçek dosya adıyla **aynı** (yanlış dosyaya
   bakan bir tanık tanık değildir).
3. Eşik dosyalarının `gold_sha256` künyesi, `gold` alanında adı geçen
   dosyanın gerçek özetiyle **tutuyor**. Künye kısa önek olabilir
   (ör. `e9c24391`); önek karşılaştırması yapılır.
4. Eşik dosyasında `gold_sha256` künyesi **var**. Eksik künye de bir
   ihlaldir: eşiklerin hangi gold üzerinde ölçüldüğü yazılı olmayan bir
   kapı, neyi koruduğunu söyleyemez.

## Kapıyı ne kapatır, ne kapatmaz

**Kapatır (çıkış 1):** sidecar ile dosya arasında sapma; sidecar'da yanlış
dosya adı; eşik künyesi ile gold arasında sapma; eşik dosyasında künye
eksikliği.

**Kapatmaz:** sidecar'ı hiç olmayan gold dosyası. Her ara dosyaya tanık
zorlamak (`gold.v2.aday.json`, `preannotations*.json`) gürültü üretir;
tanık, ÖLÇÜMDE KULLANILAN setler için anlamlıdır ve onlarda vardır.
Bir sidecar bir kez oluşturulduğunda bu kapı onu sonsuza dek denetler.

## Sidecar tazeleme

Gold'u BİLEREK değiştirdiyseniz tanığı da tazelemek işin parçasıdır:

    cd data/gold && shasum -a 256 gold.round1.json > gold.round1.json.sha256

ve eşik dosyasındaki `gold_sha256` künyesini güncelleyin. Değişikliğin
GEREKÇESİ commit mesajına yazılır — sessiz tazeleme, kapının varlık
sebebini ortadan kaldırır.

## Kullanım

    python -m scripts.gold_butunluk
    python -m scripts.gold_butunluk --kok /yol/app
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

# Sidecar'ı denetlenen eşik dosyaları. Her biri `gold` ve `gold_sha256`
# alanlarını taşımak ZORUNDADIR (bkz. yukarıda 4. madde).
ESIK_DOSYALARI = ("eval/esikler.json", "eval/esikler-round1.json")

GOLD_DIZINI = "data/gold"


def ozet(yol: Path) -> str:
    """Dosyanın sha256'sı. Gold setleri MB düzeyinde; parça parça okunur."""
    h = hashlib.sha256()
    with yol.open("rb") as f:
        for parca in iter(lambda: f.read(1 << 20), b""):
            h.update(parca)
    return h.hexdigest()


def sidecar_oku(yol: Path) -> tuple[str, str] | None:
    """`<hash>  <dosya adi>` -> (hash, ad). Bozuk biçimde None."""
    metin = yol.read_text(encoding="utf-8").strip()
    if not metin:
        return None
    parcalar = metin.split()
    if len(parcalar) < 2:
        return None
    return parcalar[0].lower(), parcalar[-1]


def sidecar_denetimi(kok: Path) -> list[str]:
    """Sidecar'ı olan her gold dosyası için ihlal satırları."""
    ihlaller: list[str] = []
    dizin = kok / GOLD_DIZINI
    for sc in sorted(dizin.glob("*.sha256")):
        hedef = dizin / sc.name[: -len(".sha256")]
        if not hedef.exists():
            ihlaller.append(f"{sc.name}: tanık var ama dosya YOK ({hedef.name})")
            continue
        okunan = sidecar_oku(sc)
        if okunan is None:
            ihlaller.append(f"{sc.name}: biçim bozuk — `<hash>  <dosya>` beklenir")
            continue
        beyan, ad = okunan
        gercek = ozet(hedef)
        if ad != hedef.name:
            ihlaller.append(
                f"{sc.name}: tanık '{ad}' dosyasına bakıyor, kardeşi ise "
                f"'{hedef.name}' — yanlış dosyaya bakan tanık tanık değildir")
        if beyan != gercek:
            ihlaller.append(
                f"{hedef.name}: SAPMA — tanık {beyan[:16]}…, gerçek {gercek[:16]}… "
                f"(gold değiştiyse tanığı tazeleyin; bkz. betik başlığı)")
    return ihlaller


def esik_denetimi(kok: Path) -> list[str]:
    """Eşik dosyalarının `gold_sha256` künyesi gerçek gold ile tutuyor mu."""
    ihlaller: list[str] = []
    for bagil in ESIK_DOSYALARI:
        yol = kok / bagil
        if not yol.exists():
            ihlaller.append(f"{bagil}: dosya YOK")
            continue
        veri = json.loads(yol.read_text(encoding="utf-8"))
        gold_bagil = veri.get("gold")
        if not gold_bagil:
            ihlaller.append(f"{bagil}: `gold` alanı yok — hangi seti ölçtüğü yazılı değil")
            continue
        gold = kok / gold_bagil
        if not gold.exists():
            ihlaller.append(f"{bagil}: `gold` = {gold_bagil} ama dosya YOK")
            continue
        kunye = veri.get("gold_sha256")
        if not kunye:
            ihlaller.append(
                f"{bagil}: `gold_sha256` künyesi EKSİK — eşiklerin hangi gold "
                f"üzerinde ölçüldüğü yazılı olmayan kapı neyi koruduğunu söyleyemez")
            continue
        gercek = ozet(gold)
        # Künye kısa önek olabilir; önek karşılaştırması yapılır.
        if not gercek.startswith(str(kunye).lower()):
            ihlaller.append(
                f"{bagil}: künye {kunye} ile {gold_bagil} SAPMIŞ "
                f"(gerçek {gercek[: max(8, len(str(kunye)))]}…)")
    return ihlaller


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Gold bütünlük tanığı denetimi (sidecar + eşik künyesi).")
    ap.add_argument("--kok", default=None,
                    help="app/ dizini (varsayılan: bu betiğin iki üstü)")
    a = ap.parse_args(argv)

    kok = Path(a.kok) if a.kok else Path(__file__).resolve().parent.parent

    sidecarlar = sorted((kok / GOLD_DIZINI).glob("*.sha256"))
    ihlaller = sidecar_denetimi(kok) + esik_denetimi(kok)

    print("Gold bütünlük denetimi\n")
    print(f"  denetlenen tanık : {len(sidecarlar)}")
    print(f"  denetlenen eşik  : {len(ESIK_DOSYALARI)}")
    print(f"  ihlal            : {len(ihlaller)}")
    if ihlaller:
        print()
        for satir in ihlaller:
            print(f"  ✗ {satir}")
        return 1
    print("\n  ✅ tüm tanıklar ve künyeler tutuyor.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
