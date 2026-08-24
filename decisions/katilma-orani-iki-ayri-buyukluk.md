---
title: "Katılma hesabı oranı iki ayrı büyüklüktür: getiri ile pay aynı kolonda yarışmaz"
tags: [karar, kiyas, katilma-hesabi, kar-payi, terminoloji]
source: "[[2026-08-24-tkbb-kar-payi-veri-seti]]"
date: 2026-08-24
status: stable
---

# Katılma hesabı oranı iki ayrı büyüklüktür

## Karar

TKBB verisinden gelen her kayıt bir `buyukluk` alanı taşır ve yalnız iki değer
alabilir:

| değer | rapor | ne demek | örnek |
|---|---|---|---|
| `getiri` | Dağıtılan Kâr Payı Oranları % | gerçekleşen yıllık getiri | %42,79 |
| `pay` | Kâr Paylaşım Oranları % | katılımcıya düşen pay | %90 |

Sıralama **her zaman tek bir büyüklük içinde** yapılır. Cevap hangisini
sıraladığını yazar; `pay` sıralandığında bunun bir kazanç değil bölüşüm olduğu
AYRICA belirtilir.

## Gerekçe

Paylaşım oranı sayısal olarak getiriden neredeyse her zaman büyüktür (%90 vs
%42). İkisi tek kolona girerse "en iyi kâr payı oranını hangi banka veriyor"
sorusunun cevabı, en yüksek getiriyi veren bankayı değil **en yüksek bölüşüm
oranını** ilan eden bankayı gösterir. Cevap teknik olarak "en yüksek sayı"dır
ve pratikte yanlıştır.

Bu, [[urun-karsilastirma]] sayfasındaki adil kıyas garantisinin aynı
uygulamasıdır: yalnız aynı birime normalize alanlar kıyaslanır. Buradaki birim
farkı gizlidir — ikisi de "%" ile yazılır — ve bu yüzden şema düzeyinde
işaretlenmek zorundadır.

Terminoloji tarafı da bunu gerektiriyor: "kâr **paylaşım** oranı" (85/15) ile
"kâr **payı** oranı" (%28,03) katılım bankacılığında iki farklı büyüklüktür ve
karıştırılmaları jürinin ilk yakalayacağı hata sınıfındandır
([[kar-payi-orani]]).

## Uygulama

- Hasat betikleri `buyukluk` alanını rapordan türetir
  (`tkbb_karpayi_hasat.RAPORLAR`, `tkbb_guncel_hasat.DASHLETLER`).
- `app/src/chatbot/katilma_orani.py::_buyukluk_sec` soruya bakar: "paylaşım
  oranı", "kâra katılma oranı", "bölüşüm" geçerse `pay`, aksi hâlde `getiri`.
  Varsayılan `getiri`dir çünkü kullanıcı "en iyi kâr payı oranı" derken
  kazancı sorar.
- `pay` cevabına şu not düşer: *"bu oran bir bölüşüm oranıdır — kârın yüzde
  kaçının katılımcıya verildiğini gösterir, kazancın kendisi değildir."*
- Test: `app/tests/test_chat_katilma_orani.py::TestIkiBuyukluk` —
  `test_getiri_ve_pay_ayni_tabloda_YARISMAZ` bu kararı kilitler.

## Reddedilen seçenek

**Tek kolon, "oran" adıyla.** Şema basitleşirdi ama iki büyüklük tek sıralamaya
girerdi. Basitlik burada yanlış cevap üretiyor; reddedildi.

## Sources

- [[2026-08-24-tkbb-kar-payi-veri-seti]] — iki raporun ölçülmüş değerleri
- `app/src/chatbot/katilma_orani.py` — modül başlığı

## Related

- [[tkbb-kar-payi-veri-seti]] — verinin kaynağı
- [[kar-payi-orani]] — kavram
- [[urun-karsilastirma]] — adil kıyas garantisi
- [[katilma-hesabi-orani-korpusta-yoktu]] — kararı doğuran boşluk
