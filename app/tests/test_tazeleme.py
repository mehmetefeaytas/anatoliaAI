"""Tazeleme işi — ağa ÇIKMADAN, sahte çekiciyle.

İlgili: ../src/scraping/tazeleme.py, ../src/scraping/collector.py

## Bu dosyanın koruduğu değişmezler

1. **Kritik yol çevrimdışı kalır.** Tazeleme yalnız `data/raw` altına yazar;
   veri tabanı katmanını içe bile aktarmaz. Aşağı akışa tek bağ enjekte
   edilen `alt_akis` geri çağrısıdır ve YALNIZ metni değişen belgeler için
   koşar — değişmeyen belgeye dokunulmaz.
2. **Etik kısıtlar gevşetilemez.** robots.txt denetimini kapatan bir yol
   yoktur; gecikme 2–5 saniye aralığına kırpılır; User-Agent açıklayıcıdır;
   her belge provenance sidecar'ıyla yazılır.
3. **Yarıda kesilme yarım belge bırakmaz.** İptal edilen iş diske hiçbir şey
   yazmaz — çekim evresi tamamen bellekte biter.
4. **Sonuç sayıları anlamlı.** "Değişen" ham bayt farkıyla değil, temiz metin
   farkıyla ölçülür; aksi halde her tazeleme "hepsi değişti" derdi.

Hiçbir test ağ kullanmaz: `StaticFetcher` yerine elden yazılmış bir sahte
çekici, `RobotsCache` yerine enjekte edilmiş bir robots.txt gövdesi konur.
"""

from __future__ import annotations

import json
import sys
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.scraping.collector import LIVE_SUBDIR
from src.scraping.config import BankConfig
from src.scraping.fetcher import FetcherBundle, FetchResult
from src.scraping.robots import RobotsCache
from src.scraping.tazeleme import (
    BELGE_AYNI,
    BELGE_DEGISEN,
    BELGE_YENI,
    DURUM_HATA,
    DURUM_IPTAL,
    DURUM_TAMAM,
    GECIKME_ALT_SN,
    GECIKME_UST_SN,
    VARSAYILAN_AZAMI_BELGE,
    TazelemeDurumu,
    TazelemeMesgul,
    TazelemeYoneticisi,
    gecikmeyi_kirp,
    onizleme,
    son_tazeleme_oku,
    son_tazeleme_yaz,
    tazele,
)

BANKA = BankConfig(
    slug="ornek-katilim",
    name="Örnek Katılım",
    website_url="https://ornek.example",
    campaign_paths=["/kampanyalar"],
    detail_patterns=["kampanya"],
    max_docs=10,
)


def _sayfa(baslik: str, govde: str) -> str:
    """Kabul eşiğini (200 karakter) geçen küçük bir kampanya sayfası."""
    return (
        f"<html><head><title>{baslik}</title></head><body><main>"
        f"<h1>{baslik}</h1><p>{govde}</p>"
        "<p>Katılım bankacılığı kampanya metni. Kâr payı oranı ve vade "
        "bilgileri bu sayfada yayımlanır. Tahsis ücreti ve masraf durumu "
        "kampanya koşullarına göre değişebilir. Başvuru şartları için "
        "şubelerimize danışabilirsiniz. Kampanya süresi sınırlıdır.</p>"
        "</main></body></html>"
    )


LISTE = (
    "<html><body>"
    "<a href='/kampanyalar/kampanya-bir'>Bir</a>"
    "<a href='/kampanyalar/kampanya-iki'>İki</a>"
    "</body></html>"
)


class SahteCekici:
    """`StaticFetcher` yerine geçen, ağa çıkmayan çekici.

    `available` her zaman True; `fetch` yalnızca sözlükte tanımlı adresleri
    döndürür, gerisi bağlantı hatası verir — "site erişilemedi" yolunu da
    test edebilmek için.
    """

    method = "live"

    def __init__(self, sayfalar: dict[str, str], *,
                 hepsi_dussun: bool = False) -> None:
        self.sayfalar = sayfalar
        self.hepsi_dussun = hepsi_dussun
        self.istekler: list[str] = []
        self.available = True

    def fetch(self, url: str) -> FetchResult:
        self.istekler.append(url)
        if self.hepsi_dussun:
            return FetchResult(url, error="ConnectionError: ag yok",
                               method=self.method)
        html = self.sayfalar.get(url)
        if html is None:
            return FetchResult(url, status=404, method=self.method)
        return FetchResult(url, status=200, html=html, method=self.method,
                           final_url=url)

    def close(self) -> None:
        pass


