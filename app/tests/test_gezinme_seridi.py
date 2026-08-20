"""Gezinme şeridi ölçütü — TEK doğruluk kaynağı ve ölçülmüş SINIRI.

İlgili: ../src/extraction/rules/_ortak.py (`gezinme_seridi`)
        ../src/extraction/rules/hedef_kitle.py (geriye dönük takma ad)
        ../docs/rapor/campaign-type-onarimi.md (kök neden 0)

Bu dosya iki şeyi birden korur:

1. **Ölçüt taşınırken DEĞİŞMEDİ.** Fonksiyon 2026-08-20'de
   `hedef_kitle.py`den `_ortak.py`ye taşındı ve kamuya açıldı; taşıma bir
   davranış değişikliği DEĞİLDİ ve öyle kalmalı. Aşağıdaki vakalar taşımadan
   ÖNCEKİ ölçütün vakalarıdır.
2. **Ölçütün YETMEDİĞİ yer.** Şerit noktalama taşımadığı için
   `split_sentences` onu ilk gerçek cümleye kaynatır; birleşik cümle `.`/`!`
   ile bittiği için ölçüt `False` döner. Bu bir kusur değil, ölçütün
   TANIMLANMIŞ sınırıdır — ve sınıflandırıcı girdisini bu ölçütle temizleme
   denemesinin niçin başarısız olduğunu açıklar. Sınır teste bağlanmazsa
   birileri onu tekrar keşfeder.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.extraction.rules import hedef_kitle as HK
from src.extraction.rules._ortak import gezinme_seridi
from src.extraction.rules.extract import _gezinme_seridi as EXTRACT_ALIAS
from src.preprocessing.clean import split_sentences

#: Gerçek korpustan: sayfanın başındaki menü şeridi (albaraka/kuveyt-türk
#: kalıbı). Noktalama YOK, büyük harf yoğunluğu yüksek.
MENU = ("Anasayfa Kendim İçin İçerik Finansmanlar Konut Finansmanları "
        "Kredi Kartları Kampanyalar")
CUMLE = ("Konut finansmanı, ev sahibi olmak isteyen kişilere sunulan bir "
         "üründür.")


class TestOlcut(unittest.TestCase):
    """>= 6 kelime + >= %60 büyük harf + sonda `.`/`!` YOK."""

    def test_menu_seridi_yakalanir(self) -> None:
        self.assertTrue(gezinme_seridi(MENU))

    def test_gercek_cumle_yakalanmaz(self) -> None:
        self.assertFalse(gezinme_seridi(CUMLE))

    def test_kisa_ifade_serit_sayilmaz(self) -> None:
        """< 6 kelime: başlık da olabilir, karar verilemez -> False."""
        self.assertFalse(gezinme_seridi("Konut Finansmanı Nedir"))

    def test_nokta_ile_biten_buyuk_harfli_dizi_serit_sayilmaz(self) -> None:
        """Noktalama, yazarın cümle kurduğunun kanıtıdır."""
        self.assertFalse(
            gezinme_seridi("Ali Veli Ayşe Fatma Hasan Hüseyin Mehmet."))

    def test_kucuk_harf_yogun_dizi_serit_sayilmaz(self) -> None:
        self.assertFalse(
            gezinme_seridi("anasayfa kendim için içerik finansmanlar kartlar"))

    def test_bos_girdi_patlamaz(self) -> None:
        self.assertFalse(gezinme_seridi(""))
        self.assertFalse(gezinme_seridi("   "))


class TestTekDogrulukKaynagi(unittest.TestCase):
    """Üç ad da TEK tanımı göstermeli: `_ortak.gezinme_seridi`.

    Kimlik (`is`) yerine TANIM YERİ + davranış karşılaştırılıyor. Sebep
    ölçülmüş: `tests/test_properties.py` bilinçli olarak `sys.modules`ten tüm
    `src.*` modüllerini düşürüyor (H1 katlama hatasını geri getirip
    denetleyicinin onu yakaladığını kanıtlamak için). Aynı koşumda bu dosyanın
    modül düzeyinde tuttuğu fonksiyon nesnesiyle sonradan içe aktarılan nesne
    FARKLI olur — kimlik testi orada sahte bir kırmızı verir. Korunması
    gereken şey nesne kimliği değil, ölçütün TEK yerde tanımlı olmasıdır.
    """

    def _fonksiyonlar(self):
        return {"HK._gezinme_seridi": HK._gezinme_seridi,
                "extract._gezinme_seridi": EXTRACT_ALIAS}

    def test_tanim_yeri_ortak_modul(self) -> None:
        for ad, fn in self._fonksiyonlar().items():
            with self.subTest(ad=ad):
                self.assertEqual(fn.__module__,
                                 "src.extraction.rules._ortak",
                                 "ölçüt kopyalandı — tek kaynak bozuldu")
                self.assertEqual(fn.__name__, gezinme_seridi.__name__)

    def test_davranis_birebir_ayni(self) -> None:
        ornekler = (MENU, CUMLE, "", "Konut Finansmanı Nedir",
                    "Ali Veli Ayşe Fatma Hasan Hüseyin Mehmet.")
        for ad, fn in self._fonksiyonlar().items():
            for o in ornekler:
                with self.subTest(ad=ad, metin=o[:30]):
                    self.assertEqual(fn(o), gezinme_seridi(o))


class TestOlculmusSinir(unittest.TestCase):
    """Şerit + cümle TEK parçaya kaynadığında ölçüt onu GÖREMEZ.

    Bu davranış bilerek teste bağlandı: `campaign_type` sınıflandırıcısının
    girdisini bu ölçütle temizleme hipotezi tam bu yüzden çürüdü
    (ölçüm: docs/rapor/campaign-type-onarimi.md).
    """

    def test_serit_gercek_cumleye_kaynadiginda_olcut_False_doner(self) -> None:
        birlesik = f"{MENU} {CUMLE}"
        # `split_sentences` ikisini AYIRAMIYOR: şeritte cümle sonu yok.
        parcalar = split_sentences(birlesik)
        self.assertTrue(any(MENU.split()[0] in p and CUMLE.split()[-1] in p
                            for p in parcalar),
                        "şerit ve cümle ayrı parçalara düştü — ölçüm değişti")
        # Ve birleşik parça `.` ile bittiği için şerit sayılmıyor.
        for p in parcalar:
            if MENU.split()[0] in p:
                self.assertFalse(gezinme_seridi(p))


if __name__ == "__main__":
    unittest.main()
