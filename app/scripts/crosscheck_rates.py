"""Kâr payı oranı gold satırlarını BAĞIMSIZ kaynakla çapraz doğrula.

İlgili: ../src/scraping/rates.py, ../data/gold/ANNOTATION_GUIDE.md,
        ../docs/rapor/banka-siteleri-veri-kaynagi-haritasi.md §1–§2

Kullanım:
    python -m scripts.crosscheck_rates
    python -m scripts.crosscheck_rates --out data/gold/rate_crosscheck.csv

## Neden bu betik var

Gold sette 3.422 satırın 0'ı doldurulmuş ve bu, Model Başarısı (%30) için tek
girdi. Satırların 235'i `kar_payi_orani` alanına ait — şartnamenin manşet alanı.

Elimizde artık **bağımsız bir doğruluk kaynağı** var: bankaların kendi hesaplama
uçlarından/oran tablolarından toplanan 299 kayıt (`data/raw/*/rates/`). Bu,
modelin kendi çıktısı DEĞİL; bankanın ilan ettiği değer.

Betik, kural katmanının bir belgeden çıkardığı oranı aynı bankanın aynı ürün
sınıfı için ilan edilmiş oranlarla karşılaştırır ve satırları üçe ayırır:

    dogrulandi  — çıkarılan değer ilan edilen bir oranla örtüşüyor
    celisiyor   — ilan edilen oran var ama hiçbiriyle örtüşmüyor (kural hatası)
    kaynak_yok  — o ürün için ilan edilmiş oran toplanamadı → insan karar verir

Böylece insan gözü yalnızca gerçekten gereken satırlara harcanır.

## Neden anotasyon CSV'leri EZİLMEZ

`gold_value` insanın kararıdır. Makine önerisini oraya yazmak, anotasyonu
yapılmış gibi göstermek olur — değerlendirme metriklerini kendi kendini
doğrulayan bir döngüye sokar. Bu yüzden çıktı AYRI bir dosyadır ve her satır
`kaynak_url` ile gerekçelendirilir; anotasyoncu kabul/ret verir.

## Eşleştirme neden SIKI

Yanlış ürün eşleşmesi hayalet "çelişki" üretir. Bu yüzden:
  * yalnızca `doc_id` ürün sınıfını AÇIKÇA belirtiyorsa eşleştirilir,
  * finansman (aylık kâr oranı) ile katılma hesabı (yıllık kâr payı) ASLA
    karşılaştırılmaz — farklı büyüklükler (CLAUDE.md §17),
  * ilan edilen oran yoksa "çelişki" DEĞİL "kaynak_yok" denir.
"""

from __future__ import annotations

import argparse
import csv
import glob
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

# Ürün sınıfı → `doc_id` içinde aranan izler + ilan edilen kayıtta aranan izler.
# Sıra ÖNEMLİ: "togg" taşıt sınıfının altındadır ama daha özgüldür.
PRODUCT_CLASSES: tuple[tuple[str, tuple[str, ...], tuple[str, ...]], ...] = (
    ("konut", ("konut", "ev-finansman", "mortgage", "arsa", "isyeri", "is-yeri"),
     ("konut", "arsa", "işyeri", "is yeri", "ev/ofis")),
    ("tasit", ("tasit", "arac", "togg", "motosiklet", "binek"),
     ("taşıt", "tasit", "araç", "arac", "togg", "motosiklet", "binek")),
    ("ihtiyac", ("ihtiyac", "egitim", "kira-finansman", "seyahat", "hac-umre",
                 "tekne", "bisiklet"),
     ("ihtiyaç", "ihtiyac", "eğitim", "kira", "yurt", "teknoloji", "cep",
      "engelsiz", "prefabrik")),
    ("katilma", ("katilma", "hesap", "birikim", "altin", "vadeli", "cari"),
     ("katılma", "katilma", "hesap")),
)

# Aylık oran karşılaştırma toleransı (yüzde puanı). %2,99 ile %2,9900 aynıdır;
# %2,99 ile %3,04 farklıdır.
RATE_TOLERANCE = 0.02

