# Anotasyon Atama Planı — round1_v2 (protokol v2, yeni belgeler)

> Hazırlayan: `scripts/sample_gold_v2` → `scripts/preannotate` → `scripts/to_review_csv`
> Hazırlık tarihi: 2026-08-13 · Ön-anotasyon: `data/gold/preannotations.v3.json`
> Kılavuz: [`../ANNOTATION_GUIDE.md`](../ANNOTATION_GUIDE.md) — **başlamadan okunacak.**

## Bu tur NEDEN var — iki açığı birden kapatıyor

**1) Gold seti 48 → 74.** Mevcut `gold.v2.json` 48 kayıt. Ölçüm setinin dar
olması bilinen bir kırılganlık: bir alanın F1'i tek haneli kayıt sayısına
dayandığında kural değişikliğinin gerçek mi gürültü mü olduğu ayrılamıyor.

**2) Protokol v2 altında uyum hiç ölçülmedi.** `iaa_report.md` yayımlanan
Fleiss κ = 0,302 **protokol v1** turundan geliyor. κ, anotasyon başlamadan
ilan edilen eşiğin (0,67) altında kaldığı için kılavuz v1→v2 revize edildi
(`../../docs/rapor/kilavuz-revizyonu.md`, 7 Ağustos) ve 123 uyuşmazlık tek tek
listelendi. Revizyondan **sonra** uyum bir daha ölçülmedi: bunun için dağıtılan
`round0_kalibrasyon_v2_{A,B,C,D}.csv` dosyalarının dördünün sha256'sı birebir
aynı — hiçbiri doldurulmamış.

Bu tur ikisini tek işte birleştirir: dört anotatör **aynı 26 belgeyi** anote
eder, böylece hem gold büyür hem Fleiss κ protokol v2 altında hesaplanabilir.

### Neden eski belgeler yeniden anote edilmiyor

`round0_kalibrasyon_v2_*` aynı belgeleri v2 protokolüyle yeniden anote ettirmek
için üretilmişti. O yol **bilerek seçilmedi**: anotatörler o 20 belgenin
hakemlik sonuçlarını gördü. Aynı kişilere aynı belgeleri tekrar sormak,
hatırlama etkisiyle şişmiş bir κ üretir — kılavuzun düzelip düzelmediğini
değil, insanların ne hatırladığını ölçer. Yeni belgelerde ölçülen κ bu
bulaşmadan uzaktır.

**Karşılığında kabul edilen bedel:** bu κ, 0,302 ile **birebir kıyaslanamaz**
(farklı belge kümesi). Raporlarken "v1'de 0,302 → v2'de X" diye bir iyileşme
oku çizilmeyecek; iki ayrı ölçüm olarak yazılacak.

## Kim neyi açacak

Dördü de **aynı** belgeleri görür (kalibrasyon turu). Kendi harfinizi açın:

| Anotatör | Dosya | Satır |
|---|---|---:|
| A | `round1_v2_A.csv` | 338 |
| B | `round1_v2_B.csv` | 338 |
| C | `round1_v2_C.csv` | 338 |
| D | `round1_v2_D.csv` | 338 |

- Belge: **26** (11 banka, 9 kampanya türünde 3'er) · alan: 12 · tam kapsama
  (her belgede 12/12 alan karara bağlanır)
- **Protokol: v2** — dosyalarda `protokol` sütunu var. Boş `verdict` "onay"
  DEĞİL, "karar verilmedi" demektir ve gold'a girmez. Model doğruysa `ok`,
  yanlışsa `fix` + değer, metinde yoksa `absent`, karar veremiyorsanız
  `unclear` yazın (§3.1). Boş bırakılan satır ölçüme hiç katılmaz.
- Belge tam metinleri: `belgeler/<doc_id>.txt`
- Tohum: `42` — aynı komut aynı dosyaları üretir

**Birbirinizle konuşmadan doldurun.** κ'nın ölçtüğü şey bağımsız kararların
örtüşmesidir; tartışarak doldurulan turda κ anlamını yitirir. Tartışma
doldurduktan **sonra**, uyuşmazlık listesi üzerinden yapılır.

## Doldurduktan sonra

```bash
# 1) Biçim denetimi (boş verdict = KARAR VERİLMEDİ, v2 protokolü)
python -m scripts.lint_review_csv 'data/gold/review/round1_v2_*.csv'

# 2) Uyum — protokol v2 altında ilk ölçüm
python -m scripts.report_iaa \
    data/gold/review/round1_v2_A.csv data/gold/review/round1_v2_B.csv \
    data/gold/review/round1_v2_C.csv data/gold/review/round1_v2_D.csv \
    --out data/gold/iaa_report_v2.md

# 3) Gold üretimi
python -m scripts.build_gold --pre data/gold/preannotations.v3.json \
    --csv-dir data/gold/review

# 4) Ölçümü yeniden koş — G1.5 regresyon kapısı burada devreye girer
python -m eval.run_eval --gold data/gold/gold.v3.json --esikler eval/esikler.json
```

`--pre` **mutlaka** `data/gold/preannotations.v3.json` olmalı. CSV'ler bu
dosyadan üretildi; varsayılan başka bir ön-anotasyonu gösterir ve belgelerin
çoğu "bilinmeyen doc_id" diye sessizce atlanır.

## Beklenti: yeni kayıtlar F1'i DÜŞÜREBİLİR

Bu kötü haber değil, ölçümün amacı. Mevcut 48 kaydın 40'ı kasten zor vakaydı ve
FAZ 1 kuralları o kayıtlara bakılarak yazıldı. Yeni 26 belge kural yazımında
görülmedi; F1 düşerse aradaki fark **ezberin payıdır** ve bilinmesi gerekir.
Regresyon kapısı (`eval/esikler.json`) bu turda bilerek gevşetilmez.

## Hazırlık sırasında bulunan iki şey

- **Örnekleyicide tekillik kusuru** — havuz içi tekilleştirme `content_hash`
  yerine sözlük eşitliğine dayanıyordu; yalnız URL harf durumunda ayrışan aynı
  belge örneğe iki kez giriyordu. Düzeltildi, regresyon:
  `tests/test_sample_gold_tekillik.py`.
- **İki belgenin metni değişmiş.** `hayat-finans--...biz-kart-yemek-harcamasi...`
  ve `vakif-katilim--detay-3-ay-ertelemeli-motosiklet-kampanyasi` daha önce
  dağıtılan sürümlerinden farklı (sayfa yeniden toplanmış). İkisinde de
  doldurulmuş anotasyon **yoktu**, bu yüzden `belgeler/` altındaki kopyalar
  güncel korpusla eşitlendi. Doldurulmuş olsalardı eşitlenmez, ayrı `doc_id`
  ile taşınırlardı — anote edilen metin sonradan değiştirilemez.
