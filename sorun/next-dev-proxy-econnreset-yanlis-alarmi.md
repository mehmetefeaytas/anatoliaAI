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

## Sources
- log.md — [2026-08-21] karar | jüri sunumu 15 slayttan 5 slayta indirildi

## Related
- [[juri-sunumu-bes-slayt]] — alarmın görüldüğü ekran çekimi bu sunum çalışması
  içindi
