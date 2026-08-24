"""`GET /katilma-oranlari` — panel yüzeyi, iki büyüklük, girdi doğrulama.

İlgili: src/api/routers/katilma.py
        src/chatbot/katilma_orani.py (aynı veriyi sohbette cevaplar)
        ../../decisions/katilma-orani-iki-ayri-buyukluk.md

## Bu testin varlık sebebi

Chatbot katılma oranlarını cevaplıyordu, panel görmüyordu — sohbette görünen
bir sıralamanın ekranda bulunamaması kapsam kaybıydı. Bu test hem ucun
çalıştığını hem de İKİ BÜYÜKLÜĞÜN ayrı kaldığını kilitler: getiri (%42) ile
pay (%90) aynı listede yarışırsa "en iyi oran" yanlış bankayı gösterir.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

# Desen `test_api_advantageous.py`den: test aracının yokluğu, sınanan kodun
# kusuru değildir. RuntimeError de yakalanır (starlette httpx2 istiyor).
try:  # pragma: no cover - ortama bağlı
    from fastapi.testclient import TestClient
    FASTAPI_VAR = True
except (ImportError, RuntimeError):  # pragma: no cover
    TestClient = None  # type: ignore[assignment,misc]
    FASTAPI_VAR = False

from src.api.routers.katilma import (
    BUYUKLUKLER,
    PARA_BIRIMLERI,
    VADELER,
    _satirlar,
)


def _k(slug: str, ad: str, oran: float, *, ay: int = 1, para: str = "TRY",
       buyukluk: str = "getiri") -> dict:
    return {"bank_slug": slug, "bank_name": ad, "buyukluk": buyukluk,
            "currency": para, "term_months": ay, "period_date": "2026-08-24",
            "annual_rate": oran, "source_url": "https://tkbb.org.tr/x"}


ORNEK = (
    _k("tom-katilim", "T.O.M. Katılım Bankası A.Ş.", 42.79),
    _k("hayat-finans", "Hayat Finans Katılım Bankası A.Ş.", 41.28, ay=6),
    _k("albaraka", "Albaraka Türk Katılım Bankası A.Ş.", 40.85, ay=12),
    _k("albaraka", "Albaraka Türk Katılım Bankası A.Ş.", 31.35, ay=1),
    _k("albaraka", "Albaraka Türk Katılım Bankası A.Ş.", 0.93, para="USD"),
    _k("turkiye-finans", "Türkiye Finans Katılım Bankası A.Ş.", 98.0,
       buyukluk="pay"),
)


class TestSiralama(unittest.TestCase):
    def test_azalan_sirada(self):
        s = _satirlar(ORNEK, "getiri", "TRY", None)
        self.assertEqual([x["bank_slug"] for x in s],
                         ["tom-katilim", "hayat-finans", "albaraka"])

    def test_banka_basina_EN_IYI_satir(self):
        """Albaraka'nın iki TL getiri satırı var; yalnız en iyisi listelenir."""
        s = _satirlar(ORNEK, "getiri", "TRY", None)
        alb = [x for x in s if x["bank_slug"] == "albaraka"]
        self.assertEqual(len(alb), 1)
        self.assertEqual(alb[0]["annual_rate"], 40.85)

    def test_vade_satirda_TASINIR(self):
        """Vade gizlenirse farklı vadeler aynı kolonda kıyaslanmış olurdu."""
        s = _satirlar(ORNEK, "getiri", "TRY", None)
        self.assertEqual({x["bank_slug"]: x["term_months"] for x in s},
                         {"tom-katilim": 1, "hayat-finans": 6, "albaraka": 12})

    def test_getiri_ve_pay_AYRI(self):
        getiri = _satirlar(ORNEK, "getiri", "TRY", None)
        pay = _satirlar(ORNEK, "pay", "TRY", None)
        self.assertNotIn(98.0, [x["annual_rate"] for x in getiri])
        self.assertEqual([x["annual_rate"] for x in pay], [98.0])

    def test_vade_suzgeci(self):
        s = _satirlar(ORNEK, "getiri", "TRY", 6)
        self.assertEqual([x["bank_slug"] for x in s], ["hayat-finans"])

    def test_para_birimi_suzgeci(self):
        s = _satirlar(ORNEK, "getiri", "USD", None)
        self.assertEqual([x["bank_slug"] for x in s], ["albaraka"])

    def test_eslesme_yoksa_bos(self):
        self.assertEqual(_satirlar(ORNEK, "getiri", "XAU", None), [])

    def test_kaynak_her_satirda(self):
        for x in _satirlar(ORNEK, "getiri", "TRY", None):
            self.assertIn("tkbb", x["source_url"])


