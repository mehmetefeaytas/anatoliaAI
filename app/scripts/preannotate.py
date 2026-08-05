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
import hashlib
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

from scripts.gold_schema import (
    CAMPAIGN_TYPE_KEY,
    GOLD_SCHEMA_VERSION,
    validate_canonical,
    values_equal,
)
from src.extraction.llm.extractor import default_extractor
from src.extraction.llm.schema import EXTRACTION_FIELDS
from src.extraction.ner.classifier import default_classifier
from src.extraction.rules.extract import extract_all as rule_extract
from src.preprocessing.clean import normalize_text
from src.schemas import ExtractedField

DEFAULT_RAW_DIR = "data/raw"
DEFAULT_OUT = "data/gold/preannotations.json"
# Çok kısa metinler kampanya değil, menü/gezinme artığıdır; anotatör zamanını
# yer ve gold'u kirletir.
DEFAULT_MIN_CHARS = 250
# Korpus onarımında "içeriği yok, yalnız gezinme iskeleti" diye işaretlenen
# belgelerin meta değeri (bkz. data/raw/_reextract_report.md).
SHELL_STATUS = "kabuk"


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
def _read_meta(txt_path: Path) -> dict[str, Any]:
    """`<belge>.txt.meta.json` provenance dosyasını okur (yoksa boş sözlük)."""
    meta_path = Path(f"{txt_path}.meta.json")
    if not meta_path.is_file():
        return {}
    try:
        loaded = json.loads(meta_path.read_text(encoding="utf-8"))
    except ValueError:
        return {}
    return loaded if isinstance(loaded, dict) else {}


def _unique_doc_id(bank_slug: str, txt_path: Path, taken: set[str]) -> str:
    """Çakışmayan `doc_id` üretir.

    `<banka>--<dosya adı>` TEKİL DEĞİL: aynı sayfa `live/` ve `products/`
    altında ayrı dosya olarak duruyor. v1'de 1.678 belgenin 88'i aynı kimliği
    paylaşıyordu; `to_review_csv` girdiyi `{d["id"]: d}` sözlüğüne çevirdiği
    için bunlar SESSİZCE düşüyordu (plan 250 belge diyor, `_atama.md` 243).
    Metin farklıysa üstelik hangi metnin kaldığı da rastgele oluyordu:
    anotatör bir belgenin snippet'ini, başka bir belgenin tam metniyle
    doğrulamaya çalışırdı.

    Çakışmada klasör adı kimliğe girer (`--products-`), gerekirse sayaç eklenir.
    """
    base = f"{bank_slug}--{txt_path.stem}"[:120]
    if base not in taken:
        return base
    scoped = f"{bank_slug}--{txt_path.parent.name}-{txt_path.stem}"[:120]
    if scoped not in taken:
        return scoped
    for n in range(2, 100):
        candidate = f"{scoped[:116]}-{n}"
        if candidate not in taken:
            return candidate
    raise RuntimeError(f"doc_id çakışması çözülemedi: {txt_path}")


