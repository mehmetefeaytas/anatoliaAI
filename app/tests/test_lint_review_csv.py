"""İnceleme CSV linter'ı testleri.

İlgili: ../scripts/lint_review_csv.py

## Neden bu testler

Linter'ın işi, anotasyon emeğinin sessizce çöpe gitmesini önlemek. Kalibrasyon
A'nın ilk turunda ölçülen üç sessiz kayıp yolu:

1. **Elektronik tablo sayfa-adı satırı.** Google Sheets bir sekmeyi CSV'ye
   yazarken başa sekme adını koydu; `csv.DictReader` onu BAŞLIK sandı ve
   dolu dosya bomboş okundu (195 cevap görünmez oldu).
2. **Tek değerli alana aralık.** `"2026-07-01 - 2026-07-31"` reddedilmiyor,
   ayrıştırıcı `2026-07-01`'i alıyor — yani BAŞLANGIÇ tarihi bitiş alanına
   giriyor ve modelin doğru cevabı yanlışla değiştiriliyor.
3. **Otomatik düzeltmenin bozduğu `doc_id`.** `--` ayıracı em-dash'e (`—`)
   dönüşünce satır hiçbir belgeyle eşleşmiyor ve `build_gold` onu atlıyor.

Ayrıca desen tabanlı aralık tespiti YANLIŞ POZİTİF üretiyordu: ISO tarih
(`2023-08-31`) ve TR ondalık (`1500.50`) ayıraç karakteri taşıyor. Ölçüm:
9 bulgunun 4'ü hayaletti. Bu yüzden kontrol **değer belirteci sayısına**
dayanıyor ve o davranış burada çitlenmiştir.
"""

from __future__ import annotations

import csv
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.lint_review_csv import (
    SEVERITY_ERROR,
    SEVERITY_WARN,
    lint,
    looks_like_range,
)

COLS = ["doc_id", "bank", "field", "model_value", "model_conf",
        "confidence_source", "disagreement", "snippet", "gold_value",
        "verdict", "note"]


def _write(rows: list[dict], *, sheet_name: str | None = None) -> str:
    """Geçici inceleme CSV'si yazar, yolunu döndürür."""
    tmp = tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False,
                                      encoding="utf-8-sig", newline="")
    if sheet_name:
        tmp.write(sheet_name + "\n")
    writer = csv.DictWriter(tmp, fieldnames=COLS, delimiter=";")
    writer.writeheader()
    for row in rows:
        writer.writerow({c: "" for c in COLS} | row)
    tmp.close()
    return tmp.name


def _row(**kw) -> dict:
    base = {"doc_id": "kuveyt-turk--konut-finansmani", "bank": "kuveyt-turk",
            "field": "kar_payi_orani", "model_value": "1.89"}
    return base | kw


def _msgs(rows: list[dict], **kw) -> list[str]:
    return [f.message for f in lint([_write(rows, **kw)])]


def _errors(rows: list[dict], **kw) -> list:
    return [f for f in lint([_write(rows, **kw)]) if f.severity == SEVERITY_ERROR]


class TestSayfaAdiSatiri(unittest.TestCase):
    """EN KRİTİK: bu satır kalırsa dolu dosya bomboş okunur."""

    def test_sayfa_adi_satiri_hata_verir(self) -> None:
        errs = _errors([_row()], sheet_name="round0_kalibrasyon_A")
        self.assertTrue(any("sayfa adini" in e.message for e in errs),
                        f"sayfa-adı satırı yakalanmadı: {errs}")

    def test_sayfa_adi_atlanip_satirlar_yine_okunur(self) -> None:
        """Satır atılmalı ama denetim devam etmeli — yoksa gerçek hatalar gizlenir."""
        rows = [_row(field="vade_ay", model_value="12",
                     gold_value="", verdict="fix")]
        errs = _errors(rows, sheet_name="sekme")
        self.assertTrue(any("gold_value bos" in e.message for e in errs),
                        f"sayfa adı atıldıktan sonra satır denetlenmedi: {errs}")

    def test_normal_dosyada_uyari_yok(self) -> None:
        self.assertEqual(_errors([_row()]), [])


class TestDocIdBozulmasi(unittest.TestCase):
    def test_em_dash_yakalanir(self) -> None:
        errs = _errors([_row(doc_id="vakif-katilim—finansmanlar-konut")])
        self.assertTrue(any("em-dash" in e.message for e in errs), errs)

    def test_bosluk_yakalanir(self) -> None:
        self.assertTrue(_errors([_row(doc_id="kuveyt turk konut")]))

    def test_gecerli_slug_temiz(self) -> None:
        self.assertEqual(_errors([_row(doc_id="tom-katilim--hesaplama_araclari.2")]),
                         [])


