# C ve D Denetimi — Round1 Ana Tur

> **Kapsam.** Yalnız `round1_main_C.csv` ve `round1_main_D.csv`. A ve B'nin
> κ hattı (`round1_A.csv` + `round1_B.csv`) bu raporun konusu değildir; yalnız
> §6'da bir çapraz bulgu not düşülmüştür.
>
> **Bu rapor CSV'ye yazmaz.** Gold hücresini model dolduramaz
> (`scripts/onarim_recetesi.py` modül başlığı). Aşağıdaki her düzeltme bir
> **öneri**dir; kararı anotatör verir.
>
> Tarih: 2026-08-15 · Ölçüm dosyası: `data/gold/gold.round1.json`
> (sha256 `bb14b158…f5ed538e`, yeniden üretildi ve birebir eşleşti)

---

## 0. Bir bakışta bilanço

| | C | D |
|---|---:|---:|
| Dağıtılan satır / belge | 573 / 90 | 572 / 90 |
| **Kendi dağıtımında karara bağlanan** | **33** (%5,8) | **180** (%31,5) |
| Karar verilen belge | 12 / 90 | 82 / 90 |
| Şema hatası yüzünden `build_gold`'un attığı karar | **12** (%36,4) | 3 (%1,7) |
| "Kampanya değil" diye elenen belgeyle kaybolan karar | 0 | 3 |
| **Gold'a ULAŞAN karar** | **21** | **174** |
| Gold'da sayılabilir hücre | 21 | 170 |
| Gold'a giren kayıt (yalnız bu anotatör) | 12 | 80 |
| `absent` (halüsinasyon kanıtı) | **0** | 23 |
| `unclear` | **0** | 9 |
| Zor-vaka hashtag'i | **0** | **0** |
| Gönderilen ama hiçbir dağıtıma oturmayan karar | **168** | 0 |

**Gold'a net katkı (§5):** C + D birlikte gold'un **92/158 kaydını (%58)** ve
**93/183 değer alanının (%51)** tek kaynağıdır. C ve D'nin belge kümeleri
birbirinden ve A/B'den **tamamen ayrıktır** (ölçüldü: `C ∩ D = 0`,
`C ∩ (A∪B) = 0`, `D ∩ (A∪B) = 0`) — yani bu 92 kayıt onlar olmadan gold'da
hiç yoktu.

**Ama bedava değil:** §3.1'de ölçülen **22 gold hücresi**, anotatörün
onaylamadığı bir değer taşıyor.

---

## 1. Yöntem — her sayı hangi komuttan çıktı

```bash
# Biçim denetimi (rapordaki HATA/UYARI sayıları)
.venv/bin/python -m scripts.lint_review_csv 'data/gold/review/round1_main_C.csv'
.venv/bin/python -m scripts.lint_review_csv 'data/gold/review/round1_main_D.csv'

# Onarım reçetesi — VARSAYILAN DOSYALARI round0'dır, açıkça vermek şart
.venv/bin/python -m scripts.onarim_recetesi --sadece-ozet \
    data/gold/review/round1_main_C.csv data/gold/review/round1_main_D.csv

# Gold'un yeniden üretimi (sha256 doğrulaması için, /tmp'ye)
.venv/bin/python -m scripts.build_gold \
    --pre data/gold/preannotations.v2.json --csv-dir data/gold/review \
    --out /tmp/gold_test.json --report /tmp/gold_test.md \
    --excluded-out /tmp/exc_test.json --allow-errors
```

### Ölçüm çıktıları

| Komut | C | D |
|---|---|---|
| `lint_review_csv` | **12 hata · 8 uyarı** | **3 hata · 1 uyarı** |
| `lint` — karar verilmemiş satır | 540/573 | 392/572 |
| `onarim_recetesi` (C+D birlikte) | 15 hata · 3 kalıp · **mekanik öneri 0** · insan kararı 15 | |
| `build_gold` — atılan satır | 12 | 3 |

> **`onarim_recetesi` uyarısı.** `--sadece-ozet` tek başına koşulursa
> `DEFAULT_FILES` (`scripts/onarim_recetesi.py:48`) devreye girer ve
> **round0 kalibrasyon** dosyalarını okur (64 hata / 10 kalıp / A:0 B:35 C:12
> D:17). Bu sayılar round1 ile ilgisizdir. Round1 dosyaları açıkça verildiğinde
> sonuç **15 hata / 3 kalıp / 0 mekanik öneri**tir.
>
> Ayrıca `_ANOTATOR_RE` (satır 53) yalnız `round0_kalibrasyon_([ABCD]).csv`
> kalıbıyla eşleşir; round1 dosyalarında anotatör kırılımı `A: 0 · B: 0 · C: 0 ·
> D: 0` diye **yanlış** basılır. Rapordaki C/D kırılımı bu yüzden elle,
> satır numarası üzerinden yapılmıştır.

---

## 2. Hata kalıpları

### K1 — Taksonomi dışı `campaign_type` · **8 hücre** (C 6 · D 2)

