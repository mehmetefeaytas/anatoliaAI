"""Doldurulmamış anotasyon turu κ = 1,000 vermemeli — regresyon.

Çalıştır:  python -m unittest tests.test_iaa_bos_tur  (app/ kökünden)

## Bulunan kusur (2026-08-13)

Yeni üretilmiş, tek hücresi bile doldurulmamış dört CSV `report_iaa`'ya
verildiğinde şunu bastı:

    protokol            : v1
    Fleiss' kappa       : 1.000
    DURUM: kabul — Gold güvenilir. Ana geçişe devam.

Sebep veri değil, protokol semantiği: v1'de boş `verdict` = "ok" (onay).
Dolayısıyla "hiç kimse çalışmadı" ile "herkes her satırı onayladı" aynı
girdiye düşüyor ve ikincisi mükemmel uyum demek.

Bu, projenin daha önce bir kez yandığı hata biçiminin aynısı — YANLIŞ ŞEYİ
ÖLÇÜP DOĞRU GÖRÜNMEK — ve en pahalı yönde: sıfır iş, tam not. Bir gold seti
"güvenilir" ilan edip ölçüme devam etmek, sonraki bütün sayıları çürütürdü.

Koruma protokolden BAĞIMSIZ tutuldu. v2 boş hücreyi zaten karar saymıyor ama
v1 dosyaları hâlâ okunabiliyor ve arşivdeki turlar v1.
"""

from __future__ import annotations

import csv
import sys
import tempfile
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from scripts.report_iaa import compute

SUTUNLAR = ["doc_id", "bank", "field", "model_value", "model_conf",
            "confidence_source", "disagreement", "snippet", "gold_value",
            "verdict", "note"]


def _csv_yaz(yol: Path, satirlar: list[dict], protokol: str | None = None) -> None:
    kolonlar = list(SUTUNLAR) + (["protokol"] if protokol else [])
    with yol.open("w", encoding="utf-8-sig", newline="") as h:
        w = csv.DictWriter(h, fieldnames=kolonlar, delimiter=";",
                           lineterminator="\r\n", extrasaction="ignore")
        w.writeheader()
        for s in satirlar:
            r = {k: "" for k in kolonlar}
            r.update(s)
            if protokol:
                r["protokol"] = protokol
            w.writerow(r)


def _satirlar(verdict: str = "", gold_value: str = "") -> list[dict]:
    return [
        {"doc_id": f"banka--belge{i}", "bank": "banka", "field": f, "model_value": "12",
         "verdict": verdict, "gold_value": gold_value}
        for i in range(3) for f in ("vade_ay", "kar_payi_orani")
    ]


class BosTur(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.d = Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)

    def _koş(self, satirlar, protokol=None):
        yollar = []
        for ad in "ABCD":
            p = self.d / f"round_{ad}.csv"
            _csv_yaz(p, satirlar, protokol)
            yollar.append(str(p))
        return compute(yollar)

    def test_v1_bos_tur_kappa_uretmez(self):
        """Asıl kusur: v1'de boş = 'ok' olduğu için κ 1,000 çıkıyordu."""
        r = self._koş(_satirlar())
        self.assertTrue(r["bos_tur"])
        self.assertNotEqual(r["verdict_kappa"], r["verdict_kappa"],
                            "doldurulmamış turda κ sayı üretmemeli (NaN olmalı)")

    def test_v1_bos_turda_alfalar_da_uretilmez(self):
        r = self._koş(_satirlar())
        for anahtar in ("value_alpha_nominal", "value_alpha_ratio"):
            self.assertNotEqual(r[anahtar], r[anahtar], f"{anahtar} NaN olmalı")

    def test_v2_bos_tur_da_yakalanir(self):
        r = self._koş(_satirlar(), protokol="v2")
        self.assertTrue(r["bos_tur"])
        self.assertNotEqual(r["verdict_kappa"], r["verdict_kappa"])

    def test_tek_isaret_turu_olculebilir_yapar(self):
        """Koruma fazla geniş olmamalı: bir işaret varsa tur ölçülür."""
        satirlar = _satirlar()
        satirlar[0] = {**satirlar[0], "verdict": "ok"}
        r = self._koş(satirlar)
        self.assertFalse(r["bos_tur"])
        self.assertEqual(r["verdict_kappa"], r["verdict_kappa"],
                         "işaret varsa κ hesaplanmalı")

    def test_yalnizca_gold_value_dolu_da_isaret_sayilir(self):
        """`fix` kararı `gold_value` ile verilir; verdict boş kalabilir."""
        satirlar = _satirlar()
        satirlar[0] = {**satirlar[0], "gold_value": "36"}
        r = self._koş(satirlar)
        self.assertFalse(r["bos_tur"])


if __name__ == "__main__":
    unittest.main()
