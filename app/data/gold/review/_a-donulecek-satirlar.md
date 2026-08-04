# Kalibrasyon A — dönülecek satırlar

> 2026-08-04 tarihli ilk turun denetimi. Yapıştırdığınız 195 cevap CSV'nin
> gerçek satır sırasıyla hizalandı ve her `gold_value` `parse_gold_value()`'dan
> geçirildi. Aşağıdaki satır numaraları **CSV dosyasının satır numarasıdır**
> (başlık satırı 1'dir, yani elektronik tabloda gördüğünüz numara).
>
> Biçim kuralları: `_bicim-karti.md`

---

## A. Sessiz bozulma — 9 satır (en kritik)

Ayrıştırıcı bu hücreleri reddetmiyor, **yanlış ucu alıp devam ediyor.** Hata
mesajı görmezsiniz; gold sete yanlış değer girer.

| CSV satırı | Alan | Yazdığınız | Gold'a giren | Olması gereken |
|---:|---|---|---|---|
| 7 | `kampanya_suresi` | `2026-01-01 - 2026-12-31` | `2026-01-01` | `2026-12-31`, note: `baslangic=2026-01-01` |
| 22 | `kampanya_suresi` | `2023-07-01 - 2023-08-31` | `2023-07-01` | `2023-08-31`, note: `baslangic=2023-07-01` |
| 34 | `kampanya_suresi` | `2026-07-01- 2026-07-31` | `2026-07-01` | **model `2026-07-31` demişti, doğruydu → iki hücreyi de boşalt** |
| 39 | `kampanya_suresi` | `2021-12-14 - 2021-12-31` | `2021-12-14` | `2021-12-31`, note: `baslangic=2021-12-14` |
| 41 | `kampanya_suresi` | `2026-01-01 - 2026-01-31` | `2026-01-01` | `2026-01-31`, note: `baslangic=2026-01-01` |
| 25 | `finansman_tutari` | `{...5000} - {...150000}` | `5000` | `{"value": 150000, "currency": "TRY"}`, note: `alt=5000` |
| 31 | `finansman_tutari` | `{...20000} - {...25000} - …` | `20000` | üst sınır + note'a diğerleri |
| — | `finansman_tutari` | `tutar: 800000 / tutar2: 1700000 / …` | `800000` | tek üst sınır + note'a 7 tutar |
| — | `kar_payi_orani` | `“85 / 15”` | `{"min": 15, "max": 85}` | **`absent`** + note: `#terminoloji paylasim orani` |

Son satır tek başına en pahalısı: **%85 kâr payı oranı** gold sete girer, o
bankayı karşılaştırma tablosunda en pahalı gösterir, üstüne doğru davranıp
hiçbir şey üretmeyen model "kaçırdı" sayılır.

34. satırda düzeltme, modelin **doğru** cevabını yanlışla değiştiriyor.

---

## B. `absent` + değer birlikte — 4 satır

`build_gold` `absent` görünce yazdığınız değeri atar ve modeli **halüsinasyon**
sayar. Oysa model yanlış sınıf verdi, uydurmadı. Doğrusu `fix`.

| CSV satırı | Belge | Alan | Yazdığınız | Olması gereken |
|---:|---|---|---|---|
| 10 | `dunya-katilim--katilma-hesaplari-gunes…` | `campaign_type` | `Günlük Vadeli Hesap` / `absent` | `fix` + `Yatırım Ürünü` |
| 11 | `dunya-katilim--katilma-hesaplari-gunes…` | `vade_ay` | `1` / `absent` | `fix` + `1` |
| 12 | `dunya-katilim--kendim-icin-altin-banka…` | `campaign_type` | `Altın Yatırım Hesabı` / `absent` | `fix` + `Yatırım Ürünü` |
| 23 | `kuveyt-turk--leasing-leasing-sureci-ve…` | `campaign_type` | `Leasing` / `absent` | `fix` + `Finansman` |

`Günlük Vadeli Hesap`, `Altın Yatırım Hesabı`, `Leasing` — üçü de 8 sınıf
dışında; ayrıştırıcı bu metinleri kabul etmiyor.

---

## C. Derlemeyi durduran satırlar

| CSV satırı | Alan | Yazdığınız | Neden durur |
|---:|---|---|---|
| 29 | `vade_ay` | *(boş)* / `fix` | `fix` verildi, değer yok → `unclear` yapın |
| 32 | `kampanya_suresi` | *(boş)* / `fix` | aynı — **ama burası aslında `absent`** (aşağıya bakın) |
| 16 | `vade_ay` | `1 , 3-12` | tamsayı alanına kademe |
| 26 | `vade_ay` | `1 - 36` | tamsayı alanına aralık → `36` |
| 43 | `vade_ay` | `120 -  84` | aralık → `120` |
| 36 | `taksit_sayisi` | `3-6` | aralık → `6` |
| — | `taksit_sayisi` | `3 - 6 -12` | aralık → `12` |
| — | `masraf_durumu` | `{...500} + {...3000} + {...16500}` | tek masraf şeması → toplam `20000` |
| — | `campaign_type` | `Genel Sağlık Yüksek risk içermeyen…` | 8 sınıf dışı serbest metin |
| — | 3 alan | hesap JSON'u (`finansman_tutari`/`vade_ay`/`aylik_kar_orani` bir arada) | her alana yalnız o alanın değeri yazılır |

### 32. satır — turun en pahalı tek etiketi

`turkiye-emlak-katilim--finansmanlar-ih…` · `kampanya_suresi` · model
`2001-11-22` üretmiş. Notunuz doğru teşhis: *"Kanun maddesi ile kampanya
tarihini karıştırmıştır."*

Bu **tam tanımıyla halüsinasyondur** ve `absent` olmalı. `fix` yazıldığında
halüsinasyon metriğinin dışında kalır — yani projenin merkezindeki iddiayı
ölçen etiket kaybolur (kılavuz §3.3).

---

## D. `fix` + aynı değer — 4 satır

`fix` "bu değer yanlış" demektir. Değer doğruysa model haksız yere yanlış sayılır.
Notunuzu koruyup verdict'i **`unclear`** yapın (birden çok ürün var, hangi ürünün
değeri olduğu belirsiz) ya da doğruysa **boş bırakın**.

