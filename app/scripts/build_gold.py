"""Gold set derleyici — doldurulmuş CSV'ler -> `data/gold/gold.v1.json` (+ sha256).

İlgili: scripts/gold_schema.py (şema + kanonik doğrulama)
        scripts/to_review_csv.py (girdi CSV'lerini üretir)
        data/gold/ANNOTATION_GUIDE.md §3 (verdict anlamları)

Kullanım:
    python3 -m scripts.build_gold --csv-dir data/gold/review --out data/gold/gold.v1.json

## Verdict -> gold eşlemesi

    (boş) / ok  model değeri doğru.  Model değer ürettiyse -> `fields`
                Model HİÇBİR ŞEY üretmediyse -> `absent_fields`
                ("kontrol ettim, bu belgede yok")
    fix         `gold_value` kanonik biçime çevrilir -> `fields`
    absent      alan bu belgede YOK -> `absent_fields`  (model ürettiyse: FP)
    unclear     karar verilemedi -> `unclear_fields`, metrik DIŞI, hakemliğe düşer

`verdict` boş ama `gold_value` doluysa `fix` varsayılır: anotatör düzeltmeyi
yazıp verdict sütununu atlamıştır; bu düzeltmeyi sessizce çöpe atmak, elle
girilmiş en değerli veriyi kaybetmek olur.

## Çift anotasyon ve çelişki

Aynı (belge, alan) birden çok CSV'de geçiyorsa kararlar KARŞILAŞTIRILIR:
hemfikirlerse uygulanır, ayrışırlarsa alan `unclear_fields`'a düşer ve kayıt
`needs_adjudication: true` işaretlenir. Çelişki gizlenmez, otomatik de
çözülmez — hangi tarafın haklı olduğuna insan karar verir (CLAUDE.md HARD
RULE #4 ile aynı ilke).
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Optional

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from scripts.gold_schema import (  # noqa: E402
    CAMPAIGN_TYPE_KEY,
    EXTRACTION_FIELDS,
    GoldRecord,
    GoldValidationError,
    extract_hard_tags,
    parse_gold_value,
    validate_gold,
    values_equal,
    write_gold,
)
from scripts.to_review_csv import CSV_DELIMITER, CSV_ENCODING  # noqa: E402

DEFAULT_OUT = "data/gold/gold.v1.json"
DEFAULT_REPORT = "data/gold/build_report.md"
DEFAULT_EXCLUDED = "data/gold/excluded.json"

_ANNOTATOR_RE = re.compile(r"^round\d*_(?:main_|kalibrasyon_)?(.+)$", re.IGNORECASE)


def infer_annotator(path: str | Path) -> str:
    """Dosya adından anotatör adı: `round1_main_C.csv` -> `C`."""
    stem = Path(path).stem
    match = _ANNOTATOR_RE.match(stem)
    return (match.group(1) if match else stem).strip() or stem


# --------------------------------------------------------------------------- #
# CSV okuma
# --------------------------------------------------------------------------- #
class BuildError(Exception):
    """Anotatöre gösterilecek, konumu belli hata."""

    def __init__(self, file: str, line: int, doc_id: str, field: str, message: str):
        self.file, self.line = file, line
        self.doc_id, self.field = doc_id, field
        self.message = message
        super().__init__(str(self))

    def __str__(self) -> str:
        return (f"{self.file}:{self.line} [{self.doc_id} / {self.field}] "
                f"{self.message}")


def read_review_csv(path: str | Path) -> list[dict]:
    """Doldurulmuş inceleme CSV'sini okur; satır numarasını `_line` olarak taşır."""
    rows: list[dict] = []
    with Path(path).open("r", encoding=CSV_ENCODING, newline="") as handle:
        reader = csv.DictReader(handle, delimiter=CSV_DELIMITER)
        missing = {"doc_id", "field", "verdict"} - set(reader.fieldnames or [])
        if missing:
            raise ValueError(
                f"{path}: CSV başlığında şu sütunlar yok: {sorted(missing)}. "
                f"Dosya `scripts/to_review_csv.py` ile üretilmiş olmalı "
                f"(ayırıcı '{CSV_DELIMITER}', kodlama UTF-8 BOM).")
        for line, row in enumerate(reader, start=2):
            row["_line"] = line
            row["_file"] = str(path)
            rows.append(row)
    return rows


# --------------------------------------------------------------------------- #
# Karar çözümleme
# --------------------------------------------------------------------------- #
def _clean(value: Optional[str]) -> str:
    return (value or "").strip()


