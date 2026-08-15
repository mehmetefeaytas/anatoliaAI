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
#
# ANSI renk kodu sayının hemen soluna `m` bırakıyor (`\x1b[32m2873 passed`).
# Baştaki `\b` bu yüzden EŞLEŞMİYORDU — `m` ile `2` ikisi de sözcük karakteri,
# arada sınır yok. Sessiz sonucu: her sayı 0 okunuyordu, yani kanıt artefaktı
# "0 test geçti" diyordu ve kimse fark etmiyordu. Renk kodları önce silinir.
_ANSI = re.compile(r"\x1b\[[0-9;]*m")
_OZET = re.compile(r"(?<!\d)(\d+)\s+(passed|failed|skipped|errors?|xfailed|xpassed)\b")
_TOPLANAN = re.compile(r"(\d+)\s+tests?\s+collected")


def git_durumu(cikti: Path | None = None) -> tuple[str, bool]:
    """(HEAD sha, kirli mi) — artefaktın KENDİSİ kirlilik sayılmaz.

    Aksi hâlde sorun özyinelemeli olur: artefakt yazılır, ağaç kirlenir,
    bir sonraki koşu "kirli ağaçta üretildi" der ve artefakt hiçbir zaman
    kanıt olamaz. Denetlenmek istenen şey KAYNAK durumudur, aracın kendi
    çıktısı değil.
    """
    def _git(*a: str) -> str:
        return subprocess.run(["git", "-C", str(KOK), *a],
                              capture_output=True, text=True,
                              check=True).stdout.strip()

    hedef = (cikti or VARSAYILAN_CIKTI).resolve()
    satirlar = []
    for satir in _git("status", "--porcelain").splitlines():
        yol = satir[3:].strip().strip('"')
        if (KOK.parent / yol).resolve() == hedef:
            continue
        satirlar.append(satir)
    return _git("rev-parse", "HEAD"), bool(satirlar)


def kos(cikti: Path | None = None) -> dict[str, object]:
    proc = subprocess.run([sys.executable, "-m", "pytest", "tests/", "-q"],
                          cwd=KOK, capture_output=True, text=True)
    cikti = _ANSI.sub("", proc.stdout + proc.stderr)
    sayilar = {ad: int(n) for n, ad in _OZET.findall(cikti)}
    if not sayilar:
        raise RuntimeError(
            "pytest özet satırı ayrıştırılamadı — artefakt sıfırlarla "
            f"yazılamaz. Çıktının sonu:\n{cikti[-500:]}")
    toplanan = _TOPLANAN.search(cikti)

    gecti = sayilar.get("passed", 0)
    atlandi = sayilar.get("skipped", 0)
    basarisiz = sayilar.get("failed", 0) + sayilar.get("error", 0) \
        + sayilar.get("errors", 0)

    sha, kirli = git_durumu(cikti)
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

    ozet = kos(a.cikti)
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
