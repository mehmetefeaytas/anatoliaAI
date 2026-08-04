# Anotasyon Hattı Planı — LLM destekli, insan çapalı

> Kaynak: kullanıcının 5 aşamalı planı (2026-08-04). Bu belge planı olduğu gibi
> almıyor; **iki yerini alıyor, bir yerini değiştiriyor, bir kısıt ekliyor.**
> Değişikliklerin her biri gerekçeli.
>
> İlgili: `data/gold/ANNOTATION_GUIDE.md`, `data/gold/review/_bicim-karti.md`,
> `src/extraction/silver/`, `scripts/build_silver.py`, `scripts/build_gold.py`

---

## Planın aldığım iki üstünlüğü

**1. Kör ikinci anotatör.** Sizin B aşaması, A'nın kararını **görmeden** anote
ediyor. Benim ilk kurduğum gümüş hattında denetleyici öneriyi görüyordu — bu
lastik damga riski taşır (bilinen başarısızlık kipi: denetleyici onaylama
eğilimine girer, iki bağımsız oy tek oya iner). Sizin tasarımınız daha güçlü.

Bu yüzden iki hat **kasıtlı olarak farklı** kalıyor:

| Hat | Roller | Neden böyle |
|---|---|---|
| **Gümüş** (kapsam dışı bankalar, tek alan: `campaign_type`) | etiketleyici → denetleyici (öneriyi görür) | Yüksek hacim, ucuz olmalı. Kanıt kapısı zaten mekanik koruma sağlıyor. |
| **Gold** (yarışma belgeleri, 13 alan) | A → B **kör** → hakem | Ölçümün kendisi buna dayanıyor; bağımsızlık pazarlık dışı. |

**2. Üçüncü hakem farklı modelde.** Fable 5 tercihiniz doğru: aynı model
ailesinin iki oturumu **ilişkili hata** yapar (aynı önyargı, aynı kör nokta).
Farklı model, oy çeşitliliğini gerçek kılar. Hakemin kanıt zorunluluğu da
doğru konmuş.

---

## Değiştirdiğim yer: buna "gold" diyemeyiz — ölçümün çapası kaybolur

Bu, planın tek yapısal sorunu ve en önemli maddesi.

`CLAUDE.md` §16 ve şartname §6 şunu istiyor: modelin başarısını **insan
referansına** karşı ölçmek, ve `inter-annotator agreement` (Cohen κ) ile o
referansın güvenilirliğini göstermek. Eğer referansı Opus 5 üretirse:

- **Precision/recall, "model insanla ne kadar örtüşüyor"u değil, "bir model
  başka bir modelle ne kadar örtüşüyor"u ölçer.** Çıkarım hattı kural + yerel
  8B; anotatör Opus 5. Farklı modeller olduğu için tam döngüsel değil, ama
  insan referansı da değil.
- **Halüsinasyon oranı çapasız kalır.** O metrik tanımı gereği `absent`
  etiketinden hesaplanıyor ve `absent` "bir insan kontrol etti, metinde yok"
  demek. LLM'in `absent`ı, ölçülmemiş bir iddiadır.
- **κ anlamını yitirir.** İki LLM oturumu arasındaki uyum, insan anotasyonunun
  güvenilirliğini göstermez.

### Çözüm: insan çapası + iki ayrı sayı

Planı iptal etmiyorum, **çapalıyorum**:

1. **İnsan çapa kümesi.** Kalibrasyon A/B/C/D (20 belge × 13 alan) **insan**
   tarafından doldurulmaya devam eder. Bu, hattın tamamının ölçüldüğü referans.
2. **LLM hattı aynı 20 belgeyi de anote eder.** Böylece elde şu ölçülebilir:
   *"otomatik anotatör insan gold'uyla %N örtüşüyor, alan bazında dağılım şu."*
3. **Raporda iki sayı ayrı verilir:**
   - `κ(insan, insan)` — kalibrasyondan, gold setin güvenilirliği
   - `uyum(LLM, insan)` — otomatik hattın kendi doğruluğu
4. **Adlandırma dürüst olur:** LLM üretimi küme `gold` değil
   **`silver-extended`**; `gold` yalnızca insan onaylı satırları taşır.
   Uyuşmazlık ve düşük güvenli satırlar insan kuyruğuna gider.

Bu, "LLM ile anote ettik"i bir zayıflıktan **ölçülmüş bir yönteme** çevirir —
ve jüriye anlatılabilir hâle getirir. Ölçmezseniz, sorulduğunda savunacak
sayınız olmaz.

`scripts/build_silver.py score` bu ölçümü zaten yapıyor (`score_against_gold`),
ve kesişim 20'nin altındaysa uyarı basıyor — yüksek yüzdenin küçük örneklemi
gizlemesini engellemek için.

---

## Eklediğim kısıt: kanıt kapısı mekanik olmalı

