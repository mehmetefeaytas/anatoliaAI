"""8-sınıf kampanya türü sınıflandırmasını gold üzerinde ölç.

İlgili: ../eval/run_eval.py (Counts + macro_f1 yeniden kullanılıyor),
        ../src/extraction/ner/classifier.py (kural temel çizgisi),
        ../data/silver/silver.jsonl (Faz 3 eğitim kümesi),
        CLAUDE.md §4, §16 (ablasyon tablosu)

Kullanım:
    # Temel çizgi — kural sınıflandırıcı
    python -m scripts.eval_classifier

    # İnce ayarlı model (Colab'da eğitilip tahminleri dışa aktarıldıktan sonra)
    python -m scripts.eval_classifier --predictions data/eval/berturk_preds.jsonl \\
        --name berturk

    # İkisini yan yana
    python -m scripts.eval_classifier --predictions ... --name berturk --compare

## Neden bu betik var

CLAUDE.md §4 kampanya türü sınıflandırması için BERTurk ince ayarına izin veren
tek yer; §16 ise kazananın **ablasyon tablosuna satır olarak** girmesini
istiyor. Bunun için iki şey gerekiyordu ve ikisi de yoktu:

1. **Temel çizgi.** BERTurk'ün geçmesi gereken sayı neydi? `RuleHintClassifier`
   korpusta koşuyordu ama gold üzerinde hiç ölçülmemişti.
2. **Eşit koşul.** İki modelin aynı gold, aynı metrik, aynı çekimser
   muamelesiyle ölçülmesi. Ayrı ölçüm hattı = kıyaslanamaz sayı.

Bu betik ikisini de veriyor: kural çizgisini koşar, `--predictions` ile herhangi
bir modelin tahminlerini **aynı** hattan geçirir.

## Çekimserlik (abstain) nasıl sayılıyor

`RuleHintClassifier` ipucu bulamazsa `None` döner — bu kasıtlı, "uydurma yok"
kuralının sınıflandırma tarafındaki karşılığı (CLAUDE.md §19). Ama metrikte
çekimserliği görmezden gelmek modeli **ödüllendirir**: zor belgelerde susup
kolaylarda konuşan bir model yüksek precision alır.

Bu yüzden çekimserlik **FN sayılır** (doğru sınıf yakalanmadı) ama **FP
sayılmaz** (yanlış bir sınıf iddia edilmedi). Böylece susmak recall'u düşürür,
precision'ı şişirmez. Çekimser sayısı ayrıca raporlanır.

## n=20 — sayının sınırı

Gold sette `campaign_type` taşıyan **20** belge var. Bu, sınıf başına ortalama
2-3 örnek demek; makro-F1 tek bir belgenin gidip gelmesiyle oynar. Betik bunu
gizlemez, çıktının başında yazar. Sayı bir sıralama sinyalidir, kesin bir
performans ölçüsü değil.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from collections.abc import Sequence
from typing import Any, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from eval.run_eval import Counts, macro_f1
from src.schemas import CAMPAIGN_TYPES

#: Makro-F1'in tek belgeye duyarlı olmaktan çıktığı kaba eşik. Altındaysa
#: çıktı bunu açıkça söyler.
GUVENILIR_N = 50


def _gold_yukle(path: str) -> list[tuple[str, str, str, Optional[str]]]:
    """(doc_id, metin, gerçek etiket, source_url) — `campaign_type` taşıyanlar.

    DÖRDÜNCÜ alan 2026-08-20'de eklendi: `RuleHintClassifier` artık URL yolunu
    kullanıyor (bkz. src/extraction/ner/classifier.py) ve URL'i harness'ta
    düşürmek, ölçülen kolu üretimde koşan koldan FARKLI kılardı — tam olarak
    bu dosyanın başlığında "eşit koşul" diye adlandırılan kusur.

    Tüketiciler ÜÇ elemanlı kayıtları da kabul eder (`olc`, `_kural_tahminleri`
    indekse göre okur); testlerdeki elle yazılmış 3'lüler bozulmadan çalışır.
    """
    from scripts.gold_schema import load_gold
    out = []
    for rec in load_gold(path):
        if isinstance(rec.campaign_type, str) and rec.campaign_type:
            out.append((rec.id, rec.text, rec.campaign_type, rec.source_url))
    return out


def _tahminleri_yukle(path: str) -> dict[str, Optional[str]]:
    """`{"doc_id": ..., "label": ...}` JSONL. `label: null` = çekimser."""
    out: dict[str, Optional[str]] = {}
    with open(path, encoding="utf-8") as fh:
        for satir in fh:
            satir = satir.strip()
            if not satir:
                continue
            d = json.loads(satir)
            out[d["doc_id"]] = d.get("label")
    return out


def _kural_tahminleri(gold: Sequence[Sequence[Any]]) -> dict[str, Optional[str]]:
    """Kural kolunu ÜRETİMDEKİ imzasıyla koşturur (metin + `source_url`)."""
    from src.extraction.ner.classifier import RuleHintClassifier
    clf = RuleHintClassifier()
    return {k[0]: clf.classify(k[1], k[3] if len(k) > 3 else None)[0]
            for k in gold}


def olc(gold: Sequence[Sequence[Any]],
        tahmin: dict[str, Optional[str]]) -> dict[str, Any]:
    """Sınıf başına bire-karşı-hepsi sayaçları + özet.

    Kayıtlar 3 ya da 4 elemanlı olabilir (bkz. `_gold_yukle`); dördüncü alan
    `source_url` yalnız tahmin üretiminde kullanılır, metrikte yer almaz.
    """
    tablo = {sinif: Counts() for sinif in CAMPAIGN_TYPES}
    dogru = cekimser = 0
    karisiklik: Counter[tuple[str, str]] = Counter()

    for kayit in gold:
        doc_id, gercek = kayit[0], kayit[2]
        pred = tahmin.get(doc_id)
        if pred is None:
            # Çekimserlik: doğru sınıf için FN, hiçbir sınıf için FP değil.
            cekimser += 1
            tablo[gercek].fn += 1
            karisiklik[(gercek, "(çekimser)")] += 1
            continue
        if pred == gercek:
            dogru += 1
            tablo[gercek].tp += 1
        else:
            tablo[gercek].fn += 1
            if pred in tablo:
                tablo[pred].fp += 1
            karisiklik[(gercek, pred)] += 1

    return {
        "n": len(gold),
        "dogru": dogru,
        "cekimser": cekimser,
        "accuracy": dogru / len(gold) if gold else 0.0,
        "macro_f1": macro_f1(tablo),
        "tablo": tablo,
        "karisiklik": karisiklik,
    }


def _yazdir(ad: str, s: dict[str, Any]) -> None:
    print(f"\n=== {ad} ===")
    print(f"n={s['n']}  doğru={s['dogru']}  çekimser={s['cekimser']}")
    print(f"accuracy = {s['accuracy']:.3f}")
    print(f"macro-F1 = {s['macro_f1']:.3f}")
    print(f"\n{'sınıf':<22}{'destek':>7}{'P':>8}{'R':>8}{'F1':>8}")
    for sinif in CAMPAIGN_TYPES:
        c = s["tablo"][sinif]
        if c.support == 0 and c.fp == 0:
            continue
        print(f"{sinif:<22}{c.support:>7}{c.precision():>8.3f}"
              f"{c.recall():>8.3f}{c.f1():>8.3f}")

    if s["karisiklik"]:
        print("\nkarışıklıklar (gerçek -> tahmin):")
        for (g, p), n in s["karisiklik"].most_common(10):
            print(f"  {g} -> {p}: {n}")


def main(argv: Optional[list[str]] = None) -> int:
    ap = argparse.ArgumentParser(
        description="Kampanya türü sınıflandırmasını gold üzerinde ölç")
    ap.add_argument("--gold", default="data/gold/gold.v1.json")
    ap.add_argument("--predictions",
                    help="JSONL: {doc_id, label}. Verilmezse kural çizgisi.")
    ap.add_argument("--name", default="model", help="rapordaki ad")
    ap.add_argument("--compare", action="store_true",
                    help="kural çizgisini de koş ve yan yana bas")
    ap.add_argument("--out", help="özeti JSON olarak yaz")
    args = ap.parse_args(argv)

    gold = _gold_yukle(args.gold)
    if not gold:
        print("HATA: gold içinde campaign_type taşıyan kayıt yok.")
        return 2

    print(f"Gold: {len(gold)} belge, "
          f"{len({k[2] for k in gold})} farklı sınıf")
    if len(gold) < GUVENILIR_N:
        print(f"UYARI: n={len(gold)} < {GUVENILIR_N}. Sınıf başına ortalama "
              f"{len(gold) / len(CAMPAIGN_TYPES):.1f} örnek düşüyor; makro-F1 "
              f"tek belgenin gidip gelmesiyle oynar.\n"
              f"       Bu sayı bir SIRALAMA sinyalidir, kesin performans "
              f"ölçüsü değil.")

    sonuclar: dict[str, dict[str, Any]] = {}

    if args.predictions:
        tahmin = _tahminleri_yukle(args.predictions)
        eksik = [d for d, _, _ in gold if d not in tahmin]
        if eksik:
            # Eksik tahmini "çekimser" saymak modeli kayırırdı; sessiz de
            # geçilmez, çünkü kapsam metriğin bir parçası.
            print(f"\nUYARI: {len(eksik)} gold belgesi için tahmin YOK; "
                  f"çekimser sayılacak. Örnek: {eksik[:3]}")
        sonuclar[args.name] = olc(gold, tahmin)

    if args.compare or not args.predictions:
        sonuclar["kural"] = olc(gold, _kural_tahminleri(gold))

    for ad, s in sonuclar.items():
        _yazdir(ad, s)

    if len(sonuclar) > 1:
        print(f"\n{'kol':<14}{'accuracy':>10}{'macro-F1':>10}{'çekimser':>10}")
        for ad, s in sonuclar.items():
            print(f"{ad:<14}{s['accuracy']:>10.3f}{s['macro_f1']:>10.3f}"
                  f"{s['cekimser']:>10}")
        adlar = list(sonuclar)
        fark = sonuclar[adlar[0]]["macro_f1"] - sonuclar[adlar[1]]["macro_f1"]
        print(f"\nmakro-F1 farkı ({adlar[0]} - {adlar[1]}): {fark:+.3f}")
        if abs(fark) < 0.05:
            print("Fark n=20'de gürültüden ayırt edilemez; kazanan ilan etme.")

    if args.out:
        ozet = {ad: {k: v for k, v in s.items()
                     if k not in ("tablo", "karisiklik")}
                for ad, s in sonuclar.items()}
        os.makedirs(os.path.dirname(os.path.abspath(args.out)) or ".",
                    exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as fh:
            json.dump(ozet, fh, ensure_ascii=False, indent=2)
        print(f"\nözet -> {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
