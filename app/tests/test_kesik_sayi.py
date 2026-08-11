"""Bir eşleşme sayının ORTASINDAN başlayamaz — "5000 TL" asla "000 TL" olmaz.

İlgili: ../src/extraction/rules/extract.py (`_SAYI_BASI`,
        `extract_odul_miktari`, `extract_alisveris_puani`)

## Bu testlerin varlık sebebi — ÖLÇÜLDÜ (2026-08-11, `data/demo.db`)

Kullanıcı kıyas ekranında "0 TL" değerleri gördü ve "sıfır olmaması gerek"
dedi. Haklıydı: `odul_miktari`'nda **7 çıkarım** sayının başı kesilerek
üretilmişti ve yedisi de güven kapısını (0,65) geçip kıyas tablosuna
girmişti — "en düşük ödül" sıralamasının ilk dört satırı 0 TL'ydi:

    "…Özel 5000 TL'lik Harcamaya…"      -> ham '000 TL' -> 0 TL
    "…yapılacak 5,000 TL ve üzeri…"     -> ham  '00 TL' -> 0 TL
    "…toplamda 12.500 TL harcamadan…"   -> ham   '0 TL' -> 0 TL
    "06.02.2026 00:00:00 TL Çek…"       -> ham  '00 TL' -> 0 TL  (SAAT!)

Kök neden desen değil, ÇAĞIRAN taraftı: tetikleyicinin çevresinden 30
karakterlik bir dilim alınıp desen o dilimde aranıyordu. Dilimin sol kenarı
bir sayının ortasına düşünce desenin gördüğü ilk karakter "0" oluyordu.

Düzeltme iki katmanlı ve İKİSİ DE gerekli:

1. **Çağrı yeri dilim ALMAZ** — `search(text, pos, endpos)` kullanır, böylece
   geriye-bakış `pos`tan önceki gerçek karakterleri görür.
2. **Desen sayının ortasından başlayamaz** (`_SAYI_BASI`) — çağrı yerlerinden
   biri ileride yine dilim alsa bile değer sessizce çökmez.

Korpus genelinde ölçülen etki: 8 çıkarım (7'si değer üretmiyor artık, 1'i
'00 TL' yerine doğru '120 TL'). Başka hiçbir alan etkilenmedi.

## Neden "değer yok", "0" değil

Kesik sayının doğrusu tahmin EDİLMEZ. "000 TL"nin 5000 mi 1000 mi olduğunu
çıkarımın kendisi bilemez; boş bırakmak CLAUDE.md §19'un gereğidir. Değer
yoksa kıyasta o banka için satır oluşmaz, uydurma bir sayı görünmez.
"""

from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.extraction.rules.extract import (
    _PARA_IFADESI,
    _PUAN_SAYI_RE,
    extract_alisveris_puani,
    extract_odul_miktari,
)

#: Korpustan alınmış GERÇEK cümleler — her biri bir "0 TL" üretiyordu.
KESIK_VAKALAR = (
    "Miles&Smiles Kredi Kartı Sahibi Müşterilere Özel 5000 TL'lik Harcamaya "
    "1000 Mil Hediye! Kampanya koşulları geçerlidir.",
    "Miles&Smiles Business kartından yapılacak 5,000 TL ve üzeri harcamaya "
    "1500 hediye Mil verilecektir.",
    "Asgari harcama tutarı 1000 TL'dir. Yalnızca 1000 TL altındaki işlemler "
    "tek çekim olarak kazanılacaktır.",
    "Kredi kartları ile yapılacak toplamda 12.500 TL harcamadan 0,01 gr "
    "altın kazanılacaktır.",
)


def _deger(f) -> float | None:
    if f is None or not isinstance(f.canonical_value, dict):
        return None
    return f.canonical_value.get("value")


