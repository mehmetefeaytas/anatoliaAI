"""Damga işaretleme geçişi testleri — kuru koşu güvenliği + idempotanlık.

İlgili: ../scripts/damga_isaretle.py, ../src/scraping/expiry_stamp.py

## Neden bu testler

Geçiş `data/raw/` altındaki 772 belgenin `.meta.json`'ına yazıyor. Üç hatayı
yapmamalı:

1. **İstenmeden yazmak.** Varsayılan KURU KOŞU; `--uygula` verilmedikçe diskte
   hiçbir şey değişmemeli.
2. **Provenance'ı bozmak.** `source_url` / `scraped_at` / `content_hash`
   korunmalı; dosya taşınmamalı, silinmemeli.
3. **Her koşuda dosyayı değiştirmek.** İşaret veriden TÜRETİLİR; aynı korpusta
   ikinci koşu diski değiştirmemeli (aksi hâlde her koşu git gürültüsü üretir
   ve `checked_at` anlamsızlaşır).

Ayrıca belge yeniden hasat edilip damga kalkarsa KENDİ işaretimizi geri
almalı — ama başkasının (`reconcile_stale` / hasatçı) yazdığına dokunmamalı.
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import damga_isaretle as di

DAMGALI = ("Jumbo'da 5 Taksit Kampanya 30-04-2026 Tarihinde Sona Ermiştir. "
           "Sektör: Mobilya ve Dekorasyon.")
BELIRSIZ = ("Vakıf Katılım Bankası AŞ önceden haber vermeksizin kampanyayı "
            "durdurma, sona erdirme, kampanya kapsamını ve koşullarını "
            "değiştirme hakkını saklı tutar.")
TEMIZ = "Konut finansmanında 120 aya varan vade ve %2,05 kâr payı oranı."


def _belge(kok: Path, bank: str, stem: str, metin: str,
           meta_ek: dict | None = None) -> Path:
    live = kok / bank / "live"
    live.mkdir(parents=True, exist_ok=True)
    (live / f"{stem}.txt").write_text(metin, encoding="utf-8")
    meta = {"bank_slug": bank,
            "source_url": f"https://{bank}.test/kampanyalar/{stem}",
            "scraped_at": "2026-08-03T16:00:00+00:00",
            "content_hash": "h1", "collection_method": "live"}
    meta.update(meta_ek or {})
    p = live / f"{stem}.txt.meta.json"
    p.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n",
                 encoding="utf-8")
    return p


class TestTara(unittest.TestCase):
    def test_uc_durum_ayrilir(self):
        with tempfile.TemporaryDirectory() as tmp:
            kok = Path(tmp)
            _belge(kok, "ziraat-katilim", "a", DAMGALI)
            _belge(kok, "vakif-katilim", "b", BELIRSIZ)
            _belge(kok, "kuveyt-turk", "c", TEMIZ)
            durum = {b.meta_path.split("/")[0]: b.durum for b in di.tara(kok)}
        self.assertEqual(durum["ziraat-katilim"], "damgali")
        self.assertEqual(durum["vakif-katilim"], "belirsiz",
                         "ihtar cümlesi 'kapanmış' sayılmamalı")
        self.assertEqual(durum["kuveyt-turk"], "temiz")

    def test_kuru_kosu_diske_dokunmaz(self):
        with tempfile.TemporaryDirectory() as tmp:
            kok = Path(tmp)
            meta_p = _belge(kok, "ziraat-katilim", "a", DAMGALI)
            once = meta_p.read_text(encoding="utf-8")
            bulgular = di.tara(kok)          # `isaretle` ÇAĞRILMAZ
            self.assertEqual(meta_p.read_text(encoding="utf-8"), once)
            self.assertFalse(any(b.yazildi for b in bulgular))


class TestIsaretle(unittest.TestCase):
    def test_damga_yazilir_provenance_korunur(self):
        with tempfile.TemporaryDirectory() as tmp:
            kok = Path(tmp)
            meta_p = _belge(kok, "ziraat-katilim", "a", DAMGALI)
            di.isaretle(di.tara(kok), kok)
            meta = json.loads(meta_p.read_text(encoding="utf-8"))

            self.assertEqual(meta["campaign_status"], di.STATUS_EXPIRED)
            damga = meta["expiry_stamp"]
            self.assertEqual(damga["end_date"], "2026-04-30")
            self.assertEqual(damga["marked_by"], di.ISARETLEYEN)
            self.assertEqual(damga["source"], "metin-damgasi")
            self.assertIn("30-04-2026", damga["quote"])
            self.assertIn("checked_at", damga)
            # Provenance olduğu gibi
            self.assertEqual(meta["content_hash"], "h1")
            self.assertEqual(meta["scraped_at"], "2026-08-03T16:00:00+00:00")
            self.assertTrue(meta["source_url"].endswith("/a"))
            # Dosya taşınmadı, silinmedi
            self.assertTrue((kok / "ziraat-katilim" / "live" / "a.txt").is_file())
            self.assertFalse((kok / "ziraat-katilim" / "archive").exists())

    def test_belirsiz_belgeye_yazilmaz(self):
        """"Belirsiz" hiçbir zaman karar almaz — ne bitmiş ne aktif."""
        with tempfile.TemporaryDirectory() as tmp:
            kok = Path(tmp)
            b_p = _belge(kok, "vakif-katilim", "b", BELIRSIZ)
            once = b_p.read_text(encoding="utf-8")
            di.isaretle(di.tara(kok), kok)
            self.assertEqual(b_p.read_text(encoding="utf-8"), once)

    def test_temiz_belge_aktif_isaretlenir(self):
        """Damgasız/temiz + hiçbir mekanizma önceden durum yazmamışsa → active.

        Ölçüldü (2026-08-25): `collector.STATUS_ACTIVE` tanımlıydı ama hiçbir
        kod yolu tarafından atanmıyordu — dashboard'da "aktif: 0" hep
        böyle görünüyordu. Bu test o boşluğun kapatıldığını doğrular.
        """
        with tempfile.TemporaryDirectory() as tmp:
            kok = Path(tmp)
            t_p = _belge(kok, "kuveyt-turk", "c", TEMIZ)
            bulgular = di.isaretle(di.tara(kok), kok)
            meta = json.loads(t_p.read_text(encoding="utf-8"))

            self.assertEqual(meta["campaign_status"], di.STATUS_ACTIVE)
            aktif = meta["active_stamp"]
            self.assertEqual(aktif["marked_by"], di.ISARETLEYEN)
            self.assertEqual(aktif["source"], "hasat-damgasiz")
            self.assertIn("checked_at", aktif)
            self.assertNotIn("expiry_stamp", meta)
            # Provenance olduğu gibi
            self.assertEqual(meta["content_hash"], "h1")
            self.assertTrue(any(b.yazildi for b in bulgular))

    def test_temiz_ikinci_kosu_dosyayi_degistirmez(self):
        """İdempotanlık: `active` işareti de ikinci koşuda dosyayı değiştirmez."""
        with tempfile.TemporaryDirectory() as tmp:
            kok = Path(tmp)
            t_p = _belge(kok, "kuveyt-turk", "c", TEMIZ)
            di.isaretle(di.tara(kok), kok)
            ilk = t_p.read_text(encoding="utf-8")
            ikinci = di.isaretle(di.tara(kok), kok)
            self.assertEqual(t_p.read_text(encoding="utf-8"), ilk)
            self.assertFalse(any(b.yazildi for b in ikinci))

    def test_aktif_belge_sonra_damgalanirsa_expired_olur(self):
        """Aktif işaretli belge bir sonraki hasatta damga kazanırsa geçiş yapar."""
        with tempfile.TemporaryDirectory() as tmp:
            kok = Path(tmp)
            meta_p = _belge(kok, "kuveyt-turk", "c", TEMIZ)
            di.isaretle(di.tara(kok), kok)
            # Yeniden hasat: kampanya bu turda bitmiş
            (kok / "kuveyt-turk" / "live" / "c.txt").write_text(
                DAMGALI, encoding="utf-8")
            di.isaretle(di.tara(kok), kok)
            meta = json.loads(meta_p.read_text(encoding="utf-8"))
            self.assertEqual(meta["campaign_status"], di.STATUS_EXPIRED)
            self.assertNotIn("active_stamp", meta)

    def test_aktif_belge_belirsizlesirse_durum_silinir(self):
        """Aktif işaretli belge belirsiz hâle gelirse (kendi) işareti geri alınır."""
        with tempfile.TemporaryDirectory() as tmp:
            kok = Path(tmp)
            meta_p = _belge(kok, "kuveyt-turk", "c", TEMIZ)
            di.isaretle(di.tara(kok), kok)
            (kok / "kuveyt-turk" / "live" / "c.txt").write_text(
                BELIRSIZ, encoding="utf-8")
            bulgular = di.isaretle(di.tara(kok), kok)
            meta = json.loads(meta_p.read_text(encoding="utf-8"))
            self.assertNotIn("active_stamp", meta)
            self.assertNotIn("campaign_status", meta)
            self.assertTrue(any(b.geri_alindi for b in bulgular))

    def test_ikinci_kosu_dosyayi_degistirmez(self):
        """İdempotanlık: aynı korpusta ikinci koşu diski değiştirmemeli."""
        with tempfile.TemporaryDirectory() as tmp:
            kok = Path(tmp)
            meta_p = _belge(kok, "ziraat-katilim", "a", DAMGALI)
            di.isaretle(di.tara(kok), kok)
            ilk = meta_p.read_text(encoding="utf-8")
            ikinci = di.isaretle(di.tara(kok), kok)
            self.assertEqual(meta_p.read_text(encoding="utf-8"), ilk)
            self.assertFalse(any(b.yazildi for b in ikinci))

    def test_damga_kalkarsa_aktife_gecer(self):
        """Damga kalkarsa (yeniden hasat "temiz" bulur) kendi eski işaretimiz
        silinir VE belge `active` olur — "kampanya devam ediyor" burada
        "hiçbir durum" değil, olumlu bir durumdur (bkz. modül başlığı,
        2026-08-25 eklemesi)."""
        with tempfile.TemporaryDirectory() as tmp:
            kok = Path(tmp)
            meta_p = _belge(kok, "ziraat-katilim", "a", DAMGALI)
            di.isaretle(di.tara(kok), kok)
            # Yeniden hasat: damga kalktı
            (kok / "ziraat-katilim" / "live" / "a.txt").write_text(
                TEMIZ, encoding="utf-8")
            bulgular = di.isaretle(di.tara(kok), kok)
            meta = json.loads(meta_p.read_text(encoding="utf-8"))
            self.assertNotIn("expiry_stamp", meta)
            self.assertEqual(meta["campaign_status"], di.STATUS_ACTIVE)
            self.assertTrue(any(b.yazildi for b in bulgular))

    def test_baskasinin_isaretine_dokunulmaz(self):
        """`reconcile_stale` veya hasatçı `expired` yazmışsa geri alınmaz."""
        with tempfile.TemporaryDirectory() as tmp:
            kok = Path(tmp)
            meta_p = _belge(kok, "kuveyt-turk", "c", TEMIZ, meta_ek={
                "campaign_status": di.STATUS_EXPIRED,
                "removal_check": {"decision": "kaldirilmis", "http_status": 404},
            })
            di.isaretle(di.tara(kok), kok)
            meta = json.loads(meta_p.read_text(encoding="utf-8"))
            self.assertEqual(meta["campaign_status"], di.STATUS_EXPIRED)
            self.assertEqual(meta["removal_check"]["decision"], "kaldirilmis")


class TestRapor(unittest.TestCase):
    def test_kuru_kosu_belirtilir_ve_belirsiz_gorunur(self):
        with tempfile.TemporaryDirectory() as tmp:
            kok = Path(tmp)
            _belge(kok, "ziraat-katilim", "a", DAMGALI)
            _belge(kok, "vakif-katilim", "b", BELIRSIZ)
            rapor = di.render_report(di.tara(kok), applied=False,
                                     raw_dir=str(kok), buckets=("live",))
        self.assertIn("KURU KOŞU", rapor)
        self.assertIn("hiçbir dosya değişmedi", rapor)
        self.assertIn("belirsiz", rapor)
        self.assertIn("2026-04", rapor)


if __name__ == "__main__":
    unittest.main()
