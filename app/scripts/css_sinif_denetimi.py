"""TSX'te kullanılan her CSS sınıfının tanımı VAR MI — mekanik denetim.

İlgili: web/app/styles/*.css, web/app/components/*, tests/test_css_sinif.py

## Bu betiğin varlık sebebi

Arayüz yeniden tasarımından önce **11 sınıfın CSS karşılığı hiç yazılmamıştı**:
`summary-box`, `fairness-item`, `jury-dot`, `fold-open`, `headline-bad` ve
diğerleri. Beş bileşen tarayıcıda stilsiz (varsayılan blok/inline) render
oluyordu ve hiçbir test, hiçbir derleme adımı bunu yakalamıyordu — TypeScript
`className` dizgesinin içine bakmaz, CSS de kimin kendisini kullandığını
bilmez. Kusur ancak ekrana bakınca görülüyordu, o da fark edilirse.

En görünür sonucu şuydu: LLM özeti kaynak metinden görsel olarak ayrışmıyordu,
yani `SummaryNotice` kendi docstring'indeki vaadi tutamıyordu.

Bu betik o boşluğu kapatır: `className` içinde geçen her sabit sınıf adının
stil dosyalarında bir tanımı olmalıdır.

## Neyi denetlemez

Ters yönü — tanımlı ama kullanılmayan sınıfı — denetlemez ve bu bilinçlidir:
`.badge-ner` gibi bazı sınıflar şema uyumluluğu için bilerek duruyor
(NER katmanı bu teslimde üretilmiyor, CLAUDE.md §3). "Ölü CSS" bir kusur
değil, bir tercih olabilir; "tanımsız sınıf" ise her zaman kusurdur.

## Kullanım

    .venv/bin/python -m scripts.css_sinif_denetimi
    .venv/bin/python -m scripts.css_sinif_denetimi --ayrinti

Çıkış kodu: tanımsız sınıf varsa 1, yoksa 0.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

_KOK = Path(__file__).resolve().parents[1]
WEB_APP = _KOK / "web" / "app"
STIL_DIZINI = WEB_APP / "styles"

#: CSS'te sınıf seçicisi.
_CSS_SINIF = re.compile(r"\.(-?[_a-zA-Z][\w-]*)")

#: `className="..."` ve `className={`...`}` gövdesi.
_CLASSNAME = re.compile(r'className=(?:\{`([^`]*)`\}|"([^"]*)")', re.DOTALL)

#: Şablon değişkeni `${...}`. Gövdesi tümüyle atılamaz: koşullu ifadeler
#: `${secili ? " first" : ""}` biçiminde SABİT sınıf adları taşıyor ve onları
#: da denetlemek gerekiyor — `.first` tanımsız olsaydı yakalanmalıydı.
#: Çözüm: değişkenin içindeki dizge sabitleri korunur, gerisi (tanımlayıcılar,
#: operatörler) atılır.
_SABLON_DEGISKENI = re.compile(r"\$\{([^}]*)\}")

#: Bir JS ifadesindeki dizge sabitleri.
_DIZGE_SABITI = re.compile(r"""["']([^"']*)["']""")

#: Geçerli bir CSS sınıf adı.
_GECERLI_AD = re.compile(r"-?[_a-zA-Z][\w-]*$")


def tanimli_siniflar(stil_dizini: Path = STIL_DIZINI) -> set[str]:
    """Stil dosyalarında tanımlanmış tüm sınıf adları."""
    metin = "\n".join(
        p.read_text(encoding="utf-8") for p in sorted(stil_dizini.glob("*.css"))
    )
    return set(_CSS_SINIF.findall(metin))


def kullanilan_siniflar(kaynak: str) -> set[str]:
    """Bir TSX kaynağındaki SABİT sınıf adları.

    Şablon değişkenleri (`${sira === 1 ? " first" : ""}`) DÜZLEŞTİRİLİR:
    içindeki `sira` bir JS tanımlayıcısıdır ve atılır, ama `" first"` gerçek
    bir sınıf adıdır ve korunur. Değişkeni tümüyle atmak, koşullu sınıfları
    denetim dışı bırakırdı — `.first`, `.on`, `.selected` hep bu biçimde
    yazılıyor.
    """
    adlar: set[str] = set()
    for sablon, duz in _CLASSNAME.findall(kaynak):
        govde = _SABLON_DEGISKENI.sub(
            lambda m: " " + " ".join(_DIZGE_SABITI.findall(m.group(1))) + " ",
            sablon or duz,
        )
        for ad in govde.split():
            if _GECERLI_AD.fullmatch(ad):
                adlar.add(ad)
    return adlar


def denetle(web_app: Path = WEB_APP) -> dict[str, list[str]]:
    """Dosya başına tanımsız sınıflar. Boş sözlük = temiz."""
    tanimli = tanimli_siniflar(web_app / "styles")
    bulgular: dict[str, list[str]] = {}
    for p in sorted(web_app.rglob("*.tsx")):
        eksik = sorted(kullanilan_siniflar(p.read_text(encoding="utf-8")) - tanimli)
        if not eksik:
            continue
        # Depo kökü dışındaki yollar (testlerin geçici dizini) olduğu gibi
        # yazılır; `relative_to` orada hata atardı.
        try:
            ad = str(p.relative_to(_KOK))
        except ValueError:
            ad = str(p)
        bulgular[ad] = eksik
    return bulgular


def main(argv: list[str] | None = None) -> int:
    ayristirici = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ayristirici.add_argument("--ayrinti", action="store_true",
                             help="tanımlı sınıf sayısını da yaz")
    args = ayristirici.parse_args(argv)

    if not STIL_DIZINI.exists():
        print(f"HATA: stil dizini yok: {STIL_DIZINI}", file=sys.stderr)
        return 1

    tanimli = tanimli_siniflar()
    bulgular = denetle()

    if args.ayrinti:
        print(f"tanımlı sınıf: {len(tanimli)}")

    if bulgular:
        toplam = sum(len(v) for v in bulgular.values())
        print(f"TANIMSIZ SINIF: {toplam} adet, {len(bulgular)} dosyada.",
              file=sys.stderr)
        for dosya, adlar in bulgular.items():
            print(f"  {dosya}", file=sys.stderr)
            for ad in adlar:
                print(f"    .{ad}", file=sys.stderr)
        return 1

    print("CSS sınıfları TEMİZ — TSX'te kullanılan her sınıfın tanımı var.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
