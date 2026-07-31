"""VectorRetriever + RAG gömme boru hattı testleri — SIFIR üçüncü parti bağımlılık.

İlgili: src/chatbot/rag.py (VectorRetriever, build_retriever)
        src/rag/{chunking,embedding,store,build_embeddings}.py
        docs/veri-katmani.md

## Neden sahte (fake) gömme üreticisi

bge-m3 ağırlıkları bu ortamda YOK ve teslim CI'sinde de olmayacak (çekirdek
testler bilinçli olarak hiçbir şey kurmuyor — on-prem iddiasının parçası).
Model indirmeyi test ön koşulu yapmak, testleri ya ağa bağımlı ya da sürekli
atlanan hale getirirdi.

Bu yüzden gömme üreticisi ENJEKTE EDİLİYOR: `HashingEmbedder` deterministik,
1024 boyutlu (şemadaki `vector(1024)` ile aynı) ve token torbası tabanlı —
yani anlamsal olmasa da ÖLÇÜLEBİLİR bir benzerlik üretir. Test edilen şey
model kalitesi değil, BORU HATTI: parçalama → gömme → yazma → arama →
tekilleştirme → eşik → düşme (fallback) davranışı.

Model kalitesi ayrı bir soru ve bu repoda HENÜZ ÖLÇÜLMEDİ; bu dosya onu
ölçtüğünü iddia etmez.
"""

import hashlib
import logging
import math
import os
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.chatbot import rag
from src.db.repository import Repository
from src.extraction.reconcile import build_campaign
from src.rag.build_embeddings import build_embeddings
from src.rag.chunking import chunk_text
from src.rag.embedding import EMBEDDING_DIM, EmbeddingModelUnavailable
from src.rag.store import SqliteVectorStore, open_vector_store, to_pgvector_literal

CORPUS = [
    ("kuveyt-turk", "Konut finansmanında kâr payı oranı %1,89, 120 ay vade. "
                    "Tahsis ücreti alınmaz.", "Konut Finansmanı"),
    ("albaraka", "Taşıt finansmanı kampanyası: 48 ay vade, %2,49 kâr payı, "
                 "masrafsız.", "Taşıt Finansmanı"),
    ("vakif-katilim", "Yeni müşterilere özel alışveriş puanı kampanyası. "
                      "Market alışverişlerinde puan kazanın.", "Alışveriş Puanı"),
    ("tom-katilim", "", "Kart"),   # boş metin: hiç parça üretmemeli
]


class HashingEmbedder:
    """Deterministik, bağımlılıksız sahte gömme üreticisi (1024 boyut)."""

    name = "test-hashing-embedder"
    dim = EMBEDDING_DIM

    def unavailable_reason(self):
        return None

    def encode(self, texts):
        return [self._one(t) for t in texts]

    def _one(self, text: str) -> list[float]:
        vec = [0.0] * self.dim
        for token in (text or "").lower().split():
            h = hashlib.sha256(token.encode("utf-8")).digest()
            idx = int.from_bytes(h[:4], "big") % self.dim
            vec[idx] += 1.0
        norm = math.sqrt(sum(x * x for x in vec))
        if norm == 0.0:
            # Boş metin: sıfır vektör yerine sabit bir yön (kosinüs tanımsız
            # kalmasın). Gerçek modelde de boş girdi anlamlı bir vektör verir.
            vec[0] = 1.0
            return vec
        return [x / norm for x in vec]


class MissingModelEmbedder:
    """Ağırlığı olmayan model — açık hata veren yol."""

    name = "yok/bge-m3"
    dim = EMBEDDING_DIM

    def unavailable_reason(self):
        return "ağırlık dosyası bulunamadı (test)"

    def encode(self, texts):
        raise EmbeddingModelUnavailable("ağırlık dosyası bulunamadı (test)")


def seed(repo: Repository) -> None:
    for slug, text, ctype in CORPUS:
        repo.insert_campaign(
            build_campaign(text, bank_slug=slug, campaign_type=ctype))


