"""Ablasyon tahmin önbelleği testleri — eşleştirici karşılaştırması tek değişkenli kalsın.

İlgili: ../eval/ablation.py (`cache_predictions`, modül başlığı
        "`--matcher both` ve tahmin önbelleği")
        ../eval/predictors.py (tahmin üretimi TEK KAYNAĞI)

## Hangi hatayı kilitliyor

`run_ablation` her EŞLEŞTİRİCİ için bir kez çağrılır ve `score_all` belge
başına `predictor.predict()` çağırır. Önbellek olmadan `--matcher both` aynı
belgeyi kola **iki kez** sorar.

Kural katmanı için bu yalnız israftır (saf fonksiyon, aynı cevap). LLM kolu
için ise bir **ölçüm kusuru**dur: `strict` ile `tolerant` tablolarının farkı
tanım gereği yalnız eşleştiricinin katılığından gelmelidir, ama kol iki kez
sorulursa örnekleme gürültüsü bu farka sızar. O zaman "tolerant eşleştirici
şu kadar kazandırdı" cümlesi ölçülmemiş bir şeyi iddia eder.

`TestOnbellekEslestiriciArasi` bunu doğrudan kilitler: iki eşleştiriciyle
koşulan bir ablasyonda, DEĞİŞKEN çıktı veren bir kol bile her iki tabloda
aynı tahmin kümesiyle puanlanır.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from eval.ablation import cache_predictions, run_ablation
from eval.predictors import Predictor, field_values
from scripts.gold_schema import GoldRecord, load_gold
from src.schemas import ExtractedField, Extractor

GOLD_SAMPLE = Path(__file__).resolve().parents[1] / "data" / "gold" / "gold.sample.json"


def _field(name: str, value, conf: float = 0.9) -> ExtractedField:
    return ExtractedField(field_name=name, raw_value=str(value),
                          canonical_value=value, confidence=conf,
                          source_span=None, extractor=Extractor.LLM)


class SayanKol:
    """Çağrı sayan, DEĞİŞKEN çıktı veren sahte kol (ağ YOK).

    Değişkenliği kasıtlıdır: her çağrıda farklı bir `vade_ay` döndürür.
    Önbellek çalışıyorsa ikinci eşleştirici birinciyle aynı değeri görür;
    çalışmıyorsa değerler ayrışır ve test bunu yakalar.
    """

    def __init__(self) -> None:
        self.calls: list[str] = []

    def __call__(self, text: str) -> list[ExtractedField]:
        self.calls.append(text)
        return [_field("vade_ay", len(self.calls))]


class SahteCikarici:
    """`LLMExtractor.summary()` arayüzünü taklit eden sahte çıkarıcı (ağ YOK)."""

    def __init__(self) -> None:
        self.calls = 0
        self.available = True

    def summary(self) -> dict:
        return {"available": self.available, "strict": True,
                "structured_mode": "sahte", "client": "SahteCikarici",
                "calls": self.calls, "ok": self.calls}


class TestOnbellekTemelDavranis(unittest.TestCase):
    """Aynı metin bir kez sorulur, sonuç birebir aynı nesne kümesidir."""

    def test_ayni_metin_tek_kez_sorulur(self):
        kol = SayanKol()
        p = cache_predictions(Predictor("llm", "sahte", kol))

        self.assertEqual(p.predict("metin A"), {"vade_ay": 1})
        self.assertEqual(p.predict("metin A"), {"vade_ay": 1})
        self.assertEqual(len(kol.calls), 1, "aynı metin ikinci kez soruldu")

    def test_farkli_metin_ayri_ayri_sorulur(self):
        kol = SayanKol()
        p = cache_predictions(Predictor("llm", "sahte", kol))

        p.predict("metin A")
        p.predict("metin B")
        p.predict("metin A")
        self.assertEqual(kol.calls, ["metin A", "metin B"])

    def test_ozgun_predictor_degismez(self):
        """`cache_predictions` KOPYA üretir; çağıran önbelleksiz kolu korur."""
        kol = SayanKol()
        ozgun = Predictor("llm", "sahte", kol)
        onbellekli = cache_predictions(ozgun)

        self.assertIsNot(ozgun, onbellekli)
        self.assertIs(ozgun.fn, kol, "özgün kolun fn'i değiştirildi")
        ozgun.predict("metin A")
        ozgun.predict("metin A")
        self.assertEqual(len(kol.calls), 2, "özgün kol beklenmedik şekilde belledi")

    def test_kimlik_alanlari_korunur(self):
        kol = SayanKol()
        ozgun = Predictor("llm", "yalnız LLM katmanı", kol, llm=SahteCikarici())
        onbellekli = cache_predictions(ozgun)

        self.assertEqual(onbellekli.name, ozgun.name)
        self.assertEqual(onbellekli.description, ozgun.description)
        self.assertTrue(onbellekli.available)
        self.assertEqual(onbellekli.llm_summary, ozgun.llm_summary)

    def test_llm_sayaclari_canli_okunur(self):
        """Sayaçlar koşum sırasında artar; `llm_summary` donmuş kopya OLMAMALI.

        Eski kod `build_predictor` içinde `summary()`'yi bir kez çağırıp
        sonucu saklıyordu, bu yüzden rapora her zaman `calls: 0` düşüyordu.
        """
        cikarici = SahteCikarici()
        p = cache_predictions(Predictor("llm", "sahte", SayanKol(),
                                        llm=cikarici))

        self.assertEqual(p.llm_summary["calls"], 0)
        cikarici.calls += 7
        self.assertEqual(p.llm_summary["calls"], 7,
                         "llm_summary donmuş kopya döndürüyor")


class TestOlculemeyenKol(unittest.TestCase):
    """Ölçülemeyen kol olduğu gibi döner — `available=False` sözleşmesi gizlenmez."""

    def test_olculemeyen_kol_sarmalanmaz(self):
        olculemeyen = Predictor(
            "hibrit", "teslim edilen sistem", fn=lambda _t: [],
            available=False, unavailable_reason="LLM backend kapalı (offline)")
        sonuc = cache_predictions(olculemeyen)

        self.assertIs(sonuc, olculemeyen)
        self.assertFalse(sonuc.available)


class TestOnbellekEslestiriciArasi(unittest.TestCase):
    """ASIL TEST: iki eşleştirici AYNI tahmin kümesini puanlar.

    Bu kilitlenmezse `strict` ve `tolerant` tablolarının farkı, eşleştiricinin
    katılığı yerine LLM örnekleme gürültüsünü yansıtabilir.
    """

    def setUp(self):
        self.records: list[GoldRecord] = load_gold(GOLD_SAMPLE)
        self.assertTrue(self.records, "gold.sample.json boş")

    def test_iki_eslestirici_tek_tahmin_kumesi(self):
        kol = SayanKol()
        p = cache_predictions(Predictor("llm", "sahte", kol))

        for matcher_name in ("strict", "tolerant"):
            run_ablation(self.records, [p], matcher_name, bootstrap=False)

        # Belge başına TEK çağrı — eşleştirici sayısından bağımsız.
        self.assertEqual(len(kol.calls), len(self.records),
                         "eşleştirici başına yeniden soruldu (önbellek çalışmıyor)")

    def test_onbelleksiz_kol_eslestirici_basina_yeniden_sorulur(self):
        """Kusurun gerçekten var olduğunu gösterir (test anlamlı olsun diye)."""
        kol = SayanKol()
        p = Predictor("llm", "sahte", kol)  # önbellek YOK

        for matcher_name in ("strict", "tolerant"):
            run_ablation(self.records, [p], matcher_name, bootstrap=False)

        self.assertEqual(len(kol.calls), 2 * len(self.records))


class TestKuralKoluIcinDegersizlik(unittest.TestCase):
    """Saf (deterministik) kol için önbellek sonucu DEĞİŞTİRMEZ — yalnız hızlandırır."""

    def test_saf_kol_sonucu_ayni(self):
        cagri = {"n": 0}

        def saf(text: str) -> list[ExtractedField]:
            cagri["n"] += 1
            return [_field("vade_ay", 120), _field("kar_payi_orani", 1.89)]

        ozgun = Predictor("kural", "sahte", saf)
        beklenen = field_values(saf("metin"))
        cagri["n"] = 0

        onbellekli = cache_predictions(ozgun)
        self.assertEqual(onbellekli.predict("metin"), beklenen)
        self.assertEqual(onbellekli.predict("metin"), beklenen)
        self.assertEqual(cagri["n"], 1)


if __name__ == "__main__":
    unittest.main()
