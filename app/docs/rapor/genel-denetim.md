---
title: "Uçtan uca denetim — altı bağımsız hakem, puanlar ve kapatılanlar"
tags: [denetim, olcum, sartname, teslim]
date: 2026-08-08
status: stable
---

# Uçtan uca denetim (2026-08-08)

Teslime **18 gün**. Proje altı bağımsız hakeme verildi; hiçbiri diğerinin
raporunu görmedi. Örtüşen bulgular bu yüzden **bağımsız doğrulama** sayılır.

Hakemler: ölçüm/istatistik · şartname/uyum · kod/mimari · alan/terminoloji ·
güvenlik-dayanıklılık-on-prem · jüri simülasyonu. Ayrıca iki alt denetim
(gold set güvenilirliği, belge jargon taraması).

## Puanlar

| hakem | puan | kapsam |
|---|---|---|
| Jüri simülasyonu | **62 / 100** | ağırlıklı toplam |
| Şartname / uyum | **66 / 100** | ağırlıklı toplam |
| Ölçüm / istatistik | **15 / 30** | Model Başarısı |
| Güvenlik / on-prem | **13 / 20** | On-Prem |
| Kod / mimari | **13 / 20** | Teknik İmplementasyon |

İki bağımsız hakem toplamı **62** ve **66** verdi. Ölçüm hakemi Model
Başarısı'na 15/30, jüri simülasyonu aynı kaleme 15/30 verdi — **birbirinden
habersiz aynı sayı**. On-Prem'de de iki hakem bağımsız olarak 13/20'de
buluştu. Bu yakınsama, puanların gürültü olmadığını gösteriyor.

## Diskalifiye riski: YOK

Şartname hakemi tek tek doğruladı: ücretli API/servis/yazılım yok, tüm
bağımlılıklar MIT/Apache/BSD, model ağırlıklarının hepsi Apache-2.0/MIT ve
`base_model` zincirleri **köke kadar** takip edilmiş, Gemma/Llama açıkça
reddedilmiş, robots.txt uyumu kodda gerçekten uygulanıyor (domain başına
3 sn), provenance 1.772/1.776 belgede tam, repoda anahtar/kişisel veri yok.

Bu turda ayrıca bir **ters yönde** doğrulama disiplini kayda geçti:
`NuExtract-2.0-4B` etiketi temiz görünürken tabanı Qwen Research License
çıktı ve reddedildi. Model kartına değil zincire bakılmış.

---

## Bu denetimde kapatılan altı kusur

Hepsi hakemlerin bulgusu, hepsi bu turda düzeltildi ve testle kilitlendi.

### 1. Takvim yılı vade sanılıyordu — ürün yüzeyinde görünüyordu

Chatbot "en yüksek vade hangi bankada?" sorusuna **"Albaraka Türk, 24312
ay"** diyordu. Kök neden: `extract_vade` deseni `2026 yılı` ifadesini süre
sanıp 2026 × 12 yapıyordu. DB'de bu sınıftan 10 kayıt, artı bir açılır menü
döküntüsü (`2021 Ay` ≈ 168 yıl). Artefaktlar çıkınca korpustaki meşru en
yüksek vade tam olarak **120 ay**.

İki kapı eklendi (1900–2100 aralığı takvim yılıdır; aya çevrilmiş değer 600
ayı aşamaz), 9 regresyon testi. Gold n=48: mikro-F1 0,387 → 0,389,
halüsinasyon 45 → 44.

### 2. Şapkalı ünlü erişim token'ını düşürüyordu

`_tokenize` karakter sınıfı `â î û`'yu tanımıyordu, bu yüzden sözcük sınırı
sayıyordu:

    "kâr payı oranı"  ->  ['payı', 'oranı']      # kâr TAMAMEN düştü

`kâr payı` bu projenin **merkezî terimi** ve korpusun **319 belgesinde
(%18)** şapkalı yazılıyor. 36 bin karakterlik TKBB Müşâreke Standardı'nda
terim 89 kez geçmesine rağmen belge erişime hiç katılmıyordu. Şapka tabana
indirildi; yan kazanç olarak iki yazım birleşti. Kök-parçalı terim 2/15 →
1/15.

