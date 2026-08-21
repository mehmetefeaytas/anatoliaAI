# NotebookLM'e Yükleme Rehberi

Bu rehber, Anatolia AI dokümanlarını Google NotebookLM'e (veya benzeri bir doküman-tabanlı
asistana) yüklerken **hangi dosyaları, hangi sırayla ve neden** yüklemeniz gerektiğini anlatır.

---

## Önce bilmeniz gereken tek şey

**NotebookLM PDF içindeki grafikleri ve ekran görüntülerini okumaz — yalnızca metni indeksler.**

Bu yüzden rapor iki formatta üretildi:

| Format | Kime | Ne içerir |
|---|---|---|
| `anatolia-ai-teknik-rapor.pdf` | **insan** | 12 grafik + 11 ekran görüntüsü, 57 sayfa, basılabilir |
| `anatolia-ai-teknik-rapor.md` | **NotebookLM** | aynı metin; grafiklerin taşıdığı her sayı tablo olarak da var |
| `olcumler.md` | **NotebookLM** | projedeki **her ölçülmüş sayı** tek dosyada, kaynak referanslı |

Yani: PDF'i de yükleyebilirsiniz (zararı yok), ama **sayıların kaynağı markdown dosyaları
olmalı.** Sadece PDF yüklerseniz NotebookLM "chatbot p99 kaç ms?" sorusuna cevap veremez,
çünkü o sayı grafiğin içinde piksel olarak durur.

---

## Yüklenecek dosyalar (12 kalem, öncelik sırasıyla)

NotebookLM klasör yüklemeyi desteklemez — dosyaları **tek tek** eklemeniz gerekir.
Tüm yollar repo kökünden (`/Users/mehmetefeaytas/anatoliaaI/`) verilmiştir.

### Zorunlu çekirdek (1–3)

| # | Dosya | Neden |
|---|---|---|
| 1 | `app/docs/rapor/anatolia-ai-teknik-rapor.md` | **Ana doküman.** Mimari, kararlar, problemler, eksikler, yol haritası, uzman soruları, jüri simülasyonu |
| 2 | `app/docs/rapor/olcumler.md` | **Tüm ölçümler tek tabloda.** Sayı sorularının doğru cevaplanması buna bağlı |
| 3 | `2026_TEKNOFEST_TYDA_SARTNAME_Ikinci_Senaryo_TR_1_SmsXO.pdf` | Şartnamenin kendisi (metin katmanı var, okunur). Rubrik, §5.x maddeleri, teslim kalemleri |

### Teknik derinlik (4–10)

| # | Dosya | Neyi cevaplar |
|---|---|---|
| 4 | `app/docs/sartname-kod-eslesme.md` | "§5.7 nerede uygulanmış?" — madde → dosya → test eşlemesi |
| 5 | `app/docs/OFFLINE-KANIT.md` | "İnternetsiz çalıştığı nasıl kanıtlandı?" — 14 adım, ağ probu, digest pin |
| 6 | `app/docs/invariants.md` (vitrin dalında; `main` klonunda bulunmaz) | "Değişmez denetimi nedir, ne buldu?" — P1–P4, 134→0 |
| 7 | `app/docs/katilim-bankaciligi-guvenligi.md` | "5 güvenlik kapısı nasıl çalışır?" — politika, ablasyon, 9 eksik |
| 8 | `app/docs/model-license-audit.md` | "Hangi model neden reddedildi?" — `base_model` zinciri |
| 9 | `app/docs/veri-katmani.md` | "SQLite mi Postgres mi?" — parite, pgvector, NUL baytı |
| 10 | `app/docs/kaynak-tuketimi.md` | "Hangi donanım gerekir?" — 4 profil, 40× fark |

### Bağlam (11–12)

