"""Gold şema v1 testleri — yükleme, geriye uyumluluk, kanonik doğrulama.

Çalıştır:  python -m unittest tests.test_gold_schema  (app/ kökünden)
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.gold_schema import (  # noqa: E402
    ALL_HARD_TAGS,
    GoldRecord,
    GoldValidationError,
    extract_hard_tags,
    format_gold_value,
    load_gold,
    parse_gold_value,
    record_from_dict,
    validate_canonical,
    validate_gold,
    values_equal,
    write_gold,
)
from src.extraction.llm.schema import EXTRACTION_FIELDS  # noqa: E402

_ROOT = Path(__file__).resolve().parents[1]
SAMPLE = _ROOT / "data" / "gold" / "gold.sample.json"


class TestLegacyCompatibility(unittest.TestCase):
    """v0 (`hard: bool`) kayıtları kayıpsız okunmalı — mevcut 3 kayıt dahil."""

    def test_sample_file_loads(self):
        records = load_gold(SAMPLE)
        self.assertEqual(len(records), 3)
        self.assertTrue(all(r.text for r in records))

    def test_hard_bool_becomes_legacy_tag(self):
        """`hard: true` hangi KATEGORİ olduğunu söylemiyor -> `legacy`."""
        records = load_gold(SAMPLE)
        hard = [r for r in records if r.hard_tags]
        self.assertEqual(len(hard), 2)          # örnekte 2 kayıt hard:true
        for record in hard:
            self.assertEqual(record.hard_tags, ["legacy"])

    def test_hard_false_gives_no_tags(self):
        records = load_gold(SAMPLE)
        easy = [r for r in records if not r.hard_tags]
        self.assertEqual(len(easy), 1)

    def test_legacy_records_get_stable_ids(self):
        """id yoksa metinden türetilir; iki yükleme aynı id'yi vermeli."""
        first = [r.id for r in load_gold(SAMPLE)]
        second = [r.id for r in load_gold(SAMPLE)]
        self.assertEqual(first, second)
        self.assertTrue(all(i.startswith("legacy-") for i in first))
        self.assertEqual(len(set(first)), 3)

    def test_legacy_absent_fields_default_empty(self):
        """v0'da absent_fields yoktu; boş liste olmalı, None değil."""
        for record in load_gold(SAMPLE):
            self.assertEqual(record.absent_fields, [])

    def test_to_dict_keeps_hard_key_for_existing_evaluator(self):
        """Mevcut değerlendirme harness'i (dokunulmadı) `item.get("hard")` okuyor."""
        record = record_from_dict({"text": "x", "fields": {}, "hard": True})
        self.assertIs(record.to_dict()["hard"], True)
        self.assertEqual(record.to_dict()["hard_tags"], ["legacy"])

    def test_v1_record_round_trips(self):
        original = GoldRecord(
            id="kuveyt-turk-konut-001",
            text="Konut finansmanında kâr payı oranı %1,89.",
            fields={"kar_payi_orani": 1.89},
            absent_fields=["vade_ay"],
            hard_tags=["terminoloji"],
            bank_slug="kuveyt-turk",
            campaign_type="Konut Finansmanı",
            annotators=["A", "B"],
        )
        restored = record_from_dict(original.to_dict())
        self.assertEqual(restored.id, original.id)
        self.assertEqual(restored.fields, original.fields)
        self.assertEqual(restored.absent_fields, original.absent_fields)
        self.assertEqual(restored.hard_tags, original.hard_tags)
        self.assertEqual(restored.annotators, original.annotators)


