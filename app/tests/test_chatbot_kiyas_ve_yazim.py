"""Tek bankaya sorulan soru başka bankalarla, kıyas sorusu RAG'le cevaplanmaz.

İlgili: ../src/chatbot/safety.py (`detect_banks`, yazım toleransı)
        ../src/chatbot/router.py (`_kiyas_niyeti`, `VARSAYILAN_KIYAS_ALANI`)
        ../src/chatbot/bot.py (`_KIYAS_KAPSAM_NOTU`)

## Bu testlerin varlık sebebi — İKİ ÖLÇÜLMÜŞ KUSUR (2026-08-11)

**1. Bir harflik yazım hatası süzgeci düşürüyordu.** Kullanıcı "Türkiye
**Finas** Bankası'nın konut finansmanı oranı ne?" diye sordu. Tam eşleşme
tutmadı, banka süzgeci hiç kurulmadı ve sistem DÖRT bankanın oranını birden
listeledi. Aynı soru doğru yazımla sorulduğunda yalnız Türkiye Finans
dönüyordu — süzgeç çalışıyordu, ona ulaşılamıyordu. Jüri sunumunda tek bir
tuş hatası aynı sonucu verirdi.

**2. "Hangisi daha avantajlı?" RAG'e düşüyordu.** İki banka da soruda ADIYLA
geçtiği hâlde alan çıkarılamadığı için yapısal sorgu kurulamıyordu. RAG
anahtar-kelime örtüşmesiyle Findeks kredi notu ve altın hesabı belgelerini
getirdi; LLM o alakasız bağlamdan cevap üretemeyince kendi genel bilgisinden
yazdı: *"her iki bankanın web sitelerini ziyaret edip veya şubelerine
danışmak daha uygun olacaktır"*. Kıyas verisi sistemin elindeydi.

Aynı sorunun "daha **iyi**" biçimi DOĞRU çalışıyordu (tavsiye kapısı onu
yakalıyor). Yani mekanizma kuruluydu, ona ulaşan ifade kümesi eksikti.

## Neden yazım toleransı bu kadar dar sınandı

Yanlış bankaya süzmek, süzgeçsiz kalmaktan KÖTÜDÜR: süzgeçsiz cevap fazla
bilgi verir, yanlış süzgeç yanlış bilgi verir. Bu yüzden aşağıda yakalama
testlerinden daha çok "eşleşmemeli" testi var.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.chatbot.router import VARSAYILAN_KIYAS_ALANI, route
from src.chatbot.safety import BANK_NAME_TO_SLUG, detect_banks


class TestYazimToleransi(unittest.TestCase):
    """Bir harflik hata bankayı kaybettirmemeli."""

    def test_kusurun_kendisi_Finas(self) -> None:
        self.assertEqual(
            detect_banks("Türkiye Finas Bankası'nın konut finansmanı oranı ne?"),
            ["turkiye-finans"])

    def test_diger_yazim_hatalari(self) -> None:
        for soru, bek in [
            ("Türkiye Finanss oranı", "turkiye-finans"),
            ("Albarka'nın kâr payı", "albaraka"),
            ("Zirat Katılım oranı", "ziraat-katilim"),
            ("Vakıf Katlım oranı", "vakif-katilim"),
            ("Hayat Finas oranı", "hayat-finans"),
        ]:
            with self.subTest(soru=soru):
                self.assertEqual(detect_banks(soru), [bek])

    def test_tam_eslesmeler_BOZULMADI(self) -> None:
        """Tolerans yalnız tam eşleşme yokken koşar; mevcut davranış birebir."""
        for ad, slug in BANK_NAME_TO_SLUG.items():
            with self.subTest(ad=ad):
                self.assertEqual(detect_banks(f"{ad} kâr payı oranı ne?"), [slug])

    def test_banka_gecmeyen_sorular_ESLESMEZ(self) -> None:
        """Asıl risk burada: alan sözcükleri bankaya benzemeye başlamamalı."""
        for soru in (
            "Konut finansmanı oranı en düşük hangi bankada?",
            "İhtiyaç finansmanında vade kaç ay?",
            "Finansman tutarı en yüksek hangisi?",
            "Katılım bankacılığı nedir?",
            "Taşıt finansmanı kampanyaları neler?",
            "Kâr payı oranı en düşük banka hangisi?",
            "Adet başına indirim var mı?",
            "Tam olarak ne kadar ödeyeceğim?",
            "Şirket kredisi var mı?",
            "Emlak vergisi ne kadar?",
            "Hangi bankada masrafsız finansman var?",
            "Alışveriş puanı kampanyaları",
            "Yatırım ürünü seçenekleri neler?",
        ):
            with self.subTest(soru=soru):
                self.assertEqual(detect_banks(soru), [])

    def test_kisa_adlarda_tolerans_YOK(self) -> None:
        """'adil' / 'tom' 4 harf; bir harflik hata alakasız sözcüğü bankaya çevirir."""
        self.assertEqual(detect_banks("adet katılım payı"), [])
        self.assertEqual(detect_banks("tam bank hesabı"), [])

    def test_iki_harflik_hata_AFFEDILMEZ(self) -> None:
        """Sınır 1'de kalmalı; 2'ye çıkmak yanlış eşleşmeyi ucuzlatır."""
        self.assertEqual(detect_banks("Türkiye Fnas oranı"), [])


class TestKiyasNiyeti(unittest.TestCase):
    """Kıyas sorusu yapısal sorguya gitmeli, RAG'e değil."""

    def test_kusurun_kendisi_daha_avantajli(self) -> None:
        r = route("Türkiye Finans Bankası mı daha avantajlı, Albaraka Bankası mı?")
        self.assertEqual(r.handler, "structured")
        self.assertEqual(r.field, VARSAYILAN_KIYAS_ALANI)
        self.assertEqual(sorted(r.filters["banks"]),
                         ["albaraka", "turkiye-finans"])
        self.assertTrue(r.alan_varsayildi,
                        "alan varsayıldıysa bayrak taşınmalı — cevaba kapsam "
                        "notu bu bayrakla ekleniyor")

    def test_acik_kiyas_fiili(self) -> None:
        r = route("Kuveyt Türk ile Albaraka'yı karşılaştır")
        self.assertEqual(r.handler, "structured")
        self.assertEqual(sorted(r.filters["banks"]), ["albaraka", "kuveyt-turk"])

    def test_iki_banka_iki_soru_edati(self) -> None:
        """Açık kıyas sözcüğü olmasa da "A mı B mi" bir kıyastır."""
        r = route("Kuveyt Türk mü Albaraka mı?")
        self.assertEqual(r.handler, "structured")
        self.assertEqual(sorted(r.filters["banks"]), ["albaraka", "kuveyt-turk"])

    def test_tek_edat_KIYAS_DEGIL(self) -> None:
        """"Albaraka mı kâr payı veriyor?" tek bankaya sorulmuş bir sorudur."""
        r = route("Albaraka mı en düşük kâr payını veriyor?")
        self.assertFalse(r.alan_varsayildi,
                         "alan soruda geçiyor; varsayım YAPILMAMALI")

    def test_alan_SOYLENMISSE_varsayim_yapilmaz(self) -> None:
        """Kullanıcının söylediği her zaman kazanır."""
        r = route("Kuveyt Türk ile Albaraka'nın vadesini karşılaştır")
        self.assertEqual(r.field, "vade_ay")
        self.assertFalse(r.alan_varsayildi)

    def test_kiyas_isareti_YOKSA_davranis_degismedi(self) -> None:
        """Tek bankalı, alansız bir soru hâlâ RAG'e gider (geri uyum)."""
        r = route("Albaraka Türk hakkında bilgi ver")
        self.assertEqual(r.handler, "rag")
        self.assertFalse(r.alan_varsayildi)


class TestKapsamNotu(unittest.TestCase):
    """Varsayılan alan GİZLENMEMELİ."""

    def test_not_metni_alani_ve_eksik_boyutlari_soyluyor(self) -> None:
        from src.chatbot.bot import _KIYAS_KAPSAM_NOTU

        self.assertIn("kâr payı oranı", _KIYAS_KAPSAM_NOTU)
        for boyut in ("vade", "tahsis ücreti", "masraf durumu"):
            self.assertIn(boyut, _KIYAS_KAPSAM_NOTU,
                          "not, kıyasa GİRMEYEN boyutları saymalı; saymazsa "
                          "tek boyutlu cevap tam cevap gibi okunur")


if __name__ == "__main__":
    unittest.main()
