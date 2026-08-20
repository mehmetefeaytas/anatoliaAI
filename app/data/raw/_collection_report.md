# Ham Veri Toplama Raporu

> Otomatik üretildi: `python -m src.scraping.harvest`. Elle düzenlemeyin — yeniden koşuda üzerine yazılır.

- **Başlangıç:** 2026-08-20T16:35:46+00:00
- **Bitiş:** 2026-08-20T16:46:56+00:00
- **User-Agent:** `AnatoliaAI-Research/1.0 (+TEKNOFEST 2026; arastirma amacli)`
- **Domain başına gecikme:** 3.0 sn (CLAUDE.md §14)
- **robots.txt uyumu:** AÇIK (varsayılan)
- **Toplam belge:** 191

## Banka Bazında Özet

| Banka | Mod | Belge | Yöntem | Manuel | Boyut | Keşif (sitemap/liste) | Başarısız URL |
|---|---|---:|---|---:|---:|---|---:|
| `tom-katilim` | js | 164 | browser | 0 | 16710 KB | 162/2 | 0 |
| `hayat-finans` | js | 27 | browser | 0 | 4759 KB | 40/11 | 24 |

## Depolama Notu

Toplam ham veri: **21 MB** — bunun neredeyse tamamı `.html` dosyalarıdır (`.txt` + `.meta.json` birlikte ~2 MB).

`.html` cache'i CLAUDE.md §14 (provenance) gereği tutulur ve metin çıkarımı iyileştiğinde yeniden-çıkarıma imkân verir. Depo boyutu sorun olursa `data/raw/*/live/*.html` `.gitignore`'a alınabilir: `.txt` + `content_hash` provenance'ı korumaya yeter, ancak yeniden-çıkarım için tekrar toplama gerekir.

## robots.txt Durumu

- **tom-katilim** — cekilemedi (404); REP geregi izin varsayildi
- **hayat-finans** — HTTP 200; 1 Allow / 0 Disallow; agent='*'; 1 sitemap

## Engellenen / Başarısız URL'ler

Bu URL'ler otomatik alınamadı. Şartname §5.1 manuel toplamaya izin
veriyor: sayfaları elle kaydedip `data/raw/<banka>/manual/`
altına koyun (yanına `.meta.json` provenance dosyası ekleyin).

### hayat-finans (24)

- `https://hayatpay.com.tr/kampanya/164` — **HTTP 404**
- `https://hayatpay.com.tr/kampanya/507` — **HTTP 404**
- `https://hayatpay.com.tr/kampanya/588` — **HTTP 404**
- `https://hayatpay.com.tr/kampanya/83` — **HTTP 404**
- `https://hayatpay.com.tr/kampanya/280` — **HTTP 404**
- `https://hayatpay.com.tr/kampanya/362` — **HTTP 404**
- `https://hayatpay.com.tr/kampanya/636` — **HTTP 404**
- `https://hayatpay.com.tr/kampanya/637` — **HTTP 404**
- `https://hayatpay.com.tr/kampanya/631` — **HTTP 404**
- `https://hayatpay.com.tr/kampanya/512` — **HTTP 404**
- `https://hayatpay.com.tr/kampanya/553` — **HTTP 404**
- `https://hayatpay.com.tr/kampanya/370` — **HTTP 404**
- `https://hayatpay.com.tr/kampanya/500` — **HTTP 404**
- `https://hayatpay.com.tr/kampanya/316` — **HTTP 404**
- `https://hayatpay.com.tr/kampanya/501` — **HTTP 404**
- `https://hayatpay.com.tr/kampanya/590` — **HTTP 404**
- `https://hayatpay.com.tr/kampanya/638` — **HTTP 404**
- `https://hayatpay.com.tr/kampanya/592` — **HTTP 404**
- `https://hayatpay.com.tr/kampanya/494` — **HTTP 404**
- `https://hayatpay.com.tr/kampanya/589` — **HTTP 404**
- `https://hayatpay.com.tr/kampanya/508` — **HTTP 404**
- `https://hayatpay.com.tr/kampanya/591` — **HTTP 404**
- `https://hayatpay.com.tr/kampanya/73` — **HTTP 404**
- `https://hayatpay.com.tr/kampanya/416` — **HTTP 404**

## Notlar

- **tom-katilim** — sayfalama: https://www.tombank.com.tr/kampanyalar.html icin tek sayfa bulundu (sayfalama denetimi yok)
- **tom-katilim** — sayfalama: https://www.tombank.com.tr/urunlerimiz.html icin tek sayfa bulundu (sayfalama denetimi yok)
- **tom-katilim** — sayfalama: https://tombankhadi.com/hadi-kazan/kampanyalar icin tek sayfa bulundu (sayfalama denetimi yok)
- **hayat-finans** — sayfalama: https://hayatfinans.com.tr/kampanyalar icin tek sayfa bulundu (sayfalama denetimi yok)
- **hayat-finans** — sayfalama: https://hayatpay.com.tr/kampanya icin tek sayfa bulundu (sayfalama denetimi yok)
- **hayat-finans** — sayfalama: https://hayatfinans.com.tr/isim-kampanyalar icin tek sayfa bulundu (sayfalama denetimi yok)