| Dosya:satır | Yazılan | Belge |
|---|---|---|
| C:33 | `Katılım hesabı` | `hayat-finans--hesaplar-avantajli-gunluk-hesap` |
| C:45 | `Eğitim finansmanı` | `hayat-finans--krediler-…-egitim-finansmani-sistemi` |
| C:49 | `Alışveriş finansmanı` | `kuveyt-turk--alisveris-finansmanlari-alisveris-finansmani` |
| C:57 | `Alışveriş finansmanı` | `kuveyt-turk--…-vivense-alisveris-finansmani` |
| C:62 | `Katılım hesabı` | `kuveyt-turk--hesaplar-katilma-hesaplari-2` |
| C:150 | `Katılım hesabı` | `turkiye-finans--ticari-katilma-hesaplari-…` |
| D:43 | `mevcut müşteri` | `hayat-finans--kampanyalar-hayatfinansla-islem-yaptikca-kazan` |
| D:84 | `Belirli Segment` | `kuveyt-turk--kampanya-arsivi-…-mil-kampanyasi` |

**Kök neden — iki ayrı şey.**
- **C (6 hücre):** `_bicim-karti.md` §3 vaka 8 eşlemesi uygulanmamış. Katılma /
  altın / yatırım hesabı → `Yatırım Ürünü`; kart formunda alışveriş finansmanı
  ve eğitim finansmanı → 8 sınıftan birine (`Finansman` / `İhtiyaç
  Finansmanı`). C ürünün **kendi adını** yazmış.
- **D (2 hücre):** `hedef_kitle` etiketi `campaign_type` sütununa yazılmış.
  Alan karışması (§K5 ile aynı kök).

