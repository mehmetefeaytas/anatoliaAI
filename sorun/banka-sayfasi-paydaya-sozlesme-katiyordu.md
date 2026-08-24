---
title: "Banka sayfası paydaya sözleşme katıyordu: «93 belge · %15 kapsama» yanlış evrenden"
tags: [sorun, panel, kapsama, belge-turu, olcum, banka-sayfasi]
source: "kullanıcı raporu (2026-08-24) + demo.db ölçümü"
date: 2026-08-24
status: stable
---

# Banka sayfası paydaya sözleşme katıyordu

## Belirti

Kullanıcı raporu (2026-08-24), Vakıf Katılım banka sayfası — dokuz kampanya
türünün **sekizi** «ölçülemedi»:

```
Finansman          ölçülemedi   93 belge. veri kapsaması düşük (15%)
Kart               ölçülemedi   76 belge. veri kapsaması düşük (20%)
Yatırım Ürünü      ölçülemedi   53 belge. veri kapsaması düşük (35%)
Konut Finansmanı   ölçülemedi   14 belge. veri kapsaması düşük (25%)
```

Sorulan soru yerindeydi: *"bunlar gerçekten ölçülemedi mi?"*

## Kök neden — payda ile hüküm FARKLI evrenlerden geliyordu

Belge sayısı `GET /campaigns?bank=…` ile geliyordu; o uç **süzgeçsiz**, yani
sözleşmeleri de sayıyordu. Kapsama yüzdesi ise `/advantageous`ten geliyor ve o
uç sözleşmeleri **zaten dışlıyor** (`main.py::_tur_satirlari`,
`base.kiyas_where()` — *"sözleşme hariç, türü BİLİNMEYEN dahil"*).

Ölçüldü (`data/demo.db`, Vakıf Katılım):

| tür | toplam | kampanya | **sözleşme** |
|---|---:|---:|---:|
| Finansman | 93 | 51 | **42** |
| Konut Finansmanı | 14 | 5 | **9** |
| Sınıflandırılamadı | 56 | 22 | **34** |
| Yatırım Ürünü | 53 | 32 | **21** |
| Kart | 76 | 70 | 6 |

Yani «93 belgenin ancak %15'i ölçülebildi» cümlesi hiç kurulmamıştı: %15,
51 belgelik bir kümenin kapsamasıydı. Sayı aritmetik olarak yanlış değildi,
**yanlış nüfusu ölçüyordu**.

## İkinci bulgu — yakalanmayan yüzdeler gerçek oran DEĞİL

"Belki oran metinde var ama çıkarılamıyor" hipotezi de ölçüldü. Vakıf
Katılım Finansman belgelerinde `%` geçen ama `kar_payi_orani` çıkarılmamış
23 belge var; örneklerine bakıldı:

```
#1774  …uyguladığı en yüksek cari akdi kâr payı oranlarının %50 fazlasına kadar…
#1827  …Altına Endeksli Kredilere uygulanan en yüksek cari kâr payı oranlarının %30 fazlası…
#1794  …fatura bedelinin tamamının (%100 ünün) Bankaca Müşteriye…
```

Üçü de **gecikme (temerrüt) kâr payı formülü** ya da finansman oranı — kampanyanın
kâr payı oranı değil. Kural hattı bunları bilerek almıyor; alsaydı
[[llm-yalniz-kural-bosluklarini-doldurur]] kararındaki *yanlış-alan* hatasının
ta kendisi üretilirdi.

**Sonuç: «ölçülemedi» hükmü büyük ölçüde DOĞRU.** Yanlış olan paydaydı.

## Çözüm

1. Payda kıyas evreniyle eşitlendi: `belge_turu === "sozlesme"` olanlar
   sayılmıyor. Süzme `=== "kampanya"` DEĞİL — türü belirlenememiş belge
   kıyasa giriyor ve o kontrolden geçemezdi.
2. Çıkarılan sayı **gizlenmiyor**, satırda yazıyor:

   > Bu türde ayrıca **42 sözleşme belgesi** var; paydaya girmiyorlar.
   > Sözleşmede kâr payı oranı ya da ödül miktarı bulunmaması BEKLENEN bir
   > şeydir — çıkarımın başarısızlığı değil.

## Kalan sınır — ölçütler ürün ailesine göre değişmiyor

Sözleşmeler çıkarıldıktan sonra bile Kart türünde kapsama düşük: 70 kampanya
belgesinin 0'ında `kar_payi_orani`, 0'ında `finansman_tutari` var. Bu bir veri
boşluğu değil **kategori uyuşmazlığı**: bir kart kampanyasında finansman oranı
zaten bulunmaz. Beş ölçütlü tek bir karne, kart kampanyasını uygulanamayan iki
ölçütten ceza almış gibi gösteriyor.

Doğru çözüm ölçüt ağırlıklarını ürün ailesine göre değiştirmek olurdu; teslime
beş gün kala skorlama modelini değiştirmek [[adil-kiyas-garantisi]] doktrinine
dokunur ve ölçülmeden yapılmamalı. **Açık bırakıldı, gizlenmedi.**

## İlgili dosyalar

- `app/web/app/components/BankaSayfasi.tsx` — `turBelgeleri`, `turSozlesmeleri`,
  `sozlesmeNotu`
- `app/src/api/main.py` — `_tur_satirlari` (kıyas evreninin tanımı)

## Sources

- Kullanıcı raporu, 2026-08-24 — Vakıf Katılım banka sayfası çıktısı
- `data/demo.db` — tür × `belge_turu` kırılımı, alan doluluk sayımı
- `data/demo.db` — `#1774`, `#1827`, `#1794` metin örnekleri

## Related

- [[urun-baglami-alan-duzeyinde-tasinmali]] — aynı ailenin başka bir yüzü
- [[llm-yalniz-kural-bosluklarini-doldurur]] — yanlış-alan kapısının gerekçesi
- [[kampanya-metninde-olmayan-oran-banka-yayinindan]] — buradaki gecikme formülü
  örnekleri, oranın metinde OLMADIĞININ üçüncü kanıtı olarak kullanıldı
