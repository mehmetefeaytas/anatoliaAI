"""`GET /search` + arama katmanı — arayüzdeki en büyük gezinme boşluğunun kapısı.

İlgili: ../src/api/main.py (`search`)
        ../src/db/base.py (`arama_where`, `arama_sutunlari`, `arama_suz`,
                           `arama_eslesmesi`, `tr_katla_haritali`)
        ../src/db/repository.py, ../src/db/postgres.py (`search_campaigns`)
        ../web/app/lib/arama.ts, ../web/tests/arama.test.ts (istemci ikizi)
        ./arama_katlama_ornekleri.json (iki dilin ORTAK fikstürü)
        ./test_kampanya_listesi_suzgeci.py (aynı yer tutucu tuzağı deseni)

## Bu testlerin varlık sebebi

Ölçüldü (2026-08-12, `GET /stats`): korpus 1774 belge, bunun 126'sı akit ve
458'i süresi dolmuş. Arayüzde arama YOKTU; denetim panelinde bu 1774 belge tek
bir açılır listeye seçenek seçenek diziliyordu ve o listede akitler de süresi
dolmuş belgeler de AYIRT EDİLEMİYORDU.

Burada beş şey kilitleniyor:

1. **`?` / `%s` tuzağı.** Arama SQL'i iki backend için TEK yerde üretilir;
   burada iki lehçe de üretilip yer tutucudan başka hiçbir farkın olmadığı
   doğrulanır. Postgres kurulu olmadan koşar — tuzak SQL METNİNDE.
2. **Ham gövde TARANMAZ.** `raw_text` ne SELECT listesinde ne aranan alan
   listesindedir. Tuş başına 10 MB taramak bedava değildir.
3. **Türkçe katlama.** 'ihtiyac' → 'İhtiyaç Finansmanı' bulunmalı; iki
   backend ve İSTEMCİ aynı katlamayı üretmeli (ortak fikstür).
4. **`eslesme` = NEDEN eşleşti.** Her sonuç kanıt taşır ve kanıt, satırın
   zaten gösterdiği alanı değil GÖRÜNMEYENİ göstermeye çalışır.
5. **Boş sorgu BOŞ döner.** Arama kutusu her açıldığında korpusun tamamı tel
   üzerinden geçmemeli.
"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.db.base import (
    ARAMA_ALANLARI,
    ARAMA_AZAMI_LIMIT,
    ARAMA_VARSAYILAN_LIMIT,
    arama_eslesmesi,
    arama_konumu,
    arama_parcasi,
    arama_sutunlari,
    arama_suz,
    arama_terimleri,
    arama_where,
    tr_katla_haritali,
)
from src.db.repository import Repository
from src.preprocessing.clean import tr_fold_ascii
from src.schemas import Campaign, ExtractedField, Extractor
from tests._ortam_gereksinimleri import arayuz_var

try:  # pragma: no cover - ortama bağlı
    import httpx  # noqa: F401
    from fastapi.testclient import TestClient
    HAS_API = True
except ModuleNotFoundError:  # pragma: no cover
    HAS_API = False

requires_api = unittest.skipUnless(
    HAS_API, "fastapi/httpx yok — uç testi atlanıyor")

_KOK = Path(__file__).resolve().parents[1]
KATLAMA_FIKSTUR = Path(__file__).with_name("arama_katlama_ornekleri.json")


#: (banka slug, banka adı, tür, belge_turu, durum, özet, adres)
KORPUS = (
    ("kuveyt-turk", "Kuveyt Türk", "Konut Finansmanı", "kampanya", None,
     "Konut finansmanında kâr payı oranı %2,05 ve tahsis ücreti alınmaz.",
     "https://kuveytturk.test/konut"),
    ("kuveyt-turk", "Kuveyt Türk", "İhtiyaç Finansmanı", "kampanya", "expired",
     "İhtiyaç finansmanı kampanyası 31.12.2025 tarihinde sona ermiştir.",
     "https://kuveytturk.test/ihtiyac"),
    ("albaraka", "Albaraka Türk", "Taşıt Finansmanı", "sozlesme", None,
     None, "https://albaraka.test/genel-akit.pdf"),
)


def _alan() -> ExtractedField:
    return ExtractedField(
        field_name="kar_payi_orani", raw_value="%2,05", canonical_value=2.05,
        confidence=0.9, source_span="kâr payı oranı %2,05",
        extractor=Extractor.RULE)


def _korpus_yaz(repo: Repository) -> list[int]:
    for slug, ad, *_ in KORPUS:
        repo.upsert_bank(ad, slug)
    ids = []
    for slug, _ad, tur, belge_turu, durum, ozet, url in KORPUS:
        cid = repo.insert_campaign(
            Campaign(bank_slug=slug, raw_text=f"{tur} ham gövde metni.",
                     campaign_type=tur, source_url=url, fields=[_alan()]),
            clean_text=f"{tur} ham gövde metni.",
            scraped_at="2026-08-01T00:00:00+00:00", campaign_status=durum)
        repo.set_belge_turu({cid: belge_turu})
        if ozet:
            repo.set_ozet({cid: ozet})
        ids.append(cid)
    return ids


# --------------------------------------------------------------------------- #
# 1. Yer tutucu tuzağı — Postgres GEREKMEZ
# --------------------------------------------------------------------------- #
class TestAramaSqlIkiLehcedeAyni(unittest.TestCase):
    """Arama süzgeci TEK yerde üretilir; iki lehçe arasındaki fark yalnız `?`/`%s`.

    `src/api/main.py` başlığındaki ölçülmüş tuzak: `?` taşıyan SQL Postgres'te
    `ProgrammingError` ile düşer. Süzgeç iki backend'de elle yazılsaydı fark
    ancak Postgres kurulu bir makinede görünürdü.
    """

    KAPSAM = dict(bank="kuveyt-turk", campaign_type="Konut Finansmanı",
                  belge_turu="kampanya", status="expired")

    def test_yalnizca_yer_tutucu_farkli(self) -> None:
        lite, lite_p = arama_where(yer_tutucu="?", **self.KAPSAM)
        pg, pg_p = arama_where(yer_tutucu="%s", **self.KAPSAM)
        self.assertEqual(lite.replace("?", "%s"), pg)
        self.assertEqual(lite_p, pg_p)

    def test_sqlite_metninde_yuzde_s_YOK(self) -> None:
        sql, _ = arama_where(yer_tutucu="?", bank="x", status="active")
        self.assertNotIn("%s", sql)
        self.assertEqual(sql.count("?"), 2)

    def test_postgres_metninde_soru_isareti_YOK(self) -> None:
        sql, _ = arama_where(yer_tutucu="%s", bank="x", status="active")
        self.assertNotIn("?", sql)
        self.assertEqual(sql.count("%s"), 2)

    def test_kapsamsiz_cagri_bos_where_verir(self) -> None:
        self.assertEqual(arama_where(yer_tutucu="?"), ("", []))

    def test_gecersiz_deger_reddedilir(self) -> None:
        """Doğrulama `kampanya_where()` ile AYNI kapıdan geçmeli."""
        with self.assertRaises(ValueError):
            arama_where(yer_tutucu="?", status="aktif")
        with self.assertRaises(ValueError):
            arama_where(yer_tutucu="?", belge_turu="broşür")


class TestAramaSutunlari(unittest.TestCase):
    """Ham gövde SEÇİLMEZ ve seçilebilir bir kapı da bırakılmaz."""

    def test_raw_text_YOK(self) -> None:
        self.assertNotIn("raw_text", arama_sutunlari())
        self.assertNotIn("clean_text", arama_sutunlari())

    def test_aranan_alanlarda_ham_govde_YOK(self) -> None:
        self.assertNotIn("raw_text", ARAMA_ALANLARI)
        self.assertNotIn("clean_text", ARAMA_ALANLARI)

    def test_aranan_her_alan_secilen_sutunlarda_var(self) -> None:
        """Aranan bir alan SELECT'te yoksa süzgeç sessizce hiç eşleşmezdi."""
        sutunlar = arama_sutunlari()
        for alan in ARAMA_ALANLARI:
            with self.subTest(alan=alan):
                self.assertIn(alan, sutunlar)

    def test_scraped_at_YOK(self) -> None:
        """İki backend'in ayrışabildiği tek sütun sorgunun dışında kalmalı."""
        self.assertNotIn("scraped_at", arama_sutunlari())


