# Çerçeve (boilerplate) ayıklaması — yarışma korpusunda kapsam kararı

**Tarih:** 2026-08-07 · **Korpus:** `data/raw`, 1761 belge, 8.325.907 karakter
**Araç:** `scripts/boilerplate_audit.py` (yalnız okur, hiçbir şey yazmaz)
**Mekanizma:** `scripts/split_trainable.py` — 8-gram shingling, `BOILERPLATE_MIN_DOCS=3`,
`SIGNAL_MIN_FRACTION=0.25`
**İlgili:** aksiyon planı Faz 0.2 · envanter T-019 (chatbot alakasız içerik döndürüyor)

---

## 0. KARAR (özet)

> **Çerçeve ayıklaması `data/raw` korpusuna YALNIZ `products` bölümünde,
> `banka` gruplamasıyla ve noktalama sinyali KAPALI uygulanmalıdır.**
> `live`, `docs`, `archive` bölümlerine UYGULANMAMALIDIR.

Gerekçe tek satırda: gold'da bu kapsam mikro-F1'i **0,612 → 0,688** çıkarıyor
ve halüsinasyon oranını **0,102 → 0,066** düşürüyor; korpusun tamamına
uygulandığında ise aynı mekanizma mikro-F1'i **0,532**'ye düşürüyor. Fark
bölümden geliyor, eşikten değil.

| kapsam (gruplama / noktalama / bölüm) | mikro-F1 | makro-F1 | çıkarım hatası | halüsinasyon |
|---|---|---|---|---|
| **TABAN — temizlik yok** | 0,612 | 0,560 | 0,369 | 0,102 |
| **banka / kapalı / yalnız `products`** ✅ | **0,688** | **0,624** | **0,338** | **0,066** |
| banka-bolum-konak / kapalı / `products` | 0,677 | 0,614 | 0,338 | — |
| banka-bolum-yol / kapalı / `products` | 0,672 | 0,612 | 0,338 | — |
| banka / geniş / `products` | 0,667 | 0,606 | 0,338 | — |
| banka-bolum / kapalı / `products` | 0,646 | 0,587 | 0,369 | 0,078 |
| banka / geniş / tüm bölümler | 0,620 | 0,590 | 0,385 | — |
| banka-bolum / geniş / tüm bölümler | 0,589 | 0,562 | 0,415 | 0,090 |
| banka / kapalı / tüm bölümler | 0,562 | 0,563 | 0,477 | — |
| banka / kapalı / yalnız `live` | 0,558 | 0,561 | 0,446 | — |
| banka-bolum / kapalı / yalnız `live` | 0,538 | 0,531 | 0,462 | — |
| banka-bolum / kapalı / tüm bölümler | 0,532 | 0,524 | 0,492 | 0,078 |

`python -m eval.run_eval --gold <varyant> --config kural --matcher strict --no-write`
(20 belge, `matcher=both` koşuldu; strict ve tolerant bu gold'da aynı sonucu
veriyor).

**Uyarı — istatistiksel güç:** gold 20 belge. Kazanan yapılandırmanın
%95 GA'sı **0,688 [0,527–0,792]**, tabanınki **0,612 [0,483–0,716]** ve
aralıklar ÖRTÜŞÜYOR. Yön tutarlı (12 yapılandırmanın hepsinde `products`
kazanıyor, `live` kaybediyor) ama fark gold büyütülene kadar "kanıtlanmış"
değil, "ölçülmüş" sayılmalıdır.

---

## 1. Teşhis — içeriğinin %75'inden fazlasını yitiren 143 belge

Ölçüt: finansal sinyal taşıyan (`has_financial_signal`) ve çekirdeği ham
metnin %25'inin altına düşen belgeler. `banka-bolum` / kapalı yapılandırmasında
**143 belge** (kullanıcının ölçümü birebir doğrulandı; banka dağılımı da:
dunya-katilim 77, bölüm dağılımı live 86 / products 46 / docs 11).

143'ün tamamı 13 (banka, bölüm) kovasına düşüyor. Her kovadan 2 belge **elle
okundu** (24 belge; atılan en uzun sürekli blok + kalan çekirdek yan yana):

