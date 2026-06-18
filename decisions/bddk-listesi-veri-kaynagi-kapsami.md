---
title: "Karar: Veri kaynağı kapsamı = BDDK katılım bankaları listesi"
tags: [decision, veri, kapsam]
source: "[[2026-06-16-teknofest-tyda-sartname-2-senaryo]]"
date: 2026-06-16
status: stable
---

# Karar: Veri kaynağı kapsamı = BDDK katılım bankaları listesi

**Karar:** Veri seti kapsamı, [[bddk]]'nın resmî listesinde
(https://www.bddk.org.tr/Kurulus/Liste/77) yer alan **tüm** katılım bankalarını
içerir; veri her bankanın resmî web sitesinden toplanır.

**Gerekçe (şartname dayanağı):** 5.1 Veri Toplama: "Veri seti BDDK'nın resmî web
sitesinde yer alan Katılım Bankacılığı alanında faaliyet gösteren kuruluşların
tümünü içermelidir." (s.6)

**Etkileri:**
- Eksiksiz kapsam, "fonksiyonellik ve senaryo kapsamı" (%20) puanını etkiler (s.15).
- Toplama yöntemi → [[python-tabanli-veri-toplama]].

## Sources
- [[2026-06-16-teknofest-tyda-sartname-2-senaryo]] — 5.1 Veri Toplama (s.6)

## Related
- [[bddk]] — liste kaynağı
- [[katilim-bankalari]] — hedef küme
- [[python-tabanli-veri-toplama]] — toplama yöntemi
