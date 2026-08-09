"""Anotatör başına ROUND1 HAZIRLIK KARTI üretir — kendi hata kalıpların, ölçülmüş.

İlgili: ../data/gold/ANNOTATION_GUIDE.md §3.3, §4 (K1-K4, kelime testi)
        ../data/gold/review/_kalibrasyon-sonucu.md (turun teşhisi)
        ../data/gold/review/_ANA-TUR-TALIMATI.md (anotatöre verilen tek sayfa)
        lint_review_csv.py (biçim bulguları), kalibrasyon_hakemlik.py (kurallar)

Kullanım:
    python -m scripts.calisma_listesi
    python -m scripts.calisma_listesi --ozet          # dosya yazmaz, sayı basar

## Bu betik ANOTASYON YAPMAZ

Tek bir `verdict` ya da `gold_value` hücresine dokunmaz; CSV'leri yalnız OKUR.
Gold, modelin ölçüldüğü referanstır — onu üreten taraf insan olmak zorundadır,
yoksa ölçüm modelin kendi çıktısına çapalanır (kılavuz §3.1 "Neden değişti").

## Neden "geri dön ve doldur" listesi DEĞİL

`round0_kalibrasyon_*` bir kalibrasyon turuydu, gold değil. İşi ekibi
hizalamaktı ve onu yaptı: dört kural çıktı (kılavuz §4 K1-K4). Kalibrasyon
YENİDEN ETİKETLENMİYOR.

Asıl κ `round1_A` + `round1_B`'den çıkacak. Gerçek gold verisi round1'dir ve
henüz etiketlenmedi. Bu kartın tek amacı, kalibrasyonda ÖLÇÜLEN hata
kalıplarının round1'in ~2.400 satırına taşınmaması.

## Kalıplar nereden ölçülüyor

Hakemlik ÖNCESİ anlık görüntüden (`*.yedek-hakemlik`) — anotatörün gerçekten
yazdığı şey. Güncel dosyalar hakemlikten geçti; oradan ölçmek "kimse hata
yapmamış" der. Yedek yoksa betik o anotatör için kalıp basmaz ve nedenini
raporun başına yazar; sessizce "temiz" demez.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from dataclasses import dataclass
from dataclasses import field as dc_field
from pathlib import Path
from typing import Callable, Iterable, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.build_gold import read_review_csv
from scripts.lint_review_csv import SEVERITY_ERROR, lint
from src.extraction.llm.schema import HEDEF_KITLE_LABELS

DEFAULT_REVIEW_DIR = "data/gold/review"
#: Hakemlik ÖNCESİ anlık görüntü — "anotatör gerçekte ne yazdı".
PRE_ARBITRATION_SUFFIX = ".yedek-hakemlik"
DOCS_SUBDIR = "belgeler"

ANNOTATORS = ("A", "B", "C", "D")

#: Anotatör -> ana turda açacağı dosya (`_atama.md` "Kim neyi açacak").
ROUND1_FILES = {
    "A": "round1_A.csv",
    "B": "round1_B.csv",
    "C": "round1_main_C.csv",
    "D": "round1_main_D.csv",
}

#: Kılavuz §8: 20 belge · 260 satır ≈ 25 dk. Tahminlerin TEK dayanağı budur.
GUIDE_ROWS = 260
GUIDE_MINUTES = 25


def calibration_name(ad: str) -> str:
    return f"round0_kalibrasyon_{ad}.csv"


def out_name(ad: str) -> str:
    return f"_calisma-listesi-{ad}.md"


def sure_dk(satir: int) -> int:
    """Kılavuz §8'in kendi hızıyla süre. Ölçüm değil, kılavuzdan TÜRETME."""
    return round(satir * GUIDE_MINUTES / GUIDE_ROWS)


# --------------------------------------------------------------------------- #
# Kalıplar
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Kalip:
    """Ölçülebilir tek hata kalıbı + doğrusu."""

    ad: str
    baslik: str
    dogrusu: str
    kaynak: str
    #: (satır, belge metni | None) -> kalıba giriyor mu
    dedektor: Optional[Callable[[dict, Optional[str]], bool]] = None
    #: `lint` mesajında aranan parça (dedektör yerine)
    lint_ipucu: Optional[str] = None


def _clean(value: Optional[str]) -> str:
    return (value or "").strip()


def _sayisal_alan(field: str) -> bool:
    return field in {"vade_ay", "taksit_sayisi", "finansman_tutari",
                     "odul_miktari", "tahsis_ucreti", "kar_payi_orani",
                     "indirim_orani"}


