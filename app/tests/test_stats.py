"""İstatistik testleri — BİLİNEN CEVAPLI vakalar.

İlgili: ../eval/stats.py

Bir istatistik kütüphanesini "çalışıyor gibi görünüyor" diye kabul etmek,
ölçmediğimiz bir şeyi ölçtüğümüzü sanmaktır. Buradaki testlerin çoğu ders
kitabından / Wikipedia'dan alınmış, cevabı ÖNCEDEN bilinen vakalardır:

  * McNemar χ²: Wikipedia "McNemar's test" örneği (b=121, c=59 -> χ²≈20,672)
  * Tam binom: elle hesaplanabilir küçük vakalar (b=1, c=4 -> p=0,375)
  * χ² kuyruk: klasik %5 kritik değer (3,841459 -> 0,05)
  * Bootstrap: dejenere girdide GA genişliği 0

Ayrıca bir META test var: bootstrap'ın BELGE düzeyinde örneklediği, alan
düzeyinde örnekleseydi GA'nın daralacağı gösterilerek doğrulanır — yani
kritik istatistiksel kararın gerçekten uygulandığı kanıtlanır.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from eval.stats import (
    DEFAULT_SEED,
    EXACT_THRESHOLD,
    binom_two_sided_p,
    bootstrap_ci,
    bootstrap_diff_ci,
    chi2_sf_1df,
    mcnemar,
    mcnemar_from_pairs,
    percentile,
)


class TestYuzdelik(unittest.TestCase):
    """`percentile` — NumPy'ın doğrusal aradeğerlemesiyle aynı tanım."""

    def test_medyan(self):
        self.assertAlmostEqual(percentile([1, 2, 3, 4, 5], 50), 3.0)

    def test_medyan_cift_uzunluk(self):
        self.assertAlmostEqual(percentile([1, 2, 3, 4], 50), 2.5)

    def test_uc_noktalar(self):
        data = [10, 20, 30, 40]
        self.assertAlmostEqual(percentile(data, 0), 10.0)
        self.assertAlmostEqual(percentile(data, 100), 40.0)

    def test_aradegerleme(self):
        # 4 eleman -> pos = 3 * 0.25 = 0.75 -> 10 + (20-10)*0.75 = 17.5
        self.assertAlmostEqual(percentile([10, 20, 30, 40], 25), 17.5)

    def test_tek_eleman(self):
        self.assertAlmostEqual(percentile([7.0], 95), 7.0)

    def test_siralanmamis_girdi_sorun_degil(self):
        self.assertAlmostEqual(percentile([5, 1, 3, 2, 4], 50), 3.0)

    def test_bos_dizi_hata(self):
        with self.assertRaises(ValueError):
            percentile([], 50)

    def test_gecersiz_q_hata(self):
        with self.assertRaises(ValueError):
            percentile([1, 2, 3], 150)


class TestChi2Kuyruk(unittest.TestCase):
    """`chi2_sf_1df` — scipy olmadan 1 sd χ² sağ kuyruğu."""

    def test_klasik_kritik_deger(self):
        """χ²(1) = 3,841459 -> p = 0,05 (ders kitabı değeri)."""
        self.assertAlmostEqual(chi2_sf_1df(3.841459), 0.05, places=6)

    def test_bir_yuzde_kritik_deger(self):
        """χ²(1) = 6,634897 -> p = 0,01."""
        self.assertAlmostEqual(chi2_sf_1df(6.634897), 0.01, places=6)

    def test_sifir_ve_negatif(self):
        self.assertEqual(chi2_sf_1df(0.0), 1.0)
        self.assertEqual(chi2_sf_1df(-3.0), 1.0)

    def test_monotonluk(self):
        """Büyüyen istatistik küçülen p — kuyruk fonksiyonunun tanımı."""
        values = [chi2_sf_1df(x) for x in (0.5, 1.0, 2.0, 5.0, 10.0)]
        self.assertEqual(values, sorted(values, reverse=True))


