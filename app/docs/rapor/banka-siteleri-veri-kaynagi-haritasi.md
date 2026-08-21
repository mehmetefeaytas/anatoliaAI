---
title: "Banka Siteleri Veri Kaynağı Haritası (Tarayıcı Keşfi)"
tags: [veri-toplama, scraping, banka, kesif, playwright]
date: 2026-08-03
status: taslak
---

# Banka Siteleri Veri Kaynağı Haritası

10 katılım bankasının resmî sitesi Playwright (gerçek tarayıcı) ile gezilerek
hangi veri türünün nerede durduğu, hangi uç noktaların yapılandırılmış veri
verdiği ve mevcut korpusun neyi kaçırdığı tespit edilmiştir.

Referans: [[katilim-bankalari]], `app/config/banks.yaml`,
`app/data/raw/_collection_report.md` (hasat: 2026-07-30).

## Yöntem

- Playwright MCP ile canlı gezinme; her sayfada erişilebilirlik anlık görüntüsü,
  ağ trafiği (XHR/JSON) incelemesi ve DOM içi gömülü veri araması.
- Hesaplama araçları gerçekten sürüldü (düğmeye basıldı), sonuç DOM'dan okundu.
- 10 bankanın `sitemap.xml`'leri özyinelemeli çözülüp URL kümeleri çıkarıldı;
  `app/data/raw/*/**/*.meta.json` içindeki hasat edilmiş URL'lerle karşılaştırıldı.
- `robots.txt` kuralları yeni bulunan uç noktalar için ayrıca doğrulandı.

## 1. Kritik bulgu — aylık kâr oranı korpusta YOK

Şartnamenin karşılaştırma ekseni olan **aylık kâr oranı**, finansman ürün
sayfalarında yalnızca *etiket* olarak duruyor; değer istemci-taraflı hesaplama
aracı çalıştırılmadan DOM'a girmiyor. Bu yüzden statik hasat oranı `%0` olarak
kaydetmiş.

Doğrulama:

```
$ grep -rl 'Aylık Kâr Oranı' app/data/raw --include='*.txt' | wc -l   # 25+ dosya
$ # her birinde etiketin yanında sayısal değer yok
app/data/raw/kuveyt-turk/products/konut-finansmanlari-konut-finansmani.txt -> DEGER YOK
app/data/raw/albaraka/products/tasit-finansmani-togg-finansmani.txt       -> DEGER YOK
app/data/raw/kuveyt-turk/products/hesaplama-araclari-finansman-hesaplama.txt -> DEGER YOK
```

Tarayıcıda hesaplama aracı sürüldüğünde aynı Kuveyt Türk konut finansmanı
sayfası şunu veriyor (100.000 TL / 120 ay):

| Alan | Değer |
|---|---|
| Aylık Kâr Oranı | %2,9900 |
| Aylık Maliyet Oranı | %4,2928 |
| Yıllık Maliyet Oranı | %65,5966 |
| Efektif Yıllık Kâr Oranı | %35,8800 |
| Taksit Tutarı | 3.079,76 TL |
| Ödenecek Toplam Tutar | 369.577,03 TL |
| Toplam Masraf | 28.720,00 TL |

Ayrıca taksit başına **ana para / kâr tutarı / KKDF / BSMV** kırılımı olan tam
amortisman tablosu da elde ediliyor. Kaynak:
`https://www.kuveytturk.com.tr/kendim-icin/finansmanlar/konut-finansmanlari/konut-finansmani`

## 2. Yapılandırılmış JSON uç noktaları (en yüksek değerli kaynak)

Üç bankada oranlar doğrudan parametreli JSON uçlarından alınabiliyor. `robots.txt`
hiçbirinde bu yolları engellemiyor (2026-08-03 kontrolü).

### Türkiye Emlak Katılım

