---
title: "Lint Raporu"
tags: [lint, rapor]
date: 2026-08-21
status: stable
---

# Lint Raporu — 2026-08-21

Tam denetim (mekanik + semantik). **Düzeltme yapılmamıştır**, yalnızca bulgular
raporlanmıştır (CLAUDE.md Lint workflow kuralı gereği). Bir önceki rapor
2026-06-16 tarihliydi ve 37 sayfalık vault'u tarıyordu; bu rapor onu tümüyle
değiştirir.

**Kapsam.** Taranan dizinler: `entities/ concepts/ decisions/ sorun/ syntheses/
sources/ archive/`. Kapsam dışı: `app/`, `raw/`, `docs-ekran/`, `colab/`, kök
`_*.md` çalışma notları, `README.md`, `CLAUDE.md`, `AGENTS.md`. `index.md` ve
`log.md` sayfa değil, ayrı raporlanır.

---

## Özet tablo

| Metrik | Değer |
|---|---|
| Toplam içerik sayfası | **59** |
| Toplam giden wikilink (sayfa içi) | 498 |
| **Kırık wikilink** | **0** |
| Orphan (hiçbir sayfadan link almayan) | **6** |
| Orphan (index.md linki de sayılınca) | **4** |
| `status: taslak` sayfa | **3** |
| Frontmatter'ı eksik sayfa | 1 |
| Duplicate title | 0 |
| Dizine (`index.md`) alınmamış sayfa | 4 |
| Sink (giden linki olmayan) sayfa | 1 |

### Dizin bazında sayfa dağılımı

| Dizin | Sayfa |
|---|---|
| `decisions/` | 16 |
| `concepts/` | 14 |
| `entities/` | 11 |
| `sorun/` | 8 |
| `sources/` | 6 (`docs` 3 · `mentor` 1 · `tcmb` 1 · `teknofest` 1) |
| `syntheses/` | 3 |
| `archive/` | 1 |
| **Toplam** | **59** |

### Status dağılımı

| Status | Sayfa |
|---|---|
| `stable` | 54 |
| `taslak` | 3 |
| `celiskili` | 1 |
| _(frontmatter yok)_ | 1 |

---

## 1. Kırık wikilinkler — **0** ✅

Vault içindeki 498 sayfa-içi wikilink'in **tamamı** mevcut bir `.md` hedefine
çözümleniyor (`sources/` alt dizinleri, `#başlık` çıpaları ve `|görünen ad`
biçimleri dahil).

**Bugünkü düzeltme doğrulandı.** 2026-08-21 ingest girişinde bildirilen
72 kırık link indirimi (`2026-08-05-ablasyon` 23, `2026-08-03-anatolia-ai-teknik-rapor`
23, `2026-07-31-offline-kanit` 26) gerçekten uygulanmış; üç sayfa da
`status: taslak`. Kalan kırık link **yok**.

**Yok sayılanlar (kırık değil):**

- `CLAUDE.md` ve `AGENTS.md` içindeki 4'er format örneği placeholder'ı
  (`[[YYYY-MM-DD-slug]]` ×2, `[[diger-sayfa]]`, `[[wikilink]]`). Sayfa metni
  değil, şablon örneği.
- `log.md` içindeki 9 wikilink — günlük kaydı, sayfa metni değil. **Hepsi
  geçerli hedefe çözümleniyor**, kırık yok.
- `index.md` içindeki tüm wikilinkler geçerli, kırık yok.

---

## 2. Orphan sayfalar — 6 (index sayılınca 4)

### 2a. Hiçbir içerik sayfasından ve index.md'den link almayanlar (4) — gerçek orphan

| Sayfa | Not |
|---|---|
| `archive/_plan-rakip-ustunluk.md` | Frontmatter'sız, hem orphan hem sink hem dizin dışı. Bkz. §4. |
| `sources/docs/2026-07-31-offline-kanit.md` | Yarım ingest, `taslak` |
| `sources/docs/2026-08-03-anatolia-ai-teknik-rapor.md` | Yarım ingest, `taslak` |
| `sources/docs/2026-08-05-ablasyon.md` | Yarım ingest, `taslak` |

