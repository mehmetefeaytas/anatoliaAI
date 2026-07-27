"""8-sınıf kampanya türü sınıflandırıcı.

İlgili: ../../../decisions/ner-fine-tune-yerine-kural-few-shot.md
        ../../../concepts/kampanya-turleri.md  ../../../concepts/metin-siniflandirma.md
        CLAUDE.md §4 (fine-tune YALNIZ bu sınıflandırma için)

İki yol:
- RuleHintClassifier: anahtar-kelime ipuçlu, sıfır bağımlılık, offline fallback.
- BerturkClassifier: fine-tune edilmiş BERTurk (transformers). Model yoksa
  otomatik olarak RuleHint'e düşülür.
"""

from __future__ import annotations

from typing import Optional, Protocol

from ...preprocessing.clean import tr_fold_ascii
from ...schemas import CAMPAIGN_TYPES
from ..rules.synonyms import FOLDED_TYPE_HINTS


class Classifier(Protocol):
    def classify(self, text: str) -> tuple[Optional[str], float]: ...


class RuleHintClassifier:
    """Anahtar-kelime ipuçlarıyla sınıflandırma (zayıf etiket / fallback).

    En spesifik tür önce eşleşir; 'Finansman'/'Kart' gibi genel türler en sona
    bırakılır. Hiç ipucu yoksa (None, 0.0) döner — uydurma yok.
    """

    # Genel türleri sona iten değerlendirme sırası
    _ORDER = [
        "Konut Finansmanı", "Taşıt Finansmanı", "İhtiyaç Finansmanı",
        "Alışveriş Puanı", "Yeni Müşteri", "Yatırım Ürünü", "Kart", "Finansman",
    ]

    def classify(self, text: str) -> tuple[Optional[str], float]:
        # TR-doğru katlama: ALL-CAPS başlıklar ve diakritiksiz yazımlar da eşleşir.
        # Düz .lower() burada 'TAŞIT' -> 'taşit' üretip eşleşmeyi kaçırıyordu.
        low = tr_fold_ascii(text)
        scores: dict[str, int] = {}
        for label in self._ORDER:
            hits = sum(1 for kw in FOLDED_TYPE_HINTS.get(label, frozenset())
                       if kw in low)
            if hits:
                scores[label] = hits
        if not scores:
            return None, 0.0
        # en spesifik (sıra önceliği) + en çok eşleşen
        best = max(scores, key=lambda l: (scores[l], -self._ORDER.index(l)))
        # güven: eşleşme yoğunluğuna göre kaba [0.5, 0.9]
        conf = min(0.9, 0.5 + 0.1 * scores[best])
        return best, conf


class BerturkClassifier:
    """Fine-tune BERTurk yolu. Model yüklenemezse RuleHint'e düşer.

    model_dir: kaydedilmiş HuggingFace modeli (offline, Apache-2.0 BERTurk).
    """

    def __init__(self, model_dir: Optional[str] = None):
        self._pipe = None
        self._fallback = RuleHintClassifier()
        try:
            import os
            md = model_dir or os.environ.get("BERTURK_MODEL_DIR")
            if md and os.path.isdir(md):
                from transformers import pipeline  # type: ignore
                self._pipe = pipeline("text-classification", model=md, top_k=1)
        except Exception:
            self._pipe = None

    @property
    def available(self) -> bool:
        return self._pipe is not None

    def classify(self, text: str) -> tuple[Optional[str], float]:
        if self._pipe is None:
            return self._fallback.classify(text)
        try:
            res = self._pipe(text[:512])
            top = res[0][0] if isinstance(res[0], list) else res[0]
            label = top["label"]
            # model etiketi geçerli türe eşlenir; değilse fallback
            if label not in CAMPAIGN_TYPES:
                return self._fallback.classify(text)
            return label, float(top["score"])
        except Exception:
            return self._fallback.classify(text)


def default_classifier() -> Classifier:
    """Ortama göre sınıflandırıcı (model varsa BERTurk, yoksa kural-ipucu)."""
    clf = BerturkClassifier()
    return clf if clf.available else RuleHintClassifier()
