"""gold aday örnekleyicisinin HAVUZ İÇİ tekilliği — regresyon.

Çalıştır:  python -m unittest tests.test_sample_gold_tekillik  (app/ kökünden)

## Neden bu test var

`sample_gold_v2` docstring'inin 2. ilkesi: "Aynı belgeyi iki kez ölçmek n'i
şişirir, bilgi eklemez." Bu ilke uzun süre yalnız MEVCUT gold'a karşı
uygulandı; havuzun kendi içinde uygulanmadı.

Kusur 2026-08-13'te gold'u 48'den 75'e çıkarmak için örnek alınırken yakalandı:
27 kayıtlık örnekte 26 farklı `content_hash` çıktı. Tekrarlayan belge Türkiye
Finans taşıt finansmanı sayfasıydı ve iki kaydı yalnız URL'nin BÜYÜK/küçük
harfinde ayrışıyordu:

    .../Sayfalar/Tasit-Finansmani.aspx
    .../Sayfalar/tasit-Finansmani.aspx

`orneklendir` içindeki `if a in secilen` koruması sözlük EŞİTLİĞİNE bakar;
`source_url` farklı olduğu için iki kayıt "farklı" görünüyor ve aynı belge
örnekleme iki kez giriyordu. Korpus genelinde bu sınıftan 98 tekrar grubu ve
105 fazladan satır var (1.782 satır -> 1.677 farklı belge), yani kusur tek bir
sayfaya özgü değildi.

Tekilleştirme `havuz()` içinde `content_hash` üzerinden yapılır ve DB satır
sırasına bırakılmaz: aynı hash'ten `source_url`'ü sözlük sırasında en küçük
olan kalır. "İlk geleni tut" DB sırası değişince başka kaydı seçerdi ve örnek
tekrar üretilemez olurdu — determinizm bu betiğin 5. ilkesidir.
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.sample_gold_v2 import orneklendir


def _aday(hash_: str, url: str, tur: str = "Kart", banka: str = "x-katilim") -> dict:
    return {
        "id": f"{banka}--{hash_}",
        "bank_slug": banka,
        "source_url": url,
        "content_hash": hash_,
        "text": "metin",
        "campaign_type": tur,
    }


class HavuzIciTekillik(unittest.TestCase):
    def test_ayni_hash_iki_kez_secilmez(self):
        """Havuzda aynı içerik iki kez varsa örnek onu bir kez almalı.

        Bu testin bulduğu gerçek kusur: kayıtlar yalnız URL harf durumunda
        ayrıştığı için sözlük eşitliği onları farklı sanıyordu.
        """
        havuz = [
            _aday("h1", "https://ornek/Sayfalar/Tasit.aspx"),
            _aday("h1", "https://ornek/Sayfalar/tasit.aspx"),
            _aday("h2", "https://ornek/b"),
            _aday("h3", "https://ornek/c"),
        ]
        secilen = orneklendir(havuz, n=3)
        hashler = [s["content_hash"] for s in secilen]
        self.assertEqual(
            len(hashler), len(set(hashler)),
            f"aynı belge birden çok kez seçildi: {hashler}")

    def test_tekilleştirme_deterministik(self):
        """Aynı havuz + aynı tohum -> aynı örnek (5. ilke)."""
        havuz = [_aday(f"h{i}", f"https://ornek/{i}") for i in range(12)]
        a = [s["content_hash"] for s in orneklendir(havuz, n=6, tohum=42)]
        b = [s["content_hash"] for s in orneklendir(havuz, n=6, tohum=42)]
        self.assertEqual(a, b)


if __name__ == "__main__":
    unittest.main()
