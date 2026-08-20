# Veri Kaynağı İstihbaratı — Kâr Payı Oranı Kapsamını Artırma

**Tarih:** 2026-08-20
**Yöntem:** Yalnız web araması + sayfa okuma (WebSearch/WebFetch). Hasat/indirme yapılmadı, `data/raw` değiştirilmedi.
**Amaç:** `kar_payi_orani` alanının 2.592 belgenin yalnız %5,7'sinde (147 belge) dolu olması sorununa karşı yeni kaynak adayları haritalamak.

---

## 1. Kâr payı oranı kaynakları — banka başına

| Kurum | Sayfa türü | URL | Biçim | Erişilebilirlik |
|---|---|---|---|---|
| Kuveyt Türk | Kâr payı hesaplama aracı | https://www.kuveytturk.com.tr/en/calculation-tools | HTML/JS araç, sabit tablo değil | Erişilebilir ama oran tablo halinde değil — hesaplayıcı |
| Kuveyt Türk | Ticari Ürün ve Hizmet Ücret Tablosu | https://www.kuveytturk.com.tr/medium/ticari-urun-ve-hizmet-ucret-tablosu-3834.pdf | PDF | Erişilebilir; ticari ücretler, kâr payı oranı değil |
| Kuveyt Türk | Sermaye Piyasası İşlemleri Komisyon ve Ücret Tarifesi | https://www.kuveytturk.com.tr/medium/sermaye-piyasasi-islemleri-komisyon-ve-ucret-tarif-3443.pdf | PDF | Erişilebilir; kapsam dışı (yatırım işlemleri) |
| Albaraka Türk | **Kâr Paylaşım Oranları PDF** | https://www.albaraka.com.tr/documents/bireysel/hesaplar/PDF/kar-paylasim-oranlari.pdf | PDF (dosya adı `kar-paylasim-oranlari-09-07-25`, meta tarih 22 Temmuz 2026) | Erişilebilir — periyodik güncellenen doğrudan PDF, düzenli isimlendirme kalıbı var (tarih sürümlü) → **otomatik izlenebilir aday** |
| Türkiye Finans | **Kar Payı Oranları (bireysel)** | https://www.turkiyefinans.com.tr/tr-tr/bireysel/sayfalar/kar-payi-oranlari.aspx | HTML tablo | Erişilebilir |
| Türkiye Finans | **Ticari Kâr Paylaşım Oranları** | https://www.turkiyefinans.com.tr/tr-tr/ticari/ticari-katilma-hesaplari/sayfalar/ticari-karpaylasim-oranlari.aspx | HTML tablo | Erişilebilir |
| Türkiye Finans | Komisyonlu-Taksitli Çalışma Koşulları Bildirim Tablosu | https://www.turkiyefinans.com.tr/tr-tr/sayfalar/komisyonlu-taksitli-calisma-kosullari-bildirim-tablosu.aspx | HTML tablo | Erişilebilir; BSMV, katkı payı, bonservis ücreti hariç tutulduğu belirtiliyor |
| Ziraat Katılım | Doğrudan resmi "kar payı oranları" tablo sayfası | *bulunamadı* | — | Aramalarda yalnız üçüncü taraf siteler (encazip, hangikredi, karpayihesapla) çıktı; ziraatkatilim.com.tr üzerinde ürün sayfaları var (`/bireysel/hesaplar/katilma-hesaplari/...`) ama merkezi bir oran tablosu sayfası tespit edilemedi |
| Vakıf Katılım | Kâr Paylaşım Oranları (Yardım Merkezi SSS) | https://www.vakifkatilim.com.tr/tr/diger/yardim-merkezi/kendim-icin-detay/hesaplar/kar-paylasim-oranlari | HTML — bu sayfa yönlendirme/SSS; asıl oran tablosu ayrı sayfada (linkte belirtiliyor ama tam URL doğrulanamadı) | Kısmen — takip gerekiyor |
| Vakıf Katılım | Profit Sharing Rates (EN) | https://www.vakifkatilim.com.tr/en/for-me/accounts/participation-accounts/profit-sharing-rates | HTML tablo (İngilizce sürüm) | Erişilebilir — TR eşleniği bulunmalı |
| Türkiye Emlak Katılım | **Ürün ve Hizmet Ücretleri** | https://www.emlakkatilim.com.tr/tr/urun-ve-hizmet-ucretleri | Sayfa → PDF linkleri (Bireysel/Ticari) | Erişilebilir; tahsis ücreti, dosya masrafı gibi alanlar PDF'lerde olabilir — **tahsis_ucreti/finansman_tutari kapsamını artırma adayı** |
| T.O.M. Katılım | **Kâr Paylaşım Oranları PDF** | https://www.tombank.com.tr/assets/images/doc/kpo.pdf | PDF, doğrudan tablo (Vade Türü × TL Kâra Katılma Oranı) | Erişilebilir — sabit URL, düzenli güncelleniyor görünüyor |
| Hayat Finans | Doğrudan resmi oran tablosu | *bulunamadı* | — | Yalnız ürün açıklama sayfaları (`/en/accounts/participation-account`) bulundu; sabit oran tablosu/PDF tespit edilemedi |
| Dünya Katılım | Katılma Hesapları sayfası | https://dunyakatilim.com.tr/kolayliklar/kendim-icin/hesaplar/katilma-hesaplari | HTML, oranlar vade bazlı anlatılıyor ama sabit tablo görülmedi | Kısmen |
| Adil Katılım | Ürün ve Hizmet Ücretlendirmeleri (PDF linki ana sayfada var, tam URL doğrulanamadı) | https://www.adilkatilim.com.tr (ana sayfadan link) | PDF (muhtemelen) | Kısmen — banka çok yeni (bkz. Bölüm 3), ürün/oran içeriği sınırlı olabilir |