**Çözüm.**
- C'nin 6 hücresi: §3-8 eşlemesi elle uygulanır. `Katılım hesabı` → `Yatırım
  Ürünü` (3 hücre); `Eğitim finansmanı` → `İhtiyaç Finansmanı`; `Alışveriş
  finansmanı` ×2 → `Finansman` (**önce §4.13/1 tek özne testi**: sayfa ürün
  listesi ise `absent`).
- D'nin 2 hücresi: `campaign_type` doğru sınıfla doldurulur, segment bilgisi
  aynı belgenin `hedef_kitle` satırına taşınır.
- **Araç tarafı:** `onarim_recetesi.TUR_ESLEME` (satır 65) yalnız 5 ifade
  tanıyor; `katılım hesabı`, `eğitim finansmanı`, `alışveriş finansmanı`
  yok. Bu üçü eklenirse 6 hücrenin 6'sı mekanik öneriye döner. **Bu bir kod
  değişikliğidir, bu raporda yapılmadı.**

> Not: eşleştirme **büyük/küçük harfe duyarsızdır**
> (`gold_schema.py:396-397`). D'nin `konut finansmanı` yazımı sessizce
> `Konut Finansmanı`ya çevrildi ve gold'a doğru girdi. Harf durumu hata
> değildir; **sözcük** hatadır.

---

### K2 — `verdict=fix` ama `gold_value` boş · **6 hücre (hepsi C)**

C:34 `finansman_tutari` · C:35 `odul_miktari` · C:64 `odul_miktari` ·
C:136 `finansman_tutari` · C:193 `finansman_tutari` · C:197 `finansman_tutari`

**Kök neden.** `fix` "değer yanlış" demektir; doğrusu yazılmadığında
`build_gold` o satırda durur (`build_gold.py:200`) — `--allow-errors` ile
koşulduğu için **satır sessizce atıldı**. Anotatör "modelin değeri yanlış"
bilgisini üretti ama düzeltmeyi yazmadı; bilgi tamamen kayboldu.

**Çözüm.** Üç seçenekten biri, hücre hücre: (a) doğru değeri yaz → `fix`
kalır; (b) metinde değer yoksa `absent` (ki bu bir **halüsinasyon kanıtıdır**,
gold'un en değerli etiketi — §3.3); (c) belirsizse `unclear`. Boş
bırakmak/`fix` bırakmak üçünden de kötüdür: bilgi ne ölçüme girer ne saklanır.

---

### K3 — `fix` yazılıp modelin değerinin **aynısı** girilmiş · **7 hücre (hepsi C)**

`kampanya_suresi` 4 · `vade_ay` 2 · `taksit_sayisi` 1 — lint'in 8 uyarısının
çekirdeği.

**Kök neden.** `_bicim-karti.md` §3 tuzak 1: doğru değeri `gold_value`'ya
tekrar yazmak. `fix` "bu değer yanlış" demektir; model haklıyken `fix`
yazmak **modeli haksız yere yanlış gösterir** ve precision'ı düşürür.

**Çözüm.** Yedisinde de `verdict` → `ok`, `gold_value` → boş. Ölçüme etkisi
tek yönlü ve bilinen yönde: bu 7 hücre bugün modelin aleyhine sayılıyor.

---

### K4 — `ok` satırına da `gold_value` yazmak · **C 3 · D 116 hücre**

D'nin **116 `ok` kararının 116'sında** `gold_value` doludur (modelin değeri
kopyalanmış). `build_gold` `verdict=ok` gördüğünde `gold_value`'yu **hiç
okumaz** (`build_gold.py:209-213`), doğrudan ön-anotasyondaki değeri alır.

**Kök neden.** Kart §3 tuzak 1'in ikinci yüzü. Tek başına zararsız görünür
ama **iki gerçek zararı** var:

1. **Sessizce yutulan çöp.** D:140
   (`turkiye-emlak-katilim--sozlesme-formlar-uye-syer-kullanici-sozlesmes-pdf`,
   `kampanya_suresi`) hücresinde `gold_value` = **`kampanya_suresi`** —
   sütun başlığının kendisi yapıştırılmış. Lint bunu görmez (çünkü `ok`
   satırında `gold_value` denetlenmiyor), `build_gold` atar. Aynı belgede
   `taksit_sayisi` hücresine `{"currency": "TRY", "value": 100000.0}` gibi
   **para tipli** bir değer kopyalanmış — satır kayması işareti.
2. **Denetim izini yok eder.** `ok` satırındaki `gold_value` bir karar değil,
   modelin o günkü çıktısının fotokopisidir. Model değeri sonradan
   değiştiğinde (K5) hangi değerin onaylandığını gösteren tek kayıt bu
   sütundur — ama `build_gold` ona bakmadığı için ölçüm onu kullanamaz.

**Çözüm.** Yeni turlarda `ok` satırında `gold_value` **boş** bırakılır.
Geçmişe dönük düzeltme gerekmez (gold değişmez), ama D:140 tipi hücreler
**satır kayması şüphesiyle** elden geçirilmelidir: `taksit_sayisi` hücresine
para değeri kopyalanan satırlar, komşu satırın kararının bu satıra yazılmış
olabileceğini gösterir.

---

### K5 — ⚠️ EN AĞIR: `ok`, anotatörün **görmediği** bir değeri gold'a yazdı · **22 hücre (C 1 · D 21)**

Bu bir biçim hatası değil; **ölçüm geçerliliği** sorunudur ve linter'ın
göremediği tek kalıptır.

`build_gold`, `verdict=ok` satırında değeri **CSV'nin `model_value`
sütunundan değil**, `preannotations.v2.json`'dan okur
(`build_gold.py:293-297`, `resolve_decision` → `model_value`). CSV'deki
`model_value` yalnız ekranda görünen kopyadır. İkisi ayrışmışsa anotatörün
onayladığı değer değil, **ön-anotasyonun bugünkü değeri** gold'a girer.

Ölçüm (C+D, `ok` satırları, JSON anahtar sırası normalize edilerek):

| Tip | C | D | Sonuç |
|---|---:|---:|---|
| CSV'de değer **boş**, ön-anotasyonda **dolu** | 0 | **6** | Anotatör "baktım, yok" (`ok`) dedi → gold'a **değer** girdi |
| CSV'de değer var, ön-anotasyondaki **farklı** | 1 | 15 | Anotatör X'i onayladı → gold'a **Y** girdi |
| **Toplam** | **1** | **21** | **22 hücre** |

#### Muhasebe kapanıyor — kalıp tesadüf değil

D'nin gold'a ulaşan 174 kararında `model_value`'su boş olan `ok` sayısı **6**;
K5'in "boş → değer" satırı da **6**. Yani D'nin *"kontrol ettim, bu alan
belgede yok"* anlamındaki `ok` kararlarının **hepsi** değere çevrildi.
Doğrulaması gold'un içinden geliyor: `gold.round1.json`'da yalnız-D
kayıtlarının `absent_fields` toplamı **21**'dir ve D'nin ulaşan `absent`
verdict sayısı da **21**'dir — aradaki 6 hücre eksik değil, **kayıp**.
(C'de aynı hesap tutarlı çıkıyor: 1 `ok`+boş → ön-anotasyon da boş →
`absent_fields` = 1.)

#### En zararlı 6 hücre — onaylanmış yokluk, değere çevrildi

| Belge | Alan | CSV'de | Gold'a giren |
|---|---|---|---|
| `kuveyt-turk--katilma-hesaplari-guvenceli-birikim-hesabi` | `kar_payi_orani` | (boş) | **50.0** |
| `kuveyt-turk--medium-genel-kredi-sozlesmesi-ucret-bilgi-…` | `kar_payi_orani` | (boş) | **5.0** |
| `turkiye-emlak-katilim--qr-bankacilik-hizmetleri-sozlesm…` | `kar_payi_orani` | (boş) | **50.0** |
| `turkiye-emlak-katilim--sozlesme-formlar-uye-syer-…-pdf` | `kar_payi_orani` | (boş) | **50.0** |
| `ziraat-katilim--2024-08-konut-20finansman-20s…` | `kar_payi_orani` | (boş) | **30.0** |
| `turkiye-emlak-katilim--sozlesme-formlar-uye-syer-…-pdf` | `kampanya_suresi` | (boş) | **2007-03-10** |

Beş `kar_payi_orani` hücresinin `source_span`'ı ön-anotasyonda okunabiliyor ve
hepsi **aynı terminoloji tuzağı**: *"kâr payının %50'sini alabilirsiniz"*,
*"yıllık bileşik kâr payı oranının yüzde 5'i"*. Bunlar finansman kâr payı
oranı **değil**, kâr paylaşım / ceza oranıdır — kılavuz §4.13/6 ve
`_bicim-karti.md` §3 vaka 7 bunlara açıkça `absent` + `#terminoloji` diyor.
Yani D **doğru** karar verdi (`ok` = "bu alan yok"), gold **yanlış** kaydetti.
`2007-03-10` de bir kampanya bitişi değil, sözleşme metnindeki bir tarihtir.