### 3. Ölçüm seti n=68 değil n=66

Ayrıklık kapısı gold.v1 ile v2'yi `content_hash` üzerinden karşılaştırıyordu.
Ölçüldü: v2'nin **48/48** kaydında `content_hash == sha256(text)`, v1'in
**0/20**'sinde. İki hash uzayı karşılaştırılamaz olduğu için kapı
**yapısal olarak** her zaman "kesişim yok" döndürüyordu. Gerçekte iki belge
örtüşüyor — aynı `id`, bayt bayt aynı metin.

Kapı artık metnin kendisini karşılaştırıyor. Ayrıca `gold.v1.json.sha256`
bütünlük çapası `da02e22`'den beri tutmuyordu (dosya değişti, çapa
yenilenmedi); yenilendi ve gold.v2'ye çapa eklendi.

### 4. Makro-F1 yalnız uydurma üreten alanları cezasız bırakıyordu

Süzgeç `support > 0` ve gerekçesi doğru (desteksiz alanın recall'u
tanımsızdır). Ama sonucu **tek yönlü ve lehimize**: gold bir alanda hiç değer
taşımıyorsa ama model orada **yalnızca uydurma** üretiyorsa, alan ortalamadan
tamamen düşüyor ve ceza sıfır oluyor.

gold.v2'de gerçekleşti: `tahsis_ucreti` desteksiz, tek çıktısı bir
halüsinasyon. Süzgeçli makro **0,409**, alan dâhil edilseydi **0,375** —
**+0,034 iyimser** ve hiçbir yerde görünmüyordu. Modülün kendi ilkesiyle
("bilmediğimizi lehimize sayamayız") çelişiyordu.

Süzgeç korundu, yanına `macro_f1_uydurma_dahil` kondu. İki sayının farkı,
ölçümün ne kadar iyimser olduğunun doğrudan ölçüsü.

### 5. LLM hattında toplam süre sınırı yoktu

`urlopen`'ın `timeout`'u **soket başına** işler. Sunucu bağlantıyı açık tutup
veri göndermezse süre hiç dolmaz. Ölçüldü: bir koşum `OLLAMA_TIMEOUT=900`
verilmiş olmasına rağmen **18 dakika** asılı kaldı — %0 CPU, log'a tek satır
yazmadan. Demo günü tek gerçek donma riski buydu.

Çağrı artık duvar-saati sınırıyla bağlı (`LLM_DEADLINE_CARPANI`).

### 6. Tutarı bilinmeyen ücret sıralamada 0 TL sayılıyordu

`_numeric_key`, `{"has_fee": True, "amount": None}` değerini **0,0** sayıp
`comparable=True` işaretliyordu. `masraf_durumu` "düşük daha iyi" alanı
olduğu için 0,0 sıralamanın **tepesidir**.

Sonuç demonun manşet ekranındaydı: kanıt metninde *"1.000 TL başvuru ücreti
tahsil edilecektir"* yazan bir kampanya, "En Düşük Masraf" sıralamasında
gerçekten ücretsiz olanların **önünde**, tek uyarı işareti olmadan.
Ölçüldü: `sort_key == 0.0` olan 509 satırın **35'i** ücretliydi.

Proje bunun yanlış olduğunu **zaten biliyordu**: ikiz fonksiyon
`_composite_numeric` tersini yapıyor ve gerekçesini yazıyor — *"sıfır saymak
'masrafsız' demek olurdu (yalan)"*. İlke doğru yazılmış, tek alanlı yola
uygulanmamıştı. Üstelik arayüzdeki `FairnessNotice` şeridi tam bu ayrımı
vaat ediyordu; sistem uyardığı karışıklığı kendisi yapıyordu.

Düzeltmeden sonra 31 kayıt doğru şekilde kıyaslanamaz işaretleniyor. Kök
neden **ayrışmaydı** — doğru semantik bir yolda kilitli, karşı semantik
diğerinde serbest. Parite testi ikisini birbirine bağladı.

