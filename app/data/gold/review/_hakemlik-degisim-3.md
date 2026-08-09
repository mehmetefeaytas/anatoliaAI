# Kalibrasyon Hakemlik — Değişim Kaydı

> `scripts/kalibrasyon_hakemlik.py` üretti. Her değişen hücre burada.
> Geri almak için `.yedek-hakemlik` kopyaları duruyor (silme yok).

## Uygulanan kurallar

- **`taksit-vade`** — belgede 'taksit' hiç geçmiyorsa taksit_sayisi'na yazılan sayı vadedir; değer silinir (kılavuz: vade ayı taksit sayısı DEĞİLDİR)
- **`paylasim-orani`** — belge 'kâr paylaşım oranı' diyorsa X/Y biçimindeki değer paylaşım oranıdır, kâr payı oranı değil; değer silinir
- **`hedef-kitle-etiket`** — hedef_kitle serbest metni izinli dört etikete indirgenir; segment sinyali yoksa ('bireysel müşteriler') silinir, çözülemezse dokunulmaz

## Özet

| Dosya | satır | değişen | korunan: dolu gold_value | korunan: meşru absent |
|---|---:|---:|---:|---:|
| `round0_kalibrasyon_A.csv` | 260 | 4 | 0 | 19 |
| `round0_kalibrasyon_B.csv` | 260 | 20 | 39 | 2 |
| `round0_kalibrasyon_C.csv` | 260 | 6 | 0 | 6 |
| `round0_kalibrasyon_D.csv` | 260 | 14 | 0 | 10 |

## Değişen hücreler

### `taksit-vade` (0 hücre)

_yok_

### `paylasim-orani` (0 hücre)

_yok_

### `hedef-kitle-etiket` (21 hücre)

| Dosya | Belge | Alan | eski -> yeni |
|---|---|---|---|
| `round0_kalibrasyon_B.csv` | `turkiye-emlak-katilim--bireysel-hesaplar` | `hedef_kitle` | `["Bireysel müşteriler, gerçek kişi ticari, sosyal içerik üreticileri, yurt dışında yaşayan vatandaşlar, Üretici tüzel kişiler"]` -> `(boş)` |
| `round0_kalibrasyon_B.csv` | `turkiye-emlak-katilim--finansmanlar-ihtiyac-finansmani` | `hedef_kitle` | `["gerçek kişi bireysel müşteriler"]` -> `(boş)` |
| `round0_kalibrasyon_B.csv` | `turkiye-finans--konut-finansmani-konut-finansmani` | `hedef_kitle` | `⁠["Ev sahibi olmak isteyen bireysel müşteriler (İlk konut alımı yapacaklar ve mevcut konut sahipleri)"]⁠` -> `(boş)` |
| `round0_kalibrasyon_B.csv` | `turkiye-finans--tasit-finansmani-tasit-finansmani-2` | `hedef_kitle` | `["0 km veya 2. el araç satın almak isteyen gerçek kişi bireysel müşteriler"]⁠` -> `(boş)` |
| `round0_kalibrasyon_B.csv` | `albaraka--detay-vade-farksiz-kampanyasi` | `hedef_kitle` | `["Albaraka Mobil veya şube üzerinden banka müşterisi olan yeni bireysel müşteriler ve Albaraka World Kart sahipleri"]⁠` -> `yeni_musteri` |
| `round0_kalibrasyon_B.csv` | `albaraka--tasit-finansmani-togg-finansmani` | `hedef_kitle` | `["Sıfır km Togg otomobil satın almak isteyen bireysel müşteriler"]` -> `(boş)` |
| `round0_kalibrasyon_B.csv` | `dunya-katilim--katilma-hesaplari-gunes-katilma-hesabi` | `hedef_kitle` | `["Gündelik TL tasarruflarını değerlendirmek isteyen bireysel müşteriler (Resmi, kredi ve finansal kuruluşlar hariç)"]⁠` -> `(boş)` |
| `round0_kalibrasyon_B.csv` | `dunya-katilim--kendim-icin-altin-bankaciligi` | `hedef_kitle` | `["Tasarruflarını altın olarak değerlendirmek ve elindeki hurda altınları vadesiz hesaba aktarmak isteyen bireysel müşteriler"]⁠` -> `(boş)` |
| `round0_kalibrasyon_B.csv` | `kuveyt-turk--altin-hesaplari-altina-altin-katilma-hesabi` | `hedef_kitle` | `⁠["Altın birikimlerini kâr payı elde ederek değerlendirmek isteyen bireysel müşteriler"]⁠` -> `(boş)` |
| `round0_kalibrasyon_B.csv` | `kuveyt-turk--finansmanlar-ihtiyac-finansmanlari` | `hedef_kitle` | `⁠["Hac/Umre ziyareti yapacak, eğitim, seyahat, tekne, kira veya bisiklet gibi kişisel ihtiyaçları için finansman arayan bireysel müşteriler"]⁠` -> `(boş)` |
| `round0_kalibrasyon_B.csv` | `tom-katilim--hesaplama-araclari` | `hedef_kitle` | `["Taksitli alışveriş kredisi veya veresiye kredi kullanmak isteyen bireysel müşteriler"]` -> `(boş)` |
| `round0_kalibrasyon_B.csv` | `vakif-katilim--detay-espressolab-hediye-kahve-kampanyasi` | `hedef_kitle` | `["KAHVE davet kodu ile vakıf katılım mobil şube üzerinden ilk kez müşteri olan bireysel müşteriler"]` -> `yeni_musteri` |
| `round0_kalibrasyon_B.csv` | `vakif-katilim--finansmanlar-konut-finansmani-2` | `hedef_kitle` | `["Sıfır veya 2. el konut satın almak isteyen bireysel müşteriler"]` -> `(boş)` |
| `round0_kalibrasyon_C.csv` | `albaraka--tasit-finansmani-togg-finansmani` | `hedef_kitle` | `Bireysel Müşteri` -> `(boş)` |
| `round0_kalibrasyon_C.csv` | `vakif-katilim--detay-espressolab-hediye-kahve-kampanyasi` | `hedef_kitle` | `yeni müşteri` -> `yeni_musteri` |
| `round0_kalibrasyon_D.csv` | `vakif-katilim--detay-dijitalden-musteri-ol-hisse-senedi-islemlerinde-75-komisyon-indirimi-kazan` | `hedef_kitle` | `yeni müşteri` -> `yeni_musteri` |
| `round0_kalibrasyon_D.csv` | `albaraka--detay-vade-farksiz-kampanyasi` | `hedef_kitle` | `yeni müşteri` -> `yeni_musteri` |
| `round0_kalibrasyon_D.csv` | `albaraka--ihtiyac-saglik-harcamalariniz-icin` | `hedef_kitle` | `Bireysel müşteriler` -> `(boş)` |
| `round0_kalibrasyon_D.csv` | `albaraka--tasit-finansmani-togg-finansmani` | `hedef_kitle` | `Bireysel müşteriler` -> `(boş)` |
| `round0_kalibrasyon_D.csv` | `vakif-katilim--detay-espressolab-hediye-kahve-kampanyasi` | `hedef_kitle` | `Vakıf Katılım Mobil Şube üzerinden KAHVE davet koduyla müşteri olan kişiler` -> `yeni_musteri` |
| `round0_kalibrasyon_D.csv` | `vakif-katilim--finansmanlar-konut-finansmani-2` | `hedef_kitle` | `Konut satın almak isteyen bireysel müşteriler` -> `(boş)` |

