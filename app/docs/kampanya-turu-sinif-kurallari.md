# 8 Kampanya Türü — Sınıflandırma Kuralları

> Karar tarihi: 2026-08-04. Dayanak: 502 belgelik otomatik etiketleme turunda
> üç bağımsız denetleyicinin **aynı iki kural boşluğuna** çarpması.
>
> İlgili: `CLAUDE.md` §12 (8 sınıf), §17 (adil kıyas garantisi),
> `data/gold/ANNOTATION_GUIDE.md`, `data/gold/review/_bicim-karti.md`,
> `docs/anotasyon-hatti-plani.md`

---

## Terminoloji uyarısı — bu belge konvansiyonel terim İÇERİR ve içermelidir

Bu belge bir **sınıflandırma kuralıdır** ve iki korpusu birden sınıflandırır:
yarışma korpusu (`data/raw`, katılım bankaları) ve gümüş eğitim korpusu
(`data/raw-classic`, konvansiyonel bankalar — `CLAUDE.md` §12 kapsamı
dışında, yalnız sınıflandırıcı eğitiminde).

Bu yüzden aşağıda "ihtiyaç kredisi", "KMH", "faiz" gibi terimler geçer.
Bunlar **bizim ürünümüzün adı değil, tanınması gereken girdi desenleridir**:
sınıflandırıcı konvansiyonel bir sayfayı doğru sınıfa atayabilmek için o
sayfanın kendi sözcüklerini bilmek zorundadır. Konvansiyonel bir rotatif
limitin faizle işlediğini yazmak da olgusal olarak doğrudur.

**Kural:** konvansiyonel terim yalnız *konvansiyonel ürünü* anlatırken
kullanılır. Katılım ürünü anlatılırken katılım terimi kullanılır ve ikisi
aynı listede ayrım yapılmadan yan yana yazılmaz. Kullanıcıya dönük hiçbir
yüzeyde (arayüz, chatbot, özet) bu terimler üretilmez — orayı
`scripts/jargon_lint.py` ve `src/chatbot/safety.py` KAPI 1 korur.

## Neden bu belge var

Kılavuzda 8 sınıfın listesi vardı, ama **aralarındaki sınır tanımlı değildi.**
Ölçüm: 420 etiketli belgede 34 ayrışma çıktı ve yarısı tek bir eksende
toplandı. Aynı ürün, neredeyse aynı sayfalarda iki farklı etiket aldı:

| Ürün | Bir belgede | Diğerinde |
|---|---|---|
| World Pay Alışveriş Kredisi | `Finansman` | `İhtiyaç Finansmanı` |
| Kapama Koşullu Kredi | `İhtiyaç Finansmanı` | `Finansman` |
| Taksitli Nakit Avans / Artı Para | `İhtiyaç Finansmanı` | `Finansman` |

Bu tek tek belge hatası değil, kural boşluğudur. Üç denetleyici farklı
dilimlere bakıp aynı sınıra çarptığı için ölçüm güvenilir.

---

## Belirleyici ilke: sınıf, karşılaştırma tablosunu belirler

`CLAUDE.md` §17: *"Yalnızca aynı birime normalize alanlar kıyaslanır. Koşullar
farklıysa doğrudan kıyaslanamaz işaretle, uydurma sıralama yapma."*

Sınıf, hangi ürünün hangi ürünle yan yana konacağını belirler. Dolayısıyla
yanlış sınıf **etiket hatası değil, dashboard'da yanlış sıralamadır.** Bütün
kurallar bu ilkeden türetildi.

---

## Kural 1 — Sınıf, sayfanın SATTIĞI ürünün türüdür

Ödül mekaniği, uygunluk koşulu ve başvuru kanalı sınıfı **belirlemez**.
Onların kendi alanları var: `odul_miktari`, `alisveris_puani`,
`kampanya_kosullari`, `hedef_kitle`.

**Neden:** koşulu sınıfa taşımak aynı ürünü iki sınıfa dağıtır. "Yeni müşteriye
özel ihtiyaç kredisi" ile "mevcut müşteriye ihtiyaç kredisi" **aynı ürünü**
satıyor; karşılaştırma tablosunda aynı satırda olmalılar. Koşul farkı
`hedef_kitle` alanında görünür ve orada zaten görünmesi gerekiyor.

---

## Kural 2 — Ürün 8 sınıf dışıysa `null`