# --------------------------------------------------------------------------- #
# 2. Türkçe katlama — istemciyle ORTAK fikstür
# --------------------------------------------------------------------------- #
class TestKatlama(unittest.TestCase):
    """Sunucu katlaması: fikstürdeki her beklenen değeri üretmeli."""

    def setUp(self) -> None:
        self.fikstur = json.loads(
            KATLAMA_FIKSTUR.read_text(encoding="utf-8"))

    def test_fikstur_bos_degil(self) -> None:
        """Fikstür boşalırsa istemci parite testi de sessizce boşalırdı."""
        self.assertGreaterEqual(len(self.fikstur["ornekler"]), 20)

    def test_beklenen_katlamalar(self) -> None:
        for ornek in self.fikstur["ornekler"]:
            with self.subTest(girdi=ornek["girdi"]):
                self.assertEqual(tr_fold_ascii(ornek["girdi"]),
                                 ornek["katli"])

    def test_fikstur_istemci_testini_isaret_eder(self) -> None:
        """İkiz test dosyası gerçekten var mı (yol bayatlamasın)."""
        for yol in self.fikstur["kosanlar"]:
            with self.subTest(yol=yol):
                # `web/` teslim imajına kopyalanmaz; oradaki yolu bu ortamda
                # doğrulamak imkânsız. Python tarafı yine de sınanır.
                if yol.startswith("web/") and not arayuz_var():
                    self.skipTest("web/ yok — arayüz ikizinin yolu CI'daki "
                                  "`test` işinde doğrulanır")
                self.assertTrue((_KOK / yol).exists(), yol)


