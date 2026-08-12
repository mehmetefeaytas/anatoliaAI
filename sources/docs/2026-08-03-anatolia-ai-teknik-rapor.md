---
title: "Anatolia AI Teknik Rapor ve Durum Değerlendirmesi (3 Ağustos 2026)"
tags: [source, teknik-rapor, durum-degerlendirmesi, mimari, teslim, sartname-eslesme, ic-ek]
source: "raw/docs/anatolia-ai-teknik-rapor.md"
date: 2026-08-03
status: stable
---

# Anatolia AI Teknik Rapor ve Durum Değerlendirmesi

> Bu sayfa raporun **A1 alan sorumluluğu** (genel durum, mimari, ekip, takvim,
> şartname madde eşlemesi, uçtan uca hat, teslim durumu) açısından işlenmiş
> özetidir. Model/eval, on-prem kanıt paketi, çıkarım kapsamı, veri toplama ve
> anotasyon başlıkları ayrı ingest'lerde ele alınır; burada yalnızca durum
> düzeyinde anılır.

## goal

Raporun kendi tanımladığı iki amacı var ve **hedef kitleleri farklıdır**:

- **Bölüm A–D** şartname §6.3'ün istediği "Proje Dokümantasyonu"dur; jüriye gider
  ve on zorunlu başlığın tamamını kapsar.
- **Bölüm E** iç ektir: eksikler, riskler, açık sorular, yol haritası, rakip
  analizi ve uzman toplantısı soruları. **Teslimde çıkarılır**
  → [[rapor-a-d-juri-e-ic-ek]].

Raporun kendi koyduğu tek kural: *"her sayı ya bir komutun çıktısıdır ya da bir
dosyaya referans verir. Ölçülmemiş şey ⏳ ile işaretlenir; tahmin yazılmaz."*
Gerekçe üslup değil kural: şartname §15.1 sonuç manipülasyonunu diskalifiye
sebebi sayıyor ve rubriğin %30'u ölçüme dayanıyor.

İşaret dili: ✅ koşulup doğrulandı · ⚠️ kısmi · ⏳ ölçülmedi · ❌ yapılmadı.

## what-was-done

### Künye (rapor kapağı)

| | |
|---|---|
| Takım | Anatolia AI → [[anatolia-ai-takimi]] |
| Ekip | Mehmet Efe Aytaş (kaptan), Irmak Altay, Ayça Engindeniz, Ecegüneş Dağ |
| Rapor tarihi | **3 Ağustos 2026** |
| Teslim tarihi | **26 Ağustos 2026 — kalan 23 gün** |
| Kod durumu | **39 test dosyası · 890 test yeşil · ruff kapısı temiz · commit `03835ce`** |
| Korpus | **849 belge · 10 banka · 2.204 çıkarılmış alan** |
| Lisans | Apache-2.0 → [[apache-2-acik-kaynak-lisansi]] |

### Tek paragrafta durum (raporun yönetici özeti)

Sistem uçtan uca çalışıyor: 10 katılım bankasının resmî sitelerinden toplanan
849 belge, kural tabanlı çıkarımla 2.204 alana dönüştürülmüş, hepsi kaynak
metindeki karakter offsetine bağlı, PostgreSQL ve SQLite üzerinde birebir aynı
sonucu veriyor, [[dashboard]] ve [[chatbot]] ile sunuluyor, ve internet erişimi
olmadan (`docker run --network none`) ölçülmüş biçimde ayağa kalkıyor.

**Rubriğin %70'i** (fonksiyonellik, teknik implementasyon, on-prem, yenilikçilik)
ölçülmüş kanıta dayanıyor. **Rubriğin en ağır maddesi Model Başarısı %30 için
hâlâ ölçülmüş bir precision/recall/F1 yok** — ölçüm altyapısının tamamı yazılmış
ve test edilmiş, ama hiç koşulmamış. Detay → [[rubrik-agirlik-haritasi]].

