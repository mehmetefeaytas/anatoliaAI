"""RAG katmanı — açıklama/koşul soruları için.

İlgili: ../../decisions/hibrit-chatbot-text-to-sql-rag.md
        ../../concepts/web-scraping.md (içerik kaynağı), CLAUDE.md §5, §7

İki retriever:

- `KeywordRetriever`: TF-örtüşme + ters dizin, sıfır bağımlılık. **ÜRETİM YOLU.**
  1696 belgelik korpusta p99 12,18 ms (öncesi 576 ms) ve 54 soruda eski/yeni
  birebir eşdeğerliği kanıtlanmış durumda (tests/test_rag_index.py).
- `VectorRetriever`: bge-m3 + pgvector. `KeywordRetriever`'ın YERİNE GEÇMEZ,
  yanına gelir; anlamsal (semantik) sorularda tamamlayıcıdır. Gömme modeli ya
  da dolu `embeddings` tablosu yoksa devreye girmez.

Hangi retriever'ın kullanıldığı GÖRÜNÜRDÜR: `build_retriever()` seçimini
`logging` ile bildirir ve `RagAnswer.retriever` alanı yanıtla birlikte taşınır.
Sessizce düşmek, "vektör aramamız var" derken aslında anahtar-kelime araması
yapmak demek olurdu.

Üretim cevabı yerel LLM ile sentezlenir; LLM yoksa en alakalı pasajlar
"alıntı (extractive)" olarak döndürülür — yine kaynağa dayalı, halüsinasyonsuz.

## Pasajlar neden `ozet` taşıyor

Pasaj sözlüğündeki `text` belgenin TAMAMIDIR ve öyle kalmalıdır: LLM bağlamı,
karantina taraması ve denetim hep tam metne bakar. Ama tam metin arayüzde
basılabilir bir şey değil — korpusta belge başına ortalama 4.744 karakter var,
1774 belgenin 1005'i (%57) 2.000 karakteri aşıyor, en uzunu 178.825 karakter.
Kaynak tablosuna bu metnin dökülmesi ekranı okunmaz hâle getiriyordu.

Bu yüzden her pasaj, belgenin ÖNCEDEN üretilmiş özetini (`campaigns.ozet`,
ortalama 259 karakter) da taşır. Özet burada ÜRETİLMEZ, yalnızca taşınır;
üretilmemişse alan `None` kalır ve kural tabanlı sahte bir özet uydurulmaz —
gerekçesi `src/summarize/ozet.py` modül başlığında yazılı.
"""

from __future__ import annotations

import logging
import math
import os
import re
from collections import defaultdict
from dataclasses import dataclass
from dataclasses import field as dc_field
from typing import Any, Optional

from ..comparison.compare import RankRow, tekil_banka_urun
from ..db.repository import Repository
from ..preprocessing.clean import split_sentences, tr_fold, tr_fold_ascii
from . import safety
from .dayanak import dayanaksiz_sayilar
from .router import BANK_DISPLAY

try:                                    # yardımcı taşınıyor (bkz. _anlamli_alinti)
    from ..extraction.rules._ortak import gezinme_seridi as _gezinme_seridi
except ImportError:                     # henüz taşınmadı — eski adresten oku
    from ..extraction.rules.hedef_kitle import _gezinme_seridi

logger = logging.getLogger(__name__)

# En az kaç ANLAMLI sözcük örtüşmesi bir pasajı "kanıt" saymaya yeter.
# 1 örtüşme yetersizdir: "Helal gıda alışverişinde puan veren kampanya var mı?"
# sorusu yalnızca 'kampanya' üzerinden konut finansmanı metnini getiriyordu ve
# alakasız pasajı "ilgili kampanya" diye sunuyordu — sessiz halüsinasyon.
# Eşiğin altındaysa hiç pasaj döndürülmez; çekimserlik kapısı (safety KAPI 5)
# dürüstçe "verimde yok" der.
MIN_OVERLAP = 2

# BM25 parametreleri — SIRALAMA için, kapı için DEĞİL.
#
# ## Neden ikili örtüşme yerine BM25 (ölçüldü 2026-08-12, 1.774 belge)
#
# Eski skor `overlap / (sqrt(|qtok|) + 1)` idi: TF yok, IDF yok, uzunluk
# normalizasyonu yok. Sonucu, sıralayıcı korpus ortalamasının **1,7 katı**
# uzunlukta belge getiriyordu (935 vs 538 token) — uzun belge daha çok
# DEĞİŞİK token içerdiği için ikili örtüşme şişiyor. `_bankaya_suz()` sert
# filtresinin yazılma sebebi tam olarak buydu.
#
# Aynı tokenizer'la, yalnız skor formülü değiştirilerek ölçüldü:
#
#   skorlayıcı            R@1     MRR    banka+tür (n=55)
#   ikili örtüşme        0,766   0,871      15/55
#   ikili + IDF          0,766   0,871      15/55   (IDF tek başına SIFIR etki)
#   BM25                 0,795   0,889      31/55
#
# McNemar (banka+tür): b=16, c=0, p=3,1e-05 — düzelttiği 16 vaka, bozduğu 0.
# BM25+/L/F varyantları birbirine karşı anlamsız (p=0,73/1/1), bu yüzden
# EKLENMEDİ: ekstra δ ve alan ağırlıkları bu korpusta kendini ödemiyor,
# ölçülmemiş parametre yükü olurdu.
#
# UYARI — yukarıdaki 31/55 HAM sıralayıcının sayısıdır, üretim yolunun
# değil: ölçümdeki BM25 kolunun kapısı yoktu, üretimde `min_overlap` kapısı
# ve `_bankaya_suz()` var. Üretim hattındaki gerçek etki `eval/rag_eval.py`
# ile ayrıca ölçülür.
BM25_K1 = 1.2
BM25_B = 0.75

#: Bu süreçte kaç RAG sentezi istisnayla düştü.
#:
#: Sayaç, `logger.exception` ile birlikte var: günlük satırı bir OLAYı
#: anlatır, sayaç ise "bu koşumda sentez gerçekten çalıştı mı" sorusuna
#: cevap verir. `eval_injection.py` raporu "SENTEZ DAHİL (LLM açık)" derken
#: modelin sıfır token üretmiş olabileceğini ayırt edememişti; ölçüm
#: katmanının bu ayrımı okuyabilmesi gerekiyor.
#:
#: Sözlük (skaler değil) bilinçli: modül düzeyi bir `int`i fonksiyon içinden
#: artırmak `global` gerektirir; sözlük mutasyonu o bildirimi gereksiz kılar
#: ve sayacın tek bir yerde tanımlı kalmasını sağlar.
_SENTEZ_HATALARI: dict[str, int] = {"sayi": 0}


def sentez_hata_sayisi() -> int:
    """Bu süreçte istisnayla düşen RAG sentezi sayısı (ölçüm katmanı için)."""
    return _SENTEZ_HATALARI["sayi"]

# ...ama eşik MUTLAK sayı olarak uygulanamaz: soru tek anlamlı sözcükten
# ibaretse (`Sukuk nedir?` -> {'sukuk'}) 2 örtüşme MATEMATİKSEL OLARAK
# imkânsızdır ve terim soruları yapısal olarak cevapsız kalır. Ölçüldü
# (`docs/rapor/rag-terim-kapsama.md`, 15 fıkhî terim, kanıt şartı: dönen
# pasaj terimi gerçekten içermeli):
#
#     korpus 1761 belge, mutlak eşik 2   ->  4/15
#     korpus 1761 belge, oransal eşik    -> 14/15
#
# Doğru ölçüt "kaç sözcük tuttu" değil, **sorunun ne kadarı kanıtlandı**:
# eşik, sorunun anlamlı sözcük sayısını AŞAMAZ. Çok sözcüklü sorularda
# davranış birebir eskisi gibi kalır (min(2, n) = 2), yani yukarıdaki
# "helal gıda" halüsinasyonu geri gelmez.
def _etkin_esik(min_overlap: int, qtok: set[str]) -> int:
    """Eşiği sorunun anlamlı sözcük sayısıyla sınırlar (asla onu aşmaz)."""
    if min_overlap <= 0:
        return min_overlap
    return min(min_overlap, len(qtok)) if qtok else min_overlap

