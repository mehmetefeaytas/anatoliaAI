"""Rapor yazıcı — iddiayı TEKRAR-ÜRETİLEBİLİR KANITA çevirir.

İlgili: ../../syntheses/teslim-ve-degerlendirme-rehberi.md
        CLAUDE.md §16

## Neden diske yazmak zorunda

Eski eval'in tek çıktısı `print()`'ti. Sonuçları:

1. **CI'da metrik regresyon kapısı kurulamaz.** Karşılaştıracak bir önceki
   dosya yok; F1 düşse kimse görmez.
2. **Jüriye kanıt gösterilemez.** "F1 0,86" bir cümledir; `metrics.json` +
   `env.json` bir kanıttır.
3. **Sayı hangi koşulda üretildi bilinmez.** Hangi commit, hangi gold sürümü,
   hangi eşleştirici, hangi seed? Bunlar yazılmazsa sayı tekrar üretilemez ve
   tekrar üretilemeyen sayı bilimsel olarak yoktur.

`env.json` tam olarak bu üçüncü sorunu kapatır: git sha + gold dosyasının
sha256'sı + Python sürümü + konfig + seed + eşleştirici. Gold sessizce
değişirse sha256 değişir ve eski karşılaştırmaların geçersiz olduğu ANLAŞILIR.

## Çıktılar

    eval/reports/<timestamp>/
      metrics.json    makine-okur tüm metrikler (CI kapısı bunu okur)
      report.md       insan-okur tablo (jüri / ekip)
      per_field.csv   alan bazında satırlar (Excel'de hata analizi)
      decisions.csv   BELGE×ALAN düzeyinde ham kararlar (eşleştirilmiş testler)
      env.json        tekrar-üretim künyesi

## decisions.csv neden ayrı bir dosya

`per_field.csv` alan×kapsam düzeyinde TOPLAR; `doc_id` sütunu yoktur. Toplanmış
sayılardan eşleştirilmiş (paired) bir test kurulamaz: McNemar'ın sorduğu soru
"AYNI belgenin AYNI alanında A doğru, B yanlış mıydı?" sorusudur ve toplam
tablo bu bilgiyi geri döndürülemez biçimde yitirir.

`run_eval.DocScore.decisions` bu bilgiyi zaten üretiyordu ama diske hiç
yazılmıyordu — süreç bitince veri çöpe gidiyor, iki ayrı koşum sonradan
eşleştirilemiyordu. `decisions.csv` tam olarak bu boşluğu kapatır:

    matcher;doc_id;field;correct

`matcher` sütunu ŞART: strict ve tolerant iki AYRI geçiştir, aynı (doc_id,
field) çifti iki kez görünür ve karışırlarsa eşleştirme sessizce bozulur.
Tüketici: `scripts/mcnemar_report.py`.
"""

from __future__ import annotations

import csv
import hashlib
import json
import platform
import subprocess
import sys
from dataclasses import dataclass
from dataclasses import field as dc_field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_OUT_DIR = "eval/reports"

# CSV ayırıcısı ';' — TR yerelli Excel virgülü ondalık ayırıcı sanar ve tüm
# tabloyu tek sütuna yığar (aynı gerekçe scripts/to_review_csv.py'de de var).
CSV_DELIMITER = ";"


def timestamp() -> str:
    """`20260731-142530` biçiminde UTC damgası (dizin adı olarak sıralanabilir)."""
    return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")


def git_sha(repo_root: Path | None = None) -> str | None:
    """`git rev-parse HEAD`. Git yoksa / repo değilse `None` (hata değil).

    Ağ çağrısı yok; yalnız yerel git. Başarısızlık sessizce yutulmaz: dönen
    `None` env.json'a yazılır ve okuyan "commit bilinmiyor" olduğunu görür.
    """
    root = repo_root or Path(__file__).resolve().parents[2]
    try:
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=str(root),
            capture_output=True, text=True, check=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        return None
    sha = out.stdout.strip()
    return sha or None


# Ölçümün KENDİ çıktısı. Bunlar türetilmiş veridir: değişmeleri, raporlanan
# sayının tekrar üretilebilirliğini etkilemez.
TURETILMIS_YOLLAR = ("app/eval/reports/",)


