"""Jargon denetimi — yakalama ve muafiyet testleri.

İlgili: ../scripts/jargon_lint.py, ../src/domain/terminology.py

Buradaki iki test birbirinin karşıtı ve İKİSİ DE zorunlu:

  TestYakalar   — lint gerçek ihlali bulmalı. Her zaman geçen bir lint
                  tiyatrodur; CI'da yeşil yanar ama hiçbir şey korumaz.
  TestMuafTutar — lint kendi altyapımızı işaretlememeli. Eşleştirici sabitler
                  yasak terimi İÇERMEK ZORUNDA, çünkü onları banka metninde
                  arıyorlar; belgeler ayrımı anlatmak zorunda.
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import jargon_lint as JL


def _tara(dosyalar: dict[str, str]) -> list[JL.Bulgu]:
    with tempfile.TemporaryDirectory() as td:
        for ad, icerik in dosyalar.items():
            (Path(td) / ad).write_text(icerik, encoding="utf-8")
        return JL.kapsami_tara([td], JL.oneri_tablosu())


def _ihlaller(dosyalar: dict[str, str]) -> list[JL.Bulgu]:
    return [b for b in _tara(dosyalar) if b.ihlal]


def _muaflar(dosyalar: dict[str, str]) -> list[JL.Bulgu]:
    return [b for b in _tara(dosyalar) if not b.ihlal]


class TestYakalar(unittest.TestCase):
    def test_arayuz_etiketi(self) -> None:
        i = _ihlaller({"u.tsx": '<h2>Konut Kredisi Karşılaştırma</h2>'})
        self.assertEqual([b.terim for b in i], ["Kredisi"])

    def test_arayuz_metni_faiz(self) -> None:
        i = _ihlaller({"u.tsx": '<p>En düşük faiz oranını bulun.</p>'})
        self.assertTrue(any(b.terim == "faiz" for b in i))

    def test_chatbot_cevap_sablonu(self) -> None:
        i = _ihlaller({"r.py": 'CEVAP = "Bu bankanın kredi faizi düşüktür."'})
        self.assertEqual({b.terim for b in i}, {"kredi", "faizi"})

    def test_mevduat(self) -> None:
        i = _ihlaller({"u.tsx": '<span>Mevduat getirisi</span>'})
        self.assertEqual([b.terim for b in i], ["Mevduat"])

    def test_oneri_sozlukten_gelir(self) -> None:
        i = _ihlaller({"r.py": 'X = "faiz oranı yüksek"'})
        self.assertIn("Kâr payı", i[0].oneri)

    def test_cikis_kodu_ihlalde_1(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            (Path(td) / "u.tsx").write_text('<h2>Konut Kredisi</h2>',
                                            encoding="utf-8")
            self.assertEqual(JL.main(["--paths", td]), 1)

    def test_cikis_kodu_temizde_0(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            (Path(td) / "u.tsx").write_text('<h2>Konut Finansmanı</h2>',
                                            encoding="utf-8")
            self.assertEqual(JL.main(["--paths", td]), 0)


class TestMuafTutar(unittest.TestCase):
    def test_docstring_ayrimi_anlatabilir(self) -> None:
        """Kendi açıklamamızı sansürlemek saçma olurdu."""
        self.assertEqual(
            _ihlaller({"m.py": '"""Kâr payı faiz değildir, kredi de değil."""'}),
            [])

    def test_karsitlik_baglami(self) -> None:
        m = _muaflar({"r.py": 'A = "Kâr payı faiz değildir; murabaha kârıdır."'})
        self.assertTrue(any("karşıtlık" in (b.muafiyet or "") for b in m))

    def test_eslestirici_sabit(self) -> None:
        """Kullanıcı 'kredi' diye sorar; router yakalayamazsa soru cevapsız."""
        m = _muaflar({"r.py": '_FIELD_KEYWORDS = {"a": ["kredi tutar"]}'})
        self.assertTrue(any("eşleştirici" in (b.muafiyet or "") for b in m))

    def test_eslestirici_KURAN_fonksiyon(self) -> None:
        m = _muaflar({"s.py": 'def _build_scope_lexicon():\n'
                              '    return ("faiz", "kredi")\n'})
        self.assertEqual([b for b in _tara({"s.py": 'def _build_scope_lexicon():'
                                                    '\n    return ("faiz",)\n'})
                          if b.ihlal], [])
        self.assertTrue(m)

    def test_karsilastirma_operandi(self) -> None:
        m = _muaflar({"s.py": 'def f(stem):\n    return stem == "kredi"\n'})
        self.assertTrue(any("karşılaştırma" in (b.muafiyet or "") for b in m))

    def test_kredi_karti_gercek_urun_adi(self) -> None:
        """Katılım bankaları da 'kredi kartı' der; körlemesine değiştirmek
        veriyi bozar (safety.py::_SOFT_EXCEPTION_RE ile aynı gerekçe)."""
        self.assertEqual(_ihlaller({"u.tsx": '<p>Kredi kartınızla alışveriş</p>'}),
                         [])

    def test_faizsiz_dogru_terimdir(self) -> None:
        self.assertEqual(_ihlaller({"u.tsx": '<p>Faizsiz finansman</p>'}), [])

    def test_url_deseni(self) -> None:
        self.assertEqual(
            _ihlaller({"s.py": 'YOL = "/bireysel/kredi/konut-finansmani"'}), [])

    def test_pragma_gerekceli_kacis(self) -> None:
        m = _muaflar({"s.py": 'A = "faiz"  # jargon-lint: ok — şartname alıntısı'})
        self.assertTrue(any("pragma" in (b.muafiyet or "") for b in m))

    def test_kredibilite_yanlis_pozitif_degil(self) -> None:
        self.assertEqual(_ihlaller({"s.py": 'A = "kredibilite notu"'}), [])


class TestGercekRepo(unittest.TestCase):
    def test_varsayilan_kapsam_TEMIZ(self) -> None:
        """CI kapısı: kapsam bugün temiz, öyle kalmalı."""
        kok = Path(__file__).resolve().parents[1]
        yollar = [str(kok / p) for p in JL.VARSAYILAN_KAPSAM
                  if (kok / p).exists()]
        ihl = [b for b in JL.kapsami_tara(yollar, JL.oneri_tablosu()) if b.ihlal]
        self.assertEqual(ihl, [], f"{len(ihl)} jargon ihlali")

    def test_birincil_oneri_urun_dilidir(self) -> None:
        """Sözlük tek başına yetmiyor: `degildir` içinde birebir 'kredi' geçen
        ALTI girdi var ve aralarında türetilebilir bir üstünlük sırası yok.
        Alfabetik seçim "Kâr/zarar ortaklığı yatırımı" öneriyordu."""
        t = JL.oneri_tablosu()
        self.assertEqual(t["faiz"][0], "Kâr payı")
        self.assertEqual(t["kredi"][0], "Finansman")
        self.assertEqual(t["mevduat"][0], "Katılma hesabı")

    def test_sozluk_adaylari_da_gosterilir(self) -> None:
        """Kullanıcı 'kredi' yerine fıkhî akit adını da diyebilmeli."""
        t = JL.oneri_tablosu()
        self.assertIn("Murabaha", t["kredi"])
        self.assertIn("Katılım fonu", t["mevduat"])


if __name__ == "__main__":
    unittest.main()
