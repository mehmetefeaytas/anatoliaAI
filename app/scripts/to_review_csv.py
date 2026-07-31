"""İnceleme CSV'si üretici — ön-anotasyon -> alan-başına-satır Excel dosyaları.

İlgili: data/gold/ANNOTATION_GUIDE.md (anotatörün okuyacağı kılavuz)
        scripts/preannotate.py (girdi), scripts/build_gold.py (çıktıyı okur)

Kullanım:
    python3 -m scripts.to_review_csv --duplicate-subset 50 --calibration 20 --seed 42

## Tasarım kısıtı: darboğaz İNSAN ZAMANI

4 kişi × ~1,5 saat = ~360 kişi-dakika. 250 belge × 12 alan = 3.000 karar.
Her karara eşit zaman ayrılamaz; ayrılmamalı da. İki kaldıraç kullanılır:

**1) Boş hücre = "model doğru".** `verdict` boş bırakılırsa `ok` sayılır. Yüksek
güvenli satırların çoğu doğrudur; anotatör onlara HİÇ dokunmaz. Tuş yalnızca
hata için harcanır.

**2) Bilgi yoğunluğuna göre sıralama.** Satırlar şu kova sırasıyla dizilir:

    kova 0  anlaşmazlık (kural ≠ LLM)   -> etiket başına en çok bilgi
    kova 1  düşük/orta güven [0.50, 0.90)
    kova 2  çok düşük güven (< 0.50)
    kova 3  yüksek güven (>= 0.90)       -> toplu onaylanabilir
    kova 4  modelin BULAMADIĞI alanlar   -> recall kontrolü, belge belge gruplu

Zaman biterse kesilen yer kova 3-4'ün kuyruğudur; oradaki kayıp en ucuzudur.

## Kova 4 ve `absent_fields`

Modelin hiçbir şey üretmediği alan için satır olmazsa anotatör "kontrol ettim,
YOK" diyemez — ve `absent_fields` boş kalır, precision tanımsızlaşır
(bkz. scripts/gold_schema.py modül başlığı). Bu yüzden kova 4 vardır.

Ama 250 belge × ~8 boş alan = ~2.000 satır, bütçeyi tek başına yer. Varsayılan
uzlaşma: kova 4 satırları yalnızca `--absent-docs` (varsayılan 100) belgede
üretilir. Sonuç:
  - 250 belgenin TAMAMINDA precision + halüsinasyon oranı ölçülebilir
    (model bir değer üretti mi, doğru mu — kova 0-3 bunu kapsar),
  - 100 belgelik alt kümede AYRICA recall ölçülebilir (12/12 alan karara bağlı).
Hangi belgenin tam kapsandığı gold'da `fields ∪ absent_fields` sayısından
okunur; `build_gold.py` raporunda açıkça yazar.
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import re
import sys
from pathlib import Path
from typing import Any, Optional

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from scripts.gold_schema import (
    CAMPAIGN_TYPE_KEY,
    format_gold_value,
)
from src.extraction.llm.schema import EXTRACTION_FIELDS

# Görev tanımındaki sütun kümesi — SIRA DEĞİŞTİRİLMEZ (build_gold başlıkla okur).
COLUMNS = [
    "doc_id", "bank", "field", "model_value", "model_conf", "confidence_source",
    "disagreement", "snippet", "gold_value", "verdict", "note",
]

# TR Excel varsayılanı: ayırıcı ';', kodlama UTF-8 BOM'lu.
CSV_DELIMITER = ";"
CSV_ENCODING = "utf-8-sig"
CSV_LINETERMINATOR = "\r\n"

DEFAULT_OUT_DIR = "data/gold/review"
DEFAULT_ANNOTATORS = "A,B,C,D"
SNIPPET_PAD = 120
CONTEXT_CHARS = 220

LOW_CONF = 0.50
HIGH_CONF = 0.90

_WS_RE = re.compile(r"\s+")
_FIELD_ORDER = {name: i for i, name in enumerate(EXTRACTION_FIELDS)}
_FIELD_ORDER[CAMPAIGN_TYPE_KEY] = -1   # tür etiketi belgenin çerçevesini kurar


# --------------------------------------------------------------------------- #
# Snippet
# --------------------------------------------------------------------------- #
def _flatten(text: str) -> str:
    """CSV hücresi için: satır sonları ve tekrarlı boşluklar tek boşluğa."""
    return _WS_RE.sub(" ", text).strip()


def build_snippet(text: str, payload: Optional[dict], pad: int = SNIPPET_PAD) -> str:
    """Değerin geçtiği yeri ±`pad` karakterlik pencerede, KÖŞELİ PARANTEZLE verir.

        "... kâr payı oranı [%1,89] ile 120 aya kadar ..."

    Anotatörün gözü değeri metinde aramak zorunda kalmasın diye. İşaretleme
    olmadan 120 karakterlik pencerede doğru sayıyı bulmak satır başına birkaç
    saniye ekler; 3.000 satırda bu saatlerdir.

    Model değer üretmediyse (kova 4) belgenin ilk cümleleri bağlam olarak verilir.
    """
    if not payload:
        return _flatten(text[:CONTEXT_CHARS]) + (" …" if len(text) > CONTEXT_CHARS else "")

    start, end = payload.get("span_start"), payload.get("span_end")
    if not (isinstance(start, int) and isinstance(end, int)
            and 0 <= start <= end <= len(text)):
        # Offset yoksa ham değeri metinde ara (LLM katmanı offset üretmeyebilir).
        needle = payload.get("raw_value") or payload.get("source_span")
        start = text.find(needle) if needle else -1
        if start < 0:
            return _flatten(text[:CONTEXT_CHARS]) + (" …" if len(text) > CONTEXT_CHARS else "")
        end = start + len(needle)

    left = max(0, start - pad)
    right = min(len(text), end + pad)
    marked = f"{text[left:start]}[{text[start:end]}]{text[end:right]}"
    prefix = "…" if left > 0 else ""
    suffix = "…" if right < len(text) else ""
    return _flatten(f"{prefix}{marked}{suffix}")


# --------------------------------------------------------------------------- #
# Satır üretimi
# --------------------------------------------------------------------------- #
def _bucket(payload: Optional[dict], low: float, high: float) -> int:
    """Satırın öncelik kovası (küçük = önce; bkz. modül başlığı)."""
    if payload is None:
        return 4
    if payload.get("disagreement"):
        return 0
    conf = float(payload.get("confidence") or 0.0)
    if conf >= high:
        return 3
    if conf >= low:
        return 1
    return 2


def rows_for_doc(doc: dict, include_absent: bool, low: float = LOW_CONF,
                 high: float = HIGH_CONF) -> list[dict]:
    """Bir belgenin tüm inceleme satırları (kova bilgisiyle birlikte)."""
    text = doc.get("text", "")
    bank = doc.get("bank_slug") or ""
    doc_id = doc["id"]
    fields: dict[str, Any] = doc.get("fields") or {}

    rows: list[dict] = []

    # 8-sınıf kampanya türü — BERTurk macro-F1'i buna dayanır (CLAUDE.md §16).
    type_payload = {
        "value": doc.get(CAMPAIGN_TYPE_KEY),
        "confidence": doc.get("campaign_type_confidence") or 0.0,
        "confidence_source": "classifier",
        "disagreement": False,
        "span_start": None, "span_end": None, "raw_value": None,
    }
    has_type = doc.get(CAMPAIGN_TYPE_KEY) is not None
    rows.append(_row(doc_id, bank, CAMPAIGN_TYPE_KEY,
                     type_payload if has_type else None, text, low, high))

    for name in EXTRACTION_FIELDS:
        payload = fields.get(name)
        if payload is None and not include_absent:
            continue
        rows.append(_row(doc_id, bank, name, payload, text, low, high))

    return rows


def _row(doc_id: str, bank: str, field: str, payload: Optional[dict],
         text: str, low: float, high: float) -> dict:
    bucket = _bucket(payload, low, high)
    if payload is None:
        model_value, conf, source, disagreement = "", "", "", ""
    else:
        model_value = format_gold_value(field, payload.get("value"))
        conf_value = payload.get("confidence")
        conf = f"{float(conf_value):.2f}" if conf_value is not None else ""
        source = payload.get("confidence_source") or ""
        disagreement = "EVET" if payload.get("disagreement") else ""

    return {
        "_bucket": bucket,
        "_field_order": _FIELD_ORDER.get(field, 99),
        "doc_id": doc_id,
        "bank": bank,
        "field": field,
        "model_value": model_value,
        "model_conf": conf,
        "confidence_source": source,
        "disagreement": disagreement,
        "snippet": build_snippet(text, payload),
        "gold_value": "",
        "verdict": "",
        "note": "",
    }


def sort_rows(rows: list[dict]) -> list[dict]:
    """Kova -> belge -> alan sırası. Kova birinci: zaman biterse ucuz olan kesilir."""
    return sorted(rows, key=lambda r: (r["_bucket"], r["doc_id"], r["_field_order"]))


def write_csv(rows: list[dict], path: str | Path) -> int:
    """Satırları TR-Excel uyumlu CSV'ye yazar. Dönen değer: satır sayısı."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding=CSV_ENCODING, newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS,
                                delimiter=CSV_DELIMITER,
                                lineterminator=CSV_LINETERMINATOR,
                                extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
    return len(rows)


