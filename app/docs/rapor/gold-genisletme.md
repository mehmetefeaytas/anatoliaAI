# Ölçüm setini genişletme — n=20'den n=68'e

**Durum:** aday havuzu üretildi ve anotasyon koştu. Sonuç bölümü ölçüm
bittikçe doldurulur.

İlgili: `scripts/sample_gold_v2.py`, `data/gold/ANNOTATION_GUIDE.md`,
`docs/rapor/karar-bekleyenler.md` (K-1)

---

## Neden gerekliydi — üç somut kanıt

**1. Kararlar tek haneli sayılara dayanıyor.** K-1'de (çerçeve ayıklaması)
n-gram ile blok yaklaşımı arasındaki fark halüsinasyonda **5 kayıt**,
kaçırmada **2 alan**. F1 farkı 0,688 vs 0,687 — istatistiksel olarak yok.
Bu büyüklükte "kazanan" ilan etmek ölçüm değil, gürültü okumaktır.

**2. Gerçek bir hata sınıfı sette hiç iz bırakmadı.** Gecikme cezası
maddesinden kâr payı oranı çıkarma hatası, korpusta üretilen
`kar_payi_orani` kayıtlarının **%17,9'unu** etkiliyordu. Düzeltildikten
sonra gold mikro-F1'i **0,677'de sabit kaldı** — çünkü o 20 belgede tek bir
ceza maddesi yok. Ölçüm seti, sistemin en yaygın hatalarından birini
göremiyordu.

**3. Kapsama dar.** gold.v1: 7 banka, hepsi web sayfası, hiç PDF yok.
Korpusta 10 banka var; Ziraat Katılım (291 belge), Hayat Finans (48) ve
Adil Katılım (6) ölçümde **hiç temsil edilmiyordu**.

---

## Tasarım

### Örnekleme (`scripts/sample_gold_v2.py`)

- **48 yeni belge**, gold.v1'in 20'sine EK. Toplam **n=68** (3,4×).
- Tabakalı: 8 kampanya türü + sınıflandırılmamışlar; tür başına ~5 belge.
- Banka çeşitliliği gözetilir — **10 bankanın hepsi** temsil ediliyor.
- `content_hash` ile gold.v1'den ayrık: aynı belge iki kez ölçülmez.
- Kabuk belgeler elenir (uzunluk + sözcük çeşitliliği eşiği).
- **PDF yok.** Sözleşme PDF'leri farklı bir tür (akit, kampanya değil) ve
  alanların çoğu orada yapısal olarak yoktur. Karıştırmak iki seti
  kıyaslanamaz kılardı. Bu bir KAPSAM kararıdır; PDF'ler ayrı bir set
  olarak ele alınmalı (açık iş).
- Deterministik: sabit tohum (20260807) + kararlı sıralama.

### Anotasyon — dairesellik karşıtı protokol

Ölçüm setini sistemin çıktısına bakarak üretmek F1'i şişirir ve ölçümü
değersiz kılar. Bu yüzden anotasyon **kör** koştu:

| kural | gerekçe |
|---|---|
| `src/extraction/` okunmaz, koşulmaz | etiket sistemin kopyası olmasın |
| `preannotations*.json` değerlerine bakılmaz | aynı |
| her değer için **birebir alıntı** zorunlu (`field_spans`) | uydurmaya karşı mekanik koruma |
| alıntının metinde geçtiği programatik doğrulanır | iddia değil, kanıt |
| emin olunmayan alan hiçbir listeye girmez | tahmin metrik dışı |
| "yok" da bir karardır → `absent_fields` | halüsinasyon paydası |

Dört anotatör (M1–M4) ayrık 12'şer belge üzerinde bağımsız çalıştı.

### Statü — dürüstlük şartı

gold.v2 kayıtları `annotators: ["M1".."M4"]`, `adjudicated: false` taşır.
**gold.v1 ile aynı sayılmaz ve raporda birleştirilerek sunulmaz:**

- **gold.v1 (n=20)** — insan anotasyonlu, hakemlikten geçmiş. Birincil ölçüm.
- **gold.v2 (n=48)** — makine anotasyonlu, kanıt doğrulamalı, **insan
  hakemliği bekliyor**. İkincil / doğrulayıcı ölçüm.

