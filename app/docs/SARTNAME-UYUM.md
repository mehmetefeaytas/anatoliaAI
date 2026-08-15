---
title: "Şartname Uyum Matrisi — TEKNOFEST 2026 TYDA 2. Senaryo"
tags: [sartname, uyum, teslim, degerlendirme, denetim]
date: 2026-08-15
status: taslak
---

# Şartname Uyum Matrisi

TEKNOFEST 2026 **Türkçe Yapay Zekâ Dil Ajanları Yarışması — 2. Senaryo**
(yürütücü: Bilişim Vadisi) şartnamesinin madde-madde uyum matrisi.

Bu belge bir **pazarlama metni değil, bir denetim aracıdır**. Amacı jürinin
"bu takım neyi yapmış, neyi yapmamış" sorusunu tek sayfada, kanıtla
cevaplayabilmesidir. Yapılmayan iş burada saklanmaz — çünkü saklanan tek bir
kalem yakalandığında matrisin geri kalanı da değersizleşir.

> **Şartname metni kaynağı.** Bu matris ham PDF'i değil, vault'taki işlenmiş
> özetleri kullanır: [`sources/teknofest/2026-06-16-teknofest-tyda-sartname-2-senaryo.md`](../../sources/teknofest/2026-06-16-teknofest-tyda-sartname-2-senaryo.md)
> ve [`syntheses/teslim-ve-degerlendirme-rehberi.md`](../../syntheses/teslim-ve-degerlendirme-rehberi.md).
> Bu iki kaynaktan **doğrulanamayan** madde metinleri satır notunda
> *"şartname metni doğrulanmadı"* ile işaretlidir; o satırlarda madde
> numarası/sayfası ikinci elden alınmıştır.

---

## 1. Nasıl okunur

### Durum işaretleri

| İşaret | Anlamı | Kabul koşulu |
|---|---|---|
| ✅ | **Kanıtlı** | Kanıt sütunundaki dosya bu depoda **gerçekten var** (bu belge yazılırken `ls`/`Read` ile açıldı) veya komut bu depodaki **var olan** bir modüle/hedefe işaret ediyor. Kanıtı açılamayan hiçbir satıra ✅ verilmedi. |
| 🟠 | **Kısmi** | İş vardır ama ya kapsamı şartnamenin istediğinden dar, ya ölçümü bayat, ya da kanıtı bu depodan (yerel klondan) doğrulanamıyor. Nedeni Not sütununda **açıkça** yazılıdır. |
| ❌ | **Yok** | Kalem üretilmemiştir. Plan/tasarım belgesi olması kalemi ❌'ten çıkarmaz — jüriye teslim edilen şey plan değil, kalemin kendisidir. |

**Kural:** "planı var" ≠ ✅. "kodu var ama ölçülmedi" ≠ ✅. "iddia README'de
yazıyor ama doğrulanamıyor" ≠ ✅.

### Kanıt komutları nereden koşulur

Kanıt sütunundaki her komutun önünde çalışma dizini yazılıdır:

- **`kök$`** → depo kökü (`anatoliaaI/`). Git, CI tanımı, kök `README.md`,
  kök `LICENSE` ve vault klasörleri (`sources/`, `syntheses/`, `decisions/`)
  buradan görülür.
- **`app$`** → uygulama kökü (`anatoliaaI/app/`). Python modülleri
  (`python -m ...`), `pytest`, `make`, `docker-compose` ve `scripts/`
  **yalnızca buradan** koşar. Depo kökünden koşulursa modül bulunamaz.

Dosya yolları matriste depo köküne göre verilmiştir.

---

## 2. Teslim kalemleri

