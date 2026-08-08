"""Çıktı token sınırı + kapanmamış dizge onarımı.

İlgili: src/extraction/llm/clients.py (`num_predict`, `stop`)
        src/extraction/llm/parse.py (`_kapanmamis_dizgeyi_onar`)
        docs/rapor/ozet-uretimi.md

## Bu testin varlık sebebi — ölçülmüş tek kök neden, iki farklı yüz

Ollama'nın çıktı token sınırı varsayılan olarak SINIRSIZDIR. Özet üretiminde
(`qwen2.5:7b-instruct`) model geçerli bir özet yazıp JSON'u kapatmadan
`<tool_call>` üretiyor ve ardından çöp döngüsüne giriyordu. Bu tek arıza iki
ayrı hata olarak görünüyordu:

    döngü zaman aşımına kadar sürerse -> LLMTransportError (180 sn)
    bağlam dolup çıktı kesilirse      -> LLMError "kesik yanit"

Ölçüldü: 10 belgenin 4'ü düşüyordu, belge başına 44 sn. `num_predict=512` +
`stop=["<tool_call>"]` + dar sınırlayıcı onarımı sonrası **20/20 başarılı,
belge başına 6,9 sn** (6,4 kat hızlanma, %0 hata).
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.extraction.llm.clients import OllamaClient
from src.extraction.llm.parse import parse_llm_json

SEMA = {"type": "object", "properties": {"ozet": {"type": "string"}},
        "required": ["ozet"]}


def _istemci(**kw) -> OllamaClient:
    return OllamaClient(transport=lambda *a, **k: {}, **kw)


class CiktiSiniri(unittest.TestCase):

    def test_num_predict_payloada_giriyor(self):
        p = _istemci().build_payload("s", "u", SEMA)
        self.assertIn("num_predict", p["options"],
                      "sınırsız üretim ölçülmüş bir donma sebebidir")
        self.assertEqual(p["options"]["num_predict"], 512)

    def test_tool_call_kacisi_durduruluyor(self):
        p = _istemci().build_payload("s", "u", SEMA)
        self.assertIn("<tool_call>", p["options"]["stop"])

    def test_ortamdan_ayarlanabilir(self):
        self.assertEqual(_istemci(num_predict=128).build_payload(
            "s", "u", SEMA)["options"]["num_predict"], 128)

    def test_mevcut_secenekler_korundu(self):
        p = _istemci().build_payload("s", "u", SEMA)
        self.assertEqual(p["options"]["num_ctx"], 8192)
        self.assertIn("temperature", p["options"])


class KapanmamisDizgeOnarimi(unittest.TestCase):
    """Onarım YALNIZ sınırlayıcıya dokunur; içerik üretmez."""

    def test_kapanis_tirnagi_dusmus_ozet_kurtarilir(self):
        obj, err = parse_llm_json('{"ozet": "maksimum kazanım 300 TL\'dir.}')
        self.assertIsNone(err)
        self.assertEqual(obj["ozet"], "maksimum kazanım 300 TL'dir.")

    def test_ikinci_alanda_da_calisir(self):
        obj, _ = parse_llm_json('{"ozet": "a", "not": "b}')
        self.assertEqual(obj, {"ozet": "a", "not": "b"})

    def test_nesne_KAPANMAMISSA_onarilmaz(self):
        """Model `}` yazmadıysa cevabını bitirmemiştir — kesik metin kabul edilmez."""
        obj, err = parse_llm_json('{"ozet": "yarım kalmış cümle')
        self.assertIsNone(obj)
        self.assertIn("kesik", err)

    def test_ic_ice_yapida_onarilmaz(self):
        """Açık dizgede `{`/`}` varsa neyin kesildiği belirsizdir."""
        obj, _ = parse_llm_json('{"a": "x", "b": {"c": "y}')
        self.assertIsNone(obj)

    def test_zaten_gecerli_json_bozulmaz(self):
        for ham, beklenen in (('{"ozet": "tam."}', {"ozet": "tam."}),
                              ('{"ozet": 5}', {"ozet": 5}),
                              ('{"a": {"b": "c"}}', {"a": {"b": "c"}})):
            with self.subTest(ham=ham):
                obj, err = parse_llm_json(ham)
                self.assertIsNone(err)
                self.assertEqual(obj, beklenen)

    def test_bos_ve_JSONsuz_girdi_yine_reddedilir(self):
        for ham in ("", "   ", "JSON yok burada", "}"):
            with self.subTest(ham=ham):
                self.assertIsNone(parse_llm_json(ham)[0])


if __name__ == "__main__":
    unittest.main()
