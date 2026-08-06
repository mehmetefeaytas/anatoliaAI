# Dayanıklılık Anlatısı — Kural Katmanı Neden "Eksik Teknoloji" Değil

İlgili: `CLAUDE.md` §3 (mimari), `docs/positioning.md`
Kod: `src/extraction/rules/`, `src/chatbot/safety.py`
Ölçüm: `docs/rapor/ablasyon.md`, `docs/rapor/olcumler.md`
Tarih: 2026-08-07

---

## 1. Savunulan iddia

Sistemin deterministik kural katmanı, LLM'e ulaşılamadığında devreye giren bir
**geri düşüş (fallback) değildir**. Ölçülmüş olarak **en iyi koldur** ve
bankacılık bağlamında bir **dayanıklılık ve uyum (compliance) özelliğidir**.

Bu, mimarimizin en çok yanlış anlaşılan tarafıdır. "Neden LLM'i daha çok
kullanmıyorsunuz" sorusunun cevabı "yapamadık" değil, "ölçtük ve daha kötü
çıktı"dır.

---

## 2. Ölçüm — hipotezimizi kendimiz yanlışladık

Ablasyon: gold n = **20 belge**, **12 alan**, **1000 örneklemli** bootstrap,
**belge düzeyinde**, seed 42. Ölçüm tarihi 2026-08-05.

| Kol | mikro-F1 | %95 GA | halüsinasyon |
|---|---:|---|---:|
| **kural** | **0,612** | [0,483–0,716] | **0,102** |
| hibrit | 0,575 | [0,443–0,688] | 0,163 |
| hibrit-verify | 0,562 | [0,426–0,675] | 0,163 |
| saf LLM | 0,169 | [0,095–0,242] | 0,145 |

**McNemar p = 0,0117 — kazanan `kural`.**

Üç sonuç birden okunmalı:

1. **LLM eklemek doğruluğu artırmadı.** Hibrit (0,575) kuraldan (0,612) düşük
   çıktı ve fark istatistiksel olarak anlamlı.
2. **LLM eklemek halüsinasyonu artırdı.** Hibritte 0,163, kuralda 0,102 —
   yani kural katmanının **%60 üstü**. Bankacılıkta uydurulmuş bir kâr payı
   oranı, kaçırılmış bir orandan çok daha pahalıdır.
3. **Bir doğrulama katmanı da kurtarmadı.** `hibrit-verify` kolu 0,562 ile daha
   da düştü; halüsinasyon aynı kaldı (0,163).

Beklentimiz bunun tersiydi. `docs/rapor/ablasyon.md` sonucu açıkça
"kanıtlanmadı, tersi ölçüldü" diye kaydediyor. Bu belge o kaydı gizlemiyor —
tam tersine, **anlatının en güçlü kanıtı odur**.

Buna bağlı bir olgu: korpustaki **2.204** çıkarılmış alanın **%100'ü** kural
katmanından geldi (`ner` 0, `llm` 0). Yani bugün çalışan sistem fiilen
deterministiktir ve bu bir kaza değil, ölçümün doğrudan sonucudur.

---

## 3. Bankanın gerçekten sorduğu üç soru

Cavide Hanım'ı ikna eden anlatı, üç operasyonel senaryo üzerinden kuruldu.
Üçünde de soru aynıdır: **LLM olmadığında sistem ne yapar?**

### (a) "LLM'i acilen kapatmam gerekirse?"

Bir bankanın modeli aniden devre dışı bırakması istisna değil, prosedürdür:
düzenleyici bir soru, bir güvenlik bulgusu, bir sağlayıcı sözleşmesi. Bu düğme
her kurumsal yapıda bulunmak zorundadır.

Bizim sistemimizde bu düğme **zaten var ve etkisi ölçülü**: `LLM_BACKEND`
boşken çıkarım `NullLLMExtractor`'a düşer ve sistem kural katmanıyla çalışmaya
devam eder. Kaybedilen doğruluk **sıfırdır** — çünkü kural kolu zaten en iyi
koldur (§2). Çoğu sistemde bu düğmeye basmak ürünü öldürür; bizde ölçülmüş
olarak **iyileştirir**.

### (b) "Model yükseltmesinden sonra halüsinasyon görürsem?"

Model sürümü değiştiğinde davranış değişir; bu, üzerine ürün kurulan her LLM
için geçerlidir. Kural katmanı bu riski taşımaz: aynı girdi, aynı çıktı, her
sürümde. Sayısal ve yapısal alanlar (kâr payı oranı, tutar, vade, taksit, tarih,
masraf) model sürümünden **bağımsızdır**.

Dahası, sistem hiçbir zaman değer uydurmaz: alan gerçekten yoksa `null` + düşük
güven döner. Her alan `confidence` ve `source_span` taşır — yani "bu sayıyı
nereden aldın" sorusunun cevabı kaynak metinde işaretlidir. Bir halüsinasyon
şüphesi denetlenebilir bir iddiaya dönüşür.

### (c) "Altyapı kesintisinde ne olur?"

GPU düğümü düşse, model sunucusu yanıt vermese bile temel yetenek ayakta kalır.
Ölçülmüş gecikme, kural kolunun ne kadar hafif olduğunu gösteriyor
(konteyner içi, 1.696 belge):

| Kol | p50 | p95 | p99 |
|---|---:|---:|---:|
| kural-only | **1,03 ms** | 4,80 ms | 6,30 ms |
| hibrit (LLM kapalı) | 1,50 ms | — | 8,86 ms |
| chatbot | 12,48 ms | 325,02 ms | — |

