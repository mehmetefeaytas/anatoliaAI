"""Gold bütünlük kapısının davranışı.

Çalıştır:  python -m unittest tests.test_gold_butunluk  (app/ kökünden)

## Neden bu testler

Bu kapı 20-21 Ağustos 2026'da yaşanan somut bir olaya karşı yazıldı:
`gold.round1.json.sha256` üç hakemlik commit'i boyunca tazelenmedi ve
`shasum -c` koşan biri FAILED alacak duruma geldi. Kapının kendisi
sessizce bozulursa aynı boşluk geri döner — bu yüzden iki hata biçimi
ayrı ayrı kilitleniyor:

1. **Yanlış tamam** — sapmış bir tanığa "tutuyor" demek. Kapının varlık
   sebebini ortadan kaldırır; kaybettiğimiz şey tam olarak buydu.
2. **Yanlış alarm** — sağlam bir depoda ihlal uydurmak. Her koşumda
   kırmızı yanan kapı okunmaz, okunmayan kapı da yok demektir.

Ayrıca DEPONUN GERÇEK HÂLİ denetleniyor (`test_depo_temiz`): kapı yalnız
sentetik zeminde değil, teslim edilen dosyalarda da yeşil olmalı. O test
kırmızıya dönerse tanıklardan biri yine bayatlamıştır.
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from scripts.gold_butunluk import (
    esik_denetimi,
    main,
    ozet,
    sidecar_denetimi,
    sidecar_oku,
)

GOLD_ICERIK = b'[{"id": "ornek--kampanya", "bank_slug": "ornek"}]\n'


class Zemin(unittest.TestCase):
    """Sentetik bir app/ kökü: data/gold/ + eval/esikler*.json."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.kok = Path(self.tmp.name)
        self.gold_dizin = self.kok / "data" / "gold"
        self.gold_dizin.mkdir(parents=True)
        (self.kok / "eval").mkdir()
        self.addCleanup(self.tmp.cleanup)

    def _gold_yaz(self, ad: str = "gold.test.json", icerik: bytes = GOLD_ICERIK) -> Path:
        yol = self.gold_dizin / ad
        yol.write_bytes(icerik)
        return yol

    def _sidecar_yaz(self, gold: Path, ozet_degeri: str | None = None,
                     ad: str | None = None) -> Path:
        """Tanığı yaz. `ozet_degeri`/`ad` verilirse KASTEN yanlış yazılır."""
        h = ozet_degeri if ozet_degeri is not None else ozet(gold)
        n = ad if ad is not None else gold.name
        yol = gold.with_name(gold.name + ".sha256")
        yol.write_text(f"{h}  {n}\n", encoding="utf-8")
        return yol

    def _esikler_yaz(self, bagil: str, govde: dict) -> None:
        (self.kok / bagil).write_text(
            json.dumps(govde, ensure_ascii=False, indent=2), encoding="utf-8")


class SidecarDenetimi(Zemin):
    def test_tutan_tanik_ihlal_uretmez(self):
        gold = self._gold_yaz()
        self._sidecar_yaz(gold)
        self.assertEqual(sidecar_denetimi(self.kok), [])

    def test_sapan_tanik_yakalanir(self):
        """Yaşanan olayın ta kendisi: gold değişti, tanık eski kaldı."""
        gold = self._gold_yaz()
        self._sidecar_yaz(gold)
        gold.write_bytes(GOLD_ICERIK + b'\n// hakemlik sonrasi degisiklik\n')
        ihlaller = sidecar_denetimi(self.kok)
        self.assertEqual(len(ihlaller), 1)
        self.assertIn("SAPMA", ihlaller[0])

    def test_yanlis_dosyaya_bakan_tanik_yakalanir(self):
        """Doğru hash + yanlış dosya adı = geçerli olmayan tanık."""
        gold = self._gold_yaz()
        self._sidecar_yaz(gold, ad="baska.json")
        ihlaller = sidecar_denetimi(self.kok)
        self.assertTrue(any("yanlış dosyaya bakan" in s for s in ihlaller))

    def test_bozuk_bicim_yakalanir(self):
        gold = self._gold_yaz()
        gold.with_name(gold.name + ".sha256").write_text("bozuk\n", encoding="utf-8")
        ihlaller = sidecar_denetimi(self.kok)
        self.assertTrue(any("biçim bozuk" in s for s in ihlaller))

    def test_dosyasi_olmayan_tanik_yakalanir(self):
        (self.gold_dizin / "hayalet.json.sha256").write_text(
            "0" * 64 + "  hayalet.json\n", encoding="utf-8")
        ihlaller = sidecar_denetimi(self.kok)
        self.assertTrue(any("dosya YOK" in s for s in ihlaller))

    def test_tanigi_olmayan_gold_ihlal_degildir(self):
        """Ara dosyalara tanık zorlamak gürültüdür; kapı bunu yapmaz."""
        self._gold_yaz("gold.aday.json")
        self.assertEqual(sidecar_denetimi(self.kok), [])

    def test_sidecar_oku_bosluk_ve_yildiz_toleransi(self):
        gold = self._gold_yaz()
        yol = gold.with_name(gold.name + ".sha256")
        yol.write_text(f"{ozet(gold)} *{gold.name}\n", encoding="utf-8")
        okunan = sidecar_oku(yol)
        self.assertIsNotNone(okunan)
        self.assertEqual(okunan[0], ozet(gold))


