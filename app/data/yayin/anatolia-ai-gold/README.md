---
language:
  - tr
license: apache-2.0
pretty_name: Katılım Bankacılığı Kampanya Metinleri Altın Seti
size_categories:
  - n<1K
task_categories:
  - token-classification
  - text-classification
tags:
  - turkish
  - finance
  - participation-banking
  - islamic-finance
  - information-extraction
  - teknofest
configs:
  - config_name: default
    data_files:
      - split: train
        path: train.jsonl
      - split: validation
        path: val.jsonl
      - split: test
        path: test.jsonl
  - config_name: gold_round1
    data_files:
      - split: train
        path: gold.round1.jsonl
  - config_name: gold_v2
    data_files:
      - split: train
        path: gold.v2.jsonl
---

# Anatolia AI — Katılım Bankacılığı Kampanya Metinleri Altın Seti

**Paket tarihi:** 2026-08-15 · **Lisans:** Apache-2.0 (anotasyon katmanı) — bkz. `LISANS.md`

> **Kesit uyarısı (2026-08-21):** bu paket 2026-08-15 kesitidir. 2026-08-21'de
> HAKEM-05/S1 tahkim onarımı depo gold'unu değiştirdi (round1 manşeti
> 0,793 → 0,795); güncel gold depodaki `app/data/gold/` dizinidir. Paket bir
> sonraki yayında yenilenecek.
**Dil:** Türkçe · **Alan:** katılım bankacılığı (faizsiz finans) kampanya metinleri
**Görev:** belgeden yapılandırılmış finansal bilgi çıkarımı + kampanya türü sınıflandırması

> ⚠️ **Bu setler MAKİNE anotasyonludur ve insan hakemliğinden GEÇMEMİŞTİR.**
> Ayrıntı aşağıda "Kim etiketledi" bölümünde. Bunu manşetten önce yazıyoruz
> çünkü sonradan öğrenilmesi, veri setinin bütün iddiasını çürütür.

---

## İçerik

| Dosya | Kayıt | Ne |
|---|---:|---|
| `gold.round1.jsonl` | 134 | inceleme kuyruğundan gelen **geniş** örneklem |
| `gold.v2.jsonl` | 48 | kasten **zor** seçilmiş küçük set |
| `train.jsonl` | 127 | iki setin birleşiminden, belge düzeyinde bölme |
| `val.jsonl` | 27 | " |
| `test.jsonl` | 28 | " |
| `ANNOTATION_GUIDE.md` | — | anotasyon protokolü: kararların nasıl verildiği |
| `LISANS.md` | — | lisans + veri kökeni |

Biçim **JSONL**: her satır bir JSON nesnesi, bir kayıt. Ham HTML **yoktur**;
pakette çıkarılmış metin (`text`) ve provenance alanları (`source_url`,
`content_hash`) bulunur.

---

## Alan şeması — 12 alan + `campaign_type`

| Alan | Tip | Kanonik biçim | Dolu | `absent` |
|---|---|---|---:|---:|
| `kar_payi_orani` | `float · {min,max}` | yüzde işaretsiz ondalık (`%2,05` → `2.05`); aralıksa `{min,max}` | 10 | 53 |
| `finansman_tutari` | `{value,currency}` | `{"value": 150000.0, "currency": "TRY"}` — binlik `.`, ondalık `,` çözülmüş | 26 | 48 |
| `vade_ay` | `int` | ay cinsinden tam sayı (`1 yıl` → `12`) | 38 | 72 |
| `taksit_sayisi` | `int` | taksit adedi, tam sayı | 21 | 44 |
| `tahsis_ucreti` | `{value,currency} · float` | tutar ya da oransal ücret — **bu sette 0 pozitif örnek var** (bkz. Bilinen sınırlar) | 0 | 47 |
| `masraf_durumu` | `{has_fee,amount}` | `masrafsız` → `{"has_fee": false, "amount": 0.0}`; negasyon yokluk DEĞİLDİR | 11 | 39 |
| `odul_miktari` | `{value,currency}` | parasal ödül; puan/mil ise `alisveris_puani` | 7 | 44 |
| `indirim_orani` | `float · {min,max}` | yüzde işaretsiz ondalık | 2 | 45 |
| `alisveris_puani` | `{kind,value}` | `kind` ∈ {`points`, `tl`}; mil/puan gibi parasal olmayan ödüller burada | 10 | 38 |
| `kampanya_suresi` | `str (ISO-8601)` | `YYYY-MM-DD` — aralık verilmişse **bitiş** tarihi alınır | 75 | 29 |
| `kampanya_kosullari` | `list[str]` | belgede birebir geçen koşul cümleleri (serbest metin listesi) | 39 | 16 |
| `hedef_kitle` | `list[str]` | kapalı etiket kümesinden çoklu seçim (aşağıda) | 21 | 29 |

