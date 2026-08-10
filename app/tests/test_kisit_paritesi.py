"""Kısıt paritesi: iki backend AYNI veriyi kabul etmeli, AYNI veriyi reddetmeli.

İlgili: ../src/db/base.py (`extractor_dogrula`, `nul_denetle` — tek doğrulama
            noktaları)
        ../src/db/repository.py (SQLite), ../src/db/postgres.py (Postgres)
        ../src/db/schema.sql (Postgres CHECK metni)
        test_goc_listesi_paritesi.py (aynı hata sınıfının göç listesi hâli)

## Bu testin varlık sebebi

`test_goc_listesi_paritesi.py` bu depoda tekrarlayan bir hata sınıfını kapıya
bağladı: aynı bilgi iki yerde yaşayınca biri güncelleniyor, öteki unutuluyor.
Bu dosya aynı sınıfın KISIT tarafını bağlar; iki delik ölçüldü (2026-08-10):

1. **`extractor` CHECK kısıtı taze DB'ye ulaşıyor, diskteki DB'ye ulaşmıyor.**
   Kısıt iki şemada da `CREATE TABLE` içinde. Zaten var olan bir veri tabanında
   `CREATE TABLE IF NOT EXISTS` hiçbir şey yapmaz ve göç yolu yalnız
   `ADD COLUMN` bilir; SQLite `ALTER TABLE` ile CHECK eklemeye zaten izin
   vermez. Ölçüm: teslim edilen `data/demo.db` sütunu `extractor TEXT` olarak
   KISITSIZ taşıyor; geçici bir kopyasına `extractor='UYDURMA'` yazılabildi ve
   `Repository(...)` ile açıp göç koşturmak şemayı ONARMADI.

   Yani parite iki backend arasında değil, **taze DB ile diskteki DB** arasında
   delinmişti — ve teslim edilen dosya yanlış taraftaydı.

2. **NUL (0x00) denetimi yalnız Postgres'te vardı.** SQLite NUL saklar,
   PostgreSQL saklamaz. Denetimin tek backend'de yaşaması iddiayı TERSİNDEN
   deliyordu: offline yolda (SQLite) sorunsuz kurulan bir korpus üretime
   (Postgres) göç ederken düşüyordu, üstelik hata kaynağı düzeltmenin en
   pahalı olduğu anda çıkıyordu.

Her iki delik de `base.belge_turu_dogrula()`'nın zaten yazılı olan gerekçesiyle
kapatıldı: **şema kısıtı ikinci savunmadır, sözleşme Python'daki tek doğrulama
noktasıdır.** Bu dosya o noktanın gerçekten tek ve gerçekten zorunlu olduğunu
denetler.

## Postgres neden burada koşmuyor

Bu testler `psycopg` VEYA erişilebilir bir Postgres İSTEMEZ: doğrulama artık
`base.py`'de, yani motordan bağımsız olarak koşturulabiliyor. Paritenin canlı
Postgres'e karşı ölçümü `test_pgvector_repository.py`'dedir (ön koşul yoksa
atlanır). Doğrulamayı ortak bir yere taşımanın kazancı tam olarak budur:
kural, kuralın uygulandığı motora erişmeden denetlenebilir hâle geldi.
"""

from __future__ import annotations

import inspect
import re
import sqlite3
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.db.base import (
    EXTRACTOR_DEGERLERI,
    ON_NUL_MODES,
    NulByteInText,
    extractor_dogrula,
    nul_denetle,
    on_nul_dogrula,
)
from src.db.postgres import SCHEMA_PATH, PostgresRepository
from src.db.repository import _SQLITE_SCHEMA, Repository
from src.schemas import Campaign, ExtractedField, Extractor

# `extracted_fields.extractor` sütununun CHECK ifadesindeki tırnaklı değerler.
_CHECK_RE = re.compile(r"extractor\s+TEXT\s+CHECK\s*\((.*?)\)\s*,", re.S | re.I)


def _check_degerleri(sema_metni: str) -> set[str]:
    """Şema metnindeki `extractor` CHECK ifadesinden kabul edilen değerler."""
    m = _CHECK_RE.search(sema_metni)
    if m is None:
        raise AssertionError(
            "şemada `extractor ... CHECK (...)` bulunamadı — kısıt kaldırıldıysa "
            "bu testin gerekçesi de gözden geçirilmeli")
    return set(re.findall(r"'([^']*)'", m.group(1)))


