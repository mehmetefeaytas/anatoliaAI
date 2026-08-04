# DEVAM NOTU — Konut / Taşıt sınıf dengesi hasatı

> Yazıldı: 2026-08-04, oturum internet kesintisi nedeniyle yarıda kapandı.
> Veri commit'i: `8ee63b2` (106 yeni belge + `config/banks-classic.yaml`).
>
> İlgili: `config/banks-classic.yaml` · `docs/kampanya-turu-sinif-kurallari.md`
> `scripts/build_silver.py` · `src/extraction/silver/consensus.py`

---

## 1. DURUM ÖZETİ — okumadan devam etme

**Belgeler toplandı, ETİKETLENMEDİ.** Gümüşteki sınıf sayıları bu commit'te
**değişmedi**:

| Sınıf | Gümüşteki güncel sayı (ölçüldü) | Hedef | Eksik |
|---|---:|---:|---:|
| **Konut Finansmanı** | **13** | 20 | **7** |
| **Taşıt Finansmanı** | **9** | 20 | **11** |

Ölçüm komutu (tekrar üretilebilir):

```bash
.venv/bin/python -c "
import json,collections
c=collections.Counter(json.loads(l)['label'] for l in open('data/silver/silver.jsonl'))
print(c['Konut Finansmanı'], c['Taşıt Finansmanı'])"
```

`data/silver/` bu commit'te **HİÇ DEĞİŞTİRİLMEDİ** — `.bak` alma ihtiyacı
doğmadı, çünkü yazma yapılmadı.

### Sayılar neden artmadı

Üç oylu uzlaşma (`consensus.py`) bir belgeyi `silver` sayması için **iki
BAĞIMSIZ LLM oyu** ister: `proposals.jsonl` (etiketleyici) + `verdicts.jsonl`
(denetleyici). Etiketleyici repo DIŞINDA çalışır (şartname §5.10 —
açık-kaynak-olmayan bağımlılık teslim edilen sisteme giremez).

Bu oturumda etiketleme **kasten yapılmadı**. Gerekçe teknik değil,
**bütünlükle ilgili**: tek bir asistan oturumu hem etiketleyici hem
denetleyici rolünü oynarsa iki oy aslında **tek oy** olur.
`consensus.py`'nin kendi docstring'i bu başarısızlık kipini adıyla anıyor
("lastik damga") ve `VerifyVerdict.own_label`ın ayrı alan olmasının tek
sebebi bunu engellemek. Sayıyı 20'ye çıkarmak için sahte bir bağımsız
denetleyici üretmek, sınıf sayısını yükseltir ama **veri setinin kökenini
savunulamaz kılar**. Yapılmadı.

Yani: **sınıf sayıları, ikinci bağımsız etiketleyici turu koşulana kadar
artmayacak.** Bu bir ağ sorunu değil, bir rol-bağımsızlığı sorunu; internet
gelse bile aynı oturumun iki rolü oynaması sorunu çözmez.

---

## 2. İNTERNET GELİNCE İLK KOŞULACAK KOMUT

Hasata GEREK YOK — belgeler diskte ve commit'li. Doğrudan etiketlemeye geç:

```bash
cd app

# 1) 724 belgelik partiyi ve prompt'ları çıkar (OFFLINE, ağ istemez)
.venv/bin/python scripts/build_silver.py prepare \
    --docs data/raw-classic --out data/silver/batch.jsonl

# 2) (repo DIŞI) proposals.jsonl üret — etiketleyici rolü.
#    Mevcut 502 kayıt korunur; YALNIZ 222 yeni doc_id eklenecek.
#    Yeni doc_id'ler = products/ altındaki 106 belge + önceki turdan kalanlar.

# 3) (repo DIŞI, AYRI oturum/model) verdicts.jsonl üret — denetleyici rolü.
#    ADIM 2 İLE AYNI OTURUMDA YAPILMAZ (bkz. §1 gerekçe).
.venv/bin/python scripts/build_silver.py prepare-verify \
    --docs data/raw-classic --proposals data/silver/proposals.jsonl \
    --out data/silver/verify_batch.jsonl

# 4) Üç oylu uzlaşma — silver.jsonl'i YENİDEN ÜRETİR, önce yedek al!
cp data/silver/silver.jsonl data/silver/silver.jsonl.bak
.venv/bin/python scripts/build_silver.py merge \
    --docs data/raw-classic \
    --proposals data/silver/proposals.jsonl \
    --verdicts data/silver/verdicts.jsonl \
    --out-dir data/silver
```