VERDICT_CONFIRMED = "dogrulandi"
VERDICT_CONFLICT = "celisiyor"
VERDICT_NO_SOURCE = "kaynak_yok"
# Sentetik demo belgesi: canlı ilan edilen oranla kıyaslanamaz.
VERDICT_FIXTURE = "fixture"

# FİNANSMAN ürün sayfasında AYLIK kâr oranı beklenir. Gerçek ölçülen aralık
# (2026-08-03, 299 ilan edilmiş kayıt): %1,89 – %4,29 (Emlak), %2,99 – %3,57
# (Kuveyt Türk), %3,04 – %4,00 (Albaraka), %2,95 – %5,99 (Türkiye Finans
# aralıkları). Üst sınır cömert tutuldu.
FINANCING_RATE_MAX = 12.0
FINANCING_CLASSES = ("konut", "tasit", "ihtiyac")

# Aylık oran alanına sızan tipik VADE değerleri. Bir finansman sayfasında
# "36" bir oran değil vadedir; kural katmanı bunları oran sanıyor.
COMMON_MATURITIES = (6, 9, 12, 18, 24, 36, 48, 60, 72, 84, 96, 120)

# NOT: katılma hesabı tarafında makullük kontrolü YAPILMAZ. İlan edilen yıllık
# oranlar %0,04 (altın/gümüş) ile %38,73 (TL) arasında değişiyor; bu kadar geniş
# bir aralık ayırt edici değil, dolayısıyla bilgi vermeyen bir uyarı üretirdi.


@dataclass
class Row:
    """Bir gold satırı + çapraz doğrulama sonucu."""

    file: str
    doc_id: str
    bank: str
    field: str
    model_value: str
    model_conf: str
    product_class: Optional[str]
    verdict: str
    published: str = ""
    suggested_gold: str = ""
    source_url: str = ""
    note: str = ""
    plausibility: str = ""
    freshness: str = ""
    current_value: str = ""

    def to_csv(self) -> dict[str, Any]:
        return {
            "file": self.file, "doc_id": self.doc_id, "bank": self.bank,
            "field": self.field, "model_value": self.model_value,
            "model_conf": self.model_conf,
            "product_class": self.product_class or "",
            "crosscheck": self.verdict, "plausibility": self.plausibility,
            "freshness": self.freshness, "current_value": self.current_value,
            "published_rates": self.published,
            "suggested_gold": self.suggested_gold,
            "source_url": self.source_url, "note": self.note,
        }


def load_fixture_doc_ids(raw_dir: str = "data/raw") -> set[str]:
    """Sentetik demo belgelerinin `doc_id`leri.

    Fixture'lar `data/raw/<banka>/<ad>.txt` KÖKÜNDE durur; canlı hasat belgeleri
    her zaman bir küme alt klasöründedir (`live/`, `products/`, `archive/`,
    `docs/`, `manual/`). Ayrım budur.

    NEDEN ŞART: `kuveyt-turk--konut` fixture'ı şartnamenin örnek metnini taşıyor
    ("kâr payı oranı %1,89'dan başlayan") ve canlı ilan edilen Kuveyt Türk
    oranı %2,99. Fixture dışlanmazsa bu, KURAL HATASI gibi raporlanır — oysa
    belge zaten sentetik.
    """
    out: set[str] = set()
    for path in glob.glob(f"{raw_dir}/*/*.txt"):
        p = Path(path)
        out.add(f"{p.parent.name}--{p.stem}")
    return out