Jüriye sunumda bu ayrım açıkça yazılır. İkisinin sonucu **aynı yönü**
gösteriyorsa bulgu güçlenir; **ayrışıyorsa** bu bir bulgudur ve saklanmaz.

κ (anotatörler arası uyum) için ikinci insan anotatör hâlâ gereklidir —
gold.v2 onun yerine geçmez, önceliğini artırır.

---

## Sonuçlar

Anotasyon bitti: **48 belge, 112 dolu alan, 444 "yok" kararı, 20 belirsiz
(%3,5)**. Üç kapı da geçti (şema, kanıt, ayrıklık). 40 belge `hard`.

### 1. Ana ölçüm — ve neden iki sayı bu kadar ayrışıyor

| ölçüm | gold.v1 (n=20) | gold.v2 (n=48) |
|---|---|---|
| kural / strict mikro-F1 | **0,677** | **0,387** |
| `kampanya_kosullari` hariç mikro-F1 | 0,660 | 0,536 |
| halüsinasyon | 0,096 [16/166] | **0,101 [45/444]** |

Farkın **yaklaşık %57'si tek bir alandan** geliyor: `kampanya_kosullari`
gold.v2'de **0/36/33** (TP/FP/FN), yani F1 = 0,000. 33 destekli vakada tek
bir isabet yok. Bu bir kabiliyet çöküşü değil — serbest metin **liste**
alanında birebir eşleşme.

**Kök neden protokol farkı.** `ANNOTATION_GUIDE.md` §3.1 birebir şöyle:

> "Boş bırakmak = `ok` = model doğru. Boş bırakınca *modelin bu satırdaki
> çıktısını onaylıyorum* demiş olursunuz."

Yani gold.v1, **modelin çıktısı çapa alınarak** etiketlendi. Anotatörün
itiraz etmediği her değer gold'a modelin yazdığı gibi girdi. Bu bilinçli ve
belgelenmiş bir tasarım (anotatör verimliliği) ama ölçülen skoru yukarı
çeker — özellikle "doğru cevap tek değil" tipindeki alanlarda.

gold.v2 **kör** etiketlendi. Serbest metin liste alanında iki bağımsız
seçimin birebir örtüşmesi zaten beklenmez; 0,000 bunu gösteriyor.

**Bu bir suçlama değil, bir kalibrasyon.** İki protokol iki farklı soruyu
ölçüyor:

- gold.v1 → *"model önerisini bir uzman onaylar mı?"*
- gold.v2 → *"model, bağımsız bir uzmanın vardığı sonuca varır mı?"*

İkincisi jürinin sorduğu sorudur. **0,677 tek başına sunulmamalıdır.**

### 2. Halüsinasyon — asıl güvenilir sayı

0,096 → **0,101**, üstelik payda **166'dan 444'e** çıkmışken. Yani
"uydurma oranı ~%10" bulgusu 2,7 kat daha fazla kararla **tekrarlandı**.
Bu, iki protokolden de bağımsız çıkan tek sayıdır ve raporlanabilir.

### 3. K-1 yeniden ölçümü — n=20'deki F1 kazancı GÜRÜLTÜYMÜŞ

Kural kolu / strict, aynı üç yapılandırma, n=20 ve n=48 yan yana:

| yapılandırma | F1 (n=20) | F1 (n=48) | halüsinasyon (n=20) | halüsinasyon (n=48) | kaçırma (n=48) |
|---|---|---|---|---|---|
| temel | 0,677 | **0,387** | 0,096 [16/166] | 0,101 [45/444] | 21 |
| n-gram | **0,688** | 0,369 | **0,066** | **0,070 [31/444]** | 33 |
| blok | 0,687 | 0,376 | 0,090 | 0,077 [34/444] | 29 |

%95 güven aralıkları (belge düzeyi bootstrap, 2000 örnek, seed=42):

| yapılandırma | mikro-F1 | %95 GA | genişlik |
|---|---|---|---|
| temel | 0,387 | [0,329–0,442] | 0,113 |
| n-gram | 0,369 | [0,304–0,427] | 0,123 |
| blok | 0,376 | [0,315–0,435] | 0,120 |

**Üç aralık da tamamen örtüşüyor** — F1 farkları istatistiksel olarak
ayırt edilemez. Karşılaştırma için n=20'deki aralık **[0,493–0,748]**,
yani genişlik **0,255**. n=48'de genişlik yarıya indi: ölçüm gerçekten
keskinleşti ve keskinleşince F1 farkının olmadığını gösterdi.

