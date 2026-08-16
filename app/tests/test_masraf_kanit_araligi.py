"""`masraf_durumu` kanıtı: tetikleyici sözcük değil, onu taşıyan tümcecik.

İlgili: src/extraction/rules/extract.py (`_kanit_araligi`, `_cumle_araligi`)
        src/schemas.py (`ExtractedField.verify_span`)
        eval/properties.py (P1 — span/raw_value değişmezi)

## Ölçülen kusur (2026-08-16, `data/demo.db`, 494 kayıt)

`masraf_durumu` kanıt olarak yalnız TETİKLEYİCİ SÖZCÜĞÜ saklıyordu —
494 kaydın **488'i tek sözcük**:

    'Ücretsiz' 176 · 'ücretsiz' 145 · 'ücret' 95 · 'Ücret' 23
    'Masrafsız' 13 · 'masraf' 12 · 'masrafsız' 11 · 'tahsis' 12

`masrafsız` bir KANIT değil bir ETİKETtir — kanonik değerin tekrarı.
Komşu kurallar cümleyi saklıyordu (`extract_tahsis_ucreti` → "tahsis ücreti
yansıtılmayacaktır"), bu alan atlanmıştı. Şartname ürün tablosunun «Kampanya
Avantajı» hücresi kanıt cümlesini bastığı için 414 hücrede yan kolonun
birebir tekrarı görünüyordu.

Darlık BİLİNÇLİ BİR KARAR DEĞİLDİ: `git log -S`, `docs/`, vault `decisions/`
ve kod yorumları tarandı, gerekçe yok. Tersine kanıt var — DEĞER zaten 40
karakterlik ileri pencereden hesaplanıyordu, yani kaydedilen kanıt
kullanılan kanıttan dardı.

## Bu testin koruduğu iki şey

1. **Değişmez:** `text[span_start:span_end] == raw_value` birebir. Bu depo
   bunu "kendi kendini denetleyen çıkarım" diye jüriye iddia ediyor
   (`docs/SARTNAME-UYUM.md`), `eval/properties.py` P1 olarak denetliyor.
2. **`canonical_value` DEĞİŞMEZ.** Bu bir kanıt/span işidir; `{has_fee,
   amount}` birebir aynı kalmalı.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.extraction.rules.extract import extract_masraf

#: (metin, beklenen kanonik değer) — kanonik değerler DEĞİŞMEMELİ.
KANONIK_SABIT = (
    ("Kampanya kapsamında dosya masrafı alınmamaktadır.",
     {"has_fee": False, "amount": 0.0}),
    ("masrafsız finansman", {"has_fee": False, "amount": 0.0}),
    ("Bu üründe tahsis ücreti yansıtılmayacaktır.",
     {"has_fee": False, "amount": 0.0}),
    ("Tahsis ücreti 500 TL olarak tahsil edilir.",
     {"has_fee": True, "amount": 500.0}),
    ("Tahsis ücreti %0,5 oranında uygulanır.",
     {"has_fee": True, "amount": None}),
)


class SpanDegismezi(unittest.TestCase):
    """`text[span_start:span_end] == raw_value` — pazarlık dışı."""

    def test_verify_span_tutuyor(self):
        for metin, _ in KANONIK_SABIT:
            with self.subTest(metin=metin):
                f = extract_masraf(metin)
                self.assertIsNotNone(f)
                self.assertEqual(metin[f.span_start:f.span_end], f.raw_value)
                self.assertTrue(f.verify_span(metin))

    def test_uzun_ve_tabloya_benzer_metinlerde_de(self):
        for metin in (
                "Kalan Ana Para Kâr Tutarı KKDF BSMV Tahsis ücreti "
                "müşteriden peşin olarak tahsil edilecektir",
                "Azami Oran Açıklama Güncelleme Tarihi İşlem Ücreti 0 TL "
                "0 TL Ücretsiz 27.01.2022",
                "Ücretsiz",
                "İhtiyaç Kart kullanımında tahsis ücreti (%0,5) ihtiyaç "
                "kartın 2 aylık ödemesine eklenir"):
            with self.subTest(metin=metin[:40]):
                f = extract_masraf(metin)
                self.assertIsNotNone(f)
                self.assertTrue(f.verify_span(metin))


class KanonikDegerDEGISMEZ(unittest.TestCase):
    """Bu bir kanıt işi — değerler birebir aynı kalmalı."""

    def test_degerler_sabit(self):
        for metin, beklenen in KANONIK_SABIT:
            with self.subTest(metin=metin):
                self.assertEqual(extract_masraf(metin).canonical_value,
                                 beklenen)


class KanitArtikTUMCECIK(unittest.TestCase):
    """Tek sözcüklük etiket yerine okunabilir kanıt."""

    def test_iddiayi_tasiyan_tumcecik(self):
        f = extract_masraf(
            "Kampanya kapsamında 50.000 TL'ye kadar dosya masrafı "
            "alınmamaktadır.")
        self.assertEqual(
            f.raw_value,
            "Kampanya kapsamında 50.000 TL'ye kadar dosya masrafı "
            "alınmamaktadır")

    def test_tek_sozcuk_olmaktan_cikti(self):
        """Eski davranışın nöbetçisi: kanıt artık etiketin tekrarı değil."""
        f = extract_masraf("Konut finansmanında dosya masrafı alınmaz.")
        self.assertGreater(len(f.raw_value.split()), 1,
                           "kanıt yine tek sözcüğe düştü")
        self.assertIn("alınmaz", f.raw_value)

    def test_niteleyici_sozcuk_yarim_kalmaz(self):
        """40 karakterlik sol sınır sözcük ortasına düşerse GERİYE hizalanır."""
        f = extract_masraf(
            "Kampanya kapsamında 50.000 TL'ye kadar dosya masrafı "
            "alınmamaktadır.")
        self.assertTrue(f.raw_value.startswith("Kampanya"),
                        f"kanıt sözcük ortasından başladı: {f.raw_value!r}")

    def test_sag_kenar_sozcugu_bolmez(self):
        """40 karakterlik üst sınır sözcüğü ortadan bölmemeli.

        Elle doğrulamada ölçülen kırık kanıtlar: "tahsil edilece",
        "2 aylık öd", "50 yapr".
        """
        for metin, bitis in (
                ("Kalan Ana Para Kâr Tutarı KKDF BSMV Tahsis ücreti "
                 "müşteriden peşin olarak tahsil edilecektir", "edilecektir"),
                ("Size özel 3.000 TL tutarındaki 50 yapraklı Çek Karnesi "
                 "Paketi Ücretsiz olarak verilir", "verilir")):
            with self.subTest(bitis=bitis):
                f = extract_masraf(metin)
                self.assertTrue(f.raw_value.endswith(bitis),
                                f"sağ kenar sözcüğü böldü: {f.raw_value!r}")


class CumleSiniriASILMAZ(unittest.TestCase):
    """Komşu cümlenin metni kanıta bulaşmamalı — vade işindeki disiplin."""

    def test_onceki_cumle_bulasmaz(self):
        f = extract_masraf(
            "Kampanya 31 Aralık 2026 tarihine kadar geçerlidir. "
            "Dosya masrafı alınmaz.")
        self.assertNotIn("Aralık", f.raw_value)
        self.assertNotIn("geçerlidir", f.raw_value)

    def test_sonraki_cumle_bulasmaz(self):
        f = extract_masraf(
            "Dosya masrafı alınmaz. Kampanya 31 Aralık 2026 tarihine "
            "kadar geçerlidir.")
        self.assertNotIn("Aralık", f.raw_value)

    def test_satir_sonu_sinirdir(self):
        f = extract_masraf("Dosya masrafı alınmaz\nEkspertiz ücreti 1.000 TL")
        self.assertNotIn("Ekspertiz", f.raw_value)

    def test_kanit_makul_uzunlukta(self):
        """Noktalamasız tablo dökümünde kanıt metin dökümüne dönüşmemeli.

        Ölçüldü: cümle uzunluğu p99=1373, maks=2781 karakter. Aralık
        tetikleyici çevresinde budandığı için kanıt bu tavanı görmez.
        """
        dokum = "Ücret Tarifesi " + "Kalem Tutar Açıklama " * 60 + \
                "dosya masrafı alınmaz " + "Diğer Kalem Tutar " * 60
        f = extract_masraf(dokum)
        self.assertIsNotNone(f)
        self.assertLess(len(f.raw_value), 140,
                        f"kanıt metin dökümüne dönüştü: {len(f.raw_value)} kr")
        self.assertTrue(f.verify_span(dokum))


class MuafiyetYoluBOZULMADI(unittest.TestCase):
    """Ekspertiz muafiyeti kendi (zaten geniş) span'ini korumalı."""

    def test_ekspertiz_muafiyeti(self):
        metin = ("Kampanya kapsamında ekspertiz ücreti banka tarafından "
                 "karşılanmaktadır.")
        f = extract_masraf(metin)
        self.assertEqual(f.raw_value,
                         "ekspertiz ücreti banka tarafından karşılanmaktadır")
        self.assertTrue(f.verify_span(metin))
        self.assertEqual(f.canonical_value.get("muaf_ucret"), "ekspertiz")


if __name__ == "__main__":
    unittest.main()