`merge` çıktısında `sinif_dengesi_uyarilari` alanı Konut/Taşıt hâlâ 20'nin
altındaysa uyarır — hedefin tutup tutmadığını orası söyler.

### İki tuzak

1. **`merge` silver.jsonl'i baştan yazar**, eklemez. `proposals.jsonl`'daki
   ESKİ 502 kaydı silme, yoksa mevcut 416 gümüş etiket buhar olur.
2. **`load_proposals` mükerrer doc_id'de patlar** (sessiz üzerine yazma yok).
   Bu turda `products/` ile `live/` arasında **19 çakışma** çıktı ve
   temizlendi; yeni hasat yaparsan denetimi tekrarla:
   ```bash
   .venv/bin/python - <<'PY'
   from pathlib import Path; from collections import Counter
   c=Counter(f"{b.name}--{p.stem}" for b in Path('data/raw-classic').iterdir()
             if b.is_dir() for p in b.rglob('*.txt'))
   print("ÇAKIŞMA:", [k for k,v in c.items() if v>1])
   PY
   ```

---

## 3. BULUNAN GERÇEK ÜRÜN YOLLARI (hepsi HTTP 200 doğrulandı)

Dördü de "önceki tahminler 404 döndü" diye boş bırakılmış bankalardı.
**Ortak kök neden: dört bankanın hiçbiri ürünü "konut kredisi" diye
adlandırmıyor.** Tahmin bu yüzden çalışmıyordu.

### Akbank — `https://www.akbank.com`
Doğru önek `/krediler/...` (eski tahmin `/Sayfalar/...` biçimindeydi).
```
/krediler/konut-kredileri                      (hub, 6 alt ürün)
/krediler/konut-kredileri/akbank-konut-kredisi
/krediler/konut-kredileri/ilk-evim-konut-kredisi
/krediler/konut-kredileri/borc-transferi-kredisi
/krediler/konut-kredileri/emlakci-yonlendirmeli-kredi
/krediler/konut-kredileri/maas-musterilerine-ozel-kredi
/krediler/konut-kredileri/pesin-faiz-odemeli-konut-kredisi
/krediler/konut-kredileri/odeme-plani-turleri  (hub, 5 mortgage varyantı)
/krediler/tasit-kredileri                      (hub, 5 alt ürün)
/krediler/tasit-kredileri/0-km-tasit-kredisi
/krediler/tasit-kredileri/ikinci-el-tasit-kredisi
/krediler/tasit-kredileri/motosiklet-kredisi
/krediler/tasit-kredileri/togg-dijital-tasit-kredisi
/krediler/tasit-kredileri/akon-tasit-kredisi-sistemi
/kampanyalar/konut-kredilerine-bahari-getiren-kampanya
/kampanyalar/tasit-kredilerine-bahari-getiren-kampanya
```

### İş Bankası — `https://www.isbank.com.tr`
**Banka "konut" kelimesini ürün adında KULLANMIYOR → `/ev-kredisi`.**
Site ayrıca DÜZ: ürün yolları tek segmentli, `/tr/bireysel/...` hiyerarşisi
yok. Konut tarafında **tek** ürün sayfası var; alt ağaç yok (tarayıcıyla
doğrulandı, uydurulmadı).
```
/ev-kredisi                                (konut — TEK sayfa)
/tasit-kredisi
/aninda-tasit-kredisi
/kampanyalar/tasit-kredisi-kampanyalari    (liste, ~15 taşıt kampanyası)
```

### DenizBank — `https://www.denizbank.com`
**Ürün adı "mortgage", "konut" değil.**
```
/krediler/bireysel-bankacilik/mortgage-kredileri
/krediler/bireysel-bankacilik/kentsel-donusum-kredisi
/krediler/bireysel-bankacilik/tasit-kredisi
/krediler/bireysel-bankacilik/togga-ozel-tasit-kredisi
/krediler/kobi-bankaciligi/ticari-tasit
```
DİKKAT: `/hesap/konut` kredi DEĞİL, birikim hesabı (`Yatırım Ürünü`).

