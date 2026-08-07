# Ablasyon: kural-only vs LLM-only vs hibrit

**Durum:** ✅ **koşuldu** (envanter T-014, T-018, T-044)
**Ölçüm tarihi:** 2026-08-05
**Ölçülen commit:** `4117601f76cc6ff63455fb01f26ade9636eb5315` — **çalışma ağacı temiz**
**Ham çıktı:** `eval/reports/20260804-215206` (strict), `eval/reports/20260804-215208` (tolerant)

---

## Yönetici özeti — beklentinin tersi çıktı

`CLAUDE.md` §16 bu tabloyu *"hibridin kazandığını kanıtla"* diye istiyor.
**Kanıtlanmadı. Tersi ölçüldü.**

| iddia | ölçüm |
|---|---|
| Hibrit, kural katmanını geçer | ❌ **Yanlış.** Hibrit 0,575 < kural 0,612 (McNemar p = 0,0117, kazanan kural) |
| Hibrit özellikle ZOR vakalarda kazanır | ❌ Ölçülemedi — gold'da yalnız **1** zor belge var; hibrit orada kuralla **eşit** (0,667) |
| LLM katmanı kuralların kaçırdığını toplar | ⚠️ **Kısmen.** Geri çağırma +1 TP kazandırıyor, ama precision 11 FP kaybettiriyor |
| LLM halüsinasyonu düşük | ❌ **Yanlış.** Hibrit halüsinasyon oranı 0,163 — kural katmanının (0,102) **%60 üstü** |

Bu belge o sonucu düzeltmeye çalışmıyor, **ölçüldüğü gibi bırakıyor.** Nedeni
`CLAUDE.md` kural 4: çelişki gizlenmez. Jüriye "hibrit kazandı" demek için elde
kanıt yok; elde olan kanıt tersini söylüyor ve **sebebi mekanik olarak
açıklanabiliyor** (bkz. §4).

---

## 1. Ablasyon tablosu (eşleştirici `strict`)

n = 20 belge, 12 alan. Bootstrap 1000 yeniden örnekleme, belge düzeyinde, seed 42.

| konfig | mikro-F1 | makro-F1 | mikro-F1 %95 GA | halüsinasyon | mikro-F1 (zor, n=1) |
|---|---|---|---|---|---|
| `kural` | **0.612** | **0.560** | 0.612 [0.483–0.716] | **0.102** | 0.667 |
| `llm` | 0.169 | 0.164 | 0.169 [0.095–0.242] | 0.145 | 0.286 |
| `hibrit` | 0.575 | 0.522 | 0.575 [0.443–0.688] | 0.163 | 0.667 |
| `hibrit-verify` | 0.562 | 0.507 | 0.562 [0.426–0.675] | 0.163 | 0.333 |

`tolerant` eşleştiricide `kural`, `llm` ve `hibrit` satırları **birebir aynı**;
tek fark `hibrit-verify` 0,562 → 0,575 (yani tolerant eşleştirme, doğrulama
kolunun bozduğu tek kararı bağışlıyor). Tam tablo:
`eval/reports/20260804-215208/report.md`.

> **Künyedeki `git_dirty` hakkında — sayıdan şüphe edilmesin.** `215206`
> (strict) `git_dirty: False`, `215208` (tolerant) ise `git_dirty: True`
> gösteriyor. İkisi **1,4 saniye arayla, aynı sabitlenmiş ağaçta** koştu ve kod
> aynıydı; ikinci koşumun kirli görünmesinin sebebi **birinci koşumun kendi
> rapor dosyalarını o ağaca yazması.** Yani bayrak kendi kendini tetikledi,
> ölçüm kirlenmedi. (Ölçüm hijyeni açısından doğru düzeltme raporları çalışma
> ağacının dışına yazmak; ayrı iş olarak not edildi.)
>
> Ayrıca `git_dirty: True` taşıyan ve **commit'lenmeyen** bir üçüncü koşum vardı
> (`20260804-211513`, sha `1a9c00d`): o gerçekten kirliydi — paralel ajanlar
> koşum sırasında `src/extraction/rules/` altını değiştirdi ve `kural` satırı
> aynı oturumda 0,578 ile 0,612 arasında oynadı. Yanıltıcı olacağı için depoya
> alınmadı; tablo yalnız sabitlenmiş ağaçtaki koşuma dayanıyor.

### Güven aralıkları geniş — nokta tahminine güvenilmemeli

GA genişlikleri 0,23–0,25 bandında. n = 20 belgede bu **kaçınılmazdır** ve
tablodaki sıralamanın bir kısmı gürültü olabilir. Somut olarak:

- `kural` [0.483–0.716] ile `hibrit` [0.443–0.688] aralıkları **büyük ölçüde
  örtüşüyor.** İki bağımsız GA'nın örtüşmesine bakıp "fark yok" demek yaygın
  bir hatadır; doğru test **eşleşmiş** farktır (§3).
- `llm` [0.095–0.242] ise diğerleriyle **hiç örtüşmüyor** — LLM-only kolunun
  belirgin biçimde kötü olduğu n = 20'de bile güvenle söylenebilir.

### Karışıklık matrisi kırılımı — F1 nereden geliyor

