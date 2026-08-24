# Kâr Payı Oranı Toplama Raporu

> Otomatik üretildi: `python -m src.scraping.harvest_rates`. Elle düzenlemeyin — yeniden koşuda üzerine yazılır.

- **Başlangıç:** 2026-08-24T21:27:03+00:00
- **Bitiş:** 2026-08-24T21:27:12+00:00
- **Domain başına gecikme:** 2.0 sn (CLAUDE.md §14)
- **robots.txt uyumu:** AÇIK (varsayılan)
- **Toplam oran kaydı:** 3

## Neden bu tur var

Aylık kâr payı oranı HTML'de yok; değer istemci-taraflı hesaplama aracının arkasında. Ürün sayfalarında yalnızca *etiket* bulunuyor. Bu tur oranı bankanın hesaplama ucundan alır.

## Banka Bazında

| Banka | Kayıt | Finansman | Katılma | Aylık oran aralığı | İstek | Başarısız |
|---|---:|---:|---:|---|---:|---:|
| `tom-katilim` | 3 | 3 | 0 | %3.99 | 5 | 0 |

## Kapsanan ürünler

- **tom-katilim** — Taksitli Alışveriş Finansmanı

## Adaptörü olmayan bankalar

Bu bankalarda oran, parametreli bir JSON ucundan alınamıyor. Kuveyt Türk için hesaplama aracını tarayıcıyla sürmek gerekir (ayrı adaptör); diğerlerinde ya hesaplama aracı yok ya oran istemci-taraflı sabit.

- `adil-katilim`
- `tkbb`

## Başarısız istekler

Başarısız istek yok.

## Notlar

Not yok.
