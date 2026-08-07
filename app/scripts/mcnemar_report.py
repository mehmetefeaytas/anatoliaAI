"""İki koşumun EŞLEŞTİRİLMİŞ karşılaştırması — McNemar + eşleşmiş fark GA'sı.

İlgili: eval/stats.py (istatistiğin kendisi), eval/report.py (`decisions.csv`),
        eval/run_eval.py (`decision_rows`), docs/rapor/gold-genisletme.md

## Bu betik neden var

`eval/run_eval.py` her koşumda `decisions.csv` yazıyor: BELGE×ALAN düzeyinde
"bu karar doğru muydu". İki ayrı koşumun (ör. çerçeve ayıklaması açık / kapalı)
bu dosyaları elde varken, aradaki farkın gürültü olup olmadığı EŞLEŞTİRİLMİŞ
olarak sınanabilir.

**Neden eşleştirme şart:** iki bağımsız güven aralığının örtüşüp örtüşmediğine
bakmak yaygın bir hatadır. Aynı belgeler iki kola da verildiği için kolların
hataları KORELELİDİR; eşleştirilmiş tasarım bu ortak varyansı düşürür ve
gerçek farkı görebilir. GA'lar örtüşürken McNemar anlamlı çıkabilir — bu bir
çelişki değil, eşleştirmenin kazandırdığı güçtür.

## Ne ölçülür, ne ÖLÇÜLMEZ

`decisions.csv` yalnız "karar doğru muydu" bilgisini taşır; TP/FP/FN ayrımını
taşımaz. Dolayısıyla buradan **F1 türetilemez**. Bu betiğin ürettiği iki sayı:

- **McNemar** — uyumsuz çiftler (b, c) üzerinde YÖN testi.
- **Eşleşmiş bootstrap fark GA'sı** — aynı yeniden örneklenmiş BELGE kümesi
  iki kola da verilerek hesaplanan **karar doğruluğu** (accuracy) farkı.

İkisi de AYNI büyüklüğü konu alır (karar doğruluğu), o yüzden birlikte
okunabilirler: GA farkın BÜYÜKLÜĞÜNÜ, McNemar YÖNÜNÜ söyler. Mikro-F1 güven
aralıkları `run_eval`'in kendi bootstrap'ından (`metrics.json`) okunur; bu
betik onları ÜRETMEZ, yalnız varsa künyeye yazar.

Bootstrap birimi **belgedir**, alan değil. Alan düzeyinde örneklemek aynı
belgeden gelen kararların bağımsız olduğunu varsayar ve GA'yı yapay olarak
daraltır (gerekçe: `eval/stats.py:166` docstring'i).

## Hizalama

Anahtar `(matcher, doc_id, field)`. `matcher` ŞART: strict ve tolerant AYRI
geçişlerdir ve aynı `(doc_id, field)` çifti iki kez görünür.

Hizalanamayan anahtar **sessizce atılmaz**: sayısı ve örnekleri hem konsola
hem JSON/markdown çıktısına yazılır. Sessiz atma, iki koşumun aslında farklı
belge kümelerinde koştuğu durumu gizler ve "fark yok" gibi görünen sahte bir
sonuç üretir (bu projede bir kez yaşandı: bkz. `docs/rapor/gold-genisletme.md`
"Bulunan ve düzeltilen bir ölçüm kusuru").

## Kullanım

    .venv/bin/python -m scripts.mcnemar_report \\
        --a eval/reports/<damga-A> --b eval/reports/<damga-B> \\
        --ad-a temel --ad-b n-gram \\
        --matcher strict --markdown /tmp/mcnemar.md
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Sequence

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from eval.report import CSV_DELIMITER, DECISION_COLUMNS
from eval.stats import (
    DEFAULT_CONFIDENCE,
    DEFAULT_RESAMPLES,
    DEFAULT_SEED,
    EXACT_THRESHOLD,
    BootstrapResult,
    McNemarResult,
    bootstrap_ci,
    bootstrap_diff_ci,
    mcnemar_from_pairs,
)

DECISIONS_FILENAME = "decisions.csv"

# CSV'den okunan `correct` sütununun kabul edilen gösterimleri.
# `bool("False") == True` olduğu için ham `bool()` çevrimi KULLANILMAZ.
_TRUE = frozenset({"1", "true", "True", "TRUE", "evet", "dogru", "doğru"})
_FALSE = frozenset({"0", "false", "False", "FALSE", "hayir", "hayır", "yanlis",
                    "yanlış"})

Key = tuple[str, str, str]  # (matcher, doc_id, field)


# --------------------------------------------------------------------------
# Okuma
# --------------------------------------------------------------------------
def resolve_decisions_path(path: str | Path) -> Path:
    """Dosya yolu ya da `run_eval` çıktı dizini -> `decisions.csv` yolu."""
    p = Path(path)
    if p.is_dir():
        p = p / DECISIONS_FILENAME
    if not p.is_file():
        raise FileNotFoundError(
            f"karar dökümü bulunamadı: {p}. `run_eval` bu dosyayı yazıyor mu? "
            f"(--no-write verilmiş koşumlarda yazılmaz)")
    return p


def _parse_correct(raw: str, path: Path, line: int) -> bool:
    value = (raw or "").strip()
    if value in _TRUE:
        return True
    if value in _FALSE:
        return False
    raise ValueError(
        f"{path}:{line} — `correct` sütunu çözümlenemedi: {raw!r}. "
        f"Beklenen 0/1 (ya da true/false).")


def load_decisions(path: str | Path) -> dict[Key, bool]:
    """`decisions.csv` -> `(matcher, doc_id, field) -> doğru mu` sözlüğü.

    Aynı anahtar iki kez geçerse HATA yükseltilir. Sessizce üzerine yazmak,
    iki farklı geçişin birbirini ezdiği durumu gizler ve eşleştirmeyi bozar.
    """
    csv_path = resolve_decisions_path(path)
    out: dict[Key, bool] = {}
    with csv_path.open(encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh, delimiter=CSV_DELIMITER)
        missing = [c for c in DECISION_COLUMNS if c not in (reader.fieldnames or [])]
        if missing:
            raise ValueError(
                f"{csv_path} eksik sütun taşıyor: {', '.join(missing)}. "
                f"Beklenen başlık: {CSV_DELIMITER.join(DECISION_COLUMNS)}")
        for line, row in enumerate(reader, start=2):
            key: Key = (row["matcher"], row["doc_id"], row["field"])
            if key in out:
                raise ValueError(
                    f"{csv_path}:{line} — anahtar iki kez geçiyor: {key}. "
                    f"Eşleştirme bozulur, koşum kontrol edilmeli.")
            out[key] = _parse_correct(row["correct"], csv_path, line)
    if not out:
        raise ValueError(f"{csv_path} boş; karşılaştırılacak karar yok.")
    return out


def read_metrics(path: str | Path) -> Optional[dict]:
    """Koşum dizini verildiyse `metrics.json` — yoksa `None` (hata değil)."""
    p = Path(path)
    if not p.is_dir():
        return None
    target = p / "metrics.json"
    if not target.is_file():
        return None
    try:
        return json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def micro_f1_ci(metrics: Optional[dict], matcher: str) -> Optional[dict]:
    """`metrics.json` içindeki ilgili eşleştiricinin mikro-F1 GA künyesi."""
    if not metrics:
        return None
    for result in metrics.get("results", []):
        if result.get("matcher") == matcher:
            return result.get("ci_micro_f1")
    return None


# --------------------------------------------------------------------------
# Hizalama
# --------------------------------------------------------------------------
@dataclass
class Alignment:
    """İki karar dökümünün kesişimi + hizalanamayan anahtarların dökümü."""

    matcher: str
    keys: list[Key]
    a_correct: list[bool]
    b_correct: list[bool]
    only_a: list[Key]
    only_b: list[Key]

    @property
    def n_common(self) -> int:
        return len(self.keys)

    @property
    def n_unaligned(self) -> int:
        return len(self.only_a) + len(self.only_b)

    def as_dict(self, sample: int = 5) -> dict:
        return {
            "matcher": self.matcher,
            "n_common": self.n_common,
            "n_only_a": len(self.only_a),
            "n_only_b": len(self.only_b),
            "only_a_sample": [list(k) for k in self.only_a[:sample]],
            "only_b_sample": [list(k) for k in self.only_b[:sample]],
        }


def matchers_in(decisions: dict[Key, bool]) -> list[str]:
    return sorted({m for m, _, _ in decisions})


def align(a: dict[Key, bool], b: dict[Key, bool], matcher: str) -> Alignment:
    """Tek eşleştirici için kesişim + fark kümeleri.

    Sıra `sorted` ile sabitlenir: iki dizinin AYNI sırada AYNI birimi anlatması
    testin tüm gücüdür (bkz. `eval/stats.mcnemar_from_pairs`).
    """
    ka = {k for k in a if k[0] == matcher}
    kb = {k for k in b if k[0] == matcher}
    common = sorted(ka & kb)
    return Alignment(
        matcher=matcher,
        keys=common,
        a_correct=[a[k] for k in common],
        b_correct=[b[k] for k in common],
        only_a=sorted(ka - kb),
        only_b=sorted(kb - ka),
    )


# --------------------------------------------------------------------------
# İstatistik
# --------------------------------------------------------------------------
# Bootstrap birimi: BİR BELGENİN tüm (a_dogru, b_dogru) karar çiftleri.
DocUnit = list[tuple[bool, bool]]


def doc_units(alignment: Alignment) -> list[DocUnit]:
    """Hizalanmış kararları BELGE düzeyinde gruplar — bootstrap'ın birimi.

    Aynı belgeden gelen kararlar bağımsız değildir (aynı metin, aynı imla,
    aynı hata kaynağı). Belge birlikte çekilir; alan düzeyinde çekmek GA'yı
    yapay olarak daraltır.
    """
    groups: dict[str, DocUnit] = {}
    for (_, doc_id, _), ok_a, ok_b in zip(alignment.keys, alignment.a_correct,
                                          alignment.b_correct, strict=True):
        groups.setdefault(doc_id, []).append((ok_a, ok_b))
    return [groups[doc_id] for doc_id in sorted(groups)]


def _accuracy(units: Sequence[DocUnit], index: int) -> float:
    """Örneklemdeki karar doğruluğu — payda TOPLAM karar sayısıdır."""
    total = correct = 0
    for unit in units:
        for pair in unit:
            total += 1
            correct += int(pair[index])
    return correct / total if total else 0.0


@dataclass
class PairComparison:
    """İki kolun tek eşleştiricideki karşılaştırması."""

    a_name: str
    b_name: str
    alignment: Alignment
    mcnemar: McNemarResult
    acc_a: float
    acc_b: float
    ci_a: BootstrapResult
    ci_b: BootstrapResult
    diff_ci: BootstrapResult
    n_docs: int
    f1_ci_a: Optional[dict] = None
    f1_ci_b: Optional[dict] = None

    @property
    def ci_overlap(self) -> bool:
        """İki bağımsız GA örtüşüyor mu? (KARAR ÖLÇÜTÜ DEĞİL, yalnız gözlem.)"""
        return not (self.ci_a.low > self.ci_b.high or self.ci_b.low > self.ci_a.high)

    @property
    def diff_significant(self) -> bool:
        """Eşleşmiş fark GA'sı sıfırı DIŞARIDA mı bırakıyor?"""
        return self.diff_ci.low > 0.0 or self.diff_ci.high < 0.0

    def as_dict(self) -> dict:
        data = {
            "a": self.a_name,
            "b": self.b_name,
            "matcher": self.alignment.matcher,
            "alignment": self.alignment.as_dict(),
            "n_documents": self.n_docs,
            "accuracy_a": self.acc_a,
            "accuracy_b": self.acc_b,
            "accuracy_ci_a": self.ci_a.as_dict(),
            "accuracy_ci_b": self.ci_b.as_dict(),
            "accuracy_diff_ci": self.diff_ci.as_dict(),
            "independent_ci_overlap": self.ci_overlap,
            "paired_diff_significant": self.diff_significant,
            "mcnemar": self.mcnemar.as_dict(),
        }
        if self.f1_ci_a is not None:
            data["micro_f1_ci_a"] = self.f1_ci_a
        if self.f1_ci_b is not None:
            data["micro_f1_ci_b"] = self.f1_ci_b
        return data

    def lines(self) -> list[str]:
        winner = self.mcnemar.winner
        who = ("fark anlamsız" if winner is None
               else f"kazanan: {self.a_name if winner == 'A' else self.b_name}")
        out = [
            f"## {self.a_name} ↔ {self.b_name} [{self.alignment.matcher}]",
            f"  hizalanan karar : {self.alignment.n_common} "
            f"({self.n_docs} belge)",
            f"  hizalanamayan   : {self.alignment.n_unaligned} "
            f"(yalnız A: {len(self.alignment.only_a)}, "
            f"yalnız B: {len(self.alignment.only_b)})",
            f"  karar doğruluğu : {self.a_name} {self.ci_a.fmt()} · "
            f"{self.b_name} {self.ci_b.fmt()}",
            f"  eşleşmiş fark   : {self.diff_ci.fmt()} "
            f"({'sıfırı DIŞLIYOR' if self.diff_significant else 'sıfırı içeriyor'})",
            f"  McNemar         : {self.mcnemar.fmt()} — {who}",
        ]
        if self.ci_overlap and self.mcnemar.significant:
            out.append("  NOT: bağımsız GA'lar örtüşüyor ama eşleştirilmiş test "
                       "anlamlı — eşleştirme güç kazandırdı.")
        return out


