# Eğitilebilirlik Ayrımı Raporu

> Otomatik üretildi: `python -m scripts.split_trainable`. Elle düzenlemeyin — yeniden koşuda üzerine yazılır.

- **Kaynak:** `data/raw-classic`
- **Toplam belge:** 548
- **Kullanılabilir (`R_UYGUN`):** 502
- **Kullanılamaz:** 46
- **Toplam doğrulaması:** 502 + 46 = 548 (TAMAM)

## Gerekçe Başına Sayım

| Gerekçe | Belge | Oran |
|---|--:|--:|
| `R_UYGUN` | 502 | %91.6 |
| `R_MUKERRER` | 0 | %0.0 |
| `R_KISA` | 0 | %0.0 |
| `R_BOS_KABUK` | 2 | %0.4 |
| `R_BLOG` | 2 | %0.4 |
| `R_URUN_DEGIL` | 5 | %0.9 |
| `R_CERCEVE_AGIRLIKLI` | 37 | %6.8 |

## Banka Başına Dağılım

| Banka | Toplam | Kullanılabilir | MUKERRER | KISA | BOS_KABUK | BLOG | URUN_DEGIL | CERCEVE_AGIRLIKLI |
|---|--:|--:|--:|--:|--:|--:|--:|--:|
| `akbank` | 64 | 62 | 0 | 0 | 0 | 0 | 0 | 2 |
| `denizbank` | 35 | 26 | 0 | 0 | 0 | 0 | 0 | 9 |
| `garanti-bbva` | 64 | 62 | 0 | 0 | 0 | 0 | 0 | 2 |
| `halkbank` | 28 | 22 | 0 | 0 | 0 | 0 | 3 | 3 |
| `ing` | 35 | 34 | 0 | 0 | 0 | 0 | 0 | 1 |
| `is-bankasi` | 41 | 38 | 0 | 0 | 0 | 0 | 0 | 3 |
| `qnb` | 80 | 72 | 0 | 0 | 0 | 2 | 2 | 4 |
| `teb` | 19 | 16 | 0 | 0 | 2 | 0 | 0 | 1 |
| `vakifbank` | 25 | 25 | 0 | 0 | 0 | 0 | 0 | 0 |
| `yapi-kredi` | 104 | 94 | 0 | 0 | 0 | 0 | 0 | 10 |
| `ziraat-bankasi` | 53 | 51 | 0 | 0 | 0 | 0 | 0 | 2 |

## Eşikler

- `SHINGLE_SIZE` = 8 sözcük
- `BOILERPLATE_MIN_DOCS` = 3 belge
- `MIN_CORE_TOKENS` = 12 sözcük
- `MIN_DOC_CHARS` = 200 karakter
- `EMPTY_RESULT_MAX_CHARS` = 600 karakter

Gerekçeler için `scripts/split_trainable.py` sabit yorumlarına bakın.

## Elenen Belgeler

