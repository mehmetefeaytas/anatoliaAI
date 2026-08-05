"""Ön-anotasyon üretici testleri (`scripts/preannotate.py`).

Çalıştır:  python -m unittest tests.test_preannotate  (app/ kökünden)

Buradaki testler tek bir soruyu kovalıyor: **anotatörün önüne konan 250 belge
gerçekten 250 AYRI, ANOTE EDİLEBİLİR belge mi?** Bu katmanda kaybedilen şey
sessiz kaybolur — ne bir istisna atılır ne metrik bozulur, yalnızca insan
zamanı çöpe gider ve gold beklenenden küçük çıkar.
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.preannotate import (
    RawDoc,
    annotate_doc,
    read_pinned_ids,
    read_raw_docs,
    sample_docs,
)
from src.schemas import ExtractedField

# `min_chars` eşiğini (250) geçen, kural katmanının değer bulacağı gövde.
GOVDE = ("Konut finansmanında kâr payı oranı %1,89 ve vade 120 aya kadar. "
         "Kampanya 31.12.2026 tarihine kadar geçerlidir. Tahsis ücreti 500 TL. "
         "Başvuru şubelerden veya mobil uygulamadan yapılabilir; kampanya "
         "yalnızca bireysel müşteriler için geçerlidir ve banka koşulları "
         "değiştirme hakkını saklı tutar. ")


def yaz(root: Path, rel: str, text: str, **meta) -> Path:
    """`data/raw` düzeninde belge + provenance dosyası yazar."""
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    if meta:
        Path(f"{path}.meta.json").write_text(
            json.dumps(meta, ensure_ascii=False), encoding="utf-8")
    return path


class TestReadRawDocs(unittest.TestCase):
    def test_shell_pages_are_skipped(self):
        """`content_status: kabuk` = yalnız gezinme menüsü.

        `min_chars` bunları yakalamıyor (1-2 KB menü metni eşiği geçiyor);
        anotatöre giderse 12 alanın 12'si `absent` çıkar — tam kayıp.
        """
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            yaz(root, "banka/products/gercek.txt", GOVDE, content_hash="h1")
            yaz(root, "banka/products/kabuk.txt", GOVDE * 2,
                content_hash="h2", content_status="kabuk")

            docs = read_raw_docs(root)
            self.assertEqual([d.doc_id for d in docs], ["banka--gercek"])

            # Kapatılabilir olmalı: korpus onarımının kendisi bu belgeleri okur.
            hepsi = read_raw_docs(root, skip_shell=False)
            self.assertEqual(len(hepsi), 2)

    def test_same_text_collected_twice_is_deduped(self):
        """Aynı sayfa `live/` ve `products/` altında iki dosya olarak duruyor.

        `content_hash` HAM HTML'in hash'i olduğu için iki kayıtta farklı;
        tekilleştirme ona bakarsa belge gold'a iki kez girer ve metrik şişer.
        """
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            yaz(root, "banka/live/konut.txt", GOVDE, content_hash="hash-a")
            yaz(root, "banka/products/konut.txt", GOVDE, content_hash="hash-b")

            docs = read_raw_docs(root)
            self.assertEqual(len(docs), 1)

    def test_same_stem_different_text_gets_unique_ids(self):
        """Metin farklıysa belge ayrıdır ve kimliği de ayrı olmalı.

        Kimlik çakışırsa `to_review_csv` girdiyi sözlüğe çevirirken birini
        atar: plan 250 belge der, dosyalarda 243 belge olur.
        """
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            yaz(root, "banka/live/konut.txt", GOVDE, content_hash="hash-a")
            yaz(root, "banka/products/konut.txt", GOVDE + "Ek koşullar geçerlidir.",
                content_hash="hash-b")

            docs = read_raw_docs(root)
            ids = [d.doc_id for d in docs]
            self.assertEqual(len(ids), 2)
            self.assertEqual(len(set(ids)), 2, f"kimlikler çakıştı: {ids}")
            self.assertIn("banka--konut", ids)
            self.assertIn("banka--products-konut", ids)

    def test_short_documents_are_skipped(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            yaz(root, "banka/live/menu.txt", "Ana Sayfa Kartlar Krediler")
            self.assertEqual(read_raw_docs(root), [])


class TestSampleDocs(unittest.TestCase):
    @staticmethod
    def _docs(n: int) -> list[RawDoc]:
        return [RawDoc(doc_id=f"banka--doc-{i:03d}", bank_slug="banka",
                       text=GOVDE) for i in range(n)]

    def test_pinned_docs_survive_a_tight_limit(self):
        """Anote edilmiş belge örneklemden düşerse o emek ölçüm dışına çıkar."""
        docs = self._docs(40)
        pinned = frozenset({"banka--doc-030", "banka--doc-039"})
        secilen = {d.doc_id for d in sample_docs(docs, limit=5, seed=42,
                                                 pinned=pinned)}
        self.assertTrue(pinned <= secilen)
        self.assertEqual(len(secilen), 5, "sabitlenenler kotanın İÇİNDEN sayılmalı")

    def test_sampling_is_deterministic(self):
        docs = self._docs(40)
        birinci = [d.doc_id for d in sample_docs(docs, 10, seed=42)]
        ikinci = [d.doc_id for d in sample_docs(docs, 10, seed=42)]
        self.assertEqual(birinci, ikinci)


class _KapaliLLM:
    available = False
    structured_mode = None


class _SabitSiniflandirici:
    def classify(self, text: str):
        return "Konut Finansmanı", 0.9


def _alan(name: str, value, raw: str = "500 TL") -> ExtractedField:
    return ExtractedField(field_name=name, raw_value=raw, canonical_value=value,
                          confidence=0.9, source_span=raw,
                          confidence_source="rule_heuristic")


class TestSchemaViolatingValues(unittest.TestCase):
    """Şema dışı değer, DEĞER sayılmaz.

    Kural katmanı ara sıra alanın kanonik biçimini tutmayan bir değer üretiyor
    (en sık: `tahsis_ucreti` için para yerine oran — "tutarın %0,5'i").
    Bu değer `fields`'a girerse CSV'ye ön-doldurulur, boş verdict ONAY sayılır
    ve `build_gold` değeri gold'a yazar; hata en sonda `validate_gold`'da
    patlar — yani anotasyon bittikten sonra.
    """

    def _kayit(self):
        doc = RawDoc(doc_id="banka--doc-1", bank_slug="banka", text=GOVDE)
        alanlar = [
            _alan("tahsis_ucreti", {"rate": 0.5}, "%0,5"),
            _alan("vade_ay", 120, "120 ay"),
        ]
        with mock.patch("scripts.preannotate.rule_extract", return_value=alanlar):
            return annotate_doc(doc, _KapaliLLM(), _SabitSiniflandirici())

    def test_invalid_value_is_not_a_field(self):
        kayit = self._kayit()
        self.assertNotIn("tahsis_ucreti", kayit["fields"])
        self.assertIn("tahsis_ucreti", kayit["invalid_fields"])
        self.assertIn("tahsis_ucreti", kayit["missing_fields"])

    def test_invalid_value_keeps_its_evidence(self):
        """Kanıt kaybolmamalı: CSV bu kayıttan span'i işaretli uyarı satırı üretir."""
        payload = self._kayit()["invalid_fields"]["tahsis_ucreti"]
        self.assertEqual(payload["value"], {"rate": 0.5})
        self.assertIn("tahsis_ucreti", payload["schema_error"])
        self.assertEqual(payload["raw_value"], "%0,5")

    def test_valid_value_is_untouched(self):
        kayit = self._kayit()
        self.assertEqual(kayit["fields"]["vade_ay"]["value"], 120)


