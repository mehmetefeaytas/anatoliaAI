"""Belge metni denetimi testleri.

İlgili: ../scripts/belge_metni_denetimi.py ·
../data/gold/review/_belge-eksikligi.md

## Neden bu testler

`round2_zor_vaka.csv` ekibe yollanmaya bir adım kala fark edildi: CSV 73 belge
sayıyordu, `belgeler/` altında 41 metin vardı. Paket geçici bir dizine
üretilmiş, `belgeler/` orada bırakılmıştı. Anotatör 32 belgeyi göremediği için
949 satırın büyük kısmı kararsız dönecekti.

Bu sınıf hatanın sessiz kalmasının nedeni, kimsenin bakmıyor olmasıydı:
`lint_review_csv` satır BİÇİMİNİ denetler, satırın anote EDİLEBİLİR olup
olmadığını değil. Buradaki son test o boşluğu kapatan kapıdır ve deponun
gerçek paketleri üzerinde koşar — yani aynı hata tekrar edilirse `unittest`
kırmızı yanar, teslimden sonra değil.

Diğer testler `--uret`'in fren mekanizmalarını çitler. Onlar kritik çünkü
üretecin YANLIŞ metin yazması, metin yazmamasından beterdir: anotatör yanlış
belgeye bakıp emin bir karar verir ve gold sessizce bozulur.
"""

from __future__ import annotations

import csv
import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.belge_metni_denetimi import (
    NEDEN_BOS,
    NEDEN_YOK,
    _csv_yollari,
    csv_belge_kimlikleri,
    db_metinleri,
    denetle,
    on_anotasyon_kaynagi,
    uret,
)

KOK = Path(__file__).resolve().parents[1]
INCELEME = KOK / "data" / "gold" / "review"

SUTUNLAR = ["doc_id", "bank", "field", "model_value", "model_conf",
            "confidence_source", "disagreement", "snippet", "gold_value",
            "verdict", "note", "protokol"]


def _paket_yaz(dizin: Path, ad: str, doc_ids: list[str]) -> Path:
    """Verilen belgelerden oluşan sahte bir inceleme CSV'si yazar."""
    yol = dizin / ad
    with yol.open("w", encoding="utf-8-sig", newline="") as fh:
        yazici = csv.DictWriter(fh, fieldnames=SUTUNLAR, delimiter=";")
        yazici.writeheader()
        for doc_id in doc_ids:
            yazici.writerow({c: "" for c in SUTUNLAR}
                            | {"doc_id": doc_id, "field": "kar_payi_orani"})
    return yol


def _db_yaz(yol: Path, satirlar: list[tuple[str, str]]) -> None:
    """(source_url, raw_text) satırlarından minik bir demo DB kurar."""
    con = sqlite3.connect(yol)
    con.execute("CREATE TABLE campaigns (id INTEGER PRIMARY KEY, "
                "raw_text TEXT, source_url TEXT)")
    con.executemany("INSERT INTO campaigns(source_url, raw_text) VALUES (?,?)",
                    satirlar)
    con.commit()
    con.close()


def _on_anotasyon_yaz(yol: Path, docs: list[dict]) -> None:
    yol.write_text(json.dumps({"docs": docs}, ensure_ascii=False),
                   encoding="utf-8")


