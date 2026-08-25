"""`GET /campaigns` süzgeçleri + `GET /stats` — 10,3 MB'lık yükün kapısı.

İlgili: ../src/api/main.py (`campaigns`, `stats`)
        ../src/db/base.py (`kampanya_where`, `kampanya_sutunlari`,
                           `kampanya_metin_suz`, `kampanya_durumu_dogrula`)
        ../src/db/repository.py, ../src/db/postgres.py
        ../tests/test_api_backend.py (iki backend uç paritesi)

## Bu testlerin varlık sebebi

Ölçüldü (2026-08-11): `curl -s localhost:8000/campaigns | wc -c` =
**10.339.015 bayt**. Uç 1774 satırı `raw_text` ile birlikte döndürüyordu ve
arayüz o alanı hiçbir yerde okumuyordu — `web/app` içinde tek geçtiği yer bir
tip tanımıydı. Dashboard her açılışta 10 MB indiriyordu.

Burada dört şey kilitleniyor:

1. **Varsayılan yanıt gövdesiz.** `raw_text` yalnız `?govde=true` ile gelir.
   Alan SİLİNMEDİ, kapatıldı — geri açan yol test edilmezse sessizce ölür.
2. **Yanıt ÇIPLAK LİSTE kalır.** Toplam `X-Toplam-Kayit` başlığındadır.
   Gövdeyi bir zarfa sarmak her çağıranı aynı anda kırardı
   (`tests/test_api_tazeleme.py` `len(...json())` sayıyor).
3. **`?` / `%s` tuzağı.** Süzgeç metni iki backend için TEK yerde üretilir;
   burada iki lehçe için de üretilip yer tutucunun ayrışmadığı doğrulanır.
   Postgres kurulu olmadan koşar — tuzak SQL METNİNDE, bağlantıda değil.
4. **`damgasiz` üçüncü kovadır.** `campaign_status IS NULL` "aktif" DEĞİLDİR
   ve iki sayaç (`/campaigns?status=`, `/stats`) bunu aynı biçimde saymalı.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.db.base import (
    KAMPANYA_DURUMU_DAMGASIZ,
    kampanya_metin_suz,
    kampanya_sutunlari,
    kampanya_where,
)
from src.schemas import Campaign, ExtractedField, Extractor

try:  # pragma: no cover - ortama bağlı
    import httpx  # noqa: F401
    from fastapi.testclient import TestClient
    HAS_API = True
except ModuleNotFoundError:  # pragma: no cover
    HAS_API = False

requires_api = unittest.skipUnless(
    HAS_API, "fastapi/httpx yok — uç testi atlanıyor")


def _alan() -> ExtractedField:
    return ExtractedField(
        field_name="kar_payi_orani", raw_value="%2,05", canonical_value=2.05,
        confidence=0.9, source_span="kâr payı oranı %2,05",
        extractor=Extractor.RULE)


#: (banka, tür, belge_turu, durum, metin) — dördü de farklı kovada.
KORPUS = (
    ("kuveyt-turk", "Konut Finansmanı", "kampanya", "expired",
     "Konut finansmanında kâr payı oranı %2,05."),
    ("kuveyt-turk", "Taşıt Finansmanı", "kampanya", None,
     "Taşıt finansmanında kâr payı oranı %2,05."),
    ("albaraka", "İhtiyaç Finansmanı", "sozlesme", "active",
     "Genel akit metni: kâr payı oranı %2,05."),
)


def _korpus_yaz(repo) -> list[int]:
    ids = []
    for slug, tur, belge_turu, durum, metin in KORPUS:
        cid = repo.insert_campaign(
            Campaign(bank_slug=slug, raw_text=metin, campaign_type=tur,
                     source_url=f"https://{slug}.test/{len(ids)}",
                     fields=[_alan()]),
            clean_text=metin, scraped_at="2026-08-01T00:00:00+00:00",
            campaign_status=durum)
        repo.set_belge_turu({cid: belge_turu})
        ids.append(cid)
    return ids


# --------------------------------------------------------------------------- #
# Yer tutucu tuzağı — Postgres GEREKMEZ
# --------------------------------------------------------------------------- #
class TestSuzgecMetniIkiLehcedeAyni(unittest.TestCase):
    """Süzgeç TEK yerde üretilir; iki lehçe arasındaki fark yalnız yer tutucu.

    `src/api/main.py` başlığındaki ölçülmüş tuzak: `?` taşıyan SQL Postgres'te
    `ProgrammingError` ile düşer. Süzgeç iki backend'de elle yazılsaydı bu
    fark ancak Postgres kurulu bir makinede görünürdü — burada SQL METNİ
    üzerinden, bağlantısız yakalanır.
    """

    def test_yalnizca_yer_tutucu_farkli(self) -> None:
        kw = dict(bank="kuveyt-turk", campaign_type="Konut Finansmanı",
                  belge_turu="kampanya", status="expired")
        lite, lite_p = kampanya_where(yer_tutucu="?", **kw)
        pg, pg_p = kampanya_where(yer_tutucu="%s", **kw)
        self.assertEqual(lite.replace("?", "%s"), pg)
        self.assertEqual(lite_p, pg_p)

    def test_sqlite_metninde_yuzde_s_YOK(self) -> None:
        sql, _ = kampanya_where(yer_tutucu="?", bank="x", status="active")
        self.assertNotIn("%s", sql)
        self.assertEqual(sql.count("?"), 2)

    def test_postgres_metninde_soru_isareti_YOK(self) -> None:
        sql, _ = kampanya_where(yer_tutucu="%s", bank="x", status="active")
        self.assertNotIn("?", sql)
        self.assertEqual(sql.count("%s"), 2)

    def test_damgasiz_IS_NULL_a_cevrilir_ve_parametre_uretmez(self) -> None:
        """`= 'damgasiz'` hiçbir satır döndürmezdi: o dizge sütunda yazılı değil."""
        sql, params = kampanya_where(yer_tutucu="?",
                                     status=KAMPANYA_DURUMU_DAMGASIZ)
        self.assertIn("c.campaign_status IS NULL", sql)
        self.assertEqual(params, [])

    def test_suzgecsiz_cagri_bos_where_verir(self) -> None:
        self.assertEqual(kampanya_where(yer_tutucu="?"), ("", []))

    def test_gecersiz_deger_reddedilir(self) -> None:
        with self.assertRaises(ValueError):
            kampanya_where(yer_tutucu="?", status="aktif")
        with self.assertRaises(ValueError):
            kampanya_where(yer_tutucu="?", belge_turu="broşür")

    def test_govde_sutun_listesinden_CIKAR(self) -> None:
        self.assertNotIn("raw_text", kampanya_sutunlari(govde=False))
        self.assertIn("c.raw_text", kampanya_sutunlari(govde=True))

    def test_govde_disinda_iki_liste_ayni(self) -> None:
        """Kapatılan tek şey gövde; başka sütun sessizce düşmemeli."""
        acik = [s for s in kampanya_sutunlari(govde=True).split(", ")
                if s != "c.raw_text"]
        self.assertEqual(acik, kampanya_sutunlari(govde=False).split(", "))


class TestMetinSuzgeciTurkceKatlar(unittest.TestCase):
    """`q` Python'da uygulanır: SQL `LOWER()`'ı iki backend'de aynı değil."""

    SATIRLAR = [
        {"bank": "kuveyt-turk", "bank_name": "Kuveyt Türk",
         "campaign_type": "İhtiyaç Finansmanı", "ozet": None,
         "source_url": "https://kt.test/a"},
        {"bank": "albaraka", "bank_name": "Albaraka Türk",
         "campaign_type": "Konut Finansmanı", "ozet": "Kâr payı avantajı",
         "source_url": "https://ab.test/b"},
    ]

    def test_buyuk_kucuk_ve_diakritik_farki_onemsiz(self) -> None:
        for aranan in ("İHTİYAÇ", "ihtiyac", "İhtiyaç"):
            with self.subTest(q=aranan):
                bulunan = kampanya_metin_suz(self.SATIRLAR, aranan)
                self.assertEqual([r["bank"] for r in bulunan], ["kuveyt-turk"])

    def test_ozet_ve_url_de_taranir(self) -> None:
        self.assertEqual(
            [r["bank"] for r in kampanya_metin_suz(self.SATIRLAR, "kar payi")],
            ["albaraka"])
        self.assertEqual(
            [r["bank"] for r in kampanya_metin_suz(self.SATIRLAR, "ab.test")],
            ["albaraka"])

    def test_bos_sorgu_hicbir_seyi_elemez(self) -> None:
        for aranan in (None, "", "   "):
            with self.subTest(q=aranan):
                self.assertEqual(len(kampanya_metin_suz(self.SATIRLAR, aranan)),
                                 len(self.SATIRLAR))

    def test_eslesmeyen_sorgu_bos_liste(self) -> None:
        self.assertEqual(kampanya_metin_suz(self.SATIRLAR, "sukuk"), [])


