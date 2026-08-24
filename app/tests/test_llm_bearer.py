"""Bearer başlıklı taşıma — uzak OpenAI-uyumlu uçlar (EVREN) için.

İlgili: ../src/extraction/llm/clients.py (`bearer_transport`, `VLLMClient`)
        CLAUDE.md §19 (modülerlik), §20 (repoda API anahtarı YOK)

## Bu dosya neyi koruyor

Yerel vLLM/Ollama kimlik doğrulaması İSTEMEZ; uzak bir vLLM ucu (SSB EVREN)
`Authorization: Bearer` İSTER. Aynı `VLLMClient` ikisini de konuşmak zorunda:
başlık **yalnızca anahtar verildiğinde** eklenir. Aksi hâlde localhost'a
gereksiz bir başlık gider ve geriye uyum bozulur.

İkinci sözleşme: `transport` AÇIKÇA enjekte edildiğinde anahtar onu EZMEZ.
Bütün mevcut testler sahte taşıma ile koşuyor; anahtar bir env değişkeninde
duruyor olsa bile (geliştirici makinesinde durabilir) o testlerin ağa
çıkmaması gerekir.

Hiçbir test ağa bağlanmaz: `urllib.request.urlopen` mock'lanır.
"""

from __future__ import annotations

import io
import json
import os
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.extraction.llm.clients import (
    VLLMClient,
    bearer_transport,
)


class _SahteYanit(io.BytesIO):
    """`urlopen` bağlam yöneticisi taklidi."""

    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.close()
        return False


def _yakala() -> tuple[mock.MagicMock, list]:
    """`urlopen`'ı mock'lar; yakalanan `Request` nesnelerini toplar."""
    istekler: list = []

    def _fake_urlopen(req, timeout=None):
        istekler.append(req)
        return _SahteYanit(json.dumps({"choices": []}).encode("utf-8"))

    return mock.patch("urllib.request.urlopen", _fake_urlopen), istekler


class BearerTransportTest(unittest.TestCase):
    """`bearer_transport` başlığı ekler; boş anahtar eklemez."""

    def test_anahtar_verilince_authorization_gider(self):
        yama, istekler = _yakala()
        with yama:
            bearer_transport("sk-test-123")("http://x/v1/chat", {"a": 1}, 5.0)
        self.assertEqual(len(istekler), 1)
        self.assertEqual(istekler[0].get_header("Authorization"),
                         "Bearer sk-test-123")

    def test_content_type_korunur(self):
        yama, istekler = _yakala()
        with yama:
            bearer_transport("sk-test-123")("http://x/v1/chat", {"a": 1}, 5.0)
        self.assertEqual(istekler[0].get_header("Content-type"),
                         "application/json")

    def test_bos_anahtar_authorization_EKLEMEZ(self):
        """Yerel vLLM/Ollama geriye uyumu: başlık hiç gitmemeli."""
        yama, istekler = _yakala()
        with yama:
            bearer_transport("")("http://localhost:8001/v1/chat", {"a": 1}, 5.0)
        self.assertIsNone(istekler[0].get_header("Authorization"))


class VLLMClientAnahtarTest(unittest.TestCase):
    """İstemci anahtarı env'den ya da argümandan alır; enjeksiyonu ezmez."""

    def setUp(self):
        self._eski = os.environ.pop("VLLM_API_KEY", None)

    def tearDown(self):
        os.environ.pop("VLLM_API_KEY", None)
        if self._eski is not None:
            os.environ["VLLM_API_KEY"] = self._eski

    def test_argumanla_verilen_anahtar_istege_girer(self):
        c = VLLMClient(base_url="https://uzak/", model="llm-large",
                       api_key="sk-arg")
        yama, istekler = _yakala()
        with yama:
            c.transport(c.endpoint, {"a": 1}, 5.0)
        self.assertEqual(istekler[0].get_header("Authorization"), "Bearer sk-arg")

    def test_env_anahtari_okunur(self):
        os.environ["VLLM_API_KEY"] = "sk-env"
        c = VLLMClient(base_url="https://uzak/", model="llm-large")
        yama, istekler = _yakala()
        with yama:
            c.transport(c.endpoint, {"a": 1}, 5.0)
        self.assertEqual(istekler[0].get_header("Authorization"), "Bearer sk-env")

    def test_anahtar_yoksa_varsayilan_tasima_degismez(self):
        """Kimlik değil TANIM YERİ karşılaştırılır.

        `test_properties.py` / `test_api_startup.py` koşumda `sys.modules`ten
        `src.*`ı düşürüyor; modül düzeyinde tutulan fonksiyon nesnesi o
        koşumda tazesinden farklı olur ve `assertIs` sahte kırmızı verir
        (bkz. `test_gezinme_seridi.py::TestTekDogrulukKaynagi`).
        """
        c = VLLMClient(base_url="http://localhost:8001")
        self.assertEqual(c.transport.__module__,
                         "src.extraction.llm.clients")
        self.assertEqual(c.transport.__qualname__, "_urllib_transport")

    def test_acik_transport_anahtardan_GUCLU(self):
        """Enjekte edilmiş sahte taşıma her koşulda kazanır (ağsız CI şartı)."""
        os.environ["VLLM_API_KEY"] = "sk-env"
        cagrildi: list = []

        def sahte(url, payload, timeout):
            cagrildi.append(url)
            return {"choices": []}

        c = VLLMClient(base_url="https://uzak/", transport=sahte)
        self.assertIs(c.transport, sahte)
        c.transport(c.endpoint, {}, 1.0)
        self.assertEqual(len(cagrildi), 1)


if __name__ == "__main__":
    unittest.main()
