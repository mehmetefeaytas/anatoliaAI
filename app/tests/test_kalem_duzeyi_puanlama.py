"""Liste alanlarında kalem düzeyinde puanlama.

İlgili: eval/matchers.py (`item_counts`) · eval/run_eval.py (`aggregate_item`)
        docs/rapor/olcumler.md

## Bu testin varlık sebebi

`_list_equal` KÜME EŞİTLİĞİ arıyor: beş koşuldan dördü doğru çıkarılsa bile
TP=0, FP=1, FN=1. Ölçüldü — gold.v2'de `kampanya_kosullari` her iki
eşleştiricide de TAM OLARAK 0,000; `tolerant` bile birebir aynı sayıları
veriyor. Yani sorun toleransta değil, ölçütün İKİLİ olmasında.

Kalem düzeyi ölçüt ikili ölçütün YERİNE GEÇMEZ, yanında durur. İkisi
karşılaştırılabilir kalsın diye liste OLMAYAN alanlarda iki tablo birebir aynı
olmak zorundadır — bu testin en kritik iddiası budur.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from eval.matchers import ITEM_JACCARD_ESIK, ItemCounts, item_counts
from eval.run_eval import aggregate, aggregate_item, score_document
from scripts.gold_schema import GoldRecord

KK = "kampanya_kosullari"      # serbest metin listesi
HK = "hedef_kitle"             # etiket listesi (denetimli sözcük)


class KalemSayaci(unittest.TestCase):

    def test_liste_olmayan_alan_None_doner(self):
        for alan in ("vade_ay", "kar_payi_orani", "masraf_durumu"):
            self.assertIsNone(item_counts(alan, 12, 12),
                              f"{alan} liste alanı değil")

    def test_kismi_ortusme_kredi_alir(self):
        """Beş koşuldan dördü tutuyorsa sonuç 0 OLAMAZ — asıl kusur buydu."""
        gold = [f"koşul {i}" for i in range(5)]
        pred = [f"koşul {i}" for i in range(4)]
        c = item_counts(KK, pred, gold)
        self.assertEqual((c.tp, c.fp, c.fn), (4, 0, 1))

    def test_tam_eslesme(self):
        gold = ["kampanya 31 Aralık 2026 tarihine kadar geçerlidir"]
        c = item_counts(KK, list(gold), gold)
        self.assertEqual((c.tp, c.fp, c.fn), (1, 0, 0))

    def test_noktalama_ve_TR_imla_kaleme_engel_degil(self):
        gold = ["Banka koşulları değiştirme hakkını saklı tutar."]
        pred = ["banka kosullari degistirme hakkini sakli tutar"]
        self.assertEqual(item_counts(KK, pred, gold).tp, 1)

    def test_bir_tahmin_iki_gold_kalemini_karsilayamaz(self):
        """Tek uzun cümle tüm koşulları 'karşılıyor' görünmemeli (1-1 eşleşme)."""
        gold = ["ilk üç ay ödemesizdir", "ilk üç ay ödemesizdir"]
        c = item_counts(KK, ["ilk üç ay ödemesizdir"], gold)
        self.assertEqual((c.tp, c.fp, c.fn), (1, 0, 1))

    def test_model_liste_uretmediyse_hepsi_kacirma(self):
        gold = ["a b c", "d e f"]
        self.assertEqual(item_counts(KK, None, gold), ItemCounts(fn=2))

    def test_etiket_listesinde_birebir_aranir(self):
        """`KOBİ` ile `KOBİ sahipleri` FARKLI hedef kitledir; Jaccard birleştirirdi."""
        c = item_counts(HK, ["KOBİ sahipleri"], ["KOBİ"])
        self.assertEqual((c.tp, c.fp, c.fn), (0, 1, 1))
        self.assertEqual(item_counts(HK, ["KOBİ"], ["KOBİ"]).tp, 1)

    def test_esik_monoton(self):
        """Eşik yükseldikçe TP azalır — uçurum ya da ters dönüş olmamalı."""
        gold = ["ilk üç ay ödemesiz dönem uygulanır"]
        pred = ["ilk üç ay ödemesiz dönem"]
        tps = [item_counts(KK, pred, gold, esik=e).tp
               for e in (0.5, 0.6, 0.7, 0.8, 0.9, 1.0)]
        self.assertEqual(tps, sorted(tps, reverse=True))

    def test_ilan_edilmis_esik_degismedi(self):
        """Eşik anotasyondan ÖNCE ilan edildi; sonuca bakıp değiştirmek yasak."""
        self.assertEqual(ITEM_JACCARD_ESIK, 0.7)


def _kayit(fields: dict, absent=(), unclear=()) -> GoldRecord:
    return GoldRecord(id="t--1", text="metin", fields=dict(fields),
                      absent_fields=list(absent), unclear_fields=list(unclear))


def _eslesir(name, pred, gold):
    return pred == gold


class IkiTablonunParitesi(unittest.TestCase):
    """Liste OLMAYAN alanlarda iki tablo birebir aynı olmak ZORUNDA."""

    def test_skaler_alanlarda_iki_tablo_ayni(self):
        senaryolar = [
            ({"vade_ay": 12}, {"vade_ay": 12}),        # TP
            ({"vade_ay": 12}, {"vade_ay": 36}),        # FP + FN
            ({}, {"vade_ay": 12}),                     # FN
        ]
        for preds, gold in senaryolar:
            with self.subTest(preds=preds, gold=gold):
                score = score_document(_kayit(gold), preds, _eslesir,
                                       fields=("vade_ay",))
                ikili = aggregate([score])["vade_ay"]
                kalem = aggregate_item([score])["vade_ay"]
                self.assertEqual(
                    (ikili.tp, ikili.fp, ikili.fn),
                    (kalem.tp, kalem.fp, kalem.fn),
                    "liste olmayan alanda iki tablo ayrıştı — iki mikro-F1 "
                    "artık karşılaştırılabilir değil")

    def test_uydurma_liste_alaninda_kalem_kalem_sayilir(self):
        """Gold 'YOK' derken üretilen HER koşul ayrı bir uydurmadır."""
        score = score_document(_kayit({}, absent=[KK]),
                               {KK: ["a b", "c d", "e f"]}, _eslesir,
                               fields=(KK,))
        ikili = aggregate([score])[KK]
        kalem = aggregate_item([score])[KK]
        self.assertEqual(ikili.fp_hallucinated, 1)
        self.assertEqual(kalem.fp_hallucinated, 3)

    def test_liste_alaninda_kismi_basari_gorunur_olur(self):
        gold = {KK: [f"koşul numara {i}" for i in range(5)]}
        preds = {KK: [f"koşul numara {i}" for i in range(4)]}
        score = score_document(_kayit(gold), preds, _eslesir, fields=(KK,))
        ikili = aggregate([score])[KK]
        kalem = aggregate_item([score])[KK]
        self.assertEqual(ikili.f1(), 0.0, "ikili ölçüt 4/5'i sıfır sayar")
        self.assertGreater(kalem.f1(), 0.8)

    def test_karar_verilmemis_alan_iki_tabloda_da_metrik_disi(self):
        score = score_document(_kayit({}), {"vade_ay": 12}, _eslesir,
                               fields=("vade_ay",))
        self.assertEqual(aggregate([score])["vade_ay"].skipped, 1)
        self.assertEqual(aggregate_item([score])["vade_ay"].skipped, 1)


if __name__ == "__main__":
    unittest.main()
