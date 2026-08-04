"""Ablasyon: kural vs LLM vs hibrit — hibridin kazandığını İSTATİSTİKLE kanıtla.

İlgili: ../../decisions/zor-anlama-vakalari-merkezi.md (özellikle ZOR vakalarda)
        ../../syntheses/teslim-ve-degerlendirme-rehberi.md, CLAUDE.md §16
        eval/predictors.py (tahmin üretimi TEK KAYNAĞI)
        eval/stats.py (McNemar + bootstrap)

Kullanım:
    python -m eval.ablation --gold data/gold/gold.sample.json
    python -m eval.ablation --gold data/gold/gold.v1.json --matcher tolerant

Jüri için en ikna edici tek artefakt budur (CLAUDE.md §16). Ama "hibrit 0,02
daha yüksek" cümlesi tek başına kanıt DEĞİLDİR: fark gürültü olabilir. Bu yüzden
her konfig çifti için **McNemar testi** koşulur (eşleşmiş çiftler, uyumsuzluğa
odaklı) ve sonuç diske yazılır.

## Eski hâlindeki üç kusur

**1. `run_eval` ile aynı tahmin kümesini üretmiyordu.** `run_eval` `is not None`
süzgeci, ablasyon `f.is_present` kullanıyordu; iki harness'ın sayıları
kıyaslanabilir değildi. Artık ikisi de `eval/predictors.py`'den beslenir.

**2. `absent_fields` yoktu**, dolayısıyla halüsinasyon oranı ölçülemiyordu.
Artık `eval/run_eval.py:score_document` kullanılır (aynı puanlama çekirdeği —
iki harness'ın ayrışması imkânsız).

**3. Diske hiçbir şey yazmıyordu** — tek çıktı `print()`'ti. CI'da kapı
kurulamaz, jüriye kanıt gösterilemezdi.

## McNemar'ın eşleştirme birimi

Eşleşmiş çift = **(belge, alan) kararı**. Her kol aynı karar kümesi üzerinde
"doğru/yanlış" üretir; McNemar yalnız UYUMSUZ çiftlere (biri doğru, öbürü
yanlış) bakar. İki kol aynı kararı verdiğinde test bilgi almaz ve almaması
doğrudur — ortak başarı/başarısızlık iki sistemi ayırt etmez.

## Offline dürüstlüğü

LLM yoksa `llm` / `hibrit` / `hibrit-verify` kolları **ÖLÇÜLMEDİ** yazılır ve
atlanır. Eski kod bu durumda "hibrit = kural-only" satırı basıyordu; teknik
olarak doğru ama iletişim olarak yalan — okuyucu hibridin ölçüldüğünü sanır.

## `--matcher both` ve tahmin önbelleği

`run_ablation` her EŞLEŞTİRİCİ için bir kez çağrılır, `score_all` ise belge
başına `predictor.predict()` çağırır. Önbellek olmadan `--matcher both`,
aynı belgeyi LLM'e **iki kez** sorar. Bu iki ayrı soruna yol açar:

**1. Ölçüm kusuru (asıl gerekçe).** `strict` ile `tolerant` tablolarının FARKI,
tanım gereği yalnız eşleştiricinin katılığından gelmelidir. Kol iki kez
sorulursa örnekleme gürültüsü (aynı prompt, farklı çıktı) bu farka SIZAR ve
"tolerant eşleştirici 0,02 kazandırdı" cümlesi ölçülmemiş bir şeyi iddia eder.
`temperature=0` bunu azaltır ama garanti etmez: toplama sırası kaynaklı
kayan-nokta belirsizliği ve sunucu tarafı toplu iş (batching) çıktıyı
değiştirebilir.

**2. Maliyet.** Ölçülen: kol başına 20 belge ≈ 12 dk (Ollama + Qwen2.5-7B,
Apple M5). Üç LLM kolu × iki eşleştirici = ~70 dk; önbellekle ~35 dk.

Çözüm: `cache_predictions` kolu, `fn`'i belge metnine göre bellekleyen bir
kopyayla değiştirir. Böylece tüm eşleştiriciler **aynı** tahmin kümesini
puanlar ve eşleştirici karşılaştırması tek değişkenli kalır.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass, replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from eval import report as report_mod
from eval.matchers import get_matcher, resolve_matchers
from eval.predictors import (
    CONFIG_HIBRIT,
    CONFIG_HIBRIT_VERIFY,
    CONFIG_KURAL,
    CONFIG_LLM,
    CONFIG_NAMES,
    DEFAULT_VERIFY_THRESHOLD,
    Predictor,
    build_all,
)
from eval.run_eval import (
    DocScore,
    aggregate,
    macro_f1,
    micro,
    micro_f1_of,
    score_all,
)
from eval.stats import (
    DEFAULT_RESAMPLES,
    DEFAULT_SEED,
    McNemarResult,
    bootstrap_ci,
    bootstrap_diff_ci,
    mcnemar_from_pairs,
)
from scripts.gold_schema import GoldRecord, load_gold, validate_gold

# Ablasyonun varsayılan kolları. `hibrit-verify` de dâhildir: `reconcile.py`
# docstring'i bu kolun "ablasyonda ayrı satır olarak ölçüldüğünü" söylüyordu
# ama hiçbir çağıran açmıyordu (ölü özellik). Artık gerçekten ölçülüyor.
DEFAULT_ARMS = (CONFIG_KURAL, CONFIG_LLM, CONFIG_HIBRIT, CONFIG_HIBRIT_VERIFY)


@dataclass
class ArmResult:
    """Tek bir ablasyon kolunun sonucu."""

    config: str
    description: str
    docs: list[DocScore]
    available: bool = True
    unavailable_reason: str | None = None
    ci_micro: object = None

    @property
    def table(self) -> dict:
        return aggregate(self.docs)

    @property
    def hard_table(self) -> dict:
        return aggregate([d for d in self.docs if d.is_hard])

    def as_dict(self) -> dict:
        if not self.available:
            return {"config": self.config, "available": False,
                    "reason": self.unavailable_reason}
        table = self.table
        m = micro(table)
        data = {
            "config": self.config,
            "description": self.description,
            "available": True,
            "documents": len(self.docs),
            "micro": m.as_dict(),
            "macro_f1": macro_f1(table),
        }
        hard = self.hard_table
        if hard:
            data["hard"] = {
                "documents": sum(1 for d in self.docs if d.is_hard),
                "micro": micro(hard).as_dict(),
                "macro_f1": macro_f1(hard),
            }
        if self.ci_micro is not None:
            data["ci_micro_f1"] = self.ci_micro.as_dict()
        return data


def decision_vector(docs: list[DocScore]) -> list[tuple[str, str, bool]]:
    """`(belge, alan) -> doğru mu` vektörü — McNemar'ın eşleştirme birimi.

    Sıra deterministiktir (belge sırası + alan sırası korunur), böylece iki
    kolun vektörleri birebir hizalanır. Hizalama testin tüm gücüdür.
    """
    return [(doc.doc_id, name, ok) for doc in docs for name, ok in doc.decisions]


def paired_correctness(a: list[DocScore], b: list[DocScore]
                       ) -> tuple[list[bool], list[bool]]:
    """İki kolun ORTAK kararları üzerinde hizalanmış doğru/yanlış dizileri.

    Ortak kesişim alınır: hizalanamayan çift teste GİRMEMELİDİR. Sessizce
    kaydırmak (ör. `zip` ile kısaltmak) eşleştirmeyi bozar ve p-değerini
    anlamsız kılar.
    """
    da = {(doc_id, field): ok for doc_id, field, ok in decision_vector(a)}
    db = {(doc_id, field): ok for doc_id, field, ok in decision_vector(b)}
    keys = sorted(set(da) & set(db))
    return [da[k] for k in keys], [db[k] for k in keys]


@dataclass
class Comparison:
    """İki kolun karşılaştırması: McNemar + EŞLEŞMİŞ bootstrap fark GA'sı."""

    a: str
    b: str
    scope: str
    mcnemar: McNemarResult
    diff_ci: object = None

    def as_dict(self) -> dict:
        data = {"a": self.a, "b": self.b, "scope": self.scope,
                "mcnemar": self.mcnemar.as_dict()}
        if self.diff_ci is not None:
            data["micro_f1_diff_ci"] = self.diff_ci.as_dict()
        return data

    def line(self) -> str:
        winner = self.mcnemar.winner
        who = ("fark anlamsız" if winner is None
               else f"kazanan: {self.a if winner == 'A' else self.b}")
        return f"{self.a} vs {self.b} [{self.scope}]: {self.mcnemar.fmt()} — {who}"


