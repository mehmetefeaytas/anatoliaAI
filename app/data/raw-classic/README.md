# `data/raw-classic/` — KLASİK BANKA KORPUSU

```
╔══════════════════════════════════════════════════════════════════════════╗
║                                                                          ║
║   ⛔  Y A R I Ş M A   K A P S A M I   D I Ş I   ⛔                        ║
║                                                                          ║
║   Bu klasör TEKNOFEST yarışma veri seti DEĞİLDİR.                        ║
║   Buradaki 724 belge KATILIM BANKASI belgesi DEĞİLDİR.                   ║
║   Bu belgeler DEĞERLENDİRMEYE (gold/eval) GİRMEZ.                        ║
║                                                                          ║
║   Yarışma korpusu → ../raw/  (10 katılım bankası, 1759 kazınmış belge)   ║
║   Değerlendirme kümesi → ../gold/  (yalnızca katılım bankası belgeleri)  ║
║                                                                          ║
║   Bu klasörün TEK meşru kullanımı:                                       ║
║   8-sınıf kampanya türü sınıflandırıcısı için GÜMÜŞ EĞİTİM VERİSİ.       ║
║                                                                          ║
╚══════════════════════════════════════════════════════════════════════════╝
```

> **Jüri / dış okuyucu için özet:** `data/raw-classic/` içindeki Akbank, Garanti
> BBVA, İş Bankası, ING gibi bankalar **katılım bankası değildir** ve yarışma
> şartnamesinin veri seti kapsamına dâhil edilmemiştir. Bu korpus bilerek ve
> ayrı bir dizine toplanmıştır; yarışma veri seti, altın (gold) küme ve
> değerlendirme metrikleri bu klasörden **etkilenmez**. Yarışmaya sunulan veri
> seti için `../raw/` dizinine bakın.

---

## 1. Bu klasör nedir?

Türkiye'deki **klasik (konvansiyonel, katılım bankacılığı yapmayan)** 11 bankanın
resmî sitelerinden toplanmış kampanya/ürün metinleri korpusu.

| Nicelik | Değer | Nasıl ölçüldü |
|---|--:|---|
| Belge sayısı | **724** | `find data/raw-classic -name '*.txt' \| wc -l` |
| Provenance dosyası | **724** | `find data/raw-classic -name '*.meta.json' \| wc -l` |
| Depoda izlenen dosya | **1461** | `git ls-files data/raw-classic \| wc -l` |
| Banka sayısı | **11** | `data/raw-classic/*/` dizinleri |
| Toplama tarihi | **2026-08-04** (tek tur) | 724 `.meta.json` dosyasının tamamında `scraped_at` alanı `2026-08-04` |

`.html` ham önbelleği diskte tutulur ama `.gitignore` ile depo dışıdır
(`data/raw-classic/**/*.html`, bkz. `app/.gitignore` satır 42-47); `.txt` +
`content_hash` provenance'ı korumaya yeter.

### Banka bazında belge dağılımı

| Banka | Belge | Banka | Belge |
|---|--:|---|--:|
| `akbank` | 87 | `qnb` | 85 |
| `denizbank` | 40 | `teb` | 43 |
| `garanti-bbva` | 105 | `vakifbank` | 59 |
| `halkbank` | 45 | `yapi-kredi` | 117 |
| `ing` | 41 | `ziraat-bankasi` | 53 |
| `is-bankasi` | 49 | **TOPLAM** | **724** |

## 2. Neden toplandı?

Toplama gerekçesi `config/banks-classic.yaml` dosyasının başındaki "NE İÇİN VAR"
bloğunda kayıtlıdır. Üç amaç:

1. **Gümüş (silver) eğitim verisi.** 8-sınıf kampanya türü sınıflandırıcısı,
   `CLAUDE.md §4` gereği fine-tune edilen tek bileşendir ve dengeli 150-300
   örnek ister. İnsan anotasyon bütçesi altın (gold) kümeye ayrıldığı için
   eğitim verisi bu korpustan **LLM uzlaşmasıyla** üretilir.
