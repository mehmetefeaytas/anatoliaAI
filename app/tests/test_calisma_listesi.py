"""Round1 hazırlık kartı üreteci testleri.

İlgili: ../scripts/calisma_listesi.py

## Neden bu testler

Kart bir anotatöre "senin kalıbın şu" diyor. Yanlış söylerse iki tür zarar
verir ve ikisi de sessizdir:

1. **Fazla söylerse** olmayan bir hata için kural öğretilir; kartın
   güvenilirliği gider ve okunmaz.
2. **Eksik söylerse** kalibrasyonda ölçülmüş kalıp round1'in ~2.400 satırına
   taşınır — kartın var olma sebebi tam da bunu önlemek.

Bu yüzden burada çitlenen davranışlar:

- **Kaynak hakemlik ÖNCESİ dosyadır.** Güncel dosyalar hakemlikten geçti;
  oradan ölçmek "kimse hata yapmamış" der. Yedek yoksa betik SESSİZCE "temiz"
  demez, uyarı basar.
- **Kalıp dedektörleri gerçekten ayırt eder.** Kanonik değer kalıba girmez,
  metinden alıntı girer; izinli `hedef_kitle` etiketi girmez, serbest metin
  girer; model dolu iken `absent` MEŞRUDUR (halüsinasyon iddiası) ve kalıba
  girmez.
- **Toplam AYRIK hücredir.** Bir hücre birden çok kalıba girebilir; kalıp
  sayılarını toplamak D'de 278 gösterip 169 hücreyi şişirirdi.
- **Betik CSV'ye YAZMAZ.** Gold'u bir betiğin doldurması ölçümü anlamsız
  kılar; girdi dosyalarının baytları koşudan sonra da aynı kalmalı.
"""

from __future__ import annotations

import csv
import hashlib
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.calisma_listesi import (
    GUIDE_MINUTES,
    GUIDE_ROWS,
    PRE_ARBITRATION_SUFFIX,
    ROUND1_FILES,
    _hedef_kitle_gecersiz,
    _metinden_alinti,
    _taksit_vade,
    _yanlis_absent,
    calibration_name,
    olc,
    out_name,
    render,
    sure_dk,
    topla,
    yaz,
)

COLS = ["doc_id", "bank", "field", "model_value", "model_conf",
        "confidence_source", "disagreement", "snippet", "gold_value",
        "verdict", "note"]


def satir(doc_id: str, field: str, *, model: str = "", gold: str = "",
          verdict: str = "", note: str = "") -> dict:
    return {"doc_id": doc_id, "bank": "test", "field": field,
            "model_value": model, "model_conf": "0.9",
            "confidence_source": "rule", "disagreement": "HAYIR",
            "snippet": "…", "gold_value": gold, "verdict": verdict,
            "note": note}


def yaz_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLS, delimiter=";")
        writer.writeheader()
        writer.writerows(rows)


