# ÜRÜN AİLESİ KAPSAMI HASADI — ölçüm defteri

> Koşuldu: **2026-08-20**. Bu dosya bir plan değil, **koşulmuş hasadın
> tutanağıdır**: her sayı diskte veya ağ yanıtında ölçülmüştür.
>
> İlgili: `config/banks.yaml` · `src/scraping/harvest_extra.py`
> `src/scraping/harvest_products.py` · `src/scraping/discover.py`
> `data/raw/_extra_report.md` · `data/raw/_collection_report.md`
> `docs/rapor/banka-siteleri-veri-kaynagi-haritasi.md`
> `docs/rapor/devam-konut-tasit-hasati.md` (klasik bankalar için kardeş tur)

---

## 0. Neden bu tur — ölçülen sorun

Korpus **toplamda derindi ama ürün ailesi bazında sığdı**. Jürinin en bariz
sorusu ("hangi banka en iyi konut finansmanı veriyor") yalnız 6 bankayı
kıyaslayabiliyordu; şartnamenin manşet alanı `kar_payi_orani` ise
**1.782 belgenin 69'unda (%3,9)** vardı.

Kök neden tek bir yerde değildi. Bu tur **dört ayrı kök neden** buldu ve
hepsi ÖLÇÜMLE gerekçelendi:

| # | Kök neden | Nerede | Etkisi (ölçüldü) |
|---|---|---|---|
| 1 | `max_document_docs` kırpması | `config/banks.yaml` | Kuveyt Türk'te 444 adayın 404'ü sessizce atılıyordu |
| 2 | `document_paths` **tanımsız** | tom-katilim, adil-katilim | belge turu bu bankalarda hiç koşmadı (0 PDF) |
| 3 | Belge deseni **uzantıya** bağlı | hayat-finans | belgeler `.pdf` uzantısız (`/getmedia/<guid>`) → keşif 0 buluyordu |
| 4 | Keşif **başlangıcı yok** | tom-katilim | `sitemap_urls` tanımsızdı; 235 URL'lik sitemap kullanılmıyordu |

Kırpmanın **config'ten mi koddan mı** geldiği ilk iş olarak denetlendi:
`harvest_extra.harvest_extra()` `max_docs=max_docs or bank.max_document_docs`
diyor, `collect_documents` da onu `discover_documents`a geçiriyor. Yani
**kırpma config'tendir** → `src/scraping/*.py` dosyalarına DOKUNULMADI.

---

## 1. ÖNCE / SONRA — banka × ürün ailesi matrisi

Ölçüm komutu (tekrar üretilebilir; "önce" tablosu için hasat başlangıcından
eski dosyalarla, `mtime` kesmesiyle koşuldu):

```bash
# aile eşleşmesi = belge GÖVDESİNDE ürün terimi (dosya adı ya da URL değil)
#   konut   : konut (finansman|kredi) | mortgage | ev kredi | kentsel donusum (finansman|kredi)
#   tasit   : (tasit|arac|oto|otomobil|motosiklet) (finansman|kredi)
#   ihtiyac : ihtiyac (finansman|kredi) | bireysel finansman
#   isyeri  : (isyeri|ticari|isletme|kobi|mikro) finansman | ticari kredi
#   kart    : kredi kart | banka kart | sanal kart | debit kart
#   katilma : katilma hesab | kar paylasim oran | kara katilma oran
# kar_payi_orani sütunu src/extraction/rules/extract.extract_all ile sayıldı
```

### ÖNCE — 1.782 belge

| banka | belge | konut | taşıt | ihtiyaç | işyeri/ticari | kart | katılma hesabı | kar_payi_orani |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| adil-katilim | 6 | **0** | **0** | 1 | 1 | 0 | 1 | 0 |
| albaraka | 228 | 17 | 28 | 56 | 46 | 93 | 20 | 3 |
| dunya-katilim | 123 | 5 | 8 | 13 | 15 | 50 | 6 | 2 |
| hayat-finans | 48 | **0** | **0** | 6 | 7 | 14 | 13 | 0 |
| kuveyt-turk | 537 | 29 | 39 | 28 | 29 | 287 | 19 | 31 |
| tkbb | 2 | 0 | 0 | 0 | 0 | 1 | 2 | 0 |
| tom-katilim | 19 | **0** | **0** | 0 | 0 | 18 | 2 | 1 |
| turkiye-emlak-katilim | 239 | 19 | 6 | 34 | 26 | 44 | 31 | 6 |
| turkiye-finans | 92 | 80 | 82 | 81 | 80 | 90 | 80 | 22 |
| vakif-katilim | 197 | 11 | 15 | 11 | 10 | 74 | 29 | 3 |
| ziraat-katilim | 291 | 23 | 16 | 22 | 120 | 194 | 12 | 1 |
| **TOPLAM** | **1.782** | **184** | **194** | **252** | **334** | **865** | **215** | **69** |

### SONRA — 2.672 belge

