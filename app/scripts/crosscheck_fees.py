"""Masrafsızlık iddiasını bankanın kendi ücret tarifesiyle çapraz kontrol et.

İlgili: ./crosscheck_rates.py (kardeş desen, oranlar için),
        ../docs/rapor/zor-vaka-kurleme.md §"celiskili" (bu betiği doğuran bulgu),
        CLAUDE.md §18 yenilikçilik hedefi #2

Kullanım:
    python -m scripts.crosscheck_fees
    python -m scripts.crosscheck_fees --out data/gold/fee_crosscheck.csv

## Neden bu betik var

CLAUDE.md §18'in 2 numaralı yenilikçilik hedefi şu: *"masrafsız deyip tahsis
ücreti alanı yakala"*. Zor-vaka kürlemesi bu hedefi gold sette `celiskili`
etiketiyle aramanın **yapısal olarak imkânsız** olduğunu ölçtü: 13 aday
incelendi, kampanya belgesi olan yalnız 1'i çıktı, kalan 12'si ücret
tarifesiydi ve hiçbiri çelişki değildi — oralarda "ücret alınmaz" kapsamı
belirli, meşru bir ifade.

Sebep şu: **belge içi çelişki korpusta pratik olarak yok.** Kampanya "masrafsız"
der; ücreti ilan eden belge ise bankanın AYRI bir ücret tarifesidir. Yani bu bir
belgeler ARASI karşılaştırma. `crosscheck_rates.py` oranlar için tam bu deseni
kuruyor; bu betik aynı deseni **ücretlere** taşır.

## Bu betik neyi İDDİA ETMEZ

Bir kampanyanın "Dosya Masrafsız Konut Finansmanı" demesi, bankanın tarifesinde
%0,5 tahsis ücreti ilan etmiş olmasıyla **kendiliğinden çelişmez.** Kampanya
pekâlâ meşru bir *muafiyet* olabilir: standart ücret %0,5'tir, bu kampanyada
alınmaz.

Ölçülen gerçek bunu doğruluyor: 33 ilan edilmiş kayıttan **30'u tam olarak
%0,5** ve bu değer beş bankanın hepsinde geçiyor — yani BDDK'nın konut
finansmanı için koyduğu üst sınır sektörde fiilen tek fiyat. Dolayısıyla
"tarifede ücret var" tek başına hiçbir şey söylemez; öyle kullanılırsa betik
meşru muafiyetleri sahtekârlık diye işaretler.

(Kalan 3 kayıt raporda ayrıca listelenir. Biri kendi içinde bir tutarsızlık:
Türkiye Emlak Katılım taşıt tahsis ücretini bir formda %0,5, başka bir formda
%0,1 ilan ediyor. Bu betiğin işi değil ama sinyal kaydedilir.)

Ayırt edici olan şey **kapsam**: muafiyet bir koşula bağlı mı?

    kosullu_muafiyet — iddia var, tarifede ücret var, kampanya muafiyeti bir
                       koşulla sınırlıyor (yeni müşteri, tutar, tarih).
                       ÇELİŞKİ DEĞİL; ama kullanıcının görmesi gereken şey
                       "masrafsız" değil, "koşul dışında %0,5".
    kapsamsiz_iddia  — iddia var, tarifede ücret var, hiçbir koşul yok.
                       Çelişki ADAYI; insan hakemliğine gider.
    tutarli          — tarifede o ürün için ücret ilan edilmemiş / sıfır.
    tarife_yok       — o banka/ürün için bağımsız kaynak toplanamadı.

`kosullu_muafiyet` bir kusur değil, **ürünün kendisidir**: şartname §5.7'nin
istediği karşılaştırma tablosunda "masrafsız" yazmak yanıltıcıdır; doğru olan
"yeni müşteriye masrafsız, aksi hâlde %0,5" demektir.

## Neden anotasyon CSV'leri EZİLMEZ

`crosscheck_rates.py` ile aynı gerekçe: `gold_value` insanın kararıdır. Makine
önerisini oraya yazmak, değerlendirmeyi kendi kendini doğrulayan bir döngüye
sokar. Çıktı AYRI bir dosyadır, her satır kaynak belgesiyle gerekçelenir.

## Eşleştirme neden SIKI

Bu depoda gevşek desenlerin maliyeti iki kez ölçüldü: bir sezgisel 101 belgenin
87'sinde yanlış pozitif üretti, zor-vaka taramasının ilk desen kümesi ise
`celiskili`yi 476 belgede "buldu" (gerçek: 13). Bu yüzden burada **beş** sıkı
kapı var ve her biri bu betiğin ilk koşusunda GERÇEKTEN görülmüş bir yanlış
pozitifi kapatıyor:

  K1 — İddia, ürün sözcüğüne YAKIN olmalı (±60 karakter). Ölçüldü: gevşek
       pencerede Albaraka'nın "masrafsız bir bankacılık sunuyoruz" cümlesi
       "finansal ihtiyaçlarına" ifadesindeki `ihtiyaç` sözcüğüne takılıp
       İhtiyaç Finansmanı iddiası sayılıyordu.
  K2 — `masrafsız (bir) bankacılık` kalıbı AÇIKÇA dışlanır. Havale/EFT/FAST
       masrafsızlığını anlatır, finansman tahsis ücretiyle ilgisi yoktur.
  K3 — Tarife tarafında `Tahsis Ücreti` etiketi ile değer arasına BAŞKA bir
       ücret kalemi (rehin, ekspertiz, ipotek, sigorta, noter) girmemeli.
       Ölçüldü: bu kapı olmadan Türkiye Finans'ın "Taşıt Rehin Tesis Ücreti
       350,92 TL" kalemi tahsis ücreti sanılıyordu.
  K4 — MAKULLÜK. Tahsis ücreti düzenlenmiş bir kalem; oran %1,0'ı, TL figürü
       25.000'i geçemez. Bu kapı olmadan rapor "Türkiye Finans %4,09 tahsis
       ücreti ilan ediyor" diyordu — 4,09 bir KÂR PAYI ORANI. Vakıf Katılım
       tarafında da "100.000 TL" (finansman tutarı kolonu) ücret sanılıyordu.
  K5 — AYNI BELGE yasağı. Bir iddia, kendi belgesindeki ücret kaydıyla
       eşleştirilmez. Kontrol belgeler ARASI olmak zorunda; aksi hâlde
       kampanya kendi kanıtı olur.

Koşul tarafında da bir daraltma var: `kampanya kapsamında`, `mobil üzerinden`
ve `dijital kanal` ifadeleri koşul SAYILMAZ. Her kampanya sayfasında geçerler,
muafiyetin kapsamını daraltmazlar; ilk koşuda Albaraka satırında tek "koşul"
olarak yakalanıp meşru olmayan bir `kosullu_muafiyet` üretmişlerdi.
"""