def _hedef_kitle_gecersiz(row: dict, _metin: Optional[str]) -> bool:
    if row.get("field") != "hedef_kitle":
        return False
    ham = _clean(row.get("gold_value"))
    if not ham:
        return False
    try:
        cozulmus = json.loads(ham)
        parcalar = ([str(x) for x in cozulmus] if isinstance(cozulmus, list)
                    else [str(cozulmus)])
    except (json.JSONDecodeError, ValueError):
        parcalar = [p.strip() for p in ham.replace(",", "|").split("|")]
    return any(p.strip().strip('"[]⁠') not in HEDEF_KITLE_LABELS
               for p in parcalar if p.strip())


def _yanlis_absent(row: dict, _metin: Optional[str]) -> bool:
    return (_clean(row.get("verdict")).casefold() == "absent"
            and not _clean(row.get("model_value")))


def _taksit_vade(row: dict, metin: Optional[str]) -> bool:
    return (row.get("field") == "taksit_sayisi"
            and bool(_clean(row.get("gold_value")))
            and metin is not None and "taksit" not in metin)


def _metinden_alinti(row: dict, _metin: Optional[str]) -> bool:
    """Sayısal alana kanonik değer yerine cümle yazılmış."""
    ham = _clean(row.get("gold_value"))
    if not ham or not _sayisal_alan(row.get("field", "")):
        return False
    if ham.startswith(("{", "[")):
        return False
    # Harf içeriyorsa kanonik değil ("48 aya kadar", "1-12 ay arası").
    return any(ch.isalpha() for ch in ham)


KALIPLAR: tuple[Kalip, ...] = (
    Kalip("yanlis-absent", "Model boş bırakmışken `absent` yazmak",
          "`ok` yazın — `absent` yalnız modelin ÜRETTİĞİ değeri reddetmek "
          "içindir. Model bir şey üretmediyse reddedilecek bir şey yok.",
          "kılavuz §3.3 kutusu", dedektor=_yanlis_absent),
    Kalip("absent-dolu-deger", "`gold_value`'ya belgenin ne hakkında "
          "olduğunu yazmak",
          "O sütun alanın DEĞERİ içindir, belgenin özeti değil. Değer yoksa "
          "hücre BOŞ kalır. `build_gold` açıklamayı sessizce atar.",
          "kılavuz §5", lint_ipucu="verdict=absent ama gold_value dolu"),
    Kalip("aralik", "Tek değerli alana iki değer yazmak",
          "Üst sınırı/bitişi yazın, diğerini `note`'a düşün. Ayrıştırıcı "
          "REDDETMEZ — ilk ucu alır, yani sessizce yanlış değer gold'a girer.",
          "`_bicim-karti.md`", lint_ipucu="tek deger alir ama"),
    Kalip("metinden-alinti", "Kanonik değer yerine metinden alıntı",
          "`48` yazın, `\"en fazla 48 aya kadar\"` değil. Aralık gerekiyorsa "
          "`{\"min\": 12, \"max\": 48}`.", "kılavuz §5",
          dedektor=_metinden_alinti),
    Kalip("hedef-kitle", "`hedef_kitle`ye serbest metin yazmak",
          "Yalnız dört etiket: " + " · ".join(f"`{x}`" for x in HEDEF_KITLE_LABELS)
          + ". \"Bireysel müşteriler\" segment DEĞİLDİR (herkes demek) → "
          "`absent`. Cümleyi saklamak isterseniz `kampanya_kosullari`na.",
          "kılavuz §4 `hedef_kitle`", dedektor=_hedef_kitle_gecersiz),
    Kalip("taksonomi-disi", "8 sınıf dışında `campaign_type` uydurmak",
          "Sınıf kümesi SABİTTİR. Uymuyorsa `absent` — `null` bir hatanın "
          "değil bir kararın adıdır.", "kılavuz §4.13/1",
          lint_ipucu="kampanya türü"),
    Kalip("taksit-vade", "\"taksit\" geçmeyen belgede `taksit_sayisi` doldurmak",
          "Belgede \"taksit\" kelimesi yoksa o sayı VADEDİR → `vade_ay`. "
          "`taksit_sayisi` `absent` olur.", "kılavuz §4 kelime testi",
          dedektor=_taksit_vade),
    Kalip("fix-bos", "`fix` yazıp `gold_value`'yu boş bırakmak",
          "`build_gold` burada DURUR. Doğru değeri yazın ya da kararı "
          "`absent`/`unclear` yapın.", "kılavuz §3.2",
          lint_ipucu="verdict=fix ama gold_value bos"),
)


