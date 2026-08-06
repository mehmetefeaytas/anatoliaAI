"""Çerçeve (boilerplate) ayıklamasının YARIŞMA korpusundaki kapsam denetimi.

İlgili: scripts/split_trainable.py (mekanizmanın kendisi)
        docs/rapor/boilerplate-kapsam.md (bu betiğin ürettiği karar raporu)
        docs/yapilacaklar-envanteri.md T-019 (chatbot alakasız içerik döndürüyor)

## Bu betik neden var

`split_trainable.py` çerçeve ayıklamasını `data/raw-classic` (yarışma DIŞI
gümüş eğitim verisi) için koşuyor. Yarışma korpusu `data/raw/` bu geçişten
HİÇ geçmiyor. Mekanizmayı oraya taşımadan önce üç sorunun sayıyla
cevaplanması gerekiyor ve bu betik yalnız onu yapar — **hiçbir şeyi
değiştirmez, yalnız ölçer**:

1. **Kim ne kaybediyor?** Ayıklama sonrası içeriğinin çoğunu yitiren belgeler
   gerçekten çerçeveden mi ibaretti, yoksa mekanizma gerçek içeriği mi yedi?
   Ölçüt "kaç karakter gitti" DEĞİL — kural katmanının (`extract_all`)
   çıkarabildiği KANONİK ALANLARDAN hangileri kayboldu. Karakter sayısı
   yanıltıcıdır: 9 KB'lık bir Dünya Katılım sayfasının 8,7 KB'ı çerez/KVKK
   metnidir ve gitmesi DOĞRUDUR.

2. **Gruplama ne olmalı?** Çerçeve "aynı grup içinde ≥N belgede geçen n-gram"
   diye tanımlı; grubun tanımı sonucu belirler. Şablon banka içinde bile
   değişiyor (Kuveyt Türk `saglamkart.` / `milesandsmiles.` alt alan adları,
   Türkiye Finans `happycard.com.tr`, Albaraka `albarakaozel.com`), yani
   "banka" tek başına yanlış grup olabilir.

3. **Noktalama ikinci sinyal olarak ne katıyor?** Gerçek kampanya metni
   noktalı ve cümle yapılıdır; menü/liste bloklarında nokta-virgül yoktur.

## Ölçülen üç büyüklük (hepsi aynı anda raporlanır)

- **çerçeve kazancı**: atılan karakterin toplam karaktere oranı. TEK BAŞINA
  ANLAMSIZDIR — her şeyi atmak %100 kazanç verir.
- **zararlı kayıp**: ham metinden çıkarılabilen bir kanonik alan çekirdekte
  kayboldu VE alanın kaynak konumu krom (çerez/KVKK/menü/çapraz kampanya)
  değildi. Mekanizmanın gerçek maliyeti budur.
- **krom sızıntısı**: çekirdekte hâlâ çerez/KVKK/footer işaretçisi taşıyan
  belge sayısı. Ayıklamanın işini yapmadığı yer.

Üçü birlikte olmadan karar verilemez: kazanç ↑ / zararlı kayıp ↑ bir takas,
kazanç ↑ / sızıntı ↓ / zararlı kayıp sabit ise saf iyileşmedir.
"""

from __future__ import annotations

import argparse
import bisect
import collections
import json
import math
import os
import re
import sys
import zlib
from dataclasses import dataclass, field
from typing import Callable, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.split_trainable import (
    _WORD_RE,
    BOILERPLATE_MIN_DOCS,
    SHINGLE_SIZE,
    SIGNAL_CONTEXT_WORDS,
    SIGNAL_MIN_FRACTION,
    Doc,
    core_text,
    has_financial_signal,
    iter_docs,
)
from src.extraction.rules.extract import extract_all
from src.preprocessing.clean import tr_fold, tr_fold_ascii

# --------------------------------------------------------------------------
# NOKTALAMA SİNYALİ — eşikler ölçümle seçildi (docs/rapor/boilerplate-kapsam.md)
# --------------------------------------------------------------------------

# Düzyazı testinin uygulandığı bloğun yarıçapı (n-gramın iki yanına eklenen
# sözcük sayısı).
#
# NEDEN 8-GRAM PENCERESİ YETMİYOR: ortalama cümle uzunluğu 8+2+2=12 sözcüklük
# bir pencerede TANIM GEREĞİ 12 ile sınırlıdır — menü (0 cümle sonu → 12) ile
# düzyazı (1 cümle sonu → 12) aynı değeri verir, sinyal saturasyona girer.
# ±24 sözcük (toplam ~56) menüde 0-1, düzyazıda 4-7 cümle sonu görür.
PROSE_BLOCK_WORDS = 24