# Soru kalıbı sözcükleri: örtüşme sayımında sinyal değil gürültüdür.
_STOPWORDS = frozenset("""
bir bu şu o ve ile için mi mı mu mü var yok ne nedir nelerdir hangi hangisi
kaç daha en de da den dan te ta ten tan olan olarak göre gibi ama veya her
tüm ben sen siz bana beni bize nasıl niye neden misin misiniz mısın mısınız
kadar sonra önce çok az ki ise ancak yani hem ya
""".split())


# `build_retriever()` davranışını seçen ortam değişkeni.
#   keyword (VARSAYILAN) — yalnız KeywordRetriever. Üretim yolu değişmez.
#   auto                 — VectorRetriever dene, olmazsa KeywordRetriever'a düş
#                          (düşüş WARNING olarak loglanır).
#   vector               — VectorRetriever ZORUNLU; yoksa hata yükselt.
RETRIEVER_ENV = "RAG_RETRIEVER"
DEFAULT_RETRIEVER_MODE = "keyword"
RETRIEVER_MODES = ("keyword", "auto", "vector")


@dataclass
class RagAnswer:
    text: str
    #: Kaynak pasajlar — `/chat` yanıtındaki `sources` bunlardır.
    #: [{"bank","bank_slug","campaign_id","source_url","text","score"}]
    #:
    #: `campaign_id` ve `source_url` DENETİM alanlarıdır: jüri "bu bilgiyi
    #: nereden aldın" diye sorduğunda arayüz tek tıkla
    #: `GET /campaigns/{campaign_id}/text` uç noktasına gidip iddianın
    #: geldiği belgeyi offset'leriyle gösterebilmelidir. Daha önce yalnız
    #: metin parçası dönüyordu ve bağlantı kurulamıyordu.
    #:
    #: Bilinmeyen alan **null** kalır; URL uydurulmaz (CLAUDE.md §21).
    passages: list[dict]
    # Hangi retriever cevabı üretti ('keyword' | 'vector'). Varsayılanı olan
    # bir alan: mevcut `RagAnswer(text, passages)` çağrıları bozulmaz.
    retriever: str = "keyword"
    # KAPI 6 — talimat-devralma işareti taşıdığı için düşürülen pasajlar.
    # Boş liste normal koşu; dolu ise korpusta zehirli belge VAR demektir ve
    # bu SESSİZ GEÇİLMEZ (bkz. safety.detect_injection).
    quarantined: list[dict] = dc_field(default_factory=list)


# --------------------------------------------------------------------------- #
# Özet taşıma — üretim değil, aktarım
# --------------------------------------------------------------------------- #
#: LLM kapalıyken üretilen çıkarımsal cevaba konacak ham metin payı.
#: Cevap satırı bir okuma kutusudur, belge görüntüleyicisi değil; belgenin
#: tamamına erişim kaybolmaz, kaynak satırındaki katlanır kutuda durur.
ALINTI_KARAKTER = 320


def _ozet_alani(d: dict) -> Optional[str]:
    """Belgenin önceden üretilmiş özeti; üretilmemişse `None`.

    Burada özet ÜRETİLMEZ. Boş dizeyi `None`'a indirger, çünkü arayüz için
    "özet yok" ile "özet boş" aynı şeydir ve boş bir «AI Özeti» kutusu
    göstermek, üretilmemiş bir yeteneği üretilmiş gibi göstermek olurdu.
    """
    ozet = (d.get("ozet") or "").strip()
    return ozet or None


def kisa_alinti(metin: str, sinir: int = ALINTI_KARAKTER) -> str:
    """Metnin başından, sözcük ortasından kesmeyen kısa parça — ÖZET DEĞİL.

    Adı bilerek "özet" değil: bu parça belgenin ilk cümlelerinden ibarettir ve
    belgenin neyi anlattığına dair hiçbir iddia taşımaz. Onu «özet» diye
    sunmak, `src/summarize/ozet.py`'nin yasakladığı kural tabanlı sahte özetin
    ta kendisi olurdu; çağıran taraf bu ayrımı kullanıcıya SÖYLEMEK zorundadır.
    """
    metin = " ".join((metin or "").split())
    if len(metin) <= sinir:
        return metin
    kesik = metin[:sinir]
    bosluk = kesik.rfind(" ")
    # Tek bir devasa "sözcük" (boşluksuz) gelirse geri düşüş sert kesmedir.
    if bosluk > sinir // 2:
        kesik = kesik[:bosluk]
    return kesik.rstrip(" ,;:.") + "…"


#: Şapkalı ünlü -> taban ünlü. `tr_fold` küçültme yaptığı için büyük
#: biçimler de eşlenir (girdi her iki hâlde de gelebilsin diye).
_SAPKA_INDIRGEME = str.maketrans({
    "â": "a", "Â": "a", "î": "i", "Î": "i", "û": "u", "Û": "u",
})


def _tokenize(text: str) -> list[str]:
    """TR-doğru katlama + durak sözcük ayıklaması.

    `str.lower()` KULLANILMAZ: Türkçede hatalıdır ('TAŞIT'.lower() -> 'taşit',
    'İ'.lower() -> 'i' + U+0307 birleşen nokta). Bu retriever'da eskiden
    `.lower()` vardı ve ALL-CAPS banka başlıklarını sessizce kaçırıyordu
    (bkz. preprocessing/clean.tr_fold docstring'i).

    **Tek karakterli token'lar atılır.** Osmanlıca tamlamalar tirelidir ve
    ayırıcı sözcük sınırı sayıldığı için ortada tek harflik bir parça kalır:

        "Karz-ı hasen nedir?"  ->  ['karz', 'ı', 'hasen']
        "Hüsn-i niyet nedir?"  ->  ['hüsn', 'i', 'niyet']

    Bu parçalar leksik sinyal taşımaz ama örtüşme sayısını ŞİŞİRİR. Ölçüldü:
    'i' token'ı korpusta 672 belgede geçiyor; "Hüsn-i niyet nedir?" sorusu
    üç pasaj döndürüyor ve **hiçbiri iki gerçek terimi de taşımıyordu** —
    yani eşik gürültüyle dolduruluyordu. `MIN_OVERLAP`'in var oluş sebebi
    tam olarak bu sessiz halüsinasyondur; tek harfli token onu delen bir
    arka kapıydı.

    Rakamlar da atılır ('5', '3'): tek başına bir rakam bu retriever'da
    ayırt edici değildir — '5' korpusta 722 belgede geçiyor. Çok haneli
    sayılar ('36', '120') KORUNUR.

    **Şapkalı ünlüler tabanlarına indirilir** (`â î û` → `a i u`).
    Sebebi ölçülmüş bir kayıptı: karakter sınıfı bu harfleri tanımıyordu,
    bu yüzden sözcük sınırı sayılıyorlardı ve ortada kalan tek harfli
    parçalar yukarıdaki kuralla atılıyordu:

        "kâr payı oranı"  ->  ['payı', 'oranı']      # 'kâr' TAMAMEN düştü
        "vekâlet akdi"    ->  ['vek', 'let', 'akdi']

    `kâr payı` bu projenin merkezî terimi ve korpusun **319 belgesinde
    (%18) şapkalı** yazılıyor; hepsinde erişim dizininden düşüyordu.
    İndirgeme ayrıca iki yazımı birleştiriyor: 84 belgedeki şapkasız
    'kar payı' ile 319 belgedeki 'kâr payı' artık aynı token.

    Yalnız şapka kaldırılır, tam ASCII katlaması YAPILMAZ: `ş ç ğ ı ö ü`
    Türkçede ayırt edici harflerdir ve onları da katlamak farklı sözcükleri
    ('sac'/'saç') birleştirirdi. Tam katlama gerektiğinde
    `preprocessing.clean.tr_fold_ascii` var.
    """
    metin = tr_fold(text or "").translate(_SAPKA_INDIRGEME)
    toks = re.findall(r"[a-zçğıöşü0-9]+", metin)
    return [t for t in toks if len(t) > 1 and t not in _STOPWORDS]


