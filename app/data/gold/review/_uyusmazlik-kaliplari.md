# Uyuşmazlık Kalıpları — kalan 123 satırın kalıba indirgenmesi

> **Amaç tek tek çözmek değil.** Kalibrasyon yeniden etiketlenmeyecek; bu
> satırların değeri, aynı hataların **round1'in 2.400 satırında** tekrarlanmasını
> engellemekte. Her kalıp: kaç satırı açıklıyor · belgede aranacak somut kanıt ·
> doğru karar · yanlış karar · round1'de nasıl önlenir.
>
> Ölçüldü: 2026-08-09 · κ 0,302 · 123 uyuşmazlık
> Kaynak: `round0_kalibrasyon_{A,B,C,D}.csv` + `belgeler/*.txt` (123/123 belge mevcut)
> Yöntem: her uyuşmazlığın belgesi açıldı ve okundu; sayılar ölçüldü.

---

## 0. Manşet — 123'ün %40'ı fikir ayrılığı DEĞİL

Her uyuşmazlıktaki dört değer `parse_gold_value`'dan geçirilip **kanonik
karşılıkları** karşılaştırıldı:

| | satır | pay |
|---|---:|---:|
| **SAHTE** — kanonik değer AYNI, yalnız etiket/biçim farklı | **49** | **%40** |
| GERÇEK — kanonik değer farklı, içerik tartışması | 53 | %43 |
| AYRIŞTIRILAMADI — biçim o kadar bozuk ki karşılaştırılamıyor | 21 | %17 |

```bash
# üreten ölçüm (scratch değil, yeniden koşulabilir mantık):
# her jeton parse_gold_value(field, jeton) ile kanonikleştirilir,
# küme boyu 1 ise uyuşmazlık SAHTEdir.
```

**49 satır ölçülen bir fikir ayrılığı değil, protokol artefaktıdır.** Aynı oran
round1'e taşınırsa 2.400 satırda **~960 sahte uyuşmazlık** üretir ve κ'yı
gerçekte olmadığı kadar kötü gösterir.

`_kalibrasyon-sonucu.md` "kalan 106'sı gerçek değer ayrışması" diyordu. Bu ölçüm
onu daraltıyor: **gerçek ayrışma 53.** Aradaki fark, hakemliğin `verdict`
sütununu düzeltip `gold_value`nun İÇERİĞİNE dokunmamasından geliyor.

---

## 1. ÇAPRAZ KALIPLAR — dört alan grubunda da tekrarlıyor

Bunlar en yüksek değerli kalıplar: tek bir kural dört alan grubunu birden
temizliyor.

### Ç1 · Onaylarken değeri tekrar yazmak → sahte `fix` — **~36 satır**

**Ayırt edici kanıt:** `verdict` hücresi BOŞ + `gold_value` hücresi
`model_value` ile **birebir aynı**.

Sistem bunu `fix` sayar (kılavuz §3.2) — yani anotatör "model doğru" demek
isterken **"model yanlış"** demiş olur ve modeli haksız yere yanlış gösterir.
Ölçülen dağılım: B 13 + 11 hücre, D 13, C 3 (alan gruplarına göre).

- **Doğru:** `verdict=ok`, `gold_value` **boş**.
- **Yanlış:** değeri teyit için tekrar yazmak.
- **round1'de önleme:** "Doğru değeri gold_value'ya yazmak ONAY DEĞİL,
  DÜZELTMEDİR." Bu cümle `_bicim-karti.md` §1'de var ama tuzak 1 olarak
  gömülü; kartın başına alınmalı.

### Ç2 · Aralık tek-değer alanına → ayrıştırıcı SESSİZCE yanlış ucu alır — **~24 satır**

En tehlikeli kalıp, çünkü **durmuyor**. Ölçülen sonuçlar:

| yazılan | ayrıştırıcının ürettiği | doğrusu (kart §3) |
|---|---|---|
| `"2 ile 3 taksit arasında"` | **23** | `3` |
| `"3_48"` | **348** | `48` |
| `"12ile 48 arasında değişiyor"` | **1248** | `48` |
| `"%20-%70"` | **`{"value": 20.0, "currency": "TRY"}`** | oran, tutar değil |
| `"2026-07-01 - 2026-07-31"` | `2026-07-01` (başlangıç) | `2026-07-31` |

Parasal alanlarda ölçüm: aralık yazılan **9 hücrenin 9'unda da** gold yanlış uca
düştü. Vade/taksitte 12 hücrenin 5'i derlemeyi durdurdu, 3'ü sessizce bozuldu,
4'ü **kazara** doğru çıktı — kazara, çünkü `normalize_term_months` yalnız
`vade_ay` için çağrılıyor ve regex "ay"a bitişik sayıyı yakalıyor. Aynı dize
`taksit_sayisi`'ne yazılınca derleme duruyor.

- **Doğru:** vade/taksit → **en büyük**; tutar → **üst sınır**; tarih →
  **bitiş**. Aralığın kendisi `note`'a (`aralik=1-36`).
- **round1'de önleme:** aralık gördüğün an İKİ hücre doldur. Kart §3-1/2/4.

### Ç3 · `gold_value`ya belgenin KONUSUNU yazmak — **~15 satır**

**Ayırt edici kanıt:** `gold_value` bir DEĞER değil, belgenin ne hakkında
olduğunu anlatan bir isim tamlaması — `konut finansmanı`, `katılma hesapları`,
`Finansman hesaplama aracı`, `Leasing Süreci ve Hesaplama Aracı`.

Neredeyse tamamı D'de (`kampanya_kosullari` 6 + `campaign_type` 1 lint hatası;
kalan satırlar `ok`/`absent` ile birleşince linter'a hiç görünmüyor). `absent`
ile birlikteyse `build_gold` değeri **sessizce atar**.

- **D'nin KARARI çoğunlukla doğru** — o belgeler gerçekten kampanya değil.
  Yanlış olan, gerekçeyi değer hücresine yazması.
- **round1'de önleme:** "`gold_value` alanın değeridir. Neden o kararı verdiğin
  `note`'a gider."

### Ç4 · Kampanya olmayan belgede alan aramak — **~14 satır**

**Ayırt edici kanıt (üç tanık, belgede aranabilir):**
1. **Navigasyon menüsü / kırıntı yolu:** "Ana Sayfa Kendim İçin Finansmanlar
   İhtiyaç Finansmanları **Konut Finansmanları Araç Finansmanları**" — kardeş
   menü öğeleri yan yana. Belge bir liste sayfasıdır.
2. **KVKK / çerez gövdesi:** "…otuz (30) gün içinde **ücretsiz** olarak
   sonuçlandırılmaktadır" — `ücretsiz` burada masraf bilgisi DEĞİLDİR.
3. **Kanun atfı:** "22/11/2001 tarihli ve **4721 sayılı** Türk Medeni Kanununun
   684 üncü maddesi" — buradaki tarih kampanya süresi DEĞİLDİR.

- **Doğru:** `absent` (kılavuz §3.3 — onaylanmış halüsinasyon, gold'un en
  değerli etiketi).
- **round1'de önleme:** değeri yazmadan önce "bu cümle ürünü mü anlatıyor,
  siteyi mi?" diye sor.

---

## 2. LİDERİN İKİ HİPOTEZİ — dürüst sonuç

Her ikisi de ölçüldü. Biri çürüdü, biri düzeltilerek doğrulandı.

### 2a · "taksit yok → yazılan sayı vadedir" — **ÇÜRÜDÜ (0/24 satır)**