| banka | belge | konut | taşıt | ihtiyaç | işyeri/ticari | kart | katılma hesabı | kar_payi_orani |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| adil-katilim | 11 | **0** | **0** | 1 | 2 | 0 | 2 | 0 |
| albaraka | 354 | 25 | 40 | 74 | 53 | 139 | 60 | 21 |
| dunya-katilim | 123 | 5 | 8 | 13 | 15 | 50 | 6 | 2 |
| hayat-finans | 73 | **0** | **0** | 6 | 9 | 22 | 16 | 2 |
| kuveyt-turk | 939 | 80 | 42 | 45 | 30 | 409 | 97 | 50 |
| tkbb | 2 | 0 | 0 | 0 | 0 | 1 | 2 | 0 |
| tom-katilim | 340 | **0** | **0** | 1 | 0 | 280 | 19 | 39 |
| turkiye-emlak-katilim | 242 | 19 | 6 | 34 | 26 | 45 | 32 | 6 |
| turkiye-finans | 99 | 86 | 89 | 88 | 86 | 96 | 86 | 23 |
| vakif-katilim | 197 | 11 | 15 | 11 | 10 | 74 | 29 | 3 |
| ziraat-katilim | 292 | 23 | 16 | 22 | 121 | 195 | 12 | 1 |
| **TOPLAM** | **2.672** | **249** | **216** | **295** | **352** | **1.311** | **361** | **147** |

### Alan kapsamı — şartnamenin manşet alanları

| alan | önce | sonra | değişim |
|---|---:|---:|---:|
| **kar_payi_orani** | **69** | **147** | **+113%** |
| vade_ay | 445 | 654 | +47% |
| taksit_sayisi | 361 | 453 | +25% |
| masraf_durumu | 493 | 795 | +61% |
| tahsis_ucreti | 20 | 33 | +65% |
| finansman_tutari | 67 | 83 | +24% |

`kar_payi_orani` kapsamı belge başına %3,9 → **%5,5**'e çıktı; mutlak sayı
iki katından fazla arttı. Artışın büyük kısmı PDF ürün bilgi formlarından
geliyor (oran orada METİN olarak yayımlanıyor).

### ÖLÇÜM UYARISI — Türkiye Finans satırı şişkin

Türkiye Finans'ın her ailede ~86 göstermesi **veri değil, ölçüm eseridir**:
SharePoint şablonu her sayfanın kuyruğuna tüm ürün ailelerini sayan bir menü
basıyor, anahtar kelime ölçümü onu da sayıyor. Bu satırı aile derinliği kanıtı
olarak KULLANMAYIN; `docs/rapor/boilerplate-kapsam.md` aynı olguyu ölçüyor.
Tablodaki diğer bankalarda böyle bir menü yok (kontrol: hayat-finans ve
tom-katilim'de konut sütunu 0 kalıyor — şablon şişmesi olsaydı orada da
dolardı).

---

## 2. Hangi config değişti ve NİÇİN

Değişen tek dosya: **`config/banks.yaml`**. Python koduna dokunulmadı.

### 2.1 `max_document_docs` — ölçülmüş kuru koşuya göre

Kırpma tavanları tahminle değil, **PDF indirmeden koşulan bir keşif kuru
koşusuyla** belirlendi (banka başına yalnız 2-3 liste sayfası isteği):

| banka | aday | robots engelli | çekilebilir | eski tavan | yeni tavan | gerekçe |
|---|---:|---:|---:|---:|---:|---|
| kuveyt-turk | 444 | 0 | 444 | 40 | **460** | 404 aday sessizce kırpılıyordu |
| albaraka | 427 | 282 | 145 | 40 → 160 → **440** | **440** | bkz. §2.2, iki aşamalı düzeltme |
| turkiye-emlak-katilim | 43 | 0 | 43 | 40 | **60** | diskte tam 40 vardı = tavan tam tamına vurmuş |
| tom-katilim | 99* | 0 | 99 | (yol yoktu) | **110** | `document_paths` yeni eklendi |
| turkiye-finans | 342 | **342** | **0** | 40 | 40 (DEĞİŞMEDİ) | robots tümünü engelliyor, tavan işe yaramaz |
| vakif-katilim | 117 | **117** | **0** | 40 | 40 (DEĞİŞMEDİ) | aynı |
| ziraat-katilim | 18 | 0 | 18 | 40 | 40 (DEĞİŞMEDİ) | havuz tavanın altında |
| dunya-katilim | 2 | 0 | 2 | 40 | 40 (DEĞİŞMEDİ) | aynı |
| hayat-finans | 0 → 10 | 0 | 10 | 40 | 40 (DEĞİŞMEDİ) | sorun tavan değil DESEN'di, bkz. §2.4 |
| adil-katilim | 10* | 0 | 10 | (yol yoktu) | 40 (DEĞİŞMEDİ) | havuz tavanın altında |

`*` yeni eklenen `document_paths` sonrası ölçüldü.

**Tavanı yükseltmediğimiz yerler bilinçli.** Türkiye Finans'ta 40'ı 400 yapmak
tek belge kazandırmaz; config'i yanıltıcı yapar. Bu, "her tavanı yükselt"
refleksinin reddi.

### 2.2 Albaraka — kırpma robots süzgecinden ÖNCE çalışıyor (iki aşamalı ders)

İlk düzeltmede tavan 40 → 160 yapıldı, koşuldu, **yetmediği ölçüldü**:
160 tavanıyla kalan adayların **103'ü robots engelliydi** ve yalnız 57 PDF
geldi. Sebep sıralama: `rank_documents` "ucret|tarife" geçen her adayı 0.
kovaya alıyor ve Albaraka'nın `/TranslateTool/pdf-isaretdili/…` ile
`/TranslateTool/pdf-ses/…` **sarmalayıcıları** da o desene uyduğu için
çekilebilir adaylarla aynı kovada yarışıp onları dışarı itiyor.

