# Çapraz değerlendirme — iki motor, iki gold seti, tek metrik kodu

**Tarih:** 19 Ağustos 2026
**Kapsam:** kural katmanı (`config=kural`), 5 ortak alan
**Karşı taraf:** kamuya açık, Apache-2.0 lisanslı üçüncü taraf bir katılım
bankacılığı çıkarım korpusu ve onun regex çıkarım motoru. Korpus repoya
kopyalanmadı; ölçüm yerel bir kopya üzerinden, yol parametresiyle yapıldı.

---

## Neden bu rapor var

Kendi gold setimizde ölçtüğümüz mikro-F1 (0,477) ile karşı tarafın ilan ettiği
makro-F1 (%98,28) arasında büyük bir uçurum var. İki sayı yan yana konduğunda
akla gelen ilk açıklama "onların motoru daha iyi" oluyor. Bu raporun amacı o
uçurumun **neyden kaynaklandığını ölçmek** — tahmin etmek değil.

Yöntem basit ve simetrik: iki çıkarım motorunu birbirinin gold setine soktuk.
İki yönde de **karşı tarafın kendi metrik tanımını ve toleransını** kullandık
(TP/FP/FN sayımı, 0,01 tolerans), böylece hiçbir yerde kendi lehimize ölçüt
yazmadık. Tek metrik kodu iki motora da uygulandığı için sonuç elmalar-elmalar.

Ortak alan kümesi, iki tarafın ölçtüğü alanların kesişimi:
`kar_payi_orani`, `vade_ay`, `odul_miktari`, `finansman_tutari`,
`taksit_sayisi`.

## Sonuç

| Zemin | Anatolia AI | Karşı motor |
|---|---|---|
| Kendi `gold.v2` (48 kayıt, 40'ı zor) | **0,708 / 0,769** | 0,370 / 0,325 |
| Harici korpus — geliştirme yarısı (26 kayıt) | 0,576 | **0,961** |
| Harici korpus — held-out (10 kayıt) | 1,000 | 1,000 |

*(mikro / makro F1. Held-out sütununda yalnız mikro verildi — gerekçe aşağıda.)*

**Bulgu simetriktir: her motor kendi gold setinde kazanıyor, karşı zeminde
düşüyor.** Yani "biz sadece daha zor bir sette ölçüyoruz" savunması yarım
doğru. Asıl mesele her iki takımın da kendi topladığı metin dağılımına
ayarlanmış olması. Bu bizim için rahatlatıcı bir sonuç değil — ama eyleme
dönüştürülebilir bir sonuç: eksik olan motor kalitesi değil, kapsanmayan
ifade kalıplarıydı.

## Kendi aleyhimize olan yarı

Bu raporun ölçüm değeri, yalnız lehimize olan yarıyı yayımlarsak sıfırdır.
Dolayısıyla:

- **Karşı motor kendi zemininde bizden çok daha iyi** (0,961 vs 0,576).
  Bu sayı gerçek ve onların mühendisliğinin hakkı.
- **Asimetri bizim lehimize çalışıyor:** biz onların korpusunu hata analizi
  için açtık, onlar bizim korpusumuzu görmedi. Aşağıdaki düzeltmeler o
  analizden çıktı. Karşı motorun bizim setimizdeki 0,370'i ise hiç
  optimize edilmemiş bir sayı.
- **Held-out yarısı istatistiksel güç taşımıyor.** Hata analizinde hangi
  kayıtları açtığımızı kimlik düzeyinde kaydettik; 36 canlı kayıttan 26'sı
  görüldü, 10'u hiç açılmadı. O 10 kayıtta yalnız **4 ölçülebilir
  alan-örnek** var ve iki motor da 4/4 doğru yaptı. "Held-out'ta berabere"
  cümlesi teknik olarak doğru ama üzerine hiçbir iddia kurulamaz. Dürüst
  ifade: held-out çok küçük.
- Karşı taraf %98,28'lik manşetini kendi raporunda daraltıyor (yalnız regex
  katmanı, yalnız 7 ölçülebilir alan, 58 kayıtlık set, tek etiketleyici,
  IAA yok). Bu daraltmayı onlar yazdığı için burada da yazıyoruz.

## Farkın anatomisi — üç ayrı kategori