**Not:** Üçüncü taraf siteler (karpayihesapla.com, encazip.com, enuygunfinans.com, hangikredi.com) neredeyse her banka için "güncel oran" sayfası üretiyor ve genelde resmi sayfadan daha kolay parse edilebilir görünüyor — ama Bölüm 5'teki kullanım koşulu kısıtına tabi.

---

## 2. Otorite kaynaklar — TKBB / BDDK / TCMB

### TKBB (Türkiye Katılım Bankaları Birliği)

- **Kâr Paylaşım Oranları veri sayfası (güncel):** https://tkbb.org.tr/veripetegi-detay/40 — "Veri Peteği" başlığı altında.
  - **Önemli teknik bulgu:** Eski/bilinen URL `https://karpayi.tkbb.org.tr/veri/karpaylari` artık **kalıcı olarak (HTTP 301) bu sayfaya yönlendiriyor**. Eski alt alan adının SSL sertifikası süresi dolmuş durumda (tarayıcıdan doğrudan erişimde "certificate has expired" hatası veriyor); `curl -k` ile zorlandığında 301 yönlendirmesi görülüyor. Yani veri hâlâ yayında ama **URL değişmiş** — mevcut korpus/scraper konfigürasyonu eski URL'i hedefliyorsa güncellenmesi gerekir.
  - İçerik: WebSearch özetine göre "hesap vadesi dolan hesaplara dağıtılan yıllık brüt kâr payı oranları" — pazartesi resmi tatile denk gelirse bir sonraki iş günü verisi gösteriliyor. Banka bazında kırılım olduğu düşünülüyor (TKBB üye bankaları için) ama sayfanın canlı içeriği bu oturumda doğrudan okunamadı (JS/tablo render sorunu). **Doğrulama gerekiyor.**
- **Düzenleme — Bireysel Finansman İşlemlerinde Kâr Payı Oranlarının İlan İlkeleri:**
  - Güncel: https://tkbb.org.tr/mevzuat/birligimiz-duzenlemeleri-details/1394 — 1 Ocak 2010'dan itibaren yürürlükte; bankaların ilan/reklamlarda "Yıllık Toplam Kâr Payı Maliyeti Tablosu" kullanmasını zorunlu kılıyor (akdi kâr payı oranı + dosya/tahsis/kullandırım ücretleri + haberleşme/istihbarat masrafları + kâr payı indirimi komisyonları dahil; ekspertiz/ipotek/sigorta hariç).
  - **ÇELİŞKİ/DİKKAT:** Aynı başlıkta bir de "Mülga" (yürürlükten kalkmış) sürüm var: https://tkbb.org.tr/duzenlemeler-detay/bireysel-finansman-islemlerinde-kar-payi-oranlarinin-ilan-ilkeleri---mulga — hangisinin güncel, hangisinin eski olduğu bu oturumda netleştirilemedi (mülga sayfa tarih/gerekçe içermiyor). Kullanılacaksa iki sayfa karşılaştırılıp tarihlendirilmeli.
