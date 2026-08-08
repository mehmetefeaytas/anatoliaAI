"""Şapkalı ünlü erişim token'ını düşürmemeli — `kâr payı` bu projenin merkezi.

İlgili: ../src/chatbot/rag.py (`_tokenize`, `_SAPKA_INDIRGEME`),
        ../src/preprocessing/clean.py (`tr_fold`, `tr_fold_ascii`),
        ../scripts/eval_rag_terim.py (kök-parçalı terim uyarısı)

## Neden bu dosya var — ölçülmüş kayıp

`_tokenize` karakter sınıfı `[a-zçğıöşü0-9]+` idi; `â î û` bu sınıfta yok,
dolayısıyla **sözcük sınırı** sayılıyorlardı. Ortada kalan tek harfli
parçalar da "tek karakterli token atılır" kuralıyla eleniyordu:

    "kâr payı oranı"  ->  ['payı', 'oranı']      # 'kâr' TAMAMEN düştü
    "vekâlet akdi"    ->  ['vek', 'let', 'akdi']
    "müşâreke"        ->  ['müş', 'reke']

Korpusun **319 belgesi (%18)** `kâr`ı şapkalı yazıyor; hepsinde terim
erişim dizinine hiç girmiyordu. 36.000 karakterlik TKBB Müşâreke Standardı
belgesinde terim 89 kez geçmesine rağmen belge erişime katılmıyordu.

Düzeltme şapkayı tabana indirir. Yan kazanç: 84 belgedeki şapkasız
'kar payı' ile 319 belgedeki 'kâr payı' artık **aynı token**.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.chatbot import rag


class TestSapkaliUnluDusmez(unittest.TestCase):
    """Asıl regresyon: şapkalı sözcük token üretmeli, parçalanmamalı."""

    def test_kar_payi_token_uretir(self) -> None:
        self.assertIn("kar", rag._tokenize("kâr payı oranı nedir"))

    def test_sapkali_sozcuk_parcalanmaz(self) -> None:
        for metin, beklenen in (("vekâlet akdi", "vekalet"),
                                ("müşâreke standardı", "müşareke"),
                                ("icâre sözleşmesi", "icare"),
                                ("mudârebe esası", "mudarebe")):
            with self.subTest(metin=metin):
                toks = rag._tokenize(metin)
                self.assertIn(beklenen, toks)
                # Parçalanmanın imzası: kısa artık parçalar.
                self.assertNotIn("vek", toks)
                self.assertNotIn("müş", toks)

    def test_iki_yazim_AYNI_token_kumesi(self) -> None:
        """84 belge şapkasız, 319 belge şapkalı yazıyor; birleşmeliler."""
        self.assertEqual(set(rag._tokenize("kâr payı oranı")),
                         set(rag._tokenize("kar payı oranı")))


class TestMevcutDavranisKorundu(unittest.TestCase):
    """İndirgeme yalnız şapkayı kaldırır; Türkçe ayırt edici harfler kalır."""

    def test_turkce_harfler_KATLANMAZ(self) -> None:
        """`ş ç ğ ı ö ü` ayırt edicidir; katlamak 'sac'/'saç'ı birleştirirdi."""
        self.assertEqual(rag._tokenize("saç şekli"), ["saç", "şekli"])
        self.assertIn("taşıt", rag._tokenize("TAŞIT FİNANSMANI"))

    def test_tr_fold_hala_dogru(self) -> None:
        """'İ' -> 'i' + birleşen nokta tuzağı geri gelmemeli."""
        self.assertIn("finansmanı", rag._tokenize("TAŞIT FİNANSMANI"))

    def test_tek_karakterli_token_hala_atiliyor(self) -> None:
        """Osmanlıca tamlamada tire kalan 'ı' eleniyor — bu KASITLI."""
        self.assertEqual(rag._tokenize("Karz-ı hasen nedir?"),
                         ["karz", "hasen"])

    def test_tek_haneli_rakam_hala_atiliyor(self) -> None:
        self.assertEqual(rag._tokenize("5 taksit 36 ay"),
                         ["taksit", "36", "ay"])


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
