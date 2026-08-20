# κ (Cohen's kappa) — ikinci etiketleyici turu (İNSAN)

**İkinci etiketleyici bir İNSANDIR** (proje sahibi, `INSAN-01`). Bu, jürinin "κ'da ikinci etiketleyiciyi insana taşı" gerekçesini karşılar: ölçülen şey artık model-model uyumu değil, iki BAĞIMSIZ İNSAN yargıcın (birincil anotatör + `INSAN-01`) uyumudur ve κ'nın klasik tanımına birebir uyar. `INSAN-01` gold değerini de kural motoru/LLM çıktısını da GÖRMEDİ — yalnız belge metnini ve alan şemasını gördü (`scripts/ikinci_etiketleyici._alan_sor` körlemesi; ayrıntı: `tests/test_insan_etiketleyici.py`).

* etiketleyici: `insan` / `INSAN-01`
* belge: **16** (insan hatası: 0)
* κ çifti (karar verilmiş (belge, alan) ikilisi): **192**
* toplam insan süresi: 287 dk

## Sonuç

| Ölçüt | Değer |
|---|---|
| κ — varlık kararı (dolu / absent) | **0.716** (notla) |
| Değer uyumu — birebir (iki taraf da dolu) | 18/24 = 0.750 |
| Krippendorff α (`ratio`, sayısal alanlar) | 0.760 — **YETERSİZ BİRİM** (9 < 10) |

α 9 sayısal birim üzerinden hesaplandı ve bu sayı bir iddiaya taban olamaz: tek bir birimin değişmesi α'yı 1.000'den sıfıra düşürebilir. Sebep kapsam: 26 ortak-dolu çiftin çoğu liste ya da serbest metin alanı (`hedef_kitle`, `kampanya_kosullari`) ve `ratio` ölçeğine oturmuyor; aralık değerleri de (`comparable=False`) atlanıyor. Kılavuz §7'nin vaat ettiği α ÖLÇÜLDÜ ama şu korpus kesitinde anlamlı değil — sayının kendisi değil bu sınır raporlanıyor.

`κ` yalnız **varlık** kararını ölçer: "bu alan bu belgede var mı?". Değer uyumu ayrı satırda ve şans düzeltmesi YOKTUR, bu yüzden κ olarak sunulmuyor. Kanıt penceresi (`field_spans`) uyumu hiç ölçülmedi — insan tarafında span yalnız bazı kayıtlarda var, eksik veriyle κ hesaplamak sayıyı uydurmak olurdu.

## Alan bazında uyum

Marjinal sayılar (kaç kez "dolu" dendi) tabloda BİLEREK duruyor: κ'yı onlar olmadan okumak yanıltıcıdır (aşağıdaki paradoks notu).

| Alan | çift | gözlenen uyum | gold/birincil "dolu" | `INSAN-01` "dolu" | κ |
|---|---|---|---|---|---|
| `alisveris_puani` | 16 | 16/16 | 3 | 3 | 1.000 |
| `finansman_tutari` | 16 | 16/16 | 1 | 1 | 1.000 |
| `hedef_kitle` | 16 | 12/16 | 6 | 4 | 0.429 |
| `indirim_orani` | 16 | 16/16 | 1 | 1 | 1.000 |
| `kampanya_kosullari` | 16 | 10/16 | 10 | 4 | 0.333 |
| `kampanya_suresi` | 16 | 16/16 | 7 | 7 | 1.000 |
| `kar_payi_orani` | 16 | 16/16 | 0 | 0 | 1.000 |
| `masraf_durumu` | 16 | 14/16 | 2 | 0 | 0.000 |
| `odul_miktari` | 16 | 14/16 | 3 | 5 | 0.673 |
| `tahsis_ucreti` | 16 | 16/16 | 0 | 0 | 1.000 |
| `taksit_sayisi` | 16 | 15/16 | 1 | 2 | 0.636 |
| `vade_ay` | 16 | 16/16 | 1 | 1 | 1.000 |

### κ paradoksu — yüksek uyum, sıfır κ

Yukarıdaki tabloda gözlenen uyumu 15/16 olup κ'sı **0.000** çıkan alanlar var. Bu bir hesap hatası değil, Cohen's κ'nın bilinen davranışı: κ gözlenen uyumdan ŞANS uyumunu düşer ve marjinal dağılım çok dengesiz olduğunda (her iki etiketleyici de neredeyse her belgede "yok" diyorsa) şans uyumu gözlenen uyuma yaklaşır, pay sıfıra iner. Yani κ o alanda "uyum yok" DEMİYOR; "bu marjinal dağılımda uyumun şanstan ayırt edilemeyeceğini" diyor.

