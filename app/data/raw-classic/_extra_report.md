# Ek Toplama Turları Raporu (Arşiv + PDF Belge)

> Otomatik üretildi: `python -m src.scraping.harvest_extra`. Elle düzenlemeyin — yeniden koşuda üzerine yazılır.

- **Başlangıç:** 2026-08-04T12:36:51+00:00
- **Bitiş:** 2026-08-04T12:37:08+00:00
- **Turlar:** archive
- **Domain başına gecikme:** 3.0 sn (CLAUDE.md §14)
- **robots.txt uyumu:** AÇIK (varsayılan)
- **Arşiv belgesi:** 0
- **PDF belgesi:** 0

## Arşiv Turu — Süresi Dolmuş Kampanyalar

`campaign_status: expired` etiketiyle `data/raw/<banka>/archive/` altına yazılır. Aktif kampanyalarla karışmaması `discover.DEFAULT_ARCHIVE_PATTERNS` ile garanti edilir (aktif turda exclude, arşiv turunda include).

| Banka | Keşif | Belge | Boyut |
|---|---:|---:|---:|
| `ziraat-bankasi` | 0 | 0 | 0 KB |
| `vakifbank` | 1 | 0 | 0 KB |
| `halkbank` | 0 | 0 | 0 KB |
| `akbank` | 0 | 0 | 0 KB |
| `yapi-kredi` | 0 | 0 | 0 KB |
| `garanti-bbva` | 0 | 0 | 0 KB |
| `is-bankasi` | 0 | 0 | 0 KB |
| `qnb` | 0 | 0 | 0 KB |
| `denizbank` | 0 | 0 | 0 KB |
| `ing` | 0 | 0 | 0 KB |
| `teb` | 0 | 0 | 0 KB |

## Belge Turu — PDF Ücret Tarifeleri / Bilgi Formları

| Banka | Keşif | PDF | Sayfa | Boyut |
|---|---:|---:|---:|---:|

## Engellenen / Başarısız

Engellenen URL yok.

## Notlar

- **ziraat-bankasi/archive** — ziraat-bankasi: archive_paths tanimli degil — tur atlandi
- **vakifbank/archive** — sitemap basarisiz: https://www.vakifbank.com.tr/XML/www.vakifbank.com.tr_sitemap-tr.xml (404)
- **vakifbank/archive** — cok kisa icerik atlandi: https://www.vakifbank.com.tr/tr/kampanya-arsivi (141 krkt)
- **halkbank/archive** — halkbank: archive_paths tanimli degil — tur atlandi
- **akbank/archive** — akbank: archive_paths tanimli degil — tur atlandi
- **yapi-kredi/archive** — yapi-kredi: archive_paths tanimli degil — tur atlandi
- **garanti-bbva/archive** — garanti-bbva: archive_paths tanimli degil — tur atlandi
- **is-bankasi/archive** — is-bankasi: archive_paths tanimli degil — tur atlandi
- **qnb/archive** — sayfalama: https://www.qnb.com.tr/kampanyalar/arsivdeki-kampanyalar icin 6 sayfa gezildi
- **denizbank/archive** — denizbank: archive_paths tanimli degil — tur atlandi
- **ing/archive** — ing: archive_paths tanimli degil — tur atlandi
- **teb/archive** — teb: archive_paths tanimli degil — tur atlandi
