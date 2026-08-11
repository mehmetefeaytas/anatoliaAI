"""Alfabe kapısına takılan özet için sıcaklık merdiveni.

İlgili: ../src/summarize/ozet.py (`SICAKLIK_MERDIVENI`, `ozetle`)
        ../src/extraction/llm/clients.py (`sicaklikla`)

## Bu testlerin varlık sebebi

Arayüze «AI özeti üret» düğmesi eklenince ölçüldü (2026-08-11, `data/demo.db`
kopyası, `qwen2.5:7b-instruct`): 35 özetsiz belgenin 12'si HER koşuda alfabe
kapısına takılıyordu. Kök neden model değil, tekrar denemenin kendisiydi —
`OllamaClient` sıcaklığı 0,0 ve aynı girdi aynı çıktıyı BİREBİR üretiyor.
Düğme o 12 belge için kısır bir döngüydü: bas, bekle, sonuç hep sıfır.

Merdiven eklendikten sonra aynı 12 belgenin 11'i temiz Türkçe özet üretti
(kapsam 1739 -> 1750). Testler merdivenin üç ayrılığını kapıda tutar:

1. Kapıya takılan çıktı için TIRMANIYOR ve temiz çıktıyı kabul ediyor.
2. Boş çıktı için TIRMANMIYOR — model "özetlenecek şey yok" diyorsa sıcaklığı
   yükseltmek, olmayan içeriği uydurtmaya zorlamaktır (CLAUDE.md §19).
3. Üç basamak da kirliyse özet ÜRETİLMİYOR — kapı gevşetilmedi.

Ayrıca sıcaklık değişikliği paylaşılan istemciyi DEĞİŞTİRMEMELİ: API'de aynı
nesne sohbet ve canlı çıkarım yollarında da kullanılıyor.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.extraction.llm.clients import OllamaClient
from src.summarize.ozet import (
    SEBEP_YABANCI_ALFABE,
    SICAKLIK_MERDIVENI,
    ozetle,
)

#: Gerçek kaymaların biçimi: Latin harflerin ortasına giren ideogram.
KIRLI = "Kampanya, konut finansmanı için geçerli提供的优惠活动。"
TEMIZ = "Kampanya konut finansmanı için geçerlidir ve kâr payı oranı %2,05'tir."
METIN = ("Konut Finansmanı Kampanyası. Kâr payı oranı %2,05'ten başlar. "
         "Vade 120 aya kadar uzayabilir ve tahsis ücreti alınmaz.")


class _Istemci:
    """Sıcaklığa göre farklı cevap veren sahte istemci.

    `cevaplar`: sıcaklık -> döndürülecek özet metni. `çağrılar` hangi
    sıcaklıkların gerçekten denendiğini kaydeder; testler merdivenin
    tırmandığını (ya da tırmanMADIĞINI) buradan doğrular.
    """

    def __init__(self, cevaplar: dict[float, str], kayit: list[float],
                 temperature: float = 0.0) -> None:
        self.cevaplar = cevaplar
        self.kayit = kayit
        self.temperature = temperature

    def sicaklikla(self, temperature: float) -> "_Istemci":
        return _Istemci(self.cevaplar, self.kayit, temperature)

    def generate_json(self, system: str, user: str, schema: dict) -> dict:
        self.kayit.append(self.temperature)
        return {"ozet": self.cevaplar.get(self.temperature, KIRLI)}


class _Llm:
    def __init__(self, istemci: _Istemci) -> None:
        self.available = True
        self.client = istemci


class TestMerdiven(unittest.TestCase):
    def test_kapiya_takilinca_TIRMANIYOR(self) -> None:
        kayit: list[float] = []
        llm = _Llm(_Istemci({0.0: KIRLI, 0.35: TEMIZ}, kayit))
        sonuc = ozetle(METIN, llm)
        self.assertEqual(sonuc.ozet, TEMIZ)
        self.assertEqual(kayit, [0.0, 0.35],
                         "ilk basamak 0,0 olmalı ve yalnız gerektiği kadar "
                         "tırmanmalı")

    def test_son_basamaga_kadar_tirmaniyor(self) -> None:
        kayit: list[float] = []
        llm = _Llm(_Istemci({0.0: KIRLI, 0.35: KIRLI, 0.7: TEMIZ}, kayit))
        self.assertEqual(ozetle(METIN, llm).ozet, TEMIZ)
        self.assertEqual(kayit, list(SICAKLIK_MERDIVENI))

    def test_ilk_basamakta_gecen_belge_EK_CAGRI_YAPMAZ(self) -> None:
        """Merdiven varsayılan yolu yavaşlatmamalı: 1774 belgede 3x maliyet."""
        kayit: list[float] = []
        llm = _Llm(_Istemci({0.0: TEMIZ}, kayit))
        self.assertEqual(ozetle(METIN, llm).ozet, TEMIZ)
        self.assertEqual(kayit, [0.0])

    def test_hepsi_kirliyse_ozet_URETILMEZ(self) -> None:
        """Kapı GEVŞETİLMEDİ — merdiven kirli çıktıyı kabul ettirmez."""
        kayit: list[float] = []
        llm = _Llm(_Istemci({}, kayit))          # her sıcaklıkta KIRLI
        sonuc = ozetle(METIN, llm)
        self.assertIsNone(sonuc.ozet)
        self.assertEqual(sonuc.sebep, SEBEP_YABANCI_ALFABE)
        self.assertEqual(kayit, list(SICAKLIK_MERDIVENI))

    def test_bos_cikti_TIRMANMAZ(self) -> None:
        """Model "özetlenecek şey yok" diyorsa zorlamak uydurtmaktır."""
        kayit: list[float] = []
        llm = _Llm(_Istemci({0.0: "", 0.35: TEMIZ}, kayit))
        sonuc = ozetle(METIN, llm)
        self.assertIsNone(sonuc.ozet)
        self.assertEqual(sonuc.sebep, "bos_cikti")
        self.assertEqual(kayit, [0.0],
                         "boş çıktıda sıcaklık YÜKSELTİLMEMELİ")

    def test_merdiveni_desteklemeyen_istemcide_tek_deneme(self) -> None:
        """`sicaklikla` yoksa merdiven sessizce tek basamağa iner.

        Suit boyunca onlarca sahte istemci var; merdiveni protokole zorunlu
        kılmak hepsini değiştirmeyi gerektirirdi.
        """

        class _Duz:
            temperature = 0.0

            def generate_json(self, *a, **k):
                return {"ozet": KIRLI}

        sonuc = ozetle(METIN, _Llm(_Duz()))
        self.assertIsNone(sonuc.ozet)
        self.assertEqual(sonuc.sebep, SEBEP_YABANCI_ALFABE)


class TestPaylasilanIstemciDegismiyor(unittest.TestCase):
    """Sıcaklık kopyayla değişir; ORTAK nesne olduğu gibi kalır.

    API'de bu nesne sohbet, canlı çıkarım ve özet yollarının ortağıdır. Özet
    işi sıcaklığı yerinde değiştirseydi, aynı anda koşan bir alan çıkarımı
    ölçülmemiş bir ayarla cevap alır ve hiçbir iz kalmazdı.
    """

    def test_kopya_ayri_nesne_ve_asil_DEGISMEZ(self) -> None:
        asil = OllamaClient(temperature=0.0)
        kopya = asil.sicaklikla(0.7)
        self.assertIsNot(kopya, asil)
        self.assertEqual(kopya.temperature, 0.7)
        self.assertEqual(asil.temperature, 0.0,
                         "asıl istemcinin sıcaklığı DEĞİŞMEMELİ")

    def test_kopya_ayni_model_ve_adresi_tasir(self) -> None:
        asil = OllamaClient(temperature=0.0)
        kopya = asil.sicaklikla(0.35)
        self.assertEqual(kopya.model, asil.model)
        self.assertEqual(kopya.base_url, asil.base_url)
        self.assertEqual(kopya.num_ctx, asil.num_ctx)

    def test_istek_govdesinde_yeni_sicaklik_var(self) -> None:
        """Kopyanın ayarı gerçekten isteğe giriyor mu (yoksa merdiven sahte)."""
        govde = OllamaClient(temperature=0.0).sicaklikla(0.7).build_payload(
            "sistem", "kullanıcı", {"type": "object"})
        self.assertEqual(govde["options"]["temperature"], 0.7)


if __name__ == "__main__":
    unittest.main()