# Bloğun düzyazı sayılması için sözcük başına asgari noktalama.
#
# ÖLÇÜM (data/raw, 250 belgelik rastgele örneklem, 5302 blok; krom işaretçisi
# taşıyan blok = KROM, kalanı = İÇERİK):
#
#     grup     n      noktalama/sözcük            cümlesiz blok
#              -      p10     medyan   p90        oranı
#     KROM     495    0,020   0,102    0,163      %16
#     İÇERİK  4807    0,041   0,122    0,184      %16
#
# **BULGU — sinyal beklenenden ZAYIF.** Mentörün öncülü ("menüde nokta-virgül
# yok") menüler için doğru, ama `data/raw` kromunun HACİMCE ağırlığı menü
# değil ÇEREZ/KVKK METNİ ve o metin tam anlamıyla düzyazıdır (medyan 0,102).
# Ayrım gücü bu yüzden düşük: 0,04 eşiği içerik bloklarının %90'ını korurken
# krom bloklarının ancak %18'ini eliyor. Sinyal yine de tek yönlü faydalı —
# menü/liste kromunu (`hedef_kitle = "Emeklilik"` gibi halüsinasyonların
# kaynağı) kesiyor. Karar bu sinyale TEK BAŞINA dayandırılamaz.
PROSE_MIN_PUNCT_RATIO = 0.04

# Bloğun düzyazı sayılması için azami ortalama cümle uzunluğu (sözcük).
#
# ÖLÇÜM: dağılım İKİ TEPELİ — blokta cümle sonu varsa ortalama 7-16 sözcük,
# yoksa ortalama blok boyuna (≈49) eşitleniyor; arada gözlem yok. Bu yüzden
# 20 ile 40 arasındaki her eşik AYNI sonucu veriyor (ölçülen: %83,8 / %84,3).
# 30 seçildi çünkü iki tepenin ortasında duruyor ve dağılım değişirse
# (uzun cümleli sözleşme metinleri) hangi tarafa kaydığı görünür.
PROSE_MAX_SENTENCE_WORDS = 30

_PUNCT_RE = re.compile(r"[.,;:!?]")
_SENTENCE_END_RE = re.compile(r"[.!?]")

# --------------------------------------------------------------------------
# ŞABLON İMZASI (MinHash + LSH) — gruplama alternatifi
# --------------------------------------------------------------------------

# MinHash imza uzunluğu ve bant düzeni.
#
# 16 hash / 8 bant x 2 satır → yakalama eşiği ≈ (1/8)^(1/2) = 0,35 Jaccard.
# NEDEN DÜŞÜK EŞİK: şablon kardeşleri gövdeleri farklı olduğu için Jaccard'ı
# 0,4-0,6 bandında kalıyor; 4 bant x 4 satır (eşik 0,71) yalnız NEREDEYSE
# AYNI belgeleri kümeleyip şablon kümelerini 1-2 üyeye düşürüyordu ve
# `BOILERPLATE_MIN_DOCS`ın altında kalan küme hiç ayıklanmıyordu.
SIGNATURE_HASHES = 16
SIGNATURE_BANDS = 8
_MERSENNE = (1 << 61) - 1

# Yerelleştirme yol parçaları — URL öneki gruplamasında ATLANIR.
# Albaraka'nın tüm yolları `/tr/...`, Türkiye Finans'ınkiler `/tr-tr/...` ile
# başlıyor; bu parça hiçbir şeyi ayırmadığı için önek olarak alınırsa
# `banka-bolum-yol` gruplaması `banka-bolum`e ÇÖKER.
LOCALE_SEGMENTS: frozenset[str] = frozenset({
    "tr", "tr-tr", "en", "en-us", "en-gb", "ar", "de",
})

# --------------------------------------------------------------------------
# KAYIP TÜRÜ İŞARETÇİLERİ — bir alanın kaybı zararlı mı, temizlik mi?
# --------------------------------------------------------------------------

# ÇEREZ / KVKK / footer bloğu. Bu bloktan çıkarılan alan HALÜSİNASYONDUR:
# ölçülmüş örnekler (data/raw, 2026-08-07):
#   vade_ay = "1 yıl"   <- "...toplamak amacıyla kullanılan çerezdir. 1 yıl"
#   masraf_durumu = "ücretsiz" <- "...otuz (30) gün içinde ücretsiz olarak
#                                  sonuçlandırılmaktadır" (KVKK başvuru metni)
# Bu alanların ÇEKİRDEKTE KAYBOLMASI kazançtır, kayıp değil.
CHROME_MARKERS: tuple[str, ...] = (
    "cerez", "kisisel veri", "aydinlatma metni", "kvkk", "gizlilik politikasi",
    "veri sorumlusu", "acik riza", "tum haklari saklidir", "site haritasi",
    "kanunu kapsaminda", "tarayicinizi", "web sitemizde",
)

# ÇAPRAZ KAMPANYA bloğu — sayfanın kendi kampanyası DEĞİL, kenar çubuğundaki
# BAŞKA kampanyaların adı/tarihi/indirimi. T-019'un ta kendisi: konut
# finansmanı sorgusunda "POS hizmetleri" dönmesinin kaynağı.
# Ölçülmüş örnek: `vakif-katilim--detay-troy-kredi-karti-ile-lcw-hediye-ceki`
# belgesinden indirim_orani=%15 çıkıyor ama %15 KOMŞU kampanyanın
# ("English Home'da %15 İndirim!") oranı.
CROSS_CAMPAIGN_MARKERS: tuple[str, ...] = (
    "diger kampanyalar", "tum kampanyalar", "benzer kampanyalar",
    "diger firsatlar", "sona erdi bitis tarihi",
)

