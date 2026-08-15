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

## Kanıt (`field_spans`) — kaynağı ve SINIRI

Ölçüldü (2026-08-10): bu hattın çıktısı gold.v1.json'un **65 alanının
0'ında** kanıt vardı, çünkü betik `field_spans` üretmiyordu. Aynı anda
`merge_gold_v2.py` her alanda kanıt ŞART koşuyordu; iki hat sessizce
ayrışmıştı (bkz. `gold_schema` modül başlığı).

Kanıtın kaynağı **ön-anotasyondaki çıkarıcı konumudur**, inceleme CSV'si
değil. CSV'nin `snippet` sütunu kanıt taşıyamaz: `to_review_csv.build_snippet`
onu okunurluk için BOZAR — pencere kenarlarına `…`, değerin çevresine `[ ]`
koyar ve boşlukları düzler. Metinde birebir aranırsa hiçbiri bulunmaz.
Ön-anotasyon ise aynı pencerenin bozulmamış hâlini (`source_span`) ve tam
metne göre offset'ini (`span_start`/`span_end`) taşır.

Kanıt YALNIZCA şu üç koşul birden sağlanırsa yazılır:

  1. anotatörün onayladığı gold değeri, modelin ürettiği değerle AYNI
     (yani `verdict=ok` yolu — anotatör CSV'de gördüğü snippet'i onaylamıştır),
  2. offset'ler gerçekten o değeri gösteriyor (`text[start:end] == raw_value`),
  3. `source_span` metinde birebir geçiyor ve ham değeri İÇERİYOR.

`verdict=fix` değerlerinde kanıt **YAZILMAZ**. Anotatör düzeltilmiş bir
değer yazdı ama alıntı yazmadı; modelin konumu YANLIŞ değerin kanıtıdır,
düzeltilmişin değil. Kanonik değeri (`{"value": 500, "currency": "TRY"}`)
metinde geri arayıp bir yer "bulmak", kanıt üretmek değil kanıt UYDURMAKTIR
— ve tam olarak kapının engellemek için var olduğu şeydir. O alanlar
kanıtsız kalır, sayılır ve raporda tek tek listelenir.

Bu yüzden bu hattın kanıtı ile `merge_gold_v2` hattınınki aynı ağırlıkta
DEĞİLDİR ve rapor bunu yazar: orada alıntıyı anotatör kör olarak elle yazdı,
burada çıkarıcının kaydettiği konumu anotatör onayladı. İkisi de belgede
birebir geçer; ikincisi bağımsız bir gözlem değildir.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from collections import Counter, defaultdict
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from scripts.gold_schema import (
    CAMPAIGN_TYPE_KEY,
    EXTRACTION_FIELDS,
    PROTOCOL_V1,
    PROTOCOL_V2,
    SKIPPED_DECISION,
    GoldRecord,
    GoldValidationError,
    extract_hard_tags,
    fabrication_errors,
    parse_gold_value,
    row_protocol,
    span_supports,
    uncovered_fields,
    validate_gold,
    values_equal,
    write_gold,
)
from scripts.to_review_csv import CSV_DELIMITER, CSV_ENCODING

DEFAULT_OUT = "data/gold/gold.v1.json"
DEFAULT_REPORT = "data/gold/build_report.md"
DEFAULT_EXCLUDED = "data/gold/excluded.json"

_ANNOTATOR_RE = re.compile(r"^round\d*_(?:main_|kalibrasyon_)?(.+)$", re.IGNORECASE)


# --------------------------------------------------------------------------- #
# Hakemlik damgası -> `adjudicated`
# --------------------------------------------------------------------------- #
# `adjudicated` 2026-08-15'e kadar HİÇ set edilmiyordu: `gold.round1.json`'un
# 134/134 kaydı "hakemlik yapılmadı" diyordu, oysa round1'de 41 uyuşmazlık
# üçüncü bir gözden geçmişti. Bayrağın tek dürüst kaynağı, o geçişi hücreye
# yazan damgadır (`note` sütunu).
#
# Damga KİMİN karar verdiğini gizlemez: `hakemlik_uygula` kör MAKİNE hakemliği,
# `sema_onarimi_uygula` şema onarımıdır; ikisi de insan hakemliği DEĞİLDİR ve
# `notes` alanı gold'da olduğu gibi durur, okuyan ayırt edebilir.


