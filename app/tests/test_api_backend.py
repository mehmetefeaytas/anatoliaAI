"""API'nin veri tabanından BAĞIMSIZ olduğunu uçlar üzerinden kanıtlar.

İlgili: src/api/main.py, src/db/factory.py (create_repository)
        tests/test_repo_parity.py (depo seviyesi parite + thread güvenliği)
        tests/test_api_startup.py (koşullu tohumlama, SQLite yolu)
        docs/veri-katmani.md

## Neden bu dosya var

`tests/test_repo_parity.py` DEPO seviyesinde pariteyi kilitler. Ama asıl iddia
API seviyesindedir: *"`DATABASE_URL` verirsen sistem Postgres'te, vermezsen
SQLite'ta AYNI cevabı verir."* 31 Tem 2026'ya kadar bu iddia **yanlıştı**:
`src/api/main.py` `Repository(DATABASE_PATH)` kuruyor ve beş yerde `?` yer
tutuculu ham SQL koşuyordu; `DATABASE_URL` verilse bile okunmuyordu, verilse ve
okunsa Postgres'te `ProgrammingError` ile düşerdi.

Bu dosya iki şeyi ölçer:

1. **Uç bazında parite** (Postgres GEREKİR, yoksa ATLANIR): AYNI korpus iki
   backend'e yazılır, uygulama İKİ KEZ kurulur, `/health` `/banks` `/campaigns`
   `/campaigns/{id}/text` `/compare` `/scoring` `/contradictions` `/chat`
   yanıtları karşılaştırılır.
2. **Koşullu tohumlama** İKİ backend'de de çalışıyor mu: dolu bir DB'ye
   fixture verisi EKLENMEMELİ (kalıcı hacimde her yeniden başlatma korpusu
   çiftlerdi).

`TestClient` bilinçli olarak kullanılır: uçları FastAPI'nin threadpool'unda
koşturur, yani thread güvenliği düzeltmesi de gerçek yolda sınanır.
"""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.db.repository import Repository
from src.schemas import Campaign

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_repo_parity import CORPUS, _postgres_reachable, reset_pg, seed

# Çekirdek paket SIFIR üçüncü parti bağımlılıkla koşar (on-prem iddiasının
# parçası). fastapi/httpx yoksa bu dosya ATLANIR, başarısız OLMAZ.
try:  # pragma: no cover - ortama bağlı
    import httpx  # noqa: F401
    from fastapi.testclient import TestClient
    HAS_API = True
except ModuleNotFoundError:  # pragma: no cover
    HAS_API = False

_PG_OK, _PG_REASON = _postgres_reachable()

requires_api = unittest.skipUnless(HAS_API, "fastapi/httpx yok — API testi atlanıyor")
requires_pg = unittest.skipUnless(_PG_OK, f"Postgres yok — {_PG_REASON}")

# `scraped_at` yalnız Postgres'te TIMESTAMPTZ'e yazılıp geri okunur; parite
# testinin kendisi bunu kilitliyor (tests/test_repo_parity.py). Burada
# karşılaştırmadan çıkarılan tek şey `campaign_id`/`id` DEĞİL — iki DB de
# boştan başladığı için id'ler bile eşleşmek zorunda.


def _build_app(*, database_url: str = "", database_path: str = ":memory:"):
    """`build_app()`'i verilen backend ayarlarıyla kurar.

    `DATABASE_URL` `create_repository()` içinde ORTAMDAN okunur, `DB_PATH` ise
    modül seviyesinde sabitlenir — bu yüzden ikisi farklı biçimde ayarlanır.
    Modül yeniden import EDİLMEZ (import anında `app = build_app()` koşar ve
    her seferinde yeni bir depo açardı); `DB_PATH` global'i geçici olarak
    değiştirilir.
    """
    from src.api import main as api_main

    onceki_url = os.environ.get("DATABASE_URL")
    onceki_path = api_main.DB_PATH
    if database_url:
        os.environ["DATABASE_URL"] = database_url
    else:
        os.environ.pop("DATABASE_URL", None)
    api_main.DB_PATH = database_path
    try:
        return api_main.build_app()
    finally:
        api_main.DB_PATH = onceki_path
        if onceki_url is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = onceki_url


def _get(app, yol: str, **params: Any) -> Any:
    with TestClient(app) as c:
        r = c.get(yol, params=params)
        r.raise_for_status()
        return r.json()


