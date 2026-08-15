"""Anotatörün doldurduğu dosyadan KARARLARI inceleme CSV'sine taşır.

Kaynak `.xlsx` **ya da** `.csv` olabilir; ikisi de aynı yolu izler.

İlgili: scripts/protokol_yukselt.py (aynı taşıma felsefesi, farklı yön)
        scripts/to_review_csv.py (CSV üreteci — sütun sırası ve biçim oradan)
        scripts/lint_review_csv.py (taşımadan sonra koşulacak kapı)
        data/gold/review/_atama.md (κ için satır kümesi sabittir)

## Neden gerekli

Anotatörler CSV'yi Excel/Numbers ile açıp `.xlsx` olarak geri gönderiyor.
Dosyayı doğrudan CSV'ye çevirmek (Excel'in kendi "CSV olarak kaydet"i dahil)
üç sessiz bozulma üretir ve üçü de ölçüldü:

  * `model_conf` `0.70` -> `0.7` (Excel sayı olarak yorumlayıp sondaki sıfırı
    atar). Üreteçten gelen değer değişmiş olur.
  * Ayırıcı `;` yerine `,` olur, kodlama BOM'suz UTF-8 ya da CP1254'e döner.
  * Satır sırası sıralama/filtre sonrası kalıcı değişebilir.

Üçüncüsü en tehlikelisidir: Fleiss κ dört dosyanın **birebir aynı satır
kümesini** taşımasını şart koşar (`_atama.md`). Satır sırası kayarsa κ
hizalanmaz ve bu hata sessizdir.

Anotatör Excel'in kendi "CSV olarak kaydet"ini kullandığında dosya `.csv`
uzantısıyla gelir ama **aynı bozulmaları taşır** — round1_A'da ölçüldü: BOM
düştü, `gold_value` ile `verdict` arasına adsız bir sütun girdi (12 -> 13
sütun). Böyle bir dosyayı hedefin üzerine kopyalamak üreteç sütunlarını da
değiştirir. Bu yüzden `.csv` kaynak da `.xlsx` ile aynı kapıdan geçer: yalnız
karar sütunları okunur, hedefin üreteç sütunlarına dokunulmaz.

## Çözüm: yalnız ANOTATÖR sütunları taşınır

Hedef CSV'deki üreteç sütunlarına (`doc_id`, `bank`, `field`, `model_value`,
`model_conf`, `confidence_source`, `disagreement`, `snippet`) **hiç
dokunulmaz**; `.xlsx`'ten yalnız `gold_value`, `verdict`, `note` okunur.
Eşleme satır sırasına değil `(doc_id, field)` anahtarına dayanır, yani
anotatör Excel'de sıralama yapmış olsa bile karar doğru satıra düşer.

`protokol_yukselt.py` v1 -> v2 taşımasında aynı ilkeyi uyguluyor; bu araç onun
`.xlsx` -> CSV yönündeki karşılığıdır.

## Bağımlılık yok

`.xlsx` bir ZIP + XML paketidir; `zipfile` ve `xml.etree` standart
kütüphanededir. `openpyxl`/`pandas` KURULMAZ — offline kısıtı ve lisans
denetimi (CLAUDE.md §1, §20) yeni bağımlılığı gereksiz yere pahalı kılar,
okunan yapı ise ~40 satırlık bir alt kümedir.

## Silme yok

Hedef CSV üzerine yazmadan önce `<dosya>.yedek-xlsx-oncesi` alınır (varsa sıra
numarası eklenir). CLAUDE.md "silme yok" kuralı burada da geçerlidir.

## Kullanım

    .venv/bin/python -m scripts.xlsx_to_review_csv \\
        --kaynak data/gold/review/round0_kalibrasyon_B.xlsx \\
        --csv    data/gold/review/round0_kalibrasyon_B.csv

    # anotatör CSV olarak kaydettiyse — aynı komut, farklı uzantı
    .venv/bin/python -m scripts.xlsx_to_review_csv \\
        --kaynak data/gold/review/round1_A_Etiketli.csv \\
        --csv    data/gold/review/round1_A.csv

    # yazmadan ne olacağını gör
    .venv/bin/python -m scripts.xlsx_to_review_csv --kuru --kaynak ... --csv ...

`--xlsx` eski adıyla çalışmayı sürdürür (`--kaynak` ile eşanlamlı).

Çıkış kodu: 0 taşındı · 1 satır kümesi uyuşmuyor / dosya okunamadı.
"""

from __future__ import annotations

