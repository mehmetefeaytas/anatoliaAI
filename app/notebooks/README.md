# notebooks/

Colab'da koşan deney defterleri. **Hiçbiri üretim yolunda değildir** — üretim
kodu `src/` altında, ölçüm `scripts/` ve `eval/` altındadır. Defterler yalnızca
GPU gerektiren veya tek seferlik olan işleri yapar.

| Defter | Ne yapar |
|---|---|
| `00_vllm_smoke.ipynb` | vLLM duman testi |
| `10_colab_eval.ipynb` | Colab'da değerlendirme koşumu |
| **`berturk_ince_ayar.ipynb`** | **BERTurk ince ayarı — 8 sınıflı kampanya türü sınıflandırması** |

---

## `berturk_ince_ayar.ipynb`

### Ne yapar

`dbmdz/bert-base-turkish-cased` (BERTurk) modelini gümüş kümedeki 505 etiketli
kampanya belgesiyle ince ayarlar (fine-tune) ve sonucu kural tabanlı temel
çizgiyle **aynı gold küme, aynı metrik** üzerinden karşılaştırır.

`CLAUDE.md` §4 ince ayara yalnızca bu göreve izin verir; alan çıkarımı (NER)
kural + few-shot LLM ile yapılır.

36 hücre (17 markdown, 19 kod), sırasıyla:

1. Lisans doğrulaması — **çalıştırılabilir kapı**, uygun değilse `RuntimeError`
2. GPU kontrolü + sürümü pinlenmiş bağımlılık kurulumu
3. Veri hazırlama (yerel) + Colab'a yükleme (Drive veya elle)
4. Katmanlı bölme, `random_state=42` — dağılım bölmeden önce **ve** sonra basılır
5. Eğitim — sınıf ağırlıklı kayıp, doğrulama makro-F1'i üzerinden erken durdurma
6. Değerlendirme — accuracy, makro-F1, sınıf bazlı P/R/F1, karışıklık matrisi
7. **Temel çizgiyle yan yana karşılaştırma tablosu** (0,700 / 0,762)
8. Bootstrap güven aralığı + istatistiksel uyarı
9. Model dışa aktarma + projeye geri taşıma
10. **Çevrimdışı çıkarım doğrulaması** (`local_files_only=True`)

### Lisans durumu ✅

| Alan | Değer |
|---|---|
| Model | `dbmdz/bert-base-turkish-cased` |
| `cardData.license` | **`mit`** |
| `base_model` | **beyan edilmemiş** → zincirin **kökü**, takip edilecek taban yok |
| Karar | ✅ **UYGUN** — MIT, `CLAUDE.md` §3/§20 izinli listesinde |

Kanıt:
- <https://huggingface.co/dbmdz/bert-base-turkish-cased>
- <https://huggingface.co/api/models/dbmdz/bert-base-turkish-cased>

Bu, `docs/model-license-audit.md`'deki BERTurk satırıyla (MIT, taban: "kök")
tutarlıdır. Defterin ilk kod hücresi bunu **her koşuşta canlı doğrular** ve
lisans izinli listede değilse defteri durdurur — model kartı ileride değişirse
yanlış bir ağırlık sessizce eğitilmez.

> Gemma ve Llama community lisanslı ağırlıklar kullanım kısıtı içerdiği için
> **yasaktır** (diskalifiye riski). BERTurk bu kategoriye girmez.

### Nasıl koşulur

**Adım 1 — veriyi yerelde hazırla.** Defterdeki *"YEREL HAZIRLIK"* hücresini
depo kökünde (`app/`) çalıştır. Etiketler ve metinler depoda ayrı dosyalarda
durduğu için birleştirilmeleri gerekir:

- `data/silver/silver.jsonl` → 505 etiket (metin yok)
- `data/silver/trainable.jsonl` → 491 belgenin ayıklanmış `core_text`'i
- `data/raw-classic/<banka>/{live,products}/<slug>.txt` → 505/505 ham metin

Hücre 505/505 kaydı çözer ve iki dosya üretir:

```
data/eval/berturk_egitim.jsonl      # 505 satır — {doc_id, text, label, bank_slug, confidence}
data/eval/berturk_gold_eval.jsonl   #  20 satır — {doc_id, text, label}
```

Hücre ayrıca **sızıntı kontrolü** yapar: gold belgeleri eğitim kümesine
karışırsa `assert` ile durur (ölçülen durum: kesişim = 0).

> `data/silver/trainable.jsonl` depoda **izlenmiyor** (`.gitignore` s.76,
> 12 MB). Taze bir klonda hücre 505'in tamamını ham `.txt`'ten çözer —
> çalışır, ama metinler kalıp (boilerplate) içerdiği için sonuç birebir aynı
> olmaz. Hücre hangi modda koştuğunu basar.

