# DEVAM NOTU — Gümüş etiketleme: ETİKETLEYİCİ turu bitti, DENETLEYİCİ sırada

> Yazıldı: 2026-08-04. Bu oturum **yalnız etiketleyici** rolünü oynadı.
> Öncesi: `docs/rapor/devam-konut-tasit-hasati.md` (belgeler toplandı,
> etiketlenmedi).
>
> İlgili: `src/extraction/silver/{contract,prompts,consensus}.py` ·
> `scripts/build_silver.py` · `docs/kampanya-turu-sinif-kurallari.md`

---

## 0. ÖNCE BUNU OKU — bu oturum neyi KASITEN yapmadı

`verdicts.jsonl` **üretilmedi**. `data/silver/silver.jsonl` içindeki sınıf
sayıları bu commit'te de **değişmedi** (Konut 13, Taşıt 9).

Sebep teknik değil, köken (provenance) ile ilgili. `consensus.decide()` bir
kaydı `silver` sayması için **iki BAĞIMSIZ LLM oyu** ister. Aynı oturum hem
etiketleyici hem denetleyici olursa iki oy tek oya iner; `consensus.py` bu
başarısızlık kipini adıyla anıyor ("lastik damga") ve `VerifyVerdict.own_label`
ayrı bir alan olarak yalnız bunu engellemek için var. Sayıyı 20 hedefine
çıkarmak için sahte bir bağımsız oy üretmek, sınıf sayısını yükseltir ama veri
setinin kökenini savunulamaz kılar (şartname §8). Yapılmadı.

**Yani sınıf sayıları, AYRI bir oturumda `verdicts.jsonl` üretilene kadar
artmayacak.**

---

## 1. YAPILAN — ölçülmüş sayılar

### 1.1 Etiketlenen belgeler

`data/raw-classic/*/products/` altındaki **106 yeni ürün belgesinin tamamı**
etiketlendi → `data/silver/proposals_5.jsonl` (yeni dosya, mevcutların üzerine
yazılmadı). Aynı 106 kayıt `data/silver/proposals.jsonl` sonuna da eklendi:
**502 → 608**. `load_proposals` her iki dosyada da mükerrer doc_id bulmadan
geçiyor (çakışma 0).

`labeler` alanı: `opus-5-batch5`.

### 1.2 Sınıf dağılımı (106 belge)

| Sınıf | Sayı |
|---|---:|
| **Konut Finansmanı** | **43** |
| **Taşıt Finansmanı** | **38** |
| `null` (taksonomi dışı / ürün sayfası değil) | 17 |
| İhtiyaç Finansmanı | 4 |
| Finansman | 3 |
| Yatırım Ürünü | 1 |
| **Toplam** | **106** |

Etiketli 89, `null` 17.

### 1.3 Güven dağılımı (etiketli 89 kayıt)

| Güven bandı | Sayı |
|---|---:|
| ≥ 0.85 | 52 |
| 0.70 – 0.84 | 20 |
| 0.55 – 0.69 | 13 |
| < 0.55 | 4 |

### 1.4 Konut / Taşıt hedefi — ÜST SINIR, sonuç değil

| Sınıf | Gümüşte şu an | Bu turdan aday | Hepsi geçerse | Hedef |
|---|---:|---:|---:|---:|
| Konut Finansmanı | 13 | 43 | 56 | 20 |
| Taşıt Finansmanı | 9 | 38 | 47 | 20 |

**Bu bir üst sınırdır.** Denetleyici ayrışırsa (ya da kanıtı desteklemez
bulursa) kayıt kuyruğa düşer. `merge` koştuktan sonra gerçek sayı
`data/silver/silver_report.json` içindeki `sinif_dagilimi` alanında yazacak.
Kaba beklenti: 0.85+ bandındaki 52 kaydın çoğu geçer → hedef (20/20) rahatça
tutar; ama bu **tahmin**, ölçüm değil.

---

## 2. BULUNAN VE DÜZELTİLEN GERÇEK KUSUR — prompt kırpma penceresi

`prompts.py` metni **6000 karaktere** kırpıyordu. Gerekçe docstring'de yazılıydı:
*"kampanya sayfalarının ana konusu başta geçer"*. Bu varsayım KAMPANYA
sayfaları için doğru, **ÜRÜN sayfaları için yanlış** — ürün sayfalarında başta
dev bir gezinme bloğu var, gövde ortada.

Ölçüm (106 ürün belgesi, sınıfı gerekçelendiren alıntının konumu):

