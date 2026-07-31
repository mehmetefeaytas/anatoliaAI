"""`normalize_text` denetim karakterlerini (NUL dahil) atmalı.

## Neden bu dosya var

`normalize_whitespace`'in `\\s+` deseni C0 denetim karakterlerini
**yakalamaz** — `\\x00` regex'te boşluk sayılmaz. Bu yüzden NUL baytları
ön işleme, çıkarım ve veri tabanı katmanlarının hepsini geçiyordu.

Korpusta ölçüldü: 849 belgeden birinde (bir KVKK aydınlatma **PDF'i**
metin olarak kaydedilmiş) 177.768 baytın **352'si NUL**.

Kritik olan taşınabilirlik: **SQLite NUL'u sessizce yutuyor, PostgreSQL
ise `text` sütununda kabul etmiyor** ve bağlantıyı hata ile düşürüyor.
Yani aynı korpus SQLite'ta çalışıp Postgres'te patlıyordu — ve bu, iki
backend paritesi kurulana kadar görünmüyordu.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.preprocessing.clean import normalize_text, normalize_whitespace

NUL = "\x00"


class TestDenetimKarakterleri(unittest.TestCase):

    def test_nul_atilir(self) -> None:
        self.assertNotIn(NUL, normalize_text(f"Kâr payı{NUL} oranı %1,89"))

    def test_nul_kelimeleri_birlestirmez(self) -> None:
        """NUL silinirken metin bozulmamalı: 'a\\x00b' -> 'ab' değil 'a b'
        olmasına gerek yok, ama sözcük içi NUL sözcüğü bölmemeli."""
        self.assertEqual(normalize_text(f"%1,{NUL}89"), "%1,89")

    def test_diger_c0_karakterleri(self) -> None:
        for kod in (0x01, 0x07, 0x08, 0x0B, 0x0C, 0x1F, 0x7F):
            with self.subTest(kod=hex(kod)):
                sonuc = normalize_text(f"vade{chr(kod)} 36 ay")
                self.assertNotIn(chr(kod), sonuc)

    def test_sekme_ve_satirsonu_korunur_bosluga_cevrilir(self) -> None:
        """`\\t`, `\\n`, `\\r` denetim karakteri ama MEŞRU boşluktur —
        atılmaz, `normalize_whitespace` tarafından boşluğa indirgenir."""
        self.assertEqual(normalize_text("kâr payı\toranı\n%1,89"),
                         "kâr payı oranı %1,89")

    def test_turkce_karakterler_korunur(self) -> None:
        """Denetim karakteri süzgeci TR harflerine dokunmamalı."""
        self.assertEqual(normalize_text("şçğüöıİ ÜÇĞÖŞ"), "şçğüöıİ ÜÇĞÖŞ")

    def test_normalize_whitespace_nul_yakalamaz(self) -> None:
        """Kök nedeni kayda geçirir: `\\s+` deseni NUL'u boşluk saymaz.

        Bu test bir DAVRANIŞ belgelemesi. `normalize_whitespace` tek başına
        NUL'u temizlemiyor; temizlik `normalize_text`'in sorumluluğunda.
        """
        self.assertIn(NUL, normalize_whitespace(f"a{NUL}b"))

    def test_bos_ve_none_guvenli(self) -> None:
        self.assertEqual(normalize_text(""), "")
        self.assertEqual(normalize_text(NUL * 10), "")


class TestGercekKorpus(unittest.TestCase):
    """Korpusta NUL taşıyan gerçek belge normalize edildikten sonra temiz."""

    def test_korpusta_nul_kalmiyor(self) -> None:
        kok = Path(__file__).resolve().parents[1] / "data" / "raw"
        if not kok.exists():
            self.skipTest("korpus bu ortamda yok")
        kalan = 0
        bakilan = 0
        for f in kok.rglob("*.txt"):
            bakilan += 1
            metin = normalize_text(f.read_text(encoding="utf-8", errors="replace"))
            kalan += metin.count(NUL)
        self.assertGreater(bakilan, 0, "hiç belge okunamadı — test anlamsız")
        self.assertEqual(kalan, 0, f"{bakilan} belgede {kalan} NUL kaldı")


if __name__ == "__main__":
    unittest.main()
