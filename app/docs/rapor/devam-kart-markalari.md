# Devam Notu — Katılım Bankalarının Kart Markası Alan Adları

> 2026-08-04. İlgili: `config/banks.yaml` · `data/raw/**` ·
> `src/scraping/discover.py` (`same_site`, `_host`) · `src/scraping/fetcher.py`
> (`StaticFetcher`, `BrowserFetcher`)
>
> Hipotez: *"kampanyaların bir kısmı bankanın ana sitesinde değil kart
> markasının ayrı sitesinde yayımlanıyor, bu kaynak kaçıyor."*
> **Doğrulandı** — ama beklenen bankalarda değil, ve beklenen alan adlarıyla değil.

---

## 1. Görevin öncülü yanlıştı — düzeltildi

Görev `vakifkart.com.tr`'nin "çözülmediğini" bildirmişti. Doğru; ama sebebi
alan adının değişmesi değil, **öyle bir markanın hiç olmaması**.

Vakıf Katılım'ın kart markası **VKart**'tır (site haritasından ölçüldü:
`/kartlar/kredi-karti/vkart`, `/kartlar/banka-karti/vkart-debit`,
`/isim-icin/ticari-kartlar/kredi-karti/vkart-business`). VKart'ın ayrı sitesi
yoktur; kampanyaları ana alanda kalır.

---

## 2. Bulunan alan adları (tam URL + HTTP durumu)

Hepsi **bankanın kendi sayfasındaki gerçek bağlantı izlenerek** bulundu; hiçbiri
tahmin edilmedi.

| Banka | Kart markası | Kampanya kataloğu URL'i | HTTP | Nasıl bulundu |
|---|---|---|---:|---|
| Türkiye Finans | **Happy Kart** | `https://www.happycard.com.tr/kampanyalar/Sayfalar/default.aspx` | 200 | `/tr-tr/bireysel/Sayfalar/kredi-kartlari.aspx` sayfasındaki Happy Silver/Gold/Platinum bağlantıları |
| Albaraka Türk | **Worldcard** | `https://www.albaraka.com.tr/tr/world-dunyasi/kampanyalar` | 200 | Toplanmış `data/raw/albaraka/live/tr-kampanyalar.html` içindeki "Worldcard Kampanyaları" düğmesi (`albarakaworldcard.com/kampanyalarimiz` → 301) |
| Albaraka Türk | **Albaraka Özel** kartları | `https://www.albarakaozel.com/tr/ayricaliklar` | 200 | Ham korpusta 153 referans + sitenin kendi gezinme menüsü |
| Kuveyt Türk | **Miles&Smiles Kuveyt Türk** | `https://milesandsmiles.kuveytturk.com.tr/kampanyalar` | 200 | Ham korpusta 13 referans; ana alanın `/kartlar/kredi-karti/milesandsmiles-kuveyt-turk-kart` ürünü |
| Kuveyt Türk | **Sağlam Kart** | `https://saglamkart.kuveytturk.com.tr/kampanyalar` | 200 | Önceki turda eklenmişti; bu turda **hiç belge üretmediği** ölçüldü ve düzeltildi |

### Alan adı biçimi tuzakları (ölçülmüş)

- `happycard.com.tr` **çıplak alan adı 404 verir**, `www.` zorunludur.
  `extra_hosts`a yine de `happycard.com.tr` yazıldı, çünkü `discover._host()`
  karşılaştırma öncesi `www.` ekini atıyor.
- `albarakaworldcard.com` **ayrı site değil**: 301 ile
  `www.albaraka.com.tr/tr/world-dunyasi/...` altına düşüyor. Bu yüzden
  `extra_hosts`a yazılmadı — aynı kayıtlı alan.
- `saglamkart.*` ve `milesandsmiles.*` **alt alanlardır**; `same_site()`
  `a.endswith("." + b)` kuralıyla onları zaten tolere ediyor → `extra_hosts`
  gereksiz. `happycard.com.tr` ve `albarakaozel.com` ise **ayrı kayıtlı
  alanlar** → `extra_hosts` ZORUNLU (yoksa sayfa ve ondan çıkan tüm bağlantılar
  atılır).

---

