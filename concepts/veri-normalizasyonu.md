---
title: "Veri Normalizasyonu (Standart Formata Dönüştürme)"
tags: [concept, veri, normalizasyon]
source: "[[2026-06-16-teknofest-tyda-sartname-2-senaryo]]"
date: 2026-06-16
status: stable
---

# Veri Normalizasyonu (Standart Formata Dönüştürme)

Kampanya metinlerindeki farklı formatlarda yazılmış finansal bilgilerin **tek bir
standart yapıya** dönüştürülmesi (şartname 5.6, s.9).

Örnekler (şartname 5.6):

- `%2,05`, `% 2.05`, `2.05 %` → **aynı değer** olarak yorumlanmalı.
- `500 TL`, `500₺`, `500 Türk Lirası` → **aynı değer** olarak algılanmalı.

Bu adım, [[farkli-ifade-bicimleri]] sorununun doğrudan çözümüdür ve
[[urun-karsilastirma]]'nın doğru çalışması için ön koşuldur. Çıktı genelde
[[yapilandirilmis-veri-formati]]'na yazılır.

## Sources
- [[2026-06-16-teknofest-tyda-sartname-2-senaryo]] — 5.6 Bilgilerin Standart
  Formata Dönüştürülmesi (s.9)

## Related
- [[farkli-ifade-bicimleri]] — çözdüğü sorun
- [[yapilandirilmis-veri-formati]] — hedef format
- [[urun-karsilastirma]] — bu normalizasyona bağımlı
- [[kar-payi-orani]] — normalize edilen tipik alan
