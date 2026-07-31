# Şartname → Kod Eşleme Tablosu

**Belge amacı:** TEKNOFEST 2026 TYDA 2. Senaryo şartnamesinin her maddesinin
kod tabanındaki karşılığını göstermek. Jüri bir maddeyi okuduğunda hangi
dosyaya bakacağını, hangi testin onu koruduğunu ve **hangi kısmın eksik
olduğunu** buradan görür.

**Son güncelleme:** 2026-07-31 · **Test sayısı:** 695 · **Korpus:** 849 belge

> **Dürüstlük kuralı:** Bu tabloda "✅" yalnızca *koşturulup doğrulanmış*
> kalemler için kullanılır. Yapılmamış iş "❌", kısmi iş "⚠️", ölçülmemiş
> iş "⏳" ile işaretlenir ve gerekçesi yazılır. Bu belge bir pazarlama
> metni değil, bir denetim aracıdır.

---

## §5.1 Veri Toplama

> *"Veri seti BDDK'nın resmî web sitesinde yer alan Katılım Bankacılığı
> alanında faaliyet gösteren kuruluşların tümünü içermelidir. […] python
> tabanlı veri toplama araçları, kütüphaneleri, web scraping yöntemleri
> veya manuel veri toplama teknikleri kullanılarak elde edilmelidir."*

| Beklenti | Karşılık | Durum |
|---|---|---|
| BDDK listesindeki tüm katılım bankaları | `config/banks.yaml` — 10 banka, config-driven | ✅ |
| Python tabanlı toplama | `src/scraping/` (`collector.py`, `discover.py`, `fetcher.py`, `harvest_products.py`) | ✅ |
| Web scraping | `requests`+`BeautifulSoup`; JS'li sayfalar için Playwright (`fetcher.BrowserFetcher`) | ✅ |
| Provenance | `source_url` · `scraped_at` · `content_hash` · `collection_method` her belgede | ✅ |
| robots.txt uyumu | `src/scraping/robots.py`; varsayılan **uyumlu**, `--ignore-robots` bilinçli opt-out | ✅ |

**Ölçülmüş sonuç:** 849 belge, 10 banka. Dağılım dengesiz — Adil Katılım'da
6 belge, T.O.M.'da 2 ürün sayfası (sitelerinde katalog yok). Bu, veri
setinin bilinen sınırıdır ve gizlenmemektedir.

**Testler:** `tests/test_scraping_provenance.py` (28), `tests/test_scraping_pipeline.py` (6)

---

## §5.2 Metin Analizi Yeteneği

> *Model şu ifade biçimlerini yorumlayabilmelidir:* `"%2,05 kâr payı oranı"` ·
> `"avantajlı kâr payı fırsatı"` · `"özel oranlı finansman"` ·
> `"düşük maliyetli finansman"`

| İfade | Karşılık | Durum |
|---|---|---|
| `"%2,05 kâr payı oranı"` (sayısal) | `extract_kar_payi` — **iki yönlü**: sayı anahtar kelimeden önce de sonra da olabilir | ✅ |
| `"avantajlı kâr payı fırsatı"` | `synonyms.qualitative_rate_claim()` | ✅ tanınır |
| `"özel oranlı finansman"` | aynı | ✅ tanınır |
| `"düşük maliyetli finansman"` | aynı | ✅ tanınır |

**Tasarım kararı — nitel iddiadan sayı üretilmez.** Son üç ifadede **sayı
yoktur**. Bunlardan bir oran türetmek halüsinasyondur ve `CLAUDE.md` §19'un
("bilgi yoksa null") doğrudan ihlalidir. Sistem iddianın **varlığını**
kaydeder, değerini uydurmaz.

**Ölçülmüş sonuç:** 849 belgenin **54'ünde** nitel iddia var; **45'inde hiç
sayısal oran yok**. Bu 45 belge, sayısal oran veren kampanyalarla
**doğrudan kıyaslanamaz** — adil kıyas garantisi (§5.7) bunu işaretler.

