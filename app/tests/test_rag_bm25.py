"""BM25 SIRALAR, örtüşme sayımı KAPIYI tutar — ikisi ayrı kalmalı.

İlgili: ../src/chatbot/rag.py (`KeywordRetriever._bm25_skorlari`, `MIN_OVERLAP`),
        ./test_rag_index.py (dizinli/dizinsiz eşdeğerlik — referans elle BM25),
        ./test_safety.py (KAPI 5 çekimserlik eşiği bu kapıya dayanır)

## Neden BM25 (ölçüldü 2026-08-12, 1.774 belge)

Eski skor `overlap / (sqrt(|qtok|) + 1)` idi: TF yok, IDF yok, uzunluk
normalizasyonu yok. Ölçülen sonucu, sıralayıcı korpus ortalamasının **1,7
katı** uzunlukta belge getiriyordu (935 vs 538 token) — uzun belge daha çok
DEĞİŞİK token içerdiği için ikili örtüşme şişiyor.

Aynı tokenizer'la yalnız skor formülü değiştirilerek:

    skorlayıcı        R@1     MRR    banka+tür (n=55)
    ikili örtüşme    0,766   0,871      15/55
    ikili + IDF      0,766   0,871      15/55   (IDF tek başına SIFIR etki)
    BM25             0,795   0,889      31/55

McNemar (banka+tür): b=16, c=0, p=3,1e-05 — düzelttiği 16, bozduğu 0.
BM25+/L/F varyantları birbirine karşı anlamsız (p=0,73/1/1) ve EKLENMEDİ.

## ÜRETİM YOLUNDA ölçülen etki (`eval/rag_eval.py`, demo.db, 1.782 belge)

Yukarıdaki tablo HAM sıralayıcının; üretimde kapı ve `_bankaya_suz()` var.
Üretim hattı ayrıca ölçüldü:

    ölçüt                   önce    sonra
    banka hedefleme R@1     0,500   0,800
    banka hedefleme R@5     0,600   0,800
    banka hedefleme MRR     0,533   0,800
    terim kapsama R@5       0,867   0,867   (değişmedi)
    TOPLAM R@5              0,760   0,840
    reddetme kararı         30/30   30/30   (KAPI KORUNDU)

README'nin "bilinen açıklar" bölümünde ilan edilen 0,600 açığı buydu.

## PAZARLIK DIŞI: eşik BM25 skoruna BAĞLANMAZ

`min_overlap` kapısı örtüşme SAYIMINDA kalır. Gerekçe: BM25 skoru korpus
istatistiğine bağlı SÜREKLİ bir sayıdır (aynı soru, korpus büyüyünce farklı
skor alır), "kaç soru sözcüğü bu belgede geçiyor" ise SAYILABİLİR bir
kanıttır ve çekimserlik kapısı (safety KAPI 5) ile 54 soruluk regresyon
seti o kanıta göre kalibre edilmiştir. Eşiği skora bağlamak, kapıyı
kalibrasyonsuz bırakırdı — reddetme doğruluğu 30/30'dan düşerdi ve bunu
fark etmek için ayrı bir ölçüm gerekirdi.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.chatbot import rag
from src.db.repository import Repository
from src.extraction.reconcile import build_campaign

#: Kısa ve ODAKLI belge vs uzun ve DAĞINIK belge. İkili örtüşmede uzun belge
#: kazanıyordu (daha çok değişik token içeriyor); BM25 uzunluğa göre
#: normalize ettiği için odaklı belgeyi öne almalı.
ODAKLI = "Vakıf Katılım konut finansmanı kâr payı oranı %1,89'dur."
DAGINIK = (
    "Kampanya duyurusu. " + ("Banka şubelerimiz hafta içi açıktır. " * 40)
    + "Konut finansmanı hakkında bilgi almak için şubeye başvurabilirsiniz. "
    + ("Çerez politikamız gereği tarayıcı ayarlarınızı yönetebilirsiniz. " * 40)
)


class BM25UzunBelgeSismesiniDUZELTIR(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        cls.repo = Repository(":memory:")
        cls.repo.insert_campaign(build_campaign(
            ODAKLI, bank_slug="vakif-katilim", campaign_type="Konut Finansmanı"))
        cls.repo.insert_campaign(build_campaign(
            DAGINIK, bank_slug="albaraka", campaign_type="Konut Finansmanı"))
        cls.ret = rag.KeywordRetriever(cls.repo)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.repo.close()

    def test_odakli_belge_daginik_belgeyi_YENER(self) -> None:
        sonuc = self.ret.retrieve("konut finansmanı kâr payı oranı", k=2)
        self.assertTrue(sonuc, "kapı iki belgeyi de eledi — test bir şey ölçmüyor")
        self.assertEqual(
            "vakif-katilim", sonuc[0]["bank_slug"],
            "uzun/dağınık belge hâlâ öne geçiyor — BM25 uzunluk "
            "normalizasyonu devrede değil")


class KapiORTUSMEDEKalir(unittest.TestCase):
    """Skor BM25 olsa da kabul/ret kararı örtüşme sayımına dayanır."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.repo = Repository(":memory:")
        cls.repo.insert_campaign(build_campaign(
            ODAKLI, bank_slug="vakif-katilim", campaign_type="Konut Finansmanı"))
        cls.ret = rag.KeywordRetriever(cls.repo)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.repo.close()

    def test_tek_ortusmeli_alakasiz_soru_PASAJ_DONDURMEZ(self) -> None:
        """`MIN_OVERLAP=2`nin varlık sebebi: tek sözcük kanıt değildir.

        Modül başlığındaki ölçülmüş vaka: "Helal gıda alışverişinde puan
        veren kampanya var mı?" yalnız 'kampanya' üzerinden konut finansmanı
        metnini getiriyordu — sessiz halüsinasyon.
        """
        self.assertEqual(
            [], self.ret.retrieve("helal gıda alışverişinde puan var mı", k=3),
            "tek örtüşmeli alakasız soru pasaj döndürdü — kapı BM25'e "
            "kaymış olabilir")

    def test_ortusme_alani_SONUCTA_tasiniyor(self) -> None:
        """Kapıyı geçme gerekçesi skordan okunamıyor, ayrıca taşınmalı."""
        sonuc = self.ret.retrieve("konut finansmanı kâr payı", k=1)
        self.assertTrue(sonuc)
        self.assertIn("overlap", sonuc[0],
                      "örtüşme sayısı sonuçtan düşmüş — çekimserlik "
                      "kararının dayanağı denetlenemez hâle gelir")
        self.assertGreaterEqual(sonuc[0]["overlap"], rag.MIN_OVERLAP)

    def test_esik_BM25_skoruna_BAGLANMADI(self) -> None:
        """Kapı, skor formülünden bağımsız olmalı.

        `min_overlap=0` verildiğinde (eşik kapalı) BM25 skoru düşük olan
        belgeler de dönebilmeli: kapı ile sıralama ayrı eksenlerdir.
        """
        gevsek = rag.KeywordRetriever(self.repo, min_overlap=0)
        try:
            self.assertTrue(
                gevsek.retrieve("kampanya", k=3),
                "eşik kapalıyken bile sonuç yok — kapı skora bağlanmış")
        finally:
            pass


class BM25ParametreleriILANEDILMIS(unittest.TestCase):
    """Ölçülen parametreler koddan okunabilir olmalı."""

    def test_k1_ve_b_olculen_degerlerde(self) -> None:
        self.assertEqual(1.2, rag.BM25_K1)
        self.assertEqual(0.75, rag.BM25_B)


if __name__ == "__main__":
    unittest.main()