2. **Terminoloji ayrımı testi.** Klasik ve katılım kolları aynı ürünü farklı
   sözlükle anlatır ve neredeyse kusursuz bir *minimal pair* seti oluşturur
   (Ziraat Bankası "konut kredisi / faiz oranı" ↔ Ziraat Katılım "konut
   finansmanı / kâr payı oranı"; VakıfBank ↔ Vakıf Katılım; Halkbank ↔ Emlak
   Katılım).
3. **Negatif örnek / halüsinasyon testi.** Klasik banka sayfasında modelin
   `kar_payi_orani` alanını **üretmemesi** gerekir. İnsan etiketi gerektirmez.

Şartname §5.1 veri setinin BDDK katılım bankalarının **tümünü içermesini** şart
koşar; bu bir **taban**dır, tavan değil. Klasik bankalar o tabanın dışında, ek
amaçla toplanmıştır ve yarışma veri seti olarak sunulmaz.

## 3. Nerede KULLANILIR

- `scripts/build_silver.py` — gümüş etiketleme hattı. Varsayılan girdi
  `--docs data/raw-classic` (bkz. betiğin 278/283/289. satırları).
- `scripts/split_trainable.py` — eğitilebilirlik ayrımı. Varsayılan kök
  `data/raw-classic` (883. satır). Çıktı: `data/silver/split_report.md`.
- Sonuç: **505 kayıtlık gümüş eğitim kümesi** (`data/silver/silver.jsonl`,
  `wc -l` = 505; `data/silver/silver_report.json` → `durum.silver = 505`).
  608 öneriden 505'i uzlaşmayla gümüş sayıldı, 100'ü reddedildi.

Gümüş küme **yalnızca ürün ailesi yapısını** (Konut / Taşıt / İhtiyaç
Finansmanı, Kart, Alışveriş Puanı, Yeni Müşteri, Yatırım Ürünü, Finansman)
aktarmak için kullanılır.

## 4. Nerede KULLANILMAZ (kritik)

- ❌ **Yarışma veri seti olarak sunulmaz.** Teslim edilen veri seti `../raw/`.
- ❌ **Altın (gold) kümeye girmez.** `data/gold/gold.v1.json` yalnızca katılım
  bankası belgelerinden derlenmiştir.
- ❌ **Değerlendirme/eval metriklerine girmez.** Macro-F1, P/R/F1, κ ve
  normalizasyon doğruluğu katılım verisinde ölçülür.
- ❌ **Terminoloji aktarımı için kullanılmaz.** Bu korpustan öğrenilmesi
  istenen şey terim değil, **yapı**dır. Terminolojiyi modelin kendisinin
  aktarması beklenir — sınavın konusu tam olarak budur.

`scripts/build_silver.py` bu ayrıklığı çalışma anında da duyurur: gümüş küme ile
gold küme kesişimi **sıfır** çıktığında betik "Bu bir kusur değil, TASARIM"
mesajını basar ve ölçümün Faz 3'te, ince ayarlı sınıflandırıcının gold
üzerindeki macro-F1'i ile yapılacağını söyler.

## 5. Ölçülmüş terim dağılımı — ayrıklığın kanıtı

Aşağıdaki tablo **belge kapsama oranıdır** (terimi en az bir kez içeren belgenin
toplam belgeye oranı), sıklık değil. Ölçüm yöntemi: her `.txt` dosyası
küçük harfe indirilip alt dizge araması yapıldı.

```bash
.venv/bin/python -c "
from pathlib import Path
for kok, n in (('data/raw-classic', None), ('data/raw', None)):
    d = sorted(Path(kok).rglob('*.txt'))
    m = [p.read_text(encoding='utf-8', errors='ignore').lower() for p in d]
    for t in ('faiz', 'kâr payı', 'murabaha', 'sukuk', 'katılma hesabı'):
        c = sum(1 for x in m if t in x)
        print(kok, t, c, round(100*c/len(m), 1))
"
```

