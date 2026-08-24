---
title: "Çelişki Tespiti 47 saniye sürüyordu ve 500 dönüyordu"
tags: [sorun, celiski, performans, onbellek, api, panel]
source: "kullanıcı raporu (2026-08-24) + ölçüm"
date: 2026-08-24
status: stable
---

# Çelişki Tespiti 47 saniye sürüyordu

## Belirti

Kullanıcı raporu (2026-08-24): panelin Çelişki Tespiti sekmesi *"yavaş"* ve
ekranda iki kez şu duruyor:

```
İstek başarısız
Sunucu 500 döndü.
```

İki kez, çünkü panel iki ucu birden çağırıyor: `/contradictions` (bulgular) ve
`/contradictions/summary` (tarama kapsamı).

## Ölçüm — nerede olmadığını da ölçtük

| ne | süre |
|---|---|
| `repo.all_campaigns()` — 2.708 belge, gövdeyle | **0,08 sn** |
| tam tarama (çıkarım + tespit) | **47,2 sn** |
| ↳ belge başına | 17,4 ms |
| ↳ `build_campaign` payı | ~%92 |
| ↳ `detect` payı | ~%8 |

Yani sorun veri tabanı okumasında **değil**. Her istek 2.708 belgede kural
çıkarımını sıfırdan koşuyor; 29 MB metin yeniden ayrıştırılıyor.

İlk ölçüm yanıltmıştı: 200 belgelik örneklem 7,5 saniye tahmini vermişti, çünkü
`id` sırasındaki ilk 200 belge korpusun küçük olanları. Tam korpusta ölçülünce
gerçek sayı çıktı — **örneklem seçimi ölçümü üçe böldü.**

## Kök neden — üç katman

1. **Önbellek yoktu.** Sonuç korpus sabitken değişmiyor ama her istekte
   yeniden hesaplanıyordu.
2. **Özet, taramayı ikinci kez koşturuyordu.** `contradictions_summary()`
   doğrudan `contradictions()` çağırıyordu; panel iki ucu birlikte çağırdığı
   için her sekme açılışı **iki tam tarama** demekti.
3. **Eşzamanlılık korumasızdı.** İki istek aynı anda gelince iki iş parçacığı
   da önbelleği boş buluyor ve 47 saniyelik taramayı paralel koşuyordu.
   Next dev sunucusunun `/api/*` proxy'si o kadar beklemiyor ve yavaş yanıtı
   **500**'e çeviriyor — kullanıcının gördüğü hata buydu.

## Çözüm — üç adım, sonuncusu asıl olan

**1. Süreç içi önbellek + kilit.** Tarama bir kez koşuyor; kilidi bekleyen
ikinci istek birincinin sonucunu buluyor. Geçersizleştirme veri tazelendiğinde
dışarıdan yapılıyor (`app.state.celiski_onbellegini_dus`) — bayat bir çelişki
listesi göstermek, yavaş olmaktan kötüdür.

**2. Açılışta ön ısıtma.** Tarama arka plan iş parçacığında, istek gelmeden
başlıyor.

**3. KALICI ARTEFAKT — asıl çözüm.** İlk ikisi ikinci isteği çözüyor, birinciyi
çözmüyordu; jüri sekmeye ilk tıkladığında beklediği süre yine o 47 saniyeydi.
`scripts/celiski_tarama.py` taramayı bir kez koşup sonucu
`data/celiski-taramasi.json`'a yazıyor; API açılışta imzayı denetleyip tazeyse
hiç taramıyor.

Tazelik **dosya damgasına değil korpus imzasına** bakıyor: belge sayısı + en
yeni `scraped_at`. Dosya tarihi depo klonlanınca değişir, içerik değişmez;
imza ise korpus değişmeden değişmez. İmza tutmuyorsa artefakt **yok sayılıyor**
ve tarama koşuyor.

### Ölçülen sonuç

| | önce | sonra |
|---|---|---|
| soğuk `/contradictions` | 47,9 sn | **0,001 sn** |
| soğuk `/contradictions/summary` | 47,9 sn (ikinci tarama) | **0,022 sn** |
| bulgu sayısı | 20 | 20 (değişmedi) |
| etkilenen belge | 19 | 19 (değişmedi) |

## Yan bulgu — sessiz yutma

`_campaign_contradictions` içindeki `except Exception: out = []` bir belgeyi
taramadan sessizce düşürüyordu. İz bırakmadığı için *"0 çelişki"* ile *"tarama
çöktü"* ayırt edilemiyordu ve tarama kapsamı olduğundan geniş görünüyordu.
Artık `logger.debug` ile kampanya kimliğiyle birlikte kaydediliyor; betik
tarafında `stderr`'e yazılıyor.

## İlgili dosyalar

- `app/src/comparison/celiski_artefakti.py` — yeni (biçim + tazelik kuralı)
- `app/scripts/celiski_tarama.py` — yeni (artefaktı üretir, `--denetle` ile CI'ya bağlanabilir)
- `app/src/api/routers/denetim.py` — önbellek, kilit, ön ısıtma, artefakt okuma
- `app/src/api/main.py` — geçersizleştirme + sessiz yutmanın izlenmesi
- `app/tests/test_celiski_artefakti.py` — 15 test

## Sources

- Kullanıcı raporu, 2026-08-24 — iki canlı 500
- Ölçüm: `all_campaigns` 0,08 sn · tam tarama 47,2 sn · soğuk uç 47,9 → 0,001 sn

## Related

- [[ekran-cekimi-ham-veriyi-yeniden-topladi]] — aynı sekmenin başka arızası
- [[celiski-tespiti]] — taramanın kavramsal zemini