# --------------------------------------------------------------------------- #
# Belge paylaştırma
# --------------------------------------------------------------------------- #
def partition(doc_ids: list[str], calibration: int, duplicate: int, seed: int
              ) -> tuple[list[str], list[str], list[str]]:
    """Belgeleri (kalibrasyon, çift-anotasyon, ana) olarak deterministik böler.

    Üçü AYRIK kümedir: aynı belge iki kez anote edilip iki kez saydırılmaz.
    """
    rng = random.Random(seed)
    shuffled = sorted(doc_ids)
    rng.shuffle(shuffled)

    calib = sorted(shuffled[:calibration])
    dup = sorted(shuffled[calibration:calibration + duplicate])
    main = sorted(shuffled[calibration + duplicate:])
    return calib, dup, main


def balance_main(main: list[str], annotators: list[str], row_counts: dict[str, int],
                 fixed_load: list[int]) -> dict[str, list[str]]:
    """Ana kümeyi, herkesin TOPLAM SATIR yükü eşitlenecek şekilde paylaştırır.

    Belge sayısına göre bölmek yanıltıcıdır: kalibrasyon ve çift-anotasyon
    belgelerinde 12/12 alan karara bağlandığı için belge başına ~13 satır çıkar,
    ana kümede ise ~5. Belge sayısı eşitlenirse A ve B'nin gerçek yükü diğerlerinin
    iki katı olur ve Cuma turu yarım kalır. Zamanın gerçek vekili SATIRdır.

    Yöntem: en büyük belgeden başlayarak, o an en az yüklü kişiye ata (LPT).

    Args:
        row_counts: belge -> üreteceği satır sayısı.
        fixed_load: her anotatörün kalibrasyon + çift anotasyondan gelen sabit
            satır yükü (sırası `annotators` ile aynı).
    """
    count = len(annotators)
    if count == 0:
        return {}

    assignment: dict[str, list[str]] = {name: [] for name in annotators}
    totals = list(fixed_load)

    # Büyük belgeleri önce yerleştirmek (LPT), sondaki dengesizliği küçültür.
    for doc_id in sorted(main, key=lambda d: (-row_counts.get(d, 0), d)):
        target = min(range(count), key=lambda i: (totals[i], i))
        assignment[annotators[target]].append(doc_id)
        totals[target] += row_counts.get(doc_id, 0)

    for name in assignment:
        assignment[name].sort()
    return assignment


