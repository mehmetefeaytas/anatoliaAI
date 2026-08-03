# Kâr Payı Oranı Çapraz Doğrulama Raporu

> Otomatik üretildi: `python -m scripts.crosscheck_rates`. Anotasyon CSV'leri DEĞİŞTİRİLMEZ; bu dosya öneridir.

- **İncelenen satır:** 235
- **Bağımsız kaynak:** bankaların kendi hesaplama uçları / ilan edilen oran tabloları (`data/raw/*/rates/quotes.jsonl`)

| Sonuç | Adet | Oran | Anotasyoncu ne yapmalı |
|---|---:|---:|---|
| `dogrulandi` | 0 | %0.0 | Öneriyi doğrula ve `gold_value`'ya geçir (hızlı) |
| `celisiyor` | 10 | %4.3 | Belgeye bak: kural hatası mı, sayfaya özel kampanya mı? |
| `kaynak_yok` | 224 | %95.3 | Bağımsız kaynak yok — elle anotasyon (makullük kolonuna bak) |
| `fixture` | 1 | %0.4 | Sentetik demo belgesi — kıyas dışı |

## Makullük kontrolü (finansman sayfaları)

Finansman ürün sayfasında **aylık** kâr oranı beklenir; ölçülen gerçek aralık %1,89–%5,99, üst sınır %12 olarak cömert tutuldu. Bu kontrol ilan edilmiş orana ihtiyaç duymadığı için çapraz doğrulamanın ulaşamadığı satırlarda da çalışır.

| Sonuç | Adet | Anlamı |
|---|---:|---|
| `makul` | 32 | değer aylık oran olarak makul |
| `vade_gibi` | 6 | **değer bir VADE gibi görünüyor** (36, 48, 120...) — kural katmanı vadeyi oran sanmış olabilir |
| `sinir_disi` | 1 | aylık oran için fazla yüksek — yıllık oran ya da başka bir alan karışmış olabilir |

<details><summary>Şüpheli değerler</summary>

- `kuveyt-turk--ihtiyac-finansmanlari-bisiklet-finansmani` — çıkarılan **36.0** (güven 0.37, vade_gibi)
- `albaraka--ihtiyac-hac-ve-umre-finansmani` — çıkarılan **36.0** (güven 0.37, vade_gibi)
- `kuveyt-turk--ihtiyac-finansmanlari-elektrikli-arac-sarj-unit` — çıkarılan **36.0** (güven 0.37, vade_gibi)
- `kuveyt-turk--kampanya-arsivi-bisiklet-finansmaninda-enerji-t` — çıkarılan **36.0** (güven 0.40, vade_gibi)
- `ziraat-katilim--ihtiyac-finansmani-aninda-finansman` — çıkarılan **36.0** (güven 0.37, vade_gibi)
- `vakif-katilim--katilma-hesaplari-konut-hesabi` — çıkarılan **20.0** (güven 0.50, sinir_disi)

</details>


## Kural katmanının bu alandaki isabeti

Bağımsız kaynakla kıyaslanabilen **10** satırda kural katmanının isabeti **%0.0**.

Bu, modelin kendi çıktısına değil bankanın ilan ettiği değere karşı ölçülmüş bir sayıdır; gold set doldurulmadan önce elde edilebilen tek gerçek doğruluk göstergesidir.

## Güven skoruna göre isabet

| Model güveni | Doğrulandı | Çelişiyor | İsabet |
|---|---:|---:|---:|
| yüksek (≥0,90) | 0 | 4 | %0.0 |
| düşük (<0,70) | 0 | 6 | %0.0 |

## Tazelik — CSV'deki `model_value` mevcut kuralla uyuşuyor mu?

Anotasyon CSV'lerindeki `model_value`, ön-anotasyonun KOŞTUĞU ANDAKİ model çıktısıdır. Kural katmanı o günden beri değiştiyse anotasyoncu **artık var olmayan bir modelin** çıktısını doğrular; üretilen gold ve ondan çıkan metrikler yanlış modele ait olur.

| Durum | Adet | Anlamı |
|---|---:|---|
| `guncel` | 170 | CSV değeri mevcut kuralın ürettiğiyle aynı |
| `bayat_fazla` | 55 | CSV değer taşıyor, mevcut kural artık üretmiyor (hata düzeltilmiş) |
| `bayat_farkli` | 10 | **mevcut kural FARKLI bir değer üretiyor** |

**65 satır bayat.** Anotasyona başlamadan önce ön-anotasyonun yeniden koşturulması gerekir (`python -m scripts.preannotate`), aksi halde emek eski model çıktısına harcanır.


## Çelişen satırlar (öncelikli inceleme)

| Belge | Banka | Çıkarılan | İlan edilen | Güven |
|---|---|---|---|---:|
| `turkiye-emlak-katilim--bireysel-hesaplar` | turkiye-emlak-katilim | `25.0` | %33.84, %36.27, %36.78, %37.71, %38.73 | 0.50 |
| `albaraka--tasit-finansmani-togg-finansmani` | albaraka | `2.99` | %3.75 | 0.95 |
| `turkiye-emlak-katilim--bireysel-hesaplar` | turkiye-emlak-katilim | `25.0` | %33.84, %36.27, %36.78, %37.71, %38.73 | 0.50 |
| `albaraka--tasit-finansmani-togg-finansmani` | albaraka | `2.99` | %3.75 | 0.95 |
| `turkiye-emlak-katilim--bireysel-hesaplar` | turkiye-emlak-katilim | `25.0` | %33.84, %36.27, %36.78, %37.71, %38.73 | 0.50 |
| `albaraka--tasit-finansmani-togg-finansmani` | albaraka | `2.99` | %3.75 | 0.95 |
| `turkiye-emlak-katilim--bireysel-hesaplar` | turkiye-emlak-katilim | `25.0` | %33.84, %36.27, %36.78, %37.71, %38.73 | 0.50 |
| `albaraka--tasit-finansmani-togg-finansmani` | albaraka | `2.99` | %3.75 | 0.95 |
| `albaraka--ihtiyac-hac-ve-umre-finansmani` | albaraka | `36.0` | %4.0 | 0.37 |
| `kuveyt-turk--ihtiyac-finansmanlari-elektrikli-arac-s` | kuveyt-turk | `36.0` | %3.57 | 0.37 |