| kova | belge | atılan içerik | karar |
|---|---|---|---|
| dunya-katilim/live | 46 | çerez + KVKK aydınlatma metni (9 KB sayfanın 8,7 KB'ı) | ✅ meşru |
| dunya-katilim/products | 31 | aynı çerez/KVKK bloğu | ✅ meşru |
| turkiye-finans/live | 13 | blog başlık listesi + mega menü | ✅ meşru |
| turkiye-finans/products | 13 | mega menü ("POS Hizmetleri … Engelsiz Bankacılık") | ✅ meşru |
| hayat-finans/live | 2 | çerez bandı + erişilebilirlik menüsü | ✅ meşru |
| ziraat-katilim/live | 2 | yatırımcı ilişkileri footer'ı | ✅ meşru |
| kuveyt-turk/products | 2 | "Sıkça Sorulan Sorular" başlık bloğu | ✅ meşru |
| **turkiye-emlak-katilim/live** | **12** | **gerçek kampanya koşulu cümleleri** | ❌ zararlı |
| **albaraka/live** | **8** | **gerçek kampanya koşulu cümleleri** | ❌ zararlı |
| **albaraka/docs** | **6** | **sözleşme maddeleri; kalan = sayfa numarası döküntüsü** | ❌ zararlı |
| **kuveyt-turk/docs** | **5** | **PDF tarife metni; kalan = OCR döküntüsü** | ❌ zararlı |
| **vakif-katilim/live** | **2** | **kampanya koşulu cümleleri (kısmi)** | ❌ zararlı |
| **kuveyt-turk/live** | **1** | **kampanya katılım koşulu** | ❌ zararlı |

**Sonuç: 109 meşru (%76) / 34 zararlı (%24).**

### 1.1 dunya-katilim neden 77 belge?

Çünkü Dünya Katılım'ın HER sayfası, gövdenin hemen ardına ~8,7 KB'lık bir
çerez + KVKK aydınlatma metni gömüyor. Örnek
(`dunya-katilim--finansmanlar-nakdi-finansman`, 9070 karakter):

- **Kalan çekirdek (328 kr):** "Anasayfa … Finansmanlar Nakdi Finansman
  Taksitli Ticari Finansman Arsa, araç, iş yeri, makine teçhizat, ekipman
  ihtiyaçlarınızı Taksitli Ticari Finansman ile rahatça karşılayabilirsiniz…"
- **Atılan 8742 kr:** "Tüm site ziyaretçilerimizi daha iyi tanımak… Çerez
  Politikası… ÇEREZ KULLANIMINA İLİŞKİN AYDINLATMA METNİ 1. Giriş Bu metin,
  6698 sayılı Kişisel Verilerin Korunması Kanunu'nun…"

Yani **77 belgenin 77'sinde düşüş mekanizmanın başarısıdır.** Bankanın
çerçeve oranı %86,8 ile korpusun en yükseği ve bu doğru sayıdır. Bu
belgelerden ayıklama olmadan çıkan alanlar HALÜSİNASYONDUR:

- `vade_ay = "1 yıl"` ← "…toplamak amacıyla kullanılan çerezdir. **1 yıl**"
  (çerez saklama süresi) — 91 belgede ölçüldü.
- `masraf_durumu = "ücretsiz"` ← "…en geç otuz (30) gün içinde **ücretsiz**
  olarak sonuçlandırılmaktadır" (KVKK başvuru metni) — 91 belgede ölçüldü.

### 1.2 Sözleşme şablonları — kullanıcının teşhisi doğrulandı

`albaraka/docs` (6 belge, 108-110 KB) ve `kuveyt-turk/docs` (5 belge):
**tekrar burada gürültü değil, içeriğin kendisi.** Albaraka'nın altı
sözleşmesi aynı hukuki gövdeyi paylaştığı için gövde çerçeve sayılıyor ve
geriye yalnız sayfa numaraları kalıyor:

```
KALAN: "50 1 / 50  50 2 / 50  50 3 / 50 … olduğu kredi/finansman
        taksitleri içerisinde yer alan Albaraka Türk Katılım Bankası A.Ş
        50 11 / 50"
ATILAN: "…Aracı bilgi güvenliği farkındalık eğitimlerini aşağıdaki
         yöntemlerden günün şartlarına uygun olan biri kanalıyla…"
```

`docs` bölümünde ayıklamanın **11/11 belgesi zararlı** ve bölümün "%37
çerçeve" sayısı yanıltıcı: atılan şey site kromu değil, sözleşme şablonudur.

### 1.3 Otomatik kayıp taraması ve ölçülmüş hata payı

`boilerplate_audit.py` her kaybolan alanı kaynak konumuna bakarak sınıflıyor
(krom / menü / başlık-listesi / çapraz-kampanya / gerçek). Referans
yapılandırmada (banka / kapalı):

| alan | krom | menü | başlık listesi | çapraz | gerçek |
|---|---|---|---|---|---|
| masraf_durumu | 0 | 5 | 0 | 0 | 269 |
| kampanya_suresi | 34 | 6 | 0 | 0 | 172 |
| kampanya_kosullari | 1 | 10 | 37 | 14 | 161 |
| vade_ay | 91 | 0 | 0 | 0 | 22 |
| hedef_kitle | 6 | 25 | 52 | 13 | 16 |
| indirim_orani | 58 | 0 | 0 | 0 | 0 |
| taksit_sayisi / finansman_tutari / kar_payi_orani / odul_miktari | 0 | 0 | 0 | 0 | 17 |

**Bu tablonun "gerçek" sütunu ÜST SINIRDIR, gerçek zarar değildir.** Ölçüldü:
"gerçek" sayılan 620 kaybın **173'ü (%28)** aslında bir krom işaretçisinden
1000 karakter içinde duruyor — sınıflandırıcının ±180 karakterlik penceresi
KVKK bloğunun ortasına düşen alanları göremiyor (`masraf_durumu`'nun 269'unun
büyük kısmı bu). Pencere körlemesine genişletilmedi, çünkü işaretçi konumu iki
tepeli: belgelerin %25'inde ilk işaretçi metnin %3'ünde (çerez bandı başta),
%25'inde %95'inde (footer bağlantısı). Sabit yarıçap ikisini birden doğru
kesemiyor.

Bu yüzden tablo **yapılandırmaları KARŞILAŞTIRMAK** için kullanıldı (aynı yanlılık
her yapılandırmada aynı), **karar** ise gold'a bağlandı.

---

## 2. Gruplama stratejisi — ölçülmüş karşılaştırma

Korpus geneli (`data/raw`, 1761 belge). "Zararlı" sütunu §1.3'teki üst sınır.

| gruplama | noktalama | grup | çerçeve | düşen belge | zararlı kayıplı belge | krom sızıntısı |
|---|---|---|---|---|---|---|
| banka | kapalı | 10 | **43,9%** | 159 | 539 | **91** |
| banka | geniş | 10 | 23,3% | 93 | **138** | 158 |
| banka-bolum | kapalı | 29 | 42,4% | 143 | 524 | 96 |
| banka-bolum | dar | 29 | 42,7% | 144 | 525 | 92 |
| banka-bolum | geniş | 29 | 30,2% | 98 | 164 | 154 |
| banka-bolum-konak | kapalı | 35 | 42,5% | 149 | 529 | 96 |
| banka-bolum-konak | geniş | 35 | 30,7% | 104 | 179 | 144 |
| banka-bolum-yol | kapalı | 104 | 41,5% | 151 | 576 | 115 |
| banka-bolum-yol | geniş | 104 | 31,2% | 111 | 282 | 143 |
| sablon-imzasi | kapalı | 1050 | 30,4% | 166 | 341 | **368** |
| sablon-imzasi | geniş | 1050 | 28,7% | 149 | 293 | 371 |

### 2.1 Mentörün uyarısı doğru — ama global çözüm değil

Kuveyt Türk `saglamkart.` / `milesandsmiles.`, Türkiye Finans `happycard.com.tr`,
Albaraka `albarakaozel.com`, Türkiye Finans `hizlifinansman.com.tr`: toplam
**41 belge** ayrı şablon kullanıyor. Bu 41 belgede ölçüm:

| gruplama | 41 belgede çerçeve |
|---|---|
| banka-bolum | 32,7% |
| banka-bolum-yol | **43,1%** (+10,4 puan) |

Yani uyarı **yerel olarak doğrulandı**. Ama `banka-bolum-yol` aynı anda ana
siteyi 104 küçük gruba bölüyor ve TOPLAM kazanç düşüyor (%42,4 → %41,5),
zararlı kayıp artıyor (524 → 576), sızıntı artıyor (96 → 115).

Bunun için melez bir strateji ölçüldü — **`banka-bolum-konak`**: anahtar
(banka, bölüm, alan adı), ama alan adı `BOILERPLATE_MIN_DOCS`ın altında
kalıyorsa belge ana kovaya geri düşüyor. Sonuç: kazanç ve sızıntı `banka-bolum`
ile aynı (%42,5 / 96), alt alan adları düzeliyor. Gold'da `banka-bolum`in
üstünde (0,677 vs 0,646) ama `banka`nın altında (0,688).

### 2.2 Şablon imzası (MinHash + LSH) kaybediyor — net

16 hash / 8 bant × 2 satır (≈0,35 Jaccard eşiği) ile 1761 belge **1050 kümeye**
dağılıyor. Kümelerin çoğu `BOILERPLATE_MIN_DOCS=3`ün altında kaldığı için hiç
ayıklanmıyor: çerçeve %30,4'e düşüyor ve **krom sızıntısı 96'dan 368'e
fırlıyor** (3,8 kat). "Zararlı kayıp" sayısının düşük görünmesi (341) iyileşme
değil, mekanizmanın çoğu belgeye hiç dokunmamasının yan etkisi. **Reddedildi.**

### 2.3 Kazanan: `banka` (en KABA gruplama)

Beklenenin tersine en kaba gruplama kazandı. Gerekçe ölçümde görünüyor: grup
büyüdükçe site kromu daha çok belgede tekrar ediyor ve `min_docs=3` eşiğini
rahat aşıyor; buna karşılık belgeye ÖZGÜ metnin 3 belgede birden görünme
olasılığı düşüyor. Yani kaba gruplama hem daha çok krom yakalıyor hem daha az
içerik yiyor. Gold'da `products` kapsamında:

| gruplama | mikro-F1 | makro-F1 |
|---|---|---|
| **banka** | **0,688** | **0,624** |
| banka-bolum-konak | 0,677 | 0,614 |
| banka-bolum-yol | 0,672 | 0,612 |
| banka-bolum | 0,646 | 0,587 |

**Not:** bölümler zaten kapsam kararıyla ayrıldığı için (`products` dışına
uygulanmıyor), `banka` gruplaması pratikte "aynı bankanın TÜM sayfalarından
çıkarılan krom, ürün sayfalarına uygulanır" demek. Bölümü anahtardan çıkarmak
kromu daha zengin bir örneklemden öğrenmeyi sağlıyor — kazancın kaynağı bu.

---

## 3. İkinci sinyal: noktalama yoğunluğu

Blok = n-gramın iki yanına ±24 sözcük. Ölçülenler: sözcük başına noktalama
(`.,;:!?`) ve ortalama cümle uzunluğu (sözcük / `.!?`). İki kip denendi:

- **`dar`** — koruma DARALIR: bir gram korunmak için hem finansal sinyal
  taşımalı hem düzyazı olmalı. Amaç: kromun sinyalli ama cümlesiz parçalarının
  ("Taksitli Nakit Avans", "Vadeli Mevduat" menü öğeleri) korumaya sığınıp
  çekirdeğe sızmasını kesmek.
- **`geniş`** — koruma GENİŞLER: sinyal VEYA düzyazı olan gram oran eşiğine
  tabi olur. Amaç: kampanya şablonu kardeşlerinin ortak KOŞUL METNİNİ
  kurtarmak (bu metinde sayı olmadığı için `SIGNAL_MIN_FRACTION` onu görmez).

### 3.1 Sinyalin ayrım gücü ÖLÇÜLDÜ ve zayıf çıktı

250 belgelik rastgele örneklem, 5302 blok:

| grup | n | noktalama/sözcük p10 | medyan | p90 | cümlesiz blok |
|---|---|---|---|---|---|
| krom işaretçili blok | 495 | 0,020 | 0,102 | 0,163 | %16 |
| kalan (içerik) | 4807 | 0,041 | 0,122 | 0,184 | %16 |

Mentörün öncülü ("menü/liste kısmında nokta-virgül yok") **menüler için
doğru**, ama `data/raw` kromunun hacimce ağırlığı menü değil **çerez/KVKK
metni** ve o metin tam anlamıyla düzyazıdır (medyan 0,102). 0,04 eşiği içerik
bloklarının %90'ını korurken krom bloklarının ancak %18'ini eliyor.

Ortalama cümle uzunluğu dağılımı **iki tepeli**: blokta cümle sonu varsa
ortalama 7-16 sözcük, yoksa blok boyuna (≈49) eşitleniyor; arada gözlem yok.
Bu yüzden 20-40 arasındaki her eşik aynı sonucu veriyor ve sinyalin gerçek
ayırıcı bileşeni "blokta en az bir cümle var mı" sorusudur.

### 3.2 Katkı — kapsamına göre işaret değiştiriyor

| kapsam | kapalı | dar | geniş | geniş'in katkısı |
|---|---|---|---|---|
| korpus geneli, zararlı kayıplı belge (banka-bolum) | 524 | 525 | **164** | −%69 |
| korpus geneli, çerçeve kazancı | 42,4% | 42,7% | 30,2% | −12,2 puan |
| korpus geneli, krom sızıntısı | 96 | 92 | 154 | +%60 |
| gold, yalnız `live` (banka-bolum) | 0,538 | — | **0,602** | **+0,064** |
| gold, yalnız `products` (banka) | **0,688** | — | 0,667 | **−0,021** |
| gold, tüm bölümler (banka-bolum) | 0,532 | — | 0,589 | +0,057 |

Üç bulgu:

1. **`dar` kipi ölçülebilir bir katkı yapmıyor** (524→525 zararlı, sızıntı
   96→92, çerçeve +0,3 puan). Mentörün dar hipotezi bu korpusta boş çıktı;
   çünkü koruma kümesi zaten küçük ve kromun sinyalli parçaları oran eşiğini
   çoktan aşıp çerçeveye gidiyor.
2. **`geniş` kipi hasarı onarıyor ama kazancı da yiyor.** `live` bölümünde
   ayıklamanın verdiği zararın %76'sını geri alıyor (0,538 → 0,602; taban
   0,612) — ama yine de tabanı geçemiyor. Yani "noktalamayı ekleyip `live`'ı
   da temizleyelim" seçeneği ÖLÇÜLDÜ ve kaybediyor.
