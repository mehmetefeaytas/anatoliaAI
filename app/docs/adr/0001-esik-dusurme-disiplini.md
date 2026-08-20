# ADR-0001 · Bir regresyon eşiği ancak ÖLÇÜT KUSURU kanıtlanırsa düşürülebilir

| | |
|---|---|
| durum | **kabul** |
| tarih | 2026-08-20 |
| karar veren | ölçüm sahibi (teknik yazar/denetçi) + gold sahibi — **iki ayrı imza** |
| kapsam | `eval/esikler.json`, `eval/esikler-round1.json`, `scripts/kanit_tazeligi.py`, `docs/rapor/olcumler.md` |
| ilgili | [`ANNOTATION_GUIDE.md`](../../ANNOTATION_GUIDE.md) §7 · [`docs/rapor/ablasyon.md`](../rapor/ablasyon.md) · vault `decisions/` |

---

## Bağlam

`eval/esikler*.json` bir **hedef listesi değil, gerileme (regresyon)
kapısıdır**: değerler ölçülmüş mevcut başarımın hemen altındadır ve anlamı
"daha iyisini yap" değil, **"bugünkünü kaybetme"**dir.

Böyle bir kapının tek düşmanı, kapının **sonuca bakılarak** gevşetilmesidir.
`ANNOTATION_GUIDE.md` §7 bunu anotasyon başlamadan yasakladı ve proje o yasağı
bir kez uyguladı: round0'da κ = 0,302 ölçüldüğünde eşik değiştirilmedi, ilan
edilmiş sonuç (zorunlu hakemlik + kılavuz revizyonu) uygulandı.

**20 Ağustos 2026'da iki eşik bilerek düşürüldü.** İkisinin de gerekçesi
`eval/esikler-round1.json` içinde ayrıntılı yazılıydı — ama **gömülü**ydü: o
dosyayı açmayan biri yalnız düşmüş sayıyı görüyordu. Gerekçenin görünmez
olması, meşru bir hamleyi meşru olmayanından ayırt edilemez kılar. Bu ADR o
ayrımı dışa taşımak için var.

### Düşürülen iki eşik (ölçüm künyeleriyle)

**1. `kampanya_kosullari` — `alanlar`dan `alanlar_kalem`e taşındı.**

| | ikili F1 | kalem F1 |
|---|---|---|
| önce (commit `d9c0444` öncesi) | 0,847 | 0,409 |
| sonra | **0,143** | **0,429** |

Aynı gold, aynı değişiklik: ikili ölçüt **düştü**, kalem ölçütü **yükseldi**.
Motor özde kötüleşmedi; kalemleri farklı böldü ve tümü-ya-hiç ölçütü bunu
tamamen kayıp saydı. Aynı desen `gold.v2`'de daha keskin görünüyor: 20 Ağustos
koşumunda **137 kalemin 78'i doğru** çıkarılmasına rağmen **hiçbir kayıt**
birebir küme eşleşmesi vermedi → ikili F1 **0,000**, kalem F1 **0,520**.

**2. `odul_miktari` — 0,490 → 0,390** (ölçülen 0,400).

HAKEM-04 turu, kılavuz §4'ün chip-para/ADET kuralı gereği bir ParafPara
ödülünün `odul_miktari` değil `alisveris_puani` olduğunu tespit etti; o kaydın
desteği `absent_fields`e taşındı ve **kalan destek 1'e düştü**. Destek 1'de F1
anlamsıza yakındır — tek bir kararın yönü metriği 0'dan 1'e taşır.

---

## Karar

Bir regresyon eşiği **yalnız ölçütün o alanda kusurlu olduğu gösterildiğinde**
düşürülebilir; başarımın düşmesi **hiçbir zaman** yeterli gerekçe değildir.

Düşürme talebi şu **dört kapıyı birlikte** geçmek zorundadır. Biri
karşılanmıyorsa cevap "hayır"dır ve doğru hamle motoru onarmaktır.

