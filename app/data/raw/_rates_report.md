# Kâr Payı Oranı Toplama Raporu

> Otomatik üretildi: `python -m src.scraping.harvest_rates`. Elle düzenlemeyin — yeniden koşuda üzerine yazılır.

- **Başlangıç:** 2026-08-24T21:09:53+00:00
- **Bitiş:** 2026-08-24T21:10:37+00:00
- **Domain başına gecikme:** 2.0 sn (CLAUDE.md §14)
- **robots.txt uyumu:** AÇIK (varsayılan)
- **Toplam oran kaydı:** 23

## Neden bu tur var

Aylık kâr payı oranı HTML'de yok; değer istemci-taraflı hesaplama aracının arkasında. Ürün sayfalarında yalnızca *etiket* bulunuyor. Bu tur oranı bankanın hesaplama ucundan alır.

## Banka Bazında

| Banka | Kayıt | Finansman | Katılma | Aylık oran aralığı | İstek | Başarısız |
|---|---:|---:|---:|---|---:|---:|
| `hayat-finans` | 23 | 3 | 20 | %4.25 | 23 | 0 |

## Kapsanan ürünler

- **hayat-finans** — Bana Bunu Al (alışveriş finansmanı)

## Adaptörü olmayan bankalar

Bu bankalarda oran, parametreli bir JSON ucundan alınamıyor. Kuveyt Türk için hesaplama aracını tarayıcıyla sürmek gerekir (ayrı adaptör); diğerlerinde ya hesaplama aracı yok ya oran istemci-taraflı sabit.

- `adil-katilim`
- `dunya-katilim`
- `tkbb`
- `tom-katilim`

## Başarısız istekler

Başarısız istek yok.

## Notlar

Not yok.
