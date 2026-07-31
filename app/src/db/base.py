"""Depo (repository) sözleşmesi — SQLite ve PostgreSQL uygulamalarının ortak arayüzü.

İlgili: CLAUDE.md §9 (veri modeli), ../../decisions/demo-onceden-doldurulmus-db.md
        docs/veri-katmani.md (hangi backend ne zaman)

## Neden bu dosya var

Proje iki depo uygulaması taşır:

- `repository.Repository`      — SQLite, stdlib, sıfır kurulum (offline/test yolu)
- `postgres.PostgresRepository` — PostgreSQL + pgvector (üretim yolu)

"İki backend destekliyoruz" iddiasının tek kabul kriteri, iki uygulamanın AYNI
soruya AYNI cevabı vermesidir. Bu dosya iki şeyi merkezileştirir:

1. `RepositoryProtocol` — hangi metotların sözleşmede olduğunu tip düzeyinde
   sabitler; yeni bir metot yalnızca bir backend'e eklenirse tip denetimi
   yakalar.
2. `finalize_campaign_text()` — `campaign_text()`'in span doğrulama mantığı.
   Bu mantık iki backend'de KOPYALANMAZ; kopyalansaydı biri düzeltilip diğeri
   unutulduğunda "kaynak vurgulaması" (CLAUDE.md §18 yenilikçilik hedefi #1)
   sessizce iki farklı davranış üretirdi.
3. `ThreadSafeRepository` — iki backend için ORTAK thread serileştirmesi
   (aşağıdaki sınıfın docstring'i bunun neden bir hata düzeltmesi olduğunu
   anlatır).
"""

from __future__ import annotations

import json
import threading
from typing import Any, Optional, Protocol, runtime_checkable

from ..schemas import Campaign


@runtime_checkable
class RepositoryProtocol(Protocol):
    """İki depo uygulamasının paylaştığı yüzey.

    `backend` alanı çağıranın hangi yolda olduğunu bilmesini sağlar
    ('sqlite' | 'postgres'); vektör deposu seçimi (`rag.store.open_vector_store`)
    buna bakar.
    """

    backend: str

    def upsert_bank(self, name: str, slug: str,
                    website_url: Optional[str] = None,
                    bddk_active: bool = True) -> int: ...

    def insert_campaign(self, c: Campaign, clean_text: Optional[str] = None,
                        scraped_at: Optional[str] = None) -> int: ...

    def field_value(self, campaign_id: int, field_name: str) -> Any: ...

    def query_fields(self, field_name: str) -> list[dict]: ...

    def campaign_text(self, campaign_id: int) -> Optional[dict]: ...

    def all_banks(self) -> list[dict]: ...

    def counts(self) -> dict[str, int]: ...

    def field_coverage(self) -> dict[str, int]: ...

    def campaigns_per_bank(self) -> dict[str, int]: ...

    def all_campaigns(self) -> list[dict]: ...

    def close(self) -> None: ...


def finalize_campaign_text(campaign: dict, field_rows: list[dict]) -> dict:
    """`campaign_text()` çıktısını iki backend için AYNI biçimde tamamlar.

    Girdi:
      - `campaign`: campaigns+banks JOIN satırının dict hali
        (id, raw_text, clean_text, source_url, campaign_type, bank, bank_name)
      - `field_rows`: extracted_fields satırları (canonical_value JSON METNİ olarak)

    Yaptıkları:
      - `span_reference` / `text` seçimi: span offset'leri `clean_text` üzerinde
        ölçülür. `raw_text` ile karıştırmak offset'leri kaydırır, bu yüzden
        hangi metnin kullanıldığı yanıtta açıkça belirtilir.
      - `canonical_value` JSON çözümü.
      - `span_verified`: saklanan offset gerçekten `raw_value`'yu mu gösteriyor?
        Bozuksa arayüz yanlış yeri boyamaktansa hiç boyamamalı.
    """
    d = dict(campaign)
    d["span_reference"] = "clean_text" if d.get("clean_text") else "raw_text"
    d["text"] = d.get("clean_text") or d.get("raw_text") or ""
    d["fields"] = []
    for row in field_rows:
        alan = dict(row)
        alan["canonical_value"] = json.loads(alan["canonical_value"])
        s, e = alan.get("span_start"), alan.get("span_end")
        alan["span_verified"] = bool(
            s is not None and e is not None
            and 0 <= s <= e <= len(d["text"])
            and d["text"][s:e] == (alan.get("raw_value") or ""))
        d["fields"].append(alan)
    return d


