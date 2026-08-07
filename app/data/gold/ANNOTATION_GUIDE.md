# Gold Set Anotasyon Kılavuzu — Anatolia AI

> **Sürüm: v2 protokolü.** İki şey v1'e göre değişti: (1) **boş hücre artık onay
> değil** — onay `ok` yazılarak verilir (§3.1); (2) dört anotatörün bağımsız
> olarak işaretlediği **sekiz boşluk kapatıldı** (§4.13). Hangi setin hangi
> protokolle etiketlendiği §11'de kayıtlıdır; v1 metinleri silinmedi, arşiv
> kutularında duruyor.

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
- v2 paketlerinde salt-okunur bir **`protokol`** sütunu vardır (değeri `v2`).
  Doldurmayın, silmeyin — araçlar hangi kuralla okuyacağını buradan anlar.
- **Her satıra bir `verdict` yazılır** (v2). Boş kalan satır "karar verilmedi"
  sayılır ve gold'a girmez (§3.1).
- Belgenin tam metni: `data/gold/review/belgeler/<doc_id>.txt`

### Satırlar neden bu sırada

| Sıra | Satır tipi | Ne yapmalı |
|---|---|---|
| 1 | `disagreement = EVET` | Kural ve LLM ayrışmış. **En dikkatli bakılacak yer.** |
| 2 | Düşük/orta güven (0,50–0,90) | Model tereddütlü; kontrol edin. |
| 3 | Çok düşük güven (< 0,50) | Muhtemelen yanlış ya da uydurma. |
| 4 | Yüksek güven (≥ 0,90) | Genelde doğru; hızlı tarayın, **toplu `ok` yazın** (kopyala-yapıştır). |
| 5 | `model_value` boş | Modelin bulamadığı alanlar. Belgeyi okuyup teyit edin. |

Zamanınız biterse **sondan kesin**, baştan değil. Dosyanın başındaki 100 satır,
sonundaki 400 satırdan daha değerlidir.

---

## 3. `verdict` sütunu — EN KRİTİK BÖLÜM

Dört değer alır: `ok` · `fix` · `absent` · `unclear`

### 3.1 Boş bırakmak = KARAR VERİLMEDİ (v2 protokolü)

**Boş hücre bir karar değildir.** Boş bırakılan satır gold'a HİÇ girmez; ne
`fields`'a ne `absent_fields`'a. `eval/run_eval.py` onu `skipped_undecided`
sayar ve metriğin dışında tutar (`eval/run_eval.py:287`).

**Onay açık işaretle verilir: `verdict` hücresine `ok` yazın.**

| Satır | `ok` yazarsanız | Gold'a ne girer |
|---|---|---|
| `model_value` **dolu** | "Bu değer doğru" | `fields` içine o değer |
| `model_value` **boş** | "Kontrol ettim, bu alan belgede yok" | `absent_fields` içine alan adı |
| (boş bırakılır) | "Bakmadım / karar veremedim" | **hiçbir şey — metrik dışı** |

Dört karar da tek harflik bir tuş kadar ucuzdur; tek fark, artık **sessizlik
onay sayılmıyor**.

#### Neden değişti — ölçülmüş gerekçe

Eski kural ("boş = `ok` = model doğru") gold'u **modelin kendi çıktısına
çapaladı**. Anotatörün bakmadığı her satır, modelin değerini gold'a yazıyordu;
model o satırda kendi cevabıyla karşılaştırılıyor ve otomatik olarak haklı
çıkıyordu.

Etkisi ölçülmüştür: aynı sistem gold.v1 üzerinde **mikro-F1 0,677**, kör
protokolle ölçüldüğünde **0,536**. Aradaki farkın bir kısmı model başarısı
değil, **protokol artefaktıdır**. Jüriye tek bir sayı sunulamamasının sebebi
budur (bkz. §11).

Boş bırakmak artık bedava değil ama **dürüst**: ölçülmeyen şey ölçülmüş gibi
görünmüyor.

> **Zamanınız biterse** yine sondan kesin. Kesilen satırlar `skipped_undecided`
> olarak raporlanır — kapsama düşer, doğruluk şişmez. Bu doğru ödünleşimdir.

<details>
<summary><b>ARŞİV — v1 protokolü (artık geçerli değil, silinmedi)</b></summary>