Üç `sources/docs` sayfası **bilerek** dizine alınmadı (index.md'deki not, hard
rule #3). Ama bu durum artık kalıcılaştı: sayfalar 16–21 gün önce yazıldı, hâlâ
hiçbir türev sayfası yok ve içerdikleri ölçümler karar sayfalarına akmadı
(bkz. §6.1 — bu, raporun en ciddi bulgusu).

### 2b. Yalnızca `index.md`'den link alanlar (2) — içerik sayfası bağı yok

| Sayfa | Not |
|---|---|
| `sorun/gold-round1-csvden-yeniden-uretilemiyor.md` | Bugün "ÇÖZÜLDÜ" olarak yazıldı; hiçbir `decisions/` veya `entities/veri-seti` sayfasından atıf yok |
| `sources/tcmb/2026-08-07-terimler-sozlugu.md` | **Kaynak sayfası, tek yönlü.** `concepts/katilim-finans-terimleri.md` ondan türemesine rağmen ona link vermiyor → hard rule #6 (çift yönlü bağ) ihlali |

---

## 3. Bugün eklenen 4 sayfanın doğrulaması — ✅ tümü geçti

| Sayfa | index.md'de | Çift yönlü bağ |
|---|---|---|
| `decisions/juri-sunumu-bes-slayt` | ✅ | ✅ üç sorun sayfasına link veriyor, üçünden de link alıyor |
| `sorun/turkce-buyuk-harf-yerel-duyarliligi` | ✅ | ✅ karar ↔ sorun |
| `sorun/sunum-slayt-sigdirma-olcek-cokusu` | ✅ | ✅ karar ↔ sorun |
| `sorun/next-dev-proxy-econnreset-yanlis-alarmi` | ✅ | ✅ karar ↔ sorun |

Dördü de tam frontmatter'lı (`title`/`tags`/`date`/`status`), `date: 2026-08-21`,
`status: stable`.

**Küçük eksik:** dört sayfa da yalnız kendi aralarında bağlı — dış vault'a
(ör. `syntheses/teslim-ve-degerlendirme-rehberi`, `entities/dashboard`,
`entities/chatbot`) bağ kurmuyorlar. Sunum kararı şartname §10'a dayandığı halde
`[[teslim-ve-degerlendirme-rehberi]]`'ne link yok, o sayfa da yeni karardan
haberdar değil.

---

## 4. Frontmatter ve biçim

- **`archive/_plan-rakip-ustunluk.md` — frontmatter'ı tamamen yok** (`title`,
  `tags`, `date`, `status` dördü de eksik). CLAUDE.md'ye göre arşive taşınan
  sayfa `status: arsiv` almalıydı. Ayrıca kök çalışma notu adlandırması (`_`
  öneki) korunmuş; vault sayfası olarak kebab-case bekleniyor.
- Diğer 58 sayfada frontmatter tam.
- Duplicate title yok.
- Tüm dosya adları kebab-case ve Türkçe-sadeleştirilmiş — `_plan-rakip-ustunluk`
  dışında ihlal yok.

---

## 5. index.md ve log.md senkronu

### log.md — ✅ kronoloji doğru

En yeni en üstte kuralı tutuyor: `2026-08-21` ×4 → `2026-08-10` → `2026-08-07`
×3 → `2026-08-06` → `2026-08-05` → `2026-07-27` ×3 → `2026-06-16` ×3. Bugünkü
kronoloji onarımı doğrulandı. Kırık link yok.

### index.md — 3 drift noktası

1. **`## Archive` bölümü "_(arşivlenmiş sayfa yok)_" diyor** ama
   `archive/_plan-rakip-ustunluk.md` mevcut. **Yanlış beyan.**
2. **Yarım-ingest notu bayatladı.** Not şöyle diyor: *"o sayfalardan çıkan
   wikilink'ler kırık"*. Bu bugün itibarıyla **artık doğru değil** — linkler düz
   metne indirildi, kırık link 0. Not güncellenmeli.
3. Aynı not "~45 türev sayfa" diyor; bu sayı doğrulanmadı, bir tahmin olarak
   işaretlenmeli veya kaldırılmalı.

Bunlar dışında index.md ↔ disk senkronu tam: 59 sayfanın 55'i dizinde, dizinde
olup diskte olmayan sayfa yok.

