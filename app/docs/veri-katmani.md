# Veri Katmanı — SQLite mi Postgres mi, ne zaman?

İlgili: `CLAUDE.md` §7 (teknoloji yığını), §9 (veri modeli), §11 (demo stratejisi)
Kod: `src/db/` (`base.py`, `repository.py`, `postgres.py`, `factory.py`, `schema.sql`),
`src/rag/`, `src/chatbot/rag.py`
Tarih: 2026-07-31

---

## 1. Neden bu belge var

31 Temmuz 2026'ya kadar mimari **slaytta** PostgreSQL + pgvector vardı, **kodda**
yoktu. Somut olarak:

| İddia | 31 Tem öncesi gerçek |
|---|---|
| `docker-compose.yml` Postgres ayağa kaldırıyor | Kaldırıyordu, ama `api` servisi `DATABASE_PATH=":memory:"` ile koşuyordu — Postgres'e **tek sorgu bile** gitmiyordu |
| `api`, Postgres'e `depends_on` ile bağlı | Bağlıydı; kullanmadığı bir servisi bekliyordu |
| `src/db/schema.sql` `embeddings(vector(1024))` tanımlıyor | Tanımlıyordu, ama **hiçbir Python kodu** o tabloya yazmıyor/okumuyordu |
| `src/rag/` "chunk → embed → retrieve" katmanı | Dizin **boştu** (yalnız `.gitkeep`) |
| `src/chatbot/rag.py` docstring'i `VectorRetriever` vaat ediyor | Sınıf **hiç yazılmamıştı** |
| `requirements.txt`: `psycopg`, `pgvector`, `sentence-transformers` | Kod tabanında **sıfır referans** |

Bu belge boşluğun nasıl kapatıldığını ve **hangi yolun ne zaman** kullanılacağını
yazar.

---

## 2. İki backend, tek sözleşme

```
                    src/db/base.py  (RepositoryProtocol + finalize_campaign_text)
                              │
              ┌───────────────┴───────────────┐
   repository.Repository            postgres.PostgresRepository
   backend = "sqlite"               backend = "postgres"
   stdlib sqlite3                   psycopg 3
   OFFLINE / TEST YOLU              ÜRETİM / VEKTÖR YOLU
                              │
                    src/db/factory.create_repository()
                    DATABASE_URL dolu -> Postgres, boş -> SQLite
```

Paylaşılan sekiz metot: `upsert_bank`, `insert_campaign`, `query_fields`,
`campaign_text`, `all_campaigns`, `counts`, `field_coverage`,
`campaigns_per_bank` (+ `field_value`, `close`).

`campaign_text()`'in span doğrulama mantığı **kopyalanmaz**: iki backend de
`base.finalize_campaign_text()` çağırır. Kopyalansaydı biri düzeltilip diğeri
unutulduğunda "kaynak vurgulaması" (CLAUDE.md §18) sessizce iki farklı davranış
üretirdi.

### SQLite bir eksiklik değil, bir karar

- Çekirdek testler ve eval katmanı **sıfır üçüncü parti bağımlılıkla** koşar.
  Bu, on-prem iddiasının parçasıdır ve CI'daki `test` işi bilinçli olarak
  hiçbir şey kurmaz.
- Jüri `docker compose up` dediğinde sistem bir veritabanı sunucusunun hazır
  olmasını **beklemez**. 4 dakikalık sunumda beklenecek tek servis bile fazladır.
- Demo, önceden doldurulmuş `data/demo.db`'den okur (CLAUDE.md §11).

### Postgres ne zaman

- `embeddings` tablosuna gerçek vektör yazılacaksa (pgvector `<=>`, IVFFlat).
- Eşzamanlı yazma / çok kullanıcılı erişim gerekiyorsa.
- Ölçek: SQLite vektör yolu **tam tarama** (O(n)) yapar; pgvector ölçek yoludur.

---

## 3. İki Compose profili