### Uçtan uca mimari — 11 aşama, tek orkestrasyon

Sistem tek bir fonksiyonda toplanır: `src/pipeline.py:149 run_pipeline()`
→ [[run-pipeline]]. On bir aşama, her biri bağımsız test edilebilir bir modül:

| # | Aşama | Modül | Ana giriş noktası |
|---|---|---|---|
| 1 | Veri toplama | `src/scraping/` | `collector.py:170 collect_from_fixtures()`, `:227 collect_live()` |
| 2 | Ön işleme | `src/preprocessing/clean.py` | `:112 normalize_text()`, `:30 tr_fold()` |
| 3 | Sınıflandırma (8 tür) | `src/extraction/ner/classifier.py` | `:26 RuleHintClassifier` |
| 4 | Kural çıkarımı (12 alan) | `src/extraction/rules/extract.py` | `:856 extract_all()` |
| 5 | LLM katmanı | `src/extraction/llm/extractor.py` | `:97 LLMExtractor.extract()` |
| 6 | Uzlaştırma | `src/extraction/reconcile.py` | `:69 reconcile()` |
| 7 | Normalizasyon | `src/normalization/normalize.py` | `:75 normalize_rate()`, `:135 normalize_money()` |
| 8 | Çelişki tespiti | `src/comparison/contradiction.py` | `:323 detect()` |
| 9 | Depolama | `src/db/factory.py` | `:52 create_repository()` |
| 10 | Karşılaştırma | `src/comparison/compare.py` | `:82 rank()`, `:454 rank_advantageous_by_type()` |
| 11 | Sunum | `src/api/main.py` + `web/` | `:236 build_app()` |

Bu hat, [[teknik-cozum-mimarisi]] sentezinde şartnameden türetilen 8 adımlı
kavramsal hattın **gerçekleşmiş** halidir; aradaki fark uzlaştırma (6) ve
çelişki tespiti (8) aşamalarının eklenmiş olmasıdır.

`src/pipeline.py:50-53` **dört çalışma modu** tanımlar — aynı kod yolu hem üç
belgelik hızlı testte hem 849 belgelik tam korpusta koşar
→ [[dort-calisma-modu]].

### İki veritabanı arka ucu ve ödenen bedel

`src/db/base.py:38` `RepositoryProtocol` **13 metotlu tek bir sözleşme** tanımlar
→ [[repository-protocol]]. SQLite ve PostgreSQL/pgvector bu sözleşmeyi ayrı ayrı
uygular; `create_repository()` `DATABASE_URL` doluysa Postgres'i, boşsa SQLite'ı
seçer.

Bedel ödendi: **depo katmanı dışında SQL yazmak yasaklandı**
→ [[depo-katmani-disinda-sql-yasak]]. Önceden bir `rows()` kaçış kapısı vardı ve
beş yerde ham SQL çağrılıyordu; SQLite `?`, PostgreSQL `%s` yer tutucusu
kullandığı için bu beş çağrı Postgres'te `ProgrammingError` ile düşüyordu — yani
soyutlama kağıt üstündeydi.

**Ölçülmüş parite:** 849 kampanya ve 2.204 alan iki arka uçta birebir aynı;
`test_repo_parity.py` 26 test, `test_pgvector_repository.py` 27 test.

Bunun şartname karşılığı: §7'nin *"kurum sistemlerine entegre edilebilir mimari
yaklaşım"* alt maddesi — kurum hangi veritabanını kullanıyorsa sistem oraya
takılabilmelidir → [[on-premise-uygulanabilirlik]].

### Ortak örüntü: dokuz hatanın hiçbiri çökme değildi

Rapor A8'de on bir problem (P1–P11) kök neden + ölçülen etki + çözüm biçiminde
sayılır ve kendi çıkardığı ders şudur: *"Ortak örüntü: dokuz hatanın hiçbiri
çökme değildi. Hepsi sessizce yanlış değer üretiyordu."* Bu örüntü
[[sessiz-hata]] kavram sayfasında toplandı. Ölçülen üç örnek:

- `str.lower()` Türkçe `İ/I` tuzağı `masraf_durumu` alanını **ters** çeviriyordu
  (P1; projede **üç ayrı yerde** aynı tuzak).
- `float()` Türkçe binlik ayırıcıyı ondalık sanıyordu: `1.500,00 TL` → **1,0 TL** (P2).
- Alt-dize eşleşmesi (`"ev"` ipucu `"devam"`, `"seviye"` içinde) **korpusun
  %48'ini** sahte "Konut Finansmanı" etiketiyle işaretliyordu (P5; 849 belgenin ~408'i).

Raporun kendi ifadesiyle: *"en pahalı hatalar çökmez. Bu hata hiçbir testi
kırmadı, hiçbir istisna fırlatmadı — sadece yarım korpusu yanlış etiketledi ve
dashboard bunu güvenle gösterdi."*

### Şartname madde bazında durum (§5.1–§5.10)

On maddenin tamamı ✅ işaretli; iki maddede açık kalem var (§5.9 x86_64 ⏳,
§5.10 `trafilatura` ⏳). Tam tablo → [[sartname-madde-kod-eslemesi]].

### Rubrik durumu (E1)

| Kriter | Ağırlık | Durum | Kanıt |
|---|---|---|---|
| Model Başarısı | %30 | ⏳ **SAYI YOK** | altyapı hazır (3.406 satır), gold 3 kayıt, `metrics.json` hiç üretilmedi |
| Fonksiyonellik | %20 | ✅ | 5/5 ölçüt · dashboard + chatbot · 849 belge uçtan uca |
| Teknik İmplementasyon | %20 | ✅ | 890 test · ruff kapısı temiz · değişmez denetimi 0 ihlal |
| On-Prem | %20 | ✅ | 14/14 adım · ağ 4/4 engellendi + pozitif kontrol · digest pin |
| Yenilikçilik | %10 | ✅ | span vurgulama · çelişki tespiti · 5 güvenlik kapısı · config onboarding |

### 23 günlük yol haritası (E5)

**Kritik yol seridir** — her adım öncekini bekler; anotasyon gecikirse zincirin
tamamı kayar:

