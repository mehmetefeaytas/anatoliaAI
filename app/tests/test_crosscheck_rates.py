"""Oran çapraz doğrulama betiği testleri.

İlgili: ../scripts/crosscheck_rates.py

## Neden bu testler

Betik, anotasyoncuya "şu satıra bakma, şuna bak" diyor. Yanlış çalışırsa insan
emeği yanlış yere gider ya da gerçek hata gözden kaçar. Üç ölçülmüş tuzak:

1. **Kendi çıktısını gold sanmak.** Betik `data/gold/` altına yazıyor ve
   çıktısında `field` kolonu var; kolon kontrolü olmadan sonraki koşuda kendi
   önerilerini gold satırı sayar.
2. **Fixture'ı gerçek belge sanmak.** `kuveyt-turk--konut` sentetik demo
   belgesi şartnamenin örnek metnini (%1,89) taşıyor; canlı Kuveyt Türk oranı
   %2,99. Dışlanmazsa KURAL HATASI gibi raporlanır.
3. **Farklı büyüklükleri kıyaslamak.** Finansman AYLIK, katılma hesabı YILLIK
   oran taşır; karıştırmak hayalet çelişki üretir (CLAUDE.md §17).
"""

from __future__ import annotations

import csv
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.crosscheck_rates import (
    REQUIRED_GOLD_COLUMNS,
    VERDICT_CONFIRMED,
    VERDICT_CONFLICT,
    VERDICT_FIXTURE,
    VERDICT_NO_SOURCE,
    Row,
    _model_bounds,
    check_freshness,
    check_plausibility,
    classify_product,
    crosscheck,
    load_fixture_doc_ids,
    load_gold_rows,
    render_report,
)

GOLD_HEADER = ["doc_id", "bank", "field", "model_value", "model_conf",
               "snippet", "gold_value", "verdict", "note"]


def _gold(doc_id: str, bank: str, model_value: str, conf: str = "0.95",
          field: str = "kar_payi_orani") -> dict:
    return {"doc_id": doc_id, "bank": bank, "field": field,
            "model_value": model_value, "model_conf": conf,
            "snippet": "", "gold_value": "", "verdict": "", "note": "",
            "_file": "test.csv"}


def _pub(bank: str, name: str, *, monthly=None, gross=None,
         kind: str = "finansman") -> dict:
    d = {"bank_slug": bank, "kind": kind, "product_name": name,
         "source_url": f"https://{bank}.test/x"}
    if monthly is not None:
        d["monthly_rate"] = monthly
    if gross is not None:
        d["gross_annual_rate"] = gross
    return d


class TestProductClassification(unittest.TestCase):
    def test_bilinen_siniflar(self):
        self.assertEqual(classify_product("emlak--finansmanlar-konut-finansmani"),
                         "konut")
        self.assertEqual(classify_product("kt--arac-finansmanlari-togg"), "tasit")
        self.assertEqual(classify_product("kt--ihtiyac-finansmani-egitim"),
                         "ihtiyac")
        self.assertEqual(classify_product("tf--katilma-hesaplari-e-katilma"),
                         "katilma")

    def test_kampanya_sayfasi_siniflanmaz(self):
        """Kampanya sayfasında ilan edilmiş ÜRÜN oranı uygulanamaz."""
        self.assertIsNone(
            classify_product("albaraka--detay-kahve-keyfiniz-albarakadan"))


class TestModelBounds(unittest.TestCase):
    def test_tek_deger(self):
        self.assertEqual(_model_bounds("1.89"), (1.89, 1.89))

    def test_aralik_json(self):
        self.assertEqual(_model_bounds('{"max": 4.42, "min": 2.95}'),
                         (2.95, 4.42))

    def test_bos_ve_bozuk(self):
        self.assertIsNone(_model_bounds(""))
        self.assertIsNone(_model_bounds("bilinmiyor"))


