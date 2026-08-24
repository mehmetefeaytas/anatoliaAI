"""Uygulanamayan sıralama yönü SESSİZ kalmaz.

İlgili: ../src/chatbot/structured.py (`_yon_uyarisi`)
        ../src/chatbot/router.py (`Route.intent`)

## Ölçülmüş sessizlik

Kullanıcı iki ayrı soru sordu (24 Ağu 2026):

    "Hangi bankada en DÜŞÜK konut finansmanı var"
    "Hangi bankada en YÜKSEK konut finansmanı var"

ve **aynı cevabı** aldı. Sebep: birincil alan (`kar_payi_orani`) o ailede
kıyaslanabilir değil (Albaraka sayfasında oran DEĞERİ yayınlanmıyor), sistem
çok boyutlu bileşik skora düşüyor ve bileşik skor TEK YÖNLÜ (yüksek skor =
daha avantajlı). Yön böylece uygulanamıyor.

Düşmenin kendisi doğru davranıştır; **söylenmemesi** yanlıştır. Kullanıcı
"en düşük" diye sordu ve yönünün yok sayıldığını bilmiyor — bu, cevabı
yanıltıcı yapar. Aynı dosya ailesindeki kural: kıyaslanamayan boyut sessizce
düşmez, SÖYLENİR.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.chatbot.structured import _yon_uyarisi


class UyariTest(unittest.TestCase):

    def test_lowest_ve_bilesik_skor_UYARI_verir(self):
        u = _yon_uyarisi("lowest", bilesige_dusuldu=True)
        self.assertIsNotNone(u)
        self.assertIn("en düşük", u)
        self.assertIn("bileşik", u.lower())

    def test_highest_icin_de_uyarir(self):
        u = _yon_uyarisi("highest", bilesige_dusuldu=True)
        self.assertIsNotNone(u)
        self.assertIn("en yüksek", u)

    def test_bilesige_DUSULMEDIYSE_uyari_YOK(self):
        """Yön gerçekten uygulandıysa uyarı gürültüdür."""
        self.assertIsNone(_yon_uyarisi("lowest", bilesige_dusuldu=False))

    def test_yonsuz_niyette_uyari_YOK(self):
        for intent in ("list", "filter", None, ""):
            with self.subTest(intent=intent):
                self.assertIsNone(_yon_uyarisi(intent, bilesige_dusuldu=True))

    def test_uyari_SEBEBI_soyler(self):
        """'Uygulanamadı' yeterli değil; NEDEN uygulanamadığı yazılmalı."""
        u = _yon_uyarisi("lowest", bilesige_dusuldu=True)
        self.assertIn("tek yönlü", u.lower())

    def test_iki_yon_AYNI_metni_vermez(self):
        self.assertNotEqual(_yon_uyarisi("lowest", bilesige_dusuldu=True),
                            _yon_uyarisi("highest", bilesige_dusuldu=True))


if __name__ == "__main__":
    unittest.main()
