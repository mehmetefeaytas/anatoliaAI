---
title: "TEKNOFEST TYDA Yarışması — Teknik Şartname (2. Senaryo)"
tags: [kaynak, sartname, teknofest, nlp, katilim-bankaciligi]
source: "raw/teknofest/2026-teknofest-tyda-sartname-2-senaryo.pdf"
date: 2026-06-16
status: stable
---

# TEKNOFEST TYDA Yarışması — Teknik Şartname (2. Senaryo)

TEKNOFEST **Türkçe Yapay Zeka Dil Ajanları Yarışması**'nın 2. senaryosuna ait
resmi teknik şartnamenin ingest özeti. Belge, Anatolia AI projesinin tüm
gereksinim, takvim, değerlendirme ve kuralları için **birincil kaynaktır**.

## Goal (Amaç)

Yarışmanın kapsamını, problemini, beklentilerini, teslim edilecekleri,
değerlendirme kriterlerini, takvimi, katılım şartlarını ve etik kuralları
tanımlamak. Yürütücü: **Bilişim Vadisi**, TEKNOFEST kapsamında.

## What-was-done (Belge ne anlatıyor)

Katılım bankalarının resmî web sitelerinde **doğal dilde** yayımlanan finansman,
kart ve yatırım kampanyası metinlerinden, **NLP** teknikleriyle anlamlı finansal
bilgilerin otomatik çıkarılması; bu bilgilerin **standart/yapılandırılmış**
formata dönüştürülmesi; farklı bankaların ürünlerinin **karşılaştırılabilir** hale
getirilmesi; sonuçların **dashboard** ve **chatbot** üzerinden sunulması istenir.
Çözüm **on-premise** çalışabilmeli ve **açık kaynak** olmalıdır.

Belgenin ana bölümleri: Giriş, Amaç, Yarışma Takvimi, Problem Tanımı, Temel
Beklentiler (5.1–5.10), Tespit Edilmesi Gerekenler (teslimler), Değerlendirme
Kriterleri, Katılım Şartları, Proje/Yarışma Sunumları, Puanlama, Ödüller,
İletişim, Genel/Etik Kurallar, Sorumluluk Beyanı.

## Files-changed / touched (bahsi geçen varlık ve kavramlar)

Bu ingest sırasında oluşturulan/güncellenen wiki sayfaları:

- Entities: [[teknofest]], [[bilisim-vadisi]], [[bddk]],
  [[turkiye-acik-kaynak-platformu]], [[t3kys-basvuru-sistemi]], [[github]],
  [[chatbot]], [[dashboard]], [[veri-seti]], [[katilim-bankalari]]
- Concepts: [[katilim-bankaciligi]], [[kar-payi-orani]], [[nlp]],
  [[bilgi-cikarimi]], [[metin-siniflandirma]], [[veri-on-isleme]],
  [[veri-normalizasyonu]], [[kampanya-turleri]], [[on-premise-uygulanabilirlik]],
  [[acik-kaynak-yaklasimi]], [[web-scraping]], [[urun-karsilastirma]]
- Decisions: [[on-premise-calistirilabilir-mimari]],
  [[apache-2-acik-kaynak-lisansi]], [[python-tabanli-veri-toplama]],
  [[dashboard-ve-chatbot-arayuzu]], [[bddk-listesi-veri-kaynagi-kapsami]],
  [[yapilandirilmis-veri-formati-zorunlulugu]]
- Sorunlar: [[standart-veri-formati-eksikligi]],
  [[katilim-bankaciligi-terminoloji-farkliligi]],
  [[farkli-ifade-bicimleri]], [[manuel-karsilastirma-zorlugu]]

## Decisions (çıkan kararlar)

- Çözüm **on-premise** çalışmalı, dış servise bağımlı olmamalı →
  [[on-premise-calistirilabilir-mimari]]
- Tüm kod **Apache 2.0** ile açık kaynak yayımlanmalı →
  [[apache-2-acik-kaynak-lisansi]]
- Veri toplama **Python tabanlı** araçlar/web scraping ile →
  [[python-tabanli-veri-toplama]]
- Sunum katmanı **dashboard + chatbot** → [[dashboard-ve-chatbot-arayuzu]]
- Veri seti kapsamı **BDDK katılım bankaları listesi** →
  [[bddk-listesi-veri-kaynagi-kapsami]]
- Çıktılar **yapılandırılmış veri formatına** dönüştürülmeli →
  [[yapilandirilmis-veri-formati-zorunlulugu]]

## Issues (çıkan sorunlar)

- Kampanya metinleri standart formatta değil →
  [[standart-veri-formati-eksikligi]]
- Katılım bankacılığı terminolojisi bankadan bankaya değişiyor →
  [[katilim-bankaciligi-terminoloji-farkliligi]]
- Aynı değer farklı yazılıyor (%2,05 vs 2.05%) → [[farkli-ifade-bicimleri]]
- Kullanıcının manuel karşılaştırması zor → [[manuel-karsilastirma-zorlugu]]

## Open-threads (açık konular)

- Belgede **Yarışma Çevrimiçi Süreci** tarihleri (s.18, "... 2026") boş bırakılmış;
  kesin son teslim tarihi TEKNOFEST/KYS duyurusundan teyit edilmeli.
- **Puanlama Sistemi** (s.19) yalnızca "100'lük sistem" der; kriter ağırlıkları
  Değerlendirme Kriterleri (s.15) bölümünden gelir → [[teslim-ve-degerlendirme-rehberi]].
- Demo videosu süresi belgede iki yerde farklı: "maks. 5 dk" (s.14) ve "1 dk demo
  videosu" (s.19) → bkz. çelişki notu [[teslim-ve-degerlendirme-rehberi]].
- Hangi NLP yaklaşımının (kural tabanlı / LLM / hibrit) seçileceği ekip kararı;
  şartname serbest bırakmış → [[teknik-cozum-mimarisi]].

## Sources

- raw/teknofest/2026-teknofest-tyda-sartname-2-senaryo.pdf —
  "2026 TEKNOFEST TYDA Şartname İkinci Senaryo (TR)", 25 sayfa, tüm bölümler.

## Related

- [[yarisma-genel-bakis]] — bu kaynaktan türeyen genel bakış sentezi
- [[teknik-cozum-mimarisi]] — beklentilerden türeyen çözüm mimarisi sentezi
- [[teslim-ve-degerlendirme-rehberi]] — teslimler + değerlendirme sentezi
