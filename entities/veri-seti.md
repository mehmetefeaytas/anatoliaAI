---
title: "Veri Seti (Kampanya/Ürün Metinleri)"
tags: [entity, veri, artifact]
source: "[[2026-06-16-teknofest-tyda-sartname-2-senaryo]]"
date: 2026-06-16
status: stable
---

# Veri Seti (Kampanya/Ürün Metinleri)

Anatolia AI çözümünün üzerine kurulduğu veri kümesi: katılım bankalarının resmî
web sitelerinden toplanan finansman, kart ve yatırım ürünü kampanya metinleri.

- **Kapsam:** [[bddk]] listesindeki **tüm** katılım bankaları
  (https://www.bddk.org.tr/Kurulus/Liste/77) içerilmelidir (şartname s.6).
- **Toplama yöntemi:** Python tabanlı araçlar/kütüphaneler, [[web-scraping]] veya
  manuel toplama (şartname s.6) → bkz. [[python-tabanli-veri-toplama]].
- **Teslim:** Veri setine herkese açık bir indirme bağlantısı [[github]] deposunda
  yer almalı (şartname s.18).
- Veri seti üzerinden [[bilgi-cikarimi]], [[metin-siniflandirma]] ve
  [[urun-karsilastirma]] işlemleri yapılır.

## Sources
- [[2026-06-16-teknofest-tyda-sartname-2-senaryo]] — Veri Toplama (s.6), Proje
  Bilgileri Sunumları (s.18)

## Related
- [[bddk]] — kapsam kaynağı
- [[katilim-bankalari]] — veri kaynağı bankalar
- [[web-scraping]] — toplama tekniği
- [[veri-on-isleme]] — toplama sonrası işlem
