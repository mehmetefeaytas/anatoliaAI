"""Vektör deposu — pgvector (üretim) + SQLite tam tarama (offline/test).

İlgili: ../db/schema.sql (embeddings tablosu), CLAUDE.md §7, §9
        docs/veri-katmani.md

İki uygulama aynı `VectorStore` sözleşmesini paylaşır:

- `PgVectorStore`     — PostgreSQL + pgvector, kosinüs mesafesi `<=>` operatörü,
                        IVFFlat dizini. ÖLÇEK YOLU.
- `SqliteVectorStore` — float32 BLOB + saf Python tam tarama. Postgres olmadan
                        VectorRetriever'ı test edilebilir kılar; O(n) olduğu
                        için üretim yolu DEĞİLDİR.

pgvector'ün Python paketi (`pgvector`) BİLEREK kullanılmıyor: vektör, pgvector'ün
belgelenmiş metin biçimiyle ('[0.1,0.2,...]') gönderilip sunucuda `::vector`'e
çevriliyor. Böylece bir bağımlılık daha ilan etmeden aynı iş yapılıyor
(şartname §9 "bağımlılıkların eksiksiz listesi" — kullanılmayan bağımlılık
ilan etmek listeyi yanıltıcı yapar).
"""

from __future__ import annotations

import array
import math
from dataclasses import dataclass
from typing import Optional, Protocol, Sequence

from .embedding import EMBEDDING_DIM


@dataclass(frozen=True)
class VectorHit:
    """Bir arama sonucu."""

    campaign_id: int
    chunk_index: int
    chunk_text: str
    score: float          # kosinüs benzerliği, [-1, 1]; büyük = daha yakın


class VectorStore(Protocol):
    """Vektör deposu sözleşmesi."""

    backend: str
    dim: int

    def replace_campaign(self, campaign_id: int, chunks: Sequence[str],
                         vectors: Sequence[Sequence[float]],
                         model: str) -> int: ...

    def search(self, vector: Sequence[float], k: int = 5) -> list[VectorHit]: ...

    def count(self) -> int: ...

    def clear(self) -> None: ...


def to_pgvector_literal(vector: Sequence[float]) -> str:
    """Vektörü pgvector metin biçimine çevirir: '[0.1,0.2,...]'."""
    return "[" + ",".join(repr(float(x)) for x in vector) + "]"


def _check_dim(vector: Sequence[float], dim: int) -> None:
    if len(vector) != dim:
        raise ValueError(
            f"Vektör boyutu {len(vector)}, beklenen {dim}. "
            "Şema vector(1024) ile sabit; karışık boyutlu korpus arama "
            "sonuçlarını sessizce bozar.")


# --------------------------------------------------------------------------- #
# PostgreSQL + pgvector
# --------------------------------------------------------------------------- #
class PgVectorStore:
    """pgvector destekli vektör deposu. `PostgresRepository` bağlantısını kullanır."""

    backend = "postgres"

    def __init__(self, repo, dim: int = EMBEDDING_DIM):
        self.repo = repo
        self.conn = repo.conn
        self.dim = dim

    def replace_campaign(self, campaign_id: int, chunks: Sequence[str],
                         vectors: Sequence[Sequence[float]],
                         model: str) -> int:
        """Bir kampanyanın TÜM parçalarını değiştirir (idempotent yeniden gömme).

        Önce siler, sonra yazar: `UNIQUE(campaign_id, chunk_index)` çakışmasına
        güvenmek, parça sayısı azaldığında eski fazlalık satırları bırakırdı.
        """
        if len(chunks) != len(vectors):
            raise ValueError("chunks ve vectors aynı uzunlukta olmalı")
        for v in vectors:
            _check_dim(v, self.dim)
        with self.conn.cursor() as cur:
            cur.execute("DELETE FROM embeddings WHERE campaign_id=%s",
                        (campaign_id,))
            rows = [(campaign_id, i, text, to_pgvector_literal(vec), model)
                    for i, (text, vec) in enumerate(zip(chunks, vectors, strict=True))]
            if rows:
                cur.executemany(
                    "INSERT INTO embeddings(campaign_id, chunk_index, chunk_text, "
                    "vector, model) VALUES (%s,%s,%s,CAST(%s AS vector),%s)", rows)
        self.conn.commit()
        return len(chunks)

    def search(self, vector: Sequence[float], k: int = 5) -> list[VectorHit]:
        """En yakın k parça (kosinüs). `<=>` kosinüs MESAFESİDİR: benzerlik = 1 - d."""
        _check_dim(vector, self.dim)
        with self.conn.cursor() as cur:
            cur.execute(
                "SELECT campaign_id, chunk_index, chunk_text, "
                "1 - (vector <=> CAST(%s AS vector)) AS score "
                "FROM embeddings WHERE vector IS NOT NULL "
                "ORDER BY vector <=> CAST(%s AS vector), campaign_id, chunk_index "
                "LIMIT %s",
                (to_pgvector_literal(vector), to_pgvector_literal(vector), k))
            rows = cur.fetchall()
        return [VectorHit(int(r["campaign_id"]), int(r["chunk_index"]),
                          r["chunk_text"] or "", float(r["score"])) for r in rows]

    def count(self) -> int:
        with self.conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) AS n FROM embeddings")
            return int(cur.fetchone()["n"])

    def clear(self) -> None:
        with self.conn.cursor() as cur:
            cur.execute("DELETE FROM embeddings")
        self.conn.commit()


