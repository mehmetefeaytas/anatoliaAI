---
title: Sunum slayt sığdırma — ölçek çöküşü
tags: [sorun, sunum, tipografi, yerlesim]
source: "log.md — [2026-08-21] karar | jüri sunumu 15 slayttan 5 slayta indirildi"
date: 2026-08-21
status: stable
---

# Sunum slayt sığdırma — ölçek çöküşü

**Kök neden:** `uret-sunum.py` taşan slaytı tek katsayıyla küçültüyor. 5 slaytlık
yeni sunumun ilk taslağında beş slaytın beşi de taşıyordu ve ölçek **0,75'e
kadar** düşüyordu — tipografi okunmaz oluyordu.

**Çözüm:** İçerik, beş slayt da **1080px'e kendi başına** sığana kadar
sıkıştırıldı (taşma raporu boş). Tasarım sistemine üç yoğun yerleşim
değiştiricisi eklendi: `.zaman.sik`, `.akis.dar`, `.kart.sik`. `uret-sunum.py`
betiğinin kendisi değiştirilmedi.

## Sources
- log.md — [2026-08-21] karar | jüri sunumu 15 slayttan 5 slayta indirildi

## Related
- [[juri-sunumu-bes-slayt]] — sorunun ortaya çıktığı ve kapatıldığı sunum
  çalışması
