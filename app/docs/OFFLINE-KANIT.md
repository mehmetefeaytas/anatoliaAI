# Offline / On-Prem Kanıt Paketi

**Durum:** ölçüldü — `--network none` koşusu **14/14 adım beklendiği gibi**,
**beklenmedik sonuç: 0 / 14**
**Koşu tarihi:** 2026-08-15T20:32:25Z (UTC)
**Üreten betik:** [`scripts/offline_proof.sh`](../scripts/offline_proof.sh)
**Ham transkript:** [`docs/offline-proof/transcript-20260815-233225.log`](offline-proof/transcript-20260815-233225.log) (5048 satır, kesilmemiş)
**Ham gecikme JSON:** [`docs/offline-proof/latency-20260815-233225.json`](offline-proof/latency-20260815-233225.json)
**Koşulan commit:** `9493c29` — **temiz ağaç**
**Sorumlu kalem:** Şartname §5.9 (dış servise bağımlı olmadan yerel çalışma), §8, §5.10
**⚠️ Kapsam sınırı (önce okuyun):** kanıt yalnız **API konteynerini** kapsar;
tam yığın ağsız denenmedi ve **imaj derlemesi internet ister**. Ayrıntı: **§0-b**.

> **Ağaç temizliği neden burada yazıyor.** Transkript başlığındaki satır
> `git durum : 1 degisik dosya` der. O tek dosya **koşumun kendi
> transkriptidir**: betik `exec > >(tee "$LOG")` ile log dosyasını başlığı
> basmadan önce açar, dolayısıyla `git status --porcelain` kendi çıktısını
> sayar. Kaynak ağacında commit'lenmemiş değişiklik yoktu. Karşılaştırma:
> 31 Temmuz koşumunda aynı satır **9 değişik dosya** diyordu ve o koşumun
> kanıtı gerçekten kirli bir ağaçtan geliyordu.

---

## Neden bu belge var

Şartname §5.9 sistemin dış servise bağımlı olmadan yerel (on-premise)
çalışmasını şart koşuyor; rubrikte **On-Prem Uygulanabilirlik %20**.

Bugüne kadar elimizde bu başlıkta **tek bir ölçüm yoktu**. `docker-compose.yml`
"offline ayağa kalkar" diyordu, `Dockerfile.api` yorumu var olmayan bir
`docs/OFFLINE-KANIT.md`'ye atıf yapıyordu. Bu belge o boşluğu kapatır ve
iddiaları **koşturulmuş komut çıktısıyla** değiştirir.

**Belgenin sözleşmesi:** burada yazan her sayı gerçekten koşturulmuş bir
komuttan gelir. Koşturulmayan her kalem `⏳ ölçülmedi — sebep: ...` ile
işaretlidir. Ara değer, tahmin, "olması beklenen" sayı yoktur.

---

## 1. Ölçüm ortamı

