# Gold Set Anotasyon Kılavuzu — Anatolia AI

> **Anotasyona başlamadan önce bu kılavuz baştan sona okunur.** Kalibrasyon turu
> (§8) atlanmaz. Eşik politikası (§7) anotasyon başlamadan ilan edilmiştir ve
> sonuçlara bakılarak değiştirilmez.

İlgili: `CLAUDE.md` §6 (zor anlama vakaları), §10 (normalizasyon), §12 (faizsiz
finans terminolojisi), §16 (değerlendirme metodolojisi) · Şartname §5.5
(terminolojiye uyum), §5.6 (normalizasyon)

---

## 1. Ne yapıyoruz ve neden

Model, katılım bankası kampanya metinlerinden 12 finansal alan çıkarıyor. Siz
modelin çıktısını **doğrulayacaksınız** — sıfırdan yazmayacaksınız. Bu, belge
başına ~5 dakikayı ~1 dakikaya indirir.

Ürettiğimiz şey bir **gold set**: modelin ne kadar doğru olduğunu ölçen tek
referans. İki sayı buna dayanır:

- **Precision** — model bir değer ürettiğinde ne sıklıkla haklı?
- **Halüsinasyon oranı** — model metinde OLMAYAN bir bilgiyi ne sıklıkla uyduruyor?

İkincisi projenin merkezindeki iddiadır. Ve **yalnızca sizin `absent` kararınızla
ölçülebilir** (§3.3).

### Model çıktısına kapılmayın

Ön-anotasyon bir kolaylıktır, bir otorite değil. `snippet` sütununda değerin
metinde geçtiği yer köşeli parantezle işaretlidir — **oraya bakın**, model ne
yazmış diye değil. Modelin en çok hata yaptığı satırlar CSV'nin başına konmuştur;
başlarda yavaş gitmeniz normaldir.

---

## 2. CSV'yi açma ve doldurma

Dosyanız `data/gold/review/` altında; kim hangi dosyayı açacak: `_atama.md`.

