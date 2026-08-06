"""Katılım jargonu denetimi — TESPİT EDER, DEĞİŞTİRMEZ.

İlgili: ../src/domain/terminology.py (öneriler sözlükten türetilir),
        ../src/chatbot/safety.py (KAPI 1 — çalışma zamanı bekçisi),
        ../docs/terminoloji-sozlugu.md, CLAUDE.md §12, §19

Kullanım:
    python -m scripts.jargon_lint                 # varsayılan kapsam
    python -m scripts.jargon_lint --explain       # muafiyet gerekçelerini de bas
    python -m scripts.jargon_lint --paths web src/chatbot
    python -m scripts.jargon_lint --json rapor.json

Çıkış kodu 1 = ihlal var (CI build'i kırar).

## Neden bu betik DEĞİŞTİRMİYOR

Mentör (Cavide Hanım, 2026-08-06): "Birebir değiştirmek anlamda bozukluk
yaratıyor… Türkçeleri aynı anlamı replace ile taşımıyor." Bu betik bir dönüşüm
aracı değil; yanlış terimi bulur, sözlükten türettiği doğru karşılığı ÖNERİR ve
düzeltmeyi insana bırakır.

## Kapsam neden dar — ÖLÇÜLDÜ

Kör tarama (faiz|kredi|mevduat kökleri, tüm repo) **494 bulgu** verdi. Neredeyse
hepsi meşru:

    docs     238   terim ayrımını ANLATAN belgeler ("kâr payı faiz değildir")
    tests    115   gerçek banka metnini alıntılayan fikstürler
    src       89   eşleştirici sabitler + scraper URL desenleri (/kredi/...)
    scripts   47   aynı
    eval       4   'kredibilite' — kök eşleşmesinin yanlış pozitifi
    web        1   <- GERÇEK İHLAL: kullanıcıya dönük arayüz etiketi

494 bulgu basan bir lint kimsenin koşmadığı bir linttir. Bu yüzden kapsam
**kullanıcıya/modele dönük metin**: arayüz etiketleri, chatbot cevap şablonları,
prompt sabitleri. Mentörün "istisna listesi sadece ham banka metni için geçerli"
beklentisi ölçümle uyuşmuyor — eşleştiricilerimiz yasak terimi İÇERMEK ZORUNDA,
çünkü onları banka metninde arıyorlar.
"""

from __future__ import annotations

import argparse
import ast
import json
import os
import re
import sys
from dataclasses import asdict, dataclass
from typing import Iterable, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.domain.terminology import TermEntry, load_terminology
from src.preprocessing.clean import tr_fold_ascii

#: Kullanıcıya/modele dönük metnin bulunduğu yerler.
VARSAYILAN_KAPSAM = ("web", "src/chatbot", "src/extraction/llm",
                     "src/extraction/silver", "src/api")

#: Konvansiyonel bankacılık kökleri. `\w*` Türkçe ekleri yakalar.
YASAK_KOKLER = ("faiz", "kredi", "mevduat")

#: Kökün yasak SAYILMADIĞI biçimler.
#: - faizsiz*  : katılım bankacılığının tanımı, kendi doğru terimimiz
#: - kredi kartı: katılım bankalarının da kullandığı GERÇEK ürün adı
#:   (`safety.py::_SOFT_EXCEPTION_RE` ile aynı gerekçe)
#: - kredibilite: kök eşleşmesinin yanlış pozitifi, farklı kavram
MUAF_BICIMLER = re.compile(
    r"faizsiz\w*|kredi\s*kart\w*|kredibilite\w*|kredi\s*notu\w*",
    re.IGNORECASE)

#: Eşleştirici sabitler ve onları KURAN fonksiyonlar — banka metninde ya da
#: kullanıcı sorusunda yasak terimi ARADIKLARI için onu içermek ZORUNDALAR.
#: (Kullanıcı "kredi" diye sorar; router onu yakalayamazsa soru cevapsız kalır.)
ESLESTIRICI_AD_RE = re.compile(
    r"_RE$|_RE_|_PATTERN|_TRIGGER|_HINT|_STEM|_REPLACEMENT|_LEXICON|_KEYWORD|"
    r"SYNONYM|VARYANT|_KEYS|_SLUG|_EXCEPTION|SCOPE|FORBIDDEN|"
    r"^_?build_|_build_|mentions_|detect_|soft_term",
    re.IGNORECASE)

#: Satır içi kaçış. Gerekçesiyle yazılmalı: `# jargon-lint: ok — <gerekçe>`
PRAGMA_RE = re.compile(r"#\s*jargon-lint:\s*ok", re.IGNORECASE)