| Kalem | Değer |
|---|---|
| Host | Darwin 25.5.0, arm64 (Apple Silicon, MacBook Air), 10 çekirdek |
| Docker | CLI 29.5.3 · daemon 29.6.1 (linux/aarch64) |
| Konteyner | `linux/arm64`, Python 3.11.15, Linux 6.12.76-linuxkit, glibc 2.41 |
| Taban imaj | `python:3.11-slim@sha256:db3ff2e1…53a93` (digest'e sabit) |
| Teslim imajı | `anatolia-api:offline-proof` · ID `sha256:c3348bf6a451…` · **230 642 126 bayt (≈220,0 MiB)** |
| Git commit | `9493c29` (temiz ağaç) |
| LLM arka ucu | **kapalı** (`LLM_BACKEND=""` → `NullLLMExtractor`) |
| Sınıflandırıcı | `RuleHintClassifier` (BERTurk **kullanılmıyor**, bkz. §9) |
| Depolama | `/health` → `"backend":"sqlite"` (önceden doldurulmuş yerel DB) |

> ⚠️ **GPU yok.** Bu makinede GPU bulunmadığı için vLLM / Trendyol-LLM-8B-T1
> kolu **hiç koşturulmadı**. Aşağıdaki tüm gecikme sayıları **CPU, LLM'siz**
> yoldan gelir. Ayrıntı: §7 ve §9.
>
> **GÜNCELLEME (19 Ağu 2026):** yukarıdaki cümle *vLLM / Trendyol* kolu için
> hâlâ geçerli. Ancak **Ollama kolu** o tarihte ilk kez koşturuldu ve
> doğrulandı (CPU, `qwen2.5:7b-instruct`, katı mod `LLM_STRICT=1`): üç alanın
> üçü de doğru çıkarıldı. Bu koşumun kanıtı ayrı bir belgede —
> `docs/rapor/llm-kolu-kosum-kaniti.md`. Yani "sistem yalnız
> `NullLLMExtractor` ile çalışabiliyor" ifadesi artık doğru değil; bu
> belgedeki gecikme sayıları ise değişmedi, çünkü onlar LLM'siz yoldan
> ölçülmüştü ve o yol hâlâ varsayılan.

---

## 2. Kanıtın omurgası: negatif kontrol ve onun pozitif kontrolü

Bir sistemin offline çalıştığını göstermenin zayıf yolu, testlerin ağsız
geçtiğini söylemektir — testler ağı hiç denemiyor olabilir. Güçlü yol, ağ
erişimi **deneyen** bir çağrının izolasyon içinde **başarısız olduğunu**
göstermektir.

Ama bu da tek başına yetmez: prob başka bir sebeple (yazım hatası, eksik ikili,
yanlış hostname) her koşulda başarısız oluyorsa "izolasyon çalışıyor" diye
**yanlış** sonuç çıkarırız. Bu projede daha önce *"duman testi bağlantı hatasını
BAŞARILI raporladı"* sınıfından bir hata yaşandı.

Bu yüzden **aynı prob iki kez** koşturulur:

| Adım | Ortam | Beklenti | Gerçekleşen |
|---|---|---|---|
| 2 | ağ **AÇIK** (`docker run`) | proba **ULAŞMALI** | ✅ 4/4 ulaştı |
| 3 | ağ **KAPALI** (`--network none`) | proba **ULAŞAMAMALI** | ✅ 4/4 engellendi |

Adım 2 olmadan adım 3 hiçbir şey kanıtlamaz. İkna edici olan çift.

### 2.1 Adım 2 — ağ AÇIK, prob çalışıyor (ham çıktı)

```
ADIM 2: Prob dogrulama: ag ACIK iken prob ULASMALI (metaKontrol)
beklenti : cikis kodu 0
komut    : docker run --rm anatolia-api:offline-proof python -c <prob>
------------------------------------------------------------------------------
  [ULASILDI]   DNS huggingface.co       -> AG ERISIMI VAR
  [ULASILDI]   TCP 1.1.1.1:443          -> AG ERISIMI VAR
  [ULASILDI]   HTTPS huggingface.co     -> AG ERISIMI VAR
  [ULASILDI]   HTTPS pypi.org           -> AG ERISIMI VAR

engellenen: 0/4   ulasilan: 4/4
------------------------------------------------------------------------------
sonuc    : cikis kodu=0  sure=582 ms  -> BEKLENDIGI GIBI
```

### 2.2 Adım 3 — NEGATİF KONTROL, `--network none` (ham çıktı)

```
ADIM 3: NEGATIF KONTROL: --network none icinde ag ERISILEMEZ olmali
beklenti : cikis kodu 0 DEGIL (negatif kontrol)
komut    : docker run --rm --network none ... anatolia-api:offline-proof python -c <prob>
------------------------------------------------------------------------------
  [ENGELLENDI] DNS huggingface.co       -> gaierror: [Errno -3] Temporary failure in name resolution
  [ENGELLENDI] TCP 1.1.1.1:443          -> OSError: [Errno 101] Network is unreachable
  [ENGELLENDI] HTTPS huggingface.co     -> URLError: <urlopen error [Errno -3] Temporary failure in name resolution>
  [ENGELLENDI] HTTPS pypi.org           -> URLError: <urlopen error [Errno -3] Temporary failure in name resolution>

engellenen: 4/4   ulasilan: 0/4
------------------------------------------------------------------------------
sonuc    : cikis kodu=3  sure=210 ms  -> BEKLENDIGI GIBI
```

Dört prob **birbirinden bağımsız katmanları** sınar: DNS çözümleme (ad
çözümleme), ham TCP (yönlendirme), ve iki ayrı HTTPS hedefi (model deposu +
paket deposu). Hata mesajları farklı ve işletim sistemi düzeyinde
(`Errno -3`, `Errno 101`) — yani gerçekten çekirdek seviyesinde ağ yok, uygulama
katmanında bir zaman aşımı taklidi değil.

### 2.3 `curl` neden yok

Görev tanımında `curl -sS --max-time 5 https://huggingface.co` istenmişti.
`python:3.11-slim` taban imajı **curl içermez**. Bu adım koşturulsaydı
`command not found` da 0-dışı dönerdi ve *ağ izolasyonunun kanıtı sanılırdı* —
tam olarak kaçındığımız hata sınıfı. Betik bu yüzden `curl`'ün varlığını **ayrı
olarak** sınar ve yoksa adımı atlayıp gerekçesini transkripte yazar:

```
NOT: imajda 'curl' YOK (python:3.11-slim taban imaji curl icermez).
     Bu yuzden 'curl -sS --max-time 5 https://huggingface.co' adimi
     KOSTURULMADI. Kosturulsa 'command not found' da 0-disi donerdi ve
     ag izolasyonunun kaniti SANILIRDI — bu tam olarak kacinilan hata.
     Ayni is adim 3'teki stdlib probu ile, bagimliliksiz yapiliyor.
```

Aynı iş stdlib probuyla, bağımlılıksız ve daha ayrıntılı yapılıyor.

---

## 3. `--network none` içinde koşan gerçek iş

Aşağıdakilerin hepsi **ağı tamamen kapatılmış** konteynerde koştu.

| # | Adım | Çıkış | Süre | Sonuç |
|---|---|---|---|---|
| 1 | `docker build -f Dockerfile.api` | 0 | 660 ms (önbellekli) | ✅ |
| 2 | Prob doğrulama (ağ açık) | 0 | 582 ms | ✅ |
| 3 | **NEGATİF KONTROL** (ağ kapalı) | 3 | 210 ms | ✅ |
| 4 | Test paketi (`unittest discover`) | 0 | 20 028 ms | ✅ |
| 5 | `eval.properties --raw-dir data/raw` | 0 | 58 877 ms | ✅ |
| 6 | `eval.run_eval --gold …` | 0 | 353 ms | ✅ |
| 7 | `eval.ablation --gold …` | 0 | 209 ms | ✅ |
| 8 | `scripts.latency_bench --recursive` | 0 | 160 120 ms | ✅ |
| 9 | Offline ortam değişkenleri | 0 | 227 ms | ✅ |
| 10 | `pip list` dökümü | 0 | 355 ms | ✅ |
| 11 | `trafilatura` yok (negatif kontrol) | 1 | 350 ms | ✅ |
| 12 | `trafilatura` import edilemez | 0 | 158 ms | ✅ |
| 13 | **API sunucusu ağsız ayağa kalkıyor** | 0 | 2 914 ms | ✅ |
| 14 | İmaj künyesi | 0 | 52 ms | ✅ |

**beklenmedik sonuç: 0 / 14**

> Tablodaki 660 ms **önbellekli** derlemedir (yalnız `COPY scripts/` katmanı
> yeniden koştu). Aynı gün soğuk derleme (`pip install` katmanı dahil)
> **34 745 ms** sürdü — [`transcript-20260815-230505.log`](offline-proof/transcript-20260815-230505.log)
> adım 1. Her iki sayı da transkriptlerdedir.
>
> **Derleme adımı ağsız DEĞİLDİR** — `docker build` `pip install` yapar ve
> internet ister. Adım 1 kapsam gereği ağ açıkken koşar; ağsızlık iddiası
> **adım 3'ten sonrasını** kapsar (bkz. §0-b kapsam sınırı).

### 3.1 Testler (ham kuyruk)

```
Ran 2999 tests in 19.199s

OK (skipped=272)
```

> Betik test sayısını **yazmaz**. Sabit bir "345 test" ifadesi paket büyüdükçe
> sessizce yalan olurdu; gerçek sayı her koşuda transkriptteki `Ran N tests`
> satırındadır. Bu koşuda 2 999 test toplandı, hepsi **OK**.

#### 3.1.1 Atlanan 272 test — gizlenmiyor, gerekçelendiriliyor

`skipped=272` bir kusur değil, **kapsam kararıdır**: teslim imajı yalnız
`requirements-api.txt` kurar ve içinde **`git` yok, `httpx2` yok, `web/` yok**.
O üç şeye ihtiyaç duyan testler teslim ortamında koşamaz.

Gerekçeler kodda taşınır — `tests/_ortam_gereksinimleri.py`:

| Prob | Ne eksik | Neden bilerek eksik |
|---|---|---|
| `git_var()` | `git` ikilisi | Teslim edilen sistem test aracına ihtiyaç duymaz |
| `istemci_var()` | `starlette.testclient` → `httpx2` | Yalnız test aracı; CI'da ayrı `test-with-deps` işi kurar |
| `arayuz_var()` | `web/app` | `Dockerfile.api` `web/` kopyalamaz; API imajı arayüzü servis etmez |

Ayrım şudur: **bağımlılık yok → SKIP**, **kod yanlış → FAIL**. Bu ayrım
ölçülmüş bir sorundan doğdu: kanıt 15 gün sonra ilk kez koşulduğunda teslim
imajının test paketi `errors=52` ile çöktü ve hiçbiri gerçek kusur değildi —
ama `ERROR` sayıldıkları için **gerçek bir kusur o yığının içinde
görünmezdi**.

Atlanan test sayısı **raporlanan bir iddiadır**, saklanmaz: `README.md`
"Test" satırında yazar ve `scripts/kanit_tazeligi.py` onu denetler. Atlamayı
"şu an geçmiyor" gerekçesiyle kullanmak kapıyı kapatmak değil **sökmek**
olur; bu modül yalnız **ortam** probları taşır.

### 3.2 Değişmez denetimi (ham çıktı)

```
1782 belge (1597 tanesinde en az bir alan çıktı; 185 boş belgede denetim hiçbir şey
test etmiyor — kapsam 89.6%) — tüm değişmezler GEÇTİ (0 ihlal)
```

### 3.3 Değerlendirme ve ablasyon (ham çıktı, kısaltılmadı)

```
konfig : kural — yalnız kural katmanı (regex + normalizasyon), LLM kapalı — RESMÎ VARSAYILAN (K-2)
gold   : data/gold/gold.sample.json (3 kayıt, alt küme 'all' -> 3 belge)

=== KURAL / strict — TÜM VAKALAR ===
MİKRO                   1.000  1.000  1.000    9    0    0    0    0   27
MAKRO (F1 ort.)                       1.000
MİKRO (yapısal)         1.000  1.000  1.000    9    0    0    0    0   24   <- kampanya_kosullari HARİÇ
MAKRO (yapısal)                       1.000

=== HATA SINIFLARI ===
çıkarım hatası (bilgi metinde VAR, doğru alınamadı): 0.000  [0/9]
halüsinasyon (bilgi metinde YOK, değer uyduruldu): ölçülemedi (gold'da absent kararı yok)  [0/0]
metrik dışı bırakılan (gold karar vermemiş) alan-kararı: 27  — bilinmeyen lehimize sayılmadı

mikro-F1 %95 GA: 1.000 [1.000–1.000]  (belge düzeyi bootstrap, n=3 belge, 1000 örnek, seed=42)

=== ABLASYON — eşleştirici 'strict' ===
konfig            F1(tüm)   makro  F1(zor)    TP    FP    FN   UYD  mikro-F1 %95 GA
kural               1.000   1.000    1.000     9     0     0     0  1.000 [1.000–1.000]
llm             ÖLÇÜLMEDİ   (bkz. NOTLAR)
hibrit          ÖLÇÜLMEDİ   (bkz. NOTLAR)
hibrit-verify   ÖLÇÜLMEDİ   (bkz. NOTLAR)

=== İSTATİSTİKSEL KARŞILAŞTIRMA ===
Karşılaştırılacak en az iki ÖLÇÜLEBİLEN kol yok.
```

> **Bu tablodan doğruluk sonucu çıkarmayın.** `gold.sample.json` yalnızca **3
> kayıt** içerir; F1=1.000 istatistiksel olarak anlamsızdır (güven aralığı da
> dejenere: `[1.000–1.000]`, n=3). Buradaki kanıt **doğruluk değil**, bu
> boru hattının **ağsız koşabildiğidir**. Doğruluk kanıtı gold setin
> büyümesini bekliyor ve bu belgenin konusu değil.

### 3.4 Offline ortam değişkenleri (ham çıktı)

```
ADIM 9: Offline ortam degiskenleri (HF_HUB_OFFLINE vb.)
komut    : docker run --rm --network none ... anatolia-api:offline-proof \
             sh -c 'env | grep -E "OFFLINE|TELEMETRY|UPDATE_CHECK" | sort'
------------------------------------------------------------------------------
HF_HUB_DISABLE_TELEMETRY=1
HF_HUB_DISABLE_UPDATE_CHECK=1
HF_HUB_OFFLINE=1
TRANSFORMERS_OFFLINE=1
------------------------------------------------------------------------------
sonuc    : cikis kodu=0  sure=227 ms  -> BEKLENDIGI GIBI
```

> ⚠️ **`ANATOLIA_OFFLINE=1` bu listeden ÇIKARILDI — ve çıkarılması
> düzeltmedir.** Belgenin 31 Temmuz sürümü bu bayrağı kanıt olarak
> gösteriyordu. Bayrak 2026-08-08'de `a3c2f05` commit'iyle koddan
> kaldırıldı; commit mesajının gerekçesi: *"repoda hiçbir yerde okunmuyordu,
> yani offline olduğumuza dair **SAHTE** bir sinyaldi"*.
>
> Hiçbir kod yolunun okumadığı bir değişkeni "offline kanıtı" diye
> göstermek, tam olarak bu belgenin var oluş sebebine aykırıdır: kanıt,
> **etkisi olan** bir şeyi ölçmelidir. Yukarıdaki dört değişkenin dördü de
> `huggingface_hub` / `transformers` tarafından gerçekten okunur ve ağ
> davranışını değiştirir. Kanıt artık yalnız onlara dayanıyor.
>
> Bu satırın kaybı kanıtı **zayıflatmaz**: ağsızlığın asıl kanıtı ortam
> değişkeni beyanı değil, adım 3'teki negatif kontrol ile adım 4–13'ün
> `--network none` içinde koşmasıdır. Ortam değişkenleri yalnız "kütüphane
> kendiliğinden ağa çıkmayı denemesin" kemeridir.

### 3.5 API sunucusu `--network none` içinde ayağa kalkıyor (adım 13)

Adım 4–12 **toplu iş (batch)** kanıtıydı. Şartname §5.9 çalışan bir **servis**
istiyor; *"testler ağsız geçti"* ile *"sunucu ağsız ayağa kalktı"* farklı
iddialardır. Adım 13 ikincisini ölçer: konteyner başlatılır, HTTP istekleri
**konteynerin İÇİNDEN** `127.0.0.1`'e atılır (dışarı çıkış yok), bellek
ölçülür, konteyner durdurulur.

```
konteyner : 63172698aaca…
hazir olma suresi : ~1 sn

--- /health (konteyner ICINDEN, localhost) ---
{"status":"ok","llm":false,"backend":"sqlite"}

--- /banks (ilk 300 karakter) ---
[{"slug":"adil-katilim","name":"Adil Katılım","website_url":"https://www.adilkatilim.com.tr",
"bddk_active":true},{"slug":"albaraka","name":"Albaraka Türk","website_url":
"https://www.albaraka.com.tr","bddk_active":true},{"slug":"dunya-katilim","name":"Dünya Katili…

--- calisma zamani kaynak kullanimi ---
BELLEK=39.21MiB / 7.75GiB  CPU=0.67%  PID=2

--- sunucu gunlugu ---
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     127.0.0.1:38256 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:38260 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:38272 - "GET /banks HTTP/1.1" 200 OK
```

Üç bulgu:

1. Sunucu **~1 saniyede** hazır — demo için fazlasıyla yeterli.
2. `/health` `llm:false` diyerek LLM'in kapalı olduğunu **dürüstçe** raporluyor;
   `backend:"sqlite"` diyerek de hangi depoyu kullandığını söylüyor. Sahte bir
   "hazır" yok; servis neyin çalışmadığını söylüyor.
3. `/banks` gerçek veri dönüyor (çıktı transkriptte **300 karakterde kesildi**,
   ilk üç banka görünüyor; `config/banks.yaml` 10 banka tanımlıyor ve
   `run_pipeline` hepsini kaydediyor).

---

## 4. Betiğin gerçekten hata yakaladığının kanıtı

Yeşil bir koşu, harness'ın çalıştığını değil, sistemin o an sağlam olduğunu
gösterir. Harness'ın **lastik damga olmadığını** göstermek için: ara koşulardan
biri gerçek bir kırılmayı yakaladı ve betik 0-dışı çıktı.

Bu iddianın kanıtı **iki ayrı tarihten** geliyor.

### 4.1 Bugünkü koşum: ilk iki deneme KIRMIZI yandı (2026-08-15)

Yetkili koşum (23:32:25) üçüncü denemeydi. Ondan önceki iki deneme aynı
adımda beklenmedik sonuç verdi ve betik **`exit 1`** ile "kanıt paketi
GEÇERSİZ" dedi:

| Koşum | Transkript | Adım 4 | Sonuç |
|---|---|---|---|
| 23:05:05 | [`transcript-20260815-230505.log`](offline-proof/transcript-20260815-230505.log) | kod 1 — **BEKLENMEDIK** | 1 adım beklenmedik → GEÇERSİZ |
| 23:25:58 | [`transcript-20260815-232558.log`](offline-proof/transcript-20260815-232558.log) | kod 1 — **BEKLENMEDIK** | 1 adım beklenmedik → GEÇERSİZ |
| **23:32:25** | [`transcript-20260815-233225.log`](offline-proof/transcript-20260815-233225.log) | kod 0 | **14/14, 0 beklenmedik** |

İkinci koşumun kalan kırığı tek bir testti:

```
FAIL: test_dolu_dosyadan_SIFIR_kayit_HATA_verir
      (test_lisans_kapisi.TestStdlibAyristiriciParitesi.test_dolu_dosyadan_SIFIR_kayit_HATA_verir)
Ran 2999 tests in 19.381s
FAILED (failures=1, skipped=272)
```

Kırık düzeltildikten sonra üçüncü koşum `Ran 2999 tests … OK (skipped=272)`
verdi. Aynı gün, aynı harness, aynı imaj — **kırmızıyken kırmızı, yeşilken
yeşil** raporladı. Lastik damga değil.

### 4.2 31 Temmuz koşumu (ilk kanıt)

**Transkript:** [`transcript-20260731-134646.log`](offline-proof/transcript-20260731-134646.log)

```
4   Test paketi (345 test) — --network none            1      648      BEKLENMEDIK
...
adim sayisi        : 13
beklenmedik sonuc  : 1

SONUC: 1 ADIM BEKLENMEDIK. Kanit paketi GECERSIZ.
```

Kök neden (o an paralel geliştirilen `tests/test_run_eval.py` dosyasında
eksik `import contextlib`):

```
ERROR: test_basarili_kosum (test_run_eval.TestCLI.test_basarili_kosum)
NameError: name 'contextlib' is not defined
```

Bu kırılma bizim dosyalarımızda değildi ve sonraki koşudan önce düzeltildi;
buraya **betiğin sessizce yeşil raporlamadığının kanıtı** olarak konuldu.

---

## 5. Digest pin tablosu (tekrar-üretilebilirlik)

Önceki `docker-compose.yml` üç imajı da **hareketli etiketle** (`:pg16`,
`:latest`) çekiyordu. "Offline **ve** tekrar üretilebilir" iddiası hareketli
etiketle teknik olarak yanlıştır: aynı dosya üç ay sonra farklı imajlar çeker ve
jürinin gördüğü sistem bizim test ettiğimiz sistem olmaz.

Digest'ler **2026-07-31'de** `docker buildx imagetools inspect <imaj>` ile
gerçekten çözüldü (uydurulmadı):

| Bileşen | Etiket | Digest (çoklu-mimari indeks) | Sıkıştırılmış boyut (linux/arm64) |
|---|---|---|---|
| PostgreSQL + pgvector | `pgvector/pgvector:pg16` | `sha256:a36250871de0833b8757561c72f2477ef1ddd1101afa4e617fb552e0de514c6b` | 154,1 MB (16 katman) |
| vLLM sunucusu | `vllm/vllm-openai:latest` | `sha256:ffb2d59b1c059a5bd8d781320c9f5189de8293693b7d95da54befddaa54abf52` | **10 349,3 MB** (32 katman) |
| Ollama (yedek) | `ollama/ollama:latest` | `sha256:4dea9fb511947e24a84237bb636b0203abcb2ff0d3fbc7b4ff865deb91362131` | 2 774,1 MB (4 katman) |
| API taban imajı | `python:3.11-slim` | `sha256:db3ff2e1800a8581e2c48a27c3995339d47bdf046da21c7627accd3d51053a93` | — (teslim imajına gömülü) |

> `⏳ 2026-08-15 koşumunda yeniden çözülmedi — sebep: kanıt betiği digest
> çözümlemesi yapmaz (ağ ister), yalnız API taban imajını kullanır.` Yukarıdaki
> dört digest 2026-07-31 ölçümüdür. **API taban imajı** satırı bugünkü koşumda
> dolaylı olarak doğrulandı: derleme günlüğü
> `FROM docker.io/library/python:3.11-slim@sha256:db3ff2e1…53a93` satırını
> basıyor (transkript adım 1), yani `Dockerfile.api` hâlâ aynı digest'e sabit.
> Diğer üç satır (Postgres, vLLM, Ollama) **tazelenmedi**.

Yenilemek için:

```bash
docker buildx imagetools inspect pgvector/pgvector:pg16 | grep Digest
```

> Digest yenilenirse bu tablo **ve** `docker-compose.yml` birlikte güncellenmeli;
> aksi halde belge ile dosya çelişir.

### 5.1 Model lisansı — vLLM kolu korundu

`--model Trendyol/Trendyol-LLM-8B-T1` **çıkarılmadı**. Lisans zinciri
2026-07-31'de doğrulandı: `license: Apache-2.0`, zincir
`Qwen3-8B-Base → Qwen3-8B → Trendyol-LLM-8B-T1`. Zincirde Llama/Gemma **yok**,
ticari-olmayan kısıt **yok** → §5.10 uyumlu.

> ℹ️ Bu bölüm yazılırken `docs/model-license-audit.md` hâlâ 2026-07-27 tarihli
> sürümdeydi ve modeli `⛔ BLOKE` listeliyordu; burada bir çelişki kayda
> geçirilmişti. **Çelişki aynı gün kapatıldı** (commit `009c89e`): denetim
> belgesi 2026-07-31'de güncellendi, model `✅` oldu ve zincir kanıtı
> (`license: Apache-2.0`, *"free for commercial and research use"*,
> `base_model: Qwen/Qwen3-8B`) belgeye alıntılandı. İki belge artık uyumlu.

---

## 6. `trafilatura` (GPLv3+) teslim imajında YOK — ölçülmüş kanıt

`docs/model-license-audit.md` §2'ye göre `requirements.txt` yorumunda `# GPLv3+`
işareti vardı ve GPLv3, projenin Apache-2.0 ile dağıtım şartıyla (§8) uyumsuz.
Karar: teslim imajına (`requirements-api.txt`) alınmayacak. **Kanıtı:**

Teslim imajının tam paket dökümü (adım 10, ham, kesilmemiş):

```
annotated-doc==0.0.5      idna==3.18                setuptools==79.0.1
annotated-types==0.8.0    packaging==26.2           soupsieve==2.9.2
anyio==4.14.2             pip==24.0                 starlette==1.6.0
beautifulsoup4==4.15.0    psycopg-binary==3.3.4     typing-inspection==0.4.4
click==8.4.2              psycopg==3.3.4            typing_extensions==4.16.0
fastapi==0.141.1          pydantic==2.13.4          uvicorn==0.52.3
h11==0.16.0               pydantic_core==2.46.4     wheel==0.46.3
```

**21 paket**, tamamı MIT / BSD / Apache-2.0 / PostgreSQL / LGPL(dinamik).
**`trafilatura` listede yok.**

> 31 Temmuz koşumunda 22 paket vardı; aradaki fark `pgvector==0.5.0`'ın
> düşmesidir. Teslim imajı bu koşumda SQLite ile ayağa kalkıyor
> (`/health` → `"backend":"sqlite"`, §3.5) — pgvector yalnız Postgres
> koluyla gerekir ve o kol bu pakette **ölçülmedi** (§10).

İki bağımsız negatif kontrol:

```
ADIM 11: trafilatura teslim imajinda YOK (grep bos donmeli)
komut    : ... sh -c 'pip list --format=freeze | grep -i trafilatura'
------------------------------------------------------------------------------
                                    <boş — hiçbir satır eşleşmedi>
------------------------------------------------------------------------------
sonuc    : cikis kodu=1  sure=350 ms  -> BEKLENDIGI GIBI

ADIM 12: trafilatura import EDILEMEZ (ikinci, bagimsiz kanit)
------------------------------------------------------------------------------
trafilatura find_spec: None
------------------------------------------------------------------------------
sonuc    : cikis kodu=0  sure=158 ms  -> BEKLENDIGI GIBI
```

`grep`'in boş dönmesi tek başına zayıf kanıttır (`pip` çalışmasaydı da 1
dönerdi); bu yüzden adım 10 tam listeyi basar ve adım 12 `importlib` ile
bağımsız olarak doğrular. Üçü birlikte kesin.

