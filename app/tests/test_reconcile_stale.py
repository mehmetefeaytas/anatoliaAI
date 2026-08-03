"""Bayat belge mutabakatı testleri — sınıflandırma + kuru koşu güvenliği.

İlgili: ../src/scraping/reconcile_stale.py, ../src/scraping/snapshot.py

## Neden bu testler

Yeniden hasat eski dosyaları silmez; sitede artık olmayan kampanya `live/` altında
kalır ve AKTİF sanılır. Mutabakat modülü bunu düzeltir ama iki hatayı yapmamalı:

1. **Körlemesine "expired" etiketlemek.** "Hasatta kayıp" ≠ "süresi doldu";
   sayfa hâlâ yayında olabilir (keşif kaçırmış olabilir). Yanlış etiket veri
   uydurmaktır (CLAUDE.md §19).
2. **İstenmeden dosya taşımak.** Varsayılan KURU KOŞU olmalı; `--apply`
   verilmedikçe diskte hiçbir şey değişmemeli.
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.scraping import reconcile_stale as rs
from src.scraping.fetcher import FetchResult


class _FakeFetcher:
    """`StaticFetcher` arayüzünü taklit eder; URL → (status, html) eşlemesi."""

    method = "live"

    def __init__(self, pages: dict[str, tuple[int, str]]):
        self.pages = pages
        self.calls: list[str] = []

    @property
    def available(self) -> bool:
        return True

    def fetch(self, url: str, **kwargs) -> FetchResult:
        self.calls.append(url)
        status, html = self.pages.get(url, (404, ""))
        return FetchResult(url, status=status, html=html or None,
                           method=self.method, final_url=url)

    def close(self) -> None:
        pass


def _manifest(label: str, entries: list[dict]) -> dict:
    return {"manifest_version": 1, "label": label, "entry_count": len(entries),
            "entries": entries}


def _entry(url: str, *, bucket: str = "live", slug: str = "testbank",
           path: str = "", digest: str = "h1") -> dict:
    return {"url": url, "bank_slug": slug, "bucket": bucket,
            "content_hash": digest, "title": "T", "text_chars": 500,
            "scraped_at": "2026-07-30T00:00:00+00:00", "path": path}


URL_GONE = "https://banka.test/kampanyalar/biten"
URL_SELF_EXPIRED = "https://banka.test/kampanyalar/damgali"
URL_STILL_LIVE = "https://banka.test/kampanyalar/duruyor"
URL_SERVER_ERR = "https://banka.test/kampanyalar/hata"


class TestClassification(unittest.TestCase):
    """Her HTTP durumu doğru karara eşlenmeli."""

    def setUp(self):
        self.before = _manifest("onceki", [
            _entry(URL_GONE), _entry(URL_SELF_EXPIRED),
            _entry(URL_STILL_LIVE), _entry(URL_SERVER_ERR),
        ])
        self.after = _manifest("yeni", [])  # hepsi kayıp
        self.pages = {
            URL_GONE: (404, ""),
            URL_SELF_EXPIRED: (200, "<html><body>Kampanya Süresi Dolmuştur"
                                    "</body></html>"),
            URL_STILL_LIVE: (200, "<html><body>Kampanya devam ediyor, "
                                  "%2,05 kâr payı</body></html>"),
            URL_SERVER_ERR: (503, ""),
        }

    def _run(self):
        fake = _FakeFetcher(self.pages)
        orig_fetcher, orig_robots = rs.StaticFetcher, rs.RobotsCache
        rs.StaticFetcher = lambda **kw: fake
        rs.RobotsCache = lambda **kw: type(
            "R", (), {"allows": staticmethod(lambda u: (True, ""))})()
        try:
            with tempfile.TemporaryDirectory() as tmp:
                return rs.verify_stale(self.before, self.after, tmp, delay_s=0.0)
        finally:
            rs.StaticFetcher, rs.RobotsCache = orig_fetcher, orig_robots

    def test_kararlar(self):
        by_url = {v.url: v.decision for v in self._run()}
        self.assertEqual(by_url[URL_GONE], rs.DECISION_REMOVED)
        self.assertEqual(by_url[URL_SELF_EXPIRED], rs.DECISION_SELF_EXPIRED)
        self.assertEqual(by_url[URL_STILL_LIVE], rs.DECISION_STILL_LIVE)
        self.assertEqual(by_url[URL_SERVER_ERR], rs.DECISION_UNVERIFIED)

    def test_hala_yayindaki_sayfa_tasinmaz(self):
        """En kritik koruma: yayında olan sayfa `expired` sayılmaz."""
        v = next(v for v in self._run() if v.url == URL_STILL_LIVE)
        self.assertNotIn(v.decision, rs.MOVE_DECISIONS)

    def test_baska_kumede_taze_hali_varsa_yeniden_cekilmez(self):
        """URL yeni turda `archive/`'da TAZE hâliyle varsa istek atılmaz.

        Bu "süresi doldu" DEĞİL, "mükerrer kopya"dır: belge kaybolmadı, doğru
        kümeye yazıldı. Gerçek vaka: Temmuz'da Kuveyt Türk arşiv sayfaları
        `live/`'a toplanıyordu; arşiv dışlama düzeltmesinden sonra aynı 34 URL
        `archive/`'a taşındı.
        """
        before = _manifest("onceki", [_entry(URL_GONE)])
        after = _manifest("yeni", [_entry(URL_GONE, bucket="archive")])
        fake = _FakeFetcher({})
        orig_fetcher, orig_robots = rs.StaticFetcher, rs.RobotsCache
        rs.StaticFetcher = lambda **kw: fake
        rs.RobotsCache = lambda **kw: type(
            "R", (), {"allows": staticmethod(lambda u: (True, ""))})()
        try:
            with tempfile.TemporaryDirectory() as tmp:
                out = rs.verify_stale(before, after, tmp, delay_s=0.0)
        finally:
            rs.StaticFetcher, rs.RobotsCache = orig_fetcher, orig_robots
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0].decision, rs.DECISION_SUPERSEDED)
        self.assertIn("mükerrer", out[0].detail)
        self.assertEqual(fake.calls, [], "taze hâli olan belge yeniden çekilmemeli")
        # Mükerrer kopya da `live/` altında KALMAMALI (aktif sanılır)
        self.assertIn(rs.DECISION_SUPERSEDED, rs.MOVE_DECISIONS)


class TestApplyMoves(unittest.TestCase):
    """Taşıma gerçekten `live/` → `archive/` yapıyor mu, provenance yazılıyor mu?"""

    def _corpus(self, tmp: Path) -> str:
        live = tmp / "testbank" / "live"
        live.mkdir(parents=True)
        stem = "kampanyalar-biten"
        (live / f"{stem}.txt").write_text("kampanya metni", encoding="utf-8")
        (live / f"{stem}.html").write_text("<html>x</html>", encoding="utf-8")
        meta = {"bank_slug": "testbank", "source_url": URL_GONE,
                "scraped_at": "2026-07-30T00:00:00+00:00", "content_hash": "h1"}
        (live / f"{stem}.txt.meta.json").write_text(
            json.dumps(meta, ensure_ascii=False), encoding="utf-8")
        return f"testbank/live/{stem}.txt.meta.json"

    def test_kuru_kosu_dosyaya_dokunmaz(self):
        with tempfile.TemporaryDirectory() as tmpname:
            tmp = Path(tmpname)
            rel = self._corpus(tmp)
            verdicts = [rs.Verdict(url=URL_GONE, bank_slug="testbank",
                                   bucket="live", decision=rs.DECISION_REMOVED,
                                   http_status=404, meta_path=rel)]
            # apply_moves ÇAĞRILMAZ → hiçbir şey değişmemeli
            self.assertTrue((tmp / rel).is_file())
            self.assertFalse((tmp / "testbank" / "archive").exists())
            self.assertEqual(verdicts[0].moved, [])

    def test_apply_tasir_ve_provenance_yazar(self):
        with tempfile.TemporaryDirectory() as tmpname:
            tmp = Path(tmpname)
            rel = self._corpus(tmp)
            verdicts = [rs.Verdict(url=URL_GONE, bank_slug="testbank",
                                   bucket="live", decision=rs.DECISION_REMOVED,
                                   http_status=404,
                                   detail="HTTP 404 — sayfa kaldırılmış",
                                   meta_path=rel)]
            rs.apply_moves(verdicts, tmp)

            archive = tmp / "testbank" / "archive"
            self.assertTrue(archive.is_dir())
            # 3 dosya da taşındı (txt + html + meta), live boşaldı
            self.assertEqual(len(list(archive.glob("kampanyalar-biten*"))), 3)
            self.assertEqual(list((tmp / "testbank" / "live").glob("*.txt")), [])
            # HİÇBİR DOSYA SİLİNMEDİ
            self.assertTrue((archive / "kampanyalar-biten.txt").is_file())
            self.assertTrue((archive / "kampanyalar-biten.html").is_file())

            meta = json.loads(
                (archive / "kampanyalar-biten.txt.meta.json").read_text(
                    encoding="utf-8"))
            self.assertEqual(meta["campaign_status"], rs.STATUS_EXPIRED)
            self.assertEqual(meta["removal_check"]["decision"],
                             rs.DECISION_REMOVED)
            self.assertEqual(meta["removal_check"]["http_status"], 404)
            self.assertIn("checked_at", meta["removal_check"])
            # Orijinal provenance korunmuş olmalı
            self.assertEqual(meta["source_url"], URL_GONE)
            self.assertEqual(meta["content_hash"], "h1")

    def test_tasinmayan_kararlar_diske_dokunmaz(self):
        with tempfile.TemporaryDirectory() as tmpname:
            tmp = Path(tmpname)
            rel = self._corpus(tmp)
            for decision in (rs.DECISION_STILL_LIVE, rs.DECISION_UNVERIFIED):
                verdicts = [rs.Verdict(url=URL_GONE, bank_slug="testbank",
                                       bucket="live", decision=decision,
                                       meta_path=rel)]
                rs.apply_moves(verdicts, tmp)
                self.assertTrue((tmp / rel).is_file(),
                                f"{decision} kararında dosya taşınmamalı")
                self.assertFalse((tmp / "testbank" / "archive").exists())


class TestReport(unittest.TestCase):
    def test_rapor_kuru_kosuyu_belirtir(self):
        out = rs.render_report([], applied=False)
        self.assertIn("KURU KOŞU", out)
        self.assertIn("hiçbir dosya taşınmadı", out)

    def test_rapor_kesif_acigini_ayri_bolumde_verir(self):
        v = rs.Verdict(url=URL_STILL_LIVE, bank_slug="testbank", bucket="live",
                       decision=rs.DECISION_STILL_LIVE, http_status=200)
        out = rs.render_report([v], applied=True)
        self.assertIn("Keşif Açığı", out)
        self.assertIn(URL_STILL_LIVE, out)
        self.assertIn("UYGULANDI", out)


if __name__ == "__main__":
    unittest.main()
