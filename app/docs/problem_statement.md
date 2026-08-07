# Problem Tanımı — Katılım Bankacılığında Kıyaslanamayan Ürünler

İlgili: `CLAUDE.md` §1 (proje özeti), §12 (domain bilgisi), §13 (hedef bankalar)
Kod: `config/banks.yaml`, `src/comparison/compare.py`
Tarih: 2026-08-07

---

## 1. Problem kimin?

Katılım bankacılığı ürünü arayan vatandaşın. Bu kişi konvansiyonel bankacılığı
**tercih etmiyor** — dolayısıyla piyasadaki kıyaslama araçlarının tamamı ona
yanlış ürünü, yanlış terimle gösteriyor.

Somut hâli şu: konut finansmanı arayan bir kullanıcı, Türkiye'deki 10 katılım
bankasının kampanya sayfalarını **tek tek** açmak zorunda. Her bankanın kâr payı
oranını, vadesini, tahsis ücretini, kampanya bitiş tarihini ayrı ayrı okuyup
kendi kafasında bir tablo kuruyor. Sayfalar farklı düzende, oranlar bazen aylık
bazen yıllık, bazen `%1,99–%2,49` gibi aralık, bazen "ilk 6 ay %0" gibi
zaman-koşullu. "Masrafsız" ifadesinin ücret alanının boş olduğu anlamına mı
yoksa ücretin sıfır olduğu anlamına mı geldiği bile ayrı bir yorum işi.

---

## 2. Kök neden

Kök neden bir yazılım eksikliği değil, **terminolojik bir kopukluk**.

Katılım bankacılığının ürün dili konvansiyonel bankacılıktan farklıdır: kâr payı,
finansman, katılma hesabı, murabaha, icara, mudarebe, muşareke, karz-ı hasen,
sukuk, kira sertifikası, tahsis ücreti, vade farkı. Bu terimlerin konvansiyonel
karşılıkları **birebir çevrilemez** — çünkü altlarındaki akit yapısı farklıdır.
Bir murabaha işlemini konvansiyonel bir borç ürünü gibi modelleyen sistem,
kullanıcıya doğru sayıyı gösterse bile yanlış ürünü göstermiş olur.

Sonuç: piyasadaki kıyaslama altyapıları bu ürün ailesini **veri modeli
düzeyinde tanımıyor**. Tanımadığı için de kıyaslayamıyor.

Bu yüzden projede 101 terimlik bir katılım finansı sözlüğü
(`data/terminology/katilim-terim-sozlugu.json`, mentör sağladı, avukat
doğrulaması) veri modelinin merkezinde duruyor — bir ek özellik olarak değil.

---

## 3. Yarattığı maliyet

**Vatandaş tarafında:** 10 bankayı elle taramak, her birinde ortalama birkaç
kampanya sayfası okumak ve bunları karşılaştırılabilir hâle getirmek bir
oturuşta bitmiyor. Üstelik kampanyalar **tarihli**; bugün doğru olan tablo iki
hafta sonra yanlış. Kullanıcı ya süreci tekrarlıyor ya da eski bilgiyle karar
veriyor.

**Karar kalitesi tarafında:** Elle kurulan tabloda en sık yapılan hata
**adil olmayan kıyas** — aylık oranla yıllık oranı, farklı vadeleri, farklı
tutar bantlarını yan yana koymak. Sistem bu yüzden karşılaştırmayı serbest
bırakmıyor; `src/comparison/compare.py` yalnızca aynı ürün türü, aynı vade ve
aynı tutar bandı içinde kıyas yapıyor (adil-kıyas garantisi).

**Ölçülmüş bir maliyet kalemi de var:** korpusta bankalar arası ve banka içi
**çelişkiler** tespit ediliyor — aynı ürün için farklı sayfalarda farklı
sayılar. Kullanıcının bunu elle fark etme şansı yok.

**Problemin ne kadar sinsi olduğunu gösteren somut bir bulgu:** kampanya
metinlerinde başlangıç ve bitiş tarihi çoğu zaman aynı cümlede geçiyor.
Naif bir çıkarım — metindeki ilk tarihi al — başlangıç-bitiş çifti içeren
**492 belgenin 442'sinde (%90)** kampanya süresi alanına yanlışlıkla
**başlangıç** tarihini yazıyordu. Yani kullanıcıya "bu kampanya şu tarihte
bitiyor" diye gösterilen şey, aslında kampanyanın başladığı tarihti.
Düzeltmeden sonra aynı ölçüm **sıfır** verdi.

Bu bulgu problemin doğasını özetliyor: metin insan gözüne açık, makineye
tuzaklı. Sorun veriye erişmek değil, **doğru okumak**.

