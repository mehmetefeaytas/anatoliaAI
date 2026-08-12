"""«LLM ile özet üret» düğmesinin arkasındaki uçlar ve iş yöneticisi.

İlgili: ../src/summarize/ozet_isi.py, ../src/api/main.py (`/summaries/*`)
        ../web/app/components/SummaryCoverage.tsx

## Bu testlerin varlık sebebi

Düğme veri tabanına YAZAN, dakikalarca süren, arka planda koşan bir iş
başlatıyor. Üç davranışı sessizce bozulabilir ve üçü de demoda görünür:

1. **LLM kapalıyken iş başlamamalı.** Başlasaydı her belgeye `llm_kapali`
   sebebi yazılır, korpus sistemin geçici bir durumuyla kirlenir ve sonraki
   koşu o belgeleri "denenmiş" sayardı. Sahte özet yasağının (`ozet.py`)
   toplu üretimdeki karşılığı budur.
2. **Aynı anda iki iş koşmamalı.** İki iş aynı hedef kümesini hesaplayıp aynı
   belgeleri iki kez modele gönderirdi — iki kat süre, aynı sonuç.
3. **İptal, o ana kadar üretilmiş özetleri KORUMALI.** Aksi hâlde "durdur"a
   basmak dakikalarca süren bir üretimi çöpe atardı.

Yerel model çağrılmıyor: `llm_ver` ile sahte bir çıkarıcı geçiliyor. Testin
ölçtüğü şey modelin kalitesi değil, işin sözleşmesi.
"""

from __future__ import annotations

import sys
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# fastapi yardımcı içinde import ediliyordu: modül yüklenir ama testler HATA
# verir, atlanmaz. 12 Ağu CI koşusunda bu dosya 3 hata üretti. Koruma yalnız
# `TestUclar`a konur — `TestLlmKapali` ve `TestUretim` sahte istemciyle koşar
# ve bağımlılıksız koşuda KOŞMAYA DEVAM ETMELİ.
# Desen: `test_api_startup.py:37-41`.
try:  # pragma: no cover - ortama bağlı
    import fastapi  # noqa: F401
    FASTAPI_VAR = True
except (ImportError, RuntimeError):  # pragma: no cover
    # RuntimeError de yakalanır: starlette 1.6 `TestClient` için `httpx2`
    # istiyor ve yokluğunda ModuleNotFoundError DEĞİL RuntimeError atıyor
    # ("The starlette.testclient module requires the httpx2 package").
    # 12 Ağu CI koşusu 31642385024 tam buna düştü: fastapi kuruluydu,
    # test istemcisinin bağımlılığı değildi ve koruma ATLAMA yerine
    # HATA üretti. Test aracının yokluğu, sınanan kodun kusuru değildir.
    FASTAPI_VAR = False

from src.db.repository import Repository
from src.schemas import Campaign
from src.summarize.ozet_isi import (
    DURUM_IPTAL,
    DURUM_TAMAM,
    LlmKapali,
    OzetMesgul,
    OzetYoneticisi,
)


class _SahteIstemci:
    """`llm.client.generate_json()` yüzeyi — modelin çağrıldığı tek nokta."""

    def __init__(self, sahip: "_SahteLlm") -> None:
        self._sahip = sahip

    def generate_json(self, *a, **k):
        self._sahip.cagri += 1
        if self._sahip.gecikme:
            time.sleep(self._sahip.gecikme)
        return {"ozet": self._sahip.ozet}


class _SahteLlm:
    """`llm_hazir()` açık sayar ve her belge için sabit bir özet döndürür.

    `llm_hazir` iki şeye birden bakar: `available` doğru VE `client` `None`
    değil. Sahte nesne ikisini de taşımak zorunda; yalnız `available=True`
    veren bir nesne gerçek kapıdan geçemezdi ve test yanlış şeyi ölçerdi.

    `gecikme` iptal testinin işi koşarken yakalayabilmesi için var: gerçek
    model belge başına saniyeler harcıyor, sahte model mikrosaniyede biterdi
    ve iptal hiç ateşlenemezdi.
    """

    def __init__(self, gecikme: float = 0.0,
                 ozet: str = "Kısa Türkçe özet.") -> None:
        self.gecikme = gecikme
        self.ozet = ozet
        self.cagri = 0
        self.available = True
        self.client = _SahteIstemci(self)


class _KapaliLlm:
    """`default_extractor()`ın LLM kapalıyken döndürdüğü nesnenin şekli."""

    available = False
    client = None


def _depo(adet: int = 6) -> Repository:
    repo = Repository(":memory:", check_same_thread=False)
    repo.upsert_bank("Örnek Katılım", "ornek")
    for i in range(adet):
        repo.insert_campaign(Campaign(
            bank_slug="ornek",
            raw_text=(f"{i} numaralı konut finansmanı kampanyası. Kâr payı "
                      "oranı %2,05'ten başlar ve vade 120 aya kadardır."),
            source_url=f"https://ornek.test/kampanya-{i}"))
    return repo