# --------------------------------------------------------------------------- #
# Veri tipleri
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Bulgu:
    """Bir kalıbın tek anotatördeki ölçümü."""

    kalip: Kalip
    #: Kalıba giren hücreler — `(doc_id, field)`.
    hucreler: tuple[tuple[str, str], ...] = ()
    ornekler: tuple[str, ...] = ()

    @property
    def sayi(self) -> int:
        return len(self.hucreler)


@dataclass
class HazirlikKarti:
    ad: str
    kalibrasyon_dosyasi: str
    round1_dosyasi: str
    round1_satir: int
    round1_belge: int
    kalibrasyon_satir: int
    acik_karar: Optional[int] = None
    bulgular: list[Bulgu] = dc_field(default_factory=list)
    uyarilar: list[str] = dc_field(default_factory=list)

    @property
    def toplam_hata(self) -> int:
        """AYRIK hücre sayısı — bir hücre birden çok kalıba girebilir.

        Kalıp sayılarını toplamak D'de 278 verir ama gerçek hücre sayısı
        daha azdır: `gold_value`'ya belge açıklaması yazılan satır hem
        `absent-dolu-deger` hem `metinden-alinti` kalıbına düşer.
        """
        return len({h for b in self.bulgular for h in b.hucreler})


# --------------------------------------------------------------------------- #
# Ölçüm
# --------------------------------------------------------------------------- #
def _kisalt(text: str, limit: int = 60) -> str:
    text = " ".join(_clean(text).split())
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _hucre(text: str, limit: int = 60) -> str:
    return _kisalt(text, limit).replace("|", "\\|")


def _belge_metni(review_dir: Path, doc_id: str, önbellek: dict) -> Optional[str]:
    if doc_id not in önbellek:
        yol = review_dir / DOCS_SUBDIR / f"{doc_id}.txt"
        önbellek[doc_id] = (yol.read_text(encoding="utf-8").casefold()
                            if yol.exists() else None)
    return önbellek[doc_id]


def _ornek(row: dict) -> str:
    deger = _clean(row.get("gold_value")) or _clean(row.get("verdict")) or "(boş)"
    return f"`{row.get('field')}` = {_kisalt(deger, 40)}"


def olc(ad: str, review_dir: Path) -> HazirlikKarti:
    """Tek anotatörün kalibrasyondaki kalıplarını ölçer. CSV'ye YAZMAZ."""
    review_dir = Path(review_dir)
    kalib = review_dir / calibration_name(ad)
    round1 = review_dir / ROUND1_FILES[ad]

    r1_rows = read_review_csv(round1) if round1.exists() else []
    kart = HazirlikKarti(
        ad=ad, kalibrasyon_dosyasi=str(kalib), round1_dosyasi=str(round1),
        round1_satir=len(r1_rows),
        round1_belge=len({r["doc_id"] for r in r1_rows}),
        kalibrasyon_satir=0)

    onceki = kalib.with_name(kalib.name + PRE_ARBITRATION_SUFFIX)
    if not onceki.exists():
        kart.uyarilar.append(
            f"`{onceki.name}` yok — hakemlik öncesi anlık görüntü okunamadı. "
            f"Kalıplar ÖLÇÜLEMEDİ; bu 'hata yok' demek değildir.")
        return kart

    rows = read_review_csv(onceki)
    kart.kalibrasyon_satir = len(rows)
    kart.acik_karar = sum(1 for r in rows
                          if _clean(r.get("verdict")) or _clean(r.get("gold_value")))

    lint_mesajlari = [(f.doc_id, f.field, f.message)
                      for f in lint([str(onceki)]) if f.severity == SEVERITY_ERROR]
    satir_dizini = {(r["doc_id"], r["field"]): r for r in rows}
    önbellek: dict = {}

    for kalip in KALIPLAR:
        eslesenler: list[dict] = []
        if kalip.lint_ipucu:
            for doc_id, field, mesaj in lint_mesajlari:
                if kalip.lint_ipucu in mesaj:
                    eslesenler.append(satir_dizini.get(
                        (doc_id, field), {"doc_id": doc_id, "field": field}))
        elif kalip.dedektor:
            for row in rows:
                metin = _belge_metni(review_dir, row["doc_id"], önbellek)
                if kalip.dedektor(row, metin):
                    eslesenler.append(row)
        if eslesenler:
            kart.bulgular.append(Bulgu(
                kalip=kalip,
                hucreler=tuple(dict.fromkeys(
                    (r["doc_id"], r["field"]) for r in eslesenler)),
                ornekler=tuple(_ornek(r) for r in eslesenler[:3])))

    kart.bulgular.sort(key=lambda b: -b.sayi)
    return kart


