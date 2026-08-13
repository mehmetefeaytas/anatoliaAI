"""İşlem günlüğü (audit log) — yazıcı, ara katman ve `GET /log`.

İlgili: ../src/api/gunluk.py, ../src/api/main.py

## Bu dosyanın koruduğu değişmezler

1. **Günlük yazımı isteği DÜŞÜRMEZ.** Disk dolu / izin yok / yol bozuk
   olduğunda uç yine 200 döner ve hata ayrı kanaldan (logger) bildirilir.
   Sistemin en sık ihlal edilecek vaadi budur: bir denetim kaydı, uğruna
   kullanıcının ekranını karartmaya değmez.
2. **Sır sızmaz.** İstek gövdesi ve sorgu dizgesi günlüğe GİRMEZ. Sohbet
   soruları ve `?q=` arama terimleri kişisel veri taşıyabilir; kalıcı ve
   ekleme-only bir dosyaya yazılan şey geri alınamaz.
3. **Yazan uçlar işaretlenir.** Kullanıcının saydığı eylem uçlarının hepsi
   (`/refresh`, `/refresh/cancel/{id}`, `/summaries/build`,
   `/summaries/cancel/{id}`, `/extract`) `yazan=true` ile düşer; okuma uçları
   düşmez. Panel varsayılanı bu bayrağa dayanıyor.
4. **Döndürme sessiz değildir.** Dosya sınırı aştığında döndürülür VE
   döndürmenin kendisi yeni dosyanın ilk satırına kayıt olarak düşer; yoksa
   kısalmış bir günlüğe bakan kişi "kayıt kayboldu mu" sorusunu
   cevaplayamaz.
5. **Ekleme eşzamanlı güvenlidir.** FastAPI `def` uçlarını threadpool'da
   koşturuyor; paralel yazımlar birbirinin satırını bozmamalı.

Hiçbir test gerçek `data/gunluk/` dizinine yazmaz: her koşu kendi `tempfile`
dizinini kullanır ve uygulamanın yazıcısı onunla değiştirilir.
"""

from __future__ import annotations

import json
import sys
import tempfile
import threading
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

from src.api.gunluk import (
    OLAY_DONDURME,
    OLAY_ISTEK,
    YAZAN_METOTLAR,
    GunlukYazici,
    yazan_mi,
)

requires_api = unittest.skipUnless(HAS_API, "fastapi/httpx yok — API testi atlanıyor")


def _oku(yol: Path) -> list[dict]:
    """Günlük dosyasındaki kayıtlar (yazılış sırasıyla)."""
    if not yol.exists():
        return []
    return [json.loads(s) for s in yol.read_text(encoding="utf-8").splitlines() if s.strip()]


def _app():
    """Bellek içi depoyla `build_app()` — komşu testlerin sızıntısına karşı.

    `main.DB_PATH` MODÜL SEVİYESİNDE okunuyor ve birçok API testi onu kendi
    geçici dosyasına çevirip geri koyuyor. Tam suite koşumunda bu değer,
    dizini çoktan silinmiş bir yolu gösterebiliyor ve `build_app()`
    `sqlite3.OperationalError: unable to open database file` ile düşüyor.
    Sabit doğrudan sabitleniyor (aynı çare `test_chat_guvenlik_yuzeyi.py`
    içinde de kullanılıyor); bu dosyanın ölçtüğü şey günlük, depo değil.
    """
    from src.api import main as api_main
    eski = api_main.DB_PATH
    api_main.DB_PATH = ":memory:"
    try:
        return api_main.build_app()
    finally:
        api_main.DB_PATH = eski