> Karar ve gerekçe `docs/model-license-audit.md` §2'ye aittir; bu belge onu
> **düzenlemez**, yalnızca ölçülmüş kanıtını sağlar.

### 6.1 Yan bulgu: `bs4` sapması (düzeltildi)

> 📌 **Bu bölüm 31 Temmuz koşumunun kaydıdır**; içindeki sayılar (1696 belge,
> imaj boyutu) o günün fotoğrafıdır ve bilerek dondurulmuştur — bir düzeltmenin
> gerekçesi, düzeltmenin yapıldığı andaki ölçümdür. Düzeltmenin **hâlâ yürürlükte
> olduğu** bugünkü koşumdan doğrulanıyor: `beautifulsoup4==4.15.0` ve
> `soupsieve==2.9.2` yukarıdaki 2026-08-15 paket dökümünde duruyor.

Ölçüm sırasında bulundu: `src/scraping/collector._extract_main_text`,
`beautifulsoup4` yoksa `except ModuleNotFoundError` ile **sessizce**
`normalize_text(html)`'e düşüyor. `requirements-api.txt`'te bs4 olmadığı için
teslim konteyneri, geliştirme ortamından **farklı metin** üretiyordu:

| Ortam | bs4 | 1696 belgede ortalama karakter |
|---|---|---|
| Geliştirme (host) | var | **4 317** |
| Teslim imajı (önce) | yok | **6 232** (+%44 menü/altbilgi gürültüsü) |
| Teslim imajı (sonra) | var | **4 320** ✅ |

