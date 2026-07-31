# Model ve Bağımlılık Lisans Denetimi

**Durum:** modeller doğrulandı; bağımlılıklarda 1 açık kalem (`⏳ trafilatura`)
**Son güncelleme:** 2026-07-31
**Sorumlu kalem:** Şartname §5.10 ve §8

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
| **trafilatura** | **⚠️ belirsiz** | ⏳ **AÇIK RİSK** | Aşağıya bakınız |

### ⏳ trafilatura — açık risk kalemi

`requirements.txt` kendi yorumunda `# GPLv3+` yazıyor. GPLv3, Apache-2.0 ile
birlikte dağıtımda **uyumsuzluk yaratır** ve şartnamenin "yarışma bitiminde
Apache-2.0 ile paylaşılacak" şartıyla çelişir.

Bilinen: trafilatura projesi bir sürümde Apache-2.0'a geçti ve `requirements.txt`
pinlemesi (`>=1.8`) muhtemelen o eşiğin üstünde. **Ancak bu doğrulanmadı** —
bu ortamda paket kurulu değil ve ağ erişimiyle teyit edilmedi.

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

**Not:** GPL lisanslı *araçlar* (OBS, Kdenlive) sorun değildir — bunlar teslim
edilen yazılımın parçası değil, onu üretmekte kullanılan editörlerdir. Sorun
yaratan, GPL kodun teslim edilen ürüne **linklenmesi**dir (trafilatura vakası).

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
- [ ] `requirements.txt` = kodda gerçekten kullanılan paketler → §4'teki temizlik borcu
- [ ] Teslim imajında GPL linklenmiş kod yok → kanıtı `OFFLINE-KANIT.md`'ye yazılacak
- [x] Kök `LICENSE` = Apache-2.0
- [ ] Veri seti lisansı belirtilmiş (CC-BY-4.0) + şartname s.18'in istediği **herkese açık indirme bağlantısı** README'de

**Kural hatırlatması:** Bu tabloda `✅` olmayan hiçbir bileşen teslim edilen
sisteme giremez. Tersi de geçerli — `⛔` bir kalem kodda kullanılıyorsa bu bir
**doküman–kod tutarsızlığıdır** ve jüri için lisans ihlalinden farksız görünür.
27–31 Temmuz arasında tam bu durumdaydık (Trendyol `⛔` işaretliyken
`docker-compose.yml:27`'de çalışıyordu); doğrulama bunu kapattı.

---

## Sources

- `raw/teknofest/2026-teknofest-tyda-sartname-2-senaryo.pdf` — §5.10, §8
- `../../decisions/apache-2-acik-kaynak-lisansi.md`
- `app/CLAUDE.md` §7 (lisans tuzağı), §20 (uyumluluk kontrol listesi)

## Related

- [[apache-2-acik-kaynak-lisansi]] — kararın kendisi
- [[on-premise-calistirilabilir-mimari]] — offline kısıtı, model seçimini daraltır
- [[acik-kaynak-yaklasimi]]
