# Biçim Kartı — `gold_value` nasıl yazılır

> **GEÇİCİ.** Bu kart, kalibrasyon A'nın ilk turunda ortaya çıkan 8 kılavuz
> açığına verilmiş **ara kararları** taşır (2026-08-04). Kalibrasyon turu
> tamamlanıp κ ölçüldükten sonra bu kararlar tartışılır ve kalıcı olanlar
> `ANNOTATION_GUIDE.md`'ye taşınır (kılavuz §8 adım 4).
>
> Buradaki her biçim `scripts/gold_schema.py`'den **ölçülerek** yazıldı,
> tahminle değil. Kart dışı bir biçim yazarsanız `build_gold` durur.

---

## 1. Üç cümlelik karar kuralı

| Durum | verdict | `gold_value` |
|---|---|---|
| Modelin değeri doğru | **boş bırak** | **boş bırak** |
| Değer yanlış, doğrusunu biliyorum | `fix` | doğru değer (zorunlu) |
| Metinde böyle bir değer **yok** | `absent` | **boş bırak** |
| Metin belirsiz, karar veremiyorum | `unclear` | boş bırak |

Üç tuzak, üçü de A dosyasında görüldü:

1. **Doğru değeri `gold_value`'ya tekrar yazmak `fix` sayılır.** Kılavuz §3.2:
   verdict boş + gold_value dolu → sistem `fix` varsayar. Model doğruysa **iki
   hücreyi de boş bırakın**; yazdığınız her tekrar, modeli haksız yere yanlış
   gösterir.
2. **`absent` + değer birlikte olamaz.** `build_gold.py:142` `absent` görünce
   yazdığınız değeri **sessizce atar** ve modeli halüsinasyon sayar. Değeri
   biliyorsanız kural `fix`'tir. `absent` yalnızca "metinde hiçbir değer yok"
   demektir.
3. **`fix` + boş `gold_value` derlemeyi durdurur** (`build_gold.py:147`).
   Doğru değeri bilmiyorsanız `unclear` yazın.

---

## 2. Kanonik biçimler (ölçülmüş)

| Alan | Kabul edilen **tek** biçim | Örnek |
|---|---|---|
| `kar_payi_orani`, `indirim_orani` | sayı **ya da** `{"min": a, "max": b}` (`a < b`) | `1.89` · `{"min": 1.99, "max": 2.49}` |
| `finansman_tutari`, `tahsis_ucreti`, `odul_miktari` | `{"value": sayı, "currency": "TRY"}` | `{"value": 40000, "currency": "TRY"}` |
| `vade_ay`, `taksit_sayisi` | **pozitif tamsayı** (0 bile geçmez) | `36` |
| `kampanya_suresi` | **tek** ISO tarih | `2026-07-31` |
| `masraf_durumu` | `{"has_fee": true\|false, "amount": sayı}` | `{"has_fee": false, "amount": 0}` |
| `alisveris_puani` | `{"kind": "rate"\|"points", "value": sayı}` | `{"kind": "rate", "value": 5}` |
| `hedef_kitle` | liste, yalnız 4 etiket | `["yeni_musteri"]` |
| `kampanya_kosullari` | metin listesi | `["...", "..."]` |
| `campaign_type` | 8 türden **birebir biri** | `Yatırım Ürünü` |

> **Para, vade, taksit ve tarih alanlarında aralık biçimi YOKTUR.** Şema tek
> değer alır. Aralık yazarsanız ikisinden biri olur: ya derleme durur
> (`vade_ay: "1 - 36"`), ya da **sessizce yanlış ucu alır**
> (`"2026-07-01 - 2026-07-31"` → `2026-07-01`). İkincisi daha tehlikelidir.

### 8 kampanya türü — birebir bu yazımlar

`Finansman` · `İhtiyaç Finansmanı` · `Konut Finansmanı` · `Taşıt Finansmanı` ·
`Kart` · `Alışveriş Puanı` · `Yeni Müşteri` · `Yatırım Ürünü`

Kılavuzda bu alanın bölümü hiç yoktu; 260 satırın 20'si bu alan.

---

## 3. Ara kararlar — kılavuzun cevaplamadığı 8 vaka

Hepsinin ortak mantığı: **şemaya sığanı `gold_value`'ya, sığmayanı `note`'a
yaz.** Böylece hiçbir bilgi kaybolmaz ve şema sonradan genişletilirse yeniden
anotasyon gerekmez.

| # | Vaka | Ara karar |
|---|---|---|
| 1 | Kampanya hem başlangıç hem bitiş taşıyor | `gold_value` = **bitiş** tarihi. `note`'a: `baslangic=2026-01-01` |
| 2 | `vade_ay` / `taksit_sayisi` aralık (`1–36`) | `gold_value` = **en büyük** (`36`). `note`'a: `aralik=1-36` (kılavuz §4) |
| 3 | Vade tutara bağlı (`100 gr'a kadar 1 ay, üstü 3–12 ay`) | `gold_value` = en uzun (`12`). `note`'a kademeleri yaz + `#kosullu_aralik` |
| 4 | Finansman tutarı aralık (`5.000 – 150.000 TL`) | `gold_value` = **üst sınır** (ürünün ilan ettiği tavan). `note`'a: `alt=5000` |
| 5 | Birden çok masraf kalemi | `gold_value` = **toplam** `{"has_fee": true, "amount": 20000}`. `note`'a kalemleri tek tek yaz |
| 6 | Oransal tahsis ücreti (`binde 5`) | **`unclear`** + `note`: `binde 5, tutara bagli`. Para şeması oran tutamıyor — gerçek şema açığı, karar bekliyor |
| 7 | Kâr payı **paylaşım** oranı (`%85 / %15`) | `kar_payi_orani` = **`absent`** + `note`: `#terminoloji paylasim orani`. Kılavuz §4: finansman oranı DEĞİLDİR |
| 8 | 8 sınıfa sığmayan tür | Katılma/altın/yatırım hesabı → `Yatırım Ürünü` · Leasing (icara) → `Finansman`. `note`'a gerçek ürün adını yaz |

### Bir belgede birden çok ürün varsa

Aynı metinde iki farklı ihtiyaç finansmanı varsa hangi değeri yazacağınız
belirsizdir → **`unclear`** + `note`'a kaç ürün olduğu. `fix` yazıp bir ürünün
değerini seçmek, ölçümü sessizce bozar. Bu satırlar hakemliğe düşer ve metrik
dışında tutulur (kılavuz §3.4).

---

## 4. Kart dışı kalan doğru davranışlar (A dosyasında doğru yapılmışlar)

- `kar_payi_orani = 0` **geçerlidir**. "Vade farksız" oranın SIFIR olduğunun
  pozitif ifadesidir, bilgi eksikliği değil (kılavuz §9.2 mantığı).
- Model hiçbir şey üretmemiş + metinde de yok → **her iki hücre boş**. En sık
  satır tipi bu ve doğru dolduruldu.
- Metin "tahsis ücreti alınmaz" diyor, model bulamamış →
  `fix` + `{"value": 0, "currency": "TRY"}`. Sıfır bir bilgidir.
- Çerez bandı / KVKK metni / kanun maddesinden üretilmiş değer → **`absent`**.
  Bunlar onaylanmış halüsinasyondur ve gold setteki en değerli etikettir
  (kılavuz §3.3).