- **TKBB Yıllık Sektör Raporları:** https://www.tkbb.org.tr/faaliyetler/yayinlar/yillik-sektor-raporlari — PDF, 60-174 sayfa arası, yıllık. Lisans/kullanım koşulu sayfada açıkça belirtilmemiş (**belirsiz**).
- **Araştırma ve Raporlar:** https://tkbb.org.tr/sayfa/yayinlar/arastirma-ve-raporlar
- **Sektör Sunumları (ör. "Türk Finans Sisteminde Katılım Bankacılığı Mart 2024"):** https://www.tkbb.org.tr/faaliyetler/yayinlar/sektor-sunumlari
- **Strateji Güncelleme Raporu 2021-2025:** https://www.tkbb.org.tr/upload/TU%CC%88RKI%CC%87YE%20KATILIM%20BANKACILIG%CC%86I%20STRATEJI%CC%87%20GU%CC%88NCELLEME%20RAPORU%202021-2025.pdf

### BDDK

- **Aylık Bankacılık Sektörü Verileri:** https://www.bddk.org.tr/BultenDosyalari/Home/Index/Aylik-MetaVeri — BVTS (BDDK Veri Transfer Sistemi) üzerinden derlenen aylık veri, fonksiyon grubuna göre (katılım, kalkınma-yatırım, mevduat) ve mülkiyet grubuna göre (kamu/yerli özel/yabancı) kırılım var. **Banka bazında kâr payı oranı değil, sektörel bankacılık verisi** (aktif büyüklüğü, kredi hacmi vb. — kâr payı oranı bu bültende yer alıyor mu doğrulanamadı, muhtemelen hayır).
- **Ulusal Veri Yayım Takvimi (UVYT):** BDDK'nın yayın takvimi burada — hangi verinin ne zaman güncellendiğini gösteriyor.
- **Sonuç:** BDDK'da doğrudan "kâr payı oranı" tablosu bulunamadı; bu konuda otorite kaynak artık **TCMB** (aşağıda).

### TCMB — **En değerli yeni bulgu**

- **Faiz ve Kâr Payı İstatistikleri (ana sayfa):** https://www.tcmb.gov.tr/wps/wcm/connect/TR/TCMB+TR/Main+Menu/Istatistikler/Faiz+Istatistikleri
- **Haftalık Akım Faiz ve Kâr Payı İstatistikleri:** https://www.tcmb.gov.tr/wps/wcm/connect/TR/TCMB+TR/Main+Menu/Istatistikler/Faiz+Istatistikleri/Haftalik/
- **Basın Duyurusu (2025-26):** https://www.tcmb.gov.tr/wps/wcm/connect/TR/TCMB+TR/Main+Menu/Duyurular/Basin/2025/DUY2025-26
- **Başlangıç tarihi:** TCMB bu istatistiği **17 Nisan 2025'te ilk kez** yayımlamaya başladı — "Faiz İstatistikleri" yayını genişletilerek "Faiz ve Kâr Payı İstatistikleri" oldu.
- **Yayımlanan seriler:**
  1. Katılım Bankaları Kredi ve Katılma Hesabı Kâr Oranları (haftalık akım — katılma hesabı; haftalık akım + aylık stok — finansman/kredi)
  2. Finansman Şirketleri Aylık Stok Kredi Faiz Oranları
  3. Bankalar Aylık Stok Kredi Faiz Oranları
  4. Tasarruf ve Ticari Mevduat Faiz Oranları
  5. Fiilen Uygulanan En Yüksek İşletme Kredisi Faiz Oranı
