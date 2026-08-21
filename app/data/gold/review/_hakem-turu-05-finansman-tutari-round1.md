# Hakem turu 05 — `finansman_tutari` · `gold.round1`

> ## ✅ ONAYLANDI — anotatör kararı, 2026-08-21
>
> Aşağıdaki §4 listesinin **23 satırının tamamı** anotatör tarafından
> onaylandı ve uygulandı. Uygulama betiği:
> `scratchpad/hakem05_uygula.py` (karar VERMEZ, onaylanmış kararı YAZAR).
>
> **ÖLÇÜLEN SONUÇ** (`gold.round1.json`, aynı çıkarıcı, aynı commit):
>
> | | önce | sonra |
> |---|---|---|
> | `finansman_tutari` F1 | 0,500 | **0,9655** |
> | `finansman_tutari` P / R | 0,80 / 0,364 | **0,933 / 1,000** |
> | TP / FP / FN | 8 / 2 / 14 | **14 / 1 / 0** |
> | manşet mikro-F1 (TÜMÜ) | 0,738 | **0,786** |
> | halüsinasyon (TÜMÜ) | 0,344 | **0,297** |
> | makro-F1 | 0,600 | 0,647 |
>
> Projeksiyon **Senaryo 2**'ydi (0,9655) ve birebir tuttu.
>
> **DÜRÜSTLÜK NOTU — support daraldı.** `finansman_tutari` desteği 22'den
> 15'e düştü (14 TP + 1 FP); 4 hücre `unclear` olduğu için metrik dışı.
> Bu raporun §3'te yazdığı uyarı geçerlidir: F1'in yükselmesinin bir kısmı
> ölçümün DARALMASINDAN gelir, iyileşmesinden değil. Yükselen şey ölçümün
> DOĞRULUĞU — kaldırılan 14 hücrenin taşıdığı şey finansman tutarı değildi
> (temassız limit, mevduat limiti, vade kademesi eşiği, örnek ödeme planı).
>
> **S1 HÂLÂ AÇIK.** 4 `unclear` hücre onun cevabını bekliyor. Cevap
> "finansman tavanıdır" olursa F1 0,9730'a çıkar, "harcama eşiğidir" olursa
> 0,8485'e düşer — ikisi de bu satırların doldurulmasıyla, ölçümün
> genişlemesiyle olur.
>
> **AYRICA ÖLÇÜLDÜ:** kanıtsız (`field_spans` boş/uydurma) hücre sayısı
> 19'dan **15'e** düştü — bu düzeltme yeni kanıtsızlık ÜRETMEDİ.
>
> **KAPSAM SINIRI:** kararlar `gold.round1.json`'a uygulandı; kaynak
> CSV'lere (`round1_*.csv`) İŞLENMEDİ. Sebep ölçüldü ve ayrı bir kusurdur:
> `gold.round1.json` bugün CSV'lerden yeniden ÜRETİLEMİYOR — dört round1
> CSV'sinden derleme 134 yerine **57** kayıt veriyor (46 D, 30 A+B, 1
> D+HAKEM-04 kaydı düşüyor). Derleme komutu hiçbir yerde kayıtlı değil.
> Bu boşluk `sorun/` altına yazılmalı; JSON'u CSV'lerden türetmek bugün
> ölçüm tabanını değiştirir.


**Tarih:** 2026-08-21
**Tetikleyen:** `finansman_tutari` round1'de **F1 = 0,500** (P = 0,800 ·
R = 0,3636 · TP 8 · FP 2 · FN 14). Recall alanın en zayıf yarısı ve Model
Başarısı rubrikte en ağır kalem (%30); ama düşüşün modelde mi gold'da mı
olduğu ölçülmeden bilinemiyordu.
**Hakem:** LLM (bu oturum). İnsan hakem DEĞİLDİR ve rapor bunu saklamıyor.
**Kapsam:** round1'in 134 kaydında `finansman_tutari` için gold ile kural
katmanının ayrıştığı **23 kayıt** — hepsi tek tek, belgenin tam metni
üzerinden açıldı. Kalan 111 kayıt bu turda açılmadı.
**Sahiplenilen dosya:** yalnız bu belge. `gold.round1.json`, `*.csv`,
`ANNOTATION_GUIDE.md`, `src/**`, `eval/**` bu turda **DEĞİŞTİRİLMEDİ** —
gold hücresini model doldurmaz, kararı anotatör verir
(`scripts/onarim_recetesi.py` modül başlığı).

---

## 0. Kapsam ve yöntem

### Ölçüm künyesi

| | |
|---|---|
| Ölçüm dizini | `eval/reports/20260821-112217/` |
| `config` | `kural` |
| `gold_path` | `data/gold/gold.round1.json` |
| `gold_sha256` | `dc0e45d8ec27901b9bc76194c0128d3ec46c62bbc64c5dd6ff3280a8f4e7b722` |
| `gold_records` | 134 |
| `git_sha` | `552098a075ede1b1744228acee6b8a658d17549f` (`dirty: true`) |
| `created_utc` | 2026-08-21T11:22:17Z |

`per_field.csv`, `kural;strict;all;finansman_tutari` satırı birebir:

```
precision=0.8  recall=0.3636  f1=0.5
tp=8  fp=2  fn=14  tn=5
fp_hallucinated=0  fp_wrong=2
support=22  absent_decisions=5  skipped_undecided=104  unclear=3
```

**Bu satırdan okunan üç şey** (kararlardan önce, kararları etkilemeyen ölçüm
gerçekleri):

1. `support = 22` — gold'da `finansman_tutari` **dolu** olan 22 hücre var;
   8'inde model uyuşuyor, **14'ünde uyuşmuyor** (FN).
2. `fp_hallucinated = 0`, `fp_wrong = 2` — modelin ölçülen iki hatası da
   "uydurma" değil "yanlış değer"; ikisi de aşağıdaki 16. ve 19. vaka.
3. `skipped_undecided = 104` — modelin değer ürettiği ama gold'un hücreyi
   **ne doldurduğu ne `absent` işaretlediği** 9 kayıt metrik dışında. Yani
   bugün bedeli sıfır; anotatör onları `absent` yaparsa precision'a, doldurursa
   recall'a yazılırlar. Bu, P = 0,800'ün neden bu kadar yüksek göründüğünün
   açıklaması: modelin dokunduğu 9 vaka hiç tartılmıyor.

### Bağımsız çapraz ölçüm — aynı çıkarıcı, başka gold

`eval/reports/20260821-112036/` · `gold_path = data/gold/gold.v2.json`
(sha `e38a5276…`, 48 kayıt, **hakemlikten geçmiş**) · aynı `git_sha`:

```
kural;strict;all;finansman_tutari;1.0;1.0;1.0;tp=4;fp=0;fn=0
```

Aynı commit'teki aynı çıkarıcı, hakemlenmiş gold'da **F1 = 1,000**, round1
gold'unda **0,500**. Bu tek başına bir karar değil; ama "sorun hangi tarafta"
sorusuna bakılacak ilk yerin **gold** olduğunu söylüyor.

### Sapma dökümü nasıl üretildi

23 vakanın bağlamlı dökümü:

```
scratchpad/hakem05-ham.txt
sha256 = 11c1da6ea7db52c1a580a668de7449353f480a0a0e506371e361d1775926def5
```

Döküm **başlangıç noktası olarak kullanıldı, kanıt olarak kullanılmadı.** Her
vakada `gold.round1.json`'daki tam `text` alanı açıldı ve belgedeki *bütün*
parasal ifadelerin ±160 karakterlik pencereleri tarandı; aşağıdaki alıntıların
hepsi o tam metinden. Dökümün "METİNDE BULUNAMADI" dediği tek vaka (4) ayrıca
biçim varyantlarıyla doğrulandı (bkz. 4. vaka).

### Karar ölçütü

Kararların dayanağı **yalnız `ANNOTATION_GUIDE.md`**. Sıkça anılan maddeler:

- **§4 / `finansman_tutari` / Sayılmaz:** *"ödül/hediye tutarı
  (`odul_miktari`), taksit tutarı, masraf tutarı, finansmanın kendi ücreti,
  **kart harcama eşiği** ('2.500 TL ve altındaki harcamalar', 'tek seferde
  5.000 TL kredi kartı harcaması'), **temassız işlem limiti**,
  **mevduat/katılma hesabı alt-üst limiti** ('hesapta kalacak minimum
  tutar')"* → bundan sonra **K-SAYILMAZ**.
- **§4 / ARALIKTA KANONİK UÇ — ÜST SINIR:** aralıkta `gold_value` üst
  sınırdır, alt sınır `note`'a → **K-ÜST**.
- **§4 / VADE KADEMESİ EŞİĞİ KANONİK DEĞİLDİR:** *"Finansman tutarı 125.000 TL
  ve altında ise 36 ay…"* — buradaki sayı vade eşiğidir, kampanyanın tutarı
  değil; `finansman_tutari`ye **yazılmaz** → **K-EŞİK**.
- **§4 / HESAPLAMA ARACI / WIDGET İSKELETİ → `absent`:** yer tutucu ya da
  örnek ödeme planının sayısı kanıt değildir → **K-ARAÇ**.
- **§3.3:** boş hücre `absent` demek değildir; emin değilse `unclear` →
  **K-BOŞ**.

### Rol ayrımı — bu alanda dört ayrı şey aynı kolona sızıyor

`src/extraction/rules/tutar.py` başlığı bu karışıklığı **ölçmüş** halde
yazıyor; alıntı birebir:

> `kredi` de ayırt etmiyor, çünkü korpusta 56 kaydın 54'ü **kredi KARTI**:
> `"İlk Ek Kredi Kartınıza 1.000 TL Bankkart Lira"` → kart ödülü ·
> `"TROY kredi kartınız ile 1.000 TL- 100.000 TL"` → harcama bandı.
> Kredi kartı bir finansman ürünü değil bir ödeme aracıdır; yanındaki tutar
> harcama eşiği ya da ödüldür.

Yani kural katmanı bu dört rolü **bilerek** eliyor ve elediği örneklerden
biri (`TROY kredi kartınız ile 1.000 TL- 100.000 TL`) aşağıdaki **1. vakanın
gold değerinin tam kendisi.** Aşağıdaki tabloda her vaka bu dört rolden
biriyle etiketlendi:

| Rol | Kısaltma |
|---|---|
| yer tutucu / örnek plan (hesaplama aracı) | `ARAÇ` |
| kart harcama eşiği · temassız limit · ödül | `KART` |
| vade kademesi eşiği | `EŞİK` |
| mevduat / katılma hesabı alt-üst limiti | `HESAP` |
| **gerçek finansman üst sınırı** | **`GERÇEK`** |

---

## 1. Yirmi üç vaka

Alıntılar `gold.round1.json` → `text` alanından birebirdir.

### Grup A — gold dolu, model boş (12 vaka)

#### A1 · `albaraka--detay-saglik-harcamalarina-vade-farksiz-6-taksit-kampanyasi-1-1`
- **gold:** `{"value": 100000.0, "currency": "TRY"}` · **model:** `None`
- **rol:** `KART`
- **alıntı:** *"TROY kredi kartlarınız ile yapacağınız **1.000 TL- 100.000 TL
  arası sağlık harcamalarınıza** vade farksız 6 taksit fırsatı!"* — aynı bant
  belgede üç kez, hep "harcamalarında" çekimiyle: *"Kampanya, TROY kredi
  kartları ile 1.000 TL- 100.000 TL tutarları arasındaki sağlık
  harcamalarında geçerlidir."* `campaign_type = Kart`.
- **öneri: GOLD YANLIŞ** → `absent`; 1.000–100.000 bandı
  `kampanya_kosullari`na.
- **kılavuz:** K-SAYILMAZ ("kart harcama eşiği").
- **gerekçe:** özne harcama, finansman değil; bu cümle
  `src/extraction/rules/tutar.py` başlığında elenmesi *gerekçelendirilmiş*
  sınıfın birebir örneğidir.

#### A2 · `albaraka--kredi-kartlari-world-platinum-kart`
- **gold:** `2500.0 TRY` · **model:** `None` · **rol:** `KART`
- **alıntı:** *"World Platinum Kart **temassız özellikli** olup temassız
  özellikli POS cihazları üzerinden kredi kartınız ile **2.500 TL ve altındaki
  harcamalarınızı** temassız özellik sayesinde şifre tuşlamaya gerek duymadan
  … gerçekleştirebilirsiniz."*
- **öneri: GOLD YANLIŞ** → `absent`.
- **kılavuz:** K-SAYILMAZ — kılavuz "2.500 TL ve altındaki harcamalar"
  ifadesini **örnek olarak** sayılmazlar listesine yazmış; gold tam o ifadeyi
  almış.
- **gerekçe:** temassız ödeme limiti finansman tavanı değildir.

#### A3 · `hayat-finans--hesaplar-avantajli-hesap`
- **gold:** `200000.0 TRY` · **model:** `None` · **rol:** `HESAP`
- **alıntı:** metinde **200.000 yok.** Doğrulandı: `'200.000' in text →
  False`, `'200000' in text → False`. Belgedeki TL'li sayıların tamamı:
  `19.999 · 20.000 · 50.000 · 84.999 · 85.000 · 2.000.000`. İlgili cümle:
  *"Hesap açılışı için **minimum tutar 50.000 TL, maksimum tutar ise
  2.000.000 TL**'dir."* `campaign_type = Yatırım Ürünü`.
- **gold notu:** *"model finansman tutarının minimum değerini almış. Doğrusu
  maksimum değeri olan 200000.0 TL olacaktır."*
- **öneri: GOLD YANLIŞ** → `absent`. **İKİ KATMANLI HATA:** (a) rol yanlış —
  katılma hesabı açılış alt-üst limiti; (b) değer metinde yok — 2.000.000
  bir basamak eksik yazılmış.
- **kılavuz:** K-SAYILMAZ ("mevduat/katılma hesabı alt-üst limiti").
- **gerekçe:** notun kendisi K-ÜST'ü doğru uyguluyor ama yanlış alanda; üst
  sınır doğru okunsa bile bu bir hesap limiti, finansman değil.

#### A4 · `hayat-finans--yatirim-ve-birikim-yatirim-fonlari-yatirim-ve-birikim`
- **gold:** `100.0 TRY` · **model:** `None` · **rol:** `HESAP`
- **alıntı:** *"…ileri valörlü fonlarda **asgari işlem tutarı 100 TL** (Yüz
  Türk Lirası) olarak uygulanacaktır."* Aynı belge başka yerde: *"…işlem
  yaptığınız yatırım fonu için **alt limit 1 TL**, 1 EUR ve 1 USD'dir."*
  `campaign_type = Yatırım Ürünü`.
- **öneri: GOLD YANLIŞ** → `absent`.
- **kılavuz:** K-SAYILMAZ'ın en yakın maddesi ("mevduat/katılma hesabı
  alt-üst limiti"); ayrıca §4 `kar_payi_orani` *"Katılım fonu / katılma hesabı
  getiri oranı finansman oranı DEĞİLDİR"* maddesiyle aynı ayrım.
- **gerekçe:** fon alım tabanı bir finansman değildir — bu belgede hiç
  finansman kullandırılmıyor.
- **⚠ HAKEM-04 ETKİLEŞİMİ:** `_hakem-turu-04` ÇELİŞKİ/3, bu kaydın
  `kampanya_kosullari` kalemini tartışırken *"Aynı kayıtta `finansman_tutari`
  = 100"* olgusuna dayanıyor. Bu hücre `absent`e çevrilirse ÇELİŞKİ/3'ün K3
  bacağı (tutar "ikinci kez yazılmış") dayanağını yitirir ve kalem
  tartışmasız `koru` olur. **İki karar birlikte verilmelidir.**

#### A5 · `kuveyt-turk--kampanya-arsivi-elektrikli-arac-sarj-unitesi-finansmaninda-enerji-tasarrufu-haft`
- **gold:** `13.88247 TRY` · **model:** `None` · **rol:** `ARAÇ`
- **alıntı:** *"**12 ay vadeli 10.000 TL'lik başvuru için örnek ödeme
  planı:** Aylık kar payı oranı %4,19 … **Ödenecek toplam tutar: 13,882.47
  TL.** Bu Ödeme Planı bilgi amaçlı olup … taahhüt altına sokmaz."*
- **öneri: GOLD YANLIŞ** → `absent`; `note`'a `ornek_basvuru=10000`.
- **kılavuz:** K-ARAÇ; ayrıca K-SAYILMAZ (bu "ödenecek toplam tutar", yani
  geri ödeme, anapara değil).
- **gerekçe: ÜÇ KATMANLI HATA:** (a) örnek ödeme planı — belgenin kendisi
  "bilgi amaçlı, taahhüt değil" diyor; (b) toplam geri ödeme ≠ finansman
  tutarı; (c) `13,882.47` **ABD ayraç düzeniyle** yazılmış, gold onu Türkçe
  düzenle okuyup `13.88247` yapmış — **1000 kat** sapma ve bu değer
  karşılaştırma tablosunda "en düşük finansman" sıralamasının başına geçer.

#### A6 · `kuveyt-turk--katilma-hesaplari-birikimli-katilma-hesabi`
- **gold:** `50.0 TRY` · **model:** `None` · **rol:** `HESAP`
- **gold `field_span`:** *"…otlarla **yatırabileceğiniz minimum tutar 50 TL**,
  50 dolar, 50 euro ya da 1 gram altındı[r]"*; aynı cümlenin öncesi: *"Açılış
  için hesabınızda minimum 150 TL, 100 dolar, 100 euro veya 50 gr altın olması
  gerekir."* `campaign_type = Yatırım Ürünü`.
- **öneri: GOLD YANLIŞ** → `absent`.
- **kılavuz:** K-SAYILMAZ ("mevduat/katılma hesabı alt-üst limiti").
- **gerekçe:** periyodik asgari yatırım tutarı katılma hesabının kendi
  kuralıdır; belge finansman ürünü değil birikim ürünüdür.

#### A7 · `tom-katilim--urunlerimiz`
- **gold:** `2500.0 TRY` · **model:** `None` · **rol:** `KART`
- **alıntı:** *"15 Ocak 2026 itibarıyla, tek seferde yapılabilecek
  **maksimum temassız işlem limiti 1.500 TL'den 2.500 TL'ye
  yükseltilmiştir.**"* (aynı cümle sayfada üç kez).
  `campaign_type = Kart`.
- **gold notu:** *"model, veri metnindeki eski finansman tutarını almış.
  Güncel finansman tutarı 2500 Tldir"* — not, temassız limitini açıkça
  "finansman tutarı" olarak adlandırıyor; kök neden budur.
- **öneri: GOLD YANLIŞ** → `absent`. Sayfa çok ürünlü bir ürün listesi;
  içinde finansman tavanı ilan eden tek bir cümle yok.
- **kılavuz:** K-SAYILMAZ ("temassız işlem limiti").

#### A8 · `turkiye-finans--bireysel-gunluk-hesap`
- **gold:** `5500000.0 TRY` · **model:** `None` · **rol:** `HESAP`
- **alıntı:** *"TL Günlük Hesapla ilgili **cari hesap işlem limitleri
  dahilinde kalacak minimum tutar en az 5.000 TL, en fazla 5.500.000 TL**'dir.
  Toplam hesap bakiyesine göre değişen getiriye konu … alt limiti … 5.000 TL,
  **üst limiti 44.500.000 TL**'dir."*
- **gold notu:** *"model, finansman tutarının minimum değerini alarak hata
  yapmıştır. Doğru finansman tutatı 5500000 Tl dir."*
- **öneri: GOLD YANLIŞ** → `absent`.
- **kılavuz:** K-SAYILMAZ — kılavuzun parantez içi örneği ("hesapta kalacak
  minimum tutar") ile metnin ifadesi ("hesapta kalacak minimum tutar")
  **kelime kelime aynı.**
- **gerekçe:** günlük hesap bir mevduat/katılma ürünü; getiri kırılımı
  tablosundaki hiçbir sayı finansman değil.

#### A9 · `turkiye-finans--kobi-kobi-icin-gunluk-hesap`
- **gold:** `5500000.0 TRY` · **model:** `None` · **rol:** `HESAP`
- **alıntı:** *"TL Günlük Hesapla ilgili cari hesap işlem limitleri dahilinde
  **minimum tutar en az 5.000 TL, en fazla 5.500.000 TL**'dir."* — ama aynı
  belgenin ilerisinde: *"**TL Günlük Hesap cari alt limit tutarı 5.000 TL,
  üst limit 5.000.000 TL'dir.**"* `campaign_type = Yatırım Ürünü`.
- **öneri: GOLD YANLIŞ** → `absent`.
- **kılavuz:** K-SAYILMAZ (A8'in ikizi).
- **gerekçe:** A8 ile aynı sınıf; üstelik belge kendi içinde 5.500.000 ile
  5.000.000 arasında **çelişiyor** — hangi ucun alınacağı sorusu bile
  cevaplanamaz, alan zaten bu belgeye ait değil.

#### A10 · `turkiye-finans--kampanyalar-emeklilere-nakit-promosyon`
- **gold:** `5000.0 TRY` · **model:** `None` · **rol:** `KART`
- **gold `field_span`:** *"…rı Yedek Hesap Bonus Tutarı **Tek Seferde 5.000 TL
  Kredi Kartı Harcaması** Her bir Emekli Ya[kını]…"* — yani değer bir promosyon
  tablosunun **sütun başlığından** alınmış. Sayfanın manşeti: *"Emeklilere
  **32.000 TL'ye Varan Nakit Promosyon, Bonus ve Ödül**"*.
- **öneri: GOLD YANLIŞ** → `absent`. Sayfadaki tüm tutarlar promosyon/ödül;
  32.000 TL `odul_miktari`ya adaydır (bu turun kapsamı dışında, ayrıca
  değerlendirilmeli).
- **kılavuz:** K-SAYILMAZ — kılavuzun ikinci örneği **"tek seferde 5.000 TL
  kredi kartı harcaması"**; gold tam o ifadeyi almış.

#### A11 · `vakif-katilim--detay-ogretmenlerimize-vakif-katilimdan-avantajli-paket`
- **gold:** `1000.0 TRY` · **model:** `None` · **rol:** `KART`
- **alıntı:** *"• **Kredi kartından minimum 1000 TL ve üzeri alışverişe** tek
  seferde maksimum 100 TL değerinde iade alınabilecektir."*
- **öneri: GOLD YANLIŞ** → `absent`. (Belgedeki 100 TL / 500 TL iade
  değerleri `odul_miktari`ya adaydır — bu turun kapsamı dışında.)
- **kılavuz:** K-SAYILMAZ ("kart harcama eşiği").
- **gerekçe:** 1.000 TL, iade kazanmanın **eşiği**; kimseye 1.000 TL
  finansman kullandırılmıyor.

#### A12 · `ziraat-katilim--kart-kampanyalari-size-ozel-banka-karti-kampanyasi`
- **gold:** `5000.0 TRY` · **model:** `None` · **rol:** `KART`
- **gold `field_span`:** *"…ampanyalar **İlk Bankkart Kredi Kartınıza 5.000 TL
  Bankkart Lira!** Son Gün 07.08.2026 Diğer[ Kampanyalar]"* — ifade sayfanın
  altındaki **"Diğer Kampanyalar"** kutusundan geliyor. Belgenin kendi
  kampanyası: *"…tek seferde 1.000 TL ve üzeri harcamaya 250 TL iade
  edilecektir."*
- **öneri: GOLD YANLIŞ** → `absent`.
- **kılavuz:** K-SAYILMAZ ("ödül/hediye tutarı → `odul_miktari`"); ayrıca §4
  `alisveris_puani` ADET kuralı — *Bankkart Lira* bir **marka puanıdır**,
  HAKEM-04'ün ParafPara kararıyla aynı sınıf.
- **gerekçe: İKİ KATMANLI HATA:** değer (a) **başka bir kampanyanın** tanıtım
  kutusundan, (b) finansman değil marka puanı ödülü.
  `src/extraction/rules/tutar.py` başlığı bu tam ifadeyi
  (`"İlk Ek Kredi Kartınıza 1.000 TL Bankkart Lira"`) elenmesi gereken sınıf
  olarak listeliyor.

### Grup B — model dolu, gold boş (9 vaka)

> Bu 9 hücrenin hiçbiri gold'da `absent_fields`e de yazılmamış (K-BOŞ), yani
> **ölçümde skipped_undecided** olarak duruyor. Bugün ne precision'a ne
> recall'a giriyorlar.

#### B1 · `albaraka--ihtiyac-subesiz-umre-finansmani`
- **gold:** boş · **model:** `50000.0 TRY` · **rol:** `GERÇEK`
- **alıntı:** *"Neler Sunuyoruz? **Vade Farksız Finansman: 50.000 TL'ye kadar
  vade farksız finansman imkânı.**"* ve *"Finansman limiti ve ödeme
  seçenekleri nelerdir? **50.000 TL'ye kadar finansman sağlanabilir.**"*
- **öneri: GOLD YANLIŞ** (eksik) → `{"value": 50000.0, "currency": "TRY"}`.
- **kılavuz:** §4 Sayılır — *"500.000 TL'ye varan finansman"* kalıbının
  birebir eşi; iki ayrı cümlede tekrarlanıyor.
- **gerekçe:** ürünün adı finansman, cümlenin öznesi finansman, tavan ilan
  edilmiş — kaçırılacak bir belirsizlik yok.

#### B2 · `hayat-finans--krediler-hayat-finans-egitim-finansmani-sistemi`
- **gold:** boş · **model:** `600000.0 TRY` · **rol:** `GERÇEK`
- **alıntı:** *"**Eğitim finansmanı üst limiti 600.000TL'dir.**"*
- **öneri: GOLD YANLIŞ** (eksik) → `600000.0`.
- **kılavuz:** §4 Sayılır. Ayrıca §4 sınır vakası biçim varyantı: `600.000TL`
  (boşluksuz) → `600000.0`.
- **gerekçe:** cümle "üst limit" sözcüğünü kullanıyor; kılavuzun aradığı
  ifadeden daha açığı yok. **Kayıt `adjudicated: true` (anotatör C) — yani
  hakemlenmiş bir kayıtta atlanmış hücre.**

#### B3 · `turkiye-emlak-katilim--nakdi-finansman-cevreci-ihracat-finansmani`
- **gold:** boş · **model:** `5000000.0 TRY` · **rol:** `GERÇEK`
- **alıntı:** *"Söz konusu ürün kapsamında **firma başına finansman üst limiti
  5.000.000 TL'dir.**"*
- **öneri: GOLD YANLIŞ** (eksik) → `5000000.0`; `note`'a `kapsam=firma_basina`.
- **kılavuz:** §4 Sayılır.
- **gerekçe:** ticari üründe kişi/firma başına tavan yine tavandır.

#### B4 · `turkiye-finans--kampanyalar-emekliler-haftasina-ozel-avantajlar`
- **gold:** boş · **model:** `50000.0 TRY` · **rol:** `GERÇEK`
- **alıntı:** *"Yeni Müşterilere Özel Avantajlar **50.000 TL'ye Kadar Kâr
  Paysız İhtiyaç Finansmanı** kampanyası ile … %0 kâr payı oranı ve 3 ay
  vadeli olarak **50.000 TL'ye kadar İhtiyaç Finansmanı** başvurusu yapma
  avantajından faydalanabilirsiniz."*
- **öneri: GOLD YANLIŞ** (eksik) → `50000.0`; `note`'a
  `yedek_hesap=2500 (ayri urun)`.
- **kılavuz:** §4 Sayılır.
- **gerekçe:** sayfa çok ürünlü bir paket (Yedek Hesap 2.500 TL, ATM
  limitleri, bonuslar) ama **finansman** tavanı ilan eden tek cümle bu; gold'un
  `null`u savunulamaz çünkü belgede bir finansman tavanı var.
- **⚠ Açık iplik:** HAKEM-01/A3'ün çözülmemiş "çok ürünlü belgede tek değer"
  sorusu bu vakada da duruyor (bkz. Kılavuz Soruları / S3).

#### B5–B8 · Kuveyt Türk "Alışveriş Finansmanı" dörtlüsü
`kuveyt-turk--alisveris-finansmanlari-{hepsiburada,teknosa,vivense}` →
model `200000.0 TRY`; `…-lc-waikiki-…` → model `5000.0 TRY`. Gold dördünde boş.

- **rol:** `GERÇEK` mi `KART` mı — **kılavuz cevap vermiyor.**
- **alıntı (üçünde birebir aynı):** *"**Alışveriş Finansmanı** ödeme seçeneği
  ile **200.000 TL'ye kadar olan alışverişlerinizde** 36 aya varan taksit
  fırsatından faydalanarak alışverişinizi hızlıca tamamlayabilirsiniz."*
- **alıntı (LC Waikiki, daha güçlü):** *"LC Waikiki'den alacağınız ürünlerde
  **5000 TL'ye kadar vade farksız 3 ay taksit imkanı ile Alışveriş Finansmanı
  fırsatını kullanabilir**, **kredi kartı limitiniz ve nakit paranızdan
  harcamadan** alışveriş keyfin[i yaşayabilirsiniz]"*.
- **öneri: KILAVUZ BELİRSİZ** (4 vaka) — karar S1'e bağlı.
- **kılavuz:** K-SAYILMAZ'ın "kart harcama eşiği" maddesi bu belgelere
  **uymuyor**: ürün açıkça kredi kartı değil (metin *"kredi kartı limitiniz …
  harcamadan"* diyor), adı "Alışveriş **Finansmanı**" ve finanse edilen tutar
  ile harcama tutarı **aynı sayı**. Öte yandan cümlenin dilbilgisel öznesi
  "alışverişlerinizde", yani biçim olarak bir harcama eşiği.
- **gerekçe:** iki okuma da savunulabilir; kılavuz "harcama eşiği" istisnasını
  yalnız **kart** için yazmış, kart-dışı alışveriş finansmanı için hüküm yok.
  Model bu dördünde tutarlı davranıyor — yani karar hangi yöne verilirse
  dördü birlikte gider.

#### B9 · `turkiye-finans--kampanyalar-yakininizi-davet-edin`
- **gold:** boş · **model:** `11000.0 TRY` · **rol:** ödül (`KART` ailesi)
- **alıntı:** *"…yeni müşterilere sunulan %0 kâr paylı **50.000 TL'ye varan
  İhtiyaç Finansmanı ve 11.000 TL'ye varan bonus** fırsatından
  yararlanmalarını sağlayın."* Sayfanın kendi ödülü: *"her yakınınız için
  500 TL, toplamda 5.000 TL bonus"*.
- **öneri: MODEL YANLIŞ.** Gold'un boş bırakması **doğru okumadır**; hücre
  `absent_fields`e yazılmalı (K-BOŞ).
- **kılavuz:** K-SAYILMAZ ("ödül/hediye tutarı → `odul_miktari`").
- **gerekçe:** 11.000 TL bir **bonustur**, finansman değil; üstelik cümlede
  anılan 50.000 TL'lik finansman bu kampanyaya değil, *"detaylı bilgi için
  tıklayın"* denen **başka bir kampanyaya** ait — bu sayfa bir davet/ödül
  kampanyasıdır.
- **KURAL TARAFINDA NE GEREKİYOR** (tek gerçek kod işi bu turda):
  `_TUTAR_PAT`'ın `([^\d]{0,20})` boşluğu **" ve "** bağlacını geçiyor;
  tetikleyici `Finansmanı`, sayı ise bağlaçtan sonraki `11.000 TL`.
  HAKEM-01/B1'in ("cümle sınırını geçen yakınlık eşleşmesi") bağlaç
  varyantı. Öneri: (a) boşlukta bağlaç (`ve|ile|ayrıca|,|;`) yasaklanır;
  (b) sayının **sağ** bağlamında ödül adı (`bonus|ödül|iade|promosyon|
  hediye|lira`) varsa aday düşürülür. Ek gözlem: doğru değer (50.000)
  tetikleyiciden **önce** duruyor; kalıp yalnız ileriye baktığı için o değeri
  hiç göremez — geriye bakış ayrı bir iş olarak ayrılmalı.

### Grup C — ikisi de dolu, değer farklı (2 vaka)

> Ölçümdeki `fp_wrong = 2`'nin tamamı bu iki vaka.

#### C1 · `turkiye-finans--kampanyalar-banka-calisanlarina-ozel-ihtiyac-finansmani`
- **gold:** `125000.0 TRY` · **model:** `1000000.0 TRY`
- **gold'un rolü:** `EŞİK` · **modelin rolü:** `GERÇEK`
- **gold `field_span`:** *"…yararlanabilir. **Finansman tutarının 125.000 TL'
  ye kadar olması durumunda maksimum vade 36 aydır.** Finansman tutarının
  125.000 TL – 250.000 TL arasında olması durumunda maksimum vade 24 ayı
  aşamaz."*
- **modelin kaynağı:** *"**Kampanya kapsamında 1.000 TL-1.000.000 TL arasında
  ihtiyaçlarınız için** size özel koşularla ve 3 ay öteleme avantajıyla
  İhtiyaç Finansmanı başvurusu yapabilirsiniz."* (belgede iki kez).
- **öneri: GOLD YANLIŞ** → `{"value": 1000000.0, "currency": "TRY"}`,
  `note`'a `alt=1000`.
- **kılavuz:** K-EŞİK (gold'un aldığı sayı birebir kılavuzun yasakladığı
  çekim: *"…olması durumunda maksimum vade 36 ay"*) + K-ÜST (modelin aldığı
  sayı ilan edilmiş aralığın üst ucu).
- **gerekçe:** gold vade kademesi eşiğini almış, model kampanyanın ilan ettiği
  aralığın üst sınırını almış; kılavuz ikisi arasında **açıkça** modelin
  tarafında.

#### C2 · `turkiye-finans--kampanyalar-ihtiyac-finansmani-kampanyasi`
- **gold:** `125000.0 TRY` · **model:** `50000.0 TRY`
- **gold'un rolü:** `EŞİK` · **modelin rolü:** `GERÇEK`
- **gold `field_span`:** *"…sayfasında yer almaktadır. **Finansman tutarı;
  125.000TL'ye kadar olması durumunda maksimum vade 36 ayı**, 125.001-250.000
  TL'ye kadar olması durumunda 24 ayı … aşamaz."*
- **modelin kaynağı** — belgenin **başlığı ve manşeti**: *"Mobilden Türkiye
  Finanslı Ol, **Kâr Paysız 50.000 TL'ye Varan İhtiyaç Finansmanını
  Kaçırma!**"* ve *"Kampanya kapsamında … **%0 kâr payı oranı ve 3 ay vadeli
  olarak 50.000 TL'ye kadar İhtiyaç Finansmanı** başvurusu yapma avantajı
  sunulacaktır."*
- **öneri: GOLD YANLIŞ** → `{"value": 50000.0, "currency": "TRY"}`.
- **kılavuz:** K-EŞİK (gold) + §4 Sayılır (model).
- **gerekçe:** 125.000 bu kampanyanın değil ürünün genel vade kademesinin
  sayısı; kampanyanın kendi tavanı başlıkta yazıyor.
- **Not:** belgede *"50.001 TL Üzeri … Kâr Oranları"* ve *"70.000 TL üzeri
  finansmanlar için…"* satırları da var — bunlar **ürünün** genel
  fiyatlaması, kampanyanın (%0 kâr paylı) tavanı değil. Ayrım `note`'a
  düşürülmeli.

---

## 2. Sayım

| Öneri etiketi | Sayı | Vakalar |
|---|---:|---|
| **GOLD YANLIŞ** | **18** | A1–A12 (12) · B1–B4 (4) · C1–C2 (2) |
| **MODEL YANLIŞ** | **1** | B9 |
| **KILAVUZ BELİRSİZ** | **4** | B5–B8 (Kuveyt Türk alışveriş finansmanı dörtlüsü) |
| Toplam | 23 | |

### Rol dağılımı — hangi şey `finansman_tutari`ye sızmış

| Rol | Vaka | Sayı |
|---|---|---:|
| `KART` (harcama eşiği · temassız limit · ödül) | A1 A2 A7 A10 A11 A12 B9 | 7 |
| `HESAP` (mevduat/katılma alt-üst limiti) | A3 A4 A6 A8 A9 | 5 |
| `EŞİK` (vade kademesi) | C1 C2 | 2 |
| `ARAÇ` (örnek plan / yer tutucu) | A5 | 1 |
| `GERÇEK` (kaçırılmış tavan) | B1 B2 B3 B4 | 4 |
| Belirsiz | B5–B8 | 4 |

**Ölçülmüş gözlem, öneri değil:** gold'daki 22 dolu `finansman_tutari`
hücresinin **14'ü** (%64) kılavuzun *"Sayılmaz"* listesindeki bir şeyi
taşıyor; kalan 8'i modelin de kabul ettiği TP'lerin ta kendisi. Yani round1'de
bu alanın dolu hücrelerinin çoğunluğu alan tanımına uymuyor.

### Anotatör kırılımı — sistematik, kişiye özel bir kalıp

| Anotatör | Kayıt | `finansman_tutari` dolu | Kılavuza aykırı | Hata oranı |
|---|---:|---:|---:|---:|
| `D` (tek geçiş, `adjudicated: false`) | 77 | 14 | **11** | %79 |
| `A`+`B` | 43 | 5 | 3 | %60 |
| `C` | 12 | 2 | 0 | %0 |
| `A`+`B`+`HAKEM-04` | 1 | 1 | 0 | %0 |
| **Toplam** | **134** | **22** | **14** | **%64** |

23 sapmanın **17'si** tek anotatörün (`D`) tek geçişli, hakemlenmemiş
kayıtlarından geliyor. Bu, kılavuzun anlaşılmadığı değil, **rol ayrımının
kılavuzda geç yazıldığı** anlamına da gelebilir: K-EŞİK ve K-ÜST maddelerinin
gerekçesi kılavuza *"ölçüldü, 2026-08-20"* damgasıyla eklenmiş, round1
etiketlemesinden **sonra.** Suç ataması değil, kapsama boşluğu.

---

## 3. Gold düzeltilirse F1 ne olur (hesap açık)

Taban (ölçülmüş): `support=22 · TP=8 · FP=2 · FN=14` →
**P = 0,800 · R = 0,3636 · F1 = 0,500**

### Senaryo 1 — yalnız gold'daki 14 dolu hücre düzeltilir
12 hücre `absent` (model de `None` → 12 yeni TN) · C1 ve C2 modelin değerine
düzeltilir.

```
support = 22 - 12 = 10
TP = 8 + 2 = 10      FP = 2 - 2 = 0      FN = 0
P = 10/10 = 1,000    R = 10/10 = 1,000   F1 = 1,000
```

### Senaryo 2 — Senaryo 1 + kaçırılan 4 tavan doldurulur + B9 `absent` yapılır
B1–B4 gold'a girer (model zaten doğru) · B9 `absent_fields`e yazılır ve
modelin 11.000'i **gerçek bir FP** olur.

```
support = 10 + 4 = 14
TP = 14              FP = 1 (B9)          FN = 0
P = 14/15 = 0,9333   R = 14/14 = 1,000    F1 = 0,9655
```

### Senaryo 3 — Senaryo 2 + kılavuz S1'i "finansman tavanıdır" diye kapatır
B5–B8 gold'a girer, model dördünde doğru.

```
support = 18 · TP = 18 · FP = 1 · FN = 0
P = 18/19 = 0,9474 · R = 1,000 · F1 = 0,9730
```

### Senaryo 4 — kılavuz S1'i tersine kapatır ("harcama eşiğidir")
B5–B8 `absent` olur, modelin dört değeri FP'ye döner.

```
support = 14 · TP = 14 · FP = 1 + 4 = 5 · FN = 0
P = 14/19 = 0,7368 · R = 1,000 · F1 = 0,8485
```

### Senaryo 0 — gold'a hiç dokunulmaz, yalnız kural katmanı çalışılır

Kural tarafında **meşru kazanç ≈ 0.** F1'i 0,500'den yukarı taşımak için
çıkarıcının şunları üretmesi gerekir: temassız işlem limiti (A2, A7), mevduat
hesabı üst limiti (A3, A6, A8, A9), kart harcama eşiği (A1, A10, A11), başka
kampanyanın marka puanı ödülü (A12), örnek ödeme planının toplam geri ödemesi
(A5), vade kademesi eşiği (C1, C2). Bunların **hepsi** kılavuzun
"Sayılmaz" listesinde. Yani bu alanda ölçümü kural tarafından yükseltmenin
tek yolu **kılavuzu ihlal etmek**; kazanılan puan karşılaştırma tablosunu
bozarak ödenir (13,88 TL'lik bir "finansman" en düşük tutar sıralamasının
başına geçer — A5).

**Dürüst çerçeve:** 0,500 rakamı bu alanda **modelin değil ölçü aletinin**
kalitesini ölçüyor. Bu, "gold'u düzeltirsek F1 yükselir" temennisi değil;
yukarıdaki dört senaryonun aritmetiği ve `gold.v2.json`'daki F1 = 1,000
çapraz ölçümüyle birlikte okunacak bir gözlem. Rapora yazılırken **Senaryo 2**
konservatif taban olarak sunulmalı (Senaryo 1'in F1 = 1,000'i, `support`
10'a düştüğü için tek başına yanıltıcıdır ve öyle sunulmamalı).

---

## 4. Anotatöre karar listesi

> Her satır tek tek onaylanır ya da reddedilir. **Hiçbiri uygulanmadı.**
> Onay sonrası uygulama yolu: `scripts/onarim_recetesi.py` (gold hücresini
> anotatör kararıyla yazan tek meşru yol).

### 4.1 `absent` yapılacak hücreler (13 satır)

```
# id | alan | mevcut deger | islem | note eki
albaraka--detay-saglik-harcamalarina-vade-farksiz-6-taksit-kampanyasi-1-1 | finansman_tutari | 100000.0 TRY | -> absent | HAKEM-05: kart harcama esigi (1.000-100.000 TL saglik harcamasi bandi); kilavuz S4/Sayilmaz. Bant kampanya_kosullari'na.
albaraka--kredi-kartlari-world-platinum-kart | finansman_tutari | 2500.0 TRY | -> absent | HAKEM-05: temassiz odeme limiti; kilavuz S4/Sayilmaz ("2.500 TL ve altindaki harcamalar" birebir ornek).
hayat-finans--hesaplar-avantajli-hesap | finansman_tutari | 200000.0 TRY | -> absent | HAKEM-05: katilma hesabi acilis alt-ust limiti; AYRICA 200.000 metinde HIC GECMIYOR (metindeki deger 2.000.000).
hayat-finans--yatirim-ve-birikim-yatirim-fonlari-yatirim-ve-birikim | finansman_tutari | 100.0 TRY | -> absent | HAKEM-05: yatirim fonu asgari islem tutari, finansman degil. DIKKAT: HAKEM-04 CELISKI/3 bu hucreye dayaniyor, birlikte karara baglanmali.
kuveyt-turk--kampanya-arsivi-elektrikli-arac-sarj-unitesi-finansmaninda-enerji-tasarrufu-haft | finansman_tutari | 13.88247 TRY | -> absent | HAKEM-05: ornek odeme planinin "odenecek toplam tutar"i (kilavuz K-ARAC); ayrica 13,882.47 ABD ayraciyla yazilmis, deger 1000 kat sapmis. ornek_basvuru=10000.
kuveyt-turk--katilma-hesaplari-birikimli-katilma-hesabi | finansman_tutari | 50.0 TRY | -> absent | HAKEM-05: katilma hesabina periyodik asgari yatirim tutari; kilavuz S4/Sayilmaz.
tom-katilim--urunlerimiz | finansman_tutari | 2500.0 TRY | -> absent | HAKEM-05: temassiz islem limiti (1.500 -> 2.500 yukseltimi); kilavuz S4/Sayilmaz. Sayfa cok urunlu urun listesi, finansman tavani ilan etmiyor.
turkiye-finans--bireysel-gunluk-hesap | finansman_tutari | 5500000.0 TRY | -> absent | HAKEM-05: cari hesapta kalacak minimum/maksimum tutar; kilavuz S4/Sayilmaz parantezi ile birebir ayni ifade.
turkiye-finans--kobi-kobi-icin-gunluk-hesap | finansman_tutari | 5500000.0 TRY | -> absent | HAKEM-05: ayni sinif; belge kendi icinde 5.500.000 / 5.000.000 celiskisi tasiyor.
turkiye-finans--kampanyalar-emeklilere-nakit-promosyon | finansman_tutari | 5000.0 TRY | -> absent | HAKEM-05: promosyon tablosu sutun basligi "Tek Seferde 5.000 TL Kredi Karti Harcamasi"; kilavuz S4/Sayilmaz birebir ornek. 32.000 TL odul_miktari adayi (ayri karar).
vakif-katilim--detay-ogretmenlerimize-vakif-katilimdan-avantajli-paket | finansman_tutari | 1000.0 TRY | -> absent | HAKEM-05: iade kazanma esigi (kart harcamasi); kilavuz S4/Sayilmaz. 100/500 TL iade odul_miktari adayi (ayri karar).
ziraat-katilim--kart-kampanyalari-size-ozel-banka-karti-kampanyasi | finansman_tutari | 5000.0 TRY | -> absent | HAKEM-05: "Diger Kampanyalar" kutusundan gelen BASKA kampanyanin Bankkart Lira odulu; marka puani (HAKEM-04 ParafPara karariyla ayni sinif).
turkiye-finans--kampanyalar-yakininizi-davet-edin | finansman_tutari | (bos) | -> absent_fields | HAKEM-05: MODEL YANLIS. Sayfa davet/odul kampanyasi; 11.000 TL bonus, finansman degil. Hucre bos degil ACIKCA absent olmali (kilavuz S3.3).
```

### 4.2 Değeri düzeltilecek hücreler (2 satır)

```
turkiye-finans--kampanyalar-banka-calisanlarina-ozel-ihtiyac-finansmani | finansman_tutari | 125000.0 TRY | -> 1000000.0 TRY | HAKEM-05: 125.000 VADE KADEMESI ESIGI (kilavuz "VADE KADEMESI ESIGI KANONIK DEGILDIR"). Kampanyanin ilan ettigi aralik "1.000 TL-1.000.000 TL"; K-UST geregi ust uc kanonik. alt=1000
turkiye-finans--kampanyalar-ihtiyac-finansmani-kampanyasi | finansman_tutari | 125000.0 TRY | -> 50000.0 TRY | HAKEM-05: 125.000 vade kademesi esigi. Kampanyanin kendi tavani baslikta: "Kar Paysiz 50.000 TL'ye Varan Ihtiyac Finansmani". 50.001+/70.000+ satirlari URUNUN genel fiyatlamasi, kampanyanin degil.
```

### 4.3 Doldurulacak boş hücreler (4 satır)

```
albaraka--ihtiyac-subesiz-umre-finansmani | finansman_tutari | (bos) | -> 50000.0 TRY | HAKEM-05: "50.000 TL'ye kadar vade farksiz finansman imkani" + "50.000 TL'ye kadar finansman saglanabilir" (iki ayri cumle).
hayat-finans--krediler-hayat-finans-egitim-finansmani-sistemi | finansman_tutari | (bos) | -> 600000.0 TRY | HAKEM-05: "Egitim finansmani ust limiti 600.000TL'dir". Kayit adjudicated:true (anotator C) - hakemlenmis kayitta atlanmis hucre.
turkiye-emlak-katilim--nakdi-finansman-cevreci-ihracat-finansmani | finansman_tutari | (bos) | -> 5000000.0 TRY | HAKEM-05: "firma basina finansman ust limiti 5.000.000 TL'dir". kapsam=firma_basina
turkiye-finans--kampanyalar-emekliler-haftasina-ozel-avantajlar | finansman_tutari | (bos) | -> 50000.0 TRY | HAKEM-05: "50.000 TL'ye Kadar Kar Paysiz Ihtiyac Finansmani". Cok urunlu paket sayfasi; yedek_hesap=2500 ayri urun (bkz. S3).
```

### 4.4 Karara bağlanamayan hücreler — S1 cevaplanana kadar `unclear` (4 satır)

```
kuveyt-turk--alisveris-finansmanlari-hepsiburada-alisveris-finansmani | finansman_tutari | (bos) | -> unclear | HAKEM-05: "Alisveris Finansmani odeme secenegi ile 200.000 TL'ye kadar olan alisverislerinizde". Kilavuz S1 bekliyor.
kuveyt-turk--alisveris-finansmanlari-teknosa-alisveris-finansmani | finansman_tutari | (bos) | -> unclear | HAKEM-05: ayni cumle, ayni soru.
kuveyt-turk--alisveris-finansmanlari-vivense-alisveris-finansmani | finansman_tutari | (bos) | -> unclear | HAKEM-05: ayni cumle, ayni soru. Kayit adjudicated:true (anotator C).
kuveyt-turk--alisveris-finansmanlari-lc-waikiki-alisveris-finansmani | finansman_tutari | (bos) | -> unclear | HAKEM-05: "5000 TL'ye kadar vade farksiz 3 ay taksit imkani ile Alisveris Finansmani"; metin ayrica "kredi karti limitiniz ... harcamadan" diyor - kart DEGIL.
```

> **`unclear` bütçesi uyarısı:** kılavuz §3.4 satırların %5'inden fazlası
> `unclear` olursa kılavuzda eksik olduğunu söyler. 134 kayıtta 4 hücre
> = %3,0; sınırın altında ama S1 cevaplanmazsa bu alan tek başına bütçenin
> yarısını yer.

### 4.5 Kural tarafına düşen tek iş

`src/extraction/rules/tutar.py` · `_TUTAR_PAT` (bu turda **uygulanmadı**,
ANA OTURUM'a bırakıldı):

1. `([^\d]{0,20})` boşluğunda **bağlaç yasağı** (`ve|ile|ayrıca|,|;`) —
   ölçülen vaka B9: *"…İhtiyaç Finansmanı **ve** 11.000 TL'ye varan bonus…"*.
   HAKEM-01/B1'in ("cümle sınırını geçen yakınlık") bağlaç varyantı.
2. Sayının **sağ** bağlamında ödül adı (`bonus|ödül|iade|promosyon|hediye|
   lira`) varsa aday düşürülür.
3. *(ayrı iş, kapsamı büyük)* Kalıp yalnız ileriye bakıyor; B9'daki doğru
   değer (50.000) tetikleyiciden **önce** duruyor ve hiç görünmüyor. Geriye
   bakış eklenirse yeni yanlış pozitif sınıfı doğabilir — ölçülmeden
   yapılmamalı.

---

## 5. Kılavuza sorulacak sorular

### S1 — Kart olmayan "alışveriş finansmanı"nda harcama tavanı finansman tavanı mıdır? (4 hücreyi bağlıyor)

Kılavuz K-SAYILMAZ'da **"kart harcama eşiği"** diyor ve iki örneği de kredi
kartı. Kuveyt Türk'ün "Alışveriş Finansmanı" ürünü kart **değil** — metin
bunu birebir söylüyor: *"kredi kartı limitiniz ve nakit paranızdan
harcamadan"*. Bu üründe finanse edilen tutar ile harcanan tutar **aynı
sayıdır**.

- **Karara bağlanması gereken:** *"X TL'ye kadar olan alışverişlerinizde"*
  kalıbı, ürün bir alışveriş finansmanıysa `finansman_tutari` = X mi, yoksa
  `absent` + koşul mu?
- **Etki:** B5–B8 (4 hücre) · F1 Senaryo 3 (0,9730) ile Senaryo 4 (0,8485)
  arasındaki fark.
- **HAKEM-05'in eğilimi** (karar değil): ürünün adı finansman, tavanı
  finansmanın tavanıdır → doldurulur. Ama kılavuzda dayanağı olmadığı için
  hücreler `unclear` bırakıldı.

### S2 — Ters ayraç düzeni (ABD biçimi) nasıl okunur?

Kılavuz §4 sınır vakası yalnız Türkçe düzeni tanımlıyor: *"1.500,00 TL" →
`1500.0` (binlik `.`, ondalık `,`)*. A5'te metin **`13,882.47 TL`** yazıyor —
ayraçlar ters. Gold onu Türkçe düzenle okuyup `13.88247` yazdı; 1000 kat
sapma.

- **Karara bağlanması gereken:** ondalık kısmı iki basamaklıysa ve son ayraç
  `.` ise ABD düzeni varsayılır mı? Yoksa böyle bir hücre `unclear` mı olur?
- **Etki:** bu turda 1 hücre, ama sessiz ve büyük bir hata sınıfı —
  karşılaştırma sıralamasını doğrudan bozuyor.

### S3 — Çok ürünlü belgede tek değer (HAKEM-01/A3'ten devralınan açık iplik)

HAKEM-01 bu soruyu **2026-08-04'te** açtı ve hâlâ kapanmadı. Bu turda üç
vakada tekrar çıktı: B4 (ihtiyaç finansmanı 50.000 + Yedek Hesap 2.500),
A7 (ürün listesi sayfası), A10 (promosyon paketi).

- **Karara bağlanması gereken:** manşet ürünün değeri mi alınır, alt kırılım
  `note`'a mı düşer, yoksa çok ürünlü belge `unclear` mı olur?
- **Etki:** B4'ün önerisi bu karara **bağımlı** — S3 "unclear" derse B4 de
  `unclear` olur ve Senaryo 2'nin `support`u 13'e düşer
  (P = 13/14 = 0,9286 · R = 1,000 · **F1 = 0,9630**).

### S4 — "Diğer kampanyalar" kutusu belgenin metni sayılır mı?

A12'de gold değeri sayfanın altındaki **başka kampanyanın** tanıtım
kutusundan alınmış. HAKEM-04, düzleştirilmiş HTML'den gelen **başlık
sızıntısı** için "kılavuzda yasaklayan bağlayıcı kural yok" demişti; bu ondan
farklı ve daha ağır bir sınıf: **başka bir kaydın değeri** bu kayda sızıyor.

- **Karara bağlanması gereken:** §4'e *"sayfa altındaki 'Diğer Kampanyalar' /
  'İlginizi Çekebilecek Kampanyalar' bloklarındaki değerler bu belgenin
  değeri değildir"* maddesi eklenir mi?
- **Etki:** bu turda 1 hücre; ama A11'de de aynı blok var
  (*"İlginizi Çekebilecek Kampanyalar … ENUYGUN.com'da 150 TL İndirim"*),
  yani sınıf tekrarlıyor ve `indirim_orani` / `odul_miktari` alanlarını da
  tehdit ediyor.

### S5 — Kapsama sorusu: `finansman_tutari` yatırım/mevduat belgelerinde hiç dolabilir mi?

A3, A4, A6, A8, A9 — beş vaka, hepsi `campaign_type ∈ {Yatırım Ürünü, None}`
ve hepsinde bir hesap limiti finansman sanılmış. Kılavuz bu sınıfı
"Sayılmaz"da anıyor ama **belge türü üzerinden bir kapı** koymuyor.

- **Karara bağlanması gereken:** *"Belge bir mevduat/katılma/yatırım ürünü
  sayfasıysa `finansman_tutari` kural olarak `absent`tir; istisna, sayfada
  ayrıca bir finansman ürünü tanıtılıyorsa geçerlidir"* maddesi yazılır mı?
- **Etki:** bu turda 5 hücre; kılavuza yazılırsa round2'de aynı sınıf en
  baştan önlenir.

---

## ÇELİŞKİ

> CLAUDE.md HARD RULE 4: çelişki gizlenmez, silinmez.

### ÇELİŞKİ/1 — Gold notu kendi değerini yalanlıyor (üç kayıt)

A3, A8, A9'un `notes.finansman_tutari` alanı şunu diyor: *"model finansman
tutarının **minimum** değerini almış. Doğrusu **maksimum** değeri olan …"* —
yani not, K-ÜST kuralını **doğru** uyguluyor. Ama üç kayıtta da uygulandığı
sayı bir **hesap limitidir**, finansman değil. Not haklı, değer yanlış: doğru
kural yanlış alanda çalıştırılmış.

- *Notun tarafı:* K-ÜST gerçekten üst sınırı ister ve anotatör onu seçmiş.
- *Değerin tarafı:* K-SAYILMAZ, aralığın hangi ucunun alınacağı sorusuna
  sıra gelmeden hücreyi kapatıyor — "mevduat/katılma hesabı alt-üst limiti"
  bu alana hiç girmez.
- **Hangisi kazandı:** K-SAYILMAZ. Sıralama önemli: rol testi uç testinden
  **önce** gelir. Notlar **silinmedi** (HARD RULE 3); üstlerine HAKEM-05
  kaydı öneriliyor, böylece kaydı okuyan biri "not değeri doğruluyor"
  tuzağına düşmüyor.
- **Kılavuz önerisi (uygulanmadı):** §4'e karar sırası yazılmalı —
  *"1) rol testi (bu sayı finansmanın kendisi mi?), 2) uç testi (aralıkta üst
  sınır)."* Bugün kılavuz K-ÜST'ü K-SAYILMAZ'dan sonra anlatıyor ama sıralamayı
  bağlayıcı kılmıyor.

### ÇELİŞKİ/2 — A4 hücresi HAKEM-04'ün gerekçesini taşıyor

HAKEM-04/ÇELİŞKİ/3, `hayat-finans--…-yatirim-fonlari-…` kaydının
`kampanya_kosullari` kalemini tartışırken K3 bacağını *"tutar zaten
`finansman_tutari`de duruyor, cümle ikinci kopyadır"* diye kurdu.

- *HAKEM-04'ün tarafı:* o turda hücre doluydu ve argüman geçerliydi.
- *HAKEM-05'in tarafı:* hücrenin **kendisi** kılavuza aykırı — fon alım
  tabanı finansman değil. Hücre boşalırsa K3 tetiklenmez ve kalem
  tartışmasız `koru` olur.
- **Hangisi kazandı: hiçbiri — tek taraflı kapatılmadı.** İki karar
  birbirine bağlı; anotatör ikisini **aynı oturumda** görmeli. A4 satırı
  4.1'de bu uyarıyla duruyor.

### ÇELİŞKİ/3 — F1 = 1,000 çekici bir sonuçtur ve şüpheyle okunmalı

Senaryo 1 aritmetik olarak **F1 = 1,000** veriyor. Bu sayı raporda manşet
yapılırsa yanıltıcıdır ve yanlılık şüphesini haklı çıkarır:

- *Lehte:* hesap doğru; 14 hücrenin her biri kılavuz maddesine bağlı ve
  alıntısı yukarıda duruyor.
- *Aleyhte:* F1 = 1,000'e ulaşmanın yolu `support`u 22'den **10'a
  düşürmekten** geçiyor. Daha küçük bir tabanda daha yüksek bir skor, ölçümün
  iyileşmesi değil **daralması** olabilir; 10 hücreyle hesaplanan bir F1'in
  güven aralığı çok geniştir (`bootstrap_resamples = 1000` ile ölçülmeli).
- **HAKEM-05'in duruşu:** manşet **Senaryo 2** (F1 = 0,9655, `support` 14)
  olmalı; Senaryo 1 ara adım olarak, `support` düşüşü **açıkça yazılarak**
  verilmeli. Rapora "F1 0,50 → 1,00" diye yazmak, HAKEM-01'in uyardığı hatanın
  aynısıdır: *"metriği süsler, sistemi bozar."*

---

## Sonraki adım

1. **4.1 · 4.2 · 4.3** (19 satır) anotatör onayına gider. Onaylanan satırlar
   `scripts/onarim_recetesi.py` ile uygulanır; bu belge tek başına gold'u
   değiştirmez.
2. **A4** satırı HAKEM-04/ÇELİŞKİ/3 ile **birlikte** karara bağlanır.
3. **S1** cevaplanana kadar B5–B8 `unclear` (4.4). S1 kapanınca dört hücre
   tek hamlede gider.
4. **S2 · S3 · S4 · S5** kılavuz maddesi olarak yazılır (yetki bu turun değil,
   ekibin). S5 yazılırsa round2'de `HESAP` sınıfı baştan önlenir.
5. Kural tarafı: **4.5/1** ve **4.5/2** uygulanır; **4.5/3** ölçülmeden
   yapılmaz.
6. Düzeltme sonrası ölçüm `--config kural --gold data/gold/gold.round1.json`
   ile yeniden koşulur ve **gerçekleşen** F1 buraya işlenir; yukarıdaki dört
   senaryo *projeksiyondur*, ölçüm değildir.

## Sources
- `eval/reports/20260821-112217/{env.json,per_field.csv,decisions.csv}` —
  ölçümün kendisi (gold sha `dc0e45d8…`)
- `eval/reports/20260821-112036/` — `gold.v2.json` çapraz ölçümü (F1 = 1,000)
- `data/gold/gold.round1.json` — 23 kaydın tam `text`, `fields`, `notes`,
  `field_spans`, `annotators` alanları
- `data/gold/ANNOTATION_GUIDE.md` §3.3 · §3.4 · §4 (`finansman_tutari`,
  `odul_miktari`, `alisveris_puani`)
- `src/extraction/rules/tutar.py` — modül başlığı, ölçülmüş rol karışıklığı
  envanteri
- `scratchpad/hakem05-ham.txt` (sha256 `11c1da6e…`) — sapma dökümü,
  başlangıç noktası

## Related
- [[_hakem-turu-01-finansman-tutari]] — aynı alanın ilk turu; A1/A2'de
  "varlık fiyatı ≠ finansman tutarı", A3'te çözülmemiş çok ürünlü belge
  sorusu (bu turda S3 olarak yeniden açıldı)
- [[_hakem-turu-04-gold-kilavuz-celiskisi]] — ÇELİŞKİ/3 bu turun A4 hücresine
  dayanıyor; ParafPara kararı A12'nin marka puanı gerekçesiyle aynı sınıf
- [[_bicim-karti]] — §3.4/4 para aralığında üst sınır kuralının kaynağı
- [[_onarim-recetesi]] — onaylanan satırların uygulanma yolu