class KeywordRetriever:
    """Basit kelime-örtüşme (Jaccard-benzeri) retriever — offline.

    ## Neden ters dizin (inverted index)

    İlk sürüm her soruda TÜM korpusu baştan tokenize ediyordu. 1696 belgelik
    gerçek korpusta bu, soru başına ~290 ms demekti ve chatbot p99'unun
    (~570 ms) neredeyse tamamını tek başına açıklıyordu — üstelik tam da RAG
    koluna düşen "en zor soru"da. 4 dakikalık jüri sunumunda yarım saniyelik
    duraklama demoyu zayıflatır (CLAUDE.md §11 aynı disiplini LLM için zaten
    şart koşuyor).

    Çözüm: tokenizasyon KURULUMDA bir kez yapılır, `token -> {belge_id}`
    ters dizini kurulur. Sorguda yalnızca sorunun token'larının gönderi
    listeleri (posting list) gezilir; korpusun geri kalanına hiç dokunulmaz.

    Sonuçlar DEĞİŞMEZ. Skor formülü, `min_overlap` eşiği ve eşitlik (tie)
    sıralaması birebir korunur:
    - `overlap = len(qtok & dtok)` <=> "kaç soru token'ı bu belgede geçiyor"
      (gönderi listeleri belge başına tekilleştirilmiş olduğu için aynı sayı).
    - Adaylar belge sırasına (dizin sırası) göre gezilir ve Python'un sort'u
      kararlı (stable) olduğundan eşit skorlu belgeler eski koddaki korpus
      sırasını korur.
    Bu eşdeğerlik `tests/test_rag_index.py` içinde dizinli/dizinsiz
    karşılaştırmasıyla kilitlenmiştir.

    Dizin kurulumdaki korpusun fotoğrafıdır: depoya kurulumdan SONRA eklenen
    kampanyalar görünmez. Teslim edilen demo önceden doldurulmuş DB'den okur
    (CLAUDE.md §11), veri sonradan değişirse `reindex()` çağrılır.
    """

    def __init__(self, repo: Repository, min_overlap: int = MIN_OVERLAP):
        self.repo = repo
        self.min_overlap = min_overlap
        self.reindex()

    def reindex(self) -> None:
        """Korpusu depodan okuyup ters dizini yeniden kurar (kurulum maliyeti).

        Dizin artık terim FREKANSINI de taşıyor (`token -> [(belge, tf)]`).
        Örtüşme sayımı bundan türetilir (gönderi listesi belge başına tekil
        olduğu için `len(posting)` aynı sayıyı verir), yani KAPI semantiği
        değişmez; frekans yalnız BM25 sıralaması için gerekli.
        """
        self._docs = self.repo.all_campaigns()
        # token -> [(belge indeksi, terim frekansı)]. Aynı belge bir token için
        # yalnızca bir kez eklenir; eski koddaki `set(_tokenize(...))` semantiği
        # örtüşme sayımında böylece korunur.
        index: dict[str, list[tuple[int, int]]] = defaultdict(list)
        df: dict[str, int] = defaultdict(int)
        uzunluk: dict[int, int] = {}
        # Boş metinli belgeler eski kodda `continue` ile atlanıyordu; dizine
        # hiç girmedikleri için burada da aday olamazlar.
        self._indexed_docs: list[int] = []
        for i, d in enumerate(self._docs):
            toks = _tokenize(d.get("raw_text", ""))
            if not toks:
                continue
            self._indexed_docs.append(i)
            tf: dict[str, int] = defaultdict(int)
            for t in toks:
                tf[t] += 1
            uzunluk[i] = len(toks)
            for t, n in tf.items():
                index[t].append((i, n))
                df[t] += 1
        self._index: dict[str, list[tuple[int, int]]] = dict(index)
        self._df: dict[str, int] = dict(df)
        # ASCII köprüsü: diakritiksiz yazım -> dizindeki gerçek token'lar.
        # Yalnız KARŞILIĞI OLMAYAN sorgu token'ları için kullanılır (bkz.
        # `_cozumle`), bu yüzden dizinin kendisi ASCII'ye ÇÖKMEZ.
        kopru: dict[str, set[str]] = defaultdict(set)
        for tok in index:
            kopru[tr_fold_ascii(tok)].add(tok)
        self._ascii_kopru: dict[str, list[str]] = {
            a: sorted(v) for a, v in kopru.items()}
        self._uzunluk: dict[int, int] = uzunluk
        self._N = len(self._indexed_docs)
        self._avgdl = (sum(uzunluk.values()) / self._N) if self._N else 1.0

    @property
    def document_count(self) -> int:
        """Dizindeki (kurulum anındaki) toplam belge sayısı."""
        return len(self._docs)

    def retrieve(self, query: str, k: int = 3) -> list[dict]:
        qtok = set(_tokenize(query))
        gruplar = self._cozumle(qtok)
        overlaps = self._count_overlaps(gruplar)
        # Eşik ORİJİNAL token kümesine dayanır: köprü bir soru sözcüğünü
        # varyantlarına açar ama yeni bir soru sözcüğü ÜRETMEZ.
        esik = _etkin_esik(self.min_overlap, qtok)

        bm25 = self._bm25_skorlari(gruplar)
        scored = []
        # Belge indeksi sırası = korpus sırası; eşit skorlarda eski kodun
        # sıralamasını korumak için artan sırada geziyoruz.
        for i in sorted(overlaps):
            overlap = overlaps[i]
            if overlap < esik:
                continue
            d = self._docs[i]
            cid = d.get("id")
            scored.append({
                "bank": d.get("bank_name") or d.get("bank"),
                # Slug ayrıca taşınır: `bank` insan-okur addır ve iki bankanın
                # görünen adı benzeşebilir; denetim bağlantısı slug'a dayanır.
                "bank_slug": d.get("bank"),
                "campaign_id": int(cid) if cid is not None else None,
                # Ürün ailesi ARTIK TAŞINIYOR. `_tur_suz()` ve çeşitlilik
                # tavanı (`_cesitlilik_tavani`) ikisi de bu alana bakar;
                # taşınmadığı sürece RAG yolu, yapısal yolun (`structured.
                # _apply_filters`) uyguladığı tür süzgecini uygulayamıyordu.
                "campaign_type": d.get("campaign_type"),
                "source_url": d.get("source_url"),
                "text": d.get("raw_text"),
                # Önceden üretilmiş özet; yoksa None. Arayüz uzun ham metin
                # yerine bunu basar (modül başlığı).
                "ozet": _ozet_alani(d),
                "score": round(bm25.get(i, 0.0), 3),
                # Kapıyı geçme gerekçesi ayrıca taşınır: skor artık BM25
                # olduğu için "kaç soru sözcüğü geçti" bilgisi skordan
                # OKUNAMIYOR, oysa çekimserlik kararının dayanağı odur.
                "overlap": overlap,
            })
        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:k]

    def _cozumle(self, qtok: set[str]) -> list[list[str]]:
        """Her soru token'ını dizindeki ARAMA ANAHTARLARINA çözer.

        Dönüş, soru token'ı BAŞINA bir liste taşır; örtüşme sayımı bu grupları
        gezerek her soru sözcüğünü belge başına **bir kez** sayar (varyanta
        bölünüp şişmesin).

        ## Neden köprü var

        `_tokenize` bilerek tam ASCII katlaması YAPMAZ: `ş ç ğ ı ö ü`
        Türkçede ayırt edicidir ve dizini ASCII'ye çökertmek 'sac' ile 'saç'ı
        birleştirirdi (bkz. `_tokenize` docstring'i). O karar duruyor.

        Ama bedeli ölçüldü: Türkçe klavyesi olmayan ya da hızlı yazan
        kullanıcı `Konut finansmani kampanyasinin kosullari neler?` diye
        sorar; hiçbir token dizinde bulunmaz ve chatbot **"bu bilgi verimde
        yok"** der. Aynı soru aksanlı yazılınca üç pasaj döner. Yani yapısal
        kol diakritiksiz girdiyi işlerken RAG kolu işlemiyordu — asimetri.
        Ağırlaştırıcı: projenin kendi dokümantasyonu RAG örneği olarak
        birebir bu soruyu kullanıyor.

        ## Niçin hassasiyeti bozmuyor

        Köprü **yalnız dizinde hiç karşılığı olmayan** token için devreye
        girer. `sac` korpusta gerçekten geçiyorsa `self._index` onu bulur ve
        genişletme HİÇ olmaz — 'saç' ile karışmaz. Yani doğru yazılmış her
        sorgunun davranışı birebir aynı kalır; gevşeme sadece "aksi hâlde
        sıfır sonuç" durumunda oluşur ve orada 'sac'/'saç' karışması,
        "bilgi yok" demekten kesinlikle daha iyi bir sonuçtur.
        """
        gruplar: list[list[str]] = []
        for t in sorted(qtok):
            if t in self._index:
                gruplar.append([t])
                continue
            varyantlar = self._ascii_kopru.get(tr_fold_ascii(t))
            gruplar.append(list(varyantlar) if varyantlar else [t])
        return gruplar

    def _bm25_skorlari(self, gruplar: list[list[str]]) -> dict[int, float]:
        """Aday belgelerin BM25 skorları (`K1`/`B` ölçülmüş değerler).

        Yalnız SIRALAMA için. Kapı (`min_overlap`) örtüşme SAYIMINDA kalır —
        eşiği BM25 skoruna bağlamak çekimserlik kapısını (safety KAPI 5)
        kalibrasyonsuz bırakırdı: BM25 skoru korpus istatistiğine bağlı
        sürekli bir sayıdır, "kaç soru sözcüğü geçti" ise sayılabilir bir
        kanıt ve 54 soruluk regresyon seti o kanıta göre kalibre edilmiş.
        """
        skor: dict[int, float] = defaultdict(float)
        # Grup içinde EN İYİ varyant alınır, varyantlar TOPLANMAZ. Bir soru
        # sözcüğü bir birim kanıt taşır; köprü onu iki yazıma açtığında
        # ikisini toplamak aynı sözcüğü çift saymak olurdu — `_count_overlaps`
        # kapı tarafında zaten grup başına bir kez sayıyor, skorun ondan
        # ayrışması sıralamayı köprülü sorgularda sessizce şişirirdi.
        # Ölçüldü: `finansmani` korpusta iki yazıma çözülüyor (`finansmanı`
        # ve noktasız-ı'lı `fınansmanı`); toplama sıralamayı oynatıyordu.
        #
        # Grup tek elemanlıysa (doğru yazılmış her sorgu) max == toplam,
        # yani bu değişiklik köprüsüz yolda HİÇBİR ŞEYİ değiştirmez.
        for grup in gruplar:
            grup_skoru: dict[int, float] = {}
            for t in grup:
                df = self._df.get(t)
                if not df:
                    continue
                idf = math.log(1 + (self._N - df + 0.5) / (df + 0.5))
                for i, tf in self._index.get(t, ()):
                    dl = self._uzunluk.get(i) or 1
                    s = idf * (tf * (BM25_K1 + 1)) / (
                        tf + BM25_K1 * (1 - BM25_B + BM25_B * dl / self._avgdl))
                    if s > grup_skoru.get(i, 0.0):
                        grup_skoru[i] = s
            for i, s in grup_skoru.items():
                skor[i] += s
        return skor

    def _count_overlaps(self, gruplar: list[list[str]]) -> dict[int, int]:
        """Belge indeksi -> soruyla örtüşen ANLAMLI token sayısı."""
        if self.min_overlap <= 0:
            # Eşik yoksa örtüşmesi 0 olan belgeler de sonuca girer (eski kod
            # onları da skorluyordu). Bu yol üretimde kullanılmaz; yalnızca
            # eşdeğerliği bozmamak için var.
            overlaps = {i: 0 for i in self._indexed_docs}
        else:
            overlaps = {}
        for grup in gruplar:
            # Gönderi listesi artık `(belge, tf)` taşıyor; örtüşme SAYIMI
            # frekanstan bağımsızdır (belge başına bir kez sayılır), yani
            # kapı semantiği dizin biçimi değişse de aynı kalır.
            #
            # Grup = BİR soru sözcüğünün arama anahtarları (bkz. `_cozumle`).
            # Belgeler önce grup içinde tekilleştirilir: bir soru sözcüğü iki
            # varyanta çözülüp ikisi de aynı belgede geçiyorsa örtüşme yine
            # 1 artar. Aksi hâlde köprü, kapıyı şişirerek delerdi.
            gorulen: set[int] = set()
            for t in grup:
                for i, _tf in self._index.get(t, ()):
                    gorulen.add(i)
            for i in gorulen:
                overlaps[i] = overlaps.get(i, 0) + 1
        return overlaps


