# Demo Videosu — üretim hattı

TEKNOFEST TYDA 2. Senaryo teslim kalemi: **en fazla 5 dakikalık demo videosu**.
Aynı hattan iki sürüm çıkıyor:

| Sürüm | Dosya | Süre | İşi |
|---|---|---|---|
| Tam | `cikti/anatolia-ai-demo.mp4` | **4 dk 54 sn** | Şartname teslimi: her ekranı anlatarak gösterir |
| Kısa | `cikti/anatolia-ai-demo-60sn.mp4` | **1 dk 02 sn** | Tanıtım: on iki ekranı etiketleyip hızlı geçer |


İkisi de 1920×1080, 30 fps, H.264 + AAC stereo, −16 LUFS. Altyazılar:
`cikti/anatolia-ai-demo.tr.srt`, `cikti/anatolia-ai-demo-60sn.tr.srt`.

Video **kayıttan oynatılan bir ekran videosu değil**: her panel sahnesi, o an
ayakta olan sistemin üzerinde Playwright ile gerçekten koşturuluyor. Canlı
çıkarım sahnesinde yerel dil modeli gerçekten çağrılıyor.

## Şartname kapsaması — tam sürüm (4:54)

| İstenen | Nerede |
|---|---|
| Kullanıcı arayüzü + dashboard | 00:19 – 00:37 |
| Metin girdisi verilmesi | 00:37 – 01:11 |
| Modelin ürettiği yapılandırılmış çıktı | 00:55 – 01:11 |
| Zor vaka / altın küme karşılaştırması | 01:11 – 01:36 |
| Kanıt zinciri (kaynak span + güven) | 01:36 – 01:54 |
| Karşılaştırma sonuçları + ürün tablosu (s.12) | 01:54 – 02:19 |
| Isı haritası · En Avantajlı · Banka sayfası · Delta | 02:19 – 02:51 |
| Çelişki tespiti | 02:51 – 03:12 |
| Chatbot | 03:12 – 03:35 |
| Veri tazeleme · İşlem günlüğü · Ayarlar | 03:35 – 03:52 |
| Mimari + ölçüm sonuçları | 03:52 – 04:20 |
| Gelecek vizyonu | 04:20 – 04:46 |
| Kapanış | 04:46 – 04:53 |

## Kısa sürüm (1:02) — her ekran ayrı sahne, iki sütunlu kadraj

Tam sürümde üç ekran tek sahnede geçiyor (En Avantajlı → Banka → Delta,
Tazeleme → Günlük → Ayarlar). Kısa sürümde **her ekranın kendi sahnesi, kendi
etiketi ve kendi cümlesi var** — on iki panel ekranı da tek tek görünür.

Altmış saniyede özelliğin ANLAŞILMASI için üç kanal aynı anda çalışır:

1. **Anlatım** — ne yaptığını söyler.
2. **İki sütunlu kadraj** — panel uzun bir pencerede (1280×2304) kaydedilir,
   montaj kareyi ortadan bölüp yan yana koyar: sol sütun sayfanın üstü, sağ
   sütun hemen devamı. 1080p'de tek sütun ekranın ancak yarısını taşıyordu ve
   üç saniyede kaydırarak yetişmek mümkün değildi.
3. **Alt bant** — özelliğin adı ve altında sayılarla künyesi ekranda kalır
   ("12 alan · güven skoru · üreten katman · karakter aralığı").

| Sahne | Etiket | Zaman |
|---|---|---|
| Açılış kartı | — | 00:00 – 00:05 |
| Karşılaştırma | PANEL · Dashboard, canlı künye | 00:05 – 00:09 |
| Canlı çıkarım (kutuya yazma) | ANA ÖZELLİK · Metin girdisi | 00:09 – 00:13 |
| Canlı çıkarım (alan tablosu) | ANA ÖZELLİK · Yapılandırılmış çıktı | 00:13 – 00:17 |
| Zor vaka tezgâhı | YENİLİKÇİ · Altın küme | 00:17 – 00:21 |
| Jüri audit paneli | YENİLİKÇİ · Kanıt zinciri | 00:21 – 00:24 |
| Karşılaştırma (vade · Finansman) | ANA ÖZELLİK · Bankalar arası karşılaştırma | 00:24 – 00:27 |
| Ürün tablosu (Kart) | ŞARTNAME s.12 | 00:27 – 00:31 |
| Isı haritası (vade, 47/99 hücre) | YENİLİKÇİ · Kapsama | 00:31 – 00:34 |
| En Avantajlı (Kart) | ANA ÖZELLİK · Bileşik skor | 00:34 – 00:38 |
| Banka sayfası **+** banka içi delta | BANKA EKRANI (iki ekran yan yana) | 00:38 – 00:42 |
| Çelişki tespiti | YENİLİKÇİ | 00:42 – 00:46 |
| Chatbot (yapısal sorgu **+** RAG) | ANA ÖZELLİK | 00:46 – 00:52 |
| Tazeleme · günlük · ayarlar | OPERASYON | 00:52 – 00:56 |
| Gelecek vizyonu kartı | — | 00:56 – 00:59 |
| Kapanış kartı | — | 00:59 – 01:02 |

