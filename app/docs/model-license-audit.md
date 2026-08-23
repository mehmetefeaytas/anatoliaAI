# Model ve Bağımlılık Lisans Denetimi

**Durum:** modeller doğrulandı; bağımlılıklarda 1 açık kalem (`⏳ trafilatura`)
**Son güncelleme:** 2026-07-31
**Sorumlu kalem:** Şartname §5.10 ve §8

**Ek denetim (15 Ağu 2026):** Ollama yerel ağırlıkları (`qwen2.5:7b-instruct`,
`qwen3.5:9b-q4_K_M`) denetime alındı — bkz. §1'deki iki yeni satır, "Ollama
yerel ağırlıkları" alt bölümü ve belge sonundaki *2026-08-15 eklemesi* notu.

**Doğrulama yöntemi (31 Tem 2026):** her model için HuggingFace model kartı
canlı çekildi; `license` alanı ve `base_model` zinciri **köküne kadar** takip
edildi; kullanım kısıtı içeren cümleler birebir alıntılandı. Aşağıdaki
"Kanıt" sütunundaki alıntılar model kartından **doğrudan** aktarılmıştır.

---

## Neden bu belge var

Şartname §5.10 birebir şunu söylüyor:

> Çalışmada geliştirilecek tüm kodlar **açık kaynak kod tabanlı teknolojiler**
> kullanılarak geliştirilmelidir. **Açık kaynaklı gözüküp, uygulama aşamasında
> lisans problemi çıkarma potansiyeli olan çözümler kullanılmamalıdır.**

§8 ise ücretli yazılım ve üçüncü taraf hizmet kullanımını yasaklıyor, ve
yarışma bitiminde tüm bileşenlerin **Apache-2.0** ile Türkiye Açık Kaynak
Platformu hesabında paylaşılacağını şart koşuyor.

"Açık kaynaklı gözüküp lisans problemi çıkarma potansiyeli" ifadesi doğrudan
**Llama Community License** ve **Gemma Terms of Use** gibi, açık kaynak
sanılan ama kullanım kısıtı içeren model lisanslarını tarif ediyor. Bu belge,
projedeki her model ve ağır bağımlılık için lisans zincirini kayıt altına alır.

**Kural:** Bu tabloda `✅` olmayan hiçbir bileşen teslim edilen sisteme
giremez.

---

## 1. Modeller

