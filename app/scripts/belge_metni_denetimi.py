"""İnceleme paketlerindeki belge metni eksikliğini denetler ve onarır.

İlgili: `scripts/to_review_csv.py` (metinleri asıl üreten yer) ·
`data/gold/review/belgeler/` · `data/gold/review/_belge-eksikligi.md`

## Neden bu araç var

`to_review_csv.generate()` iki çıktıyı **aynı** `--out-dir` altına yazar:
inceleme CSV'lerini ve `belgeler/<doc_id>.txt` tam metinlerini
(`to_review_csv.py:486-489`). İkisi ayrıldığı anda paket sessizce sakatlanır.

Ölçülen vaka: `round2_zor_vaka.csv` geçici bir dizine üretildi
(`docs/rapor/zor-vaka-kurleme.md` §Tekrar üretim, `--out-dir <tmp>`), sonra
**yalnız CSV** `data/gold/review/` altına taşındı. Klasörde zaten duran 41
metin v1/v2 turlarından kalmıştı; zor-vaka paketine ÖZGÜ 32 belgenin metni
hiç gelmedi. CSV 73 belge / 949 satır diyor, anotatör 41 belge görüyor.

Bu, linter'ın yakalayamadığı bir sınıf: `lint_review_csv` satır BİÇİMİNE
bakar, satırın anote EDİLEBİLİR olup olmadığına değil. Metni olmayan belge
için anotatörün tek dürüst cevabı "karar veremedim"dir; kova 4 (recall
kontrolü) ise tam metin okunmadan doldurulamaz.

## Neden boş .txt yazmak yasak

Boş belge, anotatöre "bu alan metinde yok" dedirtir — yani `absent` kararı
üretir. O karar gold'a girer ve modelin doğru çıkarımını YANLIŞ sayar.
Eksik metin görünür bir engel, boş metin görünmez bir hatadır. Bu yüzden
`--uret` bir metni ancak kaynağından birebir okuyabildiğinde yazar; okuyamazsa
o belgeyi raporlar ve dosyaya DOKUNMAZ.

## Metin nereden geliyor

`doc_id` ham korpustan türetilir (`preannotate._unique_doc_id`), veritabanında
böyle bir kolon yoktur. Kimliği DB satırına bağlayan tek köprü ön-anotasyon
JSON'undaki `source_url`'dür — üreteç de belgeyi oradan tanır. Zincir:

    doc_id → preannotations*.json[source_url] → campaigns.raw_text

Yazmadan önce iki kaynak karşılaştırılır: `campaigns.raw_text` ile
ön-anotasyondaki `text` birebir aynı olmalı. Ayrıştıkları belge yazılmaz,
raporlanır — hangisinin doğru olduğunu bu betik bilemez ve tahmin etmez.
(Ölçüm: zor-vaka paketinin 73 belgesinin 73'ünde ikisi birebir aynı.)

## Kullanım

    python3 -m scripts.belge_metni_denetimi                  # kapı: denetle
    python3 -m scripts.belge_metni_denetimi --uret           # eksikleri üret
    python3 -m scripts.belge_metni_denetimi --inceleme-dir <dir>

Çıkış kodu: eksik/boş metin kaldıysa 1, temizse 0.
"""

from __future__ import annotations

import argparse
import glob
import json
import sqlite3
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.lint_review_csv import read_rows

VARSAYILAN_INCELEME = "data/gold/review"
VARSAYILAN_DB = "data/demo.db"
VARSAYILAN_ON_ANOTASYON = "data/gold/preannotations*.json"

NEDEN_YOK = "metin dosyasi yok"
NEDEN_BOS = "metin dosyasi bos"


@dataclass(frozen=True)
class Eksik:
    """Anote edilemez bir (paket, belge) çifti."""

    csv_adi: str
    doc_id: str
    neden: str

    def __str__(self) -> str:
        return f"{self.csv_adi}: {self.doc_id} — {self.neden}"


def csv_belge_kimlikleri(path: str | Path) -> set[str]:
    """İnceleme CSV'sindeki tekil `doc_id` kümesi.

    Okuma `lint_review_csv.read_rows` üzerinden yapılır: elektronik tablodan
    gelen sayfa-adı satırı orada zaten ele alınıyor ve o mantığın iki kopyası
    olması, birinin düzeltilip diğerinin unutulması demek olurdu.
    """
    rows, _ = read_rows(str(path))
    return {r["doc_id"].strip() for r in rows if r.get("doc_id", "").strip()}