def compare(a: dict[Key, bool], b: dict[Key, bool], matcher: str, *,
            a_name: str = "A", b_name: str = "B",
            n_resamples: int = DEFAULT_RESAMPLES,
            confidence: float = DEFAULT_CONFIDENCE,
            seed: int = DEFAULT_SEED,
            alpha: float = 0.05,
            exact_threshold: int = EXACT_THRESHOLD,
            f1_ci_a: Optional[dict] = None,
            f1_ci_b: Optional[dict] = None) -> PairComparison:
    """Tek eşleştirici için McNemar + eşleşmiş bootstrap fark GA'sı."""
    alignment = align(a, b, matcher)
    if not alignment.keys:
        raise ValueError(
            f"'{matcher}' eşleştiricisinde ortak karar yok. İki koşum aynı gold "
            f"üzerinde mi koştu? (hizalanamayan: yalnız A "
            f"{len(alignment.only_a)}, yalnız B {len(alignment.only_b)})")

    units = doc_units(alignment)

    def stat_a(sample: Sequence[DocUnit]) -> float:
        return _accuracy(sample, 0)

    def stat_b(sample: Sequence[DocUnit]) -> float:
        return _accuracy(sample, 1)

    return PairComparison(
        a_name=a_name,
        b_name=b_name,
        alignment=alignment,
        mcnemar=mcnemar_from_pairs(alignment.a_correct, alignment.b_correct,
                                   alpha=alpha, exact_threshold=exact_threshold),
        acc_a=stat_a(units),
        acc_b=stat_b(units),
        ci_a=bootstrap_ci(units, stat_a, n_resamples=n_resamples,
                          confidence=confidence, seed=seed),
        ci_b=bootstrap_ci(units, stat_b, n_resamples=n_resamples,
                          confidence=confidence, seed=seed),
        diff_ci=bootstrap_diff_ci(units, stat_a, stat_b, n_resamples=n_resamples,
                                  confidence=confidence, seed=seed),
        n_docs=len(units),
        f1_ci_a=f1_ci_a,
        f1_ci_b=f1_ci_b,
    )