## 3. Denenmiş ve BAŞARISIZ alan adları — tekrar denemeyin

### 3a. DNS'te yok / bağlantı kurulamıyor (curl HTTP 000)

| Alan adı | Neden denendi | Sonuç |
|---|---|---|
| `vakifkart.com.tr` | Görev tanımındaki öncül | HTTP 000, zaman aşımı |
| `vkart.com.tr` | Vakıf Katılım'ın gerçek marka adı VKart | HTTP 000 |
| `vkartdunyasi.com.tr` | "…dünyası" kalıbı (worlddunyasi/happy dünyası benzeri) | HTTP 000 |
| `vkartdunyasi.com` | aynı | HTTP 000 |
| `happykart.com.tr` | Happy markasının Türkçe yazımı | HTTP 000 |

`vkart.com` **çözülüyor (HTTP 200)** ama Vlad Kononov adlı kişinin kişisel
sitesidir — alan adı benzerliğine aldanılmamalı.

### 3b. Ayakta ama ATIF nedeniyle bilinçli REDDEDİLDİ

Bunlar teknik olarak toplanabilir; eklenmedi çünkü **konvansiyonel bankaların
kampanyalarını katılım bankasına atfederler** (korpus zehirlenmesi).

| Alan adı | Sahibi | HTTP | robots | Ret gerekçesi (ölçülmüş) |
|---|---|---:|---|---|
| `bankkart.com.tr` | Ziraat Bankası | 200 | `Allow: /` | Ana sayfada "katılım" **0 kez** geçiyor. Ziraat Katılım korpusundaki tek referans anlaşmalı mağaza listesi PDF'i (`medium/document-file-129.vsf`), kampanya kataloğu bağlantısı değil |
| `paraf.com.tr` | Halkbank | 200 | yok | Ana sayfada "katılım" **0 kez** geçiyor. Emlak Katılım ve Dünya Katılım kartları gerçekten Paraf ("Emlak Katılım Paraf Kredi Kartı") ama Paraf ORTAK program; bankaların kart sayfaları paraf.com.tr'ye **hiç bağlantı vermiyor** |
| `worldcard.com.tr` | Yapı Kredi | 200 | — | Albaraka World kartı satıyor ama kendi kart sayfalarından buraya bağlantı yok; Albaraka'nın World kampanyaları **kendi alanında** (`/tr/world-dunyasi/`) yayımlanıyor — doğru kaynak o |
| `bonus.com.tr`, `maximum.com.tr`, `axess.com.tr`, `cardfinans.com.tr` | Garanti/İş/Akbank/QNB | 200 | — | Hiçbir katılım bankasının sayfasından referans verilmiyor (10 bankanın 1684 belgelik ham korpusunda 0 geçiş) |

### 3c. Kart markası ARANDI, YOK (`null`)

| Banka | Kart markası | Ayrı site |
|---|---|---|
| Vakıf Katılım | VKart | **yok** (§1) |
| Ziraat Katılım | Aile Kart / Bağımsız Kart / Sanal Kart | **yok** — kampanyalar `/kart-kampanyalari` altında |
| Türkiye Emlak Katılım | Emlak Katılım Paraf | **yok** (kendi sitesi; Paraf ortak program, §3b) |
| Dünya Katılım | Dünya Katılım Paraf | **yok** (aynı) |
| Hayat Finans | HayatPay | zaten `extra_hosts`ta (`hayatpay.com.tr`) |
| T.O.M. Katılım | Hadi | zaten `extra_hosts`ta (`tombankhadi.com`) |
| Adil Katılım | — | banka henüz kart/kampanya yayımlamıyor |

### 3d. Boş çıkan arşiv yolları

`saglamkart.kuveytturk.com.tr/kampanyalar/biten-kampanyalar` ve
`milesandsmiles.kuveytturk.com.tr/kampanyalar/biten-kampanyalar` **0 kampanya
bağlantısı** döndürüyor (`?isArchived=true` sorgusuyla da 0). `archive_paths`a
eklenmedi. Yanlış "aktif" etiketi riski yok: `DEFAULT_ARCHIVE_PATTERNS`
içindeki `biten-kampanya` deseni bu URL'leri aktif turdan zaten eliyor.