def _alan(extractor: Extractor | str = Extractor.RULE,
          raw_value: str = "%2,49") -> ExtractedField:
    return ExtractedField(
        field_name="kar_payi_orani", raw_value=raw_value, canonical_value=2.49,
        confidence=0.9, source_span="kâr payı %2,49", extractor=extractor)


def _kampanya(alanlar: list[ExtractedField] | None = None,
              raw_text: str = "Kâr payı %2,49, 36 ay vade.") -> Campaign:
    return Campaign(bank_slug="kuveyt-turk", raw_text=raw_text,
                    source_url="https://example.test/k",
                    campaign_type="Konut Finansmanı",
                    fields=alanlar if alanlar is not None else [_alan()])


class TestExtractorTekDogrulamaNoktasi(unittest.TestCase):
    """`base.extractor_dogrula()` sözleşmenin tamamını taşıyor mu?"""

    def test_gecerli_degerler_gecer(self) -> None:
        for deger in EXTRACTOR_DEGERLERI:
            with self.subTest(deger=deger):
                self.assertEqual(extractor_dogrula(deger), deger)

    def test_enum_uyesi_de_kabul_edilir(self) -> None:
        """Çağıran `Extractor.RULE` geçebilmeli; `.value` ÇAĞIRANDA çözülmesin."""
        for uye in Extractor:
            with self.subTest(uye=uye):
                self.assertEqual(extractor_dogrula(uye), uye.value)

    def test_none_gecerlidir(self) -> None:
        """Sütunu sonradan eklenmiş DB'deki eski satırlar NULL taşır."""
        self.assertIsNone(extractor_dogrula(None))

    def test_gecersiz_deger_reddedilir(self) -> None:
        for deger in ("UYDURMA", "RULE", "rule ", "", "regex"):
            with self.subTest(deger=deger):
                with self.assertRaises(ValueError):
                    extractor_dogrula(deger)

    def test_hata_mesaji_gecerli_kumeyi_soyluyor(self) -> None:
        """Kriptik hata, düzeltilmeyen hatadır."""
        with self.assertRaises(ValueError) as ctx:
            extractor_dogrula("UYDURMA")
        mesaj = str(ctx.exception)
        for deger in EXTRACTOR_DEGERLERI:
            self.assertIn(deger, mesaj)

    def test_gecerli_kume_enumdan_turetilmis(self) -> None:
        """Elle yazılmış bir kopya olsaydı enum'a yeni katman eklendiğinde ayrışırdı."""
        self.assertEqual(set(EXTRACTOR_DEGERLERI), {e.value for e in Extractor})


class TestCheckMetinleriEnumIleUyusuyor(unittest.TestCase):
    """Aynı liste ÜÇ yerde yaşıyor: enum + iki şema. Ayrışmasınlar.

    Kısıtı ikinci savunma olarak TUTUYORUZ (taze DB'lerde ham SQL yazanları
    bedava yakalar). İkinci savunmanın yanlış kümeyi savunması, hiç savunmamaktan
    daha kötüdür: `Extractor`e yeni bir katman eklendiğinde CHECK onu reddeder
    ve hata veri tabanı sınırında, alakasız bir yerde patlar.
    """

    def test_sqlite_check_enum_ile_ayni(self) -> None:
        self.assertEqual(_check_degerleri(_SQLITE_SCHEMA),
                         set(EXTRACTOR_DEGERLERI))

    def test_postgres_check_enum_ile_ayni(self) -> None:
        sema = SCHEMA_PATH.read_text(encoding="utf-8")
        self.assertEqual(_check_degerleri(sema), set(EXTRACTOR_DEGERLERI))

    def test_iki_sema_ayni_kumeyi_kabul_ediyor(self) -> None:
        sema = SCHEMA_PATH.read_text(encoding="utf-8")
        self.assertEqual(_check_degerleri(_SQLITE_SCHEMA),
                         _check_degerleri(sema))


