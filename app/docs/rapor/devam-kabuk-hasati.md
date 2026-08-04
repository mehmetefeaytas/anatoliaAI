# Devam Notu — "Kabuk" Belge Hasatı (101 aday)

> Tarih: 2026-08-04. Yazan: kabuk-hasatı ajanı. Durum: **ölçüm tamamlandı,
> bekleyen hasat İŞİ YOK** (aşağıdaki gerekçeyle). İnternet kesintisi nedeniyle
> yeni tarayıcı isteği başlatılmadı — ancak 101 adayın **tamamı** kesintiden
> önce zaten tarayıcıyla denenmişti.

## 1. Ölçülmüş sonuç (tahmin değil)

| Ölçüm | Sayı |
|---|---:|
| Kabuk şüphelisi (görev tanımındaki sezgisel) | 101 |
| Tarayıcıyla yeniden hasat DENENEN | 101 / 101 |
| **Kurtarılan (yeni içerik yazılan)** | **0** |
| Tarayıcı metni statikle **bayt-aynı** çıkan | 98 |
| Gerçekten içeriksiz = kabuk (işaretlenen) | 14 |
| Sezgiselin **yanlış pozitifi** (zaten içerik taşıyor) | 87 |

### Neden 0 kurtarıldı — görevin öncülü yanlıştı

Görev tanımı "içerik JS ile üretiliyor, tek yol tarayıcı ile hasat" diyordu.
**Ölçüm bunu çürüttü:**

- 101 URL `src/scraping/fetcher.BrowserFetcher` (Playwright + Chromium 149)
  ile yeniden çekildi. Playwright **çalışıyor** ve **render ediyor** —
  fetcher'da kusur YOK.
- Buna rağmen çıkarılan metin **98/101'de bayt-aynı** uzunlukta geldi.
  Uzunluğu değişen 3 sayfa, içeriği dönen liste/karusel sayfalarıydı
  (kampanya listesi), kampanya belgesi değil.
- Yani bu sitelerin gövdesi **sunucuda render ediliyor**; statik çekim zaten
  sayfadaki her şeyi alıyordu.

Kalan 14 sayfada içerik **canlı sitede de yok**. `document.body.innerText`
ile doğrulandı: sayfa yalnızca menü + başlık + kırıntı yolu (breadcrumb) +
altbilgi yayınlıyor. Akordeon/sekme/`<details>` tıklaması da denendi —
her sayfada **aynı +358 karakter** geldi, bu da altbilgi menüsünün açılması,
içerik değil.

Örnek (Emlak Katılım, süresi dolmuş kampanya):
```
Çerez Politikası'nı hazırlanmıştır.
Emlak Konut Asansör – Emlak Katılım İş Birliği
Ana sayfa  Bireysel  Kampanyalar  Kampanya  Emlak Konut Asansör – ...
İletişim / Bize Yazın / Şube ve ATM'ler / ... (altbilgi)
```
Gövde metni hiç yok. Banka, süresi dolan kampanya sayfasını gövdesiz yayında
bırakıyor. **Kurtarılacak veri mevcut değil** — uydurma yapılmadı (CLAUDE.md §21).

### 87 yanlış pozitif — sezgiseldeki kusur

Görevdeki tarayıcı sezgiseli `MARK` listesinde `"ana sayfa"` ve `"müşteri ol"`
kullanıyor. Bunlar bu üç bankanın **her sayfasında** bulunan kırıntı yolu /
menü sözcükleri, çerez bandı işaretçisi değil. Bu yüzden gerçek içerik taşıyan
belgeler kabuk sanıldı. Ölçülen yanlış pozitif oranı **%86 (87/101)**.

- `kuveyt-turk`: 21/21 yanlış pozitif — **hiç gerçek kabuk yok**. Örn.
  `kampanya-arsivi-kampusten-ucuran-firsat.txt` 1182 karakter, tam kampanya
  koşulları ("AJet uçak bileti alımında 1000 TL'ye varan indirim", tarihler,
  referans kodu) içeriyor.
- Görev tanımındaki kanıt dosyası da yanlıştı:
  `kampanya-paraf-ile-ds-damatta-2000-tl-parafpara.txt` **2994 karakter** ve
  tam kampanya metni taşıyor; kabuk listesinde hiç değil. 287 karakterlik
  dosya `...pttavmcomda-pesin-fiyatina-2-taksit.txt`, farklı bir belge.

**Sonuç: bu 87 belgeye DOKUNULMADI.** İçerik taşıdıkları için `kabuk`
işareti konmadı; korpustan düşürülmemeleri gerekir.

## 2. Hâlâ bekleyen liste

**Yeniden hasat bekleyen URL YOK.** 101 adayın hepsi denendi. Aşağıdaki 14 URL
"bekleyen iş" değil, **kaynağında içeriksiz olduğu doğrulanmış** belgelerdir;
`content_status: kabuk` ile işaretlendiler (silinmedi — CLAUDE.md §3).

