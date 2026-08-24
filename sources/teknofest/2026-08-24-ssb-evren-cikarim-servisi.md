---
title: "SSB EVREN Yapay Zekâ Çıkarım Servisi — Erişime Açılış Duyurusu"
tags: [kaynak, teknofest, ssb, evren, llm, altyapi, gomme, qdrant]
source: "TEKNOFEST 2026 TYDA yarışma duyurusu (e-posta, 2026-08-24) + https://evren-teknofest.ssyz.org.tr"
date: 2026-08-24
status: stable
---

# SSB EVREN Yapay Zekâ Çıkarım Servisi — Erişime Açılış Duyurusu

TEKNOFEST 2026 Yapay Zekâ Dil Ajanları Yarışması kapsamında T.C. Cumhurbaşkanlığı
**Savunma Sanayii Başkanlığı (SSB)** tarafından yarışmadaki **tüm takımların
kullanımına açılan** yapay zekâ çıkarım servisinin duyurusu ve servisin canlı
ölçümü.

## Goal (Amaç)

Takımlara ücretsiz, kotasız ve senaryo kısıtsız bir çıkarım altyapısı sağlamak;
böylece donanım erişimi olmayan takımların da büyük dil modelleri, görsel-dil
modelleri ve gömme (embedding) modelleriyle çalışabilmesini mümkün kılmak.

## What-was-done (Duyuru ne anlatıyor)

Yarışmaya **8 × NVIDIA H200 GPU** tahsis edilmiş; üzerinde **10 model** vLLM ile
**BF16** olarak (kuantizasyon yok) sunuluyor. Metin, video/VLM ve gömme
modelleri mevcut. Her takıma **izole edilmiş Qdrant vektör veritabanı**
veriliyor. **Kota, senaryo kısıtı ve takım başına model listesi bulunmuyor** —
on modelin tamamı bütün takımlara açık.

Duyuru iki performans tavsiyesi veriyor: video isteklerinde kısa klip tercih
edilmesi ve aynı bağlam üzerinden tekrarlı soru sorulması (**ön ek önbelleği**,
prefix caching).

Anatolia AI için tahsis: takım kimliği **team16**, LLM ucu
`https://evren-llmapi.ssyz.org.tr/v1` (**OpenAI-uyumlu**), Qdrant ucu
`https://evren-vektor.ssyz.org.tr/team16/`.

### Canlı ölçüm (2026-08-24) — servis gerçekten ne veriyor

Model listesi doğrudan `/v1/models` ucundan çekildi:

| Takma ad | Bağlam | Ölçülen |
|---|---|---|
| `llm-large` | 262.144 | Qwen3.5-122B-A10B (modelin kendi beyanı) |
| `llm-fast` | 262.144 | `llm-large`'dan yavaş (4,1 vs 3,8 s) |
| `router` | 40.960 | yönlendirici değil, kendisi LLM |
| `vlm` | 262.144 | **görüntü KAPALI (400)** |
| `guard` | 32.768 | çalışıyor (Jailbreak yakaladı) |
| `embed` | 32.768 | 2560 boyut; R@1 %97 (bge-m3 kadar) |
| `bge-m3-embed` | 8.192 | **1024 boyut; R@1 %97, MRR 0,983** — en değerli uç |
| `bge-m3-sparse` / `bge-m3-colbert` | 8.192 | **HTTP 501 — uç yok** |
| `rerank` | 32.768 | gerçek korpusta MRR 0,68 → **0,29 (bozuyor)** |

Doğrulanan yetenekler: OpenAI-uyumlu `/v1/chat/completions`, `logprobs`
(alan bazlı güven skoru için kritik — Ollama bunu hiç vermez), Türkçe finansal
bilgi çıkarımı, `response_format` ile JSON kısıtı.

Doğrulanan **kusurlar**: 12 alanlı karmaşık çıkarım şemamız `json_schema`
modunda **HTTP 500** veriyor; `guided_json` parametresi **HTTP 200 dönüp kısıtı
sessizce yok sayıyor**; şema desteği alan bazında değişiyor (`hedef_kitle`
alanının tek alanlık şeması bile 500 veriyor). Ayrıntı: [[pazarlik-http-200-kisit-uygulanmadi]].

### Ölçülen kalite — tam şemayla EVREN kural hattının ALTINDA

`gold.v2` (48 kayıt, 40 zor), eşleştirici `strict`, `LLM_STRICT=1`:

| Kol | F1 (tüm) | F1 (zor) |
|---|---|---|
| kural | **0,570** | **0,587** |
| llm (`llm-large`, kısıtsız mod) | 0,329 | 0,332 |
| hibrit | 0,556 | 0,571 |

McNemar: `kural vs llm` p=0,00051 → anlamlı, kazanan **kural**; mikro-F1 farkı
0,242 [0,157–0,323], güven aralığı dışında. `kural vs hibrit` farkı ise GA
içinde, yani hibrit kol kural-only'nin üstüne ölçülebilir bir şey koymuyor.

Bu sonuç "122B model zayıf" demek **değil**: bu koşumlarda gerçek şema kısıtı
hiç devreye girmedi (yukarıdaki 500 hatası nedeniyle).

## Files-changed / touched

- `app/src/extraction/llm/clients.py` — bearer başlığı, kısıt probu, `json_object` modu
- `app/src/extraction/llm/cascade.py` — **yeni**, kademe zinciri
- `app/src/extraction/llm/extractor.py` — `LLM_BACKEND` kademe listesi
- `app/tests/test_llm_bearer.py`, `test_llm_kisit_probu.py`, `test_llm_cascade.py`,
  `test_llm_zincir_fabrikasi.py` — **yeni**, 42 test
- `app/docs/evren-servisi.md` — **yeni**, ölçüm ve kapsam sınırları belgesi
- `app/docs/SARTNAME-UYUM.md` — §5.10 satırı EVREN alanını açıkça anıyor
- `app/.env.example` — EVREN bloğu (anahtar **boş**)

## Decisions

- [[evren-opsiyonel-kademe-olarak-entegrasyon]] — EVREN teslim yoluna yalnız
  kademe (fallback) olarak konur; sistem ona bağlı olmaz.

## Issues

- [[pazarlik-http-200-kisit-uygulanmadi]] — yetenek pazarlığı "parametreyi
  tanıdım" ile "kısıtı uyguladım"ı ayırt etmiyordu.

## Open-threads

- `llm-large` lisansı modelin kendi beyanına dayanıyor; [[apache-2-acik-kaynak-lisansi]]
  disipliniyle (HF model kartı + `base_model` zinciri köke kadar) bağımsız
  doğrulanmadı.
- Alan başına çağrı (`LLM_ALAN_BASINA=1`) ile `json_schema` kısıtı tek alanlık
  şemada çalışıyor **ama kalite kazandırmıyor**: aynı gold'da (`gold.v1`)
  llm kolu 0,331 → 0,323, çağrı sayısı 40 → 413. Kısıtın devreye girmesi
  tek başına yetmiyor; darboğaz başka yerde.
- ~~`vlm`, `guard`, `router`, sparse/colbert ve Qdrant sınanmadı~~ → **hepsi
  sınandı (24 Ağu).** `vlm` görüntü kabul etmiyor (400), sparse/colbert uçları
  501, `rerank` sıralamayı bozuyor, `guard` çalışıyor ama bizde karşılığı var,
  Qdrant tam çalışıyor ama uzak depo §5.9'u zedeliyor. Tek net kazanç:
  `bge-m3-embed` (R@1 %97) — ve o kazanç `embeddings` tablosunun BOŞ olması
  yüzünden gerçek: `sentence-transformers` kurulu değil, chatbot'un vektör
  kolu hiç devrede değil.
- Şema desteğinin alan bazında değişmesi, pazarlığın istemci başına
  cache'lemesiyle çelişiyor — şema-başına pazarlık mı, şema sadeleştirme mi?

## Sources

- TEKNOFEST 2026 TYDA yarışma duyurusu, 2026-08-24 (e-posta) — takım listesi,
  erişim bilgileri, performans tavsiyeleri
- `https://evren-teknofest.ssyz.org.tr` — model kartları, donanım sayfası,
  canlı servis durumu
- `app/docs/evren-servisi.md` — bu sayfadaki tüm ölçümlerin ayrıntılı dökümü
- `app/eval/reports/evren-ceiling/20260824-080634/` — ablasyon artefaktı

## Related

- [[ssb-evren-cikarim-servisi]] — servisin varlık (entity) sayfası
- [[2026-06-16-teknofest-tyda-sartname-2-senaryo]] — §5.9 on-prem, §5.10 ücretli API yasağı
- [[on-premise-calistirilabilir-mimari]] — kademe mimarisinin korumak zorunda
  olduğu karar