---

## 6. Semantik bulgular

### 6.1. ⚠️ İşaretlenmemiş çelişki: ablasyon ölçümü vs çıkarım kararı — **YÜKSEK ÖNCELİK**

- `decisions/ner-fine-tune-yerine-kural-few-shot.md` (2026-06-16, **`status: stable`**)
  alan çıkarımını *"kural + few-shot LLM"* ile yapmaya karar veriyor.
- `sources/docs/2026-08-05-ablasyon.md` (2026-08-05) bunu ölçtü ve **tersini
  buldu**: `kural` 10-1 ile `hibrit`i yeniyor (tam binom p = 0,01172), `hibrit`
  +1 TP kazanıp +11 FP kaybediyor. Sayfa başlığı zaten "**hibrit KAYBETTİ**".

**Sorun:** Karar sayfası hâlâ `stable`, hiçbir `## ÇELİŞKİ` başlığı veya
güncelleme notu yok, ölçüme atıf yok. Karşı yönde de bağ yok. Hard rule #4
(çelişki işaretlenir) ve #6 (çift yönlü bağ) ihlali. 16 gündür ölçülmüş bir
sonuç karar katmanına hiç ulaşmamış — vault şu an teslim edilecek varsayılan
konfigürasyon hakkında **iki farklı şey söylüyor**.

### 6.2. ⚠️ Terim çakışması: "hibrit" iki farklı şeyi anlatıyor

- `decisions/hibrit-chatbot-text-to-sql-rag.md` → **chatbot yönlendirme** hibriti
  (text-to-SQL + RAG). Geçerli.
- `sources/docs/2026-08-05-ablasyon.md` → **alan çıkarımı** hibriti
  (kural + LLM). Ölçümde kaybetti.

İkisi de vault'ta yalın "hibrit" diye geçiyor. Bir okuyucunun (veya jürinin)
"hibrit kaybetti" ifadesini chatbot mimarisine yayması çok kolay. Ayrıştırıcı
adlandırma gerekiyor ("çıkarım-hibriti" / "sorgu-hibriti").

### 6.3. `status: celiskili` sayfası hâlâ gerekçeli mi? — ✅ evet

