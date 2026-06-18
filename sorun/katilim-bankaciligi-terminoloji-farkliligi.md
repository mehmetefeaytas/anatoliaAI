---
title: "Sorun: Katılım bankacılığı terminolojisinin farklılığı"
tags: [sorun, terminoloji, nlp]
source: "[[2026-06-16-teknofest-tyda-sartname-2-senaryo]]"
date: 2026-06-16
status: stable
---

# Sorun: Katılım bankacılığı terminolojisinin farklılığı

**Belirti:** [[katilim-bankaciligi]] terminolojisi hem konvansiyonel bankacılıktan
hem de bankadan bankaya farklıdır; aynı kavram farklı ifadelerle yazılır
(şartname Giriş s.2, Problem Tanımı s.5).

**Kök neden:** Faiz yerine [[kar-payi-orani]], kredi yerine finansman gibi
alana-özgü terimler + her bankanın kendi pazarlama dili.

**Etki:** Genel amaçlı NLP modelleri kavramları yanlış yorumlayabilir; çıkarım ve
sınıflandırma hatalı olur.

**Çözüm (fix):** Modelin terminolojiye uyum sağlaması (5.5, s.8): "%2,05 kâr payı
oranı", "avantajlı kâr payı fırsatı", "özel oranlı finansman" gibi farklı ifadeler
aynı kavrama eşlenir. Terim sözlüğü/kuralları + alan-uyarlı [[metin-siniflandirma]].

## Sources
- [[2026-06-16-teknofest-tyda-sartname-2-senaryo]] — Giriş (s.2), Problem Tanımı
  (s.5), 5.2 (s.7), 5.5 (s.8)

## Related
- [[katilim-bankaciligi]] — alan
- [[kar-payi-orani]] — tipik terim
- [[metin-siniflandirma]] — çözüm yeteneği
