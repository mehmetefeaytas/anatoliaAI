# Gold Derleme Raporu

> `scripts/build_gold.py` üretti. Elle düzenlemeyin.

- Çıktı: `data/gold/gold.round1.json`
- SHA-256: `4d53fe6d4d11fb9b3be54b2f3a49fa8d748dba74f33f1e3a12f5e08eb3676616`
- Kayıt: **134**
- Çift anote edilmiş kayıt: **44**
- 12/12 alan karara bağlı (recall ÖLÇÜLEBİLİR): **0**
- Kampanya sayılmayıp elenen belge: **10**
- Çelişki (anotatörler ayrıştı): **11**
- Hakemlik bekleyen kayıt: **11**
- Hakemlikten/şema onarımından geçmiş kayıt (`adjudicated`): **38** — damgalar: `#hakemlik-round1`, `#sema-onarimi-round1`
- Kanıtlı alan (`field_spans`): **129/148** (%87.2)

## Protokol künyesi

| Dosya | Protokol | Boş hücre |
|---|---|---|
| `data/gold/review/round1_A.csv` | **v2** | karar verilmedi — gold'a GİRMEZ |
| `data/gold/review/round1_B.csv` | **v2** | karar verilmedi — gold'a GİRMEZ |
| `data/gold/review/round1_main_C.csv` | **v2** | karar verilmedi — gold'a GİRMEZ |
| `data/gold/review/round1_main_D.csv` | **v2** | karar verilmedi — gold'a GİRMEZ |

- v2'de karar verilmemiş satır: **1936** (A=504, B=500, C=540, D=392)


## Ölçülebilirlik

- **Precision + halüsinasyon oranı:** tüm kayıtlarda ölçülebilir — modelin ürettiği her alan için karar var.
- **Recall:** yalnızca 12/12 kapsanan 0 kayıtta ölçülebilir; diğerlerinde anote edilmemiş alan ile gerçekten olmayan alan ayrılamaz.

## Kanıt (`field_spans`)

- Kanıtlı: **129/148** alan
- Kanıtsız: **19** alan — değer var, belgede birebir geçen alıntısı yok.

> Bu hattın kanıtı `merge_gold_v2` hattınınkiyle **aynı ağırlıkta değildir.** Orada alıntıyı anotatör belgeyi kör okuyarak elle yazdı; burada çıkarıcının kaydettiği konumu anotatör onayladı (`verdict=ok`). İkisi de belgede birebir geçer, ikincisi bağımsız bir gözlem değildir.

> Kanıtsız alanların çoğu `verdict=fix`tir: anotatör değeri düzeltti ama alıntı yazacağı bir sütun yok. Kanonik değeri metinde geri arayıp bir yer bulmak kanıt üretmek değil, **kanıt uydurmak** olurdu.

## Alan bazında

| Alan | değer | kanıtlı | yok (absent) | belirsiz |
|---|---:|---:|---:|---:|
| `kar_payi_orani` | 7 | 6 | 10 | 0 |
| `finansman_tutari` | 22 | 15 | 5 | 3 |
| `vade_ay` | 33 | 27 | 30 | 4 |
| `taksit_sayisi` | 16 | 16 | 2 | 0 |
| `tahsis_ucreti` | 0 | 0 | 0 | 0 |
| `masraf_durumu` | 5 | 2 | 0 | 0 |
| `odul_miktari` | 2 | 2 | 5 | 1 |
| `indirim_orani` | 0 | 0 | 0 | 0 |
| `alisveris_puani` | 2 | 2 | 0 | 1 |
| `kampanya_suresi` | 52 | 51 | 6 | 0 |
| `kampanya_kosullari` | 6 | 6 | 2 | 2 |
| `hedef_kitle` | 3 | 2 | 0 | 0 |

### Kanıtsız alanlar — kapatılacak iş listesi