Ham veri: [`latency-20260731-133540.json`](offline-proof/latency-20260731-133540.json)
(önce, `avg_chars: 6232`) ve
[`latency-20260731-135051.json`](offline-proof/latency-20260731-135051.json)
(sonra, `avg_chars: 4320`).

Testler yeşil olduğu için hata görünmüyordu — tam olarak "sessiz bozulma"
sınıfı. `beautifulsoup4` (MIT, saf Python) + `soupsieve` ince imaja eklendi;
imaj **100 802 593 → 101 208 799 bayt** büyüdü (**+406 KB**, %0,4). Bu bedel
karşılığında teslim imajı ile geliştirme ortamı aynı metni üretiyor.

On-prem kanıtının anlamı, **teslim edilen imajın test edilen sistemle aynı
davranmasıdır**; bu sapma kapatılmadan yukarıdaki hiçbir ölçüm teslim edilen
sistemi temsil etmiyordu.

---

## 7. Gecikme (latency) — üç yol ayrı ayrı

**Ölçüm:** `python -m scripts.latency_bench --recursive --iterations 3`,
**`--network none` konteyneri içinde**, **3 437** gerçek banka belgesi
(ortalama **4 098** karakter), toplam **14 085 382** karakter.
Ham JSON: [`latency-20260815-233225.json`](offline-proof/latency-20260815-233225.json)