class TestCrosscheck(unittest.TestCase):
    def test_ortusen_deger_dogrulanir(self):
        rows = crosscheck(
            [_gold("emlak--finansmanlar-konut-finansmani",
                   "turkiye-emlak-katilim", "1.89")],
            [_pub("turkiye-emlak-katilim", "Konut Finansmanı", monthly=1.89)])
        self.assertEqual(rows[0].verdict, VERDICT_CONFIRMED)
        self.assertEqual(rows[0].suggested_gold, "%1.89")

    def test_ortusmeyen_deger_celiski(self):
        rows = crosscheck(
            [_gold("kt--finansmanlar-konut-finansmani", "kuveyt-turk", "1.89")],
            [_pub("kuveyt-turk", "Konut Finansmanı", monthly=2.99)])
        self.assertEqual(rows[0].verdict, VERDICT_CONFLICT)
        self.assertEqual(rows[0].suggested_gold, "%2.99")

    def test_ilan_edilmis_oran_yoksa_celiski_denmez(self):
        """Kaynak yokluğu, hata KANITI değildir."""
        rows = crosscheck(
            [_gold("kt--ihtiyac-finansmani-egitim", "kuveyt-turk", "4.82")],
            [_pub("kuveyt-turk", "Konut Finansmanı", monthly=2.99)])
        self.assertEqual(rows[0].verdict, VERDICT_NO_SOURCE)

    def test_finansman_ile_katilma_karistirilmaz(self):
        """Aylık finansman oranı, yıllık katılma oranıyla kıyaslanmaz (§17)."""
        rows = crosscheck(
            [_gold("tf--katilma-hesaplari-e-katilma", "turkiye-finans", "28.03")],
            [_pub("turkiye-finans", "Konut Finansmanı", monthly=2.99)])
        self.assertEqual(rows[0].verdict, VERDICT_NO_SOURCE,
                         "finansman kaydı katılma satırına kaynak sayılmamalı")

    def test_katilma_yillik_oran_eslesir(self):
        rows = crosscheck(
            [_gold("tf--katilma-hesaplari-e-katilma", "turkiye-finans", "28.03")],
            [_pub("turkiye-finans", "Katılma Hesabı", gross=28.03,
                  kind="katilma")])
        self.assertEqual(rows[0].verdict, VERDICT_CONFIRMED)

    def test_aralik_ilan_edilen_orani_kapsiyorsa_dogrulanir(self):
        rows = crosscheck(
            [_gold("tf--konut-finansmani", "turkiye-finans",
                   '{"min": 2.95, "max": 4.42}')],
            [_pub("turkiye-finans", "Konut Finansmanı", monthly=3.39)])
        self.assertEqual(rows[0].verdict, VERDICT_CONFIRMED)

    def test_fixture_kiyas_disi(self):
        rows = crosscheck(
            [_gold("kuveyt-turk--konut", "kuveyt-turk", "1.89")],
            [_pub("kuveyt-turk", "Konut Finansmanı", monthly=2.99)],
            fixtures={"kuveyt-turk--konut"})
        self.assertEqual(rows[0].verdict, VERDICT_FIXTURE)
        self.assertIn("sentetik", rows[0].note)

    def test_baska_alan_atlanir(self):
        rows = crosscheck([_gold("x--konut", "b", "12", field="vade_ay")], [])
        self.assertEqual(rows, [])


class TestPlausibility(unittest.TestCase):
    def test_finansmanda_makul_aylik_oran(self):
        self.assertEqual(check_plausibility("konut", (1.89, 1.89)), "makul")

    def test_vade_gibi_deger_isaretlenir(self):
        self.assertEqual(check_plausibility("ihtiyac", (36.0, 36.0)),
                         "vade_gibi")

    def test_sinir_disi(self):
        self.assertEqual(check_plausibility("tasit", (55.0, 55.0)), "sinir_disi")

    def test_katilmada_kontrol_yapilmaz(self):
        """İlan edilen yıllık oranlar %0,04–%38,73; aralık ayırt edici değil."""
        self.assertEqual(check_plausibility("katilma", (33.84, 33.84)), "")

    def test_sinif_yoksa_kontrol_yapilmaz(self):
        self.assertEqual(check_plausibility(None, (36.0, 36.0)), "")