`null` bir kayıp değil, **doğru cevaptır.** Taksonomi 8 sınıfla sabit
(şartname); dışındaki ürünü zorla içeri sokmak sınıflandırıcıya kalıcı hata
öğretir.

8 sınıf dışı olduğu ölçülmüş ürünler:

| Ürün | Neden dışarıda |
|---|---|
| **BES / bireysel emeklilik** | aşağıda ayrı bölüm |
| Sigorta (DASK, konut, hayat, kasko) | banka ürünü değil, acentelik |
| Çek karnesi, POS, yazarkasa | işlem hizmeti, finansman değil |
| Araç **kiralama** indirimi | satılan şey banka ürünü değil |
| Maaş promosyonu | ürün değil, tek seferlik ödeme |
| Uygulama tanıtımı, hesaplama aracı, SSS | ürün sayfası değil |
| Çekiliş (araç, telefon) | ürün yok, teşvik var |

---

## Kural 3 — `İhtiyaç Finansmanı` vs `Finansman` ⭐ (asıl karar)

### `İhtiyaç Finansmanı`
**Bireysel** + **genel amaçlı** + **sabit vade** + **taksit planı**.

Ürün adının "ihtiyaç kredisi" olması şart değil; belirleyici olan bu dört
niteliğin birlikte bulunması. Buraya girer:

- ihtiyaç / tüketici kredisi
- emekli kredisi, maaş müşterisi kredisi
- borç transferi / borç birleştirme
- **taksitli nakit avans** (vade + taksit + oran taşıyor)
- alışveriş kredisi
- evlilik / eğitim / tatil / sağlık kredisi (amaç niteleyici, ürün ailesi aynı)

### `Finansman` — artakalan sınıf, iki grup

**(a) Bireysel olmayan finansman:** ticari, KOBİ, işletme, tarım, proje,
dış ticaret, leasing (icara).

**(b) Vadesiz / rotatif kredi limitleri:** KMH (Kredili Mevduat Hesabı),
Ek Hesap, Artı Para, Taksitli Esnek Hesap.

### (b) grubunun gerekçesi — §17

Rotatif bir limitin **vadesi ve taksit planı yoktur**; faiz yalnızca
kullanılan tutar ve süre üzerinden işler. Taksitli bir tüketici kredisiyle
aynı sınıfa koymak, dashboard'da şu karşılaştırmayı üretir:

    A Bankası ihtiyaç kredisi   %3,79   36 ay   taksit 5.986 TL
    B Bankası KMH               %4,25   —       —

İkinci satır birinciyle kıyaslanamaz: aynı birimde değil. §17 bunu açıkça
yasaklıyor. Ayrı sınıf, tablonun yanlış sıralama üretmesini **yapısal olarak**
engelliyor — bu, sonradan bir uyarı eklemekten güçlüdür.

`teb--kredili-mevduat-hesabi` belgesi bunu kendi metninde söylüyor:
*"KMH … hesapta yeterli bakiye olmadığında bile hesaptan provizyon
alınabilmesini sağlayan bir **kredi türüdür**."* Kredi, ama ihtiyaç kredisi
değil.

### Neden taksitli nakit avans `İhtiyaç Finansmanı`, KMH değil

İkisi de karta bağlı olabilir, ama **taksitli nakit avans vade + taksit + oran
ilan eder** — yani karşılaştırma tablosunda taksitli bir tüketici kredisiyle
aynı birimde durur. KMH etmez. Ayrım kart olup olmamasında değil,
**karşılaştırılabilirlikte**.

Kartın rolü burada yalnızca kullandırma kanalıdır ve Kural 1 gereği sınıfı
değiştirmez.

---

## Kural 4 — `Yeni Müşteri` yalnızca teklifin KENDİSİ müşteri kazanımıysa

`Yeni Müşteri` sınıfı, altında 8 sınıftan somut bir ürün **olmadığında**
kullanılır: hoş geldin nakdi/hediyesi, davet-referans ödülü, "müşteri ol X TL
kazan".

Sayfa somut bir ürün satıyorsa (kredi, mevduat, kart) sınıf **o üründür**;
"yeni müşteri" koşulu `hedef_kitle` alanına `yeni_musteri` olarak gider.

**Neden:** aksi hâlde her banka aynı ürünü "yeni müşteriye özel" diye
paketlediğinde ürün karşılaştırma tablosundan düşer. Kullanıcının sorduğu soru
"hangi bankada en düşük oran" — ürün sınıfı korunmadan bu soru
cevaplanamaz.

