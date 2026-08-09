# Onarım Reçetesi — 64 biçim hatası, anotatör başına

> **Bu belge CSV'ye dokunmaz.** Mekanik olarak düzeltilebilen satırlar için
> öneri üretildi ama ayrı bir dosyaya yazıldı: [`_oneriler.csv`](./_oneriler.csv).
> Anotatör tek bakışta onaylar ya da reddeder — karar insanındır.
>
> Ölçüldü: 2026-08-09 · `scripts/onarim_recetesi.py`
> Kaynak: `round0_kalibrasyon_{A,B,C,D}.csv` (protokol v1)

---

## Manşet

```
64 HATA · 59 ayrı satır · 10 kalıp
A: 0     B: 35     C: 12     D: 17
mekanik öneri üretildi: 39 satır
insan kararı gereken:   20 satır
```

64 hata 59 satıra düşüyor çünkü **5 satır aynı anda iki hata veriyor** (ör.
`3-6 taksit` hem "tek alana çoklu değer" hem "tamsayıya çevrilemedi" üretir).

**A'nın sıfır hatası tesadüf değil, kopyalanabilir bir davranıştır** — A biçim
kartına harfiyen uydu. Round1'de hedef, diğer üçünü A'nın çizgisine çekmektir;
aşağıdaki reçete bunun için yazıldı.

---

## 1. Anotatör × kalıp tablosu

| Kalıp | A | B | C | D | **Σ** | Mekanik? |
|---|---:|---:|---:|---:|---:|---|
| `tek-alana-coklu-deger` | 0 | 16 | 3 | 5 | **24** | ✅ evet |
| `fix-ama-deger-bos` | 0 | 6 | 1 | 0 | **7** | ❌ hayır |
| `absent-ama-deger-dolu` | 0 | 0 | 0 | 7 | **7** | ✅ evet |
| `hedef_kitle-serbest-metin` | 0 | 5 | 1 | 0 | **6** | ❌ hayır |
| `taksonomi-disi-tur` | 0 | 1 | 3 | 2 | **6** | ✅ kısmen (5/6) |
| `tamsayi-cevrilemedi` | 0 | 2 | 1 | 2 | **5** | ✅ evet (aralıkla örtüşür) |
| `sema-yanlis-anahtar` | 0 | 3 | 0 | 0 | **3** | ✅ evet |
| `masraf-kanonik-degil` | 0 | 0 | 2 | 1 | **3** | ✅ evet |
| `puan-oran-adet-belirsiz` | 0 | 1 | 1 | 0 | **2** | ✅ evet |
| `gecersiz-verdict` | 0 | 1 | 0 | 0 | **1** | ❌ hayır |

---

## 2. Anotatör A — 0 hata

Düzeltilecek bir şey yok. **Round1'de A'nın davranışı referanstır:**

- Aralık gördüğünde kartın kuralını uyguladı (en büyük/bitiş değeri), aralığı
  `gold_value`ya yazmadı.
- `absent` yazdığında `gold_value`yu boş bıraktı.
- 8 tür listesinin dışına çıkmadı.

---

## 3. Anotatör B — 35 hata (5 kalıp)

### B-1 · `tek-alana-coklu-deger` — 16 satır ⚠️ en büyük tek kalıp

Alanlar: `finansman_tutari` 5 · `vade_ay` 4 · `kampanya_suresi` 4 · `taksit_sayisi` 3

| mevcut | olması gereken | kural |
|---|---|---|
| `1-12 ay` | `12` | kart §3-2: en büyük |
| `2 ile 3 taksit arasında` | `3` | kart §3-2 |
| `12ile 48 arasında değişiyor` | `48` | kart §3-2 |
| `600.000 TL - 1.700.000 TL` | `{"value": 1700000, "currency": "TRY"}` | kart §3-4: üst sınır |
| `{"currency": "TRY", "value": 5000.0-150000.0}` | `{"value": 150000, "currency": "TRY"}` | kart §3-4 |
| `01 Ocak 2026 - 31 Aralık 2026` | `2026-12-31` | kart §3-1: bitiş |