def resolve_decision(row: dict, model_value: Any, has_model_value: bool
                     ) -> tuple[str, Any]:
    """Tek satırı `(karar, değer)` ikilisine çevirir.

    karar: "value" | "absent" | "unclear"

    Raises:
        BuildError: `gold_value` kanonik biçime çevrilemezse.
    """
    verdict = _clean(row.get("verdict")).casefold()
    gold_raw = _clean(row.get("gold_value"))
    field = _clean(row.get("field"))

    # Verdict boş ama düzeltme yazılmış -> fix (bkz. modül başlığı).
    if not verdict and gold_raw:
        verdict = "fix"
    if not verdict:
        verdict = "ok"

    if verdict not in ("ok", "fix", "absent", "unclear"):
        raise BuildError(row["_file"], row["_line"], row.get("doc_id", ""), field,
                         f"verdict {verdict!r} tanınmıyor. İzin verilenler: "
                         f"(boş)=ok, ok, fix, absent, unclear")

    if verdict == "unclear":
        return ("unclear", None)
    if verdict == "absent":
        return ("absent", None)

    if verdict == "fix":
        if not gold_raw:
            raise BuildError(row["_file"], row["_line"], row.get("doc_id", ""), field,
                             "verdict=fix verildi ama gold_value boş. Doğru değeri "
                             "yaz ya da verdict'i absent/unclear yap.")
        try:
            return ("value", parse_gold_value(field, gold_raw))
        except GoldValidationError as exc:
            raise BuildError(row["_file"], row["_line"], row.get("doc_id", ""),
                             field, str(exc)) from exc

    # verdict == "ok"
    if has_model_value:
        return ("value", model_value)
    # Model hiçbir şey üretmedi + anotatör onayladı = "kontrol ettim, YOK".
    return ("absent", None)


# --------------------------------------------------------------------------- #
# Derleme
# --------------------------------------------------------------------------- #
def build(pre_path: str, csv_paths: list[str]) -> dict[str, Any]:
    """CSV'leri ön-anotasyonla birleştirip gold kayıtları üretir."""
    pre = json.loads(Path(pre_path).read_text(encoding="utf-8"))
    docs = {d["id"]: d for d in pre["docs"]}

    errors: list[BuildError] = []
    # (doc_id, field) -> [(annotator, karar, deger, not)]
    decisions: dict[tuple[str, str], list[tuple[str, str, Any, str]]] = defaultdict(list)
    doc_annotators: dict[str, list[str]] = defaultdict(list)
    unknown_docs: Counter = Counter()

    for csv_path in csv_paths:
        annotator = infer_annotator(csv_path)
        for row in read_review_csv(csv_path):
            doc_id = _clean(row.get("doc_id"))
            field = _clean(row.get("field"))
            if doc_id not in docs:
                unknown_docs[doc_id] += 1
                continue
            if field != CAMPAIGN_TYPE_KEY and field not in EXTRACTION_FIELDS:
                errors.append(BuildError(row["_file"], row["_line"], doc_id, field,
                                         f"bilinmeyen alan {field!r}"))
                continue

            if field == CAMPAIGN_TYPE_KEY:
                model_value = docs[doc_id].get(CAMPAIGN_TYPE_KEY)
                has_model_value = model_value is not None
            else:
                payload = (docs[doc_id].get("fields") or {}).get(field)
                has_model_value = payload is not None
                model_value = payload.get("value") if payload else None

            try:
                kind, value = resolve_decision(row, model_value, has_model_value)
            except BuildError as exc:
                errors.append(exc)
                continue

            decisions[(doc_id, field)].append(
                (annotator, kind, value, _clean(row.get("note"))))
            if annotator not in doc_annotators[doc_id]:
                doc_annotators[doc_id].append(annotator)

    records, excluded, conflicts = _assemble(docs, decisions, doc_annotators)
    return {
        "records": records,
        "excluded": excluded,
        "conflicts": conflicts,
        "errors": errors,
        "unknown_docs": unknown_docs,
        "csv_files": list(csv_paths),
    }


def _merge_decisions(entries: list[tuple[str, str, Any, str]]
                     ) -> tuple[str, Any, bool]:
    """Bir alandaki anotatör kararlarını birleştirir.

    Returns:
        (karar, değer, çelişki_var_mı)
    """
    kinds = {kind for _, kind, _, _ in entries}

    if "unclear" in kinds:
        return ("unclear", None, len(kinds) > 1)
    if len(kinds) > 1:
        # Biri "değer var" diyor, diğeri "yok" diyor -> insana kalır.
        return ("unclear", None, True)

    kind = kinds.pop()
    if kind == "absent":
        return ("absent", None, False)

    values = [value for _, _, value, _ in entries]
    first = values[0]
    if all(values_equal(first, other) for other in values[1:]):
        return ("value", first, False)
    return ("unclear", None, True)