3. **Önerilen kapsamda (`products`) noktalama ZARAR veriyor** (0,688 → 0,667).
   Sebebi ölçümde görünüyor: `products` kromu menü ağırlıklı ve `geniş` kip
   menü bloklarını df eşiğinin altında kaldıkları ölçüde korumaya alıp
   çekirdeğe geri sokuyor (sızıntı 96 → 154).

**Sonuç: noktalama sinyali önerilen kapsamda AÇILMAMALI.** Kod tabanında
ölçüm aracının içinde (`boilerplate_audit.py`, `--noktalama`) kalıyor; gold
büyüdüğünde `live` kararı yeniden açılırsa hazır bekliyor.

---

## 4. Kapsam kararı — bölüm bölüm

Referans: `banka` / kapalı.

| bölüm | belge | çerçeve | düşen | zararlı oran (üst sınır) | gold kanıtı | **KARAR** |
|---|---|---|---|---|---|---|
| `products` | 637 | 42,4% | 56 | %17,1 | 16 gold belgesi, F1 +0,076 | ✅ **UYGULA** |
| `live` | 808 | 54,6% | 90 | %40,6 | 4 gold belgesi, F1 −0,054 | ❌ **UYGULAMA** |
| `docs` | 112 | 37,0% | 11 | %24,1 | gold kapsamı YOK; 11/11 elle okundu, hepsi zararlı | ❌ **UYGULAMA** |
| `archive` | 201 | 31,0% | 2 | %39,8 | gold kapsamı YOK | ❌ **UYGULAMA** (ölçülmedi) |
| `(kok)` / `manual` | 3 | — | 0 | 0 | — | ❌ önemsiz |

