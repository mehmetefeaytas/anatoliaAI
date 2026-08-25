"""`GET /advantageous` — bileşik skorlama artık bir uçtan sunuluyor.

İlgili: src/api/main.py (`/advantageous`, `/scoring`)
        src/comparison/compare.py (`rank_advantageous_by_type`, `weight_manifest`)
        docs/rapor/genel-denetim.md §D (kod/mimari hakeminin ikinci açığı)

## Bu testin varlık sebebi

Denetimde bulundu: `compare.py` `DEFAULT_WEIGHTS`, `WEIGHT_RATIONALE`,
`_composite_numeric`, `rank_advantageous` ve `weight_manifest`'i taşıyor ve
**test ediyordu** (~420 satır) — ama hiçbir uçtan çağrılmıyordu. Üstelik
`/scoring` ucu *"kod tabanında ağırlıklı bileşik skor **yoktur**"* diyerek
kendi kodunu yalanlıyordu. Jüri kodu okusa bu çelişkiyi görürdü.

Bu test iki şeyi kilitler: uç çalışıyor **ve** `/scoring` artık yalan
söylemiyor.
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
except (ImportError, RuntimeError):  # pragma: no cover
    # RuntimeError de yakalanır: starlette 1.6 `TestClient` için `httpx2`
    # istiyor ve yokluğunda ModuleNotFoundError DEĞİL RuntimeError atıyor
    # ("The starlette.testclient module requires the httpx2 package").
    # 12 Ağu CI koşusu 31642385024 tam buna düştü: fastapi kuruluydu,
    # test istemcisinin bağımlılığı değildi ve koruma ATLAMA yerine
    # HATA üretti. Test aracının yokluğu, sınanan kodun kusuru değildir.
    TestClient = None  # type: ignore[assignment,misc]
    FASTAPI_VAR = False

from src.comparison.compare import DEFAULT_WEIGHTS, MIN_GROUP_SIZE
from src.db.repository import Repository
from src.extraction.reconcile import build_campaign

# Farklı oranlar: bileşik skorda `kar_payi_orani` "düşük iyi" ve en yüksek
# ağırlıklı alandır, bu yüzden en düşük oranlı kampanya kazanmalı.
ORANLAR = (1.89, 2.49, 3.19, 4.09)
SLUGLAR = ("kuveyt-turk", "albaraka", "turkiye-finans", "vakif-katilim")


def _seed(repo, n: int, tur: str = "Konut Finansmanı") -> None:
    """n kampanya — hepsi aynı türde, farklı oranlarla."""
    for i in range(n):
        oran = str(ORANLAR[i % len(ORANLAR)]).replace(".", ",")
        repo.insert_campaign(build_campaign(
            f"Konut finansmanında kâr payı oranı %{oran}, 36 ay vade.",
            bank_slug=SLUGLAR[i % len(SLUGLAR)], campaign_type=tur))


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

    def client(self) -> TestClient:
        self.repo.close()
        return TestClient(_app(self.path))


class UcCalisiyor(_DepoluTest):

    def test_uc_200_doner_ve_kapilari_bildirir(self):
        """Boş depo test edilemez: `build_app` boş DB'yi fixture ile tohumlar."""
        r = self.client().get("/advantageous")
        self.assertEqual(r.status_code, 200)
        d = r.json()
        self.assertEqual(d["min_group_size"], MIN_GROUP_SIZE)
        # `İ`nin casefold'u birleşen noktalı `i̇` üretir; adil kıyas notunu
        # ararken İ içermeyen bir parça seçilir (TR imla tuzağı).
        self.assertIn("türler arası", d["fairness_note"])

    def test_agirliklar_gerekceleriyle_doner(self):
        d = self.client().get("/advantageous").json()
        self.assertEqual(len(d["weights"]), len(DEFAULT_WEIGHTS))
        for w in d["weights"]:
            self.assertIn(w["field_name"], DEFAULT_WEIGHTS)
            self.assertTrue(w["rationale"],
                            f"{w['field_name']} ağırlığının gerekçesi yok — "
                            f"jüri 'neden bu ağırlık' diye sorduğunda cevap "
                            f"kodun içinde gömülü kalmamalı")
            self.assertIn(w["direction"], ("dusuk_iyi", "yuksek_iyi"))

    def test_siralama_uretilir_ve_en_dusuk_oran_kazanir(self):
        """`banka_yayini=false` — iddia SALT KAMPANYA popülasyonu hakkında.

        Kardeş testle aynı gerekçe: uç 2026-08-25'ten beri bankaların kendi
        yayımladığı oranlardan da satır üretiyor. Bu test "en düşük oran
        kazanır" diyor ama o iddia tek kaynaklı bir popülasyonda anlamlı;
        karışık popülasyonda BİRİNCİLİK EŞİTLENEBİLİYOR.

        Ölçüldü: fixture'a yayın satırları karışınca kampanya satırı
        (kar_payi 1,89 · vade 36) ile Türkiye Finans yayın satırı
        (kar_payi 0,89 · vade 12) BİREBİR aynı bileşik skoru alıyor —
        0,7681818181818182, kapsama da eşit. Eşitlik gerçek ve anlamlı:
        `kar_payi_orani` 0,40 ağırlıkla "düşük iyi", `vade_ay` 0,15 ağırlıkla
        ters yönde çekiyor ve iki etki birbirini götürüyor.

        Eşit skorda `ranked[0]`'ı belirleyen şey skor değil sıralamanın
        KARARLILIĞI, yani satırların listeye giriş sırası. O sıra ortama göre
        değişebiliyor: aynı commit'te (8b9a3f71) yerelde kampanya satırı
        başa geçti ve test GEÇTİ, CI'da yayın satırı başa geçti ve test
        `0.89 != 1.89` ile DÜŞTÜ. Kusur skorlamada değil, testin karışık bir
        popülasyonda tek bir kazanan varsaymasındaydı.
        """
        _seed(self.repo, MIN_GROUP_SIZE + 1)
        d = self.client().get("/advantageous?banka_yayini=false").json()
        grup = d["types"]["Konut Finansmanı"]
        self.assertIsNone(grup["note"])
        kiyaslanabilir = [c for c in grup["ranked"] if c["comparable"]]
        self.assertTrue(kiyaslanabilir)
        # `kar_payi_orani` "düşük iyi" ve en yüksek ağırlıklı alan.
        en_iyi = kiyaslanabilir[0]
        oran = next(c for c in en_iyi["components"]
                    if c["field_name"] == "kar_payi_orani")
        self.assertEqual(oran["value"], min(ORANLAR))

    def test_kucuk_grup_SIRALANMAZ_ama_gizlenmez(self):
        """2 kampanyada 'en avantajlı' iddiası bilgi taşımaz — kapı görünür.

        `banka_yayini=false` ile SALT KAMPANYA görünümü isteniyor: uç
        2026-08-25'ten beri bankaların kendi yayımladığı oranlardan da satır
        üretiyor (`kiyas_toplama.yayin_satirlari`) ve o satırlar fixture'ın
        grubunu MIN_GROUP_SIZE'ın üstüne çıkarıyordu. Kapının kendisi
        değişmedi; test yalnız onu YALIN popülasyonda sınıyor.
        """
        _seed(self.repo, MIN_GROUP_SIZE - 1)
        grup = (self.client().get("/advantageous?banka_yayini=false")
                .json()["types"]["Konut Finansmanı"])
        self.assertEqual(grup["ranked"], [])
        self.assertEqual(grup["count"], MIN_GROUP_SIZE - 1)
        self.assertIn(str(MIN_GROUP_SIZE), grup["note"] or "",
                      "kapı sessizce uygulanmamalı, gerekçesi dönmeli")

    def test_tur_suzmesi(self):
        _seed(self.repo, MIN_GROUP_SIZE + 1, tur="Konut Finansmanı")
        _seed(self.repo, MIN_GROUP_SIZE + 1, tur="Kart")
        d = self.client().get("/advantageous", params={"type": "Kart"}).json()
        self.assertEqual(list(d["types"]), ["Kart"])

    def test_her_bilesen_gerekcesini_tasir(self):
        _seed(self.repo, MIN_GROUP_SIZE + 1)
        grup = self.client().get("/advantageous").json()["types"]["Konut Finansmanı"]
        for c in grup["ranked"][0]["components"]:
            if c["normalized"] is None:
                self.assertTrue(c["note"],
                                "skorlanmayan alanın nedeni yazılmalı — "
                                "sessiz atlama kabul değil")


class ScoringArtikYalanSoylemiyor(_DepoluTest):
    """Denetimin bulduğu çelişki: uç kendi kodunu yalanlıyordu."""

    def test_composite_weights_artik_null_degil(self):
        d = self.client().get("/scoring", params={"field": "kar_payi_orani"}).json()
        self.assertIsNotNone(
            d["composite_weights"],
            "`DEFAULT_WEIGHTS` kodda duruyor; uç `null` döndüremez")
        self.assertEqual(len(d["composite_weights"]), len(DEFAULT_WEIGHTS))

    def test_composite_note_yoktur_demiyor(self):
        d = self.client().get("/scoring", params={"field": "kar_payi_orani"}).json()
        note = d["composite_note"].casefold()
        self.assertNotIn("yoktur", note,
                         "uç, var olan kodu 'yok' diye sunamaz")
        self.assertEqual(d["composite_endpoint"], "/advantageous")


if __name__ == "__main__":
    unittest.main()