def _assemble(docs: dict[str, dict],
              decisions: dict[tuple[str, str], list],
              doc_annotators: dict[str, list[str]]
              ) -> tuple[list[GoldRecord], list[dict], list[dict]]:
    """Kararları `GoldRecord` listesine dönüştürür."""
    by_doc: dict[str, dict[str, list]] = defaultdict(dict)
    for (doc_id, field), entries in decisions.items():
        by_doc[doc_id][field] = entries

    records: list[GoldRecord] = []
    excluded: list[dict] = []
    conflicts: list[dict] = []

    for doc_id in sorted(by_doc):
        doc = docs[doc_id]
        per_field = by_doc[doc_id]

        # 1) Kampanya türü — `absent` = "bu belge bir kampanya DEĞİL".
        campaign_type = None
        type_entries = per_field.pop(CAMPAIGN_TYPE_KEY, None)
        if type_entries:
            kind, value, clash = _merge_decisions(type_entries)
            if clash:
                conflicts.append({"doc_id": doc_id, "field": CAMPAIGN_TYPE_KEY,
                                  "entries": [(a, k, v) for a, k, v, _ in type_entries]})
            if kind == "absent":
                excluded.append({
                    "id": doc_id,
                    "bank_slug": doc.get("bank_slug"),
                    "source_url": doc.get("source_url"),
                    "reason": "kampanya_degil",
                    "detail": "campaign_type=absent — anotatör bu belgeyi kampanya "
                              "metni saymadı (menü/kurumsal sayfa vb.).",
                })
                continue
            if kind == "value":
                campaign_type = value

        record = GoldRecord(
            id=doc_id,
            text=doc.get("text", ""),
            bank_slug=doc.get("bank_slug"),
            source_url=doc.get("source_url"),
            content_hash=doc.get("content_hash"),
            campaign_type=campaign_type,
            annotators=sorted(doc_annotators.get(doc_id, [])),
        )

        hard_tags: list[str] = []
        for field in EXTRACTION_FIELDS:
            entries = per_field.get(field)
            if not entries:
                continue

            for _, _, _, note in entries:
                for tag in extract_hard_tags(note):
                    if tag not in hard_tags:
                        hard_tags.append(tag)
                if note:
                    prev = record.notes.get(field, "")
                    record.notes[field] = f"{prev} | {note}".strip(" |") if prev else note

            kind, value, clash = _merge_decisions(entries)
            if clash:
                conflicts.append({"doc_id": doc_id, "field": field,
                                  "entries": [(a, k, v) for a, k, v, _ in entries]})
            if kind == "value":
                record.fields[field] = value
            elif kind == "absent":
                record.absent_fields.append(field)
            else:
                record.unclear_fields.append(field)

        record.hard_tags = hard_tags
        record.needs_adjudication = bool(record.unclear_fields)
        records.append(record)

    return records, excluded, conflicts


