"""Alfabesi kaymış özetlerin temizliği — yeniden üret, olmazsa `NULL`.

İlgili: ../scripts/ozet_dil_temizligi.py, ../src/summarize/ozet.py

## Bu testin varlık sebebi

Kirli bir özeti "düzeltmenin" en kolay yolu kaymış harfleri silmektir ve o yol
YASAK: kalan metin artık modelin yazdığı metin değildir ama ekranda hâlâ "AI
özeti" etiketiyle durur. Buradaki testler, betiğin yalnızca iki dürüst sonucu
üretebildiğini kilitler — kapıdan geçen yeni bir özet ya da `NULL`.

İkinci kilit sonsuz döngüye karşıdır: yerel model varsayılan sıcaklıkta
belirlenimci çalışır, yani aynı belgeyi aynı sıcaklıkta tekrar sormak
bayt-aynı kirli çıktıyı geri getirir. Denemeler hem sıcaklığı yükseltmeli hem
de sabit bir tavanda durmalı.
"""

from __future__ import annotations

import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import ozet_dil_temizligi as T

KIRLI = "Kuveyt Türk müşterisine 500 TL iade提供的优惠活动。"
TEMIZ = "Kuveyt Türk müşterisine 500 TL nakit iade sağlanıyor."


class _Istemci:
    """Belirli sayıda kirli çıktı verip sonra temize dönen sahte istemci.

    `temiz_deneme=None` = hiç temizlenmez (model o belgede ısrarla kayıyor).
    Çağrı anındaki sıcaklık KAYDEDİLİR: merdivenin gerçekten uygulandığını
    rapordan değil, istemcinin gördüğü değerden doğrularız.
    """

    def __init__(self, temiz_deneme: int | None = None):
        self.temiz_deneme = temiz_deneme
        self.cagri = 0
        self.temperature = 0.0
        self.sicakliklar: list[float] = []

    def generate_json(self, system: str, user: str, schema: dict) -> dict:
        self.cagri += 1
        # `getattr`: sıcaklık ayarı olmayan istemci senaryosu (aşağıda `del`)
        # burada `AttributeError` atıp koşuyu sahte bir "llm_hatasi"na çevirmesin.
        self.sicakliklar.append(getattr(self, "temperature", None))
        if self.temiz_deneme is not None and self.cagri >= self.temiz_deneme:
            return {"ozet": TEMIZ}
        return {"ozet": KIRLI}


class _LLM:
    def __init__(self, temiz_deneme: int | None = None):
        self.available = True
        self.client = _Istemci(temiz_deneme)


def _db_kur(yol: Path, ozetler: list[str | None]) -> None:
    """`all_campaigns()` `banks` ile JOIN yapıyor — iki tablo da gerekli."""
    conn = sqlite3.connect(yol)
    conn.executescript("""
        CREATE TABLE banks (id INTEGER PRIMARY KEY, slug TEXT, name TEXT);
        CREATE TABLE campaigns (
            id INTEGER PRIMARY KEY, bank_id INTEGER, raw_text TEXT,
            clean_text TEXT, source_url TEXT, scraped_at TEXT,
            campaign_type TEXT, belge_turu TEXT, ozet TEXT
        );
        INSERT INTO banks (id, slug, name)
            VALUES (1, 'test-katilim', 'Test Katılım');
    """)
    conn.executemany(
        "INSERT INTO campaigns (id, bank_id, raw_text, belge_turu, ozet) "
        "VALUES (?, 1, ?, 'kampanya', ?)",
        [(i, f"Konut finansmanı kampanyası {i}. Kâr payı oranı %2,05.", oz)
         for i, oz in enumerate(ozetler, start=1)])
    conn.commit()
    conn.close()


def _ozet(yol: Path, kimlik: int):
    conn = sqlite3.connect(yol)
    try:
        return conn.execute("SELECT ozet FROM campaigns WHERE id=?",
                            (kimlik,)).fetchone()[0]
    finally:
        conn.close()


