# BERTurk İnce Ayar Planı — 8 Sınıflı Kampanya Türü Sınıflandırması

**Durum:** KAPANDI — eğitim koşuldu (8 Ağu 2026, yerel MPS), ölçüldü ve
**kabul kapısında KALDI**; model projeye alınmadı, kural sınıflandırıcısı
korunuyor. Sonuç ve kök neden: §10. Künye:
`models/berturk-kampanya-8sinif/KUNYE.json` (`kabul_kapisi: "KALDI"`).
§1–§9 hipotezi ve tasarımı **koşum öncesi** hâliyle duruyor — plan
geriye dönük düzeltilmedi ki hipotezin ölçümden önce ne olduğu okunabilsin.
**Defter:** `notebooks/berturk_ince_ayar.ipynb` (Colab, ücretsiz katman, T4)
**İlgili:** `CLAUDE.md` §4, §16, §19, §20 · `scripts/eval_classifier.py` ·
`src/extraction/ner/classifier.py` · `docs/model-license-audit.md` ·
`notebooks/README.md`

---

## 1. Hipotez

> 505 gümüş etiketli kampanya belgesiyle ince ayarlanmış BERTurk, 8 sınıflı
> kampanya türü sınıflandırmasında kural tabanlı `RuleHintClassifier`'ı
> **makro-F1'de ölçülebilir biçimde geçer.**

Hipotezin dayandığı gözlem — temel çizginin ölçülmüş hata deseni
(`python -m scripts.eval_classifier` çıktısı):

| Karışıklık (gerçek → tahmin) | Adet |
|---|---|
| Yatırım Ürünü → İhtiyaç Finansmanı | 2 |
| İhtiyaç Finansmanı → Konut Finansmanı | 2 |
| Finansman → Taşıt Finansmanı | 1 |
| Yeni Müşteri → (çekimser) | 1 |

Hataların tamamı **anahtar kelime çakışmasından** kaynaklanıyor: kural
sınıflandırıcı sözcük varlığına bakar, bağlama bakmaz. "Konut" sözcüğü geçen
bir ihtiyaç kredisi metni `Konut Finansmanı`'na kayıyor. Bir dil modeli bağlamı
kodladığı için bu hata sınıfını **prensipte** çözebilir.

**Karşı hipotez (ciddiye alınıyor):** 505 örnek 110 M parametreli bir modeli
bağlamı öğrenecek kadar beslemez; model gümüş etiketlerin gürültüsünü ezberler
ve gold'da kural çizgisinin altına düşer. Bölüm 6'daki alan kayması bu riski
büyütüyor.

---

## 2. Ölçüt (metrik)

**Birincil: makro-F1.** Sınıf dağılımı dengesiz (Kart 144 ↔ Finansman 41,
**3,51×**); accuracy çoğunluk sınıfını ödüllendirir. Makro-F1 her sınıfı eşit
tartar. Erken durdurma da (`metric_for_best_model="macro_f1"`) bu metriğe
bağlanır, accuracy'ye değil.

**İkincil:** accuracy, sınıf bazlı P/R/F1, karışıklık matrisi, çekimser sayısı.

### Ölçüm hattı — tek ve ortak

Karşılaştırma ancak **aynı küme + aynı metrik + aynı çekimser muamelesi** ile
anlamlıdır. Bu yüzden defter, `eval/run_eval.py`'deki tanımları birebir taşır:

1. **Makro-F1**, yalnız `support > 0` olan sınıflar üzerinden ortalanır.
   Gold'da hiç örneği olmayan sınıfın recall'ı tanımsızdır; 0 sayıp ortalamaya
   katmak metriği gold kapsamına göre keyfî düşürür.
2. **Çekimserlik**, doğru sınıf için **FN**, hiçbir sınıf için **FP** değildir.
   Susmak recall'u düşürür ama precision'ı şişirmez — zor belgelerde susup
   kolaylarda konuşan model ödüllendirilmez.
3. **Accuracy** = doğru / toplam; çekimser cevap yanlış sayılır.

**Doğrulandı:** Defterin metrik uygulaması kural çizgisi üzerinde koşuldu ve
depoyla **birebir aynı** sayıyı üretti — accuracy 0,700, makro-F1 0,762,
çekimser 1. Yani iki taraf gerçekten aynı hattı kullanıyor.

---

## 3. Temel çizgi (baseline) — ölçülmüş

`RuleHintClassifier`, `data/gold/gold.v1.json` üzerinde
(`python -m scripts.eval_classifier`):