from __future__ import annotations

import argparse
import csv
import glob
import os
import re
import sys
from dataclasses import dataclass
from dataclasses import field as dc_field
from typing import Any, Optional

# --- sınıflandırma sonuçları -------------------------------------------------

V_KOSULLU = "kosullu_muafiyet"
V_KAPSAMSIZ = "kapsamsiz_iddia"
V_TUTARLI = "tutarli"
V_TARIFE_YOK = "tarife_yok"

# --- ölçülmüş sabitler -------------------------------------------------------

#: İddia ile ürün sözcüğü arasındaki azami uzaklık (K1). 60 karakter,
#: "Dosya Masrafsız İhtiyaç Finansmanı" gibi bitişik kalıpları yakalar ama
#: aynı paragraftaki alakasız ürün bahsini yakalamaz.
ADJACENCY = 60

#: Tahsis ücreti etiketi ile değeri arasındaki azami uzaklık.
FEE_VALUE_WINDOW = 120

#: `Tahsis Ücreti` etiketinden sonra ürün sözcüğü aranan pencere. Kuveyt Türk /
#: Albaraka / Emlak tarifeleri "Tahsis Ücreti Konut Finansmanı 0.5% Taşıt
#: Finansmanı 0.5% ..." biçiminde tek etiket altında ürünleri sıralar.
FEE_PRODUCT_WINDOW = 400

URUN_SINIFLARI = ("konut", "tasit", "ihtiyac")

#: Tarife (bağımsız kaynak) tarafı. `live/` ve `archive/` YOK — orası iddia
#: tarafı; ikisini karıştırmak kampanyayı kendi kanıtı yapar.
TARIFE_KAYNAKLARI = ("docs", "products", "manual")

#: Varsayılan çıktılar. `data/gold/review/` ALTINDA DEĞİL — orada insanın
#: doldurduğu `round*.csv` dosyaları duruyor ve oraya yazan bir betik
#: anotasyonu ezme riskini taşır.
VARSAYILAN_CSV = "data/gold/fee_crosscheck.csv"
VARSAYILAN_RAPOR = "data/gold/fee_crosscheck.md"

#: İddia tarafı. `products/` iki listede de var, çünkü bankanın ürün sayfası
#: hem tarifeyi ilan edebilir hem masrafsızlık iddiası taşıyabilir. Karışmayı
#: dizin değil, `crosscheck()` içindeki **aynı belge** kapısı engelliyor:
#: bir iddia kendi belgesindeki ücret kaydıyla eşleştirilmez.
IDDIA_KAYNAKLARI = ("live", "archive", "products")

_URUN_RE = {
    "konut": re.compile(r"konut", re.IGNORECASE),
    "tasit": re.compile(r"ta[şs][ıi]t|ara[çc]\s*(?:kredi|finansman|al[ıi]m)",
                        re.IGNORECASE),
    "ihtiyac": re.compile(r"ihtiya[çc]", re.IGNORECASE),
}