# BLOG BAŞLIK LİSTESİ — sayfanın kendi metni değil, kenar çubuğundaki eğitici
# yazı başlıklarının arka arkaya dizilmiş hali. Düzyazı testini SORU
# İŞARETLERİYLE geçiyor ama cümle değil, başlık dizisi.
# Ölçülmüş örnek (`turkiye-finans--altin-urunleri-default`):
#   "...Katılma Hesabı Nedir, Nasıl Açılır? Sürdürülebilir Bir Geleceğin
#    Anahtarı: Net Sıfır Hedefi Tüm Renkleri Buluşturan Güzellikleriyle Hoş
#    Geldin Ramazan! İşsizlik Maaşı (İşsizlik Ödeneği) Nedir?..."
# Buradan çıkan `hedef_kitle = "Hoş Geldin"` HALÜSİNASYONDUR; kaybı kazançtır.
TITLE_LIST_MIN_QUESTIONS = 2

# Kayıp sınıflandırmasında alanın kaynak konumunun iki yanına bakılan karakter.
# 180: ölçülen çerez cümlelerinin ("...çerezdir. 1 yıl 5.Kişisel Veri Sahibi
# Olarak Haklarınız") işaretçiye uzaklığı en fazla 120 karakterdi.
LOSS_CONTEXT_CHARS = 180

ROOT_SECTION = "(kok)"

GROUPINGS: tuple[str, ...] = (
    "banka", "banka-bolum", "banka-bolum-konak", "banka-bolum-yol",
    "sablon-imzasi",
)
PUNCTUATION_MODES: tuple[str, ...] = ("kapali", "dar", "genis")

# İçeriğinin bu orandan azını koruyan belge "düşen belge" sayılır — teşhis
# listesinin girdi filtresi. Karar ölçütü DEĞİL (karar `zararli_kayip`).
DROP_RATIO = 0.25


# --------------------------------------------------------------------------
# Bölüm / URL yardımcıları
# --------------------------------------------------------------------------

def section_of(rel_path: str) -> str:
    """Belgenin bölümü: `<banka>/<bolum>/...` yolundaki ikinci parça.

    Bölüm bir toplama kanalıdır (`live` canlı kampanya, `products` ürün
    sayfası, `docs` PDF/sözleşme, `archive` arşiv) ve şablonu belirler:
    aynı bankanın `docs` PDF'i ile `live` HTML sayfası ortak tek bir n-gram
    bile paylaşmaz. Kökte duran belgeler için `(kok)`.
    """
    parts = rel_path.split(os.sep)
    return parts[1] if len(parts) > 2 else ROOT_SECTION


def _host(url: Optional[str]) -> str:
    """URL'nin alan adı (port ve şema atılmış, küçük harf).

    Port kasten atılıyor: korpusta `www.turkiyefinans.com.tr` ve
    `www.turkiyefinans.com.tr:443` aynı siteyi gösteren 2 ayrı ad olarak
    geliyor ve ayrı grup sayılırlarsa 7 belge tek başına kalıp hiç
    ayıklanmıyor.
    """
    if not url:
        return ""
    host = re.sub(r"^[a-zA-Z]+://", "", url).split("/", 1)[0]
    return host.split(":", 1)[0].lower()


def url_prefix(url: Optional[str]) -> str:
    """URL yolunun ilk ANLAMLI parçası (yerelleştirme parçaları atlanır)."""
    if not url:
        return ""
    path = re.sub(r"^[a-zA-Z]+://[^/]*", "", url)
    path = path.split("?", 1)[0].split("#", 1)[0]
    for seg in path.split("/"):
        if not seg:
            continue
        folded = tr_fold_ascii(seg)
        if folded in LOCALE_SEGMENTS:
            continue
        return folded
    return ""


# --------------------------------------------------------------------------
# Noktalama sinyali
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class ProseStats:
    """Bir metin bloğunun düzyazı ölçümleri."""

    words: int
    punct_per_word: float
    mean_sentence_words: float
    sentences: int = 0

    @property
    def is_prose(self) -> bool:
        """Blok cümle yapılı mı? (menü/liste değil)

        EN AZ BİR CÜMLE koşulu ayrı duruyor, ortalama uzunluk eşiğine
        gömülmüyor: cümlesiz kısa bir blokta (`words < 30`) ortalama uzunluk
        eşiğin altında kalır ve virgülle ayrılmış menü listesi ("Krediler,
        Kartlar, Mevduat, Sigorta, ...") düzyazı sayılırdı. Cümle sayısı
        koşulu blok boyundan bağımsızdır.
        """
        return (self.punct_per_word >= PROSE_MIN_PUNCT_RATIO
                and self.sentences >= 1
                and self.mean_sentence_words <= PROSE_MAX_SENTENCE_WORDS)


def prose_stats(block: str) -> ProseStats:
    """Blok başına noktalama oranı + ortalama cümle uzunluğu + cümle sayısı.

    Ortalama cümle uzunluğu = sözcük / cümle sonu işareti. Cümle sonu YOKSA
    bölen 1 alınır, yani blok tek bir "cümle" sayılır ve uzunluk blok boyuna
    eşitlenir — ölçülen iki tepeli dağılımın üst tepesi budur.
    """
    words = len(_WORD_RE.findall(block))
    if not words:
        return ProseStats(0, 0.0, 0.0, 0)
    punct = len(_PUNCT_RE.findall(block))
    ends = len(_SENTENCE_END_RE.findall(block))
    return ProseStats(words, punct / words, words / max(1, ends), ends)