| # | kapı | ne kanıtlanmalı |
|---|---|---|
| **K1** | **Ölçüt kusuru, başarım kusuru değil** | Aynı değişiklik **başka bir ölçütte iyileşme** ya da en az kararlılık göstermeli. Tek yönlü düşüş = motor sorunu. |
| **K2** | **Mekanizma yazılı** | Ölçütün niçin bu alanda bozuk olduğu **kodla** gösterilmeli (ör. `eval/matchers.py` küme eşitliği). "Bence sert" gerekçe değil. |
| **K3** | **Bağımsız hakem turu** | Etiketlerin kendisi denetlenmiş olmalı. Kaç kayıt korundu / düzeltildi / çelişkili bırakıldı **sayıyla** yazılmalı. |
| **K4** | **Eski sayı yayımda kalır** | Düşen değer **silinmez**; yeni değerle yan yana durur. Düşürme "gevşetme" olarak **adlandırılır**. |

### Kim onaylar

**İki imza, tek kişi değil.** Eşiği düşürme talebi ölçüm sahibinden gelirse
gold sahibi onaylar, tersi de geçerlidir. Gerekçe her hâlde bir ADR'ye ya da
mevcut bir ADR'nin ekine yazılır; onay **yazılı olmadan geçerli değildir**.

### Ne yapılmayacağı — bu kararın asıl yükü

| yasak | niçin |
|---|---|
| Halüsinasyon tavanını gevşetmek | `gold.v2`'nin `halusinasyon_ust_sinir: 0.08` değeri **önceden ilan edilmiştir**. round1'de aynı oran 0,433'e fırlıyor ama bu bir **seçim etkisidir** (payda 444 → 60, `absent` kümesi düşmanca seçilmiş). O sayıya bakıp tavanı gevşetmek §7'nin yasakladığı şeyin ta kendisidir. Tavan `gold.v2`'de kalır. |
| Manşet ölçütü sonradan değiştirmek | "İkili düştü, artık kalem manşet olsun" **yapılmadı**. Üç görünüm (ikili · kalem · yapısal) birlikte yayımlanmaya devam ediyor; hiçbiri diğerinin yerine geçmez. |
| Alanı listeden çıkarmak | `masraf_durumu` round1'de gerçekten 0,000 (destek 5, TP 0). Eşik 0,000 yazılıyor — kapı o alanda etkisiz ama **sessiz değil**: satır listede duruyor ve okuyan sıfırı görüyor. |
| Tutulmayan hedefi indirmek | 12-alan ikili mikro-F1 **0,5702**, ilan edilen 0,60 hedefinin altında. Hedef indirilmedi; **tutulmadığı yazıldı**. |

---

## Gerekçe

**Niçin "ölçüt kusuru" ölçütü seçildi.** Bir eşiği düşürmenin iki olası nedeni
vardır: (a) sistem kötüleşti, (b) ölçüt o alanda yanlış şeyi ölçüyor. Yalnız
(b) meşrudur, çünkü (a)'da eşiğin işi tam olarak alarm çalmaktır. İkisini
ayıran tek gözlemlenebilir işaret, **aynı değişikliğin farklı ölçütlerde ters
yönde hareket etmesidir** — K1 bunu şarta bağlıyor.

**Niçin iki imza.** Eşiği düşürmek, ölçüm sahibinin kendi ölçümünü kolaylaştıran
bir hamledir; tek imza bunu yapısal olarak kontrolsüz bırakır. Aynı asimetri
`orkestrasyon` kararında da tanımlıydı (ajan önerir, hakem yalnız reddeder) ve
aynı gerekçeyle burada tekrarlanıyor.

**Niçin eski sayı kalıyor.** Bu deponun tek farklılaştırıcısı ölçüm
dürüstlüğüdür. Düşen bir sayıyı silmek, o sayıyı kaybetmekten daha pahalıdır:
biri metrik, öteki güven.

