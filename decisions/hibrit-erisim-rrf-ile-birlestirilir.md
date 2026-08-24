---
title: "Hibrit erişim RRF ile birleştirilir (skor toplamıyla değil)"
tags: [karar, mimari, rag, chatbot, erisim, hibrit, rrf]
source: "[[2026-08-24-ssb-evren-cikarim-servisi]]"
date: 2026-08-24
status: stable
---

# Hibrit erişim RRF ile birleştirilir

## Karar

Chatbot erişiminde anahtar-kelime ve vektör kolları **Reciprocal Rank Fusion
(RRF)** ile birleştirilir; skorlar toplanmaz. `RAG_RETRIEVER=hibrit` modu
eklendi. Üretim varsayılanı bu kararla **değişmedi** — hâlâ `keyword`.

## Gerekçe: ölçülmüş zıtlık

255 soruluk, iki bölümlü ve otomatik altın etiketli bir test kuruldu
(24 Ağu 2026):

| kol | A. özet-tabanlı sorgu (n=200) | B. banka hedefleme (n=55) |
|---|---|---|
| keyword | **MRR 0,774** · R@1 %69,0 | 23/55 (**%42**) |
| vector | MRR 0,559 · R@1 %49,5 | **43/55 (%78)** |
| hibrit (RRF) | MRR 0,761 · **R@10 %92,5** | 39/55 (%71) |

**Hiçbir tek kol iki tipte de iyi değil.** Ve A bölümündeki keyword üstünlüğü
YAPAY: sorgular belgenin kendi özetinden türetildiği için kelime örtüşmesi
doğal olmayan biçimde yüksek. Gerçek kullanıcı belgenin cümlelerini
kopyalamaz — "Kuveyt Türk kâr payı oranı" diye sorar, yani **B bölümü gerçek
kullanıma daha yakın** ve orada vektör kolu keyword'ü %42 → %78 ile geçiyor.

## Neden RRF, neden skor toplamı DEĞİL

İki kolun skorları aynı ölçekte değil: `KeywordRetriever` örtüşme sayısı
üretir (tamsayı, üst sınırsız), `VectorRetriever` kosinüs üretir (0–1).
Doğrudan toplamak, ölçeği büyük olan kolun ötekini **ezmesi** demektir —
"birleşim" adı altında tek kol çalışırdı. RRF skoru değil SIRAYI kullanır
(`1/(60 + rank)`) ve ölçekten bağımsızdır.

Aday derinliği `k`'nın dört katıdır: yalnız ilk `k` alınırsa iki liste büyük
ölçüde örtüşür ve birleştirmenin kazandıracağı bir şey kalmaz.

## Bir kol düşerse

Vektör kolu koşum ortasında düşebilir (gömme ucu, ağ). Erişim tümden durmaz:
hata loglanır ve öteki kolun sıralaması kullanılır. Yarım erişim, hiç erişim
olmamasından iyidir — ve sessiz de değildir. Bu, [[gomme-yolu-evren-ile-acildi]]
kararındaki kademe felsefesinin erişim tarafındaki karşılığıdır.

`build_retriever` `hibrit` modunda vektör kolu kurulamazsa **yükseltmez**
(`vector` modunun aksine): hibritin yarısı çalışıyordur ve onu teslim etmek
doğru olandır — WARNING ile.

## ÖLÇÜM SONRASI DÜZELTME — hibrit önerilmez

Yukarıdaki tablo test betiğinden geldi (her koldan 10 aday). Mimarideki
`HybridRetriever` aynı soru kümesinde **27/55 (%49)** verdi; betik 39/55 (%71)
vermişti. Fark aday derinliğinde: sınıf `k`'nın dört katını alıyor ve `k=1`
çağrısında yalnız 4 aday kalıyor. O derinlikte iki kolun birinci adayı RRF'de
**eşit skor** alıyor ve eşitlik anahtar-kelime kolu lehine bozuluyor.

| kol | banka hedefleme (n=55) |
|---|---|
| keyword | 23/55 (%42) |
| **vector** | **43/55 (%78)** |
| hibrit (mimari) | 27/55 (%49) |
| hibrit (betik, derinlik 10) | 39/55 (%71) |

Hibrit hiçbir derinlikte `vector`ü geçmedi. **Bu soru tipinde en iyi kol tek
başına vektördür.** `hibrit` modu kodda opsiyonel duruyor (testli, zararsız)
ama önerilmez; eşitlik bozma ve kol ağırlığı ölçülmeden üzerine bir şey inşa
edilmemeli. Bu sayfa o yüzden `status: stable` ama kararı "hibrit kullanılsın"
DEĞİL, "hibrit ölçüldü ve tek başına vektör kadar iyi değil"dir.

## Varsayılan neden DEĞİŞMEDİ

Ham vektör aramasında uzun sözleşmeler baskın çıkabiliyor: *"en yüksek kâr
payı oranı hangi bankada"* sorgusu **Genel Kredi Sözleşmesi** pasajları
döndürdü (982 sözleşme, 51.556 chunk'ın büyük kısmı). Ölçüm kümesi bunu
cezalandırmıyor. `belge_turu` süzgeci ya da tür-farkında skorlama ölçülmeden
varsayılanı değiştirmek, ölçülmemiş bir davranışı teslim yoluna koymak olurdu
([[on-premise-calistirilabilir-mimari]] ile aynı disiplin).

Açmak için: `RAG=hibrit make baslat` ya da `RAG_RETRIEVER=hibrit`.

## Sources

- [[2026-08-24-ssb-evren-cikarim-servisi]] — büyük erişim testinin dökümü
- `app/docs/evren-servisi.md` §8 — test tabloları ve metodolojik uyarı
- `app/src/chatbot/rag.py` — `HybridRetriever`
- `app/tests/test_rag_hibrit_retriever.py` — 10 test

## Related

- [[gomme-yolu-evren-ile-acildi]] — vektör kolunu mümkün kılan karar
- [[ssb-evren-cikarim-servisi]] — gömmeleri üreten servis
- [[on-premise-calistirilabilir-mimari]] — ölçülmemiş davranışı teslime koymama disiplini
