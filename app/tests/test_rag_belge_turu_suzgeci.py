"""Vektör erişiminde `belge_turu` süzgeci — sözleşme baskınlığına karşı.

İlgili: ../src/chatbot/rag.py (`VectorRetriever`)
        docs/evren-servisi.md §8

## Niçin var — ölçülmüş baskınlık

Korpus 1.726 kampanya ve 982 sözleşme içeriyor, ama sözleşmeler çok uzun:
51.556 gömme parçasının büyük kısmı onlardan geliyor. Jenerik hukuki metin her
sorguya orta düzeyde benzediği için ham vektör aramasında öne çıkıyor —
ölçüldü (24 Ağu): *"en yüksek kâr payı oranı hangi bankada"* sorgusu
**Genel Kredi Sözleşmesi** pasajları döndürdü.

## Aday derinliği niçin ARTIRILIYOR

`retrieve` normalde `k*5` parça istiyor. Süzgeç uygulanırsa o adayların hepsi
elenebilir ve sonuç BOŞ dönerdi — süzgeç, arama derinliğini artırmadan
eklenemez. Bu yüzden süzgeç etkinken derinlik ayrıca çarpılıyor.

## Süzgeç niçin sonradan uygulanıyor, sorguya gömülmüyor

`store.search` yalnız vektör benzerliği biliyor; `belge_turu` kampanya
kaydında (`_meta`). Süzgeci store'a taşımak, iki farklı arka uç (SQLite ve
pgvector) için ayrı SQL yazmak demekti. Arama sonrası süzme aynı sonucu verir
ve tek yerde durur.
"""

from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.chatbot.rag import VectorRetriever


class _Hit:
    """`EmbeddingStore.search` isabet sözleşmesi (bkz. src/db)."""

    def __init__(self, campaign_id, score, text="parca metni"):
        self.campaign_id = campaign_id
        self.score = score
        self.chunk_text = text
        self.chunk_index = 0


class _Store:
    """Sabit isabet listesi döndüren sahte gömme deposu."""

    backend = "sahte"

    def __init__(self, hits):
        self.hits = hits
        self.istenen_k: list[int] = []

    def count(self):
        return 100

    def search(self, vector, k):
        self.istenen_k.append(k)
        return self.hits[:k]


class _Embedder:
    name = "sahte"
    dim = 4
    available = True

    def encode(self, texts):
        return [[1.0, 0.0, 0.0, 0.0] for _ in texts]


class _Repo:
    """`all_campaigns` yalnız meta döndürür — türler burada."""

    def __init__(self, kayitlar):
        self._k = kayitlar

    def all_campaigns(self):
        return self._k


def _kur(hits, kayitlar, **kw):
    return VectorRetriever(_Repo(kayitlar), embedder=_Embedder(),
                           store=_Store(hits), **kw)


KAYITLAR = [
    {"id": 1, "bank": "A", "bank_slug": "a", "source_url": "u1",
     "belge_turu": "kampanya", "clean_text": "kampanya metni"},
    {"id": 2, "bank": "B", "bank_slug": "b", "source_url": "u2",
     "belge_turu": "sozlesme", "clean_text": "sozlesme metni"},
    {"id": 3, "bank": "C", "bank_slug": "c", "source_url": "u3",
     "belge_turu": "sozlesme", "clean_text": "sozlesme metni"},
    {"id": 4, "bank": "D", "bank_slug": "d", "source_url": "u4",
     "belge_turu": "kampanya", "clean_text": "kampanya metni"},
]
# Sözleşmeler ÖNDE — baskınlık senaryosu
HITS = [_Hit(2, 0.90), _Hit(3, 0.88), _Hit(1, 0.60), _Hit(4, 0.55)]


def _ids(sonuc):
    return [p["campaign_id"] for p in sonuc]


class SuzgecTest(unittest.TestCase):

    def test_suzgec_YOKSA_davranis_degismez(self):
        r = _kur(HITS, KAYITLAR)
        self.assertEqual(_ids(r.retrieve("s", k=2)), [2, 3])

    def test_suzgec_yalniz_izinli_TURU_dondurur(self):
        r = _kur(HITS, KAYITLAR, belge_turleri={"kampanya"})
        self.assertEqual(_ids(r.retrieve("s", k=2)), [1, 4])

    def test_coklu_tur_izni(self):
        r = _kur(HITS, KAYITLAR, belge_turleri={"kampanya", "sozlesme"})
        self.assertEqual(len(r.retrieve("s", k=4)), 4)

    def test_ADAY_DERINLIGI_artiyor(self):
        """Süzgeç, derinlik artmadan eklenemez: adaylar elenip liste boşalırdı."""
        suz = _kur(HITS, KAYITLAR, belge_turleri={"kampanya"})
        suz.retrieve("s", k=2)
        yalin = _kur(HITS, KAYITLAR)
        yalin.retrieve("s", k=2)
        self.assertGreater(suz.store.istenen_k[0], yalin.store.istenen_k[0])

    def test_suzgecten_sonra_AZ_kalirsa_kalani_dondurur(self):
        r = _kur(HITS, KAYITLAR, belge_turleri={"kampanya"})
        self.assertEqual(len(r.retrieve("s", k=10)), 2)   # yalnız 2 kampanya var

    def test_hicbiri_uymazsa_BOS_doner(self):
        r = _kur(HITS, KAYITLAR, belge_turleri={"yok-boyle-tur"})
        self.assertEqual(r.retrieve("s", k=3), [])

    def test_turu_OLMAYAN_kayit_elenir_ama_patlamaz(self):
        kayitlar = KAYITLAR + [{"id": 5, "bank": "E", "bank_slug": "e",
                                "source_url": "u5", "clean_text": "x"}]
        hits = HITS + [_Hit(5, 0.5)]
        r = _kur(hits, kayitlar, belge_turleri={"kampanya"})
        self.assertNotIn(5, _ids(r.retrieve("s", k=5)))


class EnvTest(unittest.TestCase):

    def test_env_den_okunur(self):
        with mock.patch.dict(os.environ, {"RAG_BELGE_TURU": "kampanya"}):
            r = _kur(HITS, KAYITLAR)
        self.assertEqual(_ids(r.retrieve("s", k=2)), [1, 4])

    def test_env_virgullu_liste(self):
        with mock.patch.dict(os.environ,
                             {"RAG_BELGE_TURU": " kampanya , sozlesme "}):
            r = _kur(HITS, KAYITLAR)
        self.assertEqual(r.belge_turleri, {"kampanya", "sozlesme"})

    def test_env_BOSSA_suzgec_yok(self):
        with mock.patch.dict(os.environ, {"RAG_BELGE_TURU": ""}):
            r = _kur(HITS, KAYITLAR)
        self.assertIsNone(r.belge_turleri)

    def test_arguman_env_den_GUCLU(self):
        with mock.patch.dict(os.environ, {"RAG_BELGE_TURU": "sozlesme"}):
            r = _kur(HITS, KAYITLAR, belge_turleri={"kampanya"})
        self.assertEqual(r.belge_turleri, {"kampanya"})


if __name__ == "__main__":
    unittest.main()