| Sıra | İş | Süre |
|---|---|---|
| 1 | Ön-anotasyon üret | 1 gün |
| 2 | Anotatör CSV'lerini üret | ½ gün |
| 3 | **4 anotatör × ~1,5 sa** | 4–5 gün |
| 4 | IAA hesabı (κ<0,67 ise kılavuz düzeltilip 3'e dön) | ½ gün |
| 5 | Gold üret + dondur | 1 gün |
| 6 | Metrik üret (`run_eval` + `ablation` + bootstrap GA + McNemar) | 2 gün |

Rapor: *"Anotasyon 4 kişiye paralel dağıtılabilen tek iştir — bu yüzden en erken
başlaması gereken kalem odur. **4 Ağustos'ta başlamalı.**"*

Paralel yürüyebilecek işler: veri seti GitHub Release + CC-BY-4.0 (1 gün),
E4'teki tutarsızlıkların düzeltilmesi (2 gün), x86_64 + tam compose doğrulaması
(1 gün), menü metni sızması + `%0` gürültüsü (1–2 gün), demo videosu (3 gün),
sunum PDF + PPTX (3 gün), prova + tampon (2 gün).

**Bilinçli kapsam dışı:** GPU profilleri B/C/D (donanım yok, uydurmak §15.1
ihlali), bge-m3 vektör yolunun devreye alınması, `gliner` kolunun geliştirilmesi,
`rate_nature` sütunu (uzman görüşü alınmadan şema değişmez).

### Raporun kendisi üretilmiş bir artefakt

Rapor elle yazılmadı; üç betikle üretildi (11 gerçek ekran görüntüsü, 12 SVG
grafik, markdown → HTML → PDF) → [[teknik-rapor-uretim-hatti]] ve karar
[[rapor-uretilir-elle-yazilmaz]]. **Yeni bağımlılık eklenmedi**; matplotlib /
reportlab / pandoc kurmak §5.10 lisans denetimini yeniden açacaktı.

### Farklılaşma tezi ve kendi karşı-argümanı (E6)

Tez: *"LLM ile kod üretmek üç şeyi bol bol verir: çok kod, çalışan demo, güzel
README. Vermediği tek şey ölçüm disiplinidir."* Dokuz ayrışma noktası sayılır
(gold setin bağımsızlığı, istatistiksel iddia, halüsinasyon ölçümü, etiketsiz
veride hata avı, on-prem iddiası, lisans temizliği, adil kıyas, domain
güvenliği, dürüstlük artefaktları).

Raporun kendi karşı-argümanı bölümün en sert paragrafıdır:
*"**Yukarıdaki dokuz ayrışmanın hiçbiri %30'u kurtarmaz.** … Elimizde 3.406
satırlık kusursuz bir ölçüm hattı ve hiç sayı var. … Farklılaşmamız gerçek ama
**koşullu**. Koşul, 4 Ağustos'ta anotasyonun başlamasıdır."*

## files-changed / touched

Bu rapor bir **durum belgesidir**; kod değiştirmez. Raporun referans verdiği
başlıca kod ve doküman yolları (hiçbiri bu ingest'te değiştirilmedi):

Orkestrasyon ve mimari:

- `app/src/pipeline.py` — `:149 run_pipeline()`, `:50-53` dört mod
- `app/src/db/base.py` — `:38 RepositoryProtocol` (13 metot)
- `app/src/db/factory.py` — `:52 create_repository()`
- `app/src/api/main.py` — `:236 build_app()`
- `app/config/banks.yaml` — 10 banka, config olarak
- `app/docker-compose.yml` — varsayılan + `postgres` / `gpu` / `ollama` profilleri

Aşama modülleri (ayrıntısı başka ingest'lerde):

- `app/src/scraping/`, `app/src/preprocessing/clean.py`,
  `app/src/extraction/` (`ner/classifier.py`, `rules/extract.py`,
  `llm/extractor.py`, `reconcile.py`), `app/src/normalization/normalize.py`,
  `app/src/comparison/` (`compare.py`, `contradiction.py`),
  `app/src/chatbot/` (`router.py`, `safety.py`), `app/src/schemas.py`

Ölçüm ve kanıt:

- `app/eval/` (`run_eval.py`, `matchers.py`, `stats.py`, `ablation.py`,
  `iaa.py`, `properties.py`)
- `app/scripts/offline_proof.sh` → `app/docs/OFFLINE-KANIT.md`

Raporun kendi üretim hattı:

- `app/docs/rapor/anatolia-ai-teknik-rapor.md` (bu belgenin proje içindeki kopyası)
- `app/docs/rapor/ekran_goruntuleri.py`, `grafikler.py`, `build_pdf.py`

Raporun **bayat/çelişkili** olarak işaretlediği dosyalar
(→ [[dokuman-tutarsizliklari-bayatlama]]):

- kök `README.md`, `app/README.md`, `CLAUDE.md §15`, `AGENTS.md`
- `app/docs/sartname-kod-eslesme.md` (iç çelişki), `app/docs/veri-katmani.md`
- vault `log.md` (7 günlük boşluk; "Trendyol BLOKE" bayat kaydı)
- `app/.env.example`, `app/data/.../violations-son.jsonl`

## decisions

Bu kaynaktan çıkan ve `decisions/` altına açılan kararlar:

- [[rapor-a-d-juri-e-ic-ek]] — rapor iki kısma bölünür; Bölüm E teslimde çıkarılır
- [[depo-katmani-disinda-sql-yasak]] — depo katmanı dışında ham SQL yazmak yasak,
  `rows()` kaçış kapısı kaldırıldı
- [[rapor-uretilir-elle-yazilmaz]] — rapor betiklerle üretilir, yeni bağımlılık eklenmez
- [[demo-videosu-iki-format-birden]] — şartname içi süre çelişkisine karşı hem
  ≤5 dk hem 1 dk hazırlanır

Raporda teyit edilen, **daha önce kaydedilmiş** kararlar:

- [[ner-fine-tune-yerine-kural-few-shot]] — A2 bu kararın bütçe gerekçesini
  tekrar ediyor: anotasyon bütçesi 150–300 örnek; fine-tune yalnız 8 sınıflı
  kampanya türü sınıflandırıcısına ayrıldı
- [[demo-onceden-doldurulmus-db]] — A2, LLM'in korpus üretiminde devre dışı
  kalmasının ikinci sebebi olarak bu kararı gösteriyor
- [[hibrit-chatbot-text-to-sql-rag]] — A9, chatbot'un saf RAG olmadığını
  `router.py:63 route()` ile kanıtlıyor
- [[apache-2-acik-kaynak-lisansi]] — kapak künyesinde teyit

Raporda **bilinçli olarak alınmayan** karar:

- `rate_nature` sütunu (`taahhut` | `beklenen` | `gerceklesmis` | `bilinmiyor`)
  **uygulanmadı**; uzman görüşü alınmadan şema değiştirilmiyor. Bu yüzden
  güvenlik KAPI 4 muhafazakâr davranıp her yüzdeye uyarı ekliyor.

## issues

Bu kaynaktan çıkan ve `sorun/` altına açılan sorunlar:

- [[dokuman-tutarsizliklari-bayatlama]] — E4'ün 14 kalemi; en görünürü test
  sayısının **altı ayrı yerde altı farklı** yazılması (54 / 129 / 345 / 607 /
  695 / 835; doğrusu **890**)
- [[teslim-zorunlulari-eksik]] — E2'nin 4 açık zorunluluğu (veri seti indirme
  bağlantısı §9, demo videosu §6.2, sunum PDF+PPTX §6.4, veri seti lisansı §8)

Raporun kaydettiği, alan sorumluluğu **başka ajanlarda** olan açık kalemler
(burada yalnız sayılır):

- Gold seti dondurulmadı → %30 için P/R/F1 yok *(kritik)*; IAA/κ hesaplanmadı;
  4 kollu ablasyon koşulmadı → hibridin üstünlüğü **iddia**, ölçüm değil;
  LLM kolu korpusa hiç alan katmadı (2.204/2.204 = kural)
- Altyapı: GPU profilleri ölçülmedi, x86_64/amd64 doğrulanmadı (host arm64),
  model ağırlığı SHA-256 tablosu boş, tam `docker compose up` (postgres+web,
  ağsız) koşturulmadı, pgvector ağsız başlatma denenmedi, `trafilatura` GPL
  riski doğrulanmadı
- Kalite: bge-m3 gerçek gömme ölçülmedi (pgvector ölçümü `HashingEmbedder` ile),
  keyword vs vector ablasyonu yok, chatbot RAG p95 = 325 ms borcu, menü/navigasyon
  metni kaynak span'ine sızıyor, bağlamsız `%0` oranlar "en düşük" sıralamasına
  giriyor, `gliner` bağımlılığı kullanılmıyor, arayüzde markdown render edilmiyor

Mevcut sorun sayfalarıyla ilişki: [[farkli-ifade-bicimleri]] ve
[[standart-veri-formati-eksikligi]] raporun P2/P4 ve normalizasyon bölümünde
ölçülmüş biçimde karşılığını buluyor; [[manuel-karsilastirma-zorlugu]] adil kıyas
garantileriyle (`comparable=False`, `MIN_COVERAGE=0.5`, `MIN_GROUP_SIZE=3`)
karşılanıyor.

## open-threads

- **4 Ağustos kritik yol tarihi geçti mi?** Rapor 3 Ağustos tarihli ve
  anotasyonun 4 Ağustos'ta başlamasını zincirin ön koşulu sayıyor. Bu vault'a
  ingest 9 Ağustos'ta yapılıyor — **anotasyonun fiilen başlayıp başlamadığı ve
  23 günlük planın kayıp kaymadığı doğrulanmalı.**
- **Kök `CLAUDE.md` ≠ `AGENTS.md`** (E4-14): ikisi de 5,8K, farklı içerik;
  hangisinin bağlayıcı olduğu belirsiz. Karar verilmeli.
- **Alan sayısı 12 mi 13 mü** (E4-8): çıkarım şeması 12, şartname tablosu 13
  (kampanya türü ayrı sayılıyor). Rapor bunun çelişki değil "farklı denominatör"
  olduğunu söylüyor ama dokümanlarda açıklanması gerekiyor.
- **Korpus büyüklüğü üç farklı sayı** (E4-11): 291 / 849 / 1.696. Rapor bunların
  farklı dilimler olduğunu (invariants ilk koşu / `demo.db` / raw önbellek)
  söylüyor ama *"hiçbir belge ilişkiyi açıklamıyor"* diye ekliyor. Bu vault'ta da
  hangi sayının hangi bağlamda geçerli olduğu netleştirilmeli.
- **`app/docs/` altındaki 7 doküman vault `index.md`'de yok** (E4-12): lint'in
  gördüğü graf gerçek graf değil; "0 orphan" iddiası eksik veriyle üretiliyor.
- **Kodda bulunan gerçek hataların hiçbiri `sorun/` klasörüne girmemiş**
  (E4-13): 10 hata `log.md` ve `app/docs/` içinde kalmış. Bu ingest bunun bir
  kısmını kapatıyor ama P1–P11'in tamamının `sorun/` karşılığı hâlâ yok.
- **Uzman toplantısı 4 blok × ~10 soru** (E7) hazırlanmış ama toplantı yapılmadı;
  her sorunun "hangi kararı değiştirir" notu var. Toplantı sonrası bu kararların
  vault'a düşmesi gerekir.
- **Jüri simülasyonu 15 soru** (E8) hazır cevaplarıyla yazılmış; sunum
  provasında test edilmedi.

## Sources

- Ham kaynak: `raw/docs/anatolia-ai-teknik-rapor.md` (1.390 satır, ~79 KB;
  rapor tarihi 3 Ağustos 2026)
- Proje içi kopya: `app/docs/rapor/anatolia-ai-teknik-rapor.md`
- Raporun atıf verdiği kanıt dosyaları: `app/docs/OFFLINE-KANIT.md`,
  `app/docs/rapor/` altındaki üretim betikleri, `app/eval/reports/`

## Related

- [[2026-06-16-teknofest-tyda-sartname-2-senaryo]] — bu raporun karşıladığı
  şartnamenin kendisi; madde eşlemesi [[sartname-madde-kod-eslemesi]]
- [[teknik-cozum-mimarisi]] — şartnameden türetilmiş kavramsal hat; bu rapor onun
  **gerçekleşmiş** halini 11 aşama olarak veriyor
- [[teslim-ve-degerlendirme-rehberi]] — teslim ve puanlama çerçevesi; bu raporun
  E1/E2 bölümleri o çerçevenin fiilî durumudur
- [[yarisma-genel-bakis]] — takvim bağlamı (teslim 26 Ağustos 2026)
- [[anatolia-ai-takimi]] — ekip ve anotasyon iş gücü
- [[run-pipeline]] — 11 aşamalı orkestrasyon
- [[rubrik-agirlik-haritasi]] — %30 / %20 / %20 / %20 / %10 kanıt durumu
- [[sessiz-hata]] — raporun ortak örüntüsü ve en güçlü anlatısı
