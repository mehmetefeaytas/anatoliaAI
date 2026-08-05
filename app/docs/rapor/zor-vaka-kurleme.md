# Zor-vaka alt kümesi kürleme

**Tarih:** 2026-08-05
**Neden:** CLAUDE.md §6 zor vakaları mimarinin merkezi sayıyor ("%30 burada
kazanılır"), §16 ise "hibridin **özellikle orada** kazandığını göster" diyor. Ama
gold sette **yalnız 1 zor belge** vardı; ablasyon raporu bu iddiayı
"ölçülemedi" diye kaydetmek zorunda kaldı (`docs/rapor/ablasyon.md` §8-5).

**Çıktı:** `data/gold/review/round2_zor_vaka.csv` — **949 satır**, 71 belge,
linter **0 hata 0 uyarı**. `gold_value` sütunları boş; anotatör dolduracak.

---

## Taksonomi

`scripts/gold_schema.py:59` `HARD_TAGS`, altı çok-etiketli sınıf:

| etiket | tanım |
|---|---|
| `terminoloji` | katılım bankacılığı terimi (kâr payı ≠ faiz, katılım fonu) |
| `format_varyant` | TR sayı/tarih/para biçim varyantı |
| `eksik_bilgi` | sayı verilmemiş, sadece niteleyici ("avantajlı finansman") |
| `celiskili` | metin kendi içinde çelişiyor ("masrafsız" + tahsis ücreti) |
| `kosullu_aralik` | aralık ya da zaman/koşul bağımlı oran ("ilk 6 ay %0") |
| `tr_ortografi` | Türkçe imla/karakter tuzağı (İ/ı, şapkalı â, ALL-CAPS) |

## Yöntem ve ilk denemenin çürütülmesi

Tarama 1651 belge üzerinde koştu (kabuk işaretli ve 600 karakterden kısa
belgeler ayıklandı). **İlk desen kümesi işe yaramadı** ve bu kayda geçiyor,
çünkü aynı hata tekrar edilebilir:

| sınıf | gevşek desen | sıkı desen |
|---|---:|---:|
| `celiskili` | 476 (%28,8) | **13** |
| `format_varyant` | 663 (%40,2) | **62** |
| `tr_ortografi` | 878 (%53,2) | **elendi** |
| `kosullu_aralik` | 14 | 12 |
| `eksik_bilgi` | 65 | 25 |

Neden gevşek olduğu gözle görüldü:

- `celiskili` yalnız "ücretsiz" sözcüğünü arıyordu ve *"Aracı'nın işyerlerinde
  **ücretsiz** stant açabilecektir"* gibi cümleleri yakalıyordu — masraf
  çelişkisiyle ilgisi yok. Sıkı sürüm masrafsızlık İDDİASI **ve** sıfırdan büyük
  gerçek bir ücret figürünü birlikte arıyor.
- `tr_ortografi` ALL-CAPS bloklarını sayıyordu; başlıklar her belgede ALL-CAPS.
  Ayırt edici değil, **sınıf tamamen elendi** — korpusta ölçülebilir bir imla
  tuzağı sinyali bulunamadı. Bu bir eksiklik değil bulgudur: o sınıf için iddia
  kurulamaz.

> Bu depoda tek sözcüklü sezgisellerin maliyeti daha önce de ölçüldü: bir
> sezgisel ("ana sayfa"/"müşteri ol") 101 belgenin **87'sinde** yanlış pozitif
> üretmişti, çünkü o sözcükler bazı bankaların her sayfasındaki kırıntı yolunda
> geçiyor.

## Kampanya / tarife ayrımı — havuzu belirleyen ölçüm

Gold seti **kampanya** setidir (şartname §5.1). Adayları belge türüne göre
ayırdım:

| sınıf | kampanya | tarife/form |
|---|---:|---:|
| `format_varyant` | 33 | 19 |
| `eksik_bilgi` | 23 | 2 |
| `kosullu_aralik` | 11 | 1 |
| `terminoloji_paylasim` | 5 | 1 |
| **`celiskili`** | **1** | **12** |

Tarife/form belgeleri havuzdan çıkarıldı → **73 kampanya adayı** (CSV'de 71;
2 belge tekilleştirme sonrası farklı `doc_id` taşıdığı için sabitlenemedi,
`preannotate` bunu uyarı olarak bildirdi).

---

## Sınıf başına adaylar ve kanıt

Alıntılar belgelerden **birebir** alınmıştır.

### `kosullu_aralik` — 10 belge

En değerli sınıf: kademeli oran tabloları ve zaman koşullu ödemesiz dönemler.

- `albaraka--detay-dijital-musterilere-ozel-pratik-finansman-kart`
  > "Vade Aylık Kar Oranı 250-TL-40.000-TL (3 ay ertelemeli) 1-6 ay vade 0%
  > 40.001 – 150.000 TL (3 ay ertelemeli) 1-6 ay vade 3,95%"

  Tutar dilimine göre oran değişiyor: tek bir `kar_payi_orani` değeri tanımsız.
- `albaraka--ihtiyac-pratik-finansman-kart`
  > "125.000 TL'ye kadar 2 ay ödemesiz dönem seçeneği ile 36 aya kadar vade"
- `kuveyt-turk--kampanya-arsivi-e-ihracatiniza-guc-veren-finansman`
  > "E-İhracatçılara özel **ilk 6 ay ödemesiz**, uygun oranlı ve KFK … temin"

### `terminoloji_paylasim` — 5 belge

Biçim kartının işaretlediği tuzak: bu bir **kâr payı oranı değil, paylaşım
oranı**. Yanlış alana yazılırsa §5.7 karşılaştırması elmayla armut kıyaslar.

- `hayat-finans--hesaplar-katilma-hesabi`
  > "Asgari Hesap Açılış Bakiyesi: 1.000 TL* **%90 - %10** %90 - %10 …"
- `kuveyt-turk--altin-hesaplari-altina-altin-katilma-hesabi`
  > "tahakkuk eden kâr, hesap sahibi ile kurum arasında **%40'a %60** şeklinde
  > paylaşılır"

### `eksik_bilgi` — 22 belge

Sayı hiç verilmemiş; doğru davranış `null` üretmek, uydurmamak.

- `albaraka--ihtiyac-eviniz-icin`
  > "**Avantajlı oranlar** ve geri ödeme seçenekleri ile kredi ihtiyacınız…"
- `albaraka--finansmanlar-kobi-gayri-nakdi-finansman`
  > "**uygun koşullarda** ürün ithal edebilirsiniz"

### `format_varyant` — 31 belge

Ölçülen tuzak beklediğimden farklı çıktı: sorun `1.500,00` değil, **noktanın
ondalık ayıraç olarak kullanılması** — Türkçe metinde virgül beklenirken:

- `kuveyt-turk--kampanya-arsivi-bisiklet-finansmaninda-…`
  > "Enerji Tasarrufu Haftasına Özel **%4.19** Kar Oranı Fırsatı!"
- `hayat-finans--kampanyalar-…-fx-dar-makas-avantaji`
  > "**%0.1** dar makas avantajından yararlanılabilmesi için"

`%4.19` ayrıştırıcıda 4,19 mu 419 mu? Aynı belgede hem `0,50%` hem `% 0.5`
biçimi geçen dosyalar var; kararı belirsiz bırakan tek şey ayıraç.

### `celiskili` — 1 belge, ve bu bir BULGU

Tek kampanya adayı:

- `turkiye-finans--kampanyalar-masrafsiz-bankacilik` — adı birebir "Masrafsız
  Bankacılık".

Diğer 12 aday **ücret tarifesi / bilgi formu** çıktı ve hiçbiri çelişki değil;
oralarda "ücret alınmaz" **kapsamı belirli, meşru** bir ifade:
*"debit kartlardan herhangi bir ücret alınmamaktadır"*, *"ilk yıl için ücret
alınmaz"*, *"bir yıl içerisindeki talepler Ücret Alınmaz"*.

**Sonuç: belge İÇİ çelişki korpusta pratik olarak yok.** CLAUDE.md §18'in 2
numaralı yenilikçilik hedefi ("masrafsız deyip tahsis ücreti alanı yakala")
yapısı gereği **belgeler ARASI** bir karşılaştırma: kampanyanın iddiası ile
bankanın ücret tarifesi. Bu, `celiskili` etiketiyle gold sette aranacak bir şey
değil; ayrı bir çapraz-kontrol işi.

İyi haber: makine zaten var. `scripts/crosscheck_rates.py` ve
`data/gold/rate_crosscheck.csv` oranlar için tam bunu yapıyor (bağımsız kaynakla
çapraz doğrulama). Aynı desen **ücretler** için kurulmalı — hedef, kampanya
metnindeki masrafsızlık iddiasını `rates/*.jsonl` ve ücret tarifesi
belgelerindeki tahsis ücreti kayıtlarıyla karşılaştırmak.

### KURULDU — `scripts/crosscheck_fees.py` (2026-08-05)

Bu açık uç kapandı. Ölçülen kapsam: **5 bankadan 33 ilan edilmiş tahsis ücreti
kaydı**, 7 iddia × ürün satırı.

Kurulum sırasında beklenmedik bir şey çıktı ve tasarımı değiştirdi: **"tarifede
ücret var" tek başına çelişki değil.** 33 kaydın **30'u tam olarak %0,5** — bu
BDDK'nın konut finansmanı üst sınırı ve sektörde fiilen tek fiyat. Yani her
"Dosya Masrafsız Konut Finansmanı" kampanyası tarifeyle "çelişiyor" görünür;
oysa çoğu meşru bir **muafiyettir** (standart %0,5'tir, bu kampanyada alınmaz).
Ayırt edici olan **kapsam**:

| sonuç | adet | anlamı |
|---|---:|---|
| `kosullu_muafiyet` | 6 | muafiyet koşula bağlı (yeni müşteri, tarih) |
| `kapsamsiz_iddia` | 1 | tanınan türde koşul yok → insan hakemliği |
| `tutarli` / `tarife_yok` | 0 | — |

Ürün açısından asıl çıktı `dashboard_ifadesi` kolonu: karşılaştırma tablosunda
"masrafsız" yazmak **yanıltıcı**; doğrusu *"yeni müşterilere kapsamında
masrafsız; aksi hâlde %0,5"*. Bu, §17'nin adil kıyas kuralının ücretlere
uygulanmış hâli.

İlk koşu **beş** yanlış pozitif üretti (kâr payı oranını tahsis ücreti sanmak,
finansman tutarı kolonunu ücret sanmak, rehin ücretini tahsis sanmak, uzak ürün
bahsi, "masrafsız bankacılık"). Beşi de kapıya çevrildi ve
`tests/test_crosscheck_fees.py` ile çitlendi.

Yan bulgu: Türkiye Emlak Katılım taşıt tahsis ücretini bir formda %0,5,
diğerinde %0,1 ilan ediyor — bankanın kendi içinde tutarsızlığı.

---

## Tekrar üretim

```bash
# Adaylar sabitlenmiş ön-anotasyon (v1/v2 dosyalarına DOKUNULMAZ)
.venv/bin/python -m scripts.preannotate --limit 73 --seed 42 \
  --pin-csv <aday-listesi>.csv --out data/gold/preannotations.zor.json

# İnceleme CSV'si
.venv/bin/python -m scripts.to_review_csv \
  --pre data/gold/preannotations.zor.json --out-dir <tmp> \
  --annotators A --calibration 0 --duplicate-subset 0 --absent-docs -1 --seed 42

# Denetim
.venv/bin/python -m scripts.lint_review_csv data/gold/review/round2_zor_vaka.csv
```

## Sonraki adım

1. `round2_zor_vaka.csv` anote edilir → gold zor-vaka alt kümesi doğar.
2. Ablasyon `--split hard` ile tekrar koşulur; §16'nın istediği "hibrit zor
   vakada kazanıyor mu" sorusu **ilk kez** cevaplanabilir hâle gelir.
3. ~~Ücret çapraz-kontrolü ayrı iş olarak açılır.~~ **Yapıldı** —
   `scripts/crosscheck_fees.py`, yukarıdaki "KURULDU" bölümüne bakın.
4. `dashboard_ifadesi` kolonu dashboard'un karşılaştırma tablosuna bağlanır.
   Şu an bir CSV kolonu; ürüne dönüşmesi için `src/comparison/` tarafına
   girmesi gerekiyor.
5. `tarife_yok` çıkan banka/ürün çiftleri için ücret tarifesi hasat edilir.
   Şu an 0 satır ama korpus büyüdükçe çıkacak; kapsamı büyütmenin yolu hasat,
   desen gevşetmek değil.

## Related
- [[ablasyon]] — §8-5 zor-vaka iddiasının neden ölçülemediği
- [[_bicim-karti]] — paylaşım oranı kuralı (`absent` + `#terminoloji`)
- [[_hakem-turu-01-finansman-tutari]] — gold hatası / sözleşme boşluğu ayrımı
- `scripts/crosscheck_fees.py` — `celiskili` bulgusunun ürüne dönüşmüş hâli
