"""`/refresh*` uçları — ağa çıkmadan, gerçek HTTP yüzeyi üzerinden.

İlgili: ../src/api/main.py, ../src/scraping/tazeleme.py

## Bu dosyanın koruduğu değişmezler

1. **Ön izleme ağa çıkmaz.** Düğmeye basılmadan önce "kaç istek, ne kadar
   sürer, internet gerekir" cevabı çevrimdışı verilebilmeli.
2. **Kritik yol tazelemeden etkilenmez.** Tazeleme koşarken de bittikten
   sonra da `/campaigns`, `/compare` ve `/chat` aynı veri tabanından okumaya
   devam eder; tazeleme kampanya sayısını değiştirmez. Aşağı akışa tek
   dokunuşu, metni DEĞİŞEN belgenin bayat özetini düşürmektir
   (`src/tazeleme_sonrasi.py`) — kayıt silmez, metin/alan yazmaz.
3. **Aynı anda tek iş.** İkinci istek 409 ile reddedilir, sessizce sıraya
   alınmaz.
4. **Bilinmeyen banka 404.** İstemciden gelen slug ile dosya sistemine
   gidilmez.

Hiçbir test ağ kullanmaz: iş yürütücüsü (`calisma_fn`) sahte bir işle
değiştirilir, gerçek toplama katmanı hiç çağrılmaz.
"""

from __future__ import annotations

import sys
import threading
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

try:  # pragma: no cover - ortama bağlı
    import httpx  # noqa: F401
    from fastapi.testclient import TestClient
    HAS_API = True
except ModuleNotFoundError:  # pragma: no cover
    HAS_API = False

from src.scraping.tazeleme import DURUM_TAMAM

requires_api = unittest.skipUnless(HAS_API, "fastapi/httpx yok — API testi atlanıyor")


def _app():
    from src.api.main import build_app
    return build_app()