| Grup | Alıntının konumu |
|---|---|
| Yapı Kredi (10 belge) | **~17.500 – 18.400** karakter |
| Garanti BBVA (10 belge) | ~6.000 – 6.200 karakter |
| kalan 76 belge | < 6.000 karakter |

Etiketlenebilir 96 belgenin **20'sinde (%21)** gövde 6000 penceresinin
tamamen dışındaydı. Yapı Kredi'nin 6000 karakterlik penceresinde **tek satır
ürün metni yok** — yalnız menü.

**Neden sessiz bir başarısızlık:** `consensus.decide` kanıtı **TAM** metinde
arar (`evidence_is_verbatim(texts[doc_id], ...)`), denetleyici ise **KIRPILMIŞ**
metinde. Doğru bir alıntı mekanik kapıdan geçip denetleyici tarafından
"belgede yok" diye reddedilir → `R_EVIDENCE_WEAK` → kuyruk. Kayıp tam olarak
hasadın amacı olan Konut/Taşıt belgelerinde yoğunlaşıyordu.

**Düzeltme:** `prompts.MAX_PROMPT_CHARS = 24000` (ölçülen en uzak konum 18.321
+ pay). Kırpma kaldırılmadı; `note` işaretlemesi korundu.

Test çiti: `tests/test_silver.py::TestPromptKirpmasi` (4 test) — pencere
ölçülen gövde konumunu kapsıyor mu, etiketleyici ve denetleyici **aynı**
gövdeyi görüyor mu, kırpma bilgisi hâlâ işaretleniyor mu.

### 2.1 TUZAK — `batch.jsonl` bayat

`data/silver/batch.jsonl` **eski 6000 penceresiyle** üretilmişti ve bu oturumda
yenilenmedi (kapsam dışıydı). Denetleyici turundan önce `prepare` yeniden
koşulmalı, yoksa Yapı Kredi belgeleri yine menü metniyle gider.

---

## 3. `evidence_weak` kayıtları — 5'i düzeltildi, işaret KALDI

`scripts/resolve_queue.py:227` beş kaydı `evidence_weak: true` işaretlemişti.
Ölçüm: beşinin de alıntısı belgede **birebir geçiyordu** (uydurma yoktu); sorun
alıntının gezinme/şablon metni olması ve etiketi gerekçelendirmemesiydi
(ör. `"SecondaryPageContent ShortDescription"`, breadcrumb kırıntıları).

Beşinin de alıntısı, aynı belgeden **etiketi gerçekten gerekçelendiren** birebir
bir alıntıyla değiştirildi. Doğrulama: 5/5 `evidence_is_verbatim` ✓ ve 5/5
`MAX_PROMPT_CHARS` penceresi içinde ✓.

Eklenen alanlar (silme yok):

```json
"evidence_previous": "<eski alıntı>",
"evidence_fix": {"by": "opus-5-batch5-etiketleyici",
                 "reason": "<neden yetersizdi>", "verified": false}
```

**`evidence_weak: true` KASITEN duruyor.** Bu işaret alıntının kalitesini değil
**denetim durumunu** taşıyor: olumsuz kararı veren bağımsız denetleyiciydi,
etiketleyici kendi yeni alıntısını onaylayamaz — bu da lastik damganın aynısı
olurdu. İşaret ancak bağımsız bir denetleyici yeni alıntıyı onaylayınca kalkar
(bkz. §4.3).

Düzeltilen 5 kayıt:

| doc_id | etiket |
|---|---|
| `is-bankasi--kampanyalar-a101de-taksit-firsati` | Kart |
| `is-bankasi--kampanyalar-akzonobel-ilave-taksit-kampanyasi` | Kart |
| `ziraat-bankasi--kredi-kartlari-bankkart` | Kart |
| `ziraat-bankasi--kredi-kartlari-bankkart-gold` | Kart |
| `ziraat-bankasi--genel-ihtiyaclar-dijital-kredi` | İhtiyaç Finansmanı |

---

## 4. DENETLEYİCİNİN YAPMASI GEREKEN

> **AYRI bir oturum / ayrı bir model olmalı.** Bu oturumun devamı olarak
> koşulursa üretilen `verdicts.jsonl` geçersizdir — iki oy tek oya iner.

### 4.1 Komutlar

