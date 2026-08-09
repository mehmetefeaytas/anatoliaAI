"""Hakemlik kuralları — anotatör kararını değiştiren araç, kapıya bağlı.

İlgili: ../scripts/kalibrasyon_hakemlik.py
        ../data/gold/ANNOTATION_GUIDE.md §3.1, §3.3 (kuralların kaynağı)
        ../data/gold/review/_kalibrasyon-sonucu.md §8 (uygulama kaydı)

Bu araç 472 anotatör hücresini değiştirdi. Bir hakemlik aracının en tehlikeli
kusuru sessizce YANLIŞ düzeltmektir: kimse bakmaz, çünkü "düzeltildi" der.

Buradaki en önemli test `test_cozulemeyen_tarih_DOKUNULMAZ`. Gerçek bir
kusurdu: `'1.07.2023-31.08.23'` girdisinde bitişin yılı iki haneli, katı kalıp
onu görmüyor ve "son eşleşme = bitiş" kuralı BAŞLANGICI döndürüyordu — yani
araç, düzeltmek için yazıldığı hatanın aynısını üretiyordu.
"""

from __future__ import annotations

import csv
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import kalibrasyon_hakemlik as H
from scripts.to_review_csv import CSV_DELIMITER, CSV_ENCODING

BASLIK = ["doc_id", "bank", "field", "model_value", "model_conf",
          "confidence_source", "disagreement", "snippet", "gold_value",
          "verdict", "note"]


def _satir(field="vade_ay", model="12", gold="", verdict="", doc="d1"):
    return {"doc_id": doc, "bank": "t", "field": field, "model_value": model,
            "model_conf": "0.70", "confidence_source": "rule",
            "disagreement": "", "snippet": "…", "gold_value": gold,
            "verdict": verdict, "note": ""}


class TestIsoBitis(unittest.TestCase):
    """`kampanya_suresi` = geçerlilik BİTİŞ tarihi (kılavuz)."""

    def test_aralikta_BITIS_alinir(self):
        self.assertEqual(H._iso_bitis("01.01.2026 - 31.12.2026"), "2026-12-31")

    def test_tek_tarih_oldugu_gibi(self):
        self.assertEqual(H._iso_bitis("31.12.2026"), "2026-12-31")

    def test_zaten_iso_ise_degismez(self):
        self.assertEqual(H._iso_bitis("2026-07-31"), "2026-07-31")

    def test_cozulemeyen_tarih_DOKUNULMAZ(self):
        """İki haneli yıl: başlangıcı bitiş sanma kusuru buradaydı."""
        self.assertIsNone(H._iso_bitis("1.07.2023-31.08.23"))

    def test_gecersiz_tarih_None(self):
        self.assertIsNone(H._iso_bitis("31.13.2026"))

    def test_tarih_yoksa_None(self):
        self.assertIsNone(H._iso_bitis("yaz boyunca"))
        self.assertIsNone(H._iso_bitis(""))

    def test_yazili_ay_DOKUNULMAZ(self):
        """'1 – 31 Temmuz 2026' ayrıştırılmıyor; uydurmaktansa insana bırak."""
        self.assertIsNone(H._iso_bitis("1 – 31 Temmuz 2026"))

    def test_anotator_yazim_hatasi_KORUNUR(self):
        """`21.12` muhtemelen `31.12` idi ama düzeltmek bizim işimiz değil."""
        self.assertEqual(H._iso_bitis("01.01.2026 - 21.12.2026"), "2026-12-21")


class TestTurYazimi(unittest.TestCase):
    def test_kucuk_harf_kanoniklesir(self):
        self.assertEqual(H._TUR_INDEKS.get(H.tr_fold_ascii("ihtiyaç finansmanı")),
                         "İhtiyaç Finansmanı")
        self.assertEqual(H._TUR_INDEKS.get(H.tr_fold_ascii("kart")), "Kart")

    def test_taksonomi_disi_eslesmez(self):
        for uydurma in ("Güneş Katılma Hesabı", "Leasing", "Yatırım Hesabı"):
            self.assertIsNone(H._TUR_INDEKS.get(H.tr_fold_ascii(uydurma)),
                              f"{uydurma} 8 sınıfta yok, eşleşmemeli")

    def test_sekiz_sinif(self):
        self.assertEqual(len(H.KAMPANYA_TURLERI), 8)


