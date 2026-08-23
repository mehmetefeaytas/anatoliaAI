# Model lisans artefaktları — iddia olarak değil dosya olarak

4. tur On-Prem jürisi haklı bir eksik buldu: kullanılan modellerin Apache-2.0
olduğunu **yazıyorduk** ama depoda bağımsız bir lisans artefaktı yoktu. Jüri
ayrıca `qwen3.5:9b-q4_K_M` adının Alibaba'nın resmî Qwen sürümleriyle
eşleşmediğini not etti. O şüphe **kaydedildiği tarihte yerindeydi ama artık
geçersizdir** — 23 Ağu 2026'da yukarı akış doğrulandı; bkz. §ÇELİŞKİ.

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

## ÇELİŞKİ — `qwen3.5` adı (ÇÖZÜLDÜ, 23 Ağustos 2026)

Bu belge ile `../model-license-audit.md` §1 aynı model hakkında **birbirini
yalanlıyordu**. Çelişki 5. tur On-Prem jürisi tarafından bulundu ve
işaretlenmemişti; aşağıda iki taraf da kaynağıyla duruyor.

**Bu belgenin iddiası (15 Ağu 2026):** *"`qwen3.5` Alibaba'nın
numaralandırmasında doğrulanabilir bir sürüm değil (Qwen, 1.5, 2, 2.5, 3)…
adın yukarı akış (upstream) karşılığını doğrulayamıyoruz."* Gerekçe olarak
*"yukarı akış model kartını indirip karşılaştırmak ağ ister; bu doğrulama
yapılmadı"* yazılmıştı.

**`model-license-audit.md` §1'in iddiası:** aile **gerçek**, Qwen'in kendi
HuggingFace hesabı altında yayımlı, zincirin kökü `Qwen/Qwen3.5-9B-Base`
ve tamamı Apache-2.0.

**ÇÖZÜM: §1 doğru, bu belgenin şüphesi geçersiz.** Yukarı akış 23 Ağu
2026'da HuggingFace API'sinden canlı doğrulandı:

| Alan | `Qwen/Qwen3.5-9B` | `Qwen/Qwen3.5-9B-Base` |
|---|---|---|
| `author` | `Qwen` (resmî hesap) | `Qwen` (resmî hesap) |
| `license` | `apache-2.0` | `apache-2.0` |
| `base_model` | `Qwen/Qwen3.5-9B-Base` | **yok** (zincirin kökü) |
| `createdAt` | 2026-02-27 | 2026-02-26 |
| indirme | 13.785.751 | 425.740 |

```bash
curl -s https://huggingface.co/api/models/Qwen/Qwen3.5-9B     | python3 -m json.tool
curl -s https://huggingface.co/api/models/Qwen/Qwen3.5-9B-Base | python3 -m json.tool
```

**Şüphe niçin doğmuş:** dayanak olarak yazılan sürüm listesi
(*"Qwen, 1.5, 2, 2.5, 3"*) Qwen3.5 **yayımlanmadan önceki** durumu
anlatıyor. Aile Şubat 2026'da çıktı; liste güncellenmeyince var olan bir
model "doğrulanamaz" göründü. Yani hata veri değil, **bayat bir referans
listesiydi** — ve tam olarak bu yüzden "doğrulanamadı" ile "yok" arasındaki
ayrım korunmalı: birincisi bir bilgi eksiği, ikincisi bir olgu iddiasıdır.
Bu belge birincisini yazmıştı, doğru davranış buydu; eksik olan şey ağ
erişimi gerektiren adımın sonradan da koşulmamasıydı.

**Ne değişmedi:** modelin rolü. `qwen3.5:9b-q4_K_M` teslim edilen üretim
yolunda **kullanılmıyor** — `--llm` varsayılanı `kapali`, model yalnız
düşünme kipi ölçümünde ikame olarak koştu
(`docs/rapor/llm-uretim-devreye-alma.md`) ve **ölçüm onu reddetti**: 9B
kolu kabul kapısından geçemedi. Lisans temiz olduğu için bu bir engel
değildi; rol bilgisi yine de burada duruyor çünkü "hangi model teslimde
var" sorusu lisanstan ayrı bir sorudur.

**Kalan sınır:** yukarıdaki tablo HuggingFace'in beyanına dayanır. Ollama
etiketi ile HF deposu arasındaki bağ künye örtüşmesiyle kuruldu
(`model-license-audit.md` §1: mimari `qwen35`, 9.65B, Q4_K_M, 262.144
bağlam — üçü de örtüşüyor), bayt düzeyinde ağırlık karşılaştırmasıyla
değil. Bu ayrım korunuyor.
