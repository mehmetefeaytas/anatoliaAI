---
title: "Katılım finansı terim sözlüğü"
tags: [concept, terminoloji, katilim-bankaciligi, sozluk]
source: "[[2026-08-06-mentor-terim-sozlugu]]"
date: 2026-08-06
status: stable
---

# Katılım finansı terim sözlüğü

101 girdilik, mentör tarafından sağlanmış ve avukat gözünden geçmiş yapılandırılmış
sözlük. Dosya: `app/data/terminology/katilim-terim-sozlugu.json`.

## Şema ve hangi alanın ne işe yaradığı

| alan | kullanan |
|---|---|
| `kanonik`, `varyantlar` | terim yönlendirici (kart seçimi) — **seçici** |
| `halk_dili` | RAG sorgu genişletme — **kapsayıcı** |
| `degildir` | prompt kartı + çıktı bekçisi (yanlış eşitleme) |
| `ayrim_notu` | prompt kartı — modelin asıl bilmediği bilgi |
| `risk_notu` | çıktı bekçisi (değişken tutar, tartışmalı yapı) |
| `kaynak` | rapor/atıf |

**İki sözcük dağarcığı karıştırılmamalı.** `halk_dili` "durum", "konu",
"ödeme", "kazanç" gibi son derece genel ifadeler taşır. Kart seçiminde
kullanılırsa neredeyse her belge `keyfiyet` ve `tediye` kartını çeker; kapsam
kapısında kullanılırsa yanlış pozitif 3/18'den 11/18'e fırlar (ölçüldü).

## Sözlüğün taşıdığı üç tuzak sınıfı

**1. Anlam çakışması** — aynı kelime iki farklı şey:
`katilim-fonu` (mevzuatta mevduat karşılığı ↔ günlük dilde faizsiz yatırım
fonu), `havale` (para transferi ↔ borcun nakli), `zimmet` (borç sorumluluğu ↔
ceza hukukundaki zimmet suçu). Bağlam ayrılmadan cevap verilmemeli.

**2. Tersine dönen ekler** — `muaccel` / `müeccel` tek harf farkla taban tabana
zıt; `adem-i ifa` olumsuzluk taşır; `gayri kabili rücu` / `kabili rücu`
önekiyle tersine döner. Normalizasyon bu ekleri silmemeli.

**3. Değişken rakamlar** — `tmsf` sigorta limiti ve `nisap` dönemsel olarak
güncellenir; model sabit rakam söylememeli.

## En maliyetli tek hata

Sözlüğün kendi ifadesiyle: *"Modelin sukuku tahvil gibi modellemesi en sık
görülen ve en maliyetli hatadır."* Tahvil bir **borç** senedidir ve faiz
üretir; sukuk bir **varlığa** dayanır. "Faizsiz tahvil" ifadesi yanlıştır.

## Ölçülmüş davranış

Gerçek korpusta (120 belge örneklem) en sık çekilen terimler: `kar-payi`,
`katilma-hesabi`, `ozel-cari-hesap`, `bireysel-finansman-destegi`, `sukuk`,
`havale`. Belgelerin yarısına yakını hiç terim çekmiyor — bunlar perakende
taksit kampanyaları ve bu doğru davranıştır (kart yok, bağlam israfı yok).

## Sources
- [[2026-08-06-mentor-terim-sozlugu]]

## Related
- [[terim-sozlugu-enjeksiyon-replace-degil]] — nasıl kullanıldığı kararı
- [[katilim-bankaciligi]] — alan bilgisi
- [[katilim-bankaciligi-terminoloji-farkliligi]] — çözülen sorun
