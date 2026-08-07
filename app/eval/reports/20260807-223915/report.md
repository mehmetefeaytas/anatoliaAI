# Ablasyon raporu — kural vs LLM vs hibrit

## Künye (tekrar-üretim)

| künye | değer |
|---|---|
| konfig | ablation[kural,orkestra,orkestra-hakemsiz] |
| gold dosyası | data/gold/gold.v2.json |
| gold sha256 | af1d4f1b7ab2470a… |
| gold kayıt sayısı | 48 |
| alt küme (split) | all |
| eşleştirici(ler) | strict |
| seed | 42 |
| git sha | 155a0713453b2a8de5a2c720f5245737fd9aeed7 |
| commit'lenmemiş değişiklik | hayır |
| Python | 3.14.6 |
| platform | macOS-26.5.2-arm64-arm-64bit-Mach-O |
| bağımlılık | yalnız Python stdlib (numpy/scipy/sklearn YOK) |
| üretim zamanı (UTC) | 2026-08-07T22:39:15.182080+00:00 |

## Kollar (eşleştirici `strict`)

| konfig | mikro-F1 (tüm) | makro-F1 | mikro-F1 (zor) | mikro-F1 %95 GA | halüsinasyon |
|---|---|---|---|---|---|
| kural | 0.387 | 0.408 | 0.405 | 0.387 [0.329–0.442] | 0.101 |
| orkestra | 0.377 | 0.404 | 0.394 | 0.377 [0.325–0.426] | 0.119 |
| orkestra-hakemsiz | 0.362 | 0.380 | 0.377 | 0.362 [0.308–0.414] | 0.135 |

## İstatistiksel karşılaştırma (McNemar)

Eşleşmiş çift = **(belge, alan) kararı**. Test yalnız UYUMSUZ çiftlere bakar; iki kol aynı kararı verdiğinde ayırt edici bilgi yoktur.

Yöntem seçimi: `b + c < 25` ise **tam binom testi**, değilse **süreklilik düzeltmeli χ²**. χ², kesikli binom dağılımına yapılan sürekli bir yaklaşımdır ve `b + c` küçükken hatası göreli olarak büyür (ör. b=8, c=0: tam test 0,0078, χ² 0,0133). Hangi yöntemin kullanıldığı her satırda yazar.

| A | B | alt küme | b | c | p | yöntem | sonuç | mikro-F1 farkı (A−B) %95 GA |
|---|---|---|---|---|---|---|---|---|
| kural | orkestra | all | 8 | 1 | 0.03906 | exact_binomial | kazanan kural | 0.010 [-0.008–0.026] |
| kural | orkestra | hard | 8 | 1 | 0.03906 | exact_binomial | kazanan kural | 0.011 [-0.008–0.028] |
| kural | orkestra-hakemsiz | all | 15 | 1 | 0.0005188 | exact_binomial | kazanan kural | 0.025 [0.005–0.042] |
| kural | orkestra-hakemsiz | hard | 15 | 1 | 0.0005188 | exact_binomial | kazanan kural | 0.028 [0.007–0.045] |
| orkestra | orkestra-hakemsiz | all | 7 | 0 | 0.01562 | exact_binomial | kazanan orkestra | 0.015 [0.007–0.025] |
| orkestra | orkestra-hakemsiz | hard | 7 | 0 | 0.01562 | exact_binomial | kazanan orkestra | 0.017 [0.008–0.026] |
