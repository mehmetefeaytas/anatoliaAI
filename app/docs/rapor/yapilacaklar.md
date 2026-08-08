# Yapılacaklar — 2026-08-08 · teslime **18 gün**

Bu liste **bugünkü** durumu yansıtır. `yapilacaklar-envanteri.md` (3 Ağustos,
62 KB) tam envanterdir ama bayattır; buradaki maddelerle çeliştiğinde **bu
dosya geçerlidir**.

Sıralama ölçütü: TEKNOFEST ağırlıkları × şu anki açık.
Model Başarısı %30 · Fonksiyonellik %20 · Teknik %20 · On-Prem %20 · Yenilik %10

**S** = sende (insan işi, ben yapamam) · **B** = bende (kodlanabilir)

---

## 0. Senin kararını bekleyen

| # | karar | durum |
|---|---|---|
| ~~K-1~~ | Çerçeve ayıklaması | **kapandı** — çıkarımda uygulanmıyor; ayıklama arayüze taşındı (çerçeve katlanıyor + LLM özeti) |
| ~~K-2~~ | `DEFAULT_CONFIG` | **kapandı** — `kural`. Orkestra n=48'de geçemedi |
| ~~K-4~~ | Prompt-injection LLM modu | **kapandı** — koşuldu, sentez açıkken de 22/22 |
| **K-3** | **106 commit push edilmedi** | **AÇIK — tek bekleyen karar** |

**K-3 tek kalan.** `yayin/hafta-04` dalı hazırlandı ve iki yayın-dışı dosya
geçmişinden çıkarıldı, doğrulandı. Ama dal o günden beri **bayatladı**; push
öncesi çalışma dalından yeniden üretilmeli. Ayrıca yayın kademesi denetimi
`yapilacaklar.md` ve `karar-bekleyenler.md` için de kademe-3 önerdi — ikisi
de kendi açıklarımızı madde madde sayıyor. Karar senin.
Ayrıntı: `yayin-kademesi.md` (kendisi de yayınlanmıyor).

---

## 1. Model Başarısı %30 — en ağır kalem

| | iş | kim | durum |
|---|---|---|---|
| 1.1 | gold.v2 anotasyonu — 48 belge, 10 banka, kör protokol | B | **bitti** |
| 1.2 | gold.v2'de kural kolu, gold.v1 ile ayrı raporlandı | B | **bitti** (0,387 vs 0,677 — sebebi protokol) |
| 1.3 | K-1'i geniş sette tekrarla | B | **bitti** — F1 kazancı gürültüymüş |
| 1.4 | McNemar eşleştirilmiş test | B | **bitti** — üç çiftte de anlamlı fark yok |
| 1.4b | Anotasyon kılavuzundaki 8 boşluk + §3.1 çapa düzeltmesi | B | **bitti** |
| 1.5 | **κ ölçümü** — çift anotasyonlu 20 belgelik paket hazır, doldurulmayı bekliyor | **S** | hat hazır, veri senden |
| 1.6 | Ö1 üç kollu terim deneyi | B | **bitti** — sadeleştirme reddedildi |
| 1.7 | BERTurk ince ayarı | B | **bitti** — kapıda kaldı, model ALINMADI |
| 1.8 | gold.v2'de orkestra kolu | B | **bitti** — kuralı geçemedi |

**Bu bölümün özeti:** Model Başarısı tarafında ölçülmemiş iş kalmadı. Üç ayrı
"daha güçlü model ekleyelim" denemesi (hibrit kol, orkestrasyon, BERTurk)
**üçü de ölçümle yanlışlandı**; kural katmanı her seferinde önde kaldı ve
mekanizma her seferinde aynı çıktı — doğru sayısı artmıyor, yanlış artıyor.
Bu, jüriye anlatılacak en güçlü tek bulgudur.