### 7. Sunumda olmayan bir katman vaat ediliyordu

`docs/pitch_outline.md` — jüri sunumuna giden metin — "çıkarım üç katmanlı:
kurallar birincil, **GLiNER2 tamamlayıcı**" diyordu. GLiNER kodda **hiç
yok**. `model-license-audit.md` bunu zaten dürüstçe kaydetmiş, sunum
güncellenmemişti.

---

## Jüriye sunulan ve savunulamayan dört sayı — dördü de düzeltildi

Bunlar bu turda **README'ye benim yazdığım** satırlardı; hakemler çürüttü.

| iddia | gerçek |
|---|---|
| "849 belgede **0 ihlal**" | güncel korpusta koşuldu: **1.774 belgede 1 ihlal** (`P4_cumle_sirasi`), kapsam %91,3. Rozet korpus büyüyünce geçersizleşmiş, kimse yeniden koşmamış |
| "`kampanya_kosullari` 0,000 — **eşleştirici sertliği**" | **tolerant da tam olarak 0,000**, birebir aynı TP/FP/FN. Gevşetmek hiçbir şeyi değiştirmiyor; sorun liste karşılaştırmasının **küme eşitliği** araması. Beş koşuldan dördü tutsa bile FP+FN |
| "mikro-F1 0,389 **[0,329–0,442]**" | o aralık 0,387'lik **başka bir koşuma** ait. Yeniden ölçüldü: **[0,331–0,443]** |
| "McNemar **p=0,039**, kazanan kural" | projede **≥18 test** koşuldu, çoklu karşılaştırma düzeltmesi yok. Bu p herhangi bir düzeltme altında düşer. Sonuç (kural önde) dört ölçüte dayandığı için değişmiyor, **gerekçe olarak sunulan p yanlış** |

Ayrıca gold setin kimliği: README "insan-etiketli 66 belge" diyordu; gold.v2
**makine anotasyonlu**, `adjudicated: false`, belge başına tek anotatör.
Manşet metrik o sette ölçülmüş. İki setin statüsü artık ayrı tabloda.

Jüri hakeminin uyarısı yerinde: *"Sorun 'κ yok' olmaktan çıkar, 'beyanınız
ile kanıtınız uyuşmuyor'a döner. O noktadan sonra hiçbir sayınız
tartışılmaz."*

---

## EK — 2026-08-08 akşamı: puan yükseltme turu

Denetimden sonra aynı gün içinde yedi fazlık bir kapatma turu koşuldu. Üç yeni
sessiz kusur bulundu (8., 9., 10.) ve hepsi testle kilitlendi.

> Not: yukarıdaki bölüm "altı kusur" diyor ama **yedi** madde listeliyor;
> numaralandırma buradan devam ediyor.

### Kapatılanlar

| faz | ne yapıldı | ölçülen sonuç |
|---|---|---|
| 1 | κ hattı: `round1_A`/`round1_B` çiftinin **aynı 50 belge / 650 satır** olduğu bulundu; round1+round2 v2 protokolüne damgalandı | κ paketi 20 belgeden **50 belgeye** çıktı |
| 2 | `kampanya_kosullari` kalem düzeyinde puanlandı | alan 0,000 → **0,198**; mikro 0,389 → **0,338** |
| 3 | Vitrin sorusunun grounding hataları + kanıtsız değerler | 13 hatalı kayıt düştü, **26 kanıtsız kayıt → 0** |
| 4a | Bileşik skorlama `GET /advantageous` ile bağlandı | 9 kampanya türü sıralanıyor |
| 4b | "3 katman" anlatısı dürüst 2 katmana indirildi | erişilmez dal açıkça işaretlendi |
| 4c | Postgres paritesi koşuldu | **53 atlanan test → 0**, `postgres.py` %20,4 → **%80,4** |
| 5 | Ağ kapalı tam prova (`--internal` Docker ağı) | kalkış **1,5 sn**, API **106 MiB**, en yavaş uç p95 **64 ms** |
| 6 | Özet üretimi (sürüyor) | hata %40 → **%0**, hız 44 → **6,9 sn/belge** |
| 7 | Yayın dalı `yayin/hafta-05` **push edildi** | `origin/main` 31 Tem → **8 Ağu** |

