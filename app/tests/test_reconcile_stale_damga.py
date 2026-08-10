"""`verify_stale` regresyonu — canlı sayfa ASLA `suresi_dolmus` sayılmamalı.

İlgili: ../src/scraping/reconcile_stale.py, ../src/scraping/expiry_stamp.py
        ../docs/rapor/suresi-dolmus-damgasi.md
        ../docs/rapor/bayat-veri-mutabakati.md §3 (kusurun ölçüldüğü yer)

## Neden bu dosya

`verify_stale`, sayfanın kendini bitmiş ilan edip etmediğini
`comparison.contradiction._SELF_EXPIRED` deseniyle **ham HTML'de** arıyordu.
Ölçüldü (2026-08-10): o koşuda üretilen 5 `suresi_dolmus` kararının **5'i de**
yanlış pozitifti ve aynı desen canlı sayılan 750 belgenin 190'ında ateşliyordu.

`tests/test_reconcile_stale.py` bu kusuru göremezdi çünkü oradaki damgalı
sayfa UYDURMA bir parçacık ("<body>Kampanya Süresi Dolmuştur</body>") ve
kontrol grubu YOK. Buradaki sayfalar gerçek korpustan alınmıştır ve kontrol
grubu, o raporun deneyindeki üç yanlış pozitif kaynağını temsil eder.
"""

from __future__ import annotations

import json
import re
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.scraping import reconcile_stale as rs
from src.scraping.fetcher import FetchResult

#: Düzeltmeden ÖNCEKİ desen. Testte YALNIZCA kontrol grubunun gerçekten
#: tuzak olduğunu ispatlamak için duruyor; karar yolunda kullanılmıyor.
ESKI_GENIS = re.compile(
    r"(s[üu]resi\s+dolmu[şs]|sona\s+erdi|sona\s+ermi[şs]|"
    r"biten\s+kampanya|ge[çc]mi[şs]\s+kampanya)", re.IGNORECASE)


def _sayfa(govde: str, *, menu: str = "") -> str:
    """Gerçek sitelerin iskeletine benzeyen minimal HTML."""
    return (f"<html><head><title>Kampanya</title></head><body>"
            f"<header><nav>{menu}</nav></header>"
            f"<main><article>{govde}</article></main>"
            f"<footer>Türkiye Katılım Bankası</footer></body></html>")


# --------------------------------------------------------------------------- #
# KONTROL GRUBU — canlı sayfalar (gerçek korpustan alıntı)
# --------------------------------------------------------------------------- #

#: turkiye-finans: menü bağlantısı hem metinde hem `href` içinde geçiyor.
#: Rapor §3: bu bankanın canlı olduğu kesin 3 kontrol sayfasının 3'ü de eski
#: desenle eşleşiyordu.
MENU_TF = (
    '<ul><li><a href="/tr-tr/kampanyalar/Sayfalar/diger-kampanyalar.aspx">'
    '<span>Diğer Kampanyalar</span></a></li>'
    '<li><a href="/tr-tr/kampanyalar/Sayfalar/Biten-Kampanyalar.aspx">'
    '<span>Biten Kampanyalar</span></a></li></ul>')

SAYFA_MENU = _sayfa(
    "<h1>Bireysel Arsa Finansmanı</h1><p>Arsa alımlarınız için 120 aya varan "
    "vade ile finansman. Kâr payı oranı %2,05'ten başlar.</p>",
    menu=MENU_TF)

#: vakif-katilim: standart ihtar cümlesi (birebir alıntı).
SAYFA_IHTAR = _sayfa(
    "<h1>Dijitalden Müşteri Ol</h1><p>Hisse senedi işlemlerinde %75 komisyon "
    "indirimi. Kampanyaya dahil değildir. Vakıf Katılım Bankası AŞ önceden "
    "haber vermeksizin kampanyayı durdurma, sona erdirme, kampanya kapsamını "
    "ve koşullarını değiştirme hakkını saklı tutar.</p>")

#: albaraka: sayfanın KENDİ kampanyası canlı; damga alttaki "Diğer
#: Kampanyalar" kartında ve BAŞKA bir kampanyaya ait.
SAYFA_KUYRUK = _sayfa(
    "<h1>BOSCH Harcamalarınızda World'e Özel 6 Taksit Fırsatı!</h1>"
    "<p>BOSCH harcamalarınızda 24 Haziran 2026 tarihine kadar World'e özel "
    "6 taksit fırsatını kaçırmayın. Kampanya Başlangıç ve Bitiş Tarihi: "
    "Kampanya 1 Mayıs 2026 – 24 Haziran 2026 tarihlerinde geçerlidir.</p>"
    "<section><h2>Diğer Kampanyalar</h2>"
    "<p>Arçelik, Altus ve Beko Harcamalarınızda World'e Özel 9 Taksit "
    "Fırsatı! Bu kampanya sona ermiştir.</p></section>")

KONTROL_SAYFALARI = {
    "menu-turkiye-finans": SAYFA_MENU,
    "ihtar-vakif-katilim": SAYFA_IHTAR,
    "kuyruk-albaraka": SAYFA_KUYRUK,
}

# --------------------------------------------------------------------------- #
# DAMGALI SAYFA — ziraat-katilim (birebir alıntı)
# --------------------------------------------------------------------------- #

SAYFA_DAMGA = _sayfa(
    "<h1>Jumbo'da 5 Taksit</h1>"
    "<p>Kampanya 30-04-2026 Tarihinde Sona Ermiştir. Sektör: Mobilya ve "
    "Dekorasyon. Ziraat Katılım Bankkart kredi kartınız ile Jumbo'da "
    "yapacağınız alışverişlerde 5 taksit fırsatı.</p>")


