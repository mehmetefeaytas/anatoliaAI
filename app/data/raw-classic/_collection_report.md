<!-- KAPSAM UYARISI — elle eklendi (2026-08-07). Hasat betiği bu bloğu üretmez;
     `python -m src.scraping.harvest` yeniden koşarsa blok SİLİNİR, geri ekleyin. -->

```
╔══════════════════════════════════════════════════════════════════════════╗
║                                                                          ║
║   ⛔  Y A R I Ş M A   K A P S A M I   D I Ş I   ⛔                        ║
║                                                                          ║
║   Bu rapor KLASİK (katılım bankacılığı YAPMAYAN) bankaların toplama      ║
║   turlarını belgeler. Buradaki belgeler TEKNOFEST yarışma veri setinin   ║
║   parçası DEĞİLDİR ve DEĞERLENDİRMEYE (gold/eval) GİRMEZ.                ║
║                                                                          ║
║   Yarışma korpusu → ../raw/  (10 katılım bankası, 1759 kazınmış belge)   ║
║   Tek meşru kullanım → 8-sınıf sınıflandırıcı için GÜMÜŞ EĞİTİM VERİSİ.  ║
║                                                                          ║
║   Ayrıntı, ölçülmüş terim dağılımı ve `data/raw` ile fark tablosu:       ║
║   >>> ./README.md <<<                                                    ║
║                                                                          ║
╚══════════════════════════════════════════════════════════════════════════╝
```

> Ölçülen ayrıklık (2026-08-07): klasik korpusun **%70,2**'sinde `faiz` geçer,
> fıkhî terim (murabaha, icara, mudarebe, muşareke, karz-ı hasen, sukuk,
> katılma hesabı, tekafül) oranı **%0,0**. Katılım korpusunda tersi:
> `faiz` %7,3, `kâr payı` %18,1. Ölçüm yöntemi `./README.md` §5'te.

---

# Ham Veri Toplama Raporu

> Otomatik üretildi: `python -m src.scraping.harvest`. Elle düzenlemeyin — yeniden koşuda üzerine yazılır.
>
> **Not:** Aşağıdaki sayılar **bu turun** sayılarıdır (288 belge, 5 banka), tüm
> korpusun değil. Korpusun bugünkü toplamı **724 belge / 11 banka**
> (`find data/raw-classic -name '*.txt' | wc -l`) — birden çok tur birikmiştir.

- **Başlangıç:** 2026-08-04T13:14:55+00:00
- **Bitiş:** 2026-08-04T13:34:19+00:00
- **User-Agent:** `AnatoliaAI-Research/1.0 (+TEKNOFEST 2026; arastirma amacli)`
- **Domain başına gecikme:** 3.0 sn (CLAUDE.md §14)
- **robots.txt uyumu:** AÇIK (varsayılan)
- **Toplam belge:** 288

## Banka Bazında Özet

| Banka | Mod | Belge | Yöntem | Manuel | Boyut | Keşif (sitemap/liste) | Başarısız URL |
|---|---|---:|---|---:|---:|---|---:|
| `halkbank` | static | 28 | live | 0 | 10375 KB | 271/19 | 0 |
| `yapi-kredi` | js | 103 | browser | 0 | 74149 KB | 1475/160 | 5 |
| `garanti-bbva` | static | 90 | live | 0 | 9524 KB | 354/258 | 0 |
| `ing` | js | 34 | browser | 0 | 3038 KB | 272/6 | 0 |
| `teb` | static | 33 | live | 0 | 6831 KB | 0/58 | 0 |

## Depolama Notu

Toplam ham veri: **101 MB** — bunun neredeyse tamamı `.html` dosyalarıdır (`.txt` + `.meta.json` birlikte ~2 MB).

`.html` cache'i CLAUDE.md §14 (provenance) gereği tutulur ve metin çıkarımı iyileştiğinde yeniden-çıkarıma imkân verir. Depo boyutu sorun olursa `data/raw/*/live/*.html` `.gitignore`'a alınabilir: `.txt` + `content_hash` provenance'ı korumaya yeter, ancak yeniden-çıkarım için tekrar toplama gerekir.

## robots.txt Durumu

- **halkbank** — HTTP 200; 1 Allow / 0 Disallow; agent='*'; 2 sitemap
- **yapi-kredi** — HTTP 200; 1 Allow / 0 Disallow; agent='*'; 1 sitemap
- **garanti-bbva** — HTTP 200; 1 Allow / 2 Disallow; agent='*'; 2 sitemap
- **ing** — HTTP 200; 14 Allow / 14 Disallow; agent='*'; 2 sitemap
- **teb** — HTTP 200; 1 Allow / 2 Disallow; agent='*'

## Engellenen / Başarısız URL'ler

Bu URL'ler otomatik alınamadı. Şartname §5.1 manuel toplamaya izin
veriyor: sayfaları elle kaydedip `data/raw/<banka>/manual/`
altına koyun (yanına `.meta.json` provenance dosyası ekleyin).

### yapi-kredi (5)

- `https://www.yapikredi.com.tr/kampanyalar` — **HTTP 404**
- `https://www.crystalcard.com.tr/kampanyalar/index.html` — **HTTP 404**
- `https://www.yapikredi.com.tr/kampanyalar/kategori/bireysel` — **HTTP 404**
- `https://www.yapikredi.com.tr/kampanyalar/kategori/kisiye-ozel` — **HTTP 404**
- `https://www.yapikredi.com.tr/kampanyalar/kategori/kobi` — **HTTP 404**

## Notlar

