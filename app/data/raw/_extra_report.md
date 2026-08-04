# Ek Toplama Turları Raporu (Arşiv + PDF Belge)

> Otomatik üretildi: `python -m src.scraping.harvest_extra`. Elle düzenlemeyin — yeniden koşuda üzerine yazılır.

- **Başlangıç:** 2026-08-03T17:50:44+00:00
- **Bitiş:** 2026-08-03T18:03:51+00:00
- **Turlar:** archive, docs
- **Domain başına gecikme:** 3.0 sn (CLAUDE.md §14)
- **robots.txt uyumu:** AÇIK (varsayılan)
- **Arşiv belgesi:** 199
- **PDF belgesi:** 54

## Arşiv Turu — Süresi Dolmuş Kampanyalar

`campaign_status: expired` etiketiyle `data/raw/<banka>/archive/` altına yazılır. Aktif kampanyalarla karışmaması `discover.DEFAULT_ARCHIVE_PATTERNS` ile garanti edilir (aktif turda exclude, arşiv turunda include).

| Banka | Keşif | Belge | Boyut |
|---|---:|---:|---:|
| `kuveyt-turk` | 200 | 199 | 25957 KB |
| `albaraka` | 0 | 0 | 0 KB |

## Belge Turu — PDF Ücret Tarifeleri / Bilgi Formları

| Banka | Keşif | PDF | Sayfa | Boyut |
|---|---:|---:|---:|---:|
| `kuveyt-turk` | 40 | 39 | 165 | 8540 KB |
| `albaraka` | 40 | 15 | 299 | 7311 KB |

## Engellenen / Başarısız

