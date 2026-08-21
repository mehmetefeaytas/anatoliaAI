# LLM boşluk-doldurma katmanının üretime alınması — kök neden ve ölçüm

**Tarih:** 2026-08-21 · **Durum:** ölçüm tamamlandı, kabul kararı §5'te
**İlgili:** `src/extraction/llm/extractor.py`, `src/extraction/reconcile.py`,
`scripts/build_demo_db.py`, `eval/run_eval.py`, `docs/rapor/ablasyon.md`,
CLAUDE.md §3 (katman mimarisi), §21 (halüsinasyon yasağı)

> ## KARAR: REDDEDİLDİ
>
> LLM boşluk-doldurma katmanı A100 üzerinde **iki gold'da da ölçüldü** ve kabul
> kapısından geçmedi. Mikro-F1 düştü (0,570 → 0,539 · 0,738 → 0,703),
> halüsinasyon yükseldi (0,034 → 0,058 · 0,344 → 0,541), iki regresyon kapısı
> da kapandı. Sebep tek cümlede: **katman 182 belgede tek bir doğru değer
> üretmedi** (TP 65→65 ve 110→110), yalnız yanlış pozitif ekledi (§5.3).
>
> **İkinci tur da reddetti.** Bulgu bir hipotez üretmişti (hata alan
> ETİKETLEME hatası olabilir), iki açıklaması ölçüldü: daha büyük/yeni model
> (`qwen3.5:9b-q4_K_M`) ve tek çağrıda tek alan sorma. 2×2 ablasyonun
> **dört hücresinin hiçbiri** kabul ölçütünü geçmedi; sekiz koşumun sekizinde
> regresyon kapısı kapalı — ayrıntı §10.
>
> Kapsam uyarısı: round1 hücreleri, `gold.round1` yeniden anotlanmadan ÖNCE
> ölçüldü. Tahkim barı yükseltti (0,738 → 0,786), yani kararı güçlendiriyor;
> tahkim sonrası round1 hibrit sayıları ölçülmedi ve iddia edilmiyor (§10.7).
>
> Üretim korpusu yeniden kurulmadı; `--llm` varsayılanı `kapali`.
> Kök nedenin YAPISAL kısmı (niyetin ifade edilemiyor olması ve kural-only
> koşumun raporda arıza gibi görünmemesi) karardan bağımsız olarak kapatıldı.

## 0. Bulgu

Jüri iki turdur aynı maddeyi yazıyor: teslim edilen korpusta LLM katmanı
**hiçbir alan üretmiyor**.

```
$ sqlite3 data/demo.db "select extractor, count(*) from extracted_fields group by 1"
rule|7032
```

2.708 belgenin tamamı, 7.032 alanın tamamı `rule`. CLAUDE.md §3 mimariyi
"kural birincil → LLM yalnız boşluklar" diye anlatıyor; ikinci katman ateşlemiyor.

---

## 1. Kök neden — kod değil, ÇAĞRI

LLM katmanı çalışmıyor değil; **hiç istenmiyor**. Zincir:

| adım | dosya | davranış |
|---|---|---|
| 1 | `scripts/build_demo_db.py:265` | `run_pipeline(repo, config, raw_dir, mode=MODE_CORPUS, on_progress=…)` — `llm=` argümanı **verilmiyor** |
| 2 | `src/pipeline.py:run_pipeline` | `llm = llm if llm is not None else default_extractor()` |
| 3 | `src/extraction/llm/extractor.py:default_extractor` | `LLM_BACKEND` boş → `NullLLMExtractor` (`"LLM_BACKEND bos -> NullLLMExtractor (kural-only, kasitli offline)"`) |
| 4 | `src/extraction/reconcile.py:reconcile` | `if ask and llm.available:` → `available=False`, LLM'e hiç sorulmuyor |

Yani `LLM_BACKEND=ollama` verilerek koşulsa katman **kendiliğinden** devreye
girerdi. Girmemesinin sebebi, korpus koşumunun bu değişken olmadan yapılmış
olması. Depodaki bütün belgelenmiş çağrılar bu biçimde:

```
docs/rapor/belge-turu.md:114            .venv/bin/python -m scripts.build_demo_db --force --json-report …
docs/rapor/anatolia-ai-teknik-rapor.md:634  python -m scripts.build_demo_db
```

Hiçbirinde `LLM_BACKEND` yok. Depoda `LLM_BACKEND` ayarlayan **tek bir** betik,
Makefile hedefi ya da compose servisi de yok.

**İki yapısal kusur bunu sessiz kıldı:**

1. **Niyet ifade edilemiyordu.** `build_demo_db.py`'nin LLM'i isteyecek bir
   anahtarı yoktu (`--out`, `--config`, `--raw-dir`, `--database-url`,
   `--force`, `--quiet`, `--json-report`). Operatörün "ikinci katman koşsun"
   diyebileceği bir yer yoktu; yalnız üstü örtük bir ortam değişkeni vardı.
2. **Sonuç raporda arıza gibi görünmüyordu.** `_report()` "KATMAN BAŞINA ALAN:
   rule 7032" satırını basıyor ama LLM'in istenip istenmediğini, kurulup
   kurulamadığını, kaç çağrı yapıldığını hiç yazmıyor. `rule 7032` satırı,
   kural-only bir koşumda da tasarım gereği aynı görünür.

Bu, `extractor.py` başlığında anlatılan "sessiz hata yutma" sınıfının bir üst
katmandaki eşi: hata yutulmuyor, **soru hiç sorulmuyor**.

---

## 2. Yerel koşum — şema tutuyor mu, uydurma var mı

> **Not:** bu bölüm ilk elemedir (şema tutuyor mu, uydurma var mı). Buradaki
> SÜRELER güvenilir değildir — makine takas alanında koşuyordu; güvenilir
> süreler §6.2'de, resmî metrikler §5'te (A100).

