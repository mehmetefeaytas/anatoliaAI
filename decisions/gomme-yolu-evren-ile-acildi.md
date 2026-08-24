---
title: "Gömme (embedding) yolu EVREN ile açıldı; yerel bge-m3 yedek"
tags: [karar, mimari, gomme, rag, chatbot, evren, vektor]
source: "[[2026-08-24-ssb-evren-cikarim-servisi]]"
date: 2026-08-24
status: stable
---

# Gömme yolu EVREN ile açıldı; yerel bge-m3 yedek

## Karar

Gömme vektörleri birincil olarak [[ssb-evren-cikarim-servisi]]'nin
`bge-m3-embed` ucundan üretilir; yerel `BAAI/bge-m3` **yedek kademe** olarak
kurulu kalır (`EMBEDDING_BACKEND=evren,yerel`). Üretilen vektörler
`embeddings` tablosuna yazılır.

## Neden gerekliydi

Ölçüldü (24 Ağu 2026): `embeddings` tablosu **boştu** çünkü
`sentence-transformers` kurulu değildi. Sonuç, `chatbot/rag.py` içindeki
`VectorRetriever`'ın hiç devreye girmemesiydi — chatbot yalnız anahtar-kelime
erişimiyle çalışıyor, **anlamsal kol tümüyle eksik**ti. Bu bir yapılandırma
tercihi değil, sessiz bir boşluktu.

## Neden EVREN birincil

- Uç, bizim modelimizin **aynısını** sunuyor: `bge-m3-embed` = `BAAI/bge-m3`,
  1024 boyut, `EMBEDDING_DIM` ile birebir.
- Ölçülen kalite (gerçek korpus, 30 kampanya; sorgu = özet, hedef = metin):
  **Recall@1 %97, MRR 0,983**. 2560 boyutlu `embed` ucu aynı sonucu daha
  pahalıya veriyor.
- Yerel ağırlık ve `torch` yükü olmadan çalışır; 256 girdi tek istekte 1,34 s.
- Tam koşum: **2708/2708 kampanya, 51.556 chunk, 647 sn, 0 hata.**

## Neden yerel YEDEK olarak duruyor

`sentence-transformers==6.0.0` kuruldu ve sürüm pinlendi
(`requirements.txt`'teki notun kendi talimatı: *"Kurulduğunda SBOM'a girecek ve
buraya da pinlenecek"*). SBOM tazelendi, lisans kapısı geçti.

`requirements-api.txt` onu hâlâ **bilerek dışlıyor**: torch ince API imajını
GB'lara çıkarır ve [[on-premise-calistirilabilir-mimari]] kararının paket
boyutu ölçümünü bozar.

## Kademe neden GÜVENLİ

Vektör kademesi, LLM kademesinden farklı bir tehlike taşır: iki kademe farklı
modeller olsaydı vektörleri farklı uzaylarda olurdu, tablo karışık uzaylardan
dolar ve arama **sessizce** bozulurdu — hata vermez, yalnız yanlış belge
döndürür. Burada iki kademe **aynı modeldir**; yine de varsayıma bırakılmadı:
`KademeliEmbedder` boyut eşitliğini kurulumda denetler, eşit değilse zincir
kurulmaz.

## §5.9 (on-prem) neden zedelenmiyor

Uzak uç yalnız **tek seferlik bir üretim adımında** kullanılır; çıktı vektörler
`embeddings` tablosuna yazılır. Teslim edilen sistem arama yaparken ağa
çıkmaz. Bu, [[evren-opsiyonel-kademe-olarak-entegrasyon]] kararındaki
"iyileştiren katman, ayakta tutan katman değil" ilkesinin gömme tarafındaki
karşılığıdır.

## Ölçülen kazanç

`eval/rag_eval.py`'ye `--vektor` kolu eklendi (araç yalnız `KeywordRetriever`'ı
ölçebiliyordu). Aynı soru kümesi, k=5:

| kol | terim kapsama (15) | banka hedefleme (10) | toplam isabet |
|---|---|---|---|
| keyword (üretim) | 13 · MRR 0,867 | 8 · MRR 0,800 | 21/25 |
| bm25 | 13 · MRR 0,867 | 8 · MRR 0,800 | 21/25 |
| **vector (EVREN)** | 13 · MRR 0,833 | **10 · MRR 1,000** | **23/25** |

Vektör kolu keyword'ün kaçırdığı iki soruyu ("Dünya Katılım kampanyaları",
"T.O.M. Katılım kampanyaları") buluyor. Çekimserlik iki kolda da 30/30 — yani
vektör kolu "bilmiyorum" demesi gereken yerde konuşmaya başlamıyor.

## Kalan sınır — üretim varsayılanı DEĞİŞMEDİ

`RAG_RETRIEVER` varsayılanı hâlâ `keyword`. Gerekçe ölçülmüş bir risk: ham
vektör aramasında uzun sözleşmeler baskın çıkabiliyor. *"En yüksek kâr payı
oranı hangi bankada"* sorgusu **Genel Kredi Sözleşmesi** pasajları döndürdü —
982 sözleşme 51.556 chunk'ın büyük kısmını oluşturuyor ve jenerik hukuki metin
her sorguya orta benzerlik veriyor. Ölçüm kümesi bunu cezalandırmıyor.

Açmak için `RAG=auto make baslat`. Kalıcı olarak açmadan önce `belge_turu`
süzgeci ya da hibrit skor (anahtar-kelime + vektör) ölçülmelidir.

## Sources

- [[2026-08-24-ssb-evren-cikarim-servisi]] — ölçümlerin tamamı
- `app/docs/evren-servisi.md` §8 — gömme yolu, koşum raporu, RAG ölçümü
- `app/src/rag/embedding.py` — `EvrenEmbedder`, `KademeliEmbedder`
- `app/tests/test_rag_evren_embedder.py` — 22 test

## Related

- [[ssb-evren-cikarim-servisi]] — vektörleri üreten servis
- [[evren-opsiyonel-kademe-olarak-entegrasyon]] — LLM tarafındaki eş karar
- [[on-premise-calistirilabilir-mimari]] — paket boyutu ölçümünü koruyan karar
- [[bilgi-cikarimi]] — anlamsal erişimin hizmet ettiği kavram
