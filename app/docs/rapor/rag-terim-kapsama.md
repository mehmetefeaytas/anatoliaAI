# RAG terim kapsaması — korpus mu, eşik mi?

**Soru:** Katılım bankacılığının fıkhî terimlerini (murabaha, icare, sukuk,
muacceliyet…) chatbot kaynak göstererek açıklayabiliyor mu?

**Cevap: hayır — ve sebebi iki katmanlıydı.** İkisi de düzeltildi.

Ölçüm tarihi: 2026-08-07. Kural kolu, LLM kapalı, deterministik.

---

## Kapsama ölçütü

15 fıkhî terim için `"<terim> nedir?"` sorusu sorulur. Terim **kapsanmış**
sayılır ancak ve ancak dönen pasajlardan biri terimi **gerçekten içeriyorsa**.
Yani "pasaj döndü" yetmez — kanıt şartı vardır. Dönen ama terimi içermeyen
pasaj kapsama sayılmaz, çünkü kullanıcıya alakasız kaynak göstermek
sessiz halüsinasyondur.

Terimler: murabaha · mudaraba · müşaraka · icare · sukuk · istisna ·
karz-ı hasen · vekâlet · muacceliyet · tekafül · katılma hesabı · kâr payı ·
teverruk · selem · vaad

---

## Sonuç — 2×2 çarpanlı

| | mutlak eşik (`MIN_OVERLAP = 2`) | oransal eşik |
|---|---|---|
| **849 belge** (`demo.db`, 31 Tem) | 3/15 | 11/15 |
| **1761 belge** (`demo.v2.db`) | 4/15 | **14/15** |

İki değişiklik de gerekli, hiçbiri tek başına yeterli değil.

### 1. Korpus bayattı

`data/demo.db` **31 Temmuz'da** kuruldu. Korpus **3 Ağustos'ta** 1635+ belgeye
çıktı ve `docs/` bölümü (sözleşme + tarife PDF'leri) aynı gün eklendi. Yani
chatbot, dashboard ve RAG korpusun %48'ini hiç görmüyordu — üstelik fıkhî
terim yoğunluğu en yüksek bölümün **tamamını**.

Kod yolunda bölüm filtresi YOK: `src/pipeline.py::collect_corpus` bugün
koşulduğunda 1761 belge yükler (8 saniye). Sorun kodda değil, DB'nin
yeniden kurulmamış olmasındaydı.

> **Sayı hijyeni düzeltmesi.** 849, daha önce "filtrelenmiş alt küme" diye
> kaydedilmişti. Yanlış: filtre yok, DB **bayattı**. Bu satır eski notu
> düzeltir.

### 2. Eşik mutlaktı — tek sözcüklü soru matematiksel olarak cevapsızdı

`MIN_OVERLAP = 2` (en az 2 anlamlı sözcük örtüşmesi) sessiz halüsinasyona
karşı doğru bir korumaydı ve korunuyor. Ama mutlak sayı olarak uygulanınca:

    "Sukuk nedir?"  ->  anlamlı token: {'sukuk'}  ->  1 < 2  ->  HİÇ pasaj yok

Terim tanımı soruları **yapısal olarak** cevapsız kalıyordu. Terimler
dizinde vardı: `sukuk` 40 belge, `muaccel` 36, `murabaha` 31.

Doğru ölçüt "kaç sözcük tuttu" değil, **sorunun ne kadarı kanıtlandı**:

    etkin eşik = min(MIN_OVERLAP, anlamlı sözcük sayısı)

Çok sözcüklü sorularda davranış birebir aynı kalır (`min(2, n) = 2`), yani
eşiğin var oluş sebebi olan "Helal gıda alışverişinde puan veren kampanya
var mı?" halüsinasyonu geri gelmez — regresyon testiyle kilitli
(`tests/test_rag_index.py`).

### Kapsanmayan tek terim

**müşaraka** — korpusta yalnız 3 belgede geçiyor ve hiçbiri tanım metni
değil. Bu bir erişim kusuru değil, **veri boşluğu**. Uydurulmaz; sistem
çekimser kalır.

---

## Yan bulgu: korpus büyümesi yeni bir hata sınıfı getirdi

`docs/` bölümü gelince `kar_payi_orani` üretimi 47 → 84 kayda çıktı, ama
bunların **15'i (%17,9)** bir gecikme cezası maddesinden geliyordu:

> "Gecikme Cezası Oranı, akdi kâr payı oranının **%30** fazlasını geçemez."

Buradaki %30 ürünün kâr payı oranı değil, orana uygulanan **çarpandır**.
Karşılaştırma tablosuna girdiğinde Ziraat Katılım'ı %30 "oranla" en pahalı
banka gösteriyordu — güvenlik değerlendirmesinde C03 vakası olarak yakalandı.

Düzeltme (`_CEZA_BAGLAMI_RE`, `src/extraction/rules/extract.py`): çift kapı —
değerin sağındaki `fazla|artırım` eki ve solundaki (aynı cümle içindeki)
ceza/gecikme/temerrüt bağlamı.

| | kar_payi_orani | ceza bağlamlı |
|---|---:|---:|
| 849 belge | 47 | 0 |
| 1761 belge, düzeltme öncesi | 84 | **15** |
| 1761 belge, düzeltme sonrası | 70 | **1** |

Kalan 1 kayıt **doğru**: "Bankamızca, akdi kâr payı oranı %0 olarak
belirlenmiştir" — bu gerçek orandır, ceza sözcüğü penceresinde sonradan
geçiyor. Kapı bilinçli olarak "akdi kâr payı oranı"nı elemez.

**Bu kazanç gold'da (n=20) görünmez** — o 20 belgede ceza maddesi yok,
mikro-F1 0,677'de sabit kalır. Ölçüm setinin darlığının somut örneğidir:
korpusun %17,9'unu etkileyen bir hata sınıfı, ölçüm setinde sıfır iz
bırakıyor.

---

## Tekrar üretim

```bash
.venv/bin/python -m scripts.build_demo_db --out data/demo.db --force
.venv/bin/python -m scripts.eval_rag_terim          # kapsama tablosu
.venv/bin/python -m unittest discover -s tests      # 1482 test
```

## Kaynaklar

- `src/chatbot/rag.py` — `_etkin_esik()`, `MIN_OVERLAP`
- `src/extraction/rules/extract.py` — `_CEZA_BAGLAMI_RE`, `_YABANCI_KAVRAM_RE`
- `tests/test_rag_index.py` — eşik regresyon testleri
- `tests/test_kar_payi_yon.py` — `TestGecikmeCezasiOranSayilmaz`
- `docs/rapor/karar-bekleyenler.md` — K-1 (n=20 kırılganlığı)