**Neden tehlikeli:** ayrıştırıcı bunları REDDETMEZ, **ilk ucu alır**. `1-12 ay`
sessizce `1` olur — yani en kısa vade gold'a "ürünün vadesi" diye girer.
Durup kalan bir hatadan daha kötüdür, çünkü kimse fark etmez.

**Round1'de nasıl önlenir:** aralık gördüğün an iki hücre doldur — `gold_value`ya
tek değer (en büyük / bitiş / üst sınır), `note`'a aralığın kendisi
(`aralik=1-12`). Bilgi kaybolmaz, şema bozulmaz.

### B-2 · `fix-ama-deger-bos` — 6 satır ⛔ derlemeyi DURDURUR

`kampanya_kosullari` 2 · `hedef_kitle` 4. Hepsinde not var, değer yok:

> `verdict=Fix` · `gold_value=(boş)` · `note="Model genel bir segment etiketi
> kullanmıştır. Hedef kitle metindeki tanımlarıyla güncellenmeli"`

**Mekanik öneri ÜRETİLMEDİ** — doğru değeri yalnız anotatör bilir. B "model
yanlış" demiş ama doğrusunu yazmamış.

**Round1'de nasıl önlenir:** `fix` yazıyorsan değeri de yaz. Doğrusunu
bilmiyorsan `unclear` yaz — kaçış kapısı var ve kullanılması ayıp değil.

### B-3 · `hedef_kitle-serbest-metin` — 5 satır

`hedef_kitle` yalnız 4 etiket alır: `yeni_musteri`, `mevcut_musteri`,
`maas_musterisi`, `belirli_segment`. B belgeden cümle kopyalamış:

> `["Kuveyt Türk Business Plus kart sahibi müşteriler"]`
> `Hizmet ya da mal üretimi amacıyla faaliyette olan ... ticari oluşumlar`
> `["6306 sayılı kanun kapsamında riskli yapı ... hak sahipleri"]`

**Mekanik öneri ÜRETİLMEDİ.** Üçü de büyük olasılıkla `belirli_segment` ama
"hangi segment" bilgisi etiket kümesinde yok; eşleme insan kararıdır.

> **Yan bulgu — görünmez karakter.** Bu hücrelerin 4'ünde U+2060 (word joiner)
> artığı var; elektronik tablodan yapıştırma izi. Gözle görülmez, ayrıştırıcı
> takılır. Round1'de yapıştırmadan önce düz metne çevirin.

**Round1'de nasıl önlenir:** belgedeki tanımı `note`'a yaz, `gold_value`ya
4 etiketten uyanı koy.

### B-4 · `sema-yanlis-anahtar` — 3 satır

| alan | mevcut | sorun |
|---|---|---|
| `tahsis_ucreti` ×2 | `{"rate": 0.5}` | para alanı oran tutamaz |
| `kar_payi_orani` ×1 | `{"rate": 3.99}` | oran alanı düz sayı alır |

`kar_payi_orani` mekanik: `{"rate": 3.99}` → `3.99`.

`tahsis_ucreti` **gerçek bir şema açığıdır**, anotatör hatası değil: kart §3-6
oransal tahsis ücreti için `unclear` + `note` diyor, çünkü para şeması oranı
tutamıyor. Öneri "hücreyi boşalt + `verdict=unclear`".

### B-5 · `gecersiz-verdict` — 1 satır

`verdict` sütununa not yazılmış:

> `verdict = "Model bulunmayan bir şeyi arayıp bulamayarak doğru bir iş yapmış"`

Bu cümle **`ok` demek** ama karar sütununa yazılamaz. Metin `note`'a taşınmalı,
`verdict`e `ok` yazılmalı. Mekanik öneri üretilmedi (karar sütununa betik
yazmaz — bu tam olarak yasak olan şey).

---

## 4. Anotatör C — 12 hata (7 kalıp)

C'nin hataları dağınık; tek baskın kalıbı yok.

### C-1 · `taksonomi-disi-tur` — 3 satır
`Güneş Katılma Hesabı` · `Yatırım Hesabı` · `Leasing`

