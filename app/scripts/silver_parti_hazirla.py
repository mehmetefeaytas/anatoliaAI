"""Round1 inceleme CSV'lerinde KARAR VERİLMEMİŞ satırlardan gümüş etiket partisi üretir.

İlgili: scripts/build_silver.py (8-sınıf gümüş hattı — ayrı kapsam, aynı felsefe)
        src/extraction/silver/contract.py (JSONL sözleşmesi)
        scripts/build_gold.py (ALTIN hattı — bu partiyle KARIŞMAZ)
        data/gold/ANNOTATION_GUIDE.md §3 (verdict anlamları)

## Neden ayrı bir hat

`build_silver` yalnız **kampanya türünü** (8 sınıf) etiketler; burada eksik
kalan şey **12 alanın tamamıdır**. Round1 turunda dört anotatör 1795 (belge,
alan) hücresinden 368'ini karara bağladı; kalan 1427'si v2 protokolünde
"karar verilmedi" sayılır ve gold'a GİRMEZ. O hücreler boş kaldığı sürece ne
recall ölçülebilir ne de sınıflandırıcı eğitilebilir.

## Gümüş ALTIN DEĞİLDİR — karışması yasak

Bu partiden çıkan etiketler `data/silver/` altında kalır ve `build_gold`'un
okuduğu `data/gold/review/*.csv` dosyalarına **yazılmaz**. Gerekçe ölçülmüştür:
gold modelin çıktısına çapalıyken mikro-F1 0,677, kör protokolde 0,536 —
aradaki 0,141 protokol artefaktıydı (ANNOTATION_GUIDE §3.1). Bir modelin
ürettiği etiketi gold'a koyup aynı modeli onunla ölçmek bu artefaktın daha
büyüğünü üretir.

Gümüş etiketin meşru kullanımı: sınıflandırıcı/çıkarıcı EĞİTİMİ ve kapsama
analizi. Ölçüm (`eval/run_eval.py`) gold'dan okur, buradan değil.

## Parti biçimi

Belge başına tek kayıt üretilir — etiketleyici belgeyi bir kez okur, o
belgenin tüm boş alanlarını birlikte karara bağlar. Alan alan sormak aynı
metni onlarca kez okutur ve tutarsız kararlar üretir.

Kullanım:
    .venv/bin/python -m scripts.silver_parti_hazirla \\
        --out data/silver/round1_parti.jsonl

    # yalnız ilk 5 belge (pilot)
    .venv/bin/python -m scripts.silver_parti_hazirla --limit 5 --out ...
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from scripts.to_review_csv import CSV_DELIMITER, CSV_ENCODING

#: Round1 turunun dört dosyası. Kaynak CSV'ler (`.kaynak-tasindi`) ve yedekler
#: DIŞARIDA: kararları zaten bu dördüne taşındı, yeniden okumak çift sayardır.
VARSAYILAN_CSVLER = (
    "round1_A.csv", "round1_B.csv", "round1_main_C.csv", "round1_main_D.csv",
)

BELGE_DIZINI = "data/gold/review/belgeler"
VARSAYILAN_CIKTI = "data/silver/round1_parti.jsonl"


def bos_hucreler(review_dizini: Path, dosyalar: tuple[str, ...]) -> tuple[dict, dict]:
    """Karar verilmemiş `(doc_id, field)` hücrelerini toplar.

    Bir hücre **hiçbir** dosyada karara bağlanmamışsa gümüş adayıdır. Tek bir
    anotatörün kararı bile varsa hücre insanındır ve partiye alınmaz.
    """
    kararli: set[tuple[str, str]] = set()
    aday: dict[tuple[str, str], dict] = {}
    banka: dict[str, str] = {}

    for ad in dosyalar:
        yol = review_dizini / ad
        if not yol.exists():
            continue
        with yol.open(encoding=CSV_ENCODING, newline="") as fh:
            for satir in csv.DictReader(fh, delimiter=CSV_DELIMITER):
                doc = (satir.get("doc_id") or "").strip()
                alan = (satir.get("field") or "").strip()
                if not doc or not alan:
                    continue
                banka.setdefault(doc, (satir.get("bank") or "").strip())
                if (satir.get("verdict") or "").strip():
                    kararli.add((doc, alan))
                    continue
                # Aynı hücre birden çok dosyada olabilir; model çıktısı aynıdır.
                aday.setdefault((doc, alan), {
                    "field": alan,
                    "model_value": (satir.get("model_value") or "").strip(),
                    "model_conf": (satir.get("model_conf") or "").strip(),
                    "confidence_source": (satir.get("confidence_source") or "").strip(),
                    "snippet": (satir.get("snippet") or "").strip(),
                })

    return {k: v for k, v in aday.items() if k not in kararli}, banka


def parti_uret(kok: Path, limit: int | None = None,
               dosyalar: tuple[str, ...] = VARSAYILAN_CSVLER) -> list[dict]:
    review = kok / "data/gold/review"
    belgeler = kok / BELGE_DIZINI

    aday, banka = bos_hucreler(review, dosyalar)

    belge_alanlari: dict[str, list[dict]] = defaultdict(list)
    for (doc, _), bilgi in sorted(aday.items()):
        belge_alanlari[doc].append(bilgi)

    kayitlar = []
    for doc in sorted(belge_alanlari):
        metin_yolu = belgeler / f"{doc}.txt"
        if not metin_yolu.exists():
            # Metni olmayan belge etiketlenemez; sessizce atmak yerine sayılır.
            continue
        kayitlar.append({
            "doc_id": doc,
            "bank": banka.get(doc, ""),
            "metin_yolu": str(metin_yolu.relative_to(kok)),
            "metin_karakter": metin_yolu.stat().st_size,
            "alanlar": sorted(belge_alanlari[doc], key=lambda a: a["field"]),
        })
    return kayitlar[:limit] if limit else kayitlar


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", default=VARSAYILAN_CIKTI)
    ap.add_argument("--limit", type=int, default=None,
                    help="yalnız ilk N belge (pilot koşu)")
    args = ap.parse_args(argv)

    kayitlar = parti_uret(_ROOT, limit=args.limit)
    hedef = _ROOT / args.out
    hedef.parent.mkdir(parents=True, exist_ok=True)
    with hedef.open("w", encoding="utf-8") as fh:
        for k in kayitlar:
            fh.write(json.dumps(k, ensure_ascii=False) + "\n")

    alan_sayisi = sum(len(k["alanlar"]) for k in kayitlar)
    karakter = sum(k["metin_karakter"] for k in kayitlar)
    print(f"parti yazıldı: {args.out}")
    print(f"  belge          : {len(kayitlar)}")
    print(f"  etiketlenecek  : {alan_sayisi} (belge, alan) hücresi")
    print(f"  metin hacmi    : {karakter/1024:.0f} KB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