class TestAralikTespiti(unittest.TestCase):
    """Değer belirteci sayımı — desen araması değil."""

    def test_iso_tarih_aralik_sayilmaz(self) -> None:
        """Ölçülen hayalet: `2023-08-31` iki tire taşır ama TEK değerdir."""
        self.assertFalse(looks_like_range("kampanya_suresi", "2023-08-31"))

    def test_tr_ondalik_aralik_sayilmaz(self) -> None:
        self.assertFalse(looks_like_range(
            "finansman_tutari", '{"value": 1500.50, "currency": "TRY"}'))

    def test_iki_tarih_aralik(self) -> None:
        self.assertTrue(looks_like_range("kampanya_suresi",
                                         "2026-07-01 - 2026-07-31"))

    def test_bosluksuz_iki_tarih_aralik(self) -> None:
        self.assertTrue(looks_like_range("kampanya_suresi",
                                         "2026-07-01- 2026-07-31"))

    def test_tamsayi_araligi(self) -> None:
        for text in ("1 - 36", "3-6", "120 -  84", "1 , 3-12", "3 - 6 -12"):
            with self.subTest(text=text):
                self.assertTrue(looks_like_range("vade_ay", text))

    def test_iki_para_nesnesi_aralik(self) -> None:
        self.assertTrue(looks_like_range(
            "finansman_tutari",
            '{"value": 5000, "currency": "TRY"} - '
            '{"value": 150000, "currency": "TRY"}'))

    def test_ucnokta_acik_uclu_aralik(self) -> None:
        self.assertTrue(looks_like_range("finansman_tutari", "20000 - 25000 - …"))
        self.assertTrue(looks_like_range("vade_ay", "3 ila 12"))

    def test_tek_deger_temiz(self) -> None:
        for field, text in (("vade_ay", "36"), ("kampanya_suresi", "2026-12-31"),
                            ("finansman_tutari",
                             '{"value": 150000, "currency": "TRY"}'),
                            ("masraf_durumu",
                             '{"has_fee": true, "amount": 20000}')):
            with self.subTest(field=field):
                self.assertFalse(looks_like_range(field, text))

    def test_liste_alanlari_kontrol_edilmez(self) -> None:
        """kampanya_kosullari ÇOK değer alır; aralık kontrolü uygulanmaz."""
        self.assertFalse(looks_like_range("kampanya_kosullari", '["a 1-2", "b 3-4"]'))
        self.assertFalse(looks_like_range("hedef_kitle", '["yeni_musteri"]'))

    def test_aralik_satiri_hata_uretir(self) -> None:
        errs = _errors([_row(field="kampanya_suresi", model_value="2026-07-31",
                             gold_value="2026-07-01 - 2026-07-31", verdict="fix")])
        self.assertTrue(any("sessiz bozulma" in e.message for e in errs), errs)


class TestVerdictSozlesmesi(unittest.TestCase):
    def test_absent_ve_deger_birlikte_hata(self) -> None:
        errs = _errors([_row(gold_value="1.89", verdict="absent")])
        self.assertTrue(any("sessizce atar" in e.message for e in errs), errs)

    def test_fix_ve_bos_deger_hata(self) -> None:
        errs = _errors([_row(gold_value="", verdict="fix")])
        self.assertTrue(any("DURUR" in e.message for e in errs), errs)

    def test_taninmayan_verdict_hata(self) -> None:
        self.assertTrue(_errors([_row(verdict="belki")]))

    def test_bos_verdict_gecerli(self) -> None:
        self.assertEqual(_errors([_row()]), [])

    def test_verdict_bos_gold_dolu_uyarir(self) -> None:
        msgs = _msgs([_row(gold_value="2.05")])
        self.assertTrue(any("`fix` sayar" in m for m in msgs), msgs)

    def test_gold_model_ile_ayni_uyarir(self) -> None:
        msgs = _msgs([_row(gold_value="1.89", verdict="fix")])
        self.assertTrue(any("AYNI" in m for m in msgs), msgs)


class TestKanonikOnay(unittest.TestCase):
    def test_kanonik_olmayan_model_degeri_onaylanirsa_hata(self) -> None:
        """`{"rate": 0.5}` bir para değeri değil; boş verdict onu onaylıyor."""
        errs = _errors([_row(field="tahsis_ucreti",
                             model_value='{"rate": 0.5}')])
        self.assertTrue(any("kanonik degil" in e.message for e in errs), errs)

    def test_kanonik_model_degeri_temiz(self) -> None:
        self.assertEqual(
            _errors([_row(field="tahsis_ucreti",
                          model_value='{"value": 500, "currency": "TRY"}')]),
            [])

    def test_bos_model_degeri_onaylanabilir(self) -> None:
        """Model bir şey üretmediyse boş verdict 'kontrol ettim, yok' demektir."""
        self.assertEqual(_errors([_row(model_value="")]), [])


class TestUnclearEsigi(unittest.TestCase):
    def test_cok_unclear_uyarir(self) -> None:
        rows = [_row(doc_id=f"b--d{i}", verdict="unclear") for i in range(10)]
        msgs = _msgs(rows)
        self.assertTrue(any("unclear" in m and "esik" in m for m in msgs), msgs)

    def test_esik_altinda_uyarmaz(self) -> None:
        rows = [_row(doc_id=f"b--d{i}") for i in range(100)]
        rows[0]["verdict"] = "unclear"
        self.assertFalse(any("esik" in m for m in _msgs(rows)))


class TestEksikSutun(unittest.TestCase):
    def test_zorunlu_sutun_eksikse_hata(self) -> None:
        tmp = tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False,
                                          encoding="utf-8-sig", newline="")
        tmp.write("doc_id;field\nx--y;kar_payi_orani\n")
        tmp.close()
        findings = lint([tmp.name])
        self.assertTrue(any("zorunlu sutun eksik" in f.message
                            for f in findings), findings)


class TestGercekDosya(unittest.TestCase):
    """Kalibrasyon A temiz kalmalı — regresyon çiti."""

    def test_kalibrasyon_a_temiz(self) -> None:
        path = (Path(__file__).resolve().parents[1] / "data" / "gold" /
                "review" / "round0_kalibrasyon_A.csv")
        if not path.exists():
            self.skipTest("kalibrasyon A dosyası yok")
        errs = [f for f in lint([str(path)]) if f.severity == SEVERITY_ERROR]
        self.assertEqual(errs, [], f"kalibrasyon A'da hata: {errs}")


class TestSeverityDegerleri(unittest.TestCase):
    def test_severity_sabitleri_ayrik(self) -> None:
        self.assertNotEqual(SEVERITY_ERROR, SEVERITY_WARN)


if __name__ == "__main__":
    unittest.main()