`hedef_kitle` kapalı etiket kümesi: `yeni_musteri` · `mevcut_musteri` · `maas_musterisi` · `belirli_segment`.

**`campaign_type`** — 13. alan, 8 sınıflı kapalı küme:
`Finansman` · `İhtiyaç Finansmanı` · `Konut Finansmanı` · `Taşıt Finansmanı` · `Kart` · `Alışveriş Puanı` · `Yeni Müşteri` · `Yatırım Ürünü`.
Etiketli kayıt: `gold.round1` 114/134 ·
`gold.v2` 39/48. Etiketsiz kayıtta alan `null`'dur —
"tür yok" demek değil, **karara bağlanmadı** demektir.

### Kayıt yapısı

| Anahtar | Anlamı |
|---|---|
| `id` · `bank_slug` · `source_url` · `content_hash` | kimlik ve provenance |
| `text` | belgeden çıkarılmış düz metin (ham HTML değil) |
| `fields` | karara bağlanmış alanlar → kanonik değer |
| `field_spans` | her alanın belgedeki **birebir** kanıt alıntısı |
| `absent_fields` | "kontrol ettim, bu belgede YOK" kararı verilen alanlar |
| `campaign_type` · `hard` · `hard_tags` | tür etiketi ve zor-vaka işaretleri |
| `annotators` · `adjudicated` · `notes` | anotasyon künyesi |

---

## Protokol v2 — boş `verdict` ne demek

Her iki set de **protokol v2** ile etiketlendi. Tek cümlelik farkı şudur:

> **Boş `verdict` = KARAR VERİLMEDİ, metrik dışıdır.**

Öncülü olan protokol v1'de boş hücre `ok` (onay) sayılıyordu — yani anotatör
bir hücreye hiç dokunmadığında **modelin çıktısı onaylanmış** kabul ediliyordu.
Bu, etiketi modele çapalar ve ölçümü sistematik olarak iyimser yapar. v2 bunu
tersine çevirdi: dokunulmayan hücre ölçüme hiç girmez.

Bunun veri setindeki karşılığı üç durumlu bir ayrımdır ve **karıştırılmamalıdır**:

| Durum | Kayıttaki karşılığı | Anlamı |
|---|---|---|
| değer var | `fields[alan]` dolu | anotatör bir değere karar verdi |
| **`absent`** | alan `absent_fields` içinde | **kontrol ettim, belgede yok** |
| karar yok | alan hiçbirinde geçmiyor | bakılmadı — **metrik dışı** |

`absent` ile "karar yok" aynı şey değildir. **Halüsinasyon oranının paydası
`absent` kümesidir**: model, anotatörün "yok" dediği bir alana değer üretmişse
uydurmuştur. `absent` taşınmazsa bu oran dışarıdan yeniden üretilemez —
bu yüzden alan pakette birinci sınıf vatandaştır.

`absent` kararı: `gold.round1` **60** hücre · `gold.v2` **444** hücre.

---

## Anotatörler arası uyum (κ) — iki tur, AYRI AYRI

⛔ **Aşağıdaki iki sayı simetrik değildir ve toplanamaz, kıyaslanamaz.**

| Tur | Ölçüt | Değer | Anotatör | Protokol | Hakemlik | Rapor |
|---|---|---:|---:|---|---|---|
| **round0** | Fleiss κ | **0,302** | 4 | v1 | **SONRASI** | `data/gold/iaa-raporu-round0-kalibrasyon-v1.md` |
| **round1** | Cohen κ | **0,274** | 2 | v2 | **ÖNCESİ** | `data/gold/iaa_report_round1.md` |

Asimetri **üç** eksende birden:

1. **Hakemlik konumu.** round0'ın 0,302'si hakemlik **sonrası** bir
   durumdur (0,051 → 0,268 → 0,302 ilerlemesi kayıtlıdır); round1'in
   0,274'ü hakemlik **öncesidir**. Round1'in hakemlik sonrası
   tutarlılığı 0,844'tür — ama bu **bağımsız uyum değildir** ve manşet olarak
   kullanılmaz.
2. **Ölçüt.** Fleiss κ çok-anotatörlü, Cohen κ iki-anotatörlüdür. Farklı
   tahmin ediciler; aynı ölçekte okunamazlar.
3. **Protokol.** round0 **v1** (boş = onay, modele çapalı), round1 **v2**
   (boş = karar yok). Payda bile aynı değil.

