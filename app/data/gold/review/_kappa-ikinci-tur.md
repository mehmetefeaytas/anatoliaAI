# κ (Cohen's kappa) — ikinci etiketleyici turu

**İkinci etiketleyici bir LLM'dir.** İnsan çift-anotasyonun yerine geçtiği iddia edilmiyor; ölçülen şey bağımsız bir ikinci etiketleyicinin kararlarıyla uyumdur. LLM gold'u da kural motoru çıktısını da GÖRMEDİ — yalnız belge metnini ve alan şemasını aldı.

* arka uç / model: `ollama` / `qwen2.5:7b-instruct`
* belge: **16** (LLM hatası: 0)
* κ çifti (karar verilmiş (belge, alan) ikilisi): **192**
* toplam LLM süresi: 9 dk

## Sonuç

| Ölçüt | Değer |
|---|---|
| κ — varlık kararı (dolu / absent) | **0.700** (notla) |
| Değer uyumu — birebir (iki taraf da dolu) | 11/26 = 0.423 |
| Krippendorff α (`ratio`, sayısal alanlar) | 1.000 — **YETERSİZ BİRİM** (3 < 10) |

α 3 sayısal birim üzerinden hesaplandı ve bu sayı bir iddiaya taban olamaz: tek bir birimin değişmesi α'yı 1.000'den sıfıra düşürebilir. Sebep kapsam: 26 ortak-dolu çiftin çoğu liste ya da serbest metin alanı (`hedef_kitle`, `kampanya_kosullari`) ve `ratio` ölçeğine oturmuyor; aralık değerleri de (`comparable=False`) atlanıyor. Kılavuz §7'nin vaat ettiği α ÖLÇÜLDÜ ama şu korpus kesitinde anlamlı değil — sayının kendisi değil bu sınır raporlanıyor.

`κ` yalnız **varlık** kararını ölçer: "bu alan bu belgede var mı?". Değer uyumu ayrı satırda ve şans düzeltmesi YOKTUR, bu yüzden κ olarak sunulmuyor. Kanıt penceresi (`field_spans`) uyumu hiç ölçülmedi — insan tarafında span yalnız bazı kayıtlarda var, eksik veriyle κ hesaplamak sayıyı uydurmak olurdu.

## Alan bazında uyum

Marjinal sayılar (kaç kez "dolu" dendi) tabloda BİLEREK duruyor: κ'yı onlar olmadan okumak yanıltıcıdır (aşağıdaki paradoks notu).

| Alan | çift | gözlenen uyum | insan "dolu" | LLM "dolu" | κ |
|---|---|---|---|---|---|
| `alisveris_puani` | 16 | 13/16 | 3 | 0 | 0.000 |
| `finansman_tutari` | 16 | 15/16 | 1 | 0 | 0.000 |
| `hedef_kitle` | 16 | 14/16 | 6 | 8 | 0.750 |
| `indirim_orani` | 16 | 16/16 | 1 | 1 | 1.000 |
| `kampanya_kosullari` | 16 | 14/16 | 10 | 10 | 0.733 |
| `kampanya_suresi` | 16 | 15/16 | 7 | 8 | 0.875 |
| `kar_payi_orani` | 16 | 16/16 | 0 | 0 | 1.000 |
| `masraf_durumu` | 16 | 12/16 | 3 | 1 | -0.103 |
| `odul_miktari` | 16 | 14/16 | 3 | 5 | 0.673 |
| `tahsis_ucreti` | 16 | 16/16 | 0 | 0 | 1.000 |
| `taksit_sayisi` | 16 | 15/16 | 1 | 0 | 0.000 |
| `vade_ay` | 16 | 15/16 | 1 | 0 | 0.000 |

### κ paradoksu — yüksek uyum, sıfır κ

Yukarıdaki tabloda gözlenen uyumu 15/16 olup κ'sı **0.000** çıkan alanlar var. Bu bir hesap hatası değil, Cohen's κ'nın bilinen davranışı: κ gözlenen uyumdan ŞANS uyumunu düşer ve marjinal dağılım çok dengesiz olduğunda (her iki etiketleyici de neredeyse her belgede "yok" diyorsa) şans uyumu gözlenen uyuma yaklaşır, pay sıfıra iner. Yani κ o alanda "uyum yok" DEMİYOR; "bu marjinal dağılımda uyumun şanstan ayırt edilemeyeceğini" diyor.

