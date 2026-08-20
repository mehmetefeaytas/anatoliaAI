# `campaign_type` onarımı — kök nedenler, ölçümler ve çürütülenler

**Tarih:** 2026-08-20 · **Kapsam:** `campaign_type` (8 sınıf kampanya türü)
**Dokunulan dosyalar:** `src/extraction/rules/_ortak.py` ·
`src/extraction/rules/hedef_kitle.py` · `src/extraction/ner/classifier.py` ·
`src/pipeline.py` · `eval/run_eval.py` · `eval/esikler.json` ·
`eval/esikler-round1.json` · `scripts/eval_classifier.py` ·
`tests/test_gezinme_seridi.py` · `tests/test_campaign_type_kapisi.py`

**Tek satırlık özet:** Kampanya türü, metindeki anahtar kelime çeşidine
bakıyordu ve puan eşitliğinde her zaman `Konut Finansmanı` kazanıyordu; artık
kararı önce URL yolu veriyor, eşitlikte tür uydurulmuyor, ve alan ilk kez resmî
değerlendirme hattında ölçülüyor.

---

## 1. Manşet sayılar — önce / sonra

| Ölçüt | gold.round1 (134 kayıt) | gold.v2 (48 kayıt) | gold.v1 (20 kayıt) |
|---|---|---|---|
| doğruluk, gold ETİKETLİ | **0,667 → 0,798** | **0,590 → 0,769** | 0,700 → 0,800 |
| doğruluk, TÜM belgeler | 0,567 → 0,731 | 0,521 → 0,729 | — |
| makro-F1 (8 sınıf) | — → 0,702 | — → 0,775 | 0,762 → 0,793 |
| uydurma (gold `null`, tür üretildi) | 20/20 → **13/20** | 7/9 → 4/9 | — |
| çekimserlik (gold etiketli, tahmin `null`) | 0 → 2 | 3 → 3 | 2 → 1 |

`etiketli` paydası gold'da tür yazan belgelerdir (round1'de 114, v2'de 39) ve
görev tanımındaki taban sayılarla (0,667 / 0,590) birebir aynı paydadır.

**Hedef 0,85'e ULAŞILAMADI.** Niçin ulaşılamayacağı §5'te ölçüldü: URL dizinini
ezberleyen bir kâhin bile round1'de **0,798**'de kalıyor — yani bu gold üzerinde
bugünkü sonuç, URL yolunu kullanan herhangi bir deterministik kuralın
erişebileceği tavanın tam üzerinde. Sayıyı yukarı çekmenin yolu daha çok kural
değil, gold'un kendi tutarlılığıdır.

---

## 2. Kök neden 0 — `raw_text` gezinme şeridi taşıyor

`hedef_kitle._gezinme_seridi` ölçütü (≥6 kelime, ≥%60 büyük harfle başlayan
sözcük, sonda `.`/`!` yok) `src/extraction/rules/_ortak.py`ye **taşındı ve
kamuya açıldı** (`gezinme_seridi`). Davranış birebir korundu; eski private ad
`hedef_kitle`de takma ad olarak duruyor, `extract.py` yeniden ihracı ve
`tests/test_hedef_kitle_etiket.py` bozulmadı. Yeni test:
`tests/test_gezinme_seridi.py` (9 vaka, biri ölçütün SINIRINI kilitler).

Gerekçe: aynı kirlilik iki ayrı hataya sebep oluyor (`hedef_kitle` yanlış
pozitifleri **ve** arayüzün şeridi ekrana basması), yani ölçüt iki katmanın
ortak malıdır. İki kopya kaçınılmaz olarak ayrışırdı.

**ÇÜRÜTÜLDÜ — bu ölçüt sınıflandırıcı girdisini temizlemeye YETMEZ.**
Şerit noktalama taşımadığı için `split_sentences` onu ilk gerçek cümleye
kaynatır; birleşik cümle `.` ile bittiği için ölçüt `False` döner. Üç ayrı
temizleme kipi ölçüldü, URL sinyali sabit tutularak:

| Nav temizleme kipi | round1 (etiketli) | gold.v2 (etiketli) |
|---|---|---|
| yok (**seçilen**) | **0,754** | **0,667** |
| şerit cümlesini tamamen at | 0,746 | 0,667 |
| ilk cümlenin baş şeridini kırp | 0,746 | 0,641 |
| her cümlenin baş şeridini kırp | 0,754 | 0,641 |

