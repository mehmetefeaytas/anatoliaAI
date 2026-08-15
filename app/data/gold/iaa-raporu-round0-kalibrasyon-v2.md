# Anotatörler Arası Uyum (IAA) Raporu

> `scripts/report_iaa.py` üretti. Eşik politikası anotasyon BAŞLAMADAN ilan edilmiştir (ANNOTATION_GUIDE.md §7); sayılara bakıp eşik değiştirmek yasaktır.

- **Tur: `round0-kalibrasyon-v2`**
- Anotatörler: v2_A, v2_B, v2_C, v2_D
- Ortak anote edilmiş satır: **260**
- Karar bulunmayan hücre (boş/eksik): **1040**

## Protokol künyesi

| Dosya | Protokol | Boş hücrenin anlamı |
|---|---|---|
| `data/gold/review/round0_kalibrasyon_v2_A.csv` | **v2** | karar verilmedi — metrik dışı |
| `data/gold/review/round0_kalibrasyon_v2_B.csv` | **v2** | karar verilmedi — metrik dışı |
| `data/gold/review/round0_kalibrasyon_v2_C.csv` | **v2** | karar verilmedi — metrik dışı |
| `data/gold/review/round0_kalibrasyon_v2_D.csv` | **v2** | karar verilmedi — metrik dışı |

## Sonuçlar

| Ölçüt | Neyi ölçer | Değer |
|---|---|---:|
| Fleiss' kappa (karar) | Aynı satırda aynı kararı mı verdiler (ok/fix/absent/unclear) | **ölçülemedi** |
| Krippendorff α (nominal) | Ortaya çıkan gold DEĞERİ birebir aynı mı | ölçülemedi |
| Krippendorff α (ratio) | Sayısal alanlarda değer yakınlığı (0 birim) | ölçülemedi |

## Karar (önceden ilan edilmiş eşik)

- **Durum: `olcusuz`**
- Yapılacak: Ortak anote edilmiş birim yok; çift anotasyon alt kümesi gerçekten paylaşıldı mı kontrol et.

| Eşik | Karar |
|---|---|
| κ ≥ 0,80 | kabul |
| 0,67 ≤ κ < 0,80 | notla kabul |
| κ < 0,67 | zorunlu hakemlik + kılavuz revizyonu |

## Uyuşmazlıklar (0)

_Tam uyum._