```bash
docker compose up                      # VARSAYILAN: api + web (SQLite/offline)
docker compose --profile postgres up   # + PostgreSQL 16 + pgvector
docker compose --profile gpu up        # + vLLM
docker compose --profile ollama up     # + Ollama
```

**Varsayılan profil jüri demosudur.** `postgres` servisi `profiles: ["postgres"]`
ile opt-in oldu ve `api`'nin `depends_on: postgres` bağı **kaldırıldı** — API
Postgres'e bağlanmıyor, beklemesi için de sebep yok.

`api` servisinin `DATABASE_PATH`'i `":memory:"` yerine **`data/demo.db`** oldu.
Ölçülen fark (2026-07-31, `app-api` imajı, aynı imaj iki ortam değişkeniyle):

| `DATABASE_PATH` | `GET /campaigns` kampanya sayısı |
|---|---|
| `:memory:` (eski) | **3** (fixture tohumlama) |
| `data/demo.db` (yeni) | **849** (gerçek korpus) |

`:memory:` her yeniden başlatmada 849 belgelik korpusu atıp fixture'lara
düşüyordu; jüri demoda ikinci kez yeniden başlatırsa farklı bir sistem görürdü.
`data/demo.db` yoksa (repoda gitignore'lu) API yine fixture'lardan tohumlar —
sistem çalışır, sadece korpus küçük olur.

### Postgres profilinin kanıtı

```bash
docker compose --profile postgres up -d postgres
docker compose --profile postgres run --rm db-check
```

`db-check` tek seferlik bir servistir ve teslim API imajının **içinde**
`tests/test_pgvector_repository.py`'yi koşturur (`tests/` ve `psycopg[binary]`
o imajda zaten var). Ön koşul yoksa testler **atlanır** — "geçti" demez.

---

## 4. RAG / pgvector yolu

```
kampanya metni
   └─ src/rag/chunking.chunk_text()      cümle sınırlı, 800 karakter, 120 örtüşme
        └─ src/rag/embedding.BgeM3Embedder  BAAI/bge-m3, 1024 boyut, L2-normalize
             └─ src/rag/store.PgVectorStore   INSERT ... CAST(%s AS vector)
                  └─ embeddings tablosu       UNIQUE(campaign_id, chunk_index)
                       └─ src/chatbot/rag.VectorRetriever   `<=>` kosinüs araması
```

Üretim komutu:

```bash
DATABASE_URL=postgresql://anatolia:anatolia@localhost:5432/anatolia \
  python3 -m src.rag.build_embeddings
```

### Model yoksa ne olur

`sentence-transformers` ya da bge-m3 ağırlığı yoksa:

- `BgeM3Embedder.encode()` **`EmbeddingModelUnavailable`** yükseltir; sessizce
  boş vektör dönmez.
- `build_embeddings` **`ran=False`** raporu döner, çıkış kodu **3**, tabloya
  **sıfır satır** yazılır. "Gömme tamamlandı" demez.
- `VectorRetriever` kurulamaz (`VectorRetrieverUnavailable`).
- `build_retriever(mode="auto")` **`KeywordRetriever`'a düşer** ve düşüşü
  `logging.WARNING` ile bildirir.
- `build_retriever(mode="vector")` **hata yükseltir** — operatör vektör yolunu
  zorunlu kıldıysa sessizce başka bir sistem çalıştırmak yanlış olurdu.

Ayrıca `local_files_only=True` varsayılandır: kod kendiliğinden internete
çıkmaz (CLAUDE.md §1 offline kısıtı).

### `KeywordRetriever` üretim yolu olarak KALIR

`RAG_RETRIEVER` ortam değişkeni:

| Değer | Davranış |
|---|---|
| `keyword` (**varsayılan**) | Yalnız `KeywordRetriever`. Üretim yolu değişmedi. |
| `auto` | `VectorRetriever` dene; olmazsa görünür biçimde `KeywordRetriever`'a düş. |
| `vector` | `VectorRetriever` zorunlu; kurulamazsa hata. |