| Kol | n | accuracy | makro-F1 | çekimser |
|---|---|---|---|---|
| **kural (`RuleHintClassifier`)** | **20** | **0,700** | **0,762** | **1** |

Sınıf bazlı:

| sınıf | destek | P | R | F1 |
|---|---|---|---|---|
| Finansman | 3 | 1,000 | 0,667 | 0,800 |
| İhtiyaç Finansmanı | 4 | 0,500 | 0,500 | 0,500 |
| Konut Finansmanı | 2 | 0,500 | 1,000 | 0,667 |
| Taşıt Finansmanı | 2 | 0,667 | 1,000 | 0,800 |
| Kart | 2 | 1,000 | 1,000 | 1,000 |
| Alışveriş Puanı | 1 | 1,000 | 1,000 | 1,000 |
| Yeni Müşteri | 2 | 1,000 | 0,500 | 0,667 |
| Yatırım Ürünü | 4 | 1,000 | 0,500 | 0,667 |

Bu sayılar uydurulmadı; komut çıktısından kopyalandı.

---

## 4. Veri

### Eğitim kümesi — gümüş küme

| Alan | Değer |
|---|---|
| Yol | `data/silver/silver.jsonl` |
| Kayıt | **505** |
| Sınıf | **8** (`src/schemas.py:CAMPAIGN_TYPES`) |
| Etiket kaynağı | LLM uzlaşması — 255 kayıt `uc_oy_ayni`, 206 `iki_llm_ayni`, 23 `kanit_desteklemiyor`, 21 `etiketler_ayristi` |
| Güven | 255 `yuksek`, 250 `orta` |

Sınıf dağılımı (ölçülmüş):

| sınıf | adet | oran |
|---|---|---|
| Kart | 144 | 28,5% |
| Alışveriş Puanı | 73 | 14,5% |
| Konut Finansmanı | 56 | 11,1% |
| İhtiyaç Finansmanı | 54 | 10,7% |
| Yatırım Ürünü | 49 | 9,7% |
| Taşıt Finansmanı | 47 | 9,3% |
| Yeni Müşteri | 41 | 8,1% |
| Finansman | 41 | 8,1% |

Her sınıfta ≥41 örnek; dengesizlik **3,51×**.

### Metin nereden geliyor

`silver.jsonl` **metin içermez**, yalnız `doc_id` + `label` taşır. Birleştirme
(defterdeki *YEREL HAZIRLIK* hücresi, koşuldu ve doğrulandı):

| Kaynak | Kapsam | Kalite |
|---|---|---|
| `data/silver/trainable.jsonl` → `core_text` | 505'in **491**'i | kalıp metin ayıklanmış |
| `data/raw-classic/<banka>/{live,products}/<slug>.txt` | 505'in **505**'i (`live` 416 + `products` 89) | ham |

**505/505 çözülüyor, kayıt düşmüyor.** `core_text` tercih edilir; bulunamayan
14 belge (hepsi `denizbank`/`ing`/`teb` kredi ürün sayfası) ham `.txt`'ten
kurtarılır — atlanırlarsa `Taşıt Finansmanı` ve `Konut Finansmanı` orantısız
zarar görür.

`trainable.jsonl` depoda **izlenmiyor** (`.gitignore` s.76). Taze klonda hücre
tamamen ham `.txt`'e düşer; çalışır ama metinler kalıp içerir.

Uzunluklar: `core_text` medyan 1 718 karakter (`text` 5 043) → BERT'in 512
alt-sözcük penceresine çok daha yakın. `max_length=256` seçildi; defter gerçek
token uzunluk dağılımını ve 256'nın kapsama oranını **ölçüp basar**.

### Değerlendirme kümesi

`data/gold/gold.v1.json` — `campaign_type` taşıyan **20** belge. Temel çizginin
ölçüldüğü kümenin **aynısı**; başka türlüsü kıyaslanamaz sayı üretir.

### Bölme

%70 eğitim / %15 doğrulama / %15 test, **katmanlı**, `random_state=42` sabit.
En küçük sınıf (41) her bölmede ≥6 örnekle temsil edilir. Dağılım bölmeden
**önce ve sonra** basılır.

---

## 5. Kabul kriteri — hangi sayıyı geçerse projeye alınır

> **BERTurk, gold makro-F1'inin %95 bootstrap güven aralığının ALT SINIRI
> 0,762'yi aşarsa projeye alınır.**

