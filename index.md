# Anatolia AI — Dizin (Index)

Bu vault'taki tüm sayfaların kategorize dizini. Her ingest sonrası güncellenir.
Son güncelleme: 2026-08-21.

## Sources
- [[2026-06-16-teknofest-tyda-sartname-2-senaryo]] — TEKNOFEST TYDA Teknik Şartname (2. Senaryo) ingest özeti
- [[2026-08-06-mentor-terim-sozlugu]] — mentör maili: 101 girdilik katılım finansı
  sözlüğü + "replace etme, LLM'e analizi ver" görüşü
- [[2026-08-07-terimler-sozlugu]] — TCMB Terimler Sözlüğü (314 terim), karşıt
  (konvansiyonel) terminoloji otoritesi

> **Dizine alınmamış 3 kaynak sayfası var** (`sources/docs/` altında:
> `2026-07-31-offline-kanit`, `2026-08-03-anatolia-ai-teknik-rapor`,
> `2026-08-05-ablasyon`). Yarıda kalmış bir ingest'e aittirler: ürettikleri
> ~45 türev sayfa (entity/concept/decision) hiç oluşturulmamış. 2026-08-21'de
> kırık wikilink'leri düz metne indirildi ve üçü `status: taslak` yapıldı;
> türev sayfalar hâlâ yazılmayı bekliyor. Silinmediler (hard rule #3).
- [[2026-08-24-ssb-evren-cikarim-servisi]] — SSB EVREN çıkarım servisi: duyuru + canlı ölçüm (10 model, 8×H200)
- [[2026-08-24-tkbb-kar-payi-veri-seti]] — TKBB kâr payı: iki uç, 210.474 tarihsel + 245 güncel kayıt

## Entities
- [[teknofest]] — yarışma organizasyonu
- [[bilisim-vadisi]] — yürütücü kurum
- [[bddk]] — veri kapsamı kaynağı (katılım bankaları listesi)
- [[turkiye-acik-kaynak-platformu]] — kod paylaşım platformu
- [[t3kys-basvuru-sistemi]] — başvuru/süreç sistemi (KYS)
- [[github]] — kod/veri/doküman teslim ortamı
- [[chatbot]] — sunum bileşeni (soru-cevap)
- [[dashboard]] — sunum bileşeni (raporlama)
- [[veri-seti]] — kampanya/ürün metinleri veri kümesi (kapsam **İÇİ**)
- [[klasik-banka-korpusu]] — `data/raw-classic`, klasik banka korpusu — **YARIŞMA
  KAPSAMI DIŞI**, yalnızca gümüş eğitim verisi
- [[katilim-bankalari]] — hedef kuruluşlar
- [[ssb-evren-cikarim-servisi]] — SSB'nin tüm takımlara açtığı ücretsiz çıkarım servisi
- [[tkbb-kar-payi-veri-seti]] — TKBB'nin katılma hesabı oranı uçları (tarihsel arşiv + güncel hafta)

## Concepts
- [[katilim-bankaciligi]] — alan
- [[kar-payi-orani]] — temel finansal terim
- [[nlp]] — doğal dil işleme
- [[bilgi-cikarimi]] — finansal bilgi çıkarımı
- [[metin-siniflandirma]] — kampanya sınıflandırma
- [[kampanya-turleri]] — sınıflandırma etiketleri
- [[veri-on-isleme]] — ön işleme adımları
- [[veri-normalizasyonu]] — standart formata dönüştürme
- [[yapilandirilmis-veri-formati]] — çıktı yapısı
- [[on-premise-uygulanabilirlik]] — kurum içi çalışma
- [[acik-kaynak-yaklasimi]] — açık kaynak kısıtı
- [[web-scraping]] — veri toplama tekniği
- [[urun-karsilastirma]] — bankalar arası kıyas
- [[katilim-finans-terimleri]] — 101 girdilik yapılandırılmış terim sözlüğü
  (şema: `kanonik`/`varyantlar`/`degildir`/`ayrim_notu`/`risk_notu`)

## Decisions
- [[on-premise-calistirilabilir-mimari]] — kurum içi mimari
- [[apache-2-acik-kaynak-lisansi]] — Apache 2.0 lisansı
- [[python-tabanli-veri-toplama]] — Python ile toplama
- [[dashboard-ve-chatbot-arayuzu]] — sunum katmanı
- [[bddk-listesi-veri-kaynagi-kapsami]] — veri kapsamı
- [[yapilandirilmis-veri-formati-zorunlulugu]] — yapılandırma kararı
- [[hibrit-chatbot-text-to-sql-rag]] — chatbot hibrit mimari (text-to-SQL + RAG)
- [[ner-fine-tune-yerine-kural-few-shot]] — çıkarım: kural + few-shot, fine-tune yalnız sınıflandırma
- [[demo-onceden-doldurulmus-db]] — demo önceden doldurulmuş DB'den
- [[zor-anlama-vakalari-merkezi]] — zor anlama vakaları + gold alt kümesi
- [[daraltilmis-yenilikcilik-hedefleri]] — yenilikçilik 3 hedefe daraltıldı
- [[masrafsizlik-celiskisi-kapsam-testi]] — masrafsızlık çelişkisi kapsam testidir, ücret varlığı testi değil
- [[klasik-veri-ince-ayar-rag-reddi]] — klasik banka verisi ince ayar ve RAG kaynağı olarak reddedildi
- [[terim-sozlugu-enjeksiyon-replace-degil]] — terim sözlüğü prompt'a enjekte
  edilir; kör dize değiştirme (replace) yapılmaz
- [[orkestrasyon-yetki-asimetrisi]] — ajanlar önerir, hakem yalnız reddeder;
  LLM ajanlarının yazma yetkisi yok
- [[juri-sunumu-bes-slayt]] — şartname §10 4 dk verir; 15 slaytlık sunum 5
  slaytlık yönetici seviyesi sunumla değiştirildi, eskisi arşivlendi
- [[evren-opsiyonel-kademe-olarak-entegrasyon]] — EVREN bağımlılık değil, kademe (fallback)
- [[gomme-yolu-evren-ile-acildi]] — gömme yolu EVREN ile açıldı, yerel yedek
- [[hibrit-erisim-rrf-ile-birlestirilir]] — erişimde RRF birleşimi; varsayılan değişmedi
- [[urun-baglami-alan-duzeyinde-tasinmali]] — çok ürünlü belge uyarısı; alan-başına aile açık

- [[katilma-orani-iki-ayri-buyukluk]] — getiri (%42) ile pay (%90) aynı kolonda yarışmaz
- [[llm-yalniz-kural-bosluklarini-doldurur]] — iki kabul kapısı: dayanak + doğru alan
- [[tkbb-sozlugu-ikincil-kaynak-olarak-baglanir]] — 101 → 577 terim; çakışmada proje kaydı kazanır
## Sorunlar
- [[standart-veri-formati-eksikligi]] — standart format yok
- [[katilim-bankaciligi-terminoloji-farkliligi]] — terminoloji farkı
- [[farkli-ifade-bicimleri]] — aynı değer farklı yazım
- [[manuel-karsilastirma-zorlugu]] — manuel kıyas zorluğu
- [[gold-round1-csvden-yeniden-uretilemiyor]] — derleme komutu belgesizdi (`--pre .v2`), ÇÖZÜLDÜ; tahkim kararları CSV'lere taşındı
- [[turkce-buyuk-harf-yerel-duyarliligi]] — `text-transform:uppercase` yerel-duyarlı; `lang` yoksa noktasız-İ hataları («ÜRETIMDE»), çözüm `kok.lang = "tr"`
- [[sunum-slayt-sigdirma-olcek-cokusu]] — taşan slayt tek katsayıyla 0,75'e küçülüyordu; içerik 1080px'e sığana kadar sıkıştırıldı
- [[next-dev-proxy-econnreset-yanlis-alarmi]] — «Sunucu 500» ürün hatası değil, Next dev proxy'sinin ölü keep-alive soketi (`ECONNRESET`); yanlış alarm
- [[pazarlik-http-200-kisit-uygulanmadi]] — HTTP 200 ≠ kısıt uygulandı (sessiz hata)
- [[ozet-sayisal-degeri-denetleyen-kapi-yoktu]] — özetteki sayı kaynakta yoktu; kapı eklendi
- [[kiyas-cevabinda-iki-gosterim-hatasi]] — vade %120 basılıyordu; yön sessizce yok sayılıyordu
- [[terim-sorusuna-sozlukten-cevap-verilmiyordu]] — 101 terimlik sözlük vardı, chatbot bakmıyordu
- [[katilma-hesabi-orani-korpusta-yoktu]] — katılma getirisi kampanya metninde yok; TKBB'den geldi

- [[merkezi-veri-segment-ayrimini-gizliyor]] — TKBB tek oran, banka beş oran (Klasik %85 vs merkezî %92)
- [[tcmb-sozlugu-terim-boslugunu-kapatmiyor]] — 314 terim ölçüldü, 'Finansman' yok, %22'si yasak kök taşıyor
- [[evren-celiski-tespitinde-katki-vermedi]] — 230 belgede 0 bulgu; yol ölçülerek kapatıldı
- [[celiski-tespiti-yavasti-ve-500-donuyordu]] — soğuk tarama 47,2 sn ölçüldü; artefaktla 0,001 sn'ye indi
- [[ekran-cekimi-ham-veriyi-yeniden-topladi]] — kare almak canlı tazeleme başlattı, `expiry_stamp` damgaları silindi
- [[banka-sayfasi-paydaya-sozlesme-katiyordu]] — «93 belge · %15 kapsama» yanlış evrenden; 42'si sözleşmeydi
## Syntheses
- [[yarisma-genel-bakis]] — yarışma çerçevesi, takvim, ödüller
- [[teknik-cozum-mimarisi]] — uçtan uca çözüm hattı
- [[teslim-ve-degerlendirme-rehberi]] — teslimler + puanlama (çelişki notu içerir)

## Archive
- `archive/_plan-rakip-ustunluk.md` — 12 Ağu tarihli rakip analizi çalışma
  notu (gitignore'lu; geçerli sürüm `app/_plan-rakip-ustunluk.md`)
