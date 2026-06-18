---
title: "Yapılandırılmış Veri Formatı"
tags: [concept, veri, format]
source: "[[2026-06-16-teknofest-tyda-sartname-2-senaryo]]"
date: 2026-06-16
status: stable
---

# Yapılandırılmış Veri Formatı

Metinden çıkarılan finansal bilgilerin, makine-okur ve karşılaştırılabilir bir
yapıya (tablo/satır-alan) dönüştürülmüş hali (şartname 5.3 ve Amaç, s.3, s.7).

Şartname s.12'deki örnek yapı (konut finansmanı):

| Banka | Ürün Türü | Kâr Payı | Vade | Kampanya Avantajı | Masraf | Kampanya Süresi |
|---|---|---|---|---|---|---|
| A Bankası | Konut finansmanı | %1,89 | 120 ay | 50.000 TL'ye kadar masraf yok | Dosya masrafı yok | 31 Aralık 2026 |
| B Bankası | Konut finansmanı | %1,95 | 120 ay | Ekspertiz banka tarafından | Ekspertiz ücretsiz | Belirtilmemiş |
| C Bankası | Konut finansmanı | %1,87 | 96 ay | 5.000 TL alışveriş çeki | Belirtilmemiş | Belirtilmemiş |

Bu format, [[bilgi-cikarimi]]'nın çıktısı, [[urun-karsilastirma]]'nın ve
[[dashboard]]/[[chatbot]] sunumunun girdisidir.

## Sources
- [[2026-06-16-teknofest-tyda-sartname-2-senaryo]] — Amaç (s.3), 5.3 (s.7),
  Örnek Senaryo-1 tablosu (s.12)

## Related
- [[bilgi-cikarimi]] — üreten süreç
- [[veri-normalizasyonu]] — değer standartlaştırma
- [[urun-karsilastirma]] — tüketen süreç
- [[yapilandirilmis-veri-formati-zorunlulugu]] — bu formata dönüştürme kararı
