# Sunum Taslağı — 4 Dakika + 1 Dakika Canlı Demo

İlgili: `docs/problem_statement.md`, `docs/positioning.md`,
`docs/resilience_narrative.md`, `docs/future_work.md`
Artefaktlar: `docs/rapor/gorseller/`, `docs/rapor/grafikler/`
Tarih: 2026-08-07

---

## Zaman bütçesi

| Bölüm | Süre | Konu |
|---|---|---|
| 1 | 0:00–1:00 | Problem + çözüm |
| 2 | 1:00–3:00 | Teknik mimari, veri toplama, model seçimi, kalibrasyon, metrikler |
| 3 | 3:00–4:00 | Çıktı, sektörel kullanım, avantajlar |
| 4 | 4:00–5:00 | Canlı demo |

**Toplam konuşulan sayı hedefi: en fazla 6.** Slayta sığdırılan her ek rakam,
akılda kalan rakam sayısını düşürür. Aşağıda **kalın** yazılanlar telaffuz
edilecek olanlardır; geri kalanı slaytta durur, soru gelirse söylenir.

---

## Bölüm 1 — Problem + çözüm (0:00–1:00)

**Gösterilecek artefakt:** `docs/rapor/gorseller/01-karsilastirma.png`
(kıyaslama ekranı — açılış görseli olarak, konuşma boyunca ekranda kalır).

**Konuşma notu:**

> Katılım bankacılığı ürünü arayan bir vatandaş bugün 10 bankanın sayfasını tek
> tek açmak zorunda. Sayfalar farklı düzende; oran bazen aylık bazen yıllık,
> bazen `%1,99–%2,49` gibi bir aralık, bazen "ilk 6 ay %0" gibi zamana bağlı.
>
> "Peki kıyaslama siteleri ne yapıyor?" — Onlar katılım ürünlerini
> kıyaslamıyor. Sukuk yok, kira sertifikası yok, katılma hesabı yok. Çünkü bu
> ürün ailesi konvansiyonel bir şemaya sığmıyor: kâr payı, konvansiyonel bir
> orana **eşit değildir**, altındaki akit farklıdır.
>
> Biz 10 katılım bankasının kampanyalarını otomatik topluyor, 12 alanı
> çıkarıyor, katılım terminolojisiyle normalize ediyor ve adil kıyas garantisiyle
> karşılaştırıyoruz. Adil kıyas: aynı ürün türü, aynı vade, aynı tutar bandı.

**Bu bölümde telaffuz edilecek sayı: yalnızca "10 banka".**

**Tuzak:** Buraya mimari sokmayın. İlk dakika problemin dakikasıdır.

---

## Bölüm 2 — Teknik mimari ve ölçüm (1:00–3:00)

Sunumun ağırlık merkezi. Dört alt başlık, her biri ~30 saniye.

### 2.1 Mimari (~30 sn)

**Artefakt:** `docs/rapor/grafikler/g01-mimari.svg`

**Konuşma notu:**

> Boru hattı: topla → temizle → çıkar → uzlaştır → normalize et → sakla →
> kıyasla → dashboard ve chatbot.
>
> Çıkarım üç katmanlı: deterministik kurallar birincil; GLiNER2 tamamlayıcı;
> yerel LLM yalnızca kuralların kaçırdığı örtük ifadeler için, kısıtlı JSON
> üretimiyle. Uzlaştırma şu sırayla çalışır: kural çıktısı varsa onu tercih et,
> boşlukları LLM ile doldur, her alana güven skoru ve **kaynak span'i** ekle.
> Alan gerçekten yoksa `null` döndürürüz — asla değer uydurmayız.

### 2.2 Veri toplama (~30 sn)

**Artefakt:** `docs/rapor/gorseller/02-karsilastirma-kaynak-span.png`
(her sayının kaynak cümlesinin vurgulandığı ekran).

**Konuşma notu:**

> Toplama config-driven: yeni bir banka eklemek **kod değişikliği değil**,
> `config/banks.yaml`'a bir yapılandırma bloğu eklemek demek.
>
> Etik taraf kodda: kendi robots.txt ayrıştırıcımız `Disallow`'a uyuyor,
> kimliğini beyan eden bir User-Agent kullanıyoruz, alan adı başına 3 saniye
> bekliyoruz. Her belge `source_url` + zaman damgası + sha256 ile izlenebilir.
>
> Bu ekrandaki her sayının altında hangi cümleden geldiği duruyor. Kıyaslama
> sitelerinin veremediği şey tam olarak bu.