(Bu tablo onarımın ara aşamasında, bileşik ipuçları eklenmeden önce ölçüldü;
sıralama sonraki aşamalarda da değişmedi.) Şeridi kırpmak gerçek başlığı da
kesiyor — sayfa başlığı ürünün adını taşıyan **en iyi** metin sinyalidir, menü
ile aynı sözdizimsel imzayı taşır ve ikisi ayırt edilemiyor. Bu yüzden
sınıflandırıcı girdisi temizlenmedi; kirliliğin panzehiri URL sinyali oldu.

Ayrıca ölçüldü: sınıflandırıcıyı kandıran çerçeve, öngörülen menü şeridi
DEĞİL, **çerez/onay metni**. Dört belgede (`dunyakatilim/kampanyalar/carter-s`,
`divarese`, `damat-tween`, `ramsey`) tek "ihtiyaç" geçişi şu cümledeydi:
*"…kullanıcının kişisel tercihlerine ve ihtiyaçlarına uygun içerikleri…"* —
tam bir cümle, şerit değil, dolayısıyla hiçbir şerit ölçütü onu elemez.

---

## 3. Kök neden 1 — sınıflandırıcının üç kusuru

### 3.1 Beraberlik kırıcı `Konut`u varsayılan galip yapıyordu

Eski kod: `max(scores, key=lambda l: (scores[l], -self._ORDER.index(l)))` ve
`_ORDER[0] == "Konut Finansmanı"`. Artık eşitlikte `(None, 0.0)` dönüyor
(CLAUDE.md §19, kılavuz §4.13/1: *"`null` bir hatanın değil bir kararın
adıdır"*).

Korpus üzerinde ölçüldü (`data/raw`, 2.184 belge):

| | ÖNCE | SONRA |
|---|---|---|
| beraberlikle karara bağlanan (metin kolu) | 666 (%30,5) | 359 (%16,4) |
| kararı URL kovasının verdiği belge | 0 | 1.355 (%62,0) |
| `Konut Finansmanı` etiketi | 230 | **96** |
| `None` (tür yok) | 160 | 233 |

Yani beraberlik hem AZALDI (bileşik ipuçları yapay beraberlikleri çözdüğü için)
hem de kalan beraberlik artık `Konut`a değil `None`a gidiyor; ve belgelerin
%62'si beraberlik hesabına hiç girmiyor çünkü kararı URL veriyor.

### 3.2 URL yolu hiç kullanılmıyordu

`RuleHintClassifier.classify(text, source_url=None)` artık URL yolunu
deterministik bir kova tablosundan geçirir (`_URL_KOVALARI`); eşleşme varsa o
tür döner, eşleşme yoksa metin kolu koşar, o da karar veremezse `None`.
Kalıp `scripts/build_demo_db.py::belge_turu_ata`den alındı: URL + yol →
deterministik, eşleşmezse `NULL`, tür uydurma yok. `src/pipeline.py:193` artık
`doc.source_url`'ü veriyor; `scripts/eval_classifier.py` de aynı imzayı koşuyor
(harness ile üretimin ayrışmaması için — o dosyanın kendi başlığındaki "eşit
koşul" kuralı).

Kova tablosuna KASITLI olarak alınmayanlar ve gerekçeleri (hepsi ölçülü):

| Aday | Niçin YOK |
|---|---|
| `arac` (tek başına) | `hesaplama-araclari` ve `elektrikli-arac-sarj-…` yollarını taşıt sanıyor; yalnız `arac-finansman` bileşiği alındı |
| `musteri-ol` | +1 doğru / −1 yanlış — net sıfır |
| `iade` | gold "5'e varan iade"yi `Kart`, "3 nakit iade"yi `Alışveriş Puanı` etiketliyor; ayırt etmiyor |
| `bankkart` | tek örnek; tek örnekten kural aşırı uyum |
| `bireysel`+`finansman` → İhtiyaç | +4 doğru / −5 yanlış |

Jeton eşleşmesi üç eşiklidir (`_url_eslesir`): <4 karakter TAM jeton
(`fon`, `mil`), 4–5 karakter ÖN EK (Türkçe sondan eklemeli), ≥6 karakter
ALT DİZE. Alt dize eşiği ölçümle geldi: slug'lar bitişiyor
(`kuveyt-turkandvavacars`) ve ön ek eşleşmesi `vavacars`ı kaçırıyordu
(round1 0,781 → 0,789).

### 3.3 `kredi kartı` iki etikete birden oy veriyordu

`Kart` ipucu "kredi kartı", `Finansman` ipucu "kredi" — aynı öbek iki etiketi
puanlıyor ve **yapay** bir beraberlik üretiyordu. Ölçülen dört belge
(`avvada-500-tl-indirim`, `business-plus-ile-akaryakitta-indirim`,
`cok-kazananlar-kulubu`, `akaryakit-harcamalarinda-5e-varan-iade`) gold `Kart`
iken beraberlikten `None` çıkıyordu.

Çözüm iki parçalı ve tek mekanizma:
* **Bileşik ipuçları** (`_BILESIK_IPUCLARI`) — "kredi kart\*", "konut
  finansman\*", "araç kredi\*", "katılma hesab\*" gibi daha uzun, daha özgül
  öbekler; sahibi etikete puan verir.
* **Kapsama kuralı** — bir eşleşme, BAŞKA bir etikete ait daha uzun bir
  eşleşmenin içine tamamen düşüyorsa sayılmaz.

Dilbilgisel gerekçe: Türkçe'de bileşik ad öbeğinin anlamı öbeğin tamamına
aittir. Ölçüm:

| Bileşik ipucu katmanı | round1 | gold.v2 |
|---|---|---|
| yok | 0,772 | 0,744 |
| var, PUANSIZ (yalnız gölgeleyen) | 0,789 | 0,744 |
| var, PUANLI (**seçilen**) | **0,798** | **0,769** |

Puanlı sürüm ayrıca çekimserliği 5 → 2, uydurmayı 16 → 13 düşürdü. Sebep
`synonyms.keyword_pattern`in kısa-anahtar kuralıdır: "kart" 4 karakter olduğu
için iki taraftan sınırlı eşleşir ve "kartları"na UYMAZ; bileşik ipucu
`\w*` ile bittiği için uyar.

---

## 4. Çürütülen hipotezler (ölçüldü, uygulanmadı)

### 4.1 "Puan anahtarı frekans olmalı, çeşit değil" — ÇÜRÜK

| Puan anahtarı | round1 | gold.v2 |
|---|---|---|
| çeşit (**korundu**) | **0,667** (o aşamadaki taban) | **0,590** |
| frekans | 0,526 | 0,436 |

Sebep ölçülebilir: çerçeve metninde onlarca kez tekrarlanan genel sözcükler
("kart", "finansman", "kredi") bir kez geçen özgül ipucunu ("parafpara",
"mil") eziyor. Frekans, tam olarak düzeltmeye çalıştığımız hatayı —çerçeve
hacminin etiketi belirlemesini— **büyütüyor**.

### 4.2 "Nav şeridi temizliği sınıflandırıcıyı düzeltir" — ÇÜRÜK

Sayılar §2'de. Ek olarak: aynı belge iki kez daha kötüleşmedi, yalnız gold.v2
0,667 → 0,641 düştü ve round1 sabit kaldı — yani en iyi durumda etkisiz.

### 4.3 "`synonyms.NEGATION_RE` ile dışlama penceresi id 601'i eler" — ÇÜRÜK, İKİ KEZ

**Birincisi olgusal:** `NEGATION_RE` gerekçe olarak gösterilen cümleyle **hiç
eşleşmiyor**. Doğrulama (`tr_fold_ascii` sonrası):

```
"sadece ihtiyac finansmani olan pratik kart urunumuzde arac veya konut alima
 konu oldugunda ilgili finansman kart kullanilamamaktadir."
-> re.search(NEGATION_RE, ...) is None
```

Desen ücret negasyonu için yazılmış (`alınmaz`, `tahsil edilmez`, `muaf`,
`bedelsiz`); `kullanılamamaktadır` orada yok ve olmaması doğrudur — o desenin
işi masraf alanıdır.

**İkincisi ölçümsel:** dışlama penceresi (NEGATION_RE + `değil`, `hariç`,
`dışında`, `-ama-` yetersizlik eki) uygulandığında doğruluk DÜŞTÜ:

| Dışlama penceresi | round1 | gold.v2 |
|---|---|---|
| yok (**seçilen**) | **0,754** | **0,667** |
| var | 0,737 | 0,667 |

Ve ironi belgeye kayıtlı: id 601'in "dışlama" cümlesi aynı zamanda o belgedeki
**tek** `ihtiyaç finansmanı` kanıtıdır. Cümleyi elemek, gold'un istediği
etiketi (`İhtiyaç Finansmanı`) üreten yegâne kanıtı silmek olurdu.

### 4.4 "URL adayları arasından metin hakemlik yapsın" — ÇÜRÜK

URL birden çok kovayla eşleştiğinde metin puanına bakıp seçmek denendi:
round1 0,754 → 0,746, gold.v2 sabit. Sabit öncelik sırası daha iyi ve daha
açıklanabilir.

### 4.5 "Alt dize eşleşmesi her uzunlukta iyi" — KISMEN, sınırlandı

Tüm ≥4 karakterli sözcüklerde alt dize eşleşmesi round1'i 0,781 → 0,789 yaptı
ama "kart"ı "bankkart" içinde eşleştiriyor. Eşik ≥6'ya çekildi: aynı sayı,
savunulabilir kural.

---

## 5. Niçin 0,85 bu gold'da erişilemez — tavan ölçümü

İki bağımsız tavan ölçüldü (yalnız gold'da ETİKET olan kayıtlar üzerinde):

| Tavan | round1 (n=114) | gold.v2 (n=39) |
|---|---|---|
| URL **kovası** çoğunluk kâhini | 0,737 | 0,795 |
| URL **dizini** çoğunluk kâhini (ezberci) | **0,798** | **0,846** |
| bugünkü sonuç | 0,798 | 0,769 |

*URL dizini kâhini*, her URL dizinine o dizindeki çoğunluk etiketini veren,
genelleme yapmayan bir ezberciyi taklit eder — yani URL yolundan türetilebilecek
her deterministik kuralın üst sınırıdır. round1'de **0,798**'de kalıyor çünkü
**23 kayıt** kendisiyle aynı dizindeki kardeşinden farklı etiketlenmiş.
Örnekler:

* `kuveytturk…/finansmanlar/alisveris-finansmanlari/` — `alisveris-finansmani`
  ve `vivense-…` → `İhtiyaç Finansmanı`; `hepsiburada-…`, `lc-waikiki-…`,
  `teknosa-…` → `Finansman`.
* `kuveytturk…/medium/bireysel-finansman-talebi-…-40{12,13,14}.pdf` — neredeyse
  aynı üç form; 4012 ve 4014 `İhtiyaç Finansmanı`, 4013 `Finansman`.
* `ziraatkatilim…/kart-kampanyalari/` — 3 kayıt `Kart`, 1 `Alışveriş Puanı`,
  2 `null`.
* `turkiye-finans-avantajlariyla-mobilden-tanis.aspx` — **aynı URL** round1'de
  `null`, gold.v2'de `Yeni Müşteri`. Deterministik hiçbir fonksiyon ikisini
  birden doğru yapamaz.

Bu bir bahane değil, ölçülmüş bir sınır: alanın hakemlik sonrası insan uyumu
**%91 / κ = 0,841** (`data/gold/iaa_report_round1_hakemlik_sonrasi.md`).
0,85 hedefi bu gold'un kendi tutarlılığının üzerindedir.

---

## 6. Kök neden 2 — alan ölçülmüyordu

`grep campaign_type eval/run_eval.py` → **0 eşleşme**. CLAUDE.md §16 bu alan
için accuracy + makro-F1 istiyor, gold şeması onu birinci sınıf alan sayıyor
(`gold_schema.ANNOTATABLE_KEYS`), ama resmî değerlendirme hattı hiç ölçmüyordu.
Ölçülmeyen alan çürür — ve çürüdü.

Eklenenler:

* `eval/run_eval.py`: `TurSonuc`, `tur_puanla()`, `format_tur()`,
  `tur_bolumu()`. Konsolda ayrı bölüm, `report.md`de ayrı bölüm,
  `metrics.json`da `campaign_type` anahtarı.
* `esik_ihlalleri(..., tur=...)`: dört alt eşik — `dogruluk_etiketli`,
  `dogruluk_tumu`, `makro_f1`, `uydurma_orani_ust_sinir` (ters yönlü).
  Eşik dosyası bölümü tanımlıyor ama ölçüm verilmemişse kapı **sessiz
  geçmez**, ihlal yazar.
* `eval/esikler.json` + `eval/esikler-round1.json`: `campaign_type` satırı,
  ölçülen değerin hemen altına konmuş eşikler ve yazılı gerekçe.

Alan bilerek 12 alanın P/R/F1 tablosuna **girmedi**: bir çıkarıcı değil bir
sınıflandırıcı üretiyor, kapalı 8 elemanlı bir kümeden tek etiket seçiliyor ve
`strict`/`tolerant` eşleştirici ayrımı burada anlamsız. Aynı mikro-F1'de
toplamak kıyaslanamaz iki sayıyı tek sayıya katmak olurdu.

### Ölçülmüş kısıt — gold `absent` ile `karar yok`u ayırmıyor

12 alanda "baktım, yok" kararı `absent_fields`e yazılır ve TN olarak
ödüllendirilir. `campaign_type` için böyle bir kayıt **yok**: ölçüldü,
`absent_fields`/`unclear_fields` içinde `campaign_type` round1'de 0, v2'de 0
kez geçiyor; kılavuzun §4.13/1 "liste sayfası → `absent`" kararı dosyada düpedüz
`campaign_type: null` olarak duruyor. Yani `null`, "tür yok" ile "anotatör karar
vermedi"yi aynı kovada tutuyor.

Belirsizlik gizlenmiyor, **iki** doğruluk birden yayımlanıyor:
`dogruluk_etiketli` çekimserliği cezalandırır, `dogruluk_tumu` dürüst
çekimserliği ödüllendirir. Kapı ikisini birden denetler; birini seçmek, ölçütü
sonuca göre seçmek olurdu.

---

## 7. Beklenen yan etki — daralan tür filtresi

Korpusta **675 belgenin (%30,9)** türü değişti; **117 belge** tür alıyorken
`NULL`a düştü, **44 belge** `NULL`ken tür kazandı (net `None`: 160 → 233).

Bu, tür filtresi kullanan sohbet cevaplarını daraltır: bugün "çalışıyor
görünen" bazı cevaplar "veri yok"a dönebilir. **Bu bir gerileme değildir** —
yerine geçen şey yanlış bir cevap değil, dürüst bir çekimserliktir. Ölçülmüş
karşılığı `Konut Finansmanı` sayısıdır: 230 → 96. Kaybedilen 134 belgenin
büyük kısmı zaten konutla ilgili değildi; gold'da `Konut Finansmanı`
precision'ı 1,000 (round1), yani artık `Konut` diyen her karar doğru.

Dikkat çeken ikinci kayma: `Yeni Müşteri` 29 → 4. URL kovası bu sınıfın
belgelerini (çoğu `kampanyalar/detay/…` yolunda, ürün sözcüğü taşıyan) başka
bir ürün türüne yönlendiriyor. gold.v2'de bu sınıfın recall'ı 0,200; sınıf
`TYPE_HINTS`te yalnız 4 ipucuyla temsil ediliyor ("yeni müşteri", "ilk kez",
"hoş geldin") ve "müşterimiz olun" / "davet et" kalıpları yok. Açık iş (§8).

---

## 8. Açık işler

1. **Liste sayfası tanıma.** Kılavuz §4.13/1 liste ve kampanya-dışı sayfaların
   `absent` olmasını istiyor; motor round1'de 20 `null` belgenin 13'üne tür
   veriyor. Uydurmanın kalan tek büyük kaynağı bu. `belge_turu_ata`nın
   `sozlesme` ayrımı burada kullanılabilir ama tek başına yetmez: gold
   `kredi-karti-uyelik-sozlesmesi.pdf`i `Kart`, `finansal-kiralama-…-leasing.pdf`i
   `Konut Finansmanı` etiketliyor.
2. **`Yeni Müşteri` ipucu kümesi.** `synonyms.TYPE_HINTS` bu sınıfta zayıf;
   genişletmek bu turda YAPILMADI çünkü `synonyms.py` başka bir ajanın
   çalıştığı dosya ve ölçüm dışı bir değişiklik olurdu.
3. **Gold'un kendi tutarlılığı.** §5'teki 23 + 6 kardeş-çelişkisi ve tek URL
   çelişkisi hakemliğe açılmalı. 0,85 hedefi ancak bundan sonra anlamlıdır.
4. **`campaign_type` için `absent_fields` kaydı.** Gold şeması bu alanda
   "baktım, tür yok" kararını ayrı tutmalı; o zaman tek bir doğruluk sayısı
   yeterli olur ve TN ödüllendirilebilir.

---

## Kaynaklar

* `src/extraction/ner/classifier.py` (modül başlığı — kusurlar ve çürütülenler)
* `src/extraction/rules/_ortak.py::gezinme_seridi` (ölçüt ve SINIRI)
* `eval/run_eval.py::tur_puanla` (ölçüt tanımı ve gold kısıtı)
* `eval/esikler.json`, `eval/esikler-round1.json`
  (`_campaign_type_NEDEN_EKLENDI`)
* `data/gold/ANNOTATION_GUIDE.md` §4.13/1 (tek özne testi, `absent` kuralı)
* `data/gold/iaa_report_round1_hakemlik_sonrasi.md` (κ = 0,841, %91 uyum)
* `scripts/build_demo_db.py::belge_turu_ata` (taklit edilen deterministik kalıp)
