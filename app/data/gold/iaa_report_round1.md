# Anotatörler Arası Uyum (IAA) Raporu

> `scripts/report_iaa.py` üretti. Eşik politikası anotasyon BAŞLAMADAN ilan edilmiştir (ANNOTATION_GUIDE.md §7); sayılara bakıp eşik değiştirmek yasaktır.

- Anotatörler: A, B
- Ortak anote edilmiş satır: **650**
- Karar bulunmayan hücre (boş/eksik): **1004**

## Protokol künyesi

| Dosya | Protokol | Boş hücrenin anlamı |
|---|---|---|
| `/Users/mehmetefeaytas/.claude/jobs/89734536/tmp/oncesi/round1_A.csv` | **v2** | karar verilmedi — metrik dışı |
| `/Users/mehmetefeaytas/.claude/jobs/89734536/tmp/oncesi/round1_B.csv` | **v2** | karar verilmedi — metrik dışı |

## Sonuçlar

| Ölçüt | Neyi ölçer | Değer |
|---|---|---:|
| Cohen's kappa (karar) | Aynı satırda aynı kararı mı verdiler (ok/fix/absent/unclear) | **0.274** |
| Krippendorff α (nominal) | Ortaya çıkan gold DEĞERİ birebir aynı mı | 0.615 |
| Krippendorff α (ratio) | Sayısal alanlarda değer yakınlığı (33 birim) | 0.848 |

## Alan bazında kırılım

Toplu κ bir ORTALAMADIR. Uyuşmazlıklar birkaç alanda yığılıyorsa ortalama, hem sorunun yerini hem de iyi çalışan alanları gizler.

> ⚠️ Alan başına **n küçüktür**; tek bir alanın κ'sına dayanarak eşik kararı VERİLMEZ. §7 eşiği toplu κ içindir. Bu tablo nereye müdahale edileceğini söyler, kabul/ret kararını değil.

| Alan | n | Uyum | κ | Uyuşmazlık | En sık ayrışma |
|---|---:|---:|---:|---:|---|
| `campaign_type` | 47 | %64 | 0.331 | 17 | `fix/ok` ×8 |
| `vade_ay` | 32 | %53 | 0.242 | 15 | `absent/ok` ×8 |
| `kampanya_kosullari` | 9 | %33 | -0.125 | 6 | `absent/ok` ×6 |
| `masraf_durumu` | 5 | %20 | 0.091 | 4 | `absent/fix` ×2 |
| `finansman_tutari` | 9 | %67 | 0.270 | 3 | `fix/ok` ×3 |
| `kampanya_suresi` | 18 | %89 | 0.463 | 2 | `fix/ok` ×1 |
| `taksit_sayisi` | 6 | %67 | 0.000 | 2 | `fix/ok` ×1 |
| `hedef_kitle` | 3 | %67 | 0.000 | 1 | `fix/ok` ×1 |
| `kar_payi_orani` | 9 | %89 | 0.609 | 1 | `absent/ok` ×1 |
| `odul_miktari` | 1 | %0 | 0.000 | 1 | `absent/ok` ×1 |
| `tahsis_ucreti` | 1 | %0 | 0.000 | 1 | `absent/fix` ×1 |
| `alisveris_puani` | 1 | %100 | 1.000 | 0 | — |

## Karar (önceden ilan edilmiş eşik)

- **Durum: `hakemlik`**
- Yapılacak: ZORUNLU hakemlik + kılavuz revizyonu. Etkilenen alanlar yeniden anote edilir.

| Eşik | Karar |
|---|---|
| κ ≥ 0,80 | kabul |
| 0,67 ≤ κ < 0,80 | notla kabul |
| κ < 0,67 | zorunlu hakemlik + kılavuz revizyonu |

## Uyuşmazlıklar (56)

Kalibrasyon toplantısında sırayla konuşulacak liste.