def _bundle(cekici: SahteCekici) -> FetcherBundle:
    """Sahte çekiciyi hem statik hem tarayıcı yuvasına koyar."""
    return FetcherBundle(static=cekici, browser=cekici)  # type: ignore[arg-type]


def _robots(govde: str = "User-agent: *\nAllow: /\n") -> RobotsCache:
    """robots.txt gövdesi enjekte edilmiş önbellek — ağ yok."""
    return RobotsCache(fetcher=lambda url: (200, govde))


def _iki_sayfali() -> SahteCekici:
    return SahteCekici({
        "https://ornek.example/kampanyalar": LISTE,
        "https://ornek.example/kampanyalar/kampanya-bir":
            _sayfa("Konut Finansmanı", "Kâr payı oranı %1,89."),
        "https://ornek.example/kampanyalar/kampanya-iki":
            _sayfa("Taşıt Finansmanı", "Vade 48 aya kadar."),
    })


class TestOnizleme(unittest.TestCase):
    """Ön izleme AĞA ÇIKMAZ ve ne olacağını önceden söyler."""

    def test_onizleme_ag_kullanmadan_tahmin_verir(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            bilgi = onizleme(BANKA, raw_dir=tmp, azami_belge=25)
        self.assertTrue(bilgi["internet_gerekir"])
        self.assertTrue(bilgi["robots_uyumu"])
        self.assertGreater(bilgi["tahmini_istek_ust"], bilgi["tahmini_istek_alt"])
        self.assertGreater(bilgi["tahmini_sure_ust_sn"], 0)
        self.assertIn("AnatoliaAI", bilgi["user_agent"])

    def test_onizleme_veri_tabani_etkisini_dogru_soyler(self) -> None:
        """Bu beklenti 2026-08-13'te `False`'tan `True`'ya DÖNDÜ.

        Beklenti değişti çünkü DAVRANIŞ değişti: tazeleme artık bittiğinde
        metni değişen belgelerin bayat AI özetini düşürüyor
        (`src/tazeleme_sonrasi.py`). `False` bırakmak, ön izlemeyi — yani
        "basmadan önce ne olacak" sorusunun tek cevabını — yalancı yapardı.

        Bayrağın tek başına verdiği izlenim ("veri tabanı yeniden kuruluyor")
        yanlış olacağı için kapsamı taşıyan cümle de aranıyor.
        """
        with tempfile.TemporaryDirectory() as tmp:
            bilgi = onizleme(BANKA, raw_dir=tmp)
        self.assertTrue(bilgi["veri_tabani_etkilenir"])
        self.assertIn("özet", bilgi["veri_tabani_etkisi"])
        self.assertIn("DEĞİŞEN", bilgi["veri_tabani_etkisi"])

    def test_azami_belge_varsayilani_otuz_bes(self) -> None:
        """Sınır 25 → 35: ölçülmüş süreye dayanır, tahmine değil.

        25 URL'lik gerçek koşu ~90 sn sürdü (belge başına ~3,6 sn); 35 belge
        aynı hızda ~2 dakikadır, yani sabitin gerekçesi ("operatör eylemi
        dakikalar sürmeli, saatler değil") hâlâ karşılanıyor.

        Ön izlemedeki istek üst sınırı sabiti TAKİP ETMELİ: iki sayı ayrışırsa
        operatöre söylenen süre ile gerçekte atılan istek sayısı ayrışır.
        """
        self.assertEqual(VARSAYILAN_AZAMI_BELGE, 35)
        with tempfile.TemporaryDirectory() as tmp:
            bilgi = onizleme(BANKA, raw_dir=tmp)
        self.assertEqual(bilgi["azami_belge"], 35)
        giris = len(BANKA.campaign_paths) + len(BANKA.sitemap_urls)
        self.assertEqual(bilgi["tahmini_istek_ust"], 1 + giris + 35)

    def test_onizleme_arsivdeki_belgeyi_sayar(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            hedef = Path(tmp) / BANKA.slug / LIVE_SUBDIR
            hedef.mkdir(parents=True)
            (hedef / "a.txt").write_text("x", encoding="utf-8")
            (hedef / "b.txt").write_text("y", encoding="utf-8")
            self.assertEqual(onizleme(BANKA, raw_dir=tmp)["arsivdeki_belge"], 2)


class TestGecikmeKirpma(unittest.TestCase):
    """Alan başına gecikme etik aralığın DIŞINA çıkarılamaz."""

    def test_alt_sinira_kirpilir(self) -> None:
        self.assertEqual(gecikmeyi_kirp(0.0), GECIKME_ALT_SN)
        self.assertEqual(gecikmeyi_kirp(-5), GECIKME_ALT_SN)

    def test_ust_sinira_kirpilir(self) -> None:
        self.assertEqual(gecikmeyi_kirp(60), GECIKME_UST_SN)

    def test_aradaki_deger_korunur(self) -> None:
        self.assertEqual(gecikmeyi_kirp(3.0), 3.0)


class TestTazeleAkisi(unittest.TestCase):
    """Çek → karşılaştır → yaz akışı, sahte çekiciyle."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.raw = self._tmp.name

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _kos(self, cekici: SahteCekici, **kwargs) -> TazelemeDurumu:
        durum = TazelemeDurumu(is_id="t1", bank=BANKA.slug, bank_name=BANKA.name)
        # `son_tazeleme_kok` GEÇİCİ dizine sabitlenir: yoksa `tazele()` TAMAM
        # olan her koşuda gerçek depo kökündeki `data/son-tazeleme.json`'a
        # yazardı ve test koşusu gerçek dosyayı kirletirdi.
        kwargs.setdefault("son_tazeleme_kok", Path(self.raw))
        return tazele(BANKA, self.raw, durum, bundle=_bundle(cekici),
                      robots=_robots(), **kwargs)

    def test_ilk_kosu_hepsi_yeni_ve_provenance_yazilir(self) -> None:
        durum = self._kos(_iki_sayfali())
        self.assertEqual(durum.durum, DURUM_TAMAM)
        self.assertEqual(durum.cekilen, 2)
        self.assertEqual(durum.yeni, 2)
        self.assertEqual(durum.degisen, 0)
        self.assertEqual(durum.ayni, 0)

        hedef = Path(self.raw) / BANKA.slug / LIVE_SUBDIR
        metinler = sorted(hedef.glob("*.txt"))
        self.assertEqual(len(metinler), 2)
        # Provenance: ham HTML + zaman damgası + kaynak adresi + özet
        for txt in metinler:
            meta = json.loads(
                (hedef / f"{txt.stem}.txt.meta.json").read_text(encoding="utf-8"))
            self.assertTrue(meta["source_url"].startswith("https://ornek.example"))
            self.assertTrue(meta["scraped_at"])
            self.assertTrue(meta["content_hash"])
            self.assertTrue((hedef / f"{txt.stem}.html").is_file(),
                            "ham HTML saklanmadı — provenance eksik")

    def test_ikinci_kosuda_degismemis_belge_ayni_sayilir(self) -> None:
        self._kos(_iki_sayfali())
        durum = self._kos(_iki_sayfali())
        self.assertEqual(durum.ayni, 2)
        self.assertEqual(durum.yeni, 0)
        self.assertEqual(durum.degisen, 0)

    def test_metin_degisince_degisen_sayilir(self) -> None:
        self._kos(_iki_sayfali())
        yeni = _iki_sayfali()
        yeni.sayfalar["https://ornek.example/kampanyalar/kampanya-bir"] = _sayfa(
            "Konut Finansmanı", "Kâr payı oranı %1,59 olarak güncellendi.")
        durum = self._kos(yeni)
        self.assertEqual(durum.degisen, 1)
        self.assertEqual(durum.ayni, 1)
        self.assertEqual(durum.yeni, 0)

    def test_ham_bayt_gurultusu_degisiklik_sayilmaz(self) -> None:
        """Oturum simgesi değişince belge "değişti" DENMEZ.

        Bu testin varlık sebebi ölçülmüş bir davranış: ham HTML her istekte
        farklı analitik kimliği taşır. Karşılaştırma ham bayt özetiyle
        yapılsaydı her tazeleme "hepsi değişti" derdi ve sayı hiçbir şey
        anlatmazdı.
        """
        self._kos(_iki_sayfali())
        gurultulu = _iki_sayfali()
        for url, html in list(gurultulu.sayfalar.items()):
            gurultulu.sayfalar[url] = html.replace(
                "<body>", "<body><script>var oturum='%s';</script>" % time.time())
        durum = self._kos(gurultulu)
        self.assertEqual(durum.degisen, 0,
                         "betik gürültüsü içerik değişikliği sayıldı")
        self.assertEqual(durum.ayni, 2)

    def test_robots_disallow_belgeyi_engeller_ve_raporlanir(self) -> None:
        cekici = _iki_sayfali()
        durum = TazelemeDurumu(is_id="t1", bank=BANKA.slug, bank_name=BANKA.name)
        tazele(BANKA, self.raw, durum, bundle=_bundle(cekici),
               robots=_robots("User-agent: *\nDisallow: /kampanyalar\n"))
        self.assertEqual(durum.cekilen, 0)
        self.assertTrue(durum.hatalar)
        self.assertTrue(all(h["reason"] == "robots disallow" for h in durum.hatalar))
        # Yasaklı sayfa HİÇ istenmemiş olmalı
        self.assertEqual(cekici.istekler, [])

    def test_ag_yoksa_acik_hata_verir_kritik_yol_bozulmaz(self) -> None:
        durum = self._kos(SahteCekici({}, hepsi_dussun=True))
        self.assertEqual(durum.durum, DURUM_HATA)
        self.assertIn("Ağ bağlantısı kurulamadı", durum.mesaj or "")
        # Hiçbir dosya yazılmadı
        hedef = Path(self.raw) / BANKA.slug / LIVE_SUBDIR
        self.assertFalse(list(hedef.glob("*.txt")) if hedef.is_dir() else [])

    def test_iptal_hicbir_sey_yazmaz(self) -> None:
        durum = self._kos(_iki_sayfali(), iptal=lambda: True)
        self.assertEqual(durum.durum, DURUM_IPTAL)
        self.assertEqual(durum.yazilan_dosya, 0)
        hedef = Path(self.raw) / BANKA.slug / LIVE_SUBDIR
        self.assertFalse(hedef.is_dir() and list(hedef.glob("*.txt")),
                         "iptal edilen iş ham arşive yazdı")

    def test_belge_listesi_durum_tasir(self) -> None:
        durum = self._kos(_iki_sayfali())
        durumlar = {b["durum"] for b in durum.belgeler}
        self.assertEqual(durumlar, {BELGE_YENI})
        self.assertTrue(all(b["source_url"] for b in durum.belgeler))
        for b in durum.belgeler:
            self.assertIn(b["durum"], (BELGE_YENI, BELGE_DEGISEN, BELGE_AYNI))


class TestAltAkis(unittest.TestCase):
    """Alt akış geri çağrısı — YALNIZ metni değişen belge için koşar.

    Kural: değişmeyen belgeye dokunulmaz. Geri çağrı aşağı akışta veri tabanı
    yazıyor (`src/tazeleme_sonrasi.py`); gereksiz tetiklenmesi, hiç değişmemiş
    bir belgenin sağlam özetini düşürmek demekti.
    """

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.raw = self._tmp.name
        self.cagrilar: list[list[dict]] = []

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _hook(self, degisenler):
        self.cagrilar.append(degisenler)
        return {"gecersizlenen_ozet": len(degisenler),
                "mesaj": "Sahte alt akış koştu."}

    def _kos(self, cekici: SahteCekici, alt_akis=None, **kwargs) -> TazelemeDurumu:
        durum = TazelemeDurumu(is_id="t1", bank=BANKA.slug, bank_name=BANKA.name)
        # Bkz. `TestTazeleAkisi._kos`: gerçek depo köküne yazmayı önler.
        kwargs.setdefault("son_tazeleme_kok", Path(self.raw))
        return tazele(BANKA, self.raw, durum, bundle=_bundle(cekici),
                      robots=_robots(),
                      alt_akis=self._hook if alt_akis is None else alt_akis,
                      **kwargs)

    def test_yeni_ve_ayni_belgeler_alt_akisi_tetiklemez(self) -> None:
        ilk = self._kos(_iki_sayfali())
        self.assertEqual(ilk.yeni, 2)
        self.assertEqual(self.cagrilar, [], "yeni belge alt akışı tetikledi")
        ikinci = self._kos(_iki_sayfali())
        self.assertEqual(ikinci.ayni, 2)
        self.assertEqual(self.cagrilar, [],
                         "değişmeyen belge alt akışı tetikledi")
        self.assertIsNone(ikinci.alt_akis)

    def test_degisen_belge_onceki_metniyle_gecer(self) -> None:
        self._kos(_iki_sayfali())
        yeni = _iki_sayfali()
        url = "https://ornek.example/kampanyalar/kampanya-bir"
        yeni.sayfalar[url] = _sayfa("Konut Finansmanı",
                                    "Kâr payı oranı %1,59 olarak güncellendi.")
        durum = self._kos(yeni)
        self.assertEqual(len(self.cagrilar), 1)
        kayitlar = self.cagrilar[0]
        self.assertEqual([k["source_url"] for k in kayitlar], [url],
                         "yalnız değişen belge geçmeliydi")
        # ÖNCEKİ metin şart: veri tabanındaki doğru satırı bulmanın anahtarı o.
        self.assertIn("%1,89", kayitlar[0]["onceki_metin"])
        self.assertNotIn("%1,59", kayitlar[0]["onceki_metin"])
        self.assertEqual(durum.alt_akis["gecersizlenen_ozet"], 1)
        self.assertIn("Sahte alt akış koştu.", durum.mesaj or "")

    def test_belge_raporu_ham_metin_tasimaz(self) -> None:
        """Durum uçları 1,5 sn'de bir sorgulanıyor; ham metin oraya girmez."""
        self._kos(_iki_sayfali())
        yeni = _iki_sayfali()
        yeni.sayfalar["https://ornek.example/kampanyalar/kampanya-bir"] = _sayfa(
            "Konut Finansmanı", "Kâr payı oranı %1,59 olarak güncellendi.")
        durum = self._kos(yeni)
        for b in durum.to_dict()["belgeler"]:
            self.assertNotIn("onceki_metin", b)

    def test_iptal_alt_akisi_tetiklemez(self) -> None:
        self._kos(_iki_sayfali(), iptal=lambda: True)
        self.assertEqual(self.cagrilar, [])

    def test_alt_akis_dusse_tazeleme_hataya_donmez(self) -> None:
        """Ham arşiv doğru yazıldı; işi HATA göstermek olmayan bir kaybı haber
        vermek olurdu. Ama sessiz de kalınmaz: not düşülür."""
        self._kos(_iki_sayfali())
        yeni = _iki_sayfali()
        yeni.sayfalar["https://ornek.example/kampanyalar/kampanya-bir"] = _sayfa(
            "Konut Finansmanı", "Kâr payı oranı %1,59 olarak güncellendi.")

        def patlayan(_degisenler):
            raise RuntimeError("depo kapalı")

        durum = self._kos(yeni, alt_akis=patlayan)
        self.assertEqual(durum.durum, DURUM_TAMAM)
        self.assertGreater(durum.yazilan_dosya, 0)
        self.assertIsNone(durum.alt_akis)
        self.assertTrue(any("geçersizlenemedi" in n for n in durum.notlar),
                        f"alt akış düşüşü sessiz kaldı: {durum.notlar}")


class TestVeriTabaniDokunulmaz(unittest.TestCase):
    """Tazeleme modülü veri tabanı katmanını HİÇ tanımaz.

    Denetim `ast` ile yapılır, düz metin aramasıyla değil: modül başlığı
    veri tabanına NEDEN dokunulmadığını anlatıyor ve o açıklamanın kendisi
    testi kırmamalı.
    """

    def _agac(self):
        import ast
        return ast.parse(
            (ROOT / "src" / "scraping" / "tazeleme.py").read_text(encoding="utf-8"))

    def test_modul_depo_katmanini_ice_aktarmaz(self) -> None:
        import ast
        yasak = ("sqlite3", "psycopg", "db", "db.repository", "db.factory")
        ithal: list[str] = []
        for d in ast.walk(self._agac()):
            if isinstance(d, ast.Import):
                ithal.extend(a.name for a in d.names)
            elif isinstance(d, ast.ImportFrom):
                ithal.append(d.module or "")
        for ad in ithal:
            kok = ad.lstrip(".")
            self.assertNotIn(
                kok, yasak,
                f"tazeleme veri tabanı katmanını içe aktarıyor: {ad}")

    def test_robots_denetimi_kapatilamaz(self) -> None:
        """`ignore=True` bu yoldan geçirilemez — etik kısıt pazarlık dışı."""
        import ast
        for d in ast.walk(self._agac()):
            if not isinstance(d, ast.Call):
                continue
            for kw in d.keywords:
                self.assertNotIn(
                    kw.arg, ("ignore", "ignore_robots"),
                    f"robots denetimini kapatan çağrı: satır {d.lineno}")


class TestYonetici(unittest.TestCase):
    """Tek yuva: aynı anda iki tazeleme başlatılamaz."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_ikinci_is_reddedilir(self) -> None:
        birak = __import__("threading").Event()

        def yavas(bank, raw_dir, durum, **kwargs):
            birak.wait(5)
            kwargs["guncelle"](durum=DURUM_TAMAM, asama="bitti")
            return durum

        y = TazelemeYoneticisi(self._tmp.name, calisma_fn=yavas)
        ilk = y.baslat(BANKA)
        try:
            with self.assertRaises(TazelemeMesgul) as ctx:
                y.baslat(BANKA)
            self.assertEqual(ctx.exception.calisan_banka, BANKA.name)
        finally:
            birak.set()
        self.assertIsNotNone(y.durum(ilk["is_id"]))

    def test_biten_isten_sonra_yeni_is_baslatilabilir(self) -> None:
        def hizli(bank, raw_dir, durum, **kwargs):
            kwargs["guncelle"](durum=DURUM_TAMAM, asama="bitti")
            return durum

        y = TazelemeYoneticisi(self._tmp.name, calisma_fn=hizli)
        ilk = y.baslat(BANKA)
        for _ in range(200):
            if y.aktif_banka() is None:
                break
            time.sleep(0.01)
        ikinci = y.baslat(BANKA)
        self.assertNotEqual(ilk["is_id"], ikinci["is_id"])
        self.assertEqual(y.son_is()["is_id"], ikinci["is_id"])

    def test_alt_akis_ise_gecirilir(self) -> None:
        """Yönetici geri çağrıyı işe TAŞIMALI.

        Taşımasaydı bağ sessizce kopardı: `tazele` alt akışı `None` görür,
        bayat özet düşürülmez ve hiçbir test bunu fark etmezdi — uçtan uca
        yol yalnız burada birleşiyor.
        """
        gorulen: dict[str, object] = {}

        def kaydeden(bank, raw_dir, durum, **kwargs):
            gorulen["alt_akis"] = kwargs.get("alt_akis")
            kwargs["guncelle"](durum=DURUM_TAMAM, asama="bitti")
            return durum

        def hook(degisenler):
            return {}

        y = TazelemeYoneticisi(self._tmp.name, calisma_fn=kaydeden,
                               alt_akis=hook)
        y.baslat(BANKA)
        for _ in range(200):
            if y.aktif_banka() is None:
                break
            time.sleep(0.01)
        self.assertIs(gorulen.get("alt_akis"), hook)

    def test_bilinmeyen_is_none_doner(self) -> None:
        y = TazelemeYoneticisi(self._tmp.name)
        self.assertIsNone(y.durum("yok-boyle-bir-is"))
        self.assertIsNone(y.iptal_et("yok-boyle-bir-is"))
        self.assertIsNone(y.son_is())

    def test_iptal_bayragi_ise_islenir(self) -> None:
        gorulen: dict[str, bool] = {}
        birak = __import__("threading").Event()

        def bekleyen(bank, raw_dir, durum, **kwargs):
            birak.wait(5)
            gorulen["iptal"] = kwargs["iptal"]()
            kwargs["guncelle"](durum=DURUM_IPTAL, asama="durduruldu")
            return durum

        y = TazelemeYoneticisi(self._tmp.name, calisma_fn=bekleyen)
        kayit = y.baslat(BANKA)
        y.iptal_et(kayit["is_id"])
        birak.set()
        for _ in range(200):
            if y.aktif_banka() is None:
                break
            time.sleep(0.01)
        self.assertTrue(gorulen.get("iptal"), "iptal isteği işe ulaşmadı")


class TestSonTazelemeOzeti(unittest.TestCase):
    """`data/son-tazeleme.json` — bellek içi `TazelemeDurumu`'nun kalıcı izi.

    `TazelemeYoneticisi`/`tazele()` TAMAMEN bellek içidir; bu dosya "en son ne
    zaman tazeleme yapıldı, kaç belge değişti/yeni geldi" iddiasının süreç
    yeniden başlasa da hayatta kalan tek izidir. `kok` her testte geçici bir
    dizine sabitlenir — gerçek depo kökü hiç dokunulmaz.
    """

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.kok = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_dosya_yoksa_bos_sozluk_doner(self) -> None:
        self.assertEqual(son_tazeleme_oku(kok=self.kok), {})

    def test_tamam_olmayan_is_yazilmaz(self) -> None:
        durum = TazelemeDurumu(is_id="t1", bank="ornek", bank_name="Örnek",
                               durum=DURUM_HATA)
        son_tazeleme_yaz(durum, kok=self.kok)
        self.assertEqual(son_tazeleme_oku(kok=self.kok), {})
        self.assertFalse((self.kok / "data" / "son-tazeleme.json").exists())

    def test_tamam_is_yazilir_ve_okunur(self) -> None:
        durum = TazelemeDurumu(
            is_id="t1", bank="ornek", bank_name="Örnek", durum=DURUM_TAMAM,
            bitis="2026-08-25T12:00:00Z", yeni=1, degisen=2, ayni=3, hata=0,
            belgeler=[
                {"source_url": "https://a", "title": "A", "durum": BELGE_DEGISEN},
                {"source_url": "https://b", "title": "B", "durum": BELGE_YENI},
            ])
        son_tazeleme_yaz(durum, kok=self.kok)
        ozet = son_tazeleme_oku(kok=self.kok)
        self.assertIn("ornek", ozet)
        kayit = ozet["ornek"]
        self.assertEqual(kayit["bank_name"], "Örnek")
        self.assertEqual(kayit["yeni"], 1)
        self.assertEqual(kayit["degisen"], 2)
        self.assertEqual(kayit["ayni"], 3)
        # Yalnız DEĞİŞEN belge geçer — yeni/aynı belge listeye girmez.
        self.assertEqual(kayit["degisen_belgeler"],
                         [{"title": "A", "source_url": "https://a"}])

    def test_ayni_banka_uzerine_yazar_digeri_korunur(self) -> None:
        birinci = TazelemeDurumu(is_id="t1", bank="banka-a", bank_name="A",
                                 durum=DURUM_TAMAM, yeni=1)
        ikinci = TazelemeDurumu(is_id="t2", bank="banka-b", bank_name="B",
                                durum=DURUM_TAMAM, yeni=2)
        son_tazeleme_yaz(birinci, kok=self.kok)
        son_tazeleme_yaz(ikinci, kok=self.kok)
        guncellenen_a = TazelemeDurumu(is_id="t3", bank="banka-a", bank_name="A",
                                       durum=DURUM_TAMAM, yeni=5)
        son_tazeleme_yaz(guncellenen_a, kok=self.kok)
        ozet = son_tazeleme_oku(kok=self.kok)
        self.assertEqual(set(ozet), {"banka-a", "banka-b"})
        self.assertEqual(ozet["banka-a"]["yeni"], 5,
                         "aynı bankanın eski kaydı üzerine yazılmadı")
        self.assertEqual(ozet["banka-b"]["yeni"], 2,
                         "başka bankanın kaydı korunmadı")

    def test_bozuk_dosya_bos_sozluk_doner(self) -> None:
        yol = self.kok / "data" / "son-tazeleme.json"
        yol.parent.mkdir(parents=True, exist_ok=True)
        yol.write_text("{ bozuk json", encoding="utf-8")
        self.assertEqual(son_tazeleme_oku(kok=self.kok), {})


if __name__ == "__main__":
    unittest.main()