class _FakeFetcher:
    """`StaticFetcher` arayüzünü taklit eder — ağa çıkılmaz."""

    method = "live"

    def __init__(self, pages: dict[str, tuple[int, str]]):
        self.pages = pages

    @property
    def available(self) -> bool:
        return True

    def fetch(self, url: str, **kwargs) -> FetchResult:
        status, html = self.pages.get(url, (404, ""))
        return FetchResult(url, status=status, html=html or None,
                           method=self.method, final_url=url)

    def close(self) -> None:
        pass


def _entry(url: str, *, slug: str, path: str = "") -> dict:
    return {"url": url, "bank_slug": slug, "bucket": "live",
            "content_hash": "h1", "title": "T", "text_chars": 500,
            "scraped_at": "2026-08-03T16:00:00+00:00", "path": path}


def _manifest(label: str, entries: list[dict]) -> dict:
    return {"manifest_version": 1, "label": label, "entry_count": len(entries),
            "entries": entries}


def _kosturt(pages: dict[str, tuple[int, str]], entries: list[dict],
             raw_dir: str) -> list[rs.Verdict]:
    fake = _FakeFetcher(pages)
    orig_fetcher, orig_robots = rs.StaticFetcher, rs.RobotsCache
    rs.StaticFetcher = lambda **kw: fake
    rs.RobotsCache = lambda **kw: type(
        "R", (), {"allows": staticmethod(lambda u: (True, ""))})()
    try:
        return rs.verify_stale(_manifest("onceki", entries),
                               _manifest("yeni", []), raw_dir, delay_s=0.0)
    finally:
        rs.StaticFetcher, rs.RobotsCache = orig_fetcher, orig_robots


class TestKontrolGrubuTasinmaz(unittest.TestCase):
    """Canlı sayfa `suresi_dolmus` sayılmamalı — bu testin ana sebebi."""

    def setUp(self):
        self.urls = {ad: f"https://banka.test/kampanyalar/{ad}"
                     for ad in KONTROL_SAYFALARI}
        self.pages = {self.urls[ad]: (200, html)
                      for ad, html in KONTROL_SAYFALARI.items()}
        self.entries = [_entry(u, slug="kontrolbank") for u in self.urls.values()]

    def test_kontrol_grubu_gercekten_tuzak(self):
        """Eski desen bu sayfaların HEPSİNDE ateşliyor — kontrol grubu anlamlı."""
        for ad, html in KONTROL_SAYFALARI.items():
            with self.subTest(sayfa=ad):
                self.assertRegex(html, ESKI_GENIS,
                                 "kontrol sayfası eski deseni tetiklemiyorsa "
                                 "regresyonu ölçmez")

    def test_hepsi_kesif_acigi(self):
        with tempfile.TemporaryDirectory() as tmp:
            verdicts = _kosturt(self.pages, self.entries, tmp)
        self.assertEqual(len(verdicts), 3)
        for v in verdicts:
            with self.subTest(url=v.url):
                self.assertEqual(v.decision, rs.DECISION_STILL_LIVE)
                self.assertNotIn(v.decision, rs.MOVE_DECISIONS)
                self.assertIsNone(v.stamp)


class TestDamgaliSayfaTasinir(unittest.TestCase):
    """Gerçek damga hâlâ yakalanmalı ve kanıtı taşımalı."""

    URL = "https://banka.test/kampanyalar/jumboda-5-taksit"

    def _corpus(self, tmp: Path) -> str:
        live = tmp / "ziraat-katilim" / "live"
        live.mkdir(parents=True)
        stem = "kart-kampanyalari-jumboda-5-taksit"
        (live / f"{stem}.txt").write_text("kampanya metni", encoding="utf-8")
        (live / f"{stem}.txt.meta.json").write_text(json.dumps(
            {"bank_slug": "ziraat-katilim", "source_url": self.URL,
             "scraped_at": "2026-08-03T16:00:00+00:00", "content_hash": "h1"},
            ensure_ascii=False), encoding="utf-8")
        return f"ziraat-katilim/live/{stem}.txt.meta.json"

    def test_damga_yakalanir_ve_tarih_okunur(self):
        with tempfile.TemporaryDirectory() as tmpname:
            tmp = Path(tmpname)
            rel = self._corpus(tmp)
            verdicts = _kosturt(
                {self.URL: (200, SAYFA_DAMGA)},
                [_entry(self.URL, slug="ziraat-katilim", path=rel)], tmpname)

            self.assertEqual(len(verdicts), 1)
            v = verdicts[0]
            self.assertEqual(v.decision, rs.DECISION_SELF_EXPIRED)
            self.assertIsNotNone(v.stamp)
            self.assertEqual(v.stamp.end_date, "2026-04-30")
            self.assertIn("30-04-2026", v.detail)   # kanıt gerekçede

            rs.apply_moves(verdicts, tmp)
            arsiv = tmp / "ziraat-katilim" / "archive"
            meta = json.loads(
                (arsiv / "kart-kampanyalari-jumboda-5-taksit.txt.meta.json")
                .read_text(encoding="utf-8"))
            self.assertEqual(meta["campaign_status"], rs.STATUS_EXPIRED)
            damga = meta["removal_check"]["expiry_stamp"]
            self.assertEqual(damga["end_date"], "2026-04-30")
            self.assertIn("Sona Ermiştir", damga["phrase"])
            # Provenance korunmalı
            self.assertEqual(meta["source_url"], self.URL)


if __name__ == "__main__":
    unittest.main()
