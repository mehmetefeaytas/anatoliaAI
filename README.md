<div align="center">

# Anatolia AI

### Katılım Bankacılığı Kampanya Metinlerinden Finansal Bilgi Çıkarımı

**TEKNOFEST 2026 — Türkçe Yapay Zekâ Dil Ajanları Yarışması · 2. Senaryo**
Yürütücü: **Bilişim Vadisi**

[![CI](https://github.com/mehmetefeaytas/anatoliaAI/actions/workflows/ci.yml/badge.svg)](https://github.com/mehmetefeaytas/anatoliaAI/actions/workflows/ci.yml)
[![Lisans](https://img.shields.io/badge/lisans-Apache--2.0-blue.svg)](app/LICENSE)
[![Testler](https://img.shields.io/badge/testler-2943%20ye%C5%9Fil-brightgreen.svg)](app/tests/)
[![Değişmez denetimi](https://img.shields.io/badge/de%C4%9Fi%C5%9Fmez%20denetimi-1782%20belge-yellow.svg)](app/eval/properties.py)
[![On-prem](https://img.shields.io/badge/on--prem-14%2F14%20a%C4%9Fs%C4%B1z%20ad%C4%B1m-success.svg)](app/docs/OFFLINE-KANIT.md)
[![Veri seti](https://img.shields.io/badge/veri%20seti-Hugging%20Face-orange.svg)](https://huggingface.co/datasets/mehmetefeaytas/katilim-bankaciligi-kampanya-gold)
[![SBOM](https://img.shields.io/badge/SBOM-CycloneDX%20·%2096%20paket-informational.svg)](app/docs/sbom.json)

**Yarışma etiketleri:** `BilisimVadisi2026` · **Türkiye Açık Kaynak Platformu**

</div>

---

Türkiye'deki **katılım bankalarının** (faizsiz finans) resmî sitelerindeki
kampanya ve ürün metinlerinden finansal bilgileri **otomatik çıkaran**,
**normalize eden**, **sınıflandıran** ve **karşılaştıran**; sonuçları
**dashboard + hibrit chatbot** ile sunan; **tamamen açık kaynak (Apache-2.0)**,
**on-premise** ve **internetsiz** çalışabilen bir Türkçe NLP sistemi.

> **1.782 gerçek belge · 10/10 katılım bankası · 6 tarama tarihi ·
> 2.943 yeşil test · 14/14 ağsız kanıt adımı · yayımlanmış altın veri seti**

---

## 🏆 Bizi ayıran şey: ölçümün kendisi

Bu alanda yüksek bir F1 ilan etmek kolaydır. Zor olan, o sayının **ne anlama
geldiğini** ve **nerede tutmadığını** aynı sayfada söylemektir. Projeyi üç ilke
üzerine kurduk ve üçünü de **kod olarak** uyguladık — slogan değil, kapı.

<table>
<tr>
<td width="33%" valign="top">

### 1️⃣ Sayı ≠ İddia
**Yayımlanan her sayı, onu üreten kanıtla eşleşmek zorunda.**

`scripts/kanit_tazeligi.py` bu README'deki her rakamı üreten komutun
çıktısıyla karşılaştırır. Ayrışırsa **CI kırmızı yanar**.

Kapı kurulduğu gün 8 sapma buldu — kendi belgelerimizde.

</td>
<td width="33%" valign="top">

### 2️⃣ Kaçırmak ≠ Uydurmak
**Tek bir parlak yüzde vermiyoruz.**

Bir alanı kaçırmak bilgi eksikliğidir; uydurmak kullanıcıyı yanlış yönlendirir.
Bunlar aynı hata değildir ve **ayrı paydalarla** sayılır.

CI kapısı yalnız F1'e değil **halüsinasyon tavanına** da bakar.

</td>
<td width="33%" valign="top">

### 3️⃣ Açığı biz söyleriz
**Bir vitrinin en kolay yalanı, eksiği yazmamaktır.**

Bilinen açıklarımız aşağıda kendi başlığı altında duruyor — jüri bulmadan önce
biz yazıyoruz.

Ölçüp **geri adım attığımız** kararlar da öyle.

</td>
</tr>
</table>

---

## 📊 Ölçülebilir Durum

Bu tablodaki her sayı, yanındaki komutla **yeniden üretilebilir** — ve bu bir
iddia değil, **kapı**: `python -m scripts.kanit_tazeligi` her satırı üreten
kanıtla karşılaştırır, ayrışırsa CI kırmızı yanar. Ölçüm tarihi:
**15 Ağustos 2026** · ölçüm kolu: `kural` (resmî varsayılan, LLM kapalı).

| Ne | Değer | Üreten komut |
|---|---|---|
| Banka (config-driven) | **10 katılım bankası** + TKBB (şemsiye kuruluş) | `config/banks.yaml` |
| Korpus | **1.782 belge** (ham arşivle eşit) | `python -m scripts.check_demo_db` |
| AI özeti kapsaması | **1.759** üretildi · 23 belge gerekçeli boş | `python -m scripts.build_summaries --db data/demo.db --devam` |
| Gold — zor vaka seti | gold seti: `gold.v2.json` (48 kayıt), 40'ı kasten zor | `data/gold/gold.v2.json` |
| Gold — geniş örneklem | `gold.round1` \| 134 \| protokol v2, 38'i hakemlikten geçti | `data/gold/gold.round1.json` |
| **Yapılandırılmış alan mikro-F1** (gold.v2, 11 alan) | **0,671** | `python -m eval.run_eval --gold data/gold/gold.v2.json` |
| 12-alan mikro-F1 | 0,464 [%95 GA 0,398–0,522] | *(aynı komut — farkı aşağıda açıklıyoruz)* |
| makro-F1 | **0,601** | *(aynı komut)* |
| Halüsinasyon oranı | **0,047** (21/444) · yapısal kesitte 0,035 | *(aynı komut)* |
| RAG — terim kapsama R@5 | **0,867** | `python -m eval.rag_eval --db data/demo.db` |
| RAG — banka hedefleme R@5 | **0,800** (BM25 sıralama) | *(aynı komut)* |
| RAG — kaynak gösterme oranı | **1,000** | *(aynı komut)* |
| Reddetme kararı doğruluğu | **30/30 = 1,000** | *(aynı komut)* |
| Güvenlik seti | **29/30 = 0,97** · aşırı red **0/6** | `python -m src.chatbot.run_safety_eval --db data/demo.db` |
| Anotatör uyumu — round0 | Fleiss κ **0,302** · Krippendorff α 0,620 / 0,787 (hakemlik **sonrası**) | `python -m scripts.report_iaa data/gold/review/round0_kalibrasyon_{A,B,C,D}.csv --tur round0-kalibrasyon-v1` |
| Anotatör uyumu — round1 | Cohen κ **0,274** (hakemlik **öncesi**, 141 ortak karar) | `python -m scripts.report_iaa data/gold/review/round1_{A,B}.csv --tur round1` |
| Güven kalibrasyonu | ECE **0,188** · MCE 0,379 · Brier 0,201 (n=153) | `python -m eval.calibration --gold data/gold/gold.round1.json` |
| Bağımlılık envanteri | **96 paket**, CycloneDX SBOM + lisans kapısı | `make sbom lisanslar lisans-kapisi` |
| On-prem kanıtı | **14 adımın 13'ü** ağsız beklendiği gibi ([ayrıntı](#-bilinen-açıklar--biz-söylüyoruz)) | `bash scripts/offline_proof.sh` |
| Test | **2.996** toplanan · **2.943** geçti · **53** atlandı (Postgres — CI'da koşar) | `python -m scripts.test_ozeti` |
| CI regresyon kapısı | **iki taban** (gold.v2 + round1), alan F1 + halüsinasyon tavanı | `python -m eval.run_eval --gold data/gold/gold.v2.json --esikler eval/esikler.json` |
| Kanıt-tazeliği kapısı | **var** — yayımlanan sayı ile kanıt ayrışırsa CI düşer | `python -m scripts.kanit_tazeligi` |

<details>
<summary><b>📐 Ölçüm metodolojisi — dört ilke, hepsi kod olarak</b></summary>

<br>

**1) Hata tek tip değildir.** `eval/run_eval.py` her kararı dört kovaya ayırır:

| Kova | Ne demek | Neden ayrı sayılır |
|---|---|---|
| **kaçırma** | bilgi metinde var, model hiçbir şey üretmedi | bilgi eksikliği |
| **yanlış çıkarım** | bilgi metinde var, model yanlış yerden aldı | düzeltilebilir kural hatası |
| **halüsinasyon** | bilgi metinde **yok**, model uydurdu | kullanıcıyı yanlış yönlendirir — en pahalısı |
| **ATL (atlanan)** | gold bu alan hakkında karar vermemiş | metriğe **girmez**; paydayı şişirmemek için |

CI kapısı bu yüzden yalnız F1'e değil **halüsinasyon üst sınırına** da bakar
(`eval/esikler.json`): uydurma artarsa F1 yükselse bile kapı kapanır.

**2) Güven aralığı belge düzeyinde yeniden örneklenir.** Bir belgeden 12 alan
çıkar ve bu 12 gözlem **bağımsız değildir** (aynı metin, aynı banka şablonu,
aynı hata kaynağı). Alan düzeyinde örneklemek GA'yı yapay olarak daraltır —
bu bir tercih değil, istatistiksel bir hatadır. `stats.bootstrap_ci` örnekleme
birimi olarak **belgeyi** alır (küme bootstrap): belge düzeyi bootstrap 1000
örnek, tohum 42. Seed'i raporlanmayan bir GA tekrar üretilemez, dolayısıyla
kanıt değildir.

**3) Karşılaştırmalar McNemar ile yapılır.** İki yapılandırma aynı belgelerde
koşulduğu için eşleştirilmiş test gerekir. Sonucu şudur: **hibrit yapı kural
katmanını geçemedi** — 0,575 < 0,612, p = 0,0117, ve halüsinasyon oranı kural
katmanının %60 üstünde. Projenin kendi iç kılavuzu bu tablodan "hibridin
kazandığının kanıtlanmasını" istiyordu; kanıtlanmadı, **tersi ölçüldü**. Rapor
sonucu düzeltmeye çalışmıyor, ölçüldüğü gibi bırakıyor.

**4) Anotasyon uyumu, önceden ilan edilmiş eşikle.** Round0: 4 anotatör, 260
ortak satır, 0 boş hücre → Fleiss κ **0,302**. Round1: 2 anotatör, 141 ortak
karar → Cohen κ **0,274**. Eşik anotasyon **başlamadan** ilan edilmişti
(`ANNOTATION_GUIDE.md` §7) ve ilan edilen sonuç uygulandı: κ < 0,67 → zorunlu
hakemlik + kılavuz revizyonu. **Sayıya bakıp eşiği değiştirmek yasaktır.**

⚠️ **İki κ simetrik değil ve bunu yazmak zorundayız:** round0'ın 0,302'si
**hakemlik sonrası** bir durumdur (yedekler 0,051 → 0,268 → 0,302 ilerlemesini
gösteriyor), round1'in 0,274'ü ise **hakemlik öncesidir**. İkisini yan yana
koyup "uyum düzeliyor" demek, ölçtüğümüz şeyi ölçmediğimizi söylemek olurdu.

</details>

<details>
<summary><b>🔍 İki gold seti, iki farklı soru — ve neden birleştirmiyoruz</b></summary>

<br>

`gold.v2` (n=48) **kasten zor** seçilmiş bir settir: 40 kaydı koşullu aralık,
format varyantı, çelişki ya da terminoloji tuzağı taşır. `gold.round1` (n=134)
inceleme kuyruğundan gelen **geniş** bir örneklemdir. İkisi aynı sistemi ölçer
ama aynı soruyu sormaz, bu yüzden **manşet sayı gold.v2'dir** — zor olan.

| | gold.v2 | gold.round1 |
|---|---:|---:|
| kayıt | 48 | 134 |
| zor vaka | 40 | 3 |
| `absent` kararı (halüsinasyon paydası) | **444** | **60** |
| 12-alan mikro-F1 | 0,464 | 0,744 |
| halüsinasyon | **0,047** | **0,433** |

**Round1'in 0,433'ü bir gerileme değil, seçim etkisidir** ve bunu gizlemiyoruz:
round1'de bir hücre inceleme kuyruğuna **zaten model bir şey ürettiği için**
giriyor. Yani o setin `absent` kümesi rastgele değil, düşmanca seçilmiş bir alt
kümedir; payda 60'a düşünce oran şişer.

Aynı sebeple **halüsinasyon tavanı `gold.v2`'de kalıyor**: kapıyı round1'e
taşımak, önceden ilan edilmiş 0,08'lik tavanı sayıya bakarak gevşetmek olurdu.
Round1 kendi tabanında **ikinci bir kapı** olarak koşar
(`eval/esikler-round1.json`).

</details>

<details>
<summary><b>📏 İki mikro-F1 neden farklı — ve neden ikisini de veriyoruz</b></summary>

<br>

`kampanya_kosullari` **serbest cümle listesi** döndüren bir alandır ("Kampanyaya
dahil olmak için X gerekir"). Span/jeton eşleşmesiyle F1 ölçmek bu alanda
metodolojik olarak yanlıştır: aynı koşulu farklı sözcüklerle yazan iki anotatör
bile birbirini "yanlış" bulurdu. Bu tek alan mikro-F1'i **0,671'den 0,464'e**
çekiyor.

Alanı **gizlemiyoruz**: ana tabloda satırı duruyor, değerlendirme raporunda
kendi bölümünde **kalem düzeyi ölçütle** (jeton-Jaccard ≥ 0,70) raporlanıyor ve
iki sayı yan yana yayımlanıyor. Eşik duyarlılığı da basılıyor — ve ölçüldü ki
sonuç eşikten bağımsız: 0,6/0,7/0,8'in üçünde de aynı sayı çıkıyor, yani bu
korpusta sınır vaka yok. **Eşiğin sonucu taşımadığını söylemek, taşıdığını
söylemek kadar raporlanmaya değer.**

</details>

<details>
<summary><b>🎯 RAG Recall@5 burada ne demek</b></summary>

<br>

Klasik bilgi erişiminde bir sorgunun "ilgili belge kümesi" bilinir; bizde
bilinmiyor. Bu yüzden ölçülen şey **kanıtlanabilir isabet**: ilk 5 sonuç
arasında şartı sağlayan (terimi gerçekten içeren / doğru bankaya ait) en az bir
belge var mı. Tanım `eval/rag_eval.py` başlığında yazılıdır ve başka bir
sistemin Recall@5'iyle **doğrudan kıyaslanamaz**. Bunu biz söylüyoruz.

</details>

---

## ⚠️ Bilinen açıklar — biz söylüyoruz

Bir vitrin tablosunun en kolay yalanı, eksiği yazmamaktır. Ölçüm sırasında çıkan
ve **henüz kapatılmamış** açıklar:

| Açık | Durum | Neden gizlemiyoruz |
|---|---|---|
| **İnsan hakemliği yok** | 🟠 Gold setleri makine anotatörlü; `gold.round1`'de 38 kayıt **makine kör hakemliğinden** geçti | `adjudicated: true` "hakemlikten geçti" der, "insan onayladı" demez |
| **On-prem kanıtı 14/14 değil** | 🟠 13 adım beklendiği gibi; **Adım 4** (imaj içi test paketi) kırmızı | Sebep ölçüldü: konteynerde `git`/`httpx2` yok, kod bozuk değil — ama düzeltilene kadar ✅ demiyoruz |
| **Tam yığın ağsız denenmedi** | 🟠 Kanıt yalnız **API konteynerini** kapsıyor; `docker compose up` tam yığını (Postgres, web, LLM) ağsız sınanmadı | "İnternetsiz çalışır" iddiası **önceden derlenmiş imajlarla** doğrudur |
| **`tahsis_ucreti` ölçülemiyor** | 🟠 Gold'da 0 pozitif örnek (47 kayıtta `absent`) | Bu "hiç çalışmıyor" değil, **"ölçülemiyor"** demektir — ikisi farklı |
| **`kar_payi_orani` seyrek** | 🟠 Korpusun **70/1.782** belgesinde (%3,9) | Model kısıtı değil **veri gerçeği**: bankalar oranı HTML'de değil hesaplama ucunda veriyor. Ayrıca bu 70 kaydın 26'sında `raw_value` boş — "her değer bir aralığa bağlı" iddiası bu alanın %37'sinde tutmuyor |
| **Korpusta çoğaltılmış kaynak** | 🔴 Albaraka sağlık kampanyası aynı `source_url` altında 3 dosya | `check_demo_db` bunu raporlar ve **bilerek kırmızı kalır**: `raw/` değişmez olduğu için düzeltmesi bir korpus politikası kararıdır |

**Ölçüp geri adım attığımız kararlar** da aynı dürüstlükle duruyor:

- **LLM orkestrasyonu reddedildi.** Yetki-kısıtlı çok-ajanlı çıkarım yazıldı,
  ölçüldü ve kabul kapısından **geçemedi** (McNemar p = 0,0391, kazanan kural
  katmanı). Üretime alınmadı ve bu karar `tests/test_orchestrator.py` ile
  **testle kilitlendi**.
- **Oransal ücret türetmesi kaldırıldı.** Belgenin başka bir yerindeki tutarla
  çarpmak çıkarım değil **türetmedir**; 6 belgede metinde hiç geçmeyen bir TL
  değeri üretiyordu — birinde taban finansman tutarı bile değil bir vade eşiğiydi.
- **BERTurk ince ayarı yapıldı, kullanılmadı.** Ölçüldü, kabul kapısını
  geçemedi, teslim edilen sistemde yok — ve bunu mimari belgesi açıkça yazıyor.

---

## 💡 Yenilikçi Yönler

<table>
<tr><td width="50%" valign="top">

**🔎 Alan bazlı güven skoru + kaynak vurgulama**

Her çıkarılan değer `confidence` + `source_span` taşır; arayüz kanıtı belgede
**vurgular**. `verify_span()` ile `text[start:end] == raw_value` kendi kendini
denetler.

Skor kalibre **edildi ve ölçüldü** (ECE 0,188) — kalibre edilmemiş bir skora
eşik koymak, eşiğin ne attığını bilmemektir.

</td><td width="50%" valign="top">

**⚖️ Bankalar arası çelişki tespiti**

"Masrafsız" diyen bir kampanyanın ücret tarifesinde tahsis ücreti alması gibi
**belgeler arası** çelişkileri yakalar (`src/comparison/contradiction.py`).

Kıyas motoru ayrıca **adil kıyas garantisi** uygular: yalnız aynı birime
normalize edilmiş alanlar kıyaslanır; koşullar farklıysa "doğrudan
kıyaslanamaz" işaretlenir, uydurma sıralama yapılmaz.

</td></tr>
<tr><td width="50%" valign="top">

**🏦 Config-driven banka onboarding**

Yeni banka eklemek = `config/banks.yaml` içine **tek blok**. Statik/JS/manuel
toplama modları, sitemap keşfi ve detay süzgeçleri hep config'ten okunur.

10/10 katılım bankası bu yolla toplanıyor.

</td><td width="50%" valign="top">

**🧪 Kanıt-tazeliği kapısı**

Yayımlanan her sayıyı üreten kanıtla karşılaştıran bir CI kapısı. İki ayrı
denetim yapar: **değer** (belgedeki sayı = kanıttaki sayı) ve **tazelik**
(kanıt güncel girdilerden mi üretilmiş).

İkincisi olmadan birincisi kendini kandırır: bayat bir rapordan okunan bayat
bir sayı, bayat bir README ile mükemmel uyum gösterir.

</td></tr>
</table>

---

## 🎯 Proje Tanımı

Katılım bankacılığında bilgiler doğal dilde, dağınık ve birbiriyle kıyaslanması
zor biçimde sunulur ("ilk 6 ay masrafsız", "%1,99–%2,49 arası kâr payı", "120
aya kadar vade"). Anatolia AI bu metinleri makine tarafından okunabilir,
**karşılaştırılabilir** yapısal veriye dönüştürür:

| # | Aşama | Ne yapar |
|---|---|---|
| 1 | **Toplama** | Banka sitelerinden kampanya metinleri (config-driven, robots.txt uyumlu, provenance'lı) |
| 2 | **Bilgi çıkarımı** | "Önce Kural, Sonra LLM" hibrit yaklaşımı: kâr payı oranı, tutar, vade, taksit, masraf, tarih… |
| 3 | **Normalizasyon** | TR sayı/oran/para/vade/tarih biçimleri tek kanonik biçime (`%1,89` → `1.89`, `1.500,00` → `1500.00`, `12 ay` → `12`) |
| 4 | **Sınıflandırma** | 8 kampanya türü (Konut/Taşıt/İhtiyaç Finansmanı, Kart, Alışveriş Puanı, Yeni Müşteri, Yatırım Ürünü, Finansman) |
| 5 | **Karşılaştırma** | Bankalar arası **adil kıyas** + **çelişki tespiti** |
| 6 | **Sunum** | Next.js dashboard + router'lı **hibrit chatbot** (text-to-SQL + RAG) |

### 🏗️ Mimari

```
                    ┌──────────────────────────────────────────┐
  banka siteleri ──▶│  scrape (config-driven) → clean → TR ön  │
                    │  işleme                                   │
                    └────────────────────┬─────────────────────┘
                                         ▼
                    ┌──────────────────────────────────────────┐
                    │  ÇIKARIM — "önce kural, sonra LLM"        │
                    │  ① kural/regex  (birincil, deterministik) │
                    │  ② LLM + guided_json (yalnız boşluklar)   │
                    │  → reconcile: kural kazanır, LLM doldurur │
                    └────────────────────┬─────────────────────┘
                                         ▼
   normalize (kanonik) ──▶ PostgreSQL/SQLite ──▶ compare & rank
                                         │
                          ┌──────────────┴──────────────┐
                          ▼                             ▼
                    Next.js dashboard          hibrit chatbot
                    (kanıt vurgulamalı)     (router: SQL │ RAG)
```

- **Kural/Regex (birincil, deterministik):** sayısal ve yapısal alanlar.
- **Yerel LLM + `guided_json`:** yalnızca örtük/bulanık ifadeler için; serbest
  metin **asla** parse edilmez.
- **Halüsinasyon yasağı:** bilgi yoksa `null` + düşük güven döner, değer
  uydurulmaz. Bu bir temenni değil, `eval/properties.py` ve CI kapısıyla
  denetlenen bir değişmezdir.

> **Dürüst mimari notu:** planlanan üçüncü katman (NER) **teslim edilmedi**.
> GLiNER projeye hiç girmedi; BERTurk eğitildi, ölçüldü ve kabul kapısını
> geçemedi. Teslim edilen sistem **iki katmandır** ve belgeler bunu gizlemiyor
> (`src/extraction/reconcile.py` modül başlığı).

---

## 📦 (1) Bağımlılıklar

Tüm bağımlılıklar **açık kaynaktır** (Apache/MIT/BSD). **Ücretli
API/servis/yazılım kullanılmaz.** Deterministik çekirdek (normalizasyon + kural
çıkarımı + değerlendirme) **hiçbir harici bağımlılık olmadan**, saf Python
standart kütüphanesiyle çalışır.

| Katman | Dosya | Not |
|---|---|---|
| Python (geliştirme) | [`app/requirements.txt`](app/requirements.txt) | pydantic, requests, beautifulsoup4, playwright, transformers, fastapi, psycopg, zeyrek … |
| Python (teslim imajı) | [`app/requirements-api.txt`](app/requirements-api.txt) | çalışma zamanı için gereken asgari küme |
| Web (Node.js) | [`app/web/package.json`](app/web/package.json) | next 14, react 18, typescript |
| Servis orkestrasyonu | [`app/docker-compose.yml`](app/docker-compose.yml) | postgres + vllm/ollama + api + web — **anahtarsız, offline** |

**Makine-okur envanter:** [`app/docs/sbom.json`](app/docs/sbom.json) (CycloneDX
1.6, **96 paket** — geçişli bağımlılıklar dâhil) ve insan-okur
[`app/docs/LISANSLAR.md`](app/docs/LISANSLAR.md). CI'da bir **lisans kapısı**
koşar: izin listesi dışı ya da `UNKNOWN` lisanslı bir paket girerse build düşer.
Muafiyet mümkündür ama **gerekçesiz muafiyet kabul edilmez**
(`config/lisans_istisnalari.yaml`).

**Model ağırlıkları:** yalnızca Apache-2.0/MIT. Gemma ve Llama community
license altındaki ağırlıklar **bilinçli olarak reddedilmiştir**; `base_model`
zinciri köke kadar izlenmiştir ([`app/NOTICE`](app/NOTICE),
[`model-license-audit.md`](app/docs/model-license-audit.md)).

**Gereksinimler:** Python 3.11+, (opsiyonel) Node.js 18+ ve Docker.

---

## ▶️ (2) Kurulum ve Çalıştırma

### A) Sıfır bağımlılık — deterministik çekirdek (en hızlı doğrulama)

> ⚠️ **Python 3.11+ gerekir** (`python3 -V`). Kod `zip(..., strict=)` gibi
> 3.10+ sözdizimi kullanıyor; macOS'un sistemle gelen `python3`'ü 3.9'dur.

```bash
git clone https://github.com/mehmetefeaytas/anatoliaAI.git
cd anatoliaAI/app

# Birim testler (normalizasyon + kural çıkarımı) — hiçbir kurulum gerekmez
python3 -m unittest tests.test_normalize tests.test_extract

# Tüm test paketi — temiz ağaçta ölçüldü (15 Ağu): 2.943 geçti, 53 atlandı.
# Atlananlar isteğe bağlı bağımlılık isteyenlerdir (Postgres, FastAPI, model
# indirmesi); çekirdek hiçbirine bağlı değildir ve tamamı offline koşar.
python3 -m unittest discover -s tests

# Değerlendirme: alan bazında P/R/F1 + zor-vaka alt kümesi
python3 -m eval.run_eval --gold data/gold/gold.sample.json
```

### B) Geliştirme ortamı (tam Python bağımlılıkları)

```bash
cd app && pip install -r requirements.txt
python -m playwright install chromium     # yalnız YENİ veri toplarken gerekir

python -m src.scraping.run --config config/banks.yaml
python -m src.extraction.run --input data/processed/sample.txt
python -m eval.run_eval --gold data/gold/gold.v2.json --esikler eval/esikler.json
```

### C) Tam sistem — Docker (offline, anahtarsız)

```bash
cd app
cp .env.example .env          # API anahtarı YOK; sadece yerel config
docker-compose up             # postgres + vllm/ollama + api + web
```

- Dashboard: `http://localhost:3000` · API: `http://localhost:8000`
- LLM **opsiyoneldir**; `LLM_BACKEND` boşsa sistem **kural-only** modda çalışır
  ve tüm alanlar yine çıkarılır.

### D) Denetim komutları (tek satır)

```bash
make lisanslar sbom lisans-kapisi   # bağımlılık envanteri + lisans kapısı
make veri-seti                       # yayına hazır veri seti paketi
python -m scripts.kanit_tazeligi     # yayımlanan sayı ↔ kanıt denetimi
bash scripts/offline_proof.sh        # 14 adımlık ağsız on-prem kanıtı
```

Ayrıntılı komut listesi: [`app/README.md`](app/README.md).

---

## 🗂️ (3) Veri Seti

<div align="center">

### 📥 [huggingface.co/datasets/mehmetefeaytas/katilim-bankaciligi-kampanya-gold](https://huggingface.co/datasets/mehmetefeaytas/katilim-bankaciligi-kampanya-gold)

</div>

```python
from datasets import load_dataset
ds = load_dataset("mehmetefeaytas/katilim-bankaciligi-kampanya-gold")
# train / validation / test  —  sızıntısız, belge düzeyinde bölünmüş
```

| Dosya | Kayıt | Ne |
|---|---:|---|
| `gold.round1.jsonl` | 134 | inceleme kuyruğundan gelen **geniş** örneklem |
| `gold.v2.jsonl` | 48 | kasten **zor** seçilmiş küçük set |
| `train / val / test` | 127 / 27 / 28 | iki setin birleşimi, **belge düzeyinde** bölme |

**Sızıntı denetimi: 0 ihlal.** Ve bu risk teorik değildi — ölçüldü: iki gold
seti **5 `source_url` paylaşıyor** (aynı belge, iki hasat arasında değişmiş).
Naif kayıt düzeyi bölme tam oradan sızardı: neredeyse aynı metin hem eğitimde
hem testte. Bölme bu yüzden **birleşim-bul** ile belge düzeyinde yapılır ve
denetim `tests/test_veri_seti_paketle.py` ile çitlenmiştir.

⚠️ **İki gold seti tek küme gibi raporlanmaz.** Her kayıt `kaynak_set` alanı
taşır (`gold.round1` / `gold.v2`) — bu bilgi örtük bırakılmadı, çünkü iki set
kıyaslanamaz ve karıştırmayı önleyen bilgi açık olmalı.

**Veri seti kartı** alan şemasını, protokolü, κ değerlerini (iki turu ayırarak),
"insan hakemliği yapılmadı" uyarısını ve kullanım sınırlarını taşır. Kartın her
sayısı veriden **hesaplanır** — elle yazılmış tek bir rakam yoktur — ve
dürüstlük uyarıları testle korunur: biri düşerse test kırılır.

**Yeniden üretim:**

```bash
make veri-seti           # paketi gold'dan tek komutla üretir
make veri-seti-yukle     # KURU koşu: ne yükleneceğini sha256 ile listeler
```

### Veri toplama yöntemi ve kökeni (provenance)

- Veri **kamuya açık** katılım bankası sitelerinden **config-driven scraping**
  ile toplanır ([`app/config/banks.yaml`](app/config/banks.yaml)).
- Banka listesi resmî **BDDK Liste 77**'ye dayanır:
  <https://www.bddk.org.tr/Kurulus/Liste/77>
- Scraping **etik kurallara uyar**: robots.txt, domain başına rate-limit,
  açıklayıcı User-Agent, provenance/timestamp cache'i. Site engellediğinde
  şartnamenin izin verdiği manuel toplamaya düşülür ve bu **dokümana yazılır**.
- **Ham HTML yayımlanmaz** — pakete çıkarılmış metin ve provenance alanları
  (`source_url`, `content_hash`) girer; "bu bilgiyi nereden aldınız" sorusunu
  cevaplamaya yeter.
- Gold'un kaynağı ham arşive kadar izlenir ve bu bir **CI kapısıdır**
  (`scripts/kanit_zinciri`): kaynağı gösterilemeyen tek bir kayıt build'i düşürür.

---

## 📋 Şartname Uyumu

Madde madde uyum matrisi: **[`app/docs/SARTNAME-UYUM.md`](app/docs/SARTNAME-UYUM.md)**

Her kalem ✅ / 🟠 / ❌ olarak işaretli ve **✅ yazan her satırın kanıt sütununda
çalışan bir komut ya da var olan bir dosya var**. Doğrulayamadığımız hiçbir
kaleme ✅ vermedik — kanıtsız bir ✅, yakalandığında tüm matrisi değersizleştirir.

---

## 📄 Lisans

**Apache-2.0** — [`app/LICENSE`](app/LICENSE). Yalnızca Apache/MIT/BSD lisanslı
kütüphaneler ve model ağırlıkları kullanılır; uyum bir **CI kapısıyla**
denetlenir.

---

## 📚 Depo Yapısı

```
├── README.md                    # bu dosya (yarışma teslim özeti)
├── app/                         # UÇTAN UCA NLP ÇÖZÜMÜ
│   ├── src/                     #   scraping · extraction · normalization
│   │                            #   comparison · rag · chatbot · api · db
│   ├── web/                     #   Next.js dashboard + chatbot arayüzü
│   ├── eval/                    #   P/R/F1 · zor-vaka · ablasyon · kalibrasyon
│   ├── tests/                   #   2.996 birim/entegrasyon testi (offline)
│   ├── scripts/                 #   ölçüm, denetim ve yayın araçları
│   ├── data/gold/               #   altın setler + anotasyon kılavuzu
│   ├── docs/                    #   SBOM · lisans envanteri · offline kanıt
│   │                            #   şartname uyum matrisi · teknik rapor
│   ├── Makefile                 #   make lisanslar / sbom / veri-seti
│   ├── docker-compose.yml       #   offline servis orkestrasyonu
│   └── CLAUDE.md                #   ayrıntılı mimari/karar dokümanı
├── decisions/ concepts/ entities/ syntheses/ sorun/   # bilgi arşivi
└── index.md log.md              # dizin + değişiklik günlüğü
```

**Kaynaklar** — [ablasyon raporu](app/docs/rapor/ablasyon.md) ·
[IAA raporu — round0 v1](app/data/gold/iaa-raporu-round0-kalibrasyon-v1.md) ·
[IAA raporu — round1](app/data/gold/iaa_report_round1.md) ·
[şartname uyum matrisi](app/docs/SARTNAME-UYUM.md) ·
[lisans envanteri](app/docs/LISANSLAR.md) ·
[on-prem kanıt paketi](app/docs/OFFLINE-KANIT.md) ·
[anotasyon kılavuzu](app/data/gold/ANNOTATION_GUIDE.md) ·
[tam teknik rapor](app/docs/rapor/anatolia-ai-teknik-rapor.md)

---

<div align="center">

## 👥 Ekip — Anatolia AI

| Üye | Görev |
|---|---|
| **Mehmet Efe Aytaş** | Takım Kaptanı |
| Irmak Altay | Ekip Üyesi |
| Ayça Engindeniz | Ekip Üyesi |
| Ecegüneş Dağ | Ekip Üyesi |

<br>

*Tek bir parlak yüzde vermiyoruz — çünkü bir alanı kaçırmak ile uydurmak
aynı hata değildir.*

</div>