class _DosyaTemel(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.yol = Path(self._tmp.name) / "round0_X.csv"

    def tearDown(self):
        self._tmp.cleanup()

    def yaz(self, satirlar):
        with self.yol.open("w", encoding=CSV_ENCODING, newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=BASLIK, delimiter=CSV_DELIMITER,
                               lineterminator="\r\n")
            w.writeheader()
            w.writerows(satirlar)

    def oku(self):
        with self.yol.open(encoding=CSV_ENCODING, newline="") as fh:
            return list(csv.DictReader(fh, delimiter=CSV_DELIMITER))


class TestBosOk(_DosyaTemel):
    def test_bos_bos_ok_olur(self):
        self.yaz([_satir()])
        H.uygula(self.yol, ("bos-ok",))
        self.assertEqual(self.oku()[0]["verdict"], "ok")

    def test_DOLU_gold_value_KORUNUR(self):
        """Boş verdict + dolu gold_value = fix. Onaya çevrilemez."""
        self.yaz([_satir(gold="36")])
        r = H.uygula(self.yol, ("bos-ok",))
        self.assertEqual(self.oku()[0]["verdict"], "")
        self.assertEqual(r["korunan"]["dolu_gold_value"], 1)
        self.assertEqual(r["degisimler"], [])


class TestAbsentOk(_DosyaTemel):
    def test_model_bos_absent_ok_olur(self):
        self.yaz([_satir(model="", verdict="absent")])
        H.uygula(self.yol, ("absent-ok",))
        self.assertEqual(self.oku()[0]["verdict"], "ok")

    def test_model_DOLU_absent_KORUNUR(self):
        """Meşru halüsinasyon iddiası — projenin ölçtüğü en değerli sinyal."""
        self.yaz([_satir(model="12", verdict="absent")])
        r = H.uygula(self.yol, ("absent-ok",))
        self.assertEqual(self.oku()[0]["verdict"], "absent")
        self.assertEqual(r["korunan"]["mesru_absent"], 1)

    def test_buyuk_harfli_Absent_de_yakalanir(self):
        self.yaz([_satir(model="", verdict="Absent")])
        H.uygula(self.yol, ("absent-ok",))
        self.assertEqual(self.oku()[0]["verdict"], "ok")


class TestDegerBicim(_DosyaTemel):
    def test_tarih_araligi_iso_bitise_iner(self):
        self.yaz([_satir(field="kampanya_suresi",
                         gold="01.01.2026 - 31.12.2026", verdict="fix")])
        H.uygula(self.yol, ("deger-bicim",))
        self.assertEqual(self.oku()[0]["gold_value"], "2026-12-31")

    def test_cozulemeyen_tarih_YAZILMAZ(self):
        self.yaz([_satir(field="kampanya_suresi",
                         gold="1.07.2023-31.08.23", verdict="fix")])
        r = H.uygula(self.yol, ("deger-bicim",))
        self.assertEqual(self.oku()[0]["gold_value"], "1.07.2023-31.08.23")
        self.assertEqual(r["degisimler"], [])

    def test_tur_yazimi_kanoniklesir(self):
        self.yaz([_satir(field="campaign_type", gold="ihtiyaç finansmanı",
                         verdict="fix")])
        H.uygula(self.yol, ("deger-bicim",))
        self.assertEqual(self.oku()[0]["gold_value"], "İhtiyaç Finansmanı")

    def test_taksonomi_disi_tur_DOKUNULMAZ(self):
        self.yaz([_satir(field="campaign_type", gold="Güneş Katılma Hesabı",
                         verdict="fix")])
        r = H.uygula(self.yol, ("deger-bicim",))
        self.assertEqual(self.oku()[0]["gold_value"], "Güneş Katılma Hesabı")
        self.assertEqual(r["degisimler"], [])

    def test_diger_alanlara_dokunmaz(self):
        self.yaz([_satir(field="vade_ay", gold="48 aya kadar", verdict="fix")])
        r = H.uygula(self.yol, ("deger-bicim",))
        self.assertEqual(self.oku()[0]["gold_value"], "48 aya kadar")
        self.assertEqual(r["degisimler"], [])


class TestKayitVeYedek(_DosyaTemel):
    def test_her_degisim_KAYDA_gecer(self):
        self.yaz([_satir(), _satir(doc="d2", model="", verdict="absent")])
        r = H.uygula(self.yol, ("bos-ok", "absent-ok"))
        self.assertEqual(len(r["degisimler"]), 2)
        for d in r["degisimler"]:
            self.assertEqual(set(d), {"dosya", "doc_id", "field", "sutun",
                                      "eski", "yeni", "kural"})

    def test_yedek_TASIMADAN_ONCEKI_hali(self):
        self.yaz([_satir()])
        r = H.uygula(self.yol, ("bos-ok",))
        with Path(r["yedek"]).open(encoding=CSV_ENCODING, newline="") as fh:
            self.assertEqual(next(csv.DictReader(fh, delimiter=CSV_DELIMITER))
                             ["verdict"], "")

    def test_kuru_kosu_YAZMAZ(self):
        self.yaz([_satir()])
        r = H.uygula(self.yol, ("bos-ok",), kuru=True)
        self.assertEqual(len(r["degisimler"]), 1)
        self.assertEqual(self.oku()[0]["verdict"], "")
        self.assertIsNone(r["yedek"])

    def test_bilinmeyen_kural_ACIK_HATA(self):
        self.yaz([_satir()])
        with self.assertRaises(ValueError):
            H.uygula(self.yol, ("olmayan-kural",))

    def test_zaten_ok_olan_satir_degisim_SAYILMAZ(self):
        self.yaz([_satir(verdict="ok")])
        r = H.uygula(self.yol, ("bos-ok",))
        self.assertEqual(r["degisimler"], [])


if __name__ == "__main__":
    unittest.main()
