# Hakem turu 04 — gold ↔ kılavuz çelişkisi (`kampanya_kosullari` · `odul_miktari`)

**Tarih:** 2026-08-20
**Tetikleyen:** `gold.round1` regresyon kapısı iki alanda kapandı —
`kampanya_kosullari` 0,847 → **0,143** (`d9c0444` sonrası, "Liste alanları
ONARILDI") ve `odul_miktari` 0,571 → **0,333** (`20b37e8` sonrası, "Büyük harf
değişmezliği ONARILDI + skaler alanlar"). İki düşüşün de sebebi motorun bozulması
değil: bu iki alandaki round1 etiketlerinin bir kısmı bağlayıcı kılavuzla
(`ANNOTATION_GUIDE.md` §4 + §4 "Dört kural" K1–K4 + §4.13) çelişiyor.
**Hakem:** LLM (bu oturum). İnsan hakem DEĞİLDİR ve rapor bunu saklamıyor.
**Kapsam:** round1'de `kampanya_kosullari` dolu **6** kayıt (15 kalem) +
`odul_miktari` dolu **2** kayıt. Toplam 8 kayıt. Diğer 126 kayıt açılmadı.
**Sahiplenilen dosyalar:** `gold.round1.json` (+ `.sha256`), bu belge,
`ANNOTATION_GUIDE.md` §7 künyesi. `gold.v2.json`, `src/**` ve `eval/esikler*.json`
bu turda **DEĞİŞTİRİLMEDİ**.

## Karar dağılımı

| Karar | Sayı | Kayıtlar |
|---|---|---|
| `düzelt` | **2** | `albaraka--detay-dijital-…-pratik-finansman-kart` · `turkiye-emlak-katilim--…-2000-tlye-varan-parafpara` |
| `koru` | **5** | `albaraka--tarim-bankaciligi-diger-finansmanlar` · `dunya-katilim--kredi-kartlari-paraf-platinum-kredi-karti` · `dunya-katilim--…-yatirim-fonlari` · `dunya-katilim--…-yatirim-fonlari-2` · `hayat-finans--kampanyalar-biz-kart-dijital-uyelikler-kampanyasi` |
| `çelişkili` | **1** | `hayat-finans--yatirim-ve-birikim-yatirim-fonlari-yatirim-ve-birikim` |

Kararların dayanağı **yalnız kılavuzdur**. Motorun ne ürettiğine bakılarak
hiçbir etiket değiştirilmedi; ölçüm bölümü (aşağıda) kararlardan **sonra**
okundu ve iki düzeltmenin biri kapıyı hâlâ açmıyor, diğeri açtığı kadar başka
bir alanı da kıpırdatmadı. Skor bu turun amacı değildi.

## 1. Tam envanter — `kampanya_kosullari` (6 kayıt · 15 kalem)

`K1` birebir alıntı · `K2` genel yasal ihtar koşul değildir · `K3` başka alanın
değeri koşula tekrar yazılmaz (istisna: değer bir KOŞULA bağlıysa cümlenin
tamamı girer) · `K4` koşul kalmazsa `absent` · "Sayılmaz": salt geçerlilik
tarihi bildiren cümle + pazarlama sloganı.

| # | Kayıt | Kalem (kısaltılmış) | Kılavuz okuması | Kalem kararı |
|---|---|---|---|---|
| 1 | albaraka pratik-finansman-kart | "Pratik Finansman Kart Finansman Kampanyası **Koşulları** Kampanyadan **1 Ocak 2026 – 31 Aralık 2026** … ilk defa Albaraka'lı olan müşterilerimiz … başvurabilecektir." | Başlık sızıntısı + `kampanya_suresi`de duran tarih aralığı; ama cümle salt tarih bildirmiyor (kanal + ilk kez müşteri şartı) → K3 **istisnası** | **korundu — ÇELİŞKİLİ** (bkz. ÇELİŞKİ/1) |
| 2 | " | "Kampanyamız sadece yeni müşterilerimiz için geçerli olup … faydalanamaz." | Meşru koşul; segment kısmı `hedef_kitle`de, cümle §4.13/2 gereği burada da durur | korundu |
| 3 | " | "Müşterilerimiz kampanya süresi boyunca yalnızca 1 kez … faydalanabilecektir." | Meşru koşul (kullanım sınırı) | korundu |
| 4 | " | "Kampanyadan 25 yaş ve üzerindeki müşteriler yararlanabilecek olup, ayrıca gelir şartı aranacaktır." | Meşru koşul | korundu |
| 5 | " | "Kampanya sadece Albaraka Mobil ve İnternet üzerinden … geçerlidir." | Kanal kısıtı → §4.13/2 gereği tam olarak bu alan | korundu |
| 6 | " | "Pratik Finansman Kart ile **asgari 250 TL, azami 150.000 TL** finansman kullanılabilmektedir." | **K3 ihlali**: çıplak tutar bildirimi; değer `finansman_tutari` = 150.000 TL'de ve o alanın notunda duruyor, hiçbir koşula bağlı değil ("120 aya varan vade tek başına bir koşul değildir" kalıbının aynısı) | **KALDIRILDI** |
| 7 | " | "Sadece ihtiyaç finansmanı olan pratik kart ürünümüzde araç veya konut alıma konu olduğunda … kullanılamamaktadır." | Meşru koşul (kullanım kısıtı) | korundu |
| 8 | " | "Pratik Finansman Kart kullanım koşulları ve ürün detayları için **tıklayınız**." | §4 tanımı: koşul cümlesi değil, gezinme çağrısı; hiçbir şart bildirmiyor, kıyasta sıfır bilgi (K2'nin gerekçesiyle aynı ölçüt) | **KALDIRILDI** |
| 9 | albaraka tarim-bankaciligi | "Finansal Kiralama Makine ekipman, traktör ve biçerdöver finansmanı … **hasat dönemine uygun ödeme koşulları** ile 48 ay vadeye kadar yapılabilmektedir." | İçinde `vade_ay` = 48 var ama cümle salt vade bildirmiyor; ödeme koşulunu da taşıyor → K3 **istisnası** | korundu |
| 10 | " | "IPARD Programı kapsamında destek alan projeleriniz için gerekli olan finansmanı bankamızdan kullanabilirsiniz." | Kapsam koşulu | korundu |
| 11 | dunya paraf-platinum | "Fizikî alışverişlerde, satıcıya ödemenizi Paraf Para ile yapmak istediğinizi **söylemeniz gerekmektedir**." | K1 birebir, gerçek kullanım koşulu; K2/K3 kapsamı dışında | korundu |
| 12 | dunya yatirim-fonlari | "Valörlü fonlarda 100 TL asgari alım limiti bulunmaktadır." | Tutar başka bir alanda **durmuyor** (`finansman_tutari` boş) → K3 tetiklenmiyor; cümle gerçek bir kısıt | korundu |
| 13 | dunya yatirim-fonlari-2 | (12'nin aynısı — belge ikizi) | (12 ile aynı) | korundu |
| 14 | hayat-finans yatirim-fonlari | "TEFAS'ta yazan bütün ihbar süreleri 13.30'dan önce iletilen emirler için geçerlidir." | İşlem koşulu (kesim saati); tarih/tutar değil | korundu |
| 15 | " | "Bahse konu değişiklikler, **03.03.2025** tarihinde uygulamaya alınacak olup, ileri valörlü fonlarda asgari işlem tutarı **100 TL** … uygulanacaktır." | İki savunulabilir okuma → karar verilemedi | **ÇELİŞKİLİ** (bkz. ÇELİŞKİ/3) |

K2 (genel yasal ihtar) kalemi bu 15 kalemin **hiçbirinde** yok — K2 kalibrasyon
dosyalarına `scripts/kalibrasyon_hakemlik --kural kosul-ihtar` ile geçmişe dönük
zaten işlenmişti (§4, "Zaten uygulandı").

## 2. Tam envanter — `odul_miktari` (2 kayıt)

| Kayıt | Etiket | Kılavuz okuması | Karar |
|---|---|---|---|
| `hayat-finans--kampanyalar-biz-kart-dijital-uyelikler-kampanyasi` | `{"value": 300.0, "currency": "TRY"}` — "…kazanılabilecek maksimum **nakit ödül** tutarı toplamda 300 TL'dir" | §4 `odul_miktari` "Sayılır: … **1.000 TL nakit iade**" kalıbının birebir eşi. Ödül nakit olarak cari hesaba aktarılıyor → marka puanı değil | **koru** |
| `turkiye-emlak-katilim--…-2000-tlye-varan-parafpara` | `{"value": 2000.0, "currency": "TRY"}` — "…kazanabileceği **ParafPara** tutarı 2.000 TL ile sınırlı olacaktır" | §4 `alisveris_puani` ADET kuralı ("1.000 chip-para", "60.000 Mil") — ParafPara marka puanıdır, nakit değildir | **düzelt** → `alisveris_puani` = `{"kind": "points", "value": 2000.0}`, `odul_miktari` → `absent_fields` |

---

## ÇELİŞKİ

> CLAUDE.md HARD RULE 4: çelişki gizlenmez, silinmez; iki taraf da kaynağıyla
> yazılır. Aşağıdaki dört başlıkta her iki taraf duruyor.

### ÇELİŞKİ/1 — Başlık sızıntısı + tarih aralığı bir koşul kaleminin içinde

**Round1'in etiketi** (`gold.round1.json`,
`albaraka--detay-dijital-musterilere-ozel-pratik-finansman-kart`, 1. kalem):
`"Pratik Finansman Kart Finansman Kampanyası Koşulları Kampanyadan 1 Ocak 2026 –
31 Aralık 2026 tarihleri arasında … başvurabilecektir."` Aynı belgede
`kampanya_suresi` = `2026-12-31`, yani tarih ikinci kez yazılmış; ayrıca kalemin
başında alanın kendi başlığı ("… Kampanyası **Koşulları**") duruyor.

**Kılavuzun iki tarafı:**
- *Aleyhte:* §4 "Sayılmaz: sadece geçerlilik tarihi bildiren cümle (o
  `kampanya_suresi`)" ve **K3** "Vade, tutar, oran, **tarih**, taksit kendi
  alanına yazılır; koşullara ikinci kez kopyalanmaz."