Gerekçeler:

- **`products` ✅** — Çerçevesi hacimli (1,15 milyon karakter atılıyor), zararlı
  oranı en düşük bölüm (%17,1) ve gold'un %80'i burada. Ürün sayfalarındaki
  tekrar GERÇEKTEN kromdur: aynı bankanın 40-110 ürün sayfası aynı mega menüyü
  ve aynı çerez bandını taşıyor, ürünü ayıran metin ise tek belgeye özgü.
- **`live` ❌** — Kampanya sayfalarında tekrar iki kaynaktan geliyor: krom (iyi)
  ve **kampanya şablonu kardeşleri** (kötü). Albaraka'nın "World'e özel N
  taksit" ailesi, Türkiye Emlak'ın "Paraf ile … ParafPara" ailesi aynı koşul
  metnini paylaşıyor ve o metin `kampanya_kosullari`nın ta kendisi.
  Gold'da ölçüldü: yalnız `live` temizlenince mikro-F1 0,612 → 0,538.
- **`docs` ❌** — Tekrar burada içeriğin kendisi. 11 belgenin 11'i elle okundu;
  Albaraka'nın 110 KB'lık sözleşmelerinden geriye sayfa numarası döküntüsü
  ("50 1 / 50 50 2 / 50…"), Kuveyt Türk PDF tarifelerinden OCR artığı kalıyor.
  Gold'da hiç `docs` belgesi yok, yani ölçülemez — ve ölçülemeyen bir kapsam
  uygulanmaz.