> TODO: ölçülecek — kullanıcının elle kıyas için harcadığı ortalama süre
> saha ölçümüyle doğrulanmadı; bu belge süre iddiası yapmıyor.

---

## 4. Bugün nasıl çözülüyor

Üç yol var, üçü de eksik:

1. **Elle tarama.** Kullanıcı her bankaya tek tek giriyor. Yukarıdaki maliyetin
   tamamı burada.
2. **Ticari kıyaslama siteleri.** Konvansiyonel ürünleri kıyaslıyorlar. Katılım
   ürünleri (sukuk, kira sertifikası, ihtiyaç/konut/taşıt finansmanı, katılma
   hesabı) bu platformlarda **yok**. Olanlar da konvansiyonel şemaya
   sıkıştırılmış hâlde — yani kâr payı oranı, konvansiyonel bir orana denk
   sayılarak listeleniyor ki bu katılım bankacılığı açısından yanlış bir
   eşitleme.
3. **Bankanın kendi kanalı.** Her banka kendi ürününü gösteriyor; kıyas yok.

---

## 5. Farkımız

Üç maddede:

**(a) Ürün ailesini gerçekten tanıyoruz.** 8 kampanya türü (Finansman, İhtiyaç
Finansmanı, Konut Finansmanı, Taşıt Finansmanı, Kart, Alışveriş Puanı, Yeni
Müşteri, Yatırım Ürünü) ve 101 terimlik sözlük veri modelinin içinde. Çıkarılan
her alan katılım terminolojisiyle normalize ediliyor; chatbot'un çıkışında
konvansiyonel terim sızmasını engelleyen bir güvenlik katmanı var (ölçüldü:
1.696 belgelik korpus stresinde nihai yanıtlarda kalan konvansiyonel terim
**0/30**).

**(b) Her sayı kaynağına bağlı.** Çıkarılan her alan `source_span` taşıyor —
yani "bu oranı hangi cümleden aldın" sorusunun cevabı arayüzde vurgulanabiliyor.
Her belge `source_url` + `scraped_at` + sha256 `content_hash` ile izlenebilir.
Kıyaslama sitelerinin veremediği şey tam olarak budur.

**(c) İddiamızı ölçtük — ve ölçüm bizi yanlışladığında onu da yazdık.**
Ablasyonda LLM eklemek doğruluğu **artırmadı**. Güncel ölçüm (HEAD `654dd1f`,
gold 20 belge, 12 alan, `strict` eşleştirici):

| kol | mikro-F1 | halüsinasyon |
|---|---:|---:|
| **kural** | **0,677** | **0,096** |
| orkestra (yetkisiz LLM) | 0,672 | 0,114 |
| hibrit (yazma yetkili LLM) | 0,575 | 0,163 |

Kural katmanı her iki LLM'li kolu da geçti. Bu sonuç beklentimizin tersiydi ve
`docs/rapor/ablasyon.md` bunu açıkça "kanıtlanmadı, tersi ölçüldü" diye yazıyor.
Ayrıntılı gerekçe: `docs/resilience_narrative.md`.

Bu üçüncü madde konumlandırmanın kalbidir: alanda "önce kural, sonra LLM"
argümanını savunan başka çalışmalar da var. Ayrıştığımız yer argüman değil,
**onu güven aralığıyla birlikte ölçmüş olmamız**.

---

## 6. Kapsam sınırı — dürüstlük notu

- Ablasyon **n = 20 belgelik** bir gold set üzerinde koştu. Bir önceki ölçüm
  turunda kural kolunun %95 güven aralığı **[0,483–0,716]** genişliğindeydi;
  bu belge dar bir aralık iddia etmiyor.
- Kampanya türü sınıflandırmasında kural temel çizgisi accuracy **0,700**,
  makro-F1 **0,762** (n=20, çekimser 1/20). Sınıf başına ~2,5 örnek düştüğü
  için bu bir **sıralama sinyalidir**, kesin performans değil. BERTurk ince
  ayarının geçmesi gereken çizgi budur.
- Korpustaki 2.204 çıkarılmış alanın **%100'ü** kural katmanından geldi
  (`ner` 0, `llm` 0). Yani bugünkü sistem fiilen deterministiktir.

---

## Kaynaklar

- `docs/rapor/ablasyon.md` §1 — ablasyon tablosu (2026-08-05)
- `docs/rapor/devam-gumus-denetleme.md` — kampanya türü kural temel çizgisi
- `docs/rapor/olcumler.md` §6 — güvenlik katmanı ve korpus stresi
- `data/terminology/katilim-terim-sozlugu.json` — 101 terim
- `config/banks.yaml` — 10 katılım bankası
- `docs/positioning.md`, `docs/resilience_narrative.md`
