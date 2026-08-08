"""CSS sınıf denetimi — hem denetçinin doğruluğu hem gerçek arayüzün durumu.

İlgili: ../scripts/css_sinif_denetimi.py, ../web/app/styles/*.css

Denetçi eskiden YOKTU ve 11 sınıf tanımsız olarak teslim edilmişti; beş bileşen
tarayıcıda stilsiz render oluyordu. Ne TypeScript ne derleme bunu yakalıyordu:
tip denetleyicisi `className` dizgesinin içine bakmaz, CSS de kimin kendisini
kullandığını bilmez.

Buradaki iki sınıf birbirinin karşıtı ve İKİSİ DE gerekli:

  TestYakalar   — denetçi gerçek bir eksiği bulmalı. Her zaman "temiz" diyen
                  bir denetçi, korumadığı hâlde koruyormuş gibi görünür.
  TestGercekArayuz — teslim edilen arayüzde tanımsız sınıf kalmamalı.
"""

from __future__ import annotations

import unittest

from scripts import css_sinif_denetimi as CSD


class TestSinifCikarimi(unittest.TestCase):
    """`className` gövdesinden sabit sınıf adları."""

    def test_duz_dizge(self) -> None:
        self.assertEqual(
            CSD.kullanilan_siniflar('<div className="card stack" />'),
            {"card", "stack"},
        )

    def test_sablon_degiskeni_ATILIR(self) -> None:
        """`${sira === 1 ? " first" : ""}` içindeki `sira` bir JS adıdır."""
        kaynak = '<span className={`rank-pill${sira === 1 ? " first" : ""}`} />'
        self.assertEqual(
            CSD.kullanilan_siniflar(kaynak),
            {"rank-pill", "first"},
            "değişken atılmalı ama ürettiği sabit parça korunmalı",
        )

    def test_cok_satirli_sablon(self) -> None:
        kaynak = '<div className={`notice\n  notice-warn`} />'
        self.assertEqual(CSD.kullanilan_siniflar(kaynak), {"notice", "notice-warn"})

    def test_classname_olmayan_dizge_sayilmaz(self) -> None:
        self.assertEqual(CSD.kullanilan_siniflar('<div title="card" />'), set())

    def test_tire_ve_alt_cizgi_gecerlidir(self) -> None:
        self.assertEqual(
            CSD.kullanilan_siniflar('<i className="badge-llm _x" />'),
            {"badge-llm", "_x"},
        )


class TestYakalar(unittest.TestCase):
    """Denetçi gerçek bir eksiği bulmalı."""

    def setUp(self) -> None:
        import tempfile
        from pathlib import Path

        self._tmp = tempfile.TemporaryDirectory()
        self.kok = Path(self._tmp.name)
        (self.kok / "styles").mkdir()
        (self.kok / "styles" / "a.css").write_text(
            ".card { color: red; }\n.stack { gap: 0; }", encoding="utf-8"
        )

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _yaz(self, icerik: str) -> None:
        (self.kok / "X.tsx").write_text(icerik, encoding="utf-8")

    def test_tanimsiz_sinif_YAKALANIR(self) -> None:
        self._yaz('<div className="card summary-box" />')
        bulgular = CSD.denetle(self.kok)
        self.assertEqual(len(bulgular), 1)
        self.assertEqual(list(bulgular.values())[0], ["summary-box"])

    def test_hepsi_tanimliysa_TEMIZ(self) -> None:
        self._yaz('<div className="card stack" />')
        self.assertEqual(CSD.denetle(self.kok), {})

    def test_birden_cok_eksik_siralı_doner(self) -> None:
        self._yaz('<div className="zeta alfa card" />')
        self.assertEqual(list(CSD.denetle(self.kok).values())[0], ["alfa", "zeta"])

    def test_kullanilmayan_CSS_sinifi_kusur_SAYILMAZ(self) -> None:
        """`.badge-ner` gibi şema için ayrılmış sınıflar bilerek duruyor."""
        self._yaz('<div className="card" />')
        self.assertEqual(CSD.denetle(self.kok), {})


class TestGercekArayuz(unittest.TestCase):
    """Teslim edilen arayüz — asıl kapı."""

    def test_stil_dizini_var(self) -> None:
        self.assertTrue(CSD.STIL_DIZINI.is_dir(), f"eksik: {CSD.STIL_DIZINI}")

    def test_TANIMSIZ_SINIF_YOK(self) -> None:
        bulgular = CSD.denetle()
        self.assertEqual(
            bulgular,
            {},
            "tanımsız sınıf → bileşen tarayıcıda stilsiz render olur: "
            + "; ".join(f"{d}: {', '.join(a)}" for d, a in bulgular.items()),
        )

    def test_cikis_kodu_temizde_0(self) -> None:
        self.assertEqual(CSD.main([]), 0)


if __name__ == "__main__":
    unittest.main()
