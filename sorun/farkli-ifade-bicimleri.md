---
title: "Sorun: Aynı değerin farklı ifade biçimleri"
tags: [sorun, veri, normalizasyon]
source: "[[2026-06-16-teknofest-tyda-sartname-2-senaryo]]"
date: 2026-06-16
status: stable
---

# Sorun: Aynı değerin farklı ifade biçimleri

**Belirti:** Aynı finansal değer metinlerde farklı yazılır:
`%2,05` / `% 2.05` / `2.05 %`; `500 TL` / `500₺` / `500 Türk Lirası`
(şartname 5.6, s.9).

**Kök neden:** Yazım/biçim standardizasyonu olmaması; ondalık ayraç (virgül/nokta),
boşluk ve birim gösterimi tutarsızlığı.

**Etki:** Doğrudan karşılaştırma yanlış sonuç verir; "en düşük kâr payı" gibi
kriterler ([[urun-karsilastirma]]) bozulur.

**Çözüm (fix):** [[veri-normalizasyonu]] — farklı formatlar tek standart değere
dönüştürülür; bu, [[bilgi-cikarimi]] sonrası uygulanan zorunlu adımdır.

## Sources
- [[2026-06-16-teknofest-tyda-sartname-2-senaryo]] — 5.6 (s.9)

## Related
- [[veri-normalizasyonu]] — çözüm
- [[kar-payi-orani]] — etkilenen alan
- [[standart-veri-formati-eksikligi]] — ilişkili sorun
