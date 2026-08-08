# Gelecek Çalışmalar — API Bankacılığı ve Gerçek Ürün Yönü

İlgili: `docs/positioning.md` §3-§4, `docs/legal_notes.md` §6
Tarih: 2026-08-07

---

## 1. mentörün içgörüsü — fiyat tek sayı değil

Mentör toplantısında ortaya çıkan ve ürün yönümüzü değiştiren tespit şudur:

**Bankalar kıyaslama platformlarına tek bir fiyat vermiyorlar.**

Bir bankanın bir ürün için ilan ettiği kâr payı oranı, o bankanın o ürün için
verebileceği tek oran değildir. Banka, karşı tarafla paylaştığı veriyi
müşteriye göre katmanlar:

- **Müşteri segmenti.** Aynı ürün, farklı segmentte farklı fiyatlanır.
- **O müşteriye özel inebilecekleri alt limit.** Banka, ilan ettiği orandan
  daha aşağı inebileceği bir taban taşır ve bunu ilan etmez.
- **Üste çıkmak için ekstra veri.** Platform daha iyi bir teklif almak
  istiyorsa, banka karşılığında müşteri hakkında **daha fazla veri** ister.

Yani kıyaslama bir tablo okuma işi değil, **iki taraflı bir veri
alışverişidir**. Kamuya açık sayfadan okunan oran, bu alışverişin yalnızca
başlangıç noktasıdır.

---

## 2. Sonuç: gerçek ürün banka API'lerini tüketir

Bu tespitin doğrudan sonucu, bugünkü veri katmanımızın geçici olduğudur.

Bugün kazıma yaptığımız yerde, gerçek üründe **banka API'leri** olacaktır.
Kazıma bize ilan edilmiş oranı verir; API bize o müşteri için geçerli oranı
verir. Aradaki fark, ürünün gerçekten işe yarayıp yaramamasıdır.

Zincir şöyle kapanır:

```
banka API'si → müşteri segmenti + özel limit paylaşımı
             → sisteme ticari sır ve müşteri verisi girer
             → kapalı taraf (closed side) gerekir
             → on-prem ZORUNLU
```

Bu, `docs/positioning.md` §4'teki on-prem gerekçesinin ikinci ve daha güçlü
ayağıdır. Birinci ayak düzenleyicidir (BDDK, satın alınan ürünün yurt içinde
barındırılmasını zorunlu kılar). İkinci ayak mimaridir: **API bankacılığı
kurgusunda sistemin işlediği veri artık kamuya açık değildir.** Kamuya açık
metin kazıyan bir sistem için "neden lokal host" sorusu haklıdır; müşteri
segmentine özel fiyat pazarlığı yürüten bir sistem için aynı soru sorulmaz.

---

## 3. `src/mock_bank_api/` — önerilen future work, YAPILMADI

Bu kurguyu sunumda somutlaştırmanın yolu, sentetik veriyle çalışan bir
**örnek banka API'si** ve sistemin onu tüketen bir adaptörüdür: segment bazlı
fiyat döndüren, alt limit taşıyan, ekstra veri karşılığında daha iyi teklif
veren bir uç nokta.

**Bu bileşen bugün mevcut değildir.** Depoda `src/mock_bank_api/` diye bir
dizin yoktur; sentetik banka API'si ne kodda ne de yapılacaklar envanterinde
bulunmaktadır. Sistem bugün canlı API değil, **kazınmış statik metin +
PostgreSQL/SQLite** üzerinden çalışmaktadır.

### Sunum kuralı — pazarlık konusu değil

> Bu bileşen **yalnızca bir future work slaytı** olarak anlatılır.
> **Gerçek entegrasyon gibi sunulmaz.** Sentetik veriyle çalıştığı, gerçek
> banka API'si olmadığı ve henüz yazılmadığı slaytta ve konuşmada **açıkça**
> söylenir.

Gerekçe iki tanedir. Birincisi dürüstlük: sistemin geri kalanının tamamı
ölçülmüş ve kaynağa bağlı iddialardan oluşuyor; tek bir abartılı iddia bu
güvenilirliği bütünüyle harcar. İkincisi stratejik: jüri veya banka tarafındaki
teknik bir dinleyici "hangi bankayla entegresiniz" diye sorduğunda verilecek
cevap net olmalıdır — **hiçbiriyle, ve bunu baştan söylüyoruz.**

Sunumdaki doğru cümle: *"Gerçek ürün banka API'lerini tüketmek zorunda.
Bunu göstermek için sentetik veriyle bir örnek API tasarladık — henüz
yazılmadı, gerçek bir entegrasyon değil. Ama mimarinin nereye gittiğini
gösteriyor: kapalı tarafa, yani on-prem'e."*

