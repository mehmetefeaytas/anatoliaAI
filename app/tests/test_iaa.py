"""Anotatörler arası uyum istatistikleri (stdlib unittest).

Çalıştır:  python -m unittest tests.test_iaa  (app/ kökünden)

Beklenen değerler LİTERATÜRDEN alınmıştır ve her biri testin içinde elle
yeniden türetilebilecek şekilde belgelenmiştir. "Kod ne veriyorsa o doğrudur"
biçiminde bir doğrulama yapılmaz — o, hatayı test etmektir.
"""

import math
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from eval.iaa import (
    cohen_kappa,
    fleiss_kappa,
    fleiss_kappa_from_labels,
    interpret_kappa,
    krippendorff_alpha,
)


def _confusion(yes_yes, yes_no, no_yes, no_no):
    """2x2 karışıklık tablosundan iki anotatörün etiket dizilerini üretir."""
    a = ["E"] * yes_yes + ["E"] * yes_no + ["H"] * no_yes + ["H"] * no_no
    b = ["E"] * yes_yes + ["H"] * yes_no + ["E"] * no_yes + ["H"] * no_no
    return a, b


class TestCohenKappa(unittest.TestCase):
    """Wikipedia "Cohen's kappa" maddesindeki işlenmiş örnekler."""

    def test_simple_example(self):
        """20/5/10/15 -> kappa = 0.40.

        p_o = 35/50 = 0.70
        p_e = 0.5*0.6 + 0.5*0.4 = 0.50
        kappa = (0.70-0.50)/(1-0.50) = 0.40
        """
        a, b = _confusion(20, 5, 10, 15)
        self.assertAlmostEqual(cohen_kappa(a, b), 0.40, places=4)

    def test_same_percentage_different_marginals(self):
        """45/15/25/15 -> kappa = 0.1304.

        p_o = 60/100 = 0.60
        p_e = 0.6*0.7 + 0.4*0.3 = 0.54
        kappa = 0.06/0.46 = 0.13043...
        """
        a, b = _confusion(45, 15, 25, 15)
        self.assertAlmostEqual(cohen_kappa(a, b), 0.06 / 0.46, places=6)

    def test_skewed_marginals(self):
        """25/35/5/35 -> kappa = 0.2593.

        p_o = 60/100 = 0.60
        p_e = 0.6*0.3 + 0.4*0.7 = 0.46
        kappa = 0.14/0.54 = 0.25926...
        """
        a, b = _confusion(25, 35, 5, 35)
        self.assertAlmostEqual(cohen_kappa(a, b), 0.14 / 0.54, places=6)

    def test_perfect_agreement(self):
        labels = ["ok", "fix", "absent", "ok", "unclear"]
        self.assertAlmostEqual(cohen_kappa(labels, labels), 1.0, places=9)

    def test_single_category_is_total_agreement(self):
        """Herkes tek kategoriye yığılmışsa p_e = 1 ve 0/0 belirsizliği doğar.

        Doğru yorum "tam uyum"dur; nan döndürmek raporu okunamaz yapardı.
        """
        labels = ["ok"] * 10
        self.assertEqual(cohen_kappa(labels, labels), 1.0)

    def test_missing_values_are_dropped_pairwise(self):
        """Biri bakmamışsa (None) o çift uyuma girmez."""
        a = ["ok", "fix", None, "ok"]
        b = ["ok", "fix", "absent", None]
        # Kalan 2 çift tam uyumlu.
        self.assertAlmostEqual(cohen_kappa(a, b), 1.0, places=9)

    def test_no_shared_rows_is_nan(self):
        self.assertTrue(math.isnan(cohen_kappa([None, None], ["ok", "fix"])))

    def test_length_mismatch_raises(self):
        with self.assertRaises(ValueError):
            cohen_kappa(["ok"], ["ok", "fix"])


