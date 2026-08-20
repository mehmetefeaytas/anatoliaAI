# Ablasyon raporu — kural vs LLM vs hibrit

## Künye (tekrar-üretim)

| künye | değer |
|---|---|
| konfig | ablation[kural,llm,hibrit,hibrit-verify] |
| gold dosyası | data/gold/gold.v2.json |
| gold sha256 | e38a52766cf55e56… |
| gold kayıt sayısı | 48 |
| alt küme (split) | all |
| eşleştirici(ler) | strict |
| seed | 42 |
| git sha | 0728bc445d1682cc8c33796347c77be7ceefe30b |
| commit'lenmemiş değişiklik | hayır |
| Python | 3.14.6 |
| platform | macOS-26.5.2-arm64-arm-64bit-Mach-O |
| bağımlılık | yalnız Python stdlib (numpy/scipy/sklearn YOK) |
| üretim zamanı (UTC) | 2026-08-20T05:34:01.909521+00:00 |

## Kollar (eşleştirici `strict`)

| konfig | mikro-F1 (tüm) | makro-F1 | mikro-F1 (zor) | mikro-F1 %95 GA | halüsinasyon |
|---|---|---|---|---|---|
| kural | 0.477 | 0.632 | 0.500 | 0.477 [0.407–0.536] | 0.043 |
| llm | ÖLÇÜLMEDİ | — | — | — | — |
| hibrit | ÖLÇÜLMEDİ | — | — | — | — |
| hibrit-verify | ÖLÇÜLMEDİ | — | — | — | — |

## İstatistiksel karşılaştırma (McNemar)

Eşleşmiş çift = **(belge, alan) kararı**. Test yalnız UYUMSUZ çiftlere bakar; iki kol aynı kararı verdiğinde ayırt edici bilgi yoktur.

Yöntem seçimi: `b + c < 25` ise **tam binom testi**, değilse **süreklilik düzeltmeli χ²**. χ², kesikli binom dağılımına yapılan sürekli bir yaklaşımdır ve `b + c` küçükken hatası göreli olarak büyür (ör. b=8, c=0: tam test 0,0078, χ² 0,0133). Hangi yöntemin kullanıldığı her satırda yazar.

Karşılaştırılacak en az iki ölçülebilen kol yok.

## Notlar (sessiz sınırlama YOK)

- `llm` ÖLÇÜLMEDİ: LLM backend kapalı (offline). Bu konfig ÖLÇÜLMEDİ — sahte bir 'hibrit = kural' satırı üretmemek için atlandı. Ölçmek için: LLM_BACKEND=vllm|ollama (ve tercihen LLM_STRICT=1).
- `hibrit` ÖLÇÜLMEDİ: LLM backend kapalı (offline). Bu konfig ÖLÇÜLMEDİ — sahte bir 'hibrit = kural' satırı üretmemek için atlandı. Ölçmek için: LLM_BACKEND=vllm|ollama (ve tercihen LLM_STRICT=1).
- `hibrit-verify` ÖLÇÜLMEDİ: LLM backend kapalı (offline). Bu konfig ÖLÇÜLMEDİ — sahte bir 'hibrit = kural' satırı üretmemek için atlandı. Ölçmek için: LLM_BACKEND=vllm|ollama (ve tercihen LLM_STRICT=1).
