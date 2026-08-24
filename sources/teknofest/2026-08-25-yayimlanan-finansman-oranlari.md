---
title: "Bankaların kendi yayımladığı finansman oranları — 7 banka, 154 kayıt"
tags: [kaynak, finansman-orani, kar-payi, oran-hasadi, veri-toplama, olcum]
source: "app/data/raw/<banka>/rates/quotes.jsonl · 7 banka hesaplama ucu"
date: 2026-08-25
status: stable
---

# Yayımlanan finansman oranları

## goal

Şartname §5.7'nin birinci karşılaştırma ölçütü *"En Düşük Kâr Payı Oranı"*.
Kampanya korpusunda `kar_payi_orani` yalnız **164 / 2.708 belgede (%6,1)**
dolu; ölçüt bu alana dayandığı için kıyas ya boş ya çok dar kalıyordu.

Sorulması gereken soru, boşluğun bir çıkarım kusuru mu yoksa veri gerçeği mi
olduğuydu ([[kampanya-metninde-olmayan-oran-banka-yayinindan]]).

## what-was-done

### 1. Boşluğun bir çıkarım kusuru OLMADIĞI ölçüldü

| kanıt | ölçüm | sonuç |
|---|---|---|
| EVREN `llm-large` boşluk doldurma sondajı | 2026-08-25, 60 aday belge | **0 kabul** |
| Yerel `qwen2.5:7b` sondajı | 2026-08-24, 30 belge | **0 kabul** |
| Metnin okunması | `%` geçen ama alanı boş belgeler | *gecikme kâr payı formülü* |

İki sondajda da iki kabul kapısı (dayanak + alan,
[[llm-yalniz-kural-bosluklarini-doldurur]]) çalıştı; hiçbir aday geçemedi.
Üçüncü kanıt en anlatıcısı: yakalanmayan yüzdelerin çoğu *"en yüksek cari kâr
payı oranlarının %50 fazlası"* biçiminde **gecikme** formülü, kampanyanın oranı
değil.

Bilgi o metinlerde yok. Bankalar oranı **hesaplama araçlarında** yayımlıyor.

### 2. Dört yeni adaptör yazıldı

`src/scraping/rates.py` içine `ZiraatKatilimAdapter`, `HayatFinansAdapter`,
`DunyaKatilimAdapter`, `TomKatilimAdapter` eklendi. Finansman oranı taşıyan
banka sayısı **3 → 7**.

| banka | yöntem | uç | ürün | kayıt |
|---|---|---|---:|---:|
| Dünya Katılım | `rate-api` | `dunyakatilim.com.tr/LoanCheckRate` | 6 | **56** |
| Türkiye Emlak Katılım | `rate-api` | `emlakkatilim.com.tr/Plugins/CalculateLoansProduct` | 5 | **42** |
| Ziraat Katılım | `rate-api` | `ziraatkatilim.com.tr/ajax/get-vade` | 17 | **31** |
| Albaraka Türk | `rate-catalog` | `albaraka.com.tr/tr/hesaplama-araclari/finansman-hesaplama` | 16 | **16** |
| Hayat Finans | `rate-api` | `hayatfinans.com.tr/api/integration/calculateloansproduct` | 1 | **3** |
| Kuveyt Türk | `rate-browser` | `kuveytturk.com.tr/.../arac-finansmani` | 3 | **3** |
| T.O.M. Katılım | `rate-api` | `webintegration.tombank.com.tr/.../GetLoanPayBackPlan` | 1 | **3** |
| **Toplam** | | | | **154** |

Toplama [[python-tabanli-veri-toplama]] kararına ve `robots.txt` uyumuna bağlı
kalarak yapıldı (domain başına 2 sn gecikme).

### 3. Vakıf Katılım segment oranları — robots engelli, elle indirildi

Vakıf Katılım oranlarını HTML'de hiç yayımlamıyor; tek kaynak
`/documents/PerakendeBankacilik/kar-paylasim-oranlari.pdf` ve bankanın
`robots.txt`'i `/documents/` yolunu **açıkça** kapatıyor (yalnız
`.jpg/.png/.jpeg` izinli). Bu bir kaza değil, bankanın bilinçli tercihi; kod
onu `VakifKatilimBlockedAdapter` ile zaten kayıt altına alıyordu.

Şartname §5.1 böyle bir belge için elle toplamaya izin veriyor. PDF elle
indirildi (`data/raw/vakif-katilim/manual/`) ve `scripts/vakif_paylasim_pdf.py`
**yalnız yerel dosyayı** okuyor: ağa çıkmıyor, tarayıcı taklit etmiyor, robots
kuralını dolanmıyor. Engellenen şey otomatik gezinmedir; belgenin kendisi
kamuya açık bir yayın.

Sonuç: **103 kayıt · 13 segment · TRY/USD/EUR/XAU.** Çıktı şeması
`kt_paylasim_pdf.py` ile birebir aynı, böylece iki banka aynı yüzeyden
okunuyor. Segment ayrımı burada da gerçek:

```
250 – 99.999 TL    → 85 / 15
100.000 TL ve üzeri → 90 / 10
```

