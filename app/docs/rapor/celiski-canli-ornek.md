---
başlık: Çelişki tespiti — çift-snapshot canlı ateşleme kanıtı
durum: ölçüldü (2026-08-20), dürüstçe raporlandı
üretici: scripts/celiski_canli.py
girdi: data/snapshots/fark-2026-07-30_2026-08-03.json + git (c3f3b90, e05bc83)
---

> **Güncelleme (2026-08-21):** bu belgedeki "0 belgeler-arası çelişki" sonucu
> DEĞİŞTİRİLMEDİ (tarihli ölçüm olarak kalır) ama artık TEK ölçüm değil.
> Farklı bir kod yolu (`src.comparison.scan`, tek anlık görüntü içinde
> `product_key` gruplaması) aynı korpusta **8 gerçek belgeler-arası çelişki**
> buldu — 6 çapraz bitiş tarihi + **2 çapraz kâr payı uyuşmazlığı** (manşet:
> Albaraka aynı ürün için %7,0 ve %1,0). Ayrıntı ve komut:
> [`celiski-canli-atesleme-2026-08-21.md`](celiski-canli-atesleme-2026-08-21.md).

# Çelişki tespiti — çift-snapshot canlı ateşleme kanıtı

> Bu belge jüri bulgusuna cevaptır: *"Çelişki tespiti hâlâ 849 belgede SIFIR
> belgeler-arası çelişki buluyor — canlı bir örnek yakala."* Aşağıdaki sonuç
> **üretim kodunun (`src/comparison/contradiction.detect_across`) gerçek
> korpus metniyle fiilen ateşlendiğinin** kanıtıdır — ama dürüstlük gereği
> hemen belirtilmeli: bulunan olay **eşzamanlı bir çelişki değil, bankanın
> kendi kampanyasını uzattığı bir tarihçe (temporal update) olayıdır**. Bunu
> "çelişki" diye satmak `contradiction.py`'nin kendi tasarım ilkesini
> ("sayı değil doğruluk") ihlal eder; bu yüzden aşağıda ikisi ayrı ayrı
> etiketlendi.

## 1. Mekanizmanın tanımı (kod okunarak, uydurulmadan)

