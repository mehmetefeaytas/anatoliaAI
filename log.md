# Anatolia AI — Günlük (Log)

Kronolojik ingest / değişiklik günlüğü. En yeni en üstte.

## [2026-06-16] kod | app/ uçtan uca çekirdek inşa edildi

Bağlam: Kararlaştırılan v2 mimarisine göre `app/` altındaki tüm katmanlar kuruldu;
ağır modeller (vLLM/BERTurk) bu ortamda çalışamadığı için her katman **gerçek
kütüphane yolu + offline fallback** ile yazıldı. Tüm sistem modeller olmadan da
uçtan uca koşar (on-prem/offline kanıtı).

Kurulan katmanlar (hepsi test edildi):
- preprocessing, normalization (oran/para/vade/tarih/TR-sayı/aralık/negasyon)
- extraction: rules (birincil), llm (guided_json + vLLM/Ollama + Null-fallback),
  reconcile (kural birincil), ner/classifier (kural-ipucu + BERTurk yolu)
- db (SQLite offline + Postgres/pgvector şema), comparison (adil-kıyas) +
  contradiction (yenilikçilik), chatbot (router + yapısal sorgu + RAG)
- scraping (config-driven banks.yaml + offline fixtures), pipeline, api (FastAPI),
  web (Next.js dashboard+chatbot), eval (run_eval + ablation)

Doğrulama:
- **54 birim/entegrasyon testi, tamamı offline yeşil.**
- 10 banka config'ten yüklendi; 3 fixture uçtan uca işlendi.
- Chatbot doğru yönlendirdi: "en düşük kâr payı" → Kuveyt Türk %1,89 (yapısal),
  "taşıt koşulları" → RAG. Ablasyon dürüst rapor (LLM offline notu).

İlgili kararlar: [[hibrit-chatbot-text-to-sql-rag]],
[[ner-fine-tune-yerine-kural-few-shot]], [[zor-anlama-vakalari-merkezi]],
[[daraltilmis-yenilikcilik-hedefleri]], [[demo-onceden-doldurulmus-db]].

## [2026-06-16] karar | kod-projesi-mimari-v2 (5 kritik karar)

Bağlam: Önceki oturumda kullanıcının paylaştığı kod projesi planı (`CLAUDE.md v1`)
değerlendirildi; kazandıran 5 mimari değişiklik kararlaştırıldı ve `app/CLAUDE.md`
(v2) yazıldı. Bu kararlar şartname kaynağına dayanır.

Dokunulan dosyalar:

- **app/CLAUDE.md** (oluşturuldu — kod projesinin v2 operasyon kılavuzu)
- **decisions/** hibrit-chatbot-text-to-sql-rag.md,
  ner-fine-tune-yerine-kural-few-shot.md, demo-onceden-doldurulmus-db.md,
  zor-anlama-vakalari-merkezi.md, daraltilmis-yenilikcilik-hedefleri.md (oluşturuldu)
- index.md (Decisions bölümüne 5 yeni karar eklendi)
- entities/chatbot.md, syntheses/teknik-cozum-mimarisi.md (geri-bağlantı eklendi)
- _oturum-devir.md (oluşturuldu — eski `anatoliaal` oturumunun bağlam devri)

Notlar:
- Kararların 5'i de şartname değerlendirme ağırlıklarına (%30 model başarısı, %20
  fonksiyonellik, %20 on-prem, %10 yenilikçilik) dayandırıldı.
- Sıradaki adım: deterministik kural/normalizasyon katmanı + eval harness (kod).

## [2026-06-16] ingest | teknofest-tyda-sartname-2-senaryo

Kaynak: `raw/teknofest/2026-teknofest-tyda-sartname-2-senaryo.pdf`
(sembolik link → TEKNOFEST TYDA Şartname 2. Senaryo, 25 sayfa, ~36k karakter).
Tek pass kurulum + ilk ingest.

Dokunulan dosyalar:

- **sources/teknofest/** 2026-06-16-teknofest-tyda-sartname-2-senaryo.md (oluşturuldu)
- **entities/** teknofest.md, bilisim-vadisi.md, bddk.md,
  turkiye-acik-kaynak-platformu.md, t3kys-basvuru-sistemi.md, github.md,
  chatbot.md, dashboard.md, veri-seti.md, katilim-bankalari.md (oluşturuldu)
- **concepts/** katilim-bankaciligi.md, kar-payi-orani.md, nlp.md,
  bilgi-cikarimi.md, metin-siniflandirma.md, kampanya-turleri.md,
  veri-on-isleme.md, veri-normalizasyonu.md, yapilandirilmis-veri-formati.md,
  on-premise-uygulanabilirlik.md, acik-kaynak-yaklasimi.md, web-scraping.md,
  urun-karsilastirma.md (oluşturuldu)
- **decisions/** on-premise-calistirilabilir-mimari.md,
  apache-2-acik-kaynak-lisansi.md, python-tabanli-veri-toplama.md,
  dashboard-ve-chatbot-arayuzu.md, bddk-listesi-veri-kaynagi-kapsami.md,
  yapilandirilmis-veri-formati-zorunlulugu.md (oluşturuldu)
- **sorun/** standart-veri-formati-eksikligi.md,
  katilim-bankaciligi-terminoloji-farkliligi.md, farkli-ifade-bicimleri.md,
  manuel-karsilastirma-zorlugu.md (oluşturuldu)
- **syntheses/** yarisma-genel-bakis.md, teknik-cozum-mimarisi.md,
  teslim-ve-degerlendirme-rehberi.md (oluşturuldu)
- index.md, lint-report.md (güncellendi/oluşturuldu)

Notlar:
- Çelişki tespit edildi (demo videosu süresi 5 dk vs 1 dk) →
  teslim-ve-degerlendirme-rehberi.md içinde `## ÇELİŞKİ` ile işaretlendi.
- Slug çakışması düzeltildi: decisions kararı
  `yapilandirilmis-veri-formati-zorunlulugu` olarak adlandırıldı (concept
  `yapilandirilmis-veri-formati` ile çakışmaması için).
