"""Değerlendirme harness'inin KENDİ testi — metrik doğru mu sayıyor?

İlgili: ../eval/run_eval.py, ../eval/report.py

Metrik harness'ının test edilmemiş olması kabul edilemez: yanlış sayan bir
eval, olmayan bir başarıyı raporlar ve kimse fark etmez. Buradaki testler
sentetik mini gold ile ÇALIŞTIRILIR (gerçek gold seti henüz yok; kod 3 kayıtla
da 250 kayıtla da çalışmalı).

En kritik sınıf `TestAbsentFields`: eski kodun tamamen kaçırdığı ayrım.
"kontrol ettim, YOK" ile "hiç bakılmadı" farkı olmadan precision tanımsızdır.
"""

from __future__ import annotations

import contextlib
import csv
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from typing import ClassVar

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from eval.matchers import strict_match, tolerant_match
from eval.predictors import CONFIG_KURAL, Predictor, build_predictor
from eval.run_eval import (
    SPLITS,
    Counts,
    aggregate,
    build_arg_parser,
    by_hard_tag,
    evaluate,
    macro_f1,
    main,
    micro,
    score_document,
    select_split,
)
from scripts.gold_schema import GoldRecord
from src.schemas import ExtractedField, Extractor


def fake_predictor(mapping: dict[str, dict]) -> Predictor:
    """Metin -> sabit tahmin sözlüğü döndüren sahte üretici (deterministik)."""
    def fn(text: str) -> list[ExtractedField]:
        return [ExtractedField(field_name=k, raw_value=str(v), canonical_value=v,
                               confidence=0.9, source_span=None,
                               extractor=Extractor.RULE)
                for k, v in mapping.get(text, {}).items()]
    return Predictor("sahte", "test amaçlı sabit üretici", fn)


class TestCounts(unittest.TestCase):
    """Sayaç aritmetiği."""

    def test_bos_sayac_sifir(self):
        c = Counts()
        self.assertEqual((c.precision(), c.recall(), c.f1()), (0.0, 0.0, 0.0))

    def test_mukemmel_skor(self):
        c = Counts(tp=10)
        self.assertEqual((c.precision(), c.recall(), c.f1()), (1.0, 1.0, 1.0))

    def test_bilinen_f1(self):
        """TP=8, FP=2, FN=4 -> P=0,8 R=0,667 F1=0,727."""
        c = Counts(tp=8, fp=2, fn=4)
        self.assertAlmostEqual(c.precision(), 0.8)
        self.assertAlmostEqual(c.recall(), 8 / 12)
        self.assertAlmostEqual(c.f1(), 2 * 0.8 * (8 / 12) / (0.8 + 8 / 12))

    def test_halusinasyon_orani(self):
        c = Counts(tn=8, fp_hallucinated=2, fp=2)
        self.assertAlmostEqual(c.hallucination_rate(), 0.2)
        self.assertEqual(c.absent_decisions, 10)

    def test_absent_karari_yoksa_halusinasyon_TANIMSIZ(self):
        """0,0 yazmak "hiç uydurmadık" demektir — oysa doğru cevap "ölçemedik"."""
        self.assertIsNone(Counts(tp=5).hallucination_rate())

    def test_toplama(self):
        a, b = Counts(tp=1, fp=2, fn=3, tn=4), Counts(tp=10, fp=20, fn=30, tn=40)
        a.add(b)
        self.assertEqual((a.tp, a.fp, a.fn, a.tn), (11, 22, 33, 44))

    def test_support_ve_atlanan_ayri(self):
        c = Counts(tp=3, fn=2, skipped=7)
        self.assertEqual(c.support, 5)
        self.assertEqual(c.skipped, 7)


