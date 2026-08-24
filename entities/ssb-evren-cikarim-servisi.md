---
title: "SSB EVREN Çıkarım Servisi"
tags: [varlik, altyapi, llm, ssb, teknofest, servis]
source: "[[2026-08-24-ssb-evren-cikarim-servisi]]"
date: 2026-08-24
status: stable
---

# SSB EVREN Çıkarım Servisi

T.C. Cumhurbaşkanlığı **Savunma Sanayii Başkanlığı** tarafından TEKNOFEST 2026
Yapay Zekâ Dil Ajanları Yarışması'ndaki **tüm takımlara ücretsiz** açılan yapay
zekâ çıkarım servisi. 8 × NVIDIA H200 üzerinde vLLM · BF16, 10 model, kotasız.
Takım başına izole Qdrant örneği de veriliyor.

Anatolia AI erişimi: takım kimliği **team16**, uç
`https://evren-llmapi.ssyz.org.tr/v1` (**OpenAI-uyumlu** — bu yüzden mevcut
`VLLMClient`'ımız onu doğrudan konuşuyor).

## Projedeki rolü

**Geliştirme/ölçüm aracı** ve **opsiyonel kademe**. Teslim yolunda bir
bağımlılık DEĞİL: [[evren-opsiyonel-kademe-olarak-entegrasyon]] kararı gereği
zincirin başına konur, düştüğünde yerel yol devralır, hepsi düşerse sistem
kural-only koşar. [[on-premise-calistirilabilir-mimari]] kararı ve şartname
§5.9 (%20) bu yüzden korunur.

## Ölçülen yetenekler (2026-08-24)

On modelin **tamamı** sınandı (2026-08-24):

- ✓✓ `bge-m3-embed` — 1024 boyut, gömme katmanımızla birebir. Gerçek korpusta
  **Recall@1 %97, MRR 0,983**. **KULLANILDI (24 Ağu):** 2708/2708 kampanya,
  51.556 chunk, 647 sn, 0 hata. `VectorRetriever` artık kuruluyor; RAG
  ölçümünde banka hedefleme 8/10 → **10/10**. Karar:
  [[gomme-yolu-evren-ile-acildi]].
- ✗ **262k bağlam** — ilk ölçüm "net kazanç" diyordu; **iddia geri çekildi.**
  İki hata vardı: (1) alan ANAHTARI sayıldı, dolu değer değil — şema boş
  alanı da döndürüyor; (2) karşılaştırma kırpık-vs-tam, yani LLM kolunun
  kendi içinde kıyasıydı. Kural hattı regex tabanlı ve metnin tamamını
  tarıyor. Doğru ölçümde (6 en uzun belge, dolu değer) kural **24** alan,
  EVREN **10**, EVREN'in ekstrası **0**. Uzun bağlam bir yetenek olarak
  duruyor ama çıkarım işimizde karşılığı yok.
- ✓ `llm-large` = Qwen3.5-122B-A10B, `logprobs` **döndürüyor** (Ollama hiç
  vermez). Çıkarım kalitesi kısıtsız modlarda kural hattımızın altındaydı;
  **tool calling** ile gerçek şema kısıtı elde edildi (aynı şema
  `response_format` ile HTTP 500 verirken tool calling'de 12 alanın tamamı
  doğru yapıda döndü) ve ölçüm yenilendi.
- ⚠ **TUZAK:** bilinmeyen model adı **sessizce** kabul ediliyor —
  `llm-buyuk-yanlis-ad` ile istek HTTP 200 döndü. `EVREN_MODEL` yanlış
  yazılırsa koşum farklı modelle yapılır ve artefakt yanlış adı raporlar.
- ✓ izole Qdrant 1.19.0 — tam CRUD çalışıyor (40 nokta upsert 0,89 s), ancak
  uzak vektör deposu §5.9'u zedelediği için kullanılmıyor.
- ✗ `guard` — çapraz doğrulandı: prompt injection'da bizim enjeksiyon kapısı
  4/26, guard 5/26; meşru soruda yanlış alarm ikisinde de 0/23. **Anlamlı
  fark yok**, dış bağımlılık ekler.
- ~ `embed` (2560 boyut) — `bge-m3-embed` kadar iyi, daha pahalı.
- ~ `router` — yönlendirici değil, kendisi bir LLM.
- ✗ `rerank` — gerçek korpusta sıralamayı **bozuyor** (MRR 0,68 → 0,29, her
  pasaj uzunluğunda kayıp)
- ✓ **görüntü (vision)** — `vlm`'de DEĞİL, `llm-fast`/`llm-large`'da (en çok
  2 görüntü). İlk denememiz `vlm`'e yapılmıştı ve `At most 0 image(s)`
  hatası aldık; `vlm` video İÇİN ve görüntüyü kasıtlı reddediyor.
  Doğru uçla ölçüldü: panel kıyas tablosunu ekran görüntüsünden **doğru
  okudu** (Emlak %0 · Türkiye Finans %1,9 · Kuveyt Türk %3,49; konut
  %1,69/%1,89/%3,85–3,95/%2,95), 5,7 sn.
- ✗ `llm-fast` — `llm-large`'dan yavaş (4,1 vs 3,8 s/belge)
- ~ **özet yenileme** — iki kez ölçüldü. İlk ölçüm EVREN'i "%16 doğrulanamayan
  sayı" ile suçluyordu; o ölçüm **yanlıştı** (prompt bizim basit test
  prompt'umuzdu). Gerçek özet hattıyla 14/14 özet **ihlalsiz** üretildi.
  İddia geri çekildi; karar yeniden açık. Karşı gerekçe olarak yalnız
  Türkçe ondalık ayırıcıyı nokta yazması ve özetlerin 2,4 kat uzunluğu
  duruyor. Eksik özetler için kullanıldı (39 belge) ve sayı kapısının
  yakaladığı 9 bozuk özeti yeniden üretti
  ([[ozet-sayisal-degeri-denetleyen-kapi-yoktu]]).
- ~ `bge-m3-sparse`, `bge-m3-colbert` — `/v1/embeddings`te HTTP 501, ama
  **`/pooling/<alias>` ucunda çalışıyor** (ilk denememiz yanlış uçtaydı).
  Sparse çıktı biçimi `FlagEmbedding`den farklı — hangi terime hangi
  ağırlığın verildiğini bilmek tokenizer eşlemesi gerektiriyor, bu yüzden
  doğrudan kullanımı zor.

## Ölçülen kısıtlar

12 alanlı çıkarım şemamız `json_schema` modunda **HTTP 500** veriyor;
`guided_json` **200 dönüp kısıtı sessizce yok sayıyor**
([[pazarlik-http-200-kisit-uygulanmadi]]); şema desteği alan bazında değişiyor.
Servis paylaşımlı olduğu için demo yolunda kullanılması **önerilmez**
([[demo-onceden-doldurulmus-db]] kuralı geçerli).

## Sources

- [[2026-08-24-ssb-evren-cikarim-servisi]] — duyuru ve canlı ölçüm dökümü
- `app/docs/evren-servisi.md` — ayrıntılı ölçüm, kurulum, kapsam sınırları

## Related

- [[evren-opsiyonel-kademe-olarak-entegrasyon]] — LLM tarafı entegrasyon kararı
- [[gomme-yolu-evren-ile-acildi]] — gömme tarafı kararı
- [[pazarlik-http-200-kisit-uygulanmadi]] — ölçümün açığa çıkardığı hata
- [[on-premise-calistirilabilir-mimari]] — korunması gereken karar
- `OllamaClient` · `VLLMClient` (`app/src/extraction/llm/clients.py`) — zincirdeki yerel kademeler
