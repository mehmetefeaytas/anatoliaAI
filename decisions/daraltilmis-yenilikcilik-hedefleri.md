---
title: "Karar: Yenilikçilik 3 hedefe daraltıldı (trend/çift dil çıkarıldı)"
tags: [decision, yenilikcilik, kapsam]
source: "[[2026-06-16-teknofest-tyda-sartname-2-senaryo]]"
date: 2026-06-16
status: stable
---

# Karar: Yenilikçilik 3 hedefe daraltıldı (trend/çift dil çıkarıldı)

**Karar:** Yenilikçilik bütçesi dağıtılmaz; üç hedefe yığılır:
1. Alan bazlı **güven skoru + kaynak vurgulama** (açıklanabilirlik),
2. **Bankalar arası çelişki tespiti** ("masrafsız" deyip tahsis ücreti alan
   kampanyayı yakalama),
3. **Config-driven banka onboarding** (`config/banks.yaml` ile tek satırda yeni banka).

Trend analizi ve TR/EN çift dilli chatbot **kapsam dışı** bırakılır.

**Gerekçe:** Yenilikçilik ağırlığı %10; dağıtılan çok sayıda yarım özellik yerine az
sayıda tamamlanmış, jüride güçlü etki yapan özellik daha yüksek puan getirir. Çelişki
tespiti doğrudan [[manuel-karsilastirma-zorlugu]] ve [[farkli-ifade-bicimleri]]
sorunlarına değer katar; güven+kaynak vurgulama halüsinasyon yasağını görünür kılar.

**Etkileri:**
- Geliştirme eforu çekirdek doğruluğa (%30) ve uçtan uca çalışmaya odaklanır.
- Çelişki tespiti [[urun-karsilastirma]] motoruna ek bir kontrol katmanı ekler.

## Sources
- [[2026-06-16-teknofest-tyda-sartname-2-senaryo]] — Değerlendirme / Yenilikçilik
  (%10) ağırlığı

## Related
- [[urun-karsilastirma]] — çelişki tespitinin dayandığı motor
- [[manuel-karsilastirma-zorlugu]] — değer katılan sorun
- [[teknik-cozum-mimarisi]] — mimari sentez