class DedektorTest(unittest.TestCase):
    """Kalıp dedektörleri — neyi yakalar, neyi yakalamaz."""

    def test_absent_model_dolu_iken_MESRUDUR(self) -> None:
        """Model bir değer ürettiyse `absent` halüsinasyon iddiasıdır."""
        mesru = satir("d", "vade_ay", model="12", verdict="absent")
        yanlis = satir("d", "vade_ay", model="", verdict="absent")

        self.assertFalse(_yanlis_absent(mesru, None))
        self.assertTrue(_yanlis_absent(yanlis, None))

    def test_kanonik_deger_alinti_sayilmaz(self) -> None:
        for kanonik in ("48", "1.89", '{"min": 12, "max": 48}',
                        '{"value": 500, "currency": "TRY"}'):
            with self.subTest(kanonik):
                self.assertFalse(_metinden_alinti(
                    satir("d", "vade_ay", gold=kanonik), None))

    def test_metinden_alinti_yakalanir(self) -> None:
        for ham in ("en fazla 48 aya kadar", "1-12 ay arası", "36 ay"):
            with self.subTest(ham):
                self.assertTrue(_metinden_alinti(
                    satir("d", "vade_ay", gold=ham), None))

    def test_sayisal_olmayan_alanda_metin_alinti_degildir(self) -> None:
        """`kampanya_kosullari` zaten cümle taşır — kalıba girmemeli."""
        self.assertFalse(_metinden_alinti(
            satir("d", "kampanya_kosullari", gold="Yalnızca mobilden başvuru"),
            None))

    def test_izinli_hedef_kitle_etiketi_gecerlidir(self) -> None:
        for gecerli in ("yeni_musteri", '["yeni_musteri", "maas_musterisi"]',
                        "maas_musterisi | belirli_segment"):
            with self.subTest(gecerli):
                self.assertFalse(_hedef_kitle_gecersiz(
                    satir("d", "hedef_kitle", gold=gecerli), None))

    def test_hedef_kitle_serbest_metni_yakalanir(self) -> None:
        for ham in ("Bireysel müşteriler", '["gerçek kişi bireysel müşteriler"]',
                    "yeni müşteri"):
            with self.subTest(ham):
                self.assertTrue(_hedef_kitle_gecersiz(
                    satir("d", "hedef_kitle", gold=ham), None))

    def test_taksit_kelimesi_belgede_varsa_kalip_degil(self) -> None:
        row = satir("d", "taksit_sayisi", gold="6")

        self.assertFalse(_taksit_vade(row, "vade farksız 6 taksit imkânı"))
        self.assertTrue(_taksit_vade(row, "48 aya varan vade"))

    def test_belge_metni_yoksa_taksit_kalibi_iddia_edilmez(self) -> None:
        """Metin okunamadıysa 'taksit geçmiyor' DENEMEZ — sessiz yanlış olur."""
        self.assertFalse(_taksit_vade(satir("d", "taksit_sayisi", gold="6"),
                                      None))