| # | Dosya | Neyi cevaplar |
|---|---|---|
| 11 | `app/data/gold/ANNOTATION_GUIDE.md` | "Anotasyon nasıl yapılacak?" — anotatörlere verilecek kılavuz |
| 12 | `syntheses/teslim-ve-degerlendirme-rehberi.md` **ve** `syntheses/yarisma-genel-bakis.md` | Takvim, ödüller, teslim kalemleri, demo videosu çelişkisi |

### İsteğe bağlı

| Dosya | Not |
|---|---|
| `app/docs/rapor/anatolia-ai-teknik-rapor.pdf` | İnsan okuması için; NotebookLM grafikleri okumaz ama metni okur |
| `app/CLAUDE.md` | Mimari kararların gerekçeleri (LLM işletim kılavuzu formatında) |
| `log.md` | Kronolojik geliştirme günlüğü — ⚠️ 27 Temmuz'da donmuş, bayat |

---

## Yükleme sonrası doğrulama

NotebookLM'in dokümanları gerçekten indekslediğini şu **beş kontrol sorusuyla** test edin.
Parantez içindeki cevabı vermiyorsa markdown dosyaları eksik yüklenmiş demektir:

| Soru | Doğru cevap |
|---|---|
| "Değişmez ihlalleri kaçtan kaça düştü?" | **134 → 43 → 15 → 0** |
| "Chatbot p99 gecikmesi kaç ms?" | **351,36 ms** (konteyner içi) |
| "Model Başarısı kriteri için ölçülmüş F1 var mı?" | **Hayır** — gold seti dondurulmadı, `metrics.json` hiç üretilmedi |
| "Kâr payı oranı kaç belgede var?" | **47 / 849 (%5,5)** |
| "Teslim edilen korpustaki alanların kaçı LLM'den geldi?" | **0** — 2.204 alanın %100'ü kural katmanından |

Son iki soru özellikle önemli: bunlar raporun en dürüst iki bulgusudur ve NotebookLM bunları
kaçırıyorsa özet çıkarırken projeyi olduğundan iyi gösterir.

---

## Kaçınılması gerekenler

| Yapma | Neden |
|---|---|
| Sadece PDF yüklemek | Grafiklerdeki sayılar kaybolur |
| `app/` altındaki tüm `.md` dosyalarını yüklemek | Kaynak kod docstring'leri gürültü yaratır; NotebookLM'in kaynak limiti dolar |
| `log.md`'ye dayanarak durum sormak | 27 Temmuz'da donmuş; 31 Temmuz'daki 40+ commit işlenmemiş. Güncel durum `olcumler.md`'de |
| `eval/reports/violations-son.jsonl`'a güvenmek | Bayat ara artefakt (15 ihlal içeriyor); bugün ölçülen değer **0** |

---

## Dosyalar güncellenince

Rapor üretilebilir bir çıktıdır. Ölçümler değişince şu sırayla yenileyin, sonra NotebookLM'deki
kaynakları değiştirin:

```bash
cd app

# 1) sunucuları kaldır (iki terminal)
DATABASE_PATH=data/demo.db DATABASE_URL= LLM_BACKEND= RAG_RETRIEVER=keyword \
  ./.venv/bin/python -m uvicorn src.api.main:app --port 8000
cd web && NEXT_PUBLIC_API_URL=http://127.0.0.1:8000 npm run dev

# 2) görselleri, grafikleri ve PDF'i yeniden üret
./.venv/bin/python docs/rapor/ekran_goruntuleri.py   # 11 ekran görüntüsü
./.venv/bin/python docs/rapor/grafikler.py           # 12 SVG (ölçüm dosyalarından)
./.venv/bin/python docs/rapor/build_pdf.py           # HTML + PDF
```

`grafikler.py` sayıları `docs/offline-proof/*.json`, `eval/reports/*.jsonl` ve `data/demo.db`'den
**canlı okur** — elle yazılmış sayı yoktur. Bu yüzden ölçüm güncellenince grafik de güncellenir.

`olcumler.md` ise **elle** bakım gerektirir; yeni bir ölçüm yapıldığında ilgili tabloya
eklenmesi gerekir.