Gerekçe: `KeywordRetriever` bugün 1696 belgelik korpusta p99 **12,18 ms** ve
54 soruda eski/yeni birebir eşdeğerliği kanıtlanmış durumda. Vektör yolunun
ölçülmüş bir kazancı **henüz yok** (bge-m3 ağırlıkları bu ortamda indirilmedi),
ve ölçülmemiş bir iddiayla üretim yolunu değiştirmek yanlış olurdu.

Hangi retriever'ın kullanıldığı `RagAnswer.retriever` alanında taşınır.

---

## 5. Ölçülen sonuçlar (2026-07-31)

Aşağıdakiler **gerçekten koşturuldu**. Koşulmayanlar §6'da.

### 5.1 Postgres + pgvector parite testleri

`pgvector/pgvector:pg16@sha256:a362508...` (compose'daki digest'in aynısı),
psycopg 3.3.4.

| Koşu | Sonuç |
|---|---|
| `python -m unittest tests.test_pgvector_repository` (host) | **27/27 OK** |
| `docker compose --profile postgres run --rm db-check` (konteyner içi) | **27/27 OK** |
| `python3 -m unittest discover -s tests` (sistem python3, psycopg YOK) | **835 test OK, 29 atlandı** |
| `python -m unittest discover -s tests` (.venv, Postgres AÇIK) | **835 test OK, 0 atlandı** |

Sistem python3 koşusunda atlananlar: 3 (fastapi yok — 31 Tem öncesinde de
atlanıyordu) + 26 (psycopg/Postgres yok).
**Atlamak ile "geçti" demek farklı şeylerdir** — atlananlar raporda görünür.

### 5.2 Gerçek korpus ölçeği (849 belge)

`data/demo.db` → Postgres kopyalama + gömme + arama:

| Ölçüm | Değer |
|---|---|
| Kopyalanan kampanya / alan | 849 / 2204 (SQLite `counts()` ile **birebir aynı**) |
| Kopyalama süresi | 1,0 s |
| Üretilen parça (chunk) | **6376** |
| `embeddings` tablosuna yazma | 2,166 s |
| pgvector arama gecikmesi (n=50) | medyan **16,49 ms**, p95 **17,31 ms**, maks 42,40 ms |

> **DÜRÜSTLÜK NOTU:** bu ölçüm bge-m3 ile **yapılmadı**. Kullanılan gömme
> üreticisi `tests/test_vector_retriever.HashingEmbedder` — deterministik,
> 1024 boyutlu bir hash torbası. Ölçülen şey **veri katmanı + pgvector
> yazma/arama yolunun gerçek korpus ölçeğinde çalıştığı**; **model kalitesi
> DEĞİL**. Getirilen pasajlar anlamsal olarak zayıftır ve öyle olmaları
> beklenir. bge-m3 ile gerçek gecikme, model çıkarım süresi kadar daha
> yüksek olacaktır.

---

## 6. Koşturulamayanlar

| Ne | Neden |
|---|---|
| bge-m3 ile gerçek gömme üretimi | Ağırlıklar bu ortamda yok; `local_files_only=True` gereği kod indirmeye çalışmaz. Kod yolu `HashingEmbedder` ile uçtan uca test edildi, model yolu edilmedi. |
| `VectorRetriever` alaka (relevance) kalitesi | Yukarıdakinin sonucu. `VectorRetriever.DEFAULT_MIN_SCORE = 0.5` **kalibre edilmiş bir eşik değildir**, muhafazakâr bir başlangıç değeridir. |
| `KeywordRetriever` vs `VectorRetriever` ablasyonu | Aynı sebep. Ablasyon yapılmadan üretim yolu değiştirilmedi. |
| IVFFlat dizininin fayda ölçümü | 6376 satırda IVFFlat yaklaşık aramadır ve tam taramadan hızlı olmayabilir. Dizin **doğruluk ön koşulu değildir**; `search()` dizinsiz de doğru çalışır. |

