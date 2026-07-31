"""Değerlendirme harness'i — alan bazında P/R/F1 + makro + bootstrap GA + disk.

İlgili: ../../decisions/zor-anlama-vakalari-merkezi.md (zor-vaka alt kümesi)
        ../../syntheses/teslim-ve-degerlendirme-rehberi.md
        scripts/gold_schema.py (KANONİK gold okuyucu)
        CLAUDE.md §16

Kullanım:
    python -m eval.run_eval --gold data/gold/gold.sample.json --config kural
    python -m eval.run_eval --gold data/gold/gold.v1.json --matcher both --split hard

## Bu dosya neden baştan yazıldı — dört kusur

**1. Teslim ettiğimiz sistemi ölçmüyordu.** Eski kod yalnız `extract_all`
(kural katmanı) çağırıyordu; tablo başlığı bunu itiraf ediyordu
(`"KURAL KATMANI"`). Artık tahmin üretimi `eval/predictors.py`'den gelir ve
`--config hibrit` ile API/dashboard'un gerçekten koştuğu hat ölçülür.

**2. `absent_fields` metriğe hiç girmiyordu.** Gold şemasının birinci sınıf
alanı (`scripts/gold_schema.py`) `run_eval.py`'de SIFIR kez geçiyordu. Eski kod
`name in gold_fields` bakıyordu; bu, "anotatör kontrol etti, YOK" ile "anotatör
hiç bakmadı"yı aynı kovaya atar. O ikisi ayrılmadan **precision tanımsızdır ve
halüsinasyon oranı ölçülemez** — projenin merkezindeki "değer uydurmuyoruz"
iddiası (CLAUDE.md §19, §21) tam olarak bu sayıyla ayakta durur. Artık:

    gold'da DEĞER var      -> eşleşme TP, yanlış değer FP+FN, hiç yoksa FN
    gold'da "YOK" yazıyor  -> tahmin ürettiyse FP (HALÜSİNASYON), üretmediyse TN
    gold KARAR VERMEMİŞ    -> metriğe GİRMEZ (sayılır ve raporlanır)

Üçüncü satır disiplinin kendisidir: bilmediğimizi lehimize sayamayız.

**3. Kanonik okuyucu kullanılmıyordu.** Eski kod düz `json.loads` yapıyordu,
`gold_schema.py`'yi import etmiyordu; `gold.v1.json` üretilse bile
`absent_fields` / `unclear_fields` yok sayılırdı. Artık `load_gold()` çağrılır.

**4. Eşleştirme docstring'i yalan söylüyordu.** `_equal` "dict/aralıkta
alan-alan" diyordu, kod düz `==` yapıyordu. Artık `eval/matchers.py`: `strict`
ve `tolerant` yan yana, aralık alan-alan, parada birim zorunlu.

## Neden hem mikro hem MAKRO

Mikro-F1 alanları gözlem sayısına göre ağırlıklar; `vade_ay` neredeyse her
belgede geçtiği için tabloyu domine eder, `alisveris_puani` gibi seyrek alanlar
görünmez olur. Makro-F1 her alana eşit ağırlık verir ve "seyrek alanlarda
çöküyor muyuz" sorusunu cevaplar. 12 alanın hepsi sayıldığı için tek başına
mikro raporlamak zayıf alanları gizlemek olurdu.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from dataclasses import field as dc_field
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from eval import report as report_mod
from eval.matchers import get_matcher, resolve_matchers
from eval.predictors import (
    CONFIG_NAMES,
    DEFAULT_VERIFY_THRESHOLD,
    Predictor,
    build_predictor,
)
from eval.stats import DEFAULT_RESAMPLES, DEFAULT_SEED, bootstrap_ci
from scripts.gold_schema import (
    ALL_HARD_TAGS,
    GoldRecord,
    load_gold,
    validate_gold,
)
from src.extraction.llm.schema import EXTRACTION_FIELDS

SPLITS = ("all", "hard", "easy")


# --------------------------------------------------------------------------- #
# Sayaçlar
# --------------------------------------------------------------------------- #
@dataclass
class Counts:
    """Bir alanın karışıklık matrisi + halüsinasyon kırılımı.

    `tn` (doğru çekimserlik) eski kodda YOKTU; "kontrol ettim, yok" kararları
    hiç ödüllendirilmiyordu. Şimdi var: gold `absent_fields`'ta olan ve modelin
    de üretmediği alan TN'dir ve `hallucination_rate`'in paydasıdır.

    `fp` iki alt türe ayrılır — farklı hatalardır, farklı düzeltme gerektirir:
      fp_hallucinated: gold "YOK" diyor, model bir değer UYDURDU.
      fp_wrong:        gold'da değer var, model YANLIŞ değer üretti.
    """

    tp: int = 0
    fp: int = 0
    fn: int = 0
    tn: int = 0
    fp_hallucinated: int = 0
    fp_wrong: int = 0
    skipped: int = 0          # gold karar vermemiş (metrik dışı)
    unclear: int = 0          # anotatör "belirsiz" dedi (metrik dışı)

    def add(self, other: Counts) -> None:
        self.tp += other.tp
        self.fp += other.fp
        self.fn += other.fn
        self.tn += other.tn
        self.fp_hallucinated += other.fp_hallucinated
        self.fp_wrong += other.fp_wrong
        self.skipped += other.skipped
        self.unclear += other.unclear

    def precision(self) -> float:
        d = self.tp + self.fp
        return self.tp / d if d else 0.0

    def recall(self) -> float:
        d = self.tp + self.fn
        return self.tp / d if d else 0.0

    def f1(self) -> float:
        p, r = self.precision(), self.recall()
        return 2 * p * r / (p + r) if (p + r) else 0.0

    @property
    def support(self) -> int:
        """Gold'da DEĞER bulunan karar sayısı (makro ortalamanın süzgeci)."""
        return self.tp + self.fn

    @property
    def absent_decisions(self) -> int:
        """Gold'da "YOK" denen karar sayısı (halüsinasyon oranının paydası)."""
        return self.tn + self.fp_hallucinated

    def hallucination_rate(self) -> float | None:
        """Gold "YOK" dediği hâlde değer uydurma oranı.

        `None` döner: gold'da hiç `absent_fields` kararı yoksa bu oran
        TANIMSIZDIR ve 0,0 yazmak yalan olur (0,0 "hiç uydurmadık" demektir,
        oysa doğru cevap "ölçemedik"tir).
        """
        d = self.absent_decisions
        return self.fp_hallucinated / d if d else None

    def as_dict(self) -> dict:
        return {
            "precision": self.precision(), "recall": self.recall(),
            "f1": self.f1(),
            "tp": self.tp, "fp": self.fp, "fn": self.fn, "tn": self.tn,
            "fp_hallucinated": self.fp_hallucinated, "fp_wrong": self.fp_wrong,
            "support": self.support, "absent_decisions": self.absent_decisions,
            "hallucination_rate": self.hallucination_rate(),
            "skipped_undecided": self.skipped, "unclear": self.unclear,
        }