> ⚠️ **31 Tem'de düzeltilen hata:** Şartnamenin manşet örneği
> `"%2,05 kâr payı oranı"` **çalışmıyordu** — çıkarıcı yalnız ileri
> bakıyordu. Dahası `"%1,89 kâr payı oranı ile 120 aya kadar"` ifadesinde
> **120'yi (vadeyi) oran olarak** döndürüyordu. Bkz. `tests/test_kar_payi_yon.py`.

**Testler:** `tests/test_kar_payi_yon.py` (17), `tests/test_sartname_terminoloji.py` (15)

---

## §5.3 Finansal Bilgi Çıkarımı

> *Çıkarılan bilgilerin yapılandırılmış veri formatına dönüştürülmesi.*

Şartnamenin tablosu dört grupta 13 alan sayıyor. **13/13 karşılanıyor:**

| Grup | Alan | Çıkarıcı |
|---|---|---|
| Finansman | Kâr Payı Oranı | `extract_kar_payi` |
| | Finansman Tutarı | `extract_finansman_tutari` |
| | Vade Süresi | `extract_vade` |
| | Taksit Sayısı | `extract_taksit` |
| | Tahsis Ücreti | `extract_tahsis_ucreti` |
| | Masraf Bilgisi | `extract_masraf` |
| Kampanya | Kampanya Türü | `ner/classifier.py` |
| | Ödül Miktarı | `extract_odul_miktari` |
| | İndirim Oranı | `extract_indirim_orani` |
| | Alışveriş Puanı | `extract_alisveris_puani` |
| | Kampanya Süresi | `extract_kampanya_suresi` |
| | Kampanya Koşulları | `extract_kampanya_kosullari` |
| Hedef Kitle | 4 segment | `extract_hedef_kitle` |

