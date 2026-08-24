"""Pazarlık kısıt probu — "200 döndü" ile "kısıt uygulandı" ayrımı.

İlgili: ../src/extraction/llm/clients.py (`VLLMClient.negotiate`)
        sorun/evren-guided-json-sessiz-yok-sayma.md

## Neden bu dosya var — ölçülmüş sessiz yok sayma

`negotiate()` bir modu "çalışıyor" saymak için YALNIZCA HTTP 200'e bakıyordu.
Bu, sunucunun parametreyi TANIMASI ile UYGULAMASI'nı aynı şey sanan bir
varsayımdır ve ölçümle yanlışlandı:

SSB EVREN ucunda (2026-08-24, `llm-large`) `guided_json` gönderildiğinde
sunucu **HTTP 200** döndü ama kısıtı hiç uygulamadı — prob yanıtı `'P'`
("Pong!"), gerçek çağrının çıktısı ise serbest Türkçe metin oldu. Pazarlık
`guided_json`'u seçti, `parse.py` o metni ayrıştıramadı ve sonuç üst katmanda
**"LLM hiç alan bulamadı"** olarak göründü — modül docstring'inin önlemeye
çalıştığı hata sınıfının tam olarak aynısı, yeni bir kılıkta.

Ayrım şu tek gözlemle ölçülebiliyor: kısıtlı decoding'de ilk token `{`
olmak ZORUNDADIR. Kısıt yoksa model kendi cümlesine başlar.

## Muhafazakârlık kuralı

Prob yanıtı BOŞSA mod elenmez. Bazı sunucular `max_tokens=1`'de boş içerik
döndürür; kararsızlığı "kısıt yok" diye okumak çalışan bir modu eler ve
sistemi gereksizce `prompt_only`a düşürür. Yanlış eleme, yanlış kabulden
daha pahalıdır.

`prompt_only` hiç proba tabi değildir: orada kısıt zaten YOK, son çaredir ve
elenirse hiç mod kalmaz.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.extraction.llm.clients import (
    STRUCTURED_MODES,
    LLMHTTPError,
    VLLMClient,
)

SCHEMA = {"type": "object", "properties": {"a": {"type": "string"}}}


def _mod(payload: dict) -> str:
    """İstek gövdesinden hangi modun denendiğini okur."""
    if "tools" in payload:
        return "tool_calling"
    if "response_format" in payload:
        # json_object da `response_format` kullanır; ayrım `type`ta.
        tur = (payload["response_format"] or {}).get("type")
        return "json_object" if tur == "json_object" else "json_schema"
    if "structured_outputs" in payload:
        return "structured_outputs"
    if "guided_json" in payload:
        return "guided_json"
    return "prompt_only"


class _Sunucu:
    """Modları kabul eden/yok sayan yapılandırılabilir sahte sunucu.

    `kabul`: HTTP 200 dönen modlar. `uygular`: kısıtı GERÇEKTEN uygulayan
    modlar — yalnız bunlarda prob yanıtı `{` ile başlar.
    """

    def __init__(self, kabul, uygular, bos_prob=()):
        self.kabul = set(kabul)
        self.uygular = set(uygular)
        self.bos_prob = set(bos_prob)
        self.denenen: list[str] = []

    def __call__(self, url: str, payload: dict, timeout: float) -> dict:
        mode = _mod(payload)
        self.denenen.append(mode)
        if mode not in self.kabul:
            raise LLMHTTPError(400, "bilinmeyen parametre", url)
        if mode in self.bos_prob:
            icerik = ""
        elif mode in self.uygular:
            icerik = "{"
        else:
            icerik = "P"          # "Pong!" — kısıt yok sayıldı
        return {"choices": [{"message": {"content": icerik}}]}


class KisitProbuTest(unittest.TestCase):
    """Yok sayılan mod elenir; uygulayan mod seçilir."""

    def test_sessizce_yok_sayilan_mod_ELENIR(self):
        """EVREN senaryosu: guided_json 200 döner ama kısıt uygulamaz."""
        s = _Sunucu(kabul={"guided_json", "prompt_only"}, uygular=set())
        c = VLLMClient(transport=s)
        self.assertEqual(c.negotiate(SCHEMA), "prompt_only")
        gerekce = dict(c.negotiation_log)
        self.assertIn("kisit", gerekce["guided_json"].lower())

    def test_kisit_uygulayan_mod_SECILIR(self):
        s = _Sunucu(kabul={"guided_json", "prompt_only"},
                    uygular={"guided_json"})
        c = VLLMClient(transport=s)
        self.assertEqual(c.negotiate(SCHEMA), "guided_json")

    def test_ilk_uygulayan_mod_kazanir(self):
        """json_schema kabul edilir ama uygulamaz; structured_outputs uygular."""
        s = _Sunucu(kabul={"json_schema", "structured_outputs", "prompt_only"},
                    uygular={"structured_outputs"})
        c = VLLMClient(transport=s)
        self.assertEqual(c.negotiate(SCHEMA), "structured_outputs")

    def test_bos_prob_yaniti_modu_ELEMEZ(self):
        """Kararsızlık yanlış elemeye yol açmamalı (muhafazakârlık kuralı)."""
        s = _Sunucu(kabul={"json_schema", "prompt_only"}, uygular=set(),
                    bos_prob={"json_schema"})
        c = VLLMClient(transport=s)
        self.assertEqual(c.negotiate(SCHEMA), "json_schema")

    def test_prompt_only_proba_TABI_DEGIL(self):
        """Son çare elenemez: 'P' dönse bile seçilir."""
        s = _Sunucu(kabul={"prompt_only"}, uygular=set())
        c = VLLMClient(transport=s)
        self.assertEqual(c.negotiate(SCHEMA), "prompt_only")

    def test_prob_kapatilabilir(self):
        """`kisit_probu=False` eski davranışı geri verir (kaçış kapısı)."""
        s = _Sunucu(kabul={"guided_json", "prompt_only"}, uygular=set())
        c = VLLMClient(transport=s, kisit_probu=False)
        self.assertEqual(c.negotiate(SCHEMA), "guided_json")

    def test_mod_sirasi_korunur(self):
        """Pazarlık soldan sağa: STRUCTURED_MODES sırası bozulmamalı."""
        s = _Sunucu(kabul=set(STRUCTURED_MODES), uygular={"prompt_only"})
        c = VLLMClient(transport=s)
        c.negotiate(SCHEMA)
        self.assertEqual(s.denenen, list(STRUCTURED_MODES))


if __name__ == "__main__":
    unittest.main()