Küçük bakiyeli müşteri, merkezî TKBB verisinde görünen orandan beş puan düşük
oran alıyor. Aynı boşluk Kuveyt Türk'te ölçülmüştü
([[merkezi-veri-segment-ayrimini-gizliyor]]); artık **iki bankada** kapalı
(144 + 103 kayıt).

Ayrıştırmada iki ölçülmüş hata düzeltildi: ① *"Çeyiz ve Konut Hesabı"*
tablosunun 95/5 oranı, kendinden önceki USD ara dönem bölümünün bağlamını
devralıp **sahte** bir kayıt üretiyordu — katılma dışı bölüm başlığı artık
bağlamı kapatıyor. ② Ara dönem satırları ürün adıyla başladığı için dilim
deseni açılış bakiyesini kaçırıyordu (20.000 / 150.000). Vade sütunları
**başlıktan** okunuyor, sabit sıradan değil: ALTIN tablosunda "1 Ay" sütunu yok
ve sabit sıra varsayımı bütün altın satırlarını bir sütun kaydırırdı.

### 4. Üç yüzey açıldı

- `GET /finansman-oranlari` — `src/api/routers/finansman_orani.py`
- Panel: *Karşılaştırma* sekmesinde **dördüncü görünüm** — *Yayımlanan
  finansman oranları*; kaynak farkı başlıktan hemen sonra yazıyor
- Sohbet: `finansman_orani` yolu — yapısal sorgu **boş dönerse** devreye giren
  yedek; tek banka adı geçen soru bu yola hiç girmiyor

Yön (`yon`) sunucudan okunuyor: katılmada yüksek oran iyi, finansmanda düşük
oran iyi. Yıllık maliyet oranı uydurulmuyor; banka yayımlamamışsa
"yayımlanmadı" yazıyor.

## files-changed / touched

- `app/src/scraping/rates.py` — dört yeni adaptör
- `app/src/domain/yayimlanan_oran.py` — yeni
- `app/src/api/routers/finansman_orani.py` — yeni · `src/api/main.py` (kayıt)
- `app/src/chatbot/finansman_orani.py` — yeni · `bot.py` · `terim_cevabi.py`
- `app/web/app/components/FinansmanOranPanel.tsx` — yeni ·
  `ComparePanel.tsx` · `lib/api.ts`
- `app/scripts/vakif_paylasim_pdf.py` — yeni · `scripts/baslat.sh` (`.env`)
- `app/data/raw/{ziraat-katilim,hayat-finans,dunya-katilim,tom-katilim}/rates/quotes.jsonl`
- `app/data/raw/vakif-katilim/rates/vakif-paylasim-pdf.jsonl` — 103 kayıt
- `app/tests/test_yayimlanan_oran.py` · `test_rates_yeni_adaptorler.py` ·
  `test_vakif_paylasim_pdf.py`

## decisions

- [[katilma-orani-iki-ayri-buyukluk]] — ayrı büyüklük ayrı tablo; bu kol da
  aynı kurala uyuyor (kayıtlar `extracted_fields`e yazılmıyor)
- [[python-tabanli-veri-toplama]] — robots uyumu ve gecikme disiplini

## issues

- [[kampanya-metninde-olmayan-oran-banka-yayinindan]] — boşluğun kendisi ve
  kapatılışı
- [[merkezi-veri-segment-ayrimini-gizliyor]] — segment kırılımı, ikinci banka
- [[turkce-buyuk-harf-yerel-duyarliligi]] — `casefold()` Ziraat'ın taşıt
  ürünlerini sessizce düşürüyordu

## open-threads

- **Üç banka dışarıda:** Vakıf Katılım finansman oranını hiç yayımlamıyor
  (PDF'te yalnız katılma tarafı var), Türkiye Finans yalnız katılma hesabı
  tablosu yayımlıyor, Adil Katılım hiç oran yayımlamıyor.
- Oranlar bankanın hesaplama aracından geliyor; **bağlayıcı fiyat değil** —
  her kayıt bankanın kendi uyarısını `note` alanında taşıyor.
- Ziraat Katılım'da oran ürün başına sabit: tutar ve vade ile değişmiyor.
  Diğer bankalarda vade kademesi oranı değiştiriyor; tek bir "banka oranı"
  cümlesi bu yüzden kurulmuyor.

## Sources

- `app/data/raw/*/rates/quotes.jsonl` — `kind == "finansman"` sayımı: **154**
- `app/data/raw/vakif-katilim/rates/vakif-paylasim-pdf.jsonl` — **103** kayıt
- `app/data/raw/kuveyt-turk/rates/kt-paylasim-pdf.jsonl` — **144** kayıt
- `app/src/domain/yayimlanan_oran.py` — modül başlığı, ölçüm kaydı 2026-08-25
- `app/data/demo.db` — `kar_payi_orani`: 146 kural + 18 LLM = **164** / 2.708

## Related

- [[2026-08-24-tkbb-kar-payi-veri-seti]] — kardeş veri kolu (katılma tarafı)
- [[tkbb-kar-payi-veri-seti]] — merkezî kaynak varlığı
- [[kar-payi-orani]] — kavram; bu kaynak onun finansman ayağını besliyor
- [[urun-karsilastirma]] — kıyasın kendisi
- [[dashboard]] · [[chatbot]] — veriyi gösteren iki yüzey
