# Anatolia AI — Katılım Bankacılığı Kampanya Bilgi Çıkarımı

> **TEKNOFEST 2026 — Türkçe Yapay Zekâ Dil Ajanları Yarışması (2. Senaryo)**
> Yürütücü: **Bilişim Vadisi**

**Yarışma etiketleri:** `BilisimVadisi2026` · **Türkiye Açık Kaynak Platformu**

Türkiye'deki **katılım bankalarının** (faizsiz finans) resmî sitelerindeki
kampanya/ürün metinlerinden finansal bilgileri **otomatik çıkaran**, **normalize
eden**, **sınıflandıran** ve **karşılaştıran**; sonuçları **dashboard + hibrit
chatbot** ile sunan; **tamamen açık kaynak (Apache-2.0)**, **on-premise** ve
**internetsiz (offline)** çalışabilen bir Türkçe Doğal Dil İşleme (NLP) sistemidir.

---

## 👥 Ekip — Anatolia AI

| Üye | Görev |
|---|---|
| **Mehmet Efe Aytaş** | Takım Kaptanı |
| Irmak Altay | Ekip Üyesi |
| Ayça Engindeniz | Ekip Üyesi |
| Ecegüneş Dağ | Ekip Üyesi |

---

## 🎯 Proje Tanımı

