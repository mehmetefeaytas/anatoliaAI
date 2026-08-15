# Sunum ve Demo Planı — 5 dk video · 1 dk demo · 4 dk sunum

**Hazırlık tarihi:** 13 Ağustos 2026
**Son güncelleme:** 15 Ağustos 2026 — sayılar 15 Ağustos ölçümüne taşındı, iki
ölü iddia çıkarıldı, iki slayt eklendi (§Ç "Ölü iddiaların mezarlığı" bunu kayda
geçirir).
**Kapsam:** G4.2 (demo videosu) ve G4.3 (sunum materyali)

**Kural:** bu belgedeki her sayı ölçülmüştür ve yanındaki komutla yeniden
üretilir. Slayta girmeden önce sayıyı **o gün** yeniden koşun; bayat sayı
sunumda savunulamaz. Ölçülmemiş hiçbir sayı bu belgeye yazılmaz — yerine
`🔬 ölçülecek` işareti konur (topluca §E'de listelidir).

**Sunum günü tek komutluk tazelik denetimi:**

```bash
cd app
python -m scripts.kanit_tazeligi     # yayımlanan sayı ≠ kanıt ise çıkış kodu ≠ 0
```

Bu kapı sayıların **tamamını** kapsamaz (§C slayt 5); kapsadıklarını §D
tablosundaki "üreten komut" sütunu gösterir.

---

## Şartnamedeki süre çelişkisi

Şartname s.14 "en fazla 5 dakika", s.19 "1 dakika" diyor. Çelişki
`syntheses/teslim-ve-degerlendirme-rehberi.md`'de kayıtlı. **İkisi de
hazırlanır**; kısa olan uzunun kesitidir, ayrı çekim yapılmaz.

---

## Anlatının omurgası

Bu projenin rakiplerden ayrıldığı yer daha yüksek bir F1 değil — **ölçümün
dürüstlüğü**. Sunum bunun üzerine kurulur:

> "Tek bir parlak yüzde vermiyoruz, çünkü bir alanı kaçırmak ile uydurmak aynı
> hata değildir."

Rakip tek sayı gösterecek. Biz iki sayı, güven aralığı ve halüsinasyon oranı
göstereceğiz. Jüri karşısında güçlü olan bu.

**Ölçek cümlesi (tek biçim — başka biçimde telaffuz edilmez):**

> "1.782 belge · 6 tarama tarihi · 10/10 banka — ve ölçülmüş altın seti olan
> tek takım."

Son yarım cümlenin savunulabilir tam hâli, jüri "ne demek ölçülmüş?" derse:
*altın setini yalnız teslim etmekle kalmayıp üzerinde alan bazlı P/R/F1'i,
%95 güven aralığını ve ayrı bir halüsinasyon oranını yayımlayan tek takım.*
Sahada altın set teslim eden başka takım **var**; F1'e kadar götüren yok.
Bu ayrımı biz söylemezsek slaytta "tek" kelimesi savunmasız kalır.

---

## A) 5 dakikalık demo videosu — çekim listesi

Toplam 5:00. Süreler tavan; taşarsa §5 kısaltılır, §3 asla kısaltılmaz.

| # | Süre | Ekranda | Anlatım (özet) |
|---|---|---|---|
| 1 | 0:00–0:30 | Kapak + problem: üç banka sayfası yan yana, farklı ifadeler ("ilk 6 ay masrafsız", "%1,99–%2,49", "120 aya kadar") | Katılım bankacılığında bilgi doğal dilde ve kıyaslanamaz biçimde duruyor |
| 2 | 0:30–1:15 | Mimari şeması: toplama → temizleme → **kural (birincil)** → LLM (yalnız boşluk) → normalizasyon → DB → dashboard/chatbot | İki katman. LLM kritik yolda değil; kapalıyken sistem çalışır |
| 3 | 1:15–2:30 | **Dashboard**: kıyas tablosu, alan başına güven skoru, kaynak vurgulama; "doğrudan kıyaslanamaz" rozeti | Her değerin yanında nereden geldiği var. Koşullar farklıysa sıralama uydurmuyoruz |
| 4 | 2:30–3:30 | **Chatbot**: (a) kıyas sorusu → yapısal sorgu yolu, (b) koşul sorusu → RAG + kaynak, (c) **alan dışı soru → reddetme** | Üçüncüsü kasten: sistem bilmediğinde bilmediğini söylüyor |
| 5 | 3:30–4:15 | **Çelişki tespiti**: kampanya "dosya masrafsız" diyor, aynı bankanın ücret tarifesinde tahsis ücreti %0,5 (§A-5 notu) | Bu bir kapsam testi: ücretin varlığı değil, kampanyanın hangi ücreti kapsadığını söylememesi |
| 6 | 4:15–4:45 | Terminalde önce `python -m eval.run_eval`, arkasından `python -m scripts.kanit_tazeligi` koşuyor | Sayılar slayttan değil komuttan geliyor — ve ikinci komut slayttaki sayının komuttan sapmadığını denetliyor |
| 7 | 4:45–5:00 | `docker-compose up` + ağ kapalı rozeti; Apache-2.0 · üstüne **kapsam sınırı alt yazısı** | On-prem, internetsiz, ücretli servis yok — kanıt paketinin neyi kapsamadığını da biz yazıyoruz |

**§A-5 notu — çelişki örneği ölçülmüştür ve kaynağı bellidir.**
15 Ağustos'ta `python -m scripts.crosscheck_fees` ile yeniden koşuldu:
**7 iddia × ürün satırı**, bağımsız kaynak **33 ilan edilmiş tahsis ücreti
kaydı / 5 banka**; sonuç **1 `kapsamsiz_iddia` · 6 `kosullu_muafiyet` ·
0 `tutarli`**. Kartta gösterilecek vaka `kapsamsiz_iddia` olanıdır: Vakıf
Katılım taşıt finansmanı kampanyası "dosya masrafsız" diyor, aynı bankanın
finansman hesaplama sayfasındaki tarife "tahsis ücreti finansman tutarının
%0,5'idir" diyor. Çelişki **belgeler arasıdır**, belge içi değil — rapor
(`data/gold/fee_crosscheck.md`) bunu açıkça yazıyor ve kartın alt yazısı da
yazmalı.

⚠️ **Eski çelişki örneği kullanılamaz.** 15 Ağustos'ta oransal tahsis
ücretinde türetme kaldırıldı; `test_p4_kapsam_etkisi` çit belgesinin
`masrafsiz_ama_ucret` çelişkisi **uydurma bir 50 TL'ye dayanıyormuş** ve
artık üretilmiyor
(`oturum-2026-08-15-round1-onarimi.md` §6). Kaydı iyi haber olarak veriyoruz:
çelişki tespiti sahte bir dayanaktan kurtuldu. Çekimden önce vakanın hâlâ
üretildiğini `crosscheck_fees` ile **o gün** doğrulayın.

**§A-7 notu — on-prem kapsam sınırı slaytta yazılı olmalı.** Kanıt paketi
gerçek ve ölçülmüş (`--network none` içinde 14/14 adım, negatif kontrol 4/4
engellendi, pozitif kontrolü 4/4 ulaştı, üç imaj `@sha256:` pinli), ama üç
sınırı var ve üçünü de **biz** söylüyoruz: (a) koşum 31 Temmuz'dan ve depo o
gün kirliydi, (b) kanıt yalnız API konteynerini kapsıyor — tam yığın
(Postgres + web + vLLM/Ollama) ağsız denenmedi, (c) imaj **derlemesi**
internet gerektiriyor; "internetsiz çalışır" iddiası *önceden derlenmiş
imajlarla* doğrudur. Kaynak: `docs/OFFLINE-KANIT.md` §0-b, §10 ·
`docs/SARTNAME-UYUM.md` kalem 16.

**Çekim kuralları**

- Demo **önceden doldurulmuş DB'den** okur (karar: `demo-onceden-doldurulmus-db`).
  4 dakikada yerel 8B LLM + canlı scraping donma riski taşır.
- Tek bir örnekte "canlı çıkarım" butonu gösterilir — çalıştığını ispatlar.
- Ekran kaydı 1080p, imleç vurgulu, ses ayrı kayıttan.
- Sayıların göründüğü her karede o sayı **o gün** koşulmuş olmalı.
- Çekim öncesi `python -m scripts.kanit_tazeligi` **yeşil** olmalı; kırmızıysa
  önce belge/ölçüm ayrışması kapatılır, sonra kamera açılır.

---

## B) 1 dakikalık kısa demo — kesit

Uzun videonun §3 + §4c + §5'inden kurulur. Yeni çekim yok.

| Süre | İçerik |
|---|---|
| 0:00–0:20 | Dashboard kıyas tablosu + kaynak vurgulama |
| 0:20–0:40 | Chatbot: alan dışı soruya **cevap vermeme** |
| 0:40–1:00 | Çelişki tespiti kartı |

Kısa sürüme mimari ve eval koşusu **girmez**; onlar sunumun işi.

---

## C) 4 dakikalık sunum — slayt iskeleti

PDF + PPTX olarak teslim edilir (s.14). 10 slayt · toplam 4:00.

| # | Slayt | Süre | Çekirdek mesaj |
|---|---|---|---|
| 1 | Kapak — takım, senaryo | 0:10 | — |
| 2 | Problem | 0:20 | Aynı bilgi, farklı ifade; manuel kıyas pratikte imkânsız |
| 3 | Mimari (tek şema) | 0:30 | Kural birincil, LLM tamamlayıcı, hepsi on-prem |
| 4 | **Ölçüm dürüstlüğü** ← ana farklılaştırıcı | 0:50 | Dört hata kovası (kaçırma / yanlış çıkarım / halüsinasyon / atlanan); iki mikro-F1 ve farkının açıklaması; belge düzeyi bootstrap |
| 5 | **Sayılarımızı CI'ımız denetliyor** ← YENİ | 0:30 | Ölçüm dürüstlüğü bir iddia değil, bizde bir **kapı** |
| 6 | **Ölçüp geri adım attığımız yer** | 0:30 | Ablasyon hibridi yanlışladı; sonucu düzeltmedik |
| 7 | **Biz söylüyoruz — açık kalemler** ← YENİ | 0:25 | Eksiklerimizi jüri sormadan biz sayıyoruz |
| 8 | Yenilikçilik: çelişki tespiti + güven/kaynak + config-driven banka | 0:20 | Üçü de ölçülebilir, üçü de demoda görünüyor |
| 9 | On-prem kanıtı **ve kapsam sınırı** | 0:15 | `--network none` içinde koşan kanıt paketi; Apache-2.0 zinciri köke kadar; kanıtın neyi kapsamadığı |
| 10 | Kapanış + demo geçişi | 0:10 | — |

### Slayt 5 — "Sayılarımızı CI'ımız denetliyor" (yeni)

Tek cümlelik anlatı:

> **"Ölçüm dürüstlüğü bir iddia değil, bizde bir kapıdır."**

`scripts/kanit_tazeligi.py` yayımlanan **her sayıyı** onu üreten kanıtla
karşılaştıran bir CI kapısıdır. Sahada emsali yok: rakiplerde ölçüm var, ölçümü
**denetleyen** bir kapı yok.

Kapı **iki ayrı denetim** yapar ve ikisi karıştırılmaz:

1. **Değer denetimi** — belgedeki sayı = kanıttan okunan sayı.
2. **Tazelik denetimi** — kanıtın kendisi bugünkü girdilerden mi üretilmiş?
   `env.json`'daki `gold_sha256` bugünkü gold'un sha'sı değilse o rapor
   **kanıt değildir**, sayı tesadüfen tutsa bile.

İkincisi olmadan birincisi kendini kandırır: bayat bir rapordan okunan bayat bir
sayı, bayat bir README ile mükemmel uyum gösterir.

**Kapının bulduğu gerçek sapmalar** (slaytta 2 satır yeter — 12→15 Ağustos
arasında üç kez sapma oldu, düzeltme değil mekanizma gerekti):

| Belge ne diyordu | Kanıt ne diyor | Ne demek |
|---|---|---|
| 2.631 test | pytest'in kendi sayımı (bugün **2.947** toplanan) | rozet aylarca gerçekten koşulan sayının altındaydı |
| 1.774 belge | demo.db **1.782** | korpus büyüdü, vitrin büyümedi |
| bootstrap 2.000 örnek | `eval/stats.py: DEFAULT_RESAMPLES = 1000` | **2.000 hiç koşmamış** — yayımlanan güven aralığı, ilan edilen yöntemle üretilmemişti |
| alan F1 0,500 | `per_field.csv` 0,800 | düzeltme yayımlanmamıştı |

Üçüncü satır slaydın vurucu noktasıdır: bir güven aralığının yeniden
üretilebilmesi için örnekleme sayısı ve tohumun **doğru** raporlanması gerekir;
yanlış raporlanan bir GA kanıt değildir. Kapıyı yazma sebebimiz tam olarak
budur.

**Kapının kasıtlı sınırı da söylenir:** ağır ölçüm koşturmaz. `pytest
--collect-only` ve SQLite sayımı ucuzdur; ölçüm hattı ve kalibrasyon değildir —
onlar için artefakt okunur. Yani kapı "sayı doğru mu"yu değil, **"sayı
elimizdeki kanıtla tutarlı mı"yı** ölçer. Bugün denetlediği iddia sayısı
**10**'dur (`python -m scripts.kanit_tazeligi --liste`); geri kalan sayılar
§D tablosundaki komutla elle koşulur. Kapıyı kapsadığından geniş göstermek,
kapının kendisini yalanlamak olurdu.

Çıkış kodu: `0` = sapma yok · `1` = sapma var · `2` = kanıt eksik/bayat.

### Slayt 7 — "Biz söylüyoruz" (yeni)

Bir vitrin tablosunun en kolay yalanı, eksiği yazmamaktır. Şartname uyum
matrisimizde (`docs/SARTNAME-UYUM.md`) bugün **✅ 7 · 🟠 6 · ❌ 6** var ve
matrisi biz tutuyoruz. Slaytta üç kalem açıkça sayılır:

| Açık | Bugünkü durum | Neden hâlâ açık |
|---|---|---|
| **Veri seti indirme bağlantısı** (§9, s.18) | ❌ — README'de yer tutucu | Paket **tek komutla** üretiliyor ve provenance kapısından geçiyor (kaynağı doğrulanamayan tek kayıtta çıkış kodu 1), ama yüklenmedi: gold seti genişletiliyor, yarım gold yayımlamak indirilen kopyayı yanlış bırakır |
| **İnsan hakemliği** (%30'luk rubrik kalemi) | 🟠 — round1'in 53 vakalık kör hakemliğini **alt ajanlar** yaptı | Referans "gold" değil `silver-extended`'dir; makine üretimi referansa karşı ölçülen P/R/F1 "model insanla ne kadar örtüşüyor"u değil "bir model başka bir modelle ne kadar örtüşüyor"u ölçer ve halüsinasyon oranı çapasız kalır. Kapatılması gereken en büyük açığımız budur ve rubriğin en ağır kalemidir |
| **On-prem kanıt tazeliği** | 🟠 — koşum 31 Temmuz'dan, kapsam yalnız API konteyneri | Kanıt gerçek ve ölçülmüş; sınırı §A-7 notundaki üç maddeyle biz yazıyoruz |

Slaydın kapanış cümlesi:

> "Bu üç kalemi jüri bulmadan biz sayıyoruz. Çünkü saklanan tek bir kalem
> yakalandığında matrisin geri kalanı da değersizleşir."

Bu, savunma değil **konumlandırmadır**: rakiplerin on-prem ve ölçüm
kalemlerinde kredi kaybettiği yer tam olarak kapsamı yazmamış olmalarıdır.

---

## D) Slayt 4'ün tablosu — 15 Ağustos ölçümü

Ölçüm kolu: **`kural`** (resmî varsayılan, LLM kapalı) · temiz çalışma ağacı ·
strict eşleştirici · belge düzeyi bootstrap **1000** örnek · tohum **42**.
Sunum günü yeniden koşulacak.

| Ne | Değer | Üreten komut |
|---|---|---|
| Yapılandırılmış alan mikro-F1 (11 alan) | **0,671** | `python -m eval.run_eval --gold data/gold/gold.v2.json` |
| 12-alan mikro-F1 | **0,464** [%95 GA 0,398–0,522] | *(aynı komut)* |
| makro-F1 | **0,601** | *(aynı komut)* |
| Halüsinasyon oranı | **0,047** (21/444) · yapısal kesitte 0,035 | *(aynı komut)* |
| RAG terim kapsama R@5 | **0,867** · banka hedefleme R@5 0,800 · kaynak gösterme 1,000 | `python -m eval.rag_eval --db data/demo.db` |
| Reddetme kararı doğruluğu | **30/30** | *(aynı komut)* |
| Güvenlik seti | **29/30** · aşırı red **0/6** | `python -m src.chatbot.run_safety_eval --db data/demo.db` |
| Anotatör uyumu — round0 | Fleiss κ **0,302** · Krippendorff α 0,620 / 0,787 — hakemlik **SONRASI** | `python -m scripts.report_iaa data/gold/review/round0_kalibrasyon_{A,B,C,D}.csv --tur round0-kalibrasyon-v1` |
| Anotatör uyumu — round1 | Cohen κ **0,274** (141 ortak karar) — hakemlik **ÖNCESİ** | `python -m scripts.report_iaa data/gold/review/round1_{A,B}.csv --tur round1` |
| Güven kalibrasyonu | ECE **0,188** · MCE 0,379 · Brier 0,201 (gold.round1, 12 alan, n=153) | `python -m eval.calibration --gold data/gold/gold.round1.json` |
| Test | **2.947** toplanan · **2.894** geçti · **53** atlandı (Postgres — CI'da koşar) | `python -m scripts.test_ozeti` |
| Korpus | **1.782** belge · **10** banka | `python -m scripts.check_demo_db` · `config/banks.yaml` |
| Tarama tarihi sayısı | **6** (30 Tem · 3/4/8/11/12 Ağu; ayrıca `scraped_at` boş 2 kayıt) | `sqlite3 data/demo.db "select substr(scraped_at,1,10) d, count(*) from campaigns group by d order by d"` |
| Gold setleri | `gold.v2` **48** (40'ı kasten zor) · `gold.round1` **134** (38'i hakemlikten geçti) | `data/gold/gold.v2.json` · `data/gold/gold.round1.json` |
| Bağımlılık envanteri | **96 paket** — CycloneDX SBOM + **CI lisans kapısı** | `make sbom lisanslar lisans-kapisi` |
| Kanıt-tazeliği kapısı | **var** — 10 iddia denetleniyor | `python -m scripts.kanit_tazeligi` |

### İki κ neden yan yana konmaz — slaytta yazılı olacak cümle

**round0'ın 0,302'si hakemlik SONRASI, round1'in 0,274'ü hakemlik ÖNCESİ bir
durumdur.** Round0'ın yedekleri 0,051 → 0,268 → 0,302 ilerlemesini gösteriyor;
round1'in hakemlik sonrası tutarlılığı 0,844'tür ama bu **bağımsız uyum
değildir** ve manşet olarak kullanılmaz. İki sayıyı yan yana koyup "uyum
düzeliyor" ya da "uyum bozuldu" demek, ölçtüğümüz şeyi ölçmediğimizi söylemek
olurdu. Asimetri slaytta bir dipnot değil, **satırın kendisidir**.

### ECE'nin hangi sette ölçüldüğü

**0,188** `gold.round1` üzerinde, 12 alanda, 153 kararla ölçüldü. Aynı modül
`gold.v2` üzerinde (n=82) **0,306** veriyor. İkisi farklı setlerdir, birbirinin
düzelmesi değildir; manşete konacaksa hangi sette ölçüldüğü **aynı satırda**
yazılır. Ortak bulgu ikisinde de aynı: **en yüksek güven bandı en kötü kalibre
banddır** (round1'de 0,90+ bandı 16 kararla ortalama 0,947 güven ilan edip
0,688 doğruluk veriyor). Kök neden bulundu ve yazıldı — `extract.py`'de 11
çağrı yerinde `trigger_distance=0` sabit yazılı, `confidence.score()` bununla
0,95 üretiyor; skor o alanlarda ölçüm değil sabit. **Düzeltilmedi**, çünkü
teslime yakın üretim davranışı değiştirmek ayrı bir karardır; bulgu olarak
raporlanıyor.

---

## Ç) Ölü iddiaların mezarlığı — 15 Ağustos'ta ÇIKARILAN iki cümle

Bu bölüm silinmez. Bir iddianın neden çıkarıldığını yazmak, o iddiayı bir daha
yanlışlıkla slayta koymamanın tek güvenilir yoludur.

| Çıkarılan iddia | Ne zaman öldü | Neden |
|---|---|---|
| **"Adil Katılım'ı toplayan tek takım"** | 14 Ağustos | Sahaya yeni bir depo doğdu ve **Adil Katılım dâhil 10/10 bankayı** topladı (kendi `scrapers/adil_katilim.py` dosyası, 8 kayıt). "Tek takım" artık yanlış bir olgu beyanıdır |
| **"6,8× ölçek farkı"** | 14 Ağustos | Aynı depo **771 kayıtla** geldi. 1.782 / 771 → fark artık **2,3×**. 6,8 rakamı en yakın rakip 263 kayıttayken doğruydu; bugün değil |

Yerine geçen tek cümle §"Anlatının omurgası" bölümündedir.

**Kural:** ölçek üstünlüğü artık **tek başına** bir slayt taşımaz. Ölçek,
"ölçülmüş altın set" ile birlikte söylenir; yalnız başına söylenirse 2,3×'lik
bir farkı 6,8× gibi sunma refleksine kapı açar ve bu, dürüstlük anlatısını
sunumun kendi içinde çürütür.

---

## D2) Jüri sorularına hazır cevaplar

**"F1'iniz rakibinkinden düşük."**
Farklı şey ölçüyoruz. Onlar 5–8 alanda, biz 12 alanda; gold setimizin 40/48'i
**kasten** zor vaka; halüsinasyonu ayrı paydayla sayıyoruz. Yapılandırılmış
alan kesitinde **0,671**, tam kesitte **0,464 [0,398–0,522]** — ikisini de
yayımlıyoruz ve farkını README'de açıklıyoruz. Tek sayıya indirmek bu farkı
gizlemek olurdu.

**"κ = 0,302 düşük değil mi?"**
Düşük ve bunu biz ilan ettik. Eşik anotasyon **başlamadan** açıklanmıştı (0,67)
ve ilan edilen sonuç uygulandı: zorunlu hakemlik, kılavuz v1→v2 revizyonu, 123
uyuşmazlığın tek tek listelenmesi. Sayıya bakıp eşik değiştirmedik. Round1'de
aynı politika ikinci kez işledi: κ 0,274 → zorunlu hakemlik koşuldu, 41
uyuşmazlık karara bağlandı, uyuşmazlık 56→14 ve çelişki 120→11'e indi.
**Ama round1'in 0,274'ü hakemlik öncesidir; round0'ın 0,302'si sonrası.**
Bu asimetriyi biz söylüyoruz.

**"LLM'i neden daha çok kullanmıyorsunuz?"**
Kullanmayı denedik ve ölçtük: hibrit kol kural kolundan **kötü** çıktı
(0,575 < 0,612, McNemar p = 0,0117), üstelik halüsinasyonu %60 daha yüksekti
(0,163 vs 0,102). Ölçümü düzeltmek yerine kararı değiştirdik.
🔬 *Bu ablasyon 5 Ağustos ölçümüdür; 15 Ağustos kural düzeltmelerinden sonra
yeniden koşulmadı — sunum öncesi `python -m eval.ablation` ile tazelenecek.*

**"Veri seti nerede?"**
Paket tek komutla üretiliyor ve provenance kapısından geçiyor; kaynağı
doğrulanamayan **tek** kayıt varsa komut çıkış kodu 1 verir ve paket
"yayımlanabilir" sayılmaz. Gold seti şu an genişletildiği için yükleme tur
bitiminde yapılacak — yarım gold yayımlamak, indirilen kopyayı yanlış bırakır.
**Bu kalem şartname zorunluluğudur ve bugün karşılanmıyor; slayt 7'de zaten
biz sayıyoruz.**

**"Halüsinasyon oranınız neden rakiplerinkinden yüksek görünüyor?"**
Çünkü aynı şeyi ölçmüyoruz. Sahada yaygın tanım "çıkarılan değer ham metinde
geçiyor mu" testidir ve **gold gerektirmez**. Bizimki "gold'da *kaynakta yok*
diye işaretlenmiş bir alana model değer uydurdu mu" testidir; payda 444
`absent` kararıdır. Bizim tanımımız kat kat serttir. Bu ayrım söylenmezse iki
sayı yan yana okunur ve haksız yere kaybederiz.

---

## D3) Yüksek rakamlara hazır cevap — metodolojik soru olarak

> ⛔ **BU BÖLÜM İÇ İSTİHBARATA DAYANIR.** Kaynağı `docs/rapor/rakip-analizi.md`
> (yayın kademesi 3 — **hiçbir zaman push edilmez, damıtılmış hâlde bile
> yayımlanmaz**). Bu dosya git'te izleniyor; bu yüzden burada **hiçbir rakip
> adı, deposu ya da kişi adı geçmez** ve slaytta da geçmeyecektir.
>
> **Sunumda rakip ADI VERİLMEZ.** Aşağıdakiler yalnızca *"yüksek bir F1
> gördüğünüzde şunu sorun"* biçiminde, kimseyi işaret etmeden kurulan
> **metodolojik sorulardır**. Bir rakibi adıyla eleştirmek jüri değeri sıfır,
> etik riski yüksek bir hamledir; ayrıca kendi dürüstlük anlatımızı ilk
> cümlede çürütür.
>
> Kimlik eşlemesi ve ham bulgular yalnızca kademe-3 dosyasındadır. Aşağıdaki
> kesit **15 Ağustos** iç istihbaratıdır ve `rakip-analizi.md` §A'ya (13
> Ağustos kesiti) **henüz işlenmemiştir** — sunumdan önce oraya işlenmeli.

Sahada bugün üç yüksek/parlak rakam dolaşıyor. Her birine karşı tek bir
metodolojik soru yeter:

**1) "Altın set teslim edildi" ≠ "model ölçüldü."**
> Sorulacak soru: *"Altın setiniz var — üzerinde **F1** hesapladınız mı, yoksa
> yalnız 'doğruluk' mu veriyorsunuz?"*

Sahadaki bir takım altın setini **15 Ağustos'ta teslim etti** (60 örnek,
8 alan) ama **F1 hesaplamadı**; sonuç belgesi yalnız "doğruluk" veriyor.
Ayrıca: şans düzeltmeli uyum yok (**%80,8 ham uyum** — ham uyum κ değildir,
rastgele örtüşmeyi düşmez), kendi ilan ettiği hedefi raporunda **❌** ile
ıskaladı (0,857 < 0,90) ve iki metriği 13→15 Ağustos arasında **kötüleşti**.
*Bizim karşılığımız:* 12 alan, iki mikro-F1, %95 GA, ayrı halüsinasyon paydası,
ve iki turda ölçülmüş şans düzeltmeli κ.

