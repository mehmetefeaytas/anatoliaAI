# Bayat Veri Döngüsü — Mutabakat Raporu (2026-08-10)

> Koşulan döngü: `src.scraping.snapshot build` → `snapshot diff` →
> `src.scraping.reconcile_stale` (önce kuru koşu, sonra kısmî uygulama).
> Ham veri yalnızca `reconcile_stale.apply_moves` ile taşındı; **hiçbir dosya
> silinmedi**. `data/demo.db`'ye dokunulmadı.

---

## 1. Sorun ve döngünün ne yaptığı

Yeniden hasat `data/raw/` altındaki dosyaları **silmez, üzerine yazar**
(`snapshot.py::build_manifest` docstring'i). Sitede artık olmayan bir kampanya bu
yüzden `live/` altında öylece kalır. `live/` "şu an aktif" anlamına geldiği için
bu, adil kıyası (CLAUDE.md §17) doğrudan bozar: kapanmış bir kampanya açık bir
kampanyayla aynı kolonda sıralanır.

Döngü bunu üç adımda çözer:

1. **Manifest** — `.meta.json` sidecar'larından URL + `scraped_at` + temiz metin
   özeti çıkarılır.
2. **Fark** — son tam turda YENİDEN GÖZLENMEMİŞ belgeler `kayip` kümesine düşer.
3. **Mutabakat** — her `kayip` URL **yeniden çekilir** ve karar kanıta bağlanır.
   Körlemesine "expired" etiketlemek veri uydurmak olurdu (CLAUDE.md §19).

### Kullanılan kesme noktası ve neden bu

Korpustaki `scraped_at` dağılımı:

| Gün | Belge | Kapsam |
|---|---:|---|
| 2026-07-30 | 61 | ilk tur artıkları |
| **2026-08-03** | **1619** | **son TAM tur — 10 bankanın hepsi** |
| 2026-08-04 | 79 | kısmî yeniden hasat (albaraka, kuveyt-turk, turkiye-finans) |
| 2026-08-08 | 13 | yalnız PDF turu (albaraka, tkbb) |

`since` eşiği **2026-08-03T16:00:00+00:00** seçildi. Gerekçe: 08-03 turu
16:28:07–18:03:51 arasında koştu, 07-30 turu ise 20:29:46'da bitti — iki küme
saat düzeyinde temiz ayrılıyor. **08-04 veya 08-08 eşik seçilseydi**, o turlarda
yer almayan yedi banka toptan "kaybolmuş" görünürdü; bu, raporda aranması istenen
yanlış pozitifin ta kendisi olurdu. Kısmî turlar eşiğin üstünde kaldığı için
yalnızca `after` kümesini büyütür, yanlış pozitif üretmez.

| Manifest | Kayıt | live |
|---|---:|---:|
| `2026-08-10-korpus-tam.json` (before, süzgeçsiz) | 1772 | 808 |
| `2026-08-10-son-tam-tur.json` (after, `--since`) | 1711 | 750 |

Fark: **kayip 61 · yeni 0 · degisti 0 · ayni 1702.** 61 kaybın 58'i `live/`
kümesinde; `reconcile_stale` varsayılan olarak yalnız `live/`'ı doğrular.

---

## 2. Kuru koşu sonucu

`data/snapshots/mutabakat-2026-08-10-kuru.md` · 58 URL yeniden çekildi
(domain başına 3 sn, robots.txt açık, açıklayıcı User-Agent).

| Karar | Adet | Anlamı |
|---|---:|---|
| `gecersiz_kilindi` | 35 | Aynı URL yeni turda `archive/` altında TAZE hâliyle var → `live/` kopyası mükerrer |
| `kesif_acigi` | 17 | HTTP 200, bitmiş görünmüyor → **dokunulmaz**, keşif açığı |
| `suresi_dolmus` | 5 | Sayfa kendini bitmiş ilan ediyor (regex) |
| `kaldirilmis` | 1 | HTTP 404 |
| `dogrulanamadi` | 0 | — |

Banka bazında:

| Banka | `gecersiz_kilindi` | `suresi_dolmus` | `kaldirilmis` | `kesif_acigi` |
|---|---:|---:|---:|---:|
| kuveyt-turk | 33 | — | — | — |
| turkiye-emlak-katilim | — | — | — | 13 |
| turkiye-finans | 1 | 3 | — | — |
| vakif-katilim | — | 2 | — | 2 |
| albaraka | — | — | 1 | 1 |
| ziraat-katilim | 1 | — | — | — |
| tom-katilim | — | — | — | 1 |

`dogrulanamadi: 0` — 58 isteğin hiçbiri ağ/5xx hatasıyla dönmedi. Yani
"geçici bir ağ hatası bütün bir bankayı kapanmış gösteriyor" senaryosu bu koşuda
gerçekleşmedi.

---

## 3. Yanlış pozitif denetimi — `suresi_dolmus` kararlarının HEPSİ hatalı

Kuru koşu makul görünüyordu; kararı kanıtına kadar takip edince görünüm değişti.

`verify_stale`, sayfanın kendini bitmiş ilan edip etmediğini `SELF_EXPIRED`
düzenli ifadesiyle **ham HTML'in tamamında** arıyor
(`reconcile_stale.py:181` → `SELF_EXPIRED.search(r.html or "")`).

**Kontrol grubu deneyi.** 5 adayın yanına, aynı bankaların son tam turda
toplanmış ve canlı sayılan sayfalarından örnek eklenip aynı regex koşuldu:

| Banka | Eşleşen metin | Adaylar | Kontrol grubu |
|---|---|---|---|
| turkiye-finans (3) | `<a href="…/Biten-Kampanyalar.aspx">Biten Kampanyalar</a>` — **site menüsü** | 3/3 eşleşti | **3/3 eşleşti** |
| vakif-katilim (2) | "…kampanyayı durdurma, **sona erdirme**, … hakkını saklı tutar" — **kalıp hukuk metni** | 2/2 eşleşti | 0/3 |

Türkiye Finans'ta eşleşme, sayfanın durumuyla hiç ilgisi olmayan **gezinti
menüsündeki bağlantı**; her sayfada var. Vakıf Katılım'da eşleşme, bankanın
kampanyayı sonlandırma **hakkını saklı tuttuğunu** söyleyen kalıp cümle — yani
"bitti"nin tam tersi.

**Korpus genelinde ölçüm.** Aynı regex, son tam turda toplanmış ve dolayısıyla
canlı sayılan 750 `live/` belgesinin ham HTML'ine uygulandı:

| Banka | live belge | regex eşleşti | oran |
|---|---:|---:|---:|
| turkiye-finans | 41 | 31 | %75,6 |
| dunya-katilim | 59 | 38 | %64,4 |
| ziraat-katilim | 215 | 102 | %47,4 |
| tom-katilim | 12 | 2 | %16,7 |
| albaraka | 89 | 13 | %14,6 |
| vakif-katilim | 86 | 4 | %4,7 |
| adil / hayat / kuveyt-turk / emlak | 337 | 0 | %0 |
| **TOPLAM** | **750** | **190** | **%25,3** |

Bu 190 belgenin hepsi bugün `kayip` kümesine düşseydi, hepsi `suresi_dolmus`
damgasıyla arşive taşınırdı. **Kusur gerçek ve ölçülmüş.**

### Kusurun kökü

`SELF_EXPIRED`, `comparison/contradiction.py::_SELF_EXPIRED`'ten alınıyor — orada
**temiz metin** (`campaign.raw_text`) üzerinde ve **koruma amaçlı** (bulguyu
bastırmak için) kullanılıyor; yanlış eşleşmenin maliyeti bir bulgunun
kaçırılması. `reconcile_stale` aynı ifadeyi **ham HTML** üzerinde ve **karar
amaçlı** kullanıyor; yanlış eşleşmenin maliyeti canlı bir belgenin arşive
gömülmesi. Aynı desen, iki farklı girdi türü, iki farklı hata yönü.

### Önerilen düzeltme — UYGULANMADI, karar sizin

`src/scraping/**` yalnız gerçek kusurda ve **önce raporlanarak** değiştirilebilir
dendiği için kodu değiştirmedim. Somut öneri:

1. Aramayı ham HTML'de değil, `collector._extract_main_text(r.html)` çıktısında
   yap — gezinti menüsü (Türkiye Finans'ın %75,6'sı) böylece elenir.
2. Kalıp metni ele: eşleşmenin ±250 karakterinde `saklı tutar` / `hakkını sakl`
   varsa kararı verme.
3. Karar için `_SELF_EXPIRED`'i değil, **damga niteliğinde** dar bir desen kullan:
   `bu kampanya sona ermiştir` · `kampanya süresi dolmuştur` ·
   `sona erdi bitiş tarihi` · `<tarih> tarihinde sona ermiştir`.
   Bu dar desenin kontrol grubundaki 750 belgede ürettiği eşleşmelerin tamamı
   elle bakıldığında gerçek damga çıktı (bkz. §5).
4. Ayırt edilemeyen durumda `dogrulanamadi` de; `suresi_dolmus` deme.

Test önerisi: Türkiye Finans menüsünü ve Vakıf Katılım kalıp cümlesini içeren iki
kısa HTML parçacığıyla, kararın `suresi_dolmus` **olmadığını** doğrulayan bir
regresyon testi.

### Tek gözlemin yeterli olmadığına dair ikinci bulgu

Tek `kaldirilmis` kararını uygulamadan önce yeniden doğruladım. **İkinci gözlem
404 değil `RemoteDisconnected` döndü.** `verify_stale` her URL'i bir kez çekiyor
ve yeniden deneme yok; o an bu URL doğrulansaydı `dogrulanamadi` çıkardı.
Dört gözlem + kontrol sayfası:

| Deneme | Aday URL | Bankanın kampanya listesi (kontrol) |
|---|---|---|
| kuru koşu | HTTP 404 | — |
| 1 | `RemoteDisconnected` | — |
| 2 | HTTP 404 | HTTP 200 |
| 3 | HTTP 404 | HTTP 200 |
| 4 | HTTP 404 | HTTP 200 |

3/4 gözlem 404, banka sitesi her seferinde ayakta → **kaldırılma doğrulandı**.
Ama bu, `verify_stale`'in tek gözleme dayanmasının kırılgan olduğunu gösteriyor:
öneri, `kaldirilmis` ve `suresi_dolmus` kararları için 2 gözlem şartı (ör.
`--confirm 2`) ya da en azından ağ hatasında bir kez yeniden deneme.

---

## 4. Uygulanan alt küme

Kuru koşunun **doğrulanmış-güvenli** alt kümesi uygulandı; `suresi_dolmus`
kararları (5 belge) yanlış pozitif olduğu gösterildiği için **taşınmadı**,
belgeler `live/` altında kaldı ve kararları raporda duruyor.

| Karar | Adet | Uygulandı mı |
|---|---:|---|
| `gecersiz_kilindi` | 35 | **evet** |
| `kaldirilmis` | 1 | **evet** (4 gözlemle doğrulandı) |
| `suresi_dolmus` | 5 | **hayır** — §3 |
| `kesif_acigi` | 17 | hayır (zaten dokunulmaz) |
| `dogrulanamadi` | 0 | — |

- **36 belge**, **108 dosya** taşındı (`.txt` + `.html` + `.txt.meta.json`).
- Taşıma `apply_moves` ile: `live/` → `archive/`; ad çakışmasında `-onceki-2`
  soneki, üzerine yazma yok.
- Her taşınan `.meta.json`'a `campaign_status: expired` + `removal_check` kanıt
  bloğu (karar, HTTP kodu, gerekçe, `checked_at`, `moved_from`) yazıldı.
- **Silme yok:** korpus toplamı taşımadan önce ve sonra **1772 belge**.

### Korpusun banka bazında değişimi

| Banka | live önce | live sonra | Δ | arşiv önce | arşiv sonra |
|---|---:|---:|---:|---:|---:|
| kuveyt-turk | 186 | 153 | −33 | 199 | 232 |
| albaraka | 91 | 90 | −1 | 0 | 1 |
| turkiye-finans | 45 | 44 | −1 | 2 | 3 |
| ziraat-katilim | 216 | 215 | −1 | 0 | 1 |
| adil-katilim | 6 | 6 | 0 | 0 | 0 |
| dunya-katilim | 59 | 59 | 0 | 0 | 0 |
| hayat-finans | 13 | 13 | 0 | 0 | 0 |
| tom-katilim | 13 | 13 | 0 | 0 | 0 |
| turkiye-emlak-katilim | 89 | 89 | 0 | 0 | 0 |
| vakif-katilim | 90 | 90 | 0 | 0 | 0 |
| **TOPLAM** | **808** | **772** | **−36** | **201** | **237** |

Kuveyt Türk'ün 33'ü tek bir vakadan: Temmuz turunda bankanın **arşiv** sayfaları
`live/` altına toplanıyordu. Arşiv dışlama düzeltmesinden sonra aynı URL'ler
`archive/` altına taze hâliyle yazıldı; eski `live/` kopyaları mükerrer kaldı.
URL'lerin hepsi `…/kampanyalar/kampanya-arsivi/…` yolunda — yani karar ağdan
değil, korpusun kendi kanıtından geliyor.

---

## 5. Asıl risk döngünün kapsamı DIŞINDA: `live/` altındaki 231 bitmiş kampanya

Bayat döngüsü yalnızca **kaybolan URL'leri** yakalar. Ama bir kampanya
kaybolmadan da bitebilir: banka sayfayı yayında bırakıp üstüne "sona ermiştir"
damgası basar. Bu belgeler her turda yeniden toplanır, `kayip` kümesine hiç
düşmez, dolayısıyla `reconcile_stale` onlara **hiçbir zaman** ulaşamaz.

Uygulama sonrası 772 `live/` belgesinin temiz metninde damga niteliğinde dar
desen arandığında:

| Banka | live belge | kendini "bitmiş" ilan eden | oran |
|---|---:|---:|---:|
| vakif-katilim | 90 | 81 | %90,0 |
| dunya-katilim | 59 | 38 | %64,4 |
| ziraat-katilim | 215 | 102 | %47,4 |
| albaraka | 90 | 10 | %11,1 |
| adil / hayat / kuveyt-turk / emlak / tom / turkiye-finans | 318 | 0 | %0 |
| **TOPLAM** | **772** | **231** | **%29,9** |

Örnek damgalar (temiz metinden birebir):

- `Kampanya 24-05-2026 Tarihinde Sona Ermiştir.` (ziraat-katilim)
- `Kampanya Geçerlilik Tarihi Kampanya Süresi Dolmuştur` (vakif-katilim)
- `Paraf Kampanyaları Sona erdi Bitiş Tarihi: 31 Temmuz 2026` (dunya-katilim)
- `Bu kampanya sona ermiştir.` (albaraka)

Damgadaki bitiş tarihi okunabilen 140 belgenin dağılımı:

| Bitiş ayı | Belge | | Bitiş ayı | Belge |
|---|---:|---|---|---:|
| 2025-06 … 2025-12 | 25 | | 2026-04 | 5 |
| 2026-01 | 1 | | 2026-05 | 20 |
| 2026-02 | 2 | | 2026-06 | 24 |
| 2026-03 | 9 | | 2026-07 | 54 |

Yani bankalar bitmiş kampanyayı **aylarca, kimi zaman bir yıldan uzun süre**
yayında bırakıyor. `live/` kümesinin yaklaşık **üçte biri** şu anda kapanmış
kampanya — ve bu, döngü ne sıklıkla koşulursa koşulsun düzelmez.

**Öneri (uygulanmadı, `src/` ve `data/` sınırlarını aşıyor):** hasat sırasında
veya ayrı bir geçişte, dar damga deseniyle eşleşen `live/` belgeleri
`campaign_status: expired` ile işaretlensin. Taşımaya bile gerek yok — kıyas
motoru `campaign_status`'a bakarak bunları sıralama dışında tutabilir. Bu, adil
kıyas açısından bu raporda taşınan 36 belgeden **altı kat** daha büyük bir
düzeltmedir. Kararı size bırakıyorum; ölçüm yukarıda.

---

## 6. Keşif açığı — bedava teşhis

17 URL HTTP 200 dönüyor, bitmiş görünmüyor, ama son tam tur onları bulamadı.
Bunlar süresi dolmuş değil; `banks.yaml` giriş noktalarının / `detail_patterns`
/ `max_docs` kırpmasının kaçırdığı sayfalar.

| Banka | Kaçırılan | Not |
|---|---:|---|
| turkiye-emlak-katilim | 13 | Hepsi `/bireysel/kampanyalar/kampanya/…` yolunda, Paraf/ParafPara kampanyaları — tek bir aile toptan kaçırılmış, kırpma sırası şüphelisi |
| vakif-katilim | 2 | `/kendim-icin/kampanyalar/detay/…` |
| albaraka | 1 | Aşağıdaki nota bak |
| tom-katilim | 1 | `tombankhadi.com` — `extra_hosts` kapsamı |

**Albaraka'nın slug ikizi.** `kaldirilmis` çıkan URL ile `kesif_acigi` çıkan URL
tek harf farklı:

- `…/albaraka-restoran-harcamaniza-5-indirim-kazandiriyor` → **404**
- `…/albaraka-restoran-harcamaniza-5-indirim**m**-kazandiriyor` → **200**

Banka aynı kampanyayı yazım hatalı bir adrese taşımış. Doğru davranış üretildi:
ölü URL arşive gitti, yaşayan kopya `live/` altında kaldı — mükerrer kayıt oluşmadı.

---

## 7. Etik ve teknik uyum

- **robots.txt**: `RobotsCache` açık, `--ignore-robots` **kullanılmadı**. Kuru
  koşuda robots nedeniyle atlanan URL çıkmadı.
- **Hız sınırı**: domain başına 3,0 sn (`--delay 3.0`), CLAUDE.md §14'ün 2–5 sn
  bandında. Doğrulama denemelerinde 4–6 sn kullanıldı.
- **User-Agent**: `robots.DEFAULT_USER_AGENT`, açıklayıcı.
- **Zorlama yok**: engelleyen site çıkmadı; çıksaydı `dogrulanamadi` olarak
  kalırdı.
- **Provenance**: taşınan her belgede `source_url` + `scraped_at` korundu,
  üstüne `removal_check` kanıt bloğu eklendi.
- **Silme yok**: 1772 → 1772 belge.
- `data/demo.db` **okunmadı, yazılmadı**. Bayatlık sonucunun DB'ye işlenmesi
  gerekiyorsa bu ayrı bir karardır ve bu raporun kapsamı dışındadır.

---

## 8. Döngü ne sıklıkla koşulmalı

Elimizdeki tek gerçek ölçüm 07-30 → 08-03 aralığı, yani **4 gün**:

| Ölçüt | Değer |
|---|---|
| 07-30 turundaki `live/` belge sayısı | 289 |
| 4 günde kaybolan `live/` URL | 44 (**%15,2**) |
| 4 günde içeriği değişen `live/` URL | 121 (%41,9) |

4 günde `live/` kümesinin altıda biri yok oluyor. Buna göre:

- **Hasat + snapshot + fark: haftada bir.** İki hafta beklenirse `live/` kümesinin
  kabaca üçte biri gerçeği yansıtmaz hâle gelir. Bugünkü korpus zaten 7 gün
  bekletilmiş ve 58 bayat URL birikmişti.
- **`reconcile_stale` kuru koşusu: her hasat turundan hemen sonra**, aynı
  koşumda. Maliyeti düşük (bugün 58 istek ≈ 3 dakika) ve `kesif_acigi` kolonu
  bedava kapsam teşhisi veriyor.
- **`--apply`: rapor okunmadan asla.** Bugünkü koşu tam da bunu haklı çıkardı —
  otomatik uygulansaydı 5 canlı belge yanlış pozitifle arşive gömülürdü.
- **Yarışma teslimi öncesi son tam tur zorunlu**, çünkü demo DB'si dolu korpustan
  besleniyor (CLAUDE.md §11) ve jüri "bu kampanya hâlâ geçerli mi" diye sorabilir.
- Damga tabanlı bitmişlik işaretlemesi (§5) devreye alınırsa **her hasatta**
  koşmalı; o kontrol ağ isteği gerektirmiyor, yalnız yerel metin taraması.

---

## Üretilen dosyalar

| Dosya | İçerik |
|---|---|
| `data/snapshots/2026-08-10-korpus-tam.json` | before manifesti (1772 kayıt) |
| `data/snapshots/2026-08-10-son-tam-tur.json` | after manifesti (1711 kayıt, `--since`) |
| `data/snapshots/fark-2026-08-10.{json,md}` | fark raporu |
| `data/snapshots/mutabakat-2026-08-10-kuru.{json,md}` | **kuru koşu** raporu |
| `data/snapshots/mutabakat-2026-08-10-uygulandi.{json,md}` | uygulama sonrası rapor |
| `data/snapshots/2026-08-10-uygulama-sonrasi.json` | taşımadan sonraki durum manifesti |

## İlgili

- `src/scraping/reconcile_stale.py` — mutabakat mantığı, §3'teki kusurun yeri
- `src/scraping/snapshot.py` — manifest ve fark
- `docs/kod-haritasi/scraping.md` — katmanın haritası
- `src/comparison/contradiction.py` — `_SELF_EXPIRED` deseninin asıl sahibi
- CLAUDE.md §14 (scraping etiği), §17 (adil kıyas), §19 (halüsinasyon yasağı)
