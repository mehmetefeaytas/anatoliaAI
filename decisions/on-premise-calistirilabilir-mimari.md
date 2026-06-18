---
title: "Karar: On-premise çalıştırılabilir mimari"
tags: [decision, mimari, on-premise]
source: "[[2026-06-16-teknofest-tyda-sartname-2-senaryo]]"
date: 2026-06-16
status: stable
---

# Karar: On-premise çalıştırılabilir mimari

**Karar:** Çözüm tamamen kurum içinde (on-premise) çalışacak şekilde tasarlanır;
hiçbir kritik bileşen dış servise bağımlı olmaz, müşteri verisi kurum dışına
çıkmaz.

**Gerekçe (şartname dayanağı):** Bankalar veri güvenliği ve regülasyon nedeniyle
çözümün kurum içinde çalışmasını ister (5.9, s.10). Ayrıca değerlendirmenin **%20'si**
"On-Prem Uygulanabilirlik" kriteridir: lokal çalıştırılabilirlik, düşük harici
bağımlılık, kurum sistemlerine entegre edilebilir mimari (s.15).

**Etkileri:**
- Modeller lokal çalışabilen, açık kaynak seçeneklerden seçilir →
  [[apache-2-acik-kaynak-lisansi]], [[acik-kaynak-yaklasimi]].
- Bulut tabanlı/ücretli API'lere bağımlılık dışlanır.

## Sources
- [[2026-06-16-teknofest-tyda-sartname-2-senaryo]] — 5.9 (s.10), Değerlendirme
  Kriterleri (s.15)

## Related
- [[on-premise-uygulanabilirlik]] — kavram
- [[acik-kaynak-yaklasimi]] — birlikte kısıt
- [[teknik-cozum-mimarisi]] — mimari sentez