- **halkbank** — 290 aday bulundu, max_docs=45 ile kirpildi
- **halkbank** — mukerrer icerik atlandi: https://www.paraf.com.tr/tr/kampanyalar/akaryakit.html
- **halkbank** — mukerrer icerik atlandi: https://www.paraf.com.tr/tr/kampanyalar/beyaz-esya-ve-elektronik.html
- **halkbank** — mukerrer icerik atlandi: https://www.paraf.com.tr/tr/kampanyalar/diger-firsatlar.html
- **halkbank** — mukerrer icerik atlandi: https://www.paraf.com.tr/tr/kampanyalar/e-ticaret.html
- **halkbank** — mukerrer icerik atlandi: https://www.paraf.com.tr/tr/kampanyalar/egitim-kirtasiye.html
- **halkbank** — mukerrer icerik atlandi: https://www.paraf.com.tr/tr/kampanyalar/giyim-kozmetik-ve-aksesuar.html
- **halkbank** — mukerrer icerik atlandi: https://www.paraf.com.tr/tr/kampanyalar/kafe-ve-restoran.html
- **halkbank** — mukerrer icerik atlandi: https://www.paraf.com.tr/tr/kampanyalar/kuyum-ve-mucevherat.html
- **halkbank** — mukerrer icerik atlandi: https://www.paraf.com.tr/tr/kampanyalar/market.html
- **halkbank** — mukerrer icerik atlandi: https://www.paraf.com.tr/tr/kampanyalar/mobilya-ve-dekorasyon.html
- **halkbank** — mukerrer icerik atlandi: https://www.paraf.com.tr/tr/kampanyalar/otomotiv.html
- **halkbank** — mukerrer icerik atlandi: https://www.paraf.com.tr/tr/kampanyalar/seyahat.html
- **halkbank** — mukerrer icerik atlandi: https://www.paraf.com.tr/tr/kampanyalar/sigorta.html
- **halkbank** — mukerrer icerik atlandi: https://www.halkbank.com.tr/tr/bireysel/emekli-bankaciligi/paraf-degerlimiz-dunyasi/kampanyalar
- **halkbank** — mukerrer icerik atlandi: https://www.halkbank.com.tr/tr/bireysel/krediler/ihtiyac-kredileri/kampanyali-ihtiyac-kredisi
- **halkbank** — mukerrer icerik atlandi: https://www.halkbank.com.tr/tr/dijital-bankacilik/mobil-bankacilik/paraf-mobil/kampanyalar
- **halkbank** — mukerrer icerik atlandi: https://www.halkbank.com.tr/tr/bankamiz/bizi-taniyin/haberler-ve-duyurular/haberler/2020/mart/milli-dayanisma-kampanyasi
- **yapi-kredi** — sayfalama: https://www.yapikredi.com.tr/bireysel-bankacilik/krediler/konut-kredisi icin 2 sayfa gezildi
- **yapi-kredi** — sayfalama: https://www.yapikredi.com.tr/bireysel-bankacilik/krediler/tasit-kredisi icin 3 sayfa gezildi
- **yapi-kredi** — sayfalama: https://www.yapikredi.com.tr/kampanyalar icin 2 sayfa gezildi
- **yapi-kredi** — sayfalama: https://www.yapikredi.com.tr/kampanyalar/kategori/bireysel/ icin 5 sayfa gezildi
- **yapi-kredi** — sayfalama: https://www.worldcard.com.tr/kampanyalar icin tek sayfa bulundu (sayfalama denetimi yok)
- **yapi-kredi** — sayfalama: https://www.adioscard.com.tr/kampanyalar icin tek sayfa bulundu (sayfalama denetimi yok)
- **yapi-kredi** — sayfalama: https://www.yapikrediplay.com.tr/kampanyalar icin tek sayfa bulundu (sayfalama denetimi yok)
- **yapi-kredi** — sayfalama: https://www.crystalcard.com.tr/kampanyalar/crystala-ozel-kampanyalar icin tek sayfa bulundu (sayfalama denetimi yok)
- **yapi-kredi** — 1635 aday bulundu, max_docs=110 ile kirpildi
- **yapi-kredi** — mukerrer icerik atlandi: https://www.yapikredi.com.tr/kampanyalar/detay/256902
- **yapi-kredi** — mukerrer icerik atlandi: https://www.yapikredi.com.tr/kampanyalar/detay/256906
- **garanti-bbva** — 612 aday bulundu, max_docs=90 ile kirpildi
- **ing** — sayfalama: https://www.ing.com.tr/tr/sizin-icin/krediler/konut-kredisi icin 11 sayfa gezildi
- **ing** — sayfalama: https://www.ing.com.tr/tr/sizin-icin/krediler/tasit-kredisi icin tek sayfa bulundu (sayfalama denetimi yok)
- **ing** — sayfalama: https://www.ing.com.tr/tr/bireysel icin tek sayfa bulundu (sayfalama denetimi yok)
- **ing** — sayfalama: https://www.ing.com.tr/tr/sizin-icin/kampanyalar icin tek sayfa bulundu (sayfalama denetimi yok)
- **ing** — 278 aday bulundu, max_docs=35 ile kirpildi
- **ing** — mukerrer icerik atlandi: https://www.ing.com.tr/tr/sizin-icin/kampanyalar/arkadasini-getir-nakit-kazan-2
- **teb** — 58 aday bulundu, max_docs=35 ile kirpildi
- **teb** — mukerrer icerik atlandi: https://www.teb.com.tr/kredi-karti-basvurusu?kartTipi=B
- **teb** — mukerrer icerik atlandi: https://www.teb.com.tr/kredi-karti-basvurusu?kartTipi=SH