class TestBinom(unittest.TestCase):
    """`binom_two_sided_p` — elle hesaplanabilir vakalar."""

    def test_bilinen_1_4(self):
        """b=1, c=4 -> 2*(C(5,0)+C(5,1))/32 = 12/32 = 0,375."""
        self.assertAlmostEqual(binom_two_sided_p(1, 4), 0.375)

    def test_bilinen_0_5(self):
        """b=0, c=5 -> 2*1/32 = 0,0625."""
        self.assertAlmostEqual(binom_two_sided_p(0, 5), 0.0625)

    def test_bilinen_0_10(self):
        """b=0, c=10 -> 2/1024 = 0,001953125."""
        self.assertAlmostEqual(binom_two_sided_p(0, 10), 2 / 1024)

    def test_esit_uyumsuzluk_p_bir(self):
        """b == c -> hiçbir yönde kanıt yok, p 1,0'a sınırlanır."""
        self.assertEqual(binom_two_sided_p(5, 5), 1.0)

    def test_uyumsuz_cift_yok(self):
        self.assertEqual(binom_two_sided_p(0, 0), 1.0)

    def test_simetrik(self):
        self.assertAlmostEqual(binom_two_sided_p(2, 7), binom_two_sided_p(7, 2))

    def test_hicbir_zaman_birden_buyuk(self):
        for b in range(6):
            for c in range(6):
                self.assertLessEqual(binom_two_sided_p(b, c), 1.0)


class TestMcNemar(unittest.TestCase):
    """`mcnemar` — yöntem seçimi + bilinen cevaplar."""

    def test_wikipedia_ornegi_chi2(self):
        """Klasik örnek: b=121, c=59 -> χ² ≈ 20,672, p ≈ 5,4e-6."""
        result = mcnemar(121, 59)
        self.assertEqual(result.method, "chi2_continuity")
        self.assertAlmostEqual(result.statistic, 3721 / 180, places=6)
        self.assertAlmostEqual(result.statistic, 20.6722, places=3)
        self.assertLess(result.p_value, 1e-5)
        self.assertTrue(result.significant)
        self.assertEqual(result.winner, "A")   # b > c -> A daha iyi

    def test_kucuk_orneklemde_tam_binom(self):
        """b+c < 25 -> tam binom; yöntem sonuçta AÇIKÇA döner."""
        result = mcnemar(1, 4)
        self.assertEqual(result.method, "exact_binomial")
        self.assertIsNone(result.statistic)
        self.assertAlmostEqual(result.p_value, 0.375)

    def test_esik_tam_sinirda(self):
        """b+c == 25 -> artık χ² (eşik 'küçüktür' ile tanımlı)."""
        self.assertEqual(mcnemar(13, 12).method, "chi2_continuity")
        self.assertEqual(mcnemar(12, 12).method, "exact_binomial")  # 24 < 25

    def test_esik_sabiti_beklenen_deger(self):
        self.assertEqual(EXACT_THRESHOLD, 25)

    def test_kucuk_orneklemde_yaklasim_hatasi_BUYUK(self):
        """Eşiğin GEREKÇESİ: küçük b+c'de χ² ile tam test belirgin ayrışır.

        Bu test bir belge düzeltmesini kilitler. Docstring bir ara "χ²
        p-değerini olduğundan KÜÇÜK gösterir" diyordu; ölçünce yanlış olduğu
        görüldü — süreklilik düzeltmesiyle genelde tersi olur. Doğru gerekçe
        "hata BÜYÜK ve yönü tek düze değil"dir; test ikisini de gösterir.
        """
        # Göreli hata büyük (b=8, c=0: 0,0078 vs 0,0133)
        exact = binom_two_sided_p(8, 0)
        approx = chi2_sf_1df((abs(8 - 0) - 1) ** 2 / 8)
        self.assertGreater(abs(approx - exact) / exact, 0.5)

        # Yön tek düze DEĞİL: burada χ² daha büyük (konservatif)...
        self.assertGreater(approx, exact)
        # ...burada daha küçük (anti-konservatif).
        exact2 = binom_two_sided_p(3, 1)
        approx2 = chi2_sf_1df((abs(3 - 1) - 1) ** 2 / 4)
        self.assertLess(approx2, exact2)

    def test_buyuk_orneklemde_yaklasim_tam_teste_yakinsar(self):
        """Eşiğin üstünde χ² kullanmak güvenli — yakınsama gösterilir."""
        b, c = 300, 200
        exact = binom_two_sided_p(b, c)
        approx = chi2_sf_1df((abs(b - c) - 1) ** 2 / (b + c))
        self.assertLess(abs(approx - exact), 0.01)

    def test_uyumsuz_cift_yoksa_fark_yok(self):
        result = mcnemar(0, 0)
        self.assertEqual(result.p_value, 1.0)
        self.assertFalse(result.significant)
        self.assertIsNone(result.winner)

    def test_esit_uyumsuzlukta_kazanan_yok(self):
        self.assertIsNone(mcnemar(30, 30).winner)

    def test_b_kucukse_kazanan_B(self):
        result = mcnemar(20, 100)
        self.assertTrue(result.significant)
        self.assertEqual(result.winner, "B")

    def test_uyumlu_ciftler_teste_girmez(self):
        """Uyumlu çift sayısı p-değerini DEĞİŞTİRMEZ — McNemar'ın tanımı."""
        a = mcnemar(3, 9, n_agree_correct=0, n_agree_wrong=0)
        b = mcnemar(3, 9, n_agree_correct=5000, n_agree_wrong=4000)
        self.assertAlmostEqual(a.p_value, b.p_value)
        self.assertEqual(b.n_pairs, 3 + 9 + 5000 + 4000)

    def test_negatif_sayim_hata(self):
        with self.assertRaises(ValueError):
            mcnemar(-1, 3)

    def test_sonuc_sozlugu_yontemi_tasir(self):
        """Rapora yazılan sözlükte hangi yöntemin kullanıldığı GÖRÜNMELİ."""
        data = mcnemar(2, 8).as_dict()
        self.assertEqual(data["method"], "exact_binomial")
        self.assertIn("p_value", data)
        self.assertIn("n_discordant", data)