### Bulunan üç yeni sessiz kusur

**8. Gold derleyici v2 protokolünü hiç bilmiyordu.** `report_iaa` ve
`lint_review_csv` protokolü sayıyordu, `build_gold` koşulsuz `verdict = "ok"`
diyordu. Yani **κ dürüst, gold çapalı** olacaktı: ekip v2 dosyasını doldurup
derleseydi dokunulmamış her satır sessizce "model doğru" sayılırdı — kılavuzun
§3.1 ile kaldırdığı çapalamanın kendisi. Ayrıca canlı kalibrasyon dosyasında
**134 satırda not var ama karar yok** (*"Ödül tutarı yok"* yazıp `verdict` boş).

**9. Oran tablosunda kanıt bağı sessizce kopuyordu.** `parse_rate_table`
başlıkta "payı"yı opsiyonel sayıyor, `extract_from_rate_table` zorunlu tutan
**ikinci bir arama** yapıyordu. Tablo ayrışıyor, değer üretiliyor, konum
`(0,0)`'a düşüyordu: `raw_value` boş, span yok, güven yine 0,95. 70 kaydın
**26'sı (%37)** böyleydi — "her değer bir karakter aralığına bağlıdır" iddiası
bu alanın üçte birinde tutmuyordu.

**10. LLM çıktısında token sınırı yoktu.** Model geçerli özet üretip JSON'u
kapatmadan `<tool_call>` yazıyor ve çöp döngüsüne giriyordu. Tek arıza iki
yüzle görünüyordu: döngü zaman aşımına kadar sürerse `LLMTransportError`
(180 sn), bağlam dolup çıktı kesilirse `LLMError`. 5. kusurda eklenen
duvar-saati sınırı doğru çalışıyordu ama **sebebi teşhis edilmemişti**.

### Ortak kalıp: ayrışma, dördüncü ve beşinci kez

6. kusur (`_numeric_key` / `_composite_numeric`) bir kalıbın ilk örneğiydi;
bu turda **dört tane daha** bulundu:

| ayrışan çift | bedeli |
|---|---|
| `build_gold` / `report_iaa` (protokol) | κ dürüst, gold çapalı |
| `parse_rate_table` / `extract_from_rate_table` (başlık deseni) | değer var, kanıt yok |
| `schema.sql` / `_SQLITE_SCHEMA` (`extractor` CHECK) | iki backend aynı veriyi kabul etmiyor |
| `/scoring` metni / `compare.py` kodu | uç kendi kodunu yalanlıyor |

Kalıp her seferinde aynı: **doğru kural bir yolda kilitli, karşıtı diğerinde
serbest, ve fark sessiz.** Beşinin de üstüne yolları birbirine bağlayan parite
testleri yazıldı — tek doğruluk kaynağı yetmiyor, bağ gerekiyor.

### Kişisel veri

Yayın dalı taranınca mentörün adının **17 izlenen dosyada** geçtiği bulundu
(kod yorumları, bir test, kasa sayfaları, dosya adı). Kaynak sayfasını
geçmişten çıkarmak yetmiyordu. Ad role dönüştürüldü (`Mentör (eski bankacı)`),
kaynak dosyası yeniden adlandırıldı, 11 wikilink güncellendi. Katkının izi ve
gerekçesi korundu; kişi tanımlanamıyor (CLAUDE.md §19).

---

## Kapanmayan üç açık

### A. κ ölçülmedi — §16'nın tek karşılanmayan kalemi

> **GÜNCELLEME (8 Ağu akşamı): artık ÖLÇÜLEBİLİR.** `round1_A`/`round1_B`
> çifti birebir aynı 50 belgeyi ve 650 satırı taşıyor; v2 protokolüne
> damgalandı ve doldurulmayı bekliyor. Eksik olan tek şey insan işi.