#: Masrafsızlık İDDİASI. "dosya masrafsız", "masraf alınmaz", "masrafsız".
_IDDIA_RE = re.compile(
    r"(dosya\s+masrafs[ıi]z\w*|masrafs[ıi]z\w*|masraf\s*al[ıi]nmaz|"
    r"dosya\s*masraf[ıi]\s*(?:al[ıi]nmaz|yok|ödemeden|odemeden)|"
    r"s[ıi]f[ıi]r\s*masraf|tahsis\s*ücreti\s*al[ıi]nmaz)",
    re.IGNORECASE)

#: K2 — bankacılık hizmetleri masrafsızlığı. Finansman ücretiyle ilgisi yok.
#: Araya sıfat/belirteç girebiliyor: ölçüldü, Albaraka "masrafsız **bir**
#: bankacılık sunuyoruz" yazıyor ve bitişik desen bunu kaçırıyordu.
_HIZMET_MASRAFSIZ_RE = re.compile(
    r"masrafs[ıi]z\s*(?:bir\s+|bu\s+)?"
    r"(?:bankac[ıi]l[ıi]k|hesap\w*|kart\w*|havale|eft|fast)", re.IGNORECASE)

#: Muafiyeti sınırlayan BELİRLEYİCİ koşullar — muafiyetin KİME/NE ZAMANE/NE
#: KADARA açık olduğunu söyleyenler.
#:
#: Kasıtlı olarak DIŞARIDA bırakılanlar ve gerekçeleri (hepsi ölçülmüş yanlış
#: pozitif): `kampanya kapsamında` — her kampanya sayfasında geçer, kapsamı
#: daraltmaz, dolayısıyla ayırt edici değil. `mobil üzerinden` / `dijital
#: kanal` — başvuru kanalını anlatır, muafiyetin kapsamını değil; Albaraka
#: satırında bu ifade tek "koşul" olarak yakalanıp meşru olmayan bir
#: `kosullu_muafiyet` üretmişti.
_KOSUL_RE = re.compile(
    r"(yeni\s+mü[şs]teri\w*|ilk\s+kez\s+mü[şs]teri|"
    r"maa[şs]\s*mü[şs]teri\w*|maa[şs][ıi]n[ıi]\s*\w+\s*ta[şs][ıi]y|"
    r"\d[\d.,]*\s*(?:tl|₺)\s*(?:ve\s*)?(?:üzeri|üstü|kadar)|"
    r"\d{1,2}[./]\d{1,2}[./]\d{2,4}\s*tarihine\s*kadar|"
    r"ilk\s+\d+\s*(?:ay|m[üu][şs]teri|ba[şs]vuru)|"
    r"\d+\s*aya?\s*kadar\s*vade)",
    re.IGNORECASE)

#: K3 — tahsis ücreti etiketiyle değer arasına giremeyecek başka ücret kalemleri.
_BASKA_KALEM_RE = re.compile(
    r"rehin|ekspertiz|ipotek|sigorta|noter|de[ğg]erleme|fek|muvafakat|"
    r"yenileme|üyelik|uyelik", re.IGNORECASE)

_TAHSIS_RE = re.compile(r"tahsis\s*ücret\w*|tahsis\s*ucret\w*", re.IGNORECASE)

#: Ücret değeri: yüzde ya da TL. Yüzde ÖNCE denenir — "%0,5" içindeki "0,5"in
#: TL sanılmaması için.
_DEGER_RE = re.compile(
    r"(%\s*\d[\d.,]*|\d[\d.,]*\s*%|\d[\d.,]*\s*(?:tl|₺|try))",
    re.IGNORECASE)

#: K4 — MAKULLÜK. Tahsis ücreti düzenlenmiş bir kalemdir: BDDK konut
#: finansmanında finansman tutarının **%0,5**'ini üst sınır koyuyor ve
#: tarifesi toplanabilen beş bankanın tamamı bu değeri ilan ediyor. Üst sınır
#: BSMV dahil ilan edilmiş figürlere yer bırakmak için %1,0 tutuldu.
#:
#: Bu kapı iki ölçülmüş yanlış pozitifi kapatıyor:
#:   * Türkiye Finans ürün sayfasında `Tahsis Ücreti` etiketinden sonra gelen
#:     ilk yüzde **%4,09**'du — o bir KÂR PAYI ORANI. Kapı olmadan rapor
#:     "banka %4,09 tahsis ücreti ilan ediyor" diyordu.
#:   * Vakıf Katılım taşıt oran tablosunda etiketten sonraki ilk sayı
#:     **100.000 TL** — finansman tutarı kolonu, ücret değil.
TAHSIS_YUZDE_MAX = 1.0
TAHSIS_TL_MIN = 50.0
TAHSIS_TL_MAX = 25_000.0

