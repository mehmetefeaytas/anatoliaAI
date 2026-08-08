"""Takvim yılı vade sanılmamalı — güvenlik seti K02'nin kök nedeni.

İlgili: ../src/extraction/rules/extract.py (`_takvim_yili`, `MAKS_VADE_AY`),
        ../data/safety/katilim-guvenlik-seti.jsonl (K02),
        ../docs/rapor/guvenlik-llm-modu.md

## Neden bu dosya var

`vade_ay` deseni `(\\d[\\d.,]*)\\s*(ay|yıl|yil|sene)(?:…|ı|…)?` biçiminde
olduğu için "2026 yılı" ifadesini yakalıyor ve `normalize_term_months` onu
2026 × 12 = **24312 ay** yapıyordu.

Sonuç ürün yüzeyinde görünüyordu: "en yüksek vade hangi bankada?" sorusuna
chatbot **"Albaraka Türk, 24312 ay"** (2026 yıl) cevabını veriyordu.
`data/demo.db`'de bu sınıftan 10 kayıt vardı ('2024/2025/2026 yılı'), ayrıca
bir açılır menü döküntüsü ('2021 Ay'). Artefaktlar dışlandığında korpustaki
meşru en yüksek vade **120 ay**.

Bu testler iki kapıyı ayrı ayrı kilitler; biri kaldırılırsa diğeri hatayı
tek başına yakalayamaz.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.extraction.rules.extract import MAKS_VADE_AY, extract_vade


def _deger(metin: str):
    f = extract_vade(metin)
    return f.canonical_value if f else None


class TestTakvimYiliVadeSayilmaz(unittest.TestCase):
    """KAPI 1 — 1900-2100 aralığı + yıl/sene birimi = tarih, süre değil."""

    def test_yalnizca_takvim_yili_iceren_metin_alan_uretmez(self) -> None:
        for metin in ("2024 Yılı Faaliyet Raporu",
                      "2026 yılı kampanya takvimi",
                      "2025 yılında yürürlüğe girer"):
            with self.subTest(metin=metin):
                self.assertIsNone(_deger(metin))

    def test_takvim_yili_varken_GERCEK_vade_secilir(self) -> None:
        """Asıl risk: takvim yılı, aynı metindeki doğru vadeyi bastırıyordu."""
        self.assertEqual(
            _deger("2026 yılı kampanyası kapsamında 36 ay vade sunulur."), 36)

    def test_eksiz_yazim_da_reddedilir(self) -> None:
        """'2026 yıl' de takvim yılıdır; ek aramaya güvenilmez."""
        self.assertIsNone(_deger("2026 yıl"))

    def test_arahk_disi_yil_MESRU_kalir(self) -> None:
        """Kapı yalnız takvim aralığını eler; gerçek yıl vadesi dokunulmaz."""
        self.assertEqual(_deger("1 yıl vadeli katılma hesabı"), 12)
        self.assertEqual(_deger("30 yıl vadeli konut finansmanı"), 360)


class TestGercekciUstSinir(unittest.TestCase):
    """KAPI 2 — aya çevrilmiş değer MAKS_VADE_AY'ı aşamaz."""

    def test_acilir_menu_dokuntusu_elenir(self) -> None:
        """'2021 Ay' ≈ 168 yıl; 'Yıl Seçiniz' menüsünden geliyor."""
        self.assertIsNone(_deger("Yıl Seçiniz 2021 Ay Seçiniz"))

    def test_sinirin_hemen_altindaki_deger_KABUL_edilir(self) -> None:
        self.assertEqual(_deger(f"{MAKS_VADE_AY} ay vade"), MAKS_VADE_AY)

    def test_sinirin_ustundeki_deger_REDDEDILIR(self) -> None:
        self.assertIsNone(_deger(f"{MAKS_VADE_AY + 1} ay vade"))


class TestMevcutDavranisKorundu(unittest.TestCase):
    """Düzeltme, çalışan kuralları bozmamalı."""

    def test_promosyon_donemi_hala_geri_itiliyor(self) -> None:
        """'ilk N ay' gerçek vade değildir (zor-anlama vakası)."""
        self.assertEqual(_deger("İlk 6 ay ödemesiz, 48 ay vade"), 48)

    def test_ek_cekimli_biçimler(self) -> None:
        self.assertEqual(_deger("Vade 120 aya kadar uzayabilir."), 120)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