```
GET /Plugins/CalculateProfitShareRate?LanguageId=1&Money=100000&Fec=0
    &profitShareInstallment=0&MaturityTerm=92&profitShareInstallmentValueDay=92
-> {"Success":true,"Data":{"GrossProfitShare":9141.69,"GrossProfitShareYearly":36.27,
    "NetProfitShare":7541.89,"NetProfitShareYearly":29.92,"SegmentName":"Altın",
    "TotalAmountNetProfitShare":107541.89}}

GET /Plugins/CalculateLoansProduct?CalculationTypeId=1&ProductTypeId=KONUT
    &LoanAmount=1000000&LoanMaturity=120&LoanSegmentId=1
-> {"Success":true,"Data":{"ProfitRate":1.99,"TotalCost":27.4712912,
    "MonthlyConstRate":2.0432695767578668,"TotalInstallmentAmount":2635735.62,
    "CommissionAmount":5250,"ExpertiseAmount":11000,"HypothecAmount":3684,
    "TotalExpense":19934,"InstallmentContractList":[{...taksit taksit...}]}}
```

`ProductTypeId` numaralandırılabilir (doğrulanan: `KONUT`, `ARACBINEK2EL`).
`Fec` para birimi, `MaturityTerm` gün cinsinden vade.

### Albaraka Türk

`X-Requested-With: XMLHttpRequest` başlığı **zorunlu** — başlıksız istek ana
sayfa HTML'i döndürüyor (sessiz başarısızlık riski).

```
GET /plugins/getProfitShareCalculate?...&DepositedAmount=250000&Currency=TRY
    &Maturity=12&Period=MONTH&Type=KTLMHSP
-> {"Result":true,"Data":{"GrossRate":"% 40.828621","NetRate":"% 36.745759",
    "GrossProfit":"102.351,20 TRY","NetProfit":"92.116,08 TRY","IncomeTax":"% 0,1"}}

GET /plugins/getFinanceCalculate?...&FinanceType=<URL-encoded JSON>&FinanceAmount=150000
    &Maturity=23&ProfitRate=0&Type=B&CreditType=B
```

Dahası: `getFinanceCalculate` çağrısındaki `FinanceType` JSON'u sayfanın HTML'ine
gömülü halde duruyor ve **16 ürünün oran kataloğunu** içeriyor — ayrı istek
gerekmiyor:

| Ürün kodu | Kampanya | Aylık oran | Vade üst sınırı | Tutar üst sınırı |
|---|---|---:|---:|---:|
| KONTKRD / YKKNT0B | İLK EVİM KONUT FİNANSMANI | 3,04 | 120 | 9.999.999 |
| KONTKRD / VRKNT0B | 2. VE SONRAKİ KONUT FİNANSMANI | 3,04 | 120 | 9.999.999 |
| TASKRED / KMPARAC | SIFIR KM TAŞIT FİNANSMANI | 3,75 | 48 | 9.999.999 |
| TASKRED / 2.ELTŞT | 2. EL TAŞIT FİNANSMANI | 3,75 | 48 | 9.999.999 |
| TASKRED / SBSZARC | DİJİTAL ARAÇ FİNANSMANI | 3,75 | 48 | 9.999.999 |
| ARSAKRD / ISYERII | İŞYERİ FİNANSMANI | 3,95 | 60 | 1.000.000 |
| ARSAKRD / ARSABIR | ARSA FİNANSMANI | 3,95 | 60 | 9.999.999 |
| IHTKRED / PRTKRT | PRATİK FİNANSMAN KART | 3,95 | 34 | 150.000 |
| IHTKRED (7 varyant) | Eğitim / Kira / Yurt / Teknoloji / Cep tel. / Engelsiz Hayat / Prefabrik / Motosiklet | 4,00 | 10–36 | değişken |

### Kuveyt Türk

Hesaplama sunucu tarafında ama parametreli JSON ucu **yok**; oran yalnızca
etkileşim sonrası `id="ProfitRate"` düğümüne yazılıyor. Sayfa JS paketlerinde ve
gizli alanlarda (`txtProfilRate` boş) oran bulunmuyor → **tarayıcı sürmek şart**.