def current_rule_values(docs_dir: str = "data/gold/review/belgeler",
                        field: str = "kar_payi_orani") -> dict[str, str]:
    """Anotasyon belgelerinde MEVCUT kural katmanının ürettiği değerler.

    NEDEN ÖNEMLİ: anotasyon CSV'lerindeki `model_value` kolonu, ön-anotasyonun
    KOŞTUĞU ANDAKİ model çıktısıdır. Kural katmanı o günden beri değiştiyse
    anotasyoncu ARTIK VAR OLMAYAN bir modelin çıktısını doğrular; üretilen gold
    ve ondan çıkan metrikler yanlış modele ait olur.

    Ölçüldü (2026-08-03): Temmuz'da üretilen CSV'lerde `36.0` gibi vade
    değerleri oran olarak duruyordu; mevcut kural aynı belgelerde `None`
    döndürüyor — yani o hata sınıfı çoktan düzeltilmişti.

    Yalnızca `kar_payi_orani` desteklenir; başka alan istenirse boş döner
    (uydurma yapmamak için).
    """
    if field != "kar_payi_orani":
        return {}
    try:
        from src.extraction.rules.extract import extract_kar_payi
    except ImportError:
        return {}
    out: dict[str, str] = {}
    for path in sorted(glob.glob(f"{docs_dir}/*.txt")):
        p = Path(path)
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        f = extract_kar_payi(text)
        out[p.stem] = "" if f is None else json.dumps(
            f.canonical_value, ensure_ascii=False)
    return out


def check_freshness(csv_value: str, current: Optional[str]) -> str:
    """CSV'deki model değeri mevcut kuralın ürettiğiyle aynı mı?"""
    if current is None:
        return ""  # belge kopyası yok, karşılaştırılamaz
    a = (csv_value or "").strip()
    b = (current or "").strip().strip('"')
    if a == b:
        return "guncel"
    # Sayısal eşdeğerlik: "36.0" ile "36" aynı değerdir.
    try:
        if a and b and abs(float(a) - float(b)) < 1e-9:
            return "guncel"
    except ValueError:
        pass
    if not a and b:
        return "bayat_eksik"   # CSV boş, kural artık değer üretiyor
    if a and not b:
        return "bayat_fazla"   # CSV değer taşıyor, kural artık üretmiyor
    return "bayat_farkli"


def check_plausibility(product_class: Optional[str],
                       bounds: Optional[tuple[float, float]]) -> str:
    """Değer, ürün sınıfına göre makul aralıkta mı?

    Yalnızca FİNANSMAN sayfaları için ayırt edicidir (aylık oran beklenir).
    Katılma hesabında ilan edilen oranlar %0,04–%38,73 arası olduğu için
    aralık kontrolü bilgi vermez ve yapılmaz.

    Bu kontrol ilan edilmiş orana İHTİYAÇ DUYMAZ; bu yüzden çapraz doğrulamanın
    kapsayamadığı satırlarda da çalışır.
    """
    if bounds is None or product_class not in FINANCING_CLASSES:
        return ""
    lo, hi = bounds
    if hi <= FINANCING_RATE_MAX:
        return "makul"
    if int(hi) in COMMON_MATURITIES and abs(hi - int(hi)) < 0.01:
        return "vade_gibi"
    return "sinir_disi"


def load_published(raw_dir: str = "data/raw") -> list[dict[str, Any]]:
    """`rates/quotes.jsonl` kayıtlarını yükler (bankanın ilan ettiği oranlar)."""
    out: list[dict[str, Any]] = []
    for path in sorted(glob.glob(f"{raw_dir}/*/rates/quotes.jsonl")):
        for line in Path(path).read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                try:
                    out.append(json.loads(line))
                except ValueError:
                    continue
    return out


# Bir CSV'in ANOTASYON dosyası olduğunu belirleyen zorunlu kolonlar.
# Kolon kontrolü ŞART: bu betiğin ÇIKTISI da `data/gold/` altına yazılıyor ve
# içinde `field` kolonu var; kontrol olmadan sonraki koşuda kendi çıktısını
# gold satırı sayar (kendi kendini besleyen sayım hatası).
REQUIRED_GOLD_COLUMNS = {"doc_id", "bank", "field", "model_value", "gold_value"}


def load_gold_rows(gold_dir: str = "data/gold") -> list[dict[str, Any]]:
    """Anotasyon CSV'lerini okur (noktalı virgül ayraçlı, BOM'lu)."""
    rows: list[dict[str, Any]] = []
    for path in sorted(glob.glob(f"{gold_dir}/**/*.csv", recursive=True)):
        with open(path, encoding="utf-8-sig", newline="") as fh:
            reader = csv.DictReader(fh, delimiter=";")
            cols = set(reader.fieldnames or ())
            if not REQUIRED_GOLD_COLUMNS <= cols:
                continue  # anotasyon dosyası değil (ör. bu betiğin çıktısı)
            for r in reader:
                r["_file"] = Path(path).name
                rows.append(r)
    return rows