---

## 4. `scrape_mode` — Türkiye Finans `static` → `js` (ÖLÇÜMLE)

Depodaki kural: *`js`'e geçmeyi ölçmeden önerme.* Ölçüldü, iki bağımsız sebeple
geçildi.

### Sebep 1 (zorunlu): `happycard.com.tr` TLS zinciri eksik

Sunucu el sıkışmada **yalnızca yaprak sertifikayı** gönderiyor, ara sertifikayı
(`DigiCert Global G2 TLS RSA SHA256 2020 CA1`) göndermiyor:

```
openssl s_client → Verify return code: 21 (unable to verify the first certificate)
requests+certifi → SSLError: CERTIFICATE_VERIFY_FAILED
                   unable to get local issuer certificate
```

`curl` (macOS anahtar zinciri, ara sertifikayı AIA ile kendi çekiyor) ve
Playwright **başarılı**. `StaticFetcher` ise düşüyor ve `collect_live` bunu
`blocked` listesine yazıp sessizce geçiyor → 10 kampanya belgesi hiç
toplanmazdı. Aynı bankanın ana alanı (`www.turkiyefinans.com.tr`) sorunsuz
(`Verify return code: 0`), yani sorun banka geneli değil bu tek alan.

`verify=False` YAPILMADI: doğrulamayı kapatmak tüm alanlar için güvenlik
gerilemesidir ve `src/scraping/fetcher.py` bu turun kapsamı dışıydı.

### Sebep 2 (destekleyici): `js` ana sitede de kayıp vermiyor

| Sayfa | static bağlantı | js bağlantı | statik-fazlası |
|---|--:|--:|--:|
| `/tr-tr/kampanyalar/Sayfalar/default.aspx` | 11 | **12** | 0 |
| `/tr-tr/kampanyalar/Sayfalar/kart-kampanyalari.aspx` | 12 | **14** | 0 |

Metin de artıyor (6506 → 8163 krkt) çünkü liste kartları geç yükleniyor.
`js`-only bulunanlar gerçek sayfalar: `kobi-kampanyalari.aspx`,
`turkiye-finans-avantajlariyla-mobilden-tanis.aspx`.

`js` ayrıca `fetch_all_pages`i etkinleştiriyor. Yan etki kontrol edildi: TF liste
sayfalarında sayfalama widget'ı yok (`sayfa=1`), `biten-kampanyalar.aspx`'te 21
arşiv bağlantısı görüyor. Bedel yalnızca hız.

### Diğer bankalarda `js`'e geçilmedi

`albarakaozel.com`, `/tr/world-dunyasi/kampanyalar`, `saglamkart.*`,
`milesandsmiles.*` liste sayfalarında static ve js **birebir aynı** sayıda
bağlantı buldu (`jsFazla=0`, `staticFazla=0`): 11, 37, 10, 9. Gövde sunucuda
render ediliyor — önceki turların bulgusuyla tutarlı.

---

## 5. Doğrulama hasatı — 77 yeni belge, mükerrer YOK

Yeni giriş noktaları gerçekten hasat edildi (sitemap kapalı, yalnızca yeni yollar),
belgeler `data/raw/<slug>/live/` altına yazıldı.

| Banka | Keşfedilen | Belge | Tekil hash | Engellenen | Yeni dosya |
|---|--:|--:|--:|--:|--:|
| albaraka | 52 | 52 | **52** | 0 | 48 |
| kuveyt-turk | 19 | 19 | **19** | 0 | 19 |
| turkiye-finans | 11 | 11 | **11** | 0 | 10 |