`syntheses/teslim-ve-degerlendirme-rehberi.md` tek `celiskili` sayfa. Çelişki
(demo videosu s.14 "maks. 5 dk" ↔ s.19 "1 dk") **hâlâ açık**: her iki taraf
sayfa referansıyla yazılı, olası yorum ve geçici karar ("hem ≤5 dk hem 1 dk
hazırla") mevcut. Gizlenmemiş, silinmemiş. Statü doğru.

**Ancak:** çözüm koşulu olarak *"yarışma sırasında gönderilecek bilgilendirme
maili"* bekleniyor. Bugün 2026-08-21, çevrimiçi süreç bitişi 26 Ağustos, final
27–28 Ağustos. Bu çelişkinin **5 gün içinde** kapanması veya "her iki formatta da
hazırız" diye kesinleşmesi gerekiyor. Ayrıca bugünkü
`decisions/juri-sunumu-bes-slayt` (§10, 4 dk) bu sayfayla aynı konuyu işliyor
ama iki sayfa birbirini görmüyor (bkz. §3).

### 6.4. Bayat iddialar — korpus büyüklüğü 5 farklı değerle geçiyor

**Yerdeki gerçek (bugün ölçüldü):** `app/data/demo.db` → `campaigns` **2.708**
satır, `banks` 11, `extracted_fields` 7.022.

| İddia | Nerede | Durum |
|---|---|---|
| **2.708 belge** | `decisions/juri-sunumu-bes-slayt.md:28` | ✅ **güncel** — DB ile birebir |
| **1.774 belge** | `sources/docs/2026-07-31-offline-kanit.md:237` | ⚠️ bayat |
| **1.782 belge** | `archive/_plan-rakip-ustunluk.md:404,407` | ⚠️ bayat (arşiv sayfası, düşük öncelik) |
| **1759 belge** | `decisions/klasik-veri-ince-ayar-rag-reddi.md:14,24` · `entities/klasik-banka-korpusu.md:72` | ⚠️ bayat — **`stable` statülü karar/entity sayfasında** |
| **849 belge** | `sources/docs/2026-08-03-anatolia-ai-teknik-rapor.md:47,53,87,121,137` · `2026-07-31-offline-kanit.md:89` | ⚠️ bayat |

Ek olarak `2026-07-31-offline-kanit.md:159` "1696 belge çıkarımı" (tepe RSS
ölçümü) ve `:161` "21 087 belge/dakika" — ölçüm anına ait sayılar, bayat
sayılmaz ama korpus büyüklüğüyle karıştırılmamalı.

**En kritik olan `1759`:** iki `status: stable` sayfada geçiyor
(`klasik-veri-ince-ayar-rag-reddi`, `klasik-banka-korpusu`) ve orada
*"yarışma korpusu"* / *"katılım korpusu"* diye adlandırılıyor. Yani vault'un
`stable` katmanı yarışma korpusunu 1759 sanıyor, gerçek 2.708. `724 belge`
(klasik banka korpusu) ayrı bir kümedir, kapsam dışıdır — doğrulanmadı, bayat
listesine alınmadı.

**Düzeltme yapılmadı** (lint kuralı). Ancak bu bulgular jüri sunumuna doğrudan
sızabilir.

### 6.5. Kendi sayfası olmayan, 3+ sayfada geçen kavramlar (en fazla 5 öneri)

| Kavram | Kaç sayfada | Öneri |
|---|---|---|
| **gold küme / altın standart** | **9** | `concepts/gold-kume.md` — vault'un en çok atıf alan sayfasız kavramı. Şu an yalnız `sorun/gold-round1-...` (bir arıza kaydı) ve `decisions/zor-anlama-vakalari-merkezi` içinde dağınık. Model Başarısı %30 kriterinin dayanağı. **En yüksek öncelik.** |
| **RAG** | **8** | `concepts/rag.md` — `hibrit-chatbot-text-to-sql-rag` ve `klasik-veri-ince-ayar-rag-reddi` kararlarının ortak öncülü, ama tanımı hiçbir yerde yok |
| **F1 / değerlendirme metrikleri** | **7** | `concepts/degerlendirme-metrikleri.md` — F1, precision/recall, strict↔tolerant eşleştirici ayrımı, güven aralığı. Ablasyon tablosu bunlar olmadan okunamıyor |
| **Ollama** | **6** | `entities/ollama.md` — somut çalıştırma bileşeni, on-prem iddiasının taşıyıcısı; `on-premise-uygulanabilirlik` ondan bahsediyor ama entity sayfası yok |
| **ablasyon** | **5** | `concepts/ablasyon.md` — yöntem olarak tanımlı değil; §6.1'deki çelişkinin çözülmesi için de ortak bir kavram sayfası gerekiyor |

Ayrıca 3 sayfada geçen ama şimdilik düşük öncelikli: `few-shot` (6 — karar
sayfası başlığında var, ayrı concept gerekmeyebilir), `text-to-SQL` (5),
`uydurma/halüsinasyon` (3), `Docker` (3).

### 6.6. Çapraz referans boşlukları

- `concepts/katilim-finans-terimleri.md` → `sources/tcmb/2026-08-07-terimler-sozlugu`
  bağı **tek yönlü** (§2b).
- Bugünkü 4 sayfa dış vault'a bağlanmıyor (§3).
- `sources/docs` üçlüsünün ürettiği bulgular hiçbir `decisions/` sayfasına
  bağlanmamış (§6.1).

---

## 7. Graf sağlığı

- **Bağlı bileşen:** ana gövde tek parça; `archive/_plan-rakip-ustunluk` tümüyle
  kopuk (giden 0, gelen 0) → **2 bileşen**.
- **En çok gelen link (hub):** `sources/teknofest/2026-06-16-...-sartname-2-senaryo`
  (44), `concepts/urun-karsilastirma` (18), `concepts/bilgi-cikarimi` (18),
  `syntheses/teknik-cozum-mimarisi` (14), `entities/chatbot` (12).
- **En çok giden link:** `syntheses/yarisma-genel-bakis` (18),
  `sources/docs/2026-08-03-anatolia-ai-teknik-rapor` (16),
  `entities/klasik-banka-korpusu` (16).
- **Sink:** yalnızca `archive/_plan-rakip-ustunluk`.
- **Bayat sayfa (90+ gün):** **yok.** En eski sayfalar 2026-06-16 (42 sayfa,
  66 günlük) — eşiğin altında.

---

## Önerilen aksiyonlar

Etkiye göre sıralı. **Hiçbiri uygulanmadı.**

1. **§6.1 çelişkisini işaretle.** `decisions/ner-fine-tune-yerine-kural-few-shot.md`'ye
   `## ÇELİŞKİ` başlığı aç, 2026-08-05 ablasyon ölçümünü kaynağıyla yaz,
   `status: celiskili` yap; `sources/docs/2026-08-05-ablasyon.md`'den karara
   geri-link kur. **Teslime 5 gün kala vault'un çıkarım konfigürasyonu hakkında
   iki farklı beyanı olması en büyük risk.**
2. **§6.4 korpus sayılarını tazele.** Özellikle `stable` statülü
   `decisions/klasik-veri-ince-ayar-rag-reddi.md` ve
   `entities/klasik-banka-korpusu.md`'deki **1759** → 2.708 (veya sayının neyi
   saydığı — kazınmış ham belge mi, DB kaydı mı — açıkça yazılsın). Jüri
   sunumuna sızma riski yüksek.
