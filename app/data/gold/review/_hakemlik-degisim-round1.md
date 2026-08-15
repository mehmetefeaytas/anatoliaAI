# Round1 Hakemlik Değişim Kaydı

> `scripts/hakemlik_uygula.py` üretti. Kör hakem A ve B'nin kararlarını GÖRMEDEN aynı hücrelere baktı; kararı hangi anotatörle örtüştüyse diğeri ona çekildi.

## ⛔ κ üzerindeki etkisi

Manşet κ = **0,274** (hakemlik ÖNCESİ, `iaa_report_round1.md`) olarak kalır. Bu dosyadan sonra hesaplanan κ, bağımsız uyum değil **üçüncü göz sonrası gold tutarlılığıdır**; ikisi ayrı raporlanır (round0 emsali: `_kalibrasyon-sonucu.md` §8, 0,051 → 0,268).

## Sayılar

- Hakem kararı: **53**
- Uygulanan değişiklik: **41**
  - A haklı (B düzeltildi): **11**
  - B haklı (A düzeltildi): **30**
- Dokunulmayan (hakem ikisiyle de örtüşmedi): **10**
- `unclear` olduğu için atlanan: **2**

### Alan dağılımı

| Alan | Değişiklik |
|---|---:|
| `campaign_type` | 13 |
| `vade_ay` | 13 |
| `masraf_durumu` | 4 |
| `kampanya_kosullari` | 4 |
| `kampanya_suresi` | 2 |
| `taksit_sayisi` | 2 |
| `hedef_kitle` | 1 |
| `kar_payi_orani` | 1 |
| `odul_miktari` | 1 |

## Uygulanan değişiklikler

