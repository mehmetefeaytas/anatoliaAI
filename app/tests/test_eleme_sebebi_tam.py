"""Eleme sebebi sözlüğü TAM olmalı — eksik anahtar HTTP 500 demek.

İlgili: ../src/chatbot/structured.py (`_SEBEP_SIFATI`, `_sayim_cumlesi`)
        ../src/comparison/compare.py (`ELEME_*` sabitleri)

## Ölçülen çökme (4. tur Fonksiyonellik jürisi, canlı `/chat`)

*"Ziraat Katılım'ın konut finansmanında en az 12 ay vadeli ve masrafsız
kampanyası var mı?"* → **HTTP 500**. Kök neden: `_sayim_cumlesi`
`_SEBEP_SIFATI[kod]` ile erişiyor, `compare.py` `ELEME_ALAN_YOK` üretiyor
ve sözlükte karşılığı yoktu → `KeyError`.

Bu, sessizce düşen bir koşuldan **kötü**: kullanıcı hiç cevap almıyor.
Jüri kusuru bir sebeple buldu (`alan_yok`); aynı durumda olan ikinci sabit
(`ELEME_ORAN_BAZI`) gözden kaçmıştı ve birlikte kapatıldı.

## Bu testin işi

Sözlüğe iki satır eklemek kusuru kapatır ama SINIFI kapatmaz — üçüncü bir
eleme sebebi eklendiğinde aynı 500 geri gelir. Bu test `compare` modülündeki
`ELEME_*` sabitlerini **çalışma anında toplayıp** her birinin sözlükte
karşılığı olduğunu denetliyor. Yeni sebep eklenip sözlüğe yazılmazsa test
kırılır ve kusur üretime çıkmaz.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.chatbot.structured import _SEBEP_SIFATI, _sayim_cumlesi
from src.comparison import compare


def _eleme_sabitleri() -> dict[str, str]:
    """`compare` modülündeki tüm `ELEME_*` sabitleri: ad -> değer."""
    return {ad: getattr(compare, ad) for ad in dir(compare)
            if ad.startswith("ELEME_")}


class TestSozlukTam(unittest.TestCase):
    def test_her_eleme_sebebinin_sifati_var(self) -> None:
        eksik = {ad: deger for ad, deger in _eleme_sabitleri().items()
                 if deger not in _SEBEP_SIFATI}
        self.assertEqual(
            eksik, {},
            "eleme sebebi sözlükte yok — `_sayim_cumlesi` bu kodu görürse "
            "KeyError ve HTTP 500 verir. `_SEBEP_SIFATI`'ya Türkçe sıfatını "
            "ekleyin.")

    def test_en_az_on_sebep_var(self) -> None:
        """Sabit listesi boşalırsa test kendini kandırmasın."""
        self.assertGreaterEqual(len(_eleme_sabitleri()), 10)

    def test_sifatlar_bos_degil(self) -> None:
        for kod, sifat in _SEBEP_SIFATI.items():
            with self.subTest(kod=kod):
                self.assertTrue(sifat and sifat.strip(), kod)

    def test_juri_vakasi_patlamaz(self) -> None:
        """Jürinin 500 aldığı yolla cümle kurulabiliyor mu — HER sebep için?

        `_sayim_cumlesi` gerçek `RankRow` bekliyor; sözlük geçirmek
        `AttributeError` verir ve testin kendisi kusuru ıskalar.
        """
        from collections import Counter

        from src.comparison.compare import RankRow
        satir = RankRow(bank="ziraat-katilim", bank_name="Ziraat Katılım",
                        value=None, sort_key=None, comparable=False,
                        note=None, source_span=None, campaign_id=1)
        for ad, kod in _eleme_sabitleri().items():
            with self.subTest(sebep=ad):
                cumle = _sayim_cumlesi("kar_payi_orani", [satir],
                                       Counter({kod: 1}), None)
                self.assertIn(_SEBEP_SIFATI[kod], cumle)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