| konfig | P (mikro) | R (mikro) | TP | FP | FN | TN | FP (yanlış değer) | FP (uydurma) |
|---|---|---|---|---|---|---|---|---|
| `kural` | 0.594 | 0.631 | 41 | **28** | 24 | 149 | 11 | **17** |
| `llm` | 0.169 | 0.169 | 11 | 54 | 54 | 142 | 30 | 24 |
| `hibrit` | 0.519 | **0.646** | **42** | 39 | **23** | 139 | 12 | 27 |
| `hibrit-verify` | 0.506 | 0.631 | 41 | 40 | 24 | 139 | 13 | 27 |

Tablonun tek satırda özeti: **hibrit +1 TP kazanıyor, +11 FP kaybediyor.**
Geri çağırma 0,631 → 0,646 çıkıyor; precision 0,594 → 0,519 düşüyor. F1 bu
takasta kaybediyor.

---

## 2. Hangi konfig hangi ALANDA kazanıyor

| alan | `kural` | `llm` | `hibrit` | `hibrit-verify` | gold desteği |
|---|---|---|---|---|---|
| `alisveris_puani` | 0.000 | 0.000 | 0.000 | 0.000 | 1 |
| `finansman_tutari` | **0.444** | 0.182 | **0.444** | **0.444** | 6 |
| `hedef_kitle` | **0.727** | 0.133 | 0.500 | 0.500 | 5 |
| `indirim_orani` | **1.000** | 0.000 | **1.000** | **1.000** | 1 |
| `kampanya_kosullari` | **0.733** | 0.000 | **0.733** | **0.733** | 12 |
| `kampanya_suresi` | **0.308** | 0.000 | **0.308** | **0.308** | 6 |
| `kar_payi_orani` | **0.667** | 0.000 | 0.545 | 0.364 | 4 |
| `masraf_durumu` | **0.857** | 0.133 | 0.750 | 0.750 | 7 |
| `odul_miktari` | **0.400** | **0.400** | **0.400** | **0.400** | 3 |
| `tahsis_ucreti` | **0.400** | 0.333 | 0.333 | 0.333 | 2 |
| `taksit_sayisi` | 0.600 | 0.200 | **0.667** | **0.667** | 7 |
| `vade_ay` | 0.583 | **0.588** | 0.583 | 0.583 | 11 |

**LLM'in kazandığı yer yalnız iki alan, ikisi de kıl payı:**
`vade_ay` (0,588 vs 0,583) ve hibrit üzerinden `taksit_sayisi` (0,667 vs 0,600).
Toplam 12 alanın **9'unda kural katmanı tek başına en iyi ya da eşit.**

**LLM'in bozduğu yerler ve nedeni** (`per_field.csv`'den, `strict`):

| alan | kural | hibrit | ne oldu |
|---|---|---|---|
| `hedef_kitle` | 0.727 (TP 4, FP 2, uydurma 2) | 0.500 (TP 4, FP 7, uydurma **6**) | TP hiç artmadı; LLM gold'un "YOK" dediği 4 belgede değer uydurdu |
| `masraf_durumu` | 0.857 (TP 6, FP 1, uydurma 0) | 0.750 (TP 6, FP 3, uydurma **2**) | Aynı desen: TP sabit, uydurma eklendi |
| `kar_payi_orani` | 0.667 | 0.545 | Kuralın boş bıraktığı yeri LLM yanlış doldurdu |

Desen tek ve nettir: **hibridin kaybı geri çağırma kaybı değil, precision
kaybıdır** ve kaynağı gold'un `absent` dediği alanlara LLM'in değer üretmesidir.

---

## 3. İstatistiksel karşılaştırma (McNemar, eşleşmiş çiftler)

Eşleşmiş çift = (belge, alan) kararı. Test yalnız **uyumsuz** çiftlere bakar.

| A | B | b | c | uyumsuz | p | yöntem | sonuç | mikro-F1 farkı (A−B) %95 GA |
|---|---|---|---|---|---|---|---|---|
| `kural` | `llm` | 52 | 15 | 67 | 1.092e-05 | χ² (süreklilik) | **kazanan `kural`** | 0.443 [0.290–0.581] |
| `kural` | `hibrit` | 10 | 1 | 11 | 0.01172 | tam binom | **kazanan `kural`** | 0.037 [-0.004–0.072] |
| `kural` | `hibrit-verify` | 11 | 1 | 12 | 0.006348 | tam binom | **kazanan `kural`** | 0.050 [0.003–0.095] |
| `llm` | `hibrit` | 15 | 43 | 58 | 0.0003922 | χ² (süreklilik) | **kazanan `hibrit`** | -0.406 [-0.555–-0.256] |
| `llm` | `hibrit-verify` | 15 | 42 | 57 | 0.0005736 | χ² (süreklilik) | **kazanan `hibrit-verify`** | -0.392 [-0.554–-0.235] |
| `hibrit` | `hibrit-verify` | 1 | 0 | 1 | 1 | tam binom | fark anlamsız | 0.014 [0.000–0.047] |

### İki testin çeliştiği yer — dürüstçe yazılmalı

`kural` vs `hibrit` satırında iki ölçüt **aynı yöne işaret etmiyor**:

