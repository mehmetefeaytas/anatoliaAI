---
title: "Kalem düzeyinde puanlama — ikili ölçüt neyi gizliyordu"
tags: [olcum, metrik, kampanya-kosullari]
date: 2026-08-08
status: stable
---

# Kalem düzeyinde puanlama (2026-08-08)

> **Bu bir ÖLÇÜM değişikliğidir, sistem değişikliği değildir.** Hiçbir çıkarım
> kuralı değişmedi; yalnız liste alanlarının nasıl sayıldığı değişti. İki sayı
> yan yana yayımlanır, ikili ölçüt manşet sayı olarak kalır.

## Sorun

`eval/matchers.py::_list_equal` **küme eşitliği** arıyor. Beş koşuldan dördü
doğru çıkarılsa bile sonuç TP=0, FP=1, FN=1 olur — yani "%80 doğru" ile
"tamamen yanlış" aynı puanı alır.

Ölçüldü (gold.v2, n=48, `kural`): `kampanya_kosullari` **her iki
eşleştiricide de tam olarak 0,000**. `strict` ve `tolerant` birebir aynı
TP/FP/FN üretiyor. Yani sorun toleransta değil, **ölçütün ikili olmasında**.

| ölçüt | TP | FP | FN | F1 |
|---|---:|---:|---:|---:|
| ikili (küme eşitliği) | **0** | 36 | 33 | **0,000** |
| kalem düzeyi (Jaccard ≥ 0,7) | **27** | 109 | 110 | **0,198** |

## Yöntem

Serbest metin kalemleri **jeton-Jaccard** ile eşleşir; eşleştirme **açgözlü ve
1-1**'dir — bir tahmin kalemi iki gold kalemini birden karşılayamaz, aksi
halde tek bir uzun cümle tüm koşulları "karşılıyor" görünürdü.

Etiket listeleri (`hedef_kitle`) **birebir** eşleşir: *KOBİ* ile *KOBİ
sahipleri* farklı hedef kitlelerdir, jeton örtüşmesi onları birleştirirdi.

**Eşik 0,70 anotasyondan önce ilan edilmiştir** ve sonuca bakılarak
değiştirilmemiştir. Duyarlılık:

| eşik | `kampanya_kosullari` F1 | TP | mikro-F1 | makro-F1 |
|---:|---:|---:|---:|---:|
| 0,5 | 0,242 | 33 | 0,364 | 0,438 |
| 0,6 | 0,234 | 32 | 0,360 | 0,437 |
| **0,7** | **0,198** | **27** | **0,338** | **0,434** |
| 0,8 | 0,176 | 24 | 0,325 | 0,432 |
| 0,9 | 0,168 | 23 | 0,320 | 0,431 |
| 1,0 (birebir) | 0,154 | 21 | 0,311 | 0,430 |

Monoton, uçurum yok. Birebir eşleşmede bile **21 koşul** tutuyor — yani sistem
gerçekten koşul metni çıkarıyor, ölçüt onu görmüyordu.

## Sonuç — beklenenin TERSİ çıktı

Planlarken bu düzeltmenin manşet mikro-F1'i **yükselteceği** varsayılmıştı.
Ölçüm bunu yanlışladı:

| ölçüt | mikro-F1 | makro-F1 |
|---|---:|---:|
| ikili (manşet) | **0,389** | 0,409 |
| kalem düzeyi | **0,338** | 0,434 |

**Mikro düşüyor, makro yükseliyor.** İkisi de doğru ve mekanizma tek:

- **Makro yükseliyor** çünkü alan artık 0,000 değil 0,198. Alan bazlı resim
  gerçekten daha iyi.
- **Mikro düşüyor** çünkü ikili ölçüt her belgenin katkısını **1 FP + 1 FN ile
  sınırlıyordu**. Gerçekte 48 belgede ~137 gold kalemi ve ~136 tahmin kalemi
  var. Kalem düzeyi bu hacmi görünür kılıyor ve alan kötü performans
  gösterdiği için mikro ortalamada çok daha ağır basıyor.

Yani ikili ölçüt bu alanda **iki yönlü yanlıştı**: alan F1'ini olduğundan kötü
(0,000), toplam mikro-F1'i olduğundan **iyi** gösteriyordu. İkincisi lehimize
sapan bir kör noktadır ve `macro_f1_uydurma_dahil` ile bulunan kusurla aynı
sınıftandır.

## Jüriye nasıl sunulur

Manşet sayı **ikili ölçütün 0,389'u** olarak kalır — geçmiş tüm koşumlar,
ablasyon tabloları ve McNemar testleri ona dayanıyor; yerinde değiştirmek her
geriye dönük karşılaştırmayı sessizce geçersiz kılardı.

Kalem düzeyi sayı yanında durur ve iki şey söyler:
1. `kampanya_kosullari` gerçekten sıfır değil — %20 civarı kalem tutuyor.
2. Manşet mikro-F1 bu alanda **iyimserdi**; dürüst hacimle 0,338.

## Yeniden üretim

```bash
.venv/bin/python -m eval.run_eval --gold data/gold/gold.v2.json --config kural
.venv/bin/python -m eval.run_eval --gold data/gold/gold.v2.json --config kural \
    --kalem-esik 0.6      # duyarlılık
```

`n=48` uyarısı bu tablonun her satırında geçerlidir; gold.v2 makine
anotasyonludur (`adjudicated: false`) ve κ henüz ölçülmemiştir.

## Sources
- `eval/reports/20260808-181215/metrics.json` (ikili + kalem, iki eşleştirici)
- `eval/matchers.py::item_counts` · `eval/run_eval.py::aggregate_item`
- `tests/test_kalem_duzeyi_puanlama.py` (13 test)

## Related
- [[olcumler]] — manşet metrikler
- [[genel-denetim]] — hakemlerin ortak önceliği (2. madde)
- [[gold-genisletme]] — gold.v2'nin statüsü ve n=48 uyarısı