Bu yüzden "v1'de 0,302 → v2'de 0,274, uyum düştü" **yanlış bir
cümledir**; aynı şekilde "uyum düzeliyor" da yanlıştır. İki bağımsız ölçümdür.

**Eşik anotasyon BAŞLAMADAN ilan edilmişti** (`ANNOTATION_GUIDE.md` §7):
κ ≥ 0,80 kabul · 0,67 ≤ κ < 0,80 notla kabul · κ < 0,67 zorunlu hakemlik +
kılavuz revizyonu. **Her iki tur da eşiğin altında kaldı** ve ilan edilen
sonuç uygulandı (kılavuz v1→v2 revize edildi, hakemlik koşuldu). Sayıya
bakıp eşik değiştirilmedi.

---

## Kim etiketledi — makine anotatör, makine hakem

⛔ **İNSAN HAKEMLİĞİ YAPILMADI.** Bu, setin en büyük kısıtıdır ve gizlenmez.

| Set | Anotatör | Hakemlik |
|---|---|---|
| `gold.round1` | **makine** (A–D), protokol v2 | 🟠 **makine kör hakem** — 38 kayıt `adjudicated: true` |
| `gold.v2` | **makine** (M1–M4), her değer birebir alıntı kanıtıyla | ❌ hakemlik yok (0 kayıt `adjudicated: true`) |

`gold.round1`'deki **38 kayıtlık hakemlik MAKİNE hakemliğidir.**
Uyuşmazlıklar, yalnız kendi alanının kılavuz paragrafını gören ve birbirinden
habersiz çalışan **kör** hakemlerce karara bağlandı. Protokol, hakemin
taraflardan biriyle **hem karar hem değer** olarak örtüşmesini şart koşar;
üçüncü bir cevap çıkarsa **hiçbir tarafa dokunulmaz**.

`adjudicated: true` bayrağı **"hakemlikten geçti"** der — **"insan onayladı"
demez.** Anotasyon kanıt kapılıydı (her değer belgede birebir geçen bir
alıntıya bağlı, programatik doğrulandı), ama **kanıt kapısı insan hakemliğinin
yerine geçmez**.

---

## İki set KIYASLANAMAZ — ve birleştirilerek sunulmaz

| | `gold.v2` | `gold.round1` |
|---|---:|---:|
| kayıt | 48 | 134 |
| **zor vaka** | **40** | **3** |
| `absent` kararı (halüsinasyon paydası) | **444** | **60** |
| banka | 10 | 9 |
| 12-alan mikro-F1 (referans sistem) | 0,464 | 0,744 |
| halüsinasyon oranı | **0,047** | **0,433** |

`gold.v2`'nin 40/48 kaydı **kasten zor** seçilmiştir
(koşullu aralık, format varyantı, çelişki, terminoloji tuzağı).
`gold.round1` ise inceleme kuyruğundan gelen **geniş** bir örneklemdir.
İkisi aynı sistemi ölçer ama **aynı soruyu sormaz**.

**round1'in 0,433'lük halüsinasyonu bir gerileme değil, SEÇİM ETKİSİDİR.**
round1'de bir hücre inceleme kuyruğuna **zaten model bir şey ürettiği için**
girer; yani o setin `absent` kümesi rastgele değil, düşmanca seçilmiş bir alt
kümedir. Payda 60'a düşünce oran şişer. Aynı sebeple bu iki setin
F1'lerini yan yana koyup "hangi set daha kolay" demek de yanıltıcıdır.

---

## Bölme — sızıntısız, belge düzeyinde, `seed=42`

İki setin **birleşimi** (182 kayıt) bölünür. Bölme birimi kayıt değil
**belge**dir: `source_url` ya da `content_hash` paylaşan kayıtlar tek gruba
çekilir ve grup bölünmez. Toplam 177 grup.

Bu gerekli, çünkü iki set **5 `source_url`'ü
paylaşıyor** (aynı sayfa, iki farklı hasat → farklı `content_hash`). Kayıt
düzeyinde bölseydik o belgenin bir kopyası eğitime, diğeri teste düşerdi.

| Bölme | Kayıt | Tekil belge | Oran |
|---|---:|---:|---:|
| `train.jsonl` | 127 | 124 | %69,8 |
| `val.jsonl` | 27 | 27 | %14,8 |
| `test.jsonl` | 28 | 26 | %15,4 |

Hedef oran 70/15/15;
gerçekleşen oran grup boyutları yüzünden birkaç kayıt sapabilir — grup
bölünmesindense sapma tercih edilir.

