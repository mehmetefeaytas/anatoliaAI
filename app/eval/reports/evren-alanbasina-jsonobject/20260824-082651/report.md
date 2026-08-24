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
| üretim zamanı (UTC) | 2026-08-24T08:26:51.742310+00:00 |

## Kollar (eşleştirici `strict`)

| konfig | mikro-F1 (tüm) | makro-F1 | mikro-F1 (zor) | mikro-F1 %95 GA | halüsinasyon |
|---|---|---|---|---|---|
| kural | 0.469 | 0.510 | 0.000 | 0.469 [0.322–0.574] | 0.096 |
| llm | 0.323 | 0.345 | 0.000 | 0.323 [0.215–0.415] | 0.108 |
| hibrit | 0.507 | 0.544 | 0.000 | 0.507 [0.376–0.601] | 0.157 |

## İstatistiksel karşılaştırma (McNemar)

Eşleşmiş çift = **(belge, alan) kararı**. Test yalnız UYUMSUZ çiftlere bakar; iki kol aynı kararı verdiğinde ayırt edici bilgi yoktur.

Yöntem seçimi: `b + c < 25` ise **tam binom testi**, değilse **süreklilik düzeltmeli χ²**. χ², kesikli binom dağılımına yapılan sürekli bir yaklaşımdır ve `b + c` küçükken hatası göreli olarak büyür (ör. b=8, c=0: tam test 0,0078, χ² 0,0133). Hangi yöntemin kullanıldığı her satırda yazar.

| A | B | alt küme | b | c | p | yöntem | sonuç | mikro-F1 farkı (A−B) %95 GA |
|---|---|---|---|---|---|---|---|---|
| kural | llm | all | 27 | 16 | 0.1273 | chi2_continuity | fark anlamsız | 0.146 [-0.000–0.256] |
| kural | llm | hard | 0 | 0 | 1 | exact_binomial | fark anlamsız | 0.000 [0.000–0.000] |
| kural | hibrit | all | 10 | 7 | 0.6291 | exact_binomial | fark anlamsız | -0.038 [-0.109–0.019] |
| kural | hibrit | hard | 0 | 0 | 1 | exact_binomial | fark anlamsız | 0.000 [0.000–0.000] |
| llm | hibrit | all | 9 | 17 | 0.1698 | chi2_continuity | fark anlamsız | -0.184 [-0.284–-0.071] |
| llm | hibrit | hard | 0 | 0 | 1 | exact_binomial | fark anlamsız | 0.000 [0.000–0.000] |