class TestPuanlama(unittest.TestCase):
    """`score_document` — karar tablosunun her satırı."""

    def test_dogru_deger_tp(self):
        record = GoldRecord(id="d1", text="t", fields={"vade_ay": 120})
        score = score_document(record, {"vade_ay": 120}, strict_match)
        self.assertEqual(score.per_field["vade_ay"].tp, 1)

    def test_yanlis_deger_FP_VE_FN(self):
        """Eski kod yalnız FP sayıyordu ve recall'u yapay olarak yükseltiyordu."""
        record = GoldRecord(id="d1", text="t", fields={"vade_ay": 120})
        counts = score_document(record, {"vade_ay": 36}, strict_match).per_field
        self.assertEqual(counts["vade_ay"].fp, 1)
        self.assertEqual(counts["vade_ay"].fn, 1)
        self.assertEqual(counts["vade_ay"].fp_wrong, 1)
        self.assertEqual(counts["vade_ay"].fp_hallucinated, 0)

    def test_kacirilan_deger_fn(self):
        record = GoldRecord(id="d1", text="t", fields={"vade_ay": 120})
        counts = score_document(record, {}, strict_match).per_field
        self.assertEqual(counts["vade_ay"].fn, 1)
        self.assertEqual(counts["vade_ay"].fp, 0)

    def test_karar_verilmemis_alan_metrige_girmez(self):
        """Bilmediğimizi lehimize DE aleyhimize DE sayamayız."""
        record = GoldRecord(id="d1", text="t", fields={"vade_ay": 120})
        counts = score_document(record, {"vade_ay": 120, "odul_miktari": 999},
                                strict_match).per_field
        odul = counts["odul_miktari"]
        self.assertEqual((odul.tp, odul.fp, odul.fn, odul.tn), (0, 0, 0, 0))
        self.assertEqual(odul.skipped, 1)

    def test_unclear_alan_metrige_girmez(self):
        record = GoldRecord(id="d1", text="t", fields={},
                            unclear_fields=["kar_payi_orani"])
        counts = score_document(record, {"kar_payi_orani": 1.89},
                                strict_match).per_field
        c = counts["kar_payi_orani"]
        self.assertEqual((c.tp, c.fp, c.fn, c.tn), (0, 0, 0, 0))
        self.assertEqual(c.unclear, 1)

    def test_kararlar_mcnemar_icin_kaydedilir(self):
        record = GoldRecord(id="d1", text="t", fields={"vade_ay": 120},
                            absent_fields=["odul_miktari"])
        score = score_document(record, {"vade_ay": 120}, strict_match)
        self.assertEqual(dict(score.decisions),
                         {"vade_ay": True, "odul_miktari": True})

    def test_gevsek_esleştirici_kullanilabilir(self):
        record = GoldRecord(id="d1", text="t", fields={"kar_payi_orani": 1.89})
        strict = score_document(record, {"kar_payi_orani": 1.90}, strict_match)
        tolerant = score_document(record, {"kar_payi_orani": 1.90}, tolerant_match)
        self.assertEqual(strict.per_field["kar_payi_orani"].tp, 0)
        self.assertEqual(tolerant.per_field["kar_payi_orani"].tp, 1)


class TestAbsentFields(unittest.TestCase):
    """`absent_fields` — eski kodun TAMAMEN kaçırdığı ayrım.

    "kontrol ettim, bu belgede YOK" ile "anotatör hiç bakmadı" ayrılmazsa
    precision tanımsızdır ve halüsinasyon oranı ölçülemez.
    """

    def test_dogru_cekimserlik_TN(self):
        record = GoldRecord(id="d1", text="t", absent_fields=["odul_miktari"])
        counts = score_document(record, {}, strict_match).per_field
        self.assertEqual(counts["odul_miktari"].tn, 1)
        self.assertEqual(counts["odul_miktari"].fp, 0)

    def test_uydurma_deger_HALUSINASYON_FP(self):
        record = GoldRecord(id="d1", text="t", absent_fields=["odul_miktari"])
        counts = score_document(record, {"odul_miktari": 500},
                                strict_match).per_field
        self.assertEqual(counts["odul_miktari"].fp, 1)
        self.assertEqual(counts["odul_miktari"].fp_hallucinated, 1)
        self.assertEqual(counts["odul_miktari"].fp_wrong, 0)

    def test_absent_ile_kararsiz_AYNI_DEGIL(self):
        """Aynı tahmin, iki farklı gold -> iki farklı sonuç. Ayrımın kanıtı."""
        uyduran = {"odul_miktari": 500}
        absent = GoldRecord(id="a", text="t", absent_fields=["odul_miktari"])
        kararsiz = GoldRecord(id="b", text="t")

        a = score_document(absent, uyduran, strict_match).per_field["odul_miktari"]
        b = score_document(kararsiz, uyduran, strict_match).per_field["odul_miktari"]
        self.assertEqual(a.fp_hallucinated, 1)
        self.assertEqual(b.fp_hallucinated, 0)
        self.assertEqual(b.skipped, 1)

    def test_halusinasyon_orani_uctan_uca(self):
        """4 absent kararı, 1 uydurma -> oran 0,25."""
        records = [
            GoldRecord(id=f"d{i}", text=f"t{i}",
                       absent_fields=["odul_miktari", "indirim_orani"])
            for i in range(2)
        ]
        preds = [{}, {"odul_miktari": 5}]
        docs = [score_document(r, p, strict_match) for r, p in zip(records, preds)]
        m = micro(aggregate(docs))
        self.assertEqual(m.absent_decisions, 4)
        self.assertEqual(m.fp_hallucinated, 1)
        self.assertAlmostEqual(m.hallucination_rate(), 0.25)

    def test_precision_absent_olmadan_yaniltici(self):
        """Aynı model, absent kararı eklenince precision DÜŞER — beklenen."""
        uyduran = {"vade_ay": 120, "odul_miktari": 500}
        dar = GoldRecord(id="a", text="t", fields={"vade_ay": 120})
        genis = GoldRecord(id="b", text="t", fields={"vade_ay": 120},
                           absent_fields=["odul_miktari"])
        p_dar = micro(aggregate([score_document(dar, uyduran, strict_match)]))
        p_genis = micro(aggregate([score_document(genis, uyduran, strict_match)]))
        self.assertEqual(p_dar.precision(), 1.0)      # uydurma GÖRÜNMÜYOR
        self.assertEqual(p_genis.precision(), 0.5)    # uydurma yakalandı