**2) "Bir sayı" ≠ "yaşayan bir ölçüm."**
> Sorulacak soru: *"Bu yüzde ne zaman koşuldu, kaç alanın desteği kaç, ve güven
> aralığı nerede?"*

Sahadaki bir başka takımın **%98,28**'i **12 Ağustos'tan beri tazelenmedi** —
depo üç gündür donmuş. Destek sayıları **1–23 arasında değişen 5 alan**
üzerinden makro ortalama; tek kayıtlık bir alandan gelen %100 ortalamayı yukarı
çeker. **Güven aralığı yok.**
*Bizim karşılığımız:* 48 belgede 12 alan, [0,398–0,522] aralığıyla, belge
düzeyi küme bootstrap ile (alan düzeyinde örneklemek GA'yı yapay olarak
daraltır — bu bir tercih değil istatistiksel bir hatadır), tohum 42 raporlu.

**3) "Büyük veri" ≠ "ölçülmüş veri."**
> Sorulacak soru: *"Etiketleriniz kim tarafından üretildi — ve ölçtüğünüz
> sistemle aynı yöntem mi?"*

Sahadaki üçüncü takımın **2.964 span'inin tamamı makine etiketidir** ve
doğrulama klasörü depoda yok. Kural tabanlı bir çıkarımı kural tabanlı bir
etiketle ölçmek **döngüseldir**: sistem kendi tanımıyla sınanır. Ayrıca model,
dashboard ve chatbot yok — yani şartnamenin fonksiyonellik kalemi karşılıksız.
*Bizim karşılığımız:* bizde de referansın bir kısmı makine üretimidir ve **bunu
slayt 7'de biz söylüyoruz** (`silver-extended`, insan hakemliği açık kalem).
Fark, kendi zayıflığımızı kendimizin ilan etmesidir.

