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
"""

from __future__ import annotations

import os
from typing import Optional, Protocol, Sequence

# bge-m3 yoğun (dense) vektör boyutu. `db/schema.sql`'deki vector(1024) ile
# AYNI olmak ZORUNDA; ayrışırlarsa INSERT Postgres tarafında patlar.
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


def load_embedder(model_name: Optional[str] = None) -> BgeM3Embedder:
    """Varsayılan gömme üreticisi (yüklemeyi denemez — tembel)."""
    return BgeM3Embedder(model_name)
