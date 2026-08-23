"""SBOM sapma kapısının davranışı.

Çalıştır:  python -m unittest tests.test_sbom_sapma  (app/ kökünden)

## Neden bu testler

Bu kapı, İKİ KEZ yaşanan aynı gerilemeye karşı yazıldı: demo videosu
seslendirmesi `.venv`e dokuz paket sokuyor (96 -> 105), taze SBOM'la lisans
kapısı düşüyor. 16 Ağu 2026'da paketler kaldırıldı ve karar `app/README.md`ye
yazıldı; 23 Ağu 2026'da AYNI dokuz paket geri geldi — çünkü kararı koruyan bir
kapı yoktu, yalnız bir belge vardı.

Kapının kendisi sessizce bozulursa aynı boşluk üçüncü kez açılır. Üç davranış
ayrı ayrı kilitleniyor:

1. **Sapma varsa kırmızı** — iki yön de (ortamda fazla / SBOM'da fazla).
2. **Sapma yoksa yeşil** — yanlış alarm veren kapı okunmaz, okunmayan kapı yok
   demektir.
3. **Belirteç yoksa ATLA** — bağımlılıksız CI işinde ya da temiz bir klonda 96
   paketin yokluğu kusur değil, işin tanımıdır. Bu dal olmazsa kapı kendi
   CI'ını kırar.

`test_depo_temiz` ayrıca DEPONUN GERÇEK HÂLİNİ denetler: kapı yalnız sentetik
zeminde değil, teslim edilen ortamda da yeşil olmalı.
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from scripts import sbom_sapma as S


def _sbom_yaz(yol: Path, adlar: list[str]) -> None:
    yol.parent.mkdir(parents=True, exist_ok=True)
    yol.write_text(json.dumps({
        "bomFormat": "CycloneDX",
        "specVersion": "1.6",
        "components": [{"name": a, "version": "1.0.0", "type": "library"}
                       for a in adlar],
    }, ensure_ascii=False), encoding="utf-8")


class Zemin(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.kok = Path(self.tmp.name)
        self.sbom = self.kok / "docs" / "sbom.json"
        self.addCleanup(self.tmp.cleanup)

    def _kos(self, kurulu: set[str]) -> int:
        with mock.patch.object(S, "kurulu_paketler", return_value=kurulu):
            return S.main(["--kok", str(self.kok)])


class SapmaYakalanir(Zemin):
    def test_ortamda_fazla_paket_kirmizi(self):
        """Yaşanan olayın ta kendisi: `edge-tts` ailesi `.venv`e girdi."""
        _sbom_yaz(self.sbom, ["cyclonedx-bom", "fastapi"])
        kod = self._kos({"cyclonedx-bom", "fastapi", "edge-tts", "aiohttp"})
        self.assertEqual(kod, 1)

    def test_sbomda_fazla_paket_kirmizi(self):
        """Ters yön: ortam eksik kurulmuş ya da SBOM şişmiş."""
        _sbom_yaz(self.sbom, ["cyclonedx-bom", "fastapi", "torch"])
        self.assertEqual(self._kos({"cyclonedx-bom", "fastapi"}), 1)

    def test_sbom_dosyasi_yoksa_kirmizi(self):
        self.assertEqual(self._kos({"cyclonedx-bom"}), 1)


class SapmaYoksaYesil(Zemin):
    def test_birebir_esitlik_yesil(self):
        _sbom_yaz(self.sbom, ["cyclonedx-bom", "fastapi", "torch"])
        self.assertEqual(self._kos({"cyclonedx-bom", "fastapi", "torch"}), 0)

    def test_buyuk_kucuk_harf_duyarsiz(self):
        """SBOM `CycloneDX-BOM`, pip `cyclonedx-bom` yazabilir; sapma DEĞİL."""
        _sbom_yaz(self.sbom, ["CycloneDX-BOM", "FastAPI"])
        self.assertEqual(self._kos({"cyclonedx-bom", "fastapi"}), 0)


class BelirtecYoksaAtlar(Zemin):
    def test_bagimliliksiz_ortamda_atlar(self):
        """Bu dal olmazsa kapı kendi bağımlılıksız CI işini kırar."""
        _sbom_yaz(self.sbom, ["cyclonedx-bom", "fastapi", "torch"])
        self.assertEqual(self._kos({"pip", "setuptools"}), 0)

    def test_api_alt_kumesi_de_atlar(self):
        """CI'ın `test-with-deps` işi: `requirements-api.txt` kurulu.

        Belirteç `pydantic` olsaydı bu dal KOŞAR ve beş paketlik API
        kümesini 96 paketlik geliştirici envanteriyle karşılaştırıp CI'ı
        kırardı. `cyclonedx-bom` orada kurulu olmadığı için atlar.
        """
        _sbom_yaz(self.sbom, ["cyclonedx-bom", "fastapi", "torch", "ruff"])
        api_kumesi = {"fastapi", "uvicorn", "pydantic", "beautifulsoup4",
                      "psycopg", "psycopg-binary", "httpx2"}
        self.assertEqual(self._kos(api_kumesi), 0)

    def test_atlarken_sbom_yoklugu_bile_kirmizi_degil(self):
        """Belirteç yoksa denetim hiç başlamaz — SBOM'a bakılmaz."""
        self.assertEqual(self._kos(set()), 0)