#### Kalan 16 hücre — tarih kayması

15'i `kampanya_suresi`, 1'i `taksit_sayisi`. Örnekler: CSV `2026-07-31` →
gold `2026-07-01`; CSV `2025-12-31` → gold `2025-07-10`; CSV `2026-12-31` →
gold `2025-06-15`; CSV `taksit_sayisi=3` → gold `26`. Kalıp tanıdık:
**bitiş tarihi yerine başlangıç tarihi** (`_bicim-karti.md` §2 uyarısı:
aralık biçimi "sessizce yanlış ucu alır").

**Kök neden.** CSV'ler ön-anotasyon tazelenmeden **önceki** çıkarıcıyı
gösteriyor; `build_gold` tazelenmiş dosyayı okuyor. Bu risk projede zaten
biliniyor ve yazılı: `_atama.md` "Korunan dosyada YENİDEN bakılacak satırlar"
bölümü aynı mekanizmayı `round0_kalibrasyon_A.csv` için 1 satırda tespit edip
listelemiş. **Aynı denetim round1 paketlerine uygulanmamış.**

**Çözüm (öncelik sırasıyla):**
1. **Bu 22 hücre yeniden karara bağlanır.** Anotatöre güncel `model_value` ile
   gösterilir. Özellikle 5 `kar_payi_orani` hücresi: bugünkü gold değerleri
   büyük olasılıkla **yanlış** ve `absent` olmalı — bu, gold'un halüsinasyon
   ölçümünü doğrudan etkiler.
2. **Kalıcı kapı:** `lint_review_csv`'ye "CSV'deki `model_value`,
   ön-anotasyondaki değerden farklı" denetimi eklenir. Bugün bu kalıbı **hiçbir
   araç görmüyor**; 22 hücrenin tamamı lint'ten temiz geçti.
3. Tazeleme sonrası `_atama.md`'deki "yeniden bakılacak satırlar" listesi
   **her** round paketi için üretilir, yalnız korunan dosya için değil.

---

### K6 — Yanlış alana yazılmış değer (satır/sütun karışması) · **3 hücre (D)**

- D:22 `vade_ay` ← `{"has_fee": false,"amount": 0}` (bir `masraf_durumu`
  değeri). Ayrıştırıcı içinden `0` okudu ve "pozitif tamsayı olmalı, 0 geldi"
  diye durdu. **Şanslı bir yakalama:** değer `{"has_fee": true, "amount": 36}`
  olsaydı `36` sessizce `vade_ay`a girebilirdi.
- D:43 `campaign_type` ← `mevcut müşteri` (bir `hedef_kitle` etiketi).
- D:84 `campaign_type` ← `Belirli Segment` (aynı).

**Kök neden.** Elektronik tabloda blok kopyalama; hedef sütun/satır kayması.
K4'teki `taksit_sayisi` ← para değeri örneği aynı ailedendir.

**Çözüm.** Üç hücre doğru alanlarına taşınır. Kalıcı önlem: `ok` satırlarında
`gold_value` boş bırakılırsa (K4) blok kopyalama alışkanlığı kendiliğinden
biter.

---

### K7 — C'de `absent` ve `unclear` hiç yok · **0 / 33**

| | A | B | C | D |
|---|---:|---:|---:|---:|
| Karar | 146 | 150 | **33** | 180 |
| `absent` | 23 | 37 | **0** | 23 |
| `unclear` | 2 | 1 | **0** | 9 |

**Neden önemli.** `absent`, model bir değer ürettiğinde yazıldığında
**onaylanmış halüsinasyondur** ve kılavuzun deyişiyle "gold setteki en değerli
tek etiket"tir (§3.3); halüsinasyon oranı birebir ondan hesaplanır.
C'nin 33 kararı bu ölçüme **sıfır** katkı yapar. C'nin arşivlenen 168
kararında da yalnız **2** `Absent` var (%1,2) — A/B/D'de bu oran %13–25
bandında.

**Çözüm.** C'nin bir sonraki turu, kılavuz §3.3 kutusu ve §9 madde 3
okunarak açılmalı. Bu bir biçim eğitimi değil, **hangi etiketin ne ölçtüğü**
eğitimidir.

---

### K8 — Zor-vaka hashtag'i hiç yok · **C 0 / 33 · D 0 / 180**

