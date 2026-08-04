# Bayat Belge Mutabakatı Raporu

> Otomatik üretildi: `python -m src.scraping.reconcile_stale`. Elle düzenlemeyin.

- **Önceki tur:** `2026-07-30`
- **Yeni tur:** `2026-08-03`
- **Mod:** KURU KOŞU (hiçbir dosya taşınmadı)
- **Doğrulanan kayıp URL:** 44

| Karar | Adet | Ne yapıldı |
|---|---:|---|
| `kaldirilmis` | 1 | HTTP 404/410 → `archive/`, `campaign_status: expired` |
| `suresi_dolmus` | 5 | sayfa kendini bitmiş ilan ediyor → `archive/`, `expired` |
| `gecersiz_kilindi` | 35 | yeni turda başka kümede taze hâli var → mükerrer kopya `archive/`'a |
| `kesif_acigi` | 3 | **dokunulmadı** — keşif açığı (aşağıya bak) |
| `dogrulanamadi` | 0 | **dokunulmadı** — karar verilemedi |

## Keşif Açığı — hâlâ yayında ama bu turda bulunamadı

Bunlar süresi dolmuş DEĞİL: sayfa HTTP 200 dönüyor ve kendini bitmiş ilan etmiyor. Yani `banks.yaml` giriş noktaları / `detail_patterns` / `max_docs` bu sayfaları kaçırdı. Kapsamı artırmak için en somut girdi budur.

| Banka | Kaçırılan |
|---|---:|
| `albaraka` | 1 |
| `vakif-katilim` | 2 |

<details><summary>URL listesi</summary>

**albaraka**

- `https://www.albaraka.com.tr/tr/kampanyalar/detay/albaraka-restoran-harcamaniza-5-indirimm-kazandiriyor`

**vakif-katilim**

- `https://www.vakifkatilim.com.tr/tr/kendim-icin/kampanyalar/detay/mastercard-kredi-kartinizla-200-tl-marti-kuponu`
- `https://www.vakifkatilim.com.tr/tr/kendim-icin/kampanyalar/detay/mastercard-kredi-kartinizla-n11-alisverisinize-300-tl-indirim_1`

</details>

## Kaldırılmış belgeler (1)

<details><summary>URL listesi</summary>

- `https://www.albaraka.com.tr/tr/kampanyalar/detay/albaraka-restoran-harcamaniza-5-indirim-kazandiriyor` — HTTP 404 — sayfa kaldırılmış

</details>

## Süresi dolmuş belgeler (5)

<details><summary>URL listesi</summary>

- `https://www.turkiyefinans.com.tr/tr-tr/kampanyalar/Sayfalar/emekliler-haftasina-ozel-avantajlar.aspx` — sayfa yayında ama kendini 'süresi dolmuş' olarak işaretliyor
- `https://www.turkiyefinans.com.tr/tr-tr/kampanyalar/Sayfalar/gunluk-hesap-vade-kampanyasi.aspx` — sayfa yayında ama kendini 'süresi dolmuş' olarak işaretliyor
- `https://www.turkiyefinans.com.tr/tr-tr/kampanyalar/Sayfalar/katilim-hesabi-kampanyasi.aspx` — sayfa yayında ama kendini 'süresi dolmuş' olarak işaretliyor
- `https://www.vakifkatilim.com.tr/tr/kendim-icin/kampanyalar/detay/mastercard-ile-enuyguncomda-150-tl-indirim` — sayfa yayında ama kendini 'süresi dolmuş' olarak işaretliyor
- `https://www.vakifkatilim.com.tr/tr/kendim-icin/kampanyalar/detay/mastercardla-egitimde-vade-farksiz-5-taksit` — sayfa yayında ama kendini 'süresi dolmuş' olarak işaretliyor

</details>

## Geçersiz kılınan (mükerrer) kopyalar (35)

<details><summary>URL listesi</summary>

