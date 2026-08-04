# Gold Derleme Raporu

> `scripts/build_gold.py` üretti. Elle düzenlemeyin.

- Çıktı: `data/gold/gold.v1.json`
- SHA-256: `ea04e444755210577f6186658f17944256b7fbdfa5c0b5f7eeb9360f3c924b1a`
- Kayıt: **20**
- Çift anote edilmiş kayıt: **0**
- 12/12 alan karara bağlı (recall ÖLÇÜLEBİLİR): **14**
- Kampanya sayılmayıp elenen belge: **0**
- Çelişki (anotatörler ayrıştı): **0**
- Hakemlik bekleyen kayıt: **6**

## Ölçülebilirlik

- **Precision + halüsinasyon oranı:** tüm kayıtlarda ölçülebilir — modelin ürettiği her alan için karar var.
- **Recall:** yalnızca 12/12 kapsanan 14 kayıtta ölçülebilir; diğerlerinde anote edilmemiş alan ile gerçekten olmayan alan ayrılamaz.

## Alan bazında

| Alan | değer | yok (absent) | belirsiz |
|---|---:|---:|---:|
| `kar_payi_orani` | 4 | 14 | 2 |
| `finansman_tutari` | 6 | 13 | 1 |
| `vade_ay` | 11 | 7 | 2 |
| `taksit_sayisi` | 7 | 10 | 3 |
| `tahsis_ucreti` | 2 | 17 | 1 |
| `masraf_durumu` | 7 | 13 | 0 |
| `odul_miktari` | 3 | 17 | 0 |
| `indirim_orani` | 1 | 19 | 0 |
| `alisveris_puani` | 1 | 19 | 0 |
| `kampanya_suresi` | 6 | 14 | 0 |
| `kampanya_kosullari` | 12 | 8 | 0 |
| `hedef_kitle` | 5 | 15 | 0 |

## Zor-vaka etiketleri

| Etiket | Kayıt |
|---|---:|
| `kosullu_aralik` | 1 |

## Belirsiz (unclear) alanlar

Metrik hesabının DIŞINDA tutulur.

| Belge | Alan |
|---|---|
| `kuveyt-turk--finansmanlar-ihtiyac-finansmanlari` | `vade_ay` |
| `turkiye-emlak-katilim--bireysel-hesaplar` | `kar_payi_orani` |
| `turkiye-emlak-katilim--bireysel-hesaplar` | `vade_ay` |
| `turkiye-emlak-katilim--finansmanlar-ihtiyac-finansmani` | `finansman_tutari` |
| `turkiye-emlak-katilim--finansmanlar-ihtiyac-finansmani` | `taksit_sayisi` |
| `turkiye-finans--konut-finansmani-konut-finansmani` | `kar_payi_orani` |
| `turkiye-finans--konut-finansmani-konut-finansmani` | `tahsis_ucreti` |
| `vakif-katilim--detay-dijitalden-musteri-ol-hisse-senedi-islemlerinde-75-komisyon-indirimi-kazan` | `taksit_sayisi` |
| `vakif-katilim--detay-espressolab-hediye-kahve-kampanyasi` | `taksit_sayisi` |