Kart §3-8 bunların hepsini çözüyor: katılma/altın/yatırım hesabı →
**`Yatırım Ürünü`**, leasing (icara) → **`Finansman`**. Gerçek ürün adı `note`'a.
Üçü de mekanik önerildi.

### C-2 · `tek-alana-coklu-deger` — 3 satır
`400.000 TL, 800.000 TL, 1.200.000 TL, 2.000.000 TL` → `{"value": 2000000, "currency": "TRY"}` (kart §3-4);
`3-6 taksit` → `6`; `1.07.2023-31.08.23` → `2023-08-31`.

### C-3 · `masraf-kanonik-degil` — 2 satır
`Ücretli` ve `masraflı` kanonik değil. Tutar belgede yoksa:
`{"has_fee": true, "amount": null}`. **`masrafsız` ise `{"has_fee": false, "amount": 0}`** —
negasyon "değer yok" demek değildir, masrafın SIFIR olduğunun pozitif ifadesidir.

### C-4 · kalan 4 satır
`tamsayi-cevrilemedi` 1 (C-2 ile aynı satır) · `puan-oran-adet-belirsiz` 1
(`1.500 TL ParafPara` → `{"kind": "points", "value": 1500}`) ·
`fix-ama-deger-bos` 1 (insan) · `hedef_kitle-serbest-metin` 1 (insan).

> **Yan bulgu — refleks `unclear`.** Kalıp analizinde C'nin 6 satırda `unclear`
> yazdığı, ama `note`'unun doğru cevabı zaten içerdiği görüldü. `unclear` metrik
> DIŞIdır: doğru cevabı bilip `unclear` yazmak, o satırı ölçümden düşürür.
> Bu bir lint hatası değil (linter yakalamaz) ama gold'u küçültür.

---

## 5. Anotatör D — 17 hata (5 kalıp)

### D-1 · `absent-ama-deger-dolu` — 7 satır ⚠️ D'nin imza kalıbı

`kampanya_kosullari` 6 · `campaign_type` 1. Hepsinde aynı davranış:
**`gold_value`ya belgenin KONUSU yazılmış, alanın DEĞERİ değil.**