| Yol | n | p50 | p95 | p99 | max | ortalama |
|---|---|---|---|---|---|---|
| **(a) kural-only** `extract_all()` | 10 311 | **1,40 ms** | 7,07 ms | 17,76 ms | 345,67 ms | 2,78 ms |
| **(b) hibrit boru hattı** `build_campaign()` | 10 311 | **1,80 ms** | 9,53 ms | 21,03 ms | 284,93 ms | 3,48 ms |
| **(c) chatbot** `Chatbot.ask()` | 504 | **2,74 ms** | 16,10 ms | 16,99 ms | 44,57 ms | 4,40 ms |

> **Konteyner-dışı (host) karşılaştırma bu koşumda tekrarlanmadı.** Elimizdeki
> tek host ölçümü **31 Temmuz** tarihlidir
> ([`latency-host-20260731.json`](offline-proof/latency-host-20260731.json):
> kural p50 1,05 ms · hibrit p50 1,67 ms · chatbot p50 6,47 ms) ve o gün
> **1 696 belgelik** bir korpusla alınmıştı. Bugünkü konteyner sayıları
> **3 437 belgelik** korpustan geliyor; iki ölçüm farklı korpuslar olduğu için
> yan yana konup "konteyner cezası şu kadar" denemez. O gün ölçülen konteyner
> ↔ host farkı kural ve hibrit yollarında ihmal edilebilirdi;
> `⏳ 2026-08-15'te yeniden ölçülmedi — sebep: host koşumu bu pakette
> koşturulmadı.`