- *Lehte:* K3'ün kendi **istisnası** — "değer bir KOŞULA bağlıysa cümlenin
  tamamı buraya da girer" (§4 `kar_payi_orani` sınır vakası, §4.13/4 ile aynı
  kural). Bu cümle salt tarih bildirmiyor: uygulamayı indirme, "Müşteri Olmak
  İstiyorum" adımı ve **ilk defa müşteri olma** şartını taşıyor; tarih bu
  koşulun zaman niteleyicisidir. "Sayılmaz" maddesi "**sadece** … bildiren
  cümle" diyor, bu cümle o tanıma girmiyor.
- Başlık sızıntısına gelince: kılavuzda başlık sızıntısını yasaklayan **hiçbir
  bağlayıcı kural yok**, ve aynı olguya daha önce karar verilmiş — `_hakem_
  kararlari.jsonl`, `albaraka--tarim-bankaciligi-diger-finansmanlar`: *"Başındaki
  'Finansal Kiralama' başlık sızıntısı düzleştirilmiş HTML kaynaklı biçim
  kusurudur, değeri yanlış kılmaz"* → `verdict: ok`.

**Hangisi kazandı ve neden:** kalem **korundu**. Kılavuzda dayanağı olmayan bir
kesme işlemi yapmak, hakem turunu "motoru haklı çıkarma" turuna çevirirdi. Ama
çelişki gizlenmiyor: kalem biçim olarak kusurludur (alan adının kendisi değerin
içinde) ve bunu yasaklayacak kural **kılavuzda yoktur**. Kural yazma yetkisi bu
turun değil, ekibin: öneri, §4'e "kalem, cümlenin kendisidir; düzleştirilmiş
HTML'den gelen başlık öneki kaleme dahil edilmez" cümlesinin eklenmesidir
(uygulanmadı, ANA OTURUM'a bırakıldı).

### ÇELİŞKİ/2 — Round1'in notu ile round1'in değeri birbirini yalanlıyor

**İki kayıtta** (`albaraka--tarim-bankaciligi-diger-finansmanlar`,
`dunya-katilim--kredi-kartlari-paraf-platinum-kredi-karti`) `notes.kampanya_
kosullari` şunu diyor: *"… ürün tanıtım sayfasıdır, **kampanya koşulu
içermemektedir**. Model … koşulu olarak **hatalı üretmiştir**."* — oysa alan
**dolu**.

**İki taraf:**
- *Notun tarafı:* B etiketleyicisinin özgün kararı. Kaynağı
  `review/round1_B.csv` (aynı not, aynı cümle) — B bu hücrede modelin değerini
  reddetmişti.
- *Değerin tarafı:* A aynı hücreye `verdict: ok` yazdı
  (`review/round1_A.csv`), kör makine hakemi uyuşmazlığı **B→A** yönünde
  kapattı (notun kuyruğundaki `#hakemlik-round1 B->A (kor hakem onayi)` damgası)
  ve ikinci bir hakem turu (`review/_hakem_kararlari.jsonl`) K1/K3'e dayanarak
  **`verdict: ok`** dedi.

**Hangisi kazandı ve neden:** değer **korundu** (`koru`). HAKEM-04 kılavuza
bakarak bağımsız olarak aynı sonuca varıyor (envanter satırları 9–11): iki
cümle de K1 birebirdir, K2 kalıbı değildir ve K3'ün istisnası kapsamındadır.
Not metni **silinmedi** (HARD RULE 3); üstüne HAKEM-04 kaydı eklendi, böylece
kaydı okuyan biri "not değeri yalanlıyor" tuzağına düşmüyor.

### ÇELİŞKİ/3 — K3 mü, K3 istisnası mı: tarih + tutar taşıyan koşul cümlesi

**Round1'in etiketi** (`hayat-finans--yatirim-ve-birikim-yatirim-fonlari-…`,
2. kalem): *"Bahse konu değişiklikler, 03.03.2025 tarihinde uygulamaya alınacak
olup, ileri valörlü fonlarda asgari işlem tutarı 100 TL … uygulanacaktır."*
Aynı kayıtta `finansman_tutari` = `{"value": 100.0, "currency": "TRY"}`.

