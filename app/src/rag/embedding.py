"""Gömme (embedding) modeli — BAAI/bge-m3.

İlgili: CLAUDE.md §7 (Embeddings: BAAI/bge-m3), docs/model-license-audit.md
        (bge-m3 = MIT, §5.10 uyumlu ✅)

## Tasarım kısıtı: model yoksa AÇIK HATA

Bu ortamda (ve muhtemelen teslim makinesinde de, ağırlık önceden indirilmemişse)
`sentence-transformers` veya bge-m3 ağırlıkları bulunmayabilir. İki yanlış
davranış var ve ikisinden de kaçınılıyor:

1. **Sessizce boş vektör dönmek** — retriever hiçbir şey bulamaz, chatbot
   "verimde yok" der. Veri VARDIR; sistem yalan söylemiş olur.
2. **Sessizce indirmeye çalışmak** — on-prem/offline iddiası (CLAUDE.md §1)
   ağ isteği çıkaran bir kod yolunu kaldırmaz.

Bu yüzden: model yoksa `EmbeddingModelUnavailable` yükselir, mesajda ne
kurulacağı ve offline alternatifin ne olduğu yazar. `HF_HUB_OFFLINE=1` +
`local_files_only=True` varsayılandır — kod kendiliğinden internete çıkmaz.

## İkinci kaynak: SSB EVREN (`EvrenEmbedder`)

Ölçüldü (2026-08-24): bu makinede `sentence-transformers` kurulu olmadığı
için `embeddings` tablosu BOŞ kalmıştı ve `chatbot/rag.py` içindeki
`VectorRetriever` hiç devreye girmiyordu — chatbot yalnız anahtar-kelime
ile çalışıyordu. EVREN aynı modeli (`bge-m3-embed` = `BAAI/bge-m3`, 1024
boyut) uzak uçtan veriyor; gerçek korpusta ölçülen kalite Recall@1 %97,
MRR 0,983 (bkz. `docs/evren-servisi.md` §8).

Bu yol §5.9 (on-prem) ile çelişmez: üretilen vektörler `embeddings`
tablosuna YAZILIR, yani uzak uç **tek seferlik bir üretim adımında**
kullanılır. Teslim edilen sistem arama yaparken ağa çıkmaz.
"""

from __future__ import annotations

import logging
import os
from typing import Optional, Protocol, Sequence

# bge-m3 yoğun (dense) vektör boyutu. `db/schema.sql`'deki vector(1024) ile
# AYNI olmak ZORUNDA; ayrışırlarsa INSERT Postgres tarafında patlar.
logger = logging.getLogger(__name__)

# bge-m3 yogun vektor boyutu (asagidaki yorum korunuyor).
EMBEDDING_DIM = 1024
DEFAULT_MODEL_NAME = "BAAI/bge-m3"

# Yerel ağırlık dizini (offline teslim). Verilmezse model adı kullanılır ve
# HF önbelleği aranır.
MODEL_DIR_ENV = "EMBEDDING_MODEL_DIR"
MODEL_NAME_ENV = "EMBEDDING_MODEL"


class EmbeddingModelUnavailable(RuntimeError):
    """Gömme modeli yüklenemedi — sessiz düşme yerine açık hata."""


class Embedder(Protocol):
    """Gömme üreticisi sözleşmesi (test sahteleri de bunu uygular)."""

    name: str
    dim: int

    def encode(self, texts: Sequence[str]) -> list[list[float]]: ...