**Telaffuz edilecek sayı: "849 belge, 10 banka".** (Ölçümlerin dayandığı,
veritabanına giren korpus. Ham toplam 2.485'tir; sorulursa söylenir, slaytta
durur.)

### 2.3 Model seçimi ve kalibrasyon (~25 sn)

**Artefakt:** `docs/rapor/grafikler/g06-katman-katkisi.svg`

**Konuşma notu:**

> Model seçiminde tek kısıt vardı: lisans zincirini köke kadar takip etmek.
> Trendyol-LLM-8B-T1 Apache-2.0 ve zinciri Qwen3-8B-Base'e kadar temiz.
> Llama türevlerini, Gemma'yı, TURNA'yı bu yüzden eledik. NuExtract'ın 8B'si
> MIT, 4B'si araştırma lisanslı — aynı ailenin iki sürümü farklı lisansta, bu
> yüzden zinciri takip etmek bir prensip.
>
> Kalibrasyon tarafında: her alan bir güven skoru taşıyor ve düşük güvenli alan
> kullanıcıya işaretli gösteriliyor.

> **TODO: ölçülecek** — ECE / reliability diagram henüz üretilmedi. Bu cümle
> "kalibrasyon ölçüldü" demiyor, "güven skoru taşınıyor" diyor. Sunumda ECE
> sayısı verilmeyecek.

### 2.4 Metrikler — sunumun en güçlü 35 saniyesi

**Artefakt:** `docs/rapor/grafikler/g09-guvenlik-ablasyon.svg` +
ablasyon tablosu slaytı.

**Konuşma notu:**

> Şimdi kendi hipotezimizi yanlışladığımız yere geliyorum.
>
> Ablasyon kurduk: 20 belgelik gold set, 12 alan, 1000 örneklemli bootstrap,
> belge düzeyinde. Beklentimiz, LLM eklemenin doğruluğu artırmasıydı.
>
> **Artmadı.** Kural katmanı mikro-F1 **0,612**. Hibrit **0,575**. Saf LLM
> 0,169. McNemar testi p = 0,0117 — fark anlamlı, kazanan kural.
>
> Daha önemlisi halüsinasyon: kuralda **0,102**, hibritte **0,163** — yani LLM
> eklemek uydurma oranını %60 artırdı.
>
> Bu sonucu değiştirmedik. Negatif sonuç olarak yazdık. Ve bu, sunacağım en
> güçlü argümanın kanıtı.

**Tuzak — çok önemli:** Bu bölümde **prompt-injection sayısı verilmeyecek**.
Set kurulu (26 vaka: 22 saldırı + 4 kontrol) ama koşulmadı. Aynı şekilde
**toplam test sayısı telaffuz edilmeyecek** — belgeler arasında tutarsız
(345 ile 1.359 arası). Soru gelirse: *"O ölçüm henüz koşulmadı"* denir.

---

## Bölüm 3 — Çıktı, sektörel kullanım, avantajlar (3:00–4:00)

### 3.1 Dayanıklılık anlatısı (~25 sn)

**Artefakt:** `docs/rapor/grafikler/g02-gecikme.svg`

**Konuşma notu:**

> O ablasyon sonucu bize bir ürün özelliği kazandırdı.
>
> Bir banka LLM'i acilen kapatmak isterse — düzenleyici bir soru, bir güvenlik
> bulgusu, bir sağlayıcı sözleşmesi — bizde bu düğme var. Ve bastığınızda
> **doğruluk kaybı sıfır**, çünkü kural kolu zaten en iyi kol.
>
> Model yükseltmesinden sonra halüsinasyon görürse: sayısal alanlar model
> sürümünden bağımsız, aynı girdi aynı çıktı.
>
> Altyapı kesintisinde: kural kolu belge başına **1 milisaniye**, tepe bellek
> 100 MB. Felaket senaryosunda ayakta kalması gereken şey bir GPU kümesi değil.
>
> Yani kural katmanı bizim eksik teknolojimiz değil; **ölçtüğümüzde en iyi
> çıkan kol** ve bankacılıkta bir uyum özelliği.

### 3.2 İki hedef kitle (~25 sn)

**Artefakt:** `docs/rapor/grafikler/g12-yol-haritasi.svg`

**Konuşma notu:**