- **McNemar anlamlı** (p = 0,0117): hibrit 10 kararı bozup yalnız 1 karar
  kazandı. Karar düzeyinde bu tesadüf değil.
- **Mikro-F1 farkının GA'sı 0'ı içeriyor** ([-0.004–0.072]): toplu metrik
  düzeyinde fark kanıtlanmadı.

Çelişki değil, **iki farklı soruya iki farklı cevap**: "hibrit kararları
bozuyor mu?" → evet, sistematik olarak. "Bu bozulma toplam F1'i kesin
düşürüyor mu?" → n = 20'de kesin diyemiyoruz. Doğru okuma: *hibridin kural
katmanını geçtiğine dair hiçbir kanıt yok; bozduğuna dair karar düzeyinde
kanıt var.*

### `hibrit-verify` kolu kazanç sağlamadı

`reconcile.verify_low_conf` (eşik 0,75) düşük güvenli KURAL alanlarını LLM'e
doğrulatır. Hibrit ile farkı **anlamsız** (b=1, c=0, p=1) ve `strict`'te
0,013 puan **daha kötü**. `kar_payi_orani`'nda belirgin zarar veriyor
(0,545 → 0,364): LLM, kuralın doğru ama düşük güvenli değerini yanlışla
değiştiriyor.

`reconcile.py` docstring'i bu kolun *"kanıtlanmadan varsayılan hâline
getirilmeyeceğini"* söylüyordu. **Kanıt geldi ve olumsuz** — varsayılan
`0.0` kalmalı.

---

## 4. Neden hibrit kaybediyor — mimari sebep

`src/extraction/reconcile.py` sözleşmesi: **kural birincil, LLM yalnız
boşlukları doldurur.** Bunun iki matematiksel sonucu var ve ikisi de ölçümde
görünüyor:

1. **Hibrit, kural katmanının FP'lerini ASLA düzeltemez.** Kural bir alanda
   değer ürettiyse o alan LLM'e hiç sorulmaz. Bu yüzden `finansman_tutari` ve
   `alisveris_puani` satırlarında `kural` ile `hibrit` **birebir aynı** —
   LLM o alanlara hiç bakmadı.
2. **Hibrit yalnız FP EKLEYEBİLİR.** Kuralın boş bıraktığı her alan LLM'e
   sorulur; LLM "bilmiyorum" demek yerine değer üretme eğilimindedir ve
   gold o alan için `absent` diyorsa sonuç doğrudan halüsinasyon FP'sidir.

Yani hibridin F1 üzerindeki etkisi yapısal olarak **asimetriktir**: kazanç
tavanı "kuralın kaçırdığı gerçek değerler" ile sınırlı, kayıp tabanı ise
"kuralın boş bıraktığı tüm absent alanlar" kadar geniş. Ölçüm bu asimetriyi
doğruluyor: +1 TP karşılığında +11 FP.

**Uydurma FP sayısı 17 → 27.** `CLAUDE.md` §3'ün *"halüsinasyon en büyük
risk"* uyarısı burada sayıya dönüştü.

---

## 5. Görevin sorduğu iki alan: LLM düzeltiyor mu?

Soru şuydu: kural katmanının 0,000 aldığı `finansman_tutari` ve
`alisveris_puani` alanlarını LLM düzeltiyor mu?

**Cevap: hayır. İkisini de düzeltmiyor.**

| alan | kural (düzeltme ÖNCESİ) | kural (bugün) | `llm` | `hibrit` | kim düzeltti |
|---|---|---|---|---|---|
| `finansman_tutari` | 0.000 | **0.444** | 0.182 | 0.444 | **kural katmanı onarımı** (commit `caa260e`), LLM değil |
| `alisveris_puani` | 0.000 | 0.000 | 0.000 | 0.000 | **hiçbiri** |

- `finansman_tutari` 0,000'dan 0,444'e çıktı ama bu **LLM'in katkısı değil**;
  `extract_tutar`'ın cümle sınırını aşan yakınlık deseni onarıldığı için çıktı.
  LLM tek başına bu alanda 0,182 alıyor (TP 1, FP 4) — kuralın yarısından az.
- `alisveris_puani` **dört kolda da 0,000.** Gold desteği yalnız 1 belge;
  kural o belgede yanlış değer üretiyor (`fp_wrong=1`), LLM ise farklı bir
  belgede uydurma yapıyor (`fp_hallucinated=1`). Hibrit kuralı tercih ettiği
  için sonuç değişmiyor.

### Bu iki alan zaten güvenilir ölçülemiyor

`data/gold/review/_hakem-turu-01-finansman-tutari.md` bu alanlarda **2
muhtemel gold hatası ve 2 sözleşme boşluğu** kaydediyor (ör. `turkiye-finans`
belgelerinde 20.000.000 ve 2.000.000 değerleri finansman tutarı değil
**konut/araç fiyat dilimi**; `alisveris_puani`'nda işlem başına ödül mü toplam
ödül mü sorusu cevapsız).

Sonuç: `finansman_tutari` 0,444 ve `alisveris_puani` 0,000, kural katmanını
**hak ettiğinden kötü** gösteriyor. n = 20'de tek bir yanlış etiket bir alanı
sıfırlayabilir — `alisveris_puani`'nda gold desteği **1 belge** olduğu için o
alanın F1'i tam anlamıyla tek bir etikete bağlıdır ve istatistiksel olarak
yorumlanmamalıdır.