| Gerekçe | doc_id | Krkt | Çekirdek | Ayrıntı |
|---|--:|--:|--:|--:|
| `R_BLOG` | `qnb--akademi-yemek-kartlarinda-qr-kod-kullanmanin-avantajlari-10587` | 5225 | 681 | baslik bolgesinde 'akademi blog' |
| `R_BLOG` | `qnb--kart-sozlugu` | 1252 | 21 | baslik bolgesinde 'sozlugu' |
| `R_BOS_KABUK` | `teb--filenotfound` | 3628 | 130 | cekirdekte 404 isaretcisi: 'sayfa bulunamadi' |
| `R_BOS_KABUK` | `teb--filenotfound-2` | 3062 | 362 | cekirdekte 404 isaretcisi: 'sayfa bulunamadi' |
| `R_CERCEVE_AGIRLIKLI` | `akbank--393-kampanyalar` | 1904 | 251 | listeleme sayfasi: url 'kampanyalar' ile bitiyor (kampanya dizini) |
| `R_CERCEVE_AGIRLIKLI` | `akbank--kampanyalar` | 8461 | 107 | listeleme sayfasi: url 'kampanyalar' ile bitiyor (kampanya dizini) |
| `R_CERCEVE_AGIRLIKLI` | `denizbank--arsivdeki-kampanyalar-deneeme-kampanya-18027` | 56964 | 7 | cekirdek 7 sozcuk < 12 (toplam 7078) |
| `R_CERCEVE_AGIRLIKLI` | `denizbank--kampanya` | 57178 | 0 | listeleme sayfasi: url 'kampanya' ile bitiyor (kampanya dizini) |
| `R_CERCEVE_AGIRLIKLI` | `denizbank--kampanya-afililere-ozel-kampanyalar` | 57191 | 1 | cekirdek 1 sozcuk < 12 (toplam 7103) |
| `R_CERCEVE_AGIRLIKLI` | `denizbank--kampanya-ciftcilerimize-ozel-kampanyalar` | 57198 | 1 | cekirdek 1 sozcuk < 12 (toplam 7103) |
| `R_CERCEVE_AGIRLIKLI` | `denizbank--kampanya-diger-kampanyalar` | 57184 | 1 | cekirdek 1 sozcuk < 12 (toplam 7102) |
| `R_CERCEVE_AGIRLIKLI` | `denizbank--kampanya-emeklilere-ozel-kampanyalar` | 57194 | 1 | cekirdek 1 sozcuk < 12 (toplam 7103) |
| `R_CERCEVE_AGIRLIKLI` | `denizbank--kampanya-isletme-kart-kampanyalari` | 57192 | 3 | cekirdek 3 sozcuk < 12 (toplam 7103) |
| `R_CERCEVE_AGIRLIKLI` | `denizbank--kampanya-kart-kampanyalari` | 57184 | 2 | cekirdek 2 sozcuk < 12 (toplam 7102) |
| `R_CERCEVE_AGIRLIKLI` | `denizbank--kampanya-mobildeniz-firsatlari` | 57188 | 1 | cekirdek 1 sozcuk < 12 (toplam 7102) |
| `R_CERCEVE_AGIRLIKLI` | `garanti-bbva--kampanyalar` | 24906 | 3803 | listeleme sayfasi: url 'kampanyalar' ile bitiyor (kampanya dizini) |
| `R_CERCEVE_AGIRLIKLI` | `garanti-bbva--kampanyalar-2` | 12265 | 612 | listeleme sayfasi: url 'kampanyalar' ile bitiyor (kampanya dizini) |
| `R_CERCEVE_AGIRLIKLI` | `halkbank--bireysel-kampanyalar` | 2296 | 296 | listeleme sayfasi: url 'kampanyalar' ile bitiyor (kampanya dizini) |
| `R_CERCEVE_AGIRLIKLI` | `halkbank--halkbank-kampuste-kampanyalar` | 2061 | 193 | listeleme sayfasi: url 'kampanyalar' ile bitiyor (kampanya dizini) |
| `R_CERCEVE_AGIRLIKLI` | `halkbank--tr-kampanyalar` | 1579 | 205 | listeleme sayfasi: url 'kampanyalar' ile bitiyor (kampanya dizini) |
| `R_CERCEVE_AGIRLIKLI` | `ing--sizin-icin-kampanyalar` | 2774 | 296 | listeleme sayfasi: url 'kampanyalar' ile bitiyor (kampanya dizini) |
| `R_CERCEVE_AGIRLIKLI` | `is-bankasi--kampanyalar` | 6863 | 972 | listeleme sayfasi: url 'kampanyalar' ile bitiyor (kampanya dizini) |
| `R_CERCEVE_AGIRLIKLI` | `is-bankasi--kampanyalar-2` | 7986 | 1147 | listeleme sayfasi: url 'kampanyalar' ile bitiyor (kampanya dizini) |
| `R_CERCEVE_AGIRLIKLI` | `is-bankasi--kampanyalar-3` | 2158 | 276 | listeleme sayfasi: url 'kampanyalar' ile bitiyor (kampanya dizini) |
| `R_CERCEVE_AGIRLIKLI` | `qnb--kampanyalar` | 1936 | 121 | listeleme sayfasi: url 'kampanyalar' ile bitiyor (kampanya dizini) |
| `R_CERCEVE_AGIRLIKLI` | `qnb--kampanyalar-2` | 608 | 53 | listeleme sayfasi: url 'kampanyalar' ile bitiyor (kampanya dizini) |
| `R_CERCEVE_AGIRLIKLI` | `qnb--kampanyalar-arsivdeki-kampanyalar` | 1074 | 137 | listeleme sayfasi: url 'arsivdeki-kampanyalar' ile bitiyor (kampanya dizini) |
| `R_CERCEVE_AGIRLIKLI` | `qnb--kartlar` | 1390 | 3 | cekirdek 3 sozcuk < 12 (toplam 202) |
| `R_CERCEVE_AGIRLIKLI` | `teb--sizin-icin-kampanyalar` | 8499 | 793 | listeleme sayfasi: url 'kampanyalar' ile bitiyor (kampanya dizini) |
| `R_CERCEVE_AGIRLIKLI` | `yapi-kredi--detay-248614` | 27210 | 6 | cekirdek 6 sozcuk < 12 (toplam 3657) |
| `R_CERCEVE_AGIRLIKLI` | `yapi-kredi--detay-248614-2` | 27215 | 7 | cekirdek 7 sozcuk < 12 (toplam 3658) |
| `R_CERCEVE_AGIRLIKLI` | `yapi-kredi--detay-250218` | 27237 | 8 | cekirdek 8 sozcuk < 12 (toplam 3660) |
| `R_CERCEVE_AGIRLIKLI` | `yapi-kredi--detay-250218-2` | 27242 | 9 | cekirdek 9 sozcuk < 12 (toplam 3661) |
| `R_CERCEVE_AGIRLIKLI` | `yapi-kredi--detay-253260` | 27244 | 10 | cekirdek 10 sozcuk < 12 (toplam 3662) |
| `R_CERCEVE_AGIRLIKLI` | `yapi-kredi--kampanyalar` | 7624 | 68 | listeleme sayfasi: url 'kampanyalar' ile bitiyor (kampanya dizini) |
| `R_CERCEVE_AGIRLIKLI` | `yapi-kredi--kampanyalar-2` | 7842 | 121 | listeleme sayfasi: url 'kampanyalar' ile bitiyor (kampanya dizini) |
| `R_CERCEVE_AGIRLIKLI` | `yapi-kredi--kampanyalar-3` | 7392 | 145 | listeleme sayfasi: url 'kampanyalar' ile bitiyor (kampanya dizini) |
| `R_CERCEVE_AGIRLIKLI` | `yapi-kredi--kampanyalar-4` | 7325 | 82 | listeleme sayfasi: url 'kampanyalar' ile bitiyor (kampanya dizini) |
| `R_CERCEVE_AGIRLIKLI` | `yapi-kredi--kategori-kobi` | 28726 | 206 | listeleme sayfasi: url yol parcasi 'kategori' (kategori listelemesi) |
| `R_CERCEVE_AGIRLIKLI` | `ziraat-bankasi--kartlar-yurt-ici-banka-karti-atm-paylasimi` | 1503 | 2 | cekirdek 2 sozcuk < 12 (toplam 202) |
| `R_CERCEVE_AGIRLIKLI` | `ziraat-bankasi--www-bankkart-com-tr` | 2182 | 364 | listeleme sayfasi: url site kokunu gosteriyor (kampanya detayi degil) |
| `R_URUN_DEGIL` | `halkbank--bagislar-yardim-kampanyalari-bagis-ve-kurban-tahsilatlari` | 3790 | 500 | baslik bolgesinde 'bagis ve kurban' |
| `R_URUN_DEGIL` | `halkbank--eylul-halkbanktan-sahan-gokbakarli-yeni-reklam-kampanyasi` | 4344 | 574 | baslik bolgesinde 'reklam kampanyasi' |
| `R_URUN_DEGIL` | `halkbank--mart-milli-dayanisma-kampanyasi` | 1037 | 135 | baslik bolgesinde 'milli dayanisma kampanyasi' |
| `R_URUN_DEGIL` | `qnb--bize-ulasin-kampanya` | 559 | 53 | url parcasi 'bize-ulasin' |
| `R_URUN_DEGIL` | `qnb--yatirimci-iliskileri-kredi-derecelendirme-notlari` | 1295 | 157 | url parcasi 'yatirimci-iliskileri' |