Bu yüzden alan bazlı κ tek başına raporlanmaz: yanında gözlenen uyum ve iki tarafın "dolu" sayıları durur. Toplam κ (0'dan uzak) anlamlıdır çünkü 192 çiftte dağılım dengelidir.

**Negatif κ — gerçek bulgu:** `masraf_durumu` alanında κ sıfırın ALTINDA. Bu, yüksek gözlenen uyuma rağmen iki etiketleyicinin anlaşmazlığının sistematik olduğunu gösterir: aynı belgelerde ters yönde karar veriyorlar. Kılavuzun o alandaki tanımı belirsiz olabilir ve hakem turunun ilk bakacağı yer burasıdır.

**κ = 1.000 olan alanlar tam uyum DEĞİL, boş uyumdur:** `kar_payi_orani`, `tahsis_ucreti` alanlarında iki etiketleyici de HİÇBİR belgede "dolu" demedi. `cohen_kappa` beklenen uyum 1'e eşitken 1.0 döndürüyor (0/0 yerine "tam uyum" doğru yorum olduğu için) ama bu sayı "bu alanda mükemmel anlaşıyoruz" anlamına gelmez — o alanda 16 belgenin hiçbirinde ölçülecek bir karar yok. Kapsam sorunu olarak okunmalı: `kar_payi_orani` korpus kapsaması %3,4'tür ve bunun sebebi çıkarım değil kaynak yapısıdır (`docs/rapor/banka-siteleri-veri-kaynagi-haritasi.md`).

## Uyuşmazlıklar — hakeme gidecek liste

Toplam **32** uyuşmazlık. Hakem turu yalnız bunlara bakar; uyuşan kararlar yeniden açılmaz.

| Belge | Alan | Tür | İnsan | LLM |
|---|---|---|---|---|
| `turkiye-emlak-katilim--kampanya-beyaz-esya-ve-elektronik-alisverislerinize-3000-tlye-varan-parafpara` | `odul_miktari` | insan_yok_llm_dolu | `None` | `{'value': 300, 'currency': 'TRY'}` |
| `turkiye-emlak-katilim--kampanya-beyaz-esya-ve-elektronik-alisverislerinize-3000-tlye-varan-parafpara` | `alisveris_puani` | insan_dolu_llm_yok | `{'kind': 'points', 'value': 3000}` | `None` |
| `turkiye-emlak-katilim--kampanya-beyaz-esya-ve-elektronik-alisverislerinize-3000-tlye-varan-parafpara` | `kampanya_kosullari` | deger | `["Kampanyaya katılmak için HARCA yazıp 6026'ya SMS gönderilmesi gerekir", 'Yurt içi beyaz eşya, elektronik ve bilgisayar sektörlerinde tek seferde en az 5.000 TL ilk harcama yapılması gerekir', 'Bir müşteri kampanyadan bir defa yararlanabilir ve tek bir ParafPara tutarı kazanır', 'Pazar yeri e-ticaret sitelerinden yapılan harcamalar kampanyaya dahil değildir', 'Yalnızca Emlak Katılım Paraf ve Emlak Katılım Paraf Premium kartlar kampanyaya dahildir']` | `['Kampanya kapsamında yurt içi beyaz eşya, elektronik ve bilgisayar sektörlerinde tek seferde yapılacak 5.000 TL ile 14.999 TL arasındaki ilk harcamaya 300 TL, 15.000 TL ile 49.999 TL arasındaki ilk harcamaya 750 TL, 50.000 TL ile 99.999 TL arasındaki ilk harcamaya 1.750 TL, 100.000 TL ve üzeri ilk harcamaya 3.000 TL ParafPara verilecektir.', 'Kampanya müşteri bazlı olup bir müşteri kampanyadan bir defa yararlanabilir ve ilk alışveriş tutarına göre 300 TL, 750 TL, 1.750 TL ya da 3.000 TL ParafPara tutarından sadece birini kazanabilir.', 'Kampanyaya beyaz eşya, elektronik ve bilgisayar kategorisine giren fiziki ve sanal iş yerlerinde yapılan harcamalar dahildir.', 'Alışverişin yapıldığı iş yerinin, sistemde kayıtlı sektör bilgisinin doğru olmasının sorumluluğu iş yerine aittir.', 'Pazar yeri e-ticaret sitelerinden yapılan harcamalar kampanyaya dahil değildir.', 'Kampanyadan Emlak Katılım Paraf ve Emlak Katılım Paraf Premium kartlar faydalanabilecektir.', 'Sanal ve ek kartlar kampanyaya dahildir.', 'Alışverişin iptal/iade edilmesi durumunda ParafPara yüklenmeyecektir.', 'Finans kuruluşları ve ödeme hizmet sağlayıcıları üzerinden gerçekleşen harcama işlemleri ile dijital cüzdana yapılan yüklemeler ve dijital cüzdan kullanılarak yapılan harcamalar kampanyaya dahil değildir.', 'ParafPara kullanılarak yapılan alışverişler kampanyaya dahil değildir.']` |
| `turkiye-emlak-katilim--kampanya-beyaz-esya-ve-elektronik-alisverislerinize-3000-tlye-varan-parafpara` | `hedef_kitle` | insan_yok_llm_dolu | `None` | `['mevcut_musteri']` |
| `turkiye-emlak-katilim--kampanya-paraf-ile-secili-e-ticaret-alisverislerinize-1500-tlye-varan-parafpara` | `odul_miktari` | insan_yok_llm_dolu | `None` | `{'value': 1500, 'currency': 'TRY'}` |
| `turkiye-emlak-katilim--kampanya-paraf-ile-secili-e-ticaret-alisverislerinize-1500-tlye-varan-parafpara` | `alisveris_puani` | insan_dolu_llm_yok | `{'kind': 'points', 'value': 1500}` | `None` |
| `turkiye-emlak-katilim--kampanya-paraf-ile-secili-e-ticaret-alisverislerinize-1500-tlye-varan-parafpara` | `kampanya_kosullari` | deger | `["Kampanyaya katılmak için ALIŞVERİŞ yazıp 6026'ya SMS gönderilmesi gerekir", "Seçili e-ticaret siteleri ve mobil uygulamalarından Paraf POS'undan tek seferde 30.000 TL ve üzeri ilk taksitli harcama yapılması gerekir", 'Kampanya sadece taksitli işlemlerde geçerlidir', 'Bir müşteri kampanyadan bir defa yararlanabilir ve en fazla 1.500 TL ParafPara kazanabilir', 'Fiziki mağaza ve fiziki POS işlemleri kampanyaya dahil değildir']` | `['Kampanya sadece taksitli işlemlerde geçerlidir.', 'Bir müşteri kampanyadan bir defa yararlanabilir ve en fazla 1.500 TL ParafPara kazanabilir.', "Fiziki mağazalardan, fiziki POS'lardan ve ödeme kuruluşları aracılığıyla yapılan işlemler kampanyaya dahil olmayıp, kampanya koşullarında yer alan seçili internet sitelerinden ve mobil uygulamalarından ve Paraf POS'larından gerçekleştirilen alışverişler kampanyaya dahildir.", 'Market, Altın & Gümüş, Hat, Bilet vd belirli kategorilerden yapılan alışverişler kampanya kapsamında değildir.', 'Sanal ve ek kartlar kampanyaya dahildir.', 'Alışverişin iptal/iade edilmesi durumunda ParafPara yüklenmeyecektir.', 'Fatura ödemesi, düzenli ödeme, para yatırma-çekme, vergi ve bağış ödemesi, BES ödemesi, bakiye görüntüleme ve para transferi işlemleri kampanyaya dahil değildir.', 'Finans kuruluşları ve ödeme hizmet sağlayıcıları üzerinden gerçekleşen harcama işlemleri ile dijital cüzdana yapılan yüklemeler ve dijital cüzdan kullanılarak yapılan harcamalar kampanyaya dahil değildir.', 'ParafPara kullanılarak yapılan alışverişler kampanyaya dahil değildir.']` |
| `turkiye-emlak-katilim--kampanya-paraf-ile-secili-e-ticaret-alisverislerinize-1500-tlye-varan-parafpara` | `hedef_kitle` | insan_yok_llm_dolu | `None` | `['belirli_segment']` |
| `vakif-katilim--hesaplar-ozel-cari-hesaplar` | `masraf_durumu` | insan_dolu_llm_yok | `{'has_fee': False, 'amount': 0.0}` | `None` |
| `adil-katilim--katilim-bankaciligi-urun-ve-hizmetler` | `masraf_durumu` | insan_yok_llm_dolu | `None` | `{'has_fee': False, 'amount': 0}` |
| `adil-katilim--katilim-bankaciligi-urun-ve-hizmetler` | `kampanya_kosullari` | insan_yok_llm_dolu | `None` | `["Metin 'kâr payı uygulanmaz' ifadesinde masrafsız finansman belirtilmiş."]` |
| `hayat-finans--kampanyalar-hayat-finans-ile-gastroclub-ayricaliklari` | `masraf_durumu` | insan_dolu_llm_yok | `{'has_fee': False, 'amount': 0.0}` | `None` |
| `hayat-finans--kampanyalar-hayat-finans-ile-gastroclub-ayricaliklari` | `indirim_orani` | deger | `{'min': 10.0, 'max': 50.0}` | `{'min': 0.1, 'max': 0.5}` |
| `hayat-finans--kampanyalar-hayat-finans-ile-gastroclub-ayricaliklari` | `kampanya_suresi` | insan_yok_llm_dolu | `None` | `2023-04-18T00:00:00Z` |
| `hayat-finans--kampanyalar-hayat-finans-ile-gastroclub-ayricaliklari` | `kampanya_kosullari` | deger | `['Sadece bireysel Hayat Finans müşterileri yararlanabilir.', 'Bu kampanya diğer davet kodlu kampanyalarla birleştirilemez.', 'İndirim oranları ve geçerli markalar Hayat Finans uygulamasında Kampanyalar > Ayrıcalıklar alanından güncel olarak görüntülenebilir.']` | `['Sadece bireysel Hayat Finans müşterileri yararlanabilir.', 'Bu kampanya diğer davet kodlu kampanyalarla birleştirilemez.']` |
| `tom-katilim--kampanyalar-a101de-her-alisveriste-3-nakit-iade` | `alisveris_puani` | insan_dolu_llm_yok | `{'kind': 'rate', 'value': 3.0}` | `None` |
| `tom-katilim--kampanyalar-a101de-her-alisveriste-3-nakit-iade` | `kampanya_kosullari` | deger | `["Kampanya'dan faydalanmak için Hadi Gold üyesi olmalısın.", 'Kampanya kapsamında bir takvim ayında en fazla 125 TL nakit iade kazanılabilir', 'Kampanyadan aynı gün içerisinde en fazla 5 farklı işlemden kazanım sağlanabilir.', '1 Eylül 2026 itibarıyla iade oranı %1 olarak güncellenecektir.', 'Hadi Veresiye kullandığın alışverişlerinde nakit iade kazanımı yoktur.']` | `['Kampanyadan faydalanmak için Hadi Gold üyesi olmalısın.', 'Hadi Kredi Kartları ile yapacağın işlemler için kazandığın nakit iade ortalama 5 gün içerisinde kredi kartına yansıtılır.', 'Hadi Kredi Kartları ile kazanım sağlamak için açık kredi kartına sahip olman gerekmektedir.', "Henüz Hadi Kredi Kartları'ndan birine sahibi değilsen, başvurmak için TOM Bank Hadi uygulamasını ziyaret edebilirsin."]` |
| `ziraat-katilim--konut-finansmani-kentsel-donusum-finansmani` | `finansman_tutari` | insan_dolu_llm_yok | `{'value': 1250000.0, 'currency': 'TRY'}` | `None` |
| `ziraat-katilim--konut-finansmani-kentsel-donusum-finansmani` | `vade_ay` | insan_dolu_llm_yok | `120` | `None` |
| `ziraat-katilim--konut-finansmani-kentsel-donusum-finansmani` | `kampanya_kosullari` | deger | `["T.C. Çevre ve Şehircilik Bakanlığı tarafından belirlenen kâr destek oranlarından faydanılabilmesi için, gayrimenkulün riskli alanda bulunması ve riskli alan içinde yer almamakla birlikte gayrimenkulün ‘'riskli yapı'' olduğuna dair teknik raporlarla tespit edilmiş olması gerekmektedir.", 'Riskli yapılarda en az 1 yıl oturan kiracı veya sınırlı ayni hak sahipleri']` | `['Kentsel Dönüşüm Finansmanı, T.C. Çevre ve Şehircilik Bakanlığı tarafından belirlenen riskli alanda bulunan binalar için kullanılabilmektedir.', "Gayrimenkulün riskli alanda bulunması ve riskli alan içinde yer almamakla birlikte gayrimenkulün ‘'riskli yapı'' olduğuna dair teknik raporlarla tespit edilmiş olması gerekmektedir.", 'Konutlarını yeniden inşa etmek isteyen hak sahipleri, Riskli yapılarda en az 1 yıl oturan kiracı veya sınırlı ayni hak sahipleri, Konutu riskli yapı olarak tespit edilen ve farklı bir konut almak isteyen malikleri Kentsel Dönüşüm Finansmanından yararlanabilirler.', 'Kentsel Dönüşüm Finansmanı için azami vade 10 yıl olup, bireysel işyeri finansmanı için ise 7 yıl olmaktadır.']` |
| `hayat-finans--yatirim-ve-birikim-hisse-senedi-islemleri-yatirim-ve-birikim` | `masraf_durumu` | insan_dolu_llm_yok | `{'has_fee': True, 'amount': None}` | `None` |
| `hayat-finans--yatirim-ve-birikim-hisse-senedi-islemleri-yatirim-ve-birikim` | `kampanya_kosullari` | insan_dolu_llm_yok | `['Hisse senedi hesap açılışı için Uygunluk Testi yapılması zorunludur.', 'Yalnızca Borsa İstanbul Katılım Endeksi hisse senetlerinde alım-satım yapılabilir.', '2 dönem üst üste katılım endeksi kriterlerine uymayan hisse senetlerinde yalnız satışa izin verilir, alış yapılamaz.']` | `None` |
| `vakif-katilim--detay-ria-a101-hediye-ceki-kampanyasi` | `kampanya_suresi` | deger | `2026-03-18` | `2026-02-01T00:00:00Z/2026-03-18T23:59:59Z` |
| `vakif-katilim--detay-ria-a101-hediye-ceki-kampanyasi` | `kampanya_kosullari` | deger | `['Gelen Ria havalesinin Vakıf Katılım Mobil Şube üzerinden hesaba alınması gerekir.', "A101 hediye çekleri Mobil Şube'den işlem yapan kişilere bir (1) defaya mahsus verilir.", 'Hediye çeki kampanya süresini takip eden 15 iş günü içinde SMS ile iletilir.', 'Hediye çeki stoklarla sınırlıdır; hedef sayıya ulaşıldığında gönderim sonlandırılır.']` | `['Kampanya, belirlenen tarihler içerisinde, gelen Ria ödemesini Vakıf Katılım Mobil Şubesini kullanarak hesaplarına aktaran yeni müşterilerimiz için düzenlenmektedir.', "Ria işlemini mobil şubemizden yapacak kişilere 500 TL'lik A101 hediye çeki verilecektir.", 'Hediye çekleri, ödül kazanan kişilerin işlem yaptıkları cep telefonlarına SMS kodu olarak iletilecektir.', "Gönderilen SMS kodu ile A101 marketlerinde 500 TL'lik alışveriş yapılması mümkün olacaktır."]` |
| `dunya-katilim--kampanyalar-carter-s` | `taksit_sayisi` | insan_dolu_llm_yok | `4` | `None` |
| `dunya-katilim--kampanyalar-carter-s` | `kampanya_kosullari` | deger | `['Kampanyadan Dünya Katılım Paraf kartlar faydalanabilecektir', 'Sanal kartlar kampanyaya dahildir', 'ParafPara kullanılarak yapılan işlemler ile iptal ve iade işlemleri dahil değildir', '4 taksitten yararlanabilmek için kampanyanın satış görevlisine belirtilmesi gerekmektedir', 'www.cartersoshkosh.com.tr web sitesinden yapılacak işlemler kampanyaya dahil değildir']` | `['4 taksit imkanı, kampanyadan Dünya Katılım Paraf kartlar faydalanılabilir.', 'Sanal kartlar kampanyaya dahildir.', 'İptal ve iade işlemleri ile 4 taksitten yararlanabilmek için kampanyanın satış görevlisine belirtilmesi gerekmektedir.', 'www.cartersoshkosh.com.tr web sitesinden yapılacak işlemler kampanyaya dahil değildir.']` |
| `kuveyt-turk--musteri-ol-kampanyalari-kuveyt-turk-mobilden-musterimiz-olun-ozel-kur-firsatini-` | `kampanya_suresi` | deger | `2026-09-01` | `2026-05-15/2026-09-01` |
| `kuveyt-turk--musteri-ol-kampanyalari-kuveyt-turk-mobilden-musterimiz-olun-ozel-kur-firsatini-` | `kampanya_kosullari` | deger | `['Özel kurlar döviz ve kıymetli maden işlemlerinizde geçerlidir ve mobil uygulama üzerinden görüntülenebilir', "Özel kurlar Kuveyt Türk Mobil' den müşterimiz olan bireysel müşterileriz için otomatik olarak tanımlanır"]` | `["Kuveyt Türk Mobil'den müşterimiz olan bireysel müşterilerimize özel avantajlı kur fırsatları.", "Kuveyt Türk Mobil' den müşterimiz olan bireysel müşterileriz için otomatik olarak tanımlanır."]` |
| `kuveyt-turk--musteri-ol-kampanyalari-kuveyt-turk-mobilden-musterimiz-olun-ozel-kur-firsatini-` | `hedef_kitle` | deger | `['yeni_musteri']` | `['mevcut_musteri']` |
| `tom-katilim--kampanyalar-hadi-kredi-karti-limitini-artir-toplam-2000-tlye-kadar-a101-hediye-b` | `kampanya_suresi` | deger | `2026-08-31` | `2026-07-31T00:00:00` |
| `tom-katilim--kampanyalar-hadi-kredi-karti-limitini-artir-toplam-2000-tlye-kadar-a101-hediye-b` | `kampanya_kosullari` | deger | `['Kampanyadan faydalanabilmek için tarafınıza ilgili kampanya SMS yolu ile iletilmiş olmalıdır', 'Kampanya limiti artırılan Hadi Kredi Kartları ile en az 5 farklı günde, toplam en az 10.000 TL harcamada geçerlidir', "Kampanya 31 Temmuz'a kadar mevcut kredi kartı limitini artıran seçili müşteriler için geçerlidir", 'Kampanyaya sadece yurt içinde yapılan harcamalar dahildir', 'Kampanya kapsamındaki alışverişlerin iptal/iade olması durumlarında, iade kazanılmaz']` | `['Kampanyanın bitiş tarihi sonrası iade kazanılmaz.', 'Kampanya kapsamındaki alışverişlerin iptal/iade olması durumlarında, iade kazanılmaz.', 'Önceki dönemden bir kazanım var ise, kazanım tutarı kredi kartına borç olarak yansıtılır.', 'Kampanyaya sadece yurt içinde yapılan harcamalar dahildir.']` |
| `tom-katilim--kampanyalar-hadi-kredi-karti-limitini-artir-toplam-2000-tlye-kadar-a101-hediye-b` | `hedef_kitle` | deger | `['belirli_segment']` | `['mevcut_musteri']` |

## Yöntem

1. 48 kayıttan 16'sı seçildi: her insan etiketleyici bloğundan 4, blok içinde id sırasına göre EŞİT ARALIKLA (ilk 4 değil — bloklar zorluk sırasına dizilmiş olabilir ve baştan almak bir zorluk bandını sistematik dışlardı). Seçim tohumsuz ve tekrar-üretilebilir.
2. LLM her belgeyi bağımsız etiketledi (`llm.call(text)`), gold'u görmeden.
3. Varlık kararları eşleştirildi; karar verilmemiş alanlar (`fields`'ta da `absent_fields`'ta da olmayan) çiftten ATILDI.
4. κ `eval/iaa.cohen_kappa` ile, değer uyumu `eval/matchers.tolerant_match` ile — resmî metriğin AYNI kodu.

Üretim: `python -m scripts.ikinci_etiketleyici kappa`