**İki taraf:** (a) **K3** — tarih ve tutar kendi alanlarına aittir, tutar zaten
`finansman_tutari`de duruyor, cümle ikinci kopyadır. (b) **K3 istisnası** —
tutar bir koşula bağlıdır ("**ileri valörlü fonlarda**" asgari işlem tutarı),
o hâlde cümlenin tamamı buraya da girer; ayrıca cümle salt tarih bildirmediği
için "Sayılmaz" maddesi tetiklenmiyor.

**Hangisi kazandı:** **hiçbiri.** Kayıt `çelişkili` işaretlendi, etiket
**değiştirilmedi**, iki okuma da `notes`a yazıldı. Kılavuz "bir tutar hem kendi
alanına hem bir koşul cümlesine girdiğinde hangi eşik geçerlidir" sorusuna cevap
vermiyor; bu bir kılavuz boşluğudur ve tek taraflı kapatmak kılavuzu hakemin
tercihiyle yazmak olurdu.

### ÇELİŞKİ/4 — Aynı nesne (ParafPara) iki farklı alanda

**Round1 kendi içinde tutarsız.** Aynı etiketleyici (`D`), aynı banka, aynı
`campaign_type` (`Alışveriş Puanı`), aynı nesne:

| Kayıt | Alan | Değer |
|---|---|---|
| `…-beyaz-esya-ve-elektronik-alisverislerinize-3000-tlye-varan-parafpara` | `alisveris_puani` | `{"kind": "points", "value": 3000.0}` |
| `…-paraf-ile-secili-e-ticaret-alisverislerinize-2000-tlye-varan-parafpara` | `odul_miktari` | `{"value": 2000.0, "currency": "TRY"}` |

