# Ham Veri Toplama Raporu

> Otomatik üretildi: `python -m src.scraping.harvest`. Elle düzenlemeyin — yeniden koşuda üzerine yazılır.

- **Başlangıç:** 2026-08-04T12:57:47+00:00
- **Bitiş:** 2026-08-04T13:07:24+00:00
- **User-Agent:** `AnatoliaAI-Research/1.0 (+TEKNOFEST 2026; arastirma amacli)`
- **Domain başına gecikme:** 3.0 sn (CLAUDE.md §14)
- **robots.txt uyumu:** AÇIK (varsayılan)
- **Toplam belge:** 47

## Banka Bazında Özet

| Banka | Mod | Belge | Yöntem | Manuel | Boyut | Keşif (sitemap/liste) | Başarısız URL |
|---|---|---:|---|---:|---:|---|---:|
| `vakifbank` | static | 47 | live | 0 | 5286 KB | 0/50 | 1 |

## Depolama Notu

Toplam ham veri: **5 MB** — bunun neredeyse tamamı `.html` dosyalarıdır (`.txt` + `.meta.json` birlikte ~2 MB).

`.html` cache'i CLAUDE.md §14 (provenance) gereği tutulur ve metin çıkarımı iyileştiğinde yeniden-çıkarıma imkân verir. Depo boyutu sorun olursa `data/raw/*/live/*.html` `.gitignore`'a alınabilir: `.txt` + `content_hash` provenance'ı korumaya yeter, ancak yeniden-çıkarım için tekrar toplama gerekir.

## robots.txt Durumu

- **vakifbank** — HTTP 200; 1 Allow / 4 Disallow; agent='*'; 2 sitemap

## Engellenen / Başarısız URL'ler

Bu URL'ler otomatik alınamadı. Şartname §5.1 manuel toplamaya izin
veriyor: sayfaları elle kaydedip `data/raw/<banka>/manual/`
altına koyun (yanına `.meta.json` provenance dosyası ekleyin).

### vakifbank (1)

- `https://www.vakifkart.com.tr/kampanyalar/masterpass-ile-mobilette-mutlu-pazartesiler-7334` — **HTTP 404**

## Notlar

- **vakifbank** — sitemap basarisiz: https://www.vakifbank.com.tr/XML/www.vakifbank.com.tr_sitemap-tr.xml (404)
- **vakifbank** — cok kisa icerik atlandi: https://www.vakifbank.com.tr/tr/kampanyalar (142 krkt)
- **vakifbank** — mukerrer icerik atlandi: https://www.vakifkart.com.tr/kampanyalar/sayfa/1
