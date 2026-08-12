"""Serbest metin alanı ayrı ölçülür — gizlenmez, doğru ölçütle raporlanır.

İlgili: ../eval/run_eval.py (`yapisal_kesit`, `_serbest_metin_alani`,
        `format_table`, `markdown_report`)
        ../scripts/gold_schema.py (`TEXT_LIST_FIELDS`, `LABEL_LIST_FIELDS`)

## Bu testlerin varlık sebebi — ÖLÇÜLDÜ (2026-08-12, gold.v2, 48 kayıt)

`kampanya_kosullari` tek başına 36 FP ve 33 FN üretiyor ve mikro-F1'i
**0,619'dan 0,439'a** çekiyor (zor vakalarda 0,634 -> 0,458). Tek alan,
diğer 11 alanın toplam performansını 0,18 puan gölgeliyordu.

Sebep ÖLÇÜT hatasıdır, sistem hatası değil: alan serbest cümle listesi
döndürür ("Kampanyaya dahil olmak için X gerekir") ve span/jeton eşleşmesiyle
F1 ölçmek metodolojik olarak yanlıştır.

## Bu testlerin ASIL işi: gizlemediğimizi kanıtlamak

Bir metrik kesitinin en büyük riski, kötü sayıyı sessizce düşürmektir.
Aşağıdaki testler tam da bunu engeller:

* serbest metin alanı ana tablodan KAYBOLMAZ,
* raporda hangi alanın neden dışarıda bırakıldığı YAZILI olur,
* etiket listesi (`hedef_kitle`) yanlışlıkla dışarı ATILMAZ — o kapalı
  kümeden seçilir, eşleşmesi anlamlıdır.
"""

from __future__ import annotations

import unittest

from eval.run_eval import (
    Counts,
    _serbest_metin_alani,
    macro_f1,
    micro,
    yapisal_kesit,
)


def _c(tp=0, fp=0, fn=0, tn=0) -> Counts:
    c = Counts()
    c.tp, c.fp, c.fn, c.tn = tp, fp, fn, tn
    return c


class TestSerbestMetinAyrimi(unittest.TestCase):

    def test_kampanya_kosullari_serbest_metindir(self):
        self.assertTrue(_serbest_metin_alani("kampanya_kosullari"))

    def test_hedef_kitle_serbest_metin_DEGILDIR(self):
        """Etiket listesi kapalı kümeden seçilir; eşleşmesi anlamlıdır.

        Bu ayrım olmasaydı kesit iki liste alanını birden atardı ve
        «yapılandırılmış» sayı hak etmediği kadar yükselirdi.
        """
        self.assertFalse(_serbest_metin_alani("hedef_kitle"))

    def test_sayisal_alanlar_kesitte_kalir(self):
        for alan in ("kar_payi_orani", "vade_ay", "finansman_tutari"):
            with self.subTest(alan=alan):
                self.assertFalse(_serbest_metin_alani(alan))


class TestYapisalKesit(unittest.TestCase):

    TABLO = {
        "kar_payi_orani": _c(tp=2, fp=0, fn=1),
        "vade_ay": _c(tp=3, fp=3, fn=2),
        "hedef_kitle": _c(tp=4, fp=8, fn=14),
        "kampanya_kosullari": _c(tp=0, fp=36, fn=33),
    }

    def test_yalniz_serbest_metin_cikarilir(self):
        k = yapisal_kesit(self.TABLO)
        self.assertEqual(set(k),
                         {"kar_payi_orani", "vade_ay", "hedef_kitle"})

    def test_kesit_mikro_f1i_yukseltir(self):
        tum = micro(self.TABLO).f1()
        yap = micro(yapisal_kesit(self.TABLO)).f1()
        self.assertGreater(yap, tum)

    def test_kaynak_tablo_DEGISTIRILMEZ(self):
        """Kesit kopya döndürür; ana tablo yerinde değişirse manşet sayı bozulur."""
        once = dict(self.TABLO)
        yapisal_kesit(self.TABLO)
        self.assertEqual(dict(self.TABLO), once)
        self.assertIn("kampanya_kosullari", self.TABLO)

    def test_serbest_metin_yoksa_kesit_ayni_tablodur(self):
        t = {"vade_ay": _c(tp=1)}
        self.assertEqual(set(yapisal_kesit(t)), set(t))

    def test_makro_da_kesitten_hesaplanabilir(self):
        self.assertNotEqual(macro_f1(self.TABLO),
                            macro_f1(yapisal_kesit(self.TABLO)))


class TestGizlemeYok(unittest.TestCase):
    """Kesit bir GİZLEME aracına dönüşmemeli."""

    def test_ana_tabloda_serbest_metin_alani_DURUR(self):
        from eval.run_eval import format_table
        cikti = format_table("SINAMA", TestYapisalKesit.TABLO)
        self.assertIn("kampanya_kosullari", cikti,
                      "serbest metin alanı ana tablodan silinmiş")

    def test_hangi_alanin_disarida_kaldigi_YAZILI(self):
        from eval.run_eval import format_table
        cikti = format_table("SINAMA", TestYapisalKesit.TABLO)
        self.assertIn("MİKRO (yapısal)", cikti)
        self.assertIn("HARİÇ", cikti,
                      "dışarıda bırakılan alan rapora yazılmamış")

    def test_iki_sayi_YAN_YANA_durur(self):
        from eval.run_eval import format_table
        cikti = format_table("SINAMA", TestYapisalKesit.TABLO)
        self.assertIn("MİKRO", cikti)
        self.assertIn("MİKRO (yapısal)", cikti)


if __name__ == "__main__":                                # pragma: no cover
    unittest.main()
