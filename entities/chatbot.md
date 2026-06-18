---
title: "Chatbot (Sunum Bileşeni)"
tags: [entity, bilesen, arayuz, teslim]
source: "[[2026-06-16-teknofest-tyda-sartname-2-senaryo]]"
date: 2026-06-16
status: stable
---

# Chatbot (Sunum Bileşeni)

Anatolia AI çözümünün iki zorunlu sunum arayüzünden biri. Toplanan ve
yapılandırılan kampanya/ürün verileri üzerinden **doğal dilde soru-cevap**
yapılmasını sağlar.

- Chatbot, katılım bankalarının ürün ve kampanya verileriyle çalışır; kullanıcının
  doğal dildeki sorusunu analiz eder, ilgili veri alanını tespit eder ve doğru
  kampanya bilgisini sunar (şartname Senaryo-2, s.13).
- Örnek davranışlar (şartname s.13):
  - Tek banka sorgusu: "A Bankası'nın konut finansmanı oranı ne?" → "...kâr payı
    oranı %1,89, 120 aya kadar vade."
  - Karşılaştırma: "A Bankası mı C Bankası mı daha avantajlı?" → kâr payı, vade,
    masraf ve ödül boyutlarında kıyaslı yanıt.
- Soru-cevap, [[urun-karsilastirma]] ve [[bilgi-cikarimi]] çıktılarına dayanır.

## Sources
- [[2026-06-16-teknofest-tyda-sartname-2-senaryo]] — Amaç (s.3), Örnek Temsili
  Senaryo-2 (s.13)

## Related
- [[dashboard]] — diğer zorunlu sunum arayüzü
- [[dashboard-ve-chatbot-arayuzu]] — sunum katmanı kararı
- [[urun-karsilastirma]] — yanıtların dayandığı kıyaslama
- [[teknik-cozum-mimarisi]] — mimari içindeki yeri
- [[hibrit-chatbot-text-to-sql-rag]] — chatbot'un hibrit (text-to-SQL + RAG) mimari kararı