### Ekranlardaki veriler ölçülerek seçildi

Boş bir tablo sistemin çalışmadığını değil, o kesişimde belge olmadığını
gösterir — ama üç saniyelik bir sahnede kimse bu ayrımı yapmaz. `/compare` ve
`/stats` uçları taranıp her ekran korpusun **en dolu** kesişimine ayarlandı:

| Ekran | Seçim | Neden |
|---|---|---|
| Karşılaştırma, panel açılışı, ısı haritası | `vade (ay)` | 9 bankada dolu, 9'u da kıyaslanabilir; kâr payı × Konut Finansmanı yalnız 2 bankaydı |
| Ürün tablosu, En Avantajlı, delta | `Kart` türü | 9 bankada dolu (28/45 hücre) |
| Banka sayfası, kanıt zinciri | Kuveyt Türk | 885 belge, 12 alanın 12'si dolu; varsayılan banka 11 belgeyle boş ekran veriyordu |
| Isı haritası alanı | `vade (ay)` | «Kampanya Süresi» 1.179 kayıtla dolu görünüyor ama haritada 0/99 hücre veriyor — harita kıyaslanabilir değerleri sayıyor, tarih alanı sıralamaya girmiyor |

## Yeniden üretme

Önce sistem ayakta olmalı — sahneler canlı panelden çekiliyor:

```bash
cd app && LLM=1 make baslat        # panel :3000, API :8000, yerel model açık
```

Tam sürüm (hepsi `app/.venv` yorumlayıcısıyla; `edge-tts` ve `ffmpeg` gerekir):

```bash
cd app
./.venv/bin/python ../demo-video/uret_ses.py     # 1) anlatım seslerini üret + süre ölç
./.venv/bin/python ../demo-video/uret_kart.py    # 2) kart sahnelerini PNG'ye bas
./.venv/bin/python ../demo-video/uret_sahne.py   # 3) panel sahnelerini kaydet (~6 dk)
./.venv/bin/python ../demo-video/montaj.py       # 4) birleştir → cikti/
```

Kısa sürüm — kendi senaryosu, kendi kayıtları, kendi etiketleri:

```bash
cd app
./.venv/bin/python ../demo-video/uret_ses.py senaryo-60.json   # ses-60/ + sesler-60.json
./.venv/bin/python ../demo-video/uret_kart.py vizyon-60        # kısa vizyon kartı
./.venv/bin/python ../demo-video/uret_sahne60.py               # sahne-60/ (~3 dk)
./.venv/bin/python ../demo-video/uret_etiket60.py              # etiket-60/ şeritleri
./.venv/bin/python ../demo-video/montaj60.py                   # → 60sn.mp4
```

Tek bir sahneyi yeniden çekmek için adını ver (iki sürümde de çalışır):

```bash
./.venv/bin/python ../demo-video/uret_sahne60.py 07-banka 04-hesap-makinesi
```

**Sıra bağlayıcıdır.** `uret_ses.py` her sahnenin süresini `sesler*.json`'a
yazar; hem sahne kaydı hem montaj bu süreleri okur. Metin değişip ses yeniden
üretilmezse sahneler eski süreye göre hizalanır.

## Dosyalar

| Yol | İçerik | İzleniyor mu |
|---|---|---|
| `senaryo.json` | Tam sürüm: sahne sırası, anlatım, ses/video ayarı | ✅ tek doğruluk kaynağı |
| `senaryo-60.json` | Kısa sürüm: sahneler + kesit ucu, hız, etiket metinleri | ✅ tek doğruluk kaynağı |
| `kart/*.html`, `kart/ortak.css` | Açılış / mimari / vizyon / vizyon-60 / kapanış kartları | ✅ |
| `sahne_ortak.py` | İki kayıt betiğinin paylaştığı tarayıcı yardımcıları | ✅ |
| `uret_ses.py` | edge-tts (Bing seslendirme motoru) ile anlatım + süre ölçümü | ✅ |
| `uret_kart.py` | Kart HTML → 1920×1080 PNG | ✅ |
| `uret_sahne.py` / `uret_sahne60.py` | Playwright ile canlı panel kayıtları | ✅ |
| `uret_etiket60.py` | Kısa sürümün alt bant etiketleri (şeffaf PNG) | ✅ |
| `montaj.py` / `montaj60.py` | Süre hizalama + geçiş + ses karışımı + SRT | ✅ |
| `anlatim*/` | Sahne başına anlatım metni (seslendirme senaryosu) | ✅ |
| `ses*/`, `kart/*.png`, `sahne*/`, `etiket-60/`, `cikti/`, `sesler*.json` | Türetilmiş | ❌ `.gitignore` |