### Vakıf Katılım / Dünya / Hayat / TOM

Hesaplama API'si yok. Vakıf'ta oran istemci-taraflı ve kullanıcı düzenleyebilir
(varsayılan %3,75, "Kâr Oranı Kendin Belirle" onay kutusu) — bu değer bankanın
ilan ettiği oran mı yoksa yalnızca form varsayılanı mı, **doğrulanmadı**.

#### Hayat Finans katılma hesabı sayfası — ÜÇ TABLO, HİÇBİRİ KÂR PAYI ORANI DEĞİL

19 Ağu 2026'da `hayatfinans.com.tr/hesaplar/katilma-hesabi` yeniden incelendi
(robots.txt: **izin var**; UA `AnatoliaAI-Research/1.0`, 3 sn gecikme). Sayfada
üç HTML tablo bulunuyor ve **naif bir çıkarım üçünü de yanlış okur**:

| Tablo | Başlık / içerik | Değerler | Gerçekte ne |
|---|---|---|---|
| 1 | Türk Lirası · 1/3/6 Aylık · 1 Yıllık · 1 Yıldan Uzun | `%90 - %10` | kâr **PAYLAŞIM** oranı (banka–müşteri bölüşümü) |
| 2 | Dolar & Euro, aynı vade kolonları | `%70 - %30` | kâr paylaşım oranı |
| 3 | **"Stopaj Oranları"** · Para Birimi × vade | `%17,5` `%15` `%10` | **STOPAJ — vergi kesintisi** |

**Tuzak somut:** sayfadan regex ile "en belirgin yüzde" alınsa `%17,5`
çıkardı ve bu bir **vergi oranı** olarak `kar_payi_orani`'na yazılırdı. Bankalar
arası kıyas tablosunda o satır Hayat Finans'ı tamamen yanlış konumlandırırdı.
İkinci tuzak paylaşım oranıdır; `extract.py::_PAYLASIM_ORANI_RE` onu belge
düzeyinde zaten eliyor (o koruyucunun var olma sebebi tam bu sınıf).

Sonuç: bu sayfa **getiri oranı yayımlamıyor**. Gerçek oran hesaplama aracının
arkasında ve sayfada yalnızca aracın tanımı gömülü
(`"resultBoxes":["Net Kâr","Brüt Oran (Yıllık)",…]`). Yani `harvest_rates.py`
başlığındaki tespit bu banka için de birebir geçerli: *değer istemci-taraflı
hesaplama aracının arkasındadır.*

**Adaptör yazılmadı.** Gerekçe: değeri almak için aracın ağ çağrısını tersine
çevirmek gerekiyor (Playwright + istek izleme) ve bu banka başına ayrı bir iş.
Riski de yüksek — yukarıdaki iki tablo, yanlış değeri "oran" diye kaydetmenin
ne kadar kolay olduğunu gösteriyor. Belgelenmiş eksik, sessiz eksikten iyidir.

#### Banka bazında `kar_payi_orani` kapsamı (19 Ağu 2026, `data/demo.db`)

Kapsamın nerede yoğunlaştığı ölçüldü — açık, korpus genelinde değil banka
bazında:

| banka | belge | `kar_payi_orani` | verim |
|---|---:|---:|---:|
| turkiye-finans | 92 | 22 | %24 |
| kuveyt-turk | 537 | 22 | %4 |
| turkiye-emlak-katilim | 239 | 6 | %3 |
| albaraka | 228 | 3 | %1 |
| vakif-katilim | 197 | 3 | %2 |
| dunya-katilim | 123 | 2 | %2 |
| ziraat-katilim | **291** | **1** | **%0,3** |
| tom-katilim | 19 | 1 | %5 |
| hayat-finans | 48 | **0** | — |
| adil-katilim | **6** | 0 | scrape eksik |