@unittest.skipUnless(FASTAPI_VAR, "fastapi/TestClient yok")
class TestUc(unittest.TestCase):
    def setUp(self):
        from fastapi import FastAPI

        from src.api.routers import katilma
        self._gercek = katilma.kayitlari_yukle
        katilma.kayitlari_yukle = lambda *a, **k: ORNEK  # type: ignore[assignment]
        app = FastAPI()
        app.include_router(katilma.router_kur())
        self.c = TestClient(app)

    def tearDown(self):
        from src.api.routers import katilma
        katilma.kayitlari_yukle = self._gercek  # type: ignore[assignment]

    def test_varsayilan_getiri_TRY(self):
        y = self.c.get("/katilma-oranlari").json()
        self.assertEqual(y["buyukluk"], "getiri")
        self.assertEqual(y["currency"], "TRY")
        self.assertFalse(y["veri_yok"])
        self.assertEqual(y["rows"][0]["bank_slug"], "tom-katilim")
        self.assertEqual(y["period_date"], "2026-08-24")

    def test_pay_secilebilir(self):
        y = self.c.get("/katilma-oranlari?buyukluk=pay").json()
        self.assertIn("pay", y["buyukluk_etiketi"].lower())
        self.assertEqual(y["rows"][0]["annual_rate"], 98.0)

    def test_mevcut_secenekler_VERIDEN_gelir(self):
        """Sabit liste basmak, verisi olmayan para birimini seçilebilir gösterirdi."""
        y = self.c.get("/katilma-oranlari").json()
        self.assertEqual(y["mevcut"]["para_birimleri"], ["TRY", "USD"])
        self.assertEqual(y["mevcut"]["vadeler"], [1, 6, 12])

    def test_gecersiz_buyukluk_400(self):
        r = self.c.get("/katilma-oranlari?buyukluk=oran")
        self.assertEqual(r.status_code, 400)

    def test_gecersiz_para_birimi_400(self):
        self.assertEqual(
            self.c.get("/katilma-oranlari?currency=GBP").status_code, 400)

    def test_gecersiz_vade_400(self):
        self.assertEqual(
            self.c.get("/katilma-oranlari?term_months=9").status_code, 400)

    def test_veri_yok_HATA_DEGIL(self):
        """Boş sonuç 'oran sıfır' değil 'veri toplanmadı' demektir."""
        y = self.c.get("/katilma-oranlari?currency=XAU").json()
        self.assertTrue(y["veri_yok"])
        self.assertEqual(y["rows"], [])
        # Kaynak ve uyarı veri yokken de basılır
        self.assertIn("tkbb", y["source_url"].lower())
        self.assertIn("garanti edilemez", y["uyari"])

    def test_uyari_ve_kaynak_KOSULSUZ(self):
        y = self.c.get("/katilma-oranlari").json()
        self.assertIn("garanti edilemez", y["uyari"])
        self.assertEqual(y["source_label"], "TKBB Veri Peteği")


class TestSabitler(unittest.TestCase):
    def test_kabul_edilen_degerler(self):
        self.assertEqual(BUYUKLUKLER, ("getiri", "pay"))
        self.assertEqual(PARA_BIRIMLERI, ("TRY", "USD", "EUR", "XAU"))
        self.assertEqual(VADELER, (1, 3, 6, 12))


if __name__ == "__main__":
    unittest.main()
