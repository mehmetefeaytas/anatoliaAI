"""Protokol semantiğinin ÜÇ tüketicide de aynı olduğunu kilitler.

İlgili: scripts/gold_schema.py (tek doğruluk kaynağı — `row_protocol`)
        scripts/build_gold.py (gold'u YAZAN)
        scripts/report_iaa.py (κ'yı hesaplayan)
        scripts/lint_review_csv.py (kapı)
        data/gold/ANNOTATION_GUIDE.md §3.1, §11

## Bu testin varlık sebebi

Boş `verdict` hücresinin anlamı protokole göre değişir (v1: onay · v2: karar
verilmedi). Bu semantiğin üç ayrı tüketicisi var ve ölçüldü ki **ikisi biliyor,
biri bilmiyordu**: `report_iaa` ve `lint_review_csv` protokolü sayıyordu,
`build_gold.resolve_decision` ise koşulsuz `if not verdict: verdict = "ok"`
diyordu. Yani κ dürüsttü, GOLD çapalıydı — ve gold'u kimse denetlemiyordu.

Kök neden ayrışmadır ve bu projede ölçülmüş bir hata sınıfıdır: aynı semantik
bir yolda kilitli, karşıtı diğerinde serbest (bkz.
`tests/test_masraf_kiyas_paritesi.py` — `_numeric_key` / `_composite_numeric`).
Tek doğruluk kaynağı yetmez; yolları birbirine BAĞLAYAN bir test gerekir,
yoksa biri değişir ve fark sessiz kalır.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from scripts import build_gold, lint_review_csv, report_iaa
from scripts.gold_schema import (
    PROTOCOL_COLUMN,
    PROTOCOL_V1,
    PROTOCOL_V2,
    SKIPPED_DECISION,
    row_protocol,
)

MODEL_VALUE = 24
UYARLAR = (build_gold, report_iaa, lint_review_csv)


def _satir(**kwargs) -> dict:
    """Tek inceleme satırı. Varsayılan: boş verdict, model bir değer üretmiş."""
    row = {
        "doc_id": "albaraka--ornek", "bank": "albaraka", "field": "vade_ay",
        "model_value": str(MODEL_VALUE), "model_conf": "0.95",
        "confidence_source": "rule", "disagreement": "", "snippet": "36 ay vade",
        "gold_value": "", "verdict": "", "note": "",
        "_line": 2, "_file": "test.csv",
    }
    row.update(kwargs)
    return row


class TekDogrulukKaynagi(unittest.TestCase):
    """Üç modül de protokolü `gold_schema`dan okumalı — kendi kopyasından değil."""

    def test_uc_modul_ayni_row_protocol_nesnesini_kullanir(self):
        for modul in UYARLAR:
            fn = getattr(modul, "row_protocol", None)
            if fn is None:          # modül doğrudan içe aktarmıyorsa sorun yok
                continue
            self.assertIs(
                fn, row_protocol,
                f"{modul.__name__} kendi `row_protocol` kopyasını taşıyor. "
                f"Kopyalar ayrışırsa κ dürüst, gold çapalı kalır.")

    def test_protokol_sabitleri_ayni(self):
        for modul in UYARLAR:
            for ad, beklenen in (("PROTOCOL_V1", PROTOCOL_V1),
                                 ("PROTOCOL_V2", PROTOCOL_V2),
                                 ("PROTOCOL_COLUMN", PROTOCOL_COLUMN)):
                deger = getattr(modul, ad, beklenen)
                self.assertEqual(deger, beklenen,
                                 f"{modul.__name__}.{ad} ayrışmış")


class BosHucreninAnlami(unittest.TestCase):
    """v1: boş = onay (modelin değeri gold'a girer). v2: boş = gold'a GİRMEZ."""

    def test_v1_bos_verdict_modelin_degerini_golda_yazar(self):
        kind, value = build_gold.resolve_decision(_satir())
        self.assertEqual(kind, "value")
        self.assertEqual(value, MODEL_VALUE)

    def test_v2_bos_verdict_golda_YAZMAZ(self):
        kind, value = build_gold.resolve_decision(
            _satir(**{PROTOCOL_COLUMN: PROTOCOL_V2}))
        self.assertEqual(
            kind, SKIPPED_DECISION,
            "v2'de boş hücre 'model doğru' sayılamaz — kılavuzun §3.1 ile "
            "kaldırdığı çapalama tam olarak budur.")
        self.assertIsNone(value)

    def test_v2_skipped_unclear_DEGILDIR(self):
        """`unclear` = 'baktım, karar veremedim'. `skipped` = 'hiç bakılmadı'.

        İkisini birleştirmek hakemlik kuyruğunu, bakılmamış satırlarla şişirir.
        """
        self.assertNotEqual(SKIPPED_DECISION, "unclear")
        kind, _ = build_gold.resolve_decision(
            _satir(verdict="unclear", **{PROTOCOL_COLUMN: PROTOCOL_V2}))
        self.assertEqual(kind, "unclear")

    def test_protokol_sutunu_yoksa_v1(self):
        """Geriye dönük uyum: eski CSV'lerin yorumu DEĞİŞMEZ."""
        self.assertEqual(row_protocol({}), PROTOCOL_V1)
        self.assertEqual(row_protocol({PROTOCOL_COLUMN: ""}), PROTOCOL_V1)
        self.assertEqual(row_protocol({PROTOCOL_COLUMN: "v3"}), PROTOCOL_V1)
        self.assertEqual(row_protocol({PROTOCOL_COLUMN: "V2"}), PROTOCOL_V2)


class KararYolPariteleri(unittest.TestCase):
    """`build_gold` ile `report_iaa` aynı satıra aynı kararı vermeli."""

    def test_bos_hucre_iki_yolda_da_ayni_yone_bakar(self):
        for protokol, golda_var, kapaya_girer in (
            (PROTOCOL_V1, True, True),      # v1: her ikisi de "ok"
            (PROTOCOL_V2, False, False),    # v2: her ikisi de "yok say"
        ):
            with self.subTest(protokol=protokol):
                row = _satir(**{PROTOCOL_COLUMN: protokol})

                kind, _ = build_gold.resolve_decision(row)
                gold_yazar = kind != SKIPPED_DECISION

                iaa_karari = report_iaa.row_verdict(row)
                iaa_sayar = iaa_karari is not None

                self.assertEqual(gold_yazar, golda_var)
                self.assertEqual(iaa_sayar, kapaya_girer)
                self.assertEqual(
                    gold_yazar, iaa_sayar,
                    f"{protokol}: gold'a giren satır kümesi ile κ'ya giren "
                    f"satır kümesi ayrıştı. Biri diğerini yalanlıyor.")

    def test_acik_karar_iki_protokolde_de_ayni(self):
        """Açık işaret protokolden bağımsızdır — taşıma bu yüzden kayıpsız."""
        for verdict in ("ok", "absent", "unclear"):
            for protokol in (PROTOCOL_V1, PROTOCOL_V2):
                with self.subTest(verdict=verdict, protokol=protokol):
                    row = _satir(verdict=verdict, **{PROTOCOL_COLUMN: protokol})
                    kind, _ = build_gold.resolve_decision(row)
                    self.assertNotEqual(kind, SKIPPED_DECISION)
                    self.assertEqual(report_iaa.row_verdict(row), verdict)

    def test_verdict_bos_gold_dolu_iki_protokolde_de_fix(self):
        """Anotatör düzeltmeyi yazıp verdict'i atlamışsa emek çöpe atılmaz."""
        for protokol in (PROTOCOL_V1, PROTOCOL_V2):
            with self.subTest(protokol=protokol):
                row = _satir(gold_value="36", **{PROTOCOL_COLUMN: protokol})
                kind, value = build_gold.resolve_decision(row)
                self.assertEqual(kind, "value")
                self.assertEqual(value, 36)
                self.assertEqual(report_iaa.row_verdict(row), "fix")


if __name__ == "__main__":
    unittest.main()
