# "Süresi Dolmuş" Damgası — Desen Düzeltmesi ve Korpus İşaretlemesi (2026-08-10)

> Devamı olduğu rapor: `docs/rapor/bayat-veri-mutabakati.md` (§3 kusuru ölçtü,
> §5 boşluğu ölçtü). Bu belge o iki bulgunun **uygulanmış** hâlidir.
>
> Ağ isteği yapılmadı. Bütün ölçümler `data/raw/` altındaki yerel korpus
> üzerinde koşuldu. Hiçbir dosya silinmedi, hiçbir belge taşınmadı.

---

## 0. Özet

| İş | Önce | Sonra |
|---|---|---|
| **İŞ 1** — `verify_stale`'in `suresi_dolmus` kararı | 5 karar, **5'i yanlış pozitif** (%100) | aynı 5 belge → **0 damga**, hepsi `kesif_acigi` |
| **İŞ 1** — desenin canlı korpustaki ateşleme oranı | 772 belgenin **195'i** (%25,3, ham HTML) | 772 belgenin **221'i** (%28,6), elle bakılan yanlış pozitif **0** |
| **İŞ 2** — `live/` altında damgalı ama işaretsiz belge | **221** (%28,6) | **221'i işaretlendi** (`campaign_status: expired`) |

Ortak parça: `src/scraping/expiry_stamp.py` — damganın **tek doğruluk kaynağı**.
Hem ağ tabanlı mutabakat (`reconcile_stale`) hem ağsız korpus geçişi
(`scripts/damga_isaretle.py`) aynı fonksiyonu çağırır. İhtar kalıbı
kopyalanmadı; `src/extraction/rules/ihtar.py`'den okunuyor.

---

## 1. İŞ 1 — kusur neydi

`verify_stale`, sayfanın kendini bitmiş ilan edip etmediğini
`comparison.contradiction._SELF_EXPIRED` deseniyle **ham HTML'in tamamında**
arıyordu (`reconcile_stale.py:181`). O desen `comparison` katmanında
**koruma** amaçlıdır — bir bulguyu bastırır, yanlış eşleşmenin bedeli bir
bulgunun kaçırılmasıdır. `reconcile_stale` onu **karar** amaçlı kullanınca hata
yönü tersine döndü: yanlış eşleşmenin bedeli canlı bir belgenin arşive
gömülmesi oldu.

Kuru koşudaki 5 `suresi_dolmus` kararının 5'i de yanlış pozitifti:

| Banka | Eşleşen şey | Neden yanlış |
|---|---|---|
| turkiye-finans (3) | `Biten Kampanyalar` | her sayfada duran **gezinti menüsü** bağlantısı; canlı olduğu kesin 3 kontrol sayfasının 3'ü de eşleşiyordu |
| vakif-katilim (2) | `… sona erdirme … hakkını saklı tutar` | standart **ihtar** cümlesi — "bitti"nin tam tersi |

---

## 2. Deseni gerçeğe uydurma — hangi kararlar, hangi ölçümle

### 2.1 Ayırt edici dilbilgisi