import argparse
import csv
import re
import shutil
import sys
import zipfile
from datetime import date, timedelta
from pathlib import Path
from typing import Optional
from xml.etree import ElementTree as ET

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from scripts.to_review_csv import (
    CSV_DELIMITER,
    CSV_ENCODING,
    CSV_LINETERMINATOR,
)

#: SpreadsheetML ad alanı.
_NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"

#: Excel tarih başlangıcı. 1900 artık-yıl hatası yüzünden 1899-12-30'dur.
_EXCEL_EPOCH = date(1899, 12, 30)

#: Yerleşik tarih/saat biçim kimlikleri (ECMA-376 §18.8.30). Bunların dışında
#: kalan özel biçimler `formatCode` içinde yıl (`yy`) arayarak tanınır.
_YERLESIK_TARIH_BICIMLERI = frozenset(
    {14, 15, 16, 17, 18, 19, 20, 21, 22, *range(27, 37), 45, 46, 47, *range(50, 59)}
)

#: Anotatörün doldurduğu sütunlar — YALNIZ bunlar `.xlsx`'ten alınır.
KARAR_SUTUNLARI = ("gold_value", "verdict", "note")

#: Satırı kimliklendiren anahtar. Satır SIRASI değil bu kullanılır.
ANAHTAR = ("doc_id", "field")

_HUCRE_ADRESI = re.compile(r"^([A-Z]+)(\d+)$")


def _sutun_indeksi(adres: str) -> int:
    """`C7` -> 2 (0 tabanlı sütun indeksi)."""
    m = _HUCRE_ADRESI.match(adres)
    if not m:
        raise ValueError(f"çözülemeyen hücre adresi: {adres!r}")
    harfler = m.group(1)
    n = 0
    for ch in harfler:
        n = n * 26 + (ord(ch) - ord("A") + 1)
    return n - 1


def _tarih_stilleri(z: zipfile.ZipFile) -> set[int]:
    """Hangi stil indeksleri TARİH biçimlidir — `xl/styles.xml`'den okunur.

    Excel bir tarihi sayı olarak saklar; "bu sayı bir tarihtir" bilgisi yalnız
    hücrenin biçiminde durur. Biçime bakmadan okunursa `2026-12-31` sessizce
    `46387` olur ve gold'a öyle girer (round1_B'de 17, round1_main_D'de 33
    hücrede oldu).
    """
    if "xl/styles.xml" not in z.namelist():
        return set()
    kok = ET.fromstring(z.read("xl/styles.xml"))

    ozel_tarih: set[int] = set()
    for nf in kok.iter(f"{_NS}numFmt"):
        kod = (nf.get("formatCode") or "").lower()
        kimlik = nf.get("numFmtId")
        # Köşeli parantezli bölümler renk/koşuldur (`[Red]`), biçim değil.
        govde = re.sub(r"\[[^\]]*\]", "", kod)
        if kimlik and "y" in govde:
            ozel_tarih.add(int(kimlik))

    stiller: set[int] = set()
    xfs = kok.find(f"{_NS}cellXfs")
    if xfs is None:
        return stiller
    for i, xf in enumerate(xfs.findall(f"{_NS}xf")):
        kimlik = xf.get("numFmtId")
        if kimlik is None:
            continue
        n = int(kimlik)
        if n in _YERLESIK_TARIH_BICIMLERI or n in ozel_tarih:
            stiller.add(i)
    return stiller


def _seri_tarihten_iso(ham: str) -> Optional[str]:
    """Excel seri numarasını `YYYY-MM-DD`ye çevirir; çeviremezse `None`.

    Saat bileşeni (ondalık kısım) ATILIR: inceleme CSV'lerinde tarih alanları
    gün çözünürlüğündedir (`ANNOTATION_GUIDE` §4 — ISO-8601 tarih).
    """
    try:
        gun = float(ham)
    except (TypeError, ValueError):
        return None
    if not 1 <= gun <= 2_958_465:  # 1900-01-01 .. 9999-12-31
        return None
    return (_EXCEL_EPOCH + timedelta(days=int(gun))).isoformat()