Hepsi `src/extraction/rules/extract.py`. Yapılandırılmış çıktı:
`src/schemas.py` → `ExtractedField` (kanonik değer + güven + kaynak offset'i).

**Kaynak izlenebilirliği:** Her alan `span_start`/`span_end` taşır ve
`verify_span()` ile `text[start:end] == raw_value` kendi kendini denetler.
Offset'ler veri tabanında da saklanır (`schema.sql`, `repository.py`).

**Testler:** `test_extract.py`, `test_kampanya_alanlari.py` (20),
`test_confidence_span.py` (16), `test_db_span_persistence.py` (10),
`test_masraf_precision.py` (14)

---

## §5.4 Kampanya Türünün Belirlenmesi

Şartname 8 tür sayıyor. **8/8 üretilebiliyor** (849 belgede ölçüldü):

| Tür | Belge | Tür | Belge |
|---|---:|---|---:|
| Yatırım Ürünü | 186 | Konut Finansmanı | 106 |
| İhtiyaç Finansmanı | 146 | Taşıt Finansmanı | 49 |
| Kart | 145 | Alışveriş Puanı | 13 |
| Finansman | 135 | Yeni Müşteri | 9 |

Sınıflanamayan: 60 belge (%7,1) — çoğu kurumsal/bilgi sayfası.

`src/extraction/ner/classifier.py` — `RuleHintClassifier` (üretim yolu) +
`BerturkClassifier` (fine-tune yolu, ağırlık verilirse devreye girer).

> ⚠️ **Bilinen geçmiş hata:** Alt-dize eşleşmesi (`"ev"` → `"devam"`,
> `"seviye"`) korpusun **%48'ini** sahte Konut Finansmanı yapıyordu.
> `synonyms.keyword_pattern()` sözcük sınırı uyguluyor.

---

## §5.5 Katılım Bankacılığı Terminolojisine Uyum

Şartname **beş kavramı** isim isim tanımlıyor. **5/5 karşılanıyor:**

| Kavram | Karşılık | Korpusta |
|---|---|---:|
| Kâr Payı Oranı | `extract_kar_payi` + `synonyms.FIELD_TRIGGERS` | 47 belge |
| **Finansman Maliyeti** | `TERMINOLOGY_5_5` + `terminology_hits()` | 53 belge |
| **Katılım Fonu** | aynı; ayrıca §5.4 "Yatırım Ürünü" türüne bağlı | 173 belge |
| Masrafsız Finansman | `normalize_fee_status` → `has_fee=False` | 196 belge |
| Avantajlı Finansman | `qualitative_rate_claim()` — nitel, sayısal değeri yok | 54 belge |

> ⚠️ **31 Tem'de kapatılan boşluk:** "Finansman maliyeti" ve "katılım fonu"
> **yalnızca LLM prompt'unda** (`llm/schema.py:241,244`) tanımlıydı. LLM
> kapalıyken — ki offline varsayılanımız bu — sistem bu iki kavramı hiç
> bilmiyordu. Toplam **226 belgeyi** etkiliyordu.

**Kritik ayrım:** *Finansman maliyeti* (toplam geri ödeme, **TL**) ile *kâr
payı oranı* (**%**) aynı şey değildir. Aynı alana yazmak karşılaştırmayı
sessizce bozar; şema bunu açıkça ayırıyor ve bir test kilitliyor.

**Chatbot terminoloji kapısı:** Kullanıcı "faiz" derse kabul edilir ama
yanıtta **asla üretilmez** — nazikçe "kâr payı" olarak düzeltilir.
`src/chatbot/safety.py`, 30 soruluk ölçülmüş set: **30/30**.

---

## §5.6 Bilgilerin Standart Formata Dönüştürülmesi

> *`%2,05`, `% 2.05` ve `2.05 %` aynı değer. `500 TL`, `500₺`, `500 Türk
> Lirası` aynı değer.*

`src/normalization/normalize.py`:

| Dönüşüm | Fonksiyon |
|---|---|
| Oran → decimal | `normalize_rate` |
| Para → `{value, currency}` | `normalize_money` |
| Vade → ay (int) | `normalize_term` |
| Tarih → ISO-8601 | `normalize_date` |
| TR sayı (`1.500,00`) | `parse_tr_number` |
| Negasyon (`masrafsız` = 0, bilgi yok değil) | `normalize_fee_status` |
| Dejenere aralık `{min:X,max:X}` → `X` | `collapse_degenerate_range` |

**Türkçe doğruluk:** `str.lower()` Türkçe için **hatalıdır** (`I↔ı`, `İ↔i`).
`preprocessing/clean.py` içindeki `tr_fold`/`tr_fold_ascii` kullanılır.
Bu tuzak projede **üç kez** hata üretti (`'ÜCRETSİZ'` → `has_fee=True`
işaret dönmesi dahil).

**Testler:** `test_normalize.py` (22), `test_turkish_fold.py` (18)

---

## §5.7 Ürünlerin Karşılaştırılması

Şartname **beş** karşılaştırma ölçütü sayıyor:

| Ölçüt | Karşılık | Durum |
|---|---|---|
| En Düşük Kâr Payı Oranı | `compare.rank()` · `_LOWER_IS_BETTER` | ✅ |
| En Yüksek Ödül Miktarı | `compare.rank()` · `_HIGHER_IS_BETTER` | ✅ |
| En Uzun Vade Seçeneği | aynı | ✅ |
| En Düşük Masraf | `_LOWER_IS_BETTER` | ✅ |
| **En Avantajlı Kampanya** | `compare.rank_advantageous_by_type()` — **tür içinde** bileşik | ✅ |

**Neden tür içinde.** Şartnamenin kendi çalışılmış örneği (s.12–13) **aynı
ürünü** karşılaştırıyor: A, B ve C Bankası'nın *konut finansmanı*
kampanyaları, tek tabloda, banka başına bir satır.

Ölçüm de bunu gerektiriyordu: 495 skorlanabilir kampanyanın yalnızca
**%9,5'inde** kâr payı oranı var (Kart 114 kampanyanın 3'ü, Alışveriş Puanı
13'ün 0'ı). Türler arası tek listede kâr payına hangi ağırlık verilirse
verilsin %90 için yeniden dağıtılır. Dahası bir kredi kartı kampanyası ile
bir konut finansmanı birbirinin alternatifi değildir.

**Yöntem:** sıralama tabanlı normalizasyon (min-max değil — çıkarım kaynaklı
uç değerler sıralamayı yok ediyordu), **grup içinde** koşar. Ağırlıklar
`DEFAULT_WEIGHTS`, her biri `WEIGHT_RATIONALE`'de tek cümle gerekçeli ve
`weight_manifest()` ile API'den okunabilir. 3'ten az kampanyası olan tür
sıralanmaz ama **gizlenmez** — sayı ve sebep raporlanır.