Bu yüzden alan bazlı κ tek başına raporlanmaz: yanında gözlenen uyum ve iki tarafın "dolu" sayıları durur. Toplam κ (0'dan uzak) anlamlıdır çünkü 192 çiftte dağılım dengelidir.

Negatif κ'lı alan yok — hiçbir alanda sistematik ters karar örüntüsü ölçülmedi.

**κ = 1.000 olan alanlar tam uyum DEĞİL, boş uyumdur:** `kar_payi_orani`, `tahsis_ucreti` alanlarında iki etiketleyici de HİÇBİR belgede "dolu" demedi. `cohen_kappa` beklenen uyum 1'e eşitken 1.0 döndürüyor (0/0 yerine "tam uyum" doğru yorum olduğu için) ama bu sayı "bu alanda mükemmel anlaşıyoruz" anlamına gelmez — o alanda 16 belgenin hiçbirinde ölçülecek bir karar yok. Kapsam sorunu olarak okunmalı: `kar_payi_orani` korpus kapsaması %3,4'tür ve bunun sebebi çıkarım değil kaynak yapısıdır (`docs/rapor/banka-siteleri-veri-kaynagi-haritasi.md`).

## Uyuşmazlıklar — hakeme gidecek liste

Toplam **21** uyuşmazlık. Hakem turu yalnız bunlara bakar; uyuşan kararlar yeniden açılmaz.

| Belge | Alan | Tür | İnsan | LLM |
|---|---|---|---|---|
| `turkiye-emlak-katilim--kampanya-beyaz-esya-ve-elektronik-alisverislerinize-3000-tlye-varan-parafpara` | `odul_miktari` | insan_yok_llm_dolu | `None` | `{'value': 3000.0, 'currency': 'TRY'}` |
| `turkiye-emlak-katilim--kampanya-beyaz-esya-ve-elektronik-alisverislerinize-3000-tlye-varan-parafpara` | `kampanya_kosullari` | deger | `["Kampanyaya katılmak için HARCA yazıp 6026'ya SMS gönderilmesi gerekir", 'Yurt içi beyaz eşya, elektronik ve bilgisayar sektörlerinde tek seferde en az 5.000 TL ilk harcama yapılması gerekir', 'Bir müşteri kampanyadan bir defa yararlanabilir ve tek bir ParafPara tutarı kazanır', 'Pazar yeri e-ticaret sitelerinden yapılan harcamalar kampanyaya dahil değildir', 'Yalnızca Emlak Katılım Paraf ve Emlak Katılım Paraf Premium kartlar kampanyaya dahildir']` | `['Kampanyaya katılmak için "HARCA" yazıp 6026\'ya SMS gönderilmesi gerekmektedir. Kampanya katılımının başarılı sayılabilmesi için banka sisteminde adınıza tanımlı telefon numarasından katılım sağlanmalıdır. Katılım SMS\'i ücretsiz olup; kampanyaya katılabilmek için SMS\'in Turkcell, Vodafone veya Türk Telekom operatörleri üzerinden ve yurt içinden gönderilmesi gerekmektedir. Kampanya Koşulları Kampanya 1-31 Temmuz 2026 tarihleri arasında geçerlidir. Kampanya kapsamında yurt içi beyaz eşya, elektronik ve bilgisayar sektörlerinde tek seferde yapılacak 5.000 TL ile 14.999 TL arasındaki ilk harcamaya 300 TL, 15.000 TL ile 49.999 TL arasındaki ilk harcamaya 750 TL, 50.000 TL ile 99.999 TL arasındaki ilk harcamaya 1.750 TL, 100.000 TL ve üzeri ilk harcamaya 3.000 TL ParafPara verilecektir. Kampanya müşteri bazlı olup bir müşteri kampanyadan bir defa yararlanabilir ve ilk alışveriş tutarına göre 300 TL, 750 TL, 1.750 TL ya da 3.000 TL ParafPara tutarından sadece']` |
| `turkiye-emlak-katilim--kampanya-paraf-ile-secili-e-ticaret-alisverislerinize-1500-tlye-varan-parafpara` | `odul_miktari` | insan_yok_llm_dolu | `None` | `{'value': 1500.0, 'currency': 'TRY'}` |
| `turkiye-emlak-katilim--kampanya-paraf-ile-secili-e-ticaret-alisverislerinize-1500-tlye-varan-parafpara` | `kampanya_kosullari` | deger | `["Kampanyaya katılmak için ALIŞVERİŞ yazıp 6026'ya SMS gönderilmesi gerekir", "Seçili e-ticaret siteleri ve mobil uygulamalarından Paraf POS'undan tek seferde 30.000 TL ve üzeri ilk taksitli harcama yapılması gerekir", 'Kampanya sadece taksitli işlemlerde geçerlidir', 'Bir müşteri kampanyadan bir defa yararlanabilir ve en fazla 1.500 TL ParafPara kazanabilir', 'Fiziki mağaza ve fiziki POS işlemleri kampanyaya dahil değildir']` | `['Kampanyaya katılmak için " ALIŞVERİŞ " yazıp 6026\'ya SMS gönderilmesi gerekmektedir. Kampanya katılımının başarılı sayılabilmesi için banka sisteminde adınıza tanımlı telefon numarasından katılım sağlanmalıdır.']` |
| `turkiye-emlak-katilim--kampanya-paraf-ile-secili-e-ticaret-alisverislerinize-1500-tlye-varan-parafpara` | `hedef_kitle` | insan_yok_llm_dolu | `None` | `['mevcut_musteri']` |
| `vakif-katilim--hesaplar-ozel-cari-hesaplar` | `masraf_durumu` | insan_dolu_llm_yok | `{'has_fee': False, 'amount': 0.0}` | `None` |
| `hayat-finans--kampanyalar-hayat-finans-ile-gastroclub-ayricaliklari` | `kampanya_kosullari` | insan_dolu_llm_yok | `['Sadece bireysel Hayat Finans müşterileri yararlanabilir.', 'Bu kampanya diğer davet kodlu kampanyalarla birleştirilemez.', 'İndirim oranları ve geçerli markalar Hayat Finans uygulamasında Kampanyalar > Ayrıcalıklar alanından güncel olarak görüntülenebilir.']` | `None` |
| `hayat-finans--kampanyalar-hayat-finans-ile-gastroclub-ayricaliklari` | `hedef_kitle` | insan_dolu_llm_yok | `['mevcut_musteri']` | `None` |
| `tom-katilim--kampanyalar-a101de-her-alisveriste-3-nakit-iade` | `taksit_sayisi` | insan_yok_llm_dolu | `None` | `3` |
| `tom-katilim--kampanyalar-a101de-her-alisveriste-3-nakit-iade` | `alisveris_puani` | deger | `{'kind': 'rate', 'value': 3.0}` | `{'kind': 'points', 'value': 2000.0}` |
| `tom-katilim--kampanyalar-a101de-her-alisveriste-3-nakit-iade` | `kampanya_kosullari` | insan_dolu_llm_yok | `["Kampanya'dan faydalanmak için Hadi Gold üyesi olmalısın.", 'Kampanya kapsamında bir takvim ayında en fazla 125 TL nakit iade kazanılabilir', 'Kampanyadan aynı gün içerisinde en fazla 5 farklı işlemden kazanım sağlanabilir.', '1 Eylül 2026 itibarıyla iade oranı %1 olarak güncellenecektir.', 'Hadi Veresiye kullandığın alışverişlerinde nakit iade kazanımı yoktur.']` | `None` |
| `tom-katilim--kampanyalar-a101de-her-alisveriste-3-nakit-iade` | `hedef_kitle` | insan_dolu_llm_yok | `['belirli_segment']` | `None` |
| `ziraat-katilim--konut-finansmani-kentsel-donusum-finansmani` | `finansman_tutari` | deger | `{'value': 1250000.0, 'currency': 'TRY'}` | `{'value': 6000000.0, 'currency': 'TRY'}` |
| `ziraat-katilim--konut-finansmani-kentsel-donusum-finansmani` | `kampanya_kosullari` | insan_dolu_llm_yok | `["T.C. Çevre ve Şehircilik Bakanlığı tarafından belirlenen kâr destek oranlarından faydanılabilmesi için, gayrimenkulün riskli alanda bulunması ve riskli alan içinde yer almamakla birlikte gayrimenkulün ‘'riskli yapı'' olduğuna dair teknik raporlarla tespit edilmiş olması gerekmektedir.", 'Riskli yapılarda en az 1 yıl oturan kiracı veya sınırlı ayni hak sahipleri']` | `None` |
| `ziraat-katilim--konut-finansmani-kentsel-donusum-finansmani` | `hedef_kitle` | insan_dolu_llm_yok | `['belirli_segment']` | `None` |
| `hayat-finans--yatirim-ve-birikim-hisse-senedi-islemleri-yatirim-ve-birikim` | `masraf_durumu` | insan_dolu_llm_yok | `{'has_fee': True, 'amount': None}` | `None` |
| `hayat-finans--yatirim-ve-birikim-hisse-senedi-islemleri-yatirim-ve-birikim` | `kampanya_kosullari` | insan_dolu_llm_yok | `['Hisse senedi hesap açılışı için Uygunluk Testi yapılması zorunludur.', 'Yalnızca Borsa İstanbul Katılım Endeksi hisse senetlerinde alım-satım yapılabilir.', '2 dönem üst üste katılım endeksi kriterlerine uymayan hisse senetlerinde yalnız satışa izin verilir, alış yapılamaz.']` | `None` |
| `vakif-katilim--detay-ria-a101-hediye-ceki-kampanyasi` | `kampanya_kosullari` | insan_dolu_llm_yok | `['Gelen Ria havalesinin Vakıf Katılım Mobil Şube üzerinden hesaba alınması gerekir.', "A101 hediye çekleri Mobil Şube'den işlem yapan kişilere bir (1) defaya mahsus verilir.", 'Hediye çeki kampanya süresini takip eden 15 iş günü içinde SMS ile iletilir.', 'Hediye çeki stoklarla sınırlıdır; hedef sayıya ulaşıldığında gönderim sonlandırılır.']` | `None` |
| `dunya-katilim--kampanyalar-carter-s` | `kampanya_kosullari` | deger | `['Kampanyadan Dünya Katılım Paraf kartlar faydalanabilecektir', 'Sanal kartlar kampanyaya dahildir', 'ParafPara kullanılarak yapılan işlemler ile iptal ve iade işlemleri dahil değildir', '4 taksitten yararlanabilmek için kampanyanın satış görevlisine belirtilmesi gerekmektedir', 'www.cartersoshkosh.com.tr web sitesinden yapılacak işlemler kampanyaya dahil değildir']` | `['4 taksitten yararlanabilmek için kampanyanın satış görevlisine belirtilmesi gerekmektedir.']` |
| `kuveyt-turk--musteri-ol-kampanyalari-kuveyt-turk-mobilden-musterimiz-olun-ozel-kur-firsatini-` | `kampanya_kosullari` | insan_dolu_llm_yok | `['Özel kurlar döviz ve kıymetli maden işlemlerinizde geçerlidir ve mobil uygulama üzerinden görüntülenebilir', "Özel kurlar Kuveyt Türk Mobil' den müşterimiz olan bireysel müşterileriz için otomatik olarak tanımlanır"]` | `None` |
| `tom-katilim--kampanyalar-hadi-kredi-karti-limitini-artir-toplam-2000-tlye-kadar-a101-hediye-b` | `kampanya_kosullari` | deger | `['Kampanyadan faydalanabilmek için tarafınıza ilgili kampanya SMS yolu ile iletilmiş olmalıdır', 'Kampanya limiti artırılan Hadi Kredi Kartları ile en az 5 farklı günde, toplam en az 10.000 TL harcamada geçerlidir', "Kampanya 31 Temmuz'a kadar mevcut kredi kartı limitini artıran seçili müşteriler için geçerlidir", 'Kampanyaya sadece yurt içinde yapılan harcamalar dahildir', 'Kampanya kapsamındaki alışverişlerin iptal/iade olması durumlarında, iade kazanılmaz']` | `['Kampanya limiti artırılan Hadi Kredi Kartları ile en az 5 farklı günde, toplam en az 10.000 TL harcamada geçerlidir.', 'Kampanya 31 Temmuz’a kadar mevcut kredi kartı limitini artıran seçili müşteriler için geçerlidir.', 'Kampanyaya sadece yurt içinde yapılan harcamalar dahildir.', 'Kampanya kapsamındaki alışverişlerin iptal/iade olması durumlarında, iade kazanılmaz.', 'Önceki dönemden bir kazanım var ise, kazanım tutarı kredi kartına borç olarak yansıtılır.']` |

## Yöntem

1. 48 kayıttan 16'sı seçildi: her insan etiketleyici bloğundan 4, blok içinde id sırasına göre EŞİT ARALIKLA (ilk 4 değil — bloklar zorluk sırasına dizilmiş olabilir ve baştan almak bir zorluk bandını sistematik dışlardı). Seçim tohumsuz ve tekrar-üretilebilir.
2. LLM her belgeyi bağımsız etiketledi (`llm.call(text)`), gold'u görmeden.
3. Varlık kararları eşleştirildi; karar verilmemiş alanlar (`fields`'ta da `absent_fields`'ta da olmayan) çiftten ATILDI.
4. κ `eval/iaa.cohen_kappa` ile, değer uyumu `eval/matchers.tolerant_match` ile — resmî metriğin AYNI kodu.

Üretim: `python -m scripts.ikinci_etiketleyici kappa --girdi data/gold/review/ikinci-tur-insan.jsonl`