def xlsx_satirlari(yol: Path) -> list[list[str]]:
    """`.xlsx`'in ilk sayfasını satır listesi olarak döndürür.

    Boş hücreler `""` olur ve satır sonundaki boşluklar KIRPILMAZ: `verdict`
    sütunu boşsa bu bir bilgidir ("karar verilmedi"), kaybedilmemeli.
    """
    with zipfile.ZipFile(yol) as z:
        adlar = z.namelist()

        paylasilan: list[str] = []
        if "xl/sharedStrings.xml" in adlar:
            kok = ET.fromstring(z.read("xl/sharedStrings.xml"))
            for si in kok.findall(f"{_NS}si"):
                paylasilan.append("".join(t.text or "" for t in si.iter(f"{_NS}t")))

        tarih_stilleri = _tarih_stilleri(z)

        sayfalar = sorted(
            n for n in adlar if re.match(r"xl/worksheets/sheet\d+\.xml$", n)
        )
        if not sayfalar:
            raise ValueError(f"{yol}: çalışma sayfası bulunamadı")
        kok = ET.fromstring(z.read(sayfalar[0]))

    satirlar: list[list[str]] = []
    for row in kok.iter(f"{_NS}row"):
        hucreler: dict[int, str] = {}
        for c in row.findall(f"{_NS}c"):
            adres = c.get("r")
            idx = _sutun_indeksi(adres) if adres else len(hucreler)
            tur = c.get("t")
            if tur == "inlineStr":
                deger = "".join(t.text or "" for t in c.iter(f"{_NS}t"))
            elif tur == "s":
                v = c.find(f"{_NS}v")
                deger = paylasilan[int(v.text)] if v is not None and v.text else ""
            else:
                v = c.find(f"{_NS}v")
                deger = v.text if v is not None and v.text is not None else ""
                # Hücre TARİH biçimliyse saklanan sayı bir seri numarasıdır.
                # Ham okunursa `2026-12-31` yerine `46387` taşınır ve bu hata
                # sessizdir — ayrıştırıcı sayıyı sorunsuz kabul eder.
                stil = c.get("s")
                if deger and stil is not None and int(stil) in tarih_stilleri:
                    iso = _seri_tarihten_iso(deger)
                    if iso is not None:
                        deger = iso
            hucreler[idx] = deger
        if not hucreler:
            satirlar.append([])
            continue
        genislik = max(hucreler) + 1
        satirlar.append([hucreler.get(i, "") for i in range(genislik)])
    return satirlar


def xlsx_kararlari(yol: Path) -> dict[tuple[str, str], dict[str, str]]:
    """`(doc_id, field)` -> anotatör kararları.

    Başlık satırı `.xlsx`'in kendisinden okunur; anotatör sütun EKLEMİŞ olsa
    bile bilinen adlar doğru indekse eşlenir.
    """
    satirlar = xlsx_satirlari(yol)
    if not satirlar:
        raise ValueError(f"{yol}: dosya boş")

    baslik = [h.strip().lstrip("﻿") for h in satirlar[0]]
    yer = {ad: i for i, ad in enumerate(baslik)}
    eksik = [a for a in (*ANAHTAR, *KARAR_SUTUNLARI) if a not in yer]
    if eksik:
        raise ValueError(f"{yol}: başlıkta eksik sütun: {', '.join(eksik)}")

    def al(satir: list[str], ad: str) -> str:
        i = yer[ad]
        return (satir[i] if i < len(satir) else "").strip()

    kararlar: dict[tuple[str, str], dict[str, str]] = {}
    for satir in satirlar[1:]:
        if not satir:
            continue
        anahtar = (al(satir, "doc_id"), al(satir, "field"))
        if not anahtar[0]:
            continue
        kararlar[anahtar] = {s: al(satir, s) for s in KARAR_SUTUNLARI}
    return kararlar


def csv_kararlari(yol: Path) -> dict[tuple[str, str], dict[str, str]]:
    """`(doc_id, field)` -> anotatör kararları — kaynak bir `.csv` olduğunda.

    `xlsx_kararlari` ile aynı sözleşme. Sütunlar ADLARIYLA bulunur, sırayla
    değil: Excel'den geçmiş bir CSV'de adsız bir sütun belirmiş olabilir
    (round1_A'da oldu) ve indekse güvenmek kararları bir sütun kaydırır.
    """
    baslik, satirlar = _csv_oku(yol)
    eksik = [a for a in (*ANAHTAR, *KARAR_SUTUNLARI) if a not in baslik]
    if eksik:
        raise ValueError(f"{yol}: başlıkta eksik sütun: {', '.join(eksik)}")

    kararlar: dict[tuple[str, str], dict[str, str]] = {}
    for satir in satirlar:
        anahtar = (satir.get("doc_id", "").strip(), satir.get("field", "").strip())
        if not anahtar[0]:
            continue
        kararlar[anahtar] = {s: (satir.get(s) or "").strip()
                             for s in KARAR_SUTUNLARI}
    return kararlar