class VectorRetrieverUnavailable(RuntimeError):
    """`VectorRetriever` kurulamadı: model yok ya da `embeddings` tablosu boş."""


class VectorRetriever:
    """bge-m3 + pgvector tabanlı anlamsal retriever.

    `KeywordRetriever` ile AYNI arayüzü sunar (`retrieve(query, k)` → aynı
    biçimde pasaj sözlükleri, `document_count`, `reindex()`), böylece
    `rag.answer()` ve `Chatbot` hangi retriever'ı kullandığını bilmek zorunda
    kalmaz.

    ## Neden yerine geçmiyor

    Anahtar-kelime retriever'ı bugün p99 12,18 ms ve 54 soruda davranışı
    kilitli. Vektör yolu bir model yüklemesi + vektör araması ekler; ölçülmüş
    bir kazanç gösterilmeden üretim yolunu değiştirmek, ölçülmemiş bir
    iddiayı demoya koymak olurdu. Bu yüzden varsayılan `RAG_RETRIEVER=keyword`
    ve bu sınıf açıkça istendiğinde devreye girer.

    ## Sessiz boşluk yok

    Kurulum üç şeyi ister ve üçü de yoksa AÇIK hata verir:
      1. gömme modeli (`embedding.BgeM3Embedder.available`),
      2. dolu `embeddings` tablosu (`store.count() > 0`),
      3. gömmelerin ait olduğu kampanyaların depoda bulunması.
    Üçü de sağlanmazsa boş sonuç dönüp "veride yok" demek, veri VARKEN
    kullanıcıya yanlış cevap vermek olurdu.

    `min_score`: kosinüs benzerliği eşiği. `KeywordRetriever.MIN_OVERLAP`'ın
    karşılığıdır — eşiğin altındaki pasaj "kanıt" sayılmaz ve çekimserlik
    kapısı (safety KAPI 5) dürüstçe devreye girer.
    """

    retriever_name = "vector"

    # bge-m3 normalize edilmiş vektörlerinde alakasız TR metin çiftleri tipik
    # olarak 0.3-0.45 bandındadır. Eşik ölçülmüş bir kalibrasyon DEĞİLDİR —
    # gömme korpusu üretilmediği için ölçülemedi; muhafazakâr bir başlangıç
    # değeridir ve `min_score` ile geçersiz kılınabilir.
    DEFAULT_MIN_SCORE = 0.5

    def __init__(self, repo: Repository, embedder=None, store=None,
                 min_score: float = DEFAULT_MIN_SCORE,
                 require_embeddings: bool = True):
        # Tembel import: `src.chatbot.rag` modülünü import etmek, gömme
        # katmanının (opsiyonel bağımlılıklar) yüklenmesini tetiklememeli.
        from ..rag.embedding import EmbeddingModelUnavailable, load_embedder
        from ..rag.store import open_vector_store

        self.repo = repo
        self.min_score = min_score
        self.store = store if store is not None else open_vector_store(repo)
        self.embedder = embedder if embedder is not None else load_embedder()

        reason = self._embedder_reason(EmbeddingModelUnavailable)
        if reason is not None:
            raise VectorRetrieverUnavailable(
                f"Gömme modeli kullanılamıyor: {reason}")
        if require_embeddings and self.store.count() == 0:
            raise VectorRetrieverUnavailable(
                f"`embeddings` tablosu boş ({self.store.backend}). Önce "
                "`python3 -m src.rag.build_embeddings` ile doldurun.")
        self.reindex()

    def _embedder_reason(self, unavailable_exc) -> Optional[str]:
        probe = getattr(self.embedder, "unavailable_reason", None)
        if callable(probe):
            return probe()
        try:
            self.embedder.encode(["ön kontrol"])
        except unavailable_exc as e:
            return str(e)
        return None

    def reindex(self) -> None:
        """Kampanya üstverisini (banka, URL, metin) yeniden okur.

        Vektörler `embeddings` tablosundadır; burada yalnızca `campaign_id` →
        üstveri eşlemesi tazelenir. Yeni kampanyaların ARANABİLİR olması için
        `build_embeddings` ayrıca koşturulmalıdır — dizin kendiliğinden
        gömme üretmez.
        """
        self._meta: dict[int, dict] = {
            int(d["id"]): d for d in self.repo.all_campaigns()
        }

    @property
    def document_count(self) -> int:
        """Gömmesi olan (aranabilir) belge sayısı — dizindeki belge değil."""
        return len(self._meta)

    def retrieve(self, query: str, k: int = 3) -> list[dict]:
        """En alakalı k kampanyayı döndürür (kampanya başına en iyi parça)."""
        if not (query or "").strip():
            return []
        vector = self.embedder.encode([query])[0]
        # Parça bazında ara, kampanya bazında tekilleştir: aynı kampanyanın
        # üç parçası ilk üç sırayı kapatırsa kullanıcı tek bankayı görürdü.
        hits = self.store.search(vector, k=max(k * 5, k))
        best: dict[int, Any] = {}
        for h in hits:
            if h.score < self.min_score:
                continue
            if h.campaign_id in best and best[h.campaign_id].score >= h.score:
                continue
            best[h.campaign_id] = h

        scored: list[dict] = []
        for campaign_id, hit in best.items():
            meta = self._meta.get(campaign_id)
            if meta is None:
                # Gömme var ama kampanya silinmiş: bayat satır. Uydurma
                # üstveriyle göstermektense atla, ama görünür kıl.
                logger.warning(
                    "embeddings satırı bilinmeyen kampanyaya işaret ediyor "
                    "(campaign_id=%s) — depo ve gömmeler senkron değil.",
                    campaign_id)
                continue
            scored.append({
                "bank": meta.get("bank_name") or meta.get("bank"),
                "bank_slug": meta.get("bank"),
                "campaign_id": int(campaign_id),
                # `KeywordRetriever` ile aynı sözleşme (bkz. oradaki yorum):
                # tür süzgeci ve çeşitlilik tavanı hangi retriever konuşursa
                # konuşsun aynı alanı okumalı.
                "campaign_type": meta.get("campaign_type"),
                "source_url": meta.get("source_url"),
                # Tam kampanya metni döndürülür (KeywordRetriever ile aynı
                # sözleşme); eşleşen parça ayrıca `chunk` alanında verilir.
                "text": meta.get("raw_text"),
                # `KeywordRetriever` ile aynı sözleşme: arayüz hangi
                # retriever'ın konuştuğunu bilmeden özeti bulabilmeli.
                "ozet": _ozet_alani(meta),
                "score": round(float(hit.score), 3),
                "chunk": hit.chunk_text,
                "chunk_index": hit.chunk_index,
            })
        scored.sort(key=lambda x: (-x["score"], x["bank"] or ""))
        return scored[:k]


