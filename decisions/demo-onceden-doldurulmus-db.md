---
title: "Karar: Demo önceden doldurulmuş DB'den okur, canlı LLM/scrape'e bağlı değil"
tags: [decision, demo, on-premise, sunum]
source: "[[2026-06-16-teknofest-tyda-sartname-2-senaryo]]"
date: 2026-06-16
status: stable
---

# Karar: Demo önceden doldurulmuş DB'den okur, canlı LLM/scrape'e bağlı değil

**Karar:** Demo videosu/sunumu **önceden scrape edilmiş + önceden çıkarımı yapılmış**
ve DB'ye yüklenmiş veriden okur. Canlı çalışmayı ispatlamak için **tek bir örnek**
üzerinde "canlı çıkarım" butonu bırakılır; gerisi cache'ten gösterilir.

**Gerekçe:** Demo videosunda dashboard ve chatbot gösterilmesi gerekir (s.14). 4
dakikalık sunumda yerel 8B LLM + canlı scraping **donma/zaman aşımı riski** taşır;
bu kritik yolu ortadan kaldırmak teslimi sağlamlaştırır ve
[[on-premise-calistirilabilir-mimari]] (%20) iddiasını güçlendirir (offline hazır
veri).

**Etkileri:**
- LLM kritik yolda olmaktan çıkar (ayrıca quantize + Ollama yedeği — bkz. mimari).
- Veri provenance (scrape timestamp + source_url) demo öncesi hazır olmalı.

## Sources
- [[2026-06-16-teknofest-tyda-sartname-2-senaryo]] — Tespit Edilmesi Gerekenler /
  demo videosu (s.14)

## Related
- [[on-premise-calistirilabilir-mimari]] — offline çalışma kararı
- [[dashboard-ve-chatbot-arayuzu]] — demoda gösterilen arayüzler
- [[teslim-ve-degerlendirme-rehberi]] — teslim sentezi
