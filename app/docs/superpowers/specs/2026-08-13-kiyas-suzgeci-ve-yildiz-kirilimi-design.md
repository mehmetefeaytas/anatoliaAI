# Kıyas süzgeci budaması + yıldız kırılımı — tasarım

> Tarih: 2026-08-13 · Durum: onaylandı (kullanıcı, 13 Ağustos)
> Kapsam: `app/web` arayüzü. Sunucu tarafında **değişiklik yok**.

İki bağımsız iş tek belgede toplanıyor çünkü ikisi de aynı kusurun iki yüzü:
**ekran, ölçemediği şeyi ölçmüş gibi gösteriyor.** Süzgeç hiç sonuç vermeyecek
bir seçeneği sunuyor; yıldız, ağırlık tablosunun beşte birinden gelen bir puanı
beş yıldız diye basıyor.

---

## A) Karşılaştırma — kampanya türü süzgeci alana göre budanır

### Sorun

`ComparePanel` süzgeci `stats.campaign_types`ten gelen **8 türün tamamını** her
alan için basıyor. Oysa tür kapsaması alandan alana değişiyor — ölçüldü
(13 Ağustos, `data/demo.db`, 1.774 belge):

| alan | veri taşıyan tür | boş dönen tür |
|---|---|---|
| `kar_payi_orani` | 7 | 1 (Alışveriş Puanı) |
| `tahsis_ucreti` | 4 | 4 (Alışveriş Puanı · Finansman · Yeni Müşteri · İhtiyaç Finansmanı) |
| `alisveris_puani` | 8 | 0 |

`tahsis_ucreti` + `Finansman` seçen kullanıcı boş bir ekran alıyor ve "veri mi
yok, sistem mi bozuk" sorusuyla baş başa kalıyor.

### Karar

Süzgeç **seçili alanda veri taşıyan** türleri listeler. Alan değişince liste
yeniden hesaplanır.

Reddedilen iki seçenek:

- **Korpusa göre sabit budama** — liste kararlı kalırdı ama `tahsis_ucreti` +
  `Alışveriş Puanı` gibi boş kombinasyonlar yine listede kalırdı; sorunu
  çözmüyor.
- **Görünür kalsın, pasif olsun** — projenin "boşluğu gizleme, say" doktrinine
  en sadık seçenek, ama istenen sadeleşmeyi vermiyor. Doktrin bunun yerine
  aşağıdaki *düşen türler* satırıyla korunuyor.

### Veri yolu

`ComparePanel`'e ikinci bir sorgu eklenir; **yalnız seçenek listesini** üretir:

```ts
const turKaynagi = useAsync(
  () => api.compare(field, undefined, undefined, "best"),
  [field],
);
```

Bağımlılık dizisi yalnız `field`. Gerekçe ölçüldü: `intent` sıralama
değiştirir, satır kümesini değil; `per_bank` ise `best` ve `all` hâllerinde
**aynı tür kümesini** döndürüyor (`best`, banka+tür çifti başına en iyi satırı
tutuyor, türü düşürmüyor).

Tabloyu besleyen mevcut sorgu **olduğu gibi kalır**. İstemci tarafı süzme
denendi ve reddedildi: satır kümesi aynı çıkıyor ama sunucunun döndürdüğü
`rank` değerleri farklı oluyor (sunucu süzülmüş küme üzerinden numaralıyor —
ölçüldü: `kar_payi_orani` + `Kart`, Kuveyt Türk `rank` 3 yerine 5). Ekranda
`turlereBol()` sırayı zaten bölüm içinde yeniden verdiği için görünür sonuç
değişmezdi, ama bu istenmemiş bir davranış değişikliği olurdu.

### Görünen davranış

1. **Budama sessiz değildir.** Süzgecin altında küçük bir satır düşen türleri
   adıyla sayar:

   > 4 tür bu alanda veri taşımıyor, listeden düştü: Alışveriş Puanı ·
   > Finansman · Yeni Müşteri · İhtiyaç Finansmanı

   Hiç tür düşmediyse satır basılmaz.

2. **Seçili tür düşerse süzgeç `Tümü`ne döner ve bunu yazar.** Kullanıcı "Kart"
   seçiliyken veri taşımayan bir alana geçtiğinde boş ekran görmez:

   > «Kart» bu alanda veri taşımıyor; süzgeç Tümü'ne alındı.

   Uyarı bir sonraki kullanıcı etkileşimine kadar durur.

3. **Ölçemediğimizde budama yapılmaz.** `turKaynagi` yüklenirken ya da hata
   verdiğinde **tam liste** basılır. Ölçülemeyen bir yokluğu yokluk gibi
   göstermek bu ekranın reddettiği hatanın ta kendisi.

4. Kanonik sıra korunur: liste `campaignTypes` propunun sırasından süzülür,
   yanıttan yeniden üretilmez.

### Kapsam sınırı

Yalnız `ComparePanel`'in kampanya türü süzgeci. **Alan çipleri budanmaz** —
`FieldChips` başlığındaki "12 alanın 12'si her hâlde basılır, boş olan
gizlenmez" vaadi bağlayıcıdır. `BankaSayfasi`, `BankDeltaPanel` ve
`AdvantageousPanel` bu turda dokunulmadan kalır.

---

## B) Banka Sayfası — yıldızın kırılımı

### Sorun

