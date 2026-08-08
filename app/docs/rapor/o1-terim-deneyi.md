---
title: "Ö1 — terim müdahalesi üç kollu deney: sadeleştirme mi, sözlük kartı mı?"
tags: [deney, terminoloji, olcum, mentor]
date: 2026-08-07
status: stable
---

# Ö1 — sadeleştirme mi, sözlük kartı mı?

## Neden bu deney var: iki mentör kaynağı çelişiyor

**Mentör belgesi §2.3 + D2 deneyi** bir *yasak/karşılık tablosu* istiyor ve
"terimi sadeleştirince model daha iyi anlar" hipotezini kuruyor.

**mentörün maili** (avukat gözünden geçmiş ~101 terimlik sözlükle
birlikte) bunu reddediyor:

> "Birebir değiştirmek anlamda bozukluk yaratıyor… Türkçeleri aynı anlamı
> replace ile taşımıyor. O sebeple böyle bir kapsamlı analiz vermek gerekiyor.
> Bir de dönüşte atıyorum **fon ya da bono yazmak da yanlış**. Yine bunların
> jargonla cevap oluşturmak doğrusu."

Çelişki otoriteyle değil **ölçümle** kapanacaktı. Bu belgenin tezi budur.

## Yöntem — üç kol

| kol | ne yapar |
|---|---|
| **temel** | terim müdahalesi yok (`LLMOrchestrator(terim_karti=False)`) |
| **sadeleştirme** | belgedeki fıkhî terim, sözlüğün `resmi_tr` / `halk_dili` karşılığıyla **değiştirilerek** modele verilir (mentör D2) |
| **sözlük kartı** | terim değiştirilmez; `kanonik → degildir → ayrim_notu → risk_notu` kartı prompt'a **enjekte** edilir (mentör) |

Set `data/gold/gold.v2.json` (n=48, kör etiketli), bootstrap 2000, tohum 42,
eşleştirici `strict`, model `qwen2.5:7b-instruct` (Q4_K_M, Apache-2.0),
`num_ctx=8192`. Koşum süresi kol başına ~18 dk.

Değiştirme **çıplak `str.replace` ile değil**, `synonyms.keyword_pattern`
üzerinden yapıldı — projenin ölçülmüş tuzağı bu: `'fon'` deseni
`'fonksiyon'`u yakalıyordu ve korpusun %48'i sahte "Konut Finansmanı"
çıkmıştı. mentörün uyardığı kelime tam olarak "fon".

## Sonuç 1 — F1'de kazanan yok

| kol | mikro-F1 | %95 GA | makro-F1 | kaçırma | yanlış çıkarım | halüsinasyon |
|---|---|---|---|---|---|---|
| temel | 0,375 | [0,323–0,425] | 0,404 | 17 | 46 | 0,122 [54/444] |
| sadeleştirme | 0,380 | [0,327–0,432] | 0,406 | 17 | 46 | 0,115 [51/444] |
| sözlük kartı | 0,377 | [0,325–0,426] | 0,404 | 17 | 46 | 0,119 [53/444] |
| *kural (referans)* | *0,387* | *[0,329–0,442]* | — | *21* | — | *0,101 [45/444]* |

Farklar: temel−sadeleştirme = −0,004 · temel−sözlük kartı = −0,001 ·
sadeleştirme−sözlük kartı = +0,003. **Üçü de |Δ| < 0,05 eşiğinin altında;
n=48'de gürültüden ayırt edilemez. Kazanan ilan edilmiyor.**

Üç GA tamamen örtüşüyor ve üç kol da kural referansının altında —
`ablasyon.md`'deki n=48 bulgusuyla tutarlı.

> **n=48 uyarısı.** Bu bir sıralama sinyalidir, kesin performans ölçüsü değil.

## Sonuç 2 — asıl bulgu: metrik zararı GÖREMİYOR

Deneyin LLM koşulmadan önceki deterministik metin analizi çok daha net
konuşuyor. 48 belgede sadeleştirme **261 değişiklik** yaptı; bunların
**43'ü (%16,5) anlam bozucu**, 10 belgeyi etkiliyor:

| çökme türü | adet | ne demek |
|---|---|---|
| **`degildir` çökmesi** | **29** | terim, sözlüğün "bu DEĞİLDİR" dediği şeyle değiştirildi |
| tekrar çökmesi | 14 | terim, aynı cümlede zaten geçen bir ifadeye eşitlendi |
| karşıtlık bağlamı | 12 | terimin karşıtıyla birlikte anıldığı cümlede değiştirildi |

En sık zararlı dönüşümler:

| dönüşüm | adet |
|---|---|
| **kira sertifikası → faizsiz tahvil** | **10** |
| kâr payı → faiz | 12 (iki yazım) |
| sukuk → Kira sertifikası | 7 |

Terime göre: `sukuk` 21 · `kar-payi` 15 · `ozel-cari-hesap` 2 · kalanlar 1'er.

### İki örnek — tek başına yeterli

