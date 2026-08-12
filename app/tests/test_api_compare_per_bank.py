"""`GET /compare?per_bank=` — şartnamenin "banka başına bir satır" tablosu.

İlgili: src/api/main.py (`/compare`, `VALID_PER_BANK`)
        src/comparison/compare.py:487-489 (şartname referansı)

## Bu testin varlık sebebi

Şartnamenin çalışılmış örneği (s.12–13) **banka başına bir satır** gösteriyor:
A, B ve C bankasının konut finansmanı kampanyaları tek tabloda. `/compare` ise
`extracted_fields`'taki HER satırı döndürüyordu ve her birine ayrı sıra
veriyordu. Aynı banka aynı alanda 5 kampanya taşıdığında "en düşük kâr payı
hangi bankada" ekranı, tek bir bankanın kendi kampanyalarıyla dolu bir listeye
dönüşüyordu.

Tekilleştirme anahtarı `(bank, campaign_type)` — yalnız `bank` DEĞİL. Bir
bankanın konut finansmanı ile taşıt finansmanı farklı ürünlerdir; aynı satıra
indirgemek adil kıyas garantisinin (CLAUDE.md §17) ürün ailesi düzeyindeki
karşılığını bozardı. Aşağıdaki `AyriUrunAileleriKorunur` tam bunu kilitler.

Elenen satırlar SAKLANMAZ, SAYILIR (`other_count`) ve `per_bank=all` ile
tamamı yine alınabilir — bilgi gizlenmiyor, özetleniyor.
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

# Çekirdek paket SIFIR üçüncü parti bağımlılıkla koşar; CI'daki `test` işi
# bilinçli olarak hiçbir şey kurmuyor (bkz. ci.yml). Bu import KORUMASIZ
# olduğu için modül yükleme aşamasında patlıyor ve `unittest` bunu ATLAMA
# değil HATA sayıyordu: 12 Ağu CI koşusunda `unittest.loader._FailedTest`.
# Desen `test_api_startup.py:37-41`den alındı.
try:  # pragma: no cover - ortama bağlı
    from fastapi.testclient import TestClient
    FASTAPI_VAR = True
except ModuleNotFoundError:  # pragma: no cover
    TestClient = None  # type: ignore[assignment,misc]
    FASTAPI_VAR = False

from src.db.repository import Repository
from src.extraction.reconcile import build_campaign

ALAN = "kar_payi_orani"


def _app(path: str):
    """`build_app()`'i verilen SQLite dosyasıyla kurar (test_api_backend kalıbı)."""
    from src.api import main as api_main
    onceki = api_main.DB_PATH
    api_main.DB_PATH = path
    try:
        return api_main.build_app()
    finally:
        api_main.DB_PATH = onceki


