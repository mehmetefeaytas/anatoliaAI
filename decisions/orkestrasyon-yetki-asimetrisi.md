---
title: "Karar: orkestrasyonda ajanlar önerir, hakem yalnız reddeder"
tags: [decision, llm, orkestrasyon, olcum, halusinasyon]
source: "[[2026-08-06-mentor-terim-sozlugu]]"
date: 2026-08-06
status: stable
---

# Karar: ajanlar önerir, hakem yalnız reddeder

**Karar:** Çok-ajanlı çıkarımda LLM ajanlarının **yazma yetkisi yoktur**.
Ajanlar yalnız *önerir*, hakem yalnız *reddeder*, reddedilen alan kural
katmanının değerine düşer. Hakem asla değer yazamaz, düzeltemez, alan ekleyemez.

## Gerekçe — ölçüm dayattı

`app/docs/rapor/ablasyon.md` (n=20, bootstrap 1000) hibrit kolun kural
kolundan **daha kötü** olduğunu ölçtü:

| kol | mikro-F1 | halüsinasyon |
|---|---|---|
| kural | 0,612 | 0,102 |
| hibrit | 0,575 | **0,163** |

Yani "LLM ekleyelim" refleksi bu projede ölçümle yanlışlanmış durumda. Daha
fazla LLM çağrısı eklemek, aynı regresyonu daha pahalıya yeniden üretmek
demekti.

Yetki asimetrisinin sonucu: **orkestrasyonun en kötü hâli kural-only'dir**,
yani bugünkü en iyi ölçülmüş kol. Hibrit kolun regresyonu artık yapısal olarak
tekrarlanamaz. `test_EN_KOTU_HAL_kural_only` bunu sabitler.

## Mekanik kapılar LLM oylarından ÖNCE

`app/src/extraction/silver/consensus.py`'deki desen taşındı: modelin beyanına
bakmayan kapılar önce çalışır.

- **kanıt kapısı** — alıntı metinde birebir yoksa öneri düşer.
- **kalem kapısı** — ücret alanında komşu kalem karışması düşer.

Kalem kapısı bir prompt yaması değil, bir ölçüm sonucudur: hakem beş kontrol
vakasının dördünü doğru bildi ama "Taşıt Rehin Tesis Ücreti 350,92 TL"
alıntısını `tahsis_ucreti` için KABUL etti. Aynı karışma ücret çapraz
denetiminde de ölçülmüş ve orada mekanik kapıyla çözülmüştü. Bilinen ve
sistematik bir hata için LLM'e güvenilmez.

## Hakem çökerse — fail-closed AMA sessiz değil

Tüm öneriler düşer ve sonuç kural-only olur. Bu doğru davranış ama tehlikeli
yan etkisi var: ablasyon tablosunda "orkestra" satırı sessizce "kural" satırına
dönüşürdü. Hata rapora yazılır, loglanır, katı modda yükselir.

## Rol ayrımı model düzeyinde DEĞİL

Mentör "basit alan küçük model, bağlamsal alan yetenekli model" önerdi.
Donanım (RTX 5060, 8 GB) iki 8B modeli aynı anda kaldırmıyor; ayrım **prompt ve
şema düzeyinde**. Bu sınır rapora yazılır, gizlenmez.

## Ölçüm kapısı

Orkestrasyon kural kolunu geçemezse `DEFAULT_CONFIG` **kural** kalır ve
orkestrasyon ablasyon tablosuna ölçülmüş bir satır olarak girer. Kazanan ilan
etmek için |Δ| ≥ 0,05 gerekir (n=20'de altı gürültüdür).

## Sources
- [[2026-08-06-mentor-terim-sozlugu]] — multi-agent + hakem önerisi

## Related
- [[terim-sozlugu-enjeksiyon-replace-degil]] — kartların enjekte edildiği yer
- [[zor-anlama-vakalari-merkezi]]
- [[demo-onceden-doldurulmus-db]] — LLM kritik yolda olmamalı ilkesi