**1.5 senin elinde:** düzeltilmiş kılavuz ve aynı 20 belgeyi taşıyan çift
anotasyon paketi hazır (`data/gold/review/round0_kalibrasyon_v2_*.csv`).
Doldurulunca `python -m scripts.report_iaa <dosyalar>` tek komutla Fleiss κ +
Krippendorff α üretir. Eşikler önceden ilan edildi (κ≥0,80 kabul · 0,67–0,80
notla · <0,67 hakemlik), sonradan oynatılmayacak.

**1.4b neden kritik:** dört anotatör **bağımsız olarak** aynı üç boşluğu
işaretledi — kampanya olmayan belgeler için sınıf yok (gold.v2'nin %19'u),
ürün kısıtı mı müşteri segmenti mi, tutar cinsinden indirim hangi alana
gider. Kılavuz düzeltilmeden ölçülen κ, anotatör uyumsuzluğunu değil
**kılavuz belirsizliğini** ölçer. Ayrıntı: `gold-genisletme.md` §4.

## 2. Fonksiyonellik %20 — Faz G dashboard

Altısı da **bitti** (`npm run build` geçiyor): kıyas tablosu · kaynak gösteren
chatbot (artık tıklanabilir `campaign_id` + `source_url`) · çelişki tespiti ·
banka içi delta ekranı · güven skorları jüri moduna alındı · **"0 = ürün yok,
ceza değil"** ve adil-kıyas notu arayüzde yazıyor.

Ek olarak K-1'in yeni hâli: metnin gösterildiği yerlerde çerçeve **siliniyor
değil katlanıyor** — `source_span` offset'leri ham metne göre olduğu için
silme bütün kaynak vurgularını kaydırırdı. Katlanmış bir bloğun içinde kanıt
span'i varsa blok otomatik açılıyor; kanıt gizlenemiyor.

| kalan | durum |
|---|---|
| LLM özetlerinin önceden üretimi | **kısmi** — makine ~28 sn/belge yapıyor, tam korpus ~13 saat. Kıyasta görünen alt küme üretiliyor; arayüz özet yoksa bölümü hiç göstermiyor (sahte özet basmıyor) |

## 3. Şartname zorunlulukları — yapılmazsa puan yanar