def kaynak_kararlari(yol: Path) -> dict[tuple[str, str], dict[str, str]]:
    """Uzantıya göre `.xlsx` ya da `.csv` okuyucusuna yönlendirir."""
    if yol.suffix.lower() == ".xlsx":
        return xlsx_kararlari(yol)
    if yol.suffix.lower() == ".csv":
        return csv_kararlari(yol)
    raise ValueError(f"{yol}: desteklenmeyen uzantı (.xlsx ya da .csv bekleniyor)")


def _csv_oku(yol: Path) -> tuple[list[str], list[dict]]:
    with yol.open(encoding=CSV_ENCODING, newline="") as fh:
        okuyucu = csv.DictReader(fh, delimiter=CSV_DELIMITER)
        baslik = [(h or "").lstrip("﻿") for h in (okuyucu.fieldnames or [])]
        satirlar = [
            {(k or "").lstrip("﻿"): (v or "") for k, v in r.items()}
            for r in okuyucu
        ]
    return baslik, satirlar


def _yedekle(yol: Path) -> Path:
    """`<dosya>.yedek-xlsx-oncesi`; varsa sıra numarası eklenir (silme yok)."""
    hedef = yol.with_suffix(yol.suffix + ".yedek-xlsx-oncesi")
    n = 2
    while hedef.exists():
        hedef = yol.with_suffix(f"{yol.suffix}.yedek-xlsx-oncesi{n}")
        n += 1
    shutil.copy2(yol, hedef)
    return hedef


def tasi(xlsx: Path, hedef_csv: Path, kuru: bool = False,
         kismi: bool = False) -> dict:
    """Kaynak (`.xlsx` ya da `.csv`) kararlarını CSV'ye taşır; rapor döndürür.

    Satır kümesi ayrışıyorsa (anotatör satır silmiş/eklemiş) taşıma YAPILMAZ:
    eksik satırlar κ birimlerini hizasız bırakır ve bu hata sessizdir.

    `kismi=True` bu kapıyı **bilerek** açar: yalnız kesişen satırlar taşınır,
    dışarıda kalanlar raporda sayılır. Yalnız κ'ya girmeyecek bir dosya için
    kullanılır — round1_main_C'de anotatör kendi dağıtımı yerine derlediği bir
    kümeyi doldurdu ve 201 kararının 33'ü hedefte karşılık buldu. Hizasız bir
    dosyayı κ'ya sokmak sayıyı anlamsız kılar; emeği çöpe atmak da gereksiz.
    """
    kararlar = kaynak_kararlari(xlsx)
    baslik, satirlar = _csv_oku(hedef_csv)

    csv_anahtarlari = {(r.get("doc_id", ""), r.get("field", "")) for r in satirlar}
    xlsx_anahtarlari = set(kararlar)

    rapor = {
        "xlsx": str(xlsx),
        "csv": str(hedef_csv),
        "csv_satir": len(satirlar),
        "xlsx_satir": len(kararlar),
        "csvde_olmayan": sorted(xlsx_anahtarlari - csv_anahtarlari),
        "xlsxte_olmayan": sorted(csv_anahtarlari - xlsx_anahtarlari),
        "yazilan": 0,
        "verdict_dolu": 0,
        "gold_value_dolu": 0,
        "note_dolu": 0,
        "ustune_yazilan": [],
        "yedek": None,
        "kismi": kismi,
        "disarida_kalan_dolu": 0,
    }
    if (rapor["csvde_olmayan"] or rapor["xlsxte_olmayan"]) and not kismi:
        return rapor

    if kismi:
        # Hedefte karşılığı olmayan DOLU kararlar — taşınamayanın ölçüsü.
        rapor["disarida_kalan_dolu"] = sum(
            1 for a in (xlsx_anahtarlari - csv_anahtarlari)
            if any(kararlar[a].get(s) for s in KARAR_SUTUNLARI))

    for satir in satirlar:
        anahtar = (satir.get("doc_id", ""), satir.get("field", ""))
        karar = kararlar.get(anahtar)
        if karar is None:
            continue
        degisti = False
        for sutun in KARAR_SUTUNLARI:
            yeni = karar.get(sutun, "")
            eski = (satir.get(sutun) or "").strip()
            if not yeni:
                # BOŞ HÜCRE TAŞINMAZ. Anotatör kararı silmiş olabilir ama daha
                # olası olan, hiç dokunmamış olmasıdır; hedefteki dolu bir
                # kararı boşla ezmek bilgi kaybıdır.
                continue
            if eski and eski != yeni:
                rapor["ustune_yazilan"].append(
                    {"doc_id": anahtar[0], "field": anahtar[1],
                     "sutun": sutun, "eski": eski, "yeni": yeni})
            satir[sutun] = yeni
            degisti = True
        if degisti:
            rapor["yazilan"] += 1

    for satir in satirlar:
        for sutun in KARAR_SUTUNLARI:
            if (satir.get(sutun) or "").strip():
                rapor[f"{sutun}_dolu"] += 1

    if not kuru:
        rapor["yedek"] = str(_yedekle(hedef_csv))
        with hedef_csv.open("w", encoding=CSV_ENCODING, newline="") as fh:
            yazici = csv.DictWriter(fh, fieldnames=baslik,
                                    delimiter=CSV_DELIMITER,
                                    lineterminator=CSV_LINETERMINATOR)
            yazici.writeheader()
            yazici.writerows(satirlar)
    return rapor