class TestMakroMikro(unittest.TestCase):
    """Makro seyrek alanları gizlemiyor mu?"""

    def test_makro_mikrodan_farkli(self):
        """Sık alan mükemmel, seyrek alan sıfır: mikro yüksek, makro düşük."""
        table = {
            "vade_ay": Counts(tp=99),                     # sık ve mükemmel
            "odul_miktari": Counts(fn=1),                 # seyrek ve tamamen kaçmış
        }
        self.assertAlmostEqual(micro(table).f1(), 2 * 99 / (2 * 99 + 1), places=4)
        self.assertAlmostEqual(macro_f1(table), 0.5)      # (1.0 + 0.0) / 2
        self.assertLess(macro_f1(table), micro(table).f1())

    def test_makro_desteksiz_alani_haric_tutar(self):
        """Gold'da hiç değeri olmayan alan makro ortalamayı bozmamalı."""
        table = {"vade_ay": Counts(tp=10), "odul_miktari": Counts(tn=5)}
        self.assertAlmostEqual(macro_f1(table), 1.0)

    def test_bos_tablo_sifir(self):
        self.assertEqual(macro_f1({}), 0.0)


class TestAltKumeler(unittest.TestCase):
    """`--split` ve zor-vaka etiketi kırılımı."""

    RECORDS: ClassVar[list] = [
        GoldRecord(id="k1", text="t1", fields={"vade_ay": 12}),
        GoldRecord(id="z1", text="t2", fields={"vade_ay": 24},
                   hard_tags=["terminoloji"]),
        GoldRecord(id="z2", text="t3", fields={"vade_ay": 36},
                   hard_tags=["terminoloji", "format_varyant"]),
    ]

    def test_all(self):
        self.assertEqual(len(select_split(self.RECORDS, "all")), 3)

    def test_hard(self):
        self.assertEqual([r.id for r in select_split(self.RECORDS, "hard")],
                         ["z1", "z2"])

    def test_easy(self):
        self.assertEqual([r.id for r in select_split(self.RECORDS, "easy")], ["k1"])

    def test_bilinmeyen_split_hata(self):
        with self.assertRaises(ValueError):
            select_split(self.RECORDS, "orta")

    def test_split_isimleri(self):
        self.assertEqual(set(SPLITS), {"all", "hard", "easy"})

    def test_etiket_kirilimi_ortusur(self):
        """Çok etiketli: bir belge iki tabloda birden görünür."""
        docs = [score_document(r, {"vade_ay": r.fields["vade_ay"]}, strict_match)
                for r in self.RECORDS]
        per_tag = by_hard_tag(docs)
        self.assertEqual(set(per_tag), {"terminoloji", "format_varyant"})
        self.assertEqual(micro(per_tag["terminoloji"]).tp, 2)
        self.assertEqual(micro(per_tag["format_varyant"]).tp, 1)