class TestChunking(unittest.TestCase):
    def test_bos_metin_parca_uretmez(self):
        self.assertEqual(chunk_text(""), [])
        self.assertEqual(chunk_text("   \n  "), [])

    def test_kisa_metin_tek_parca(self):
        parts = chunk_text("Konut finansmanı kâr payı %1,89.")
        self.assertEqual(len(parts), 1)

    def test_parcalar_max_chars_asmaz(self):
        text = " ".join(f"Bu {i}. cümledir ve biraz uzundur." for i in range(200))
        parts = chunk_text(text, max_chars=200, overlap_chars=40)
        self.assertGreater(len(parts), 1)
        for p in parts:
            self.assertLessEqual(len(p), 200)

    def test_uzun_tek_cumle_kaybolmaz(self):
        """max_chars'tan uzun tek cümle sessizce atılmamalı."""
        text = "A" * 500
        parts = chunk_text(text, max_chars=100, overlap_chars=0)
        self.assertEqual("".join(parts), text)

    def test_ortusme_kosulu_korur(self):
        """Örtüşme, cümle sınırında bölünen koşulun iki parçada da görünmesini sağlar."""
        text = ("İlk altı ay kâr payı sıfırdır. " + "Dolgu cümlesi burada. " * 20)
        parts = chunk_text(text, max_chars=120, overlap_chars=60)
        self.assertGreaterEqual(len(parts), 2)
        # İkinci parça birinci parçanın kuyruğundan bir şey taşımalı
        self.assertTrue(any(w in parts[1] for w in parts[0].split()[-3:]))


class TestSqliteVectorStore(unittest.TestCase):
    def setUp(self):
        self.repo = Repository(":memory:")
        seed(self.repo)
        self.store = open_vector_store(self.repo)
        self.emb = HashingEmbedder()

    def tearDown(self):
        self.repo.close()

    def test_backend_secimi(self):
        self.assertIsInstance(self.store, SqliteVectorStore)
        self.assertEqual(self.store.backend, "sqlite")

    def test_yaz_ve_ara(self):
        cid = self.repo.all_campaigns()[0]["id"]
        chunks = ["Konut finansmanı kâr payı oranı", "Tahsis ücreti alınmaz"]
        self.store.replace_campaign(cid, chunks, self.emb.encode(chunks), "test")
        self.assertEqual(self.store.count(), 2)
        hits = self.store.search(self.emb.encode(["kâr payı oranı"])[0], k=2)
        self.assertEqual(hits[0].campaign_id, cid)
        self.assertGreater(hits[0].score, hits[1].score)

    def test_yeniden_gomme_satirlari_cogaltmaz(self):
        """Aynı kampanyayı iki kez gömmek tabloyu şişirmemeli (idempotent)."""
        cid = self.repo.all_campaigns()[0]["id"]
        chunks = ["bir", "iki", "üç"]
        self.store.replace_campaign(cid, chunks, self.emb.encode(chunks), "test")
        self.store.replace_campaign(cid, chunks, self.emb.encode(chunks), "test")
        self.assertEqual(self.store.count(), 3)

    def test_parca_azalinca_eski_satirlar_silinir(self):
        cid = self.repo.all_campaigns()[0]["id"]
        cok = ["a", "b", "c", "d"]
        self.store.replace_campaign(cid, cok, self.emb.encode(cok), "test")
        az = ["a"]
        self.store.replace_campaign(cid, az, self.emb.encode(az), "test")
        self.assertEqual(self.store.count(), 1)

    def test_yanlis_boyut_hata_verir(self):
        cid = self.repo.all_campaigns()[0]["id"]
        with self.assertRaises(ValueError):
            self.store.replace_campaign(cid, ["x"], [[0.1, 0.2]], "test")

    def test_pgvector_literal_bicimi(self):
        self.assertEqual(to_pgvector_literal([1, 2.5]), "[1.0,2.5]")