## Uyarılar (elenmedi, bilgi amaçlı)

| doc_id | Krkt | Uyarı |
|---|--:|--:|
| `garanti-bbva--kampanyalar-musteri-ol-genclik-bankaciligi-kampanyasi` | 209636 | cok-kampanyali olabilir ('Kampanya' x735) |
| `garanti-bbva--kampanyalar-faizsiz-kredi-kampanyasi` | 186204 | cok-kampanyali olabilir ('Kampanya' x363) |
| `garanti-bbva--kampanyalar-emeklilik-kampanyasi` | 117845 | cok-kampanyali olabilir ('Kampanya' x341) |
| `akbank--kampanyalar-davet-et-kazan` | 102557 | cok-kampanyali olabilir ('Kampanya' x347) |
| `akbank--kampanyalar-akbank-fon-kampanyasi` | 84534 | cok-kampanyali olabilir ('Kampanya' x254) |
| `garanti-bbva--kampanyalar-musteri-ol-jolly-kampanyasi` | 73262 | cok-kampanyali olabilir ('Kampanya' x206) |

## Çekirdek Uzunluğu Dağılımı (kullanılabilir belgeler)

| Ölçü | Değer |
|---|--:|
| en az | 12 |
| %10 | 40 |
| ortanca | 182 |
| %90 | 831 |
| en çok | 25605 |
