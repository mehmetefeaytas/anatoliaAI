---
title: "Sorun: gold.round1.json kaynak CSV'lerden yeniden üretilemiyor"
tags: [sorun, gold, tekrar-uretilebilirlik, olcum]
date: 2026-08-21
status: stable
---

# Sorun: `gold.round1.json` kaynak CSV'lerden yeniden üretilemiyor

**Belirti.** Ölçümün referansı olan `app/data/gold/gold.round1.json` 134 kayıt
taşıyor. Aynı dosyayı üreten dört anotasyon CSV'sinden derleme yalnız **57**
kayıt veriyor:

```bash
cd app && .venv/bin/python -m scripts.build_gold \
  --csv data/gold/review/round1_A.csv --csv data/gold/review/round1_B.csv \
  --csv data/gold/review/round1_main_C.csv --csv data/gold/review/round1_main_D.csv \
  --out /tmp/deneme.json
# -> kayıt: 57   (hedef: 134)
```

Düşen 77 kaydın anotatör kırılımı: **46 `D`**, **30 `A`+`B`**, 1
`D`+`HAKEM-04`. Yalnız `D`'den derleme 31 kayıt veriyor; `D` ile dörtlünün
birleşimi hâlâ 57'de kalıyor, yani eksik kayıtlar CSV'lerin bugünkü hâlinde
**yok**.

**Kök neden.** İki aday var ve ikisi de kayıtsız:

1. **Derleme komutu hiçbir yerde yazılı değil.** `build_gold.py` `--csv-dir`
   ile `round*.csv` deseni kabul ediyor ama `gold.round1.json`'u hangi dosya
   kümesiyle ve hangi bayraklarla ürettiğimiz ne README'de, ne `log.md`'de,
   ne bir Makefile hedefinde duruyor. Deponun kendi kuralı ("her sayı bir
   komutla yeniden üretilebilir") burada tutmuyor.
2. **CSV'ler gold üretildikten SONRA değişti.** `data/gold/review/` altında
   `round1_A.csv.yedek-hakemlik-round1` ve `.yedek-sema-onarimi-round1`
   yedekleri var; yani hakemlik ve şema onarımı turları CSV'lere dokundu.
   Gold JSON o turlardan önceki bir durumdan türemiş olabilir.

**Etki.** Üç ayrı yerden vuruyor:

- **Ölçüm tabanı denetlenemez.** Jüri "gold'u kim, hangi kararla doldurdu"
  diye sorup CSV'den JSON'a giden yolu izleyemiyor.
- **Tahkim kararları JSON'a yazılmak zorunda kaldı.** HAKEM-05'in 23 kararı
  (anotatör onaylı, 2026-08-21) doğrudan `gold.round1.json`'a uygulandı;
  CSV'lere işlenmedi. CSV'den türetmek bugün ölçüm tabanını 134'ten 57'ye
  düşürür, yani düzeltme yaparken ölçümü bozar.
- **Şartnamenin tekrar-üretilebilirlik beklentisi (Teknik İmplementasyon)
  bu noktada karşılanmıyor.** Jüri 3. turda bunu bulmadı; 4. turda kendimiz
  yazdık ve jüri "üç turdur aynı itiraf" diye not düştü.

**Çözüm — henüz UYGULANMADI, sıra ve gerekçe:**

1. **Kanıt yolunu tersten kur.** `gold.round1.json`'daki her kaydın hangi
   CSV satırından geldiğini `doc_id` + `annotators` üzerinden eşle; eşleşmeyen
   77 kaydı adlandır. Bu, hangi turun hangi kaydı ürettiğini gösterir.
2. **Yedeklerle dene.** `*.yedek-hakemlik-round1` ve
   `*.yedek-sema-onarimi-round1` dosyalarıyla derleme 134'ü veriyor mu?
   Veriyorsa komut belgelenir ve iş biter.
3. **Vermiyorsa JSON'u kaynak ilan et.** O zaman CSV'ler *tarihî kayıt*,
   JSON *doğruluk kaynağı* olur; bu karar bir ADR'ye yazılır ve JSON'a
   yazan tek meşru yol (`scripts/hakem_uygula.py` gibi bir betik, anotatör
   onayı zorunlu) tanımlanır. Bugün o betik yok; HAKEM-05 kararları
   scratchpad'deki geçici bir betikle uygulandı ve bu izlenebilirlik açığı.
4. **Kayıt sayısını bir kapıya bağla.** `kanit_tazeligi` `gold_round1_kayit`
   iddiasını zaten ölçüyor (134) ama *kaynaktan üretilebilirliği* ölçmüyor.
   Bir test derlemeyi koşup kayıt sayısını karşılaştırmalı; ayrışırsa CI
   düşmeli.

**Neden şimdi kapatılmadı.** Yarışmanın çevrimiçi süreci 26 Ağustos'ta
bitiyor ve bu iş ölçüm tabanına dokunuyor. Yanlış sırada yapılırsa
`gold.round1` ölçümleri (mikro-F1 0,793, halüsinasyon 0,284) yeniden
üretilemez hâle gelir. Boşluk gizlenmiyor: HAKEM-05 paketinde, kök
README'de ve burada yazılı.

## Sources
- `app/data/gold/review/_hakem-turu-05-finansman-tutari-round1.md` — "KAPSAM
  SINIRI ve YENİ KUSUR" bölümü, ölçümün yapıldığı yer
- 4. tur Yenilikçilik jürisi — "kendi tespit ettiği kusuru kendi önerdiği
  yere taşımamış" bulgusu; bu sayfa o bulgunun karşılığı

## Related
- [[standart-veri-formati-eksikligi]] — aynı ailedeki veri disiplini sorunu
