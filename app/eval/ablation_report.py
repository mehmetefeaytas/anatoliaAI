"""Ablasyon tablosunu ÖLÇÜLMÜŞ `metrics.json`'dan üretir — elle sayı yazma yok.

İlgili: ablation.py (tabloyu üreten koşum), report.py (rapor yazımı)
        ../docs/rapor/ablasyon.md (bu betiğin beslediği belge)

Kullanım:
    python eval/ablation_report.py eval/reports/<koşum>/metrics.json
    python eval/ablation_report.py <strict-koşumu> <tolerant-koşumu> --alan-tablosu

## Neden bu modül var

`docs/rapor/ablasyon.md`'nin tablosu jüriye gösterilecek en ikna edici
artefakt. O tabloyu **elle** yazmak iki hataya davetiye çıkarır:

1. **Kopyalama hatası.** Konsol çıktısından markdown'a 4 kol × 6 kolon sayı
   taşımak; bir hanenin kayması metriği sessizce değiştirir ve kimse
   yakalamaz — çünkü karşılaştırılacak ikinci bir kaynak yoktur.
2. **Bayatlama.** Kod değişip ablasyon yeniden koşulduğunda belgedeki tablo
   eski koşumun sayılarını göstermeye devam eder. Bu, "hangi sürümde
   ölçüldü" sorusunu cevapsız bırakır (CLAUDE.md: kaynaksız iddia yasak).

Çözüm: tablo `metrics.json`'dan TÜRETİLİR. Belgeye yapıştırılan blok her zaman
diskteki ölçümün birebir yansımasıdır ve künyesinde koşumun `git_sha`'sı yazar.

Bu betik **hiçbir sayı hesaplamaz** — yalnız `metrics.json` içindeki değerleri
biçimlendirir. Hesap `eval/run_eval.py` + `eval/stats.py`'de tek yerde durur.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# Alan adı -> tabloda görünecek sıra. `EXTRACTION_FIELDS` sırası korunur ki
# alan tablosu koşumlar arasında satır satır kıyaslanabilir olsun.
_HALL_TANIMSIZ = "ölçülemedi"


def _load(path: Path) -> dict:
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def _fmt_f(value: Any, digits: int = 3) -> str:
    return "—" if value is None else f"{value:.{digits}f}"


def _fmt_ci(ci: dict | None, digits: int = 3) -> str:
    """`0.578 [0.423–0.692]`. GA yoksa em-dash — 0,0 yazmak yalan olurdu."""
    if not ci:
        return "—"
    return (f"{ci['point']:.{digits}f} "
            f"[{ci['low']:.{digits}f}–{ci['high']:.{digits}f}]")


def _fmt_hall(micro: dict) -> str:
    """Halüsinasyon oranı; gold'da `absent` kararı yoksa TANIMSIZdır."""
    rate = micro.get("hallucination_rate")
    return _HALL_TANIMSIZ if rate is None else f"{rate:.3f}"


def md_table(headers: list[str], rows: list[list[str]]) -> str:
    out = ["| " + " | ".join(headers) + " |",
           "|" + "|".join("---" for _ in headers) + "|"]
    out += ["| " + " | ".join(r) + " |" for r in rows]
    return "\n".join(out)


# --------------------------------------------------------------------------- #
# Ana tablo
# --------------------------------------------------------------------------- #
def arms_table(metrics: dict) -> str:
    """Ablasyon ana tablosu: kol başına mikro/makro F1 + GA + halüsinasyon."""
    rows = []
    for arm in metrics["arms"]:
        if not arm.get("available"):
            rows.append([f"`{arm['config']}`", "**ÖLÇÜLMEDİ**", "—", "—", "—", "—"])
            continue
        m = arm["micro"]
        hard = arm.get("hard")
        rows.append([
            f"`{arm['config']}`",
            _fmt_f(m["f1"]),
            _fmt_f(arm["macro_f1"]),
            _fmt_ci(arm.get("ci_micro_f1")),
            _fmt_hall(m),
            _fmt_f(hard["micro"]["f1"]) if hard else "—",
        ])
    return md_table(
        ["konfig", "mikro-F1", "makro-F1", "mikro-F1 %95 GA", "halüsinasyon",
         "mikro-F1 (zor)"], rows)


