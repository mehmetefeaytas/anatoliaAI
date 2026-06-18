---
title: "Sorun: Ürünlerin manuel karşılaştırılmasının zorluğu"
tags: [sorun, kullanici, karsilastirma]
source: "[[2026-06-16-teknofest-tyda-sartname-2-senaryo]]"
date: 2026-06-16
status: stable
---

# Sorun: Ürünlerin manuel karşılaştırılmasının zorluğu

**Belirti:** Kullanıcılar/banka çalışanları, en uygun ürünü bulmak için çok sayıda
kampanya metnini elle incelemek zorunda kalır; karar süreci uzar (şartname Giriş
s.2, Problem Tanımı s.5).

**Kök neden:** [[standart-veri-formati-eksikligi]] +
[[katilim-bankaciligi-terminoloji-farkliligi]] +
[[farkli-ifade-bicimleri]] birleşimi → otomatik kıyas yapılamaması.

**Etki:** Yavaş ve hataya açık karar verme; iş verimsizliği.

**Çözüm (fix):** Uçtan uca NLP hattı — toplama → çıkarım → normalizasyon →
[[urun-karsilastirma]] — ve sonuçların [[dashboard]] / [[chatbot]] ile sunumu.
Şartmenin temel iş hedefi budur (Amaç, s.3).

## Sources
- [[2026-06-16-teknofest-tyda-sartname-2-senaryo]] — Giriş (s.2), Problem Tanımı
  (s.5), Amaç (s.3)

## Related
- [[urun-karsilastirma]] — çözüm
- [[standart-veri-formati-eksikligi]], [[farkli-ifade-bicimleri]] — kök sorunlar
- [[dashboard]], [[chatbot]] — sunum
