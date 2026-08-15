# Kılavuz Revizyon Önerisi — round1 κ sonrası

> Üretildi: 2026-08-15 · Tetikleyen: `iaa_report_round1.md` → Cohen κ = **0,274**
> Önceden ilan edilmiş eşik (ANNOTATION_GUIDE §7): κ < 0,67 → **zorunlu hakemlik
> + kılavuz revizyonu**.
>
> **Bu belge kılavuzu DEĞİŞTİRMEZ.** Öneridir; her madde ekip kararıyla
> `ANNOTATION_GUIDE.md`'ye girer ya da reddedilir. Kaynak: `uyusmazlik_kalibi.py`
> çıktısı (`../uyusmazlik_kaliplari_round1.md`) + gümüş etiketleme turunun
> etiketleyici notları (`../../silver/ROUND1-GUMUS.md`).

## Neden bu maddeler — iki BAĞIMSIZ kanıt

Aşağıdaki boşluklar iki ayrı yoldan, birbirini görmeden işaretlendi:

1. **İnsan anotatörler** (A ↔ B, 141 ortak karar, 56 uyuşmazlık)
2. **Gümüş etiketleyiciler** (10 ayrı oturum, 1.427 hücre) — hepsi "kararsız
   kaldığım vakalar" başlığı altında aynı yerleri saydı

Aynı yerde bağımsız tökezleme anotatör gürültüsü değil, **kılavuz kusurudur**
(§4.13 girişinin kendi ilkesi).

## Gold'u bozan uyuşmazlıkların alan dağılımı

56 uyuşmazlığın 46'sı iki farklı gold değeri üretiyor (10'u κ'yı düşürüp gold'u
bozmuyor). O 46'nın dağılımı:

| Alan | Adet | Pay |
|---|---:|---:|
| `campaign_type` | 15 | %33 |
| `vade_ay` | 13 | %28 |
| `kampanya_kosullari` | 6 | %13 |
| `masraf_durumu` | 4 | %9 |
| diğer 6 alan | 8 | %17 |

**İlk iki alan tek başına %61.** Revizyon buraya odaklanmalı; kalan alanlara
harcanan emek κ'yı kayda değer biçimde oynatmaz.

---

## Öneri 1 — `campaign_type`: 8 sınıfın HİYERARŞİSİ tanımlı değil

**Kanıt.** Dokuz gerçek anlam farkının hepsi aynı belirsizlikten çıkıyor:

| A dedi | B dedi |
|---|---|
| `Finansman` | `İhtiyaç Finansmanı` |
| `İhtiyaç Finansmanı` | `Finansman` |
| `Yatırım Ürünü` | `Finansman` |
| `Konut Finansmanı` | `Yatırım Ürünü` |
| `Kart` | `Alışveriş Puanı` |
| `Finansman` | `Taşıt Finansmanı` |

İlk iki satır **ters yönlerde aynı çift** — yani kimse tutarsız değil, kural
yok. `Finansman` bir **üst küme** mi (her finansman türü onu da sağlar), yoksa
"diğerlerine uymayanlar" kutusu mu? Kılavuz bunu hiç söylemiyor.

**Öneri.** `Finansman`ı açıkça **artık sınıf** ilan edin: belge konut/taşıt/
ihtiyaç ayrımını yapıyorsa o özel sınıf yazılır; yapmıyorsa (ya da birden çok
türü aynı anda sunuyorsa) `Finansman`. Karar ağacı tek cümleyle:

> Özel sınıf varsa özel sınıf; belge türü daraltmıyorsa `Finansman`.

Aynı ilke `Kart` ↔ `Alışveriş Puanı` için: kampanyanın **verdiği şey** puan/mil
ise `Alışveriş Puanı`, kartın kendisi ürünse `Kart`.

## Öneri 2 — Sekiz sınıfın hiçbiri uymadığında ne olur

**Kanıt.** Gümüş etiketleyicilerin en sık bildirdiği ikilem. Örnekler: tutar
cinsinden indirim kampanyası (200 TL indirim kodu), "Masrafsız Bankacılık"
paketi, emekli maaş promosyonu, ücretsiz dış ticaret paketi. Hepsinde **tek
özne var** — yani §4.13/1'in `absent`'ı uymuyor — ama sınıf yok.

**Öneri.** §4.13/1'e üçüncü satır ekleyin:

| Belge | `campaign_type` |
|---|---|
| Tek özneli gerçek kampanya, ama 8 sınıftan hiçbiri karşılamıyor | **`absent`** + `note: #sema_disi` |

`#sema_disi` etiketi taksonominin kendi eksiğini ölçülebilir kılar: bu etiket
sık çıkıyorsa sorun anotatörde değil, 8 sınıflı şemadadır.

## Öneri 3 — `vade_ay`: hangi sayı "bu kampanyanın vadesi"

**Kanıt.** 13 gold-bozan uyuşmazlığın 8'i "biri değer yazdı, diğeri yok dedi"
biçiminde. Gümüş turunda aynı kalıp bağımsız ölçüldü: mevzuat gereği konan
**örnek ödeme planındaki** ay (`3 ay vadeli 10.000 TL için örnek plan`), ürün
sayfasındaki **hesaplama aracının** varsayılanı (`TAŞIT FINANSMANI(1-48 AY)`),
ve erken kapama/tazminat kademelerindeki ay (`kalan vadesi 36 ayı aşan`) —
üçü de vade sanılıyor.

**Öneri.** §4'ün `vade_ay` maddesine öncelik sırası koyun:

1. Kampanyanın/ürünün **ilan ettiği** üst sınır (`36 aya varan vade`)
2. Yoksa ürün tablosunun en uzun kademesi
3. **Sayılmaz:** örnek ödeme planı, hesaplama aracı varsayılanı, erken
   kapama/tazminat kademesi, kefalet/bildirim süresi, çerez saklama süresi

## Öneri 4 — `kampanya_kosullari`: neyin koşul OLMADIĞI

**Kanıt.** Gümüş turunda tek başına **118 düzeltme** — bütün `fix`lerin yarısı.
Kalıp her oturumda aynı: blog/menü navigasyonu, SSS başlıkları, "Kampanyayı
Paylaş Facebook'da paylaş" bandı, ve yalnız tarih bildiren cümleler listeye
giriyor.

**Öneri.** Mevcut K1/K2/K3 kurallarına bir **dışlama listesi** ekleyin ve
`to_review_csv` üreticisinde de aynı süzgeci uygulayın — anotatöre hiç
gösterilmeyen kabuk, tartışılmaz.

## Öneri 5 — `hedef_kitle`: ticari/tüzel segment karşılığı YOK

**Kanıt.** Dört etiket (`yeni_musteri`, `mevcut_musteri`, `maas_musterisi`,
`belirli_segment`) bireysel müşteri niteliği üzerine kurulu. Gümüş turunda üç
ayrı oturum aynı boşluğu bildirdi: KOBİ'ye özel proje finansmanı, "tüzel
kişiliğe haiz müşteriler", turizm işletme belgesi olanlara özel ürün. Bir
oturum `belirli_segment` yazdı, bir diğeri `absent` — ikisi de kılavuza uygun.

**Öneri.** Ya beşinci etiket (`ticari_musteri`) ekleyin, ya da "ticari/tüzel
kısıt segment SAYILMAZ → `absent`" cümlesini açıkça yazın. Hangisi olduğu
önemli değil; **yazılı olmaması** κ'yı yiyor.

## Öneri 6 — Ücret tarifesi / sözleşme PDF'leri tek özne testinden geçer mi

**Kanıt.** Hem insan uyuşmazlıklarında (`albaraka--formlar-genel-kredi-
sozlesmesi`, `turkiye-emlak-katilim--qr-kredi-karti-uyelik-sozlesmesi`) hem
gümüş turunda tekrarlandı. Bu belgeler tek bir ürün adı ilan ediyor ("Ürünün
Adı/Tanımı: Ticari Finansman") ama kampanya değil, üstelik kural katmanı
tablolarından bol miktarda sahte değer üretiyor.

**Öneri.** §4.13/1'e açık bir satır: sözleşme / ücret tarifesi / bilgilendirme
formu → `#kampanya_disi`, 12 alan `absent`. Böylece hem κ'daki tekrar eden
çekişme biter hem bu belgeler halüsinasyon ölçümüne doğru katkı verir.

---

## Sonraki adım

Bu maddeler kabul edilirse κ **yeniden ölçülmelidir** — ama round1'in kendi
belgeleriyle değil. Aynı kişilere aynı belgeleri tekrar sormak hatırlama
etkisiyle şişmiş bir κ üretir (`_atama-round1-v2.md`'nin kendi gerekçesi).
Revizyondan sonra dağıtılacak yeni bir küme gerekir.