**① `degildir` çökmesi.** Vakıf Katılım, özel cari hesap sayfası:

> özgün: "…para yatırılıp çekilebilen ve **kâr payı** dağıtımı yapılmayan
> hesaplardır."
> sadeleşmiş: "…para yatırılıp çekilebilen ve **faiz** dağıtımı yapılmayan
> hesaplardır."

Bir katılım bankasının kendi sayfasına "faiz" sokuldu. Üstelik cümle
anlamsızlaştı: katılım bankası hesabının faiz dağıtmaması zaten tanım
gereğidir; özgün cümlenin söylediği şey — bu hesabın **kâr payı da**
dağıtmadığı — kayboldu. Ürünü ayırt eden tek bilgi silindi.

**② Mailin birebir uyardığı vaka.** `kira sertifikası → faizsiz tahvil`,
**10 kez**. mentör "dönüşte fon ya da bono yazmak da yanlış" diye
yazmıştı; sukuk bir borç senedi değil varlığa dayalı ortaklık belgesidir,
"tahvil" demek onu fıkhen yanlış bir enstrüman sınıfına sokar.

### Neden F1 bunu yakalamadı

Gold alanları oran, tutar, vade, taksit, tarih — **sayısal ve yapısal**.
Bir belgede "kâr payı" yerine "faiz" yazması, oranın **%2,05 olduğunu
değiştirmiyor**. Model sayıyı yine buluyor, F1 kıpırdamıyor.

Zarar **cevabın kendisinde**: chatbot bu metinden konuşurken kullanıcıya
"faiz" ve "tahvil" diyor. Bu, alan çıkarımı metriğinin ölçmediği bir
yüzey — güvenlik seti (`data/safety/katilim-guvenlik-seti.jsonl`,
terminoloji kapısı) ve `jargon_lint` orayı ölçüyor.

**Ö1, mentörün iddiasını yanlış yüzeyde sınamış.** Bu da bir
bulgudur: mailin itirazı çıkarım doğruluğuna değil, **cevap kalitesine**
dairdi ve haklıydı.

## Karar

| soru | cevap | dayanak |
|---|---|---|
| Sadeleştirme çıkarımı iyileştiriyor mu? | **Hayır** — fark gürültü içinde | üç kolun GA'ları örtüşüyor |
| Sadeleştirmenin ölçülebilir zararı var mı? | **Evet** — 261 değişikliğin 43'ü anlam bozucu | deterministik analiz, 43 örnek kayıtlı |
| Sözlük kartı zarar veriyor mu? | **Hayır** — ne kazancı ne kaybı ölçülebilir | Δ = −0,001 |

**Sadeleştirme reddedildi.** Ölçülebilir kazancı yok, ölçülebilir zararı var.
Mentör belgesinin §2.3 tablosu bir *dönüşüm kuralı* olarak kullanılmaz;
kendi çıktımız için bir *tespit hedefi* olarak kalır (`jargon_lint`).

**Sözlük kartı korunuyor.** Çıkarım F1'ine katkısı ölçülemedi, ama zararı da
yok ve `degildir` / `ayrim_notu` alanları güvenlik kapısının dayanağı.
Terim enjeksiyonu kararı `decisions/terim-sozlugu-enjeksiyon-replace-degil.md`
belgesinde zaten kayıtlı; bu deney onu **ölçümle** destekliyor.

## Yan doğrulama — bağlam bütçesi tutuyor

Sözlüğün tamamı ~45.000 karakter, `num_ctx=8192`. Ollama bağlamı **baştan
sessizce kırpar** ve sistem prompt'unu yok eder, yani bütçe aşımı sessiz bir
kalite kaybıdır. Ölçüldü:

| ölçüm | değer |
|---|---|
| kart bütçesi | 1500 karakter / en fazla 6 kart |
| bütçeyi aşan belge | **0 / 48** |
| en büyük kart metni | 1427 karakter |
| ortalama kart metni | 314 karakter |
| kart üreten belge | 24 / 48 |

`relevant_terms(text, limit=…)` deterministik yönlendiricisi işini yapıyor.

## Tekrar üretim

```bash
LLM_BACKEND=ollama LLM_STRICT=1 OLLAMA_NUM_CTX=8192 OLLAMA_TIMEOUT=1200 \
  .venv/bin/python -m scripts.eval_o1 --gold data/gold/gold.v2.json --resamples 2000
# LLM olmadan yalnız metin analizi:
.venv/bin/python -m scripts.eval_o1 --sadece-analiz
```

## Sources
- `data/eval/o1-sonuc.json` — üç kolun metrikleri
- `data/eval/o1-metin-analizi.json` — kart bütçesi + değişim sayıları
- `data/eval/o1-sadelestirme-ornekleri.json` — 43 anlam bozucu vakanın tamamı

## Related
- [[ablasyon]] — n=48'de kural kolu üç kolu da geçiyor
- [[gold-genisletme]] — n=48 setinin kurulumu ve kör protokol