def compare_arms(arms: list[ArmResult], *, seed: int = DEFAULT_SEED,
                 n_resamples: int = DEFAULT_RESAMPLES,
                 alpha: float = 0.05) -> list[Comparison]:
    """Tüm ölçülebilen kol çiftleri için McNemar + eşleşmiş fark GA'sı."""
    live = [a for a in arms if a.available and a.docs]
    out: list[Comparison] = []
    for i, arm_a in enumerate(live):
        for arm_b in live[i + 1:]:
            for scope in ("all", "hard"):
                da = (arm_a.docs if scope == "all"
                      else [d for d in arm_a.docs if d.is_hard])
                db = (arm_b.docs if scope == "all"
                      else [d for d in arm_b.docs if d.is_hard])
                if not da or not db:
                    continue
                ca, cb = paired_correctness(da, db)
                if not ca:
                    continue
                test = mcnemar_from_pairs(ca, cb, alpha=alpha)

                # Eşleşmiş fark GA'sı: aynı yeniden örneklenmiş BELGE kümesi
                # her iki kola verilir. İki BAĞIMSIZ GA'nın çakışmasına bakmak
                # yaygın bir hatadır ve farkın anlamlılığını yanlış ölçer.
                diff_ci = None
                index_b = {d.doc_id: d for d in db}
                shared = [(d, index_b[d.doc_id]) for d in da if d.doc_id in index_b]
                if shared:
                    diff_ci = bootstrap_diff_ci(
                        shared,
                        lambda pairs: micro_f1_of([p[0] for p in pairs]),
                        lambda pairs: micro_f1_of([p[1] for p in pairs]),
                        n_resamples=n_resamples, seed=seed)
                out.append(Comparison(arm_a.config, arm_b.config, scope,
                                      test, diff_ci))
    return out