- **Kapsam düzeyi:** Basın duyurusu metni **sektör toplamı düzeyinde** veri sunulduğunu ima ediyor (katılım bankaları toplamı), banka bazında (Kuveyt Türk/Albaraka/vb. ayrı ayrı) kırılım olduğuna dair açık ifade yok. **EVDS3 arayüzü (evds3.tcmb.gov.tr) JavaScript-render edilen bir SPA olduğu için bu oturumda otomatik erişimle doğrulanamadı** — seri kataloğunun banka kırılımı içerip içermediği manuel kontrol gerektiriyor.
- **Biçim:** EVDS (Elektronik Veri Dağıtım Sistemi) — genelde Excel/CSV export ve API sunar (genel EVDS bilgisi; bu spesifik seri için doğrulanmadı).
- **Lisans/kullanım koşulu:** Duyuruda açık bir lisans metni yok — **belirsiz**, EVDS genel kullanım şartları sayfasından kontrol edilmeli.
- **Önemi:** Sektör toplamı olsa bile bu, korpustaki `kar_payi_orani` çıkarımlarının **sağlaması (sanity check)** için resmî, düzenli, tarihli bir referans seri sağlıyor — banka bazında doldurma için değil, çıkarım kalitesi doğrulaması için kullanılabilir.

---

## 3. Üç bankanın ürün gerçeği (konut/taşıt finansmanı)

| Banka | Bulgu | Kanıt URL |
|---|---|---|
| **T.O.M. Katılım (tombank.com.tr)** | **Doğrulandı — konut/taşıt finansmanı ürünü YOK.** Sunulan finansman ürünleri: "HADİ Veresiye Kredisi" (şimdi al sonra öde) ve "HADİ Taksitli Alışveriş Kredisi". Bunlar günlük tüketim/alışveriş amaçlı, konut/taşıt değil. | https://www.tombank.com.tr/ (ana sayfa, menü: Ürünlerimiz / Kampanyalar / Ürün ve Hizmet Ücretleri) |
| **Hayat Finans (hayatfinans.com.tr)** | **Doğrulandı — konut/taşıt finansmanı ürünü YOK.** Ürün kataloğu: Avantajlı Hesap, Katılma Hesabı, "Bana Bunu Al" adlı ihtiyaç kredisi, kartlar, yatırım/birikim. Konut veya taşıt finansmanı kategorisi menüde bulunmuyor. | https://hayatfinans.com.tr/ (ana sayfa) |
| **Adil Katılım (adilkatilim.com.tr)** | **Farklı neden — banka çok yeni, ürün kataloğu henüz sığ olabilir.** BDDK kuruluş izni 27 Mayıs 2025 (bazı kaynaklarda kurul kararı 23 Mayıs 2024), **faaliyet izni 20 Eylül 2025**'te verildi — yani şu an (Ağustos 2026) yalnızca ~11 aydır faal, tamamen dijital bir katılım bankası. Web sitesi son derece minimal: yalnız "Hakkımızda" ve "Ürün ve Hizmet Ücretlendirmeleri" (PDF) sayfaları görünür durumda; ana sayfada hiçbir somut ürün listelenmiyor. | https://www.adilkatilim.com.tr ; kuruluş/faaliyet izni haberleri: https://fintechistanbul.org/2024/05/25/bddkdan-adil-katilim-bankasinin-kurulusuna-onay/ , https://tr.tradingview.com/news/reuters.com,2025:newsml_L5N3V902N:0/ |

**Değerlendirme:** TOM Katılım ve Hayat Finans için "konut finansmanı yok" iddiası **güçlendi** — her ikisi de bilinçli olarak alışveriş/ihtiyaç kredisi + katılma hesabı odaklı dijital banka modeli izliyor, konut/taşıt segmentine hiç girmemiş görünüyor. Adil Katılım için durum farklı yorumlanmalı: bu bir "ürün yok" kararı değil, **bankanın yaşı** (11 aylık) meselesi olabilir — ürün kataloğu zamanla genişleyebilir, korpusta "0 belge" bulgusu şu an için doğru ama kalıcılığı garantili değil. Bu üçünün hiçbiri "veresiye/taksitli alışveriş/ev tadilat" gibi bir gizli isimle konut/taşıt finansmanı sunmuyor — bulunan tek örtük ürün TOM'un "HADİ Veresiye/Taksitli Alışveriş" ürünleri, ama bunlar tüketim harcaması odaklı, gayrimenkul/araç değil.

