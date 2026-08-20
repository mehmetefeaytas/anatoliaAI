"""RAG yolunda ÜRÜN AİLESİ süzgeci, banka×aile ÇEŞİTLİLİK tavanı ve şerit
arındırma.

İlgili: ../src/chatbot/rag.py (`_bankaya_suz`, `_tur_suz`,
        `_cesitlilik_tavani`, `_anlamli_alinti`, `_bos_sonuc_metni`)
        ../src/chatbot/bot.py (`rag.answer(..., filters=r.filters)`)
        ../src/comparison/compare.py (`tekil_banka_urun` — kural burada)
        ../src/extraction/rules/_ortak.py (`gezinme_seridi` — imza burada)

## Üç ölçülmüş kusur (2026-08-20, canlı sistem, jürinin gördüğü ekran)

1. **Süzgeç çöpe atılıyordu.** `bot.py` router'ın çıkardığı `Route.filters`'ı
   `rag.answer`'a HİÇ GEÇMİYORDU. `rag._bankaya_suz` banka süzgecini soruyu
   yeniden okuyarak kuruyor, ürün ailesi için hiçbir karşılığı yoktu. Sonuç:
   **konut** sorusuna dönen üç pasajın ikisi **İhtiyaç Finansmanı** belgesi.
   Aynı süzgeci yapısal yol (`structured._apply_filters`) zaten uyguluyordu —
   iki yolun aynı soruya farklı dürüstlük standardı uygulaması.

2. **Banka çeşitlilik tavanı yoktu.** `KeywordRetriever.retrieve` düz BM25 +
   `scored[:k]`; `_PASAJ_SAYISI = 3` yalnız bir ADETtir. Dünya Katılım'ın 123
   şablon-benzeri belgesi ilk üç sırayı süpürüyordu (10,04 / 8,99 / 8,99) ve
   "hangi banka" sorusunun cevabı olarak TEK banka görünüyordu. Kural iki
   yerde zaten yazılıydı (`VectorRetriever` kampanya tekilleştirmesi,
   `compare.tekil_banka_urun`) ve üretim yolu (`RAG_RETRIEVER=keyword`)
   ikisini de kullanmıyordu.

3. **Snippet'te gezinme şeridi.** Özeti olmayan belgede cevabın gövdesi ham
   metnin başlangıcıdır ve bir banka sayfasının başı MENÜDÜR.

## Etiket doğruluğu bu dosyanın konusu DEĞİLDİR

`campaigns.campaign_type` 8-sınıf sınıflandırıcının çıktısıdır ve kendi hata
payı vardır. Burada ölçülen tek şey süzgecin UYGULANDIĞIDIR: sorulan aileyle
belgenin ailesi karşılaştırılıyor mu. Sınıflandırma hatası yanlış aileden
belge gösterebilir; o hata `src/extraction/` tarafındadır.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.chatbot import rag
from src.chatbot.bot import Chatbot
from src.chatbot.router import BANK_DISPLAY, route
from src.db.repository import Repository
from src.extraction.reconcile import build_campaign


class _Retriever:
    """Sabit pasaj listesi döndüren sahte getirici (aday havuzunu kaydeder)."""

    retriever_name = "keyword"

    def __init__(self, pasajlar: list[dict]) -> None:
        self.pasajlar = pasajlar
        self.son_k: int | None = None

    def retrieve(self, query: str, k: int = 3) -> list[dict]:
        self.son_k = k
        return self.pasajlar[:k]


def _pasaj(slug: str, metin: str, cid: int, tur: str | None = None) -> dict:
    return {"bank": BANK_DISPLAY.get(slug, slug), "bank_slug": slug,
            "campaign_id": cid, "campaign_type": tur, "source_url": None,
            "text": metin, "ozet": None, "score": 1.0, "overlap": 3}


class TestTurSuzgeci(unittest.TestCase):
    """Sorulan ürün ailesi dışındaki belge CEVAP OLARAK gösterilmez."""

    def _ret(self) -> _Retriever:
        return _Retriever([
            _pasaj("dunya-katilim", "İhtiyaç finansmanı kampanyası bir.", 1,
                   "İhtiyaç Finansmanı"),
            _pasaj("dunya-katilim", "İhtiyaç finansmanı kampanyası iki.", 2,
                   "İhtiyaç Finansmanı"),
            _pasaj("albaraka", "Konut finansmanı kampanyası.", 3,
                   "Konut Finansmanı"),
        ])

    def test_kusurun_kendisi_KONUT_sorusuna_IHTIYAC_belgesi_GELMEZ(self) -> None:
        a = rag.answer(None, "Konut finansmanı kampanyası ne?", llm=None,
                       retriever=self._ret(),
                       filters={"campaign_type": "Konut Finansmanı"})
        self.assertEqual([p["campaign_id"] for p in a.passages], [3])

    def test_suzgec_GECILMEZSE_davranis_eskisi_gibi(self) -> None:
        """Geriye dönük uyum: `filters` yoksa tür süzgeci hiç kurulmaz."""
        a = rag.answer(None, "Konut finansmanı kampanyası ne?", llm=None,
                       retriever=self._ret())
        self.assertIn(1, [p["campaign_id"] for p in a.passages])

    def test_aile_bos_kalirsa_CEKIMSER(self) -> None:
        """Başka ailenin belgesini göstermektense cevapsız kalmak yeğdir."""
        a = rag.answer(None, "Taşıt finansmanı kampanyası ne?", llm=None,
                       retriever=self._ret(),
                       filters={"campaign_type": "Taşıt Finansmanı"})
        self.assertEqual(a.passages, [])
        self.assertIn("Taşıt Finansmanı", a.text,
                      "boş cevap NEYİN elediğini söylemeli")

    def test_bos_cevap_banka_kisitini_da_soyler(self) -> None:
        a = rag.answer(None, "Dünya Katılım taşıt kampanyası?", llm=None,
                       retriever=self._ret(),
                       filters={"campaign_type": "Taşıt Finansmanı",
                                "banks": ["dunya-katilim"]})
        self.assertEqual(a.passages, [])
        self.assertIn("Dünya Katılım", a.text)

    def test_baglamdan_devralinan_banka_suzgeci_de_UYGULANIR(self) -> None:
        """Süzgeç ÇAĞIRANDAN gelir; soru metninde banka geçmese de geçerlidir."""
        a = rag.answer(None, "Kampanya koşulları neler?", llm=None,
                       retriever=self._ret(), filters={"banks": ["albaraka"]})
        self.assertEqual([p["bank_slug"] for p in a.passages], ["albaraka"])


class TestCesitlilikTavani(unittest.TestCase):
    """Banka × ürün ailesi başına TEK pasaj; düşürülenler SAYILIR."""

    def test_kusurun_kendisi_tek_banka_ilk_UCU_supurmez(self) -> None:
        ret = _Retriever([
            _pasaj("dunya-katilim", "Şablon belge bir.", 1, "Kart"),
            _pasaj("dunya-katilim", "Şablon belge iki.", 2, "Kart"),
            _pasaj("dunya-katilim", "Şablon belge üç.", 3, "Kart"),
            _pasaj("albaraka", "Albaraka kart kampanyası.", 4, "Kart"),
            _pasaj("vakif-katilim", "Vakıf Katılım kart kampanyası.", 5, "Kart"),
        ])
        a = rag.answer(None, "Kart kampanyası ne?", llm=None, retriever=ret)
        self.assertEqual([p["bank_slug"] for p in a.passages],
                         ["dunya-katilim", "albaraka", "vakif-katilim"])

    def test_ayni_banka_FARKLI_aile_tekilleştirilmez(self) -> None:
        """Bir bankanın konut ve taşıt kampanyası FARKLI ürünlerdir."""
        ret = _Retriever([
            _pasaj("albaraka", "Konut kampanyası.", 1, "Konut Finansmanı"),
            _pasaj("albaraka", "Taşıt kampanyası.", 2, "Taşıt Finansmanı"),
            _pasaj("albaraka", "Kart kampanyası.", 3, "Kart"),
        ])
        a = rag.answer(None, "Albaraka kampanyaları?", llm=None, retriever=ret)
        self.assertEqual([p["campaign_id"] for p in a.passages], [1, 2, 3])

    def test_dusurulenler_SAYILIR_ve_YAZILIR(self) -> None:
        ret = _Retriever([
            _pasaj("dunya-katilim", "Şablon bir.", 1, "Kart"),
            _pasaj("dunya-katilim", "Şablon iki.", 2, "Kart"),
            _pasaj("dunya-katilim", "Şablon üç.", 3, "Kart"),
        ])
        a = rag.answer(None, "Kart kampanyası ne?", llm=None, retriever=ret)
        self.assertEqual(len(a.passages), 1)
        self.assertEqual(a.passages[0]["other_count"], 2)
        self.assertIn("2 belge daha", a.text)

    def test_tavan_sirayi_KORUR_en_alakaliyi_birakir(self) -> None:
        """Adaylar BM25 sırasındadır; kalan, çiftin en alakalı belgesidir."""
        ret = _Retriever([
            _pasaj("albaraka", "En alakalı.", 7, "Kart"),
            _pasaj("albaraka", "Daha az alakalı.", 8, "Kart"),
        ])
        a = rag.answer(None, "Kart kampanyası ne?", llm=None, retriever=ret)
        self.assertEqual([p["campaign_id"] for p in a.passages], [7])

    def test_aday_havuzu_TAVAN_icin_genis(self) -> None:
        ret = _Retriever([_pasaj("albaraka", "Kart.", 1, "Kart")])
        rag.answer(None, "Kart kampanyası ne?", llm=None, retriever=ret)
        self.assertEqual(ret.son_k, rag._CESITLILIK_ADAY_SAYISI)


class TestSeritArindirma(unittest.TestCase):
    """Özeti olmayan belgenin snippet'i MENÜ olmamalı.

    ## Sınırı BİLEREK ölçüyoruz: pencere kayması SINIRDA artık bırakır

    Kırpma `_SERIT_PENCERESI` sözcüklük bir pencereyi ileri kaydırır ve
    pencere gerçek cümlenin küçük harfli sözcüklerini görmeye başladığında
    durur. Yani şeritten geriye en fazla pencere boyu kadar sözcük kalabilir.
    Bu artık KABUL EDİLİYOR: alternatifi "ilk küçük harfli sözcüğe kadar
    kırp" olurdu ve o kural gerçek başlıkları da silerdi ("TÜRKİYE EMLAK
    KATILIM BANKASI A.Ş. … Aydınlatma Metni" ölçüldü, korunmalı).

    Testler bu yüzden "şeridin BAŞI gitti ve gerçek cümle geldi" der,
    "hiçbir artık kalmadı" demez — ölçülmemiş bir iddiayı kilitlemek, testin
    kendisini yalancı yapardı.
    """

    MENU = ("Bireysel Kurumsal Ana Sayfa Müşteri Ol Kredi Kartı Kampanyaları "
            "Maaş Ödemesi Kampanyaları Worldcard Kampanyaları")
    CUMLE = ("Konut finansmanında kâr payı oranı yüzde iki olarak "
             "uygulanmaktadır.")

    def test_seridin_BASI_atilir_gercek_cumle_kalir(self) -> None:
        alinti = rag._anlamli_alinti(f"{self.MENU} {self.CUMLE}")
        self.assertIn("kâr payı oranı", alinti)
        self.assertNotIn("Bireysel Kurumsal Ana Sayfa", alinti)
        self.assertNotIn("Müşteri Ol", alinti)
        self.assertLess(len(alinti), len(f"{self.MENU} {self.CUMLE}"))

    def test_belgenin_TAMAMI_seritse_ham_metne_dusulur(self) -> None:
        """Boş alıntı basmak, elde duran tek kanıtı hiç göstermemek olurdu."""
        self.assertIn("Worldcard", rag._anlamli_alinti(self.MENU))

    def test_gercek_cumle_KIRPILMAZ(self) -> None:
        """Şerit imzası taşımayan metne dokunulmamalı (geri uyum)."""
        self.assertEqual(rag._anlamli_alinti(self.CUMLE), self.CUMLE)

    def test_cikarimsal_cevap_serit_basmaz(self) -> None:
        metin = rag._cikarimsal_cevap(
            {"bank": "Albaraka Türk", "text": f"{self.MENU} {self.CUMLE}"})
        self.assertIn("kâr payı oranı", metin)
        self.assertNotIn("Bireysel Kurumsal Ana Sayfa", metin)


class TestBotSuzgeciGECIRIR(unittest.TestCase):
    """Uçtan uca: `bot.ask` router'ın süzgecini RAG'e taşımalı."""

    KORPUS = [
        ("dunya-katilim", "İhtiyaç finansmanı kampanyası koşulları nelerdir.",
         "İhtiyaç Finansmanı"),
        ("dunya-katilim", "İhtiyaç finansmanı kampanyası koşulları hangileri.",
         "İhtiyaç Finansmanı"),
        ("albaraka", "Konut finansmanı kampanyası koşulları nelerdir.",
         "Konut Finansmanı"),
    ]

    def setUp(self) -> None:
        self.depo = Repository(":memory:")
        self.addCleanup(self.depo.close)
        for slug, metin, tur in self.KORPUS:
            self.depo.upsert_bank(BANK_DISPLAY.get(slug, slug), slug)
            self.depo.insert_campaign(
                build_campaign(metin, bank_slug=slug, campaign_type=tur))
        self.bot = Chatbot(self.depo)

    def test_konut_sorusunda_IHTIYAC_belgesi_kaynak_olmaz(self) -> None:
        soru = "Konut finansmanı kampanyasının koşulları nelerdir?"
        self.assertEqual(route(soru).handler, "rag",
                         "bu soru RAG yolunda kalmalı (açıklama sorusu)")
        a = self.bot.ask(soru)
        self.assertEqual(a.handler, "rag")
        for s in a.sources:
            self.assertNotIn("İhtiyaç", s["text"])


if __name__ == "__main__":
    unittest.main()