---

## 6. Kullanılan model, lisans ve `base_model` zinciri

| kalem | değer |
|---|---|
| Model | `Qwen2.5-7B-Instruct` (Ollama etiketi `qwen2.5:7b-instruct`) |
| Nicemleme | **Q4_K_M** GGUF, 7,6 B parametre, 28 katman |
| Ağırlık boyutu | 4.683.073.952 bayt (≈ 4,36 GiB) |
| Lisans | **Apache-2.0** ✅ |
| Bağlam | eğitimde 32.768; koşumda `num_ctx = 8192` |
| Çalışma zamanı | Ollama 0.30.11, `format=<json schema>` ile kısıtlı çıktı |

### Zincir köke kadar takip edildi

```
Qwen2.5-7B-Instruct  (apache-2.0)
        └── base_model: Qwen/Qwen2.5-7B  (apache-2.0)
                    └── base_model: yok  →  KÖK (sıfırdan eğitim, Qwen)
```

Llama / Gemma / non-commercial **yok**. Üç bağımsız kanıt:

1. **GGUF üstverisi** (ağırlık dosyasının içinde, offline doğrulanabilir):
   `general.license = apache-2.0`,
   `general.base_model.0.name = Qwen2.5 7B`,
   `general.base_model.0.organization = Qwen`.
2. **Paketle gelen LICENSE bloğu:** Apache License 2.0 metni birebir.
   `non-commercial`, `research only`, `Llama`, `Gemma` kelimeleri için
   tarama → **0 eşleşme**.
3. **HuggingFace model kartı** (`api/models/...`): `Qwen2.5-7B-Instruct`
   → `license: apache-2.0`, `base_model: Qwen/Qwen2.5-7B`;
   `Qwen2.5-7B` → `license: apache-2.0`, `base_model: None`.

### Ağırlık SHA-256 (envanter T-042'ye girdi)

| blob | SHA-256 |
|---|---|
| model ağırlığı (GGUF) | `2bada8a7450677000f678be90653b85d364de7db25eb5ea54136ada5f3933730` |
| LICENSE | `832dd9e00a68dd83b3c3fb9f5588dad7dcf337a0db50f7d9483f310cd292e92e` |

### Plandan sapma — neden Trendyol-LLM-8B-T1 / vLLM değil

`docker-compose.yml` ve `docs/model-license-audit.md` ana modeli
**Trendyol-LLM-8B-T1 + vLLM** olarak tanımlıyor. Bu koşumda kullanılmadı,
sebebi **donanım**:

- Plan **RTX 5060 8 GB (CUDA)** varsayıyor. Bu makine **Apple M5, 16 GB
  birleşik bellek** — CUDA yok, dolayısıyla **vLLM koşamaz**.
- `models/` dizini boş ve `.gitignore`'lu; Trendyol ağırlıkları indirilmemiş.
- Ollama + Qwen2.5-7B-Instruct **yerel önbellekte hazırdı** ve lisansı
  yukarıdaki üç kanıtla temiz çıktı.

Bu bir **kol değişikliğidir ve tabloyu etkiler**: Trendyol-LLM-8B-T1
Türkçeye özel ayarlanmış bir modeldir; Qwen2.5-7B-Instruct değildir. Yani
buradaki `llm` satırı, planlanan modelin performansının **alt sınırı** olarak
okunmalıdır — Türkçe finans metninde Türkçe-ayarlı bir modelin daha iyi
yapması beklenir. **Ama bu beklenti ölçülmedi; iddia edilmiyor.**
`model-license-audit.md`'nin "ablasyon kolu K2b" (Trendyol vs saf Qwen)
karşılaştırması **hâlâ koşulmadı.**

---

## 7. Ölçülen gecikme (envanter T-044)

Uçtan uca hibrit yolun gerçek maliyeti ilk kez ölçüldü.

| ölçüm | değer |
|---|---|
| LLM çağrı sayısı (3 kol × 20 belge) | **60** |
| Başarılı | **60** (`parse_error`, `http_error`, `schema_violation`, `repairs` = **0**) |
| Toplam duvar saati (strict geçişi) | 00:30:32 → 00:52:06 ≈ **21 dk 34 sn** |
| Ortalama (çekişmeli) | ≈ **21,6 sn** / belge / kol |
| Belge başına (çekişmesiz, izole ölçüm) | 550 karakter → **16,6 sn**; 2.528 → **50,3 sn**; 3.689 → **58,1 sn** |
| Üretim hızı | ≈ **14,5 token/sn** |
| Prompt işleme | ≈ **250–380 token/sn** |
| Bellek | ağırlık ≈ 4,4 GiB + 8K KV önbelleği — 16 GB'a rahat sığıyor |

`0 parse_error / 0 schema_violation` satırı ayrıca şunu kanıtlıyor: Ollama'nın
`format=<json schema>` kısıtlı çıktısı **20/20 belgede şemaya uydu**. LLM
katmanının kaybı ayrıştırma (parsing) kusurundan değil, **içerik yanlışlığından**
geliyor.

