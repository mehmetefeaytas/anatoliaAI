"""Kuyruk çözücünün YAZMA davranışı — veri kaybı ve bayat rapor regresyonları.

İlgili: ../scripts/resolve_queue.py, ../scripts/build_silver.py

Bu dosya iki gerçek olayı çitliyor; ikisi de bu betiği ikinci kez koştururken
yaşandı ve ikisi de SESSİZDİ:

  O1 — VERİ KAYBI. Betik `silver.jsonl`'a EKLER ama `queue.jsonl` ve
       `rejected_from_queue.jsonl` dosyalarını "w" ile yazar. Kuyruk boşken
       ikinci koşu, ilk turun ürettiği 3 reddedilen kaydı SIFIRLADI.
       CLAUDE.md'nin "silme yok" kuralının sessiz ihlali.

  O2 — BAYAT RAPOR. `build_silver merge` raporu yazar, SONRA bu betik silver'a
       kayıt ekler. Rapor tazelenmeyince 461 diyordu, dosyada 505 kayıt vardı.
       Tehlikeli olan sayı değil `sinif_dengesi_uyarilari`: fine-tune kapısı
       açıkken kapalı görünebilirdi.
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from io import StringIO
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import resolve_queue as RQ
from scripts.build_silver import MIN_PER_CLASS
from src.schemas import CAMPAIGN_TYPES


def _jsonl(p: Path, kayitlar: list[dict]) -> None:
    p.write_text("".join(json.dumps(k, ensure_ascii=False) + "\n"
                         for k in kayitlar), encoding="utf-8")


def _oku(p: Path) -> list[dict]:
    if not p.is_file():
        return []
    return [json.loads(s) for s in p.read_text(encoding="utf-8").splitlines()
            if s.strip()]


class _Ortam:
    """Geçici gümüş dizini: silver + queue + rejected + rapor."""

    def __init__(self, kuyruk: list[dict], silver_n: int = 3):
        self.kuyruk = kuyruk
        self.silver_n = silver_n

    def __enter__(self):
        self._td = tempfile.TemporaryDirectory()
        self.dir = Path(self._td.name)
        self.silver = self.dir / "silver.jsonl"
        self.queue = self.dir / "queue.jsonl"
        self.rejected = self.dir / "rejected_from_queue.jsonl"
        self.rapor = self.dir / "silver_report.json"
        self.trainable = self.dir / "trainable.jsonl"

        _jsonl(self.silver, [{"doc_id": f"b--{i}", "label": "Kart",
                              "status": "silver"}
                             for i in range(self.silver_n)])
        _jsonl(self.queue, self.kuyruk)
        # İlk turdan kalmış, KORUNMASI gereken kayıtlar.
        _jsonl(self.rejected, [{"doc_id": "eski--1", "label": None,
                                "resolution": "kural2_taksonomi_disi"}])
        self.trainable.write_text("", encoding="utf-8")
        self.rapor.write_text(json.dumps({
            "toplam": 10, "durum": {"silver": 1, "reject": 0, "queue": 9},
            "sinif_dagilimi": {"Kart": 1}, "sinif_dengesi_uyarilari": ["bayat"],
        }, ensure_ascii=False), encoding="utf-8")
        return self

    def __exit__(self, *exc):
        self._td.cleanup()
        return False

    def kos(self, apply: bool = True) -> str:
        argv = ["--queue", str(self.queue), "--silver", str(self.silver),
                "--trainable", str(self.trainable), "--out-dir", str(self.dir)]
        if apply:
            argv.append("--apply")
        yakala = StringIO()
        with mock.patch("sys.stdout", yakala):
            kod = RQ.main(argv)
        assert kod == 0, f"resolve_queue çıkış kodu {kod}"
        return yakala.getvalue()


class TestBosKuyrukVeriSilmez(unittest.TestCase):
    """O1: boş kuyrukla koşu hiçbir dosyayı sıfırlamamalı."""

    def test_reddedilenler_korunur(self) -> None:
        with _Ortam(kuyruk=[]) as o:
            cikti = o.kos()
            self.assertEqual(len(_oku(o.rejected)), 1,
                             "önceki turun reddedilen kaydı silindi")
            self.assertIn("dokunulmadı", cikti)

    def test_silver_cogaltilmaz(self) -> None:
        with _Ortam(kuyruk=[], silver_n=5) as o:
            o.kos()
            o.kos()
            self.assertEqual(len(_oku(o.silver)), 5)

    def test_bos_kuyruk_yine_de_raporu_tazeler(self) -> None:
        """Bayat raporu düzeltmek, betiği boşta koşturmanın tek meşru sebebi."""
        with _Ortam(kuyruk=[], silver_n=4) as o:
            o.kos()
            r = json.loads(o.rapor.read_text(encoding="utf-8"))
            self.assertEqual(r["durum"]["silver"], 4)


class TestRaporTazelenir(unittest.TestCase):
    """O2: merge'in yazdığı rapor, eklenen kayıtlardan sonra güncellenmeli."""

    KUYRUK = [{"doc_id": "b--9", "votes": {"labeler": "Kart",
                                           "verifier": "Kart"},
               "evidence": "kart", "text": "kredi kartı kampanyası"}]

    def test_silver_sayisi_guncellenir(self) -> None:
        with _Ortam(kuyruk=self.KUYRUK, silver_n=3) as o:
            o.kos()
            r = json.loads(o.rapor.read_text(encoding="utf-8"))
            self.assertEqual(r["durum"]["silver"], len(_oku(o.silver)))
            self.assertNotEqual(r["durum"]["silver"], 1, "bayat kaldı")

    def test_kuyruk_sifirlanir(self) -> None:
        with _Ortam(kuyruk=self.KUYRUK) as o:
            o.kos()
            r = json.loads(o.rapor.read_text(encoding="utf-8"))
            self.assertEqual(r["durum"]["queue"], 0)

    def test_tazelendigi_isaretlenir(self) -> None:
        with _Ortam(kuyruk=self.KUYRUK) as o:
            o.kos()
            r = json.loads(o.rapor.read_text(encoding="utf-8"))
            self.assertTrue(r.get("kuyruk_cozumu_sonrasi"))

    def test_eksik_sinif_listesi_yeniden_hesaplanir(self) -> None:
        """Bayat liste ("bayat") gitmeli, yerine gerçek hesap gelmeli."""
        with _Ortam(kuyruk=self.KUYRUK) as o:
            o.kos()
            r = json.loads(o.rapor.read_text(encoding="utf-8"))
            self.assertNotIn("bayat", r["sinif_dengesi_uyarilari"])
            # 8 sınıfın çoğu eşiğin altında olmalı (küçük sahte küme).
            self.assertTrue(all("/" in s
                                for s in r["sinif_dengesi_uyarilari"]))

    def test_esik_ve_taksonomi_tek_kaynaktan(self) -> None:
        """İki dosya ayrışırsa farklı 'eksik sınıf' listesi üretirlerdi."""
        with _Ortam(kuyruk=self.KUYRUK) as o:
            o.kos()
            r = json.loads(o.rapor.read_text(encoding="utf-8"))
            for satir in r["sinif_dengesi_uyarilari"]:
                sinif = satir.split(":")[0]
                self.assertIn(sinif, CAMPAIGN_TYPES)
                self.assertIn(f"/{MIN_PER_CLASS}", satir)


class TestKuruKosuYazmaz(unittest.TestCase):
    def test_apply_yoksa_dosya_degismez(self) -> None:
        with _Ortam(kuyruk=TestRaporTazelenir.KUYRUK, silver_n=3) as o:
            o.kos(apply=False)
            self.assertEqual(len(_oku(o.silver)), 3)
            self.assertEqual(len(_oku(o.rejected)), 1)
            r = json.loads(o.rapor.read_text(encoding="utf-8"))
            self.assertEqual(r["durum"]["silver"], 1, "kuru koşu rapor yazdı")


if __name__ == "__main__":
    unittest.main()
