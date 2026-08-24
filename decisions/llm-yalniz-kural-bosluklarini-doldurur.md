---
title: "LLM yalnız kural boşluklarını doldurur — iki kabul kapısıyla"
tags: [karar, cikarim, llm, evren, dayanak, olcum]
source: "[[2026-08-24-tkbb-kar-payi-veri-seti]]"
date: 2026-08-24
status: stable
---

# LLM yalnız kural boşluklarını doldurur

## Karar

LLM çıkarımı, kural hattının **hiç değer üretmediği** alanlarda çalışır ve her
bulgusu iki kapıdan geçer. Kapılardan biri düşerse değer DB'ye yazılmaz.

| kapı | soru | ölçülmüş vaka |
|---|---|---|
| **dayanak** | değerin bütün sayıları metinde geçiyor mu? | `{min:0, max:4.82}` ← *"Aylık Kâr Oranı %0"* → 4,82 metinde YOK |
| **alan** | kanıt penceresi alanla çelişmiyor mu? | `0.4` ← *"%0.4 Aval komisyon oranı"* → aval komisyonu kâr payı DEĞİL |

`Repository.add_fields(..., ezme=False)` kural değerini **asla ezmez**.
`extractor='llm'` damgası zorunlu: kaynağı görünmeyen bir değer denetlenemez.

## Gerekçe: bu, "LLM kuraldan zayıf" ölçümüyle ÇELİŞMİYOR

Daha önce ölçüldü: EVREN'in çıkarım kolu F1 **0,304–0,331**, kural hattı
**0,469–0,570** ([[ssb-evren-cikarim-servisi]]). O ölçümde iki kol **aynı
alan için yarışıyordu** ve kural kazandı.

Buradaki soru farklı: kural **hiçbir şey söylemiyorsa** LLM ne bulur?
Hedef kategorilerde (Taşıt/İhtiyaç/Konut Finansmanı, Yatırım Ürünü,
Finansman) kural `kar_payi_orani`'nı 773 kampanya belgesinin yalnız 48'inde
(%6,2) çıkarabiliyor — bir kural hatası değil, veri gerçeği: bankalar oranı
çoğu kampanya metninde yayınlamıyor. Ama 368 belgede "kâr payı / oran"
sözcüğü geçiyor ve değer çıkmamış.

Ölçüm (2026-08-24, 120 belge, EVREN `llm-large`):

| alan | LLM buldu | dayanaksız | yanlış-alan | KABUL |
|---|---|---|---|---|
| `kar_payi_orani` | 14/120 | 0 | 0 | **14 (%12)** |
| `finansman_tutari` | 17/120 | 0 | 0 | **17 (%14)** |

Yani kuralın boş bıraktığı yerde **%12–14 ek kapsam, sıfır uydurma**. Bu tam
olarak CLAUDE.md §3'ün tasarımı: kural birincil, LLM yalnız boşluk.

## Niçin İKİ kapı, biri yetmiyor

*"%0.4 Aval komisyon oranı"* → `kar_payi_orani = 0.4`. Sayı metinde
**gerçekten var**, yani halüsinasyon değil; değer doğru okunmuş, **yanlış
alana** yazılmış. Dayanak kapısı bunu geçirir. İki ayrı soru, iki ayrı kapı.

30 belgelik kuru koşumda semantik kapı tam bu vakayı yakaladı (6 kabul,
1 yanlış-alan).

## Sözcükle yazılmış büyüklükler

*"1 milyar TL limitli"* → `1000000000` **doğru** bir çevrimdir ama sayısal
biçimi metinde geçmez; ilk ölçümde yanlış biçimde "uydurma" sayıldı. Kapı
`bin/milyon/milyar` çarpanlarını da deniyor ve tam kat olmayanı da kabul
ediyor (*"2,5 milyon"* — testle yakalandı).

## Reddedilen seçenek

**Serbest metin alanlarını da doldurmak** (`kampanya_kosullari`). Orada dayanak
kapısı UYGULANAMAZ (sayı yok), yani tek savunma kalmaz. `kabul_edilir` bu
durumda `sayisal-degil` gerekçesiyle reddediyor — sessizce geçirmiyor.

## İlgili dosyalar

- `app/src/extraction/llm/dayanak.py` — iki kapı
- `app/src/db/repository.py` — `add_fields`, kural değerini ezmez
- `app/scripts/llm_bosluk_doldur.py` — koşum ve raporlama
- `app/tests/test_llm_dayanak_kapilari.py` (26) · `test_db_add_fields.py` (9)

## Sources

- [[2026-08-24-tkbb-kar-payi-veri-seti]] — aynı günün ölçüm oturumu
- `app/docs/evren-servisi.md` §3-c, §9 — çıkarım kolunun F1 ölçümü

## Related

- [[ssb-evren-cikarim-servisi]] — ölçülen servis
- [[bilgi-cikarimi]] — kavramsal zemin
- [[kar-payi-orani]] — kapsamı artırılan alan
- [[urun-baglami-alan-duzeyinde-tasinmali]] — aynı disiplin: sessiz hata yerine açık işaret