# --------------------------------------------------------------------------
# Rapor
# --------------------------------------------------------------------------
def _fmt(value: float, digits: int = 3) -> str:
    return f"{value:.{digits}f}"


def markdown_report(comparisons: list[PairComparison], *,
                    n_docs: int, alpha: float) -> str:
    """Rapora yapıştırılabilir markdown gövdesi."""
    parts = [
        "# McNemar — eşleştirilmiş karşılaştırma",
        "",
        f"n = **{n_docs} belge**. Küçük örneklem: p-değeri ve GA genişliği "
        "buna göre okunmalıdır.",
        "",
        "Ölçülen büyüklük **karar doğruluğu** (belge×alan kararlarının doğru "
        "oranı). `decisions.csv` TP/FP/FN ayrımını taşımadığı için buradan F1 "
        "türetilemez; mikro-F1 güven aralıkları `run_eval`'in kendi "
        "bootstrap'ından gelir.",
        "",
        "| A | B | eşleştirici | hizalanan | hizalanamayan | doğruluk A | "
        "doğruluk B | eşleşmiş fark %95 GA | b | c | p | yöntem | sonuç |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for cmp_ in comparisons:
        m = cmp_.mcnemar
        winner = m.winner
        verdict = ("anlamsız" if winner is None
                   else f"**{cmp_.a_name if winner == 'A' else cmp_.b_name}**")
        parts.append(
            f"| {cmp_.a_name} | {cmp_.b_name} | {cmp_.alignment.matcher} "
            f"| {cmp_.alignment.n_common} | {cmp_.alignment.n_unaligned} "
            f"| {_fmt(cmp_.acc_a)} | {_fmt(cmp_.acc_b)} "
            f"| {cmp_.diff_ci.fmt()} | {m.b} | {m.c} | {m.p_value:.4g} "
            f"| {m.method} | {verdict} |")
    parts += [
        "",
        f"α = {alpha}. `b` = A doğru & B yanlış, `c` = A yanlış & B doğru. "
        "Uyumlu çiftler teste girmez.",
        "",
    ]
    for cmp_ in comparisons:
        if cmp_.alignment.n_unaligned:
            parts.append(
                f"- **{cmp_.a_name} ↔ {cmp_.b_name} "
                f"[{cmp_.alignment.matcher}]**: "
                f"{cmp_.alignment.n_unaligned} anahtar hizalanamadı "
                f"(yalnız A: {len(cmp_.alignment.only_a)}, yalnız B: "
                f"{len(cmp_.alignment.only_b)}). Teste GİRMEDİLER.")
    return "\n".join(parts) + "\n"


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------
def build_arg_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        description="İki run_eval koşumunu eşleştirilmiş olarak karşılaştırır.")
    ap.add_argument("--a", required=True,
                    help="A kolu: decisions.csv ya da run_eval çıktı dizini")
    ap.add_argument("--b", required=True,
                    help="B kolu: decisions.csv ya da run_eval çıktı dizini")
    ap.add_argument("--ad-a", default=None, help="A kolunun rapordaki adı")
    ap.add_argument("--ad-b", default=None, help="B kolunun rapordaki adı")
    ap.add_argument("--matcher", default=None,
                    help="tek eşleştirici (varsayılan: ikisinde de bulunan hepsi)")
    ap.add_argument("--seed", type=int, default=DEFAULT_SEED)
    ap.add_argument("--resamples", type=int, default=DEFAULT_RESAMPLES)
    ap.add_argument("--confidence", type=float, default=DEFAULT_CONFIDENCE)
    ap.add_argument("--alpha", type=float, default=0.05)
    ap.add_argument("--json", dest="json_out", default=None,
                    help="makine-okur çıktı yolu")
    ap.add_argument("--markdown", dest="md_out", default=None,
                    help="markdown rapor yolu")
    return ap