class TestCanonicalValidation(unittest.TestCase):
    """Kanonik biçim doğrulaması — hata mesajı NET olmalı."""

    def test_valid_values(self):
        cases = [
            ("kar_payi_orani", 1.89),
            ("kar_payi_orani", {"min": 1.99, "max": 2.49}),
            ("indirim_orani", 10),
            ("finansman_tutari", {"value": 500000.0, "currency": "TRY"}),
            ("tahsis_ucreti", {"value": 0, "currency": "TRY"}),
            ("vade_ay", 120),
            ("taksit_sayisi", 6),
            ("masraf_durumu", {"has_fee": False, "amount": 0.0}),
            ("masraf_durumu", {"has_fee": True, "amount": 500}),
            ("masraf_durumu", {"has_fee": True, "amount": None}),
            ("alisveris_puani", {"kind": "rate", "value": 5}),
            ("alisveris_puani", {"kind": "points", "value": 1000}),
            ("kampanya_suresi", "2026-12-31"),
            ("kampanya_kosullari", ["İlk 6 ay %0 uygulanır."]),
            ("hedef_kitle", ["yeni_musteri", "maas_musterisi"]),
            ("campaign_type", "Konut Finansmanı"),
        ]
        for name, value in cases:
            with self.subTest(field=name, value=value):
                self.assertIsNone(validate_canonical(name, value))

    def test_rate_as_string_rejected(self):
        error = validate_canonical("kar_payi_orani", "%1,89")
        self.assertIsNotNone(error)
        self.assertIn("1.89", error)          # doğru biçim örneği verilmeli

    def test_degenerate_range_rejected(self):
        """min == max olan aralık, aralık değildir; kıyaslamadan sessizce düşer."""
        error = validate_canonical("kar_payi_orani", {"min": 1.89, "max": 1.89})
        self.assertIn("Düz sayı yaz", error)

    def test_inverted_range_rejected(self):
        self.assertIn("min > max",
                      validate_canonical("kar_payi_orani", {"min": 3.0, "max": 1.0}))

    def test_money_requires_currency(self):
        self.assertIn("currency", validate_canonical("tahsis_ucreti", {"value": 500}))

    def test_foreign_currency_rejected(self):
        self.assertIn("TRY", validate_canonical(
            "odul_miktari", {"value": 100, "currency": "USD"}))

    def test_term_must_be_int_not_string(self):
        error = validate_canonical("vade_ay", "120 ay")
        self.assertIn("tamsayı", error)

    def test_term_float_rejected(self):
        self.assertIsNotNone(validate_canonical("vade_ay", 120.5))

    def test_date_must_be_iso(self):
        error = validate_canonical("kampanya_suresi", "31.12.2026")
        self.assertIn("2026-12-31", error)

    def test_fee_free_must_have_zero_amount(self):
        """'masrafsız' ise amount 0 olmalı — bu bilgi eksikliği DEĞİL."""
        error = validate_canonical("masraf_durumu",
                                   {"has_fee": False, "amount": 250})
        self.assertIn("masrafsız", error)

    def test_points_requires_kind(self):
        error = validate_canonical("alisveris_puani", {"value": 5})
        self.assertIn("kind", error)

    def test_points_kind_must_be_rate_or_points(self):
        self.assertIn("rate", validate_canonical(
            "alisveris_puani", {"kind": "mil", "value": 5}))

    def test_unknown_segment_label_rejected(self):
        error = validate_canonical("hedef_kitle", ["emekli"])
        self.assertIn("yeni_musteri", error)   # izin verilenler listelenmeli

    def test_duplicate_segment_rejected(self):
        self.assertIsNotNone(validate_canonical(
            "hedef_kitle", ["yeni_musteri", "yeni_musteri"]))

    def test_none_value_directed_to_absent_fields(self):
        error = validate_canonical("vade_ay", None)
        self.assertIn("absent_fields", error)

    def test_unknown_field_lists_valid_fields(self):
        error = validate_canonical("kar_orani", 1.0)
        self.assertIn("kar_payi_orani", error)

    def test_unknown_campaign_type_lists_the_eight(self):
        error = validate_canonical("campaign_type", "Mevduat")
        self.assertIn("Konut Finansmanı", error)