Donanım: yerel makine (Apple Silicon), Ollama, `qwen2.5:7b-instruct`
(Q4_K_M, Apache-2.0 — `docs/rapor/ablasyon.md §6`'daki künyeli ağırlık).
`LLM_STRICT=1`, `structured_mode=ollama_format`, `num_predict=1536`.

**20 belge (gold.v2'nin ilk 20'si), `reconcile()` hibrit yolu:**

| ölçüm | değer |
|---|---|
| çağrı | 20 |
| şema geçti | **20/20** |
| ayrıştırma hatası / HTTP hatası / şema ihlali / onarım | 0 / 0 / 0 / 0 |
| LLM'in doldurduğu alan | 19 |
| bunlardan alıntısı metinde **birebir bulunan** | 17 |
| bunlardan **kanıtsız** (uydurma riski) | **2** |
| süre | 1.017 s → **50,9 s/belge** |

Kanıtsız iki değer:

```
hedef_kitle   = ['mevcut_musteri']            (alıntı metinde yok)
tahsis_ucreti = {'value': 0.5, 'currency': 'TRY'}  (alıntı metinde yok)
```

İkisi de tam olarak CLAUDE.md §21'in yasakladığı şey: metinde dayanağı
olmayan değer. Bu yüzden ölçüme **kanıt kapısı** eklendi (§3).

---

## 3. Eklenen iki mekanizma

### 3.1 Kanıt kapısı (`LLM_KANIT_ZORUNLU`)

`src/extraction/llm/extractor.py::_to_fields` içinde: LLM'in verdiği
`source_span` kaynak metinde **birebir** bulunmuyorsa (`span_start is None`)
değer düşürülür ve `stats["kanit_reddi"]` artar.

İlke yeni değil — `orchestrator._kanit_kapisi` aynı kapıyı çok-ajanlı kolda
zaten uyguluyordu. Buradaki değişiklik onu **tek-ajanlı hibrit yolda da**
kullanılabilir kılmak. Varsayılan `require_evidence` argümanı ya da
`LLM_KANIT_ZORUNLU` ortam değişkeninden okunur.

Neden bu kapı hibrit kolun tek savunması: hibridin ölçülmüş kaybı geri çağırma
değil **precision** kaybıdır (`docs/rapor/ablasyon.md §2`: `hedef_kitle`'de
doğru 4→4, uydurma 2→6). Kapı tam o mekanizmayı hedefler.

### 3.2 Makine-okur sağlık günlüğü (`eval/reports/llm-sagligi.jsonl`)

"384/384 temiz LLM çağrısı" iddiası iki turdur yalnız bir rapor tablosu
satırıydı: `self.stats` sayaçları koşum bitince bellekle birlikte kayboluyordu.
Artık **her LLM çağrısı bir JSONL satırı**:

```json
{"ts":"2026-08-21T11:11:15+0300","kosum":"v2-hibrit-kanit-acik",
 "model":"qwen2.5:7b-instruct","client":"OllamaClient",
 "structured_mode":"ollama_format","num_predict":1536,"kanit_zorunlu":true,
 "rol":"genel","istenen_alanlar":["kar_payi_orani","finansman_tutari","…"],
 "metin_uzunlugu":1553,"istem_uzunlugu":4327,"sure_ms":27102.6,
 "sema_gecti":true,"sebep":null,"onarim":0,"uretilen_alan":1,"kanit_reddi":0}
```

- Yol: `eval/reports/llm-sagligi.jsonl` (`LLM_SAGLIK_LOG` ile değiştirilebilir,
  `LLM_SAGLIK_LOG=0` ile kapatılır). `.gitignore` dışlamıyor —
  `git check-ignore` boş döndü, artefakt **izlenir**.
- **Başarısız çağrı da yazılır** (`sema_gecti:false` + `sebep`). Sessiz hata
  yutmanın karşıtı, hatanın kaydıdır.
- Günlük yazımı best-effort: disk/izin hatası çıkarımı **düşürmez** (test:
  `test_yazilamayan_gunluk_cikarimi_dusurmez`). Denetim artefaktı, denetlenen
  işi bozmamalı.
- `LLM_BACKEND` boşken günlük **kapalıdır**. Gerekçe: sahte istemcilerle koşan
  birim testleri aynı dosyaya satır yazsaydı, "kaç gerçek çağrı yapıldı"
  sorusuna artefaktın kendisi yanlış cevap verirdi.

### 3.3 Yanıt önbelleği (`LLM_ONBELLEK`) — ölçümü yeniden başlatılabilir kılar

Bu ölçüm sırasında **ölçülen** bir arıza: yerel makinede bellek baskısı
altında (başka bir koşum 9,7B'lik ikinci bir modeli belleğe almışken, sistem
belleğinin %77'si kullanımda) `run_eval` süreci işletim sistemi tarafından
**iki kez** düşürüldü — 46. ve 4. dakikada, hiçbir çıktı yazılmadan. Belge
başına ~40 s'de 134 belgelik gold ~90 dakika demek; her düşme tüm koşumu
sıfırlıyordu.

`LLM_ONBELLEK=<dizin>` verildiğinde her yanıt içerik-adresli olarak diske
yazılır. Anahtar istemin TAMAMINI kapsar (model + istemci + sistem istemi +
kullanıcı istemi + şema + `num_predict`), böylece bayat bir yanıt yeni bir
yapılandırmaya sızamaz. Sıcaklık 0 olduğu için önbellek yalnızca mevcut
determinizmi diske yazar.

**Önbellek iddiayı şişirmez.** Önbellekten gelen çağrı sağlık günlüğüne
`"onbellek": true` olarak yazılır, `cache_hit` sayacına gider ve künye
`gercek_cagri = calls - cache_hit` satırını yayımlar. `calls` sayacının
anlamı değiştirilmedi (o "kaç çıkarım isteği geldi"yi sayar, önbellek isabeti
de bir istektir); eklenen şey, "kaç tanesi GERÇEKTEN modele gitti" sorusunun
künyeden okunabilmesi. Bu ayrım olmadan `calls: 384, ok: 384` satırı 384
gerçek çağrı gibi okunurdu — kapatmaya çalıştığımız denetlenemezlik yeni bir
kılıkta geri gelirdi. Testler:
`test_onbellek_isabeti_gunluge_ISARETLENIR`, `test_ikinci_cagri_istemciye_gitmez`.

Varsayılan **KAPALI**: önbellek bir ölçüm kolaylığıdır, üretim davranışı değil.

Testler: `tests/test_llm_saglik.py` (17 test). Mevcut LLM ve orkestrasyon
testleri kırılmadı; `tests/test_orchestrator.py`'daki `summary()` sözleşme
testi yeni künye anahtarlarını (`kanit_reddi`, `require_evidence`,
`saglik_log`, `onbellek`, `cache_hit`, `model`) orkestrasyon kolunda da
zorunlu kıldı ve eksikliği yakaladı.

---

## 4. Ölçüm protokolü

Kabul kararı **iki ayrı gold** üzerinde alınır; tek bir set üzerinde iyileşme
görmek yetmez (`eval/esikler.json` ve `eval/esikler-round1.json` iki bağımsız
regresyon kapısıdır).

```
# gold.v2  (n=48, zor-vaka ağırlıklı)
LLM_BACKEND=ollama LLM_STRICT=1 LLM_KANIT_ZORUNLU=1 \
LLM_SAGLIK_LOG=eval/reports/llm-sagligi.jsonl LLM_KOSUM=v2-hibrit-kanit-acik \
.venv/bin/python -m eval.run_eval --gold data/gold/gold.v2.json \
  --config hibrit --esikler eval/esikler.json \
  --matcher strict --kalem-duyarlilik-yok --no-bootstrap

# gold.round1  (n=134, geniş kapsam)
… --gold data/gold/gold.round1.json --esikler eval/esikler-round1.json
```

**`--matcher strict --kalem-duyarlilik-yok` neden zorunluydu.** `run_eval`
varsayılan `--matcher both` ile tahmin üretimini **8 kez** tekrarlar
(2 eşleştirici × [1 ana geçiş + 3 kalem-eşik duyarlılığı]). Kural kolunda bu
ucuzdur; LLM kolunda belge başına ~40 s demek, gold.v2 için tek başına ~4,3
saat. Eşik dosyalarının ikisi de `"matcher": "strict"` yazdığı için resmî kapı
zaten strict'tir — bu yüzden yalnız strict koşuldu ve tahmin üretimi belge
başına **bir kez** yapıldı. Kural tabanı aynı bayraklarla yeniden koşularak
sayıların birebir aynı olduğu doğrulandı (mikro-F1 0,570 → 0,570).

**KABUL ÖLÇÜTÜ (önceden ilan edildi, sonuca göre değiştirilmedi):**

1. Hibrit kolun mikro-F1'i kural tabanının **ÜSTÜNDE** olacak — **her iki**
   gold'da.
2. Halüsinasyon oranı kural tabanının **ÜSTÜNE ÇIKMAYACAK** — her iki gold'da.

İkisi birden sağlanmazsa üretime alınmaz. `eval/esikler*.json` eşikleri sonuç
görüldükten sonra **değiştirilmedi**.

---

## 5. ÖLÇÜM SONUÇLARI ve KABUL KARARI

### 5.0 Ölçüm nerede yapıldı — ve niçin yeniden yapıldı

İlk koşumlar yerel makinede (Apple Silicon MacBook Air) başlatıldı ve
**güvenilir değildi**: takas alanı %90+ dolu, çağrı başına 40–200 s, işletim
sistemi ölçüm süreçlerini birkaç kez düşürdü. Bu koşullarda ölçülen SÜRE
yanıltıcı, çıktı kalitesi ise en iyi hâlde şüphelidir.

Ölçüm bu yüzden **NVIDIA A100-SXM4-40GB** üzerinde tekrarlandı (Colab, Ollama
0.32.15, `qwen2.5:7b-instruct` Q4_K_M). Yüklenen şey yalnız koddur:
`src/`, `eval/`, `scripts/`, `config/`, `data/gold/` (9 MB arşiv).
**`data/raw` yüklenmedi** — değerlendirme yalnız gold belgelerinin metnini
okur, ham korpusa ihtiyaç duymaz.

Aşağıdaki tüm sayılar bu A100 koşumundandır. Kural kolu da AYNI makinede
yeniden koşuldu ve yerel taban sayılarıyla birebir aynı çıktı (v2 0,570 /
round1 0,738) — yani kural katmanı donanımdan bağımsız, kıyas geçerli.

### 5.1 Manşet tablo (strict eşleştirici · TÜM VAKALAR)

| gold | kol | mikro-F1 | yapısal mikro-F1 | makro-F1 | halüsinasyon | regresyon kapısı |
|---|---|---|---|---|---|---|
| **gold.v2** (n=48) | kural (taban) | **0,570** | 0,823 | 0,765 | **0,034** [15/447] | AÇIK |
| gold.v2 | hibrit + kanıt kapısı | 0,539 | 0,760 | 0,707 | 0,058 [26/447] | **KAPALI** (6 gerileme) |
| gold.v2 | hibrit, kanıt kapısı KAPALI | 0,537 | 0,756 | 0,704 | 0,060 [27/447] | **KAPALI** (6 gerileme) |
| **gold.round1** (n=134) | kural (taban) | **0,738** | 0,768 | 0,600 | **0,344** [21/61] | AÇIK |
| gold.round1 | hibrit + kanıt kapısı | 0,703 | 0,729 | 0,567 | 0,541 [33/61] | **KAPALI** (5 gerileme) |
| gold.round1 | hibrit, kanıt kapısı KAPALI | 0,703 | 0,729 | 0,567 | 0,541 [33/61] | **KAPALI** (5 gerileme) |

### 5.2 KABUL KARARI: **REDDEDİLDİ — üretime ALINMADI**

| ölçüt | gold.v2 | gold.round1 | sonuç |
|---|---|---|---|
| F1 kural tabanının ÜSTÜNE çıkacak | 0,539 < 0,570 (**−0,031**) | 0,703 < 0,738 (**−0,035**) | ✗ ✗ |
| halüsinasyon YÜKSELMEYECEK | 0,034 → 0,058 (**+71 %**) | 0,344 → 0,541 (**+57 %**) | ✗ ✗ |

Dört hücrenin dördü de başarısız. `eval/esikler.json` ve
`eval/esikler-round1.json` regresyon kapıları **ikisi de kapandı** (6 ve 5
gerileme). Eşikler sonuç görüldükten sonra **değiştirilmedi**.

`scripts/build_demo_db.py --llm` varsayılanı `kapali` bırakıldı; üretim
korpusu (`data/demo.db`) **yeniden kurulmadı**.

### 5.3 MEKANİZMA — bu ölçümün en önemli bulgusu

Manşet farkın nereden geldiği alan kırılımından okunuyor ve beklenenden daha
keskin:

| gold | kol | TP | FP | FN | geri çağırma |
|---|---|---|---|---|---|
| v2 | kural | 65 | 54 | 44 | 0,596 |
| v2 | hibrit | **65** | **67** | 44 | **0,596** |
| round1 | kural | 110 | 40 | 38 | 0,743 |
| round1 | hibrit | **110** | **55** | 38 | **0,743** |

**TP değişmiyor. FN değişmiyor. Geri çağırma değişmiyor. Yalnız FP artıyor.**

Yani LLM boşluk-doldurma katmanı, iki gold'un toplam 182 belgesinde
**tek bir doğru değer üretmedi**. Ürettiği 28 (v2) ve 15 (round1) yeni
değerin tamamı yanlış: bir kısmı gold'un "bu alan YOK" dediği yeri doldurdu
(halüsinasyon: +11 ve +12), kalanı yanlış değer verdi.

Alan bazında da hiçbir alan İYİLEŞMEDİ; 6 alan (v2) ve 6 alan (round1)
kötüleşti:

| alan | v2 kural → hibrit | round1 kural → hibrit |
|---|---|---|
| `kar_payi_orani` | 1,000 → 0,750 (uyd. 0→2) | 0,800 → 0,632 (uyd. 1→5) |
| `odul_miktari` | 0,727 → 0,571 (uyd. 1→4) | 0,400 → 0,333 (uyd. 3→4) |
| `hedef_kitle` | 0,571 → 0,488 (uyd. 6→10) | 0,667 → 0,667 (=) |
| `vade_ay` | 1,000 → 0,909 (uyd. 0→1) | 0,693 → 0,650 (uyd. 10→15) |
| `masraf_durumu` | 0,667 → 0,615 (uyd. 2→3) | 0,000 → 0,000 (=) |
| `kampanya_suresi` | 0,936 → 0,936 (=) | 0,935 → 0,917 (uyd. 4→5) |
| `finansman_tutari` | 1,000 → 1,000 (=) | 0,500 → 0,457 (uyd. 0→1) |

Bu, 2026-08-07 ablasyonunun (`docs/rapor/ablasyon.md §2`) `hedef_kitle` için
gözlediği kalıbın **tüm alanlara** genellenmiş hâli: "LLM'in yazma yetkisi yeni
bilgi getirmiyor, gold'un YOK dediği yerleri dolduruyor." O gözlem n=20'de tek
alanda yapılmıştı; şimdi n=48 ve n=134'te 12 alanın tamamında doğrulandı.

### 5.4 Kanıt kapısı ne yaptı — ve neden yetmedi

Kapı, alıntısı kaynak metinde birebir bulunmayan değeri düşürür. Ölçülen:

| gold | kapının düşürdüğü değer | F1 kazancı | halüsinasyon kazancı |
|---|---|---|---|
| gold.v2 | 1 | +0,002 (0,537 → 0,539) | 27 → 26 uydurma |
| gold.round1 | 23 | 0,000 (0,703 → 0,703) | 33 → 33 uydurma |

**Bulgu: halüsinasyonun kaynağı kanıtsızlık DEĞİL.** Model alıntıyı metinden
birebir kopyalıyor — sonra o alıntıya, anotatörün "bu alanda bilgi yok" dediği
bir alan etiketi yakıştırıyor. Yani hata *çıkarım* değil *eşleme* hatası;
"alıntı gerçek mi" kapısı bu hatayı görmez. round1'de düşürülen 23 değerin
metriklere hiç dokunmaması bunu doğruluyor (o değerler gold'un "belirsiz"
dediği, metrik dışı hücrelere düşmüş).

Kapı bu yüzden **korunuyor ama tek başına yetersiz**: maliyeti sıfır, kestiği
şey gerçekten savunulamaz değerler, ama kabul kapısını açan mekanizma değil.

### 5.5 LLM sağlık künyesi — iddia artık dosyada

A100 koşumunun tamamı `eval/reports/llm-sagligi.jsonl`de:

| koşum | kayıt | modele giden | şema geçti | hata | onarım | kanıt reddi | ortanca süre |
|---|---|---|---|---|---|---|---|
| `colab-v2-hibrit-kanit-acik` | 48 | 48 | **48/48** | 0 | 0 | 1 | 1,10 s |
| `colab-v2-hibrit-kanit-kapali` | 48 | 0 (önbellek) | 48/48 | 0 | 0 | 0 | — |
| `colab-r1-hibrit-kanit-acik` | 134 | 129 | **134/134** | 0 | 0 | 23 | 1,45 s |
| `colab-r1-hibrit-kanit-kapali` | 134 | 0 (önbellek) | 134/134 | 0 | 0 | 0 | — |

**364 kayıt, 364'ü şema-geçerli; 0 ayrıştırma hatası, 0 HTTP hatası, 0 şema
ihlali, 0 onarım denemesi.** Modele gerçekten giden çağrı 177; kalan 187
önbellek isabetidir ve satırlarında `"onbellek": true` yazılıdır.

Yani "temiz LLM çağrısı" iddiası artık bir tablo satırı değil, satır satır
denetlenebilir bir dosya. Ve bu dosya aynı zamanda kararın da kanıtı: **LLM
teknik olarak kusursuz çalıştı** (şema tuttu, JSON bozulmadı, onarım
gerekmedi) — ölçüm başarısızlığı bir mühendislik arızası değil, modelin bu
görevdeki **anlamlandırma** yetersizliğidir. Ayrım önemlidir: birincisi
düzeltilir, ikincisi ölçülür ve raporlanır.

---

## 6. Üretim koşumu — komut ve süre

### 6.1 `build_demo_db` artık niyeti ifade edebiliyor

Kök nedenin yapısal kısmı (§1) sonuçtan **bağımsız** olarak kapatıldı, çünkü
"LLM'i istemenin bir yolu yok" ve "kural-only koşum raporda arıza gibi
görünmüyor" kusurları kabul kararına bakmaksızın kusurdur:

```
--llm {kapali,ollama,vllm}    boşluk doldurma katmanı (VARSAYILAN: kapali)
--llm-kanit {zorunlu,serbest} LLM değerinin alıntısı metinde birebir bulunmak
                              zorunda mı (VARSAYILAN: zorunlu)
--ornek N                     yalnız N belge (adımlı örnekleme) — SÜRE ölçümü
```

Üç davranış garantisi:

1. `--llm ollama|vllm` verilip istemci kurulamıyorsa betik **DURUR**
   (`default_extractor(strict=True)`). Sessiz `NullLLMExtractor` düşüşü artık
   imkânsız — bu, arızanın kendisiydi.
2. Rapor artık **LLM BOŞLUK DOLDURMA** bloğu basıyor: açık/kapalı, model,
   çağrı, şema geçti, hata, onarım, kanıt kapısı reddi, sağlık günlüğü yolu.
   Kural-only koşum artık `rule 7032` satırının ardında saklanamıyor.
3. `PipelineResult.llm` künyesi eklendi; `summary()` satırı
   `katman=kural-only` ya da `katman=kural+llm(N cagri)` yazıyor.

4. Çıkarım koşum ORTASINDA patlarsa (servis düşer, zaman aşımı, `LLM_STRICT`
   altında şema hatası) **yarım DB dosyası silinir**. Aksi hâlde diskte
   binlerce kampanyası eksik ama geçerli görünen bir SQLite kalırdı; API onu
   açar, dashboard sayı basar ve hiçbir yerde "bu DB yarım" yazmazdı — yani
   kapattığımız sessiz-yanlış sınıfı yeni bir kılıkta geri gelirdi.

Varsayılan **`kapali`** bırakıldı: kabul kapısı geçilmeden varsayılanı
değiştirmek, ölçmeden karar vermek olurdu.

**Üçü de ÖLÇÜLDÜ, iddia edilmiyor:**

```
$ .venv/bin/python -m scripts.build_demo_db --out /tmp/wire.db --force \
      --quiet --ornek 3 --llm ollama --llm-kanit zorunlu
  LLM BOŞLUK DOLDURMA: AÇIK
    istemci / model            : OllamaClient / qwen2.5:7b-instruct
    çağrı                      : 3
    şema geçti                 : 3/3
    hata (ayrıştırma/HTTP/şema): 0
    kanıt kapısı reddi         : 0   (kanıt zorunlu: True)
$ sqlite3 /tmp/wire.db "select extractor, count(*) from extracted_fields group by 1"
llm|1
rule|9
```

`llm|1` satırı kök nedeni kanıtlıyor: **kod çalışıyordu, çağrılmıyordu.** Aynı
betik `--llm vllm` ile ulaşılamayan bir sunucuya karşı koşulduğunda
`LLMExtractionError` ile durdu ve yarım DB dosyasını sildi (`ls` → dosya yok).

### 6.2 Ölçülen süre

Belge başına maliyet, sağlık günlüğünden okunan **gerçek** (önbelleksiz)
çağrıların ORTANCASIdır; ortalama değil, çünkü ilk çağrı model yüklemesini
(76 s) taşıyor ve ortalamayı tek başına bozuyor.

| ortam | model | ortanca çağrı | 2.708 belge tahmini |
|---|---|---|---|
| A100-SXM4-40GB, Ollama 0.32.15 | `qwen2.5:7b-instruct` | **1,10–1,45 s** | **~55–65 dk** |
| yerel MacBook Air, takas %90+ dolu | aynı | 44–84 s | ~33–63 saat |

A100 yerelden **~40× hızlı** çıktı. Görevde verilen ~8 s/belge varsayımı
hiçbir ortamda tutmadı: yerelde çok yavaş, A100'de çok hızlı. İki ortam
arasındaki farkın sebebi ölçülü — yerelde işletim sistemi model ağırlıklarını
takas alanına atıyor, dolayısıyla "sıcak" çağrı "soğuk"tan yavaş olabiliyor.

### 6.3 Tam korpus koşumu — komut

**Bu komut ÇALIŞTIRILMADI ve ÖNERİLMİYOR**: §5.2'deki kabul kararı reddetti.
Buraya yazılmasının sebebi, kararın gelecekte (başka bir model, başka bir
istem tasarımı, alan alt kümesi kısıtı) yeniden ölçülmesi hâlinde komutun
hazır olması. Bugün koşulursa `data/demo.db`nin doğruluğu ÖLÇÜLDÜĞÜ ÜZERE
düşer.

```bash
# A100 (Colab) — Ollama ayakta ve qwen2.5:7b-instruct çekilmiş olmalı
cd /content/app
export LLM_STRICT=1 OLLAMA_TIMEOUT=900 OLLAMA_KEEP_ALIVE=60m
export LLM_SAGLIK_LOG=eval/reports/llm-sagligi.jsonl
export LLM_KOSUM=uretim-korpus-2708
python3 -m scripts.build_demo_db \
    --out data/demo.db --force \
    --llm ollama --llm-kanit zorunlu \
    --json-report data/eval/demo-db-rapor.json
```

Beklenen süre: **~55–65 dk** (2.708 belge × 1,1–1,45 s ortanca + kural katmanı
ve DB yazımı). Beklenen çıktı: rapordaki `LLM BOŞLUK DOLDURMA: AÇIK` bloğu ve
`extracted_fields.extractor` sütununda `rule` yanında `llm` satırları.

Ön koşul: `data/raw` (2.708 `.txt` + sidecar) koşumun yapıldığı makinede
bulunmalı. Bu ölçüm için Colab'a **yüklenmedi** — değerlendirme yalnız gold
metinlerini okur; tam korpus koşumu için gerekir.

Vazgeçmek için: komutu `--llm kapali` ile (yani varsayılanıyla) koşmak yeter;
bugünkü `data/demo.db` bu şekilde üretilmiştir.

---

## 7. Ölçümün kendisiyle ilgili dürüstlük notları

**7.1 Halüsinasyon oranı bu kolda yapısal olarak AZALAMAZ.** Hibrit hat, kural
çıktısını korur ve yalnız BOŞ alanları doldurur (`reconcile()`; `verify_low_conf`
varsayılan 0,0). Dolayısıyla hibridin tahmin kümesi kural kümesinin
**üst kümesidir**. Gold'un "bu alan YOK" dediği bir alanda kural hiçbir şey
üretmemişse TN sayılır; hibrit bir değer üretirse aynı hücre FP (halüsinasyon)
olur. Ters yönde bir hareket mümkün değildir.

Bunun sonucu: "halüsinasyon oranı YÜKSELMEYECEK" ölçütü bu kolda
**"LLM, gold'un YOK dediği hiçbir alanı doldurmayacak"** ile eşdeğerdir. Bu
zorlu bir bardır ve kasıtlıdır — CLAUDE.md §21 tam olarak bunu istiyor. Barı
gevşetmek ölçütü sonradan değiştirmek olurdu; yapılmadı.

Ölçüm bu asimetriyi bir mazerete dönüştürmedi, çünkü **F1 ölçütü de bağımsız
olarak başarısız oldu** (§5.2) ve mekanizma tek yönlü: LLM sıfır doğru değer
üretti (§5.3). Yani kol, gevşetilmiş bir halüsinasyon ölçütüyle bile geçmezdi.

**7.2 Ölçülmeyen kollar, ölçülmüş gibi yazılmadı.** Aşağıdakiler bu koşumda
ÖLÇÜLMEDİ ve bu raporda sayı ile geçmiyor:

- **`orkestra` / `hibrit-verify`** kolları — bu koşumun kapsamı dışında.
  (Kanıt kapısı KAPALI kolu ölçüldü, bkz. §5.1/§5.4.)
- **vLLM kolu** — bu ölçüm Ollama ile yapıldı; vLLM ile sayılar
  tekrarlanmadı.
- **Bootstrap güven aralıkları** — `--no-bootstrap` ile koşuldu, dolayısıyla
  farkların GA'ları raporlanmıyor. Kararı bu eksik zayıflatmıyor: fark her iki
  gold'da da AYNI yönde ve regresyon kapıları bağımsız olarak kapandı; ayrıca
  §5.3'teki TP/FN eşitliği (LLM sıfır doğru değer üretti) bir aralık
  sorusu değil, sayım sonucudur.

**7.3 Ölçüm ortamı sonucu etkiliyor mu.** Etkilemesi beklenmez: sıcaklık 0,0,
`format` şeması sabit, tek model. Ortamın etkilediği tek şey SÜREdİR — ve süre
tahminleri ölçülen ortancadan türetildi, varsayılan bir sayıdan değil.

**7.4 Sağlık günlüğü karma koşumlar taşıyor.** Resmî sayılar `colab-` ön ekli
364 kayıttan gelir. Dosyada ayrıca yerel makinede yapılan eleme koşumunun ve
işletim sistemi tarafından düşürülen yarım koşumların kayıtları da var
(`onbellek-isitma`, `v2-hibrit-kanit-acik`); ilk 5 satır ise `kosum` alanı
eklenmeden önce yazıldığı için etiketsizdir.

Satırlar SİLİNMEDİ: günlük append-only bir denetim kaydıdır ve düşen bir koşum
da olgudur. Ayrım `kosum` etiketinden ve zaman damgasından yapılır.

---

## 8. Kararı değiştirebilecek şeyler (ölçülmedi, iddia edilmiyor)

§5.3 mekanizması yön veriyor: sorun modelin metni okuyamaması değil (alıntılar
gerçek, şema kusursuz), **hangi alanın gerçekten boş olduğuna karar
verememesi**. Buradan üç ölçülebilir hipotez çıkar:

1. **Alan alt kümesi kısıtı.** LLM'e yalnız kuralların yapısal olarak
   göremediği alanlar sorulsun (`hedef_kitle`, `kampanya_kosullari` gibi serbest
   metin alanları), sayısal alanlar (`kar_payi_orani`, `vade_ay`,
   `finansman_tutari`) hiç sorulmasın. Ölçüm bu alanların en çok bozulan
   alanlar olduğunu gösteriyor. **Uyarı:** alt küme gold.v2'ye bakarak
   seçilirse bu bir aşırı-uydurmadır (overfitting); seçim bir gold'da yapılıp
   ÖTEKİ gold'da doğrulanmalı. **ÖLÇÜLMEDİ.**
2. **"YOK" için açık kanıt zorunluluğu.** Bugün model bir alanı doldurmak için
   alıntı veriyor ama BOŞ bırakmak için hiçbir gerekçe vermiyor; istem
   asimetrik. Alanın etiketinin (tetikleyici terimin) metinde hiç geçmediği
   durumda değer üretiminin mekanik olarak engellenmesi
   (`orchestrator._kalem_kapisi`nin genelleştirilmiş hâli) ölçülebilir bir kol.
   **ÖLÇÜLMEDİ.**
3. **Daha güçlü model** ve **sorgu granülaritesi** — bu ikisi §10'da
   **ÖLÇÜLDÜ ve ikisi de kararı değiştirmedi.** Bu maddeler artık "denenmemiş
   ihtimal" değil, kapatılmış hipotezdir; ayrıntı §10.3 tablosunda.

1. ve 2. maddeler ölçülmedi, dolayısıyla onlar için sayı verilmiyor.

## 9. Yeniden üretme

```bash
# yerel: taban (kural) — saniyeler, LLM gerekmez
.venv/bin/python -m eval.run_eval --gold data/gold/gold.v2.json --config kural \
  --esikler eval/esikler.json --matcher strict --kalem-duyarlilik-yok --no-bootstrap
.venv/bin/python -m eval.run_eval --gold data/gold/gold.round1.json --config kural \
  --esikler eval/esikler-round1.json --matcher strict --kalem-duyarlilik-yok --no-bootstrap

# A100: hibrit kolu (kod + gold yüklenir, data/raw GEREKMEZ)
tar --exclude='__pycache__' -czf kod.tgz src eval scripts config data/gold
# ... arşivi hedefe açıp:
export LLM_BACKEND=ollama LLM_STRICT=1 LLM_KANIT_ZORUNLU=1
export LLM_SAGLIK_LOG=eval/reports/llm-sagligi.jsonl LLM_ONBELLEK=/content/onbellek
export LLM_KOSUM=colab-v2-hibrit-kanit-acik
python3 -m eval.run_eval --gold data/gold/gold.v2.json --config hibrit \
  --esikler eval/esikler.json --matcher strict --kalem-duyarlilik-yok --no-bootstrap --no-write
```

`LLM_ONBELLEK` sayesinde `LLM_KANIT_ZORUNLU=0` ile ikinci kol **HTTP'ye hiç
dokunmadan** ölçülür (sağlık günlüğünde `"onbellek": true`).

---

## 10. İKİNCİ TUR — model kapasitesi ve sorgu granülaritesi ablasyonu

### 10.1 Neden ikinci tur

§5.3'ün bulgusu bir hipotez üretti. Hata "değer bulamama" değildi: model
alıntıyı metinden birebir kopyalıyor, sonra o alıntıya anotatörün "bu alanda
bilgi yok" dediği bir alan etiketi yakıştırıyordu. Bu bir **sınıflandırma**
hatasıdır, çıkarım hatası değil. Buradan iki test edilebilir açıklama çıkar:

**H1 — model kapasitesi.** 7B Q4 alan ayrımını yapamıyor; daha yeni ve daha
büyük bir model (`qwen3.5:9b-q4_K_M`) yapabilir.

**H2 — sorgu granülaritesi.** Modele tek çağrıda 8-9 alan verildiğinde
"hangi alan" sorusu MODELİN işi olur ve alan karışması bunun beklenen
hatasıdır. Eksik alan başına AYRI çağrı yapılırsa model artık alan seçmez,
yalnız "bu tek alan metinde var mı" sorusuna cevap verir; karışma imkânı
**yapısal olarak** ortadan kalkar.

İkisi bir 2×2 ablasyon: {7b, 9b} × {çoklu-alan, alan-başına}. `7b × çoklu-alan`
hücresi §5'te ölçüldü ve tekrar koşulmadı; kalan üç hücre ölçüldü.

### 10.2 Kodda ne değişti

`LLM_ALAN_BASINA=1` (ya da `LLMExtractor(alan_basina=True)`) verildiğinde
`extract()` eksik alanları tek tek sorar. İki kol arasındaki tek fark
granülaritedir — few-shot gövdesi, şema üreteci, sıcaklık, `num_predict`
aynı kalır (test: `test_tek_alan_istemi_daraltilmis_talimat_tasir` iki istemin
örnek gövdesinin **birebir aynı** olduğunu doğruluyor). Tek alan istendiğinde
istemin son talimatı daralır: *"YALNIZ bu tek alanı değerlendir … GEÇMİYORSA
null yap. Başka hiçbir alan üretme."*

Hata davranışı: katı modda ilk hata yükseltilir; hoşgörülü modda başarısız
alan atlanır ve kalan alanlar sorulmaya devam eder (tek alanın hatası diğer
sekiz alanın cevabını çöpe atmamalı). Künyeye `alan_basina` alanı eklendi ki
iki kolun sayıları yalnız bu ayar bilinerek karşılaştırılabilsin.

Varsayılan **çoklu-alan**: alan-başına kipin maliyeti belge başına ~9 kat
çağrıdır ve bu tur onun kazanmadığını gösterdi (§10.3).

### 10.3 Dört hücrenin sayıları (A100 · `strict` eşleştirici · TÜM VAKALAR)

Taban (kural katmanı, aynı kod anlık görüntüsü, aynı makine):
**gold.v2 F1 0,570 · halüsinasyon 0,034** · **gold.round1 F1 0,738 ·
halüsinasyon 0,344**.

> **round1 satırları** tahkimden ÖNCEKİ `gold.round1`e karşı ölçüldü
> (taban 0,738 / hal 0,344). `HEAD`te o gold yeniden anotlandı ve taban
> 0,786 / 0,297 oldu — bar YÜKSELDİ. Ayrıntı ve etkisi §10.7'de.
> **v2 satırları** `HEAD` tabanıyla doğrudan karşılaştırılabilir.

| hücre | model | granülarite | gold | mikro-F1 | yapısal F1 | halüsinasyon | TP | FP | regresyon kapısı | koşum kipi |
|---|---|---|---|---|---|---|---|---|---|---|
| **A** | qwen2.5:7b | çoklu-alan | v2 | 0.539 | 0.760 | 0.058 [26/447] | 65 | 67 | KAPALI (6) | katı |
| **B** | qwen3.5:9b | çoklu-alan | v2 | 0.473 | 0.632 | 0.143 [64/447] | 66 | 104 | KAPALI (11) | katı |
| **C** | qwen2.5:7b | alan-başına | v2 | 0.520 | 0.722 | 0.078 [35/447] | 65 | 76 | KAPALI (10) | katı |
| **D** | qwen3.5:9b | alan-başına | v2 | 0.537 | 0.756 | 0.060 [27/447] | 65 | 68 | KAPALI (6) | katı |
| **A** | qwen2.5:7b | çoklu-alan | r1 | 0.703 | 0.729 | 0.541 [33/61] | 110 | 55 | KAPALI (5) | katı |
| **B** | qwen3.5:9b | çoklu-alan | r1 | 0.735 | 0.763 | 0.508 [31/61] | 115 | 50 | KAPALI (3) | katı |
| **C** | qwen2.5:7b | alan-başına | r1 | 0.714 | 0.741 | 0.525 [32/61] | 111 | 52 | KAPALI (3) | **hoşgörülü** |
| **D** | qwen3.5:9b | alan-başına | r1 | 0.721 | 0.748 | 0.492 [30/61] | 111 | 49 | KAPALI (3) | katı |

`A` hücresi §5'te ölçüldü, tekrar koşulmadı. Kural tabanının TP değeri
karşılaştırma için: gold.v2 **65**, gold.round1 **110**.

**Artefakt köken bilgisi (dürüstlük notu).** Ölçüm sırasında Colab oturumu
**beş kez** geri alındı ve her seferinde `/content` silindi. Bugün diskte
duran koşum çıktıları: `B/v2`, `C/round1`, `D/v2`, `D/round1` ve iki kural
tabanı. `B/round1` (0,735) ile `C/gold.v2` (0,520) hücrelerinin sayıları
**koşum transkriptinden** alınmıştır; o oturumun dosyaları kurtarılamadı ve
altıncı bir oturum açılmadı. Bu iki hücre yeniden koşulursa §10.3c'deki
±0,01 varyans beklenmelidir; ikisi de eşiğe 0,02 ve 0,05 uzakta olduğu için
karar değişmez.

#### Tablonun okunuşu — iki hipotez de çürüdü

**H1 (model kapasitesi) çürüdü.** `qwen3.5:9b`, gold.v2'de 7b'den **belirgin
biçimde daha kötü**: F1 0,539 → 0,473, halüsinasyon 0,058 → **0,143**
(tabanın 4,2 katı), yanlış pozitif 67 → **104**. Daha yeni ve büyük model
alan etiketleme hatasını azaltmadı, **artırdı**. gold.round1'de 9b LLM
kollarının en iyisi (0,735) ama hâlâ kuralın (0,738) altında ve halüsinasyonu
1,5 katı.

**H2 (sorgu granülaritesi) çürüdü.** Alan-başına sormak alan karışmasını
kaldırmadı. gold.v2'de 7b için F1 0,539 → **0,520** (kötüleşti), halüsinasyon
0,058 → **0,078**. Yapısal sebep hipotezin öngörmediği yönde işliyor: model
"şu 9 alandan hangisi?" sorusunda bir alanı seçmek zorunda değilken, "bu
metinde `vade_ay` var mı?" sorusunda **tek bir alana odaklanıp onu bulmaya
teşvik ediliyor**. İzolasyon karışmayı engellerken **iddia etme eğilimini**
artırıyor. Karışmayı kaldırmak yetmiyor, çünkü hata "yanlış kutu" değil
"boş kalması gereken kutuya bir şey yazmak".

**Neredeyse değişmeyen şey: TP.** gold.v2'de kural tabanı TP = 65; dört
hücrenin üçünde TP **aynen 65**, birinde (B) 66. Yani daha büyük model ve
alan-başına sorgu, 48 belgede toplam **bir** doğru değer kazandırdı; hücreler
esasen yanlış pozitifte ayrışıyor (67 · 104 · 76 · 68 — tabanda 54).
gold.round1'de tablo biraz kırılıyor: TP 110 → 115 (B), 111 (C ve D). Daha
büyük model bu geniş kümede **5 doğru değer** ekliyor, ama aynı hamlede 10
yanlış pozitif getiriyor (FP 40 → 50); F1 yine düşüyor.

Kısaca: LLM katmanının iki gold'da kazandırdığı doğru değer toplamı **6**;
getirdiği yanlış pozitif **23–60** aralığında. Oran hiçbir hücrede lehte değil.

**En iyi LLM hücresi bile geçmiyor.** İki gold'un ikisinde de en iyi LLM kolu
`D` (9b + alan-başına): v2'de 0,537 (< 0,570), round1'de 0,721 (< 0,738);
halüsinasyon v2'de 0,060 (> 0,034), round1'de 0,492 (> 0,344). Dört eşiğin
dördü de aşılmış durumda.

**Sekiz koşumun sekizinde regresyon kapısı KAPALI.**

### 10.3b Taban, kıyas anında da geçerli miydi

Ölçüm sırasında depoya ilgisiz bir kural düzeltmesi girdi (`%2 TL` →
`finansman_tutari` yanlış pozitifi; `_ortak.py` + `tutar.py`). Kıyasın hâlâ
geçerli olup olmadığı **varsayılmadı, yeniden ölçüldü** — düzeltme sonrası
`HEAD`te kural kolu:

```
gold.v2      MİKRO 0.546 0.596 0.570   TP 65  FP 54  FN 44   halüsinasyon 0.034 [15/447]
gold.round1  MİKRO 0.733 0.743 0.738   TP 110 FP 40  FN 38   halüsinasyon 0.344 [21/61]
```

O düzeltme için sayılar birebir aynıydı. **Ama ölçüm bittikten sonra
gold.round1'in KENDİSİ değişti** — bu, §10.7'de ayrıca ele alınıyor ve
§10.3 tablosunun round1 satırlarını etkiliyor.

gold.v2 tabanı `HEAD`te de aynıdır (0,570 / 0,034), dolayısıyla tablonun
**v2 satırları `HEAD` ile karşılaştırılabilir** durumda.

### 10.3c ÖLÇÜLEN tekrar-varyansı: LLM kolu determinist DEĞİL, kural kolu determinist

İkinci turun ortasında Colab oturumu geri alındı ve bazı hücreler **yeni bir
oturumda ikinci kez** koşuldu. Bu istenmeyen olay ücretsiz bir tekrarlanabilirlik
ölçümü verdi:

| ölçüm | 1. koşum | 2. koşum (yeni oturum) | fark |
|---|---|---|---|
| kural / gold.v2 | 0,570 · hal 0,034 [15/447] | **0,570 · hal 0,034 [15/447]** | **0** |
| kural / gold.round1 | 0,738 · hal 0,344 [21/61] | **0,738 · hal 0,344 [21/61]** | **0** |
| B (9b, çoklu) / gold.v2 | 0,464 · hal 0,145 [65/447] · TP 65 | 0,473 · hal 0,143 [64/447] · TP 66 | **+0,009** |

Kural katmanı **birebir** tekrarlanıyor — beklenen, çünkü deterministik kod.
LLM kolu ise sıcaklık 0,0 ve sabit şemayla bile birebir tekrarlanmıyor:
aynı hücre iki koşumda 0,464 ve 0,473 verdi (TP 65 → 66). Sebep modelde değil
sunucuda: Ollama/GPU tarafında toplu işleme (batching) ve KV önbelleği
kayan-nokta toplama sırasını değiştirebiliyor.

**Karara etkisi yok** ve bu önemli: gözlenen varyans ±0,01 mertebesinde,
hücrelerin eşiğe olan uzaklığı ise 0,03–0,11. Yani varyans hiçbir hücreyi
eşiğin öbür tarafına taşımıyor. Ama varyansın **var olduğu** raporlanmalı;
aksi hâlde tablodaki üçüncü hane olduğundan fazla kesinlik iddia ederdi.

§10.3 tablosundaki `B` hücresi için **ikinci (yeni oturumdaki) koşum**
yazılıdır: artefaktı diskte duran, denetlenebilir olan o koşumdur.

### 10.4 Alan-başına kipin ÖLÇÜLEN yan etkisi: kesik yanıt riski 9 katına çıkıyor

Alan-başına kip gold.round1'de **katı modda tamamlanamadı**. Sebep ölçüldü ve
tesadüf değil:

```
alan=indirim_orani  metin_uzunlugu=110770  istem_uzunlugu=113530
sema_gecti=false  onarim=1
sebep=parse_error: dengeli JSON nesnesi kapanmamis (kesik yanit olabilir)
ham='{\n'
```

Korpusta 110.770 karakterlik (≈35 bin jeton) bir belge var; `num_ctx` 8192.
Ollama istemi kırpıyor ve model bu belgede `{` yazıp susuyor. Onarım denemesi
de düzeltemiyor (sıcaklık 0 → aynı çıktı).

**Bu, granülarite değişikliğinin doğrudan bir maliyetidir.** Çoklu-alan kipinde
belge başına 1 çağrı vardır; alan-başına kipte ~9. Belge başına ayrıştırma
hatası olasılığı da yaklaşık 9 katına çıkar. Aynı belge çoklu-alan kolunda
(B-r1) ayrıştırılabilir JSON döndürüp koşumu geçirdi; alan-başına kolda
dokuz denemeden biri kesildi ve `LLM_STRICT=1` koşumu — doğru davranışla —
durdurdu.

Sayı yine de üretildi: ölçüm katı modda düşen hücreler için **hoşgörülü modda**
(`LLM_STRICT=0`) tekrarlandı; o kipte başarısız alan atlanır, kalan alanlar
sorulmaya devam eder. Hangi hücrenin hangi kipte ölçüldüğü §10.3 tablosunda
**açıkça** yazıyor ve başarısız çağrı sayısı sağlık günlüğünden okunabilir.
İki kip arasındaki fark tek bir alanın düşmesidir; kolun lehine değil aleyhine
bir farktır (atlanan alan hiç değer üretmez), dolayısıyla hoşgörülü sayı bu
kolun **en iyimser** okumasıdır ve kabul kararını zayıflatmıyor.

### 10.5 Bağımsız ikinci doğrulama — README'nin 20 Ağustos ablasyonu

Bu rapordaki A100 ölçümü, depoda **zaten var olan** bir ablasyonun ikinci
bağımsız doğrulamasıdır. `README.md` (20 Ağu, 40 zor belge, `strict`) şunu
yayımlıyor:

| kol | mikro-F1 | halüsinasyon | McNemar vs `kural` |
|---|---|---|---|
| **kural** | **0,4771** | **0,0425** | — |
| llm (yalnız LLM) | 0,2545 | 0,0582 | p = 0,00105 · kural üstün |
| hibrit | 0,4402 | 0,1029 | p = 0,00050 · kural üstün |
| hibrit-verify | 0,3672 | 0,0984 | p = 0,0000123 · kural üstün |

İki ölçüm **farklı donanımda** (yerel vs A100), **farklı alt kümede** (40 zor
belge vs 48 + 134 tüm vakalar), **farklı tarihte** yapıldı ve aynı sonuca
çıktı: kural katmanı hiçbir LLM konfigürasyonunda geçilmiyor ve hibrit
halüsinasyonu belirgin biçimde artırıyor (README'de 2,4 kat; burada v2'de 1,7
kat, round1'de 1,6 kat).

Bu tekrarlanabilirlik iddiayı güçlendiriyor çünkü tek koşumun "şanssız bir
gün" olma ihtimalini kapatıyor. README'nin tablosu McNemar p-değerleri
taşıyor; bu rapor onları yeniden hesaplamadı (`--no-bootstrap`, bkz. §7.2) —
ama iki bağımsız ölçümün aynı yönde çıkması, tek bir p-değerinden daha güçlü
bir kanıttır.

**Şartname §16 açısından:** istenen şey bir ablasyon tablosudur, "hibridin
kazandığı" bir tablo değil. Bir katmanın KAZANMADIĞINI ölçmüş olmak da geçerli
bir ablasyon sonucudur ve bu proje onu gizlemiyor: negatif sonuç README'de,
`docs/rapor/ablasyon.md`'de ve bu raporda üç kez, sayılarıyla yazılı.

### 10.5b İkinci turun sağlık künyesi

`eval/reports/llm-sagligi.jsonl` (4.469 satır) ikinci turun tamamını taşıyor.
Kolonlar: kayıt = çıkarım isteği, gerçek = modele giden çağrı (kalanı
önbellek isabeti).

| koşum | kayıt | gerçek | başarısız | ortanca | model |
|---|---|---|---|---|---|
| `colab-B-9b-coklu-strict1` (kısmi) | 78 | 77 | 0 | 4,06 s | `qwen3.5:9b-q4_K_M` |
| `colab-C-7b-alan-strict0` | 1.123 | 996 | **4** | 0,54 s | `qwen2.5:7b-instruct` |
| `colab-C-7b-alan-strict1` | 127 | 0 | **1** | — | `qwen2.5:7b-instruct` |
| `colab-D-9b-alan-strict1` | **1.573** | 1.298 | **0** | 0,79 s | `qwen3.5:9b-q4_K_M` |

`colab-B-9b-coklu-strict1` satırı **kısmidir**: oturum bu koşumun ortasında
geri alındı (bkz. §10.3 köken notu). İlk turun satırları (`colab-v2-*`,
`colab-r1-*`) aynı dosyada duruyor.

Üç okuma:

1. **Alan-başına kipin maliyeti sayıyla görünüyor:** `D` hücresi tek başına
   1.573 çıkarım isteği; çoklu-alan kolları 48 ve 134. Yani ~9-12 kat.
2. **Başarısızlıklar yalnız 7b + alan-başına kolunda.** 9b, 1.573 tek-alan
   çağrısının **tamamında** geçerli JSON döndürdü (0 hata). Yani §10.4'teki
   kesik-yanıt arızası modele bağımlı: 9b onu göstermedi, dolayısıyla
   `D` hücresi katı modda ölçülebildi. Kolun kaybı bir mühendislik arızası
   değil, yine anlamlandırma.
3. **A100 ölçek farkı:** ortanca çağrı 0,54–4,06 s. Yerel makinedeki
   84–129 s'lik ortancalarla (aynı dosyanın `v2-hibrit-*` satırları) yan yana
   durduğu için donanım etkisi de aynı artefaktan okunabiliyor.

### 10.6 İkinci turun kararı: REDDEDİLDİ

Ölçüt dört eşiğin **hepsini** ister: v2'de F1 > 0,570 **ve** halüsinasyon
≤ 0,034; round1'de F1 > 0,738 **ve** halüsinasyon ≤ 0,344.
**Hiçbir hücre kabul ölçütünü geçmedi** — sekiz koşumun sekizinde regresyon
kapısı da kapalı.

Ölçümden sonra `gold.round1` yeniden anotlandı ve round1 barı **yükseldi**
(0,738 → 0,786 · hal 0,344 → 0,297). Bu, ret kararını güçlendirir, zayıflatmaz;
tahkim sonrası round1 hibrit sayıları ise **ölçülmedi** ve bu raporda
verilmiyor (§10.7).

Eşiklere dokunulmadı, hiçbir hücre gizlenmedi.

### 10.7 KAPSAM UYARISI — gold.round1 ölçümden SONRA yeniden anotlandı

Bu ölçüm bittikten sonra, ilgisiz bir iş kolunda `gold.round1` üzerinde bir
anotasyon tahkimi yapıldı ve uygulandı (`c5100ddb` "HAKEM-05 UYGULANDI",
23 hücre: 13 `absent`, 2 değer düzeltmesi, 4 boş hücre dolduruldu, 4
`unclear`). Etkisi kural kolunda **ölçülmüştür**:

| gold | taban (ölçüm anı) | taban (`HEAD`, HAKEM-05 sonrası) |
|---|---|---|
| gold.v2 | 0,570 · hal 0,034 [15/447] | **0,570 · hal 0,034 [15/447]** — değişmedi |
| gold.round1 | 0,738 · hal 0,344 [21/61] | **0,786 · hal 0,297 [22/74]** — değişti |

**Bunun anlamı, dürüst hâliyle:**

1. **§10.3'ün v2 satırları geçerli.** gold.v2 dokunulmadı; o dört hücre
   `HEAD`teki tabanla doğrudan karşılaştırılabilir.
2. **§10.3'ün round1 satırları, tahkimden ÖNCEKİ gold'a karşı ölçülmüştür**
   (`42493665` anlık görüntüsü). Tahkim sonrası round1 sayıları **ölçülmedi**;
   dolayısıyla bu raporda tahkim sonrası round1 hibrit F1'i için sayı
   verilmiyor.
3. **Kararın yönü değişmez, ve sebebi mekanik.** Tahkim, tabanı
   0,738 → 0,786'ya **yükseltti** ve halüsinasyon eşiğini 0,344 → 0,297'ye
   **sıkılaştırdı**. Yani geçilmesi gereken bar iki ölçütte de **yukarı**
   gitti; LLM kolları ise eski, daha alçak bara göre bile 0,703–0,735
   (F1) ve 0,492–0,541 (halüsinasyon) ile kalıyordu. Ayrıca tahkimin
   13 hücreyi `absent` yapması halüsinasyon fırsat sayısını 61 → 74'e
   çıkardı; hücreleri kuraldan DAHA ÇOK dolduran LLM kolları bu yeni
   `absent` hücrelerden daha fazla ceza alır, daha az değil.

   Kısacası: barın yükseldiği, kolun ise aynı kaldığı bir karşılaştırmada
   ret kararı zayıflamaz. Ama "kesin sayı" iddiası yalnız v2 için yapılıyor.
4. **Yeniden ölçüm gerekirse** dört round1 hücresi (A/B/C/D) yeniden
   koşulmalıdır; A100'de maliyeti ~1 saat ve komutlar §9'da hazır. Bu turda
   yapılmadı, çünkü ölçüm kapsamı dört hücreyle sınırlıydı ve tahkim ölçüm
   bittikten sonra geldi.

`eval/esikler-round1.json` bu turda **değiştirilmedi**; regresyon kapısı
sekiz koşumun sekizinde zaten kapalıydı.

## Kaynaklar

- `sqlite3 data/demo.db "select extractor, count(*) …"` → `rule|7032` (kök bulgu)
- `eval/reports/llm-sagligi.jsonl` → 364 A100 kaydı, 364/364 şema-geçerli
- `docs/rapor/ablasyon.md` §2, §6 → 2026-08-07 n=20 ablasyonu ve model künyesi
- `eval/esikler.json`, `eval/esikler-round1.json` → iki regresyon kapısı
- `tests/test_llm_saglik.py` → 17 test (kanıt kapısı · sağlık günlüğü · önbellek)