def _post(app, yol: str, govde: dict) -> Any:
    with TestClient(app) as c:
        r = c.post(yol, json=govde)
        r.raise_for_status()
        return r.json()


@requires_api
class TestSqliteYolu(unittest.TestCase):
    """DATABASE_URL yoksa SQLite — ve uçlar gerçekten veri döndürür."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.path = str(Path(self._tmp.name) / "api.db")
        repo = Repository(self.path)
        seed(repo)
        repo.close()
        self.app = _build_app(database_path=self.path)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_health_backend_bildirir(self) -> None:
        self.assertEqual(_get(self.app, "/health")["backend"], "sqlite")

    def test_banks_dolu_ve_bool(self) -> None:
        rows = _get(self.app, "/banks")
        self.assertEqual([r["slug"] for r in rows],
                         ["albaraka", "kuveyt-turk", "vakif-katilim"])
        self.assertIsInstance(rows[0]["bddk_active"], bool)

    def test_campaigns_dolu(self) -> None:
        rows = _get(self.app, "/campaigns")
        self.assertEqual(len(rows), len(CORPUS))
        self.assertEqual([r["bank"] for r in rows], [c[0] for c in CORPUS])

    def test_campaign_text_saklanan_offseti_kullanir(self) -> None:
        d = _get(self.app, "/campaigns/1/text")
        self.assertEqual(d["span_reference"], "clean_text")
        self.assertTrue(d["fields"])
        dogrulanan = [f for f in d["fields"] if f["span_verified"]]
        self.assertTrue(dogrulanan, "hiç doğrulanmış span yok")
        for f in dogrulanan:
            self.assertEqual(d["text"][f["span_start"]:f["span_end"]],
                             f["raw_value"])
        # `confidence_source` artık DB'den okunuyor (yeniden çıkarımdan değil).
        self.assertTrue(any(f["confidence_source"] for f in d["fields"]),
                        "confidence_source hiçbir alanda dolu değil")

    def test_compare_calisiyor(self) -> None:
        rows = _get(self.app, "/compare", field="kar_payi_orani", intent="lowest")
        self.assertTrue(rows)
        siralanan = [r for r in rows if r["rank"] is not None]
        self.assertEqual([r["sort_key"] for r in siralanan],
                         sorted(r["sort_key"] for r in siralanan))

    def test_olmayan_kampanya_404(self) -> None:
        with TestClient(self.app) as c:
            self.assertEqual(c.get("/campaigns/99999/text").status_code, 404)


@requires_api
@requires_pg
class TestIkiBackendUcParitesi(unittest.TestCase):
    """AYNI korpus, iki backend, uçlardan AYNI JSON."""

    @classmethod
    def setUpClass(cls) -> None:
        from src.db.postgres import PostgresRepository
        cls.dsn = os.environ["ANATOLIA_TEST_DATABASE_URL"].strip()
        pg = PostgresRepository(cls.dsn)
        reset_pg(pg.conn)
        pg.ensure_schema()
        seed(pg)
        pg.close()

        cls._tmp = tempfile.TemporaryDirectory()
        cls.path = str(Path(cls._tmp.name) / "api.db")
        lite = Repository(cls.path)
        seed(lite)
        lite.close()

        cls.app_pg = _build_app(database_url=cls.dsn)
        cls.app_lite = _build_app(database_path=cls.path)

    @classmethod
    def tearDownClass(cls) -> None:
        from src.db.postgres import PostgresRepository
        pg = PostgresRepository(cls.dsn, ensure_schema=False)
        reset_pg(pg.conn)
        pg.close()
        cls._tmp.cleanup()

    def test_dogru_backendler_secildi(self) -> None:
        """Test kendini kandırmasın: iki uygulama GERÇEKTEN farklı DB'de."""
        self.assertEqual(_get(self.app_pg, "/health")["backend"], "postgres")
        self.assertEqual(_get(self.app_lite, "/health")["backend"], "sqlite")

    def _esit(self, yol: str, **params: Any) -> Any:
        pg = _get(self.app_pg, yol, **params)
        lite = _get(self.app_lite, yol, **params)
        self.assertEqual(pg, lite, f"{yol} iki backend'de farklı")
        return pg

    def test_banks(self) -> None:
        self.assertTrue(self._esit("/banks"))

    def test_campaigns(self) -> None:
        rows = self._esit("/campaigns")
        self.assertEqual(len(rows), len(CORPUS))

    def test_campaign_text(self) -> None:
        for cid in (1, 2, 3):
            with self.subTest(campaign_id=cid):
                d = self._esit(f"/campaigns/{cid}/text")
                self.assertTrue(d["text"])

    def test_compare_tum_alanlar(self) -> None:
        for alan in ("kar_payi_orani", "vade_ay", "masraf_durumu",
                     "kampanya_kosullari"):
            for niyet in (None, "lowest", "highest"):
                with self.subTest(field=alan, intent=niyet):
                    params = {"field": alan}
                    if niyet:
                        params["intent"] = niyet
                    self._esit("/compare", **params)

    def test_compare_tur_suzgeci(self) -> None:
        self._esit("/compare", field="vade_ay", type="Konut Finansmanı")

    def test_scoring(self) -> None:
        self.assertTrue(self._esit("/scoring", field="kar_payi_orani")["rows"])

    def test_fields(self) -> None:
        self.assertEqual(len(self._esit("/fields")), 12)

    def test_contradictions(self) -> None:
        self._esit("/contradictions")
        ozet = self._esit("/contradictions/summary")
        self.assertEqual(ozet["scanned_campaigns"], len(CORPUS))

    def test_chat(self) -> None:
        for soru in ("en düşük kâr payı hangi bankada",
                     "36 ay vade veren konut finansmanları",
                     "tahsis ücreti alınmayan kampanyalar"):
            with self.subTest(soru=soru):
                pg = _post(self.app_pg, "/chat", {"question": soru})
                lite = _post(self.app_lite, "/chat", {"question": soru})
                self.assertEqual(pg, lite, f"/chat farklı: {soru}")
                self.assertTrue(pg["answer"])

    def test_extract_backendden_bagimsiz(self) -> None:
        """Canlı çıkarım DB'ye dokunmaz; yine de iki kurulumda aynı olmalı."""
        govde = {"text": "Konut finansmanında kâr payı %1,45, 60 ay vade.",
                 "bank": "test"}
        self.assertEqual(_post(self.app_pg, "/extract", govde),
                         _post(self.app_lite, "/extract", govde))


