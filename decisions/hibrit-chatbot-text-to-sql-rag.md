---
title: "Karar: Chatbot hibrit (text-to-SQL + RAG), saf RAG değil"
tags: [decision, chatbot, rag, sorgu]
source: "[[2026-06-16-teknofest-tyda-sartname-2-senaryo]]"
date: 2026-06-16
status: stable
---

# Karar: Chatbot hibrit (text-to-SQL + RAG), saf RAG değil

**Karar:** [[chatbot]] saf semantik RAG ile değil, bir **router** üzerinden
**hibrit** kurulur: sayısal/karşılaştırmalı sorular `extracted_fields` tablosu
üzerinde **text-to-SQL / yapısal sorgu** ile, koşul/açıklama soruları **RAG** ile
yanıtlanır.

**Gerekçe (şartname dayanağı):** Senaryonun merkezinde bankalar arası
[[urun-karsilastirma]] var — *"hangi bankada en düşük kâr payı?"*, *"36 ay vade
veren konut finansmanları"* gibi **toplama/sıralama** soruları (s.3, s.6). Saf
semantik RAG (bge-m3 + pgvector) bu tür kesin sayısal-karşılaştırmalı sorulara zayıf
cevap verir; yapılandırılmış sorgu kesin sonuç döndürür.

**Etkileri:**
- Fonksiyonellik (%20) ve Model Başarısı (%30) kriterlerini birlikte yükseltir.
- [[yapilandirilmis-veri-formati]] zorunlu — text-to-SQL ancak normalize alanlar
  üzerinde güvenilir çalışır.
- Router'ın soru sınıflandırması yeni bir bileşendir (`src/chatbot/`).

## Sources
- [[2026-06-16-teknofest-tyda-sartname-2-senaryo]] — Amaç (s.3), Temel
  Beklentiler/chatbot (s.6)

## Related
- [[chatbot]] — etkilenen bileşen
- [[urun-karsilastirma]] — sorgu hedefi
- [[dashboard-ve-chatbot-arayuzu]] — sunum katmanı kararı
- [[teknik-cozum-mimarisi]] — mimari sentez