**Genel ders:** `_discover` kırpmayı robots denetiminden ÖNCE yapıyor, yani
tavan engelli adayları da sayıyor. Robots engelli havuzu büyük olan bankada
tavan, **çekilebilir** aday sayısına değil **toplam** aday sayısına göre
konmalı. 160 → 440 yapıldı, yeniden koşuldu: **57 → 141 PDF**.

### 2.3 `document_paths` eklenenler (bugüne kadar tanımsızdı)

Yollar tahmin edilmedi; **zaten diskteki HTML'den** ya da **canlı statik
çekimden** ölçülerek bulundu.

| banka | eklenen yol | ölçülen PDF bağlantısı | sonuç |
|---|---|---:|---:|
| tom-katilim | `/sozlesme-ve-formlar.html` | 99 (curl, HTTP 200) | 99 PDF |
| tom-katilim | `https://tombankhadi.com/urun-ve-hizmet-ucretleri` | 1 | (aynı 99 içinde) |
| adil-katilim | `/katilim-bankaciligi/belgeler` | 10 | 5 PDF (bkz. §5) |
| hayat-finans | `/finansmanlar/bana-bunu-al-is-ortagim` | 1 (`/getmedia/`) | 10 PDF |
| hayat-finans | `/krediler/hayat-finans-egitim-finansmani-sistemi` | 1 | " |
| hayat-finans | `https://hayatpay.com.tr/sozlesmeler` | 5 | " |

