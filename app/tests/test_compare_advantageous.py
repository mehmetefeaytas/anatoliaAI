"""§5.7 "En Avantajlı Kampanya" — çok alanlı bileşik sıralama testleri.

İlgili: ../src/comparison/compare.py (`rank_advantageous`)
        CLAUDE.md §17 (adil kıyas), §19 (halüsinasyon yasağı)

Şartname §5.7 beş karşılaştırma ölçütü sayar; ilk dördü tek alanlıdır
(`rank()`), beşincisi bileşiktir. Bu dosya bileşik skorun üç sözünü test eder:

1. **Eksik veri ≠ kötü değer.** Alanı olmayan kampanya sıfır puan almaz;
   kapsama oranı ayrı raporlanır ve düşükse `comparable=False` olur.
2. **Yön doğru.** Düşük-iyi alanla yüksek-iyi alan skora ters yönde katkı verir.
3. **Şeffaflık.** Tek bir "87 puan" değil, alan alan alt puanlar döner.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.comparison.compare import (  # noqa: E402
    DEFAULT_WEIGHTS,
    WEIGHT_RATIONALE,
    best_advantageous,
    rank_advantageous,
    weight_manifest,
)


def _row(bank: str, **fields) -> dict:
    return {"bank": bank, "bank_name": bank.upper(), "fields": fields}


def _comp(score, field_name):
    return next(c for c in score.components if c.field_name == field_name)


class TestAgirliklar(unittest.TestCase):
    def test_her_agirligin_gerekcesi_var(self):
        # Jüri "neden bu ağırlık" diye soracak; gerekçesiz ağırlık kabul edilmez.
        for fname in DEFAULT_WEIGHTS:
            self.assertIn(fname, WEIGHT_RATIONALE, fname)
            self.assertGreater(len(WEIGHT_RATIONALE[fname]), 40, fname)

    def test_agirliklar_toplami_bir(self):
        self.assertAlmostEqual(sum(DEFAULT_WEIGHTS.values()), 1.0, places=6)

    def test_manifest_apiden_okunabilir(self):
        man = weight_manifest()
        self.assertEqual(len(man), len(DEFAULT_WEIGHTS))
        self.assertEqual(man[0]["field_name"], "kar_payi_orani")  # en yüksek
        self.assertEqual(man[0]["direction"], "dusuk_iyi")
        self.assertTrue(all(m["rationale"] for m in man))

    def test_agirlik_disaridan_gecersiz_kilinabilir(self):
        rows = [_row("a", kar_payi_orani=1.89, vade_ay=12),
                _row("b", kar_payi_orani=2.49, vade_ay=120)]
        # Yalnız vadeye bakan bir ağırlık setiyle b kazanmalı.
        ranked = rank_advantageous(rows, weights={"vade_ay": 1.0})
        self.assertEqual(ranked[0].bank, "b")


class TestYon(unittest.TestCase):
    def test_dusuk_kar_payi_daha_iyi(self):
        rows = [_row("pahali", kar_payi_orani=4.50),
                _row("ucuz", kar_payi_orani=1.89)]
        ranked = rank_advantageous(rows)
        self.assertEqual(ranked[0].bank, "ucuz")
        self.assertEqual(_comp(ranked[0], "kar_payi_orani").normalized, 1.0)

    def test_yuksek_odul_daha_iyi(self):
        rows = [_row("az", odul_miktari={"value": 200.0, "currency": "TRY"}),
                _row("cok", odul_miktari={"value": 5000.0, "currency": "TRY"})]
        self.assertEqual(rank_advantageous(rows)[0].bank, "cok")

    def test_ters_yonlu_alanlar_dogru_toplanir(self):
        # a: kâr payı iyi (düşük), vade kötü (kısa)
        # b: kâr payı kötü (yüksek), vade iyi (uzun)
        # kâr payı ağırlığı (0.40) vadeninkinden (0.15) büyük → a kazanmalı.
        rows = [_row("a", kar_payi_orani=1.89, vade_ay=12),
                _row("b", kar_payi_orani=4.50, vade_ay=120)]
        ranked = rank_advantageous(rows)
        self.assertEqual(ranked[0].bank, "a")
        self.assertEqual(_comp(ranked[0], "kar_payi_orani").normalized, 1.0)
        self.assertEqual(_comp(ranked[0], "vade_ay").normalized, 0.0)


class TestEksikVeri(unittest.TestCase):
    """Eksik alan SIFIR PUAN DEĞİLDİR — "veri yok" ile "kötü değer" ayrıdır."""

    def test_eksik_alan_sifir_puan_saymaz(self):
        # a'nın yalnız kâr payı var ve o alanda en iyisi; eksik alanlar onu
        # sıfıra çekmemeli — skoru bilinen ölçütler üzerinden hesaplanır.
        rows = [_row("a", kar_payi_orani=1.89),
                _row("b", kar_payi_orani=4.50, vade_ay=120,
                     odul_miktari={"value": 100.0, "currency": "TRY"})]
        ranked = {c.bank: c for c in rank_advantageous(rows)}
        self.assertEqual(ranked["a"].score, 1.0)
        self.assertEqual(_comp(ranked["a"], "vade_ay").normalized, None)
        self.assertEqual(_comp(ranked["a"], "vade_ay").note, "veri yok")

    def test_kapsama_raporlanir(self):
        rows = [_row("tam", kar_payi_orani=1.89, vade_ay=120,
                     odul_miktari={"value": 100.0, "currency": "TRY"},
                     masraf_durumu={"has_fee": False, "amount": 0.0}),
                _row("eksik", kar_payi_orani=2.49)]
        ranked = {c.bank: c for c in rank_advantageous(rows)}
        self.assertAlmostEqual(ranked["tam"].coverage, 1.0, places=6)
        self.assertAlmostEqual(ranked["eksik"].coverage, 0.40 / 0.90, places=6)

    def test_dusuk_kapsama_kiyaslanamaz_isaretlenir(self):
        # CLAUDE.md §17: koşullar/veri yetersizse uydurma sıralama yapma.
        rows = [_row("tam", kar_payi_orani=2.49, vade_ay=120,
                     odul_miktari={"value": 100.0, "currency": "TRY"},
                     masraf_durumu={"has_fee": True, "amount": 500.0}),
                _row("tekalan", odul_miktari={"value": 9999.0, "currency": "TRY"})]
        ranked = rank_advantageous(rows)
        by = {c.bank: c for c in ranked}
        self.assertTrue(by["tam"].comparable)
        self.assertFalse(by["tekalan"].comparable)
        self.assertIn("kapsama", by["tekalan"].note)
        # Kıyaslanamayan skoru 1.0 olsa bile listenin SONUNA gider.
        self.assertEqual(ranked[-1].bank, "tekalan")
        self.assertEqual(best_advantageous(rows).bank, "tam")

    def test_hicbir_olcut_olculemezse_skor_none(self):
        rows = [_row("a"), _row("b")]
        ranked = rank_advantageous(rows)
        self.assertTrue(all(c.score is None and not c.comparable for c in ranked))
        self.assertEqual(ranked[0].note, "hiçbir ölçüt ölçülemedi")

    def test_populasyonda_hic_olmayan_alanin_agirligi_dagitilir(self):
        # Kimsede finansman_tutari yoksa herkesin kapsaması sebepsiz düşmemeli.
        rows = [_row("a", kar_payi_orani=1.89, vade_ay=12,
                     odul_miktari={"value": 1.0, "currency": "TRY"},
                     masraf_durumu={"has_fee": False, "amount": 0.0}),
                _row("b", kar_payi_orani=2.49, vade_ay=24,
                     odul_miktari={"value": 2.0, "currency": "TRY"},
                     masraf_durumu={"has_fee": False, "amount": 0.0})]
        for c in rank_advantageous(rows):
            self.assertAlmostEqual(c.coverage, 1.0, places=6)
            self.assertNotIn("finansman_tutari",
                             {x.field_name for x in c.components})


class TestMasrafDurumuSayisallastirma(unittest.TestCase):
    """`masraf_durumu` bir dict; sayısallaştırma kuralı açıkça test edilir."""

    def test_masrafsiz_en_iyi(self):
        rows = [_row("ucretli", masraf_durumu={"has_fee": True, "amount": 750.0}),
                _row("masrafsiz", masraf_durumu={"has_fee": False, "amount": 0.0})]
        ranked = rank_advantageous(rows)
        self.assertEqual(ranked[0].bank, "masrafsiz")
        self.assertEqual(_comp(ranked[0], "masraf_durumu").normalized, 1.0)

    def test_tutari_bilinmeyen_ucret_skorlanmaz(self):
        # {"has_fee": True, "amount": None} → sıfır SAYILMAZ (bu "masrafsız"
        # demek olurdu) ve en kötü değer ATANMAZ (değer uydurmak olurdu).
        # Alan skorlanmaz, kapsama düşer, not görünür kalır.
        rows = [_row("bilinmeyen", kar_payi_orani=1.89,
                     masraf_durumu={"has_fee": True, "amount": None}),
                _row("bilinen", kar_payi_orani=2.49,
                     masraf_durumu={"has_fee": True, "amount": 750.0})]
        by = {c.bank: c for c in rank_advantageous(rows)}
        comp = _comp(by["bilinmeyen"], "masraf_durumu")
        self.assertIsNone(comp.normalized)
        self.assertEqual(comp.contribution, 0.0)
        self.assertEqual(comp.note, "ücret var, tutarı belirtilmemiş")
        self.assertLess(by["bilinmeyen"].coverage, by["bilinen"].coverage)

    def test_oran_bicimli_ucret_tl_ile_karistirilmaz(self):
        rows = [_row("oran", masraf_durumu={"rate": 0.5}, kar_payi_orani=1.89),
                _row("tutar", masraf_durumu={"has_fee": True, "amount": 750.0},
                     kar_payi_orani=2.49)]
        by = {c.bank: c for c in rank_advantageous(rows)}
        self.assertIsNone(_comp(by["oran"], "masraf_durumu").normalized)
        self.assertIn("kıyaslanamaz", _comp(by["oran"], "masraf_durumu").note)

    def test_farkli_para_birimi_skorlanmaz(self):
        rows = [_row("usd", odul_miktari={"value": 100.0, "currency": "USD"},
                     kar_payi_orani=1.89),
                _row("try", odul_miktari={"value": 100.0, "currency": "TRY"},
                     kar_payi_orani=2.49)]
        by = {c.bank: c for c in rank_advantageous(rows)}
        self.assertIsNone(_comp(by["usd"], "odul_miktari").normalized)
        self.assertIn("para birimi", _comp(by["usd"], "odul_miktari").note)


class TestAralik(unittest.TestCase):
    def test_aralik_en_iyi_ucla_skorlanir_ve_not_dusulur(self):
        # Kâr payı düşük-iyi → aralığın ALT sınırı; not kullanıcıya gösterilir.
        rows = [_row("aralikli", kar_payi_orani={"min": 1.89, "max": 4.99}),
                _row("sabit", kar_payi_orani=2.49)]
        by = {c.bank: c for c in rank_advantageous(rows)}
        comp = _comp(by["aralikli"], "kar_payi_orani")
        self.assertEqual(comp.normalized, 1.0)
        self.assertIn("aralık", comp.note)

    def test_vadede_aralik_ust_uctan_skorlanir(self):
        rows = [_row("a", vade_ay={"min": 12, "max": 120}),
                _row("b", vade_ay=60)]
        by = {c.bank: c for c in rank_advantageous(rows)}
        self.assertEqual(_comp(by["a"], "vade_ay").normalized, 1.0)

    def test_dejenere_aralik_duz_sayi_gibi(self):
        rows = [_row("a", kar_payi_orani={"min": 1.89, "max": 1.89}),
                _row("b", kar_payi_orani=2.49)]
        by = {c.bank: c for c in rank_advantageous(rows)}
        self.assertIsNone(_comp(by["a"], "kar_payi_orani").note)


class TestEsitlikVeTekAday(unittest.TestCase):
    def test_hepsi_esitse_hepsi_tam_puan(self):
        rows = [_row(b, kar_payi_orani=2.00, vade_ay=36) for b in ("a", "b", "c")]
        ranked = rank_advantageous(rows)
        self.assertTrue(all(c.score == 1.0 for c in ranked))
        self.assertTrue(all(c.comparable for c in ranked))

    def test_tek_aday_kendisiyle_kiyaslanmaz_ama_skorlanir(self):
        ranked = rank_advantageous([_row("a", kar_payi_orani=4.99, vade_ay=6)])
        self.assertEqual(ranked[0].score, 1.0)
        self.assertTrue(ranked[0].comparable)

    def test_bos_giris(self):
        self.assertEqual(rank_advantageous([]), [])
        self.assertIsNone(best_advantageous([]))

    def test_esit_degerler_ayni_normalize_alir(self):
        rows = [_row("a", kar_payi_orani=2.00), _row("b", kar_payi_orani=2.00),
                _row("c", kar_payi_orani=5.00)]
        by = {c.bank: c for c in rank_advantageous(rows)}
        self.assertEqual(_comp(by["a"], "kar_payi_orani").normalized,
                         _comp(by["b"], "kar_payi_orani").normalized)
        self.assertEqual(_comp(by["c"], "kar_payi_orani").normalized, 0.0)


class TestUcDegereDayaniklilik(unittest.TestCase):
    """Min-max yerine SIRALAMA tabanlı normalizasyon seçildi — nedeni test edilir."""

    def test_tek_uc_deger_sirlamayi_bozmaz(self):
        # Korpusta ölçülen gerçek uç değer: vade_ay = 24.312 (çıkarım gürültüsü).
        # Min-max normalizasyonda 12 ile 120 arasındaki fark 0.0044'e inerdi ve
        # kâr payı farkı bunu tamamen ezerdi. Sıralama tabanlı normalizasyonda
        # 120 ay hâlâ 60 aydan belirgin biçimde iyidir.
        rows = [_row("uc", vade_ay=24312), _row("uzun", vade_ay=120),
                _row("orta", vade_ay=60), _row("kisa", vade_ay=12)]
        by = {c.bank: c for c in rank_advantageous(rows)}
        self.assertEqual(_comp(by["uc"], "vade_ay").normalized, 1.0)
        self.assertAlmostEqual(_comp(by["uzun"], "vade_ay").normalized,
                               2 / 3, places=6)
        self.assertAlmostEqual(_comp(by["orta"], "vade_ay").normalized,
                               1 / 3, places=6)
        self.assertEqual(_comp(by["kisa"], "vade_ay").normalized, 0.0)


class TestSeffaflik(unittest.TestCase):
    def test_alt_puanlar_gorunur_ve_toplami_skoru_verir(self):
        rows = [_row("a", kar_payi_orani=1.89, vade_ay=120),
                _row("b", kar_payi_orani=4.50, vade_ay=12)]
        c = rank_advantageous(rows)[0]
        covered = [x for x in c.components if x.normalized is not None]
        total_w = sum(x.weight for x in covered)
        self.assertAlmostEqual(
            sum(x.contribution for x in covered) / total_w, c.score, places=9)
        # Ağırlığı büyük olan bileşen önce listelenir (UI okunabilirliği).
        self.assertEqual(c.components[0].field_name, "kar_payi_orani")

    def test_to_dict_json_uyumlu(self):
        import json
        rows = [_row("a", kar_payi_orani=1.89,
                     masraf_durumu={"has_fee": False, "amount": 0.0}),
                _row("b", kar_payi_orani=2.49,
                     masraf_durumu={"has_fee": True, "amount": None})]
        payload = [c.to_dict() for c in rank_advantageous(rows)]
        json.dumps(payload, ensure_ascii=False)  # patlamamalı
        self.assertIn("components", payload[0])
        self.assertIn("coverage", payload[0])


if __name__ == "__main__":
    unittest.main()