A 3 (`#kampanya_disi`), B 8 (`#kampanya_disi`, `#terminoloji`,
`#kosullu_aralik`) hashtag yazmış; C ve D **hiç** yazmamış. `note` sütunu boş
değil (C 12/33, D 56/180 satırda not var) — yani yazmaktan kaçınmamışlar,
**etiket sistemini kullanmamışlar**.

**Neden önemli.** Bu etiketler ablasyon tablosunda hibridin nerede kazandığını
gösteren tek kırılımdır (CLAUDE.md §6, kılavuz §6) — "jüriye sunulacak en
ikna edici artefakt". `gold_report_round1.md`'deki zor-vaka tablosu bugün
toplam **6 kayıt** gösteriyor (`kosullu_aralik` 3, `celiskili` 2,
`terminoloji` 1) ve **hiçbiri C/D'den gelmiyor** — oysa gold kayıtlarının
%58'i onlardan.

**Çözüm.** Hashtag'ler zorunlu değil ama ölçülebilir olmalı: gelecek turda
`note` yazılan her satırda hashtag beklenir, `lint`'e UYARI seviyesinde
"not var, etiket yok" denetimi eklenebilir. Geçmişe dönük: C/D'nin notlu
68 satırı (12 + 56) taranıp etiketlenirse zor-vaka alt kümesi 6'dan anlamlı
bir sayıya çıkar.

---

### K9 — Büyük harfli `verdict` (`Fix` / `Ok`) · **C 33 / 33**

C'nin taşınan 33 kararının **tamamı** büyük harflidir; D'nin 180'inin
tamamı küçük.

**Etki: yok.** Hem `lint_review_csv.py:192` hem `build_gold.py:172`
`casefold()` uyguluyor. Ölçülerek doğrulandı: 33 kararın 21'i gold'a girdi,
12'si K1/K2 yüzünden düştü — harf durumu hiçbirinde rol oynamadı.

**Çözüm.** Kozmetik; düzeltilmesi gerekmez. Raporda yer alması, "C dosyasının
sorunları" listesinden **bu maddenin çıkarılması** içindir — gerçek sorunlar
K1, K2 ve §3'tür.

---

## 3. C dosyasının kök nedeni — yanlış havuzdan üretilmiş CSV

Denetimin tek en önemli teşhisi budur ve **ölçüldü**:

