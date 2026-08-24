---
title: "Finansman kâr payı oranı kampanya metninde yoktu: bilgi bankanın kendi yayınından alındı"
tags: [sorun, veri-kapsami, kar-payi, finansman-orani, oran-hasadi, olcum]
source: "[[2026-08-25-yayimlanan-finansman-oranlari]]"
date: 2026-08-25
status: stable
---

# Kampanya metninde olmayan oran, bankanın kendi yayınından alındı

## Belirti

Şartname §5.7'nin birinci karşılaştırma ölçütü *"En Düşük Kâr Payı Oranı"*.
Ama `kar_payi_orani` kampanya korpusunun yalnız **%6,1'inde** (164 / 2.708
belge) dolu. *"Hangi bankada en düşük konut finansmanı kâr payı oranı var"*
sorusu yapısal sorgu yoluna gidiyor ve orada ya boş ya çok dar bir cevap
üretiyordu.

Buradaki asıl soru şu: bu bir **çıkarım kusuru** mu, yoksa bilgi gerçekten
metinlerde yok mu? İki cevabın maliyeti bambaşka — birincisi düzeltilecek bir
hata, ikincisi kapatılacak bir veri boşluğu.

## Kök neden — üç bağımsız kanıt, hepsi "bilgi metinde yok" diyor

| Kanıt | Ölçüm | Sonuç |
|---|---|---|
| EVREN `llm-large` boşluk doldurma sondajı | 2026-08-25, 60 aday belge | **0 kabul** |
| Yerel `qwen2.5:7b` sondajı | 2026-08-24, 30 belge | **0 kabul** |
| Metnin kendisi | `%` geçen ama alanı boş belgelerin okunması | yakalanan yüzdeler *gecikme kâr payı formülü* |

İki sondajda da [[llm-yalniz-kural-bosluklarini-doldurur]] kararının iki kabul
kapısı (dayanak + alan) çalıştı; modeller kapılardan geçen **hiçbir** aday
üretemedi. Boşluk doldurma yolu kapalı değil — koşuyor ve bulacak bir şey yok.

Bu, alanın 146'dan 164'e çıkmış olmasıyla çelişmez: ilk koşum (2026-08-24, 120
belge) alınabilecek **18** değeri zaten almıştı, 25 Ağustos sondajı yeni hiçbir
kabul üretmedi. Havuz tükendi.

Üçüncü kanıt en anlatıcı olanı. Aynı örnekler
[[banka-sayfasi-paydaya-sozlesme-katiyordu]] sayfasında da ölçülmüştü:

```
#1774  …uyguladığı en yüksek cari akdi kâr payı oranlarının %50 fazlasına kadar…
#1827  …Altına Endeksli Kredilere uygulanan en yüksek cari kâr payı oranlarının %30 fazlası…
```

Bunlar kampanyanın oranı değil, **gecikmede uygulanacak formül**. Kural hattı
onları bilerek almıyor; alsaydı üretilen şey tam olarak *yanlış-alan*
hatası olurdu ([[bilgi-cikarimi]] — halüsinasyon yasağı).

Bankalar finansman oranını kampanya sayfasında değil **hesaplama araçlarında**
yayımlıyor: ürün sayfasında yalnız etiket duruyor, sayı istemci tarafında
çağrılan bir orandan geliyor.

## Çözüm — üçüncü veri kolu

Aynı refleks daha önce katılma hesabı tarafında verilmişti
([[katilma-hesabi-orani-korpusta-yoktu]]): bilgi korpusta yoksa korpusu
zorlamak yerine yayımlandığı yerden alınır. Bu kez kaynak ortak bir yayın
değil, **bankaların kendisi**.

Dört yeni adaptör yazıldı (`ZiraatKatilimAdapter`, `HayatFinansAdapter`,
`DunyaKatilimAdapter`, `TomKatilimAdapter`); finansman oranı taşıyan banka
sayısı **3'ten 7'ye** çıktı.

| Banka | Finansman kaydı |
|---|---:|
| Dünya Katılım | 56 |
| Türkiye Emlak Katılım | 42 |
| Ziraat Katılım | 31 |
| Albaraka Türk | 16 |
| Hayat Finans | 3 |
| Kuveyt Türk | 3 |
| T.O.M. Katılım | 3 |
| **Toplam** | **154** |

Yüzey üç yerde birden açıldı: `GET /finansman-oranlari` ucu, *Karşılaştırma*
sekmesinin dördüncü görünümü (*Yayımlanan finansman oranları*) ve sohbetin
`finansman_orani` yolu.

## Kritik disiplin — kayıtlar `extracted_fields`e YAZILMIYOR

Bu oranları kampanya alanlarına yazmak `kar_payi_orani` kapsamasını bir gecede
%6,1'den yükseltirdi. Yapılmadı, çünkü **banka düzeyinde yayımlanmış bir oranı
belirli bir kampanyanın alanına yazmak, o belgenin söylemediği bir şeyi ona
atfetmektir.** Kaynak gösterme zinciri (span → belge) kırılır ve ölçülen
kapsama sayısı yalan söylemeye başlar.

Kaynak ayrı tutuluyor, ekranda ayrı etiketleniyor, kıyasa ayrı bir görünüm
olarak giriyor — [[katilma-orani-iki-ayri-buyukluk]] kararının aynısı.