| | iş | kim |
|---|---|---|
| 3.1 | **5 dakikalık demo videosu** + 1 dakikalık kısa versiyon | **S** |
| 3.2 | Jüri sunumu **PDF ve PPTX** olarak | **S** |
| 3.3 | Veri setini herkese açık yayınla + **açık lisans** ata | **S** + B |
| 3.4 | Haftalık commit etiketleri (`hafta-02`, `hafta-03`…) | **S** (K-3'e bağlı) |
| 3.5 | `assets/demo_backup.mp4` — canlı demo çökerse tek sigorta | **S** |
| 3.6 | Ağ kapalı uçtan uca demo provası (Wi-Fi kapalı + container ağı kesik) | B + **S** |

## 4. Mentör / insan işleri

| | iş | kim |
|---|---|---|
| 4.1 | **Cavide Hanım'a dönüş**: TCMB çapraz analizinin 19 terimlik `ayrim_notu` zenginleştirme önerisi onayını bekliyor | **S** |
| 4.2 | Samet Bey'in ödevi: problem / hangi sorun / farkımız / MVP / somut bitiş | **S** |
| 4.3 | 4 mentör toplantısı şartının tuttuğunu sekretaryaya doğrula | **S** |
| 4.4 | `iletisim@teknofest.org` — ücretli LLM sorusu; **yazılı cevap savunma olur** | **S** |

## 5. Teknik borç — ölçülmüş, kapatılmamış

| | iş | not |
|---|---|---|
| ~~5.1~~ | Sözleşme PDF'leri kampanya gibi işleniyor | **kapandı** — `belge_turu` sütunu; 113 sözleşme kıyastan çıktı, RAG'de kaldı. Ayrım bölüme değil belgenin kendisine dayanıyor (113/113 `.pdf`) |
| 5.2 | `müşaraka` 3 belgede, hiçbiri tanım değil | veri boşluğu — hedefli toplama sırada |
| 5.3 | Güvenlik setinde 2 kayıt düşüyor (C05, K02) | teşhis sürüyor |
| 5.4 | `rakip-analizi.md` teslim öncesi tekrar koşulmalı | |
| **5.5** | **LLM çağrısında toplam süre sınırı yok** | **yeni.** `urllib` zaman aşımı soket başına; bağlantı açık kalıp veri gelmeyince tetiklenmiyor. Demo donanımında model takılırsa arayüz süresiz bekler. `OLLAMA_TIMEOUT` eklendi ama bu bir *soket* sınırı — hattın **deadline**'ı ayrı iş |
| **5.7** | **κ hâlâ ÖLÇÜLEMEZ durumda** | **yeni, kritik.** v2 kalibrasyon paketinin 4 dosyası da tamamen boş; gold.v2'nin 4 anotatörü **ayrık** kümelere baktı, örtüşme sıfır. "4 anotatör" çift anotasyon demek değil. Kod, eşik ve CSV hazır — **eksik olan tek şey doldurulmuş veri** |
| **5.8** | **`jargon_lint` `docs/*.md`'yi taramıyor** | **yeni.** İç çalışma belgelerinde konvansiyonel terim kullanımı denetlenmiyor. Jüriye giden teknik raporda ihlal YOK (denetlendi), yani risk sınırlı; ama muafiyet listesiyle birlikte kapsamı genişletmek en ucuz kapanış |
| **5.9** | **`parca/etiket-*.json` ile `gold.v2.json` kimlik kuralı ayrışmış** | **yeni.** Parçalarda sayısal id (`kuveyt-turk--35985512`), çıktıda slug id; kesişim **0/48**. `merge_gold_v2` bugün yeniden koşulursa gold.v2 sayısal id'lerle üretilir ve id-anahtarlı her eşleştirme (ablasyon, McNemar, çerçeve ayıklaması) **sessizce** boşa düşer. Bu kusur bir kez zaten gerçekleşti |
| **5.6** | **`build_summaries` parti sonunda yazıyor** | **yeni.** Kesilen koşum bütün işini kaybediyor; 20 belgelik parça 569 sn sürüyor ve erken kesilirse 0 satır yazılıyor |

## Bu turda kapananlar (kayıt için)

- Klasik veriyle ince ayar / RAG **reddedildi**, gerekçesi kalıcı kayıtta
- Klasik korpus dizinin kendisinde **"YARIŞMA KAPSAMI DIŞI"** etiketli
- **TCMB Terimler Sözlüğü** (314 terim) karşıt-otorite referansı olarak eklendi;
  katılım terimlerinin **%93,1'i** TCMB'de yok — tezin ölçülmüş kanıtı
- RAG terim kapsaması **4/15 → 14/15** (korpus tazelendi + erişim eşiği oransal oldu)
- Gecikme cezası maddesinden kâr payı oranı çıkarma hatası kapatıldı (**15 → 1**)
- `demo.db` yeniden kuruldu: **849 → 1761 belge**
- Ölçüm seti **n=20 → n=66**'ya çıktı (önce 68 sanılmıştı; iki belge örtüşüyordu); K-1 geniş sette tekrarlandı ve
  n=20'deki F1 kazancının gürültü olduğu, halüsinasyon kazancının gerçek
  olduğu ayrıştı
- **gold.v1'in 0,677'si çapa etkisi taşıyor** — kılavuz §3.1 "boş bırakmak
  = model doğru" diyor. Kör protokolde karşılığı 0,536 (liste alanı hariç).
  Bu, jüriye tek sayı sunmama gerekçesidir
- Tek karakterli token'ın erişim eşiğini gürültüyle doldurması kapatıldı
- Demo DB tazelik kapısı + testleri (CI'da)