> v1 metni: *"Boş hücre bir karardır, kararsızlık değil. Boş bırakınca 'modelin
> bu satırdaki çıktısını onaylıyorum' demiş olursunuz. Bu bilinçli bir
> tasarımdır: yüksek güvenli satırların çoğu doğrudur ve onlara tuş harcamamanız
> gerekir."*
>
> | Satır | Boş bırakırsanız (v1) | Gold'a ne girerdi (v1) |
> |---|---|---|
> | `model_value` **dolu** | "Bu değer doğru" | `fields` içine o değer |
> | `model_value` **boş** | "Model haklı, bu alan belgede yok" | `absent_fields` içine alan adı |
>
> Bu kural `gold.v1.json` ve `gold.v2.json` üretilirken yürürlükteydi. O iki set
> **v1 protokolüyle** etiketlenmiştir ve v2 setleriyle aynı tabloda tek sayı
> hâlinde birleştirilemez (§11).

</details>

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
| Model değer üretti, metinde gerçekten var | **`ok`** yaz | doğru çıkarım (TP) |
| Model değer üretti, **metinde yok** | **`absent`** | **halüsinasyon (FP) — ölçülür** |
| Model değer üretti, var ama yanlış yazılmış | `fix` + doğru değer | normalizasyon hatası |
| Model değer üretmedi, metinde de yok | **`ok`** yaz | doğru sessizlik (TN) |
| Model değer üretmedi, **ama metinde var** | `fix` + doğru değer | kaçırma (FN) |
| Bakmadım / karar veremedim | boş bırak | **metrik dışı** (`skipped_undecided`) |

> `absent`in tanımı v2'de bir adım keskinleşti: *"bu belgenin ANLATTIĞI
> kampanyaya ait böyle bir değer yok"*. Değer dosyada geçse bile yan menüden ya
> da "İlginizi çekebilir" bloğundan geliyorsa bu kampanyaya ait değildir —
> §4.13/8'e bakın.

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
- **Ürün/kart/kanal kısıtı segment DEĞİLDİR** — §4.13/2.

---

## 4.13 Sekiz boşluk — kapatılmış kurallar (v2)

> Dört anotatör (M1–M4) gold.v2'de **ayrık** belge kümelerine baktı ve
> **bağımsız olarak aynı sekiz belirsizliği** işaretledi. Aynı yerde bağımsız
> tökezleme anotatör gürültüsü değil, **kılavuz kusurudur**
> (`docs/rapor/gold-genisletme.md:168-190`). Aşağıdaki sekiz kural o kusuru
> kapatır ve κ ölçümünden **önce** yürürlüğe girer.
>
> Kural yoksa dört anotatör dört ayrı kural icat eder; sonra çıkan düşük κ
> anotatör uyumsuzluğunu değil kılavuz belirsizliğini ölçer.

### 1) Kampanya olmayan belge — 8 sınıfın hiçbiri uymuyorsa `absent`

Korpusta zekât hesaplama aracı, KVKK/aydınlatma metni, kurumsal tanıtım sayfası
ve **kampanya LİSTESİ** sayfaları var. gold.v2'nin **9 belgesi (%19)** böyle.

**Kural:** Belge tek bir kampanyayı anlatmıyorsa `campaign_type` → **`absent`**.
`null` meşrudur ve bir hatanın değil, bir kararın adıdır. 12 alan da varsayılan
olarak `absent`tir; ancak metinde o kampanyaya ait gerçek bir değer geçiyorsa
doldurulur. `note`'a **`#kampanya_disi`** yazın.

*Gerekçe:* 8 sınıf kapalı bir kümedir; uymayan belgeye en yakın sınıfı vermek
macro-F1'i dürüst bir `null`dan daha çok bozar ve modelin "her metne bir sınıf
uydurma" davranışını ödüllendirir.

**Kampanya listesi sayfası ayrımı:** sayfa birden çok kampanyanın başlığını
sıralıyor ve hiçbirinin koşulunu vermiyorsa listedir → `absent`. Tek kampanyayı
anlatıp altında "diğer kampanyalar" bloğu taşıyorsa liste değildir → normal
anote edilir, blok yok sayılır (§4.13/8).

### 2) Ürün kısıtı mı, müşteri segmenti mi — tek soruluk test

`hedef_kitle` **yalnız 4 etiket** taşır (§4): `yeni_musteri` ·
`mevcut_musteri` · `maas_musterisi` · `belirli_segment`. Bu kümede ürün diye
bir şey yoktur.

**Kural — KİM/NE testi:** Cümle müşterinin **KİM olduğunu** mu söylüyor (yaş,
meslek, statü, bankayla ilişkisi), yoksa **NE kullandığını** mı (kart, ürün,
kanal, uygulama)?