**Demo için sonuç:** belge başına 17–58 sn, `CLAUDE.md` §11'in *"4 dakikalık
sunumda canlı LLM = donma riski"* kararını doğruluyor. Tek belgelik "canlı
çıkarım" butonu ≈ 1 dakika sürer; toplu çıkarım demoda **koşulamaz**.

---

## 7b. `hibrit-verify` neden YAPISAL olarak ölü — güven skoru kalibre değil

Yukarıda `hibrit-verify` kolunun kazanç sağlamadığı ölçüldü. Sebebi "eşik iyi
seçilmedi" değil; o koldan kazanç çıkması **mümkün değil.**

`reconcile.py`'nin tek kaçış kapısı `verify_low_conf`: kural katmanının
**güveni eşiğin altındaki** alanları LLM'e yeniden sormak. Yani bu kapı, kural
katmanının hatalarının düşük güvenli olduğunu varsayar. Ölçüm bunu çürütüyor.

Krom kaynaklı `alisveris_puani` halüsinasyonlarının güven dağılımı
(`data/gold/preannotations.json`, gezinme bağlantısı `"(Kredi Puanı) Nedir?"`
kaynaklı kayıtlar):

| Kayıt | Güven | Kaynak |
|---|---|---|
| **41 / 41** | **0,95** | `rule_heuristic` |

Yani **saf halüsinasyonların hepsi ölçeğin en üstünde.** Üstelik 0,95 doğru
alanların da en sık değeri:

| Güven | Alan sayısı |
|---|---:|
| **0,95** | **612** |
| 0,85 | 133 |
| 0,72 | 53 |
| 0,55 | 36 |
| 0,45 | 31 |

Sonuç zinciri:

1. Halüsinasyonlar 0,95 taşıyor → eşik 0,95'in altında olduğu sürece onlara
   **hiç dokunamaz**.
2. 0,95 aynı zamanda doğru alanların modu (612 kayıt) → eşiği 0,95'in üstüne
   çıkarmak **doğru alanların çoğunu** LLM'e yeniden sordurur, yani asıl
   kaybettiren kola (FP ekleme) tam gaz basar.
3. Arada ayırt edici bir eşik **yok**. `hibrit-verify` iki uçta da kaybeder.

Bu, ablasyon tablosundaki `hibrit-verify` satırının neden `hibrit`'ten de kötü
olduğunu (0,562 vs 0,575, `kar_payi_orani` 0,667 → 0,364) eşik ayarıyla
açıklanamayacağını gösteriyor.

**Asıl kusur güven skorunun kalibre olmaması.** `CLAUDE.md` §18 "alan bazlı
güven skoru + kaynak vurgulama"yı üç yenilikçilik hedefinden **birincisi**
olarak sayıyor; hem doğru değere hem site kromundan gelen saf uydurmaya 0,95
veren bir skor açıklanabilirlik sağlamaz, yanlış güven telkin eder.

**Doğru müdahale katmanı:** güven, değerin **kanıt kalitesini** yansıtmalı —
span sayfa kromunda mı, tetikleyici sözcük ne kadar uzakta, aynı belgede kaç
rakip aday var. Bu sinyaller `rules/confidence.py`'de kısmen var
(`trigger_distance`, `candidate_count`) ama krom/gezinme bağlamı yok. Krom
kaynaklı halüsinasyonlar bu turda **çıkarıcı katmanında** düzeltildi (`caa260e`,
`d2cc832`) — doğru katman orasıydı.

### 7c. Kalibrasyon eklendi ve `hibrit-verify` DAHA DA kötüleşti — hipotez çürüdü

§7b'yi ilk yazdığımda şu tahmini kurdum: gezinme/SSS bağlamı cezası eklenirse
kural hataları eşiğin altına düşer, `verify_low_conf` onlara erişebilir hâle
gelir ve kol kurtarılabilir. **Ölçüm bu tahmini çürüttü.**

Ceza eklendi (`759a665`: gezinme/SSS bağlamındaki değer 0,95 → 0,65) ve kol
yeniden koşuldu. İki değişken birlikte değiştiği için confound ayrıştırıldı:

| kol | eşik | güven | mikro-F1 | zor (n=1) |
|---|---|---|---:|---:|
| `hibrit-verify` | 0,75 | kalibre **edilmemiş** | 0,562 | 0,333 |
| `hibrit-verify` | 0,75 | **kalibre** | **0,534** | 0,333 |
| `hibrit-verify` | 0,70 | **kalibre** | **0,521** | 0,333 |
| (karşılaştırma) `kural` | — | — | **0,612** | 0,667 |

Kalibrasyon tek başına **0,028 kaybettirdi**; eşiği 0,70'e düşürmek **0,013
daha**. İki yönde de kayıp, ve mekanizma tutarlı: ceza daha fazla kural değerini
eşiğin altına indiriyor → daha fazlası LLM'e yeniden soruluyor → `_wins()`
doğrulama alanlarında önceliği gevşettiği için LLM doğru kural değerlerini
eziyor. Sayıya dönüşü: TP 42 → 38, FP 39 → 43.

Ve artık istatistiksel olarak kanıtlı: `kural` vs `hibrit-verify` (0,70)
p = 0,00098, mikro-F1 farkı 0,091 [0,030–0,164] → **GA sıfırı içermiyor.**

