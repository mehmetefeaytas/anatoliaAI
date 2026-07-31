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
"""

from __future__ import annotations

import json
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