Planınız `evidence` alanı istiyor — doğru. Ama LLM'in "bu alıntı belgede var"
demesi bir kanıt değil, bir beyandır. `contract.evidence_is_verbatim` bunu
**deterministik** doğruluyor: alıntı belgede birebir (boşluk/kasa toleranslı)
geçmiyorsa kayıt düşer, hiçbir LLM'e sorulmadan.

Ölçülmüş etkisi: duman testinde uydurulmuş alıntı taşıyan çerez-politikası
sayfası, iki LLM de aynı etiketi verse bile `reject / kanit_dogrulanmadi` oldu.

Bu, projenin `source_span` ilkesinin (CLAUDE.md §3) anotasyona taşınmış hâli ve
hattın en güvenilir tek savunması — çünkü modelin kendi beyanına bakmıyor.

---

## Aşama 1–2 hakkında: doğru fikir, iki not

Kapsam dışı bankalardan **önce kural tabanı** çıkarmak metodolojik olarak
güçlü: kılavuz test setinden bağımsız türetilmiş olur. Bu ayrımı koruyun.

**Not 1 — kılavuz zaten var, sıfırdan yazmayın.** `ANNOTATION_GUIDE.md` 13
alanın hepsi için pozitif/negatif/sınır vaka taşıyor. Kalibrasyon A'nın ilk
turu **8 gerçek açık** buldu ve hepsi `_bicim-karti.md`'de ara kararla kayıtlı
(tarih aralığı, para aralığı, oransal tahsis ücreti, çoklu masraf, tutara bağlı
vade, paylaşım oranı, 8 sınıf dışı tür, `campaign_type` bölümünün hiç
olmaması). Aşama 1'in çıktısı bu açıkları **kapatmak** olmalı, kılavuzu
baştan yazmak değil.

**Not 2 — yurt dışı Islamic Banking örneklerinin getirisi düşük.** Kavram
eşlemesi (murabaha, icara, mudarebe) için bir miktar değerli, ama
normalizasyon kuralları **Türkçe yüzey biçimlerine** bağlı: `1.500,00`,
`%2,05`, `31 Aralık 2026`, ALL-CAPS `ÜCRETSİZ`, şapkalı `kâr`. İngilizce
kaynaklar bunları öğretmez. Bütçeyi Türkçe klasik bankalara yığın.

---

## Çıkış formatı — mevcut derleyiciyle uyum

Planınızın alan listesi doğru; `build_gold.py`'nin sözleşmesine oturması için
üç kural zorunlu (üçü de kalibrasyon A'da ihlal edildiği ölçüldü):

| Kural | Neden |
|---|---|
| `verdict=absent` ise `gold_value` **boş** | `build_gold.py:142` `absent` görünce değeri **sessizce atar** ve modeli halüsinasyon sayar. Değer biliniyorsa doğru verdict `fix`. |
| `verdict=fix` ise `gold_value` **dolu** | `build_gold.py:147` boşsa derlemeyi durdurur. Değer bilinmiyorsa `unclear`. |
| `gold_value` **kanonik biçimde** | Aralık/serbest metin ya reddedilir ya da **sessizce yanlış ucu alır** (`"2026-01-01 - 2026-12-31"` → `2026-01-01`). Biçimler: `_bicim-karti.md` §2. |

`verdict=ok` + `gold_value=model_value` yazmanız zararsız: derleyici `ok`
yolunda `model_value`'yu alır, `gold_value`'ya bakmaz.

**Eksik olan araç:** anotasyon çıktısını üretildiği anda `parse_gold_value`'dan
geçiren bir linter. Kalibrasyon A'da 9 satır **sessizce** bozulmuştu — linter
olsaydı hiçbiri geçmezdi. LLM hattı insan hızından çok daha fazla satır
üreteceği için bu araç artık isteğe bağlı değil.

---

## Hacim gerçeği

243 belge × 13 alan = **3.159 satır**. A + kör B = **6.318** anotasyon,
üstüne uyuşmazlıklar için hakem turu. Bu, tek oturumda yapılacak iş değil;
partili (batch) koşmak ve her partiyi ayrı JSONL olarak biriktirmek gerekiyor —
sözleşme buna uygun tasarlandı (`doc_id` bazlı, tekrar eden `doc_id` sessizce
üzerine yazmıyor, hata veriyor).

Öneri sıralama: **önce çapa** (20 belgelik kalibrasyon kümesi, A+B+hakem tam
tur) → uyum sayısını ölç → sayı kabul edilebilirse kalan 223 belgeye aç.
Çapada uyum düşük çıkarsa kılavuz düzeltilir; 3.159 satırı çöpe atmaktansa 260
satırı atmak yeğdir. Bu, kılavuz §8'in insan kalibrasyonu için söylediği şeyin
LLM hattına uygulanmış hâli.
