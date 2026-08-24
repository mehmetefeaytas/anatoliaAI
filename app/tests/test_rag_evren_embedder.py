"""EVREN destekli gömme üreticisi + kademeli (yedekli) seçim.

İlgili: ../src/rag/embedding.py
        ../src/extraction/llm/clients.py (`bearer_transport` yeniden kullanılıyor)
        docs/evren-servisi.md §8 (gömme yolu neden kapalıydı)

## Neden bu dosya var

`embeddings` tablosu boştu, çünkü bu makinede `sentence-transformers` kurulu
değildi ve `BgeM3Embedder` açık hata veriyordu. Sonuç: `chatbot/rag.py`
içindeki `VectorRetriever` hiç devreye girmiyor, chatbot yalnız anahtar-kelime
ile çalışıyordu. EVREN aynı modeli (`BAAI/bge-m3`, 1024 boyut) uzak uçtan
veriyor ve ölçülen kalitesi yüksek (gerçek korpusta Recall@1 %97).

## Kademe neden GÜVENLİ — ve ne zaman olmazdı

Vektör kademesi, LLM kademesinden farklı bir tehlike taşır: iki kademe FARKLI
modeller olsaydı ürettikleri vektörler farklı uzaylarda olurdu, `embeddings`
tablosu karışık uzaylardan dolardı ve arama **sessizce** bozulurdu — hata
vermez, sadece yanlış sonuç verir. Kademe burada güvenlidir çünkü iki kademe
de **aynı modeldir**: EVREN'in `bge-m3-embed` ucu ile yerel `BAAI/bge-m3` aynı
ağırlıklar. Bu yüzden `KademeliEmbedder` boyut eşitliğini kurulumda DENETLER;
eşit değilse kurulmaz.

Hiçbir test ağa çıkmaz: taşıma (transport) enjekte edilir.
"""

from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.rag.embedding import (
    EMBEDDING_DIM,
    EmbeddingModelUnavailable,
    EvrenEmbedder,
    KademeliEmbedder,
    load_embedder,
)


class _SahteUc:
    """`(url, payload, timeout) -> dict` — EVREN /v1/embeddings taklidi."""

    def __init__(self, dim: int = EMBEDDING_DIM, karistir: bool = False,
                 hata: Exception | None = None):
        self.dim = dim
        self.karistir = karistir
        self.hata = hata
        self.istekler: list[dict] = []

    def __call__(self, url: str, payload: dict, timeout: float) -> dict:
        if self.hata is not None:
            raise self.hata
        self.istekler.append(payload)
        girdiler = payload["input"]
        veri = [{"index": i, "embedding": [float(i)] * self.dim}
                for i in range(len(girdiler))]
        if self.karistir:            # API sırayı korumayabilir
            veri = list(reversed(veri))
        return {"data": veri}


class _YerelSahte:
    """Yerel `Embedder` taklidi."""

    def __init__(self, dim: int = EMBEDDING_DIM, kullanilabilir: bool = True):
        self.name = "sahte-yerel"
        self.dim = dim
        self._k = kullanilabilir
        self.cagri = 0

    @property
    def available(self) -> bool:
        return self._k

    def encode(self, texts):
        if not self._k:
            raise EmbeddingModelUnavailable("sahte yerel model yok")
        self.cagri += 1
        return [[-1.0] * self.dim for _ in texts]


class EvrenEmbedderTest(unittest.TestCase):

    def test_dogru_boyutta_vektor_uretir(self):
        uc = _SahteUc()
        e = EvrenEmbedder(api_key="sk-x", transport=uc)
        v = e.encode(["a", "b", "c"])
        self.assertEqual(len(v), 3)
        self.assertEqual(len(v[0]), EMBEDDING_DIM)
        self.assertEqual(e.dim, EMBEDDING_DIM)

    def test_SIRA_korunur(self):
        """API `index` alanını karışık döndürse bile giriş sırası korunmalı.

        Korunmazsa `embeddings.campaign_id` ile vektör eşleşmesi bozulur ve
        arama yanlış belgeyi döndürür — sessiz, teşhisi zor bir bozulma.
        """
        uc = _SahteUc(karistir=True)
        e = EvrenEmbedder(api_key="sk-x", transport=uc)
        v = e.encode(["a", "b", "c"])
        self.assertEqual([x[0] for x in v], [0.0, 1.0, 2.0])

    def test_toplu_gonderim_PARCALANIR(self):
        uc = _SahteUc()
        e = EvrenEmbedder(api_key="sk-x", transport=uc, batch=4)
        v = e.encode([f"m{i}" for i in range(10)])
        self.assertEqual(len(v), 10)
        self.assertEqual(len(uc.istekler), 3)             # 4 + 4 + 2
        self.assertEqual([len(p["input"]) for p in uc.istekler], [4, 4, 2])

    def test_YANLIS_boyut_acik_hata(self):
        """`db/schema.sql` vector(1024) ile uyuşmazlık sessizce geçmemeli."""
        e = EvrenEmbedder(api_key="sk-x", transport=_SahteUc(dim=768))
        with self.assertRaises(EmbeddingModelUnavailable) as ctx:
            e.encode(["a"])
        self.assertIn("768", str(ctx.exception))

    def test_anahtarsiz_KULLANILAMAZ(self):
        with mock.patch.dict(os.environ, {"EVREN_API_KEY": ""}):
            e = EvrenEmbedder()
        self.assertFalse(e.available)

    def test_anahtarsiz_encode_acik_hata(self):
        with mock.patch.dict(os.environ, {"EVREN_API_KEY": ""}):
            e = EvrenEmbedder()
        with self.assertRaises(EmbeddingModelUnavailable):
            e.encode(["a"])

    def test_bos_girdi_AGA_CIKMAZ(self):
        uc = _SahteUc()
        e = EvrenEmbedder(api_key="sk-x", transport=uc)
        self.assertEqual(e.encode([]), [])
        self.assertEqual(uc.istekler, [])

    def test_model_ve_uc_ozelleştirilebilir(self):
        uc = _SahteUc()
        e = EvrenEmbedder(api_key="sk-x", transport=uc,
                          base_url="https://ornek.invalid/", model="bge-m3-embed")
        e.encode(["a"])
        self.assertEqual(uc.istekler[0]["model"], "bge-m3-embed")
        self.assertTrue(e.name.startswith("evren:"))


