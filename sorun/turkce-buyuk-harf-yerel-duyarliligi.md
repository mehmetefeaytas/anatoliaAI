---
title: Türkçe büyük harf — text-transform yerel duyarlılığı
tags: [sorun, turkce, tipografi, sunum, html-lang]
source: "log.md — [2026-08-21] karar | jüri sunumu 15 slayttan 5 slayta indirildi"
date: 2026-08-21
status: stable
---

# Türkçe büyük harf — `text-transform:uppercase` yerel duyarlılığı

**Kök neden:** Sunum HTML'i `<meta charset>` ile başlıyordu; örtük `<html>`
öğesinin `lang` niteliği yoktu. CSS `text-transform:uppercase` yerel-duyarlı
(locale-sensitive) olduğundan, dil bilgisi olmayan tarayıcı i→I eşlemesini
Türkçe kuralla (i→İ) yapmadı ve mono etiketler «ÜRETIMDE», «BIÇIM VARYANTI»,
«KURUM IÇINDE» gibi noktasız-İ hatalarıyla basıldı.

**Çözüm:** Deck'in kendi betiği artık `kok.lang = "tr"` atıyor; PDF/PPTX
çıktıları da doğru eşlemeyi alıyor.

**Not:** Arşivlenen 15 slaytlık sürümde
(`app/docs/archive/sunum-15-slayt-2026-08-21.html`) bu hata **bilinçli olarak
duruyor** — arşiv değişmezdir.

Bu sorun, log.md'deki `[2026-07-27] sorun+kod | Gün 1: Türkçe küçük-harf hatası
(H1)` girişiyle aynı ailedendir: orada Python `str.lower()` Türkçe I/İ eşlemesini
bozuyordu, burada CSS `uppercase` aynı eşlemeyi ters yönde bozdu. İki hata da
büyük/küçük harf dönüşümünün yerel (locale) bilgisi olmadan yapılmasından doğdu.
(O girişin `sorun/` altında ayrı sayfası yok; kayıt log.md'dedir.)

## Sources
- log.md — [2026-08-21] karar | jüri sunumu 15 slayttan 5 slayta indirildi
- log.md — [2026-07-27] sorun+kod | Gün 1: Türkçe küçük-harf hatası (H1) —
  aynı aileden önceki vaka

## Related
- [[juri-sunumu-bes-slayt]] — hatanın bulunduğu ve kapatıldığı sunum çalışması