def counts_table(metrics: dict) -> str:
    """Karışıklık matrisi kırılımı — F1'in NEREDEN geldiği görünsün."""
    rows = []
    for arm in metrics["arms"]:
        if not arm.get("available"):
            continue
        m = arm["micro"]
        rows.append([
            f"`{arm['config']}`", _fmt_f(m["precision"]), _fmt_f(m["recall"]),
            str(m["tp"]), str(m["fp"]), str(m["fn"]), str(m["tn"]),
            str(m["fp_wrong"]), str(m["fp_hallucinated"]),
        ])
    return md_table(
        ["konfig", "P (mikro)", "R (mikro)", "TP", "FP", "FN", "TN",
         "FP (yanlış değer)", "FP (uydurma)"], rows)


def mcnemar_table(metrics: dict, scope: str = "all") -> str:
    """McNemar sonuçları — nokta farkı tek başına kanıt değildir."""
    rows = []
    for c in metrics.get("comparisons", []):
        if c.get("scope") != scope:
            continue
        mc = c["mcnemar"]
        winner = mc.get("winner")
        verdict = ("fark anlamsız" if winner is None
                   else f"**kazanan `{c['a'] if winner == 'A' else c['b']}`**")
        rows.append([
            f"`{c['a']}`", f"`{c['b']}`", str(mc["b"]), str(mc["c"]),
            str(mc["n_discordant"]), f"{mc['p_value']:.4g}", mc["method"],
            verdict, _fmt_ci(c.get("micro_f1_diff_ci")),
        ])
    if not rows:
        return "_Karşılaştırılacak en az iki ölçülebilen kol yok._"
    return md_table(
        ["A", "B", "b", "c", "uyumsuz", "p", "yöntem", "sonuç",
         "mikro-F1 farkı (A−B) %95 GA"], rows)


# --------------------------------------------------------------------------- #
# Alan bazında kol karşılaştırması
# --------------------------------------------------------------------------- #
def field_matrix(per_field_rows: list[dict], arms: list[str]) -> str:
    """Alan × kol F1 matrisi — hangi kol hangi ALANDA kazandığı görünsün.

    Girdi `per_field.csv`'nin satırlarıdır (aynı koşumdan). Alan bazında
    kırılım olmadan "hibrit kazandı" cümlesi hangi alanların taşıdığını
    saklar — kural katmanının 0.000 aldığı alanlar tam burada görünür.
    """
    by_field: dict[str, dict[str, dict]] = {}
    for row in per_field_rows:
        by_field.setdefault(row["field"], {})[row["config"]] = row

    rows = []
    for field in sorted(by_field):
        cells = [f"`{field}`"]
        best = max((float(by_field[field][a]["f1"])
                    for a in arms if a in by_field[field]), default=0.0)
        for arm in arms:
            row = by_field[field].get(arm)
            if row is None:
                cells.append("—")
                continue
            f1 = float(row["f1"])
            # En iyi kol kalın; hepsi 0,000 ise kalınlaştırma yapılmaz
            # (0,000'ı "kazanan" göstermek yanıltıcı olurdu).
            cells.append(f"**{f1:.3f}**" if (f1 == best and best > 0)
                         else f"{f1:.3f}")
        cells.append(str(by_field[field][arms[0]]["support"])
                     if arms[0] in by_field[field] else "—")
        rows.append(cells)
    return md_table(["alan"] + [f"`{a}`" for a in arms] + ["gold desteği"], rows)


