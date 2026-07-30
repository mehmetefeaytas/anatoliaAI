"""Gold set şeması v1 — yükleme, doğrulama, kanonikleştirme.

İlgili: CLAUDE.md §9 (veri modeli), §10 (normalizasyon), §16 (değerlendirme
        metodolojisi), §6 (zor anlama vakaları)
        data/gold/ANNOTATION_GUIDE.md (anotatör kılavuzu)

## Neden `absent_fields` — bu dosyanın varlık sebebi

v0 şeması yalnızca `fields` tutuyordu: "bu belgede doğrulanmış değerler".
Bir alan `fields` içinde YOKSA iki farklı şey demek olabiliyordu:

  (a) anotatör kontrol etti, bu belgede gerçekten YOK   -> model üretirse FP
  (b) anotatör o alana hiç bakmadı                      -> model üretirse BİLİNMEZ

Bu ikisi ayrılamadığında **precision tanımsızdır** ve dolayısıyla halüsinasyon
oranı ÖLÇÜLEMEZ. Projenin merkezindeki iddia ("değer uydurmuyoruz", CLAUDE.md
§19) tam olarak bu sayıyla ayakta durur. `absent_fields` (a) durumunu AÇIKÇA
kaydeder; listede olmayan ve `fields`'ta da olmayan alan (b)'dir ve metrik
dışında bırakılır.

## Geriye uyumluluk

`data/gold/gold.sample.json` (3 kayıt) `{text, fields, hard: bool}` biçiminde.
`load_gold()` bunu sessizce v1'e taşır: `hard: true` -> `hard_tags: ["legacy"]`.
Yazarken `to_dict()` eski `hard` anahtarını da üretir, böylece `eval/run_eval.py`
(dokunulmadı) gold.v1.json'u okumaya devam eder.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from dataclasses import dataclass, field as dc_field
from pathlib import Path
from typing import Any, Optional

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.extraction.llm.schema import (  # noqa: E402
    EXTRACTION_FIELDS,
    HEDEF_KITLE_LABELS,
)
from src.normalization import normalize as N  # noqa: E402
from src.schemas import CAMPAIGN_TYPES  # noqa: E402

GOLD_SCHEMA_VERSION = "1.0"

# --------------------------------------------------------------------------- #
# Zor-vaka etiketleri (çok etiketli) — CLAUDE.md §6
# --------------------------------------------------------------------------- #
# Tek bir `hard: bool` bayrağı, ablasyonda "hibrit NEREDE kazandı" sorusunu
# cevaplayamıyordu. Altı kategori, few-shot örneklerinin (llm/schema.py FEWSHOT)
# kapsadığı vaka tipleriyle birebir hizalıdır.
HARD_TAGS = (
    "terminoloji",      # katılım bankacılığı terimi (kâr payı ≠ faiz, katılım fonu…)
    "format_varyant",   # TR sayı/tarih/para biçim varyantı (1.500,00 · 31.12.2026)
    "eksik_bilgi",      # sayı verilmemiş, sadece niteleyici ("avantajlı finansman")
    "celiskili",        # metin kendi içinde çelişiyor ("masrafsız" + tahsis ücreti)
    "kosullu_aralik",   # aralık ya da zaman/koşul bağımlı oran ("ilk 6 ay %0")
    "tr_ortografi",     # Türkçe imla/karakter tuzağı (İ/ı, şapkalı â, ALL-CAPS)
)
LEGACY_HARD_TAG = "legacy"
ALL_HARD_TAGS = HARD_TAGS + (LEGACY_HARD_TAG,)

# --------------------------------------------------------------------------- #
# Anotasyon kararları
# --------------------------------------------------------------------------- #
# `ok` VARSAYILANDIR: boş bırakılan hücre "model doğru" demektir. Yüksek güvenli
# satırlarda anotatörün hiçbir tuşa basmaması için (Cuma günü darboğaz insan
# zamanı, bkz. ANNOTATION_GUIDE.md §2).
VERDICTS = ("ok", "fix", "absent", "unclear")
DEFAULT_VERDICT = "ok"

# `campaign_type` 12 alandan biri DEĞİL ama gold'da etiketlenir: 8-sınıf
# BERTurk sınıflandırıcısının macro-F1'i buna dayanır (CLAUDE.md §16).
CAMPAIGN_TYPE_KEY = "campaign_type"
ANNOTATABLE_KEYS = tuple(EXTRACTION_FIELDS) + (CAMPAIGN_TYPE_KEY,)

# --------------------------------------------------------------------------- #
# Alan -> kanonik tip ailesi (llm/schema.py FIELD_VALUE_SCHEMA ile birebir)
# --------------------------------------------------------------------------- #
RATE_FIELDS = frozenset({"kar_payi_orani", "indirim_orani"})
MONEY_FIELDS = frozenset({"finansman_tutari", "tahsis_ucreti", "odul_miktari"})
INT_FIELDS = frozenset({"vade_ay", "taksit_sayisi"})
DATE_FIELDS = frozenset({"kampanya_suresi"})
TEXT_LIST_FIELDS = frozenset({"kampanya_kosullari"})
LABEL_LIST_FIELDS = frozenset({"hedef_kitle"})
FEE_FIELDS = frozenset({"masraf_durumu"})
POINTS_FIELDS = frozenset({"alisveris_puani"})

# IAA'da `ratio` ölçeğiyle değerlendirilecek sayısal alanlar: 1,89 ile 1,90
# arasındaki fark "tam uyuşmazlık" sayılmasın (bkz. eval/iaa.py).
NUMERIC_FIELDS = RATE_FIELDS | MONEY_FIELDS | INT_FIELDS

_NUMBER_RE = re.compile(r"^-?\d+(?:[.,]\d+)?$")
_HASHTAG_RE = re.compile(r"#([a-zçğıöşü_]+)", re.IGNORECASE)


class GoldValidationError(ValueError):
    """Kanonik biçim ihlali — anotatöre gösterilecek NET mesajı taşır."""


# --------------------------------------------------------------------------- #
# Kanonik biçim doğrulama
# --------------------------------------------------------------------------- #
def _is_number(v: Any) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def validate_canonical(name: str, value: Any) -> Optional[str]:
    """`value` alanın kanonik biçimine uyuyor mu? Uymuyorsa NET hata metni.

    Dönen metin doğrudan anotatöre gösterilir; "invalid value" gibi bir şey
    yazmaz, beklenen biçimi ve düzeltme örneğini verir.
    """
    if name == CAMPAIGN_TYPE_KEY:
        if value in CAMPAIGN_TYPES:
            return None
        return (f"kampanya türü {value!r} tanınmıyor. İzin verilen 8 tür: "
                f"{', '.join(CAMPAIGN_TYPES)}")

    if name not in EXTRACTION_FIELDS:
        return (f"{name!r} bilinen bir alan değil. 12 alan: "
                f"{', '.join(EXTRACTION_FIELDS)}")

    if value is None:
        return (f"{name}: değer None. Alan belgede yoksa `fields`'a yazma, "
                f"`absent_fields`'a ekle (verdict=absent).")

    if name in RATE_FIELDS:
        if _is_number(value):
            return None
        if isinstance(value, dict) and set(value) == {"min", "max"}:
            if not (_is_number(value["min"]) and _is_number(value["max"])):
                return f"{name}: aralığın min/max değerleri sayı olmalı, {value!r} geldi."
            if value["min"] > value["max"]:
                return f"{name}: min > max ({value['min']} > {value['max']})."
            if value["min"] == value["max"]:
                return (f"{name}: min == max olan aralık, aralık değildir. "
                        f"Düz sayı yaz: {value['min']}")
            return None
        return (f"{name}: oran ya düz sayı (%1,89 -> 1.89) ya da aralık "
                f'({{"min": 1.99, "max": 2.49}}) olmalı; {value!r} geldi.')

    if name in MONEY_FIELDS:
        if not isinstance(value, dict) or set(value) != {"value", "currency"}:
            return (f'{name}: para {{"value": 500, "currency": "TRY"}} biçiminde '
                    f"olmalı; {value!r} geldi.")
        if not _is_number(value["value"]):
            return f"{name}: para value alanı sayı olmalı, {value['value']!r} geldi."
        if value["currency"] != "TRY":
            return (f"{name}: currency yalnız \"TRY\" olabilir, "
                    f"{value['currency']!r} geldi.")
        return None

    if name in INT_FIELDS:
        if isinstance(value, bool) or not isinstance(value, int):
            return (f"{name}: tamsayı olmalı (\"1 yıl\" -> 12, \"120 aya varan\" "
                    f"-> 120); {value!r} geldi.")
        if value <= 0:
            return f"{name}: pozitif tamsayı olmalı, {value!r} geldi."
        return None

    if name in DATE_FIELDS:
        if not isinstance(value, str):
            return f"{name}: ISO-8601 tarih metni olmalı, {value!r} geldi."
        if N.normalize_date(value) != value:
            return (f"{name}: tarih ISO-8601 (YYYY-AA-GG) olmalı. "
                    f'"31.12.2026" -> "2026-12-31"; {value!r} geldi.')
        return None

    if name in FEE_FIELDS:
        if not isinstance(value, dict) or set(value) != {"has_fee", "amount"}:
            return (f'{name}: {{"has_fee": true|false, "amount": sayı|null}} '
                    f"biçiminde olmalı; {value!r} geldi.")
        if not isinstance(value["has_fee"], bool):
            return f"{name}: has_fee true/false olmalı, {value['has_fee']!r} geldi."
        if value["amount"] is not None and not _is_number(value["amount"]):
            return f"{name}: amount sayı ya da null olmalı, {value['amount']!r} geldi."
        if value["has_fee"] is False and value["amount"] not in (0, 0.0):
            return (f"{name}: \"masrafsız\" ise amount 0 olmalı (bilgi yok DEĞİL), "
                    f"{value['amount']!r} geldi.")
        return None

    if name in POINTS_FIELDS:
        if not isinstance(value, dict) or set(value) != {"kind", "value"}:
            return (f'{name}: {{"kind": "rate"|"points", "value": sayı}} biçiminde '
                    f"olmalı; {value!r} geldi.")
        if value["kind"] not in ("rate", "points"):
            return (f'{name}: kind yalnız "rate" (%5 puan) ya da "points" '
                    f"(1.000 chip-para) olabilir; {value['kind']!r} geldi.")
        if not _is_number(value["value"]):
            return f"{name}: value sayı olmalı, {value['value']!r} geldi."
        return None

    if name in LABEL_LIST_FIELDS:
        if not isinstance(value, list) or not value:
            return (f"{name}: boş olmayan etiket listesi olmalı. İzin verilen: "
                    f"{', '.join(HEDEF_KITLE_LABELS)}")
        bad = [v for v in value if v not in HEDEF_KITLE_LABELS]
        if bad:
            return (f"{name}: tanınmayan etiket {bad!r}. İzin verilen: "
                    f"{', '.join(HEDEF_KITLE_LABELS)}")
        if len(set(value)) != len(value):
            return f"{name}: aynı etiket iki kez yazılmış: {value!r}"
        return None

    if name in TEXT_LIST_FIELDS:
        if not isinstance(value, list) or not value:
            return f"{name}: boş olmayan metin listesi olmalı; {value!r} geldi."
        bad = [v for v in value if not isinstance(v, str) or not v.strip()]
        if bad:
            return f"{name}: liste öğeleri boş olmayan metin olmalı; {bad!r} geldi."
        return None

    return f"{name}: kanonik tipi tanımlı değil (scripts/gold_schema.py)."


def assert_canonical(name: str, value: Any) -> None:
    """`validate_canonical` hata verirse `GoldValidationError` yükseltir."""
    err = validate_canonical(name, value)
    if err:
        raise GoldValidationError(err)


# --------------------------------------------------------------------------- #
# İnsan girdisi -> kanonik değer
# --------------------------------------------------------------------------- #
def _try_json(raw: str) -> tuple[bool, Any]:
    try:
        return True, json.loads(raw)
    except (ValueError, TypeError):
        return False, None


def parse_gold_value(name: str, raw: Any) -> Any:
    """CSV'ye elle yazılmış değeri kanonik biçime çevirir.

    İki yol denenir:
      1) JSON — CSV'yi biz ürettiysek değer zaten JSON'dur (gidiş-dönüş garantisi).
      2) Serbest TR metni — `src/normalization/normalize.py` fonksiyonları
         yeniden kullanılır. Anotatörün "%1,89" ya da "31.12.2026" yazması yeter.

    (2) ayrıca Excel hasarına karşı sigortadır: TR yerelli Excel `1.89`
    hücresini kaydederken `1,89` yapar; `parse_tr_number` bunu düzeltir.

    Raises:
        GoldValidationError: değer okunamazsa ya da kanonik biçime uymazsa.
    """
    if raw is None:
        raise GoldValidationError(f"{name}: değer boş bırakılmış.")
    if not isinstance(raw, str):
        assert_canonical(name, raw)
        return raw

    text = raw.strip()
    if not text:
        raise GoldValidationError(
            f"{name}: verdict=fix verildi ama gold_value boş. Doğru değeri yaz "
            f"ya da verdict'i absent/unclear yap.")

    if name == CAMPAIGN_TYPE_KEY:
        for candidate in CAMPAIGN_TYPES:
            if candidate.casefold() == text.casefold():
                return candidate
        raise GoldValidationError(
            f"kampanya türü {text!r} tanınmıyor. İzin verilen 8 tür: "
            f"{', '.join(CAMPAIGN_TYPES)}")

    value = _coerce(name, text)
    assert_canonical(name, value)
    return value


def _coerce(name: str, text: str) -> Any:
    """Ham metni alanın kanonik tipine zorlar (doğrulama çağıran tarafta)."""
    ok, parsed = _try_json(text)

    if name in RATE_FIELDS:
        if ok and (_is_number(parsed) or isinstance(parsed, dict)):
            return N.collapse_degenerate_range(parsed)
        rate = N.normalize_rate(text)
        if rate is None:
            raise GoldValidationError(
                f'{name}: "{text}" bir orana çevrilemedi. Örnek: %1,89 ya da '
                f'{{"min": 1.99, "max": 2.49}}')
        return N.collapse_degenerate_range(rate)

    if name in MONEY_FIELDS:
        if ok and isinstance(parsed, dict):
            return parsed
        money = N.normalize_money(text)
        if money is None:
            raise GoldValidationError(
                f'{name}: "{text}" bir para değerine çevrilemedi. Örnek: 500 TL '
                f'ya da {{"value": 500, "currency": "TRY"}}')
        return money

    if name in INT_FIELDS:
        if ok and isinstance(parsed, int) and not isinstance(parsed, bool):
            return parsed
        if name == "vade_ay":
            months = N.normalize_term_months(text)
            if months is not None:
                return months
        number = N.parse_tr_number(text)
        if number is None:
            raise GoldValidationError(
                f'{name}: "{text}" tamsayıya çevrilemedi. Örnek: 120 ya da '
                f'"1 yıl" (-> 12)')
        return int(round(number))

    if name in DATE_FIELDS:
        if ok and isinstance(parsed, str):
            text = parsed
        iso = N.normalize_date(text)
        if iso is None:
            raise GoldValidationError(
                f'{name}: "{text}" tarihe çevrilemedi. Örnek: 31.12.2026 ya da '
                f'31 Aralık 2026 (-> "2026-12-31")')
        return iso

    if name in FEE_FIELDS:
        if ok and isinstance(parsed, dict):
            return parsed
        fee = N.normalize_fee_status(text)
        if fee is None:
            raise GoldValidationError(
                f'{name}: "{text}" masraf durumuna çevrilemedi. Örnek: '
                f'masrafsız ya da {{"has_fee": true, "amount": 500}}')
        return fee

    if name in POINTS_FIELDS:
        if ok and isinstance(parsed, dict):
            return parsed
        # Kısayol: "rate=5" / "oran=5" / "points=1000" / "puan=1000".
        match = re.match(r"^(rate|oran|points|puan)\s*[:=]\s*(.+)$", text, re.I)
        if match:
            kind = "rate" if match.group(1).lower() in ("rate", "oran") else "points"
            number = N.parse_tr_number(match.group(2))
            if number is not None:
                return {"kind": kind, "value": number}
        raise GoldValidationError(
            f'{name}: "{text}" okunamadı. ORAN mı ADET mi belirtmelisin: '
            f'{{"kind": "rate", "value": 5}} ya da kısayol `puan=1000`')

    if name in LABEL_LIST_FIELDS or name in TEXT_LIST_FIELDS:
        if ok and isinstance(parsed, list):
            return parsed
        # CSV ayırıcısı ';' olduğu için liste ayırıcısı '|'.
        return [part.strip() for part in text.split("|") if part.strip()]

    raise GoldValidationError(f"{name}: kanonik tipi tanımlı değil.")


def format_gold_value(name: str, value: Any) -> str:
    """Kanonik değeri CSV hücresine yazılacak metne çevirir.

    `parse_gold_value(name, format_gold_value(name, v)) == v` garantisi vardır
    (gidiş-dönüş testi: tests/test_gold_csv.py).
    """
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, bool):
        return json.dumps(value)
    if isinstance(value, (int, float)):
        return repr(value)
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


# --------------------------------------------------------------------------- #
# Kayıt
# --------------------------------------------------------------------------- #
@dataclass
class GoldRecord:
    """Tek bir anotasyonlu belge (gold şema v1).

    fields         : doğrulanmış DEĞERLER (alan -> kanonik değer)
    absent_fields  : "kontrol ettim, bu belgede YOK" (precision'ın tanımı)
    unclear_fields : anotatör karar veremedi -> metrik dışı, hakemliğe düşer
    hard_tags      : çok etiketli zor-vaka kategorileri (HARD_TAGS)
    """

    id: str
    text: str
    fields: dict[str, Any] = dc_field(default_factory=dict)
    absent_fields: list[str] = dc_field(default_factory=list)
    hard_tags: list[str] = dc_field(default_factory=list)
    bank_slug: Optional[str] = None
    source_url: Optional[str] = None
    content_hash: Optional[str] = None
    campaign_type: Optional[str] = None
    annotators: list[str] = dc_field(default_factory=list)
    adjudicated: bool = False
    needs_adjudication: bool = False
    unclear_fields: list[str] = dc_field(default_factory=list)
    notes: dict[str, str] = dc_field(default_factory=dict)

    @property
    def hard(self) -> bool:
        """Eski `hard: bool` bayrağı — `eval/run_eval.py` bunu okur."""
        return bool(self.hard_tags)

    def to_dict(self) -> dict:
        """JSON'a yazılacak sözlük. `hard` anahtarı geriye uyum için korunur."""
        out: dict[str, Any] = {
            "id": self.id,
            "bank_slug": self.bank_slug,
            "source_url": self.source_url,
            "content_hash": self.content_hash,
            "text": self.text,
            "campaign_type": self.campaign_type,
            "fields": self.fields,
            "absent_fields": sorted(self.absent_fields),
            "hard_tags": sorted(self.hard_tags),
            "annotators": list(self.annotators),
            "adjudicated": self.adjudicated,
            # v0 uyumu: eval/run_eval.py `item.get("hard")` okuyor.
            "hard": self.hard,
        }
        if self.needs_adjudication:
            out["needs_adjudication"] = True
        if self.unclear_fields:
            out["unclear_fields"] = sorted(self.unclear_fields)
        if self.notes:
            out["notes"] = self.notes
        return out

    def validate(self) -> list[str]:
        """Kayıt düzeyinde tutarlılık hataları (boş liste = temiz)."""
        errors: list[str] = []
        if not self.id:
            errors.append("id boş.")
        if not (self.text or "").strip():
            errors.append(f"{self.id}: text boş.")

        if self.campaign_type is not None and self.campaign_type not in CAMPAIGN_TYPES:
            errors.append(f"{self.id}: {validate_canonical(CAMPAIGN_TYPE_KEY, self.campaign_type)}")

        for tag in self.hard_tags:
            if tag not in ALL_HARD_TAGS:
                errors.append(f"{self.id}: bilinmeyen zor-vaka etiketi {tag!r}. "
                              f"İzin verilen: {', '.join(ALL_HARD_TAGS)}")

        for name, value in self.fields.items():
            err = validate_canonical(name, value)
            if err:
                errors.append(f"{self.id}: {err}")

        for name in self.absent_fields:
            if name not in EXTRACTION_FIELDS:
                errors.append(f"{self.id}: absent_fields içinde bilinmeyen alan {name!r}.")

        # ÇEKİRDEK DEĞİŞMEZ: bir alan aynı anda hem "değeri şu" hem "yok" olamaz.
        clash = sorted(set(self.fields) & set(self.absent_fields))
        if clash:
            errors.append(f"{self.id}: {clash} hem fields hem absent_fields içinde. "
                          f"Bir alan ya vardır ya yoktur.")

        clash2 = sorted(set(self.fields) & set(self.unclear_fields))
        if clash2:
            errors.append(f"{self.id}: {clash2} hem fields hem unclear_fields içinde.")

        return errors

    def coverage(self) -> int:
        """Kaç alan hakkında KARAR verilmiş (değer + yok). 12 = tam kapsama."""
        return len(set(self.fields) | set(self.absent_fields))


# --------------------------------------------------------------------------- #
# Yükleme / yazma
# --------------------------------------------------------------------------- #
def _legacy_id(text: str) -> str:
    digest = hashlib.sha256((text or "").encode("utf-8")).hexdigest()[:8]
    return f"legacy-{digest}"


def record_from_dict(item: dict) -> GoldRecord:
    """Sözlükten `GoldRecord` — v0 (`hard: bool`) kayıtları otomatik taşınır."""
    text = item.get("text", "")

    if "hard_tags" in item:
        hard_tags = list(item.get("hard_tags") or [])
    else:
        # v0 -> v1 taşıma: `hard: true` hangi KATEGORİ olduğunu söylemiyor;
        # bilgi uydurmak yerine `legacy` ile işaretlenir ve ablasyonda
        # kategori kırılımı dışında bırakılır.
        hard_tags = [LEGACY_HARD_TAG] if item.get("hard") else []

    return GoldRecord(
        id=item.get("id") or _legacy_id(text),
        text=text,
        fields=dict(item.get("fields") or {}),
        absent_fields=list(item.get("absent_fields") or []),
        hard_tags=hard_tags,
        bank_slug=item.get("bank_slug"),
        source_url=item.get("source_url"),
        content_hash=item.get("content_hash"),
        campaign_type=item.get("campaign_type"),
        annotators=list(item.get("annotators") or []),
        adjudicated=bool(item.get("adjudicated", False)),
        needs_adjudication=bool(item.get("needs_adjudication", False)),
        unclear_fields=list(item.get("unclear_fields") or []),
        notes=dict(item.get("notes") or {}),
    )


def load_gold(path: str | Path) -> list[GoldRecord]:
    """Gold JSON dosyasını okur (v0 ve v1 aynı çağrıyla)."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(data, dict):          # {"records": [...]} sarmalı da kabul
        data = data.get("records", [])
    if not isinstance(data, list):
        raise GoldValidationError(
            f"{path}: gold dosyası JSON listesi olmalı, {type(data).__name__} geldi.")
    return [record_from_dict(item) for item in data]


def validate_gold(records: list[GoldRecord]) -> list[str]:
    """Koleksiyon düzeyinde doğrulama (kayıt hataları + id tekrarı)."""
    errors: list[str] = []
    seen: dict[str, int] = {}
    for record in records:
        errors.extend(record.validate())
        seen[record.id] = seen.get(record.id, 0) + 1
    for rid, count in sorted(seen.items()):
        if count > 1:
            errors.append(f"id {rid!r} {count} kez geçiyor — id'ler benzersiz olmalı.")
    return errors


def write_gold(records: list[GoldRecord], path: str | Path) -> str:
    """Gold'u JSON olarak yazar ve yanına `.sha256` kontrol dosyası koyar.

    Sağlama, "eval hangi gold sürümüyle koştu" sorusunu kesin cevaplar; gold
    sessizce değişirse metrik karşılaştırmaları geçersizdir.
    """
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps([r.to_dict() for r in records], ensure_ascii=False, indent=2)
    target.write_text(payload + "\n", encoding="utf-8")
    digest = hashlib.sha256(payload.encode("utf-8") + b"\n").hexdigest()
    Path(f"{target}.sha256").write_text(f"{digest}  {target.name}\n", encoding="utf-8")
    return digest


def values_equal(a: Any, b: Any, tolerance: float = 1e-6) -> bool:
    """İki kanonik değer aynı mı? Sayılarda tolerans, dict/list'te öğe-öğe.

    `eval/run_eval.py._equal` ile aynı semantik; burada iç içe yapılara
    (para sözlüğü, aralık) da iner. Anlaşmazlık tespiti ve IAA bunu kullanır.
    """
    # bool ÖNCE elenir: Python'da True == 1 doğrudur ve `masraf_durumu`nun
    # {"has_fee": true} ile {"has_fee": 1} hâlini eşit sayardık.
    if isinstance(a, bool) or isinstance(b, bool):
        return a is b
    if _is_number(a) and _is_number(b):
        return abs(float(a) - float(b)) < tolerance
    if isinstance(a, dict) and isinstance(b, dict):
        if set(a) != set(b):
            return False
        return all(values_equal(a[k], b[k], tolerance) for k in a)
    if isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            return False
        return all(values_equal(x, y, tolerance) for x, y in zip(a, b))
    return a == b


def extract_hard_tags(note: str) -> list[str]:
    """Anotatör notundaki `#terminoloji` gibi hashtag'leri etikete çevirir.

    Ayrı bir sütun eklemek yerine hashtag: anotatör zaten not yazıyor, ekstra
    hücre gezinmesi yok (tuş tasarrufu, ANNOTATION_GUIDE.md §2).
    """
    if not note:
        return []
    found = []
    for raw in _HASHTAG_RE.findall(note):
        tag = raw.casefold()
        if tag in ALL_HARD_TAGS and tag not in found:
            found.append(tag)
    return found