---

## 7. Açık uç: API bağlanma noktası

`src/api/main.py` hâlâ `Repository(DATABASE_PATH)` kuruyor; `create_repository()`
fabrikasını **kullanmıyor**. Yani bugün `DATABASE_URL` verilse bile API onu
okumaz. Bu yüzden `docker-compose.yml`'de `api` servisine `DATABASE_URL`
**bilerek yazılmadı** — kodun okumadığı bir ayarı ilan etmek, tam da bu belgenin
§1'de anlattığı hatanın tekrarı olurdu.

Bağlamak için gereken değişiklik `src/api/main.py` içinde tek satırdır
(`ApiRepository`'nin `Repository` alt sınıfı olmasıyla birlikte ele alınmalı):

```python
# şu an:
repo = ApiRepository(DB_PATH)
# hedef:
repo = create_repository()          # DATABASE_URL varsa Postgres
```

`ApiRepository` SQLite'a özgü yardımcılar (`rows()`, `_SQLITE_SCHEMA`, `?`
yer tutucuları) taşıdığı için bu, API sahibinin yapması gereken ayrı bir iştir.

---

## 8. Kapsam dışı bulgu: korpusta ikili (binary) belge

Gerçek korpusu Postgres'e aktarırken SQLite'ın sessizce yuttuğu bir veri hatası
ortaya çıktı: **849 belgeden 1'i** metin değil ikili çöp.

- Belge: `kuveyt-turk`,
  `.../kisisel-verilerle-ilgili-aydinlatma---finansman-is-3895.pdf`
- İçerik: **352 adet NUL (0x00) baytı** — bir PDF'in metin olarak
  ayrıştırılamamış hali `.txt` olarak korpusa girmiş.
- Çıkarılan alan sayısı: **0** (bu yüzden SQLite yolunda hiç görünmüyordu).

PostgreSQL `TEXT` sütunları NUL kabul etmez, SQLite eder. `PostgresRepository`
artık psycopg'nin kriptik `DataError`'ı yerine **hangi bankanın hangi belgesinin**
bozuk olduğunu söyleyen `NulByteInText` hatası verir. `on_nul="strip"` ile
temizlenebilir ama temizlik **karakter offset'lerini kaydırır** (span
doğrulaması bozulabilir), bu yüzden varsayılan değildir.

**Asıl çözüm bu katmanda değil:** PDF'in metne çevrilmesi ya da korpustan
elenmesi `src/scraping/` veya `src/preprocessing/` sorumluluğundadır.

---

## 9. Bağımlılık listesinde ne değişti

| Paket | Önce | Sonra | Gerekçe |
|---|---|---|---|
| `zeyrek` | yorumlu, "kullanılmıyor" | **kaldırıldı** | TR ihtiyaçlarını `preprocessing.clean.tr_fold` + `extraction/rules/synonyms.py` saf stdlib ile karşılıyor |
| `psycopg[binary]` | ilan edilmiş, sıfır referans | **gerçekten kullanılıyor** | `src/db/postgres.py` |
| `pgvector` (Python paketi) | ilan edilmiş, sıfır referans | **kaldırıldı** | Sunucu tarafı pgvector **eklentisi** kullanılmaya devam ediyor; Python istemcisi gereksiz — vektör pgvector'ün metin biçimiyle gönderilip `CAST(... AS vector)` ile dönüştürülüyor |
| `sentence-transformers` | ilan edilmiş, sıfır referans | **gerçekten kullanılıyor** | `src/rag/embedding.py` (ince API imajında bilerek yok) |

Şartname §9 "bağımlılıkların eksiksiz listesi" istiyor; kullanılmayan bağımlılık
ilan etmek listeyi yanıltıcı yapar.
