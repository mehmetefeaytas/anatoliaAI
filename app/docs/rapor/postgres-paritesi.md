---
title: "Postgres paritesi ölçüldü — 53 atlanan test koştu"
tags: [on-prem, test, veritabani, parite]
date: 2026-08-08
status: stable
---

# Postgres paritesi (2026-08-08)

Denetimin kod/mimari hakemi üç açık saymıştı; bu, üçüncüsüydü:

> *"Postgres paritesi varsayılan koşumda **hiç doğrulanmıyor** — 53 testin
> tamamı atlanıyor, `postgres.py` kapsamı %20,4."*

## Ne yapıldı

`docker-compose.yml` **değiştirilmedi**. Yerel makinede 5432'yi dinleyen
başka bir Postgres olduğu ölçüldü:

```
com.docke  ... TCP *:5432 (LISTEN)          <- konteyner (IPv6 joker)
postgres   ... TCP 127.0.0.1:5432 (LISTEN)  <- YEREL kurulum
```

Yerel sunucu `127.0.0.1`'e özel bağlandığı için `localhost` bağlantılarını o
karşılıyor ve `role "anatolia" does not exist` hatası veriyordu. Yani konteyner
ayaktayken bile testler onunla konuşmuyordu. Teslim dosyasına dokunmamak için
test konteyneri **55432**'ye alındı; şema yine tek doğruluk kaynağından
(`src/db/schema.sql`) initdb ile uygulandı.

```bash
docker run -d --name anatolia-pg-test \
  -e POSTGRES_USER=anatolia -e POSTGRES_PASSWORD=anatolia -e POSTGRES_DB=anatolia \
  -p 55432:5432 \
  -v "$PWD/src/db/schema.sql:/docker-entrypoint-initdb.d/schema.sql:ro" \
  pgvector/pgvector:pg16

ANATOLIA_TEST_DATABASE_URL="postgresql://anatolia:anatolia@localhost:55432/anatolia" \
  .venv/bin/python -m unittest discover -s tests
```

## Sonuç

| | önce | sonra |
|---|---:|---:|
| atlanan test | **53** | **0** |
| koşan test | 1.611 | **1.664** |
| `src/db/postgres.py` satır kapsamı | %20,4 | **%80,4** (193/240) |
| toplam kapsam | %67,7 | **%68,5** |

Hiçbir parite testi başarısız olmadı. İki backend aynı korpusu aynı sırayla
yazıp aynı sonuçları döndürüyor — bu, `ORDER BY f.id` gibi daha önce yalnız
Postgres yolunda bulunan ayrıntıların artık gerçekten doğrulandığı anlamına
geliyor.

## Yanında kapatılan şema ayrışması

`schema.sql` (Postgres) `extractor` sütununda `CHECK (extractor IN
('rule','ner','llm'))` taşıyordu; `_SQLITE_SCHEMA` **taşımıyordu**. Bedeli
somut: SQLite yolunda geçersiz bir `extractor` değeri sessizce yazılır,
Postgres yolunda aynı yazma hata verir — yani iki backend **aynı veriyi kabul
etmez** ve "parite" testi backend'e göre farklı davranır.

Kısıt SQLite tarafına taşındı (`extractor IS NULL OR extractor IN (...)`;
`NULL` bilerek serbest — alan opsiyoneldir). Mevcut korpusta ihlal yok:
5.455 kaydın tamamı `'rule'`.

Bu, bu oturumda kapatılan **dördüncü ayrışma** vakası. Diğerleri:
`_numeric_key` / `_composite_numeric` (masraf), gold protokolü
(`build_gold` / `report_iaa`), oran tablosu başlık deseni
(`parse_rate_table` / `extract_from_rate_table`). Hepsinde kalıp aynı: doğru
kural bir yolda kilitli, karşıtı diğerinde serbest, ve fark sessiz.

## Yeniden üretim için not

Test konteyneri teslim yapılandırmasının parçası **değildir**; jüri yolunda
`docker compose --profile postgres up` yeterlidir ve orada port çakışması
olmaz (temiz makinede yerel Postgres bulunmaz).

## Sources
- `unittest discover -s tests` koşumu, `ANATOLIA_TEST_DATABASE_URL` set
- `tests/test_repo_parity.py`, `tests/test_api_backend.py`,
  `tests/test_pgvector_repository.py`
- `src/db/schema.sql`, `src/db/repository.py` (`_SQLITE_SCHEMA`)

## Related
- [[genel-denetim]] — kod/mimari hakeminin üçüncü açığı
- [[on-prem-prova]] — ağ kapalı tam prova
