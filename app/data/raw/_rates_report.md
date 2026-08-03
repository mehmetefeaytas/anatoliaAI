# Kâr Payı Oranı Toplama Raporu

> Otomatik üretildi: `python -m src.scraping.harvest_rates`. Elle düzenlemeyin — yeniden koşuda üzerine yazılır.

- **Başlangıç:** 2026-08-03T19:11:40+00:00
- **Bitiş:** 2026-08-03T19:16:44+00:00
- **Domain başına gecikme:** 3.0 sn (CLAUDE.md §14)
- **robots.txt uyumu:** AÇIK (varsayılan)
- **Toplam oran kaydı:** 299

## Neden bu tur var

Aylık kâr payı oranı HTML'de yok; değer istemci-taraflı hesaplama aracının arkasında. Ürün sayfalarında yalnızca *etiket* bulunuyor. Bu tur oranı bankanın hesaplama ucundan alır.

## Banka Bazında

| Banka | Kayıt | Finansman | Katılma | Aylık oran aralığı | İstek | Başarısız |
|---|---:|---:|---:|---|---:|---:|
| `kuveyt-turk` | 3 | 3 | 0 | %2.99–%3.57 | 20 | 5 |
| `albaraka` | 16 | 16 | 0 | %3.04–%4.0 | 1 | 0 |
| `turkiye-finans` | 230 | 0 | 230 | — | 2 | 0 |
| `vakif-katilim` | 0 | 0 | 0 | — | 0 | 0 |
| `turkiye-emlak-katilim` | 50 | 42 | 8 | %1.89–%4.29 | 68 | 0 |

## Kapsanan ürünler

- **kuveyt-turk** — Konut Finansmanı
- **kuveyt-turk** — TOGG Finansmanı
- **kuveyt-turk** — Taşıt Finansmanı
- **albaraka** — 2. EL TAŞIT FİNANSMANI
- **albaraka** — 2. VE SONRAKİ KONUT FİNANSMANI
- **albaraka** — ARSA FİNANSMANI
- **albaraka** — CEP TELEFONU FİNANSMANI
- **albaraka** — DİJİTAL ARAÇ FİNANSMANI
- **albaraka** — DİĞER TAŞIT FİNANSMANI (MOTOSİKLET)
- **albaraka** — DİĞER TEKNOLOJİ FİNANSMANI
- **albaraka** — ENGELSİZ HAYAT FİNANSMANI
- **albaraka** — Eğitim Finansmanı
- **albaraka** — KONUT KİRA FİNANSMANI
- **albaraka** — PRATİK FİNANSMAN KART
- **albaraka** — PREFABRİK FİNANSMANI
- **albaraka** — SIFIR KM TAŞIT FİNANSMANI
- **albaraka** — YURT HİZMETİ FİNANSMANI
- **albaraka** — İLK EVİM KONUT FİNANSMANI
- **albaraka** — İŞYERİ FİNANSMANI
- **turkiye-emlak-katilim** — Ev/Ofis Gereçleri Finansmanı
- **turkiye-emlak-katilim** — Konut Finansmanı
- **turkiye-emlak-katilim** — Konut Finansmanı (sıfır konut)
- **turkiye-emlak-katilim** — Taşıt Finansmanı (2. el binek)
- **turkiye-emlak-katilim** — Taşıt Finansmanı (sıfır binek)

## Adaptörü olmayan bankalar

Bu bankalarda oran, parametreli bir JSON ucundan alınamıyor. Kuveyt Türk için hesaplama aracını tarayıcıyla sürmek gerekir (ayrı adaptör); diğerlerinde ya hesaplama aracı yok ya oran istemci-taraflı sabit.

- `adil-katilim`
- `dunya-katilim`
- `hayat-finans`
- `tom-katilim`
- `ziraat-katilim`

## Başarısız istekler

- **kuveyt-turk** `https://www.kuveytturk.com.tr/kendim-icin/finansmanlar/ihtiyac-finansmani` — tarayici vade=varsayilan: hesaplama araci bulunamadi
- **kuveyt-turk** `https://www.kuveytturk.com.tr/kendim-icin/finansmanlar/ihtiyac-finansmani` — tarayici vade=12: hesaplama araci bulunamadi
- **kuveyt-turk** `https://www.kuveytturk.com.tr/kendim-icin/finansmanlar/ihtiyac-finansmani` — tarayici vade=36: hesaplama araci bulunamadi
- **kuveyt-turk** `https://www.kuveytturk.com.tr/kendim-icin/finansmanlar/ihtiyac-finansmani` — tarayici vade=60: hesaplama araci bulunamadi
- **kuveyt-turk** `https://www.kuveytturk.com.tr/kendim-icin/finansmanlar/ihtiyac-finansmani` — tarayici vade=120: hesaplama araci bulunamadi

## Notlar

- **albaraka** — albaraka: katilma hesabi orani TOPLANMADI — calisan tek URL bicimi robots.txt'in *search*/*slug kurallarina takiliyor, parametresiz uc baglantiyi kapatiyor, statik HTML'de oran yok (bkz. sinif docstring'i)
- **vakif-katilim** — vakif-katilim: oran TOPLANMADI — oranlar yalnizca https://www.vakifkatilim.com.tr/documents/PerakendeBankacilik/kar-paylasim-oranlari.pdf belgesinde ve robots.txt '/documents/' yolunu acikca engelliyor. Sartname 5.1 geregi elle indirilip manual/ altina konabilir.
- **turkiye-emlak-katilim** — turkiye-emlak-katilim: ARACBINEK2EL — 6 (tutar, vade) noktasi FIYATLANMAMIS yanit verdi (oran 0 + toplam = ana para); kayit UYDURULMADI
- **turkiye-emlak-katilim** — turkiye-emlak-katilim: ARACBINEKYENI — 6 (tutar, vade) noktasi FIYATLANMAMIS yanit verdi (oran 0 + toplam = ana para); kayit UYDURULMADI
- **turkiye-emlak-katilim** — turkiye-emlak-katilim: EVOFISGERECLERI — 6 (tutar, vade) noktasi FIYATLANMAMIS yanit verdi (oran 0 + toplam = ana para); kayit UYDURULMADI
