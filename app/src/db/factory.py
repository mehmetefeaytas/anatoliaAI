"""Depo seçimi — `DATABASE_URL` varsa Postgres, yoksa SQLite.

İlgili: docs/veri-katmani.md, CLAUDE.md §9
        base.py (sözleşme), repository.py (SQLite), postgres.py (Postgres)

## Seçim kuralı (tek yerde)

    DATABASE_URL dolu  -> PostgresRepository(DATABASE_URL)     [üretim / pgvector]
    DATABASE_URL boş   -> Repository(DATABASE_PATH | ':memory:') [offline / test]

İki ortam değişkeni de bilerek destekleniyor: teslim edilen demo
`DATABASE_PATH=data/demo.db` ile 849 belgelik önceden doldurulmuş dosyadan
okur (CLAUDE.md §11) ve hiçbir sunucu beklemez; Postgres profili aynı kodu
`DATABASE_URL` ile çalıştırır.

## Sessiz düşme (silent fallback) YOK

`DATABASE_URL` verilip `psycopg` kurulu değilse `PsycopgUnavailable` yükselir.
Bu bilinçlidir: operatör Postgres istediğini söylemişken verinin sessizce
geçici bir SQLite dosyasına yazılması, bu projede daha önce yaşanmış
"bağlantı hatasını BAŞARILI raporlama" hatasının aynısı olurdu.

## `thread_safe=True` — çok thread'li sunucu yolu

FastAPI `def` uçlarını bir threadpool'da koşturur. NE `sqlite3` NE `psycopg`
bağlantısı bu kullanım için güvenlidir (gerekçeleri
`base.ThreadSafeRepository` docstring'inde). `thread_safe=True` iki backend
için de tek bir doğru kurulum üretir:

    sqlite   -> Repository(path, check_same_thread=False) + RLock sarmalayıcı
    postgres -> PostgresRepository(url)                   + RLock sarmalayıcı

Betikler ve testler (tek thread) bayrağı vermez; ek kilit maliyeti ödemezler.
"""

from __future__ import annotations

import os
from typing import Optional

from .base import RepositoryProtocol, ThreadSafeRepository
from .repository import Repository


def resolve_database_url(database_url: Optional[str] = None) -> str:
    """Etkin `DATABASE_URL` (boş dize = Postgres istenmiyor)."""
    if database_url is not None:
        return database_url.strip()
    return os.environ.get("DATABASE_URL", "").strip()


def create_repository(database_url: Optional[str] = None,
                      database_path: Optional[str] = None,
                      *, thread_safe: bool = False) -> RepositoryProtocol:
    """Ortama göre depo örneği üretir.

    Argümanlar verilmezse ortam değişkenlerinden okunur; testler argümanla
    çağırarak ortamdan bağımsız kalabilir.

    Args:
        thread_safe: `True` ise depo `base.ThreadSafeRepository` ile sarılır ve
            SQLite bağlantısı `check_same_thread=False` ile açılır (FastAPI
            threadpool yolu — bkz. modül başlığı).
    """
    url = resolve_database_url(database_url)
    if url:
        # Tembel import: `psycopg` kurulu olmayan offline ortamda bu modülün
        # import edilmesi bile hata vermemeli (çekirdek testler sıfır üçüncü
        # parti bağımlılıkla koşuyor).
        from .postgres import PostgresRepository

        pg = PostgresRepository(url)
        return ThreadSafeRepository(pg) if thread_safe else pg
    path = (database_path if database_path is not None
            else os.environ.get("DATABASE_PATH", ":memory:"))
    if thread_safe:
        return ThreadSafeRepository(
            Repository(path, check_same_thread=False))
    return Repository(path)
