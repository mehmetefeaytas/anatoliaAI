"""Alfabe kapısı — Latin dışına kayan özet KABUL EDİLMEZ, düzeltilmez.

İlgili: ../src/summarize/ozet.py, ../scripts/ozet_dil_temizligi.py

Bu dosyanın koruduğu üç ilke:

1. **Kapı çıkışta durur.** Yerel model üretimin ortasında dil değiştirebiliyor
   (ölçüldü 2026-08-11: 1751 özetin 67'si). Kirli çıktı depoya, oradan da
   "AI özeti" etiketiyle ekrana ulaşıyordu.
2. **Onarım yok.** Kaymış harfleri ayıklayıp kalanı yazmak, modelin yazmadığı
   bir metni model çıktısı gibi sunmaktır. Doğru cevap `None` + sebep.
3. **Yanlış pozitif yok.** Türkçenin gerçekten kullandığı her şey — Türkçe
   harfler, tırnak/tire çeşitleri, ₺ ve € — kapıdan geçer.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.summarize import ozet as O
from tests.test_ozet import BELGE, SahteIstemci, SahteLLM


class TestKapiReddediyor(unittest.TestCase):
    """Latin dışı tek karakter bile özeti düşürür."""

    def _sebep(self, metin: str):
        return O.ozetle(BELGE, SahteLLM(client=SahteIstemci({"ozet": metin})))

    def test_kiril_harf_kelime_ortasinda_reddedilir(self) -> None:
        """Ekranda görülen gerçek vaka: Kiril harfi Türkçe kelimenin içinde."""
        s = self._sebep("Tutar, vade ve kâr payı oranı gibi etkenlere "
                        "зависecektir.")
        self.assertIsNone(s.ozet)
        self.assertEqual(s.sebep, O.SEBEP_YABANCI_ALFABE)
        self.assertFalse(s.uretildi)

    def test_cince_ideogram_reddedilir(self) -> None:
        s = self._sebep("500 TL nakit iade提供的优惠活动")
        self.assertIsNone(s.ozet)
        self.assertEqual(s.sebep, O.SEBEP_YABANCI_ALFABE)

    def test_yalniz_cin_noktalamasi_da_reddedilir(self) -> None:
        """İdeogram olmadan yalnız `。`/`，` taşıyan iki kayıt gerçekten vardı."""
        s = self._sebep("Kampanya 31 Mart 2026 tarihine kadar geçerlidir。")
        self.assertIsNone(s.ozet)
        self.assertEqual(s.sebep, O.SEBEP_YABANCI_ALFABE)

    def test_kirli_ozet_onarilmaz_kirpilmaz(self) -> None:
        """Temiz parçayı kurtarmak = modelin yazmadığı metni ona atfetmek."""
        s = self._sebep("Kuveyt Türk müşterilerine özel 500 TL iade提供的优惠")
        self.assertIsNone(s.ozet)
        self.assertNotIn("Kuveyt", str(s.ozet))
        self.assertIsNone(s.kaynak)

    def test_kirpma_bilgisi_redde_ragmen_korunur(self) -> None:
        """Ret, girdi tanılamasını silmez — koşu raporu ikisini de sayar."""
        uzun = "Kâr payı oranı %2,05'tir. " * 800
        s = O.ozetle(uzun, SahteLLM(client=SahteIstemci({"ozet": "iade提供"})),
                     maks_karakter=500)
        self.assertEqual(s.sebep, O.SEBEP_YABANCI_ALFABE)
        self.assertTrue(s.kirpildi)
        self.assertEqual(s.girdi_karakter, 500)


class TestKapiGeciriyor(unittest.TestCase):
    """Türkçenin gerçekten kullandığı hiçbir şey elenmemeli."""

    def _ozet(self, metin: str):
        """Kaynak, özet metnini de KAPSAR — kasıtlı.

        Bu sınıfın konusu ALFABE kapısıdır. Özet örnekleri `BELGE`de geçmeyen
        sayılar taşıyor (`36 ay`, `1.500,00 ₺`) ve `ozetle()` artık bir sayı
        kapısı uyguluyor (`_sayi_ihlali`): kaynak genişletilmezse bu özetler
        alfabe kapısına hiç varmadan sayı kapısında elenir ve testin ölçtüğü
        şey sessizce değişirdi. Kaynağa özet metnini eklemek yalnız SAYI
        kapısını nötrleştirir, alfabe kapısını değil.
        """
        return O.ozetle(f"{BELGE} {metin}",
                        SahteLLM(client=SahteIstemci({"ozet": metin})))

    def test_turkce_harfler_gecer(self) -> None:
        metin = "Çğıİöşü ÂÎÛ karakterleri taşıyan özet kabul edilir."
        self.assertEqual(self._ozet(metin).ozet, metin)

    def test_para_birimi_ve_noktalama_gecer(self) -> None:
        metin = "Kâr payı oranı %2,05 — tutar 1.500,00 ₺ ya da 50 €… “koşullu”."
        self.assertEqual(self._ozet(metin).ozet, metin)
        self.assertEqual(self._ozet(metin).kaynak, O.OZET_KAYNAK_LLM)

    def test_kesme_isaretinin_iki_bicimi_de_gecer(self) -> None:
        metin = "Vade 36 ay'dan uzun; müşteri’nin talebine bağlı."
        self.assertEqual(self._ozet(metin).ozet, metin)


class TestYuklem(unittest.TestCase):
    """`alfabe_disi_karakterler` kapının hem kararı hem kanıtıdır."""

    def test_temiz_metinde_bos_liste(self) -> None:
        self.assertEqual(O.alfabe_disi_karakterler("Kâr payı %2,05 — 1.500 ₺"), [])
        self.assertTrue(O.turkce_alfabede_mi("Kâr payı %2,05 — 1.500 ₺"))

    def test_kanit_tekil_ve_sirali(self) -> None:
        self.assertEqual(O.alfabe_disi_karakterler("a提b提c的"), ["提", "的"])

    def test_emoji_de_alfabe_disidir(self) -> None:
        self.assertFalse(O.turkce_alfabede_mi("Kampanya başladı 🎉"))

    def test_bos_metin_temiz_sayilir(self) -> None:
        self.assertEqual(O.alfabe_disi_karakterler(""), [])


class TestYonerge(unittest.TestCase):
    def test_yonerge_alfabeyi_de_kisitliyor(self) -> None:
        """Kapı son savunma; yönerge ilk savunma. İkisi birden durmalı."""
        self.assertIn("Türk alfabesi dışında", O.SISTEM_PROMPT)

    def test_sebep_sabiti_kararli(self) -> None:
        """Toplu raporlar bu anahtarı sayıyor; değişirse sayım sessizce sıfırlanır."""
        self.assertEqual(O.SEBEP_YABANCI_ALFABE, "yabanci_alfabe")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
