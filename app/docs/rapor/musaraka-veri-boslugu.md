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

Tümü proje modülleriyle (`src/scraping/robots.py`, `fetcher.py`) çekildi:
User-Agent `AnatoliaAI-Research/1.0 (+TEKNOFEST 2026; arastirma amacli)`,
domain başına **3 sn** gecikme, her belgede provenance (timestamp +
`source_url` + `content_hash` + `robots_decision`).

**robots.txt kararı: denenen 10 origin'in 10'unda da İZİN.** Hiçbir kaynak
robots.txt nedeniyle atlanmadı, dolayısıyla manuel toplamaya düşülmedi.

| Kaynak | robots | Sonuç |
|---|---|---|
| `tkbb.org.tr/upload/…musareke_standardi.pdf` | izin (kural yok) | **alındı** — 36.463 krkt, 89 geçiş |
| `tkbbegitim.org.tr/tr/sayfa/faizsiz-finans-urunleri-99` | izin | **alındı** — 10.765 krkt |
| `albaraka.com.tr/…/musareke_-kar_zarar_ortakligi.pdf` | izin | **alındı** — 3.230 krkt |
| `albaraka.com.tr/…/` diğer 10 akit formu | izin | **alındı** (mudarebe, murabaha, teverruk, selem, tevliye, müsaveme, karz-ı hasen, yatırım vekâleti, icare ×2) |
| `albaraka.com.tr/…/garanti.pdf` | izin | **elendi** — ölçülen terimlerin hiçbirini içermiyor |
| `tkbb.org.tr/upload/sorularla_katilim_bankaciligi_baski.pdf` | izin | **elendi** — gerekçe aşağıda |
| `albaraka.com.tr/tr/hakkimizda/katilim-bankaciligi` | izin | **elendi** — terim yalnız bağlantı etiketi olarak geçiyor, tanım yok |
| `kuveytturk.com.tr/hakkimizda/faizsiz-bankacilik` | izin | **HTTP 404** |
| `vakifkatilim.com.tr/tr/katilim-bankaciligi` | izin | **HTTP 404** |

### Neden "Sorularla Katılım Bankacılığı" alınmadı

336.381 karakter — korpus azamisinin (178.825) iki katı. `KeywordRetriever`
skoru `örtüşme / (√|soru token| + 1)` ve **belge uzunluğu normalizasyonu
YOK**. Bu boyda bir belge çok sözcüklü sorularda neredeyse her zaman azami
örtüşmeye ulaşır ve gerçek kampanya sayfalarını sıralamadan iter. Terim
kazancı da düşüktü (336k karakterde 8 geçiş, hepsi şapkalı `müşârek`
biçiminde — aşağıdaki tokenizasyon kusuru yüzünden zaten görünmez).
Alınmaması bir robots kararı değil, **veri kalitesi kararıdır**.

### Eklenen belge sayısı