# --------------------------------------------------------------------------- #
# SQLite tam tarama
# --------------------------------------------------------------------------- #
class SqliteVectorStore:
    """SQLite BLOB + saf Python kosinüs. Offline/test yolu; O(n)."""

    backend = "sqlite"

    def __init__(self, repo, dim: int = EMBEDDING_DIM):
        self.repo = repo
        self.conn = repo.conn
        self.dim = dim

    @staticmethod
    def _pack(vector: Sequence[float]) -> bytes:
        return array.array("f", [float(x) for x in vector]).tobytes()

    @staticmethod
    def _unpack(blob: bytes) -> list[float]:
        a = array.array("f")
        a.frombytes(blob)
        return list(a)

    def replace_campaign(self, campaign_id: int, chunks: Sequence[str],
                         vectors: Sequence[Sequence[float]],
                         model: str) -> int:
        if len(chunks) != len(vectors):
            raise ValueError("chunks ve vectors aynı uzunlukta olmalı")
        for v in vectors:
            _check_dim(v, self.dim)
        self.conn.execute("DELETE FROM embeddings WHERE campaign_id=?",
                          (campaign_id,))
        self.conn.executemany(
            "INSERT INTO embeddings(campaign_id, chunk_index, chunk_text, "
            "vector, model) VALUES (?,?,?,?,?)",
            [(campaign_id, i, text, self._pack(vec), model)
             for i, (text, vec) in enumerate(zip(chunks, vectors, strict=True))])
        self.conn.commit()
        return len(chunks)

    def search(self, vector: Sequence[float], k: int = 5) -> list[VectorHit]:
        _check_dim(vector, self.dim)
        query = [float(x) for x in vector]
        qnorm = math.sqrt(sum(x * x for x in query)) or 1.0
        hits: list[VectorHit] = []
        for row in self.conn.execute(
                "SELECT campaign_id, chunk_index, chunk_text, vector "
                "FROM embeddings WHERE vector IS NOT NULL "
                "ORDER BY campaign_id, chunk_index"):
            stored = self._unpack(row["vector"])
            if len(stored) != self.dim:
                # Karışık boyut = bozuk korpus. Sessizce atlamak yanlış
                # sıralama üretirdi; açıkça hata veriyoruz.
                raise ValueError(
                    f"embeddings satırı (campaign_id={row['campaign_id']}, "
                    f"chunk_index={row['chunk_index']}) {len(stored)} boyutlu, "
                    f"beklenen {self.dim}. Depoyu yeniden gömün.")
            dnorm = math.sqrt(sum(x * x for x in stored)) or 1.0
            score = sum(a * b for a, b in zip(query, stored, strict=True)) / (qnorm * dnorm)
            hits.append(VectorHit(int(row["campaign_id"]),
                                  int(row["chunk_index"]),
                                  row["chunk_text"] or "", score))
        # Kararlı sıralama: eşit skorda campaign_id/chunk_index sırası korunur
        # (yukarıdaki ORDER BY + Python'un stable sort'u).
        hits.sort(key=lambda h: h.score, reverse=True)
        return hits[:k]

    def count(self) -> int:
        return int(self.conn.execute("SELECT COUNT(*) FROM embeddings").fetchone()[0])

    def clear(self) -> None:
        self.conn.execute("DELETE FROM embeddings")
        self.conn.commit()


def open_vector_store(repo, dim: int = EMBEDDING_DIM) -> VectorStore:
    """Deponun backend'ine uygun vektör deposunu açar."""
    backend: Optional[str] = getattr(repo, "backend", None)
    if backend == "postgres":
        return PgVectorStore(repo, dim=dim)
    if backend == "sqlite":
        return SqliteVectorStore(repo, dim=dim)
    raise ValueError(
        f"Bilinmeyen depo backend'i: {backend!r}. "
        "Vektör deposu yalnızca 'postgres' ve 'sqlite' için tanımlı.")