Kod hazır (`eval/iaa.py`: Cohen, Fleiss, Krippendorff), eşikler **önceden
ilan edilmiş** (κ≥0,80 kabul · 0,67–0,80 notla · <0,67 hakemlik), CSV paketi
bekliyor. Eksik olan **veri**: v2 kalibrasyon paketinin dört dosyası da boş
ve gold.v2'nin dört anotatörü **ayrık** kümelere baktı — örtüşme sıfır, κ
tanımsız.

Model Başarısı'nın tamamı, güvenilirliği ölçülmemiş 66 belgelik bir etikete
dayanıyor. **En öncelikli açık budur ve insan işidir.**

### B. Vitrin sorusu yanlış cevap veriyor

> **GÜNCELLEME (8 Ağu akşamı): KAPANDI.** Üç desen de yakalandı (13 kayıt
> düştü), 26 kanıtsız kayıt sıfırlandı, chatbot uçtan uca doğrulandı.

"En düşük kâr payı hangi bankada?" sorusunda üç gerçek grounding hatası
ölçüldü ve **henüz düzeltilmedi**:

| desen | örnek | kayıt |
|---|---|---|
| erken ödeme cezası formülü | `(yıllık bileşik kâr payı oranı **\* 0,05**)` | 3 |
| aynı formülün sözel hâli | `bileşik kâr payı oranının **yüzde 5'i**` | 8 |
| kâr paylaşım payı | `brüt kâr payının **%50**'si geri alınır` | 2 |

Ayrıca `kar_payi_orani` kayıtlarının **26/70'inde** `raw_value` boş ve
`span=[0,0]` — yani "her değer bir karakter aralığına bağlı" iddiası bu
alanın **%37'sinde tutmuyor**.

Mevcut `_CEZA_BAGLAMI_RE` kapısı bu desenleri kapsayacak şekilde
genişletilebilir; desen zaten yazılı.

### C. Ölçüm setinin kendisi dar

`kar_payi_orani` gold.v2'de yalnız **3 karar** destekli — oradan çıkan F1
yorumlanamaz. Korpusta da alan 70 belgede (%3,9) var. Bu bir model kısıtı
değil **veri gerçeği**: bankalar oranları kampanya sayfalarında büyük ölçüde
yayımlamıyor. Ama senaryonun kalp alanı bu, ve ölçülmemiş sayılır.

> **Düzeltme (2026-08-15).** Bu paragraf "TP 1, FN 2" ve "70/1.774" diyordu;
> ikisi de yanlıştı. Gerçek: **TP 2, FN 1** (F1 0,800, yine yorumlanamaz —
> üç karar bir F1 taşımaz) ve payda **1.782**. Aynı %3,9 oranı üç ayrı
> paydayla dolaştığı için (1.684 · 1.774 · 1.782) hata yakalanmamıştı. Sayı
> artık `scripts/kanit_tazeligi.py` kapısına bağlıdır.

---

### D. Kod/mimari hakeminin üç ek açığı

> **GÜNCELLEME (8 Ağu akşamı): ÜÇÜ DE KAPANDI.** Katman anlatısı 2'ye
> indirildi, bileşik skorlama `/advantageous` ile bağlandı, Postgres paritesi
> koşuldu (53 atlanan test → 0, kapsam %20,4 → %80,4).

- **"3 katmanlı mimari" fiilen 2 katman.** `Extractor.NER` hiçbir kod
  yolunda üretilmiyor; `reconcile._PRIORITY`'nin orta basamağı erişilmez dal.
  `reconcile.py` başlığı hâlâ "3 katmanı birleştirir" diyor. Dürüst bir
  2-katman anlatısı, erişilmez bir daldan iyi okunur.
- **§5.7'nin beşinci ölçütü (bileşik skorlama) yazılmış, test edilmiş,
  hiçbir uçtan çağrılmıyor** — ~420 satır. Üstelik `/scoring` ucu
  *"kod tabanında ağırlıklı bileşik skor **yoktur**"* diyerek kendi kodunu
  yalanlıyor; `DEFAULT_WEIGHTS` gerekçeleriyle o dosyada duruyor.
