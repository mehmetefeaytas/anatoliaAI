# Ham Veri Toplama Raporu

> Otomatik üretildi: `python -m src.scraping.harvest`. Elle düzenlemeyin — yeniden koşuda üzerine yazılır.

- **Başlangıç:** 2026-08-03T16:27:54+00:00
- **Bitiş:** 2026-08-03T17:05:24+00:00
- **User-Agent:** `AnatoliaAI-Research/1.0 (+TEKNOFEST 2026; arastirma amacli)`
- **Domain başına gecikme:** 3.0 sn (CLAUDE.md §14)
- **robots.txt uyumu:** AÇIK (varsayılan)
- **Toplam belge:** 687

## Banka Bazında Özet

| Banka | Mod | Belge | Yöntem | Manuel | Boyut | Keşif (sitemap/liste) | Başarısız URL |
|---|---|---:|---|---:|---:|---|---:|
| `kuveyt-turk` | static | 134 | live | 0 | 17628 KB | 136/0 | 1 |
| `albaraka` | static | 41 | live | 0 | 7403 KB | 41/5 | 2 |
| `turkiye-finans` | static | 31 | live | 0 | 3569 KB | 0/31 | 0 |
| `ziraat-katilim` | static | 215 | live | 0 | 103327 KB | 27/195 | 5 |
| `vakif-katilim` | static | 86 | live | 0 | 11908 KB | 84/2 | 0 |
| `turkiye-emlak-katilim` | static | 89 | live | 0 | 14666 KB | 106/8 | 1 |
| `tom-katilim` | js | 13 | browser | 0 | 1206 KB | 0/13 | 0 |
| `hayat-finans` | js | 13 | browser | 0 | 3825 KB | 13/0 | 0 |
| `dunya-katilim` | static | 59 | live | 0 | 29813 KB | 57/2 | 0 |
| `adil-katilim` | js | 6 | browser | 0 | 5502 KB | 0/6 | 0 |

## Depolama Notu

Toplam ham veri: **194 MB** — bunun neredeyse tamamı `.html` dosyalarıdır (`.txt` + `.meta.json` birlikte ~2 MB).

`.html` cache'i CLAUDE.md §14 (provenance) gereği tutulur ve metin çıkarımı iyileştiğinde yeniden-çıkarıma imkân verir. Depo boyutu sorun olursa `data/raw/*/live/*.html` `.gitignore`'a alınabilir: `.txt` + `content_hash` provenance'ı korumaya yeter, ancak yeniden-çıkarım için tekrar toplama gerekir.

## robots.txt Durumu

- **kuveyt-turk** — HTTP 200; 0 Allow / 0 Disallow; 1 sitemap
- **albaraka** — HTTP 200; 1 Allow / 8 Disallow; agent='*'; 1 sitemap
- **turkiye-finans** — HTTP 200; 0 Allow / 12 Disallow; agent='*'; 1 sitemap
- **ziraat-katilim** — HTTP 200; 18 Allow / 33 Disallow; agent='*'; 2 sitemap
- **vakif-katilim** — HTTP 200; 4 Allow / 6 Disallow; agent='*'; 2 sitemap
- **turkiye-emlak-katilim** — HTTP 200; 1 Allow / 0 Disallow; agent='*'
- **tom-katilim** — cekilemedi (404); REP geregi izin varsayildi
- **hayat-finans** — HTTP 200; 1 Allow / 0 Disallow; agent='*'; 1 sitemap
- **dunya-katilim** — HTTP 200; 1 Allow / 1 Disallow; agent='*'; 1 sitemap
- **adil-katilim** — HTTP 200; 0 Allow / 0 Disallow

## Engellenen / Başarısız URL'ler

Bu URL'ler otomatik alınamadı. Şartname §5.1 manuel toplamaya izin
veriyor: sayfaları elle kaydedip `data/raw/<banka>/manual/`
altına koyun (yanına `.meta.json` provenance dosyası ekleyin).

### kuveyt-turk (1)

- `https://www.kuveytturk.com.tr/kampanyalar/kendim-icin/kart-kampanyalari/konforda-vade-farksiz-9-aya-varan-taksit-firsati` — **HTTP 404**

### albaraka (2)

- `https://www.albaraka.com.tr/tr/kampanyalar/detay/albaraka-otopark-ve-vale-harcamaniza-10-indirim-kazandiriyor` — **HTTP 404**
- `https://www.albaraka.com.tr/tr/kampanyalar/detay/albaraka-restoran-harcamaniza-5-indirim-kazandiriyor` — **HTTP 404**

### ziraat-katilim (5)

- `https://www.ziraatkatilim.com.tr/bireysel/kampanyalar/nisan-ayi-boyunca-avantajlar` — **HTTP 493**
- `https://www.ziraatkatilim.com.tr/bireysel/kampanyalar/pazaramada-ayin-ilk-haftasi-troy-haftasi` — **HTTP 493**
- `https://www.ziraatkatilim.com.tr/bireysel/kampanyalar/troy-idefix-kampanyasi` — **HTTP 493**
- `https://www.ziraatkatilim.com.tr/bireysel/kampanyalar/troy-kartla-biletinial-indirim` — **HTTP 493**
- `https://www.ziraatkatilim.com.tr/bireysel/kampanyalar/yeni-uye-isyeri-kazanimi-pos-kampanyasi` — **HTTP 493**

### turkiye-emlak-katilim (1)

- `https://www.emlakkatilim.com.tr/tr/kurumsal/kampanyalar/emlak-konut-asansor-emlak-katilim-is-birligi` — **HTTP 404**

## Notlar

- **kuveyt-turk** — cok kisa icerik atlandi: https://www.kuveytturk.com.tr/kampanyalar/isim-icin/is-birlik-kampanyalari (178 krkt)
- **albaraka** — cok kisa icerik atlandi: https://www.albaraka.com.tr/tr/kampanyalar/detay/2026 (66 krkt)
- **albaraka** — cok kisa icerik atlandi: https://www.albaraka.com.tr/tr/kampanyalar/detay/albaraka-otopark-ve-vale-harcamaniza-10-indirim-kazandiriyorr (124 krkt)
- **albaraka** — cok kisa icerik atlandi: https://www.albaraka.com.tr/tr/kampanyalar/detay/albaraka-restoran-harcamaniza-5-indirimm-kazandiriyor (117 krkt)
- **ziraat-katilim** — 222 aday bulundu, max_docs=220 ile kirpildi
- **vakif-katilim** — liste sayfasi basarisiz: https://www.vakifkatilim.com.tr/tr/isim-icin/kampanyalar/mevcut-kampanyalar (404)
- **turkiye-emlak-katilim** — 114 aday bulundu, max_docs=90 ile kirpildi
