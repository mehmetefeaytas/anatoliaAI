# Liste ve skaler alanların iyileştirilmesi — ölçüm defteri

**Tarih:** 2026-08-20
**Kapsam:** `src/extraction/rules/extract.py` (kural katmanı)
**Ölçüm künyesi:** `data/gold/gold.v2.json` (48 kayıt · 40 zor) · konfig `kural`
(LLM kapalı) · eşleştirici `strict` · split `all` · kalem eşiği jeton-Jaccard
0,70 (önceden ilan edildi)
**Önce:** `eval/reports/20260820-101434` · **Sonra:** `eval/reports/20260820-115842`

Bu defter iki işi kaydeder: (1) `kampanya_kosullari` iyileştirmesinin getirdiği
**büyük harf değişmezliği ihlalinin** kök nedeni ve düzeltmesi, (2) skaler
alanlarda yapılan **precision/recall temizliği**. Çürütülen hipotezler
uygulananlarla aynı ayrıntıda yazılıdır — bir hipotezi ölçüp çürütmek de bir
sonuçtur ve tekrar denenmesini önlemek ancak kaydedilirse mümkündür.

---

## 1. Büyük harf değişmezliği ihlali (CI kırmızıydı)

### Belirti

    .venv/bin/python -m eval.properties --raw-dir data/raw
    -> 1782 belge, 3 İHLAL: P2_buyuk_harf_deger_degisti

Üçü de `kampanya_kosullari` alanında:

| belge | önce | BÜYÜK harfte |
|---|---|---|
| `albaraka/docs/bilgilendirme-formu-murabaha.txt` | *"alıcının, satıcının, akde konu malın … irade beyanının (icap -kabul) bulunması gerekir."* | `KABUL) BULUNMASI GEREKİR.` |
| `albaraka/docs/bilgilendirme-formu-icare-is-gucu-hizmet-kiralamasi.txt` | (aynı yapı, 3 kalem) | ilk kalem ortadan kesiliyor |
| `turkiye-emlak-katilim/docs/qr-kur-referanslarina-iliskin-musteri-taahhutnamesi-pdf.txt` | 2 kalem | 3 kalem (fazladan bir parça) |

### Kök neden

Birleşik blok bölücüsünün **tire ayıracı harf büyüklüğüne bağlıydı**:

```python
_IC_AYIRAC_RE = re.compile(r"\s*[;•‣]\s*|\s+-(?=[A-ZÇĞİÖŞÜ])")
#                                        ^^^^^^^^^^^^^^^^^^^^^ ORTOGRAFİK
```

