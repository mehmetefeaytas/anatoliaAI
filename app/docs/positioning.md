# Konumlandırma — İki Hedef Kitle ve On-Prem'in Gerçek Gerekçesi

İlgili: `docs/problem_statement.md`, `docs/resilience_narrative.md`,
`docs/future_work.md`, `docs/legal_notes.md`
Tarih: 2026-08-07

---

## 1. Özet iddia

Aynı çekirdek iki farklı ürüne dönüşür: vatandaşa dönük bir **kıyaslama aracı**
(B2C) ve bankanın satın alıp kendi kanalına gömdüğü bir **kıyaslama motoru**
(B2B). İkinci kurgu, mentörlerin önerisidir ve on-prem tercihimizi ilk kez
gerçekten gerekçelendiren şeydir.

---

## 2. B2C — vatandaş kıyaslama aracı

**Kim:** Katılım bankacılığı ürünü arayan, konvansiyonel bankacılığı tercih
etmeyen kullanıcı.

**Ne alıyor:** 10 katılım bankasının kampanyalarını tek ekranda, adil kıyas
garantisiyle (aynı ürün türü, aynı vade, aynı tutar bandı) ve her sayının
kaynak cümlesi vurgulanmış hâlde. Yapısal sorular (`en düşük kâr payı hangi
bankada`) text-to-SQL yoluna, koşul/açıklama soruları RAG yoluna gidiyor.

**Neden inandırıcı:** Bugün bu kitleye hizmet eden bir araç yok. Ticari
kıyaslama platformları katılım ürün ailesini veri modeli düzeyinde tanımıyor
(`docs/problem_statement.md` §4).

**Zayıf noktası — dürüstçe:** B2C tarafında veri, bankaların herkese açık
sayfalarından kazınıyor. Bu, yarışma için yeterli ve hukuken temiz
(`docs/legal_notes.md`), ama ticari ölçekte kırılgan: sayfa yapısı değişir,
site engeller, kullanım koşulları bağlayıcı hâle gelir. B2C tek başına bir
şirket kurgusu değil, bir **vitrin**dir.

---

## 3. B2B — bankanın içine giren ürün

**Kim:** Katılım bankasının dijital kanal / ürün ekibi.

**Ne satın alıyor:** Kendi mobil uygulamasına ve internet şubesine gömülen bir
kıyaslama modülü. Banka, müşterisine "piyasadaki tüm katılım ürünlerini
karşılaştır" diyor ve karşılaştırma sonucunda **kendi üstünlüğünü** gösteriyor.

**Bankanın kazancı üç katmanlı:**

1. **Müşteriyi kendi kanalında tutar.** Bugün müşteri kıyas yapmak için
   bankanın uygulamasından çıkıp üçüncü taraf bir siteye gidiyor. O sitede
   rakibin reklamını görüyor. Kıyas bankanın kendi uygulamasında yapılırsa
   müşteri çıkmıyor — ve kıyası kimin sunduğu, kimin kazandığı kadar önemli.
2. **Kendi üstünlüğünü kanıtla gösterir.** "Bizim konut finansmanımız daha
   avantajlı" cümlesi pazarlama iddiasıdır; kaynak cümlesi vurgulanmış bir
   kıyas tablosu **kanıttır**. Sistem her alanı `source_span` ile döndürdüğü
   için banka gösterdiği sayının arkasında durabilir.
3. **Rakip istihbaratı iç kullanım olarak da değerlidir.** Aynı motor,
   müşteriye hiç gösterilmeden, ürün ekibinin rakip kampanyalarını izlemesi
   için çalışır. Sistem korpusta çelişki tespiti yapıyor — banka rakibin
   sayfaları arasındaki tutarsızlığı da görebiliyor.

**Neden bu kurgu B2C'den sağlam:** Veri sorunu ortadan kalkıyor. Banka kendi
ürün verisini kendi sistemlerinden besliyor; kazımanın hukuki yükü azalıyor
(`docs/legal_notes.md` §6). Gerçek üründe kazımanın yerini banka API'leri alıyor
(`docs/future_work.md`).

---

## 4. On-prem gerekçesi — mentörün eleştirisi haklıydı

**Eleştiri:** "Sadece herkese açık veri kazıyorsan lokal host anlamsız."

Bu itiraz doğrudur ve kabul ediyoruz. Kamuya açık kampanya metni gizli veri
değildir; onu işlemek için verinin kurum içinde kalmasını gerektiren bir
gerekçe yoktur. B2C kurgusunda on-prem, teknik bir tercih olmanın ötesine
geçmiyor.

**Cevap:** On-prem, sistem bankanın **içine** girdiğinde anlam kazanır.

Ürün bankanın kanalına gömüldüğü anda üç şey değişir:

- Sisteme giren veri artık yalnızca kamuya açık metin değildir. Bankanın kendi
  ürün verisi, fiyat politikası, ve (`docs/future_work.md`'de anlatılan
  API bankacılığı kurgusunda) müşteri segmentine özel indirilebilir alt limitler
  sisteme girer. Bunlar bankanın ticari sırrıdır.