def classify_product(doc_id: str) -> Optional[str]:
    """`doc_id`'den ürün sınıfını çıkarır. Belirsizse None (eşleştirme yapılmaz)."""
    d = (doc_id or "").lower()
    for name, doc_markers, _ in PRODUCT_CLASSES:
        if any(m in d for m in doc_markers):
            return name
    return None


def _published_for(published: list[dict[str, Any]], bank: str,
                   product_class: str) -> list[dict[str, Any]]:
    """Bankanın o ürün sınıfı için ilan ettiği kayıtlar."""
    markers = next((m for name, _, m in PRODUCT_CLASSES if name == product_class),
                   ())
    want_kind = "katilma" if product_class == "katilma" else "finansman"
    out = []
    for r in published:
        if r.get("bank_slug") != bank or r.get("kind") != want_kind:
            continue
        name = (r.get("product_name") or "").lower()
        if any(m in name for m in markers):
            out.append(r)
    return out


def _rate_of(record: dict[str, Any]) -> Optional[float]:
    """Kaydın kıyaslanabilir oranı: finansmanda aylık, katılmada yıllık brüt."""
    if record.get("kind") == "katilma":
        v = record.get("gross_annual_rate")
    else:
        v = record.get("monthly_rate")
    return float(v) if isinstance(v, (int, float)) else None


def _model_bounds(raw: str) -> Optional[tuple[float, float]]:
    """Model değerini (alt, üst) aralığına indirger. Aralık JSON'u da destekler."""
    s = (raw or "").strip()
    if not s:
        return None
    if s.startswith("{"):
        try:
            j = json.loads(s)
            lo, hi = float(j["min"]), float(j["max"])
            return (min(lo, hi), max(lo, hi))
        except (ValueError, KeyError, TypeError):
            return None
    try:
        v = float(s)
    except ValueError:
        return None
    return (v, v)


def crosscheck(gold_rows: list[dict[str, Any]],
               published: list[dict[str, Any]], *,
               field: str = "kar_payi_orani",
               fixtures: Optional[set[str]] = None,
               current: Optional[dict[str, str]] = None) -> list[Row]:
    """Gold satırlarını ilan edilen oranlarla karşılaştırır."""
    fixtures = fixtures or set()
    current = current or {}
    out: list[Row] = []
    for r in gold_rows:
        if r.get("field") != field:
            continue
        bank = (r.get("bank") or "").strip()
        doc_id = (r.get("doc_id") or "").strip()
        model_raw = (r.get("model_value") or "").strip()
        pc = classify_product(doc_id)
        row = Row(file=r["_file"], doc_id=doc_id, bank=bank, field=field,
                  model_value=model_raw, model_conf=(r.get("model_conf") or ""),
                  product_class=pc, verdict=VERDICT_NO_SOURCE)
        bounds_all = _model_bounds(model_raw)
        row.plausibility = check_plausibility(pc, bounds_all)
        cur = current.get(doc_id)
        row.current_value = (cur or "").strip('"') if cur is not None else ""
        row.freshness = check_freshness(model_raw, cur)

        if doc_id in fixtures:
            row.verdict = VERDICT_FIXTURE
            row.note = ("sentetik demo belgesi — canli ilan edilen oranla "
                        "kiyaslanamaz")
            out.append(row)
            continue

        if pc is None:
            row.note = "doc_id urun sinifini belirtmiyor — esleştirme yapilmadi"
            out.append(row)
            continue

        candidates = _published_for(published, bank, pc)
        rates = sorted({round(x, 4) for x in
                        (_rate_of(c) for c in candidates) if x is not None})
        if not rates:
            row.note = f"'{pc}' icin ilan edilmis oran toplanamadi"
            out.append(row)
            continue

        row.published = ", ".join(f"%{x}" for x in rates)
        row.source_url = next((c.get("source_url") or "" for c in candidates), "")

        bounds = _model_bounds(model_raw)
        if bounds is None:
            row.verdict = VERDICT_CONFLICT if model_raw else VERDICT_NO_SOURCE
            row.suggested_gold = f"%{rates[0]}" if len(rates) == 1 else ""
            row.note = ("model degeri sayiya cevrilemedi" if model_raw
                        else "model deger uretmedi — ilan edilen oran mevcut")
            out.append(row)
            continue

        lo, hi = bounds
        match = [x for x in rates if lo - RATE_TOLERANCE <= x <= hi + RATE_TOLERANCE]
        if match:
            row.verdict = VERDICT_CONFIRMED
            row.suggested_gold = f"%{match[0]}"
            row.note = "ilan edilen oranla ortusuyor"
        else:
            row.verdict = VERDICT_CONFLICT
            row.suggested_gold = f"%{rates[0]}" if len(rates) == 1 else ""
            row.note = (f"cikarilan {model_raw} ilan edilen oranlarla "
                        f"ortusmuyor")
        out.append(row)
    return out