class TestMcNemarCiftlerden(unittest.TestCase):
    """`mcnemar_from_pairs` — eşleşmiş dizilerden b/c sayımı."""

    def test_sayim_dogru(self):
        a = [True, True, False, False, True]
        b = [True, False, True, False, False]
        result = mcnemar_from_pairs(a, b)
        self.assertEqual(result.n_agree_correct, 1)   # (T,T)
        self.assertEqual(result.b, 2)                 # (T,F) x2
        self.assertEqual(result.c, 1)                 # (F,T)
        self.assertEqual(result.n_agree_wrong, 1)     # (F,F)
        self.assertEqual(result.n_pairs, 5)

    def test_ayni_diziler_uyumsuzluk_yok(self):
        a = [True, False, True, True]
        result = mcnemar_from_pairs(a, a)
        self.assertEqual(result.b, 0)
        self.assertEqual(result.c, 0)
        self.assertEqual(result.p_value, 1.0)

    def test_farkli_uzunluk_hata(self):
        """Sessizce kısaltmak eşleştirmeyi bozar; hata YÜKSELTİLMELİ."""
        with self.assertRaises(ValueError):
            mcnemar_from_pairs([True, False], [True])

    def test_bos_dizi(self):
        result = mcnemar_from_pairs([], [])
        self.assertEqual(result.n_pairs, 0)
        self.assertEqual(result.p_value, 1.0)


class TestBootstrap(unittest.TestCase):
    """`bootstrap_ci` — determinizm, dejenere girdi, belge düzeyi örnekleme."""

    @staticmethod
    def _mean(units):
        return sum(units) / len(units) if units else 0.0

    def test_dejenere_girdide_ga_genisligi_sifir(self):
        """Tüm birimler aynıysa hiçbir yeniden örnekleme farklı sonuç üretemez."""
        result = bootstrap_ci([5.0] * 20, self._mean, n_resamples=200)
        self.assertAlmostEqual(result.point, 5.0)
        self.assertAlmostEqual(result.low, 5.0)
        self.assertAlmostEqual(result.high, 5.0)
        self.assertAlmostEqual(result.width, 0.0)

    def test_deterministik_ayni_seed(self):
        data = [1.0, 2.0, 3.0, 4.0, 5.0, 9.0]
        a = bootstrap_ci(data, self._mean, n_resamples=300, seed=7)
        b = bootstrap_ci(data, self._mean, n_resamples=300, seed=7)
        self.assertEqual((a.low, a.high), (b.low, b.high))

    def test_farkli_seed_farkli_sonuc(self):
        data = [1.0, 2.0, 3.0, 4.0, 5.0, 9.0]
        a = bootstrap_ci(data, self._mean, n_resamples=300, seed=7)
        b = bootstrap_ci(data, self._mean, n_resamples=300, seed=8)
        self.assertNotEqual((a.low, a.high), (b.low, b.high))

    def test_seed_sonucta_raporlanir(self):
        """Seed'siz bir GA tekrar üretilemez, dolayısıyla kanıt değildir."""
        result = bootstrap_ci([1.0, 2.0, 3.0], self._mean, n_resamples=50)
        self.assertEqual(result.seed, DEFAULT_SEED)
        self.assertEqual(result.as_dict()["seed"], DEFAULT_SEED)
        self.assertEqual(result.as_dict()["unit"], "document")

    def test_nokta_tahmini_yeniden_orneklenmemis_veriden(self):
        data = [1.0, 2.0, 3.0, 4.0]
        result = bootstrap_ci(data, self._mean, n_resamples=100)
        self.assertAlmostEqual(result.point, 2.5)

    def test_ga_nokta_tahminini_icerir(self):
        data = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0]
        result = bootstrap_ci(data, self._mean, n_resamples=500)
        self.assertLessEqual(result.low, result.point)
        self.assertLessEqual(result.point, result.high)

    def test_bos_girdi_sifir_genislik(self):
        result = bootstrap_ci([], self._mean, n_resamples=100)
        self.assertEqual(result.n_units, 0)
        self.assertAlmostEqual(result.width, 0.0)

    def test_gecersiz_parametreler(self):
        with self.assertRaises(ValueError):
            bootstrap_ci([1.0], self._mean, confidence=1.5)
        with self.assertRaises(ValueError):
            bootstrap_ci([1.0], self._mean, n_resamples=0)

    def test_daha_dusuk_guven_daha_dar_ga(self):
        data = [float(i) for i in range(30)]
        wide = bootstrap_ci(data, self._mean, n_resamples=500, confidence=0.99)
        narrow = bootstrap_ci(data, self._mean, n_resamples=500, confidence=0.80)
        self.assertLess(narrow.width, wide.width)

    def test_fmt_okunabilir(self):
        result = bootstrap_ci([1.0, 2.0], self._mean, n_resamples=50)
        self.assertIn("[", result.fmt())
        self.assertIn("–", result.fmt())


