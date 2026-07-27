# Model ve Bağımlılık Lisans Denetimi

**Durum:** taslak — açık doğrulama kalemleri var (aşağıda `⏳` ile işaretli)
**Son güncelleme:** 2026-07-27
**Sorumlu kalem:** Şartname §5.10 ve §8

---

## Neden bu belge var

Şartname §5.10 birebir şunu söylüyor:

> Çalışmada geliştirilecek tüm kodlar **açık kaynak kod tabanlı teknolojiler**
> kullanılarak geliştirilmelidir. **Açık kaynaklı gözüküp, uygulama aşamasında
> lisans problemi çıkarma potansiyeli olan çözümler kullanılmamalıdır.**

§8 ise ücretli yazılım ve üçüncü taraf hizmet kullanımını yasaklıyor, ve
yarışma bitiminde tüm bileşenlerin **Apache-2.0** ile Türkiye Açık Kaynak
Platformu hesabında paylaşılacağını şart koşuyor.

"Açık kaynaklı gözüküp lisans problemi çıkarma potansiyeli" ifadesi doğrudan
**Llama Community License** ve **Gemma Terms of Use** gibi, açık kaynak
sanılan ama kullanım kısıtı içeren model lisanslarını tarif ediyor. Bu belge,
projedeki her model ve ağır bağımlılık için lisans zincirini kayıt altına alır.

**Kural:** Bu tabloda `✅` olmayan hiçbir bileşen teslim edilen sisteme
giremez.

---

## 1. Modeller

| Bileşen | Rol | İddia edilen lisans | Durum | Not |
|---|---|---|---|---|
| **Qwen3-8B** | Çıkarım LLM'i (Colab/deney) | Apache-2.0 | ⏳ | Model kartı + `LICENSE` dosyası indirilip SHA-256'sı buraya yazılacak |
| **Qwen3-4B** | Çıkarım LLM'i (demo, CPU/GGUF) | Apache-2.0 | ⏳ | Aynı denetim |
| **Trendyol-LLM-8B-T1** | Ablasyon kolu (opsiyonel) | Apache-2.0 (iddia) | ⛔ **BLOKE** | **Taban model zinciri doğrulanmadan kullanılamaz.** Trendyol hem Llama hem Qwen tabanlı modeller yayımladı. Taban Llama-3.x ise Llama Community License devreye girer → §5.10 ihlali. |
| **BERTurk** (`dbmdz/bert-base-turkish-cased`) | 8-sınıf sınıflandırıcı | MIT | ⏳ | Model kartından teyit |
| **TabiBERT** | Sınıflandırıcı alternatifi | bilinmiyor | ⏳ | Lisans doğrulanmadan gündeme alınmaz |
| **bge-m3** (`BAAI/bge-m3`) | Embedding | MIT | ⏳ | Model kartından teyit |

### ⛔ Kullanılmayacaklar (karar verilmiş)

| Model ailesi | Sebep |
|---|---|
| Llama 3.x / 3.3 (tüm türevleri) | Llama Community License — kullanım kısıtı içerir, Apache-2.0'a dönüştürülemez |
| Gemma 2 / 3, EmbeddingGemma, WiroAI-9b | Gemma Terms of Use — aynı sorun |

`app/CLAUDE.md` §7 bu kararı zaten kayıt altına almış; bu belge onun kanıt katmanıdır.

### Doğrulama prosedürü (her model için)

```bash
# 1. Model kartını ve LICENSE dosyasını indir
huggingface-cli download <repo_id> LICENSE README.md --local-dir /tmp/lic/<ad>

# 2. SHA-256 al ve bu belgeye yaz
shasum -a 256 /tmp/lic/<ad>/LICENSE

# 3. Model kartındaki `base_model:` alanını takip et — zincirin KÖKÜNE kadar.
#    Kök Llama/Gemma ise model reddedilir.
```

---

## 2. Python bağımlılıkları

Kaynak: `app/requirements.txt`, `app/requirements-api.txt`

| Paket | Lisans | Durum | Not |
|---|---|---|---|
| pydantic | MIT | ✅ | |
| fastapi | MIT | ✅ | |
| uvicorn | BSD | ✅ | |
| requests | Apache-2.0 | ✅ | |
| beautifulsoup4 | MIT | ✅ | |
| playwright | Apache-2.0 | ✅ | |
| transformers | Apache-2.0 | ✅ | |
| sentence-transformers | Apache-2.0 | ✅ | |
| gliner | Apache-2.0 | ✅ | Şu an **kodda hiç kullanılmıyor** — bkz. §4 |
| zeyrek | MIT | ✅ | Şu an **kodda hiç kullanılmıyor** — bkz. §4 |
| ruff / black / pytest | MIT | ✅ | Yalnızca geliştirme |
| psycopg[binary] | LGPL | ✅ | Dinamik bağlı istemci kütüphanesi; Apache-2.0 uygulama ile birlikte dağıtımı sorun değil |
| pgvector (Python) | PostgreSQL lisansı | ✅ | İzin verici |
| **trafilatura** | **⚠️ belirsiz** | ⏳ **AÇIK RİSK** | Aşağıya bakınız |