class TestKesikSayiUretilmiyor(unittest.TestCase):
    """Asıl iddia: bu cümlelerin hiçbiri artık 0 TL üretmiyor."""

    def test_gercek_korpus_cumleleri_SIFIR_URETMIYOR(self) -> None:
        for metin in KESIK_VAKALAR:
            with self.subTest(metin=metin[:45]):
                self.assertNotEqual(
                    _deger(extract_odul_miktari(metin)), 0.0,
                    "sayının başı kesilip 0 TL üretilmiş")

    def test_ham_deger_sifirla_BASLAMIYOR(self) -> None:
        """Kesik eşleşmenin imzası: ham değerin '00 TL' gibi görünmesi."""
        for metin in KESIK_VAKALAR:
            f = extract_odul_miktari(metin)
            if f is None:
                continue
            with self.subTest(metin=metin[:45]):
                self.assertFalse(
                    re.fullmatch(r"0+\s*(?:TL|₺)", f.raw_value or "", re.I),
                    f"kesik ham değer: {f.raw_value!r}")

    def test_saat_bileseni_TUTAR_SAYILMAZ(self) -> None:
        """"06.02.2026 00:00:00 TL" satırında `TL` bir sonraki hücreye ait."""
        metin = ("6000 TL BSMV hariçtir. 06.02.2026 00:00:00 TL Çek Tahsile "
                 "Alma 30 TL 750 TL hediye edilecektir.")
        self.assertNotEqual(_deger(extract_odul_miktari(metin)), 0.0)

    def test_dogru_odul_HALA_bulunuyor(self) -> None:
        """Düzeltme, çalışan vakaları bozmamalı (geri uyum)."""
        f = extract_odul_miktari(
            "Kampanyaya katılan müşterilere 250 TL hediye verilecektir.")
        self.assertEqual(_deger(f), 250.0)

    def test_bin_ayracli_odul_TAM_okunuyor(self) -> None:
        f = extract_odul_miktari(
            "Kampanya kapsamında 1.500 TL nakit iade yapılacaktır.")
        self.assertEqual(_deger(f), 1500.0)


class TestDesenSolSiniri(unittest.TestCase):
    """Desen düzeyinde kapı: çağrı yeri ileride yine dilim alsa bile korur."""

    def test_para_deseni_sayinin_ortasindan_BASLAMAZ(self) -> None:
        desen = re.compile(_PARA_IFADESI, re.IGNORECASE)
        # Dilim, "5000" içinde başlıyormuş gibi arama yapılırsa bile...
        self.assertIsNone(desen.search("5000 TL", 1),
                          "eşleşme sayının ortasından başlayamaz")
        self.assertIsNotNone(desen.search("5000 TL", 0))

    def test_ayirac_sonrasi_da_BASLAMAZ(self) -> None:
        desen = re.compile(_PARA_IFADESI, re.IGNORECASE)
        self.assertIsNone(desen.search("12.500 TL", 3))

    def test_iki_nokta_sonrasi_saat_BASLAMAZ(self) -> None:
        desen = re.compile(_PARA_IFADESI, re.IGNORECASE)
        self.assertIsNone(desen.search("00:00:00 TL", 6))

    def test_puan_deseni_de_korunuyor(self) -> None:
        self.assertIsNone(_PUAN_SAYI_RE.search("2500 puan", 1))
        self.assertIsNotNone(_PUAN_SAYI_RE.search("2500 puan", 0))

    def test_normal_tutar_ETKILENMEDI(self) -> None:
        """Sol sınır, boşluk/noktalama sonrası tutarı elemez."""
        desen = re.compile(_PARA_IFADESI, re.IGNORECASE)
        for metin in ("Tutar: 500 TL", "toplam 1.500,50 TL", "(250 TL)"):
            with self.subTest(metin=metin):
                self.assertIsNotNone(desen.search(metin))


class TestPuanCikarimiBozulmadi(unittest.TestCase):
    """`alisveris_puani` aynı kalıptan düzeltildi; ölçülen vakası yoktu."""

    def test_puan_hala_bulunuyor(self) -> None:
        f = extract_alisveris_puani(
            "Harcamalarınıza 500 ChipPara hediye ediyoruz.")
        self.assertIsNotNone(f)
        self.assertEqual(f.canonical_value.get("value"), 500.0)


if __name__ == "__main__":
    unittest.main()
