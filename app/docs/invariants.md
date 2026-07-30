# Değişmez Denetimi — Etiketsiz Veride Otomatik Hata Avı

> **Durum:** çalışır. 291 gerçek banka belgesinde 0 ihlal.
> **Kod:** [`app/eval/properties.py`](../eval/properties.py) ·
> **Testler:** [`app/tests/test_properties.py`](../tests/test_properties.py)
> **Çalıştır:** `python -m eval.properties --raw-dir data/raw`

---

## Problem: hatalar çökmez, sessizce yanlış cevap verir

Bu projede bulunan hataların **hiçbiri** çökme değildi. Hepsi kendinden emin,
düzgün biçimli, **yanlış** değerler üretiyordu:

| Bulunan hata | Ne üretiyordu |
|---|---|
| `'ÜCRETSİZ'.lower()` → `'ücretsi̇z'` | "masrafsız" metnini **"masraf var"** okuyordu |
| `"1.500,00 TL"` | **1,0 TL** |
| `"%1,89 ile 120 aya kadar"` | kâr payı aralığı **%1,89–%120** |
| `"ücret alınmaz. Kampanya 31 Aralık"` | **31 TL** tahsis ücreti (tarihten) |
| `{"min": 1.89, "max": 1.89}` | karşılaştırmadan **düşüyor**, yanlış banka "en ucuz" |
| `"ev"` anahtar kelimesi | `"devam"`, `"seviye"` içinde eşleşiyor → korpusun **%48'i** sahte "Konut Finansmanı" |

Bir kullanıcı bunların hiçbirini fark edemez. Çıktı makul görünür. Karşılaştırma
tablosu dolu gelir. **Sadece yanlıştır.**

Bu proje için asıl risk "model yeterince iyi değil" değil,
**"sistem kendinden emin çöp üretiyor ve kimse fark etmiyor"**dur.

---

## Neden örnek tabanlı test yetmez

Klasik test "şu girdi → şu çıktı" der. Sorun: **yalnızca aklınıza gelen
vakaları** korur. Yukarıdaki altı hatanın hiçbiri aklımıza gelmemişti; test
fixture'ları küçük harfle yazıldığı için Türkçe büyük-harf hatası aylarca
görünmez kaldı.

Ayrıca gold set **insan işidir ve yavaştır**. 291 belge topladık ama 250'sini
anote edeceğiz; geri kalanı ve gelecekte toplanacak her belge etiketsiz kalacak.
Etiketsiz veride hata aramanın bir yolu gerekiyor.

---

## Çözüm: değişmezler

**Değişmez**, her girdi için doğru olması gereken bir özelliktir.
Kritik nokta: *doğru cevabı bilmeye gerek yoktur.*

> Girdinin **anlamını değiştirmeyen** bir dönüşüm çıktıyı **değiştiriyorsa**,
> ortada kesinlikle bir hata vardır.

Bu, gold etiketi olmadan hata bulmayı mümkün kılar.

### Uyguladığımız dört değişmez

**P1 — Kaynak bütünlüğü.**
Çıkarılan her değerin `span_start`/`span_end` offset'i, kaynak metinde
gerçekten o değeri göstermelidir.
*İhlal ne demek:* dashboard'da **yanlış yeri** vurgularız. Açıklanabilirlik
iddiamız bunun üzerine kurulu olduğu için sessizce yanlış olması özellikle
zararlıdır.

**P2 — Ortografik değişmezlik.**
`çıkar(metin) == çıkar(BÜYÜK_HARF(metin))`
Yazım biçimi bir değeri değiştirmemelidir. Banka başlıkları büyük harflidir.
*Yakaladığı hata:* Türkçe `.lower()` hatası — hem sınıflandırmayı tamamen
kaçırıyor hem `masraf_durumu`'nun **işaretini ters çeviriyordu**.

**P3 — Alakasız ekleme.**
Konuyla ilgisiz nötr bir cümle eklemek, hâlihazırda çıkarılmış değerleri
değiştirmemelidir.
*Yakaladığı hata:* bir alanın arama penceresi komşu cümleye taşıp oradan sayı
devşiriyordu — *"ücret alınmaz. Kampanya 31 Aralık 2026"* metninden **31 TL**
üretiliyordu.