### 7.1 "Önce kural" mimarisi sayıyla gerekçelendi

CLAUDE.md §3 "önce kural, sonra LLM" kararını ilan ediyordu ama destekleyen
ölçüm yoktu. Artık var: **kural yolu belge başına medyan 1,40 ms**, p99
17,76 ms. Yerel 8B bir LLM'in tek çağrısı tipik olarak **saniyeler**
mertebesindedir. Yüksek güvenle kuralla çıkan alanı LLM'e göndermemek, uçtan
uca gecikmeyi **üç mertebe** düşürüyor. Karar doğrulandı.

### 7.2 ⚠️ Bu tablonun okunma biçimi — LLM DAHİL DEĞİL

`LLM_BACKEND` boş olduğu için `default_extractor()` **`NullLLMExtractor`**
döndürür. Yani (b) ve (c) satırları boru hattının **LLM dışı** kısmıdır.

Bu bilinçli bir ölçümdür — teslim edilen offline demo tam olarak bu
konfigürasyonda koşar (CLAUDE.md §11, önceden doldurulmuş DB). Ama
**"hibrit gecikmesi" diye 8B model çıkarımını içeren bir sayı sanılmamalı.**

`⏳ ölçülmedi — sebep: bu makinede GPU yok, vLLM/Trendyol-LLM-8B-T1 kolu
hiç çalıştırılmadı.` Ölçmek için:

```bash
LLM_BACKEND=vllm VLLM_URL=http://localhost:8001 \
  python -m scripts.latency_bench --recursive
```

Betik hangi arka ucun aktif olduğunu başlıkta basar; sahte "hibrit = kural"
satırı üretmez.

### 7.3 Kapanan bulgu: chatbot p95/p99 artık yüksek değil

31 Temmuz koşumunda chatbot p50 12,48 ms iken p95 **325,02 ms**, p99
**351,36 ms** ölçülmüştü (~26× yayılım) ve bu bir **performans borcu** olarak
kayda geçmişti: 4 dakikalık demoda RAG sorusu sorulursa yarım saniyelik
duraklama görünürdü.

**2026-08-15 ölçümünde borç kapanmış görünüyor** — üstelik korpus 1 696'dan
3 437 kampanyaya, yani iki katına çıkmışken:

| Ölçüt | 2026-07-31 | 2026-08-15 |
|---|---|---|
| korpus | 1 696 kampanya | **3 437 kampanya** |
| p50 | 12,48 ms | **2,74 ms** |
| p95 | 325,02 ms | **16,10 ms** |
| p99 | 351,36 ms | **16,99 ms** |
| max | 368,53 ms | **44,57 ms** |
| ortalama | 155,11 ms | **4,40 ms** |

`⏳ ölçülmedi — sebep:` bu belge **hangi değişikliğin** iyileşmeyi getirdiğini
ölçmedi. İki koşum arasında 498 commit var ve aradaki farkı ayrıştıran bir
ablasyon koşturulmadı. Burada iddia edilen tek şey **sayıların kendisidir**:
iki ham JSON dosyası yan yana duruyor, yorum onların üstünde değil yanında.

Demoya etkisi doğrudan: RAG kolunda artık yarım saniyelik duraklama beklenmiyor.

---

## 8. Kaynak tüketimi

Ayrıntılı tablo ve profil kırılımı: [`kaynak-tuketimi.md`](kaynak-tuketimi.md)

Özet (hepsi `--network none` konteyner koşusundan, gerçekten ölçüldü):

| Kalem | Ölçülen değer | Kaynak |
|---|---|---|
| Teslim imajı (API) boyutu | 230 642 126 bayt (≈220,0 MiB) | transkript adım 14 |
| API sunucusu çalışırken bellek (boşta) | **39,21 MiB**, 2 PID, %0,67 CPU | transkript adım 13 |
| API hazır olma süresi (`--network none`) | **~1 s** | transkript adım 13 |
| Tepe RSS (çıkarım süreci, 3 437 belge) | **216,2 MB** | gecikme JSON `peak_rss_mb` |
| Demo soğuk başlatma (`build_demo_repo`) | **22,0 ms** | gecikme JSON `cold_start` |
| Tam korpus alımı (3 437 belge, uçtan uca) | **16,81 s** | gecikme JSON `cold_start` |
| Verim | **12 266,3 belge/dakika** | gecikme JSON `docs_per_minute` |
| Test paketi (2 999 test, 272 atlandı) | 19,199 s | transkript adım 4 |
| Değişmez denetimi (1 782 belge) | 58 877 ms | transkript adım 5 |

> **İki farklı belge sayısı, iki farklı kapsam — çelişki değil.** Değişmez
> denetimi `eval.properties --raw-dir data/raw` ile **1 782** belge sayar;
> gecikme ölçümü `latency_bench --recursive` ile **3 437** belge tarar. İlki
> ham toplama dizinini, ikincisi özyinelemeli tüm belge ağacını gezer. Her
> sayı kendi komutuyla birlikte verilmiştir; birbirinin yerine kullanılamaz.
>
> **İmaj 31 Temmuz'a göre ≈96,5 MiB'den ≈220,0 MiB'ye büyüdü.** Bu belge
> büyümenin **hangi katmandan** geldiğini ölçmedi;
> `⏳ ölçülmedi — sebep: katman bazlı (docker history) kırılım koşturulmadı.`
> Ölçülmemiş bir sebebi buraya yazmıyoruz.

---

## 0-b. TAZELİK UYARISI → **ÇÖZÜLDÜ (2026-08-15)**

### Uyarı ne diyordu (2026-08-08'de yazıldı)

Belgedeki koşum **31 Temmuz 2026**'da yapılmıştı ve o gün ağaç **kirliydi**
(transkript başlığı: `git durum : 9 degisik dosya`). Uyarı üç şey söylüyordu:

1. sayılar o günün fotoğrafıdır, bugünkü sistemle örtüşmez;
2. kanıtın **mantığı** (14/14 adım, `--network none`, pozitif + negatif
   kontrol) geçerliliğini korur — ölçülen şey API konteynerinin ağsız
   davranışıdır ve o katmanda mimari değişmedi;
3. **en doğrusu teslimden önce `scripts/offline_proof.sh`'i temiz ağaçta
   yeniden koşmaktır.**