def git_dirty(repo_root: Path | None = None) -> bool | None:
    """Çalışma ağacında commit'lenmemiş **kaynak** değişikliği var mı?

    `True` ise raporlanan sayı bir commit'e karşılık GELMEZ; sha tek başına
    yeterli değildir ve bu bilgi gizlenmemeli.

    Ölçümün kendi çıktısı (`eval/reports/`) hesaba KATILMAZ ve bu bir
    gevşetme değil, düzeltmedir: her koşu o dizine yazdığı için bayrak
    özyinelemeli olarak `True`ya kilitleniyordu — bir koşu kirli olmasa bile
    bir öncekinin çıktısı yüzünden kirli görünüyordu. Ölçülmüş sonucu:
    2026-08-12 tarihli gold.v2 raporu `git_dirty=true` ile damgalandı ve
    kanıt-tazeliği kapısı onu haklı olarak reddetti — oysa kusur o koşumda
    değil, bu bayraktaydı.

    Kaynak, test ve yapılandırma değişikliği ise SAYILIR; onlar sayının
    tekrar üretilebilirliğini gerçekten bozar.
    """
    root = repo_root or Path(__file__).resolve().parents[2]
    try:
        # `--untracked-files=all`: git izlenmeyen bir DİZİNİ tek satıra
        # toplar (`?? app/eval/`). Önek eşleşmesi o satırı kaçırır ve
        # türetilmiş çıktı kirlilik sayılır. Dosya bazında listelemek bu
        # belirsizliği kaldırır.
        out = subprocess.run(
            ["git", "status", "--porcelain", "--untracked-files=all"],
            cwd=str(root),
            capture_output=True, text=True, check=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return None
    for satir in out.stdout.splitlines():
        yol = satir[3:].strip().strip('"')
        if not yol:
            continue
        if any(yol.startswith(t) for t in TURETILMIS_YOLLAR):
            continue
        return True
    return False


def sha256_file(path: str | Path) -> str | None:
    """Dosyanın sha256'sı — "eval hangi gold sürümüyle koştu" sorusunun cevabı."""
    p = Path(path)
    try:
        return hashlib.sha256(p.read_bytes()).hexdigest()
    except OSError:
        return None


@dataclass
class EnvInfo:
    """Tekrar-üretim künyesi."""

    config: str
    gold_path: str
    gold_sha256: str | None
    gold_records: int
    matchers: list[str]
    seed: int
    split: str
    git_sha: str | None = None
    git_dirty: bool | None = None
    python_version: str = dc_field(default_factory=lambda: sys.version.split()[0])
    platform: str = dc_field(default_factory=platform.platform)
    created_utc: str = dc_field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat())
    dependencies: str = "yalnız Python stdlib (numpy/scipy/sklearn YOK)"
    llm: dict | None = None
    extra: dict[str, Any] = dc_field(default_factory=dict)

    def as_dict(self) -> dict:
        data = {
            "config": self.config,
            "gold_path": self.gold_path,
            "gold_sha256": self.gold_sha256,
            "gold_records": self.gold_records,
            "matchers": list(self.matchers),
            "seed": self.seed,
            "split": self.split,
            "git_sha": self.git_sha,
            "git_dirty": self.git_dirty,
            "python_version": self.python_version,
            "platform": self.platform,
            "created_utc": self.created_utc,
            "dependencies": self.dependencies,
        }
        if self.llm is not None:
            data["llm"] = self.llm
        if self.extra:
            data["extra"] = self.extra
        return data


def build_env(config: str, gold_path: str, gold_records: int,
              matchers: list[str], seed: int, split: str,
              llm: dict | None = None,
              extra: dict | None = None) -> EnvInfo:
    """Künyeyi ortamdan toplar (git sha, gold sha256, Python, platform)."""
    return EnvInfo(
        config=config,
        gold_path=str(gold_path),
        gold_sha256=sha256_file(gold_path),
        gold_records=gold_records,
        matchers=list(matchers),
        seed=seed,
        split=split,
        git_sha=git_sha(),
        git_dirty=git_dirty(),
        llm=llm,
        extra=dict(extra or {}),
    )