def render_report(rows: list[Row]) -> str:
    """Markdown özet — anotasyoncunun nereye bakacağını söyler."""
    by_verdict: dict[str, list[Row]] = {}
    for r in rows:
        by_verdict.setdefault(r.verdict, []).append(r)
    total = len(rows) or 1

    lines = [
        "# Kâr Payı Oranı Çapraz Doğrulama Raporu",
        "",
        "> Otomatik üretildi: `python -m scripts.crosscheck_rates`. "
        "Anotasyon CSV'leri DEĞİŞTİRİLMEZ; bu dosya öneridir.",
        "",
        f"- **İncelenen satır:** {len(rows)}",
        "- **Bağımsız kaynak:** bankaların kendi hesaplama uçları / ilan edilen "
        "oran tabloları (`data/raw/*/rates/quotes.jsonl`)",
        "",
        "| Sonuç | Adet | Oran | Anotasyoncu ne yapmalı |",
        "|---|---:|---:|---|",
    ]
    guide = {
        VERDICT_CONFIRMED: "Öneriyi doğrula ve `gold_value`'ya geçir (hızlı)",
        VERDICT_CONFLICT: "Belgeye bak: kural hatası mı, sayfaya özel kampanya mı?",
        VERDICT_NO_SOURCE: "Bağımsız kaynak yok — elle anotasyon "
                           "(makullük kolonuna bak)",
        VERDICT_FIXTURE: "Sentetik demo belgesi — kıyas dışı",
    }
    for v in (VERDICT_CONFIRMED, VERDICT_CONFLICT, VERDICT_NO_SOURCE,
              VERDICT_FIXTURE):
        n = len(by_verdict.get(v, []))
        lines.append(f"| `{v}` | {n} | %{100 * n / total:.1f} | {guide[v]} |")

    # Makullük — ilan edilmiş orana İHTİYAÇ DUYMAZ, bu yüzden çapraz
    # doğrulamanın kapsamadığı satırlarda da sinyal verir.
    plaus: dict[str, list[Row]] = {}
    for r in rows:
        if r.plausibility:
            plaus.setdefault(r.plausibility, []).append(r)
    if plaus:
        lines += [
            "", "## Makullük kontrolü (finansman sayfaları)", "",
            "Finansman ürün sayfasında **aylık** kâr oranı beklenir; ölçülen "
            f"gerçek aralık %1,89–%5,99, üst sınır %{FINANCING_RATE_MAX:.0f} "
            "olarak cömert tutuldu. Bu kontrol ilan edilmiş orana ihtiyaç "
            "duymadığı için çapraz doğrulamanın ulaşamadığı satırlarda da çalışır.",
            "",
            "| Sonuç | Adet | Anlamı |", "|---|---:|---|",
        ]
        meaning = {
            "makul": "değer aylık oran olarak makul",
            "vade_gibi": "**değer bir VADE gibi görünüyor** (36, 48, 120...) — "
                         "kural katmanı vadeyi oran sanmış olabilir",
            "sinir_disi": "aylık oran için fazla yüksek — yıllık oran ya da "
                          "başka bir alan karışmış olabilir",
        }
        for k in ("makul", "vade_gibi", "sinir_disi"):
            items = plaus.get(k)
            if items:
                lines.append(f"| `{k}` | {len(items)} | {meaning[k]} |")
        suspicious = plaus.get("vade_gibi", []) + plaus.get("sinir_disi", [])
        if suspicious:
            lines += ["", "<details><summary>Şüpheli değerler</summary>", ""]
            seen_docs: set[tuple[str, str]] = set()
            for r in suspicious:
                key = (r.doc_id, r.model_value)
                if key in seen_docs:
                    continue
                seen_docs.add(key)
                lines.append(f"- `{r.doc_id[:60]}` — çıkarılan "
                             f"**{r.model_value}** (güven {r.model_conf}, "
                             f"{r.plausibility})")
            lines += ["", "</details>", ""]

    lines += ["", "## Kural katmanının bu alandaki isabeti", ""]
    judged = len(by_verdict.get(VERDICT_CONFIRMED, [])) + \
        len(by_verdict.get(VERDICT_CONFLICT, []))
    if judged:
        acc = 100 * len(by_verdict.get(VERDICT_CONFIRMED, [])) / judged
        lines += [
            f"Bağımsız kaynakla kıyaslanabilen **{judged}** satırda kural "
            f"katmanının isabeti **%{acc:.1f}**.",
            "",
            "Bu, modelin kendi çıktısına değil bankanın ilan ettiği değere karşı "
            "ölçülmüş bir sayıdır; gold set doldurulmadan önce elde edilebilen "
            "tek gerçek doğruluk göstergesidir.",
            "",
        ]
    else:
        lines += ["Kıyaslanabilen satır yok.", ""]

    # Güven eşiğine göre kırılım — düşük güvenli satırların gerçekten kötü olup
    # olmadığını ölçer (kalibrasyon kanıtı).
    lines += ["## Güven skoruna göre isabet", "",
              "| Model güveni | Doğrulandı | Çelişiyor | İsabet |",
              "|---|---:|---:|---:|"]
    buckets: dict[str, list[Row]] = {}
    for r in rows:
        if r.verdict not in (VERDICT_CONFIRMED, VERDICT_CONFLICT):
            continue
        try:
            c = float(r.model_conf)
        except (TypeError, ValueError):
            c = -1.0
        key = "bilinmiyor" if c < 0 else ("yüksek (≥0,90)" if c >= 0.90
                                          else "orta (0,70–0,89)" if c >= 0.70
                                          else "düşük (<0,70)")
        buckets.setdefault(key, []).append(r)
    for key in ("yüksek (≥0,90)", "orta (0,70–0,89)", "düşük (<0,70)",
                "bilinmiyor"):
        items = buckets.get(key)
        if not items:
            continue
        ok = sum(1 for r in items if r.verdict == VERDICT_CONFIRMED)
        bad = len(items) - ok
        lines.append(f"| {key} | {ok} | {bad} | %{100 * ok / len(items):.1f} |")

    # Tazelik — anotasyona başlamadan önce bilinmesi gereken en kritik şey.
    fresh: dict[str, list[Row]] = {}
    for r in rows:
        if r.freshness:
            fresh.setdefault(r.freshness, []).append(r)
    if fresh:
        stale = sum(len(v) for k, v in fresh.items() if k.startswith("bayat"))
        lines += [
            "", "## Tazelik — CSV'deki `model_value` mevcut kuralla uyuşuyor mu?",
            "",
            "Anotasyon CSV'lerindeki `model_value`, ön-anotasyonun KOŞTUĞU ANDAKİ "
            "model çıktısıdır. Kural katmanı o günden beri değiştiyse anotasyoncu "
            "**artık var olmayan bir modelin** çıktısını doğrular; üretilen gold ve "
            "ondan çıkan metrikler yanlış modele ait olur.",
            "",
            "| Durum | Adet | Anlamı |", "|---|---:|---|",
        ]
        meaning = {
            "guncel": "CSV değeri mevcut kuralın ürettiğiyle aynı",
            "bayat_farkli": "**mevcut kural FARKLI bir değer üretiyor**",
            "bayat_fazla": "CSV değer taşıyor, mevcut kural artık üretmiyor "
                           "(hata düzeltilmiş)",
            "bayat_eksik": "CSV boş, mevcut kural artık değer üretiyor",
        }
        for k in ("guncel", "bayat_fazla", "bayat_farkli", "bayat_eksik"):
            items = fresh.get(k)
            if items:
                lines.append(f"| `{k}` | {len(items)} | {meaning[k]} |")
        if stale:
            lines += [
                "",
                f"**{stale} satır bayat.** Anotasyona başlamadan önce "
                "ön-anotasyonun yeniden koşturulması gerekir "
                "(`python -m scripts.preannotate`), aksi halde emek eski model "
                "çıktısına harcanır.",
                "",
            ]

    lines += ["", "## Çelişen satırlar (öncelikli inceleme)", ""]
    conflicts = by_verdict.get(VERDICT_CONFLICT, [])
    if conflicts:
        lines += ["| Belge | Banka | Çıkarılan | İlan edilen | Güven |",
                  "|---|---|---|---|---:|"]
        for r in conflicts[:60]:
            lines.append(f"| `{r.doc_id[:52]}` | {r.bank} | "
                         f"`{r.model_value or '—'}` | {r.published} | "
                         f"{r.model_conf} |")
        if len(conflicts) > 60:
            lines.append(f"| … | | | +{len(conflicts) - 60} satır | |")
    else:
        lines.append("Çelişen satır yok.")
    lines.append("")
    return "\n".join(lines)


