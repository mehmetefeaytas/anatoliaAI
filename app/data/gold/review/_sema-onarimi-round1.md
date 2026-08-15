# Round1 Şema Onarımı

> `scripts/sema_onarimi_uygula.py` üretti. Bu hücrelerde anotatörün yazdığı değer kanonik biçime çevrilemiyordu ve `build_gold` satırı ATIYORDU — yani anotasyon emeği gold'a hiç ulaşmıyordu.

## Bu bir hakemlik DEĞİL

Hücrelerde tek anotatör var; gizlenecek ikinci karar yok. Üçüncü göze anotatörün yazdığı ham değer de verildi (niyeti veridir, bağlayıcı değildir). Uyuşmazlık çözümü için `_hakemlik-degisim-round1.md`'ye bakın.

## Sayılar

- öneri: **18**
- uygulanan: **18**
- reddedilen: **0**

| dosya | hücre |
|---|---:|
| `round1_A` | 2 |
| `round1_B` | 1 |
| `round1_main_C` | 12 |
| `round1_main_D` | 3 |

| yeni karar | adet |
|---|---:|
| `absent` | 10 |
| `fix` | 3 |
| `ok` | 4 |
| `unclear` | 1 |

## Değişen hücreler

### `round1_A`:2 — albaraka--detay-dijital-musterilere-ozel-pratik-finansman-kart · `campaign_type`

- **önce:** `fix` / `İhtiyaç Finasmanı`
- **sonra:** `fix` / `İhtiyaç Finansmanı`
- **gerekçe:** Metinde birçok finasman vardır ama ana odak ihtiyaç finasmanıdır | #sema-onarimi-round1 Anotatörün niyeti doğru, yazımı kanonik değildi (Finasmanı -> Finansmanı). Belge tek ürünü anlatıyor: 'Pratik Finansman Kart; ... tüm bireysel ihtiyaçlarınıza ... kart formunda alışveriş finansmanıdır' ve 'belirlediğiniz vade ve kar oranı üzerinden ihtiyaç finansmanı kullanmış olursunuz'; ayrıca araç veya konut alımını açıkça dışlıyor. Modelin 'Konut Finansmanı' değeri belgeyle çelişiyor.

### `round1_A`:105 — ziraat-katilim--kart-kampanyalari-troy-kartla-drda-1000-tlye-varan-indirim · `finansman_tutari`

- **önce:** `fix` / `(boş)`
- **sonra:** `absent` / `(boş)`
- **gerekçe:** #sema-onarimi-round1 Anotatör fix dedi ama değer yazmadı; fix + boş gold_value derlemeyi durdurur. Belgede finansman kullandırımı yok: kampanya TROY kartla indirim kampanyasıdır. Modelin gösterdiği 1.000 TL, finansman tutarı değil indirimi hak etmek için gereken asgari sepet tutarı ve kart başına toplam indirim tavanıdır. Model dolu değer üretti, kampanyaya ait böyle bir değer yok -> absent (halüsinasyon).

### `round1_B`:134 — albaraka--formlar-genel-kredi-sozlesmesi-ucret-bilgilendirme-formu-pdf · `tahsis_ucreti`

- **önce:** `fix` / `{"max": 0.25, "min": 0}`
- **sonra:** `unclear` / `(boş)`
- **gerekçe:** Belgede ticari limit tahsis ücreti için oran %0,25 olarak belirtilmiştir. | #sema-onarimi-round1 Anotatörün yazdığı {min:0, max:0.25} bir ORAN; tahsis_ucreti alanı para tiplidir ({value, currency}) ve kılavuz §4.13/5 gereği oransal tahsis ücreti unclear'dır. Belgede 'Ticari Limit Tahsis Ücreti ... Maksimum Oran %0,25' ve 'Taşıt Tahsis Ücreti (BİREYSEL) TRY 0,5' geçiyor; ikisi de tutara bağlı oran, TL tutar yok. #oransal_ucret

### `round1_main_C`:33 — hayat-finans--hesaplar-avantajli-gunluk-hesap · `campaign_type`

