# Kâr Payı Oranı Toplama Raporu

> Otomatik üretildi: `python -m src.scraping.harvest_rates`. Elle düzenlemeyin — yeniden koşuda üzerine yazılır.

- **Başlangıç:** 2026-08-24T22:32:45+00:00
- **Bitiş:** 2026-08-24T22:32:51+00:00
- **Domain başına gecikme:** 2.0 sn (CLAUDE.md §14)
- **robots.txt uyumu:** AÇIK (varsayılan)
- **Toplam oran kaydı:** 375

## Neden bu tur var

Aylık kâr payı oranı HTML'de yok; değer istemci-taraflı hesaplama aracının arkasında. Ürün sayfalarında yalnızca *etiket* bulunuyor. Bu tur oranı bankanın hesaplama ucundan alır.

## Banka Bazında

| Banka | Kayıt | Finansman | Katılma | Aylık oran aralığı | İstek | Başarısız |
|---|---:|---:|---:|---|---:|---:|
| `turkiye-finans` | 375 | 145 | 230 | %0.89–%6.1 | 3 | 0 |

## Kapsanan ürünler

- **turkiye-finans** — Arsa Finansmanı Sigortalı — Arsa Finansman
- **turkiye-finans** — Arsa Finansmanı Sigortasız — Arsa Finansman
- **turkiye-finans** — Bankamız Gayrimenkulleri Konut — Banka Gayrimenkulleri Konut Finansmanı
- **turkiye-finans** — Bankamız Gayrimenkulleri Ticari Mülk — Banka Gayrimenkulleri Ticari Mülk Finansmanı
- **turkiye-finans** — Mevcut Konutu Olan / Sigortalı Konut Finansmanı — Mortgage Finansmanı
- **turkiye-finans** — Mevcut Konutu Olan / Sigortasız Konut Finansmanı — Mortgage Finansmanı
- **turkiye-finans** — Sigortalı Motosiklet Finansmanı — Sigortalı Motosiklet Finansmanı
- **turkiye-finans** — Sigortalı Taşıt Finansmanı 0 km — Taşıt Finansmanı
- **turkiye-finans** — Sigortalı Taşıt Finansmanı 2. El — Taşıt Finansmanı
- **turkiye-finans** — Sigortasız Motosiklet Finansmanı — Sigortasız Motosiklet Finansmanı
- **turkiye-finans** — Sigortasız Taşıt Finansmanı 0 km — Taşıt Finansmanı
- **turkiye-finans** — Sigortasız Taşıt Finansmanı 2. El — Taşıt Finansmanı
- **turkiye-finans** — Sigortasız İhtiyaç Finansmanı — Sigortasız İhtiyaç Finansmanı
- **turkiye-finans** — Sigortasız İhtiyaç Finansmanı — Sigortasız İhtiyaç Finansmanı  
- **turkiye-finans** — İhtiyaç Finansmanı — İhtiyaç Finansmanı
- **turkiye-finans** — İhtiyaç Finansmanı — İhtiyaç Finansmanı  
- **turkiye-finans** — İlk Konutunu Alan / Sigortalı Konut Finansmanı — Mortgage Finansmanı
- **turkiye-finans** — İlk Konutunu Alan / Sigortasız Konut Finansmanı — Mortgage Finansmanı
- **turkiye-finans** — İşyeri Finansmanı Sigortalı — İşyeri Finansman
- **turkiye-finans** — İşyeri Finansmanı Sigortasız — İşyeri Finansman

## Adaptörü olmayan bankalar

Bu bankalarda oran, parametreli bir JSON ucundan alınamıyor. Kuveyt Türk için hesaplama aracını tarayıcıyla sürmek gerekir (ayrı adaptör); diğerlerinde ya hesaplama aracı yok ya oran istemci-taraflı sabit.

- `adil-katilim`
- `tkbb`

## Başarısız istekler

Başarısız istek yok.

## Notlar

Not yok.