| Banka | Belge | txt | tarayıcı |
|---|---|---:|---:|
| turkiye-emlak-katilim | live/kampanya-emlak-konut-asansor-emlak-katilim-is-birligi | 381 | 428 |
| turkiye-emlak-katilim | live/kampanya-paraf-ile-pttavmcomda-pesin-fiyatina-2-taksit | 287 | 287 |
| turkiye-emlak-katilim | live/kurumsal-kampanyalar | 300 | 300 |
| turkiye-emlak-katilim | products/katilma-hesaplari-tfs-degerlenen-pesinat-katilma-hesabi | 331 | 331 |
| turkiye-emlak-katilim | products/konut-finansmani-cevreci-konut-finansmani | 295 | 295 |
| turkiye-emlak-katilim | products/yatirim-urunleri-sermaye-piyasasi-urunleri-2 | 477 | 477 |
| vakif-katilim | live/kampanyalar-mevcut-kampanyalar | 292 | 814 |
| vakif-katilim | live/tr-404 | 247 | 247 |
| vakif-katilim | products/bireysel-bankacilik-kad-sis-kuyumcu-altin-degerlendirme-sistemi | 430 | 430 |
| vakif-katilim | products/isim-icin-detay-altin-katilma-hesabi | 201 | 201 |
| vakif-katilim | products/isim-icin-detay-katilma-hesabi | 201 | 201 |
| vakif-katilim | products/isim-icin-detay-kosgeb-destekli-finansman | 201 | 201 |
| vakif-katilim | products/isim-icin-detay-kredi-karti | 201 | 201 |
| vakif-katilim | products/tarim-finansmanlari-elektronik-urun-senedi-karsiligi-kredi | 434 | 434 |

Ek not: `vakif-katilim/live/tr-404.txt` bir **404 hata sayfası**; korpusta
belge olarak durmaması gerekir (ayrı temizlik işi, bu görevin kapsamı değil).
`kurumsal-kampanyalar`, `kampanyalar-mevcut-kampanyalar` ve
`isim-icin-finansmanlar` ise **liste/dizin** sayfalarıdır, kampanya belgesi değil.

## 3. Çalışan yöntem / engeller

- **İşe yarayan araç:** deponun kendi `BrowserFetcher`'ı
  (`src/scraping/fetcher.py`). Playwright kurulu, Chromium 149.0.7827.55
  başlıyor, `available == True`. **MCP tarayıcısına gerek olmadı.**
- **Beklemeler:** `wait_until="domcontentloaded"` → `networkidle` (8–10 sn)
  → ek `wait_for_timeout(1500–2500)`. Bu üçlü yeterliydi; içerik hiçbir
  sayfada gecikmeli gelmedi.
- **robots.txt:** üç bankanın da tüm hedef URL'leri **izinli** (`izin`).
  Engelleyen site YOK, HTTP hatası YOK, rate-limit cezası YOK.
  Domain başına 3 sn gecikme uygulandı (CLAUDE.md §14).
- **Kritik tuzak — yönlendirme:** Emlak Katılım'da
  `/kampanyalar/kampanya?slug=<x>` biçimi `/kampanyalar?slug=<x>` **kampanya
  LİSTESİNE** yönleniyor ve 4166 karakterlik "kurtarılmış içerik" gibi
  görünüyor. Bu metin 40 farklı kampanyanın listesidir. Doğru `source_url`
  biçimi `/kampanyalar/kampanya/<slug>` (yol, sorgu değil). Yeniden hasat
  kodunda **`final_url` yol karşılaştırması + liste-işaretçisi sayımı +
  slug jeton örtüşmesi** kabul kapıları bu yüzden şart; yoksa korpus zehirlenir.
- `banks.yaml`'da üç bankaya da bu ölçümü anlatan yorum düşüldü ki ileride
  kimse `scrape_mode: js`'e çevirip boşa zaman harcamasın.

## 4. İnternet gelince ilk çalıştırılacak komut

Yeniden hasat gerekmiyor. Yapılacak tek şey **doğrulama**: 14 belgenin
kaynağında hâlâ içerik olmadığını teyit et (banka sayfayı sonradan
doldurmuş olabilir).

```bash
cd /Users/mehmetefeaytas/anatoliaaI/app
.venv/bin/python - <<'PY'
import json, pathlib, sys
sys.path.insert(0, ".")
from src.scraping.fetcher import BrowserFetcher, RateLimiter
from src.scraping.collector import _extract_main_text

bf = BrowserFetcher(limiter=RateLimiter(3.0), timeout_ms=45000)
print("tarayici:", bf.available, bf.unavailable_reason)
for mp in sorted(pathlib.Path("data/raw").rglob("*.txt.meta.json")):
    m = json.loads(mp.read_text(encoding="utf-8"))
    if m.get("content_status") != "kabuk":
        continue
    p = pathlib.Path(str(mp)[:-len(".meta.json")])
    old = len(p.read_text(encoding="utf-8"))
    r = bf.fetch(m["source_url"])
    new = len(_extract_main_text(r.html or "")) if r.ok else -1
    flag = "DOLMUS!" if new > old * 1.4 else "hala bos"
    print(f"{flag:9} {old:5} -> {new:5}  {p.name}")
bf.close()
PY
```

`DOLMUS!` çıkan bir belge olursa gövdesini `.txt`'ye yaz, `.meta.json`'da
`content_hash` / `text_chars` / `scraped_at` / `collection_method: browser`
güncelle ve `content_status` anahtarını **kaldır**. Dosya adını **asla**
değiştirme — anotasyon CSV'lerindeki `doc_id` bu adlara bağlı.

## 5. Değiştirilen dosyalar

- `app/data/raw/**/*.txt.meta.json` — 14 belgeye `content_status: kabuk`
  (8'i yeni; 6'sı zaten işaretliydi) + `recollection_attempt`,
  `recollection_method`, `recollection_result` ölçüm provenance'ı.
- `app/config/banks.yaml` — kuveyt-turk / vakif-katilim /
  turkiye-emlak-katilim bloklarına "js denendi, ölçüldü, kazanç yok" notu.
- `app/src/scraping/fetcher.py` — **DEĞİŞTİRİLMEDİ** (kusur bulunmadı).
- **Hiçbir `.txt` gövdesi değiştirilmedi** (kurtarılan belge olmadığı için).
