---
title: "Sentez: Teknik Çözüm Mimarisi"
tags: [synthesis, mimari, nlp]
source: "[[2026-06-16-teknofest-tyda-sartname-2-senaryo]]"
date: 2026-06-16
status: stable
---

# Sentez: Teknik Çözüm Mimarisi

Şartnamenin "Temel Beklentiler" (5.1–5.10) bölümünden türetilen, Anatolia AI
çözümünün uçtan uca mimarisi. Kaynak:
[[2026-06-16-teknofest-tyda-sartname-2-senaryo]].

## Uçtan uca veri hattı (pipeline)

```
[1] Veri Toplama        → [[web-scraping]] / [[python-tabanli-veri-toplama]]
        ↓                  kapsam: [[bddk-listesi-veri-kaynagi-kapsami]] → [[veri-seti]]
[2] Veri Ön İşleme      → [[veri-on-isleme]]
        ↓
[3] Metin Analizi/NLP   → [[nlp]] (metin madenciliği, kural tabanlı, model)
        ↓
[4] Bilgi Çıkarımı      → [[bilgi-cikarimi]] (kâr payı, vade, ödül, segment...)
[4'] Sınıflandırma      → [[metin-siniflandirma]] → [[kampanya-turleri]]
        ↓
[5] Normalizasyon       → [[veri-normalizasyonu]] (%2,05 ≡ 2.05%)
        ↓
[6] Yapılandırma        → [[yapilandirilmis-veri-formati]]
        ↓                  (karar: [[yapilandirilmis-veri-formati-zorunlulugu]])
[7] Karşılaştırma       → [[urun-karsilastirma]]
        ↓
[8] Sunum               → [[dashboard]] + [[chatbot]]
                           (karar: [[dashboard-ve-chatbot-arayuzu]])
```

## Bağlayıcı mimari kısıtlar

- **On-premise:** lokal, dış servis bağımsız → [[on-premise-calistirilabilir-mimari]]
  / [[on-premise-uygulanabilirlik]].
- **Açık kaynak:** ücretli yazılım yok, modeller açık ve ölçeklenebilir →
  [[acik-kaynak-yaklasimi]] / [[apache-2-acik-kaynak-lisansi]].
- **Terminoloji uyumu:** [[katilim-bankaciligi]] kavramları doğru yorumlanmalı.

## Açık karar (ekibe bırakılmış)

NLP yaklaşımının türü (kural tabanlı / açık kaynak LLM / hibrit) şartnamede serbest
bırakılmıştır; model başarısı değerlendirmenin **%30'unu** oluşturur (en yüksek
ağırlık) → [[teslim-ve-degerlendirme-rehberi]].

## Sources
- [[2026-06-16-teknofest-tyda-sartname-2-senaryo]] — 5.1–5.10 (s.6–11),
  Örnek Senaryolar (s.11–13)

## Related
- [[yarisma-genel-bakis]] — bağlam
- [[teslim-ve-degerlendirme-rehberi]] — teslim ve puanlama
- [[hibrit-chatbot-text-to-sql-rag]] — chatbot mimari kararı (v2)
- [[ner-fine-tune-yerine-kural-few-shot]] — çıkarım stratejisi kararı (v2)
- [[demo-onceden-doldurulmus-db]] — demo stratejisi kararı (v2)
- [[zor-anlama-vakalari-merkezi]] — zor vaka odağı kararı (v2)
- [[daraltilmis-yenilikcilik-hedefleri]] — yenilikçilik kapsamı kararı (v2)