---

## 4. Diğer açık işler

Aşağıdakiler ölçülmüş boşluklardır; hiçbiri bugün tamamlanmış gibi sunulmaz.

**(a) Prompt-injection'ı LLM modunda koştur.** Kapı modu ölçüldü ve **22/22
saldırı savuşturuldu**, aşırı-red denetimi 4/4 (`data/eval/injection.json`).
Ancak ölçüm `llm_modu: false` ile yapıldı — yani deterministik kapılar
sınandı, **RAG sentezi devre dışıydı**. Eksik olan, modelin ikna edilip
edilemediğidir. Aynı seti `llm_modu: true` ile koşturmak, güvenlik anlatısının
kalan tek boşluğunu kapatır.

**(b) Gold seti büyüt ve güven aralıklarını yeniden üret.** Ablasyon n = 20
üzerinde koştu. Güncel turda (kural 0,677 / orkestra 0,672) bootstrap güven
aralığı ve McNemar testi **yeniden koşulmadı**; bir önceki turda kural kolunun
aralığı [0,483–0,716] genişliğindeydi. Δ = −0,005'lik bir farkın bu n'de
anlamlılık taşıması zaten beklenmez — n'i büyütmek hem aralığı daraltır hem de
orkestrasyon karşılaştırmasını sonuçlandırılabilir kılar.

**(c) BERTurk ince ayarını yap.** Kampanya türü sınıflandırmasında geçilmesi
gereken kural temel çizgisi ölçüldü: accuracy **0,700**, makro-F1 **0,762**
(n=20, çekimser 1/20). Gümüş küme hazır: **505 kayıt, 8 sınıf**, en küçük sınıf
41 örnek (Finansman 41, Yeni Müşteri 41; en büyüğü Kart 144). Kural katmanının
zorlandığı yer teşhis edildi — **ürün ailesi ayrımı** (İhtiyaç Finansmanı en
zayıf halka, 0,500; karışıklıklar Yatırım Ürünü → İhtiyaç ve İhtiyaç → Konut
yönünde). BERTurk'ün kazanması beklenen yer tam olarak burasıdır.

**(d) Test sayısını belgeler arasında hizala.** Kanonik değer ölçüldü:
`python -m unittest discover -s tests` → **1455 test**, çıkış kodu 0
(2026-08-07). Eski belgelerdeki 345 / 607 / 890 / 1187 / 1359 sayıları
yazıldıkları anda doğruydu; bayat değiller ama güncel de değiller. Yeni
belgeler 1455 kullanıyor — bu sayı büyümeye devam edeceği için her alıntıda
tarih verilmeli.

**(e) Ticarileşme öncesi hukuki kapatmalar.** `docs/legal_notes.md` §4'teki
yedi kalem: robots fail-open'ın 403/5xx için fail-closed'a çevrilmesi,
`Crawl-delay`'in fiilen uygulanması, `--ignore-robots` bayrağının kaldırılması,
banka kullanım koşullarının incelenmesi, User-Agent'taki "araştırma amaçlı"
ibaresinin değiştirilmesi, `LICENSE` telif satırının doldurulması, veri seti
lisansının belirlenmesi.

**(f) Çerçeve (boilerplate) temizliği — ölçüldü, uygulanmadı.** Korpusun
**%42,6'sı** çerçeve metin (8,3M → 4,7M karakter). Körlemesine uygulanamıyor:
143 belge sinyal taşıdığı hâlde içeriğinin %75'inden fazlasını kaybediyor.
Sebep teşhis edildi — sözleşme şablonlarında tekrar gürültü değil, bilginin
kendisi.

---

## 5. Yol haritasının tek cümlesi

> Bugün ilan edilmiş oranı kaynağıyla birlikte çıkarıyoruz. Yarın müşteriye
> özel oranı banka API'sinden alacağız. Aradaki fark, sistemin nerede
> çalıştığını da belirliyor: kamuya açık veri her yerde işlenebilir,
> müşteriye özel fiyat **yalnızca bankanın içinde**.

---

## Kaynaklar

- `docs/positioning.md` §3-§4 — B2B kurgusu ve on-prem gerekçesi
- `docs/legal_notes.md` §4, §6 — ticarileşme öncesi kapatmalar
- `docs/rapor/ablasyon.md` — gold set büyüklüğü ve güven aralıkları
- `docs/rapor/devam-gumus-denetleme.md` — sınıflandırma temel çizgisi, gümüş küme
- `docs/rapor/devam-orkestrasyon.md` Faz C4 — çerçeve ölçümü