#: Tarifede ücretin SIFIR olduğunu söyleyen ifadeler.
_SIFIR_RE = re.compile(
    r"(?:tahsis\s*ücret\w*[^.]{0,60}?)?(?:al[ıi]nmaz|al[ıi]nmamaktad[ıi]r|"
    r"yoktur|ücretsizdir|ucretsizdir)", re.IGNORECASE)


# --- veri yapıları -----------------------------------------------------------


@dataclass
class IlanEdilenUcret:
    """Bankanın kendi tarifesinde ilan ettiği tahsis ücreti."""

    banka: str
    urun: str
    deger: str
    kaynak_dosya: str
    kaynak_alinti: str


@dataclass
class Iddia:
    """Bir kampanya/ürün sayfasındaki masrafsızlık iddiası."""

    banka: str
    doc_id: str
    kaynak_dosya: str
    urunler: list[str]
    iddia_alinti: str
    kosullar: list[str] = dc_field(default_factory=list)


@dataclass
class Row:
    """Bir iddia × ürün sınıfı kesişimi + çapraz kontrol sonucu."""

    banka: str
    doc_id: str
    urun: str
    sonuc: str
    iddia_alinti: str
    ilan_edilen: str = ""
    kosul: str = ""
    ilan_kaynagi: str = ""
    ilan_alintisi: str = ""
    dashboard_ifadesi: str = ""
    not_: str = ""

    def to_csv(self) -> dict[str, Any]:
        return {
            "banka": self.banka,
            "doc_id": self.doc_id,
            "urun_sinifi": self.urun,
            "sonuc": self.sonuc,
            "iddia_alintisi": self.iddia_alinti,
            "ilan_edilen_tahsis_ucreti": self.ilan_edilen,
            "muafiyet_kosulu": self.kosul,
            "ilan_kaynagi": self.ilan_kaynagi,
            "ilan_alintisi": self.ilan_alintisi,
            "dashboard_ifadesi": self.dashboard_ifadesi,
            "not": self.not_,
        }


CSV_ALANLARI = list(Row("", "", "", "", "").to_csv().keys())


# --- yardımcılar -------------------------------------------------------------


def _oku(path: str) -> str:
    try:
        with open(path, encoding="utf-8") as fh:
            return fh.read()
    except OSError:
        return ""


def _banka_of(path: str) -> str:
    parts = os.path.normpath(path).split(os.sep)
    return parts[-3] if len(parts) >= 3 else ""


def _doc_id_of(path: str) -> str:
    """`raw/<banka>/<alt>/<slug>.txt` -> `<banka>--<slug>`.

    `preannotate`/`build_gold` ile aynı biçim; satırlar oradaki `doc_id`'lerle
    elle eşleştirilebilsin.
    """
    parts = os.path.normpath(path).split(os.sep)
    slug = os.path.splitext(parts[-1])[0]
    return f"{_banka_of(path)}--{slug}"


def _sadelestir(s: str) -> str:
    """Alıntıyı tek satıra indir — CSV hücresi okunabilir kalsın."""
    return re.sub(r"\s+", " ", s).strip()


def _deger_temiz(s: str) -> str:
    return _sadelestir(s).replace(" ", "")


# --- tarife tarafı -----------------------------------------------------------


def urun_sinifi_dosyadan(path: str) -> Optional[str]:
    """Tek ürünlü sayfalarda ürün sınıfı dosya adından gelir.

    Vakıf Katılım gibi bankalar tahsis ücretini ayrı ürün sayfalarında ilan
    ediyor (`finansmanlar-konut-finansmani.txt`); orada metnin içinde ürün
    başlığı olmayabilir.
    """
    ad = os.path.basename(path).lower()
    for urun, rx in _URUN_RE.items():
        if rx.search(ad):
            return urun
    return None