- **`archive` ❌** — Gold kapsamı sıfır. Çerçeve oranı düşük (%31), kazanç küçük
  (83.864 karakter), zararlı oranı yüksek görünüyor (%39,8). Kanıt yokken
  201 belgeyi riske atmanın getirisi yok.

**"Yarım uygulayıp gerisini bozmaktansa dar bir kapsamda doğru uygulamak"
ilkesi burada sayıya dönüşüyor:** `products`-only kapsamı korpusun %36'sına
dokunuyor, atılan 1.148.000 karakterin tamamı ölçülmüş kazançla geliyor.

---

## 5. Gold'da önce/sonra — kazanan yapılandırmanın alan kırılımı

`banka` / kapalı / yalnız `products`, `--config kural --matcher strict`:

| alan | taban F1 | sonra F1 | fark |
|---|---|---|---|
| kampanya_suresi | 0,308 | **1,000** | **+0,692** |
| hedef_kitle | 0,727 | 0,889 | +0,162 |
| kampanya_kosullari | 0,733 | 0,786 | +0,053 |
| vade_ay | 0,583 | 0,636 | +0,053 |
| alisveris_puani | 0,000 | 0,000 | 0 |
| finansman_tutari | 0,444 | 0,444 | 0 |
| indirim_orani | 1,000 | 1,000 | 0 |
| kar_payi_orani | 0,667 | 0,667 | 0 |
| odul_miktari | 0,400 | 0,400 | 0 |
| tahsis_ucreti | 0,400 | 0,400 | 0 |
| taksit_sayisi | 0,600 | 0,600 | 0 |
| **masraf_durumu** | **0,857** | **0,667** | **−0,190** |
| **MİKRO** | **0,612** | **0,688** | **+0,076** |
| **MAKRO** | **0,560** | **0,624** | **+0,064** |

Hata sınıfları:

