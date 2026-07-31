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
"""

from __future__ import annotations

import logging
import os
import re
from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Optional

from ..db.repository import Repository
from ..preprocessing.clean import tr_fold

logger = logging.getLogger(__name__)

# En az kaç ANLAMLI sözcük örtüşmesi bir pasajı "kanıt" saymaya yeter.
# 1 örtüşme yetersizdir: "Helal gıda alışverişinde puan veren kampanya var mı?"
# sorusu yalnızca 'kampanya' üzerinden konut finansmanı metnini getiriyordu ve
# alakasız pasajı "ilgili kampanya" diye sunuyordu — sessiz halüsinasyon.
# Eşiğin altındaysa hiç pasaj döndürülmez; çekimserlik kapısı (safety KAPI 5)
# dürüstçe "verimde yok" der.
MIN_OVERLAP = 2

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
    passages: list[dict]   # [{"bank","source_url","text","score"}]
    # Hangi retriever cevabı üretti ('keyword' | 'vector'). Varsayılanı olan
    # bir alan: mevcut `RagAnswer(text, passages)` çağrıları bozulmaz.
    retriever: str = "keyword"


def _tokenize(text: str) -> list[str]:
    """TR-doğru katlama + durak sözcük ayıklaması.

    `str.lower()` KULLANILMAZ: Türkçede hatalıdır ('TAŞIT'.lower() -> 'taşit',
    'İ'.lower() -> 'i' + U+0307 birleşen nokta). Bu retriever'da eskiden
    `.lower()` vardı ve ALL-CAPS banka başlıklarını sessizce kaçırıyordu
    (bkz. preprocessing/clean.tr_fold docstring'i).
    """
    toks = re.findall(r"[a-zçğıöşü0-9]+", tr_fold(text or ""))
    return [t for t in toks if t not in _STOPWORDS]


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
        """Korpusu depodan okuyup ters dizini yeniden kurar (kurulum maliyeti)."""
        self._docs = self.repo.all_campaigns()
        # token -> belge indeksleri. Aynı belge bir token için yalnızca bir kez
        # eklenir; eski koddaki `set(_tokenize(...))` semantiği budur.
        index: dict[str, list[int]] = defaultdict(list)
        # Boş metinli belgeler eski kodda `continue` ile atlanıyordu; dizine
        # hiç girmedikleri için burada da aday olamazlar.
        self._indexed_docs: list[int] = []
        for i, d in enumerate(self._docs):
            dtok = set(_tokenize(d.get("raw_text", "")))
            if not dtok:
                continue
            self._indexed_docs.append(i)
            for t in dtok:
                index[t].append(i)
        self._index: dict[str, list[int]] = dict(index)

    @property
    def document_count(self) -> int:
        """Dizindeki (kurulum anındaki) toplam belge sayısı."""
        return len(self._docs)

    def retrieve(self, query: str, k: int = 3) -> list[dict]:
        qtok = set(_tokenize(query))
        overlaps = self._count_overlaps(qtok)

        scored = []
        denom = len(qtok) ** 0.5 + 1
        # Belge indeksi sırası = korpus sırası; eşit skorlarda eski kodun
        # sıralamasını korumak için artan sırada geziyoruz.
        for i in sorted(overlaps):
            overlap = overlaps[i]
            if overlap < self.min_overlap:
                continue
            d = self._docs[i]
            scored.append({
                "bank": d.get("bank_name") or d.get("bank"),
                "source_url": d.get("source_url"),
                "text": d.get("raw_text"),
                "score": round(overlap / denom, 3),
            })
        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:k]

    def _count_overlaps(self, qtok: set[str]) -> dict[int, int]:
        """Belge indeksi -> soruyla örtüşen ANLAMLI token sayısı."""
        if self.min_overlap <= 0:
            # Eşik yoksa örtüşmesi 0 olan belgeler de sonuca girer (eski kod
            # onları da skorluyordu). Bu yol üretimde kullanılmaz; yalnızca
            # eşdeğerliği bozmamak için var.
            overlaps = {i: 0 for i in self._indexed_docs}
        else:
            overlaps = {}
        for t in qtok:
            for i in self._index.get(t, ()):
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
                "source_url": meta.get("source_url"),
                # Tam kampanya metni döndürülür (KeywordRetriever ile aynı
                # sözleşme); eşleşen parça ayrıca `chunk` alanında verilir.
                "text": meta.get("raw_text"),
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


def answer(repo: Repository, question: str, llm=None, retriever=None) -> RagAnswer:
    """Soru için pasaj getirir; LLM varsa sentezler, yoksa alıntılar.

    `retriever` GEÇİLMEZSE her çağrıda yeni bir dizin kurulur — soru başına
    korpusun tamamı yeniden tokenize edilir. Tekrarlayan çağrılarda (chatbot)
    retriever'ı bir kez kurup geçirin; `Chatbot` tam olarak bunu yapar.

    Dönen `RagAnswer.retriever` hangi yolun kullanıldığını taşır; API/log
    tarafı bunu kullanıcıya gösterebilir.
    """
    retriever = retriever or KeywordRetriever(repo)
    used = getattr(retriever, "retriever_name", "keyword")
    passages = retriever.retrieve(question)
    if not passages:
        return RagAnswer("İlgili bir kampanya metni bulunamadı.", [], used)

    if llm is not None and getattr(llm, "available", False):
        context = "\n---\n".join(f"[{p['bank']}] {p['text']}" for p in passages)
        try:
            resp = llm.client.generate_json(
                "Sadece verilen bağlamdan, kaynağa dayalı, kısa Türkçe cevap ver. "
                "Bağlamda yoksa 'bilgi bulunamadı' de. Çıktı: {\"cevap\": \"...\"}",
                f"Bağlam:\n{context}\n\nSoru: {question}",
                {"type": "object", "properties": {"cevap": {"type": "string"}}},
            )
            return RagAnswer(resp.get("cevap", ""), passages, used)
        except Exception:
            pass

    # LLM yok → extractive: en alakalı pasajı kaynağıyla döndür
    top = passages[0]
    text = f"İlgili kampanya ({top['bank']}): {top['text']}"
    return RagAnswer(text, passages, used)