**DENENDİ ve ALINMADI** (0 statik PDF bağlantısı verdiği ölçüldü — boş yolu
config'e yazmak istek üretir, belge üretmez):

- `tombankhadi.com/ucretler-ve-limitler` → HTTP 200, 0 PDF (içerik JS ile)
- `tombankhadi.com/sozlesme-ve-formlar` → HTTP 200, 0 PDF (aynı sebep)
- `www.tombank.com.tr/urun-ve-hizmet-ucretleri.html` → **HTTP 404** (ölü)
- `hayatpay.com.tr/islemler-ve-ucretler` → HTTP 200, 0 PDF; ücret tablosu
  HTML olarak yayımlanıyor → belge turu değil KAMPANYA turuna alındı

### 2.4 hayat-finans — belgeler `.pdf` uzantısız (kök neden #3)

`document_paths` tanımlıydı, tavan da bol geliyordu, ama belge turu **0 PDF**
döndürüyordu. Sebep tavan değil `DEFAULT_DOCUMENT_PATTERNS`: yalnız
`\.pdf(\?|$)` arıyor. Hayat Finans belgeleri **uzantısız** yayımlıyor:

```
https://hayatfinans.com.tr/getmedia/<guid>/<baslik>
```

Ölçüldü (`curl -I`): `HTTP 200`, `content-type: application/pdf`; indirilen
gövde `%PDF-1.4` ile başlıyor (91 KB). Yani gerçek PDF, yalnız adı `.pdf`
değil. `looks_like_pdf` içerik-tipi + imzaya baktığı için **indirme tarafı
zaten çalışıyordu**; kırılan tek yer keşif süzgeciydi.

Düzeltme banka bazında `document_patterns` (varsayılanı ezer, bu yüzden
`\.pdf` deseni de **korundu**):

```yaml
document_patterns:
  - '\.pdf(\?|$)'
  - /getmedia/
```

Sonuç: 0 → **10 PDF, 93 sayfa**. Aralarında "sözleşme öncesi bilgilendirme ile
**ücret ve masraflara** ilişkin bilgilendirme formu" ve "bana-bunu-al-finansman-
**ihtiyac-finansmani** sözleşmesi" var — bankanın ihtiyaç finansmanı ailesindeki
tek birincil kaynağı.

### 2.5 tom-katilim — keşif başlangıcı yoktu (kök neden #4)

Korpusun en sığ bankasıydı: **19 belge**, hiç PDF yok. `sitemap_urls` hiç
tanımlı değildi, keşif yalnız 3 liste sayfasından yürüyordu.

Ölçüldü (curl, tahmin değil):

| adres | sonuç |
|---|---|
| `www.tombank.com.tr/sitemap.xml` | HTTP **404** — kurumsal sitede sitemap yok |
| `www.tombank.com.tr/robots.txt` | HTTP **404** — kural yok |
| `tombankhadi.com/sitemap.xml` | HTTP **200**, `application/xml`, **235 `<loc>`** |
| `tombankhadi.com/robots.txt` | `Allow: /` + `Disallow: /*arama-sonuclari?q=` |

Sitemap eklendi. `detail_patterns` ile eşleşen 162 adayın 14'ü korpusta zaten
vardı → **148 yeni aday** (ölçüm: `matches()` + mevcut `meta.json`'lar). Arama
sonucu sayfası `DEFAULT_EXCLUDE_PATTERNS`taki `/arama` ile zaten eleniyor, yani
robots'un tek `Disallow` kuralına dokunulmuyor.

`max_docs` 60 → **180**. Sonuç: kampanya turu **164 belge** (0 başarısız URL).

### 2.6 hayat-finans — kampanya deseni TEKİL/ÇOĞUL uyuşmazlığı

`extra_hosts`ta `hayatpay.com.tr` doğru tanımlıydı ama korpusta o alandan
**tek belge yoktu** (ölçüldü). Sebep: hayatpay yolu **tekil** yazıyor
(`/kampanya/`), ana banka **çoğul** (`/kampanyalar/`); `detail_patterns`
yalnız çoğulu tanıyordu. Aynı sınıf hata `/isim-kampanyalar` (KOBİ kampanya
ağacı) için de vardı — `-kampanyalar` ile `/kampanyalar` ayrı dizgeler.

Eklenen desenler: `/isim-kampanyalar`, `/kampanya/`, `islemler-ve-ucretler`.
Ölçüldü: aday 12 → 51, bunların **39'u yeni**. Sonuç: kampanya turu 13 → 28
belge.

### 2.7 tom-katilim — MÜKERRER AĞAÇ kesildi (`exclude_patterns`)

Hasat koşulduktan **sonra** ölçüldü: tombankhadi.com aynı kampanyayı iki
yoldan yayımlıyor.

| yol | belge |
|---|---:|
| `/kampanyalar/<slug>` | 82 |
| `/cok-kazananlar-kulubu-kampanya/<slug>` | 81 |
| aynı slug'ın iki yolda birlikte bulunması | **81** |
| YALNIZ `cok-kazananlar`'da bulunan slug | **0** |

İkinci ağaç tek bir özgün belge getirmiyor. `collect_live`in temiz metin
tekilleştirmesi bunları **yakalayamadı**, çünkü aradaki tek fark kırıntı yolu:
`Kampanyalar` ↔ `TOM Bank Çok Kazananlar Kulübü … Kampanya` (ölçülen fark
56 bayt; gövde metni birebir aynı, `content_hash`ler farklı).

`exclude_patterns: [/cok-kazananlar-kulubu-kampanya/]` eklendi → aday 162 → 81
(ölçüldü). Diskteki 81 mükerrer dosya **SİLİNMEDİ** (bu turun kuralı: yalnız
ekle) — bkz. §7 açık uçlar, tek komutluk temizlik orada.

### 2.8 GERİ ALINAN değişiklik — hayatpay sitemap'i (bayat)

`hayatpay.com.tr/sitemap.xml` robots.txt tarafından bildiriliyor, HTTP 200
dönüyor, 36 `<loc>` içeriyor ve 24'ü ana bankanın sitemap'inde olmayan
`/kampanya/<sayi>` adresleri. Umut verici göründü, **eklendi ve hasat
koşuldu**. Sonuç: **24/24 sayısal adres HTTP 404** (§6'da tam liste).
Sitemap bayat. Kayıp yok — aynı kampanyalar liste sayfasından slug'la geliyor
ve `/kampanya/` deseniyle toplanıyor (11 belge ölçüldü). Sitemap **geri
alındı**: kalsa her koşuda 24 boşa istek + 24 sahte "başarısız URL" üretirdi.

> Bu, `devam-konut-tasit-hasati.md` §4'teki dersin tekrarı: **sitemap'te
> görmek kanıt değildir.**

---

## 3. KOŞULAN TURLAR ve gelen belge

Hepsi robots.txt uyumlu (`--ignore-robots` **kullanılmadı**), alan adı başına
3,0 sn bekleme (`--delay 3`, değiştirilmedi), paralel istek yok.

```bash
# 1) BELGE (PDF) turu — tüm bankalar
.venv/bin/python -m src.scraping.harvest_extra --round docs --config config/banks.yaml

# 2) Albaraka için tavan 440'a çıkarılıp YENİDEN koşuldu (bkz. §2.2)
.venv/bin/python -m src.scraping.harvest_extra --round docs --config config/banks.yaml --only albaraka

# 3) KAMPANYA turu — yalnız kapsamı büyüyen iki banka
.venv/bin/python -m src.scraping.harvest --config config/banks.yaml \
    --banks tom-katilim,hayat-finans

# 4) ÜRÜN turu — ürün tarafı sığ kalan altı banka
.venv/bin/python -m src.scraping.harvest_products --config config/banks.yaml \
    --only tom-katilim,adil-katilim,hayat-finans,turkiye-finans,ziraat-katilim,dunya-katilim \
    --max-docs 110 --delay 3
```

### Belge (PDF) turu sonucu — 758 PDF, 5.410 sayfa

Sayılar `data/raw/_extra_report.md` ile birebir aynıdır. "Keşif" sütunu
**kırpmadan SONRAKİ** aday sayısıdır; kırpmadan önceki havuz ayrı sütunda.

| banka | havuz (kuru koşu) | keşif (kırpma sonrası) | PDF | sayfa | robots engeli | HTTP hata / metin çıkmadı |
|---|---:|---:|---:|---:|---:|---:|
| kuveyt-turk | 444 | 444 | **441** | 3.189 | 0 | 3 |
| albaraka | 427 | 427 | **141** | 1.134 | **282** | 0 |
| tom-katilim | 99 | 99 | **99** | 424 | 0 | 0 |
| turkiye-emlak-katilim | 43 | 43 | **43** | 414 | 0 | 0 |
| ziraat-katilim | 18 | 18 | 17 | 141 | 0 | 1 |
| hayat-finans | 10 | 10 | **10** | 93 | 0 | 0 |
| adil-katilim | 10 | 10 | 5 | 8 | 0 | 5 |
| dunya-katilim | 2 | 2 | 2 | 7 | 0 | 0 |
| **turkiye-finans** | **342** | 40 | **0** | 0 | 40 | 0 |
| **vakif-katilim** | **117** | 40 | **0** | 0 | 40 | 0 |
| tkbb | — | — | 0 | 0 | 0 | `document_paths` yok, tur atlandı |
| **TOPLAM** | **1.512** | **1.133** | **758** | **5.410** | **362** | **9** |

Türkiye Finans ve Vakıf Katılım'da tavan bilinçli olarak 40'ta bırakıldığı için
koşu yalnız 40 adayı deniyor ve 40'ı da engelli çıkıyor. **Engelli havuzun
tamamı** kuru koşuda ölçüldü: TF 342/342, Vakıf 117/117 — yani tavanı
yükseltmek 0 belge kazandırırdı (§4). Robots ile atlanan gerçek aday toplamı
bu havuzlarla birlikte **741**'dir (282 + 342 + 117); koşu sırasında fiilen
denenip atlanan sayı 362'dir.

### Kampanya turu sonucu

| banka | keşif | belge | başarısız URL |
|---|---:|---:|---:|
| tom-katilim | 164 | **164** | 0 |
| hayat-finans | 51 | **27** | 24 (hepsi bayat hayatpay sitemap'i, §6) |

### Ürün turu sonucu

| banka | keşif | belge | not |
|---|---:|---:|---|
| tom-katilim | 79 | **74** | 5'i çok kısa içerik (JS ile gelen ücret tabloları) |
| dunya-katilim | 61 | 61 | — |
| ziraat-katilim | 62 | 59 | 3 ölü URL (§6) |
| turkiye-finans | 45 | 45 | — |
| hayat-finans | 35 | 35 | — |
| **adil-katilim** | **0** | **0** | Nuxt SPA ana sayfasından ürün bağlantısı çıkmıyor |

### Banka başına önce → sonra

| banka | önce | sonra | fark | live | products | archive | docs |
|---|---:|---:|---:|---:|---:|---:|---:|
| kuveyt-turk | 537 | **939** | +402 | 157 | 108 | 232 | 441 |
| tom-katilim | 19 | **340** | +321 | 165 | 76 | 0 | 99 |
| albaraka | 228 | **354** | +126 | 90 | 110 | 1 | 152 |
| hayat-finans | 48 | **73** | +25 | 28 | 35 | 0 | 10 |
| turkiye-finans | 92 | **99** | +7 | 44 | 51 | 3 | 0 |
| adil-katilim | 6 | **11** | +5 | 6 | 0 | 0 | 5 |
| turkiye-emlak-katilim | 239 | **242** | +3 | 89 | 110 | 0 | 43 |
| ziraat-katilim | 291 | **292** | +1 | 215 | 59 | 1 | 17 |
| dunya-katilim | 123 | 123 | 0 | 59 | 62 | 0 | 2 |
| vakif-katilim | 197 | 197 | 0 | 90 | 107 | 0 | 0 |
| tkbb | 2 | 2 | 0 | 0 | 0 | 0 | 2 |
| **TOPLAM** | **1.782** | **2.672** | **+890** | | | | |

`data/raw` boyutu: **669 MB**. Silinen dosya: **0** (`git status` doğrulandı).
`data/raw` altında yeni dosya **1.556**, güncellenen **393** — güncellenenler aynı `source_url`in
yeniden çekilmesiyle tazelenen belgeler; `content_hash` yeni baytların özeti,
`source_url` / `collection_method` korunuyor.

---

## 4. ROBOTS ENGELİ — 741 aday (`--ignore-robots` KULLANILMADI)

CLAUDE.md §14 taahhüdü korunmuştur. Engel, iki bankada **PDF ağacının
tamamını** kapsıyor ve bu ölçülmüş robots kuralına dayanıyor:

**Türkiye Finans** (`www.turkiyefinans.com.tr/robots.txt`):
```
Disallow: /*pdf$
Disallow: /tr-tr/bireysel/ihtiyac-finansmani/Sayfalar/konut-gelistirme-finansmani.aspx
```
`/*pdf$` **bütün PDF'leri** engelliyor → 342/342 aday atlandı. Dahası bankanın
kendi **konut geliştirme finansmanı** ürün sayfası da ayrıca engelli — yani
Türkiye Finans'ın konut ailesindeki boşluk kısmen robots kaynaklı.

**Vakıf Katılım** (`www.vakifkatilim.com.tr/robots.txt`):
```
Allow: /documents/*.jpg
Allow: /documents/*.png
Allow: /documents/*.jpeg
Disallow: /documents/
```
Tüm PDF'ler `/documents/` altında → 117/117 aday atlandı (yalnız görsel
uzantılarına izin var).

**Albaraka**: 282 aday, `/TranslateTool/pdf-isaretdili/…` ve
`/TranslateTool/pdf-ses/…` erişilebilirlik sarmalayıcıları — asıl PDF'in
işaret dili / sesli sürüm görüntüleyicileri. Bunların engellenmesi gerçek
kayıp değil: asıl belgeler `/documents/…` altından zaten alınıyor (141 PDF).

**Şartname §5.1** bu belgeler için elle toplamaya izin veriyor
(`data/raw/<banka>/manual/`). Bu ayrı bir karardır; **bu turda otomatik hat
robots'a uyumlu bırakıldı** ve config'e o yönde yanıltıcı bir tavan
yazılmadı.

---

## 5. ARANAN AMA GERÇEKTEN OLMAYAN AİLELER

Bu bölüm "eksik hasat" ile "olmayan ürün" ayrımını yapar. Her iddia
**tam sitemap** ya da bankanın **kendi ürün kataloğu** ile kanıtlanmıştır;
hiçbiri "bulamadım" demeye dayanmıyor.

### Hayat Finans — konut/taşıt **YOK** (kanıt: 360 URL'lik tam sitemap)

`https://hayatfinans.com.tr/sitemap.xml` → HTTP 200, **360 tekil `<loc>`**.
İçinde `konut`, `tasit`, `mortgage`, `ev-kredi` geçen **tek ürün sayfası
yok**; `ihtiyac` yalnız bir blog yazısında geçiyor
(`/finansal-kilavuz/alisveris-istek-mi-ihtiyac-mi`).

Bankanın **tüm** finansman hattı sitemap'te 7 sayfa:

```
/krediler/bana-bunu-al
/krediler/hayat-finans-egitim-finansmani-sistemi
/finansmanlar/bana-bunu-al-is-ortagim
/finansmanlar-is/e-teminat-mektubu
/finansmanlar-is/isletme-finansmani
/finansmanlar-is/mikro-finansman
/finansmanlar-is/ticari-finansman
```

Zaten toplanmış `products/krediler.txt` ve `products/finansmanlar.txt`
metinleri de aynı şeyi söylüyor. Türkiye'nin ilk dijital bankası; konut/taşıt
ürünü yayımlamıyor. **Olmayan sayfa için config yazılmadı.**

### T.O.M. Katılım — konut/taşıt **YOK** (kanıt: 235 URL'lik tam sitemap)

`tombankhadi.com/sitemap.xml` 235 URL; `konut|tasit|mortgage|ev-kredi`
eşleşmesi **0**. Kredi hattı `/hadi-krediler` altında tam üç ürün:

```
/hadi-krediler/veresiye-kredi
/hadi-krediler/taksitli-alisveris-kredisi
/hadi-krediler/magazadan-alisveris-kredisi
```

Zaten toplanmış `live/urunlerimiz.txt` bunu doğruluyor (ayrıca "Sağlık
Kredisi" kampanyaları var). Hepsi alışveriş/BNPL sınıfı; konut ve taşıt
finansmanı hattı yok. Hasat 19 → 340 belgeye çıktı ama **konut sütunu hâlâ 0**
— bu bir hasat eksiği değil, bankanın ürün yelpazesidir.

### Adil Katılım — konut/taşıt **YOK** (kanıt: bankanın kendi kataloğu)

`live/katilim-bankaciligi-urun-ve-hizmetler.txt` dört ürün sayıyor: Özel Cari
Hesap, Ticari Finansman, Katılma Hesapları, Bireysel Finansman ("eğitim,
sağlık, tatil, ev eşyası"). Konut/taşıt hattı henüz açılmamış — banka yeni ve
mobil uygulaması "çok yakında" durumunda.

Ayrıca ölçüldü:
- `robots.txt` → HTTP 200 ama gövde **boş (1 bayt)** → kural yok
- `sitemap.xml` → HTTP 200 ama **XML değil**: SPA ana sayfasının HTML'i
  (`<title>Anasayfa | Adil Katılım</title>`). Bu yüzden `sitemap_urls`
  **yazılmadı** — eklenirse her koşuda 0 `<loc>`luk boş bir istek üretirdi.

### Vakıf Katılım — kart markası yok (önceki turdan, doğrulandı)

`config/banks.yaml` içindeki 2026-08-04 notu geçerli: VKart'ın ayrı sitesi
yok, denenen 4 alan adı DNS'te çözülmüyor. Bu turda tekrar denenmedi.

---

## 6. ÖLÜ / 404 URL'ler — ölçülmüş liste

### hayatpay.com.tr sitemap'i — 24/24 sayısal adres HTTP 404

```
/kampanya/73   /kampanya/83   /kampanya/164  /kampanya/280  /kampanya/316
/kampanya/362  /kampanya/370  /kampanya/416  /kampanya/494  /kampanya/500
/kampanya/501  /kampanya/507  /kampanya/508  /kampanya/512  /kampanya/553
/kampanya/588  /kampanya/589  /kampanya/590  /kampanya/591  /kampanya/592
/kampanya/631  /kampanya/636  /kampanya/637  /kampanya/638
```
→ sitemap config'ten **geri alındı** (§2.8).

### Belge turunda ölü PDF adresleri

| banka | URL | sonuç |
|---|---|---|
| kuveyt-turk | `/medium/2025-ticari-urun-ve-hizmet-ucret-tablosu-3159.pdf` | HTTP 404 |
| kuveyt-turk | `/medium/ticari-urun-hizmet-tablosu-3541.pdf` | HTTP 404 |
| kuveyt-turk | `/medium/sermaye-piyayasi-kurulundan-bankalarin-kamuyu-aydi-433.pdf` | PDF metni çıkarılamadı |
| ziraat-katilim | `…/2024-08/Filika (Finansman Limitli Kart) Banka Kartı Ürün Sözleşmesi.pdf` | HTTP 404 |
| adil-katilim | `/assets/pdfs/icazet-belgeleri/*.pdf` (5 dosya) | PDF metni çıkarılamadı |

**Adil Katılım'ın 5 icâzet belgesi taranmış görüntü** — metin katmanı yok, bu
yüzden 10 adaydan 5'i belge olarak kaydedilemedi. Kaybedilen 5 dosya
bilgilendirme formu DEĞİL, icâzet (fıkhî uygunluk) belgesidir; oran/ücret
taşımıyor. OCR ayrı bir karar konusudur, bu turda yapılmadı.

### Ürün turunda ölü URL'ler

| banka | URL | sonuç |
|---|---|---|
| ziraat-katilim | `/yatirimci-kosesi` | HTTP 404 |
| ziraat-katilim | `/clone-hesaplar` | HTTP 404 (sitemap'te kalmış kopya sayfa) |
| ziraat-katilim | `/ticari/finansman-urunleri/surdurulebilirlik-temali-ticari-urunler/yenilenebilir-enerji-…` | HTTP 493 |

### Diğer ölçülmüş ölü/işe yaramaz kaynaklar

| adres | sonuç | not |
|---|---|---|
| `www.tombank.com.tr/sitemap.xml` | 404 | kurumsal sitede sitemap yok |
| `www.tombank.com.tr/robots.txt` | 404 | kural yok |
| `www.tombank.com.tr/urun-ve-hizmet-ucretleri.html` | 404 | tahmin edilen yol, ölü |
| `www.turkiyefinans.com.tr/sitemap.xml` | 200 ama **işe yaramaz** | 375 baytlık sitemapindex; çocukları (`sitemap0.xml`, `sitemap1.xml`) 200 dönüyor ama **XML değil**, SharePoint hata sayfası HTML'i. TF için sitemap YOK sayılmalı. |
| `dunyakatilimsite.blueprint.com.tr/sitemap.xml` | **403** | dunya-katilim robots.txt bunu bildiriyor; kanonik `dunyakatilim.com.tr/sitemap.xml` çalışıyor (474 `<loc>`) |
| `www.adilkatilim.com.tr/sitemap.xml` | 200 ama XML değil | SPA HTML'i |

---

## 7. AÇIK UÇLAR — sıradaki oturuma

### 7.1 (ÖNCELİK) tom-katilim'de 81 mükerrer dosya diskte duruyor

§2.7'de ölçüldü: `/cok-kazananlar-kulubu-kampanya/<slug>` ağacının **81
dosyasının tamamı** `/kampanyalar/<slug>` ikizinin kopyası; özgün belge 0.
Config artık ikinci ağacı kesiyor (yeni koşuda toplanmayacak) ama **diskteki
81 dosya silinmedi** — bu turun kuralı "yalnız ekle"ydi. Silinene kadar
tom-katilim korpusta 340 değil gerçekte **259 özgün belge** taşıyor ve
kıyas/metrik tarafında çifte sayılır.

Temizlik komutu (önce kuru koşu):

```bash
cd app
# KURU KOŞU — ne silineceğini listeler
.venv/bin/python - <<'PY'
import json
from pathlib import Path
kam = {json.load(open(m))["source_url"].rsplit("/", 1)[1]
       for m in Path("data/raw/tom-katilim/live").glob("*.txt.meta.json")
       if "/kampanyalar/" in json.load(open(m))["source_url"]}
sil = []
for m in Path("data/raw/tom-katilim/live").glob("*.txt.meta.json"):
    u = json.load(open(m))["source_url"]
    if "/cok-kazananlar-kulubu-kampanya/" in u and u.rsplit("/", 1)[1] in kam:
        kok = str(m)[:-len(".txt.meta.json")]
        sil += [p for p in (kok + ".txt", kok + ".txt.meta.json", kok + ".html") if Path(p).exists()]
print(len(sil), "dosya")
for p in sil: print(p)
PY
```

### 7.2 (ÖNCELİK) `tests/test_expiry_stamp.py` ölçülmüş sabiti bayatladı

**Tek başarısız test:**
`TestKorpusRegresyonu::test_kontrol_bankalarinda_sifir (banka='tom-katilim')`
— `22 != 0`.

Bu bir hata değil, testin **kendi docstring'inin öngördüğü durum**: "Sayı
değişirse … korpus yeniden hasat edilmiştir; ikinci durumda ölçüm tekrarlanıp
bu sayılar ve rapor güncellenmelidir."

Damga **gerçektir**, yanlış pozitif değil. Kanıt (gövde metninden):

```
… A101'de Hadi Veresiye ile Toplam 5.000 TL Harcamana,500 TL Kazan!
(GEÇMİŞ KAMPANYA) Bu kampanya sona ermiştir. Kampanya Detayları
Kampanya 1 Kasım – 31 Aralık tarihleri …
```

22 belgenin tamamında ifade `Bu kampanya sona ermiştir` (bitmiş kip — ihtar
mastarı değil, `expiry_stamp.py`'nin ayırt ettiği tam ayrım). 11 özgün
kampanya × 2 mükerrer ağaç = 22; §7.1 temizliği sonrası **11** kalacak.

`scripts/damga_isaretle.py --uygula` KOŞULDU (offline, dosya taşımaz/silmez):
22 `.meta.json`'a `campaign_status: expired` + `expiry_stamp` kanıt bloğu
yazıldı, **0 işaret geri alındı**, provenance (`source_url`/`scraped_at`/
`content_hash`/`collection_method`) korundu. Diğer bankaların işaretleri
değişmedi (dunya 38, vakif 81, ziraat 102 — hepsi aynı).

Ama test `.txt` gövdesini okuyor, `meta.json`'ı değil; dolayısıyla işaretleme
testi geçirmiyor. Gereken karar `tests/` sahibinde: `tom-katilim`
`KONTROL_BANKALAR`dan çıkarılıp `DAMGALI_BANKALAR`a **ölçülmüş sayıyla**
(temizlikten önce 22, sonra 11) eklenmeli ve
`docs/rapor/suresi-dolmus-damgasi.md` güncellenmelidir. **Bu turda testler
değiştirilmedi** — geçirmek için sabit uydurmak, testin koruduğu şeyi yok
eder.

### 7.3 `collect_documents` yalnız statik çekici kullanıyor

Tasarım kararı (`collector.py`: "PDF indirmek için tarayıcı gerekmez") ama iki
yerde ölçülmüş kayba yol açıyor — belge **listesi** JS ile üretiliyorsa keşif
0 buluyor:

- `dunyakatilim.com.tr/sozlesme-ve-formlar` → 506 KB gövde, 107 href,
  **0 belge bağlantısı** (liste JS ile geliyor). Bu yüzden dunya-katilim'de
  yalnız 2 PDF var.
- `tombankhadi.com/sozlesme-ve-formlar` ve `/ucretler-ve-limitler` → aynı
  durum (tom-katilim'in 99 PDF'i **tombank.com.tr**'nin statik sayfasından
  geldi, tombankhadi'den değil).

Config'le çözülemez. Karar: `collect_documents`'a `scrape_mode`a saygılı bir
keşif aşaması (keşif tarayıcıyla, indirme statik) eklenip eklenmeyeceği.
Bu turda **koda dokunulmadı**.

### 7.4 `harvest_products` `max_product_docs`'u OKUMUYOR

`harvest_products.py`: `max_docs=max_docs or 40`. `BankConfig.max_product_docs`
(varsayılan 80) alanı **tanımlı ama hiçbir kod yolunda kullanılmıyor**; ürün
turunun tavanı yalnız CLI `--max-docs` ile ayarlanabiliyor. Bu turda CLI'dan
110 verildi, kod değiştirilmedi (dosya bu turun sahiplik kapsamında değildi ve
başka bir yolu vardı). Düzeltilirse config-driven onboarding iddiası (§18-3)
ürün turunda da tutar.

### 7.5 adil-katilim ürün turu 0 dönüyor

`discover_products` `product_paths` ve `sitemap_urls` yoksa `paths=["/"]`
fallback'ine düşüyor; Adil Katılım'ın Nuxt SPA ana sayfasından ürün deseniyle
eşleşen **hiç** bağlantı çıkmıyor (keşif 0). Belge turu ise çalışıyor
(`/katilim-bankaciligi/belgeler` sunucuda render ediliyor). Ürün tarafı için
`product_paths` elle yazılmalı; bu turda hangi yolların gerçekten var olduğu
ölçülmediği için **tahminle yol yazılmadı**.

### 7.6 Arşiv turu bu turda koşulmadı

`--round docs` kullanıldı, `--round archive` değil. `data/raw/_extra_report.md`
bu yüzden arşiv tablosunu boş gösteriyor; diskteki arşiv belgeleri (kuveyt-turk
232, turkiye-finans 3, ziraat 1, albaraka 1) önceki turlardan **duruyor,
silinmedi**. Arşiv turu ayrıca koşulmalı.

---

## 8. Kalite kapıları

| kapı | sonuç |
|---|---|
| `.venv/bin/python -m pytest tests -q` | **3.373 geçti** (tur öncesi 3.275), 53 atlandı, **1 başarısız** — §7.2 |
| `app/.venv/bin/ruff check .` (repo kökü) | **All checks passed!** |
| `robots.txt` uyumu | KORUNDU — `--ignore-robots` hiç kullanılmadı, 741 aday atlandı ve sayıldı (koşuda denenen 362) |
| Alan adı başına gecikme | 3,0 sn (değiştirilmedi), paralel istek yok |
| Provenance | her yeni belgede `source_url` + `scraped_at` + `content_hash` + `collection_method` |
| Silinen dosya | **0** (`git status --porcelain`: `data/raw` altında 1.556 yeni, 393 güncel, 0 silme) |
| Commit | **atılmadı** (ana oturumun işi) |

---

## Sources
- `data/raw/_extra_report.md` — belge turunun otomatik raporu (bu turda üretildi)
- `data/raw/_collection_report.md` — kampanya turunun otomatik raporu
- `config/banks.yaml` — her değişiklik gerekçesiyle satır içinde belgelendi
- `docs/rapor/banka-siteleri-veri-kaynagi-haritasi.md` — 2026-08-03 aday sayıları
- `docs/rapor/devam-konut-tasit-hasati.md` — klasik banka korpusundaki kardeş tur
- `docs/rapor/suresi-dolmus-damgasi.md` — damga deseni ve ölçümleri
- `docs/rapor/boilerplate-kapsam.md` — Türkiye Finans şablon şişmesi ölçümü

## Related
- `docs/rapor/bayat-veri-mutabakati.md` — damga/bayatlık döngüsünün tamamı
- `docs/rapor/musaraka-veri-boslugu.md` — "olmayan kaynak" ayrımının emsali