@dataclass
class DocScore:
    """TEK BELGENİN katkısı — bootstrap'ın örnekleme birimi.

    Bootstrap belge düzeyinde yeniden örnekler (bkz. `eval/stats.py`); bunun
    çalışabilmesi için sayaçların belge belge AYRIK tutulması gerekir. Toplam
    tabloyu sonradan `aggregate()` üretir.
    """

    doc_id: str
    hard_tags: list[str] = dc_field(default_factory=list)
    per_field: dict[str, Counts] = dc_field(default_factory=dict)
    # McNemar için: (alan adı, karar doğru muydu). Sıra deterministiktir.
    decisions: list[tuple[str, bool]] = dc_field(default_factory=list)

    @property
    def is_hard(self) -> bool:
        return bool(self.hard_tags)


# --------------------------------------------------------------------------- #
# Puanlama
# --------------------------------------------------------------------------- #
def score_document(record: GoldRecord, preds: dict[str, Any],
                   matcher: Callable[[str, Any, Any], Any],
                   fields: Sequence[str] = tuple(EXTRACTION_FIELDS)) -> DocScore:
    """Tek belgeyi puanlar — `absent_fields` dahil, karar verilmemiş alan HARİÇ.

    Karar tablosu (bkz. modül başlığı, kusur 2):

    | gold                   | tahmin     | sonuç        |
    |------------------------|------------|--------------|
    | değer var, eşleşiyor   | var        | TP           |
    | değer var, eşleşmiyor  | var        | FP + FN      |
    | değer var              | yok        | FN           |
    | "YOK" (absent_fields)  | var        | FP (uydurma) |
    | "YOK" (absent_fields)  | yok        | TN           |
    | unclear_fields         | (herhangi) | metrik dışı  |
    | karar yok              | (herhangi) | metrik dışı  |

    Yanlış değer neden FP **ve** FN: model hem olmayan bir şeyi iddia etti
    (precision cezası) hem de doğru değeri kaçırdı (recall cezası). Eski kod
    yalnız FP sayıyordu ve recall'u yapay olarak yükseltiyordu.
    """
    score = DocScore(doc_id=record.id, hard_tags=list(record.hard_tags))
    gold_values = record.fields
    absent = set(record.absent_fields)
    unclear = set(record.unclear_fields)

    for name in fields:
        counts = score.per_field.setdefault(name, Counts())
        has_pred = name in preds

        if name in unclear:
            counts.unclear += 1
            continue

        if name in gold_values:
            if has_pred and matcher(name, preds[name], gold_values[name]):
                counts.tp += 1
                score.decisions.append((name, True))
            elif has_pred:
                counts.fp += 1
                counts.fp_wrong += 1
                counts.fn += 1
                score.decisions.append((name, False))
            else:
                counts.fn += 1
                score.decisions.append((name, False))
            continue

        if name in absent:
            if has_pred:
                counts.fp += 1
                counts.fp_hallucinated += 1
                score.decisions.append((name, False))
            else:
                counts.tn += 1
                score.decisions.append((name, True))
            continue

        # Gold bu alan hakkında KARAR VERMEMİŞ. Tahmin varsa da yoksa da
        # metriğe girmez — bilmediğimizi lehimize sayamayız.
        counts.skipped += 1

    return score


