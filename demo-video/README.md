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

## Kısa sürüm (1:02) — her ekran ayrı sahne

Tam sürümde üç ekran tek sahnede geçiyor (En Avantajlı → Banka → Delta,
Tazeleme → Günlük → Ayarlar). Kısa sürümde **her ekranın kendi sahnesi, kendi
etiketi ve kendi cümlesi var** — on iki panel ekranı da tek tek görünür.

| Sahne | Etiket | Zaman |
|---|---|---|
| Açılış kartı | — | 00:00 – 00:06 |
| Karşılaştırma (üst künye) | PANEL · Dashboard | 00:06 – 00:09 |
| Canlı çıkarım (kutuya yazma) | ANA ÖZELLİK · Metin girdisi | 00:09 – 00:12 |
| Canlı çıkarım (alan tablosu) | ANA ÖZELLİK · Yapılandırılmış çıktı | 00:12 – 00:18 |
| Zor vaka tezgâhı | YENİLİKÇİ · Altın küme | 00:18 – 00:22 |
| Jüri audit paneli | YENİLİKÇİ · Kanıt zinciri | 00:22 – 00:25 |
| Karşılaştırma (sıralama) | ANA ÖZELLİK · Bankalar arası karşılaştırma | 00:25 – 00:29 |
| Ürün tablosu | ŞARTNAME s.12 | 00:29 – 00:32 |
| Isı haritası | YENİLİKÇİ · Kapsama | 00:32 – 00:35 |
| En Avantajlı | ANA ÖZELLİK · Bileşik skor | 00:35 – 00:38 |
| Banka sayfası | BANKA EKRANI | 00:38 – 00:41 |
| Banka içi delta | YENİLİKÇİ | 00:41 – 00:44 |
| Çelişki tespiti | YENİLİKÇİ | 00:44 – 00:47 |
| Chatbot | ANA ÖZELLİK · Hibrit yönlendirme | 00:47 – 00:51 |
| Tazeleme · günlük · ayarlar | OPERASYON | 00:51 – 00:54 |
| Gelecek vizyonu kartı | — | 00:54 – 00:59 |
| Kapanış kartı | — | 00:59 – 01:02 |

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
./.venv/bin/python ../demo-video/uret_sahne60.py 10-banka 14-operasyon
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

**Ses: `tr-TR-AhmetNeural`.** Tam sürümde hız +%11, kısa sürümde +%30. Tam
sürümde hız pazarlık sonucu: metinler +%8'de 5 dk 2 sn tutuyordu, bir kademe
artırmak 4 dk 54 sn'ye indirdi. Kısa sürümde on yedi sahne için tek nefeslik
cümleler yazıldı ve hız bir kademe daha yükseltildi.

**Süreyi ses belirler.** Sahneler bilerek anlatımdan uzun kaydedilir; montaj
fazlalığı hızlandırma ve sahnenin **başından** kırpma ile alır. Sondan
kırpmak, çıkarım sonuçlarının tam da göründüğü anı keserdi.

**Kısa sürümde hız sahne başına seçilir.** Tek bir üst sınır işe yaramadı:
sonuç tablosu okunacak sahneler 1,3–1,5× civarında kalır, tek sahnede üç ekran
gezen operasyon turu 3× koşar. Değerler `senaryo-60.json` içindeki `hiz`
alanında; `yer` alanı kesitin kaydın hangi ucundan alınacağını söyler.
Çıkarımın sürdüğü yirmi saniye kısa sürüme HİÇ girmiyor: aynı kaydın başı
"metin girdisi", sonu "yapılandırılmış çıktı" sahnesi oluyor.

**Etiket köşede kutu değil, alt bant.** İlk tur sol alt köşeye bir kutu
koydu ve tam da okunması gereken yeri kapattı (çıkarım künyesi, zor vaka
sayımları, banka sayfasının bölüm başlığı). Şerit artık alt kenarda tam
genişlikte; montaj panel görüntüsünü 1768×994'e indirip üste yaslıyor, yani
panelden hiçbir piksel örtülmüyor.

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
`app/README.md` "Ölçüm sonuçları" bölümünden; `2.708 belge · 11 banka`
canlı `/stats` ucundan. Ablasyon anlatısı da (yerel modelin kural katmanını
geçemediği) tam sürümde dürüstçe söyleniyor — gizlenmiyor.

**Serbest metin örneği sentetiktir**, korpustan alınmamıştır: "önceden
hazırlanmış bir belgeyi tanıyor" itirazını kapatmak için. İçindeki beş alan
doludur, taksit sayısı bilerek yoktur — boş bırakılan alanın ekranda nasıl
göründüğü de gösterilmiş olur.
