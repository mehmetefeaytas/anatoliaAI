---
title: "Karar: 'Zor anlama' vakaları mimarinin merkezinde + ayrı gold alt kümesi"
tags: [decision, normalizasyon, model-basarisi, eval]
source: "[[2026-06-16-teknofest-tyda-sartname-2-senaryo]]"
date: 2026-06-16
status: stable
---

# Karar: 'Zor anlama' vakaları mimarinin merkezinde + ayrı gold alt kümesi

**Karar:** Normalizasyon ([[veri-normalizasyonu]]) ve çıkarım, zor anlama
vakalarını **açıkça** ele alır: aralık (`%1,99–%2,49`), zaman-koşullu oran (`ilk 6
ay %0`), aylık vs. yıllık baz, TR sayı formatı (`1.500,00`), negasyon (`masrafsız` =
masraf 0, "değer yok" değil). Gold sette ayrı bir **"zor vakalar" alt kümesi**
kürlenir ve ablasyonda hibridin **özellikle orada** kazandığı gösterilir.

**Gerekçe:** En yüksek ağırlık Model Başarısı ve Anlamlandırma'dır (%30); kriter
açıkça "farklı ifade biçimlerini doğru yorumlama, eksik/farklı yazılmış bilgide
doğru sonuç" der. Bu puan tam olarak [[farkli-ifade-bicimleri]] vakalarında
kazanılır; bunları ölçmeden iddia ispatlanamaz.

**Etkileri:**
- Ablasyon tablosu jüri için en ikna edici artefakt olur.
- [[veri-on-isleme]] ve normalizasyon sözlüğü bu vakaları kapsamak zorunda.
- Halüsinasyon yasağı (`null` döndür) negasyon vakalarında kritik.

## Sources
- [[2026-06-16-teknofest-tyda-sartname-2-senaryo]] — Değerlendirme / Model Başarısı
  (%30) tanımı

## Related
- [[farkli-ifade-bicimleri]] — hedef sorun
- [[veri-normalizasyonu]] — etkilenen yöntem
- [[veri-on-isleme]] — ön işleme bağlamı
- [[teknik-cozum-mimarisi]] — mimari sentez