class HazirlikKartiTest(unittest.TestCase):

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self._tmp.name)
        (self.dir / "belgeler").mkdir()
        self.addCleanup(self._tmp.cleanup)

    def kur(self, ad: str, *, guncel: list[dict],
            onceki: list[dict] | None = None,
            round1: list[dict] | None = None) -> Path:
        yol = self.dir / calibration_name(ad)
        yaz_csv(yol, guncel)
        if onceki is not None:
            yaz_csv(yol.with_name(yol.name + PRE_ARBITRATION_SUFFIX), onceki)
        if round1 is not None:
            yaz_csv(self.dir / ROUND1_FILES[ad], round1)
        return yol

    def belge(self, doc_id: str, metin: str) -> None:
        (self.dir / "belgeler" / f"{doc_id}.txt").write_text(
            metin, encoding="utf-8")

    # -- kaynak ------------------------------------------------------------ #
    def test_kalip_hakemlik_oncesinden_olculur(self) -> None:
        """Hakemlik hatayı sildiyse bile kart onu göstermeli."""
        temiz = [satir("d1", "vade_ay", model="12", verdict="ok")]
        hatali = [satir("d1", "vade_ay", model="", verdict="absent")]
        self.kur("D", guncel=temiz, onceki=hatali)

        kart = olc("D", self.dir)

        self.assertEqual([b.kalip.ad for b in kart.bulgular], ["yanlis-absent"])
        self.assertEqual(kart.bulgular[0].sayi, 1)

    def test_yedek_yoksa_sessizce_temiz_denmez(self) -> None:
        self.kur("D", guncel=[satir("d1", "vade_ay", model="", verdict="absent")])

        kart = olc("D", self.dir)

        self.assertEqual(kart.bulgular, [])
        self.assertTrue(kart.uyarilar, "uyarı basılmalıydı")
        self.assertIn("ÖLÇÜLEMEDİ", " ".join(kart.uyarilar))
        self.assertIsNone(kart.acik_karar, "ölçülemeyen sayı basılmamalı")

    # -- sayım -------------------------------------------------------------- #
    def test_toplam_ayrik_hucre_sayar(self) -> None:
        """Bir hücre iki kalıba girerse toplam 1 olmalı, 2 değil."""
        # `absent` + sayısal alana cümle: hem lint kalıbı hem alıntı kalıbı.
        rows = [satir("d1", "vade_ay", model="12",
                      gold="Leasing süreci ve hesaplama aracı", verdict="absent")]
        self.kur("D", guncel=rows, onceki=rows)

        kart = olc("D", self.dir)

        self.assertGreaterEqual(len(kart.bulgular), 2, "iki kalıp beklenirdi")
        self.assertEqual(sum(b.sayi for b in kart.bulgular), 2)
        self.assertEqual(kart.toplam_hata, 1, "ayrık hücre 1 olmalı")

    def test_acik_karar_yazili_duzeltmeyi_kapsar(self) -> None:
        """Boş `verdict` + dolu `gold_value` karardır (kılavuz §3.2)."""
        rows = [satir("d1", "vade_ay", verdict="ok"),
                satir("d2", "vade_ay", gold="48"),
                satir("d3", "vade_ay")]
        self.kur("B", guncel=rows, onceki=rows)

        kart = olc("B", self.dir)

        self.assertEqual(kart.acik_karar, 2)
        self.assertEqual(kart.kalibrasyon_satir, 3)

    def test_kalip_yoksa_bulgu_uretilmez(self) -> None:
        rows = [satir("d1", "vade_ay", model="12", verdict="ok")]
        self.kur("A", guncel=rows, onceki=rows)

        kart = olc("A", self.dir)

        self.assertEqual(kart.bulgular, [])
        self.assertEqual(kart.toplam_hata, 0)

    def test_bulgular_buyukten_kucuge_siralanir(self) -> None:
        rows = [satir(f"d{i}", "vade_ay", model="", verdict="absent")
                for i in range(3)]
        rows.append(satir("d9", "hedef_kitle", gold="Bireysel müşteriler"))
        self.kur("D", guncel=rows, onceki=rows)

        adlar = [b.kalip.ad for b in olc("D", self.dir).bulgular]

        self.assertEqual(adlar[0], "yanlis-absent")

    # -- round1 künyesi ----------------------------------------------------- #
    def test_round1_dosyasi_ve_suresi_raporlanir(self) -> None:
        rows = [satir("d1", "vade_ay", model="12", verdict="ok")]
        r1 = [satir(f"r{i}", "vade_ay", model="12") for i in range(GUIDE_ROWS)]
        self.kur("C", guncel=rows, onceki=rows, round1=r1)

        kart = olc("C", self.dir)

        self.assertEqual(Path(kart.round1_dosyasi).name, ROUND1_FILES["C"])
        self.assertEqual(kart.round1_satir, GUIDE_ROWS)
        self.assertEqual(kart.round1_belge, GUIDE_ROWS)
        self.assertEqual(sure_dk(kart.round1_satir), GUIDE_MINUTES)

    def test_kart_kalibrasyona_donulmeyecegini_soyler(self) -> None:
        rows = [satir("d1", "vade_ay", model="", verdict="absent")]
        self.kur("D", guncel=rows, onceki=rows)

        metin = render(olc("D", self.dir))

        self.assertIn("GERİ DÖNMÜYORSUNUZ", metin)
        self.assertIn("yalnız okur", metin, "betiğin sınırı yazılı olmalı")
        self.assertIn("Model boş bırakmışken", metin)

    def test_boru_karakteri_tabloyu_bozmaz(self) -> None:
        rows = [satir("d1", "vade_ay", gold="12 ay | 48 ay")]
        self.kur("A", guncel=rows, onceki=rows)

        metin = render(olc("A", self.dir))

        self.assertNotIn("| 48 ay ", metin)

    # -- betik anotasyon YAPMAZ --------------------------------------------- #
    def test_girdi_csvleri_degismez(self) -> None:
        rows = [satir("d1", "vade_ay", model="", verdict="absent"),
                satir("d2", "hedef_kitle", gold="Bireysel müşteriler")]
        yollar = []
        for ad in "ABCD":
            yollar.append(self.kur(ad, guncel=rows, onceki=rows, round1=rows))
        once = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in yollar}

        yaz(topla(self.dir), self.dir)

        for yol in yollar:
            self.assertEqual(hashlib.sha256(yol.read_bytes()).hexdigest(),
                             once[yol], f"{yol.name} DEĞİŞTİ — betik yazmamalı")

    def test_yaz_anotator_basina_tek_dosya_uretir(self) -> None:
        rows = [satir("d1", "vade_ay", model="12", verdict="ok")]
        for ad in "ABCD":
            self.kur(ad, guncel=rows, onceki=rows)

        yazilan = yaz(topla(self.dir), self.dir)

        self.assertEqual([p.name for p in yazilan],
                         [out_name(ad) for ad in "ABCD"])


if __name__ == "__main__":
    unittest.main()