class TestHaritaliKatlama(unittest.TestCase):
    """Katlanmış konumdan ÖZGÜN konuma dönüş — parça buradan kesiliyor."""

    def test_harita_uzunlugu_katli_metinle_ayni(self) -> None:
        katli, harita = tr_katla_haritali("Kâr Payı Oranı")
        self.assertEqual(len(katli), len(harita))

    def test_ozgun_indeksleri_dogru(self) -> None:
        metin = "İhtiyaç Finansmanı"
        yer = arama_konumu(metin, "finansmani")
        self.assertIsNotNone(yer)
        s, e = yer  # type: ignore[misc]
        self.assertEqual(metin[s:e], "Finansmanı")

    def test_diakritikli_hedef_ozgun_yaziyla_doner(self) -> None:
        metin = "Kampanyada kâr payı oranı düşüktür."
        s, e = arama_konumu(metin, "kar payi")  # type: ignore[misc]
        self.assertEqual(metin[s:e], "kâr payı")

    def test_bulunamayan_terim_None(self) -> None:
        self.assertIsNone(arama_konumu("Konut Finansmanı", "tasit"))

    def test_bos_metin_None(self) -> None:
        self.assertIsNone(arama_konumu("", "x"))


class TestTerimler(unittest.TestCase):
    def test_bosluklara_bolunur_ve_katlanir(self) -> None:
        self.assertEqual(arama_terimleri("  İhtiyaç   FİNANSMANI "),
                         ("ihtiyac", "finansmani"))

    def test_tekrar_eden_terim_bir_kez(self) -> None:
        self.assertEqual(arama_terimleri("konut konut"), ("konut",))

    def test_bos_sorgu_bos_demet(self) -> None:
        self.assertEqual(arama_terimleri(""), ())
        self.assertEqual(arama_terimleri(None), ())
        self.assertEqual(arama_terimleri("   "), ())


class TestParca(unittest.TestCase):
    def test_kirpilan_uclara_ucnokta(self) -> None:
        metin = "a" * 200
        parca = arama_parcasi(metin, 100, 105)
        self.assertTrue(parca.startswith("…"))
        self.assertTrue(parca.endswith("…"))

    def test_kisa_metin_kirpilmaz(self) -> None:
        self.assertEqual(arama_parcasi("Kuveyt Türk", 0, 6), "Kuveyt Türk")

    def test_bosluklar_tek_bosluga_iner(self) -> None:
        self.assertEqual(arama_parcasi("Kuveyt\n\n  Türk", 0, 6),
                         "Kuveyt Türk")