# --------------------------------------------------------------------------- #
# Depo katmanı (SQLite yolu)
# --------------------------------------------------------------------------- #
class TestDepoSuzgecleri(unittest.TestCase):
    def setUp(self) -> None:
        from src.db.repository import Repository
        self.repo = Repository(":memory:")
        self.ids = _korpus_yaz(self.repo)

    def tearDown(self) -> None:
        self.repo.close()

    def test_govde_varsayilani_TRUE_kalir(self) -> None:
        """Depo içi çağıranlar (RAG, gömme, toplu özet) gövdeye MUHTAÇ.

        Varsayılanı `False` yapmak onları sessizce boş metinle koştururdu;
        kararı veren taraf uçtur.
        """
        self.assertIn("raw_text", self.repo.all_campaigns()[0])
        self.assertNotIn("raw_text", self.repo.all_campaigns(govde=False)[0])

    def test_banka_ve_tur_suzgeci(self) -> None:
        self.assertEqual(len(self.repo.all_campaigns(bank="kuveyt-turk")), 2)
        self.assertEqual(
            len(self.repo.all_campaigns(campaign_type="Konut Finansmanı")), 1)
        self.assertEqual(
            len(self.repo.all_campaigns(bank="albaraka",
                                        campaign_type="Konut Finansmanı")), 0)

    def test_durum_suzgeci_damgasizi_AKTIFTEN_ayirir(self) -> None:
        aktif = self.repo.all_campaigns(status="active")
        damgasiz = self.repo.all_campaigns(status=KAMPANYA_DURUMU_DAMGASIZ)
        self.assertEqual(len(aktif), 1)
        self.assertEqual(len(damgasiz), 1)
        self.assertNotEqual(aktif[0]["id"], damgasiz[0]["id"])
        self.assertIsNone(damgasiz[0]["campaign_status"])

    def test_belge_turu_suzgeci_korunur(self) -> None:
        """Var olan `belge_turu` seçicisi geriye tam uyumlu kalmalı."""
        self.assertEqual(
            len(self.repo.all_campaigns(belge_turu="sozlesme")), 1)

    def test_id_sirasi_suzgecten_sonra_da_korunur(self) -> None:
        ids = [r["id"] for r in self.repo.all_campaigns(bank="kuveyt-turk")]
        self.assertEqual(ids, sorted(ids))

    def test_campaign_status_counts_sabit_anahtar_kumesi(self) -> None:
        self.assertEqual(self.repo.campaign_status_counts(),
                         {"active": 1, "expired": 1, "damgasiz": 1})

    def test_campaign_status_counts_bos_korpusta_sifir_yazar(self) -> None:
        """Eksik anahtar, `0` ile "ölçülmedi"yi ayırt edilemez kılardı."""
        from src.db.repository import Repository
        bos = Repository(":memory:")
        try:
            self.assertEqual(bos.campaign_status_counts(),
                             {"active": 0, "expired": 0, "damgasiz": 0})
        finally:
            bos.close()

    def test_bank_field_coverage_alan_CESIDI_sayar(self) -> None:
        """`alan` satır değil FARKLI alan adı sayar — 12 çeşit üst sınırdır."""
        kapsam = self.repo.bank_field_coverage()
        self.assertEqual(kapsam["kuveyt-turk"], {"belge": 2, "alan": 1})
        self.assertEqual(kapsam["albaraka"], {"belge": 1, "alan": 1})

    def test_bank_field_coverage_belgesiz_bankayi_SIFIRLA_gosterir(self) -> None:
        self.repo.upsert_bank("Boş Katılım", "bos-katilim")
        self.assertEqual(self.repo.bank_field_coverage()["bos-katilim"],
                         {"belge": 0, "alan": 0})

    def test_belge_sayisi_campaigns_per_bank_ile_TUTARLI(self) -> None:
        """İki metot aynı soruyu iki kez cevaplıyor; ayrışırlarsa biri yalan."""
        per_bank = self.repo.campaigns_per_bank()
        for slug, kapsam in self.repo.bank_field_coverage().items():
            self.assertEqual(kapsam["belge"], per_bank[slug], slug)