def main(argv: Optional[list[str]] = None) -> int:
    """Çıkış kodu: 0 başarılı, 2 kullanım/veri hatası."""
    args = build_arg_parser().parse_args(argv)

    try:
        a = load_decisions(args.a)
        b = load_decisions(args.b)
    except (FileNotFoundError, ValueError) as exc:
        print(f"HATA: {exc}", file=sys.stderr)
        return 2

    a_name = args.ad_a or Path(args.a).name
    b_name = args.ad_b or Path(args.b).name
    metrics_a, metrics_b = read_metrics(args.a), read_metrics(args.b)

    if args.matcher:
        matchers = [args.matcher]
    else:
        matchers = [m for m in matchers_in(a) if m in set(matchers_in(b))]
    if not matchers:
        print(f"HATA: iki koşumda ortak eşleştirici yok "
              f"(A: {matchers_in(a)}, B: {matchers_in(b)}).", file=sys.stderr)
        return 2

    comparisons: list[PairComparison] = []
    for matcher in matchers:
        try:
            comparisons.append(compare(
                a, b, matcher, a_name=a_name, b_name=b_name,
                n_resamples=args.resamples, confidence=args.confidence,
                seed=args.seed, alpha=args.alpha,
                f1_ci_a=micro_f1_ci(metrics_a, matcher),
                f1_ci_b=micro_f1_ci(metrics_b, matcher)))
        except ValueError as exc:
            print(f"HATA: {exc}", file=sys.stderr)
            return 2

    n_docs = max(c.n_docs for c in comparisons)
    for cmp_ in comparisons:
        print("\n".join(cmp_.lines()))
        print()

    payload = {
        "a": {"name": a_name, "path": str(args.a)},
        "b": {"name": b_name, "path": str(args.b)},
        "seed": args.seed,
        "resamples": args.resamples,
        "confidence": args.confidence,
        "alpha": args.alpha,
        "n_documents": n_docs,
        "measured_quantity": "karar doğruluğu (belge×alan); F1 DEĞİL",
        "comparisons": [c.as_dict() for c in comparisons],
    }
    if args.json_out:
        Path(args.json_out).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8")
        print(f"json: {args.json_out}")
    if args.md_out:
        Path(args.md_out).write_text(
            markdown_report(comparisons, n_docs=n_docs, alpha=args.alpha),
            encoding="utf-8")
        print(f"markdown: {args.md_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