- `https://www.kuveytturk.com.tr/kampanyalar/kampanya-arsivi/1-aylik-tod-taraftar-paketi-ucretsiz` — aynı URL yeni turda archive kümesinde TAZE hâliyle toplandı; bu live/ kopyası mükerrer
- `https://www.kuveytturk.com.tr/kampanyalar/kampanya-arsivi/10-yilini-dolduran-milesandsmiles-kredi-karti-sahibi-musterilerimize-1000-mil-hediye-scr` — aynı URL yeni turda archive kümesinde TAZE hâliyle toplandı; bu live/ kopyası mükerrer
- `https://www.kuveytturk.com.tr/kampanyalar/kampanya-arsivi/10-yilini-dolduran-saglam-kart-sahibi-musterilerimize-500-tl-indirim-scr` — aynı URL yeni turda archive kümesinde TAZE hâliyle toplandı; bu live/ kopyası mükerrer
- `https://www.kuveytturk.com.tr/kampanyalar/kampanya-arsivi/1000-tl-hediyesiyle-saglam-tohum-kart-hizmetinizde` — aynı URL yeni turda archive kümesinde TAZE hâliyle toplandı; bu live/ kopyası mükerrer
- `https://www.kuveytturk.com.tr/kampanyalar/kampanya-arsivi/1000-tlye-varan-market-indirimi-saglam-kart-troyda` — aynı URL yeni turda archive kümesinde TAZE hâliyle toplandı; bu live/ kopyası mükerrer
- `https://www.kuveytturk.com.tr/kampanyalar/kampanya-arsivi/10000-tl-degerindeki-cek-karnesi-ve-cek-tahsil-paketi-ucretsiz-scr` — aynı URL yeni turda archive kümesinde TAZE hâliyle toplandı; bu live/ kopyası mükerrer
- `https://www.kuveytturk.com.tr/kampanyalar/kampanya-arsivi/3000-tl-degerindeki-cek-karnesi-paketi-ucretsiz-scr` — aynı URL yeni turda archive kümesinde TAZE hâliyle toplandı; bu live/ kopyası mükerrer
- `https://www.kuveytturk.com.tr/kampanyalar/kampanya-arsivi/50000-tlye-kadar-ertesi-gun-199-ya-da-25-gun-blokeli-0-pos` — aynı URL yeni turda archive kümesinde TAZE hâliyle toplandı; bu live/ kopyası mükerrer
- `https://www.kuveytturk.com.tr/kampanyalar/kampanya-arsivi/7000-tl-degerindeki-cek-tahsil-paketi-ucretsiz-scr` — aynı URL yeni turda archive kümesinde TAZE hâliyle toplandı; bu live/ kopyası mükerrer
- `https://www.kuveytturk.com.tr/kampanyalar/kampanya-arsivi/akaryakit-istasyonlari-kuveyt-turk-ile-gelecege-hazir` — aynı URL yeni turda archive kümesinde TAZE hâliyle toplandı; bu live/ kopyası mükerrer
- `https://www.kuveytturk.com.tr/kampanyalar/kampanya-arsivi/anneler-gunu-hediyenize-500-tl-nakit-iade` — aynı URL yeni turda archive kümesinde TAZE hâliyle toplandı; bu live/ kopyası mükerrer
- `https://www.kuveytturk.com.tr/kampanyalar/kampanya-arsivi/arac-finansmani-musterilerine-ozel-akaryakit-harcamalarina-300-tl-indirim-scr` — aynı URL yeni turda archive kümesinde TAZE hâliyle toplandı; bu live/ kopyası mükerrer
- `https://www.kuveytturk.com.tr/kampanyalar/kampanya-arsivi/arac-finansmani-musterilerine-ozel-akaryakit-harcamalarina-300-tl-indirim-firsati` — aynı URL yeni turda archive kümesinde TAZE hâliyle toplandı; bu live/ kopyası mükerrer
- `https://www.kuveytturk.com.tr/kampanyalar/kampanya-arsivi/arac-finansmanina-ucretsiz-hgs-etiketi-kuveyt-turkte` — aynı URL yeni turda archive kümesinde TAZE hâliyle toplandı; bu live/ kopyası mükerrer
- `https://www.kuveytturk.com.tr/kampanyalar/kampanya-arsivi/arac-kiralamasina-ozel-ekstra-3000-mil` — aynı URL yeni turda archive kümesinde TAZE hâliyle toplandı; bu live/ kopyası mükerrer
- `https://www.kuveytturk.com.tr/kampanyalar/kampanya-arsivi/avalli-islemlerde-uygun-oran-kuveyt-turkte-scr` — aynı URL yeni turda archive kümesinde TAZE hâliyle toplandı; bu live/ kopyası mükerrer
- `https://www.kuveytturk.com.tr/kampanyalar/kampanya-arsivi/avansasta-1500-tl-indirim-ve-vade-farksiz-5-aya-varan-taksit-firsati` — aynı URL yeni turda archive kümesinde TAZE hâliyle toplandı; bu live/ kopyası mükerrer
- `https://www.kuveytturk.com.tr/kampanyalar/kampanya-arsivi/avansasta-1500-tlye-varan-indirim-ve-vade-farksiz-5-aya-varan-taksit-firsati` — aynı URL yeni turda archive kümesinde TAZE hâliyle toplandı; bu live/ kopyası mükerrer
- `https://www.kuveytturk.com.tr/kampanyalar/kampanya-arsivi/avvada-500-tl-indirim-firsati` — aynı URL yeni turda archive kümesinde TAZE hâliyle toplandı; bu live/ kopyası mükerrer
- `https://www.kuveytturk.com.tr/kampanyalar/kampanya-arsivi/babalar-gunu-hediyenize-1000-tl-nakit-iade` — aynı URL yeni turda archive kümesinde TAZE hâliyle toplandı; bu live/ kopyası mükerrer
- `https://www.kuveytturk.com.tr/kampanyalar/kampanya-arsivi/bireysel-kredi-kartlariyla-indirimli-alisveris-altinbasta` — aynı URL yeni turda archive kümesinde TAZE hâliyle toplandı; bu live/ kopyası mükerrer
- `https://www.kuveytturk.com.tr/kampanyalar/kampanya-arsivi/bisiklet-finansmaninda-enerji-tasarrufu-haftasina-ozel-419-kar-orani-firsati` — aynı URL yeni turda archive kümesinde TAZE hâliyle toplandı; bu live/ kopyası mükerrer
- `https://www.kuveytturk.com.tr/kampanyalar/kampanya-arsivi/biz-bize-ile-yurt-disi-seyahatlerinizde-ayricaliklar-sizinle-scr` — aynı URL yeni turda archive kümesinde TAZE hâliyle toplandı; bu live/ kopyası mükerrer
- `https://www.kuveytturk.com.tr/kampanyalar/kampanya-arsivi/business-plus-ile-akaryakitta-indirim-firsati` — aynı URL yeni turda archive kümesinde TAZE hâliyle toplandı; bu live/ kopyası mükerrer
- `https://www.kuveytturk.com.tr/kampanyalar/kampanya-arsivi/business-plus-karta-ozel-yapi-malzemeleri-ve-mobilya` — aynı URL yeni turda archive kümesinde TAZE hâliyle toplandı; bu live/ kopyası mükerrer
- `https://www.kuveytturk.com.tr/kampanyalar/kampanya-arsivi/business-plus-karttan-vade-farksiz-3-taksit-imkani` — aynı URL yeni turda archive kümesinde TAZE hâliyle toplandı; bu live/ kopyası mükerrer
- `https://www.kuveytturk.com.tr/kampanyalar/kampanya-arsivi/business-plus-ve-milesandsmiles-business-ramazan-kampanyasi` — aynı URL yeni turda archive kümesinde TAZE hâliyle toplandı; bu live/ kopyası mükerrer
- `https://www.kuveytturk.com.tr/kampanyalar/kampanya-arsivi/business-plustan-1000-tl-indirim-firsati-scr` — aynı URL yeni turda archive kümesinde TAZE hâliyle toplandı; bu live/ kopyası mükerrer
- `https://www.kuveytturk.com.tr/kampanyalar/kampanya-arsivi/cocugunuzun-gelecegini-guvence-altina-almak-sizden-karne-hediyesi-bizden` — aynı URL yeni turda archive kümesinde TAZE hâliyle toplandı; bu live/ kopyası mükerrer
- `https://www.kuveytturk.com.tr/kampanyalar/kampanya-arsivi/dbs-fatura-odemelerinizde-100000-mil-firsati` — aynı URL yeni turda archive kümesinde TAZE hâliyle toplandı; bu live/ kopyası mükerrer
- `https://www.kuveytturk.com.tr/kampanyalar/kampanya-arsivi/dbs-firmalarina-akaryakit-indirimi` — aynı URL yeni turda archive kümesinde TAZE hâliyle toplandı; bu live/ kopyası mükerrer
- `https://www.kuveytturk.com.tr/kampanyalar/kampanya-arsivi?root=kendim-icin` — aynı URL yeni turda archive kümesinde TAZE hâliyle toplandı; bu live/ kopyası mükerrer
- `https://www.kuveytturk.com.tr/kampanyalar/kampanya-arsivi` — aynı URL yeni turda archive kümesinde TAZE hâliyle toplandı; bu live/ kopyası mükerrer
- `https://www.turkiyefinans.com.tr/tr-tr/kampanyalar/Sayfalar/Biten-Kampanyalar.aspx` — aynı URL yeni turda archive kümesinde TAZE hâliyle toplandı; bu live/ kopyası mükerrer
- `https://www.ziraatkatilim.com.tr/ticari/finansman-urunleri/surdurulebilirlik-temali-ticari-urunler/ges-cati-ges-ges-yatirim-ve-isletme-finansmani` — aynı URL yeni turda products kümesinde TAZE hâliyle toplandı; bu live/ kopyası mükerrer

</details>

## Doğrulanamayanlar (0)

Kayıt yok.
