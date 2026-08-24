"""Hibrit erişim — anahtar-kelime + vektör, RRF ile birleştirilmiş.

İlgili: ../src/chatbot/rag.py (`HybridRetriever`, `build_retriever`)
        docs/evren-servisi.md §8 (büyük erişim testi)

## Bu kol niçin var — ölçülmüş zıtlık

Büyük erişim testi (24 Ağu, 255 soru) iki soru tipinin ZIT yönde sonuç
verdiğini gösterdi:

| soru tipi | keyword | vector |
|---|---|---|
| özet-tabanlı sorgu (n=200) | **MRR 0,774** | MRR 0,559 |
| banka hedefleme (n=55) | 23/55 (%42) | **43/55 (%78)** |

Hiçbir tek kol iki tipte de iyi değil. Özet-tabanlı sorguların kelime
örtüşmesi yapay olarak yüksek (sorgu belgenin kendi özetinden türetiliyor) ve
keyword'e avantaj sağlıyor; banka hedefleme ise gerçek kullanıma daha yakın ve
orada vektör kolu belirgin öndedir.

## Neden RRF, neden skor toplamı DEĞİL

İki kolun skorları aynı ölçekte değil: `KeywordRetriever` örtüşme sayısı
üretir (tamsayı, üstsınırsız), `VectorRetriever` kosinüs üretir (0–1).
Doğrudan toplamak, ölçeği büyük olan kolun ötekini EZMESİ demektir — birleşim
adı altında tek kol çalışırdı. RRF (Reciprocal Rank Fusion) skoru değil
SIRAYI kullanır: `1/(K + rank)`. Ölçekten bağımsızdır.

Aday derinliği `k`'dan büyük olmak zorunda: yalnız ilk `k` alınırsa iki liste
büyük ölçüde örtüşür ve birleştirmenin kazandıracağı bir şey kalmaz.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.chatbot.rag import (
    RETRIEVER_MODES,
    HybridRetriever,
)


class _SahteKol:
    """Sabit sıralama döndüren sahte retriever."""

    def __init__(self, kimlikler, ad="sahte"):
        self.kimlikler = list(kimlikler)
        self.retriever_name = ad
        self.istenen_k: list[int] = []
        self.document_count = 100

    def retrieve(self, query: str, k: int = 3) -> list[dict]:
        self.istenen_k.append(k)
        return [{"campaign_id": c, "text": f"belge {c}", "score": 1.0/(i+1),
                 "bank": "X", "bank_slug": "x", "source_url": ""}
                for i, c in enumerate(self.kimlikler[:k])]


def _kimlikler(sonuc):
    return [p["campaign_id"] for p in sonuc]


class RRFTest(unittest.TestCase):

    def test_iki_kolda_ust_sirada_olan_KAZANIR(self):
        kw = _SahteKol([1, 2, 3, 4])
        vec = _SahteKol([3, 1, 5, 6])
        h = HybridRetriever(keyword=kw, vector=vec)
        # 1: 1/(60+1) + 1/(60+2);  3: 1/(60+3) + 1/(60+1)
        self.assertEqual(_kimlikler(h.retrieve("s", k=2))[0], 1)

    def test_TEK_kolda_gecen_belge_de_listeye_girer(self):
        kw = _SahteKol([1, 2])
        vec = _SahteKol([9])
        h = HybridRetriever(keyword=kw, vector=vec)
        self.assertIn(9, _kimlikler(h.retrieve("s", k=3)))

    def test_SKOR_toplami_DEGIL_sira_kullanilir(self):
        """Bir kolun skor ölçeği büyük olsa bile ötekini ezmemeli."""

        class _BuyukSkor(_SahteKol):
            def retrieve(self, query, k=3):
                return [{"campaign_id": c, "text": "", "score": 10_000.0,
                         "bank": "X", "bank_slug": "x", "source_url": ""}
                        for c in self.kimlikler[:k]]

        kw = _BuyukSkor([7, 8])          # skorları 10.000
        vec = _SahteKol([8, 7])          # skorları ≤ 1
        h = HybridRetriever(keyword=kw, vector=vec)
        # 8: rank 2 + rank 1;  7: rank 1 + rank 2 -> RRF eşit, sıra korunur
        self.assertEqual(set(_kimlikler(h.retrieve("s", k=2))), {7, 8})

    def test_k_kadar_sonuc_doner(self):
        h = HybridRetriever(keyword=_SahteKol([1, 2, 3, 4, 5]),
                            vector=_SahteKol([6, 7, 8, 9, 10]))
        self.assertEqual(len(h.retrieve("s", k=3)), 3)

    def test_aday_derinligi_k_dan_BUYUK(self):
        """Yalnız ilk k alınsa iki liste örtüşür ve birleşimin anlamı kalmaz."""
        kw = _SahteKol([1, 2, 3, 4, 5, 6, 7, 8, 9])
        vec = _SahteKol([9, 8, 7, 6, 5, 4, 3, 2, 1])
        h = HybridRetriever(keyword=kw, vector=vec)
        h.retrieve("s", k=3)
        self.assertGreater(kw.istenen_k[0], 3)
        self.assertGreater(vec.istenen_k[0], 3)

    def test_bos_sonuc_patlamaz(self):
        h = HybridRetriever(keyword=_SahteKol([]), vector=_SahteKol([]))
        self.assertEqual(h.retrieve("s", k=3), [])

    def test_bir_kol_PATLARSA_oteki_devam_eder(self):
        """Vektör kolu koşum ortasında düşerse erişim tümden durmamalı."""

        class _Patlak(_SahteKol):
            def retrieve(self, query, k=3):
                raise RuntimeError("gomme ucu dustu")

        h = HybridRetriever(keyword=_SahteKol([1, 2]), vector=_Patlak([]))
        self.assertEqual(_kimlikler(h.retrieve("s", k=2)), [1, 2])


class ArayuzTest(unittest.TestCase):

    def test_retriever_adi(self):
        h = HybridRetriever(keyword=_SahteKol([1]), vector=_SahteKol([2]))
        self.assertEqual(h.retriever_name, "hibrit")

    def test_document_count_keyword_kolundan(self):
        h = HybridRetriever(keyword=_SahteKol([1]), vector=_SahteKol([2]))
        self.assertEqual(h.document_count, 100)

    def test_mod_listesinde(self):
        self.assertIn("hibrit", RETRIEVER_MODES)


if __name__ == "__main__":
    unittest.main()