### VakıfBank — `https://www.vakifbank.com.tr`
Marka **"SarıPanjur Ev Kredisi"**. Ürünler hub'ın **BİR ALT** seviyesinde;
kampanya turu liste sayfasından tek seviye indiği için hub'ı alıp
çocuklarını kaçırıyordu (7 konut belgesi sessizce dışarıda kalmıştı).
```
/tr/bireysel/krediler/saripanjur-ev-kredisi                              (hub)
/tr/bireysel/krediler/saripanjur-ev-kredisi/saripanjur-konut-kredisi
/tr/bireysel/krediler/saripanjur-ev-kredisi/yesil-konut-kredisi
/tr/bireysel/krediler/saripanjur-ev-kredisi/kentsel-donusum-kredisi
/tr/bireysel/krediler/saripanjur-ev-kredisi/konut-finansmani-mortgage
/tr/bireysel/krediler/saripanjur-ev-kredisi/banka-gayrimenkulu-konut-isyeri-ve-arsa-alim-kredisi-kampanyasi
/tr/bireysel/krediler/saripanjur-ev-kredisi/oyak-uyelerine-ozel-konut-kredisi-kampanyasi
/tr/bireysel/krediler/saripanjur-ev-kredisi/tsk-uyelerine-ozel-konut-kredisi-kampanyasi
/tr/bireysel/krediler/tasit-kredileri
/tr/ticari/krediler/ticari-tasit-kredisi
```

---

## 4. DENENMİŞ VE BAŞARISIZ — TEKRAR DENEME

| Yol / kaynak | Sonuç | Not |
|---|---|---|
| `vakifbank.com.tr/tr/bireysel/krediler/konut-kredileri` | **404** | marka SarıPanjur |
| `vakifbank.com.tr/tr/bireysel/krediler/konut-kredisi` | **404** | aynı |
| `vakifbank.com.tr/tr/bireysel/krediler/ev-kredisi` | **404** | önek eksik |
| `.../saripanjur-ev-kredisi/kentsel-donusum` | **404** | doğrusu `-kredisi` ekli |
| `vakifbank.com.tr/XML/...sitemap-tr.xml` | **404** | robots.txt bildiriyor ama adres ölü; 164 KB gövde bir 404 sayfası. VakıfBank için sitemap YOK sayılmalı, tarayıcı gerekir. |
| `akbank.com/krediler/tasit-kredileri/cevre-dostu-tasit-kredisi` | **404** | sitemap'te DURUYOR ama ölü — sitemap bayat. Sitemap'te görmek kanıt değil. |
| `garantibbva.com.tr/sitemap/sitemap.xml` | 200 ama **işe yaramaz** | yalnızca 356 byte'lık sitemapindex; gerçek içerik `sitemap/sayfalar-sitemap.xml` |
| İş Bankası `/konut-kredisi`, `/konut-kredileri` | yok | sitemap'te hiç geçmiyor; ürün adı `/ev-kredisi` |
| TEB sitemap | **YOK** | robots.txt bildirmiyor; yalnız gezinme yollarıyla çalışılır |

---

## 5. KÖK NEDEN — neden ilk turda toplanmamışlardı

Eksiklik tesadüf değil, **yapısal**. `discover.rank()` kırpma sırasında
`/kampanya`yı 0. kovaya, ürün sayfalarını **EN SON** kovaya koyuyor. Klasik
bankalar konut/taşıtı KAMPANYA değil ÜRÜN sayfası olarak yayımladığı için
`max_docs` kırpması bu sayfaları **sistematik olarak** atıyordu.

En net kanıt: Garanti BBVA'da `/krediler/konut-kredisi` ve
`/krediler/tasit-kredisi` yolları config'de **VARDI**, ama 354 adaydan
`max_docs=90` kırpması sonrası korpusta Garanti'den **tek bir** konut/taşıt
belgesi yoktu.

**Çözüm:** kampanya turu değil **ürün turu** (`harvest_products`).
`rank_products()` `kredi`yi 1. kovaya alır → kırpmada hayatta kalır.
Ek olarak `product_patterns` konut/taşıt ürün ailesine daraltıldı; varsayılan
desenler (`kredi|hesap|kart|finansman...`) yüzlerce ilgisiz sayfa getirip
konut/taşıtı yine kırpmaya kurban ediyordu.

Koşulan komut (10 banka, ziraat hariç — bkz. §7):

```bash
.venv/bin/python -m src.scraping.harvest_products \
    --config config/banks-classic.yaml --raw-dir data/raw-classic \
    --only akbank,is-bankasi,denizbank,vakifbank,halkbank,garanti-bbva,yapi-kredi,ing,qnb,teb \
    --delay 3
```

---

## 6. TOPLANAN VERİNİN DOĞRULAMASI (ölçüldü)