class TestEvaluate(unittest.TestCase):
    """`evaluate` — uçtan uca, sentetik mini gold ile."""

    def setUp(self):
        self.records = [
            GoldRecord(id="d1", text="a", fields={"vade_ay": 12},
                       absent_fields=["odul_miktari"]),
            GoldRecord(id="d2", text="b", fields={"vade_ay": 24},
                       absent_fields=["odul_miktari"], hard_tags=["celiskili"]),
        ]
        self.predictor = fake_predictor({
            "a": {"vade_ay": 12},
            "b": {"vade_ay": 99, "odul_miktari": 500},   # yanlış + uydurma
        })

    def test_temel_sayilar(self):
        """d1: vade_ay TP + odul TN. d2: vade_ay FP+FN (yanlış) + odul FP (uydurma)."""
        result = evaluate(self.records, self.predictor, "strict", bootstrap=False)
        m = result.micro
        self.assertEqual(m.tp, 1)               # yalnız vade_ay(d1)
        self.assertEqual(m.tn, 1)               # odul_miktari(d1) — doğru çekimserlik
        self.assertEqual(m.fp_wrong, 1)         # vade_ay(d2) yanlış değer
        self.assertEqual(m.fp_hallucinated, 1)  # odul_miktari(d2) uydurma
        self.assertEqual(m.fp, 2)               # ikisinin toplamı
        self.assertEqual(m.fn, 1)               # vade_ay(d2) doğru değeri kaçırdı
        self.assertAlmostEqual(m.hallucination_rate(), 0.5)   # 1 / (1 TN + 1 uyd.)

    def test_zor_alt_kumesi_ayri(self):
        result = evaluate(self.records, self.predictor, "strict", bootstrap=False)
        self.assertEqual(result.hard_docs, 1)
        self.assertTrue(result.hard_table)
        self.assertEqual(micro(result.hard_table).tp, 0)

    def test_bootstrap_ga_uretilir(self):
        result = evaluate(self.records, self.predictor, "strict",
                          bootstrap=True, n_resamples=100, seed=42)
        self.assertIsNotNone(result.ci_micro)
        self.assertEqual(result.ci_micro.n_units, 2)   # 2 BELGE
        self.assertEqual(result.ci_micro.seed, 42)

    def test_bootstrap_kapatilabilir(self):
        result = evaluate(self.records, self.predictor, "strict", bootstrap=False)
        self.assertIsNone(result.ci_micro)

    def test_sozluk_ciktisi_json_serilestirilebilir(self):
        result = evaluate(self.records, self.predictor, "strict",
                          bootstrap=True, n_resamples=50)
        json.dumps(result.as_dict())    # hata verirse test kırılır

    def test_tek_kayitla_calisir(self):
        """Kod 3 kayıtla da 250 kayıtla da çalışmalı."""
        result = evaluate(self.records[:1], self.predictor, "strict",
                          bootstrap=True, n_resamples=20)
        self.assertEqual(len(result.docs), 1)


