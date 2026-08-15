"""Lisans kapısı testleri — hem kapının doğruluğu hem deponun gerçek durumu.

İlgili: ../scripts/lisans_kapisi.py, ../config/lisans_istisnalari.yaml,
../docs/sbom.json, ../docs/LISANSLAR.md

Bir lisans kapısı, yanlış "GEÇTİ" derse korumadığı hâlde koruyormuş gibi
görünür — `css_sinif_denetimi` denetçisiyle aynı tuzak. Bu yüzden testler iki
yönde de bastırıyor:

  TestDusurur   — kapı GERÇEK bir ihlali yakalamalı. Her zaman "temiz" diyen
                  kapı, hiç olmamasından daha kötüdür: yanlış güven verir.
  TestGecirir   — kapı meşru paketi düşürmemeli. Her şeye "düştü" diyen kapı
                  ilk haftada devre dışı bırakılır.

Ayrıca `TestGercekDepo`, teslim edilen deponun BUGÜNKÜ durumunu ölçüyor:
`docs/sbom.json` gerçekten var mı, kapı gerçekten geçiyor mu.

## Regresyon testi olarak yazılanlar

`test_kucuk_harf_or_operator_SAYILMAZ` bir kurgu değil, yaşanmış bir kusurun
kaydıdır. Kapı ilk yazıldığında AND/OR ayrımı harf duyarsızdı ve
"GNU Lesser General Public License v2 or later" dizgesindeki " or " bir SPDX
OR operatörü sanılıyordu. İfade ikiye bölünüyor, OR semantiği "en iyi dalı"
seçtiği için masum görünen ikinci dal kazanıyordu — yani kapı bir LGPL paketini
GEÇİRİYORDU. Tam olarak engellemek için var olduğu şeyi yapıyordu.
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts import lisans_kapisi as LK

KOK = Path(__file__).resolve().parent.parent


def _paket(ad: str, lisans: str, surum: str = "1.0") -> LK.Paket:
    return LK.Paket(ad=ad, surum=surum, lisans=lisans)


# =============================================================================
# Lisans ifadesi çözümleme
# =============================================================================
class TestIfadeHukmu(unittest.TestCase):
    """Tek ve bileşik lisans ifadelerinin hükmü."""

    def test_izinli_temel_lisanslar(self) -> None:
        for ifade in ("MIT", "Apache-2.0", "BSD-3-Clause", "ISC", "MPL-2.0"):
            with self.subTest(ifade=ifade):
                self.assertEqual(LK.ifade_hukmu(ifade), LK.IZINLI)

    def test_yazim_varyantlari_ayni_hukmu_alir(self) -> None:
        """"MIT" ve "MIT License" aynı lisanstır."""
        for ifade in (
            "MIT License",
            "Apache Software License",
            "BSD License",
            "ISC License (ISCL)",
            "Mozilla Public License 2.0 (MPL 2.0)",
            "Python Software Foundation License",
        ):
            with self.subTest(ifade=ifade):
                self.assertEqual(LK.ifade_hukmu(ifade), LK.IZINLI)

    def test_pypi_classifier_oneki_ayiklanir(self) -> None:
        """CycloneDX classifier metnini olduğu gibi taşır; önek anlam taşımaz."""
        self.assertEqual(
            LK.ifade_hukmu("License :: OSI Approved :: Apache Software License"),
            LK.IZINLI,
        )

    def test_gpl_ailesi_YASAK(self) -> None:
        for ifade in (
            "GPL-3.0",
            "GPL-2.0-only",
            "LGPL-3.0-only",
            "AGPL-3.0",
            "GNU General Public License v3",
            "GNU Lesser General Public License v2 or later (LGPLv2+)",
            "License :: OSI Approved :: GNU Affero General Public License v3",
        ):
            with self.subTest(ifade=ifade):
                self.assertEqual(LK.ifade_hukmu(ifade), LK.YASAK)

    def test_bos_ve_unknown_BILINMIYOR(self) -> None:
        for ifade in ("", "   ", "UNKNOWN", "unknown", "None", "n/a"):
            with self.subTest(ifade=repr(ifade)):
                self.assertEqual(LK.ifade_hukmu(ifade), LK.BILINMIYOR)

    def test_taninmayan_lisans_LISTEDE_YOK(self) -> None:
        """Tanımadığımızı 'herhalde izinlidir' diye geçirmiyoruz."""
        self.assertEqual(LK.ifade_hukmu("BSL-1.0"), LK.LISTEDE_YOK)
        self.assertEqual(LK.ifade_hukmu("0BSD"), LK.LISTEDE_YOK)

    def test_OR_en_iyi_dali_secer(self) -> None:
        """Seçim bizdeyse izin verici dalı seçeriz."""
        self.assertEqual(LK.ifade_hukmu("Apache-2.0 OR BSD-2-Clause"), LK.IZINLI)
        self.assertEqual(LK.ifade_hukmu("GPL-3.0 OR MIT"), LK.IZINLI)

    def test_AND_en_kotu_dali_secer(self) -> None:
        """Hepsi birden bağlıyorsa en kısıtlayıcı olan hükmü verir."""
        self.assertEqual(LK.ifade_hukmu("MPL-2.0 AND MIT"), LK.IZINLI)
        self.assertEqual(LK.ifade_hukmu("MIT AND GPL-3.0"), LK.YASAK)
        self.assertEqual(LK.ifade_hukmu("Apache-2.0 AND CNRI-Python"), LK.LISTEDE_YOK)

    def test_noktali_virgul_OR_sayilir(self) -> None:
        """`pip-licenses` çoklu classifier'ı `;` ile ayırır."""
        self.assertEqual(
            LK.ifade_hukmu("Apache Software License; BSD License"), LK.IZINLI
        )

    def test_WITH_eki_atilir(self) -> None:
        """İstisna eki hakları genişletir; lisansı sıkılaştırmaz."""
        self.assertEqual(
            LK.ifade_hukmu("Apache-2.0 WITH LLVM-exception"), LK.IZINLI
        )

    def test_kucuk_harf_or_operator_SAYILMAZ(self) -> None:
        """REGRESYON: " or later" bir SPDX operatörü DEĞİLDİR.

        Harf duyarsız bölme, LGPL dizgesini ikiye ayırıp masum dalı seçiyor ve
        copyleft paketi kapıdan geçiriyordu. SPDX operatörleri büyük harftir.
        """
        self.assertEqual(
            LK.ifade_hukmu("GNU Lesser General Public License v2 or later (LGPLv2+)"),
            LK.YASAK,
        )

    def test_kucuk_harf_and_operator_SAYILMAZ(self) -> None:
        """Aynı tuzağın AND tarafı."""
        self.assertEqual(
            LK.ifade_hukmu("GNU General Public License and friends"), LK.YASAK
        )

    def test_GPL_baska_sozcugun_icinde_yakalanmaz(self) -> None:
        """Yanlış pozitif olmamalı: kapı gürültü üretirse kimse okumaz."""
        self.assertEqual(LK.ifade_hukmu("MIT"), LK.IZINLI)
        self.assertNotEqual(LK.ifade_hukmu("Apache-2.0"), LK.YASAK)