Türkiye Finans oranı düz HTML tablo olarak yayımladığı için en yüksek verimde
(§3). Ziraat 291 belgede yalnız 1 orana sahip — §5'teki "yanlış giriş noktası"
bulgusuyla tutarlı. `adil-katilim` 6 belgede kalmış: bu bir oran sorunu değil,
**toplama** sorunu ve ayrı ele alınmalı.

## 3. Yayımlanmış oran tabloları (statik HTML — en kolay kaynak)

**Türkiye Finans** oranları düz HTML tablo olarak yayımlıyor: tek sayfada
**20 tablo**, tutar dilimi × vade × hesap türü kırılımıyla.

`https://www.turkiyefinans.com.tr/tr-tr/bireysel/Sayfalar/Kar-Payi-Oranlari.aspx`

```
Katılma Hesabı        1 Ay    3 Ay    6 Ay    1 Yıl   1 Yıldan Uzun
250 - 100.000.000     28.03   28.64   29.43   31.29   31.30

Ara Dönem Kâr Payı Ödemeli Katılma Hesabı
250-49.999            21.06   21.14   21.80   22.75   -
100.000-249.999       25.93   26.40   27.02   28.56   -
250.000-999.999       21.87   20.70   21.85   23.28   -
```

Bu sayfa korpusta **var** (`turkiye-finans/products/bireysel-kar-payi-oranlari.txt`).
Benzer sayfalar: Vakıf `/tr/kendim-icin/hesaplar/katilma-hesaplari/kar-paylasim-oranlari`,
Türkiye Finans `/tr-tr/bireysel/Sayfalar/Kar-Paylasim-Oranlari.aspx`.

Emlak Katılım'da ise oran sayfa açılışında hesaplanıp gösteriliyor
(`/tr/hesaplama-araclari` → brüt %31,08 / net %25,64, 1 ay).

## 4. Kapsam açığı — sitemap'te var, korpusta yok

| Banka | Sitemap URL (TR) | Hasat | Kampanya URL (sitemap) | Kampanya (hasat) | Ücret/sözleşme (sitemap/hasat) |
|---|---:|---:|---:|---:|---|
| kuveyt-turk | 2679 | 124 | **475** | 39 | 64 / 6 |
| albaraka | 992 | 127 | 44 | 37 | 43 / 4 |
| ziraat-katilim | 899 | 71 | 18 | **5** | 45 / 3 |
| vakif-katilim | 784 | 126 | 88 | 39 | 34 / 2 |
| turkiye-emlak-katilim | 586 | 129 | 68 | 39 | 15 / 2 |
| dunya-katilim | 273 | 101 | 45 | 40 | 5 / 3 |
| hayat-finans | 249 | 47 | 13 | 12 | 3 / 2 |
| tom-katilim | 0 (sitemap yok) | — | — | 13 | — |
| adil-katilim | 0 (sitemap yok) | — | — | 6 | — |
| turkiye-finans | 0 (sitemap yok) | — | — | 35 | — |

Ana neden `max_docs: 40` kırpması (`app/config/banks.yaml`) ve yanlış giriş
noktaları. Hasat raporu bunu zaten not ediyor: "kuveyt-turk — 453 aday bulundu,
max_docs=40 ile kirpildi".

## 5. Yanlış giriş noktası — Ziraat Katılım

Config `campaign_paths: [/bireysel/kampanyalar]` kullanıyor; o sayfa neredeyse
boş (7 bağlantı, hiçbiri kampanya detayı değil). Gerçek katalog:

- `https://www.ziraatkatilim.com.tr/kart-kampanyalari` → **191 kampanya bağlantısı**
- 15 sektör kategorisi: `/kampanyalar/market-ve-gida`, `/kampanyalar/akaryakit`,
  `/kampanyalar/e-ticaret`, `/kampanyalar/beyaz-esya-ve-ev-aletleri`,
  `/kampanyalar/giyim-ve-aksesuar`, `/kampanyalar/turizm-ve-seyahat`,
  `/kampanyalar/elektronik-ve-telekomunikasyon`, `/kampanyalar/mobilya-ve-dekorasyon`,
  `/kampanyalar/kuyum-optik-ve-saat`, `/kampanyalar/egitim-kitap-ve-kirtasiye`,
  `/kampanyalar/yapi-sektoru-ve-iklimlendirme`, `/kampanyalar/hobi-ve-oyuncak`,
  `/kampanyalar/genel-kampanyalar`, `/kampanyalar/diger-kampanyalar`