class TestFleissKappa(unittest.TestCase):
    """Wikipedia "Fleiss' kappa" maddesindeki işlenmiş örnek."""

    # 10 birim × 14 anotatör × 5 kategori. Her satır toplamı 14.
    WORKED = [
        [0, 0, 0, 0, 14],
        [0, 2, 6, 4, 2],
        [0, 0, 3, 5, 6],
        [0, 3, 9, 2, 0],
        [2, 2, 8, 1, 1],
        [7, 7, 0, 0, 0],
        [3, 2, 6, 3, 0],
        [2, 5, 3, 2, 2],
        [6, 5, 2, 1, 0],
        [0, 2, 2, 3, 7],
    ]

    def test_worked_example(self):
        """Yayımlanmış sonuç: P̄=0.378, P̄e=0.213, kappa=0.210."""
        for row in self.WORKED:
            self.assertEqual(sum(row), 14, "satır toplamı 14 olmalı")
        self.assertAlmostEqual(fleiss_kappa(self.WORKED), 0.210, places=3)

    def test_intermediate_quantities(self):
        """P̄ ve P̄e ara değerleri de yayımlanan sayılarla tutuyor mu."""
        total = sum(sum(row) for row in self.WORKED)
        p_j = [sum(row[j] for row in self.WORKED) / total for j in range(5)]
        p_expected = sum(p * p for p in p_j)
        agreements = [
            (sum(v * v for v in row) - sum(row)) / (sum(row) * (sum(row) - 1))
            for row in self.WORKED
        ]
        p_bar = sum(agreements) / len(agreements)
        self.assertAlmostEqual(p_bar, 0.378, places=3)
        self.assertAlmostEqual(p_expected, 0.213, places=3)

    def test_perfect_agreement(self):
        matrix = [[4, 0, 0], [0, 4, 0], [0, 0, 4]]
        self.assertAlmostEqual(fleiss_kappa(matrix), 1.0, places=9)

    def test_variable_rater_count_per_unit(self):
        """Biri bir belgeyi bitirmezse tur çöpe gitmemeli — n_i satır bazlı."""
        matrix = [[4, 0], [3, 0], [0, 2]]
        self.assertAlmostEqual(fleiss_kappa(matrix), 1.0, places=9)

    def test_units_with_single_rater_are_ignored(self):
        """Tek anotatörlü birim uyum taşımaz; elenmezse kappa bozulur."""
        with_singleton = self.WORKED + [[1, 0, 0, 0, 0]]
        self.assertAlmostEqual(fleiss_kappa(with_singleton),
                               fleiss_kappa(self.WORKED), places=9)

    def test_from_labels_matches_matrix(self):
        units = [["a", "a", "b"], ["b", "b", "b"], ["a", "b", "a"]]
        matrix = [[2, 1], [0, 3], [2, 1]]
        self.assertAlmostEqual(fleiss_kappa_from_labels(units),
                               fleiss_kappa(matrix), places=9)

    def test_ragged_matrix_raises(self):
        with self.assertRaises(ValueError):
            fleiss_kappa([[1, 1], [1, 1, 1]])


