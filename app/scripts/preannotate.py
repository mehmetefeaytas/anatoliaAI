"""Ön-anotasyon üretici — `data/raw/` -> hibrit çıkarım -> ön-anotasyon JSON.

İlgili: CLAUDE.md §3 (önce kural sonra LLM), §16 (gold set), §19 (halüsinasyon yasağı)
        scripts/to_review_csv.py (bu çıktıyı insan-okur CSV'ye çevirir)

Kullanım (offline, kural-only):
    python3 -m scripts.preannotate --limit 250 --seed 42

LLM de devrede (anlaşmazlık sinyali için):
    LLM_BACKEND=ollama python3 -m scripts.preannotate --limit 250 --seed 42

## Neden ön-anotasyon

Sıfırdan anotasyon belge başına ~4-6 dakikadır; model çıktısını DOĞRULAMAK
~1 dakikadır. 250 belge × 12 alan elle yazılamaz. Model önce doldurur, insan
onaylar/düzeltir. Riski de var: anotatör model çıktısına demirlenir (anchoring).
Kılavuz bunu iki şekilde kırar — snippet'te değerin GEÇTİĞİ YER işaretlenir
(anotatör metne bakmak zorunda) ve düşük güvenli/anlaşmazlıklı satırlar CSV'nin
başına alınır.

## Anlaşmazlık (disagreement) sinyali

`reconcile()` LLM'e YALNIZCA kuralların bulamadığı alanları sorar; bu üretim
için doğru (token tasarrufu) ama anotasyon için körlük yaratır: iki katmanın
AYNI alanda farklı değer üretmesi, hatanın en yoğun olduğu yerdir. Burada
bilerek her iki katman da 12 alanın TAMAMI için koşturulur ve ayrışma
`disagreement: true` ile işaretlenir. Bu satırlar CSV'de ilk sırada gelir —
etiket başına en çok bilgi orada.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from scripts.gold_schema import (  # noqa: E402
    CAMPAIGN_TYPE_KEY,
    GOLD_SCHEMA_VERSION,
    values_equal,
)
from src.extraction.llm.extractor import default_extractor  # noqa: E402
from src.extraction.llm.schema import EXTRACTION_FIELDS  # noqa: E402
from src.extraction.ner.classifier import default_classifier  # noqa: E402
from src.extraction.rules.extract import extract_all as rule_extract  # noqa: E402
from src.preprocessing.clean import normalize_text  # noqa: E402
from src.schemas import ExtractedField  # noqa: E402

DEFAULT_RAW_DIR = "data/raw"
DEFAULT_OUT = "data/gold/preannotations.json"
# Çok kısa metinler kampanya değil, menü/gezinme artığıdır; anotatör zamanını
# yer ve gold'u kirletir.
DEFAULT_MIN_CHARS = 250


@dataclass
class RawDoc:
    """Ham belgenin anotasyona hazır hâli."""

    doc_id: str
    bank_slug: str
    text: str
    source_url: Optional[str] = None
    content_hash: Optional[str] = None
    scraped_at: Optional[str] = None
    title: Optional[str] = None
    path: Optional[str] = None


# --------------------------------------------------------------------------- #
# Ham veri okuma (data/raw SALT OKUNUR — buraya asla yazılmaz)
# --------------------------------------------------------------------------- #
def read_raw_docs(raw_dir: str | Path, min_chars: int = DEFAULT_MIN_CHARS
                  ) -> list[RawDoc]:
    """`data/raw/<banka>/{live,manual}/*.txt` belgelerini okur.

    `.txt.meta.json` varsa provenance (source_url, content_hash, scraped_at)
    oradan alınır. İçerik hash'i ile tekilleştirme yapılır: aynı sayfa iki
    kez toplanmışsa gold'a iki kez girmemeli (metrik şişer).
    """
    root = Path(raw_dir)
    if not root.is_dir():
        raise FileNotFoundError(f"ham veri klasörü yok: {root}")

    docs: list[RawDoc] = []
    seen_hashes: set[str] = set()

    for bank_dir in sorted(p for p in root.iterdir() if p.is_dir()):
        bank_slug = bank_dir.name
        for txt_path in sorted(bank_dir.rglob("*.txt")):
            raw_text = txt_path.read_text(encoding="utf-8", errors="replace")
            text = normalize_text(raw_text)
            if len(text) < min_chars:
                continue

            meta: dict[str, Any] = {}
            meta_path = Path(f"{txt_path}.meta.json")
            if meta_path.is_file():
                try:
                    meta = json.loads(meta_path.read_text(encoding="utf-8"))
                except ValueError:
                    meta = {}

            content_hash = meta.get("content_hash")
            dedupe_key = content_hash or text
            if dedupe_key in seen_hashes:
                continue
            seen_hashes.add(dedupe_key)

            docs.append(RawDoc(
                doc_id=f"{bank_slug}--{txt_path.stem}"[:120],
                bank_slug=meta.get("bank_slug") or bank_slug,
                text=text,
                source_url=meta.get("source_url"),
                content_hash=content_hash,
                scraped_at=meta.get("scraped_at"),
                title=meta.get("title"),
                path=str(txt_path.relative_to(_ROOT)) if txt_path.is_relative_to(_ROOT)
                else str(txt_path),
            ))
    return docs


# §5.7'nin karşılaştırma kriterlerini besleyen, korpusta SEYREK alanlar.
# 849 belgede: kar_payi_orani 54 · tahsis_ucreti 28 · vade_ay 337.
NADIR_ALANLAR = ("kar_payi_orani", "tahsis_ucreti")
ORTA_ALANLAR = ("vade_ay", "finansman_tutari")


def _katman(doc: RawDoc) -> int:
    """Belgeyi değerine göre katmana ayırır (0 = en değerli).

    Katman 0: kâr payı oranı veya tahsis ücreti içerir. Bunlar korpusun
              yalnızca %6'sında var ve şartnamenin manşet karşılaştırmasını
              (§5.7 "En Düşük Kâr Payı") besleyen tek kaynak.
    Katman 1: vade veya finansman tutarı içerir.
    Katman 2: kalanlar (indirim/puan/ödül kampanyaları, kurumsal sayfalar).
    """
    from src.extraction.rules.extract import extract_all

    adlar = {f.field_name for f in extract_all(doc.text)}
    if adlar & set(NADIR_ALANLAR):
        return 0
    if adlar & set(ORTA_ALANLAR):
        return 1
    return 2


def sample_docs(docs: list[RawDoc], limit: Optional[int], seed: int) -> list[RawDoc]:
    """KATMANLI + bankalar arası dengeli, deterministik örnekleme.

    İki sorunu birden çözer:

    1. **Düz rastgele seçim seyrek alanları kaçırır.** 849 belgenin yalnızca
       54'ünde kâr payı oranı var. Rastgele 250 seçilirse yaklaşık 16'sı
       gelir ve dört kişinin Cuma günkü emeği ağırlıkla alışveriş indirimi
       anote etmeye gider — oysa %30'luk "Model Başarısı" kalemi §5.7'nin
       karşılaştırma kriterlerine dayanıyor.
       Çözüm: kâr payı / tahsis ücreti içeren belgeler ÖNCE alınır.

    2. **Düz rastgele seçim büyük bankayı küçüğe ezdirir.** Her katmanın
       içinde banka bazında round-robin yapılır, böylece gold tek bankanın
       diline aşırı uymaz.

    `seed` ile tekrar üretilebilir.
    """
    if limit is None or limit >= len(docs):
        return sorted(docs, key=lambda d: d.doc_id)

    rng = random.Random(seed)
    havuz: dict[int, list[RawDoc]] = {0: [], 1: [], 2: []}
    for doc in docs:
        havuz[_katman(doc)].append(doc)

    # KATMAN 2 İÇİN KOTA. Yalnız katman 0+1 alınırsa korpus tamamen
    # finansman olur ve 8 sınıflı sınıflandırıcıyı değerlendirecek Kart /
    # Alışveriş Puanı / Yeni Müşteri örneği KALMAZ. Şartname üç ürün
    # kategorisini de (finansman, kart, yatırım) istiyor, bu yüzden
    # kalanın ~%25'i katman 2'ye ayrılır ve KAMPANYA TÜRÜNE göre dengelenir.
    kota2 = max(0, int(round((limit - len(havuz[0])) * 0.25)))

    picked: list[RawDoc] = []
    picked += _round_robin(havuz[0], limit - len(picked), rng,
                           anahtar=lambda d: d.bank_slug)
    picked += _round_robin(havuz[1], limit - len(picked) - kota2, rng,
                           anahtar=lambda d: d.bank_slug)
    # Katman 2 kampanya TÜRÜNE göre dengelenir (bankaya göre değil):
    # buradaki amaç sınıf çeşitliliği.
    picked += _round_robin(havuz[2], limit - len(picked), rng,
                           anahtar=_kampanya_turu)
    return sorted(picked, key=lambda d: d.doc_id)


def _kampanya_turu(doc: RawDoc) -> str:
    from src.extraction.ner.classifier import RuleHintClassifier

    return RuleHintClassifier().classify(doc.text)[0] or "(sinifsiz)"


def _round_robin(docs: list[RawDoc], n: int, rng, anahtar) -> list[RawDoc]:
    """`anahtar` fonksiyonuna göre gruplayıp sırayla n belge toplar.

    Round-robin, büyük grubun küçüğü ezmesini engeller: bankaya göre
    çağrılırsa 90 belgeli banka 6 belgeliyi bastırmaz, kampanya türüne göre
    çağrılırsa baskın tür diğer sınıfları silmez.
    """
    if n <= 0 or not docs:
        return []
    gruplar: dict[str, list[RawDoc]] = {}
    for d in docs:
        gruplar.setdefault(anahtar(d), []).append(d)
    for bucket in gruplar.values():
        bucket.sort(key=lambda d: d.doc_id)
        rng.shuffle(bucket)

    out: list[RawDoc] = []
    adlar = sorted(gruplar)
    while len(out) < n and any(gruplar[a] for a in adlar):
        for ad in adlar:
            if gruplar[ad] and len(out) < n:
                out.append(gruplar[ad].pop())
    return out


# --------------------------------------------------------------------------- #
# Çıkarım
# --------------------------------------------------------------------------- #
def _field_payload(f: ExtractedField) -> dict[str, Any]:
    return {
        "value": f.canonical_value,
        "raw_value": f.raw_value,
        "confidence": round(float(f.confidence), 4),
        "confidence_source": f.confidence_source,
        "extractor": f.extractor.value,
        "source_span": f.source_span,
        "span_start": f.span_start,
        "span_end": f.span_end,
        "span_verified": f.verify_span(f.source_span or ""),
    }


def annotate_doc(doc: RawDoc, llm, classifier) -> dict[str, Any]:
    """Tek belge için ön-anotasyon kaydı üretir (kural + varsa LLM)."""
    text = doc.text

    rule_fields = {f.field_name: f for f in rule_extract(text) if f.is_present}

    llm_fields: dict[str, ExtractedField] = {}
    if getattr(llm, "available", False):
        # BİLEREK 12 alanın tamamı sorulur (reconcile'ın aksine): anlaşmazlık
        # ancak iki katman aynı alanı da ürettiğinde görülebilir.
        for f in llm.extract(text, list(EXTRACTION_FIELDS)):
            if f.is_present:
                llm_fields[f.field_name] = f

    fields: dict[str, Any] = {}
    for name in EXTRACTION_FIELDS:
        rule_f = rule_fields.get(name)
        llm_f = llm_fields.get(name)
        if rule_f is None and llm_f is None:
            continue

        # Katman önceliği reconcile.py ile aynı: kural birincil.
        winner = rule_f or llm_f
        payload = _field_payload(winner)
        payload["disagreement"] = bool(
            rule_f is not None and llm_f is not None
            and not values_equal(rule_f.canonical_value, llm_f.canonical_value)
        )
        payload["rule_value"] = rule_f.canonical_value if rule_f else None
        payload["llm_value"] = llm_f.canonical_value if llm_f else None
        fields[name] = payload

    campaign_type, type_conf = classifier.classify(text)

    return {
        "id": doc.doc_id,
        "bank_slug": doc.bank_slug,
        "source_url": doc.source_url,
        "content_hash": doc.content_hash,
        "scraped_at": doc.scraped_at,
        "title": doc.title,
        "path": doc.path,
        "text": text,
        CAMPAIGN_TYPE_KEY: campaign_type,
        "campaign_type_confidence": round(float(type_conf), 4),
        "fields": fields,
        # Modelin HİÇBİR ŞEY üretmediği alanlar: recall kontrolü için CSV'ye
        # ayrı satır olarak düşerler (boş bırakılırsa `absent_fields`'a girer).
        "missing_fields": [n for n in EXTRACTION_FIELDS if n not in fields],
    }


def preannotate(raw_dir: str = DEFAULT_RAW_DIR, limit: Optional[int] = None,
                seed: int = 42, min_chars: int = DEFAULT_MIN_CHARS
                ) -> dict[str, Any]:
    """Ham veriyi okur, çıkarımı koşar, ön-anotasyon sözlüğü döndürür."""
    docs = sample_docs(read_raw_docs(raw_dir, min_chars=min_chars), limit, seed)

    llm = default_extractor()
    classifier = default_classifier()

    records = [annotate_doc(doc, llm, classifier) for doc in docs]

    field_count = sum(len(r["fields"]) for r in records)
    disagreements = sum(
        1 for r in records for p in r["fields"].values() if p["disagreement"]
    )
    return {
        "schema_version": GOLD_SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "raw_dir": str(raw_dir),
        "seed": seed,
        "llm_available": bool(getattr(llm, "available", False)),
        "llm_mode": getattr(llm, "structured_mode", None),
        "doc_count": len(records),
        "field_count": field_count,
        "disagreement_count": disagreements,
        "docs": records,
    }


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="data/raw belgelerinden ön-anotasyon üretir (offline çalışır).")
    parser.add_argument("--raw-dir", default=DEFAULT_RAW_DIR)
    parser.add_argument("--out", default=DEFAULT_OUT)
    parser.add_argument("--limit", type=int, default=250,
                        help="kaç belge örneklenecek (bankalar arası dengeli)")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--min-chars", type=int, default=DEFAULT_MIN_CHARS)
    args = parser.parse_args(argv)

    limit = None if args.limit is not None and args.limit <= 0 else args.limit
    result = preannotate(raw_dir=args.raw_dir, limit=limit, seed=args.seed,
                         min_chars=args.min_chars)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                        encoding="utf-8")

    banks = sorted({r["bank_slug"] for r in result["docs"]})
    per_doc = result["field_count"] / result["doc_count"] if result["doc_count"] else 0
    print(f"ön-anotasyon yazıldı: {out_path}")
    print(f"  belge          : {result['doc_count']} ({len(banks)} banka)")
    print(f"  dolu alan      : {result['field_count']} (belge başına {per_doc:.1f}/12)")
    print(f"  anlaşmazlık    : {result['disagreement_count']}")
    print(f"  LLM            : {'açık' if result['llm_available'] else 'KAPALI (kural-only)'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
