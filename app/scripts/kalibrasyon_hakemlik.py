"""Kalibrasyon CSV'lerine kılavuz kaynaklı hakemlik kurallarını uygular.

İlgili: data/gold/ANNOTATION_GUIDE.md §3.1, §3.3 (kuralların kaynağı)
        data/gold/review/_kalibrasyon-sonucu.md (neden gerekti — ölçüm)
        scripts/report_iaa.py (κ'yı okuyan taraf)
        scripts/lint_review_csv.py (uygulamadan sonra koşulacak kapı)

## Bu araç anotatör kararını DEĞİŞTİRİR

Bu yüzden üç şey zorunlu ve hiçbiri seçenek değil:

1. **Kurallar önceden ilan edilir** ve kılavuzdan türer — koşu anında
   uydurulmaz. Aşağıdaki `KURALLAR` sözlüğü tek kaynaktır.
2. **Her değişen hücre kayda geçer** (`--degisim-raporu`): dosya, `doc_id`,
   alan, sütun, eski değer, yeni değer, hangi kural. Sayı değil, satır satır.
3. **Yazmadan önce yedek** alınır. CLAUDE.md "silme yok".

## Kurallar

### `bos-ok` — boş karar, boş değer -> `ok`

v1 protokolünde boş hücre zaten `ok` OKUNUYOR (`report_iaa.row_verdict`), bu
kural onu diske YAZAR. Tek etkisi v2'ye taşındığında kararın korunmasıdır;
κ'ya katkısı yoktur.

**Dolu `gold_value` olan satıra DOKUNMAZ.** Boş `verdict` + dolu `gold_value`
her iki protokolde de `fix` demektir: anotatör düzeltmeyi yazıp karar sütununu
atlamıştır. Ona `ok` yazmak, ölçülmüş bir düzeltmeyi onaya çevirirdi — B'de
39 satır böyledir ve ikisi arasındaki fark gerçek (ör. `kampanya_suresi`
model `2026-01-01`, anotatör `01.01.2026 - 31.12.2026`).

### `absent-ok` — model bir şey ÜRETMEDİYSE `absent` -> `ok`

`ANNOTATION_GUIDE.md` §3.1 tablosu: `model_value` boşken doğru karar `ok`'tur
("kontrol ettim, bu alan belgede yok") ve gold'a `absent_fields` girer.
`absent` ise §3.3'e göre **modelin ÜRETTİĞİ bir değeri reddetmek** içindir ve
halüsinasyon (FP) olarak ölçülür.

Model hiçbir şey üretmediğinde `absent` yazmak, olmayan bir halüsinasyonu
işaretlemektir. İki etiket aynı gold değerini ürettiği için sonuç değişmez ama
κ çöker: dört anotatör aynı şeyi söyleyip farklı kelime kullanır.

**`model_value` DOLU olan `absent`'e dokunmaz** — o meşru bir halüsinasyon
iddiasıdır ve projenin ölçtüğü en değerli sinyaldir (dört dosyada 37 satır).

## Kullanım

    .venv/bin/python -m scripts.kalibrasyon_hakemlik --kuru \\
        data/gold/review/round0_kalibrasyon_[ABCD].csv

    .venv/bin/python -m scripts.kalibrasyon_hakemlik \\
        --degisim-raporu data/gold/review/_hakemlik-degisim.md \\
        data/gold/review/round0_kalibrasyon_[ABCD].csv

Çıkış kodu: 0 uygulandı · 1 dosya okunamadı.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import shutil
import sys
from datetime import date
from pathlib import Path
from typing import Optional

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from scripts.to_review_csv import (
    CSV_DELIMITER,
    CSV_ENCODING,
    CSV_LINETERMINATOR,
)
from src.preprocessing.clean import tr_fold_ascii

#: 8 kampanya türü (CLAUDE.md §12). Yazım BİREBİR bu kümedendir.
KAMPANYA_TURLERI = (
    "Finansman", "İhtiyaç Finansmanı", "Konut Finansmanı", "Taşıt Finansmanı",
    "Kart", "Alışveriş Puanı", "Yeni Müşteri", "Yatırım Ürünü",
)

#: `tr_fold_ascii(tür) -> kanonik yazım`. Türkçe küçültme `str.lower()` ile
#: hatalıdır ('İhtiyaç'.lower() -> 'i̇htiyaç'), o yüzden proje katlayıcısı.
_TUR_INDEKS = {tr_fold_ascii(t): t for t in KAMPANYA_TURLERI}

#: ISO-8601 tarih.
_ISO = re.compile(r"^\d{4}-\d{2}-\d{2}$")

#: `31.12.2026`, `31/12/2026`, `31-12-2026`. Yıl DÖRT haneli olmalı.
_TR_TARIH = re.compile(r"\b(\d{1,2})[./-](\d{1,2})[./-](\d{4})\b")

#: Aynı kalıbın gevşek hâli: yıl 2 ya da 4 haneli. Yalnız SAYMAK için.
#: İki haneli yılı çözmeye çalışmıyoruz ('23' -> 1923 mü 2023 mü); varlığını
#: fark edip ÇEKİLİYORUZ.
_TR_TARIH_GEVSEK = re.compile(r"\b\d{1,2}[./-]\d{1,2}[./-]\d{2,4}\b")


def _iso_bitis(metin: str) -> Optional[str]:
    """Metindeki EN SON tarihi ISO-8601 olarak döndürür.

    `kampanya_suresi` kılavuzda "geçerlilik BİTİŞ tarihi" olarak tanımlı
    (`ANNOTATION_GUIDE.md`): "1 – 31 Temmuz 2026" -> `2026-07-31`. Anotatör
    aralığın tamamını yazdıysa ("01.01.2026 - 31.12.2026") bitiş alınır.

    Kural çıkarıcısı da aynı şeyi yapıyor (`extract_kampanya_suresi` ->
    `aralik["bitis"]`), yani gold ile üretim aynı tanımda buluşur.

    Tek tarih varsa o alınır. Hiç tarih yoksa `None` — uydurulmaz.

    ÇÖZÜLEMEYEN TARİH VARSA HİÇ DOKUNULMAZ. Ölçüldü: `'1.07.2023-31.08.23'`
    girdisinde bitişin yılı iki haneli ve katı kalıp onu görmüyor; "son eşleşme
    = bitiş" kuralı o zaman BAŞLANGICI (`2023-07-01`) döndürüyordu — yani tam
    da bu aracın düzeltmeye çalıştığı hatayı üretiyordu. İki haneli yılı
    çözmeye çalışmak da doğru değil ('23' -> 1923 mü 2023 mü); doğru davranış
    çekilmek ve satırı insana bırakmaktır.
    """
    metin = (metin or "").strip()
    if _ISO.fullmatch(metin):
        return metin
    bulunan = _TR_TARIH.findall(metin)
    if not bulunan:
        return None
    if len(_TR_TARIH_GEVSEK.findall(metin)) != len(bulunan):
        return None                     # çözülemeyen tarih var -> dokunma
    gun, ay, yil = bulunan[-1]          # aralıkta SON tarih = bitiş
    try:
        return date(int(yil), int(ay), int(gun)).isoformat()
    except ValueError:
        return None                     # 21.13.2026 gibi geçersiz tarih


#: Kural adı -> (açıklama, koşul). Koşul `(verdict, gold_value, model_value)`
#: üçlüsünü alır ve satırın `ok`'a çevrilip çevrilmeyeceğini söyler.
#: Değerler ÇAĞRIDAN ÖNCE kırpılmış ve `casefold` edilmiş `verdict` ile gelir.
KURALLAR = {
    "bos-ok": (
        "boş karar + boş değer -> ok (v1'de zaten öyle okunuyordu)",
        lambda verdict, gold, model: not verdict and not gold,
    ),
    "absent-ok": (
        "model bir şey üretmediyse absent -> ok (kılavuz §3.1/§3.3)",
        lambda verdict, gold, model: verdict == "absent" and not model,
    ),
    # `verdict` değil `gold_value` üzerinde çalışır; koşulu `uygula()` içinde,
    # alana özgü olduğu için. Burada yalnız adı ve açıklaması duruyor ki
    # `--kural` seçenekleri ve değişim raporu tek yerden okunsun.
    "deger-bicim": (
        "gold_value BİÇİMİ kanonikleştirilir: kampanya_suresi -> ISO bitiş "
        "tarihi, campaign_type -> 8 sınıfın birebir yazımı",
        None,
    ),
    # Kanıta dayalı: karar BELGE METNİNDEN çıkar, hücreye bakarak değil.
    "taksit-vade": (
        "belgede 'taksit' hiç geçmiyorsa taksit_sayisi'na yazılan sayı "
        "vadedir; değer silinir (kılavuz: vade ayı taksit sayısı DEĞİLDİR)",
        None,
    ),
    "paylasim-orani": (
        "belge 'kâr paylaşım oranı' diyorsa X/Y biçimindeki değer paylaşım "
        "oranıdır, kâr payı oranı değil; değer silinir",
        None,
    ),
    "hedef-kitle-etiket": (
        "hedef_kitle serbest metni izinli dört etikete indirgenir; segment "
        "sinyali yoksa ('bireysel müşteriler') silinir, çözülemezse dokunulmaz",
        None,
    ),
    "kosul-ihtar": (
        "kampanya_kosullari'ndan genel yasal ihtar cümlesi ayıklanır "
        "('…hakkını saklı tutar'); geriye koşul kalmazsa değer silinir",
        None,
    ),
}

#: Her kampanyada birebir tekrarlanan genel yasal ihtar. Kıyasta sıfır bilgi
#: taşır: ayırt edici olmayan bir cümle "koşul" diye sayılırsa iki bankanın
#: koşul listesi aynı görünür. Projede bu kalıbı gürültü sayan bir kod yolu
#: zaten var (`scripts/boilerplate_audit.py`).
_IHTAR = re.compile(
    r"hakk[ıi]n[ıi]\s+sakl[ıi]\s+tutar|"
    r"de[ğg]i[şs]iklik\s+yapma\s+(?:ve/?veya\s+)?(?:kampanyay[ıi]\s+)?durdurma|"
    r"bilgilendirme\s+ama[çc]l[ıi]d[ıi]r",
    re.IGNORECASE)


def _kosul_ayikla(ham: str) -> Optional[str]:
    """Koşul listesinden genel yasal ihtar cümlelerini düşürür.

    Dönen: temizlenmiş değer, hiç koşul kalmazsa `""` (silinir), değişiklik
    gerekmiyorsa `None`.

    Liste hem JSON dizisi (`["a", "b"]`) hem `|` ayraçlı olarak geliyor;
    ikisi de desteklenir ve ÇIKTI `|` ayraçlıdır (kılavuzun biçimi).
    """
    ham = (ham or "").strip()
    if not ham:
        return None
    try:
        cozulmus = json.loads(ham)
        parcalar = ([str(x) for x in cozulmus] if isinstance(cozulmus, list)
                    else [str(cozulmus)])
    except (json.JSONDecodeError, ValueError):
        parcalar = [p.strip() for p in ham.split("|")]

    kalan = [p.strip() for p in parcalar if p.strip() and not _IHTAR.search(p)]
    yeni = " | ".join(kalan)
    return None if yeni == ham else yeni

#: Belge metni gerektiren kurallar.
_KANIT_KURALLARI = {"taksit-vade", "paylasim-orani"}

#: `hedef_kitle`'nin İZİN VERİLEN dört etiketi (ANNOTATION_GUIDE §hedef_kitle).
HEDEF_KITLE_ETIKETLERI = ("yeni_musteri", "mevcut_musteri",
                          "maas_musterisi", "belirli_segment")

#: Serbest metinden etikete eşleme. Sıra önemli: 'yeni müşteri' 'müşteri'den
#: önce denenmeli. Anahtarlar `tr_fold_ascii` ile katlanmış aranır.
_HEDEF_KITLE_IPUCU = (
    ("yeni musteri", "yeni_musteri"),
    ("yeni bireysel musteri", "yeni_musteri"),
    ("musteri olan", "yeni_musteri"),
    ("maas", "maas_musterisi"),
    ("emekli", "belirli_segment"),
    ("mevcut musteri", "mevcut_musteri"),
    ("ogrenci", "belirli_segment"),
    ("esnaf", "belirli_segment"),
    ("kamu calisan", "belirli_segment"),
)

#: Segment SİNYALİ TAŞIMAYAN ifadeler. "Bireysel müşteriler" herkestir;
#: kılavuz §4.13/2 ürün/kanal/kitle kısıtının segment olmadığını söylüyor.
#: Bunlar tek başınaysa değer SİLİNİR — uydurma etiket üretilmez.
_HEDEF_KITLE_SINYALSIZ = ("bireysel musteri", "tum musteri", "herkes",
                          "bireysel musteriler")


def _hedef_kitle_etiketle(ham: str) -> Optional[str]:
    """Serbest metni izinli etiketlere indirger.

    Dönen: `"yeni_musteri | belirli_segment"` biçiminde etiket dizgesi,
    sinyal yoksa `""` (değer silinir), zaten geçerliyse `None` (dokunma).

    Uydurma YOK: metinde karşılığı olmayan etiket üretilmez. Hiçbir ipucu
    tutmuyorsa ve metin de "sinyalsiz" listesinde değilse `None` döner —
    yani karar insana bırakılır.
    """
    ham = (ham or "").strip()
    if not ham:
        return None
    katlanmis = tr_fold_ascii(ham)

    # Zaten yalnız izinli etiketlerden mi oluşuyor?
    parcalar = [p.strip().strip('[]"\'' + " ")
                for p in re.split(r"[|,]", ham.strip("[]"))]
    parcalar = [p for p in parcalar if p]
    if parcalar and all(p in HEDEF_KITLE_ETIKETLERI for p in parcalar):
        return None

    bulunan = []
    for ipucu, etiket in _HEDEF_KITLE_IPUCU:
        if ipucu in katlanmis and etiket not in bulunan:
            bulunan.append(etiket)
    if bulunan:
        return " | ".join(bulunan)
    if any(s in katlanmis for s in _HEDEF_KITLE_SINYALSIZ):
        return ""              # segment sinyali yok -> değer silinir
    return None                # çözemedim -> insana bırak

#: Belge metinlerinin bulunduğu dizin.
BELGE_DIZINI = _ROOT / "data" / "gold" / "review" / "belgeler"

_TAKSIT = re.compile(r"taksit", re.IGNORECASE)
_PAYLASIM = re.compile(r"payla[şs][ıi]m\s+oran", re.IGNORECASE)

#: `85/15`, `%40-60`, `%40'a %60` — iki payı olan PAYLAŞIM biçimi.
#: Tek sayı (`2.99`) ya da min/max sözlüğü bir ORANDIR, buraya girmez.
_PAY_ORANI = re.compile(
    r"^[\"'“”]?\s*%?\s*\d{1,3}\s*(?:/|-|'a\s*%?|\s+/\s+)\s*%?\s*\d{1,3}\s*[\"'“”]?$"
)


def _belge_metinleri(satirlar: list[dict], dizin: Path) -> dict[str, str]:
    """`doc_id -> metin`. Metni bulunamayan belge sözlüğe GİRMEZ."""
    out: dict[str, str] = {}
    for doc in sorted({(s.get("doc_id") or "").strip() for s in satirlar}):
        p = dizin / f"{doc}.txt"
        if p.exists():
            out[doc] = p.read_text(encoding="utf-8")
    return out

VARSAYILAN_KURALLAR = tuple(KURALLAR)


def _oku(yol: Path) -> tuple[list[str], list[dict]]:
    with yol.open(encoding=CSV_ENCODING, newline="") as fh:
        r = csv.DictReader(fh, delimiter=CSV_DELIMITER)
        baslik = [(h or "").lstrip("﻿") for h in (r.fieldnames or [])]
        satirlar = [{(k or "").lstrip("﻿"): (v or "") for k, v in s.items()}
                    for s in r]
    return baslik, satirlar


def _yedekle(yol: Path) -> Path:
    hedef = yol.with_suffix(yol.suffix + ".yedek-hakemlik")
    n = 2
    while hedef.exists():
        hedef = yol.with_suffix(f"{yol.suffix}.yedek-hakemlik{n}")
        n += 1
    shutil.copy2(yol, hedef)
    return hedef


def uygula(yol: Path, kurallar: tuple[str, ...] = VARSAYILAN_KURALLAR,
           kuru: bool = False, belge_dizini: Path = BELGE_DIZINI) -> dict:
    """Kuralları bir dosyaya uygular; değişen her hücreyi kaydeder."""
    bilinmeyen = [k for k in kurallar if k not in KURALLAR]
    if bilinmeyen:
        raise ValueError(f"bilinmeyen kural: {', '.join(bilinmeyen)}")

    baslik, satirlar = _oku(yol)
    degisimler: list[dict] = []
    korunan = {"dolu_gold_value": 0, "mesru_absent": 0}
    # Belge metni yalnız KANITA DAYALI kurallar için okunur; ötekiler
    # metne bakmadan çalıştığı için maliyet ödenmez.
    metinler = (_belge_metinleri(satirlar, belge_dizini)
                if _KANIT_KURALLARI & set(kurallar) else {})

    for s in satirlar:
        # --- KANITA DAYALI kurallar: karar BELGEDEN çıkar -------------------
        if metinler:
            alan = (s.get("field") or "").strip()
            ham = (s.get("gold_value") or "").strip()
            metin = metinler.get((s.get("doc_id") or "").strip())
            gerekce = None
            if metin is not None and ham:
                if alan == "taksit_sayisi" and "taksit-vade" in kurallar \
                        and not _TAKSIT.search(metin):
                    gerekce = "belgede 'taksit' geçmiyor; yazılan sayı vadedir"
                elif alan == "kar_payi_orani" and "paylasim-orani" in kurallar \
                        and _PAY_ORANI.match(ham) and _PAYLASIM.search(metin):
                    gerekce = ("belge 'kâr paylaşım oranı' diyor; X/Y bir "
                               "paylaşım oranıdır, kâr payı oranı değil")
            if gerekce:
                degisimler.append({
                    "dosya": yol.name, "doc_id": s.get("doc_id", ""),
                    "field": alan, "sutun": "gold_value",
                    "eski": ham, "yeni": "(boş)",
                    "kural": gerekce,
                })
                s["gold_value"] = ""
                # Model bir değer ÜRETTİYSE bu artık meşru bir `absent`tir
                # (üretilen değer metinde bu alana ait değil). Üretmediyse
                # `ok` — "kontrol ettim, bu alan belgede yok".
                s["verdict"] = "absent" if (s.get("model_value") or "").strip() \
                    else "ok"

        # --- DEĞER normalizasyonu (yalnız BİÇİM; anlam değişmez) -----------
        # `verdict` kurallarından ÖNCE çalışır ve onlardan bağımsızdır:
        # anotatörün ne dediğini değil, NASIL yazdığını düzeltir.
        if {"deger-bicim", "hedef-kitle-etiket", "kosul-ihtar"} & set(kurallar):
            alan = (s.get("field") or "").strip()
            ham = (s.get("gold_value") or "").strip()
            bicim = "deger-bicim" in kurallar
            yeni = None
            if ham and alan == "kampanya_suresi" and bicim:
                yeni = _iso_bitis(ham)
            elif ham and alan == "campaign_type" and bicim:
                yeni = _TUR_INDEKS.get(tr_fold_ascii(ham))
            elif ham and alan == "hedef_kitle" \
                    and "hedef-kitle-etiket" in kurallar:
                yeni = _hedef_kitle_etiketle(ham)
            elif ham and alan == "kampanya_kosullari" \
                    and "kosul-ihtar" in kurallar:
                yeni = _kosul_ayikla(ham)
            # `yeni == ""` DE bir karardır (değer silinir); `None` "dokunma"
            # demektir. `if yeni:` yazmak silmeyi sessizce atlardı.
            if yeni is not None and yeni != ham:
                degisimler.append({
                    "dosya": yol.name, "doc_id": s.get("doc_id", ""),
                    "field": alan, "sutun": "gold_value",
                    "eski": ham, "yeni": yeni or "(boş)",
                    "kural": {"hedef_kitle": "hedef-kitle-etiket",
                              "kampanya_kosullari": "kosul-ihtar"}.get(
                                  alan, "deger-bicim"),
                })
                s["gold_value"] = yeni
                if not yeni and not (s.get("model_value") or "").strip():
                    s["verdict"] = "ok"   # değer yok, model de üretmedi

        verdict = (s.get("verdict") or "").strip().casefold()
        gold = (s.get("gold_value") or "").strip()
        model = (s.get("model_value") or "").strip()

        # Korunanları önce say: raporda "dokunmadım"ın da sayısı olmalı.
        if not verdict and gold:
            korunan["dolu_gold_value"] += 1
        if verdict == "absent" and model:
            korunan["mesru_absent"] += 1

        for ad in kurallar:
            _, kosul = KURALLAR[ad]
            if kosul is None:            # `deger-bicim` yukarıda işlendi
                continue
            if not kosul(verdict, gold, model):
                continue
            eski = (s.get("verdict") or "").strip()
            if eski.casefold() == "ok":
                continue
            degisimler.append({
                "dosya": yol.name,
                "doc_id": s.get("doc_id", ""),
                "field": s.get("field", ""),
                "sutun": "verdict",
                "eski": eski,
                "yeni": "ok",
                "kural": ad,
            })
            s["verdict"] = "ok"
            break

    yedek = None
    if not kuru and degisimler:
        yedek = str(_yedekle(yol))
        with yol.open("w", encoding=CSV_ENCODING, newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=baslik, delimiter=CSV_DELIMITER,
                               lineterminator=CSV_LINETERMINATOR)
            w.writeheader()
            w.writerows(satirlar)

    return {
        "dosya": str(yol),
        "satir": len(satirlar),
        "degisimler": degisimler,
        "korunan": korunan,
        "yedek": yedek,
    }


def rapor_yaz(raporlar: list[dict], kurallar: tuple[str, ...]) -> str:
    """Değişim kaydını markdown olarak üretir (satır satır, sayı değil)."""
    satirlar = [
        "# Kalibrasyon Hakemlik — Değişim Kaydı",
        "",
        "> `scripts/kalibrasyon_hakemlik.py` üretti. Her değişen hücre burada.",
        "> Geri almak için `.yedek-hakemlik` kopyaları duruyor (silme yok).",
        "",
        "## Uygulanan kurallar",
        "",
    ]
    for ad in kurallar:
        satirlar.append(f"- **`{ad}`** — {KURALLAR[ad][0]}")
    satirlar += ["", "## Özet", "",
                 "| Dosya | satır | değişen | korunan: dolu gold_value | "
                 "korunan: meşru absent |", "|---|---:|---:|---:|---:|"]
    for r in raporlar:
        satirlar.append(
            f"| `{Path(r['dosya']).name}` | {r['satir']} | "
            f"{len(r['degisimler'])} | {r['korunan']['dolu_gold_value']} | "
            f"{r['korunan']['mesru_absent']} |")

    satirlar += ["", "## Değişen hücreler", ""]
    for ad in kurallar:
        ilgili = [d for r in raporlar for d in r["degisimler"] if d["kural"] == ad]
        satirlar += [f"### `{ad}` ({len(ilgili)} hücre)", ""]
        if not ilgili:
            satirlar += ["_yok_", ""]
            continue
        satirlar += ["| Dosya | Belge | Alan | eski -> yeni |", "|---|---|---|---|"]
        for d in ilgili:
            eski = d["eski"] or "(boş)"
            satirlar.append(
                f"| `{d['dosya']}` | `{d['doc_id']}` | `{d['field']}` | "
                f"`{eski}` -> `{d['yeni']}` |")
        satirlar.append("")
    return "\n".join(satirlar) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("csv", nargs="+", help="inceleme CSV'leri")
    ap.add_argument("--kural", action="append", choices=list(KURALLAR),
                    help="uygulanacak kural (yinelenebilir; öntanım: hepsi)")
    ap.add_argument("--kuru", action="store_true", help="yazmadan dene")
    ap.add_argument("--degisim-raporu", default=None,
                    help="değişim kaydının yazılacağı markdown dosyası")
    a = ap.parse_args(argv)

    kurallar = tuple(a.kural) if a.kural else VARSAYILAN_KURALLAR
    raporlar = []
    for ham in a.csv:
        yol = Path(ham)
        if not yol.exists():
            print(f"HATA: dosya yok: {yol}", file=sys.stderr)
            return 1
        raporlar.append(uygula(yol, kurallar, kuru=a.kuru))

    for r in raporlar:
        print(f"  {Path(r['dosya']).name:<34}"
              f"değişen {len(r['degisimler']):>4} · "
              f"korunan(dolu gold) {r['korunan']['dolu_gold_value']:>3} · "
              f"korunan(meşru absent) {r['korunan']['mesru_absent']:>3}")
    toplam = sum(len(r["degisimler"]) for r in raporlar)
    print(f"\ntoplam değişen hücre: {toplam}")

    if a.degisim_raporu and not a.kuru:
        Path(a.degisim_raporu).write_text(rapor_yaz(raporlar, kurallar),
                                          encoding="utf-8")
        print(f"değişim kaydı: {a.degisim_raporu}")
    if a.kuru:
        print("(kuru koşu — dosyalar YAZILMADI)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
