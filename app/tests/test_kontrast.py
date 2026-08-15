"""Kontrast kapısı — hem hesabın doğruluğu hem gerçek paletin uygunluğu.

İlgili: ../scripts/kontrast_kontrol.py, ../web/app/styles/tokens.css

Buradaki üç sınıf farklı şeyleri korur ve ÜÇÜ DE gerekli:

  TestHesap        — WCAG formülü doğru mu? Bilinen referans değerlerle
                     (siyah/beyaz = 21:1) ölçülür. Yanlış formül, her paleti
                     "temiz" gösteren sessiz bir tiyatrodur.
  TestPaletCozumu  — koyu tema açığın ÜSTÜNE yazılıyor mu? Koyu blok yalnız
                     değişen isimleri yeniden tanımlar; devralma bozulursa
                     ölçüm yanlış palet üzerinde koşar ve bunu kimse görmez.
  TestGercekPalet  — teslim edilen paletin kendisi AA'yı geçiyor mu? Kapının
                     asıl işi bu; diğer ikisi kapının kendisini denetler.
"""

from __future__ import annotations

import unittest

from scripts import kontrast_kontrol as KK
from tests._ortam_gereksinimleri import arayuz_gerekir


class TestHesap(unittest.TestCase):
    """WCAG göreli parlaklık ve kontrast formülü."""

    def test_siyah_beyaz_azami_orandir(self) -> None:
        self.assertAlmostEqual(KK.kontrast("#000000", "#ffffff"), 21.0, places=2)

    def test_ayni_renk_asgari_orandir(self) -> None:
        self.assertAlmostEqual(KK.kontrast("#3b82f6", "#3b82f6"), 1.0, places=6)

    def test_oran_simetriktir(self) -> None:
        """Hangisinin metin hangisinin zemin olduğu oranı değiştirmez."""
        self.assertAlmostEqual(
            KK.kontrast("#1d1d1f", "#fbfbfd"),
            KK.kontrast("#fbfbfd", "#1d1d1f"),
            places=9,
        )

    def test_kisa_hex_uzun_hexle_ayni(self) -> None:
        self.assertEqual(KK.hex_to_rgb("#fff"), KK.hex_to_rgb("#ffffff"))
        self.assertEqual(KK.hex_to_rgb("#08f"), (0, 136, 255))

    def test_bozuk_hex_REDDEDILIR(self) -> None:
        """Sessizce 0 döndürmek, ölçülmemiş bir paleti temiz göstermek olurdu."""
        for ham in ("#12", "#12345", "mavi", ""):
            with self.subTest(ham=ham):
                with self.assertRaises(ValueError):
                    KK.hex_to_rgb(ham)

    def test_parlaklik_sinirlari(self) -> None:
        self.assertAlmostEqual(KK.goreli_parlaklik("#000000"), 0.0, places=9)
        self.assertAlmostEqual(KK.goreli_parlaklik("#ffffff"), 1.0, places=9)

    def test_dogrusallastirma_esigi(self) -> None:
        """Çok koyu kanallar doğrusal koldan geçer (c <= 0,04045)."""
        self.assertAlmostEqual(KK._kanal_dogrusal(0.04), 0.04 / 12.92, places=9)
        self.assertGreater(KK._kanal_dogrusal(0.5), 0.5 / 12.92)


class TestPaletCozumu(unittest.TestCase):
    """Koyu tema, açık temanın üstüne yazılan bir FARKtır."""

    CSS = """
    :root {
      --bg: #ffffff;
      --fg: #111111;
      --accent: #0071e3;
      --radius-md: 12px;
      --font-sans: system-ui, sans-serif;
    }
    @media (prefers-color-scheme: dark) {
      :root {
        --bg: #000000;
      }
    }
    """

    def setUp(self) -> None:
        self.paletler = KK.paletleri_coz(self.CSS)

    def test_iki_tema_cozulur(self) -> None:
        self.assertEqual(set(self.paletler), {"açık", "koyu"})

    def test_koyu_tema_yeniden_tanimlar(self) -> None:
        self.assertEqual(self.paletler["açık"]["--bg"], "#ffffff")
        self.assertEqual(self.paletler["koyu"]["--bg"], "#000000")

    def test_koyu_tema_TANIMLAMADIGINI_devralir(self) -> None:
        """Koyu blokta `--fg` yok; açık temadan gelmeli."""
        self.assertEqual(self.paletler["koyu"]["--fg"], "#111111")

    def test_renk_olmayan_tokenlar_dislanir(self) -> None:
        """`--radius-md: 12px` bir renk değildir; kontrast listesine girmemeli."""
        for palet in self.paletler.values():
            self.assertNotIn("--radius-md", palet)
            self.assertNotIn("--font-sans", palet)

    def test_eksik_token_SESSIZ_GECMEZ(self) -> None:
        """Çift listesinde olup palette olmayan token hata vermeli."""
        with self.assertRaises(KeyError):
            KK.olc({"açık": {"--fg": "#111111"}})


@arayuz_gerekir
class TestGercekPalet(unittest.TestCase):
    """Teslim edilen `tokens.css` — asıl kapı."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.olcumler = KK.olc(
            KK.paletleri_coz(KK.TOKENS_CSS.read_text(encoding="utf-8"))
        )

    def test_token_dosyasi_var(self) -> None:
        self.assertTrue(KK.TOKENS_CSS.exists(), f"eksik: {KK.TOKENS_CSS}")

    def test_iki_tema_da_olculuyor(self) -> None:
        temalar = {o.tema for o in self.olcumler}
        self.assertEqual(temalar, {"açık", "koyu"})

    def test_her_cift_iki_temada_da_var(self) -> None:
        self.assertEqual(len(self.olcumler), len(KK.CIFTLER) * 2)

    def test_TUM_ciftler_AA_esigini_geciyor(self) -> None:
        ihlaller = [o for o in self.olcumler if not o.gecti]
        self.assertEqual(
            ihlaller,
            [],
            "AA eşiğinin altında kalan çiftler: "
            + ", ".join(
                f"{o.tema} {o.metin}/{o.zemin} = {o.oran:.2f}:1" for o in ihlaller
            ),
        )

    def test_cikis_kodu_temizde_0(self) -> None:
        self.assertEqual(KK.main([]), 0)


if __name__ == "__main__":
    unittest.main()
