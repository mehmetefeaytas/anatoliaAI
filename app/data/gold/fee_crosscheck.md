# Masrafsızlık İddiası — Ücret Tarifesi Çapraz Kontrol Raporu

> Otomatik üretildi: `python -m scripts.crosscheck_fees`. Anotasyon CSV'leri DEĞİŞTİRİLMEZ; bu dosya öneridir.

Bu, CLAUDE.md §18 hedef #2'nin ("masrafsız deyip tahsis ücreti alanı yakala") **belgeler arası** kurulumudur. Zor-vaka kürlemesi belge İÇİ çelişkinin korpusta pratik olarak bulunmadığını ölçtü; iddia kampanyada, ücret ise bankanın ayrı tarifesinde duruyor.

- **İncelenen iddia × ürün satırı:** 7
- **Bağımsız kaynak:** 33 ilan edilmiş tahsis ücreti kaydı, 5 banka

| Sonuç | Adet | Oran | Ne yapılmalı |
|---|---:|---:|---|
| `kapsamsiz_iddia` | 1 | %14.3 | Belgeye bak: gerçek çelişki mi, yoksa koşul metinde yazmıyor mu? |
| `kosullu_muafiyet` | 6 | %85.7 | Dashboard'da 'masrafsız' YAZMA — koşulu birlikte göster |
| `tutarli` | 0 | %0.0 | İddia tarifeyle uyumlu — işlem yok |
| `tarife_yok` | 0 | %0.0 | O bankanın ücret tarifesi toplanmalı (hasat işi) |

## Neden `kosullu_muafiyet` bir kusur değil, ÜRÜNÜN KENDİSİ

Ölçülen gerçek: 33 ilan edilmiş kayıttan **30'i tam olarak %0,5** — BDDK'nın konut finansmanı için koyduğu üst sınır, yani sektörde fiilen tek fiyat. Dolayısıyla "tarifede ücret var" tek başına hiçbir şey söylemez; öyle kullanılırsa bu betik meşru muafiyetleri sahtekârlık diye işaretler.

Ayırt edici olan **kapsam**. Kullanıcının karşılaştırma tablosunda görmesi gereken şey "masrafsız" değil, `dashboard_ifadesi` kolonundaki koşullu ifadedir.

### %0,5 dışındaki kayıtlar

| Banka | Ürün | Değer | Kaynak |
|---|---|---|---|
| turkiye-emlak-katilim | tasit | `0.1%` | `urun-ve-hizmet-ucretleri-breysel-bankacilik-urun-ve-hzmet-ucretler-2026-tr-pdf.txt` |
| turkiye-emlak-katilim | ihtiyac | `157.50₺` | `finansmanlar-ihtiyac-finansmani.txt` |
| vakif-katilim | tasit | `500₺` | `finansmanlar-tasit-finansmani.txt` |

### Banka içi tutarsızlık (yan bulgu)

Aynı banka, aynı ürün ve **aynı birim** için farklı belgelerde farklı tahsis ücreti ilan ediyor. Bu betiğin hedefi değil, ama ölçüldüğü için kayda geçiyor:

- `turkiye-emlak-katilim` / `tasit` (%): `0.1%`, `0.5%`

## İlan edilmiş tahsis ücretleri (bağımsız kaynak)