def _yazdir(rapor: dict) -> None:
    print(f"  {Path(rapor['xlsx']).name} -> {Path(rapor['csv']).name}")
    if (rapor["csvde_olmayan"] or rapor["xlsxte_olmayan"]) and rapor.get("kismi"):
        print("  KISMİ TAŞIMA — satır kümesi uyuşmuyor, yalnız kesişim taşındı.")
        print(f"    kaynakta var, hedefte yok : {len(rapor['csvde_olmayan'])} satır")
        print(f"      bunlardan DOLU olan     : {rapor['disarida_kalan_dolu']} karar "
              f"(TAŞINMADI)")
        print(f"    hedefte var, kaynakta yok : {len(rapor['xlsxte_olmayan'])} satır")
    elif rapor["csvde_olmayan"] or rapor["xlsxte_olmayan"]:
        print("  SATIR KÜMESİ UYUŞMUYOR — taşıma YAPILMADI.")
        for etiket, anahtar in (("xlsx'te var, CSV'de yok", "csvde_olmayan"),
                                ("CSV'de var, xlsx'te yok", "xlsxte_olmayan")):
            liste = rapor[anahtar]
            if liste:
                print(f"    {etiket}: {len(liste)} satır")
                for d, f in liste[:5]:
                    print(f"      - {d} · {f}")
                if len(liste) > 5:
                    print(f"      … {len(liste) - 5} satır daha")
        return
    print(f"    satır            : {rapor['csv_satir']}")
    print(f"    karar yazılan    : {rapor['yazilan']}")
    print(f"    verdict dolu     : {rapor['verdict_dolu']}")
    print(f"    gold_value dolu  : {rapor['gold_value_dolu']}")
    print(f"    note dolu        : {rapor['note_dolu']}")
    if rapor["ustune_yazilan"]:
        print(f"    ÜZERİNE YAZILAN  : {len(rapor['ustune_yazilan'])} hücre")
        for u in rapor["ustune_yazilan"][:5]:
            print(f"      - {u['doc_id']} · {u['field']} · {u['sutun']}: "
                  f"{u['eski']!r} -> {u['yeni']!r}")
    if rapor["yedek"]:
        print(f"    yedek            : {Path(rapor['yedek']).name}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--kaynak", "--xlsx", dest="kaynak", required=True,
                    help="anotatörün gönderdiği .xlsx ya da .csv")
    ap.add_argument("--csv", required=True, help="hedef inceleme CSV'si")
    ap.add_argument("--kuru", action="store_true", help="yazmadan dene")
    ap.add_argument("--kismi", action="store_true",
                    help="satır kümesi uyuşmasa da kesişimi taşı — κ'ya "
                         "GİRMEYECEK dosyalar için")
    args = ap.parse_args(argv)

    xlsx, hedef = Path(args.kaynak), Path(args.csv)
    if xlsx.resolve() == hedef.resolve():
        print("HATA: kaynak ve hedef aynı dosya", file=sys.stderr)
        return 1
    for p in (xlsx, hedef):
        if not p.exists():
            print(f"HATA: dosya yok: {p}", file=sys.stderr)
            return 1

    rapor = tasi(xlsx, hedef, kuru=args.kuru, kismi=args.kismi)
    _yazdir(rapor)
    if (rapor["csvde_olmayan"] or rapor["xlsxte_olmayan"]) and not args.kismi:
        return 1
    if args.kuru:
        print("  (kuru koşu — dosya YAZILMADI)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