class TestRecordInvariants(unittest.TestCase):
    def test_field_cannot_be_both_present_and_absent(self):
        """Çekirdek değişmez: bir alan ya vardır ya yoktur."""
        record = GoldRecord(id="x", text="t", fields={"vade_ay": 12},
                            absent_fields=["vade_ay"])
        errors = record.validate()
        self.assertTrue(any("absent_fields" in e for e in errors))

    def test_unknown_hard_tag_rejected(self):
        record = GoldRecord(id="x", text="t", hard_tags=["zor"])
        self.assertTrue(any("zor" in e for e in record.validate()))

    def test_all_known_hard_tags_accepted(self):
        record = GoldRecord(id="x", text="t", hard_tags=list(ALL_HARD_TAGS))
        self.assertEqual(record.validate(), [])

    def test_empty_text_rejected(self):
        self.assertTrue(any("text" in e for e in GoldRecord(id="x", text=" ").validate()))

    def test_duplicate_ids_rejected(self):
        records = [GoldRecord(id="same", text="a"), GoldRecord(id="same", text="b")]
        self.assertTrue(any("benzersiz" in e for e in validate_gold(records)))

    def test_coverage_counts_decided_fields(self):
        record = GoldRecord(id="x", text="t", fields={"vade_ay": 12},
                            absent_fields=["kar_payi_orani", "tahsis_ucreti"])
        self.assertEqual(record.coverage(), 3)

    def test_full_coverage_is_twelve(self):
        record = GoldRecord(id="x", text="t",
                            absent_fields=list(EXTRACTION_FIELDS))
        self.assertEqual(record.coverage(), 12)


class TestParseGoldValue(unittest.TestCase):
    """Anotatörün elle yazdığı serbest TR metni kanonik biçime çevrilmeli."""

    def test_turkish_rate(self):
        self.assertEqual(parse_gold_value("kar_payi_orani", "%1,89"), 1.89)
        self.assertEqual(parse_gold_value("kar_payi_orani", "1,89"), 1.89)

    def test_rate_range(self):
        self.assertEqual(parse_gold_value("kar_payi_orani", "%1,99 - %2,49"),
                         {"min": 1.99, "max": 2.49})

    def test_degenerate_range_collapses(self):
        self.assertEqual(
            parse_gold_value("kar_payi_orani", '{"min": 1.89, "max": 1.89}'), 1.89)

    def test_turkish_money_thousands_separator(self):
        self.assertEqual(parse_gold_value("finansman_tutari", "1.500,00 TL"),
                         {"value": 1500.0, "currency": "TRY"})

    def test_term_from_years(self):
        self.assertEqual(parse_gold_value("vade_ay", "1 yıl"), 12)
        self.assertEqual(parse_gold_value("vade_ay", "1,5 yıl"), 18)
        self.assertEqual(parse_gold_value("vade_ay", "120 ay"), 120)

    def test_date_variants(self):
        for raw in ("31.12.2026", "31/12/2026", "31 Aralık 2026", "2026-12-31"):
            with self.subTest(raw=raw):
                self.assertEqual(parse_gold_value("kampanya_suresi", raw),
                                 "2026-12-31")

    def test_negation_becomes_zero_fee(self):
        """'masrafsız' -> masraf SIFIR; bilgi yok değil."""
        self.assertEqual(parse_gold_value("masraf_durumu", "masrafsız"),
                         {"has_fee": False, "amount": 0.0})
        self.assertEqual(parse_gold_value("masraf_durumu", "ücret alınmaz"),
                         {"has_fee": False, "amount": 0.0})

    def test_points_shortcut(self):
        self.assertEqual(parse_gold_value("alisveris_puani", "puan=1000"),
                         {"kind": "points", "value": 1000.0})
        self.assertEqual(parse_gold_value("alisveris_puani", "oran=5"),
                         {"kind": "rate", "value": 5.0})

    def test_list_pipe_separator(self):
        """CSV ayırıcısı ';' olduğu için liste ayırıcısı '|'."""
        self.assertEqual(
            parse_gold_value("hedef_kitle", "yeni_musteri | maas_musterisi"),
            ["yeni_musteri", "maas_musterisi"])

    def test_campaign_type_case_insensitive(self):
        self.assertEqual(parse_gold_value("campaign_type", "konut finansmanı"),
                         "Konut Finansmanı")

    def test_excel_locale_damage_survives(self):
        """TR Excel `1.89`u kaydederken `1,89` yapar; okuma bozulmamalı."""
        self.assertEqual(parse_gold_value("kar_payi_orani", "1,89"), 1.89)

    def test_empty_value_gives_actionable_error(self):
        with self.assertRaises(GoldValidationError) as ctx:
            parse_gold_value("vade_ay", "   ")
        self.assertIn("absent", str(ctx.exception))

    def test_unparseable_value_names_the_field(self):
        with self.assertRaises(GoldValidationError) as ctx:
            parse_gold_value("kampanya_suresi", "yakında")
        self.assertIn("kampanya_suresi", str(ctx.exception))

    def test_invalid_segment_rejected(self):
        with self.assertRaises(GoldValidationError):
            parse_gold_value("hedef_kitle", "emekli")

    def test_round_trip_format_then_parse(self):
        """format -> parse aynı değeri vermeli (CSV gidiş-dönüş garantisi)."""
        cases = [
            ("kar_payi_orani", 1.89),
            ("kar_payi_orani", {"min": 1.99, "max": 2.49}),
            ("finansman_tutari", {"value": 1500.0, "currency": "TRY"}),
            ("vade_ay", 120),
            ("taksit_sayisi", 6),
            ("masraf_durumu", {"has_fee": False, "amount": 0.0}),
            ("masraf_durumu", {"has_fee": True, "amount": 500.0}),
            ("alisveris_puani", {"kind": "points", "value": 1000.0}),
            ("kampanya_suresi", "2026-12-31"),
            ("hedef_kitle", ["yeni_musteri", "maas_musterisi"]),
            ("kampanya_kosullari", ["İlk 6 ay %0 uygulanır."]),
            ("campaign_type", "Taşıt Finansmanı"),
        ]
        for name, value in cases:
            with self.subTest(field=name, value=value):
                text = format_gold_value(name, value)
                self.assertEqual(parse_gold_value(name, text), value)


