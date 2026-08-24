---
title: "TCMB sözlüğü terim boşluğunu kapatmıyor (ölçüldü, entegrasyon yapılmadı)"
tags: [sorun, terminoloji, sozluk, olcum, reddedilen-yol]
source: "ölçüm (2026-08-24, data/terminology/)"
date: 2026-08-24
status: stable
---

# TCMB sözlüğü terim boşluğunu kapatmıyor

## Öneri neydi

*"Finansman ne demek"* sorusu cevaplanamıyordu; katılım terim sözlüğü (101
kayıt) katılım bankacılığına **özgü** terimleri içeriyor (murabaha, riba,
garar…) ve "finansman" gibi genel bir terim orada yok
([[terim-sorusuna-sozlukten-cevap-verilmiyordu]] "Kalan sınır" bölümü).

Öneri: `data/terminology/tcmb-terimler.json` (314 terim, tanımlı, kaynak
URL'li) arama kapsamına alınsın.

## Ölçüm — öneri ÇÜRÜDÜ

| ölçüt | sonuç |
|---|---|
| TCMB sözlüğünde **"Finansman"** kaydı | **YOK** |
| "finansman" içeren TCMB terimi | 2 (*Kamu Kaynaklı Finansman*, *Oto-Finansman*) |
| katılım sözlüğüyle çakışan | 7 |
| **teriminde** yasak kök (faiz/kredi/mevduat) | 19 |
| **tanımında** yasak kök | 69 (**%22**) |

TCMB sözlüğü bir **makroekonomi** sözlüğüdür — ilk kaydı *"AB Tanımlı Genel
Yönetim Borç Stoku"*. Bankacılık ÜRÜN terimleri sözlüğü değil. Yani
hedeflenen boşluğu kapatmıyor ve %22'si katılım bağlamında sorunlu terim
taşıyor.

**Karar: entegrasyon YAPILMADI.** Gerekçesi ölçüm.

## Asıl boşluk nerede — ölçüldü

Chatbot'a sorulması en muhtemel 27 temel terim tarandı; **10'u eksik** ve
hepsi **projenin kendi alan adlarıyla örtüşüyor**:

    finansman · vade · taksit · tahsis ücreti · masraf · stopaj
    ekspertiz · limit · hesap işletim ücreti · dosya masrafı

Yani sistem `tahsis_ucreti` alanını çıkarıyor ama *"tahsis ücreti ne demek"*
sorusuna cevap veremiyor.

## Korpustan tanım çıkarma da işlemedi

982 sözleşme belgesinde tanım kalıbı arandı:

| terim | sözleşmede geçiyor | tanım kalıbı |
|---|---|---|
| tahsis ücreti | 79 | **0** |
| taksit | 288 | **0** |
| stopaj | 59 | **0** |
| limit | 464 | **0** |
| masraf | 621 | **0** |
| finansman | 423 | 11 (ama taraf tanımı: *"finansman temin eden … Müşteriyi ifade eder"*) |
| vade | 661 | 23 (işleyiş cümlesi, tanım değil) |

Sözleşmeler bu terimleri **kullanıyor ama tanımlamıyor** — projede daha önce
ölçülen *"bankalar terimi kullanır ama açıklamaz"* bulgusunun aynısı
(`docs/rapor/musaraka-veri-boslugu.md`).

## SONRAKİ ADIM UYGULANDI — ama boşluk yine kapanmadı

TKBB Katılım Sözlüğü hasat edildi (**509 terim**, hepsi kullanım örnekli,
ortalama 398 karakter tanım) ve ikincil kaynak olarak bağlandı:
**101 → 577 terim** ([[tkbb-sozlugu-ikincil-kaynak-olarak-baglanir]]).

Ama o sözlük de fıkhî/kavramsal: hasat edilen 509 terimin yalnız
`murabaha`'sı yukarıdaki 10 terimlik eksik listeyle kesişiyor. Yani üç kaynak
denendi (TCMB, korpus sözleşmeleri, TKBB) ve **hiçbiri operasyonel terimleri
içermiyor**. Kazanç gerçek — `zarûriyyât`, `içtihâd`, `konvansiyonel
bankacılık` gibi 476 terim artık cevaplanıyor — ama *"tahsis ücreti ne demek"*
hâlâ cevapsız.

## Açık kalan yol

Tanımı bir dil modeline ürettirmek **kaynaksız iddia** olurdu (CLAUDE.md §19)
ve bu yüzden yapılmadı. Kalan seçenekler:

1. ~~TKBB Katılım Sözlük~~ — **yapıldı**, operasyonel terimleri içermiyor
   (yukarı bkz.).
2. Mevzuat kaynakları (BDDK ücret yönetmeliği, GVK 94 — stopaj) — elle,
   kaynak künyesiyle.
3. Alan açıklaması olarak sunmak: terim tanımı değil, "bu sistemde bu alan şu
   demek". Kaynağı kendi şemamız olurdu, yani kaynaklı — ama sorulan soruya
   tam cevap değil.

## Sources

- `data/terminology/tcmb-terimler.json` — 314 kayıt, ölçüldü
- `data/terminology/katilim-terim-sozlugu.json` — 101 kayıt, 574 arama anahtarı
- `data/demo.db` — 982 sözleşme, tanım kalıbı taraması

## Related

- [[terim-sorusuna-sozlukten-cevap-verilmiyordu]] — boşluğun ilk tespiti
- [[kar-payi-orani]] — sözlüğün beslediği kavram