| Metin | Nereye | Neden |
|---|---|---|
| "Yalnız Paraf kartlar" | `kampanya_kosullari` | ürün kısıtı — KİM değil, NE |
| "Sadece mobil başvurularda" | `kampanya_kosullari` | kanal kısıtı |
| "Ticari kredi kartı sahiplerine" | `kampanya_kosullari` | ürün kısıtı |
| "Emekli müşterilerimize" | `hedef_kitle: belirli_segment` | kişi niteliği |
| "Maaşını bankamızdan alanlara" | `hedef_kitle: maas_musterisi` | bankayla ilişki |
| "İlk kez müşteri olanlara" | `hedef_kitle: yeni_musteri` | bankayla ilişki |

Bir cümle her ikisini birden taşıyorsa **iki alana da yazılır**: segment kısmı
`hedef_kitle`ye, ürün kısmı `kampanya_kosullari`na
("Paraf kartlı emekli müşterilerimize" → `belirli_segment` + koşul cümlesi).

*Gerekçe:* `belirli_segment` hem "emekli" hem "Paraf kart sahibi" için
kullanılırsa etiket iki ayrı şey demeye başlar ve eşleşme rastlantısallaşır.
gold.v2'de `hedef_kitle` F1'i **0,727 → 0,267** düştü; payın çoğu buradan
geliyor.

### 3) Tutar cinsinden indirim ("100 TL indirim") → `odul_miktari`

`indirim_orani` **yalnız yüzde** alır (`{"value": 10}` tipi bir oran).
"100 TL indirim" bir oran değildir.

**Kural:** Tutar cinsinden indirim **`odul_miktari`**na yazılır
(`{"value": 100, "currency": "TRY"}`), `note`'a **`#tutar_indirimi`** eklenir.
`indirim_orani` o satırda `absent`tir (metinde yüzde geçmiyorsa).

*Gerekçe:* Üçüncü bir alan açmak 12 alanlık şemayı ve ona bağlı her artefaktı
(DB şeması, dashboard, karşılaştırma motoru, önceki gold setleri) değiştirir.
`odul_miktari` zaten para-tipli müşteri kazancı alanıdır; tutar indirimi tam
olarak odur. §4'teki "indirim tutarı … belirsizse note düşün" ifadesi bu kuralla
kesinleştirilmiştir.

Aynı cümlede hem yüzde hem tavan varsa ("%20, en fazla 100 TL") ikisi de yazılır:
`indirim_orani` = `20`, `odul_miktari` = `{"value": 100, "currency": "TRY"}`,
`note`'a "tavan" düşülür.

### 4) Çok değerli `alisveris_puani` — sektöre göre farklı oranlar

"Marketlerde %5, akaryakıtta %3, restoranlarda %10 puan" gibi.

**Kural:** Alana **en yüksek** değer yazılır (`{"kind": "rate", "value": 10}`),
**sektör–oran çiftlerinin tamamı** `kampanya_kosullari`na dikey çizgiyle
dizilir, `note`'a **`#kosullu_aralik`** yazılır. `kind` karışıksa (bir sektörde
oran, bir sektörde puan) oranı yazın ve puan kısmını koşullara düşün.

*Gerekçe:* Şema tek değerlidir; "en büyüğü al" kuralı `vade_ay` aralıklarında
zaten yürürlükte (§4) — aynı deterministik kuralı ikinci kez icat etmiyoruz.
Ortalama almak metinde bulunmayan bir sayı üretir.

### 5) Oransal tahsis ücreti ("binde 5")

`tahsis_ucreti` para tiplidir (`{"value": …, "currency": "TRY"}`); "binde 5" bir
oran, ücret **tutarı değildir**.

**Kural:**
- `tahsis_ucreti` → **`unclear`**, `note`'a metindeki ifade birebir yazılır
  (`"binde 5"`) + **`#oransal_ucret`**.
- `masraf_durumu` → **`{"has_fee": true, "amount": null}`** (masraf VARDIR,
  tutarı metinde TL olarak yoktur — şema `amount: null`a izin verir).
- Oran cümlesi ayrıca `kampanya_kosullari`na eklenir.

**Hesaplamayın.** Finansman tutarı aynı belgede geçse bile çarpıp TL yazmak
çıkarım değil **türetmedir**; anotatör metinde yazmayan bir sayıyı gold'a
sokamaz.

*Gerekçe:* `absent` yazmak yanlış olurdu — belgede ücret bilgisi VAR; `absent`
yazılsaydı doğru davranan bir model halüsinasyonla suçlanırdı. `has_fee: true`
+ `amount: null` masrafın varlığını kaydeder, tutarı uydurmaz.

### 6) `N/M` biçiminde kâr paylaşım oranı ("85/15") → `kar_payi_orani` DEĞİL