class TestValuesEqual(unittest.TestCase):
    def test_float_tolerance(self):
        self.assertTrue(values_equal(1.89, 1.8900000001))
        self.assertFalse(values_equal(1.89, 1.90))

    def test_int_float_equivalence(self):
        self.assertTrue(values_equal(120, 120.0))

    def test_nested_dict(self):
        self.assertTrue(values_equal({"value": 500, "currency": "TRY"},
                                     {"value": 500.0, "currency": "TRY"}))
        self.assertFalse(values_equal({"value": 500, "currency": "TRY"},
                                      {"value": 501, "currency": "TRY"}))

    def test_list_order_matters(self):
        self.assertFalse(values_equal(["a", "b"], ["b", "a"]))

    def test_bool_is_not_number(self):
        self.assertFalse(values_equal(True, 1))


class TestHardTagExtraction(unittest.TestCase):
    def test_hashtags_become_tags(self):
        self.assertEqual(extract_hard_tags("metin çelişiyor #celiskili"),
                         ["celiskili"])

    def test_multiple_tags(self):
        tags = extract_hard_tags("#terminoloji ve #format_varyant")
        self.assertEqual(sorted(tags), ["format_varyant", "terminoloji"])

    def test_unknown_hashtag_ignored(self):
        self.assertEqual(extract_hard_tags("#acayip bir durum"), [])

    def test_duplicates_collapsed(self):
        self.assertEqual(extract_hard_tags("#celiskili #celiskili"), ["celiskili"])

    def test_empty_note(self):
        self.assertEqual(extract_hard_tags(""), [])


class TestWriteGold(unittest.TestCase):
    def test_writes_json_and_sha256(self):
        records = [GoldRecord(id="a", text="metin", fields={"vade_ay": 12},
                              absent_fields=["kar_payi_orani"])]
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "gold.v1.json"
            digest = write_gold(records, target)

            self.assertTrue(target.exists())
            checksum = Path(f"{target}.sha256")
            self.assertTrue(checksum.exists())
            self.assertIn(digest, checksum.read_text(encoding="utf-8"))

            data = json.loads(target.read_text(encoding="utf-8"))
            self.assertEqual(data[0]["id"], "a")
            self.assertEqual(data[0]["absent_fields"], ["kar_payi_orani"])
            self.assertIn("hard", data[0])          # eski harness uyumu

    def test_reload_preserves_content(self):
        records = [GoldRecord(id="a", text="metin",
                              fields={"kar_payi_orani": 1.89},
                              absent_fields=["vade_ay"],
                              hard_tags=["kosullu_aralik"])]
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "gold.v1.json"
            write_gold(records, target)
            reloaded = load_gold(target)
            self.assertEqual(reloaded[0].fields, {"kar_payi_orani": 1.89})
            self.assertEqual(reloaded[0].absent_fields, ["vade_ay"])
            self.assertEqual(reloaded[0].hard_tags, ["kosullu_aralik"])
            self.assertEqual(validate_gold(reloaded), [])


if __name__ == "__main__":
    unittest.main()