**13 yeni belge** (`.txt` + `.txt.meta.json`; PDF'ler mevcut korpus deseniyle
uyumlu olarak `.gitignore`'da):

- `data/raw/tkbb/docs/` — 2 belge
- `data/raw/albaraka/docs/` — 11 belge

Korpus 1761 → **1774**. DB yeniden kuruldu (başka bir iş kapsamında);
`scripts/check_demo_db` **GÜNCEL** (1774/1774) doğruladı.

### TKBB'nin `banks.yaml`'da olması ve ürün riski

Ingest yolu (`src/pipeline.py::run_pipeline`) banka kayıtlarını
`config/banks.yaml`'dan sürer: orada olmayan bir `data/raw/<slug>/` klasörü
korpusa **hiç girmez**. TKBB bu yüzden config'e eklendi.

Yan etkisi ölçüldü ve kapatıldı: süzme olmadan `GET /banks` TKBB'yi **11.
banka** olarak döndürüyordu. Jüri kıyas ekranında TKBB satırı görseydi bu
doğrudan kusur olurdu (CLAUDE.md §13 hedef listeyi BDDK Liste 77 ile
tanımlar). Ayrım `otorite_kaynak: true` bayrağıyla kuruldu — `bddk_active`
ile **değil**, çünkü o alan "gerçek banka ama lisansı aktif değil" demektir
ve lisansı düşmüş gerçek bir bankayı da katalogdan silerdi.

Kıyas tarafı zaten korunuyordu: `/compare` belge türüne göre süzülüyor ve iki
TKBB belgesinin de `belge_turu='sozlesme'` (ölçüldü) — hiçbir zaman kıyas
satırı üretmediler.

---

## 4. Kapanan ve kapanmayan

### Kapanan: tanım boşluğu (2b) gerçekten kapandı

Korpus artık müşarekayı **tanımlayan** belgeler içeriyor. Albaraka akit
formundan, birebir alıntı:

> Müşareke, iki veya daha fazla tarafın belirli bir miktar sermaye koyarak,
> birlikte iş yapmak ve oluşabilecek kâr veya zararı paylaşmak üzere
> kurdukları ortaklıktır. […] Taraflar; zarara kendi hisseleri kadar, kâra
> ise aralarındaki anlaşmaya göre dâhil olurlar.

Chatbot üzerinde ölçüldü (`data/demo.db`, 1774 belge, LLM kapalı):

```
"müşareke nedir?" -> handler=rag, 3 kaynak
   1. albaraka.com.tr/.../musareke_-kar_zarar_ortakligi.pdf   ← TANIM
   2. adilkatilim.com.tr/katilim-bankaciligi/...
   3. tkbbegitim.org.tr/tr/sayfa/faizsiz-finans-urunleri-99   ← TANIM
```

Toplama öncesinde aynı soru yalnızca adil-katilim'in tek sözcüklük parantez
içi anmasını döndürüyordu. Yeni belgeler ayrıca **10/15 terime** yeni kanıt
belgesi getirdi (murabaha, icare, sukuk, istisna, karz-ı hasen, vekâlet,
katılma hesabı, kâr payı, teverruk, selem) — hepsi *tanım* metni, sözleşme
içinde geçen bir sözcük değil.

### Kapanmayan: `müşaraka` yazımı (2a) — ölçüm hâlâ 14/15

```
python -m scripts.eval_rag_terim --db data/demo.db
DB: data/demo.db  |  belge: 1774  |  min_overlap: 2
kapsama: 14/15        Kapsanmayan: müşaraka
```

Nedeni veri değil, **yazım**: `müşaraka` dizisi korpusta hâlâ hiç geçmiyor ve
`_tokenize` ü/ş katlaması yapmadığı için `müşareke` ile eşleşmiyor.

```
"müşaraka nedir?" -> 0 pasaj -> "Bu bilgi verimde yok."   (dürüst çekimserlik)
"müşareke nedir?" -> 3 pasaj -> tanım                     (yukarıdaki)
```

Bu **bilinçli olarak kapatılmadı.** `TERIMLER` listesindeki `müşaraka`'yı
`müşareke` ile değiştirmek ölçümü tek satırda 15/15 yapardı, ama bu veriyi
değil ölçüm aletini değiştirmek olurdu. Aynı şey varyant-duyarlı bir kanıt
kapısı için de geçerli: o değişiklik **toplama yapılmadan da** 15/15
verirdi, çünkü eski korpustaki `Muşaraka sukuk` anması eşleşirdi — yani
gerçek bir tanım kazanımını, olmayan bir kazanımdan ayırt edemezdi.

Doğru düzeltme erişim katmanındadır ve bu işin dosya kapsamı dışındadır:
`src/chatbot/rag.py::_tokenize` katlaması.

### Yan bulgu: şapkalı ünlü terimleri ORTADAN BÖLÜYOR

`_tokenize` `â/î/û`'yu sözcük sınırı sayıyor:

```
_tokenize('kâr payı')  -> ['payı']        # 'kâr' TAMAMEN düşüyor
_tokenize('vekâlet')   -> ['vek', 'let']
_tokenize('müşâreke')  -> ['müş', 'reke']
_tokenize('mudârebe')  -> ['mud', 'rebe']
```

Üç sonucu var:

1. **En iyi kaynağımız görünmez.** TKBB Müşâreke Standardı'nda terim 89 kez
   geçiyor ama tamamı şapkalı `Müşârek…` — belgenin `müş` ile başlayan tek
   token'ı `'müş'`. 36k karakterlik otorite standardı erişime hiç katılmıyor.
2. **Kapsama iddiası yumuşuyor.** `vekâlet` için kanıt kapısı `'vek'` öneki
   arıyor; `karz-ı hasen` için `'karz'`. `kâr payı` ölçümü aslında `payı`
   ölçümüdür.
3. Bu, ölçümün 14/15'ini olduğundan iyimser gösteriyor — ama düşürdüğü terim
   `müşaraka` değil, o zaten sayılmıyor.

`scripts/eval_rag_terim.py` bunu artık **raporluyor** (`kok_parcali` alanı +
konsol uyarısı): şu an 2/15 terim kök-parçalı. Ölçütün kendisi
DEĞİŞTİRİLMEDİ — sadece görünür kılındı, çünkü kusur `rag.py`'de ve oradan
düzeltilmesi gerekiyor.

### Sözlük yolu: veri var, bağlantı yok

`data/terminology/katilim-terim-sozlugu.json` müşarakayı **tam ve doğru**
tanımlıyor (`id: musaraka`, kanonik `Muşaraka`, kaynak AAOIFI Şer'i
Standartları, `degildir: [kredi, mudaraba]`, mudaraba ile ayrım notu dahil).
Dahası, sözlük eşlemesi yazıma **dayanıklı** — retriever'ın olamadığı yerde:

```
relevant_terms('müşaraka nedir?') -> [Muşaraka]     ← retriever'ın 0 döndürdüğü yazım
relevant_terms('müşareke nedir?') -> [Muşaraka]
relevant_terms('muşaraka nedir?') -> [Muşaraka]
```

**Ama chatbot bunu kullanmıyor.** `src/chatbot/bot.py::_dispatch` yalnız iki
yol tanıyor: `structured` (text-to-SQL) ve `rag`. Sözlük için handler yok;
`terminology.py` bugün yalnızca çıkarım istemlerinde (`llm/agents.py::cards_for`)
ve güvenlik kapsam kontrolünde (`safety.py::scope_terms`) kullanılıyor.

Ölçüldü: `bot.ask("müşaraka nedir?")` → `handler=rag`, 0 kaynak, çekimser
cevap. Sözlükten cevaplamıyor, sözlüğü kaynak göstermiyor.

Yani **"sözlükten cevaplanıyor" diye raporlanacak bir davranış yok.** Böyle
bir yol kurulursa meşrudur, ama o zaman bile ayrı yazılmalıdır: sözlük
kapsaması **korpus kapsaması değildir** ve `eval_rag_terim.py`'nin ölçtüğü
şey korpustur.

---

## 5. Açık kalan işler (bu işin kapsamı dışında)

1. `src/chatbot/rag.py::_tokenize` — şapkalı ünlü katlaması (`â→a`) ve
   isteğe bağlı `ü/ş` katlaması. En büyük tek kazanç: TKBB standardını
   erişilebilir yapar ve `kâr payı` ölçümünü gerçek kılar.
2. Sözlük handler'ı — `bot.py::_dispatch`'e "terim tanımı" yolu; kaynak
   olarak sözlük gösterilmeli, korpus gibi sunulmamalı.
3. `TERIMLER` listesindeki `müşaraka` yazımı — korpusta ve projenin kendi
   sözlüğünde (`kanonik: Muşaraka`) karşılığı olmayan beşinci varyant.
   Değiştirilecekse (1) ile birlikte ve gerekçesi yazılarak.

## Sources
- `scripts/eval_rag_terim.py` — ölçüm (2026-08-08, `data/demo.db`, 1774 belge)
- `data/eval/rag-terim-kapsama.json` — terim terim JSON çıktı
- `config/banks.yaml` — TKBB otorite kaynak girdisi
- `data/raw/tkbb/docs/*.txt.meta.json`, `data/raw/albaraka/docs/bilgilendirme-formu-*.txt.meta.json` — provenance

## Related
- `docs/rapor/rag-terim-kapsama.md` — kapsama ölçümünün kaynağı
- `docs/rapor/belge-turu.md` — `belge_turu` ayrımı (kıyas süzmesi)
- `CLAUDE.md` §13 (hedef banka listesi), §14 (scraping etiği), §17 (adil kıyas), §21 (uydurma yasağı)
