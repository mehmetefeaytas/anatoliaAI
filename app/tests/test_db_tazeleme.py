"""DB tazeleme: geçerli özet taşınır, bayat özet taşınmaz, kapı ikisini de görür.

İlgili: ../scripts/ozet_tasi.py, ../scripts/check_demo_db.py,
        ../scripts/build_demo_db.py, ../scripts/build_summaries.py

## Bu testlerin varlık sebebi — ÖLÇÜLMÜŞ VAKA (2026-08-12)

Korpus 11 Ağustos'ta tazelendi; `data/demo.db` 12 Ağustos'a kadar bayat
kaldı. Sebep bir hata değil, bir MALİYET SANRISIYDI: "DB'yi yeniden kurmak
1.750 özeti siler, yerel modelle ~4 saat" sanılıyordu, bu yüzden ertelendi.

Ölçünce çıkan gerçek:

    DB metni diskle AYNI  : 1.724 belge  -> özeti HÂLÂ GEÇERLİ
    metni değişmiş        :    48 belge  -> özeti bayat
    DB'de hiç yok (yeni)  :     8 belge  -> özeti yok

Yani yeniden üretilecek özet 1.750 değil **56**; 4 saat değil ~8 dakika.
`ozet_tasi` bu farkı kapatır.

## İkinci ve daha sinsi bulgu

`check_demo_db` yalnız belge SAYISINI karşılaştırıyordu. Tazelemede 48
belgenin İÇERİĞİ de değişmişti ama sayı aynı kaldığı için kapı bunu HİÇ
görmedi. İçerik bayatlığı daha tehlikelidir: `ozet` sütunu dolu olduğu için
arayüzde her şey normal görünür, kullanıcı kaynağında artık bulunmayan bir
oranı okur.
"""

from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

from scripts.check_demo_db import icerik_bayatligi
from scripts.ozet_tasi import tasi

SEMA = """
CREATE TABLE campaigns (
    id INTEGER PRIMARY KEY,
    source_url TEXT,
    raw_text TEXT,
    ozet TEXT,
    ozet_sebep TEXT
);
"""


def _db(yol: Path, satirlar) -> Path:
    conn = sqlite3.connect(yol)
    conn.executescript(SEMA)
    conn.executemany(
        "INSERT INTO campaigns(id, source_url, raw_text, ozet, ozet_sebep) "
        "VALUES (?,?,?,?,?)", satirlar)
    conn.commit()
    conn.close()
    return yol


def _ozetler(yol: Path) -> dict[int, str | None]:
    conn = sqlite3.connect(yol)
    try:
        return {r[0]: r[1] for r in
                conn.execute("SELECT id, ozet FROM campaigns")}
    finally:
        conn.close()