Kaçırmaları tek tek metne kadar takip ettiğimizde tek bir sebep çıkmadı, üç
farklı sebep çıktı. Ayrım önemli, çünkü üçü farklı iş demek.

### 1. Gerçek kapsam açığı — düzeltildi

Motorumuz iki ifade kalıbını hiç görmüyordu:

- **Vade kademesi eşiği** birinci aday oluyordu: "Finansman tutarının
  125.000 TL'ye kadar olması durumunda maksimum vade 36 aydır." Buradaki
  tutar bir eşik; aynı cümle 250.000 üstü finansmanın da mümkün olduğunu
  söylüyor. Tetikleyici tam da aradığımız çapa olduğu için aday birinci
  sıraya geçiyor ve belgedeki gerçek sınır hiç değerlendirilmiyordu.
- **Çapası sonra gelen sınır** hiç aday olamıyordu: "400.000 TL'ye Kadar
  İhtiyaç Finansmanı", "1.000 TL-1.000.000 TL arasında … İhtiyaç Finansmanı".
  Desen tetikleyici→tutar sırası bekliyordu.

Bu kalıp **korpus bağımsızdı**: aynı hata kendi gold setimizde de vardı
(`turkiye-finans--kampanyalar-turkiye-finans-avantajlariyla-`, gold
400.000 TL, çıkarım 125.000 TL). Düzeltme iki zeminde birden kazandırdı —
kapsam açığının gerçek olduğunun kanıtı bu.

### 2. Ontoloji farkı — bilinçli olarak düzeltilmedi

Kaçırmaların önemli bir bölümü çıkarım hatası değil, iki setin aynı olguyu
farklı alanlara yazması:

| Metin | Karşı gold | Bizim ontoloji |
|---|---|---|
| "1.000 TL – 100.000 TL arası **sağlık harcaması**" | `finansman_tutari` | harcama limiti — finansman değil |
| "50.000 TL'ye kadar **vade farksız 5 taksit**" | `finansman_tutari` | taksitli harcama limiti |
| "5.000 **Worldpuan**" | `odul_miktari` + `odul_birimi` | `alisveris_puani` (puan/adet) |
| "**vade farksız**" | `kar_payi_orani = 0` | `masraf_durumu.has_fee = False` |

Bu satırlarda motorumuz doğru değeri **buluyor**, sadece başka alana yazıyor
ya da bilinçli olarak yazmıyor. Örnek: bir kayıtta karşı gold
`odul_miktari = 5000/Worldpuan` derken bizim motor `alisveris_puani = 5000`
üretiyor — aynı sayı, farklı alan.

"Vade farksız → kâr payı = 0" kuralını **eklemedik** ve gerekçesi ölçüldü:
kendi gold setimizde bu ifadeyi içeren 5 kayıt var ve hiçbirinde
`kar_payi_orani` dolu değil (dördü açıkça `absent`). Kuralı eklemek dört
yanlış pozitif üretip F1'i düşürürdü. Bilgi kaybolmuyor; `masraf_durumu`
alanında duruyor.

Harcama limitini finansman tutarı saymak da tartışmalı bir etiketleme
kararıdır. Taksitli alışverişte üst sınır, kullandırılan finansmanın tutarı
değildir. Bu ayrımı korumayı seçtik ve yeni desenlerde `finansman` çapasını
**zorunlu** tuttuk; böylece harcama bantları yapısal olarak dışarıda kalıyor.

### 3. Kendi gold setimizdeki tutarsızlık — hakem turuna bırakıldı

Ödül alanını düzeltmeye çalışırken kendi sözleşmemizde tutarsızlık bulduk:

- "500 TL **Bonus**" → `alisveris_puani`
- "11.000 TL'ye varan **bonus**" → `odul_miktari`
- "2000 TL **iade**" → `odul_miktari` dolu
- "3.500 TL'ye varan **iade**" → `absent`

Aynı marka ve aynı ödül türü farklı kayıtlarda farklı alanlara yazılmış.
Motoru bu hedefe göre ayarlamak, hangi yöne gidilirse gidilsin başka bir
kaydı bozuyor. Bu bir çıkarım hatası değil, **gold sözleşmesindeki bir
tutarsızlık**; kodda yorumla işaretlendi ve hakem turuna bırakıldı. Marka
puanlarına (ParafPara / Worldpuan / Bonus) bilerek dokunulmadı.