def _bitene_kadar(yon: OzetYoneticisi, is_id: str, azami_sn: float = 10.0) -> dict:
    son = time.time() + azami_sn
    while time.time() < son:
        kayit = yon.durum(is_id)
        assert kayit is not None
        if kayit["bitti"]:
            return kayit
        time.sleep(0.02)
    raise AssertionError(f"iş {azami_sn} sn içinde bitmedi: {yon.durum(is_id)}")


class TestLlmKapali(unittest.TestCase):
    def test_llm_kapaliyken_is_BASLAMAZ(self) -> None:
        repo = _depo(3)
        try:
            yon = OzetYoneticisi(lambda: repo, llm_ver=_KapaliLlm)
            with self.assertRaises(LlmKapali):
                yon.baslat()
            # Ve korpus kirlenmemiş olmalı: hiçbir belgeye sebep yazılmadı.
            self.assertTrue(all(c["ozet_sebep"] is None
                                for c in repo.all_campaigns()))
        finally:
            repo.close()

    def test_sayim_llm_durumunu_ve_gerekcesini_TASIR(self) -> None:
        repo = _depo(3)
        try:
            yon = OzetYoneticisi(lambda: repo, llm_ver=_KapaliLlm)
            s = yon.sayim()
            self.assertFalse(s["llm_acik"])
            self.assertTrue(s["llm_notu"],
                            "kapalıyken ekranda gösterilecek gerekçe olmalı")
        finally:
            repo.close()


class TestUretim(unittest.TestCase):
    def test_ozetler_uretilip_YAZILIYOR(self) -> None:
        repo = _depo(4)
        try:
            yon = OzetYoneticisi(lambda: repo, llm_ver=_SahteLlm)
            is_id = yon.baslat()["is_id"]
            kayit = _bitene_kadar(yon, is_id)
            self.assertEqual(kayit["durum"], DURUM_TAMAM)
            self.assertEqual(kayit["uretilen"], 4)
            self.assertEqual(
                sum(1 for c in repo.all_campaigns() if (c["ozet"] or "").strip()),
                4)
        finally:
            repo.close()

    def test_ikinci_kosu_HEDEF_BULAMAZ(self) -> None:
        """`devam=True` olduğu için özetlenmiş belge tekrar işlenmez."""
        repo = _depo(3)
        try:
            llm = _SahteLlm()
            yon = OzetYoneticisi(lambda: repo, llm_ver=lambda: llm)
            _bitene_kadar(yon, yon.baslat()["is_id"])
            ilk_cagri = llm.cagri
            _bitene_kadar(yon, yon.baslat()["is_id"])
            self.assertEqual(llm.cagri, ilk_cagri,
                             "özetlenmiş belgeler modele TEKRAR gönderilmemeli")
        finally:
            repo.close()

    def test_ayni_anda_ikinci_is_REDDEDILIR(self) -> None:
        repo = _depo(8)
        try:
            yon = OzetYoneticisi(lambda: repo,
                                 llm_ver=lambda: _SahteLlm(gecikme=0.05))
            is_id = yon.baslat()["is_id"]
            with self.assertRaises(OzetMesgul):
                yon.baslat()
            _bitene_kadar(yon, is_id)
        finally:
            repo.close()

    def test_iptal_o_ana_kadarki_ozetleri_KORUR(self) -> None:
        """Durdurmak veri kaybı OLMAMALI.

        `parca` varsayılanı 25 olduğu için 20 belgelik bir koşuda ara yazma
        hiç gerçekleşmez; korunan özetler döngü kırıldıktan SONRA yazılan
        bekleyen parçadan gelir (bkz. `toplu.calistir` içindeki `bosalt()`).

        Sabit bir `sleep` ile beklenMEZ: yüklü bir makinede iş hiç ilerlemeden
        iptal edilir (o zaman "hiçbir şey korunmadı" diye düşer), boş bir
        makinede ise 20 belge bitip iptal hiç ateşlenmez. İki yönde de test
        kendi zamanlamasını ölçmüş olurdu, davranışı değil. Koşula bağlanır:
        ilk iki belge işlenene kadar bekle, sonra durdur.
        """
        repo = _depo(20)
        try:
            yon = OzetYoneticisi(lambda: repo,
                                 llm_ver=lambda: _SahteLlm(gecikme=0.02))
            is_id = yon.baslat()["is_id"]
            son = time.time() + 10.0
            while time.time() < son:
                kayit = yon.durum(is_id) or {}
                if kayit.get("islenen", 0) >= 2 or kayit.get("bitti"):
                    break
                time.sleep(0.01)
            self.assertFalse((yon.durum(is_id) or {}).get("bitti"),
                             "iş, iptal edilemeden bitti — testin ölçtüğü "
                             "davranışa hiç sıra gelmedi")
            yon.iptal_et(is_id)
            kayit = _bitene_kadar(yon, is_id)
            self.assertEqual(kayit["durum"], DURUM_IPTAL)
            yazilan = sum(1 for c in repo.all_campaigns()
                          if (c["ozet"] or "").strip())
            self.assertGreater(yazilan, 0,
                               "iptal, üretilmiş özetleri ÇÖPE ATMAMALI")
            self.assertLess(yazilan, 20, "iptal gerçekten durdurmalıydı")
        finally:
            repo.close()

    def test_uretilemeyen_belgeye_SEBEP_yaziliyor(self) -> None:
        """Model boş dönerse belge "denenmiş" olarak işaretlenmeli."""
        repo = _depo(3)
        try:
            yon = OzetYoneticisi(lambda: repo,
                                 llm_ver=lambda: _SahteLlm(ozet=""))
            _bitene_kadar(yon, yon.baslat()["is_id"])
            kayitlar = repo.all_campaigns()
            self.assertTrue(all(not (c["ozet"] or "").strip() for c in kayitlar))
            self.assertTrue(all(c["ozet_sebep"] for c in kayitlar),
                            "üretilemeyen her belgeye sebep YAZILMALI")
        finally:
            repo.close()


