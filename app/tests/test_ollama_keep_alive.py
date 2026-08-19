"""`OLLAMA_KEEP_ALIVE` birimsiz verildiğinde istek 400 ile düşmemeli.

İlgili: ../src/extraction/llm/clients.py (`OllamaClient.keep_alive`)

## Kök neden

`keep_alive` değeri sunucu env'ine DEĞİL istek gövdesine gider ve iki bağlam
aynı değeri farklı kabul eder:

* Ollama'nın kendi belgesi "modeli bellekte süresiz tut" için
  `OLLAMA_KEEP_ALIVE=-1` önerir ve sunucu bunu env olarak kabul eder.
* `/api/chat` gövdesindeki `keep_alive` alanı Go'nun `time.ParseDuration`'ıyla
  çözülür; birimsiz `-1` için sunucu
  `HTTP 400 {"error": "time: missing unit in duration \"-1\""}` döner.

## Ürün yüzeyindeki etki (ÖLÇÜLDÜ, 2026-08-19, Colab A100)

`colab/02_ablasyon.py` env'i `-1` yazıyordu. Ablasyonun `kural` kolu 8
saniyede koştu; `llm`, `hibrit` ve `hibrit-verify` kollarının ÜÇÜ DE 0
saniyede düştü. Yani jüri için "en ikna edici tek artefakt" olan ablasyon
tablosu üç kolu eksik üretildi — ve `LLM_STRICT=1` olmasaydı sessizce
kural-only sonuçları LLM etiketiyle yayımlanacaktı.

Belgesi `-1` öneren bir sistemin istemcisi `-1`i kabul etmek zorunda; bu
yüzden düzeltme Colab betiğinde değil İSTEMCİDE yapıldı.
"""

from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.extraction.llm.clients import OllamaClient, _birimsiz_sayi


class TestBirimsizSayi(unittest.TestCase):
    """Yardımcının kendisi — süre biçimlerini doğru ayırıyor mu."""

    def test_birimsiz_tam_sayilar(self) -> None:
        for v in ("-1", "0", "300", "+30"):
            self.assertTrue(_birimsiz_sayi(v), v)

    def test_birimli_sureler_dokunulmaz(self) -> None:
        for v in ("30m", "1h30m", "-1s", "5h", "500ms"):
            self.assertFalse(_birimsiz_sayi(v), v)

    def test_bos_dize_sayi_degil(self) -> None:
        """`""` + `"s"` = `"s"` — geçersiz bir süre. Çağıran varsayılana düşer."""
        self.assertFalse(_birimsiz_sayi(""))


class TestKeepAliveNormalizasyonu(unittest.TestCase):
    """KAPI 1: birimsiz değer Go süresine çevrilir, anlamı korunur."""

    def setUp(self) -> None:
        self._eski = os.environ.get("OLLAMA_KEEP_ALIVE")

    def tearDown(self) -> None:
        if self._eski is None:
            os.environ.pop("OLLAMA_KEEP_ALIVE", None)
        else:
            os.environ["OLLAMA_KEEP_ALIVE"] = self._eski

    def _keep_alive(self, env_degeri: str) -> str:
        os.environ["OLLAMA_KEEP_ALIVE"] = env_degeri
        return OllamaClient().keep_alive

    def test_eksi_bir_saniyeye_cevrilir_ve_SURESIZ_kalir(self) -> None:
        """Negatif işaret korunur: Ollama'da negatif süre = süresiz."""
        self.assertEqual(self._keep_alive("-1"), "-1s")

    def test_birimsiz_pozitif_saniye_sayilir(self) -> None:
        """Ollama CLI'ının kendi kuralı: birimsiz sayı saniyedir."""
        self.assertEqual(self._keep_alive("300"), "300s")

    def test_birimli_deger_AYNEN_gecer(self) -> None:
        self.assertEqual(self._keep_alive("30m"), "30m")
        self.assertEqual(self._keep_alive("1h30m"), "1h30m")


class TestBosEnvKapisi(unittest.TestCase):
    """KAPI 2: env tanımlı ama boşsa varsayılana düşülür.

    `os.environ.get(ad, "30m")` env TANIMLI ve boş olduğunda varsayılanı
    DÖNDÜRMEZ, boş dizeyi döndürür. Boş dize istek gövdesine girse aynı 400
    hatası ikinci bir kapıdan geri gelirdi.
    """

    def setUp(self) -> None:
        self._eski = os.environ.get("OLLAMA_KEEP_ALIVE")

    def tearDown(self) -> None:
        if self._eski is None:
            os.environ.pop("OLLAMA_KEEP_ALIVE", None)
        else:
            os.environ["OLLAMA_KEEP_ALIVE"] = self._eski

    def test_bos_env_varsayilana_duser(self) -> None:
        os.environ["OLLAMA_KEEP_ALIVE"] = ""
        self.assertEqual(OllamaClient().keep_alive, "30m")

    def test_yalnizca_bosluk_da_varsayilana_duser(self) -> None:
        os.environ["OLLAMA_KEEP_ALIVE"] = "   "
        self.assertEqual(OllamaClient().keep_alive, "30m")

    def test_acik_parametre_env_i_ezer(self) -> None:
        os.environ["OLLAMA_KEEP_ALIVE"] = "30m"
        self.assertEqual(OllamaClient(keep_alive="-1").keep_alive, "-1s")


if __name__ == "__main__":
    unittest.main()