| Durum | Karar |
|---|---|
| alt sınır > 0,762 | ✅ **Alınır.** `BERTURK_MODEL_DIR` devreye girer, `docs/rapor/ablasyon.md`'ye satır eklenir. |
| üst sınır < 0,762 | ❌ **Alınmaz.** Kural çizgisi korunur. |
| aralık 0,762'yi içeriyor | ⚠️ **Ayırt edilemez → alınmaz.** Varsayılan `RuleHintClassifier` kalır. |

Üçüncü durum en olası sonuçtur (gold n=20, sınıf başına 2,5 örnek) ve
**başarısızlık değildir** — "bu kümede ayırt edilemez" geçerli bir bulgudur.
Nokta tahmini karşılaştırıp kazanan ilan etmek `CLAUDE.md` §19'daki "uydurma
yok" kuralının ölçüm tarafındaki ihlalidir.

Ek koşullar (üçü de şart):

1. Ölçüm **depoda** tekrarlandı:
   `python -m scripts.eval_classifier --predictions data/eval/berturk_preds.jsonl --name berturk --compare`
   defterdeki tabloyu birebir yeniden üretti.
2. **Çevrimdışı çıkarım** doğrulandı (`local_files_only=True`, `HF_HUB_OFFLINE=1`).
3. Model etiketleri `CAMPAIGN_TYPES` ile birebir uyumlu (aksi hâlde
   `BerturkClassifier` sessizce kurala düşer ve ölçüm yanıltıcı olur).

---

## 6. Riskler

### R1 — 505 kayıt küçük *(yüksek)*

353 eğitim örneğiyle 110 M parametreli model ezberleyebilir. Önlemler: erken
durdurma (doğrulama makro-F1, sabır 3), `load_best_model_at_end=True`,
`weight_decay=0.01`, `warmup_ratio=0.1`, düşük öğrenme oranı (2e-5), ayrı test
kümesi. Bunlar sorunu **çözmez**, görünür kılar — defter epoch başına eğitim/
doğrulama kaybını basar; ıraksama oradan okunur.

### R2 — gümüş etiketler gürültülü *(yüksek)*

Etiketler insan değil **LLM uzlaşmasıyla** üretildi. 505'in yalnız 255'i üç oy
aynı; 206'sı iki LLM aynı, 23'ü `kanit_desteklemiyor`, 21'i `etiketler_ayristi`.
**Modelin tavanı etiketleyicinin doğruluğudur** ve bu doğruluk ölçülmedi.
İnsan doğrulaması yapılmadı. Azaltma: kayıtlarda `confidence` alanı taşınıyor;
yalnız `yuksek` güvenli 255 kayıtla tekrar koşmak bir ablasyon kolu olabilir —
**henüz koşulmadı.**

### R3 — sınıf dengesizliği *(orta)*

3,51× (Kart 144 ↔ Finansman/Yeni Müşteri 41). Ağırlıksız kayıp modeli çoğunluğa
iter, makro-F1 düşer. Azaltma: `balanced` formüllü sınıf ağırlıklı
`CrossEntropyLoss` (`SINIF_AGIRLIGI=True`) + katmanlı bölme + makro-F1'e
bağlanmış erken durdurma.

### R4 — alan kayması: klasik banka → katılım bankası *(yüksek, en az fark edilen)*

**Ölçülmüş olgu:** gold ∩ gümüş = **0 belge**. Sızıntı yok — ama sebebi sadece
dikkatli ayırma değil, iki kümenin **farklı bankacılık türünden** gelmesi:

- **Gümüş (eğitim):** klasik bankalar — `yapi-kredi` 90, `garanti-bbva` 71,
  `qnb` 66, `akbank` 53, `ziraat-bankasi` 49, `is-bankasi` 39, `halkbank` 34,
  `vakifbank` 31, `ing` 32, `denizbank` 25, `teb` 15.
- **Gold (değerlendirme):** katılım bankaları — `albaraka`, `vakif-katilim`,
  `turkiye-finans` vb.

Katılım bankacılığında "faiz" yerine **kâr payı**, "kredi" yerine **finansman**
kullanılır. BERTurk klasik bankacılık dilinde eğitilip katılım bankacılığı
dilinde sınanıyor. Kural sınıflandırıcı her iki dağarcığı da elle içerdiği için
bu kaymadan **etkilenmiyor** — yani karşılaştırma BERTurk aleyhine eğimli.

**Sonuç yorumlanırken:** BERTurk gold'da kaybederse bu "BERTurk kötü" değil,
"eğitim kümesi hedef alanı temsil etmiyor" demek olabilir. Bu iki açıklamayı
ayırt edecek ölçüm (katılım bankası verisiyle eğitim) **yapılmadı.**

### R5 — gold küme n=20 *(yüksek)*

