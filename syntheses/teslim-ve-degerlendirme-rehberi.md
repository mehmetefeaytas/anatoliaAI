---
title: "Sentez: Teslim ve Değerlendirme Rehberi"
tags: [synthesis, teslim, degerlendirme]
source: "[[2026-06-16-teknofest-tyda-sartname-2-senaryo]]"
date: 2026-06-16
status: celiskili
---

# Sentez: Teslim ve Değerlendirme Rehberi

Anatolia AI'ın ne teslim edeceği ve neye göre puanlanacağı. Kaynak:
[[2026-06-16-teknofest-tyda-sartname-2-senaryo]].

## Teslim edilecekler (şartname s.13–14)

1. **Çalışan proje kodu** — ön işleme, bilgi çıkarımı, normalizasyon, bankalar
   arası karşılaştırma çıktısı + kurulum adımları. Açık kaynak [[github]] deposu,
   bağımlılık listesi, çalıştırma adımları, veri seti indirme bağlantısı (s.18).
2. **Demo videosu** — sistemin metinden bilgi çıkarımını ve karşılaştırmayı
   gösteren video; arayüz/[[dashboard]]/[[chatbot]] gösterilmeli.
3. **Proje dokümantasyonu** — mimari, NLP yaklaşımı, veri seti, ön işleme, model
   yapısı, karşılaştırma yöntemi, kurulum, karşılaşılan problemler, örnek çıktılar,
   performans değerlendirme yöntemi.
4. **Sunum materyali** — PDF + PPTX (s.14).

## Değerlendirme kriterleri (şartname s.15, toplam %100)

| Kriter | Ağırlık |
|---|---|
| Model Başarısı ve Anlamlandırma Yeteneği | **%30** |
| Fonksiyonellik ve Senaryo Kapsamı | %20 |
| Teknik İmplementasyon ve Mimari | %20 |
| On-Prem Uygulanabilirlik | %20 |
| Yenilikçilik ve Yaratıcılık | %10 |

Puanlama 100'lük sistem üzerindendir (s.19). En yüksek ağırlık **model başarısı**:
farklı ifade biçimlerini doğru yorumlama, eksik/farklı yazılmış bilgide doğru
sonuç → [[bilgi-cikarimi]], [[veri-normalizasyonu]],
[[katilim-bankaciligi-terminoloji-farkliligi]].

## Süreç teslim kuralları

- En az **haftalık** GitHub güncellemesi; **"BilisimVadisi2026"** etiketi (s.18).
- Son 24 saat fiziksel: [[bilisim-vadisi]] Kocaeli Kampüsü; canlı sunum + demo (s.18–19).
- Nihai lisans **Apache 2.0** → [[apache-2-acik-kaynak-lisansi]].

## ÇELİŞKİ: Demo videosu süresi

Şartname demo videosu süresini iki ayrı yerde farklı belirtir:

- **s.14 (Tespit Edilmesi Gerekenler):** "maksimum **5 dakikalık** bir video
  hazırlanmalıdır."
- **s.19 (Yarışma Sunumları):** "Sunum süresi **4 dakika**, demo videosu süresi
  ise **1 dakika** olacaktır."

Olası yorum: s.14 bağımsız teslim videosunu (maks. 5 dk), s.19 canlı sunum sırasında
oynatılacak kısa demoyu (1 dk) tarif ediyor olabilir; ancak metin bunu açıkça
ayırmaz. **Karar:** Her iki gereksinime de uyacak şekilde hem ≤5 dk tam demo hem
1 dk'lık sunum-içi kısa demo hazırlanmalı; kesin format yarışma sırasında
gönderilecek bilgilendirme mailiyle teyit edilmeli (s.19).

## Sources
- [[2026-06-16-teknofest-tyda-sartname-2-senaryo]] — Tespit Edilmesi Gerekenler
  (s.13–14), Değerlendirme Kriterleri (s.15), Sunumlar/Puanlama (s.18–19)

## Related
- [[yarisma-genel-bakis]] — bağlam ve takvim
- [[teknik-cozum-mimarisi]] — neyin teslim edileceğinin teknik temeli
- [[github]] — teslim ortamı