- **önce:** `Fix` / `Katılım hesabı`
- **sonra:** `ok` / `(boş)`
- **gerekçe:** #sema-onarimi-round1 Anotatörün yazdığı 'Katılım hesabı' kapalı kümede yok; biçim kartı §3/8 eşlemesi katılma/altın/yatırım hesabını 'Yatırım Ürünü'ne bağlıyor. Sayfa tek özne testinden geçiyor: baştan sona yalnız Avantajlı Günlük Hesap (1 günlük katılma hesabı) anlatılıyor. Modelin 'Yatırım Ürünü' değeri doğru.

### `round1_main_C`:34 — hayat-finans--hesaplar-avantajli-gunluk-hesap · `finansman_tutari`

- **önce:** `Fix` / `(boş)`
- **sonra:** `absent` / `(boş)`
- **gerekçe:** Metindeki 10000 TL finansman tutarı değil katılım hesabı açılış limitidir | #sema-onarimi-round1 Anotatörün gerekçesi doğru ama kararı yanlış kodlanmış: fix + boş gold_value derlemeyi durdurur. Belge bir katılma hesabını anlatıyor, finansman kullandırımı yok; modelin gösterdiği 10.000 TL 'Minimum Açılış Tutarı'dır. Model dolu değer üretti, kampanyaya ait finansman tutarı yok -> absent.

### `round1_main_C`:35 — hayat-finans--hesaplar-avantajli-gunluk-hesap · `odul_miktari`

- **önce:** `Fix` / `(boş)`
- **sonra:** `absent` / `(boş)`
- **gerekçe:** Metinde sayısal bir ödül miktarı yer almamaktadır.⁠ | #sema-onarimi-round1 Anotatörün notu doğru ('metinde sayısal ödül miktarı yok') ama fix + boş gold_value derlemeyi durdurur; model dolu bir değer ({value: 0.0}) ürettiği için doğru etiket absent'tır. Modelin dayandığı 85.000 TL bir ödül değil, Altın derecesine hak kazanma eşiğidir. Ödül yerine derece bazlı kâr paylaşım oranları veriliyor, tutar değil.

### `round1_main_C`:45 — hayat-finans--krediler-hayat-finans-egitim-finansmani-sistemi · `campaign_type`

- **önce:** `Fix` / `Eğitim finansmanı`
- **sonra:** `ok` / `(boş)`
- **gerekçe:** #sema-onarimi-round1 Anotatörün yazdığı 'Eğitim finansmanı' 8 sınıfta yok. Ürün bir finansman ürünüdür (üst limit 600.000 TL, vade farksız, gelir belgesiz) ama ihtiyaç/konut/taşıt olarak nitelenmiyor; belge kendini hiçbir yerde 'ihtiyaç finansmanı' demiyor. Kapalı kümedeki jenerik 'Finansman' sınıfı bu ürünü gerçekten kapsıyor, dolayısıyla absent + #sema_disi gerekmez. Model doğru.

### `round1_main_C`:49 — kuveyt-turk--alisveris-finansmanlari-alisveris-finansmani · `campaign_type`

- **önce:** `Fix` / `Alışveriş finansmanı`
- **sonra:** `fix` / `İhtiyaç Finansmanı`
- **gerekçe:** #sema-onarimi-round1 Anotatörün yazdığı 'Alışveriş finansmanı' kapalı kümede yok, ama belge kendi tanımını veriyor: 'Alışveriş Finansmanı, anlaşmalı e-ticaret siteleri ve bayilerde ödeme imkanı sunan dijital ihtiyaç finansmanı ürünüdür' -> İhtiyaç Finansmanı. Modelin 'Kart' değeri yanlış; ürün açıkça 'kredi kartı limitinizi kullanmadan' çalışıyor. Soldaki bağlantılar yan menüdür (§4.13/8), gövde tek ürünü anlatır.

### `round1_main_C`:57 — kuveyt-turk--alisveris-finansmanlari-vivense-alisveris-finansmani · `campaign_type`