Katılma hesabında bankayla müşteri arasındaki **kâr paylaşım anahtarıdır**;
murabahadaki finansman kâr payı oranı ile ilgisi yoktur.

**Kural:** `kar_payi_orani` → **`absent`**; ifade `kampanya_kosullari`na
("Kâr paylaşım oranı 85/15") yazılır, `note`'a **`#terminoloji`**.

*Gerekçe:* Ölçülmüş bir bozulma: `"85 / 15"` yazılan hücreyi ayrıştırıcı
reddetmedi, `{"min": 15, "max": 85}` üretti ve %15–85 aralıklı bir kâr payı
oranı gold'a girdi (`scripts/lint_review_csv.py` modül başlığı, kalibrasyon A'da
9 sessiz bozulmanın biri). Katılım bankacılığı terminolojisi %30'luk model
başarısı kaleminin kalbindedir (CLAUDE.md §12).

### 7) Gün cinsinden vade

`vade_ay` **ay cinsinden tamsayıdır**.

**Kural:** Gün sayısı 30'un tam katıysa `30 gün = 1 ay` ile çevirin
("90 gün" → `3`, "180 gün" → `6`). Tam katı değilse (`45 gün`, `100 gün`)
→ **`unclear`**, `note`'a gün sayısı birebir yazılır + **`#gun_vade`**.
Metin ayrıca ay cinsinden bir vade veriyorsa **ay olan kazanır**.

*Gerekçe:* 45 günü 1 ya da 2 aya yuvarlamak metinde olmayan bir kesinlik üretir
ve iki anotatör iki farklı yöne yuvarlar. Tam kat kuralı tersinirdir: gold'daki
`3` her zaman "90 gün"e geri okunur.

### 8) Yan menü / "İlginizi çekebilir" bloğu kirliliği

Temizlenmiş metinde sayfanın kendi kampanyasına ait olmayan bloklar kalabiliyor:
sol/sağ menü, "İlginizi çekebilir", "Diğer kampanyalar", "Size özel", altbilgi.
Bu bloklardaki sayılar **komşu kampanyalara** aittir.

**Kural:** Değer yalnızca bu bloklarda geçiyorsa → **`absent`** +
**`#kabuk_kirliligi`**. `absent` burada "dosyada bu karakter dizisi yok" değil,
**"bu belgenin anlattığı kampanyaya ait böyle bir değer yok"** demektir (§3.3).

Nasıl anlaşılır: `snippet`teki köşeli parantezin etrafına bakın. Değerin
çevresinde başka bir kampanyanın **başlığı/linki** varsa ya da aynı satırda
birbiriyle ilgisiz üç-dört kampanya adı sıralanıyorsa bloktasınız. Emin
değilseniz belgenin tam metnini açın:
`data/gold/review/belgeler/<doc_id>.txt`. Hâlâ emin değilseniz `unclear`.

*Gerekçe:* Blok değeri onaylanırsa komşu bankanın oranı bu bankaya yazılır ve
karşılaştırma motoru (CLAUDE.md §17 "adil kıyas") yanlış sıralama üretir.
Korpusta bu kirlilik ölçülmüş ve işaretlenmiştir (kabuk/boilerplate denetimi).

### Özet — sekiz kuralın hashtag'leri

`#kampanya_disi` · `#tutar_indirimi` · `#oransal_ucret` · `#gun_vade` ·
`#kabuk_kirliligi` (yeni) — mevcutlar: `#kosullu_aralik` (madde 4),
`#terminoloji` (madde 6). Madde 2'nin ayrı etiketi yoktur; kararı `hedef_kitle`
ile `kampanya_kosullari` arasındaki dağıtımda görünür.

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
| `#kampanya_disi` | Belge kampanya değil (§4.13/1) | zekât aracı · KVKK · kampanya listesi |
| `#tutar_indirimi` | Tutar cinsinden indirim (§4.13/3) | "100 TL indirim" |
| `#oransal_ucret` | Ücret oran olarak verilmiş (§4.13/5) | "binde 5 tahsis ücreti" |
| `#gun_vade` | Vade gün cinsinden, 30'un katı değil (§4.13/7) | "45 gün" |
| `#kabuk_kirliligi` | Değer yan menü / "İlginizi çekebilir" bloğundan (§4.13/8) | komşu kampanyanın oranı |

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

v2 paketi: `round0_kalibrasyon_v2_A.csv` … `round0_kalibrasyon_v2_D.csv`
(aynı 20 belge, aynı 260 satır, `protokol=v2`). Eski `round0_kalibrasyon_A..D.csv`
dosyaları v1 protokolüne aittir ve **karıştırılmaz** (§11).

