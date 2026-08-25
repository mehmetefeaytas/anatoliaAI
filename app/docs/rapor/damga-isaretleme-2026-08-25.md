# Damga Tabanlı Bitmişlik İşaretlemesi

> Otomatik üretildi: `python -m scripts.damga_isaretle`. Elle düzenlemeyin.

- **Korpus:** `data/raw` · bölümler: `live/`
- **Mod:** UYGULANDI (.meta.json yazıldı)
- **Ağ isteği:** yok (yalnız yerel temiz metin taraması)
- **Taşınan/silinen dosya:** yok

| Karar | Adet | Oran | Anlamı |
|---|---:|---:|---|
| `damgali` | 210 | %23,8 | sayfa kendini bitmiş ilan ediyor → `campaign_status: expired` |
| `belirsiz` | 71 | %8,0 | geniş desen ateşliyor ama damga değil → **karar verilmedi**, dokunulmadı |
| `temiz` | 601 | %68,1 | bitmişlik işareti yok → `campaign_status: active` (başka bir mekanizma zaten yazmadıysa) |

`belirsiz` satırı bilerek ayrı: o belgelerde eşleşen şey menü bağlantısı, ihtar kalıbı ya da başka bir kampanyanın damgası olabilir. Emin olunmayan belgeye "kapanmış" demek veri uydurmaktır (CLAUDE.md §19).

## Banka bazında

| Banka | Belge | Damgalı | Oran | Belirsiz | Bitiş tarihi okunan |
|---|---:|---:|---:|---:|---:|
| `ziraat-katilim` | 219 | 104 | %47,5 | 0 | 104 |
| `vakif-katilim` | 91 | 81 | %89,0 | 7 | 0 |
| `dunya-katilim` | 59 | 14 | %23,7 | 0 | 13 |
| `tom-katilim` | 88 | 11 | %12,5 | 19 | 0 |
| `adil-katilim` | 6 | 0 | %0,0 | 0 | 0 |
| `albaraka` | 90 | 0 | %0,0 | 13 | 0 |
| `hayat-finans` | 29 | 0 | %0,0 | 0 | 0 |
| `kuveyt-turk` | 159 | 0 | %0,0 | 0 | 0 |
| `turkiye-emlak-katilim` | 98 | 0 | %0,0 | 0 | 0 |
| `turkiye-finans` | 43 | 0 | %0,0 | 32 | 0 |
| **TOPLAM** | **882** | **210** | **%23,8** | **71** | **117** |

## Damgadan okunan bitiş tarihleri

117 belgede bitiş tarihi damgaya YAPIŞIK olarak yazılı; kalan 93 belgede damga tarih taşımıyor ve tarih UYDURULMADI.

| Bitiş ayı | Belge |
|---|---:|
| 2025-06 | 1 |
| 2025-07 | 1 |
| 2025-08 | 2 |
| 2025-09 | 4 |
| 2025-10 | 5 |
| 2025-11 | 6 |
| 2025-12 | 6 |
| 2026-01 | 1 |
| 2026-02 | 2 |
| 2026-03 | 8 |
| 2026-04 | 3 |
| 2026-05 | 20 |
| 2026-06 | 24 |
| 2026-07 | 32 |
| 2026-08 | 2 |

## Damgalı belgeler (210)

<details><summary>Liste</summary>