class TestEslesme(unittest.TestCase):
    """`eslesme` = NEDEN eşleşti. Kanıt, GÖRÜNMEYENİ göstermeli."""

    SATIR = {
        "bank_name": "Kuveyt Türk",
        "campaign_type": "Konut Finansmanı",
        "ozet": "Konut finansmanında kâr payı oranı %2,05 ve masraf yoktur.",
        "source_url": "https://kuveytturk.test/konut",
    }

    def test_tum_terimler_gerekli(self) -> None:
        self.assertIsNone(arama_eslesmesi(self.SATIR,
                                          ("kuveyt", "tasit")))

    def test_terimler_farkli_alanlara_dagilabilir(self) -> None:
        """'kuveyt konut' — biri banka adında, öteki türde/özette."""
        self.assertIsNotNone(arama_eslesmesi(self.SATIR, ("kuveyt", "konut")))

    def test_beraberlikte_ozet_kazanir(self) -> None:
        """Banka adı yanıtta zaten var; kanıt olarak özet daha çok şey söyler."""
        e = arama_eslesmesi(self.SATIR, ("kuveyt", "konut"))
        self.assertEqual(e["alan"], "ozet")  # type: ignore[index]

    def test_yalniz_banka_adinda_gecen_terim_banka_adini_gosterir(self) -> None:
        e = arama_eslesmesi(self.SATIR, ("kuveyt",))
        self.assertEqual(e["alan"], "bank_name")  # type: ignore[index]

    def test_adres_SON_CARE_kanittir(self) -> None:
        """Adres iki terimi birden yakalıyor ama kanıt değeri düşük."""
        e = arama_eslesmesi(self.SATIR, ("kuveyt", "konut"))
        self.assertNotEqual(e["alan"], "source_url")  # type: ignore[index]

    def test_yalniz_adreste_gecen_terim_adresi_gosterir(self) -> None:
        """Son çare olmak, hiç kullanılmamak demek değil."""
        e = arama_eslesmesi(self.SATIR, ("https",))
        self.assertEqual(e["alan"], "source_url")  # type: ignore[index]

    def test_diakritiksiz_sorgu_diakritikli_metni_bulur(self) -> None:
        e = arama_eslesmesi(self.SATIR, arama_terimleri("kar payi"))
        self.assertIsNotNone(e)
        self.assertIn("kâr payı", e["parca"])  # type: ignore[index]

    def test_bos_terim_listesi_None(self) -> None:
        self.assertIsNone(arama_eslesmesi(self.SATIR, ()))

    def test_bos_alanlar_cokmez(self) -> None:
        self.assertIsNone(arama_eslesmesi({"ozet": None, "bank_name": None},
                                          ("konut",)))


class TestAramaSuz(unittest.TestCase):
    def test_bos_sorgu_BOS_liste(self) -> None:
        """Süzgeç değil ARAMA: aranmamış şeyin sonucu yoktur."""
        rows = [{"bank_name": "Kuveyt Türk"}]
        self.assertEqual(arama_suz(rows, ""), [])
        self.assertEqual(arama_suz(rows, None), [])
        self.assertEqual(arama_suz(rows, "   "), [])

    def test_eslesen_satira_eslesme_eklenir(self) -> None:
        rows = [{"bank_name": "Kuveyt Türk"}]
        out = arama_suz(rows, "kuveyt")
        self.assertEqual(len(out), 1)
        self.assertIn("eslesme", out[0])
        self.assertEqual(out[0]["bank_name"], "Kuveyt Türk")

    def test_girdi_satirlari_DEGISMEZ(self) -> None:
        rows = [{"bank_name": "Kuveyt Türk"}]
        arama_suz(rows, "kuveyt")
        self.assertNotIn("eslesme", rows[0])


# --------------------------------------------------------------------------- #
# 3. Depo yolu (SQLite) — gerçek SQL üzerinden
# --------------------------------------------------------------------------- #
class TestDepoAramasi(unittest.TestCase):
    def setUp(self) -> None:
        self.repo = Repository(":memory:")
        _korpus_yaz(self.repo)

    def tearDown(self) -> None:
        self.repo.close()

    def test_diakritiksiz_sorgu_bulur(self) -> None:
        out = self.repo.search_campaigns("ihtiyac")
        self.assertEqual([r["campaign_type"] for r in out],
                         ["İhtiyaç Finansmanı"])

    def test_iki_terim_farkli_alanlardan(self) -> None:
        out = self.repo.search_campaigns("kuveyt konut")
        self.assertEqual([r["id"] for r in out], [1])

    def test_akit_belgesi_de_bulunur(self) -> None:
        """126 akit ARAMADA GÖRÜNÜR — süzülen yer kıyas yoludur, arama değil."""
        out = self.repo.search_campaigns("albaraka")
        self.assertEqual([r["belge_turu"] for r in out], ["sozlesme"])

    def test_kapsam_suzgeci_calisir(self) -> None:
        self.assertEqual(
            [r["id"] for r in self.repo.search_campaigns(
                "finansmani", belge_turu="sozlesme")],
            [3])
        self.assertEqual(
            [r["id"] for r in self.repo.search_campaigns(
                "finansmani", status="expired")],
            [2])

    def test_ham_govde_TARANMAZ(self) -> None:
        """Gövdede geçen ama üstveride geçmeyen kelime BULUNMAMALI."""
        self.assertEqual(self.repo.search_campaigns("gövde"), [])

    def test_yanit_ham_govde_TASIMAZ(self) -> None:
        for r in self.repo.search_campaigns("kuveyt"):
            self.assertNotIn("raw_text", r)

    def test_eslesmeyen_sorgu_bos(self) -> None:
        self.assertEqual(self.repo.search_campaigns("mudarebe"), [])

    def test_sira_id(self) -> None:
        """Uydurma bir alaka sıralaması YOK; sıra belgelerin kendi sırası."""
        out = self.repo.search_campaigns("finansmani")
        self.assertEqual([r["id"] for r in out], sorted(r["id"] for r in out))


