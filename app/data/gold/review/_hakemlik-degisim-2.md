# Kalibrasyon Hakemlik — Değişim Kaydı

> `scripts/kalibrasyon_hakemlik.py` üretti. Her değişen hücre burada.
> Geri almak için `.yedek-hakemlik` kopyaları duruyor (silme yok).

## Uygulanan kurallar

- **`deger-bicim`** — gold_value BİÇİMİ kanonikleştirilir: kampanya_suresi -> ISO bitiş tarihi, campaign_type -> 8 sınıfın birebir yazımı

## Özet

| Dosya | satır | değişen | korunan: dolu gold_value | korunan: meşru absent |
|---|---:|---:|---:|---:|
| `round0_kalibrasyon_A.csv` | 260 | 0 | 0 | 19 |
| `round0_kalibrasyon_B.csv` | 260 | 6 | 39 | 2 |
| `round0_kalibrasyon_C.csv` | 260 | 5 | 0 | 6 |
| `round0_kalibrasyon_D.csv` | 260 | 7 | 0 | 10 |

## Değişen hücreler

### `deger-bicim` (18 hücre)

| Dosya | Belge | Alan | eski -> yeni |
|---|---|---|---|
| `round0_kalibrasyon_B.csv` | `albaraka--detay-vade-farksiz-kampanyasi` | `kampanya_suresi` | `01.01.2026 - 31.12.2026` -> `2026-12-31` |
| `round0_kalibrasyon_B.csv` | `kuveyt-turk--finansmanlar-ihtiyac-finansmanlari` | `campaign_type` | `İhtiyaç finansmanı` -> `İhtiyaç Finansmanı` |
| `round0_kalibrasyon_B.csv` | `kuveyt-turk--kampanya-arsivi-business-plus-karttan-vade-farksiz-3-taksit-imkani` | `kampanya_suresi` | `1.07.2023 - 31.08.2023` -> `2023-08-31` |
| `round0_kalibrasyon_B.csv` | `turkiye-emlak-katilim--finansmanlar-ihtiyac-finansmani` | `campaign_type` | `İhtiyaç finansmanı` -> `İhtiyaç Finansmanı` |
| `round0_kalibrasyon_B.csv` | `vakif-katilim--finansmanlar-kentsel-donusum-finansmani` | `campaign_type` | `Konut finansmanı` -> `Konut Finansmanı` |
| `round0_kalibrasyon_B.csv` | `vakif-katilim--finansmanlar-konut-finansmani-2` | `campaign_type` | `Konut finansmanı` -> `Konut Finansmanı` |
| `round0_kalibrasyon_C.csv` | `albaraka--detay-vade-farksiz-kampanyasi` | `kampanya_suresi` | `01.01.2026 - 21.12.2026` -> `2026-12-21` |
| `round0_kalibrasyon_C.csv` | `turkiye-emlak-katilim--kampanya-market-alisverislerinize-1500-tl-parafpara-hediye` | `kampanya_suresi` | `1.07.2026-31.07.2026` -> `2026-07-31` |
| `round0_kalibrasyon_C.csv` | `vakif-katilim--detay-dijitalden-musteri-ol-hisse-senedi-islemlerinde-75-komisyon-indirimi-kazan` | `kampanya_suresi` | `14.12.2021-31.12.2027` -> `2027-12-31` |
| `round0_kalibrasyon_C.csv` | `vakif-katilim--detay-espressolab-hediye-kahve-kampanyasi` | `kampanya_suresi` | `1.01.2026-31.12.2026` -> `2026-12-31` |
| `round0_kalibrasyon_C.csv` | `vakif-katilim--detay-espressolab-hediye-kahve-kampanyasi` | `campaign_type` | `yeni müşteri` -> `Yeni Müşteri` |
| `round0_kalibrasyon_D.csv` | `albaraka--detay-vade-farksiz-kampanyasi` | `campaign_type` | `ihtiyaç finansmanı` -> `İhtiyaç Finansmanı` |
| `round0_kalibrasyon_D.csv` | `albaraka--detay-vade-farksiz-kampanyasi` | `kampanya_suresi` | `01.01.2026 - 31.12.2026` -> `2026-12-31` |
| `round0_kalibrasyon_D.csv` | `kuveyt-turk--kampanya-arsivi-business-plus-karttan-vade-farksiz-3-taksit-imkani` | `campaign_type` | `kart` -> `Kart` |
| `round0_kalibrasyon_D.csv` | `kuveyt-turk--kampanya-arsivi-business-plus-karttan-vade-farksiz-3-taksit-imkani` | `kampanya_suresi` | `1.07.2023 - 31.08.2023` -> `2023-08-31` |
| `round0_kalibrasyon_D.csv` | `turkiye-emlak-katilim--kampanya-paraf-ile-hepsiburadada-pesin-fiyatina-9-aya-varan-taksit-firsati` | `campaign_type` | `kart` -> `Kart` |
| `round0_kalibrasyon_D.csv` | `vakif-katilim--detay-dijitalden-musteri-ol-hisse-senedi-islemlerinde-75-komisyon-indirimi-kazan` | `kampanya_suresi` | `14.12.2021-31.12.2027` -> `2027-12-31` |
| `round0_kalibrasyon_D.csv` | `vakif-katilim--detay-espressolab-hediye-kahve-kampanyasi` | `kampanya_suresi` | `1.01.2026-31.12.2026` -> `2026-12-31` |

