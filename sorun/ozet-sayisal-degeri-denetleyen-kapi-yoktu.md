---
title: "Özetteki sayısal değeri denetleyen kapı yoktu"
tags: [sorun, ozet, halusinasyon, kapi, finansal-dogruluk]
source: "[[2026-08-24-ssb-evren-cikarim-servisi]]"
date: 2026-08-24
status: stable
---

# Özetteki sayısal değeri denetleyen kapı yoktu

## Belirti

Panelde "AI Özeti" etiketiyle gösterilen özetlerde, kaynak belgede **hiç
geçmeyen** kâr payı oranları ve tutarlar duruyordu. Örnekler (elle
doğrulandı):

| kampanya | özet ne diyor | kaynakta ne var |
|---|---|---|
| 1123 | `%50` indirim | yalnız `300 TL` |
| 311 | `%25` | yalnız `3 gün` |
| 2528 | `5000 TL` | `5001 TL` — yakın ama **farklı** |

## Kök neden

`SISTEM_PROMPT` "yalnız metinde geçen bilgileri kullan" diyor. Bu bir
**yönergedir, kapı değil** — model ona uymayabilir. Aynı asimetri daha önce
terminoloji kuralında da yaşanmıştı ([[pazarlik-http-200-kisit-uygulanmadi]]
ile aynı aile: yönergeye güvenip ölçmemek).

Özet hattında iki kapı vardı — alfabe (`turkce_alfabede_mi`) ve terminoloji
(`_terminoloji_ihlali`) — ama **sayısal doğruluğun kapısı yoktu**. Finansal
bir panelde uydurulmuş bir oran, jürinin ilk yakalayacağı hatadır ve
CLAUDE.md §19'un halüsinasyon yasağının doğrudan ihlalidir.

## Çözüm (fix)

`_sayi_ihlali(ozet, kaynak)` kapısı eklendi (`src/summarize/ozet.py`).
Özetteki her **finansal** sayı (oran, tutar, vade) kaynak metinde bulunmak
zorunda; bulunmazsa özet reddedilir ve sıcaklık merdiveninde yeniden denenir.
Sebep kodu `sayi_dogrulanmadi`, **kalıcı değil** — farklı bir sıcaklıkta model
sayı uydurmadan özetleyebilir.

Üç tasarım kararı ölçümle şekillendi:

1. **Ölçüt biçim değil ÇIPLAK BASAMAK.** İlk sürüm `%3.54` ile `%3,54`yi
   farklı sayıyordu; çıplak rakamlar kaynakta VARDI, fark yalnız ondalık
   ayırıcıdaydı. Kapının işi sayının doğruluğu, biçimi değil.
2. **Asimetri kasıtlı.** Özet tarafında yalnız finansal desenler denetlenir;
   kaynak tarafında metindeki TÜM sayılar toplanır. Kaynakta bir oran tabloda
   çıplak dururken (`1,89`) özette yüzdeli geçebilir (`%1,89`) ve bu uydurma
   değildir.
3. **Tarih tuzağı.** İlk desen `01.04.2025` içindeki `4.202` parçasını
   "binlik gruplu sayı" sanıyordu ve kapı 2.676 özetten **114'ünü (%4,3)**
   düşürüyordu — hepsi tarihti, yani hiç uydurma yakalamadan geçerli özetleri
   eliyordu. `(?!\d)` sıkılaştırmasıyla oran **9'a (%0,34)** indi.

## Ölçülen sonuç

| aşama | kapıya takılan özet |
|---|---|
| ilk regex (tarih tuzağı) | 114 — hepsi yanlış pozitif |
| `(?!\d)` sonrası | **9** — hepsi gerçek, elle doğrulandı |
| düşürülüp yeniden üretildikten sonra | **0** |

Dokuz özet düşürüldü (`ozet_sebep` yazıldı — sessiz kayıp yok) ve
[[ssb-evren-cikarim-servisi]] ile yeniden üretildi (15,4 sn). Korpus artık
kapıdan 0 ihlalle geçiyor.

## Yan bulgu — geri çekilen bir iddia

Kapı, EVREN'in özet yenilemede "%16 doğrulanamayan sayı" ürettiği ölçümünden
doğdu. O ölçüm **yanlıştı**: prompt bizim basit test prompt'umuzdu, projenin
`SISTEM_PROMPT`'u değil. Gerçek hatla 14/14 özet ihlalsiz üretildi (sıcaklık
merdiveni kapalıyken de aynı). İddia geri çekildi; ayrıntı
`app/docs/evren-servisi.md` §10'da.

Kapının değeri bu yüzden gelecekteki uzak çağrılarda değil, **geçmişteki yerel
çıktılarda** ortaya çıktı — ve her iki model için ileriye dönük güvence olarak
duruyor.

## İlgili dosyalar

- `app/src/summarize/ozet.py` — `_sayi_ihlali`, `SEBEP_SAYI`, `_basamaklar`
- `app/tests/test_ozet_sayi_kapisi.py` — 11 test + 7 alt test
- `app/tests/test_ozet_alfabe.py` · `app/tests/test_ozet_dil_temizligi.py` —
  fikstürleri kapıyı hesaplayacak şekilde güncellendi (davranış değişmedi)

## Sources

- [[2026-08-24-ssb-evren-cikarim-servisi]] — ölçüm dökümü
- `app/docs/evren-servisi.md` §10

## Related

- [[ssb-evren-cikarim-servisi]] — yeniden üretimi yapan servis
- [[pazarlik-http-200-kisit-uygulanmadi]] — "yönergeye güvenip ölçmemek" ailesi
- [[bilgi-cikarimi]] — finansal doğruluğun hizmet ettiği kavram