Uyarının kendi tavsiyesi ayrıca bir sayıyı yanlış veriyordu: "136 commit"
dendiği yerde gerçek **498 commit**'tir (`git rev-list --count
743b7d5..HEAD` = 498; 31 Temmuz koşumunun kendi commit'i `025c1e5`'ten
sayılırsa 500).

### Ne değişti

**Tavsiye uygulandı.** Kanıt 2026-08-15'te `9493c29` commit'inde, **temiz
ağaçta** yeniden koşuldu ve **14 adımın 14'ü beklendiği gibi, 0 beklenmedik**
çıktı. Yol düz değildi: aynı gün ilk iki deneme adım 4'te kırmızı yandı,
kırık testler düzeltildi, üçüncü koşum tertemiz geçti (§4.1). Bu belgedeki
**tüm sayılar artık o koşumdan** okunmaktadır.

Bayat sayılar, düzeltilmiş halleriyle:

| kalem | 31 Tem koşumu | 8 Ağu uyarısı ne diyordu | **2026-08-15 ölçümü** |
|---|---|---|---|
| test | 607 test | "1.977 test" | **2 999 test toplandı, OK (272 atlandı)** |
| korpus (değişmez denetimi) | 849 belge | "1.774 belge" | **1 782 belge** |
| korpus (gecikme, özyinelemeli) | 1 696 belge | — | **3 437 belge** |
| commit farkı | — | "136 commit" (**yanlış**) | **498 commit** (`743b7d5..HEAD`) |
| gold | 3 kayıt | "66 tekil belge" | **3 kayıt** (`gold.sample.json`, §3.3) |
| `app/models/` | yok | **var** (BERTurk) | var, ama **kullanılmıyor** (§9) |

> Son iki satır dikkat ister. Uyarı gold setin 66 tekil belgeye büyüdüğünü
> söylüyordu; **kanıt koşumu hâlâ `gold.sample.json` (3 kayıt) ile koşuyor**
> çünkü betiğin varsayılanı odur (`GOLD=data/gold/gold.sample.json`). Yani
> §3.3'teki F1 sayıları büyümüş gold setten gelmiyor — ve zaten §3.3'ün
> uyardığı gibi o sayılardan doğruluk sonucu çıkarılmamalı. BERTurk ağırlığı
> diskte durur ama teslim sisteminde kullanılmaz; bu koşumda sınıflandırıcı
> `RuleHintClassifier`'dır (gecikme JSON `environment.classifier`).

### Kapsam sınırı — DEĞİŞMEDİ, sunumda açıkça söylenmeli

Koşum tazelenmiş olması bu sınırları kaldırmaz. Üçü de aynen geçerlidir:

1. **Kanıt yalnız API konteynerini kapsıyor.** Ölçülen şey
   `anatolia-api:offline-proof` imajının `--network none` içindeki
   davranışıdır.
2. **`docker compose up` tam yığını ağsız denenmedi** — Postgres, Next.js
   web katmanı, vLLM ve Ollama servislerinin ağsız birlikte ayağa kalkması
   **ölçülmedi**.
3. **İmaj derlemesi internet gerektiriyor** (`pip install`, `npm ci`).
   Dolayısıyla *"internetsiz çalışır"* iddiası **önceden derlenmiş
   imajlarla** doğrudur — sıfırdan derleme ağ ister (bkz. §3 tablo notu).

Bu boşlukları önce **biz** söylüyoruz. Jüri kendisi bulursa kaybedilen bir
puan değil, belgenin geri kalanına duyulan güven olur.

---

## 9. Ağırlık bütünlüğü (model ağırlıkları)

**`◐ KISMEN KOŞTURULDU (güncelleme: 2026-08-08).`**

Bu bölüm 31 Temmuz'da yazıldığında `app/models/` dizini gerçekten yoktu.
**Artık var:** BERTurk 8 Ağustos'ta yerelde (Apple Silicon / MPS) ince
ayarlandı ve ağırlığı diskte duruyor. Doğrulandı:

| Bileşen | Repo ID | Dosya | Boyut | SHA-256 | Durum |
|---|---|---|---|---|---|
| BERTurk 8-sınıf (ince ayarlı) | `dbmdz/bert-base-turkish-cased` tabanlı | `models/berturk-kampanya-8sinif/model.safetensors` | 442,5 MB | `2c9e3af2410d835a479c7e33b033c01535247bef63ad49f1c436548985eb1a5d` | ✅ künye ile **eşleşiyor** |

Hash `models/berturk-kampanya-8sinif/KUNYE.json` içindeki kayıtla birebir
tutuyor (2026-08-08'de yeniden hesaplanarak doğrulandı). Ağırlık git'e
**girmiyor** (`.gitignore`), tekrar üretimi `scripts/train_berturk.py`
(tohum 42, katmanlı %70/%15/%15 bölme).

> **Not:** bu model **teslim sisteminde KULLANILMIYOR.** Kabul kapısında
> kaldı (gold makro-F1 0,565 vs kural temel çizgisi 0,762, `KUNYE.json`
> `"kabul_kapisi": "KALDI"`), dolayısıyla `docker-compose.yml` içinde
> `BERTURK_MODEL_DIR` bilinçli olarak set edilmiyor ve `Dockerfile.api`
> `models/` dizinini kopyalamıyor. Ağırlığın burada listelenmesi bütünlük
> kaydı içindir, kullanım beyanı değildir.

Aşağıdaki tablodaki **diğer** bileşenler (vLLM/Ollama LLM ağırlıkları,
bge-m3) bu ortamda indirilmedi; onlar için satırlar **boş bırakılmıştır** —
uydurma SHA-256 yazılmadı.

| Bileşen | Repo ID | Revizyon (commit) | Dosya | SHA-256 |
|---|---|---|---|---|
| Çıkarım LLM'i | `Trendyol/Trendyol-LLM-8B-T1` | ⏳ | `model-*.safetensors` | ⏳ |
| Sınıflandırıcı | `dbmdz/bert-base-turkish-cased` | ⏳ | `pytorch_model.bin` | ⏳ |
| Embedding | `BAAI/bge-m3` | ⏳ | `model.safetensors` | ⏳ |

### 9.1 Uygulanacak prosedür (yazıldı, koşturulmadı)

Ağırlıklar **ağı olan** bir makinede bir kez indirilir, SHA-256'ları kaydedilir,
sonra hedef makineye taşınır ve `HF_HUB_OFFLINE=1` ile ağsız kullanılır.

```bash
# 1. İndir — REVİZYONU SABİTLE. Etiketsiz indirme tekrar üretilemez;
#    `main` hareketli bir referanstır.
huggingface-cli download Trendyol/Trendyol-LLM-8B-T1 \
    --revision <commit-sha> \
    --local-dir models/Trendyol-LLM-8B-T1

# 2. Bütünlük künyesi al — bu çıktı bu belgeye yapıştırılır.
find models/Trendyol-LLM-8B-T1 -type f \
    \( -name '*.safetensors' -o -name '*.json' -o -name 'LICENSE' \) \
    -exec shasum -a 256 {} \; | sort -k2

# 3. Çözülen revizyonu kaydet (etiket -> commit).
git -C models/Trendyol-LLM-8B-T1 rev-parse HEAD

