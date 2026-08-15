# Round1 A–B Uyuşmazlık Kalıpları

> `scripts/uyusmazlik_kalibi.py` üretti. Bu dosya bir TARTIŞMA listesidir; hiçbir karar otomatik uygulanmaz.

- Karşılaştırılan: `round1_A.csv` ↔ `round1_B.csv`
- İkisinin de karar verdiği satır: **141**
- Uyuşmazlık: **56**

## Kalıp dağılımı

| Kalıp | Adet | Gold'u bozar mı |
|---|---:|---|
| `etiket-karisikligi` | 3 | hayır — κ'yı düşürür, değeri değiştirmez |
| `bicim-farki` | 1 | hayır — κ'yı düşürür, değeri değiştirmez |
| `yazim-hatasi` | 3 | hayır — κ'yı düşürür, değeri değiştirmez |
| `kapsam-farki` | 27 | evet — iki farklı gold değeri |
| `gercek-fark` | 19 | evet — iki farklı gold değeri |
| `unclear-tarafi` | 3 | hayır — metrik dışı |

**7/56 uyuşmazlık (%12) aynı gold değerini üretiyor** — κ'yı düşüren ama gold'u bozmayan kalıplar. Kalan 49 tanesi gerçek karar farkıdır ve hakemliğe düşer.

## Hangi alan κ'yı yiyor

Gold'u gerçekten bozan uyuşmazlıkların alan dağılımı. Kılavuz revizyonu bu sıraya göre yapılır — en üstteki alan en çok anotatör ayrıştıran alandır.

| Alan | Bozan uyuşmazlık | Payı |
|---|---:|---:|
| `campaign_type` | 15 | %33 |
| `vade_ay` | 13 | %28 |
| `kampanya_kosullari` | 6 | %13 |
| `masraf_durumu` | 4 | %9 |
| `taksit_sayisi` | 2 | %4 |
| `kampanya_suresi` | 2 | %4 |
| `hedef_kitle` | 1 | %2 |
| `finansman_tutari` | 1 | %2 |
| `tahsis_ucreti` | 1 | %2 |
| `odul_miktari` | 1 | %2 |

### Kapsam farkının yönü

- A değer yazdı / B 'yok' dedi: **17**
- A 'yok' dedi / B değer yazdı: **10**

Tek yönlü bir yığılma, bir anotatörün modelin çıktısını sistematik olarak daha kolay kabul ettiğini (ya da reddettiğini) gösterir; bu bir kişi farkı değil, **eşik tanımının eksikliğidir** (ANNOTATION_GUIDE §4.13/8 — değer bu kampanyaya mı ait?).

## Kapsam farkı — biri değer yazdı, diğeri 'yok' dedi (27)

