# Round1 Hazırlık Kartı — Anotatör A

> `scripts/calisma_listesi.py` üretti. Elle düzenlemeyin; yeniden
> koşuda üzerine yazılır. Betik CSV'lere **yazmaz**, yalnız okur.

## Kalibrasyona GERİ DÖNMÜYORSUNUZ

`round0_kalibrasyon_*` bir kalibrasyon turuydu, gold değil. İşi ekibi
hizalamaktı ve onu yaptı: dört kural çıktı (kılavuz §4 K1–K4).
**O dosya yeniden etiketlenmeyecek.**

Sizin açacağınız dosya: **`round1_A.csv`** — 650 satır, 50 belge.
Kılavuz §8'in kendi hızıyla (**260 satır ≈ 25 dk**) kabaca **62 dakika**. Bu ölçüm değil,
kılavuzdaki orandan türetmedir; ilk 50 satır daha yavaş gider.

## Kalibrasyonda ne yaptınız

Açık kararınız: **79/260** (%30). 'Açık karar' = dolu `verdict` **ya da** dolu
`gold_value` (kılavuz §3.2: yazılmış düzeltme karardır).

> Round1'de boş hücre **v2 protokolündedir**: onay değil,
> "karar verilmedi" demektir ve satır gold'a HİÇ girmez.
> Kapsama düşer ama doğruluk şişmez — `lint` boş `verdict`i
> HATA sayar ve dosyayı `build_gold` öncesi durdurur.

## Kendi hata kalıplarınız — kalibrasyonda ÖLÇÜLDÜ

**22 ayrık hücre**, 3 kalıpta. Kaynak: `round0_kalibrasyon_A.csv.yedek-hakemlik`
(hakemlik ÖNCESİ — sizin gerçekten yazdığınız hâli).

| # | Kalıp | Hücre | Doğrusu | Kural |
|---:|---|---:|---|---|
| 1 | Model boş bırakmışken `absent` yazmak | **18** | `ok` yazın — `absent` yalnız modelin ÜRETTİĞİ değeri reddetmek içindir. Model bir şey üretmediyse reddedilecek bir şey yok. | kılavuz §3.3 kutusu |
| 2 | "taksit" geçmeyen belgede `taksit_sayisi` doldurmak | **3** | Belgede "taksit" kelimesi yoksa o sayı VADEDİR → `vade_ay`. `taksit_sayisi` `absent` olur. | kılavuz §4 kelime testi |
| 3 | Kanonik değer yerine metinden alıntı | **1** | `48` yazın, `"en fazla 48 aya kadar"` değil. Aralık gerekiyorsa `{"min": 12, "max": 48}`. | kılavuz §5 |

### Kendi satırlarınızdan örnek

1. **Model boş bırakmışken `absent` yazmak** — `finansman_tutari` = absent · `taksit_sayisi` = absent · `indirim_orani` = absent
2. **"taksit" geçmeyen belgede `taksit_sayisi` doldurmak** — `taksit_sayisi` = 36 · `taksit_sayisi` = 48 · `taksit_sayisi` = 36
3. **Kanonik değer yerine metinden alıntı** — `tahsis_ucreti` = Tahsis Ücreti yok {"rate": 0.0}

## Round1'e başlamadan

1. `_ANA-TUR-TALIMATI.md` — iki dakika, tek sayfa.
2. Yukarıdaki tabloyu bir kez okuyun. Bunlar sizin kalıplarınız;
   round1 dört kat büyük, aynı kalıp dört kat maliyet demek.
3. İlk 20 satırı doldurduktan sonra `lint`i koşun — kalıp hâlâ
   sürüyorsa 20 satırda görün, 600 satırda değil:

```bash
.venv/bin/python -m scripts.lint_review_csv \
    data/gold/review/round1_A.csv
```

## Takıldığınızda

- Biçim: `_bicim-karti.md` · Kural: `../ANNOTATION_GUIDE.md`
- Belgenin tam metni: `belgeler/<doc_id>.txt`
- Emin değilseniz **tahmin etmeyin** — `unclear` yazın (kılavuz §3.4).
- Kılavuz vakayı cevaplamıyorsa bu bir kılavuz kusurudur: söyleyin.

## Üreten komut

```bash
.venv/bin/python -m scripts.calisma_listesi
```
