"""`mode="corpus"` testleri — gerçek korpus modu + fixture semantiğinin korunması.

İlgili: src/pipeline.py, CLAUDE.md §11

Bu dosyanın avladığı hata sınıfı: pipeline'ın SESSİZCE az belge yüklemesi.
Eski demo yolu 3 belge yükleyip "hazır" diyordu; hiçbir test bunu yakalamıyordu
çünkü hiçbir test "kaç belge yüklendi?" diye sormuyordu.
"""

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.db.repository import Repository  # noqa: E402
from src.pipeline import (  # noqa: E402
    MODE_CORPUS,
    MODE_FIXTURE,
    collect_corpus,
    run_pipeline,
)
from src.scraping.config import load_banks  # noqa: E402

CONFIG = str(ROOT / "config" / "banks.yaml")
RAW = str(ROOT / "data" / "raw")

# Fixture kümesinin boyutu — bu sayı DEĞİŞMEMELİ (testlerin deterministik zemini).
FIXTURE_DOCS = 3
# Korpusun bugünkü boyutu (2026-07-31 ölçümü). Alt sınır olarak kullanılır:
# korpus büyüyebilir, ama fixture seviyesine DÜŞMESİ sessiz bir gerilemedir.
CORPUS_DOCS_MIN = 800


def _yaz(kok: Path, rel: str, icerik: str) -> Path:
    yol = kok / rel
    yol.parent.mkdir(parents=True, exist_ok=True)
    yol.write_text(icerik, encoding="utf-8")
    return yol


def _mini_banks_yaml(hedef: Path, sluglar: list[str]) -> str:
    """Mini YAML parser'ın (pyyaml yoksa) anladığı biçimde banks.yaml üretir."""
    satirlar = ["banks:"]
    for s in sluglar:
        satirlar += [f"  - slug: {s}",
                     f"    name: {s.title()}",
                     "    website_url: https://ornek.invalid",
                     "    scrape_mode: manual"]
    hedef.write_text("\n".join(satirlar) + "\n", encoding="utf-8")
    return str(hedef)


class TestCollectCorpus(unittest.TestCase):
    """`collect_corpus` — özyinelemeli, yalnız .txt, provenance korumalı."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.kok = Path(self.tmp.name)
        self.raw = self.kok / "raw"
        _yaz(self.raw, "a-bank/kok.txt", "Kâr payı oranı %1,89.")
        _yaz(self.raw, "a-bank/live/canli.txt", "36 ay vade sunulur.")
        _yaz(self.raw, "a-bank/products/urun.txt", "Konut finansmanı %2,05.")
        _yaz(self.raw, "a-bank/manual/elle.txt", "Masrafsız kampanya.")
        # .html okunmamalı (çift sayım + markup gürültüsü)
        _yaz(self.raw, "a-bank/live/canli.html", "<p>%9,99 kâr payı</p>")
        # boş dosya atlanmalı
        _yaz(self.raw, "a-bank/live/bos.txt", "   \n  ")
        self.bank = load_banks(_mini_banks_yaml(self.kok / "banks.yaml",
                                                ["a-bank"]))[0]

    def tearDown(self):
        self.tmp.cleanup()

    def test_alt_klasorler_taranir(self):
        docs = collect_corpus(self.bank, raw_dir=str(self.raw))
        self.assertEqual(len(docs), 4, "kök + live + products + manual bekleniyor")

    def test_html_okunmaz(self):
        metinler = " ".join(d.clean_text for d in
                            collect_corpus(self.bank, raw_dir=str(self.raw)))
        self.assertNotIn("9,99", metinler)

    def test_bos_dosya_atlanir(self):
        adlar = {Path(d.source_url or "").name
                 for d in collect_corpus(self.bank, raw_dir=str(self.raw))}
        self.assertNotIn("bos.txt", adlar)

    def test_deterministik_sira(self):
        a = [d.source_url for d in collect_corpus(self.bank, raw_dir=str(self.raw))]
        b = [d.source_url for d in collect_corpus(self.bank, raw_dir=str(self.raw))]
        self.assertEqual(a, b)
        self.assertEqual(a, sorted(a))

    def test_sidecar_provenance_korunur(self):
        _yaz(self.raw, "a-bank/live/canli.txt.meta.json",
             '{"source_url": "https://banka.invalid/kampanya", '
             '"scraped_at": "2026-07-30T12:00:00+00:00", '
             '"collection_method": "live", "title": "Kampanya"}')
        docs = collect_corpus(self.bank, raw_dir=str(self.raw))
        doc = next(d for d in docs
                   if d.source_url == "https://banka.invalid/kampanya")
        self.assertEqual(doc.scraped_at, "2026-07-30T12:00:00+00:00")
        self.assertEqual(doc.collection_method, "live")
        self.assertEqual(doc.title, "Kampanya")
        # sidecar'sız belge uydurma URL almaz, file:// yoluna düşer
        koksuz = next(d for d in docs if d.source_url.endswith("kok.txt"))
        self.assertTrue(koksuz.source_url.startswith("file://"))

    def test_bozuk_sidecar_cokmez(self):
        _yaz(self.raw, "a-bank/live/canli.txt.meta.json", "{bozuk json")
        docs = collect_corpus(self.bank, raw_dir=str(self.raw))
        self.assertEqual(len(docs), 4)

    def test_olmayan_banka_bos_doner(self):
        yok = load_banks(_mini_banks_yaml(self.kok / "b.yaml", ["yok-boyle"]))[0]
        self.assertEqual(collect_corpus(yok, raw_dir=str(self.raw)), [])


class TestRunPipelineRaporlama(unittest.TestCase):
    """`run_pipeline` kapsamı raporlar — "3 belge yükledim" görünür olmalı."""

    def test_fixture_semantigi_korunur(self):
        repo = Repository(":memory:")
        res = run_pipeline(repo, CONFIG, raw_dir=RAW, mode=MODE_FIXTURE)
        self.assertEqual(res.documents_loaded, FIXTURE_DOCS)
        self.assertEqual(res.campaigns_stored, FIXTURE_DOCS)
        self.assertEqual(res.mode, MODE_FIXTURE)
        repo.close()

    def test_corpus_fixtureden_cok_daha_buyuk(self):
        """Asıl iddia: korpus modu fixture'ın iki katı değil, YÜZLERCE katı."""
        toplam = sum(len(collect_corpus(b, raw_dir=RAW))
                     for b in load_banks(CONFIG))
        self.assertGreaterEqual(toplam, CORPUS_DOCS_MIN)

    def test_docs_per_bank_tum_bankalari_icerir(self):
        repo = Repository(":memory:")
        res = run_pipeline(repo, CONFIG, raw_dir=RAW, mode=MODE_FIXTURE)
        self.assertEqual(len(res.docs_per_bank), len(load_banks(CONFIG)))
        self.assertEqual(sum(res.docs_per_bank.values()), res.documents_loaded)
        repo.close()

    def test_summary_modu_ve_sayiyi_yazar(self):
        repo = Repository(":memory:")
        res = run_pipeline(repo, CONFIG, raw_dir=RAW, mode=MODE_FIXTURE)
        s = res.summary()
        self.assertIn(f"mod={MODE_FIXTURE}", s)
        self.assertIn(f"belge={FIXTURE_DOCS}", s)
        repo.close()

    def test_on_progress_her_belge_icin_cagrilir(self):
        cagrilar: list[tuple[int, int, str]] = []
        repo = Repository(":memory:")
        res = run_pipeline(repo, CONFIG, raw_dir=RAW, mode=MODE_FIXTURE,
                           on_progress=lambda d, t, b: cagrilar.append((d, t, b)))
        self.assertEqual(len(cagrilar), res.documents_loaded)
        self.assertEqual([c[0] for c in cagrilar],
                         list(range(1, res.documents_loaded + 1)))
        # toplam ilk çağrıdan itibaren DOĞRU olmalı (iki fazlı toplama sebebi)
        self.assertTrue(all(c[1] == res.documents_loaded for c in cagrilar))
        repo.close()