def resolve_retriever_mode(mode: Optional[str] = None) -> str:
    """Etkin retriever modunu döndürür ('keyword' | 'auto' | 'vector')."""
    value = (mode if mode is not None
             else os.environ.get(RETRIEVER_ENV, DEFAULT_RETRIEVER_MODE))
    value = (value or DEFAULT_RETRIEVER_MODE).strip().lower()
    if value not in RETRIEVER_MODES:
        raise ValueError(
            f"{RETRIEVER_ENV}={value!r} geçersiz. Geçerli: "
            f"{', '.join(RETRIEVER_MODES)}")
    return value


def build_retriever(repo: Repository, mode: Optional[str] = None,
                    embedder=None, store=None):
    """Moda göre retriever kurar; `auto` modunda GÖRÜNÜR biçimde düşer.

    Dönen nesnenin `retriever_name` alanı hangi yolun seçildiğini söyler
    (`KeywordRetriever` bu alanı taşımaz; `answer()` onu 'keyword' sayar).
    """
    resolved = resolve_retriever_mode(mode)
    if resolved == "keyword":
        return KeywordRetriever(repo)
    try:
        retriever = VectorRetriever(repo, embedder=embedder, store=store)
    except VectorRetrieverUnavailable as e:
        if resolved == "vector":
            # Operatör vektör yolunu ZORUNLU kıldı; sessizce başka bir şey
            # çalıştırmak istediğinden farklı bir sistem teslim etmek olur.
            raise
        logger.warning(
            "VectorRetriever kurulamadı, KeywordRetriever'a düşülüyor. "
            "Sebep: %s", e)
        return KeywordRetriever(repo)
    logger.info("VectorRetriever etkin (%s parça, backend=%s).",
                retriever.store.count(), retriever.store.backend)
    return retriever


