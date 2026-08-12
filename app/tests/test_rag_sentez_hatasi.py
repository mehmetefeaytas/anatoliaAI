"""RAG sentezi çökerse SESSİZ kalmaz — yedeğe düşer ama kayda geçer.

İlgili: ../src/chatbot/rag.py (`answer`, `_SENTEZ_HATALARI`),
        ../src/extraction/llm/extractor.py:8-23 (aynı desenin ilk kurbanı),
        ../scripts/eval_injection.py (raporu bu ayrıma dayanıyor)

## Bu testin varlık sebebi — ÖLÇÜLDÜ (2026-08-12)

`rag.answer` içinde LLM sentez bloğu şöyle bitiyordu:

    except Exception:
        pass

Kayıtsız, sessiz, TÜM istisnaları yutan bir satır. Tam olarak
`extraction/llm/extractor.py`nin kaldırmak için yeniden yazıldığı desen; o
modülün başlığı bunu "bu tek satır sessizce yalan söyleyebiliyordu" diye
anıyor.

Somut zarar bir GÜVENLİK ölçümündeydi: `scripts/eval_injection.py` raporu
"SENTEZ DAHİL (LLM açık)" başlığını basıyor. Sentez her çağrıda istisnayla
düşse bile rapor aynı başlığı basar ve enjeksiyon savunmasının LLM yolunda
gerçekten sınandığını ima eder — oysa model hiç konuşmamış olabilir. Ölçüm
katmanının en tehlikeli hata biçimi budur: yanlış şeyi ölçüp doğru görünmek.

## Yutma DEVAM EDİYOR, sessizlik BİTTİ

İstisnanın yutulması doğru davranıştır: LLM çökerse kullanıcı boş ekran
değil, kaynağa dayalı çıkarımsal bir cevap almalı (`_cikarimsal_cevap`).
Değişen şey yalnız görünürlük — `logger.exception` + süreç sayacı.
"""

from __future__ import annotations

import logging
import sys
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.chatbot import rag
from src.db.repository import Repository
from src.extraction.reconcile import build_campaign

METIN = "Vakıf Katılım konut finansmanı kâr payı oranı %1,89, vade 120 ay."


class _CokenIstemci:
    """`generate_json` her çağrıda çöker."""

    def __init__(self) -> None:
        self.cagri = 0

    def generate_json(self, *a, **kw):
        self.cagri += 1
        raise RuntimeError("sentez servisi çöktü")


class _CokenLlm:
    def __init__(self) -> None:
        self.client = _CokenIstemci()

    @property
    def available(self) -> bool:
        return True


class SentezCokunceSESSIZKALINMAZ(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        cls.repo = Repository(":memory:")
        cls.repo.insert_campaign(build_campaign(
            METIN, bank_slug="vakif-katilim", campaign_type="Konut Finansmanı"))
        cls.ret = rag.KeywordRetriever(cls.repo)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.repo.close()

    def setUp(self) -> None:
        self._onceki = rag._SENTEZ_HATALARI["sayi"]

    def test_cevap_YINE_DONER_cikarimsal_yedekle(self) -> None:
        """Yutma doğru davranış: kullanıcı boş ekran görmemeli."""
        llm = _CokenLlm()
        cevap = rag.answer(self.repo, "konut finansmanı kâr payı oranı",
                           llm=llm, retriever=self.ret)
        self.assertTrue(llm.client.cagri, "LLM hiç çağrılmadı — test bir şey ölçmüyor")
        self.assertTrue(
            (cevap.text or "").strip(),
            "sentez çöktü ve kullanıcıya BOŞ cevap döndü")
        self.assertTrue(cevap.passages, "kaynak pasajlar da kayboldu")

    def test_istisna_GUNLUGE_yazilir(self) -> None:
        llm = _CokenLlm()
        with self.assertLogs("src.chatbot.rag", level=logging.ERROR) as kayit:
            rag.answer(self.repo, "konut finansmanı kâr payı oranı",
                       llm=llm, retriever=self.ret)
        birlesik = "\n".join(kayit.output)
        self.assertIn("sentez", birlesik.lower(),
                      "sentez hatası günlüğe yazılmadı — sessiz yutma geri gelmiş")
        self.assertIn("sentez servisi çöktü", birlesik,
                      "istisnanın kendisi günlüğe geçmedi (yığın izi yok)")

    def test_sayac_ARTAR(self) -> None:
        """Günlük satırı olayı, sayaç ise koşumun bütününü anlatır."""
        llm = _CokenLlm()
        rag.answer(self.repo, "konut finansmanı kâr payı oranı",
                   llm=llm, retriever=self.ret)
        self.assertEqual(
            self._onceki + 1, rag.sentez_hata_sayisi(),
            "sentez hata sayacı artmadı — ölçüm katmanı 'sentez gerçekten "
            "çalıştı mı' sorusunu yine cevaplayamaz")

    def test_saglikli_sentezde_sayac_ARTMAZ(self) -> None:
        """Sayaç yalnız gerçek hatayı saymalı; yoksa gürültü olur."""

        class _SaglikliIstemci:
            def generate_json(self, *a, **kw):
                # Bağlamda geçen bir değeri kullanan, dayanaklı kısa cevap.
                return {"cevap": "Kâr payı oranı %1,89'dur."}

        class _SaglikliLlm:
            client = _SaglikliIstemci()
            available = True

        rag.answer(self.repo, "konut finansmanı kâr payı oranı",
                   llm=_SaglikliLlm(), retriever=self.ret)
        self.assertEqual(
            self._onceki, rag.sentez_hata_sayisi(),
            "sağlıklı sentezde hata sayacı arttı")


if __name__ == "__main__":
    unittest.main()
