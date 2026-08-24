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

    def test_tur_kirilimi(self) -> None:
        """Alan adı `turler` — projenin kanonik terimi «kampanya türü»."""
        o = Y.banka_ozeti("a", kayitlar=KAYITLAR)
        self.assertEqual(o["kayit"], 3)
        self.assertEqual(o["en_dusuk_oran"], 1.89)
        self.assertIn("Konut Finansmanı", o["turler"])
        self.assertIn("İhtiyaç Finansmanı", o["turler"])


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


# --------------------------------------------------------------------------- #
# Yıldız cetveline giren banka-yayını satırları
# --------------------------------------------------------------------------- #

class TestYayinSatirlari(unittest.TestCase):
    """`/advantageous` girdisine eklenen (banka, tür) satırları.

    ## Niçin bu satırlar var

    Yıldız cetvelinde 81 olası (banka × tür) hücrenin yalnız **37'sinde**
    yıldız vardı; boş hücrelerin çoğu finansman aileleriydi — `kar_payi_orani`
    gereken yerler. O oran kampanya metninde YOK (EVREN 60 belgede 0 kabul)
    ama bankalar onu hesaplama araçlarında yayımlıyor. 37 → 54 oldu.

    ## Kilitlenen üç kural

    1. `campaign_id=None` ve `kaynak="banka-yayini"` — kanıt zinciri ayrı.
    2. Katılma getirisi `kar_payi_orani`ne YAZILMAZ; ters yönlü büyüklük.
    3. Tanınmayan ürün ailesi satır ÜRETMEZ.
    """

    def setUp(self) -> None:
        from src.api.routers.kiyas_toplama import yayin_satirlari
        self.satirlar = yayin_satirlari()

    def test_hepsi_banka_yayini_damgali(self) -> None:
        self.assertTrue(self.satirlar)
        self.assertEqual({s["kaynak"] for s in self.satirlar}, {"banka-yayini"})

    def test_kampanya_kimligi_YOK(self) -> None:
        """Bir kampanyaya bağlanmak, o belgenin söylemediğini ona atfetmekti."""
        self.assertTrue(all(s["campaign_id"] is None for s in self.satirlar))

    def test_kaynak_baglantisi_her_satirda(self) -> None:
        self.assertTrue(all(s.get("source_url") for s in self.satirlar))

    def test_turler_KAMPANYA_TURU_kumesinden(self) -> None:
        """Uydurma bir tür açmak kıyası sessizce bozardı."""
        from src.comparison.compare import TUR_AGIRLIKLARI
        for s in self.satirlar:
            self.assertIn(s["campaign_type"], TUR_AGIRLIKLARI, s["campaign_type"])

    def test_katilma_getirisi_AYRI_alanda(self) -> None:
        """%42'lik getiri, %2'lik finansman oranının yanında «kötü» görünürdü."""
        yatirim = [s for s in self.satirlar
                   if s["campaign_type"] == "Yatırım Ürünü"]
        self.assertTrue(yatirim)
        for s in yatirim:
            self.assertIn("katilma_getirisi", s["fields"])
            self.assertNotIn("kar_payi_orani", s["fields"])

    def test_finansman_turlerinde_kar_payi_orani_var(self) -> None:
        fin = [s for s in self.satirlar
               if s["campaign_type"] != "Yatırım Ürünü"]
        self.assertTrue(fin)
        for s in fin:
            self.assertIn("kar_payi_orani", s["fields"])
            self.assertNotIn("katilma_getirisi", s["fields"])

    def test_her_banka_turde_TEK_satir(self) -> None:
        """Aynı bankanın onlarca ürünü tek türde listeyi boğardı."""
        anahtarlar = [(s["bank"], s["campaign_type"]) for s in self.satirlar]
        self.assertEqual(len(anahtarlar), len(set(anahtarlar)))

    def test_genel_Finansman_turu_uretilir(self) -> None:
        """Ürüne bağlanmamış «Finansman» kovasında banka temsil edilmeli."""
        genel = {s["bank"] for s in self.satirlar
                 if s["campaign_type"] == "Finansman"}
        self.assertGreaterEqual(len(genel), 3)


class TestKatilmaGetirisiYonu(unittest.TestCase):
    def test_YUKSEK_iyi(self) -> None:
        from src.comparison.compare import _HIGHER_IS_BETTER, _LOWER_IS_BETTER
        self.assertIn("katilma_getirisi", _HIGHER_IS_BETTER)
        self.assertNotIn("katilma_getirisi", _LOWER_IS_BETTER)

    def test_kar_payi_orani_DUSUK_iyi(self) -> None:
        """İki alanın yönü TERS; aynı kolonda yarışmamalarının sebebi bu."""
        from src.comparison.compare import _LOWER_IS_BETTER
        self.assertIn("kar_payi_orani", _LOWER_IS_BETTER)


class TestTurAgirliklari(unittest.TestCase):
    """«Ölçülemedi» salgınının kökü: her türe AYNI beş ölçüt uygulanıyordu."""

    def test_kart_turunde_finansman_olcutleri_YOK(self) -> None:
        """Kart belgelerinin %2'sinde kâr payı, %0'ında finansman tutarı var."""
        from src.comparison.compare import tur_agirliklari
        w = tur_agirliklari("Kart")
        self.assertNotIn("kar_payi_orani", w)
        self.assertNotIn("finansman_tutari", w)

    def test_alisveris_puani_turunun_TANIMLAYICI_olcutu(self) -> None:
        """Belgelerin %97'sinde dolu ve ağırlık tablosunda HİÇ YOKTU."""
        from src.comparison.compare import tur_agirliklari
        self.assertIn("alisveris_puani", tur_agirliklari("Alışveriş Puanı"))

    def test_yatirim_urununde_katilma_getirisi_var(self) -> None:
        from src.comparison.compare import tur_agirliklari
        self.assertIn("katilma_getirisi", tur_agirliklari("Yatırım Ürünü"))

    def test_agirliklar_1_0e_NORMALLESTIRILIR(self) -> None:
        """Elle yazılan tablo zamanla kayar ve kayma eşiği sessizce oynatırdı."""
        from src.comparison.compare import TUR_AGIRLIKLARI, tur_agirliklari
        for tur in TUR_AGIRLIKLARI:
            self.assertAlmostEqual(sum(tur_agirliklari(tur).values()), 1.0,
                                   places=6, msg=tur)

    def test_taninmayan_tur_varsayilani_alir(self) -> None:
        """Yeni bir tür eklendiğinde sistem BOŞ ağırlıkla çalışmamalı."""
        from src.comparison.compare import DEFAULT_WEIGHTS, tur_agirliklari
        self.assertEqual(set(tur_agirliklari("Yepyeni Tür")), set(DEFAULT_WEIGHTS))