class TestBelgeDuzeyiOrnekleme(unittest.TestCase):
    """KRİTİK: örnekleme birimi BELGE mi, alan mı?

    `eval/stats.py`'nin en önemli kararı budur. Aynı belgeden çıkan alanlar
    bağımsız değildir; alan düzeyinde örneklemek GA'yı YAPAY OLARAK DARALTIR.
    Bu test kararın gerçekten uygulandığını, "belirtildiğini" değil, gösterir.
    """

    def test_belge_kumesi_birlikte_geliyor(self):
        """Bir birim seçildiğinde İÇİNDEKİ TÜM alanlar birlikte gelmeli.

        Kurgu: 10 belge, her biri 10 alanlık blok. Yarısı tamamen doğru (1.0),
        yarısı tamamen yanlış (0.0) — yani belge içi korelasyon TAM.
        """
        docs = [[1.0] * 10 for _ in range(5)] + [[0.0] * 10 for _ in range(5)]

        def mean_of_docs(units):
            flat = [v for unit in units for v in unit]
            return sum(flat) / len(flat) if flat else 0.0

        doc_ci = bootstrap_ci(docs, mean_of_docs, n_resamples=1000, seed=1)

        # Alan düzeyinde örnekleme (YANLIŞ yöntem) — karşılaştırma için.
        flat = [v for doc in docs for v in doc]

        def mean_of_fields(units):
            return sum(units) / len(units) if units else 0.0

        field_ci = bootstrap_ci(flat, mean_of_fields, n_resamples=1000, seed=1)

        # Aynı nokta tahmini...
        self.assertAlmostEqual(doc_ci.point, 0.5)
        self.assertAlmostEqual(field_ci.point, 0.5)
        # ...ama alan düzeyi GA belirgin biçimde DAHA DAR. Bizim uyguladığımız
        # belge düzeyi yöntem daha geniş (ve doğru) aralığı verir.
        self.assertGreater(doc_ci.width, field_ci.width * 1.5)

    def test_n_units_belge_sayisini_raporlar(self):
        docs = [[1.0] * 12 for _ in range(7)]
        result = bootstrap_ci(docs, lambda u: 1.0, n_resamples=50)
        self.assertEqual(result.n_units, 7)   # 7 belge, 84 alan DEĞİL


class TestBootstrapFark(unittest.TestCase):
    """`bootstrap_diff_ci` — EŞLEŞMİŞ fark aralığı."""

    def test_ayni_istatistik_fark_sifir(self):
        data = [1.0, 2.0, 3.0, 4.0]

        def mean(units):
            return sum(units) / len(units) if units else 0.0

        result = bootstrap_diff_ci(data, mean, mean, n_resamples=200)
        self.assertAlmostEqual(result.point, 0.0)
        self.assertAlmostEqual(result.width, 0.0)

    def test_sabit_fark_ga_icinde(self):
        pairs = [(1.0, 0.5), (2.0, 1.5), (3.0, 2.5), (4.0, 3.5)]

        def first(units):
            return sum(p[0] for p in units) / len(units) if units else 0.0

        def second(units):
            return sum(p[1] for p in units) / len(units) if units else 0.0

        result = bootstrap_diff_ci(pairs, first, second, n_resamples=300)
        self.assertAlmostEqual(result.point, 0.5)
        # Fark her çiftte tam olarak 0,5 -> hiçbir yeniden örnekleme değiştiremez.
        self.assertAlmostEqual(result.width, 0.0)
        self.assertGreater(result.low, 0.0)   # 0 GA dışında -> fark kanıtlandı


if __name__ == "__main__":
    unittest.main()
