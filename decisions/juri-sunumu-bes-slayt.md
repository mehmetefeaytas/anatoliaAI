---
title: Jüri sunumu 15 slayttan 5 slayta indirildi
tags: [karar, sunum, juri, sartname, teslim]
source: "log.md — [2026-08-21] karar | jüri sunumu 15 slayttan 5 slayta indirildi"
date: 2026-08-21
status: stable
---

# Jüri sunumu 15 slayttan 5 slayta indirildi

**Karar:** Şartname §10 sunum süresini **4 dakika** verir. 16 Ağustos'ta
üretilen 15 slaytlık sunum bu sürede sunulamıyordu; sahnede konuşulan bir ikna
metni değil, okunan bir savunma dokümanı gibi davranıyordu. Yerine yönetici
seviyesinde **5 slaytlık** bir sunum yazıldı (hedef kitle karma: teknik jüri +
katılım bankacılığı uzmanları + banka yöneticileri).

**Eski sürüm silinmedi** (HARD RULE 3):
`app/docs/archive/sunum-15-slayt-2026-08-21.html` olarak arşivlendi; başında
neden arşivlendiği ve bilinen sapmaları yazılıdır. Savunma derinliği (κ
asimetrisi, ölçüp geri adım atılan kararlar, halüsinasyon payda tanımı)
konuşmacı notlarındaki jüri soru bankasına taşındı.

## Ölçülüp düzeltilen sapmalar

| Sapma | Kanıt | Ne yapıldı |
|---|---|---|
| Eski deck slayt 03 manşeti **%3,9** diyordu, kendi kanıt satırı 146/2.708 | 146/2708 = **%5,4** | yeni deck %5,4 yazıyor |
| Ekran kareleri **1.774 belge** rozetiyle bayattı (12 Ağu çekimi) | `data/demo.db` bugün **2.708** belge | kareler canlı arayüzden 2.708 rozetiyle yeniden çekildi |
| «Sıradaki» denen tam yığın ağsız kanıtı aslında kazanılmıştı | **3/3 koşum · 39/39 adım** ölçülmüş | yeni deck kazanılmış kanıt olarak yazıyor |

## Sources
- log.md — [2026-08-21] karar | jüri sunumu 15 slayttan 5 slayta indirildi

## Related
- [[turkce-buyuk-harf-yerel-duyarliligi]] — bu sunum çalışması sırasında bulunan
  ve kapatılan Türkçe `text-transform:uppercase` hatası
- [[sunum-slayt-sigdirma-olcek-cokusu]] — bu sunum çalışması sırasında bulunan
  ve kapatılan slayt sığdırma / ölçek çöküşü sorunu
- [[next-dev-proxy-econnreset-yanlis-alarmi]] — ekran çekimi sırasında görülen
  «Sunucu 500» yanlış alarmı