class TestSpanVerified(unittest.TestCase):
    """`span_verified` TAM belge metnine karşı doğrulanmalı.

    Eskiden `f.verify_span(f.source_span)` çağrılıyordu, yani ±40 karakterlik
    pencere DİZESİ. `span_start`/`span_end` tam metne göre offset olduğu için
    doğrulama anlamsızdı: ölçüm, alanların %94,7'sinde `false` — DOĞRU
    değerlerde bile. Doğru çağrıyla 196/196 alan doğrulanıyor.

    %95 `false` üreten bir "doğrulandı" alanı yokluğundan kötüdür: sinyal gibi
    görünür, gürültüdür. Doğru çağrı biçimi zaten `src/api/main.py`'de vardı.
    """

    def _kayit(self, raw: str, govde: str):
        # span'i gerçek metne oturt — çıkarıcıyı taklit ediyoruz.
        start = govde.index(raw)
        alan = ExtractedField(
            field_name="vade_ay", raw_value=raw, canonical_value=120,
            confidence=0.9, source_span=govde[max(0, start - 40): start + len(raw) + 40],
            confidence_source="rule_heuristic",
            span_start=start, span_end=start + len(raw))
        doc = RawDoc(doc_id="banka--doc-1", bank_slug="banka", text=govde)
        with mock.patch("scripts.preannotate.rule_extract", return_value=[alan]):
            return annotate_doc(doc, _KapaliLLM(), _SabitSiniflandirici())

    def test_gecerli_span_dogrulanir(self) -> None:
        govde = GOVDE if "120 ay" in GOVDE else GOVDE + " Vade 120 ay boyunca geçerlidir."
        kayit = self._kayit("120 ay", govde)
        self.assertTrue(kayit["fields"]["vade_ay"]["span_verified"],
                        "tam metne oturan span 'false' işaretlendi — "
                        "doğrulama yine pencere dizesine karşı yapılıyor")

    def test_yanlis_offset_dogrulanmaz(self) -> None:
        """Bayrak her zaman True dönen bir sabit olmamalı; yanlışı da yakalasın."""
        govde = GOVDE + " Vade 120 ay boyunca geçerlidir."
        start = govde.index("120 ay")
        alan = ExtractedField(
            field_name="vade_ay", raw_value="120 ay", canonical_value=120,
            confidence=0.9, source_span="120 ay", confidence_source="rule_heuristic",
            span_start=start + 5, span_end=start + 11)   # kaydırılmış offset
        doc = RawDoc(doc_id="banka--doc-2", bank_slug="banka", text=govde)
        with mock.patch("scripts.preannotate.rule_extract", return_value=[alan]):
            kayit = annotate_doc(doc, _KapaliLLM(), _SabitSiniflandirici())
        self.assertFalse(kayit["fields"]["vade_ay"]["span_verified"])


class TestReadPinnedIds(unittest.TestCase):
    def test_reads_doc_ids_from_review_csv(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "round0.csv"
            path.write_text(
                "doc_id;field;model_value;gold_value;verdict\r\n"
                "banka--a;vade_ay;12;;\r\n"
                "banka--a;kar_payi_orani;1.89;;ok\r\n"
                "banka--b;vade_ay;24;;\r\n",
                encoding="utf-8-sig")
            self.assertEqual(read_pinned_ids([str(path)]),
                             frozenset({"banka--a", "banka--b"}))

    def test_missing_file_is_loud(self):
        with self.assertRaises(FileNotFoundError):
            read_pinned_ids(["/olmayan/dosya.csv"])


if __name__ == "__main__":
    unittest.main()