Verim **21.087 belge/dk**, tepe RSS **100,4 MB**, teslim imajı **96,5 MiB**.
Yani felaket senaryosunda çalışması gereken şey bir GPU kümesi değil, 100 MB'lık
bir süreç.

---

## 4. Uyum (compliance) tarafı — güvenlik katmanı ölçüldü

Dayanıklılık yalnızca "ayakta kalmak" değil, **yanlış şeyi söylememek**tir.
Chatbot çıkışındaki kural tabanlı güvenlik kapıları ölçüldü
(`docs/rapor/olcumler.md` §6, 30 vakalık katılım güvenlik seti):

| Koşu | Sonuç |
|---|---|
| Ana koşu | **30 / 30 = 1,00** |
| Ablasyon (5 kapı kapalı) | **0,20** |
| Aşırı red oranı | **0 / 6 = 0,00** |
| Korpus stresi (1.696 belge) | **27 / 30 = 0,90**, aşırı red 0/6 |

Kategori bazında (kapılar açık → kapalı): terminoloji 1,00 → 0,00; fıkhî hüküm
1,00 → 0,00; yatırım tavsiyesi 1,00 → 0,00; garanti iması 1,00 → 0,25;
çekimserlik/atıf 1,00 → 0,20. Kontrol grubu (aşırı red) **her iki hâlde 1,00**.

İki şey birden kanıtlanıyor:

- **Kapılar çalışıyor.** Kapatıldığında genel skor 1,00'dan 0,20'ye düşüyor —
  yani sonucu üreten şey modelin nezaketi değil, kuralın kendisi.
- **Kapılar aşırı reddetmiyor.** Kontrol grubu kapılar açıkken de kapalıyken de
  1,00. Meşru sorular reddedilmiyor. Bu, güvenlik katmanı eklerken en sık
  yapılan hatanın bizde ölçülerek dışlandığı anlamına gelir.

Korpus stresi ayrıntısı da anlatıya hizmet ediyor: 1.696 belgenin
**44'ünde (%2,6)** konvansiyonel terim geçiyor, toplam 62 geçiş var, post-filtre
5 tanesini yakalayıp düzeltiyor ve **nihai yanıtlarda kalan terim 0/30**.

---

## 5. Hataların anatomisi — neyi bilmediğimizi biliyoruz

Kural kolunda hata sınıfları ayrı paydalarla raporlanıyor
(`docs/rapor/devam-orkestrasyon.md`, Faz C1):

- **Çıkarım hatası 0,369 [24/65]** — bunun **13'ü kaçırma**, **11'i yanlış
  çıkarım**. Yani hataların neredeyse yarısı bir *grounding* meselesi: değer
  var, ama yanlış yerden alınmış.
- **Halüsinasyon 0,102** — kaynakta olmayan bir değer üretme oranı.

Bu ayrım kasıtlıdır. Bir alanı **kaçırmak** ile kaynakta olmayan bir değeri
**uydurmak** aynı ağırlıkta değildir; tek bir F1 sayısı bu farkı gizler.
Bankacılık bağlamında kaçırma bir eksikliktir, uydurma bir yükümlülüktür.
Kural katmanının halüsinasyonu düşük tutması (0,102 vs hibritte 0,163)
tam da bu yüzden dayanıklılık anlatısının merkezindedir.

---

## 6. Anlatının tek cümlesi

> Kural katmanı bizim LLM'e ulaşamadığımızda düştüğümüz yer değil; ölçtüğümüzde
> **en iyi çıkan kol**. Bankaya sattığımız şey bu yüzden bir model değil,
> modelin kapatılabilir olduğu bir mimari.

---

## 7. Açık kalan ölçüm

- **Prompt-injection değerlendirmesi koşulmadı.** Değerlendirme seti kurulu:
  `data/safety/prompt-injection-seti.jsonl` **26 vaka** — 22 saldırı
  (doğrudan talimat, rol değiştirme, sistem sızıntısı, terminoloji kaçırma,
  hüküm kaçırma, uydurma zorlama, dolaylı belge enjeksiyonu, kodlama kaçırma)
  + **4 kontrol** (aşırı red). Koşucu `scripts/eval_injection.py`, kapı
  `src/chatbot/safety.py` KAPI 6, regresyon testleri
  `tests/test_injection_guard.py`.
  **TODO: ölçülecek** — kaç saldırının savuşturulduğu hiçbir belgede yazılı
  değil. Sunumda bu konuda sayı verilmeyecek.
- **Toplam test sayısı için kanonik bir rakam yok.** Belgeler arasında 345
  (README rozeti, bayat) ile 1.359 (`devam-orkestrasyon.md`) arasında değişiyor.
  **TODO: ölçülecek** — tek bir sayım yöntemi belirlenip tüm belgeler
  hizalanmalı. Sunumda test sayısı telaffuz edilmeyecek.
- Ablasyon **n = 20** üzerinde koştu; güven aralıkları geniştir. Bu belge dar
  aralık iddia etmiyor.

---

## Kaynaklar

- `docs/rapor/ablasyon.md` §1 — ablasyon tablosu, McNemar
- `docs/rapor/olcumler.md` §6 — güvenlik katmanı, korpus stresi, gecikme
- `docs/rapor/devam-orkestrasyon.md` Faz C1 — hata sınıfları
- `docs/OFFLINE-KANIT.md` — `--network none` altında çalışma kanıtı
- `docs/positioning.md` §4 — on-prem gerekçesiyle bağlantı