| Bileşen | Rol | Lisans | Taban zinciri (köke kadar) | Durum |
|---|---|---|---|---|
| **Qwen3-8B** (`Qwen/Qwen3-8B`) | Çıkarım LLM'i (Colab/deney) | **Apache-2.0** | kök (sıfırdan eğitim, Qwen) | ✅ |
| **Qwen3-4B** (`Qwen/Qwen3-4B`) | Çıkarım LLM'i (demo, CPU/GGUF) | **Apache-2.0** | kök | ✅ |
| **Trendyol-LLM-8B-T1** | Ana çıkarım LLM'i (`docker-compose` vLLM) | **Apache-2.0** | `Qwen3-8B-Base → Qwen3-8B → Trendyol-8B` — Llama/Gemma **yok** | ✅ |
| **BERTurk** (`dbmdz/bert-base-turkish-cased`) | 8-sınıf sınıflandırıcı | **MIT** | kök | ✅ |
| **bge-m3** (`BAAI/bge-m3`) | Embedding (İH5'te devreye girecek) | **MIT** | XLM-RoBERTa (MIT) | ✅ |
| **mDeBERTa-v3-base** (`microsoft/mdeberta-v3-base`) | GLiNER omurgası | **MIT** | kök | ✅ |
| **GLiNER v2.1** (`urchade/gliner_multi-v2.1`) | Tamamlayıcı NER (geri-çağırma ağı) | **Apache-2.0** | mDeBERTa-v3-base (MIT) → temiz | ✅ |
| **NuExtract-2.0-8B** (`numind/NuExtract-2.0-8B`) | Ablasyon kolu — şablon-güdümlü çıkarım | **MIT** | `Qwen2.5-VL-7B-Instruct` (**Apache-2.0**) → temiz | ✅ |
| **TabiBERT** | Sınıflandırıcı alternatifi | bilinmiyor | doğrulanmadı | ⏳ gündeme alınmadı |
| **Qwen2.5-7B-Instruct** (`qwen2.5:7b-instruct`, Ollama Q4_K_M) | **Ollama kolunun ÜRETİM VARSAYILANI** (`clients.py:437`, `.env.example:56`) — ablasyon, gümüş denetleyici, özetleyici, chatbot | **Apache-2.0** | `Qwen/Qwen2.5-7B` (kök, sıfırdan eğitim) → `Qwen/Qwen2.5-7B-Instruct` → Ollama GGUF Q4_K_M — Llama/Gemma **yok** | ✅ (15 Ağu 2026) |
| **Qwen3.5-9B** (`qwen3.5:9b-q4_K_M`, Ollama Q4_K_M) | Yalnız **ölçüm aracı** — düşünme kipi ölçümü (`clients.py:486`, `.env.example:61`, `tests/test_llm_client.py:534`); teslim edilen kod yolunda **kullanılmıyor** | **Apache-2.0** | `Qwen/Qwen3.5-9B-Base` (kök, sıfırdan eğitim) → `Qwen/Qwen3.5-9B` → Ollama GGUF Q4_K_M — Llama/Gemma **yok** | ✅ (15 Ağu 2026) |

### Trendyol-LLM-8B-T1 — ⛔ BLOKE kararının kaldırılması (31 Tem 2026)

Bu model 27 Temmuz'da *"taban model zinciri doğrulanmadan kullanılamaz — Trendyol
hem Llama hem Qwen tabanlı modeller yayımladı"* gerekçesiyle **⛔ BLOKE**
işaretlenmişti. Gerekçe o tarihte doğruydu; zincir bugün doğrulandı ve **temiz
çıktı**, karar bu yüzden ✅'e çevrildi:

| Kanıt | Model kartındaki karşılığı |
|---|---|
| Lisans | `license: Apache-2.0` — *"identical to the base Qwen 3-8B"* |
| Ticari kullanım | *"Apache-2.0 licence – free for commercial and research use."* |
| Taban model | `Qwen/Qwen3-8B` üzerinden fine-tune; model ağacı `Qwen3-8B-Base → Qwen3-8B → Trendyol-LLM-8B-T1` |
| Llama / Gemma / Mistral | Model kartında bu kelimeler **hiç geçmiyor** |
| Ek kısıt | Non-commercial veya research-only kısıtı **yok** |

Bu, `app/CLAUDE.md` §7'nin baştan beri yaptığı *"Trendyol-LLM-8B-T1 (Qwen3-8B
tabanlı, Apache-2.0)"* tespitini teyit eder. Model `docker-compose.yml`'de
kullanılmaya devam eder ve ayrıca **ablasyon kolu K2b** olarak ölçülür:
*Türkçeye özel ayarlama finansal bilgi çıkarımında saf Qwen3-8B'ye göre kazanç
sağlıyor mu?* İkisinin **tabanı aynı** olduğu için tek değişken Türkçe fine-tune
— temiz kontrollü karşılaştırma.

### Ollama yerel ağırlıkları — zincir doğrulaması (15 Ağu 2026)

Bu iki ağırlık geliştirme makinesinde **kurulu** ve biri **üretim varsayılanı**
olduğu halde 31 Temmuz denetimine hiç girmemişti; §5'teki *"docker-compose'da
kullanılan her ağırlığın burada ✅ karşılığı var"* maddesi Ollama kolunu
kapsamıyordu. Zincirler bugün köke kadar takip edildi ve **ikisi de temiz çıktı.**

#### Qwen2.5-7B-Instruct (`qwen2.5:7b-instruct`) — üretim varsayılanı