@unittest.skipUnless(FASTAPI_VAR, "fastapi kurulu değil — API testi atlanıyor")
class TestUclar(unittest.TestCase):
    """HTTP yüzeyi — durum kodları sözleşmenin parçası.

    Kendi geçici veri tabanını kurar ve `DATABASE_PATH`i AÇIKÇA yazar.
    `os.environ.setdefault(..., "data/demo.db")` denenmişti ve tam suit
    koşusunda düştü: başka bir test değişkeni kendi geçici dizinine
    ayarlıyor, `setdefault` dolu değişkeni ezmiyor ve o dizin temizlenmiş
    olduğu için `unable to open database file` geliyordu. Test kendi
    kurulumunu başka bir testin artığına dayandıramaz.
    """

    def setUp(self) -> None:
        import os
        import tempfile

        self._tmp = tempfile.TemporaryDirectory()
        self.db = Path(self._tmp.name) / "t.db"
        repo = Repository(str(self.db))
        repo.upsert_bank("Örnek Katılım", "ornek")
        repo.insert_campaign(Campaign(
            bank_slug="ornek",
            raw_text="Konut finansmanı kampanyası. Kâr payı oranı %2,05.",
            source_url="https://ornek.test/kampanya"))
        repo.close()
        self._eski = os.environ.get("DATABASE_PATH")
        os.environ["DATABASE_PATH"] = str(self.db)

    def tearDown(self) -> None:
        import os

        if self._eski is None:
            os.environ.pop("DATABASE_PATH", None)
        else:
            os.environ["DATABASE_PATH"] = self._eski
        self._tmp.cleanup()

    def _istemci(self):
        import importlib

        from fastapi.testclient import TestClient

        from src.api import main as M
        # `DB_PATH` modül düzeyinde, İÇE AKTARMA anında okunuyor. Ortam
        # değişkenini setUp'ta yazmak yetmez: modül zaten yüklüyse eski yolu
        # taşır — ve o yol başka bir testin temizlenmiş geçici dizini olabilir.
        importlib.reload(M)
        return TestClient(M.build_app())

    def test_coverage_dort_kova_dondurur(self) -> None:
        c = self._istemci()
        y = c.get("/summaries/coverage")
        self.assertEqual(y.status_code, 200)
        veri = y.json()
        for alan in ("toplam", "ozetli", "icerik_yok", "basarisiz",
                     "denenmemis", "hedef", "llm_acik"):
            self.assertIn(alan, veri)
        self.assertEqual(
            veri["ozetli"] + veri["icerik_yok"] + veri["basarisiz"]
            + veri["denenmemis"], veri["toplam"])

    def test_llm_kapaliyken_build_503(self) -> None:
        """Testler LLM'siz koşuyor; uç sahte bir 202 DÖNDÜRMEMELİ."""
        c = self._istemci()
        if c.get("/summaries/coverage").json()["llm_acik"]:
            self.skipTest("bu makinede LLM açık; kapalı dal sınanamaz")
        y = c.post("/summaries/build")
        self.assertEqual(y.status_code, 503)
        self.assertIn("özet", y.json()["detail"].lower())

    def test_bilinmeyen_is_404(self) -> None:
        c = self._istemci()
        self.assertEqual(c.get("/summaries/status/yokboyle").status_code, 404)
        self.assertEqual(c.post("/summaries/cancel/yokboyle").status_code, 404)


if __name__ == "__main__":
    unittest.main()
