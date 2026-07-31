"""RAG katmanı — açıklama/koşul soruları için.

İlgili: ../../decisions/hibrit-chatbot-text-to-sql-rag.md
        ../../concepts/web-scraping.md (içerik kaynağı), CLAUDE.md §5, §7

İki retriever:
- KeywordRetriever: TF-örtüşme tabanlı, sıfır bağımlılık, offline fallback.
- VectorRetriever: bge-m3 + pgvector (üretim). Embedding modeli yoksa
  KeywordRetriever kullanılır.

Üretim cevabı yerel LLM ile sentezlenir; LLM yoksa en alakalı pasajlar
"alıntı (extractive)" olarak döndürülür — yine kaynağa dayalı, halüsinasyonsuz.
"""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass
from typing import Optional

from ..db.repository import Repository
from ..preprocessing.clean import tr_fold

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


@dataclass
class RagAnswer:
    text: str
    passages: list[dict]   # [{"bank","source_url","text","score"}]


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


def answer(repo: Repository, question: str, llm=None, retriever=None) -> RagAnswer:
    """Soru için pasaj getirir; LLM varsa sentezler, yoksa alıntılar.

    `retriever` GEÇİLMEZSE her çağrıda yeni bir dizin kurulur — soru başına
    korpusun tamamı yeniden tokenize edilir. Tekrarlayan çağrılarda (chatbot)
    retriever'ı bir kez kurup geçirin; `Chatbot` tam olarak bunu yapar.
    """
    retriever = retriever or KeywordRetriever(repo)
    passages = retriever.retrieve(question)
    if not passages:
        return RagAnswer("İlgili bir kampanya metni bulunamadı.", [])

    if llm is not None and getattr(llm, "available", False):
        context = "\n---\n".join(f"[{p['bank']}] {p['text']}" for p in passages)
        try:
            resp = llm.client.generate_json(
                "Sadece verilen bağlamdan, kaynağa dayalı, kısa Türkçe cevap ver. "
                "Bağlamda yoksa 'bilgi bulunamadı' de. Çıktı: {\"cevap\": \"...\"}",
                f"Bağlam:\n{context}\n\nSoru: {question}",
                {"type": "object", "properties": {"cevap": {"type": "string"}}},
            )
            return RagAnswer(resp.get("cevap", ""), passages)
        except Exception:
            pass

    # LLM yok → extractive: en alakalı pasajı kaynağıyla döndür
    top = passages[0]
    text = f"İlgili kampanya ({top['bank']}): {top['text']}"
    return RagAnswer(text, passages)
