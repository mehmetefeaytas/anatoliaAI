"""İkincil sözlük kaynağı — TKBB Katılım Sözlüğü'nün yüklenmesi ve önceliği.

İlgili: ../src/domain/terminology.py (`IKINCIL_YOL`, `_ikincil_yukle`)
        ../scripts/tkbb_sozluk_hasat.py (kaynağı üreten hasat)
        ../../sorun/tcmb-sozlugu-terim-boslugunu-kapatmiyor.md (elenen alternatif)

## Kilitlenen kural

Çakışan terimde **proje kaydı kazanır**. Proje sözlüğü elle bakımlıdır ve
`degildir` / `risk_notu` / `ayrim_notu` alanlarını taşır — bunlar terminoloji
kaleminin kalbi ve hiçbir dış kaynakta yok. 509 terimlik dış kaynak, 101
terimlik elle bakımlı kaydı EZEMEZ.
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from src.domain import terminology as T


class TestIkincilYukleyici(unittest.TestCase):
    def setUp(self):
        T.onbellegi_temizle()

    def tearDown(self):
        T.onbellegi_temizle()

    def _jsonl(self, kayitlar) -> str:
        d = tempfile.mkdtemp()
        p = Path(d) / "ikincil.jsonl"
        p.write_text("\n".join(json.dumps(k, ensure_ascii=False)
                               for k in kayitlar), encoding="utf-8")
        return str(p)

    def test_terim_ve_tanim_cevrilir(self):
        yol = self._jsonl([{
            "id": "tkbb-1", "terim": "zarûriyyât",
            "tanim": "İnsanoğlunun ihtiyaçları önem sırasına göre üç grupta toplanır.",
            "kaynak_kurum": "TKBB", "kaynak_url": "https://tkbb.org.tr/x/1"}])
        e = T._ikincil_yukle(yol)
        self.assertEqual(len(e), 1)
        self.assertEqual(e[0].kanonik, "zarûriyyât")
        self.assertEqual(e[0].kategori, "tkbb-sozluk")
        self.assertIn("TKBB", e[0].kaynak)
        self.assertIn("tkbb.org.tr", e[0].kaynak)

    def test_kisa_tanim_DUSURULUR(self):
        """Tanımsız bir kayıt terim sorusuna cevap veremez."""
        yol = self._jsonl([{"id": "x", "terim": "abc", "tanim": "kısa"}])
        self.assertEqual(T._ikincil_yukle(yol), ())

    def test_terimsiz_kayit_dusurulur(self):
        yol = self._jsonl([{"id": "x", "terim": "",
                            "tanim": "Yeterince uzun bir tanım metni buraya."}])
        self.assertEqual(T._ikincil_yukle(yol), ())

    def test_bozuk_satir_dosyayi_iptal_ETMEZ(self):
        d = tempfile.mkdtemp()
        p = Path(d) / "i.jsonl"
        p.write_text(
            json.dumps({"id": "a", "terim": "helal",
                        "tanim": "Şer'an yapılmasına izin verilen fiil ve işlemler."},
                       ensure_ascii=False)
            + "\n{bozuk\n"
            + json.dumps({"id": "b", "terim": "haram",
                          "tanim": "Şer'an yasaklanmış fiil ve işlemler bütünü."},
                         ensure_ascii=False) + "\n",
            encoding="utf-8")
        self.assertEqual(len(T._ikincil_yukle(str(p))), 2)

    def test_dosya_yoksa_bos_demet(self):
        self.assertEqual(T._ikincil_yukle("/olmayan/yol/x.jsonl"), ())


class TestOncelik(unittest.TestCase):
    """Gerçek sözlükle: proje kaydı çakışmada kazanır."""

    def setUp(self):
        T.onbellegi_temizle()

    def tearDown(self):
        T.onbellegi_temizle()

    def test_ikincil_kaynak_terim_sayisini_ARTIRIR(self):
        hepsi = T.load_terminology()
        yalniz_proje = T.load_terminology(T.VARSAYILAN_YOL)
        if not Path(T.IKINCIL_YOL).exists():
            self.skipTest("tkbb-sozluk.jsonl yok (hasat koşulmamış)")
        self.assertGreater(len(hepsi), len(yalniz_proje))

    def test_cakismada_PROJE_kaydi_kazanir(self):
        """Murabaha iki kaynakta da var; proje kaydının `sade_aciklama`sı
        korunmalı — TKBB kaydında o alan YOK."""
        if not Path(T.IKINCIL_YOL).exists():
            self.skipTest("tkbb-sozluk.jsonl yok")
        e = [x for x in T.load_terminology()
             if T.tr_fold_ascii(x.kanonik) == "murabaha"]
        self.assertEqual(len(e), 1, "çakışan terim iki kez yüklenmemeli")
        self.assertNotEqual(e[0].kategori, "tkbb-sozluk")
        self.assertTrue(e[0].sade_aciklama)

    def test_SAYACLAR_AYRI(self):
        """`DUSURULEN` proje sözlüğü sağlığını ölçer; ikincil çakışma NORMAL
        ve onu kirletmemeli."""
        T.load_terminology()
        self.assertEqual(sum(T.DUSURULEN.values()), 0)
        if Path(T.IKINCIL_YOL).exists():
            self.assertGreater(sum(T.IKINCIL_CAKISMA.values()), 0)

    def test_acik_yol_verildiginde_ikincil_YUKLENMEZ(self):
        """Testler belirli bir dosyayı istiyordur; izolasyon bozulmamalı."""
        yalniz = T.load_terminology(T.VARSAYILAN_YOL)
        self.assertFalse([x for x in yalniz if x.kategori == "tkbb-sozluk"])


if __name__ == "__main__":
    unittest.main()