class TestCLI(unittest.TestCase):
    """`main()` — uçtan uca, gerçek dosya yazma dahil."""

    GOLD: ClassVar[list] = [
        {"id": "g1",
         "text": "Konut finansmanında kâr payı oranı %1,89, 120 aya kadar vade.",
         "fields": {"kar_payi_orani": 1.89, "vade_ay": 120},
         "absent_fields": ["odul_miktari", "indirim_orani"],
         "hard_tags": []},
        {"id": "g2",
         "text": "İhtiyaç finansmanında ilk 6 ay masrafsız, 36 ay vade imkânı.",
         "fields": {"vade_ay": 36},
         "absent_fields": ["odul_miktari"],
         "hard_tags": ["eksik_bilgi"]},
    ]

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.gold_path = self.root / "gold.json"
        self.gold_path.write_text(json.dumps(self.GOLD, ensure_ascii=False),
                                  encoding="utf-8")
        self.out_dir = self.root / "reports"

    def tearDown(self):
        self.tmp.cleanup()

    def _run(self, *extra: str) -> int:
        # Konsol çıktısı bastırılır: harness'ın kendi tabloları test çıktısını
        # okunmaz hale getiriyor. Test edilen şey DÖNÜŞ KODU ve YAZILAN DOSYALAR.
        with contextlib.redirect_stdout(io.StringIO()):
            return main(["--gold", str(self.gold_path), "--config", CONFIG_KURAL,
                         "--out-dir", str(self.out_dir), "--resamples", "50",
                         *extra])

    @staticmethod
    def _quiet_main(argv: list[str]) -> int:
        with contextlib.redirect_stdout(io.StringIO()), \
                contextlib.redirect_stderr(io.StringIO()):
            return main(argv)

    def test_basarili_kosum(self):
        self.assertEqual(self._run(), 0)

    def test_dosyalar_yazilir(self):
        self._run()
        run_dirs = list(self.out_dir.iterdir())
        self.assertEqual(len(run_dirs), 1)
        for name in ("metrics.json", "report.md", "per_field.csv", "env.json"):
            with self.subTest(file=name):
                self.assertTrue((run_dirs[0] / name).is_file(), f"{name} yok")

    def test_env_json_kunye_tasir(self):
        """Tekrar-üretilemeyen bir sayı kanıt değildir."""
        self._run()
        env = json.loads(next(self.out_dir.iterdir()).joinpath("env.json")
                         .read_text(encoding="utf-8"))
        for key in ("git_sha", "gold_sha256", "python_version", "config",
                    "seed", "matchers", "split", "dependencies"):
            with self.subTest(key=key):
                self.assertIn(key, env)
        self.assertEqual(env["config"], CONFIG_KURAL)
        self.assertEqual(env["seed"], 42)
        self.assertEqual(len(env["gold_sha256"]), 64)

    def test_metrics_json_absent_alanlari_tasir(self):
        self._run()
        metrics = json.loads(next(self.out_dir.iterdir()).joinpath("metrics.json")
                             .read_text(encoding="utf-8"))
        micro_data = metrics["results"][0]["micro"]
        for key in ("fp_hallucinated", "fp_wrong", "tn", "absent_decisions",
                    "hallucination_rate", "skipped_undecided"):
            with self.subTest(key=key):
                self.assertIn(key, micro_data)
        self.assertEqual(micro_data["absent_decisions"], 3)

    def test_per_field_csv_okunabilir(self):
        self._run()
        path = next(self.out_dir.iterdir()) / "per_field.csv"
        with path.open(encoding="utf-8", newline="") as fh:
            rows = list(csv.DictReader(fh, delimiter=";"))
        self.assertTrue(rows)
        self.assertIn("fp_hallucinated", rows[0])
        self.assertTrue(any(r["field"] == "vade_ay" for r in rows))

    def test_her_iki_esleştirici_raporlanir(self):
        self._run("--matcher", "both")
        metrics = json.loads(next(self.out_dir.iterdir()).joinpath("metrics.json")
                             .read_text(encoding="utf-8"))
        self.assertEqual([r["matcher"] for r in metrics["results"]],
                         ["strict", "tolerant"])

    def test_no_write_dosya_uretmez(self):
        self.assertEqual(self._run("--no-write"), 0)
        self.assertFalse(self.out_dir.exists())

    def test_split_hard(self):
        self._run("--split", "hard")
        metrics = json.loads(next(self.out_dir.iterdir()).joinpath("metrics.json")
                             .read_text(encoding="utf-8"))
        self.assertEqual(metrics["documents"], 1)

    def test_eksik_gold_dosyasi_cikis_2(self):
        self.assertEqual(self._quiet_main(["--gold", str(self.root / "yok.json")]), 2)

    def test_bos_gold_cikis_2(self):
        """Boş gold ile üretilen bir metrik yanıltıcıdır."""
        empty = self.root / "empty.json"
        empty.write_text("[]", encoding="utf-8")
        self.assertEqual(self._quiet_main(["--gold", str(empty), "--no-write"]), 2)

    def test_bos_alt_kume_cikis_2(self):
        only_easy = self.root / "easy.json"
        only_easy.write_text(json.dumps([self.GOLD[0]], ensure_ascii=False),
                             encoding="utf-8")
        self.assertEqual(self._quiet_main(["--gold", str(only_easy),
                                           "--split", "hard", "--no-write"]), 2)

    def test_llm_gerektiren_konfig_offline_cikis_3(self):
        """Sahte satır basmaktansa AÇIK hata: çıkış 3."""
        self.assertEqual(self._quiet_main(["--gold", str(self.gold_path),
                                           "--config", "hibrit", "--no-write"]), 3)

    def test_ayni_seed_ayni_ga(self):
        """Determinizm: aynı seed + aynı veri = aynı GA."""
        predictor = build_predictor(CONFIG_KURAL)
        from scripts.gold_schema import load_gold
        records = load_gold(self.gold_path)
        a = evaluate(records, predictor, "strict", n_resamples=200, seed=42)
        b = evaluate(records, predictor, "strict", n_resamples=200, seed=42)
        self.assertEqual((a.ci_micro.low, a.ci_micro.high),
                         (b.ci_micro.low, b.ci_micro.high))

    def test_arg_parser_secenekleri(self):
        parser = build_arg_parser()
        args = parser.parse_args(["--gold", "x.json"])
        self.assertEqual(args.matcher, "both")
        self.assertEqual(args.split, "all")
        self.assertEqual(args.seed, 42)
        self.assertEqual(args.resamples, 1000)


if __name__ == "__main__":
    unittest.main()