class BgeM3Embedder:
    """`sentence-transformers` üzerinden bge-m3.

    Model YÜKLENMEZ (tembel): `available` kontrolü ucuzdur, gerçek yükleme ilk
    `encode()` çağrısında olur.
    """

    def __init__(self, model_name: Optional[str] = None,
                 device: Optional[str] = None,
                 local_files_only: bool = True):
        self.name = (model_name
                     or os.environ.get(MODEL_DIR_ENV, "").strip()
                     or os.environ.get(MODEL_NAME_ENV, "").strip()
                     or DEFAULT_MODEL_NAME)
        self.dim = EMBEDDING_DIM
        self.device = device
        self.local_files_only = local_files_only
        self._model = None

    @property
    def available(self) -> bool:
        """Model gerçekten yüklenebiliyor mu (yükleyip önbelleğe alır)."""
        try:
            self._load()
        except EmbeddingModelUnavailable:
            return False
        return True

    def unavailable_reason(self) -> Optional[str]:
        """Yüklenemiyorsa insan-okur sebep, yükleniyorsa None."""
        try:
            self._load()
        except EmbeddingModelUnavailable as e:
            return str(e)
        return None

    def _load(self):
        if self._model is not None:
            return self._model
        try:
            from sentence_transformers import SentenceTransformer
        except ModuleNotFoundError as e:
            raise EmbeddingModelUnavailable(
                "`sentence-transformers` kurulu değil, bge-m3 gömmeleri "
                "üretilemez. Kurulum: pip install 'sentence-transformers>=2.7'. "
                "Offline teslimde ağırlıklar önceden indirilip "
                f"{MODEL_DIR_ENV} ile gösterilmelidir "
                "(bkz. docs/OFFLINE-KANIT.md 'Ağırlık bütünlüğü'). "
                "Model olmadan sistem KeywordRetriever ile çalışır — "
                "bkz. src/chatbot/rag.build_retriever()") from e
        try:
            kwargs = {"local_files_only": self.local_files_only}
            if self.device:
                kwargs["device"] = self.device
            self._model = SentenceTransformer(self.name, **kwargs)
        except Exception as e:  # ağırlık yok / bozuk / uyumsuz sürüm
            raise EmbeddingModelUnavailable(
                f"bge-m3 modeli ('{self.name}') yüklenemedi: {type(e).__name__}: {e}. "
                f"Offline modda ağırlıklar yerelde olmalı ({MODEL_DIR_ENV} veya "
                "HF önbelleği). Ağdan indirmek isteniyorsa "
                "local_files_only=False ile çağırın — ama bu on-prem/offline "
                "kısıtını (CLAUDE.md §1) ihlal eder.") from e
        got = int(self._model.get_sentence_embedding_dimension())
        if got != self.dim:
            raise EmbeddingModelUnavailable(
                f"Model boyutu {got}, beklenen {self.dim} "
                f"(db/schema.sql: vector({self.dim})). Yanlış model yüklendi; "
                "boyut uyuşmazlığı INSERT sırasında patlar.")
        return self._model

    def encode(self, texts: Sequence[str]) -> list[list[float]]:
        """Metinleri L2-normalize edilmiş yoğun vektörlere çevirir.

        Normalizasyon burada yapılır: kosinüs benzerliği hem pgvector
        (`<=>`) hem SQLite tam-tarama yolunda aynı ölçekte olsun.
        """
        model = self._load()
        vectors = model.encode(list(texts), normalize_embeddings=True,
                               convert_to_numpy=True)
        return [[float(x) for x in row] for row in vectors]


#: EVREN gömme ucu varsayılanları. Anahtar burada TUTULMAZ (§5.10).
EVREN_URL_VARSAYILAN = "https://evren-llmapi.ssyz.org.tr"
EVREN_MODEL_VARSAYILAN = "bge-m3-embed"
#: Ölçüldü (24 Ağu): 256 girdi tek istekte 1,34 s; 32'lik parçalarla aynı
#: iş ~4 kat daha uzun sürer. Sunucu paylaşımlı olduğu için sınırsız
#: büyütülmez — 128 hem hızlı hem nazik.
EVREN_BATCH_VARSAYILAN = 128
BATCH_ENV = "EVREN_EMBEDDING_BATCH"

#: Hangi kademeler kurulacak. Boşsa eski davranış (yalnız yerel).
BACKEND_ENV = "EMBEDDING_BACKEND"


def _batch_env() -> int:
    """`EVREN_EMBEDDING_BATCH` — okunamazsa varsayılana düşer, patlamaz."""
    ham = os.environ.get(BATCH_ENV, "").strip()
    if not ham:
        return EVREN_BATCH_VARSAYILAN
    try:
        return max(1, int(ham))
    except ValueError:
        logger.warning("%s okunamadi (%r) -> %d", BATCH_ENV, ham,
                       EVREN_BATCH_VARSAYILAN)
        return EVREN_BATCH_VARSAYILAN