Dahası: 2.000'lik kayıt **zaten hakemliğe düşmüştü** —
`needs_adjudication: true`, `unclear_fields: ["alisveris_puani"]`. Kaynak
`review/round1_main_D.csv`: ön anotasyon **aynı 2.000 değerini iki alana birden**
üretti; D `odul_miktari`na `ok`, `alisveris_puani`na **`unclear`** dedi. Yani bu
hücre karara bağlanmamış, askıda bırakılmıştı.

**İki taraf:**
- *`odul_miktari` lehine:* §4.13/3, `odul_miktari`nı "zaten **para-tipli müşteri
  kazancı** alanı" diye tanımlıyor; ParafPara TL cinsinden ifade edilmiş
  ("2.000 TL ParafPara") ve bir ödüldür.
- *`alisveris_puani` lehine:* §4 `alisveris_puani` **ADET** kuralı marka puanı
  birimlerini birebir sayıyor ("1.000 chip-para", "60.000 Mil"). ParafPara nakit
  değildir: yalnız Paraf üye iş yerlerinde harcanır ve *"Kullanılmayan
  ParafPara'lar 15 Ekim 2026 tarihinde geri alınacaktır"* (belge metni) — yani
  bir marka puanı bakiyesidir. Ayrıca `campaign_type` = `Alışveriş Puanı`.

