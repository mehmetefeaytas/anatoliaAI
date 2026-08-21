# Anatolia AI — Dizin (Index)

Bu vault'taki tüm sayfaların kategorize dizini. Her ingest sonrası güncellenir.
Son güncelleme: 2026-08-10.

## Sources
- [[2026-06-16-teknofest-tyda-sartname-2-senaryo]] — TEKNOFEST TYDA Teknik Şartname (2. Senaryo) ingest özeti
- [[2026-08-06-mentor-terim-sozlugu]] — mentör maili: 101 girdilik katılım finansı
  sözlüğü + "replace etme, LLM'e analizi ver" görüşü
- [[2026-08-07-terimler-sozlugu]] — TCMB Terimler Sözlüğü (314 terim), karşıt
  (konvansiyonel) terminoloji otoritesi

> **Dizine alınmamış 3 kaynak sayfası var** (`sources/docs/` altında:
> `2026-07-31-offline-kanit`, `2026-08-03-anatolia-ai-teknik-rapor`,
> `2026-08-05-ablasyon`). Yarıda kalmış bir ingest'e aittirler: ürettikleri
> ~45 türev sayfa (entity/concept/decision) hiç oluşturulmamış, dolayısıyla o
> sayfalardan çıkan wikilink'ler kırık. **Bilerek** dizine alınmadılar;
> kullanıcı kararı bekliyorlar. Silinmediler, taşınmadılar (hard rule #3).

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

## Sorunlar
- [[standart-veri-formati-eksikligi]] — standart format yok
- [[katilim-bankaciligi-terminoloji-farkliligi]] — terminoloji farkı
- [[farkli-ifade-bicimleri]] — aynı değer farklı yazım
- [[manuel-karsilastirma-zorlugu]] — manuel kıyas zorluğu
- [[gold-round1-csvden-yeniden-uretilemiyor]] — derleme komutu belgesizdi (`--pre .v2`), ÇÖZÜLDÜ; tahkim kararları CSV'lere taşındı

## Syntheses
- [[yarisma-genel-bakis]] — yarışma çerçevesi, takvim, ödüller
- [[teknik-cozum-mimarisi]] — uçtan uca çözüm hattı
- [[teslim-ve-degerlendirme-rehberi]] — teslimler + puanlama (çelişki notu içerir)

## Archive
_(arşivlenmiş sayfa yok)_