| Kanıt | Karşılığı |
|---|---|
| Yerel künye (`ollama show`) | `architecture qwen2` · `parameters 7.6B` · `context 32768` · `quantization Q4_K_M` |
| Yerel lisans metni (`ollama show --license`) | 202 satır, **birebir Apache License 2.0**; `llama` / `gemma` / `non-commercial` / `research only` / `acceptable use` / `qwen research` kelimelerinin **hiçbiri geçmiyor** (grep ile tarandı) |
| Ollama dağıtım künyesi | Lisans: *"Apache License Version 2.0, January 2004"* · `qwen2` · 7.62B · Q4_K_M — <https://ollama.com/library/qwen2.5:7b-instruct> |
| Üst kaynak model kartı | `license: apache-2.0`, `base_model: Qwen/Qwen2.5-7B` — <https://huggingface.co/Qwen/Qwen2.5-7B-Instruct> |
| **Zincirin kökü** | `Qwen/Qwen2.5-7B` — `base_model` alanı **yok**, sıfırdan ön-eğitim (*"This repo contains the base 7B Qwen2.5 model"*), `license: apache-2.0` — <https://huggingface.co/Qwen/Qwen2.5-7B> |
| Ticari kısıt | Zincirin **hiçbir halkasında** non-commercial / research-only kısıtı yok |

#### Qwen3.5-9B (`qwen3.5:9b-q4_K_M`) — yalnız ölçüm aracı