def denetle(csv_yollari: list[str] | list[Path],
            belgeler_dir: str | Path) -> list[Eksik]:
    """Her CSV'deki her `doc_id` için `belgeler/<doc_id>.txt` var mı, dolu mu.

    Boş dosya da eksik sayılır: anotatör açısından "metin yok"tan farksız,
    ama sessizce `absent` kararı ürettiği için daha zararlı.
    """
    belgeler = Path(belgeler_dir)
    bulgular: list[Eksik] = []
    for yol in sorted(csv_yollari, key=lambda p: Path(p).name):
        ad = Path(yol).name
        for doc_id in sorted(csv_belge_kimlikleri(yol)):
            txt = belgeler / f"{doc_id}.txt"
            if not txt.exists():
                bulgular.append(Eksik(ad, doc_id, NEDEN_YOK))
            elif not txt.read_text(encoding="utf-8").strip():
                bulgular.append(Eksik(ad, doc_id, NEDEN_BOS))
    return bulgular


def on_anotasyon_kaynagi(yollar: list[str] | list[Path]
                         ) -> dict[str, list[dict]]:
    """`doc_id` → o kimliğe ait TÜM ön-anotasyon kayıtları.

    Liste dönüyor, tek kayıt değil: aynı belge birden çok turda ön-anotalanmış
    olabilir (v1 / v2 / zor) ve korpus tazelendiğinde eski turun `text`'i
    veritabanındaki güncel `raw_text`'ten ayrışır. Tek kayıt seçmek, hangi
    turun kazandığına göre değişen keyfi bir sonuç üretirdi; `uret` bunun
    yerine kayıtların HERHANGİ BİRİ veritabanıyla örtüşüyorsa yazar.
    """
    kaynak: dict[str, list[dict]] = {}
    for yol in yollar:
        veri = json.loads(Path(yol).read_text(encoding="utf-8"))
        for doc in veri.get("docs", []):
            kaynak.setdefault(doc["id"], []).append(doc)
    return kaynak


def db_metinleri(db_yolu: str | Path) -> dict[str, set[str]]:
    """`source_url` → o URL'ye ait TEKİL `raw_text` kümesi.

    Küme dönüyor çünkü `source_url` tekil değil (aynı sayfa birden çok kez
    hasat edilmiş olabilir). Küme birden büyükse hangi metnin doğru olduğu
    belirsizdir; `uret` böyle bir belgeyi yazmaz.

    Bağlantı SALT OKUNUR açılır: bu betik demo veritabanına asla yazmaz.
    """
    con = sqlite3.connect(f"file:{Path(db_yolu)}?mode=ro", uri=True)
    try:
        metinler: dict[str, set[str]] = {}
        for url, raw in con.execute(
                "SELECT source_url, raw_text FROM campaigns"):
            if url is None:
                continue
            metinler.setdefault(url, set()).add(raw or "")
        return metinler
    finally:
        con.close()