Kaynak bazında yeni belge: `world-dunyasi/detay/` **37** · `albarakaozel/tr/ayricalik/`
**11** · `happycard.com.tr` **10** · `saglamkart` **10** · `milesandsmiles` **9**
= **77 yeni `.txt`** (+ 77 `.meta.json`; `.html` `.gitignore`'da).

### "Aynı liste metni her sayfaya" tuzağı — YOK

Her belgenin temiz metni SHA-1'lendi: **82 belge → 82 tekil hash, 0 mükerrer.**
Karakter aralığı 765–8624; hepsinde en az bir içerik sinyali (`%\d`, `\d+ TL`,
`taksit`, `vade`, `kâr payı`). Yani liste metni detay sayfalarına kopyalanmıyor.

`collect_live` ayrıca temiz metin üzerinden tekilleştirme yapıyor (`_text_key`),
yani `world-dunyasi/detay/...worldpuan`, `..._1`, `..._2`, `..._3` varyantları aynı
gövdeyi paylaşsaydı teke inecekti — inmediler, gerçekten farklı metinler.

### Beklenen ama zararsız çıkan tekrar: aynı kampanya iki kart programında

`saglamkart` ve `milesandsmiles` aynı üye işyeri kampanyasını farklı ID ile
yayımlıyor (Beymen 3136/2166, Hantech 3134/2164, Vatan 2598/1602, Wome 2890/1870).
Metinler FARKLI (kart programına özgü koşullar, 765–1661 krkt) ve `_text_key`
onları ayrı tuttu. Bu doğru davranış: iki ayrı kartın koşulları ayrı belgedir.
Karşılaştırma katmanı bunları "aynı kampanya" saymamalı — CLAUDE.md §17 adil-kıyas
açısından izlenmesi gereken bir nokta.

---

## 5b. BULUNAN VE ONARILAN HATA: dosya adı çakışması korpusu bozdu

Hasat sırasında **gerçek veri kaybı** ölçüldü ve geri alındı.

`collector.url_to_slug` yalnızca yolun son parçalarını kullanıyor, alan adını
kullanmıyor. Bu yüzden:

```
www.turkiyefinans.com.tr/tr-tr/kampanyalar/Sayfalar/default.aspx  → kampanyalar-default
www.happycard.com.tr/kampanyalar/Sayfalar/default.aspx            → kampanyalar-default
```

happycard'ın liste sayfası (2777 krkt) Türkiye Finans'ın **ANA kampanya listesini**
(6506 krkt) ezdi; `.meta.json` içindeki `source_url` bile happycard'a döndü.
Sessiz kayıptı — hiçbir hata/uyarı üretmedi.

**Neden kaçtı:** `save_docs` çakışmayı yalnızca **aynı çağrı içinde** `-2` ekiyle
çözüyor (`used` kümesi). Ayrı çağrılar arasında üzerine yazıyor. Tek bir tam
hasatta (her iki URL aynı `docs` listesinde) kayıp OLMAZDI; bu tur doğrulamayı
banka bazında ayrı çağrılarla yaptığı için tetiklendi.

**Onarım (yapıldı):**
1. `kampanyalar-default.txt` + `.meta.json` `git checkout` ile geri alındı.
2. `.html` `.gitignore`'da olduğu için geri alınamadı (diskte happycard'ın HTML'i
   kalmıştı) → o tek URL yeniden hasat edilerek `.html`/`.txt`/`.meta.json`
   üçlüsü tutarlı hale getirildi. Yeni değer **8175 krkt** (js modu 6506'dan
   fazlasını görüyor, §4 ile tutarlı), `source_url` doğru, HTML'de 137
   `turkiyefinans` referansı ve **0** `happycard`.
3. Tekrarı önlemek için `turkiye-finans`a `exclude_patterns` eklendi:
   `happycard\.com\.tr/kampanyalar/Sayfalar/default\.aspx`.
   Doğrulandı (`matches()` ile ölçüldü): TF'nin kendi `default.aspx`i **belge**,
   happycard'ın `default.aspx`i **belge değil**, happycard'ın detay sayfaları
   **belge**. Kayıp yok — `_listing_pages` exclude'a bakmadığı için sayfa gezinme
   girişi olarak hâlâ kullanılıyor ve 10 detay eksiksiz geliyor.

**Yan hasar (kabul edildi):** geri alma sırasında 4 `.meta.json`'daki
`reextracted_at` / `extraction_result` alanları düştü (3'ü sonra tamamen geri
alındı, `kampanyalar-default` yeniden hasat edildiği için onda yok). Bu alanlar
yalnızca "yeniden çıkarım denendi, `degisim_yok`" kaydıydı; `text_chars` ve
`content_hash` etkilenmedi.