@lru_cache(maxsize=1)
def hakemlik_damgalari() -> tuple[str, ...]:
    """Hakemlik/onarım damgalarının tek doğruluk kaynağı — damgayı YAZAN betikler.

    İçe aktarma neden gövdede: `hakemlik_uygula` -> `report_iaa` -> `build_gold`
    döngüsü var; modül başında import etmek `build_gold`u yarı kurulmuş hâlde
    yakalar ve `report_iaa`nın `infer_annotator` importu patlar. Sabiti buraya
    KOPYALAMAK da çözüm değil: bu depoda "aynı sabitin iki kopyası ayrışır"
    ölçülmüş bir hata sınıfıdır (bkz. `report_iaa` modül başlığı).
    """
    from scripts.hakemlik_uygula import DAMGA as HAKEMLIK_DAMGASI
    from scripts.sema_onarimi_uygula import DAMGA as SEMA_ONARIMI_DAMGASI

    return (HAKEMLIK_DAMGASI, SEMA_ONARIMI_DAMGASI)


@lru_cache(maxsize=1)
def _damga_re() -> re.Pattern[str]:
    """Damgaları TAM etiket olarak arayan desen.

    Kenarlıklar şart: `#hakemlik-round1` deseni çıplak arandığında
    `#hakemlik-round10` ya da `#hakemlik-round1-taslak` de eşleşir ve gold'a
    yanlış bayrak yazılır. Etiketin bittiği yerde harf/rakam/`_`/`-` olamaz;
    başladığı yerde de bir etiketin ortasına düşmüş olamaz.
    """
    govde = "|".join(re.escape(d) for d in hakemlik_damgalari())
    return re.compile(rf"(?<![\w#-])(?:{govde})(?![\w-])")


def hakemlik_damgali(note: Optional[str]) -> bool:
    """Not bir hakemlik/şema-onarımı damgası taşıyor mu?"""
    return bool(note) and _damga_re().search(note) is not None


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


def resolve_decision(row: dict) -> tuple[str, Any]:
    """Tek satırı `(karar, değer)` ikilisine çevirir.

    karar: "value" | "absent" | "unclear" | "skipped"

    `skipped` YALNIZCA v2 protokolünde çıkar: boş `verdict` + boş `gold_value`
    = "karar verilmedi". Gold'a girmez.

    Boş hücrenin anlamı satırın `protokol` sütunundan okunur
    (`gold_schema.row_protocol`, tek doğruluk kaynağı). Sütun yoksa v1 sayılır
    ve eski davranış korunur — geriye dönük hiçbir karar kaybolmaz.

    ## `ok` kararında değer SATIRIN KENDİ `model_value`'sundan okunur

    2026-08-15'e kadar bu fonksiyon ön-anotasyon havuzundan (`--pre`) gelen
    değeri alıyordu. Sonuç ölçüldü: **59 hücrede** (A 18 · B 19 · C 1 · D 21)
    gold'a, anotatörün EKRANDA HİÇ GÖRMEDİĞİ bir değer girdi.

    Mekanizma `scripts/onanotasyon_tazele.py` başlığında zaten yazılıydı:
    CSV'lerin `model_value` sütunu 8–9 Ağustos'ta bugünkü çıkarıcıyla tazelendi,
    `preannotations.v2.json` ise 4 Ağustos'tan kalmaydı. 42 tarih sürüklemesinin
    39'unda CSV bitiş tarihini (`2026-12-31`), havuz başlangıcı (`2026-01-01`)
    tutuyordu; 14 `kar_payi_orani` hücresinin 14'ünde de CSV boştu ama havuz
    `%50` gibi bir kâr PAYLAŞIM oranı taşıyordu (kılavuz §4.13/6 `absent` der).

    Anotatörün onayı gördüğü değere aittir. `ok` "ekranda okuduğum değer doğru"
    demektir; başka bir değeri onaylanmış saymak anotasyonu geçersiz kılar.
    Aynı kaynağı `report_iaa.row_value_token` da kullanıyor — bu düzeltme gold'u
    Krippendorff α ile aynı zemine oturtur.

    Raises:
        BuildError: `gold_value` ya da `model_value` kanonik biçime çevrilemezse.
    """
    verdict = _clean(row.get("verdict")).casefold()
    gold_raw = _clean(row.get("gold_value"))
    field = _clean(row.get("field"))

    # Verdict boş ama düzeltme yazılmış -> fix (bkz. modül başlığı).
    if not verdict and gold_raw:
        verdict = "fix"
    if not verdict:
        # v2: boş hücre onay DEĞİLDİR. Burayı `ok`a düşürmek, kılavuzun §3.1
        # ile kaldırdığı çapalamayı gold'un yazıldığı yerde geri getirirdi —
        # κ tarafı (report_iaa) protokolü sayarken derleyici saymazsa, ölçüm
        # dürüst, gold değil.
        if row_protocol(row) == PROTOCOL_V2:
            return (SKIPPED_DECISION, None)
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

    # verdict == "ok" -> anotatörün ONAYLADIĞI değer, yani EKRANDA GÖRDÜĞÜ değer.
    model_raw = _clean(row.get("model_value"))
    if not model_raw:
        # Model hiçbir şey üretmedi + anotatör onayladı = "kontrol ettim, YOK".
        return ("absent", None)
    try:
        return ("value", parse_gold_value(field, model_raw))
    except GoldValidationError as exc:
        # `fix` kolundaki kapının ikizi. Kanonik olmayan bir `model_value`
        # sessizce gold'a giremez; giderse ölçüm kendi çıktısını doğrular.
        raise BuildError(row["_file"], row["_line"], row.get("doc_id", ""),
                         field, f"verdict=ok ama model_value kanonik değil: "
                                f"{exc}") from exc