| ölçü | taban | sonra |
|---|---|---|
| çıkarım hatası | 0,369 [24/65] | **0,338** [22/65] |
| ├─ kaçırma | 13 | 16 |
| └─ yanlış çıkarım (grounding) | 11 | **6** |
| halüsinasyon | 0,102 [17/166] | **0,066** [11/166] |
| mikro-F1 %95 GA | [0,483–0,716] | [0,527–0,792] |

Okunuşu:

- **Grounding hataları neredeyse yarıya indi (11 → 6).** T-019'un ("chatbot
  konut finansmanı sorgusunda POS hizmetleri döndürüyor") ölçülebilir karşılığı
  budur: model artık komşu kampanyanın / menünün metninden değer devşiremiyor.
- **`kampanya_suresi` 0,308 → 1,000.** Taban, kenar çubuğundaki BAŞKA
  kampanyaların bitiş tarihlerini bu kampanyanın süresi sanıyordu (ölçülen
  örnek: "Diğer Kampanyalar … Sona erdi Bitiş Tarihi: 30 Haziran 2026").
- **Halüsinasyon %35 düştü** (17 → 11 uydurulan değer). Kayıp kaynağının kendisi
  gittiği için üretilecek uydurma da kalmadı.
- **Tek gerileyen alan `masraf_durumu` (−0,190, recall 0,857 → 0,571).** Kaçırma
  2 belgede arttı: "masrafsız / ücretsiz" ifadeleri bazı ürün sayfalarında
  kardeş sayfalarla ortak olan bir dipnotta geçiyor ve çerçeveye gidiyor. Bu
  alan için öneri §6'da.

---

## 6. Öneriler (kod değişikliği `src/` içinde, bu görevin dışında)

1. **`src/` tarafına kapsamlı bir çerçeve ayıklama adımı eklenirken bölüm
   filtresi ZORUNLU olmalı.** Bölümü yok sayan bir uygulama gold'da 0,612 →
   0,532 gerileme demektir. Uygulanacak yapılandırma:
   `grup = banka`, `noktalama = kapalı`, `bölüm ∈ {products}`.

2. **`masraf_durumu` için ham metne düşme (fallback).** Bu tek alan çerçeve
   ayıklamasından zarar görüyor. Öneri: `extract_all` bu alanı çekirdekte
   bulamazsa HAM metinde bir kez daha arasın, ancak eşleşme çerez/KVKK
   işaretçisinden ≥1000 karakter uzaktaysa kabul etsin. (Ölçülmedi — gold'daki
   2 belgelik kayba dayanan bir hipotez.)