def read_raw_docs(raw_dir: str | Path, min_chars: int = DEFAULT_MIN_CHARS,
                  skip_shell: bool = True) -> list[RawDoc]:
    """`data/raw/<banka>/{live,manual}/*.txt` belgelerini okur.

    `.txt.meta.json` varsa provenance (source_url, content_hash, scraped_at)
    oradan alınır. Aynı sayfa iki kez toplanmışsa gold'a iki kez girmemeli
    (metrik şişer), bu yüzden tekilleştirme yapılır — ölçütü NORMALİZE METİN,
    çünkü `content_hash` ham HTML'in hash'idir ve aynı içerik iki farklı
    kaynak yolundan (ör. `live/` + `products/`) geldiğinde HTML farklı, metin
    aynı olur. v1 ön-anotasyonunda 250 kayıttan 7'si tam bu yüzden çift girdi.

    `skip_shell` açıkken `content_status: kabuk` işaretli belgeler atlanır:
    bunlar gezinme menüsünden ibaret sayfalardır, 1-2 KB metinle `min_chars`
    eşiğini geçerler ama 12 alanın 12'si `absent` çıkar — anotatör zamanının
    tam kaybı.
    """
    root = Path(raw_dir)
    if not root.is_dir():
        raise FileNotFoundError(f"ham veri klasörü yok: {root}")

    docs: list[RawDoc] = []
    seen_hashes: set[str] = set()
    seen_ids: set[str] = set()

    for bank_dir in sorted(p for p in root.iterdir() if p.is_dir()):
        bank_slug = bank_dir.name
        for txt_path in sorted(bank_dir.rglob("*.txt")):
            meta = _read_meta(txt_path)
            if skip_shell and meta.get("content_status") == SHELL_STATUS:
                continue

            raw_text = txt_path.read_text(encoding="utf-8", errors="replace")
            text = normalize_text(raw_text)
            if len(text) < min_chars:
                continue

            content_hash = meta.get("content_hash")
            text_key = hashlib.sha256(text.encode("utf-8")).hexdigest()
            if text_key in seen_hashes or (content_hash and content_hash in seen_hashes):
                continue
            seen_hashes.add(text_key)
            if content_hash:
                seen_hashes.add(content_hash)

            doc_id = _unique_doc_id(bank_slug, txt_path, seen_ids)
            seen_ids.add(doc_id)

            docs.append(RawDoc(
                doc_id=doc_id,
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


def sample_docs(docs: list[RawDoc], limit: Optional[int], seed: int,
                pinned: frozenset[str] = frozenset()) -> list[RawDoc]:
    """KATMANLI + bankalar arası dengeli, deterministik örnekleme.

    `pinned` içindeki `doc_id`'ler örneklemeye KOŞULSUZ girer (kota içinden
    sayılır). Gerekçe: korpus büyüyünce aynı `seed` bile farklı bir örneklem
    verir; halihazırda insan tarafından anote edilmiş belgeler örneklemden
    düşerse o emek ölçülemez hâle gelir (kalibrasyon turunun Fleiss kappa'sı
    A'yı diğer üçüyle karşılaştırılamaz kılar).

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
    picked: list[RawDoc] = [d for d in docs if d.doc_id in pinned]

    havuz: dict[int, list[RawDoc]] = {0: [], 1: [], 2: []}
    for doc in docs:
        if doc.doc_id in pinned:
            continue
        havuz[_katman(doc)].append(doc)

    # KATMAN 2 İÇİN KOTA. Yalnız katman 0+1 alınırsa korpus tamamen
    # finansman olur ve 8 sınıflı sınıflandırıcıyı değerlendirecek Kart /
    # Alışveriş Puanı / Yeni Müşteri örneği KALMAZ. Şartname üç ürün
    # kategorisini de (finansman, kart, yatırım) istiyor, bu yüzden
    # kalanın ~%25'i katman 2'ye ayrılır ve KAMPANYA TÜRÜNE göre dengelenir.
    kota2 = max(0, int(round((limit - len(picked) - len(havuz[0])) * 0.25)))

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
def _field_payload(f: ExtractedField, text: str) -> dict[str, Any]:
    """Alanı JSON'a çevirir.

    `span_verified` TAM belge metnine karşı doğrulanır. Eskiden `f.source_span`
    (±40 karakterlik pencere DİZESİ) veriliyordu; `span_start`/`span_end` ise
    tam metne göre offset olduğu için doğrulama anlamsızdı ve alanların
    **%94,7'si `false`** çıkıyordu — doğru değerlerde bile.

    Doğru çağrıyla ölçüm: 60 belgede 196 alanın **196'sı** (%100) doğrulanıyor;
    eski çağrıyla %95,4'ü `false` çıkıyordu.

    NE OLMADIĞINA dikkat: bu bir halüsinasyon dedektörü DEĞİL. Krom kaynaklı 35
    `alisveris_puani` halüsinasyonunun span'leri **doğruydu** — `"10"` gerçekten
    o offset'teydi; yanlış olan yorumdu (gezinme bağlantısını ödül sanmak).
    Onlarda `span_verified: false` görünmesinin sebebi de halüsinasyon değil,
    işte bu hatalı çağrıydı. Yani bu alanı halüsinasyon kapısı yapmak yanlış
    olur; işi provenance doğruluğu.

    Neden yine de önemli: %95 `false` üreten bir "doğrulandı" alanı, yokluğundan
    daha kötüdür — sinyal gibi görünür, gürültüdür. Ayrıca CLAUDE.md §18'in
    yenilikçilik hedeflerinden biri **kaynak vurgulama** ve arayüzün doğru
    karakterleri işaretlemesi buna dayanıyor.

    Doğru çağrı biçimi zaten depoda vardı (`src/api/main.py:620`:
    `f.verify_span(text)`); iki çağrı yeri ayrışmıştı.
    """
    return {
        "value": f.canonical_value,
        "raw_value": f.raw_value,
        "confidence": round(float(f.confidence), 4),
        "confidence_source": f.confidence_source,
        "extractor": f.extractor.value,
        "source_span": f.source_span,
        "span_start": f.span_start,
        "span_end": f.span_end,
        "span_verified": f.verify_span(text),
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
    invalid_fields: dict[str, Any] = {}
    for name in EXTRACTION_FIELDS:
        rule_f = rule_fields.get(name)
        llm_f = llm_fields.get(name)
        if rule_f is None and llm_f is None:
            continue

        # Katman önceliği reconcile.py ile aynı: kural birincil.
        winner = rule_f or llm_f
        payload = _field_payload(winner, text)
        payload["disagreement"] = bool(
            rule_f is not None and llm_f is not None
            and not values_equal(rule_f.canonical_value, llm_f.canonical_value)
        )
        payload["rule_value"] = rule_f.canonical_value if rule_f else None
        payload["llm_value"] = llm_f.canonical_value if llm_f else None

        # ŞEMA DIŞI DEĞER, DEĞER SAYILMAZ. Kural katmanı ara sıra alanın
        # kanonik biçimini tutmayan bir değer üretiyor — en sık örnek
        # `tahsis_ucreti` için para yerine oran (`{"rate": 0.5}`: "tahsis
        # ücreti tutarın %0,5'i"). Bu değer `fields`'a girerse:
        #   1. CSV'ye ön-doldurulur ve boş verdict = ONAY sayılır,
        #   2. `build_gold` model değerini olduğu gibi gold'a yazar,
        #   3. hata en sonda `validate_gold` adımında patlar — anotasyon
        #      bittikten sonra, yani düzeltmesi en pahalı anda.
        # Bu yüzden değer burada AYRI tutulur: alan "model üretmedi" sayılır
        # (kural katmanının hatası gold'a sızmaz) ama kanıtı kaybolmaz —
        # `to_review_csv` bu kaydı span'i işaretli bir uyarı satırına çevirir,
        # anotatör metindeki yeri görüp doğru değeri yazabilir.
        schema_error = validate_canonical(name, payload["value"])
        if schema_error:
            payload["schema_error"] = schema_error
            invalid_fields[name] = payload
            continue
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
        # Şemaya uymadığı için DEĞER SAYILMAYAN çıkarımlar (yukarıdaki gerekçe).
        "invalid_fields": invalid_fields,
        # Modelin HİÇBİR ŞEY üretmediği alanlar: recall kontrolü için CSV'ye
        # ayrı satır olarak düşerler (boş bırakılırsa `absent_fields`'a girer).
        "missing_fields": [n for n in EXTRACTION_FIELDS if n not in fields],
    }


def read_pinned_ids(paths: list[str]) -> frozenset[str]:
    """İnceleme CSV'lerinden (ya da satır başına bir kimlik içeren düz metinden)
    örneklemde KALMASI gereken `doc_id`'leri toplar.

    Kullanımı: `--pin-csv data/gold/review/round0_kalibrasyon_A.csv`. Anote
    edilmiş bir dosyanın belgeleri yeni örneklemin dışında kalırsa o anotasyon
    hiçbir metriğe girmez.
    """
    from scripts.to_review_csv import read_doc_ids

    ids: set[str] = set()
    for raw_path in paths:
        ids |= read_doc_ids(raw_path)
    return frozenset(ids)


def preannotate(raw_dir: str = DEFAULT_RAW_DIR, limit: Optional[int] = None,
                seed: int = 42, min_chars: int = DEFAULT_MIN_CHARS,
                pinned: frozenset[str] = frozenset()) -> dict[str, Any]:
    """Ham veriyi okur, çıkarımı koşar, ön-anotasyon sözlüğü döndürür."""
    corpus = read_raw_docs(raw_dir, min_chars=min_chars)
    docs = sample_docs(corpus, limit, seed, pinned=pinned)
    secilen = {d.doc_id for d in docs}
    kayip = sorted(pinned - secilen)

    llm = default_extractor()
    classifier = default_classifier()

    records = [annotate_doc(doc, llm, classifier) for doc in docs]

    field_count = sum(len(r["fields"]) for r in records)
    invalid_count = sum(len(r["invalid_fields"]) for r in records)
    disagreements = sum(
        1 for r in records for p in r["fields"].values() if p["disagreement"]
    )
    return {
        "schema_version": GOLD_SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "raw_dir": str(raw_dir),
        "seed": seed,
        "min_chars": min_chars,
        "llm_available": bool(getattr(llm, "available", False)),
        "llm_mode": getattr(llm, "structured_mode", None),
        # Örneklem tekrar üretilebilirliği: korpus büyüdükçe aynı seed farklı
        # örneklem verir, bu yüzden havuz büyüklüğü de kayda geçer.
        "corpus_size": len(corpus),
        "doc_count": len(records),
        "field_count": field_count,
        # Şema dışı olduğu için değer sayılmayan çıkarımlar (kural katmanı hata
        # raporu olarak da okunabilir).
        "invalid_field_count": invalid_count,
        "disagreement_count": disagreements,
        "pinned_ids": sorted(pinned & secilen),
        # Sabitlenmesi istenip korpusta BULUNAMAYAN kimlikler. Sessizce
        # yutulmaz: o belgelerin anotasyonu artık hiçbir metriğe girmiyor.
        "pinned_missing": kayip,
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
    parser.add_argument("--pin-csv", action="append", default=[],
                        metavar="YOL",
                        help="bu inceleme CSV'sindeki belgeler örneklemde kalsın "
                             "(anote edilmiş dosyalar için; tekrarlanabilir)")
    args = parser.parse_args(argv)

    limit = None if args.limit is not None and args.limit <= 0 else args.limit
    pinned = read_pinned_ids(args.pin_csv) if args.pin_csv else frozenset()
    result = preannotate(raw_dir=args.raw_dir, limit=limit, seed=args.seed,
                         min_chars=args.min_chars, pinned=pinned)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                        encoding="utf-8")

    banks = sorted({r["bank_slug"] for r in result["docs"]})
    per_doc = result["field_count"] / result["doc_count"] if result["doc_count"] else 0
    print(f"ön-anotasyon yazıldı: {out_path}")
    print(f"  korpus         : {result['corpus_size']} belge (kabuk + kopya ayıklandı)")
    print(f"  belge          : {result['doc_count']} ({len(banks)} banka)")
    print(f"  dolu alan      : {result['field_count']} (belge başına {per_doc:.1f}/12)")
    print(f"  şema dışı alan : {result['invalid_field_count']} (değer sayılmadı, "
          f"CSV'de uyarı satırı)")
    print(f"  anlaşmazlık    : {result['disagreement_count']}")
    print(f"  LLM            : {'açık' if result['llm_available'] else 'KAPALI (kural-only)'}")
    if result["pinned_ids"]:
        print(f"  sabitlenen     : {len(result['pinned_ids'])} belge")
    if result["pinned_missing"]:
        print(f"  UYARI: sabitlenemedi (korpusta yok): {len(result['pinned_missing'])} "
              f"belge -> {result['pinned_missing'][:3]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