class TestKisitDiskteKiDByeUlasmiyor(unittest.TestCase):
    """ÖLÇÜLEN DELİK — geri gelmesin diye kilitleniyor.

    Buradaki testler kısıtın eksikliğini bir KUSUR olarak değil, bir GERÇEK
    olarak sabitler: SQLite'ta sonradan CHECK eklenemez, dolayısıyla diskteki
    `data/demo.db` bu kısıtı asla taşımayacak. Sözleşmenin buna rağmen ayakta
    kaldığını ispatlamak bu sınıfın işidir.
    """

    def _eski_db(self, yol: Path) -> None:
        """`data/demo.db` ile aynı biçimde, CHECK'SİZ bir DB kurar."""
        con = sqlite3.connect(yol)
        con.executescript("""
            CREATE TABLE banks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL, slug TEXT UNIQUE NOT NULL,
                website_url TEXT, bddk_active INTEGER DEFAULT 1);
            CREATE TABLE campaigns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                bank_id INTEGER, raw_text TEXT NOT NULL, clean_text TEXT,
                source_url TEXT, scraped_at TEXT, campaign_type TEXT);
            CREATE TABLE extracted_fields (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                campaign_id INTEGER, field_name TEXT NOT NULL, raw_value TEXT,
                canonical_value TEXT, confidence REAL, source_span TEXT,
                extractor TEXT);
        """)
        con.commit()
        con.close()

    def test_taze_db_kisiti_TASIR(self) -> None:
        """Kontrol grubu: sıfırdan kurulan DB'de CHECK gerçekten çalışıyor."""
        repo = Repository(":memory:")
        try:
            with self.assertRaises(sqlite3.IntegrityError):
                repo.conn.execute(
                    "INSERT INTO extracted_fields(campaign_id, field_name, "
                    "canonical_value, extractor) VALUES (1,'x','1.0','UYDURMA')")
        finally:
            repo.close()

    def test_eski_db_goc_sonrasi_da_kisiti_TASIMAZ(self) -> None:
        """Ölçülen gerçek: göç şemayı onaramaz (SQLite ADD CONSTRAINT yok)."""
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            yol = Path(d) / "eski.db"
            self._eski_db(yol)
            repo = Repository(str(yol))
            try:
                sema = repo.conn.execute(
                    "SELECT sql FROM sqlite_master "
                    "WHERE name='extracted_fields'").fetchone()[0]
                self.assertNotIn(
                    "CHECK", sema.upper(),
                    "beklenmedik: SQLite göçü CHECK ekleyebilmiş — bu testin "
                    "dayandığı kısıt ortadan kalkmış olabilir")
            finally:
                repo.close()

    def test_kisit_olmasa_da_UYGULAMA_reddediyor(self) -> None:
        """ASIL GARANTİ: şema susuyor ama `insert_campaign()` susmuyor."""
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            yol = Path(d) / "eski.db"
            self._eski_db(yol)
            repo = Repository(str(yol))
            try:
                with self.assertRaises(ValueError):
                    repo.insert_campaign(_kampanya([_alan(extractor="UYDURMA")]))
            finally:
                repo.close()

    def test_reddedilen_kampanya_YARIM_yazilmaz(self) -> None:
        """Doğrulama yazmadan ÖNCE koşmalı; yoksa satırı olan alansız kampanya kalır."""
        repo = Repository(":memory:")
        try:
            with self.assertRaises(ValueError):
                repo.insert_campaign(_kampanya(
                    [_alan(), _alan(extractor="UYDURMA")]))
            self.assertEqual(repo.counts()["campaigns"], 0,
                             "geçersiz alan reddedildi ama kampanya satırı yazılmış")
            self.assertEqual(repo.counts()["fields"], 0)
        finally:
            repo.close()

    def test_gecerli_kampanya_hala_yazilabiliyor(self) -> None:
        """Doğrulama yalnız geçersizi elemeli; kontrol grubu."""
        repo = Repository(":memory:")
        try:
            cid = repo.insert_campaign(_kampanya())
            self.assertEqual(repo.counts()["campaigns"], 1)
            self.assertEqual(
                repo.campaign_text(cid)["fields"][0]["extractor"], "rule")
        finally:
            repo.close()