def read_per_field(path: Path) -> list[dict]:
    """`per_field.csv` okur (ayırıcı `;` — Türkçe Excel uyumu)."""
    import csv

    with path.open(encoding="utf-8") as fh:
        return list(csv.DictReader(fh, delimiter=";"))


# --------------------------------------------------------------------------- #
# Künye
# --------------------------------------------------------------------------- #
def provenance(env: dict, metrics: dict) -> str:
    """Sayıların hangi koşuma ait olduğunu belirsiz bırakmayan künye."""
    llm = env.get("llm") or {}
    rows = [
        ["gold dosyası", f"`{env.get('gold_path')}`"],
        ["gold sha256", f"`{(env.get('gold_sha256') or '')[:16]}…`"],
        ["gold kayıt sayısı", str(env.get("gold_records"))],
        ["eşleştirici", ", ".join(f"`{m}`" for m in env.get("matchers", []))],
        ["seed", str(env.get("seed"))],
        ["bootstrap yeniden örnekleme",
         str((env.get("extra") or {}).get("bootstrap_resamples"))],
        ["git sha", f"`{env.get('git_sha')}`"],
        ["commit'lenmemiş değişiklik",
         "**EVET — sayı bir commit'e karşılık gelmiyor**"
         if env.get("git_dirty") else "yok"],
        ["Python", str(env.get("python_version"))],
        ["platform", f"`{env.get('platform')}`"],
        ["LLM istemcisi", f"`{llm.get('client', '—')}`"],
        ["yapılandırılmış çıktı modu", f"`{llm.get('structured_mode', '—')}`"],
        ["üretim zamanı (UTC)", f"`{env.get('created_utc')}`"],
    ]
    return md_table(["künye", "değer"], rows)


def llm_stats(env: dict) -> str:
    """LLM gerçekten çağrıldı mı, kaç kez patladı — sessiz başarısızlık avı."""
    llm = env.get("llm") or {}
    if not llm:
        return "_LLM künyesi yok._"
    rows = [[k, str(llm.get(k))] for k in
            ("available", "strict", "client", "structured_mode", "calls", "ok",
             "parse_error", "http_error", "schema_violation", "repairs")
            if k in llm]
    return md_table(["sayaç", "değer"], rows)


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def render(run_dir: Path, *, with_fields: bool = True) -> str:
    metrics = _load(run_dir / "metrics.json")
    env = _load(run_dir / "env.json")
    matcher = metrics.get("matcher", "?")

    out = [f"### Eşleştirici `{matcher}`", "", arms_table(metrics), "",
           "#### Karışıklık matrisi kırılımı", "", counts_table(metrics), "",
           "#### McNemar (eşleşmiş çiftler, TÜM belgeler)", "",
           mcnemar_table(metrics, "all"), ""]

    per_field_path = run_dir / "per_field.csv"
    if with_fields and per_field_path.is_file():
        arms = [a["config"] for a in metrics["arms"] if a.get("available")]
        out += ["#### Alan bazında F1 (kol karşılaştırması)", "",
                field_matrix(read_per_field(per_field_path), arms), ""]

    out += ["#### Künye", "", provenance(env, metrics), "",
            "#### LLM sayaçları", "", llm_stats(env), ""]
    if metrics.get("notes"):
        out += ["#### Notlar", ""] + [f"- {n}" for n in metrics["notes"]] + [""]
    return "\n".join(out)


def build_arg_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        description="Ablasyon tablosunu metrics.json'dan markdown olarak üretir.")
    ap.add_argument("run_dirs", nargs="+", type=Path,
                    help="ablasyon koşum dizin(ler)i (metrics.json içeren)")
    ap.add_argument("--no-fields", action="store_true",
                    help="alan bazında matrisi atla")
    return ap


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    for run_dir in args.run_dirs:
        if not (run_dir / "metrics.json").is_file():
            print(f"HATA: {run_dir}/metrics.json yok", file=sys.stderr)
            return 2
        print(render(run_dir, with_fields=not args.no_fields))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