| Belge | Alan | A | B | Not |
|---|---|---|---|---|
| `albaraka--dis-ticaret-finansmanlari-harici-ga` | `campaign_type` | ok `Finansman` | absent `__YOK__` | biri deger yazdi, digeri 'metinde yok' dedi |
| `albaraka--formlar-altin-hesaplarindan-donusum` | `kampanya_kosullari` | absent `__YOK__` | ok `["Vergi kesintileri, Katılma Hesabı'nın ` | biri deger yazdi, digeri 'metinde yok' dedi |
| `albaraka--formlar-genel-kredi-sozlesmesi-ucre` | `campaign_type` | absent `__YOK__` | fix `Finansman` | biri deger yazdi, digeri 'metinde yok' dedi |
| `albaraka--formlar-genel-kredi-sozlesmesi-ucre` | `masraf_durumu` | absent `__YOK__` | fix `{"amount": null, "has_fee": true}` | biri deger yazdi, digeri 'metinde yok' dedi |
| `albaraka--formlar-genel-kredi-sozlesmesi-ucre` | `tahsis_ucreti` | absent `__YOK__` | fix `{"max": 0.25, "min": 0}` | biri deger yazdi, digeri 'metinde yok' dedi |
| `albaraka--gecmis-tarihli-aracfinansmanitalep-` | `campaign_type` | absent `__YOK__` | ok `Finansman` | biri deger yazdi, digeri 'metinde yok' dedi |
| `albaraka--gecmis-tarihli-aracfinansmanitalep-` | `masraf_durumu` | absent `__YOK__` | fix `{"amount": null, "has_fee": true}` | biri deger yazdi, digeri 'metinde yok' dedi |
| `albaraka--sozlesmeler-bayide-finansman-ihtiya` | `kampanya_kosullari` | ok `["Taraflar, işbu Sözleşme gereğince uyul` | absent `__YOK__` | biri deger yazdi, digeri 'metinde yok' dedi |
| `albaraka--tarim-bankaciligi-diger-finansmanla` | `kampanya_kosullari` | ok `["Finansal Kiralama Makine ekipman, trak` | absent `__YOK__` | biri deger yazdi, digeri 'metinde yok' dedi |
| `albaraka--tatiliniz-icin-devre-mulk` | `kampanya_kosullari` | ok `["Albaraka Mobil Mobil Bankacılık Aç Dev` | absent `__YOK__` | biri deger yazdi, digeri 'metinde yok' dedi |
| `albaraka--tr-urun-ve-hizmet-ucretleri` | `kampanya_kosullari` | ok `["1.03.2020 İhtiyaç Finansmanı - % 0.5 -` | absent `__YOK__` | biri deger yazdi, digeri 'metinde yok' dedi |
| `dunya-katilim--hizmetler-doviz-transferi-swif` | `vade_ay` | absent `__YOK__` | ok `12` | biri deger yazdi, digeri 'metinde yok' dedi |
| `dunya-katilim--kredi-kartlari-paraf-platinum-` | `kampanya_kosullari` | ok `["Fizikî alışverişlerde, satıcıya ödemen` | absent `__YOK__` | biri deger yazdi, digeri 'metinde yok' dedi |
| `kuveyt-turk--kart-kampanyalari-dogtas-grubund` | `vade_ay` | ok `5` | absent `__YOK__` | biri deger yazdi, digeri 'metinde yok' dedi |
| `kuveyt-turk--kart-kampanyalari-saglam-busines` | `odul_miktari` | ok `{"currency": "TRY", "value": 300.0}` | absent `__YOK__` | biri deger yazdi, digeri 'metinde yok' dedi |
| `kuveyt-turk--kart-kampanyalari-saglam-busines` | `vade_ay` | ok `3` | absent `__YOK__` | biri deger yazdi, digeri 'metinde yok' dedi |
| `kuveyt-turk--katilma-hesaplari-ara-donem-kar-` | `kampanya_suresi` | ok `__YOK__` | fix `2025-07-09` | biri deger yazdi, digeri 'metinde yok' dedi |
| `kuveyt-turk--katilma-hesaplari-ara-donem-kar-` | `vade_ay` | ok `6` | absent `__YOK__` | biri deger yazdi, digeri 'metinde yok' dedi |
| `kuveyt-turk--medium-bireysel-finansman-talebi` | `campaign_type` | absent `__YOK__` | ok `Finansman` | biri deger yazdi, digeri 'metinde yok' dedi |
| `tom-katilim--kampanyalar-giyim-alisverislerin` | `vade_ay` | ok `6` | absent `__YOK__` | biri deger yazdi, digeri 'metinde yok' dedi |
| `turkiye-emlak-katilim--kartlar-kredi-karti` | `kampanya_suresi` | ok `2026-01-01` | absent `__YOK__` | biri deger yazdi, digeri 'metinde yok' dedi |
| `turkiye-emlak-katilim--qr-kredi-karti-uyelik-` | `campaign_type` | absent `__YOK__` | fix `Kart` | biri deger yazdi, digeri 'metinde yok' dedi |
| `turkiye-finans--kampanyalar-biten-kampanyalar` | `vade_ay` | ok `3` | absent `__YOK__` | biri deger yazdi, digeri 'metinde yok' dedi |
| `vakif-katilim--kendim-icin-finansmanlar` | `campaign_type` | ok `Konut Finansmanı` | absent `__YOK__` | biri deger yazdi, digeri 'metinde yok' dedi |
| `vakif-katilim--kobi-destekli-finansmanlar-kos` | `vade_ay` | ok `36` | absent `__YOK__` | biri deger yazdi, digeri 'metinde yok' dedi |
| `ziraat-katilim--finansman-urunleri-surduruleb` | `vade_ay` | ok `48` | absent `__YOK__` | biri deger yazdi, digeri 'metinde yok' dedi |
| `ziraat-katilim--kart-kampanyalari-mobilya-ali` | `taksit_sayisi` | ok `5` | absent `__YOK__` | biri deger yazdi, digeri 'metinde yok' dedi |

## GERÇEK anlam farkı — hakemlik şart (19)

