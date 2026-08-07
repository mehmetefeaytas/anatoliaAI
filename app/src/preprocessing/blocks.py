"""Blok düzeyinde içerik/çerçeve ayrımı — üç sinyal, öncelikli.

İlgili: ../../scripts/split_trainable.py (tekrar sinyali buradan gelir),
        ../../scripts/boilerplate_audit.py (kapsam kararı),
        ../../docs/rapor/boilerplate-kapsam.md (ölçümler ve gerekçe),
        ../extraction/rules/synonyms.py, ../domain/terminology.py

## Neden bu modül var

Mevcut çerçeve ayıklaması **tek sinyalle (tekrar) iki ayrı soruyu**
cevaplamaya çalışıyor:

    1. Bu blok site çerçevesi mi?   -> tekrar İYİ bir kanıt
    2. Bu blok ürünle ilgili mi?    -> tekrar KÖTÜ bir kanıt

Ölçüldü: ayıklamanın kaybettiği 8 alanın 7'si çöptü (KVKK'daki "ücretsiz",
çerez metnindeki "1 yıl", "Hoş Geldin Ramazan!" afişi, blog başlıkları) ama
1'i gerçek içerikti — her ürün sayfasında geçtiği için, yani **tekrar ettiği
için** silinen meşru bir başvuru koşulu cümlesi.

Tersi de var: 3'ten az benzer sayfası olan bir bankanın çerez bloğu tekrar
eşiğini geçemiyor ve bugün **hiç silinemiyor**.

## Öncelik sırası: alan-dışılık > alan değeri > tekrar

Sıra sekiz kombinasyonun hepsine karşı sınandı; dördü sırayı zorluyor:

| alan-dışı | değer | tekrar | olması gereken | gerektirdiği kural |
|---|---|---|---|---|
| var | **var** | var | SİL — KVKK'daki "ücretsiz" | alan-dışı > değer |
| var | yok | **yok** | SİL — az sayfalı bankanın çerezi | alan-dışı, tekrarsız da yeter |
| yok | **var** | var | KORU — şablonlaşmış başvuru cümlesi | değer > tekrar |
| yok | yok | var | SİL — menü/altbilgi | tekrar, değersiz de yeter |

Sıra ters kurulursa kazanç sıfırlanır: KVKK bloğundaki "ücretsiz" bir
`masraf_durumu` tetikleyicisidir ve naif bir değer-koruması o bloğu kurtarıp
bugünkü halüsinasyon düşüşünü geri verir.

## Neden blok, neden bölge yayılımı

Belgeler HTML çıkarımından **tek satır** olarak geliyor — boş satır yok,
düzen ipucu yok. Bu yüzden bölme cümle dizisi üzerinden yapılır.

Ve karar tek cümleye bakarak verilemez: "en geç otuz (30) gün içinde
ÜCRETSİZ olarak sonuçlandırılmaktadır" cümlesinde hiçbir alan-dışı işaret
yoktur; onu KVKK yapan şey cümlelerce önce geçen "Kişisel Veri"dir. Bu yüzden
alan-dışılık bir **bölge** olarak yayılır ve ancak güçlü bir alan değeri
görülünce ya da yayılım ömrü dolunca söner.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable, Optional

from ..extraction.rules.synonyms import FOLDED_FIELD_TRIGGERS, matches
from .clean import split_sentences, tr_fold_ascii

#: Bir bloğa girecek en fazla cümle. **1 = cümle düzeyi** ve bu ölçümle
#: seçildi: 2 cümlelik blokta içerik/KVKK sınırına oturan blok tamamen
#: siliniyordu ve "Yeni açılan ve vadesi yenilenen TL Katılma Hesapları
#: yüksek paylaşım oranları üzerinden kâr dağıtacaktır" gibi GERÇEK ürün
#: cümleleri, yalnız ardından gelen çerez cümlesi yüzünden gidiyordu.
#: n-gram yaklaşımında düzeltmeye çalıştığımız sınır sorununun aynısı.
BLOK_CUMLE = 1

#: Alan-dışı bölgenin, yeni işaret görülmeden kaç blok daha süreceği.
#: Ölçümle ayarlanır; 0 = yayılım kapalı (yalnız işaretin kendi bloğu silinir).
YAYILIM_BLOK = 6

#: Bölgeyi söndürmek için gereken alan değeri. Yüksek tutuluyor — bölgeyi
#: zayıf bir sinyalle söndürmek KVKK metnini geri getirir.
SONDURME_DEGERI = 3

#: Bir cümlenin çerçeve sayılması için gereken BELGE sayısı (grup içinde).
CERCEVE_MIN_BELGE = 3


# --------------------------------------------------------------------------- #
# Alan-dışılık — yüksek kesinlikli olmak ZORUNDA
# --------------------------------------------------------------------------- #
#
# Bu sinyal tek başına siliyor (tekrar kanıtı aranmadan), dolayısıyla yanlış
# pozitifi doğrudan içerik kaybı demek. Liste bu yüzden dar ve ifade düzeyinde:
# tek başına "veri", "politika", "çerez" gibi sözcükler DEĞİL, yalnız hukuki
# metin bloklarını adlandıran kalıplar.
_ANTI_DESENLER: tuple[str, ...] = (
    r"cerez(?:ler)?\s+(?:politika|ayar|aydinlatma|kullan|tercih)",
    r"cerez\s+(?:kullaniyoruz|kullanilmaktadir)",
    r"zorunlu\s+cerez|analitik\s+cerez|pazarlama\s+cerez|islevsel\s+cerez",
    r"kisisel\s+veri(?:ler)?(?:in|inizin)?\s+(?:korunmasi|islenmesi|sahibi)",
    r"aydinlatma\s+metni",
    r"acik\s+riza\s+(?:metni|beyani)",
    r"veri\s+sorumlusu",
    r"gizlilik\s+(?:politikasi|bildirimi)",
    r"kullanim\s+(?:kosullari|sartlari)\s*$|kullanim\s+kosullari\s+ve",
    r"kvkk",
    r"6698\s+sayili",
    r"site\s+haritasi",
    r"bizi\s+takip\s+edin|sosyal\s+medya\s+hesap",
    r"cookie\s+(?:policy|settings|consent)",
)
_ANTI_RE = re.compile("|".join(_ANTI_DESENLER), re.IGNORECASE)


def anti_skoru(metin: str) -> int:
    """Blokta kaç alan-dışı kalıp geçiyor."""
    return len(_ANTI_RE.findall(tr_fold_ascii(metin)))


# --------------------------------------------------------------------------- #
# Alan değeri
# --------------------------------------------------------------------------- #
#: Sayı + birim: oran, para, vade, taksit. `split_trainable._SIGNAL_RE` ile
#: aynı aile ama burada blok metnine uygulanır.
_DEGER_RE = re.compile(
    r"%\s?\d|\d[\d.,]*\s?%"
    r"|\d[\d.,]*\s?(?:tl\b|try\b|₺|turk lirasi)"
    r"|\d+\s*(?:ay\b|yil\b|taksit)"
    r"|\d{1,2}[./]\d{1,2}[./]\d{2,4}",
    re.IGNORECASE)


#: Alan sözcükleri — SOLDAN sınırlı, ek serbest.
#:
#: `FIELD_TRIGGERS` üzerinden `matches()` yetmiyor: `keyword_pattern` kısa
#: anahtarı (<=4 karakter) iki taraftan sınırlıyor, dolayısıyla "vade"
#: anahtarı **"vadesi"yi kaçırıyor**. Ölçümde yakalandı — gerçek bir ürün
#: cümlesi ("vadesi yenilenen ... paylaşım oranları") `değer=0` alıyordu.
#: Burada Türkçenin sondan eklemeli yapısına uygun ayrı bir desen kullanılır.
_ALAN_SOZCUK_RE = re.compile(
    r"\b(?:kar\s*payi|kâr\s*payi|vade|taksit|tahsis|masraf|ucret|oran|"
    r"finansman|katilma\s*hesab|cari\s*hesap|kampanya|puan|indirim|"
    r"faiz|getiri|tutar|limit|odeme)", re.IGNORECASE)


def deger_skoru(metin: str, terimler: Optional[Iterable[str]] = None) -> int:
    """Blokta kaç alan-değeri sinyali var.

    Üç kaynak toplanır: alan sözcükleri, sayı+birim desenleri ve verilirse
    katılım finansı terim sözlüğü. Üçü de repoda zaten var — bu sinyal için
    yeni altyapı gerekmiyor.
    """
    katli = tr_fold_ascii(metin)
    skor = len(_DEGER_RE.findall(katli))
    skor += len(_ALAN_SOZCUK_RE.findall(katli))
    for anahtarlar in FOLDED_FIELD_TRIGGERS.values():
        if any(matches(a, katli) for a in anahtarlar):
            skor += 1
    if terimler:
        skor += sum(1 for t in terimler if t and matches(t, katli))
    return skor


# --------------------------------------------------------------------------- #
# Bloklar ve karar
# --------------------------------------------------------------------------- #

@dataclass(frozen=True)
class Blok:
    """Ardışık birkaç cümle. `bas`/`son` ORİJİNAL metindeki karakter aralığı."""

    metin: str
    bas: int
    son: int


@dataclass
class Karar:
    """Tek bir blok için karar ve gerekçesi — denetlenebilir olmak zorunda."""

    blok: Blok
    tut: bool
    gerekce: str
    anti: int = 0
    deger: int = 0
    tekrar: float = 0.0
    bolge: bool = False          # alan-dışı bölge yayılımıyla mı silindi

    def as_dict(self) -> dict:
        return {"bas": self.blok.bas, "son": self.blok.son, "tut": self.tut,
                "gerekce": self.gerekce, "anti": self.anti,
                "deger": self.deger, "tekrar": round(self.tekrar, 3),
                "bolge": self.bolge,
                "onizleme": self.blok.metin[:80]}


def bloklara_ayir(text: str, blok_cumle: int = BLOK_CUMLE) -> list[Blok]:
    """Metni ardışık cümle gruplarına böler.

    Belgeler tek satır geldiği için düzen (boş satır/başlık) kullanılamaz;
    `clean.split_sentences` TR kısaltma ve ondalık sayı duyarlıdır.

    Cümleler orijinal metinde SIRAYLA aranır — aynı cümle iki kez geçse bile
    ikinci kopya birincinin konumunu almaz, aksi hâlde silme aralıkları
    çakışırdı.
    """
    cumleler = split_sentences(text or "")
    if not cumleler:
        return []
    bloklar: list[Blok] = []
    imlec = 0
    for i in range(0, len(cumleler), blok_cumle):
        parca = cumleler[i:i + blok_cumle]
        bas = text.find(parca[0], imlec)
        if bas < 0:
            bas = imlec
        son = bas
        for c in parca:
            k = text.find(c, son)
            son = (k + len(c)) if k >= 0 else (son + len(c))
        imlec = son
        bloklar.append(Blok(" ".join(parca), bas, min(son, len(text))))
    return bloklar


def cumle_anahtari(cumle: str) -> str:
    """Cümlenin tekrar karşılaştırması için kanonik anahtarı."""
    return " ".join(re.findall(r"\w+", tr_fold_ascii(cumle)))


def cerceve_cumleler(metinler: Iterable[str], min_docs: int = 3,
                     min_sozcuk: int = 3) -> set[str]:
    """Grup içinde >= `min_docs` BELGEDE geçen cümlelerin anahtar kümesi.

    Neden cümle-DF, neden 8-gram değil: karar birimi cümleye indiğinde
    n-gram kapsaması ölçülemez hale geliyor — cümlelerin çoğu 8 sözcükten
    kısa, dolayısıyla tekrar sinyali SESSİZCE hiç ateşlenmiyordu (ölçüldü:
    eşiği değiştirmek sonucu hiç değiştirmedi). Cümle-DF aynı olguyu doğrudan
    ölçer: menü satırı ve altbilgi cümlesi belgeler arasında BİREBİR tekrar
    eder.

    Çok kısa cümleler (`min_sozcuk` altı) dışarıda: "Detaylı Bilgi", "Başvur"
    gibi parçalar her yerde geçer ve gerçek içeriğin parçası olabilir.
    """
    df: dict[str, int] = {}
    for metin in metinler:
        gorulen = {cumle_anahtari(c) for c in split_sentences(metin or "")}
        for a in gorulen:
            if a and a.count(" ") + 1 >= min_sozcuk:
                df[a] = df.get(a, 0) + 1
    return {a for a, n in df.items() if n >= min_docs}


def kararlar(text: str, cerceve: Optional[set[str]] = None, *,
             terimler: Optional[Iterable[str]] = None,
             yayilim: int = YAYILIM_BLOK) -> list[Karar]:
    """Her blok için tut/sil kararı — öncelik: alan-dışı > sayısal > tekrar."""
    cerceve = cerceve or set()
    cikti: list[Karar] = []
    kalan_yayilim = 0

    for blok in bloklara_ayir(text):
        anti = anti_skoru(blok.metin)
        deger = deger_skoru(blok.metin, terimler)
        sayisal = len(_DEGER_RE.findall(tr_fold_ascii(blok.metin)))
        tekrar = 1.0 if cumle_anahtari(blok.metin) in cerceve else 0.0

        # 1) ALAN-DIŞILIK — en yüksek öncelik, tekrar kanıtı aranmaz.
        if anti:
            kalan_yayilim = yayilim
            cikti.append(Karar(blok, False, "alan_disi", anti, deger, tekrar))
            continue

        # 1b) Bölge yayılımı: işaret cümlelerce önce geçmiş olabilir.
        #     Güçlü alan değeri bölgeyi SÖNDÜRÜR.
        if kalan_yayilim > 0:
            if deger >= SONDURME_DEGERI:
                kalan_yayilim = 0
            else:
                kalan_yayilim -= 1
                cikti.append(Karar(blok, False, "alan_disi_bolge",
                                   anti, deger, tekrar, bolge=True))
                continue

        # 2) SAYISAL DEĞER — tekrarı EZER.
        #
        #    Yalnız sayı+birim bu ayrıcalığı hak ediyor. Ölçüldü: alan
        #    SÖZCÜĞÜ (finansman, kampanya, hesap...) tek başına yeterli
        #    sayılınca menü blokları da kurtuluyor — menüler tam olarak bu
        #    sözcüklerden oluşuyor — ve halüsinasyon geri geliyordu.
        if sayisal > 0:
            cikti.append(Karar(blok, True, "sayisal_deger", anti, deger, tekrar))
            continue

        # 3) TEKRAR — sayısal değer yoksa çerçeve sayılır. Alan sözcüğü
        #    taşısa bile: menü/altbilgi tam da böyle görünür.
        if tekrar > 0:
            cikti.append(Karar(blok, False, "tekrar", anti, deger, tekrar))
            continue

        # 3b) ALAN SÖZCÜĞÜ — tekrar kanıtı YOKKEN korur. Şablonlaşmış ama
        #     tekrar eşiğini geçmeyen gerçek içerik burada kurtulur.
        if deger > 0:
            cikti.append(Karar(blok, True, "alan_sozcugu", anti, deger, tekrar))
            continue

        # 4) Hiçbir sinyal yok -> KORU. Çerçeve olduğunu ispatlayamıyoruz.
        cikti.append(Karar(blok, True, "sinyal_yok", anti, deger, tekrar))

    return cikti


def temizle(text: str, cerceve: Optional[set[str]] = None, *,
            terimler: Optional[Iterable[str]] = None,
            yayilim: int = YAYILIM_BLOK) -> tuple[str, list[Karar]]:
    """(temiz metin, kararlar). Kararlar denetim için birlikte döner."""
    kr = kararlar(text, cerceve, terimler=terimler, yayilim=yayilim)
    tutulan = " ".join(k.blok.metin for k in kr if k.tut)
    return tutulan.strip(), kr


# --------------------------------------------------------------------------- #
# Sunum katmanı — çerçeveyi SİLMEDEN "katlanabilir" işaretle
# --------------------------------------------------------------------------- #
#
# ## Neden silme değil katlama (pazarlıksız kısıt)
#
# `extracted_fields.span_start` / `span_end` offset'leri **HAM metne** göre
# ölçülür ve veri tabanında öyle saklanır (`src/db/repository.py`, sütunlar
# 31 Tem 2026'da tam bu sebeple eklendi). Çerçeveyi metinden SİLMEK bu
# offset'lerin tamamını kaydırır ve projenin en özgün iddiası — her çıkarılan
# değerin ham metinde bir karakter aralığına bağlı olması (CLAUDE.md §18
# yenilikçilik hedefi #1) — sessizce çöker.
#
# Bu yüzden çerçeve ayıklaması ÇIKARIM yolundan alınıp SUNUM katmanına
# taşındı: metin değişmez, yalnızca hangi karakter aralığının arayüzde
# katlanacağı bildirilir. `kararlar()`'ın karar mantığına dokunulmaz; burası
# yalnızca bir OKUMA yoludur.
#
# ## Kapsama garantisi
#
# Dönen aralıklar ham metni **eksiksiz ve bitişik** kaplar:
#
#     araliklar[0].start == 0
#     araliklar[i].end   == araliklar[i+1].start      (boşluk ve örtüşme yok)
#     araliklar[-1].end  == len(text)
#     "".join(text[a.start:a.end] for a in araliklar) == text
#
# Bu garanti şart, çünkü arayüz metni aralıklardan yeniden birleştiriyor.
# `bloklara_ayir()` tek başına bunu VERMEZ: cümle segmentasyonu
# `normalize_whitespace()`'ten geçtiği için cümleler arası ayırıcılar blok
# aralıklarının dışında kalır ve bir cümle ham metinde hiç bulunamazsa blok
# kayabilir. Aradaki boşluklar burada açıkça doldurulur.

#: Gizleme gerekçeleri — `kararlar()`'ın ürettiği adların gizleyen alt kümesi.
#: Arayüz bu değerleri kullanıcıya çevirir; buraya yeni ad UYDURULMAZ.
GIZLEME_GEREKCELERI: tuple[str, ...] = ("alan_disi", "alan_disi_bolge", "tekrar")


@dataclass(frozen=True)
class Aralik:
    """Ham metnin bir karakter aralığı ve arayüzde katlanıp katlanmayacağı.

    `gerekce` yalnızca `gizle=True` iken doludur ve `kararlar()`'ın kendi
    gerekçe adıdır (`alan_disi`, `alan_disi_bolge`, `tekrar`). Gösterilen
    aralıklarda `None`'dır: "neden gizlendi" sorusunun cevabı yoktur.
    """

    start: int
    end: int
    gizle: bool
    gerekce: Optional[str]

    def as_dict(self) -> dict:
        return {"start": self.start, "end": self.end,
                "gizle": self.gizle, "gerekce": self.gerekce}


def _sigdir(text: str, kr: list[Karar]) -> list[tuple[int, int, bool, Optional[str]]]:
    """Karar bloklarını metne sığdırılmış, monoton, örtüşmeyen aralıklara indirger.

    `bloklara_ayir()` imleci ileri taşıdığı için aralıklar zaten artan sırada
    gelir; yine de savunmacı davranılır: bir cümle ham metinde bulunamazsa
    (`find` -1) blok imlece düşer ve sınırlar metin dışına taşabilir. Kapsama
    garantisi buradaki kırpmaya dayanıyor, varsayıma değil.
    """
    n = len(text)
    out: list[tuple[int, int, bool, Optional[str]]] = []
    imlec = 0
    for k in kr:
        bas = max(imlec, min(k.blok.bas, n))
        son = max(bas, min(k.blok.son, n))
        if son <= bas:
            continue  # boş ya da tamamen kaymış blok — kapsamı bozmasın
        out.append((bas, son, not k.tut, k.gerekce if not k.tut else None))
        imlec = son
    return out


def gorunum_araliklari(text: str, cerceve: Optional[set[str]] = None, *,
                       terimler: Optional[Iterable[str]] = None,
                       yayilim: int = YAYILIM_BLOK) -> list[Aralik]:
    """Ham metni eksiksiz kaplayan görünürlük aralıkları (silme YOK).

    Blok aralıkları arasında kalan boşluklar iki kuraldan biriyle sahiplenilir:

    * Boşluk yalnızca beyaz karakterden ibaretse ve İKİ yanındaki aralık aynı
      kararı taşıyorsa, o kararı devralır. Aksi hâlde `BLOK_CUMLE = 1` olduğu
      için gizlenen her bölge cümleler arası boşluklarla onlarca parçaya
      bölünürdü.
    * Diğer her durumda **gösterilir**. Sınıflandırılamayan metni gizlemek,
      `kararlar()`'ın "sinyal yok -> KORU" ilkesini sunum katmanında delmek
      olurdu: çerçeve olduğunu ispatlayamadığımız şeyi saklamayız.

    Ardışık ve aynı kararlı aralıklar birleştirilir; farklı gerekçeler
    (`alan_disi` ile `alan_disi_bolge`) denetlenebilirlik için ayrı kalır.
    """
    text = text or ""
    n = len(text)
    if n == 0:
        return []

    kr = kararlar(text, cerceve, terimler=terimler, yayilim=yayilim)

    # 1) Boşlukları `gizle=None` (sahipsiz) işaretiyle araya serp.
    ham: list[tuple[int, int, Optional[bool], Optional[str]]] = []
    imlec = 0
    for bas, son, gizle, gerekce in _sigdir(text, kr):
        if bas > imlec:
            ham.append((imlec, bas, None, None))
        ham.append((bas, son, gizle, gerekce))
        imlec = son
    if imlec < n:
        ham.append((imlec, n, None, None))
    if not ham:  # hiç karar üretilmedi (ör. cümle bulunamadı) — metnin tamamı görünür
        ham.append((0, n, False, None))

    # 2) Sahipsiz boşlukları çöz.
    cozulmus: list[tuple[int, int, bool, Optional[str]]] = []
    for i, (bas, son, gizle, gerekce) in enumerate(ham):
        if gizle is not None:
            cozulmus.append((bas, son, gizle, gerekce))
            continue
        onceki = cozulmus[-1] if cozulmus else None
        sonraki = next((h for h in ham[i + 1:] if h[2] is not None), None)
        if (not text[bas:son].strip() and onceki is not None and sonraki is not None
                and onceki[2] == sonraki[2] and onceki[3] == sonraki[3]):
            cozulmus.append((bas, son, onceki[2], onceki[3]))
        else:
            cozulmus.append((bas, son, False, None))

    # 3) Ardışık aynı kararları birleştir.
    birlesik: list[Aralik] = []
    for bas, son, gizle, gerekce in cozulmus:
        if (birlesik and birlesik[-1].end == bas
                and birlesik[-1].gizle == gizle
                and birlesik[-1].gerekce == gerekce):
            onceki_a = birlesik.pop()
            birlesik.append(Aralik(onceki_a.start, son, gizle, gerekce))
        else:
            birlesik.append(Aralik(bas, son, gizle, gerekce))
    return birlesik


def gorunur_metin(text: str, cerceve: Optional[set[str]] = None, *,
                  terimler: Optional[Iterable[str]] = None,
                  yayilim: int = YAYILIM_BLOK) -> str:
    """Katlanmış metin: arayüzde GÖRÜNEN aralıkların birleşimi.

    `temizle()` ile aynı kararlara dayanır ama parçaları ham metinden keser,
    yeniden birleştirmez — yani kullanıcının panelde gördüğü metnin birebir
    aynısıdır. Özet üretimi bunu kullanır: modele giden metin ile kullanıcıya
    gösterilen metin ayrışırsa, özet ekranda olmayan bir cümleyi anlatabilir.
    """
    text = text or ""
    return "".join(text[a.start:a.end]
                   for a in gorunum_araliklari(text, cerceve, terimler=terimler,
                                               yayilim=yayilim)
                   if not a.gizle).strip()
