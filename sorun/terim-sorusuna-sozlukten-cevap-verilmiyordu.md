---
title: "Terim sorusuna sözlükten cevap verilmiyordu (veri vardı, kimse bakmıyordu)"
tags: [sorun, chatbot, terminoloji, sozluk, kaynak]
source: "kullanıcı raporu (2026-08-24, canlı chatbot çıktısı)"
date: 2026-08-24
status: stable
---

# Terim sorusuna sözlükten cevap verilmiyordu

## Belirti

İki canlı çıktı:

```
"Finansman ne demek"  → "Bu soru elimdeki verinin kapsamı dışında — bilmiyorum,
                         tahmin etmiyorum."
"Murabaha ne demek"   → "Bu bilgi verimde yok. Uydurmak yerine bilmediğimi
                         belirtiyorum."
```

## Kök neden — veri VARDI

`data/terminology/katilim-terim-sozlugu.json` **101 terim** için tam kayıt
tutuyor: `tanim`, `sade_aciklama`, `resmi_tr`, `varyantlar`, `halk_dili`,
`degildir`, `iliskili`, `risk_notu` ve **`kaynak`**. Murabaha kaydının kaynağı
*AAOIFI Şer'i Standart No. 8; Bankaların Kredi İşlemlerine İlişkin Yönetmelik*;
risk notu *"müşteriye anlatırken 'faiz oranı' değil 'kâr oranı / vade farkı'
denmelidir"*.

`src/domain/terminology.py` de bu sözlüğü yükleyip eşleştiriyor ve **çıkarım**
ile **güvenlik** katmanlarında kullanılıyor (`cards_for`, `scope_terms`,
`output_violations`). Yalnız **chatbot cevap üretimi** ona hiç bakmıyordu.

Bu, `eval/rag_eval.py`'nin *"müşaraka nedir → isabetsiz"* bulgusunu da
açıklıyor: terim sözlükte VARDI (`Muşaraka`, AAOIFI Şer'i Standart No. 12),
chatbot bakmıyordu.

## Çözüm

`src/chatbot/terim_cevabi.py` yazıldı ve `bot.py` yönlendirmesine KATALOG ile
aynı seviyede bağlandı (`handler="terminoloji"`). Cevap sözlükten kurulur:
tanım + sade anlatım + resmî karşılık + "karıştırılmamalı" + risk notu +
ilgili terimler + **kaynak**.

**Niçin uzak model değil, sözlük:** terim tanımını bir dil modeline
ürettirmek kaynaksız bir iddia olurdu (CLAUDE.md §19). Sözlük gerçek kaynak
taşıyor ve `risk_notu` gibi alanlar hiçbir genel modelin üretemeyeceği kurum
bilgisidir.

Testler: `tests/test_chat_terim_cevabi.py` (13 test + 3 alt test).

## İki tuzak — ikisi de ölçülerek bulundu

### 1. Çıktı koruması sözlük tanımını BOZUYORDU

`Riba` kaydının `resmi_tr` alanı **"Faiz"**tir — riba'nın Türkçe karşılığı
gerçekten faizdir ve katılım finansının YASAKLADIĞI şeydir. `sanitize_output`
onu "Kâr payı" yapıyor ve tanım **tersine dönüyordu**: yasak olan şey meşru
olanla değiştirilmiş oluyordu.

Post-filter LLM üretimi için var; terminoloji gövdesi ise kendi sözlüğümüzden
bir **alıntı**. `guard_output(..., alinti=True)` eklendi ve yalnız
`handler == "terminoloji"` için geçiliyor — model çıktısı için asla.

### 2. Terim yolu ALAN sorularını çalınca güvenlik açığı doğuyordu

*"Bu üründe masraf durumu nedir, faiz uygulanır mı?"* sorusu `nedir` kalıbı
yüzünden terim yoluna gidiyordu. O yol alıntı modunda çalıştığı için
post-filter atlanıyor ve **kaynaktaki yasak terim ekrana sızıyordu** —
`tests/test_safety.py::test_forbidden_term_in_source_is_filtered_out` bunu
yakaladı.

`_ALAN_IZLERI` deseni alan adlarıyla genişletildi. Ayrım "oranı"
sözcüğündedir: *"kâr payı ne demek"* bir TERİM sorusudur ve cevaplanır,
*"kâr payı ORANI nedir"* bir ALAN sorusudur ve yapısal sorgu yoluna gider.

## Kalan sınır

*"Finansman ne demek"* hâlâ cevaplanmıyor — sözlük katılım bankacılığına
**özgü** terimleri içeriyor (riba, garar, murabaha, muşaraka…), "finansman"
gibi genel bir bankacılık terimi bağımsız kayıt olarak yok. `tcmb-terimler.json`
(314 terim, tanımlı, kaynak URL'li) henüz arama kapsamında değil; şeması
farklı (`terim`/`tanim`/`kaynak_url`) ve `TermEntry`'ye dönüştürülmesi
gerekiyor. Ayrıca TCMB terimleri konvansiyonel bankacılık terimleri içerdiği
için katılım bağlamında `degildir`/`risk_notu` karşılıkları olmadan
gösterilmeleri değerlendirilmelidir.

## İlgili dosyalar

- `app/src/chatbot/terim_cevabi.py` — yeni
- `app/src/chatbot/bot.py` — `terminoloji` handler'ı, `alinti=True`
- `app/src/chatbot/safety.py` — `guard_output(..., alinti=...)`
- `app/tests/test_chat_terim_cevabi.py` — 13 test

## Sources

- Kullanıcı raporu, 2026-08-24 — iki canlı çıktı
- `data/terminology/katilim-terim-sozlugu.json` — 101 terim
- `app/eval/rag_eval.py` — "müşaraka nedir" isabetsizliği

## Related

- [[kiyas-cevabinda-iki-gosterim-hatasi]] — aynı gün, aynı raporlama hattı
- [[bilgi-cikarimi]] — terminolojinin hizmet ettiği kavram
