# Gold Kanıt Zinciri

> `scripts/kanit_zinciri.py` üretti. Kaynak: `data/gold/gold.v2.json`

Her gold kaydı ham arşive kadar izlenir: çıkarılmış metin -> ham HTML ->
kaynak URL + indirme zamanı. Ekran görüntüsü yerine **koşulabilir** kanıt.

## Özet

| Ölçüt | Değer |
|---|---:|
| Gold kaydı | 48 |
| **Zinciri tam (hash birebir)** | **45** |
| Zinciri tam, içerik kaymış (URL üzerinden) | 3 |
| Zinciri KIRIK | 0 |
| Ham arşivde birden çok kopyası olan | 4 |

## İçerik kayması — kanıt duruyor, sayfa değişmiş

Gold **donmuş** bir anlık görüntüdür; korpus tazeleniyor. Aşağıdaki
kayıtlarda anote edilen metin ile arşivdeki güncel metin ayrışmış.
Bu bir kanıt kaybı DEĞİLDİR: anote edilen metnin kendisi gold kaydının
`text` alanında saklı ve ölçüm onu kullanıyor; alan değerlerinin o
metinden geldiği `field_spans` ile ayrıca kanıtlı. Kayıt burada
görünür kalır ki 'gold ile korpus aynı' sanılmasın.

| id | arşivdeki son indirme | ham dosya |
|---|---|---|
| `turkiye-finans--kampanyalar-ofot` | 2026-08-11T16:15:58+00:00 | `turkiye-finans/live/kampanyalar-ofot.txt` |
| `tom-katilim--kampanyalar-a101de-her-alisveriste-3-nakit-iade` | 2026-08-12T08:37:09+00:00 | `tom-katilim/live/kampanyalar-a101de-her-alisveriste-3-nakit-iade.txt` |
| `tom-katilim--kampanyalar-cok-kazananlar-kulubu-kat-kat-kazandiran-kampanyalari-ile-seninle` | 2026-08-12T08:37:27+00:00 | `tom-katilim/live/kampanyalar-cok-kazananlar-kulubu-kat-kat-kazandiran-kampanyalari-ile-seninle.txt` |

## Ham arşivde birden çok kopya

Aynı içerik birden çok dosyada duruyor. Zinciri kırmaz (ilk dosya
kullanılır) ama korpus sayımını şişirir — `sample_gold_v2` ilke 2.

| id | kopya |
|---|---:|
| `ziraat-katilim--konut-finansmani-kentsel-donusum-finansmani` | 2 |
| `kuveyt-turk--kampanya-arsivi-business-plus-ile-akaryakitta-indirim-firsati` | 2 |
| `dunya-katilim--ihtiyac-finansmanlari-enerya-ihtiyac-finansmani` | 2 |
| `kuveyt-turk--kampanya-arsivi-7000-tl-degerindeki-cek-tahsil-paketi-ucretsiz-scr` | 2 |

## Zincir — kayıt başına

