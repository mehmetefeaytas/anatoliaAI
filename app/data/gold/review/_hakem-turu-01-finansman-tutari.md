# Hakem turu 01 — `finansman_tutari` ve `alisveris_puani`

**Tarih:** 2026-08-04
**Tetikleyen:** kural katmanının ilk gerçek ölçümü (`eval/reports/20260804-202009`).
Bu iki alan **F1 = 0.000** aldı; sebebini aramak için 20 belgenin tamamı tek tek
karşılaştırıldı.
**Durum:** `celiskili` — karar bekliyor, ikinci anotatör gerekiyor.

## Neden bu belge var

10 tutarsızlığın **hepsi çıkarıcı kusuru değil.** Beşi kod hatası, üçü gold
hatası, ikisi de sözleşmenin kendisinin cevap vermediği belirsizlik.

Bu ayrım yapılmadan çıkarıcıyı 0.000'dan kurtarmak mümkündü — ama yanlış
etiketlere uydurarak. O da metriği süsler, sistemi bozar. CLAUDE.md kural 4
gereği çelişki gizlenmiyor, işaretleniyor.

---

## A. GOLD HATASI ŞÜPHESİ — çıkarıcı bunlara uydurulmamalı

### A1. `turkiye-finans--konut-finansmani` · `finansman_tutari` = 20.000.000

Gold 20.000.000 TRY diyor. Kaynak metin:

> `10.000.001 – 20.000.000  50% 40% 30%`
> `DEĞER > 20 MİLYON TL  40% 30% 20%`

Bu bir **kredi/değer oranı tablosu** ve anahtar sütunu **konutun DEĞERİ**.
Metin bunu kelimesi kelimesine söylüyor: *"DEĞER > 20 MİLYON TL"*. Yani
20.000.000 konutun fiyat dilimidir, **verilen finansman tutarı değildir** —
tablonun söylediği şey "değeri 20 milyonu aşan konutta finansman oranı %40'a
düşer".

**Önerilen karar:** `finansman_tutari` bu belgede **yok** (`absent`). Kredi/değer
oranı bilgisi `kampanya_kosullari`'na ait.

### A2. `turkiye-finans--tasit-finansmani` · `finansman_tutari` = 2.000.000

Aynı hata sınıfı. Kaynak:

> `1.200.000-2.000.000 TL arasında araçlar için maksimum vade süresi 12 aydır`
> `1.200.000-2.000.000 TL arasında %20'si ... 2.000.000 TL üzerinde %0'ı`

2.000.000 **aracın fiyat dilimi**. Metin "arasında araçlar" diyor — özne araç,
finansman değil. Üstelik 2.000.000 üzerinde finansman oranı **%0**, yani o tutar
finanse edilen değil finanse edilmeyen sınır.

**Önerilen karar:** `absent`.

### A3. `albaraka--detay-vade-farksiz-kampanyasi` · `finansman_tutari` = 40.000

Belge **iki ayrı ürünü** birlikte anlatıyor:

| Ürün | Tutar |
|---|---:|
| Pratik Finansman Kart (ihtiyaç finansmanı) | 40.000 TL |
| Vade farksız taksitli alışveriş (kredi kartı) | 100.000 TL |
| **Kampanyanın kendi manşeti** | **140.000 TL** ("Toplamda 140.000 TL'ye kadar") |

Gold alt ürünlerden birini (40.000) seçmiş. Kural katmanı diğerini (100.000)
seçmiş. İkisi de "doğru", ikisi de eksik.

**Önerilen karar:** biçim kartı §3.4'e göre çok ürünlü belgede tek değer
tanımsızdır → `unclear`; ya da manşet değer 140.000 alınıp alt kırılım `note`'a
yazılır. **Karar verilmesi gereken şey hangisinin kural olacağı** — bu belgeye
özel bir seçim değil, sözleşme boşluğu.

### A4. `turkiye-emlak-katilim--kampanya-market-...-1500-tl-parafpara` · `alisveris_puani` = 150

Kaynak:

> "tek seferde yapacağınız 2.500 TL ve üzeri her ... alışverişinize **150 TL**,
> toplamda **1.500 TL** ParafPara verilecektir"

Gold 150 (işlem başına) seçmiş; kampanyanın manşeti ve dosya adı ise 1.500
(toplam). A3 ile **aynı sözleşme boşluğu**: işlem başına ödül mü, toplam ödül mü?

**Önerilen karar:** ikisi de saklanmalı — `alisveris_puani` = toplam üst sınır,
işlem başına değer `note`'a (`islem_basina=150`). Biçim kartının "şemaya sığanı
`gold_value`'ya, sığmayanı `note`'a" ilkesi bunu zaten söylüyor.

---

## B. GERÇEK ÇIKARICI KUSURU — kod düzeltilecek

### B1. Cümle sınırını geçen yakınlık eşleşmesi → halüsinasyon

`extract_tutar` deseni:

```python
r"(finansman|kredi|tutar|limit)[^\d]{0,20}(\d[\d.,]*\s*(?:tl|₺|try|...))"
```

`[^\d]{0,20}` boşluğu **nokta içerebiliyor**, yani eşleşme cümle sınırını
aşıyor. Ölçülen vaka (`turkiye-emlak-katilim--finansmanlar-ihtiyac-finansmani`):

> "...tüketici ihtiyaç **finansmanı** ürünüdür. **Fiyatı 20.000 TL**'ye kadar
> olan cep telefonu alımı amacıyla kullandırılan kredilerin vadesi 12 ayı..."