@requires_api
class TestOnizlemeUcu(unittest.TestCase):
    """`GET /refresh/preview` — ağa çıkmadan tahmin verir."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.client = TestClient(_app())

    def test_onizleme_beklenen_alanlari_dondurur(self) -> None:
        r = self.client.get("/refresh/preview", params={"bank": "kuveyt-turk"})
        self.assertEqual(r.status_code, 200)
        veri = r.json()
        self.assertEqual(veri["bank"], "kuveyt-turk")
        self.assertTrue(veri["internet_gerekir"])
        # 2026-08-13'e kadar `False` bekleniyordu. Beklenti DAVRANIŞ değiştiği
        # için döndü: tazeleme artık metni değişen belgelerin bayat AI özetini
        # düşürüyor (`src/tazeleme_sonrasi.py`). Kapsam dar ve cümleyle
        # anlatılıyor; bayrağı `False` bırakmak ön izlemeyi yalancı yapardı.
        self.assertTrue(veri["veri_tabani_etkilenir"])
        self.assertIn("özet", veri["veri_tabani_etkisi"])
        self.assertTrue(veri["robots_uyumu"])
        self.assertGreaterEqual(veri["gecikme_sn"], 2.0)
        self.assertLessEqual(veri["gecikme_sn"], 5.0)
        self.assertGreater(veri["tahmini_istek_ust"], 0)
        self.assertIn("live", veri["hedef_dizin"])

    def test_bilinmeyen_banka_404(self) -> None:
        r = self.client.get("/refresh/preview", params={"bank": "olmayan-banka"})
        self.assertEqual(r.status_code, 404)


@requires_api
class TestTazelemeUcu(unittest.TestCase):
    """Başlatma / durum / iptal — sahte iş yürütücüsüyle."""

    def setUp(self) -> None:
        self.app = _app()
        self.client = TestClient(self.app)
        # Gerçek toplama katmanı DEVRE DIŞI: testler ağa çıkmaz.
        self.birak = threading.Event()
        self.calisti: list[str] = []

        def sahte_is(bank, raw_dir, durum, **kwargs):
            self.calisti.append(bank.slug)
            self.birak.wait(5)
            kwargs["guncelle"](durum=DURUM_TAMAM, asama="bitti", cekilen=3,
                               yeni=1, degisen=1, ayni=1, hata=0,
                               mesaj="Sahte iş tamamlandı.")
            return durum

        self.app.state.tazeleme._calisma_fn = sahte_is

    def tearDown(self) -> None:
        self.birak.set()

    def _bitene_kadar(self, is_id: str, sn: float = 5.0) -> dict:
        son = time.time() + sn
        while time.time() < son:
            veri = self.client.get(f"/refresh/status/{is_id}").json()
            if veri["bitti"]:
                return veri
            time.sleep(0.02)
        raise AssertionError("iş süresinde bitmedi")

    def test_baslatma_202_ve_durum_izlenebilir(self) -> None:
        r = self.client.post("/refresh", json={"bank": "kuveyt-turk"})
        self.assertEqual(r.status_code, 202)
        is_id = r.json()["is_id"]
        self.assertFalse(r.json()["bitti"])
        self.birak.set()
        son = self._bitene_kadar(is_id)
        self.assertEqual(son["durum"], DURUM_TAMAM)
        self.assertEqual((son["cekilen"], son["yeni"], son["degisen"], son["ayni"]),
                         (3, 1, 1, 1))
        self.assertEqual(self.calisti, ["kuveyt-turk"])

    def test_ayni_anda_ikinci_tazeleme_409(self) -> None:
        ilk = self.client.post("/refresh", json={"bank": "kuveyt-turk"})
        self.assertEqual(ilk.status_code, 202)
        ikinci = self.client.post("/refresh", json={"bank": "albaraka"})
        self.assertEqual(ikinci.status_code, 409)
        self.assertIn("tazeleniyor", ikinci.json()["detail"])
        # İkinci iş HİÇ başlamamalı
        self.birak.set()
        self._bitene_kadar(ilk.json()["is_id"])
        self.assertEqual(self.calisti, ["kuveyt-turk"])

    def test_iptal_bayragi_isaretlenir(self) -> None:
        is_id = self.client.post("/refresh", json={"bank": "kuveyt-turk"}).json()["is_id"]
        r = self.client.post(f"/refresh/cancel/{is_id}")
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.json()["iptal_istendi"])
        self.birak.set()
        self._bitene_kadar(is_id)

    def test_bilinmeyen_is_404(self) -> None:
        self.assertEqual(self.client.get("/refresh/status/yok").status_code, 404)
        self.assertEqual(self.client.post("/refresh/cancel/yok").status_code, 404)

    def test_bilinmeyen_banka_404(self) -> None:
        r = self.client.post("/refresh", json={"bank": "olmayan-banka"})
        self.assertEqual(r.status_code, 404)

    def test_hic_is_yokken_son_durum_null(self) -> None:
        self.assertIsNone(self.client.get("/refresh/status").json())

    def test_tazeleme_kritik_yolu_bozmaz(self) -> None:
        """Tazeleme koşarken kıyas ve belge listesi aynı veri tabanından okur."""
        once = len(self.client.get("/campaigns").json())
        self.assertGreater(once, 0)
        is_id = self.client.post("/refresh", json={"bank": "kuveyt-turk"}).json()["is_id"]
        # İş sürerken kritik yol çalışmaya devam etmeli
        self.assertEqual(len(self.client.get("/campaigns").json()), once)
        self.assertEqual(self.client.get("/health").status_code, 200)
        self.birak.set()
        self._bitene_kadar(is_id)
        self.assertEqual(len(self.client.get("/campaigns").json()), once)


@requires_api
class TestAltAkisBagli(unittest.TestCase):
    """Alt akış gerçekten BAĞLI mı — sahte depo değil, uygulamanın kendi deposu.

    Birim testleri (`test_tazeleme_sonrasi.py`) uzlaştırma mantığını kendi
    kurduğu depoda ölçüyor. Burada ölçülen başka bir şey: `build_app()` geri
    çağrıyı kurdu mu ve o geri çağrı UYGULAMANIN deposunda gerçek kayıtlarla
    eşleşiyor mu. Eşleşme anahtarı belgenin metni; ham dosya metni ile veri
    tabanındaki metin arasındaki normalizasyon farkı bu bağı sessizce koparan
    tek şeydi, ve o ancak gerçek korpusla ölçülebilir.
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.app = _app()
        cls.client = TestClient(cls.app)

    def _ornek_kampanya(self) -> tuple[str, str]:
        for kayit in self.client.get("/campaigns").json():
            if not kayit.get("source_url"):
                continue
            metin = self.client.get(
                f"/campaigns/{kayit['id']}/text").json().get("text") or ""
            if metin.strip():
                return kayit["source_url"], metin
        raise unittest.SkipTest("korpusta adresli belge yok")

    def test_alt_akis_kurulmus(self) -> None:
        self.assertIsNotNone(self.app.state.tazeleme._alt_akis,
                             "tazeleme yöneticisine alt akış bağlanmamış")

    def test_gercek_belge_veri_tabaninda_eslesir(self) -> None:
        url, metin = self._ornek_kampanya()
        rapor = self.app.state.tazeleme._alt_akis(
            [{"source_url": url, "onceki_metin": metin}])
        self.assertEqual(rapor["eslesmeyen_belge"], 0,
                         "değişen belge veri tabanındaki kaydıyla eşleşmedi — "
                         "alt akış sessizce hiçbir şey yapmaz hâle gelir")
        self.assertEqual(rapor["degisen_belge"], 1)

    def test_baska_belgeye_dokunulmaz(self) -> None:
        """Korpusta olmayan bir adres hiçbir satırı etkilemez."""
        once = self.client.get("/summaries/coverage").json()
        rapor = self.app.state.tazeleme._alt_akis(
            [{"source_url": "https://yok.example/hic", "onceki_metin": "x" * 50}])
        self.assertEqual(rapor["gecersizlenen_ozet"], 0)
        self.assertEqual(rapor["eslesmeyen_belge"], 1)
        self.assertEqual(self.client.get("/summaries/coverage").json()["ozetli"],
                         once["ozetli"])


@requires_api
class TestIstemciKisitiGevsetemez(unittest.TestCase):
    """Etik toplama kısıtları istek gövdesinden ayarlanamaz.

    Gövdeye `gecikme_sn: 0` ya da `ignore_robots: true` koyan bir istemci
    hiçbir şeyi değiştiremez: şema yalnız banka slug'ını taşır ve fazladan
    alanlar hiçbir yere bağlanmaz.
    """

    def test_sema_yalnizca_banka_tasir(self) -> None:
        # `RefreshReq` 19 Ağu 2026'da `routers/isler.py`'ye taşındı
        # (API katmanının kademeli bölünmesi, 3. adım).
        from src.api.routers.isler import RefreshReq

        istek = RefreshReq(bank="kuveyt-turk", gecikme_sn=0, ignore_robots=True)
        self.assertEqual(istek.bank, "kuveyt-turk")
        self.assertEqual(set(istek.model_dump().keys()), {"bank"})


if __name__ == "__main__":
    unittest.main()