Detay sayfaları çıkarıma hazır metin veriyor (tarih aralığı, eşik tutar, ödül,
kanal koşulu, hariç tutulanlar) — örnek
`/kart-kampanyalari/market-alisverislerinize-toplam-1500-tl-bankkart-lira-0`:

> "10 Temmuz 2026 - 7 Ağustos 2026 tarihleri arasında market, bakkal, kasap …
> tek seferde yapacağınız 2.500 TL ve üzeri her alışverişiniz ile 125 TL, toplam
> 1.500 TL Bankkart Lira kazanabilirsiniz. … E-ticaret işlemleri kampanyaya
> dahil değildir."

`robots.txt` bu yolları engellemiyor (standart Drupal kuralları).

**HTTP 493 notu:** Hasat raporundaki 6 başarısız Ziraat URL'si gerçek tarayıcıyla
da açılmıyor (`net::ERR_HTTP_RESPONSE_CODE_FAILURE`). Bot engeli değil; sitemap'te
kalmış ölü bağlantılar. `manifest.json` de 493 dönüyor.

## 6. Süresi dolmuş kampanya kaynakları (zamansal doğrulama için)

- **Kuveyt Türk arşivi:** `/kampanyalar/kampanya-arsivi`
  (`?root=kendim-icin` / `?root=isim-icin` süzgeçleriyle). Liste sayfası her
  kampanya için **bitiş tarihini** ayrı düğümde veriyor (ör. `31.07.2026`) →
  başlık + bitiş tarihi + özet üçlüsü bedava etiket.
- **Türkiye Finans:** `/tr-tr/kampanyalar/Sayfalar/biten-kampanyalar.aspx`
  (korpusta var: `turkiye-finans/live/kampanyalar-biten-kampanyalar.txt`).

Bu iki kaynak, `suresi_dolmus_kampanya` kuralı için sentetik değil **gerçek**
doğrulama kümesi sağlar.

## 7. Ücret/komisyon tarifeleri ayrı alan adlarında PDF

Ücret tarifeleri HTML tablo değil, PDF. Bazıları farklı hostta — mevcut
`sitemap_urls` + `detail_patterns` yapılandırması bunlara ulaşamıyor.

| Banka | Sayfa | Belge |
|---|---|---|
| Emlak Katılım | `/tr/urun-ve-hizmet-ucretleri` | `asset.emlakkatilim.com.tr/documents/urun-ve-hizmet-ucretleri/breysel-bankacilik-urun-ve-hzmet-ucretler-2026-tr.pdf` (+ ticari) |
| Dünya Katılım | `/urun-hizmet-ve-ucretleri` | `/content/files/uploads/2516/dk-bireysel-ucrt11-180526.pdf` (+ ticari) |
| Hayat Finans | `/urun-ve-hizmet-ucretleri` | — (doğrulanmadı) |
| Türkiye Finans | `/tr-tr/bireysel/Sayfalar/urun-hizmet-ucretleri.aspx` | korpusta var |

Ayrıca her bankada `sozlesmeler-ve-formlar` sayfaları var; "Ürün Bilgi Formu"
PDF'leri kesin oran/ücret içerir (Emlak 15, Kuveyt 64, Ziraat 45, Albaraka 43,
Vakıf 34 aday URL).

## 8. Gerçek sayfa-içi çelişki örneği (çelişki tespiti için)

Kuveyt Türk TOGG Finansmanı sayfasında **aynı sayfanın** tablosu ile SSS'si
çelişiyor:

