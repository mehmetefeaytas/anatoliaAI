"""Gömme üretimi: kampanya metinleri → parça → vektör → `embeddings` tablosu.

İlgili: CLAUDE.md §8 (src/rag), §9 (embeddings tablosu), docs/veri-katmani.md

Kullanım:

    # Postgres + pgvector (üretim yolu)
    DATABASE_URL=postgresql://anatolia:anatolia@localhost:5432/anatolia \\
        python3 -m src.rag.build_embeddings

    # SQLite (offline test yolu)
    python3 -m src.rag.build_embeddings --database-path data/demo.db

## Model yoksa "koşulmadı" diye raporlanır

Ağırlık yoksa betik sıfır satır yazar, çıkış kodu 3 döner ve raporun `ran`
alanı False olur. Boş bir tabloyu "gömme tamamlandı" diye raporlamak, bu
projede daha önce yaşanmış "bağlantı hatasını BAŞARILI raporlama" hatasının
aynısı olurdu. `--strict` ile aynı durum hata (exception) yapılabilir.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import asdict, dataclass, field
from typing import Callable, Optional, Sequence

from ..db.factory import create_repository
from .chunking import DEFAULT_CHUNK_CHARS, DEFAULT_OVERLAP_CHARS, chunk_text
from .embedding import Embedder, EmbeddingModelUnavailable, load_embedder
from .store import VectorStore, open_vector_store


@dataclass
class EmbeddingBuildReport:
    """Ölçülen sayılar — tahmin yok."""

    ran: bool
    backend: str
    model: str
    campaigns_seen: int = 0
    campaigns_embedded: int = 0
    campaigns_empty: int = 0     # metni boş → gömülecek parça yok
    chunks_written: int = 0
    elapsed_s: float = 0.0
    reason: Optional[str] = None   # ran=False ise neden
    errors: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return asdict(self)


def build_embeddings(repo, embedder: Optional[Embedder] = None,
                     store: Optional[VectorStore] = None,
                     *, batch_size: int = 16, limit: Optional[int] = None,
                     max_chars: int = DEFAULT_CHUNK_CHARS,
                     overlap_chars: int = DEFAULT_OVERLAP_CHARS,
                     strict: bool = False,
                     on_progress: Optional[Callable[[int, int], None]] = None,
                     ) -> EmbeddingBuildReport:
    """Depodaki tüm kampanyaları parçalayıp gömer ve vektör deposuna yazar.

    `embedder` verilmezse bge-m3 denenir. Model yoksa `strict=False` iken
    `ran=False` raporu döner (exception yok), `strict=True` iken
    `EmbeddingModelUnavailable` yükselir.
    """
    store = store or open_vector_store(repo)
    embedder = embedder or load_embedder()
    model_name = getattr(embedder, "name", "?")
    report = EmbeddingBuildReport(ran=False, backend=store.backend,
                                  model=model_name)

    reason = _unavailable_reason(embedder)
    if reason is not None:
        if strict:
            raise EmbeddingModelUnavailable(reason)
        report.reason = reason
        return report

    t0 = time.perf_counter()
    campaigns = repo.all_campaigns()
    if limit is not None:
        campaigns = campaigns[:limit]
    report.ran = True
    report.campaigns_seen = len(campaigns)

    pending: list[tuple[int, list[str]]] = []
    pending_chunks = 0
    for i, c in enumerate(campaigns, start=1):
        chunks = chunk_text(c.get("raw_text") or "", max_chars=max_chars,
                            overlap_chars=overlap_chars)
        if not chunks:
            report.campaigns_empty += 1
        else:
            pending.append((int(c["id"]), chunks))
            pending_chunks += len(chunks)
        if pending_chunks >= batch_size:
            _flush(pending, embedder, store, model_name, report)
            pending, pending_chunks = [], 0
        if on_progress is not None:
            on_progress(i, len(campaigns))
    if pending:
        _flush(pending, embedder, store, model_name, report)

    report.elapsed_s = round(time.perf_counter() - t0, 3)
    return report


def _unavailable_reason(embedder: Embedder) -> Optional[str]:
    """Gömme üreticisi kullanılabilir mi; değilse insan-okur sebep."""
    probe = getattr(embedder, "unavailable_reason", None)
    if callable(probe):
        return probe()
    try:
        embedder.encode(["ön kontrol"])
    except EmbeddingModelUnavailable as e:
        return str(e)
    return None


def _flush(pending: Sequence[tuple[int, list[str]]], embedder: Embedder,
           store: VectorStore, model_name: str,
           report: EmbeddingBuildReport) -> None:
    """Biriken parçaları tek `encode()` çağrısıyla gömüp yazar."""
    if not pending:
        return
    flat: list[str] = []
    for _, chunks in pending:
        flat.extend(chunks)
    vectors = embedder.encode(flat)
    if len(vectors) != len(flat):
        raise RuntimeError(
            f"Gömme sayısı ({len(vectors)}) parça sayısıyla ({len(flat)}) "
            "uyuşmuyor; model beklenmedik çıktı verdi.")
    offset = 0
    for campaign_id, chunks in pending:
        vecs = vectors[offset:offset + len(chunks)]
        offset += len(chunks)
        written = store.replace_campaign(campaign_id, chunks, vecs, model_name)
        report.campaigns_embedded += 1
        report.chunks_written += written


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def _parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="python3 -m src.rag.build_embeddings",
        description="Kampanya metinlerini bge-m3 ile gömüp embeddings "
                    "tablosuna yazar (Postgres/pgvector veya SQLite).")
    p.add_argument("--database-url", default=None,
                   help="Postgres DSN. Verilmezse DATABASE_URL ortam değişkeni.")
    p.add_argument("--database-path", default=None,
                   help="SQLite dosyası (DATABASE_URL yokken).")
    p.add_argument("--limit", type=int, default=None,
                   help="Yalnızca ilk N kampanya (duman testi).")
    p.add_argument("--batch-size", type=int, default=16)
    p.add_argument("--max-chars", type=int, default=DEFAULT_CHUNK_CHARS)
    p.add_argument("--overlap-chars", type=int, default=DEFAULT_OVERLAP_CHARS)
    p.add_argument("--strict", action="store_true",
                   help="Model yoksa hata yükselt (sessiz 'koşulmadı' yerine).")
    p.add_argument("--json", action="store_true", help="Raporu JSON olarak bas.")
    return p.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None, stream=None) -> int:
    """Çıkış kodları: 0 = koşuldu, 3 = model yok (koşulmadı), 2 = boş depo."""
    args = _parse_args(argv)
    stream = stream if stream is not None else sys.stderr
    repo = create_repository(args.database_url, args.database_path)
    try:
        if repo.counts().get("campaigns", 0) == 0:
            print("HATA: depoda hiç kampanya yok. Önce "
                  "`python3 -m scripts.build_demo_db` ile doldurun.", file=stream)
            return 2
        report = build_embeddings(
            repo, batch_size=args.batch_size, limit=args.limit,
            max_chars=args.max_chars, overlap_chars=args.overlap_chars,
            strict=args.strict)
    finally:
        repo.close()

    if args.json:
        # Makine-okur rapor STDOUT'a; insan-okur özet stderr'e.
        sys.stdout.write(
            json.dumps(report.as_dict(), ensure_ascii=False, indent=2) + "\n")
    elif report.ran:
        print(f"Gömme tamamlandı ({report.backend}, model={report.model}): "
              f"{report.campaigns_embedded}/{report.campaigns_seen} kampanya, "
              f"{report.chunks_written} parça, {report.elapsed_s}s "
              f"(boş metin: {report.campaigns_empty})", file=stream)
    else:
        print("KOŞULMADI — gömme modeli yok, embeddings tablosuna hiçbir satır "
              f"yazılmadı.\nSebep: {report.reason}\n"
              "Sistem bu durumda KeywordRetriever ile çalışmaya devam eder "
              "(src/chatbot/rag.build_retriever).", file=stream)
    return 0 if report.ran else 3


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