| Belge | Alan |
|---|---|
| `albaraka--detay-dijital-musterilere-ozel-pratik-finansman-kart` | `finansman_tutari` |
| `albaraka--detay-dijital-musterilere-ozel-pratik-finansman-kart` | `hedef_kitle` |
| `albaraka--detay-dijital-musterilere-ozel-pratik-finansman-kart` | `kar_payi_orani` |
| `albaraka--detay-dijital-musterilere-ozel-pratik-finansman-kart` | `vade_ay` |
| `albaraka--eviniz-icin-prefabrik` | `vade_ay` |
| `albaraka--gecmis-tarihli-aracfinansmanitalep-onayveucretbilgilendirmeformu-pdf` | `masraf_durumu` |
| `albaraka--tatiliniz-icin-devre-mulk` | `vade_ay` |
| `albaraka--tr-urun-ve-hizmet-ucretleri` | `masraf_durumu` |
| `dunya-katilim--kredi-kartlari-paraf-platinum-kredi-karti` | `masraf_durumu` |
| `hayat-finans--hesaplar-avantajli-hesap` | `finansman_tutari` |
| `tom-katilim--urunlerimiz` | `finansman_tutari` |
| `turkiye-emlak-katilim--katilma-hesaplari-zumrut-katilma-hesabi` | `vade_ay` |
| `turkiye-finans--bireysel-gunluk-hesap` | `finansman_tutari` |
| `turkiye-finans--bireysel-urun-hizmet-ucretleri` | `vade_ay` |
| `turkiye-finans--kampanyalar-turkiye-finans-avantajlariyla-mobilden-tanis` | `finansman_tutari` |
| `turkiye-finans--kampanyalar-turkiye-finans-avantajlariyla-mobilden-tanis` | `kampanya_suresi` |
| `turkiye-finans--katilma-hesaplari-e-katilma-hesabi` | `vade_ay` |
| `turkiye-finans--kobi-kobi-icin-gunluk-hesap` | `finansman_tutari` |
| `vakif-katilim--detay-igdas-finansman-kampanyasi` | `finansman_tutari` |

## Zor-vaka etiketleri

| Etiket | Kayıt |
|---|---:|
| `kosullu_aralik` | 2 |
| `terminoloji` | 1 |

## Çelişkiler — HAKEMLİK GEREKİYOR

| Belge | Alan | Kararlar |
|---|---|---|
| `albaraka--formlar-altin-hesaplarindan-donusumun-desteklenmesi-tl-katilma-hesabi-bilgilendi` | `kampanya_kosullari` | A=absent:None; B=value:["Vergi kesintileri, Katılma Hesabı'nın açılış/vade yenileme tarihinde ilgili vade için geçerli olan cari vergi oranları üzerinden hesaplanacağı, 8.", "Müşteri, katılma hesaplarının; Banka'nın herhangi bir oran veya tutarda getiri taahhüdü bulunmadığı, bu bakımdan Banka'nın asgari de olsa getiri taahhüdü/garantisi olmayan, karşılığında hesap sahibine önceden belirlenmiş herhangi bir getiri ödenmeyen ve anaparanın aynen geri ödenmesi garanti edilmeyen hesaplar olduğunu bildiğini, 10."] |
| `albaraka--gecmis-tarihli-aracfinansmanitalep-onayveucretbilgilendirmeformu-pdf` | `campaign_type` | A=absent:None; B=value:'Finansman' |
| `albaraka--tarim-bankaciligi-diger-finansmanlar` | `campaign_type` | A=value:'Finansman'; B=value:'İhtiyaç Finansmanı' |
| `albaraka--tatiliniz-icin-devre-mulk` | `kampanya_kosullari` | A=value:['Albaraka Mobil Mobil Bankacılık Aç Devre Mülk Anasayfa Bireysel Finansmanlar İhtiyaç Finansmanı Tatiliniz İçin Devre Mülk Seyahat Devre Mülk Devre Tatil Hemen Başvur Devre mülkler tapu kaydı gerektiren ve her yıl belirli dönemlerde asgari 15 gün süreli konaklama imkânı veren mülklerdir.']; B=absent:None |
| `albaraka--tr-urun-ve-hizmet-ucretleri` | `campaign_type` | A=value:'Yatırım Ürünü'; B=value:'Finansman' |
| `kuveyt-turk--kampanya-arsivi-bisiklet-finansmaninda-enerji-tasarrufu-haftasina-ozel-419-kar-o` | `finansman_tutari` | A=value:{'value': 13882.47, 'currency': 'TRY'}; B=value:{'currency': 'TRY', 'value': 13.88247} |
| `kuveyt-turk--kampanya-arsivi-hepsiburada-alisveris-finansmaninda-enerji-tasarrufu-haftasina-o` | `finansman_tutari` | A=value:{'value': 13682.22, 'currency': 'TRY'}; B=value:{'currency': 'TRY', 'value': 13.68222} |
| `kuveyt-turk--katilma-hesaplari-ara-donem-kar-payi-odemeli-hesaplar` | `vade_ay` | A=value:6; B=absent:None |
| `vakif-katilim--detay-vakif-katilim-aile-yili-paketi` | `campaign_type` | A=unclear:None; B=absent:None |
| `vakif-katilim--nakdi-finansmanlar-is-yeri-finansmani` | `campaign_type` | A=value:'İhtiyaç Finansmanı'; B=value:'Konut Finansmanı' |
| `ziraat-katilim--kart-kampanyalari-troy-kartla-drda-1000-tlye-varan-indirim` | `finansman_tutari` | A=absent:None; B=value:{'currency': 'TRY', 'value': 1000.0} |