| # | Kalem | Şartname referansı | Durum | Kanıt (dosya/komut) | Not |
|---:|---|---|:---:|---|---|
| 1 | Açık kaynak kod deposu | §6.1 (s.13–14), §9 (s.18) | ✅ | `kök$ git remote -v` → `github.com/mehmetefeaytas/anatoliaAI.git` | Depo ve uzak adres doğrulandı. **Deponun GitHub'daki "public" görünürlüğü yerel klondan doğrulanamaz**; teslimden önce tarayıcıdan teyit edilmeli. |
| 2 | Açık kaynak lisans (Apache-2.0) | §5.10 (s.11), §8 | ✅ | `LICENSE` (kök) · `app/LICENSE` · `app/NOTICE` · `app/docs/model-license-audit.md` · `app/docs/LISANSLAR.md` · `app$ make lisans-kapisi` | İkisi de yerinde. `NOTICE` model ağırlıklarının `base_model` zincirini köke kadar veriyor; Gemma/Llama lisanslı ağırlıklar bilinçli reddedilmiş. ✅ Lisans kapısı **CI'da koşuyor** (`ci.yml`, `Lisans kapisi` adımı): izin listesi dışı ya da UNKNOWN lisanslı paket çıkarsa build düşer. `docs/sbom.json` (CycloneDX 1.6, 96 paket) commit'li olduğu için bağımlılıksız işte de çalışır. |
| 3 | README — bağımlılık listesi | §6.1, §9 (s.18) | ✅ | `README.md` §"(1) Bağımlılıklar" · `app/requirements.txt` · `app/requirements-api.txt` · `app/web/package.json` · `app/docker-compose.yml` | Dört dosyanın dördü de var. Deterministik çekirdeğin sıfır bağımlılıkla koştuğu iddiası CI'daki *"Ucuncu parti bagimlilik kurulmadigini dogrula"* adımıyla korunuyor. |
| 4 | README — kurulum ve çalıştırma adımları | §6.1, §9 (s.18) | ✅ | `README.md` §"(2) Kurulum ve Çalıştırma Adımları" (A/B/C yolları) · `app/Makefile` · `app/docker-compose.yml` | Üç ayrı yol veriliyor: sıfır bağımlılık, tam Python ortamı, Docker. Python 3.11+ tuzağı ayrıca uyarılmış. |
| 5 | **README — veri seti indirme bağlantısı** | §9 (s.18) | ✅ | `kök$ grep -n 'huggingface' README.md` → link canlı (https://huggingface.co/datasets/mehmetefeaytas/katilim-bankaciligi-kampanya-gold, HTTP 200 doğrulandı) | Şartnamenin adı geçen tek zorunlu artefaktı; 2026-08-15'te yayımlandı. |
| 6 | Veri setinin herkese açık yayını | §9 (s.18) | ✅ | https://huggingface.co/datasets/mehmetefeaytas/katilim-bankaciligi-kampanya-gold · üretici `app$ make veri-seti` (`scripts/veri_seti_paketle.py`) · yükleyici `scripts/veri_seti_yukle.py` | 182 kayıt (gold.round1 134 + gold.v2 48) + sızıntısız train/val/test (127/27/28). Sızıntı denetimi 0 ihlal ve testle çitli. |
| 7 | Veri seti lisansı | §8 | ✅ | Pakette `LISANS.md` — Apache-2.0 + veri kökeni notu; HF deposunda `license: apache-2.0` künyesi | Kaynak sayfaların telif durumu ayrıca yazılı; ham HTML yeniden dağıtılmıyor, yalnız çıkarılmış metin + provenance. |
| 8 | Demo videosu — tam sürüm (**maks. 5 dk**) | §6.2, **s.14** | ✅ | `app/docs/sunum/anatolia-ai-demo.mp4` — **1 dk 55 sn**, 1920×1080, 30 fps, Türkçe seslendirmeli | Tamamı GERÇEK arayüzden: kıyas cetveli, kanıt defteri, hibrit sohbet, çelişki tespiti ve `kanit_tazeligi` kapısının canlı koşumu. Sahte ekran yok. Üretim betikleri `docs/sunum/video-uretim/` — tek komutla yeniden üretilebilir. ⚠️ Seslendirme şu an **geçici yapay ses**; 20 cümle ayrı dosya, insan sesiyle değiştirilebilir. |
| 9 | Demo videosu — kısa sürüm (**1 dk**) | §10, **s.19** | ✅ | `app/docs/sunum/anatolia-ai-demo-1dk.mp4` — **59 sn** | Ayrı çekim yok: uzun videonun dört sahnesinin kesiti (açılış · pano · kıyas cetveli · kanıt defteri · kapanış). |
| — | ⚠️ **Süre çelişkisi (şartname içi, açık)** | s.14 ↔ s.19 | 🟠 | `syntheses/teslim-ve-degerlendirme-rehberi.md` §"ÇELİŞKİ: Demo videosu süresi" | s.14 *"maksimum **5 dakikalık** bir video"*, s.19 *"sunum süresi 4 dakika, demo videosu süresi ise **1 dakika**"*. Metin ikisini açıkça ayırmıyor. **Karar: her ikisi de hazırlanacak**; kesin format yarışma bilgilendirme e-postasıyla teyit edilecek. Çelişki gizlenmiyor, kayıt altında. |
| 10 | Sunum materyali — **PDF** | §6.4 (s.14) | ❌ | Jüri sunumu PDF'i yok. (`app/docs/rapor/anatolia-ai-teknik-rapor.pdf` **teknik rapordur**, sunum değildir.) | Slayt iskeleti hazır: `sunum-ve-demo-plani.md` §C (8 slayt, 4 dk bütçeli). |
| 11 | Sunum materyali — **PPTX** | §6.4 (s.14) | ❌ | `kök$ find . -iname '*.pptx'` → boş | Şartname PDF **ve** PPTX'in ikisini birden istiyor; ikisi de yok. |
| 12 | Proje dokümantasyonu | §6.3 (s.13–14) | ✅ | `app/docs/rapor/anatolia-ai-teknik-rapor.md` (+ `.pdf`) · `app/docs/sartname-kod-eslesme.md` · `app/docs/OFFLINE-KANIT.md` · `app/docs/model-license-audit.md` · `app/docs/veri-katmani.md` | §6.3'ün istediği başlıklar (mimari, NLP yaklaşımı, veri seti, ön işleme, model yapısı, karşılaştırma yöntemi, kurulum, karşılaşılan problemler, örnek çıktılar, performans değerlendirme yöntemi) teknik raporun A–D bölümlerinde karşılanıyor. ⚠️ İçindeki **sayılar teslimden önce yeniden koşulmalı** (bkz. satır 16). |
| 13 | En az haftalık GitHub güncellemesi | §9 (s.18) | ✅ | `kök$ git tag -l 'hafta-*'` → `hafta-00` … `hafta-06` (27 Tem – 15 Ağu, yedi etiket) · `kök$ git log origin/main -1` | Aralıkların hiçbiri 7 günü aşmıyor. `hafta-06` 2026-08-15'te oluşturuldu. |
| 14 | `BilisimVadisi2026` etiketi | §9 (s.18) | ✅ | `kök$ gh repo view --json repositoryTopics` → `bilisimvadisi2026` **var** · `README.md:18` beyan | Depo topic'i 2026-08-15'te doğrulandı (önceki 🟠 'yerel klondan görülemez' gerekçesiyleydi; `gh` ile görülebiliyor). |
| 15 | Türkiye Açık Kaynak Platformu etiketi | §9 (s.18) | ✅ | `kök$ gh repo view --json repositoryTopics` → `turkiye-acik-kaynak-platformu` **var** | Satır 14 ile aynı doğrulama. |
| 16 | **On-premise çalışabilirlik** | §5.9 (s.10–11) | ✅ | `app/docs/OFFLINE-KANIT.md` · `app$ bash scripts/offline_proof.sh` → **14/14 adım beklendiği gibi, 0 beklenmedik** (transkript `docs/offline-proof/transcript-20260815-233225.log`) · `app/docker-compose.yml` · `app/Dockerfile.api` | Kanıt **kaynak ağacı temizken** üretildi — transkript başlığındaki *"1 degisik dosya"* betiğin KENDİ log dosyasıdır (`tee` log'u açtıktan sonra `git status` koşuyor, yani kendi çıktısını sayıyor); mekanizma `OFFLINE-KANIT.md` §0-b'de yazılı. Koşum: `--network none` içinde tüm test paketi + eval + ablasyon + gecikme ölçümü koştu; negatif kontrol (ağ probu engellendi) **ve** onun pozitif kontrolü (ağ açıkken ulaştı); üç imaj `@sha256:` digest pin'li. **KAPSAM SINIRI — sunumda önce biz söyleriz:** kanıt **API konteynerini** kapsıyor; `docker compose up` tam yığını (Postgres, web, vLLM/Ollama) ağsız ayrıca sınanmadı ve **imaj derlemesi internet gerektiriyor** — "internetsiz çalışır" iddiası *önceden derlenmiş imajlarla* doğrudur. |
| 17 | Ücretli API / servis / yazılım yok | §5.10 (s.11), §8 | ✅ | `app/.env.example` (88 satır, **hiçbir API anahtarı alanı yok**) · CI adımı *"Ucuncu parti bagimlilik kurulmadigini dogrula"* (`.github/workflows/ci.yml`) | LLM opsiyonel; `LLM_BACKEND` boşsa sistem kural-only modda çalışır. Kritik yolda ücretli hiçbir bileşen yok. |
| 18 | Fiziksel final — Bilişim Vadisi Kocaeli, canlı sunum + demo | s.18–19 | 🟠 | `syntheses/teslim-ve-degerlendirme-rehberi.md` §"Süreç teslim kuralları" | Şartname metni doğrulandı (son 24 saat fiziksel, canlı sunum + demo). Hazırlık tarafında **sunum ve video kalemleri (8–11) eksik** olduğu için finale hazır sayılamaz. Kesin tarihler şartnamede boş bırakılmış (s.18, "… 2026"); TEKNOFEST/KYS duyurusundan teyit edilmeli. |

**Sayım:** 18 teslim kalemi + 1 çelişki satırı → **✅ 7 · 🟠 6 · ❌ 6**

---

## 3. Değerlendirme kriterleri (§7, s.15 — toplam %100)

| Kriter | Ağırlık | Durum | Bizim kanıtımız (dosya/komut) | Not |
|---|---:|:---:|---|---|
| **Model Başarısı ve Anlamlandırma Yeteneği** | **%30** | 🟠 | `app$ python -m eval.run_eval --gold data/gold/gold.v2.json` (`app/eval/run_eval.py`) · `app/data/gold/gold.v2.json` (48 kayıt, 40'ı zor vaka) · `app$ python -m eval.calibration --gold data/gold/gold.v2.json` · `app$ python -m scripts.report_iaa data/gold/review/round0_kalibrasyon_{A,B,C,D}.csv` | Sayı **var** ve yayımlanıyor: yapılandırılmış alan mikro-F1 **0,646**, 12-alan mikro-F1 **0,452** [%95 GA 0,384–0,512], halüsinasyon **0,059**. İki sayı da veriliyor, farkı README'de açıklanıyor. **Neden ✅ değil:** ① gold **dondurulmadı** — round1 turu sahada, `gold.round1.json` çalışma ağacında değişik; ② anotatör uyumu **eşiğin altında** (Cohen κ 0,274 / Fleiss κ 0,302; anotasyon öncesi ilan edilen eşik 0,67) — eşik değiştirilmedi, ilan edilen sonuç uygulandı; ③ **insan hakemliği yok** — round1'in 53 vakalık kör hakemliği **alt ajanlara** yaptırıldı (`app/docs/rapor/oturum-2026-08-15-round1-onarimi.md` §2). `app/docs/anotasyon-hatti-plani.md` bunun sonucunu açıkça yazıyor: makine referansı **"gold" değil `silver-extended`**'dir; makine üretimi referansa karşı ölçülen P/R/F1 "model insanla ne kadar örtüşüyor"u değil, "bir model başka bir modelle ne kadar örtüşüyor"u ölçer ve **halüsinasyon oranı çapasız kalır**. Rubriğin en ağır kalemi budur; kapatılması gereken en büyük açık burasıdır. |
| **Fonksiyonellik ve Senaryo Kapsamı** | %20 | 🟠 | `app/src/comparison/compare.py` · `app/src/chatbot/` (router + text-to-SQL + RAG) · `app/web/` (Next.js dashboard) · `app$ python -m eval.rag_eval --db data/demo.db` · `app$ python -m src.chatbot.run_safety_eval --db data/demo.db` | Uçtan uca çalışıyor: 12 çıkarım alanı (+ kampanya türü), 8/8 kampanya türü üretilebiliyor, §5.7'nin **5/5 karşılaştırma ölçütü** kodda karşılanıyor (`rank()` + `rank_advantageous_by_type()`), dashboard + hibrit chatbot ayakta. RAG terim kapsama R@5 **0,867**, reddetme kararı **30/30**, güvenlik seti **29/30**. **Neden ✅ değil:** ① kâr payı oranı skorlanabilir kampanyaların yalnız **%9,5**'inde var — kıyas motoru çalışıyor ama kapsamı dar ve bu gizlenmiyor; ② sınıflanamayan 60 belge (%7,1); ③ `app/docs/sartname-kod-eslesme.md` **kendi içinde çelişiyor**: §5.7 tablosu 5. ölçütü ✅ derken rubrik bölümü "5. ölçüt eksik" diyor — bu iç çelişki teslimden önce tek yönde kapatılmalı. |
| **Teknik İmplementasyon ve Mimari** | %20 | ✅ | `app$ python -m scripts.test_ozeti` (**2.999** toplanan · 2.946 geçen · 53 atlanan · 0 hata) · `.github/workflows/ci.yml` (5 iş: bağımlılıksız testler, bağımlılıklı testler, Postgres/pgvector paritesi, ruff, frontend) · CI adımları: değişmez denetimi · eval regresyon kapısı (gold.v2) · eval regresyon kapısı (round1, ayrı taban) · gold kanıt zinciri · markdown link denetimi · **kanıt-tazeliği kapısı** · **lisans kapısı** · demo DB tazeliği | Katmanlar bağımsız test edilebilir (`src/scraping` · `preprocessing` · `extraction` · `normalization` · `comparison` · `rag` · `chatbot` · `api` · `db`). Her çıkarılan alan `span_start`/`span_end` taşıyor ve `verify_span()` ile `text[start:end] == raw_value` kendi kendini denetliyor. CI'da eval regresyon kapısı (alan F1 tabanı + halüsinasyon tavanı) var — ölçüm gerilerse build kırılır. ⚠️ Bilinen boşluk: pgvector kurulu ama üretim yolunda kullanılmıyor. CI adımları 15 Ağustos'ta ikiye çıktı: **kanıt-tazeliği kapısı** (yayımlanan sayı ile onu üreten kanıt ayrışırsa build düşer) ve **lisans kapısı**. |
| **On-Prem Uygulanabilirlik** | %20 | ✅ | `app/docs/OFFLINE-KANIT.md` · `app$ bash scripts/offline_proof.sh` · `app/docs/kaynak-tuketimi.md` · `app/docker-compose.yml` | Ölçülmüş: kural-only p50 **1,03 ms**, verim 21.087 belge/dk, tepe RSS 100,4 MB, imaj 96,5 MiB; api+postgres ≈255 MB'a karşı tam GPU yığını ≈10,6 GB (**40× fark** — "önce kural" mimarisinin paket boyutundaki karşılığı). Digest pin'li imajlar tekrar-üretilebilirlik veriyor. **Neden ✅ değil:** teslim kalemi 16'daki üç kapsam sınırı (bayat koşum · yalnız API konteyneri · imaj derlemesi internet istiyor). *Rakiplerin bu kalemde kredi kaybettiği yer tam olarak burasıdır: ölçülmemiş bir on-prem iddiası, jüri kapsamı sorduğunda tüm matrisi düşürür. Biz sınırı önce kendimiz yazıyoruz.* |
| **Yenilikçilik ve Yaratıcılık** | %10 | ✅ | ① `app/src/comparison/contradiction.py` (37 KB) + `app$ python -m scripts.crosscheck_fees` — bankalar arası **çelişki tespiti** ("masrafsız" diyen kampanya + tahsis ücreti kaydı) · ② alan bazlı **güven skoru + kaynak span vurgulama** (`app/src/schemas.py` → `ExtractedField`, `verify_span()`, `tests/test_confidence_span.py`) · ③ **config-driven banka onboarding** (`app/config/banks.yaml`, 32 KB — yeni banka tek blok) | `decisions/daraltilmis-yenilikcilik-hedefleri.md`'deki üç hedefin üçü de kodda var, testle korunuyor ve demoda gösterilebilir. Dördüncü bir farklılaştırıcı: **ölçümle yanlışlanan hipotezi düzeltmemek** — ablasyon hibridi yanlışladı (0,575 < 0,612, p=0,0117; halüsinasyon 0,163 vs 0,102) ve sonuç düzeltilmeden yayımlandı. |

**Ağırlıklı okuma (2026-08-15):** kanıtlı ✅ olan üç kriter toplam **%50** —
Teknik İmplementasyon %20 + On-Prem %20 + Yenilikçilik %10. On-Prem bugün
🟠'dan ✅'e geçti: kanıt temiz ağaçta yeniden koşuldu ve **14/14 adım**
beklendiği gibi çıktı.

Kalan %50'nin ikisi 🟠: **Model Başarısı (%30)** ve **Fonksiyonellik (%20)**.
Model Başarısı'nın 🟠 kalmasının sebebi ölçüm yokluğu değil — sayılar var,
yayımlanıyor ve CI kapısıyla korunuyor. Sebep, **referansın makine
anotasyonlu** olmasıdır: gold hem çıkarımı ölçen hem de aynı ailenin ürettiği
bir referanstır, dolayısıyla halüsinasyon oranı bağımsız bir çapaya
oturmuyor. Bunu ✅ saymak, ölçtüğümüz şeyi ölçmediğimizi söylemek olurdu.

---

## 4. Açık kalemler ve ne gerekiyor

Her satır tek bir aksiyondur. Sıra kritiklik sırasıdır.

### ❌ — üretilmemiş kalemler

| # | Kalem | Aksiyon |
|---:|---|---|
| ~~1~~ | ~~Veri seti indirme bağlantısı~~ | ✅ **KAPANDI (15 Ağu)** — link README'de ve canlı. |
| ~~2~~ | ~~Veri seti yayını~~ | ✅ **KAPANDI (15 Ağu)** — Hugging Face'te herkese açık. |
| ~~3~~ | ~~Veri seti lisansı~~ | ✅ **KAPANDI (15 Ağu)** — pakette `LISANS.md`, HF künyesinde `license: apache-2.0`. |
| ~~4~~ | ~~Demo videosu ≤5 dk~~ | ✅ **KAPANDI (16 Ağu)** — 1:55, gerçek arayüzden. |
| ~~5~~ | ~~Demo videosu 1 dk~~ | ✅ **KAPANDI (16 Ağu)** — 59 sn kesit. |
| 6 | Sunum PDF (§6.4) | `sunum-ve-demo-plani.md` §C'deki 8 slaytı tasarla, PDF olarak dışa aktar. |
| 7 | Sunum PPTX (§6.4) | Aynı slaytları PPTX olarak da dışa aktar — şartname ikisini birden istiyor. |

### 🟠 — kısmi kalemler

| # | Kalem | Aksiyon |
|---:|---|---|
| 8 | **Model Başarısı %30 — insan çapası** | Kalibrasyon A/B/C/D kümesini (20 belge × 13 alan) **insan** anotatörle tamamla; raporda iki sayıyı ayrı ver: `κ(insan, insan)` ve `uyum(LLM, insan)`. Makine üretimi kümeyi `gold` değil **`silver-extended`** olarak adlandır (`app/docs/anotasyon-hatti-plani.md`). |
| 9 | Model Başarısı %30 — gold dondurma | Round1 bitince `gold.round1.json`'ı SHA-256 ile dondur, `eval/esikler.json`'u güncelle ve P/R/F1'i **dondurulmuş** set üzerinde yeniden yayımla. |
| 10 | On-Prem %20 — kanıt tazeliği | `app$ bash scripts/offline_proof.sh`'i **temiz çalışma ağacında** yeniden koş; `OFFLINE-KANIT.md`'deki 31 Temmuz sayılarını güncelle. |
| 11 | On-Prem %20 — kapsam genişletme | `docker compose up` **tam yığınını** (Postgres + web + API) ağsız koş; şu anki kanıt yalnız API konteynerini kapsıyor. Kapatılamazsa sınırı sunum slaytına **kendimiz** yaz. |
| 12 | Haftalık güncelleme (§9) | `hafta-06` etiketini bugün at ve push'la — son etiket (`hafta-05`) 8 Ağustos, üzerinden 7 gün geçti. |
| 13 | `BilisimVadisi2026` + Türkiye Açık Kaynak Platformu topic'leri | GitHub depo ayarlarından topic'leri **tarayıcıdan** teyit et; README beyanı tek başına kanıt değil. Aynı ekranda depo görünürlüğünün **public** olduğunu doğrula. |
| 14 | Fonksiyonellik %20 — iç çelişki | `app/docs/sartname-kod-eslesme.md`'de §5.7 tablosu ("5/5 ✅") ile rubrik bölümü ("5. ölçüt eksik") çelişiyor; kodu okuyup tek yönde düzelt. |
| 15 | Proje dokümantasyonu tazeliği | Teknik rapordaki tüm ölçüm sayılarını teslimden önce yeniden koş; `.pdf`'i yeniden üret. |
| ~~16~~ | ~~Lisans kapısı otomasyonu~~ | ✅ **KAPANDI (15 Ağu):** `ci.yml`'de `Lisans kapisi` adımı olarak koşuyor. |
| 17 | Fiziksel final hazırlığı (s.18–19) | Kesin tarihleri TEKNOFEST/KYS duyurusundan teyit et (şartnamede s.18 boş bırakılmış); demo videosu süresini bilgilendirme e-postasıyla netleştir. |

---

## Sources

- [[2026-06-16-teknofest-tyda-sartname-2-senaryo]] — Temel Beklentiler
  (§5.1–5.10), Tespit Edilmesi Gerekenler (s.13–14), Değerlendirme Kriterleri
  (s.15), Süreç ve Sunumlar (s.17–19)
- [[teslim-ve-degerlendirme-rehberi]] — teslim listesi, rubrik ağırlıkları,
  süreç kuralları (s.18), demo süresi çelişkisi (s.14 ↔ s.19)
- [`app/docs/sartname-kod-eslesme.md`](sartname-kod-eslesme.md) — madde ↔ kod eşlemesi
- [`app/docs/OFFLINE-KANIT.md`](OFFLINE-KANIT.md) — on-prem kanıt paketi ve kapsam sınırları
- [`app/docs/model-license-audit.md`](model-license-audit.md) — lisans zinciri denetimi
- [`app/docs/anotasyon-hatti-plani.md`](anotasyon-hatti-plani.md) — insan çapası gerekçesi
- [`app/docs/rapor/oturum-2026-08-15-round1-onarimi.md`](rapor/oturum-2026-08-15-round1-onarimi.md) — kör hakemliğin alt ajanlarla yapıldığı kayıt
- [`app/docs/rapor/sunum-ve-demo-plani.md`](rapor/sunum-ve-demo-plani.md) — video çekim listesi ve slayt iskeleti
- [`app/docs/rapor/anatolia-ai-teknik-rapor.md`](rapor/anatolia-ai-teknik-rapor.md) — §E2 teslim eksikleri

## Related

- [[teknik-cozum-mimarisi]] — matristeki teknik kalemlerin mimari temeli
- [[yarisma-genel-bakis]] — yarışma bağlamı ve takvim
- [[on-premise-calistirilabilir-mimari]] — §5.9 kararının kendisi
- [[apache-2-acik-kaynak-lisansi]] — §5.10 lisans kararı