# --------------------------------------------------------------------------
# Genişletilmiş n-gram indeksi (sinyal + düzyazı)
# --------------------------------------------------------------------------

def _prefix_positions(text: str, pattern: re.Pattern[str]) -> list[int]:
    """Desenin metindeki karakter konumları (artan)."""
    return [m.start() for m in pattern.finditer(text)]


def _count_between(positions: list[int], lo: int, hi: int) -> int:
    """`positions` içinde [lo, hi) aralığına düşen konum sayısı."""
    return bisect.bisect_left(positions, hi) - bisect.bisect_left(positions, lo)


def shingle_index(texts: list[str], size: int = SHINGLE_SIZE,
                  ) -> tuple[collections.Counter[str], set[str], set[str]]:
    """(n-gram -> belge frekansı, sinyalli gramlar, DÜZYAZI gramlar).

    `split_trainable._shingle_index`in üstüne yalnız üçüncü kümeyi ekler;
    sinyal hesabı birebir aynı tutuldu (aynı pencere, aynı bağlam payı), aksi
    hâlde iki hattın ölçümleri karşılaştırılamazdı.

    Düzyazı testi `PROSE_BLOCK_WORDS` yarıçaplı GENİŞ blokta yapılır ve
    noktalama sayımı ham metin üzerinde önek dizileriyle (bisect) yapılır —
    gram başına blok dilimlemek 1,3 milyon gramda kabul edilemez yavaştı.
    """
    df: collections.Counter[str] = collections.Counter()
    signal: set[str] = set()
    prose: set[str] = set()
    pad = SIGNAL_CONTEXT_WORDS
    wide = PROSE_BLOCK_WORDS
    for text in texts:
        spans = [m.span() for m in _WORD_RE.finditer(text)]
        if not spans:
            continue
        folded = [tr_fold(text[a:b]) for a, b in spans]
        puncts = _prefix_positions(text, _PUNCT_RE)
        ends = _prefix_positions(text, _SENTENCE_END_RE)
        last = len(spans) - 1
        seen: set[str] = set()
        for i in range(max(0, len(folded) - size + 1)):
            gram = " ".join(folded[i:i + size])
            if gram in seen:
                continue
            seen.add(gram)
            if gram not in signal:
                lo = spans[max(0, i - pad)][0]
                hi = spans[min(last, i + size - 1 + pad)][1]
                if has_financial_signal(text[lo:hi]):
                    signal.add(gram)
            if gram not in prose:
                wlo_i = max(0, i - wide)
                whi_i = min(last, i + size - 1 + wide)
                wlo, whi = spans[wlo_i][0], spans[whi_i][1]
                words = whi_i - wlo_i + 1
                n_punct = _count_between(puncts, wlo, whi)
                n_end = _count_between(ends, wlo, whi)
                stats = ProseStats(words, n_punct / words,
                                   words / max(1, n_end), n_end)
                if stats.is_prose:
                    prose.add(gram)
        df.update(seen)
    return df, signal, prose


def boilerplate_sets_ext(texts: list[str],
                         min_docs: int = BOILERPLATE_MIN_DOCS,
                         size: int = SHINGLE_SIZE,
                         signal_min_fraction: float = SIGNAL_MIN_FRACTION,
                         punctuation: str = "kapali",
                         ) -> tuple[set[str], set[str]]:
    """(çerçeve gramları, korunan gramlar) — noktalama kipi seçilebilir.

    `punctuation` kipleri:

    - `kapali`: `split_trainable.boilerplate_sets` ile BİREBİR aynı. Referans
      hat; başka bir kip ölçülürken karşılaştırma tabanı budur.
    - `dar`: koruma DARALIR — bir gram korunmak için hem finansal sinyal
      taşımalı hem DÜZYAZI olmalı. Hedef: kromun sinyalli ama cümlesiz
      parçalarının ("Taksitli Nakit Avans Vadeli Mevduat" menü öğeleri)
      korumaya sığınıp çekirdeğe sızmasını kesmek.
    - `genis`: koruma GENİŞLER — sinyal VEYA düzyazı olan gram oran eşiğine
      tabi olur. Hedef: kampanya şablonu kardeşlerinin ORTAK KOŞUL METNİNİ
      (Albaraka'nın 5 "World'e özel N taksit" kardeşi) kurtarmak; bu metinde
      sayı yoktur, dolayısıyla `SIGNAL_MIN_FRACTION` koruması onu görmez.
      Çerez/KVKK bloğu da düzyazıdır ama belgelerin %100'ünde geçtiği için
      oran eşiğinin ÜSTÜNDE kalır ve çerçeve sayılmaya devam eder.
    """
    if punctuation not in PUNCTUATION_MODES:
        raise ValueError(f"bilinmeyen noktalama kipi: {punctuation}")
    if len(texts) < min_docs:
        return set(), set()
    df, signal, prose = shingle_index(texts, size)
    threshold = max(min_docs, math.ceil(signal_min_fraction * len(texts)))
    boiler: set[str] = set()
    protected: set[str] = set()
    for gram, n in df.items():
        if n < min_docs:
            continue
        if punctuation == "kapali":
            eligible = gram in signal
        elif punctuation == "dar":
            eligible = gram in signal and gram in prose
        else:
            eligible = gram in signal or gram in prose
        if eligible and n < threshold:
            protected.add(gram)
        else:
            boiler.add(gram)
    return boiler, protected


