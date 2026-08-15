"""Kanıt-tazeliği kapısı — ölçemediğini "uyumlu" saymaz.

İlgili: ../scripts/kanit_tazeligi.py

Bu dosyanın koruduğu beş şey:

1. **TR sayı biçimi.** `2.631` binlik, `0,452` ondalık. Karıştırmak `0,452`yi
   452 yapar — kapı sessizce her şeyi sapma sanır ya da hiçbirini görmez.
2. **Ölçülemeyen SAPMA DEĞİLDİR, ama TAMAM da değildir.** Kanıt üretilemiyorsa
   sonuç `kanit_yok` olmalı. `tamam` saymak kapının varlık sebebini siler:
   ölçemediğimiz bir sayıyı doğrulanmış gibi göstermek, tam da kapatmak için
   var olduğu hatanın kendisidir.
3. **Bayat kanıt kanıt değildir.** Başka bir gold'dan ya da kirli ağaçtan
   üretilmiş rapor reddedilmeli — sayı tesadüfen tutsa bile.
4. **Şeması farklı rapor sessizce okunmaz.** Ablasyon raporu aynı gold'dan
   üretilmiş olabilir ama tek-kol metriği taşımaz; elenmezse yanlış sayı okunur.
5. **Tanımsız oran uydurulmaz.** Gold'da hiç `absent` kararı yoksa halüsinasyon
   oranının paydası sıfırdır; `0,0` yazmak yalan olur (CLAUDE.md §19).
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import kanit_tazeligi as K


class TestTrSayi(unittest.TestCase):
    def test_binlik_ayirici(self) -> None:
        self.assertEqual(K.tr_sayi("2.631"), 2631.0)
        self.assertEqual(K.tr_sayi("1.782"), 1782.0)

    def test_ondalik_virgul(self) -> None:
        self.assertEqual(K.tr_sayi("0,452"), 0.452)
        self.assertEqual(K.tr_sayi("0,059"), 0.059)

    def test_yuzde_isareti_atilir(self) -> None:
        self.assertAlmostEqual(K.tr_sayi("%3,9"), 3.9)

    def test_nokta_ondalik_bozulmaz(self) -> None:
        """`0.452` binlik SANILMAMALI — tam kısmı "0", binlik grubu olamaz."""
        self.assertEqual(K.tr_sayi("0.452"), 0.452)

    def test_dort_haneli_binliksiz(self) -> None:
        self.assertEqual(K.tr_sayi("2000"), 2000.0)

    def test_sayi_olmayan_hata_verir(self) -> None:
        with self.assertRaises(ValueError):
            K.tr_sayi("bir hayli")


class TestYazTr(unittest.TestCase):
    def test_tam_sayi_binlikli(self) -> None:
        self.assertEqual(K.yaz_tr(2777.0), "2.777")

    def test_ondalik_virgulle(self) -> None:
        self.assertEqual(K.yaz_tr(0.452), "0,452")


class _RaporTemeli(unittest.TestCase):
    """Sahte `eval/reports` ağacı — gerçek sözleşmenin aynısı."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.kok = Path(self._tmp.name)
        (self.kok / "data" / "gold").mkdir(parents=True)
        (self.kok / "eval" / "reports").mkdir(parents=True)
        self.gold = self.kok / "data" / "gold" / "gold.test.json"
        self.gold.write_text(json.dumps([{"id": "a"}]), encoding="utf-8")
        self._yamalar = [mock.patch.object(K, "KOK", self.kok),
                         mock.patch.object(K, "DEPO", self.kok)]
        for y in self._yamalar:
            y.start()

    def tearDown(self) -> None:
        for y in self._yamalar:
            y.stop()
        self._tmp.cleanup()

    def _rapor(self, ad: str, *, gold_sha: str | None = None, kirli: bool = False,
               matchers: list[str] | None = None, ablasyon: bool = False,
               tn: int = 10, uydurma: int = 1, f1: float = 0.75,
               zaman: str = "2026-08-15T00:00:00+00:00") -> Path:
        d = self.kok / "eval" / "reports" / ad
        d.mkdir()
        (d / "env.json").write_text(json.dumps({
            "gold_sha256": gold_sha if gold_sha is not None
            else K.sha256_dosya(self.gold),
            "git_dirty": kirli,
            "created_utc": zaman,
            "extra": {"bootstrap_resamples": 1000},
        }), encoding="utf-8")
        if ablasyon:
            govde: dict = {"kind": "ablation", "arms": [], "comparisons": []}
        else:
            govde = {"results": [
                {"matcher": m,
                 "macro_f1": 0.6,
                 "micro_f1_kalem": 0.7,
                 "micro": {"f1": f1, "tn": tn, "fp_hallucinated": uydurma}}
                for m in (matchers or ["strict"])]}
        (d / "metrics.json").write_text(json.dumps(govde), encoding="utf-8")
        return d