| id | ham dosya | indirme zamanı | HTTP | yöntem |
|---|---|---|---:|---|
| `adil-katilim--katilim-bankaciligi` | `adil-katilim/live/katilim-bankaciligi.txt` | 2026-08-12T08:36:13+00:00 | 200 | browser |
| `adil-katilim--katilim-bankaciligi-danisma-komitesi` | `adil-katilim/live/katilim-bankaciligi-danisma-komitesi.txt` | 2026-08-12T08:36:23+00:00 | 200 | browser |
| `adil-katilim--katilim-bankaciligi-urun-ve-hizmetler` | `adil-katilim/live/katilim-bankaciligi-urun-ve-hizmetler.txt` | 2026-08-12T08:36:19+00:00 | 200 | browser |
| `adil-katilim--www-adilkatilim-com-tr` | `adil-katilim/live/www-adilkatilim-com-tr.txt` | 2026-08-12T08:36:11+00:00 | 200 | browser |
| `albaraka--detay-dijital-katilma-hesabina-ozel-paylasim-oranlari-10` | `albaraka/live/detay-dijital-katilma-hesabina-ozel-paylasim-oranlari-10.txt` | 2026-08-03T16:35:57+00:00 | 200 | live |
| `albaraka--hayat-ve-ferdi-kaza-sigortasi-kredi-hayat-sigortasi` | `albaraka/products/hayat-ve-ferdi-kaza-sigortasi-kredi-hayat-sigortasi.txt` | 2026-08-03T17:24:32+00:00 | 200 | live |
| `albaraka--tasit-finansmani-togg-finansmani` | `albaraka/products/tasit-finansmani-togg-finansmani.txt` | 2026-08-03T17:23:20+00:00 | 200 | live |
| `albaraka--tr-kampanyalar` | `albaraka/live/tr-kampanyalar.txt` | 2026-08-04T20:59:51+00:00 | 200 | live |
| `dunya-katilim--ihtiyac-finansmanlari-enerya-ihtiyac-finansmani` | `dunya-katilim/live/ihtiyac-finansmanlari-enerya-ihtiyac-finansmani.txt` | 2026-08-03T17:04:47+00:00 | 200 | live |
| `dunya-katilim--kampanyalar-carter-s` | `dunya-katilim/live/kampanyalar-carter-s.txt` | 2026-08-03T17:02:35+00:00 | 200 | live |
| `dunya-katilim--kampanyalar-divarese` | `dunya-katilim/live/kampanyalar-divarese.txt` | 2026-08-03T17:02:50+00:00 | 200 | live |
| `dunya-katilim--kampanyalar-tod-paraf` | `dunya-katilim/live/kampanyalar-tod-paraf.txt` | 2026-08-03T17:03:59+00:00 | 200 | live |
| `dunya-katilim--kendim-icin-kartlar` | `dunya-katilim/products/kendim-icin-kartlar.txt` | 2026-08-03T17:47:08+00:00 | 200 | live |
| `hayat-finans--hesaplar` | `hayat-finans/products/hesaplar.txt` | 2026-08-03T17:43:27+00:00 | 200 | browser |
| `hayat-finans--hesaplar-avantajli-hesap` | `hayat-finans/products/hesaplar-avantajli-hesap.txt` | 2026-08-03T17:43:49+00:00 | 200 | browser |
| `hayat-finans--kampanyalar-hayat-finans-ile-gastroclub-ayricaliklari` | `hayat-finans/live/kampanyalar-hayat-finans-ile-gastroclub-ayricaliklari.txt` | 2026-08-03T17:01:46+00:00 | 200 | browser |
| `hayat-finans--yatirim-ve-birikim-hfy-gunluk-kazandiran-fon` | `hayat-finans/products/yatirim-ve-birikim-hfy-gunluk-kazandiran-fon.txt` | 2026-08-03T17:44:28+00:00 | 200 | browser |
| `hayat-finans--yatirim-ve-birikim-hisse-senedi-islemleri-yatirim-ve-birikim` | `hayat-finans/products/yatirim-ve-birikim-hisse-senedi-islemleri-yatirim-ve-birikim.txt` | 2026-08-03T17:44:30+00:00 | 200 | browser |
| `hayat-finans--yatirim-ve-birikim-yatirim-fonlari-yatirim-ve-birikim` | `hayat-finans/products/yatirim-ve-birikim-yatirim-fonlari-yatirim-ve-birikim.txt` | 2026-08-03T17:45:02+00:00 | 200 | browser |
| `kuveyt-turk--kampanya-arsivi-7000-tl-degerindeki-cek-tahsil-paketi-ucretsiz-scr` | `kuveyt-turk/archive/kampanya-arsivi-7000-tl-degerindeki-cek-tahsil-paketi-ucretsiz-scr-onceki-2.txt` | 2026-07-30T18:32:33+00:00 | 200 | live |
| `kuveyt-turk--kampanya-arsivi-business-plus-ile-akaryakitta-indirim-firsati` | `kuveyt-turk/archive/kampanya-arsivi-business-plus-ile-akaryakitta-indirim-firsati-onceki-2.txt` | 2026-07-30T18:33:17+00:00 | 200 | live |
| `kuveyt-turk--kampanya-arsivi-kuveyt-turkten-avantajli-leasing-finansmani` | `kuveyt-turk/archive/kampanya-arsivi-kuveyt-turkten-avantajli-leasing-finansmani.txt` | 2026-08-03T17:59:02+00:00 | 200 | live |
| `kuveyt-turk--kampanya-arsivi-kuveyt-turkten-eczacilara-ozel-8000-mil` | `kuveyt-turk/archive/kampanya-arsivi-kuveyt-turkten-eczacilara-ozel-8000-mil.txt` | 2026-08-03T17:59:17+00:00 | 200 | live |
| `kuveyt-turk--leasing-leasing-sureci-ve-hesaplama-araci` | `kuveyt-turk/products/leasing-leasing-sureci-ve-hesaplama-araci.txt` | 2026-08-03T17:16:39+00:00 | 200 | live |
| `kuveyt-turk--musteri-ol-kampanyalari-kuveyt-turk-mobilden-musterimiz-olun-ozel-kur-firsatini-` | `kuveyt-turk/live/musteri-ol-kampanyalari-kuveyt-turk-mobilden-musterimiz-olun-ozel-kur-firsatini-.txt` | 2026-08-03T16:33:44+00:00 | 200 | live |
| `tom-katilim--kampanyalar-a101de-her-alisveriste-3-nakit-iade` | `tom-katilim/live/kampanyalar-a101de-her-alisveriste-3-nakit-iade.txt` | 2026-08-12T08:37:09+00:00 | 200 | browser |
| `tom-katilim--kampanyalar-cok-kazananlar-kulubu-kat-kat-kazandiran-kampanyalari-ile-seninle` | `tom-katilim/live/kampanyalar-cok-kazananlar-kulubu-kat-kat-kazandiran-kampanyalari-ile-seninle.txt` | 2026-08-12T08:37:27+00:00 | 200 | browser |
| `tom-katilim--kampanyalar-hadi-black-kredi-karti-ile-pegasus-harcamalarindan-50-iade-kazan` | `tom-katilim/live/kampanyalar-hadi-black-kredi-karti-ile-pegasus-harcamalarindan-50-iade-kazan.txt` | 2026-08-03T17:01:11+00:00 | 200 | browser |
| `tom-katilim--kampanyalar-hadi-kredi-karti-limitini-artir-toplam-2000-tlye-kadar-a101-hediye-b` | `tom-katilim/live/kampanyalar-hadi-kredi-karti-limitini-artir-toplam-2000-tlye-kadar-a101-hediye-b.txt` | 2026-08-03T17:00:47+00:00 | 200 | browser |
| `turkiye-emlak-katilim--kampanya-beyaz-esya-ve-elektronik-alisverislerinize-3000-tlye-varan-parafpara` | `turkiye-emlak-katilim/live/kampanya-beyaz-esya-ve-elektronik-alisverislerinize-3000-tlye-varan-parafpara.txt` | 2026-07-30T18:42:21+00:00 | 200 | live |
| `turkiye-emlak-katilim--kampanya-giyim-ve-kozmetik-alisverislerinize-1000-tl-parafpara` | `turkiye-emlak-katilim/live/kampanya-giyim-ve-kozmetik-alisverislerinize-1000-tl-parafpara.txt` | 2026-07-30T18:42:48+00:00 | 200 | live |
| `turkiye-emlak-katilim--kampanya-paraf-ile-adv-magazalarinda-1000-tl-parafpara` | `turkiye-emlak-katilim/live/kampanya-paraf-ile-adv-magazalarinda-1000-tl-parafpara.txt` | 2026-08-03T16:57:22+00:00 | 200 | live |
| `turkiye-emlak-katilim--kampanya-paraf-ile-networkte-4-taksit-firsati` | `turkiye-emlak-katilim/live/kampanya-paraf-ile-networkte-4-taksit-firsati.txt` | 2026-08-03T16:58:40+00:00 | 200 | live |
| `turkiye-emlak-katilim--kampanya-paraf-ile-secili-e-ticaret-alisverislerinize-1500-tlye-varan-parafpara` | `turkiye-emlak-katilim/live/kampanya-paraf-ile-secili-e-ticaret-alisverislerinize-1500-tlye-varan-parafpara.txt` | 2026-08-03T16:58:55+00:00 | 200 | live |
| `turkiye-emlak-katilim--kampanya-paraf-ile-yargici-magazalarinda-4-taksit-firsati` | `turkiye-emlak-katilim/live/kampanya-paraf-ile-yargici-magazalarinda-4-taksit-firsati.txt` | 2026-08-03T16:59:22+00:00 | 200 | live |
| `turkiye-finans--kampanyalar-ofot` | `turkiye-finans/live/kampanyalar-ofot.txt` | 2026-08-11T16:15:58+00:00 | 200 | browser |
| `turkiye-finans--kampanyalar-turkiye-finans-avantajlariyla-mobilden-tanis` | `turkiye-finans/live/kampanyalar-turkiye-finans-avantajlariyla-mobilden-tanis.txt` | 2026-08-03T16:39:02+00:00 | 200 | live |
| `vakif-katilim--detay-ria-a101-hediye-ceki-kampanyasi` | `vakif-katilim/live/detay-ria-a101-hediye-ceki-kampanyasi.txt` | 2026-08-03T16:52:01+00:00 | 200 | live |
| `vakif-katilim--detay-troy-kredi-karti-ile-50si-bizden` | `vakif-katilim/live/detay-troy-kredi-karti-ile-50si-bizden.txt` | 2026-08-03T16:54:04+00:00 | 200 | live |
| `vakif-katilim--dis-ticaret-dis-ticaret-finansmanlari` | `vakif-katilim/products/dis-ticaret-dis-ticaret-finansmanlari.txt` | 2026-08-03T17:32:44+00:00 | 200 | live |
| `vakif-katilim--hesaplar-ozel-cari-hesaplar` | `vakif-katilim/products/hesaplar-ozel-cari-hesaplar.txt` | 2026-08-03T17:37:06+00:00 | 200 | live |
| `vakif-katilim--musteri-alisveris-finansmani-basvurusu` | `vakif-katilim/products/musteri-alisveris-finansmani-basvurusu.txt` | 2026-08-03T17:32:35+00:00 | 200 | live |
| `vakif-katilim--odemeler-tasarruf-finansman-sirketleri-tahsilat-sistemi-2` | `vakif-katilim/products/odemeler-tasarruf-finansman-sirketleri-tahsilat-sistemi-2.txt` | 2026-08-03T17:36:42+00:00 | 200 | live |
| `ziraat-katilim--kart-kampanyalari-troy-kart-yemeksepeti-kampanyasi` | `ziraat-katilim/live/kart-kampanyalari-troy-kart-yemeksepeti-kampanyasi.txt` | 2026-08-03T16:48:51+00:00 | 200 | live |
| `ziraat-katilim--konut-finansmani-kentsel-donusum-finansmani` | `ziraat-katilim/live/konut-finansmani-kentsel-donusum-finansmani.txt` | 2026-08-03T16:50:48+00:00 | 200 | live |
| `ziraat-katilim--ozel-bankacilik-finansman-urunleri` | `ziraat-katilim/products/ozel-bankacilik-finansman-urunleri.txt` | 2026-08-03T17:30:20+00:00 | 200 | live |
| `ziraat-katilim--yatirim-urunleri-sukuk` | `ziraat-katilim/products/yatirim-urunleri-sukuk.txt` | 2026-08-03T17:30:14+00:00 | 200 | live |
| `ziraat-katilim--zekat-hesaplama` | `ziraat-katilim/products/zekat-hesaplama.txt` | 2026-08-03T17:31:02+00:00 | 200 | live |