| Belge | Alan | Haklı | Eski karar | Yeni karar | Hakem gerekçesi |
|---|---|---|---|---|---|
| `albaraka--detay-dijital-musterilere-ozel-p` | `hedef_kitle` | B | ok `` | fix `[ "yeni_musteri"]` | Metin: 'Kampanyamız sadece yeni musterilerimiz icin gecerli olup daha once Albaraka muster |
| `albaraka--dis-ticaret-finansmanlari-harici` | `campaign_type` | A | absent `` | ok `` | Tek özne testi geçiyor: gövde yalnız Harici Garantiler ürününü anlatıyor, üstteki İthalat/ |
| `albaraka--eviniz-icin-prefabrik` | `vade_ay` | B | ok `` | fix `36` | Metin kademeli vade veriyor: 50.000 TL'ye kadar 36 ay, ustunde 24 ay. Aralik/kademe vakasi |
| `albaraka--formlar-altin-hesaplarindan-donu` | `vade_ay` | A | fix `12` | ok `` | Belge katilma hesabi vadelerini '3 ay, 6 ay veya 1 yil' olarak veriyor; en uzun secenek 1  |
| `albaraka--formlar-genel-kredi-sozlesmesi-u` | `campaign_type` | A | fix `Finansman` | absent `` | #kampanya_disi — Genel Kredi Sözleşmesi ücret tarifesi: onlarca ürünün (leasing, akreditif |
| `albaraka--formlar-genel-kredi-sozlesmesi-u` | `masraf_durumu` | B | absent `` | fix `{"amount": null, "has_` | has_fee doğru ama amount=3.0 uydurmadır: modelin gösterdiği yerdeki '3' sayısı '3. kişiler |
| `albaraka--gecmis-tarihli-aracfinansmanital` | `kar_payi_orani` | B | absent `` | ok `` | Bos sablon form: 'Akdi Kar Payi Orani (Aylik) %' bos birakilmis, sayi yok. Belgedeki tek k |
| `albaraka--gecmis-tarihli-aracfinansmanital` | `masraf_durumu` | B | absent `` | fix `{"amount": null, "has_` | Model 'Ücret Alınmaz' ifadesini yakalamış ama bu yalnız 4. kalem (bir yıl içindeki doküman |
| `albaraka--sozlesmeler-bayide-finansman-iht` | `kampanya_kosullari` | B | ok `` | absent `` | Belge bir tüketici kampanyası değil, Banka ile Aracı arasındaki 44 sayfalık aracılık/garan |
| `albaraka--tarim-bankaciligi-diger-finansma` | `kampanya_kosullari` | A | absent `` | ok `` | İki cümle de sayfanın kendi gövde metninden birebir alınmış (K1) ve yan menü/komşu kampany |
| `albaraka--tatiliniz-icin-devre-mulk` | `vade_ay` | B | ok `` | fix `36` | Kademeli vade: 125.000 TL'ye kadar 36 ay, 125-250 bin 24 ay, ustu 12 ay. En uzun vade kura |
| `albaraka--tr-urun-ve-hizmet-ucretleri` | `kampanya_kosullari` | B | ok `` | absent `` | Belge bir kampanya sayfası değil, ürün/hizmet ücret tarifesidir. Modelin ürettiği 8 madde  |
| `albaraka--tr-urun-ve-hizmet-ucretleri` | `masraf_durumu` | B | ok `` | fix `{"amount": null, "has_` | Model 'Ücretsiz sunulmaktadır' ifadesini yakalamış ama bu yalnız dijital kanal EFT/havale  |
| `dunya-katilim--hizmetler-doviz-transferi-s` | `vade_ay` | A | ok `12` | absent `` | SWIFT transfer sayfasi; vadeli urun yok. Modelin 12'si cerez politikasindaki _ga cerezinin |
| `dunya-katilim--kredi-kartlari-paraf-platin` | `kampanya_kosullari` | A | absent `` | ok `` | Cümle SSS bölümünden birebir alınmış (K1) ve 'söylemeniz gerekmektedir' ile gerçek bir kul |
| `dunya-katilim--kredi-kartlari-paraf-platin` | `masraf_durumu` | B | ok `` | fix `{"amount": null, "has_` | Model 'ücretsiz teslimat' ifadesine dayanmış, ama bu kartın kargo teslimidir. Belge yıllık |
| `hayat-finans--yatirim-ve-birikim-yatirimci` | `campaign_type` | A | unclear `` | ok `` | Tek özne: Yatırımcı Seviye Sistemi — döviz ve kıymetli maden işlem hacmine göre kademeli a |
| `kuveyt-turk--bizden-haberler-kuveyt-turkte` | `campaign_type` | B | ok `` | fix `Finansman` | Tek özne: ticari müşterilere yönelik makine finansmanı kampanyası (leasing + makine taksit |
| `kuveyt-turk--kampanya-arsivi-hepsiburada-a` | `campaign_type` | A | fix `Alışveriş Puanı` | ok `` | Tek kampanya: Hepsiburada Alışveriş Finansmanı'nda %3.99 kâr oranı, 36 aya varan taksit, 6 |
| `kuveyt-turk--kart-kampanyalari-dogtas-grub` | `vade_ay` | B | ok `` | absent `` | Kart taksit kampanyasi: tek ifade '5 aya varan taksit imkani'. Bu sayi taksit_sayisi'na ai |
| `kuveyt-turk--kart-kampanyalari-saglam-busi` | `odul_miktari` | B | ok `` | absent `` | 300 TL, 'taksit yapilabilmesi icin minimum harcama tutari'dir — asgari harcama esigi, odul |
| `kuveyt-turk--kart-kampanyalari-saglam-busi` | `vade_ay` | B | ok `` | absent `` | Modelin 3'u '3 ay erteleme'den geliyor; erteleme odemesiz donemdir, kilavuzda vade sayilma |
| `kuveyt-turk--katilma-hesaplari-ara-donem-k` | `kampanya_suresi` | A | fix `2025-07-09` | ok `` | Urun tanitim sayfasi; kampanya bitis tarihi yok. Gecen tek tarih '09.07.2025 tarihinden it |
| `kuveyt-turk--katilma-hesaplari-birikimli-k` | `campaign_type` | B | ok `` | fix `Yatırım Ürünü` | Tek özne: Birikimli Katılma Hesabı — özellikleri, limitleri, paylaşım/stopaj oranları ayrı |
| `kuveyt-turk--medium-bireysel-finansman-tal` | `campaign_type` | B | absent `` | ok `Finansman` | Tek özne: 'Bireysel Finansman Desteği' ürününe ait talep/bilgilendirme formu. Form hem ara |
| `tom-katilim--kampanyalar-giyim-alisverisle` | `taksit_sayisi` | A | fix `6` | ok `` | Belgede 'taksit' kelimesi acikca geciyor: 'Giyim Alisverislerinde Vade Farksiz 3 Taksit'.  |
| `tom-katilim--kampanyalar-giyim-alisverisle` | `vade_ay` | B | ok `` | absent `` | Belgedeki tüm sayılar taksit adedi: 'vade farksız 3 Taksit', 'vade farksız 6 Taksit', 'tak |
| `turkiye-emlak-katilim--kartlar-kredi-karti` | `kampanya_suresi` | B | ok `` | absent `` | 01.01.2026 tablodaki 'Guncelleme Tarihi' sutunundan geliyor — akdi kar payi/gecikme cezasi |
| `turkiye-emlak-katilim--katilma-hesaplari-z` | `vade_ay` | B | ok `` | fix `12` | Vade seçenekleri: 'Aylık, 3 Aylık, 6 Aylık, Kırık Vadeli ve Yıllık vade seçenekleriyle'. K |
| `turkiye-emlak-katilim--qr-kredi-karti-uyel` | `campaign_type` | B | absent `` | fix `Kart` | Belge tek özneli: Kredi Kartı Üyelik Sözleşmesi — baştan sona kredi kartı/ek kart/sanal ka |
| `turkiye-finans--kampanyalar-biten-kampanya` | `vade_ay` | B | ok `` | absent `` | Modelin dayanağı '3 ay erteleme fırsatı' — bu ödemesiz dönem/öteleme, kılavuza göre vade s |
| `turkiye-finans--katilma-hesaplari-e-katilm` | `vade_ay` | B | ok `` | fix `15` | Modelin 6'sı ürünün vadesi değil, genel stopaj oranları tablosundan ('6 aya kadar vadeli ( |
| `turkiye-finans--kobi-dijital-taksitli-tica` | `campaign_type` | B | ok `` | fix `Finansman` | Sayfanın gövdesi tek bir ürünü anlatıyor: KOBİ'lere yönelik Dijital Taksitli Ticari Finans |
| `vakif-katilim--bireysel-bankacilik-vakif-k` | `campaign_type` | B | unclear `` | fix `Yatırım Ürünü` | Tek özne: fiziki ziynet altınının değer tespitiyle Altın Cari/Altın Katılma Hesabı'na akta |
| `vakif-katilim--finansmanlar-motosiklet-fin` | `campaign_type` | B | ok `` | fix `Taşıt Finansmanı` | Tek özne: 0 km motosiklet alımı için kullandırılan finansman (48 aya varan vade, fatura de |
| `vakif-katilim--kendim-icin-detay-ihtiyac-f` | `vade_ay` | A | fix `36-24-12` | ok `` | SSS'te tutara göre kademeli vade: '125.000 TL ve altında ise 36 ay, 125.000-250.000 TL ara |
| `vakif-katilim--kendim-icin-finansmanlar` | `campaign_type` | B | ok `` | absent `` | Saf liste sayfası: Konut, Hızlı Fon, Arsa, Taşıt, Motosiklet, İhtiyaç, İş Yeri ve Kentsel  |
| `vakif-katilim--kobi-destekli-finansmanlar-` | `vade_ay` | B | ok `` | absent `` | Modelin dayanağı 'İşletme, destekten 3 yıl süreyle yararlanır' — bu KOSGEB destek programı |
| `ziraat-katilim--finansman-urunleri-surduru` | `vade_ay` | B | ok `` | absent `` | 48, sayfadaki genel 'Finansman Hesaplama Aracı' açılır listesinden geliyor ('TAŞIT FINANSM |
| `ziraat-katilim--kart-kampanyalari-mobilya-` | `campaign_type` | B | ok `` | fix `Alışveriş Puanı` | Tek özne: 9 Haziran-9 Temmuz 2026 arası mobilya sektöründe Bankkart ile yapılan alışverişt |
| `ziraat-katilim--kart-kampanyalari-mobilya-` | `taksit_sayisi` | B | ok `` | absent `` | 5 degeri sayfa altindaki BASKA kampanya listesinden ('Mondihome'da 5 Taksit Son Gun 31.08. |

## Dokunulmayan — insan hakemliğine kalır

Hakem üçüncü bir cevap verdi. Betiğin kendi kararını dayatması hakemi anotatör yerine koymak olurdu.

| Belge | Alan | A | B | Hakem | Gerekçe |
|---|---|---|---|---|---|
| `albaraka--formlar-altin-hesaplarindan-` | `kampanya_kosullari` | absent | ok | fix | Modelin 2. maddesi (Banka'nın getiri taahhüdü/garantisi bulunmadığı) h |
| `albaraka--formlar-genel-kredi-sozlesme` | `vade_ay` | ok | fix | absent | Belge ucret tarifesi formu; urun vadesi vermiyor. Modelin 36'si 'Kalan |
| `albaraka--gecmis-tarihli-aracfinansman` | `campaign_type` | absent | ok | fix | Tek özne var: 'ARAÇ FİNANSMANI TALEP, ONAY ve ÜCRET BİLGİLENDİRME FORM |
| `albaraka--tarim-bankaciligi-diger-fina` | `campaign_type` | fix | ok | absent | #kampanya_disi — 'Diğer Finansmanlar' sayfası dört ayrı ürünü (TMO Mak |
| `albaraka--tatiliniz-icin-devre-mulk` | `kampanya_kosullari` | ok | absent | fix | Modelin tek maddesi baştan sona gezinti menüsü kabuğudur ('Albaraka Mo |
| `kuveyt-turk--kampanya-arsivi-bisiklet-` | `finansman_tutari` | fix | ok | absent | 13.88247 degeri '13,882.47 TL' ornek odeme planindaki TOPLAM GERI ODEM |
| `kuveyt-turk--kampanya-arsivi-hepsibura` | `finansman_tutari` | fix | ok | absent | 13.68222 degeri '13,682.22 TL' ornek odeme plani toplam geri odemesind |
| `kuveyt-turk--katilma-hesaplari-ara-don` | `vade_ay` | ok | absent | fix | Hesap vadesi '372 gun'; 372 gun 30'un tam kati degil ama belge ayni va |
| `vakif-katilim--nakdi-finansmanlar-is-y` | `campaign_type` | ok | fix | fix | Tek özne: tüzel/ticari müşterilere iş yeri, fabrika, depo, arsa vb. ga |
| `ziraat-katilim--kart-kampanyalari-troy` | `finansman_tutari` | fix | ok | absent | Kampanya bir indirim kampanyasi; finansman kullandirimi yok. 1.000 TL  |

## Hakem `unclear` dedi — atlandı

| Belge | Alan | A | B | Gerekçe |
|---|---|---|---|---|
| `albaraka--formlar-genel-kredi-sozlesme` | `tahsis_ucreti` | absent | fix | Belgede tahsis ucreti VAR ama yalniz oran olarak: 'Tasit Tahsis Ucreti |
| `vakif-katilim--detay-vakif-katilim-ail` | `campaign_type` | unclear | absent | Tek özne var (Aile Yılı Paketi kampanyası, koşulları ve 31/12/2025 bit |

## Geri alma

```bash
cp /Users/mehmetefeaytas/anatoliaaI/app/data/gold/review/round1_A.csv.yedek-hakemlik-round1 /Users/mehmetefeaytas/anatoliaaI/app/data/gold/review/round1_A.csv
cp /Users/mehmetefeaytas/anatoliaaI/app/data/gold/review/round1_B.csv.yedek-hakemlik-round1 /Users/mehmetefeaytas/anatoliaaI/app/data/gold/review/round1_B.csv
```
