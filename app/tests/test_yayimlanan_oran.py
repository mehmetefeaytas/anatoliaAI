"""Yayımlanan finansman oranları — yükleme, sıralama, sohbet yolu.

İlgili: ../src/domain/yayimlanan_oran.py
        ../src/chatbot/finansman_orani.py
        ../src/api/routers/finansman_orani.py

## Bu kaynağın var olma sebebi

Kampanya korpusunda `kar_payi_orani` belgelerin yalnız %6,1'inde geçiyor ve bu
bir çıkarım kusuru DEĞİL — ölçüldü (2026-08-25): EVREN `llm-large` 60 aday
belgede 0, yerel qwen2.5:7b 30 belgede 0 kabul edilebilir değer üretti. Bilgi o
metinlerde yok; bankalar onu hesaplama araçlarında yayımlıyor.

## Kilitlenen kararlar

1. **Yön TERS.** Katılmada yüksek oran iyi, finansmanda düşük iyi.
2. **Banka başına tek satır.** Aynı bankanın onlarca ürünü kıyası boğardı.
3. **Tanınmayan ürün ailesi BOŞ kalır** — rastgele bir aileye koymak kıyası
   sessizce yanlış yapardı.
4. **Kampanya sorusu ÇALINMAZ.** Ödül/puan/masraf soruları yapısal sorguya ait.
"""

from __future__ import annotations

import json
import pathlib
import tempfile
import unittest

from src.chatbot.finansman_orani import finansman_cevabi, finansman_sorusu_mu
from src.domain import yayimlanan_oran as Y


def _kayit(**kw) -> dict:
    temel = {"bank_slug": "x", "kind": "finansman", "product_name": "Konut Yeni",
             "monthly_rate": 3.0, "term_months": 12, "currency": "TRY",
             "source_url": "https://ornek/oran"}
    temel.update(kw)
    return temel


KAYITLAR = (
    _kayit(bank_slug="a", product_name="Konut Finansmanı", monthly_rate=1.89),
    _kayit(bank_slug="a", product_name="Konut Finansmanı", monthly_rate=2.50,
           term_months=36),
    _kayit(bank_slug="b", product_name="KONUT FINANSMANI KAMPANYA", monthly_rate=2.89),
    _kayit(bank_slug="c", product_name="Taşıt Finansmanı", monthly_rate=3.29),
    _kayit(bank_slug="a", product_name="Tüketici İhtiyaç Finansmanı",
           monthly_rate=3.99),
    # Tanınmayan ürün: aile BOŞ kalmalı, uydurma bir aileye girmemeli.
    _kayit(bank_slug="d", product_name="Zümrüdüanka Paketi", monthly_rate=1.00),
)


class TestAile(unittest.TestCase):
    def test_farkli_yazimlar_ayni_aileye(self) -> None:
        """Bankalar aynı ürünü üç farklı biçimde yazıyor."""
        for ad in ("Konut Yeni", "KONUT FINANSMANI (0-10.000.000 TL))",
                   "Konut Finansmanı (sıfır konut)", "Konut 2.El"):
            self.assertEqual(Y.aile(ad), "Konut Finansmanı", ad)

    def test_tasit_varyantlari(self) -> None:
        for ad in ("Araç Binek 2.El", "TOGG Finansmanı", "TAŞIT FINANSMANI(1-48 AY)"):
            self.assertEqual(Y.aile(ad), "Taşıt Finansmanı", ad)

    def test_taninmayan_urun_BOS_doner(self) -> None:
        """Rastgele bir aileye koymak kıyası sessizce yanlış yapardı."""
        self.assertEqual(Y.aile("Zümrüdüanka Paketi"), "")

    def test_bos_ad_cokmez(self) -> None:
        self.assertEqual(Y.aile(""), "")


class TestSiralama(unittest.TestCase):
    def test_DUSUK_oran_once(self) -> None:
        """Finansmanda düşük oran avantajlı — katılmanın TERSİ."""
        s = Y.siralama(urun_ailesi="Konut Finansmanı", kayitlar=KAYITLAR)
        self.assertEqual([k["monthly_rate"] for k in s], [1.89, 2.89])

    def test_banka_basina_TEK_satir(self) -> None:
        """`a` bankasının iki konut kaydı var; listede bir kez görünmeli."""
        s = Y.siralama(urun_ailesi="Konut Finansmanı", kayitlar=KAYITLAR)
        self.assertEqual([k["bank_slug"] for k in s], ["a", "b"])

    def test_banka_basina_EN_DUSUK_secilir(self) -> None:
        s = Y.siralama(urun_ailesi="Konut Finansmanı", kayitlar=KAYITLAR)
        self.assertEqual(next(k for k in s if k["bank_slug"] == "a")["monthly_rate"],
                         1.89)

    def test_vade_suzgeci(self) -> None:
        s = Y.siralama(urun_ailesi="Konut Finansmanı", vade_ay=36,
                       kayitlar=KAYITLAR)
        self.assertEqual([(k["bank_slug"], k["monthly_rate"]) for k in s],
                         [("a", 2.5)])

    def test_aile_suzgeci_taninmayani_disarida_birakir(self) -> None:
        s = Y.siralama(urun_ailesi="Konut Finansmanı", kayitlar=KAYITLAR)
        self.assertNotIn("d", [k["bank_slug"] for k in s])