def answer(repo: Repository, question: str, llm=None, retriever=None, *,
           soru_karantinada: bool = False,
           filters: Optional[dict] = None) -> RagAnswer:
    """Soru için pasaj getirir; LLM varsa sentezler, yoksa alıntılar.

    `filters` ROUTER'IN çıkardığı süzgeçtir (`router.Route.filters`) ve
    `_bankaya_suz`'a geçer: banka VE ürün ailesi süzgeci burada uygulanır.
    Geçilmezse süzgeç soru metninden yeniden çıkarılır (eski davranış) —
    ama `bot.Chatbot` artık her zaman geçirir; süzgeci çöpe atmak, konut
    sorusuna ihtiyaç finansmanı belgesi göstermenin kök nedeniydi.

    `retriever` GEÇİLMEZSE her çağrıda yeni bir dizin kurulur — soru başına
    korpusun tamamı yeniden tokenize edilir. Tekrarlayan çağrılarda (chatbot)
    retriever'ı bir kez kurup geçirin; `Chatbot` tam olarak bunu yapar.

    Dönen `RagAnswer.retriever` hangi yolun kullanıldığını taşır; API/log
    tarafı bunu kullanıcıya gösterebilir.
    """
    retriever = retriever or KeywordRetriever(repo)
    used = getattr(retriever, "retriever_name", "keyword")
    passages = _bankaya_suz(retriever, question, filters)
    if not passages:
        return RagAnswer(_bos_sonuc_metni(filters), [], used)

    # KAPI 6 — getirilen içerik karantinası. LLM'e VE çıkarımsal yedeğe
    # gitmeden ÖNCE çalışır: ölçüldü ki yedek yol, saldırganın belgeye gömdüğü
    # talimat cümlesini kullanıcıya aynen basıyordu (eval_injection PI15).
    passages, karantina = _karantina(passages)
    if not passages:
        return RagAnswer(
            "İlgili kaynak bulundu ama içeriği güvenlik denetiminden geçmedi: "
            "belgede talimat devralma işareti var. Uydurmak yerine cevap "
            "vermiyorum.", [], used, quarantined=karantina)

    # SORU KARANTİNADA — sentez atlanır, çıkarımsal yedeğe düşülür.
    #
    # `safety.screen_input` sorunun kendisinde talimat devralma işareti
    # bulduysa (KAPI 6, girdi tarafı) soru sentez prompt'una GİRMEZ. Eskiden
    # `f"...Soru: {question}"` ile birebir giriyordu; "router regex'tir, ikna
    # edilemez" gerekçesi router için doğru ama sentez LLM'i için değildi.
    #
    # Kullanıcı REDDEDİLMİYOR: çıkarımsal cevap yapısı gereği zeminlidir
    # (belgeden alıntı), yani talimatın etkileyebileceği bir üretim adımı
    # kalmaz. Aşırı red ölçütü (0/6) bu yüzden bozulmuyor.
    if soru_karantinada:
        logger.warning(
            "soru karantinada (talimat devralma işareti): sentez atlandı, "
            "çıkarımsal yedeğe düşüldü")
    elif llm is not None and getattr(llm, "available", False):
        context = "\n---\n".join(f"[{p['bank']}] {p['text']}" for p in passages)
        try:
            resp = llm.client.generate_json(
                "Sadece verilen bağlamdan, kaynağa dayalı, kısa Türkçe cevap ver. "
                "Bağlamda yoksa 'bilgi bulunamadı' de. Çıktı: {\"cevap\": \"...\"}",
                f"Bağlam:\n{context}\n\nSoru: {question}",
                {"type": "object", "properties": {"cevap": {"type": "string"}}},
            )
            metin = (resp.get("cevap") or "").strip()
            gerekce = _dayanak_kusuru(metin, context)
            if gerekce is None:
                return RagAnswer(metin, passages, used, quarantined=karantina)
            logger.warning("RAG cevabı dayanak kapısından geçemedi (%s); "
                           "çıkarımsal yedeğe düşülüyor", gerekce)
        except Exception:
            # SESSİZ YUTMA KALDIRILDI (2026-08-12).
            #
            # Burada `pass` vardı ve tüm LLM sentez hatalarını KAYITSIZ
            # siliyordu. Tam olarak `extraction/llm/extractor.py:8-23`'ün
            # kaldırılmak için yeniden yazıldığı desen: "bu tek satır
            # sessizce yalan söyleyebiliyordu".
            #
            # Somut zarar: `scripts/eval_injection.py` raporu "SENTEZ DAHİL
            # (LLM açık)" başlığını basarken model sıfır token üretmiş
            # olabilirdi ve rapor bunu ayırt edemezdi — yani bir güvenlik
            # ölçümü, ölçtüğünü sandığı şeyi ölçmemiş olurdu.
            #
            # İstisna YUTULMAYA devam ediyor (çıkarımsal yedek doğru
            # davranıştır: LLM çökerse kullanıcı kaynaklı bir cevap almalı),
            # ama artık SESSİZ değil. `exception()` yığın izini de yazar;
            # tipin kendisi teşhis için yeterli değil (bağlantı hatası mı,
            # şema hatası mı, zaman aşımı mı).
            _SENTEZ_HATALARI["sayi"] += 1
            logger.exception(
                "RAG sentezi istisnayla düştü; çıkarımsal yedeğe düşülüyor "
                "(bu koşumdaki sentez hatası: %d)", _SENTEZ_HATALARI["sayi"])

    # LLM yok → extractive: en alakalı pasajı kaynağıyla döndür
    return RagAnswer(_cikarimsal_cevap(passages[0]) + _cesitlilik_notu(passages),
                     passages, used, quarantined=karantina)


def _bos_sonuc_metni(filters: Optional[dict]) -> str:
    """Süzgeç her şeyi elediğinde basılan cevap — NEYİN elediğini söyler.

    Eskiden tek bir sabit cümle vardı ("İlgili bir kampanya metni
    bulunamadı."). Süzgeç eklendikten sonra o cümle eksik kalıyor: kullanıcı
    korpusta hiç belge olmadığını sanır, oysa gerçek "bu ÜRÜN AİLESİNDE / bu
    BANKADA eşiği geçen belge yok"tur. Farkı söylemek, kullanıcıya bir sonraki
    adımı da vermektir.
    """
    kisitlar: list[str] = []
    tur = (filters or {}).get("campaign_type")
    if tur:
        kisitlar.append(f"**{tur}** ürün ailesinde")
    bankalar = list((filters or {}).get("banks") or [])
    if bankalar:
        adlar = ", ".join(BANK_DISPLAY.get(b, b) for b in bankalar)
        kisitlar.append(f"**{adlar}** için")
    if not kisitlar:
        return "İlgili bir kampanya metni bulunamadı."
    return (f"{' ve '.join(kisitlar)} soruyla örtüşen bir kampanya metni "
            "bulunamadı. Başka bankanın ya da başka ürün ailesinin belgesini "
            "cevap yerine göstermiyorum.")


def _cesitlilik_notu(passages: list[dict]) -> str:
    """Çeşitlilik tavanının düşürdüğü belge sayısını cevabın altına yazar.

    SESSİZ ELEME YOK: tavan bir bankanın 122 belgesini gösterimden çıkardıysa
    bunu söylemek zorundayız, yoksa "bu bankanın tek belgesi var" gibi
    okunurdu. Sayı `comparison.tekil_banka_urun()`in `other_count` alanından
    gelir — eleme ile sayım aynı yerde yapılır, ikinci bir sayaç tutulmaz.
    """
    dusen = sum(int(p.get("other_count") or 0) for p in passages)
    if not dusen:
        return ""
    return (f"\n\n_Not: Gösterilen {len(passages)} belgeye ek olarak aynı "
            f"banka ve ürün ailesinden {dusen} belge daha eşleşti; her "
            f"banka-ürün ailesinden yalnız en alakalı belge gösteriliyor._")


#: Süzme ve çeşitlilik tavanı kaç aday üzerinde çalışacak.
#:
#: Süzme, ilk 3 adayın ÜZERİNDE yapılamaz: sorulan bankanın belgesi 4. sırada
#: olabilir ve o zaman süzgeç, var olan bir cevabı yok gösterirdi. Aday havuzu
#: geniş tutulup süzmeden SONRA 3'e inilir.
#:
#: Havuz 24'ten 60'a çıkarıldı (2026-08-20). İki sebep, ikisi de ölçülmüş:
#:   * ÜRÜN AİLESİ SÜZGECİ (`_tur_suz`) banka süzgecinden çok daha sert
#:     eliyor: korpusta 1.782 kampanya ve 9 aile var, yani 24 adayın tümü
#:     yanlış aileden gelebilir ve var olan bir cevap yok görünürdü.
#:   * ÇEŞİTLİLİK TAVANI (`_cesitlilik_tavani`) banka × aile başına tek satır
#:     bırakıyor; tek bankanın 123 şablon-benzeri belgesi ilk 24 sırayı
#:     süpürdüğünde geriye üç değil BİR pasaj kalırdı.
#: Maliyet yalnız sıralama listesinin dilimlenmesidir — BM25 skorları zaten
#: aday havuzundan bağımsız olarak hesaplanmış durumda.
_CESITLILIK_ADAY_SAYISI = 60

#: Süzme sonrası döndürülecek pasaj sayısı — süzgeçsiz yoldaki `k` ile aynı.
_PASAJ_SAYISI = 3