| Banka | Ürün | İlan edilen | Kaynak |
|---|---|---|---|
| albaraka | ihtiyac | `%0.5` | `tr-urun-ve-hizmet-ucretleri.txt` |
| albaraka | konut | `%0,5` | `gecmis-tarihli-konut-finansmani-talep-onay-ucret-bilgilendirme-formu-pdf.txt` |
| albaraka | konut | `%0.5` | `tr-urun-ve-hizmet-ucretleri.txt` |
| albaraka | tasit | `%0,5` | `gecmis-tarihli-aracfinansmanitalep-onayveucretbilgilendirmeformu-pdf.txt` |
| albaraka | tasit | `%0.5` | `tr-urun-ve-hizmet-ucretleri.txt` |
| kuveyt-turk | ihtiyac | `%0,5` | `medium-bireysel-finansman-talebi-onay-ve-bilgilendirme-fo-3629-pdf.txt` |
| kuveyt-turk | ihtiyac | `%0,5` | `medium-bireysel-finansman-talebionay-ve-bilgilendirme-for-404-pdf.txt` |
| kuveyt-turk | ihtiyac | `0.5%` | `medium-finansal-tuketici-urun-ve-hizmet-ucret-tablosu-4015-pdf.txt` |
| kuveyt-turk | ihtiyac | `%0,5` | `alisveris-finansmanlari-ihtiyac-kart.txt` |
| kuveyt-turk | ihtiyac | `%0,5` | `ihtiyac-finansmanlari-egitim-finansmani.txt` |
| kuveyt-turk | ihtiyac | `%0,5` | `ihtiyac-finansmanlari-hac-umre-finansmani.txt` |
| kuveyt-turk | ihtiyac | `%0,5` | `ihtiyac-finansmanlari-seyahat-finansmani.txt` |
| kuveyt-turk | ihtiyac | `%0,5` | `ihtiyac-finansmanlari-tekne-tuketici-finansmani.txt` |
| kuveyt-turk | konut | `0.5%` | `medium-finansal-tuketici-urun-ve-hizmet-ucret-tablosu-4015-pdf.txt` |
| kuveyt-turk | konut | `0,5%` | `konut-finansmanlari-gurbetten-silaya-gayrimenkul-finansmani.txt` |
| kuveyt-turk | konut | `0,5%` | `konut-finansmanlari-ilk-evim-konut-finansmani.txt` |
| kuveyt-turk | konut | `0,5%` | `konut-finansmanlari-konut-finansmani.txt` |
| kuveyt-turk | tasit | `0.5%` | `medium-finansal-tuketici-urun-ve-hizmet-ucret-tablosu-4015-pdf.txt` |
| turkiye-emlak-katilim | ihtiyac | `0.5%` | `qr-temel-bankacilik-hizmetleri-talep-ve-bilgilendirme-formu-bireyselturkce-pdf.txt` |
| turkiye-emlak-katilim | ihtiyac | `157.50₺` | `finansmanlar-ihtiyac-finansmani.txt` |
| turkiye-emlak-katilim | konut | `%0,5` | `qr-konut-finansmani-sozlesme-oncesi-bilgi-formu-pdf.txt` |
| turkiye-emlak-katilim | konut | `0.5%` | `qr-temel-bankacilik-hizmetleri-talep-ve-bilgilendirme-formu-bireyselturkce-pdf.txt` |
| turkiye-emlak-katilim | tasit | `0.5%` | `qr-temel-bankacilik-hizmetleri-talep-ve-bilgilendirme-formu-bireyselturkce-pdf.txt` |
| turkiye-emlak-katilim | tasit | `0.1%` | `urun-ve-hizmet-ucretleri-breysel-bankacilik-urun-ve-hzmet-ucretler-2026-tr-pdf.txt` |
| turkiye-finans | ihtiyac | `0,50%` | `ihtiyac-finansmani-ihtiyac-finansmani.txt` |
| turkiye-finans | konut | `0,50%` | `konut-finansmani-konut-finansmani.txt` |
| turkiye-finans | tasit | `0,50%` | `tasit-finansmani-tasit-finansmani-2.txt` |
| turkiye-finans | tasit | `0,50%` | `tasit-finansmani-tasit-finansmani.txt` |
| vakif-katilim | ihtiyac | `%0,5` | `hesaplama-araclari-finansman-hesaplama.txt` |
| vakif-katilim | konut | `%0,5` | `finansmanlar-konut-finansmani.txt` |
| vakif-katilim | konut | `%0,5` | `hesaplama-araclari-finansman-hesaplama.txt` |
| vakif-katilim | tasit | `500₺` | `finansmanlar-tasit-finansmani.txt` |
| vakif-katilim | tasit | `%0,5` | `hesaplama-araclari-finansman-hesaplama.txt` |

## Related
- [[zor-vaka-kurleme]] — bu betiği doğuran `celiskili` bulgusu
- `scripts/crosscheck_rates.py` — aynı desenin oranlar için hâli