**Üç bulgu:**

1. **F1 kazancı yok oldu.** n=20'de iki temizleme kolu da temel çizginin
   ÜSTÜNDEYDİ (+0,011). n=48'de ikisi de ALTINDA (−0,018 ve −0,011).
   İşaret değişti — yani n=20'deki "kazanç" gürültüydü. Bu tam olarak
   K-1'de uyarılan kırılganlıktı ve geniş ölçüm onu doğruladı.

2. **Halüsinasyon azalması ise TEKRARLANDI.** n-gram göreli olarak
   n=20'de −%31, n=48'de −%31 (0,101 → 0,070). Aynı büyüklük, 2,7 kat
   fazla kararla. Bu artık gürültü değil.

3. **İki kolun sıralaması da tekrarlandı.** Her iki ölçekte de n-gram
   halüsinasyonda önde, blok kaçırmada önde. Ödünleşim gerçek ve kararlı.

**K-1 için sonuç:** karar F1'e bakılarak verilemez (fark yok, hatta hafif
negatif). Karar ödünleşimdir ve iki uç nettir:

- uydurmayı en aza indir → **n-gram** (halüsinasyon 0,070, bedeli 12 ek kaçırma)
- kapsamayı koru → **temel** (halüsinasyon 0,101, kaçırma 21)
- ortası → **blok** (0,077 / 29)

### 4. Anotasyon kılavuzunda 8 boşluk bulundu

Dört anotatör **bağımsız olarak** aynı belirsizlikleri işaretledi — bu,
anotatör gürültüsü değil kılavuz kusuru olduklarının kanıtıdır. En sık
üçü:

1. **Kampanya olmayan belgeler için sınıf yok.** Korpusta zekât hesaplama
   aracı, KVKK metni, kurumsal sayfa, kampanya LİSTESİ sayfaları var. 8
   sınıfın hiçbiri uymuyor; `null`'ın meşruluğu kılavuzda yazmıyor.
   gold.v2'nin **9 belgesi (%19)** bu durumda.
2. **Ürün kısıtı mı, müşteri segmenti mi?** "Yalnız Paraf kartlar" bir
   `hedef_kitle` değeri mi, koşul mu? Kural yok; dört anotatör de kendi
   kuralını koydu. `hedef_kitle` F1'i 0,727 → 0,267 düşüşünün muhtemel
   payı burada.
3. **Tutar cinsinden indirim** ("100 TL indirim") `indirim_orani`ya
   sığmıyor (yalnız yüzde), `odul_miktari` ise "ödül/hediye" tanımlı.

Kalan beşi: çok değerli `alisveris_puani` (sektöre göre farklı oranlar),
oransal tahsis ücreti (binde 5), `N/M` biçiminde kâr paylaşım oranı, gün
cinsinden vade, yan menü/"İlginizi çekebilir" bloğu kirliliği.

**κ ölçümünden önce kılavuz bu sekiz maddeyle güncellenmeli.** Aksi hâlde
düşük κ, anotatör uyumsuzluğu değil kılavuz belirsizliği ölçer.

---

## McNemar — eşleştirilmiş test (n=48)

Bootstrap güven aralığı farkın **büyüklüğünü** söyler; McNemar farkın
**yönünü** söyler. İkisi ayrı sorulardır ve aşağıda bir kez ayrışıyorlar.

Eşleştirme birimi `(doc_id, alan)`: iki kol aynı belgenin aynı alanında
doğru mu, yanlış mı. Üç çiftin de **556 kararı hizalandı, 0 kayıp** — yani
kollar aynı evreni ölçüyor. `b` = yalnız A'nın doğru bildiği, `c` = yalnız
B'nin. Uyumsuz çift sayısı 25'in altında kaldığı için üçünde de **tam
binom** kullanıldı (`eval/stats.py:310`), χ² yaklaşımına düşülmedi.

| A ↔ B | karar doğruluğu (A / B) | eşleşmiş fark %95 GA | b | c | uyumsuz | p | sonuç |
|---|---|---|---|---|---|---|---|
| temel ↔ **n-gram** | 0,804 / 0,817 | −0,013 [−0,025 – 0,000] | 8 | 15 | 23 | 0,21 | anlamsız |
| temel ↔ **blok** | 0,804 / 0,815 | **−0,011 [−0,020 – −0,002]** | 5 | 11 | 16 | 0,21 | anlamsız |
| n-gram ↔ blok | 0,817 / 0,815 | +0,002 [−0,009 – 0,013] | 5 | 4 | 9 | 1,00 | anlamsız |