# --------------------------------------------------------------------------- #
# Rapor
# --------------------------------------------------------------------------- #
def write_report(path: str | Path, result: dict, records: list[GoldRecord],
                 digest: str, out_path: str) -> None:
    """`data/gold/build_report.md` — neyin ölçülebilir olduğunu açıkça yazar."""
    full = [r for r in records if r.coverage() == len(EXTRACTION_FIELDS)]
    field_values: Counter = Counter()
    field_absent: Counter = Counter()
    field_unclear: Counter = Counter()
    for record in records:
        # .keys() ZORUNLU: Counter.update(dict) değerleri sayı sanıp toplar.
        field_values.update(record.fields.keys())
        field_absent.update(record.absent_fields)
        field_unclear.update(record.unclear_fields)

    hard_counter: Counter = Counter()
    for record in records:
        hard_counter.update(record.hard_tags)

    double = [r for r in records if len(r.annotators) > 1]

    lines = [
        "# Gold Derleme Raporu",
        "",
        "> `scripts/build_gold.py` üretti. Elle düzenlemeyin.",
        "",
        f"- Çıktı: `{out_path}`",
        f"- SHA-256: `{digest}`",
        f"- Kayıt: **{len(records)}**",
        f"- Çift anote edilmiş kayıt: **{len(double)}**",
        f"- 12/12 alan karara bağlı (recall ÖLÇÜLEBİLİR): **{len(full)}**",
        f"- Kampanya sayılmayıp elenen belge: **{len(result['excluded'])}**",
        f"- Çelişki (anotatörler ayrıştı): **{len(result['conflicts'])}**",
        f"- Hakemlik bekleyen kayıt: "
        f"**{sum(1 for r in records if r.needs_adjudication)}**",
        "",
        "## Ölçülebilirlik",
        "",
        "- **Precision + halüsinasyon oranı:** tüm kayıtlarda ölçülebilir — "
        "modelin ürettiği her alan için karar var.",
        "- **Recall:** yalnızca 12/12 kapsanan "
        f"{len(full)} kayıtta ölçülebilir; diğerlerinde anote edilmemiş alan "
        "ile gerçekten olmayan alan ayrılamaz.",
        "",
        "## Alan bazında",
        "",
        "| Alan | değer | yok (absent) | belirsiz |",
        "|---|---:|---:|---:|",
    ]
    for field in EXTRACTION_FIELDS:
        lines.append(f"| `{field}` | {field_values[field]} | {field_absent[field]} "
                     f"| {field_unclear[field]} |")

    lines += ["", "## Zor-vaka etiketleri", ""]
    if hard_counter:
        lines += ["| Etiket | Kayıt |", "|---|---:|"]
        for tag, count in hard_counter.most_common():
            lines.append(f"| `{tag}` | {count} |")
    else:
        lines.append("_Henüz etiket yok (not sütununa `#terminoloji` gibi hashtag yazın)._")

    if result["conflicts"]:
        lines += ["", "## Çelişkiler — HAKEMLİK GEREKİYOR", "",
                  "| Belge | Alan | Kararlar |", "|---|---|---|"]
        for conflict in result["conflicts"][:200]:
            entries = "; ".join(f"{a}={k}:{v!r}" for a, k, v in conflict["entries"])
            lines.append(f"| `{conflict['doc_id']}` | `{conflict['field']}` | {entries} |")

    unclear_rows = [(r.id, f) for r in records for f in sorted(r.unclear_fields)]
    if unclear_rows:
        lines += ["", "## Belirsiz (unclear) alanlar", "",
                  "Metrik hesabının DIŞINDA tutulur.", "",
                  "| Belge | Alan |", "|---|---|"]
        for doc_id, field in unclear_rows[:200]:
            lines.append(f"| `{doc_id}` | `{field}` |")

    if result["excluded"]:
        lines += ["", "## Elenen belgeler (kampanya değil)", "",
                  "| Belge | Banka |", "|---|---|"]
        for item in result["excluded"]:
            lines.append(f"| `{item['id']}` | {item.get('bank_slug') or ''} |")

    Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Doldurulmuş inceleme CSV'lerinden gold.v1.json üretir.")
    parser.add_argument("--pre", default="data/gold/preannotations.json")
    parser.add_argument("--csv", action="append", default=[],
                        help="doldurulmuş CSV (birden çok kez verilebilir)")
    parser.add_argument("--csv-dir", default=None,
                        help="klasördeki tüm round*.csv dosyalarını al")
    parser.add_argument("--out", default=DEFAULT_OUT)
    parser.add_argument("--report", default=DEFAULT_REPORT)
    parser.add_argument("--excluded-out", default=DEFAULT_EXCLUDED)
    parser.add_argument("--allow-errors", action="store_true",
                        help="hatalı satırları atlayıp devam et (varsayılan: durdur)")
    args = parser.parse_args(argv)

    csv_paths = list(args.csv)
    if args.csv_dir:
        csv_paths += [str(p) for p in sorted(Path(args.csv_dir).glob("round*.csv"))]
    if not csv_paths:
        parser.error("en az bir CSV gerekli (--csv ya da --csv-dir)")

    result = build(args.pre, csv_paths)
    errors: list[BuildError] = result["errors"]

    if errors:
        print(f"\n{len(errors)} HATALI SATIR:\n", file=sys.stderr)
        for error in errors[:50]:
            print(f"  {error}", file=sys.stderr)
        if len(errors) > 50:
            print(f"  … ve {len(errors) - 50} tane daha", file=sys.stderr)
        if not args.allow_errors:
            print("\nDüzeltip tekrar koşun ya da --allow-errors ile atlayın.",
                  file=sys.stderr)
            return 1

    records: list[GoldRecord] = result["records"]
    schema_errors = validate_gold(records)
    if schema_errors:
        print(f"\n{len(schema_errors)} ŞEMA HATASI:\n", file=sys.stderr)
        for message in schema_errors[:50]:
            print(f"  {message}", file=sys.stderr)
        if not args.allow_errors:
            return 1

    digest = write_gold(records, args.out)
    Path(args.excluded_out).write_text(
        json.dumps(result["excluded"], ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8")
    write_report(args.report, result, records, digest, args.out)

    full = sum(1 for r in records if r.coverage() == len(EXTRACTION_FIELDS))
    print(f"gold yazıldı: {args.out}")
    print(f"  kayıt              : {len(records)}")
    print(f"  12/12 kapsanan     : {full}")
    print(f"  elenen (kampanya değil): {len(result['excluded'])}")
    print(f"  çelişki            : {len(result['conflicts'])}")
    print(f"  sha256             : {digest}")
    print(f"rapor: {args.report}")
    if result["unknown_docs"]:
        print(f"UYARI: {len(result['unknown_docs'])} bilinmeyen doc_id atlandı "
              f"(ön-anotasyonda yok).", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
