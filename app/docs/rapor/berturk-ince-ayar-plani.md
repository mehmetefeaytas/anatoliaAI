# BERTurk İnce Ayar Planı — 8 Sınıflı Kampanya Türü Sınıflandırması

**Durum:** plan — eğitim henüz koşulmadı, bu belgede hiçbir eğitim sonucu yok.
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
