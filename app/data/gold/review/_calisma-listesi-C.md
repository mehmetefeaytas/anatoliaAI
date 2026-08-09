# Round1 Hazırlık Kartı — Anotatör C

> `scripts/calisma_listesi.py` üretti. Elle düzenlemeyin; yeniden
> koşuda üzerine yazılır. Betik CSV'lere **yazmaz**, yalnız okur.

## Kalibrasyona GERİ DÖNMÜYORSUNUZ

`round0_kalibrasyon_*` bir kalibrasyon turuydu, gold değil. İşi ekibi
hizalamaktı ve onu yaptı: dört kural çıktı (kılavuz §4 K1–K4).
**O dosya yeniden etiketlenmeyecek.**

Sizin açacağınız dosya: **`round1_main_C.csv`** — 573 satır, 90 belge.
Kılavuz §8'in kendi hızıyla (**260 satır ≈ 25 dk**) kabaca **55 dakika**. Bu ölçüm değil,
kılavuzdaki orandan türetmedir; ilk 50 satır daha yavaş gider.

## Kalibrasyonda ne yaptınız

Açık kararınız: **260/260** (%100). 'Açık karar' = dolu `verdict` **ya da** dolu
`gold_value` (kılavuz §3.2: yazılmış düzeltme karardır).

## Kendi hata kalıplarınız — kalibrasyonda ÖLÇÜLDÜ

**22 ayrık hücre**, 7 kalıpta. Kaynak: `round0_kalibrasyon_C.csv.yedek-hakemlik`
(hakemlik ÖNCESİ — sizin gerçekten yazdığınız hâli).

> Kalıp sayıları toplamı 24, ayrık hücre 22: bir hücre birden çok kalıba girebilir
> (ör. `gold_value`'ya belge açıklaması yazmak hem `absent-dolu-deger` hem `metinden-alinti`dir).

| # | Kalıp | Hücre | Doğrusu | Kural |
|---:|---|---:|---|---|
| 1 | Tek değerli alana iki değer yazmak | **7** | Üst sınırı/bitişi yazın, diğerini `note`'a düşün. Ayrıştırıcı REDDETMEZ — ilk ucu alır, yani sessizce yanlış değer gold'a girer. | `_bicim-karti.md` |
| 2 | Kanonik değer yerine metinden alıntı | **5** | `48` yazın, `"en fazla 48 aya kadar"` değil. Aralık gerekiyorsa `{"min": 12, "max": 48}`. | kılavuz §5 |
| 3 | Model boş bırakmışken `absent` yazmak | **3** | `ok` yazın — `absent` yalnız modelin ÜRETTİĞİ değeri reddetmek içindir. Model bir şey üretmediyse reddedilecek bir şey yok. | kılavuz §3.3 kutusu |
| 4 | 8 sınıf dışında `campaign_type` uydurmak | **3** | Sınıf kümesi SABİTTİR. Uymuyorsa `absent` — `null` bir hatanın değil bir kararın adıdır. | kılavuz §4.13/1 |
| 5 | "taksit" geçmeyen belgede `taksit_sayisi` doldurmak | **3** | Belgede "taksit" kelimesi yoksa o sayı VADEDİR → `vade_ay`. `taksit_sayisi` `absent` olur. | kılavuz §4 kelime testi |
| 6 | `hedef_kitle`ye serbest metin yazmak | **2** | Yalnız dört etiket: `yeni_musteri` · `mevcut_musteri` · `maas_musterisi` · `belirli_segment`. "Bireysel müşteriler" segment DEĞİLDİR (herkes demek) → `absent`. Cümleyi saklamak isterseniz `kampanya_k… | kılavuz §4 `hedef_kitle` |
| 7 | `fix` yazıp `gold_value`'yu boş bırakmak | **1** | `build_gold` burada DURUR. Doğru değeri yazın ya da kararı `absent`/`unclear` yapın. | kılavuz §3.2 |

### Kendi satırlarınızdan örnek

1. **Tek değerli alana iki değer yazmak** — `kampanya_suresi` = 01.01.2026 - 21.12.2026 · `kampanya_suresi` = 1.07.2023-31.08.23 · `kampanya_suresi` = 1.07.2026-31.07.2026
2. **Kanonik değer yerine metinden alıntı** — `taksit_sayisi` = 3-6 taksit · `finansman_tutari` = 1.250.000 tl · `kar_payi_orani` = 3.9899999999999998E-2
3. **Model boş bırakmışken `absent` yazmak** — `tahsis_ucreti` = absent · `alisveris_puani` = absent · `alisveris_puani` = absent
4. **8 sınıf dışında `campaign_type` uydurmak** — `campaign_type` = Güneş Katılma Hesabı · `campaign_type` = Yatırım Hesabı · `campaign_type` = Leasing
5. **"taksit" geçmeyen belgede `taksit_sayisi` doldurmak** — `taksit_sayisi` = 36 · `taksit_sayisi` = 48 · `taksit_sayisi` = 36
6. **`hedef_kitle`ye serbest metin yazmak** — `hedef_kitle` = Bireysel Müşteri · `hedef_kitle` = yeni müşteri
7. **`fix` yazıp `gold_value`'yu boş bırakmak** — `kampanya_kosullari` = fix

## Round1'e başlamadan

1. `_ANA-TUR-TALIMATI.md` — iki dakika, tek sayfa.
2. Yukarıdaki tabloyu bir kez okuyun. Bunlar sizin kalıplarınız;
   round1 dört kat büyük, aynı kalıp dört kat maliyet demek.
3. İlk 20 satırı doldurduktan sonra `lint`i koşun — kalıp hâlâ
   sürüyorsa 20 satırda görün, 600 satırda değil:

```bash
.venv/bin/python -m scripts.lint_review_csv \
    data/gold/review/round1_main_C.csv
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
