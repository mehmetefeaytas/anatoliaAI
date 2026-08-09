# Ana Tur Talimatı — 2 dakikada okuyun, sonra başlayın

> Kalibrasyon bitti. **Kalibrasyon dosyanıza geri dönmüyorsunuz** —
> `round0_kalibrasyon_*` ekibi hizalamak içindi ve o işi yaptı: dört kural
> çıktı. Gerçek gold verisi **round1**'dir ve henüz etiketlenmedi.

## 1. Hangi dosyayı açacaksınız

| Siz | Dosya | Satır | Belge | Kılavuz hızıyla* |
|---|---|---:|---:|---:|
| **A** | `round1_A.csv` | 650 | 50 | ~62 dk |
| **B** | `round1_B.csv` | 650 | 50 | ~62 dk |
| **C** | `round1_main_C.csv` | 573 | 90 | ~55 dk |
| **D** | `round1_main_D.csv` | 572 | 90 | ~55 dk |

\* Kılavuz §8'in kendi oranı (260 satır ≈ 25 dk). Ölçüm değil, türetme —
ilk 50 satır daha yavaş gider, sonra hızlanır.

**Kendi hata kalıplarınız:** `_calisma-listesi-<harfiniz>.md`. Bir sayfa,
kalibrasyonda ÖLÇÜLMÜŞ. Başlamadan önce bir kez okuyun.

> ### A ve B: birbirinizle konuşmayın
> `round1_A` ve `round1_B` **birebir aynı 50 belgeyi** taşır. Manşet κ
> buradan çıkacak ve κ yalnız **bağımsız** iki yargıyı ölçebilir. Tek bir
> satırı bile birlikte kararlaştırırsanız o satır κ'yı şişirir ve sayı
> ölçtüğünü iddia ettiği şeyi ölçmez. Takıldığınızda birbirinize değil,
> kılavuza sorun (§5 "Kime soracaksınız").

---

## 2. Boş bırakmak artık ONAY DEĞİL

Round1 dosyaları **v2 protokolündedir** (`protokol` sütunu bunu söyler).

| `verdict` hücresi | Anlamı | Gold'a ne girer |
|---|---|---|
| `ok` | "Kontrol ettim, model doğru" | modelin değeri (ya da "alan yok") |
| `fix` | "Yanlış, doğrusu şu" | sizin yazdığınız değer |
| `absent` | "Model uydurdu, metinde yok" | halüsinasyon (FP) — **en değerli etiket** |
| `unclear` | "Karar veremedim" | metrik dışı, hakemliğe düşer |
| **(boş)** | **"Bakmadım"** | **hiçbir şey — satır gold'a girmez** |

Eski protokolde boş hücre "model doğru" sayılıyordu ve gold'u modelin kendi
çıktısına çapalıyordu. Ölçüldü: aynı sistem çapalı gold'da mikro-F1 **0,677**,
kör protokolde **0,536**. Aradaki 0,141'in bir kısmı model başarısı değil,
protokol artefaktıydı.

**Zamanınız biterse sondan kesin, baştan değil.** Kesilen satırlar
`skipped_undecided` raporlanır: kapsama düşer, doğruluk şişmez. Bu doğru
ödünleşimdir. Ama `lint` boş `verdict`i **HATA** sayar — bitirdiğinizde
kalan boşluk varsa söyleyin, sessizce bırakmayın.

---

## 3. Beş sık hata — kalibrasyonda ÖLÇÜLDÜ

Uydurma değil: dördünüzün hakemlik öncesi dosyalarından sayıldı
(`round0_kalibrasyon_*.csv.yedek-hakemlik`).

### ① Model boş bırakmışken `absent` yazmak — **159 hücre** (A 18 · B 4 · C 3 · D 134)

`absent`, modelin **ÜRETTİĞİ** bir değeri reddetmek içindir. Model hiçbir şey
üretmediyse reddedilecek bir şey yoktur.

| `model_value` | Metinde de yok | Doğrusu |
|---|---|---|
| **boş** | evet | **`ok`** ← "kontrol ettim, bu alan belgede yok" |
| **dolu** | evet | **`absent`** ← halüsinasyon iddiası |

Tek başına bedeli: bu etiketler düzeltilince Fleiss κ **0,051 → 0,268**,
Krippendorff α **kılı kıpırdamadı** (0,575). Yani kimse fikrini değiştirmedi —
aynı şeye iki farklı etiket koyuluyordu. Kılavuz §3.3 kutusu.

### ② `gold_value`'ya belgenin ne hakkında olduğunu yazmak — **69 hücre** (D)

`gold_value` alanın **DEĞERİ** içindir, belgenin özeti değil.
`absent` + `"Leasing Süreci ve Hesaplama Aracı"` yazılmış. `build_gold` bu
açıklamayı **sessizce atar** — emek çöpe gider. Değer yoksa hücre **boş**
kalır, karar sütunu `absent` olur.

### ③ Kanonik değer yerine metinden alıntı — **68 hücre** (A 1 · B 17 · C 5 · D 45)

| Yazılan | Olması gereken |
|---|---|
| `en fazla 48 aya kadar` | `48` |
| `1-12 ay arası` | `12` (üst sınır), aralık `note`'a |
| `10.000₺ ile 50.000₺ arası` | `{"value": 50000, "currency": "TRY"}` |
| `%40'a %60` | kâr **paylaşım** oranı → `absent` + `#terminoloji` |