#: Karşıtlık bağlamı — "kâr payı faiz DEĞİLDİR" bizim DOĞRU cümlemizdir.
#: `terminology._KARSITLIK_RE` ile aynı ders; burada dize üzerinde çalışır.
KARSITLIK_RE = re.compile(
    r"\bdegil|\bfarkli|\bfarki\b|\bfark\b|\byerine\b|\baksine\b|"
    r"\bkullanilmamali|\bkaristirilmamali|\byanlistir|\bdemek degil",
    re.IGNORECASE)

#: URL / dosya yolu görünümlü dizeler — scraper desenleri.
YOL_RE = re.compile(r"https?://|^/|/\w+/|\.com|\.tr\b|\.aspx|\*\*?/")

_ATLANAN_DIZIN = {"node_modules", ".next", "__pycache__", ".venv", "dist",
                  ".git", ".ruff_cache", "build", "coverage"}
_PY = (".py",)
_WEB = (".tsx", ".ts", ".jsx", ".js")

KOK_RE = re.compile("|".join(rf"\b{k}\w*" for k in YASAK_KOKLER), re.IGNORECASE)


@dataclass
class Bulgu:
    dosya: str
    satir: int
    terim: str
    baglam: str
    oneri: str
    muafiyet: Optional[str] = None       # dolu ise ihlal DEĞİL

    @property
    def ihlal(self) -> bool:
        return self.muafiyet is None


# --------------------------------------------------------------------------- #
# Öneriler — sözlükten türetilir, kodda sabit liste yok
# --------------------------------------------------------------------------- #

#: Ürün dilindeki birincil karşılık — CLAUDE.md §12 ve mentörün aksiyon
#: planındaki yasak/karşılık tablosu.
#:
#: Mentörün maili bu tablonun bir DÖNÜŞÜM KURALI olarak kullanılmasını
#: reddediyor ("replace anlamı taşımıyor") — ama bir ÖNERİ KAYNAĞI olarak
#: geçerliliğini koruyor. Bu ayrım planın çözdüğü çelişkinin ta kendisi.
#:
#: Neden sözlük tek başına yetmiyor — ÖLÇÜLDÜ: `degildir` alanında birebir
#: "kredi" geçen ALTI girdi var (murabaha, muşaraka, mudaraba, karz-ı hasen,
#: kâr/zarar ortaklığı, azalan muşaraka). Aralarında sözlükten türetilebilecek
#: bir üstünlük sırası yok; alfabetik seçim "Kâr/zarar ortaklığı yatırımı"
#: öneriyordu, oysa ürün dilindeki cevap "finansman".
BIRINCIL_KARSILIK: dict[str, str] = {
    "faiz": "Kâr payı",
    "kredi": "Finansman",
    "mevduat": "Katılma hesabı",
}


def oneri_tablosu(entries: Optional[Iterable[TermEntry]] = None,
                  ) -> dict[str, list[str]]:
    """yasak kök -> doğru karşılık(lar), en isabetli önce.

    İki kaynak birleşir: `BIRINCIL_KARSILIK` (ürün dili, otoriter) ve sözlüğün
    `degildir` alanından TÜRETİLEN adaylar. İkincisi sözlük büyüdükçe
    kendiliğinden zenginleşir ve fıkhî akit adını da gösterir — kullanıcı
    "kredi" yerine yalnız "finansman" değil, "murabaha" da diyebilmeli.
    """
    girdiler = tuple(entries) if entries is not None else load_terminology()
    #: kök -> [(siralama_anahtari, kanonik)]
    ham: dict[str, list[tuple[tuple, str]]] = {k: [] for k in YASAK_KOKLER}
    for e in girdiler:
        for yanlis in e.degildir:
            katli = tr_fold_ascii(yanlis).strip()
            for kok in YASAK_KOKLER:
                if not re.search(rf"\b{kok}", katli):
                    continue
                # Sıralama: TAM eşleşme önce. Ölçüldü — dosya sırasıyla
                # gidildiğinde 'faiz' için en doğru karşılık ("Kâr payı",
                # `degildir` içinde birebir "faiz" olarak yazılı) dördüncü
                # sıraya düşüyor ve "İcare muntehiye bi't-temlîk"
                # ("faizli leasing" bileşiğinden) öne geçiyordu.
                anahtar = (0 if katli == kok else 1, len(katli), e.id)
                ham[kok].append((anahtar, e.kanonik))
    tablo: dict[str, list[str]] = {}
    for kok, adaylar in ham.items():
        birincil = BIRINCIL_KARSILIK.get(kok)
        gorulen: list[str] = [birincil] if birincil else []
        for _, kanonik in sorted(adaylar):
            if kanonik not in gorulen:
                gorulen.append(kanonik)
        tablo[kok] = gorulen
    return tablo


def _oneri(terim: str, tablo: dict[str, list[str]]) -> str:
    katli = tr_fold_ascii(terim)
    for kok in YASAK_KOKLER:
        if katli.startswith(kok):
            adaylar = tablo.get(kok) or []
            return " / ".join(adaylar[:3]) if adaylar else "(sözlükte karşılık yok)"
    return ""