Katılım bankacılığında bilgiler doğal dilde, dağınık ve birbiriyle kıyaslanması zor
biçimde sunulur ("ilk 6 ay masrafsız", "%1,99–%2,49 arası kâr payı", "120 aya kadar
vade"). Anatolia AI bu metinleri makine tarafından okunabilir, **karşılaştırılabilir**
yapısal veriye dönüştürür:

1. **Toplama (scraping):** Banka sitelerinden kampanya metinleri (config-driven).
2. **Bilgi çıkarımı (extraction):** "Önce Kural, Sonra LLM" hibrit yaklaşımı ile
   kâr payı oranı, tutar, vade, taksit, masraf, tarih vb. alanların çıkarımı.
3. **Normalizasyon:** TR sayı/oran/para/vade/tarih formatlarının tek bir kanonik
   biçime indirgenmesi (`%1,89` → `1.89`, `1.500,00` → `1500.00`, `12 ay` → `12`).
4. **Sınıflandırma:** 8 kampanya türü (Konut/Taşıt/İhtiyaç Finansmanı, Kart,
   Alışveriş Puanı, Yeni Müşteri, Yatırım Ürünü vb.).
5. **Karşılaştırma:** Bankalar arası **adil kıyas** + **çelişki tespiti**
   ("masrafsız" denilip tahsis ücreti alınması gibi durumları yakalar).
6. **Sunum:** Next.js dashboard + router'lı **hibrit chatbot** (text-to-SQL + RAG).

Mimari kararların gerekçeleri ve teknik ayrıntı için bkz.
[`app/CLAUDE.md`](app/CLAUDE.md) ve bilgi arşivi: [`decisions/`](decisions/),
[`syntheses/`](syntheses/).

---

## 📦 (1) Bağımlılıklar (Dependencies)

Tüm bağımlılıklar **açık kaynaktır** (Apache/MIT/BSD). **Ücretli API/servis/yazılım
kullanılmaz.** Deterministik çekirdek (normalizasyon + kural çıkarımı + eval) **hiçbir
harici bağımlılık olmadan**, saf Python standart kütüphanesi ile çalışır.

- **Python bağımlılıkları:** [`app/requirements.txt`](app/requirements.txt)
  (pydantic, requests, beautifulsoup4, trafilatura, playwright, transformers,
  sentence-transformers, gliner, fastapi, uvicorn, psycopg, pgvector, zeyrek …)
- **Web (Node.js) bağımlılıkları:** [`app/web/package.json`](app/web/package.json)
  (next 14, react 18, typescript)
- **Servis orkestrasyonu:** [`app/docker-compose.yml`](app/docker-compose.yml)
  (postgres + vllm/ollama + api + web — anahtarsız, offline)

**Gereksinimler:** Python 3.11+, (opsiyonel) Node.js 18+ ve Docker.

---

## ▶️ (2) Kurulum ve Çalıştırma Adımları

### A) Sıfır bağımlılık — deterministik çekirdek (en hızlı doğrulama)

```bash
git clone https://github.com/mehmetefeaytas/anatoliaAI.git
cd anatoliaAI/app

# Birim testler (normalizasyon + kural çıkarımı)
python3 -m unittest tests.test_normalize tests.test_extract

# Tüm test paketi (54 birim/entegrasyon testi, tamamı offline)
python3 -m unittest discover -s tests

# Değerlendirme: alan bazında P/R/F1 + zor-vaka alt kümesi
python3 -m eval.run_eval --gold data/gold/gold.sample.json
```

### B) Geliştirme ortamı (tam Python bağımlılıkları)

```bash
cd app
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Uçtan uca komutlar
python -m src.scraping.run   --config config/banks.yaml          # toplama
python -m src.extraction.run --input  data/processed/sample.txt  # çıkarım
python -m eval.ablation                                          # kural vs LLM vs hibrit
```

### C) Tam sistem — Docker (offline, anahtarsız)

```bash
cd app
cp .env.example .env          # API anahtarı YOK; sadece local config
docker-compose up             # postgres + vllm/ollama + api + web
```

- Dashboard: `http://localhost:3000` · API: `http://localhost:8000`
- LLM opsiyoneldir; `LLM_BACKEND` boşsa sistem **kural-only** modda çalışır.

Ayrıntılı komut listesi: [`app/README.md`](app/README.md).

---

## 🗂️ (3) Veri Seti (Dataset)

**Herkese açık indirme bağlantısı:** _(yükleme tamamlandığında buraya eklenecektir)_

> ⚠️ **NOT:** Veri seti kamuya açık bir bağlantıya (ör. Hugging Face Datasets /
> Kaggle / Zenodo) yüklenecek ve bağlantı buraya eklenecektir. 

**Veri toplama yöntemi ve kaynağı (provenance):**

- Veri seti, **kamuya açık** katılım bankası web sitelerindeki kampanya/ürün
  metinlerinden **config-driven scraping** ile toplanır
  (bkz. [`app/config/banks.yaml`](app/config/banks.yaml)).
- Hedef banka listesi, resmî **BDDK Liste 77** (Katılım Bankaları) kaynağına
  dayanır: <https://www.bddk.org.tr/Kurulus/Liste/77>
- Scraping **etik kurallara uyar** (robots.txt, rate-limit, provenance/timestamp
  cache'i); site engellediğinde şartnamenin izin verdiği manuel toplamaya düşülür.
- Depoda çalıştırılabilirliği kanıtlayan **örnek veriler** ve **altın (gold) test
  seti örneği** bulunur:
  [`app/data/`](app/data/) · [`app/data/gold/gold.sample.json`](app/data/gold/gold.sample.json)

---

## 🏗️ Mimari (Özet)

"Önce Kural, Sonra LLM" hibrit bilgi çıkarımı:

```
scrape → clean → preprocess (TR-aware) → extract (kural → NER → LLM) → reconcile →
normalize (kanonik) → PostgreSQL → compare/rank → dashboard + hibrit chatbot
```

- **Kural/Regex (birincil, deterministik):** sayısal/yapısal alanlar.
- **GLiNER (tamamlayıcı NER) + BERTurk (8-sınıf sınıflandırma).**
- **Yerel LLM + guided_json:** yalnızca örtük/bulanık ifadeler için.
- **Halüsinasyon yasağı:** bilgi yoksa `null` + düşük güven döner; değer uydurulmaz.

Katman katman modül tablosu ve durumları için: [`app/README.md`](app/README.md).

---

## 📄 Lisans

**Apache-2.0** — bkz. [`app/LICENSE`](app/LICENSE). Yalnızca Apache/MIT/BSD lisanslı
kütüphaneler ve model ağırlıkları kullanılır.

---

## 📚 Depo Yapısı

```
├── README.md              # bu dosya (yarışma teslim özeti)
├── app/                   # UÇTAN UCA NLP ÇÖZÜMÜ (kaynak kod)
│   ├── src/               #   scraping, extraction, normalization, comparison, chatbot, api, db
│   ├── web/               #   Next.js dashboard + chatbot
│   ├── eval/              #   P/R/F1 + zor-vaka + ablasyon
│   ├── tests/             #   54 birim/entegrasyon testi (offline)
│   ├── data/              #   örnek + gold veri seti
│   ├── requirements.txt   #   Python bağımlılıkları
│   ├── docker-compose.yml #   offline servis orkestrasyonu
│   ├── LICENSE            #   Apache-2.0
│   └── CLAUDE.md          #   ayrıntılı mimari/karar dokümanı
├── decisions/ concepts/ entities/ syntheses/ sorun/   # bilgi arşivi (kararlar, kavramlar)
├── sources/ raw/          # kaynak özetleri (şartname dâhil)
└── index.md log.md        # dizin + değişiklik günlüğü
```
