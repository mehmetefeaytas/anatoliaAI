"""Kaynak satırı HANGİ ALANDAN geldiğini taşır.

İlgili: ../src/comparison/compare.py (`RankRow.field`)
        ../src/chatbot/structured.py (`_phrase_ustunluk_kiyasi`)
        ../src/chatbot/bot.py (`sources` sözlüğü)
        ../web/app/components/ChatPanel.tsx (DEĞER sütunu)

## Bu dosyanın koruduğu değişmez — ölçülmüş gösterim hatası

Bileşik "en avantajlı" cevabı satırlarını BOYUT BOYUT toplar: vade, masraf,
ödül… Ama `RankRow` hangi alandan geldiğini taşımıyordu ve `sources` sözlüğüne
de konmuyordu. Arayüz her satırı SORGUNUN alanıyla biçimlendirmek zorunda
kalıyordu (`formatValue(s.value, cevap.field)`).

Ölçüldü (gerçek sorgu, 24 Ağu 2026): sorgu alanı `kar_payi_orani` iken vade
satırı **`%120`** olarak basıldı — 120 AY vade, yüzde değil. Masraf ve ödül
satırları sözlük olduğu için o dala düşmedi ve doğru görünüyordu; hata yalnız
çıplak sayısal alanlarda görünür oluyordu, yani sessiz ve seçiciydi.

Değişmez: kaynak satırı kendi alan adını taşır ve arayüz onu kullanır.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.chatbot.structured import _fmt_value
from src.comparison.compare import RankRow


class RankRowAlanTest(unittest.TestCase):

    def test_field_alani_VAR_ve_opsiyonel(self):
        r = RankRow(bank="a", bank_name="A", value=120, sort_key=120.0,
                    comparable=True, note=None, source_span=None)
        self.assertIsNone(r.field)          # geriye uyum: varsayılan None
        r2 = RankRow(bank="a", bank_name="A", value=120, sort_key=120.0,
                     comparable=True, note=None, source_span=None,
                     field="vade_ay")
        self.assertEqual(r2.field, "vade_ay")


class BicimlemeTest(unittest.TestCase):
    """Hatanın kendisi: aynı değer, farklı alan adıyla farklı basılır."""

    def test_vade_ay_YUZDE_ile_basilmaz(self):
        self.assertEqual(_fmt_value("vade_ay", 120), "120 ay")

    def test_ayni_deger_oran_alaninda_yuzdeli(self):
        """Sorgunun alanı geçirilirse hata yeniden doğar — bu yüzden satırın
        kendi alanı taşınmak zorunda."""
        self.assertEqual(_fmt_value("kar_payi_orani", 120), "%120")

    def test_sozluk_degerler_alan_adindan_ETKILENMEZ(self):
        """Masraf ve ödül neden 'doğru' görünüyordu: sözlük dalları alan adına
        bakmıyor. Hata bu yüzden yalnız çıplak sayılarda görünüyordu."""
        self.assertEqual(_fmt_value("kar_payi_orani", {"has_fee": False}),
                         "masrafsız")
        self.assertEqual(
            _fmt_value("kar_payi_orani", {"value": 200.0, "currency": "TRY"}),
            "200 TL")


class KaynakSozluguTest(unittest.TestCase):
    """`bot.py` kaynak sözlüğü alan adını taşımalı."""

    def test_sources_sozlugunde_field_var(self):
        import inspect

        from src.chatbot import bot as B
        kaynak = inspect.getsource(B)
        self.assertIn('"field": x.field', kaynak,
                      "kaynak sözlüğü satırın alan adını taşımıyor; arayüz "
                      "sorgunun alanıyla biçimlemek zorunda kalır")


if __name__ == "__main__":
    unittest.main()