Sözcüğün birebir yokluğu 9 `taksit_sayisi` uyuşmazlığının 2'sinde doğru, **ama o
iki satırda zaten uyuşmazlık yok** — dördü de `__YOK__` diyor. Kelime testi
kılavuz §4'e girdiği için 10 belgeyi önceden temizlemiş; geriye kalanlar
sözcüğün **var olduğu** belgeler.

**Genişletilmiş hâli 3 satır açıklıyor:** sözcük var ama hiçbir sayı ona *sayım*
olarak bağlanmıyor. Kanıt: belgede yalnız `Taksit No` / `Taksit Tutarı` /
`48 aya kadar taksitlendirme` geçiyor; `(\d+)\s*taksit` ve
`taksit sayısı…(\d+)` eşleşmesi **sıfır**.

> **Bu kalıptan gelen bir yan bulgu, iki yanlış öneriyi engelledi.** İlk üretilen
> `_oneriler.csv`'de `1- 36 Ay → 36` ve `12-48 → 48` önerileri vardı: aralığı
> doğru daraltıp **yanlış alana** yazıyorlardı (B aynı aralığı hem `vade_ay`
> hem `taksit_sayisi` hücresine kopyalamış). İki koruma eklendi ve testle
> kilitlendi — bkz. `_onarim-recetesi.md` §6.

### 2b · "kâr paylaşım oranı ≠ kâr payı oranı" — **DOĞRULANDI, dedektör DEĞİŞTİ**

Kalıp gerçek (2/8 `kar_payi_orani` satırı) ama **önerilen arama dizgisi
kullanılamaz**:

- `"kâr paylaşım oranı"` 8 belgenin 3'ünde geçiyor, **2'si sayfa gezinme
  menüsü** ("…Katılma Hesapları Kâr Payı Oranları Kâr Paylaşım Oranları
  Kıymetli Maden…"). Kural yapılsaydı iki DOĞRU satır haksız yere `absent`e
  dönerdi.
- **En güçlü vakayı kaçırıyor:** belge tamlamayı hiç kullanmadan
  *"Hesabın kâr payı oranı %40'a %60'dır"* diyor.

**Yerine ölçülen dedektör: "toplamı 100 eden iki yüzde + paylaşım fiili".**
Kanıt cümlesi: *"hesap sahibi ile kurum arasında %40'a %60 şeklinde
**paylaşılır**"*. Ölçüm: 8 belgede 2 isabet · **0 yanlış alarm**; tüm korpusta
3/3 kesinlik (40+60, 95/5, 85/15). Karşıt örnek: gerçek oran çiftleri asla 100
etmez (2,95 + 4,42 = 7,37).

- **Doğru:** `kar_payi_orani = absent` + `note: #terminoloji paylasim orani`
  (kart §3-7).
- Bir satırda **dördü birden** paylaşım oranını `kar_payi_orani`'ye yazdı —
  yani bu, oy çokluğuyla çözülemeyecek bir kalıp.

---

## 3. ALAN ÖZELİNDE KALIPLAR

### 3a · `campaign_type` + `hedef_kitle` (32 satır)

| Kalıp | satır | Ayırt edici kanıt | Doğru karar |
|---|---:|---|---|
| 8 türe sığmayan ürün adı yazıldı | 4 | `Güneş Katılma Hesabı`, `Leasing`, `Hediye kampanyası` | kart §3-8: katılma/altın/yatırım → `Yatırım Ürünü`; leasing → `Finansman` |
| Kart/kanal kısıtı segment sanıldı (KİM–NE testi) | 4 | "…kartlar faydalanabilecektir" — özne KART, kişi değil | ürün kısıtı `note`'a; `hedef_kitle` bundan çıkmaz |
| `hedef_kitle`ye serbest metin | 5 | belgeden kopyalanmış cümle | 4 etiketten biri; tanım `note`'a |
| "bireysel müşterilerimiz" segment sanıldı | 2 | herkese açık ürün | `belirli_segment` DEĞİL |
| "müşteri ol" → `yeni_musteri` | 3 | "Müşteri Ol" çağrısı | `yeni_musteri` + tür `Yeni Müşteri` |
| Ödülün biçimi türü belirler | 1 | puan/para → `Alışveriş Puanı`; taksit → `Kart` | biçime bak, ürüne değil |
| Refleks `unclear` | 6 | `note` doğru cevabı yazıyor, `verdict` kararsız | `unclear` metrik DIŞIdır — biliyorsan yaz |

### 3b · `kampanya_kosullari` + `kampanya_suresi` (26 satır)

| Kalıp | satır | Not |
|---|---:|---|
| Aynı değer, farklı kabuk | 8 | `["a","b"]` ile `a \| b` aynı değere çözülüyor (`gold_schema.py:388`) |
| Tarih aralığı → başlangıç alınıyor | 4 | Ç2'nin bu alandaki hâli |
| Bitişi modelin başlangıcından "gün düzelterek" türetmek | 2 | A; belgede olmayan tarih üretilir |
| Koşulu yeniden yazmak — cümle metinde YOK | 7 | B'nin 19 cümlesinden **18'i belgede bulunamadı**; alan birebir alıntı ister |
| Genel yasal ihtarı koşul saymak | 5 | "değişiklik yapma hakkını saklı tutar" her sayfada var, koşul değil |

### 3c · `vade_ay` + `taksit_sayisi` (24 satır)

Ç2 dışında kalanlar: **tek belge birden çok ürün** (5 satır) — kart "birden çok
ürün → `unclear`" diyor; **aralığın ALT ucunu alma** (2 satır, C ve D);
**model boş + belge boş → `ok`** (2 satır, A `unclear` yazmış).

### 3d · Parasal alanlar (41 satır)

| Kalıp | satır | Ayırt edici kanıt |
|---|---:|---|
| Aynı değer, farklı verdict | 10 | — |
| Şemanın tutamadığı değer | 5 | oransal ücret ("binde 5"), ayni ödül → `unclear` (kart §3-6) |
| Bant/eşik sayısı tutar sanıldı | 4 | tablo satırı, ürünün tavanı değil |
| Belgede var ama bu ürüne ait değil | 4 | KVKK gövdesi / menü / yan kuşak |
| Tablodaki oran hiç görülmedi | 3 | oran yalnız tabloda, düz metinde yok |
| Örnek tablosu / hesaplama aracı değeri | 3 | "örnek ödeme planı" ilan edilmiş değer değildir |
| Birden çok masraf kalemi toplanır | 1 | 500 + 3.000 + 16.500 = **20.000** (kart §3-5) |

> **Oy çokluğu iki kez yanlış sonuç veriyor.** (1) Masraf kalemleri satırında
> A ve C doğru topladı (20.000), **B ve D 500 yazarak kalemlerin %97,5'ini
> düşürdü**. (2) Paylaşım oranı satırında dördü de yanlış. Round1'de
> uyuşmazlıklar oylanarak değil, karta bakılarak çözülmeli.

---

## 4. ONAYLANMIŞ HALÜSİNASYON — en pahalı iki satır

Uyuşmazlık listesinde küçük görünüyorlar ama ölçümü en çok bozan bunlar: model
uydurmuş, anotatörler **onaylamış**. Halüsinasyon oranı yalnız `absent`
etiketinden hesaplandığı için, onaylanan her halüsinasyon o metriği
ölçülemez hâle getiriyor.

1. `turkiye-emlak-katilim--finansmanlar-ihtiyac-finansmani · kampanya_suresi` —
   belgedeki tek tarih *"22/11/2001 tarihli ve 4721 sayılı Türk Medeni
   Kanununun 684 üncü maddesi"*; model `2001-11-22` üretmiş. **B, C, D `ok`
   yazdı.** Yalnız A yakaladı.
2. İki dünya-katılım belgesinde `masraf_durumu` — `ücretsiz` sözcüğü **yalnız
   KVKK gövdesinde** geçiyor; `masraf`/`komisyon`/`bedel` hiç geçmiyor. **Dördü
   de** `{"has_fee": false, "amount": 0}` kabul etti. K1'e göre "uzlaşmış"
   görünüyorlar — aldatıcı uzlaşma.

**round1'de önleme:** bir değeri onaylamadan önce, onu üreten cümlenin ÜRÜNÜ
anlatıp anlatmadığına bak. KVKK/çerez/kanun gövdesinden gelen her değer
`absent`tir.

---

## 5. ÇELİŞKİ — kılavuz kendi içinde çarpışıyor (2 nokta)

> CLAUDE.md HARD RULE #4 gereği çelişki gizlenmez, işaretlenir. Bu iki nokta
> **anotatör kusuru değildir**; ekip kararı gerektirir.

### Ç-A · Ürün tanıtım sayfası: `absent` mi, tür mü? (≈8 satırın altında)

- `ANNOTATION_GUIDE.md` §4.13/1: "kampanya olmayan belge → `absent`"
- `_bicim-karti.md` §3-8: "katılma hesabı → `Yatırım Ürünü`, leasing → `Finansman`"

İkisi de **ürün tanıtım sayfasını** konu alıyor ve zıt sonuç veriyor. B bir
satırda birincisini, D aynı durumda yine birincisini, kalan herkes ikincisini
uyguladı — **dördü de kılavuza uygun davrandı.** Bu κ'ya uyuşmazlık olarak
yansıyor.

*Öneri (karar değil):* ayrımı "kampanya mı ürün mü" yerine **"belgenin tek bir
öznesi var mı"** yapmak. Tek ürün anlatan sayfa → tür; ürün LİSTESİ → `absent`.

### Ç-B · Ürün listesi sayfası: `absent` mi `unclear` mı? (3 satır)

- §4.13/1: liste sayfası → `absent`
- `_bicim-karti.md`: "bir belgede birden çok ürün varsa → `unclear`"

Hangisinin kazandığı yazılı değil.

---

## 6. TEKİL SATIRLAR — kalıba girmeyenler (4)

Dürüstlük kaydı; bunlar kalıp değil, tek tek olay.

1. `vakif-katilim--finansmanlar-kentsel-donusum-finansmani · campaign_type` —
   B `Konut Finansmanı` demiş ama belge iş yerini de kapsıyor ("İşyeri
   Yapım/Edinme" tablo satırı) → `Finansman`.
2. `kampanya_suresi` — C'nin `2026-12-21` yazım hatası (`2026-12-31` olmalı).
3. `taksit_sayisi` — C komşu belgenin gerekçesini yapıştırmış (satır kayması).
4. `kampanya_kosullari` — gerçek içerik ayrışması; C iki koşulu doğru yakalamış,
   diğerleri kaçırmış → hakemliğe.

## 7. ÇÖZÜLEMEDİ (2)

1. `vakif-katilim--finansmanlar-kentsel-donusum-finansmani · hedef_kitle` —
   "6306 sayılı kanun kapsamında hak sahibi" yasal statü mü, niyet mi?
   Kılavuzda hüküm yok. Round1'de KOSGEB / engelli / gazi yakını gibi tüm
   kanun-tanımlı gruplarda tekrarlanacak. **Karar gerekiyor.**
2. Ç-A ve Ç-B çelişkileri kapanmadan, bunlara bağlı satırlar için öneri
   üretilmedi.

---

## 8. KODDA KÖK NEDEN — iki kusur, anotatör değil

Bu iki satır kalıpların bir kısmını **anotatör hatası olmaktan çıkarıyor**:

1. `kalibrasyon_hakemlik.py::_iso_bitis` yalnız `gg.aa.yyyy` tanıyor. **Türkçe
   ay adlı** aralıklar (`01 Ocak 2026 - 31 Aralık 2026`) hiç yakalanmıyor,
   `normalize_date` sessizce başlangıcı veriyor.
2. `--kural kosul-ihtar` yalnız `gold_value` sütununa bakıyor. `verdict=ok`
   satırlarında değer `model_value`dan geldiği için kural **hiç uygulanmamış** —
   "genel yasal ihtar" kalıbının 5 satırı buradan geliyor.

Bunlar `scripts/` altında ve bu görevin dokunma yasağı kapsamında; **rapor
edildi, düzeltilmedi.**

---

## 9. ROUND1'E TAŞINACAK KONTROL LİSTESİ

Kapsadığı satır sayısına göre sıralı:

1. **Onaylıyorsan `verdict=ok` yaz, `gold_value`yu BOŞ bırak.** Değeri tekrar
   yazmak düzeltmedir. *(~36 satır)*
2. **Aralık gördüysen tek değer + `note`.** Vade/taksit → en büyük · tutar →
   üst sınır · tarih → bitiş. *(~24 satır)*
3. **`gold_value` alanın değeridir**, belgenin konusu değil. Gerekçe `note`'a.
   `absent` değer taşımaz. *(~15 satır)*
4. **Menü / KVKK / çerez / kanun gövdesinden gelen değer `absent`tir.** *(~14 satır)*
5. **8 tür ve 4 hedef kitle etiketi SABİT.** Sığmıyorsa kart §3-8. *(~12 satır)*
6. **Toplamı 100 eden iki yüzde = paylaşım oranı** → `kar_payi_orani = absent`.
7. **Doğruyu biliyorsan `unclear` yazma**; `unclear` metrik dışıdır.
8. **Uyuşmazlığı oylama, karta bak** — iki satırda çoğunluk yanlıştı.

---

## 10. Neden bu kalıplardan `_oneriler.csv`'ye satır EKLENMEDİ

`_oneriler.csv` yalnız **64 biçim hatasından** türeyen 39 mekanik öneriyi
taşıyor. Yukarıdaki kalıp analizi çok daha fazla düzeltme adayı üretti, ama
onlar onay dosyasına **bilerek** alınmadı:

- Kalıp adaylarının çoğu **yargı** içeriyor ("bu cümle menüden geliyor",
  "bu belge kampanya değil"). Bunları hazır-onay satırı olarak sunmak,
  anotatörün yerine karar vermeye en yakın adımdır.
- Ölçülmüş gerekçe: bu görevde üretilen **41 mekanik öneriden 2'si yanlıştı**
  (`%20-%70` → 70 TL; vade aralığının taksit alanına yazılması). İkisi de
  `parse_gold_value` süzgecinden **geçiyordu** — yalnız ayrı bir doğrulama
  yakaladı. Yargı içeren adayları aynı süzgeçten geçirmenin yolu yok.

Kalıplar bu belgede kural olarak duruyor; hangi satıra uygulanacağına anotatör
karar verir.

---

## Üreten komutlar

```bash
# uyuşmazlık listesi (123)
.venv/bin/python -m scripts.report_iaa \
    data/gold/review/round0_kalibrasyon_{A,B,C,D}.csv

# biçim hataları (64) ve öneriler
.venv/bin/python -m scripts.onarim_recetesi

# (b) seçeneğinin ölçümü
.venv/bin/python -m scripts.kalibrasyondan_gold
```

## İlgili belgeler

- [`_onarim-recetesi.md`](./_onarim-recetesi.md) — 64 biçim hatası, anotatör başına reçete
- [`_oneriler.csv`](./_oneriler.csv) — 39 mekanik düzeltme önerisi (onay bekliyor)
- [`_kalibrasyondan-gold.md`](./_kalibrasyondan-gold.md) — (b) seçeneği ölçümü
- [`_bicim-karti.md`](./_bicim-karti.md) — kanonik biçimler; buradaki kuralların dayanağı