def score_all(records: Sequence[GoldRecord], predictor: Predictor,
              matcher: Callable[[str, Any, Any], Any]) -> list[DocScore]:
    """Tüm belgeleri puanlar. Tahmin ÜRETİMİ belge başına bir kez yapılır."""
    return [score_document(r, predictor.predict(r.text), matcher) for r in records]


# --------------------------------------------------------------------------- #
# Toplama
# --------------------------------------------------------------------------- #
def aggregate(docs: Iterable[DocScore]) -> dict[str, Counts]:
    """Belge puanlarını alan bazında toplar."""
    table: dict[str, Counts] = {}
    for doc in docs:
        for name, counts in doc.per_field.items():
            table.setdefault(name, Counts()).add(counts)
    return table


def micro(table: dict[str, Counts]) -> Counts:
    """Tüm alanların sayaçlarını tek karışıklık matrisine indirir."""
    total = Counts()
    for counts in table.values():
        total.add(counts)
    return total


def macro_f1(table: dict[str, Counts]) -> float:
    """Alanların F1 ORTALAMASI — yalnız gold desteği olan alanlar üzerinden.

    Süzgeç `support > 0` (gold'da en az bir DEĞER kararı olan alan). Desteksiz
    alanın recall'u tanımsızdır; onu 0 sayıp ortalamaya katmak makro-F1'i gold
    setinin kapsamına göre keyfî biçimde düşürür.
    """
    scores = [c.f1() for c in table.values() if c.support > 0]
    return sum(scores) / len(scores) if scores else 0.0


def micro_f1_of(docs: Sequence[DocScore]) -> float:
    """Bootstrap'ın çağırdığı istatistik: belge listesi -> mikro-F1."""
    return micro(aggregate(docs)).f1()


def macro_f1_of(docs: Sequence[DocScore]) -> float:
    """Bootstrap'ın çağırdığı istatistik: belge listesi -> makro-F1."""
    return macro_f1(aggregate(docs))


# --------------------------------------------------------------------------- #
# Alt kümeler
# --------------------------------------------------------------------------- #
def select_split(records: Sequence[GoldRecord], split: str) -> list[GoldRecord]:
    """`all` | `hard` | `easy` alt kümesini seçer."""
    if split == "all":
        return list(records)
    if split == "hard":
        return [r for r in records if r.hard_tags]
    if split == "easy":
        return [r for r in records if not r.hard_tags]
    raise ValueError(f"bilinmeyen split {split!r}. Seçenekler: {', '.join(SPLITS)}")


