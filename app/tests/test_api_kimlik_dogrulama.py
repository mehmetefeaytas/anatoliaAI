"""API kimlik doğrulama kancası — geriye uyum, roller, muafiyet, sızıntı.

İlgili: ../src/api/kimlik.py, ../src/api/main.py (`build_app()` bağlaması)
        ../docs/kimlik-dogrulama.md

## Neden bu dosya var

`src/api/` altında kimlik doğrulamaya dair TEK BİR SATIR yoktu:

    grep -rniE "api_key|authoriz|bearer|jwt|oauth" src/api/   ->  0 sonuç

Yani "kurum sistemlerine entegre edilebilir mimari" iddiası, en temel
entegrasyon noktasında — kimin çağırdığı — boştu. Bir katılım bankasının
kendi ağına koyacağı bir servisin, çağıranı ayırt edememesi mimari bir
eksikliktir; veri hassas olmasa bile `/refresh` internete çıkan ve diske
yazan bir EYLEM ucudur.

## Bu testlerin kilitlediği dört değişmez

1. **Geriye uyum.** Anahtar tanımlı DEĞİLSE API bugünkü gibi çalışır. Bu
   şart, jüri demosunun ve mevcut test paketinin anahtar dağıtımı olmadan
   koşabilmesi için var. Kırılırsa `docker compose up` yolu ve yüzlerce API
   testi aynı anda düşer.
2. **`/health` muaf.** Çevrimdışı kanıt koşumu (`--network none`) ve
   konteyner sağlık probu bu ucu anahtarsız çağırıyor. Kapatmak ölçülmüş bir
   kanıtı kırardı.
3. **Rol ayrımı gerçek.** Salt-okuma anahtarı okuma uçlarında çalışır, eylem
   uçlarında (`/refresh`, `/summaries/build`) 403 alır. Aksi hâlde iki rol
   ilan edip tek rol uygulamak olurdu.
4. **Anahtar hiçbir yere sızmaz.** Ne uygulama log'una, ne işlem günlüğüne,
   ne hata mesajına. Hata mesajı ayrıca hangi anahtarın yanlış olduğunu
   söylemez: "tanımsız anahtar" ile "yanlış anahtar" AYNI cevabı alır.

Saf birim testleri (`AnahtarDeposu`, `karar_ver`) fastapi OLMADAN koşar —
çekirdek katmanın sıfır bağımlılık iddiası bu dosyada da korunuyor.
"""

from __future__ import annotations

import json
import logging
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.api import kimlik

try:  # pragma: no cover - ortama bağlı
    import httpx  # noqa: F401
    from fastapi.testclient import TestClient
    HAS_API = True
except ModuleNotFoundError:  # pragma: no cover
    HAS_API = False

requires_api = unittest.skipUnless(HAS_API, "fastapi/httpx yok — API testi atlanıyor")

# Gerçekçi uzunlukta anahtarlar: `ASGARI_UZUNLUK` uyarısı bu dosyada
# tetiklenmesin ki log iddiaları başka bir uyarıyla karışmasın.
TAM = "tam-anahtar-0123456789abcdef"
OKUMA = "okuma-anahtari-fedcba9876543210"
YANLIS = "bu-anahtar-hic-tanimli-degil-0000"

#: Doğrulamayı etkileyen tüm ortam değişkenleri — test izolasyonu için.
ORTAM_ANAHTARLARI = (kimlik.ORTAM_ANAHTARLAR, kimlik.ORTAM_SALT_OKUMA,
                     kimlik.ORTAM_DOSYA)


class _OrtamKarantinasi(unittest.TestCase):
    """Kimlik ortam değişkenlerini her testten sonra eski hâline döndürür.

    Değişkenler `build_app()` ANINDA okunuyor (modül seviyesinde önbelleğe
    ALINMIYOR), yani izolasyon için modülü yeniden içe aktarmak gerekmiyor —
    ama sızan bir değişken komşu API testlerinin hepsini 401'e düşürürdü.
    """

    def setUp(self) -> None:
        self._onceki = {k: os.environ.get(k) for k in ORTAM_ANAHTARLARI}
        for k in ORTAM_ANAHTARLARI:
            os.environ.pop(k, None)

    def tearDown(self) -> None:
        for k, v in self._onceki.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    def _app(self, **ortam: str):
        """Bellek içi depoyla `build_app()` — verilen kimlik ortamıyla.

        `main.DB_PATH` modül seviyesinde okunuyor ve komşu API testleri onu
        kendi geçici dosyalarına çevirip geri koyuyor; tam suite koşumunda o
        değer silinmiş bir dizini gösterebiliyor. Bu dosyanın ölçtüğü şey
        kimlik, depo değil — bu yüzden `:memory:` sabitleniyor
        (aynı çare `test_api_gunluk.py::_app` içinde de var).
        """
        for k, v in ortam.items():
            os.environ[k] = v
        from src.api import main as api_main
        eski = api_main.DB_PATH
        api_main.DB_PATH = ":memory:"
        try:
            return api_main.build_app()
        finally:
            api_main.DB_PATH = eski