# --------------------------------------------------------------------------- #
# Koşum
# --------------------------------------------------------------------------- #
def cache_predictions(predictor: Predictor) -> Predictor:
    """Kolun tahminlerini belge metnine göre belleyen bir KOPYASINI döndürür.

    Neden gerekli: bkz. modül başlığı, "`--matcher both` ve tahmin önbelleği".
    Kısaca — eşleştirici başına yeniden sormak, eşleştirici karşılaştırmasına
    LLM örnekleme gürültüsü karıştırır ve maliyeti ikiye katlar.

    Özgün `predictor` DEĞİŞTİRİLMEZ (`dataclasses.replace` ile kopya üretilir);
    çağıran hâlâ önbelleksiz kolu elinde tutar. Ölçülemeyen kol olduğu gibi
    döner: `fn`'i sarmalamak `available=False` sözleşmesini (çağrıda
    `PredictorError`) gizlerdi.

    Anahtar belge METNİdir, `doc_id` değil: `score_all` yalnız metni görür ve
    aynı metin iki farklı `doc_id` altında geçerse tahmin yine aynı olmalıdır.
    """
    if not predictor.available:
        return predictor

    inner = predictor.fn
    store: dict[str, list] = {}

    def cached(text: str) -> list:
        if text not in store:
            store[text] = inner(text)
        return store[text]

    return replace(predictor, fn=cached)


