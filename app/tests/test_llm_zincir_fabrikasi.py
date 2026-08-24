"""`LLM_BACKEND` zinciri — hangi kademeler kurulur, hangileri atlanır.

İlgili: ../src/extraction/llm/extractor.py (`default_extractor`)
        ../src/extraction/llm/cascade.py
        docs/evren-servisi.md

## Sözleşme

`LLM_BACKEND` virgülle ayrılmış bir KADEME LİSTESİ kabul eder:
`evren,ollama` = "EVREN'i dene, düşerse yerel Ollama". Tek değer eski
davranıştır ve zincire sarılmaz — `evren` gibi tek kademeli bir kurulum
doğrudan istemciyi verir, böylece mevcut raporlar (`client` alanı, model adı)
biçim değiştirmez.

## Anahtarsız `evren` kademesi SESSİZCE atlanır

Teslim edilen kopyada `EVREN_API_KEY` bulunmaz (repoya girmez, bkz. §5.10).
O kopyada zincir kendiliğinden yerel kademeye düşmelidir; "anahtar yok" bir
kurulum hatası DEĞİL, beklenen durumdur. Ama zincirde başka kademe de yoksa
bu artık gerçek bir kurulum hatasıdır ve `LLM_STRICT` altında yükselir —
aksi hâlde "EVREN ile koştum" sanılan bir koşum sessizce kural-only olur ve
jüriye yanlış tablo gider.

Hiçbir test ağa çıkmaz: istemci kurulumu tembeldir (pazarlık ilk `generate`
çağrısında koşar), bu yüzden nesneleri kurmak güvenlidir.
"""

from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.extraction.llm.extractor import (
    LLMExtractionError,
    NullLLMExtractor,
    default_extractor,
)

ANAHTAR = "sk-test-evren-0000"

def _tur(nesne) -> str:
    """Kurulan nesnenin sınıfının TAM adı — `isinstance` yerine bu.

    Gerekçe `tests/test_gezinme_seridi.py::TestTekDogrulukKaynagi` ile birebir
    aynı ve ölçülmüştür: `test_properties.py` ile `test_api_startup.py`
    bilinçli olarak `sys.modules`ten tüm `src.*` modüllerini düşürüyor. Aynı
    koşumda bu dosyanın modül düzeyinde tuttuğu sınıf nesnesiyle fabrikanın
    sonradan içe aktardığı nesne FARKLI olur ve `assertIsInstance` sahte bir
    kırmızı verir (tam paket koşumunda görüldü, izole koşumda görülmedi).

    Korunması gereken şey nesne kimliği değil, KURULAN SINIFIN HANGİ TANIM
    olduğudur.
    """
    t = type(nesne)
    return f"{t.__module__}.{t.__qualname__}"


VLLM = "src.extraction.llm.clients.VLLMClient"
OLLAMA = "src.extraction.llm.clients.OllamaClient"
ZINCIR = "src.extraction.llm.cascade.CascadingClient"



def _ortam(**kw) -> dict:
    """Zincirle ilgili tüm değişkenleri sıfırlayıp verilenleri koyar."""
    taban = {"LLM_BACKEND": "", "LLM_STRICT": "", "EVREN_API_KEY": "",
             "EVREN_URL": "", "EVREN_MODEL": "", "VLLM_API_KEY": ""}
    taban.update(kw)
    return taban


class ZincirKurulumuTest(unittest.TestCase):

    def test_iki_kademe_zincire_sarilir(self):
        with mock.patch.dict(os.environ,
                             _ortam(LLM_BACKEND="evren,ollama",
                                    EVREN_API_KEY=ANAHTAR)):
            ex = default_extractor()
        self.assertEqual(_tur(ex.client), ZINCIR)
        self.assertEqual(len(ex.client.clients), 2)
        self.assertEqual(_tur(ex.client.clients[0]), VLLM)
        self.assertEqual(_tur(ex.client.clients[1]), OLLAMA)

    def test_evren_kademesi_anahtari_ve_ucu_kullanir(self):
        with mock.patch.dict(os.environ,
                             _ortam(LLM_BACKEND="evren",
                                    EVREN_API_KEY=ANAHTAR,
                                    EVREN_URL="https://ornek.invalid",
                                    EVREN_MODEL="llm-large")):
            ex = default_extractor()
        self.assertEqual(_tur(ex.client), VLLM)
        self.assertEqual(ex.client.api_key, ANAHTAR)
        self.assertEqual(ex.client.base_url, "https://ornek.invalid")
        self.assertEqual(ex.client.model, "llm-large")

    def test_tek_kademe_zincire_SARILMAZ(self):
        """Eski davranış korunur: raporlardaki `client` alanı biçim değiştirmez."""
        with mock.patch.dict(os.environ, _ortam(LLM_BACKEND="vllm")):
            ex = default_extractor()
        self.assertEqual(_tur(ex.client), VLLM)

    def test_bosluklu_liste_tolere_edilir(self):
        with mock.patch.dict(os.environ,
                             _ortam(LLM_BACKEND=" evren , ollama ",
                                    EVREN_API_KEY=ANAHTAR)):
            ex = default_extractor()
        self.assertEqual(len(ex.client.clients), 2)

    def test_uc_kademe(self):
        with mock.patch.dict(os.environ,
                             _ortam(LLM_BACKEND="evren,vllm,ollama",
                                    EVREN_API_KEY=ANAHTAR)):
            ex = default_extractor()
        self.assertEqual(len(ex.client.clients), 3)


class AnahtarsizEvrenTest(unittest.TestCase):
    """Anahtar yoksa kademe atlanır; zincirde başkası varsa koşum sürer."""

    def test_anahtarsiz_evren_ATLANIR_yerel_devralir(self):
        with mock.patch.dict(os.environ, _ortam(LLM_BACKEND="evren,ollama")):
            ex = default_extractor()
        self.assertEqual(_tur(ex.client), OLLAMA)

    def test_anahtarsiz_TEK_evren_hosgorulu_modda_NULL(self):
        with mock.patch.dict(os.environ, _ortam(LLM_BACKEND="evren")):
            ex = default_extractor()
        self.assertIsInstance(ex, NullLLMExtractor)

    def test_anahtarsiz_TEK_evren_KATI_modda_yukselir(self):
        with mock.patch.dict(os.environ,
                             _ortam(LLM_BACKEND="evren", LLM_STRICT="1")):
            with self.assertRaises(LLMExtractionError):
                default_extractor()


class GeriyeUyumTest(unittest.TestCase):
    """Mevcut sözleşmeler bozulmamalı."""

    def test_bos_backend_NULL(self):
        with mock.patch.dict(os.environ, _ortam()):
            self.assertIsInstance(default_extractor(), NullLLMExtractor)

    def test_bilinmeyen_ad_KATI_modda_yukselir(self):
        with mock.patch.dict(os.environ,
                             _ortam(LLM_BACKEND="openai", LLM_STRICT="1")):
            with self.assertRaises(LLMExtractionError):
                default_extractor()

    def test_zincirdeki_bilinmeyen_ad_KATI_modda_yukselir(self):
        with mock.patch.dict(os.environ,
                             _ortam(LLM_BACKEND="ollama,openai",
                                    LLM_STRICT="1")):
            with self.assertRaises(LLMExtractionError):
                default_extractor()


if __name__ == "__main__":
    unittest.main()