def _cesitlilik_tavani(adaylar: list[dict]) -> list[dict]:
    """Banka × ürün ailesi başına TEK pasaj bırakır; düşürdüklerini SAYAR.

    ## Ölçülen kusur (2026-08-20, canlı sistem)

    `KeywordRetriever.retrieve` düz BM25 + `scored[:k]`'dir ve `_PASAJ_SAYISI`
    yalnız bir ADETtir, çeşitlilik kuralı değil. Dünya Katılım'ın 123
    şablon-benzeri belgesi ilk üç sırayı birden süpürüyordu (skorlar
    10,04 / 8,99 / 8,99) ve jüri, "hangi banka" sorusunun cevabı olarak TEK
    bankanın üç belgesini görüyordu.

    ## Kural İKİ YERDE ZATEN YAZILI — üçüncü kez yazılmadı

    * `VectorRetriever.retrieve` kampanya bazında tekilleştiriyor ("aynı
      kampanyanın üç parçası ilk üç sırayı kapatırsa kullanıcı tek bankayı
      görürdü") — ama üretim yolu `RAG_RETRIEVER=keyword`.
    * `comparison.tekil_banka_urun()` `(bank, campaign_type)` başına tek satır
      bırakıp düşürdüklerini `other_count` ile SAYIYOR.

    Bu fonksiyon ikincisini AYNEN çağırır: pasajlar geçici `RankRow`'lara
    çevrilir, kural uygulanır, `other_count` pasaja geri yazılır. Kuralı
    burada yeniden yazmak, bu depoda beş kez yaşanmış ayrışmayı davet etmek
    olurdu — ve tekilleştirme anahtarının neden `bank` değil
    `(bank, campaign_type)` olduğu (bir bankanın konut ve taşıt kampanyası
    FARKLI ürünlerdir) orada gerekçeli yazılı.

    Düşürülenler GİZLENMEZ: her pasaj `other_count` taşır ve `answer()` bu
    sayıyı cevabın altına yazar.
    """
    if not adaylar:
        return []
    satirlar = [
        RankRow(bank=p.get("bank_slug"), bank_name=p.get("bank"), value=None,
                sort_key=None, comparable=False, note=None, source_span=None,
                campaign_id=p.get("campaign_id"),
                campaign_type=p.get("campaign_type"))
        for p in adaylar
    ]
    # `tekil_banka_urun` sırayı KORUR ve ilk görüleni bırakır; adaylar BM25
    # sırasında geldiği için kalan, o (banka, aile) çiftinin en alakalı
    # belgesidir. Ayrı bir "en iyisini seç" mantığı yazmak sıralama kuralını
    # ikinci kez uygulamak olurdu.
    tekil = tekil_banka_urun(satirlar)
    pasaj_by_id = {p.get("campaign_id"): p for p in adaylar}
    out: list[dict] = []
    for x in tekil[:_PASAJ_SAYISI]:
        p = pasaj_by_id.get(x.campaign_id)
        if p is None:
            continue
        out.append({**p, "other_count": x.other_count})
    return out


def _bankaya_suz(retriever: Any, question: str,
                 filters: Optional[dict] = None) -> list[dict]:
    """Soruda banka adı / ürün ailesi geçiyorsa pasajları ONLARA sınırlar.

    ## Ölçülen kusur (2026-08-11)

    "Vakıf Katılım kart kampanyasında ne var?" sorusuna sistem **Kuveyt
    Türk**'ün makine finansmanı belgesini getiriyor ve ekranda "İlgili kampanya
    (Kuveyt Türk)" diye sunuyordu. Sorulmayan bankanın belgesi, sorulan bankanın
    cevabı gibi görünüyordu.

    Aynı kusur yapısal yolda ZATEN kapalıydı (`structured._apply_filters` banka
    süzgecini uyguluyor); RAG yolunda hiç yoktu. İki yolun aynı soruya farklı
    dürüstlük standardı uygulaması, kusuru bulmayı da zorlaştırıyordu.

    ## Sonuç boş kalırsa cevap da BOŞ kalır — bilerek

    Sorulan bankanın eşiği geçen belgesi yoksa hiç pasaj dönmez ve çekimserlik
    kapısı (`safety.guard_output` KAPI 5) "bu bilgi verimde yok" der. Alternatif,
    başka bankanın belgesini göstermekti; o da sessiz halüsinasyonun ta kendisi.

    Banka adı geçmeyen sorularda davranış BİREBİR eskisi gibi kalır.

    ## ÜRÜN AİLESİ SÜZGECİ (2026-08-20) — aynı asimetrinin ikinci ekseni

    Yukarıdaki blok banka eksenindeki asimetriyi kapatmakla övünüyordu ama
    ÜRÜN ekseninde aynısı açık duruyordu: `bot.py` router'ın çıkardığı
    `Route.filters`'ı `rag.answer`'a HİÇ GEÇMİYORDU ve bu fonksiyon banka
    süzgecini soruyu YENİDEN OKUYARAK kuruyordu; kampanya türü için hiçbir
    karşılığı yoktu.

    Ölçülen sonuç (canlı sistem, jürinin gördüğü ekran): **konut** finansmanı
    sorusuna dönen üç pasajın ikisi **İhtiyaç Finansmanı** belgesiydi.
    `structured._apply_filters` aynı süzgeci yapısal yolda 2026-08-11'den beri
    uyguluyordu — iki yolun aynı soruya farklı dürüstlük standardı uygulaması,
    kusuru bulmayı da zorlaştırıyordu (aynı cümle banka ekseni için de
    yazılmıştı).

    Süzgeç ARTIK ÇAĞIRANDAN gelir (`filters`): router'ın "ev" / "araba" /
    "mortgage" gibi günlük sözcükleri ürün ailesine çeviren sözlüğü
    (`router._FOLDED_TYPE_MAP`, `router._TUR_SOZCUK_DESENLERI`) burada ikinci
    kez yazılmaz. `filters` geçilmezse davranış birebir eskisi gibidir.

    Banka süzgecinde de çağıranın süzgeci ÖNCE gelir; yoksa soru yeniden
    okunur. İkisi aynı sonucu vermek zorunda değildir: bağlam devralması
    (`router._devral`) sorunun kendisinde geçmeyen bir bankayı süzgece
    koyabilir ve doğru olan, kullanıcının o turda gördüğü kapsamdır.
    """
    filters = filters or {}
    bankalar = list(filters.get("banks") or []) or safety.detect_banks(question)
    tur = filters.get("campaign_type")
    if not bankalar and not tur:
        return _cesitlilik_tavani(retriever.retrieve(question,
                                                     k=_CESITLILIK_ADAY_SAYISI))
    adaylar = retriever.retrieve(question, k=_CESITLILIK_ADAY_SAYISI)
    if bankalar:
        adaylar = [p for p in adaylar if p.get("bank_slug") in bankalar]
    if tur:
        adaylar = _tur_suz(adaylar, tur)
    return _cesitlilik_tavani(adaylar)


def _tur_suz(adaylar: list[dict], tur: str) -> list[dict]:
    """Pasajları TEK ürün ailesine sınırlar; boş kalırsa BOŞ döner.

    "Sonuç boş kalırsa cevap da boş kalır" kuralı burada da geçerlidir
    (yukarıdaki blok, banka ekseni): konut sorusuna ihtiyaç finansmanı
    belgesi göstermek sessiz halüsinasyondur, çekimserlik ise dürüst bir
    cevaptır.

    **Etiket doğruluğu bu fonksiyonun sorumluluğu DEĞİLDİR.** `campaigns.
    campaign_type` 8-sınıf sınıflandırıcının çıktısıdır ve kendi hata payı
    vardır; burada uygulanan şey yalnızca "sorulan aile ile belgenin ailesi
    aynı mı" karşılaştırmasıdır. Sınıflandırma hatası yanlış aileden belge
    gösterebilir — o hata `src/extraction/` tarafındadır ve süzgecin
    uygulanmamasıyla karıştırılmamalıdır.
    """
    dusen = [p for p in adaylar if p.get("campaign_type") != tur]
    if dusen:
        logger.info("RAG tür süzgeci: %d/%d aday %r dışında kaldı",
                    len(dusen), len(adaylar), tur)
    return [p for p in adaylar if p.get("campaign_type") == tur]