```bash
cd app

# (a) batch.jsonl'i YENİ pencereyle tazele — §2.1 tuzağı
.venv/bin/python scripts/build_silver.py prepare \
    --docs data/raw-classic --out data/silver/batch.jsonl

# (b) denetim partisini çıkar (608 önerinin label!=null olanları)
.venv/bin/python scripts/build_silver.py prepare-verify \
    --docs data/raw-classic --proposals data/silver/proposals.jsonl \
    --out data/silver/verify_in_4.jsonl

# (c) repo DIŞI: verdicts_4.jsonl üret (yalnız 106 yeni doc_id için;
#     verdicts.jsonl'daki mevcut kararlar korunacak), sonra birleştir

# (d) uzlaşma — silver.jsonl'i YENİDEN ÜRETİR, önce yedek al
cp data/silver/silver.jsonl data/silver/silver.jsonl.bak
.venv/bin/python scripts/build_silver.py merge \
    --docs data/raw-classic \
    --proposals data/silver/proposals.jsonl \
    --verdicts data/silver/verdicts.jsonl \
    --out-dir data/silver
```

### 4.2 `merge` iki şeyi SİLER — bilerek gir

1. `merge` `silver.jsonl`'i **baştan yazar**, eklemez. `resolve_queue.py --apply`
   ile sonradan eklenen kayıtlar (§3'teki 5 düzeltme dahil) kaybolur.
   `resolve_queue` merge'den SONRA tekrar koşulmalı.
2. `queue.jsonl` ve `rejected.jsonl` da üzerine yazılır.

### 4.3 Öncelikli bakılacaklar

**(a) Prompt penceresinin gerçekten açıldığını doğrula.** Denetim isteğinde
Yapı Kredi belgelerinin gövdesi görünüyor mu? Görünmüyorsa (a) adımı
atlanmıştır; kararları verme, önce `prepare`i koş.

**(b) §3'teki 5 düzeltilmiş alıntı.** Bunlar kasten `evidence_weak: true`
bırakıldı. Yeni alıntıyı bağımsız olarak yargıla; desteklediğine karar
verirsen `evidence_fix.verified` alanını `true` yap ve `evidence_weak`
işaretini kaldır. Desteklemiyorsa **kaldırma** — işaretli kalsın.

**(c) Ölçülmüş 8 kural boşluğu — bu belgeler ayrışma bekliyor.** Düşük güvenle
işaretlendiler; `docs/kampanya-turu-sinif-kurallari.md` bu sınırları
tanımlamıyor. Ayrışırsan bu bilgidir, gizleme:

| doc_id | verilen | güven | boşluk |
|---|---|---:|---|
| `akbank--konut-kredileri-isyeri-yatirim-kredisi` | Finansman | 0.4 | **İşyeri/ticari gayrimenkul alım kredisi hiçbir kapıya düşmüyor.** Kural sırası: 4 (amaca bağlı → Konut/Taşıt) tutmuyor (işyeri konut değil), 5 (genel amaçlı) tutmuyor (amaca bağlı), 6 (bireysel değil / rotatif) tutmuyor. Artakalan sınıf olarak Finansman verildi. |
| `halkbank--konut-kredileri-isyeri` | Finansman | 0.4 | aynı boşluk; üstelik metin borçlanının **bireysel** olduğunu söylüyor ("Ticari faaliyeti olmayan bireyler") |
| `yapi-kredi--konut-kredisi-anahtar-teslim-mortgage` | İhtiyaç Finansmanı | 0.5 | Sayfa Konut Kredisi ailesinde ve "Mortgage" adını taşıyor, ama sattığı ürün metinde birebir **"İhtiyaç Kredisi"** (ev alım masraflarını konut faiz oranıyla taksitlendirme). Kural 1 (sattığı ürün) → İhtiyaç; ürün ailesi → Konut. |
| `teb--teb-oto-finans-tasit-kredi` | Taşıt Finansmanı | 0.5 | 2 KB'lik salt ön başvuru formu; ürün terimi yalnız başlıkta |
| `ing--krediler-tasit-kredisi-randevu-talep-formu` | Taşıt Finansmanı | 0.55 | aynı: randevu formu. Emsal `teb--tasit-kredisi-basvurusu` (gümüşte, Taşıt) |
| `akbank--konut-kredileri-odeme-plani-turleri` | Konut Finansmanı | 0.55 | hub sayfası: 5 mortgage varyantı listeliyor. Emsal ikiye ayrılıyor — tek aileli hub'lar etiketlendi (`vakifbank--krediler-saripanjur-ev-kredisi` 0.85), çok aileli hub'lar `null` (`teb--krediler`, `vakifbank--bireysel-krediler`) |
| `halkbank--konut-kredileri-konut-finansmani` | Konut Finansmanı | 0.55 | mevzuat/sistem anlatım sayfası ama ürün iddiası da taşıyor ("kira öder gibi ev sahibi olabilirsiniz") |
| `garanti-bbva--krediler-mortgage-uzmani` | Konut Finansmanı | 0.55 | danışmanlık hizmeti sayfası, konut kredisini pazarlıyor |

**(d) `null` verilen 17 belge — uydurma yapmamak için verildi.** Ürün sayfası
değil oldukları için: 5 basın duyurusu (`is-bankasi--bankamizi-taniyin-*`),
1 basın duyurusu (`garanti-bbva--kurumsal-iletisim-tasit-kredisinde-dijital-belge-onayi`),
sözlük (`vakifbank--...-ev-kredisi-sozlugu`), SSS
(`vakifbank--...-sorularla-ev-kredisi`), evrak listesi
(`vakifbank--...-kredi-basvuru-adimlari`), mevzuat tanımı
(`vakifbank--...-konut-finansmani-mortgage`), proje dizini
(`vakifbank--...-anlasmali-projeler`), rehber
(`akbank--tasit-kredileri-2-el-tasit-alirken-dikkat-etmeniz-gerekenler`),
bayi kanalı sayfası (`akbank--tasit-kredileri-akon-tasit-kredisi-sistemi`),
TOKİ aracılık + SSS (`halkbank--konut-kredileri-toki-islemleri`), ana sayfa
(`halkbank--www-halkbank-com-tr`), çok ürünlü KOBİ limit formu
(`ing--isiniz-icin-ing-kobi-hizli-limit-basvuru-formu`), kabuk belge
(`qnb--tasit-kredileri`, 390 karakter, meta'da `content_status: kabuk`).

Bunlar `consensus`ta `taksonomi_disi` gerekçesiyle `reject` olur — beklenen
davranış, hata değil.

### 4.4 Bu oturumun kullandığı iki ek ölçüt (denetleyici katılmayabilir)

Kural belgesinde yazmıyor; tutarlılık için uygulandı ve burada açıkça
yazılıyor ki denetleyici bilinçli ayrışabilsin:

1. **Ticari/KOBİ ama amaca bağlı finansman → Konut/Taşıt Finansmanı.**
   Uygulama sırasında 4. kapı 6. kapıdan önce geliyor. Emsal: gümüşteki
   `vakifbank--krediler-ticari-tasit-kredisi` = Taşıt Finansmanı (0.85).
   Etkilenen: `akbank--kobi-kredileri-tasit-kredisi`,
   `denizbank--kobi-bankaciligi-ticari-tasit`, `ing--krediler-kobi-tasit-kredisi`,
   `garanti-bbva--krediler-tasit-kredisi`.
   **İstisna:** müteahhide proje/inşaat finansmanı satılan sayfa → Finansman
   (`qnb--kobi-kentsel-donusum-yap-sat`, 0.75) — satılan şey konut alımı değil,
   proje finansmanı.
2. **Sayfa TEKLİF veriyor mu, yoksa yalnız TANIMLIYOR mu.** Ürün iddiası
   taşıyan anlatım sayfaları etiketlendi (`halkbank--...-konut-finansmani`),
   salt mevzuat tanımı `null` bırakıldı
   (`vakifbank--...-konut-finansmani-mortgage`).

---

## 5. AÇIK UÇLAR

- **Yeni `live/` belgeleri hâlâ etiketsiz.** Bu turda `products/` altındaki 106
  belge etiketlendi; korpusta **116 yeni `live/` belgesi** daha var
  (724 belge − 608 öneri = 116). Bunlar bu oturumun kapsamı dışıydı.
  `prepare-verify` kapsam kontrolü yapmıyor, `merge` de eksik öneriyi hata
  saymıyor — yani sessizce dışarıda kalırlar.
- **`silver_report.json` güncellenmedi**: `silver.jsonl`'deki etiketler
  değişmediği (yalnız 5 alıntı düzeltildiği) için sayımlar aynı. `merge`
  koştuğunda kendisi yeniden üretecek.
- **`docs/kampanya-turu-sinif-kurallari.md`'ye Kural 6 gerekiyor:** amaca bağlı
  ama konut/taşıt olmayan gayrimenkul finansmanı (işyeri alımı). Ölçülmüş
  ihtiyaç: 2 belge, ikisi de 0.4 güvenle Finansman'a yazıldı. Kuralı bu oturum
  YAZMADI — kural yazmak tek bir etiketleyicinin işi değil (aynı bağımsızlık
  gerekçesi).
- Testler: `1133 test, çıkış kodu 0`. `ruff check src/extraction/silver
  tests/test_silver.py`: temiz.