- `dunya-katilim/live/kampanyalar-carter-s.txt.meta.json` — «Sona erdi Bitiş Tarihi» · bitiş: 2026-06-30
- `dunya-katilim/live/kampanyalar-fiziki-altin.txt.meta.json` — «Kampanya Süresi Dolmuştur» · bitiş: —
- `dunya-katilim/live/kampanyalar-lc-waikiki.txt.meta.json` — «Sona erdi Bitiş Tarihi» · bitiş: 2026-07-15
- `dunya-katilim/live/kampanyalar-minycenter.txt.meta.json` — «Sona erdi Bitiş Tarihi» · bitiş: 2026-06-30
- `dunya-katilim/live/kampanyalar-touristica.txt.meta.json` — «Sona erdi Bitiş Tarihi» · bitiş: 2026-07-31
- `dunya-katilim/live/kampanyalar-trendyol.txt.meta.json` — «Sona erdi Bitiş Tarihi» · bitiş: 2026-07-31
- `dunya-katilim/live/kampanyalar-twist.txt.meta.json` — «Sona erdi Bitiş Tarihi» · bitiş: 2026-07-31
- `dunya-katilim/live/kampanyalar-vaillant.txt.meta.json` — «Sona erdi Bitiş Tarihi» · bitiş: 2026-07-31
- `dunya-katilim/live/kampanyalar-vakko.txt.meta.json` — «Sona erdi Bitiş Tarihi» · bitiş: 2026-07-31
- `dunya-katilim/live/kampanyalar-vatan.txt.meta.json` — «Sona erdi Bitiş Tarihi» · bitiş: 2026-07-31
- `dunya-katilim/live/kampanyalar-vestel.txt.meta.json` — «Sona erdi Bitiş Tarihi» · bitiş: 2026-07-31
- `dunya-katilim/live/kampanyalar-yatas.txt.meta.json` — «Sona erdi Bitiş Tarihi» · bitiş: 2026-07-31
- `dunya-katilim/live/kampanyalar-yenilio.txt.meta.json` — «Sona erdi Bitiş Tarihi» · bitiş: 2026-07-31
- `dunya-katilim/live/kampanyalar-zsa-zsa-zsu.txt.meta.json` — «Sona erdi Bitiş Tarihi» · bitiş: 2026-07-31
- `tom-katilim/live/kampanyalar-hadi-hesabini-aktiflestir.txt.meta.json` — «Bu kampanya sona ermiştir» · bitiş: —
- `tom-katilim/live/kampanyalar-hadi-hesabini-aktiflestirmek-icin-gonderecegin-ilk-250-tlye-alisveri.txt.meta.json` — «Bu kampanya sona ermiştir» · bitiş: —
- `tom-katilim/live/kampanyalar-hadi-hesabini-aktiflestirmek-icin-gonderecegin-ilk-500-tlye-alisveri.txt.meta.json` — «Bu kampanya sona ermiştir» · bitiş: —
- `tom-katilim/live/kampanyalar-hadi-kartlarin-ile-ucak-biletlerinde-250-tl-indirim.txt.meta.json` — «Bu kampanya sona ermiştir» · bitiş: —
- `tom-katilim/live/kampanyalar-hadi-kredi-karti-ile-spotify-ve-netflix-harcamalari-bedava.txt.meta.json` — «Bu kampanya sona ermiştir» · bitiş: —
- `tom-katilim/live/kampanyalar-hadi-kredi-karti-ni-masterpass-e-kaydet-hop-scooter-surusunde-acilis.txt.meta.json` — «Bu kampanya sona ermiştir» · bitiş: —
- `tom-katilim/live/kampanyalar-hadi-kredi-karti-ni-trendyol-a-kaydet-200-tl-indirim-kuponu-kazan.txt.meta.json` — «Bu kampanya sona ermiştir» · bitiş: —
- `tom-katilim/live/kampanyalar-hadi-taksitli-kredi-ile-2500-tl-ve-uzeri-harcamalarinda-250-tl-nakit.txt.meta.json` — «Bu kampanya sona ermiştir» · bitiş: —
- `tom-katilim/live/kampanyalar-hadi-veresiye-ile-1000tl-harca-100tl-kazan.txt.meta.json` — «Bu kampanya sona ermiştir» · bitiş: —
- `tom-katilim/live/kampanyalar-hadi-veresiye-ile-toplam-10000tl-harca-ek-250tl-kazan.txt.meta.json` — «Bu kampanya sona ermiştir» · bitiş: —
- `tom-katilim/live/kampanyalar-hadi-yilin-kampanyasi.txt.meta.json` — «Bu kampanya sona ermiştir» · bitiş: —
- `vakif-katilim/live/detay-3-ay-ertelemeli-motosiklet-kampanyasi.txt.meta.json` — «Kampanya Süresi Dolmuştur» · bitiş: —
- `vakif-katilim/live/detay-3-ay-ertelemeli-tasit-finansmani.txt.meta.json` — «Kampanya Süresi Dolmuştur» · bitiş: —
- `vakif-katilim/live/detay-50000-tl-ihtiyac-finansmani-kampanyasi.txt.meta.json` — «Kampanya Süresi Dolmuştur» · bitiş: —
- `vakif-katilim/live/detay-anneler-gunu-hediyesi-vakif-katilimda.txt.meta.json` — «Kampanya Süresi Dolmuştur» · bitiş: —
- `vakif-katilim/live/detay-babalar-gunune-ozel-vkart-hatemoglu-indirimi.txt.meta.json` — «Kampanya Süresi Dolmuştur» · bitiş: —
- `vakif-katilim/live/detay-bu-yol-indirime-gider.txt.meta.json` — «Kampanya Süresi Dolmuştur» · bitiş: —
- `vakif-katilim/live/detay-cicek-gibi-kampanya-vakif-katilimda.txt.meta.json` — «Kampanya Süresi Dolmuştur» · bitiş: —
- `vakif-katilim/live/detay-doga-dostu-arac-finansmani.txt.meta.json` — «Kampanya Süresi Dolmuştur» · bitiş: —
- `vakif-katilim/live/detay-dry-centerda-kuru-temizleme-20-indirimli.txt.meta.json` — «Kampanya Süresi Dolmuştur» · bitiş: —
- `vakif-katilim/live/detay-egitim-harcamalariniza-vade-farksiz-5-taksit.txt.meta.json` — «Kampanya Süresi Dolmuştur» · bitiş: —
- `vakif-katilim/live/detay-elektronik-esya-alisverislerinizde-400-tl-iade.txt.meta.json` — «Kampanya Süresi Dolmuştur» · bitiş: —
- `vakif-katilim/live/detay-eyt-finansmani.txt.meta.json` — «Kampanya Süresi Dolmuştur» · bitiş: —
- `vakif-katilim/live/detay-fatura-talimati-verenler-espressolabden-5-kahve-kazaniyor.txt.meta.json` — «Kampanya Süresi Dolmuştur» · bitiş: —
- `vakif-katilim/live/detay-gaziantepte-ulasim-icin-troy-kullanilir.txt.meta.json` — «Kampanya Süresi Dolmuştur» · bitiş: —
- `vakif-katilim/live/detay-gencler-troy-kredi-karti-ile-geziyor.txt.meta.json` — «Kampanya Süresi Dolmuştur» · bitiş: —
- `vakif-katilim/live/detay-genclere-ozel-hediye-kahve.txt.meta.json` — «Kampanya Süresi Dolmuştur» · bitiş: —
- `vakif-katilim/live/detay-genclere-rent-godan-40-indirim.txt.meta.json` — «Kampanya Süresi Dolmuştur» · bitiş: —
- `vakif-katilim/live/detay-getirde-600-tl-hediye-kampanyasi.txt.meta.json` — «Kampanya Süresi Dolmuştur» · bitiş: —
- `vakif-katilim/live/detay-hac-ve-umre-finansmani.txt.meta.json` — «Kampanya Süresi Dolmuştur» · bitiş: —
- `vakif-katilim/live/detay-igdas-fatura-odemelerine-vade-farksiz-2-taksit.txt.meta.json` — «Kampanya Süresi Dolmuştur» · bitiş: —
- `vakif-katilim/live/detay-igdas-fatura-odemelerinize-vade-farksiz-3-taksit.txt.meta.json` — «Kampanya Süresi Dolmuştur» · bitiş: —
- `vakif-katilim/live/detay-igdas-finansman-kampanyasi.txt.meta.json` — «Kampanya Süresi Dolmuştur» · bitiş: —
- `vakif-katilim/live/detay-mastercard-ile-gelir-vergisi-odemelerine-vade-farksiz-3-taksit-1.txt.meta.json` — «Kampanya Süresi Dolmuştur» · bitiş: —
- `vakif-katilim/live/detay-mastercard-ile-gelir-vergisi-odemelerine-vade-farksiz-3-taksit.txt.meta.json` — «Kampanya Süresi Dolmuştur» · bitiş: —
- `vakif-katilim/live/detay-mastercard-kredi-kartinizla-200-tl-marti-kuponu.txt.meta.json` — «Kampanya Süresi Dolmuştur» · bitiş: —
- `vakif-katilim/live/detay-mastercard-kredi-kartinizla-n11-alisverisinize-300-tl-indirim-1.txt.meta.json` — «Kampanya Süresi Dolmuştur» · bitiş: —
- `vakif-katilim/live/detay-mastercard-kredi-kartinizla-n11-alisverisinize-300-tl-indirim.txt.meta.json` — «Kampanya Süresi Dolmuştur» · bitiş: —
- `vakif-katilim/live/detay-masterpiece-hobi-atolyesinde-10-indirim.txt.meta.json` — «Kampanya Süresi Dolmuştur» · bitiş: —
- `vakif-katilim/live/detay-masterpiece-hobi-atolyesinde-15-indirim.txt.meta.json` — «Kampanya Süresi Dolmuştur» · bitiş: —
- `vakif-katilim/live/detay-meyve-dalindan-pos-vakif-katilimdan.txt.meta.json` — «Kampanya Süresi Dolmuştur» · bitiş: —
- `vakif-katilim/live/detay-mobilden-vakif-katilimli-olanlara-modanisada-200-tl-hediye.txt.meta.json` — «Kampanya Süresi Dolmuştur» · bitiş: —
- `vakif-katilim/live/detay-mobilya-ve-dekorasyon-alisverislerinize-500-tl-iade.txt.meta.json` — «Kampanya Süresi Dolmuştur» · bitiş: —
- `vakif-katilim/live/detay-modanisada-15-indirim.txt.meta.json` — «Kampanya Süresi Dolmuştur» · bitiş: —
- `vakif-katilim/live/detay-mtv-odemeleri-vade-farksiz-3-taksit-1.txt.meta.json` — «Kampanya Süresi Dolmuştur» · bitiş: —
- `vakif-katilim/live/detay-mtv-odemeleri-vade-farksiz-3-taksit.txt.meta.json` — «Kampanya Süresi Dolmuştur» · bitiş: —
- `vakif-katilim/live/detay-ogretmenlerimize-vakif-katilimdan-avantajli-paket.txt.meta.json` — «Kampanya Süresi Dolmuştur» · bitiş: —
- `vakif-katilim/live/detay-ria-a101-hediye-ceki-kampanyasi.txt.meta.json` — «Kampanya Süresi Dolmuştur» · bitiş: —
- `vakif-katilim/live/detay-saatleri-indirime-ayarladik.txt.meta.json` — «Kampanya Süresi Dolmuştur» · bitiş: —
- `vakif-katilim/live/detay-saglik-harcamalariniza-vade-farksiz-5-taksit.txt.meta.json` — «Kampanya Süresi Dolmuştur» · bitiş: —
- `vakif-katilim/live/detay-tiktakta-600-tl-indirim.txt.meta.json` — «Kampanya Süresi Dolmuştur» · bitiş: —
- `vakif-katilim/live/detay-trendyolda-300-tl-troy-indirimi.txt.meta.json` — «Kampanya Süresi Dolmuştur» · bitiş: —
- `vakif-katilim/live/detay-troy-ile-gelir-vergisi-odemelerine-vade-farksiz-3-taksit.txt.meta.json` — «Kampanya Süresi Dolmuştur» · bitiş: —
- `vakif-katilim/live/detay-troy-ile-haftaya-kazancli-baslayin.txt.meta.json` — «Kampanya Süresi Dolmuştur» · bitiş: —
- `vakif-katilim/live/detay-troy-ile-market-harcamalariniza-1000-tlye-varan-iade-1.txt.meta.json` — «Kampanya Süresi Dolmuştur» · bitiş: —
- `vakif-katilim/live/detay-troy-ile-market-harcamalariniza-1000-tlye-varan-iade.txt.meta.json` — «Kampanya Süresi Dolmuştur» · bitiş: —
- `vakif-katilim/live/detay-troy-ile-vergi-odemelerine-vade-farksiz-3-taksit.txt.meta.json` — «Kampanya Süresi Dolmuştur» · bitiş: —
- `vakif-katilim/live/detay-troy-kart-ile-pazaramada-150-tl-indirim.txt.meta.json` — «Kampanya Süresi Dolmuştur» · bitiş: —
- `vakif-katilim/live/detay-troy-kartla-pazaramada-200-tl-indirim.txt.meta.json` — «Kampanya Süresi Dolmuştur» · bitiş: —
- `vakif-katilim/live/detay-troy-kredi-karti-google-playde-kazandiriyor.txt.meta.json` — «Kampanya Süresi Dolmuştur» · bitiş: —
- `vakif-katilim/live/detay-troy-kredi-karti-ile-250-tl-lcw-hediye-ceki.txt.meta.json` — «Kampanya Süresi Dolmuştur» · bitiş: —
- `vakif-katilim/live/detay-troy-kredi-karti-ile-50si-bizden.txt.meta.json` — «Kampanya Süresi Dolmuştur» · bitiş: —
- `vakif-katilim/live/detay-troy-kredi-karti-ile-a101-hediye-ceki-kampanyasi.txt.meta.json` — «Kampanya Süresi Dolmuştur» · bitiş: —
- `vakif-katilim/live/detay-troy-kredi-karti-ile-a101-hediye-ceki.txt.meta.json` — «Kampanya Süresi Dolmuştur» · bitiş: —
- `vakif-katilim/live/detay-troy-kredi-karti-ile-egitimde-vade-farksiz-5-taksit.txt.meta.json` — «Kampanya Süresi Dolmuştur» · bitiş: —
- `vakif-katilim/live/detay-troy-kredi-karti-ile-giyim-yemek-ve-market-sektorleri-harcamalarina-1000-t.txt.meta.json` — «Kampanya Süresi Dolmuştur» · bitiş: —
- `vakif-katilim/live/detay-troy-kredi-karti-ile-lcw-hediye-ceki.txt.meta.json` — «Kampanya Süresi Dolmuştur» · bitiş: —
- `vakif-katilim/live/detay-vakif-katilim-aile-yili-paketi.txt.meta.json` — «Kampanya Süresi Dolmuştur» · bitiş: —
- `vakif-katilim/live/detay-vakif-katilim-dan-genclere-ucuran-firsat.txt.meta.json` — «Kampanya Süresi Dolmuştur» · bitiş: —
- `vakif-katilim/live/detay-vakif-katilim-troy-kredi-karti-ile-ucak-bileti-odemelerinizi-yapin-5-tk-pa.txt.meta.json` — «Kampanya Süresi Dolmuştur» · bitiş: —
- `vakif-katilim/live/detay-vakif-katilimli-olanlara-floda-400-tl-indirim.txt.meta.json` — «Kampanya Süresi Dolmuştur» · bitiş: —
- `vakif-katilim/live/detay-vakif-katilimlilar-davet-et-kazanla-kazaniyor.txt.meta.json` — «Kampanya Süresi Dolmuştur» · bitiş: —
- `vakif-katilim/live/detay-vakif-katilimlilara-ozel-sosyopixte-20-indirim.txt.meta.json` — «Kampanya Süresi Dolmuştur» · bitiş: —
- `vakif-katilim/live/detay-vergi-odemelerine-vade-farksiz-3-taksit.txt.meta.json` — «Kampanya Süresi Dolmuştur» · bitiş: —
- `vakif-katilim/live/detay-vkart-igdas-fatura-kampanyasi.txt.meta.json` — «Kampanya Süresi Dolmuştur» · bitiş: —
- `vakif-katilim/live/detay-vkart-ile-10-hotic-indirimi.txt.meta.json` — «Kampanya Süresi Dolmuştur» · bitiş: —
- `vakif-katilim/live/detay-vkart-ile-15-b-fit-indirimi.txt.meta.json` — «Kampanya Süresi Dolmuştur» · bitiş: —
- `vakif-katilim/live/detay-vkart-ile-15-cicek-sepeti-indirimi.txt.meta.json` — «Kampanya Süresi Dolmuştur» · bitiş: —
- `vakif-katilim/live/detay-vkart-ile-a101-hediye-ceki.txt.meta.json` — «Kampanya Süresi Dolmuştur» · bitiş: —
- `vakif-katilim/live/detay-vkart-ile-arzumda-25-indirim.txt.meta.json` — «Kampanya Süresi Dolmuştur» · bitiş: —
- `vakif-katilim/live/detay-vkart-ile-babalar-gunu-hediyesi-tek-saatte.txt.meta.json` — «Kampanya Süresi Dolmuştur» · bitiş: —
- `vakif-katilim/live/detay-vkart-ile-biletcom-etkinlik-biletleri-indirimli.txt.meta.json` — «Kampanya Süresi Dolmuştur» · bitiş: —
- `vakif-katilim/live/detay-vkart-ile-english-time-15-indirimli.txt.meta.json` — «Kampanya Süresi Dolmuştur» · bitiş: —
- `vakif-katilim/live/detay-vkart-ile-lcw-hediye-ceki-1.txt.meta.json` — «Kampanya Süresi Dolmuştur» · bitiş: —
- `vakif-katilim/live/detay-vkart-ile-lcw-hediye-ceki.txt.meta.json` — «Kampanya Süresi Dolmuştur» · bitiş: —
- `vakif-katilim/live/detay-vkart-ile-sarj-et-yola-devam-et-1.txt.meta.json` — «Kampanya Süresi Dolmuştur» · bitiş: —
- `vakif-katilim/live/detay-vkart-ile-sarj-et-yola-devam-et.txt.meta.json` — «Kampanya Süresi Dolmuştur» · bitiş: —
- `vakif-katilim/live/detay-vkart-ile-yolunuz-acik-biletiniz-indirimli-olsun.txt.meta.json` — «Kampanya Süresi Dolmuştur» · bitiş: —
- `vakif-katilim/live/detay-vkart-mastercard-ile-3-gb-internet-firsati.txt.meta.json` — «Kampanya Süresi Dolmuştur» · bitiş: —
- `vakif-katilim/live/detay-vkart-mastercard-ile-ikeada-1000-tl-indirim.txt.meta.json` — «Kampanya Süresi Dolmuştur» · bitiş: —
- `vakif-katilim/live/detay-yemeksepetinde-troy-indirimi.txt.meta.json` — «Kampanya Süresi Dolmuştur» · bitiş: —
- `vakif-katilim/live/detay-yolunuz-acik-sigortaniz-taksitli-olsun.txt.meta.json` — «Kampanya Süresi Dolmuştur» · bitiş: —
- `ziraat-katilim/live/kart-kampanyalari-19-mayisa-ozel-toplam-450-tl-bankkart-lira.txt.meta.json` — «Tarihinde Sona Ermiştir» · bitiş: 2026-05-24
- `ziraat-katilim/live/kart-kampanyalari-23-nisana-ozel-toplam-1000-tl-bankkart-lira.txt.meta.json` — «Tarihinde Sona Ermiştir» · bitiş: 2026-04-30
- `ziraat-katilim/live/kart-kampanyalari-aile-karta-ozel-2000-tlye-varan-bankkart-lira-0.txt.meta.json` — «Tarihinde Sona Ermiştir» · bitiş: 2026-07-09
- `ziraat-katilim/live/kart-kampanyalari-aile-karta-ozel-2000-tlye-varan-bankkart-lira-1-2.txt.meta.json` — «Tarihinde Sona Ermiştir» · bitiş: 2026-08-07
- `ziraat-katilim/live/kart-kampanyalari-aile-karta-ozel-2000-tlye-varan-bankkart-lira.txt.meta.json` — «Tarihinde Sona Ermiştir» · bitiş: 2026-06-08
- `ziraat-katilim/live/kart-kampanyalari-ajette-6-taksit.txt.meta.json` — «Tarihinde Sona Ermiştir» · bitiş: 2026-03-31
- `ziraat-katilim/live/kart-kampanyalari-akaryakit-harcamalariniza-400-tl-bankkart-lira-0.txt.meta.json` — «Tarihinde Sona Ermiştir» · bitiş: 2026-05-08
- `ziraat-katilim/live/kart-kampanyalari-akaryakit-harcamalariniza-400-tl-bankkart-lira-1.txt.meta.json` — «Tarihinde Sona Ermiştir» · bitiş: 2026-07-09
- `ziraat-katilim/live/kart-kampanyalari-akaryakit-harcamalariniza-400-tl-bankkart-lira-2-2.txt.meta.json` — «Tarihinde Sona Ermiştir» · bitiş: 2026-08-07
- `ziraat-katilim/live/kart-kampanyalari-akaryakit-harcamalariniza-400-tl-bankkart-lira.txt.meta.json` — «Tarihinde Sona Ermiştir» · bitiş: 2026-06-08
- `ziraat-katilim/live/kart-kampanyalari-anneler-gunune-ozel-toplam-500-tl-bankkart-lira.txt.meta.json` — «Tarihinde Sona Ermiştir» · bitiş: 2026-05-12
- `ziraat-katilim/live/kart-kampanyalari-atasun-optikte-3-taksit.txt.meta.json` — «Tarihinde Sona Ermiştir» · bitiş: 2025-11-30
- `ziraat-katilim/live/kart-kampanyalari-avvada-2-taksit.txt.meta.json` — «Tarihinde Sona Ermiştir» · bitiş: 2026-07-31
- `ziraat-katilim/live/kart-kampanyalari-ayakkabi-dunyasinda-2-taksit.txt.meta.json` — «Tarihinde Sona Ermiştir» · bitiş: 2025-10-31
- `ziraat-katilim/live/kart-kampanyalari-ayakkabi-dunyasinda-4-taksit.txt.meta.json` — «Tarihinde Sona Ermiştir» · bitiş: 2026-02-09
- `ziraat-katilim/live/kart-kampanyalari-babalar-gunune-ozel-toplam-500-tl-bankkart-lira.txt.meta.json` — «Tarihinde Sona Ermiştir» · bitiş: 2026-06-21
- `ziraat-katilim/live/kart-kampanyalari-bagimsiz-karta-ozel-5000-tlye-varan-bankkart-lira-0.txt.meta.json` — «Tarihinde Sona Ermiştir» · bitiş: 2026-07-09
- `ziraat-katilim/live/kart-kampanyalari-bagimsiz-karta-ozel-5000-tlye-varan-bankkart-lira.txt.meta.json` — «Tarihinde Sona Ermiştir» · bitiş: 2026-06-08
- `ziraat-katilim/live/kart-kampanyalari-bilet-dukkaninda-300-tlye-varan-indirim.txt.meta.json` — «Tarihinde Sona Ermiştir» · bitiş: 2025-06-30
- `ziraat-katilim/live/kart-kampanyalari-bilet-dukkaninda-500-tlye-varan-indirim.txt.meta.json` — «Tarihinde Sona Ermiştir» · bitiş: 2025-10-31
- `ziraat-katilim/live/kart-kampanyalari-chakrada-6-taksit.txt.meta.json` — «Tarihinde Sona Ermiştir» · bitiş: 2025-09-30
- `ziraat-katilim/live/kart-kampanyalari-continentalde-4-taksit.txt.meta.json` — «Tarihinde Sona Ermiştir» · bitiş: 2026-03-31
- `ziraat-katilim/live/kart-kampanyalari-daikinde-12-taksit.txt.meta.json` — «Tarihinde Sona Ermiştir» · bitiş: 2026-07-31
- `ziraat-katilim/live/kart-kampanyalari-dysonda-pesin-fiyatina-6-taksit.txt.meta.json` — «Tarihinde Sona Ermiştir» · bitiş: 2026-06-15
- `ziraat-katilim/live/kart-kampanyalari-e-ticaret-alisverislerinize-toplam-500-tl-bankkart-lira-0.txt.meta.json` — «Tarihinde Sona Ermiştir» · bitiş: 2026-06-08
- `ziraat-katilim/live/kart-kampanyalari-e-ticaret-alisverislerinize-toplam-500-tl-bankkart-lira-1.txt.meta.json` — «Tarihinde Sona Ermiştir» · bitiş: 2026-07-09
- `ziraat-katilim/live/kart-kampanyalari-e-ticaret-alisverislerinize-toplam-500-tl-bankkart-lira.txt.meta.json` — «Tarihinde Sona Ermiştir» · bitiş: 2026-05-08
- `ziraat-katilim/live/kart-kampanyalari-elektrikli-arac-sarj-istasyonlarinda-750-tl-bankkart-lira.txt.meta.json` — «Tarihinde Sona Ermiştir» · bitiş: 2026-07-09
- `ziraat-katilim/live/kart-kampanyalari-elektrikli-sarj-istasyonlarinda-750-tl-bankkart-lira-0.txt.meta.json` — «Tarihinde Sona Ermiştir» · bitiş: 2026-06-08
- `ziraat-katilim/live/kart-kampanyalari-elektrikli-sarj-istasyonlarinda-750-tl-bankkart-lira.txt.meta.json` — «Tarihinde Sona Ermiştir» · bitiş: 2026-05-08
- `ziraat-katilim/live/kart-kampanyalari-elektronik-ve-beyaz-esya-alisverislerinize-3000-tl-bankkart-li-2.txt.meta.json` — «Tarihinde Sona Ermiştir» · bitiş: 2026-07-09
- `ziraat-katilim/live/kart-kampanyalari-elektronik-ve-beyaz-esya-alisverislerinize-3000-tl-bankkart-li-3.txt.meta.json` — «Tarihinde Sona Ermiştir» · bitiş: 2026-05-08
- `ziraat-katilim/live/kart-kampanyalari-elektronik-ve-beyaz-esya-alisverislerinize-3000-tl-bankkart-li.txt.meta.json` — «Tarihinde Sona Ermiştir» · bitiş: 2026-06-08
- `ziraat-katilim/live/kart-kampanyalari-evideada-2-taksit.txt.meta.json` — «Tarihinde Sona Ermiştir» · bitiş: 2026-02-28
- `ziraat-katilim/live/kart-kampanyalari-giyim-ve-ayakkabi-alisverisinizde-toplam-1000-tl-bankkart-lira-2.txt.meta.json` — «Tarihinde Sona Ermiştir» · bitiş: 2026-07-09
- `ziraat-katilim/live/kart-kampanyalari-giyim-ve-ayakkabi-alisverisinizde-toplam-1000-tl-bankkart-lira-4.txt.meta.json` — «Tarihinde Sona Ermiştir» · bitiş: 2026-05-08
- `ziraat-katilim/live/kart-kampanyalari-giyim-ve-ayakkabi-alisverisinizde-toplam-1000-tl-bankkart-lira.txt.meta.json` — «Tarihinde Sona Ermiştir» · bitiş: 2026-06-08
- `ziraat-katilim/live/kart-kampanyalari-gumussuyunda-9-taksit.txt.meta.json` — «Tarihinde Sona Ermiştir» · bitiş: 2025-11-30
- `ziraat-katilim/live/kart-kampanyalari-hafta-ici-her-gun-ilk-ulasimin-troy-kartla-ucretsiz.txt.meta.json` — «Tarihinde Sona Ermiştir» · bitiş: 2026-06-30
- `ziraat-katilim/live/kart-kampanyalari-hafta-ici-troy-kartla-ilk-ulasimin-ucretsiz.txt.meta.json` — «Tarihinde Sona Ermiştir» · bitiş: 2026-05-26
- `ziraat-katilim/live/kart-kampanyalari-hava-yolu-bilet-aliminiza-1500-tl-bankkart-lira-0.txt.meta.json` — «Tarihinde Sona Ermiştir» · bitiş: 2026-06-08
- `ziraat-katilim/live/kart-kampanyalari-hava-yolu-bilet-aliminiza-1500-tl-bankkart-lira-1.txt.meta.json` — «Tarihinde Sona Ermiştir» · bitiş: 2026-07-09
- `ziraat-katilim/live/kart-kampanyalari-hava-yolu-bilet-aliminiza-1500-tl-bankkart-lira.txt.meta.json` — «Tarihinde Sona Ermiştir» · bitiş: 2026-05-08
- `ziraat-katilim/live/kart-kampanyalari-hoticte-6-taksit.txt.meta.json` — «Tarihinde Sona Ermiştir» · bitiş: 2025-11-30
- `ziraat-katilim/live/kart-kampanyalari-ilk-bankkart-kredi-kartiniza-5000-tl-bankkart-lira-0.txt.meta.json` — «Tarihinde Sona Ermiştir» · bitiş: 2026-07-09
- `ziraat-katilim/live/kart-kampanyalari-ilk-bankkart-kredi-kartiniza-5000-tl-bankkart-lira.txt.meta.json` — «Tarihinde Sona Ermiştir» · bitiş: 2026-06-08
- `ziraat-katilim/live/kart-kampanyalari-ilk-ek-kredi-kartiniza-1000-tl-bankkart-lira-0.txt.meta.json` — «Tarihinde Sona Ermiştir» · bitiş: 2026-07-09
- `ziraat-katilim/live/kart-kampanyalari-ilk-ek-kredi-kartiniza-1000-tl-bankkart-lira.txt.meta.json` — «Tarihinde Sona Ermiştir» · bitiş: 2026-06-08
- `ziraat-katilim/live/kart-kampanyalari-imannoorda-12-taksit.txt.meta.json` — «Tarihinde Sona Ermiştir» · bitiş: 2025-12-31
- `ziraat-katilim/live/kart-kampanyalari-jumboda-5-taksit.txt.meta.json` — «Tarihinde Sona Ermiştir» · bitiş: 2026-04-30
- `ziraat-katilim/live/kart-kampanyalari-kafe-ve-restoran-harcamalariniza-toplam-450-tl-bankkart-lira-0.txt.meta.json` — «Tarihinde Sona Ermiştir» · bitiş: 2026-06-08
- `ziraat-katilim/live/kart-kampanyalari-kafe-ve-restoran-harcamalariniza-toplam-450-tl-bankkart-lira-1.txt.meta.json` — «Tarihinde Sona Ermiştir» · bitiş: 2026-07-09
- `ziraat-katilim/live/kart-kampanyalari-kafe-ve-restoran-harcamalariniza-toplam-450-tl-bankkart-lira.txt.meta.json` — «Tarihinde Sona Ermiştir» · bitiş: 2026-05-08
- `ziraat-katilim/live/kart-kampanyalari-koctasta-2-taksit.txt.meta.json` — «Tarihinde Sona Ermiştir» · bitiş: 2026-03-31
- `ziraat-katilim/live/kart-kampanyalari-kultur-sanat-harcamalariniza-toplam-500-tl-bankkart-lira-0.txt.meta.json` — «Tarihinde Sona Ermiştir» · bitiş: 2026-06-08
- `ziraat-katilim/live/kart-kampanyalari-kultur-sanat-harcamalariniza-toplam-500-tl-bankkart-lira-1.txt.meta.json` — «Tarihinde Sona Ermiştir» · bitiş: 2026-07-09
- `ziraat-katilim/live/kart-kampanyalari-kultur-sanat-harcamalariniza-toplam-500-tl-bankkart-lira.txt.meta.json` — «Tarihinde Sona Ermiştir» · bitiş: 2026-05-08
- `ziraat-katilim/live/kart-kampanyalari-kurban-bayramina-ozel-toplam-2500-tl-bankkart-lira.txt.meta.json` — «Tarihinde Sona Ermiştir» · bitiş: 2026-05-31
- `ziraat-katilim/live/kart-kampanyalari-limasollu-naci-yayinlarinda-tum-indirimlere-ek-10-indirim.txt.meta.json` — «Tarihinde Sona Ermiştir» · bitiş: 2026-01-31
- `ziraat-katilim/live/kart-kampanyalari-lukoilde-3-indirim.txt.meta.json` — «Tarihinde Sona Ermiştir» · bitiş: 2025-12-31
- `ziraat-katilim/live/kart-kampanyalari-market-alisverislerinize-toplam-1000-tl-bankkart-lira-1.txt.meta.json` — «Tarihinde Sona Ermiştir» · bitiş: 2026-06-08
- `ziraat-katilim/live/kart-kampanyalari-market-alisverislerinize-toplam-1000-tl-bankkart-lira.txt.meta.json` — «Tarihinde Sona Ermiştir» · bitiş: 2026-05-08
- `ziraat-katilim/live/kart-kampanyalari-market-alisverislerinize-toplam-1500-tl-bankkart-lira.txt.meta.json` — «Tarihinde Sona Ermiştir» · bitiş: 2026-07-09
- `ziraat-katilim/live/kart-kampanyalari-mitsubishi-electricte-3-taksit.txt.meta.json` — «Tarihinde Sona Ermiştir» · bitiş: 2025-10-31
- `ziraat-katilim/live/kart-kampanyalari-mobilya-alisverisinize-1000-tl-bankkart-lira-1.txt.meta.json` — «Tarihinde Sona Ermiştir» · bitiş: 2026-06-08
- `ziraat-katilim/live/kart-kampanyalari-mobilya-alisverisinize-1000-tl-bankkart-lira.txt.meta.json` — «Tarihinde Sona Ermiştir» · bitiş: 2026-05-08
- `ziraat-katilim/live/kart-kampanyalari-mobilya-alisverisinize-1500-tl-bankkart-lira.txt.meta.json` — «Tarihinde Sona Ermiştir» · bitiş: 2026-07-09
- `ziraat-katilim/live/kart-kampanyalari-modanisada-15-indirim.txt.meta.json` — «Tarihinde Sona Ermiştir» · bitiş: 2025-12-31
- `ziraat-katilim/live/kart-kampanyalari-monster-notebookta-pesin-fiyatina-12-taksit.txt.meta.json` — «Tarihinde Sona Ermiştir» · bitiş: 2026-06-30
- `ziraat-katilim/live/kart-kampanyalari-mtvde-4-taksit-firsatini-kacirmayin.txt.meta.json` — «Tarihinde Sona Ermiştir» · bitiş: 2025-08-06
- `ziraat-katilim/live/kart-kampanyalari-online-dil-okulunda-50-indirim.txt.meta.json` — «Tarihinde Sona Ermiştir» · bitiş: 2025-08-31
- `ziraat-katilim/live/kart-kampanyalari-optik-alisverisinize-500-tl-bankkart-lira-0.txt.meta.json` — «Tarihinde Sona Ermiştir» · bitiş: 2026-06-08
- `ziraat-katilim/live/kart-kampanyalari-optik-alisverisinize-500-tl-bankkart-lira-1.txt.meta.json` — «Tarihinde Sona Ermiştir» · bitiş: 2026-07-09
- `ziraat-katilim/live/kart-kampanyalari-optik-alisverisinize-500-tl-bankkart-lira.txt.meta.json` — «Tarihinde Sona Ermiştir» · bitiş: 2026-05-08
- `ziraat-katilim/live/kart-kampanyalari-otomatik-fatura-odeme-talimatlariniza-450-tlye-varan-bankkart-.txt.meta.json` — «Tarihinde Sona Ermiştir» · bitiş: 2026-03-16
- `ziraat-katilim/live/kart-kampanyalari-pazarama-tatilde-secili-otellerde-5-indirim.txt.meta.json` — «Tarihinde Sona Ermiştir» · bitiş: 2025-09-30
- `ziraat-katilim/live/kart-kampanyalari-qr-ile-odemelerinize-toplam-100-tl-bankkart-lira-0.txt.meta.json` — «Tarihinde Sona Ermiştir» · bitiş: 2026-06-08
- `ziraat-katilim/live/kart-kampanyalari-qr-ile-odemelerinize-toplam-100-tl-bankkart-lira-1.txt.meta.json` — «Tarihinde Sona Ermiştir» · bitiş: 2026-07-09
- `ziraat-katilim/live/kart-kampanyalari-qr-ile-odemelerinize-toplam-100-tl-bankkart-lira.txt.meta.json` — «Tarihinde Sona Ermiştir» · bitiş: 2026-05-08
- `ziraat-katilim/live/kart-kampanyalari-samsungda-6ya-varan-taksit.txt.meta.json` — «Tarihinde Sona Ermiştir» · bitiş: 2025-12-14
- `ziraat-katilim/live/kart-kampanyalari-schaferda-6-taksit.txt.meta.json` — «Tarihinde Sona Ermiştir» · bitiş: 2025-11-30
- `ziraat-katilim/live/kart-kampanyalari-secili-okullarda-pesin-odemelerinize-6-taksit.txt.meta.json` — «Tarihinde Sona Ermiştir» · bitiş: 2026-03-31
- `ziraat-katilim/live/kart-kampanyalari-size-ozel-banka-karti-kampanyasi.txt.meta.json` — «Tarihinde Sona Ermiştir» · bitiş: 2025-09-21
- `ziraat-katilim/live/kart-kampanyalari-sosyopixte-20-indirim.txt.meta.json` — «Tarihinde Sona Ermiştir» · bitiş: 2025-12-31
- `ziraat-katilim/live/kart-kampanyalari-troy-gaziantep-ulasim-kampanyasi.txt.meta.json` — «Tarihinde Sona Ermiştir» · bitiş: 2025-10-27
- `ziraat-katilim/live/kart-kampanyalari-troy-kart-google-play-kampanyasi.txt.meta.json` — «Tarihinde Sona Ermiştir» · bitiş: 2025-09-15
- `ziraat-katilim/live/kart-kampanyalari-troy-kart-yemeksepeti-kampanyasi.txt.meta.json` — «Tarihinde Sona Ermiştir» · bitiş: 2025-11-30
- `ziraat-katilim/live/kart-kampanyalari-troy-kartini-trendyola-kaydedenlere-300-tl-indirim-firsati-0.txt.meta.json` — «Tarihinde Sona Ermiştir» · bitiş: 2026-05-31
- `ziraat-katilim/live/kart-kampanyalari-troy-kartla-biletinial-cocuk-etkinliklerinde-25-indirim.txt.meta.json` — «Tarihinde Sona Ermiştir» · bitiş: 2026-05-31
- `ziraat-katilim/live/kart-kampanyalari-troy-kartla-drda-1000-tlye-varan-indirim.txt.meta.json` — «Tarihinde Sona Ermiştir» · bitiş: 2026-07-15
- `ziraat-katilim/live/kart-kampanyalari-troy-kartla-idefixte-1000-tlye-varan-indirim.txt.meta.json` — «Tarihinde Sona Ermiştir» · bitiş: 2026-04-23
- `ziraat-katilim/live/kart-kampanyalari-troy-kartla-lc-waikikide-300-tl-indirim.txt.meta.json` — «Tarihinde Sona Ermiştir» · bitiş: 2026-07-15
- `ziraat-katilim/live/kart-kampanyalari-troy-kartla-pazaramada-200-tl-indirim.txt.meta.json` — «Tarihinde Sona Ermiştir» · bitiş: 2026-06-30
- `ziraat-katilim/live/kart-kampanyalari-troy-logolu-kartiniza-pazaramada-200-tl-indirim.txt.meta.json` — «Tarihinde Sona Ermiştir» · bitiş: 2026-05-07
- `ziraat-katilim/live/kart-kampanyalari-troy-market-kampanyasi.txt.meta.json` — «Tarihinde Sona Ermiştir» · bitiş: 2025-10-31
- `ziraat-katilim/live/kart-kampanyalari-troy-ramazan-market-kampanyasi.txt.meta.json` — «Tarihinde Sona Ermiştir» · bitiş: 2026-03-22
- `ziraat-katilim/live/kart-kampanyalari-troy-trendyol-kampanyasi.txt.meta.json` — «Tarihinde Sona Ermiştir» · bitiş: 2025-11-15
- `ziraat-katilim/live/kart-kampanyalari-troy-turk-hava-yollari-kampanyasi.txt.meta.json` — «Tarihinde Sona Ermiştir» · bitiş: 2026-03-15
- `ziraat-katilim/live/kart-kampanyalari-troy-tv-premium-yillik-paketinde-50-indirim.txt.meta.json` — «Tarihinde Sona Ermiştir» · bitiş: 2026-05-15
- `ziraat-katilim/live/kart-kampanyalari-vestelde-9-taksit.txt.meta.json` — «Tarihinde Sona Ermiştir» · bitiş: 2026-07-31
- `ziraat-katilim/live/kart-kampanyalari-wall-street-englishte-2-ay-hediye-ders.txt.meta.json` — «Tarihinde Sona Ermiştir» · bitiş: 2026-06-30
- `ziraat-katilim/live/kart-kampanyalari-yolcu360ta-ucak-bileti-alimlariniza-600-tlye-varan-indirim.txt.meta.json` — «Tarihinde Sona Ermiştir» · bitiş: 2026-03-31
- `ziraat-katilim/live/kart-kampanyalari-ziraat-katilim-troy-kart-pazarama-kampanyasi-0.txt.meta.json` — «Tarihinde Sona Ermiştir» · bitiş: 2025-12-17
- `ziraat-katilim/live/kart-kampanyalari-ziraat-katilim-troy-kart-pazarama-kampanyasi.txt.meta.json` — «Tarihinde Sona Ermiştir» · bitiş: 2025-07-16