class _Temel(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.db = Path(self._tmp.name) / "t.db"

    def tearDown(self) -> None:
        self._tmp.cleanup()


class TestTarama(_Temel):
    """Yalnız kirli kayıtlar seçilmeli; temiz olan ELLENMEMELİ."""

    def test_kirli_ve_temiz_ayrilir(self) -> None:
        _db_kur(self.db, [TEMIZ, KIRLI, None, "", TEMIZ])
        from src.db.repository import Repository

        repo = Repository(str(self.db))
        try:
            kirli = T.kirli_kayitlar(repo)
        finally:
            repo.close()
        self.assertEqual([k["id"] for k in kirli], [2])
        self.assertIn("提", kirli[0]["disari"])

    def test_kuru_kosu_veri_tabanina_dokunmaz(self) -> None:
        _db_kur(self.db, [KIRLI, TEMIZ])
        rapor = T.calistir(str(self.db), kuru=True, yalniz_null=True, parca=1)
        self.assertEqual(rapor["kirli_ozet"], 1)
        self.assertEqual(rapor["yazilan"], 0)
        self.assertEqual(_ozet(self.db, 1), KIRLI)


class TestYenidenUretim(_Temel):
    """Model temiz bir özet verirse o yazılır; veremezse kayıt silinir."""

    def test_ilk_denemede_temizlenirse_yazilir(self) -> None:
        _db_kur(self.db, [KIRLI])
        llm = _LLM(temiz_deneme=1)
        rapor = T.calistir(str(self.db), llm=llm, parca=1)
        self.assertEqual(rapor["yeniden_uretilen"], 1)
        self.assertEqual(rapor["null_cekilen"], 0)
        self.assertEqual(_ozet(self.db, 1), TEMIZ)

    def test_ikinci_denemede_temizlenirse_yazilir(self) -> None:
        _db_kur(self.db, [KIRLI])
        llm = _LLM(temiz_deneme=2)
        rapor = T.calistir(str(self.db), llm=llm, parca=1)
        self.assertEqual(rapor["yeniden_uretilen"], 1)
        self.assertEqual(_ozet(self.db, 1), TEMIZ)
        self.assertEqual(rapor["deneme_dagilimi"], {"2. denemede": 1})

    def test_israrla_kirliyse_null_yazilir(self) -> None:
        """Kirli metin KORUNMAZ ve ONARILMAZ — silinir."""
        _db_kur(self.db, [KIRLI])
        llm = _LLM(temiz_deneme=None)
        rapor = T.calistir(str(self.db), llm=llm, parca=1)
        self.assertEqual(rapor["yeniden_uretilen"], 0)
        self.assertEqual(rapor["null_cekilen"], 1)
        self.assertIsNone(_ozet(self.db, 1))

    def test_kirli_metnin_hicbir_parcasi_yazilmaz(self) -> None:
        _db_kur(self.db, [KIRLI])
        T.calistir(str(self.db), llm=_LLM(temiz_deneme=None), parca=1)
        self.assertIsNone(_ozet(self.db, 1))

    def test_temiz_kayit_yeniden_uretilmez(self) -> None:
        """Sağlam özet için model HİÇ çağrılmamalı — 1751 belge, 4 saat."""
        _db_kur(self.db, [TEMIZ, TEMIZ])
        llm = _LLM(temiz_deneme=1)
        rapor = T.calistir(str(self.db), llm=llm, parca=1)
        self.assertEqual(rapor["kirli_ozet"], 0)
        self.assertEqual(llm.client.cagri, 0)


class TestDongueYok(_Temel):
    """Tavan sabit, sıcaklık merdiveni gerçekten uygulanıyor."""

    def test_deneme_tavani_asilmaz(self) -> None:
        _db_kur(self.db, [KIRLI])
        llm = _LLM(temiz_deneme=None)
        T.calistir(str(self.db), llm=llm, denemeler=3, parca=1)
        self.assertEqual(llm.client.cagri, 3)

    def test_sicaklik_her_denemede_yukselir(self) -> None:
        """0.0'da tekrar sormak bayt-aynı kirli çıktıyı geri getirirdi."""
        _db_kur(self.db, [KIRLI])
        llm = _LLM(temiz_deneme=None)
        T.calistir(str(self.db), llm=llm, denemeler=3, parca=1)
        self.assertEqual(llm.client.sicakliklar, list(T.SICAKLIK_MERDIVENI))

    def test_sicaklik_kosu_sonunda_geri_alinir(self) -> None:
        """Betik istemcinin ayarını kalıcı olarak değiştirmemeli."""
        _db_kur(self.db, [KIRLI])
        llm = _LLM(temiz_deneme=None)
        llm.client.temperature = 0.0
        T.calistir(str(self.db), llm=llm, denemeler=3, parca=1)
        self.assertEqual(llm.client.temperature, 0.0)

    def test_sicakligi_olmayan_istemcide_de_kosar(self) -> None:
        _db_kur(self.db, [KIRLI])
        llm = _LLM(temiz_deneme=2)
        del llm.client.temperature
        rapor = T.calistir(str(self.db), llm=llm, denemeler=3, parca=1)
        self.assertEqual(rapor["yeniden_uretilen"], 1)

    def test_tavan_sifir_verilse_de_en_az_bir_deneme(self) -> None:
        _db_kur(self.db, [KIRLI])
        llm = _LLM(temiz_deneme=1)
        T.calistir(str(self.db), llm=llm, denemeler=0, parca=1)
        self.assertEqual(llm.client.cagri, 1)


class TestYalnizNull(_Temel):
    """Model kapalıyken tek dürüst seçenek silmektir — uydurma değil."""

    def test_model_cagrilmadan_null_yazilir(self) -> None:
        _db_kur(self.db, [KIRLI, TEMIZ])
        rapor = T.calistir(str(self.db), yalniz_null=True, parca=1)
        self.assertEqual(rapor["null_cekilen"], 1)
        self.assertIsNone(_ozet(self.db, 1))
        self.assertEqual(_ozet(self.db, 2), TEMIZ)
        self.assertFalse(rapor["llm_acik"])


class TestRapor(_Temel):
    """Rapor iddiayı kanıtıyla birlikte basmalı."""

    def test_alfabe_kaniti_kod_noktasiyla_raporlanir(self) -> None:
        _db_kur(self.db, [KIRLI])
        rapor = T.calistir(str(self.db), kuru=True, yalniz_null=True, parca=1)
        self.assertIn("U+63D0", rapor["alfabe_kaniti"])  # 提

    def test_alfabe_kapisindan_dusen_ayri_sayilir(self) -> None:
        """Ağ hatasıyla dil kayması aynı sepete konmamalı."""
        _db_kur(self.db, [KIRLI])
        rapor = T.calistir(str(self.db), llm=_LLM(temiz_deneme=None),
                           denemeler=2, parca=1)
        self.assertEqual(rapor["alfabe_kapisindan_dusen"], 2)

    def test_kayit_dokumu_eski_ozeti_tasir(self) -> None:
        _db_kur(self.db, [KIRLI])
        rapor = T.calistir(str(self.db), kuru=True, yalniz_null=True, parca=1)
        self.assertEqual(rapor["kayitlar"][0]["id"], 1)
        self.assertEqual(rapor["kayitlar"][0]["sonuc"], "null")


class TestKomutSatiri(_Temel):
    def test_veri_tabani_yoksa_2_doner(self) -> None:
        self.assertEqual(T.main(["--db", str(self.db / "yok.db"), "--kuru"]), 2)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
