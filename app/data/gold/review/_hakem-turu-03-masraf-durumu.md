# Hakem turu 03 — `masraf_durumu` (negatif κ'nın kaynağı)

**Tarih:** 2026-08-19
**Tetikleyen:** κ turu (`_kappa-ikinci-tur.md`) `masraf_durumu` alanında
**negatif κ (-0,103)** ölçtü. Gözlenen uyum 12/16 olmasına rağmen κ'nın sıfırın
altına düşmesi, anlaşmazlığın **sistematik** olduğunu söyler: iki etiketleyici
aynı belgelerde ters yönde karar veriyor. Kılavuzun eşik tablosu (§7) bu durumu
"hakemlik" olarak işaretliyor.
**Hakem:** LLM (bu oturum). İnsan hakem değildir ve rapor bunu saklamıyor.
**Kapsam:** yalnız 4 uyuşmazlık. Uyuşan 12 karar yeniden açılmadı.

## Karar tablosu

| Belge | İnsan (M-turu) | LLM-01 | Hakem | Sonuç |
|---|---|---|---|---|
| `vakif-katilim--hesaplar-ozel-cari-hesaplar` | `has_fee:false, amount:0` | — | **insan** | onaylandı |
| `adil-katilim--…-urun-ve-hizmetler` | — | `has_fee:false, amount:0` | **insan** | onaylandı |
| `hayat-finans--…-gastroclub-ayricaliklari` | `has_fee:false, amount:0` | — | **LLM** | gold DÜZELTİLDİ |
| `hayat-finans--…-hisse-senedi-islemleri` | `has_fee:true, amount:null` | — | **insan** | onaylandı |

## Vaka gerekçeleri

### 1. Vakıf Katılım — özel cari hesap → İNSAN DOĞRU

Metin: *"Vakıf Katılım'dan açtıracağınız hesaplardan hesap işletim ücreti
**alınmamaktadır**."* Kılavuz §4'ün "NEGASYON KRİTİK" kuralı birebir bu vakayı
tanımlıyor: *"ücret alınmaz" bilgi eksikliği DEĞİLDİR, masrafın sıfır olduğunun
pozitif ifadesidir.* Kanıt penceresi de gold'da duruyor. LLM alanı kaçırdı.

### 2. Adil Katılım — ürün ve hizmetler → İNSAN DOĞRU, LLM HALÜSİNASYON

Belgede `masraf|ücret|komisyon|tahsis|bedel|kesinti` geçen **sıfır** cümle var.
İnsan alanı `absent` bıraktı; LLM `has_fee:false, amount:0` üretti — yani
metinde dayanağı olmayan bir değer.

Bu, κ turunun en önemli tek bulgusudur: ikinci etiketleyicinin kararları
otomatik olarak "bağımsız ikinci görüş" sayılamaz, çünkü bu vakada üretilen şey
görüş değil **uydurma**. CLAUDE.md §21'in "eksik bilgiyi doldurmak için değer
uydurmak" yasağı burada gold'un LEHİNE çalıştı: insan turu doğru, model yanlış.

### 3. Hayat Finans — GastroClub → LLM DOĞRU, GOLD DÜZELTİLDİ

Metin: *"GastroClub üyeliği şimdi Hayat Finans müşterilerine özel ve
**ücretsiz**!"* İnsan bunu §4'ün negasyon kuralıyla `has_fee:false` yazdı ve
kural metnine bakılırsa **haklıydı** — kural "ücretsiz" gördüğü her yerde
sıfır masraf diyor.

Kusur kuralın kendisindeydi: kapsamı yoktu. `masraf_durumu`'nun ürün
yüzeyindeki işi *"bu kampanyayı/ürünü alırsam ne kadar masraf öderim"*
sorusunu yanıtlamaktır. GastroClub üçüncü taraf bir avantaj programıdır;
üyelik bedelinin sıfır olması finansman ya da hesap maliyeti hakkında hiçbir
şey söylemez. Ölçülen etki: belge `/compare?field=masraf_durumu` tablosunda
**"masrafsız" rozetiyle** görünüyordu, yani ürün yüzeyinde yanlış bir iddiaya
dönüşmüştü.

Karar: değer `absent_fields`'a taşındı, `notes` gerekçeyi taşıyor ve kılavuz
§4'e **kapsam kuralı** eklendi (sayılır: dosya masrafı, tahsis ücreti, hesap
işletim ücreti, işlem komisyonu; sayılmaz: üçüncü taraf avantaj programı
üyeliği → `kampanya_kosullari`).

### 4. Hayat Finans — hisse senedi işlemleri → İNSAN DOĞRU

Metin: *"Komisyon oranı: 0,002 (binde 2)"*. Kılavuz §4.13 tam bu biçimi
düzenliyor: masraf VARDIR ama tutarı TL olarak yazılı değildir →
`has_fee:true, amount:null`. Tutarı finansman tutarıyla çarpıp TL yazmak
"çıkarım değil türetme" olurdu. İnsan turu kurala birebir uymuş; LLM alanı
kaçırdı.

## Negatif κ'nın açıklaması

κ raporu değer uyumu düşüklüğü için *"sebebi 'gold tutarsız' mı 'ikinci yargıç
yetersiz' mi ayırt edilemez"* diyordu. Bu alan için ayrım **yapıldı**:

* 3/4 vakada gold doğru; LLM ikisinde alanı kaçırdı, birinde **uydurdu**.
* 1/4 vakada gold yanlıştı ama sebebi anotatör hatası değil **kılavuz
  kapsamının eksikliğiydi** — kural yazıldığı gibi uygulanmış, kural eksikti.

Yani `masraf_durumu`'ndaki negatif κ bir gold güvenilirliği sorunu değil, bir
**tanım sorunu + zayıf ikinci yargıç** bileşimidir. Kapsam kuralı yazıldıktan
sonra aynı turun tekrarı bu alanda daha yüksek κ vermelidir; `colab/03_kappa.py`
ile `qwen3` ailesinden daha güçlü bir modelle tekrar ölçmek bu tahmini sınar.

## Gold'da ne değişti

* 4 kayıt: `annotators` += `HAKEM-03`, `adjudicated` = `true`
  (toplam `adjudicated` 2 → **6**).
* 1 kayıt: `masraf_durumu` → `absent_fields`, `field_spans` girdisi kaldırıldı,
  `notes` gerekçeli.
* `gold.v2.json.sha256` güncellendi.
* `ANNOTATION_GUIDE.md` §4: `masraf_durumu` kapsam kuralı.

## Sources
- [[_kappa-ikinci-tur]] — negatif κ ölçümü ve uyuşmazlık listesi
- `data/gold/ANNOTATION_GUIDE.md` §4 (`masraf_durumu`), §4.13 (oranla verilen
  ücret), §7 (uyum eşiği ve hakemlik kararı)
