# Kâr Payı Oranı Toplama Raporu

> Otomatik üretildi: `python -m src.scraping.harvest_rates`. Elle düzenlemeyin — yeniden koşuda üzerine yazılır.

- **Başlangıç:** 2026-08-24T22:43:35+00:00
- **Bitiş:** 2026-08-24T22:43:42+00:00
- **Domain başına gecikme:** 2.0 sn (CLAUDE.md §14)
- **robots.txt uyumu:** AÇIK (varsayılan)
- **Toplam oran kaydı:** 6

## Neden bu tur var

Aylık kâr payı oranı HTML'de yok; değer istemci-taraflı hesaplama aracının arkasında. Ürün sayfalarında yalnızca *etiket* bulunuyor. Bu tur oranı bankanın hesaplama ucundan alır.

## Banka Bazında

| Banka | Kayıt | Finansman | Katılma | Aylık oran aralığı | İstek | Başarısız |
|---|---:|---:|---:|---|---:|---:|
| `vakif-katilim` | 6 | 6 | 0 | %3.4–%3.5 | 2 | 0 |

## Kapsanan ürünler

- **vakif-katilim** — Kentsel Dönüşüm Finansmanı
- **vakif-katilim** — Taşıt Finansmanı

## Adaptörü olmayan bankalar

Bu bankalarda oran, parametreli bir JSON ucundan alınamıyor. Kuveyt Türk için hesaplama aracını tarayıcıyla sürmek gerekir (ayrı adaptör); diğerlerinde ya hesaplama aracı yok ya oran istemci-taraflı sabit.

- `adil-katilim`
- `tkbb`

## Başarısız istekler

Başarısız istek yok.

## Notlar

- **vakif-katilim** — vakif-katilim: KATILMA orani toplanmadi — yalnizca https://www.vakifkatilim.com.tr/documents/PerakendeBankacilik/kar-paylasim-oranlari.pdf belgesinde ve robots.txt '/documents/' yolunu acikca engelliyor. Sartname 5.1 geregi ELLE indirildi (scripts/vakif_paylasim_pdf.py).
