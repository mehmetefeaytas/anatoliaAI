# Karar bekleyenler

Bu dosya, **kullanıcının vermesi gereken** kararları tutar. Teknik olarak
çözülmüş ama ürün/strateji tarafı açık olan işler buraya yazılır.

Her madde soğuktan okunabilir olmalı: karar neydi, seçenekler ne, hangi sayı
neyi söylüyor, seçmemenin bedeli ne.

Son güncelleme: 2026-08-07 · HEAD `fcb3c61`

---

## K-1 · Çerçeve ayıklaması: n-gram mı, blok mu, hiçbiri mi?

**Durum:** ikisi de kodlandı ve ölçüldü, hiçbiri uygulanmadı.
**Nerede:** `src/preprocessing/blocks.py` (blok), `scripts/split_trainable.py`
(n-gram), ölçümler `docs/rapor/boilerplate-kapsam.md`.

Ölçüm (kural/strict, `products` kapsamı, gold n=20):

| yapılandırma | mikro-F1 | halüsinasyon | kaçırma |
|---|---|---|---|
| temel (ayıklama yok) | 0,677 | 0,096 | **13** |
| **n-gram** | **0,688** | **0,066** | 16 |
| **blok** (üç sinyal) | 0,687 | 0,090 | **14** |

**Hiçbiri baskın değil.** İki sınır noktası:

- *daha az uydurma* isteniyorsa → **n-gram** (halüsinasyon 0,066, 3 gerçek
  alan kaybı)
- *daha çok kapsama* isteniyorsa → **blok** (kaçırma 14, halüsinasyon 0,090)

F1 farkı (0,688 vs 0,687) istatistiksel olarak yok.

**Uyarı:** n=20'de bu farklar küçük sayılara dayanıyor — halüsinasyonda **5
kayıt**, kaçırmada **2 alan**. Gold büyümeden verilen karar kırılgan olur.

**Seçmemenin bedeli:** bugünkü hâl (ayıklama yok) her iki metrikte de
ikisinden kötü; korpusun %40'ı gürültü olarak LLM'e gidiyor ve çerez/KVKK
metninden `vade_ay="1 yıl"`, `masraf_durumu="ücretsiz"` uyduruluyor.

**Kapsam kısıtı (bu kısım kararlı):** yalnız `products`. Ayrım gözetmeden
uygulanınca F1 0,562'ye çakılıyor, çünkü `docs` altındaki sözleşme
şablonlarında tekrar gürültü değil içeriğin kendisidir.

---

## K-2 · `DEFAULT_CONFIG` hâlâ `hibrit` — ölçümle çelişiyor

**Durum:** `eval/predictors.py:67` → `DEFAULT_CONFIG = CONFIG_HIBRIT`.
Bilinçli olarak değiştirilmedi; teslim edilen sistemin hangi kol olduğu
ürün kararıdır.

| kol | mikro-F1 | halüsinasyon |
|---|---|---|
| **kural** | **0,677** | **0,096** |
| orkestra | 0,672 | 0,114 |
| hibrit | **0,575** | **0,163** |

Fark artık küçük değil: hibrit kuraldan **0,10 F1 geride** ve halüsinasyonu
**%70 daha yüksek**. Dashboard ve API `reconcile()` çağırıyor, yani
kullanıcıya giden yol bu.

**Not:** `hibrit` LLM gerektiriyor; LLM kapalıyken zaten kural gibi davranıyor.
Yani karar pratikte "LLM açıkken hangi kol koşsun".

---

## K-3 · 71 commit push edilmedi

**Durum:** yerel dal `veri-toplama-genislemesi`, `origin/main`'in 71 commit
önünde. Yayınlanmış dallar `yayin/hafta-02` ve `yayin/hafta-03`.

Şartname §20 **haftalık commit** istiyor; §9 jürinin GitHub'a yüklenen projeyi
değerlendirdiğini söylüyor. Yani gecikme kalıcı olamaz.

**Push edilmemesi gereken (yayın kademesi 3):**
- `docs/rapor/rakip-analizi.md` — `.gitignore`'da, korunuyor
- `docs/rapor/yapilacaklar-envanteri.md` — kendi zayıflık listemiz
- `docs/rapor/banka-siteleri-veri-kaynagi-haritasi.md` — keşif haritası

**DİKKAT:** son ikisi `0fcab79` commit'inde **zaten depo geçmişine girdi**.
Dalı olduğu gibi push etmek onları da yayına sokar. Geçmişten çıkarmak
`git filter-repo` ister ve bu geri alınamaz bir geçmiş yazma işlemidir.
Karar senin.

---

## K-4 · Prompt-injection: LLM modunda ölçülmedi

**Durum:** 22/22 savuşturma **kapı modunda** (LLM kapalı) ölçüldü. RAG sentezi
devre dışıyken modelin ikna edilip edilemediği ÖLÇÜLMEDİ.

`LLM_BACKEND=ollama python -m scripts.eval_injection` ile koşulabilir; ~10 dk.
Sunumda "%100" bu kısıt söylenmeden telaffuz edilmemeli.

Karar: koşalım mı, yoksa kapı modu sayısıyla mı yetinelim?

---

## Kapanmış kararlar (kayıt için)

- **K3-orkestrasyon:** orkestrasyon kural kolunu geçemedi (0,672 vs 0,677),
  `DEFAULT_CONFIG` kural olarak kalması gerektiği ölçümle sabitlendi.
  Ayrıntı: `docs/rapor/ablasyon.md` eki.
- **Terim sözlüğü:** enjeksiyon, replace değil.
  `decisions/terim-sozlugu-enjeksiyon-replace-degil.md`.
- **Orkestrasyon yetkisi:** ajanlar önerir, hakem reddeder.
  `decisions/orkestrasyon-yetki-asimetrisi.md`.