class EvrenEmbedder:
    """SSB EVREN `/v1/embeddings` ucundan bge-m3 gömmeleri.

    Yerel ağırlık ya da `torch` gerektirmez. Model YÜKLENMEZ; `available`
    yalnızca anahtarın varlığına bakar ve ağa çıkmaz.

    ## Taşıma neden `clients.bearer_transport`

    Aynı sunucuya, aynı kimlik doğrulamayla gidiyoruz. İkinci bir HTTP yolu
    yazmak duvar-saati sınırını (`_urllib_transport`'un asılı çağrı koruması)
    ve hata sınıflarını çoğaltır, ikisi de ayrı ayrı bakım ister. Bu yüzden
    LLM katmanının taşıması yeniden kullanılıyor; testler `transport`
    enjekte ederek ağsız koşar.

    ## Boyut neden çağrı başına denetleniyor

    `db/schema.sql` sütunu `vector(1024)`. Sunucu farklı boyutta bir vektör
    döndürürse INSERT Postgres tarafında patlar ya da (SQLite yolunda)
    sessizce yanlış uzayda bir tablo doldurulur. İkisi de teşhisi zor; hata
    kaynağında yükseltilir.
    """

    def __init__(self, base_url: Optional[str] = None,
                 model: Optional[str] = None,
                 api_key: Optional[str] = None,
                 transport=None,
                 batch: Optional[int] = None,
                 timeout: float = 180.0):
        self.base_url = (base_url or os.environ.get("EVREN_URL", "").strip()
                         or EVREN_URL_VARSAYILAN).rstrip("/")
        self.model = (model or os.environ.get("EVREN_EMBEDDING_MODEL", "").strip()
                      or EVREN_MODEL_VARSAYILAN)
        self.api_key = (api_key if api_key is not None
                        else os.environ.get("EVREN_API_KEY", "")).strip()
        self.dim = EMBEDDING_DIM
        self.name = f"evren:{self.model}"
        self.batch = max(1, int(batch if batch is not None
                                else _batch_env()))
        self.timeout = timeout
        self._transport = transport

    @property
    def available(self) -> bool:
        """Anahtar var mı? (Ağa ÇIKMAZ — `BgeM3Embedder.available` ile aynı sözleşme.)"""
        return bool(self.api_key)

    @property
    def endpoint(self) -> str:
        return f"{self.base_url}/v1/embeddings"

    def _tasima(self):
        if self._transport is not None:
            return self._transport
        from ..extraction.llm.clients import bearer_transport
        return bearer_transport(self.api_key)

    def encode(self, texts: Sequence[str]) -> list[list[float]]:
        if not texts:
            return []
        if not self.available:
            raise EmbeddingModelUnavailable(
                "EVREN_API_KEY tanimli degil, EVREN gomme ucu kullanilamaz. "
                "Anahtari kabukta verin (repoya YAZILMAZ) ya da "
                f"{BACKEND_ENV} ile yerel kademeye gecin.")
        tasima = self._tasima()
        cikti: list[list[float]] = []
        for bas in range(0, len(texts), self.batch):
            parca = list(texts[bas:bas + self.batch])
            try:
                ham = tasima(self.endpoint,
                             {"model": self.model, "input": parca}, self.timeout)
            except Exception as exc:                 # ağ/HTTP/JSON — hepsi aynı
                raise EmbeddingModelUnavailable(
                    f"EVREN gomme ucu basarisiz ({self.endpoint}): "
                    f"{type(exc).__name__}: {exc}") from exc
            cikti.extend(self._coz(ham, len(parca)))
        return cikti

    def _coz(self, ham: dict, beklenen: int) -> list[list[float]]:
        """Yanıtı GİRİŞ SIRASINA göre çözer.

        Sıra `index` alanından kurulur; API'nin sırayı koruduğu VARSAYILMAZ.
        Varsayılsa ve API bir gün sırayı değiştirse, vektörler yanlış
        `campaign_id`lere yazılır ve arama sessizce yanlış belge döndürür.
        """
        veri = (ham or {}).get("data")
        if not isinstance(veri, list) or len(veri) != beklenen:
            raise EmbeddingModelUnavailable(
                f"EVREN yanitinda {beklenen} gomme beklendi, "
                f"{len(veri) if isinstance(veri, list) else 'yok'} geldi.")
        sirali = sorted(veri, key=lambda d: d.get("index", 0))
        sonuc: list[list[float]] = []
        for d in sirali:
            v = d.get("embedding")
            if not isinstance(v, list):
                raise EmbeddingModelUnavailable(
                    "EVREN yanitinda `embedding` alani yok ya da liste degil.")
            if len(v) != self.dim:
                raise EmbeddingModelUnavailable(
                    f"EVREN {len(v)} boyutlu vektor dondurdu, beklenen "
                    f"{self.dim} (db/schema.sql: vector({self.dim})). Model "
                    f"{self.model!r} yanlis olabilir.")
            sonuc.append([float(x) for x in v])
        return sonuc