| doc | `gold_value`ya yazılan |
|---|---|
| `kuveyt-turk--finansmanlar-ihtiyac-finansmanlari` | `finansman` |
| `tom-katilim--hesaplama-araclari` | `Finansman hesaplama aracı` |
| `turkiye-emlak-katilim--bireysel-hesaplar` | `katılma hesapları` |
| `turkiye-finans--konut-finansmani-konut-finansmani` | `konut kredisi` *(alıntı — D'nin yazdığı)* |
| `turkiye-finans--tasit-finansmani-tasit-finansmani-2` | `taşıt finansmanı` |
| `vakif-katilim--finansmanlar-konut-finansmani-2` | `Konut Finansmanı hakkında Sıkça Sorulan Sorular` |
| `kuveyt-turk--leasing-...` (`campaign_type`) | `Leasing Süreci ve Hesaplama Aracı` |

**D'nin KARARI doğru** — bu belgeler gerçekten kampanya değil, `absent` yerinde.
Yanlış olan tek şey, gerekçeyi `gold_value`ya yazması. `build_gold` `absent`
görünce o değeri zaten **sessizce atar** (kart §3 tuzak-2); yani bilgi hem
kayboluyor hem linter'ı kırıyor.

**Öneri: hücreyi boşalt, `absent` kararını KORU, açıklamayı `note`'a taşı.**
Yedisi de mekanik önerildi.

**Round1'de nasıl önlenir:** `absent` = "bu alanın değeri metinde yok". Yanına
değer yazılmaz. Neden `absent` dediğin `note`'a gider.

### D-2 · `tek-alana-coklu-deger` — 5 satır
`3-120` → `120` · `3_48` → `48` · `3-6 taksit` → `6` ·
`10000.0-50000.0` (`odul_miktari`) → `{"value": 50000, "currency": "TRY"}` ·
`1-31 Temmuz 2026` → `2026-07-31`.

### D-3 · `taksonomi-disi-tur` — 2 satır
`Güneş Yatırım Hesabı` · `Altın Katılma Hesabı` → ikisi de **`Yatırım Ürünü`** (kart §3-8).

### D-4 · `masraf-kanonik-degil` — 1 satır
`{"amount": 157.50}, "has_fee": true}` — parantez hatası. Onarımı
`{"has_fee": true, "amount": 157.5}`; **sayıya dokunulmadı**.

### D-5 · `tamsayi-cevrilemedi` — 2 satır
D-2 ile örtüşüyor (`3-120`, `3-6 taksit`).

---

## 6. Mekanik öneri üretilmeyen 20 satır — ve niçin

Dürüstlük kaydı: bu satırlar için betiğin verecek bir cevabı yok.

| Gerekçe | satır |
|---|---:|
| `fix` + boş `gold_value` — doğru değeri yalnız anotatör bilir | 7 |
| `hedef_kitle` serbest metin — 4 etikete eşleme insan kararı | 6 |
| `verdict` sütununa not yazılmış — karar sütununa betik yazmaz | 1 |
| Taksonomi dışı ama karta da uymayan tür (`Hediye kampanyası`) | 1 |
| Kartın kuralı uygulanamadı (aşağıdaki iki koruma) | 3 |

### İki koruma — bilerek üretilmeyen öneriler

Bunlar betiğin *yapabildiği* ama **yapmaması gereken** önerilerdi. Testlerle
kilitlendi (`tests/test_onarim_recetesi.py`).

1. **`%20-%70` → tutar önerilmez.** Koruma olmadan
   `{"value": 70, "currency": "TRY"}` öneriliyordu. Linter bunu **kabul
   ederdi** — yani anotatör "öneri var, biçim de doğru" diye onaylar ve %70'lik
   bir oran gold'a 70 TL olarak girerdi. *Linter'ı geçen yanlış öneri, hatanın
   kendisinden tehlikelidir.*

2. **`31 Aralık 2072` → bitiş tarihi önerilmez.** Kart §3-1 uygulanabilirdi ama
   aynı anotatörün başka bir hücresindeki not `2027` diyor. İki hücre
   çelişiyorsa doğrusunu belge bilir, betik değil.

---

## 7. `_oneriler.csv` nasıl okunur

39 satır · `;` ayraçlı · sütunlar:
`dosya · doc_id · field · mevcut · onerilen · gerekce · kanit`

- `onerilen` = `(hücreyi boşalt)` ise `gold_value` silinecek, `verdict` korunacak.
- `gerekce` her zaman biçim kartındaki maddeyi gösterir (`kart §3-2` gibi) —
  kart dışı kural üretilmedi.
- `kanit` anotatörün kendi `note`'udur; öneri onun gerekçesiyle tutarlı mı,
  tek bakışta görülür.

**Her öneri `parse_gold_value` süzgecinden geçirildi**: linter'ın reddedeceği
bir öneri anotatöre hiç gösterilmedi.

---

## 8. Round1'e taşınacak dört kural

2.400 satırda tekrarlanmaması için, önem sırasına göre (kapsadığı hata sayısı):

1. **Aralık gördüysen tek değer yaz, aralığı `note`'a düş.** *(24 hata)*
   Vade/taksit → en büyük · tutar → üst sınır · tarih → bitiş.
2. **`absent` değer taşımaz.** Gerekçe `note`'a gider. *(7 hata)*
3. **`fix` yazdıysan değeri de yaz; bilmiyorsan `unclear`.** *(7 hata)*
4. **8 tür ve 4 hedef kitle etiketi SABİTTİR.** Sığmıyorsa kart §3-8'e bak,
   uydurma. *(12 hata)*

---

## Üreten komutlar

```bash
# Hata envanteri (kaynak)
.venv/bin/python -m scripts.lint_review_csv \
    'data/gold/review/round0_kalibrasyon_[ABCD].csv'

# Kalıp gruplaması + _oneriler.csv
.venv/bin/python -m scripts.onarim_recetesi

# Yalnız sayım (dosya yazmaz)
.venv/bin/python -m scripts.onarim_recetesi --sadece-ozet

# Kuralların testleri
.venv/bin/python -m unittest tests.test_onarim_recetesi
```
