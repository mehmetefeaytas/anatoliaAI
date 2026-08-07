# Anotasyon Kılavuzu Revizyonu — v1 → v2

> Tarih: 2026-08-07 · Kapsam: `data/gold/ANNOTATION_GUIDE.md`,
> `scripts/report_iaa.py`, `scripts/lint_review_csv.py`,
> `data/gold/review/round0_kalibrasyon_v2_*.csv`, `data/gold/review/_atama.md`
>
> Bu belge iki soruya cevap verir: **ne değişti** ve **kullanıcı şimdi ne
> yapacak**. İkincisi için doğrudan [§0 Kullanıcı ne yapacak](#0-kullanıcı-ne-yapacak)
> bölümüne gidin.

---

## 0. Kullanıcı ne yapacak

κ (kappa) bugün **hesaplanamıyor**. Sebebi anotatör eksikliği değil, veri
düzeni:

- `data/gold/parca/parca-1..4.json` — dört parça **tamamen ayrık**: 48 benzersiz
  belge, **sıfır** tekrar. Uyum, iki kişinin AYNI belgeye bakmasıyla ölçülür;
  burada hiç kesişim yok.
- `round0_kalibrasyon_B/C/D.csv` — üçü **byte düzeyinde birbirinin kopyası** ve
  tamamen boş. `round0_kalibrasyon_A.csv` 76 karar dolu, ama tek başına uyum
  ölçülemez.

Bunun için **v2 kalibrasyon paketi** üretildi: aynı 20 belge, aynı 260 satır,
dört anotatör dosyası.

### Adım 1 — kılavuzun iki bölümünü oku (15 dk)

`data/gold/ANNOTATION_GUIDE.md`
- **§3.1** — boş hücrenin anlamı değişti. Bu tek değişiklik, önceki tüm
  etiketleme alışkanlığını etkiler.
- **§4.13** — sekiz yeni kural. Dört anotatörün bağımsız takıldığı sekiz nokta.

### Adım 2 — dosyanı doldur

| Anotatör | Dosya |
|---|---|
| A | `data/gold/review/round0_kalibrasyon_v2_A.csv` |
| B | `data/gold/review/round0_kalibrasyon_v2_B.csv` |
| C | `data/gold/review/round0_kalibrasyon_v2_C.csv` |
| D | `data/gold/review/round0_kalibrasyon_v2_D.csv` |

Dördü de **aynı 20 belgeyi** içerir — kasıt budur. En az **iki** dosya
dolduğunda κ hesaplanır.

Doldururken tek yeni alışkanlık: **her satıra bir `verdict` yaz.**
`ok` · `fix` · `absent` · `unclear`. Boş bırakılan satır "karar verilmedi"
sayılır ve metriğe girmez.

Salt-okunur `protokol` sütununu (değeri `v2`) silmeyin — araçlar boş hücrenin
anlamını oradan okur.

### Adım 3 — ara kontrol (istediğin kadar sık)

```bash
.venv/bin/python -m scripts.lint_review_csv 'data/gold/review/round0_kalibrasyon_v2_*.csv'
```

Biçim hatalarını (aralık yazımı, bozuk `doc_id`, `fix` + boş değer) ve kalan
karar sayısını basar. Anotasyon sürerken **durdurmaz**, uyarır.

### Adım 4 — κ + Krippendorff α (tek komut)

```bash
.venv/bin/python -m scripts.report_iaa data/gold/review/round0_kalibrasyon_v2_*.csv
```

Üretir: `data/gold/iaa_report.md` — protokol künyesi, Cohen/Fleiss κ,
Krippendorff α (nominal + ratio), önceden ilan edilmiş eşiğe göre karar ve
**uyuşmazlık listesi**.

İki dosyayla koşarsan Cohen κ, üç-dört dosyayla Fleiss κ çıkar.

### Adım 5 — eşiğe göre davran (eşik değiştirilmez)

| κ | Karar | Yapılacak |
|---|---|---|
| ≥ 0,80 | kabul | Ana geçişe devam. |
| 0,67 – 0,80 | notla kabul | Raporda açıkça not; uyuşmazlık listesi gözden geçirilir. |
| < 0,67 | **hakemlik** | Zorunlu hakemlik + kılavuz revizyonu; kalibrasyon tekrarlanır. |

Bu tablo `ANNOTATION_GUIDE.md` §7'de anotasyon **başlamadan** ilan edilmişti ve
bu revizyonda **değiştirilmedi**. Sonuca bakıp eşik oynatmak ölçümü geçersiz
kılar.

### Adım 6 — derlemeden önceki kapı

```bash
.venv/bin/python -m scripts.lint_review_csv --eksiksiz 'data/gold/review/round0_kalibrasyon_v2_*.csv'
```

Karar verilmemiş satır kalmışsa **HATA** verir ve durdurur. Bu kapı zorunludur;
gerekçesi §4'te.

---

## 1. Neden revizyon — kanıt

Dört anotatör (M1–M4) gold.v2'yi **ayrık** 12'şer belgede bağımsız etiketledi.
Birbirlerini görmeden **aynı sekiz belirsizliği** işaretlediler
(`docs/rapor/gold-genisletme.md:168-190`).

Aynı yerde bağımsız tökezleme **anotatör gürültüsü değildir**. Gürültü rastgele
dağılır; bu dağılmadı. Sekiz nokta kılavuzun cevap vermediği sekiz sorudur.

Aynı belgenin bağlayıcı hükmü (`gold-genisletme.md:189-190`):

> *"κ ölçümünden önce kılavuz bu sekiz maddeyle güncellenmeli. Aksi hâlde düşük
> κ, anotatör uyumsuzluğunu değil kılavuz belirsizliğini ölçer."*

Bu revizyon o hükmün yerine getirilmesidir.

---

## 2. Sekiz boşluk — verilen kararlar

Kuralların tam metni `ANNOTATION_GUIDE.md` §4.13'tedir. Aşağıdaki tablo kararı
ve tek cümlelik gerekçeyi verir.

| # | Boşluk | Karar | Gerekçe (tek cümle) |
|---|---|---|---|
| 1 | Kampanya olmayan belge (zekât aracı, KVKK, kurumsal sayfa, kampanya listesi) — gold.v2'nin **9 belgesi, %19** | `campaign_type` → **`absent`**; `null` meşrudur, 12 alan da varsayılan `absent`; `#kampanya_disi` | 8 sınıf kapalı bir kümedir, uymayan belgeye "en yakın" sınıfı vermek macro-F1'i dürüst bir `null`dan daha çok bozar ve modelin her metne sınıf uydurmasını ödüllendirir. |
| 2 | Ürün kısıtı mı, müşteri segmenti mi ("Yalnız Paraf kartlar") | **KİM/NE testi**: kişi niteliği → `hedef_kitle`; ürün/kart/kanal → `kampanya_kosullari`; ikisi birdeyse ikiye bölünür | `hedef_kitle` yalnız 4 etiket taşır ve hiçbiri ürün değildir; `belirli_segment` hem "emekli" hem "Paraf kart sahibi" için kullanılırsa etiket iki ayrı şey demeye başlar (F1 0,727 → 0,267 düşüşünün ana payı). |
| 3 | Tutar cinsinden indirim ("100 TL indirim") | **`odul_miktari`** (`{"value":100,"currency":"TRY"}`) + `#tutar_indirimi`; `indirim_orani` yüzde-özel kalır | Üçüncü alan açmak 12 alanlık şemayı ve ona bağlı her artefaktı (DB, dashboard, karşılaştırma, önceki gold setleri) değiştirirdi; `odul_miktari` zaten para-tipli müşteri kazancı alanıdır. |
| 4 | Çok değerli `alisveris_puani` (sektöre göre farklı oranlar) | **En yüksek** değer alana; sektör–oran çiftlerinin tamamı `kampanya_kosullari`na; `#kosullu_aralik` | Şema tek değerlidir ve "en büyüğü al" kuralı `vade_ay` aralıklarında zaten yürürlüktedir — ortalama almak metinde bulunmayan bir sayı üretirdi. |
| 5 | Oransal tahsis ücreti ("binde 5") | `tahsis_ucreti` → **`unclear`** + notta birebir ifade + `#oransal_ucret`; `masraf_durumu` → `{"has_fee": true, "amount": null}`; oran cümlesi koşullara | `absent` yanlış olurdu (belgede ücret bilgisi VAR ve doğru davranan model halüsinasyonla suçlanırdı); tutarı çarpıp yazmak ise çıkarım değil türetmedir. |
| 6 | `N/M` biçiminde kâr paylaşım oranı ("85/15") | `kar_payi_orani` → **`absent`**; ifade `kampanya_kosullari`na; `#terminoloji` | Katılma hesabının paylaşım anahtarıdır, murabaha kâr payı oranı değildir — ölçülmüş bir bozulma: `"85 / 15"` ayrıştırıcıdan `{min:15,max:85}` olarak geçip gold'a girdi. |
| 7 | Gün cinsinden vade (`vade_ay` ay cinsinden) | 30'un **tam katıysa** `30 gün = 1 ay` ("90 gün" → `3`); değilse **`unclear`** + `#gun_vade`; metinde ay varsa ay kazanır | 45 günü 1 veya 2 aya yuvarlamak metinde olmayan bir kesinlik üretir ve iki anotatör iki farklı yöne yuvarlar; tam-kat kuralı tersinirdir. |
| 8 | Yan menü / "İlginizi çekebilir" bloğu kirliliği | Değer yalnız bu bloklarda geçiyorsa → **`absent`** + `#kabuk_kirliligi`; `absent` = "bu belgenin ANLATTIĞI kampanyaya ait değer yok" | Blok değeri onaylanırsa komşu kampanyanın oranı bu bankaya yazılır ve "adil kıyas" garantisi (CLAUDE.md §17) yanlış sıralama üretir. |

**Yeni hashtag'ler:** `#kampanya_disi` · `#tutar_indirimi` · `#oransal_ucret` ·
`#gun_vade` · `#kabuk_kirliligi` (§6 tablosuna eklendi).

---

## 3. §3.1 — çapa etkisi kapatıldı

### Eskisi

> *"Boş bırakmak = `ok` = model doğru."* (`ANNOTATION_GUIDE.md` §3.1, v1)

Anotatörün bakmadığı her satır modelin değerini gold'a yazıyordu. Model o
satırda **kendi cevabıyla** karşılaştırılıyor ve otomatik olarak haklı çıkıyordu.
Gold, ölçtüğü şeye **çapalanmıştı**.

Ölçülen etki:

| Ölçüm | Protokol | Mikro-F1 |
|---|---|---|
| gold.v1 üzerinde | v1 (çapalı) | **0,677** |
| aynı sistem, kör protokol | çapasız | **0,536** |

0,141'lik farkın bir kısmı model başarısı değil, **protokol artefaktıdır**.

### Yenisi

**Boş = karar verilmedi; metriğe girmez. Onay AÇIK işaretle (`ok`) verilir.**

Altyapı bunu zaten destekliyordu:
`eval/run_eval.py:287` — gold bir alan hakkında karar vermemişse tahmin olsa da
olmasa da metriğe girmez, `Counts.skipped` (`skipped_undecided`) olarak
raporlanır. Yani "bilmediğimizi lehimize saymama" davranışı kodda vardı;
eksik olan, anotatörün "bilmiyorum"u **ifade edebilmesiydi**.

### Kodda karşılığı

**`scripts/report_iaa.py`** — `row_verdict` artık protokol duyarlı:

| Protokol | Boş `verdict` + boş `gold_value` | Sonuç |
|---|---|---|
| v1 | `ok` | κ hesabına girer (eskisi gibi) |
| v2 | `None` | κ hesabından **çıkarılır** |

Her iki protokolde de boş `verdict` + dolu `gold_value` = `fix` (anotatör
düzeltmeyi yazıp karar sütununu atlamıştır; o emek çöpe atılmaz).

Rapora iki şey eklendi: **protokol künyesi** tablosu ve karışık koşuda
(v1 + v2 aynı komutta) açık **uyarı**.

**`scripts/lint_review_csv.py`** — v2 dosyasında karar verilmemiş satırlar
dosya başına **tek** bulguda sayılır: anotasyon sürerken UYARI, `--eksiksiz`
ile HATA.

### Eski CSV'ler nasıl yorumlanacak — geriye dönük veri kaybı yok

- Protokol satırdaki **`protokol` sütunundan** okunur. **Sütun yoksa dosya v1
  sayılır.** Mevcut hiçbir dosyada bu sütun yok; dolayısıyla hepsinin yorumu
  **değişmedi**.
- v1 dosyalarının sayıları geçerlidir — ama **v1 künyesiyle** raporlanır.
- İki protokolün dosyaları aynı κ koşusunda birleştirilmez; birleştirilirse
  `report_iaa` hem terminale hem rapora uyarı basar.
- Hiçbir dosya silinmedi, hiçbir karar üzerine yazılmadı.

---

## 4. Açık iş — `build_gold.py`

`scripts/build_gold.py:130-133` hâlâ v1 sözleşmesini uygular:

```python
if not verdict and gold_raw:
    verdict = "fix"
if not verdict:
    verdict = "ok"          # <- v1 çapası
```

v2 CSV'si bu koda boş satırla ulaşırsa çapa geri döner. İki katmanlı koruma
kondu:

1. **Kapı (bugün yürürlükte):** `lint_review_csv --eksiksiz` boş satır kalmış
   v2 dosyasını HATA ile durdurur. Derleme öncesi bu komut zorunludur —
   `ANNOTATION_GUIDE.md` §8 ve `_atama.md` bu sırayı yazar.
2. **Kalıcı çözüm (yapılacak):** `build_gold.py`'a `--protokol {v1,v2}` bayrağı
   (ya da aynı `protokol` sütunu okuması) eklenip v2'de boş satırın **hiçbir
   kayıt üretmemesi**. Bu değişiklik bu turun dosya kapsamı dışındaydı ve
   bilerek yapılmadı.

Aynı şekilde `scripts/to_review_csv.py` yeni ürettiği paketlere `protokol`
sütunu koymaz; v2 paketleri şimdilik elle üretiliyor (§6). Üreteç güncellenene
kadar yeni paketlere sütunun elle eklenmesi gerekir.

---

## 5. Etkilenmiş veri — protokol künyesi

**Silme yok.** Aşağıdaki setlerin hiçbiri geçersiz değildir;
**karşılaştırılabilir değildir**. Künye `ANNOTATION_GUIDE.md` §11'de kalıcı
olarak kayıtlıdır.

| Set / dosya | Protokol | §4.13 sekiz kuralı | Kullanım |
|---|---|---|---|
| `data/gold/gold.v1.json` | v1 | yok | tarihsel; tek başına, künyesiyle raporlanır |
| `data/gold/gold.v2.json` | v1 | yok | tarihsel; tek başına, künyesiyle raporlanır |
| `round0_kalibrasyon_A.csv` (76 karar dolu) | v1 | yok | v1 κ referansı |
| `round0_kalibrasyon_B/C/D.csv` (boş) | v1 | yok | koşulmadı |
| `round1_*.csv`, `round1_main_*.csv`, `round2_zor_vaka.csv` | v1 | yok | doldurulmadıysa v2'ye taşınacak |
| `round0_kalibrasyon_v2_A..D.csv` | **v2** | **var** | **κ ölçümü buradan** |

### Jüriye tek sayı sunulamamasının gerekçesi

gold.v1/gold.v2 üzerinde ölçülen her F1, boş bırakılan satırlarda modelin kendi
çıktısıyla karşılaştırılmıştır. Aynı sistemin kör protokoldeki skoru
0,677 yerine 0,536'dır. Bu iki sayı **aynı şeyi ölçmez**; ortalamak ya da yalnız
yükseğini sunmak ölçümü geçersiz kılar.

Doğru sunum: her sayı protokol künyesiyle birlikte, ayrı satırlarda. v2 gold
üretildikten sonra karşılaştırılabilir tek sayı ondan gelir.

---

## 6. v2 paketi nasıl üretildi (yeniden üretilebilirlik)

Kaynak: `data/gold/review/round0_kalibrasyon_B.csv` — v1 turunda
`to_review_csv.py --calibration 20 --seed 42` ile üretilmiş, hiç doldurulmamış
şablon. Yapılan tek işlem: karar sütunlarının (`gold_value`, `verdict`, `note`)
boşaltılması ve `protokol` sütununun `v2` değeriyle eklenmesi; sonra dört
anotatör adına kopyalanması.

```python
# .venv/bin/python
import csv
from pathlib import Path

SRC, OUT = Path("data/gold/review/round0_kalibrasyon_B.csv"), Path("data/gold/review")
DELIM, ENC, EOL = ";", "utf-8-sig", "\r\n"

with SRC.open(encoding=ENC, newline="") as fh:
    reader = csv.DictReader(fh, delimiter=DELIM)
    cols, rows = list(reader.fieldnames), list(reader)

for r in rows:
    r["gold_value"] = r["verdict"] = r["note"] = ""
    r["protokol"] = "v2"

for name in ("A", "B", "C", "D"):
    with (OUT / f"round0_kalibrasyon_v2_{name}.csv").open(
            "w", encoding=ENC, newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols + ["protokol"],
                           delimiter=DELIM, lineterminator=EOL)
        w.writeheader()
        w.writerows(rows)
```

Sonuç: 4 dosya × 260 satır × 20 belge, `(doc_id, field)` kümesi dördünde de
birebir aynı. Doğrulandı:

```
lint_review_csv  (varsayılan): 4 dosya · 0 hata · 4 uyarı  -> çıkış 0
lint_review_csv --eksiksiz   : 4 dosya · 4 hata            -> çıkış 1 (kapı çalışıyor)
report_iaa (boş paket)       : κ = "ölçülemedi"            -> sahte κ üretmiyor
report_iaa (v1 A+B)          : protokol künyesi v1, κ = 0,000
report_iaa (v1 + v2 karışık) : "UYARI: v1 ve v2 karıştırıldı"
```

Not: v1 A+B koşusunda κ = 0,000 çıkması bu revizyonun gerekçesinin somut hâlidir
— B dosyası hiç doldurulmadığı hâlde v1 kuralı onun 260 satırının tamamını `ok`
sayar, tek kategoriye yığılmış "anotatör" üretir ve κ çöker. v2'de aynı dosya
"karar verilmedi" der ve κ dürüstçe **ölçülemedi** döner.

---

## Sources

- `docs/rapor/gold-genisletme.md:168-190` — sekiz boşluk ve bağlayıcı hüküm
- `data/gold/ANNOTATION_GUIDE.md` §3.1, §4.13, §7, §8, §11
- `eval/run_eval.py:287` — `Counts.skipped` / `skipped_undecided`
- `scripts/build_gold.py:130-133` — v1 çapası (açık iş)
- `scripts/lint_review_csv.py` modül başlığı — `"85 / 15"` sessiz bozulması

## Related

- `data/gold/review/_atama.md` — v2 kalibrasyon paketi atama tablosu
- `docs/rapor/olcumler.md` — protokol künyesiyle raporlanacak sayılar
- `docs/rapor/yapilacaklar-envanteri.md` T-011 — kalibrasyon turu