1. Herkes `round0_kalibrasyon_v2_<adınız>.csv` dosyasını doldurur (~25 dk).
2. Önce biçim denetimi, sonra uyum:
   ```bash
   python3 -m scripts.lint_review_csv data/gold/review/round0_kalibrasyon_v2_*.csv
   python3 -m scripts.report_iaa      data/gold/review/round0_kalibrasyon_v2_*.csv
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
8. **Onayı boş bırakmak.** v2'de boş = "bakmadım". Doğruysa `ok` yazın (§3.1).
9. **Ürün kısıtını segment sanmak.** "Yalnız Paraf kartlar" → `kampanya_kosullari`,
   `hedef_kitle` DEĞİL (§4.13/2).
10. **Oransal ücreti TL'ye çevirmek.** "binde 5" × finansman tutarı = **türetme**;
    anotatör metinde yazmayan sayıyı gold'a sokamaz (§4.13/5).
11. **Yan menüdeki değeri onaylamak.** Komşu kampanyanın oranı bu belgeye
    yazılırsa karşılaştırma yanlış sıralar (§4.13/8).
12. **Kampanya olmayan belgeye "en yakın" sınıfı vermek.** `absent` meşrudur
    (§4.13/1).

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

---

## 11. Protokol künyesi — hangi set hangi kuralla etiketlendi

> **Silme yok.** Aşağıdaki setlerin hiçbiri geçersiz değildir; **karşılaştırılabilir
> değildir**. Bu tablo o yüzden kalıcıdır.

| Set / dosya | Protokol | Boş hücrenin anlamı | §4.13 sekiz kuralı | Kullanım |
|---|---|---|---|---|
| `data/gold/gold.v1.json` | **v1** | `ok` (onay) — model çıktısına çapalı | yok | tarihsel; tek başına raporlanır |
| `data/gold/gold.v2.json` | **v1** | `ok` (onay) — model çıktısına çapalı | yok | tarihsel; tek başına raporlanır |
| `round0_kalibrasyon_A.csv` (dolu) | **v1** | `ok` | yok | v1 κ referansı |
| `round0_kalibrasyon_B/C/D.csv` (boş) | **v1** | `ok` | yok | koşulmadı |
| `round1_*.csv`, `round2_zor_vaka.csv` | **v1** | `ok` | yok | doldurulmadıysa v2'ye taşınmalı |
| `round0_kalibrasyon_v2_A..D.csv` | **v2** | karar verilmedi (metrik dışı) | **var** | κ ölçümü buradan |

### Bunun metriğe etkisi — jüriye tek sayı sunulamaz

v1 protokolünde boş bırakılan her satır modelin kendi değerini gold'a yazdı.
Bu, ölçümü modelin çıktısına çapaladı:

| Ölçüm | Protokol | Mikro-F1 |
|---|---|---|
| gold.v1 üzerinde | v1 (çapalı) | **0,677** |
| aynı sistem, kör protokol | çapasız | **0,536** |

Fark (0,141) model başarısındaki bir değişimden değil, **protokolden** gelir.
İki sayıyı tek tabloda ortalamak ya da yalnız yükseğini sunmak ölçümü geçersiz
kılar. Raporda her sayı **protokol künyesiyle birlikte** verilir.

### Eski CSV'ler nasıl okunacak

- Araçlar protokolü **satırdaki `protokol` sütunundan** okur. Sütun yoksa dosya
  **v1** sayılır — eski dosyaların yorumu değişmez, geriye dönük veri kaybolmaz.
- `scripts/report_iaa.py` v1 dosyalarında boş hücreyi eskisi gibi `ok` sayar;
  v2 dosyalarında boş hücreyi **karar verilmemiş** sayıp κ hesabından çıkarır.
- İki protokolün dosyaları **aynı κ koşusunda birleştirilmez**. Karıştırılırsa
  `report_iaa` uyarır ve raporun başına künye basar.
- `scripts/lint_review_csv.py` v2 dosyalarında boş `verdict`i HATA sayar; v1
  dosyalarında (eskisi gibi) sessiz geçer.

### Açık kalan tek bağımlılık

`scripts/build_gold.py` hâlâ v1 sözleşmesini uygular (boş `verdict` → `ok`).
v2 CSV'leri **lint'ten geçmeden** derlenmemelidir: lint boş `verdict` bırakılmış
v2 dosyasını HATA ile durdurur, dolayısıyla `build_gold`a çapalanacak satır
ulaşmaz. `build_gold`a `--protokol v2` bayrağı eklemek bu bağımlılığı kaldırır
ve `docs/rapor/kilavuz-revizyonu.md`de açık iş olarak kayıtlıdır.