def by_hard_tag(docs: Sequence[DocScore]) -> dict[str, dict[str, Counts]]:
    """Zor-vaka ETİKETİ başına ayrı tablo.

    Tek bir `hard: bool` bayrağı "hibrit NEREDE kazandı" sorusunu
    cevaplayamıyordu; `gold_schema.HARD_TAGS` altı kategori tanımlar ve bir
    belge birden çok kategoride olabilir (çok etiketli), o yüzden bu tablolar
    ÖRTÜŞÜR ve toplamları belge sayısını aşabilir.
    """
    out: dict[str, dict[str, Counts]] = {}
    for doc in docs:
        for tag in doc.hard_tags:
            table = out.setdefault(tag, {})
            for name, counts in doc.per_field.items():
                table.setdefault(name, Counts()).add(counts)
    return out


# --------------------------------------------------------------------------- #
# Değerlendirme (tek eşleştirici)
# --------------------------------------------------------------------------- #
@dataclass
class MatcherResult:
    """Bir eşleştiriciyle üretilmiş tüm metrikler."""

    matcher: str
    docs: list[DocScore]
    table: dict[str, Counts]
    micro: Counts
    macro_f1: float
    hard_table: dict[str, Counts]
    hard_docs: int
    per_tag: dict[str, dict[str, Counts]]
    ci_micro: Any = None
    ci_macro: Any = None

    def as_dict(self) -> dict:
        data: dict[str, Any] = {
            "matcher": self.matcher,
            "documents": len(self.docs),
            "hard_documents": self.hard_docs,
            "micro": self.micro.as_dict(),
            "macro_f1": self.macro_f1,
            "macro_support_fields": sum(1 for c in self.table.values()
                                        if c.support > 0),
            "per_field": {k: v.as_dict() for k, v in sorted(self.table.items())},
        }
        if self.hard_table:
            data["hard"] = {
                "micro": micro(self.hard_table).as_dict(),
                "macro_f1": macro_f1(self.hard_table),
                "per_field": {k: v.as_dict()
                              for k, v in sorted(self.hard_table.items())},
            }
        if self.per_tag:
            data["per_hard_tag"] = {
                tag: {"micro": micro(t).as_dict(), "macro_f1": macro_f1(t)}
                for tag, t in sorted(self.per_tag.items())
            }
        if self.ci_micro is not None:
            data["ci_micro_f1"] = self.ci_micro.as_dict()
        if self.ci_macro is not None:
            data["ci_macro_f1"] = self.ci_macro.as_dict()
        return data


def evaluate(records: Sequence[GoldRecord], predictor: Predictor,
             matcher_name: str, *,
             bootstrap: bool = True,
             n_resamples: int = DEFAULT_RESAMPLES,
             seed: int = DEFAULT_SEED) -> MatcherResult:
    """Tek konfig + tek eşleştirici için tüm metrikleri üretir."""
    matcher = get_matcher(matcher_name)
    docs = score_all(records, predictor, matcher)
    table = aggregate(docs)
    hard_docs = [d for d in docs if d.is_hard]

    result = MatcherResult(
        matcher=matcher_name,
        docs=docs,
        table=table,
        micro=micro(table),
        macro_f1=macro_f1(table),
        hard_table=aggregate(hard_docs) if hard_docs else {},
        hard_docs=len(hard_docs),
        per_tag=by_hard_tag(docs),
    )

    if bootstrap and docs:
        result.ci_micro = bootstrap_ci(docs, micro_f1_of,
                                       n_resamples=n_resamples, seed=seed)
        result.ci_macro = bootstrap_ci(docs, macro_f1_of,
                                       n_resamples=n_resamples, seed=seed)
    return result


# --------------------------------------------------------------------------- #
# Çıktı biçimlendirme
# --------------------------------------------------------------------------- #
def format_table(title: str, table: dict[str, Counts]) -> str:
    """Konsol tablosu — alan satırları + MİKRO + MAKRO."""
    lines = [f"=== {title} ===",
             (f"{'alan':<22}{'P':>7}{'R':>7}{'F1':>7}{'TP':>5}{'FP':>5}"
              f"{'FN':>5}{'TN':>5}{'UYD':>5}{'ATL':>5}")]
    for name, c in sorted(table.items()):
        lines.append(
            f"{name:<22}{c.precision():>7.3f}{c.recall():>7.3f}{c.f1():>7.3f}"
            f"{c.tp:>5}{c.fp:>5}{c.fn:>5}{c.tn:>5}{c.fp_hallucinated:>5}"
            f"{c.skipped:>5}")
    m = micro(table)
    lines.append("-" * 73)
    lines.append(
        f"{'MİKRO':<22}{m.precision():>7.3f}{m.recall():>7.3f}{m.f1():>7.3f}"
        f"{m.tp:>5}{m.fp:>5}{m.fn:>5}{m.tn:>5}{m.fp_hallucinated:>5}"
        f"{m.skipped:>5}")
    lines.append(f"{'MAKRO (F1 ort.)':<22}{'':>7}{'':>7}{macro_f1(table):>7.3f}")
    return "\n".join(lines)


