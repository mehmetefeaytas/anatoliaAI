---
title: "Sorun: gold.round1.json derleme komutu belgesizdi (ÇÖZÜLDÜ)"
tags: [sorun, gold, tekrar-uretilebilirlik, olcum, cozuldu]
date: 2026-08-21
status: stable
---

# Sorun: `gold.round1.json` derleme komutu belgesizdi

> **DÜZELTME (2026-08-21, aynı gün).** Bu sayfa ilk hâlinde *"gold kaynaktan
> yeniden üretilemiyor"* diyordu. **Teşhis yanlıştı.** Gold üretilebiliyor;
> eksik olan hangi ön-anotasyon havuzunun kullanıldığı bilgisiydi. Yanlış
> teşhisi silmiyorum — nasıl düzeltildiği aşağıda, çünkü yanlış bir kusur
> kaydı da bir kayıttır.

**İlk belirti.** Ölçümün referansı olan `app/data/gold/gold.round1.json` 134
kayıt taşıyor. Dört anotasyon CSV'sinden derleme yalnız **57** kayıt veriyordu:

```bash
# EKSİK KOMUT — 57 kayıt verir
.venv/bin/python -m scripts.build_gold \
  --csv data/gold/review/round1_A.csv --csv data/gold/review/round1_B.csv \
  --csv data/gold/review/round1_main_C.csv --csv data/gold/review/round1_main_D.csv \
  --out /tmp/deneme.json
```

Bundan "yeniden üretilemiyor" sonucunu çıkardım. Yanlıştı: `--pre` varsayılanı
`data/gold/preannotations.json`'dır ve round1 o havuzdan değil **`.v2`**
havuzundan üretilmişti.

**Kök neden.** `build_gold` bir kayıt üretmek için hem CSV satırını hem
ön-anotasyon havuzundaki belgeyi ister; havuz eşleşmeyince kayıt sessizce
düşer. Depoda dört havuz var (`preannotations.json`, `.v2`, `.v3`, `.zor`) ve
hangisinin hangi gold'u ürettiği **hiçbir yerde yazılı değildi**.

**Doğru komut — ölçüldü, 134 kayıt veriyor:**

```bash
cd app && .venv/bin/python -m scripts.build_gold \
  --pre data/gold/preannotations.v2.json \
  --csv data/gold/review/round1_A.csv --csv data/gold/review/round1_B.csv \
  --csv data/gold/review/round1_main_C.csv --csv data/gold/review/round1_main_D.csv \
  --out /tmp/gold-round1-yeniden.json
# -> kayıt: 134
```

**Nasıl bulundu.** Ben bulamadım; 4. tur Teknik Mimari jürisi buldu. Ben üç
kombinasyon deneyip (`--pre` varsayılan, `--csv-dir`, beşinci CSV) 57'de
kalınca kusur ilan etmişim. Jüri dördüncü havuzu deneyip 134'e ulaşmış. Ders
açık: "yeniden üretilemiyor" demek için tüketilmesi gereken arama uzayı, benim
tükettiğimden büyüktü.

## Kararlar artık CSV'lerde — tahkim kaynağa taşındı

İkinci ve gerçek boşluk şuydu: HAKEM-05 ve S1 kararları (23 + 4) doğrudan
`gold.round1.json`'a uygulanmıştı, kaynak CSV'lere işlenmemişti. Yani gold
kaynaktan üretilse tahkim kaybolurdu.

Kararlar CSV'lere yazıldı — **27 satır**: 22'si mevcut satırın `verdict`/
`gold_value` alanını değiştirdi, **5'i yeni satır olarak eklendi**. Beş satır
eklenmesinin sebebi kayda değer: o belgelerde `finansman_tutari` inceleme
kuyruğuna hiç girmemişti, çünkü model o alanda bir şey üretmemişti. Kuyruk
model çıktısına göre kurulduğu için, modelin görmediği bir alanda anotatörün
kararı kaydedilecek yer yoktu. Şimdi var.

**Ölçülen sonuç:** doğru komutla derleme 134 kayıt veriyor ve `finansman_tutari`
kararlarının **tamamı** yeniden üretimde görünüyor.

## Kalan fark — gizlenmiyor

Yeniden üretilen gold ile teslim edilen gold 134 kayıtta aynı kararları
taşıyor ama **birebir aynı dosya değil**. Fark kanıt alıntılarında: yeniden
üretim `field_spans`'ı CSV'nin `snippet` kolonundan alıyor, teslim edilen
dosyada bazı alıntılar metinden birebir dilimlenmiş. Ölçüldü: yeniden üretimde
kanıtsız (`span_supports` başarısız) hücre **18**, teslim edilende **15**.

Bu yüzden teslim edilen JSON *artefakt*, yeniden üretim *denetim yolu* olarak
duruyor. Karar denetlenebilir; alıntı kalitesi teslim edilende daha iyi.

## Yol boyunca bulunan kendi hatam

S1 kararlarını uygulayan betiğimde `r.setdefault("fields", {}) or {}` yazmışım.
`fields` boş sözlükse `or` **yeni ve kopuk** bir sözlük döndürüyor; yazılan
değer kayboluyor. Dört S1 hücresinden üçü başka alanlar da taşıdığı için
tuttu, `lc-waikiki` kaydının `fields`'ı boş olduğu için düştü.

Bunun ölçüme maliyeti vardı ve bir denetim onu "support daralması" diye
okumuştu: destek 22 → **17** görünüyordu. Hücre onarıldıktan sonra gerçek sayı
**18**. Yani daralmanın bir kısmı tahkim değil, benim hatamdı.

  `finansman_tutari` F1 1,000 · TP 18 · FP 0 · FN 0 · destek 18 (öncesi 22)
  round1 manşet mikro-F1 0,795 · halüsinasyon 0,284

## Açık kalan

Derleme komutu artık belgeli ama **bir kapıya bağlı değil**: `kanit_tazeligi`
`gold_round1_kayit` iddiasını (134) ölçüyor, *kaynaktan üretilebilirliği*
ölçmüyor. Bir test derlemeyi koşup kayıt sayısını ve `finansman_tutari`
kararlarını karşılaştırmalı. Yapılmadı; çevrimiçi süreç 26 Ağustos'ta bitiyor
ve bu test derleme başına ~1 dakika ekliyor.

## Sources
- 4. tur Teknik Mimari jürisi — `--pre data/gold/preannotations.v2.json`
  bulgusu; bu sayfanın ilk teşhisini çürüten ölçüm
- `app/data/gold/review/_hakem-turu-05-finansman-tutari-round1.md` — CSV'lere
  taşınan 27 kararın kaynağı

## Related
- [[standart-veri-formati-eksikligi]] — aynı ailedeki veri disiplini sorunu
