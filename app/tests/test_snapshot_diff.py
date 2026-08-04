"""Hasat anlık görüntüsü / fark testleri.

İlgili: ../src/scraping/snapshot.py

## Neden bu testler

Fark raporu, `suresi_dolmus_kampanya` kuralı için ELLE İŞARETLENMEMİŞ doğrulama
verisi üretiyor. Yanlış çalışırsa gold set kirlenir. İki ölçülmüş tuzak var:

1. **Ham HTML hash'i yalancı "değişti" üretir.** Sayfadaki analitik kimlikleri ve
   oturum simgeleri her istekte değişir; kampanya metni sabit kalsa bile HTML
   hash'i değişir. 2026-08-03 ölçümü: 238 belge "değişmiş" görünüyordu, `git diff`
   ile `.txt` içerikleri BİREBİR AYNI çıktı. Karşılaştırma TEMİZ METİN üzerinden
   olmalı.
2. **Bayat dosyalar `kayip` kümesini boşaltır.** Yeniden hasat eski dosyaları
   silmez, üzerine yazar; `--since` süzgeci olmadan yeni manifest bayat kayıtları
   da "hâlâ yayında" sayar.
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.scraping.snapshot import (
    _text_hash,
    build_manifest,
    diff_manifests,
    render_diff,
)

URL_A = "https://banka.test/kampanyalar/a"
URL_B = "https://banka.test/kampanyalar/b"


def _write_doc(raw: Path, slug: str, bucket: str, stem: str, *, url: str,
               text: str, scraped_at: str, content_hash: str = "chash") -> None:
    d = raw / slug / bucket
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{stem}.txt").write_text(text, encoding="utf-8")
    (d / f"{stem}.txt.meta.json").write_text(json.dumps({
        "bank_slug": slug, "source_url": url, "scraped_at": scraped_at,
        "content_hash": content_hash, "title": stem, "text_chars": len(text),
    }, ensure_ascii=False), encoding="utf-8")


class TestTextHash(unittest.TestCase):
    def test_bosluk_gurultusu_hash_i_degistirmez(self):
        self.assertEqual(_text_hash("a  b\n\nc"), _text_hash("a b c"))

    def test_gercek_degisiklik_hash_i_degistirir(self):
        self.assertNotEqual(_text_hash("kâr payı %2,05"), _text_hash("kâr payı %2,45"))


class TestBuildManifest(unittest.TestCase):
    def test_url_suz_ve_fixture_kayitlari_atlanir(self):
        with tempfile.TemporaryDirectory() as tmpname:
            raw = Path(tmpname)
            _write_doc(raw, "banka", "live", "a", url=URL_A, text="metin",
                       scraped_at="2026-08-03T10:00:00+00:00")
            # file:// kaynaklı fixture → sayılmaz
            _write_doc(raw, "banka", "live", "fix", url="file:///x/y.html",
                       text="metin", scraped_at="2026-08-03T10:00:00+00:00")
            man = build_manifest(raw, label="t")
            self.assertEqual(man["entry_count"], 1)
            self.assertEqual(man["skipped"], 1)
            self.assertEqual(man["entries"][0]["url"], URL_A)

    def test_text_hash_uretiliyor(self):
        with tempfile.TemporaryDirectory() as tmpname:
            raw = Path(tmpname)
            _write_doc(raw, "banka", "live", "a", url=URL_A, text="kâr payı %2,05",
                       scraped_at="2026-08-03T10:00:00+00:00")
            man = build_manifest(raw)
            self.assertEqual(man["text_missing"], 0)
            self.assertEqual(man["entries"][0]["text_hash"],
                             _text_hash("kâr payı %2,05"))

    def test_since_bayat_kayitlari_disler(self):
        with tempfile.TemporaryDirectory() as tmpname:
            raw = Path(tmpname)
            _write_doc(raw, "banka", "live", "eski", url=URL_A, text="eski",
                       scraped_at="2026-07-30T10:00:00+00:00")
            _write_doc(raw, "banka", "live", "yeni", url=URL_B, text="yeni",
                       scraped_at="2026-08-03T10:00:00+00:00")
            man = build_manifest(raw, since="2026-08-01T00:00:00+00:00")
            self.assertEqual(man["entry_count"], 1)
            self.assertEqual(man["stale_excluded"], 1)
            self.assertEqual(man["entries"][0]["url"], URL_B)

    def test_bucket_ve_banka_sayimi(self):
        with tempfile.TemporaryDirectory() as tmpname:
            raw = Path(tmpname)
            _write_doc(raw, "banka", "live", "a", url=URL_A, text="x",
                       scraped_at="2026-08-03T10:00:00+00:00")
            _write_doc(raw, "banka", "archive", "b", url=URL_B, text="y",
                       scraped_at="2026-08-03T10:00:00+00:00")
            man = build_manifest(raw)
            self.assertEqual(man["by_bucket"], {"archive": 1, "live": 1})
            self.assertEqual(man["by_bank"], {"banka": 2})


def _man(label: str, entries: list[dict]) -> dict:
    return {"manifest_version": 1, "label": label, "entries": entries}


def _e(url: str, *, bucket: str = "live", text_hash: str = "t1",
       content_hash: str = "c1", slug: str = "banka") -> dict:
    return {"url": url, "bank_slug": slug, "bucket": bucket,
            "content_hash": content_hash, "text_hash": text_hash,
            "title": "T", "text_chars": 100, "path": f"{slug}/{bucket}/x.txt.meta.json"}


class TestDiff(unittest.TestCase):
    def test_metin_ayni_ise_ham_html_farki_degisiklik_saymaz(self):
        """EN KRİTİK: 238 yalancı "değişti" bulgusunu üreten hata.

        Ham HTML hash'i farklı ama temiz metin aynı → `ayni` sayılmalı.
        """
        before = _man("a", [_e(URL_A, content_hash="html-eski", text_hash="AYNI")])
        after = _man("b", [_e(URL_A, content_hash="html-yeni", text_hash="AYNI")])
        res = diff_manifests(before, after)
        self.assertEqual(res.ayni, 1)
        self.assertEqual(res.degisti, [])

    def test_metin_degistiyse_degisiklik_sayilir(self):
        before = _man("a", [_e(URL_A, text_hash="ESKI")])
        after = _man("b", [_e(URL_A, text_hash="YENI")])
        res = diff_manifests(before, after)
        self.assertEqual(len(res.degisti), 1)
        self.assertEqual(res.degisti[0]["karsilastirma"], "metin")

    def test_text_hash_yoksa_ham_html_e_duser(self):
        """Eski manifestlerde `text_hash` olmayabilir — geriye uyumluluk."""
        before = _man("a", [{**_e(URL_A), "text_hash": None,
                             "content_hash": "c-eski"}])
        after = _man("b", [{**_e(URL_A), "text_hash": None,
                            "content_hash": "c-yeni"}])
        res = diff_manifests(before, after)
        self.assertEqual(len(res.degisti), 1)
        self.assertEqual(res.degisti[0]["karsilastirma"], "ham-html")

    def test_kayip_ve_yeni(self):
        before = _man("a", [_e(URL_A)])
        after = _man("b", [_e(URL_B)])
        res = diff_manifests(before, after)
        self.assertEqual([k["url"] for k in res.kayip], [URL_A])
        self.assertEqual([y["url"] for y in res.yeni], [URL_B])

    def test_arsive_tasinma_kayip_olarak_isaretlenir_ama_kumesi_belirtilir(self):
        """`live/`'dan `archive/`'a geçen belge kayıp DEĞİL, arşivlenmedir."""
        before = _man("a", [_e(URL_A, bucket="live")])
        after = _man("b", [_e(URL_A, bucket="archive")])
        res = diff_manifests(before, after)
        self.assertEqual(len(res.kayip), 1)
        self.assertEqual(res.kayip[0]["yeni_bucket"], ["archive"])

    def test_kumeler_ayri_karsilastirilir(self):
        """Ürün sayfası ile kampanya sayfası kıyaslanmaz (CLAUDE.md §17)."""
        before = _man("a", [_e(URL_A, bucket="products", text_hash="X")])
        after = _man("b", [_e(URL_A, bucket="live", text_hash="X")])
        res = diff_manifests(before, after)
        self.assertEqual(len(res.kayip), 1)
        self.assertEqual(len(res.yeni), 1)
        self.assertEqual(res.ayni, 0)


class TestRender(unittest.TestCase):
    def test_rapor_dort_durumu_da_verir(self):
        before = _man("2026-07-30", [_e(URL_A)])
        after = _man("2026-08-03", [_e(URL_B)])
        out = render_diff(diff_manifests(before, after))
        for token in ("kayip", "yeni", "degisti", "ayni",
                      "2026-07-30", "2026-08-03"):
            self.assertIn(token, out)


if __name__ == "__main__":
    unittest.main()