> İki kullanım var. Birincisi vatandaşa dönük kıyaslama aracı.
>
> İkincisi — ve mentörlerimizin işaret ettiği asıl fırsat — bankanın satın alıp
> kendi mobil uygulamasına gömdüğü bir modül. Banka müşterisine "piyasadaki tüm
> katılım ürünlerini karşılaştır" diyor ve karşılaştırma sonucunda **kendi
> üstünlüğünü kanıtla** gösteriyor. Müşteri kıyas için uygulamadan çıkmıyor.
>
> On-prem tercihimiz asıl anlamını burada kazanıyor. Açıkça söyleyeyim: sadece
> herkese açık veri kazıyorsanız lokal host'un güçlü bir gerekçesi yok — bu
> eleştiri haklı. Ama sistem bankanın **içine** girdiğinde işlediği veri artık
> kamuya açık değil: bankanın fiyat politikası, müşteri segmenti, sorgu
> davranışı. Üstelik BDDK satın alınan ürünün Türkiye'de barındırılmasını
> zorunlu kılıyor. Yani on-prem bir tercih değil, satın alınabilirliğin ön
> koşulu.

### 3.3 Ayrıştığımız nokta (~10 sn) — kapanış cümlesi

> Bu mimariyi savunan tek ekip biz değiliz. Ama onu güven aralığıyla ölçen ve
> **kendi hipotezini yanlışlayan sonucu yayımlayan** ekibiz.

---

## Bölüm 4 — Canlı demo (4:00–5:00)

Üç adım, her biri ~20 saniye. Prova edilmiş, sabit girdilerle.

**Adım 1 — Kıyaslama + kaynak span (20 sn).**
Ekran: canlı dashboard (yedek: `gorseller/01-karsilastirma.png`,
`02-karsilastirma-kaynak-span.png`).
Bir konut finansmanı kıyası açılır, bir orana tıklanır, kaynak cümle vurgulanır.
> *"Bu sayı buradan geldi."*

**Adım 2 — Zor vaka canlı çıkarım (20 sn).**
Ekran: canlı çıkarım (yedek: `gorseller/05-canli-cikarim-zor-vaka.png`).
"İlk 6 ay %0" veya `%1,99–%2,49` içeren bir metin yapıştırılır.
> *"Aralık ve zaman-koşullu oran — normalizasyonun asıl zor kısmı burası."*

**Adım 3 — Chatbot + güvenlik kapısı (20 sn).**
Ekran: chatbot (yedek: `gorseller/07-chatbot-yapisal-sorgu.png`,
`09-guvenlik-kapi1-terminoloji.png`).
Önce yapısal bir soru sorulur (en düşük kâr payı → text-to-SQL yolu). Ardından
konvansiyonel terimle bir soru sorulur ve terminoloji kapısının düzelttiği
gösterilir.
> *"Router soruyu yapısal sorguya gönderdi. Ve çıkışta terminoloji kapısı var —
> 1.696 belgelik korpus stresinde nihai yanıtlarda kalan konvansiyonel terim
> sıfır."*

**Demo güvenliği:** Üç adımın da ekran görüntüsü yedeği hazır bulundurulur.
Sistem `--network none` altında çalıştığı için ağ kaynaklı bir arıza riski yok;
asıl risk sunum makinesidir.

---

## Soru-cevap için hazırlık

| Soru | Cevap |
|---|---|
| "Kaç bankayla entegresiniz?" | **Hiçbiriyle.** Kamuya açık sayfalardan topluyoruz. Gerçek ürün banka API'lerini tüketmeli — bu future work, ve henüz yazılmadı. |
| "Gold setiniz neden bu kadar küçük?" | 20 belge. Güven aralıkları geniş ve bunu raporda yazıyoruz. Büyütmek yol haritasında. |
| "Prompt injection'a karşı ne yaptınız?" | 26 vakalık set kurulu, kapı ve regresyon testleri kodda. **Değerlendirme henüz koşulmadı**, sayı vermiyoruz. |
| "Kazıma yasal mı?" | Yarışma kapsamında evet: kamuya açık veri, robots.txt uyumu, kimlik beyanı, tam izlenebilirlik. Ticari senaryoda kapatılması gereken kalemleri `docs/legal_notes.md`'de listeledik. |
| "Neden LLM'i daha çok kullanmıyorsunuz?" | Ölçtük, daha kötü çıktı. Mikro-F1 0,612 → 0,575, halüsinasyon 0,102 → 0,163. |
| "Kalibrasyon sayınız var mı?" | Güven skoru taşıyoruz, **ECE henüz ölçülmedi**. |

---

## Kaynaklar

- `docs/problem_statement.md` — Bölüm 1
- `docs/rapor/ablasyon.md` — Bölüm 2.4
- `docs/resilience_narrative.md` — Bölüm 3.1
- `docs/positioning.md` — Bölüm 3.2
- `docs/future_work.md` — soru-cevap, API bankacılığı
- `docs/rapor/gorseller/`, `docs/rapor/grafikler/` — artefaktlar