@requires_api
@requires_pg
class TestPostgresKosulluTohumlama(unittest.TestCase):
    """Koşullu tohumlama Postgres yolunda da çalışmalı.

    `DATABASE_PATH` SQLite tarafında bu hatayı vermişti (849 -> 852 -> 855).
    Postgres tarafında risk daha büyük: `pgdata` KALICI bir Docker hacmidir,
    yani her `docker compose --profile postgres up` aynı veriyi bulur.
    """

    def setUp(self) -> None:
        from src.db.postgres import PostgresRepository
        self.dsn = os.environ["ANATOLIA_TEST_DATABASE_URL"].strip()
        self.pg = PostgresRepository(self.dsn)
        reset_pg(self.pg.conn)
        self.pg.ensure_schema()

    def tearDown(self) -> None:
        reset_pg(self.pg.conn)
        self.pg.close()

    def _sayi(self) -> int:
        return self.pg.counts()["campaigns"]

    def test_bos_db_tohumlanir(self) -> None:
        self.assertEqual(self._sayi(), 0)
        _build_app(database_url=self.dsn)
        self.assertGreater(self._sayi(), 0,
                           "boş Postgres tohumlanmadı — demo boş açılırdı")

    def test_yeniden_baslatma_ciftlemez(self) -> None:
        _build_app(database_url=self.dsn)
        ilk = self._sayi()
        self.assertGreater(ilk, 0)
        for tur in (2, 3):
            _build_app(database_url=self.dsn)
            with self.subTest(acilis=tur):
                self.assertEqual(self._sayi(), ilk,
                                 f"{tur}. açılışta kampanya sayısı değişti")

    def test_dolu_db_tohumlanmaz(self) -> None:
        self.pg.insert_campaign(
            Campaign(bank_slug="onceden-dolu", raw_text="hazır veri",
                     source_url="https://ornek.test/x", fields=[]),
            clean_text="hazır veri")
        onceki = self._sayi()
        _build_app(database_url=self.dsn)
        self.assertEqual(self._sayi(), onceki,
                         "dolu Postgres'e fixture verisi eklendi")


class TestSkipGorunurlugu(unittest.TestCase):
    """Atlanıyorsa SEBEBİ raporlanabilir olmalı."""

    def test_sebep_bos_degil(self) -> None:
        self.assertTrue(_PG_OK or _PG_REASON)
        self.assertIsInstance(HAS_API, bool)


if __name__ == "__main__":
    unittest.main()
