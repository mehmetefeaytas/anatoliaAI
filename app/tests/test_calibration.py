"""Kalibrasyon ölçümü doğru şeyi ölçüyor mu?

İlgili: ../eval/calibration.py, ../src/comparison/compare.py (`ASGARI_GUVEN`)

## Bu testlerin varlık sebebi

`eval/calibration.py` iki docstring'de vaat edilmiş ama hiç yazılmamıştı.
Bir ölçüm modülünün en tehlikeli hata biçimi, yanlış şeyi ölçüp doğru
görünmektir (aynı ders `eval/rag_eval.py` yazılırken iki kez yaşandı:
çekimserlik önce 0,267 sonra 0,333 ölçüldü, doğrusu 30/30'du).

Bu yüzden formüller SABİT, elle hesaplanabilir girdilerle sınanıyor —
gold set üzerinden değil. Gold değişince test kırılmamalı; kırılırsa
formül değişmiş demektir.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from eval.calibration import ASGARI_KARAR, Karar, as_dict, bicimle, hesapla


def _k(guven: float, dogru: bool, *, doc: str = "d", alan: str = "vade_ay"):
    return Karar(doc_id=doc, field=alan, guven=guven, dogru=dogru,
                 kaynak="rule_heuristic")


class ECEFormuluDOGRU(unittest.TestCase):

    def test_mukemmel_kalibre_ECE_SIFIR(self) -> None:
        """0,95 diyen 40 karardan 38'i doğruysa ECE ~0 olmalı.

        Sayı 40: `ASGARI_KARAR = 30` altında ECE bilerek hesaplanmıyor
        (bkz. `AZORNEKTEECEHESAPLANMAZ`). 38/40 = 0,95 = ortalama güven.
        """
        kararlar = ([_k(0.95, True, doc=f"d{i}") for i in range(38)]
                    + [_k(0.95, False, doc="dx"), _k(0.95, False, doc="dy")])
        r = hesapla(kararlar, resamples=50)
        self.assertIsNotNone(r.ece)
        self.assertAlmostEqual(0.0, r.ece, places=2)

    def test_tam_ters_kalibre_ECE_BUYUK(self) -> None:
        """0,95 diyen hiçbir karar doğru değilse ECE ~0,95."""
        kararlar = [_k(0.95, False, doc=f"d{i}") for i in range(40)]
        r = hesapla(kararlar, resamples=50)
        self.assertAlmostEqual(0.95, r.ece, places=2)
        self.assertAlmostEqual(0.95, r.mce, places=2)

    def test_MCE_en_kotu_kovayi_verir(self) -> None:
        """Ortalama iyi, tek kova felaket — ECE gizler, MCE gizlemez."""
        iyi = [_k(0.72, True, doc=f"i{i}") for i in range(35)]   # fark ~0,28
        kotu = [_k(0.95, False, doc=f"k{i}") for i in range(5)]  # fark 0,95
        r = hesapla(iyi + kotu, resamples=50)
        self.assertGreater(r.mce, r.ece,
                           "MCE, ECE'den büyük olmalı: en kötü kova "
                           "ortalamadan sapmalı")
        self.assertAlmostEqual(0.95, r.mce, places=2)

    def test_brier_bilinen_deger(self) -> None:
        """Elle hesaplanabilir: (0,5-1)^2 ve (0,5-0)^2 -> 0,25."""
        kararlar = ([_k(0.5, True, doc=f"a{i}") for i in range(20)]
                    + [_k(0.5, False, doc=f"b{i}") for i in range(20)])
        r = hesapla(kararlar, resamples=50)
        self.assertAlmostEqual(0.25, r.brier, places=3)


class AZORNEKTEECEHESAPLANMAZ(unittest.TestCase):
    """Az örnek kalibrasyonu güzelleştirir; sayı vermek yanıltıcı olur."""

    def test_asgarinin_altinda_ECE_None(self) -> None:
        r = hesapla([_k(0.9, True, doc=f"d{i}") for i in range(5)],
                    resamples=50)
        self.assertIsNone(r.ece, "az kararla ECE yine hesaplandı")
        self.assertIsNone(r.mce)
        self.assertIn("HESAPLANMADI", bicimle(r))

    def test_asgari_esikte_hesaplanir(self) -> None:
        r = hesapla([_k(0.9, True, doc=f"d{i}") for i in range(ASGARI_KARAR)],
                    resamples=50)
        self.assertIsNotNone(r.ece)


class ESIKANALIZIYONUSOYLER(unittest.TestCase):
    """Kapı ancak altta kalanlar daha YANLIŞSA gerekçelidir."""

    def test_ayirt_edici_kapi_ONAYLANIR(self) -> None:
        kararlar = ([_k(0.9, True, doc=f"u{i}") for i in range(30)]
                    + [_k(0.4, False, doc=f"a{i}") for i in range(10)])
        r = hesapla(kararlar, resamples=50)
        self.assertEqual(30, r.esik_ustu_sayi)
        self.assertEqual(10, r.esik_alti_sayi)
        self.assertAlmostEqual(1.0, r.esik_ustu_dogruluk)
        self.assertAlmostEqual(0.0, r.esik_alti_dogruluk)
        self.assertIn("ayırt edici", bicimle(r))

    def test_GEREKCESIZ_kapi_UYARIR(self) -> None:
        """Altta kalanlar üstteki kadar doğruysa kapı veri atıp iş yapmıyor."""
        kararlar = ([_k(0.9, True, doc=f"u{i}") for i in range(20)]
                    + [_k(0.4, True, doc=f"a{i}") for i in range(20)])
        r = hesapla(kararlar, resamples=50)
        self.assertIn("GEREKÇESİZ", bicimle(r),
                      "eşik hiçbir şey ayırmıyor ama rapor uyarmıyor")

    def test_ZAYIF_ayrim_UYARIR(self) -> None:
        kararlar = ([_k(0.9, True, doc=f"u{i}") for i in range(19)]
                    + [_k(0.9, False, doc="ux")]
                    + [_k(0.4, True, doc=f"a{i}") for i in range(18)]
                    + [_k(0.4, False, doc="ax"), _k(0.4, False, doc="ay")])
        r = hesapla(kararlar, resamples=50)   # 0,95 vs 0,90 -> ayrım 0,05
        self.assertIn("ZAYIF", bicimle(r))


class RAPORICERIGI(unittest.TestCase):

    def test_yon_AŞIRI_mi_YETERSIZ_mi_yazilir(self) -> None:
        """Tek sayı yönü söylemez; tablo söylemeli."""
        asiri = hesapla([_k(0.95, False, doc=f"d{i}") for i in range(40)],
                        resamples=50)
        self.assertIn("AŞIRI güven", bicimle(asiri))
        yetersiz = hesapla([_k(0.7, True, doc=f"d{i}") for i in range(40)],
                           resamples=50)
        self.assertIn("yetersiz güven", bicimle(yetersiz))

    def test_skor_KAYNAGI_raporlanir(self) -> None:
        """`confidence_source` ayrımı raporda görünmeli."""
        r = hesapla([_k(0.9, True, doc=f"d{i}") for i in range(35)],
                    resamples=50)
        self.assertEqual({"rule_heuristic": 35}, r.kaynak_dagilimi)
        self.assertIn("rule_heuristic", bicimle(r))

    def test_json_ciktisi_bos_kovalari_ATMAZ_ama_yazmaz(self) -> None:
        r = hesapla([_k(0.9, True, doc=f"d{i}") for i in range(35)],
                    resamples=50)
        d = as_dict(r)
        self.assertEqual(35, d["karar_sayisi"])
        self.assertTrue(all(k["sayi"] > 0 for k in d["kovalar"]),
                        "boş kova JSON'a yazıldı — gürültü")

    def test_SICAKLIK_OLCEKLEME_UYGULANMADIGI_yazili(self) -> None:
        """Modül ölçer, skoru DEĞİŞTİRMEZ; rapor bunu söylemeli."""
        r = hesapla([_k(0.9, True, doc=f"d{i}") for i in range(35)],
                    resamples=50)
        self.assertIn("UYGULAMAZ", bicimle(r))


if __name__ == "__main__":
    unittest.main()
