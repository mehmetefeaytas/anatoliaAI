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

10 katılım bankasının resmî sitelerinden toplanmış metinler.

| Nicelik | Değer | Nasıl ölçüldü |
|---|--:|---|
| Toplam `.txt` | **1761** | `find data/raw -name '*.txt' \| wc -l` |
| Kazınmış belge | **1759** | `live` / `products` / `archive` / `docs` / `manual` kovalarındaki `.txt` |
| Demo fikstürü | **2** | Banka kökündeki `.txt`: `kuveyt-turk/konut.txt`, `turkiye-finans/tasit.txt` |
| Banka sayısı | **10** | `data/raw/*/` dizinleri |

### Banka bazında belge dağılımı (`.txt`)

| Banka | Belge | Banka | Belge |
|---|--:|---|--:|
| `adil-katilim` | 6 | `tom-katilim` | 15 |
| `albaraka` | 217 | `turkiye-emlak-katilim` | 239 |
| `dunya-katilim` | 123 | `turkiye-finans` | 92 |
| `hayat-finans` | 48 | `vakif-katilim` | 197 |
| `kuveyt-turk` | 533 | `ziraat-katilim` | 291 |
| | | **TOPLAM** | **1761** |

`.html` ham önbelleği diskte tutulur ama depo dışıdır (`.gitignore` satır 30-39);
banka kökündeki fikstür `.html` dosyaları istisna olarak izlenir.

## Rolü

- **Yarışma veri seti** — teslim edilen, indirme bağlantısı verilen küme budur.
- **Altın (gold) değerlendirme** — `data/gold/gold.v1.json` yalnızca bu
  korpustan derlenmiştir; insan anotasyonludur ve Cohen κ çapasını taşır.
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