def run_ablation(records: list[GoldRecord], predictors: list[Predictor],
                 matcher_name: str, *, bootstrap: bool = True,
                 n_resamples: int = DEFAULT_RESAMPLES,
                 seed: int = DEFAULT_SEED) -> list[ArmResult]:
    """Her kolu puanlar. Kullanılamayan kol ATLANIR (sahte satır üretilmez)."""
    matcher = get_matcher(matcher_name)
    arms: list[ArmResult] = []
    for predictor in predictors:
        if not predictor.available:
            arms.append(ArmResult(predictor.name, predictor.description, [],
                                  available=False,
                                  unavailable_reason=predictor.unavailable_reason))
            continue
        docs = score_all(records, predictor, matcher)
        arm = ArmResult(predictor.name, predictor.description, docs)
        if bootstrap and docs:
            arm.ci_micro = bootstrap_ci(docs, micro_f1_of,
                                        n_resamples=n_resamples, seed=seed)
        arms.append(arm)
    return arms


def format_arms(arms: list[ArmResult], matcher_name: str) -> str:
    """Ablasyon tablosu (konsol)."""
    lines = [f"=== ABLASYON — eşleştirici '{matcher_name}' ===",
             (f"{'konfig':<16}{'F1(tüm)':>9}{'makro':>8}{'F1(zor)':>9}"
              f"{'TP':>6}{'FP':>6}{'FN':>6}{'UYD':>6}  mikro-F1 %95 GA")]
    for arm in arms:
        if not arm.available:
            lines.append(f"{arm.config:<16}{'ÖLÇÜLMEDİ':>9}   (bkz. NOTLAR)")
            continue
        table = arm.table
        m = micro(table)
        hard = arm.hard_table
        hard_f1 = f"{micro(hard).f1():.3f}" if hard else "—"
        ci = arm.ci_micro.fmt() if arm.ci_micro is not None else "—"
        lines.append(f"{arm.config:<16}{m.f1():>9.3f}{macro_f1(table):>8.3f}"
                     f"{hard_f1:>9}{m.tp:>6}{m.fp:>6}{m.fn:>6}"
                     f"{m.fp_hallucinated:>6}  {ci}")
    return "\n".join(lines)


def format_comparisons(comparisons: list[Comparison]) -> str:
    if not comparisons:
        return ("\n=== İSTATİSTİKSEL KARŞILAŞTIRMA ===\n"
                "Karşılaştırılacak en az iki ÖLÇÜLEBİLEN kol yok.")
    lines = ["\n=== İSTATİSTİKSEL KARŞILAŞTIRMA (McNemar, eşleşmiş çiftler) ===",
             ("b = ilk kol doğru & ikinci yanlış; c = tersi. Uyumlu çiftler "
              "teste girmez."),
             "Yöntem: b+c < 25 ise TAM BİNOM, değilse süreklilik düzeltmeli χ².",
             ""]
    for comparison in comparisons:
        lines.append("  " + comparison.line())
        if comparison.diff_ci is not None:
            ci = comparison.diff_ci
            zero = ("0 GA İÇİNDE (fark kanıtlanmadı)"
                    if ci.low <= 0 <= ci.high else "0 GA DIŞINDA (fark kanıtlandı)")
            lines.append(f"      mikro-F1 farkı (A−B): {ci.fmt()} → {zero}")
    return "\n".join(lines)


