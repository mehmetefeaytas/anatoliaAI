"""Tam test koşusunun sonucunu kanıt artefaktına yazar.

İlgili: scripts/kanit_tazeligi.py (bu artefaktı okur)
        .github/workflows/ci.yml

## Neden ayrı bir artefakt

"2.777 test yeşil" ile "2.830 test toplanıyor" **aynı sayı değildir** ve
ikisini karıştırmak yayımlanan bir iddiayı sessizce yanlış yapar. Fark
atlanan testlerdir (Postgres gerektirenler bağımlılıksız koşuda atlanır).

Kanıt-tazeliği kapısı ucuz olmak zorunda, bu yüzden `--collect-only`
kullanıyor; o da yalnız **toplanan** sayısını verir. Geçen/atlanan ayrımı tam
koşu ister. Çözüm ölçüm hattındakiyle aynı desen: **pahalı ölçüm bir artefakt
üretir, kapı artefaktı okur ve tazeliğini denetler.**

Tazelik ölçütü `git_sha`dır: artefakt HEAD'den başka bir commit'te
üretilmişse kanıt değildir. Kirli ağaçta üretilen artefakt da kanıt sayılmaz —
tekrar üretilemez.

## Kullanım

    python -m scripts.test_ozeti                 # koş ve yaz
    python -m scripts.test_ozeti --cikti YOL
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

KOK = Path(__file__).resolve().parents[1]
VARSAYILAN_CIKTI = KOK / "eval" / "reports" / "test-ozeti.json"

# `2777 passed, 53 skipped, 1 warning ... in 25.35s`
_OZET = re.compile(r"\b(\d+)\s+(passed|failed|skipped|error|errors|xfailed|xpassed)\b")
_TOPLANAN = re.compile(r"(\d+)\s+tests?\s+collected")


def git_durumu() -> tuple[str, bool]:
    def _git(*a: str) -> str:
        return subprocess.run(["git", "-C", str(KOK), *a],
                              capture_output=True, text=True,
                              check=True).stdout.strip()
    return _git("rev-parse", "HEAD"), bool(_git("status", "--porcelain"))


def kos() -> dict[str, object]:
    proc = subprocess.run([sys.executable, "-m", "pytest", "tests/", "-q"],
                          cwd=KOK, capture_output=True, text=True)
    cikti = proc.stdout + proc.stderr
    sayilar = {ad: int(n) for n, ad in _OZET.findall(cikti)}
    toplanan = _TOPLANAN.search(cikti)

    gecti = sayilar.get("passed", 0)
    atlandi = sayilar.get("skipped", 0)
    basarisiz = sayilar.get("failed", 0) + sayilar.get("error", 0) \
        + sayilar.get("errors", 0)

    sha, kirli = git_durumu()
    return {
        # `collected` satırı yalnız `--collect-only`de basılır; tam koşuda
        # toplam, alt sonuçların toplamıdır. İkisi ayrışırsa kapı görsün diye
        # hangi yoldan geldiği yazılır.
        "toplanan": int(toplanan.group(1)) if toplanan else gecti + atlandi + basarisiz,
        "toplanan_kaynagi": "collected satırı" if toplanan else "alt sonuç toplamı",
        "gecti": gecti,
        "atlandi": atlandi,
        "basarisiz": basarisiz,
        "cikis_kodu": proc.returncode,
        "git_sha": sha,
        "git_dirty": kirli,
        "created_utc": datetime.now(UTC).isoformat(),
        "python": sys.version.split()[0],
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Test özeti kanıt artefaktı")
    p.add_argument("--cikti", type=Path, default=VARSAYILAN_CIKTI)
    a = p.parse_args(argv)

    ozet = kos()
    a.cikti.parent.mkdir(parents=True, exist_ok=True)
    a.cikti.write_text(json.dumps(ozet, ensure_ascii=False, indent=2) + "\n",
                       encoding="utf-8")

    print(f"{ozet['toplanan']} toplandı · {ozet['gecti']} geçti · "
          f"{ozet['atlandi']} atlandı · {ozet['basarisiz']} başarısız")
    print(f"yazıldı: {a.cikti}")
    if ozet["git_dirty"]:
        print("⚠️  kirli ağaç — bu artefakt kanıt sayılmaz, temiz ağaçta tekrarla")
    return int(ozet["cikis_kodu"])


if __name__ == "__main__":
    raise SystemExit(main())
