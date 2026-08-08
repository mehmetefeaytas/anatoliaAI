# Müşaraka veri boşluğu — ölçüm, hedefli toplama, kalan boşluk

İlgili: `scripts/eval_rag_terim.py`, `docs/rapor/rag-terim-kapsama.md`,
`src/chatbot/rag.py`, `data/terminology/katilim-terim-sozlugu.json`,
CLAUDE.md §12, §14, §21.

Bu rapor tek bir soruyu izler: **RAG, "müşaraka nedir?" sorusuna korpustan
kaynak gösterebiliyor mu?** Cevap hayır. Bu belge nedenini ayrıştırır, boşluğu
kapatmak için denenen kaynakları ve robots.txt kararlarını kaydeder, ve
kapanmayan kısmı dürüstçe bırakır.

---

## 1. Başlangıç durumu (ölçülen, 2026-08-08)

`python -m scripts.eval_rag_terim --db data/demo.db` — korpus 1761 belge,
`min_overlap=2` (oransal eşik), `k=3`. Kapsama ölçütü **kanıt şartlıdır**:
dönen pasajlardan biri terimin kökünü gerçekten içermelidir.

**Sonuç: 14/15.**

| Terim | Pasaj | Kapsandı | Kanıt kaynağı (kısaltılmış) |
|---|---|---|---|
| murabaha | 3 | ✓ | kuveytturk.com.tr/kampanyalar/kampanya-arsivi/… |
| mudaraba | 3 | ✓ | ziraatkatilim.com.tr/ozel-bankacilik/yatirim-urunleri/sukuk |
| **müşaraka** | **0** | **·** | **—** |
| icare | 3 | ✓ | kuveytturk.com.tr/isim-icin/dis-ticaret/… |
| sukuk | 3 | ✓ | kuveytturk.com.tr/medium/sermaye-piyasasi-…-tarif-3857.pdf |
| istisna | 3 | ✓ | kuveytturk.com.tr/isim-icin/dis-ticaret/… |
| karz-ı hasen | 3 | ✓ | albaraka.com.tr/tr/kampanyalar/detay/… |
| vekâlet | 3 | ✓ | albaraka.com.tr/documents/…/bayide-finansman-…pdf |
| muacceliyet | 3 | ✓ | kuveytturk.com.tr/medium/banka-karti-…-391.pdf |
| tekafül | 1 | ✓ | asset.emlakkatilim.com.tr/…/genel-kredi-sozlesmesi.pdf |
| katılma hesabı | 3 | ✓ | kuveytturk.com.tr/medium/…-tarif-3856.pdf |
| kâr payı | 3 | ✓ | kuveytturk.com.tr/kampanyalar/kampanya-arsivi/… |
| teverruk | 3 | ✓ | turkiyefinans.com.tr/tr-tr/kobi/sozlesmeler-ve-formlar/… |
| selem | 2 | ✓ | turkiyefinans.com.tr/tr-tr/kobi/sozlesmeler-ve-formlar/… |
| vaad | 1 | ✓ | ziraatkatilim.com.tr/bireysel/hesaplar/katilma-hesaplari/eli-bol-hesap |

Komşu terimlerin durumu ayrıca soruldu: **mudarebe, karz-ı hasen, icare,
sukuk dördü de kapsanıyor.** Yani sorun fıkhî terimlerin tümünde değil, tek
bir terimde.

### Kapsama kalitesi hakkında bir uyarı

Kapsanan 14 terimin çoğu **sözleşme/ücret tarifesi PDF'lerinden** geliyor —
yani terimin *geçtiği* bir belge var, *tanımlandığı* değil. Kanıt kapısı
"pasaj terimi içeriyor mu" sorusunu cevaplar, "pasaj terimi açıklıyor mu"
sorusunu değil. 14/15 rakamı bu sınırla okunmalıdır.

---

## 2. Neden kapanmıyor — iki ayrı arıza

`müşaraka` için pasaj sayısı **sıfır**. Bu iki bağımsız nedenden oluşuyor ve
ikisini karıştırmak yanlış çözüme götürür.

### 2a. Yazım varyantı arızası (erişim tarafı)

Korpusta terim **var**, ama başka yazımlarla. `.txt` gövdelerinde tam liste
(1761 belge tarandı, 6 dosya):

| Dosya | Geçen biçim |
|---|---|
| `adil-katilim/live/katilim-bankaciligi-katilim-bankaciligi-nedir.txt` | `müşareke` |
| `turkiye-finans/products/sozlesmeler-ve-formlar-*.txt` (2 dosya) | `Müşâreke` |
| `ziraat-katilim/products/yatirim-urunleri-sukuk.txt` | `Muşaraka` |
| `dunya-katilim/products/sermaye-piyasasi-urunleri-kira-sertifikasi*.txt` (2 dosya) | `Muşaraka` |

`src/chatbot/rag.py::_tokenize` **ü→u / ş→s katlaması yapmaz** (`tr_fold`
yalnız büyük/küçük harf katlar). Ölçüldü:

```
_tokenize('müşaraka')  -> ['müşaraka']
_tokenize('müşareke')  -> ['müşareke']
_tokenize('Muşaraka')  -> ['muşaraka']
_tokenize('Müşâreke')  -> ['müş', 'reke']      # şapkalı â sözcüğü ikiye böler
```

Dördü de **ayrı token**. Sonuç, sorgu biçimine göre tamamen değişiyor:

```
'müşaraka nedir?'  -> 0 pasaj
'muşaraka nedir?'  -> 3 pasaj (ziraat sukuk + dünya kira sertifikası ×2)
'müşareke nedir?'  -> 1 pasaj (adil katılım)
'musharakah nedir?'-> 0 pasaj
```

Yani `eval_rag_terim.py`'nin sorduğu `müşaraka` yazımı korpusta **hiç
geçmiyor**; projenin kendi sözlüğündeki kanonik biçim de `Muşaraka`
(`data/terminology/katilim-terim-sozlugu.json`, `id: musaraka`, varyantlar:
`müşareke`, `musharakah`, `muşareke`, `şirket-i inan`). Ölçüm listesindeki
`müşaraka`, ne korpusta ne sözlükte bulunan **beşinci bir varyant**.

### 2b. Tanım boşluğu (veri tarafı) — asıl arıza

Yazım düzeltilse bile boşluk kapanmıyor. Erişilen dört pasajın hiçbiri tanım
değil, hepsi **geçerken anma**:

- `ziraat-katilim` / `dunya-katilim`: "Ortaklığa dayalı kira sertifikası
  (Mudaraba/Muşaraka sukuk)" — sukuk türü listesinde bir etiket.
- `turkiye-finans`: "…Müşteri Bilgilendirme Formu (Fon Kullandırım-Müşâreke)"
  — form adı.
- `adil-katilim`: "…kiralama (icare) veya ortaklık (müşareke) gibi meşru
  yöntemlerle finanse eder" — tek sözcüklük parantez içi karşılık; en yakın
  olanı, ama yine tanım değil.

**Korpusta müşarakayı tanımlayan tek bir belge yok.** Kapsama arızası
öncelikle bir veri boşluğudur; yazım varyantı onu ikinci kez maskeliyor.

---

## 3. Denenen kaynaklar ve robots.txt kararları

_(Bölüm 4 ile birlikte doldurulur.)_

---

## 4. Sonuç

_(Bölüm 3 ile birlikte doldurulur.)_