# --------------------------------------------------------------------------
# Gruplama
# --------------------------------------------------------------------------

def _minhash(text: str, size: int = SHINGLE_SIZE) -> tuple[int, ...]:
    """Belgenin n-gram kümesinin MinHash imzası.

    crc32 kasten seçildi: `hash()` PYTHONHASHSEED'e bağlıdır ve aynı korpusta
    iki koşu farklı küme üretirdi — ölçüm tekrarlanabilir olmalı.
    """
    spans = [m.span() for m in _WORD_RE.finditer(text)]
    folded = [tr_fold(text[a:b]) for a, b in spans]
    mins = [_MERSENNE] * SIGNATURE_HASHES
    seen: set[str] = set()
    for i in range(max(0, len(folded) - size + 1)):
        gram = " ".join(folded[i:i + size])
        if gram in seen:
            continue
        seen.add(gram)
        h = zlib.crc32(gram.encode("utf-8"))
        for k in range(SIGNATURE_HASHES):
            v = ((2 * k + 1) * h + (k + 1) * 7919) % _MERSENNE
            if v < mins[k]:
                mins[k] = v
    return tuple(mins)


class _UnionFind:
    """Küme birleştirme — LSH bant kovaları belgeleri kümelere bağlar."""

    def __init__(self) -> None:
        self.parent: dict[str, str] = {}

    def find(self, x: str) -> str:
        self.parent.setdefault(x, x)
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, a: str, b: str) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[rb] = ra


def _signature_groups(docs: list[Doc]) -> dict[str, list[Doc]]:
    """Belgeleri şablon imzasına göre kümele (banka İÇİNDE).

    Banka sınırı korunuyor: iki farklı bankanın sayfaları rastlantısal olarak
    aynı bant kovasına düşerse birinin menüsü diğerinin içeriğini silerdi ve
    bu hata provenance'ta görünmezdi.
    """
    uf = _UnionFind()
    buckets: dict[tuple[str, int, tuple[int, ...]], list[str]] = (
        collections.defaultdict(list))
    rows = SIGNATURE_HASHES // SIGNATURE_BANDS
    by_id = {d.doc_id: d for d in docs}
    for doc in docs:
        uf.find(doc.doc_id)
        sig = _minhash(doc.text)
        for band in range(SIGNATURE_BANDS):
            key = (doc.bank, band, sig[band * rows:(band + 1) * rows])
            buckets[key].append(doc.doc_id)
    for members in buckets.values():
        first = members[0]
        for other in members[1:]:
            uf.union(first, other)
    groups: dict[str, list[Doc]] = collections.defaultdict(list)
    for doc_id in sorted(by_id):
        groups[uf.find(doc_id)].append(by_id[doc_id])
    return dict(groups)


def _key_bank(doc: Doc) -> str:
    return doc.bank


def _key_bank_section(doc: Doc) -> str:
    return f"{doc.bank}/{section_of(doc.rel_path)}"


def _key_bank_section_path(doc: Doc) -> str:
    return (f"{doc.bank}/{section_of(doc.rel_path)}"
            f"/{_host(doc.source_url)}/{url_prefix(doc.source_url)}")


_KEY_FUNCS: dict[str, Callable[[Doc], str]] = {
    "banka": _key_bank,
    "banka-bolum": _key_bank_section,
    "banka-bolum-yol": _key_bank_section_path,
}


def _host_aware_groups(docs: list[Doc]) -> dict[str, list[Doc]]:
    """(banka, bölüm) — ama alan adı KENDİ ŞABLONUNU besleyecek kadar büyükse ayrı.

    NEDEN MELEZ: `banka-bolum-yol` alt alan adlarını doğru ayırıyor (ölçüm: 41
    alt alan adı belgesinde çerçeve %32,7 → %43,1) ama URL yol önekini de
    anahtara kattığı için ana siteyi 104 küçük gruba bölüyor ve TOPLAM kazanç
    düşüyor. Bu strateji yalnız ALAN ADINI ayırır ve eşiğin altında kalan alan
    adlarını (`BOILERPLATE_MIN_DOCS`) ana kovaya geri düşürür: küçük grup
    çerçeve üretemez, ürettiği tek şey ölçülmemiş bir boşluktur.
    """
    counts: collections.Counter[str] = collections.Counter()
    for doc in docs:
        counts[f"{_key_bank_section(doc)}/{_host(doc.source_url)}"] += 1
    groups: dict[str, list[Doc]] = collections.defaultdict(list)
    for doc in docs:
        base = _key_bank_section(doc)
        keyed = f"{base}/{_host(doc.source_url)}"
        groups[keyed if counts[keyed] >= BOILERPLATE_MIN_DOCS else base
               ].append(doc)
    return dict(groups)