| CSV satırı | Alan | Değer | Notunuz |
|---:|---|---|---|
| 18 | `vade_ay` | `36` = `36` | birden fazla İhtiyaç Finansmanı ürünü |
| 28 | `kar_payi_orani` | `25.0` = `25.0` | birden fazla yatırım ürünü |
| 38 | `taksit_sayisi` | `3` = `3` | kampanya metinleri karışmış |
| 40 | `taksit_sayisi` | `3` = `3` | kampanya metinleri karışmış |

---

## E. Onayladığınız ama kanonik olmayan 3 satır

Model `tahsis_ucreti` için `{"rate": 0.5}` üretmiş; boş bırakmak = onay. Ama
`tahsis_ucreti` bir **para** alanı, oran tutamıyor — `validate_gold` bunu hata
sayar.

| CSV satırı | Belge |
|---:|---|
| 51 | `albaraka--tasit-finansmani-togg-finans…` |
| 79 | `turkiye-finans--konut-finansmani-konut…` |
| 87 | `turkiye-finans--tasit-finansmani-tasit…` |

"Binde 5" tutara bağlı oransal bir ücret ve şemada yeri yok — **gerçek şema
açığı, sizin hatanız değil.** Şimdilik `unclear` + note: `binde 5, tutara bagli`.
Kalıcı çözüm (oran varyantı eklemek mi, TL'ye çevirmek mi) κ sonrası karar.

---

## F. Değeri tekrar yazılmış ~15 satır

Model doğru olduğu hâlde aynı değer `gold_value`'ya kopyalanmış
(`İhtiyaç Finansmanı`, `6`, `4`, `3`, `Kart`, `Finansman`, `Yatırım Ürünü`,
`{"amount": 0.0, "has_fee": false}`, uzun `kampanya_kosullari` dizileri…).

Kılavuz §3.2 gereği bunlar **`fix` sayılır**. Hepsini boşaltın: boş hücre
zaten "onaylıyorum" demek. Bu satırlar hem model başarısını haksız düşürür hem
κ'yı bozar.

---

## Doğru yapılmışlar — değiştirmeyin

- `kar_payi_orani = 40000.0` → `fix` + `0` ("vade farksız" = oran sıfır). Sıfır
  bir bilgidir, doğru karar.
- Çerez bandındaki "1 yıl"dan üretilmiş `vade_ay = 12` → **`absent`**. Onaylanmış
  halüsinasyon, gold setteki en değerli etiket tipi.
- KVKK saklama süresinden üretilmiş `vade_ay = 12` → **`absent`**. Aynı sınıf.
- `vade_ay = 99` → `fix` + `48`. Metinde 48 var, doğru düzeltme.
- Model boş + metinde de yok → iki hücre de boş. En kalabalık satır tipi,
  baştan sona doğru dolduruldu.
- `hedef_kitle` ve `kampanya_kosullari` liste biçimleri baştan sona kanonik.