# --------------------------------------------------------------------------- #
# Dize toplama
# --------------------------------------------------------------------------- #

def _python_dizeleri(kaynak: str) -> list[tuple[int, str, str]]:
    """(satir, dize, sahip) — docstring'ler HARİÇ.

    `sahip` şu üçünden biridir ve muafiyet kararında kullanılır:
      - atandığı değişken adı           (`_FIELD_KEYWORDS`)
      - içinde bulunduğu fonksiyon adı  (`_build_scope_lexicon`)
      - "<karsilastirma>"               (`if stem == "kredi"` — kod mantığı)

    Docstring dışlanır çünkü belgelendirme terim ayrımını anlatmak zorundadır;
    onu yasaklamak kendi açıklamalarımızı sansürlerdi.
    """
    try:
        agac = ast.parse(kaynak)
    except SyntaxError:
        return []

    docstring_konum: set[int] = set()
    for dugum in ast.walk(agac):
        if isinstance(dugum, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef,
                              ast.ClassDef)):
            govde = getattr(dugum, "body", None)
            if (govde and isinstance(govde[0], ast.Expr)
                    and isinstance(govde[0].value, ast.Constant)
                    and isinstance(govde[0].value.value, str)):
                docstring_konum.add(id(govde[0].value))

    #: dize düğümü -> atandığı ad (eşleştirici muafiyeti için)
    sahip: dict[int, str] = {}
    for dugum in ast.walk(agac):
        adlar: list[str] = []
        if isinstance(dugum, ast.Assign):
            adlar = [t.id for t in dugum.targets if isinstance(t, ast.Name)]
        elif isinstance(dugum, ast.AnnAssign) and isinstance(dugum.target, ast.Name):
            adlar = [dugum.target.id]
        if not adlar:
            continue
        for alt in ast.walk(dugum):
            if isinstance(alt, ast.Constant) and isinstance(alt.value, str):
                sahip[id(alt)] = adlar[0]

    # Karşılaştırma operandları kod mantığıdır, kullanıcıya dönük metin değil:
    #     if stem == "kredi": ...
    for dugum in ast.walk(agac):
        if isinstance(dugum, ast.Compare):
            for alt in ast.walk(dugum):
                if (isinstance(alt, ast.Constant)
                        and isinstance(alt.value, str)
                        and id(alt) not in sahip):
                    sahip[id(alt)] = "<karsilastirma>"

    # İçinde bulunduğu fonksiyon: eşleştiriciyi KURAN fonksiyonun gövdesindeki
    # dizeler de eşleştiricidir (`_build_scope_lexicon` içindeki "faiz").
    for dugum in ast.walk(agac):
        if not isinstance(dugum, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for alt in ast.walk(dugum):
            if (isinstance(alt, ast.Constant) and isinstance(alt.value, str)
                    and id(alt) not in sahip):
                sahip[id(alt)] = dugum.name

    cikti: list[tuple[int, str, str]] = []
    for dugum in ast.walk(agac):
        if not (isinstance(dugum, ast.Constant) and isinstance(dugum.value, str)):
            continue
        if id(dugum) in docstring_konum:
            continue
        cikti.append((dugum.lineno, dugum.value, sahip.get(id(dugum), "")))
    return cikti


_WEB_DIZE_RE = re.compile(r"""(["'`])((?:\\.|(?!\1).)*)\1""", re.DOTALL)


def _web_dizeleri(kaynak: str) -> list[tuple[int, str, str]]:
    """TSX/TS dize sabitleri + JSX metin düğümleri (kaba ama yeterli)."""
    cikti: list[tuple[int, str, str]] = []
    for m in _WEB_DIZE_RE.finditer(kaynak):
        satir = kaynak.count("\n", 0, m.start()) + 1
        cikti.append((satir, m.group(2), ""))
    # JSX gövde metni: >...< arası, etiket ve süslü parantez içermeyen
    for m in re.finditer(r">([^<>{}\n]{3,})<", kaynak):
        satir = kaynak.count("\n", 0, m.start()) + 1
        cikti.append((satir, m.group(1).strip(), ""))
    return cikti


# --------------------------------------------------------------------------- #
# Denetim
# --------------------------------------------------------------------------- #

def _muafiyet(terim: str, dize: str, sahip: str, satir_metni: str,
              konum: int = -1) -> Optional[str]:
    # İzinli biçim PENCEREDE aranır, terimin kendisinde değil: 'kredi kartı'
    # iki sözcüktür ve kök eşleşmesi yalnız 'Kredi'yi yakalar. İlk koşuda tam
    # olarak bu yüzden yanlış alarm verdi.
    if konum >= 0:
        pencere = dize[max(0, konum - 20):konum + len(terim) + 25]
    else:
        pencere = terim
    if MUAF_BICIMLER.search(pencere):
        return "izinli biçim"
    if sahip == "<karsilastirma>":
        return "karşılaştırma operandı (kod mantığı)"
    if sahip and ESLESTIRICI_AD_RE.search(sahip):
        return f"eşleştirici ({sahip})"
    if YOL_RE.search(dize):
        return "URL/yol deseni"
    if KARSITLIK_RE.search(tr_fold_ascii(dize)):
        return "karşıtlık bağlamı (ayrımı anlatıyor)"
    if PRAGMA_RE.search(satir_metni):
        return "satır içi pragma"
    return None


def dosyayi_denetle(yol: str, tablo: dict[str, list[str]]) -> list[Bulgu]:
    try:
        kaynak = open(yol, encoding="utf-8").read()
    except (OSError, UnicodeDecodeError):
        return []
    satirlar = kaynak.splitlines()

    if yol.endswith(_PY):
        dizeler = _python_dizeleri(kaynak)
    elif yol.endswith(_WEB):
        dizeler = _web_dizeleri(kaynak)
    else:
        return []

    bulgular: list[Bulgu] = []
    for satir, dize, sahip in dizeler:
        for m in KOK_RE.finditer(dize):
            terim = m.group(0)
            satir_metni = satirlar[satir - 1] if 0 < satir <= len(satirlar) else ""
            bulgular.append(Bulgu(
                dosya=yol, satir=satir, terim=terim,
                baglam=dize.strip()[:120],
                oneri=_oneri(terim, tablo),
                muafiyet=_muafiyet(terim, dize, sahip, satir_metni,
                                   m.start())))
    return bulgular


def kapsami_tara(yollar: Iterable[str], tablo: dict[str, list[str]],
                 ) -> list[Bulgu]:
    bulgular: list[Bulgu] = []
    for kok in yollar:
        if os.path.isfile(kok):
            bulgular.extend(dosyayi_denetle(kok, tablo))
            continue
        for dirpath, dirnames, files in os.walk(kok):
            dirnames[:] = [d for d in dirnames if d not in _ATLANAN_DIZIN]
            for f in sorted(files):
                if f.endswith(_PY) or f.endswith(_WEB):
                    bulgular.extend(
                        dosyayi_denetle(os.path.join(dirpath, f), tablo))
    return bulgular


def main(argv: Optional[list[str]] = None) -> int:
    ap = argparse.ArgumentParser(
        description="Katılım jargonu denetimi — tespit eder, değiştirmez")
    ap.add_argument("--paths", nargs="*", default=list(VARSAYILAN_KAPSAM))
    ap.add_argument("--explain", action="store_true",
                    help="muaf tutulan bulguları da gerekçesiyle bas")
    ap.add_argument("--json", help="raporu JSON olarak yaz")
    args = ap.parse_args(argv)

    tablo = oneri_tablosu()
    if not any(tablo.values()):
        print("UYARI: terim sözlüğü yüklenemedi; öneriler boş kalacak.")

    mevcut = [p for p in args.paths if os.path.exists(p)]
    eksik = [p for p in args.paths if not os.path.exists(p)]
    for p in eksik:
        print(f"UYARI: kapsam yolu yok, atlandı: {p}")

    bulgular = kapsami_tara(mevcut, tablo)
    ihlaller = [b for b in bulgular if b.ihlal]
    muaflar = [b for b in bulgular if not b.ihlal]

    print(f"Kapsam: {', '.join(mevcut) or '(boş)'}")
    print(f"Tarandı: {len(bulgular)} eşleşme | ihlal {len(ihlaller)} | "
          f"muaf {len(muaflar)}")

    if ihlaller:
        print("\nİHLALLER — kullanıcıya/modele dönük metinde konvansiyonel terim:")
        for b in ihlaller:
            print(f"  {b.dosya}:{b.satir}  '{b.terim}'  -> {b.oneri}")
            print(f"      {b.baglam}")

    if args.explain and muaflar:
        print("\nMUAF TUTULANLAR (gerekçeleriyle):")
        for b in muaflar:
            print(f"  {b.dosya}:{b.satir}  '{b.terim}'  [{b.muafiyet}]")

    if args.json:
        os.makedirs(os.path.dirname(os.path.abspath(args.json)) or ".",
                    exist_ok=True)
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump({"ihlal": [asdict(b) for b in ihlaller],
                       "muaf": [asdict(b) for b in muaflar]},
                      fh, ensure_ascii=False, indent=2)
        print(f"\nrapor -> {args.json}")

    if not ihlaller:
        print("\nTemiz.")
    return 1 if ihlaller else 0


if __name__ == "__main__":
    sys.exit(main())
