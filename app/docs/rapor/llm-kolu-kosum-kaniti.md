# LLM kolu koşturuldu — ölçülmüş kanıt

**Tarih:** 2026-08-19
**Ortam:** macOS (Darwin 25.5.0), **GPU YOK**, CPU çıkarım
**Arka uç:** Ollama yerel servis (`http://localhost:11434`)
**Model:** `qwen2.5:7b-instruct` (Q4_K_M, 4,7 GB) — Ollama kolunun üretim
varsayılanı (`src/extraction/llm/clients.py:437`)
**Lisans:** **Apache-2.0**, taban zinciri `Qwen/Qwen2.5-7B` (kök, sıfırdan
eğitim) — 15 Ağu 2026'da denetlendi, `docs/model-license-audit.md` §1

---

## Neden bu belge var

`docs/OFFLINE-KANIT.md` şunu yazıyordu ve o gün için doğruydu:

> LLM arka ucu | **kapalı** (`LLM_BACKEND=""` → `NullLLMExtractor`)
> ⚠️ GPU yok … vLLM / Trendyol-LLM-8B-T1 kolu **hiç koşturulmadı**

Değerlendirmede bu, On-Prem kriterinin birinci maddesi olarak işaretlendi:
sistem `NullLLMExtractor` ile teslim ediliyor, yani mimarinin ikinci katmanı
kâğıt üzerinde kalıyor. Bu belge o boşluğun **bir kısmını** kapatır ve hangi
kısmını kapatmadığını da açıkça söyler.

**AYRIM ÖNEMLİ:** OFFLINE-KANIT.md'nin cümlesi *vLLM / Trendyol-LLM-8B-T1*
kolu içindir ve **hâlâ geçerlidir** — o kol GPU ister ve bu makinede GPU yok.
Burada koşturulan **Ollama kolu**dur; `docker-compose`'da yedek olarak
tanımlı, CPU'da çalışabilen yol.

## Ne ölçüldü

Katı mod açık koşuldu (`LLM_STRICT=1`). Bu kritik: hoşgörülü modda arka uç
kurulamazsa kod sessizce `NullLLMExtractor`'a düşer ve "LLM koştu" sanılır.
Katı modda kurulamazsa exception yükselir, yani aşağıdaki çıktı LLM'in
gerçekten devrede olduğunun kanıtıdır.

```
LLM_BACKEND=ollama LLM_STRICT=1 python -c "…default_extractor()…"

extractor: LLMExtractor | available: True
süre: 12.8s
   kar_payi_orani = 2.19            | present: True
   vade_ay        = 36              | present: True
   masraf_durumu  = {'has_fee': False, 'amount': 0} | present: True
```

Girdi metni:

> "Kampanya kapsamında 36 ay vadeli konut finansmanında aylık kâr payı oranı
> %2,19 olarak uygulanır. Dosya masrafı alınmaz."

**Üç alanın üçü de doğru.** `masraf_durumu` özellikle anlamlı: "alınmaz"
negasyonu yokluk DEĞİL, sıfır ücret olarak çözülmüş — CLAUDE.md §6'nın
"masrafsız ≠ değer yok" kuralı LLM kolunda da tutuyor.

Üretim hızı Ollama sunucu günlüğünden: **~8,2 token/s** (CPU, tek slot).

## Bu ne kanıtlar, ne kanıtlamaz

**Kanıtlar:**
- Ollama kolu erişilebilir ve şema-uyumlu çıktı üretiyor; `available: True`.
- Model ağırlıkları yerelde, çağrı `localhost`a gidiyor — harici servis yok,
  ücretli API yok (şartname §5.10).
- "Sistem yalnız `NullLLMExtractor` ile çalışabiliyor" ifadesi artık doğru
  değil.

**Kanıtlamaz:**
- **Hibrit F1'i.** Ablasyon koşumu bu turda tamamlanmadı: CPU'da 8,2 token/s
  ile belge başına ~60 saniye, 48 belgelik gold.v2 için ~48 dakika. Koşum
  başlatıldı ama bu belgenin yazıldığı anda bitmemişti.
- **vLLM / Trendyol kolu.** GPU gerektiriyor, bu makinede yok. O satır
  OFFLINE-KANIT.md'de olduğu gibi kalıyor.
- **Tek örneklem yeterli değildir.** Yukarıdaki üç alan bir doğrulama, bir
  metrik değil. Metrik ancak tamamlanan ablasyondan gelir.

## Açık iş — ablasyonun anlamı bu turda değişti

5 Ağustos'taki ablasyon (`docs/rapor/ablasyon.md`) hibridin kural katmanını
geçemediğini ölçmüştü (0,575 < 0,612, McNemar p = 0,0117). Ama o rapor kendi
sınırını da yazıyor:

> Hibrit özellikle ZOR vakalarda kazanır → ❌ Ölçülemedi — gold'da yalnız
> **1** zor belge var

O gün gold'da 1 zor belge vardı. Bugün `gold.v2`'de **40 zor belge** var.
Yani hibrit-kural karşılaştırması ilk kez zor vaka alt kümesinde anlamlı
ölçülebilir durumda ve tamamlandığında sonuç iki yönde de bilgi verir:

- hibrit zor vakalarda kazanırsa, mimarinin ikinci katmanı gerekçelenir;
- kazanmazsa, 5 Ağustos'taki çürütme **güncel ve daha güçlü** bir zeminde
  tekrarlanmış olur.

İkisi de yayımlanabilir. Ölçülmeden hangisi olduğu yazılmayacak.

## Tekrar üretme

```bash
cd app
ollama serve &                        # yerel servis
LLM_BACKEND=ollama LLM_STRICT=1 \
  .venv/bin/python -m eval.run_eval --gold data/gold/gold.v2.json \
                                    --config hibrit --no-bootstrap
```

`LLM_STRICT=1` bırakılmalı: onsuz arka uç kurulamazsa koşum sessizce
kural-only'ye düşer ve tablo yanlış etiketle yayımlanır.