class KademeliEmbedder:
    """Sıralı gömme kademeleri: birincil düşerse sıradaki devralır.

    ## Boyut eşitliği neden KURULUMDA denetleniyor

    Vektör kademesi, LLM kademesinden farklı bir tehlike taşır. İki kademe
    farklı modeller olsaydı vektörleri farklı uzaylarda olurdu; `embeddings`
    tablosu karışık uzaylardan dolar ve arama **sessizce** bozulurdu — hata
    vermez, yalnızca yanlış belge döndürür. Kademe burada güvenlidir çünkü
    her iki kademe de **aynı model**: EVREN'in `bge-m3-embed` ucu ile yerel
    `BAAI/bge-m3` aynı ağırlıklardır.

    Bu güvenliği varsayım olarak bırakmak yerine denetliyoruz: boyutlar eşit
    değilse zincir kurulmaz.
    """

    def __init__(self, kademeler: Sequence[Embedder]):
        kademeler = list(kademeler)
        if not kademeler:
            raise ValueError("KademeliEmbedder bos zincirle kurulamaz")
        boyutlar = {int(k.dim) for k in kademeler}
        if len(boyutlar) > 1:
            raise ValueError(
                f"kademelerin gomme BOYUTLARI ayrisiyor: {sorted(boyutlar)}. "
                "Farkli uzaylardan dolan bir `embeddings` tablosu aramayi "
                "sessizce bozar; zincir kurulmadi.")
        self.kademeler = kademeler
        self.dim = kademeler[0].dim
        self.name = " -> ".join(getattr(k, "name", type(k).__name__)
                                for k in kademeler)
        self.son_hatalar: list[str] = []

    @property
    def available(self) -> bool:
        return any(getattr(k, "available", True) for k in self.kademeler)

    def encode(self, texts: Sequence[str]) -> list[list[float]]:
        if not texts:
            return []
        self.son_hatalar = []
        for k in self.kademeler:
            ad = getattr(k, "name", type(k).__name__)
            try:
                return k.encode(texts)
            except EmbeddingModelUnavailable as exc:
                self.son_hatalar.append(f"{ad}: {exc}")
                logger.warning("gomme kademesi dustu (%s) -> siradaki", ad)
        raise EmbeddingModelUnavailable(
            f"gomme kademelerinin tamami dustu ({len(self.son_hatalar)} kademe): "
            + " | ".join(self.son_hatalar))


def _kademe_kur(ad: str, model_name: Optional[str]):
    """Tek kademe kurar. Anahtarsız `evren` için None döner (atlanır)."""
    if ad == "yerel":
        return BgeM3Embedder(model_name)
    if ad == "evren":
        e = EvrenEmbedder()
        if not e.available:
            logger.info("gomme kademesi atlandi: evren -> EVREN_API_KEY yok")
            return None
        return e
    raise ValueError(
        f"bilinmeyen {BACKEND_ENV} kademesi: {ad!r} (evren|yerel)")


def load_embedder(model_name: Optional[str] = None) -> Embedder:
    """Ortama göre gömme üreticisi (yüklemeyi denemez — tembel).

    `EMBEDDING_BACKEND` virgüllü bir kademe listesi kabul eder:
    `evren,yerel` = "EVREN'i kullan, düşerse yerel bge-m3 devralsın".
    Boşsa eski davranış korunur (yalnız yerel) — mevcut çağrılar ve teslim
    yolu biçim değiştirmez.

    Anahtarsız `evren` kademesi sessizce atlanır: teslim edilen kopyada
    `EVREN_API_KEY` yoktur ve orada yerel kademeye düşmek BEKLENEN davranıştır.
    """
    ham = os.environ.get(BACKEND_ENV, "").strip().lower()
    if not ham:
        return BgeM3Embedder(model_name)
    adlar = [p.strip() for p in ham.split(",") if p.strip()]
    kurulan = [k for k in (_kademe_kur(a, model_name) for a in adlar)
               if k is not None]
    if not kurulan:
        logger.warning("%s=%r ile hicbir kademe kurulamadi -> yerel", BACKEND_ENV, ham)
        return BgeM3Embedder(model_name)
    if len(kurulan) == 1:
        return kurulan[0]
    return KademeliEmbedder(kurulan)