# --------------------------------------------------------------------------- #
# Yazma
# --------------------------------------------------------------------------- #
def make_run_dir(out_dir: str | Path = DEFAULT_OUT_DIR,
                 stamp: str | None = None) -> Path:
    """`<out_dir>/<timestamp>/` dizinini oluşturur ve döndürür."""
    run_dir = Path(out_dir) / (stamp or timestamp())
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


def write_json(path: Path, payload: Any) -> Path:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=False) + "\n",
        encoding="utf-8")
    return path


def write_text(path: Path, text: str) -> Path:
    path.write_text(text if text.endswith("\n") else text + "\n", encoding="utf-8")
    return path


def write_csv(path: Path, rows: list[dict], columns: list[str] | None = None
              ) -> Path:
    """Sözlük listesini CSV'ye yazar (ayırıcı `;`, bkz. `CSV_DELIMITER`)."""
    cols = columns or (list(rows[0]) if rows else [])
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=cols, delimiter=CSV_DELIMITER,
                                extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
    return path


@dataclass
class WrittenReport:
    """Nereye ne yazıldığı — çağıran bunu kullanıcıya basar."""

    run_dir: Path
    files: list[Path] = dc_field(default_factory=list)

    def summary(self) -> str:
        lines = [f"Rapor yazıldı: {self.run_dir}"]
        lines.extend(f"  - {p.name}" for p in self.files)
        return "\n".join(lines)


DECISION_COLUMNS = ["matcher", "doc_id", "field", "correct"]


def write_report(run_dir: Path, *, metrics: dict, env: EnvInfo,
                 markdown: str, per_field_rows: list[dict],
                 per_field_columns: list[str] | None = None,
                 decision_rows: list[dict] | None = None,
                 decision_columns: list[str] | None = None,
                 extra_json: dict[str, Any] | None = None) -> WrittenReport:
    """Dört (veya daha fazla) çıktıyı tek çağrıda yazar.

    `decision_rows` verilirse `decisions.csv` de yazılır (bkz. modül başlığı).
    `None` ise dosya HİÇ üretilmez — boş bir dosya yazmak, kararların
    kaydedildiği ama hepsinin kaybolduğu izlenimini verirdi.
    """
    files = [
        write_json(run_dir / "metrics.json", metrics),
        write_json(run_dir / "env.json", env.as_dict()),
        write_text(run_dir / "report.md", markdown),
        write_csv(run_dir / "per_field.csv", per_field_rows, per_field_columns),
    ]
    if decision_rows is not None:
        files.append(write_csv(run_dir / "decisions.csv", decision_rows,
                               decision_columns or DECISION_COLUMNS))
    for name, payload in (extra_json or {}).items():
        files.append(write_json(run_dir / f"{name}.json", payload))
    return WrittenReport(run_dir, files)


# --------------------------------------------------------------------------- #
# Markdown yardımcıları
# --------------------------------------------------------------------------- #
def md_table(headers: list[str], rows: list[list[str]]) -> str:
    """Hizalanmamış ama geçerli GitHub markdown tablosu."""
    out = ["| " + " | ".join(headers) + " |",
           "|" + "|".join("---" for _ in headers) + "|"]
    out.extend("| " + " | ".join(str(c) for c in row) + " |" for row in rows)
    return "\n".join(out)


def md_env_block(env: EnvInfo) -> str:
    """Raporun künye bölümü — her tabloyla birlikte gitmesi gereken bağlam."""
    dirty = ("bilinmiyor" if env.git_dirty is None
             else ("EVET (dikkat: sayı bir commit'e karşılık gelmiyor)"
                   if env.git_dirty else "hayır"))
    rows = [
        ["konfig", env.config],
        ["gold dosyası", env.gold_path],
        ["gold sha256", (env.gold_sha256 or "okunamadı")[:16] + "…"
         if env.gold_sha256 else "okunamadı"],
        ["gold kayıt sayısı", str(env.gold_records)],
        ["alt küme (split)", env.split],
        ["eşleştirici(ler)", ", ".join(env.matchers)],
        ["seed", str(env.seed)],
        ["git sha", env.git_sha or "bilinmiyor"],
        ["commit'lenmemiş değişiklik", dirty],
        ["Python", env.python_version],
        ["platform", env.platform],
        ["bağımlılık", env.dependencies],
        ["üretim zamanı (UTC)", env.created_utc],
    ]
    return md_table(["künye", "değer"], rows)