# --------------------------------------------------------------------------- #
# Ana akış
# --------------------------------------------------------------------------- #
def generate(pre_path: str, out_dir: str, annotators: list[str],
             calibration: int, duplicate: int, absent_docs: int, seed: int,
             low: float = LOW_CONF, high: float = HIGH_CONF) -> dict[str, Any]:
    """Tüm CSV'leri, belge metinlerini ve atama planını üretir."""
    data = json.loads(Path(pre_path).read_text(encoding="utf-8"))
    docs = {d["id"]: d for d in data["docs"]}
    doc_ids = list(docs)

    calib, dup, main = partition(doc_ids, calibration, duplicate, seed)

    # Kova 4 (recall kontrolü) hangi belgelerde açılacak — deterministik seçim.
    rng = random.Random(seed + 1)
    pool = sorted(doc_ids)
    rng.shuffle(pool)
    if absent_docs < 0 or absent_docs >= len(pool):
        absent_set = set(pool)
    else:
        # Kalibrasyon ve çift-anotasyon belgeleri ÖNCELİKLİ: IAA'nın `absent`
        # kararında da ölçülebilmesi için tam kapsama orada en değerlidir.
        priority = [d for d in pool if d in set(calib) | set(dup)]
        rest = [d for d in pool if d not in set(calib) | set(dup)]
        absent_set = set((priority + rest)[:absent_docs])

    def build(ids: list[str]) -> list[dict]:
        rows: list[dict] = []
        for doc_id in ids:
            rows.extend(rows_for_doc(docs[doc_id], doc_id in absent_set, low, high))
        return sort_rows(rows)

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    # ESKİ TURDAN KALAN CSV'LER SİLİNİR. Aksi halde farklı parametrelerle
    # (ör. başka bir --duplicate-subset) üretilmiş dosyalar klasörde kalır;
    # `build_gold --csv-dir` bunları `round*.csv` kalıbıyla toplayıp aynı
    # belgeyi iki kez sayar ve olmayan "çelişki"ler üretir.
    for stale in out.glob("round*.csv"):
        stale.unlink()

    written: dict[str, int] = {}

    # 1) Kalibrasyon turu — HERKES aynı belgeleri anote eder (Fleiss kappa).
    if calib:
        calib_rows = build(calib)
        for name in annotators:
            written[f"round0_kalibrasyon_{name}.csv"] = write_csv(
                calib_rows, out / f"round0_kalibrasyon_{name}.csv")

    # 2) Çift anotasyon alt kümesi — A ve B aynı belgeleri (Cohen kappa).
    if dup and len(annotators) >= 2:
        dup_rows = build(dup)
        written["round1_A.csv"] = write_csv(dup_rows, out / "round1_A.csv")
        written["round1_B.csv"] = write_csv(dup_rows, out / "round1_B.csv")

    # 3) Ana küme — SATIR yüküne göre dengeli paylaştırma, kişi başına bir dosya.
    row_counts = {
        doc_id: len(rows_for_doc(docs[doc_id], doc_id in absent_set, low, high))
        for doc_id in doc_ids
    }
    calib_rows_total = sum(row_counts[d] for d in calib)
    dup_rows_total = sum(row_counts[d] for d in dup)
    fixed_load = [
        calib_rows_total + (dup_rows_total if i < 2 and dup else 0)
        for i in range(len(annotators))
    ]
    assignment = balance_main(main, annotators, row_counts, fixed_load)
    for name, ids in assignment.items():
        if ids:
            written[f"round1_main_{name}.csv"] = write_csv(
                build(ids), out / f"round1_main_{name}.csv")

    # 4) Belge metinleri — anotatör kova 4'te tam metni okumak zorunda.
    docs_dir = out / "belgeler"
    docs_dir.mkdir(parents=True, exist_ok=True)
    for doc_id, doc in docs.items():
        (docs_dir / f"{doc_id}.txt").write_text(doc.get("text", ""), encoding="utf-8")

    # Kişi başına gerçek satır yükü — Cuma planının tek anlamlı sayısı.
    row_load = {
        name: (calib_rows_total
               + (dup_rows_total if i < 2 and dup else 0)
               + sum(row_counts[d] for d in assignment.get(name, [])))
        for i, name in enumerate(annotators)
    }

    plan = {
        "seed": seed,
        "annotators": annotators,
        "calibration": calib,
        "duplicate": dup,
        "assignment": {name: ids for name, ids in assignment.items()},
        "absent_docs": sorted(absent_set),
        "row_load": row_load,
        "files": written,
    }
    (out / "_plan.json").write_text(
        json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    _write_assignment_md(out / "_atama.md", plan, written, len(docs))
    return plan


def _write_assignment_md(path: Path, plan: dict, written: dict[str, int],
                         doc_total: int) -> None:
    """Cuma sabahı ekrana yansıtılacak tek sayfalık atama planı."""
    annotators = plan["annotators"]
    lines = [
        "# Anotasyon Atama Planı",
        "",
        "> `scripts/to_review_csv.py` üretti. Elle düzenlemeyin — yeniden koşuda "
        "üzerine yazılır.",
        "",
        f"- Toplam belge: **{doc_total}**",
        f"- Kalibrasyon (herkes aynı): **{len(plan['calibration'])}** belge",
        f"- Çift anotasyon (A + B): **{len(plan['duplicate'])}** belge",
        f"- Tam kapsama (12/12 alan karara bağlı): **{len(plan['absent_docs'])}** belge",
        f"- Rastgelelik tohumu (seed): `{plan['seed']}`",
        "",
        "## Kim neyi açacak",
        "",
        "| Anotatör | 1. Kalibrasyon | 2. Çift anotasyon | 3. Ana küme | Toplam satır |",
        "|---|---|---|---|---:|",
    ]
    for i, name in enumerate(annotators):
        calib_file = f"`round0_kalibrasyon_{name}.csv`" if plan["calibration"] else "—"
        if i == 0 and plan["duplicate"]:
            dup_file = "`round1_A.csv`"
        elif i == 1 and plan["duplicate"]:
            dup_file = "`round1_B.csv`"
        else:
            dup_file = "—"
        main_ids = plan["assignment"].get(name) or []
        main_file = (f"`round1_main_{name}.csv` ({len(main_ids)} belge)"
                     if main_ids else "—")
        load = plan.get("row_load", {}).get(name, 0)
        lines.append(f"| {name} | {calib_file} | {dup_file} | {main_file} | {load} |")

    lines += [
        "",
        "## Sıra ÖNEMLİ",
        "",
        "1. **Kalibrasyon turu birlikte yapılır.** Herkes aynı 20 belgeyi anote eder, "
        "`scripts/report_iaa.py` koşulur, uyuşmazlıklar 15 dakika konuşulur, "
        "kılavuz düzeltilir. Bu adım ATLANIRSA ana turdaki uyuşmazlıkların "
        "yarısı kılavuz belirsizliğinden çıkar ve gold yeniden yapılır.",
        "2. Çift anotasyon (A ve B) — kappa buradan hesaplanır.",
        "3. Ana küme — herkes kendi dosyasını doldurur.",
        "",
        "## Üretilen dosyalar",
        "",
        "| Dosya | Satır |",
        "|---|---:|",
    ]
    for name in sorted(written):
        lines.append(f"| `{name}` | {written[name]} |")
    lines += [
        "",
        "Belge tam metinleri: `belgeler/<doc_id>.txt`",
        "",
        "Kılavuz: [`../ANNOTATION_GUIDE.md`](../ANNOTATION_GUIDE.md) — "
        "**anotasyona başlamadan okunacak.**",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Ön-anotasyondan alan-başına-satır inceleme CSV'leri üretir.")
    parser.add_argument("--pre", default="data/gold/preannotations.json")
    parser.add_argument("--out-dir", default=DEFAULT_OUT_DIR)
    parser.add_argument("--annotators", default=DEFAULT_ANNOTATORS,
                        help="virgülle ayrılmış anotatör adları (varsayılan A,B,C,D)")
    parser.add_argument("--calibration", type=int, default=20,
                        help="kalibrasyon turu belge sayısı (herkes aynısını anote eder)")
    parser.add_argument("--duplicate-subset", type=int, default=50,
                        help="çift anote edilecek belge sayısı (kappa için)")
    parser.add_argument("--absent-docs", type=int, default=100,
                        help="kaç belgede 12/12 alan karara bağlansın (-1 = hepsi)")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--low", type=float, default=LOW_CONF)
    parser.add_argument("--high", type=float, default=HIGH_CONF)
    args = parser.parse_args(argv)

    annotators = [a.strip() for a in args.annotators.split(",") if a.strip()]
    plan = generate(args.pre, args.out_dir, annotators, args.calibration,
                    args.duplicate_subset, args.absent_docs, args.seed,
                    args.low, args.high)

    total_rows = sum(plan["files"].values())
    print(f"CSV'ler yazıldı: {args.out_dir}")
    for name in sorted(plan["files"]):
        print(f"  {name:<34} {plan['files'][name]:>6} satır")
    print(f"  {'TOPLAM':<34} {total_rows:>6} satır")
    print(f"atama planı: {Path(args.out_dir) / '_atama.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