- Kodlama UTF-8 (BOM'lu), ayırıcı `;` — Excel / LibreOffice / Google Sheets'te
  çift tıklayınca doğru açılır. Türkçe karakter bozulursa dosyayı **içe aktarma
  (import)** ile açıp kodlamayı `UTF-8` seçin.
- **Sadece 3 sütunu doldurursunuz:** `gold_value`, `verdict`, `note`.
  Diğerlerine dokunmayın; `doc_id` ve `field` bozulursa satır eşleşmez.
- Belgenin tam metni: `data/gold/review/belgeler/<doc_id>.txt`

### Satırlar neden bu sırada

| Sıra | Satır tipi | Ne yapmalı |
|---|---|---|
| 1 | `disagreement = EVET` | Kural ve LLM ayrışmış. **En dikkatli bakılacak yer.** |
| 2 | Düşük/orta güven (0,50–0,90) | Model tereddütlü; kontrol edin. |
| 3 | Çok düşük güven (< 0,50) | Muhtemelen yanlış ya da uydurma. |
| 4 | Yüksek güven (≥ 0,90) | Genelde doğru; hızlı tarayın, **toplu geçin**. |
| 5 | `model_value` boş | Modelin bulamadığı alanlar. Belgeyi okuyup teyit edin. |

Zamanınız biterse **sondan kesin**, baştan değil. Dosyanın başındaki 100 satır,
sonundaki 400 satırdan daha değerlidir.

---

## 3. `verdict` sütunu — EN KRİTİK BÖLÜM

Dört değer alır: `ok` · `fix` · `absent` · `unclear`

### 3.1 Boş bırakmak = `ok` = "model doğru"

**Boş hücre bir karardır, kararsızlık değil.** Boş bırakınca "modelin bu satırdaki
çıktısını onaylıyorum" demiş olursunuz. Bu bilinçli bir tasarımdır: yüksek güvenli
satırların çoğu doğrudur ve onlara tuş harcamamanız gerekir.

Boş bırakmanın anlamı satırın tipine göre değişir:

| Satır | Boş bırakırsanız | Gold'a ne girer |
|---|---|---|
| `model_value` **dolu** | "Bu değer doğru" | `fields` içine o değer |
| `model_value` **boş** | "Model haklı, bu alan belgede yok" | `absent_fields` içine alan adı |

### 3.2 `fix` — değer yanlış, doğrusu şu

`gold_value` sütununa doğru değeri yazın (biçimler §5'te). `verdict`'i yazmayı
unutup sadece `gold_value` doldurursanız sistem bunu yine `fix` sayar — ama
alışkanlık edinmeyin.

### 3.3 `absent` — "kontrol ettim, bu belgede YOK"

**Bu kılavuzun en önemli tek talimatı.**

`absent`, model bir değer ürettiğinde yazıldığında **onaylanmış bir halüsinasyondur**
ve gold setteki en değerli tek etikettir. Modelin uydurma oranı birebir bu
etiketlerden hesaplanır.

Karıştırılan üç durum:

| Durum | Ne yapılır | Sonuç |
|---|---|---|
| Model değer üretti, metinde gerçekten var | boş bırak (`ok`) | doğru çıkarım (TP) |
| Model değer üretti, **metinde yok** | **`absent`** | **halüsinasyon (FP) — ölçülür** |
| Model değer üretti, var ama yanlış yazılmış | `fix` + doğru değer | normalizasyon hatası |
| Model değer üretmedi, metinde de yok | boş bırak (`ok`) | doğru sessizlik |
| Model değer üretmedi, **ama metinde var** | `fix` + doğru değer | kaçırma (FN) |

> **Neden bu kadar önemli:** `absent_fields` olmadan, gold'da bulunmayan bir alan
> iki şey demek olabilir — "kontrol edildi, yok" ya da "kimse bakmadı". Bu ikisi
> ayrılamazsa precision **tanımsızdır** ve halüsinasyon oranı hesaplanamaz.
> Emin değilseniz `absent` yazmayın; `unclear` yazın.

### 3.4 `unclear` — karar veremedim

Metin gerçekten belirsizse kullanın. `unclear` alanlar **metrik hesabının
dışında** tutulur ve hakemliğe düşer. Bu bir kaçış kapısıdır ama ucuz değildir:
her `unclear` sonradan birinin zamanını yer. Satırların **%5'inden fazlası**
`unclear` oluyorsa kılavuzda eksik var demektir — söyleyin.

**Tahmin etmeyin.** Yanlış bir kesin cevap, dürüst bir `unclear`dan çok daha
pahalıdır.

---

## 4. 12 alan — ne sayılır, ne sayılmaz

### `kar_payi_orani` — kâr payı oranı
- **Sayılır:** "kâr payı oranı %1,89", "aylık %2,05 kâr payı", "özel oranlı
  finansman %1,79", aralık: "%1,99 – %2,49"
- **Sayılmaz:** vade farkı oranı, gecikme cezası oranı, indirim yüzdesi
  (o `indirim_orani`), alışveriş puanı yüzdesi (o `alisveris_puani`)
- **Sınır vakalar:**
  - "ilk 6 ay %0, sonrasında %1,89" → **yürürlükteki asıl oranı** yazın (`1.89`);
    "ilk 6 ay %0" ifadesini `kampanya_kosullari`na ekleyin. `#kosullu_aralik`
  - "avantajlı finansman" / "cazip kâr payı" → sayı yok → `absent`. `#eksik_bilgi`
  - Aylık mı yıllık mı belirsizse → metinde yazan sayıyı olduğu gibi alın,
    `note`'a "baz belirsiz" yazın.
  - Katılım fonu / katılma hesabı **getiri** oranı → finansman oranı DEĞİLDİR,
    bu alana yazmayın. `#terminoloji`

### `finansman_tutari` — finansman tutarı
- **Sayılır:** "500.000 TL'ye varan finansman", "50.000 TL – 250.000 TL arası"
- **Sayılmaz:** ödül/hediye tutarı (`odul_miktari`), taksit tutarı, masraf tutarı
- **Sınır vaka:** "1.500,00 TL" → `1500.0` (binlik `.`, ondalık `,`). `#format_varyant`

### `vade_ay` — vade (AY cinsinden tamsayı)
- **Sayılır:** "120 aya varan vade", "1 yıl" → `12`, "36 ay"
- **Sayılmaz:** kampanya süresi (`kampanya_suresi`), ödemesiz dönem
- **Sınır vakalar:**
  - "12–36 ay arası vade" → **en uzun** vadeyi yazın (`36`), aralığı `note`'a düşün.
  - "1,5 yıl" → `18`

### `taksit_sayisi` — taksit adedi
- **Sayılır:** "vade farksız 6 taksit", "9 taksit imkânı"
- **Sayılmaz:** vade ayı (ikisi aynı sayı olsa bile ayrı alandır)
- **Sınır vaka:** "3 taksit" bir KART kampanyasında geçiyorsa yine `taksit_sayisi`.

### `tahsis_ucreti` — tahsis / dosya ücreti
- **Sayılır:** "tahsis ücreti 500 TL", "dosya masrafı 1.250 TL"
- **Sayılmaz:** kart yıllık ücreti, EFT/havale ücreti
- **Sınır vaka:** "tahsis ücreti alınmaz" → `{"value": 0, "currency": "TRY"}`
  (sıfır, "yok" değil). Ayrıca `masraf_durumu` da doldurulur.

### `masraf_durumu` — masraf var mı / ne kadar
- **Sayılır:** "masrafsız" → `{"has_fee": false, "amount": 0}` ·
  "dosya masrafı 500 TL" → `{"has_fee": true, "amount": 500}`
- **NEGASYON KRİTİK:** "masrafsız", "ücret alınmaz", "masraf yoktur",
  "tahsil edilmez" **bilgi eksikliği DEĞİLDİR** — masrafın SIFIR olduğunun
  pozitif ifadesidir. `absent` yazmayın, `has_fee: false` yazın.
- **Sınır vaka:** metin "masrafsız" deyip sonra tahsis ücreti belirtiyorsa
  **çelişki** vardır: her iki bilgiyi de yazın, `note`'a durumu açıklayın,
  `#celiskili` etiketleyin.

### `odul_miktari` — ödül / hediye tutarı
- **Sayılır:** "5.000 TL'ye varan hoş geldin hediyesi", "1.000 TL nakit iade"
- **Sayılmaz:** finansman tutarı, indirim tutarı üst sınırı olarak geçen ifadeler
  belirsizse `note` düşün.

### `indirim_orani` — indirim yüzdesi
- **Sayılır:** "restoran harcamalarında %10 indirim"
- **Sayılmaz:** kâr payı oranı, puan/iade oranı (o `alisveris_puani`)

### `alisveris_puani` — ORAN mı ADET mi (ayrım zorunlu)
- **Oran:** "%5 puan iadesi" → `{"kind": "rate", "value": 5}`
- **Adet:** "1.000 chip-para", "60.000 Mil" → `{"kind": "points", "value": 1000}`
- Ayrım yapılmazsa "%5" ile "1.000 puan" aynı sütunda sıralanır ve karşılaştırma
  tablosu anlamsızlaşır.

### `kampanya_suresi` — geçerlilik bitiş tarihi (ISO-8601)
- **Sayılır:** "31.12.2026 tarihine kadar" → `2026-12-31` ·
  "1 – 31 Temmuz 2026" → **bitiş** tarihi `2026-07-31`
- **Sayılmaz:** vade süresi, kampanya duyuru tarihi
- **Sınır vaka:** yalnızca başlangıç varsa → `note`'a yazın, `unclear`.

### `kampanya_kosullari` — koşul cümleleri (liste)
- **Sayılır:** "İlk 6 ay %0 kâr payı uygulanır", "En az 3 ay maaş müşterisi olmak
  gerekir", "Kampanya yalnızca mobil başvurularda geçerlidir"
- **Sayılmaz:** sadece geçerlilik tarihi bildiren cümle (o `kampanya_suresi`),
  pazarlama sloganları ("Hayaliniz ertelenmesin!")
- **Biçim:** birden çok koşul → dikey çizgi ile ayırın:
  `İlk 6 ay %0 uygulanır | Yalnızca mobilden başvuru`

### `hedef_kitle` — segment etiketleri (yalnız 4 etiket)
`yeni_musteri` · `mevcut_musteri` · `maas_musterisi` · `belirli_segment`
- **Sayılır:** "Maaşını bankamızdan alan emekli müşterilerimize" →
  `maas_musterisi | belirli_segment`
- **NEGASYON:** "Yeni müşteri olmayanlar için geçerli değildir" ifadesi
  `yeni_musteri` etiketi ÜRETMEZ. Olumsuzlanan segmenti etiketlemeyin.
- Sinyal yoksa (herkese açık kampanya) → `absent`.

---

## 5. Değer biçimleri (Şartname §5.6 — normalizasyon denklikleri)

`gold_value` yazarken kanonik biçimi kullanın. Serbest Türkçe de kabul edilir,
sistem çevirir — ama tereddütte kanonik biçimi yazın.

| Alan tipi | Kanonik biçim | Kabul edilen serbest giriş |
|---|---|---|
| Oran | `1.89` ya da `{"min": 1.99, "max": 2.49}` | `%1,89` · `% 1.89` · `1,89%` |
| Para | `{"value": 500, "currency": "TRY"}` | `500 TL` · `500₺` · `500 Türk Lirası` |
| Vade / taksit | `120` (tamsayı) | `120 ay` · `1 yıl` (→ 12) · `1,5 yıl` (→ 18) |
| Tarih | `2026-12-31` | `31.12.2026` · `31/12/2026` · `31 Aralık 2026` |
| Masraf | `{"has_fee": false, "amount": 0}` | `masrafsız` · `ücret alınmaz` |
| Puan | `{"kind": "rate", "value": 5}` | `oran=5` · `puan=1000` |
| Liste | `["a", "b"]` | `a \| b` (dikey çizgi ile) |

### Eşanlamlılar (aynı alana yazılır)
- kâr payı ≈ getiri oranı ≈ kâr marjı
- finansman ≈ kredi (konut/taşıt/ihtiyaç finansmanı)
- vade ≈ ödeme süresi ≈ geri ödeme süresi
- masrafsız ≈ ücretsiz ≈ dosya masrafı yok ≈ masraf alınmaz

### Türkçe sayı biçimi
Binlik ayıracı `.`, ondalık ayıracı `,` → `1.500,00` = **bin beş yüz**.
`1.500` bin beş yüzdür, bir buçuk değil.

> ⚠️ **Excel uyarısı:** TR yerelli Excel `1.89` hücresini kaydederken `1,89`
> yapabilir; tarih hücrelerini de `31.12.2026`ya çevirebilir. Sistem her ikisini
> de doğru okur — panik yapmayın, elle geri düzeltmeyin.

---

## 6. Zor-vaka etiketleri — `note` sütununa hashtag

Bir satır aşağıdaki kategorilerden birine giriyorsa `note` sütununa hashtag'i
yazın. Ayrı sütun yok; not zaten yazıyorsunuz.

| Etiket | Ne zaman | Örnek |
|---|---|---|
| `#terminoloji` | Katılım bankacılığı terimi yanlış yorumlanabilir | "katılım fonu getirisi" finansman oranı sanılmış |
| `#format_varyant` | TR sayı/tarih/para biçim tuzağı | `1.500,00` · `31 Aralık 2026` |
| `#eksik_bilgi` | Niteleyici var, sayı yok | "avantajlı finansman", "cazip oran" |
| `#celiskili` | Metin kendi içinde çelişiyor | "masrafsız" + tahsis ücreti binde 5 |
| `#kosullu_aralik` | Aralık ya da zaman/koşul bağımlı değer | "%1,99–%2,49" · "ilk 6 ay %0" |
| `#tr_ortografi` | Türkçe imla/karakter tuzağı | ALL-CAPS `ÜCRETSİZ` · şapkalı `kâr` |

Bu etiketler ablasyon tablosunda **hibrit mimarinin tam olarak nerede kazandığını**
gösterir — jüriye sunulacak en ikna edici artefakt (CLAUDE.md §6).

Birden çok etiket yazılabilir: `#celiskili #terminoloji`

---

## 7. Uyum eşiği — ÖNCEDEN İLAN EDİLMİŞTİR

Kalibrasyon turundan ve çift anotasyon alt kümesinden kappa hesaplanır
(`python3 -m scripts.report_iaa <A.csv> <B.csv>`).

| Kappa | Karar | Yapılacak |
|---|---|---|
| **κ ≥ 0,80** | kabul | Gold güvenilir. Ana geçişe devam. |
| **0,67 ≤ κ < 0,80** | notla kabul | Kabul edilir ama raporda AÇIKÇA not düşülür; uyuşmazlık listesi gözden geçirilir. |
| **κ < 0,67** | **hakemlik** | Zorunlu hakemlik + kılavuz revizyonu. Etkilenen alanlar yeniden anote edilir. |

Bu tablo anotasyon **başlamadan** sabitlenmiştir. Sonuçlara bakıp eşik
gevşetmek, kendi kendini onaylayan bir ölçümdür ve gold setin tüm değerini
yok eder.

İki ayrı sayı raporlanır:
- **Karar uyumu** (Cohen/Fleiss κ) — aynı kararı mı verdiler?
- **Değer uyumu** (Krippendorff α, `ratio`) — sayısal alanlarda değerler ne kadar
  yakın? `%1,89` vs `%1,90` tam uyuşmazlık sayılmaz.

---

## 8. Kalibrasyon turu (20 belge) — ATLANMAZ

**Ana geçişten önce**, dört anotatörün hepsi **aynı 20 belgeyi** anote eder.

1. Herkes `round0_kalibrasyon_<adınız>.csv` dosyasını doldurur (~20 dk).
2. Koşulur:
   ```bash
   python3 -m scripts.report_iaa data/gold/review/round0_kalibrasyon_*.csv
   ```
3. `data/gold/iaa_report.md` içindeki **uyuşmazlık listesi** birlikte okunur (~15 dk).
4. Her uyuşmazlık için sorulur: *kılavuz bu vakayı gerçekten cevaplıyor mu?*
   Cevaplamıyorsa **bu dosyaya kural eklenir** ve herkes yeni kuralı görür.
5. κ < 0,67 ise kalibrasyon **tekrarlanır** — ana geçişe geçilmez.

Bu 35 dakika, ana turda ortaya çıkacak yüzlerce sistematik uyuşmazlığı önler.
Atlanırsa 250 belgenin yeniden anote edilmesi gerekebilir.

---

## 9. Sık yapılan hatalar

1. **Modelin değerine güvenip metne bakmamak.** Snippet'teki köşeli parantez
   tam da bunun için var.
2. **"masrafsız"ı `absent` sanmak.** Masraf sıfırdır; bu bir bilgidir.
3. **Emin olmadan `absent` yazmak.** Halüsinasyon oranını bozar. Emin değilseniz
   `unclear`.
4. **Vade ile kampanya süresini karıştırmak.** "36 ay vade" ≠ "31.12.2026'ya kadar".
5. **Aralığı tek sayıya indirmek.** `%1,99–%2,49` bir aralıktır; ortalamasını
   almayın.
6. **`doc_id` / `field` sütunlarını düzenlemek.** Satır eşleşmez, veri kaybolur.
7. **Negatif segment etiketlemek.** "yeni müşteri olmayanlar" → `yeni_musteri` DEĞİL.

---

## 10. İş akışı — komut sırası

```bash
# 1) Ön-anotasyon (offline; LLM_BACKEND boşsa kural-only)
python3 -m scripts.preannotate --limit 250 --seed 42

# 2) İnceleme CSV'leri + atama planı
python3 -m scripts.to_review_csv --calibration 20 --duplicate-subset 50 --seed 42

# --- kalibrasyon turu -> uyum ölçümü -> kılavuz revizyonu -> ana tur ---

# 3) Uyum raporu
python3 -m scripts.report_iaa data/gold/review/round1_A.csv \
                              data/gold/review/round1_B.csv

# 4) Gold derleme (+ sha256 + build_report.md)
python3 -m scripts.build_gold --csv-dir data/gold/review \
                              --out data/gold/gold.v1.json

# 5) Değerlendirme
python3 -m eval.run_eval --gold data/gold/gold.v1.json
```