- **Postgres paritesi varsayılan koşumda hiç doğrulanmıyor** — 53 testin
  tamamı atlanıyor, `postgres.py` kapsamı %20,4. Ayrıca `schema.sql`
  `extractor` için `CHECK` kısıtı taşıyor, `_SQLITE_SCHEMA` taşımıyor.

Aynı hakem test kapsamını ölçtü: toplam **%67,7**, ama kritik yollar gerçekten
kapsanmış (`extract.py` %96,5, `normalization` %93,3, `safety.py` %92,0,
`router.py` %95,9). Kapsanmayan alanlar dış servis gerektirenler ve CLI'lar —
yani "kanıt üretemeyeceğimiz" yerler. Sayı kolay yerlerde şişmemiş.

Ölü kod taraması: 54.000 satırlık ağaçta yalnız 15 sembol çağrılmıyor. Hakem
bunu *"çok temiz"* diye niteledi.

## Hakemlerin ortak vurgusu: en güçlü yan ölçüm dürüstlüğü

Dört hakem birbirinden bağımsız aynı şeyi söyledi. Jüri simülasyonundan:

> "Kendi mimarisini çürüten ablasyonu, 'n=20'deki kazanç gürültüymüş'
> itirafını, `git_dirty` bayrağının neden tetiklendiğinin açıklamasını
> yayımlayan başka takım görmedim."

Ölçüm hakemi altyapıya **+9** verdi ve kesintilerin *"bu altyapının kendi
kurallarına uymadığı yerlerden"* geldiğini yazdı. Bu doğru teşhis: harness
disiplinli, ihlaller onu kullanan belgelerde.

**Ölçümle yanlışlanan üç hipotez** (hibrit kol, orkestrasyon, BERTurk — üçü
de kural katmanının altında kaldı) sunumun merkezine konmalı. Mekanizma
üçünde de aynı: LLM doğru sayısını artırmıyor, yanlış sayısını artırıyor.
Hakem katmanının pozitif katkısı ayrıca ölçüldü (McNemar p=0,0156,
halüsinasyon 60 → 53) ve **düzeltme altında da ayakta kalıyor**.

## Sunum açılışı için hakem önerisi

> *"Sistemimizin tamamı kural tabanlı — çünkü LLM eklemeyi üç kez denedik,
> üçünde de ölçtük, üçünde de kural katmanı kazandı; bu negatif sonuçların
> üçünü de raporumuzda yayımladık."*

Gerekçe: 0,389 ile açmak savunmaya düşürür, "regex" ile açmak yarışmanın
adıyla çarpışır. Tek güçlü giriş, zayıflığı **ölçülmüş bir karar** olarak
sahiplenmektir — çünkü gerçekten öyle.

## Sıradaki üç iş (hakemlerin ortak önceliği)

1. **κ'yı ölç** — 20 belgelik kalibrasyon paketini iki bağımsız kişi
   doldursun. Şartnamenin kapanmayan tek kalemi. *(insan işi)*
2. **`kampanya_kosullari`'nı kalem düzeyinde puanla** — bugünkü metrik sistemi
   hak ettiğinden kötü gösteriyor ve manşet sayının ~%28'ini oluşturuyor.
   Düzelme **ölçüm düzelmesidir, sistem düzelmesi değil** ve öyle
   etiketlenmeli.
3. **Vitrin sorusunun grounding hatalarını kapat** — üç desen de yakalanabilir,
   kapı deseni zaten yazılı.

Ve senin kararını bekleyen: **push**. `origin/main` 31 Temmuz'da donmuş;
jüri GitHub'a bakıyor, yerel diske değil.

## Sources
- Altı hakem raporu (bu oturum, dosyaya yazılmadı — bulgular buraya sentezlendi)
- `docs/rapor/ablasyon.md`, `gold-genisletme.md`, `o1-terim-deneyi.md`,
  `berturk-ince-ayar-plani.md`, `guvenlik-llm-modu.md`, `belge-turu.md`
- `eval/reports/` koşum künyeleri

## Related
- [[yapilacaklar]] — açık kalemler ve teknik borç
- [[karar-bekleyenler]] — K-3 (push) tek açık karar
