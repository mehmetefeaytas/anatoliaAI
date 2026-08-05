"""Yerel denetleyici koşucusu — kesintiye dayanıklılık ve ölçüm testleri.

İlgili: ../scripts/run_silver_verifier.py, ../src/extraction/silver/contract.py,
        ../docs/rapor/devam-gumus-denetleme.md

Bu betik, harici denetleyici oturumu on bir kez `529 Overloaded` ile düştükten
sonra yazıldı ve o deneyimin iki dersini kodda taşıyor:

  D1 — İş **anında** diske yazılmalı. Düşen turlarda sıfır satır kurtarıldı.
  D2 — Aynı komut kaldığı yerden devam etmeli; yeniden koşmak yapılmış işi
       tekrar ücretlendirmemeli.

Ayrıca denetleyicinin zayıflığı ölçülüp basılır — gizlenmez.
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
import unittest
from io import StringIO
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import run_silver_verifier as R
from src.extraction.llm.clients import LLMError


def _jsonl(p: Path, kayitlar: list[dict]) -> None:
    p.write_text("\n".join(json.dumps(k, ensure_ascii=False)
                           for k in kayitlar) + "\n", encoding="utf-8")


def _oku(p: Path) -> list[dict]:
    return [json.loads(s) for s in p.read_text(encoding="utf-8").splitlines()
            if s.strip()]


class _SahteIstemci:
    """Ollama yerine geçer. `patlayanlar` içindeki sırada hata atar."""

    def __init__(self, model: str = "sahte:1b", patlayanlar: tuple = (),
                 etiket: str = "Konut Finansmanı", supports: bool = True):
        self.model = model
        self.patlayanlar = set(patlayanlar)
        self.etiket = etiket
        self.supports = supports
        self.cagri = 0

    def generate_json(self, system: str, user: str, schema: dict) -> dict:
        self.cagri += 1
        if self.cagri in self.patlayanlar:
            raise LLMError("sahte patlama")
        return {"own_label": self.etiket, "evidence_supports": self.supports,
                "reason": "sahte gerekçe"}


class _Ortam:
    """Geçici girdi/çıktı + sahte istemci bağlamı."""

    def __init__(self, n: int = 4, **istemci):
        self.n = n
        self.istemci = _SahteIstemci(**istemci)

    def __enter__(self):
        self._td = tempfile.TemporaryDirectory()
        kok = Path(self._td.name)
        self.inp = kok / "verify_in.jsonl"
        self.out = kok / "verdicts.jsonl"
        self.prop = kok / "proposals.jsonl"
        _jsonl(self.inp, [{"doc_id": f"b--{i}", "prompt": f"metin {i}"}
                          for i in range(self.n)])
        _jsonl(self.prop, [{"doc_id": f"b--{i}", "label": "Konut Finansmanı",
                            "evidence": "e", "confidence": 0.9, "labeler": "t"}
                           for i in range(self.n)])
        self._patch = mock.patch.object(
            R, "OllamaClient", lambda **kw: self.istemci)
        self._patch.start()
        return self

    def __exit__(self, *exc):
        self._patch.stop()
        self._td.cleanup()
        return False

    def kos(self, **kw) -> tuple[int, str]:
        args = argparse.Namespace(
            inp=str(self.inp), out=str(self.out), proposals=str(self.prop),
            model="sahte:1b", timeout=5.0)
        for k, v in kw.items():
            setattr(args, k, v)
        yakala = StringIO()
        with mock.patch("sys.stdout", yakala):
            kod = R.kos(args)
        return kod, yakala.getvalue()


class TestKesintiyeDayaniklilik(unittest.TestCase):
    """D1 + D2: iş anında yazılır, tekrar koşu kaldığı yerden devam eder."""

    def test_her_karar_hemen_yazilir(self) -> None:
        with _Ortam(n=4) as o:
            o.kos()
            self.assertEqual(len(_oku(o.out)), 4)

    def test_tekrar_kosu_yapilmis_isi_atlar(self) -> None:
        with _Ortam(n=4) as o:
            o.kos()
            ilk_cagri = o.istemci.cagri
            _kod, cikti = o.kos()
            self.assertEqual(o.istemci.cagri, ilk_cagri,
                             "yapılmış iş yeniden modele gönderildi")
            self.assertIn("Yapacak iş yok", cikti)
            self.assertEqual(len(_oku(o.out)), 4, "çıktı çoğaltıldı")

    def test_yarim_kosudan_devam(self) -> None:
        """Kesinti simülasyonu: 2 karar diskte, 4 istek var -> 2 tanesi koşar."""
        with _Ortam(n=4) as o:
            _jsonl(o.out, [{"doc_id": "b--0", "own_label": "Kart",
                            "evidence_supports": True, "reason": "r",
                            "verifier": "eski"},
                           {"doc_id": "b--1", "own_label": "Kart",
                            "evidence_supports": True, "reason": "r",
                            "verifier": "eski"}])
            o.kos()
            self.assertEqual(o.istemci.cagri, 2)
            kararlar = _oku(o.out)
            self.assertEqual(len(kararlar), 4)
            # Eski kararlar KORUNUR, ezilmez.
            self.assertEqual(kararlar[0]["verifier"], "eski")

    def test_bozuk_satir_o_belgeyi_yeniden_kosturur(self) -> None:
        """Kesinti anında yarım kalan satır, o belgeyi 'yapılmış' saymamalı."""
        with _Ortam(n=2) as o:
            o.out.write_text('{"doc_id": "b--0", "own_lab',
                             encoding="utf-8")
            o.kos()
            self.assertEqual(o.istemci.cagri, 2, "bozuk satır yapılmış sayıldı")


class TestHataYalitimi(unittest.TestCase):
    """Tek belgenin patlaması turu bitirmemeli, sessiz de kalmamalı."""

    def test_patlayan_belge_atlanir_tur_devam_eder(self) -> None:
        with _Ortam(n=4, patlayanlar=(2,)) as o:
            kod, cikti = o.kos()
            self.assertEqual(kod, 0)
            self.assertEqual(len(_oku(o.out)), 3, "diğerleri de kayboldu")
            self.assertIn("1 belge hata verdi", cikti)

    def test_patlayan_belge_tekrar_kosuda_denenir(self) -> None:
        with _Ortam(n=4, patlayanlar=(2,)) as o:
            o.kos()
            o.istemci.patlayanlar = set()   # ikinci turda düzeldi
            o.kos()
            self.assertEqual(len(_oku(o.out)), 4)


class TestKokenVeSozlesme(unittest.TestCase):
    """Her kaydın kökeni denetlenebilir, alanlar sözleşmeye uygun."""

    def test_verifier_alanina_model_adi_yazilir(self) -> None:
        with _Ortam(n=1) as o:
            o.kos()
            self.assertEqual(_oku(o.out)[0]["verifier"], "ollama:sahte:1b")

    def test_karar_VerifyVerdict_olarak_okunabilir(self) -> None:
        """`merge` bu dosyayı `load_verdicts` ile okuyacak — şimdi doğrula."""
        from src.extraction.silver import load_verdicts
        with _Ortam(n=3) as o:
            o.kos()
            v = load_verdicts(str(o.out))
            self.assertEqual(len(v), 3)
            self.assertEqual(v["b--0"].own_label, "Konut Finansmanı")
            self.assertTrue(v["b--0"].evidence_supports)

    def test_null_etiket_sozlesmede_izinli(self) -> None:
        """Ana ürün belirsizse model etiket UYDURMAK zorunda kalmamalı."""
        self.assertIn("null", str(R.VERDICT_SCHEMA["properties"]["own_label"]))

    def test_baglam_penceresi_acikca_set_edilir(self) -> None:
        """Ollama varsayılanı 2048; denetleyici prompt'u onu sessizce taşırır
        ve sistem yönergesi baştan kırpılır."""
        self.assertGreaterEqual(R.NUM_CTX, 16384)


class TestOlcumGizlenmez(unittest.TestCase):
    """Denetleyicinin zayıflığı ölçülüp basılır."""

    def test_ortusme_orani_basilir(self) -> None:
        with _Ortam(n=4) as o:
            _kod, cikti = o.kos()
            self.assertIn("öneriyle örtüşme", cikti)
            self.assertIn("4/4", cikti)

    def test_tam_ortusme_lastik_damga_uyarisi_verir(self) -> None:
        """Bağımsız bir oy %100 örtüşmez — bu kip adıyla anılıyor."""
        with _Ortam(n=4) as o:
            _kod, cikti = o.kos()
            self.assertIn("lastik damga", cikti)

    def test_cok_dusuk_ortusme_gurultu_uyarisi_verir(self) -> None:
        with _Ortam(n=4, etiket="Kart") as o:   # öneri Konut, denetleyici Kart
            _kod, cikti = o.kos()
            self.assertIn("0/4", cikti)
            self.assertIn("gürültü", cikti)

    def test_oneri_dosyasi_yoksa_oran_uydurulmaz(self) -> None:
        with _Ortam(n=2) as o:
            _kod, cikti = o.kos(proposals="/olmayan/yol.jsonl")
            self.assertIn("örtüşme ölçülemedi", cikti)
            self.assertNotIn("öneriyle örtüşme  ", cikti)


class TestBosGirdi(unittest.TestCase):
    def test_bos_girdi_hata_dondurur(self) -> None:
        with _Ortam(n=0) as o:
            o.inp.write_text("", encoding="utf-8")
            kod, _ = o.kos()
            self.assertEqual(kod, 2)


if __name__ == "__main__":
    unittest.main()
