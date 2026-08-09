# Round1 Hazırlık Kartı — Anotatör D

> `scripts/calisma_listesi.py` üretti. Elle düzenlemeyin; yeniden
> koşuda üzerine yazılır. Betik CSV'lere **yazmaz**, yalnız okur.

## Kalibrasyona GERİ DÖNMÜYORSUNUZ

`round0_kalibrasyon_*` bir kalibrasyon turuydu, gold değil. İşi ekibi
hizalamaktı ve onu yaptı: dört kural çıktı (kılavuz §4 K1–K4).
**O dosya yeniden etiketlenmeyecek.**

Sizin açacağınız dosya: **`round1_main_D.csv`** — 572 satır, 90 belge.
Kılavuz §8'in kendi hızıyla (**260 satır ≈ 25 dk**) kabaca **55 dakika**. Bu ölçüm değil,
kılavuzdaki orandan türetmedir; ilk 50 satır daha yavaş gider.

## Kalibrasyonda ne yaptınız

Açık kararınız: **260/260** (%100). 'Açık karar' = dolu `verdict` **ya da** dolu
`gold_value` (kılavuz §3.2: yazılmış düzeltme karardır).

## Kendi hata kalıplarınız — kalibrasyonda ÖLÇÜLDÜ

**169 ayrık hücre**, 7 kalıpta. Kaynak: `round0_kalibrasyon_D.csv.yedek-hakemlik`
(hakemlik ÖNCESİ — sizin gerçekten yazdığınız hâli).

> Kalıp sayıları toplamı 278, ayrık hücre 169: bir hücre birden çok kalıba girebilir
> (ör. `gold_value`'ya belge açıklaması yazmak hem `absent-dolu-deger` hem `metinden-alinti`dir).

| # | Kalıp | Hücre | Doğrusu | Kural |
|---:|---|---:|---|---|
| 1 | Model boş bırakmışken `absent` yazmak | **134** | `ok` yazın — `absent` yalnız modelin ÜRETTİĞİ değeri reddetmek içindir. Model bir şey üretmediyse reddedilecek bir şey yok. | kılavuz §3.3 kutusu |
| 2 | `gold_value`'ya belgenin ne hakkında olduğunu yazmak | **69** | O sütun alanın DEĞERİ içindir, belgenin özeti değil. Değer yoksa hücre BOŞ kalır. `build_gold` açıklamayı sessizce atar. | kılavuz §5 |
| 3 | Kanonik değer yerine metinden alıntı | **45** | `48` yazın, `"en fazla 48 aya kadar"` değil. Aralık gerekiyorsa `{"min": 12, "max": 48}`. | kılavuz §5 |
| 4 | `hedef_kitle`ye serbest metin yazmak | **12** | Yalnız dört etiket: `yeni_musteri` · `mevcut_musteri` · `maas_musterisi` · `belirli_segment`. "Bireysel müşteriler" segment DEĞİLDİR (herkes demek) → `absent`. Cümleyi saklamak isterseniz `kampanya_k… | kılavuz §4 `hedef_kitle` |
| 5 | Tek değerli alana iki değer yazmak | **9** | Üst sınırı/bitişi yazın, diğerini `note`'a düşün. Ayrıştırıcı REDDETMEZ — ilk ucu alır, yani sessizce yanlış değer gold'a girer. | `_bicim-karti.md` |
| 6 | "taksit" geçmeyen belgede `taksit_sayisi` doldurmak | **7** | Belgede "taksit" kelimesi yoksa o sayı VADEDİR → `vade_ay`. `taksit_sayisi` `absent` olur. | kılavuz §4 kelime testi |
| 7 | 8 sınıf dışında `campaign_type` uydurmak | **2** | Sınıf kümesi SABİTTİR. Uymuyorsa `absent` — `null` bir hatanın değil bir kararın adıdır. | kılavuz §4.13/1 |

### Kendi satırlarınızdan örnek

1. **Model boş bırakmışken `absent` yazmak** — `tahsis_ucreti` = absent · `indirim_orani` = absent · `alisveris_puani` = absent
2. **`gold_value`'ya belgenin ne hakkında olduğunu yazmak** — `campaign_type` = Leasing Süreci ve Hesaplama Aracı · `kampanya_kosullari` = finansman · `kampanya_kosullari` = Finansman hesaplama aracı
3. **Kanonik değer yerine metinden alıntı** — `taksit_sayisi` = 3-6 taksit · `kar_payi_orani` = 1.6899999999999998E-2 · `kar_payi_orani` = 85/15 kâr payı
4. **`hedef_kitle`ye serbest metin yazmak** — `hedef_kitle` = yeni müşteri · `hedef_kitle` = yeni müşteri · `hedef_kitle` = Bireysel müşteriler
5. **Tek değerli alana iki değer yazmak** — `kampanya_suresi` = 01.01.2026 - 31.12.2026 · `kampanya_suresi` = 1.07.2023 - 31.08.2023 · `kampanya_suresi` = 1-31 Temmuz 2026
6. **"taksit" geçmeyen belgede `taksit_sayisi` doldurmak** — `taksit_sayisi` = 36 · `taksit_sayisi` = {"min": 12, "max": 48} · `taksit_sayisi` = 36
7. **8 sınıf dışında `campaign_type` uydurmak** — `campaign_type` = Güneş Yatırım Hesabı · `campaign_type` = Altın Katılma Hesabı

## Round1'e başlamadan

1. `_ANA-TUR-TALIMATI.md` — iki dakika, tek sayfa.
2. Yukarıdaki tabloyu bir kez okuyun. Bunlar sizin kalıplarınız;
   round1 dört kat büyük, aynı kalıp dört kat maliyet demek.
3. İlk 20 satırı doldurduktan sonra `lint`i koşun — kalıp hâlâ
   sürüyorsa 20 satırda görün, 600 satırda değil:

```bash
.venv/bin/python -m scripts.lint_review_csv \
    data/gold/review/round1_main_D.csv
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
