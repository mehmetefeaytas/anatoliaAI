# Ablasyon raporu — kural vs LLM vs hibrit

## Künye (tekrar-üretim)

| künye | değer |
|---|---|
| konfig | ablation[kural,llm,hibrit] |
| gold dosyası | data/gold/gold.v2.json |
| gold sha256 | af1d4f1b7ab2470a… |
| gold kayıt sayısı | 48 |
| alt küme (split) | all |
| eşleştirici(ler) | strict |
| seed | 42 |
| git sha | f44bf25570e7b473a3a86f24c3550212f2497849 |
| commit'lenmemiş değişiklik | hayır |
| Python | 3.14.6 |
| platform | macOS-26.5.2-arm64-arm-64bit-Mach-O |
| bağımlılık | yalnız Python stdlib (numpy/scipy/sklearn YOK) |
| üretim zamanı (UTC) | 2026-08-13T20:56:10.545044+00:00 |

## Kollar (eşleştirici `strict`)

| konfig | mikro-F1 (tüm) | makro-F1 | mikro-F1 (zor) | mikro-F1 %95 GA | halüsinasyon |
|---|---|---|---|---|---|
| kural | 0.452 | 0.556 | 0.473 | 0.452 [0.386–0.510] | 0.059 |
| llm | 0.251 | 0.256 | 0.245 | 0.251 [0.185–0.325] | 0.056 |
| hibrit | 0.421 | 0.496 | 0.431 | 0.421 [0.366–0.469] | 0.117 |

## İstatistiksel karşılaştırma (McNemar)

Eşleşmiş çift = **(belge, alan) kararı**. Test yalnız UYUMSUZ çiftlere bakar; iki kol aynı kararı verdiğinde ayırt edici bilgi yoktur.

Yöntem seçimi: `b + c < 25` ise **tam binom testi**, değilse **süreklilik düzeltmeli χ²**. χ², kesikli binom dağılımına yapılan sürekli bir yaklaşımdır ve `b + c` küçükken hatası göreli olarak büyür (ör. b=8, c=0: tam test 0,0078, χ² 0,0133). Hangi yöntemin kullanıldığı her satırda yazar.

| A | B | alt küme | b | c | p | yöntem | sonuç | mikro-F1 farkı (A−B) %95 GA |
|---|---|---|---|---|---|---|---|---|
| kural | llm | all | 51 | 28 | 0.01332 | chi2_continuity | kazanan kural | 0.201 [0.108–0.284] |
| kural | llm | hard | 51 | 20 | 0.0003704 | chi2_continuity | kazanan kural | 0.227 [0.143–0.308] |
| kural | hibrit | all | 26 | 5 | 0.000328 | chi2_continuity | kazanan kural | 0.032 [-0.009–0.069] |
| kural | hibrit | hard | 26 | 4 | 0.000126 | chi2_continuity | kazanan kural | 0.042 [0.002–0.078] |
| llm | hibrit | all | 36 | 38 | 0.9075 | chi2_continuity | fark anlamsız | -0.170 [-0.239–-0.091] |
| llm | hibrit | hard | 29 | 38 | 0.3284 | chi2_continuity | fark anlamsız | -0.185 [-0.254–-0.111] |