`tolerant` eşleştiricide üç satır da aynı kalıyor (±0,001) — sonuç
eşleştirici seçimine duyarlı değil.

> **n=48 uyarısı.** Bu bir sıralama sinyalidir, kesin performans ölçüsü
> değil. Kararların çoğu "alan yok" kararıdır; karar doğruluğu bu yüzden
> mikro-F1'den yüksektir ve ikisi **kıyaslanamaz**.

### İki ölçütün ayrıştığı yer — temel ↔ blok

Tek ilginç satır bu: bootstrap fark aralığı **sıfırı dışlıyor** (−0,020 –
−0,002) ama McNemar **anlamsız** diyor (p = 0,21). Çelişki değil, iki
ölçütün farklı şeye bakması:

- **Bootstrap** belgeleri yeniden örnekler. Blok kolunun üstünlüğü 48
  belgenin geneline **tutarlı biçimde** yayılmışsa, aralık dar çıkar ve
  sıfırı dışlar.
- **McNemar** yalnız **uyumsuz** kararları sayar — burada 16 tane. 16 çiftte
  11'e 5 bölünme tam binomda p = 0,21 verir; bu örneklem büyüklüğünde
  ayrımı ilan edecek güç yoktur.

Okunuşu: **etki küçük ve tutarlı, ama uyumsuz karar sayısı onu ilan etmeye
yetmiyor.** Yalnız bootstrap'a bakıp "blok kazandı" demek, ölçümün
söylemediği bir şeyi söylemek olurdu. İki ölçütü birlikte raporlamamızın
sebebi tam olarak bu.

### Bu ölçüm neden yapıldı

Kullanıcı kararı: **çerçeve ayıklaması çıkarımda uygulanmayacak.** Ayıklama
kaçırmayı artırıyor (temel 21 → n-gram 33, blok 29) ve F1 kazancı yok.
Ayıklama bunun yerine **sunum katmanına** taşındı: metnin gösterildiği
yerlerde çerçeve katlanıyor, silinmiyor (bkz. `src/preprocessing/blocks.py`
ve `/campaigns/{id}/text` uç noktası).

Yani bu tablo bir kol seçmek için değil, **"neden ayıklama yapmıyoruz"
sorusunun ölçülmüş cevabını** kayda geçirmek için. Üç çiftin hiçbirinde
anlamlı fark yok; ayıklamanın çıkarım tarafında bedeli var, kazancı yok.

Tekrar üretim:

```bash
.venv/bin/python -m scripts.mcnemar_report \
  --a eval/reports/<temel> --b eval/reports/<n-gram> \
  --ad-a temel --ad-b n-gram --resamples 2000
```

---

## Bulunan ve düzeltilen bir ölçüm kusuru

İlk koşuda n-gram kolu temel kolla **birebir aynı sayıyı** verdi. Sebep
`sample_gold_v2`nin kimliği `abs(hash(url))` ile üretmesiydi:

- `hash()` string'lerde süreç başına rastgeledir (`PYTHONHASHSEED`) — yani
  "deterministik örnekleme" iddiası yanlıştı;
- `boilerplate_audit.clean_gold` gold kaydını korpustaki grubuna **`id`
  üzerinden** bağlar. Uydurma kimlik hiçbir gruba oturmadığı için çerçeve
  ayıklaması **0/48 belgeye** uygulandı.

Kusur "hata" olarak değil, **"fark yok" sonucu** olarak görünüyordu — bu
projede avlanan sessiz yanlış rapor sınıfının bir örneği daha. Kimlik
kuralı `split_trainable.iter_docs` ile aynı hâle getirildi
(`<banka>--<dosya adı>`); düzeltmeden sonra n-gram 44/48 belgeyi
temizliyor (karakterlerin %42'si).

---

## Tekrar üretim

```bash
.venv/bin/python -m scripts.build_demo_db --out data/demo.db --force
.venv/bin/python -m scripts.sample_gold_v2 --n 48 --parcala 4
# anotasyon -> data/gold/parca/etiket-*.json
.venv/bin/python -m eval.run_eval --gold data/gold/gold.v2.json --config kural
```
