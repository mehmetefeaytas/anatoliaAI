# Hakem turu 02 — `hedef_kitle`

**Tarih:** 2026-08-19
**Tetikleyen:** `hedef_kitle` gold.v2'de en düşük F1'li ölçülebilir alan
(0,267) ve **18 destekli** — yani en büyük iyileştirme potansiyeli orada
görünüyordu. Alanı düzeltmek için 19 tutarsızlığın (10 kaçırma + 9 fazla
üretim) tamamı tek tek, gold'un kendi kanıt span'leriyle karşılaştırıldı.
**Durum:** `celiskili` — karar bekliyor, ikinci anotatör gerekiyor.

## Neden bu belge var

Alanı kod tarafından düzeltmeye başladık ve **yarıda durdurduk.** Sebep:
tutarsızlıkların çoğu çıkarıcı kusuru değil, gold'un kendi kılavuzuyla
çelişmesi. Motoru bu hedefe uydurmak F1'i süsler, sistemi bozar
(hakem turu 01'in aynı gerekçesi).

Kılavuzun kuralı net — §4.13/2, **KİM/NE testi**: cümle müşterinin KİM
olduğunu mu söylüyor (yaş, meslek, statü, bankayla ilişki), yoksa NE
kullandığını mı (kart, ürün, kanal, uygulama)? Ürün/kart/kanal kısıtı
segment DEĞİLDİR; `kampanya_kosullari`na gider.

19 tutarsızlık bu kurala göre üçe ayrıldı.

---

## A. GOLD HATASI ŞÜPHESİ — çıkarıcı bunlara uydurulmamalı

### A1. Ürün/kart kısıtı `belirli_segment` olarak etiketlenmiş

**BU BÖLÜM DÜZELTİLDİ (aynı gün, karar verilirken).** İlk yazımda "5 vaka
kılavuz ihlali" denmişti; o iddia `notes` alanları OKUNMADAN kurulmuştu ve
fazla iddialıydı. Etiketleyici üç vakada gerekçe yazmış ve gerekçeler
savunulabilir. Doğru tablo şu:

| Kayıt (kısalt.) | Kanıt span'i | `notes` gerekçesi | Karar |
|---|---|---|---|
| `dunya-katilim--kampanyal` | "…**Paraf kredi kartına sahip** ancak henüz…" | "kartı olan ama hiç harcama yapmamış" | **savunulabilir** — davranış segmenti, salt ürün kısıtı değil |
| `tom-katilim--hadi-black` | "…**Hadi Black Kredi Kartı** ile harcama…" | "'Çok Kazananlar Kulübü üyesi' + bakiye/ekstre eşikleri" | **savunulabilir** — eşiğe dayalı statü |
| `tom-katilim--a101de` | "**Hadi Gold üyesi** olmalısın." | (boş) | **tartışmalı** — üyelik statü mü ürün mü, kılavuz cevap vermiyor |
| `kuveyt-turk--7000-tl` | "Kampanya **size özel** hazırlanmıştır, devredilemez." | (boş) | **NET HATA** — cümlede hiç segment sinyali yok |
| `tom-katilim--cok-kazananlar` | "yalnızca **Hadi Black Kredi Kartı** harcamaları için geçerli" | (boş) | **NET HATA** — saf ürün kısıtı, §4.13/2 KİM/NE testini doğrudan ihlal ediyor |

Yani **2 net hata + 1 tartışmalı + 2 savunulabilir**. Bu düzeltmenin kendisi
bir ders: kanıt span'ine bakıp `notes`'u atlamak, etiketleyicinin gerekçesini
görmeden onu hatalı ilan etmeye yol açıyor.

#### Uygulanan karar (2026-08-19)

Yalnız **2 net hata** karara bağlandı; ikisinde de `belirli_segment`
kaldırıldı ve alan `absent_fields`'a alındı:

- `kuveyt-turk--kampanya-arsivi-7000-tl-degerin…` — "size özel hazırlanmıştır"
  kişiselleştirilmiş davet bildirir, hangi segment olduğunu söylemez.
  Kılavuz: sinyal yoksa `absent`.
- `tom-katilim--kampanyalar-cok-kazananlar-kulu…` — saf ürün kısıtı,
  `kampanya_kosullari`na aittir.

Her ikisinde `notes.hedef_kitle`'ye gerekçe yazıldı, `adjudicated: true`
işaretlendi ve `annotators`'a `HAKEM-02` eklendi. `field_spans.hedef_kitle`
de kaldırıldı — gold şema doğrulaması haklı olarak "yokluğun alıntısı olmaz"
diyor.

Tartışmalı ve savunulabilir 3 vakaya **dokunulmadı**; onlar ikinci bir
anotatör kararı bekliyor.

**Ölçülen etki** (gold.v2, strict/all, kural):

| Metrik | Önce | Sonra |
|---|---|---|
| `hedef_kitle` F1 | 0,267 | **0,286** |
| 12-alan mikro-F1 | 0,477 | **0,482** |
| makro-F1 | 0,634 | **0,636** |
| yapısal mikro-F1 | 0,693 | **0,702** |
| `adjudicated` kayıt | 0/48 | **2/48** |

Kazanç küçük ve bu beklenen: iki kayıt düzeltildi, motor hiç değişmedi.
Asıl önemi başka — `adjudicated` sayacı ilk kez sıfırdan çıktı, yani
"48 kaydın hiçbiri hakem kararı görmemiş" eleştirisi artık tam doğru değil.

### A2. Gerçek segment varken gold boş bırakılmış (3 vaka)

Bu yönde de sapma var — çıkarıcının "fazla" ürettiği sayıldığı ama metinde
gerçekten segment bulunan kayıtlar:

| Kayıt | Çıkarıcının kanıtı | Gold |
|---|---|---|
| `ziraat-katilim--ozel-ban` | "…(kamu ve özel sektör çalışanları, **emekliler** vb.)…" | boş |
| `kuveyt-turk--leasing-lea` | "Şahıs Firmaları … **Serbest Meslek Sahipleri** …" | boş |
| `albaraka--tr-kampanyalar` | "**Yeni Müşterilerimize** Özel Vade Farksız…" | boş |

Üçünde de metin hedef kitleyi açıkça sayıyor. A1 ile A2 birlikte
okunduğunda tablo şu: aynı kural bazı kayıtlarda fazla geniş, bazılarında
fazla dar uygulanmış.

---

## B. KOD HATASI — düzeltilebilir, ama biri ölçülerek reddedildi

### B1. Segment sözlüğü eksik (3 vaka)

`belirli_segment` deseni yalnız altı statü tanıyor
(`emekli|öğrenci|esnaf|kamu çalışanı|kobi|serbest meslek`). Gold'un meşru
saydığı şu segmentler sözlükte yok:

- "tüzel ve şahıs firmasına sahip **eczaneler**" (meslek)
- "riskli yapı olarak tespit edilen … **malikleri**" (statü)
- "**HFY yatırımcısı** … nitelikli yatırımcı beyanı" (statü)

Bunlar kılavuza göre gerçek segment; sözlük genişletilebilir. Ancak
genişletme A1/A2 çözülmeden yapılırsa hangi yöne doğru çekildiği
ölçülemez — bu yüzden bu turda yapılmadı.

### B2. Bağlam kaçakları (3 vaka)

- `albaraka--hayat-ve-ferdi`: "Bireysel **Emekli**lik" — ürün adının içinde
  eşleşme.
- `turkiye-finans--kampanya`: "**Hoş Geldin** Ramazan!" — kampanya adı,
  müşteri segmenti değil.
- `hayat-finans--hesaplar`: "sadece **hoş geldin** kampanyası **değil**" —
  negasyon penceresi `geçerli değil` kalıbını arıyor, tek başına "değil"i
  görmüyor.

### B3. ÖLÇÜLMÜŞ YANLIŞ DENEME — tekrarlanmasın

B2'nin ilk iki maddesi lookahead ile elenmeye çalışıldı:
`emekli(?!lik)` ve `ho[şs]\s*geldin(?!iz)`.

**Sonuç: F1 0,267 → 0,214 (tp 4 → 3). Daha kötü.** Gold o iki ifadeyi
sinyal sayıyor:

- `vakif-katilim--musteri-alisveris-*`: "hoş geldiniz" → gold `yeni_musteri`
- `vakif-katilim--detay-troy-*`: "emeklilik" → gold `belirli_segment`

Yani ifade metinde ürün adı olarak geçse bile gold onu segment sinyali
kabul ediyor. Değişiklik geri alındı ve gerekçesi `extract.py` içine
yorum olarak işlendi.

---

## C. SÖZLEŞMENİN CEVAP VERMEDİĞİ BELİRSİZLİK (4 vaka)

| Metin | Soru |
|---|---|
| "**ilk kez** VKart TROY Kredi Kartı sahibi olacak" | İlk kez bir ÜRÜNE sahip olmak `yeni_musteri` mi, ürün kısıtı mı? Gold `belirli_segment` demiş, çıkarıcı `yeni_musteri` üretmiş. |
| "müşterimiz olan **bireysel müşterilerimize özel**" ("müşteri ol" sayfası) | Sayfa yeni müşteri kazanmaya dönük, cümle mevcut müşteriyi anlatıyor. Gold `yeni_musteri`, çıkarıcı `mevcut_musteri`. |
| "**Enerya Enerji A.Ş.** faaliyet alanı içindeki illerde doğalgaz dönüşümü" | Coğrafi + iş ortağı kısıtı. Segment mi, koşul mu? |
| "**seçili müşteriler** için geçerli" | "Seçili" bir segment adı değil; kim olduğu belirtilmemiş. |

---

## Sayısal tablo

| Sınıf | Vaka | Etki |
|---|---|---|
| A. Gold hatası şüphesi | 8 | Çıkarıcı düzeltilmemeli |
| B. Kod hatası | 6 | 3'ü düzeltilebilir, 2'si ölçülerek reddedildi (B3) |
| C. Sözleşme belirsizliği | 4 | Kılavuza madde gerekiyor |

Kılavuzun kendi notu bu tabloyu doğruluyor: `hedef_kitle` kalibrasyonun **en
çok ayrışan üçüncü alanı** (19 uyuşmazlık) ve F1'in 0,727 → 0,267 düşüşü
"etiket kümesi genişletildiğinde eşleşme rastlantısallaşır" diye
kayıtlıydı (§4.13/2 notu, 2026-08-09). Yani sorun 19 Ağustos'ta keşfedilmedi;
bu belge onu vaka düzeyinde somutlaştırıyor.

## Öneri — hakem turu için

1. **A1'i karara bağla.** Ürün/kart/üyelik kısıtı `belirli_segment`
   olmayacaksa 5 kayıt yeniden etiketlenmeli; olacaksa kılavuz §4.13/2
   değişmeli. İkisinden biri — mevcut hâl ikisini birden söylüyor.
2. **A2'nin 3 kaydını ikinci anotatöre ver.** Metinde açık segment var.
3. **C'nin 4 vakası için kılavuza madde yaz** (özellikle "ilk kez bir ürüne
   sahip olmak" ve "seçili müşteri").
4. **B1'i A/C çözüldükten sonra yap.** Sözlük genişletmesi ancak hedef
   netleştikten sonra ölçülebilir bir iyileştirmedir.
5. Bu alan çözülene kadar `hedef_kitle` F1'i **motor başarısının değil
   sözleşme olgunluğunun göstergesi** olarak okunmalı.