class TestYukleme(unittest.TestCase):
    def setUp(self) -> None:
        self._g = tempfile.TemporaryDirectory()
        self.kok = pathlib.Path(self._g.name)
        (self.kok / "banka" / "rates").mkdir(parents=True)
        self.addCleanup(self._g.cleanup)

    def _yaz(self, satirlar: list[dict]) -> None:
        (self.kok / "banka" / "rates" / "quotes.jsonl").write_text(
            "".join(json.dumps(s, ensure_ascii=False) + "\n" for s in satirlar),
            encoding="utf-8")

    def test_katilma_kayitlari_ALINMAZ(self) -> None:
        """İki ters yönlü büyüklük aynı listede durursa sıralama anlamsız olur."""
        self._yaz([_kayit(), _kayit(kind="katilma", gross_annual_rate=42.0)])
        self.assertEqual(len(Y.yukle(self.kok)), 1)

    def test_oransiz_kayit_ALINMAZ(self) -> None:
        self._yaz([_kayit(), _kayit(monthly_rate=None)])
        self.assertEqual(len(Y.yukle(self.kok)), 1)

    def test_bozuk_satir_dosyayi_DUSURMEZ(self) -> None:
        yol = self.kok / "banka" / "rates" / "quotes.jsonl"
        yol.write_text(json.dumps(_kayit()) + "\n{ bozuk\n"
                       + json.dumps(_kayit(bank_slug="y")) + "\n", encoding="utf-8")
        self.assertEqual(len(Y.yukle(self.kok)), 2)

    def test_dizin_yoksa_bos_liste(self) -> None:
        self.assertEqual(Y.yukle(self.kok / "olmayan"), ())


class TestBankaOzeti(unittest.TestCase):
    def test_kaydi_olmayan_banka_None(self) -> None:
        """`None` "veri yok" demek; boş özet döndürmek 0 oran ima ederdi."""
        self.assertIsNone(Y.banka_ozeti("yok", kayitlar=KAYITLAR))

    def test_aile_kirilimi(self) -> None:
        o = Y.banka_ozeti("a", kayitlar=KAYITLAR)
        self.assertEqual(o["kayit"], 3)
        self.assertEqual(o["en_dusuk_oran"], 1.89)
        self.assertIn("Konut Finansmanı", o["aileler"])
        self.assertIn("İhtiyaç Finansmanı", o["aileler"])


class TestSohbetYonlendirme(unittest.TestCase):
    def test_finansman_orani_sorusu_YAKALANIR(self) -> None:
        for q in ("Hangi bankada en düşük konut finansmanı kâr payı oranı var",
                  "taşıt finansmanı oranları nedir",
                  "ihtiyaç finansmanı kâr payı oranı kaç"):
            self.assertTrue(finansman_sorusu_mu(q), q)

    def test_KAMPANYA_sorusu_CALINMAZ(self) -> None:
        """Ödül/puan/indirim soruları yapısal sorguya ait."""
        for q in ("konut finansmanı kampanyasının ödül miktarı ne",
                  "taşıt finansmanında hangi banka puan veriyor",
                  "konut finansmanı kampanya süresi ne zaman bitiyor"):
            self.assertFalse(finansman_sorusu_mu(q), q)

    def test_oran_izi_YOKSA_yakalanmaz(self) -> None:
        self.assertFalse(finansman_sorusu_mu("konut finansmanı nasıl alınır"))

    def test_bos_soru(self) -> None:
        self.assertFalse(finansman_sorusu_mu(""))
        self.assertFalse(finansman_sorusu_mu(None))


class TestSohbetCevabi(unittest.TestCase):
    def setUp(self) -> None:
        self.c = finansman_cevabi(
            "Hangi bankada en düşük konut finansmanı kâr payı oranı var",
            kayitlar=KAYITLAR)

    def test_tablo_uretilir(self) -> None:
        self.assertIn("| # | Banka | Ürün | Aylık oran | Vade |", self.c)

    def test_en_dusuk_ONE_cikarilir(self) -> None:
        self.assertIn("%1.89", self.c)

    def test_YON_acikca_yazilir(self) -> None:
        """İki yüzey aynı kelimeyi kullanıyor; yön varsayıma bırakılmaz."""
        self.assertIn("düşük** oran avantajlıdır", self.c)
        self.assertIn("katılma hesabının", self.c)

    def test_KAYNAK_farki_yazilir(self) -> None:
        """Okuyucu bunun kampanya korpusundan gelmediğini bilmeli."""
        self.assertIn("kampanya metinlerinden çıkarılmadı", self.c)
        self.assertIn("%6,1", self.c)

    def test_kaynak_baglantisi_KOSULSUZ(self) -> None:
        self.assertIn("_Kaynak:_", self.c)

    def test_veri_yoksa_None(self) -> None:
        """Veri olmadan sıralama üretmek bu modülün sebebine aykırı."""
        self.assertIsNone(finansman_cevabi("konut finansmanı oranı", kayitlar=[]))

    def test_vade_tutmazsa_SOYLENIR(self) -> None:
        """Sessizce başka vadeye düşmek, sorulmayan soruyu cevaplamak olurdu."""
        c = finansman_cevabi("konut finansmanı 60 ay kâr payı oranı",
                             kayitlar=KAYITLAR)
        self.assertIsNotNone(c)
        self.assertIn("sorduğunuz vadede kayıt yok", c)


class TestGuvenlikKapisiBeyazListesi(unittest.TestCase):
    """ÖLÇÜLMÜŞ HATA: kapı kaynaklı tabloyu «bilgi verimde yok» ile değiştiriyordu."""

    def test_finansman_orani_kaynak_sayilir(self) -> None:
        kaynak = (pathlib.Path(__file__).resolve().parents[1]
                  / "src" / "chatbot" / "bot.py").read_text(encoding="utf-8")
        self.assertIn('"finansman_orani")', kaynak,
                      "handler beyaz listede değil — cevabı güvenlik kapısından "
                      "düşer (kaynağı `sources` değil, metnin İÇİNDE)")


if __name__ == "__main__":                   # pragma: no cover
    unittest.main()
