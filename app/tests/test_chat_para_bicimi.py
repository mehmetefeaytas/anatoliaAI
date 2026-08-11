"""Sohbet cevabındaki sayı ve para gösterimi — Türkçe, tek yerden.

İlgili: ../src/chatbot/structured.py (`_tr_sayi`, `_tr_para`, `_fmt_value`)
        ../src/normalization/normalize.py (`bicimle_tr_sayi` — ayıraç kuralı)
        ../web/app/lib/format.ts (arayüz tarafı — ayrı çalışma zamanı, aynı çıktı)

## Kusur tarayıcıda görüldü

    Konut Finansmanı: Ziraat Katılım (1.25e+06 TRY)
    Finansman: Kuveyt Türk (5e+06 TRY)

`%g` biçimlendiricisi altı anlamlı basamağı aşan sayıyı bilimsel gösterime
düşürür. 1,25 milyon liralık bir finansman tutarı, katılım bankacılığı
sorusunun tam merkezindeki sayıdır ve "1.25e+06" olarak okunamaz.

Ölçüldü (`data/demo.db`, 5.195 alan kaydı): 10 kayıt bilimsel gösterimle,
621 kayıt `TRY` koduyla, 612 kayıt ham Python sayısıyla ("12.0", "10.0")
basılıyordu; 312 kayıt binlik ayıraçsızdı.

## Tek yer kuralı

Binlik/ondalık ayıraç kuralı sohbet katmanında YENİDEN YAZILMAZ; gövde
`normalization.bicimle_tr_sayi`'dan gelir. Aşağıdaki `TestTekYer` bunu kapıda
tutar: `structured` modülünde `%g` ya da elle kurulmuş bir ayıraç değişimi
kalırsa test düşer.
"""

from __future__ import annotations

import inspect
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.chatbot import structured
from src.chatbot.structured import _fmt_value, _tr_para, _tr_sayi


class TestSayiGosterimi(unittest.TestCase):
    def test_bilimsel_gosterim_YOK(self) -> None:
        for x in (1_250_000.0, 5_000_000.0, 3e6, 1e9, 0.000001):
            with self.subTest(x=x):
                self.assertNotIn("e", _tr_sayi(x).lower())

    def test_binlik_ve_ondalik_ayirac(self) -> None:
        self.assertEqual(_tr_sayi(1_250_000.0), "1.250.000")
        self.assertEqual(_tr_sayi(1500.0), "1.500")
        self.assertEqual(_tr_sayi(120.0), "120")
        self.assertEqual(_tr_sayi(1.79), "1,79")
        self.assertEqual(_tr_sayi(0.0), "0")

    def test_gereksiz_ondalik_sifir_atilir(self) -> None:
        """Belgede "%2,5" yazan oran ekranda "%2,50" diye okunmamalı."""
        self.assertEqual(_tr_sayi(2.5), "2,5")
        self.assertEqual(_tr_sayi(12.0), "12")

    def test_para_birimi_turkce(self) -> None:
        self.assertEqual(_tr_para(1_250_000.0), "1.250.000 TL")
        self.assertEqual(_tr_para(500.0, "TRY"), "500 TL")

    def test_taninmayan_para_birimi_oldugu_gibi_kalir(self) -> None:
        """Bilinmeyen birimi TL'ye çevirmek, olmayan bir dönüşüm iddiasıdır."""
        self.assertEqual(_tr_para(100.0, "USD"), "100 USD")


class TestAlanBazliGosterim(unittest.TestCase):
    """Oran, vade, taksit, tutar, puan — hepsi AYNI fonksiyondan geçer."""

    ORNEKLER = [
        ("finansman_tutari", {"value": 1_250_000.0, "currency": "TRY"},
         "1.250.000 TL"),
        ("finansman_tutari", {"value": 5e6, "currency": "TRY"},
         "5.000.000 TL"),
        ("tahsis_ucreti", {"value": 3000.0, "currency": "TRY"}, "3.000 TL"),
        ("odul_miktari", {"value": 0.0, "currency": "TRY"}, "0 TL"),
        ("kar_payi_orani", 1.79, "%1,79"),
        ("kar_payi_orani", {"min": 3.4, "max": 3.5}, "%3,4–%3,5"),
        ("indirim_orani", 10.0, "%10"),
        ("vade_ay", 120.0, "120 ay"),
        ("taksit_sayisi", 12.0, "12 taksit"),
        ("alisveris_puani", {"kind": "points", "value": 7500.0},
         "7.500 puan"),
        ("alisveris_puani", {"kind": "rate", "value": 5.0}, "%5"),
        ("masraf_durumu", {"has_fee": False, "amount": 0.0}, "masrafsız"),
        ("masraf_durumu", {"has_fee": True, "amount": 1500.0},
         "1.500 TL masraf"),
        ("masraf_durumu", {"has_fee": True, "amount": None},
         "ücret var, tutarı belirtilmemiş"),
    ]

    def test_ornekler(self) -> None:
        for alan, deger, beklenen in self.ORNEKLER:
            with self.subTest(alan=alan, deger=deger):
                self.assertEqual(_fmt_value(alan, deger), beklenen)

    def test_hicbir_alanda_ham_python_sayisi_kalmaz(self) -> None:
        """`str(12.0)` gibi bir çıktı kullanıcıya gitmemeli."""
        for alan, deger, _b in self.ORNEKLER:
            with self.subTest(alan=alan):
                self.assertNotRegex(_fmt_value(alan, deger), r"\d\.\d{1,2}\b",
                                    "ondalık ayıracı nokta kalmış")

    def test_bilinmeyen_alan_cokmez(self) -> None:
        self.assertEqual(_fmt_value("bilinmeyen_alan", 1500.0), "1.500")
        self.assertEqual(_fmt_value("bilinmeyen_alan", "metin"), "metin")
        self.assertEqual(_fmt_value("masraf_durumu", None), "None")


class TestTekYer(unittest.TestCase):
    """Sunucu tarafında sayı biçimi TEK yerde kurulur."""

    def test_g_bicimlendiricisi_kalmadi(self) -> None:
        kaynak = inspect.getsource(structured)
        self.assertNotIn(":g}", kaynak,
                         "%g bilimsel gösterime düşürür — bkz. _tr_sayi")

    def test_ayirac_kurali_yeniden_yazilmadi(self) -> None:
        """Binlik/ondalık dönüşümü `bicimle_tr_sayi` dışında tekrarlanamaz.

        Muaf tek yer `_guven_tr`: güven skoru SABİT iki basamakla yazılır
        (0,60 ≠ 0,6) ve eşikle aynı biçimde okunmak zorundadır.
        """
        for ad, fn in vars(structured).items():
            if not callable(fn) or not hasattr(fn, "__module__"):
                continue
            if getattr(fn, "__module__", None) != structured.__name__:
                continue
            if ad == "_guven_tr":
                continue
            try:
                kaynak = inspect.getsource(fn)
            except (OSError, TypeError):
                continue
            with self.subTest(fonksiyon=ad):
                self.assertNotRegex(
                    kaynak, re.escape('replace(".", ",")'),
                    "ayıraç kuralı ikinci kez yazılmış")

    def test_kanonik_bicimlendiriciyi_kullanir(self) -> None:
        from src.normalization.normalize import bicimle_tr_sayi
        self.assertIn("bicimle_tr_sayi", inspect.getsource(_tr_sayi))
        self.assertEqual(_tr_sayi(2500.0), bicimle_tr_sayi(2500.0))


if __name__ == "__main__":
    unittest.main()
