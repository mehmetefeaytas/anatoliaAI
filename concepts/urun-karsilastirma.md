---
title: "Ürün Karşılaştırma"
tags: [concept, analiz, karsilastirma]
source: "[[2026-06-16-teknofest-tyda-sartname-2-senaryo]]"
date: 2026-06-16
status: stable
---

# Ürün Karşılaştırma

Çıkarılan finansal bilgiler kullanılarak farklı katılım bankalarına ait ürünlerin
karşılaştırılabilir hale getirilmesi (şartname 5.7, s.9). Çözümün **iş değerini**
üreten son analiz adımı.

Örnek karşılaştırma kriterleri (şartname 5.7, s.10):

- En Düşük [[kar-payi-orani]]
- En Yüksek Ödül Miktarı
- En Uzun Vade Seçeneği
- En Düşük Masraf
- En Avantajlı Kampanya

- Sonuçlar **tablo veya liste** biçiminde sunulabilir; [[dashboard]] ve
  [[chatbot]] üzerinden kullanıcıya verilir.
- **"En Düşük Masraf" kriteri tek sayıya indirilemez.** Ölçüldü: bankaların ilan
  ettiği tahsis ücreti kayıtlarının 30/33'ü tam olarak %0,5 (BDDK üst sınırı),
  ama kampanyalar bundan **koşullu** muafiyet veriyor. Tabloda "masrafsız"
  yazmak koşulu sağlamayan kullanıcıyı yanıltır; doğru gösterim koşullu
  ifadedir → [[masrafsizlik-celiskisi-kapsam-testi]].
- Doğru karşılaştırma, [[veri-normalizasyonu]] ve
  [[yapilandirilmis-veri-formati]]'na bağımlıdır.
- [[manuel-karsilastirma-zorlugu]] sorununun çözümüdür.

## Sources
- [[2026-06-16-teknofest-tyda-sartname-2-senaryo]] — 5.7 (s.9–10), Örnek
  Senaryo-2 (s.13)

## Related
- [[yapilandirilmis-veri-formati]] — girdi
- [[veri-normalizasyonu]] — ön koşul
- [[manuel-karsilastirma-zorlugu]] — çözdüğü sorun
- [[dashboard]], [[chatbot]] — sunum
- [[masrafsizlik-celiskisi-kapsam-testi]] — "En Düşük Masraf" nasıl hesaplanır
