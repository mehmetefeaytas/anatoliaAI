"""Tahmin üreticileri (predictors) — konfig adı → tahmin fonksiyonu TEK KAYNAĞI.

İlgili: ../../decisions/ner-fine-tune-yerine-kural-few-shot.md
        ../../syntheses/teslim-ve-degerlendirme-rehberi.md
        src/extraction/reconcile.py (hibrit hat)

## Neden bu modül var — iki ayrı kusurun tek kökü

**Kusur 1: `run_eval.py` teslim ettiğimiz sistemi ölçmüyordu.** Eski
`run_eval.py` yalnızca `extract_all` (kural katmanı) çağırıyordu; hibrit hat
(`reconcile()`) sadece `ablation.py`'de vardı. Yani "resmî" P/R/F1 rakamımız
teslim ettiğimiz sistemin rakamı DEĞİLDİ. Tablo başlığı bunu itiraf ediyordu:
`"KURAL KATMANI — TÜM VAKALAR"`.

**Kusur 2: iki harness aynı tahmin kümesini üretmiyordu.** `run_eval.py`
`preds[name] is not None` filtresi kullanıyordu, `ablation.py` ise
`f.is_present`. İkisi bugün aynı şeyi söylüyor (`is_present` tanımı
`canonical_value is not None`) ama bu bir TESADÜFtür: `is_present`
tanımı değişirse iki harness sessizce ayrışır ve sayıları kıyaslanamaz hale
gelir. Kıyaslanamaz iki sayıyı aynı rapora koymak, jüriye yanlış bilgi
vermektir.

Çözüm: mevcudiyet (`is_present`) semantiği TEK yerde tanımlanır
(`field_values()`), tüm konfigürasyonlar TEK kayıttan (`build_predictor`) gelir
ve `run_eval` ile `ablation` ikisi de buradan beslenir.

## Offline dürüstlüğü

LLM yoksa `llm`, `hibrit` ve `hibrit-verify` konfigleri `available=False`
döner ve çağıranlar bunları ATLAR. "hibrit = kural" satırı BASILMAZ: bu satır
teknik olarak doğru ama iletişim olarak yalandır — okuyucu hibridin ölçüldüğünü
sanır. `unavailable_reason` neden atlandığını Türkçe söyler.
"""

from __future__ import annotations

import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.extraction.llm.extractor import (
    LLMExtractor,
    NullLLMExtractor,
    default_extractor,
)
from src.extraction.reconcile import reconcile
from src.extraction.rules.extract import extract_all
from src.schemas import ExtractedField

# Konfig adları — CLI `--config` ile birebir aynı.
CONFIG_KURAL = "kural"
CONFIG_LLM = "llm"
CONFIG_HIBRIT = "hibrit"
CONFIG_HIBRIT_VERIFY = "hibrit-verify"

CONFIG_NAMES = (CONFIG_KURAL, CONFIG_LLM, CONFIG_HIBRIT, CONFIG_HIBRIT_VERIFY)

# Teslim edilen sistem: dashboard ve API `reconcile()` çağırır, dolayısıyla
# "resmî" metriğin varsayılanı da bu olmalıdır.
DEFAULT_CONFIG = CONFIG_HIBRIT

CONFIG_DESCRIPTIONS: dict[str, str] = {
    CONFIG_KURAL: "yalnız kural katmanı (regex + normalizasyon), LLM kapalı",
    CONFIG_LLM: "yalnız LLM katmanı (kısıtlı decoding), kural kapalı",
    CONFIG_HIBRIT: "kural birincil + eksikleri LLM doldurur (TESLİM EDİLEN SİSTEM)",
    CONFIG_HIBRIT_VERIFY: ("hibrit + düşük güvenli KURAL alanlarını LLM doğrular "
                           "(reconcile.verify_low_conf)"),
}

# `hibrit-verify` kolunun eşiği. 0,75 seçildi çünkü kural katmanının güven
# skorları (`rules/confidence.py`) tetikleyici uzaklığı / aday sayısı / makul
# aralık cezalarıyla üretilir; bu eşiğin altı "regex emin değil" bölgesidir.
DEFAULT_VERIFY_THRESHOLD = 0.75


class PredictorError(ValueError):
    """Bilinmeyen konfigürasyon adı."""


# --------------------------------------------------------------------------- #
# MEVCUDİYET SEMANTİĞİ — tek tanım noktası
# --------------------------------------------------------------------------- #
def is_present(f: ExtractedField) -> bool:
    """Bir alan "üretildi" sayılır mı?

    Tek tanım noktası. `ExtractedField.is_present`e delege eder ki semantik
    şemayla birlikte hareket etsin; ama tüm harness'lar BU fonksiyonu çağırır,
    böylece `run_eval` ile `ablation` arasında filtre ayrışması imkânsız olur
    (bkz. modül başlığı, Kusur 2).
    """
    return f.is_present


def field_values(fields: list[ExtractedField]) -> dict[str, Any]:
    """`ExtractedField` listesini `alan adı -> kanonik değer` sözlüğüne indirir.

    Yalnız `is_present()` olan alanlar girer. Aynı alan iki kez gelirse GÜVENİ
    yüksek olan kazanır — `extract_all` bugün tekrar üretmiyor ama
    `reconcile` + LLM birleşiminde teorik olarak mümkündür ve sessizce
    "sözlükte son yazan kazanır" davranışına bırakmak, sıraya bağlı ölçüm
    demektir.
    """
    out: dict[str, Any] = {}
    best: dict[str, float] = {}
    for f in fields:
        if not is_present(f):
            continue
        if f.field_name not in out or f.confidence > best[f.field_name]:
            out[f.field_name] = f.canonical_value
            best[f.field_name] = f.confidence
    return out