---

## Kural 5 — `Alışveriş Puanı` yalnızca teklif HARCAMAYA bağlı puan/iade ise

- Teklif **harcama karşılığı puan/iade** (chip-para, bonus, MaxiPuan,
  ParafPara, Worldpuan) → `Alışveriş Puanı`
- Teklif **kart edinimi** (ana kart, ek kart, ilk kart başvurusu) → `Kart`,
  ödül puan olsa bile
- Teklif **indirim / vade farksız taksit / ücret muafiyeti** → `Kart`

**Neden:** `Alışveriş Puanı` alanı `{"kind": "rate"|"points", "value": …}`
biçiminde ölçülebilir bir değer taşır. Kart ediniminin ölçülebilir karşılığı
puan değil, kartın kendisidir.

---

## BES kararı — `null`, ve gerekçesi ölçülmüş bir hataya dayanıyor

BES ekonomik olarak bir yatırım ürünü. Ama bu taksonomide `Yatırım Ürünü`
**banka tasarruf-yatırım ürünü** demek: katılım tarafında katılma hesabı,
altın/gümüş hesabı, katılım fonu; konvansiyonel tarafta bunların karşılığı
mevduat ve yatırım fonu. (İki taraf ayrı yazılır: katılma hesabı mevduat
DEĞİLDİR — biri kâr/zarar ortaklığı, diğeri getirisi taahhüt edilen borç
ilişkisidir.) Bunların ortak yanı ilan edilmiş bir **getiri oranı**
taşıması ve karşılaştırma tablosunda o oranla yer alması.

BES'in karşılaştırılabilir bir oranı yok; **%25 devlet katkısı** ve fon getirisi
taşır. Ve tam bu nokta ölçülmüş bir hatayı doğuruyor:

> 2026-08-03'te düzeltilen canlı hata: `kar_payi_orani` üreten 64 belgenin
> 7'si (%11) değeri yabancı kavramdan alıyordu; **6'sı "%25'e kadar devlet
> desteği" ifadesinden**. Bkz. `tests/test_kar_payi_yon.py::TestYabanciKavram`.

BES sayfaları bu hatanın doğal yaşam alanıdır. `Yatırım Ürünü` sınıfına
koymak, o sayfaları sistematik olarak mevduat karşılaştırmasına besler ve
%25'lik devlet katkısını getiri oranı sanma riskini kurumsallaştırır.

Sigorta ürünleri (DASK, konut, hayat, kasko) aynı gerekçeyle dışarıda: banka
ürünü değil, acentelik hizmeti; oranı ve vadesi banka ürünleriyle aynı birimde
değil.

**Not:** BES/sigorta kampanyasının ödülü puan ya da kart avantajı olsa bile
sınıf `null` kalır — Kural 1 gereği ödül mekaniği sınıfı belirlemez. Bu
belgeler eğitim setine girmez ama korpusta kalır; ileride taksonomi genişlerse
yeniden etiketlenebilir.

---

## Uygulama sırası (belirsizlik çıkarsa)

1. Sayfa bir ürün/kampanya sayfası mı? Değilse → `null`
2. Satılan ürün 8 sınıf dışında mı (BES, sigorta, çek/POS, kiralama)? → `null`
3. Sayfada birden çok ürün eşit ağırlıkta mı? → `null`
4. Ürün amaca bağlı finansman mı? → `Konut Finansmanı` / `Taşıt Finansmanı`
5. Ürün bireysel + genel amaçlı + vadeli + taksitli mi? → `İhtiyaç Finansmanı`
6. Ürün finansman ama (a) bireysel değil ya da (b) rotatif/vadesiz mi? → `Finansman`
7. Ürün tasarruf/yatırım (katılma hesabı / mevduat, altın, fon) mu? → `Yatırım Ürünü`
8. Teklif harcamaya bağlı puan/iade mi? → `Alışveriş Puanı`
9. Teklif kart edinimi ya da kart avantajı mı? → `Kart`
10. Teklifin kendisi müşteri kazanımı mı? → `Yeni Müşteri`

Sıra önemli: 2 ve 3 numaralı kapılar sınıf kapılarından ÖNCE gelir, çünkü
"hangi sınıf" sorusu ancak tek ve taksonomi-içi bir ürün varsa anlamlıdır.
