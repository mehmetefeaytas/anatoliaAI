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

import logging
import os
from typing import Optional, Protocol

from ...preprocessing.clean import tr_fold_ascii
from ...schemas import CAMPAIGN_TYPES
from ..rules.synonyms import FOLDED_TYPE_HINTS, matches

logger = logging.getLogger(__name__)


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
            # SÖZCÜK SINIRLI eşleşme (bkz. synonyms.keyword_pattern). Düz
            # alt-dize araması 'ev' anahtarını 'devam'/'seviye' içinde
            # buluyordu ve gerçek korpusun %48'ini sahte Konut Finansmanı
            # yapıyordu.
            hits = sum(1 for kw in FOLDED_TYPE_HINTS.get(label, frozenset())
                       if matches(kw, low))
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

    model_dir: kaydedilmiş HuggingFace modeli (offline, **MIT** BERTurk).

    Lisans doğrulandı (2026-08-07): `dbmdz/bert-base-turkish-cased`
    `cardData.license = "mit"`, `base_model` beyanı YOK — zincirin kökü,
    yani "türev kökünden serbest olamaz" tuzağı oluşmuyor. Kaynak:
    https://huggingface.co/api/models/dbmdz/bert-base-turkish-cased
    Bu satır eskiden "Apache-2.0" diyordu; ikisi de izinli listede
    (CLAUDE.md §7) ama yanlış lisans beyanı uyumluluk iddiasını çürütür.
    """

    def __init__(self, model_dir: Optional[str] = None):
        self._pipe = None
        self._fallback = RuleHintClassifier()
        self._calisma_zamani_hatasi_loglandi = False

        # Geri düşüş (fallback) DAVRANIŞI kasıtlı: çevrimdışı demoda ağırlık
        # yoksa sistem çökmemeli, kural katmanıyla çalışmalı. Ama SESSİZ geri
        # düşüş kusurluydu: model beklerken kural koşuyorsa çıktıyı okuyan
        # kişi hangi kolun ölçüldüğünü bilemez ve "BERTurk sonucu" sanılan
        # sayı aslında kural sonucudur. Davranış aynı kaldı, görünürlük eklendi.
        md = model_dir or os.environ.get("BERTURK_MODEL_DIR")
        if not md:
            logger.info(
                "BERTURK_MODEL_DIR tanımsız -> RuleHintClassifier "
                "(kural-ipucu, kasıtlı offline varsayılan)")
            return
        if not os.path.isdir(md):
            logger.warning(
                "BERTurk model dizini YOK: %r -> RuleHintClassifier'a "
                "düşülüyor. Model bekleniyorsa ölçülen kol KURAL'dır.", md)
            return
        try:
            from transformers import pipeline  # type: ignore
            # `local_files_only=True` KOŞULSUZ: `md` yukarıda `os.path.isdir`
            # ile doğrulanmış YEREL bir dizin, dolayısıyla hub'a çıkmak için
            # hiçbir meşru sebep yok. Bayrak olmadan `transformers`, eksik bir
            # yardımcı dosya için (tokenizer, config) **sessizce ağa çıkar** —
            # çevrimdışı makinede bu, yükleme anında değil ÇALIŞMA ANINDA
            # patlar. `src/rag/embedding.py:102` aynı korumayı zaten
            # uyguluyordu; burada atlanmıştı.
            #
            # Konteynerde `HF_HUB_OFFLINE=1` + `TRANSFORMERS_OFFLINE=1` bunu
            # ayrıca zorluyor (`Dockerfile.api`), ama kod konteyner dışında da
            # koşuyor ve doğruluğu ortam değişkenine bağlı olmamalı.
            self._pipe = pipeline("text-classification", model=md, top_k=1,
                                  model_kwargs={"local_files_only": True})
            logger.info("BERTurk yüklendi: %s", md)
        except Exception as exc:
            # Geniş yakalama bilinçli: eksik `transformers`, bozuk ağırlık,
            # uyumsuz sürüm — hepsinde kural katmanı çalışmaya devam etmeli.
            self._pipe = None
            logger.warning(
                "BERTurk yüklenemedi (%s: %s) -> RuleHintClassifier'a "
                "düşülüyor. Dizin: %r", type(exc).__name__, exc, md)

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
                logger.warning(
                    "BERTurk taksonomi dışı etiket üretti: %r -> "
                    "RuleHintClassifier. Model `id2label` haritası "
                    "CAMPAIGN_TYPES ile uyumlu mu?", label)
                return self._fallback.classify(text)
            return label, float(top["score"])
        except Exception as exc:
            # Belge başına log basmamak için yalnız İLK hata uyarı seviyesinde.
            if not self._calisma_zamani_hatasi_loglandi:
                self._calisma_zamani_hatasi_loglandi = True
                logger.warning(
                    "BERTurk çıkarımı başarısız (%s: %s) -> "
                    "RuleHintClassifier. Sonraki hatalar debug seviyesinde.",
                    type(exc).__name__, exc)
            else:
                logger.debug("BERTurk çıkarımı başarısız (%s): %s",
                             type(exc).__name__, exc)
            return self._fallback.classify(text)


def default_classifier() -> Classifier:
    """Ortama göre sınıflandırıcı (model varsa BERTurk, yoksa kural-ipucu)."""
    clf = BerturkClassifier()
    return clf if clf.available else RuleHintClassifier()
