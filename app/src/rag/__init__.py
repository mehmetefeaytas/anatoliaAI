"""RAG katmanı — chunk → embed → store → retrieve.

İlgili: CLAUDE.md §8 (src/rag/), §7 (bge-m3 + pgvector)
        ../chatbot/rag.py (VectorRetriever / KeywordRetriever)
        docs/veri-katmani.md

Bu paket 31 Tem 2026'ya kadar BOŞTU (yalnız .gitkeep) — mimari diyagramda RAG
vardı, kodda yoktu. İçerik:

- `chunking`         : TR-duyarlı, sıfır bağımlılıklı parçalama
- `embedding`        : bge-m3 sarmalayıcı; model yoksa AÇIK hata
- `store`            : pgvector (üretim) + SQLite tam tarama (offline/test)
- `build_embeddings` : `embeddings` tablosunu dolduran betik/CLI

`embedding` ve `store` alt modülleri BURADA import edilmez; ağır/opsiyonel
bağımlılıkları olan yolların `import src.rag` ile tetiklenmemesi için.
"""

__all__ = ["build_embeddings", "chunking", "embedding", "store"]
