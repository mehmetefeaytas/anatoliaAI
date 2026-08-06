---
title: "Karar: terim sözlüğü sisteme ENJEKTE edilir, terimler REPLACE edilmez"
tags: [decision, terminoloji, prompt, chatbot, mentor]
source: "[[2026-08-06-cavide-terim-sozlugu]]"
date: 2026-08-06
status: stable
---

# Karar: terim sözlüğü enjekte edilir, replace edilmez

**Karar:** Katılım finansı terminolojisi, yasak/karşılık tablosuyla **kör dize
değiştirme** yoluyla değil, **belgeye özel terim kartları** olarak sistem
prompt'una enjekte edilerek uygulanır. Yasak/karşılık tablosu bir *dönüşüm
kuralı* değil, yalnız bir *tespit hedefi* ve *öneri kaynağı* olarak kalır.

## Gerekçe

Mentör Cavide Hanım'ın 2026-08-06 tarihli maili ([[2026-08-06-cavide-terim-sozlugu]]):

> "Birebir değiştirmek anlamda bozukluk yaratıyor… Türkçeleri aynı anlamı
> replace ile taşımıyor. O sebeple böyle bir kapsamlı analiz vermek gerekiyor."

Bu bir dış görüş değil, **kendi ölçtüğümüz kusurun genellemesi**.
`app/src/chatbot/safety.py` KAPI 1 kök tabanlı değiştirme yapıyordu ve gerçek
korpusta çöktüğü nokta bulunmuştu: bankaların eğitim sayfaları iki kavramı
*karşılaştırıyor* —

    "Kâr Payı ile Faiz Arasındaki Farklar"

Kör değiştirme bunu "Kâr Payı ile Kâr Payı Arasındaki Farklar" yapıyordu.
`_CONTRAST_REPLACEMENTS` o **tek** vaka için yazılmıştı. Sözlüğün `degildir` ve
`ayrim_notu` alanları aynı sorunun **101 terimlik genel çözümüdür**.

## Sonuçları

- Sözlüğün tamamı prompt'a konulamaz: 76.200 karakter, bağlam penceresi
  ~25.000. Üstelik Ollama taşan bağlamı **baştan** kırpar ve sistem prompt'unu
  yok eder. Bu yüzden belgede **fiilen geçen** terimler seçilir
  (`relevant_terms`, deterministik, LLM yok).
- Kart alan sırası `kanonik → degildir → ayrim_notu → risk_notu`. `tanim` en
  sona düşer: modelin bilmediği tanım değil **ayrımdır**.
- Çıktı tarafı da bağlayıcı (mailin ikinci iddiası): cevapta "fon", "bono",
  "tahvil" kullanmak da yanlıştır. `output_violations` bunu `degildir`
  alanından türetir.
- `jargon_lint.py` **tespit eder, değiştirmez**; düzeltmeyi insana bırakır.

## ÇELİŞKİ — mentör belgesi ↔ mentör maili

Mentörlük aksiyon planının §2.3'ü bir *yasak/karşılık tablosu* istiyor ve
§6'daki D2 deneyi "terimi sadeleştirince doğruluk artar" hipotezini kuruyor.
Mail ikisinin de mekanizmasını reddediyor.

Çözüm otoriteyle değil **ölçümle**: D2 üç kollu bir deneye çevrildi —
temel / sadeleştirme / sözlük kartı. Kart enjeksiyonu bu yüzden
kapatılabilir (`LLMOrchestrator(terim_karti=False)`).

## Sources
- [[2026-08-06-cavide-terim-sozlugu]] — mailin tam metni ve sözlük şeması

## Related
- [[katilim-finans-terimleri]] — sözlüğün kavram sayfası
- [[katilim-bankaciligi-terminoloji-farkliligi]] — çözülen sorun
- [[orkestrasyon-yetki-asimetrisi]] — kartların enjekte edildiği yer
