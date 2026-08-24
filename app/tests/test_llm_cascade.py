"""Kademeli istemci zinciri — uzak uç düşerse yerel yola geçiş.

İlgili: ../src/extraction/llm/cascade.py
        ../src/extraction/llm/clients.py (LLMTransportError / LLMHTTPError ayrımı)
        CLAUDE.md §11 (canlı LLM'e bağlı demo YASAK), §5.9 on-prem

## Neyi koruyor

SSB EVREN uzak bir uçtur ve TÜM takımlarca paylaşılır. Teslim yolunda ona
bağlanmak tek başına kabul edilemez: jüri önünde yavaşlarsa ya da düşerse
arayüz bekler. `CascadingClient` bu yüzden var — EVREN varsa kullanılır,
yoksa/düşerse yerel vLLM veya Ollama devralır, o da yoksa kural-only
(`NullLLMExtractor`, fabrikanın işi) çalışır. Sistemin çalışması hiçbir
zaman uzak uca BAĞLI değildir; uzak uç yalnızca onu iyileştirir.

## Devre kesici neden zorunlu

Düşen istemci her belgede yeniden denenirse 48 belgelik bir koşum 48 kez
duvar-saati sınırını bekler. Ölçülmüş donma riski (bkz. `_urllib_transport`
docstring'i) tam buradan geliyordu. Bu yüzden bir kez düşen istemci
`cooldown` boyunca ATLANIR — denenmez bile.

Saat enjekte edilebilir: cooldown'ın dolmasını gerçek zamanda beklemek
testi yavaşlatır ve kırılgan yapar.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.extraction.llm.cascade import CascadingClient
from src.extraction.llm.clients import (
    LLMHTTPError,
    LLMResponse,
    LLMTransportError,
)

SCHEMA = {"type": "object", "properties": {"a": {"type": "string"}}}


class _Istemci:
    """Sahte istemci: ya hata fırlatır ya sabit yanıt döner; çağrıyı sayar."""

    def __init__(self, ad: str, hata: Exception | None = None,
                 structured_mode: str = "json_schema", max_tokens: int = 1536):
        self.ad = ad
        self.hata = hata
        self.structured_mode = structured_mode
        self.model = f"model-{ad}"
        self.max_tokens = max_tokens
        self.cagri = 0

    def generate(self, system: str, user: str, schema: dict) -> LLMResponse:
        self.cagri += 1
        if self.hata is not None:
            raise self.hata
        return LLMResponse(text='{"a": "%s"}' % self.ad,
                           mode=self.structured_mode, logprobs=[])

    def generate_json(self, system: str, user: str, schema: dict) -> dict:
        self.cagri += 1
        if self.hata is not None:
            raise self.hata
        return {"a": self.ad}

    def negotiate(self, schema: dict, force: bool = False) -> str:
        if self.hata is not None:
            raise self.hata
        return self.structured_mode

    def butceyle(self, token: int) -> "_Istemci":
        y = _Istemci(self.ad, self.hata, self.structured_mode, token)
        return y


class _Saat:
    """Elle ilerletilebilen tekdüze saat."""

    def __init__(self) -> None:
        self.t = 1000.0

    def __call__(self) -> float:
        return self.t

    def ilerlet(self, sn: float) -> None:
        self.t += sn


def _tasima_hatasi(ad: str = "uzak") -> LLMTransportError:
    return LLMTransportError(f"{ad} ulasilamadi")


class GecisTest(unittest.TestCase):
    """Hata türlerine göre sıradaki istemciye geçiş."""

    def test_birincil_calisirsa_ikincil_CAGRILMAZ(self):
        a, b = _Istemci("a"), _Istemci("b")
        c = CascadingClient([a, b])
        self.assertEqual(c.generate("s", "u", SCHEMA).text, '{"a": "a"}')
        self.assertEqual(b.cagri, 0)

    def test_tasima_hatasinda_ikinciye_gecilir(self):
        a, b = _Istemci("a", _tasima_hatasi()), _Istemci("b")
        c = CascadingClient([a, b])
        self.assertEqual(c.generate("s", "u", SCHEMA).text, '{"a": "b"}')
        self.assertEqual(b.cagri, 1)

    def test_http_hatasinda_ikinciye_gecilir(self):
        a = _Istemci("a", LLMHTTPError(503, "mesgul", "http://x"))
        b = _Istemci("b")
        c = CascadingClient([a, b])
        self.assertEqual(c.generate_json("s", "u", SCHEMA), {"a": "b"})

    def test_generate_json_da_zincire_TABI(self):
        a, b = _Istemci("a", _tasima_hatasi()), _Istemci("b")
        c = CascadingClient([a, b])
        self.assertEqual(c.generate_json("s", "u", SCHEMA), {"a": "b"})

    def test_hepsi_duserse_HATA_yukselir(self):
        """Hata TÜRÜ korunur; kademe gerekçeleri `son_hatalar`da durur."""
        a = _Istemci("a", _tasima_hatasi("a"))
        b = _Istemci("b", _tasima_hatasi("b"))
        c = CascadingClient([a, b])
        with self.assertRaises(LLMTransportError):
            c.generate("s", "u", SCHEMA)
        gerekce = " ".join(c.son_hatalar)
        self.assertIn("model-a", gerekce)
        self.assertIn("model-b", gerekce)

    def test_karisik_hata_turleri_SON_hatayi_yukseltir(self):
        a = _Istemci("a", LLMHTTPError(503, "mesgul", "http://x"))
        b = _Istemci("b", _tasima_hatasi("b"))
        c = CascadingClient([a, b])
        with self.assertRaises(LLMTransportError):
            c.generate("s", "u", SCHEMA)
        self.assertEqual(len(c.son_hatalar), 2)

    def test_beklenmeyen_hata_ZINCIRE_TABI_DEGIL(self):
        """Kodlama hatası (ValueError) gizlenmemeli — yükselmeli."""
        a, b = _Istemci("a", ValueError("bozuk sema")), _Istemci("b")
        c = CascadingClient([a, b])
        with self.assertRaises(ValueError):
            c.generate("s", "u", SCHEMA)
        self.assertEqual(b.cagri, 0)


class DevreKesiciTest(unittest.TestCase):
    """Düşen istemci cooldown boyunca ATLANIR."""

    def test_dusen_istemci_ikinci_cagrida_DENENMEZ(self):
        a = _Istemci("a", _tasima_hatasi())
        b = _Istemci("b")
        saat = _Saat()
        c = CascadingClient([a, b], cooldown=300.0, clock=saat)
        c.generate("s", "u", SCHEMA)
        self.assertEqual(a.cagri, 1)
        saat.ilerlet(10.0)
        c.generate("s", "u", SCHEMA)
        self.assertEqual(a.cagri, 1)          # atlandı, yeniden denenmedi
        self.assertEqual(b.cagri, 2)

    def test_cooldown_dolunca_YENIDEN_denenir(self):
        a = _Istemci("a", _tasima_hatasi())
        b = _Istemci("b")
        saat = _Saat()
        c = CascadingClient([a, b], cooldown=300.0, clock=saat)
        c.generate("s", "u", SCHEMA)
        saat.ilerlet(301.0)
        c.generate("s", "u", SCHEMA)
        self.assertEqual(a.cagri, 2)

    def test_hepsi_cooldownda_ise_gene_DENENIR(self):
        """Zincirde denenecek kimse kalmazsa körlemesine beklemek yerine dene.

        Aksi hâlde tek istemcili bir zincir ilk hatadan sonra cooldown
        boyunca HİÇ çağrı yapmaz ve sistem sessizce ölür.
        """
        a = _Istemci("a", _tasima_hatasi())
        saat = _Saat()
        c = CascadingClient([a], cooldown=300.0, clock=saat)
        with self.assertRaises(LLMTransportError):
            c.generate("s", "u", SCHEMA)
        saat.ilerlet(1.0)
        with self.assertRaises(LLMTransportError):
            c.generate("s", "u", SCHEMA)
        self.assertEqual(a.cagri, 2)

    def test_basarili_cagri_devreyi_ACIK_TUTAR(self):
        a, b = _Istemci("a"), _Istemci("b")
        saat = _Saat()
        c = CascadingClient([a, b], cooldown=300.0, clock=saat)
        for _ in range(3):
            c.generate("s", "u", SCHEMA)
        self.assertEqual(a.cagri, 3)
        self.assertEqual(b.cagri, 0)


class ArayuzTest(unittest.TestCase):
    """Zincir, tek bir istemci gibi davranmalı (LLMExtractor bunu bekler)."""

    def test_structured_mode_aktif_istemciden_okunur(self):
        a = _Istemci("a", _tasima_hatasi(), structured_mode="json_schema")
        b = _Istemci("b", structured_mode="prompt_only")
        c = CascadingClient([a, b])
        c.generate("s", "u", SCHEMA)
        self.assertEqual(c.structured_mode, "prompt_only")

    def test_model_adi_aktif_istemciden_okunur(self):
        a = _Istemci("a", _tasima_hatasi())
        b = _Istemci("b")
        c = CascadingClient([a, b])
        c.generate("s", "u", SCHEMA)
        self.assertEqual(c.model, "model-b")

    def test_butceyle_ZINCIRI_korur(self):
        a, b = _Istemci("a"), _Istemci("b")
        c = CascadingClient([a, b])
        k = c.butceyle(256)
        self.assertIsInstance(k, CascadingClient)
        self.assertEqual([i.max_tokens for i in k.clients], [256, 256])

    def test_butceyle_DEVRE_DURUMUNU_paylasir(self):
        """Kopya düşen istemciyi yeniden denememeli (bkz. dosya başlığı)."""
        a = _Istemci("a", _tasima_hatasi())
        b = _Istemci("b")
        saat = _Saat()
        c = CascadingClient([a, b], cooldown=300.0, clock=saat)
        c.generate("s", "u", SCHEMA)
        self.assertEqual(a.cagri, 1)
        k = c.butceyle(256)
        k.generate("s", "u", SCHEMA)
        self.assertEqual(k.clients[0].cagri, 0)   # kopya birincili denemedi

    def test_bos_zincir_REDDEDILIR(self):
        with self.assertRaises(ValueError):
            CascadingClient([])

    def test_negotiate_zincire_TABI(self):
        a = _Istemci("a", _tasima_hatasi())
        b = _Istemci("b", structured_mode="guided_json")
        c = CascadingClient([a, b])
        self.assertEqual(c.negotiate(SCHEMA), "guided_json")


if __name__ == "__main__":
    unittest.main()