def markdown_report(arms: list[ArmResult], comparisons: list[Comparison],
                    matcher_name: str, env: report_mod.EnvInfo,
                    notes: list[str]) -> str:
    out = ["# Ablasyon raporu — kural vs LLM vs hibrit", "",
           "## Künye (tekrar-üretim)", "", report_mod.md_env_block(env), "",
           f"## Kollar (eşleştirici `{matcher_name}`)", ""]

    rows = []
    for arm in arms:
        if not arm.available:
            rows.append([arm.config, "ÖLÇÜLMEDİ", "—", "—", "—", "—"])
            continue
        table = arm.table
        m = micro(table)
        hard = arm.hard_table
        rate = m.hallucination_rate()
        rows.append([
            arm.config, f"{m.f1():.3f}", f"{macro_f1(table):.3f}",
            f"{micro(hard).f1():.3f}" if hard else "—",
            arm.ci_micro.fmt() if arm.ci_micro is not None else "—",
            f"{rate:.3f}" if rate is not None else "ölçülemedi",
        ])
    out += [report_mod.md_table(
        ["konfig", "mikro-F1 (tüm)", "makro-F1", "mikro-F1 (zor)",
         "mikro-F1 %95 GA", "halüsinasyon"], rows), ""]

    out += ["## İstatistiksel karşılaştırma (McNemar)", "",
            ("Eşleşmiş çift = **(belge, alan) kararı**. Test yalnız UYUMSUZ "
             "çiftlere bakar; iki kol aynı kararı verdiğinde ayırt edici bilgi "
             "yoktur."), "",
            ("Yöntem seçimi: `b + c < 25` ise **tam binom testi**, değilse "
             "**süreklilik düzeltmeli χ²**. χ², kesikli binom dağılımına "
             "yapılan sürekli bir yaklaşımdır ve `b + c` küçükken hatası "
             "göreli olarak büyür (ör. b=8, c=0: tam test 0,0078, χ² 0,0133). "
             "Hangi yöntemin kullanıldığı her satırda yazar."), ""]
    if comparisons:
        out += [report_mod.md_table(
            ["A", "B", "alt küme", "b", "c", "p", "yöntem", "sonuç",
             "mikro-F1 farkı (A−B) %95 GA"],
            [[c.a, c.b, c.scope, c.mcnemar.b, c.mcnemar.c,
              f"{c.mcnemar.p_value:.4g}", c.mcnemar.method,
              ("fark anlamsız" if c.mcnemar.winner is None
               else f"kazanan {c.a if c.mcnemar.winner == 'A' else c.b}"),
              c.diff_ci.fmt() if c.diff_ci is not None else "—"]
             for c in comparisons]), ""]
    else:
        out += ["Karşılaştırılacak en az iki ölçülebilen kol yok.", ""]

    if notes:
        out += ["## Notlar (sessiz sınırlama YOK)", ""]
        out += [f"- {n}" for n in notes]
        out += [""]
    return "\n".join(out)


def per_field_rows(arms: list[ArmResult], matcher_name: str) -> list[dict]:
    rows = []
    for arm in arms:
        if not arm.available:
            continue
        for name, c in sorted(arm.table.items()):
            rows.append({
                "config": arm.config, "matcher": matcher_name, "scope": "all",
                "field": name,
                "precision": round(c.precision(), 4),
                "recall": round(c.recall(), 4), "f1": round(c.f1(), 4),
                "tp": c.tp, "fp": c.fp, "fn": c.fn, "tn": c.tn,
                "fp_hallucinated": c.fp_hallucinated, "fp_wrong": c.fp_wrong,
                "support": c.support, "absent_decisions": c.absent_decisions,
                "skipped_undecided": c.skipped, "unclear": c.unclear,
            })
    return rows


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def build_arg_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        description="Ablasyon: kural / LLM / hibrit karşılaştırması + McNemar.")
    ap.add_argument("--gold", required=True, help="gold JSON dosyası")
    ap.add_argument("--arms", default=",".join(DEFAULT_ARMS),
                    help=f"virgülle ayrılmış konfig listesi "
                         f"(seçenekler: {', '.join(CONFIG_NAMES)})")
    ap.add_argument("--matcher", default="strict",
                    choices=["strict", "tolerant", "both"],
                    help="eşleştirici (varsayılan: strict — savunulabilir taban)")
    ap.add_argument("--out-dir", default=report_mod.DEFAULT_OUT_DIR,
                    help=f"rapor kök dizini (varsayılan: {report_mod.DEFAULT_OUT_DIR})")
    ap.add_argument("--no-write", action="store_true", help="diske yazma")
    ap.add_argument("--seed", type=int, default=DEFAULT_SEED)
    ap.add_argument("--resamples", type=int, default=DEFAULT_RESAMPLES)
    ap.add_argument("--no-bootstrap", action="store_true")
    ap.add_argument("--alpha", type=float, default=0.05,
                    help="McNemar anlamlılık düzeyi (varsayılan: 0.05)")
    ap.add_argument("--verify-threshold", type=float,
                    default=DEFAULT_VERIFY_THRESHOLD,
                    help="hibrit-verify kolunun güven eşiği")
    return ap