## Kararlar

**Ses: `tr-TR-AhmetNeural`.** Tam sürümde hız +%11, kısa sürümde +%42. Tam
sürümde hız pazarlık sonucu: metinler +%8'de 5 dk 2 sn tutuyordu, bir kademe
artırmak 4 dk 54 sn'ye indirdi. Kısa sürümde cümleler özelliğin künyesini
taşıyacak kadar dolu ama tek nefeslik yazıldı; hız oradaki bütçenin
kendisidir — aynı metinler +%36'da 69,6 saniye, +%42'de 61,5 saniye tutuyor.

**Süreyi ses belirler.** Sahneler bilerek anlatımdan uzun kaydedilir; montaj
fazlalığı hızlandırma ve sahnenin **başından** kırpma ile alır. Sondan
kırpmak, çıkarım sonuçlarının tam da göründüğü anı keserdi.

**Kısa sürümde hız sahne başına seçilir.** Tek bir üst sınır işe yaramadı:
sonuç tablosu okunacak sahneler 1,3–1,5× civarında kalır, tek sahnede üç ekran
gezen operasyon turu 2,4× koşar. Değerler `senaryo-60.json` içindeki `hiz`
alanında; `yer` alanı kesitin kaydın hangi ucundan alınacağını söyler.
Çıkarımın sürdüğü yirmi saniye kısa sürüme HİÇ girmiyor: aynı kaydın başı
"metin girdisi", sonu "yapılandırılmış çıktı" sahnesi oluyor.

**İki akraba ekran tek sahnede (`duzen: yan`).** Banka künyesi ile banka içi
delta iki ayrı kayıttan gelip yan yana konuyor. On iki ekranı altmış saniyeye
sığdırırken anlatımı telgrafa çevirmemenin yolu buydu: iki sahne yerine bir
sahne, ama iki ekran da görünüyor.

**Chatbot sahnesinde soru sırası bağlayıcı.** Koşul sorusu ÖNCE sorulur:
bağlamı boş bir turda belge erişimine (RAG) düşüyor. Ters sırada ikinci soru
önceki turun alanını (`vade_ay`) devralıyor — «Yeni konu» bile bu devri
kesmiyor — ve o da yapısal sorguya gidiyor; ekranda aynı rozet iki kez
çıkıyor, oysa sahnenin iddiası iki AYRI yol. Sayısal soru bağlam devralsa da
yapısal kaldığı için bu sırada ikisi de garanti görünür.

**Etiket köşede kutu değil, alt bant.** İlk tur sol alt köşeye bir kutu
koydu ve tam da okunması gereken yeri kapattı (çıkarım künyesi, zor vaka
sayımları, banka sayfasının bölüm başlığı). Şerit artık alt kenarda tam
genişlikte ve iki satırlı; montaj panel görüntüsünü 963 piksele indirip üste
yaslıyor, kalan 117 piksel bant oluyor — panelden hiçbir piksel örtülmüyor.
İkinci satır (özelliğin sayılarla künyesi) üç saniyelik bir sahnede anlatımın
söylemeye vakit bulamadığını taşıyor.

**Kadrajlar elle doğrulandı.** Kayıt betiği bir bölüme "kaydır" dediğinde
`scroll_into_view_if_needed` hedefi ekranın en ALTINA yapıştırıyor; üç sahnede
gösterilecek blok kadrajın dışında kaldı (metin kutusu kenarda, zor vaka
sayımları görünmüyor, banka sayfası delta bölümüne düşmüş). Her sahne
montajdan sonra kare kare kontrol edildi ve kaydırma payları buna göre ayarlandı.

**Sekme şeridi ARIA sekme deseni.** Panel içinde sekme değiştirmek için
`role="tab"` aranır (`app/web/app/components/ui/Tabs.tsx`). `button` rolüyle
arandığında sahne sessizce `goto` yedeğine düşüyor, sayfa yeniden yükleniyor
ve 3× hızlandırılmış kayıtta ekran "yükleniyor" iskeletine denk geliyordu.

**Kartlarda yazan her sayı ölçülmüştür.** `0,8228` / `0,7646` / `%3,36`
`app/README.md` "Ölçüm sonuçları" bölümünden; `2.729 belge · 11 banka`
canlı `/stats` ucundan (25 Ağustos'taki banka yeniden taramasından sonraki
değer — v1'de `2.708` yazıyordu, kart o taramadan sonra yeniden basıldı).
Ablasyon anlatısı da (yerel modelin kural katmanını geçemediği) tam sürümde
dürüstçe söyleniyor — gizlenmiyor.

**Serbest metin örneği sentetiktir**, korpustan alınmamıştır: "önceden
hazırlanmış bir belgeyi tanıyor" itirazını kapatmak için. İçindeki beş alan
doludur, taksit sayısı bilerek yoktur — boş bırakılan alanın ekranda nasıl
göründüğü de gösterilmiş olur.