class TestOzetTasima(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dizin = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_metni_AYNI_olan_ozet_tasinir(self):
        eski = _db(self.dizin / "eski.db",
                   [(1, "https://a/1", "kampanya metni", "ÖZET", None)])
        yeni = _db(self.dizin / "yeni.db",
                   [(9, "https://a/1", "kampanya metni", None, None)])
        s = tasi(eski, yeni)
        self.assertEqual(s.tasinan, 1)
        self.assertEqual(_ozetler(yeni)[9], "ÖZET")

    def test_metni_DEGISMIS_ozet_TASINMAZ(self):
        """Bayat özeti taşımak, düzeltmek istediğimiz hatayı korumaktır."""
        eski = _db(self.dizin / "eski.db",
                   [(1, "https://a/1", "eski metin", "ESKİ ÖZET", None)])
        yeni = _db(self.dizin / "yeni.db",
                   [(9, "https://a/1", "YENİ metin", None, None)])
        s = tasi(eski, yeni)
        self.assertEqual(s.tasinan, 0)
        self.assertEqual(s.metni_degisti, 1)
        self.assertIsNone(_ozetler(yeni)[9],
                          "değişmiş belgeye bayat özet yazıldı")

    def test_TEKRARLI_URL_her_kayda_ayri_tasinir(self):
        """Korpusta 95 tekrarlı URL var — ilk sürüm 93 özeti sessizce düşürdü.

        `source_url` tek anahtar sayıldığında sözlük her URL için yalnız SON
        kaydı tutuyordu; aynı sayfadaki diğer ürünlerin özeti kayboluyordu ve
        betik yine de "taşındı" diye başarı raporluyordu.
        """
        eski = _db(self.dizin / "eski.db", [
            (1, "https://a/1", "ürün A metni", "ÖZET A", None),
            (2, "https://a/1", "ürün B metni", "ÖZET B", None),
        ])
        yeni = _db(self.dizin / "yeni.db", [
            (9, "https://a/1", "ürün A metni", None, None),
            (10, "https://a/1", "ürün B metni", None, None),
        ])
        s = tasi(eski, yeni)
        self.assertEqual(s.tasinan, 2, "tekrarlı URL'de özet düştü")
        self.assertEqual(_ozetler(yeni), {9: "ÖZET A", 10: "ÖZET B"})

    def test_hedefte_olmayan_belge_AYRI_sayilir(self):
        eski = _db(self.dizin / "eski.db",
                   [(1, "https://silinmis/1", "metin", "ÖZET", None)])
        yeni = _db(self.dizin / "yeni.db",
                   [(9, "https://a/1", "metin", None, None)])
        s = tasi(eski, yeni)
        self.assertEqual(s.hedefte_yok, 1)
        self.assertEqual(s.metni_degisti, 0,
                         "silinmiş belge 'metni değişti' sayılmamalı")

    def test_kuru_kosu_YAZMAZ(self):
        eski = _db(self.dizin / "eski.db",
                   [(1, "https://a/1", "metin", "ÖZET", None)])
        yeni = _db(self.dizin / "yeni.db",
                   [(9, "https://a/1", "metin", None, None)])
        s = tasi(eski, yeni, kuru=True)
        self.assertEqual(s.tasinan, 1)
        self.assertIsNone(_ozetler(yeni)[9], "kuru koşu diske yazdı")

    def test_ozet_sebep_de_tasinir(self):
        """"Neden özet yok" bilgisi kaybolursa arayüz boş kutu gösterir."""
        eski = _db(self.dizin / "eski.db",
                   [(1, "https://a/1", "metin", None, "belge çok kısa")])
        yeni = _db(self.dizin / "yeni.db",
                   [(9, "https://a/1", "metin", None, None)])
        tasi(eski, yeni)
        conn = sqlite3.connect(yeni)
        sebep = conn.execute(
            "SELECT ozet_sebep FROM campaigns WHERE id=9").fetchone()[0]
        conn.close()
        self.assertEqual(sebep, "belge çok kısa")


class TestIcerikKapisi(unittest.TestCase):
    """Sayı tutsa bile içerik ayrışabilir — kapı bunu görmeliydi, görmüyordu."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dizin = Path(self.tmp.name)
        self.raw = self.dizin / "raw"
        self.raw.mkdir()

    def tearDown(self):
        self.tmp.cleanup()

    def _belge_yaz(self, ad: str, url: str, metin: str) -> None:
        (self.raw / f"{ad}.txt").write_text(metin, encoding="utf-8")
        (self.raw / f"{ad}.txt.meta.json").write_text(
            f'{{"source_url": "{url}"}}', encoding="utf-8")

    def test_ayni_icerik_bayat_DEGIL(self):
        db = _db(self.dizin / "d.db",
                 [(1, "https://a/1", "aynı metin", "ÖZET", None)])
        self._belge_yaz("a", "https://a/1", "aynı metin")
        degisen, ozeti_bayat, n = icerik_bayatligi(str(db), str(self.raw))
        self.assertEqual((degisen, ozeti_bayat, n), (0, 0, 1))

    def test_degisen_icerik_YAKALANIR(self):
        db = _db(self.dizin / "d.db",
                 [(1, "https://a/1", "ESKİ metin", "ÖZET", None)])
        self._belge_yaz("a", "https://a/1", "YENİ metin")
        degisen, ozeti_bayat, _ = icerik_bayatligi(str(db), str(self.raw))
        self.assertEqual(degisen, 1)
        self.assertEqual(ozeti_bayat, 1, "bayat özet ayrıca sayılmalı")

    def test_bosluk_farki_YANLIS_POZITIF_uretmez(self):
        """`build_demo_db` satır sonlarını boşluğa çevirir — içerik değişimi değil.

        Bu eşitleme olmadan kapı, TAZELENMİŞ bir DB'de bile bayat raporluyordu.
        """
        db = _db(self.dizin / "d.db",
                 [(1, "https://a/1", "Mobil Bankacılık Aç Sağlık", "Ö", None)])
        self._belge_yaz("a", "https://a/1", "Mobil Bankacılık\nAç\nSağlık\n")
        degisen, _, n = icerik_bayatligi(str(db), str(self.raw))
        self.assertEqual(n, 1, "belge karşılaştırılmadı")
        self.assertEqual(degisen, 0, "boşluk farkı içerik değişikliği sanıldı")

    def test_tekrarli_URL_herhangi_biri_tutarsa_yeter(self):
        """Aynı sayfada birden çok ürün olabilir; küme eşleşmesi doğrudur."""
        db = _db(self.dizin / "d.db", [
            (1, "https://a/1", "ürün A", None, None),
            (2, "https://a/1", "ürün B", None, None),
        ])
        self._belge_yaz("a", "https://a/1", "ürün B")
        degisen, _, _ = icerik_bayatligi(str(db), str(self.raw))
        self.assertEqual(degisen, 0)

    def test_ozeti_olmayan_bayat_belge_ayri_sayilir(self):
        db = _db(self.dizin / "d.db",
                 [(1, "https://a/1", "ESKİ", None, None)])
        self._belge_yaz("a", "https://a/1", "YENİ")
        degisen, ozeti_bayat, _ = icerik_bayatligi(str(db), str(self.raw))
        self.assertEqual((degisen, ozeti_bayat), (1, 0))


if __name__ == "__main__":                                # pragma: no cover
    unittest.main()