class KademeliEmbedderTest(unittest.TestCase):

    def test_birincil_calisirsa_yedek_CAGRILMAZ(self):
        yerel = _YerelSahte()
        k = KademeliEmbedder([EvrenEmbedder(api_key="sk-x", transport=_SahteUc()),
                              yerel])
        v = k.encode(["a"])
        self.assertEqual(v[0][0], 0.0)          # EVREN'den geldi
        self.assertEqual(yerel.cagri, 0)

    def test_birincil_duserse_YEDEK_devralir(self):
        yerel = _YerelSahte()
        kirik = EvrenEmbedder(api_key="sk-x",
                              transport=_SahteUc(hata=OSError("ag yok")))
        k = KademeliEmbedder([kirik, yerel])
        v = k.encode(["a", "b"])
        self.assertEqual(v[0][0], -1.0)         # yerelden geldi
        self.assertEqual(yerel.cagri, 1)

    def test_hepsi_duserse_ACIK_HATA(self):
        k = KademeliEmbedder([
            EvrenEmbedder(api_key="sk-x", transport=_SahteUc(hata=OSError("x"))),
            _YerelSahte(kullanilabilir=False)])
        with self.assertRaises(EmbeddingModelUnavailable) as ctx:
            k.encode(["a"])
        self.assertIn("kademe", str(ctx.exception).lower())

    def test_BOYUT_uyusmazligi_kurulumda_reddedilir(self):
        """Farklı uzaylardan dolan bir tablo sessizce bozulur — kurulma."""
        with self.assertRaises(ValueError) as ctx:
            KademeliEmbedder([EvrenEmbedder(api_key="sk-x", transport=_SahteUc()),
                              _YerelSahte(dim=768)])
        self.assertIn("boyut", str(ctx.exception).lower())

    def test_bos_zincir_reddedilir(self):
        with self.assertRaises(ValueError):
            KademeliEmbedder([])

    def test_available_kademelerden_HERHANGI_biri(self):
        k = KademeliEmbedder([EvrenEmbedder(api_key="", transport=_SahteUc()),
                              _YerelSahte(kullanilabilir=True)])
        self.assertTrue(k.available)
        k2 = KademeliEmbedder([EvrenEmbedder(api_key="", transport=_SahteUc()),
                               _YerelSahte(kullanilabilir=False)])
        self.assertFalse(k2.available)


class FabrikaTest(unittest.TestCase):
    """`EMBEDDING_BACKEND` hangi kademeleri kurar."""

    def _ortam(self, **kw):
        taban = {"EMBEDDING_BACKEND": "", "EVREN_API_KEY": "",
                 "EMBEDDING_MODEL_DIR": "", "EMBEDDING_MODEL": ""}
        taban.update(kw)
        return mock.patch.dict(os.environ, taban)

    def test_varsayilan_YEREL(self):
        """Geriye uyum: env verilmezse eski davranış (yalnız yerel)."""
        with self._ortam():
            e = load_embedder()
        self.assertEqual(type(e).__name__, "BgeM3Embedder")

    def test_evren_tek_kademe(self):
        with self._ortam(EMBEDDING_BACKEND="evren", EVREN_API_KEY="sk-x"):
            e = load_embedder()
        self.assertEqual(type(e).__name__, "EvrenEmbedder")

    def test_evren_yerel_zinciri(self):
        with self._ortam(EMBEDDING_BACKEND="evren,yerel", EVREN_API_KEY="sk-x"):
            e = load_embedder()
        self.assertEqual(type(e).__name__, "KademeliEmbedder")
        self.assertEqual([type(x).__name__ for x in e.kademeler],
                         ["EvrenEmbedder", "BgeM3Embedder"])

    def test_anahtarsiz_evren_kademesi_ATLANIR(self):
        with self._ortam(EMBEDDING_BACKEND="evren,yerel"):
            e = load_embedder()
        self.assertEqual(type(e).__name__, "BgeM3Embedder")

    def test_bilinmeyen_kademe_HATA(self):
        with self._ortam(EMBEDDING_BACKEND="openai"):
            with self.assertRaises(ValueError):
                load_embedder()


if __name__ == "__main__":
    unittest.main()


class BatchEnvTest(unittest.TestCase):
    """`EVREN_EMBEDDING_BATCH` — ölçüme göre ayarlanabilir, bozuk değere dayanıklı."""

    def test_env_okunur(self):
        with mock.patch.dict(os.environ, {"EVREN_EMBEDDING_BATCH": "64"}):
            self.assertEqual(EvrenEmbedder(api_key="sk-x").batch, 64)

    def test_bozuk_env_varsayilana_duser(self):
        with mock.patch.dict(os.environ, {"EVREN_EMBEDDING_BATCH": "abc"}):
            e = EvrenEmbedder(api_key="sk-x")
        self.assertGreater(e.batch, 0)

    def test_arguman_env_den_GUCLU(self):
        with mock.patch.dict(os.environ, {"EVREN_EMBEDDING_BATCH": "64"}):
            self.assertEqual(EvrenEmbedder(api_key="sk-x", batch=8).batch, 8)