def group_docs(docs: list[Doc], strategy: str) -> dict[str, list[Doc]]:
    """Belgeleri seçilen stratejiye göre gruplara böler."""
    if strategy == "sablon-imzasi":
        return _signature_groups(docs)
    if strategy == "banka-bolum-konak":
        return _host_aware_groups(docs)
    keyfn = _KEY_FUNCS.get(strategy)
    if keyfn is None:
        raise ValueError(f"bilinmeyen gruplama: {strategy}")
    groups: dict[str, list[Doc]] = collections.defaultdict(list)
    for doc in docs:
        groups[keyfn(doc)].append(doc)
    return dict(groups)


# --------------------------------------------------------------------------
# Kayıp sınıflandırması
# --------------------------------------------------------------------------

LOSS_CHROME = "krom"
LOSS_MENU = "menu"
LOSS_TITLES = "baslik-listesi"
LOSS_CROSS = "capraz"
LOSS_REAL = "gercek"
LOSS_KINDS: tuple[str, ...] = (
    LOSS_CHROME, LOSS_MENU, LOSS_TITLES, LOSS_CROSS, LOSS_REAL,
)


def classify_loss(text: str, start: Optional[int], end: Optional[int]) -> str:
    """Kaybolan alanın KAYNAK KONUMUNA bakarak kayıp türünü söyler.

    Sıra kasıtlı: çerez/KVKK bloğu en kesin işaretçidir; menü testi
    (noktalama) yapısaldır ve işaretçi listesi tutmaz; başlık listesi menüden
    yalnız soru işaretiyle ayrılır; çapraz kampanya bloğu en gevşek olduğu
    için sona bırakıldı. Offset yoksa kayıp `gercek` sayılır — bilinmeyeni
    lehimize yazmıyoruz.

    `gercek` dönen her kayıp GERÇEKTEN zararlı demek DEĞİLDİR; bu sınıflandırma
    bir TARAMA aracıdır ve kalan kovanın elle okunması gerekir (ölçülen hata
    payı: docs/rapor/boilerplate-kapsam.md §2). Karar ölçütü gold'daki P/R/F1.
    """
    if start is None or end is None:
        return LOSS_REAL
    lo = max(0, start - LOSS_CONTEXT_CHARS)
    hi = min(len(text), end + LOSS_CONTEXT_CHARS)
    block = text[lo:hi]
    folded = tr_fold_ascii(block)
    for marker in CHROME_MARKERS:
        if marker in folded:
            return LOSS_CHROME
    if not prose_stats(block).is_prose:
        return LOSS_MENU
    if block.count("?") >= TITLE_LIST_MIN_QUESTIONS and "." not in block:
        return LOSS_TITLES
    for marker in CROSS_CAMPAIGN_MARKERS:
        if marker in folded:
            return LOSS_CROSS
    return LOSS_REAL


# --------------------------------------------------------------------------
# Denetim
# --------------------------------------------------------------------------

@dataclass
class DocAudit:
    """Tek belgenin ayıklama öncesi/sonrası ölçümü."""

    doc_id: str
    bank: str
    section: str
    group: str
    raw_chars: int
    core_chars: int
    has_signal: bool = False
    lost_fields: dict[str, str] = field(default_factory=dict)
    changed_fields: list[str] = field(default_factory=list)
    chrome_leak: bool = False

    @property
    def keep_ratio(self) -> float:
        return self.core_chars / self.raw_chars if self.raw_chars else 0.0

    @property
    def harmful(self) -> list[str]:
        """Krom OLMAYAN kayıplar — mekanizmanın gerçek maliyeti."""
        return sorted(n for n, kind in self.lost_fields.items()
                      if kind == LOSS_REAL)


@dataclass
class RunResult:
    """Bir (gruplama, noktalama) yapılandırmasının tüm korpus ölçümü."""

    grouping: str
    punctuation: str
    groups: int
    small_groups: int
    raw_chars: int
    core_chars: int
    docs: list[DocAudit]

    @property
    def boiler_ratio(self) -> float:
        if not self.raw_chars:
            return 0.0
        return 1.0 - self.core_chars / self.raw_chars

    @property
    def dropped(self) -> list[DocAudit]:
        """İçeriğinin %75'inden fazlasını yitiren, finansal sinyalli belgeler.

        Finansal sinyal koşulu şart: sinyalsiz bir belgenin (saf menü sayfası)
        %95 küçülmesi mekanizmanın BAŞARISIDIR, alarm değil.
        """
        return [d for d in self.docs
                if d.has_signal and d.keep_ratio < DROP_RATIO]

    @property
    def harmful_docs(self) -> list[DocAudit]:
        return [d for d in self.docs if d.harmful]

    @property
    def chrome_leaks(self) -> int:
        return sum(1 for d in self.docs if d.chrome_leak)


def _has_chrome(text: str) -> bool:
    folded = tr_fold_ascii(text)
    return any(m in folded for m in CHROME_MARKERS)


