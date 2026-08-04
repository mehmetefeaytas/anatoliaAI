# Ablasyon raporu — kural vs LLM vs hibrit

## Künye (tekrar-üretim)

| künye | değer |
|---|---|
| konfig | ablation[kural,llm,hibrit,hibrit-verify] |
| gold dosyası | data/gold/gold.v1.json |
| gold sha256 | ea04e44475521057… |
| gold kayıt sayısı | 20 |
| alt küme (split) | all |
| eşleştirici(ler) | strict |
| seed | 42 |
| git sha | 4117601f76cc6ff63455fb01f26ade9636eb5315 |
| commit'lenmemiş değişiklik | hayır |
| Python | 3.14.6 |
| platform | macOS-26.5.2-arm64-arm-64bit-Mach-O |
| bağımlılık | yalnız Python stdlib (numpy/scipy/sklearn YOK) |
| üretim zamanı (UTC) | 2026-08-04T21:52:06.894766+00:00 |

## Kollar (eşleştirici `strict`)

| konfig | mikro-F1 (tüm) | makro-F1 | mikro-F1 (zor) | mikro-F1 %95 GA | halüsinasyon |
|---|---|---|---|---|---|
| kural | 0.612 | 0.560 | 0.667 | 0.612 [0.483–0.716] | 0.102 |
| llm | 0.169 | 0.164 | 0.286 | 0.169 [0.095–0.242] | 0.145 |
| hibrit | 0.575 | 0.522 | 0.667 | 0.575 [0.443–0.688] | 0.163 |
| hibrit-verify | 0.562 | 0.507 | 0.333 | 0.562 [0.426–0.675] | 0.163 |

## İstatistiksel karşılaştırma (McNemar)

Eşleşmiş çift = **(belge, alan) kararı**. Test yalnız UYUMSUZ çiftlere bakar; iki kol aynı kararı verdiğinde ayırt edici bilgi yoktur.

Yöntem seçimi: `b + c < 25` ise **tam binom testi**, değilse **süreklilik düzeltmeli χ²**. χ², kesikli binom dağılımına yapılan sürekli bir yaklaşımdır ve `b + c` küçükken hatası göreli olarak büyür (ör. b=8, c=0: tam test 0,0078, χ² 0,0133). Hangi yöntemin kullanıldığı her satırda yazar.

| A | B | alt küme | b | c | p | yöntem | sonuç | mikro-F1 farkı (A−B) %95 GA |
|---|---|---|---|---|---|---|---|---|
| kural | llm | all | 52 | 15 | 1.092e-05 | chi2_continuity | kazanan kural | 0.443 [0.290–0.581] |
| kural | llm | hard | 3 | 1 | 0.625 | exact_binomial | fark anlamsız | 0.381 [0.381–0.381] |
| kural | hibrit | all | 10 | 1 | 0.01172 | exact_binomial | kazanan kural | 0.037 [-0.004–0.072] |
| kural | hibrit | hard | 0 | 0 | 1 | exact_binomial | fark anlamsız | 0.000 [0.000–0.000] |
| kural | hibrit-verify | all | 11 | 1 | 0.006348 | exact_binomial | kazanan kural | 0.050 [0.003–0.095] |
| kural | hibrit-verify | hard | 1 | 0 | 1 | exact_binomial | fark anlamsız | 0.333 [0.333–0.333] |
| llm | hibrit | all | 15 | 43 | 0.0003922 | chi2_continuity | kazanan hibrit | -0.406 [-0.555–-0.256] |
| llm | hibrit | hard | 1 | 3 | 0.625 | exact_binomial | fark anlamsız | -0.381 [-0.381–-0.381] |
| llm | hibrit-verify | all | 15 | 42 | 0.0005736 | chi2_continuity | kazanan hibrit-verify | -0.392 [-0.554–-0.235] |
| llm | hibrit-verify | hard | 1 | 2 | 1 | exact_binomial | fark anlamsız | -0.048 [-0.048–-0.048] |
| hibrit | hibrit-verify | all | 1 | 0 | 1 | exact_binomial | fark anlamsız | 0.014 [0.000–0.047] |
| hibrit | hibrit-verify | hard | 1 | 0 | 1 | exact_binomial | fark anlamsız | 0.333 [0.333–0.333] |
