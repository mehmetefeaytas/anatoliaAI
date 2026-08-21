---
başlık: Çelişki tespiti — tam korpus taraması (scan.py), 28 çelişki
durum: ölçüldü (2026-08-21), operatör tarafından koşturuldu
üretici: src.comparison.scan
girdi: data/raw (tam korpus, tek anlık görüntü + her belgenin .meta.json'undan okunan gerçek scraped_at)
---

# Çelişki tespiti — tam korpus taraması, 28 çelişki (2026-08-21)

> Bu belge [`celiski-canli-ornek.md`](celiski-canli-ornek.md)'nin YERİNE
> geçmez, ona **EK**tir. O belge dual-snapshot yöntemiyle (iki gerçek git
> hasat turunu karşılaştırarak) belgeler-arası "iki taraf aynı anda çelişiyor"
> örneği **bulamadığını (0)** dürüstçe raporlamıştı — o sonuç yanlışlanmadı,
> farklı bir soruya cevap veriyordu (iki ayrı hasat turu arasında ne
> değişti). Aşağıdaki ölçüm **farklı bir kod yolu**dur
> (`src/comparison/scan.py`): tek bir anlık görüntü üzerinde `product_key()`
> ile gruplama yapıp `.meta.json`'dan okunan gerçek `scraped_at` ile
> `detect_across()`'u fiilen ateşliyor — ve gerçek belgeler-arası çelişki
> üretiyor, dahil **kâr payı oranı uyuşmazlığı**.

## Komut (operatör tarafından koşturuldu, bu ajan tarafından tekrarlanmadı)

```bash
cd app && .venv/bin/python -m src.comparison.scan --raw-dir data/raw
```

`src/comparison/scan.py` ve `src/comparison/contradiction.py` bu ajanın
sahiplenmediği dosyalardır (`src/**` — dosya sahipliği kuralı gereği bu
raporu yazan ajan onlara dokunamaz ve komutu yeniden koşturmadı); sayı ve
kırılım operatörün ölçümünden aktarıldı, komut yukarıda tekrar üretilebilir
şekilde yazılı.

## Sonuç (2026-08-21)

**28 çelişki toplam.**

| tür | adet | kırılım |
|---|---:|---|
| **belgeler-arası** (`detect_across`) | **8** | 6 çapraz bitiş tarihi (`capraz_kampanya_bitisi`) + **2 çapraz kâr payı uyuşmazlığı** |
| **belge-içi** (`detect`) | **20** | 17 süresi dolmuş kampanya (`suresi_dolmus_kampanya`) + 2 çelişen tutar bandı (`celisen_tutar_bandi`) + 1 çelişen bitiş (`celisen_kampanya_bitisi`) |

## Manşet örnek — Albaraka, aynı ürün için iki oran

Albaraka Türk aynı ürün için iki ayrı formda **%7,0** ve **%1,0** kâr payı
oranı yayımlamış — kesişmeyen iki oran, üretim kodu `detect_across()`
tarafından belgeler-arası kâr payı çelişkisi olarak fiilen tespit edildi. Bu,
`kampanya_kosullari`/tarih dışındaki bir alanda (kâr payı) canlı ateşlenen
**ilk dokümante edilen belgeler-arası çelişki** örneğidir; önceki ölçüm
([`celiski-canli-ornek.md`](celiski-canli-ornek.md) §5) yalnız tarihçe/bitiş
tarihi örnekleri bulmuştu.

## Önceki ölçümle ilişkisi — niçin sayı farklı, ikisi de doğru

[`celiski-canli-ornek.md`](celiski-canli-ornek.md) (2026-08-20) dual-snapshot
yöntemiyle yalnız **6** "tarihçe/temporal update" örneği bulmuş, **0** gerçek
belgeler-arası çelişki raporlamıştı; sebebi orada yazılıydı: korpus tek bir
anlık görüntü tuttuğu için `detect_across`'a gerçekten ayrışan iki belge
verilemiyordu, o yüzden iki AYRI git turu manuel olarak birleştirilmişti.

Bu ölçüm ise tek bir güncel anlık görüntü İÇİNDE `product_key()` ile
gruplanan belgeler arasında tarıyor (`src.comparison.scan`, aynı bankanın
aynı ürününe ait birden çok sayfası — örn. farklı form/broşür/PDF —
karşılaştırılıyor). İki ölçüm birbirini çürütmüyor: biri "zaman içinde bu
sayfa değişti mi" sorusuna (6/0), diğeri "bugünkü korpusta aynı ürünün iki
sayfası birbiriyle çelişiyor mu" sorusuna (8 belgeler-arası, içinde 2 kâr
payı) cevap veriyor.

## Sources
- [`celiski-canli-ornek.md`](celiski-canli-ornek.md) — önceki (2026-08-20) dual-snapshot ölçümü, 0 belgeler-arası çelişki bulmuş, sebebi yazılı
- [`celiski-kod-yolu-tutarsizligi.md`](celiski-kod-yolu-tutarsizligi.md) — `_END_PATTERNS` kapsam genişletmesi, bitiş tarihi tespitinin ayrı geçmişi