**Hangisi kazandı ve neden:** **`alisveris_puani`**. Özel kural (marka puanı →
`alisveris_puani`) genel tanımı (para-tipli kazanç) yener; §4 `alisveris_puani`
bölümünün kendi gerekçesi de bunu söylüyor: *"Ayrım yapılmazsa '%5' ile '1.000
puan' aynı sütunda sıralanır ve karşılaştırma tablosu anlamsızlaşır"* — aynı
gerekçe, aynı nesnenin iki ayrı alana dağılmasında bir kat daha geçerlidir.
Round1'in kendi içindeki tutarsızlık, çoğunluk yönünde (`points`) giderildi.
`odul_miktari` `absent_fields`e eklendi: "baktım, ParafPara'dan ayrı bir ödül
tutarı YOK" (§3.1 anlamıyla) — bilgi kaybı yok, alıntı (`field_spans`) aynı
cümledir. Ayrım netleştirilmiş hâliyle: **nakit hesaba geçiyorsa
`odul_miktari`, marka puanı bakiyesiyse `alisveris_puani`** — bu turun iki
`odul_miktari` kararı tam olarak bu ayrımdan çıkıyor.

---

## KANITLANAMAYAN — bu turda İDDİA EDİLMEDİ

Round1 kayıtlarında **etiketleme tarihi ya da kılavuz sürümü meta verisi
yoktur** (`annotators`, `adjudicated` var; tarih yok). Round1 dosyası
15 Ağustos'ta yeniden derlendi — yani dört kuraldan (2026-08-09) **sonra**.
Bu yüzden *"bu etiketler kurallardan eskidir, o hâlde geçersizdir"* iddiası
**kanıtlanamaz** ve bu belgede kurulmamıştır. Kurulan tek iddia şudur ve yeterlidir:
**etiket, bağlayıcı kılavuzun belirli bir maddesiyle çelişiyor** — her satırda
madde numarası verilmiştir.

## Ölçüm — önce / sonra (dürüst)

`.venv/bin/python -m eval.run_eval --gold data/gold/gold.round1.json --config kural`

| Alan | Önce | Sonra | Not |
|---|---|---|---|
| `kampanya_kosullari` (ikili) | 0,143 (TP 1 · FP 7 · FN 5) | **0,143** (TP 1 · FP 7 · FN 5) | değişmedi — kapı hâlâ kapalı |
| `kampanya_kosullari` (kalem) | 0,409 (P 0,310 · R 0,600) | **0,429** (P 0,310 · R 0,692) | FN 6 → 4 |
| `odul_miktari` | 0,333 (TP 1 · FP 3 · FN 1) | **0,400** (TP 1 · FP 3 · FN 0) | destek 2 → 1; kapı hâlâ kapalı (eşik 0,490) |
| `alisveris_puani` | 1,000 (destek 2) | **1,000** (destek 3) | motor bu belgede de `{"kind":"points","value":2000}` üretiyor |
| MİKRO | 0,732 | **0,736** | |
| MİKRO (yapısal) | 0,761 | **0,765** | |
| MAKRO | 0,592 | **0,599** | |