| Kaynak | Bant | Oran |
|---|---|---|
| Sayfa gövdesi tablosu | 6.500.001 – 7.500.000 TL | %20 |
| Sayfa gövdesi tablosu | 7.500.001 TL ve üzeri | %0 |
| Aynı sayfanın SSS'si | 6.000.001 – 7.000.000 TL | %20 |
| Aynı sayfanın SSS'si | 7.000.001 TL ve üzeri | %0 |

Kanıt: `app/data/raw/kuveyt-turk/products/arac-finansmanlari-togg-finansmani.txt`
(tek dosya içinde iki ifade). Bu, `app/src/comparison/contradiction.py` için
sentetik olmayan, kaynaklanabilir bir test vakası.

## 9. Diğer gözlemler

- **JSON-LD:** 847 ham HTML'in 614'ünde `application/ld+json` var; 21'inde
  `FAQPage` şeması (7'ye kadar soru-cevap çifti). Kontrol edildi: bu içerik
  görünür HTML'de de olduğu için metin çıkarımına **giriyor** — ayrı bir kayıp
  yok. Yine de `FAQPage` şeması chatbot değerlendirme kümesi için hazır
  soru-cevap çiftleri sunuyor.
- **Hayat Finans** segment eşik tablosu yayımlıyor (Bronz / Gümüş / Altın;
  ör. "85.000 TL ve üzeri", "son 30 gün otomatik tahsilat adedi 3 ve üzeri") —
  koşul çıkarımı için farklı bir yapı türü.
- **TOM Katılım** kampanyaları `tombankhadi.com` üzerinde **iki ayrı yolda aynı
  içerik** veriyor: `/kampanyalar/<slug>` ve
  `/cok-kazananlar-kulubu-kampanya/<slug>` → tekilleştirme (dedup) gerekir.
- **Kuveyt Türk** ek kaynaklar: `/kart-karsilastirma/kendim-icin` (bankanın kendi
  karşılaştırması), `/finans-portali` (kur/piyasa), `/hesaplama-araclari`.
- Kampanya listeleme sayfalarında API yok; hepsi sunucu-taraflı render →
  `scrape_mode: static` doğru seçim (TOM, Hayat, Adil hariç).

## Uygulama sonucu (2026-08-03 genişletilmiş hasat)

Bu raporun önerileri aynı gün uygulandı. Dört turlu hasat + fark + mutabakat:

| Küme | Temmuz (30 Tem) | Ağustos (3 Ağu) |
|---|---:|---:|
| `live/` (aktif kampanya) | 289 | **687** |
| `products/` (ürün sayfası) | 557 | **635** |
| `archive/` (süresi dolmuş) | — | **201** |
| `docs/` (PDF tarife/form) | — | **112** (853 sayfa) |
| **toplam (taze)** | **847** | **1635** |

Banka bazında en büyük kazanç: Ziraat Katılım **5 → 215** (giriş noktası
düzeltmesi), Kuveyt Türk **39 → 134**.

### Turlar arası fark (metin bazlı)

| Durum | Adet |
|---|---:|
| `ayni` | 652 |
| `degisti` | 140 |
| `yeni` | 834 |
| `kayip` | 47 |

Karşılaştırma **temiz metin** hash'i üzerinden yapılır. Ham HTML hash'iyle
ölçüldüğünde 238 belge "değişmiş" görünüyordu; `git diff` ile `.txt` içerikleri
birebir aynı çıktı (analitik/oturum gürültüsü). Düzeltmeden sonra `ayni` 6 → 652.

### Kayıp belgelerin doğrulanması

44 kayıp `live/` URL'i yeniden çekilip karara bağlandı (kuru koşu):

| Karar | Adet | Anlamı |
|---|---:|---|
| `gecersiz_kilindi` | 35 | Temmuz'da yanlışlıkla `live/`'a düşmüş arşiv sayfaları; şimdi `archive/`'da taze hâli var |
| `suresi_dolmus` | 5 | Sayfa yayında ama kendini "süresi dolmuştur" işaretliyor (Türkiye Finans 3, Vakıf 2) |
| `kesif_acigi` | 3 | Sayfa hâlâ yayında — keşif bu turda kaçırdı |
| `kaldirilmis` | 1 | HTTP 404 (Albaraka, yazım varyantı URL) |
| `dogrulanamadi` | 0 | — |

**Doğrulamanın değeri ölçüldü:** 44 belgenin tamamı körlemesine `expired`
etiketlenseydi **35'i (%80) yanlış** olurdu — onlar kaybolmuş kampanya değil,
yanlış dosyalanmış belgelerdi.

### Oran toplama hattı (5. tur) — kuruldu

`src/scraping/rates.py` + `harvest_rates.py`. Üç adaptör, **69 oran kaydı**:

| Banka | Kayıt | Yöntem | İstek |
|---|---:|---|---:|
| `turkiye-emlak-katilim` | 50 | JSON ucu (`/Plugins/*`) | 68 |
| `albaraka` | 16 | sayfaya gömülü katalog | 1 |
| `kuveyt-turk` | 3 | tarayıcı ile hesaplama aracı | 20 |

Şartnamenin manşet örneği artık gerçek veriyle üretilebiliyor:

| Banka | Ürün | Aylık kâr oranı | Vade |
|---|---|---:|---:|
| Türkiye Emlak Katılım | Konut Finansmanı | **%1,89** | 12–60 ay |
| Türkiye Emlak Katılım | Konut Finansmanı | %1,99 | 120 ay |
| Kuveyt Türk | Konut Finansmanı | %2,99 | 120 ay |
| Albaraka | İlk Evim Konut Finansmanı | %3,04 | ≤120 ay |
| Türkiye Emlak Katılım | Konut Finansmanı (sıfır konut) | %3,39 | 12–120 ay |
| Türkiye Emlak Katılım | Taşıt Finansmanı | %4,29 | 12–36 ay |
| Kuveyt Türk | Taşıt / TOGG Finansmanı | %3,57 | 48 ay |

Ayrıca Emlak katılma hesabı oranları **segment ayrımıyla** alınıyor
(250.000 TL → Altın %38,73 brüt; 50.000 TL → Gümüş %36,78 brüt, 365 gün).

**Kıyas uyarısı (§17):** Albaraka kaydı hesaplanmış bir nokta değil, sayfaya
gömülü kataloğun **üst sınır** değerleridir (`note` alanında işaretli). Kuveyt
Türk kayıtları sayfanın kendi varsayılan noktasıdır. Doğrudan kıyas yapılırken
bu fark gözetilmelidir.

### Uydurma verinin üç noktada engellenmesi

Bu hat, ölçülmüş üç sessiz-bozulma tuzağını kapatıyor:

1. **Emlak ucu geçersiz kombinasyonda hata VERMİYOR** — `Success: true` +
   `ProfitRate: 0` + `toplam = ana para` döndürüyor. `_is_priced` kapısı olmadan
   bunlar korpusa "%0 kâr payı oranı" olarak girerdi. Doğrulandı:
   `ARACBINEK2EL` 1.000.000 TL / 120 ay. Tahmin edilen `IHTIYAC` / `ISYERI`
   kodları da hep bu yanıtı verdi → gerçek kod listesi sayfanın seçeneklerinden
   alındı.
2. **Albaraka ucu AJAX başlığı olmadan 200 + HTML döndürüyor** — içerik tipi
   doğrulanmazsa sessiz veri kaybı olur.
3. **Kuveyt Türk maskeli tutar alanı programatik değişikliği geri alıyor** —
   adaptör ilk hâlinde 500.000 TL / 60 ay istediği hâlde varsayılan
   100.000 TL / 120 ay sonucunu kaydediyordu. Artık kayıt, sayfanın **gerçekten
   kullandığı** tutar/vadeyle etiketleniyor; diyalog bunu yansıtmazsa kayıt
   düşürülüyor.

### Açık kalan sınırlar

- **Kâr payı oranı metin korpusunda hâlâ zayıf:** 1684 belgenin 73'ünde
  `kar_payi_orani` var. Oran verisi artık ayrı ve yapısal kümede (`rates/`);
  karşılaştırma motoru oradan okumalı, metin çıkarımından beklememeli.
- **Albaraka katılma hesabı oranı alınamıyor:** çalışan tek URL biçimi
  robots.txt'in `*search*` / `/*slug` kurallarına takılıyor, parametresiz uç
  bağlantıyı kapatıyor, statik HTML'de oran yok.
- **Kuveyt Türk'te ızgara sürülemiyor:** tutar maskesi nedeniyle ürün başına tek
  nokta alınıyor. Vade varyasyonu denenir, oturmazsa sessizce atlanır.
- **Adaptörü olmayan 7 banka:** Vakıf, Türkiye Finans, Ziraat, Dünya, Hayat,
  TOM, Adil. Türkiye Finans ve Vakıf oranlarını **HTML tablo** olarak
  yayımlıyor (§3) — bunlar için adaptör değil, tablo ayrıştırıcı gerekir.
- **robots.txt sınırı:** Türkiye Finans (342 aday) ve Vakıf Katılım (117 aday)
  sözleşme/tarife PDF'lerini robots.txt ile engelliyor; hat bunları ATLADI
  (CLAUDE.md §14). Şartname §5.1 bu belgeler için manuel toplamaya izin verir.
- **Mükerrer belgeler:** korpusta 99 mükerrer metin grubu / 217 dosya var.
  Kök neden (ham HTML üzerinden tekilleştirme) düzeltildi ama diskteki mevcut
  mükerrerler temizlenmedi. `celisen_tutar_bandi` bu yüzden 2 gerçek bulgu
  yerine 4 raporluyor.

## Öneriler (öncelik sırasıyla)

1. **Oran toplama yolu ekle.** İki katmanlı: (a) JSON ucu olan bankalar için
   doğrudan istek (Emlak, Albaraka), (b) olmayanlar için Playwright ile
   hesaplama aracını sürme (Kuveyt Türk). Ürün × tutar × vade ızgarası tanımla.
   Albaraka'da `X-Requested-With` başlığını atlamak sessizce HTML döndürür —
   yanıtın `content-type`'ı doğrulanmalı.
2. **Ziraat giriş noktasını düzelt:** `campaign_paths`'e `/kart-kampanyalari` ve
   15 sektör kategorisini ekle (5 → ~191 belge).
3. **`max_docs: 40` sınırını kaldır veya banka başına yükselt** — Kuveyt Türk'te
   475 kampanya URL'sinden 39'u alınıyor.
4. **Arşiv/biten kampanya sayfalarını ekle** (Kuveyt Türk arşivi, Türkiye Finans
   biten kampanyalar) — zamansal çelişki kuralı için gerçek doğrulama kümesi.
5. **PDF hattı kur:** ücret tarifeleri ve ürün bilgi formları için ayrı
   `extra_hosts` (ör. `asset.emlakkatilim.com.tr`) ve PDF metin çıkarımı.
6. **Sitemap'i keşif kaynağı olarak kalıcılaştır**, ölü URL'leri (Ziraat 493/404)
   ayrı listede tut.

## Sources

- Canlı tarayıcı keşfi (Playwright MCP), 2026-08-03 — 10 bankanın resmî siteleri
- `app/config/banks.yaml` — mevcut yapılandırma
- `app/data/raw/_collection_report.md` — 2026-07-30 hasat raporu
- `app/data/raw/kuveyt-turk/products/arac-finansmanlari-togg-finansmani.txt` — çelişki kanıtı
- `robots.txt`: albaraka.com.tr, emlakkatilim.com.tr, ziraatkatilim.com.tr (2026-08-03)

## Related

- [[katilim-bankalari]] — hedef kuruluşlar
- [[veri-seti]] — toplanan veri
- `app/src/scraping/` — toplama hattı
- `app/src/comparison/contradiction.py` — çelişki tespiti
