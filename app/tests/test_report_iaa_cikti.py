"""`report_iaa` çıktı adı turu içerir ve aynı adı sessizce EZMEZ.

İlgili: ../scripts/report_iaa.py
        ../data/gold/iaa_report.md            (emekliye ayrılan tursuz ad)
        ../data/gold/iaa-raporu-round0-kalibrasyon-v1.md
        ../data/gold/iaa-raporu-round0-kalibrasyon-v2.md

## Neden bu testler — ölçülmüş hata

`report_iaa.py` çıktıyı hep `data/gold/iaa_report.md`'ye yazıyordu. Round0'ın
**v1** turundan üretilen Fleiss κ = **0,302**'lik rapor, sonradan **v2**
turundan (260 ortak satır, **0 dolu karar**) üretilen raporla sessizce ezildi.

Dosya "ölçülemedi" derken kök `README.md` dâhil altı belge κ = 0,302 ilan
ediyor ve kanıt diye tam da o dosyayı gösteriyordu. İki sayı da doğruydu;
kaybolan şey hangisinin hangi tura ait olduğuydu.

Bu dosya iki kapıyı çitler: (1) tur adı çıktıya yansır, (2) farklı içerikle
üzerine yazmak hata verir.
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import report_iaa


class TurAdiCiktiyaYansir(unittest.TestCase):
    def test_tur_CSV_adlarindan_turetilir(self) -> None:
        """Ortak önek TURDUR; anotatör harfi dosya adının sonundadır."""
        self.assertEqual(
            report_iaa.tur_adi(["data/gold/review/round0_kalibrasyon_A.csv",
                                "data/gold/review/round0_kalibrasyon_B.csv",
                                "data/gold/review/round0_kalibrasyon_C.csv",
                                "data/gold/review/round0_kalibrasyon_D.csv"]),
            "round0-kalibrasyon")

    def test_v2_turu_v1den_AYRI_ad_uretir(self) -> None:
        """Kazanın çekirdeği: iki tur aynı ada yazamamalı."""
        v1 = report_iaa.rapor_yolu(["data/gold/review/round0_kalibrasyon_A.csv",
                                    "data/gold/review/round0_kalibrasyon_B.csv"])
        v2 = report_iaa.rapor_yolu(["data/gold/review/round0_kalibrasyon_v2_A.csv",
                                    "data/gold/review/round0_kalibrasyon_v2_B.csv"])
        self.assertNotEqual(v1, v2)
        self.assertIn("round0-kalibrasyon", v1)
        self.assertIn("round0-kalibrasyon-v2", v2)

    def test_tur_bayragi_ada_girer(self) -> None:
        yol = report_iaa.rapor_yolu(["a.csv", "b.csv"], tur="round0-kalibrasyon-v1")
        self.assertEqual(Path(yol).name, "iaa-raporu-round0-kalibrasyon-v1.md")

    def test_tur_bayragi_kebab_caseye_cevrilir(self) -> None:
        yol = report_iaa.rapor_yolu([], tur="Round0_Kalibrasyon_V1")
        self.assertEqual(Path(yol).name, "iaa-raporu-round0-kalibrasyon-v1.md")

    def test_ortak_onek_yoksa_ad_TURETILMEZ(self) -> None:
        """Karışık turlara tek bir tur adı uydurmak, ezdiğimiz hatanın aynısı."""
        with self.assertRaises(report_iaa.CiktiCakismasi):
            report_iaa.rapor_yolu(["round1_A.csv", "kalibrasyon_B.csv"])

    def test_rapor_govdesi_de_turu_yazar(self) -> None:
        """Dosya adı kopyalanırken düşebilir; içerik turu söylemek zorunda."""
        govde = report_iaa.render(
            {"annotators": ["A", "B"], "protocols": {}, "mixed_protocols": False,
             "shared_rows": 0, "undecided_cells": 0, "verdict_metric": "Cohen",
             "verdict_kappa": float("nan"), "value_alpha_nominal": float("nan"),
             "value_alpha_ratio": float("nan"), "ratio_units": 0,
             "disagreements": [], "by_field": [],
             "files": ["data/gold/review/round0_kalibrasyon_v2_A.csv",
                       "data/gold/review/round0_kalibrasyon_v2_B.csv"]})
        self.assertIn("round0-kalibrasyon-v2", govde)


class AyniAdaFarkliIcerikYAZILMAZ(unittest.TestCase):
    def setUp(self) -> None:
        self._gecici = tempfile.TemporaryDirectory()
        self.yol = Path(self._gecici.name) / "iaa-raporu-tur.md"
        self.addCleanup(self._gecici.cleanup)

    def test_yeni_dosya_yazilir(self) -> None:
        self.assertEqual(report_iaa.raporu_yaz(self.yol, "κ 0,302\n"),
                         "olusturuldu")
        self.assertEqual(self.yol.read_text(encoding="utf-8"), "κ 0,302\n")

    def test_farkli_icerik_HATA_verir_ve_dosyaya_DOKUNMAZ(self) -> None:
        report_iaa.raporu_yaz(self.yol, "κ 0,302\n")
        with self.assertRaises(report_iaa.CiktiCakismasi):
            report_iaa.raporu_yaz(self.yol, "κ ölçülemedi\n")
        self.assertEqual(
            self.yol.read_text(encoding="utf-8"), "κ 0,302\n",
            "hata veren koşu eski raporu bozmamalı")

    def test_ayni_icerik_idempotenttir(self) -> None:
        """Aynı turu yeniden koşmak zararsızdır; kapı onu engellemez."""
        report_iaa.raporu_yaz(self.yol, "κ 0,302\n")
        self.assertEqual(report_iaa.raporu_yaz(self.yol, "κ 0,302\n"),
                         "degismedi")

    def test_uzerine_yaz_bayragi_izin_verir(self) -> None:
        report_iaa.raporu_yaz(self.yol, "κ 0,302\n")
        self.assertEqual(
            report_iaa.raporu_yaz(self.yol, "κ 0,274\n", uzerine_yaz=True),
            "uzerine-yazildi")
        self.assertEqual(self.yol.read_text(encoding="utf-8"), "κ 0,274\n")


class MainCakismadaHATA_DONER(unittest.TestCase):
    """Uçtan uca: iki farklı tur aynı `--out`a yazılamaz."""

    def setUp(self) -> None:
        self._gecici = tempfile.TemporaryDirectory()
        self.addCleanup(self._gecici.cleanup)
        self.out = Path(self._gecici.name) / "iaa-raporu.md"
        self.v1 = ["data/gold/review/round0_kalibrasyon_A.csv",
                   "data/gold/review/round0_kalibrasyon_B.csv"]
        self.v2 = ["data/gold/review/round0_kalibrasyon_v2_A.csv",
                   "data/gold/review/round0_kalibrasyon_v2_B.csv"]
        for yol in self.v1 + self.v2:
            if not Path(yol).exists():
                self.skipTest(f"tur dosyası yok: {yol}")

    def test_ikinci_tur_ayni_adi_EZEMEZ(self) -> None:
        self.assertEqual(report_iaa.main([*self.v1, "--out", str(self.out)]), 0)
        onceki = self.out.read_text(encoding="utf-8")

        self.assertEqual(
            report_iaa.main([*self.v2, "--out", str(self.out)]), 1,
            "farklı turun raporu sessizce üzerine yazılamaz")
        self.assertEqual(self.out.read_text(encoding="utf-8"), onceki,
                         "v1'in κ'sı yerinde kalmalı")

    def test_uzerine_yaz_ile_bilerek_ezilir(self) -> None:
        report_iaa.main([*self.v1, "--out", str(self.out)])
        self.assertEqual(
            report_iaa.main([*self.v2, "--out", str(self.out), "--uzerine-yaz"]),
            0)


if __name__ == "__main__":
    unittest.main()