# --------------------------------------------------------------------------- #
# 1. Saf birim: anahtar deposu — fastapi GEREKMEZ
# --------------------------------------------------------------------------- #
class TestAnahtarDeposu(unittest.TestCase):

    def test_bos_depo_KAPALI(self) -> None:
        """Hiç anahtar yoksa doğrulama devrede değildir (geriye uyum)."""
        self.assertFalse(kimlik.AnahtarDeposu().acik)

    def test_ortamdan_virgullu_liste(self) -> None:
        depo = kimlik.AnahtarDeposu.ortamdan({
            kimlik.ORTAM_ANAHTARLAR: f" {TAM} , ikinci-anahtar-abcdef ",
        })
        self.assertTrue(depo.acik)
        self.assertEqual(depo.rol(TAM), kimlik.ROL_TAM)
        self.assertEqual(depo.rol("ikinci-anahtar-abcdef"), kimlik.ROL_TAM)
        self.assertEqual(depo.sayim()[kimlik.ROL_TAM], 2)

    def test_salt_okuma_degiskeni_rolu_belirler(self) -> None:
        depo = kimlik.AnahtarDeposu.ortamdan({kimlik.ORTAM_SALT_OKUMA: OKUMA})
        self.assertEqual(depo.rol(OKUMA), kimlik.ROL_SALT_OKUMA)
        self.assertEqual(depo.sayim()[kimlik.ROL_TAM], 0)

    def test_rol_oneki_ayristirilir(self) -> None:
        """`salt-okuma:<anahtar>` biçimi tek değişkende iki rol taşımayı sağlar."""
        depo = kimlik.AnahtarDeposu.ortamdan({
            kimlik.ORTAM_ANAHTARLAR: f"{TAM},salt-okuma:{OKUMA}",
        })
        self.assertEqual(depo.rol(TAM), kimlik.ROL_TAM)
        self.assertEqual(depo.rol(OKUMA), kimlik.ROL_SALT_OKUMA)

    def test_iki_nokta_iceren_anahtar_KIRPILMAZ(self) -> None:
        """Önek yalnız BİLİNEN bir rol adıysa ayrıştırılır."""
        ham = "proje:a1b2c3d4e5f6g7h8"
        depo = kimlik.AnahtarDeposu.ortamdan({kimlik.ORTAM_ANAHTARLAR: ham})
        self.assertEqual(depo.rol(ham), kimlik.ROL_TAM)

    def test_ayni_anahtar_iki_rolde_KISITLI_olani_kazanir(self) -> None:
        """Yapılandırma hatasının maliyeti FAZLA yetki olmamalı."""
        depo = kimlik.AnahtarDeposu.ortamdan({
            kimlik.ORTAM_ANAHTARLAR: TAM,
            kimlik.ORTAM_SALT_OKUMA: TAM,
        })
        self.assertEqual(depo.rol(TAM), kimlik.ROL_SALT_OKUMA)

    def test_bilinmeyen_ve_bos_anahtar_None(self) -> None:
        depo = kimlik.AnahtarDeposu.ortamdan({kimlik.ORTAM_ANAHTARLAR: TAM})
        self.assertIsNone(depo.rol(YANLIS))
        self.assertIsNone(depo.rol(""))
        self.assertIsNone(depo.rol(None))

    def test_ascii_disi_anahtar_TypeError_vermez(self) -> None:
        """`hmac.compare_digest` dizgede ASCII dışını reddeder; bayt kullanıyoruz."""
        depo = kimlik.AnahtarDeposu.ortamdan({kimlik.ORTAM_ANAHTARLAR: "şifre-çok-güçlü"})
        self.assertEqual(depo.rol("şifre-çok-güçlü"), kimlik.ROL_TAM)
        self.assertIsNone(depo.rol("sifre-cok-guclu"))

    def test_dosyadan_okur_yorum_ve_bos_satir_atlanir(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            yol = Path(td) / "anahtarlar.txt"
            yol.write_text(
                f"# panel anahtarı\n{TAM}\n\nsalt-okuma:{OKUMA}\n",
                encoding="utf-8")
            depo = kimlik.AnahtarDeposu.ortamdan({kimlik.ORTAM_DOSYA: str(yol)})
        self.assertEqual(depo.rol(TAM), kimlik.ROL_TAM)
        self.assertEqual(depo.rol(OKUMA), kimlik.ROL_SALT_OKUMA)

    def test_okunamayan_dosya_SESSIZ_gecmez(self) -> None:
        """`API_KEYS_FILE` verilip okunamıyorsa doğrulamasız açılmak YASAK."""
        with self.assertRaises(OSError):
            kimlik.AnahtarDeposu.ortamdan(
                {kimlik.ORTAM_DOSYA: "/olmayan/dizin/anahtarlar.txt"})

    def test_repr_anahtari_GOSTERMEZ(self) -> None:
        """İstisna izi ya da hata ayıklama çıktısı anahtarı diske düşürmemeli."""
        depo = kimlik.AnahtarDeposu.ortamdan({kimlik.ORTAM_ANAHTARLAR: TAM})
        self.assertNotIn(TAM, repr(depo))


# --------------------------------------------------------------------------- #
# 2. Saf birim: karar fonksiyonu — HTTP GEREKMEZ
# --------------------------------------------------------------------------- #
class TestKararVer(unittest.TestCase):

    def setUp(self) -> None:
        self.kapali = kimlik.AnahtarDeposu()
        self.acik = kimlik.AnahtarDeposu.ortamdan({
            kimlik.ORTAM_ANAHTARLAR: TAM,
            kimlik.ORTAM_SALT_OKUMA: OKUMA,
        })

    def test_depo_kapaliyken_her_sey_gecer(self) -> None:
        k = kimlik.karar_ver(self.kapali, "POST", "/refresh", None)
        self.assertTrue(k.gecer)
        self.assertEqual(k.rol, kimlik.ROL_KAPALI)

    def test_health_muaf_depo_ACIKKEN_de(self) -> None:
        k = kimlik.karar_ver(self.acik, "GET", "/health", None)
        self.assertTrue(k.gecer)
        self.assertEqual(k.rol, kimlik.ROL_MUAF)

    def test_options_muaf(self) -> None:
        """CORS ön-uçuşu özel başlık taşımaz; 401 gerçek isteği hiç göndermez."""
        self.assertTrue(kimlik.karar_ver(self.acik, "OPTIONS", "/banks", None).gecer)

    def test_anahtar_yok_401(self) -> None:
        k = kimlik.karar_ver(self.acik, "GET", "/banks", None)
        self.assertEqual(k.durum, 401)

    def test_yanlis_anahtar_401(self) -> None:
        k = kimlik.karar_ver(self.acik, "GET", "/banks", YANLIS)
        self.assertEqual(k.durum, 401)

    def test_mesaj_HANGI_anahtarin_yanlis_oldugunu_soylemez(self) -> None:
        k = kimlik.karar_ver(self.acik, "GET", "/banks", YANLIS)
        self.assertNotIn(YANLIS, k.mesaj or "")
        self.assertNotIn(TAM, k.mesaj or "")

    def test_tam_anahtar_eylem_ucunda_gecer(self) -> None:
        k = kimlik.karar_ver(self.acik, "POST", "/refresh", TAM)
        self.assertTrue(k.gecer)
        self.assertEqual(k.rol, kimlik.ROL_TAM)

    def test_salt_okuma_okuma_ucunda_gecer(self) -> None:
        self.assertTrue(kimlik.karar_ver(self.acik, "GET", "/compare", OKUMA).gecer)

    def test_salt_okuma_eylem_ucunda_403(self) -> None:
        for metot, yol in (("POST", "/refresh"), ("POST", "/summaries/build"),
                           ("POST", "/refresh/cancel/1"), ("DELETE", "/admin/banks")):
            with self.subTest(yol=yol):
                k = kimlik.karar_ver(self.acik, metot, yol, OKUMA)
                self.assertEqual(k.durum, 403)

    def test_salt_okuma_sorgu_uclarinda_gecer(self) -> None:
        """`POST /chat` ve `POST /extract` diske/ağa hiçbir eylem yapmaz."""
        for yol in sorted(kimlik.SALT_OKUMA_SORGU_YOLLARI):
            with self.subTest(yol=yol):
                self.assertTrue(kimlik.karar_ver(self.acik, "POST", yol, OKUMA).gecer)

    def test_izin_listesi_YASAK_listesi_DEGIL(self) -> None:
        """Listede olmayan yeni bir yazan uç kendiliğinden KAPALI başlar."""
        k = kimlik.karar_ver(self.acik, "POST", "/yarin-eklenen-uc", OKUMA)
        self.assertEqual(k.durum, 403)

    def test_eylem_olcutu_gunlukle_AYNI_kaynak(self) -> None:
        """"Yazan uç" tanımı tek yerden gelir; iki liste zamanla ayrışırdı."""
        from src.api.gunluk import YAZAN_METOTLAR
        for metot in sorted(YAZAN_METOTLAR):
            with self.subTest(metot=metot):
                self.assertTrue(kimlik.eylem_mi(metot, "/refresh"))
        self.assertFalse(kimlik.eylem_mi("GET", "/refresh"))


# --------------------------------------------------------------------------- #
# 3. Başlık okuma
# --------------------------------------------------------------------------- #
class TestAnahtarOku(unittest.TestCase):

    def test_x_api_key(self) -> None:
        self.assertEqual(kimlik.anahtar_oku({kimlik.BASLIK: f" {TAM} "}), TAM)

    def test_bearer_buyuk_kucuk_harf_duyarsiz(self) -> None:
        for onek in ("Bearer", "bearer", "BEARER"):
            with self.subTest(onek=onek):
                self.assertEqual(
                    kimlik.anahtar_oku({kimlik.BASLIK_YETKI: f"{onek} {TAM}"}), TAM)

    def test_bearer_disi_sema_yok_sayilir(self) -> None:
        self.assertIsNone(kimlik.anahtar_oku({kimlik.BASLIK_YETKI: f"Basic {TAM}"}))

    def test_baslik_yoksa_None(self) -> None:
        self.assertIsNone(kimlik.anahtar_oku({}))
        self.assertIsNone(kimlik.anahtar_oku({kimlik.BASLIK: "   "}))


# --------------------------------------------------------------------------- #
# 4. HTTP: geriye uyum — anahtar TANIMLI DEĞİLKEN hiçbir şey değişmez
# --------------------------------------------------------------------------- #
@requires_api
class TestGeriyeUyum(_OrtamKarantinasi):

    def test_anahtar_yokken_uclar_anahtarsiz_calisir(self) -> None:
        app = self._app()
        c = TestClient(app)
        for yol in ("/health", "/banks", "/stats", "/fields"):
            with self.subTest(yol=yol):
                self.assertEqual(c.get(yol).status_code, 200)

    def test_anahtar_yokken_depo_KAPALI_bildirir(self) -> None:
        app = self._app()
        self.assertFalse(app.state.kimlik.acik)

    def test_kapali_olmasi_ACILISTA_loglanir(self) -> None:
        """Sessiz güvensizlik yasak: kimse kapalı olduğunu bilmiyorsa kimse açmaz."""
        with self.assertLogs("src.api.kimlik", level=logging.WARNING) as kayit:
            self._app()
        birlesik = "\n".join(kayit.output)
        self.assertIn("KAPALI", birlesik)
        self.assertIn(kimlik.ORTAM_ANAHTARLAR, birlesik)


# --------------------------------------------------------------------------- #
# 5. HTTP: anahtar tanımlıyken kapı gerçekten kapanır
# --------------------------------------------------------------------------- #
@requires_api
class TestKapiHttp(_OrtamKarantinasi):

    def _client(self) -> TestClient:
        app = self._app(**{kimlik.ORTAM_ANAHTARLAR: TAM,
                           kimlik.ORTAM_SALT_OKUMA: OKUMA})
        return TestClient(app)

    def test_anahtarsiz_istek_401(self) -> None:
        c = self._client()
        yanit = c.get("/banks")
        self.assertEqual(yanit.status_code, 401)
        # Tarayıcı/istemci hangi şemayla yeniden denemesi gerektiğini görsün.
        self.assertEqual(yanit.headers.get("WWW-Authenticate"), "Bearer")

    def test_yanlis_anahtar_401(self) -> None:
        c = self._client()
        yanit = c.get("/banks", headers={kimlik.BASLIK: YANLIS})
        self.assertEqual(yanit.status_code, 401)
        # Cevap hangi anahtarın yanlış olduğunu SÖYLEMEZ.
        self.assertNotIn(YANLIS, yanit.text)
        self.assertNotIn(TAM, yanit.text)

    def test_dogru_anahtar_200(self) -> None:
        c = self._client()
        self.assertEqual(
            c.get("/banks", headers={kimlik.BASLIK: TAM}).status_code, 200)

    def test_bearer_semasi_da_kabul(self) -> None:
        c = self._client()
        yanit = c.get("/banks", headers={"Authorization": f"Bearer {TAM}"})
        self.assertEqual(yanit.status_code, 200)

    def test_health_ANAHTARSIZ_calisir(self) -> None:
        """Konteyner sağlık probu ağsız koşumda anahtar dağıtımı beklemiyor."""
        c = self._client()
        yanit = c.get("/health")
        self.assertEqual(yanit.status_code, 200)
        self.assertEqual(yanit.json()["status"], "ok")

    def test_salt_okuma_okuma_ucunda_200(self) -> None:
        c = self._client()
        self.assertEqual(
            c.get("/banks", headers={kimlik.BASLIK: OKUMA}).status_code, 200)

    def test_salt_okuma_yazma_ucunda_403(self) -> None:
        c = self._client()
        yanit = c.post("/refresh", json={"bank": "albaraka"},
                       headers={kimlik.BASLIK: OKUMA})
        self.assertEqual(yanit.status_code, 403)

    def test_tam_anahtar_yazma_ucunda_403_ALMAZ(self) -> None:
        """403'ün sebebi ROL olmalı, ucun kendisi değil."""
        c = self._client()
        yanit = c.post("/summaries/build", json={},
                       headers={kimlik.BASLIK: TAM})
        self.assertNotIn(yanit.status_code, (401, 403))

    def test_401_yaniti_CORS_basligi_tasir(self) -> None:
        """Kimlik ara katmanı CORS'un İÇİNDE: tarayıcı gerçek durum kodunu görsün."""
        c = self._client()
        yanit = c.get("/banks", headers={"Origin": "http://localhost:3000"})
        self.assertEqual(yanit.status_code, 401)
        self.assertIn("access-control-allow-origin", {k.lower() for k in yanit.headers})


# --------------------------------------------------------------------------- #
# 6. Anahtar HİÇBİR yere sızmaz
# --------------------------------------------------------------------------- #
@requires_api
class TestAnahtarSizmaz(_OrtamKarantinasi):

    def setUp(self) -> None:
        super().setUp()
        self._tmp = tempfile.TemporaryDirectory(prefix="anatolia-kimlik-")
        self._gunluk_onceki = os.environ.get("AUDIT_LOG_PATH")
        self.gunluk_yolu = Path(self._tmp.name) / "islem-gunlugu.jsonl"
        os.environ["AUDIT_LOG_PATH"] = str(self.gunluk_yolu)

    def tearDown(self) -> None:
        if self._gunluk_onceki is None:
            os.environ.pop("AUDIT_LOG_PATH", None)
        else:
            os.environ["AUDIT_LOG_PATH"] = self._gunluk_onceki
        self._tmp.cleanup()
        super().tearDown()

    def test_uygulama_logunda_anahtar_YOK(self) -> None:
        """Açılış log'u sayı verir, anahtar vermez; reddedilen istek de öyle."""
        with self.assertLogs("src.api.kimlik", level=logging.DEBUG) as kayit:
            app = self._app(**{kimlik.ORTAM_ANAHTARLAR: TAM,
                               kimlik.ORTAM_SALT_OKUMA: OKUMA})
            c = TestClient(app)
            c.get("/banks")                                  # 401
            c.get("/banks", headers={kimlik.BASLIK: YANLIS})  # 401
            c.get("/banks", headers={kimlik.BASLIK: TAM})     # 200
            c.post("/refresh", json={"bank": "albaraka"},
                   headers={kimlik.BASLIK: OKUMA})            # 403
        birlesik = "\n".join(kayit.output)
        for sir in (TAM, OKUMA, YANLIS):
            self.assertNotIn(sir, birlesik)
        # Reddin KENDİSİ log'lanır — sessiz kalmak da kabul değil.
        self.assertIn("Kimlik reddi", birlesik)

    def test_islem_gunlugunde_anahtar_YOK_ama_REDDEDILEN_ISTEK_VAR(self) -> None:
        """Denetim kaydı reddi görmeli; anahtarı ASLA görmemeli."""
        app = self._app(**{kimlik.ORTAM_ANAHTARLAR: TAM})
        c = TestClient(app)
        c.get("/banks", headers={kimlik.BASLIK: YANLIS})
        c.get("/banks", headers={kimlik.BASLIK: TAM})
        ham = self.gunluk_yolu.read_text(encoding="utf-8")
        for sir in (TAM, YANLIS):
            self.assertNotIn(sir, ham)
        kayitlar = [json.loads(s) for s in ham.splitlines() if s.strip()]
        durumlar = [k.get("durum") for k in kayitlar if k.get("yol") == "/banks"]
        self.assertIn(401, durumlar, "reddedilen istek denetim kaydına düşmedi")
        self.assertIn(200, durumlar)


if __name__ == "__main__":
    unittest.main()