---

## 4. Kampanya arşivi sayfaları — banka başına

| Banka | Arşiv/biten kampanya URL'i | Not |
|---|---|---|
| Kuveyt Türk | https://saglamkart.kuveytturk.com.tr/kampanyalar/biten-kampanyalar | Sağlam Kart (kredi kartı) alt sitesi — ana bankacılık kampanyaları değil, kart kampanyaları |
| Kuveyt Türk | https://milesandsmiles.kuveytturk.com.tr/kampanyalar/biten-kampanyalar | Miles&Smiles ortak markalı kart programı — aynı şekilde kart odaklı |
| Türkiye Finans | **https://www.turkiyefinans.com.tr/tr-tr/kampanyalar/sayfalar/biten-kampanyalar.aspx** | **En doğrudan eşleşme** — banka ana sitesinde, finansman kampanyaları dahil resmi "biten kampanyalar" sayfası |
| Ziraat Katılım | https://www.ziraatkatilim.com.tr/kampanyalar/diger-kampanyalar | Arşivleme `?IsArchived=true` URL parametresiyle yapılıyor; sayfa altında "Arşiv" başlığı altında geçmiş kampanyalar listeleniyor (tespit: WebFetch ile doğrulandı) |
| Vakıf Katılım | https://www.vakifkatilim.com.tr/en/for-me/campaigns/past-campaigns (İngilizce sürüm; Türkçe eşleniği bu oturumda 404 verdi, doğru TR slug bulunamadı) | Erişim denemesi başarısız oldu (muhtemelen slug farklı) — TR sitede "Geçmiş Kampanyalar" bağlantısı olduğu arama sonuçlarında görüldü ama tam URL doğrulanamadı |
| Türkiye Emlak Katılım | *bulunamadı* | Yalnız aktif kampanyalar sayfası (`/tr/bireysel/kampanyalar`) tespit edildi, ayrı arşiv sayfası görülmedi |
| Dünya Katılım | *bulunamadı* | Yalnız aktif kampanyalar (`dunyakatilim.com.tr/kampanyalar` ve alt sayfaları) bulundu, arşiv/biten kampanya sayfası tespit edilemedi |
| Albaraka, T.O.M., Hayat Finans, Adil Katılım | *bulunamadı* | Bu oturumda özel arşiv sayfası tespit edilemedi; üçüncü taraf "Kampanya Radar" (kampanyaradar.com) sitesi Albaraka için "Süresi Doldu" etiketli kampanyaları takip ediyor gibi görünüyor (üçüncü taraf, bkz. Bölüm 5) |

---

## 5. Üçüncü taraf kaynaklar — durum envanteri (öneri değil)