# --------------------------------------------------------------------------- #
# Uç sözleşmesi
# --------------------------------------------------------------------------- #
@requires_api
class UcTestBase(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        from src.api import main as api_main
        from src.db.factory import create_repository

        cls.repo = create_repository(database_path=":memory:", thread_safe=True)
        cls.ids = _korpus_yaz(cls.repo)
        onceki = api_main.create_repository
        api_main.create_repository = lambda **kw: cls.repo
        try:
            cls.app = api_main.build_app()
        finally:
            api_main.create_repository = onceki
        cls.client = TestClient(cls.app)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.repo.close()


class TestCampaignsUcu(UcTestBase):
    def test_varsayilan_yanitta_RAW_TEXT_YOK(self) -> None:
        """Asıl düzeltme: 10,3 MB'lık yükün neredeyse tamamı bu alandı."""
        satirlar = self.client.get("/campaigns").json()
        self.assertEqual(len(satirlar), len(KORPUS))
        for s in satirlar:
            self.assertNotIn("raw_text", s)

    def test_govde_true_eski_yaniti_GERI_verir(self) -> None:
        """Alan silinmedi, kapatıldı — geri açan yol da sözleşmenin parçası."""
        satirlar = self.client.get("/campaigns?govde=true").json()
        self.assertTrue(all(s["raw_text"] for s in satirlar))

    def test_yanit_CIPLAK_LISTE_zarf_yok(self) -> None:
        """`len(client.get('/campaigns').json())` sayan testler kırılmamalı."""
        govde = self.client.get("/campaigns").json()
        self.assertIsInstance(govde, list)

    def test_gizli_alanlar_artik_TIPTE_de_var(self) -> None:
        """Bunlar tel üzerinde ZATEN vardı; arayüz tipi onları saklıyordu."""
        satir = self.client.get("/campaigns").json()[0]
        for anahtar in ("belge_turu", "campaign_status", "ozet_sebep"):
            self.assertIn(anahtar, satir)

    def test_toplam_kayit_basligi(self) -> None:
        r = self.client.get("/campaigns")
        self.assertEqual(r.headers["X-Toplam-Kayit"], str(len(KORPUS)))

    def test_toplam_kayit_SUZGECTEN_SONRAKI_sayidir(self) -> None:
        r = self.client.get("/campaigns", params={"bank": "kuveyt-turk"})
        self.assertEqual(r.headers["X-Toplam-Kayit"], "2")

    def test_toplam_kayit_SAYFALAMADAN_ETKILENMEZ(self) -> None:
        """Başlığın tek işi bu: dilim alındıktan sonra toplam geri gelmez."""
        r = self.client.get("/campaigns", params={"limit": 1})
        self.assertEqual(len(r.json()), 1)
        self.assertEqual(r.headers["X-Toplam-Kayit"], str(len(KORPUS)))

    def test_limit_ontanimi_YOK_tam_liste_doner(self) -> None:
        self.assertEqual(len(self.client.get("/campaigns").json()), len(KORPUS))

    def test_offset_ve_limit(self) -> None:
        hepsi = self.client.get("/campaigns").json()
        dilim = self.client.get("/campaigns",
                                params={"limit": 1, "offset": 1}).json()
        self.assertEqual([r["id"] for r in dilim], [hepsi[1]["id"]])

    def test_offset_sonu_asarsa_bos_liste(self) -> None:
        self.assertEqual(
            self.client.get("/campaigns", params={"offset": 99}).json(), [])

    def test_suzgecler(self) -> None:
        for params, beklenen in (
                ({"bank": "albaraka"}, 1),
                ({"type": "Taşıt Finansmanı"}, 1),
                ({"belge_turu": "sozlesme"}, 1),
                ({"belge_turu": "kampanya"}, 2),
                ({"status": "expired"}, 1),
                ({"status": "damgasiz"}, 1),
                ({"q": "taşıt"}, 1),
                ({"q": "TASIT"}, 1),
                ({"bank": "kuveyt-turk", "status": "expired"}, 1),
                ({"bank": "albaraka", "status": "expired"}, 0)):
            with self.subTest(**params):
                r = self.client.get("/campaigns", params=params)
                self.assertEqual(r.status_code, 200, r.text)
                self.assertEqual(len(r.json()), beklenen)

    def test_gecersiz_deger_400_ve_TURKCE_gerekce(self) -> None:
        """500 değil 400: hata istemcinin, sunucunun değil."""
        for params in ({"belge_turu": "broşür"}, {"status": "aktif"},
                       {"limit": -1}, {"offset": -3}):
            with self.subTest(**params):
                r = self.client.get("/campaigns", params=params)
                self.assertEqual(r.status_code, 400, r.text)
                self.assertTrue(r.json()["detail"])


class TestStatsUcu(UcTestBase):
    def test_sozlesme_anahtarlari(self) -> None:
        veri = self.client.get("/stats").json()
        self.assertEqual(
            set(veri),
            {"korpus", "belge_turu", "campaign_status", "banka_basina",
             "banka_kapsami", "campaign_types", "campaign_type_counts",
             "alan_kapsami", "katman", "llm", "backend"})

    def test_depo_metotlarinin_BILESIMI_kendi_hesaplamaz(self) -> None:
        """Uç hiçbir sayıyı kendi üretmez; ürettiği an bilgi iki yerde yaşar."""
        veri = self.client.get("/stats").json()
        self.assertEqual(veri["korpus"], self.repo.counts())
        self.assertEqual(veri["belge_turu"], self.repo.belge_turu_counts())
        self.assertEqual(veri["campaign_status"],
                         self.repo.campaign_status_counts())
        self.assertEqual(veri["banka_basina"], self.repo.campaigns_per_bank())
        self.assertEqual(veri["alan_kapsami"], self.repo.field_coverage())
        self.assertEqual(veri["katman"], self.repo.fields_by_extractor())
        self.assertEqual(veri["backend"], self.repo.backend)

    def test_banka_kapsami_belge_ve_alan_tasir(self) -> None:
        kapsam = self.client.get("/stats").json()["banka_kapsami"]
        self.assertEqual(kapsam["kuveyt-turk"], {"belge": 2, "alan": 1})

    def test_campaign_types_sirali_ve_TEKRARSIZ(self) -> None:
        """`page.tsx` bu listeyi `<select>`e basıyor; 10 MB indirmeden."""
        turler = self.client.get("/stats").json()["campaign_types"]
        self.assertEqual(turler, sorted(set(turler)))
        self.assertEqual(set(turler), {t[1] for t in KORPUS})

    def test_damgasiz_kovasi_AKTIFE_KATILMAZ(self) -> None:
        durum = self.client.get("/stats").json()["campaign_status"]
        self.assertEqual(durum, {"active": 1, "expired": 1, "damgasiz": 1})

    def test_llm_durumu_health_ile_AYNI_kaynaktan(self) -> None:
        """Arayüz "LLM kapalı" rozetini iki uçtan farklı öğrenmemeli."""
        self.assertEqual(self.client.get("/stats").json()["llm"]["acik"],
                         self.client.get("/health").json()["llm"])


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
