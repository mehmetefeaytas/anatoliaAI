# Ablasyon raporu — kural vs LLM vs hibrit

## Künye (tekrar-üretim)

| künye | değer |
|---|---|
| konfig | ablation[kural,llm,hibrit] |
| gold dosyası | data/gold/gold.v2.json |
| gold sha256 | e38a52766cf55e56… |
| gold kayıt sayısı | 48 |
| alt küme (split) | all |
| eşleştirici(ler) | strict |
| seed | 42 |
| git sha | 6feedd1c56626d1f3b6fb1b11dd69467916cc330 |
| commit'lenmemiş değişiklik | EVET (dikkat: sayı bir commit'e karşılık gelmiyor) |
| Python | 3.14.7 |
| platform | macOS-26.5.2-arm64-arm-64bit-Mach-O |
| bağımlılık | yalnız Python stdlib (numpy/scipy/sklearn YOK) |
| üretim zamanı (UTC) | 2026-08-24T08:06:34.778708+00:00 |

## Kollar (eşleştirici `strict`)

| konfig | mikro-F1 (tüm) | makro-F1 | mikro-F1 (zor) | mikro-F1 %95 GA | halüsinasyon |
|---|---|---|---|---|---|
| kural | 0.570 | 0.765 | 0.587 | 0.570 [0.492–0.632] | 0.034 |
| llm | 0.329 | 0.589 | 0.332 | 0.329 [0.250–0.398] | 0.031 |
| hibrit | 0.556 | 0.753 | 0.571 | 0.556 [0.487–0.614] | 0.056 |

## İstatistiksel karşılaştırma (McNemar)

Eşleşmiş çift = **(belge, alan) kararı**. Test yalnız UYUMSUZ çiftlere bakar; iki kol aynı kararı verdiğinde ayırt edici bilgi yoktur.

Yöntem seçimi: `b + c < 25` ise **tam binom testi**, değilse **süreklilik düzeltmeli χ²**. χ², kesikli binom dağılımına yapılan sürekli bir yaklaşımdır ve `b + c` küçükken hatası göreli olarak büyür (ör. b=8, c=0: tam test 0,0078, χ² 0,0133). Hangi yöntemin kullanıldığı her satırda yazar.

| A | B | alt küme | b | c | p | yöntem | sonuç | mikro-F1 farkı (A−B) %95 GA |
|---|---|---|---|---|---|---|---|---|
| kural | llm | all | 47 | 18 | 0.0005147 | chi2_continuity | kazanan kural | 0.242 [0.157–0.323] |
| kural | llm | hard | 46 | 12 | 1.47e-05 | chi2_continuity | kazanan kural | 0.255 [0.172–0.343] |
| kural | hibrit | all | 10 | 2 | 0.03857 | exact_binomial | kazanan kural | 0.014 [-0.007–0.036] |
| kural | hibrit | hard | 10 | 2 | 0.03857 | exact_binomial | kazanan kural | 0.016 [-0.009–0.037] |
| llm | hibrit | all | 18 | 39 | 0.008071 | chi2_continuity | kazanan hibrit | -0.227 [-0.305–-0.147] |
| llm | hibrit | hard | 12 | 38 | 0.000407 | chi2_continuity | kazanan hibrit | -0.240 [-0.320–-0.166] |