def ilan_edilen_ucretler(raw_dir: str = "data/raw") -> list[IlanEdilenUcret]:
    """Bankaların kendi belgelerinden tahsis ücretini çıkar.

    İki farklı tarife biçimi var ve ikisi de destekleniyor:

      Biçim A (etiket → ürün → değer):
        "Tahsis Ücreti Konut Finansmanı 0.5% Taşıt Finansmanı 0.5% ..."
      Biçim B (tek ürünlü sayfa, etiket → değer):
        "\\"Tahsis Ücreti\\" finansman tutarının %0,5'idir."

    K3 kapısı ikisinde de uygulanır: etiketle değer arasına başka bir ücret
    kalemi girmişse o eşleşme atılır.
    """
    out: list[IlanEdilenUcret] = []
    gorulen: set[tuple[str, str, str]] = set()
    # `live/` KASITLI olarak dışarıda: orası iddia tarafıdır. Kampanya
    # sayfasını hem iddia hem bağımsız kaynak saymak, çapraz kontrolü kendi
    # kendini doğrulayan bir döngüye sokar.
    desenler = [os.path.join(raw_dir, "*", alt, "*.txt")
                for alt in TARIFE_KAYNAKLARI]
    yollar: list[str] = []
    for d in desenler:
        yollar.extend(glob.glob(d))

    for path in sorted(yollar):
        text = _oku(path)
        if not text or not _TAHSIS_RE.search(text):
            continue
        banka = _banka_of(path)
        dosya_urunu = urun_sinifi_dosyadan(path)

        for m in _TAHSIS_RE.finditer(text):
            kuyruk = text[m.end():m.end() + FEE_PRODUCT_WINDOW]

            # Biçim A — etiketten sonra ürün başlıkları sıralanıyor.
            eslesti = False
            for urun, rx in _URUN_RE.items():
                u = rx.search(kuyruk)
                if not u:
                    continue
                pencere = kuyruk[u.end():u.end() + FEE_VALUE_WINDOW]
                deger = _deger_bul(pencere)
                if not deger:
                    continue
                eslesti = True
                _ekle(out, gorulen, banka, urun, deger, path,
                      _sadelestir(text[m.start():m.end() + u.end() + 40]))

            if eslesti or not dosya_urunu:
                continue

            # Biçim B — tek ürünlü sayfa; ürün dosya adından geliyor.
            deger = _deger_bul(kuyruk[:FEE_VALUE_WINDOW])
            if deger:
                _ekle(out, gorulen, banka, dosya_urunu, deger, path,
                      _sadelestir(text[max(0, m.start() - 30):
                                       m.end() + FEE_VALUE_WINDOW // 2]))
    return out


def _sayi_coz(raw: str) -> Optional[float]:
    """TR biçimli sayıyı çöz: `1.234,56` -> 1234.56, `0.5` -> 0.5.

    Belirsizlik gerçek: `%0.5` içindeki nokta ondalık ayıraç, `100.000 TL`
    içindeki nokta binlik ayıraç. Ayırt edici kural — noktadan sonra tam üç
    hane varsa ve virgül yoksa binlik ayıraçtır.
    """
    s = re.sub(r"[^\d.,]", "", raw)
    if not s:
        return None
    if "," in s:
        s = s.replace(".", "").replace(",", ".")
    elif re.fullmatch(r"\d{1,3}(?:\.\d{3})+", s):
        s = s.replace(".", "")
    try:
        return float(s)
    except ValueError:
        return None


def makul_mu(deger: str) -> bool:
    """K4 — değer bir tahsis ücreti olabilir mi?"""
    sayi = _sayi_coz(deger)
    if sayi is None:
        return False
    if "%" in deger:
        return 0.0 < sayi <= TAHSIS_YUZDE_MAX
    return TAHSIS_TL_MIN <= sayi <= TAHSIS_TL_MAX


def _deger_bul(pencere: str) -> Optional[str]:
    """Pencereden tahsis ücreti değerini al — K3 ve K4 kapılarıyla.

    Tüm adaylar taranır, ilki değil: ölçüldü, oran tablolarında etiketten
    sonraki İLK sayı ücret değil (kâr payı oranı ya da finansman tutarı), ama
    makul olan aynı pencerede biraz sonra geliyor ("... 500 ₺ ... *Tahsis
    ücreti finansman tutarının %0,5'idir").

    Yüzde biçimi TL'ye TERCİH EDİLİR: tahsis ücreti oransal ilan edilen bir
    kalemdir, TL figürü genelde belirli bir örnek tutara ait.
    """
    tl: Optional[str] = None
    for d in _DEGER_RE.finditer(pencere):
        # K3 — değerden ÖNCE başka bir ücret kalemi geçiyorsa o değer tahsis
        # ücretine ait değildir ("Taşıt Rehin Tesis Ücreti 350,92 TL").
        if _BASKA_KALEM_RE.search(pencere[:d.start()]):
            break
        aday = _deger_temiz(d.group(1))
        if not makul_mu(aday):
            continue
        if "%" in aday:
            return aday
        tl = tl or aday
    return tl


def _ekle(out: list[IlanEdilenUcret], gorulen: set[tuple[str, str, str]],
          banka: str, urun: str, deger: str, path: str, alinti: str) -> None:
    """Banka+ürün+belge başına bir kayıt.

    Belge kırılımı KORUNUR (banka+ürüne indirilmez): `crosscheck()` içindeki
    "aynı belge" kapısı, iddianın kendi belgesini bağımsız kaynak saymamak için
    alternatif bir belgeye ihtiyaç duyuyor.
    """
    anahtar = (banka, urun, os.path.relpath(path))
    if anahtar in gorulen:
        return
    gorulen.add(anahtar)
    out.append(IlanEdilenUcret(banka=banka, urun=urun, deger=deger,
                               kaynak_dosya=os.path.relpath(path),
                               kaynak_alinti=alinti[:300]))


# --- iddia tarafı ------------------------------------------------------------


def masrafsizlik_iddialari(raw_dir: str = "data/raw") -> list[Iddia]:
    """Kampanya/ürün sayfalarındaki masrafsızlık iddialarını topla (K1+K2)."""
    out: list[Iddia] = []
    yollar: list[str] = []
    for alt in IDDIA_KAYNAKLARI:
        yollar.extend(glob.glob(os.path.join(raw_dir, "*", alt, "*.txt")))

    for path in sorted(yollar):
        text = _oku(path)
        if not text:
            continue
        urunler: set[str] = set()
        alintilar: list[str] = []
        kosullar: set[str] = set()

        for m in _IDDIA_RE.finditer(text):
            # K2 — "masrafsız bankacılık" finansman ücreti iddiası değil.
            if _HIZMET_MASRAFSIZ_RE.match(text, m.start()):
                continue
            # K1 — ürün sözcüğü iddiaya YAKIN olmalı.
            yakin = text[max(0, m.start() - ADJACENCY):m.end() + ADJACENCY]
            bulunan = [u for u, rx in _URUN_RE.items() if rx.search(yakin)]
            if not bulunan:
                continue
            urunler.update(bulunan)
            alintilar.append(_sadelestir(
                text[max(0, m.start() - 70):m.end() + 90]))
            # Koşul, iddianın geniş bağlamında aranır (kampanya koşulu
            # genelde ayrı bir cümlede/madde listesinde durur).
            genis = text[max(0, m.start() - 600):m.end() + 900]
            for k in _KOSUL_RE.finditer(genis):
                kosullar.add(_sadelestir(k.group(0)))

        if urunler:
            out.append(Iddia(
                banka=_banka_of(path), doc_id=_doc_id_of(path),
                kaynak_dosya=os.path.relpath(path),
                urunler=sorted(urunler),
                iddia_alinti=" | ".join(alintilar[:3])[:400],
                kosullar=sorted(kosullar)[:5]))
    return out


# --- çapraz kontrol ----------------------------------------------------------


def _norm_deger(deger: str) -> str:
    """Biçim varyantlarını tek anahtara indir: `%0,5` = `0.5%` = `%0.5`.

    Biçim varyantı bir tutarsızlık DEĞİLDİR; yalnız sayı ve birim önemli.
    """
    sayi = _sayi_coz(deger)
    birim = "%" if "%" in deger else "TL"
    return f"{sayi}{birim}" if sayi is not None else deger


def _yaklasik(deger: str, hedef: float) -> bool:
    sayi = _sayi_coz(deger)
    return sayi is not None and abs(sayi - hedef) < 1e-9


def _sifir_mi(alinti: str) -> bool:
    return bool(_SIFIR_RE.search(alinti))


def crosscheck(iddialar: list[Iddia],
               ucretler: list[IlanEdilenUcret]) -> list[Row]:
    """Her iddia × ürün sınıfı için bir satır üret."""
    index: dict[tuple[str, str], list[IlanEdilenUcret]] = {}
    for u in ucretler:
        index.setdefault((u.banka, u.urun), []).append(u)
    rows: list[Row] = []
    for idd in iddialar:
        for urun in idd.urunler:
            # AYNI BELGE kapısı: iddianın kendi belgesindeki ücret kaydı
            # bağımsız kaynak değildir. Bu kontrol belgeler ARASI olmak
            # zorunda — zor-vaka ölçümü belge içi çelişkinin korpusta
            # bulunmadığını gösterdi.
            adaylar = [u for u in index.get((idd.banka, urun), [])
                       if os.path.normpath(u.kaynak_dosya)
                       != os.path.normpath(idd.kaynak_dosya)]
            # Yüzde biçimi TL'ye tercih edilir: tahsis ücreti oransal ilan
            # edilen bir kalem, TL figürü belirli bir örnek tutara ait
            # (Vakıf Katılım taşıt tablosunda "500 ₺" = 100.000 TL'nin %0,5'i).
            # Karşılaştırma tablosunda oran yazmak bankalar arası kıyası
            # mümkün kılar, TL örneği kılmaz (CLAUDE.md §17 adil kıyas).
            adaylar.sort(key=lambda u: 0 if "%" in u.deger else 1)
            ilan = adaylar[0] if adaylar else None
            row = Row(banka=idd.banka, doc_id=idd.doc_id, urun=urun,
                      sonuc=V_TARIFE_YOK, iddia_alinti=idd.iddia_alinti,
                      kosul="; ".join(idd.kosullar))
            if ilan is None:
                row.not_ = (f"{idd.banka} için {urun} tahsis ücreti korpusta "
                            f"ilan edilmiş değil — bağımsız kaynak eksik")
                rows.append(row)
                continue

            row.ilan_edilen = ilan.deger
            row.ilan_kaynagi = ilan.kaynak_dosya
            row.ilan_alintisi = ilan.kaynak_alinti

            if _sifir_mi(ilan.kaynak_alinti):
                row.sonuc = V_TUTARLI
                row.not_ = "tarife de ücret alınmadığını söylüyor"
                row.dashboard_ifadesi = "masrafsız"
            elif idd.kosullar:
                row.sonuc = V_KOSULLU
                row.not_ = ("muafiyet koşula bağlı — koşul dışında tarife "
                            f"ücreti ({ilan.deger}) geçerli")
                row.dashboard_ifadesi = (
                    f"{idd.kosullar[0]} kapsamında masrafsız; "
                    f"aksi hâlde {ilan.deger}")
            else:
                row.sonuc = V_KAPSAMSIZ
                row.not_ = ("kampanya koşulsuz masrafsızlık iddia ediyor ama "
                            f"tarifede {ilan.deger} tahsis ücreti ilan edilmiş "
                            "— insan hakemliği gerekir")
                row.dashboard_ifadesi = f"iddia: masrafsız / tarife: {ilan.deger}"
            rows.append(row)
    return rows


# --- rapor -------------------------------------------------------------------

_REHBER = {
    V_KOSULLU: "Dashboard'da 'masrafsız' YAZMA — koşulu birlikte göster",
    V_KAPSAMSIZ: "Belgeye bak: gerçek çelişki mi, yoksa koşul metinde "
                 "yazmıyor mu?",
    V_TUTARLI: "İddia tarifeyle uyumlu — işlem yok",
    V_TARIFE_YOK: "O bankanın ücret tarifesi toplanmalı (hasat işi)",
}


def render_report(rows: list[Row], ucretler: list[IlanEdilenUcret],
                  banka_sayisi: int) -> str:
    toplam = len(rows) or 1
    sayim: dict[str, int] = {}
    for r in rows:
        sayim[r.sonuc] = sayim.get(r.sonuc, 0) + 1

    lines = [
        "# Masrafsızlık İddiası — Ücret Tarifesi Çapraz Kontrol Raporu",
        "",
        "> Otomatik üretildi: `python -m scripts.crosscheck_fees`. "
        "Anotasyon CSV'leri DEĞİŞTİRİLMEZ; bu dosya öneridir.",
        "",
        "Bu, CLAUDE.md §18 hedef #2'nin (\"masrafsız deyip tahsis ücreti "
        "alanı yakala\") **belgeler arası** kurulumudur. Zor-vaka kürlemesi "
        "belge İÇİ çelişkinin korpusta pratik olarak bulunmadığını ölçtü; "
        "iddia kampanyada, ücret ise bankanın ayrı tarifesinde duruyor.",
        "",
        f"- **İncelenen iddia × ürün satırı:** {len(rows)}",
        f"- **Bağımsız kaynak:** {len(ucretler)} ilan edilmiş tahsis ücreti "
        f"kaydı, {banka_sayisi} banka",
        "",
        "| Sonuç | Adet | Oran | Ne yapılmalı |",
        "|---|---:|---:|---|",
    ]
    for v in (V_KAPSAMSIZ, V_KOSULLU, V_TUTARLI, V_TARIFE_YOK):
        n = sayim.get(v, 0)
        lines.append(f"| `{v}` | {n} | %{100 * n / toplam:.1f} | {_REHBER[v]} |")

    # Sektör tek fiyatta mı? Sabit yazmak yerine veriden hesaplanır.
    standart = [u for u in ucretler
                if "%" in u.deger and _yaklasik(u.deger, 0.5)]
    aykiri = [u for u in ucretler if u not in standart]
    lines += [
        "",
        "## Neden `kosullu_muafiyet` bir kusur değil, ÜRÜNÜN KENDİSİ",
        "",
        f"Ölçülen gerçek: {len(ucretler)} ilan edilmiş kayıttan "
        f"**{len(standart)}'i tam olarak %0,5** — BDDK'nın konut finansmanı "
        f"için koyduğu üst sınır, yani sektörde fiilen tek fiyat. Dolayısıyla "
        "\"tarifede ücret var\" tek başına hiçbir şey söylemez; öyle "
        "kullanılırsa bu betik meşru muafiyetleri sahtekârlık diye işaretler.",
        "",
        "Ayırt edici olan **kapsam**. Kullanıcının karşılaştırma tablosunda "
        "görmesi gereken şey \"masrafsız\" değil, `dashboard_ifadesi` "
        "kolonundaki koşullu ifadedir.",
        "",
    ]
    if aykiri:
        lines += [
            "### %0,5 dışındaki kayıtlar",
            "",
            "| Banka | Ürün | Değer | Kaynak |",
            "|---|---|---|---|",
        ]
        for u in aykiri:
            lines.append(f"| {u.banka} | {u.urun} | `{u.deger}` | "
                         f"`{os.path.basename(u.kaynak_dosya)}` |")
        lines.append("")

    # Banka İÇİ tutarsızlık: aynı banka+ürün için farklı değerler. Bu betiğin
    # asıl işi değil ama ölçüldüğü için sessizce geçilmez.
    # Yalnız AYNI BİRİMDEKİ çatışma tutarsızlıktır. `%0,5` ile `500 ₺`
    # çatışmaz — 500 TL, 100.000 TL'nin %0,5'idir; bu bir birim farkı.
    # (Bu bölümün ilk hâli tam bu yanlış pozitifi üretiyordu.)
    coklu: dict[tuple[str, str, str], set[str]] = {}
    for u in ucretler:
        birim = "%" if "%" in u.deger else "TL"
        coklu.setdefault((u.banka, u.urun, birim), set()).add(u.deger)
    catisan = {k: v for k, v in coklu.items()
               if len({_norm_deger(d) for d in v}) > 1}
    if catisan:
        lines += [
            "### Banka içi tutarsızlık (yan bulgu)",
            "",
            "Aynı banka, aynı ürün ve **aynı birim** için farklı belgelerde "
            "farklı tahsis ücreti ilan ediyor. Bu betiğin hedefi değil, ama "
            "ölçüldüğü için kayda geçiyor:",
            "",
        ]
        for (b, urn, birim), degerler in sorted(catisan.items()):
            lines.append(f"- `{b}` / `{urn}` ({birim}): "
                         + ", ".join(f"`{d}`" for d in sorted(degerler)))
        lines.append("")

    lines += [
        "## İlan edilmiş tahsis ücretleri (bağımsız kaynak)",
        "",
        "| Banka | Ürün | İlan edilen | Kaynak |",
        "|---|---|---|---|",
    ]
    for u in sorted(ucretler, key=lambda x: (x.banka, x.urun)):
        lines.append(f"| {u.banka} | {u.urun} | `{u.deger}` | "
                     f"`{os.path.basename(u.kaynak_dosya)}` |")

    eksik = sorted({(r.banka, r.urun) for r in rows
                    if r.sonuc == V_TARIFE_YOK})
    if eksik:
        lines += [
            "",
            "## Kapsam boşluğu — sessizce atlanmadı",
            "",
            "Şu banka/ürün çiftleri için bağımsız kaynak yok; satır üretildi "
            "ama `tarife_yok` olarak işaretlendi. Kapsamı büyütmenin yolu "
            "hasat, kod değil:",
            "",
        ]
        for b, u in eksik:
            lines.append(f"- `{b}` / `{u}` — ücret tarifesi belgesi toplanmalı")

    if not rows:
        lines += ["", "**Satır üretilmedi.** İki kapıdan biri hiç geçmedi; "
                  "desenler gevşetilmeden önce ölçülmeli."]

    lines += [
        "",
        "## Related",
        "- [[zor-vaka-kurleme]] — bu betiği doğuran `celiskili` bulgusu",
        "- `scripts/crosscheck_rates.py` — aynı desenin oranlar için hâli",
        "",
    ]
    return "\n".join(lines)


# --- CLI ---------------------------------------------------------------------


def main(argv: Optional[list[str]] = None) -> int:
    ap = argparse.ArgumentParser(
        description="Masrafsızlık iddialarını ücret tarifesiyle çapraz kontrol et")
    ap.add_argument("--raw-dir", default="data/raw")
    ap.add_argument("--out", default=VARSAYILAN_CSV)
    ap.add_argument("--report", default=VARSAYILAN_RAPOR)
    args = ap.parse_args(argv)

    ucretler = ilan_edilen_ucretler(args.raw_dir)
    iddialar = masrafsizlik_iddialari(args.raw_dir)
    rows = crosscheck(iddialar, ucretler)

    os.makedirs(os.path.dirname(os.path.abspath(args.out)) or ".",
                exist_ok=True)
    with open(args.out, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=CSV_ALANLARI)
        w.writeheader()
        for r in rows:
            w.writerow(r.to_csv())

    banka_sayisi = len({u.banka for u in ucretler})
    with open(args.report, "w", encoding="utf-8") as fh:
        fh.write(render_report(rows, ucretler, banka_sayisi))

    sayim: dict[str, int] = {}
    for r in rows:
        sayim[r.sonuc] = sayim.get(r.sonuc, 0) + 1
    print(f"{len(iddialar)} iddia belgesi -> {len(rows)} satır -> {args.out}")
    print(f"{len(ucretler)} ilan edilmiş tahsis ücreti, "
          f"{banka_sayisi} banka")
    for v in (V_KAPSAMSIZ, V_KOSULLU, V_TUTARLI, V_TARIFE_YOK):
        print(f"  {v}: {sayim.get(v, 0)}")
    print(f"rapor -> {args.report}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
