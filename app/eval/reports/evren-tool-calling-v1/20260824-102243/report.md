# Ablasyon raporu — kural vs LLM vs hibrit

## Künye (tekrar-üretim)

| künye | değer |
|---|---|
| konfig | ablation[kural,llm,hibrit] |
| gold dosyası | data/gold/gold.v1.json |
| gold sha256 | ba2701cde3ed6fcc… |
| gold kayıt sayısı | 20 |
| alt küme (split) | all |
| eşleştirici(ler) | strict |
| seed | 42 |
| git sha | 6feedd1c56626d1f3b6fb1b11dd69467916cc330 |
| commit'lenmemiş değişiklik | EVET (dikkat: sayı bir commit'e karşılık gelmiyor) |
| Python | 3.14.7 |
| platform | macOS-26.5.2-arm64-arm-64bit-Mach-O |
| bağımlılık | yalnız Python stdlib (numpy/scipy/sklearn YOK) |
| üretim zamanı (UTC) | 2026-08-24T10:22:43.299639+00:00 |

## Kollar (eşleştirici `strict`)

| konfig | mikro-F1 (tüm) | makro-F1 | mikro-F1 (zor) | mikro-F1 %95 GA | halüsinasyon |
|---|---|---|---|---|---|
| kural | 0.469 | 0.510 | 0.000 | 0.469 [0.322–0.574] | 0.096 |
| llm | 0.304 | 0.408 | 0.000 | 0.304 [0.202–0.380] | 0.108 |
| hibrit | 0.483 | 0.541 | 0.000 | 0.483 [0.341–0.595] | 0.157 |

## İstatistiksel karşılaştırma (McNemar)

Eşleşmiş çift = **(belge, alan) kararı**. Test yalnız UYUMSUZ çiftlere bakar; iki kol aynı kararı verdiğinde ayırt edici bilgi yoktur.

Yöntem seçimi: `b + c < 25` ise **tam binom testi**, değilse **süreklilik düzeltmeli χ²**. χ², kesikli binom dağılımına yapılan sürekli bir yaklaşımdır ve `b + c` küçükken hatası göreli olarak büyür (ör. b=8, c=0: tam test 0,0078, χ² 0,0133). Hangi yöntemin kullanıldığı her satırda yazar.

| A | B | alt küme | b | c | p | yöntem | sonuç | mikro-F1 farkı (A−B) %95 GA |
|---|---|---|---|---|---|---|---|---|
| kural | llm | all | 27 | 14 | 0.06092 | chi2_continuity | fark anlamsız | 0.165 [0.058–0.259] |
| kural | llm | hard | 0 | 0 | 1 | exact_binomial | fark anlamsız | 0.000 [0.000–0.000] |
| kural | hibrit | all | 10 | 5 | 0.3018 | exact_binomial | fark anlamsız | -0.014 [-0.067–0.036] |
| kural | hibrit | hard | 0 | 0 | 1 | exact_binomial | fark anlamsız | 0.000 [0.000–0.000] |
| llm | hibrit | all | 13 | 21 | 0.2299 | chi2_continuity | fark anlamsız | -0.179 [-0.279–-0.070] |
| llm | hibrit | hard | 0 | 0 | 1 | exact_binomial | fark anlamsız | 0.000 [0.000–0.000] |