def uret(eksikler: list[Eksik], belgeler_dir: str | Path,
         kaynak: dict[str, list[dict]], db: dict[str, set[str]],
         ) -> tuple[dict[str, int], list[tuple[str, str]]]:
    """Eksik metinleri veritabanından yazar.

    Dönüş: (yazılan `doc_id` → karakter sayısı, [(doc_id, ret gerekçesi)]).

    Yazma koşulları — hepsi sağlanmazsa dosyaya DOKUNULMAZ:
      1. `doc_id` ön-anotasyonda var (kimlik → URL köprüsü kurulabiliyor),
      2. URL veritabanında var ve TEK bir `raw_text` taşıyor,
      3. `raw_text` boş değil,
      4. `raw_text`, o kimliğin ön-anotasyon metinlerinden BİRİYLE birebir
         aynı — yani iki bağımsız kaynak aynı belgeyi gösteriyor.
    """
    hedef = Path(belgeler_dir)
    hedef.mkdir(parents=True, exist_ok=True)
    yazilan: dict[str, int] = {}
    yazilamayan: list[tuple[str, str]] = []

    for doc_id in sorted({e.doc_id for e in eksikler}):
        kayitlar = kaynak.get(doc_id)
        if not kayitlar:
            yazilamayan.append((doc_id, "on-anotasyon JSON'larinda kayit yok"))
            continue
        urller = {k.get("source_url") for k in kayitlar if k.get("source_url")}
        if not urller:
            yazilamayan.append((doc_id, "on-anotasyon kaydinda source_url yok"))
            continue
        if len(urller) > 1:
            yazilamayan.append((
                doc_id,
                f"on-anotasyon turlari {len(urller)} farkli source_url "
                f"gosteriyor, kimlik koprusu belirsiz"))
            continue
        url = next(iter(urller))
        adaylar = db.get(url)
        if not adaylar:
            yazilamayan.append((doc_id, f"veritabaninda bu URL yok: {url}"))
            continue
        if len(adaylar) > 1:
            yazilamayan.append((
                doc_id,
                f"ayni URL icin {len(adaylar)} farkli raw_text var, hangisi "
                f"oldugu belirsiz: {url}"))
            continue
        raw = next(iter(adaylar))
        if not raw.strip():
            yazilamayan.append((doc_id, "veritabanindaki raw_text bos"))
            continue
        if raw not in {k.get("text", "") for k in kayitlar}:
            yazilamayan.append((
                doc_id,
                "raw_text hicbir on-anotasyon turunun metniyle ortusmuyor — "
                "hangisinin dogru oldugu bu betikten bilinemez"))
            continue
        # `newline=""` bilinçli: metin baytı baytına yazılsın, satır sonu
        # çevirisi platforma göre değişip DB'deki kayıttan ayrışmasın.
        with (hedef / f"{doc_id}.txt").open("w", encoding="utf-8",
                                            newline="") as fh:
            fh.write(raw)
        yazilan[doc_id] = len(raw)

    return yazilan, yazilamayan


def _csv_yollari(inceleme_dir: str | Path) -> list[Path]:
    """Paket CSV'leri. Yedekler (`.yedek*`, `.xlsx`) kapsam dışı."""
    return sorted(Path(inceleme_dir).glob("round*.csv"))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--inceleme-dir", default=VARSAYILAN_INCELEME,
                    help="inceleme paketlerinin klasoru")
    ap.add_argument("--db", default=VARSAYILAN_DB,
                    help="kaynak veritabani (SALT OKUNUR acilir)")
    ap.add_argument("--on-anotasyon", nargs="*",
                    default=[VARSAYILAN_ON_ANOTASYON],
                    help="on-anotasyon JSON'lari (glob olabilir)")
    ap.add_argument("--uret", action="store_true",
                    help="eksik metinleri veritabanindan yaz")
    ap.add_argument("--quiet", action="store_true", help="yalnizca ozet bas")
    args = ap.parse_args(argv)

    yollar = _csv_yollari(args.inceleme_dir)
    belgeler = Path(args.inceleme_dir) / "belgeler"
    eksikler = denetle(yollar, belgeler)

    if args.uret and eksikler:
        pre = sorted({p for kalip in args.on_anotasyon
                      for p in (glob.glob(kalip) or [kalip])})
        kaynak = on_anotasyon_kaynagi(pre)
        yazilan, yazilamayan = uret(eksikler, belgeler, kaynak,
                                    db_metinleri(args.db))
        print(f"uretildi: {len(yazilan)} metin")
        if not args.quiet:
            for doc_id, boyut in sorted(yazilan.items()):
                print(f"  + {doc_id} ({boyut} karakter)")
        for doc_id, neden in yazilamayan:
            print(f"  ! {doc_id} — URETILEMEDI: {neden}")
        eksikler = denetle(yollar, belgeler)

    if not args.quiet:
        for bulgu in eksikler:
            print(bulgu)
        if eksikler:
            print()

    print(f"{len(yollar)} paket · {len(eksikler)} anote edilemez belge satiri")
    if eksikler:
        print("Metni olmayan belge anote EDILEMEZ; o satirlar paketten "
              "cikarilmali ya da metin uretilmeli (--uret).")
    return 1 if eksikler else 0


if __name__ == "__main__":
    sys.exit(main())