# =============================================================================
# Girdi okuma
# =============================================================================
class TestPaketleriOku(unittest.TestCase):
    """Hem CycloneDX hem pip-licenses biçimi okunabilmeli."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.dizin = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _yaz(self, ad: str, veri: object) -> Path:
        y = self.dizin / ad
        y.write_text(json.dumps(veri), encoding="utf-8")
        return y

    def test_pip_licenses_json_okunur(self) -> None:
        y = self._yaz(
            "pl.json",
            [{"Name": "requests", "Version": "2.34.2", "License": "Apache-2.0"}],
        )
        paketler = LK.paketleri_oku(y)
        self.assertEqual(len(paketler), 1)
        self.assertEqual(paketler[0].ad, "requests")
        self.assertEqual(paketler[0].hukum, LK.IZINLI)

    def test_cyclonedx_json_okunur(self) -> None:
        y = self._yaz(
            "sbom.json",
            {
                "components": [
                    {
                        "type": "library",
                        "name": "pydantic",
                        "version": "2.6",
                        "licenses": [{"license": {"id": "MIT"}}],
                    }
                ]
            },
        )
        paketler = LK.paketleri_oku(y)
        self.assertEqual(len(paketler), 1)
        self.assertEqual(paketler[0].ad, "pydantic")
        self.assertEqual(paketler[0].hukum, LK.IZINLI)

    def test_cyclonedx_kok_bilesen_atlanir(self) -> None:
        """Uygulamanın kendisi bir bağımlılık değildir."""
        y = self._yaz(
            "sbom.json",
            {
                "components": [
                    {"type": "application", "name": "anatolia", "version": "1.0"},
                    {
                        "type": "library",
                        "name": "pyyaml",
                        "version": "6.0",
                        "licenses": [{"license": {"id": "MIT"}}],
                    },
                ]
            },
        )
        paketler = LK.paketleri_oku(y)
        self.assertEqual([p.ad for p in paketler], ["pyyaml"])

    def test_cyclonedx_ayni_lisansin_iki_yazimi_BIRLESTIRILIR(self) -> None:
        """`cyclonedx-py` SPDX kimliğini ve classifier'ı ikisini de yazar.

        Körü körüne AND ile birleştirmek tek lisanslı paketi bileşik gösterir.
        """
        y = self._yaz(
            "sbom.json",
            {
                "components": [
                    {
                        "type": "library",
                        "name": "requests",
                        "version": "2.34.2",
                        "licenses": [
                            {"license": {"id": "Apache-2.0"}},
                            {
                                "license": {
                                    "name": "License :: OSI Approved :: "
                                    "Apache Software License"
                                }
                            },
                        ],
                    }
                ]
            },
        )
        paketler = LK.paketleri_oku(y)
        self.assertEqual(paketler[0].lisans, "Apache-2.0")
        self.assertEqual(paketler[0].hukum, LK.IZINLI)

    def test_lisansi_olmayan_bilesen_BOS_doner(self) -> None:
        y = self._yaz(
            "sbom.json",
            {"components": [{"type": "library", "name": "x", "version": "1"}]},
        )
        paketler = LK.paketleri_oku(y)
        self.assertEqual(paketler[0].lisans, "")
        self.assertEqual(paketler[0].hukum, LK.BILINMIYOR)

    def test_taninmayan_bicim_HATA(self) -> None:
        y = self._yaz("garip.json", {"foo": "bar"})
        with self.assertRaises(ValueError):
            LK.paketleri_oku(y)


# =============================================================================
# İstisnalar
# =============================================================================
class TestIstisnalar(unittest.TestCase):
    """Gerekçe zorunluluğu — muafiyetin bedeli onu savunmaktır."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.dizin = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _yaml(self, icerik: str) -> Path:
        y = self.dizin / "ist.yaml"
        y.write_text(icerik, encoding="utf-8")
        return y

    def test_gerekceli_istisna_YUKLENIR(self) -> None:
        y = self._yaml(
            "istisnalar:\n"
            "  - paket: psycopg\n"
            "    gerekce: Dinamik bağlı LGPL istemci kütüphanesi; statik "
            "linkleme yok, türev çalışma üretilmiyor.\n"
        )
        istisnalar, hatalar = LK.istisnalari_yukle(y)
        self.assertEqual(hatalar, [])
        self.assertIn("psycopg", istisnalar)

    def test_GEREKCESIZ_istisna_REDDEDILIR(self) -> None:
        y = self._yaml("istisnalar:\n  - paket: psycopg\n")
        istisnalar, hatalar = LK.istisnalari_yukle(y)
        self.assertEqual(istisnalar, {})
        self.assertTrue(hatalar)
        self.assertIn("GEREKÇE YOK", " ".join(hatalar))

    def test_BOS_gerekce_REDDEDILIR(self) -> None:
        y = self._yaml('istisnalar:\n  - paket: psycopg\n    gerekce: ""\n')
        istisnalar, hatalar = LK.istisnalari_yukle(y)
        self.assertEqual(istisnalar, {})
        self.assertTrue(hatalar)

    def test_COK_KISA_gerekce_REDDEDILIR(self) -> None:
        """"ok" bir gerekçe değildir; dolgu metin muafiyet satın alamaz."""
        y = self._yaml("istisnalar:\n  - paket: psycopg\n    gerekce: gerekli\n")
        istisnalar, hatalar = LK.istisnalari_yukle(y)
        self.assertEqual(istisnalar, {})
        self.assertIn("çok kısa", " ".join(hatalar))

    def test_paketsiz_kayit_REDDEDILIR(self) -> None:
        y = self._yaml(
            "istisnalar:\n  - gerekce: Bu gerekçe yeterince uzun ama paketi yok.\n"
        )
        istisnalar, hatalar = LK.istisnalari_yukle(y)
        self.assertEqual(istisnalar, {})
        self.assertTrue(hatalar)

    def test_olmayan_dosya_SESSIZ_bos_doner(self) -> None:
        """İstisna dosyası olmaması bir kusur değil; hiç muafiyet yok demektir."""
        istisnalar, hatalar = LK.istisnalari_yukle(self.dizin / "yok.yaml")
        self.assertEqual(istisnalar, {})
        self.assertEqual(hatalar, [])

    def test_json_bicimi_de_okunur(self) -> None:
        y = self.dizin / "ist.json"
        y.write_text(
            json.dumps(
                {
                    "istisnalar": [
                        {
                            "paket": "chardet",
                            "gerekce": "Yalnızca denetim aracının bağımlılığı; "
                            "teslim edilen imajda yok.",
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )
        istisnalar, hatalar = LK.istisnalari_yukle(y)
        self.assertEqual(hatalar, [])
        self.assertIn("chardet", istisnalar)


# =============================================================================
# Kapının hükmü
# =============================================================================
class TestDusurur(unittest.TestCase):
    """Kapı gerçek ihlali YAKALAMALI."""

    def test_GPL_paket_kapiyi_dusurur(self) -> None:
        rapor = LK.denetle([_paket("bir-sey", "GPL-3.0")], {})
        self.assertFalse(rapor.temiz_mi)
        self.assertEqual(rapor.cikis_kodu, 1)
        self.assertEqual([p.ad for p in rapor.yasak], ["bir-sey"])

    def test_LGPL_paket_kapiyi_dusurur(self) -> None:
        rapor = LK.denetle([_paket("psycopg", "LGPL-3.0-only")], {})
        self.assertFalse(rapor.temiz_mi)
        self.assertEqual([p.ad for p in rapor.yasak], ["psycopg"])

    def test_AGPL_paket_kapiyi_dusurur(self) -> None:
        rapor = LK.denetle([_paket("pymupdf", "AGPL-3.0")], {})
        self.assertEqual([p.ad for p in rapor.yasak], ["pymupdf"])

    def test_UNKNOWN_kapiyi_dusurur_ve_AYRI_listeye_duser(self) -> None:
        """Bilinmeyen lisans sessiz geçmez ama 'yasak' da denmez."""
        rapor = LK.denetle([_paket("gizemli", "UNKNOWN")], {})
        self.assertFalse(rapor.temiz_mi)
        self.assertEqual(rapor.cikis_kodu, 1)
        self.assertEqual([p.ad for p in rapor.bilinmiyor], ["gizemli"])
        self.assertEqual(rapor.yasak, [])

    def test_BOS_lisans_kapiyi_dusurur(self) -> None:
        rapor = LK.denetle([_paket("bossuz", "")], {})
        self.assertEqual([p.ad for p in rapor.bilinmiyor], ["bossuz"])
        self.assertEqual(rapor.cikis_kodu, 1)

    def test_izin_listesi_disi_kapiyi_dusurur(self) -> None:
        rapor = LK.denetle([_paket("boostlu", "BSL-1.0")], {})
        self.assertFalse(rapor.temiz_mi)
        self.assertEqual([p.ad for p in rapor.listede_yok], ["boostlu"])

    def test_GEREKCESIZ_istisna_kapiyi_dusurur(self) -> None:
        """Kusurlu istisna dosyası, tek başına kapıyı düşürmeye yeter."""
        rapor = LK.denetle([_paket("temiz", "MIT")], {})
        rapor.istisna_hatalari = ["gerekçesiz istisna"]
        self.assertFalse(rapor.temiz_mi)
        self.assertEqual(rapor.cikis_kodu, 1)

    def test_ESKIMIS_istisna_kapiyi_dusurur(self) -> None:
        """İstisnadaki lisans, kurulu lisansla uyuşmuyorsa gerekçe eskimiştir."""
        istisnalar = {
            "psycopg": LK.Istisna(
                paket="psycopg",
                gerekce="Dinamik bağlı istemci; statik linkleme yok, sorun değil.",
                lisans="LGPL-3.0-only",
            )
        }
        rapor = LK.denetle([_paket("psycopg", "GPL-3.0")], istisnalar)
        self.assertFalse(rapor.temiz_mi)
        self.assertIn("eskimiş", " ".join(rapor.istisna_hatalari))


class TestGecirir(unittest.TestCase):
    """Kapı meşru paketi DÜŞÜRMEMELİ."""

    def test_izinli_paketler_gecer(self) -> None:
        paketler = [
            _paket("requests", "Apache-2.0"),
            _paket("pydantic", "MIT"),
            _paket("uvicorn", "BSD-3-Clause"),
            _paket("certifi", "MPL-2.0"),
        ]
        rapor = LK.denetle(paketler, {})
        self.assertTrue(rapor.temiz_mi)
        self.assertEqual(rapor.cikis_kodu, 0)
        self.assertEqual(len(rapor.izinli), 4)

    def test_GEREKCELI_istisna_GPL_paketi_gecirir(self) -> None:
        istisnalar = {
            "psycopg": LK.Istisna(
                paket="psycopg",
                gerekce="LGPL istemci kütüphanesi dinamik bağlanıyor; teslim "
                "edilen üründe statik linkleme yok.",
            )
        }
        rapor = LK.denetle([_paket("psycopg", "LGPL-3.0-only")], istisnalar)
        self.assertTrue(rapor.temiz_mi)
        self.assertEqual(rapor.cikis_kodu, 0)
        self.assertEqual(rapor.yasak, [])
        self.assertEqual([p.ad for p, _ in rapor.muaf], ["psycopg"])

    def test_GEREKCELI_istisna_UNKNOWN_paketi_gecirir(self) -> None:
        istisnalar = {
            "transformers": LK.Istisna(
                paket="transformers",
                gerekce="METADATA elle okundu: 'License: Apache 2.0 License'; "
                "aracın okuyamaması lisanssızlık değildir.",
            )
        }
        rapor = LK.denetle([_paket("transformers", "")], istisnalar)
        self.assertTrue(rapor.temiz_mi)
        self.assertEqual([p.ad for p, _ in rapor.muaf], ["transformers"])

    def test_istisna_buyuk_kucuk_harf_duyarsiz(self) -> None:
        istisnalar = {
            "psycopg-binary": LK.Istisna(
                paket="psycopg-binary",
                gerekce="psycopg ile aynı gerekçe; yalnızca dağıtım biçimi farklı.",
            )
        }
        rapor = LK.denetle([_paket("psycopg-BINARY", "LGPL-3.0-only")], istisnalar)
        self.assertTrue(rapor.temiz_mi)

    def test_KULLANILMAYAN_istisna_kapiyi_dusurmez_ama_raporlanir(self) -> None:
        """Ölü muafiyet bir kusur değil ama görünmez de olmamalı."""
        istisnalar = {
            "artik-yok": LK.Istisna(
                paket="artik-yok",
                gerekce="Bir zamanlar gerekliydi; paket artık kurulu değil.",
            )
        }
        rapor = LK.denetle([_paket("requests", "Apache-2.0")], istisnalar)
        self.assertTrue(rapor.temiz_mi)
        self.assertEqual(rapor.kullanilmayan_istisnalar, ["artik-yok"])


# =============================================================================
# Gerçek deponun bugünkü durumu
# =============================================================================
class TestGercekDepo(unittest.TestCase):
    """Üretilen artefaktlar var mı ve kapı bugün geçiyor mu."""

    def test_sbom_dosyasi_VAR(self) -> None:
        self.assertTrue(
            (KOK / "docs" / "sbom.json").exists(),
            "docs/sbom.json yok — `make sbom` koşulmamış.",
        )

    def test_lisanslar_belgesi_VAR(self) -> None:
        self.assertTrue(
            (KOK / "docs" / "LISANSLAR.md").exists(),
            "docs/LISANSLAR.md yok — `make lisanslar` koşulmamış.",
        )

    def test_sbom_gecerli_cyclonedx(self) -> None:
        veri = json.loads((KOK / "docs" / "sbom.json").read_text(encoding="utf-8"))
        self.assertEqual(veri.get("bomFormat"), "CycloneDX")
        self.assertTrue(veri.get("components"))

    def test_istisna_dosyasi_KUSURSUZ(self) -> None:
        """Depodaki her istisnanın gerekçesi yazılmış olmalı."""
        _, hatalar = LK.istisnalari_yukle(KOK / "config" / "lisans_istisnalari.yaml")
        self.assertEqual(hatalar, [], f"istisna dosyası kusurlu: {hatalar}")

    def test_KAPI_BUGUN_GECIYOR(self) -> None:
        paketler = LK.paketleri_oku(KOK / "docs" / "sbom.json")
        istisnalar, hatalar = LK.istisnalari_yukle(
            KOK / "config" / "lisans_istisnalari.yaml"
        )
        rapor = LK.denetle(paketler, istisnalar)
        rapor.istisna_hatalari = hatalar + rapor.istisna_hatalari
        self.assertTrue(
            rapor.temiz_mi,
            "Lisans kapısı düştü. "
            f"yasak={[p.ad for p in rapor.yasak]} "
            f"bilinmiyor={[p.ad for p in rapor.bilinmiyor]} "
            f"listede_yok={[p.ad for p in rapor.listede_yok]} "
            f"istisna_hatalari={rapor.istisna_hatalari}",
        )

    def test_OLU_istisna_YOK(self) -> None:
        """Karşılığı kalmayan muafiyet ileride yanlışlıkla bir şeyi affeder."""
        paketler = LK.paketleri_oku(KOK / "docs" / "sbom.json")
        istisnalar, _ = LK.istisnalari_yukle(
            KOK / "config" / "lisans_istisnalari.yaml"
        )
        rapor = LK.denetle(paketler, istisnalar)
        self.assertEqual(
            rapor.kullanilmayan_istisnalar,
            [],
            "karşılığı olmayan istisna var — temizlenmeli",
        )


if __name__ == "__main__":
    unittest.main()