| Terim | `data/raw-classic` (klasik, 724 belge) | `data/raw` (katılım, 1759 kazınmış belge) |
|---|--:|--:|
| `faiz` | **%70,2** (508 belge) | **%7,3** (128 belge) |
| `kâr payı` / `kar payı` | **%0,3** (2 belge) | **%18,1** (319 belge) |
| `murabaha` | **%0,0** (0) | %1,8 (31) |
| `sukuk` | **%0,0** (0) | %2,3 (40) |
| `katılma hesabı` | **%0,0** (0) | %11,6 (204) |
| `mudarebe` | **%0,0** (0) | %0,3 (5) |
| `karz-ı hasen` | **%0,0** (0) | %0,4 (7) |
| `muşareke` | **%0,0** (0) | %0,0 (0) |
| `icara` | **%0,0** (0) | %0,0 (0) |
| `tekafül` | **%0,0** (0) | %0,1 (1) |
| **Fıkhî terim (birleşik)** | **%0,0 — sıfır belge** | — |

> **Not (%18,1 vs %18,2):** `data/raw` altında 1761 `.txt` vardır; bunun 2'si
> demo fikstürüdür (`data/raw/kuveyt-turk/konut.txt`,
> `data/raw/turkiye-finans/tasit.txt` — banka kökünde, hasat kovası içinde
> değil). Yalnızca 1759 kazınmış belge üzerinden `kâr payı` oranı **%18,1**
> (319 belge); 1761'in tamamı sayılırsa %18,2 (321 belge) çıkar. Tabloda
> kazınmış küme esas alınmıştır.

**Okuma:** İki korpus terminoloji açısından tam ters kutuptadır. Klasik
korpusun hiçbir belgesinde fıkhî terim (murabaha, icara, mudarebe, muşareke,
karz-ı hasen, sukuk, katılma hesabı, tekafül) geçmez. Bu, klasik korpusun
terminoloji öğretemeyeceğinin kanıtıdır — ve tam da bu yüzden terminoloji
aktarımı **sınanabilir** bir hipotez hâline gelir.

## 6. `data/raw` ile farkı — özet tablo

| | `data/raw/` | `data/raw-classic/` |
|---|---|---|
| **Yarışma kapsamı** | ✅ **İÇİNDE** | ⛔ **DIŞINDA** |
| Banka türü | Katılım bankaları (faizsiz finans) | Klasik / konvansiyonel bankalar |
| Banka sayısı | 10 | 11 |
| Belge | 1759 kazınmış + 2 demo fikstürü | 724 |
| Rol | Yarışma veri seti + **altın (gold) değerlendirme** | Yalnızca **gümüş (silver) eğitim** |
| Terminoloji | kâr payı %18,1 · faiz %7,3 | faiz %70,2 · fıkhî terim %0,0 |
| İnsan anotasyonu | Var (`data/gold/`, Cohen κ çapası) | Yok (LLM uzlaşması) |
| Metriklere etkisi | Ölçülen küme | **Hiçbiri** |
| Yapılandırma | `config/banks.yaml` | `config/banks-classic.yaml` |

**Tasarımın özü:** gümüş hat klasik veride **EĞİTİR**, altın hat katılım
verisinde **ÖLÇER**. İki küme kasten ayrıktır; amaç sınıflandırıcının
terminolojiyi aktarıp aktaramadığını gerçekten sınamaktır
(`CLAUDE.md §12 — Domain Bilgisi: Faizsiz Finans`).

## 7. İlgili dosyalar

- `config/banks-classic.yaml` — toplama yapılandırması + gerekçe bloğu
- `scripts/build_silver.py` — gümüş etiketleme hattı
- `scripts/split_trainable.py` — eğitilebilirlik ayrımı
- `data/silver/split_report.md` — ayrım raporu
- `data/silver/silver_report.json` — gümüş küme sayıları
- `_collection_report.md`, `_extra_report.md` — otomatik toplama raporları
- `docs/rapor/devam-gumus-etiketleme.md` — gümüş hat oturum notu
- `../raw/README.md` — **kapsam içi** yarışma korpusu
- Bilgi arşivi: `../../../entities/klasik-banka-korpusu.md`
