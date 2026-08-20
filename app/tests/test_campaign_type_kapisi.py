"""`campaign_type` — sınıflandırıcı davranışı + ölçüm kapısı.

İlgili: ../src/extraction/ner/classifier.py (URL kovası, gölge ifadeler)
        ../eval/run_eval.py (`tur_puanla`, `esik_ihlalleri`)
        ../eval/esikler.json · ../eval/esikler-round1.json
        ../docs/rapor/campaign-type-onarimi.md
        CLAUDE.md §16 (accuracy + macro-F1), §19 (bilgi yoksa `null`)

Bu dosya jürinin canlı sistemde gördüğü hatanın DÖNMEMESİNİ korur. Korunan
üç davranış ve her birinin ölçülmüş gerekçesi:

1. **Beraberlikte `Konut Finansmanı` DÖNMEZ, `None` döner.** Eski beraberlik
   kırıcı `_ORDER` sırasına bakıyordu ve sıranın başı `Konut`tu; korpusun
   %31,5'i beraberlikle karara bağlanıyor, `Konut` etiketli 179 belgenin
   114'ü buradan geliyordu.
2. **URL yolu kararı sürüklüyor.** Aynı ürünün uzun/kısa iki kopyası farklı
   tür alıyordu — etiket ürüne değil sayfa çerçevesinin HACMİNE bağlıydı.
3. **`kredi kartı` `Finansman`a oy VERMEZ.** Bileşik ad öbeğinin anlamı
   öbeğin tamamına aittir; genel baş sözcüğün ("kredi") ayrıca genel sınıfa
   oy vermesi yapay beraberlik üretiyordu.

Ayrıca: iki eşik dosyasının da `campaign_type` satırı TAŞIDIĞI test edilir.
Ölçülmeyen alan çürür; bu alan tam olarak öyle çürüdü.
"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from eval.run_eval import Counts, TurSonuc, esik_ihlalleri, tur_puanla
from scripts.gold_schema import GoldRecord
from src.extraction.ner.classifier import RuleHintClassifier, url_turu
from src.schemas import CAMPAIGN_TYPES

KOK = Path(__file__).resolve().parents[1]


class TestBeraberlikCekimser(unittest.TestCase):
    """Eşitlikte tür UYDURULMAZ."""

    def setUp(self) -> None:
        self.clf = RuleHintClassifier()

    def test_esit_puanda_None_doner(self) -> None:
        # "konut" (Konut) ve "taşıt" (Taşıt) birer ipucu -> 1-1 beraberlik.
        tur, guven = self.clf.classify("Konut ve taşıt için avantaj")
        self.assertIsNone(tur)
        self.assertEqual(guven, 0.0)

    def test_beraberlikte_Konut_VARSAYILAN_GALIP_DEGIL(self) -> None:
        """REGRESYON: bu vaka eskiden `Konut Finansmanı` dönüyordu."""
        for metin in ("Konut ve taşıt için avantaj",
                      "ev ve araç sahipleri için puan"):
            with self.subTest(metin=metin):
                self.assertNotEqual(
                    self.clf.classify(metin)[0], "Konut Finansmanı")

    def test_ipucu_yoksa_None(self) -> None:
        self.assertEqual(self.clf.classify("Merhaba dünya"), (None, 0.0))

    def test_tek_kazanan_varsa_doner(self) -> None:
        tur, guven = self.clf.classify("Konut finansmanı kampanyası")
        self.assertEqual(tur, "Konut Finansmanı")
        self.assertGreater(guven, 0.5)


class TestUrlSinyali(unittest.TestCase):
    """URL yolu deterministik; eşleşmezse tür uydurulmaz."""

    def test_yol_turu_soyluyorsa_metne_bakilmaz(self) -> None:
        clf = RuleHintClassifier()
        # Metin tamamen ilgisiz; karar URL'den gelmeli.
        tur, guven = clf.classify(
            "Merhaba dünya",
            "https://www.kuveytturk.com.tr/kendim-icin/finansmanlar/"
            "ihtiyac-finansmanlari/egitim-finansmani")
        self.assertEqual(tur, "İhtiyaç Finansmanı")
        self.assertGreater(guven, 0.5)

    def test_ayni_urunun_iki_kopyasi_AYNI_turu_alir(self) -> None:
        """Kök neden: etiket ürüne değil çerçeve hacmine bağlıydı."""
        clf = RuleHintClassifier()
        url = ("https://www.kuveytturk.com.tr/kendim-icin/finansmanlar/"
               "ihtiyac-finansmanlari/seyahat-finansmani")
        kisa = "Seyahat finansmanı."
        uzun = ("Anasayfa Kendim İçin Konut Finansmanları Kredi Kartları "
                "Katılma Hesapları Kampanyalar " + kisa)
        self.assertEqual(clf.classify(kisa, url)[0], clf.classify(uzun, url)[0])

    def test_eslesmeyen_yol_None_doner(self) -> None:
        self.assertIsNone(url_turu("https://adilkatilim.com.tr/iletisim"))
        self.assertIsNone(url_turu(None))
        self.assertIsNone(url_turu(""))

    def test_alan_adi_karara_girmez(self) -> None:
        """Yalnız alan adından tür çıkmaz (yol boş)."""
        self.assertIsNone(url_turu("https://www.kuveytturk.com.tr/"))

    def test_hesaplama_araci_TASIT_sanilmaz(self) -> None:
        """ÖLÇÜLEN yanlış: `hesaplama-araclari` -> Konut/Taşıt oluyordu."""
        self.assertIsNone(
            url_turu("https://ornek.com.tr/hesaplama-araclari"))

    def test_sorgu_dizesi_yok_sayilir(self) -> None:
        self.assertEqual(
            url_turu("https://www.ziraatkatilim.com.tr/kart-kampanyalari/"
                     "troy-kart-yemeksepeti?IsArchived=true"), "Kart")

    def test_ozgul_kova_genel_kovadan_ONCE(self) -> None:
        """`konut-finansmani` yolunda `finansman` genel kovası KAZANMAZ."""
        self.assertEqual(
            url_turu("https://www.ziraatkatilim.com.tr/bireysel/"
                     "finansman-urunleri/konut-finansmani/kentsel-donusum"),
            "Konut Finansmanı")

    def test_puan_programi_kart_markasindan_ONCE(self) -> None:
        self.assertEqual(
            url_turu("https://www.emlakkatilim.com.tr/tr/bireysel/kampanyalar/"
                     "kampanya/paraf-ile-adv-magazalarinda-1000-tl-parafpara"),
            "Alışveriş Puanı")
        self.assertEqual(
            url_turu("https://www.emlakkatilim.com.tr/tr/bireysel/kampanyalar/"
                     "kampanya/paraf-ile-networkte-4-taksit-firsati"), "Kart")


class TestGolgeIfadeler(unittest.TestCase):
    """Bileşik öbeğin içindeki genel baş sözcük oy VERMEZ."""

    def setUp(self) -> None:
        self.clf = RuleHintClassifier()

    def test_kredi_karti_Finansmana_oy_vermez(self) -> None:
        tur, _ = self.clf.classify(
            "Kuveyt Türk bireysel kredi kartları ile 500 TL indirim fırsatı")
        self.assertEqual(tur, "Kart")

    def test_arac_kredisi_Finansmana_oy_vermez(self) -> None:
        tur, _ = self.clf.classify("Taşıt finansmanı kampanyası, araç kredisi")
        self.assertEqual(tur, "Taşıt Finansmanı")

    def test_katilma_hesabi_Finansmana_oy_vermez(self) -> None:
        tur, _ = self.clf.classify("Katılma hesabı ve altın hesabı avantajları")
        self.assertEqual(tur, "Yatırım Ürünü")


class TestTurPuanlama(unittest.TestCase):
    """`tur_puanla` muhasebesi: çekimserlik ve uydurma AYRI sayılır."""

    @staticmethod
    def _kayit(kimlik: str, metin: str, tur, url=None) -> GoldRecord:
        return GoldRecord(id=kimlik, bank_slug="x", source_url=url,
                          text=metin, campaign_type=tur)

    class _Sabit:
        """Sabit tahmin üreten sınıflandırıcı (harness'ı izole eder)."""

        def __init__(self, tahminler):
            self._t = tahminler

        def classify(self, text, source_url=None):
            p = self._t.get(text)
            return (p, 0.8 if p else 0.0)

    def test_cekimser_FN_sayilir_FP_SAYILMAZ(self) -> None:
        kayitlar = [self._kayit("a", "m1", "Kart")]
        s = tur_puanla(kayitlar, self._Sabit({"m1": None}))
        self.assertEqual(s.cekimser, 1)
        self.assertEqual(s.tablo["Kart"].fn, 1)
        self.assertEqual(sum(c.fp for c in s.tablo.values()), 0)
        self.assertEqual(s.dogruluk_etiketli, 0.0)

    def test_gold_null_iken_null_tahmin_TUMU_dogrulugunda_DOGRU(self) -> None:
        kayitlar = [self._kayit("a", "m1", None)]
        s = tur_puanla(kayitlar, self._Sabit({"m1": None}))
        self.assertEqual(s.uydurma, 0)
        self.assertEqual(s.dogru_bos, 1)
        self.assertEqual(s.dogruluk_tumu, 1.0)
        # Etiketli payda BOŞ olduğu için etiketli doğruluk 0,0 (tanımsız yerine).
        self.assertEqual(s.n_etiketli, 0)

    def test_gold_null_iken_tur_uretmek_UYDURMADIR(self) -> None:
        kayitlar = [self._kayit("a", "m1", None)]
        s = tur_puanla(kayitlar, self._Sabit({"m1": "Kart"}))
        self.assertEqual(s.uydurma, 1)
        self.assertEqual(s.uydurma_orani, 1.0)
        self.assertEqual(s.dogruluk_tumu, 0.0)

    def test_uydurma_orani_payda_yoksa_TANIMSIZ(self) -> None:
        s = tur_puanla([self._kayit("a", "m1", "Kart")],
                       self._Sabit({"m1": "Kart"}))
        self.assertIsNone(s.uydurma_orani)

    def test_taksonomi_disi_tahmin_hicbir_sinifa_FP_yazmaz(self) -> None:
        s = tur_puanla([self._kayit("a", "m1", "Kart")],
                       self._Sabit({"m1": "Uydurma Sınıf"}))
        self.assertEqual(s.tablo["Kart"].fn, 1)
        self.assertEqual(sum(c.fp for c in s.tablo.values()), 0)

    def test_tum_siniflar_tabloda(self) -> None:
        s = tur_puanla([], self._Sabit({}))
        self.assertEqual(set(s.tablo), set(CAMPAIGN_TYPES))


class TestEsikKapisi(unittest.TestCase):
    """Kapı `campaign_type`ı DENETLİYOR mu?"""

    ESIK = {"tolerans": 0.01,
            "campaign_type": {"dogruluk_etiketli": 0.70,
                              "dogruluk_tumu": 0.65,
                              "makro_f1": 0.60,
                              "uydurma_orani_ust_sinir": 0.50}}

    @staticmethod
    def _tur(dogru: int, etiketli: int, bos: int = 0, uydurma: int = 0
             ) -> TurSonuc:
        return TurSonuc(n_toplam=etiketli + bos, n_etiketli=etiketli,
                        dogru_etiketli=dogru, n_bos=bos,
                        dogru_bos=bos - uydurma, uydurma=uydurma,
                        tablo={"Kart": Counts(tp=dogru, fn=etiketli - dogru)})

    def test_esik_ustunde_kapi_acik(self) -> None:
        self.assertEqual(
            esik_ihlalleri({}, self.ESIK, tur=self._tur(9, 10)), [])

    def test_dogruluk_dususu_kapiyi_kapatir(self) -> None:
        ihlaller = esik_ihlalleri({}, self.ESIK, tur=self._tur(4, 10))
        self.assertTrue(any("dogruluk_etiketli" in i for i in ihlaller),
                        ihlaller)

    def test_uydurma_artisi_kapiyi_kapatir(self) -> None:
        # 10 etiketli hepsi doğru + 4 gold-null'un 4'üne tür uyduruldu.
        ihlaller = esik_ihlalleri({}, self.ESIK,
                                  tur=self._tur(10, 10, bos=4, uydurma=4))
        self.assertTrue(any("uydurma" in i for i in ihlaller), ihlaller)

    def test_olcum_verilmezse_SESSIZ_gecilmez(self) -> None:
        ihlaller = esik_ihlalleri({}, self.ESIK, tur=None)
        self.assertTrue(any("campaign_type" in i for i in ihlaller), ihlaller)

    def test_esik_dosyasi_yoksa_kapi_karismaz(self) -> None:
        self.assertEqual(esik_ihlalleri({}, {}, tur=self._tur(0, 10)), [])


class TestEsikDosyalari(unittest.TestCase):
    """İki gold'un eşik dosyası da `campaign_type` satırı taşımalı."""

    DOSYALAR = ("eval/esikler.json", "eval/esikler-round1.json")

    def test_iki_dosyada_da_campaign_type_var(self) -> None:
        for ad in self.DOSYALAR:
            with self.subTest(dosya=ad):
                d = json.loads((KOK / ad).read_text(encoding="utf-8"))
                self.assertIn("campaign_type", d,
                              "ölçülmeyen alan çürür — bu alan öyle çürüdü")
                blok = d["campaign_type"]
                for anahtar in ("dogruluk_etiketli", "dogruluk_tumu",
                                "makro_f1", "uydurma_orani_ust_sinir"):
                    self.assertIn(anahtar, blok)

    def test_gerekce_yazili(self) -> None:
        """Eşik değişikliği gerekçesiz KONMAZ (bkz. dosyaların kendi kuralı)."""
        for ad in self.DOSYALAR:
            with self.subTest(dosya=ad):
                d = json.loads((KOK / ad).read_text(encoding="utf-8"))
                self.assertIn("_campaign_type_NEDEN_EKLENDI", d)


if __name__ == "__main__":
    unittest.main()
