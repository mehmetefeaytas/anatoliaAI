"""`tool_calling` modu — şemanın kısıt olarak geçtiği DÖRDÜNCÜ yol.

İlgili: ../src/extraction/llm/clients.py (`STRUCTURED_MODES`, `build_payload`)
        docs/evren-servisi.md §3 (hangi modun neden düştüğü)

## Bu mod niçin eklendi — ölçülmüş boşluk

SSB EVREN ucunda yapılandırılmış çıktının ÜÇ yolu da kapalıydı:
`json_schema` ve `structured_outputs` karmaşık şemamızda **HTTP 500** veriyor,
`guided_json` ise **200 dönüp kısıtı sessizce yok sayıyor**. Elde yalnız
`json_object` (JSON garantisi, şema yok) ve `prompt_only` (hiç kısıt yok)
kalıyordu — ve ablasyon tam bu yüzden "gerçek şema kısıtı hiç devreye girmedi"
uyarısıyla raporlanmıştı.

Ölçüldü (2026-08-24): AYNI şema (12 alan, 39 `anyOf`, 5.548 karakter) tool
calling ile **kabul edildi** ve 12 alanın tamamı doğru yapıda döndü. Yani uç
şemayı derleyebiliyor; kabul etmediği şey `response_format` sarmalayıcısıydı.

## Yanıt neden `content`te değil

Tool calling'de model çıktıyı `message.tool_calls[0].function.arguments`
içine yazar ve `content` boş kalır. `generate()` bunu bilmek zorunda; yoksa
"model boş cevap verdi" diye okur ve üst katman özeti/çıkarımı sessizce
kaybeder — bu dosyanın koruduğu asıl değişmez budur.

Hiçbir test ağa çıkmaz: taşıma enjekte edilir.
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

SCHEMA = {"type": "object", "properties": {"a": {"type": "string"}},
          "required": ["a"]}


class _ToolSunucu:
    """Yalnız tool calling'i kabul eden sahte uç (EVREN'in ölçülmüş hâli)."""

    def __init__(self, arguments: str = '{"a": "x"}'):
        self.arguments = arguments
        self.payloadlar: list[dict] = []

    def __call__(self, url: str, payload: dict, timeout: float) -> dict:
        self.payloadlar.append(payload)
        if "tools" not in payload:
            # json_schema / structured_outputs / guided_json hepsi 500
            if any(k in payload for k in ("response_format", "structured_outputs",
                                          "guided_json")):
                raise LLMHTTPError(500, "InternalServerError", url)
            # prompt_only: kısıtsız serbest metin
            return {"choices": [{"message": {"content": "Pong!"}}]}
        return {"choices": [{"message": {
            "content": None,
            "tool_calls": [{"type": "function", "function": {
                "name": "kampanya_cikarimi", "arguments": self.arguments}}]}}]}


class ModListesiTest(unittest.TestCase):

    def test_mod_STRUCTURED_MODES_icinde(self):
        self.assertIn("tool_calling", STRUCTURED_MODES)

    def test_SIRA_kisit_gucune_gore(self):
        """`tool_calling` gerçek şema kısıtı verir; `json_object` vermez.

        Bu yüzden `json_object` ve `prompt_only`dan ÖNCE denenmeli — aksi
        hâlde daha zayıf bir mod kazanır ve kısıt boşa gider.
        """
        i = STRUCTURED_MODES.index
        self.assertLess(i("tool_calling"), i("json_object"))
        self.assertLess(i("tool_calling"), i("prompt_only"))
        self.assertLess(i("guided_json"), i("tool_calling"))


class PayloadTest(unittest.TestCase):

    def test_tools_ve_tool_choice_kurulur(self):
        c = VLLMClient(transport=_ToolSunucu())
        p = c.build_payload("s", "u", SCHEMA, "tool_calling")
        self.assertEqual(len(p["tools"]), 1)
        self.assertEqual(p["tools"][0]["type"], "function")
        self.assertEqual(p["tools"][0]["function"]["parameters"], SCHEMA)
        self.assertEqual(p["tool_choice"]["function"]["name"],
                         p["tools"][0]["function"]["name"])

    def test_response_format_KULLANILMAZ(self):
        """Uç `response_format`ı reddediyordu; mod onu göndermemeli."""
        c = VLLMClient(transport=_ToolSunucu())
        p = c.build_payload("s", "u", SCHEMA, "tool_calling")
        for k in ("response_format", "structured_outputs", "guided_json"):
            self.assertNotIn(k, p)

    def test_sema_prompt_a_GOMULMEZ(self):
        """Şema kısıt olarak gidiyor; prompt'a metin olarak eklemek gereksiz
        token harcar ve `prompt_only`ın işini tekrarlardı."""
        c = VLLMClient(transport=_ToolSunucu())
        p = c.build_payload("s", "u", SCHEMA, "tool_calling")
        self.assertEqual(p["messages"][0]["content"], "s")


class YanitTest(unittest.TestCase):

    def test_arguments_METIN_olarak_donuyor(self):
        s = _ToolSunucu(arguments='{"a": "kar payi"}')
        c = VLLMClient(transport=s, structured_mode="tool_calling")
        r = c.generate("s", "u", SCHEMA)
        self.assertEqual(r.text, '{"a": "kar payi"}')
        self.assertEqual(r.mode, "tool_calling")

    def test_bos_content_HATA_DEGIL(self):
        """`content: None` + `tool_calls` dolu = geçerli yanıt."""
        c = VLLMClient(transport=_ToolSunucu(), structured_mode="tool_calling")
        self.assertTrue(c.generate("s", "u", SCHEMA).text)

    def test_generate_json_ayristirir(self):
        c = VLLMClient(transport=_ToolSunucu(arguments='{"a": "5"}'),
                       structured_mode="tool_calling")
        self.assertEqual(c.generate_json("s", "u", SCHEMA), {"a": "5"})


class PazarlikTest(unittest.TestCase):
    """EVREN senaryosu: üç mod 500/yok sayma, tool calling kazanır."""

    def test_EVREN_senaryosunda_tool_calling_secilir(self):
        s = _ToolSunucu()
        c = VLLMClient(transport=s)
        self.assertEqual(c.negotiate(SCHEMA), "tool_calling")
        gerekce = dict(c.negotiation_log)
        self.assertEqual(gerekce["json_schema"], "HTTP 500")
        self.assertEqual(gerekce["tool_calling"], "OK")

    def test_prob_tool_calls_gorunce_KISIT_UYGULANDI_sayar(self):
        """Prob `content`e bakıyor; tool calling'de orası boş olur.

        `tool_calls` varlığı kısıtın uygulandığının kanıtıdır — aksi hâlde
        prob bu modu "kısıt uygulanmadı" diye eler ve `json_object`a düşerdi.
        """
        from src.extraction.llm.clients import _kisit_uygulandi
        self.assertTrue(_kisit_uygulandi({"choices": [{"message": {
            "content": None,
            "tool_calls": [{"function": {"arguments": "{}"}}]}}]}))


if __name__ == "__main__":
    unittest.main()


class ProbTokenTest(unittest.TestCase):
    """Prob 1 token istiyor; tool çağrısı o tek token'da TAMAMLANMAZ.

    Ölçüldü (24 Ağu, EVREN): prob yanıtı ham başlangıç işareti `'<tool_call>'`
    olarak geldi. `{` ile başlamadığı için mod eleniyordu ve ablasyon yine
    kısıtsız `json_object` ile koşuyordu — yani düzeltme olmadan bu modun
    hiçbir faydası görünmezdi.
    """

    def test_ham_tool_call_isareti_KISIT_sayilir(self):
        from src.extraction.llm.clients import _kisit_uygulandi
        ham = {"choices": [{"message": {"content": "<tool_call>"}}]}
        self.assertTrue(_kisit_uygulandi(ham, "tool_calling"))

    def test_ayni_isaret_BASKA_modda_kisit_sayilmaz(self):
        """`json_schema` modunda `<tool_call>` gelmesi kısıt kanıtı DEĞİL."""
        from src.extraction.llm.clients import _kisit_uygulandi
        ham = {"choices": [{"message": {"content": "<tool_call>"}}]}
        self.assertFalse(_kisit_uygulandi(ham, "json_schema"))

    def test_serbest_metin_tool_calling_modunda_da_ELENIR(self):
        from src.extraction.llm.clients import _kisit_uygulandi
        ham = {"choices": [{"message": {"content": "Pong!"}}]}
        self.assertFalse(_kisit_uygulandi(ham, "tool_calling"))