**Adım 2 — Colab.** İki `.jsonl` dosyasını Google Drive'da
`MyDrive/anatolia-ai/` klasörüne koy. Colab'da **Çalışma zamanı türü → T4 GPU**
seç, defteri aç, baştan sona koş. Ücretsiz katman yeterlidir; ücretli
servis/API kullanılmaz.

### Çıktısı nereye gider

| Çıktı | Colab'da | Depoda |
|---|---|---|
| İnce ayarlı ağırlıklar | `/content/berturk-kampanya-8sinif.zip` → Drive | `models/berturk-kampanya-8sinif/` (**`.gitignore` s.81 — commit edilmez**) |
| Gold tahminleri | `/content/berturk_preds.jsonl` → Drive | `data/eval/berturk_preds.jsonl` |
| Künye (lisans + ölçüm) | model dizininde `KUNYE.json` | ağırlıklarla birlikte taşınır |

Depoya taşıdıktan sonra ölçümü **depoda tekrarla**:

```bash
python -m scripts.eval_classifier \
    --predictions data/eval/berturk_preds.jsonl --name berturk --compare
```

Bu komut defterdeki karşılaştırma tablosunu yeniden üretmelidir. Sayılar
tutmuyorsa ölçüm hattında bir fark var demektir — **sonucu raporlama, araştır.**

Defterin metrik uygulaması `eval/run_eval.py`'den birebir taşındı ve kural
çizgisi üzerinde doğrulandı: aynı gold küme üzerinde **accuracy 0,700 /
makro-F1 0,762 / 1 çekimser** üretiyor — yani depo ile aynı sayıyı veriyor.

### `src/` içinde nereye bağlanır

Kod değişikliği **gerekmiyor**. Bağlantı noktası hazır:
`src/extraction/ner/classifier.py`

- `BerturkClassifier` model dizinini `BERTURK_MODEL_DIR` ortam değişkeninden
  okur (bkz. `.env.example` s.45); dizin yoksa sessizce `RuleHintClassifier`'a
  düşer.
- `default_classifier()` ortama bakar: ağırlık varsa BERTurk, yoksa kural.

```bash
export BERTURK_MODEL_DIR=$(pwd)/models/berturk-kampanya-8sinif
```

Docker'da `docker-compose.yml` zaten `./models` dizinini bağlıyor.

### Kabul kriteri — ne zaman projeye alınır

> BERTurk projeye ancak gold makro-F1'inin **%95 güven aralığının alt sınırı**
> kural çizgisinin **0,762** değerini aşarsa alınır.

Aralık 0,762'yi içeriyorsa sonuç **"ayırt edilemez"**dir ve varsayılan
`RuleHintClassifier` olarak kalır. Gold küme n=20 (sınıf başına 2,5 örnek)
olduğu için bu ihtimal ciddidir; defter bunu gizlemez, bootstrap hücresinde
açıkça basar.

Ayrıntılı gerekçe, riskler ve hipotez: `docs/rapor/berturk-ince-ayar-plani.md`

### Çevrimdışı notu

Yarışma sistemi çevrimdışı çalışmak zorundadır (`CLAUDE.md` §3,
`docs/OFFLINE-KANIT.md`). Ayrım:

- **Eğitim** Colab'da, çevrimiçi — teslim edilen sistemin parçası değildir.
- **Çıkarım** yerelde, **çevrimdışı zorunlu** — ağırlıklar diskten okunur.

Defterin son kod hücresi bunu kanıtlar: `HF_HUB_OFFLINE=1`,
`TRANSFORMERS_OFFLINE=1` ve `local_files_only=True` ile modeli yalnızca yerel
dosyalardan yükleyip tahmin üretir. `local_files_only=True` kritiktir — o
olmadan `transformers` eksik bir dosya için sessizce ağa çıkar ve çevrimdışı
makinede çalışma zamanında patlar.

### Bu defter burada koşulmadı

Defter **yerel makinede çalıştırılmadı** (GPU yok). Doğrulananlar:

- `.ipynb` geçerli JSON, nbformat 4.5, 36 hücre
- Tüm kod hücrelerinde sözdizimi hatası yok
- *YEREL HAZIRLIK* hücresi gerçekten koşuldu: 505/505 çözüldü, sızıntı = 0
- Sınıf dağılımı hücresi koşuldu: 8 sınıf, dengesizlik 3,51×
- Metrik hücresi koşuldu ve depo çizgisini birebir yeniden üretti

Eğitim/değerlendirme hücreleri GPU gerektirdiği için **Colab'da koşulacak**;
çıktı sayıları oradan gelir. Bu README hiçbir eğitim sonucu içermez.