def topla(review_dir: str | Path = DEFAULT_REVIEW_DIR,
          annotators: Iterable[str] = ANNOTATORS) -> dict[str, HazirlikKarti]:
    review_dir = Path(review_dir)
    mevcut = [ad for ad in annotators
              if (review_dir / calibration_name(ad)).exists()]
    if not mevcut:
        raise FileNotFoundError(f"{review_dir}: kalibrasyon CSV'si bulunamadı.")
    return {ad: olc(ad, review_dir) for ad in mevcut}


# --------------------------------------------------------------------------- #
# Rapor
# --------------------------------------------------------------------------- #
def render(kart: HazirlikKarti) -> str:
    satirlar = [
        f"# Round1 Hazırlık Kartı — Anotatör {kart.ad}",
        "",
        "> `scripts/calisma_listesi.py` üretti. Elle düzenlemeyin; yeniden",
        "> koşuda üzerine yazılır. Betik CSV'lere **yazmaz**, yalnız okur.",
        "",
        "## Kalibrasyona GERİ DÖNMÜYORSUNUZ",
        "",
        "`round0_kalibrasyon_*` bir kalibrasyon turuydu, gold değil. İşi ekibi",
        "hizalamaktı ve onu yaptı: dört kural çıktı (kılavuz §4 K1–K4).",
        "**O dosya yeniden etiketlenmeyecek.**",
        "",
        f"Sizin açacağınız dosya: **`{Path(kart.round1_dosyasi).name}`** — "
        f"{kart.round1_satir} satır, {kart.round1_belge} belge.",
        f"Kılavuz §8'in kendi hızıyla (**{GUIDE_ROWS} satır ≈ {GUIDE_MINUTES} dk**) "
        f"kabaca **{sure_dk(kart.round1_satir)} dakika**. Bu ölçüm değil,",
        "kılavuzdaki orandan türetmedir; ilk 50 satır daha yavaş gider.",
        "",
    ]

    for uyari in kart.uyarilar:
        satirlar += [f"> ⚠️ {uyari}", ""]

    if kart.acik_karar is not None:
        kapsama = 100 * kart.acik_karar / max(kart.kalibrasyon_satir, 1)
        satirlar += [
            "## Kalibrasyonda ne yaptınız",
            "",
            f"Açık kararınız: **{kart.acik_karar}/{kart.kalibrasyon_satir}** "
            f"(%{kapsama:.0f}). 'Açık karar' = dolu `verdict` **ya da** dolu",
            "`gold_value` (kılavuz §3.2: yazılmış düzeltme karardır).",
            "",
        ]
        if kapsama < 100:
            satirlar += [
                "> Round1'de boş hücre **v2 protokolündedir**: onay değil,",
                "> \"karar verilmedi\" demektir ve satır gold'a HİÇ girmez.",
                "> Kapsama düşer ama doğruluk şişmez — `lint` boş `verdict`i",
                "> HATA sayar ve dosyayı `build_gold` öncesi durdurur.",
                "",
            ]

    satirlar += ["## Kendi hata kalıplarınız — kalibrasyonda ÖLÇÜLDÜ", ""]
    if not kart.bulgular:
        satirlar += [
            "Ölçülen kalıp yok. Kalibrasyon dosyanızda `lint` hatası ve",
            "bilinen anlam hatası bulunamadı.",
            "",
            "Yine de round1 dört katı büyük ve kalibrasyonda görmediğiniz",
            "alanlar içeriyor; kılavuzun §3.3 kutusunu ve §4 K1–K4'ü okuyun.",
            "",
        ]
    else:
        kalip_toplami = sum(b.sayi for b in kart.bulgular)
        satirlar += [
            f"**{kart.toplam_hata} ayrık hücre**, {len(kart.bulgular)} kalıpta. "
            f"Kaynak: "
            f"`{Path(kart.kalibrasyon_dosyasi).name}{PRE_ARBITRATION_SUFFIX}`",
            "(hakemlik ÖNCESİ — sizin gerçekten yazdığınız hâli).",
            "",
        ]
        if kalip_toplami != kart.toplam_hata:
            satirlar += [
                f"> Kalıp sayıları toplamı {kalip_toplami}, ayrık hücre "
                f"{kart.toplam_hata}: bir hücre birden çok kalıba girebilir",
                "> (ör. `gold_value`'ya belge açıklaması yazmak hem "
                "`absent-dolu-deger` hem `metinden-alinti`dir).",
                "",
            ]
        satirlar += [
            "| # | Kalıp | Hücre | Doğrusu | Kural |",
            "|---:|---|---:|---|---|",
        ]
        for i, b in enumerate(kart.bulgular, start=1):
            satirlar.append(
                f"| {i} | {_hucre(b.kalip.baslik, 55)} | **{b.sayi}** "
                f"| {_hucre(b.kalip.dogrusu, 200)} | {b.kalip.kaynak} |")
        satirlar += ["", "### Kendi satırlarınızdan örnek", ""]
        for i, b in enumerate(kart.bulgular, start=1):
            ornek = " · ".join(b.ornekler) or "—"
            satirlar.append(f"{i}. **{b.kalip.baslik}** — {_hucre(ornek, 160)}")
        satirlar.append("")

    satirlar += [
        "## Round1'e başlamadan",
        "",
        "1. `_ANA-TUR-TALIMATI.md` — iki dakika, tek sayfa.",
        "2. Yukarıdaki tabloyu bir kez okuyun. Bunlar sizin kalıplarınız;",
        "   round1 dört kat büyük, aynı kalıp dört kat maliyet demek.",
        "3. İlk 20 satırı doldurduktan sonra `lint`i koşun — kalıp hâlâ",
        "   sürüyorsa 20 satırda görün, 600 satırda değil:",
        "",
        "```bash",
        ".venv/bin/python -m scripts.lint_review_csv \\",
        f"    data/gold/review/{Path(kart.round1_dosyasi).name}",
        "```",
        "",
        "## Takıldığınızda",
        "",
        "- Biçim: `_bicim-karti.md` · Kural: `../ANNOTATION_GUIDE.md`",
        "- Belgenin tam metni: `belgeler/<doc_id>.txt`",
        "- Emin değilseniz **tahmin etmeyin** — `unclear` yazın (kılavuz §3.4).",
        "- Kılavuz vakayı cevaplamıyorsa bu bir kılavuz kusurudur: söyleyin.",
        "",
        "## Üreten komut",
        "",
        "```bash",
        ".venv/bin/python -m scripts.calisma_listesi",
        "```",
    ]
    return "\n".join(satirlar) + "\n"