Sınıf başına 2,5 örnek. Tek belgenin yer değiştirmesi accuracy'yi 0,05 oynatır.
Zincirin en zayıf halkası burasıdır ve kabul kriterinin güven aralığına
bağlanmasının sebebi budur. Azaltma: gold kümeyi büyütmek — bu planın dışında.

### R6 — tek bölme *(orta)*

Yalnız `random_state=42` koşuluyor. Bootstrap güven aralığı **tek bölme
içindeki örnekleme belirsizliğini** ölçer, **bölme değişkenliğini ölçmez**.
Yayına giden bir iddia için 5 farklı tohumla tekrar gerekir — **planlanmadı.**

### R7 — lisans *(kapatıldı)*

`dbmdz/bert-base-turkish-cased` → `cardData.license` = **`mit`**, `base_model`
**beyan edilmemiş** (zincirin kökü, takip edilecek taban yok). `CLAUDE.md`
§3/§20 izinli listesinde. Kanıt:
<https://huggingface.co/api/models/dbmdz/bert-base-turkish-cased>

`docs/model-license-audit.md`'deki BERTurk satırıyla tutarlı. Defterin ilk kod
hücresi bunu **her koşuşta canlı doğrular** ve uygun değilse `RuntimeError` ile
durur — model kartı ileride değişirse yanlış ağırlık sessizce eğitilmez.

---

## 7. Hiperparametreler ve gerekçeleri

| Parametre | Değer | Gerekçe |
|---|---|---|
| `learning_rate` | 2e-5 | Olağan aralığın (2e-5–5e-5) **alt ucu**; 353 örnekte yüksek oran önceden eğitilmiş temsilleri bozar. |
| `num_train_epochs` | 8 + erken durdurma | Üst sınır; gerçek durma noktasını doğrulama makro-F1'i belirler (sabır 3). |
| `per_device_train_batch_size` | 16 | Epoch başına ~22 adım; daha büyük parti adım sayısını tek haneye düşürür. |
| `max_length` | 256 | Defter token dağılımını ölçüp kapsamayı basar. 512 hem 2× yavaş hem kuyruktaki kalıp metni modele geri sokar. |
| `weight_decay` | 0,01 | Küçük kümede aşırı öğrenmeye karşı ucuz sigorta. |
| `warmup_ratio` | 0,1 | İlk adımların şoku küçük kümede kalıcı hasar bırakır. |
| sınıf ağırlığı | açık | 3,51× dengesizlik; metrik makro-F1. |
| `seed` / `random_state` | 42 | Sabit, tekrarlanabilirlik. |

---

## 8. Çevrimdışı kısıtı

Yarışma sistemi çevrimdışı çalışmak zorundadır (`CLAUDE.md` §3,
`docs/OFFLINE-KANIT.md`).

| Aşama | Ortam | Ağ |
|---|---|---|
| Eğitim | Colab | çevrimiçi — **kabul edilebilir**, teslim edilen sistemin parçası değil |
| Çıkarım | yerel / Docker | **çevrimdışı zorunlu** |

Defterin son hücresi `HF_HUB_OFFLINE=1`, `TRANSFORMERS_OFFLINE=1` ve
`local_files_only=True` ile yerel ağırlıklardan tahmin üretir.
`local_files_only=True` kritiktir: o olmadan `transformers` eksik dosya için
sessizce ağa çıkar ve çevrimdışı makinede çalışma zamanında patlar.

MIT lisansı projenin Apache-2.0 dağıtımına engel değildir (atıf yükümlülüğü
korunur).

---

## 9. Bu planın kapsamadıkları

- Çok tohumlu tekrar (R6)
- Yalnız `yuksek` güvenli 255 kayıtla ablasyon kolu (R2)
- Katılım bankası verisiyle eğitim / alan uyarlaması (R4)
- Gold kümenin büyütülmesi (R5)
- Gümüş etiketlerin insan doğrulaması (R2)

Bunların hiçbiri koşulmadı; sonuç raporlanırken açık risk olarak taşınmalıdır.

---

## 10. SONUÇ (2026-08-08) — kabul kapısında KALDI, model alınmadı

> Bu başlık 23 Ağu 2026'da `2026-08-07`'den düzeltildi: künye eğitimi
> `2026-08-08T08:48:21+00:00`'a tarihliyor ve bir sonuç koşumdan önce
> olamaz. Sayılar değişmedi, yalnız tarih künyeyle hizalandı.