**Doğru sonuç:** darboğaz doğrulama kapısının erişilebilirliği DEĞİL. Bu LLM
(Qwen2.5-7B, tek başına 0,169) bu alanlarda kural katmanından zayıf; ona
yetki veren her mekanizma doğruluk kaybettirir. Kapıyı açmak sorunu çözmüyor,
büyütüyor.

**Kalibrasyon yine de geri alınmadı** ve gerekçesi ayrı: site kromundan gelen
saf uydurmaya 0,95 vermek **kendi başına bir kusurdu** (§18'in 1 numaralı
yenilikçilik hedefi güven skoru). Düzeltmenin değeri açıklanabilirlik ve
çekimserlik (abstention); **doğrulama tetikleyicisi olarak kullanılmamalı** —
en azından bu modelle.

> **Ölçümün kendi sınırı:** bu 41 kayıt `preannotations.json`'dan (v1, 31
> Temmuz) geliyor ve krom kusuru o zamandan beri düzeltildi. Yani bugün aynı
> halüsinasyonlar üretilmiyor. Buradaki iddia "bu 41 hata hâlâ var" değil,
> **"güven skoru bu hataları ayırt edemiyordu ve kalibrasyonu bunu yapacak
> şekilde değişmedi"**.

---

## 8. Bu tablodan çıkan kararlar

1. **Teslim edilen varsayılan `hibrit` olmamalı.** `eval/predictors.py`
   `DEFAULT_CONFIG = CONFIG_HIBRIT` diyor; ölçüm `kural`ı işaret ediyor.
   Bu bir **karar gerektiren çelişkidir** (bu belge kararı vermiyor, kolu
   ölçüyor).