Her kayıtta iki alan bulunur: `bolme` (train/val/test) ve **`kaynak_set`**
(`gold.round1` / `gold.v2`). Kaynak seti açıkça taşıyoruz çünkü iki set
kıyaslanamaz ve karıştırmayı önleyen bilgi örtük kalmamalı; **iki set kıyaslanamaz olduğu için** bölmeleri tek
bir homojen küme gibi raporlamayın.

### Sızıntı denetimi

**0 ihlal** — hiçbir `source_url` ve hiçbir `content_hash` iki bölmede birden yok.

Denetim `scripts/veri_seti_paketle.sizinti_denetimi` ile yapılır ve
`tests/test_veri_seti_paketle.py` içinde çitlenmiştir — hem sentetik bir
sızıntı vakasıyla (denetim yakalıyor mu) hem de gerçek paketle (sıfır ihlal).

---

## Kullanım sınırı — ne söylenebilir, ne söylenemez

| Söylenebilir | Söylenemez |
|---|---|
| "182 kayıtlık, alan başına birebir kanıt alıntılı bir Türkçe katılım bankacılığı çıkarım seti" | ❌ "insan anotasyonlu altın set" |
| "`gold.round1`'de 38 kayıt kör hakemlikten geçti" | ❌ "hakemlik tamamlandı / uyuşmazlıklar çözüldü" |
| "κ round0 = 0,302 (hakemlik sonrası), round1 = 0,274 (hakemlik öncesi)" | ❌ tek bir κ vermek ya da ikisini kıyaslamak |
| "halüsinasyon `absent` paydasıyla ölçülür" | ❌ iki setin halüsinasyon oranını yan yana koymak |
| "manşet metrik `gold.v2`'de verilir — zor olan" | ❌ iki seti birleştirip tek bir F1 ilan etmek |
| "`train`/`val`/`test` belge düzeyinde ve sızıntısızdır" | ❌ "bu bölme üzerinde eğitilen model gold kalitesinde etiket öğrenir" |

**Bu set bir REFERANS setidir, eğitim seti olarak tasarlanmamıştır.** Üzerinde
eğitim yapılırsa, ölçüm o modelin **insanla** değil **başka bir makineyle**
ne kadar örtüştüğünü ölçer. Bu ayrım raporda korunmalıdır.

---

## Bilinen sınırlar — biz söylüyoruz

- **İnsan hakemliği yok** (yukarıda). Kapatılması gereken en öncelikli açık budur.
- **`tahsis_ucreti` ölçülemiyor.** Her iki sette de **0 pozitif örnek** var;
  bu alanda precision/recall/F1 **tanımsızdır**. Alan şemada duruyor çünkü
  `absent` kararları (birleşimde 47 hücre) halüsinasyon paydasına giriyor.
- **`kampanya_kosullari` span/jeton F1'i metodolojik olarak yanıltıcıdır.**
  Serbest cümle listesi döndüren bir alanda aynı koşulu farklı sözcüklerle
  yazan iki anotatör bile birbirini "yanlış" bulurdu. Kalem düzeyi ölçüt
  (jeton-Jaccard) kullanın.
- **`campaign_type` eksik.** `gold.round1`'de 20,
  `gold.v2`'de 9 kayıtta tür karara bağlanmadı.
- **Kaynak sayfalar değişir.** `content_hash` anotasyon anındaki metni çapalar;
  bugün aynı `source_url`'e gidildiğinde farklı içerik gelebilir. Nitekim iki
  setin paylaştığı 5 belgede tam olarak bu olmuştur.
- **Küme temsil edici değildir.** `gold.v2` kasten zor kürlenmiştir,
  `gold.round1` model çıktısı olan hücrelere göre süzülmüştür. Hiçbiri Türkçe
  bankacılık metinlerinin ortalama zorluğunu temsil etmez.

---

## Köken ve toplama

Metinler Türkiye'de faaliyet gösteren **10 katılım
bankasının kamuya açık** kampanya ve ürün sayfalarından toplandı. Toplama
robots.txt kurallarına uyularak, kimliğini beyan eden bir tarayıcıyla
(`AnatoliaAI-Research/1.0`) ve alan adı başına 3 saniye aralıkla yapıldı.
Giriş gerektiren hiçbir alan, **hiçbir kişisel veri** toplanmadı.

Her kayıtta `source_url` ve `content_hash` (sha256) bulunur: "bu bilgiyi
nereden aldınız" sorusunun cevabı kayıtlıdır. Ayrıntı: `docs/legal_notes.md`.

---

## Yeniden üretim

```bash
cd app
.venv/bin/python -m scripts.veri_seti_paketle
```

Paket `data/gold/gold.round1.json` ve `data/gold/gold.v2.json`'dan türetilir;
bölme `seed=42` ile deterministiktir — aynı girdi aynı bölmeyi verir.