| Belge | Alan | A | B | Not |
|---|---|---|---|---|
| `albaraka--detay-dijital-musterilere-ozel-prat` | `hedef_kitle` | ok `["mevcut_musteri", "yeni_musteri"]` | fix `[ "yeni_musteri"]` | degerler gercekten ayrisiyor |
| `albaraka--eviniz-icin-prefabrik` | `vade_ay` | ok `24` | fix `36` | degerler gercekten ayrisiyor |
| `albaraka--tarim-bankaciligi-diger-finansmanla` | `campaign_type` | fix `Finansman` | ok `İhtiyaç Finansmanı` | degerler gercekten ayrisiyor |
| `albaraka--tatiliniz-icin-devre-mulk` | `vade_ay` | ok `12` | fix `36` | degerler gercekten ayrisiyor |
| `albaraka--tr-urun-ve-hizmet-ucretleri` | `campaign_type` | fix `Yatırım Ürünü` | fix `Finansman` | degerler gercekten ayrisiyor |
| `albaraka--tr-urun-ve-hizmet-ucretleri` | `masraf_durumu` | ok `{"amount": 0.0, "has_fee": false}` | fix `{"amount": null, "has_fee": true}` | degerler gercekten ayrisiyor |
| `dunya-katilim--kredi-kartlari-paraf-platinum-` | `masraf_durumu` | ok `{"amount": 0.0, "has_fee": false}` | fix `{"amount": null, "has_fee": true}` | degerler gercekten ayrisiyor |
| `kuveyt-turk--bizden-haberler-kuveyt-turkten-1` | `campaign_type` | ok `İhtiyaç Finansmanı` | fix `Finansman` | degerler gercekten ayrisiyor |
| `kuveyt-turk--kampanya-arsivi-hepsiburada-alis` | `campaign_type` | ok `Finansman` | fix `Alışveriş Puanı` | degerler gercekten ayrisiyor |
| `kuveyt-turk--katilma-hesaplari-birikimli-kati` | `campaign_type` | ok `Konut Finansmanı` | fix `Yatırım Ürünü` | degerler gercekten ayrisiyor |
| `tom-katilim--kampanyalar-giyim-alisverislerin` | `taksit_sayisi` | ok `3` | fix `6` | degerler gercekten ayrisiyor |
| `turkiye-emlak-katilim--katilma-hesaplari-zumr` | `vade_ay` | ok `6` | fix `12` | degerler gercekten ayrisiyor |
| `turkiye-finans--katilma-hesaplari-e-katilma-h` | `vade_ay` | ok `6` | fix `15` | degerler gercekten ayrisiyor |
| `turkiye-finans--kobi-dijital-taksitli-ticari-` | `campaign_type` | ok `Yatırım Ürünü` | fix `Finansman` | degerler gercekten ayrisiyor |
| `vakif-katilim--finansmanlar-motosiklet-finans` | `campaign_type` | ok `Finansman` | fix `Taşıt Finansmanı` | degerler gercekten ayrisiyor |
| `vakif-katilim--kendim-icin-detay-ihtiyac-fina` | `vade_ay` | ok `36` | fix `36-24-12` | degerler gercekten ayrisiyor |
| `vakif-katilim--nakdi-finansmanlar-is-yeri-fin` | `campaign_type` | ok `İhtiyaç Finansmanı` | fix `Konut Finansmanı` | degerler gercekten ayrisiyor |
| `ziraat-katilim--kart-kampanyalari-mobilya-ali` | `campaign_type` | ok `Kart` | fix `Alışveriş Puanı` | degerler gercekten ayrisiyor |
| `ziraat-katilim--kart-kampanyalari-troy-kartla` | `finansman_tutari` | fix `None` | ok `{"currency": "TRY", "value": 1000.0}` | degerler gercekten ayrisiyor |

## Yazım hatası — tek/iki karakter (3)

| Belge | Alan | A | B | Not |
|---|---|---|---|---|
| `albaraka--detay-dijital-musterilere-ozel-prat` | `campaign_type` | fix `İhtiyaç Finasmanı` | fix `İhtiyaç Finansmanı` | karakter farki (mesafe=1) |
| `kuveyt-turk--kampanya-arsivi-bisiklet-finansm` | `finansman_tutari` | fix `{"currency": "TRY", "value": 13.882,47}` | ok `{"currency": "TRY", "value": 13.88247}` | karakter farki (mesafe=1) |
| `kuveyt-turk--kampanya-arsivi-hepsiburada-alis` | `finansman_tutari` | fix `{"currency": "TRY", "value": 13.682,22}` | ok `{"currency": "TRY", "value": 13.68222}` | karakter farki (mesafe=1) |

## Etiket karışıklığı — aynı değer, farklı karar (3)

| Belge | Alan | A | B | Not |
|---|---|---|---|---|
| `albaraka--formlar-altin-hesaplarindan-donusum` | `vade_ay` | ok `12` | fix `12` | ayni deger, farkli karar (A=ok, B=fix) |
| `albaraka--formlar-genel-kredi-sozlesmesi-ucre` | `vade_ay` | ok `36` | fix `36` | ayni deger, farkli karar (A=ok, B=fix) |
| `albaraka--gecmis-tarihli-aracfinansmanitalep-` | `kar_payi_orani` | absent `__YOK__` | ok `__YOK__` | ayni deger, farkli karar (A=absent, B=ok) |

## Bir taraf karar veremedi (`unclear`) (3)

| Belge | Alan | A | B | Not |
|---|---|---|---|---|
| `hayat-finans--yatirim-ve-birikim-yatirimci-se` | `campaign_type` | ok `Yatırım Ürünü` | unclear `None` | biri karar veremedi (A=ok, B=unclear) |
| `vakif-katilim--bireysel-bankacilik-vakif-kati` | `campaign_type` | unclear `None` | fix `Yatırım Ürünü` | biri karar veremedi (A=unclear, B=fix) |
| `vakif-katilim--detay-vakif-katilim-aile-yili-` | `campaign_type` | unclear `None` | absent `__YOK__` | biri karar veremedi (A=unclear, B=absent) |

## Biçim farkı — aynı değer, farklı yazım (1)

| Belge | Alan | A | B | Not |
|---|---|---|---|---|
| `albaraka--detay-dijital-musterilere-ozel-prat` | `finansman_tutari` | fix `150000` | fix `{"currency":"TRY","value":150000}` | ayni deger, farkli yazim (kanonikte esitleniyor) |