- **önce:** `Fix` / `Alışveriş finansmanı`
- **sonra:** `fix` / `İhtiyaç Finansmanı`
- **gerekçe:** #sema-onarimi-round1 Aynı ürünün mağazaya özel sürümü: belge 'Kuveyt Türk Alışveriş Finansmanı' adını anıyor ve mobilya alışverişini 36 aya varan taksitle finanse ediyor; ana ürün sayfası bu ürünü 'dijital ihtiyaç finansmanı ürünü' diye tanımlıyor, aynı aileyi bölmemek için satır 49 ile aynı sınıf verildi. Modelin 'Kart' değeri yanlış: metin 'kredi kartı limitiniz ve nakit paranızdan harcamadan' diyor. Jenerik 'Finansman' da savunulabilirdi; aile birliği tercih edildi.

### `round1_main_C`:62 — kuveyt-turk--hesaplar-katilma-hesaplari-2 · `campaign_type`

- **önce:** `Fix` / `Katılım hesabı`
- **sonra:** `ok` / `(boş)`
- **gerekçe:** Metingenel bi yatırım ürünü değil katılma hesabı hakkındadır | #sema-onarimi-round1 Sayfa tek özne: yalnız Kuveyt Türk Katılma Hesapları anlatılıyor (tür/para birimi kırılımları aynı ürünün varyantları, ürün listesi değil). Eşleme kartı §8: katılma hesabı -> Yatırım Ürünü. Anotatörün yazdığı 'Katılım hesabı' kapalı kümede yok; modelin değeri kanonik ve doğru.

### `round1_main_C`:64 — kuveyt-turk--hesaplar-katilma-hesaplari-2 · `odul_miktari`

- **önce:** `Fix` / `(boş)`
- **sonra:** `absent` / `(boş)`
- **gerekçe:** Metindeki 1.000 TL bir ödül miktarı değil, Günlük Kazançlı Katılma Hesabı açılış bakiyesidir. | #sema-onarimi-round1 Model 1000 TRY üretti; metindeki 1000 TL Günlük Kazançlı Katılma Hesabı'nın minimum açılış bakiyesidir, ödül değildir. Belgede hiçbir ödül/hediye tutarı yok -> onaylanmış halüsinasyon. Anotatörün niyeti doğruydu ama 'fix' + boş gold_value derlemeyi durdurur; doğru etiket absent.

### `round1_main_C`:136 — turkiye-finans--bireysel-urun-hizmet-ucretleri · `finansman_tutari`

- **önce:** `Fix` / `(boş)`
- **sonra:** `absent` / `(boş)`
- **gerekçe:** 50.0 TL EFT masrafındaki asgari işlem ücretidir | #sema-onarimi-round1 Model 200 TRY üretti; bu, kıymetli maden/EFT transfer ücretinin azami tutarıdır (min 50 - maks 200 TL), finansman tutarı değil. Sayfa bir ürün ve hizmet ücretleri listesidir; hiçbir yerde finansman anapara tutarı ilan edilmiyor -> halüsinasyon.

### `round1_main_C`:150 — turkiye-finans--ticari-katilma-hesaplari-ticari-katilma-hesaplari · `campaign_type`

- **önce:** `Fix` / `Katılım hesabı`
- **sonra:** `ok` / `(boş)`
- **gerekçe:** #sema-onarimi-round1 Gövde tek ürünü anlatıyor: Ticari Katılma Hesabı (TL/USD/EUR/altın/gümüş vadeler aynı ürünün seçenekleri; kalan metin site menüsü). Eşleme kartı §8 gereği katılma hesabı -> Yatırım Ürünü. Anotatörün 'Katılım hesabı' yazımı 8 sınıfta yok, modelin değeri doğru.

### `round1_main_C`:193 — kuveyt-turk--alisveris-finansmanlari-alisveris-finansmani · `finansman_tutari`

- **önce:** `Fix` / `(boş)`
- **sonra:** `absent` / `(boş)`
- **gerekçe:** Metinde finansman tutarı bulunmamaktadır. 0.0 değeri hatalıdır | #sema-onarimi-round1 Model 0.0 TRY üretti; kaynağı hesaplama aracının boş widget alanı (0,00 TL). Metinde ürünün ilan ettiği bir finansman tutarı/tavanı yok: 10.000 TL açıkça örnek hesaplama, 20.000 TL ise cep telefonunda taksit sayısı eşiğidir. Anotatörün gerekçesi doğru, etiketi absent olmalı.