# --------------------------------------------------------------------------- #
# Yazıcının kendisi — API'siz, saf birim testleri
# --------------------------------------------------------------------------- #
class TestYaziciTemel(unittest.TestCase):
    """`GunlukYazici.yaz()` / `oku()` — dosya yokken, varken, bozukken."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.yol = Path(self.tmp.name) / "alt" / "gunluk.jsonl"
        self.yazici = GunlukYazici(self.yol)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_dizin_kendiliginden_acilir(self) -> None:
        """İlk yazımda ara dizinler kurulur; kurulum adımı gerekmez."""
        self.assertTrue(self.yazici.istek_kaydet(
            metot="POST", yol="/refresh", durum=202, sure_ms=1.0))
        self.assertTrue(self.yol.exists())

    def test_kayit_semasi(self) -> None:
        self.yazici.istek_kaydet(metot="post", yol="/refresh", durum=202,
                                 sure_ms=12.345, istemci="127.0.0.1",
                                 is_id="abc123", eylem={"banka": "albaraka"})
        (kayit,) = _oku(self.yol)
        self.assertEqual(kayit["olay"], OLAY_ISTEK)
        self.assertEqual(kayit["metot"], "POST")  # büyük harfe normalize
        self.assertEqual(kayit["yol"], "/refresh")
        self.assertEqual(kayit["durum"], 202)
        self.assertEqual(kayit["sure_ms"], 12.3)  # tek ondalık
        self.assertIs(kayit["yazan"], True)
        self.assertEqual(kayit["istemci"], "127.0.0.1")
        self.assertEqual(kayit["is_id"], "abc123")
        self.assertEqual(kayit["eylem"], {"banka": "albaraka"})
        # Zaman UTC ISO-8601 (projede `utc_now_iso()`).
        self.assertRegex(kayit["zaman"], r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}")

    def test_eylem_yoksa_alan_hic_yazilmaz(self) -> None:
        """Boş bir `eylem` sözlüğü yazılmaz — `null` ile "yok" karışmasın."""
        self.yazici.istek_kaydet(metot="GET", yol="/stats", durum=200,
                                 sure_ms=1.0, eylem={})
        (kayit,) = _oku(self.yol)
        self.assertNotIn("eylem", kayit)

    def test_eylem_ic_ice_yapiyi_dusurur(self) -> None:
        """Bir uç yanlışlıkla gövde geçirirse günlük onu YUTMAZ.

        Uçlar bugün dar sözlükler bildiriyor; bu budama, ileride birinin
        yanıtın tamamını geçirmesine karşı duruyor.
        """
        self.yazici.istek_kaydet(
            metot="POST", yol="/extract", durum=200, sure_ms=1.0,
            eylem={"banka": "albaraka", "govde": {"text": "gizli"},
                   "alanlar": [1, 2, 3], "sayi": 7, "bayrak": True,
                   "uzun": "x" * 500})
        (kayit,) = _oku(self.yol)
        eylem = kayit["eylem"]
        self.assertEqual(eylem["banka"], "albaraka")
        self.assertEqual(eylem["sayi"], 7)
        self.assertIs(eylem["bayrak"], True)
        self.assertNotIn("govde", eylem)
        self.assertNotIn("alanlar", eylem)
        self.assertLess(len(eylem["uzun"]), 500)

    def test_bozuk_satir_okumayi_durdurmaz(self) -> None:
        """Yarım/çöp bir satır atlanır; dosyanın geri kalanı okunur."""
        self.yazici.istek_kaydet(metot="POST", yol="/a", durum=200, sure_ms=1.0)
        with self.yol.open("a", encoding="utf-8") as f:
            f.write("{yarim satir\n")
        self.yazici.istek_kaydet(metot="POST", yol="/b", durum=200, sure_ms=1.0)
        kayitlar, toplam = self.yazici.oku()
        self.assertEqual(toplam, 2)
        self.assertEqual([k["yol"] for k in kayitlar], ["/b", "/a"])

    def test_yazan_mi_metoda_bakar(self) -> None:
        for metot in ("POST", "put", "PATCH", "delete"):
            self.assertTrue(yazan_mi(metot), metot)
        for metot in ("GET", "head", "OPTIONS", None, ""):
            self.assertFalse(yazan_mi(metot), metot)


class TestGunlukIstegiDusurmez(unittest.TestCase):
    """Yazma başarısız olduğunda çağıran ETKİLENMEZ — sadece uyarı düşer."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_yazilamayan_yol_istisna_atmaz(self) -> None:
        # Ara dizin adı bir DOSYA: `mkdir` de `open` de düşer.
        engel = Path(self.tmp.name) / "engel"
        engel.write_text("dosya, dizin değil", encoding="utf-8")
        yazici = GunlukYazici(engel / "gunluk.jsonl")
        with self.assertLogs("src.api.gunluk", level="WARNING"):
            sonuc = yazici.istek_kaydet(metot="POST", yol="/refresh",
                                        durum=202, sure_ms=1.0)
        self.assertFalse(sonuc)

    def test_olmayan_dosya_bos_okunur(self) -> None:
        yazici = GunlukYazici(Path(self.tmp.name) / "hic-yazilmadi.jsonl")
        self.assertEqual(yazici.oku(), ([], 0))