Ayrıştırıcı bunları reddeder; satır gold'a hiç girmez. Biçimler: `_bicim-karti.md`.

### ④ Tek değerli alana iki değer — **37 hücre** (B 21 · C 7 · D 9) · SESSİZ

En tehlikelisi bu: ayrıştırıcı **hata vermez**, ilk ucu alıp devam eder.

`kampanya_suresi` = `2026-01-01 - 2026-12-31` → gold'a **`2026-01-01`** girer.
Yani **başlangıç** tarihi bitiş alanına yazılır ve kimse görmez.

**Doğrusu:** üst sınırı/bitişi yazın, diğerini `note`'a düşün.

### ⑤ `hedef_kitle`ye serbest metin — **32 hücre** (B 18 · C 2 · D 12)

Bu alan **yalnız dört etiket** alır:
`yeni_musteri` · `mevcut_musteri` · `maas_musterisi` · `belirli_segment`

**"Bireysel müşteriler" bir segment DEĞİLDİR** — herkes demektir, hiçbir ayrım
yapmaz → **`absent`**. Cümleyi saklamak isterseniz `kampanya_kosullari`na yazın.

| Metin | `hedef_kitle` |
|---|---|
| "Bireysel müşterilerimize" | `absent` |
| "Yalnız Paraf kartlar" | `absent` (ürün kısıtı → koşullara) |
| "Emekli müşterilerimize" | `belirli_segment` |
| "Maaşını bankamızdan alanlara" | `maas_musterisi` |

---

## 4. Excel / Numbers ile çalışabilirsiniz

**Evet, `.xlsx` gönderebilirsiniz. Biçim bozulmaz.**

CSV'yi Excel/Numbers ile açın, doldurun, `.xlsx` olarak kaydedip gönderin.
`scripts/xlsx_to_review_csv.py` **yalnız** `gold_value` · `verdict` · `note`
sütunlarını taşır; üreteç sütunlarına (`doc_id`, `field`, `model_value`,
`model_conf`, `snippet` …) hiç dokunmaz. Eşleme satır sırasına değil
`(doc_id, field)` anahtarına dayanır — Excel'de **sıralama/filtre yapmış
olsanız bile** kararınız doğru satıra düşer.

```bash
.venv/bin/python -m scripts.xlsx_to_review_csv \
    --xlsx data/gold/review/round1_B.xlsx \
    --csv  data/gold/review/round1_B.csv
```

Üzerine yazmadan önce `.yedek-xlsx-oncesi` kopyası alınır — silme yok.

**Yapmayın:** Excel'in kendi "CSV olarak kaydet"i. Ayırıcıyı `;` yerine `,`
yapar, kodlamayı bozar, `model_conf` `0.70`'i `0.7`'ye çevirir ve satır
sırasını kalıcı kaydırabilir. Sonuncusu κ'yı sessizce hizasızlaştırır.

> **Panik yapmayın:** TR yerelli Excel `1.89`'u `1,89`, `2026-12-31`'i
> `31.12.2026` yapabilir. Sistem her ikisini de doğru okur; elle geri
> düzeltmeyin.

---

## 5. Takıldığınızda

**Sırayla deneyin:**

1. **Belgenin tam metnini açın** — `belgeler/<doc_id>.txt`. `snippet`teki
   köşeli parantez değerin metinde nerede geçtiğini gösterir; oraya bakın,
   modelin ne yazdığına değil.
2. **Kılavuza bakın** — `../ANNOTATION_GUIDE.md`. Alan kuralları §4,
   sekiz kapatılmış boşluk §4.13, biçimler §5, sık hatalar §9.
3. **Biçim kartı** — `_bicim-karti.md`.
4. **Hâlâ emin değilseniz `unclear` yazın.** Tahmin etmeyin: yanlış bir kesin
   cevap, dürüst bir `unclear`dan çok daha pahalıdır.

**Kılavuz vakayı cevaplamıyorsa bu sizin hatanız değil, kılavuzun kusurudur —
söyleyin.** Kalibrasyonda dördünüz de aynı sekiz yerde bağımsız olarak
tökezlemişti; o sekiz boşluk kural yazılarak kapandı (§4.13). Aynısı burada da
olacak. Sessizce kendi kuralınızı icat etmeyin: dört kişi dört kural icat
ederse çıkan düşük κ anotatör uyumsuzluğunu değil kılavuz belirsizliğini
ölçer.

> `unclear` oranınız **%5'i geçiyorsa** kılavuzda eksik var demektir.
> `lint` bunu zaten uyarı olarak basar.

---

## 6. Bitirince — kendi kapınızı koşun

```bash
# 1) biçim denetimi (ilk 20 satırdan sonra da bir kez koşun)
.venv/bin/python -m scripts.lint_review_csv data/gold/review/<dosyanız>.csv

# 2) A ve B bitirince — manşet κ
.venv/bin/python -m scripts.report_iaa \
    data/gold/review/round1_A.csv data/gold/review/round1_B.csv
```

`lint` **HATA** verdiği sürece dosya hazır değildir: o satırlar
`build_gold`'u durdurur ya da gold'a yanlış değer sokar. **UYARI**'lar
bilgilendirmedir, durdurmaz.

Eşik politikası (kılavuz §7) anotasyon başlamadan ilan edildi ve sonuca
bakılarak değiştirilmez: **κ ≥ 0,80** kabul · **0,67 ≤ κ < 0,80** notla kabul ·
**κ < 0,67** zorunlu hakemlik.