Bu bulgu, tek etiketleyicili bir gold setinin neden yetersiz olduğunu
somutlaştırıyor: 48 kaydımızda etiketleyici dağılımı 12+12+12+12, yani
hiçbir kayıtta örtüşme yok ve `adjudicated` her kayıtta `false`. Örtüşme
olmadan κ anlamlı ölçülemez ve bu tür tutarsızlıklar ölçüme hiç yansımaz.

## Ne değişti

Yalnız 1. kategori düzeltildi. Kendi gold setimizde (strict, tüm küme):

| Metrik | Önce | Sonra |
|---|---|---|
| `finansman_tutari` F1 | 0,571 | **0,857** |
| `odul_miktari` F1 | 0,533 | **0,615** |
| yapısal mikro-F1 | 0,671 | **0,693** |
| makro-F1 | 0,601 | **0,634** |
| halüsinasyon | 0,047 | **0,043** |
| 5 ortak alan, mikro | 0,667 | **0,708** |
| 5 ortak alan, makro | 0,712 | **0,769** |

Harici korpus tarafında dikkatli olmak gerekiyor: düzeltme **öncesi** ölçüm
korpusun tamamında yapılmıştı (36 canlı kayıt, mikro-F1 0,433); düzeltme
**sonrası** rakam ise geliştirme yarısına ait (26 kayıt, 0,576). İkisi farklı
alt kümeler, dolayısıyla doğrudan bir önce/sonra çifti değil. Kesin
kazanç yalnız kendi setimizde ölçülebiliyor — yukarıdaki tabloda.

Kalan farkın büyük bölümü 2. kategori (ontoloji) ve motorumuzda hiç
bulunmayan iki alan (`odul_birimi`, `erteleme_suresi_ay`).

Karşılaştırmanın diğer yönünde de bir bulgu var ve lehimize: karşı motor
bizim setimizde `kar_payi_orani` alanında **7 kez değer uyduruyor**
(kesinlik 0,125), `finansman_tutari`'nda 0,000 alıyor. Bizim motor aynı
alanda 1,000 kesinlikle hiç uydurmuyor. Yani temkinlilik bizim tarafta,
kapsam onların tarafındaydı; bu rapor kapsamın bir bölümünü kapattı.

## Açık uçlar

- **`odul_birimi` alanı yok.** Harici korpusta 23 destekli, yani sık görülen
  bir alan. Ödül miktarını çıkarıyoruz ama birimini (TL / Mil / Gram /
  Worldpuan) ayırmıyoruz. Karşılaştırmada "8.000 Mil vs 1.250 Worldpuan"
  farkı anlamlı olduğu için bu gerçek bir eksik.
- **Gold ödül ontolojisi hakemsiz.** Yukarıdaki tutarsızlık çözülmedi.
- **Held-out küçük.** 10 kayıt / 4 alan-örnek. Anlamlı bir held-out ölçümü
  için kendi korpusumuzdan (1.782 belge) yeni etiketli kayıt gerekiyor.
- **`_CUMLE_SINIRI_RE` iki kez tanımlı** (`extract.py`, iki ayrı satır).
  İkinci tanım ilkini gölgeliyor, yani `extract_tutar` okuyucunun sandığı
  deseni kullanmıyor. Davranış değiştirdiği için bu turda dokunulmadı;
  ayrı bir düzeltme olarak ele alınmalı.

## Tekrar üretme

```bash
# kendi zemin — resmî ölçüm
python -m eval.run_eval --gold data/gold/gold.v2.json --config kural

# regresyon kapısı (alan eşikleri + halüsinasyon tavanı)
python -m eval.run_eval --gold data/gold/gold.v2.json --esikler eval/esikler.json
```

Harici korpus ölçümü, korpusun yerel bir kopyasını ve onun kendi ölçüm
betiğini gerektirir; korpus bu repoya dahil edilmedi. Ölçümde kullanılan
kayıt kimlikleri (geliştirme / held-out ayrımı) bu raporun yazımı sırasında
kaydedildi ve talep hâlinde paylaşılabilir.
