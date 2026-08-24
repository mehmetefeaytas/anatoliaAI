---
title: "EVREN teslim yoluna yalnız opsiyonel kademe olarak konur"
tags: [karar, mimari, llm, on-premise, evren, dayaniklilik]
source: "[[2026-08-24-ssb-evren-cikarim-servisi]]"
date: 2026-08-24
status: stable
---

# EVREN teslim yoluna yalnız opsiyonel kademe olarak konur

## Karar

[[ssb-evren-cikarim-servisi]] teslim yoluna **bağımlılık olarak değil, kademe
(fallback) zincirinin başı olarak** konur. `LLM_BACKEND` virgüllü bir kademe
listesi kabul eder (`evren,ollama`); EVREN düşerse yerel kademe devralır, tüm
kademeler düşerse sistem **kural-only** koşar.

## Gerekçe

Karar iki kısıt arasında sıkışıyor ve ikisi de ölçülmüş:

**1. EVREN gerçek bir kazanç sunuyor.** Ücretsiz, kotasız, 122B model, 262k
bağlam ve `logprobs`. Gömme ucu (`bge-m3-embed`, 1024 boyut) bizim modelimizle
birebir aynı. Entegrasyon maliyeti tek bir bearer başlığıydı — mimarimiz zaten
OpenAI-uyumlu.

**2. Ona BAĞLANMAK iki şeyi birden bozardı.**
- Şartname §5.9 **on-prem uygulanabilirlik %20** ağırlıklı ve bizim en güçlü
  kalemimiz ([[on-premise-calistirilabilir-mimari]], ağsız kanıt 14/14 + tam
  yığın 39/39). Dış servise bağlı bir sistem bu kalemi kaybeder.
- Servis **tüm takımlarca paylaşılıyor**. Jüri önünde yavaşlarsa arayüz bekler;
  bu risk ölçülmüş bir olaydır (18 dakika asılı kalan çağrı, `_urllib_transport`
  docstring'i) ve [[demo-onceden-doldurulmus-db]] kuralının var olma sebebidir.

Kademe mimarisi ikisini uzlaştırıyor: uzak uç sistemi **iyileştiren** bir
katman olur, **ayakta tutan** bir katman olmaz. Üstelik iddia tersine çevrilir —
"dış servis düştüğünde de çalışır" artık ölçülebilir bir cümledir ve gerçek bir
koşumla kanıtlanmıştır (yerel uç kapalıyken zincir EVREN'e geçti; tersi de
geçerli).

## Kararın parçaları

- **Geçiş tetiği:** yalnız `LLMError` soyu (ulaşılamama, duvar-saati sınırı,
  HTTP reddi). Kod/şema hataları (`ValueError` vb.) yedeğe geçerek gizlenmez.
- **Devre kesici:** düşen kademe 300 sn atlanır. Zorunlu — aksi hâlde 48
  belgelik bir koşum 48 kez zaman aşımını bekler, yani yedek koşumu kurtarmaz,
  sadece yavaşlatır.
- **Anahtar repoya girmez.** `.env.example`'da alan **boş** durur; anahtarsız
  kademe sessizce atlanır. Teslim edilen kopyada beklenen davranış budur.
- **Demo yolunda kullanılmaz.** §11 kuralı geçerli kalır.

## Ölçüm — kararın koşulu

Tam şemayla (`gold.v2`, 48 kayıt) kural hattı EVREN'in LLM kolunu istatistiksel
olarak yeniyor (F1 0,570 vs 0,329; McNemar p=0,00051) ve hibrit kol kural-only'nin
üstüne ölçülebilir bir şey koymuyor.

Alan başına çağrının (`LLM_ALAN_BASINA=1`) kısıtı gerçekten devreye soktuğu
görüldü — tek alanlık şemada pazarlık `json_schema`'yı seçiyor. Ama **aynı gold
üzerinde** karşılaştırıldığında kazanç YOK (`gold.v1`, 20 kayıt):

| Mod | kural | llm | hibrit | gerçek çağrı |
|---|---|---|---|---|
| tam şema | 0,469 | 0,331 | 0,510 | 40 |
| alan başına | 0,469 | 0,323 | 0,507 | **413** |

10 kat çağrı maliyetine karşılık hafif bir DÜŞÜŞ. (İlk okumada alan başına kol
umut verici görünmüştü; o izlenim iki farklı gold setinin karşılaştırılmasından
geliyordu ve aynı gold'da koşulunca çürüdü. Ölçüm buradadır, izlenim değil.)

**Sonuç:** bugünkü hâliyle `evren` kademesinin AÇIK olması için gerekçe yok.
Kademe altyapısı hazır ve sınanmış durumda bekler; kalite kazancı ölçülene kadar
teslimde `LLM_BACKEND` boş (kural-only) ya da yerel kalır. Hibritin kural'ı
geçtiği tek koşum `gold.v1`'dedir ve fark güven aralığı içindedir — yani
kanıtlanmamıştır; `gold.v2`'de ise hibrit kural'ın altındadır. İki gold arasında
yön değiştiren bir fark, karar dayanağı olamaz.

## ÇELİŞKİ yok — ama sınır var

Bu karar §5.10'u (ücretli API yasağı) ihlal etmez: EVREN ücretsizdir ve
yarışmanın kendi altyapısıdır. Yine de `.env.example`'a bir dış servis alanı
girdiği için `app/docs/SARTNAME-UYUM.md` ilgili satırı bunu **açıkça** anar;
gizlenmez.

## Sources

- [[2026-08-24-ssb-evren-cikarim-servisi]] — ölçümlerin tamamı
- `app/docs/evren-servisi.md` §4–§6 — kademe mimarisi, ölçüm, kapsam sınırları
- `app/src/extraction/llm/cascade.py` — kararın kod karşılığı

## Related

- [[ssb-evren-cikarim-servisi]] — kararın konusu olan servis
- [[on-premise-calistirilabilir-mimari]] — korunan karar
- [[demo-onceden-doldurulmus-db]] — demo yolunda neden kullanılmadığı
- [[pazarlik-http-200-kisit-uygulanmadi]] — entegrasyon sırasında bulunan hata