### ⏳ trafilatura — açık risk kalemi

`requirements.txt` kendi yorumunda `# GPLv3+` yazıyor. GPLv3, Apache-2.0 ile
birlikte dağıtımda **uyumsuzluk yaratır** ve şartnamenin "yarışma bitiminde
Apache-2.0 ile paylaşılacak" şartıyla çelişir.

Bilinen: trafilatura projesi bir sürümde Apache-2.0'a geçti ve `requirements.txt`
pinlemesi (`>=1.8`) muhtemelen o eşiğin üstünde. **Ancak bu doğrulanmadı** —
bu ortamda paket kurulu değil ve ağ erişimiyle teyit edilmedi.

**Risk neden düşük:** trafilatura kodda **opsiyonel**. `src/scraping/collector.py`
içindeki `_extract_main_text`, paket yoksa `src/preprocessing/clean.py`'deki
saf stdlib `strip_html`'e düşüyor. Yani sistem trafilatura olmadan da çalışıyor.

**Karar (Gün 1):** doğrulanana kadar `requirements.txt`'te **opsiyonel** olarak
işaretlendi ve `requirements-api.txt`'e (teslim edilen imaj) **alınmadı**.

**Yapılacak:**
```bash
pip download trafilatura==<pin> --no-deps -d /tmp/tf && \
  python -c "import importlib.metadata as m; print(m.metadata('trafilatura')['License'])"
# Apache-2.0 değilse: readability-lxml (Apache-2.0) ile değiştir veya
# tamamen çıkar (strip_html fallback zaten yeterli).
```

---

## 3. Frontend ve araçlar

| Bileşen | Lisans | Durum |
|---|---|---|
| Next.js 14 | MIT | ✅ |
| React 18 | MIT | ✅ |
| TypeScript | Apache-2.0 | ✅ |
| Recharts (planlanan) | MIT | ⏳ eklenirse teyit |
| LibreOffice Impress (sunum) | MPL-2.0 | ✅ ücretsiz, §8 uyumlu |
| OBS Studio (video) | GPL-2.0 | ✅ araç, teslim edilen ürünün parçası değil |
| Shotcut / Kdenlive (kurgu) | GPL | ✅ aynı gerekçe |

**Not:** GPL lisanslı *araçlar* (OBS, Kdenlive) sorun değildir — bunlar teslim
edilen yazılımın parçası değil, onu üretmekte kullanılan editörlerdir. Sorun
yaratan, GPL kodun teslim edilen ürüne **linklenmesi**dir (trafilatura vakası).

---

## 4. Kullanılmayan bağımlılıklar (temizlik borcu)

Aşağıdakiler `requirements.txt`'te ilan edilmiş ama kod tabanında **sıfır
referansı** var. Şartname §9 "bağımlılıkların eksiksiz listesi" istiyor —
kullanılmayan bağımlılık ilan etmek bu listeyi yanıltıcı yapar.

| Paket | Durum | Karar |
|---|---|---|
| `gliner` | Kodda hiç geçmiyor (3 katmanlı mimarinin "tamamlayıcı NER" katmanı yok) | Kullanılacaksa uygulanmalı, kullanılmayacaksa listeden çıkarılmalı |
| `zeyrek` | Kodda hiç geçmiyor (TR morfoloji katmanı yok) | Aynı |
| `sentence-transformers` | Yalnızca yorumlarda | İH5'te gerçek `VectorRetriever` ile kullanılacak |
| `psycopg` / `pgvector` | Yalnızca yorumlarda; `repository.py` SQLite-only | İH5'te gerçekten devreye alınacak |

---

## 5. Denetim kontrol listesi (her teslim öncesi)

- [ ] Tabloda `⏳` kalmadı
- [ ] Hiçbir model zinciri Llama/Gemma köküne çıkmıyor
- [ ] `requirements.txt` = kodda gerçekten kullanılan paketler
- [ ] Teslim imajında GPL linklenmiş kod yok
- [ ] Kök `LICENSE` = Apache-2.0
- [ ] Veri seti lisansı belirtilmiş (CC-BY-4.0)

---

## Sources

- `raw/teknofest/2026-teknofest-tyda-sartname-2-senaryo.pdf` — §5.10, §8
- `../../decisions/apache-2-acik-kaynak-lisansi.md`
- `app/CLAUDE.md` §7 (lisans tuzağı), §20 (uyumluluk kontrol listesi)

## Related

- [[apache-2-acik-kaynak-lisansi]] — kararın kendisi
- [[on-premise-calistirilabilir-mimari]] — offline kısıtı, model seçimini daraltır
- [[acik-kaynak-yaklasimi]]