Eğitim **yerelde** koşuldu (Apple Silicon / MPS), Colab'a gerek kalmadı.
Bu bir yan kazanç: eğitim de teslim ortamında tekrarlanabilir, on-prem
anlatısı güçleniyor. Ağırlıklar `models/berturk-kampanya-8sinif/`
(442,5 MB, `sha256=2c9e3af2410d835a…`), künye `KUNYE.json`.

### Ölçüm — aynı gold küme (n=20), aynı metrik hattı

| kol | accuracy | makro-F1 | çekimser |
|---|---|---|---|
| **kural** (`RuleHintClassifier`) | **0,700** | **0,762** | 1 |
| BERTurk (ince ayarlı) | 0,550 | 0,565 | 0 |
| **fark** | **−0,150** | **−0,198** | |

Bootstrap %95 GA (2000 yineleme, gold n=20):

| ölçüt | nokta | %95 GA | genişlik |
|---|---|---|---|
| accuracy | 0,552 | [0,350 – 0,750] | 0,400 |
| makro-F1 | 0,521 | [0,317 – 0,710] | 0,393 |

### Kapı (plan §5) — geçilmedi

Kural: *gold makro-F1'in %95 GA **alt sınırı** temel çizgiyi (0,762) aşmalı.*
Alt sınır **0,317**. Aşmadı; üstelik **nokta tahmini bile** temel çizginin
0,20 altında.

**❌ BERTurk projeye ALINMADI. Kural sınıflandırıcısı korunuyor.**
`BERTURK_MODEL_DIR` ayarlanmadığı sürece `default_classifier()` zaten kurala
düşer; ürün yolunda değişiklik yok.

### Kök neden — plan §9 bunu risk olarak yazmıştı

Model **gümüş etiketle eğitildi, altın etiketle ölçüldü.** `KUNYE.json`
bunu birebir kaydediyor: *"data/eval/berturk_egitim.jsonl (n=505, gümüş
etiket — LLM uzlaşması, insan doğrulaması YOK)"*.

Yani BERTurk, gerçeği değil **LLM'in etiketleme fonksiyonunu** öğrendi.
Gold, insan protokolüyle etiketlendi; ikisi ayrıştığı ölçüde model
kaçınılmaz olarak geride kalır. Bu, planın §9'unda "gümüş etiketlerin insan
doğrulaması (R2) koşulmadı" diye açıkça taşınan riskin gerçekleşmesidir.

İkinci etken: **BERTurk hiç çekimser kalmıyor** (0 vs kuralın 1'i). Kural
katmanı emin olmadığında susuyor; çekimserlik muhasebesinde susmak recall'u
düşürür ama precision'ı şişirmez (`scripts/eval_classifier.py:109-113`).
Her belgeye bir sınıf atamak, belirsiz belgelerde ücretsiz hata üretiyor.

Karışıklıklar da bunu destekliyor: `İhtiyaç Finansmanı → Konut Finansmanı`
(2), `Yatırım Ürünü → İhtiyaç Finansmanı` (2) — yani model, gümüş kümede
sık karışan komşu sınıfları ayırt edemiyor.

### Dürüst okuma — n=20 uyarısı

GA genişliği 0,39. n=20 bu kararı **kesinleştirmek için dar bir set**;
`eval_classifier.py:173-178` zaten "SIRALAMA sinyalidir" uyarısı basıyor.
Ama kapı bilinçli olarak muhafazakâr kuruldu (alt sınır > temel çizgi) ve
fark bu kadar büyükken (−0,198, nokta tahmininde de geride) sonucun n ile
tersine dönmesi beklenmez.

**Bu bir başarısızlık değil, ölçülmüş bir sonuçtur** ve ablasyon anlatısının
parçasıdır: projede "LLM/derin model ekleyelim" refleksi üçüncü kez ölçümle
yanlışlandı (hibrit kol, orkestrasyon kolu, şimdi BERTurk).

### Neyin denenmediği — hâlâ geçerli

Plan §9'daki listeden hiçbiri koşulmadı. Bu sonucu tersine çevirebilecek en
olası iki müdahale, önem sırasıyla:

1. **Gümüş etiketlerin insan doğrulaması (R2)** — kök neden burada.
2. **Yalnız `yuksek` güvenli 255 kayıtla eğitim (R2 varyantı)** — gürültülü
   etiketleri elemek.

Teslime kalan sürede ikisi de anotasyon bütçesi ister; bütçe gold setine
gidiyor (CLAUDE.md §4).

### Tekrar üretim

```bash
.venv/bin/python -m scripts.train_berturk --bootstrap 2000
.venv/bin/python -m scripts.eval_classifier \
  --predictions data/eval/berturk_preds.jsonl --name berturk --compare
```