> **Çelişki kaydı.** `docs/model-lisanslari/README.md` 15 Ağu 2026'da bu
> bölümün tersini yazıyordu (*"adın yukarı akış karşılığını
> doğrulayamıyoruz"*). Çelişki 5. tur On-Prem jürisi tarafından bulundu,
> 23 Ağu 2026'da HuggingFace API'sinden canlı doğrulamayla **bu bölüm lehine
> çözüldü** ve orada `## ÇELİŞKİ` başlığı altında kayda geçti.

Önce **ad doğrulandı**: "Qwen3.5" gerçek bir aile mi, yoksa Ollama'daki etiket
başka bir modelin yeniden adlandırılmış hâli mi? Aile **gerçek** ve HuggingFace'te
Qwen'in kendi hesabı altında yayımlı; yerel künye ile üst kaynak künyesi
**birebir örtüşüyor**, yani etiket başka bir modelin takma adı değil:

| Alan | Yerel (`ollama show`) | Ollama dağıtımı | Üst kaynak (HF) |
|---|---|---|---|
| Mimari | `qwen35` | `qwen35` | Gated Delta Networks + seyrek MoE |
| Parametre | 9.7B | 9.65B | 9B |
| Nicemleme / boyut | Q4_K_M / 6.6 GB | Q4_K_M / 6.6 GB | — |
| Bağlam | 262144 | — | 262.144 (yerel) |
| Yetenek | `vision`, `thinking` | — | *"Unified Vision-Language Foundation"* + varsayılan `<think>` kipi |

| Kanıt | Karşılığı |
|---|---|
| Yerel lisans metni (`ollama show --license`) | 201 satır, **birebir Apache License 2.0**; kısıt kelimelerinin hiçbiri geçmiyor (grep ile tarandı) |
| Ollama dağıtım künyesi | Lisans: *"Apache License Version 2.0, January 2004"* — <https://ollama.com/library/qwen3.5:9b> |
| Üst kaynak model kartı | `license: apache-2.0`, `base_model: Qwen/Qwen3.5-9B-Base` — <https://huggingface.co/Qwen/Qwen3.5-9B> |
| **Zincirin kökü** | `Qwen/Qwen3.5-9B-Base` — `base_model` alanı **yok**, sıfırdan ön-eğitim (*"pre-trained only model"*), `license: apache-2.0` — <https://huggingface.co/Qwen/Qwen3.5-9B-Base> |
| Ticari kısıt | Zincirin hiçbir halkasında yok |

**GGUF nicemleyicisinin lisansı:** her iki etikette de nicemlemeyi Ollama'nın
kendi kütüphanesi yayımlıyor; üçüncü taraf quant sağlayıcısı yok. Nicemlenmiş
yapıtın **içine gömülü** lisans metni (`ollama show --license`) taban modelin
Apache-2.0'ını birebir taşıyor — yani devralma varsayılmadı, **doğrulandı**.

**Kalan tek çekince (kayda geçirilir):** Ollama kütüphane sayfası kaynak
HuggingFace deposunu **açıkça linklemiyor**; etiket→depo eşlemesi yukarıdaki
künye örtüşmesinden çıkarıldı. Bu, lisans sonucunu değiştirmez — hem yapıta
gömülü metin hem Ollama künyesi hem de eşlemenin **tüm** olası üst kaynakları
(`Qwen3.5-9B` ve `Qwen3.5-9B-Base`) Apache-2.0.

**Dikkat — Qwen2.5 ailesi tek tip DEĞİL:** `Qwen/Qwen2.5-3B-Instruct`
`license: qwen-research` taşır (<https://huggingface.co/Qwen/Qwen2.5-3B-Instruct>),
yani aynı ailede boy değiştirmek lisans değiştirebilir. Bu, NuExtract-4B
vakasının Qwen2.5 tarafındaki karşılığıdır: **"aile Apache-2.0" diye bir şey
yok, yalnız o depo Apache-2.0'dır.** `7b` etiketinden `3b`'ye düşülürse denetim
**yeniden** yapılmalıdır.

### ⛔ Kullanılmayacaklar (karar verilmiş)

| Model / aile | Sebep | Kanıt |
|---|---|---|
| Llama 3.x / 3.3 ve tüm türevleri | Llama Community License — kullanım kısıtı içerir, Apache-2.0'a dönüştürülemez | lisans metni |
| Gemma 2 / 3, EmbeddingGemma, WiroAI-9b | Gemma Terms of Use — aynı sorun | lisans metni |
| ytu-ce-cosmos Turkish-Llama / Turkish-Gemma | Taban zinciri Llama/Gemma'ya çıkıyor | model kartı |
| **TURNA** (`boun-tabi-LMG/TURNA`) | Açık kaynak **değil**. §5.10'un tam olarak tarif ettiği "açık kaynaklı gözüküp lisans problemi çıkarma potansiyeli" kategorisi | Kart birebir: *"The model is shared with the public to be used solely for **non-commercial** academic research purposes."* Ayrıca *"Out-of-Scope Use: Any commercial or malicious activity."* |
| **UniNER-7B-all** (`Universal-NER/UniNER-7B-all`) | **İki kat** engel: CC BY-NC 4.0 (non-commercial) **ve** Llama tabanlı | model kartı |
| **NuExtract-2.0-4B** | Taban `Qwen2.5-VL-3B-Instruct` → **Qwen Research License** taşıyor. Dikkat: aynı ailenin **8B ve 2B**'si temiz (Apache-2.0 tabanlı), yalnız **4B** kirli | model kartı |
| **GLiNER2** (`fastino/gliner2-base-v1`) | Lisansı temiz (Apache-2.0) ama **Türkçe desteği doğrulanamadı** — çok dilli eğitimi 7 Batı Avrupa diliyle sınırlı. Doğrulanmamış bileşen §5.10 riski taşır; GLiNER v2.1 yeterli | model kartı + proje README |

**Ders (kayda geçirilir):** türetilmiş bir modelin `license` etiketi Apache-2.0
görünse dahi **taban zinciri kirli olabilir** (NuExtract-4B örneği). Tersi de
doğru: bir model geçmişte temkinli olarak bloke edilmiş olabilir ama zinciri
temiz çıkabilir (Trendyol örneği). **Her iki yönde de zincir doğrulanmadan
karar verilmez.**

`app/CLAUDE.md` §7 bu kararı zaten kayıt altına almış; bu belge onun kanıt katmanıdır.

### Doğrulama prosedürü (her model için)

```bash
# 1. Model kartını ve LICENSE dosyasını indir
huggingface-cli download <repo_id> LICENSE README.md --local-dir /tmp/lic/<ad>

# 2. SHA-256 al ve bu belgeye yaz
shasum -a 256 /tmp/lic/<ad>/LICENSE

# 3. Model kartındaki `base_model:` alanını takip et — zincirin KÖKÜNE kadar.
#    Kök Llama/Gemma ise model reddedilir.
```

---

## 2. Python bağımlılıkları

Kaynak: `app/requirements.txt`, `app/requirements-api.txt`

> **Bu tablo doğrudan bağımlılıkları kapsar; tam envanter için**
> [`LISANSLAR.md`](LISANSLAR.md) **ve** [`sbom.json`](sbom.json).
>
> Aradaki fark büyüktür ve kasıtlı olarak gösterilir: aşağıdaki tablo elle
> yazılmış **15 satırdır**, `sbom.json` ise kurulu ortamdaki **96 bileşeni**
> makinenin okuduğu biçimde (CycloneDX 1.6) listeler. Elle tutulan tablo
> yalnızca *bizim ilan ettiğimizi* bilir; SBOM *gerçekte ne kurulu olduğunu*
> bilir — geçişli (transitive) bağımlılıklar dâhil. İkisi
> `make lisanslar sbom lisans-kapisi` ile üretilir ve
> [`../scripts/lisans_kapisi.py`](../scripts/lisans_kapisi.py) kapısıyla
> denetlenir; izin listesi dışı bir lisans çıkış kodu 1 verir.
>
> **15 Ağu 2026 güncellemesi:** aşağıdaki `⏳ trafilatura` satırı artık açık
> risk DEĞİLDİR — paketin kendi `PKG-INFO` ve `LICENSE` dosyaları okundu,
> gerçek lisansı **Apache-2.0** çıktı. Ayrıntı ve kanıt:
> [`LISANSLAR.md` § Risk kalemleri](LISANSLAR.md).

| Paket | Lisans | Durum | Not |
|---|---|---|---|
| pydantic | MIT | ✅ | |
| fastapi | MIT | ✅ | |
| uvicorn | BSD | ✅ | |
| requests | Apache-2.0 | ✅ | |
| beautifulsoup4 | MIT | ✅ | |
| playwright | Apache-2.0 | ✅ | |
| transformers | Apache-2.0 | ✅ | |
| sentence-transformers | Apache-2.0 | ✅ | |
| gliner | Apache-2.0 | ✅ | Şu an **kodda hiç kullanılmıyor** — bkz. §4 |
| zeyrek | MIT | ✅ | Şu an **kodda hiç kullanılmıyor** — bkz. §4 |
| ruff / black / pytest | MIT | ✅ | Yalnızca geliştirme |
| psycopg[binary] | LGPL | ✅ | Dinamik bağlı istemci kütüphanesi; Apache-2.0 uygulama ile birlikte dağıtımı sorun değil |
| pgvector (Python) | PostgreSQL lisansı | ✅ | İzin verici |
| **trafilatura** | **Apache-2.0** | ✅ (15 Ağu 2026'da doğrulandı) | Yorumdaki "GPLv3+" **yanlıştı**; aşağıya bakınız |

### ✅ trafilatura — kapanan risk kalemi (15 Ağu 2026)

`requirements.txt` kendi yorumunda `# GPLv3+` yazıyor. GPLv3, Apache-2.0 ile
birlikte dağıtımda **uyumsuzluk yaratır** ve şartnamenin "yarışma bitiminde
Apache-2.0 ile paylaşılacak" şartıyla çelişir.

**15 Ağu 2026 — doğrulandı, iddia yanlış çıktı.** Paketin kaynak dağıtımı
indirilip kendi dosyaları okundu (`pip download --no-deps --no-binary :all:`):

| Sürüm | `PKG-INFO` lisans alanı | `LICENSE` gövdesi |
|---|---|---|
| `2.2.0` (bugünkü uç) | `License-Expression: Apache-2.0` | Apache-2.0 tam metni, **sıfır** `GNU`/`GPL` geçişi |
| `1.8.0` (pinin alt sınırı) | `License: Apache-2.0` + OSI Apache classifier | aynı |

Pin `>=1.8` bir **aralık** açtığı için iki uç da ayrı ayrı ölçüldü; ikisi de
Apache-2.0. Yani `requirements.txt` içindeki `# GPLv3+` yorumu **yanlıştır**.

**Bunun sonuçları:**

1. Paketi teslim imajına almanın önündeki *lisans* engeli yoktur. Almak ya da
   almamak artık bir **mimari** karardır, lisans kararı değil.
2. `scripts/offline_proof.sh` (11–12. adımlar) trafilatura'nın teslim imajında
   bulunmadığını "GPLv3+ riski" gerekçesiyle kanıtlıyor. Adımlar hâlâ geçiyor
   ama **gerekçeleri dayanaksız kaldı**; metni güncellenmelidir.
3. `app/CLAUDE.md` §3 veri akışında `clean (trafilatura)` yazıyor, oysa
   `src/scraping/collector.py:199` "trafilatura KULLANILMIYOR" diyor. Bu
   doküman–kod tutarsızlığı lisanstan bağımsız olarak duruyor.

*(Tarihsel not: aşağıdaki eski gerekçe kaydı, kararın nasıl alındığını
göstermek için bırakılmıştır.)*

**Risk neden düşük:** trafilatura kodda **opsiyonel**. `src/scraping/collector.py`
içindeki `_extract_main_text`, paket yoksa `src/preprocessing/clean.py`'deki
saf stdlib `strip_html`'e düşüyor. Yani sistem trafilatura olmadan da çalışıyor.

**Karar (Gün 1):** doğrulanana kadar `requirements.txt`'te **opsiyonel** olarak
işaretlendi ve `requirements-api.txt`'e (teslim edilen imaj) **alınmadı**.

**Yapılacak:**
```bash
pip download trafilatura==<pin> --no-deps -d /tmp/tf && \
  python -c "import importlib.metadata as m; print(m.metadata('trafilatura')['License'])"
# Apache-2.0 değilse: readability-lxml (Apache-2.0) ile değiştir veya
# tamamen çıkar (strip_html fallback zaten yeterli).
```

---

## 3. Frontend ve araçlar

| Bileşen | Lisans | Durum |
|---|---|---|
| Next.js 14 | MIT | ✅ |
| React 18 | MIT | ✅ |
| TypeScript | Apache-2.0 | ✅ |
| Recharts (planlanan) | MIT | ⏳ eklenirse teyit |
| LibreOffice Impress (sunum) | MPL-2.0 | ✅ ücretsiz, §8 uyumlu |
| OBS Studio (video) | GPL-2.0 | ✅ araç, teslim edilen ürünün parçası değil |
| Shotcut / Kdenlive (kurgu) | GPL | ✅ aynı gerekçe |
| **`edge-tts`** (demo videosu anlatım sesi) | **LGPL-3.0-or-later** (+1 dosya MIT) | ✅ araç — `.venv`'de **DURMAZ**, bkz. aşağıdaki not |
| **`ffmpeg`** (montaj) | GPL/LGPL (derlemeye göre) | ✅ aynı gerekçe, harici ikili |
| `python-pptx` (sunum PPTX) | MIT | ✅ yardımcı ortamda: `~/.cache/anatolia-ai/sunum-venv` |
| `playwright` (ekran/PDF) | Apache-2.0 | ✅ proje `.venv`'inde, envanterde |

**Not:** GPL lisanslı *araçlar* (OBS, Kdenlive) sorun değildir — bunlar teslim
edilen yazılımın parçası değil, onu üretmekte kullanılan editörlerdir. Sorun
yaratan, GPL kodun teslim edilen ürüne **linklenmesi**dir (trafilatura vakası).

### `edge-tts` — beyan, iki gerileme ve kapı

5. tur On-Prem jürisi haklı bir eksik buldu: bu araç kullanılıyordu ama
**bu tabloda beyan edilmemişti**. Beyan artık yukarıda; altındaki üç şey de
kayda geçiyor.

**Neden `.venv`'de durmuyor.** `make sbom` KURULU ortamı tarar. `edge-tts`
`.venv`'e girdiğinde envanter 96'dan 105'e çıkıyor ve lisans kapısı düşüyor:
kendisi LGPL-3.0 kovasında, geçişli bağımlılığı `multidict`'in lisans alanı
ise `cyclonedx-py` tarafından okunamıyor (gerçekte Apache-2.0). Yani sorun
lisansın kendisi değil — araç olduğu için §3'ün gerekçesi ona da uyar —
**envanteri kirletmesi**dir.

**İki kez oldu.** 16 Ağu 2026'da dokuz paket (`edge-tts` + `aiohttp` ailesi +
`tabulate`) kaldırıldı, 96'ya dönüldü ve karar `app/README.md`'ye yazıldı.
23 Ağu 2026'da **aynı dokuz paket geri geldi** (1 dakikalık videonun
seslendirmesi üretilirken) ve taze SBOM'la kapı yine düştü. Karar duruyordu
ama onu **koruyan bir kapı yoktu** — yalnız bir belge vardı.

**Kapı artık var:** `make sbom-sapma` (`scripts/sbom_sapma.py`, 10 test).
Kurulu ortam ile commit'li `docs/sbom.json` ayrışırsa çıkış kodu 1 verir ve
iki meşru çözümü adıyla söyler: gerçek bağımlılıksa `requirements.txt`,
tek seferlik araçsa yardımcı ortam (emsal: `python-pptx`).

**On-prem sınırı, lisanstan bağımsız.** `edge-tts` Microsoft'un Edge
okuma-sesi **bulut** servisine çıkar. Teslim edilen yolun içine girmez ve
girmediği ölçülüyor (`tam_yigin_agsiz.sh`: izole ağ, negatif kontrol 4/4
engelli). Buluta giden tek şey **anlatım metnidir**
(`demo-video/anlatim*/*.txt`, depoda açıkça duruyor); hiçbir banka verisi,
korpus metni ya da gold kaydı gönderilmez. Ses dosyaları bir kez üretilip
dosya olarak saklanıyor; ürün çalışırken hiçbir TTS çağrısı yapılmaz.

---

## 4. Kullanılmayan bağımlılıklar (temizlik borcu)

Aşağıdakiler `requirements.txt`'te ilan edilmiş ama kod tabanında **sıfır
referansı** var. Şartname §9 "bağımlılıkların eksiksiz listesi" istiyor —
kullanılmayan bağımlılık ilan etmek bu listeyi yanıltıcı yapar.

| Paket | Durum | Karar |
|---|---|---|
| `gliner` | Kodda hiç geçmiyor (3 katmanlı mimarinin "tamamlayıcı NER" katmanı yok) | **Karar (31 Tem):** ablasyon kolu **K3** olarak uygulanacak — kural boş dönüp GLiNER bir span bulduğunda LLM tetikleyicisi ("geri-çağırma ağı"). Dev split'te K2'yi geçmezse hem kol hem bağımlılık düşer |
| `zeyrek` | Kodda hiç geçmiyor (TR morfoloji katmanı yok) | **Karar (31 Tem):** kaldırılacak. TR-özel ihtiyaçları `preprocessing/clean.py`'deki `tr_fold`/`tr_upper` ve `synonyms.py` karşılıyor; morfoloji katmanına ihtiyaç doğmadı. Kullanılmayan bağımlılık ilan etmek §9'un "eksiksiz bağımlılık listesi" şartını yanıltıcı yapar |
| `sentence-transformers` | Yalnızca yorumlarda | İH5'te gerçek `VectorRetriever` ile kullanılacak |
| `psycopg` / `pgvector` | Yalnızca yorumlarda; `repository.py` SQLite-only | İH5'te gerçekten devreye alınacak |

---

## 5. Denetim kontrol listesi (her teslim öncesi)

- [x] **Model tablosunda `⏳` kalmadı** (31 Tem — TabiBERT hiç gündeme alınmadığı için kapsam dışı)
- [x] **Hiçbir model zinciri Llama/Gemma/non-commercial köküne çıkmıyor** (her zincir köke kadar takip edildi)
- [x] **`docker-compose.yml`'de kullanılan her ağırlığın burada `✅` karşılığı var**
- [x] `requirements.txt` = kodda gerçekten kullanılan paketler *(15 Ağu 2026'da
      ölçüldü)* — §4'teki temizlik borcu kapandı: `gliner` ve `zeyrek` yoruma
      alındı, `pgvector` kaldırıldı, `sentence-transformers` ve `psycopg` artık
      gerçekten import ediliyor. Etkin olarak ilan edilen her paketin kodda
      karşılığı var; tek istisna `uvicorn` ve o da bir **kütüphane değil süreç**
      (`Dockerfile.api:47` `CMD ["uvicorn", ...]`), yani import edilmemesi
      beklenen davranıştır. `trafilatura` yorumda kalmaya devam ediyor ve kodda
      sıfır referansı var (`src/scraping/collector.py:199`) — tutarlı.
      **Kalan borç lisans değil belge borcudur:** o satırdaki `# GPLv3+` yorumu
      yanlıştır (gerçek lisans Apache-2.0, bkz. §2) ve düzeltilmelidir.
- [ ] Teslim imajında GPL linklenmiş kod yok → kanıtı `OFFLINE-KANIT.md`'ye yazılacak
- [x] Kök `LICENSE` = Apache-2.0
- [ ] Veri seti lisansı belirtilmiş (CC-BY-4.0) + şartname s.18'in istediği **herkese açık indirme bağlantısı** README'de

**Kural hatırlatması:** Bu tabloda `✅` olmayan hiçbir bileşen teslim edilen
sisteme giremez. Tersi de geçerli — `⛔` bir kalem kodda kullanılıyorsa bu bir
**doküman–kod tutarsızlığıdır** ve jüri için lisans ihlalinden farksız görünür.
27–31 Temmuz arasında tam bu durumdaydık (Trendyol `⛔` işaretliyken
`docker-compose.yml:27`'de çalışıyordu); doğrulama bunu kapattı.

---

## 2026-08-15 eklemesi — bu iki model denetime neden girdi

**Kısa cevap: üretim varsayılanı denetimsizdi.**

`qwen2.5:7b-instruct`, `src/extraction/llm/clients.py:437`'de `OllamaClient`'ın
**varsayılan modeli**; `OLLAMA_MODEL` elle verilmediği her koşumda çalışan ağırlık
budur (`.env.example:56`). Ayrıca ablasyon künyesinde
(`docs/rapor/ablasyon.md §6`), LLM modu güvenlik koşumunda
(`docs/rapor/guvenlik-llm-modu.md`), gümüş denetleyicide
(`scripts/run_silver_verifier.py`), özetleyicide (`src/summarize/ozet.py`) ve
chatbot ölçümünde (`src/chatbot/bot.py`) adı geçiyor. Buna rağmen 31 Temmuz
tablosunda **hiç yer almıyordu.**

Bu, belgenin kendi kuralının ihlaliydi: *"Bu tabloda `✅` olmayan hiçbir bileşen
teslim edilen sisteme giremez."* §5'teki kontrol maddesi `docker-compose.yml`
üzerinden yazıldığı için **Ollama kolunu görmüyordu** — oysa `app/CLAUDE.md` §2
Ollama'yı açıkça demo yedeği olarak konumlandırıyor, yani teslim edilen sistemin
parçası. Durum 27–31 Temmuz'daki Trendyol vakasının **aynadaki hâliydi**: orada
`⛔` bir kalem kodda çalışıyordu, burada **hiç işaretlenmemiş** bir kalem üretim
varsayılanıydı. İkisi de doküman–kod tutarsızlığıdır ve jüri için lisans
ihlalinden farksız görünür.

`qwen3.5:9b-q4_K_M` aynı makinede kurulu ikinci ağırlık. Teslim edilen kod
yolunda kullanılmıyor; yalnız düşünme kipinin `num_predict` bütçesini yiyip boş
cevap bıraktığını **ölçmek** için koşuldu (`clients.py:486`, `.env.example:61`).
Denetime alınmasının sebebi kullanımı değil **kurulu olması**: makinede duran her
ağırlık, ölçüm künyesine adı geçtiği anda belgelenebilir olmak zorunda.

**Sonuç:** her iki zincir de köke kadar takip edildi, ikisi de Apache-2.0 kökten
temiz çıktı, ikisi de `✅`. Denetimsizlik giderildi; **lisans riski çıkmadı.**
Süreç dersi ise duruyor: bir bileşen **denetimden geçmediği için** değil,
**kimse bakmadığı için** listede yoktu. §5'in `docker-compose.yml` odaklı kontrol
maddesi, `.env.example` ve kod varsayılanlarındaki ağırlıkları da kapsayacak
şekilde okunmalıdır.

---

## Sources

- `raw/teknofest/2026-teknofest-tyda-sartname-2-senaryo.pdf` — §5.10, §8
- `../../decisions/apache-2-acik-kaynak-lisansi.md`
- `app/CLAUDE.md` §7 (lisans tuzağı), §20 (uyumluluk kontrol listesi)

## Related

- [[apache-2-acik-kaynak-lisansi]] — kararın kendisi
- [[on-premise-calistirilabilir-mimari]] — offline kısıtı, model seçimini daraltır
- [[acik-kaynak-yaklasimi]]