**Adil kıyas:** eksik alan sıfır puan **değildir**; skor yalnız kapsanan
ölçütler üzerinden ortalanır, `coverage` ayrı raporlanır, `<0.5` ise
`comparable=False` + listenin sonu.

**Adil kıyas garantisi:** Yalnızca aynı birime normalize edilmiş alanlar
kıyaslanır. Koşullar farklıysa `comparable=False` + gerekçe notu döner;
uydurma sıralama yapılmaz.

---

## §5.8 Veri Ön İşleme Süreçlerinin Kullanılması

`src/preprocessing/clean.py`: `strip_html` · `normalize_text` ·
`split_sentences` · `tr_fold` / `tr_fold_ascii` / `tr_upper`.
İçerik çıkarımı için `trafilatura` (opsiyonel, GPL riski nedeniyle teslim
imajından çıkarıldı — `BeautifulSoup` birincil).

> ⚠️ **31 Tem'de bulunan hata:** `bs4` teslim imajında yoktu ve
> `collector._extract_main_text` sessizce ham HTML'e düşüyordu. Teslim imajı
> geliştirme ortamından **farklı metin** üretiyordu (6232 vs 4317
> karakter/belge, %44 gürültü) ve testler yeşil olduğu için görünmüyordu.

---

## §5.9 On-Premise (Kurum İçi) Uygulanabilirlik

| Beklenti | Kanıt | Durum |
|---|---|---|
| Kurum içi sunucularda çalışabilme | `docker-compose.yml` — tek komut | ✅ |
| Dış servislere bağımlı olmadan çalışma | `--network none` içinde 607 test + eval + API | ✅ **ölçüldü** |
| Veri güvenliği / veri kurum dışına çıkmaz | Negatif kontrol: ağ probu `--network none` içinde 4/4 engellendi | ✅ **ölçüldü** |
| Tekrar-üretilebilirlik | Üç imaj **digest pin**'li (`@sha256:`) | ✅ |

**Ölçülmüş gecikme** (konteyner, 1696 örnek):

