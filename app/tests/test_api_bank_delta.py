"""`GET /bank-delta` — banka içi delta, ÜRÜN AİLESİ İÇİNDE.

İlgili: src/api/main.py (`/bank-delta`), src/comparison/compare.py
        (`delta_between`), web/app/components/BankDeltaPanel.tsx

## Bu testin varlık sebebi

Delta paneli 8 ayrı **tür süzmesiz** `/compare` çağrısının üstüne istemcide
kuruluyordu. Sonuç: *«Vade — Türkiye Finans daha avantajlı: 84 ay fark»*
cümlesi, bankanın ihtiyaç finansmanı ile rakibin konut finansmanı arasında
üretilmiş olabiliyordu. Kullanıcı bunu göremiyordu bile — tabloda kampanya
türü hiç basılmıyordu.

İki ayrım burada kilitleniyor ve ikisi de sessizce bozulabilir cinsten:

  1. **Aile içi hesap.** Farklı ürün aileleri arasında delta ÜRETİLMEZ.
  2. **`eksik_urun` ≠ `eksik_veri`.** Banka o ailede hiç belge taşımıyorsa
     ürün eksikliği; belgesi var ama alan çıkarılamamışsa veri eksikliği.
     İkisini tek etikette toplamak, olmayan bir ürün eksikliği iddia etmektir.
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from fastapi.testclient import TestClient

from src.db.repository import Repository
from src.extraction.reconcile import build_campaign


def _app(path: str):
    from src.api import main as api_main
    onceki = api_main.DB_PATH
    api_main.DB_PATH = path
    try:
        return api_main.build_app()
    finally:
        api_main.DB_PATH = onceki


class _DepoluTest(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.path = str(Path(self._tmp.name) / "api.db")
        self.repo = Repository(self.path)

    def tearDown(self):
        self.repo.close()
        self._tmp.cleanup()

    def ekle(self, slug: str, metin: str, tur: str) -> None:
        self.repo.insert_campaign(build_campaign(metin, bank_slug=slug,
                                                 campaign_type=tur))

    def client(self) -> TestClient:
        self.repo.close()
        return TestClient(_app(self.path))

    def delta(self, bank: str, **params) -> dict:
        r = self.client().get("/bank-delta", params={"bank": bank, **params})
        self.assertEqual(r.status_code, 200, r.text)
        return r.json()

    def alan(self, veri: dict, tur: str, alan: str) -> dict:
        aile = [a for a in veri["families"] if a["campaign_type"] == tur]
        self.assertTrue(aile, f"{tur} ailesi dönmedi")
        satir = [f for f in aile[0]["fields"] if f["field"] == alan]
        self.assertTrue(satir, f"{alan} alanı dönmedi")
        return satir[0]


class AileIciHesap(_DepoluTest):
    """Farklı ürün aileleri arasında delta ÜRETİLMEZ."""

    def setUp(self):
        super().setUp()
        # Kuveyt Türk: konut 36 ay. Albaraka: konut 48 ay, taşıt 120 ay.
        # Tür körü bir hesap, 120 ay ile 36 ayı karşılaştırıp 84 ay fark
        # üretirdi — bildirilen şikâyetin tam kalıbı.
        self.ekle("kuveyt-turk", "Konut finansmanı 36 ay vade.", "Konut Finansmanı")
        self.ekle("albaraka", "Konut finansmanı 48 ay vade.", "Konut Finansmanı")
        self.ekle("albaraka", "Taşıt finansmanı 120 ay vade.", "Taşıt Finansmanı")

    def test_fark_AYNI_aile_icinde_hesaplanir(self):
        f = self.alan(self.delta("kuveyt-turk"), "Konut Finansmanı", "vade_ay")
        self.assertEqual(f["abs_diff"], 12.0, "48 - 36 = 12 beklenir")

    def test_baska_ailedeki_rakip_KARISMAZ(self):
        f = self.alan(self.delta("kuveyt-turk"), "Konut Finansmanı", "vade_ay")
        self.assertEqual(f["rival"]["campaign_type"], "Konut Finansmanı")
        self.assertNotEqual(f["abs_diff"], 84.0,
                            "taşıt finansmanı konut ile kıyaslanmamalı")

    def test_her_aile_ayri_bolum_olarak_doner(self):
        turler = {a["campaign_type"] for a in self.delta("albaraka")["families"]}
        self.assertIn("Konut Finansmanı", turler)
        self.assertIn("Taşıt Finansmanı", turler)

    def test_tur_suzmesi_tek_aile_dondurur(self):
        veri = self.delta("albaraka", type="Taşıt Finansmanı")
        self.assertEqual([a["campaign_type"] for a in veri["families"]],
                         ["Taşıt Finansmanı"])

    def test_her_taraf_kendi_turunu_tasir(self):
        """Arayüz neyin neyle kıyaslandığını gösterebilmeli."""
        f = self.alan(self.delta("kuveyt-turk"), "Konut Finansmanı", "vade_ay")
        self.assertEqual(f["mine"]["campaign_type"], f["rival"]["campaign_type"])


class EksikUrunEksikVeridenAyri(_DepoluTest):
    """İki eksiklik türü BİRBİRİNE karıştırılmaz."""

    def setUp(self):
        super().setUp()
        # Kuveyt Türk konut ailesinde belge taşıyor ama oranı yok (yalnız vade).
        self.ekle("kuveyt-turk", "Konut finansmanı 36 ay vade.", "Konut Finansmanı")
        self.ekle("albaraka", "Konut finansmanında kâr payı oranı %1,89.",
                  "Konut Finansmanı")
        # Taşıt ailesinde Kuveyt Türk'ün HİÇ belgesi yok.
        self.ekle("albaraka", "Taşıt finansmanı 120 ay vade.", "Taşıt Finansmanı")

    def test_belge_VAR_alan_yok_ise_eksik_veri(self):
        f = self.alan(self.delta("kuveyt-turk"), "Konut Finansmanı",
                      "kar_payi_orani")
        self.assertEqual(f["kind"], "eksik_veri")

    def test_belge_YOK_ise_eksik_urun(self):
        f = self.alan(self.delta("kuveyt-turk"), "Taşıt Finansmanı", "vade_ay")
        self.assertEqual(f["kind"], "eksik_urun")

    def test_own_campaigns_ayrimi_besliyor(self):
        veri = self.delta("kuveyt-turk")
        sayim = {a["campaign_type"]: a["own_campaigns"] for a in veri["families"]}
        self.assertEqual(sayim["Konut Finansmanı"], 1)
        self.assertEqual(sayim["Taşıt Finansmanı"], 0)


class RakipSecimi(_DepoluTest):
    """Rakip dayatılmıyor; seçilebiliyor."""

    def setUp(self):
        super().setUp()
        self.ekle("kuveyt-turk", "Konut finansmanında kâr payı oranı %2,49.",
                  "Konut Finansmanı")
        self.ekle("albaraka", "Konut finansmanında kâr payı oranı %1,69.",
                  "Konut Finansmanı")
        self.ekle("vakif-katilim", "Konut finansmanında kâr payı oranı %2,09.",
                  "Konut Finansmanı")

    def test_varsayilan_rakip_EN_IYISIDIR(self):
        f = self.alan(self.delta("kuveyt-turk"), "Konut Finansmanı",
                      "kar_payi_orani")
        self.assertEqual(f["rival"]["bank"], "albaraka")

    def test_secilen_rakip_uygulanir(self):
        f = self.alan(self.delta("kuveyt-turk", rival="vakif-katilim"),
                      "Konut Finansmanı", "kar_payi_orani")
        self.assertEqual(f["rival"]["bank"], "vakif-katilim")
        self.assertAlmostEqual(f["abs_diff"], 0.40, places=6)

    def test_konum_bildiriliyor(self):
        """«3 bankadan 3.» — eskiden bu bilgi hiç üretilmiyordu."""
        f = self.alan(self.delta("kuveyt-turk"), "Konut Finansmanı",
                      "kar_payi_orani")
        self.assertEqual(f["position"], 3)
        self.assertEqual(f["bank_count"], 3)

    def test_en_iyi_banka_1_konumda(self):
        f = self.alan(self.delta("albaraka"), "Konut Finansmanı", "kar_payi_orani")
        self.assertEqual(f["position"], 1)
        self.assertEqual(f["kind"], "daha_iyi")


class KanitTasiniyor(_DepoluTest):
    """Delta iddiası denetlenebilir olmalı."""

    def setUp(self):
        super().setUp()
        self.ekle("kuveyt-turk", "Konut finansmanında kâr payı oranı %2,49.",
                  "Konut Finansmanı")
        self.ekle("albaraka", "Konut finansmanında kâr payı oranı %1,69.",
                  "Konut Finansmanı")

    def test_her_taraf_katman_ve_guven_tasiyor(self):
        f = self.alan(self.delta("kuveyt-turk"), "Konut Finansmanı",
                      "kar_payi_orani")
        for taraf in ("mine", "rival"):
            with self.subTest(taraf=taraf):
                self.assertIn("extractor", f[taraf])
                self.assertIn("confidence", f[taraf])
                self.assertIn("contradiction_count", f[taraf])

    def test_her_taraf_kaynagina_baglanabiliyor(self):
        f = self.alan(self.delta("kuveyt-turk"), "Konut Finansmanı",
                      "kar_payi_orani")
        self.assertIsInstance(f["mine"]["campaign_id"], int)
        self.assertIn("source_url", f["rival"])

    def test_adil_kiyas_notu_doner(self):
        """Not, kullanıcıya dönük KANONİK terimi kullanmalı.

        Eskiden «ÜRÜN AİLESİ» yazıyordu. Aynı kavramın (`campaign_type`,
        8 sınıf) arayüzde üç ayrı adı vardı — «ürün ailesi», yalın «aile» ve
        «Ürün» — ve kullanıcı bunları farklı şeyler sandı. Tek ad seçildi:
        **kampanya türü**. `CLAUDE.md` §12'de 8 sınıfın resmî başlığı budur
        ve `campaign_type` alan adının birebir karşılığıdır; «ürün ailesi»
        hiçbir şemada ya da uçta geçmiyordu, iç jargondu.
        """
        veri = self.delta("kuveyt-turk")
        self.assertIn("KAMPANYA TÜRÜ", veri["fairness_note"])
        self.assertNotIn("ÜRÜN AİLESİ", veri["fairness_note"])


class DeltaAritmetigi(unittest.TestCase):
    """`delta_between` — yön yorumu ve hesaplanmayan durumlar.

    Bu aritmetik arayüzde DEĞİL motorda durur: fark hesabı yönü bilmek zorunda
    ("düşük iyi" alanda küçük değer avantajdır) ve aynı kararı istemcide ikinci
    kez uygulamak, bugün iki kez düzeltilen hatanın kalıbıdır.
    """

    def setUp(self):
        from src.comparison.compare import delta_between
        self.delta = delta_between

    def test_dusuk_iyi_alanda_kucuk_deger_KAZANIR(self):
        tur, mutlak, _ = self.delta("kar_payi_orani", 1.69, 2.49)
        self.assertEqual(tur, "daha_iyi")
        self.assertAlmostEqual(mutlak, 0.80, places=6)

    def test_yuksek_iyi_alanda_buyuk_deger_KAZANIR(self):
        self.assertEqual(self.delta("vade_ay", 120, 36)[0], "daha_iyi")
        self.assertEqual(self.delta("vade_ay", 36, 120)[0], "daha_kotu")

    def test_esitlik(self):
        self.assertEqual(self.delta("vade_ay", 36, 36), ("esit", 0.0, 0.0))

    def test_taraf_sayiya_inmiyorsa_fark_HESAPLANMAZ(self):
        """Yaklaşık fark üretmek CLAUDE.md §17'nin yasakladığı şeydir."""
        for benim, rakip in ((None, 5.0), (5.0, None), (None, None)):
            with self.subTest(benim=benim, rakip=rakip):
                self.assertEqual(self.delta("vade_ay", benim, rakip),
                                 ("kiyaslanamaz", None, None))

    def test_rakip_SIFIRSA_goreli_fark_uretilmez(self):
        """0'a bölme tanımsız; üstelik 0 burada gerçek bir üründür."""
        tur, mutlak, goreli = self.delta("tahsis_ucreti", 750.0, 0.0)
        self.assertEqual(tur, "daha_kotu")
        self.assertEqual(mutlak, 750.0)
        self.assertIsNone(goreli, "sıfıra oranlanmış bir yüzde uydurulmamalı")

    def test_goreli_fark_rakibe_oranlanir(self):
        _, _, goreli = self.delta("vade_ay", 48, 36)
        self.assertAlmostEqual(goreli, 100 * 12 / 36, places=6)


if __name__ == "__main__":
    unittest.main()
