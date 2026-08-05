"""Ablasyon tablo üreticisi testleri — belgeye giden sayı ÖLÇÜMDEN gelsin.

İlgili: ../eval/ablation_report.py
        ../docs/rapor/ablasyon.md (üretilen tablonun hedefi)

## Hangi hatayı kilitliyor

`docs/rapor/ablasyon.md` jüriye gösterilecek tablo. Elle yazılırsa iki hata
kaçınılmaz olur: kopyalama hatası (bir hanenin kayması sessizce metriği
değiştirir) ve bayatlama (kod değişip ölçüm yenilendiğinde belge eski sayıyı
göstermeye devam eder).

Bu testler üreticinin `metrics.json`'daki değerleri **olduğu gibi** taşıdığını
ve tanımsız değerleri (GA yok, halüsinasyon oranı tanımsız, kol ölçülmedi)
**0,0 gibi göstermediğini** kilitler. `0.000` yazmak "ölçtük, sıfır çıktı"
demektir; `ölçülemedi` yazmak "ölçmedik" demektir. İkisini karıştırmak jüriye
yanlış bilgi vermektir.
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from eval.ablation_report import (
    arms_table,
    counts_table,
    field_matrix,
    llm_stats,
    mcnemar_table,
    provenance,
    render,
)


def _micro(**kw) -> dict:
    base = {
        "precision": 0.5, "recall": 0.5, "f1": 0.5, "tp": 10, "fp": 10,
        "fn": 10, "tn": 10, "fp_hallucinated": 2, "fp_wrong": 8,
        "support": 20, "absent_decisions": 12, "hallucination_rate": 0.143,
        "skipped_undecided": 0, "unclear": 0,
    }
    base.update(kw)
    return base


def _ci(point: float, low: float, high: float) -> dict:
    return {"point": point, "low": low, "high": high, "width": high - low,
            "confidence": 0.95, "n_resamples": 1000, "n_units": 20,
            "seed": 42, "method": "percentile", "unit": "document"}


METRICS = {
    "kind": "ablation",
    "matcher": "strict",
    "documents": 20,
    "hard_documents": 1,
    "arms": [
        {"config": "kural", "description": "yalnız kural", "available": True,
         "documents": 20, "micro": _micro(f1=0.612, hallucination_rate=0.102),
         "macro_f1": 0.560, "ci_micro_f1": _ci(0.612, 0.483, 0.716),
         "hard": {"documents": 1, "micro": _micro(f1=0.667), "macro_f1": 0.667}},
        {"config": "llm", "description": "yalnız LLM", "available": True,
         "documents": 20, "micro": _micro(f1=0.480, hallucination_rate=None),
         "macro_f1": 0.455},
        {"config": "hibrit", "description": "teslim edilen", "available": False,
         "reason": "LLM backend kapalı (offline)"},
    ],
    "comparisons": [
        {"a": "kural", "b": "llm", "scope": "all",
         "mcnemar": {"b": 12, "c": 5, "n_discordant": 17, "n_pairs": 100,
                     "n_agree_correct": 40, "n_agree_wrong": 43,
                     "p_value": 0.1435, "method": "tam binom",
                     "statistic": None, "alpha": 0.05,
                     "significant": False, "winner": None},
         "micro_f1_diff_ci": _ci(0.132, -0.040, 0.290)},
        {"a": "kural", "b": "llm", "scope": "hard",
         "mcnemar": {"b": 2, "c": 0, "n_discordant": 2, "n_pairs": 3,
                     "n_agree_correct": 1, "n_agree_wrong": 0,
                     "p_value": 0.5, "method": "tam binom",
                     "statistic": None, "alpha": 0.05,
                     "significant": False, "winner": None}},
    ],
    "notes": ["`hibrit` ÖLÇÜLMEDİ: LLM backend kapalı (offline)"],
}

ENV = {
    "config": "ablation[kural,llm,hibrit]",
    "gold_path": "data/gold/gold.v1.json",
    "gold_sha256": "ea04e444755210577f6186658f17944256b7fbdfa5c0b5f7eeb9360f3c924b1a",
    "gold_records": 20,
    "matchers": ["strict"],
    "seed": 42,
    "git_sha": "caa260e0000000000000000000000000000000a",
    "git_dirty": False,
    "python_version": "3.14.6",
    "platform": "macOS-26.5.2-arm64-arm-64bit-Mach-O",
    "created_utc": "2026-08-04T21:00:00+00:00",
    "llm": {"available": True, "strict": True, "client": "OllamaClient",
            "structured_mode": "ollama_format", "calls": 60, "ok": 60,
            "parse_error": 0, "http_error": 0, "schema_violation": 0,
            "repairs": 0},
    "extra": {"bootstrap_resamples": 1000},
}

PER_FIELD = [
    {"config": "kural", "field": "finansman_tutari", "f1": "0.444", "support": "6"},
    {"config": "llm", "field": "finansman_tutari", "f1": "0.615", "support": "6"},
    {"config": "kural", "field": "alisveris_puani", "f1": "0.0", "support": "1"},
    {"config": "llm", "field": "alisveris_puani", "f1": "0.0", "support": "1"},
    {"config": "kural", "field": "masraf_durumu", "f1": "0.857", "support": "7"},
    {"config": "llm", "field": "masraf_durumu", "f1": "0.500", "support": "7"},
]


class TestKolTablosu(unittest.TestCase):
    def setUp(self):
        self.md = arms_table(METRICS)

    def test_olculen_sayilar_birebir_tasinir(self):
        self.assertIn("0.612", self.md)
        self.assertIn("0.560", self.md)
        self.assertIn("0.612 [0.483–0.716]", self.md)
        self.assertIn("0.102", self.md)

    def test_olculmeyen_kol_sifir_gibi_gosterilmez(self):
        """`hibrit` ölçülmedi — tabloda 0.000 DEĞİL, 'ÖLÇÜLMEDİ' yazmalı."""
        satir = [ln for ln in self.md.splitlines() if "`hibrit`" in ln]
        self.assertEqual(len(satir), 1)
        self.assertIn("ÖLÇÜLMEDİ", satir[0])
        self.assertNotIn("0.000", satir[0])

    def test_tanimsiz_halusinasyon_orani_sifir_yazilmaz(self):
        """`llm` kolunun oranı None — 'ölçülemedi' yazmalı, 0.000 değil."""
        satir = [ln for ln in self.md.splitlines() if "`llm`" in ln][0]
        self.assertIn("ölçülemedi", satir)

    def test_ga_yoksa_em_dash(self):
        satir = [ln for ln in self.md.splitlines() if "`llm`" in ln][0]
        self.assertIn("—", satir)

    def test_zor_alt_kume_kolonu(self):
        satir = [ln for ln in self.md.splitlines() if "`kural`" in ln][0]
        self.assertIn("0.667", satir)


class TestKarisiklikMatrisi(unittest.TestCase):
    def test_fp_kirilimi_ayri_kolonlarda(self):
        md = counts_table(METRICS)
        self.assertIn("FP (yanlış değer)", md)
        self.assertIn("FP (uydurma)", md)
        # Ölçülmeyen kol bu tabloda hiç görünmez (sahte satır yok).
        self.assertNotIn("`hibrit`", md)


class TestMcNemarTablosu(unittest.TestCase):
    def test_yontem_ve_p_gorunur(self):
        md = mcnemar_table(METRICS, "all")
        self.assertIn("tam binom", md)
        self.assertIn("0.1435", md)

    def test_anlamsiz_fark_kazanan_ilan_etmez(self):
        md = mcnemar_table(METRICS, "all")
        self.assertIn("fark anlamsız", md)
        self.assertNotIn("kazanan", md)

    def test_kapsam_suzgeci(self):
        """`hard` kapsamı istendiğinde `all` satırı gelmez."""
        md = mcnemar_table(METRICS, "hard")
        self.assertIn("0.5", md)
        self.assertNotIn("0.1435", md)

    def test_karsilastirma_yoksa_uydurma_tablo_yok(self):
        md = mcnemar_table({"comparisons": []}, "all")
        self.assertIn("en az iki ölçülebilen kol yok", md)


class TestAlanMatrisi(unittest.TestCase):
    def setUp(self):
        self.md = field_matrix(PER_FIELD, ["kural", "llm"])

    def test_kol_basina_alan_f1(self):
        satir = [ln for ln in self.md.splitlines()
                 if "finansman_tutari" in ln][0]
        self.assertIn("0.444", satir)
        self.assertIn("**0.615**", satir, "kazanan kol kalın olmalı")

    def test_ikisi_de_sifirsa_kazanan_ilan_edilmez(self):
        """Her iki kol 0.000 iken birini 'en iyi' diye kalınlaştırmak yanıltıcı."""
        satir = [ln for ln in self.md.splitlines()
                 if "alisveris_puani" in ln][0]
        self.assertNotIn("**", satir)

    def test_kural_kazandiginda_kural_kalin(self):
        satir = [ln for ln in self.md.splitlines() if "masraf_durumu" in ln][0]
        self.assertIn("**0.857**", satir)


class TestKunye(unittest.TestCase):
    def test_git_sha_ve_gold_sha_gorunur(self):
        md = provenance(ENV, METRICS)
        self.assertIn("caa260e", md)
        self.assertIn("ea04e444755210", md)
        self.assertIn("42", md)

    def test_kirli_agac_uyarisi(self):
        md = provenance({**ENV, "git_dirty": True}, METRICS)
        self.assertIn("EVET", md)

    def test_llm_sayaclari(self):
        md = llm_stats(ENV)
        self.assertIn("OllamaClient", md)
        self.assertIn("ollama_format", md)
        self.assertIn("60", md)


class TestUctanUca(unittest.TestCase):
    def test_render_diskteki_kosumdan_uretir(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp)
            (run_dir / "metrics.json").write_text(
                json.dumps(METRICS), encoding="utf-8")
            (run_dir / "env.json").write_text(json.dumps(ENV), encoding="utf-8")

            md = render(run_dir, with_fields=False)

        self.assertIn("Eşleştirici `strict`", md)
        self.assertIn("0.612 [0.483–0.716]", md)
        self.assertIn("ÖLÇÜLMEDİ", md)
        self.assertIn("tam binom", md)
        # Not bölümü sessiz sınırlama bırakmaz.
        self.assertIn("LLM backend kapalı", md)


if __name__ == "__main__":
    unittest.main()