def main(argv: list[str] | None = None) -> int:
    """Çıkış kodu: 0 başarılı, 2 kullanım/veri hatası."""
    args = build_arg_parser().parse_args(argv)

    gold_path = Path(args.gold)
    if not gold_path.is_file():
        print(f"HATA: gold dosyası bulunamadı: {gold_path}", file=sys.stderr)
        return 2

    records = load_gold(gold_path)
    if not records:
        print(f"HATA: {gold_path} içinde hiç kayıt yok.", file=sys.stderr)
        return 2
    errors = validate_gold(records)
    if errors:
        print(f"UYARI: gold doğrulama {len(errors)} hata buldu (ilk: {errors[0]})",
              file=sys.stderr)

    arm_names = [a.strip() for a in args.arms.split(",") if a.strip()]
    unknown = [a for a in arm_names if a not in CONFIG_NAMES]
    if unknown:
        print(f"HATA: bilinmeyen kol(lar) {unknown}. Seçenekler: "
              f"{', '.join(CONFIG_NAMES)}", file=sys.stderr)
        return 2

    predictors = build_all(arm_names, verify_threshold=args.verify_threshold)
    matcher_names = resolve_matchers(args.matcher)
    # Tüm eşleştiriciler AYNI tahmin kümesini puanlamalı — yoksa eşleştirici
    # farkına LLM gürültüsü sızar. Bkz. modül başlığı.
    predictors = [cache_predictions(p) for p in predictors]

    notes = [f"`{p.name}` ÖLÇÜLMEDİ: {p.unavailable_reason}"
             for p in predictors if not p.available]

    print(f"\ngold: {gold_path} ({len(records)} kayıt, "
          f"{sum(1 for r in records if r.hard_tags)} zor)")

    for matcher_name in matcher_names:
        arms = run_ablation(records, predictors, matcher_name,
                            bootstrap=not args.no_bootstrap,
                            n_resamples=args.resamples, seed=args.seed)
        comparisons = compare_arms(arms, seed=args.seed,
                                   n_resamples=args.resamples, alpha=args.alpha)

        print("\n" + format_arms(arms, matcher_name))
        print(format_comparisons(comparisons))
        if notes:
            print("\nNOTLAR (sessiz sınırlama yok):")
            for note in notes:
                print(f"  - {note}")

        if args.no_write:
            continue

        # Sayaçlar koşum SIRASINDA artar; künye bu yüzden koşumdan SONRA
        # okunur. Erken okumak rapora her zaman `calls: 0` yazdırırdı.
        llm_summary = next((p.llm_summary for p in predictors
                            if p.llm_summary is not None), None)

        env = report_mod.build_env(
            config=f"ablation[{','.join(arm_names)}]", gold_path=str(gold_path),
            gold_records=len(records), matchers=[matcher_name],
            seed=args.seed, split="all", llm=llm_summary,
            extra={"arms": arm_names,
                   "arms_measured": [a.config for a in arms if a.available],
                   "arms_skipped": [a.config for a in arms if not a.available],
                   "alpha": args.alpha,
                   "verify_threshold": args.verify_threshold,
                   "bootstrap_resamples": (0 if args.no_bootstrap
                                           else args.resamples)})
        metrics = {
            "kind": "ablation",
            "matcher": matcher_name,
            "documents": len(records),
            "hard_documents": sum(1 for r in records if r.hard_tags),
            "arms": [a.as_dict() for a in arms],
            "comparisons": [c.as_dict() for c in comparisons],
            "notes": notes,
        }
        run_dir = report_mod.make_run_dir(args.out_dir)
        written = report_mod.write_report(
            run_dir, metrics=metrics, env=env,
            markdown=markdown_report(arms, comparisons, matcher_name, env, notes),
            per_field_rows=per_field_rows(arms, matcher_name))
        print("\n" + written.summary())

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
