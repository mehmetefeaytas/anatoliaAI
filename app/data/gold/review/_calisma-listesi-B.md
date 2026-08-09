# Round1 Hazırlık Kartı — Anotatör B

> `scripts/calisma_listesi.py` üretti. Elle düzenlemeyin; yeniden
> koşuda üzerine yazılır. Betik CSV'lere **yazmaz**, yalnız okur.

## Kalibrasyona GERİ DÖNMÜYORSUNUZ

`round0_kalibrasyon_*` bir kalibrasyon turuydu, gold değil. İşi ekibi
hizalamaktı ve onu yaptı: dört kural çıktı (kılavuz §4 K1–K4).
**O dosya yeniden etiketlenmeyecek.**

Sizin açacağınız dosya: **`round1_B.csv`** — 650 satır, 50 belge.
Kılavuz §8'in kendi hızıyla (**260 satır ≈ 25 dk**) kabaca **62 dakika**. Bu ölçüm değil,
kılavuzdaki orandan türetmedir; ilk 50 satır daha yavaş gider.

## Kalibrasyonda ne yaptınız

Açık kararınız: **128/260** (%49). 'Açık karar' = dolu `verdict` **ya da** dolu
`gold_value` (kılavuz §3.2: yazılmış düzeltme karardır).

> Round1'de boş hücre **v2 protokolündedir**: onay değil,
> "karar verilmedi" demektir ve satır gold'a HİÇ girmez.
> Kapsama düşer ama doğruluk şişmez — `lint` boş `verdict`i
> HATA sayar ve dosyayı `build_gold` öncesi durdurur.

## Kendi hata kalıplarınız — kalibrasyonda ÖLÇÜLDÜ

**52 ayrık hücre**, 6 kalıpta. Kaynak: `round0_kalibrasyon_B.csv.yedek-hakemlik`
(hakemlik ÖNCESİ — sizin gerçekten yazdığınız hâli).

> Kalıp sayıları toplamı 67, ayrık hücre 52: bir hücre birden çok kalıba girebilir
> (ör. `gold_value`'ya belge açıklaması yazmak hem `absent-dolu-deger` hem `metinden-alinti`dir).

| # | Kalıp | Hücre | Doğrusu | Kural |
|---:|---|---:|---|---|
| 1 | Tek değerli alana iki değer yazmak | **21** | Üst sınırı/bitişi yazın, diğerini `note`'a düşün. Ayrıştırıcı REDDETMEZ — ilk ucu alır, yani sessizce yanlış değer gold'a girer. | `_bicim-karti.md` |
| 2 | `hedef_kitle`ye serbest metin yazmak | **18** | Yalnız dört etiket: `yeni_musteri` · `mevcut_musteri` · `maas_musterisi` · `belirli_segment`. "Bireysel müşteriler" segment DEĞİLDİR (herkes demek) → `absent`. Cümleyi saklamak isterseniz `kampanya_k… | kılavuz §4 `hedef_kitle` |
| 3 | Kanonik değer yerine metinden alıntı | **17** | `48` yazın, `"en fazla 48 aya kadar"` değil. Aralık gerekiyorsa `{"min": 12, "max": 48}`. | kılavuz §5 |
| 4 | "taksit" geçmeyen belgede `taksit_sayisi` doldurmak | **6** | Belgede "taksit" kelimesi yoksa o sayı VADEDİR → `vade_ay`. `taksit_sayisi` `absent` olur. | kılavuz §4 kelime testi |
| 5 | Model boş bırakmışken `absent` yazmak | **4** | `ok` yazın — `absent` yalnız modelin ÜRETTİĞİ değeri reddetmek içindir. Model bir şey üretmediyse reddedilecek bir şey yok. | kılavuz §3.3 kutusu |
| 6 | 8 sınıf dışında `campaign_type` uydurmak | **1** | Sınıf kümesi SABİTTİR. Uymuyorsa `absent` — `null` bir hatanın değil bir kararın adıdır. | kılavuz §4.13/1 |

### Kendi satırlarınızdan örnek

1. **Tek değerli alana iki değer yazmak** — `kampanya_suresi` = 01.01.2026 - 31.12.2026 · `vade_ay` = 1-12 ay · `taksit_sayisi` = 2 ile 3 taksit arasında
2. **`hedef_kitle`ye serbest metin yazmak** — `hedef_kitle` = Hizmet ya da mal üretimi amacıyla faali… · `hedef_kitle` = ["Bireysel müşteriler, gerçek kişi tica… · `hedef_kitle` = ["gerçek kişi bireysel mü…
3. **Kanonik değer yerine metinden alıntı** — `kar_payi_orani` = %40'a %60 · `vade_ay` = 1-12 ay · `vade_ay` = 36 ay
4. **"taksit" geçmeyen belgede `taksit_sayisi` doldurmak** — `taksit_sayisi` = 12 ile 48 arasında · `taksit_sayisi` = 1 ile 30 gün arası · `taksit_sayisi` = 1-12 ay arası
5. **Model boş bırakmışken `absent` yazmak** — `tahsis_ucreti` = Absent · `kar_payi_orani` = Absent · `alisveris_puani` = Absent
6. **8 sınıf dışında `campaign_type` uydurmak** — `campaign_type` = Hediye kampanyası

## Round1'e başlamadan

1. `_ANA-TUR-TALIMATI.md` — iki dakika, tek sayfa.
2. Yukarıdaki tabloyu bir kez okuyun. Bunlar sizin kalıplarınız;
   round1 dört kat büyük, aynı kalıp dört kat maliyet demek.
3. İlk 20 satırı doldurduktan sonra `lint`i koşun — kalıp hâlâ
   sürüyorsa 20 satırda görün, 600 satırda değil:

```bash
.venv/bin/python -m scripts.lint_review_csv \
    data/gold/review/round1_B.csv
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