def _rate_str(rate: float | None) -> str:
    return "ölçülemedi (gold'da absent kararı yok)" if rate is None else f"{rate:.3f}"


def format_result(result: MatcherResult, predictor: Predictor) -> str:
    """Bir eşleştiricinin tam konsol çıktısı."""
    parts = [format_table(
        f"{predictor.name.upper()} / {result.matcher} — TÜM VAKALAR", result.table)]

    m = result.micro
    parts.append(
        f"\nhalüsinasyon oranı (gold 'YOK' derken üretilen değer): "
        f"{_rate_str(m.hallucination_rate())}"
        f"  [{m.fp_hallucinated}/{m.absent_decisions}]")
    if m.skipped:
        parts.append(
            f"metrik dışı bırakılan (gold karar vermemiş) alan-kararı: {m.skipped}"
            f"  — bilinmeyen lehimize sayılmadı")
    if m.unclear:
        parts.append(f"anotatör 'belirsiz' dedi, metrik dışı: {m.unclear}")

    if result.ci_micro is not None:
        parts.append(f"\nmikro-F1 %95 GA: {result.ci_micro.fmt()}  "
                     f"(belge düzeyi bootstrap, n={result.ci_micro.n_units} belge, "
                     f"{result.ci_micro.n_resamples} örnek, seed="
                     f"{result.ci_micro.seed})")
        parts.append(f"makro-F1 %95 GA: {result.ci_macro.fmt()}")

    if result.hard_table:
        parts.append("\n" + format_table(
            f"{predictor.name.upper()} / {result.matcher} — ZOR VAKALAR "
            f"({result.hard_docs} belge)", result.hard_table))

    if result.per_tag:
        parts.append("\n=== ZOR-VAKA ETİKETİ KIRILIMI (etiketler ÖRTÜŞÜR) ===")
        parts.append(f"{'etiket':<18}{'mikro-F1':>10}{'makro-F1':>10}{'TP':>6}"
                     f"{'FP':>6}{'FN':>6}")
        for tag, table in sorted(result.per_tag.items()):
            mm = micro(table)
            parts.append(f"{tag:<18}{mm.f1():>10.3f}{macro_f1(table):>10.3f}"
                         f"{mm.tp:>6}{mm.fp:>6}{mm.fn:>6}")
    return "\n".join(parts)


def per_field_rows(results: list[MatcherResult], config: str) -> list[dict]:
    """`per_field.csv` satırları — Excel'de hata analizi için."""
    rows = []
    for result in results:
        for scope, table in (("all", result.table), ("hard", result.hard_table)):
            for name, c in sorted(table.items()):
                rows.append({
                    "config": config, "matcher": result.matcher, "scope": scope,
                    "field": name,
                    "precision": round(c.precision(), 4),
                    "recall": round(c.recall(), 4),
                    "f1": round(c.f1(), 4),
                    "tp": c.tp, "fp": c.fp, "fn": c.fn, "tn": c.tn,
                    "fp_hallucinated": c.fp_hallucinated,
                    "fp_wrong": c.fp_wrong,
                    "support": c.support,
                    "absent_decisions": c.absent_decisions,
                    "skipped_undecided": c.skipped,
                    "unclear": c.unclear,
                })
    return rows


PER_FIELD_COLUMNS = [
    "config", "matcher", "scope", "field", "precision", "recall", "f1",
    "tp", "fp", "fn", "tn", "fp_hallucinated", "fp_wrong", "support",
    "absent_decisions", "skipped_undecided", "unclear",
]