# 4. Hedef (ağsız) makineye taşı, sonra doğrula:
shasum -a 256 -c weights.sha256
```

### 9.2 Doğrulanan kısım

Ağırlıkları indirmeden de doğrulanabilen şey doğrulandı: **konteyner
ağırlıkları indirmeye çalışmıyor.** `HF_HUB_OFFLINE=1` ve
`TRANSFORMERS_OFFLINE=1` imajda gerçekten set (§3.4) ve `--network none`
altında tüm boru hattı ağ çağrısı yapmadan tamamlanıyor (§3). Ağırlık klasörü
boşken vLLM **sessizce internete çıkmaz, başlamaz** — istenen davranış budur.

---

## 10. Dürüst eksikler — neyi ölçemedik ve neden

| Kalem | Durum | Sebep |
|---|---|---|
| vLLM + Trendyol-LLM-8B-T1 uçtan uca | `⏳ ölçülmedi` | Bu makinede **GPU yok**. İmaj bile 10,3 GB. |
| Gerçek hibrit gecikmesi (LLM dahil) | `⏳ ölçülmedi` | Aynı sebep; `NullLLMExtractor` ile ölçülen sayı LLM içermez (§7.2) |
| Ollama (CPU yedeği, Qwen3-4B GGUF Q4) | `⏳ ölçülmedi` | 2,8 GB imaj + ağırlık indirilmedi; ayrı bir koşu gerektirir |
| Tüketici GPU profili | `⏳ ölçülmedi` | Donanım yok |
| Sunucu GPU profili (A100/H100) | `⏳ ölçülmedi` | Donanım yok |
| Model ağırlığı SHA-256 | `⏳ koşturulmadı` | §9 — ağırlıklar indirilmedi, prosedür yazıldı |
| `docker compose up` tam yığın (postgres + api + web) | `⏳ koşturulmadı` | Bu paket **API konteynerini** kanıtladı (adım 13: sunucu ağsız ayağa kalkıyor). Postgres + Next.js web katmanının ağsız birlikte ayağa kalkması ölçülmedi |
| pgvector / Postgres ağsız başlatma | `⏳ ölçülmedi` | İmaj çekildi mi diye bakılmadı; `docker compose` koşusu yapılmadı. Teslim imajında `pgvector` paketi de yok (§6) — bu koşum SQLite koluyla ayağa kalktı |
| **İmajın ağsız DERLENMESİ** | `⏳ ölçülmedi — ve ölçülemez` | `docker build` `pip install` yapar, ağ ister. Adım 1 bilerek ağ açıkken koşar. "İnternetsiz çalışır" iddiası **önceden derlenmiş imajlarla** doğrudur (§0-b) |
| Host ↔ konteyner gecikme karşılaştırması | `⏳ 2026-08-15'te yenilenmedi` | Host koşumu bu pakette koşturulmadı; elimizdeki host JSON 31 Temmuz tarihli ve **farklı korpustan** (§7) |
| Chatbot iyileşmesinin sebebi | `⏳ ölçülmedi` | p95 325 ms → 16 ms düştü ama hangi commit'in getirdiği ayrıştırılmadı; 498 commit'lik aralıkta ablasyon koşturulmadı (§7.3) |
| İmaj boyutu artışının katman kırılımı | `⏳ ölçülmedi` | ≈96,5 → ≈220,0 MiB; `docker history` kırılımı alınmadı (§8) |
| Postgres/vLLM/Ollama digest'lerinin tazeliği | `⏳ 2026-08-15'te yenilenmedi` | Kanıt betiği digest çözmez (ağ ister); tablo 31 Temmuz ölçümüdür (§5) |
| Doğruluk (P/R/F1) | ölçüldü **ama anlamsız** | `gold.sample.json` = 3 kayıt (§3.3). Ağsız *koşabilirlik* kanıtı, doğruluk kanıtı değil |
| `curl` negatif kontrolü | `atlandı, gerekçeli` | Taban imajda curl yok (§2.3); yerine stdlib probu |
| x86_64 (amd64) mimarisi | `⏳ ölçülmedi` | Host arm64. Digest'ler çoklu-mimari indeks olduğu için amd64 çalışmalı, ama **doğrulanmadı** |

---

## 11. Kanıtı yeniden üretme

```bash
cd app
bash scripts/offline_proof.sh
```

Betik:
- `set -euo pipefail` ile koşar,
- Docker yoksa veya daemon kapalıysa **açık hata** verip `exit 2` döner
  (sessizce "başarılı" **demez**),
- her adımın çıkış kodunu ve süresini kaydeder,
- transkripti `docs/offline-proof/transcript-<zaman>.log`'a yazar,
- en az bir adım beklenmedikse `exit 1` döner ve "kanıt paketi GEÇERSİZ" der.

Ortam değişkenleri: `IMAGE`, `OUT_DIR`, `GOLD`, `BENCH_ITERATIONS`, `SKIP_BUILD`.

---

## Sources

- `raw/teknofest/2026-teknofest-tyda-sartname-2-senaryo.pdf` — §5.9, §5.10, §8
- `app/CLAUDE.md` §2 (on-prem/Colab ayrımı), §3 (önce kural), §11 (demo), §20
- `docs/offline-proof/transcript-20260815-233225.log` — **YETKİLİ KOŞU** (2026-08-15, `9493c29`, temiz ağaç, 14/14, 0 beklenmedik). Bu belgedeki tüm güncel sayıların kaynağı.
- `docs/offline-proof/latency-20260815-233225.json` — yetkili koşunun ham gecikme/kaynak ölçümü (§7, §8)
- `docs/offline-proof/transcript-20260815-232558.log` — aynı günün 2. denemesi, adım 4 BEKLENMEDIK (§4.1)
- `docs/offline-proof/transcript-20260815-230505.log` — aynı günün 1. denemesi, adım 4 BEKLENMEDIK + soğuk derleme süresi (§3, §4.1)
- `docs/offline-proof/transcript-20260731-135858.log` — **önceki** yetkili koşu (2026-07-31, kirli ağaç; §0-b)
- `docs/offline-proof/transcript-20260731-134646.log` — harness'ın hata yakaladığı koşu (§4.2)
- `docs/offline-proof/transcript-20260731-135051.log` — ara koşu (13 adım, API adımı öncesi)
- `docs/offline-proof/transcript-20260731-133540.log` — ilk koşu (bs4 düzeltmesi öncesi, §6.1)
- `docs/offline-proof/latency-host-20260731.json` — host (konteynersiz) gecikme ölçümü, **yenilenmedi** (§7)
- `tests/_ortam_gereksinimleri.py` — atlanan 272 testin gerekçeleri (§3.1.1)
- `docs/model-license-audit.md` §2 — trafilatura kararı (bu belge onu düzenlemez)
- git `a3c2f05` (2026-08-08) — `ANATOLIA_OFFLINE` sahte bayrağının kaldırılması (§3.4)

## Related

- [[on-premise-calistirilabilir-mimari]] — kararın kendisi
- [[apache-2-acik-kaynak-lisansi]] — §8 dağıtım şartı
- [`kaynak-tuketimi.md`](kaynak-tuketimi.md) — donanım profili tabloları
- [`../scripts/offline_proof.sh`](../scripts/offline_proof.sh) — kanıtı üreten betik
- [`../scripts/latency_bench.py`](../scripts/latency_bench.py) — gecikme ölçüm betiği
