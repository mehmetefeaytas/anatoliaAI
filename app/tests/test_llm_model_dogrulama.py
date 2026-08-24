"""Model adı doğrulaması — sessizce başka modele düşmeyi engeller.

İlgili: ../src/extraction/llm/clients.py (`VLLMClient._dogrula_model`)
        docs/evren-servisi.md §14 (TUZAK)

## Bu kapı niçin var — ölçülmüş sessiz sapma

SSB EVREN dokümantasyonunun kendi uyarısı: *"Unknown model names silently
default to llm-fast."* Doğrulandı (2026-08-24): `model="llm-buyuk-yanlis-ad"`
ile istek **HTTP 200** döndü ve yanıtın `model` alanı o uydurma adı geri
verdi — yani yanıta bakarak sapmayı anlamak MÜMKÜN DEĞİL.

Sonuç: `EVREN_MODEL` bir harf yanlış yazılırsa koşum başka bir modelle yapılır,
eval artefaktı yanlış model adını raporlar ve kimse fark etmez. Bu, ölçümün
kendisini yalanlayan bir hata sınıfıdır ve projenin "sessiz hata yok"
ilkesinin doğrudan ihlalidir.

## Neden `transport` enjekte edilince ATLANIR

Doğrulama gerçek bir `GET /v1/models` çağrısı ister. Onlarca test sahte taşıma
ile koşuyor ve orada gerçek bir sunucu YOK; doğrulama koşulsuz açık olsa o
testler ağa çıkmaya çalışırdı. Açık `transport` "burada gerçek sunucu yok"
demenin kendisidir (bkz. `bearer_transport` ile aynı desen).
"""

from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.extraction.llm.clients import LLMError, VLLMClient

SCHEMA = {"type": "object", "properties": {"a": {"type": "string"}}}


class _Sunucu:
    """Her modu kabul eden, kısıt uygulayan sahte uç."""

    def __call__(self, url: str, payload: dict, timeout: float) -> dict:
        return {"choices": [{"message": {"content": "{"}}]}


class DogrulamaTest(unittest.TestCase):

    def test_listede_OLMAYAN_model_HATA(self):
        c = VLLMClient(model="llm-buyuk-yanlis-ad", api_key="sk-x",
                       model_dogrula=True)
        c.model_listesi_al = lambda: ["llm-large", "llm-fast", "bge-m3-embed"]
        with self.assertRaises(LLMError) as ctx:
            c.negotiate(SCHEMA)
        mesaj = str(ctx.exception)
        self.assertIn("llm-buyuk-yanlis-ad", mesaj)
        self.assertIn("llm-large", mesaj)          # geçerli seçenekler yazılmalı

    def test_listede_OLAN_model_gecer(self):
        c = VLLMClient(model="llm-large", api_key="sk-x", model_dogrula=True)
        c.model_listesi_al = lambda: ["llm-large", "llm-fast"]
        c.transport = _Sunucu()
        self.assertEqual(c.negotiate(SCHEMA), "json_schema")

    def test_bir_kez_dogrulanir(self):
        """Pazarlık cache'li; doğrulama da her çağrıda tekrarlanmamalı."""
        c = VLLMClient(model="llm-large", api_key="sk-x", model_dogrula=True)
        sayac = []
        c.model_listesi_al = lambda: (sayac.append(1), ["llm-large"])[1]
        c.transport = _Sunucu()
        c.negotiate(SCHEMA)
        c.negotiate(SCHEMA, force=True)
        self.assertEqual(len(sayac), 1)

    def test_liste_ALINAMAZSA_kosum_DURMAZ(self):
        """Ağ hatası doğrulamayı imkânsız kılar; koşumu engellemesi YANLIŞ olur.

        Doğrulama bir güvencedir, ön koşul değil. Liste alınamadığında
        uyarı loglanır ve pazarlık devam eder — aksi hâlde geçici bir ağ
        dalgalanması tüm koşumu düşürürdü.
        """
        c = VLLMClient(model="llm-large", api_key="sk-x", model_dogrula=True)

        def patla():
            raise OSError("ag yok")

        c.model_listesi_al = patla
        c.transport = _Sunucu()
        self.assertEqual(c.negotiate(SCHEMA), "json_schema")

    def test_BOS_liste_eleme_yapmaz(self):
        c = VLLMClient(model="her-neyse", api_key="sk-x", model_dogrula=True)
        c.model_listesi_al = lambda: []
        c.transport = _Sunucu()
        self.assertEqual(c.negotiate(SCHEMA), "json_schema")


class VarsayilanTest(unittest.TestCase):
    """Açık `transport` = "gerçek sunucu yok" — doğrulama atlanır."""

    def test_acik_transport_ile_KAPALI(self):
        c = VLLMClient(transport=_Sunucu())
        self.assertFalse(c.model_dogrula)

    def test_anahtarli_uzak_uc_ile_ACIK(self):
        with mock.patch.dict(os.environ, {"VLLM_MODEL_DOGRULA": ""}):
            c = VLLMClient(api_key="sk-x")
        self.assertTrue(c.model_dogrula)

    def test_env_ile_kapatilabilir(self):
        with mock.patch.dict(os.environ, {"VLLM_MODEL_DOGRULA": "0"}):
            c = VLLMClient(api_key="sk-x")
        self.assertFalse(c.model_dogrula)

    def test_anahtarsiz_yerel_uc_ile_KAPALI(self):
        """Yerel vLLM'de model adı HF yolu olabilir ve liste ucu farklı
        davranabilir; tuzak da yalnız uzak uçta ölçüldü."""
        with mock.patch.dict(os.environ, {"VLLM_MODEL_DOGRULA": "",
                                          "VLLM_API_KEY": ""}):
            c = VLLMClient()
        self.assertFalse(c.model_dogrula)


if __name__ == "__main__":
    unittest.main()