## Belirsiz (unclear) alanlar

Metrik hesabının DIŞINDA tutulur.

| Belge | Alan |
|---|---|
| `albaraka--formlar-altin-hesaplarindan-donusumun-desteklenmesi-tl-katilma-hesabi-bilgilendi` | `kampanya_kosullari` |
| `albaraka--tatiliniz-icin-devre-mulk` | `kampanya_kosullari` |
| `kuveyt-turk--kampanya-arsivi-bisiklet-finansmaninda-enerji-tasarrufu-haftasina-ozel-419-kar-o` | `finansman_tutari` |
| `kuveyt-turk--kampanya-arsivi-firma-ortaklari-yatirim-yaparken-mil-kazaniyor-scr` | `odul_miktari` |
| `kuveyt-turk--kampanya-arsivi-hepsiburada-alisveris-finansmaninda-enerji-tasarrufu-haftasina-o` | `finansman_tutari` |
| `kuveyt-turk--katilma-hesaplari-ara-donem-kar-payi-odemeli-hesaplar` | `vade_ay` |
| `turkiye-emlak-katilim--kampanya-paraf-ile-secili-e-ticaret-alisverislerinize-2000-tlye-varan-parafpara` | `alisveris_puani` |
| `turkiye-emlak-katilim--urun-ve-hizmet-ucretleri-breysel-bankacilik-urun-ve-hzmet-ucretler-2026-tr-pdf` | `vade_ay` |
| `turkiye-finans--bireysel-kar-payi-oranlari` | `vade_ay` |
| `vakif-katilim--katilma-hesaplari-ara-donem-kar-payi-odemeli-katilma-hesabi-2` | `vade_ay` |
| `ziraat-katilim--kart-kampanyalari-troy-kartla-drda-1000-tlye-varan-indirim` | `finansman_tutari` |

## Elenen belgeler (kampanya değil)

| Belge | Banka |
|---|---|
| `albaraka--formlar-genel-kredi-sozlesmesi-ucret-bilgilendirme-formu-pdf` | albaraka |
| `albaraka--sozlesmeler-bayide-finansman-ihtiyac-aracilik-ve-garantorluk-sozlesmesi-komisyon` | albaraka |
| `dunya-katilim--hizmetler-doviz-transferi-swift` | dunya-katilim |
| `hayat-finans--kampanyalar-hayatfinansla-islem-yaptikca-kazan` | hayat-finans |
| `kuveyt-turk--kampanya-arsivi-kuveyt-turkten-tahsildara-ozel-mil-kampanyasi` | kuveyt-turk |
| `kuveyt-turk--medium-temel-bankacilik-hizmetleri-ucret-degisikliklerine-3444-pdf` | kuveyt-turk |
| `kuveyt-turk--musteri-ol-kampanyalari-mobilden-kuveyt-turklu-olan-esnaf-ve-ciftcilere-22000-tl` | kuveyt-turk |
| `turkiye-finans--kampanyalar-biten-kampanyalar` | turkiye-finans |
| `vakif-katilim--kendim-icin-finansmanlar` | vakif-katilim |
| `ziraat-katilim--finansman-urunleri-surdurulebilirlik-temali-bireysel-urunler` | ziraat-katilim |
