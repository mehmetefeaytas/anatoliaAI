---
title: "Merkezî veri segment ayrımını gizliyor (TKBB tek oran, banka beş oran)"
tags: [sorun, veri-kalitesi, kar-payi, katilma-hesabi, tkbb, kuveyt-turk]
source: "[[tkbb-kar-payi-veri-seti]]"
date: 2026-08-24
status: stable
---

# Merkezî veri segment ayrımını gizliyor

## Belirti

TKBB, Kuveyt Türk TL katılma hesabı **kâr paylaşım oranını** tek bir değer
dizisi olarak yayınlıyor: **92 / 93 / 95 / 95** (1 / 3 / 6 / 12 ay).

Bankanın kendi PDF'i ise aynı oranı **bakiye segmenti** bazında veriyor:

| segment | 1 ay | 3 ay | 6 ay | 12 ay |
|---|---|---|---|---|
| Klasik | 85 | 86 | 88 | 88 |
| Gümüş | 87 | 88 | 91 | 91 |
| Altın | 90 | 91 | 93 | 93 |
| Platin | 92 | 93 | 94 | 94 |
| Platin+ | 94 | 94 | 95 | 95 |
| **TKBB (tek değer)** | **92** | **93** | **95** | **95** |

## Bulgu

TKBB'nin dizisi **hiçbir segmente tam denk gelmiyor**: 1 ve 3 ay Platin'e,
6 ve 12 ay Platin+'a uyuyor. Yani merkezî veri, segmentlerin **en yüksek**
değerlerinden derlenmiş görünüyor.

Sonuç: **Klasik hesap müşterisi gerçekte %85 alıyor, merkezî veri %92 diyor.**
Küçük bakiyeli müşterinin gerçek oranı merkezî kaynakta görünmüyor.

Bu bir çelişki değil, **granülerlik kaybı** — ve gizlendiğinde çelişki gibi
sonuç üretiyor: "en iyi paylaşım oranını hangi banka veriyor" sorusu, hangi
segmentte olduğunuza göre değişir.

## Sonuç ne yapıldı

Banka PDF'i ayrıca hasat edildi (`scripts/kt_paylasim_pdf.py`, 144 kayıt) ve
`segment` alanıyla saklanıyor — `quotes.jsonl` şeması bu alanı zaten
taşıyordu. Böylece iki granülerlik yan yana duruyor ve hangisinin
kullanıldığı görünür.

**Chatbot şu an TKBB verisini kullanıyor** (dokuz bankayı birlikte kapsayan
tek kaynak). Segment ayrımı henüz cevaba girmiyor; bu açık bir sınır.

## Yan bulgu — kaynakta dizgi hatası

Aynı PDF'te **Gümüş Hesap "7-20 Gün"** sütunu `91-19` yazıyor; toplam
**110** ediyor, 100 olmalı (muhtemelen `81-19`). Değer **düzeltilmedi ve
atılmadı**: `toplam_tutarsiz: true` ile işaretlendi (CLAUDE.md HARD RULES §4
— çelişki gizlenmez). 144 kaydın 1'i bu durumda.

## İlgili dosyalar

- `app/scripts/kt_paylasim_pdf.py` — ayrıştırıcı ve tutarsızlık işareti
- `app/data/raw/kuveyt-turk/rates/kt-paylasim-pdf.jsonl` — 144 kayıt
- `app/tests/test_kt_paylasim_pdf.py` (15 test)

## Sources

- `https://www.kuveytturk.com.tr/mevduat-ve-yatirim/katilma-hesaplari` — banka PDF'i
- [[tkbb-kar-payi-veri-seti]] — merkezî kaynak

## Related

- [[katilma-orani-iki-ayri-buyukluk]] — getiri/pay ayrımı
- [[katilma-hesabi-orani-korpusta-yoktu]] — verinin geliş öyküsü
- [[urun-karsilastirma]] — adil kıyas garantisi