class TestBuildEmbeddings(unittest.TestCase):
    def setUp(self):
        self.repo = Repository(":memory:")
        seed(self.repo)

    def tearDown(self):
        self.repo.close()

    def test_bos_metinli_kampanya_raporlanir(self):
        rapor = build_embeddings(self.repo, embedder=HashingEmbedder())
        self.assertTrue(rapor.ran)
        self.assertEqual(rapor.campaigns_seen, len(CORPUS))
        self.assertEqual(rapor.campaigns_empty, 1)         # tom-katilim
        self.assertEqual(rapor.campaigns_embedded, len(CORPUS) - 1)
        self.assertGreaterEqual(rapor.chunks_written, len(CORPUS) - 1)
        self.assertEqual(rapor.backend, "sqlite")

    def test_model_yoksa_kosulmadi_raporlanir(self):
        """Model yoksa 'tamamlandı' DEĞİL, 'koşulmadı' raporlanmalı."""
        rapor = build_embeddings(self.repo, embedder=MissingModelEmbedder())
        self.assertFalse(rapor.ran)
        self.assertIsNotNone(rapor.reason)
        self.assertEqual(rapor.chunks_written, 0)
        self.assertEqual(open_vector_store(self.repo).count(), 0)

    def test_strict_modda_model_yoksa_hata(self):
        with self.assertRaises(EmbeddingModelUnavailable):
            build_embeddings(self.repo, embedder=MissingModelEmbedder(),
                             strict=True)

    def test_limit_uygulanir(self):
        rapor = build_embeddings(self.repo, embedder=HashingEmbedder(), limit=1)
        self.assertEqual(rapor.campaigns_seen, 1)

    def test_batch_sinirinda_tum_kampanyalar_yazilir(self):
        """Küçük batch'te de hiçbir kampanya atlanmamalı (flush hatası avı)."""
        rapor = build_embeddings(self.repo, embedder=HashingEmbedder(),
                                 batch_size=1)
        self.assertEqual(rapor.campaigns_embedded, len(CORPUS) - 1)


class TestVectorRetriever(unittest.TestCase):
    def setUp(self):
        self.repo = Repository(":memory:")
        seed(self.repo)
        self.emb = HashingEmbedder()
        build_embeddings(self.repo, embedder=self.emb)

    def tearDown(self):
        self.repo.close()

    def _retriever(self, **kw):
        return rag.VectorRetriever(self.repo, embedder=self.emb,
                                   min_score=0.05, **kw)

    def test_keyword_ile_ayni_arayuz(self):
        """VectorRetriever, KeywordRetriever'ın sözleşmesini karşılamalı."""
        v = self._retriever()
        k = rag.KeywordRetriever(self.repo)
        for isim in ("retrieve", "reindex", "document_count"):
            self.assertTrue(hasattr(v, isim), isim)
            self.assertTrue(hasattr(k, isim), isim)
        pasajlar = v.retrieve("konut finansmanı kâr payı", k=2)
        self.assertTrue(pasajlar)
        for p in pasajlar:
            self.assertEqual({"bank", "source_url", "text", "score"}
                             - set(p), set())

    def test_alakali_kampanyayi_getirir(self):
        v = self._retriever()
        pasajlar = v.retrieve("konut finansmanında tahsis ücreti var mı", k=1)
        self.assertEqual(pasajlar[0]["bank"], "kuveyt-turk")

    def test_kampanya_basina_tekillestirme(self):
        """Aynı kampanyanın birden çok parçası sonucu tekelleştirmemeli."""
        cid = self.repo.all_campaigns()[0]["id"]
        parcalar = ["kâr payı oranı", "kâr payı oranı düşük", "kâr payı"]
        open_vector_store(self.repo).replace_campaign(
            cid, parcalar, self.emb.encode(parcalar), "test")
        pasajlar = self._retriever().retrieve("kâr payı oranı", k=3)
        ids = [p["bank"] for p in pasajlar]
        self.assertEqual(len(ids), len(set(ids)))

    def test_esik_altinda_pasaj_dondurmez(self):
        """Yüksek eşikte alakasız soru boş dönmeli (çekimserlik kapısı)."""
        v = rag.VectorRetriever(self.repo, embedder=self.emb, min_score=0.99)
        self.assertEqual(v.retrieve("xyzzy plugh qwerty"), [])

    def test_bos_soru_bos_doner(self):
        self.assertEqual(self._retriever().retrieve("   "), [])

    def test_bos_embeddings_tablosu_acik_hata(self):
        """Gömme yoksa sessiz boş sonuç değil, açık hata."""
        bos = Repository(":memory:")
        seed(bos)
        try:
            with self.assertRaises(rag.VectorRetrieverUnavailable):
                rag.VectorRetriever(bos, embedder=self.emb)
        finally:
            bos.close()

    def test_model_yoksa_acik_hata(self):
        with self.assertRaises(rag.VectorRetrieverUnavailable):
            rag.VectorRetriever(self.repo, embedder=MissingModelEmbedder())

    def test_bayat_gomme_uydurma_uretmez(self):
        """embeddings'te olmayan kampanyaya işaret eden satır atlanmalı."""
        v = self._retriever()
        self.repo.conn.execute(
            "INSERT INTO embeddings(campaign_id, chunk_index, chunk_text, "
            "vector, model) VALUES (?,?,?,?,?)",
            (999999, 0, "hayalet", SqliteVectorStore._pack(
                self.emb.encode(["konut finansmanı"])[0]), "test"))
        self.repo.conn.commit()
        with self.assertLogs("src.chatbot.rag", level="WARNING"):
            pasajlar = v.retrieve("konut finansmanı", k=5)
        self.assertTrue(all(p["bank"] for p in pasajlar))


