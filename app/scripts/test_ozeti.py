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

Tazelik ölçütü `git_sha == HEAD` OLAMAZ: artefaktı commit'lemek HEAD'i
değiştirir ve artefakt daha doğduğu anda bayatlar. Kapı bunun yerine
"kaydedilen commit ile bugün arasında **test sonucunu değiştirebilecek** bir
şey değişti mi" diye sorar (`kanit_tazeligi.TEST_ETKILEYEN`). Aynı dar tanım
buradaki `git_dirty` için de geçerli: bir README düzenlemesi testleri
etkilemez, kaynak/test/bağımlılık değişikliği etkiler.

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

# Test sonucunu değiştirebilecek yollar. Kapı (`scripts/kanit_tazeligi.py`)
# aynı listeyi kullanır ve buraya oradan gelir — iki kopya ayrışırsa artefakt
# "taze" derken kapı "bayat" der ve ikisi de haklı görünür.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.kanit_tazeligi import TEST_ETKILEYEN, _yol_suzgeci

# `TEST_ETKILEYEN` burada yeniden dışa verilir: testler iki modülün AYNI
# nesneyi paylaştığını çitliyor. Ayrışırsa artefakt "taze" derken kapı
# "bayat" der ve ikisi de haklı görünür.
__all__ = ["TEST_ETKILEYEN", "git_durumu", "kos", "main"]

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
    """(HEAD sha, KAYNAK kirli mi)

    "Kirli" burada dar bir anlam taşır: **test sonucunu değiştirebilecek**
    bir dosya commit'lenmemiş mi? Bir README düzenlemesi testleri
    etkilemez; onu kirlilik saymak artefaktı gereksiz yere kullanılamaz
    kılar. Kaynak, test ve bağımlılık değişikliği ise sayılır.

    Artefaktın kendisi de kapsam dışıdır — aksi hâlde sorun özyinelemeli
    olur: artefakt yazılır, ağaç kirlenir, bir sonraki koşu "kirli ağaçta
    üretildi" der ve artefakt hiçbir zaman kanıt olamaz.
    """
    # `TEST_ETKILEYEN` yolları DEPO KÖKÜNE göredir; git `app/` içinden
    # koşulursa süzgeç hiçbir şeyle eşleşmez ve ağaç her zaman "temiz"
    # görünür — yani kapı sessizce hiçbir şey denetlemez.
    kok = KOK.parent

    def _git(*a: str) -> str:
        return subprocess.run(["git", "-C", str(kok), *a],
                              capture_output=True, text=True,
                              check=True).stdout.strip()

    hedef = (cikti or VARSAYILAN_CIKTI).resolve()
    satirlar = []
    durum = _git("status", "--porcelain", "--untracked-files=all",
                 "--", *_yol_suzgeci())
    for satir in durum.splitlines():
        yol = satir[3:].strip().strip('"')
        if (kok / yol).resolve() == hedef:
            continue
        satirlar.append(satir)
    return _git("rev-parse", "HEAD"), bool(satirlar)


def kos(cikti_yolu: Path | None = None) -> dict[str, object]:
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

    sha, kirli = git_durumu(cikti_yolu)
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