# --------------------------------------------------------------------------- #
# 4. Uç — `GET /search`
# --------------------------------------------------------------------------- #
@requires_api
class TestSearchUcu(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        from src.api import main as api_main
        from src.db.factory import create_repository

        cls.repo = create_repository(database_path=":memory:", thread_safe=True)
        _korpus_yaz(cls.repo)
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

    def _ara(self, **params):
        r = self.client.get("/search", params=params)
        self.assertEqual(r.status_code, 200, r.text)
        return r.json()

    def test_gruplu_yanit(self) -> None:
        d = self._ara(q="kuveyt")
        self.assertEqual(d["sorgu"], "kuveyt")
        self.assertEqual([b["slug"] for b in d["banks"]], ["kuveyt-turk"])
        self.assertEqual(d["banks"][0]["name"], "Kuveyt Türk")
        self.assertEqual(len(d["campaigns"]), 2)
        self.assertEqual(sorted(d["types"]),
                         ["Konut Finansmanı", "İhtiyaç Finansmanı"])

    def test_banka_sayaci_KORPUS_toplami(self) -> None:
        """Eşleşen belge sayısı değil, bankanın toplam belge sayısı."""
        d = self._ara(q="konut")
        self.assertEqual(len(d["campaigns"]), 1)
        self.assertEqual(d["banks"][0]["campaign_count"], 2)

    def test_her_belge_eslesme_tasir(self) -> None:
        for k in self._ara(q="ihtiyac")["campaigns"]:
            self.assertIn("alan", k["eslesme"])
            self.assertTrue(k["eslesme"]["parca"])

    def test_belge_alanlari(self) -> None:
        k = self._ara(q="ihtiyac")["campaigns"][0]
        self.assertEqual(
            sorted(k), ["bank", "bank_name", "belge_turu", "campaign_status",
                        "campaign_type", "eslesme", "id"])
        self.assertEqual(k["campaign_status"], "expired")

    def test_ozet_ve_adres_yanitta_YOK(self) -> None:
        """Aranan alan olmak, dönen alan olmak demek değil (yük disiplini)."""
        k = self._ara(q="ihtiyac")["campaigns"][0]
        self.assertNotIn("ozet", k)
        self.assertNotIn("source_url", k)

    def test_toplam_gercek_sayilar(self) -> None:
        d = self._ara(q="finansmani", limit=1)
        self.assertEqual(len(d["campaigns"]), 1)
        self.assertEqual(d["toplam"]["campaigns"], 3)
        self.assertEqual(d["toplam"]["types"], 3)

    def test_bos_sorgu_bos_gruplar(self) -> None:
        d = self._ara(q="")
        self.assertEqual(d["banks"], [])
        self.assertEqual(d["campaigns"], [])
        self.assertEqual(d["types"], [])
        self.assertEqual(d["toplam"],
                         {"banks": 0, "campaigns": 0, "types": 0})

    def test_sorgu_parametresiz_de_calisir(self) -> None:
        r = self.client.get("/search")
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(r.json()["toplam"]["campaigns"], 0)

    def test_negatif_limit_400(self) -> None:
        self.assertEqual(
            self.client.get("/search", params={"q": "a", "limit": -1})
            .status_code, 400)

    def test_limit_tavani(self) -> None:
        d = self._ara(q="finansmani", limit=10_000)
        self.assertLessEqual(len(d["campaigns"]), ARAMA_AZAMI_LIMIT)

    def test_varsayilan_limit_sozlesmede(self) -> None:
        self.assertGreater(ARAMA_VARSAYILAN_LIMIT, 0)
        self.assertLessEqual(ARAMA_VARSAYILAN_LIMIT, ARAMA_AZAMI_LIMIT)


if __name__ == "__main__":
    unittest.main()