class TestKrippendorffAlpha(unittest.TestCase):
    """Krippendorff (2011) "Computing Krippendorff's Alpha-Reliability" tablosu.

    Gözlemci ×  birim (·  = bakmadı):

        birim :  1  2  3  4  5  6  7  8  9 10 11 12 13 14 15
        A     :  ·  ·  ·  ·  ·  3  4  1  2  1  1  3  3  ·  3
        B     :  1  ·  2  1  3  3  4  3  ·  ·  ·  ·  ·  ·  ·
        C     :  ·  ·  2  1  3  4  4  ·  2  1  1  3  3  ·  4
    """

    X = None
    A = [X, X, X, X, X, 3, 4, 1, 2, 1, 1, 3, 3, X, 3]
    B = [1, X, 2, 1, 3, 3, 4, 3, X, X, X, X, X, X, X]
    C = [X, X, 2, 1, 3, 4, 4, X, 2, 1, 1, 3, 3, X, 4]

    @property
    def units(self):
        return [[self.A[i], self.B[i], self.C[i]] for i in range(15)]

    def test_nominal(self):
        """Elle türetim -> alpha_nominal = 1 - (6/26)/(486/650) = 0.69136.

        Eşlenebilir (>= 2 değerli) birimler: 3,4,5,6,7,8,9,10,11,12,13,15
        n = 26 · değer sayıları: 1->7, 2->4, 3->10, 4->5
        D_o = (1/26) * [u6: 4/2 + u8: 2/1 + u15: 2/1] = 6/26
        D_e = (26^2 - (49+16+100+25)) / (26*25) = 486/650
        """
        self.assertAlmostEqual(krippendorff_alpha(self.units, "nominal"),
                               1 - (6 / 26) / (486 / 650), places=6)

    def test_interval(self):
        """Aynı tablo, interval ölçek -> 1 - (12/26)/(1586/650) = 0.81084.

        D_o = (1/26) * [u6: 4/2 + u8: 8/1 + u15: 2/1] = 12/26
        D_e = 1586/650   (sıralı çiftler üzerinden (v-v')^2 toplamı)
        """
        self.assertAlmostEqual(krippendorff_alpha(self.units, "interval"),
                               1 - (12 / 26) / (1586 / 650), places=6)

    def test_perfect_agreement(self):
        units = [[1, 1, 1], [2, 2, 2], [3, 3, 3]]
        self.assertAlmostEqual(krippendorff_alpha(units, "nominal"), 1.0, places=9)

    def test_all_values_identical_is_one_not_nan(self):
        """Beklenen uyuşmazlık 0 -> 0/0 yerine tam uyum döner."""
        self.assertEqual(krippendorff_alpha([[5, 5], [5, 5]], "nominal"), 1.0)

    def test_single_valued_units_are_dropped(self):
        """Tek anotatörlü birim eklenmesi sonucu değiştirmemeli."""
        base = krippendorff_alpha(self.units, "nominal")
        padded = self.units + [[7, None, None]]
        self.assertAlmostEqual(krippendorff_alpha(padded, "nominal"), base, places=9)

    def test_empty_input_is_nan(self):
        self.assertTrue(math.isnan(krippendorff_alpha([], "nominal")))
        self.assertTrue(math.isnan(krippendorff_alpha([[1, None]], "nominal")))

    def test_ratio_scale_forgives_near_misses(self):
        """`%1,89` vs `%1,90` tam uyuşmazlık SAYILMAMALI.

        Bu, kural katmanının varlık sebebidir: nominal ölçekte üç birimin
        tamamı "anlaşmazlık" olur ve alpha 0'a düşer; oysa anotatörler
        pratikte aynı şeyi söylemiştir.
        """
        units = [[1.89, 1.90], [5.00, 5.05], [10.0, 10.1]]
        nominal = krippendorff_alpha(units, "nominal")
        ratio = krippendorff_alpha(units, "ratio")
        self.assertAlmostEqual(nominal, 0.0, places=6)
        self.assertGreater(ratio, 0.95)

    def test_ratio_still_punishes_real_disagreement(self):
        """Ölçek hatası (120 ay vs 12 ay) yakalanmaya devam etmeli."""
        units = [[120, 12], [36, 3], [60, 6]]
        self.assertLess(krippendorff_alpha(units, "ratio"), 0.5)

    def test_unknown_level_raises(self):
        with self.assertRaises(ValueError):
            krippendorff_alpha([[1, 1]], "ordinal")


class TestThresholdPolicy(unittest.TestCase):
    """Eşik politikası ANOTASYON BAŞLAMADAN sabitlenmiştir (kılavuz §7)."""

    def test_accept(self):
        self.assertEqual(interpret_kappa(0.80)[0], "kabul")
        self.assertEqual(interpret_kappa(0.95)[0], "kabul")

    def test_marginal(self):
        self.assertEqual(interpret_kappa(0.67)[0], "notla")
        self.assertEqual(interpret_kappa(0.79)[0], "notla")

    def test_adjudication_required(self):
        self.assertEqual(interpret_kappa(0.66)[0], "hakemlik")
        self.assertEqual(interpret_kappa(0.0)[0], "hakemlik")
        self.assertEqual(interpret_kappa(-0.2)[0], "hakemlik")

    def test_nan_is_reported_not_silently_passed(self):
        self.assertEqual(interpret_kappa(float("nan"))[0], "olcusuz")


if __name__ == "__main__":
    unittest.main()
