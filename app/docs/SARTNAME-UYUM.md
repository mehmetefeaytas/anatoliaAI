---
title: "Şartname Uyum Matrisi — TEKNOFEST 2026 TYDA 2. Senaryo"
tags: [sartname, uyum, teslim, degerlendirme, denetim]
date: 2026-08-21
status: stable
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
| 2 | Açık kaynak lisans (Apache-2.0) | §5.10 (s.11), §8 | ✅ | `LICENSE` (kök) · `app/LICENSE` · `app/NOTICE` · `app/docs/model-license-audit.md` · `app/docs/LISANSLAR.md` · `app$ make lisans-kapisi` | İkisi de yerinde. `NOTICE` model ağırlıklarının `base_model` zincirini köke kadar veriyor; Gemma/Llama lisanslı ağırlıklar bilinçli reddedilmiş. ✅ Lisans kapısı **CI'da koşuyor** (`ci.yml`, `Lisans kapisi` adımı): izin listesi dışı ya da UNKNOWN lisanslı paket çıkarsa build düşer. `docs/sbom.json` (CycloneDX 1.6, **96 bileşen** — kurulu `.venv`'in tamamı, `pip`/`setuptools` ve envanter aracının kendi zinciri dâhil) commit'li olduğu için bağımlılıksız işte de çalışır. ⚠️ `docs/LISANSLAR.md`'deki **91 paket** bununla aynı şey DEĞİLDİR: `pip-licenses` kendisini + bağımlılıklarını + `pip`/`setuptools`'u dışlar, fark tam olarak beş pakettir (`pip`, `pip-licenses`, `prettytable`, `setuptools`, `wcwidth`). Kapı 96'lık dosyayı okur. ✅ **SBOM sapması ÇÖZÜLDÜ (16 Ağu).** Gün içinde `.venv` 105 pakete çıkmıştı (demo seslendirmesinden kalan `edge-tts` + 7 geçişli bağımlılığı + `tabulate`) ve ölçüldü ki SBOM o hâliyle tazelenirse kapı **düşüyordu** — `edge-tts` **LGPL-3.0-only** (YASAK kova), `multidict` lisansı boş. Dokuz paket kaldırıldı, `make sbom` yeniden koşuldu. Doğrulama: sapma **0** (96 = 96, her iki yönde), `make lisans-kapisi` **GEÇTİ ✅**, tam test paketi kaldırma sonrası o günün ağacında **3.118 geçti · 0 başarısız** (güncel paket: 3.552) — yani gerçekten çalışma zamanı bağımlılığı değillerdi. Ayrıntı: `app/README.md` §"ÇÖZÜLDÜ — SBOM sapması kapandı". |
| 3 | README — bağımlılık listesi | §6.1, §9 (s.18) | ✅ | `README.md` §"(1) Bağımlılıklar" · `app/requirements.txt` · `app/requirements-api.txt` · `app/web/package.json` · `app/docker-compose.yml` | Dört dosyanın dördü de var. Deterministik çekirdeğin sıfır bağımlılıkla koştuğu iddiası CI'daki *"Ucuncu parti bagimlilik kurulmadigini dogrula"* adımıyla korunuyor. |
| 4 | README — kurulum ve çalıştırma adımları | §6.1, §9 (s.18) | ✅ | `README.md` §"(2) Kurulum ve Çalıştırma Adımları" (A/B/C yolları) · `app/Makefile` · `app/docker-compose.yml` | Üç ayrı yol veriliyor: sıfır bağımlılık, tam Python ortamı, Docker. Python 3.11+ tuzağı ayrıca uyarılmış. |
| 5 | **README — veri seti indirme bağlantısı** | §9 (s.18) | ✅ | `kök$ grep -n 'huggingface' README.md` → link canlı (https://huggingface.co/datasets/mehmetefeaytas/katilim-bankaciligi-kampanya-gold, HTTP 200 doğrulandı) | Şartnamenin adı geçen tek zorunlu artefaktı; 2026-08-15'te yayımlandı. |
| 6 | Veri setinin herkese açık yayını | §9 (s.18) | ✅ | https://huggingface.co/datasets/mehmetefeaytas/katilim-bankaciligi-kampanya-gold · üretici `app$ make veri-seti` (`scripts/veri_seti_paketle.py`) · yükleyici `scripts/veri_seti_yukle.py` | 182 kayıt (gold.round1 134 + gold.v2 48) + sızıntısız train/val/test (127/27/28). Sızıntı denetimi 0 ihlal ve testle çitli. |
| 7 | Veri seti lisansı | §8 | ✅ | Pakette `LISANS.md` — Apache-2.0 + veri kökeni notu; HF deposunda `license: apache-2.0` künyesi | Kaynak sayfaların telif durumu ayrıca yazılı; ham HTML yeniden dağıtılmıyor, yalnız çıkarılmış metin + provenance. |
| 8 | Demo videosu — tam sürüm (**maks. 5 dk**) | §6.2, **s.14** | ✅ | **Birincil:** `app/docs/sunum/anatolia-ai-demo-kapsamli.mp4` — **3 dk 04 sn**, 1920×1080, 30 fps, Türkçe seslendirmeli | **Tek kare kart/mockup yok**: 12 ekranın tamamı gerçek arayüzden, gerçek veriyle, gerçek yükleme süreleriyle çekildi (pano · kıyas cetveli · ısı haritası · en avantajlı · banka sayfası · banka içi delta · çelişki tespiti · jüri denetim paneli · canlı çıkarım · hibrit sohbet · veri tazeleme · işlem günlüğü). Üretim betikleri `docs/sunum/video-uretim/` — tek komutla yeniden üretilebilir. **Alternatif:** `anatolia-ai-demo.mp4` (1:55) — aynı arayüz görüntüleri ama **dört başlık kartı içerir** (açılış · problem · mimari · kapanış), yani "tamamı gerçek arayüz" iddiası yalnız kapsamlı sürüm için geçerlidir. ⚠️ Her iki sürümde de seslendirme **geçici yapay ses**; cümleler ayrı dosya, insan sesiyle değiştirilebilir. |
| 9 | Demo videosu — kısa sürüm (**1 dk**) | §10, **s.19** | ✅ | **Birincil:** `app/docs/sunum/anatolia-ai-demo-1dk-sekiz-ekran.mp4` — **59 sn**, kartsız | Sekiz ekran, on üç cümle. **Korpusun dolu kesiti seçildi** (`sqlite3 data/demo.db` ölçümü): banka sayfasında varsayılan Adil Katılım yerine **Kuveyt Türk** (537 belge · 12/12 alan · 1.703 değer — en dolu banka), cetvelde seyrek `kar_payi_orani` (70 belge) yerine **masraf durumu** (498 belge · 9/10 banka), en avantajlıda en çok satırı sıralanabilen tür olan **Yatırım Ürünü** (14 sıralanabilir · arayüzden tür tür sayıldı). Görüntü ×1,4 hızlandırılmış (`setpts`) — kare atlanmıyor, aynı saniyede %40 daha çok ekran. Eski satır (aşağıdaki sekiz ekran listesi) korunuyor: Karşılaştırma · En Avantajlı · Banka Sayfası · Çelişki Tespiti · Chatbot · Veri Tazeleme · Jüri Audit Paneli · **Ayarlar**. Kapanış, `/admin/banks`, `/admin/banks/{slug}/campaigns` ve `/admin/banks/{slug}/products` uçlarının **şemasını** gösteriyor: tanımlı, sunucudan okunuyor, bugün **501** dönüyor — bankalarla iş birliği kurulup API verildiğinde açılacak. Ekranın kendisi bunu "çalışan bir form değil, sözleşme belgesi" diye yazdığı için video da öyle anlatıyor. **Önceki kesitler:** `anatolia-ai-demo-kapsamli-1dk.mp4` (55 sn, dört sahne) ve `anatolia-ai-demo-1dk.mp4` (59 sn, kartlı sürümün kesiti) — ikisi de yerinde, ama teslimde bu satırın birincili yukarıdaki dosyadır. |
| — | ℹ️ **Süre "çelişkisi" — ÇÖZÜLDÜ (2026-08-16), çelişki değilmiş** | §6 ↔ §10 | ✅ | Şartname PDF'i baştan sona okundu: `raw/teknofest/2026-teknofest-tyda-sartname-2-senaryo.pdf` **dosya sayfası 15** (§6 "Tespit Edilmesi Gerekenler") ve **dosya sayfası 20** (§10 "Yarışma Sunumları") | Bu satır uzun süre 🟠 açık çelişki olarak duruyordu ("metin ikisini açıkça ayırmıyor"). **Ayırıyor.** İki AYRI kalem: ① §6 → **teslim** artefaktı: *"Demo Videosu: Geliştirilen sistemin, metinlerden bilgileri nasıl çıkardığını ve farklı bankalara ait ürünleri nasıl karşılaştırdığını gösteren **maksimum 5 dakikalık** bir video hazırlanmalıdır."* ② §10 → **sunum günü** kalemi: *"Sunum esnasında, geliştirilen proje ile ilgili bir demo gösterimi yapılması zorunludur. Bu kapsamda, sunum sırasında herhangi bir aksaklık yaşanmaması adına, **projeye ek olarak** bir proje demo videosunun da hazırlanması gerekmektedir. Sunum süresi 4 dakika, demo videosu süresi ise **1 dakika** olacaktır."* Belirleyici ifade **"projeye ek olarak"**: §10'un 1 dakikalık videosu §6'nın ≤5 dakikalık videosunun *yerine geçmiyor*, ona EK. Yani iki gereklilik var ve **ikisi de karşılanmış** (satır 8 → 3:04 ≤ 5 dk ✓ · satır 9 → 59 sn ≈ 1 dk ✓). Ekibin "her ikisi de hazırlanacak" kararı doğruymuş. **Satır silinmedi**, çözüldü olarak kaydedildi (HARD RULE "çelişki gizlenmez" çözülmüş çelişkiyi kaydetmeyi yasaklamaz). ⚠️ Aynı çelişki `syntheses/teslim-ve-degerlendirme-rehberi.md` §"ÇELİŞKİ: Demo videosu süresi" içinde de kayıtlı ve **orası hâlâ tazelenmedi** — bu dosyanın sahibi değiliz. |
| 10 | Sunum materyali — **PDF** | §6.4 (s.14) | ✅ | `app/docs/sunum/anatolia-ai-sunum.pdf` — **748 KB · 5 sayfa · 1440×810 pt** (oran 1,7778 = tam 16:9). Üretim: `app$ .venv/bin/python docs/sunum/uret-sunum.py` (~5 sn, çevrimdışı; `--sadece pdf\|pptx`) | **Bağımsız doğrulandı (2026-08-21):** `pypdf` ile **5 sayfa**; metin katmanı **vektör/seçilebilir** (4.387 karakter çıkarıldı, taranmış görüntü değil); Türkçe diyakritikler metin katmanından sayıldı — `ş 20 · ç 31 · ı 159 · ğ 21 · ü 32 · ö 9 · **â 2**` (â'nın varlığı «k**â**r payı»nın doğru dizildiğini gösterir, mojibake yok). **Sayfa sayısı 15'ten 5'e indi (21 Ağu):** sahnede konuşulacak süre 4 dakika ve 15 slayt o sürede sunulamıyordu. 15 slaytlık sürüm silinmedi — `docs/archive/sunum-15-slayt-2026-08-21.html`. Beş slaytın hepsi 1920×1080'e **kendi başına** sığıyor (üreticinin taşma raporu boş), yani hiçbir slayt küçültülerek sığdırılmadı. |
| 11 | Sunum materyali — **PPTX** | §6.4 (s.14) | ✅ | `app/docs/sunum/anatolia-ai-sunum.pptx` — **914 KB · 5 slayt · 20″×11,25″** (her slaytta tam-sayfa 1920×1080 PNG). Aynı üreteç: `docs/sunum/uret-sunum.py` | **Bağımsız doğrulandı (2026-08-21):** `ppt/slides/slideN.xml` sayımı **5**; `zipfile.testzip()` **hatasız**. Üretimde kullanılan `python-pptx` (**MIT**) proje `.venv`'ine **KURULMADI** — ayrı yardımcı ortamda (`~/.cache/anatolia-ai/sunum-venv`) koşuldu, böylece SBOM kirlenmedi. Slayt sayısı gerekçesi satır 10'da. |
| 12 | Proje dokümantasyonu | §6.3 (s.13–14) | ✅ | `app/docs/rapor/anatolia-ai-teknik-rapor.md` (+ `.pdf` — ⚠️ bu PDF `.gitignore`'daki `*.pdf` yüzünden **izlenmiyordu**, yani buradaki atıf bir süre **yanlıştı**; istisna 2026-08-16'da eklendi, dosya artık yok sayılmıyor ama **hâlâ commit edilmemiş** — `git status` → `??`) · `app/docs/sartname-kod-eslesme.md` · `app/docs/OFFLINE-KANIT.md` · `app/docs/model-license-audit.md` · `app/docs/veri-katmani.md` | §6.3'ün istediği başlıklar (mimari, NLP yaklaşımı, veri seti, ön işleme, model yapısı, karşılaştırma yöntemi, kurulum, karşılaşılan problemler, örnek çıktılar, performans değerlendirme yöntemi) teknik raporun A–D bölümlerinde karşılanıyor. ⚠️ İçindeki **sayılar teslimden önce yeniden koşulmalı** (bkz. satır 16). |
| 13 | En az haftalık GitHub güncellemesi | §9 (s.18) | ✅ | `kök$ git tag -l 'hafta-*'` → `hafta-00` … `hafta-06` (27 Tem – 15 Ağu, yedi etiket) · `kök$ git log origin/main -1` | Aralıkların hiçbiri 7 günü aşmıyor. `hafta-06` 2026-08-15'te oluşturuldu. |
| 14 | `BilisimVadisi2026` etiketi | §9 (s.18) | ✅ | `kök$ gh repo view --json repositoryTopics` → `bilisimvadisi2026` **var** · `README.md:18` beyan | Depo topic'i 2026-08-15'te doğrulandı (önceki 🟠 'yerel klondan görülemez' gerekçesiyleydi; `gh` ile görülebiliyor). |
| 15 | Türkiye Açık Kaynak Platformu etiketi | §9 (s.18) | ✅ | `kök$ gh repo view --json repositoryTopics` → `turkiye-acik-kaynak-platformu` **var** | Satır 14 ile aynı doğrulama. |
| 16 | **On-premise çalışabilirlik** | §5.9 (s.10–11) | ✅ | `app/docs/OFFLINE-KANIT.md` · `app$ bash scripts/offline_proof.sh` → **14/14 adım beklendiği gibi, 0 beklenmedik** (transkript `docs/offline-proof/transcript-20260815-233225.log`) · `app/docker-compose.yml` · `app/Dockerfile.api` | Kanıt **kaynak ağacı temizken** üretildi — transkript başlığındaki *"1 degisik dosya"* betiğin KENDİ log dosyasıdır (`tee` log'u açtıktan sonra `git status` koşuyor, yani kendi çıktısını sayıyor); mekanizma `OFFLINE-KANIT.md` §0-b'de yazılı. Koşum: `--network none` içinde tüm test paketi + eval + ablasyon + gecikme ölçümü koştu; negatif kontrol (ağ probu engellendi) **ve** onun pozitif kontrolü (ağ açıkken ulaştı); üç imaj `@sha256:` digest pin'li. **KAPSAM SINIRI — sunumda önce biz söyleriz:** kanıt **API konteynerini** kapsıyor; `docker compose up` tam yığını (Postgres, web, vLLM/Ollama) ağsız ayrıca sınanmadı ve **imaj derlemesi internet gerektiriyor** — "internetsiz çalışır" iddiası *önceden derlenmiş imajlarla* doğrudur. |
| 17 | Ücretli API / servis / yazılım yok | §5.10 (s.11), §8 | ✅ | `app/.env.example` (146 satır, **hiçbir ÜCRETLİ dış servis anahtarı alanı yok** — OpenAI/Anthropic/Google/Cohere hiçbiri geçmiyor). **24 Ağustos'ta eklenen `EVREN_API_KEY` alanı bunun istisnası değil ve bilerek BOŞ bırakılmıştır:** SSB EVREN, TEKNOFEST'in tüm takımlara **ücretsiz** açtığı kendi çıkarım altyapısıdır (8×H200, kota yok); dışarıya para ödenen bir servis değildir. Anahtar repoya girmez, kabukta ya da `.env.local`'de durur; **yokluğunda `evren` kademesi sessizce atlanır ve sistem yerel yolla tam çalışır** (`src/extraction/llm/cascade.py`, kanıt: `docs/evren-servisi.md` §4). 21 Ağustos'ta eklenen `API_KEYS` de bunun **istisnası değil**: o, bizim API'mize GELEN isteği doğrulayan yerel bir paylaşılan sırdır (on-prem kimlik doğrulama, `docs/kimlik-dogrulama.md`), dışarıya para ödenen bir servis anahtarı değil. Ayrım önemli çünkü ikisi de "API anahtarı" adını taşıyor: biri dışarıya çıkar, öteki içeriye girişi kapatır · CI adımı *"Ucuncu parti bagimlilik kurulmadigini dogrula"* (`.github/workflows/ci.yml`) | LLM opsiyonel; `LLM_BACKEND` boşsa sistem kural-only modda çalışır. Kritik yolda ücretli hiçbir bileşen yok. |
| 18 | Fiziksel final — Bilişim Vadisi Kocaeli, canlı sunum + demo | s.18–19 | 🟠 | `syntheses/teslim-ve-degerlendirme-rehberi.md` §"Süreç teslim kuralları" | Şartname metni doğrulandı (son 24 saat fiziksel, canlı sunum + demo). **Gerekçe 2026-08-16'da güncellendi:** eski hâli *"sunum ve video kalemleri (8–11) eksik olduğu için finale hazır sayılamaz"* diyordu — **bu gerekçe artık geçersiz**, 8/9/10/11'in dördü de ✅. 🟠 kalmasının kalan **tek** sebebi kendi kontrolümüz dışında: **kesin tarihler şartnamede boş bırakılmış** (s.18, "… 2026") ve TEKNOFEST/KYS duyurusundan teyit edilmesi gerekiyor. Artefakt tarafında eksik yok; ⚠️ tek iç iş, üretilen sunum/video/rapor dosyalarının **commit edilmesi** (hepsi şu an `??`). |

**Sayım (yeniden sayıldı 2026-08-16, sunum kalemleri kapandıktan SONRA):**
18 teslim kalemi + 1 çözülmüş-çelişki satırı = **19 satır** →
**✅ 18 · 🟠 1 · ❌ 0**

- ✅ 18 → satır 1–17 (on yedi kalem) **+** çözülmüş süre satırı
- 🟠 1 → satır 18 (fiziksel final — **yalnızca** şartnamede tarih boş olduğu için)
- ❌ 0 → **eksik zorunlu teslim kalemi kalmadı**

> **Sayım aynı gün İKİ KEZ değişti; ikisi de kaydedildi:**
>
> | an | dağılım | ne oldu |
> |---|---|---|
> | önceki yayımlanan hâl | `✅ 7 · 🟠 6 · ❌ 6` | **yanlıştı** — toplam (19) doğru, dağılım tablonun eski bir hâlinden kalmıştı |
> | 16 Ağu, sunumdan önce | `✅ 16 · 🟠 1 · ❌ 2` | yeniden sayıldı; 10–11 (sunum PDF/PPTX) hâlâ eksikti |
> | **16 Ağu, sunumdan sonra** | **`✅ 18 · 🟠 1 · ❌ 0`** | 10 ve 11 üretildi ve doğrulandı |
>
> İlk hata projenin **aleyhine** işliyordu (kendimizi olduğumuzdan hazırlıksız
> gösteriyorduk); yine de yanlıştı ve kanıt kapısının kör noktasına tipik bir
> örnektir. **Aritmetiğe güvenilmedi** — her üç sayım da aşağıdaki betikle
> satır satır yapıldı.
>
> ```bash
> python3 -c "
> import collections
> ls=open('docs/SARTNAME-UYUM.md').read().split(chr(10))
> i=next(k for k,l in enumerate(ls) if l.startswith('| # | Kalem |'))+2
> c=collections.Counter()
> while ls[i].startswith('|'):
>     c[[x.strip() for x in ls[i].split('|')][4]]+=1; i+=1
> print(sum(c.values()), dict(c))"
> # 2026-08-16 (sunum sonrası) -> 19 {'✅': 18, '🟠': 1}
> ```

> ⚠️ **«✅» ürettik demektir, «commit ettik» demek DEĞİLDİR.** Satır 8–12'nin
> dayandığı dosyaların tamamı (`anatolia-ai-sunum.pdf/.pptx`, dört demo `.mp4`,
> `anatolia-ai-teknik-rapor.pdf`, `uret-sunum.py`, `video-uretim/`) şu an
> `git status` çıktısında **`??` — izlenmiyor**. Şartname §9 artefaktların
> **GitHub'a yüklenmesini** şart koşuyor; commit edilmeden bu satırlar jüri
> için var sayılmaz. Kök `.gitignore:5`'teki `*.pdf` deseni 2026-08-16'da
> istisnalarla aşıldı, yani **engel kalktı** — kalan iş yalnızca `git add`.
> Doğrulama: `git status --short -- app/docs/sunum/ app/docs/rapor/*.pdf`

---

## 3. Değerlendirme kriterleri (§7, s.15 — toplam %100)

| Kriter | Ağırlık | Durum | Bizim kanıtımız (dosya/komut) | Not |
|---|---:|:---:|---|---|
| **Model Başarısı ve Anlamlandırma Yeteneği** | **%30** | 🟠 | `app$ python -m eval.run_eval --gold data/gold/gold.v2.json` (`app/eval/run_eval.py`) · `app/data/gold/gold.v2.json` (48 kayıt, 40'ı zor vaka) · `app$ python -m eval.calibration --gold data/gold/gold.v2.json` · `app$ python -m scripts.report_iaa data/gold/review/round0_kalibrasyon_{A,B,C,D}.csv` | Sayı **var** ve yayımlanıyor (ölçüm 2026-08-21, temiz ağaç, `eval/reports/20260821-134101/`): yapılandırılmış alan mikro-F1 **0,8228**, 12-alan mikro-F1 **0,5702** [%95 GA 0,492–0,632], makro-F1 **0,7646**, halüsinasyon **0,0336** [15/447]. *(Önceki kesitler künyesiyle kayıtlı: 2026-08-15/16 → `0,671 / 0,464 [0,398–0,522] / 0,601 / 0,047 [21/447]` — `eval/reports/20260815-195653/`; 12 Ağustos → `0,646 / 0,452 [0,384–0,512] / 0,059` — `eval/reports/20260812-212355/`.)* İki sayı da veriliyor, farkı README'de açıklanıyor. **Neden ✅ değil:** ① gold hâlâ hareketli — en son 2026-08-21 HAKEM-05/S1 tahkim onarımı round1 değerlerini değiştirdi (0,738 → 0,795); sha256 yoldaş dosyaları güncel ama set "donduruldu" sayılamaz; ② anotatör uyumu **eşiğin altında** (Cohen κ 0,274 / Fleiss κ 0,302; anotasyon öncesi ilan edilen eşik 0,67) — eşik değiştirilmedi, ilan edilen sonuç uygulandı; ③ **insan hakemliği yok** — round1'in 53 vakalık kör hakemliği **alt ajanlara** yaptırıldı (`app/docs/rapor/oturum-2026-08-15-round1-onarimi.md` §2). `app/docs/anotasyon-hatti-plani.md` bunun sonucunu açıkça yazıyor: makine referansı **"gold" değil `silver-extended`**'dir; makine üretimi referansa karşı ölçülen P/R/F1 "model insanla ne kadar örtüşüyor"u değil, "bir model başka bir modelle ne kadar örtüşüyor"u ölçer ve **halüsinasyon oranı çapasız kalır**. Rubriğin en ağır kalemi budur; kapatılması gereken en büyük açık burasıdır. |
| **Fonksiyonellik ve Senaryo Kapsamı** | %20 | 🟠 | `app/src/comparison/compare.py` · `app/src/chatbot/` (router + text-to-SQL + RAG) · `app/web/` (Next.js dashboard) · `app$ python -m eval.rag_eval --db data/demo.db` · `app$ python -m src.chatbot.run_safety_eval --db data/demo.db` | Uçtan uca çalışıyor: 12 çıkarım alanı (+ kampanya türü), 8/8 kampanya türü üretilebiliyor, §5.7'nin **5/5 karşılaştırma ölçütü** kodda karşılanıyor (`rank()` + `rank_advantageous_by_type()`), dashboard + hibrit chatbot ayakta. RAG terim kapsama R@5 **0,867**, reddetme kararı **30/30**, güvenlik seti **29/30**. ✅ **YENİ (16 Ağu) — şartname Senaryo-1 tablosu artık ÜRETİLİYOR:** `GET /urun-tablosu` + Karşılaştırma sekmesi görünüm anahtarı, **7 sütun** (Banka · Ürün Türü · Kâr Payı Oranı · Vade · Kampanya Avantajı · Masraf Durumu · Kampanya Süresi), banka başına tek satır. Şartname s.12 örneğinde **21 hücrenin 18'i** dolu — boş kalan üçün üçü s.12'de de "Belirtilmemiş", yani birebir eşleşme; `tests/test_sartname_urun_tablosu.py` **32 test** bunu kilitliyor. Gerçek korpusta doluluk **%52,3** (ölçülen 5 sütun) / **%66,0** (tüm 7 sütun) — ölçüm 2026-08-16, 1.782 belgelik kesit; iki payda ayrı adlandırıldı. `/compare` **değişmedi**; yeni uç onun yerine değil yanına geldi. **Neden ✅ değil:** ① kâr payı oranı korpusun yalnız **146/2.708 = %5,4**'ünde var (ölçüm 2026-08-21; PDF hasadı payı %3,4'ten yükseltti) — kıyas motoru çalışıyor ama kapsamı dar ve bu gizlenmiyor. **Bu %5,4 Ürün Tablosu'nun GÖSTERDİĞİ kapsamı YANSITMAZ:** 146 kaydın 84'ü `belge_turu='sozlesme'` (banka "Ürün Bilgi Formu"/akit PDF'leri) ve `_field_rows`'un öntanımı (`main.py:496`, `sozlesme_dahil=False`) yüzünden Ürün Tablosu'na hiç girmiyor — bu kasıtlı, CLAUDE.md §17 "adil kıyas garantisi"nin uygulanması (akit metnindeki oran ile kampanya sayfasındaki oran aynı kolonda sıralanamaz). Ürün Tablosu'nun gerçekte gösterdiği kapsam **46/1335 = %3,4**'tür (46 = sözleşme-hariç + süresi-dolmamış kayıt sayısı, 1335 = aynı süzgeçten geçen toplam kampanya; ölçüm 2026-08-25, `data/demo.db`). **Doğrulandı (2026-08-25):** bu 84 sözleşme kaydı dahil edilse kapsam sorunu ÇÖZÜLMEZDİ — örneklenen kayıtların çoğu gerçek kâr payı oranı değil, **çıkarım hatasıdır**: madde/dipnot numaraları kâr payı oranı sanılmış (örn. "7. maddesi Kâr Payı Oranları'na" → `%7,0`), KKDF oranıyla karışmış ("Uygulanan tüm kâr payı oranlarına %15 oranında KKDF... eklenir" → `%15,0`, 16 kayıt), tahsis ücretiyle karışmış ("%0,5 oranındaki tahsis ücreti" → kâr payı sanılmış), gecikme cezası çarpanıyla karışmış ("cari en yüksek kâr payı oranına %30 ilave" → `%30,0`). Az sayıda kayıt (kredi kartı akdi kâr payı, taşıt/konut finansmanı bilgi formu gibi ürüne özgü alanlar) gerçek ve karşılaştırılabilir ama örneklemde azınlıkta; sözleşme kaynağını toptan dahil etmek Ürün Tablosu'na çıkarım gürültüsü enjekte ederdi. Bu yüzden `sozlesme_dahil` davranışı DEĞİŞTİRİLMEDİ. ② sınıflanamayan belge kesiti (2026-08-16 ölçümünde 60 belge / %7,1); ③ `app/docs/sartname-kod-eslesme.md` **kendi içinde çelişiyor**: §5.7 tablosu 5. ölçütü ✅ derken rubrik bölümü "5. ölçüt eksik" diyor — bu iç çelişki teslimden önce tek yönde kapatılmalı. |
| **Teknik İmplementasyon ve Mimari** | %20 | ✅ | `app$ python -m scripts.test_ozeti` → **3.605 toplanan · 3.552 geçen · 53 atlanan · 0 başarısız** (ölçüm 2026-08-21, **temiz ağaç** — `eval/reports/test-ozeti.json` `git_dirty: false`; atlananlar Postgres/pgvector isteyen testlerdir, `test-with-deps` işinde koşar) · `.github/workflows/ci.yml` (5 iş: bağımlılıksız testler, bağımlılıklı testler, Postgres/pgvector paritesi, ruff, frontend) · CI adımları: değişmez denetimi · eval regresyon kapısı (gold.v2) · eval regresyon kapısı (round1, ayrı taban) · gold kanıt zinciri · markdown link denetimi · **kanıt-tazeliği kapısı** · **lisans kapısı** · demo DB tazeliği | Katmanlar bağımsız test edilebilir (`src/scraping` · `preprocessing` · `extraction` · `normalization` · `comparison` · `rag` · `chatbot` · `api` · `db`). Her çıkarılan alan `span_start`/`span_end` taşıyor ve `verify_span()` ile `text[start:end] == raw_value` kendi kendini denetliyor. CI'da eval regresyon kapısı (alan F1 tabanı + halüsinasyon tavanı) var — ölçüm gerilerse build kırılır. ⚠️ Bilinen boşluk: pgvector kurulu ama üretim yolunda kullanılmıyor. CI adımları 15 Ağustos'ta ikiye çıktı: **kanıt-tazeliği kapısı** (yayımlanan sayı ile onu üreten kanıt ayrışırsa build düşer) ve **lisans kapısı**. |
| **On-Prem Uygulanabilirlik** | %20 | ✅ | `app/docs/OFFLINE-KANIT.md` · `app$ bash scripts/offline_proof.sh` · `app/docs/kaynak-tuketimi.md` · `app/docker-compose.yml` | Ölçülmüş: kural-only p50 **1,03 ms**, verim 21.087 belge/dk, tepe RSS 100,4 MB, imaj 96,5 MiB; api+postgres ≈255 MB'a karşı tam GPU yığını ≈10,6 GB (**40× fark** — "önce kural" mimarisinin paket boyutundaki karşılığı). Digest pin'li imajlar tekrar-üretilebilirlik veriyor. Kanıt iki katmanlı: tek konteyner `--network none` içinde **14/14 adım** + tam yığın (postgres + api + api-postgres + ollama + web) izole ağda **3/3 koşum · 39/39 adım** (2026-08-21 transkriptleri `docs/offline-proof/` altında). **Kalan kapsam sınırları** (kendimiz yazıyoruz): imaj derlemesi internet istiyor (iddia önceden derlenmiş imajlar için geçerli) · tüm ölçümler arm64'te, amd64 hiç ölçülmedi · vLLM/GPU kolu bu makinede koşmadı. *Rakiplerin bu kalemde kredi kaybettiği yer tam olarak burasıdır: ölçülmemiş bir on-prem iddiası, jüri kapsamı sorduğunda tüm matrisi düşürür.* |
| **Yenilikçilik ve Yaratıcılık** | %10 | ✅ | ① `app/src/comparison/contradiction.py` (37 KB) + `app$ python -m scripts.crosscheck_fees` — bankalar arası **çelişki tespiti** ("masrafsız" diyen kampanya + tahsis ücreti kaydı) · ② alan bazlı **güven skoru + kaynak span vurgulama** (`app/src/schemas.py` → `ExtractedField`, `verify_span()`, `tests/test_confidence_span.py`) · ③ **config-driven banka onboarding** (`app/config/banks.yaml`, 32 KB — yeni banka tek blok) | `decisions/daraltilmis-yenilikcilik-hedefleri.md`'deki üç hedefin üçü de kodda var, testle korunuyor ve demoda gösterilebilir. Dördüncü bir farklılaştırıcı: **ölçümle yanlışlanan hipotezi düzeltmemek** — ablasyon hibridi yanlışladı (0,575 < 0,612, p=0,0117; halüsinasyon 0,163 vs 0,102) ve sonuç düzeltilmeden yayımlandı. |

**Ağırlıklı okuma (son tazeleme 2026-08-21):** kanıtlı ✅ olan üç kriter toplam **%50** —
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
| ~~4~~ | ~~Demo videosu ≤5 dk~~ | ✅ **KAPANDI (16 Ağu)** — 3:04, kartsız, 12 ekran, tamamı gerçek arayüzden. |
| ~~5~~ | ~~Demo videosu 1 dk~~ | ✅ **KAPANDI (16 Ağu)** — 55 sn kesit, kartsız. |
| ~~6~~ | ~~Sunum PDF (§6.4)~~ | ✅ **KAPANDI (16 Ağu) · 21 Ağu'da 5 slayta indirildi** — `docs/sunum/anatolia-ai-sunum.pdf`, **5 sayfa**, 1440×810 pt (16:9), metin katmanı vektör/seçilebilir. Üreteç: `.venv/bin/python docs/sunum/uret-sunum.py`. *(Slayt sayısının seyri aşağıdaki nottadır.)* |
| ~~7~~ | ~~Sunum PPTX (§6.4)~~ | ✅ **KAPANDI (16 Ağu) · 21 Ağu'da 5 slayt** — `docs/sunum/anatolia-ai-sunum.pptx`, **5 slayt**, 20″×11,25″. Aynı üreteç. `python-pptx` (MIT) `.venv`'e kurulmadı. |

> **Slayt sayısının seyri: plan 8 → üretilen 15 → teslim edilen 5.**
> `sunum-ve-demo-plani.md` §C bir **plan** olarak 8 slayt öngörüyordu; 16
> Ağustos'ta üretilen sunum 15 slayt oldu (deponun geçmişinde «14 slayt» diyen
> bir commit mesajı da var — `7127045`). **21 Ağustos'ta 5 slayta indirildi:**
> şartname §10 sunum süresini 4 dakika veriyor ve 15 slayt o sürede
> sunulamıyordu; sunum bir savunma dokümanı gibi okunuyordu. 15 slaytlık sürüm
> **silinmedi**, `docs/archive/sunum-15-slayt-2026-08-21.html` içinde duruyor;
> savunma derinliği (κ asimetrisi, ölçüp geri adım atılan kararlar, açık
> kalemler) `docs/sunum/juri-4dk-konusmaci-notlari.md` içindeki jüri soru
> bankasına taşındı (dahili çalışma notu — yerelde durur, depoda izlenmez). Doğrulama plana ya da commit mesajına değil **sayıma**
> dayanıyor:
> ```bash
> .venv/bin/python -c "
> import zipfile,re
> from pypdf import PdfReader
> print('PDF :', len(PdfReader('docs/sunum/anatolia-ai-sunum.pdf').pages))
> z=zipfile.ZipFile('docs/sunum/anatolia-ai-sunum.pptx')
> print('PPTX:', len([n for n in z.namelist()
>                     if re.match(r'ppt/slides/slide\d+\.xml$', n)]))"
> # -> PDF : 5   PPTX: 5
> ```
> Plandaki 8 rakamı **düzeltilmedi, aşıldı** — `sunum-ve-demo-plani.md` bir
> tasarım belgesidir, teslim kanıtı değildir; bu satırın kanıtı üretilen
> dosyaların kendisidir.

### 🟠 — kısmi kalemler

| # | Kalem | Aksiyon |
|---:|---|---|
| 8 | **Model Başarısı %30 — insan çapası** | Kalibrasyon A/B/C/D kümesini (20 belge × 13 alan) **insan** anotatörle tamamla; raporda iki sayıyı ayrı ver: `κ(insan, insan)` ve `uyum(LLM, insan)`. Makine üretimi kümeyi `gold` değil **`silver-extended`** olarak adlandır (`app/docs/anotasyon-hatti-plani.md`). |
| 9 | Model Başarısı %30 — gold dondurma | Round1 bitince `gold.round1.json`'ı SHA-256 ile dondur, `eval/esikler.json`'u güncelle ve P/R/F1'i **dondurulmuş** set üzerinde yeniden yayımla. |
| ~~10~~ | ~~On-Prem %20 — kanıt tazeliği~~ | ✅ **KAPANDI** — `offline_proof.sh` temiz ağaçta yeniden koşuldu, **14/14 adım**. |
| ~~11~~ | ~~On-Prem %20 — kapsam genişletme~~ | ✅ **KAPANDI (21 Ağu)** — tam yığın (postgres + api + api-postgres + ollama + web) izole ağda **3/3 koşum · 39/39 adım**; transkriptler `docs/offline-proof/tam-yigin-agsiz-transcript-*.log`. Kalan sınır (amd64 ölçülmedi) matriste ve envanterde (T-041) yazılı. |
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
