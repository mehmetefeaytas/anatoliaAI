# TCMB Terimler Sözlüğü × Katılım Terim Sözlüğü — Çapraz Analiz

> **Ölçüm tarihi:** 2026-08-07
> **Ölçüm aracı:** `scripts/tcmb_capraz_analiz.py` (yeniden üretilebilir)
> **Veri:** `data/terminology/tcmb-terimler.json` (314 terim, TCMB) ×
> `data/terminology/katilim-terim-sozlugu.json` (101 terim, mentör Cavide Hanım,
> avukat teyitli)
> **Ham kanıt:** `data/terminology/_tcmb_ham/terimler-sozlugu.html` (+ `.meta.json`)

Bu rapordaki her sayı yukarıdaki betikle yeniden üretilebilir. Yorum satırları
sayının hangi geçişten geldiğini belirtir.

---

## 0. Toplama künyesi

| | |
|---|---|
| Kaynak | TCMB Terimler Sözlüğü |
| URL | `https://www.tcmb.gov.tr/wps/wcm/connect/tr/tcmb+tr/main+menu/banka+hakkinda/egitim-akademik/terimler+sozlugu/` |
| robots.txt | `User-agent: *` / `Disallow: */search+results` → **bu yol izinli** |
| HTTP | 200, 239 180 bayt, tek sayfa (sayfalama yok) |
| Çekilen | **314 terim** (312'sinde İngilizce karşılık), 22 harf grubu |
| Eksik | **Yok.** Ham HTML'de 336 `block-collapse-title` düğümü var; 22'si harf başlığı, 314'ü terim. J/Q/W/X harf grubu sayfada hiç yok (Türkçede bu harflerle başlayan terim bulunmuyor). |
| JS bağımlılığı | Yok — içerik sunucu tarafında üretiliyor, tümü ham HTML'de. |

Alternatif URL (`.../Terimler+Sozlugu/Sozluk`) byte-özdeş aynı içeriği döndürüyor;
mükerrer olduğu için kaydedilmedi.

---

## 1. Ölçüm yöntemi — neden naif arama yanıltıcı

İlk denemede "katılım terimi TCMB'de geçiyor mu" diye düz arama yapıldı ve
**18 eşleşme** çıktı. Bu sayı yanlıştır, iki nedenle:

1. **Çatışmayı kapsama sanmak.** `Riba` girdisinin `varyantlar` listesinde
   birebir `"faiz"` yazılıdır (kasıtlı — bkz. `src/domain/terminology.py`
   `_GURULTU` yorumu). Naif arama bunu TCMB'nin "Faiz Oranı" başlığıyla
   eşleştirip *"riba TCMB'de VAR"* der. Oysa bu kapsama değil, tam tersi:
   TCMB faizi meşru bir politika aracı olarak tanımlar, sözlüğümüz yasak olarak.
2. **İngilizce sahte-dost.** `en` alanı üzerinden eşleştirince `Vekâlet`in
   "Agency" karşılığı TCMB'nin "Central Registry **Agency**" (MKK) başlığına,
   `Tediye`nin "Payment" karşılığı yedi ayrı ödeme sistemi başlığına düşüyor.

Bu yüzden üç ayrı geçiş yapıldı: **KAPSAMA** (Türkçe kanonik + varyantlar,
`degildir` içindekiler çıkarılmış), **ÇATIŞMA** (`degildir` listesi TCMB'de
başlık mı), **SAHTE-DOST** (yalnız İngilizce üzerinden eşleşenler, ayrı sayılır).
`halk_dili` her üç geçişte de dışarıda — "ödeme", "kazanç", "faiz" gibi genel
ifadeler her katılım terimini TCMB'de "var" gösterirdi.

---

## 2. Kapsama — TCMB katılım terminolojisini içeriyor mu?

**Türkçe başlıkta karşılık bulan: 7 / 101.** Bu yedisi tek tek elden geçirildi:

| Katılım terimi | TCMB eşleşmesi | Değerlendirme |
|---|---|---|
| Finansal kiralama | Finansal Kiralama (Leasing) | **Gerçek kesişim** |
| Sukuk | Sukuk | **Gerçek kesişim** |
| Kira sertifikası | Kira Sertifikası (Lease Certificate) | **Gerçek kesişim** |
| İpotek | Tutsat (İpotek) Kredileri (Mortgage) | **Kısmî** — bizimki rehin *hakkı*, TCMB'ninki mortgage *kredisi*; farklı kavram |
| Riba | Basit/Bileşik/Reel Faiz Oranı … | **Çatışma**, kapsama değil (varyant "faiz" üzerinden) |
| Arındırma | Mevsim ve Takvim Etkisinden Arındırma | **Sahte-dost** (seasonal adjustment) |
| Mahsup | Takas (Swap) | **Sahte-dost** (varyant "takas" üzerinden) |

→ **Gerçek kavramsal kesişim: 3 tam + 1 kısmî = 4 / 101.**
→ **TCMB'de karşılığı olmayan: 94 / 101 (%93,1).**
→ Ayrıca 11 katılım terimi yalnız İngilizce üzerinden sahte eşleşme üretiyor
(Akit/Contract, İcare/Lease, Vekâlet/Agency, Özel cari hesap/Current account,
Temerrüt/Default, Müeccel/Deferred, Tediye/Payment, Nema/Yield, Zimmet/Liability,
Tenzil/Discount, IFSB). Bunlar otomatik eşleştirmede tuzaktır.

### 2.1 Çekirdek fıkhî terimler — tezin doğrudan testi

18 çekirdek katılım terimi TCMB başlıklarında arandı:

```
murabaha YOK   mudaraba YOK   muşaraka YOK   icare YOK      SUKUK  VAR
karz-ı hasen YOK   tekafül YOK   katılma hesabı YOK   kâr payı YOK
selem YOK   istisna YOK   vekâlet YOK   riba YOK   garar YOK
meysir YOK   özel cari hesap YOK   vade farkı YOK   tahsis ücreti YOK
```

**17 / 18 (%94) TCMB'de YOK.** Tek istisna Sukuk.

Daha sert iki ölçüm — bunlar yalnız başlıkta değil, **314 kaydın tanım
metinlerinde de** arandı:

- **"kâr payı"** — bu projenin en merkezî terimi — TCMB'nin 314 başlığının
  *hiçbirinde* ve 314 tanım metninin *hiçbirinde* geçmiyor. **Sıfır.**
- **"katılma hesabı"** ve **"özel cari hesap"** — aynı şekilde **sıfır**.

### 2.2 Tezin dürüst sınırı — "hiç yok" DEĞİL, "%1,6"

Görev tanımındaki *"konvansiyonel otorite katılım terminolojisini kapsamıyor"*
tezi **oransal olarak doğru, mutlak olarak yanlıştır.** TCMB'de İslami finansa
değen tam **5 kayıt** var (314'ün **%1,6**'sı):

1. **Sukuk**
2. **Kira Sertifikası**
3. **İslami Finansal Hizmetler Kurulu** (IFSB)
4. **Uluslararası İslami Likidite Yönetimi Kuruluşu** (IILM) — "faizsiz esasa dayalı"
5. **Parasal Sektör** — yalnızca geçerken anıyor ("… katılım bankaları ile …")

> **Uyarı (jüri riski):** Sunumda "TCMB katılım terminolojisini hiç içermiyor"
> demek savunulamaz; TCMB'de Sukuk maddesi vardır ve iyi yazılmıştır. Savunulabilir
> ifade: *"TCMB sözlüğünün %1,6'sı katılım finansına değiyor; çekirdek 18 fıkhî
> terimin 17'si ve projenin merkezî terimi olan 'kâr payı' hiç geçmiyor."*

### 2.3 Beklenmedik bulgu — TCMB'nin Sukuk tanımı bizi DOĞRULUYOR

TCMB, Sukuk maddesinde şunu yazıyor:

> "… Geleneksel tahviller faiz taşıyan menkul kıymetlerden oluşurken, sukuk temel
> olarak varlık sepetinde mülkiyet hakkından oluşan menkul kıymettir. **Tahvil
> borca dayalı sertifika, sukuk ise varlığa dayalı sertifika** olarak
> nitelendirilebilir."

Sözlüğümüzün `Sukuk` girdisindeki `ayrim_notu` ile aynı ayrımdır ("Tahvil bir BORÇ
senedidir ve faiz üretir; sukuk bir VARLIĞA dayanır"). Bu bir çelişki değil,
**konvansiyonel otoritenin ağzından gelen bir doğrulamadır** — ve tam da bu yüzden
alıntılanabilir değeri yüksektir (bkz. §5, Rol B).

---

## 3. Çelişki analizi — TCMB'nin "DEĞİLDİR" dediğimizi tanımlaması

Sözlüğümüzdeki `degildir` alanı, bir terimin ne *olmadığını* makine-okunur
biçimde tutar. Bu listedeki her yasak karşılık (`faiz` / `kredi` / `mevduat`
kökleri — `scripts/jargon_lint.py::YASAK_KOKLER` ile aynı üçlü) TCMB'de
başlık olarak aranmıştır.

**Sonuç: 24 doğrudan çatışma çifti, 19 ayrı katılım terimi.**

| Katılım terimi | "DEĞİLDİR" dediği | TCMB'de otoriter tanımı var |
|---|---|---|
| Murabaha | kredi / nakit kredi / tüketici kredisi | Kredi Riski, Nihai Kredi Mercii … |
| Muşaraka, Mudaraba, Karz-ı hasen, Kâr/zarar ortaklığı yatırımı | kredi | Kredi Arzı Daralması, Kredi Riski, Nihai Kredi Mercii |
| Azalan muşaraka | konut kredisi | Tutsat (İpotek) Kredileri |
| Teverruk, Mal karşılığı vesaikin finansmanı | nakit kredi | (7 kredi başlığı) |
| Kurumsal/Bireysel finansman desteği | ticari / ihtiyaç / nakit kredi | (7 kredi başlığı) |
| **Kâr payı** | **faiz** | **Faiz Oranı, Basit Faiz Oranı, Reel Faiz Oranı …** |
| Katılım oranı, Birim hesap değeri | faiz oranı | Faiz Oranı, Piyasa Faiz Oranı … |
| Katılma hesabı | faizli hesap | (11 faiz başlığı) |
| Vade farkı | faiz / gecikme faizi | (11 faiz başlığı) |
| Gecikme cezası | gecikme faizi | (11 faiz başlığı) |
| Erken ödeme indirimi | faiz iadesi | (11 faiz başlığı) |
| Nema | faiz | (11 faiz başlığı) |
| İcare muntehiye bi't-temlîk | faizli leasing | Finansal Kiralama + faiz başlıkları |

### 3.1 Yasak köklerin TCMB'deki yoğunluğu

| Kök | TCMB **başlık** sayısı | TCMB **tanım metni** sayısı |
|---|---|---|
| `faiz` | **11** | **43** |
| `kredi` | **7** | **26** |
| `mevduat` | 0 | **12** |

11 faiz başlığı: Basit Faiz Oranı, Bileşik Faiz Oranı, Bir Hafta Vadeli Repo Faiz
Oranı, Birikmiş Faiz, Değişken Faizli İhraçlar, Dönemsel Faiz, Faiz Oranı, Merkezi
Yönetim Faiz Dışı Bütçe Dengesi, Piyasa Faiz Oranı, Reel Faiz Oranı, TCMB'nin
Ağırlıklı Ortalama Faiz Oranı.

7 kredi başlığı: Banka Kredileri Eğilim Anketi, İhracat Reeskont Kredisi, Kredi
Arzı Daralması, Kredi Riski, Likidite Desteği Kredisi, Nihai Kredi Mercii,
Tutsat (İpotek) Kredileri.

**Çelişkinin niteliği.** Bunlar "iki kaynak aynı terimi farklı tanımlıyor" türü
çelişkiler değildir — daha keskin bir şey: TCMB, sözlüğümüzün *yasak* dediği
kavramları **normatif ve nötr** biçimde tanımlar. Örnek, TCMB "Tutsat (İpotek)
Kredileri":

> "… geri kalan tutar ise finans kuruluşu tarafından **ödünç verilerek**
> karşılanmaktadır. … Borcun geri ödemesi önceden belirlenmiş ödeme serisine
> uyarak **sabit** [faizle] …"

Bir konut finansmanı metnini bu tanım üzerinden yorumlayan model, murabaha temelli
bir ürünü "ödünç para + faiz" olarak anlatır. Bu, `src/chatbot/safety.py`'nin
kapatmaya çalıştığı uyum ihlalinin ta kendisidir.

---

## 4. TCMB'de olup bizde olmayanlar — hangileri işimize yarar?

Ham fark: **308 TCMB terimi** katılım sözlüğünde yok. Ama "yok" ≠ "gerekli".
Gerçek ölçüt, terimin **kampanya metinlerinde geçip geçmediğidir.** Bu yüzden
her iki sözlük repodaki gerçek korpusa karşı çalıştırıldı:

| | Katılım korpusu (389 belge, 3,2 M karakter) | Klasik banka korpusu (618 belge, 8,5 M karakter) |
|---|---|---|
| **Katılım sözlüğü** (101) | **56 terim (%55,4)** | 24 terim (%23,8) |
| **TCMB sözlüğü** (314) | 44 terim (**%14,0**) | 41 terim (%13,1) |

Katılım sözlüğü, hedef korpusta TCMB'nin **dört katı** isabet üretiyor — üstelik
üçte bir büyüklüğünde. TCMB'nin 314 teriminin %86'sı kampanya metinlerinde hiç
geçmiyor (makro politika sözlüğü: enflasyon hedeflemesi, kur rejimleri, PPK,
zorunlu karşılık…).

**Net kazanç: 39 terim** — TCMB'de var, katılım sözlüğünde yok, katılım
korpusunda geçiyor:

> Akreditif · Alış · Avans · Baz Puan · Bono · Döviz Kuru · Efektif ·
> Elektronik Para · Elektronik Para Kuruluşu · Enflasyon · Faktoring ·
> Finansal Farkındalık · Finansal Okuryazarlık · IBAN · Konsolidasyon ·
> Kredi Riski · Likidite · Mutabakat · Para Piyasası · Reeskont ·
> Saklama Hizmeti · Satış · Sermaye Piyasası · Tahvil · Takasbank · Tasarruf ·
> Türev İşlemler · Valör · Yatırım Fonları · Yeniden Yapılandırma ·
> Zamanaşımı Süresi · Ödeme Kuruluşu · Ödeme Sistemi · İhale · İhracat ·
> İskonto · İtfa · İthalat · İşgücü

**Bu 39 terimin ortak özelliği belirleyicidir: hepsi mezhep-nötr altyapı
terimleridir.** IBAN, valör, akreditif, mutabakat — katılım/konvansiyonel
ayrımı taşımazlar, dolayısıyla `degildir` veya `ayrim_notu` üretmezler. Yani
sözlüğü **genişletmezler, tamamlarlar**. Değerleri gerçektir ama sınırlıdır:
chatbot "valör nedir" diye sorulduğunda cevap verebilsin diye.

Ayrıca **9 terim karşıt-örnek adayı**: klasik banka korpusunda geçen, katılım
korpusunda hiç geçmeyen TCMB terimleri — Basit Faiz Oranı, Devalüasyon, Emisyon,
Eurobond, **Faiz Oranı**, Hazine Bonosu, Moratoryum, **Repo**, Türev Ürünler.
Bunlar "bu kelime metinde geçiyorsa metin muhtemelen katılım bankasına ait
değildir" sinyalidir.

---

## 5. NET SONUÇ — TCMB sözlüğünün projedeki rolü

Görev tanımındaki öneri şuydu: *"terim enjeksiyonu için değil; `degildir`/ayrım
kartlarını zenginleştirmek ve `jargon_lint.py` için karşıt örnek havuzu olarak."*

**Ölçüm bu öneriyi büyük ölçüde doğruluyor, bir noktada düzeltiyor.**

### Rol A — Karşıt örnek havuzu (`scripts/jargon_lint.py`) · **en yüksek değer**

`jargon_lint.py` bugün yasak kökleri (`faiz`/`kredi`/`mevduat`) yakalıyor ama
"yakalanan şey nasıl bir dildir" örneği yok. TCMB **11 faiz + 7 kredi başlığı,
43 + 26 tanım metni** ile bunu otoriter biçimde sağlıyor: bunlar uydurma değil,
merkez bankasının kendi yazdığı, kusursuz Türkçe konvansiyonel finans metinleridir.
Buna §4'teki **9 ayırt edici terim** eklenir (klasik korpusta var, katılım
korpusunda yok). Bu havuz hem lint'in regresyon testleri, hem de sınıflandırıcı
için negatif örnek üretimi anlamına gelir. **Yeni veri toplamadan elde edilen
en ucuz kazanç budur.**

### Rol B — `degildir` / `ayrim_notu` kartlarının otoriteyle güçlendirilmesi

19 katılım terimimiz "X DEĞİLDİR" diyor ama X'in ne olduğunu kendi ağzımızla
anlatıyor. TCMB, bu 19 terimin karşı-kavramı için **alıntılanabilir resmî tanım**
veriyor. `ayrim_notu` bundan sonra şu biçimi alabilir:

> Kâr payı, faiz değildir. TCMB "Faiz Oranı"nı *[TCMB tanımı]* olarak tanımlar;
> kâr payı ise gerçekleşmiş ticari faaliyetin sonucuna bağlıdır ve zarar ihtimali
> taşır.

Jüri karşısında bu, kendi iddiamızı düzenleyici otoritenin metniyle
karşılaştırdığımız anlamına gelir. §2.3'teki Sukuk vakası bunun en güçlü
örneğidir: TCMB'nin kendi tanımı bizim ayrımımızı **doğruluyor**.

### Rol C — SINIRLI enjeksiyon · öneriden sapma

Görev tanımı enjeksiyonu tümden reddediyordu. Ölçüm bunu kısmen çürütür:
**39 terim** TCMB'de var, bizde yok ve katılım korpusunda **gerçekten geçiyor**.
Bunları dışarıda bırakmak, chatbot'un "valör", "IBAN", "akreditif", "itfa"
sorularına cevapsız kalması demektir.

Ama şartla: **ayrı bir dosyada, ayrı bir katmanda.** `tcmb-terimler.json`
`katilim-terim-sozlugu.json` ile **birleştirilmemelidir**, üç gerekçeyle:

1. TCMB kayıtlarında `degildir` / `ayrim_notu` / `risk_notu` alanı yoktur.
   `src/domain/terminology.py::_kart_onceligi` bu alanlara göre sıralar; alansız
   314 kayıt eklemek gerçek ayrım kartlarını bağlam bütçesinden dışarı iter.
2. `scripts/jargon_lint.py::oneri_tablosu()` karşılıkları `degildir` alanından
   türetir. TCMB kayıtları hiçbir karşılık üretmez, yalnızca aramayı yavaşlatır.
3. Bağlam bütçesi: katılım sözlüğü zaten ~76 000 karakter ve `OLLAMA_NUM_CTX`
   8192 token. TCMB'nin 314 kaydı bütçeyi üçe katlar.

**Uygulanabilir biçim:** yalnız o 39 terimi `otorite_tipi: "notr"` etiketiyle
ayrı bir yardımcı sözlük olarak tut; kart seçiminde katılım sözlüğünden **sonra**,
yalnız artan bütçe varsa devreye gir.

### Tek cümlelik sonuç

> TCMB sözlüğü bu projede bir **terim kaynağı değil, bir karşıt-otorite
> referansıdır**: hedef korpusta katılım sözlüğünün dörtte biri kadar isabet
> üretir (%14'e karşı %55) ve çekirdek 18 fıkhî terimin 17'sini içermez — ama
> tam da bu yüzden, sözlüğümüzün "faiz/kredi/mevduat DEĞİLDİR" iddialarının
> karşı tarafını düzenleyici otoritenin kendi ağzından belgeler; birincil rolü
> `jargon_lint` karşıt örnek havuzu ve `ayrim_notu` alıntı kaynağıdır, sınırlı
> ikincil rolü ise korpusta geçen 39 mezhep-nötr terimin ayrı katmanda
> tamamlanmasıdır.

---

## 6. Açık uçlar

- Bu 39 terimin `otorite_tipi: "notr"` yardımcı sözlüğe alınması henüz
  **yapılmadı** — ayrı bir karar ve ayrı bir commit gerektirir.
- `ayrim_notu` alanlarına TCMB alıntısı eklenmesi henüz **yapılmadı**; sözlük
  mentör (Cavide Hanım) teyitli olduğu için alan düzenlemesi öncesinde mentör
  onayı alınmalıdır.
- TCMB terimlerinin kalıcı ID'si veya sürüm etiketi yok; sayfa güncellenirse
  fark tespiti yalnızca `.meta.json` içindeki SHA-256 ile yapılabilir.
- İkinci bir konvansiyonel otorite (BDDK terimler sözlüğü / TBB) ile aynı ölçüm
  tekrarlanırsa §5'teki sonucun genellenebilirliği test edilmiş olur.

## Kaynaklar

- TCMB Terimler Sözlüğü — `data/terminology/_tcmb_ham/terimler-sozlugu.html`
  (çekilme 2026-08-07, HTTP 200, SHA-256 `ae1e0069…7daaed`)
- Katılım Terim Sözlüğü — `data/terminology/katilim-terim-sozlugu.json`
  (mentör Cavide Hanım, 2026-08-06, avukat teyitli)
- `src/domain/terminology.py` — kart üretimi, `degildir` / `ayrim_notu` semantiği
- `scripts/jargon_lint.py` — yasak kökler ve `oneri_tablosu()`
- `CLAUDE.md` §12 (Domain Bilgisi — Faizsiz Finans), §14 (Scraping Kuralları)
