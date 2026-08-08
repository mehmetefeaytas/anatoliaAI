"""LLM çağrısı duvar-saati sınırıyla bağlanmalı — demo donma riski.

İlgili: ../src/extraction/llm/clients.py (`_urllib_transport`, `_deadline`)

## Neden bu dosya var — ölçülmüş donma

`urlopen(..., timeout=t)` bir SOKET zaman aşımıdır ve her `recv` için ayrı
işler. Sunucu bağlantıyı açık tutup veri göndermezse süre **hiç dolmaz**.

2026-08-08'de `build_summaries` koşumu `OLLAMA_TIMEOUT=900` verilmiş
olmasına rağmen Ollama'ya açık bir TCP soketiyle **18 dakika uykuda**
bekledi — %0 CPU, log'a tek satır yazmadan.

Demo açısından tek gerçek donma riski buydu: jüri önünde model takılırsa
arayüz süresiz bekler. Sınır artık soket zaman aşımının katı olarak
uygulanıyor ve `LLM_DEADLINE_CARPANI` ile ayarlanabiliyor.
"""

from __future__ import annotations

import sys
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.extraction.llm import clients


class _Yedek:
    """İç taşımayı geçici olarak değiştirir; testler birbirini kirletmesin."""

    def __init__(self, yeni):
        self.yeni = yeni

    def __enter__(self):
        self.orij = clients._urllib_transport_ic
        clients._urllib_transport_ic = self.yeni
        return self

    def __exit__(self, *a):
        clients._urllib_transport_ic = self.orij
        return False


class TestDuvarSaatiSiniri(unittest.TestCase):

    def test_asili_cagri_SINIRDA_kesilir(self) -> None:
        """Soket zaman aşımı tetiklenmese bile çağrı geri dönmeli."""
        with _Yedek(lambda u, p, t: time.sleep(30)):
            t0 = time.time()
            with self.assertRaises(clients.LLMTransportError) as ctx:
                clients._urllib_transport("http://ornek.invalid/x", {}, 0.4)
            gecen = time.time() - t0
        # 0,4 sn × 1,5 = 0,6 sn. Üst sınır cömert: yüklü makinede de geçsin.
        self.assertLess(gecen, 5.0, "sınır tetiklenmedi ya da çok geç kaldı")
        self.assertIn("duvar-saati", str(ctx.exception))

    def test_normal_cagri_ETKILENMEZ(self) -> None:
        with _Yedek(lambda u, p, t: {"ok": True}):
            self.assertEqual(
                clients._urllib_transport("http://ornek.invalid/x", {}, 5.0),
                {"ok": True})

    def test_hata_TURU_KORUNARAK_yayilir(self) -> None:
        """Sarmalayıcı hata sınıfını değiştirmemeli; üst katman ona bakıyor."""
        def patla(u, p, t):
            raise clients.LLMHTTPError(500, "govde", "http://ornek.invalid/x")

        with _Yedek(patla):
            with self.assertRaises(clients.LLMHTTPError):
                clients._urllib_transport("http://ornek.invalid/x", {}, 5.0)

    def test_sinir_KAPATILABILIR(self) -> None:
        """Çarpan 0 ise sarmalayıcı devre dışı — davranış eski hâline döner."""
        import os
        onceki = os.environ.get("LLM_DEADLINE_CARPANI")
        os.environ["LLM_DEADLINE_CARPANI"] = "0"
        try:
            self.assertEqual(clients._deadline(100.0), 0.0)
            with _Yedek(lambda u, p, t: {"ok": True}):
                self.assertEqual(
                    clients._urllib_transport("http://ornek.invalid/x", {}, 1.0),
                    {"ok": True})
        finally:
            if onceki is None:
                os.environ.pop("LLM_DEADLINE_CARPANI", None)
            else:
                os.environ["LLM_DEADLINE_CARPANI"] = onceki

    def test_carpan_ortamdan_okunur(self) -> None:
        import os
        onceki = os.environ.get("LLM_DEADLINE_CARPANI")
        os.environ["LLM_DEADLINE_CARPANI"] = "3"
        try:
            self.assertEqual(clients._deadline(10.0), 30.0)
        finally:
            if onceki is None:
                os.environ.pop("LLM_DEADLINE_CARPANI", None)
            else:
                os.environ["LLM_DEADLINE_CARPANI"] = onceki


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