def markdown_report(results: list[MatcherResult], predictor: Predictor,
                    env: report_mod.EnvInfo) -> str:
    """`report.md` gövdesi — jüri ve ekip için insan-okur rapor."""
    out = [f"# Değerlendirme raporu — konfig `{predictor.name}`", "",
           predictor.description, "",
           "## Künye (tekrar-üretim)", "", report_mod.md_env_block(env), ""]

    out += [
        "## Metrik tanımları", "",
        "- **TP**: gold'da değer var, tahmin eşleşti.",
        ("- **FP**: tahmin var ama yanlış (`fp_wrong`) ya da gold \"YOK\" diyor "
         "(`fp_hallucinated`)."),
        "- **FN**: gold'da değer var, tahmin yok ya da yanlış.",
        "- **TN**: gold \"YOK\" diyor, model de üretmedi (doğru çekimserlik).",
        ("- **ATL (atlanan)**: gold bu alan hakkında KARAR VERMEMİŞ — metriğe "
         "girmez. Bilmediğimizi lehimize saymıyoruz."),
        ("- **halüsinasyon oranı** = `fp_hallucinated / (tn + fp_hallucinated)`; "
         "gold'da hiç `absent_fields` kararı yoksa TANIMSIZDIR (0,0 yazmak yalan "
         "olurdu)."),
        ("- **makro-F1**: alanların F1 ortalaması (yalnız gold desteği olan "
         "alanlar). Mikro seyrek alanları gizler, makro gizlemez."),
        ("- **%95 GA**: belge düzeyinde küme bootstrap. Aynı belgeden çıkan 12 "
         "alan bağımsız değildir; alan düzeyinde örneklemek GA'yı yapay olarak "
         "daraltır (bkz. `eval/stats.py`)."),
        "",
    ]

    for result in results:
        m = result.micro
        out += [f"## Eşleştirici: `{result.matcher}`", ""]
        rows = [[
            "TÜMÜ", f"{m.precision():.3f}", f"{m.recall():.3f}",
            f"{m.f1():.3f}", f"{result.macro_f1:.3f}",
            result.ci_micro.fmt() if result.ci_micro else "—",
            _rate_str(m.hallucination_rate()),
        ]]
        if result.hard_table:
            hm = micro(result.hard_table)
            rows.append([
                f"ZOR ({result.hard_docs} belge)", f"{hm.precision():.3f}",
                f"{hm.recall():.3f}", f"{hm.f1():.3f}",
                f"{macro_f1(result.hard_table):.3f}", "—",
                _rate_str(hm.hallucination_rate()),
            ])
        out += [report_mod.md_table(
            ["alt küme", "P (mikro)", "R (mikro)", "F1 (mikro)", "F1 (makro)",
             "mikro-F1 %95 GA", "halüsinasyon"], rows), ""]

        out += ["### Alan bazında", "",
                report_mod.md_table(
                    ["alan", "P", "R", "F1", "TP", "FP", "FN", "TN",
                     "uydurma", "atlanan"],
                    [[name, f"{c.precision():.3f}", f"{c.recall():.3f}",
                      f"{c.f1():.3f}", c.tp, c.fp, c.fn, c.tn,
                      c.fp_hallucinated, c.skipped]
                     for name, c in sorted(result.table.items())]),
                ""]

        if result.per_tag:
            out += ["### Zor-vaka etiketi kırılımı", "",
                    "Etiketler çok değerlidir; tablolar ÖRTÜŞÜR.", "",
                    report_mod.md_table(
                        ["etiket", "mikro-F1", "makro-F1", "TP", "FP", "FN"],
                        [[tag, f"{micro(t).f1():.3f}", f"{macro_f1(t):.3f}",
                          micro(t).tp, micro(t).fp, micro(t).fn]
                         for tag, t in sorted(result.per_tag.items())]),
                    ""]
    return "\n".join(out)


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def build_arg_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        description="Gold set üzerinde P/R/F1 + makro + bootstrap GA; diske yazar.")
    ap.add_argument("--gold", required=True, help="gold JSON dosyası")
    ap.add_argument("--config", default="kural", choices=list(CONFIG_NAMES),
                    help="tahmin konfigürasyonu. 'hibrit' teslim edilen sistemdir "
                         "ama LLM gerektirir; varsayılan 'kural' offline çalışır.")
    ap.add_argument("--matcher", default="both",
                    choices=["strict", "tolerant", "both"],
                    help="eşleştirici (varsayılan: both — ikisi de raporlanır)")
    ap.add_argument("--split", default="all", choices=list(SPLITS),
                    help="değerlendirilecek alt küme (varsayılan: all)")
    ap.add_argument("--out-dir", default=report_mod.DEFAULT_OUT_DIR,
                    help=f"rapor kök dizini (varsayılan: {report_mod.DEFAULT_OUT_DIR})")
    ap.add_argument("--no-write", action="store_true",
                    help="diske yazma (yalnız konsol)")
    ap.add_argument("--seed", type=int, default=DEFAULT_SEED,
                    help=f"bootstrap çekirdeği (varsayılan: {DEFAULT_SEED})")
    ap.add_argument("--resamples", type=int, default=DEFAULT_RESAMPLES,
                    help=f"bootstrap örnek sayısı (varsayılan: {DEFAULT_RESAMPLES})")
    ap.add_argument("--no-bootstrap", action="store_true",
                    help="güven aralığı hesaplamayı atla (hızlı koşum)")
    ap.add_argument("--verify-threshold", type=float,
                    default=DEFAULT_VERIFY_THRESHOLD,
                    help="hibrit-verify konfigi için güven eşiği")
    ap.add_argument("--strict-gold", action="store_true",
                    help="gold doğrulama hatası varsa çık (varsayılan: uyar, devam et)")
    return ap