class TestTazelikKapisi(_RaporTemeli):
    def test_ayni_golddan_uretilmis_rapor_KABUL(self) -> None:
        self._rapor("20260815-000000")
        rapor = K.taze_rapor("gold.test.json", "strict")
        self.assertEqual(rapor.dizin.name, "20260815-000000")

    def test_BASKA_golddan_uretilmis_rapor_RED(self) -> None:
        """Doğru sayıyı taşısa bile başka gold'dan gelen rapor kanıt değildir."""
        self._rapor("20260815-000000", gold_sha="0" * 64)
        with self.assertRaises(K.KanitYok) as ctx:
            K.taze_rapor("gold.test.json", "strict")
        self.assertIn("ölçüm raporu yok", str(ctx.exception))

    def test_KIRLI_agacta_uretilmis_rapor_RED(self) -> None:
        self._rapor("20260815-000000", kirli=True)
        with self.assertRaises(K.KanitYok) as ctx:
            K.taze_rapor("gold.test.json", "strict")
        self.assertIn("git_dirty", str(ctx.exception))

    def test_ablasyon_raporu_tek_kol_metrigi_icin_ELENIR(self) -> None:
        """Aynı gold'dan üretilmiş ama `results` şeması yok — sessiz okunamaz."""
        self._rapor("20260815-120000", ablasyon=True)
        with self.assertRaises(K.KanitYok):
            K.taze_rapor("gold.test.json", "strict")

    def test_ablasyon_varken_ESKI_gecerli_rapor_secilir(self) -> None:
        self._rapor("20260814-000000", zaman="2026-08-14T00:00:00+00:00")
        self._rapor("20260815-120000", ablasyon=True,
                    zaman="2026-08-15T12:00:00+00:00")
        self.assertEqual(K.taze_rapor("gold.test.json", "strict").dizin.name,
                         "20260814-000000")

    def test_en_yeni_gecerli_rapor_secilir(self) -> None:
        self._rapor("20260814-000000", zaman="2026-08-14T00:00:00+00:00")
        self._rapor("20260815-000000", zaman="2026-08-15T00:00:00+00:00")
        self.assertEqual(K.taze_rapor("gold.test.json", "strict").dizin.name,
                         "20260815-000000")

    def test_gold_dosyasi_yoksa_KanitYok(self) -> None:
        with self.assertRaises(K.KanitYok):
            K.taze_rapor("olmayan.json", "strict")


class TestMetrikOkuma(_RaporTemeli):
    def test_mikro_f1_okunur(self) -> None:
        self._rapor("20260815-000000", f1=0.452)
        self.assertAlmostEqual(K.olc_metrik("gold.test.json", "mikro_f1")(), 0.452)

    def test_halusinasyon_orani_dogru_paydayla(self) -> None:
        self._rapor("20260815-000000", tn=444, uydurma=28)
        self.assertAlmostEqual(
            K.olc_metrik("gold.test.json", "halusinasyon")(), 28 / 472)

    def test_absent_karari_YOKSA_oran_TANIMSIZ(self) -> None:
        """Payda sıfırken 0,0 yazmak yalandır — kapı bunu KanitYok sayar."""
        self._rapor("20260815-000000", tn=0, uydurma=0)
        with self.assertRaises(K.KanitYok) as ctx:
            K.olc_metrik("gold.test.json", "halusinasyon")()
        self.assertIn("TANIMSIZ", str(ctx.exception))

    def test_bilinmeyen_anahtar_sessiz_gecmez(self) -> None:
        self._rapor("20260815-000000")
        with self.assertRaises(K.KanitYok):
            K.olc_metrik("gold.test.json", "uydurma_anahtar")()