| Ölçüm | Sonuç |
|---|---:|
| C'nin dokunduğu benzersiz belge | **86** |
| Bunlardan `preannotations.json` (243 belgelik **v1 havuzu**) içinde olan | **86 / 86 (%100)** |
| Bunlardan `preannotations.v2.json` (250 belgelik havuz, round1 CSV'lerinin kaynağı) içinde olan | 34 / 86 (%40) |
| **Yalnız v1 havuzunda olan (v2'de YOK)** | **52** |
| C'nin gerçek ataması `round1_main_C.csv` (90 belge) ile örtüşme | **12 / 90** |

**Teşhis.** C, kendisine dağıtılan `round1_main_C.csv` dosyasını değil,
**`preannotations.json`'dan üretilmiş eski nesil bir inceleme CSV'sini**
doldurmuştur. 12 belgelik örtüşme rastlantıdır (iki havuzda birden bulunan
belgeler). Bu bir yargı hatası değil, **dosya sürümü karışıklığıdır**;
bedeli 201 kararın 168'inin sahipsiz kalmasıdır.

Yan kanıt: 46 belgenin `belgeler/<doc_id>.txt` metinlerinin **46'sı da**
mevcut — yani C'ye gerçekten dağıtılmış bir paketti, uydurulmuş doc_id
değil.

**Çözüm (süreç).** Dağıtım paketlerine, üretildikleri ön-anotasyon dosyasının
adı ve sha256'sı bir sütun ya da başlık satırı olarak gömülmeli; `lint`
CSV'nin `doc_id` kümesini bildirilen ön-anotasyonla karşılaştırıp
uyuşmuyorsa **HATA** vermeli. `_atama-round1-v2.md`'de bu risk zaten yazılı
("`--pre` **mutlaka** … olmalı, yoksa belgelerin çoğu 'bilinmeyen doc_id' diye
sessizce atlanır") — kural var, **kapı yok**.

---

## 4. `_round1_C_tasinamayan.csv` — 168 kararın kaderi

168 karar (75 belge · `Fix` 91 · `Ok` 75 · `Absent` 2), hedef dosyada
karşılığı olup olmadığına göre altı gruba ayrıldı. Her satır
`(doc_id, field)` çifti üzerinden ölçüldü.

| # | Grup | Karar | Verdict | Değerlendirme |
|---|---|---:|---|---|
| **A** | `round2_zor_vaka.csv` — hedef hücrelerin **29/29'u boş** | **29** | Fix 18 · Ok 11 | ✅ **Taşınabilir** |
| B | `round1_main_D.csv` — hedef hücre boş | 2 | Ok 2 | ⚠️ Köken riski |
| C | `round1_main_D.csv` — hedef hücre **D tarafından dolu** | 19 | Fix 10 · Ok 9 | ❌ Üzerine yazılamaz |
| D | `round1_v2_*.csv` (protokol-v2 κ turu) | 5 | Fix 4 · Ok 1 | ❌ Yasak |
| E | `round1_A.csv` / `round1_B.csv` (κ turu) | 13 | Fix 6 · Ok 7 | ❌ Yasak |
| F | **Hiçbir dağıtımda karşılığı yok** | **100** | Fix 53 · Ok 45 · Absent 2 | ⚠️ Yeni CSV gerekir |
| | **Toplam** | **168** | | |

### A — 29 karar `round2_zor_vaka.csv`'ye taşınabilir ✅

**Ölçüldü:** `round2_zor_vaka.csv` 949 satır / 73 belge ve **tamamen boştur
(0 karar)**. `_atama.md:106`: *"tek anotatörlüdür — κ üretmez, zor-vaka
kapsamını büyütür"* — ve **atama tablosunda hiç kimseye verilmemiştir**.
Yani κ riski yok, çakışma yok, sahip yok.

- 29 kararın **29'unda da** hedef hücre boş; hiçbir şeyin üzerine yazılmaz.
- Taşıma `build_gold`'a `round2_zor_vaka.csv`'yi C'nin kararlarıyla sokar;
  `infer_annotator` dosya adından anotatör türettiği için köken etiketi
  **yanlış olmaz ama belirsizleşir** — dosya "tek anotatörlü" sayılıyor,
  o tek anotatörün C olduğu ayrıca yazılmalıdır.

**Kalan risk (§3/K5 ile aynı):** 11 `Ok` kararı, C'nin **v1 havuzunda**
gördüğü model değerini onaylar; `build_gold` `zor_vaka` için
`preannotations.zor.json`daki güncel değeri yazar. İkisi ayrışmışsa gold'a
C'nin görmediği değer girer. **Bu yüzden önce 18 `Fix` taşınmalıdır** —
`Fix` kararları açık değer taşır, ön-anotasyondan bağımsızdır. 11 `Ok`
ancak model değerinin değişmediği hücre hücre doğrulandıktan sonra
taşınmalıdır.

### B — 2 karar `round1_main_D.csv`'nin boş hücrelerine ⚠️

Teknik olarak mümkün ama **köken (provenance) bozar**: `build_gold`
anotatörü **dosya adından** türetir (`infer_annotator`), yani C'nin kararı
gold'a **D imzasıyla** girer. 2 karar için bu bedel ödenmeye değmez.
**Öneri: taşıma.**

### C — 19 karar D'nin dolu hücrelerine ❌ ama çöp değil

Üzerine yazılamaz. Ama bunlar **aynı hücrede ikinci bir bağımsız yargıdır**
ve iki işe yarar:
1. **Hakemlik kuyruğu:** C ile D'nin ayrıştığı hücreler
   `data/gold/review/_hakem_vakalari.jsonl` hattına beslenebilir.
2. **Küçük bir κ örneklemi:** 19 hücre / 10 belge, C–D arasında protokol-v2
   altında ölçülebilecek tek örtüşmedir. İstatistiksel güç düşüktür
   (bir κ raporlamak için yetersiz), ama uyuşma oranı bir **sağlık göstergesi**
   olarak yazılabilir. **Bu raporda hesaplanmadı** — C'nin kararları v1
   havuzundan geldiği için iki tarafın gördüğü model değeri aynı olmayabilir;
   önce §3/K5 denetiminden geçmeleri gerekir.

### D + E — 18 karar κ hatlarına ❌ YASAK

`round1_A/B` Cohen κ'nın tek kaynağıdır; `round1_v2_*` protokol-v2 altındaki
ilk κ ölçümüdür (`_atama-round1-v2.md`: *"Birbirinizle konuşmadan doldurun"*).
Üçüncü bir kişinin kararını bu dosyalara koymak κ'nın ölçtüğü şeyi
(bağımsız yargıların örtüşmesi) yok eder. **Bu 18 karar arşivde kalır.**

### F — 100 karar (46 belge) hiçbir dağıtımda yok ⚠️

98'inin `doc_id`'si **hiçbir** inceleme CSV'sinde geçmiyor; 2'sinin belgesi
var ama o alan hiç örneklenmemiş. Kökeni §3'te: bu belgeler yalnız
`preannotations.json` havuzunda.

**Kurtarılabilir mi? Evet, ama bedelli.** İzlek:

1. `scripts.to_review_csv` ile **yalnız o 46 belge için** yeni bir inceleme
   CSV'si üretilir (`--pre data/gold/preannotations.json`).
2. Arşivdeki 100 karar `(doc_id, field)` üzerinden bu CSV'ye enjekte edilir.
   Arşiv `verdict` ve `gold_value` taşıdığı için bilgi tamdır.
3. `build_gold` **ikinci bir geçişle** `--pre data/gold/preannotations.json`
   ile koşulur ve çıktı mevcut gold'la birleştirilir
   (`scripts/merge_gold_v2.py` hattı bunun için var).

**Bedel ve riskler:**
- **İki ön-anotasyon havuzu karışır.** Mevcut `gold.round1.json` v2 havuzuyla
  üretildi; bu 46 belge v1 havuzundan gelir. Aynı belgenin iki havuzdaki
  model değeri farklıysa precision iki farklı temele oturur. Protokol
  künyesine (kılavuz §11) **üçüncü bir satır** eklemek gerekir.
- **45 `Ok` kararı en riskli kısım** (§3/K5): v1 havuzunun o günkü değerini
  onaylıyorlar. 53 `Fix` + 2 `Absent` = **55 karar açık değer/karar taşır ve
  havuzdan bağımsızdır** — kurtarmanın güvenli çekirdeği budur.
- İş yükü: bir CSV üretimi + bir enjeksiyon betiği + bir birleştirme geçişi.

### Bilanço — C'nin kurtarılabilir karar sayısı

| Kategori | Karar |
|---|---:|
| Zaten gold'da (taşınan 33'ün ulaşanı) | **21** |
| **Düşük riskle kurtarılabilir** — A grubu `Fix` (18) + F grubu `Fix`/`Absent` (55) | **73** |
| Doğrulama sonrası kurtarılabilir — A grubu `Ok` (11) + F grubu `Ok` (45) + B (2) | 58 |
| Kurtarılamaz (κ yasağı D+E) | 18 |
| Kurtarılamaz ama hakemliğe yarar (C grubu) | 19 |
| **C'nin 201 kararından ölçüme dönüşebilecek üst sınır** | **21 + 73 + 58 = 152** |
| **Bugünkü gerçekleşen** | **21 (%10,4)** |

---

## 5. `build_gold` bilançosu — kim ne kazandırdı, ne kayboldu

`data/gold/gold_report_round1.md` + `data/gold/excluded.round1.json` okundu ve
`build_gold` yeniden koşularak doğrulandı (sha256 birebir aynı).
`build_gold`'un **`--allow-errors` ile** koşulduğu ölçülerek saptandı:
52 hatalı satır atıldı, dosya yine de yazıldı.

### Atılan satırların dosya kırılımı (52 satır)

| Dosya | Atılan |
|---|---:|
| `round0_kalibrasyon_B.csv` | 19 |
| **`round1_main_C.csv`** | **12** |
| `round0_kalibrasyon_C.csv` | 9 |
| `round0_kalibrasyon_D.csv` | 5 |
| `round1_A.csv` | 2 |
| `round1_B.csv` | 2 |
| **`round1_main_D.csv`** | **3** |

### C ve D'nin gold'a katkısı

| | C | D |
|---|---:|---:|
| Karar | 33 | 180 |
| − şema hatası (K1, K2, K6) | −12 | −3 |
| − "kampanya değil" elenen belge | 0 | −3 |
| **= gold'a ulaşan** | **21** | **174** |
| → değer alanı (`fields`) | 15 | 78 |
| → `absent_fields` | 1 | 21 |
| → `unclear_fields` | 0 | 5 |
| → `campaign_type` (dolu) | 5 | 66 |
| → `campaign_type` `unclear` (hücre üretmez) | 0 | 4 |
| **Gold kaydı (yalnız bu anotatör)** | **12** | **80** |

**Elenen belgeler.** 6 belgenin 2'si D'den (`campaign_type=absent`,
kılavuz §4.13/1 tek özne testi): `kuveyt-turk--medium-temel-bankacilik-…-pdf`
ve `kuveyt-turk--musteri-ol-kampanyalari-mobilden-…`. Bu bir **kayıp değil,
doğru karardır** — 3 karar gold'a girmedi ama belge zaten kampanya değil.
Kalan 4 belge A/B'den gelir.

### Veri seti büyütme açısından net bilanço

**Kazanç.**
- Gold'un **92/158 kaydı (%58)** yalnız C ve D sayesinde var.
- **93/183 değer alanı (%51)** onlardan geliyor.
- 22 `absent_fields` etiketi (C 1 · D 21) — halüsinasyon ölçümünün yeni
  yakıtı. Olması gereken 28'di; 6'sı K5 yüzünden değere çevrildi.
- Belge kümeleri ayrık olduğu için katkı **tamamen katkısaldır**; hiçbiri
  A/B'nin ölçtüğü şeyi tekrarlamıyor.

**Kayıp.**

| Kayıp | Karar | Neden | Geri alınabilir mi |
|---|---:|---|---|
| C'nin dağıtım dışı kararları | **168** | Yanlış havuzdan CSV (§3) | 73 düşük riskle, 58 doğrulamayla (§4) |
| C — şema hatası | 12 | K1 (6) + K2 (6) | Evet, elle düzeltme |
| D — şema hatası | 3 | K1 (2) + K6 (1) | Evet, elle düzeltme |
| D — elenen belge | 3 | Doğru karar | Gerek yok |
| **Gold'a yanlış değer giren hücre** | **22** | K5 — çapa/tazeleme kayması | Yeniden karara bağlanmalı |
| Karara hiç bağlanmayan satır | C 540 · D 392 | Tur tamamlanmadı | Anotasyon süresi |

**Tek cümlelik özet:** D turu **teknik olarak temiz** (180 kararın 174'ü
gold'a ulaştı, %96,7) ama **kapsamı yarım** (90 belgenin 82'sine dokunuldu,
572 satırın 392'si boş) ve 21 hücresi K5 yüzünden yanlış değer taşıyor.
C turu **teknik olarak da kapsam olarak da başarısız**: 201 kararın 21'i
(%10,4) ölçüme dönüştü, sebebi yargı değil **dosya sürümü karışıklığı**.

---

## 6. Kapsam dışı ama bildirilmesi gereken çapraz bulgu

§3/K5'teki kalıp **A ve B'de de var** (aynı yöntemle ölçüldü):

| Dosya | `ok` kararı | CSV boş → gold'a değer | CSV değer → gold'da farklı |
|---|---:|---:|---:|
| `round1_A.csv` | 113 | 5 | 13 |
| `round1_B.csv` | 81 | 5 | 14 |
| `round1_main_C.csv` | 8 | 0 | 1 |
| `round1_main_D.csv` | 116 | 6 | 15 |

A ve B **κ hattıdır ve bu raporun kapsamı dışındadır** — sayılar buraya
yalnızca kalıbın sistemik olduğunu göstermek için konmuştur. κ tarafını
yürüten ekibe iletilmesi gerekir: 37 hücre (A 18 + B 19) aynı riski taşıyor
ve κ hesabı `report_iaa` üzerinden yürüdüğü için etkisi ayrıca ölçülmelidir.

---

## 7. Belirsiz kalanlar — bu raporda **ölçülmedi**

Aşağıdakiler açıkça işaretlenmiştir; sayı uydurulmamıştır.

1. **C'nin orijinal gönderdiği dosya repoda yok.** Yalnız
   `_round1_C_tasinamayan.csv` (doc_id, field, gold_value, verdict, note)
   arşivi var; `model_value` ve `snippet` sütunları yok. Bu yüzden **168
   kararın hiçbirinde** "C'nin gördüğü model değeri bugünküyle aynı mı"
   sorusu **cevaplanamadı**. §4'teki "doğrulama sonrası kurtarılabilir" 58
   kararın gerçek kurtarılabilirlik oranı bu yüzden **belirsizdir**.
2. **C–D uyum oranı (§4/C grubu, 19 hücre) hesaplanmadı.** Ön koşul (1)
   sağlanmadığı için anlamlı olmazdı.
3. **`round2_zor_vaka.csv`'ye taşınacak 11 `Ok` kararının riski
   nicelenemedi.** `preannotations.zor.json` ile C'nin gördüğü v1 havuzu
   değerleri karşılaştırılmadı — C'nin orijinal dosyası olmadan yapılamaz.
4. **K5'teki 22 hücrenin kaçının gold'da gerçekten yanlış olduğu
   belirsizdir.** 5 `kar_payi_orani` hücresi için `source_span` okunarak
   güçlü bir gerekçe kuruldu (kâr paylaşım oranı, §4.13/6), ama belge tam
   metinleri satır satır okunmadı. **Karar anotatörün.**
5. **K4'teki "satır kayması şüphesi"** (D:140 ve para değeri taşıyan
   `taksit_sayisi` hücresi) iki örnekle sınırlıdır; D'nin 116 `ok` satırının
   tamamı bu açıdan taranmadı.

---

## Kaynaklar

- `data/gold/ANNOTATION_GUIDE.md` §3.1 (boş hücre = karar verilmedi), §3.3
  (`absent` kutusu), §4 (`campaign_type` yok — bkz. biçim kartı), §4.13/1
  (tek özne testi), §4.13/6 (`N/M` paylaşım oranı), §6 (hashtag'ler),
  §9 (sık hatalar), §11 (protokol künyesi)
- `data/gold/review/_bicim-karti.md` §1 (dört cümlelik karar kuralı, üç tuzak),
  §2 (kanonik biçimler, 8 tür), §3 vaka 7 ve 8
- `data/gold/review/_atama.md` (dağıtım tablosu, `round2_zor_vaka` sahipsiz,
  "yeniden bakılacak satırlar")
- `data/gold/review/_atama-round1-v2.md` (`round1_v2_*` κ turu, `--pre`
  uyarısı)
- `data/gold/gold_report_round1.md`, `data/gold/excluded.round1.json`
- `scripts/build_gold.py:172-213` (verdict çözümü), `:293-297` (model değeri
  ön-anotasyondan okunur), `:628-648` (`--allow-errors`)
- `scripts/lint_review_csv.py:192-237`
- `scripts/onarim_recetesi.py:48` (`DEFAULT_FILES`), `:53` (`_ANOTATOR_RE`),
  `:65` (`TUR_ESLEME`), modül başlığı (CSV'ye yazma yasağı)
- `scripts/gold_schema.py:396-397` (tür eşleşmesi harf durumuna duyarsız)