**Kapatılmayan risk (kapsam dışı):** `url_to_slug` alan adını hesaba katmıyor.
Aynı desen başka `extra_hosts` alanlarında da tekrarlayabilir (ör. iki alanda da
`/kampanyalar` veya `/kampanyalar/detay/aynislug`). Kalıcı çözüm
`src/scraping/collector.py`de slug'a alan adı önekini eklemektir; bu tur yalnızca
`config/`, `data/raw/`, `docs/rapor/` yollarına yazma yetkisiyle çalıştı.

---

## 6. `config/banks.yaml` değişiklikleri

| Banka | Değişiklik | max_docs |
|---|---|---|
| kuveyt-turk | `campaign_paths` += milesandsmiles kataloğu | 320 → **340** |
| albaraka | `campaign_paths` += `/tr/world-dunyasi/kampanyalar`, albarakaozel; `extra_hosts` += `albarakaozel.com`; `detail_patterns` += `/tr/world-dunyasi/detay/`, `/tr/ayricalik/` | 120 → **180** |
| turkiye-finans | `scrape_mode` static → **js**; `campaign_paths` += happycard kataloğu; `extra_hosts` += `happycard.com.tr`; `detail_patterns` += `/kampanyalar/Sayfalar/`; `exclude_patterns` += happycard liste sayfası (§5b) | 80 → **100** |
| vakif-katilim, ziraat-katilim, turkiye-emlak-katilim, dunya-katilim | yalnız **yorum**: denenmiş-başarısız alan adları + ret gerekçeleri | — |

`detail_patterns` eklemesi Albaraka için **kritik**: yol eklemek tek başına
yetmiyordu, çünkü desene uymayan URL "gezinme başlangıcı" sayılıp belge olarak
kaydedilmiyor. Bu yüzden 48 detay sayfası (37 + 11) korpusa hiç girmemişti.

Doğrulama: `config.load_banks` her iki ayrıştırıcı yolunda da (pyyaml **ve**
`_mini_parse` yedeği) 10 bankayı hatasız okuyor.

---

## 7. Açık kalanlar (sonraki tur)

1. **Tam hasat yapılmadı.** Bu turda yalnızca yeni giriş noktaları gezildi
   (sitemap kapalı, banka başına sınırlı tavan). `python -m src.scraping.run` ile
   tam tur atıldığında §5'teki 77 belgenin korunduğu ve §5b'deki çakışmanın
   tekrarlamadığı teyit edilmeli.
1b. **`url_to_slug` alan adını yok sayıyor** — §5b'deki kalıcı risk. Kapsam
   dışında bırakıldı, `collector.py` sahibi agent'a devredilmeli.
2. **Türkiye Finans `js` hasat süresi ölçülmedi.** Tam turun ne kadar
   uzadığı bilinmiyor; kabul edilebilir sınırı aşarsa doğru çözüm `js`'ten geri
   dönmek DEĞİL, `fetcher.py`ye alan başına ara-sertifika/CA paketi eklemek
   (bu tur kapsam dışıydı).
3. **`albaraka` arşiv tarafı bakılmadı.** `/tr/world-dunyasi/kampanyalar`
   listesinde "Geçmiş Kampanyalar (605)" ifadesi görüldü. 605 süresi dolmuş
   kampanya `suresi_dolmus_kampanya` kuralı için hazır etikettir; hangi URL'de
   sayfalandığı henüz ölçülmedi.
4. **Segment alan adları incelenmedi.** Ham korpusta yoğun referanslı, ayrı
   kayıtlı ve kampanya taşıması muhtemel alanlar: `turkiyefinansala.com` (113
   referans, Türkiye Finans Ala), `ziraatkatilimozelbankacilik.com.tr` (275),
   `ziraatdinamik.com.tr` (275). Bunlar kart markası değil **segment** markası
   olduğu için bu turun kapsamı dışında tutuldu; hepsi HTTP 200 dönüyor.
5. **`saglamkart` neden 0 belge üretti sorusu kapatılmadı.** Yol önceki turda
   eklenmiş ama korpusta 0 belge var; en olası açıklama eklemeden sonra hiç tam
   hasat çalıştırılmamış olması. Tam tur bunu doğrulayacak.