def yaz(kartlar: dict[str, HazirlikKarti], out_dir: str | Path) -> list[Path]:
    out_dir = Path(out_dir)
    yazilan = []
    for ad, kart in sorted(kartlar.items()):
        yol = out_dir / out_name(ad)
        yol.write_text(render(kart), encoding="utf-8")
        yazilan.append(yol)
    return yazilan


def ozet(kartlar: dict[str, HazirlikKarti]) -> str:
    adlar = [k.ad for k in KALIPLAR]
    satirlar = ["| Anotatör | round1 dosyası | satır | ~dk | açık karar | "
                + " | ".join(adlar) + " | TOPLAM |",
                "|---|---|---:|---:|---|" + "---:|" * (len(adlar) + 1)]
    for ad, kart in sorted(kartlar.items()):
        sayac = Counter({b.kalip.ad: b.sayi for b in kart.bulgular})
        hucreler = [str(sayac.get(k, 0)) for k in adlar]
        acik = ("—" if kart.acik_karar is None
                else f"{kart.acik_karar}/{kart.kalibrasyon_satir}")
        satirlar.append(
            f"| {ad} | {Path(kart.round1_dosyasi).name} | {kart.round1_satir} "
            f"| {sure_dk(kart.round1_satir)} | {acik} | "
            + " | ".join(hucreler) + f" | **{kart.toplam_hata}** |")
    return "\n".join(satirlar)


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Round1 hazırlık kartı üretir (CSV'lere yazmaz).")
    parser.add_argument("--review-dir", default=DEFAULT_REVIEW_DIR)
    parser.add_argument("--out-dir", default=None,
                        help="varsayılan: --review-dir ile aynı")
    parser.add_argument("--ozet", action="store_true",
                        help="dosya yazma, yalnız özet tabloyu bas")
    args = parser.parse_args(argv)

    kartlar = topla(args.review_dir)
    print(ozet(kartlar))
    if args.ozet:
        return 0
    for yol in yaz(kartlar, args.out_dir or args.review_dir):
        print(f"yazıldı: {yol}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