- Kullanıcı sorguları müşteri davranışı verisidir. "Hangi müşteri hangi ürünü
  kıyasladı" bilgisi tek başına kişisel veri işleme sorusudur.
- **BDDK, satın alınan ürünün Türkiye'de host edilmesini zorunlu kılar.** Bir
  banka, dış kaynaklı bir yazılımı ancak yurt içinde barındırılabildiği ölçüde
  satın alabilir. Yani on-prem burada bir tercih değil, **satın alınabilirliğin
  ön koşuludur**.

> TODO: ölçülecek — ilgili BDDK düzenlemesinin madde numarası ve yürürlük
> tarihi bu belgede doğrulanmadı; sunumdan önce birincil kaynaktan teyit
> edilmeli (Vakıf Katılım R&D üzerinden erişilebilir).

Sonuç: on-prem argümanı B2C'de zayıftır, B2B'de zorunludur. Bu yüzden
konumlandırmayı B2B üzerinden kuruyoruz ve on-prem'i oraya bağlıyoruz.

---

## 5. Rakip karşısında konum — ayrıştığımız gerçek nokta

Alandaki diğer çalışmalar incelendi (`docs/rapor/rakip-analizi.md`, iç belge).
İki bulgu konumlandırmayı doğrudan belirliyor:

**Bulgu 1 — "on-prem + açık kaynak + ücretsiz" ayırt edici değil.** Bu üçlü
incelenen depoların neredeyse tamamında var. Sunumda bunu bir **üstünlük**
olarak öne sürmek zaman kaybıdır. Ayırt edici olan, on-prem'in **neden** gerekli
olduğuna dair B2B gerekçesidir (§4) — ve bu gerekçeyi kuran başka bir çalışma
görülmedi.

**Bulgu 2 — argüman ortak, ölçüm bize ait.** Alandaki en olgun çalışma da
"deterministik kurallar birincil, yerel model yalnızca kısıtlı bir yardımcı"
diyor. Mimari tez aynı. Fakat o tezi destekleyen **tek bir F1 sayısı
paylaşamıyorlar**; altın setleri birkaç örnek düzeyinde ve insan doğrulaması
yok. Bazı çalışmalar noktasal doğruluk oranları yayımlıyor, ancak güven aralığı,
ablasyon kolu ve anlamlılık testi içeren bir ölçüm yok.

**Bizim konumumuz:** Aynı mimari tezi savunuyoruz — ama onu 12 alanlık bir gold
set üzerinde, birden fazla ablasyon koluyla (kural / hibrit / orkestrasyon /
saf LLM), hata sınıfları ayrı paydalarla (kaçırma, yanlış çıkarım, halüsinasyon)
**ölçtük**. İlk turda bootstrap güven aralığı ve McNemar testi de üretildi
(kural %95 GA [0,483–0,716], p = 0,0117). Ve ölçüm hipotezimizi yanlışladığında
— hibrit kuraldan kötü çıktı, orkestrasyon da geçemedi — sonucu değiştirmedik,
negatif sonuç olarak yazdık.

Ölçme disiplininin bir parçası da neyi **ölçmediğimizi** söylemektir: güncel
ablasyon turu için güven aralıkları yeniden koşulmadı, kalibrasyon (ECE) hiç
üretilmedi ve prompt-injection yalnızca kapı modunda sınandı. Bunların hepsi
`docs/resilience_narrative.md` §8'de açıkça işaretli.

> Sunumdaki cümle şu olmalı: *"Bu mimariyi savunan tek ekip biz değiliz.
> Ama onu ölçen, kendi hipotezini yanlışlayan sonucu yayımlayan ve neyi henüz
> ölçmediğini de yazan ekibiz."*

---

## 6. İki kitleyi tek çekirdek nasıl karşılıyor

| Katman | B2C | B2B |
|---|---|---|
| Veri girişi | Kamuya açık sayfaların kazınması | Bankanın kendi verisi + rakip verisi (ileride API) |
| Çıkarım | Aynı — kural birincil, LLM opsiyonel | Aynı |
| Normalizasyon + 101 terim sözlüğü | Aynı | Aynı |
| Adil kıyas garantisi | Aynı | Aynı |
| Sunum | Bağımsız dashboard + chatbot | Bankanın mobil uygulamasına gömülü modül |
| Barındırma | İsteğe bağlı | **Zorunlu on-prem (BDDK)** |

Değişen tek katman **veri girişi ve sunum**. Çekirdek aynı kaldığı için B2C
demosu, B2B satışının vitrinidir — atılacak iş değil.

---

## Kaynaklar

- `docs/problem_statement.md` — problem ve mevcut çözümlerin eksiği
- `docs/resilience_narrative.md` — kural katmanının dayanıklılık gerekçesi
- `docs/future_work.md` — API bankacılığı ve gerçek ürün yönü
- `docs/legal_notes.md` — kazımanın hukuki durumu ve B2B'de dönüşümü
- `docs/rapor/ablasyon.md` — ölçüm temelli ayrışma
- `docs/rapor/rakip-analizi.md` — iç belge, paylaşılmaz