def main(argv: Optional[list[str]] = None) -> int:
    ap = argparse.ArgumentParser(
        description="Gold oran satırlarını ilan edilen oranlarla çapraz doğrula")
    ap.add_argument("--raw-dir", default="data/raw")
    ap.add_argument("--gold-dir", default="data/gold")
    ap.add_argument("--field", default="kar_payi_orani")
    ap.add_argument("--out", default="data/gold/rate_crosscheck.csv")
    ap.add_argument("--report", default="data/gold/rate_crosscheck.md")
    args = ap.parse_args(argv)

    published = load_published(args.raw_dir)
    gold_rows = load_gold_rows(args.gold_dir)
    fixtures = load_fixture_doc_ids(args.raw_dir)
    current = current_rule_values(field=args.field)
    if not published:
        print("UYARI: ilan edilmis oran kaydi bulunamadi "
              "(once `python -m src.scraping.harvest_rates` kosun)")
    rows = crosscheck(gold_rows, published, field=args.field, fixtures=fixtures,
                      current=current)
    if not rows:
        print(f"'{args.field}' alaninda satir bulunamadi")
        return 0

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].to_csv()), delimiter=";")
        w.writeheader()
        for r in rows:
            w.writerow(r.to_csv())

    report = Path(args.report)
    report.write_text(render_report(rows), encoding="utf-8")

    counts: dict[str, int] = {}
    for r in rows:
        counts[r.verdict] = counts.get(r.verdict, 0) + 1
    print(f"{len(rows)} satir incelendi ({len(published)} ilan edilmis oran)")
    for k in (VERDICT_CONFIRMED, VERDICT_CONFLICT, VERDICT_NO_SOURCE,
              VERDICT_FIXTURE):
        print(f"  {k}: {counts.get(k, 0)}")
    plaus: dict[str, int] = {}
    for r in rows:
        if r.plausibility:
            plaus[r.plausibility] = plaus.get(r.plausibility, 0) + 1
    if plaus:
        print("  makullük (finansman sayfaları):",
              ", ".join(f"{k}={v}" for k, v in sorted(plaus.items())))
    fresh: dict[str, int] = {}
    for r in rows:
        if r.freshness:
            fresh[r.freshness] = fresh.get(r.freshness, 0) + 1
    if fresh:
        print("  tazelik:", ", ".join(f"{k}={v}" for k, v in sorted(fresh.items())))
    print(f"CSV: {out}\nRapor: {report}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