`YildizPuan` bugün yıldızın yanına yalnız şunu yazıyor: *"Dolu ölçütler: … Bu
belgelerde geçmeyen: …"*. Hangi ölçütün ne kadar katkı verdiği, skorun hangi
payda üzerinden ortalandığı ve **ağırlık tablosunun ne kadarının hiç
ölçülemediği** görünmüyor.

Ölçülmüş örnek (13 Ağustos, `/advantageous`, Kuveyt Türk · Alışveriş Puanı,
`campaign_id` 317): `score` **1,00 → 5 yıldız**, ama `coverage` **0,571** ve
bileşen listesinde 5 ölçütten yalnız 2'si var. O beş yıldız, ağırlık
tablosunun **tek bir %20'lik kaleminden** (masraf durumu) geliyor.

### Formül — kaynaktan doğrulandı

`src/comparison/compare.py:934-981`. Üç ayrı payda var:

1. **`active`** — tür grubunda *hiçbir* kampanyanın değer taşımadığı ölçüt
   baştan devre dışı kalır; `total_active` = aktif ağırlıkların toplamı.
   Alışveriş Puanı grubunda: 0,20 + 0,15 = **0,35** (kâr payı 0,40 · vade 0,15 ·
   finansman tutarı 0,10 hiç aktif değil).
2. **`coverage = covered_w / total_active`** — bu kampanyanın değer taşıdığı
   aktif ağırlık oranı. Örnekte 0,20 / 0,35 = **0,571**.
3. **`score = total / covered_w`** — skor yalnız **kapsanan** ağırlık üzerinden
   ortalanır. Örnekte 0,20 / 0,20 = **1,00**.

`comparable = coverage >= 0.5 and score is not None`.

### Karar

`YildizPuan` içine katlanmış bir `<details>`: **"bu yıldız nasıl hesaplandı"**.

Tablo sütunları: **ölçüt · ham değer · normalize (tür içi sıra) · ağırlık ·
katkı · not**. Satırlar `skor.components`ten gelir; bileşen listesi zaten
ağırlığa göre sıralı (`components.sort(key=lambda c: -c.weight)`).

Tablonun altında üç payda, üçü de veriden türetilir:

| satır | örnek |
|---|---|
| türde hiç ölçülemeyen ölçütler | 5 ölçütten 3'ü — ağırlığın **%65'i** baştan devre dışı: kâr payı oranı · vade · finansman tutarı |
| bu kampanyada boş kalan aktif ölçüt | ödül miktarı (0,15) → kapsama **%57** |
| skor | yalnız kapsanan ağırlık üzerinden: 0,20 / 0,20 = **1,00 → 5 yıldız** |

İlk satır `/advantageous.weights` ile `skor.components` farkından hesaplanır:
ağırlık tablosunda olup bileşenlerde geçmeyen alanlar. Hiçbir alan adı arayüze
sabit yazılmaz; etiketler `weights[].field_name` üzerinden `FieldMeta`
sözlüğünden okunur.

### Sınırlar

- **Yıldızsız satırda kırılım basılmaz.** Ölçülemeyen tür için açılacak bir
  hesap yok; `<details>` hiç çizilmez. `YildizPuan`ın "boş yıldız basılmaz"
  kuralının kırılım karşılığı.
- **Yeni uç gerekmiyor.** `/advantageous` `components` dizisinde `value`,
  `normalized`, `weight`, `contribution`, `note` alanlarının beşini de
  döndürüyor — doğrulandı.
- **Varsayılan kapalı.** Sayfada 9 tür satırı var; hepsi açık gelirse ekran
  hesap tablosuna döner. Yıldız özet, kırılım kanıttır.
- `<details>` yerel durum tutar; sayfa genelinde "hepsini aç" düğmesi bu turda
  **yok** (YAGNI).

### Erişilebilirlik

`YildizPuan`ın mevcut kuralı korunur: yıldız dizisi `aria-hidden`, gerçek değer
metinde. Kırılım tablosu gerçek bir `<table>`.

`<summary>` katlanmış hâlde de bilgi taşır ve **iki sayı birden** verir, çünkü
"aktif" ile "kapsanan" ayrı şeylerdir (bkz. formül): ağırlık tablosundaki toplam
ölçüt sayısı ve bu kampanyada değer taşıyan (`normalized !== null`) ölçüt
sayısı. Örnekte:

> 5 ölçütün 1'i bu kampanyada ölçüldü — hesabı aç

---

## Test

- **A:** düşen tür listesi doğru mu; seçili tür düşünce `Tümü`ne dönüyor mu;
  `turKaynagi` hata verdiğinde tam liste basılıyor mu.
- **B:** kırılım toplamı `score` ile tutuyor mu; "türde hiç ölçülemeyen"
  kümesi `weights` − `components` farkına eşit mi; skorsuz satırda `<details>`
  basılmıyor mu.

Testler `web/tests/` altına, `node --test` ile (`npm run test`).

## Dokunulacak dosyalar

| dosya | değişiklik |
|---|---|
| `web/app/components/ComparePanel.tsx` | seçenek sorgusu, budama, düşen tür satırı, tür geri alma |
| `web/app/components/YildizPuan.tsx` | `<details>` kırılımı + `weights` propu |
| `web/app/components/BankaSayfasi.tsx` | `weights`i `YildizPuan`a geçir |
| `web/app/styles/banka.css` | kırılım tablosu biçimi |
| `web/tests/` | yeni testler |
