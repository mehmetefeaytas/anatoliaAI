"""Lint hatalarını anotatör + kalıp bazında gruplar ve ÖNERİ üretir.

İlgili: scripts/lint_review_csv.py (hataların kaynağı — DEĞİŞTİRİLMEZ)
        data/gold/review/_bicim-karti.md §3 (mekanik kuralların dayanağı)
        data/gold/ANNOTATION_GUIDE.md

## Bu betik CSV'ye YAZMAZ

Gold, modelin ölçüldüğü referanstır; modelin (ya da bir betiğin) `verdict` /
`gold_value` hücrelerini doldurması ölçümü geçersiz kılar. Bu projede bedeli
ölçülmüştür: gold modele çapalıyken mikro-F1 0,677, kör protokolde 0,536 —
0,141'lik fark protokol artefaktıydı (ANNOTATION_GUIDE.md §3.1).

Bu yüzden çıktı ayrı bir dosyadır (`_oneriler.csv`): anotatör tek bakışta
onaylar ya da reddeder. Karar insanındır.

## Mekanik kuralların dayanağı

Her kural `_bicim-karti.md` §3'teki ara kararlardan birine bağlıdır; kart dışı
kural ÜRETİLMEZ. Üretilen her öneri, yayımlanmadan önce `parse_gold_value`
süzgecinden geçirilir — linter'ın reddedeceği bir öneri anotatöre gösterilmez.

Kullanım:
    python3 -m scripts.onarim_recetesi                     # rapor + öneriler
    python3 -m scripts.onarim_recetesi --sadece-ozet       # yalnız sayım
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Callable, Optional

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from scripts.gold_schema import parse_gold_value
from scripts.lint_review_csv import SEVERITY_ERROR, Finding, lint, read_rows

DEFAULT_FILES = [f"data/gold/review/round0_kalibrasyon_{x}.csv" for x in "ABCD"]
DEFAULT_ONERI = "data/gold/review/_oneriler.csv"
ONERI_SUTUNLARI = ["dosya", "doc_id", "field", "mevcut", "onerilen",
                   "gerekce", "kanit"]

_ANOTATOR_RE = re.compile(r"round0_kalibrasyon_([ABCD])\.csv")
_TEMIZLE = "__BOSALT__"  # "bu hücreyi boşalt" işareti
# Aynı anotatörün aynı belgedeki `vade_ay` hücresi; vade sızıntısı tanığı.
_VADE_KARDES = "_vade_ay_gold"

AYLAR = {
    "ocak": 1, "şubat": 2, "subat": 2, "mart": 3, "nisan": 4, "mayıs": 5,
    "mayis": 5, "haziran": 6, "temmuz": 7, "ağustos": 8, "agustos": 8,
    "eylül": 9, "eylul": 9, "ekim": 10, "kasım": 11, "kasim": 11,
    "aralık": 12, "aralik": 12,
}

# _bicim-karti.md §3 vaka 8: 8 sınıfa sığmayan tür nereye gider.
TUR_ESLEME = {
    "güneş katılma hesabı": "Yatırım Ürünü",
    "güneş yatırım hesabı": "Yatırım Ürünü",
    "altın katılma hesabı": "Yatırım Ürünü",
    "yatırım hesabı": "Yatırım Ürünü",
    "leasing": "Finansman",
}

ARALIK_ALANLARI = {"vade_ay", "taksit_sayisi"}
PARA_ALANLARI = {"finansman_tutari", "odul_miktari"}
BUGUN_YIL = date.today().year


# --------------------------------------------------------------------------- #
# Kalıp sınıflandırması
# --------------------------------------------------------------------------- #
def kalip(mesaj: str) -> str:
    """Linter mesajını akılda kalıcı bir kalıp adına indirger."""
    if "verdict=absent ama gold_value dolu" in mesaj:
        return "absent-ama-deger-dolu"
    if "tek deger alir ama" in mesaj:
        return "tek-alana-coklu-deger"
    if "kampanya türü" in mesaj and "tanınmıyor" in mesaj:
        return "taksonomi-disi-tur"
    if "hedef_kitle" in mesaj:
        return "hedef_kitle-serbest-metin"
    if "verdict=fix ama gold_value bos" in mesaj:
        return "fix-ama-deger-bos"
    if "tamsayıya çevrilemedi" in mesaj:
        return "tamsayi-cevrilemedi"
    if "masraf durumuna çevrilemedi" in mesaj:
        return "masraf-kanonik-degil"
    if "ORAN mı ADET mi" in mesaj:
        return "puan-oran-adet-belirsiz"
    if "taninmiyor. Izin verilenler" in mesaj:
        return "gecersiz-verdict"
    if "biçiminde olmalı" in mesaj or "olmalı;" in mesaj:
        return "sema-yanlis-anahtar"
    if "kanonik degil" in mesaj:
        return "model-degeri-kanonik-degil"
    return "siniflanmadi"


def anotator(path: str) -> str:
    m = _ANOTATOR_RE.search(path)
    return m.group(1) if m else "?"


# --------------------------------------------------------------------------- #
# TR sayı / tarih okuyucuları
# --------------------------------------------------------------------------- #
def tr_sayilar(metin: str) -> list[float]:
    """Metindeki TR biçimli sayıları çıkarır (`1.250.000,50` -> 1250000.5)."""
    out: list[float] = []
    for ham in re.findall(r"\d[\d.,]*", metin):
        ham = ham.strip(".,")
        if not ham:
            continue
        # Binlik ayracı `.`, ondalık `,` (CLAUDE.md §10).
        if "," in ham:
            sayi = ham.replace(".", "").replace(",", ".")
        elif re.fullmatch(r"\d{1,3}(\.\d{3})+", ham):
            sayi = ham.replace(".", "")
        else:
            sayi = ham
        try:
            out.append(float(sayi))
        except ValueError:
            continue
    return out


def tr_tarihler(metin: str) -> list[str]:
    """Metindeki tarihleri ISO-8601 listesine çevirir (kronolojik değil, sırayla).

    İki biçim tanınır: `31 Aralık 2026` ve `31.12.2026`. Ay adı olmayan
    `1-31 Temmuz 2026` gibi aralıklarda gün listesi ay+yıl ile eşleştirilir.
    """
    out: list[str] = []
    for gun, ay_adi, yil in re.findall(
            r"(\d{1,2})\s*[-–]?\s*(?:\d{1,2}\s+)?([A-Za-zÇĞİÖŞÜçğıöşü]+)\s+(\d{4})",
            metin):
        ay = AYLAR.get(ay_adi.casefold())
        if ay:
            out.append(f"{int(yil):04d}-{ay:02d}-{int(gun):02d}")
    # `1-31 Temmuz 2026`: iki gün, tek ay/yıl -> ikisini de üret.
    for g1, g2, ay_adi, yil in re.findall(
            r"(\d{1,2})\s*[-–]\s*(\d{1,2})\s+([A-Za-zÇĞİÖŞÜçğıöşü]+)\s+(\d{4})",
            metin):
        ay = AYLAR.get(ay_adi.casefold())
        if ay:
            out += [f"{int(yil):04d}-{ay:02d}-{int(g1):02d}",
                    f"{int(yil):04d}-{ay:02d}-{int(g2):02d}"]
    for gun, ay, yil in re.findall(r"(\d{1,2})[./](\d{1,2})[./](\d{2,4})", metin):
        y = int(yil)
        y += 2000 if y < 100 else 0
        out.append(f"{y:04d}-{int(ay):02d}-{int(gun):02d}")
    return sorted(set(out))


# --------------------------------------------------------------------------- #
# Mekanik kurallar — her biri `_bicim-karti.md` §3'teki bir vakaya bağlı
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Oneri:
    dosya: str
    doc_id: str
    field: str
    mevcut: str
    onerilen: str
    gerekce: str
    kanit: str


def _kural_aralik(field: str, ham: str, satir: dict) -> Optional[tuple[str, str]]:
    """Kart §3 vaka 2: `vade_ay`/`taksit_sayisi` aralığı -> EN BÜYÜK değer.

    İki VADE SIZINTISI koruması var. İkisi de aynı hatayı engelliyor: aralığı
    doğru daraltıp **yanlış alana** yazmak. `taksit_sayisi` bir SAYIMdır, `ay`
    bir SÜRE birimidir; `1- 36 Ay` taksit hücresine yazıldığında düzeltilmesi
    gereken şey aralık değil, alanın kendisidir.

      1) Birim tanığı: `taksit_sayisi` hücresinde `ay` geçiyorsa bu bir vadedir.
      2) Kopya tanığı: aynı anotatörün aynı belgedeki `vade_ay` hücresi aynı
         sayı kümesini taşıyorsa, aralık iki alana kopyalanmıştır.

    İkisi de tetiklenmezse kart §3-2 uygulanır.
    """
    if field not in ARALIK_ALANLARI or "%" in ham:
        return None
    sayilar = [s for s in tr_sayilar(ham) if s > 0]
    if len(sayilar) < 2:
        return None

    if field == "taksit_sayisi":
        if re.search(r"\bay\b", ham, re.IGNORECASE):
            return None
        kardes = (satir.get(_VADE_KARDES) or "").strip()
        if kardes and set(tr_sayilar(kardes)) == set(sayilar):
            return None

    return (str(int(max(sayilar))),
            f"kart §3-2: aralık yazılmış, en büyük değer alınır (note'a `aralik={ham.strip()}`)")


def _kural_tutar(field: str, ham: str, satir: dict) -> Optional[tuple[str, str]]:
    """Kart §3 vaka 4: tutar aralığı -> ÜST SINIR.

    `%` içeren hücre ORAN'dır, tutar değil — mekanik öneri ÜRETİLMEZ. Bu
    korumasız hâli `%20-%70` için `{"value": 70, "currency": "TRY"}` öneriyordu;
    linter'ı geçen ama gold'a yanlış değer sokan bir öneri, hatanın kendisinden
    tehlikelidir (anotatör onaylayıp geçer).
    """
    if field not in PARA_ALANLARI or "%" in ham:
        return None
    sayilar = [s for s in tr_sayilar(ham) if s > 0]
    if len(sayilar) < 2:
        return None
    return (json.dumps({"value": max(sayilar), "currency": "TRY"}),
            f"kart §3-4: tutar aralığı, üst sınır alınır (note'a `alt={min(sayilar):g}`)")


def _kural_tarih(field: str, ham: str, satir: dict) -> Optional[tuple[str, str]]:
    """Kart §3 vaka 1: başlangıç+bitiş -> BİTİŞ tarihi.

    Makul olmayan uzak yıl (bugün + 20'den öte) mekanik ÖNERİLMEZ: kalibrasyonda
    `31 Aralık 2072` yazılmış ama aynı anotatörün başka bir hücresindeki not
    `2027` diyor. İki hücre çelişiyorsa doğrusunu belge bilir, betik değil.
    """
    if field != "kampanya_suresi":
        return None
    tarihler = tr_tarihler(ham)
    if not tarihler:
        return None
    bitis = max(tarihler)
    if int(bitis[:4]) > BUGUN_YIL + 20:
        return None
    gerekce = "kart §3-1: bitiş tarihi alınır"
    if len(tarihler) > 1:
        gerekce += f" (note'a `baslangic={min(tarihler)}`)"
    return (bitis, gerekce)


def _kural_tur(field: str, ham: str, satir: dict) -> Optional[tuple[str, str]]:
    """Kart §3 vaka 8: 8 sınıfa sığmayan tür -> kartın yönlendirdiği sınıf."""
    if field != "campaign_type":
        return None
    hedef = TUR_ESLEME.get(ham.strip().casefold())
    if not hedef:
        return None
    return (hedef, f"kart §3-8: '{ham.strip()}' 8 sınıfta yok (note'a gerçek ürün adı)")


def _kural_masraf_metin(field: str, ham: str, satir: dict) -> Optional[tuple[str, str]]:
    """`Ücretli` / `masraflı` -> tutar bilinmiyorsa `amount: null`."""
    if field != "masraf_durumu":
        return None
    if ham.strip().casefold() not in {"ücretli", "ucretli", "masraflı", "masrafli"}:
        return None
    return (json.dumps({"has_fee": True, "amount": None}),
            "kanonik biçim: masraf VAR ama tutar yazılmamış -> amount null")


def _kural_json_onar(field: str, ham: str, satir: dict) -> Optional[tuple[str, str]]:
    """Bozuk JSON'u onarır — yalnız anahtar/parantez hatası, değer DEĞİŞMEZ."""
    if field != "masraf_durumu":
        return None
    sayilar = re.findall(r'"amount"\s*:\s*([\d.]+)', ham)
    if not sayilar or '"has_fee"' not in ham:
        return None
    has_fee = "true" in ham.casefold()
    return (json.dumps({"has_fee": has_fee, "amount": float(sayilar[0])}),
            "bozuk JSON onarıldı (parantez hatası); sayı değişmedi")


def _kural_oran_duz(field: str, ham: str, satir: dict) -> Optional[tuple[str, str]]:
    """`{"rate": x}` -> düz sayı (kart §2: oran alanı düz sayı alır)."""
    if field not in {"kar_payi_orani", "indirim_orani"}:
        return None
    m = re.fullmatch(r'\s*\{\s*"rate"\s*:\s*([\d.]+)\s*\}\s*', ham)
    if not m:
        return None
    return (m.group(1), "kart §2: oran alanı düz sayı alır, `rate` anahtarı yok")


def _kural_tahsis_oransal(field: str, ham: str, satir: dict) -> Optional[tuple[str, str]]:
    """Kart §3 vaka 6: oransal tahsis ücreti -> `unclear`, şema açığı."""
    if field != "tahsis_ucreti":
        return None
    m = re.fullmatch(r'\s*\{\s*"rate"\s*:\s*([\d.]+)\s*\}\s*', ham)
    if not m:
        return None
    return (_TEMIZLE,
            f"kart §3-6: oransal ücret (%{m.group(1)}) para şemasına sığmaz -> "
            f"verdict=unclear + note'a `oransal {m.group(1)}`")


def _kural_puan(field: str, ham: str, satir: dict) -> Optional[tuple[str, str]]:
    """`1.500 TL ParafPara` -> puan ADEDİ (oran değil; `%` yok, `TL` var)."""
    if field != "alisveris_puani":
        return None
    if "%" in ham:
        return None
    sayilar = tr_sayilar(ham)
    if len(sayilar) != 1:
        return None
    return (json.dumps({"kind": "points", "value": sayilar[0]}),
            "kart §2: `%` yok + `TL` var -> ADET (points), oran değil")


def _kural_absent_temizle(field: str, ham: str, satir: dict) -> Optional[tuple[str, str]]:
    """`absent` + dolu `gold_value` -> değeri BOŞALT, kararı koru.

    Kart §3 tuzak 2: `build_gold` `absent` görünce değeri zaten sessizce atar.
    Yazılan metin alanın DEĞERİ değil, belgenin konusudur.
    """
    if (satir.get("verdict") or "").strip().casefold() != "absent":
        return None
    return (_TEMIZLE,
            "kart §3 tuzak-2: `absent` değer taşımaz; yazılan metin belgenin "
            "konusu, alanın değeri değil (note'a taşınır)")


KURALLAR: list[Callable[[str, str, dict], Optional[tuple[str, str]]]] = [
    _kural_absent_temizle,   # önce: `absent` satırında biçim kuralı işletilmez
    _kural_tahsis_oransal,
    _kural_json_onar,
    _kural_masraf_metin,
    _kural_oran_duz,
    _kural_puan,
    _kural_tur,
    _kural_tarih,
    _kural_tutar,
    _kural_aralik,
]


def oneri_uret(f: Finding, satir: dict) -> Optional[Oneri]:
    """Tek hata için mekanik öneri; kural yoksa ya da öneri linter'ı geçmiyorsa None."""
    ham = (satir.get("gold_value") or "").strip()
    if not ham:
        return None
    for kural in KURALLAR:
        sonuc = kural(f.field, ham, satir)
        if sonuc is None:
            continue
        onerilen, gerekce = sonuc
        # Öneri kendi kapısından geçmeli: linter'ın reddedeceğini gösterme.
        if onerilen != _TEMIZLE:
            try:
                parse_gold_value(f.field, onerilen)
            except Exception:
                return None
        return Oneri(
            dosya=Path(f.file).name,
            doc_id=f.doc_id,
            field=f.field,
            mevcut=_guvenli(ham),
            onerilen="(hücreyi boşalt)" if onerilen == _TEMIZLE else _guvenli(onerilen),
            gerekce=_guvenli(gerekce),
            kanit=_guvenli((satir.get("note") or "").strip()[:160] or "—"),
        )
    return None


def _guvenli(metin: str) -> str:
    """`;` ayracını bozacak karakterleri temizler (dosya `;` ile ayrılıyor)."""
    return metin.replace(";", ",").replace("\n", " ").replace("\r", " ").strip()


# --------------------------------------------------------------------------- #
# Rapor
# --------------------------------------------------------------------------- #
def topla(paths: list[str]) -> tuple[list[Finding], dict[tuple[str, int], dict]]:
    """Hataları ve satırları toplar; her satıra `vade_ay` kardeşini iliştirir.

    Kardeş hücre vade sızıntısı korumasının tanığıdır (`_kural_aralik`): aynı
    anotatörün aynı belgedeki `vade_ay` değeri, `taksit_sayisi` hücresine
    kopyalanmış mı diye bakılır.
    """
    findings = [f for f in lint(paths) if f.severity == SEVERITY_ERROR]
    satirlar: dict[tuple[str, int], dict] = {}
    for p in paths:
        rows, _ = read_rows(p)
        vade = {(r.get("doc_id") or "").strip(): (r.get("gold_value") or "")
                for r in rows if (r.get("field") or "").strip() == "vade_ay"}
        for r in rows:
            r[_VADE_KARDES] = vade.get((r.get("doc_id") or "").strip(), "")
            satirlar[(p, r["_line"])] = r
    return findings, satirlar


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Lint hatalarını kalıba indirger ve ÖNERİ üretir (CSV'ye YAZMAZ).")
    parser.add_argument("csv", nargs="*", default=DEFAULT_FILES)
    parser.add_argument("--oneri-out", default=DEFAULT_ONERI)
    parser.add_argument("--sadece-ozet", action="store_true")
    args = parser.parse_args(argv)

    paths = [str(_ROOT / p) if not Path(p).is_absolute() else p
             for p in (args.csv or DEFAULT_FILES)]
    findings, satirlar = topla(paths)

    tablo: dict[tuple[str, str], list[Finding]] = defaultdict(list)
    for f in findings:
        tablo[(anotator(f.file), kalip(f.message))].append(f)

    ayri_satir = {(anotator(f.file), f.line) for f in findings}
    print(f"HATA {len(findings)} · {len(ayri_satir)} ayrı satır · "
          f"{len(set(k[1] for k in tablo))} kalıp")

    for a in "ABCD":
        alt = {k[1]: v for k, v in tablo.items() if k[0] == a}
        toplam = sum(len(v) for v in alt.values())
        print(f"\n{a}: {toplam} hata")
        for k, v in sorted(alt.items(), key=lambda x: -len(x[1])):
            alanlar = ", ".join(f"{n}×{f}" for f, n in
                                Counter(x.field for x in v).most_common())
            print(f"   {len(v):3d}  {k:28s} {alanlar}")

    # Öneriler
    oneriler: list[Oneri] = []
    gorulen: set[tuple[str, str, str]] = set()
    for f in findings:
        satir = satirlar.get((f.file, f.line))
        if satir is None:
            continue
        anahtar = (anotator(f.file), f.doc_id, f.field)
        if anahtar in gorulen:
            continue
        o = oneri_uret(f, satir)
        if o is not None:
            gorulen.add(anahtar)
            oneriler.append(o)

    print(f"\nmekanik öneri: {len(oneriler)} / {len(ayri_satir)} hatalı satır")
    kapsanmayan = len(ayri_satir) - len(oneriler)
    print(f"insan kararı gereken: {kapsanmayan}")

    if not args.sadece_ozet:
        out = Path(args.oneri_out)
        if not out.is_absolute():
            out = _ROOT / out
        out.parent.mkdir(parents=True, exist_ok=True)
        with out.open("w", encoding="utf-8", newline="") as fh:
            w = csv.writer(fh, delimiter=";")
            w.writerow(ONERI_SUTUNLARI)
            for o in sorted(oneriler, key=lambda x: (x.dosya, x.doc_id, x.field)):
                w.writerow([o.dosya, o.doc_id, o.field, o.mevcut,
                            o.onerilen, o.gerekce, o.kanit])
        print(f"öneriler: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
