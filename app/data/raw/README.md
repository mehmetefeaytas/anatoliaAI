# `data/raw/` — YARIŞMA KORPUSU (kapsam İÇİ)

```
╔══════════════════════════════════════════════════════════════════════════╗
║                                                                          ║
║   ✅  Y A R I Ş M A   K A P S A M I   İ Ç İ                               ║
║                                                                          ║
║   Bu klasör TEKNOFEST 2026 TYDA 2. Senaryo veri setidir:                 ║
║   BDDK listesindeki KATILIM BANKALARININ kampanya/ürün metinleri.        ║
║   Altın (gold) küme ve tüm değerlendirme metrikleri BU korpustan çıkar.  ║
║                                                                          ║
║   ⛔ Kapsam DIŞI klasik banka korpusu için → ../raw-classic/README.md    ║
║                                                                          ║
╚══════════════════════════════════════════════════════════════════════════╝
```

## Ne var?

10 katılım bankasının ve TKBB'nin (şemsiye kuruluş) resmî sitelerinden
toplanmış metinler ve PDF asılları. Ölçüm tarihi: **2026-08-21**.

| Nicelik | Değer | Nasıl ölçüldü |
|---|--:|---|
| Toplam `.txt` | **2.708** | `find data/raw -name '*.txt' \| wc -l` |
| Kazınmış belge | **2.706** | `live` / `products` / `archive` / `docs` / `manual` kovalarındaki `.txt` |
| Demo fikstürü | **2** | Banka kökündeki `.txt`: `kuveyt-turk/konut.txt`, `turkiye-finans/tasit.txt` |
| PDF aslı | **1.000** (~356 MB) | `find data/raw -name '*.pdf' \| wc -l` — ücret tarifesi / bilgi formu / sözleşme öncesi form asılları, `docs/` kovasında metne indirilmiş halleriyle birlikte |
| Kaynak dizini | **11** (10 banka + `tkbb`) | `data/raw/*/` dizinleri |

### Kaynak bazında dağılım (`.txt` / `.pdf`)

| Kaynak | `.txt` | `.pdf` | Kaynak | `.txt` | `.pdf` |
|---|--:|--:|---|--:|--:|
| `adil-katilim` | 11 | 5 | `tom-katilim` | 260 | 99 |
| `albaraka` | 353 | 156 | `turkiye-emlak-katilim` | 227 | 43 |
| `dunya-katilim` | 110 | 2 | `turkiye-finans` | 205 | 112 |
| `hayat-finans` | 72 | 10 | `vakif-katilim` | 307 | 113 |
| `kuveyt-turk` | 885 | 441 | `ziraat-katilim` | 276 | 17 |
| `tkbb` | 2 | 1 | **TOPLAM** | **2.708** | **999** |

`.html` ham önbelleği diskte tutulur ama depo dışıdır (**`app/.gitignore`**
`data/raw/**/*.html` kuralı); banka kökündeki fikstür `.html` dosyaları istisna
olarak izlenir. PDF asılları da aynı dosyada dışlanır; metne indirilmiş `.txt`
karşılıkları izlenir.

## Rolü

- **Yarışma veri seti** — teslim edilen, indirme bağlantısı verilen küme budur.
- **Altın (gold) değerlendirme** — üç gold seti de bu korpustan derlenmiştir:
  `gold.v1.json` (20 kayıt, insan anotasyonlu, Cohen κ çapası),
  `gold.v2.json` (48 kayıt, kör etiketleme, 40'ı zor vaka),
  `gold.round1.json` (134 kayıt, protokol v2, 38'i hakemlikten geçti).
- **Ölçüm** — P/R/F1, macro-F1, normalizasyon doğruluğu burada hesaplanır.

## Kapsam dışı korpusla ilişki

`data/raw-classic/` (11 klasik banka, 724 belge) **yarışma kapsamı dışıdır** ve
değerlendirmeye girmez. Tek kullanımı 8-sınıf kampanya türü sınıflandırıcısı
için gümüş (silver) eğitim verisi üretmektir. İki küme **kasten ayrıktır**:
gümüş hat klasik veride eğitir, altın hat katılım verisinde ölçer — böylece
sınıflandırıcının terminolojiyi aktarıp aktaramadığı gerçekten sınanır.

Ölçülmüş terim ayrıklığı (2026-08-07): bu korpusta `kâr payı` %18,1 · `faiz`
%7,3; klasik korpusta `faiz` %70,2 · fıkhî terim %0,0.

➡️ **Ayrıntı ve tam karşılaştırma tablosu: [`../raw-classic/README.md`](../raw-classic/README.md)**

## İlgili dosyalar

- `config/banks.yaml` — toplama yapılandırması (kapsam içi bankalar)
- `_collection_report.md`, `_extra_report.md`, `_rates_report.md`,
  `_reextract_report.md` — otomatik toplama/çıkarım raporları
- `../gold/` — altın değerlendirme kümesi
- `../raw-classic/README.md` — kapsam **dışı** klasik banka korpusu
- Bilgi arşivi: `../../../entities/veri-seti.md`,
  `../../../entities/klasik-banka-korpusu.md`