# --------------------------------------------------------------------------- #
# Predictor
# --------------------------------------------------------------------------- #
@dataclass
class Predictor:
    """Tek bir değerlendirme konfigürasyonu.

    name: CLI'daki konfig adı.
    fn: metin -> `ExtractedField` listesi.
    available: koşturulabilir mi (LLM gerekiyorsa ve yoksa False).
    unavailable_reason: neden koşturulamadığının TÜRKÇE açıklaması.
    """

    name: str
    description: str
    fn: Callable[[str], list[ExtractedField]]
    available: bool = True
    unavailable_reason: str | None = None
    llm: LLMExtractor | None = None

    @property
    def llm_summary(self) -> dict | None:
        """LLM sayaçlarının **o anki** hâli (çağrı sayısı, hata sayısı).

        Neden özellik (property), neden saklanan bir sözlük DEĞİL: eski kod
        `build_predictor` içinde `active.summary()` çağırıp sonucu bir alanda
        dondurur ve raporlar bu donmuş kopyayı yazardı. Sayaçlar koşum
        SIRASINDA artığı için rapora her zaman `calls: 0, ok: 0` düşerdi —
        yani "LLM gerçekten çağrıldı mı?" sorusu, LLM 60 kez çağrılmış olsa
        bile cevapsız kalırdı. Bu tam olarak `hibrit` kolunun sessizce
        kural-only koşup koşmadığını anlamak için var olan sayaçtı.

        Artık okuma anında canlı çıkarıcıdan alınır; künye yazımı koşumdan
        SONRA yapıldığı için rapora gerçek sayılar girer.
        """
        return self.llm.summary() if self.llm is not None else None

    def fields(self, text: str) -> list[ExtractedField]:
        """Ham alan listesi (span/güven bilgisi korunur)."""
        if not self.available:
            raise PredictorError(
                f"{self.name}: {self.unavailable_reason or 'kullanılamaz'}")
        return self.fn(text)

    def predict(self, text: str) -> dict[str, Any]:
        """Metrik hattının kullandığı `alan -> kanonik değer` sözlüğü."""
        return field_values(self.fields(text))


# --------------------------------------------------------------------------- #
# Konfig kurucular
# --------------------------------------------------------------------------- #
def _rule_only(text: str) -> list[ExtractedField]:
    return list(extract_all(text))


def build_predictor(config: str, llm: LLMExtractor | None = None, *,
                    verify_threshold: float = DEFAULT_VERIFY_THRESHOLD) -> Predictor:
    """Konfig adından `Predictor` üretir — TEK giriş noktası.

    Args:
        config: `CONFIG_NAMES` içinden bir ad.
        llm: kullanılacak LLM çıkarıcı. `None` ise ortamdan kurulur
            (`LLM_BACKEND` boşsa `NullLLMExtractor`, yani offline).
        verify_threshold: `hibrit-verify` kolunun güven eşiği.

    Raises:
        PredictorError: konfig adı tanınmıyorsa.
    """
    if config not in CONFIG_NAMES:
        raise PredictorError(
            f"bilinmeyen konfig {config!r}. Seçenekler: {', '.join(CONFIG_NAMES)}")

    if config == CONFIG_KURAL:
        # Kural katmanı LLM'e hiç dokunmaz: offline'da da tam ölçülür.
        return Predictor(CONFIG_KURAL, CONFIG_DESCRIPTIONS[CONFIG_KURAL], _rule_only)

    active = llm if llm is not None else default_extractor()

    if not active.available:
        return Predictor(
            config, CONFIG_DESCRIPTIONS[config],
            fn=lambda _t: [],
            available=False,
            unavailable_reason=(
                "LLM backend kapalı (offline). Bu konfig ÖLÇÜLMEDİ — sahte bir "
                "'hibrit = kural' satırı üretmemek için atlandı. Ölçmek için: "
                "LLM_BACKEND=vllm|ollama (ve tercihen LLM_STRICT=1)."),
            llm=active,
        )

    if config == CONFIG_LLM:
        fn: Callable[[str], list[ExtractedField]] = lambda t: list(active.extract(t))
    elif config == CONFIG_HIBRIT:
        fn = lambda t: list(reconcile(t, llm=active))
    else:  # CONFIG_HIBRIT_VERIFY
        fn = lambda t: list(reconcile(t, llm=active,
                                      verify_low_conf=verify_threshold))

    desc = CONFIG_DESCRIPTIONS[config]
    if config == CONFIG_HIBRIT_VERIFY:
        desc = f"{desc} (eşik={verify_threshold})"
    return Predictor(config, desc, fn, llm=active)


def build_all(configs: list[str], llm: LLMExtractor | None = None, *,
              verify_threshold: float = DEFAULT_VERIFY_THRESHOLD
              ) -> list[Predictor]:
    """Birden çok konfigi TEK LLM örneğiyle kurar.

    Tek örnek olması önemlidir: `llm.stats` sayaçları tüm ablasyon kolları
    üzerinden toplanır ve "LLM gerçekten çağrıldı mı, kaç kez patladı" sorusu
    raporda tek satırla cevaplanır.
    """
    active = llm if llm is not None else default_extractor()
    return [build_predictor(c, llm=active, verify_threshold=verify_threshold)
            for c in configs]


def offline_llm() -> LLMExtractor:
    """Testlerin ve kasıtlı offline koşumların kullandığı boş çıkarıcı."""
    return NullLLMExtractor()