Kaynak: `src/comparison/contradiction.py` (modül docstring'i + kod).

- **İki katman:**
  - `detect(campaign)` — **belge içi** çelişki: örn. aynı sayfada iki farklı
    kampanya bitiş tarihi, çakışan-ama-farklı tutar bandı, "masrafsız" iddiası
    + pozitif ücret.
  - `detect_across(campaigns)` — **belgeler arası** çelişki: aynı banka +
    aynı `product_key()` (URL'in son anlamlı yol parçası) altında gruplanan
    ≥2 belge arasında **kâr payı oranı** (`_cross_rule_rate`) veya **kampanya
    bitiş tarihi** (`_cross_rule_end_date`) uyuşmazlığı.
- **Üç savunma** (kod + docstring'den): kapsam koruması (`MAX_SCOPE_CHARS=400`),
  kıyaslanabilirlik koruması (segment-özel sayfalar elenir, aralık-nokta
  kesişimi kabul edilir), normalizasyon (kanonik değer üzerinden kıyas).
- **Belgeler arası bitiş-tarihi kuralının kendi iç eşiği ayrıca sıkı**:
  `end_date_claims()` yalnız `_END_PATTERNS`'teki 3 dar kalıpla eşleşen
  iddiaları sayar (ör. `"... 31.07.2026 tarihine kadar ... geçerli"`,
  `"Başlangıç ve Bitiş Tarihi: D1 - D2"`). Bir belgede **tam olarak 1** böyle
  iddia olmalı VE belge kendini `"Süresi Dolmuştur"/"Sona erdi"` diye
  işaretlememiş olmalı (`_SELF_EXPIRED` vetosu) — yoksa kural sessiz kalır.

Bu üçüncü madde, aşağıdaki ölçümün en önemli bulgusudur (bkz. §4).

## 2. Neden "0 belgeler arası çelişki" ölçülmüştü — zaten belgelenmiş sebep

`contradiction.py` docstring'i (2026-07-30, 849 belge) şunu zaten ölçmüş ve
yazmıştı: aynı `source_url`'i paylaşan **32 çift belge** korpusta var, ama
**hiçbirinin metni farklı değil** (byte-özdeş) — çünkü korpus **TEK bir anlık
görüntü**: `data/raw/` her hasat turunda üzerine yazılıyor, önceki tur diskte
kalmıyor. Yani `detect_across` mantıksal olarak doğru çalışıyor ama ona
**gerçekten ayrışan iki belge hiç verilmiyor**. Bu, kod hatası değil, veri
sağlama hattının (pipeline) tek-anlık-görüntü doğası.

## 3. Test edilen hipotez: iki GERÇEK hasat turu var mı, kullanılabilir mi?

Cevap: **evet**. Korpusta iki gerçek hasat turu git tarihinde duruyor:

| Etiket | Commit | Belge sayısı |
|---|---|---:|
| önceki tur | `c3f3b90` (2026-07-30) | 849 |
| sonraki tur | `e05bc83` (2026-08-03) | 1635 |

Ve `src/scraping/snapshot.py` ile bu iki tur zaten karşılaştırılmış:
`data/snapshots/fark-2026-07-30_2026-08-03.json` → **140 `degisti` kaydı**
(aynı URL, farklı `text_hash`/`content_hash`).

**Sayı ile ele alınan adaylar** (`python3 -m scripts.celiski_canli --fire-test`
ile yeniden üretilir):

| Adım | Adet | Ne elendi / neden |
|---|---:|---|
| `degisti` kaydı (aynı URL, hash farklı) | 140 | — |
| İki git blob'u da okunabilen | 140 | 0 elendi (hepsi git'te duruyor) |
| Temiz metin GERÇEKTEN farklı | 140 | (hash zaten temiz metinden — tutarlı) |
| İzlenen finansal alanlardan biri **kanonik** olarak değişmiş | **49** | 91'i biçim/boilerplate gürültüsü (ör. görsel alt-metni, menü sırası) — finansal alan aynı kaldı |

49 adayın alan dağılımı: `kampanya_suresi` 40, `taksit_sayisi` 9, `vade_ay` 4,
`finansman_tutari` 1, `masraf_durumu` 1 (bir belgede birden çok alan
değişebildiği için toplam 49 belgeden büyük).

## 4. Canlı ateşleme testi — üretim `detect_across()` fiilen çalıştırıldı

40 `kampanya_suresi` adayının hepsi aynı ÜRETİM fonksiyonuna (`detect_across`)
verildi (gerçek metinden kurulmuş `Campaign` nesneleriyle, sentetik veri YOK).
Sonuç: **6/40 gerçekten `Contradiction(kind="capraz_kampanya_bitisi")`
üretti**; kalan 34'ü üretmedi.

**Neden 34 değil 6 — ölçülmüş sebep:** `end_date_claims()`'in `_END_PATTERNS`
kalıpları `"31.07.2026 tarihine kadar geçerli"` gibi TEK tarihli veya
`"D1 - D2 tarihleri arasında"` gibi TAM iki tarihli ifadeleri yakalıyor;
ama korpusta en sık geçen biçim `"Kampanya 1 – 31 Temmuz 2026 tarihlerinde
geçerlidir"` (gün-gün + TEK ay adı) — bu format `_END_PATTERNS`'te YOK.
Buna karşılık genel alan çıkarıcı `extract_kampanya_suresi()`
(`src/extraction/rules/extract.py:2087`, `kampanya_tarih_araligi()` üzerinden)
bu formatı sorunsuz ayrıştırıyor — iki kod yolu **kasıtlı olarak farklı
sıkılıkta**: biri gold-set alan çıkarımı için (geniş), diğeri çelişki iddiası
üretmek için (dar, "hayalet üretme" endişesiyle). Bu, `contradiction.py`'de
belgelenmemiş yeni bir gözlem — mevcut docstring bunu saymıyordu.

Bu ölçüm `src/comparison/contradiction.py`'ye **dokunulmadan** elde edildi
(bu ajanın sahiplendiği dosyalar dışına yazma yasağı gereği); bulgu burada
raporlanıyor, koda müdahale edilmedi.

## 5. Seçilen canlı örnek (tam künye)

> **Etiket: TARİHÇE OLAYI (temporal update), ÇELİŞKİ DEĞİL.** İki taraf da
> kendi zamanında doğruydu; banka kampanyayı uzatmış. Ama bu, `detect_across`
> mekanizmasının GERÇEK korpus metniyle, sentetik veri olmadan, üretim
> kodundan bire bir `Contradiction` nesnesi ürettiğinin kanıtıdır — istenen
> "canlı ateşleme".

- **Banka:** Albaraka Türk (`bank_slug=albaraka`)
- **Kampanya:** İstanbul Havalimanı - Hızlı Geçiş Kampanyası
- **URL (her iki turda da aynı):**
  `https://www.albaraka.com.tr/tr/kampanyalar/detay/istanbul-havalimani-hizli-gecis-kampanyasi`

| | Önceki tur | Sonraki tur |
|---|---|---|
| `scraped_at` | 2026-07-30T18:34:40+00:00 | 2026-08-03T16:36:11+00:00 |
| `content_hash` | `8806784116110aac2dd09413c4c645a780eb435260c9e6c23d5a79976063cb53` | `653c2ee0a9b0f13c8d4e1f888db3c5d7a1027ea7ecb9a68cf3043f7af5d6b567` |
| `text_hash` | `99701282e90ad24297c993cf5bf6c9c17fb3084ead7030c2a3f03caf55fa2f96` | `7ddccb59877305591f9520a5bac885bd99978e23bade6ceed48d3b8b4b133ef8` |
| dosya (git ref) | `c3f3b90:app/data/raw/albaraka/live/detay-istanbul-havalimani-hizli-gecis-kampanyasi.txt` | `e05bc83:app/data/raw/albaraka/live/detay-istanbul-havalimani-hizli-gecis-kampanyasi.txt` |
| ilan edilen bitiş | `"Kampanya, 31.07.2026 tarihine kadar geçerlidir."` | `"Kampanya, 31.12.2026 tarihine kadar geçerlidir."` |
| kanonik `kampanya_suresi` | `2026-07-31` | `2026-12-31` |

**`detect_across()`'un ürettiği gerçek `Contradiction` çıktısı**
(`python3 -m scripts.celiski_canli --fire-test` ile yeniden üretilir):

```json
{
  "kind": "capraz_kampanya_bitisi",
  "detail": "'istanbul-havalimani-hizli-gecis-kampanyasi' kampanyası iki sayfada farklı bitiş tarihiyle yayımlanmış: 2026-07-31 ve 2026-12-31.",
  "fields": ["kampanya_suresi"],
  "scope": "cross",
  "match_key": "albaraka/istanbul-havalimani-hizli-gecis-kampanyasi",
  "evidence": [
    {
      "bank": "albaraka",
      "source_url": "https://www.albaraka.com.tr/tr/kampanyalar/detay/istanbul-havalimani-hizli-gecis-kampanyasi",
      "field_name": "kampanya_suresi",
      "value": "2026-07-31",
      "raw_value": "31.07.2026",
      "source_span": "Kampanya, 31.07.2026 tarihine kadar geçerli",
      "span_start": 1522,
      "span_end": 1532
    },
    {
      "bank": "albaraka",
      "source_url": "https://www.albaraka.com.tr/tr/kampanyalar/detay/istanbul-havalimani-hizli-gecis-kampanyasi",
      "field_name": "kampanya_suresi",
      "value": "2026-12-31",
      "raw_value": "31.12.2026",
      "source_span": "Kampanya, 31.12.2026 tarihine kadar geçerli",
      "span_start": 1522,
      "span_end": 1532
    }
  ]
}
```

Aynı ateşleme deseninde 5 örnek daha var (aynı ölçümün parçası, tekrar
üretilebilir): Albaraka "Sabiha Gökçen Havalimanı Hızlı Geçiş" (2026-07-31 →
2026-12-31), Albaraka "Yolcu 360 Yurt Dışı/Yurt İçi Uçak Bileti" (ikisi de
2026-07-31 → 2026-12-31), Hayat Finans "Troy Mağaza Fırsatları" ve "Xiaomi
Ürünlerinde Finansman Avantajı" (ikisi de 2026-07-31 → 2026-08-31).

## 6. Neden bu üretim `scan.py`'de KENDİLİĞİNDEN ateşlenmiyor

`python3 -m src.comparison.scan` bugün çalıştırıldığında bu 6 örnek de dahil
**hiçbiri tetiklenmez** — sebep §2'de zaten açıklanan tek-anlık-görüntü
kısıtı: `data/raw/` diskte SADECE en son turu tutuyor (2026-07-30'un dosyası
2026-08-03 hasadıyla üzerine yazıldı). `detect_across` iki `Campaign`
nesnesine aynı anda ihtiyaç duyar; onları sağlamanın tek yolu ya (a) geçmiş
turu git blob'undan/`data/snapshots/` arşivinden okuyup güncel korpusla aynı
`scan()` çağrısına eklemek, ya da (b) bir sonraki hasat turunda AYNI kampanya
tekrar değişirse doğal olarak oluşacak yeni bir `degisti` çiftini beklemek.
Bu betik (a)'yı manuel yaptı; üretime kalıcı olarak eklemek (`scan.py`'ye
`--include-snapshot <label>` gibi bir bayrak) **bu ajanın sahiplenmediği**
`src/**` dosyalarına dokunmayı gerektirir — bu yüzden burada önerilip
uygulanmadı.

## 7. Dürüst sonuç

- **Gerçek belgeler-arası "iki taraf da doğru ama çelişiyor" örneği: 0.**
  Bu ölçüm önceki (849 belge, 2026-07-30) ölçümü DOĞRULUYOR, çürütmüyor.
- **Gerçek belgeler-arası "tarihçe/temporal update" örneği: 6** (yukarıda
  künyelenen İstanbul Havalimanı örneği dahil), üretim `detect_across()`
  fonksiyonundan **fiilen** `Contradiction` nesnesi üretilerek doğrulandı —
  sentetik veri yok, tamamı git geçmişindeki gerçek hasat metni.
- **Mekanizmanın gerçek bir "iki kaynak aynı anda çelişiyor" olayında
  ateşlenmesi için gereken koşul:** ya (a) iki bankanın/şubenin AYNI ürünü
  gerçekten farklı anlatan İKİ AYRI belgesi tek bir hasat turunda aynı anda
  korpusta bulunmalı (bugüne kadar 0 kez gözlendi, 1782 belgede de
  `product_key` eşleşen gruplar hâlâ ya segment-özel ya da tutarlı), ya da
  (b) tarihçe verisi (bu belgedeki gibi) kasıtlı olarak "geçmiş sürüm +
  güncel sürüm" etiketiyle korpusa dahil edilmeli — bu durumda dürüst etiket
  "çelişki" değil "kampanya güncellemesi tarihçesi" olur.
