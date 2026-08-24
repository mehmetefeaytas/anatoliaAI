# Kâr Payı Oranı Toplama Raporu

> Otomatik üretildi: `python -m src.scraping.harvest_rates`. Elle düzenlemeyin — yeniden koşuda üzerine yazılır.

- **Başlangıç:** 2026-08-24T21:13:58+00:00
- **Bitiş:** 2026-08-24T21:16:25+00:00
- **Domain başına gecikme:** 2.0 sn (CLAUDE.md §14)
- **robots.txt uyumu:** AÇIK (varsayılan)
- **Toplam oran kaydı:** 56

## Neden bu tur var

Aylık kâr payı oranı HTML'de yok; değer istemci-taraflı hesaplama aracının arkasında. Ürün sayfalarında yalnızca *etiket* bulunuyor. Bu tur oranı bankanın hesaplama ucundan alır.

## Banka Bazında

| Banka | Kayıt | Finansman | Katılma | Aylık oran aralığı | İstek | Başarısız |
|---|---:|---:|---:|---|---:|---:|
| `dunya-katilim` | 56 | 56 | 0 | %2.99–%3.99 | 73 | 0 |

## Kapsanan ürünler

- **dunya-katilim** — Araç Binek 2.El
- **dunya-katilim** — Araç Binek Yeni
- **dunya-katilim** — Arsa
- **dunya-katilim** — Konut 2.El
- **dunya-katilim** — Konut Yeni
- **dunya-katilim** — Tüketici İhtiyaç Finansmanı

## Adaptörü olmayan bankalar

Bu bankalarda oran, parametreli bir JSON ucundan alınamıyor. Kuveyt Türk için hesaplama aracını tarayıcıyla sürmek gerekir (ayrı adaptör); diğerlerinde ya hesaplama aracı yok ya oran istemci-taraflı sabit.

- `adil-katilim`
- `tkbb`
- `tom-katilim`

## Başarısız istekler

Başarısız istek yok.

## Notlar

- **dunya-katilim** — dunya-katilim: ARACBINEK2ELTUKETICI — 8 (tutar, vade) noktasi RATEERROR/oransiz dondu (urun bandi disi); kayit uydurulmadi
- **dunya-katilim** — dunya-katilim: ARACBINEKYENITUKETICI — 8 (tutar, vade) noktasi RATEERROR/oransiz dondu (urun bandi disi); kayit uydurulmadi
