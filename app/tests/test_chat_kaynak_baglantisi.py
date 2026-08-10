"""`/chat` kaynakları denetlenebilir bağlantı taşımak ZORUNDA.

İlgili: ../src/api/main.py (`_kaynaklari_zenginlestir`)
        ../src/chatbot/bot.py (yapısal yolun kaynak sözlüğü)
        ../src/comparison/compare.py (`RankRow.campaign_id`)

## Bu testin varlık sebebi

Ekran görüntüsünde üç kaynağın ÜÇÜNDE birden "bağlantı yok" yazıyordu.
Belge denetlenebilirliği bu projenin iddiası; jüri "bu bilgiyi nereden
aldın" diye sorduğunda arayüz tek tıkla kaynağa gidebilmeli.

Kök neden bilgi eksikliği DEĞİLDİ — `campaigns.source_url` korpustaki 1774
belgenin 1774'ünde dolu. Sorun ANAHTARDI: yapısal yol kaynak sözlüğüne
`campaign_id` koymuyordu ve `/chat` ucu kampanyayı geri bulmak için
(banka slug'ı, kanıt penceresi) çiftiyle eşleştirmek zorunda kalıyordu.

O çift TEKİL DEĞİL. Ölçüldü (`data/demo.db`):

    finansman_tutari   303 satır — %48'i aynı (banka, pencere) çiftini paylaşıyor
    vade_ay            653 satır — %44'ü
    masraf_durumu      629 satır — %63'ü

Eşleşme belirsiz olunca (doğru davranış) alan `null` bırakılıyordu; yani
kaynakların yarısına yakını "bağlantı yok" olarak basılıyordu. Bilgi vardı,
anahtar yanlıştı.

`RankRow` `campaign_id`'yi ZATEN taşıyordu — yalnız kaynak sözlüğüne
konmuyordu. Kampanya kimliği alan başına tekildir (5455 satırda mükerrer
(alan, kampanya) çifti yok), dolayısıyla eşleştirme tahmin değil kesindir.

## Neden geri düşüş yolu KORUNUYOR

Kimlik taşımayan çağıranlar (RAG pasajları, eski istemciler) için
(banka, pencere) eşleştirmesi duruyor ve belirsizken hâlâ `null` bırakıyor.
Yaklaşık eşleştirmeyle bir kampanya seçmek, denetlenebilir bağlantı
vaadinin tam tersi olurdu (CLAUDE.md §21: değer uydurma).
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.api import main as api_main
from src.chatbot.bot import Chatbot
from src.db.repository import Repository
from src.extraction.reconcile import build_campaign


def _fastapi_var() -> bool:
    try:
        from fastapi.testclient import TestClient  # noqa: F401
    except Exception:
        return False
    return True


#: İki AYRI kampanya, aynı banka, aynı kanıt penceresini üretecek metin.
#: Eski (banka, pencere) anahtarı bu ikisini ayırt EDEMEZ ve ikisini birden
#: `null`'a düşürürdü — testin kurduğu tuzak tam olarak bu.
METIN = ("Taşıt Finansmanı Kampanyası. Finansman tutarı 250.000 TL'ye "
         "kadar. Kâr payı oranı %2,05. Vade 36 aya kadar.")
URL_A = "https://ornek-katilim.com.tr/kampanyalar/tasit-finansmani-bir"
URL_B = "https://ornek-katilim.com.tr/kampanyalar/tasit-finansmani-iki"

#: Soru YAPISAL yola gitmek ZORUNDA. Kusur oraya özgü: RAG pasajları
#: `campaign_id` ile `source_url`'ü zaten taşıyor, dolayısıyla RAG'a düşen bir
#: soru bu testi hiçbir şey ölçmeden geçirir. İlk taslakta tam bu oldu —
#: "Finansman tutarı ne kadar?" router tarafından RAG'a yollanıyor ve test
#: eski kodda da yeşil yanıyordu. `test_soru_yapisal_yola_gidiyor` bu tuzağı
#: kapıda tutar.
SORU = "Finansman tutarlarını listele"


def _korpus_kur(path: str) -> Repository:
    """İki AYRI kampanya, aynı banka, AYNI kanıt penceresi.

    Eski (banka, pencere) anahtarı bu ikisini ayırt edemez ve ikisini birden
    `null`'a düşürürdü — testin kurduğu tuzak tam olarak bu.
    """
    repo = Repository(path)
    for url in (URL_A, URL_B):
        repo.insert_campaign(build_campaign(
            METIN, bank_slug="ornek-katilim", source_url=url,
            campaign_type="Taşıt Finansmanı"))
    return repo


class TestYapisalYolKampanyaKimligiTasir(unittest.TestCase):
    """Kaynak sözlüğü `campaign_id` taşımazsa bağlantı kurulamaz."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.path = str(Path(self._tmp.name) / "chat.db")
        self.repo = _korpus_kur(self.path)
        self.addCleanup(self.repo.close)

    def test_soru_yapisal_yola_gidiyor(self):
        """Testin ölçtüğü şeyi ölçtüğünün kanıtı.

        RAG yolu `campaign_id` ile `source_url`'ü zaten taşır; soru oraya
        düşerse aşağıdaki testler eski kodda da geçer ve hiçbir şey ölçmez.
        """
        from src.chatbot.router import route
        self.assertEqual("structured", route(SORU).handler)

    def test_kaynaklar_campaign_id_tasiyor(self):
        bot = Chatbot(self.repo)
        cevap = bot.ask(SORU)
        self.assertEqual("structured", cevap.handler)
        self.assertTrue(cevap.sources, "yapısal yol kaynak üretmedi")
        eksik = [s for s in cevap.sources if s.get("campaign_id") is None]
        self.assertEqual([], eksik,
                         "kaynak kampanya kimliği taşımıyor — bağlantı "
                         "yeniden kurulamaz")


@unittest.skipUnless(_fastapi_var(), "fastapi kurulu değil")
class TestChatUcuBaglantiUretiyor(unittest.TestCase):
    """`/chat` her kaynakta `source_url` döndürmeli — mükerrer pencerede de."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.path = str(Path(self._tmp.name) / "api.db")
        _korpus_kur(self.path).close()

    def _client(self):
        from fastapi.testclient import TestClient

        onceki = api_main.DB_PATH
        api_main.DB_PATH = self.path
        try:
            return TestClient(api_main.build_app())
        finally:
            api_main.DB_PATH = onceki

    def _sorgula(self):
        r = self._client().post("/chat", json={"question": SORU})
        self.assertEqual(200, r.status_code, r.text)
        govde = r.json()
        self.assertEqual("structured", govde["handler"],
                         "soru RAG'a düştü — test yanlış yolu ölçüyor")
        return govde

    def test_her_kaynak_source_url_tasiyor(self):
        kaynaklar = self._sorgula()["sources"]
        self.assertTrue(kaynaklar, "kaynak üretilmedi")
        bagsiz = [s for s in kaynaklar if not s.get("source_url")]
        self.assertEqual(
            [], bagsiz,
            "kaynakta 'bağlantı yok' — mükerrer (banka, pencere) çifti "
            "eşleştirmeyi yine zehirliyor")

    def test_donen_url_GERCEK_kampanyaninki(self):
        """Bağlantı doldurulmuş olması yetmez; DOĞRU belgeye gitmeli."""
        for s in self._sorgula()["sources"]:
            with self.subTest(bank=s.get("bank")):
                self.assertIn(s["source_url"], {URL_A, URL_B})


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