@unittest.skipUnless(FASTAPI_VAR, "fastapi kurulu değil — API testi atlanıyor")
class _DepoluTest(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.path = str(Path(self._tmp.name) / "api.db")
        self.repo = Repository(self.path)

    def tearDown(self):
        self.repo.close()
        self._tmp.cleanup()

    def ekle(self, slug: str, oran: str, tur: str = "Konut Finansmanı") -> None:
        self.repo.insert_campaign(build_campaign(
            f"Konut finansmanında kâr payı oranı %{oran}, 36 ay vade.",
            bank_slug=slug, campaign_type=tur))

    def client(self) -> TestClient:
        self.repo.close()
        return TestClient(_app(self.path))

    def satirlar(self, **params) -> list[dict]:
        r = self.client().get("/compare", params={"field": ALAN, **params})
        self.assertEqual(r.status_code, 200, r.text)
        # Fixture tohumlaması başka bankalar ekleyebilir; testin ilgilendiği
        # bankalarla sınırlanır.
        return [x for x in r.json() if x["bank"] in self.ILGILI]

    ILGILI: frozenset[str] = frozenset()


class BankaBasinaTekSatir(_DepoluTest):
    """Aynı banka + aynı ürün ailesi → tek satır."""

    ILGILI = frozenset({"kuveyt-turk"})

    def setUp(self):
        super().setUp()
        for oran in ("1,89", "2,49", "3,19"):
            self.ekle("kuveyt-turk", oran)

    def test_varsayilan_best_tek_satir_dondurur(self):
        self.assertEqual(len(self.satirlar()), 1)

    def test_kalan_satir_EN_IYISIDIR(self):
        """`kar_payi_orani` düşük-iyi: en düşük oran kalmalı."""
        self.assertEqual(self.satirlar()[0]["value"], 1.89)

    def test_elenenler_SAYILIYOR(self):
        self.assertEqual(self.satirlar()[0]["other_count"], 2)

    def test_all_eski_davranisi_korur(self):
        satirlar = self.satirlar(per_bank="all")
        self.assertEqual(len(satirlar), 3)
        self.assertEqual({s["other_count"] for s in satirlar}, {0},
                         "hiçbir şey elenmediyse other_count 0 olmalı")

    def test_all_ile_tum_degerler_hala_erisilebilir(self):
        """Bilgi gizlenmiyor, özetleniyor."""
        self.assertEqual(
            sorted(s["value"] for s in self.satirlar(per_bank="all")),
            [1.89, 2.49, 3.19],
        )


class AyriUrunAileleriKorunur(_DepoluTest):
    """Tekilleştirme `(banka, tür)` bazında — yalnız banka bazında DEĞİL."""

    ILGILI = frozenset({"kuveyt-turk"})

    def setUp(self):
        super().setUp()
        self.ekle("kuveyt-turk", "1,89", tur="Konut Finansmanı")
        self.ekle("kuveyt-turk", "2,49", tur="Konut Finansmanı")
        self.ekle("kuveyt-turk", "3,19", tur="Taşıt Finansmanı")

    def test_ayni_bankanin_iki_urun_ailesi_AYRI_kalir(self):
        turler = sorted(s["campaign_type"] for s in self.satirlar())
        self.assertEqual(turler, ["Konut Finansmanı", "Taşıt Finansmanı"],
                         "konut ile taşıt finansmanı aynı satıra indirgenemez")

    def test_her_aile_kendi_en_iyisini_tutar(self):
        deger = {s["campaign_type"]: s["value"] for s in self.satirlar()}
        self.assertEqual(deger["Konut Finansmanı"], 1.89)
        self.assertEqual(deger["Taşıt Finansmanı"], 3.19)

    def test_other_count_aile_icindedir(self):
        sayi = {s["campaign_type"]: s["other_count"] for s in self.satirlar()}
        self.assertEqual(sayi["Konut Finansmanı"], 1)
        self.assertEqual(sayi["Taşıt Finansmanı"], 0)


class SiralamaBozulmuyor(_DepoluTest):
    """Tekilleştirme sonrası sıra numaraları BOŞLUKSUZ yeniden verilir."""

    ILGILI = frozenset({"kuveyt-turk", "albaraka", "turkiye-finans"})

    def setUp(self):
        super().setUp()
        self.ekle("albaraka", "4,09")
        self.ekle("albaraka", "3,50")
        self.ekle("kuveyt-turk", "1,89")
        self.ekle("turkiye-finans", "2,49")

    def test_bankalar_dogru_sirada(self):
        self.assertEqual(
            [s["bank"] for s in self.satirlar()],
            ["kuveyt-turk", "turkiye-finans", "albaraka"],
        )

    def test_sira_numaralari_boslugsuz(self):
        # Fixture başka banka eklemiş olabilir; ilgilenilen satırların sıraları
        # kendi aralarında artan ve tekrarsız olmalı.
        sıralar = [s["rank"] for s in self.satirlar()]
        self.assertEqual(sıralar, sorted(sıralar))
        self.assertEqual(len(set(sıralar)), len(sıralar))

    def test_albaraka_EN_IYI_satirini_tutar(self):
        albaraka = [s for s in self.satirlar() if s["bank"] == "albaraka"][0]
        self.assertEqual(albaraka["value"], 3.50)


class GecersizParametre(_DepoluTest):
    """Geçersiz değer SESSİZCE yok sayılmaz."""

    def setUp(self):
        super().setUp()
        self.ekle("kuveyt-turk", "1,89")

    def test_bilinmeyen_per_bank_400_doner(self):
        r = self.client().get("/compare", params={"field": ALAN, "per_bank": "hepsi"})
        self.assertEqual(r.status_code, 400)
        self.assertIn("per_bank", r.json()["detail"])

    def test_hata_mesaji_gecerli_degerleri_sayar(self):
        r = self.client().get("/compare", params={"field": ALAN, "per_bank": "x"})
        detay = r.json()["detail"]
        self.assertIn("best", detay)
        self.assertIn("all", detay)


if __name__ == "__main__":
    unittest.main()
