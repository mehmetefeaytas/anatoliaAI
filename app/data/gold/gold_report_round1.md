# Gold Derleme Raporu

> `scripts/build_gold.py` üretti. Elle düzenlemeyin.

- Çıktı: `data/gold/gold.round1.json`
- SHA-256: `bb14b158a0dad721d90728979226573db4ce7bd6da5296632e2ab900f5ed538e`
- Kayıt: **158**
- Çift anote edilmiş kayıt: **66**
- 12/12 alan karara bağlı (recall ÖLÇÜLEBİLİR): **0**
- Kampanya sayılmayıp elenen belge: **6**
- Çelişki (anotatörler ayrıştı): **120**
- Hakemlik bekleyen kayıt: **45**
- Kanıtlı alan (`field_spans`): **166/183** (%90.7)

## Protokol künyesi

| Dosya | Protokol | Boş hücre |
|---|---|---|
| `data/gold/review/round0_kalibrasyon_A.csv` | **v1** | `ok` (onay) — modele çapalı |
| `data/gold/review/round0_kalibrasyon_B.csv` | **v1** | `ok` (onay) — modele çapalı |
| `data/gold/review/round0_kalibrasyon_C.csv` | **v1** | `ok` (onay) — modele çapalı |
| `data/gold/review/round0_kalibrasyon_D.csv` | **v1** | `ok` (onay) — modele çapalı |
| `data/gold/review/round0_kalibrasyon_v2_A.csv` | **v2** | karar verilmedi — gold'a GİRMEZ |
| `data/gold/review/round0_kalibrasyon_v2_B.csv` | **v2** | karar verilmedi — gold'a GİRMEZ |
| `data/gold/review/round0_kalibrasyon_v2_C.csv` | **v2** | karar verilmedi — gold'a GİRMEZ |
| `data/gold/review/round0_kalibrasyon_v2_D.csv` | **v2** | karar verilmedi — gold'a GİRMEZ |
| `data/gold/review/round1_A.csv` | **v2** | karar verilmedi — gold'a GİRMEZ |
| `data/gold/review/round1_B.csv` | **v2** | karar verilmedi — gold'a GİRMEZ |
| `data/gold/review/round1_main_C.csv` | **v2** | karar verilmedi — gold'a GİRMEZ |
| `data/gold/review/round1_main_D.csv` | **v2** | karar verilmedi — gold'a GİRMEZ |
| `data/gold/review/round1_v2_A.csv` | **v2** | karar verilmedi — gold'a GİRMEZ |
| `data/gold/review/round1_v2_B.csv` | **v2** | karar verilmedi — gold'a GİRMEZ |
| `data/gold/review/round1_v2_C.csv` | **v2** | karar verilmedi — gold'a GİRMEZ |
| `data/gold/review/round1_v2_D.csv` | **v2** | karar verilmedi — gold'a GİRMEZ |
| `data/gold/review/round2_zor_vaka.csv` | **v2** | karar verilmedi — gold'a GİRMEZ |

- v2'de karar verilmemiş satır: **3613** (A=504, B=500, C=540, D=392, v2_A=312, v2_B=312, v2_C=312, v2_D=312, zor_vaka=429)


## Ölçülebilirlik

- **Precision + halüsinasyon oranı:** tüm kayıtlarda ölçülebilir — modelin ürettiği her alan için karar var.
- **Recall:** yalnızca 12/12 kapsanan 0 kayıtta ölçülebilir; diğerlerinde anote edilmemiş alan ile gerçekten olmayan alan ayrılamaz.

## Kanıt (`field_spans`)

- Kanıtlı: **166/183** alan
- Kanıtsız: **17** alan — değer var, belgede birebir geçen alıntısı yok.

> Bu hattın kanıtı `merge_gold_v2` hattınınkiyle **aynı ağırlıkta değildir.** Orada alıntıyı anotatör belgeyi kör okuyarak elle yazdı; burada çıkarıcının kaydettiği konumu anotatör onayladı (`verdict=ok`). İkisi de belgede birebir geçer, ikincisi bağımsız bir gözlem değildir.

> Kanıtsız alanların çoğu `verdict=fix`tir: anotatör değeri düzeltti ama alıntı yazacağı bir sütun yok. Kanonik değeri metinde geri arayıp bir yer bulmak kanıt üretmek değil, **kanıt uydurmak** olurdu.

## Alan bazında

| Alan | değer | kanıtlı | yok (absent) | belirsiz |
|---|---:|---:|---:|---:|
| `kar_payi_orani` | 17 | 15 | 12 | 8 |
| `finansman_tutari` | 23 | 16 | 13 | 10 |
| `vade_ay` | 39 | 34 | 29 | 20 |
| `taksit_sayisi` | 15 | 15 | 12 | 11 |
| `tahsis_ucreti` | 0 | 0 | 17 | 4 |
| `masraf_durumu` | 7 | 7 | 12 | 7 |
| `odul_miktari` | 3 | 3 | 18 | 5 |
| `indirim_orani` | 1 | 1 | 18 | 1 |
| `alisveris_puani` | 2 | 2 | 19 | 2 |
| `kampanya_suresi` | 58 | 55 | 16 | 6 |
| `kampanya_kosullari` | 12 | 12 | 3 | 16 |
| `hedef_kitle` | 6 | 6 | 7 | 10 |

### Kanıtsız alanlar — kapatılacak iş listesi

| Belge | Alan |
|---|---|
| `albaraka--detay-dijital-musterilere-ozel-pratik-finansman-kart` | `finansman_tutari` |
| `albaraka--detay-dijital-musterilere-ozel-pratik-finansman-kart` | `kar_payi_orani` |
| `albaraka--detay-dijital-musterilere-ozel-pratik-finansman-kart` | `vade_ay` |
| `albaraka--tasit-finansmani-togg-finansmani` | `vade_ay` |
| `hayat-finans--hesaplar-avantajli-hesap` | `finansman_tutari` |
| `kuveyt-turk--hesaplar-katilma-hesaplari-2` | `kampanya_suresi` |
| `tom-katilim--urunlerimiz` | `finansman_tutari` |
| `turkiye-emlak-katilim--finansmanlar-ihtiyac-finansmani` | `kar_payi_orani` |
| `turkiye-emlak-katilim--finansmanlar-ihtiyac-finansmani` | `vade_ay` |
| `turkiye-finans--bireysel-gunluk-hesap` | `finansman_tutari` |
| `turkiye-finans--bireysel-urun-hizmet-ucretleri` | `vade_ay` |
| `turkiye-finans--kampanyalar-turkiye-finans-avantajlariyla-mobilden-tanis` | `finansman_tutari` |
| `turkiye-finans--kampanyalar-turkiye-finans-avantajlariyla-mobilden-tanis` | `kampanya_suresi` |
| `turkiye-finans--kobi-kobi-icin-gunluk-hesap` | `finansman_tutari` |
| `turkiye-finans--konut-finansmani-konut-finansmani` | `vade_ay` |
| `vakif-katilim--detay-igdas-finansman-kampanyasi` | `finansman_tutari` |
| `vakif-katilim--detay-igdas-finansman-kampanyasi` | `kampanya_suresi` |

## Zor-vaka etiketleri

| Etiket | Kayıt |
|---|---:|
| `kosullu_aralik` | 3 |
| `celiskili` | 2 |
| `terminoloji` | 1 |

## Çelişkiler — HAKEMLİK GEREKİYOR