def main(argv: list[str] | None = None) -> int:
    """Çıkış kodu: 0 başarılı, 2 kullanım/veri hatası, 3 konfig ölçülemedi."""
    args = build_arg_parser().parse_args(argv)

    gold_path = Path(args.gold)
    if not gold_path.is_file():
        print(f"HATA: gold dosyası bulunamadı: {gold_path}", file=sys.stderr)
        return 2

    records = load_gold(gold_path)
    if not records:
        print(f"HATA: {gold_path} içinde hiç kayıt yok. Boş gold ile üretilen bir "
              f"metrik yanıltıcıdır; çıkılıyor.", file=sys.stderr)
        return 2

    errors = validate_gold(records)
    if errors:
        head = "\n".join(f"  - {e}" for e in errors[:10])
        more = f"\n  ... (+{len(errors) - 10} hata daha)" if len(errors) > 10 else ""
        print(f"UYARI: gold doğrulama {len(errors)} hata buldu:\n{head}{more}",
              file=sys.stderr)
        if args.strict_gold:
            return 2

    selected = select_split(records, args.split)
    if not selected:
        print(f"HATA: '{args.split}' alt kümesi boş ({len(records)} kayıt içinde). "
              f"Ölçülecek bir şey yok.", file=sys.stderr)
        return 2

    predictor = build_predictor(args.config, verify_threshold=args.verify_threshold)
    if not predictor.available:
        print(f"HATA: konfig '{predictor.name}' ölçülemedi.\n"
              f"  {predictor.unavailable_reason}", file=sys.stderr)
        return 3

    matcher_names = resolve_matchers(args.matcher)
    results = [
        evaluate(selected, predictor, name,
                 bootstrap=not args.no_bootstrap,
                 n_resamples=args.resamples, seed=args.seed)
        for name in matcher_names
    ]

    print(f"\nkonfig : {predictor.name} — {predictor.description}")
    print(f"gold   : {gold_path} ({len(records)} kayıt, alt küme "
          f"'{args.split}' -> {len(selected)} belge)")
    for result in results:
        print("\n" + format_result(result, predictor))

    if args.no_write:
        print("\n(--no-write verildi: diske yazılmadı)")
        return 0

    env = report_mod.build_env(
        config=predictor.name, gold_path=str(gold_path),
        gold_records=len(selected), matchers=matcher_names,
        seed=args.seed, split=args.split,
        llm=predictor.llm_summary,
        extra={"gold_total_records": len(records),
               "gold_validation_errors": len(errors),
               "bootstrap_resamples": (0 if args.no_bootstrap else args.resamples)})

    metrics = {
        "config": predictor.name,
        "config_description": predictor.description,
        "split": args.split,
        "documents": len(selected),
        "gold_total_records": len(records),
        "fields_evaluated": list(EXTRACTION_FIELDS),
        "hard_tags_known": list(ALL_HARD_TAGS),
        "results": [r.as_dict() for r in results],
    }

    run_dir = report_mod.make_run_dir(args.out_dir)
    written = report_mod.write_report(
        run_dir, metrics=metrics, env=env,
        markdown=markdown_report(results, predictor, env),
        per_field_rows=per_field_rows(results, predictor.name),
        per_field_columns=PER_FIELD_COLUMNS)
    print("\n" + written.summary())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
