"""İzlenen markdown dosyalarında repo-içi kırık link denetimi.

İlgili: FAZ 0 / G0.6 — depo temizliği sonrası linkler kırılır

## Neden

Depo temizliği (izlenen `.md` sayısını düşürmek) linkleri **sessizce** kırar:
`git rm --cached` dosyayı diskte bırakır, bu yüzden temizliği yapan kişinin
makinesinde her link çalışmaya devam eder. Kırıklık yalnız TEMİZ BİR KLONDA
görünür — yani ilk fark eden jüri olur.

Bu betik `git ls-files` üzerinden gider, yani diskteki değil **depodaki**
gerçeği ölçer. Yerelde var ama izlenmeyen bir hedefe verilen link kırık
sayılır; kasıtlı olan budur.

## Kapsam

Yalnız repo-içi `.md` hedefleri denetlenir. Dış bağlantılar (`http`) ve
çapa (`#bolum`) ağ erişimi ya da başlık ayrıştırması gerektirir; ikisi de bu
kapının işi değil.

## Kullanım

    python -m scripts.link_denetimi
    python -m scripts.link_denetimi --kok /yol/depo
"""

from __future__ import annotations

import argparse
import posixpath
import re
import subprocess
from pathlib import Path

# `[metin](hedef.md)` — çapa ve şema içerenler dışarıda.
LINK = re.compile(r"\]\(([^)#:\s]+\.md)\)")


def izlenen_mdler(kok: Path) -> list[str]:
    cikti = subprocess.run(["git", "-C", str(kok), "ls-files", "*.md"],
                           capture_output=True, text=True, check=True).stdout
    return [s for s in cikti.splitlines() if s]


def izlenen_kume(kok: Path) -> set[str]:
    cikti = subprocess.run(["git", "-C", str(kok), "ls-files"],
                           capture_output=True, text=True, check=True).stdout
    return {s for s in cikti.splitlines() if s}


def kirik_linkler(kok: Path) -> list[tuple[str, str, str]]:
    """(kaynak dosya, link, sebep) üçlüleri."""
    izlenen = izlenen_kume(kok)
    bulunan: list[tuple[str, str, str]] = []
    for dosya in izlenen_mdler(kok):
        p = kok / dosya
        try:
            metin = p.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for hedef in LINK.findall(metin):
            # Yol depo köküne GÖRE normalize edilir. `Path.resolve()` burada
            # kullanılamaz: çalışma dizinine göre çözer ve betik app/ içinden
            # koşulduğunda "app/app/..." üretip var olan dosyaya "yok" der.
            coz = posixpath.normpath(posixpath.join(
                posixpath.dirname(dosya), hedef))
            tam = kok / coz
            if not tam.exists():
                bulunan.append((dosya, hedef, "dosya yok"))
            elif coz not in izlenen:
                bulunan.append((dosya, hedef, "diskte var ama İZLENMİYOR"))
    return bulunan


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Repo-içi markdown link denetimi.")
    ap.add_argument("--kok", default=None, help="depo kökü (varsayılan: git üst dizini)")
    a = ap.parse_args(argv)

    kok = Path(a.kok) if a.kok else Path(
        subprocess.run(["git", "rev-parse", "--show-toplevel"],
                       capture_output=True, text=True, check=True).stdout.strip())

    kirik = kirik_linkler(kok)
    print(f"izlenen .md : {len(izlenen_mdler(kok))}")
    print(f"kırık link  : {len(kirik)}")
    for dosya, link, sebep in kirik:
        print(f"  {dosya} -> {link}  ({sebep})")
    return 1 if kirik else 0


if __name__ == "__main__":
    raise SystemExit(main())
