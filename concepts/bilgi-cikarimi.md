---
title: "Bilgi Çıkarımı (Finansal Bilgi Çıkarımı)"
tags: [concept, nlp, yetenek]
source: "[[2026-06-16-teknofest-tyda-sartname-2-senaryo]]"
date: 2026-06-16
status: stable
---

# Bilgi Çıkarımı (Finansal Bilgi Çıkarımı)

Kampanya metinleri içinden kullanıcı kararını etkileyen finansal bilgilerin
otomatik çıkarılması (şartname 5.3, s.7). [[nlp]] çözümünün çekirdek yeteneği.

Çıkarılması beklenen temel bilgi alanları (şartname 5.3 tablosu, s.7):

- **Banka bilgisi**
- **Finansman bilgileri:** [[kar-payi-orani]], finansman tutarı, vade süresi,
  taksit sayısı, tahsis ücreti, masraf bilgisi
- **Kampanya bilgileri:** kampanya türü, ödül miktarı, indirim oranı, alışveriş
  puanı, kampanya süresi, kampanya koşulları
- **Hedef kitle bilgileri:** yeni/mevcut/maaş müşterileri, belirli segmentler

Çıkarılan bilgiler [[yapilandirilmis-veri-formati]]'na dönüştürülür; sonrasında
[[veri-normalizasyonu]] ve [[urun-karsilastirma]] uygulanır.

## Sources
- [[2026-06-16-teknofest-tyda-sartname-2-senaryo]] — 5.3 Finansal Bilgi Çıkarımı
  (s.7), Tespit Edilmesi Gerekenler (s.13)

## Related
- [[nlp]] — üst alan
- [[kar-payi-orani]] — çıkarılan kritik alan
- [[yapilandirilmis-veri-formati]] — çıktının formatı
- [[urun-karsilastirma]] — çıktının kullanımı