class TestFreshness(unittest.TestCase):
    def test_ayni_deger_guncel(self):
        self.assertEqual(check_freshness("1.89", "1.89"), "guncel")

    def test_sayisal_esdegerlik(self):
        self.assertEqual(check_freshness("36.0", "36"), "guncel")

    def test_kural_artik_uretmiyorsa_bayat_fazla(self):
        """Temmuz'daki vade→oran hatası düzeltildi; CSV hâlâ eski değeri taşıyor."""
        self.assertEqual(check_freshness("36.0", ""), "bayat_fazla")

    def test_kural_farkli_uretiyorsa_bayat_farkli(self):
        self.assertEqual(check_freshness("2.99", "3.75"), "bayat_farkli")

    def test_csv_bossa_ve_kural_uretiyorsa_bayat_eksik(self):
        self.assertEqual(check_freshness("", "1.89"), "bayat_eksik")

    def test_belge_kopyasi_yoksa_karsilastirma_yapilmaz(self):
        self.assertEqual(check_freshness("1.89", None), "")


class TestLoaders(unittest.TestCase):
    def test_kendi_ciktisi_gold_sayilmaz(self):
        """EN KRİTİK: betiğin çıktısı `field` kolonu taşıyor, gold sanılmamalı."""
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            # gerçek anotasyon dosyası
            with open(d / "round1_A.csv", "w", encoding="utf-8", newline="") as fh:
                w = csv.DictWriter(fh, fieldnames=GOLD_HEADER, delimiter=";")
                w.writeheader()
                w.writerow({k: "" for k in GOLD_HEADER} |
                           {"doc_id": "x", "field": "kar_payi_orani"})
            # betiğin kendi çıktısı: `gold_value` YOK
            with open(d / "rate_crosscheck.csv", "w", encoding="utf-8",
                      newline="") as fh:
                w = csv.DictWriter(fh, fieldnames=["doc_id", "bank", "field",
                                                   "model_value", "crosscheck"],
                                   delimiter=";")
                w.writeheader()
                w.writerow({"doc_id": "y", "bank": "b",
                            "field": "kar_payi_orani", "model_value": "1",
                            "crosscheck": "dogrulandi"})
            rows = load_gold_rows(str(d))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["doc_id"], "x")

    def test_zorunlu_kolonlar_gold_value_iceriyor(self):
        self.assertIn("gold_value", REQUIRED_GOLD_COLUMNS)

    def test_fixture_tespiti_kume_klasorlerini_atlar(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            (d / "kuveyt-turk").mkdir()
            (d / "kuveyt-turk" / "konut.txt").write_text("x", encoding="utf-8")
            (d / "kuveyt-turk" / "live").mkdir()
            (d / "kuveyt-turk" / "live" / "kampanya.txt").write_text(
                "x", encoding="utf-8")
            ids = load_fixture_doc_ids(str(d))
        self.assertEqual(ids, {"kuveyt-turk--konut"},
                         "yalnızca kök seviyesindeki dosya fixture'dır")


class TestReport(unittest.TestCase):
    def test_bayat_satirlar_uyari_uretir(self):
        rows = [Row(file="f", doc_id="d", bank="b", field="kar_payi_orani",
                    model_value="36.0", model_conf="0.37", product_class="ihtiyac",
                    verdict=VERDICT_NO_SOURCE, freshness="bayat_fazla",
                    plausibility="vade_gibi")]
        out = render_report(rows)
        self.assertIn("Tazelik", out)
        self.assertIn("bayat", out)
        self.assertIn("preannotate", out, "çözüm adımı belirtilmeli")
        self.assertIn("vade_gibi", out)


if __name__ == "__main__":
    unittest.main()