class TestDondurme(unittest.TestCase):
    """Sınır aşıldığında döndürülür ve döndürme KAYDA DÜŞER."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.yol = Path(self.tmp.name) / "gunluk.jsonl"

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _doldur(self, yazici: GunlukYazici, adet: int) -> None:
        for i in range(adet):
            yazici.istek_kaydet(metot="POST", yol=f"/uc/{i}", durum=200,
                                sure_ms=1.0)

    def test_dondurme_kaydi_yeni_dosyanin_ilk_satiri(self) -> None:
        yazici = GunlukYazici(self.yol, azami_bayt=1024, yedek_sayisi=2)
        self._doldur(yazici, 40)
        self.assertTrue(self.yol.with_name("gunluk.jsonl.1").exists())
        ilk = _oku(self.yol)[0]
        self.assertEqual(ilk["olay"], OLAY_DONDURME)
        self.assertEqual(ilk["tasinan_dosya"], "gunluk.jsonl.1")
        self.assertGreaterEqual(ilk["bayt"], 1024)

    def test_kusak_sayisi_asilmaz_ve_silinen_yazilir(self) -> None:
        """Toplam tavan `(N+1) × azami_bayt`; silinen kuşak adı kayda geçer."""
        yazici = GunlukYazici(self.yol, azami_bayt=1024, yedek_sayisi=2)
        self._doldur(yazici, 400)
        self.assertFalse(self.yol.with_name("gunluk.jsonl.3").exists())
        silinenler = [k for k in _oku(self.yol)
                      if k.get("olay") == OLAY_DONDURME and k.get("silinen_dosya")]
        self.assertTrue(silinenler, "silinen kuşak hiç kayda geçmemiş")
        self.assertEqual(silinenler[-1]["silinen_dosya"], "gunluk.jsonl.2")

    def test_dondurme_kaydi_yalniz_yazanlar_suzgecinde_de_gorunur(self) -> None:
        """"Kayıt kayboldu mu" sorusu tam da bu görünümde soruluyor."""
        yazici = GunlukYazici(self.yol, azami_bayt=1024, yedek_sayisi=1)
        for i in range(40):
            yazici.istek_kaydet(metot="GET", yol=f"/oku/{i}", durum=200,
                                sure_ms=1.0)
        kayitlar, _ = yazici.oku(yalniz_yazanlar=True)
        self.assertTrue(any(k.get("olay") == OLAY_DONDURME for k in kayitlar))


class TestEszamanliYazma(unittest.TestCase):
    """Paralel yazımlar birbirinin satırını bozmaz (uçlar threadpool'da koşar)."""

    def test_paralel_yazimlar_tam_satir_uretir(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            yazici = GunlukYazici(Path(tmp) / "gunluk.jsonl")
            hatalar: list[BaseException] = []

            def kos(no: int) -> None:
                try:
                    for i in range(25):
                        yazici.istek_kaydet(metot="POST", yol=f"/is/{no}/{i}",
                                            durum=200, sure_ms=1.0)
                except BaseException as exc:  # pragma: no cover
                    hatalar.append(exc)

            isler = [threading.Thread(target=kos, args=(n,)) for n in range(8)]
            for t in isler:
                t.start()
            for t in isler:
                t.join()
            self.assertEqual(hatalar, [])
            _, toplam = yazici.oku()
            self.assertEqual(toplam, 8 * 25)


class TestSuzgecler(unittest.TestCase):
    """`oku()` süzgeçleri + sayfalama + sıra (yeniden eskiye)."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.yazici = GunlukYazici(Path(self.tmp.name) / "gunluk.jsonl")
        self.yazici.istek_kaydet(metot="GET", yol="/stats", durum=200, sure_ms=1)
        self.yazici.istek_kaydet(metot="POST", yol="/refresh", durum=202, sure_ms=2)
        self.yazici.istek_kaydet(metot="GET", yol="/compare", durum=200, sure_ms=3)
        self.yazici.istek_kaydet(metot="POST", yol="/extract", durum=200, sure_ms=4)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_varsayilan_yalniz_yazanlar(self) -> None:
        kayitlar, toplam = self.yazici.oku()
        self.assertEqual(toplam, 2)
        self.assertEqual([k["yol"] for k in kayitlar], ["/extract", "/refresh"])

    def test_hepsi_yeniden_eskiye(self) -> None:
        kayitlar, toplam = self.yazici.oku(yalniz_yazanlar=False)
        self.assertEqual(toplam, 4)
        self.assertEqual([k["yol"] for k in kayitlar],
                         ["/extract", "/compare", "/refresh", "/stats"])

    def test_metot_ve_yol_suzgeci(self) -> None:
        kayitlar, toplam = self.yazici.oku(yalniz_yazanlar=False, metot="get")
        self.assertEqual(toplam, 2)
        kayitlar, toplam = self.yazici.oku(yalniz_yazanlar=False, yol="COMP")
        self.assertEqual((toplam, kayitlar[0]["yol"]), (1, "/compare"))

    def test_sayfalama_toplami_degistirmez(self) -> None:
        kayitlar, toplam = self.yazici.oku(yalniz_yazanlar=False, limit=2,
                                           offset=1)
        self.assertEqual(toplam, 4)
        self.assertEqual([k["yol"] for k in kayitlar], ["/compare", "/refresh"])

    def test_tarih_araligi_gun_sonunu_kapsar(self) -> None:
        """Yalnız tarih verilen `bitis` o günün TAMAMINI içerir."""
        gun = _oku(self.yazici.yol)[0]["zaman"][:10]
        _, toplam = self.yazici.oku(yalniz_yazanlar=False, baslangic=gun,
                                    bitis=gun)
        self.assertEqual(toplam, 4)

    def test_bozuk_zaman_suzgeci_deger_hatasi(self) -> None:
        with self.assertRaises(ValueError):
            self.yazici.oku(baslangic="dün")


# --------------------------------------------------------------------------- #
# HTTP yüzeyi — ara katman + `GET /log`
# --------------------------------------------------------------------------- #
@requires_api
class TestAraKatman(unittest.TestCase):
    """Her istek düşer; yazanlar işaretlenir; sır sızmaz."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.yol = Path(self.tmp.name) / "gunluk.jsonl"
        self.app = _app()
        # Uygulamanın yazıcısı geçici dosyaya çevrilir: testler gerçek
        # `data/gunluk/` dizinine DOKUNMAZ.
        self.app.state.gunluk = GunlukYazici(self.yol)
        self.client = TestClient(self.app)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_okuma_istegi_kaydedilir_ama_yazan_degil(self) -> None:
        self.assertEqual(self.client.get("/health").status_code, 200)
        (kayit,) = _oku(self.yol)
        self.assertEqual((kayit["metot"], kayit["yol"], kayit["durum"]),
                         ("GET", "/health", 200))
        self.assertIs(kayit["yazan"], False)
        self.assertIsNotNone(kayit["istemci"])
        self.assertGreaterEqual(kayit["sure_ms"], 0.0)

    def test_hata_veren_istek_de_dusar(self) -> None:
        """404 sessizce kaybolmaz — günlüğün en çok gerektiği an odur."""
        self.client.post("/refresh/cancel/olmayan-is")
        (kayit,) = _oku(self.yol)
        self.assertEqual((kayit["durum"], kayit["yazan"]), (404, True))
        # İş kimliği YOL PARAMETRESİNDEN okunur; uçtan ayrıca bildirilmez.
        self.assertEqual(kayit["is_id"], "olmayan-is")

    def test_sorgu_dizgesi_kaydedilmez(self) -> None:
        gizli = "cok-gizli-arama-terimi"
        self.client.get("/campaigns", params={"q": gizli, "limit": 1})
        ham = self.yol.read_text(encoding="utf-8")
        self.assertNotIn(gizli, ham)
        self.assertIn('"yol": "/campaigns"', ham)

    def test_sohbet_govdesi_kaydedilmez(self) -> None:
        """`POST /chat` yazan sayılır ama SORUSU günlüğe girmez."""
        gizli = "50 bin TL kredim var ve kimlik numaram 11111111111"
        self.client.post("/chat", json={"question": gizli})
        ham = self.yol.read_text(encoding="utf-8")
        self.assertNotIn("11111111111", ham)
        self.assertNotIn("kredim", ham)
        kayit = _oku(self.yol)[-1]
        self.assertEqual(kayit["yol"], "/chat")
        self.assertIs(kayit["yazan"], True)
        self.assertNotIn("eylem", kayit)

    def test_gunluk_yazilamazsa_istek_yine_calisir(self) -> None:
        """DEĞİŞMEZ: günlük yazımı isteği düşürmez."""
        engel = Path(self.tmp.name) / "engel"
        engel.write_text("dosya", encoding="utf-8")
        self.app.state.gunluk = GunlukYazici(engel / "gunluk.jsonl")
        with self.assertLogs("src.api.gunluk", level="WARNING"):
            r = self.client.get("/health")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["status"], "ok")


@requires_api
class TestYazanUclarIsaretlenir(unittest.TestCase):
    """Kullanıcının saydığı eylem uçları `yazan=true` ile düşer.

    Uçların METODU üzerinden ölçülür: `gunluk.yazan_mi()` yalnız metoda bakıyor
    ve ikinci bir yol listesi tutmuyor. Bu test, o kararın bugün gerçekten
    yeterli olduğunu kilitler — bir eylem ucu ileride `GET`e çevrilirse
    burada kırmızı olur.
    """

    EYLEM_YOLLARI = (
        "/refresh",
        "/refresh/cancel/{job_id}",
        "/summaries/build",
        "/summaries/cancel/{job_id}",
        "/extract",
    )

    @classmethod
    def setUpClass(cls) -> None:
        cls.app = _app()

    def test_eylem_uclarinin_hepsi_yazan_metotta(self) -> None:
        rotalar = {}
        for rota in self.app.routes:
            for metot in getattr(rota, "methods", set()) or set():
                rotalar.setdefault(getattr(rota, "path", ""), set()).add(metot)
        for yol in self.EYLEM_YOLLARI:
            with self.subTest(yol=yol):
                self.assertIn(yol, rotalar, "eylem ucu kaybolmuş")
                yazanlar = {m for m in rotalar[yol] if m in YAZAN_METOTLAR}
                self.assertTrue(
                    yazanlar,
                    f"{yol} artık yazan bir metotta değil; günlük onu "
                    "'okuma' olarak işaretler")

    def test_okuma_uclari_yazan_degil(self) -> None:
        for yol in ("/health", "/campaigns", "/compare", "/stats",
                    "/refresh/preview", "/refresh/status", "/log"):
            with self.subTest(yol=yol):
                self.assertFalse(yazan_mi("GET"))


@requires_api
class TestRefreshEylemOzeti(unittest.TestCase):
    """`POST /refresh` günlüğe HANGİ BANKA'yı yazdığını bırakır."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.yol = Path(self.tmp.name) / "gunluk.jsonl"
        self.app = _app()
        self.app.state.gunluk = GunlukYazici(self.yol)
        self.client = TestClient(self.app)
        # Gerçek toplama katmanı DEVRE DIŞI: test ağa çıkmaz.
        self.birak = threading.Event()

        def sahte_is(bank, raw_dir, durum, **kwargs):
            self.birak.wait(5)
            kwargs["guncelle"](durum="tamam", asama="bitti")
            return durum

        self.app.state.tazeleme._calisma_fn = sahte_is

    def tearDown(self) -> None:
        self.birak.set()
        self.tmp.cleanup()

    def test_banka_ve_is_kimligi_kayda_gecer(self) -> None:
        r = self.client.post("/refresh", json={"bank": "kuveyt-turk"})
        self.assertEqual(r.status_code, 202)
        kayit = _oku(self.yol)[-1]
        self.assertEqual(kayit["yol"], "/refresh")
        self.assertIs(kayit["yazan"], True)
        self.assertEqual(kayit["is_id"], r.json()["is_id"])
        self.assertEqual(kayit["eylem"]["banka"], "kuveyt-turk")
        # `is_id` üst düzeyde tutulur, eylem özetinde İKİNCİ kopyası olmaz.
        self.assertNotIn("is_id", kayit["eylem"])

    def test_reddedilen_tazeleme_de_kayda_gecer(self) -> None:
        """409 ile reddedilen ikinci istek görünmez olmaz."""
        self.client.post("/refresh", json={"bank": "kuveyt-turk"})
        r = self.client.post("/refresh", json={"bank": "albaraka"})
        self.assertEqual(r.status_code, 409)
        kayit = _oku(self.yol)[-1]
        self.assertEqual((kayit["yol"], kayit["durum"]), ("/refresh", 409))
        # Eylem BİLDİRİLMEZ: iş başlamadı, "albaraka tazelendi" izlenimi
        # veren bir özet uydurma olurdu.
        self.assertNotIn("eylem", kayit)


@requires_api
class TestLogUcu(unittest.TestCase):
    """`GET /log` — süzgeç, sayfalama, başlık, hatalı girdi."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.yol = Path(self.tmp.name) / "gunluk.jsonl"
        self.app = _app()
        self.yazici = GunlukYazici(self.yol)
        self.app.state.gunluk = self.yazici
        self.client = TestClient(self.app)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_varsayilan_yalniz_yazanlari_dondurur(self) -> None:
        self.client.get("/health")
        self.client.get("/stats")
        self.client.post("/refresh/cancel/yok")
        kayitlar = self.client.get("/log").json()
        self.assertTrue(kayitlar)
        self.assertTrue(all(k["yazan"] for k in kayitlar))
        self.assertEqual(kayitlar[0]["yol"], "/refresh/cancel/yok")

    def test_hepsi_bayragiyla_okumalar_da_gelir(self) -> None:
        self.client.get("/health")
        r = self.client.get("/log", params={"yalniz_yazanlar": "false"})
        yollar = [k["yol"] for k in r.json()]
        self.assertIn("/health", yollar)
        # Toplam GÖVDEDE değil başlıkta — `/campaigns` ile aynı sözleşme.
        self.assertEqual(int(r.headers["X-Toplam-Kayit"]), len(yollar))

    def test_sayfalama_toplami_korur(self) -> None:
        for i in range(10):
            self.yazici.istek_kaydet(metot="POST", yol=f"/uc/{i}", durum=200,
                                     sure_ms=1.0)
        r = self.client.get("/log", params={"limit": 3, "offset": 2})
        self.assertEqual(len(r.json()), 3)
        # 10 sahte + bu isteğin kendisinden ÖNCE yazılan hiçbir şey yok.
        self.assertEqual(int(r.headers["X-Toplam-Kayit"]), 10)

    def test_yol_ve_metot_suzgeci(self) -> None:
        self.yazici.istek_kaydet(metot="POST", yol="/refresh", durum=202,
                                 sure_ms=1.0)
        self.yazici.istek_kaydet(metot="DELETE", yol="/bir-sey", durum=200,
                                 sure_ms=1.0)
        r = self.client.get("/log", params={"yol": "refresh"})
        self.assertEqual([k["yol"] for k in r.json()], ["/refresh"])
        r = self.client.get("/log", params={"metot": "delete"})
        self.assertEqual([k["yol"] for k in r.json()], ["/bir-sey"])

    def test_bozuk_tarih_400(self) -> None:
        r = self.client.get("/log", params={"baslangic": "dün"})
        self.assertEqual(r.status_code, 400)
        self.assertIn("ISO-8601", r.json()["detail"])

    def test_gecersiz_limit_400(self) -> None:
        self.assertEqual(self.client.get("/log", params={"limit": 0}).status_code, 400)
        self.assertEqual(self.client.get("/log", params={"limit": 9999}).status_code, 400)
        self.assertEqual(self.client.get("/log", params={"offset": -1}).status_code, 400)

    def test_gunluk_yokken_bos_liste(self) -> None:
        """Hiç kayıt yokken uç ÇÖKMEZ, boş liste döner (boş ≠ hata)."""
        self.app.state.gunluk = GunlukYazici(Path(self.tmp.name) / "yok.jsonl")
        r = self.client.get("/log")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json(), [])


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