class ThreadSafeRepository:
    """Bir depoyu tek bir `RLock` arkasında serileştirir. **Hata düzeltmesi.**

    ## Neden var (SQLite tarafı)

    `sqlite3.connect()` varsayılan olarak bağlantıyı **oluşturan thread'e
    kilitler** (`check_same_thread=True`). FastAPI ise `def` (async olmayan)
    uçları bir threadpool worker'ında koşturur. Bağlantı uygulama kurulumunda
    (ana thread) açıldığı için DB'ye dokunan HER uç — `/banks`, `/campaigns`,
    `/compare`, `/chat` — istek anında şu hatayla düşüyordu:

        sqlite3.ProgrammingError: SQLite objects created in a thread can only
        be used in that same thread.

    Dashboard'un boş tablo göstermesinin sebebi buydu; arayüz `catch` ile
    sessizce boş listeye düşüyordu. Çözüm iki parçalıdır ve ikisi de gerekir:
    bağlantı `check_same_thread=False` ile açılır (`Repository(...,
    check_same_thread=False)`) VE tüm erişim burada serileştirilir.

    ## Neden Postgres tarafında da gerekir

    `psycopg` DB-API `threadsafety = 2` ilan eder: thread'ler bir bağlantıyı
    PAYLAŞABİLİR. Paylaşabilmek eşzamanlı kullanımın DOĞRU olduğu anlamına
    gelmez — işlem (transaction) sınırı bağlantı başınadır. `insert_campaign()`
    gibi metotlar sonunda `commit()` çağırdığı için, iki thread aynı bağlantıda
    çalışırsa birinin `commit()`'i diğerinin YARIM işini kalıcılaştırır ve
    `cursor` yaşam döngüleri iç içe geçer. Aynı `RLock` bu yüzden Postgres
    yolunda da uygulanır.

    ## Sınır: `conn`'a doğrudan erişen kod

    `src/rag/store.py` (`PgVectorStore` / `SqliteVectorStore`) depo nesnesinden
    `repo.conn`'u ALIR ve sorguları kendisi koşturur; o yol bu kilidin dışında
    kalır. `conn` burada bilinçli olarak açığa çıkarılır (aksi halde vektör
    deposu hiç açılamazdı) ama `lock` da açığa çıkarılır: bağlantıya doğrudan
    dokunan çağıran, `with repo.lock:` almalıdır. API demo yolu bu koda
    girmiyor (`RAG_RETRIEVER=keyword` varsayılanı), bu yüzden bugün pratikte
    tetiklenmez — ama sessiz bir varsayım olarak kalmasın diye yazılıdır.
    """

    def __init__(self, inner: RepositoryProtocol):
        self._inner = inner
        self.lock = threading.RLock()
        self.backend: str = inner.backend

    @property
    def inner(self) -> RepositoryProtocol:
        """Sarmalanan depo (testler ve backend'e özgü doğrulamalar için)."""
        return self._inner

    @property
    def conn(self) -> Any:
        """Ham bağlantı — bkz. sınıf docstring'i "Sınır" başlığı."""
        return self._inner.conn  # type: ignore[attr-defined]

    # --- sözleşme metotları (hepsi kilit altında) ---
    def upsert_bank(self, name: str, slug: str,
                    website_url: Optional[str] = None,
                    bddk_active: bool = True) -> int:
        with self.lock:
            return self._inner.upsert_bank(name, slug, website_url, bddk_active)

    def insert_campaign(self, c: Campaign, clean_text: Optional[str] = None,
                        scraped_at: Optional[str] = None) -> int:
        with self.lock:
            return self._inner.insert_campaign(c, clean_text, scraped_at)

    def field_value(self, campaign_id: int, field_name: str) -> Any:
        with self.lock:
            return self._inner.field_value(campaign_id, field_name)

    def query_fields(self, field_name: str) -> list[dict]:
        with self.lock:
            return self._inner.query_fields(field_name)

    def campaign_text(self, campaign_id: int) -> Optional[dict]:
        with self.lock:
            return self._inner.campaign_text(campaign_id)

    def all_banks(self) -> list[dict]:
        with self.lock:
            return self._inner.all_banks()

    def all_campaigns(self) -> list[dict]:
        with self.lock:
            return self._inner.all_campaigns()

    def counts(self) -> dict[str, int]:
        with self.lock:
            return self._inner.counts()

    def field_coverage(self) -> dict[str, int]:
        with self.lock:
            return self._inner.field_coverage()

    def campaigns_per_bank(self) -> dict[str, int]:
        with self.lock:
            return self._inner.campaigns_per_bank()

    def close(self) -> None:
        with self.lock:
            self._inner.close()