def audit(docs: list[Doc], grouping: str, punctuation: str,
          fields: bool = True) -> RunResult:
    """Korpusu bir yapılandırmayla ayıkla ve ölç (HİÇBİR ŞEY YAZILMAZ)."""
    groups = group_docs(docs, grouping)
    audits: list[DocAudit] = []
    raw_total = core_total = 0
    small = 0
    for name, members in sorted(groups.items()):
        if len(members) < BOILERPLATE_MIN_DOCS:
            small += 1
        boiler, protected = boilerplate_sets_ext(
            [d.text for d in members], punctuation=punctuation)
        for doc in members:
            core = core_text(doc.text, boiler, protected)
            raw_total += len(doc.text)
            core_total += len(core)
            entry = DocAudit(
                doc_id=doc.doc_id, bank=doc.bank,
                section=section_of(doc.rel_path), group=name,
                raw_chars=len(doc.text), core_chars=len(core),
                has_signal=has_financial_signal(doc.text),
                chrome_leak=_has_chrome(core))
            if fields:
                before = {f.field_name: f for f in extract_all(doc.text)}
                after = {f.field_name: f for f in extract_all(core)}
                for fname, fobj in before.items():
                    if fname not in after:
                        entry.lost_fields[fname] = classify_loss(
                            doc.text, fobj.span_start, fobj.span_end)
                    elif after[fname].canonical_value != fobj.canonical_value:
                        entry.changed_fields.append(fname)
            audits.append(entry)
    return RunResult(grouping, punctuation, len(groups), small,
                     raw_total, core_total, audits)


# --------------------------------------------------------------------------
# Rapor
# --------------------------------------------------------------------------

def _table(header: list[str], rows: list[list[str]]) -> str:
    out = ["| " + " | ".join(header) + " |",
           "|" + "|".join("---" for _ in header) + "|"]
    out += ["| " + " | ".join(r) + " |" for r in rows]
    return "\n".join(out)


def compare_table(results: list[RunResult]) -> str:
    """Yapılandırma karşılaştırma tablosu."""
    rows = []
    for r in results:
        rows.append([
            r.grouping, r.punctuation, str(r.groups),
            f"{r.boiler_ratio * 100:.1f}%",
            str(len(r.dropped)), str(len(r.harmful_docs)),
            str(sum(len(d.harmful) for d in r.harmful_docs)),
            str(r.chrome_leaks),
        ])
    return _table(
        ["gruplama", "noktalama", "grup", "çerçeve", "düşen belge",
         "zararlı kayıplı belge", "zararlı alan", "krom sızıntısı"], rows)


def loss_breakdown(result: RunResult) -> str:
    """Kayıp türlerinin alan bazında dağılımı."""
    counter: dict[tuple[str, str], int] = collections.Counter()
    for d in result.docs:
        for fname, kind in d.lost_fields.items():
            counter[(fname, kind)] += 1
    names = sorted({f for f, _ in counter})
    rows = [[n] + [str(counter.get((n, k), 0)) for k in LOSS_KINDS]
            for n in names]
    return _table(["alan", *LOSS_KINDS], rows)


def section_table(result: RunResult) -> str:
    """Bölüm bazında karar tablosu — kapsam kararı burada verilir."""
    per: dict[str, list[DocAudit]] = collections.defaultdict(list)
    for d in result.docs:
        per[d.section].append(d)
    rows = []
    for sec in sorted(per):
        docs = per[sec]
        raw = sum(d.raw_chars for d in docs)
        core = sum(d.core_chars for d in docs)
        harmful = [d for d in docs if d.harmful]
        rows.append([
            sec, str(len(docs)),
            f"{(1 - core / raw) * 100:.1f}%" if raw else "-",
            str(sum(1 for d in docs if d.has_signal and d.keep_ratio < DROP_RATIO)),
            str(len(harmful)),
            f"{len(harmful) / len(docs) * 100:.1f}%",
            str(sum(1 for d in docs if d.chrome_leak)),
        ])
    return _table(["bölüm", "belge", "çerçeve", "düşen", "zararlı kayıplı",
                   "zararlı oran", "krom sızıntısı"], rows)


def bank_table(result: RunResult) -> str:
    per: dict[str, list[DocAudit]] = collections.defaultdict(list)
    for d in result.docs:
        per[d.bank].append(d)
    rows = []
    for bank in sorted(per):
        docs = per[bank]
        raw = sum(d.raw_chars for d in docs)
        core = sum(d.core_chars for d in docs)
        rows.append([
            bank, str(len(docs)),
            f"{(1 - core / raw) * 100:.1f}%" if raw else "-",
            str(sum(1 for d in docs if d.has_signal and d.keep_ratio < DROP_RATIO)),
            str(sum(1 for d in docs if d.harmful)),
            str(sum(1 for d in docs if d.chrome_leak)),
        ])
    return _table(["banka", "belge", "çerçeve", "düşen", "zararlı kayıplı",
                   "krom sızıntısı"], rows)