**P4 — Cümle sırası değişmezliği.**
Cümlelerin sırası, tespit edilen **çelişki kümesini** değiştirmemelidir.
*Yakaladığı hata:* çelişki tespiti yazım sırasına bağlıydı —
`"masrafsız ... 500 TL"` yakalanıyor, `"500 TL ... masrafsız"` kaçıyordu.

---

## Gerçek veride ne buldu

291 gerçek banka belgesi üzerinde ilk koşu **134 ihlal** verdi ve hepsini
**tek bir alana** izole etti: `kampanya_kosullari`. Diğer 11 alan baştan
temizdi. İki gerçek hata çıktı:

**1. Çerez politikası "kampanya koşulu" sanılıyordu.**
Tetikleyici sözcükler (`zorunlu`, `gerekli`, `sadece`) KVKK aydınlatma ve
gizlilik metinlerinde de geçiyor. Belge başına ~8,7 "koşul" çıkıyordu ve çoğu
şuna benziyordu:

> *"bu çerezler zorunlu çerezler dışında kalan işlevsellikleri sağlama amacıyla
> kullanılmaktadır"*

Bu gold sete ve ürüne doğrudan çöp akıtırdı.

**2. Cümle bölücü, küçük harfle başlayan cümleleri kaçırıyordu.**

> *"...belirtilmesi gerekmektedir. www.ornek.com.tr sitesinden yapılan
> alışverişlerde geçerlidir."*

Bölücü nokta sonrası **büyük harf** arıyordu; `www` küçük olduğu için iki cümle
tek koşul olarak birleşiyordu.

Düzeltmelerden sonra: **134 → 43 → 15 → 0 ihlal.**

---

## Denetleyicinin kendisi de denetlenir

Her zaman geçen bir denetleyici işe yaramaz. `test_properties.py` içinde bir
**meta test** var: bilinen bir hata (`tr_fold` düzeltmesi) geçici olarak geri
alınır ve denetleyicinin **gerçekten ihlal ürettiği** doğrulanır.

```
[GEÇTİ] bozuk TR katlama ihlal üretir
        masraf_durumu: has_fee False -> True yakalandı
```

Bu test geçmezse, "0 ihlal" sonucu anlamsızdır. Denetleyicinin körelmediğini
garanti eden şey budur.

Denetleyicinin **kendi iki yanlış pozitifi** de bu süreçte bulundu ve
düzeltildi: nötr cümle eklenirken cümle ayrımı garanti edilmiyordu, ve serbest
metin alanlarında sondaki noktalama içerik farkı sanılıyordu. Bir ölçüm aracının
ölçtüğü şeyi bozmaması gerekir.

---

## Sürekli denetim

```bash
python -m eval.properties --raw-dir data/raw --out eval/reports/violations.jsonl
```

İhlal varsa **sıfırdan farklı çıkış kodu** döner — CI kapısı olarak kullanılır.
Yeni banka verisi eklendiğinde otomatik koşar; yeni belgeler hata ortaya
çıkarırsa anotasyondan **önce** yakalanır.

---

## Sınırları — dürüst değerlendirme

- Değişmez denetimi **doğruluğu ölçmez**, tutarsızlığı ölçer. Sistem tutarlı
  biçimde yanlış olabilir ve denetim sessiz kalır. Doğruluk için gold set şart.
- Yalnızca uyguladığımız dönüşümleri kapsar. Test edilmeyen bir dönüşümde hata
  olabilir.
- P3'ün nötr cümleleri elle seçilmiştir; gerçekten "alakasız" oldukları
  varsayımına dayanır.

Bu yüzden değişmez denetimi gold seti **ikame etmez**, onu **tamamlar**:
etiketsiz veride ucuz ve sürekli, gold sette pahalı ve kesin.

---

## Sources
- `raw/teknofest/2026-teknofest-tyda-sartname-2-senaryo.pdf` — §5.5, §5.6, §7
- `app/eval/properties.py`, `app/tests/test_properties.py`
- `log.md` — 2026-07-30 girdileri (ölçülen hata listesi)

## Related
- [[zor-anlama-vakalari-merkezi]] — zor vaka taksonomisi
- [[farkli-ifade-bicimleri]] — problem tanımı
- [[daraltilmis-yenilikcilik-hedefleri]] — açıklanabilirlik hedefleri