İhtar cümlesi **mastar/isim-fiil** kullanır ("sona erdirme", "sonlandırma",
"durdurma", "iptal etme") — bankanın SAKLI TUTTUĞU haklar.
Damga **bitmiş kip** kullanır ("sona ermiştir", "sona erdi", "süresi
dolmuştur"). Dar desen yalnız ikinci kümeyi tanır. Bu, tek başına en büyük
yanlış pozitif kaynağını kapatır.

Dar desenin dört alternatifi de gerçek korpustan alındı:

| # | Kalıp | Kaynak banka | Eşleşen belge |
|---|---|---|---:|
| 1 | `(bu) kampanya sona ermiştir` | albaraka | 14 (hepsi vetolandı, §2.4) |
| 2 | `<tarih> tarihinde sona ermiştir` | ziraat-katilim | 102 |
| 3 | `kampanya süresi dolmuştur` | vakif-katilim, dunya-katilim | 83 |
| 4 | `sona erdi … bitiş tarihi` | dunya-katilim | 38 |

Çıplak `sona erdi` ve `biten kampanya` **bilerek dışarıda**: birincisi ihtar
cümlesindeki "sona erdir**me**"nin ön ekiyle eşleşir (`sona\s+erdi` deseni
"erdirme"nin içine düşer), ikincisi Türkiye Finans'ın menü bağlantısıdır.

### 2.2 Dar / geniş desenin ölçülen yanlış pozitif oranı

772 `live/` belge (tam korpus, uygulama öncesi):

| Desen | Girdi | Eşleşen belge | Oran | Elle bakılan yanlış pozitif |
|---|---|---:|---:|---|
| geniş (`_SELF_EXPIRED`) | ham HTML | 195 | %25,3 | menü + ihtar; ayrımı yok |
| geniş (`_SELF_EXPIRED`) | temiz metin | 276 | %35,8 | ihtar kaynaklı |
| **orta** (`kampanya …{0,40} sona er\|süresi dolmu\|sonlandır`) | temiz metin | 359 | %46,5 | çok |
| orta **+ ihtar vetosu** | temiz metin | 328 | %42,5 | **97** (aşağıda) |
| **dar** (ham) | temiz metin | 231 | %29,9 | 10 (kuyruk bloğu) |
| **dar + 3 koruma** | temiz metin | **221** | **%28,6** | **0** |

Orta desenin ihtar vetosundan sonra bile taşıdığı 97 yanlış pozitifin dökümü —
geniş desenin neden yetmediğinin somut kanıtı:

| Banka | Adet | Eşleşen metin | Neden yanlış |
|---|---:|---|---|
| kuveyt-turk | 90 | "… kampanya koşullarında değişiklik yapabilir ya da kampanyayı **sonlandırabilir**." | ihtarın `IHTAR_RE`'nin görmediği çekimi |
| hayat-finans | 4 | "Kampanya süresince müşteri ilişiğini **sonlandırıp** …" | müşteriyle ilgili, kampanyayla değil |
| turkiye-finans | 1 | "… kampanya süresi **sona ermeden** kullandırıldığı takdirde …" | koşul cümlesi |
| albaraka | 2 | ihtar çekimleri | — |

Dar desen bu 97 vakanın hiçbirine değmiyor.

### 2.3 Koruma 1 — temiz metin (ham HTML değil)

Bu koruma **yanlış pozitifi bitirmez** (Türkiye Finans'ın menü bağlantısı temiz
metinde de duruyor; onu dar desen eliyor). Aldığı şey kararın **markup
kazalarına bağlı olmaması**:

- Aynı geniş desen ham HTML'de 195, temiz metinde 276 belge buluyor. Aradaki
  **81 belgenin tamamı Vakıf Katılım**: damga HTML'de etiket/`&nbsp;` ile
  bölündüğü için `\s+` tutmuyor — yani karar sessizce **kaçırıyordu**.
- Ters yönde tek belge bile yok (HTML'de eşleşip temiz metinde eşleşmeyen: **0**).
- Ham HTML ayrıca `href=".../Biten-Kampanyalar.aspx"` gibi içerik olmayan
  dizgeleri arama uzayına sokar; bunlar sayfanın durumu hakkında hiçbir zaman
  kanıt olamaz.

### 2.4 Koruma 2 — ihtar vetosu (`ihtar.IHTAR_RE`, tek kaynak)

Eşleşmeden **sonra**, aynı öbek içinde ve 120 karakter içinde bir ihtar kalıbı
geliyorsa eşleşme, ihtarın saydığı hak kalemlerinden biridir → reddedilir.

Veto **yönlüdür** ve bu bir tercih değil, ölçüm sonucu: yönsüz (cümle bazlı)
veto, Dünya Katılım'da 1 **gerçek** damgayı düşürüyordu — o sayfada ihtar
cümlesinden sonra nokta yok ve iki ifade tek cümle gibi okunuyor:

> «… kampanyayı durdurma hakkını saklı tutar **Paraf Kampanyaları Sona erdi
> Bitiş Tarihi: 31 Temmuz 2026**»

Yönlü veto ile: dar desende **0** eşleşme vetolandı (dar desen ihtar cümlesine
zaten değmiyor), orta desende **40** eşleşme vetolandı — yani koruma ölü kod
değil, dar desenin dışına çıkıldığı anda çalışıyor.

### 2.5 Koruma 3 — kuyruk bloğu ("Diğer Kampanyalar")

Bu koruma bu çalışmada **yeni bulunan** bir yanlış pozitif kaynağını kapatır ve
önceki raporda yoktu.

Albaraka'nın kampanya sayfaları kendi durumunu **yazmıyor**; damga yalnız
sayfanın altındaki "Diğer Kampanyalar" kartlarında ve **başka** kampanyalara
ait olarak görünüyor. Örnek (`detay-bosch-…`): sayfanın kendi kampanyası
"24 Haziran 2026 tarihine kadar … kaçırmayın" diyor, damga 1787. karakterde ve
1583'teki `Diğer Kampanyalar` başlığından sonra, Arçelik kampanyasına ait.

Bu koruma olmadan **10 Albaraka belgesi** yanlışlıkla bitmiş sayılıyordu.

Kuyruk bloğu, metnin **ikinci yarısındaki son** başlıktan itibaren tanımlanır.
Naif "ilk başlıktan kes" kuralı ölçüldü ve **reddedildi**: Ziraat Katılım aynı
ifadeyi üst gezinti çubuğunda da kullanıyor (`Tüm Kampanyalar … Diğer
Kampanyalar 1 …`, 193. karakter) ve ilk başlıktan kesmek o bankanın **102
gerçek damgasının hepsini** düşürüyordu.

### 2.6 Bitiş tarihi — yalnız damgaya YAPIŞIKSA

İlk sürüm damganın ±45 karakterindeki ilk tarihi okuyordu. Ölçüldü: Vakıf
Katılım'ın 26 tarihli belgesinin **3'ünde kampanyanın BAŞLANGIÇ tarihi** bitiş
sanılıyordu — "… Kampanya Süresi Dolmuştur **Kampanya Detayları 15 Ekim 2024** -
31 Mayıs 2025 …" → `2024-10-15`. Yakınlık aidiyet değildir.

Şimdi tarih yalnız damgaya yapışıksa okunuyor (araya en fazla 24 karakter,
sadece iki nokta/boşluk/tire). Sonuç: **139 belgede** tarih okundu, **82
belgede** damga tarih taşımadığı için `null` yazıldı. Yanlış tarih yerine
bilgi yokluğu (CLAUDE.md §19).

---

## 3. İŞ 1 — düzeltmenin öncesi/sonrası

`verify_stale` artık kararı `expiry_stamp.find_expiry_stamp` ile veriyor ve
girdisi `collector._extract_main_text(r.html)`.

| Ölçüm | Önce | Sonra |
|---|---:|---:|
| Kuru koşudaki 5 `suresi_dolmus` adayı, aynı belgelerin korpus metniyle | 5 damga | **0 damga** → hepsi `kesif_acigi` |
| Desenin canlı sayılan `live/` korpusunda ateşleme oranı | %25,3 (ham HTML, denetlenmemiş) | %28,6 (denetlenmiş, elle bakılan yanlış pozitif 0) |

> Not: 5 aday yeniden **çekilmedi** (bu iş ağ istemiyor); ölçüm o URL'lerin
> korpustaki temiz metni üzerinde yapıldı. Beşinin de kaynağı menü/ihtar
> olduğu için sonuç sayfa yeniden çekilse de değişmez — eşleşen dizgeler
> sayfanın kalıcı çerçeve metnidir.

`suresi_dolmus` kararı artık kanıtını da taşıyor: `Verdict.stamp` (eşleşen
ifade, alıntı, konum, bitiş tarihi) hem rapora hem taşınan `.meta.json`'ın
`removal_check.expiry_stamp` bloğuna yazılıyor.

**Regresyon testleri**

- `tests/test_expiry_stamp.py` — kontrol grubu **gerçek korpustan** birebir
  alıntı (Türkiye Finans menüsü, Vakıf/T.O.M. ihtar cümleleri, Kuveyt Türk'ün
  "sonlandırabilir" çekimi, Albaraka kuyruk bloğu); hiçbiri damga sayılmamalı.
  Ayrıca **korpus geneli** regresyon: 7 kontrol bankasının `live/` belgelerinde
  damga sayısı **0**, damgalı 3 bankada ölçülen sayılar sabit. (`data/raw/*/live/*.txt`
  depoda izlendiği için bu test temiz bir klonda da koşar.)
- `tests/test_reconcile_stale_damga.py` — `verify_stale` uçtan uca: üç kontrol
  sayfası `kesif_acigi`, damgalı sayfa `suresi_dolmus` + tarih + kanıt.
  Test ayrıca **eski desenin bu üç kontrol sayfasında ateşlediğini** doğruluyor;
  yoksa kontrol grubu regresyonu ölçmezdi.

---

## 4. İŞ 2 — `live/` altındaki damgalı belgelerin işaretlenmesi

### 4.1 Sorun

Bayat döngüsü yalnız **kaybolan** URL'leri yakalar. Kampanya kaybolmadan da
biter: banka sayfayı yayında bırakıp üstüne damga basar. Bu belgeler her turda
yeniden toplanır, `kayip` kümesine hiç düşmez, `reconcile_stale` onlara
**hiçbir zaman** ulaşamaz.

### 4.2 İşaret nereye yazıldı — ve neden taşıma değil

`scripts/damga_isaretle.py`, `.meta.json` içine `campaign_status: expired` +
`expiry_stamp` kanıt bloğu yazar. **Dosya taşımaz.** Gerekçe:

1. `pipeline.collect_corpus`, `data/raw/<banka>/` altını **özyinelemeli** okur —
   `archive/` de okunuyor. Yani taşımak belgeyi kıyastan **çıkarmaz**;
   taşımanın tek başına hiçbir aşağı akış etkisi yok. `campaign_status`
   alanının ise var ve alan zaten tanımlı (`collector.STATUS_EXPIRED`).
2. Bu korpusta `archive/`, "bankanın **kendi arşiv bölümünden** toplandı"
   demektir (`harvest_extra` + `discover_archive`). Bu 221 belge bankanın
   **canlı** bölümünden toplandı; taşımak toplama provenance'ını yanlışlardı.
3. Taşıma bir sonraki hasatta **mükerrer kayıt** üretir: aynı URL yine `live/`
   altına yazılır ve arşivdeki kopyanın yanında ikinci bir belge oluşur —
   `reconcile_stale`'in Kuveyt Türk'te 33 belgeyle temizlemek zorunda kaldığı
   sorunun aynısı.

Bunun bedeli: hasat `.meta.json`'ı yeniden yazar ve işareti siler. Bu bir kusur
değil — işaret **veriden türetilebilir** kalır. Geçiş bu yüzden **her hasat
turundan sonra** koşmalıdır; ağ istemediği için maliyeti saniyeler.

### 4.3 Ölçüm — önce / sonra

Koşu: `python -m scripts.damga_isaretle --uygula` · 772 `live/` belge ·
ağ isteği yok · taşınan/silinen dosya yok.

| Karar | Adet | Oran | Ne yapıldı |
|---|---:|---:|---|
| `damgali` | **221** | %28,6 | `campaign_status: expired` + `expiry_stamp` kanıt bloğu |
| `belirsiz` | 55 | %7,1 | **dokunulmadı** — geniş desen ateşliyor ama damga değil |
| `temiz` | 496 | %64,2 | işaret yok |

`belirsiz` kolonu bilerek ayrı duruyor: o 55 belgede eşleşen şey menü
bağlantısı, ihtar kalıbı ya da başka bir kampanyanın damgası. Emin olunmayan
belgeye "kapanmış" demek veri uydurmaktır (CLAUDE.md §19).

Banka bazında (önce: hepsi işaretsiz):

| Banka | live belge | damgalı | oran | belirsiz | bitiş tarihi okunan |
|---|---:|---:|---:|---:|---:|
| ziraat-katilim | 215 | 102 | %47,4 | 0 | 102 |
| vakif-katilim | 90 | 81 | %90,0 | 6 | 0 |
| dunya-katilim | 59 | 38 | %64,4 | 0 | 37 |
| turkiye-finans | 44 | 0 | %0 | 34 | 0 |
| albaraka | 90 | 0 | %0 | 13 | 0 |
| tom-katilim | 13 | 0 | %0 | 2 | 0 |
| adil / hayat / kuveyt-turk / emlak | 261 | 0 | %0 | 0 | 0 |
| **TOPLAM** | **772** | **221** | **%28,6** | **55** | **139** |

`turkiye-finans` (34) ve `albaraka` (13) satırları düzeltmenin işe yaradığının
doğrudan kanıtı: eski desenin bitmiş saydığı belgeler artık `belirsiz`
kolonunda ve **dokunulmadan** duruyor.

### 4.4 Damgadan okunan bitiş tarihleri

139 belgede tarih damgaya yapışık yazılı; 82 belgede damga tarih taşımıyor ve
tarih **uydurulmadı**.

| Bitiş ayı | Belge | | Bitiş ayı | Belge |
|---|---:|---|---|---:|
| 2025-06 … 2025-12 | 25 | | 2026-04 | 5 |
| 2026-01 | 1 | | 2026-05 | 20 |
| 2026-02 | 2 | | 2026-06 | 24 |
| 2026-03 | 8 | | 2026-07 | 54 |

Bankalar bitmiş kampanyayı **aylarca** yayında bırakıyor; en eskisi 2025
Haziran'da bitmiş ve hâlâ canlı bölümde duruyordu.

### 4.5 Silme/taşıma yok — sayımla

| Ölçüt | Önce | Sonra |
|---|---:|---:|
| `live/` belge (`.txt`) | 772 | 772 |
| `archive/` belge | 237 | 237 |
| korpus toplamı | 1774 | 1774 |
| değişen dosya | — | yalnız 221 `.txt.meta.json` |

`source_url`, `scraped_at`, `content_hash` her dosyada olduğu gibi korundu.
`data/demo.db` okunmadı, yazılmadı.

### 4.6 İdempotanlık

İkinci koşu diski değiştirmez: damga aynıysa `checked_at` korunur ve dosya
yeniden yazılmaz. Belge yeniden hasat edilip damga kalkarsa geçiş **kendi**
işaretini geri alır; `reconcile_stale`'in veya hasatçının yazdığı
`campaign_status`'a dokunmaz (`marked_by` alanıyla ayrılır).
`tests/test_damga_isaretle.py` bunların dördünü de kapıda tutar.

---

## 5. Aşağı akış — ne yapıldı, ne YAPILMADI

`campaign_status: expired` artık 221 `live/` belgede yazılı ve kanıtlı. Ama:

- **Kıyas motoru bu alanı henüz OKUMUYOR.** `src/comparison/**` bu çalışmanın
  yazma kapsamı dışında. Adil kıyasın (CLAUDE.md §17) fiilen düzelmesi için
  sıralama/kıyas sorgusunun `campaign_status`'u süzmesi gerekir — bu ayrı bir
  iştir ve burada yapılmadı.
- **`data/demo.db` güncellenmedi** (salt okunur kabul edildi). DB yeniden
  kurulduğunda `.meta.json`'daki alan ona taşınmadıkça etkisi olmaz.

Yani bu iki iş **veriyi ve kararı doğru hâle getirdi**; sunum katmanının o
kararı kullanması bir sonraki adımdır. Bunu gizlememek gerekiyor.

---

## Üretilen / değişen dosyalar

| Dosya | İçerik |
|---|---|
| `src/scraping/expiry_stamp.py` | damga deseni + 3 koruma + tarih okuma (**yeni**, tek kaynak) |
| `src/scraping/reconcile_stale.py` | karar artık temiz metin + dar desen; kanıt `Verdict.stamp` |
| `scripts/damga_isaretle.py` | ağsız korpus geçişi (**yeni**) |
| `tests/test_expiry_stamp.py` | kontrol grubu + korpus geneli regresyon (**yeni**) |
| `tests/test_reconcile_stale_damga.py` | `verify_stale` uçtan uca regresyon (**yeni**) |
| `tests/test_damga_isaretle.py` | kuru koşu / provenance / idempotanlık (**yeni**) |
| `data/snapshots/damga-2026-08-10.{md,json}` | uygulama koşusunun ham raporu |
| `data/raw/*/live/*.txt.meta.json` | 221 dosyaya `campaign_status` + `expiry_stamp` |

## İlgili

- `docs/rapor/bayat-veri-mutabakati.md` — §3 kusuru, §5 boşluğu ölçen rapor
- `src/extraction/rules/ihtar.py` — ihtar kalıbının tek kaynağı
- `src/comparison/contradiction.py` — `_SELF_EXPIRED`'in asıl (koruma amaçlı) sahibi
- CLAUDE.md §14 (scraping etiği), §17 (adil kıyas), §19 (halüsinasyon yasağı)
