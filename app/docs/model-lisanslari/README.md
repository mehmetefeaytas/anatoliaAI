# Model lisans artefaktları — iddia olarak değil dosya olarak

4. tur On-Prem jürisi haklı bir eksik buldu: kullanılan modellerin Apache-2.0
olduğunu **yazıyorduk** ama depoda bağımsız bir lisans artefaktı yoktu. Jüri
ayrıca `qwen3.5:9b-q4_K_M` adının Alibaba'nın resmî Qwen sürümleriyle
eşleşmediğini not etti; o şüphe yerinde ve aşağıda ele alınıyor.

## Nereden geldi

Ollama modelleri içerik-adresli bir blob deposunda tutuyor ve lisans metnini
manifestte **ayrı bir katman** olarak taşıyor. Dosyalar oradan çıkarıldı:

```bash
python3 - <<'PY'
import json, pathlib
kok = pathlib.Path.home() / ".ollama/models"
yol = kok / "manifests/registry.ollama.ai/library/qwen3.5/9b-q4_K_M"
m = json.loads(yol.read_text())
print(next(l["digest"] for l in m["layers"] if "license" in l["mediaType"]))
PY
# -> sha256:7339fa418c9ad3e8e12e74ad0fd26a9cc4be8703f9c110728a992b193be85cb2
# blob: ~/.ollama/models/blobs/sha256-7339fa418c9ad3e8...
```

| Dosya | Model | Lisans katmanı sha256 | Bayt |
|---|---|---|---|
| `qwen3.5-9b-q4_K_M-LICENSE.txt` | `qwen3.5:9b-q4_K_M` | `7339fa418c9ad3e8e12e74ad0fd26a9cc4be8703f9c110728a992b193be85cb2` | 11.355 |
| `qwen2.5-7b-instruct-LICENSE.txt` | `qwen2.5:7b-instruct` | `832dd9e00a68dd83b3c3fb9f5588dad7dcf337a0db50f7d9483f310cd292e92e` | 11.343 |

İkisi de **Apache License 2.0**. Digest yazılı olduğu için artefakt
denetlenebilir: dosyanın sha256'sı yukarıdaki digest ile eşleşmeli.

## `qwen3.5` adı — şüphe yerinde, risk sınırlı

Jürinin tespiti doğru: `qwen3.5` Alibaba'nın numaralandırmasında
doğrulanabilir bir sürüm değil (Qwen, 1.5, 2, 2.5, 3). Ollama kütüphanesinde
bu etiketle bir imaj var ve **Apache-2.0 lisans katmanı taşıyor**, ama adın
yukarı akış (upstream) karşılığını doğrulayamıyoruz.

Riski üç şey sınırlıyor:

1. **Model teslim edilen üretim yolunda kullanılmıyor.** `--llm` varsayılanı
   `kapali`; bu model yalnız ablasyon ölçümünde ikame olarak koştu
   (`docs/rapor/llm-uretim-devreye-alma.md`, sekiz hücrenin dördü).
2. **Ölçüm onu zaten reddetti.** 9B kolu kabul kapısından geçemedi; üretime
   alınması gündemde bile değil.
3. **Şüphe adın kökeninde, lisans metninde değil.** Katman Apache-2.0 ve
   digest'i yukarıda.

**Ne yapılmadı ve niçin:** yukarı akış model kartını indirip karşılaştırmak ağ
ister; bu doğrulama yapılmadı. Teslimde kullanılan tek model
`qwen2.5:7b-instruct` ve onun kökeni tartışmalı değil.
