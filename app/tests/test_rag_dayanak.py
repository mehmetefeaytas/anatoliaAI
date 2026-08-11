"""RAG cevabı kaynağa DAYANMAK ve sorulan bankaya ait olmak zorunda.

İlgili: ../src/chatbot/rag.py (`_dayanak_kusuru`, `_bankaya_suz`)
        ../src/chatbot/dayanak.py (sayı denetimi — tek tanım)
        ../src/chatbot/structured.py (aynı banka süzgeci, yapısal yolda)

## Bu testlerin varlık sebebi — ÜÇÜ DE ÖLÇÜLDÜ (2026-08-11, `data/demo.db`)

RAG yönergesi modele zaten *"sadece verilen bağlamdan"* diyor. Beş soruluk
ölçümde model ona uymadı:

* **2/5** cevap BOŞ dizeydi ve kaynaklarla birlikte ekrana gidiyordu.
  Çekimserlik kapısı (`safety.guard_output` KAPI 5) yalnız kaynak YOKKEN
  ateşlenir; burada kaynak vardı, cevap yoktu. Kullanıcı üç kaynak satırı ve
  hiçbir cevap görüyordu.
* **1/5** cevap bağlamda geçmeyen bir sayı taşıyordu ("%50 indirim"). O
  sayının altında, onu doğrulamayan kaynaklar duruyordu.
* **Banka süzgeci hiç yoktu.** "Vakıf Katılım kart kampanyasında ne var?"
  sorusuna Kuveyt Türk'ün makine finansmanı belgesi geliyor ve ekranda
  "İlgili kampanya (Kuveyt Türk)" diye sunuluyordu. Aynı süzgeç yapısal yolda
  (`structured._apply_filters`) ZATEN vardı — iki yol aynı soruya farklı
  dürüstlük standardı uyguluyordu.

Düzeltmeden sonra aynı ölçüm: boş 0/5, uydurma sayı 0/5, yanlış banka 0/7.

Testler yerel modeli ÇAĞIRMAZ; kapıların sözleşmesini ölçer.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.chatbot import rag
from src.chatbot.dayanak import dayanaksiz_sayilar, sayilari_ayikla


class _Retriever:
    """Sabit pasaj listesi döndüren sahte getirici."""

    retriever_name = "keyword"

    def __init__(self, pasajlar: list[dict]) -> None:
        self.pasajlar = pasajlar
        self.son_k: int | None = None

    def retrieve(self, query: str, k: int = 3) -> list[dict]:
        self.son_k = k
        return self.pasajlar[:k]


class _Istemci:
    def __init__(self, cevap: str) -> None:
        self.cevap = cevap

    def generate_json(self, system: str, user: str, schema: dict) -> dict:
        return {"cevap": self.cevap}


class _Llm:
    def __init__(self, cevap: str) -> None:
        self.available = True
        self.client = _Istemci(cevap)


def _pasaj(slug: str, metin: str, cid: int = 1) -> dict:
    return {"bank": slug, "bank_slug": slug, "campaign_id": cid,
            "source_url": f"https://{slug}.test/x", "text": metin,
            "ozet": None, "score": 1.0}


class TestSayiDenetimi(unittest.TestCase):
    def test_ayiklama_TR_bicimini_koruyor(self) -> None:
        self.assertEqual(sayilari_ayikla("(%1,79)."), ["1,79"])
        self.assertEqual(sayilari_ayikla("1.500,00 TRY masraf"), ["1.500,00"])

    def test_kaynakta_olan_sayi_dayanaksiz_DEGIL(self) -> None:
        self.assertEqual(dayanaksiz_sayilar("oran %1,89", "kâr payı %1,89"), [])

    def test_kaynakta_olmayan_sayi_YAKALANIR(self) -> None:
        self.assertEqual(dayanaksiz_sayilar("%50 indirim", "kart kampanyası"),
                         ["50"])

    def test_tekrar_eden_sayi_BIR_KEZ_raporlanir(self) -> None:
        self.assertEqual(dayanaksiz_sayilar("50 ve yine 50", "metin"), ["50"])


class TestDayanakKapisi(unittest.TestCase):
    """Kapıya takılan cevap SİLİNMEZ; çıkarımsal yedek devreye girer."""

    METIN = "Vakıf Katılım kart kampanyası. Kâr payı oranı %2,05'ten başlar."

    def _cevap(self, llm_cevabi: str):
        ret = _Retriever([_pasaj("vakif-katilim", self.METIN)])
        return rag.answer(None, "Vakıf Katılım kampanyası ne?",
                          llm=_Llm(llm_cevabi), retriever=ret)

    def test_dayanakli_cevap_GECER(self) -> None:
        a = self._cevap("Kâr payı oranı %2,05'ten başlıyor.")
        self.assertIn("2,05", a.text)

    def test_bos_cevap_YEDEGE_duser(self) -> None:
        a = self._cevap("   ")
        self.assertTrue(a.text.strip(), "boş gövde ekrana ÇIKMAMALI")
        self.assertTrue(a.passages, "yedek yol kaynakları korumalı")

    def test_uydurma_sayili_cevap_YEDEGE_duser(self) -> None:
        a = self._cevap("Kampanyada %50 indirim var.")
        self.assertNotIn("%50", a.text,
                         "kaynakta geçmeyen sayı ekrana çıkamaz")
        self.assertIn("Vakıf Katılım", a.text)

    def test_yedek_metni_KAYNAKTAN_geliyor(self) -> None:
        """Yedek, belgeyi alıntılar; yeni cümle üretmez."""
        a = self._cevap("")
        self.assertIn("kart kampanyası", a.text.lower())


class TestBankaSuzgeci(unittest.TestCase):
    """Sorulan bankanın belgesi yoksa BAŞKA bankanınki gösterilmez."""

    def _ret(self) -> _Retriever:
        return _Retriever([
            _pasaj("kuveyt-turk", "Kuveyt Türk makine finansmanı kampanyası.", 1),
            _pasaj("albaraka", "Albaraka kart kampanyası.", 2),
            _pasaj("vakif-katilim", "Vakıf Katılım kart kampanyası.", 3),
        ])

    def test_sorulan_bankaya_SUZULUYOR(self) -> None:
        a = rag.answer(None, "Vakıf Katılım kart kampanyasında ne var?",
                       llm=None, retriever=self._ret())
        self.assertEqual([p["bank_slug"] for p in a.passages],
                         ["vakif-katilim"])

    def test_kusurun_kendisi_yanlis_banka_GOSTERILMEZ(self) -> None:
        a = rag.answer(None, "Vakıf Katılım kart kampanyasında ne var?",
                       llm=None, retriever=self._ret())
        self.assertNotIn("kuveyt-turk", [p["bank_slug"] for p in a.passages])

    def test_bankanin_belgesi_yoksa_CEKIMSER(self) -> None:
        """Başka bankanın belgesini göstermektense cevapsız kalmak yeğdir."""
        ret = _Retriever([_pasaj("kuveyt-turk", "Kuveyt Türk kampanyası.")])
        a = rag.answer(None, "Dünya Katılım kampanyası ne?", llm=None,
                       retriever=ret)
        self.assertEqual(a.passages, [],
                         "kaynak boş kalmalı ki çekimserlik kapısı devreye girsin")

    def test_aday_havuzu_GENIS_isteniyor(self) -> None:
        """Sorulan bankanın belgesi 4. sırada olabilir; ilk 3'te süzmek onu kaybeder."""
        ret = self._ret()
        rag.answer(None, "Vakıf Katılım kampanyası ne?", llm=None, retriever=ret)
        self.assertGreaterEqual(ret.son_k, 10)

    def test_banka_gecmeyen_soruda_davranis_DEGISMEDI(self) -> None:
        ret = self._ret()
        a = rag.answer(None, "Katılma hesabı nasıl çalışır?", llm=None,
                       retriever=ret)
        self.assertEqual(ret.son_k, 3, "süzgeçsiz yolda `k` değişmemeli")
        self.assertEqual(len(a.passages), 3)


if __name__ == "__main__":
    unittest.main()