**Kapı sonucu değişmedi:** `--esikler eval/esikler-round1.json` hâlâ KAPALI, iki
gerileme ile (`kampanya_kosullari` 0,143 < 0,847 · `odul_miktari` 0,400 < 0,490).
Hakem turu skoru kurtarmadı ve kurtarmak için de yapılmadı.

`gold.v2` tabanında koşu **birebir aynı** çıktıyı verdi (`gold.v2.json`
sha `e38a5276`, değişmedi): round1 düzeltmesi v2'yi bozmuyor.

### Neden `kampanya_kosullari` ikili F1'i kıpırdamadı

İkili ölçüt bu alanda **tüm listenin tam eşitliğini** arıyor; 6 destekli,
serbest metinli bir liste alanında bu neredeyse hep 0/1'dir. `esikler-round1.json`
bunu kendi içinde zaten yazıyor: *"serbest metin; ikili ölçüt bu alanda
metodolojik olarak zayıftır"*. 2026-08-15'te ölçülen 0,857, motorun o günkü
çıktısının round1'in uzun cümlelerine **birebir denk düşmesiydi**; `d9c0444`
motoru kısa kanonik cümlelere getirdiğinde eşitlik bozuldu. Bu turda kaldırılan
iki kalem gerçek bir kalem hatasıydı ve etkisi **kalem** ölçütünde görünüyor
(0,409 → 0,429) — ikili ölçütte görünmesi zaten beklenmezdi.

## `eval/esikler-round1.json` için gereken güncellemeler (UYGULANMADI)

Bu turda eşik dosyasına dokunulmadı (kapsam dışı). ANA OTURUM'a öneri:

1. `gold_sha256`: `"4d53fe6d"` → **`"dc0e45d8"`** (dosya değişti; bu alan
   "hangi gold ölçüldü" sorusunun cevabı).
2. `olculdu`: `"2026-08-15"` → **`"2026-08-20"`**.
3. `kampanya_kosullari`: `0.847` → ölçülen **0,143**. İki dürüst seçenek var ve
   ikisi de belgelenmeli: (a) eşiği 0,140'a indirmek — kapı açılır ama alanı
   fiilen ölçmeyi bırakır; (b) bu alanın kapısını **kalem** ölçütüne bağlamak
   (ölçülen 0,429 → eşik 0,420) ve ikili sayıyı yalnız raporda tutmak. Hakem
   (b)'yi öneriyor: kararı `run_eval.kalem_bolumu` zaten üretiyor ve eşik
   dosyasının kendi uyarısıyla tutarlı.
4. `odul_miktari`: `0.490` → ölçülen **0,400**; destek 2'den **1**'e düştüğü için
   `_dusuk_destekli_alanlar` notu da güncellenmeli ("destek 1 — F1 sembolik").
5. `alisveris_puani`: `0.990` yerinde kalabilir (ölçülen 1,000), ama destek
   2 → **3**; `_dusuk_destekli_alanlar` notu buna göre düzeltilmeli.
6. `mikro_yapisal`: `0.729` → ölçülen **0,765**; kapı "bugünkünü kaybetme"
   mantığıyla yükseltilebilir. Hakem karar vermiyor, sayıyı bildiriyor.

## Değişen dosyalar

- `data/gold/gold.round1.json` — 6 kayıt dokunuldu (2 etiket düzeltmesi, 4
  yalnız `notes` kaydı), sha256 `4d53fe6d…` → `dc0e45d8…`
- `data/gold/gold.round1.json.sha256` — `scripts.gold_schema.write_gold` ile
  yeniden üretildi (dosyanın kendi mekanizması)
- `data/gold/review/_hakem-turu-04-gold-kilavuz-celiskisi.md` — bu belge
- `data/gold/ANNOTATION_GUIDE.md` — **yalnız §7 künyesi**; hiçbir kural
  değiştirilmedi

Commit atılmadı (ANA OTURUM atacak).
