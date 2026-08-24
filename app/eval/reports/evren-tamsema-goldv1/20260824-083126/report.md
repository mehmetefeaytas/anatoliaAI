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
| üretim zamanı (UTC) | 2026-08-24T08:31:26.818852+00:00 |

## Kollar (eşleştirici `strict`)

| konfig | mikro-F1 (tüm) | makro-F1 | mikro-F1 (zor) | mikro-F1 %95 GA | halüsinasyon |
|---|---|---|---|---|---|
| kural | 0.469 | 0.510 | 0.000 | 0.469 [0.322–0.574] | 0.096 |
| llm | 0.331 | 0.436 | 0.000 | 0.331 [0.244–0.397] | 0.139 |
| hibrit | 0.510 | 0.555 | 0.000 | 0.510 [0.381–0.610] | 0.169 |

## İstatistiksel karşılaştırma (McNemar)

Eşleşmiş çift = **(belge, alan) kararı**. Test yalnız UYUMSUZ çiftlere bakar; iki kol aynı kararı verdiğinde ayırt edici bilgi yoktur.

Yöntem seçimi: `b + c < 25` ise **tam binom testi**, değilse **süreklilik düzeltmeli χ²**. χ², kesikli binom dağılımına yapılan sürekli bir yaklaşımdır ve `b + c` küçükken hatası göreli olarak büyür (ör. b=8, c=0: tam test 0,0078, χ² 0,0133). Hangi yöntemin kullanıldığı her satırda yazar.

| A | B | alt küme | b | c | p | yöntem | sonuç | mikro-F1 farkı (A−B) %95 GA |
|---|---|---|---|---|---|---|---|---|
| kural | llm | all | 31 | 16 | 0.04114 | chi2_continuity | kazanan kural | 0.138 [-0.003–0.254] |
| kural | llm | hard | 0 | 0 | 1 | exact_binomial | fark anlamsız | 0.000 [0.000–0.000] |
| kural | hibrit | all | 12 | 8 | 0.5034 | exact_binomial | fark anlamsız | -0.041 [-0.115–0.021] |
| kural | hibrit | hard | 0 | 0 | 1 | exact_binomial | fark anlamsız | 0.000 [0.000–0.000] |
| llm | hibrit | all | 12 | 23 | 0.09097 | chi2_continuity | fark anlamsız | -0.179 [-0.286–-0.064] |
| llm | hibrit | hard | 0 | 0 | 1 | exact_binomial | fark anlamsız | 0.000 [0.000–0.000] |