| Belge | Alan | Kararlar |
|---|---|---|
| `albaraka--detay-dijital-musterilere-ozel-pratik-finansman-kart` | `hedef_kitle` | A=value:['mevcut_musteri', 'yeni_musteri']; B=value:['yeni_musteri'] |
| `albaraka--detay-vade-farksiz-kampanyasi` | `finansman_tutari` | A=value:{'currency': 'TRY', 'value': 40000.0}; B=value:{'currency': 'TRY', 'value': 100000.0}; C=value:{'value': 100000.0, 'currency': 'TRY'}; D=value:{'value': 100000.0, 'currency': 'TRY'} |
| `albaraka--detay-vade-farksiz-kampanyasi` | `taksit_sayisi` | A=value:4; B=value:6; C=value:4; D=value:4 |
| `albaraka--detay-vade-farksiz-kampanyasi` | `tahsis_ucreti` | A=value:{'value': 0.0, 'currency': 'TRY'}; B=absent:None; C=absent:None; D=absent:None |
| `albaraka--detay-vade-farksiz-kampanyasi` | `kampanya_suresi` | A=value:'2026-12-31'; B=value:'2026-12-31'; C=value:'2026-12-21'; D=value:'2026-12-31' |
| `albaraka--detay-vade-farksiz-kampanyasi` | `hedef_kitle` | A=absent:None; B=value:['yeni_musteri']; C=value:['belirli_segment', 'yeni_musteri']; D=absent:None |
| `albaraka--dis-ticaret-finansmanlari-harici-garantiler` | `campaign_type` | A=value:'Finansman'; B=absent:None |
| `albaraka--eviniz-icin-prefabrik` | `vade_ay` | A=value:24; B=value:36 |
| `albaraka--formlar-altin-hesaplarindan-donusumun-desteklenmesi-tl-katilma-hesabi-bilgilendi` | `kampanya_kosullari` | A=absent:None; B=value:["Vergi kesintileri, Katılma Hesabı'nın açılış/vade yenileme tarihinde ilgili vade için geçerli olan cari vergi oranları üzerinden hesaplanacağı, 8.", "Müşteri, katılma hesaplarının; Banka'nın herhangi bir oran veya tutarda getiri taahhüdü bulunmadığı, bu bakımdan Banka'nın asgari de olsa getiri taahhüdü/garantisi olmayan, karşılığında hesap sahibine önceden belirlenmiş herhangi bir getiri ödenmeyen ve anaparanın aynen geri ödenmesi garanti edilmeyen hesaplar olduğunu bildiğini, 10."] |
| `albaraka--formlar-genel-kredi-sozlesmesi-ucret-bilgilendirme-formu-pdf` | `campaign_type` | A=absent:None; B=value:'Finansman' |
| `albaraka--formlar-genel-kredi-sozlesmesi-ucret-bilgilendirme-formu-pdf` | `masraf_durumu` | A=absent:None; B=value:{'amount': None, 'has_fee': True} |
| `albaraka--gecmis-tarihli-aracfinansmanitalep-onayveucretbilgilendirmeformu-pdf` | `campaign_type` | A=absent:None; B=value:'Finansman' |
| `albaraka--gecmis-tarihli-aracfinansmanitalep-onayveucretbilgilendirmeformu-pdf` | `kar_payi_orani` | A=absent:None; B=value:30.0 |
| `albaraka--gecmis-tarihli-aracfinansmanitalep-onayveucretbilgilendirmeformu-pdf` | `masraf_durumu` | A=absent:None; B=value:{'amount': None, 'has_fee': True} |
| `albaraka--ihtiyac-saglik-harcamalariniz-icin` | `kampanya_kosullari` | A=value:['Genel Sağlık Yüksek risk içermeyen cerrahi operasyon, fizik tedavi, genel sağlık harcamaları başta olmak üzere muayene gibi sağlık ihtiyaçlarıınız için Genel Sağlık Kredisi alabilirsiniz.']; B=value:['["Diş temizleme, dolgu, implant, yüksek risk içermeyen cerrahi operasyonlar, fizik tedavi ve muayene gibi genel sağlık harcamaları için geçerlidir. Azami vade süresi 36 aydır."]\u2060']; C=absent:None; D=absent:None |
| `albaraka--tarim-bankaciligi-diger-finansmanlar` | `campaign_type` | A=value:'Finansman'; B=value:'İhtiyaç Finansmanı' |
| `albaraka--tarim-bankaciligi-diger-finansmanlar` | `kampanya_kosullari` | A=value:['Finansal Kiralama Makine ekipman, traktör ve biçerdöver finansmanı işlemleri finansal kiralama yöntemiyle ve hasat dönemine uygun ödeme koşulları ile 48 ay vadeye kadar yapılabilmektedir.', 'IPARD Programı kapsamında destek alan projeleriniz için gerekli olan finansmanı bankamızdan kullanabilirsiniz.']; B=absent:None |
| `albaraka--tasit-finansmani-togg-finansmani` | `kar_payi_orani` | A=absent:None; B=value:{'min': 0.0, 'max': 2.99}; C=value:2.99; D=value:2.99 |
| `albaraka--tasit-finansmani-togg-finansmani` | `finansman_tutari` | A=value:{'value': 1700000, 'currency': 'TRY'}; B=value:{'value': 600000.0, 'currency': 'TRY'}; C=unclear:None; D=absent:None |
| `albaraka--tatiliniz-icin-devre-mulk` | `vade_ay` | A=value:12; B=value:36 |
| `albaraka--tatiliniz-icin-devre-mulk` | `kampanya_kosullari` | A=value:['Albaraka Mobil Mobil Bankacılık Aç Devre Mülk Anasayfa Bireysel Finansmanlar İhtiyaç Finansmanı Tatiliniz İçin Devre Mülk Seyahat Devre Mülk Devre Tatil Hemen Başvur Devre mülkler tapu kaydı gerektiren ve her yıl belirli dönemlerde asgari 15 gün süreli konaklama imkânı veren mülklerdir.']; B=absent:None |
| `albaraka--tr-urun-ve-hizmet-ucretleri` | `campaign_type` | A=value:'Yatırım Ürünü'; B=value:'Finansman' |
| `albaraka--tr-urun-ve-hizmet-ucretleri` | `masraf_durumu` | A=value:{'has_fee': False, 'amount': 0.0}; B=value:{'amount': None, 'has_fee': True} |
| `albaraka--tr-urun-ve-hizmet-ucretleri` | `kampanya_kosullari` | A=value:['1.03.2020 İhtiyaç Finansmanı - % 0.5 - % 0.5 BSMV Hariçtir.', '14.08.2020 Yurt Dışı Diğer Şubeden Para Çekme - Şube - % 0.5 - % 1 BSMV Hariçtir.', '14.08.2020 Nakit Çekim Ofisinden Para Çekme - Nakit Çekim Ofisi TRY - - 5 - BSMV Hariçtir.', '15.01.2026 8.300-399.000 TL arası TRY 79.76 - 79.76 - BSMV Hariçtir.', '15.01.2026 399.000 TL üstü TRY 797.68 - 797.68 - BSMV Hariçtir.', '15.01.2026 Düzenli EFT Gönderimi - 8.300 TL ve altı TRY 7.97 - 7.97 - BSMV Hariçtir.', '16.02.2026 Düzenli EFT Gönderimi - 8.300-399.000 TL arası TRY 15.96 - 15.96 - BSMV Hariçtir.', '16.02.2026 Düzenli EFT Gönderimi - 399.000 TL üstü TRY 199.41 - 199.41 - BSMV Hariçtir.']; B=absent:None |
| `dunya-katilim--katilma-hesaplari-gunes-katilma-hesabi` | `campaign_type` | A=value:'Yatırım Ürünü'; B=absent:None |
| `dunya-katilim--katilma-hesaplari-gunes-katilma-hesabi` | `vade_ay` | A=value:1; C=absent:None; D=absent:None |
| `dunya-katilim--kendim-icin-altin-bankaciligi` | `vade_ay` | A=absent:None; B=value:12; C=absent:None; D=absent:None |
| `dunya-katilim--kendim-icin-altin-bankaciligi` | `kampanya_kosullari` | A=absent:None; B=value:['\u2060["Her türlü işlenmiş ziynet, hurda ve muhtelif altınlar değer kaybına uğramadan ATOM sistemiyle vadesiz altın hesabına aktarılabilir. Dijitalden sipariş verilerek fiziki altın kapıya teslim alınabilir."]\u2060']; C=absent:None; D=absent:None |
| `dunya-katilim--kredi-kartlari-paraf-platinum-kredi-karti` | `masraf_durumu` | A=value:{'has_fee': False, 'amount': 0.0}; B=value:{'amount': None, 'has_fee': True} |
| `dunya-katilim--kredi-kartlari-paraf-platinum-kredi-karti` | `kampanya_kosullari` | A=value:['Fizikî alışverişlerde, satıcıya ödemenizi Paraf Para ile yapmak istediğinizi söylemeniz gerekmektedir.']; B=absent:None |
| `hayat-finans--yatirim-ve-birikim-yatirimci-seviye-sistemi` | `campaign_type` | A=value:'Yatırım Ürünü'; B=unclear:None |
| `kuveyt-turk--altin-hesaplari-altina-altin-katilma-hesabi` | `kar_payi_orani` | A=value:40.0; B=value:40.0; C=value:{'min': 40.0, 'max': 60.0}; D=value:{'min': 40.0, 'max': 60.0} |
| `kuveyt-turk--altin-hesaplari-altina-altin-katilma-hesabi` | `vade_ay` | A=value:12; B=value:12; C=value:1; D=value:1 |
| `kuveyt-turk--bizden-haberler-kuveyt-turkten-1-milyar-tl-limitli-yeni-makine-finansmani-kampan` | `campaign_type` | A=value:'İhtiyaç Finansmanı'; B=value:'Finansman' |
| `kuveyt-turk--finansmanlar-ihtiyac-finansmanlari` | `campaign_type` | A=value:'İhtiyaç Finansmanı'; B=value:'İhtiyaç Finansmanı'; C=value:'İhtiyaç Finansmanı'; D=value:'Konut Finansmanı' |
| `kuveyt-turk--finansmanlar-ihtiyac-finansmanlari` | `vade_ay` | A=unclear:None; B=value:36; C=value:36; D=value:36 |
| `kuveyt-turk--finansmanlar-ihtiyac-finansmanlari` | `kampanya_kosullari` | A=absent:None; B=value:["Eğitim Finansmanı'na 36 aya kadar vade seçenekleri ile başvurabilirsiniz. Tekne Tüketici Finansmanı 36 aya kadar vade ve uygun kar payı oranları sunmaktadır"]; C=value:['Ana Sayfa Kendim İçin Finansmanlar İhtiyaç Finansmanları Konut Finansmanları Araç Finansmanları Alışveriş Finansmanları İhtiyaç Finansmanları Sürdürülebilir Finansmanlar İhtiyaç Finansmanları Hac-Umre Finansmanı Hac ve umre ziyaretleriniz için finansman arayışınızda cazip geri ödeme koşulları ile Kuveyt Türk her daim sizinle!']; D=absent:None |
| `kuveyt-turk--kampanya-arsivi-bisiklet-finansmaninda-enerji-tasarrufu-haftasina-ozel-419-kar-o` | `finansman_tutari` | A=value:{'value': 13882.47, 'currency': 'TRY'}; B=value:{'value': 13.88247, 'currency': 'TRY'} |
| `kuveyt-turk--kampanya-arsivi-business-plus-karttan-vade-farksiz-3-taksit-imkani` | `finansman_tutari` | A=absent:None; B=value:{'value': 10000.0, 'currency': 'TRY'}; C=absent:None; D=absent:None |
| `kuveyt-turk--kampanya-arsivi-business-plus-karttan-vade-farksiz-3-taksit-imkani` | `taksit_sayisi` | A=value:3; B=value:23; C=value:3; D=value:3 |
| `kuveyt-turk--kampanya-arsivi-business-plus-karttan-vade-farksiz-3-taksit-imkani` | `masraf_durumu` | A=absent:None; B=value:{'amount': 0.0, 'has_fee': False}; C=value:{'has_fee': False, 'amount': 0.0}; D=absent:None |
| `kuveyt-turk--kampanya-arsivi-business-plus-karttan-vade-farksiz-3-taksit-imkani` | `odul_miktari` | A=absent:None; B=absent:None; C=absent:None; D=value:{'value': 10000.0, 'currency': 'TRY'} |
| `kuveyt-turk--kampanya-arsivi-business-plus-karttan-vade-farksiz-3-taksit-imkani` | `kampanya_suresi` | A=value:'2023-08-31'; B=value:'2023-08-31'; C=value:'2023-07-01'; D=value:'2023-08-31' |
| `kuveyt-turk--kampanya-arsivi-business-plus-karttan-vade-farksiz-3-taksit-imkani` | `kampanya_kosullari` | A=value:['Kampanyaya sadece Business Plus kartlarımız dahildir.', 'İşlemden önce kart üzerindeki taksit ve öteleme sayısının 0 olması gerekmektedir.', 'Kuveyt Türk önceden haber vermeden kampanya koşullarında değişiklik yapabilir ya da kampanyayı sonlandırabilir.']; B=value:['Kampanyaya sadece Business Plus kartlarımız dahildir.', 'İşlemden önce kart üzerindeki taksit ve öteleme sayısının 0 olması gerekmektedir.', 'Kuveyt Türk önceden haber vermeden kampanya koşullarında değişiklik yapabilir ya da kampanyayı sonlandırabilir.']; C=value:['Kampanyaya sadece Business Plus kartlarımız dahildir.', '10.000₺ ile 50.000₺ arası tek çekim işlemler için geçerlidir.', 'Bir müşteri kampanya süresince en fazla 1 işlemini taksitlendirebilir.', 'İşlemden önce kart üzerindeki taksit ve öteleme sayısının 0 olması gerekmektedir.']; D=value:['Kampanyaya sadece Business Plus kartlarımız dahildir.', 'İşlemden önce kart üzerindeki taksit ve öteleme sayısının 0 olması gerekmektedir.', 'Kuveyt Türk önceden haber vermeden kampanya koşullarında değişiklik yapabilir ya da kampanyayı sonlandırabilir.'] |
| `kuveyt-turk--kampanya-arsivi-business-plus-karttan-vade-farksiz-3-taksit-imkani` | `hedef_kitle` | A=absent:None; C=unclear:None; D=absent:None |
| `kuveyt-turk--kampanya-arsivi-hepsiburada-alisveris-finansmaninda-enerji-tasarrufu-haftasina-o` | `campaign_type` | A=value:'Finansman'; B=value:'Alışveriş Puanı' |
| `kuveyt-turk--kampanya-arsivi-hepsiburada-alisveris-finansmaninda-enerji-tasarrufu-haftasina-o` | `finansman_tutari` | A=value:{'value': 13682.22, 'currency': 'TRY'}; B=value:{'value': 13.68222, 'currency': 'TRY'} |
| `kuveyt-turk--kart-kampanyalari-dogtas-grubunda-5-aya-varan-taksit-imkani` | `vade_ay` | A=value:5; B=absent:None |
| `kuveyt-turk--kart-kampanyalari-saglam-business-karttan-dev-kampanya-3-ay-erteleme-ve-349-oran` | `vade_ay` | A=value:3; B=absent:None |
| `kuveyt-turk--kart-kampanyalari-saglam-business-karttan-dev-kampanya-3-ay-erteleme-ve-349-oran` | `odul_miktari` | A=value:{'value': 300.0, 'currency': 'TRY'}; B=absent:None |
| `kuveyt-turk--katilma-hesaplari-ara-donem-kar-payi-odemeli-hesaplar` | `vade_ay` | A=value:6; B=absent:None |
| `kuveyt-turk--katilma-hesaplari-birikimli-katilma-hesabi` | `campaign_type` | A=value:'Konut Finansmanı'; B=value:'Yatırım Ürünü' |
| `kuveyt-turk--leasing-leasing-sureci-ve-hesaplama-araci` | `campaign_type` | A=value:'Finansman'; B=value:'Finansman'; D=absent:None |
| `kuveyt-turk--leasing-leasing-sureci-ve-hesaplama-araci` | `kampanya_kosullari` | A=absent:None; B=value:['Teklifi uygun bulduğunuz takdirde proforma fatura, başvuru formu ve diğer gerekli evrakları şubemize teslim edin.']; C=value:['Teklifi uygun bulduğunuz takdirde proforma fatura, başvuru formu ve diğer gerekli evrakları şubemize teslim edin.']; D=value:['leasing'] |
| `kuveyt-turk--medium-bireysel-finansman-talebi-onay-ve-bilgilendirme-fo-4013-pdf` | `campaign_type` | A=absent:None; B=value:'Finansman' |
| `tom-katilim--hesaplama-araclari` | `kar_payi_orani` | A=absent:None; C=value:0.0399; D=absent:None |
| `tom-katilim--hesaplama-araclari` | `finansman_tutari` | A=value:{'value': 150000, 'currency': 'TRY'}; B=value:{'value': 5000.0, 'currency': 'TRY'}; C=value:{'value': 150000.0, 'currency': 'TRY'}; D=value:{'value': 150000.0, 'currency': 'TRY'} |
| `tom-katilim--hesaplama-araclari` | `vade_ay` | A=value:36; B=value:36; C=value:1; D=value:1 |
| `tom-katilim--hesaplama-araclari` | `taksit_sayisi` | A=absent:None; C=value:36; D=absent:None |
| `tom-katilim--hesaplama-araclari` | `tahsis_ucreti` | A=absent:None; B=value:{'value': 0.5, 'currency': 'TRY'}; C=value:{'value': 0.5, 'currency': 'TRY'}; D=absent:None |
| `tom-katilim--kampanyalar-giyim-alisverislerinde-kampanya` | `vade_ay` | A=value:6; B=absent:None |
| `tom-katilim--kampanyalar-giyim-alisverislerinde-kampanya` | `taksit_sayisi` | A=value:3; B=value:6 |
| `turkiye-emlak-katilim--bireysel-hesaplar` | `kar_payi_orani` | A=unclear:None; B=absent:None; C=absent:None; D=absent:None |
| `turkiye-emlak-katilim--bireysel-hesaplar` | `vade_ay` | A=unclear:None; B=value:1; C=value:1; D=value:1 |
| `turkiye-emlak-katilim--bireysel-hesaplar` | `kampanya_kosullari` | A=absent:None; B=value:['["Katılma Hesabı en az 1 ay vadeli olarak açılır. Zümrüt Katılma Hesabı 3 milyon TL ve üzeri birikimi olan müşteriler içindir. Çeyiz Hesabı 3 yıl düzenli birikimle %25\'e kadar, Konut Hesabı ise %20\'ye varan devlet katkısı sunar."]\u2060']; C=absent:None; D=absent:None |
| `turkiye-emlak-katilim--finansmanlar-ihtiyac-finansmani` | `finansman_tutari` | A=unclear:None; B=value:{'currency': 'TRY', 'value': 30000.0}; C=absent:None; D=absent:None |
| `turkiye-emlak-katilim--finansmanlar-ihtiyac-finansmani` | `taksit_sayisi` | A=unclear:None; B=value:12; C=value:12; D=absent:None |
| `turkiye-emlak-katilim--finansmanlar-ihtiyac-finansmani` | `tahsis_ucreti` | A=value:{'value': 30000.0, 'currency': 'TRY'}; B=value:{'currency': 'TRY', 'value': 157.5}; C=value:{'value': 30000.0, 'currency': 'TRY'}; D=value:{'currency': 'TRY', 'value': 157.5} |
| `turkiye-emlak-katilim--finansmanlar-ihtiyac-finansmani` | `masraf_durumu` | A=value:{'has_fee': True, 'amount': 30000.0}; B=value:{'amount': 157.5, 'has_fee': True}; C=value:{'amount': 157.5, 'has_fee': True} |
| `turkiye-emlak-katilim--finansmanlar-ihtiyac-finansmani` | `kampanya_suresi` | A=absent:None; B=value:'2001-11-22'; C=value:'2001-11-22'; D=value:'2001-11-22' |
| `turkiye-emlak-katilim--kampanya-market-alisverislerinize-1500-tl-parafpara-hediye` | `campaign_type` | A=value:'Alışveriş Puanı'; B=value:'Kart'; C=value:'Alışveriş Puanı'; D=value:'Alışveriş Puanı' |
| `turkiye-emlak-katilim--kampanya-market-alisverislerinize-1500-tl-parafpara-hediye` | `alisveris_puani` | A=value:{'kind': 'points', 'value': 150}; D=value:{'kind': 'points', 'value': 1500.0} |
| `turkiye-emlak-katilim--kampanya-market-alisverislerinize-1500-tl-parafpara-hediye` | `hedef_kitle` | A=absent:None; C=unclear:None; D=absent:None |
| `turkiye-emlak-katilim--kampanya-paraf-ile-hepsiburadada-pesin-fiyatina-9-aya-varan-taksit-firsati` | `campaign_type` | A=value:'Kart'; B=value:'Kart'; C=unclear:None; D=value:'Kart' |
| `turkiye-emlak-katilim--kampanya-paraf-ile-hepsiburadada-pesin-fiyatina-9-aya-varan-taksit-firsati` | `taksit_sayisi` | A=value:6; B=value:9 |
| `turkiye-emlak-katilim--kampanya-paraf-ile-hepsiburadada-pesin-fiyatina-9-aya-varan-taksit-firsati` | `kampanya_kosullari` | A=value:['Peşin fiyatına 6 taksit kampanyası sadece seçili ürünler özelinde geçerlidir.', 'Kampanyadan faydalanmak için ödeme esnasında ilgili taksitin seçilmesi gerekmektedir.', 'Hepsiburada belirli kategorilerde yer alan ürünleri peşin fiyatına taksit uygulamasından hariç tutabilir.', 'Hepsiburada satıcılı Xiaomi (Tablet hariç) markalı ürünler vade farksız taksit kampanyalarına dahil değildir.', 'Türkiye Emlak Katılım Bankası A.Ş. kampanya koşullarının tamamında değişiklik yapma ve/veya kampanyayı durdurma hakkını saklı tutar. × Your browser does not support the audio element.']; B=value:['100 TL ve üzeri alışverişlerde vade farksız taksit imkanı sunulur. Peşin fiyatına altı taksit kampanyası sadece seçili ürünler üzerinde geçerlidir. Hepsiburada premium müşterilerine özel 10.000 TL ve üzeri alışverişlerinde 9 taksit uygulanır ve BDDK kısıtlamaları gereği gıda, akaryakıt, kuyum, kozmetik ve benzeri harcamalarda taksit uygulanamaz.']; C=value:['Peşin fiyatına 6 taksit kampanyası sadece seçili ürünler özelinde geçerlidir.', 'Kampanyadan faydalanmak için ödeme esnasında ilgili taksitin seçilmesi gerekmektedir.', 'Hepsiburada belirli kategorilerde yer alan ürünleri peşin fiyatına taksit uygulamasından hariç tutabilir.', 'Hepsiburada satıcılı Xiaomi (Tablet hariç) markalı ürünler vade farksız taksit kampanyalarına dahil değildir.', 'Türkiye Emlak Katılım Bankası A.Ş. kampanya koşullarının tamamında değişiklik yapma ve/veya kampanyayı durdurma hakkını saklı tutar. × Your browser does not support the audio element.']; D=value:['Peşin fiyatına 6 taksit kampanyası sadece seçili ürünler özelinde geçerlidir.', 'Kampanyadan faydalanmak için ödeme esnasında ilgili taksitin seçilmesi gerekmektedir.', 'Hepsiburada belirli kategorilerde yer alan ürünleri peşin fiyatına taksit uygulamasından hariç tutabilir.', 'Hepsiburada satıcılı Xiaomi (Tablet hariç) markalı ürünler vade farksız taksit kampanyalarına dahil değildir.', 'Türkiye Emlak Katılım Bankası A.Ş. kampanya koşullarının tamamında değişiklik yapma ve/veya kampanyayı durdurma hakkını saklı tutar. × Your browser does not support the audio element.'] |
| `turkiye-emlak-katilim--kampanya-paraf-ile-hepsiburadada-pesin-fiyatina-9-aya-varan-taksit-firsati` | `hedef_kitle` | A=absent:None; C=unclear:None; D=absent:None |
| `turkiye-emlak-katilim--kartlar-kredi-karti` | `kampanya_suresi` | A=value:'2026-01-01'; B=absent:None |
| `turkiye-emlak-katilim--katilma-hesaplari-zumrut-katilma-hesabi` | `vade_ay` | A=value:6; B=value:12 |
| `turkiye-emlak-katilim--qr-kredi-karti-uyelik-sozlesmesi-pdf` | `campaign_type` | A=absent:None; B=value:'Kart' |
| `turkiye-finans--katilma-hesaplari-e-katilma-hesabi` | `vade_ay` | A=value:6; B=value:15 |
| `turkiye-finans--kobi-dijital-taksitli-ticari-finansman-destegi` | `campaign_type` | A=value:'Yatırım Ürünü'; B=value:'Finansman' |
| `turkiye-finans--konut-finansmani-konut-finansmani` | `kar_payi_orani` | A=unclear:None; B=value:{'max': 4.42, 'min': 2.95}; C=value:{'min': 2.95, 'max': 4.42}; D=value:{'min': 2.95, 'max': 4.42} |
| `turkiye-finans--konut-finansmani-konut-finansmani` | `finansman_tutari` | A=value:{'value': 20000000, 'currency': 'TRY'}; B=absent:None; C=absent:None; D=absent:None |
| `turkiye-finans--konut-finansmani-konut-finansmani` | `taksit_sayisi` | A=value:120; B=value:120; C=absent:None; D=absent:None |
| `turkiye-finans--konut-finansmani-konut-finansmani` | `tahsis_ucreti` | A=unclear:None; C=absent:None; D=absent:None |
| `turkiye-finans--konut-finansmani-konut-finansmani` | `masraf_durumu` | A=value:{'has_fee': True, 'amount': 20000}; B=value:{'amount': 500.0, 'has_fee': True}; C=value:{'amount': 20000.0, 'has_fee': True}; D=value:{'has_fee': True, 'amount': 500.0} |
| `turkiye-finans--konut-finansmani-konut-finansmani` | `kampanya_kosullari` | A=absent:None; B=value:['\u2060["Maksimum vade 120 aydır. Kullanılabilecek finansman tutarı konutun ekspertiz değerine, enerji sınıfına ve tüketicinin ilk/mevcut konut durumuna göre belirlenir. Yedek Hesap, DASK, Konut Sigortası, Ferdi Kaza Sigortası ve Otomatik Fatura Talimatı ürünlerinin finansmanla birlikte alınması gerekmektedir."]\u2060']; C=value:["Türkiye Finans'ın 100'ünde Gelecek Olan 5 Üyesi Cumhuriyetimizin Unutulmaz 100'leri Bankacılığın Tarihçesi ve Türkiye'de Bankacılık Türleri Dijital Dünyada Güvenlik İçin Temel İpuçları Avrupa Yeşil Mutabakatı: Sürdürülebilir Ekonomiler İçin Yol Haritası 2023'ü Geride Bırakırken DASK - Zorunlu Deprem Sigortası Nedir?", 'Türkiye Finans Konut Finansmanı (bankacılık kanununa göre konut kredisi), uygun koşullarda ev sahibi olmanız için sunulan finansman desteğidir.', 'Konut Finansmanı (Konut Kredisi)* çözümlerimizden bütçenize göre dilediğinizi seçebilir, uygun ödeme koşulları ile zorlanmadan ev sahibi olabilirsiniz.', 'Banka gerekli gördüğü durumlarda kefil ve ek belge isteme hakkına sahiptir.', 'Maliyet tablosu hesaplamasında yer alan kar oranları; Yedek Hesap, DASK, Finansman Ferdi Kaza Sigortası, Konut Sigortası, Otomatik Fatura Ödeme Talimatı ürünlerinin tamamının finansman başvurusu ile birlikte alınması şartıyla uygulanmaktadır.', "Finansmanın maksimum vadesi 120 ay olup, tahsis ücreti vergiler hariç finansman tutarının binde 5'i oranındadır.", 'Ekspertiz ücreti minimum maliyetler üzerinden hesaplanmış olup Ekspertiz ücreti Resmi Kurumlara ödenen harç miktarına, taşınmazın alanına, mevcut durumuna ve bulunduğu lokasyona göre değişebilmektedir.Gayrimenkulün bulunduğu lokasyona bağlı olarak ekspertiz firmasına ödenen meblağ arttığında, müşteriden tahsil edilecek ekspertiz ücreti de artacaktır.', 'Mortgage finansmanı için gerekli belgeler nelerdir?']; D=absent:None |
| `turkiye-finans--konut-finansmani-konut-finansmani` | `hedef_kitle` | A=absent:None; C=absent:None; D=value:['belirli_segment', 'maas_musterisi', 'yeni_musteri'] |
| `turkiye-finans--tasit-finansmani-tasit-finansmani-2` | `kar_payi_orani` | A=absent:None; B=value:{'max': 4.27, 'min': 3.42}; C=value:{'min': 3.42, 'max': 4.27}; D=value:{'min': 3.42, 'max': 4.27} |
| `turkiye-finans--tasit-finansmani-tasit-finansmani-2` | `finansman_tutari` | A=value:{'value': 2000000, 'currency': 'TRY'}; B=value:{'value': 20.0, 'currency': 'TRY'}; C=value:{'value': 400000.0, 'currency': 'TRY'}; D=absent:None |
| `turkiye-finans--tasit-finansmani-tasit-finansmani-2` | `vade_ay` | A=absent:None; B=value:1248; C=value:48; D=value:348 |
| `turkiye-finans--tasit-finansmani-tasit-finansmani-2` | `taksit_sayisi` | A=absent:None; C=value:48; D=absent:None |
| `turkiye-finans--tasit-finansmani-tasit-finansmani-2` | `kampanya_kosullari` | A=absent:None; B=value:['["0 km araçlarda proforma fatura, 2. el araçlarda kasko değeri baz alınır. Araç değerine göre azami 48 ay vade imkanı sunulur. En fazla 7 yaşına kadar olan taşıtlar finanse edilir. Kasko ve Finansman Güvence Sigortası ürünlerinin birlikte alınması şartıyla uygun kâr oranları uygulanır."]\u2060']; D=absent:None |
| `turkiye-finans--tasit-finansmani-tasit-finansmani-2` | `hedef_kitle` | A=absent:None; D=value:['belirli_segment', 'maas_musterisi', 'mevcut_musteri', 'yeni_musteri'] |
| `vakif-katilim--bireysel-bankacilik-vakif-katilim-ile-altin-gunler` | `campaign_type` | A=unclear:None; B=value:'Yatırım Ürünü' |
| `vakif-katilim--detay-dijitalden-musteri-ol-hisse-senedi-islemlerinde-75-komisyon-indirimi-kazan` | `vade_ay` | A=absent:None; B=absent:None; C=value:3; D=absent:None |
| `vakif-katilim--detay-dijitalden-musteri-ol-hisse-senedi-islemlerinde-75-komisyon-indirimi-kazan` | `taksit_sayisi` | A=unclear:None; B=absent:None; C=absent:None; D=absent:None |
| `vakif-katilim--detay-dijitalden-musteri-ol-hisse-senedi-islemlerinde-75-komisyon-indirimi-kazan` | `odul_miktari` | A=value:{'value': 75.0, 'currency': 'TRY'}; B=absent:None; C=absent:None; D=absent:None |
| `vakif-katilim--detay-dijitalden-musteri-ol-hisse-senedi-islemlerinde-75-komisyon-indirimi-kazan` | `kampanya_suresi` | A=value:'2021-12-31'; B=value:'2021-12-14'; C=value:'2027-12-31'; D=value:'2027-12-31' |
| `vakif-katilim--detay-espressolab-hediye-kahve-kampanyasi` | `campaign_type` | A=value:'Yeni Müşteri'; C=value:'Yeni Müşteri'; D=absent:None |
| `vakif-katilim--detay-espressolab-hediye-kahve-kampanyasi` | `taksit_sayisi` | A=unclear:None; B=absent:None; C=absent:None; D=absent:None |
| `vakif-katilim--detay-espressolab-hediye-kahve-kampanyasi` | `odul_miktari` | A=value:{'value': 2.0, 'currency': 'TRY'}; B=value:{'value': 2.0, 'currency': 'TRY'}; C=value:{'value': 2.0, 'currency': 'TRY'}; D=absent:None |
| `vakif-katilim--detay-espressolab-hediye-kahve-kampanyasi` | `indirim_orani` | A=value:15.0; B=value:15.0; C=value:15.0; D=absent:None |
| `vakif-katilim--detay-espressolab-hediye-kahve-kampanyasi` | `kampanya_suresi` | A=value:'2026-01-31'; B=value:'2026-01-01'; C=value:'2026-12-31'; D=value:'2026-12-31' |
| `vakif-katilim--detay-espressolab-hediye-kahve-kampanyasi` | `kampanya_kosullari` | A=value:['Kampanya Şartları Espressolab Hediye Kahve Kodu Nasıl Kazanılır? "KAHVE" davet koduyla Vakıf Katılım Mobil Şube üzerinden müşteri olanlara Espressolab mobil uygulamasında kullanabilecekleri 2 adet hediye kahve kodu iletilecektir.', 'Kampanya katılımı ilk 1.000 kişi için geçerlidir.', 'Vakıf Katılım Bankası AŞ ve Espressolab, önceden haber vermeksizin kampanyayı durdurma, sona erdirme, kampanya kapsamını ve koşullarını değiştirme hakkını saklı tutar.']; B=value:['Kampanya Şartları Espressolab Hediye Kahve Kodu Nasıl Kazanılır? "KAHVE" davet koduyla Vakıf Katılım Mobil Şube üzerinden müşteri olanlara Espressolab mobil uygulamasında kullanabilecekleri 2 adet hediye kahve kodu iletilecektir.', 'Kampanya katılımı ilk 1.000 kişi için geçerlidir.']; C=value:['Kampanya Şartları Espressolab Hediye Kahve Kodu Nasıl Kazanılır? "KAHVE" davet koduyla Vakıf Katılım Mobil Şube üzerinden müşteri olanlara Espressolab mobil uygulamasında kullanabilecekleri 2 adet hediye kahve kodu iletilecektir.', 'Kampanya katılımı ilk 1.000 kişi için geçerlidir.', 'Vakıf Katılım Bankası AŞ ve Espressolab, önceden haber vermeksizin kampanyayı durdurma, sona erdirme, kampanya kapsamını ve koşullarını değiştirme hakkını saklı tutar.']; D=value:['Kampanya Şartları Espressolab Hediye Kahve Kodu Nasıl Kazanılır? "KAHVE" davet koduyla Vakıf Katılım Mobil Şube üzerinden müşteri olanlara Espressolab mobil uygulamasında kullanabilecekleri 2 adet hediye kahve kodu iletilecektir.', 'Kampanya katılımı ilk 1.000 kişi için geçerlidir.', 'Vakıf Katılım Bankası AŞ ve Espressolab, önceden haber vermeksizin kampanyayı durdurma, sona erdirme, kampanya kapsamını ve koşullarını değiştirme hakkını saklı tutar.'] |
| `vakif-katilim--detay-espressolab-hediye-kahve-kampanyasi` | `hedef_kitle` | A=value:['yeni_musteri']; B=value:['yeni_musteri']; C=value:['yeni_musteri']; D=absent:None |
| `vakif-katilim--detay-vakif-katilim-aile-yili-paketi` | `campaign_type` | A=unclear:None; B=absent:None |
| `vakif-katilim--finansmanlar-kentsel-donusum-finansmani` | `campaign_type` | A=value:'Finansman'; B=value:'Konut Finansmanı'; C=value:'Finansman'; D=value:'Finansman' |
| `vakif-katilim--finansmanlar-kentsel-donusum-finansmani` | `kar_payi_orani` | A=absent:None; B=value:3.47; C=value:3.47; D=absent:None |
| `vakif-katilim--finansmanlar-kentsel-donusum-finansmani` | `finansman_tutari` | A=value:{'value': 3000000, 'currency': 'TRY'}; B=value:{'value': 1250000.0, 'currency': 'TRY'}; C=value:{'value': 1250000.0, 'currency': 'TRY'}; D=value:{'value': 3000000.0, 'currency': 'TRY'} |
| `vakif-katilim--finansmanlar-kentsel-donusum-finansmani` | `hedef_kitle` | A=absent:None; C=unclear:None; D=absent:None |
| `vakif-katilim--finansmanlar-konut-finansmani-2` | `kampanya_kosullari` | A=absent:None; B=value:['Konut finansmanı başvurusu için gerekli form doldurulduktan sonra bankamız sizinle iletişime geçecektir.', 'Evin değerinin ne kadarına finansman çıkacağı, bankanın belirlediği limitler ve finansman koşullarına göre belirlenir.']; C=value:['Konut finansmanı']; D=absent:None |
| `vakif-katilim--finansmanlar-konut-finansmani-2` | `hedef_kitle` | A=absent:None; B=absent:None; C=unclear:None; D=absent:None |
| `vakif-katilim--finansmanlar-motosiklet-finansmani` | `campaign_type` | A=value:'Finansman'; B=value:'Taşıt Finansmanı' |
| `vakif-katilim--kendim-icin-finansmanlar` | `campaign_type` | A=value:'Konut Finansmanı'; B=absent:None |
| `vakif-katilim--kobi-destekli-finansmanlar-kosgeb-destekli-finansman` | `vade_ay` | A=value:36; B=absent:None |
| `vakif-katilim--nakdi-finansmanlar-is-yeri-finansmani` | `campaign_type` | A=value:'İhtiyaç Finansmanı'; B=value:'Konut Finansmanı' |
| `ziraat-katilim--kart-kampanyalari-mobilya-alisverisinize-1500-tl-bankkart-lira` | `campaign_type` | A=value:'Kart'; B=value:'Alışveriş Puanı' |
| `ziraat-katilim--kart-kampanyalari-mobilya-alisverisinize-1500-tl-bankkart-lira` | `taksit_sayisi` | A=value:5; B=absent:None |

