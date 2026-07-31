"""Veri katmanı — iki backend, tek sözleşme.

    from src.db import create_repository
    repo = create_repository()      # DATABASE_URL varsa Postgres, yoksa SQLite

Detay: docs/veri-katmani.md

`postgres` alt modülü BİLEREK burada import EDİLMEZ; `psycopg` kurulu olmayan
offline ortamda `import src.db` çökmemeli.
"""

from .base import RepositoryProtocol, finalize_campaign_text
from .factory import create_repository, resolve_database_url
from .repository import Repository

__all__ = [
    "Repository",
    "RepositoryProtocol",
    "create_repository",
    "finalize_campaign_text",
    "resolve_database_url",
]
