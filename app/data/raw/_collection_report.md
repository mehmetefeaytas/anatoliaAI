# Ham Veri Toplama Raporu

> Otomatik üretildi: `python -m src.scraping.harvest`. Elle düzenlemeyin — yeniden koşuda üzerine yazılır.

- **Başlangıç:** 2026-07-30T18:31:34+00:00
- **Bitiş:** 2026-07-30T18:48:00+00:00
- **User-Agent:** `AnatoliaAI-Research/1.0 (+TEKNOFEST 2026; arastirma amacli)`
- **Domain başına gecikme:** 3.0 sn (CLAUDE.md §14)
- **robots.txt uyumu:** AÇIK (varsayılan)
- **Toplam belge:** 289

## Banka Bazında Özet

| Banka | Mod | Belge | Yöntem | Manuel | Boyut | Keşif (sitemap/liste) | Başarısız URL |
|---|---|---:|---|---:|---:|---|---:|
| `kuveyt-turk` | static | 39 | live | 0 | 5171 KB | 452/1 | 0 |
| `albaraka` | static | 36 | live | 0 | 6419 KB | 41/2 | 1 |
| `turkiye-finans` | static | 35 | live | 0 | 4011 KB | 0/35 | 0 |
| `ziraat-katilim` | static | 28 | live | 0 | 12666 KB | 27/7 | 6 |
| `vakif-katilim` | static | 40 | live | 0 | 5522 KB | 100/2 | 0 |
| `turkiye-emlak-katilim` | static | 39 | live | 0 | 6503 KB | 106/1 | 1 |
| `tom-katilim` | js | 13 | browser | 0 | 1216 KB | 0/13 | 0 |
| `hayat-finans` | js | 13 | browser | 0 | 3825 KB | 13/0 | 0 |
| `dunya-katilim` | static | 40 | live | 0 | 20195 KB | 57/2 | 0 |
| `adil-katilim` | js | 6 | browser | 0 | 5502 KB | 0/6 | 0 |

## Depolama Notu

Toplam ham veri: **69 MB** — bunun neredeyse tamamı `.html` dosyalarıdır (`.txt` + `.meta.json` birlikte ~2 MB).

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

### albaraka (1)

- `https://www.albaraka.com.tr/tr/kampanyalar/detay/saglik-harcamalarina-vade-farksiz-6-taksit-kampanyasi-1_1` — **baglanti hatasi** ConnectionError: ('Connection aborted.', RemoteDisconnected('Remote end closed connection without response'))

### ziraat-katilim (6)

- `https://www.ziraatkatilim.com.tr/bireysel/kampanyalar/pazaramada-ayin-ilk-haftasi-troy-haftasi` — **HTTP 493**
- `https://www.ziraatkatilim.com.tr/bireysel/kampanyalar/troy-kartla-biletinial-indirim` — **HTTP 493**
- `https://www.ziraatkatilim.com.tr/bireysel/kampanyalar/troy-idefix-kampanyasi` — **HTTP 493**
- `https://www.ziraatkatilim.com.tr/bireysel/kampanyalar/yeni-uye-isyeri-kazanimi-pos-kampanyasi` — **HTTP 493**
- `https://www.ziraatkatilim.com.tr/bireysel/kampanyalar/nisan-ayi-boyunca-avantajlar` — **HTTP 493**
- `https://www.ziraatkatilim.com.tr/ticari/finansman-urunleri/surdurulebilirlik-temali-ticari-urunler/yenilenebilir-enerji-kapsamindaki-yatirim-ve-isletme-finansmanlari` — **HTTP 493**

### turkiye-emlak-katilim (1)

- `https://www.emlakkatilim.com.tr/tr/kurumsal/kampanyalar/emlak-konut-asansor-emlak-katilim-is-birligi` — **HTTP 404**

## Notlar

- **kuveyt-turk** — 453 aday bulundu, max_docs=40 ile kirpildi
- **kuveyt-turk** — cok kisa icerik atlandi: https://www.kuveytturk.com.tr/kampanyalar/isim-icin/is-birlik-kampanyalari (178 krkt)
- **albaraka** — 43 aday bulundu, max_docs=40 ile kirpildi
- **albaraka** — cok kisa icerik atlandi: https://www.albaraka.com.tr/tr/kampanyalar/detay/2026 (66 krkt)
- **albaraka** — cok kisa icerik atlandi: https://www.albaraka.com.tr/tr/kampanyalar/detay/albaraka-otopark-ve-vale-harcamaniza-10-indirim-kazandiriyor (124 krkt)
- **albaraka** — cok kisa icerik atlandi: https://www.albaraka.com.tr/tr/kampanyalar/detay/albaraka-otopark-ve-vale-harcamaniza-10-indirim-kazandiriyorr (124 krkt)
- **vakif-katilim** — 102 aday bulundu, max_docs=40 ile kirpildi
- **turkiye-emlak-katilim** — 107 aday bulundu, max_docs=40 ile kirpildi
- **dunya-katilim** — 59 aday bulundu, max_docs=40 ile kirpildi