- **106 yeni belge** (`data/raw-classic/*/products/`). Hasat 125 yazdı; 19'u
  `live/` altında zaten vardı, `products/` kopyaları silindi (aksi hâlde
  `load_proposals` mükerrer doc_id'de patlıyor). Sonuç: **724 tekil doc_id,
  çakışma 0**.
- **content_hash: 724/724 uyuşuyor.** Doğrulamayı **BAYT** alanında yap:
  meta'daki hash orijinal yanıt baytları üzerinde. Metni utf-8'e yeniden
  kodlayıp hash'lersen 724 belgenin 534'ü yanlışlıkla "bozuk" görünür —
  bu bir bütünlük hatası DEĞİL, ölçüm hatasıdır (Türk banka siteleri
  iso-8859-9 servis ediyor).
- **Kabuk denetimi:** 105/106 gerçek ürün metni (medyan **5509** karakter,
  min 390, max 72951). **1 kabuk:** `qnb--tasit-kredileri` (390 karakter,
  yalnız breadcrumb + nav bağlantıları). `MIN_DOC_CHARS=200` eşiğini geçtiği
  için otomatik denetime yakalanmadı; elle `content_status: kabuk`
  işaretlendi, **silinmedi**. Etiketlemeye girmemeli.
- Gövdesinde konut ürün terimi geçen **66**, taşıt **58** belge.

### Hedefin tutacağına dair ölçülmüş projeksiyon (SONUÇ DEĞİL)

Üç oydan biri olan deterministik kural katmanı (`RuleHintClassifier`,
offline) 106 yeni belgeyi şöyle bölüyor:

| Kural katmanı etiketi | Sayı |
|---|---:|
| Konut Finansmanı | 51 |
| Taşıt Finansmanı | 36 |
| Kart | 12 |
| Finansman | 6 |
| İhtiyaç Finansmanı | 1 |

**Bu bir üst sınırdır, sonuç değildir.** Kural katmanının ölçülmüş kendi
hatası var (sözcük sınırı düzeltmesinden önce korpusun %48'ini sahte Konut
yapıyordu) ve `docs/kampanya-turu-sinif-kurallari.md` gereği aşağıdakiler
etiketlemede **düşecek**:

- `akbank--birikim-hesaplari-devlet-katkili-konut-hesabi` → `Yatırım Ürünü`
  (kredi değil, birikim hesabı)
- `vakifbank--saripanjur-ev-kredisi-{ev-kredisi-sozlugu, kredi-basvuru-adimlari,
  odeme-yontemleri, sorularla-ev-kredisi, anlasmali-projeler}` → Kural 2
  gereği `null` (ürün sayfası değil: sözlük / SSS / rehber)
- `is-bankasi--bankamizi-taniyin-*` → basın duyurusu, ürün sayfası değil → `null`
- `qnb--kobi-kentsel-donusum-yap-sat` → ticari → `Finansman`
- `halkbank--www-halkbank-com-tr` → ana sayfa → `null`
- `akbank--tasit-kredileri-2-el-tasit-alirken-dikkat-etmeniz-gerekenler` → rehber → `null`
- `*-basvuru`, `*-randevu-talep-formu` → ölçülecek; TEB'de başvuru sayfaları
  gümüşe girmişti, emsal var.

Bu düşüşler sayıldıktan sonra bile **Konut ve Taşıt'ın ikisi de 20'yi rahatça
geçiyor** (kaba tahmin: Konut ~35-40, Taşıt ~25-30 net yeni). Ama bu **tahmin**;
gerçek sayı §2'deki `merge` koşulduktan sonra `silver_report.json`'da yazacak.

---

## 7. AÇIK UÇLAR

- **Ziraat Bankası ürün turuna girmedi.** `product_paths` yok ve
  `sitemap_urls` config'de kasten kapalı; `discover_products` bu durumda
  `paths=["/"]` fallback'ine düşüp ana sayfadan geniş gezinme yapıyor.
  Kontrolsüz olduğu için `--only` listesinden çıkarıldı. Ziraat'in
  konut/taşıt yolları zaten korpusta mevcut
  (`konut-gayrimenkul-konut-kredisi`, `tasit-tasit-kredisi`). Eklenecekse
  önce `product_paths` yazılmalı; sitemap'te yalnız iki `/basvurular/...`
  URL'si var.
- **`_collection_report.md` bu turda GÜNCELLENMEDİ** — `harvest_products`
  kendi raporunu `--out` ile ayrı JSON'a yazıyor (bu koşuda
  `/tmp/urun_raporu.json`, kalıcı değil). Kampanya turu raporu hâlâ 288
  belgelik eski turu anlatıyor, 106 yeni ürün belgesini içermiyor.
- Testler ve `ruff` bu oturumda **koşulmadı** (yalnız veri + config değişti,
  Python kodu değişmedi). Devam edildiğinde koşulmalı:
  `.venv/bin/python -m unittest discover -s tests` ve `ruff check`.