2. **`hibrit-verify` varsayılan yapılmamalı** — `reconcile.py`'nin koyduğu
   koşul karşılanmadı (kazanç yok, `kar_payi_orani`'nda zarar var). §7b: bu kol
   eşik ayarıyla kurtarılamaz, çünkü halüsinasyonlar da doğru alanlar da 0,95
   güven taşıyor; arada ayırt edici eşik yok.
2b. **Güven kalibrasyonu `hibrit-verify`'ı KURTARMIYOR** — §7c'de ölçüldü ve
   kolu 0,562'den 0,534'e (aynı eşikte) düşürdü. Kalibrasyon §18'in 1 numaralı
   yenilikçilik hedefi ve açıklanabilirlik için tutuluyor, ama **doğrulama
   tetikleyicisi olarak kullanılmamalı**. Darboğaz kapı değil, LLM'in kendisi.
3. **LLM katmanının asıl sorunu çekimserlik (abstention) eksikliği.** Kayıp
   geri çağırmadan değil, gold'un `absent` dediği alanlara değer
   üretmesinden geliyor. Doğru müdahale prompt/şema düzeyinde
   "bilmiyorsan alanı ATLA" kısıtı ve güven eşiği — model değiştirmek değil.
4. **n = 20 yetersiz.** GA genişlikleri 0,23–0,25. Gold seti büyütülmeden
   kollar arası 0,03–0,05 puanlık farklar karara temel yapılamaz.
5. **Zor-vaka iddiası ölçülemedi.** Gold'da 1 zor belge var; `CLAUDE.md` §6
   *"hibridin özellikle orada kazandığını göster"* diyor ama 1 belgede
   gösterilemez. Zor-vaka alt kümesi kürlenmeli.

---

## 9. Tekrar üretim

```bash
# Ollama servisi (offline, yerel)
ollama serve &

# Dört kollu ablasyon — commit 4117601, temiz ağaç
cd app
LLM_BACKEND=ollama LLM_STRICT=1 OLLAMA_MODEL=qwen2.5:7b-instruct \
OLLAMA_NUM_CTX=8192 OLLAMA_KEEP_ALIVE=120m \
.venv/bin/python eval/ablation.py \
  --gold data/gold/gold.v1.json \
  --arms kural,llm,hibrit,hibrit-verify \
  --matcher both --seed 42 --resamples 1000

# Tabloyu ölçülmüş metrics.json'dan yeniden üret (elle sayı yazma yok)
.venv/bin/python eval/ablation_report.py eval/reports/20260804-215206
```

`LLM_STRICT=1` zorunludur: onsuz LLM istemcisi kurulamazsa hata **yutulur** ve
`hibrit` kolu sessizce kural-only koşar — tablo yalan söyler.

**Ölçüm sabitlenmiş bir çalışma ağacında koşuldu.** İlk iki denemede tablo
tekrar üretilemedi çünkü paralel çalışan diğer ajanlar `src/extraction/rules/`
altını koşum sırasında değiştirdi (`kural` satırı aynı oturumda 0,578 ve 0,612
olarak iki farklı değer verdi). Bu yüzden son koşum `git worktree` ile
`4117601`'e sabitlenmiş ayrı bir ağaçta yapıldı; künyedeki
`commit'lenmemiş değişiklik: yok` satırı bunun kanıtıdır.

---

## Sources

- `eval/reports/20260804-215206/` — strict eşleştirici, ham `metrics.json` + `per_field.csv`
- `eval/reports/20260804-215208/` — tolerant eşleştirici
- `eval/ablation.py`, `eval/predictors.py`, `eval/ablation_report.py` — ölçüm hattı
- `src/extraction/reconcile.py` — hibrit sözleşmesi (kural birincil, LLM boşluk doldurur)
- `data/gold/review/_hakem-turu-01-finansman-tutari.md` — iki alandaki gold hataları
- `docs/model-license-audit.md` — model lisans denetimi (Trendyol/Qwen zincirleri)
- `docs/rapor/yapilacaklar-envanteri.md` — T-014, T-018, T-042, T-044

## Related

- `docs/rapor/olcumler.md` — konsolide ölçüm tablosu (bu sonuçlar oraya işlenmeli)
- `docs/OFFLINE-KANIT.md` — T-042/T-044 kanıt satırları (ağırlık SHA-256 yukarıda)

---

# Ek — 2026-08-07: çok-ajanlı orkestrasyon kolu

**Ölçüm HEAD'i:** `654dd1f` · **gold sha:** `29b70e09ba6b` (20 belge) ·
eşleştirici `strict`.

## Sonuç

| kol | mikro-F1 | makro-F1 | halüsinasyon | kaçırma | yanlış çıkarım |
|---|---|---|---|---|---|
| **kural** | **0,677** | **0,618** | **0,096** | 13 | 9 |
| orkestra | 0,672 | 0,613 | 0,114 | 12 | 7 |

**Orkestrasyon kural kolunu geçemedi** (Δ = −0,005) ve halüsinasyonu
kötüleştirdi (0,096 → 0,114). K3 kararı gereği `DEFAULT_CONFIG` **kural**
kalır; orkestrasyon bu tabloya ölçülmüş bir satır olarak girer.

Kazanç yok değil ama net değil: orkestrasyon bir alan daha kurtarıyor
(kaçırma 13 → 12) ve grounding hatasını azaltıyor (9 → 7) — hakem ve kanıt
kapısının hedefi tam olarak buydu ve o kısım çalışıyor. Ama karşılığında
gold'un "YOK" dediği yerlerde üç değer daha üretiyor. Net etki sıfırın hafif
altında.

## Tasarım garantisi ölçümle tuttu

Asıl bulgu bu. Önceki ölçümde hibrit kol kural kolunun **altına** düşüyordu:

| kol | mikro-F1 | halüsinasyon |
|---|---|---|
| hibrit (yazma yetkili LLM) | 0,575 | 0,163 |
| orkestra (yetkisiz LLM) | 0,672 | 0,114 |

Aradaki fark mimari: hibritte LLM alan **yazabiliyor**, orkestrasyonda yalnız
**önerebiliyor** ve hakem yalnız **reddedebiliyor**. Yetki alınınca regresyon
ortadan kalktı. "LLM ekle" 0,037 F1 kaybettiriyordu; "LLM ekle ama yazdırma"
kaybı sıfırladı.

## Tekrar üretilebilirlik — önemli uyarı

Bu kol için **tek koşuya güvenilmez**. Ölçülen davranış:

- Sabit HEAD, sabit gold, ardışık ve sakin rejimde **3 koşu birebir aynı**
  (0,672 / 0,672 / 0,672). Yani hat kendi içinde deterministik.
- Ama daha önce **aynı çıkarım koduyla** iki koşu 0,609 ve 0,638 verdi.
  Aradaki tek kod farkı rapor-only `summary()` ekiydi (saf ekleme,
  `extract()` yoluna dokunmuyor — diff'le doğrulandı). Yani sebep bizim
  kodumuzda değil.

En olası açıklama Ollama sunucu durumu: model yeniden yüklendiğinde GPU/CPU
katman bölüşümü değişiyor ve llama.cpp'de sayısal sonuç bölüşüme bağlıdır.
İkinci koşu sırasında makinede eşzamanlı başka iş de vardı.

**Operasyonel kural:** LLM kolları ölçülürken model önceden ısıtılır, başka iş
koşturulmaz ve ölçüm **3 kez** tekrarlanır; üçü aynı değilse sayı rapora
girmez. Deterministik kollar (kural) bu kuraldan muaftır.

## Kural kolundaki 0,612 → 0,677 nereden geldi

Aynı güne ait iki ayrı kazanç; **toplanmazlar, ayrı ayrı okunmalıdır**:

| adım | mikro-F1 | ne değişti |
|---|---|---|
| başlangıç | 0,612 | — |
| Faz D — üç çıkarım düzeltmesi | 0,647 | **sistem** iyileşti |
| gold hakemliği — 2 anotasyon hatası | 0,677 | **ölçüm** düzeldi, sistem aynı |

Son satırda sistem hiç değişmedi: daha önce de doğru cevap veriyordu, yanlış
gold yüzünden hatalı sayılıyordu. Tek bir "0,612 → 0,677" olarak sunmak kendi
ölçüm hatamızı sistem başarısı diye göstermek olurdu.

---

## Ek (2026-08-07) — orkestrasyon geniş sette: n=48

Orkestrasyon kolu bugüne kadar **yalnız n=20'de** ölçülmüştü (kural 0,677 /
orkestra 0,672). n=48'lik bağımsız, kör etiketlenmiş sette tekrarlandı.
Koşum: `eval/reports/20260807-223915`, `qwen2.5:7b-instruct` (Q4_K_M,
Apache-2.0), `num_ctx=8192`, bootstrap 2000, tohum 42, eşleştirici `strict`.

| kol | mikro-F1 | %95 GA | makro | F1 (zor) | TP | FP | FN |
|---|---|---|---|---|---|---|---|
| **kural** | **0,387** | [0,329–0,442] | **0,408** | **0,405** | 48 | **88** | 64 |
| orkestra | 0,377 | [0,325–0,426] | 0,404 | 0,394 | 49 | 99 | 63 |
| orkestra-hakemsiz | 0,362 | [0,308–0,414] | 0,380 | 0,377 | 49 | 110 | 63 |

Üç hata sınıfı, ayrı paydalarla:

| kol | kaçırma | yanlış çıkarım | halüsinasyon | halüsinasyon oranı |
|---|---|---|---|---|
| kural | **21** | **43** | **45** | **0,101** [45/444] |
| orkestra | 17 | 46 | 53 | 0,119 [53/444] |
| orkestra-hakemsiz | **13** | 50 | 60 | 0,135 [60/444] |

### Okunuşu: tek yönlü bir takas, üç kolda da aynı

LLM'in yetkisi arttıkça **kaçırma düşüyor** (21 → 17 → 13) ama **uydurma
artıyor** (45 → 53 → 60) ve F1 geriliyor. Mekanizma TP/FP kırılımında
çıplak: orkestra kurala göre **1 doğru** ekliyor (48 → 49) ve **11 yanlış**
(88 → 99). Hakemsiz kolda aynı 1 doğruya karşılık **22 yanlış** var.

Bu, n=20'de hibrit kolda görülen desenin **farklı bir kolda ve farklı bir
ölçekte tekrarlanmasıdır**: LLM boşluğu doldururken doğru bilgi eklemiyor,
yanlış ekliyor.

### Hakemin katkısı ÖLÇÜLDÜ

`orkestra-hakemsiz` kolu tam bu soruyu izole etmek için var. Hakem:

- halüsinasyonu **60 → 53** düşürüyor (göreli −%12),
- bedeli kaçırmanın **13 → 17** çıkması,
- McNemar `b=7, c=0`, p = 0,0156 → **anlamlı, kazanan orkestra**; eşleşmiş
  mikro-F1 farkı 0,015 [0,007–0,025], **sıfırı dışlıyor**.

Yani "ajan önerir, hakem reddeder" yetki asimetrisi **işe yarıyor ve bu
ölçülmüştür**. Ama yeterli değil: hakemli kol bile kuralı geçemiyor.

### McNemar — ve iki ölçütün ters yönde ayrışması

| A ↔ B | b | c | uyumsuz | p | kazanan | eşleşmiş fark %95 GA |
|---|---|---|---|---|---|---|
| kural ↔ orkestra | 8 | 1 | 9 | **0,0391** | **kural** | 0,010 [−0,008 – 0,026] — sıfırı **içeriyor** |
| kural ↔ orkestra-hakemsiz | 15 | 1 | 16 | **0,0005** | **kural** | 0,025 [0,005 – 0,042] — sıfırı **dışlıyor** |
| orkestra ↔ orkestra-hakemsiz | 7 | 0 | 7 | **0,0156** | **orkestra** | 0,015 [0,007 – 0,025] — sıfırı **dışlıyor** |

Üçü de tam binom (uyumsuz çift < 25). Zor-vaka alt kümesinde üç satır da
aynı yönde ve aynı anlamlılıkta.

**İlk satır dikkat ister:** McNemar farkı **anlamlı** buluyor ama bootstrap
aralığı sıfırı **içeriyor**. Bu, `gold-genisletme.md`'deki temel↔blok
vakasının **tam tersi** yönde bir ayrışma — orada bootstrap sıfırı
dışlıyordu, McNemar anlamsızdı.

İkisi çelişmiyor, farklı şeye bakıyorlar:

- **McNemar** yalnız uyumsuz kararları sayar. 9 uyumsuz karardan 8'i tek
  yönde olması, "hangi kol daha sık haklı" sorusuna güçlü bir cevaptır.
- **Bootstrap** toplam mikro-F1'in belge örneklemesi altındaki oynaklığını
  ölçer. Az sayıda kararın yönü tutarlı olsa bile toplam skora etkisi
  küçükse aralık sıfırı kapsar.

Doğru okuma: **kural daha sık haklı (yön kesin), ama toplam skora etkisi
ilan edilecek kadar büyük değil.** İki ölçütü birlikte raporlamamızın sebebi
budur; tek başına biri bu farkı ya abartır ya kaçırır.

### K-2 kapısı: kapandı, karar ölçümün

Kapı şuydu: *n=48'de orkestra kuralı GA'lar örtüşmeden geçerse varsayılan
orkestraya döner.* **Geçmedi** — üç ölçütte de kural önde (F1, makro, zor
vaka) ve McNemar kuralı kazanan ilan ediyor.

`DEFAULT_CONFIG = CONFIG_KURAL` **kalıyor**. Orkestrasyon ürüne girmiyor;
ablasyon tablosunda ölçülmüş bir satır ve mimari bir gösterim olarak kalıyor
— yetki asimetrisinin ölçülebilir katkısı (hakem, −%12 uydurma) onun
gerekçesidir.