### `round1_main_C`:197 — kuveyt-turk--ihtiyac-finansmanlari-seyahat-finansmani · `finansman_tutari`

- **önce:** `Fix` / `(boş)`
- **sonra:** `absent` / `(boş)`
- **gerekçe:** Metinde finansman tutarı bulunmamaktadır. 0.0 değeri hatalıdır | #sema-onarimi-round1 Model 0.0 TRY üretti; değer hesaplama aracının boş alanından (0,00 TL) geliyor. Belgede ilan edilmiş finansman tutarı yok; tablodaki 10.000 TL 'örnek maliyet tablosu' verisidir, kampanyaya ait tutar değildir. fix + boş gold_value yerine absent.

### `round1_main_D`:22 — dunya-katilim--hesaplar-cari-hesaplar · `vade_ay`

- **önce:** `fix` / `{"has_fee": false,"amount": 0}`
- **sonra:** `absent` / `(boş)`
- **gerekçe:** model, vade_ay değerine 12 yazarak hata yapmıştır. Doğru değer veri metninde de yazdığı gibi vadesiz anlamına gelen {"has_fee": false,"amount": 0} olacaktır. | #sema-onarimi-round1 Model 12 üretti; kaynak, çerez aydınlatma metnindeki _ga çerezinin '1 yıl' saklama süresidir - kampanya/ürün vadesi değil. Sayfadaki hesapların hepsi vadesiz cari hesaptır, dolayısıyla vade_ay yok. Anotatörün yazdığı {has_fee/amount} masraf_durumu biçimidir, vade_ay pozitif tamsayı alır; o biçim bu alana yazılamaz.

### `round1_main_D`:43 — hayat-finans--kampanyalar-hayatfinansla-islem-yaptikca-kazan · `campaign_type`

- **önce:** `fix` / `mevcut müşteri`
- **sonra:** `absent` / `(boş)`
- **gerekçe:** model, hedef_kitle = yeni müşteri eşleştirmesini yaparak hata yapmıştır. Veri metninde bahsedilen hedef kitlemevcut müşteridir | #sema-onarimi-round1 değer hedef_kitle'ye aittir: mevcut müşteri. campaign_type için: kampanya, EFT/FAST gelen transfer, fatura ödeme, döviz, banka kartı harcaması ve Biz Kart başvurusundan Hayat Pay cüzdanına nakit ödül veren işlem bazlı sadakat programıdır; ödül puan değil nakittir ve tek bir ürüne bağlı değildir. 8 sınıftan hiçbiri uymuyor; Yeni Müşteri yanlış (metin mevcut bireysel müşterileri hedefliyor). #sema_disi: nakit ödül (cashback) bankacılık işlem kampanyası

### `round1_main_D`:84 — kuveyt-turk--kampanya-arsivi-kuveyt-turkten-tahsildara-ozel-mil-kampanyasi · `campaign_type`

- **önce:** `fix` / `Belirli Segment`
- **sonra:** `absent` / `(boş)`
- **gerekçe:** model,  hedef kitle olarak yeni mişteri eşleştirmesi yapmış ve yanılmıştır. Doğru hedef kitle belirli segment olmalı. | #sema-onarimi-round1 değer hedef_kitle'ye aittir: Belirli Segment. campaign_type için: belge, Tahsildar.com.tr paketi alıp POS'unu Kuveyt Türk kartlarına taksite açan üye iş yerlerine taksitli ciro karşılığı Mil (5.000-10.000 Mil / 150-300 $) veren bir POS-üye iş yeri ödül kampanyasıdır. 8 sınıftan hiçbiri uymuyor: ödül tüketici alışveriş puanı değil iş yeri mili, ürün de bir finansman/kart/yatırım ürünü değil. #sema_disi: üye iş yeri (POS) mil ödül kampanyası

## Yedekler

- `data/gold/review/round1_A.csv.yedek-sema-onarimi-round1`
- `data/gold/review/round1_B.csv.yedek-sema-onarimi-round1`
- `data/gold/review/round1_main_C.csv.yedek-sema-onarimi-round1`
- `data/gold/review/round1_main_D.csv.yedek-sema-onarimi-round1`