Desen HTML listelerinden metne inen **madde imini** ("… kazanabilir. -Bir kart
ile …") tarif ediyordu ve tipografik olarak doğruydu: madde imi büyük harfle
başlar. Ama bu, çıkarımı yazım biçimine bağladı. İkinci bir yazım kusuru bunu
tetikliyor: **PDF metin çıkarımı birleşik sözcüğün tiresinden önce boşluk
bırakıyor** —

    "(icap -kabul)"   "alım -satım"   "e -posta"   "prim -ücret"

Küçük harfte bu masumdur (ayıraç ateşlemez). Belge büyük harfe çevrildiğinde
`-KABUL`, `-SATIM` birer madde imi gibi görünür, cümle ortadan bölünür ve
listeye yarım bir koşul düşer. Blok 170 karakterlik birleşik eşiğini
(`_BIRLESIK_ESIK`) aştığı için bölücü de devrededir.

Bu kozmetik bir test hatası değil: TEKNOFEST rubriğinin %30'luk model başarısı
kaleminde *"farklı ifade biçimlerini doğru yorumlayabilmesi"* maddesi var ve
banka belgelerinin büyük bölümü (taahhütname, bilgilendirme formu, ücret
tarifesi) BÜYÜK HARFLE yazılıdır. Ürün yüzeyinde zarar somuttur: panelde ve
chatbot cevabında koşul olarak yarım bir cümle görünür, kaynak vurgulaması
cümlenin ortasını gösterir.

### Düzeltme

Ayıraç harf büyüklüğü yerine **önceki noktalamaya** bağlandı:

```python
_IC_AYIRAC_RE = re.compile(r"\s*[;•‣]\s*|(?<=[.!?:])\s+-\s*")
```

Ayrım artık yapısaldır ve ortografiden bağımsızdır: madde imi bir cümle ya da
başlık bitiminden sonra gelir (`". -Bir kart …"`, `"Bitiş Tarihi: - Paylaş"`),
birleşik sözcük tiresi ise harften sonra gelir (`"alım -satım"`).

### Neden bu seçenek — gold AYRIM YAPMIYOR, korpus yapıyor

gold.v2 üzerinde dört seçenek **birebir aynı** sonucu veriyor (48 belgede tire
ayıracı, 170 karakterden uzun ve tetikleyicili bir cümlede hiç ateşlemiyor):

| ayıraç deseni | kalem mikro-F1 | P2 ihlali |
|---|---|---|
| eski `\s+-(?=[A-ZÇĞİÖŞÜ])` | 0,520 | **3** |
| `(?<=[.!?:])\s+-\s*` ← **seçilen** | 0,520 | 0 |
| `(?<=[.!?])\s+-\s*` | 0,520 | 0 |
| tire ayıracı hiç yok | 0,520 | 0 |
| `\s+-(?=\w)` (harf-bağımsız) | 0,520 | 0 |

Seçim bu yüzden gold F1'e değil **korpus kanıtına** dayandı. 1.782 belgede 170+
karakterlik 13.502 cümle tarandı; tire alternatifinin ateşleme sayısı:

| desen | ateşleme | niteliği |
|---|---|---|
| `\s+-(?=\w)` | 208 | çoğu PDF yazım kusuru (`"e -posta"`, `"% -0,52959"`, `"alış -verişi"`) — harf-bağımsız ama YANLIŞ |
| eski desen | 81 | madde imi + büyük harfli belgelerdeki bileşik sözcükler |
| seçilen desen | 114 | madde imi + `"Bitiş Tarihi: - Paylaş"` gibi başlık sonrası liste |

Ayıracı tamamen atmak da değişmezi geçirirdi ama **belgelenmiş madde imi
işlevini** kaybettirirdi; o davranış zaten
`tests/test_kampanya_kosullari_kalite.py::test_birlesik_blok_madde_isaretinden_bolunur`
ile kilitliydi ve yeni testte de ayrıca tutuluyor.

### Doğrulama

    .venv/bin/python -m eval.properties --raw-dir data/raw
    -> 1782 belge (kapsam %91,5) — tüm değişmezler GEÇTİ (0 ihlal)

`kampanya_kosullari` kalem F1 **0,520** (değişmedi, hedef ≥0,520 tutuldu).

Kapı: `tests/test_buyuk_harf_degismezligi.py` — üç gerçek ihlal belgesi
(`eval.properties.check_orthographic_invariance` DOĞRUDAN çağrılarak, ölçüt
kopyalanmadan) + sınıfın sentetik hâli + madde imi işlevinin korunması. Testin
ayrım yaptığı doğrulandı: eski desenle 8 test düşüyor, tire ayıracı atılırsa
madde imi testi düşüyor, seçilen desenle hepsi geçiyor.

---

## 2. Skaler alanlar — önce/sonra

### Manşet

| ölçüt | önce | sonra | değişim |
|---|---|---|---|
| ikili mikro-F1 (strict, all) | 0,513 | **0,570** | +0,057 |
| kalem mikro-F1 (strict, all) | 0,601 | **0,629** | +0,028 |
| yapısal mikro-F1 (strict, all) | 0,744 | **0,823** | +0,079 |
| yapısal mikro-F1 (strict, zor) | 0,760 | **0,837** | +0,077 |
| makro-F1 (strict, all) | 0,658 | **0,765** | +0,107 |
| halüsinasyon oranı | 0,040 (18 vaka) | **0,034** (15 vaka) | −0,006 |
| ikili mikro-F1 (tolerant, all) | 0,558 | **0,614** | +0,056 |

Hedefler (ikili ≥0,60 · kalem ≥0,65) **tutulamadı**; sebebi ve neden bu
oturumda kapanamadığı §4'te.

### Alan bazında (strict, all)

| alan | önce F1 | sonra F1 | tp | fp | fn | not |
|---|---|---|---|---|---|---|
| `vade_ay` | 0,545 | **1,000** | 5 | 0 | 0 | 3 hata da kapandı |
| `kar_payi_orani` | 0,800 | **1,000** | 3 | 0 | 0 | yüzdesiz oran tablosu |
| `finansman_tutari` | 0,857 | **1,000** | 4 | 0 | 0 | tablo tutar kolonu |
| `alisveris_puani` | 0,667 | **0,933** | 7 | 0 | 1 | precision 1,00 korundu |
| `odul_miktari` | 0,615 | **0,727** | 4 | 2 | 1 | 2 uydurma elendi |
| `taksit_sayisi` | 0,909 | 0,909 | 5 | 1 | 0 | dokunulmadı |
| `kampanya_suresi` | 0,936 | 0,936 | 22 | 2 | 1 | dokunulmadı |
| `masraf_durumu` | 0,667 | 0,667 | 4 | 3 | 1 | ÇÜRÜTÜLDÜ (§3.1) |
| `indirim_orani` | 0,667 | 0,667 | 1 | 0 | 1 | ÇÜRÜTÜLDÜ (§3.2) |
| `hedef_kitle` | 0,571 | 0,571 | 10 | 9 | 6 | kural katmanının işi değil |
| `kampanya_kosullari` (kalem) | 0,520 | 0,520 | 78 | 85 | 59 | ÇÜRÜTÜLDÜ (§3.5–3.8) |
| `tahsis_ucreti` | 0,000 | 0,000 | 0 | 0 | 0 | gold.v2'de 0 pozitif örnek |

### Zor-vaka etiketi kırılımı (strict, mikro-F1)

| etiket | önce | sonra |
|---|---|---|
| `celiskili` | 0,500 | 0,571 |
| `eksik_bilgi` | 0,417 | 0,522 |
| `format_varyant` | 0,547 | 0,667 |
| `kosullu_aralik` | 0,549 | 0,653 |
| `terminoloji` | 0,480 | 0,549 |

---

## 3. Yapılan her değişiklik + gerekçesi

Sıra **precision önce** ilkesine göre kuruldu: uydurma eleme, kaçırma
kapatmadan önce gelir (halüsinasyon bileşik avantaj skorunda ağır ve jüri
uydurmayı kaçırmadan sert cezalandırıyor).

### 3.0 `odul_miktari` — marka sadakat puanı ödül DEĞİL (precision)

`_ODUL_DISI_RE`'ye `parafpara|chip-para|maximiles|worldpuan` eklendi.

Gold notu iki kayıtta birebir aynı şeyi söylüyor: *"ParafPara TL cinsinden
sadakat puanıdır (chip-para sınıfı) -> alisveris_puani."* Motor ise
`"1.000 TL ParafPara kazanabilir"` cümlesinden `odul_miktari` üretiyordu; aynı
belgede `alisveris_puani` ZATEN doğru çıkıyordu, yani ikinci alan tamamen
uydurma bir ödül tutarıydı.

Dosyadaki eski yorum marka puanlarını **bilerek** dışarıda bırakıyordu ve
gerekçesi geçerliydi: gold `"Bonus"` için tutarsız (`"500 TL Bonus"` →
`alisveris_puani`, `"11.000 TL'ye varan bonus"` → `odul_miktari`). Bu
tutarsızlık **yalnız `Bonus` için** var — o sözcük Türkçede hem marka hem cins
isim. `ParafPara`/`Worldpuan`/`Maximiles` tekil marka adıdır ve gold onları
tutarlı etiketliyor. Liste bu yüzden **ikiye ayrıldı**: tekil marka adları
eklendi, `bonus` DOKUNULMADI (tutarsızlık hakem turunda, `data/gold/review/`).

Ölçüm: `odul_miktari` 0,615 → 0,727 (fp 4 → 2) · halüsinasyon 18 → 16 · ikili
mikro 0,513 → 0,518. Kayıp yok.

### 3.1 `vade_ay` — yüklem eki (`10 YILDIR`) değeri düşürüyordu

İki ayrı kusur üst üste binmişti:

1. **Desen eşleşmiyordu.** `(ay|yıl|yil|sene)(?:a|da|ta|dan|tan|ı|i|lık|lik)?\b`
   ek listesinde yüklem eki yok; `"azami vade 10 yıldır"` ifadesinde `yıl` ile
   `dır` arasında kelime sınırı olmadığı için eşleşme HİÇ kurulmuyordu. Sonuç:
   `ziraat-katilim--konut-finansmani-kentsel-donusum-finansmani` belgesinde tek
   aday `"en az 1 yıl oturan kiracı"` kalıyor ve vade **12** çıkıyordu (gold 120).
2. **Normalizasyon eki tanımıyordu.** Ek listesine `d[ıi]r|t[ıi]r` eklenince
   eşleşme kuruldu ama `normalize_term_months("10 yıldır")` `None` döndü: değer
   üretilmedi, alan **sessizce boşaldı**.

Düzeltme iki parçalı: ek listesi genişletildi ve normalizasyona ham eşleşme
yerine **sayı + birim** verildi (`f"{group(1)} {group(2)}"`). `raw_value` ve
span ham eşleşme kalır, böylece kaynak vurgulaması bozulmaz.

Ölçüm: `vade_ay` 0,545 → 0,600 (yalnız ek) → **0,727** (normalizasyon da).

### 3.2 `vade_ay` — işlenmiş örnek cümlesi (precision)

`_islenmis_ornek()` kapısı eklendi: eşleşmenin cümlesinde **örnek işareti** VE
**para tutarı** varsa aday elenir.

Ölçülen halüsinasyon (`ziraat-katilim--zekat-hesaplama`, belge bir zekât
hesaplama aracı sayfası): *"Örneğin 10 yıl vadeli 180.000 TL ev borcu olan
kimse …"* → `vade_ay` 120. Gold notu: *"«10 yıl vadeli» ifadesi aynı örnek
cümleye aittir; ürün vadesi değildir."*

**İkinci koşul ölçümle zorunlu oldu.** Yalnız örnek işareti arayan gevşek
sürüm, `vade_ay` üreten 452 belgenin 3'ünü kesiyordu ve **biri gerçek bir ürün
vadesiydi**: *"Örneğin: Kuveyt Türk Çeyiz Hesabı, minimum 3 yıl vade ile …
açılır"*. Yani 2 doğru elemeye 1 yanlış eleme (2:1) — projenin kendi barajının
(`_ALAN_DISI_OZNE_RE`: SMS ailesi 4:0, talep ailesi 3:0) altında. Cümlede para
tutarı da arandığında oran **4:0** oldu; kesilen dördü:

    zekat-hesaplama (120)
    medium-bireysel-finansman-talebi-…-4012 / 4013 / 4014 (12)
        -> "Hesaplama Örneği" / "Örnek Ödeme Planı" blokları

Çeyiz Hesabı kaydı korunur (cümlesinde TL tutarı yok).

Ölçüm: `vade_ay` 0,727 → **0,800** · halüsinasyon 18 → 15.

### 3.3 Oran tablosu BİÇİM C — yüzde İŞARETİ OLMAYAN tablo (recall)

`parse_rate_table` yalnız `%` içeren hücreleri okuyordu. Kuveyt Türk leasing
sayfasındaki tablo yüzde işareti kullanmıyor:

    Vade TL Kar Oranı USD Kar Oranı EUR Kar Oranı
    12 Ay 4.15 0.83 0.79   24 Ay 3.90 0.83 0.79   36 Ay 3.81 0.84 0.79
    48 Ay 3.81 0.90 0.79   60 Ay 3.81 0.90 0.79

Bu belgede İKİ alan birden düşüyordu: `kar_payi_orani` hiç üretilmiyordu (gold
`{min 3,81 · max 4,15}` — tam olarak tablonun ilk kolonunun min/max'ı) ve
`vade_ay` tablonun ilk satırından 12 alıyordu (gold 60).

`_oran_tablosu_c()` yalnız kuyrukta **hiç `%` yokken** devreye girer, yani
biçim A/B'nin alanına girmez. Çıplak ondalık okumak iki yapısal kapıyla
güvenli hâle getirildi ve kapılar **ölçümle** kondu. 1.782 belgede başlığı
tanınıp mevcut biçimlerle satır kuramayan ve kuyruğunda `%` bulunmayan belge
sayısı **5**:

| belge | satırlar | niteliği |
|---|---|---|
| `…esnaf-ve-kobilere-ozel-avantajli-arac-kredisi` | (24, 3.54) (36, 3.29) (48, 3.23) (60, 3.23) | GERÇEK |
| `…esnafa-ozel-avantajli-arac-finansmani` | 6 satır, 12→60 ay | GERÇEK |
| `…kuveyt-turkten-avantajli-leasing-finansmani` | 5 satır, 12→60 ay | GERÇEK |
| `tr.txt` (hesaplama aracı widget'ı) | (1, 1.93) (12, 1.93) | ÇÖP |
| `detay-3-ay-ertelemeli-tasit-finansmani` (düz metin) | (36, 1.20) (24, 1.20) | ÇÖP |

İki çöpü eleyen yapısal özellikler: gerçek tabloların üçünde de satır sayısı
**≥ 3** ve vade kolonu **artan** sırada; çöplerin biri 2 satır, öteki azalan.
Kapı bu ikisini arar → **3:0**.

Ölçüm: `kar_payi_orani` 0,800 → **1,000**.

### 3.4 Tablo hücresi tablonun tamamını temsil etmez (`vade_ay`)

Oran tablosu başlığı `"Vade"` sözcüğüyle başladığı için `extract_vade`'in
"tetikleyiciye en yakın sayı" ölçütü neredeyse her zaman tablonun **ilk
satırını** seçiyor. Leasing belgesinde bu 12 demek; kılavuz ve
`extract_from_rate_table` ise aynı sözleşmeyi paylaşıyor: tablodan vade **en
uzun** vadedir.

Kapı çok dar tutuldu: yalnız tekil çıkarıcının değeri tablonun bir SATIR
DEĞERİYSE (yani hücreden devşirilmişse) ve tablo daha uzun bir vade biliyorsa
tablo kazanır.

**Çürütülen alternatif:** `vade_ay`'ı `_TABLO_YEDEK_ALANLARI`'ndan çıkarıp
tabloyu koşulsuz birincil yapmak. F1 **0,800 → 0,600** düştü, çünkü iki belgede
satır ayrıştırması vadeyi yanlış okuyor ve doğru değer düz metinde duruyor:

    albaraka TOGG          tablo 10 ("T10F" marka adından)   metin 48  ✓
    turkiye-finans mobil   tablo  3 (kolon kayması)          metin 36  ✓

Bu iki vaka dar kapıdan da geçmez: tablo maksimumu (10 / 3) tekil çıkarıcının
değerinden (48 / 36) küçük olduğu için kapı hiç açılmaz.

Ölçüm: `vade_ay` 0,800 → **1,000**.

### 3.5 Tablo tutar kolonu (`finansman_tutari`, recall)

`RateRow`'a `tutar` alanı, başlık deseni olarak `_TUTAR_KOLON_RE` eklendi —
`_TAHSIS_KOLON_RE` ile aynı disiplin: başlıkta adı geçiyorsa vardır, yoksa
yoktur. Çıplak `"tutar"` yetmez; tetikleyici finansmanın kendisini adlandırmalı
(gerekçe `_TUTAR_TETIK` bloğunda ölçümle yazılı: Türkçede her parasal
büyüklüğün adı "… tutarı"dır).

    Araç Modeli Vade (Ay) Kredi Tutarı Aylık Kar Oranı
    T10F V2 12 800.000 0,00%   T10F V2 48 1.700.000 2,99%   …

Gold 1.700.000 ve gold notu sözleşmeyi yazıyor: *"En yüksek finansman tutarı
alındı."* (vade tarafındaki "en uzun vade" kuralının kardeşi).

Ölçüm — korpus etkisi **1 belge** (tam bu kayıt); başka hiçbir belgenin değeri
değişmiyor. Alan ayrıca YEDEKTİR: `extract_tutar` konuşuyorsa tabloya hiç
bakılmaz. Sıfır etki burada başarısızlık değil güvenlik kanıtıdır.
`finansman_tutari` 0,857 → **1,000**.

### 3.6 `alisveris_puani` — `Mil` birimi (recall)

`_PUAN_TRIGGER_RE` ve `_PUAN_SAYI_RE`'ye `\bmil\b` eklendi. Kılavuz §4 örneği
zaten bu birimi sayıyor (*"60.000 Mil" → `{"kind": "points", …}`*), motor ise
`"8.000 Mil hediye"` ifadesini kaçırıyordu.

Büyük harf değişmezliği ayrıca sınandı: `re.IGNORECASE` altında `\bmil\b`
deseni `"MİL"` ile de eşleşiyor (Python tam Unicode kıvrımı yapıyor), yani
`tr_upper`'lı varyant aynı sonucu veriyor — §1'in kusurunun tekrarı değil.

Ölçüm: `alisveris_puani` 0,667 → **0,769** (precision 1,000 korundu).

### 3.7 `alisveris_puani` — nakit iade ORANI (recall)

Kılavuz §4 `indirim_orani` maddesi birebir şöyle diyor: *"Sayılmaz: kâr payı
oranı, puan/iade oranı (o `alisveris_puani`)"*. Motorun `iade` çapası yoktu ve
iki kayıt yalnız bu yüzden düşüyordu:

    "A101'de her alışverişte %3'e varan nakit iade!"            -> rate 3,0
    "…Pegasus harcamalarında %50'ye varan iade kazanılabilir."   -> rate 50,0

`_IADE_TRIGGER_RE` eklendi ve **yalnız oran biçimini** açar. Sebep ölçülmüş bir
tehlike: `"iade"` Türkçede ödülü değil geri dönüşü de anlatıyor
(*"Alışverişin iptal/iade edilmesi durumunda…"*). Adet biçimi de açılsaydı o
cümlelerin ±30 karakterindeki herhangi bir TL tutarı puan sanılırdı.

Korpus ölçümü (1.782 belge): kapı **28 belgede yeni değer**, **3 belgede
değişiklik** üretiyor. Elle bakıldı — 27 yeni değer gerçek nakit iade oranı,
3 değişiklik de doğru yönde (eskiden komşu cümleden 100 "puan" devşiriliyordu,
artık `"işleme %50 iade"` okunuyor). Tek çöp bir ücret tarifesiydi
(*"Çek İade Ücreti 0% 0% …"* → rate 0,0); `_IADE_UCRETI_RE` tam o sınıfı eler —
"iade ÜCRETİ" bir masraftır, ödül değil. Kalan oran **30 doğru / 0 çöp**.

Ölçüm: `alisveris_puani` 0,769 → **0,933**.

---

## 4. Çürütülen hipotezler

Aşağıdakilerin hepsi ölçüldü ve UYGULANMADI. Kayıt, aynı hipotezin bir sonraki
turda yeniden denenmesini önlemek için duruyor.

### 4.1 `masraf_durumu` — "ücretsiz"in nitelediği şeye kapsam kapısı

Üç hatanın **ikisi zaten belgelenmiş ve çürütülmüş** durumdadır
(`extract.py`, `_ALAN_DISI_OZNE_RE` bloğu): *"TOD ayrıcalığını ücretsiz yaşa"*
ve *"Ücretsiz İSPARK Otopark Kampanyası"*. Ayırt edici sinyal (ücret kalemi
adının yakınlığı) ölçüldü ve çürüdü: meşru çıkarımlarda 1/5, halüsinasyonlarda
0/2 — kural iki halüsinasyonu elerdi ama beş meşru çıkarımın dördünü de.
`tests/test_masraf_alan_disi.py` bu sınırı 2 üst sınırıyla kilitliyor.

Üçüncü hata (`hayat-finans--…-hisse-senedi-islemleri`, gold `has_fee: true`,
motor `has_fee: false`) için **yeni** bir hipotez kuruldu ve o da çürüdü:
*"belge/rapor gönderimi bağlamındaki 'ücretsiz' kapsam dışıdır"*.

* **Kılavuz aksini söylüyor.** `ANNOTATION_GUIDE.md` §4 kapsam kuralı
  *"ekstre/gönderim ücreti"*ni açıkça **SAYILIR** listesine koyuyor. Kapsam
  temelli bir kapı kılavuzla çelişirdi.
* **Kanıt n=2.** Kol, `masraf_durumu` üreten 491 belgenin yalnız 2'sinde kararı
  değiştiriyor (biri hedef kayıt, öteki bir ücret bilgi formu).
* **Asıl kusur kapsam değil ÖNCELİK.** Motorun sözleşmesi *"masrafsız iddiası
  sırası ne olursa olsun kazanır"*; burada DAR bir muafiyet (rapor gönderimi)
  GENİŞ bir pozitif ücreti (işlem komisyonu binde 2) eziyor. Gold bu kaydı
  `#celiskili` etiketliyor. Önceliği değiştirmek 1.782 belgede çelişki
  tespitini ve kıyas tablosunu etkiler; ayrı ve bilinçli bir karar olmalı.

Yan bulgu: eski analiz `"e-posta üzerinden ücretsiz gönderim"` vakasını "meşru
çıkarım" sayıyordu. Gold o kayıtta `has_fee: true` diyor, yani vaka meşru
DEĞİL bir yanlış pozitiftir. 1/5 ile 0/2 oranı bu düzeltmeyle 0/4 ve 0/2
olur — kararı DEĞİŞTİRMEZ (kural hâlâ dört meşru çıkarımı elerdi), ama kaydın
doğru olması gerekir.

### 4.2 `indirim_orani` — `"%50'si Bizden"` deyimi

Tek kaçırma bu idiyomdan geliyor (gold 50,0). Korpus taraması:
`%<sayı>'si Bizden` kalıbı **2 eşleşme** (aynı kampanyanın iki kopyası).
n=1 üzerinde kural yazmak, ölçülmemiş bir desene kural yazmaktır (aynı disiplin
`BACKLOG.md`'nin `vade_ay` ve `hedef_kitle` girişlerinde uygulandı).
`docs/rapor/yapilacaklar.md` §3.5'in teşhisi doğrulanmış oldu.

### 4.3 `odul_miktari` — en YÜKSEK tutarı seçmek

`turkiye-finans--…-mobilden-tanis` kaydında motor 1.000 TL, gold 11.000 TL
(*"11.000 TL'ye varan bonus kazanma fırsatı"*). Seçim ölçütünü "tetikleyiciye
en yakın" yerine "en büyük değer" yapmak denendi:

    odul_miktari 0,727 -> 0,600   (tp 4->3, fp 2->2, fn 1->2)

Daha dar bir varyant da denendi: tutarın ardında **tavan işareti** (`'ye varan
/ kadar / dek`) olan adayı tercih et →

    odul_miktari 0,727 -> 0,667   (tp 4->3, fp 2->1)

İkisi de gerileme. Sebep ölçüldü: iki doğru kaydın tavan işareti tutarın
SOLUNDA (*"en fazla 125 TL nakit iade"*, *"en fazla 2000 TL iade"*), yani tek
yönlü bir tavan tercihi onları düşürüyor. Doğru çözüm belge düzeyinde "manşet
ödül" akıl yürütmesi istiyor; kural katmanının işi değil.

### 4.4 `alisveris_puani` / `odul_miktari` — çıplak `Bonus` çapası

Kalan tek `alisveris_puani` kaçırması ve kalan bir `odul_miktari` uydurması
aynı belgeden (`turkiye-finans--kampanyalar-ofot`, *"500 TL Bonus
kazanılacaktır"*) geliyor. Gold `Bonus` için tutarsız: bu kayıtta
`alisveris_puani`, `mobilden-tanis` kaydında `odul_miktari`. Hangi yöne
düzeltilse öteki kayıt bozulur. Tutarsızlık hakem turunda
(`data/gold/review/`); kod tarafında DOKUNULMADI.

### 4.5 `kampanya_kosullari` — "kampanya" sözcüğü geçmeyen belgede koşul yok

Alanın 4 uydurma belgesinin **dördünde de** `"kampanya"` sözcüğü hiç geçmiyor
(`vakif-katilim--odemeler-tasarruf-…`, `ziraat-katilim--zekat-hesaplama`,
`kuveyt-turk--leasing-…-hesaplama-araci`, `adil-katilim--www-adilkatilim-com-tr`).
Sinyal kusursuz görünüyordu ve ÇÜRÜDÜ: gold'da koşulu OLAN **5 belgede** de
`"kampanya"` hiç geçmiyor ve toplam **14 gerçek gold kalemi** taşıyorlar
(`kentsel-donusum` 2, `hayat-finans` fon/hisse/yatırım 2+3+3, `dunya-katilim`
enerya 4). Korpusta koşul üreten 1.467 belgenin **467'si** etkilenirdi. Kapı
uydurmayı 4 belgede susturup gerçek koşulu 5 belgede öldürürdü.

### 4.6 `kampanya_kosullari` — kalem üst sınırını düşürmek

Kapak taraması (kapak-farkında, gold.v2 kalem ölçütü):

| kapak | tp | fp | fn | P | R | F1 |
|---|---|---|---|---|---|---|
| 2 | 38 | 31 | 99 | 0,551 | 0,277 | 0,369 |
| 3 | 56 | 43 | 81 | 0,566 | 0,409 | 0,475 |
| 4 | 66 | 58 | 71 | 0,532 | 0,482 | 0,506 |
| 5 | 73 | 73 | 64 | 0,500 | 0,533 | 0,516 |
| **6 ← yürürlükte** | 78 | 85 | 59 | 0,479 | 0,569 | **0,520** |

Kapak precision'ı yükseltiyor ama F1'i düşürüyor. Mevcut 6 doğru; gold'un en
uzun koşul listesi de 6 kalem.

### 4.7 `kampanya_kosullari` — gezinme şeridi süzgecini bu alana bağlamak

`_gezinme_seridi` (büyük harfle başlayan sözcük oranı ≥ 0,6 ve cümle sonu
noktalaması yok) `hedef_kitle` için yazılmıştı. Koşul kalemlerine bağlanınca
gold kalem F1 0,520 → **0,522** (tek yanlış pozitif elendi: bir leasing
tablosunun kolon başlığı satırı). Korpus taraması bedelini gösterdi: süzgeç
**gerçek koşulları da kesiyor**, çünkü kampanya cümlelerinde marka adları
büyük harf oranını şişiriyor —

    "Kampanyadan faydalanmak için Navlungo üzerinden oluşturduğunuz kargo
     gönderim talebinin ödeme ekranında Kuveyt Türk kredi kartı bilgilerinin…"

0,002'lik kazanç bu bedeli karşılamıyor.

### 4.8 `kampanya_kosullari` — hesaplama aracı talimatı süzgeci

`ziraat-katilim--zekat-hesaplama` belgesindeki üç uydurma koşul bir hesaplama
aracının kullanım talimatıdır. Geniş bir desen (`giriniz|girerek|sepete
ekle|hesaplama yapıl…`) gold kalem F1'i 0,520 → 0,525'e taşıyor ama korpusta
**15 kalemin çoğu gerçek koşuldu**:

    "…kart bilgilerinizi manuel girerek tamamlamanız gerekmektedir."
    "TROY300 indirim kodu … sepete eklenen ürünlerin toplam bedeli üzerinden…"
    "…ilgili kampanya sayfasına girerek size özel tek kullanımlık kod…"

Daraltılmış sürüm (`bu programda|hesaplama yapılmaktadır|hesaplamasında
çalışma`) korpusta **yalnız 2 kalem** kesiyor, ikisi de aynı belgede ve belge
yine boşalmıyor — yani uydurma bayrağı bile düşmüyor. n=1 belgeye kural
yazmanın karşılığı yok.

### 4.9 `kampanya_kosullari` — kalan kaybın büyük kısmı ÖLÇÜTTEN geliyor

Kalem düzeyinde 85 yanlış pozitifin bir bölümü aslında doğru çıkarımdır ve
jeton-Jaccard eşiğinde kayboluyor. Somut örnek (aynı belgede biri FP biri FN
sayılıyor):

    motor: 'Kampanyaya katılmak için "HARCA" yazıp 6026'ya SMS gönderilmesi
            gerekmektedir.'
    gold : 'Kampanyaya katılmak için HARCA yazıp 6026'ya SMS gönderilmesi
            gerekir'
    jeton-Jaccard = 0,636  (< 0,70)  -> hem FP hem FN

Fark iki jetonda: tırnak işareti ve `gerekmektedir.` ↔ `gerekir` çekimi. Motor
tarafında kapatılamaz — kılavuz K1 kalemin metinde BİREBİR bulunmasını
istiyor (`test_kalem_metinde_BIREBIR_bulunur` bunu kilitliyor), yani çıktıyı
gold'un ifadesine yaklaştırmak izlenebilirliği bozardı. Ölçüt tarafı bu
oturumun sahipliğinde değil (`eval/**` dokunulmaz). Kanıt olarak eşik
duyarlılığı tablosu bunu zaten gösteriyor: eşik 0,70 → 0,60 indiğinde kalem
mikro-F1 0,629 → **0,659**'a çıkıyor.

---

## 5. `eval/esikler.json` — gereken güncellemeler (UYGULANMADI)

Kapı şu an **AÇIK** (`--esikler eval/esikler.json` ile çıkış kodu 0). Ama
dosya artık ölçülen başarımın çok altında; bir gerileme sessizce geçebilir.
Aşağıdaki değerler yeni ölçümün hemen altına (0,01 tolerans payıyla) konmalı.
Uygulama ana oturuma bırakıldı.

| anahtar | mevcut eşik | yeni ölçüm | önerilen eşik |
|---|---|---|---|
| `alanlar.vade_ay` | 0,545 | 1,000 | **1,000** |
| `alanlar.kar_payi_orani` | 0,800 | 1,000 | **1,000** |
| `alanlar.finansman_tutari` | 0,857 | 1,000 | **1,000** |
| `alanlar.alisveris_puani` | 0,667 | 0,933 | **0,933** |
| `alanlar.odul_miktari` | 0,615 | 0,727 | **0,727** |
| `mikro_yapisal` | 0,702 | 0,823 | **0,823** |
| `halusinasyon_ust_sinir` | 0,08 | 0,034 | **0,04** |
| `alanlar.hedef_kitle` | 0,286 | 0,571 | **0,571** ¹ |

¹ `hedef_kitle` bu turda DEĞİŞMEDİ (0,571 → 0,571). Eşik 0,286 bir önceki
turdan bayat kalmış; listede duruyor çünkü kapı 0,285'lik bir gerilemeyi
görmez. Bu satırın yükselişi bu oturumun kazancı değildir.

Değişmeyenler (dokunulmasın): `taksit_sayisi` 0,909 · `kampanya_suresi` 0,936 ·
`masraf_durumu` 0,65 · `indirim_orani` 0,667.

`_esigi_olmayan_alanlar` girdileri geçerliliğini koruyor: `tahsis_ucreti`
gold.v2'de hâlâ 0 pozitif örnekli, `kampanya_kosullari` için ikili F1
metodolojik olarak anlamsız.

Ayrıca `olculdu` alanı `2026-08-19` → `2026-08-20` ve
`_degisiklik_gunlugu`'ne bu turun gerekçesi yazılmalı: **yükseliş gold
değişikliğinden değil motor düzeltmesinden geliyor**, gold.v2 sabit
(sha256 `e38a5276…`, 48 kayıt).

### 5.1 İKİNCİ KAPI — `eval/esikler-round1.json` (CI'da AYRI adım)

CI ikinci bir regresyon kapısı koşuyor (`gold.round1.json`, 134 kayıt).
**Bu kapı bu oturumdan ÖNCE de KAPALIYDI:**

    HEAD (bu oturumun değişiklikleri OLMADAN):
      ✗ kampanya_kosullari: F1 0.143 < eşik 0.847

Yani bugünün `kampanya_kosullari` revizyonu (`d9c0444`) round1 tabanında
0,847 → 0,143 düşürmüş; bu oturum o düşüşe dokunmadı ve dokunamaz (aynı
motorun gold.v2'de 0,204 → 0,520 yükselttiği değişiklik). Kapı zaten bilinçli
bir eşik güncellemesi bekliyor.

Bu oturum aynı kapıya **ikinci bir satır** ekliyor:

    ✗ odul_miktari: F1 0.333 < eşik 0.490

Round1 tabanında önce/sonra:

| alan | önce | sonra |
|---|---|---|
| `odul_miktari` | 0,571 (tp 2 · destek **2**) | **0,333** (tp 1) |
| `vade_ay` | 0,667 (uydurma 13) | **0,693** (uydurma 10) |
| ikili mikro | 0,728 | **0,732** |
| yapısal mikro | 0,757 | **0,761** |
| kalem mikro | 0,715 | **0,717** |
| makro | 0,613 | 0,592 ² |

² Makro düşüşünün tamamı `odul_miktari`den geliyor; alanın round1'deki desteği
**2 kayıt**, yani tek kayıt makro ortalamayı 0,02 oynatıyor.

#### ÇELİŞKİ — ParafPara iki gold dosyasında ZIT etiketli

Düşüşün tek sebebi `_ODUL_DISI_RE`'ye eklenen `parafpara` kolu (§3.0) ve
sebebi bir **gold-gold çelişkisidir**:

| kayıt | dosya | ParafPara etiketi |
|---|---|---|
| `turkiye-emlak-katilim--kampanya-paraf-ile-secili-e-ticaret-…-1500-tlye-varan-parafpara` | gold.v2 | `alisveris_puani` (points 1500) · `odul_miktari` **absent** |
| `turkiye-emlak-katilim--kampanya-paraf-ile-adv-magazalarinda-1000-tl-parafpara` | gold.v2 | `alisveris_puani` (points 1000) · `odul_miktari` **absent** |
| `turkiye-emlak-katilim--kampanya-paraf-ile-secili-e-ticaret-…-2000-tlye-varan-parafpara` | gold.round1 | **`odul_miktari`** (2.000 TL) |
| `turkiye-emlak-katilim--kampanya-beyaz-esya-ve-elektronik-…-3000-tlye-varan-parafpara` | gold.round1 | `alisveris_puani` (points 3000) |

Çelişki **round1'in kendi içinde de** var: son iki kaydı AYNI anotatör (`D`)
etiketlemiş ve aynı marka puanını iki farklı alana yazmış. İkisi de
`adjudicated: false` ve `notes` boş.

gold.v2 tarafı ise **hem tutarlı hem gerekçeli**: iki kayıtta da not birebir
*"ParafPara TL cinsinden sadakat puanıdır (chip-para sınıfı) ->
alisveris_puani."* diyor ve bu, `ANNOTATION_GUIDE.md` §4'ün
`alisveris_puani` maddesindeki *"1.000 chip-para → `{"kind": "points", …}`"*
kuralının doğrudan uygulanmasıdır.

**Karar:** motor gold.v2 + kılavuz tarafında bırakıldı. Gerekçe: (a) kılavuz
tek sözleşmedir ve chip-para sınıfını açıkça `alisveris_puani`ya veriyor,
(b) gold.v2 hakem turlarından geçti ve notlarıyla birlikte tutarlı,
(c) round1 etiketi anotatör içi tutarsızlığın bir tarafı, (d) round1'de bu
alanın desteği 2, gold.v2'de 5.

**round1 kapısı için gereken güncellemeler (UYGULANMADI):**

| anahtar | mevcut | yeni ölçüm | önerilen |
|---|---|---|---|
| `alanlar.kampanya_kosullari` | 0,847 | 0,143 | **0,143** (bu oturumun işi DEĞİL — `d9c0444`'ün sonucu) |
| `alanlar.odul_miktari` | 0,490 | 0,333 | **0,333** + gerekçe: gold-gold ParafPara çelişkisi |
| `alanlar.vade_ay` | 0,639 | 0,693 | **0,690** (yükseldi) |
| `mikro_yapisal` | 0,729 | 0,761 | **0,760** (yükseldi) |
| `olculdu` | 2026-08-15 | — | 2026-08-20 |

Doğru kalıcı çözüm eşiği düşürmek değil **çelişkiyi hakem turunda kapatmak**:
round1'in ParafPara kaydı `alisveris_puani`ya taşınırsa iki taban aynı şeyi
ölçer ve eşik yeniden yükselir. Aynı iş `Bonus` tutarsızlığını da kapsıyor
(§4.4) — ikisi tek turda çözülebilir.

---

## 6. Kalan açıklar

| # | açık | neden bu turda kapanmadı |
|---|---|---|
| 1 | ikili mikro 0,570 (hedef ≥0,60) | Manşet ikili ölçütü `kampanya_kosullari` (fp 37 · fn 33 · tp 0) tavanlıyor. Alan TAM KÜME eşleşmesi istiyor; 5 skaler alan 1,000'e çıktığı hâlde manşet 0,60'a ulaşamıyor. Yapısal mikro (o alan hariç) **0,823**. |
| 2 | kalem mikro 0,629 (hedef ≥0,65) | §4.9: kalan kaybın ölçülebilir bir kısmı ölçüt eşiğinden geliyor (0,60 eşiğinde 0,659). Motor tarafında denenen 4 süzgecin hepsi ya ≤0,007 kazandırdı ya gerçek koşul öldürdü. |
| 3 | `hedef_kitle` 0,571 | `BACKLOG.md`: iki hipotez ölçülüp çürütüldü, alan açık-sınıf semantik yüklem istiyor → LLM kolu. |
| 4 | `tahsis_ucreti` ölçülemiyor | gold.v2'de 0 pozitif örnek. Çözüm kod değil, gold büyütmek (plan G3.1). |
| 5 | `Bonus` gold tutarsızlığı | Hakem turuna bağlı (§4.4). Çözülünce `odul_miktari` ve `alisveris_puani` birlikte 1,000'e çıkabilir. |
| 6 | Oran tablosu satır ayrıştırması 2 belgede yanlış | `T10F` marka adından vade 10, kolon kaymasından vade 3 (§3.4). Bugün zararsız (tablo yedek), ama tablo birincil yapılmak istenirse önce bu düzeltilmeli. |
| 7 | `eval/esikler-round1.json` kapısı KAPALI | §5.1. `kampanya_kosullari` satırı bu oturumdan ÖNCE de kapalıydı (`d9c0444`); bu oturum `odul_miktari` satırını ekledi ve sebebi gold-gold ParafPara çelişkisi. Eşik dosyası `eval/**` altında, bu oturumun sahipliğinde DEĞİL — güncelleme ana oturuma bırakıldı. |

---

## Sources

- `eval/reports/20260820-101434/report.md` — ÖNCE ölçümü
- `eval/reports/20260820-115842/report.md` — SONRA ölçümü
- `src/extraction/rules/extract.py` — `_IC_AYIRAC_RE`, `_islenmis_ornek`,
  `_oran_tablosu_c`, `_TUTAR_KOLON_RE`, `_ODUL_DISI_RE`, `_IADE_TRIGGER_RE`,
  `extract_all` blok başlıkları (gerekçeler ve ölçümler)
- `data/gold/ANNOTATION_GUIDE.md` §4 — `masraf_durumu` kapsam kuralı,
  `alisveris_puani` oran/adet ayrımı, `indirim_orani` puan/iade dışlaması
- `BACKLOG.md` — `vade_ay` ve `hedef_kitle` için çürütülmüş hipotezler
- `docs/rapor/yapilacaklar.md` §3.5 — `vade_ay` / `indirim_orani` ön teşhisi
- `tests/test_buyuk_harf_degismezligi.py`,
  `tests/test_skaler_alan_iyilestirmeleri.py` — davranış kapıları

## Related

- `docs/rapor/olcumler.md` — ölçüm metodolojisi
- `docs/rapor/kalem-duzeyi-olcut.md` — kalem düzeyi ölçütün tanımı
- `docs/rapor/yapilacaklar.md` — açık iş listesi
</content>
</invoke>