# --------------------------------------------------------------------------- #
# Kanıt türetme
# --------------------------------------------------------------------------- #
def kanit_alintisi(doc: dict, field: str, gold_value: Any) -> Optional[str]:
    """Alanın kanıt alıntısı — türetilemiyorsa `None` (uydurma YOK).

    Üç koşulun üçü de sağlanmazsa `None` döner; "yaklaşık doğru" bir alıntı
    yazmak yerine alan kanıtsız bırakılır. Gerekçe için modül başlığına bakın.

    `None` dönmesi kayıt için bir kusur değil, bir ÖLÇÜMDÜR: kaç alanın
    kanıtı, kaç alanın sadece iddiası var.
    """
    payload = (doc.get("fields") or {}).get(field)
    if not payload:
        # Model bu alanı hiç üretmedi -> gold değeri anotatörden geldi (fix).
        return None
    if not values_equal(payload.get("value"), gold_value):
        # Anotatör modeli DÜZELTTİ. Modelin konumu düzeltilmiş değerin kanıtı
        # değildir; onu kanıt diye yazmak kapıyı kandırmaktır.
        return None

    text = doc.get("text") or ""
    raw = payload.get("raw_value") or ""
    start, end = payload.get("span_start"), payload.get("span_end")
    if not (isinstance(start, int) and isinstance(end, int)):
        return None
    if not (0 <= start <= end <= len(text)) or not raw.strip():
        return None
    if text[start:end] != raw:
        # Offset kaymış: gösterilen yer ile raporlanan değer uyuşmuyor.
        # `ExtractedField.verify_span` ile aynı kontrol; ölçüldü, alanların
        # ~%4'ünde tutmuyor ve o alanlar kanıtsız kalır.
        return None

    alinti = payload.get("source_span") or ""
    # Alıntı ham değeri İÇERMELİ: değeri göstermeyen bir pencere, o değerin
    # kanıtı değildir — yalnızca belgeden rastgele bir cümledir.
    if raw not in alinti or not span_supports(text, alinti):
        return None
    return alinti


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
    # v2 protokolünde karar verilmemiş satırlar (anotatör başına).
    skipped: Counter = Counter()
    skipped_with_note: list[dict] = []
    protocols: dict[str, str] = {}

    for csv_path in csv_paths:
        annotator = infer_annotator(csv_path)
        rows = read_review_csv(csv_path)
        # Boş dosya: `row_protocol` ile aynı geriye dönük varsayım (v1).
        protocols[str(csv_path)] = row_protocol(rows[0]) if rows else PROTOCOL_V1
        for row in rows:
            doc_id = _clean(row.get("doc_id"))
            field = _clean(row.get("field"))
            if doc_id not in docs:
                unknown_docs[doc_id] += 1
                continue
            if field != CAMPAIGN_TYPE_KEY and field not in EXTRACTION_FIELDS:
                errors.append(BuildError(row["_file"], row["_line"], doc_id, field,
                                         f"bilinmeyen alan {field!r}"))
                continue

            # `--pre` havuzu burada ARTIK OKUNMUYOR: `ok` kararının değeri
            # satırın kendi `model_value`'sundan gelir (bkz. `resolve_decision`
            # docstring'i — 59 hücrede havuz ile CSV ayrışmıştı). Havuz yalnız
            # belge kimliğini doğrulamak ve `kanit_alintisi` için kullanılır.
            try:
                kind, value = resolve_decision(row)
            except BuildError as exc:
                errors.append(exc)
                continue

            # v2: karar verilmemiş satır gold'a GİRMEZ. Sayılır ve raporlanır —
            # "hiç uyuşmazlık yok" ile "kimse bakmamış" ayrılabilsin.
            if kind == SKIPPED_DECISION:
                skipped[annotator] += 1
                if _clean(row.get("note")):
                    # Anotatör bir sorun yazmış ama kararı işaretlememiş.
                    # v1'de bu satır sessizce "model doğru" olurdu.
                    skipped_with_note.append({
                        "annotator": annotator, "doc_id": doc_id,
                        "field": field, "note": _clean(row.get("note")),
                    })
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
        "protocols": protocols,
        "skipped": skipped,
        "skipped_with_note": skipped_with_note,
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

        # 0) Hakemlik izi — `campaign_type` DAHİL her hücrenin notuna bakılır.
        # `campaign_type` az sonra `pop`lanıyor ve notu hiçbir yere yazılmıyor;
        # bayrağı popdan SONRA hesaplamak, round1'in en kalabalık uyuşmazlık
        # alanındaki (n=47, 17 uyuşmazlık) hakemliği görünmez kılardı.
        adjudicated = any(
            hakemlik_damgali(note)
            for entries in per_field.values()
            for *_, note in entries
        )

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
            adjudicated=adjudicated,
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
                alinti = kanit_alintisi(doc, field, value)
                if alinti:
                    record.field_spans[field] = alinti
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

    deger_sayisi = sum(len(r.fields) for r in records)
    kanitsiz = uncovered_fields(records)
    kanitli = deger_sayisi - len(kanitsiz)

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
        f"- Hakemlikten/şema onarımından geçmiş kayıt (`adjudicated`): "
        f"**{sum(1 for r in records if r.adjudicated)}** "
        f"— damgalar: {', '.join('`' + d + '`' for d in hakemlik_damgalari())}",
        f"- Kanıtlı alan (`field_spans`): **{kanitli}/{deger_sayisi}**"
        + (f" (%{100 * kanitli / deger_sayisi:.1f})" if deger_sayisi else ""),
        "",
        "## Protokol künyesi",
        "",
        "| Dosya | Protokol | Boş hücre |",
        "|---|---|---|",
    ]
    for path_key, protocol in sorted(result.get("protocols", {}).items()):
        meaning = ("karar verilmedi — gold'a GİRMEZ" if protocol == PROTOCOL_V2
                   else "`ok` (onay) — modele çapalı")
        lines.append(f"| `{path_key}` | **{protocol}** | {meaning} |")

    skipped = result.get("skipped") or Counter()
    skipped_notes = result.get("skipped_with_note") or []
    lines += ["", f"- v2'de karar verilmemiş satır: **{sum(skipped.values())}** "
              + (f"({', '.join(f'{a}={n}' for a, n in sorted(skipped.items()))})"
                 if skipped else ""), ""]
    if skipped_notes:
        lines += [
            f"> ⚠️ **{len(skipped_notes)} satırda not var ama karar yok.** "
            "Anotatör bir sorun yazmış, `verdict` sütununu işaretlememiş. "
            "v1 protokolünde bu satırlar sessizce **'model doğru'** sayılırdı; "
            "v2'de gold'a girmiyorlar. Kapatılmaları gerekir.",
            "",
            "| Anotatör | Belge | Alan | Not |",
            "|---|---|---|---|",
        ]
        for item in skipped_notes[:100]:
            note = item["note"].replace("|", "\\|")[:90]
            lines.append(f"| {item['annotator']} | `{item['doc_id']}` "
                         f"| `{item['field']}` | {note} |")
        if len(skipped_notes) > 100:
            lines.append(f"\n_… ve {len(skipped_notes) - 100} tane daha._")

    lines += [
        "",
        "## Ölçülebilirlik",
        "",
        "- **Precision + halüsinasyon oranı:** tüm kayıtlarda ölçülebilir — "
        "modelin ürettiği her alan için karar var.",
        "- **Recall:** yalnızca 12/12 kapsanan "
        f"{len(full)} kayıtta ölçülebilir; diğerlerinde anote edilmemiş alan "
        "ile gerçekten olmayan alan ayrılamaz.",
        "",
        "## Kanıt (`field_spans`)",
        "",
        f"- Kanıtlı: **{kanitli}/{deger_sayisi}** alan",
        f"- Kanıtsız: **{len(kanitsiz)}** alan — değer var, belgede birebir "
        "geçen alıntısı yok.",
        "",
        "> Bu hattın kanıtı `merge_gold_v2` hattınınkiyle **aynı ağırlıkta "
        "değildir.** Orada alıntıyı anotatör belgeyi kör okuyarak elle yazdı; "
        "burada çıkarıcının kaydettiği konumu anotatör onayladı (`verdict=ok`). "
        "İkisi de belgede birebir geçer, ikincisi bağımsız bir gözlem değildir.",
        "",
        "> Kanıtsız alanların çoğu `verdict=fix`tir: anotatör değeri düzeltti "
        "ama alıntı yazacağı bir sütun yok. Kanonik değeri metinde geri arayıp "
        "bir yer bulmak kanıt üretmek değil, **kanıt uydurmak** olurdu.",
        "",
        "## Alan bazında",
        "",
        "| Alan | değer | kanıtlı | yok (absent) | belirsiz |",
        "|---|---:|---:|---:|---:|",
    ]
    field_evidence: Counter = Counter()
    for record in records:
        field_evidence.update(record.field_spans.keys())
    for field in EXTRACTION_FIELDS:
        lines.append(f"| `{field}` | {field_values[field]} | {field_evidence[field]} "
                     f"| {field_absent[field]} | {field_unclear[field]} |")

    if kanitsiz:
        lines += ["", "### Kanıtsız alanlar — kapatılacak iş listesi", "",
                  "| Belge | Alan |", "|---|---|"]
        for doc_id, field in kanitsiz[:200]:
            lines.append(f"| `{doc_id}` | `{field}` |")
        if len(kanitsiz) > 200:
            lines.append(f"\n_… ve {len(kanitsiz) - 200} tane daha._")

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
    parser.add_argument("--kanit-zorunlu", action="store_true",
                        help="kanıtsız alan varsa yazma (varsayılan: yaz ama "
                             "sayıyı raporla). Uydurma alıntı her hâlükârda "
                             "ölümcüldür.")
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

    # UYDURMA KAPISI — asla gevşemez, `--allow-errors` bile geçemez.
    # Buradaki alıntılar `kanit_alintisi` tarafından doğrulanarak yazıldığı
    # için normalde boş çıkar; boş çıkmazsa türetme mantığı bozulmuştur ve
    # gold'un yazılmaması DOĞRU davranıştır.
    uydurma = fabrication_errors(records)
    if uydurma:
        print(f"\n{len(uydurma)} UYDURMA ALINTI — DOSYA YAZILMADI:\n", file=sys.stderr)
        for message in uydurma[:50]:
            print(f"  {message}", file=sys.stderr)
        return 1

    # KANIT KAPSAMI — kusur değil ÖLÇÜM. Sıfırlanması hedeftir; gizlenmesi
    # değil. Ölümcül yapmak `verdict=fix` olan her alanı gold dışına atardı:
    # anotatörün elle girdiği en değerli veri sessizce kaybolurdu.
    kanitsiz = uncovered_fields(records)
    deger_sayisi = sum(len(r.fields) for r in records)
    if kanitsiz and args.kanit_zorunlu:
        print(f"\n{len(kanitsiz)}/{deger_sayisi} ALAN KANITSIZ "
              f"(--kanit-zorunlu) — DOSYA YAZILMADI:\n", file=sys.stderr)
        for doc_id, field in kanitsiz[:50]:
            print(f"  {doc_id} / {field}: değer var, kanıt YOK", file=sys.stderr)
        if len(kanitsiz) > 50:
            print(f"  … ve {len(kanitsiz) - 50} tane daha", file=sys.stderr)
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
    print(f"  kanıtlı alan       : {deger_sayisi - len(kanitsiz)}/{deger_sayisi}")
    print(f"  sha256             : {digest}")
    print(f"rapor: {args.report}")
    if kanitsiz:
        # stderr: sayı görünür kalsın, log'a bakan gözden kaçmasın.
        print(f"UYARI: {len(kanitsiz)}/{deger_sayisi} alan KANITSIZ "
              f"(değer var, belgede alıntısı yok). Listesi raporda: "
              f"{args.report}", file=sys.stderr)
    if result["unknown_docs"]:
        print(f"UYARI: {len(result['unknown_docs'])} bilinmeyen doc_id atlandı "
              f"(ön-anotasyonda yok).", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