class TestDenetim(_RaporTemeli):
    def _iddia(self, olcer, desen=r"deger: ([\d,.]+)") -> K.Iddia:
        (self.kok / "BELGE.md").write_text("deger: 1.782\n", encoding="utf-8")
        return K.Iddia(ad="deneme", aciklama="test",
                       desenler=(("BELGE.md", desen),),
                       olcer=olcer, tolerans=0.5)

    def test_uyumlu_sayi_TAMAM(self) -> None:
        iddia = self._iddia(lambda: 1782.0)
        with mock.patch.object(K, "iddialar", lambda: [iddia]):
            (s,) = K.denetle()
        self.assertEqual(s.durum, "tamam")

    def test_sapan_sayi_dosya_ve_satirla_bildirilir(self) -> None:
        iddia = self._iddia(lambda: 1774.0)
        with mock.patch.object(K, "iddialar", lambda: [iddia]):
            (s,) = K.denetle()
        self.assertEqual(s.durum, "sapma")
        self.assertEqual(s.sapmalar[0]["dosya"], "BELGE.md")
        self.assertEqual(s.sapmalar[0]["satir"], 1)
        self.assertEqual(s.sapmalar[0]["yazan"], "1.782")

    def test_OLCULEMEYEN_tamam_SAYILMAZ(self) -> None:
        """Kapının en kritik davranışı: ölçemediğini doğrulanmış sayma."""
        def _patlat() -> float:
            raise K.KanitYok("ölçüm artefaktı yok")

        iddia = self._iddia(_patlat)
        with mock.patch.object(K, "iddialar", lambda: [iddia]):
            (s,) = K.denetle()
        self.assertEqual(s.durum, "kanit_yok")
        self.assertNotEqual(s.durum, "tamam")

    def test_belgede_gecmeyen_iddia_olcum_KOSTURMAZ(self) -> None:
        """Yayımlanmamış bir sayı için pahalı ölçüm koşulmaz."""
        cagrildi = []

        def _olcer() -> float:
            cagrildi.append(1)
            return 0.0

        iddia = K.Iddia(ad="yok", aciklama="", desenler=(("BELGE.md", r"asla(x)"),),
                        olcer=_olcer)
        with mock.patch.object(K, "iddialar", lambda: [iddia]):
            (s,) = K.denetle()
        self.assertEqual(s.durum, "tamam")
        self.assertEqual(cagrildi, [])

    def test_cikis_kodu_sapmada_1_kanit_yoksa_2(self) -> None:
        with mock.patch.object(K, "iddialar", lambda: [self._iddia(lambda: 1774.0)]):
            self.assertEqual(K.main(["--json"]), K.CIKIS_SAPMA)

        def _patlat() -> float:
            raise K.KanitYok("yok")

        with mock.patch.object(K, "iddialar", lambda: [self._iddia(_patlat)]):
            self.assertEqual(K.main(["--json"]), K.CIKIS_KANIT_YOK)

        with mock.patch.object(K, "iddialar", lambda: [self._iddia(lambda: 1782.0)]):
            self.assertEqual(K.main(["--json"]), K.CIKIS_TEMIZ)


class TestGercekIddiaListesi(unittest.TestCase):
    """Liste bozulursa kapı sessizce hiçbir şey denetlemez."""

    def test_iddialar_bos_degil_ve_adlar_tekil(self) -> None:
        adlar = [i.ad for i in K.iddialar()]
        self.assertGreaterEqual(len(adlar), 8)
        self.assertEqual(len(adlar), len(set(adlar)), "yinelenen iddia adı")

    def test_her_desenin_tek_yakalama_grubu_var(self) -> None:
        import re as _re
        for iddia in K.iddialar():
            for dosya, desen in iddia.desenler:
                with self.subTest(iddia=iddia.ad, dosya=dosya):
                    self.assertEqual(
                        _re.compile(desen).groups, 1,
                        "desen tam bir yakalama grubu içermeli")

    def test_banka_sayaci_semsiye_kurulusu_saymaz(self) -> None:
        """TKBB katılım bankası değildir; README de ikisini ayrı sayıyor."""
        self.assertEqual(K.olc_banka_sayisi(), 10.0)


if __name__ == "__main__":
    unittest.main()