- **kuveyt-turk/archive** `https://www.kuveytturk.com.tr/kampanyalar/kampanya-arsivi/kuveyt-turkten-saglik-sektorune-ozel-pos-kampanyasi` — HTTP 404
- **kuveyt-turk/docs** `https://www.kuveytturk.com.tr/medium/2025-ticari-urun-ve-hizmet-ucret-tablosu-3159.pdf` — HTTP 404
- **albaraka/docs** `https://www.albaraka.com.tr/TranslateTool/pdf-isaretdili/ceviri/viewer.html?fileName=https://www.albaraka.com.tr/documents/hakkimizda/sozlesme-ve-formlar/formlar/cek_senet_tahsiltaleponayucret_bilgilendirmeformu.pdf` — robots disallow robots.txt Disallow
- **albaraka/docs** `https://www.albaraka.com.tr/TranslateTool/pdf-isaretdili/ceviri/viewer.html?fileName=https://www.albaraka.com.tr/documents/hakkimizda/sozlesme-ve-formlar/formlar/genel-kredi-sozlesmesi-ucret-bilgilendirme-formu.pdf` — robots disallow robots.txt Disallow
- **albaraka/docs** `https://www.albaraka.com.tr/TranslateTool/pdf-isaretdili/ceviri/viewer.html?fileName=https://www.albaraka.com.tr/documents/hakkimizda/sozlesme-ve-formlar/formlar/kiralik-kasa-telep-onay-ucret-bilgilendirme-formu-tr.pdf` — robots disallow robots.txt Disallow
- **albaraka/docs** `https://www.albaraka.com.tr/TranslateTool/pdf-isaretdili/ceviri/viewer.html?fileName=https://www.albaraka.com.tr/documents/hakkimizda/sozlesme-ve-formlar/formlar/ucret-komisyon-tarifesi.pdf` — robots disallow robots.txt Disallow
- **albaraka/docs** `https://www.albaraka.com.tr/TranslateTool/pdf-isaretdili/ceviri/viewer.html?fileName=https://www.albaraka.com.tr/documents/hakkimizda/sozlesme-ve-formlar/gecmis-tarihli/aracfinansmanitalep,onayveucretbilgilendirmeformu.pdf` — robots disallow robots.txt Disallow
- **albaraka/docs** `https://www.albaraka.com.tr/TranslateTool/pdf-isaretdili/ceviri/viewer.html?fileName=https://www.albaraka.com.tr/documents/hakkimizda/sozlesme-ve-formlar/gecmis-tarihli/bireysel-finansman-destegi-kredisi-talep-onay-ucret-bilgilendirme-formu.pdf` — robots disallow robots.txt Disallow
- **albaraka/docs** `https://www.albaraka.com.tr/TranslateTool/pdf-isaretdili/ceviri/viewer.html?fileName=https://www.albaraka.com.tr/documents/hakkimizda/sozlesme-ve-formlar/gecmis-tarihli/konut-finansmani-talep-onay-ucret-bilgilendirme-formu.pdf` — robots disallow robots.txt Disallow
- **albaraka/docs** `https://www.albaraka.com.tr/TranslateTool/pdf-isaretdili/ceviri/viewer.html?fileName=https://www.albaraka.com.tr/documents/hakkimizda/sozlesme-ve-formlar/sozlesmeler/bayide-finansman-ihtiyac---aracilik-ve-garantorluk-sozlesmesi-(komisyonsuz).pdf` — robots disallow robots.txt Disallow
- **albaraka/docs** `https://www.albaraka.com.tr/TranslateTool/pdf-isaretdili/ceviri/viewer.html?fileName=https://www.albaraka.com.tr/documents/hakkimizda/sozlesme-ve-formlar/sozlesmeler/bayide-finansman-ihtiyac---aracilik-ve-garantorluk-sozlesmesi-kredi-(komisyonsuz).pdf` — robots disallow robots.txt Disallow
- **albaraka/docs** `https://www.albaraka.com.tr/TranslateTool/pdf-isaretdili/ceviri/viewer.html?fileName=https://www.albaraka.com.tr/documents/hakkimizda/sozlesme-ve-formlar/sozlesmeler/bayide-finansman-ots---aracilik-ve-garantorluk-sozlesmesi-(-komisyonsuz).pdf` — robots disallow robots.txt Disallow
- **albaraka/docs** `https://www.albaraka.com.tr/TranslateTool/pdf-isaretdili/ceviri/viewer.html?fileName=https://www.albaraka.com.tr/documents/hakkimizda/sozlesme-ve-formlar/sozlesmeler/bayide-finansman-ots---aracilik-ve-garantorluk-sozlesmesi-kredi-(-komisyonsuz).pdf` — robots disallow robots.txt Disallow
- **albaraka/docs** `https://www.albaraka.com.tr/TranslateTool/pdf-isaretdili/ceviri/viewer.html?fileName=https://www.albaraka.com.tr/documents/hakkimizda/sozlesme-ve-formlar/sozlesmeler/bayide-finansman-tasit--aracilik-ve-garantorluk-sozlesmesi-(komisyonsuz).pdf` — robots disallow robots.txt Disallow
- **albaraka/docs** `https://www.albaraka.com.tr/TranslateTool/pdf-isaretdili/ceviri/viewer.html?fileName=https://www.albaraka.com.tr/documents/hakkimizda/sozlesme-ve-formlar/sozlesmeler/bayide-finansman-tasit--aracilik-ve-garantorluk-sozlesmesi-kredi-(komisyonsuz).pdf` — robots disallow robots.txt Disallow
- **albaraka/docs** `https://www.albaraka.com.tr/TranslateTool/pdf-ses/ceviri/viewer.html?fileName=https://www.albaraka.com.tr/documents/hakkimizda/sozlesme-ve-formlar/formlar/cek_senet_tahsiltaleponayucret_bilgilendirmeformu.pdf` — robots disallow robots.txt Disallow
- **albaraka/docs** `https://www.albaraka.com.tr/TranslateTool/pdf-ses/ceviri/viewer.html?fileName=https://www.albaraka.com.tr/documents/hakkimizda/sozlesme-ve-formlar/formlar/genel-kredi-sozlesmesi-ucret-bilgilendirme-formu.pdf` — robots disallow robots.txt Disallow
- **albaraka/docs** `https://www.albaraka.com.tr/TranslateTool/pdf-ses/ceviri/viewer.html?fileName=https://www.albaraka.com.tr/documents/hakkimizda/sozlesme-ve-formlar/formlar/ucret-komisyon-tarifesi.pdf` — robots disallow robots.txt Disallow
- **albaraka/docs** `https://www.albaraka.com.tr/TranslateTool/pdf-ses/ceviri/viewer.html?fileName=https://www.albaraka.com.tr/documents/hakkimizda/sozlesme-ve-formlar/gecmis-tarihli/aracfinansmanitalep,onayveucretbilgilendirmeformu.pdf` — robots disallow robots.txt Disallow
- **albaraka/docs** `https://www.albaraka.com.tr/TranslateTool/pdf-ses/ceviri/viewer.html?fileName=https://www.albaraka.com.tr/documents/hakkimizda/sozlesme-ve-formlar/gecmis-tarihli/bireysel-finansman-destegi-kredisi-talep-onay-ucret-bilgilendirme-formu.pdf` — robots disallow robots.txt Disallow
- **albaraka/docs** `https://www.albaraka.com.tr/TranslateTool/pdf-ses/ceviri/viewer.html?fileName=https://www.albaraka.com.tr/documents/hakkimizda/sozlesme-ve-formlar/gecmis-tarihli/konut-finansmani-talep-onay-ucret-bilgilendirme-formu.pdf` — robots disallow robots.txt Disallow
- **albaraka/docs** `https://www.albaraka.com.tr/TranslateTool/pdf-ses/ceviri/viewer.html?fileName=https://www.albaraka.com.tr/documents/hakkimizda/sozlesme-ve-formlar/sozlesmeler/bayide-finansman-ihtiyac---aracilik-ve-garantorluk-sozlesmesi-(komisyonsuz).pdf` — robots disallow robots.txt Disallow
- **albaraka/docs** `https://www.albaraka.com.tr/TranslateTool/pdf-ses/ceviri/viewer.html?fileName=https://www.albaraka.com.tr/documents/hakkimizda/sozlesme-ve-formlar/sozlesmeler/bayide-finansman-ihtiyac---aracilik-ve-garantorluk-sozlesmesi-kredi-(komisyonsuz).pdf` — robots disallow robots.txt Disallow
- **albaraka/docs** `https://www.albaraka.com.tr/TranslateTool/pdf-ses/ceviri/viewer.html?fileName=https://www.albaraka.com.tr/documents/hakkimizda/sozlesme-ve-formlar/sozlesmeler/bayide-finansman-ots---aracilik-ve-garantorluk-sozlesmesi-(-komisyonsuz).pdf` — robots disallow robots.txt Disallow
- **albaraka/docs** `https://www.albaraka.com.tr/TranslateTool/pdf-ses/ceviri/viewer.html?fileName=https://www.albaraka.com.tr/documents/hakkimizda/sozlesme-ve-formlar/sozlesmeler/bayide-finansman-ots---aracilik-ve-garantorluk-sozlesmesi-kredi-(-komisyonsuz).pdf` — robots disallow robots.txt Disallow
- **albaraka/docs** `https://www.albaraka.com.tr/TranslateTool/pdf-ses/ceviri/viewer.html?fileName=https://www.albaraka.com.tr/documents/hakkimizda/sozlesme-ve-formlar/sozlesmeler/bayide-finansman-tasit--aracilik-ve-garantorluk-sozlesmesi-(komisyonsuz).pdf` — robots disallow robots.txt Disallow
- **albaraka/docs** `https://www.albaraka.com.tr/TranslateTool/pdf-ses/ceviri/viewer.html?fileName=https://www.albaraka.com.tr/documents/hakkimizda/sozlesme-ve-formlar/sozlesmeler/bayide-finansman-tasit--aracilik-ve-garantorluk-sozlesmesi-kredi-(komisyonsuz).pdf` — robots disallow robots.txt Disallow

## Notlar

- **kuveyt-turk/archive** — 318 aday bulundu, max_docs=200 ile kirpildi
- **kuveyt-turk/docs** — 444 aday bulundu, max_docs=40 ile kirpildi
- **albaraka/archive** — albaraka: archive_paths tanimli degil — tur atlandi
- **albaraka/docs** — 427 aday bulundu, max_docs=40 ile kirpildi
