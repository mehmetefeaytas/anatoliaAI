"""Çelişki tarama artefaktı — tazelik kuralı ve biçim eşliği.

İlgili: ../src/comparison/celiski_artefakti.py
        ../scripts/celiski_tarama.py
        ../src/api/routers/denetim.py

## Neden bu dosya var

Artefakt iki sessiz bozulma yolu açıyor ve ikisi de panele yanlış bilgi
basar:

1. **Bayat artefakt taze sanılır.** Korpus değişir, artefakt eski kalır ve
   panel "bu belgede çelişki yok" demeye devam eder. İmza denetimi bunu
   kapatıyor; testler imzanın gerçekten ayrıştığını doğruluyor.
2. **Biçim ayrışır.** `scripts/celiski_tarama.py` ile `denetim.py` aynı
   sözlüğü ayrı ayrı kuruyor. Anahtar listeleri ayrıştığı gün artefakt
   okunur, panele basılır ve eksik alan sessizce boş görünür.
"""

from __future__ import annotations

import json
import pathlib
import tempfile
import unittest

from src.comparison import celiski_artefakti as A


class _SahteDepo:
    """`all_campaigns(govde=False)` dışında hiçbir şey sunmaz — imza o kadarını ister."""

    def __init__(self, satirlar):
        self._satirlar = satirlar

    def all_campaigns(self, *, govde: bool = True):
        return list(self._satirlar)


class TestKorpusImzasi(unittest.TestCase):
    def test_belge_sayisi_degisince_imza_degisir(self) -> None:
        a = A.korpus_imzasi(_SahteDepo([{"scraped_at": "2026-08-01"}]))
        b = A.korpus_imzasi(_SahteDepo([{"scraped_at": "2026-08-01"},
                                        {"scraped_at": "2026-08-01"}]))
        self.assertNotEqual(a, b)

    def test_yeni_toplama_damgasi_imzayi_degistirir(self) -> None:
        """Tazeleme her zaman yeni bir `scraped_at` yazar — imza onu yakalamalı."""
        a = A.korpus_imzasi(_SahteDepo([{"scraped_at": "2026-08-01"}]))
        b = A.korpus_imzasi(_SahteDepo([{"scraped_at": "2026-08-20"}]))
        self.assertNotEqual(a, b)

    def test_ayni_korpus_ayni_imza(self) -> None:
        satirlar = [{"scraped_at": "2026-08-01"}, {"scraped_at": "2026-08-19"}]
        self.assertEqual(A.korpus_imzasi(_SahteDepo(satirlar)),
                         A.korpus_imzasi(_SahteDepo(list(satirlar))))

    def test_bos_korpus_None(self) -> None:
        """`None` artefaktı geçersiz kılar — ölçemediğimizde TAZE varsaymıyoruz."""
        self.assertIsNone(A.korpus_imzasi(_SahteDepo([])))

    def test_depo_dusunce_None(self) -> None:
        class Kirik:
            def all_campaigns(self, **_):
                raise RuntimeError("depo kapalı")
        self.assertIsNone(A.korpus_imzasi(Kirik()))


class TestOkuYaz(unittest.TestCase):
    def setUp(self) -> None:
        self._gecici = tempfile.TemporaryDirectory()
        self.kok = pathlib.Path(self._gecici.name)
        (self.kok / "data").mkdir()
        self.addCleanup(self._gecici.cleanup)

    def test_yazilan_okunur(self) -> None:
        A.yaz([{"kind": "x"}], "imza-1", kok=self.kok)
        self.assertEqual(A.oku("imza-1", kok=self.kok), [{"kind": "x"}])

    def test_imza_tutmazsa_None(self) -> None:
        A.yaz([{"kind": "x"}], "imza-1", kok=self.kok)
        self.assertIsNone(A.oku("imza-2", kok=self.kok))

    def test_imza_None_ise_None(self) -> None:
        A.yaz([{"kind": "x"}], "imza-1", kok=self.kok)
        self.assertIsNone(A.oku(None, kok=self.kok))

    def test_dosya_yoksa_None(self) -> None:
        self.assertIsNone(A.oku("imza-1", kok=self.kok))

    def test_eski_surum_yok_sayilir(self) -> None:
        """Şema değişirse eski artefakt okunmamalı — alan adı kaymış olabilir."""
        hedef = A.yol(self.kok)
        hedef.write_text(json.dumps(
            {"surum": A.SURUM - 1, "korpus_imzasi": "imza-1",
             "bulgular": [{"kind": "x"}]}), encoding="utf-8")
        self.assertIsNone(A.oku("imza-1", kok=self.kok))

    def test_bozuk_json_None(self) -> None:
        A.yol(self.kok).write_text("{ bozuk", encoding="utf-8")
        self.assertIsNone(A.oku("imza-1", kok=self.kok))

    def test_bulgular_liste_degilse_None(self) -> None:
        A.yol(self.kok).write_text(json.dumps(
            {"surum": A.SURUM, "korpus_imzasi": "i", "bulgular": {"a": 1}}),
            encoding="utf-8")
        self.assertIsNone(A.oku("i", kok=self.kok))

    def test_bos_bulgu_listesi_GECERLI(self) -> None:
        """Sıfır çelişki bir SONUÇTUR; `None` ile karıştırılmamalı.

        `oku()` `None` dönerse çağıran 47 saniyelik taramayı boşuna koşar ve
        yine sıfır bulur. Boş liste ile "artefakt yok" ayrımı şart.
        """
        A.yaz([], "imza-bos", kok=self.kok)
        self.assertEqual(A.oku("imza-bos", kok=self.kok), [])


class TestBicimEsligi(unittest.TestCase):
    """Betik ile uç noktanın kayıt anahtarları AYNI olmalı."""

    def test_anahtarlar_denetim_govdesiyle_ayni(self) -> None:
        beklenen = {"bank", "bank_name", "campaign_id", "campaign_type",
                    "source_url", "kind", "detail", "fields"}
        kaynak = (pathlib.Path(__file__).resolve().parents[1]
                  / "scripts" / "celiski_tarama.py").read_text(encoding="utf-8")
        for anahtar in beklenen:
            self.assertIn(f'"{anahtar}"', kaynak,
                          f"`{anahtar}` betiğin kayıt sözlüğünde yok — "
                          f"artefakt panelde eksik alanla görünürdü")

    def test_denetim_routeri_artefakti_okuyor(self) -> None:
        """Bağ koparsa artefakt üretilir ama HİÇ kullanılmaz (sessiz kayıp)."""
        kaynak = (pathlib.Path(__file__).resolve().parents[1]
                  / "src" / "api" / "routers" / "denetim.py"
                  ).read_text(encoding="utf-8")
        self.assertIn("celiski_artefakti.oku", kaynak)
        self.assertIn("celiski_artefakti.korpus_imzasi", kaynak)


if __name__ == "__main__":                   # pragma: no cover
    unittest.main()