def build_report(results: list[RunResult], baseline: RunResult) -> str:
    """Tam markdown rapor gövdesi."""
    parts = [
        "# Çerçeve ayıklaması — yarışma korpusu kapsam denetimi",
        "",
        f"Korpus: **{len(baseline.docs)} belge**, "
        f"**{baseline.raw_chars:,} karakter** (`data/raw`).".replace(",", "."),
        "",
        "## 1. Yapılandırma karşılaştırması",
        "",
        compare_table(results),
        "",
        "## 2. Referans yapılandırmada kayıp türleri "
        f"({baseline.grouping} / {baseline.punctuation})",
        "",
        loss_breakdown(baseline),
        "",
        "## 3. Bölüm bazında",
        "",
        section_table(baseline),
        "",
        "## 4. Banka bazında",
        "",
        bank_table(baseline),
        "",
        "## 5. Zararlı kayıp taşıyan belgeler",
        "",
    ]
    for d in sorted(baseline.harmful_docs, key=lambda x: x.doc_id)[:60]:
        parts.append(f"- `{d.doc_id}` [{d.section}] "
                     f"{d.raw_chars}→{d.core_chars} kr · {', '.join(d.harmful)}")
    return "\n".join(parts) + "\n"


# --------------------------------------------------------------------------
# Gold temizleme (etki ölçümü için)
# --------------------------------------------------------------------------

def clean_gold(gold_path: str, docs: list[Doc], grouping: str,
               punctuation: str) -> list[dict[str, object]]:
    """Gold kayıtlarının metnini çerçeveden ayıklanmış haliyle değiştirir.

    Çerçeve kümesi gold kaydının KENDİ metninden değil, korpustaki grubundan
    hesaplanır — tek belgeden çerçeve çıkarılamaz. Gold'da olup korpusta
    olmayan kayıt DEĞİŞTİRİLMEDEN geçer ve sayısı çağırana raporlanır.
    """
    with open(gold_path, encoding="utf-8") as fh:
        records = json.load(fh)
    groups = group_docs(docs, grouping)
    sets: dict[str, tuple[set[str], set[str]]] = {}
    where: dict[str, str] = {}
    for name, members in groups.items():
        for doc in members:
            where[doc.doc_id] = name
    for record in records:
        name = where.get(str(record.get("id")))
        if name is None:
            continue
        if name not in sets:
            sets[name] = boilerplate_sets_ext(
                [d.text for d in groups[name]], punctuation=punctuation)
        boiler, protected = sets[name]
        record["text"] = core_text(str(record.get("text", "")),
                                   boiler, protected)
    return records


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

def main(argv: Optional[list[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--docs", default="data/raw", help="korpus dizini")
    ap.add_argument("--gruplama", default="banka-bolum",
                    help="virgülle ayrılmış: " + ",".join(GROUPINGS))
    ap.add_argument("--noktalama", default="kapali",
                    help="virgülle ayrılmış: " + ",".join(PUNCTUATION_MODES))
    ap.add_argument("--referans", default=None,
                    help="ayrıntılı bölümler için <gruplama>/<noktalama>")
    ap.add_argument("--rapor", default=None, help="markdown rapor yolu")
    ap.add_argument("--jsonl", default=None, help="belge bazlı ölçüm çıktısı")
    ap.add_argument("--gold", default=None, help="temizlenecek gold JSON")
    ap.add_argument("--gold-cikti", default=None, help="temiz gold hedefi")
    args = ap.parse_args(argv)

    docs = iter_docs(args.docs)
    print(f"{len(docs)} belge okundu: {args.docs}")

    if args.gold:
        if not args.gold_cikti:
            ap.error("--gold ile --gold-cikti zorunlu")
        grouping = args.gruplama.split(",")[0]
        punctuation = args.noktalama.split(",")[0]
        records = clean_gold(args.gold, docs, grouping, punctuation)
        with open(args.gold_cikti, "w", encoding="utf-8") as fh:
            json.dump(records, fh, ensure_ascii=False, indent=1)
        print(f"gold temizlendi ({grouping}/{punctuation}): {args.gold_cikti}")
        return 0

    results: list[RunResult] = []
    for grouping in args.gruplama.split(","):
        for punctuation in args.noktalama.split(","):
            res = audit(docs, grouping.strip(), punctuation.strip())
            results.append(res)
            print(f"  {grouping}/{punctuation}: "
                  f"çerçeve {res.boiler_ratio * 100:.1f}% · "
                  f"düşen {len(res.dropped)} · "
                  f"zararlı {len(res.harmful_docs)} belge · "
                  f"sızıntı {res.chrome_leaks}")

    baseline = results[0]
    if args.referans:
        want = tuple(args.referans.split("/"))
        for res in results:
            if (res.grouping, res.punctuation) == want:
                baseline = res
                break

    print()
    print(compare_table(results))

    if args.rapor:
        with open(args.rapor, "w", encoding="utf-8") as fh:
            fh.write(build_report(results, baseline))
        print(f"\nrapor: {args.rapor}")
    if args.jsonl:
        with open(args.jsonl, "w", encoding="utf-8") as fh:
            for d in baseline.docs:
                fh.write(json.dumps({
                    "doc_id": d.doc_id, "bank": d.bank, "section": d.section,
                    "group": d.group, "raw_chars": d.raw_chars,
                    "core_chars": d.core_chars,
                    "keep_ratio": round(d.keep_ratio, 4),
                    "lost_fields": d.lost_fields,
                    "changed_fields": d.changed_fields,
                    "harmful": d.harmful, "chrome_leak": d.chrome_leak,
                }, ensure_ascii=False) + "\n")
        print(f"belge ölçümleri: {args.jsonl}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