</details>

## Belirsiz belgeler (71) — dokunulmadı

<details><summary>Liste</summary>

- `albaraka/live/2026-biletcom-ucak-bileti-kampanyasi.txt.meta.json`
- `albaraka/live/2026-uberde-ilk-yolculukta-80-indirim.txt.meta.json`
- `albaraka/live/detay-arcelik-altus-ve-beko-harcamalarinizda-worlde-ozel-9-taksit-firsati.txt.meta.json`
- `albaraka/live/detay-beymen-club-harcamalarinizda-worlde-ozel-6-taksit-firsati.txt.meta.json`
- `albaraka/live/detay-bosch-harcamalarinizda-worlde-ozel-6-taksit-firsati.txt.meta.json`
- `albaraka/live/detay-dyson-harcamalarinizda-worlde-ozel-9-taksit-firsati.txt.meta.json`
- `albaraka/live/detay-hepsiburada-harcamalarinizda-worlde-ozel-6-taksit-firsati.txt.meta.json`
- `albaraka/live/detay-istikbal-bellona-ve-mondihomeda-worlde-ozel-9-taksit-firsati.txt.meta.json`
- `albaraka/live/detay-modalife-harcamalarinizda-worlde-ozel-9-taksit-firsati.txt.meta.json`
- `albaraka/live/detay-opmar-optik-harcamalarinizda-worlde-ozel-6-taksit-firsati.txt.meta.json`
- `albaraka/live/detay-saatandsaat-harcamalarinizda-worlde-ozel-7-taksit-firsati.txt.meta.json`
- `albaraka/live/detay-tatilbudurda-7500-tlye-varan-worldpuan.txt.meta.json`
- `albaraka/live/tr-kampanyalar.txt.meta.json`
- `tom-katilim/live/kampanyalar-a101-de-100tl-kazan.txt.meta.json`
- `tom-katilim/live/kampanyalar-a101-ekstrada-tum-cep-telefonlarina-pesin-fiyatina-3-taksit.txt.meta.json`
- `tom-katilim/live/kampanyalar-a101ekstrada-tum-cep-telefonlarina-pesin-fiyatina-3taksit.txt.meta.json`
- `tom-katilim/live/kampanyalar-biletcomda-aile-etkinliklerinde-yuzde15-indirim.txt.meta.json`
- `tom-katilim/live/kampanyalar-biletcomda-otobus-biletlerinde-40tl-indirim.txt.meta.json`
- `tom-katilim/live/kampanyalar-derindondurucu-ve-klimalarda-pesin-fiyatina-3taksit.txt.meta.json`
- `tom-katilim/live/kampanyalar-hadi-black-kredi-karti-ile-pegasus-harcamalarindan-50-iade-kazan.txt.meta.json`
- `tom-katilim/live/kampanyalar-hadi-davet-koduyla-tom-bank-hadi-musterisi-ol-pegasus-harcamalarinda.txt.meta.json`
- `tom-katilim/live/kampanyalar-hadi-kartlarin-ile-flormarda-200-tl-indirim.txt.meta.json`
- `tom-katilim/live/kampanyalar-hadi-kredi-karti-ile-alldayesim-alisverislerinde-40-indirim.txt.meta.json`
- `tom-katilim/live/kampanyalar-hadi-kredi-karti-ile-kotonda-500-tl-indirim.txt.meta.json`
- `tom-katilim/live/kampanyalar-hadiveresiye-vadefarkinbizden.txt.meta.json`
- `tom-katilim/live/kampanyalar-mastercard-logolu-hadi-kartlarin-ile-ilk-surusun-bizden.txt.meta.json`
- `tom-katilim/live/kampanyalar-mobilya-ve-bisikletlerde-pesin-fiyatina-3taksit.txt.meta.json`
- `tom-katilim/live/kampanyalar-pegasus-davet-koduyla-tom-bank-hadi-musterisi-ol-pegasus-harcamalari.txt.meta.json`
- `tom-katilim/live/kampanyalar-tom-bank-cok-kazananlar-kulubune-ozel-vade-farksiz-3-taksit-cep-tele.txt.meta.json`
- `tom-katilim/live/kampanyalar-tom-bank-hadi-nin-hesapli-kampanyasi.txt.meta.json`
- `tom-katilim/live/kampanyalar-tum-urunlerde-pesin-fiyatina-3-taksit.txt.meta.json`
- `tom-katilim/live/kampanyalar-tv-beyazesya-pesinfiyatina3taksit.txt.meta.json`
- `turkiye-finans/live/bireysel-arsa-finansmani.txt.meta.json`
- `turkiye-finans/live/bireysel-isyeri-finansmani.txt.meta.json`
- `turkiye-finans/live/dis-ticaret-ve-finansmani-dis-ticaret-odeme-yontemleri.txt.meta.json`
- `turkiye-finans/live/ihtiyac-finansmani-ihtiyac-finansmani.txt.meta.json`
- `turkiye-finans/live/kampanyalar-banka-calisanlarina-ozel-ihtiyac-finansmani.txt.meta.json`
- `turkiye-finans/live/kampanyalar-bes-ile-yarininiza-deger-katin.txt.meta.json`
- `turkiye-finans/live/kampanyalar-birikim-fon-kampanyalari.txt.meta.json`
- `turkiye-finans/live/kampanyalar-default.txt.meta.json`
- `turkiye-finans/live/kampanyalar-diger-kampanyalar.txt.meta.json`
- `turkiye-finans/live/kampanyalar-dijital-bankacilik-kampanyalari.txt.meta.json`
- `turkiye-finans/live/kampanyalar-emekliler-haftasina-ozel-avantajlar.txt.meta.json`
- `turkiye-finans/live/kampanyalar-emeklilere-nakit-promosyon.txt.meta.json`
- `turkiye-finans/live/kampanyalar-fatura-2300tl-bonus.txt.meta.json`
- `turkiye-finans/live/kampanyalar-finansman-kampanyalari.txt.meta.json`
- `turkiye-finans/live/kampanyalar-gunluk-hesap-vade-kampanyasi.txt.meta.json`
- `turkiye-finans/live/kampanyalar-ihtiyac-finansmani-kampanyasi.txt.meta.json`
- `turkiye-finans/live/kampanyalar-kamu-calisanlarina-ozel-ihtiyac-finansmani.txt.meta.json`
- `turkiye-finans/live/kampanyalar-kart-kampanyalari.txt.meta.json`
- `turkiye-finans/live/kampanyalar-katilim-hesabi-kampanyasi.txt.meta.json`
- `turkiye-finans/live/kampanyalar-masrafsiz-bankacilik.txt.meta.json`
- `turkiye-finans/live/kampanyalar-mastercard-business-kart-firsat.txt.meta.json`
- `turkiye-finans/live/kampanyalar-odeme-kampanyalari.txt.meta.json`
- `turkiye-finans/live/kampanyalar-sigorta-kampanyalari.txt.meta.json`
- `turkiye-finans/live/kampanyalar-ticari-kampanyalar.txt.meta.json`
- `turkiye-finans/live/kampanyalar-turkiye-finans-avantajlariyla-mobilden-tanis.txt.meta.json`
- `turkiye-finans/live/kampanyalar-tuzel-onbarding-avantaj-paketi.txt.meta.json`
- `turkiye-finans/live/kampanyalar-yakininizi-davet-edin.txt.meta.json`
- `turkiye-finans/live/kampanyalar-yatirim-kampanyalari.txt.meta.json`
- `turkiye-finans/live/kampanyalar-yeni-yatirim-hesabiniza-sifir-komisyon.txt.meta.json`
- `turkiye-finans/live/konut-finansmani-konut-finansmani.txt.meta.json`
- `turkiye-finans/live/nakit-yonetimi-tedarikci-finansmani.txt.meta.json`
- `turkiye-finans/live/tasit-finansmani-tasit-finansmani.txt.meta.json`
- `vakif-katilim/live/detay-dijitalden-musteri-ol-hisse-senedi-islemlerinde-75-komisyon-indirimi-kazan.txt.meta.json`
- `vakif-katilim/live/detay-espressolab-hediye-kahve-kampanyasi.txt.meta.json`
- `vakif-katilim/live/detay-mastercard-ile-enuyguncomda-150-tl-indirim.txt.meta.json`
- `vakif-katilim/live/detay-mastercardla-egitimde-vade-farksiz-5-taksit.txt.meta.json`
- `vakif-katilim/live/detay-vakif-katilimli-olanlara-tabiiden-premium-uyelik.txt.meta.json`
- `vakif-katilim/live/kampanyalar-mevcut-kampanyalar.txt.meta.json`
- `vakif-katilim/live/kendim-icin-kampanyalar.txt.meta.json`

</details>