class DenetimTest(unittest.TestCase):
    """Eksik ve boş metinlerin tespiti."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.dizin = Path(self.tmp.name)
        self.belgeler = self.dizin / "belgeler"
        self.belgeler.mkdir()
        self.addCleanup(self.tmp.cleanup)

    def test_metni_olan_belge_bulgu_uretmez(self) -> None:
        yol = _paket_yaz(self.dizin, "round9_test.csv", ["a--bir"])
        (self.belgeler / "a--bir.txt").write_text("metin", encoding="utf-8")
        self.assertEqual(denetle([yol], self.belgeler), [])

    def test_metni_olmayan_belge_yakalanir(self) -> None:
        yol = _paket_yaz(self.dizin, "round9_test.csv", ["a--bir", "a--iki"])
        (self.belgeler / "a--bir.txt").write_text("metin", encoding="utf-8")
        bulgular = denetle([yol], self.belgeler)
        self.assertEqual([(b.doc_id, b.neden) for b in bulgular],
                         [("a--iki", NEDEN_YOK)])

    def test_bos_metin_de_eksik_sayilir(self) -> None:
        """Boş belge anotatöre `absent` dedirtir; sessiz gold bozulması."""
        yol = _paket_yaz(self.dizin, "round9_test.csv", ["a--bir"])
        (self.belgeler / "a--bir.txt").write_text("   \n", encoding="utf-8")
        bulgular = denetle([yol], self.belgeler)
        self.assertEqual([(b.doc_id, b.neden) for b in bulgular],
                         [("a--bir", NEDEN_BOS)])

    def test_ayni_belge_iki_pakette_ayri_raporlanir(self) -> None:
        """Hangi paketin sakat olduğu bilinmeden düzeltme planlanamaz."""
        a = _paket_yaz(self.dizin, "round9_a.csv", ["a--bir"])
        b = _paket_yaz(self.dizin, "round9_b.csv", ["a--bir"])
        bulgular = denetle([a, b], self.belgeler)
        self.assertEqual([x.csv_adi for x in bulgular],
                         ["round9_a.csv", "round9_b.csv"])

    def test_yedek_dosyalar_kapsam_disi(self) -> None:
        """`.yedek` kopyaları anotatöre gitmez; kapıyı gürültüyle doldurmasın."""
        _paket_yaz(self.dizin, "round9_test.csv", ["a--bir"])
        _paket_yaz(self.dizin, "round9_test.csv.yedek", ["a--bir"])
        self.assertEqual([p.name for p in _csv_yollari(self.dizin)],
                         ["round9_test.csv"])

    def test_kimlikler_bosluk_kirpilarak_okunur(self) -> None:
        yol = _paket_yaz(self.dizin, "round9_test.csv", ["  a--bir  "])
        self.assertEqual(csv_belge_kimlikleri(yol), {"a--bir"})


class UretimTest(unittest.TestCase):
    """`--uret`in yazma koşulları ve frenleri."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.dizin = Path(self.tmp.name)
        self.belgeler = self.dizin / "belgeler"
        self.belgeler.mkdir()
        self.db_yolu = self.dizin / "demo.db"
        self.pre_yolu = self.dizin / "pre.json"
        self.addCleanup(self.tmp.cleanup)

    def _hazirla(self, docs: list[dict],
                 db_satirlari: list[tuple[str, str]]) -> tuple[dict, dict]:
        _on_anotasyon_yaz(self.pre_yolu, docs)
        _db_yaz(self.db_yolu, db_satirlari)
        return (on_anotasyon_kaynagi([self.pre_yolu]),
                db_metinleri(self.db_yolu))

    def _eksikler(self, doc_ids: list[str]) -> list:
        yol = _paket_yaz(self.dizin, "round9_test.csv", doc_ids)
        return denetle([yol], self.belgeler)

    def test_db_metni_birebir_yazilir(self) -> None:
        """Özetleme/kırpma yok: dosya `raw_text` ile bayt bayt aynı olmalı."""
        metin = "Kâr payı oranı %2,05\r\nİlk 6 ay ödemesiz  \n"
        kaynak, db = self._hazirla(
            [{"id": "a--bir", "source_url": "http://x/1", "text": metin}],
            [("http://x/1", metin)])
        yazilan, yazilamayan = uret(self._eksikler(["a--bir"]), self.belgeler,
                                    kaynak, db)
        self.assertEqual(yazilamayan, [])
        self.assertEqual(yazilan, {"a--bir": len(metin)})
        with (self.belgeler / "a--bir.txt").open(encoding="utf-8",
                                                 newline="") as fh:
            self.assertEqual(fh.read(), metin)

    def test_on_anotasyonda_olmayan_kimlik_yazilmaz(self) -> None:
        """Kimlik → URL köprüsü yoksa DB satırı bulunamaz; uydurma yasak."""
        kaynak, db = self._hazirla([], [("http://x/1", "metin")])
        yazilan, yazilamayan = uret(self._eksikler(["a--bir"]), self.belgeler,
                                    kaynak, db)
        self.assertEqual(yazilan, {})
        self.assertIn("kayit yok", yazilamayan[0][1])
        self.assertFalse((self.belgeler / "a--bir.txt").exists())

    def test_dbde_olmayan_url_yazilmaz(self) -> None:
        kaynak, db = self._hazirla(
            [{"id": "a--bir", "source_url": "http://x/yok", "text": "metin"}],
            [("http://x/1", "metin")])
        yazilan, yazilamayan = uret(self._eksikler(["a--bir"]), self.belgeler,
                                    kaynak, db)
        self.assertEqual(yazilan, {})
        self.assertIn("URL yok", yazilamayan[0][1])

    def test_ayni_url_iki_farkli_metin_tasiyorsa_yazilmaz(self) -> None:
        """`source_url` tekil değil; hangi hasadın doğru olduğu belirsiz."""
        kaynak, db = self._hazirla(
            [{"id": "a--bir", "source_url": "http://x/1", "text": "metin"}],
            [("http://x/1", "metin"), ("http://x/1", "baska metin")])
        yazilan, yazilamayan = uret(self._eksikler(["a--bir"]), self.belgeler,
                                    kaynak, db)
        self.assertEqual(yazilan, {})
        self.assertIn("farkli raw_text", yazilamayan[0][1])

    def test_bos_raw_text_yazilmaz(self) -> None:
        """Boş `.txt` yazmak, eksik metinden beter: sahte `absent` üretir."""
        kaynak, db = self._hazirla(
            [{"id": "a--bir", "source_url": "http://x/1", "text": "   "}],
            [("http://x/1", "   ")])
        yazilan, yazilamayan = uret(self._eksikler(["a--bir"]), self.belgeler,
                                    kaynak, db)
        self.assertEqual(yazilan, {})
        self.assertIn("bos", yazilamayan[0][1])
        self.assertFalse((self.belgeler / "a--bir.txt").exists())

    def test_kaynaklar_ayrisirsa_yazilmaz(self) -> None:
        """İki bağımsız kaynak farklı metin gösteriyorsa hakem bu betik değil."""
        kaynak, db = self._hazirla(
            [{"id": "a--bir", "source_url": "http://x/1", "text": "eski"}],
            [("http://x/1", "yeni")])
        yazilan, yazilamayan = uret(self._eksikler(["a--bir"]), self.belgeler,
                                    kaynak, db)
        self.assertEqual(yazilan, {})
        self.assertIn("ortusmuyor", yazilamayan[0][1])

    def test_turlardan_biri_ortusuyorsa_yazilir(self) -> None:
        """Korpus tazelendiğinde eski turun metni bayatlar; yeni tur geçerlidir."""
        docs = [{"id": "a--bir", "source_url": "http://x/1", "text": "eski"},
                {"id": "a--bir", "source_url": "http://x/1", "text": "yeni"}]
        kaynak, db = self._hazirla(docs, [("http://x/1", "yeni")])
        yazilan, yazilamayan = uret(self._eksikler(["a--bir"]), self.belgeler,
                                    kaynak, db)
        self.assertEqual(yazilamayan, [])
        self.assertEqual((self.belgeler / "a--bir.txt").read_text(
            encoding="utf-8"), "yeni")

    def test_turler_farkli_url_gosteriyorsa_yazilmaz(self) -> None:
        docs = [{"id": "a--bir", "source_url": "http://x/1", "text": "m"},
                {"id": "a--bir", "source_url": "http://x/2", "text": "m"}]
        kaynak, db = self._hazirla(docs, [("http://x/1", "m")])
        yazilan, yazilamayan = uret(self._eksikler(["a--bir"]), self.belgeler,
                                    kaynak, db)
        self.assertEqual(yazilan, {})
        self.assertIn("source_url", yazilamayan[0][1])


class DepoKapisiTest(unittest.TestCase):
    """Deponun gerçek inceleme paketleri — kalıcı kapı."""

    def test_her_paketteki_her_belgenin_metni_var(self) -> None:
        yollar = _csv_yollari(INCELEME)
        self.assertTrue(yollar, "inceleme paketi bulunamadi")
        bulgular = denetle(yollar, INCELEME / "belgeler")
        self.assertEqual(
            bulgular, [],
            "Metni olmayan belge ANOTE EDILEMEZ. Uretmek icin: "
            ".venv/bin/python -m scripts.belge_metni_denetimi --uret\n"
            + "\n".join(str(b) for b in bulgular[:20]))


if __name__ == "__main__":
    unittest.main()