**Sahne disiplini.** Bu üç soru **ancak jüri yüksek bir rakam üzerinden
sorarsa** kurulur; kendiliğinden açılmaz. Sunumun kendi zamanında rakip
karşılaştırması yapmayız — dört dakikanın hiçbir saniyesi başka bir takıma
harcanmaz.

---

## E) 🔬 Ölçülmemiş / tazelenmemiş — slayta girmeden koşulacak

Bu belgede bilerek **yazılmayan** ya da bayat olduğu için işaretlenen sayılar:

| Kalem | Durum | Ne yapılacak |
|---|---|---|
| Ablasyon (0,575 vs 0,612 · p 0,0117 · halüsinasyon 0,163 vs 0,102) | 5 Ağustos ölçümü; 15 Ağustos kural düzeltmelerinden **sonra koşulmadı** | `python -m eval.ablation` — sunum öncesi |
| `OFFLINE-KANIT.md` sayıları | 31 Temmuz koşumu, o gün ağaç kirliydi | `bash scripts/offline_proof.sh` — **temiz** ağaçta |
| Tam yığın ağsız koşum (Postgres + web + API) | **hiç ölçülmedi** | `docker compose up` ağsız; kapatılamazsa sınır slayt 9'da yazılı kalır |
| `hafta-06` etiketi | son etiket `hafta-05` (8 Ağustos) | teslimden önce atılıp push'lanacak |
| GitHub depo görünürlüğü + `BilisimVadisi2026` / Türkiye Açık Kaynak Platformu topic'leri | yerel klondan **doğrulanamaz** | tarayıcıdan teyit |
| Rakip kesiti (§D3) | 15 Ağustos iç istihbaratı, `rakip-analizi.md` §A'ya işlenmemiş | teslim haftasında bir kez daha koşulacak (§A8 talimatı) |
| `tahsis_ucreti` alan F1 | **tanımsız** — gold'da 0 pozitif örnek (47 kayıtta `absent`) | slaytta sayı verilmez; "ölçülemiyor" denir, "çalışmıyor" denmez |
| `kar_payi_orani` alan F1 | 0,800 ama yalnız **3 karar** destekli — yorumlanamaz | manşete konmaz; korpusta alan 70/1.782 belgede (%3,9) var, bu bir veri gerçeği |

---

## Yapılacaklar (bu belge planı, çekimi değil)

- [ ] Ekran kaydı — dashboard, chatbot, çelişki kartı (docs-ekran/ PDF'i taslak olarak var)
- [ ] Seslendirme metni — yukarıdaki anlatım sütunundan tam cümlelere açılacak
- [ ] Slayt tasarımı — PDF + PPTX (şartname §6.4 **ikisini birden** istiyor)
- [ ] Slayt 5 ve 7'nin görselleri — kapı çıktısının ekran görüntüsü + uyum matrisinin ✅/🟠/❌ sayımı
- [ ] Sunum günü: bütün sayıları yeniden koş, §D tablosunu ve slayt 6'yı güncelle
- [ ] Sunum günü: `python -m scripts.kanit_tazeligi` yeşil olmadan slayt dondurulmaz
- [ ] `OFFLINE-KANIT.md` yeniden koşulsun (mevcut kanıt 31 Temmuz'dan)
- [ ] §E tablosundaki 🔬 kalemler tek tek kapatılsın ya da slaytta "ölçülmedi" olarak yazılsın