class EsikDenetimi(Zemin):
    def _iki_esik(self, kunye_v2, kunye_r1) -> Path:
        gv2 = self._gold_yaz("gold.v2.json")
        gr1 = self._gold_yaz("gold.round1.json", GOLD_ICERIK + b"round1\n")
        self._esikler_yaz("eval/esikler.json", {
            "gold": "data/gold/gold.v2.json",
            **({"gold_sha256": kunye_v2(gv2)} if kunye_v2 else {}),
        })
        self._esikler_yaz("eval/esikler-round1.json", {
            "gold": "data/gold/gold.round1.json",
            **({"gold_sha256": kunye_r1(gr1)} if kunye_r1 else {}),
        })
        return gr1

    def test_tutan_kunye_ihlal_uretmez(self):
        self._iki_esik(ozet, ozet)
        self.assertEqual(esik_denetimi(self.kok), [])

    def test_kisa_onek_kunye_kabul_edilir(self):
        """`dc0e45d8` gibi 8 haneli künye geçerli bir tanıktır."""
        self._iki_esik(lambda g: ozet(g)[:8], lambda g: ozet(g)[:8])
        self.assertEqual(esik_denetimi(self.kok), [])

    def test_eksik_kunye_ihlaldir(self):
        """esikler.json'da yaşanan durum: künye hiç yoktu."""
        self._iki_esik(None, ozet)
        ihlaller = esik_denetimi(self.kok)
        self.assertTrue(any("EKSİK" in s for s in ihlaller))

    def test_sapan_kunye_yakalanir(self):
        """esikler-round1.json'da yaşanan durum: künye eski gold'u gösteriyordu."""
        self._iki_esik(ozet, lambda g: "dc0e45d8")
        ihlaller = esik_denetimi(self.kok)
        self.assertTrue(any("SAPMIŞ" in s for s in ihlaller))

    def test_onek_kismi_eslesme_gecmez(self):
        """Doğru başlayıp yanlış devam eden künye kabul edilmez."""
        gr1 = self._iki_esik(ozet, lambda g: ozet(g)[:8] + "f" * 8)
        gercek = ozet(gr1)
        self.assertFalse(gercek.startswith(gercek[:8] + "f" * 8))
        ihlaller = esik_denetimi(self.kok)
        self.assertTrue(any("SAPMIŞ" in s for s in ihlaller))

    def test_gold_alani_yoksa_ihlaldir(self):
        self._esikler_yaz("eval/esikler.json", {"mikro_yapisal": 0.8})
        self._esikler_yaz("eval/esikler-round1.json", {"mikro_yapisal": 0.7})
        ihlaller = esik_denetimi(self.kok)
        self.assertTrue(any("`gold` alanı yok" in s for s in ihlaller))


class CikisKodu(Zemin):
    def test_ihlalde_1_temizde_0(self):
        gold = self._gold_yaz("gold.v2.json")
        self._sidecar_yaz(gold)
        gr1 = self._gold_yaz("gold.round1.json", GOLD_ICERIK + b"r1\n")
        self._esikler_yaz("eval/esikler.json", {
            "gold": "data/gold/gold.v2.json", "gold_sha256": ozet(gold)})
        self._esikler_yaz("eval/esikler-round1.json", {
            "gold": "data/gold/gold.round1.json", "gold_sha256": ozet(gr1)})
        self.assertEqual(main(["--kok", str(self.kok)]), 0)

        gold.write_bytes(b"[]\n")  # tanik artik sapiyor
        self.assertEqual(main(["--kok", str(self.kok)]), 1)


class DepoGercegi(unittest.TestCase):
    """Sentetik zemin değil, TESLİM EDİLEN dosyalar."""

    def test_depo_temiz(self):
        kod = main(["--kok", str(_ROOT)])
        self.assertEqual(
            kod, 0,
            "Gold bütünlük kapısı depoda KIRMIZI. Bir tanık ya da eşik künyesi "
            "bayatlamış; `python -m scripts.gold_butunluk` çıktısına bakın.")

    def test_olcumde_kullanilan_setlerin_tanigi_var(self):
        """gold.v2 ve gold.round1 ölçüm tabanlarıdır; tanıksız olamazlar."""
        for ad in ("gold.v2.json", "gold.round1.json"):
            with self.subTest(gold=ad):
                self.assertTrue(
                    (_ROOT / "data" / "gold" / f"{ad}.sha256").exists(),
                    f"{ad} bir ölçüm tabanı; sha256 tanığı zorunludur.")


if __name__ == "__main__":
    unittest.main()
