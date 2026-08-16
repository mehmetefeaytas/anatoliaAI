---
title: Demo videosu — kurgu, çekim listesi ve seslendirme metni
tags: [sunum, demo, video, teslim]
date: 2026-08-16
status: stable
---

# Demo videosu — 2:30 kurgu paketi

**Hedef süre:** 2 dk 30 sn (şartname s.14 tavanı 5 dk; s.19 ayrıca 1 dk'lık
kesit istiyor — §K'de).

**Videonun işi tanıtmak değil, dört soruyu cevaplamak:**

1. Ne problemi çözüyor?
2. Nasıl çözüyor?
3. **Gerçekten çalışıyor mu?**
4. Neden diğerlerinden daha iyi?

Üçüncü soru videonun omurgasıdır. Bu yüzden **sahte ekran yok**: her kare
çalışan sistemden alınır. Animasyon yalnız geçiş ve vurgu için kullanılır,
anlatının yerine geçmez.

> ✅ **VİDEO ÜRETİLDİ (2026-08-16).** Bu belge planı da, üretilenin künyesini
> de taşıyor: `anatolia-ai-demo.mp4` (**1:55**) ve `anatolia-ai-demo-1dk.mp4`
> (**0:59**). Aşağıdaki sahne planı korundu; ölçülen sonuç ve üretim hattı
> belgenin sonunda. Hat tamamen betikli — tek komutla yeniden üretilebilir.

---

## Ç) Çekim öncesi — 20 dakikalık hazırlık

Bunlar yapılmadan çekime başlanmaz; yarısı çekim sırasında fark edilirse
sahne yeniden çekilir.

```bash
cd app
docker compose up -d                      # pano + API ayakta
python -m scripts.check_demo_db           # korpus 1.782, kapı yeşil mi
python -m scripts.kanit_tazeligi          # 0 sapma olmalı — sahne 8'de görünecek
python -m scripts.test_ozeti              # sahne 8'deki sayılar buradan
```

**Ekran hijyeni:** 1920×1080, tarayıcı tam ekran (`⌘⌃F`), yer imleri gizli,
bildirimler kapalı, açık sekme yalnız pano. Terminal koyu tema, yazı tipi
boyutu **16 pt'den küçük olmasın** — jüri projeksiyonda okuyacak.

**İmleç:** yakalama aracında imleç vurgusu açık, tıklama halkası açık.
Sahne başına en fazla bir kez tıklama; imleç dolaşmaz.

---

## A) Sahne planı — zaman kodlu

Süreler **kümülatif**tir. Seslendirme cümleleri `S1`, `S2`… olarak
numaralandı; §S'de aynı numaralarla yeniden kaydedilebilir.

| # | Zaman | Süre | Ekranda ne var | Çekim notu |
|---|---|---|---|---|
| 1 | 0:00–0:12 | 12 sn | Açılış kartı → pano ilk kare | Kart 3 sn, sonra panoya sinematik geçiş (`cross-dissolve`, 400 ms) |
| 2 | 0:12–0:32 | 20 sn | Dört banka sayfası, yan yana | Ekran bölme; her sayfada farklı ifade biçimi vurgulanır |
| 3 | 0:32–0:44 | 12 sn | Pano açılışı — 1.782 belge | `panel-acilis.png` karesi canlı çekilir |
| 4 | 0:44–1:12 | 28 sn | **Kıyas cetveli** — asıl iş | Filtre → sıralama → sonuç. Tek akış, kesintisiz |
| 5 | 1:12–1:34 | 22 sn | **Kanıt vurgulama** — WOW anı | Değere tıkla → belgede kaynak vurgulanır |
| 6 | 1:34–1:50 | 16 sn | Sohbet: cevap + **reddetme** | İki soru: biri cevaplanır, biri reddedilir |
| 7 | 1:50–2:04 | 14 sn | Mimari animasyonu | Sade akış şeması, 6 kutu |
| 8 | 2:04–2:22 | 18 sn | Terminal: kapılar + sayılar | `kanit_tazeligi` canlı koşar |
| 9 | 2:22–2:30 | 8 sn | Kapanış kartı | Logo + slogan + depo adresi |

---

## B) Sahne sahne — ne kaydedilecek

### Sahne 1 · Açılış (0:00–0:12)

**Görüntü.** Siyah zeminde tek satır belirir: **Anatolia AI**. Altına ince
harflerle *"Katılım bankacılığı kampanya metinlerinden ölçülen bilgi
çıkarımı"*. 3 saniye sonra kart panoya karışır (`cross-dissolve`).

**Kaynak.** Açılış kartı için `app/docs/sunum/anatolia-ai-sunum.html`
slayt 01 tam ekran kullanılabilir — ayrı bir grafik üretmeye gerek yok.

**Hedef.** İlk 10 saniyede izleyici projenin ne yaptığını bilmeli.

---

### Sahne 2 · Problem (0:12–0:32)

**Görüntü.** Dört gerçek banka sayfası ekranda ikişerli belirir. Her birinde
aynı bilginin farklı ifadesi **sarı ile vurgulanır**:

- *"İlk 6 ay masrafsız"*
- *"%1,99–%2,49 arası kâr payı"*
- *"120 aya kadar vade"*
- *"Dosya masrafı yok"* — yıldız işaretiyle

Vurgular sırayla, 400 ms arayla yanar. Sonra dördü de küçülüp ekranın
köşesine toplanır; ortada tek soru kalır: **"Hangisi daha uygun?"**

**Çekim notu.** Sayfalar canlı sitelerden değil, `data/raw/` altındaki
**kaydedilmiş** kopyalardan açılır — provenance'lı, tekrar üretilebilir ve
çekim günü site değişse bile kare bozulmaz.

---

### Sahne 3 · Çözüm belirir (0:32–0:44)

**Görüntü.** Pano açılır. Üstteki sayaç **1.782 belge** yazar. Kamera
(zoom-in) sayaca 1,2× yaklaşır ve geri çekilir.

**Çekim notu.** Sayfa yüklenmesini kesme — yükleme hızı da bir iddiadır.
Soğuk kalkış ölçülmüştür ve gerçek süresiyle kalsın.

---

### Sahne 4 · Gerçek kullanım — kıyas cetveli (0:44–1:12) ⏱ **en uzun sahne**

Videonun "gerçekten çalışıyor mu" sorusunu cevaplayan bölüm. **Tek kesintisiz
akış**, kesme yok:

1. Kampanya türü süzgecinden **Konut Finansmanı** seçilir. *(3 sn)*
2. Vade süzgeci **36 ay**'a çekilir. *(3 sn)*
3. Sonuç listesi yeniden dizilir — animasyon canlı yakalanır. *(4 sn)*
4. **Kâr payı oranına** göre sıralanır; en düşük başa gelir. *(4 sn)*
5. Ekran, *"doğrudan kıyaslanamaz"* işaretli satıra kayar ve orada durur. *(6 sn)*
6. O satıra tıklanır; sebep açılır: *oran zaman koşullu*. *(8 sn)*

**Vurgulanacak etiket (alt yazı olarak):** *"Adil kıyas garantisi — yalnız
aynı birime normalize edilmiş alanlar kıyaslanır."*

**Neden bu adım kritik.** Rakip sistemler her satırı sıralar. Bizim sistemimiz
**sıralanamayanı sıralamayı reddeder** ve sebebini yazar. Jüri farkı burada
görür.

---

### Sahne 5 · WOW anı — kanıt vurgulama (1:12–1:34)

**Bu sahne videonun kalbidir. Diğerlerinden 1,5 kat daha yavaş kurgulanır.**

1. Kıyas tablosundaki bir **kâr payı değerine** tıklanır. *(2 sn)*
2. Yan panel açılır: kaynak belge belirir. *(3 sn)*
3. Belgede **değerin geldiği cümle vurgulanır** — kamera vurguya 1,4× yaklaşır. *(6 sn)*
4. Yanında güven skoru ve gerekçe görünür: *"tetikleyiciye bitişik · makul aralıkta"*. *(5 sn)*
5. Kamera geri çekilir; alt yazı: **"Her değer, belgede bir karakter aralığına bağlıdır."** *(6 sn)*

**Çekim notu.** Bu vurgu bir görselleştirme değil, `verify_span()` ile
programatik olarak doğrulanan bir bağdır: `text[start:end] == raw_value`.
Alt yazıda bu ifade **birebir** görünsün — jüri kodda arayabilsin.

---

### Sahne 6 · Sohbet ve reddetme (1:34–1:50)

İki soru, arka arkaya:

**Soru 1 (cevaplanır).** *"36 ay vade veren konut finansmanlarında en düşük
kâr payı hangi bankada?"* → Cevap kaynak listesiyle gelir. *(8 sn)*

**Soru 2 (reddedilir).** *"Bu bankanın 2027 faiz tahmini nedir?"* → Sistem
tahmin üretmez, gerekçesini yazar. *(8 sn)*

**Alt yazı:** *"Reddetme kararı doğruluğu 30/30."*

**Neden ikinci soru var.** Bir sistemin ne bildiğini göstermek kolay; **ne
bilmediğini bildiğini** göstermek zordur. Çoğu demo bu kareyi atlar.

---

### Sahne 7 · Mimari (1:50–2:04)

**Görüntü.** Altı kutu, soldan sağa sırayla belirir (her biri 200 ms):

```
topla → temizle → ÇIKAR → normalize et → kıyasla → sun
                    ▲
         kural (birincil) · LLM yalnız boşluklara
```

**Kural kutusu vurgulanır.** Altına tek satır: *"Bilgi metinde yoksa değer
üretilmez — `null` döner."*

**Çekim notu.** Bu şema `README.md` içindeki ASCII şemasının temiz
sürümüdür; iki yerde farklı bir mimari anlatılmasın.

---

### Sahne 8 · Ölçüm — kapı canlı koşar (2:04–2:22)

**Görüntü.** Terminal. Komut yazılır ve **gerçekten koşturulur**:

```bash
python -m scripts.kanit_tazeligi
```

Çıktı akar ve şu satırda durur:

```
10 iddia · 0 sapma · 0 kanıt eksik
```

Kamera bu satıra yaklaşır. Sonra ekranın sağ yarısında dört sayı belirir:

| | |
|---|---|
| **0,671** | yapılandırılmış alan mikro-F1 |
| **0,047** | halüsinasyon oranı |
| **2.946** | yeşil test |
| **14/14** | ağsız kanıt adımı |

**Alt yazı:** *"Bu README'deki her sayı, onu üreten komutla eşleşmek zorunda.
Ayrışırsa yapı kırmızı yanar."*

**Çekim notu.** Komut **canlı** koşsun; önceden alınmış bir ekran görüntüsü
kullanılmasın. Bu videonun en güçlü tek karesi, bir kapının gerçekten
çalıştığını görmektir.

---

### Sahne 9 · Kapanış (2:22–2:30)

Siyah zemin. Sırayla:

- **Anatolia AI**
- *Tek bir parlak yüzde vermiyoruz.*
- `github.com/mehmetefeaytas/anatoliaAI`

Son kare 2 saniye sabit kalır.

---

## S) Seslendirme metni

**Ton:** sakin, kendinden emin, ürün lansmanı. Acele etmeden. Cümleler kısa
tutuldu — kendi sesinle yeniden kaydederken **cümle cümle** değiştirebilirsin
ve senkron bozulmaz.

**Toplam okuma süresi:** ~2 dk 05 sn (2:30'luk videoda ~25 sn nefes payı).
Bu pay bilerek bırakıldı: sahne 4, 5 ve 8'de görüntü tek başına konuşmalı.

| # | Zaman | Sahne | Metin |
|---|---|---|---|
| **S1** | 0:00 | 1 | Anatolia AI. |
| **S2** | 0:04 | 1 | Katılım bankacılığı kampanya metinlerinden, ölçülen ve kanıtlanan bilgi çıkarımı. |
| **S3** | 0:13 | 2 | Aynı bilgi, on bankada on farklı biçimde yazılıyor. |
| **S4** | 0:19 | 2 | "İlk altı ay masrafsız." "Yüzde bir doksan dokuz ile iki kırk dokuz arası." "Yüz yirmi aya kadar vade." |
| **S5** | 0:28 | 2 | Hangisinin daha uygun olduğunu, bir insanın elle karşılaştırması pratikte mümkün değil. |
| **S6** | 0:34 | 3 | Anatolia AI on katılım bankasından bin yedi yüz seksen iki belgeyi topladı ve karşılaştırılabilir yapısal veriye dönüştürdü. |
| **S7** | 0:46 | 4 | Kampanya türünü ve vadeyi seçiyoruz. |
| **S8** | 0:52 | 4 | Sistem kâr payına göre sıralıyor. |
| **S9** | 0:59 | 4 | Ama iki kampanyayı sıralamayı reddediyor. |
| **S10** | 1:03 | 4 | Çünkü oranları zaman koşullu — doğrudan kıyaslanamazlar, ve sistem bunu uydurmak yerine söylüyor. |
| **S11** | 1:14 | 5 | Peki bu değer nereden geldi? |
| **S12** | 1:19 | 5 | Değere tıkladığınızda sistem, o sayının geldiği cümleyi belgede işaretliyor. |
| **S13** | 1:27 | 5 | Her değer, kaynak belgede bir karakter aralığına bağlı. Bu bağ programatik olarak doğrulanıyor. |
| **S14** | 1:36 | 6 | Sohbet katmanı soruyu anlıyor ve cevabı kaynağıyla veriyor. |
| **S15** | 1:43 | 6 | Cevabı bilmediğinde ise tahmin üretmiyor. Reddediyor — ve neden reddettiğini yazıyor. |
| **S16** | 1:52 | 7 | Arkada iki katman var. Kurallar birincil; dil modeli yalnızca kuralların boş bıraktığı yerleri dolduruyor. |
| **S17** | 2:00 | 7 | Bilgi metinde yoksa hiçbir değer üretilmiyor. |
| **S18** | 2:06 | 8 | Ve şu: yayımladığımız her sayı, onu üreten komutun çıktısıyla eşleşmek zorunda. |
| **S19** | 2:13 | 8 | Ayrışırsa yapı kırmızı yanıyor. Ölçüm dürüstlüğü bizde bir iddia değil, bir kapı. |
| **S20** | 2:24 | 9 | Tek bir parlak yüzde vermiyoruz — çünkü bir alanı kaçırmak ile uydurmak aynı hata değil. |

### Kayıt notları

- **S4** üç ayrı ifade — aralarına yarım saniye boşluk bırak, vurgu ifadelerin
  farklılığında.
- **S9 ve S10** videonun ilk dönüm noktası. S9'dan sonra **bir saniye sus**;
  ekrandaki reddetme işareti tek başına görünsün.
- **S11** bir soru. Yukarı tonlamayla oku ve arkasından **1,5 saniye boşluk**
  bırak — sahne 5 burada başlıyor.
- **S13** videonun teknik olarak en yoğun cümlesi. Yavaş oku.
- **S19** kapanış vurgusu. "Bir kapı" ifadesinde dur.
- **S20** son cümle. Acele etme; son kelimeden sonra 2 saniye sessizlik kalsın.

### Yeniden kayıt için

Her cümle ayrı bir ses dosyası olarak kaydedilirse (`S01.wav` … `S20.wav`),
zaman kodları sabit kaldığı için kurgu bozulmaz. Bir cümleyi yeniden okumak,
videonun geri kalanını etkilemez. **Geçici yapay ses kullanılacaksa da aynı
dosyalama uygulanmalı** — sonradan tek tek değiştirilebilsin.

---

## K) 1 dakikalık kesit (şartname s.19)

Ayrı çekim **yok**. Uzun videodan üç sahne kesilir:

| Kaynak sahne | Süre | Neden bu |
|---|---|---|
| Sahne 1 (kısaltılmış) | 6 sn | Ne olduğunu söyler |
| Sahne 4 | 24 sn | Gerçekten çalıştığını gösterir |
| Sahne 5 | 20 sn | Farkı gösterir — WOW anı |
| Sahne 9 | 10 sn | Kapanış |

Seslendirme: **S1, S2, S7, S8, S9, S10, S11, S12, S13, S20**. Diğerleri
düşer; kalan cümleler arasındaki boşluklar kısaltılarak 60 saniyeye oturur.

---

## Y) Yapılmayacaklar

Bunlar bilerek dışarıda bırakıldı; kurgu masasında "eklesek mi" diye
tartışılmasın diye yazılıyor:

- **Arka plan müziği yok.** Konuşma ve arayüz sesleri yeterli; müzik, ölçüm
  anlatısının ciddiyetini düşürür.
- **Sahte ekran, mockup, "kavramsal" animasyon yok.** Her kare çalışan
  sistemden.
- **Rakip adı geçmez.** Karşılaştırma yalnızca metodolojik bir soru olarak
  sunumda yapılır (bkz. `sunum-ve-demo-plani.md` §D3).
- **Ölçülmemiş sayı görünmez.** Ekranda beliren her rakam
  `scripts/kanit_tazeligi` kapısından geçmiş olmalı.
- **Hızlandırılmış çekim yok.** Sistem gerçekten ne kadar sürüyorsa o kadar
  görünür.

---

## Sources
- `docs/rapor/sunum-ve-demo-plani.md` — §A çekim listesi, §D2 jüri soruları
- `docs/sunum/anatolia-ai-sunum.html` — açılış/kapanış kartları
- `docs/OFFLINE-KANIT.md` — 14/14 ağsız kanıt
- `scripts/kanit_tazeligi.py` — sahne 8'de canlı koşan kapı

## Related
- [[sunum-ve-demo-plani]] — 4 dakikalık jüri sunumunun slayt iskeleti
- [[SARTNAME-UYUM]] — video kalemlerinin teslim durumu (8 · 9)

---

## ✅ Video ÜRETİLDİ — 2026-08-16

Bu belge bir plandı; artık üretilmiş videonun künyesi. Yukarıdaki sahne
planı korunuyor (kurgu ona göre yapıldı), aşağıda ölçülen sonuç var.

| | Dosya | Süre | Boyut |
|---|---|---|---|
| Tam sürüm | `anatolia-ai-demo.mp4` | **1:55** | 17 MB |
| Kısa kesit | `anatolia-ai-demo-1dk.mp4` | **0:59** | 11 MB |

1920×1080 · 30 fps · H.264 · AAC 48 kHz.

### Nasıl üretildi — ve nasıl yeniden üretilir

Hiçbir kare elle çekilmedi; hat tamamen betikli ve `docs/sunum/video-uretim/`
altında duruyor:

| Aşama | Araç | Betik |
|---|---|---|
| Gerçek arayüz çekimi | Playwright (video kaydı) | `cek.py` |
| Terminal sahnesi | VHS | `terminal.tape` |
| Başlık kartları | Playwright ekran görüntüsü | `kart.py` |
| Türkçe seslendirme | macOS `say -v Yelda` | `ses.py` → `ses.json` |
| Kurgu | ffmpeg (xfade + adelay/amix) | `kurgu.py` |

```bash
# ön koşul: API :8000 ve arayüz :3000 ayakta
python docs/sunum/video-uretim/cek.py          # klipler
vhs    docs/sunum/video-uretim/terminal.tape   # terminal
python docs/sunum/video-uretim/kart.py         # kartlar
python docs/sunum/video-uretim/ses.py          # seslendirme + süre ölçümü
python docs/sunum/video-uretim/kurgu.py        # tam sürüm
python docs/sunum/video-uretim/kurgu.py --kisa # 1 dk kesit
```

### İki tasarım kararı

**İmleç enjekte edildi.** Playwright videoya imleci basmaz; sahne ölü
görünürdü. Sayfaya saf CSS ile çizilen bir imleç enjekte ediliyor ve
tıklamadan önce hedefe yumuşakça sürülüyor. Kayıt hâlâ gerçek arayüzün
gerçek davranışı — yalnız imleç görünür oldu.

**Ses önce, kurgu sonra.** `ses.py` her cümlenin GERÇEK süresini ölçüp
`ses.json`a yazıyor; `kurgu.py` segment uzunluklarını o ölçüme göre
kuruyor. Sonuç: bir cümleyi kendi sesinle yeniden kaydettiğinde yalnız o
dosyayı değiştirmen yeterli, kurgu bozulmaz.

### Çekim sırasında düzeltilen iki kusur

İlk kurguda iki sahne yanlış zaman penceresini yakaladı ve bu **kontak
baskısında görüldü, tahmin edilmedi**:

- **Sohbet** segmenti boş sohbeti gösteriyordu; cevabın geldiği pencere
  15,5–25,0 sn imiş. Düzeltildi.
- **Çelişki tespiti** hâlâ "getiriliyor" iskeletindeydi: tarama 1.782
  belgeyi geziyor ve 14 saniyede bitmiyor. Sabit bekleme yerine panelin
  yüklenmesi **koşula bağlandı** (`wait_for_function`), sahne yeniden
  çekildi. Sonuç: 13/1.782 belgede çelişki, 15 bulgu.

### ⚠️ Seslendirme geçicidir

Ses şu an macOS'un Türkçe sesi (Yelda). 20 cümle `ses/S01.wav` …
`ses/S20.wav` olarak AYRI dosyalar. Kendi sesinle kaydederken aynı
numaralandırmayı koru; `kurgu.py`yi yeniden koşmak yeterli.

---

## ✅ İkinci sürüm: KAPSAMLI, yalnız gerçek arayüz — 2026-08-16

Yukarıdaki ilk sürüm başlık kartlarıyla anlatıyordu. Bu sürümde **tek bir
kart, mockup veya çizim yok**: her kare sistemin kendi arayüzünden, gerçek
veriyle, gerçek yükleme süreleriyle çekildi. Karşılığında ilk sürümün
göstermediği yedi ekran daha giriyor.

| | Dosya | Süre | Boyut |
|---|---|---|---|
| Tam sürüm | `anatolia-ai-demo-kapsamli.mp4` | **3:04** | 28 MB |
| Kısa kesit | `anatolia-ai-demo-kapsamli-1dk.mp4` | **0:55** | 9,5 MB |

1920×1080 · 30 fps · H.264 · AAC 48 kHz mono. Şartname s.14 tavanı (5 dk) ve
s.19 kısa kesit koşulu — ikisi de karşılanıyor (`SARTNAME-UYUM.md` satır 68'de
kayıtlı süre çelişkisi).

### Kapsanan on iki ekran

| # | Sahne | Ne kanıtlıyor |
|---|---|---|
| 1 | Pano + tema geçişi (açık ↔ koyu) | ürün gerçek, iki temada da çalışıyor |
| 2 | Karşılaştırma cetveli (alan değiştirme) | 12/12 alan, adil kıyas kapısı |
| 3 | Isı haritası | hangi banka hangi alanı yayımlıyor — boşluklar dâhil |
| 4 | En avantajlı | yalnız normalize alan üzerinden sıralama |
| 5 | Banka sayfası | tek kurumun tüm kampanyaları + toplanma tarihi |
| 6 | Banka içi delta | kurumun kendi içindeki tutarsızlık |
| 7 | Çelişki tespiti | §18/2 yenilik hedefi, korpusun tamamında tarama |
| 8 | Jüri denetim paneli | değer → karakter aralığı → kaynak cümle |
| 9 | Canlı çıkarım | önceden hazırlanmış cevap değil |
| 10 | Chatbot | hibrit yönlendirme (text-to-SQL ↔ RAG), belgeye bağlı cevap |
| 11 | Veri tazeleme | config-driven banka onboarding (§18/3) |
| 12 | İşlem günlüğü | her koşu kayıtlı |

### Üretim hattı

| Aşama | Araç | Betik |
|---|---|---|
| Gerçek arayüz çekimi (12 sahne) | Playwright | `cek-kapsamli.py` |
| Türkçe seslendirme (28 cümle) | `edge-tts` · `tr-TR-AhmetNeural` `+14%` | `ses-kapsamli.py` → `ses-kapsamli.json` |
| Kurgu | ffmpeg (xfade + adelay/amix) | `kurgu-kapsamli.py` |

```bash
# ön koşul: API :8000 ve arayüz :3000 ayakta
python docs/sunum/video-uretim/cek-kapsamli.py            # 12 klip
python docs/sunum/video-uretim/ses-kapsamli.py            # ses + süre ölçümü
python docs/sunum/video-uretim/kurgu-kapsamli.py          # 3:04
python docs/sunum/video-uretim/kurgu-kapsamli.py --kisa   # 0:55
```

### Çekim sırasında düzeltilen üç kusur

Yine **tahminle değil, kare bakarak** yakalandı:

1. **`Açık` düğmesi yanlış öğeye düşüyordu.** `has_text="Açık"` alt dize
   eşleştirdiği için `Jüri modu: açık` düğmesini yakalıyordu; tam eşleşmeye
   (`get_by_role(..., exact=True)`) çevrildi.
2. **Beş sahne, seslendirmenin gerektirdiği pencereden kısaydı.** Donmuş kare
   basmak yerine o sahneler daha uzun tutuşlarla **yeniden çekildi**.
3. **Sekme turlarında sayfa yüklemesi klibin baştaki ~6 saniyesini yiyordu**;
   sabit başlangıç yükleme ekranını kadraja sokuyordu. Kurgu penceresi artık
   klibin **sonuna yaslanıyor** (`baslangic=None`), böylece içeriğin yüklü
   olduğu garanti.

### ⚠️ İki dürüstlük notu

**Seslendirme yine geçici.** Ses Microsoft'un Türkçe nöral sesi
(`tr-TR-AhmetNeural`, %14 hızlandırılmış). 28 cümle `ses2/01.mp3` …
`ses2/28.mp3` olarak AYRI dosyalar; kendi sesinle kaydederken numaralandırmayı
koru, `kurgu-kapsamli.py` yeniden koşmak yeterli.

**`edge-tts` internet ister.** Bu yalnız videonun ÜRETİMİNDE geçerlidir.
Teslim edilen sistemin offline kısıtıyla ilgisi yoktur: video bir sunum
malzemesidir, ürünün bir parçası değildir ve `docker-compose up` yolunda
`edge-tts` hiç bulunmaz (`requirements.txt`'te yok). Kendi sesinle
kaydedildiğinde hattan tamamen çıkar.

---

## ✅ 1 dakikalık kesit: sekiz ekran + Ayarlar kapanışı — 2026-08-16

`anatolia-ai-demo-1dk-sekiz-ekran.mp4` — **56 sn** · 9,1 MB · 1920×1080 · 30 fps.

Bu kesit kapsamlı sürümün bir alt kümesi **değil**, kendi anlatısı olan ayrı bir
kurgu. Sekiz ekran, sekiz cümle, sahne başına ~7 saniye:

| # | Ekran | Cümlenin söylediği |
|---|---|---|
| 1 | Karşılaştırma | 10 banka · 1.782 belge, tek cetvel |
| 2 | En Avantajlı | yalnız aynı birime normalize alanlar sıralanıyor |
| 3 | Banka Sayfası | son toplama tarihi · kaynak adresi · 12 alanın kaçı dolu |
| 4 | Çelişki Tespiti | "masrafsız" deyip ücret alan kampanyalar |
| 5 | Chatbot | sayısal soru → yapısal sorgu, koşul sorusu → getirimli üretim |
| 6 | Veri Tazeleme | her banka tek tıkla, robots.txt ve hız sınırıyla |
| 7 | Jüri Audit Paneli | her değer, çıkarıldığı cümlenin karakter aralığına bağlı |
| 8 | **Ayarlar** | veri ekleme uçlarının şeması hazır — iş birliğinde açılacak |

### Kapanış neden bu cümle

Ayarlar sekmesi bir ayar ekranı değil, ekranın kendi deyimiyle **bir sözleşme
belgesi**: `POST /admin/banks`, `POST /admin/banks/{slug}/campaigns` ve
`POST /admin/banks/{slug}/products` uçlarının gövde şemaları **sunucudan
okunuyor** ve bugün **501** dönüyor. Doldurulabilen tek bir alan bilerek yok —
çünkü doldurulabilen bir form, doldurulunca çalışacağını vaat eder.

Video bu yüzden *"uçlar çalışıyor"* demiyor; *"şeması hazır, bankalarla iş
birliği kurulup API verildiğinde sistem açılmaya hazır bekliyor"* diyor. Ekran
ne söylüyorsa seslendirme onu söylüyor.

### Kare denetiminde düzeltilen iki şey

Kurgudan önce sekiz sahnenin sekizi de kare kare bakıldı; ikisi ilk seferde
tutmadı ve **cümle değil, önce pencere** düzeltildi:

- **En Avantajlı** penceresi sona yaslanınca sıralamanın *"kıyas dışı / skor
  yok"* kuyruğuna denk geliyordu. Pencere sıralamanın **tepesine** taşındı
  (1. sıra Kuveyt Türk, bileşik skor 1,00).
- **Banka Sayfası** ile **Veri Tazeleme** cümleleri ekranın göstermediği şeyi
  söylüyordu (*"bütün kampanyalarını getiriyor"*, *"yeni bankayı tek satırla
  sokuyor"*). Ekranlar aslında kurum künyesi + veri kapsamı ve mevcut bankaların
  yeniden toplanmasını gösteriyor. **Cümleler ekrana uyduruldu, ekran cümleye
  değil.**

### Üretim

```bash
python docs/sunum/video-uretim/cek-kapsamli.py ayarlar   # eksik tek sahne
python docs/sunum/video-uretim/ses-1dk.py                # 8 cümle + süre ölçümü
python docs/sunum/video-uretim/kurgu-1dk.py              # 56 sn
```

`kurgu-1dk.py` süre 60 saniyeyi aşarsa çıktıya **⚠ 60 sn AŞILDI** basar; sessizce
uzun bir video üretmez.

---

## ✅ 1 dk kesiti, ikinci geçiş: dolu veri + hızlandırma — 2026-08-16

Aynı sekiz ekran, ama **korpusun dolu kesiti** ve sayfa başına iki-üç cümle.
`anatolia-ai-demo-1dk-sekiz-ekran.mp4` — **59 sn** · 9,5 MB · 13 cümle.

### Neden gerekti: ilk geçiş korpusun EN BOŞ kesitini gösteriyordu

Arayüzün varsayılanları demo için ters çalışıyor. `sqlite3 data/demo.db`
ölçümü:

| Ekran | Varsayılan | Kaç veri | Seçilen | Kaç veri |
|---|---|---|---|---|
| Banka Sayfası | Adil Katılım | 6 belge · 12 alandan **2**'si | **Kuveyt Türk** | 537 belge · 12 alandan **12**'si · 1.703 değer |
| Karşılaştırma | `kar_payi_orani` | 70 belge · 3/10 banka | **`masraf_durumu`** | 498 belge · **9/10 banka** |
| En Avantajlı | Alışveriş Puanı | 1 sıralanabilir | **Yatırım Ürünü** | **14** sıralanabilir |

Adil Katılım korpusun **en boş** bankası; ilk kesit tam da onu açıyordu.
Veri uydurulmadı — var olanın en dolusu seçildi ve seçim gerekçesi ölçümle
birlikte `cek-dolu-veri.py` başlığında yazılı.

**En Avantajlı'da ayrı bir tür seçildi.** "En çok kampanya" ile "en çok
**sıralanabilir** kampanya" aynı tür değil: sıralama bileşik skor istediği için
Kart 446 kampanyanın yalnız 4'ünü sıralayabiliyor. Arayüzden tür tür sayıldı —
Yatırım Ürünü 14 · Konut 9 · Taşıt 9 · İhtiyaç 7 · Kart 4 · Yeni Müşteri 0.

### İki ayrı hızlandırma

| Ne | Nasıl | Ne kazandırıyor |
|---|---|---|
| Ses | `edge-tts` `+38%` | aynı saniyede daha çok cümle (8 → 13) |
| Görüntü | `setpts=PTS/1.4` | aynı saniyede %40 daha çok ekran |

Görüntü hızlandırması kare atlamıyor: her sahnede kaynaktan `süre × 1,4`
kadar pencere alınıp `süre`ye sıkıştırılıyor. Yani sahne daha çok kaydırma ve
tıklama gösteriyor, daha az kare değil.

`kurgu-1dk.py` süreyi 60 saniyelik tavana karşı ölçüyor ve aşarsa
**⚠ TAVAN AŞILDI** basıyor.

### Kare denetiminde düzeltilen iki şey

- **Açılış karesi alan geçişinin iskelet anına denk geliyordu** — başlık hâlâ
  önceki alanın `6/10`'unu, satırlar yükleme çizgilerini gösteriyordu. `cetvel3`
  klibine kuyruk eklenip pencere oturmuş tabloya kaydırıldı.
- **Cümle sırası ekran sırasıyla tersti**: pencere klibin sonuna yaslandığı
  için önce masraf tablosu, sonra kanıt tablosu görünüyor; ama "9/10 banka"
  iddiası kanıt tablosunun üstüne düşüyordu. Cümleler ekran sırasına dizildi.

### Üretim

```bash
python docs/sunum/video-uretim/cek-dolu-veri.py   # cetvel3 · avantaj3 · banka3
python docs/sunum/video-uretim/cek-kapsamli.py \
       celiski sohbet tazele kanit ayarlar        # kalan beş sahne
python docs/sunum/video-uretim/ses-1dk.py         # 13 cümle + süre ölçümü
python docs/sunum/video-uretim/kurgu-1dk.py       # 59 sn
```