## İkinci disiplin — sohbette YEDEK, ön alma değil

İlk denemede `finansman_orani` yapısal sorgudan **önce** koşuyordu ve
cevaplanabilen soruları çalıyordu. Dört test düştü, dördü de haklıydı:

- *"Konut finansmanı kâr payı oranlarını listele"* yapısal yola ait;
- *"Peki vade?"* takip zinciri kırılıyordu (ilk soru çalınınca bağlam
  devredilemiyor);
- güvenlik seti C03 — *"Ziraat Katılım'ın konut finansmanı kâr payı oranı
  nedir?"* sorusuna **başka bankaların** tablosu basılıyordu; setin yasakladığı
  ikame tam olarak bu;
- tek banka adı geçen soru yapısal yola gitmeli.

Doğru yer yapısal sorgunun **sonrası**: korpus bir şey bulduysa o kazanır,
çünkü kanıtı belgenin span'i. Korpus boş döndüğünde susmak yerine bankanın
kendi yayımladığı oranı göstermek kapsamı genişletiyor. Aynı ders
[[terim-sorusuna-sozlukten-cevap-verilmiyordu]] sayfasında da alınmıştı.

## Yön ters: burada DÜŞÜK oran iyidir

Katılma hesabında yüksek oran iyiydi (kazandığınız), finansmanda düşük oran iyi
(ödediğiniz). Yön yanıt gövdesinde `yon` alanıyla **sunucudan** geliyor; arayüz
sabit yazmıyor. Sabit yazsaydık, sunucu yönü değiştirdiği gün ekran sessizce
yanlış olurdu. Yıllık maliyet oranı da uydurulmuyor: banka yayımlamamışsa
hücrede "yayımlanmadı" yazıyor.

## Yan bulgu — Türkçe İ sessiz kayıp üretiyordu

`"TAŞIT".casefold()` "tasit" değil **"taşit"** veriyor (noktasız ı yerine
noktalı i). Ziraat Katılım ürün adlarını tamamen büyük harfle yayımlıyor; bu
yüzden bankanın bütün taşıt ürünleri kampanya türü eşlemesinden **sessizce**
düşüyor ve kıyas tablosunda hiç görünmüyordu. `tr_fold_ascii()`e geçildi;
Ziraat artık taşıt sıralamasının başında (%3,29). Aynı ailenin başka bir yüzü:
[[turkce-buyuk-harf-yerel-duyarliligi]].

## Kalan sınır — açıkça yazılıyor

Üç banka hâlâ dışarıda ve üçü de kayıtlı:

- **Vakıf Katılım** oranı yalnız robots-engelli PDF'te yayımlıyor; o belgede
  finansman tarafı yok (katılma tarafı elle indirilerek alındı —
  [[merkezi-veri-segment-ayrimini-gizliyor]]).
- **Türkiye Finans** yalnız katılma hesabı tablosu yayımlıyor.
- **Adil Katılım** hiç oran yayımlamıyor.

Ayrıca oranlar bankanın hesaplama aracından geldiği için **bağlayıcı fiyat
değil**; her kayıt bankanın kendi uyarısını `note` alanında taşıyor.

## İlgili dosyalar

- `app/src/scraping/rates.py` — dört yeni adaptör
- `app/src/domain/yayimlanan_oran.py` — yeni (yükleme, aile eşlemesi, sıralama)
- `app/src/api/routers/finansman_orani.py` — yeni (`GET /finansman-oranlari`)
- `app/src/chatbot/finansman_orani.py` — yeni · `bot.py` (yedek sıra),
  `terim_cevabi.py` (oran sorusunu çalmayı bırakıyor)
- `app/web/app/components/FinansmanOranPanel.tsx` — yeni ·
  `ComparePanel.tsx` (dördüncü görünüm) · `lib/api.ts`
- `app/data/raw/<banka>/rates/quotes.jsonl` — 7 banka, 154 finansman kaydı
- `app/tests/test_yayimlanan_oran.py` · `test_rates_yeni_adaptorler.py`

## Sources

- [[2026-08-25-yayimlanan-finansman-oranlari]] — hasadın ve ölçümlerin dökümü
- `app/src/domain/yayimlanan_oran.py` — modül başlığı, ölçüm kaydı (2026-08-25)
- `app/data/raw/*/rates/quotes.jsonl` — `kind == "finansman"` sayımı: 154
- `app/data/demo.db` — `kar_payi_orani`: 146 kural + 18 LLM = 164 / 2.708

## Related

- [[katilma-hesabi-orani-korpusta-yoktu]] — aynı refleksin ilk uygulaması
- [[merkezi-veri-segment-ayrimini-gizliyor]] — banka yayınının merkezî veriden
  farkı, katılma tarafında
- [[katilma-orani-iki-ayri-buyukluk]] — "ayrı büyüklük ayrı tablo" kararı
- [[llm-yalniz-kural-bosluklarini-doldurur]] — iki kabul kapısının gerekçesi
- [[banka-sayfasi-paydaya-sozlesme-katiyordu]] — gecikme formülü örnekleri
- [[kar-payi-orani]] — kavram
- [[urun-karsilastirma]] — kıyasın kendisi