| Yol | p50 | p95 | p99 |
|---|---|---|---|
| kural-only | **1,03 ms** | 4,80 ms | 6,30 ms |
| hibrit (LLM'siz) | 1,50 ms | 6,92 ms | 8,86 ms |
| chatbot | 12,48 ms | 325,02 ms | 351,36 ms |

Verim 21.087 belge/dk · tepe RSS 100,4 MB · imaj 96,5 MiB.
api+postgres ≈255 MB, tam GPU yığını ≈10,6 GB — **40× fark**, "önce kural"
mimarisinin paket boyutundaki karşılığı.

**Negatif kontrolün pozitif kontrolü:** Aynı ağ probu, ağ **açıkken** 4/4
ulaşıyor. Bu olmadan "engellendi" sonucu hiçbir şey kanıtlamaz.

Ayrıntı: [`OFFLINE-KANIT.md`](OFFLINE-KANIT.md), [`kaynak-tuketimi.md`](kaynak-tuketimi.md)

> ⏳ **Ölçülmedi:** GPU profilleri (vLLM, Ollama+GGUF), gerçek hibrit
> gecikmesi, model ağırlığı SHA-256 tablosu — bu ortamda GPU ve indirme yok.

---

## §5.10 Açık Kaynak Kod Yaklaşımı

| Beklenti | Karşılık | Durum |
|---|---|---|
| Tüm kod açık kaynak | Apache-2.0 (`LICENSE`), depo public | ✅ |
| Lisans problemi çıkarabilecek çözüm kullanılmaz | `docs/model-license-audit.md` — her modelin `base_model` zinciri **köke kadar** takip edildi | ✅ |
| Modeller ölçeklenebilir konumlandırılmalı | İki kademe: Trendyol-8B/Qwen3-8B (kalite) · Qwen3-4B GGUF (CPU demo) | ✅ |

**Kullanılanlar** (hepsi zincir doğrulamalı): Trendyol-LLM-8B-T1
(Apache-2.0, `Qwen3-8B-Base → Qwen3-8B`) · Qwen3-8B/4B (Apache-2.0) ·
BERTurk (MIT) · GLiNER v2.1 (Apache-2.0, mDeBERTa/MIT tabanlı) ·
NuExtract-2.0-8B (MIT, Qwen2.5-VL-7B/Apache-2.0 tabanlı)

**Reddedilenler** (kart alıntısıyla): TURNA — *"solely for **non-commercial**
academic research purposes"* · UniNER — CC BY-NC **+** Llama tabanlı ·
NuExtract-2.0-**4B** — tabanı Qwen Research License (aynı ailenin 8B/2B'si
temiz) · Llama/Gemma tabanlı her şey

> **Kayda geçen ders:** Türetilmiş bir modelin `license` etiketi Apache-2.0
> görünse de taban zinciri kirli olabilir (NuExtract-4B). Tersi de doğru:
> temkinle bloke edilmiş bir model temiz çıkabilir (Trendyol). **Her iki
> yönde de zincir doğrulanmadan karar verilmez.**

---

## §6 Teslim Edilecekler

| Kalem | Durum |
|---|---|
| Çalışan proje kodu + kurulum adımları | ✅ `README.md`, `docker-compose up` |
| Bağımlılık listesi | ✅ `requirements*.txt` · `web/package.json` |
| Veri setine herkese açık indirme bağlantısı (s.18) | ❌ **yapılacak** — GitHub Release |
| Demo videosu | ❌ yapılacak (≤5 dk + 1 dk, şartname iki yerde farklı süre veriyor) |
| Proje dokümantasyonu | ⚠️ kısmi — bu belge, `OFFLINE-KANIT.md`, `model-license-audit.md`, `katilim-bankaciligi-guvenligi.md` hazır |
| Sunum materyali (PDF + PPTX) | ❌ yapılacak |

## §9 Süreç Kuralları

| Kural | Durum |
|---|---|
| En az haftalık GitHub güncellemesi | ✅ `hafta-00`, `hafta-01` |
| `BilisimVadisi2026` etiketi | ✅ depo topic'i |
| Türkiye Açık Kaynak Platformu etiketi | ✅ depo topic'i |
| Nihai lisans Apache-2.0 | ✅ |

---

## Rubrik karşılığı (§7)

| Kriter | Ağırlık | Durum |
|---|---:|---|
| Model Başarısı ve Anlamlandırma | %30 | ⏳ **altyapı hazır, sayı yok** — gold seti üretilmedi. Ölçüm hattı (bootstrap GA + McNemar + kalibrasyon) kurulu ve test edildi. |
| Fonksiyonellik ve Senaryo Kapsamı | %20 | ⚠️ dashboard + chatbot çalışıyor; §5.7'nin 5. ölçütü eksik |
| Teknik İmplementasyon ve Mimari | %20 | ✅ 695 test, CI, değişmez denetimi; ⚠️ pgvector henüz kullanılmıyor |
| On-Prem Uygulanabilirlik | %20 | ✅ ölçülmüş `--network none` kanıtı + negatif kontrol |
| Yenilikçilik ve Yaratıcılık | %10 | ✅ değişmez denetimi · kaynak-span izlenebilirliği · çelişki tespiti · katılım bankacılığı güvenlik kapıları |

**En büyük açık:** Model Başarısı %30 için hâlâ **ölçülmüş bir P/R/F1 yok**.
Sebep gizlenmiyor: kural katmanı gold sete bakılmadan yazıldı, dolayısıyla
250 kayıt gerçek bir **held-out** test setidir; bu bilimsel avantajı korumak
için gold dondurulmadan metrik yayımlanmıyor. Anotasyon hattı hazır
(3406 satır), split protokolü kurulu ve test edilmiş.

---

## Sources
- `raw/teknofest/2026-teknofest-tyda-sartname-2-senaryo.pdf` — §4 (s.6),
  §5.1–§5.10 (s.7–11), Örnek Senaryo (s.12–13), Teslimler (s.13–14),
  Değerlendirme (s.15), Süreç (s.17–19)
- [`model-license-audit.md`](model-license-audit.md) · [`OFFLINE-KANIT.md`](OFFLINE-KANIT.md)
- `app/CLAUDE.md` — mimari kararlar