3. **§6.2 "hibrit" terimini ayrıştır.** İki karar sayfasında ve ablasyon
   kaynağında "çıkarım-hibriti" / "sorgu-hibriti" ayrımını açıkça yaz.
4. **`concepts/gold-kume.md` sayfasını aç** (9 sayfada geçiyor, sayfası yok).
   Ardından `sorun/gold-round1-csvden-yeniden-uretilemiyor` oradan link alsın —
   bir orphan da kapanır.
5. **§5 index.md driftini gider.** `## Archive` bölümüne
   `[[_plan-rakip-ustunluk]]` eklensin; yarım-ingest notundaki "wikilink'ler
   kırık" ifadesi "kırık linkler 2026-08-21'de düz metne indirildi, türev
   sayfalar hâlâ yazılmadı" diye güncellensin.
6. **`archive/_plan-rakip-ustunluk.md`'ye frontmatter ekle** (`status: arsiv`),
   dosyayı `archive/plan-rakip-ustunluk.md` olarak kebab-case'e taşı.
7. **§6.3 demo süresi çelişkisini kapat.** 26 Ağustos öncesi TEKNOFEST'e sor
   veya "her iki formatta hazırız" diye kesinleştir; ayrıca
   `decisions/juri-sunumu-bes-slayt` ↔ `syntheses/teslim-ve-degerlendirme-rehberi`
   çift yönlü bağını kur.
8. **§2b tek yönlü kaynak bağını onar.** `concepts/katilim-finans-terimleri`
   → `[[2026-08-07-terimler-sozlugu]]` linki eklensin.
9. **`sources/docs` üçlüsüne karar ver** (16–21 gündür `taslak` + orphan):
   ya türev sayfaları yazılıp ingest tamamlansın, ya `archive/`'a alınsın.
   Belirsiz üçüncü hâlde bırakılması vault'u aşındırıyor.
10. **Kalan concept sayfaları** (§6.5): `rag`, `degerlendirme-metrikleri`,
    `ollama`, `ablasyon`. Teslim sonrasına ertelenebilir.

## Sources
- Mekanik tarama: 2026-08-21 tarihli tek-seferlik link/frontmatter/graf
  denetimi (59 sayfa, 498 wikilink)
- `app/data/demo.db` — `campaigns` tablosu satır sayısı (2.708), 2026-08-21
- [[2026-08-05-ablasyon]] — §6.1 ölçüm sonuçları
- `log.md` — 2026-08-21 ingest girişi (kırık link indirimi beyanı, doğrulandı)

## Related
- `index.md` — dizin senkronu §5
- [[ner-fine-tune-yerine-kural-few-shot]] — §6.1 çelişki tarafı
- [[teslim-ve-degerlendirme-rehberi]] — §6.3 tek `celiskili` sayfa
- [[juri-sunumu-bes-slayt]] — §3 doğrulanan yeni sayfa