def _dayanak_kusuru(metin: str, baglam: str) -> Optional[str]:
    """LLM cevabı kaynağa dayanıyor mu — dayanmıyorsa gerekçe, dayanıyorsa None.

    ## Neden bu kapı var — ÖLÇÜLDÜ (2026-08-11, `data/demo.db`, 5 soru)

    Yönerge modele zaten *"sadece verilen bağlamdan"* diyor. Model uymuyor:

    * **2/5** cevap BOŞ dizeydi. Boş gövde kaynaklarla birlikte ekrana
      gidiyordu — çekimserlik kapısı (`safety.guard_output` KAPI 5) yalnız
      kaynak YOKKEN ateşlenir, burada kaynak vardı. Kullanıcı üç kaynak satırı
      ve hiçbir cevap görüyordu.
    * **1/5** cevap bağlamda GEÇMEYEN bir sayı taşıyordu ("%50 indirim").
      Ekranda o sayının altında, onu doğrulamayan kaynaklar duruyordu.

    Bir başka ölçülmüş biçim de şuydu: kullanıcının "hangisi daha avantajlı"
    sorusuna model, bağlamı hiç kullanmadan kendi genel bilgisinden
    *"bankaların web sitelerini ziyaret edin"* diye cevap verdi. O soru artık
    yapısal yola gidiyor (`router._kiyas_niyeti`), ama aynı davranış başka
    sorularda tekrar edebilir.

    ## Neden yalnız SAYI ve BOŞLUK

    Kapı dar tutuldu ve "anlamca uyuyor mu" gibi bir yargı VERMİYOR: öyle bir
    kapı ya çok gevşek olur (hiçbir şey yakalamaz) ya da doğru cevapları eler.
    Sayı ise bu sistemde uydurulduğunda en pahalı şeydir — kullanıcı kararını
    orana, vadeye ve tutara göre verir.

    ## Kapıya takılan cevap SİLİNMEZ, YERİNE geçilir

    Cevap atılıp boş bırakılmaz: çıkarımsal yedek (`_cikarimsal_cevap`) devreye
    girer ve en alakalı pasajı KAYNAĞIYLA alıntılar. Yani kullanıcı yine bir
    cevap alır; farkı, o cevabın her kelimesinin belgede durmasıdır.
    """
    if not metin:
        return "boş cevap"
    uydurma = dayanaksiz_sayilar(metin, baglam)
    if uydurma:
        return f"kaynakta geçmeyen sayı: {', '.join(uydurma[:5])}"
    return None


def _cikarimsal_cevap(top: dict) -> str:
    """LLM kapalıyken gösterilen cevap gövdesi.

    Eskiden burada `f"İlgili kampanya ({bank}): {top['text']}"` vardı ve
    `text` belgenin TAMAMIYDI: tek soru, cevap kutusuna 4.000+ karakterlik
    ham sayfa döküyordu. Ölçüldü — korpustaki 1774 belgenin 1005'i 2.000
    karakteri aşıyor, en uzunu 178.825 karakter.

    Artık önceden üretilmiş özet varsa o basılır. Yoksa ham metnin başlangıcı
    gösterilir ve bunun özet OLMADIĞI açıkça yazılır: özeti olmayan belgede
    ilk cümleleri «özet» diye sunmak, ölçülmemiş bir yeteneği ölçülmüş gibi
    göstermek olurdu.
    """
    banka = top.get("bank") or "banka bilinmiyor"
    ozet = _ozet_alani(top)
    if ozet:
        return f"İlgili kampanya ({banka}) — AI Özeti: {ozet}"

    alinti = _anlamli_alinti(top.get("text") or "")
    if not alinti:
        return (f"İlgili kampanya ({banka}). Belgenin metni boş olduğu için "
                "gösterilecek bir parça yok.")
    return (f"İlgili kampanya ({banka}). Bu belge için AI Özeti üretilmedi; "
            f"aşağıdaki satır özet değil, ham metnin başlangıcıdır: {alinti}")


def _anlamli_alinti(metin: str) -> str:
    """Ham metnin başından GEZİNME ŞERİDİ olmayan ilk parça.

    ## Ölçülen kusur

    Özeti olmayan belgede `_cikarimsal_cevap` ham metnin başlangıcını basıyor
    ve bir banka sayfasının BAŞI menüdür: "Bireysel Kurumsal Kredi Kartı
    Kampanyaları Maaş Ödemesi Kampanyaları …". Kullanıcı, cevabın gövdesinde
    HTML menüsünün metne inmiş hâlini görüyordu. Özet kapsaması %98,5'e
    çıkarıldı ama kalan 27 belge için bu yol duruyor.

    ## Yardımcı yeniden kullanılıyor, yeniden yazılmıyor

    `extraction.rules` içindeki `_gezinme_seridi` bu kalıbı ölçülmüş bir
    imzayla tanıyor (büyük harf yoğunluğu ≥ %60, cümle sonu noktalaması yok,
    en az 6 sözcük) ve `hedef_kitle` alanının yanlış pozitiflerinin yarısını
    tek başına o mekanizma üretiyordu. Aynı imza, aynı kirlilik.

    İçe aktarma iki adreste denenir: yardımcı `_ortak`'a taşınıp kamuya
    açılıyor (paralel çalışma, 2026-08-20) ama henüz orada olmayabilir.
    `src/extraction/**` bu değişikliğin kapsamı DIŞINDA, o yüzden burada
    yalnızca okunur — taşındığında bu blok kendiliğinden yeni adrese geçer.
    """
    cumleler = [c for c in split_sentences(metin or "") if c.strip()]
    temiz = [c for c in cumleler if not _gezinme_seridi(c)]
    # Belgenin TAMAMI şeritse ham metne düşülür: boş bir alıntı basmak, elde
    # duran tek kanıtı hiç göstermemek olurdu.
    govde = " ".join(temiz) if temiz else (metin or "")
    return kisa_alinti(_serit_kirp(govde) or govde)


#: Şerit taramasında kaç sözcüklük pencereye bakılacağı.
#:
#: `_gezinme_seridi` en az 6 sözcük ister (daha kısa parçada büyük-harf oranı
#: gürültüdür); 8 seçildi ki pencere eşiğin hemen üstünde kalsın ve tek bir
#: küçük harfli sözcük oranı %60'ın altına düşürmeye yetmesin.
_SERIT_PENCERESI = 8


def _serit_kirp(metin: str) -> str:
    """Metnin BAŞINDAKİ gezinme şeridini sözcük sözcük kırpar.

    ## Cümle bazlı süzme neden yetmedi (ölçüldü, `data/demo.db`)

    `raw_text` alanında SATIR SONU YOK (`normalize_whitespace` onları
    boşluğa çeviriyor) ve menü şeridi noktalama TAŞIMADIĞI için ilk gerçek
    cümleyle TEK parça hâlinde geliyor:

        "Müşteri Ol Kendim İçin SİZE ÖZEL ÇÖZÜMLER ÜRÜN VE HİZMETLERİMİZ …
         BANKA MÜŞTERİSİ AYDINLATMA METNİ VERİ SORUMLUSUNUN KİMLİĞİ Bu ay …"

    Bu parça noktayla bittiği için `_gezinme_seridi` onu (doğru biçimde)
    cümle sayar — imza "cümle sonu noktalaması YOK" der. Yani cümle bazlı
    süzme, özeti olmayan 27 belgenin çoğunda hiçbir şey yapmıyordu.

    ## İmza yeniden yazılmıyor, PENCEREYE uygulanıyor

    Buradaki tek yenilik tarama biçimidir: baştan `_SERIT_PENCERESI`
    sözcüklük pencereye bakılır ve pencere şerit imzasını taşıdığı sürece
    bir sözcük ileri kayılır. Kararı veren yine `_gezinme_seridi`'dir
    (büyük-harf yoğunluğu ≥ %60, cümle sonu noktalaması yok) — eşikler bu
    dosyada ikinci kez tanımlanmaz.

    Her şey kırpılırsa boş dize döner ve çağıran ham gövdeye düşer: elde
    duran tek kanıtı hiç göstermemek, menü basmaktan kötüdür.
    """
    kelimeler = (metin or "").split()
    i = 0
    while (i + _SERIT_PENCERESI <= len(kelimeler)
           and _gezinme_seridi(" ".join(kelimeler[i:i + _SERIT_PENCERESI]))):
        i += 1
    return " ".join(kelimeler[i:])


def _karantina(passages: list[dict]) -> tuple[list[dict], list[dict]]:
    """(temiz pasajlar, karantinaya alınanlar).

    Belge TAMAMEN düşürülür, saldırı satırı ayıklanmaz: içine talimat
    gömülmüş bir sayfanın geri kalanına da güvenilemez. Kaynak üçüncü taraf
    bir banka sitesidir ve içeriği bizim denetimimizde değildir.
    """
    temiz: list[dict] = []
    kirli: list[dict] = []
    for p in passages:
        isaret = safety.detect_injection(p.get("text", ""))
        if isaret:
            kirli.append({**p, "isaret": isaret})
            logger.warning("KAPI 6: pasaj karantinaya alindi (%s) isaret=%r",
                           p.get("source_url") or p.get("bank"), isaret)
        else:
            temiz.append(p)
    return temiz, kirli