class TestCorpusModuUctanUca(unittest.TestCase):
    """Sentetik korpusta uçtan uca: kayıt + alan + banka sayısı."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.kok = Path(self.tmp.name)
        self.raw = self.kok / "raw"
        _yaz(self.raw, "a-bank/live/1.txt", "Konut finansmanı kâr payı %1,89, "
                                            "120 ay vade.")
        _yaz(self.raw, "a-bank/products/2.txt", "Taşıt finansmanı %2,05, 36 ay.")
        _yaz(self.raw, "b-bank/live/1.txt", "Masrafsız ihtiyaç finansmanı, "
                                            "tahsis ücreti 500 TL.")
        self.cfg = _mini_banks_yaml(self.kok / "banks.yaml", ["a-bank", "b-bank"])

    def tearDown(self):
        self.tmp.cleanup()

    def test_tum_belgeler_kaydedilir(self):
        repo = Repository(":memory:")
        res = run_pipeline(repo, self.cfg, raw_dir=str(self.raw), mode=MODE_CORPUS)
        self.assertEqual(res.documents_loaded, 3)
        self.assertEqual(res.campaigns_stored, 3)
        self.assertEqual(res.docs_per_bank, {"a-bank": 2, "b-bank": 1})
        self.assertEqual(repo.counts()["campaigns"], 3)
        repo.close()

    def test_celiski_korpus_modunda_yakalanir(self):
        """"masrafsız" + tahsis ücreti — çelişki tespitinin canlı olduğu kanıtı."""
        repo = Repository(":memory:")
        res = run_pipeline(repo, self.cfg, raw_dir=str(self.raw), mode=MODE_CORPUS)
        kinds = {c["kind"] for c in res.contradictions}
        self.assertIn("masrafsiz_ama_ucret", kinds)
        repo.close()

    def test_fixture_modu_ayni_korpusta_daha_az_yukler(self):
        """Aynı veri, iki mod: fixture alt klasörleri GÖRMEZ."""
        repo = Repository(":memory:")
        res = run_pipeline(repo, self.cfg, raw_dir=str(self.raw), mode=MODE_FIXTURE)
        self.assertEqual(res.documents_loaded, 0)
        repo.close()


if __name__ == "__main__":
    unittest.main()