Tetikleyici bir cümlede, sayı başka cümlede, ve sayı bir **cep telefonu
fiyatı**. Gold doğru olarak `absent` diyor; kural katmanı 20.000 uyduruyor.

Dikkat: bu **A1/A2'nin tam aynı semantik hatası** — varlık fiyatını finansman
tutarı sanmak. Bir kez kodda, iki kez insan anotasyonunda. Yani bu, sözleşmenin
yeterince açık olmadığı bir yer; yalnızca regex kusuru değil.

**Düzeltme:** boşlukta cümle sonu yasak + varlık fiyatı bağlamı (`fiyatı`,
`değeri`, `bedeli`) dışlanır.

### B2. İlk eşleşmeyi almak → aralığın ALT sınırını seçiyor

`pat.search()` ilk eşleşmeyi alıyor, adaylar arasında seçim yapmıyor. Biçim
kartı §3.4 para aralığında **üst sınırı** kanonik sayıyor; kural katmanı tam
tersini yapıyor:

| Belge | Metin | Kural | Gold (üst sınır) |
|---|---|---:|---:|
| `tom-katilim--hesaplama-araclari` | `Finansman Tutarı TL 5.000 TL 150.000 TL` | 5.000 | 150.000 |
| `vakif-katilim--...-kentsel-donusum` | (aralık) | 1.250.000 | 3.000.000 |

`tom-katilim` vakası ayrıca öğretici: o sayılar bir **hesaplama aracının**
kaydırıcı alt/üst sınırları, kampanya tutarı değil. Yani sayfa türü de sinyal.

**Düzeltme:** tüm adaylar toplanır, aralık tespit edilirse üst sınır seçilir.

### B3. Tablo içindeki tutar kaçıyor

`albaraka--tasit-finansmani-togg-finansmani`: gold 1.700.000, kural `null`.
Kaynak gerçek bir ürün tablosu ve sütun adı **"Kredi Tutarı"**:

> `Araç Modeli | Vade (Ay) | Kredi Tutarı | Aylık Kar Oranı`
> `T10F V2 | 48 | 1.700.000 | 2,99%`

Burada gold **doğru** (A1/A2'nin aksine — sütun gerçekten kredi tutarı).
Kural katmanı tablo yapısını okumadığı için kaçırıyor.

**Düzeltme:** `extract_from_rate_table` benzeri bir tablo yolu tutar için de
gerekiyor. Kapsamı büyük; ayrı iş olarak ayrıldı.

### B4. `alisveris_puani` — site kromundan halüsinasyon

Tetikleyici desende çıplak `|puan)` alternatifi var ve **ilk** eşleşme alınıyor.
Ölçülen vaka: `turkiye-finans--konut-finansmani` ve `--tasit-finansmani`
sayfalarında `puan` sözcüğünün geçtiği **tek** yer bir gezinme/blog bağlantısı:

> "3D Secure Nedir, Ne İşe Yarar? **Kredi Notu (Kredi Puanı) Nedir?**"

Bu bir kampanya ödülü değil, sayfa kromu. Üstüne sayı seçimi de gevşek:

```python
num = re.search(r"(\d[\d.,]*)\s*(?:adet\s*)?(?:chip|puan)?", ctx)
```

`(?:chip|puan)?` **opsiyonel**, yani ±30 karakterlik penceredeki *herhangi* bir
sayı kabul ediliyor. Sonuç: iki sayfada da `{"kind":"points","value":10.0}` —
tamamen ilgisiz bir sayı. Bu 19 halüsinasyonun 2'si.

**Düzeltme:** çıplak `puan` tetikleyicisi kaldırılır veya ödül bağlamı
(`kazan`, `hediye`, `iade`, `verilecek`) şart koşulur; soru/gezinme kalıbı
(`Nedir?`, `Nasıl`) dışlanır; sayı bir puan birimine **komşu** olmak zorunda.

### B5. Markalı puan sözlüğü eksik

A4'teki belge ParafPara ödülü veriyor ama tetikleyici sözlükte `ParafPara` yok
(`chip-para`, `bonus puan` var). Katılım bankalarının markalı puanları
tanınmadıkça bu alan sistematik kaçırılır.

**Düzeltme:** `ParafPara`, `Paraf`, `Maximiles`, `WorldPuan`, `Bonus` eklenir.

---

## Sayım

| Sınıf | Adet |
|---|---:|
| Gold hatası şüphesi (A1, A2) | 2 |
| Sözleşme boşluğu, karar gerekiyor (A3, A4) | 2 |
| Gerçek çıkarıcı kusuru (B1, B2×2, B3, B4×2, B5) | 6 |

**Metrik üzerindeki etkisi:** A1 ve A2 düzeltilirse `finansman_tutari`'nın iki
"kaçırması" ortadan kalkar — yani ölçülen 0.000 **kural katmanını hak ettiğinden
kötü gösteriyor.** Bu, raporda dürüstçe belirtilmeli: ilk metrik yalnız modelin
değil, gold setin de kalitesini ölçüyor.

## Sonraki adım

1. B1, B2, B4, B5 düzeltilir (sözleşme açık, tartışma yok).
2. B3 (tablo yolu) ayrı iş.
3. A1–A4 **ikinci anotatör** kararı bekliyor. Tek taraflı değiştirilmez;
   kalibrasyonun anlamı budur.

## Related
- [[_bicim-karti]] — §3.4 para aralığı → üst sınır kuralı
- [[_a-donulecek-satirlar]] — kalibrasyon A'nın dönülecek satırları