**Alternatif ve niçin reddedildi.** *"Eşikleri hiç düşürmeyelim; ölçüt bozuksa
ölçütü değiştirelim."* Doğru uzun vadeli çözüm bu ve açık iş olarak kayıtlı
(iki gold setini tek kanonik sözleşmede birleştirmek). Ama kalıcı çözüm
gelene kadar kapı ya sürekli kırmızı yanar ve kapatılır, ya alanı hiç
denetlemez. Üçüncü yol — **eşiği düşür, gerekçeyi ve eski sayıyı yayımla** —
kapıyı çalışır tutuyor.

---

## Sonuçlar

**Kabul edilen bedel.** `kampanya_kosullari` alanında CI'ı kırma yetkisi ikili
ölçütten kalem ölçütüne devredildi. Yani o alanda ikili başarım çökerse kapı
**sessiz kalır**. Bu bilinçli bir açıktır ve `esikler-round1.json` içinde
"geçici" olarak adlandırılmıştır.

**`odul_miktari` için.** Eşik artık bir başarım ölçüsü değil, yalnız "bu alan
tamamen çökmedi" kapısıdır. Destek 1'de sayıya anlam yüklenmemelidir; kalıcı
çözüm desteği büyütmektir.

**Kapsam sınırı — bu ADR bir kez kullanılmak üzere yazıldı.** İki eşik
düşürüldü, ikisinin de gerekçesi yukarıda. Üçüncü bir düşürme talebi geldiğinde
bu ADR **gerekçe değildir**; yeni talep dört kapıyı kendi kanıtıyla yeniden
geçmek zorundadır. Bir ADR emsal değil, kayıttır.

**Açık iş.** K1–K4 şu an **insan disiplini**yle uygulanıyor; makine
denetiminde değil. Doğru sonraki adım, `esikler*.json` içindeki her düşürülmüş
eşiğin bir ADR'ye link taşımasını zorunlu kılan bir kapıdır — o kapı
yazılmadığı sürece bu ADR unutulabilir.

---

## Doğrulama

```bash
cd app

# 1) İki kapının ikisi de hâlâ koşuyor mu (eşikler etkin mi)
.venv/bin/python -m eval.run_eval --gold data/gold/gold.v2.json \
    --matcher strict --esikler eval/esikler.json
.venv/bin/python -m eval.run_eval --gold data/gold/gold.round1.json \
    --matcher strict --esikler eval/esikler-round1.json

# 2) Halüsinasyon tavanı gold.v2'de mi, round1'de değil mi (yasağın kendisi)
#    `grep` KULLANMAYIN: round1 dosyası bu anahtarı METİN olarak anıyor
#    (`_halusinasyon_neden_YOK` gerekçesinde) ama ANAHTAR olarak taşımıyor.
#    Aradaki fark tam olarak bu ADR'nin konusu, o yüzden JSON okunur:
.venv/bin/python -c "
import json
for f in ('eval/esikler.json','eval/esikler-round1.json'):
    d = json.load(open(f))
    print(f, 'halusinasyon_ust_sinir' in d, d.get('halusinasyon_ust_sinir'))"
# -> eval/esikler.json True 0.08
# -> eval/esikler-round1.json False None

# 3) kampanya_kosullari kalem kapısında, ikili sayısı yayımda mı
grep -n "alanlar_kalem" -A 2 eval/esikler-round1.json

# 4) Yayımlanan hiçbir sayı kanıtından sapmıyor mu
.venv/bin/python -m scripts.kanit_tazeligi
```

**Ölçülen (2026-08-20):** `kanit_tazeligi` → **14 iddia · 0 sapma**. Kalan
"kanıt eksik" satırları kirli ağaç kaynaklıdır ve teslim öncesi temiz ağaçta
tekrarlanacaktır.