| Belge | Alan | Kararlar | Değerler |
|---|---|---|---|
| `albaraka--detay-dijital-musterilere-ozel-pratik-finansman-kart` | `campaign_type` | A=fix, B=fix | A='İhtiyaç Finasmanı', B='İhtiyaç Finansmanı' |
| `albaraka--detay-dijital-musterilere-ozel-pratik-finansman-kart` | `finansman_tutari` | A=fix, B=fix | A='150000', B='{"currency":"TRY","value":150000}' |
| `albaraka--detay-dijital-musterilere-ozel-pratik-finansman-kart` | `hedef_kitle` | A=ok, B=fix | A='["mevcut_musteri", "yeni_musteri"]', B='[ "yeni_musteri"]' |
| `albaraka--dis-ticaret-finansmanlari-harici-garantiler` | `campaign_type` | A=ok, B=absent | A='Finansman', B='__YOK__' |
| `albaraka--eviniz-icin-prefabrik` | `vade_ay` | A=ok, B=fix | A='24', B='36' |
| `albaraka--formlar-altin-hesaplarindan-donusumun-desteklenmesi-tl-katilma-hesabi-bilgilendi` | `kampanya_kosullari` | A=absent, B=ok | A='__YOK__', B='["Vergi kesintileri, Katılma Hesabı\'nın açılış/vade yenileme tarihinde ilgili vade için geçerli olan cari vergi oranları üzerinden hesaplanacağı, 8.", "Müşteri, katılma hesaplarının; Banka\'nın herhangi bir oran veya tutarda getiri taahhüdü bulunmadığı, bu bakımdan Banka\'nın asgari de olsa getiri taahhüdü/garantisi olmayan, karşılığında hesap sahibine önceden belirlenmiş herhangi bir getiri ödenmeyen ve anaparanın aynen geri ödenmesi garanti edilmeyen hesaplar olduğunu bildiğini, 10."]' |
| `albaraka--formlar-altin-hesaplarindan-donusumun-desteklenmesi-tl-katilma-hesabi-bilgilendi` | `vade_ay` | A=ok, B=fix | A='12', B='12' |
| `albaraka--formlar-genel-kredi-sozlesmesi-ucret-bilgilendirme-formu-pdf` | `campaign_type` | A=absent, B=fix | A='__YOK__', B='Finansman' |
| `albaraka--formlar-genel-kredi-sozlesmesi-ucret-bilgilendirme-formu-pdf` | `masraf_durumu` | A=absent, B=fix | A='__YOK__', B='{"amount": null, "has_fee": true}' |
| `albaraka--formlar-genel-kredi-sozlesmesi-ucret-bilgilendirme-formu-pdf` | `tahsis_ucreti` | A=absent, B=fix | A='__YOK__', B='{"max": 0.25, "min": 0}' |
| `albaraka--formlar-genel-kredi-sozlesmesi-ucret-bilgilendirme-formu-pdf` | `vade_ay` | A=ok, B=fix | A='36', B='36' |
| `albaraka--gecmis-tarihli-aracfinansmanitalep-onayveucretbilgilendirmeformu-pdf` | `campaign_type` | A=absent, B=ok | A='__YOK__', B='Finansman' |
| `albaraka--gecmis-tarihli-aracfinansmanitalep-onayveucretbilgilendirmeformu-pdf` | `kar_payi_orani` | A=absent, B=ok | A='__YOK__', B='__YOK__' |
| `albaraka--gecmis-tarihli-aracfinansmanitalep-onayveucretbilgilendirmeformu-pdf` | `masraf_durumu` | A=absent, B=fix | A='__YOK__', B='{"amount": null, "has_fee": true}' |
| `albaraka--sozlesmeler-bayide-finansman-ihtiyac-aracilik-ve-garantorluk-sozlesmesi-komisyon` | `kampanya_kosullari` | A=ok, B=absent | A='["Taraflar, işbu Sözleşme gereğince uyulması gerekli her türlü kanun, tüzük, kararname, karar ve benzeri mevzuat, yasal ve idari düzenlemelerin gereğini yerine getirmek zorundadır.", "Aracı tarafından gerekli başvurular yapılmak suretiyle ve Banka\'nın izin ve yetki vermesi şartıyla Sistem, Aracı\'nın bağlı veya bağımsız tacir yardımcısı, ticari temsilci, ticari vekil, personel, alt çalışan ve kendisine bağlı olarak çalışan ve Banka\'nın izin ve yetki verdiği kişi tarafından kullanılabilir.", "Aracı, işbu Sözleşme kapsamında Başvuran\'dan bilgi, belge ve sözleşme alma yükümlülüğünü Banka\'ya bilgi vermek koşulu ile planlı tadilat, bakım, onarım, izin süreleri dışında Aracı\'ya ait işyerlerinden Banka\'nın mesai (çalışma) günlerinde ve saatlerinde yerine getirmeyi taahhüt etmektedir 3.8.", "Aracı, müşteri ilişkileri veya yönetimi anlamında Banka müşterilerinden gelen tüm talepleri de derhal tüm bilgi ve belgelerle birlikte Banka\'ya iletecek ve yönlendirecek olup, yalnızca Banka tarafından kendisine bildirilen ve verilen talimatlar kapsamda Banka müşterilerine bilgi ve belge verecektir.", "maddesinde belirtilen şartları taşıdığını ve Sözleşme süresi içerisinde bu şartların kaybedilmesi durumunda, bu durumu derhal Banka\'ya yazılı olarak bildireceğini beyan ve taahhüt eder.", "Banka tarafından talep edilmesi durumunda ya da BDDK\'ca gerekli görülmesi halinde, Aracı tarafından işbu Sözleşme kapsamında verilen hizmetlerden doğabilecek zararları karşılamak amacıyla masrafları Taraflarca karşılanmak üzere Banka\'ca sorumluluk sigortası yaptırılabilecektir.", "Aracı, işbu Sözleşme kapsamında verdiği hizmeti gerçekleştirebilecek yönetim yapısına, yeterli sayı ve nitelikte personele, gerekli teknik donanıma, belge ve kayıt düzenine, iş devamlılığı planına sahip olduğunu, Sözleşme konusu hizmet ile ilgili güvenlik risklerine, yangın ve doğal afetler gibi acil durumlara karşı gerekli önlemleri almış kabul, beyan ve taahhüt eder.", "Aracı, kendisinden mal veya hizmet satın alan Başvuran\'ın olabilecek ayıplarla ilgili şikâyet, iddia ve taleplerine meydan veremeyecek yahut bu sebeplerle mağduriyetlerine yol açmayacak şekilde gerekli tedbirli alacaktır."]', B='__YOK__' |
| `albaraka--tarim-bankaciligi-diger-finansmanlar` | `campaign_type` | A=fix, B=ok | A='Finansman', B='İhtiyaç Finansmanı' |
| `albaraka--tarim-bankaciligi-diger-finansmanlar` | `kampanya_kosullari` | A=ok, B=absent | A='["Finansal Kiralama Makine ekipman, traktör ve biçerdöver finansmanı işlemleri finansal kiralama yöntemiyle ve hasat dönemine uygun ödeme koşulları ile 48 ay vadeye kadar yapılabilmektedir.", "IPARD Programı kapsamında destek alan projeleriniz için gerekli olan finansmanı bankamızdan kullanabilirsiniz."]', B='__YOK__' |
| `albaraka--tatiliniz-icin-devre-mulk` | `kampanya_kosullari` | A=ok, B=absent | A='["Albaraka Mobil Mobil Bankacılık Aç Devre Mülk Anasayfa Bireysel Finansmanlar İhtiyaç Finansmanı Tatiliniz İçin Devre Mülk Seyahat Devre Mülk Devre Tatil Hemen Başvur Devre mülkler tapu kaydı gerektiren ve her yıl belirli dönemlerde asgari 15 gün süreli konaklama imkânı veren mülklerdir."]', B='__YOK__' |
| `albaraka--tatiliniz-icin-devre-mulk` | `vade_ay` | A=ok, B=fix | A='12', B='36' |
| `albaraka--tr-urun-ve-hizmet-ucretleri` | `campaign_type` | A=fix, B=fix | A='Yatırım Ürünü', B='Finansman' |
| `albaraka--tr-urun-ve-hizmet-ucretleri` | `kampanya_kosullari` | A=ok, B=absent | A='["1.03.2020 İhtiyaç Finansmanı - % 0.5 - % 0.5 BSMV Hariçtir.", "14.08.2020 Yurt Dışı Diğer Şubeden Para Çekme - Şube - % 0.5 - % 1 BSMV Hariçtir.", "14.08.2020 Nakit Çekim Ofisinden Para Çekme - Nakit Çekim Ofisi TRY - - 5 - BSMV Hariçtir.", "15.01.2026 8.300-399.000 TL arası TRY 79.76 - 79.76 - BSMV Hariçtir.", "15.01.2026 399.000 TL üstü TRY 797.68 - 797.68 - BSMV Hariçtir.", "15.01.2026 Düzenli EFT Gönderimi - 8.300 TL ve altı TRY 7.97 - 7.97 - BSMV Hariçtir.", "16.02.2026 Düzenli EFT Gönderimi - 8.300-399.000 TL arası TRY 15.96 - 15.96 - BSMV Hariçtir.", "16.02.2026 Düzenli EFT Gönderimi - 399.000 TL üstü TRY 199.41 - 199.41 - BSMV Hariçtir."]', B='__YOK__' |
| `albaraka--tr-urun-ve-hizmet-ucretleri` | `masraf_durumu` | A=ok, B=fix | A='{"amount": 0.0, "has_fee": false}', B='{"amount": null, "has_fee": true}' |
| `dunya-katilim--hizmetler-doviz-transferi-swift` | `vade_ay` | A=absent, B=ok | A='__YOK__', B='12' |
| `dunya-katilim--kredi-kartlari-paraf-platinum-kredi-karti` | `kampanya_kosullari` | A=ok, B=absent | A='["Fizikî alışverişlerde, satıcıya ödemenizi Paraf Para ile yapmak istediğinizi söylemeniz gerekmektedir."]', B='__YOK__' |
| `dunya-katilim--kredi-kartlari-paraf-platinum-kredi-karti` | `masraf_durumu` | A=ok, B=fix | A='{"amount": 0.0, "has_fee": false}', B='{"amount": null, "has_fee": true}' |
| `hayat-finans--yatirim-ve-birikim-yatirimci-seviye-sistemi` | `campaign_type` | A=ok, B=unclear | A='Yatırım Ürünü' |
| `kuveyt-turk--bizden-haberler-kuveyt-turkten-1-milyar-tl-limitli-yeni-makine-finansmani-kampan` | `campaign_type` | A=ok, B=fix | A='İhtiyaç Finansmanı', B='Finansman' |
| `kuveyt-turk--kampanya-arsivi-bisiklet-finansmaninda-enerji-tasarrufu-haftasina-ozel-419-kar-o` | `finansman_tutari` | A=fix, B=ok | A='{"currency": "TRY", "value": 13.882,47}', B='{"currency": "TRY", "value": 13.88247}' |
| `kuveyt-turk--kampanya-arsivi-hepsiburada-alisveris-finansmaninda-enerji-tasarrufu-haftasina-o` | `campaign_type` | A=ok, B=fix | A='Finansman', B='Alışveriş Puanı' |
| `kuveyt-turk--kampanya-arsivi-hepsiburada-alisveris-finansmaninda-enerji-tasarrufu-haftasina-o` | `finansman_tutari` | A=fix, B=ok | A='{"currency": "TRY", "value": 13.682,22}', B='{"currency": "TRY", "value": 13.68222}' |
| `kuveyt-turk--kart-kampanyalari-dogtas-grubunda-5-aya-varan-taksit-imkani` | `vade_ay` | A=ok, B=absent | A='5', B='__YOK__' |
| `kuveyt-turk--kart-kampanyalari-saglam-business-karttan-dev-kampanya-3-ay-erteleme-ve-349-oran` | `odul_miktari` | A=ok, B=absent | A='{"currency": "TRY", "value": 300.0}', B='__YOK__' |
| `kuveyt-turk--kart-kampanyalari-saglam-business-karttan-dev-kampanya-3-ay-erteleme-ve-349-oran` | `vade_ay` | A=ok, B=absent | A='3', B='__YOK__' |
| `kuveyt-turk--katilma-hesaplari-ara-donem-kar-payi-odemeli-hesaplar` | `kampanya_suresi` | A=ok, B=fix | A='__YOK__', B='2025-07-09' |
| `kuveyt-turk--katilma-hesaplari-ara-donem-kar-payi-odemeli-hesaplar` | `vade_ay` | A=ok, B=absent | A='6', B='__YOK__' |
| `kuveyt-turk--katilma-hesaplari-birikimli-katilma-hesabi` | `campaign_type` | A=ok, B=fix | A='Konut Finansmanı', B='Yatırım Ürünü' |
| `kuveyt-turk--medium-bireysel-finansman-talebi-onay-ve-bilgilendirme-fo-4013-pdf` | `campaign_type` | A=absent, B=ok | A='__YOK__', B='Finansman' |
| `tom-katilim--kampanyalar-giyim-alisverislerinde-kampanya` | `taksit_sayisi` | A=ok, B=fix | A='3', B='6' |
| `tom-katilim--kampanyalar-giyim-alisverislerinde-kampanya` | `vade_ay` | A=ok, B=absent | A='6', B='__YOK__' |
| `turkiye-emlak-katilim--kartlar-kredi-karti` | `kampanya_suresi` | A=ok, B=absent | A='2026-01-01', B='__YOK__' |
| `turkiye-emlak-katilim--katilma-hesaplari-zumrut-katilma-hesabi` | `vade_ay` | A=ok, B=fix | A='6', B='12' |
| `turkiye-emlak-katilim--qr-kredi-karti-uyelik-sozlesmesi-pdf` | `campaign_type` | A=absent, B=fix | A='__YOK__', B='Kart' |
| `turkiye-finans--kampanyalar-biten-kampanyalar` | `vade_ay` | A=ok, B=absent | A='3', B='__YOK__' |
| `turkiye-finans--katilma-hesaplari-e-katilma-hesabi` | `vade_ay` | A=ok, B=fix | A='6', B='15' |
| `turkiye-finans--kobi-dijital-taksitli-ticari-finansman-destegi` | `campaign_type` | A=ok, B=fix | A='Yatırım Ürünü', B='Finansman' |
| `vakif-katilim--bireysel-bankacilik-vakif-katilim-ile-altin-gunler` | `campaign_type` | A=unclear, B=fix | B='Yatırım Ürünü' |
| `vakif-katilim--detay-vakif-katilim-aile-yili-paketi` | `campaign_type` | A=unclear, B=absent | B='__YOK__' |
| `vakif-katilim--finansmanlar-motosiklet-finansmani` | `campaign_type` | A=ok, B=fix | A='Finansman', B='Taşıt Finansmanı' |
| `vakif-katilim--kendim-icin-detay-ihtiyac-finansmani` | `vade_ay` | A=ok, B=fix | A='36', B='36-24-12' |
| `vakif-katilim--kendim-icin-finansmanlar` | `campaign_type` | A=ok, B=absent | A='Konut Finansmanı', B='__YOK__' |
| `vakif-katilim--kobi-destekli-finansmanlar-kosgeb-destekli-finansman` | `vade_ay` | A=ok, B=absent | A='36', B='__YOK__' |
| `vakif-katilim--nakdi-finansmanlar-is-yeri-finansmani` | `campaign_type` | A=ok, B=fix | A='İhtiyaç Finansmanı', B='Konut Finansmanı' |
| `ziraat-katilim--finansman-urunleri-surdurulebilirlik-temali-bireysel-urunler` | `vade_ay` | A=ok, B=absent | A='48', B='__YOK__' |
| `ziraat-katilim--kart-kampanyalari-mobilya-alisverisinize-1500-tl-bankkart-lira` | `campaign_type` | A=ok, B=fix | A='Kart', B='Alışveriş Puanı' |
| `ziraat-katilim--kart-kampanyalari-mobilya-alisverisinize-1500-tl-bankkart-lira` | `taksit_sayisi` | A=ok, B=absent | A='5', B='__YOK__' |
| `ziraat-katilim--kart-kampanyalari-troy-kartla-drda-1000-tlye-varan-indirim` | `finansman_tutari` | A=fix, B=ok | B='{"currency": "TRY", "value": 1000.0}' |