| Site | İçerik | Kullanım koşulu / durum |
|---|---|---|
| hangikredi.com | Kâr payı hesaplama, banka bazlı oran karşılaştırma, konut/taşıt finansmanı hesaplama sayfaları (`/kredi/konut-kredisi/<banka>`, `/yatirim-araclari/kar-payi-hesaplama`) | Kullanıcı Sözleşmesi var (https://www.hangikredi.com/kullanici-sozlesmesi) — kullanıcı işlemlerinin sorumluluğunun kullanıcıda olduğu, "veritabanı, marka ve korunan içeriğin izinsiz kullanımına karşı yasal işlem" ibaresi var. Veri yeniden kullanımı için **açık izin yok — belirsiz/olumsuz** |
| enuygunfinans.com | Banka bazlı kâr payı oranları ve hesaplama sayfaları | Sitenin kendisi "kâr payı oranları bankalardan alınan bilgilere dayanır, kampanya koşullarına göre değişebilir, ENUYGUN sorumluluk kabul etmez" diyor — veri kendi beyanına göre ikincil/rivayet niteliğinde, doğruluk garantisi yok |
| karpayihesapla.com | Banka bazlı güncel oran sayfaları (`/bankalar/<banka>`), "oranlar gösterge niteliğinde, günlük değişebilir" ibaresi | Kullanım koşulu bu oturumda ayrıca incelenmedi — **belirsiz** |
| katilimekonomisi.com | "Kar Payı Hesaplama 2026" karşılaştırma aracı, tüm katılım bankaları | Kullanım koşulu incelenmedi — **belirsiz** |
| kampanyaradar.com | Banka kampanyalarını (aktif + "Süresi Doldu" etiketli) topluyor, ör. Albaraka Türk sayfası | Kullanım koşulu incelenmedi — **belirsiz** |

**Genel değerlendirme:** Üçüncü taraf siteler oran verisini genelde resmi sayfadan daha "parse edilebilir" biçimde (temiz tablo, banka başına tek sayfa) sunuyor, ama hepsi (a) veriyi bankalardan **türetilmiş/ikincil** olarak sunuyor, (b) doğruluk garantisi vermiyor, (c) yeniden dağıtım/scrape izni konusunda açık bir kullanım koşulu bulunamadı. Şartname kapsamındaki "kaynak" tanımına girip girmediği hukuki/politika kararı — bu rapor yalnız durumu bildiriyor, kullanılmasını önermiyor.

---

## 6. Öncelik sırası — `kar_payi_orani` kapsamını artırma

1. **Albaraka Türk kâr paylaşım oranları PDF'i** (https://www.albaraka.com.tr/documents/bireysel/hesaplar/PDF/kar-paylasim-oranlari.pdf) — sabit, tarih sürümlü dosya adı kalıbına sahip (`kar-paylasim-oranlari-DD-MM-YY`), doğrudan tablo formatında. Albaraka şu an muhtemelen düşük kapsamlı bankalardan biri; bu tek PDF, banka başına düzenli aralıklarla (haftalık/aylık) yeni sürüm yayımlanan bir kaynak olduğu için **tekrarlanabilir hasat + versiyon takibi** ile onlarca tarihli veri noktası üretebilir. **Tahmini katkı: yüksek** — düzenli arşivlenirse banka başına 50-100+ tarihli oran kaydı.
2. **Türkiye Finans "Kar Payı Oranları" + "Ticari Kâr Paylaşım Oranları" HTML sayfaları** (turkiyefinans.com.tr) — zaten yapılandırılmış tablo, hem bireysel hem ticari ayrı sayfa, düzenli güncellendiği görülüyor. **Tahmini katkı: orta-yüksek** — periyodik snapshot alınırsa (haftalık) zaman serisi oluşturulabilir; şartname belgesi biçiminde değil ama `kar_payi_orani` alanını doğrudan besler.
3. **T.O.M. Katılım kâr paylaşım oranı PDF'i** (tombank.com.tr/assets/images/doc/kpo.pdf) — sabit URL, doğrudan vade × oran tablosu; T.O.M. şu an konut finansmanı belgesi olmayan bankalardan biri olduğu için bu PDF konut kapsamını değiştirmez ama **kâr payı oranı kapsamını** doğrudan artırır. **Tahmini katkı: orta** (tek banka, ama düşük maliyetli/yüksek güvenilirlikli tek kaynak).
4. (Ek, düşük öncelik ama ucuz) **TKBB Veri Peteği sayfası** (tkbb.org.tr/veripetegi-detay/40) — eğer banka bazında kırılım içeriyorsa (bu oturumda doğrulanamadı, JS render sorunu), tek sayfadan 11 bankanın oranına ulaşmak mümkün olabilir; **önce manuel doğrulama (tarayıcıyla ziyaret) şart**, sonra otomasyon değerlendirilmeli.
5. (Doğrulama katmanı, kapsam artırmaz ama kaliteyi artırır) **TCMB Faiz ve Kâr Payı İstatistikleri** (EVDS, 17 Nisan 2025'ten beri) — sektör toplamı düzeyinde resmi referans seri; korpustan çıkarılan `kar_payi_orani` değerlerinin sektör ortalamasıyla makul aralıkta olup olmadığını haftalık/aylık kontrol etmek için kullanılabilir.

---

## Kaynak notu

Bu rapordaki tüm URL'ler 2026-08-20 tarihinde web araması/okuma yoluyla toplanmıştır; sayfa içerikleri değişken olabilir (bankalar oranları haftalık günceller). Otomasyon kurulmadan önce her URL'in canlı durumu yeniden doğrulanmalıdır.