class TestNulParitesi(unittest.TestCase):
    """NUL denetimi iki backend'de AYNI — mantık `base.nul_denetle()`."""

    def test_error_kipinde_reddedilir(self) -> None:
        with self.assertRaises(NulByteInText):
            nul_denetle("bo\x00zuk", "ozet", "test")

    def test_strip_kipinde_temizlenir_ve_uyarilir(self) -> None:
        with self.assertLogs("src.db.base", level="WARNING") as kayit:
            self.assertEqual(
                nul_denetle("bo\x00zuk", "ozet", "test", on_nul="strip"),
                "bozuk")
        self.assertIn("NUL", "".join(kayit.output))

    def test_temiz_metin_dokunulmadan_doner(self) -> None:
        self.assertEqual(nul_denetle("temiz", "ozet", "test"), "temiz")
        self.assertIsNone(nul_denetle(None, "ozet", "test"))

    def test_gecersiz_kip_reddedilir(self) -> None:
        with self.assertRaises(ValueError):
            on_nul_dogrula("yoksay")

    def test_sqlite_set_ozet_NUL_reddediyor(self) -> None:
        """Ölçülen delik #2: bu denetim yalnız Postgres'te vardı."""
        repo = Repository(":memory:")
        try:
            cid = repo.insert_campaign(_kampanya())
            with self.assertRaises(NulByteInText):
                repo.set_ozet({cid: "özet\x00metni"})
        finally:
            repo.close()

    def test_sqlite_insert_campaign_NUL_reddediyor(self) -> None:
        repo = Repository(":memory:")
        try:
            with self.assertRaises(NulByteInText):
                repo.insert_campaign(_kampanya(raw_text="ikili\x00cop"))
            self.assertEqual(repo.counts()["campaigns"], 0)
        finally:
            repo.close()

    def test_sqlite_strip_kipi_calisiyor(self) -> None:
        """Kaçış kapısı iki backend'de de durmalı."""
        repo = Repository(":memory:", on_nul="strip")
        try:
            cid = repo.insert_campaign(_kampanya())
            with self.assertLogs("src.db.base", level="WARNING"):
                repo.set_ozet({cid: "özet\x00metni"})
            self.assertEqual(repo.campaign_text(cid)["ozet"], "özetmetni")
        finally:
            repo.close()

    def test_sqlite_gecersiz_on_nul_kipi_reddedilir(self) -> None:
        with self.assertRaises(ValueError):
            Repository(":memory:", on_nul="yoksay")


class TestSozlesmeYuzeyiAyni(unittest.TestCase):
    """İki depo `on_nul`u aynı ADLA, aynı KİPLE, aynı VARSAYILANLA sunmalı.

    Ad veya varsayılan ayrışsaydı, `factory.create_repository()` üzerinden gelen
    çağıran hangi backend'e düştüğüne göre farklı bir politika alırdı — parite
    iddiasının sessizce delindiği tam da böyle yerlerdir.
    """

    def _on_nul_varsayilani(self, sinif) -> object:
        return inspect.signature(sinif.__init__).parameters["on_nul"].default

    def test_iki_backend_de_on_nul_aliyor(self) -> None:
        for sinif in (Repository, PostgresRepository):
            with self.subTest(backend=sinif.__name__):
                self.assertIn("on_nul",
                              inspect.signature(sinif.__init__).parameters)

    def test_varsayilan_ayni(self) -> None:
        self.assertEqual(self._on_nul_varsayilani(Repository),
                         self._on_nul_varsayilani(PostgresRepository))
        self.assertEqual(self._on_nul_varsayilani(Repository), "error")

    def test_kip_kumesi_tek_yerde(self) -> None:
        """`ON_NUL_MODES` ve `NulByteInText` YALNIZ `base`'te tanımlı olmalı.

        Nesne KİMLİĞİ (`assertIs`) denetlenmiyor: bu depoda testler `sys.path`e
        farklı kökler ekliyor ve aynı modül iki adla yüklenebiliyor, o zaman
        değerler eşit ama nesneler ayrı olur — kimlik denetimi gerçek bir
        ayrışma olmadan da düşerdi (ölçüldü: tek başına geçen test `discover`
        altında düşüyordu).

        Onun yerine KURALIN KENDİSİ denetleniyor: değerler eşit VE `postgres.py`
        kendi kopyasını TANIMLAMIYOR. Asıl kusur zaten buydu — denetim iki yerde
        yaşayınca biri güncellenip öteki unutuluyordu.
        """
        from src.db import postgres

        self.assertEqual(postgres.ON_NUL_MODES, ON_NUL_MODES)
        self.assertEqual(postgres.NulByteInText.__name__,
                         NulByteInText.__name__)

        kaynak = Path(postgres.__file__).read_text(encoding="utf-8")
        self.assertNotRegex(
            kaynak, r"(?m)^ON_NUL_MODES\s*=",
            "postgres.py kendi `ON_NUL_MODES` kopyasını tanımlıyor — kip kümesi "
            "iki yerde yaşarsa ayrışır (bkz. base.nul_denetle)")
        self.assertNotRegex(
            kaynak, r"(?m)^class\s+NulByteInText\b",
            "postgres.py kendi `NulByteInText` kopyasını tanımlıyor — SQLite "
            "yolunun fırlattığı istisna farklı bir sınıf olurdu ve çağıranların "
            "`except` blokları sessizce ıskalardı")


if __name__ == "__main__":
    unittest.main()
