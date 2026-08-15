"""Test özeti artefaktı — sessizce sıfır yazmaz.

İlgili: ../scripts/test_ozeti.py, ../scripts/kanit_tazeligi.py

Bu dosyanın koruduğu üç şey:

1. **ANSI renk kodu ayrıştırmayı bozmamalı.** pytest özeti
   `\\x1b[32m2873 passed\\x1b[0m` biçiminde gelir. Sayının solunda kalan `m`
   ile rakam arasında sözcük sınırı YOKTUR; `\\b(\\d+)` bu yüzden eşleşmiyordu
   ve artefakt "0 test geçti" diyordu. Hiçbir şey şikâyet etmiyordu — kanıt
   aracının en kötü hata biçimi budur.
2. **Ayrıştırılamayan çıktı sıfırla yazılmaz.** Özet satırı bulunamazsa
   betik hata verir. "0 geçti" yazmak, ölçüm yapılmadığını ölçüm gibi
   sunmaktır.
3. **Kirlilik ölçütü dar ve doğru olmalı.** Yol süzgeci depo köküne göredir;
   git yanlış dizinden koşulursa süzgeç hiçbir şeyle eşleşmez ve ağaç her
   zaman "temiz" görünür — kapı sessizce hiçbir şey denetlemez.
"""

from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import test_ozeti as T
from tests._ortam_gereksinimleri import git_gerekir

RENKLI = (
    "-- Docs: https://docs.pytest.org/\n"
    "\x1b[33m\x1b[32m2873 passed\x1b[0m, \x1b[33m\x1b[1m53 skipped\x1b[0m, "
    "\x1b[33m\x1b[1m1 warning\x1b[0m, \x1b[32m1078 subtests passed\x1b[0m"
    "\x1b[33m in 25.86s\x1b[0m\x1b[0m\n"
)


def _say(cikti: str) -> dict[str, int]:
    return {ad: int(n) for n, ad in T._OZET.findall(T._ANSI.sub("", cikti))}


class TestOzetAyristirma(unittest.TestCase):
    def test_ANSI_kodlu_ciktida_sayilar_okunur(self) -> None:
        """Ölçülmüş hata: renk kodu yüzünden her sayı 0 okunuyordu."""
        s = _say(RENKLI)
        self.assertEqual(s.get("passed"), 2873)
        self.assertEqual(s.get("skipped"), 53)

    def test_renksiz_cikti_da_okunur(self) -> None:
        s = _say("2873 passed, 53 skipped, 1 warning in 25.86s\n")
        self.assertEqual(s.get("passed"), 2873)
        self.assertEqual(s.get("skipped"), 53)

    def test_subtests_passed_ana_sayiyi_EZMEZ(self) -> None:
        """`1078 subtests passed` ayrı bir satır ögesidir, `passed` değildir."""
        self.assertEqual(_say(RENKLI).get("passed"), 2873)

    def test_basarisizlik_ve_hata_okunur(self) -> None:
        s = _say("3 failed, 2 errors, 10 passed in 1.0s")
        self.assertEqual(s.get("failed"), 3)
        self.assertEqual(s.get("errors"), 2)

    def test_sayinin_bir_kismi_kapilmaz(self) -> None:
        """`12873 passed` -> 12873; baştaki rakam kırpılmamalı."""
        self.assertEqual(_say("12873 passed").get("passed"), 12873)

    def test_toplanan_satiri(self) -> None:
        m = T._TOPLANAN.search("2926 tests collected in 3.2s")
        self.assertIsNotNone(m)
        self.assertEqual(int(m.group(1)), 2926)


class TestSessizSifirYok(unittest.TestCase):
    def test_ayristirilamayan_cikti_HATA_verir(self) -> None:
        """Sıfırlarla yazmak, ölçüm yapılmadığını ölçüm gibi sunmaktır."""
        import subprocess
        from unittest import mock

        sahte = subprocess.CompletedProcess(args=[], returncode=0,
                                            stdout="hicbir ozet yok", stderr="")
        with mock.patch.object(T.subprocess, "run", return_value=sahte), \
                self.assertRaises(RuntimeError) as ctx:
            T.kos()
        self.assertIn("ayrıştırılamadı", str(ctx.exception))


@git_gerekir
class TestUctanUca(unittest.TestCase):
    def test_kos_gercekten_sayi_uretir(self) -> None:
        """Ölçülmüş kusur: `kos()` içindeki yerel `cikti` (pytest çıktısı)
        `cikti` adlı parametreyi GÖLGELİYORDU. Sonuç: `git_durumu(cikti)`
        bir Path yerine metin alıyor ve `AttributeError` ile patlıyordu —
        ama betik arka planda koştuğu için sessiz görünüyordu.

        Doğrudan `git_durumu()` çağırmak bunu YAKALAMAZ; yalnız `kos()`
        üzerinden geçen bir test yakalar.
        """
        import subprocess
        from unittest import mock

        sahte = subprocess.CompletedProcess(
            args=[], returncode=0,
            stdout="10 passed, 2 skipped in 1.0s\n", stderr="")
        gercek = T.subprocess.run

        def _yonlendir(cmd, *a, **k):
            if cmd and cmd[0] == "git":
                return gercek(cmd, *a, **k)
            return sahte

        with mock.patch.object(T.subprocess, "run", side_effect=_yonlendir):
            ozet = T.kos()
        self.assertEqual(ozet["gecti"], 10)
        self.assertEqual(ozet["atlandi"], 2)
        self.assertEqual(ozet["toplanan"], 12)
        self.assertRegex(str(ozet["git_sha"]), r"^[0-9a-f]{40}$")


@git_gerekir
class TestKirlilikOlcutu(unittest.TestCase):
    def test_yol_suzgeci_depo_kokune_gore(self) -> None:
        """`app/...` önekli yollar `app/` içinden koşulursa hiç eşleşmez."""
        for yol in T.TEST_ETKILEYEN:
            with self.subTest(yol=yol):
                self.assertTrue(
                    yol.startswith("app/"),
                    "yol depo köküne göre olmalı; git de kökten koşulmalı")

    def test_gercek_depoda_calisiyor(self) -> None:
        sha, kirli = T.git_durumu()
        self.assertRegex(sha, r"^[0-9a-f]{40}$")
        self.assertIsInstance(kirli, bool)

    def test_ozet_ile_kapi_ayni_yol_listesini_paylasir(self) -> None:
        """İki kopya ayrışırsa artefakt 'taze' derken kapı 'bayat' der."""
        from scripts import kanit_tazeligi as K
        self.assertIs(T.TEST_ETKILEYEN, K.TEST_ETKILEYEN)


class TestDesenSaglamligi(unittest.TestCase):
    def test_ansi_deseni_tum_kodlari_siler(self) -> None:
        self.assertNotIn("\x1b", T._ANSI.sub("", RENKLI))

    def test_ozet_deseni_tek_yakalama_cifti(self) -> None:
        self.assertEqual(re.compile(T._OZET.pattern).groups, 2)


if __name__ == "__main__":
    unittest.main()