class TestRetrieverSecimi(unittest.TestCase):
    """`build_retriever` — hangi yolun seçildiği GÖRÜNÜR olmalı."""

    def setUp(self):
        self.repo = Repository(":memory:")
        seed(self.repo)
        self.emb = HashingEmbedder()

    def tearDown(self):
        self.repo.close()

    def test_varsayilan_keyword(self):
        """Üretim yolu değişmedi: varsayılan hâlâ KeywordRetriever."""
        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertEqual(rag.resolve_retriever_mode(), "keyword")
        r = rag.build_retriever(self.repo, mode="keyword")
        self.assertIsInstance(r, rag.KeywordRetriever)
        self.assertEqual(getattr(r, "retriever_name", "keyword"), "keyword")

    def test_auto_gomme_varsa_vector(self):
        build_embeddings(self.repo, embedder=self.emb)
        r = rag.build_retriever(self.repo, mode="auto", embedder=self.emb)
        self.assertIsInstance(r, rag.VectorRetriever)
        self.assertEqual(r.retriever_name, "vector")

    def test_auto_gomme_yoksa_gorunur_dusme(self):
        """Düşüş SESSİZ olmamalı — WARNING loglanmalı."""
        with self.assertLogs("src.chatbot.rag", level="WARNING") as log:
            r = rag.build_retriever(self.repo, mode="auto", embedder=self.emb)
        self.assertIsInstance(r, rag.KeywordRetriever)
        self.assertIn("KeywordRetriever", "\n".join(log.output))

    def test_vector_zorunluysa_hata(self):
        """mode='vector' iken sessizce başka bir retriever döndürülmemeli."""
        with self.assertRaises(rag.VectorRetrieverUnavailable):
            rag.build_retriever(self.repo, mode="vector", embedder=self.emb)

    def test_gecersiz_mod(self):
        with self.assertRaises(ValueError):
            rag.resolve_retriever_mode("bulanik")


class TestAnswerRetrieverAlani(unittest.TestCase):
    """`RagAnswer.retriever` hangi yolun kullanıldığını taşımalı."""

    def setUp(self):
        self.repo = Repository(":memory:")
        seed(self.repo)
        self.emb = HashingEmbedder()

    def tearDown(self):
        self.repo.close()

    def test_keyword_yolu_isaretlenir(self):
        a = rag.answer(self.repo, "Taşıt finansmanı koşulları nelerdir?")
        self.assertEqual(a.retriever, "keyword")

    def test_vector_yolu_isaretlenir(self):
        build_embeddings(self.repo, embedder=self.emb)
        v = rag.VectorRetriever(self.repo, embedder=self.emb, min_score=0.05)
        a = rag.answer(self.repo, "taşıt finansmanı masrafsız", retriever=v)
        self.assertEqual(a.retriever, "vector")
        self.assertTrue(a.passages)

    def test_pasaj_yokken_de_isaretlenir(self):
        build_embeddings(self.repo, embedder=self.emb)
        v = rag.VectorRetriever(self.repo, embedder=self.emb, min_score=0.99)
        a = rag.answer(self.repo, "xyzzy plugh", retriever=v)
        self.assertEqual(a.retriever, "vector")
        self.assertEqual(a.passages, [])

    def test_geriye_uyumlu_yapici(self):
        """Mevcut `RagAnswer(text, passages)` çağrıları bozulmadı."""
        self.assertEqual(rag.RagAnswer("x", []).retriever, "keyword")


if __name__ == "__main__":
    logging.disable(logging.CRITICAL)
    unittest.main()