class SurumKarsilastirilmaz(Zemin):
    def test_yalniz_ad_karsilastirilir(self):
        """Sürüm sapmasını `make sbom` + lisans kapısı zinciri yakalar."""
        _sbom_yaz(self.sbom, ["cyclonedx-bom"])
        # SBOM 1.0.0 diyor; kurulu küme sürüm taşımıyor. Sapma olmamalı.
        self.assertEqual(self._kos({"cyclonedx-bom"}), 0)


class BelirtecinKendisi(unittest.TestCase):
    """Belirteç iki yönlü doğru olmalı; bu test o iki yönü ayırır.

    İlk yazımda burada `assertIn(BELIRTEC, kurulu_paketler())` vardı ve
    CI'ı KIRDI: geliştirici `.venv`'inde doğru, CI'da yanlış bir iddiaydı
    (`cyclonedx-bom` orada kurulu değil — kurulu OLMAMASI zaten istenen
    davranış). Kapının atlaması gereken ortamda testin koşmasını şart
    koşmak, kapının kendi tasarımıyla çelişiyordu.

    Doğru değişmez ORTAMDAN BAĞIMSIZDIR: belirteç, teslim edilen bağımlılık
    beyanlarının hiçbirinde geçmemeli. Geçerse CI'ın `test-with-deps` işi
    onu kurar, kapı orada koşar ve beş paketlik API alt kümesini 96 paketlik
    geliştirici envanteriyle karşılaştırıp kırmızı yanar.
    """

    def test_belirtec_requirements_disinda(self):
        kok = _ROOT
        for ad in ("requirements.txt", "requirements-api.txt"):
            yol = kok / ad
            if not yol.exists():
                continue
            with self.subTest(dosya=ad):
                satirlar = [s.split("#")[0].strip().lower()
                            for s in yol.read_text(encoding="utf-8").splitlines()]
                self.assertNotIn(
                    S.BELIRTEC, [s.split("==")[0].split(">=")[0].split("[")[0]
                                 for s in satirlar if s],
                    f"`{S.BELIRTEC}` {ad}'te ilan edilmiş — belirteç olarak "
                    f"kullanılamaz, çünkü CI onu kurar ve kapı yanlış "
                    f"popülasyonu karşılaştırıp kırmızı yanar.")

    def test_belirtec_bos_degil(self):
        """Boş/None belirteç kapıyı her yerde atlatır — sessiz ölüm."""
        self.assertTrue(S.BELIRTEC and S.BELIRTEC.strip())


@unittest.skipUnless(S.BELIRTEC in S.kurulu_paketler(),
                     f"`{S.BELIRTEC}` yok — bu ortam docs/sbom.json'u "
                     f"üretemez, karşılaştırma kategori hatası olurdu")
class DepoGercegi(unittest.TestCase):
    """Sentetik zemin değil, TESLİM EDİLEN ortam.

    Yalnız envanteri ÜRETEBİLEN ortamda koşar (geliştirici `.venv`i).
    CI'ın iki işi de atlar; orada 96 paketin yokluğu kusur değil, işin
    tanımıdır.
    """

    def test_depo_temiz(self):
        kod = S.main([])
        self.assertEqual(
            kod, 0,
            "SBOM sapma kapısı KIRMIZI: kurulu ortam ile `docs/sbom.json` "
            "ayrışmış. `python -m scripts.sbom_sapma` çıktısına bakın — "
            "paket çalışma zamanı bağımlılığıysa requirements'a girer, "
            "tek seferlik üretim aracıysa yardımcı ortama kurulur.")


if __name__ == "__main__":
    unittest.main()