## Belirsiz (unclear) alanlar

Metrik hesabının DIŞINDA tutulur.

| Belge | Alan |
|---|---|
| `albaraka--detay-dijital-musterilere-ozel-pratik-finansman-kart` | `hedef_kitle` |
| `albaraka--detay-vade-farksiz-kampanyasi` | `finansman_tutari` |
| `albaraka--detay-vade-farksiz-kampanyasi` | `hedef_kitle` |
| `albaraka--detay-vade-farksiz-kampanyasi` | `kampanya_suresi` |
| `albaraka--detay-vade-farksiz-kampanyasi` | `tahsis_ucreti` |
| `albaraka--detay-vade-farksiz-kampanyasi` | `taksit_sayisi` |
| `albaraka--eviniz-icin-prefabrik` | `vade_ay` |
| `albaraka--formlar-altin-hesaplarindan-donusumun-desteklenmesi-tl-katilma-hesabi-bilgilendi` | `kampanya_kosullari` |
| `albaraka--formlar-genel-kredi-sozlesmesi-ucret-bilgilendirme-formu-pdf` | `masraf_durumu` |
| `albaraka--gecmis-tarihli-aracfinansmanitalep-onayveucretbilgilendirmeformu-pdf` | `kar_payi_orani` |
| `albaraka--gecmis-tarihli-aracfinansmanitalep-onayveucretbilgilendirmeformu-pdf` | `masraf_durumu` |
| `albaraka--ihtiyac-saglik-harcamalariniz-icin` | `kampanya_kosullari` |
| `albaraka--tarim-bankaciligi-diger-finansmanlar` | `kampanya_kosullari` |
| `albaraka--tasit-finansmani-togg-finansmani` | `finansman_tutari` |
| `albaraka--tasit-finansmani-togg-finansmani` | `kar_payi_orani` |
| `albaraka--tatiliniz-icin-devre-mulk` | `kampanya_kosullari` |
| `albaraka--tatiliniz-icin-devre-mulk` | `vade_ay` |
| `albaraka--tr-urun-ve-hizmet-ucretleri` | `kampanya_kosullari` |
| `albaraka--tr-urun-ve-hizmet-ucretleri` | `masraf_durumu` |
| `dunya-katilim--katilma-hesaplari-gunes-katilma-hesabi` | `vade_ay` |
| `dunya-katilim--kendim-icin-altin-bankaciligi` | `kampanya_kosullari` |
| `dunya-katilim--kendim-icin-altin-bankaciligi` | `vade_ay` |
| `dunya-katilim--kredi-kartlari-paraf-platinum-kredi-karti` | `kampanya_kosullari` |
| `dunya-katilim--kredi-kartlari-paraf-platinum-kredi-karti` | `masraf_durumu` |
| `kuveyt-turk--altin-hesaplari-altina-altin-katilma-hesabi` | `kar_payi_orani` |
| `kuveyt-turk--altin-hesaplari-altina-altin-katilma-hesabi` | `vade_ay` |
| `kuveyt-turk--finansmanlar-ihtiyac-finansmanlari` | `kampanya_kosullari` |
| `kuveyt-turk--finansmanlar-ihtiyac-finansmanlari` | `vade_ay` |
| `kuveyt-turk--kampanya-arsivi-bisiklet-finansmaninda-enerji-tasarrufu-haftasina-ozel-419-kar-o` | `finansman_tutari` |
| `kuveyt-turk--kampanya-arsivi-business-plus-karttan-vade-farksiz-3-taksit-imkani` | `finansman_tutari` |
| `kuveyt-turk--kampanya-arsivi-business-plus-karttan-vade-farksiz-3-taksit-imkani` | `hedef_kitle` |
| `kuveyt-turk--kampanya-arsivi-business-plus-karttan-vade-farksiz-3-taksit-imkani` | `kampanya_kosullari` |
| `kuveyt-turk--kampanya-arsivi-business-plus-karttan-vade-farksiz-3-taksit-imkani` | `kampanya_suresi` |
| `kuveyt-turk--kampanya-arsivi-business-plus-karttan-vade-farksiz-3-taksit-imkani` | `masraf_durumu` |
| `kuveyt-turk--kampanya-arsivi-business-plus-karttan-vade-farksiz-3-taksit-imkani` | `odul_miktari` |
| `kuveyt-turk--kampanya-arsivi-business-plus-karttan-vade-farksiz-3-taksit-imkani` | `taksit_sayisi` |
| `kuveyt-turk--kampanya-arsivi-firma-ortaklari-yatirim-yaparken-mil-kazaniyor-scr` | `odul_miktari` |
| `kuveyt-turk--kampanya-arsivi-hepsiburada-alisveris-finansmaninda-enerji-tasarrufu-haftasina-o` | `finansman_tutari` |
| `kuveyt-turk--kart-kampanyalari-dogtas-grubunda-5-aya-varan-taksit-imkani` | `vade_ay` |
| `kuveyt-turk--kart-kampanyalari-saglam-business-karttan-dev-kampanya-3-ay-erteleme-ve-349-oran` | `odul_miktari` |
| `kuveyt-turk--kart-kampanyalari-saglam-business-karttan-dev-kampanya-3-ay-erteleme-ve-349-oran` | `vade_ay` |
| `kuveyt-turk--katilma-hesaplari-ara-donem-kar-payi-odemeli-hesaplar` | `vade_ay` |
| `kuveyt-turk--leasing-leasing-sureci-ve-hesaplama-araci` | `kampanya_kosullari` |
| `tom-katilim--hesaplama-araclari` | `finansman_tutari` |
| `tom-katilim--hesaplama-araclari` | `kar_payi_orani` |
| `tom-katilim--hesaplama-araclari` | `tahsis_ucreti` |
| `tom-katilim--hesaplama-araclari` | `taksit_sayisi` |
| `tom-katilim--hesaplama-araclari` | `vade_ay` |
| `tom-katilim--kampanyalar-giyim-alisverislerinde-kampanya` | `taksit_sayisi` |
| `tom-katilim--kampanyalar-giyim-alisverislerinde-kampanya` | `vade_ay` |
| `turkiye-emlak-katilim--bireysel-hesaplar` | `kampanya_kosullari` |
| `turkiye-emlak-katilim--bireysel-hesaplar` | `kar_payi_orani` |
| `turkiye-emlak-katilim--bireysel-hesaplar` | `vade_ay` |
| `turkiye-emlak-katilim--finansmanlar-ihtiyac-finansmani` | `finansman_tutari` |
| `turkiye-emlak-katilim--finansmanlar-ihtiyac-finansmani` | `kampanya_suresi` |
| `turkiye-emlak-katilim--finansmanlar-ihtiyac-finansmani` | `masraf_durumu` |
| `turkiye-emlak-katilim--finansmanlar-ihtiyac-finansmani` | `tahsis_ucreti` |
| `turkiye-emlak-katilim--finansmanlar-ihtiyac-finansmani` | `taksit_sayisi` |
| `turkiye-emlak-katilim--kampanya-market-alisverislerinize-1500-tl-parafpara-hediye` | `alisveris_puani` |
| `turkiye-emlak-katilim--kampanya-market-alisverislerinize-1500-tl-parafpara-hediye` | `hedef_kitle` |
| `turkiye-emlak-katilim--kampanya-paraf-ile-hepsiburadada-pesin-fiyatina-9-aya-varan-taksit-firsati` | `hedef_kitle` |
| `turkiye-emlak-katilim--kampanya-paraf-ile-hepsiburadada-pesin-fiyatina-9-aya-varan-taksit-firsati` | `kampanya_kosullari` |
| `turkiye-emlak-katilim--kampanya-paraf-ile-hepsiburadada-pesin-fiyatina-9-aya-varan-taksit-firsati` | `taksit_sayisi` |
| `turkiye-emlak-katilim--kampanya-paraf-ile-secili-e-ticaret-alisverislerinize-2000-tlye-varan-parafpara` | `alisveris_puani` |
| `turkiye-emlak-katilim--kartlar-kredi-karti` | `kampanya_suresi` |
| `turkiye-emlak-katilim--katilma-hesaplari-zumrut-katilma-hesabi` | `vade_ay` |
| `turkiye-emlak-katilim--urun-ve-hizmet-ucretleri-breysel-bankacilik-urun-ve-hzmet-ucretler-2026-tr-pdf` | `vade_ay` |
| `turkiye-finans--bireysel-kar-payi-oranlari` | `vade_ay` |
| `turkiye-finans--katilma-hesaplari-e-katilma-hesabi` | `vade_ay` |
| `turkiye-finans--konut-finansmani-konut-finansmani` | `finansman_tutari` |
| `turkiye-finans--konut-finansmani-konut-finansmani` | `hedef_kitle` |
| `turkiye-finans--konut-finansmani-konut-finansmani` | `kampanya_kosullari` |
| `turkiye-finans--konut-finansmani-konut-finansmani` | `kar_payi_orani` |
| `turkiye-finans--konut-finansmani-konut-finansmani` | `masraf_durumu` |
| `turkiye-finans--konut-finansmani-konut-finansmani` | `tahsis_ucreti` |
| `turkiye-finans--konut-finansmani-konut-finansmani` | `taksit_sayisi` |
| `turkiye-finans--tasit-finansmani-tasit-finansmani-2` | `finansman_tutari` |
| `turkiye-finans--tasit-finansmani-tasit-finansmani-2` | `hedef_kitle` |
| `turkiye-finans--tasit-finansmani-tasit-finansmani-2` | `kampanya_kosullari` |
| `turkiye-finans--tasit-finansmani-tasit-finansmani-2` | `kar_payi_orani` |
| `turkiye-finans--tasit-finansmani-tasit-finansmani-2` | `taksit_sayisi` |
| `turkiye-finans--tasit-finansmani-tasit-finansmani-2` | `vade_ay` |
| `vakif-katilim--detay-dijitalden-musteri-ol-hisse-senedi-islemlerinde-75-komisyon-indirimi-kazan` | `kampanya_suresi` |
| `vakif-katilim--detay-dijitalden-musteri-ol-hisse-senedi-islemlerinde-75-komisyon-indirimi-kazan` | `odul_miktari` |
| `vakif-katilim--detay-dijitalden-musteri-ol-hisse-senedi-islemlerinde-75-komisyon-indirimi-kazan` | `taksit_sayisi` |
| `vakif-katilim--detay-dijitalden-musteri-ol-hisse-senedi-islemlerinde-75-komisyon-indirimi-kazan` | `vade_ay` |
| `vakif-katilim--detay-espressolab-hediye-kahve-kampanyasi` | `hedef_kitle` |
| `vakif-katilim--detay-espressolab-hediye-kahve-kampanyasi` | `indirim_orani` |
| `vakif-katilim--detay-espressolab-hediye-kahve-kampanyasi` | `kampanya_kosullari` |
| `vakif-katilim--detay-espressolab-hediye-kahve-kampanyasi` | `kampanya_suresi` |
| `vakif-katilim--detay-espressolab-hediye-kahve-kampanyasi` | `odul_miktari` |
| `vakif-katilim--detay-espressolab-hediye-kahve-kampanyasi` | `taksit_sayisi` |
| `vakif-katilim--finansmanlar-kentsel-donusum-finansmani` | `finansman_tutari` |
| `vakif-katilim--finansmanlar-kentsel-donusum-finansmani` | `hedef_kitle` |
| `vakif-katilim--finansmanlar-kentsel-donusum-finansmani` | `kar_payi_orani` |
| `vakif-katilim--finansmanlar-konut-finansmani-2` | `hedef_kitle` |
| `vakif-katilim--finansmanlar-konut-finansmani-2` | `kampanya_kosullari` |
| `vakif-katilim--katilma-hesaplari-ara-donem-kar-payi-odemeli-katilma-hesabi-2` | `vade_ay` |
| `vakif-katilim--kobi-destekli-finansmanlar-kosgeb-destekli-finansman` | `vade_ay` |
| `ziraat-katilim--kart-kampanyalari-mobilya-alisverisinize-1500-tl-bankkart-lira` | `taksit_sayisi` |

## Elenen belgeler (kampanya değil)

| Belge | Banka |
|---|---|
| `albaraka--sozlesmeler-bayide-finansman-ihtiyac-aracilik-ve-garantorluk-sozlesmesi-komisyon` | albaraka |
| `dunya-katilim--hizmetler-doviz-transferi-swift` | dunya-katilim |
| `kuveyt-turk--medium-temel-bankacilik-hizmetleri-ucret-degisikliklerine-3444-pdf` | kuveyt-turk |
| `kuveyt-turk--musteri-ol-kampanyalari-mobilden-kuveyt-turklu-olan-esnaf-ve-ciftcilere-22000-tl` | kuveyt-turk |
| `turkiye-finans--kampanyalar-biten-kampanyalar` | turkiye-finans |
| `ziraat-katilim--finansman-urunleri-surdurulebilirlik-temali-bireysel-urunler` | ziraat-katilim |