3. **Gold'a `docs` ve `archive` belgesi eklenmeli.** Bugün bu iki bölüm hakkında
   hiçbir ölçüm yapılamıyor; 313 belge (korpusun %18'i) kanıtsız bölgede duruyor.
   `docs` için 3-5 sözleşme/tarife belgesi yeterli olur.

4. **`live` kararı gold büyüdüğünde yeniden açılmalı.** Bugün 4 belgeye dayanıyor.
   `geniş` noktalama kipi zararın %76'sını onarıyor; gold 20 → 60 belgeye
   çıktığında `banka / geniş / live` yeniden ölçülmeli.

5. **Kampanya şablonu ailelerini ayrı ele almak.** `live`'daki zarar tek bir
   olgudan geliyor: 5-12 üyeli kampanya aileleri koşul metnini paylaşıyor.
   `BOILERPLATE_MIN_DOCS`ı `live` için 3'ten yükseltmek (ör. 6) bu aileleri
   koruyabilir — ÖLÇÜLMEDİ, bu görevin kapsamı dışındaydı.

---

## 7. Tekrar üretme

```bash
cd app

# Yapılandırma matrisi + belge bazlı ölçüm
.venv/bin/python -m scripts.boilerplate_audit \
    --gruplama banka,banka-bolum,banka-bolum-konak,banka-bolum-yol,sablon-imzasi \
    --noktalama kapali,dar,genis \
    --referans banka/kapali \
    --rapor /tmp/boilerplate-matris.md --jsonl /tmp/boilerplate-belge.jsonl

# Kazanan yapılandırmayla temizlenmiş gold üret ve ölç
.venv/bin/python -m scripts.boilerplate_audit \
    --gruplama banka --noktalama kapali \
    --gold data/gold/gold.v1.json --gold-cikti /tmp/gold.temiz.json
.venv/bin/python -m eval.run_eval --gold /tmp/gold.temiz.json \
    --config kural --matcher both --no-write
```

> `--gold` bayrağı TÜM bölümleri temizler (§0 tablosunun "tüm bölümler"
> satırı). Yalnız `products` kapsamı `section_of` ile filtrelenerek üretildi;
> filtreyi bayrağa taşımak `src/` kararı verildikten sonra anlamlı olacak.

---

## Ek — 2026-08-07: güncel temel çizgide yeniden ölçüm

Bu raporun ana ölçümü `0,612` temel çizgisine göre yapıldı. O ölçümden sonra
aynı gün iki şey değişti ve **ikisi de aynı alanı düzeltiyordu**
(`kampanya_suresi`), dolayısıyla kazançlar toplanamaz:

- `b2a4845` — Faz D'nin üç çıkarım düzeltmesi (sistem iyileşmesi)
- `da02e22` — gold hakemliği, iki anotasyon hatası (ölçüm düzelmesi)

Güncel temel çizgi **0,677**. Öneri bu çizgide yeniden ölçüldü.

### Sonuç (kural / strict, gold n=20, HEAD `8f92c27`)

| yapılandırma | mikro-F1 | makro-F1 | P | R | halüsinasyon | kaçırma | yanlış çıkarım |
|---|---|---|---|---|---|---|---|
| temel (ayıklama yok) | 0,677 | 0,618 | 0,662 | 0,692 | 0,096 | 13 | 7 |
| **products (önerilen)** | **0,688** | **0,624** | 0,717 | 0,662 | **0,066** | 16 | 6 |
| tüm bölümler | 0,562 | 0,563 | 0,607 | 0,523 | 0,066 | — | 11 |

### Okunuşu — kazanç F1'de değil, halüsinasyonda

**Önerinin varış noktası doğrulandı:** 0,688 birebir yeniden üretildi. Ama
**kazancın büyüklüğü değişti**: eski çizgide +0,076 görünen fark, güncel
çizgide **+0,011**. Aradaki farkı Faz D zaten toplamıştı.

+0,011 F1, n=20'de gürültünün içindedir ve tek başına uygulama gerekçesi
sayılmaz. Uygulamayı haklı çıkaran sayı şu:

    halüsinasyon 0,096 -> 0,066   (16 uydurma -> 11, göreli %31 azalma)

Bu, projenin en sert kuralına (CLAUDE.md §19, bilgi yoksa `null`) doğrudan
hizmet eden bir iyileşme ve F1'den daha sağlam bir sinyal: precision 0,662'den
0,717'ye çıkıyor.

**Bedeli var ve gizlenmemeli:** kaçırma 13'ten 16'ya çıkıyor, yani ayıklama üç
gerçek alanı da götürüyor. Takas "daha az uydurma, biraz daha az kapsama" —
bu proje için doğru yönde bir takas, çünkü uydurulmuş bir kâr payı oranı,
eksik bir kâr payı oranından pahalıdır.

### "Tüm bölümler" satırı neden burada

Kapsam kararının kendisi bu satırda görünüyor: aynı mekanizma ayrım
gözetmeden uygulandığında F1 **0,562**'ye düşüyor (−0,115). Yani karar
"ayıklama iyi mi kötü mü" değil, **nereye uygulandığı**. `docs` bölümündeki
sözleşme şablonlarında tekrar eden metin gürültü değil içeriğin kendisidir;
orada mekanizma ters çalışır.

### Uygulama durumu

**Henüz uygulanmadı.** `src/` değişikliği gerekiyor: çerçeve kümesi banka
bazında hesaplanıp `products` belgelerinin `core_text`'i çıkarım girdisi
olmalı. Bu, teslim edilen hattın birincil girdisini değiştiren bir karardır ve
ayrı ele alınmalıdır.

### Ayıklama LLM koluna daha mı çok yarıyor? — HAYIR

Beklenti şuydu: çerçevenin %40'ını okuyan taraf LLM olduğuna göre, ayıklamadan
en çok o faydalanmalı. **Ölçüm bunu yanlışladı.** İki kol × iki girdi:

| | kural | orkestra |
|---|---|---|
| ham gold | 0,677 · hal 0,096 | 0,672 · hal 0,114 |
| **temizlenmiş** | **0,688** · hal **0,066** | 0,682 · hal 0,084 |
| kazanç | +0,011 · −0,030 | +0,010 · −0,030 |

İki kol da **aynı miktarda** kazanıyor: F1'de ~+0,010, halüsinasyonda −0,030.

Açıklaması geriye dönük bakınca açık: çerçeve metni iki katmanı da **aynı
şekilde** kandırıyordu. Çerez metnindeki "1 yıl"ı `vade_ay` sanmak için LLM
olmaya gerek yok — regex de aynı tuzağa düşüyor. Yani gürültü LLM'e özgü bir
zaaf değil, girdi kalitesi sorunuydu ve ikisini de eşit vuruyordu.

**İkinci sonuç: sıralama girdiden bağımsız.** Kural kolu her iki koşulda da
orkestrasyonu geçiyor (0,677>0,672 ve 0,688>0,682) ve halüsinasyonu her iki
koşulda da ~0,018 daha düşük. Ayıklama K3 kararını değiştirmiyor, yalnız iki
kolu birlikte yukarı taşıyor.

---

## Kaçırmayı çözecek tasarım önerisi — blok düzeyinde üç sinyal

### Teşhis: tek sinyal, iki soru

Kaybolan 8 alanın **7'si çöp**, yalnız 1'i gerçek içerik:

| kaybolan | kanıtı | hüküm |
|---|---|---|
| `masraf_durumu='ücretsiz'` ×2 | "30 gün içinde ücretsiz sonuçlandırılmaktadır" (KVKK) | çöp |
| `vade_ay='1 yıl'` ×2 | "kullanılan çerezdir. 1 yıl" | çöp |
| `hedef_kitle='Hoş Geldin'` ×2 | "Hoş Geldin Ramazan!" afişi | çöp |
| `kampanya_kosullari` | blog başlıkları ("DASK nedir?") | çöp |
| `kampanya_kosullari` | "Konut finansmanı başvurusu için gerekli form…" | **gerçek** |

Yani "kaçırma 13 → 16" büyük ölçüde *yanlış değer üretmeyi bırakmak*. Tek
gerçek kayıp, **tekrar ettiği için** silinen meşru bir koşul cümlesi.

Kök neden burada: mekanizma **tek sinyalle (tekrar) iki ayrı soruyu**
cevaplamaya çalışıyor.

1. *Bu blok site çerçevesi mi?* → tekrar iyi bir kanıt
2. *Bu blok ürünle ilgili mi?* → tekrar **kötü** bir kanıt

Şablonlaşmış gerçek içerik (her ürün sayfasındaki standart başvuru cümlesi)
birinci soruda "evet" çıkıyor ve siliniyor. Tersi de var: bir bankanın 3'ten
az benzer sayfası varsa çerez bloğu eşiği geçemiyor ve **hiç silinemiyor** —
bugün dokunamadığımız bir uydurma kaynağı.

### Öneri: karar bloğa taşınır, sinyal üçe çıkar

Karar birimi **token değil blok** olmalı (başlık / boş satır / noktalama
yoğunluğu değişimiyle bölünmüş). Gerekçe ölçüldü: KVKK bloğundaki "ücretsiz"
kelimesinin 200 karakter ötesindeki "Kişisel Veri" işaretiyle ilişkisi ancak
blok düzeyinde görülür.

Her blok üç skor alır:

| sinyal | kaynak | yön |
|---|---|---|
| **tekrar** | mevcut shingling, banka içi df | siler |
| **alan değeri** | `synonyms.FIELD_TRIGGERS` + sayı/birim deseni + `domain/terminology.py` (101 terim) | korur |
| **alan-dışılık** | çerez, KVKK, kişisel veri, aydınlatma metni, açık rıza, gizlilik politikası, site haritası, blog, sosyal medya | siler |

**Öncelik sırası kritik:** `alan-dışılık > alan değeri > tekrar`.

Sıra bu olmazsa KVKK bloğu kurtulur: içindeki "ücretsiz" bir `masraf_durumu`
tetikleyicisidir ve naif bir değer-koruması onu koruyarak bugün kazandığımız
halüsinasyon düşüşünü geri verir.

### Bu ne kazandırır

- **Şablonlaşmış gerçek içerik korunur** → tek gerçek kayıp kapanır.
- **Alan-dışı blok tekrar eşiğinden BAĞIMSIZ silinir** → bugün eşiği geçemeyen
  çerez/KVKK blokları da temizlenir, halüsinasyon kazancı büyür.
- **Karar açıklanabilir olur**: hangi blok neden silindi, üç skorla yazılabilir
  (dashboard'daki kaynak vurgulaması için de kullanılabilir).

### Emniyet ağı — değer taşıyan span geri alınır

Ayıklamadan sonra ham metin taranır: bir alan tetikleyicisinin N sözcük
yakınında sayı+birim taşıyan bir span silinmişse, bağlamıyla birlikte geri
konur. Bu, kaçırmaya **taban** koyar: değer taşıyan hiçbir kanıt sessizce
kaybolamaz. Alan-dışı bloklar bu ağın dışında tutulur (öncelik sırası gereği).

### İkincil düzeltme — sınır aşınması

`core_text` bugün bir sözcüğü, onu kapsayan **herhangi** bir çerçeve
8-gramı varsa siliyor. İçerik/çerçeve sınırında pencere gerçek içeriğe 7
sözcük kadar sarkabiliyor. Düzeltme: yalnız **kapsayan her n-gramı çerçeve
olan** sözcükler silinir.

Buradaki tek gerçek kayıp bir sınır artefaktı değil (tam cümle), yani bu
düzeltme ikincil — ama ucuz ve ilkeli.

### Ölçüm planı

Öneri ancak şu üçü birlikte sağlanırsa uygulanır:
1. gold'da **kaçırma artmaz** (13'ün üstüne çıkmaz),
2. halüsinasyon en az bugünkü kadar düşer (≤ 0,066),
3. yanlış silinen blok listesi elle örneklenip doğrulanır.
