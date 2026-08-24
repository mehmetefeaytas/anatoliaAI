---
title: Next dev proxy ECONNRESET — «Sunucu 500» yanlış alarmı
tags: [sorun, yanlis-alarm, next-dev, proxy, econnreset]
source: "log.md — [2026-08-21] karar | jüri sunumu 15 slayttan 5 slayta indirildi"
date: 2026-08-21
status: stable
---

# Next dev proxy ECONNRESET — «Sunucu 500» yanlış alarmı

**Belirti:** Sunum için ekran çekimi sırasında çelişki sekmesi «Sunucu 500
döndü» bastı.

**Kök neden:** Ürün hatası değil. API, Next dev sunucusu ayaktayken yeniden
başlatılınca Next dev proxy'si ölü keep-alive soketini yeniden kullanıyor ve
bağlantı `ECONNRESET` ile düşüyor; proxy bunu 500 olarak yüzeye vuruyor.

**Sonuç:** Web sunucusu tazelenince geçti; **yanlış alarm** olarak kapatıldı.
Not `app/docs/sunum/ekranlar/README.md`'de de kayıtlıdır.

## DÜZELTME (2026-08-24) — bu teşhis EKSİKTİ

Aynı belirti 24 Ağustos'ta tekrar bildirildi ve bu kez ölçüldü: soğuk
`/contradictions` **47,2 saniye** sürüyor, çünkü her istek 2.708 belgede kural
çıkarımını sıfırdan koşuyor. Panel iki ucu birden çağırdığı için tarama İKİ
KEZ başlıyordu ve proxy yavaş yanıtı 500'e çeviriyordu.

Yani bu sayfadaki ECONNRESET teşhisi 21 Ağustos'taki gözlem için doğru olabilir
ama **belirtinin tek sebebi değil**. Yanlış alarm diye kapatmak, gerçek bir
performans arızasını üç gün görünmez bıraktı.

Ders: aynı belirti iki kez göründüğünde ilk teşhis yeniden açılmalı. Ölçülmüş
ikinci sebep ve çözümü: [[celiski-tespiti-yavasti-ve-500-donuyordu]].

## Sources
- log.md — [2026-08-21] karar | jüri sunumu 15 slayttan 5 slayta indirildi

## Related
- [[celiski-tespiti-yavasti-ve-500-donuyordu]] — AYNI belirtinin ikinci, gerçek
  sebebi (47 sn'lik tarama); bu sayfanın teşhisini tamamlıyor
- [[juri-sunumu-bes-slayt]] — alarmın görüldüğü ekran çekimi bu sunum çalışması
  içindi
