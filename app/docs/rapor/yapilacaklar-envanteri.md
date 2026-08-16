---
title: "Yapılacaklar Envanteri"
tags: [envanter, yapilacaklar, teknofest]
date: 2026-08-03
status: taslak
---

# Yapılacaklar Envanteri — 2026-08-03

Bu belge, depodaki **yapılmamış / yarım / test edilmemiş / doğrulanmamış** her işin
tek dosyalık envanteridir. Amaç bir yol haritası sunmak değil; **eksiklerin
kaynaklı ve sayılabilir** bir listesini tutmaktır.

**Dürüstlük kuralı:** Kanıtsız satır yazılmamıştır. Her madde ya bir `dosya:satır`
ya da bu oturumda **koşturulmuş bir komutun çıktısına** dayanır. Doğrulanamayan
şeyler `doğrulanmamış` olarak işaretlenmiştir, "yapıldı" sayılmamıştır.

Yol gösterimleri depo köküne (`/Users/mehmetefeaytas/anatoliaaI`) göredir.

**Takvim baskısı:** Şartname §3 (s.4) "Yarışma Çevrimiçi Süreci: 27 Temmuz –
26 Ağustos" diyor. Bugün 3 Ağustos → **kalan 23 gün**.

---

## Yöntem

Bakılan yerler:

| Kaynak | Ne için |
|---|---|
| `CLAUDE.md`, `AGENTS.md`, `app/CLAUDE.md`, `README.md`, `app/README.md` | bağlayıcı kurallar, ilan edilen durum |
| `_oturum-devir.md`, `index.md`, `log.md`, `lint-report.md` | açık uçlu işler, devir notları, vault durumu |
| `2026_TEKNOFEST_TYDA_SARTNAME_Ikinci_Senaryo_TR_1_SmsXO.pdf` (25 sayfa) | zorunlu çıktılar — birincil kaynak |
| `sources/teknofest/2026-06-16-teknofest-tyda-sartname-2-senaryo.md` | şartname ingest özeti + open-threads |
| `app/docs/sartname-kod-eslesme.md`, `app/docs/rapor/olcumler.md`, `app/docs/rapor/anatolia-ai-teknik-rapor.md` | projenin kendi dürüst eksik listeleri |
| `app/docs/OFFLINE-KANIT.md`, `kaynak-tuketimi.md`, `model-license-audit.md`, `katilim-bankaciligi-guvenligi.md`, `veri-katmani.md` | ölçüm/kanıt boşlukları |
| `app/src`, `app/tests`, `app/eval`, `app/scripts`, `app/web`, `app/config` | kod işaretleri, test kapsamı |
| `.github/workflows/ci.yml`, `app/docker-compose.yml`, `app/Dockerfile.api`, `app/.env.example`, `.gitignore` | CI ve dağıtım eksikleri |

Koşturulan komutlar ve sonuçları:

| Komut | Sonuç |
|---|---|
| `pdftotext -layout 2026_TEKNOFEST_..._SmsXO.pdf` | 25 sayfa metin çıkarıldı; §5.1–§5.10, §6, §7, §9, §10 doğrudan okundu |
| `cd app && python3 -m unittest discover -s tests` (sistem python3) | **`Ran 890 tests in 2.764s` · `OK (skipped=62)`** |
| aynı komut, `.venv` yorumlayıcısıyla (fastapi/psycopg kurulu) | `Ran 890 tests in 2.969s` · `OK (skipped=53)` — 62 ↔ 53 farkı `fastapi` yokluğundan |
| `pytest -q` (pytest depo dışına kurularak) | `837 passed, 53 skipped, 1 warning, 331 subtests passed in 3.52s`; `--collect-only` → `890 tests collected` — **kırık test yok** |
| `cd app && python3 -m pytest --version` | `Failed to spawn process: No such file or directory` — **pytest kurulu değil** |
| `cd app && .venv/bin/python -m pytest --version` | `No module named pytest` — **venv'de de yok**, `requirements.txt:64` ilan etmesine rağmen |
| `find app -name "metrics.json" -o -name "per_field.csv" -o -name "env.json"` | **0 sonuç** — `run_eval`/`ablation` bugüne dek hiç kalıcı metrik raporu üretmemiş |
| `python -m eval.properties --raw-dir data/raw` | `849 belge (726'sında en az bir alan; kapsam 85.5%) — tüm değişmezler GEÇTİ (0 ihlal)` |
| `csv.DictReader` ile 8 anotasyon CSV'si sayıldı | **3.422 satırın 0'ı doldurulmuş** (aşağıda tam çıktı) |
| `git log --oneline -30`, `git status --short`, `git tag -l` | son commit **2026-07-31**, `hafta-00` + `hafta-01` etiketleri, `app/docs/rapor/` ve `AGENTS.md` **takip edilmiyor** |
| `git check-ignore -v app/data/demo.db` | `app/.gitignore:9:*.db` — **demo.db depoda yok** |
| `grep -rn` (TODO/FIXME/stub/skip) `app/src app/tests app/eval app/scripts app/web app/config` | kaynak kodda `TODO`/`FIXME`/`XXX`/`HACK`/`NotImplementedError` **yok**; gerçek eksikler docstring'lerde |
| Modül ↔ test eşlemesi (`grep -rl` 27 modül için) | `src/scraping/discover.py`, `harvest.py`, `harvest_products.py`, `scripts/latency_bench.py`, `preannotate.py`, `report_iaa.py` → **0 test dosyası** |

Anotasyon CSV sayımının ham çıktısı:

```
round0_kalibrasyon_A.csv satir: 260 doldurulmus: 0
round0_kalibrasyon_B.csv satir: 260 doldurulmus: 0
round0_kalibrasyon_C.csv satir: 260 doldurulmus: 0
round0_kalibrasyon_D.csv satir: 260 doldurulmus: 0
round1_A.csv satir: 650 doldurulmus: 0
round1_B.csv satir: 650 doldurulmus: 0
round1_main_C.csv satir: 541 doldurulmus: 0
round1_main_D.csv satir: 541 doldurulmus: 0
```

**Bakılmayan / bakılamayan:** GPU gerektiren hiçbir ölçüm bu oturumda koşturulmadı;
`docker compose up` denenmedi (bu makinede doğrulanmadı); `app/web` derlemesi
koşturulmadı. Bu üçü envanterde birer madde olarak duruyor, "çalışıyor" diye
işaretlenmedi.

> ⚠️ **Kapsam sınırı — eşzamanlı çalışma:** Bu envanter, depo durumunun
> **2026-08-03 saat ~16:00** anlık görüntüsüne dayanır. Envanter yazılırken
> (19:09–19:13 arası) başka bir oturum depoda çalışmaya devam etti ve şu
> dosyalar değişti: `app/src/scraping/snapshot.py` (**yeni modül**),
> `app/src/scraping/fetcher.py`, `app/src/scraping/config.py`,
> `app/config/banks.yaml` (`git diff --stat` → 150 ekleme / 11 silme) ve
> `app/data/snapshots/` (yeni klasör). **Bu değişiklikler envanterde
> incelenmemiştir**; yeni bir snapshot/arşivleme yeteneği eklendiği için
> §5.1 (veri toplama) ve T-025, T-049, T-067 maddeleri yeniden gözden
> geçirilmelidir.

> ⚠️ **Bu envanter çıkarılırken üretilen artefakt:** CI'ın 4. adımını doğrulamak
> için `python -m eval.run_eval --gold data/gold/gold.sample.json` koşuldu ve
> komut diske yazdığı için `app/eval/reports/20260803-160006/` klasörü oluştu
> (`metrics.json`, `env.json`, `report.md`, `per_field.csv`). **Takip edilen
> hiçbir dosya değişmedi** (`git status` → `?? app/eval/reports/20260803-160006/`).
> Bu klasör 3 örneklik duman testinin çıktısıdır, gerçek metrik değildir; elle
> silinmesi gerekir (T-073).

---

## Özet — önem düzeyine göre

| Önem | Madde |
|---|---:|
| **kritik** | 12 |
| **yüksek** | 26 |
| **orta** | 25 |
| **düşük** | 10 |
| **Toplam** | **73** |

Duruma göre:

| Durum | Madde |
|---|---:|
| yapılmamış | 52 |
| doğrulanmamış | 11 |
| yarım | 9 |
| test edilmemiş | 1 |

Konuya göre:

| Konu | Madde |
|---|---:|
| Dokümantasyon | 17 |
| Değerlendirme | 12 |
| Şartname uyumu (teslimler) | 8 |
| RAG-Chatbot | 7 |
| CI-Dağıtım | 7 |
| Test | 6 |
| Çıkarım | 5 |
| On-Prem | 3 |
| Karşılaştırma | 2 |
| Dashboard | 2 |
| Veri tabanı | 2 |
| Veri toplama | 2 |

**Kritik 12 maddenin dağılımı:** 5'i teslim zorunluluğu (T-001…T-006), 5'i
Model Başarısı %30 ölçüm zinciri (T-010…T-014), 2'si jürinin göreceği demonun
korpusu (T-037, T-038).

---

## Ana tablo

### A. Şartname uyumu — teslim zorunlulukları

> ⚠️ **BU TABLONUN «Durum» KOLONU 3 AĞUSTOS KESİTİDİR.** Aşağıdaki satırların
> bir kısmı o tarihten sonra kapandı ve **satırlar bilerek düzenlenmedi** —
> envanterin değeri, o günkü durumun bozulmamış kaydı olmasıdır. Kapananlar
> (16 Ağustos 2026 itibarıyla, hepsi ölçümle doğrulandı):
>
> | task | ne oldu |
> |---|---|
> | T-001 | ✅ Veri seti Hugging Face'te herkese açık (15 Ağu) |
> | T-002 | ✅ Demo videosu 3:04, kartsız, 12 ekran |
> | T-003 | ✅ 1 dk kesit — 59 sn, sekiz ekran |
> | T-004 | ✅ Sunum PDF (15 sayfa) + PPTX (15 slayt) |
> | T-007 | ✅ Haftalık etiketler `hafta-00`…`hafta-06` kesintisiz |
> | T-020 | ✅ Sahte `%0` kâr payı temizlendi — alan 4.709 → 4.704, Dünya Katılım sahte `%0` 7 → 0 |
> | T-074 | ✅ Şartname 7 sütunlu ürün tablosu — `GET /urun-tablosu`, 32 test yeşil |
>
> Güncel ve **kanıt komutlu** teslim durumu için tek doğruluk kaynağı:
> [`app/docs/SARTNAME-UYUM.md`](../SARTNAME-UYUM.md) (2026-08-16 itibarıyla
> ✅ 18 · 🟠 1 · ❌ 0, toplam 19 satır). ⚠️ Kapanan kalemlerin dosyaları **henüz commit
> edilmemiş**; `git add` teslim öncesi zorunlu.

| Task No | Konu | Durum | Önem | İçerik | Kanıt | Bağımlılık |
|---|---|---|---|---|---|---|
| T-001 | Şartname uyumu | yapılmamış | kritik | Veri setinin herkese açık indirme bağlantısını üret (GitHub Release / HF Datasets / Zenodo) ve README'ye yaz | `README.md:117` → *"**Herkese açık indirme bağlantısı:** _(yükleme tamamlandığında buraya eklenecektir)_"*; şartname §9 s.18 "(3) kullanılan veri setinin indirilebileceği herkese açık bir bağlantısını içermelidir" | T-005 |
| T-002 | Şartname uyumu | yapılmamış | kritik | Maksimum 5 dakikalık demo videosunu çek (arayüz + dashboard + chatbot + metin girdisi + yapılandırılmış çıktı + karşılaştırma) | Şartname §6 s.14; `find . -iname "*sunum*" -o -iname "*.pptx"` → **hiç sonuç yok**; `app/docs/rapor/anatolia-ai-teknik-rapor.md:1105` "❌" | T-037 |
| T-003 | Şartname uyumu | yapılmamış | kritik | 1 dakikalık kısa demo videosunu çek (§10 ayrı süre veriyor) | Şartname §10 s.19 *"Sunum süresi 4 dakika, demo videosu süresi ise 1 dakika olacaktır"*; `app/docs/rapor/anatolia-ai-teknik-rapor.md:1105` | T-002 |
| T-004 | Şartname uyumu | yapılmamış | kritik | Jüri sunumunu **PDF ve PPTX** olarak hazırla | Şartname §6 s.14 *"Sunum Materyali: … (PDF ve PPTX formatında)"*; depoda `.pptx` dosyası yok (`find` çıktısı boş) | T-013 |
| T-005 | Şartname uyumu | yapılmamış | yüksek | Veri setine açık lisans ata (ör. CC-BY-4.0) ve veri seti kartı yaz | Şartname §8 s.17 *"veri kümelerinin … Açık Kaynak herhangi bir lisans ile paylaşımı zorunludur"*; `app/docs/rapor/anatolia-ai-teknik-rapor.md:1107` "❌" | — |
| T-006 | Dokümantasyon | yarım | kritik | Teknik raporu (`app/docs/rapor/`, 77 KB md + PDF + 11 ekran görüntüsü + 12 grafik) commit et — şu an depoda yok, jüri göremez | `git status --porcelain -uall` → `?? app/docs/rapor/anatolia-ai-teknik-rapor.md`, `?? app/docs/rapor/…` (32 kalem) | T-066 |
| T-007 | Şartname uyumu | yapılmamış | yüksek | `hafta-02` etiketiyle haftalık güncellemeyi yap; son commit 31 Temmuz, bugün 3 Ağustos | `git log -1 --format=%ad` → `2026-07-31 17:41:41`; `git tag -l` → `hafta-00`, `hafta-01`; şartname §9 s.18 "en az haftalık olarak güncellemelerin sisteme yüklenmesi zorunludur" | T-006 |
| T-008 | Şartname uyumu | doğrulanmamış | yüksek | Takım tanıtım sunumunun (üye görev tanımları dahil) hazır olduğunu doğrula — depoda izi yok | Şartname §8 s.16 *"takım tanıtım sunumu zorunludur"* + s.17 *"sunumda takım üyelerinin tamamının … görev tanımları yapılmalıdır"*; `README.md:19-24` yalnızca "Takım Kaptanı / Ekip Üyesi" yazıyor, görev tanımı yok | — |
| T-009 | Şartname uyumu | yapılmamış | orta | Jüriye yapılan sunumu GitHub hesabına yükle | Şartname §10 s.19 *"yaptıkları sunumu GitHub hesaplarına da yüklemek zorundadır"* | T-004 |

### B. Değerlendirme — Model Başarısı %30 zinciri

| Task No | Konu | Durum | Önem | İçerik | Kanıt | Bağımlılık |
|---|---|---|---|---|---|---|
| T-010 | Değerlendirme | yapılmamış | kritik | 4 anotatörle 3.422 satırlık anotasyonu doldur — **hiç başlanmadı** | 8 CSV'de `verdict`/`gold_value` dolu satır sayısı **0/3.422** (bu oturumda `csv.DictReader` ile sayıldı); `app/data/gold/review/_atama.md:5-18` planı; `app/tests/test_run_eval.py:7` *"gerçek gold seti henüz yok"* | — |
| T-011 | Değerlendirme | yapılmamış | kritik | Kalibrasyon turunu (20 belge × 4 anotatör) koş, `scripts/report_iaa.py` ile κ hesapla, κ<0,67 ise kılavuzu düzelt | `app/data/gold/review/_atama.md:22` "Bu adım ATLANIRSA … gold yeniden yapılır"; `app/docs/rapor/olcumler.md:124` "Cohen's / Fleiss' κ (IAA) ⏳ hesaplanmadı" | T-010 |
| T-012 | Değerlendirme | yapılmamış | kritik | `build_gold.py` → `split_gold.py` ile gold'u üret, TEST bölmesini dondur ve sha256'la | `app/scripts/split_gold.py:279` *"Bölme henüz üretilmemiş. Önce --gold ile koşun."*; `app/data/gold/` altında yalnızca `gold.sample.json` (**3 kayıt**) var | T-011 |
| T-013 | Değerlendirme | yapılmamış | kritik | Alan bazında P/R/F1 + makro-F1 + %95 bootstrap güven aralığı üret; `metrics.json` hiç üretilmemiş | `find app -name "metrics.json" -o -name "per_field.csv" -o -name "env.json"` → **0 sonuç**; `app/eval/reports/` içeriği yalnızca 30 Tem tarihli `violations-*.jsonl` (4 dosya); `app/docs/rapor/anatolia-ai-teknik-rapor.md:1079` *"⏳ SAYI YOK … `metrics.json` hiç üretilmedi"*; 3 örneklik duman testi `mikro-F1 1.000 [1.000–1.000] (n=3 belge)` veriyor ve 12 alanın 9'u `ATL` (atlandı) | T-012 |
| T-014 | Değerlendirme | yapılmamış | kritik | Ablasyonu koş: kural-only / LLM-only / hibrit / hibrit-verify + McNemar; hibridin üstünlüğü şu an **iddia** | `app/docs/rapor/olcumler.md:125` "Ablasyon … ⏳ koşulmadı"; `app/eval/ablation.py` (19,2 KB) yazılı ama sonucu yok | T-012, T-044 |
| T-015 | Değerlendirme | yapılmamış | yüksek | "Zor vakalar" alt kümesini kürle ve ayrı metrik yayımla (`app/CLAUDE.md:113` bunu jüri için en ikna edici artefakt sayıyor) | `app/docs/rapor/olcumler.md:126` "Zor-vaka alt kümesi metriği ⏳ kürlenmedi"; `app/data/gold/gold.sample.json` içinde `"hard": true` yalnız 2 sentetik kayıt | T-012 |
| T-016 | Değerlendirme | yapılmamış | yüksek | Halüsinasyon oranını ölç (`absent_fields` hattı kurulu ama koşulmadı) | `app/docs/rapor/olcumler.md:123` "Halüsinasyon oranı ⏳ yok (`absent_fields` hattı hazır)" | T-013 |
| T-017 | Değerlendirme | yapılmamış | yüksek | Güven skoru kalibrasyonunu yaz ve koş — `eval/calibration.py` **dosya olarak yok**, ama kod onu vaat ediyor | `app/src/extraction/rules/confidence.py:32-35` *"Skorlar kalibre edilmemiştir … gerçek kalibrasyon `eval/calibration.py`'de … yapılacak"*; `ls app/eval/` → `calibration.py` yok | T-012 |
| T-018 | Değerlendirme | doğrulanmamış | yüksek | LLM katmanının korpusa gerçekten alan katıp katmadığını ölç — bugüne dek **0 alan** kattı | `app/docs/rapor/anatolia-ai-teknik-rapor.md:1120` *"LLM kolu korpusa hiç alan katmadı (2.204/2.204 = kural)"* | T-044 |

### C. Çıkarım / RAG-Chatbot / Karşılaştırma — kalite açıkları

| Task No | Konu | Durum | Önem | İçerik | Kanıt | Bağımlılık |
|---|---|---|---|---|---|---|
| T-019 | Çıkarım | yapılmamış | yüksek | Menü/navigasyon metninin kaynak span'ine sızmasını engelle — jüri kanıt sanılan bir span'de site navigasyonu görüyor | `app/docs/rapor/anatolia-ai-teknik-rapor.md:1139-1141` *"chatbot kaynak tablosunda `\"Navigasyonu görüntüle İçeriği görüntüle…\"` görünüyor"*; aynı belge `:284` satırında da kayıtlı | — |
| T-020 | Karşılaştırma | yapılmamış | yüksek | Bağlamsız `%0` oranlarının "en düşük kâr payı" sıralamasına girmesini engelle | `app/docs/rapor/anatolia-ai-teknik-rapor.md:1142-1143` *"API market sayfasındaki `\"LCW'de %0 kâr payıyla\"` ifadesi karşılaştırmada birinci çıkıyor"* | — |
| T-021 | Çıkarım | yapılmamış | yüksek | Zaman-koşullu ifadeleri ("ilk 3 ay ödemesiz") ayrı alan olarak çıkar — `app/CLAUDE.md:104-114` bunu %30'un merkezi sayıyor | `app/docs/rapor/anatolia-ai-teknik-rapor.md:411-414` *"'İlk 3 ay ödemesiz' … ayrı bir alan olarak çıkarılmıyor … ama ölçülmedi"* | T-044 |
| T-022 | Çıkarım | yarım | orta | Sınıflanamayan 60 belgeyi (%7,1) azalt veya "kurumsal/bilgi sayfası" olarak açıkça etiketle | `app/docs/sartname-kod-eslesme.md:117` *"Sınıflanamayan: 60 belge (%7,1)"* | — |
| T-023 | Karşılaştırma | yarım | yüksek | Kâr payı kapsamının %5,5 olmasının karşılaştırmayı ne kadar kısıtladığını ölç ve arayüzde göster | `app/docs/rapor/anatolia-ai-teknik-rapor.md:1096` *"§5.7 … 5/5 ölçüt; **kâr payı kapsamı %5,5 kısıtı**"*; `app/docs/sartname-kod-eslesme.md:197-200` "495 skorlanabilir kampanyanın yalnızca %9,5'inde kâr payı oranı var" | T-013 |
| T-024 | RAG-Chatbot | yapılmamış | yüksek | `except Exception: pass` ile LLM hatasının tamamen sessizleşmesini düzelt (log/telemetri ekle) | `app/src/chatbot/rag.py:380` — `except Exception: pass`, `RagAnswer` dönmeden fallback'e düşüyor | — |
| T-025 | Veri toplama | yapılmamış | orta | `page.wait_for_selector` timeout'unu geniş `except Exception: pass` ile yutmayı bırak | `app/src/scraping/fetcher.py:172` | — |
| T-026 | RAG-Chatbot | yarım | orta | Chatbot RAG p95 = 325 ms performans borcunu kapat (korpus 1.696 belgeye çıkınca oluştu) | `app/docs/rapor/olcumler.md:203` *"Korpus 1.696 belgeye çıkınca p95 **325 ms** ⚠️ kayıtlı performans borcu"*; `app/docs/sartname-kod-eslesme.md:248` chatbot p95 325,02 ms | — |
| T-027 | RAG-Chatbot | doğrulanmamış | orta | RAG kanıt eşiğini (0,30–0,45) ölçüme dayandır — şu an elle seçilmiş sabit | `app/src/chatbot/rag.py:219` *"Eşik ölçülmüş bir kalibrasyon DEĞİLDİR"* | T-012 |
| T-028 | RAG-Chatbot | doğrulanmamış | orta | `bge-m3` ile gerçek gömme kalitesini ölç — pgvector ölçümü `HashingEmbedder` ile yapıldı, yani model kalitesi ölçülmedi | `app/docs/rapor/olcumler.md:210-211` *"⚠️ `HashingEmbedder` ile ölçüldü, **bge-m3 ile değil**"* / *"bge-m3 gerçek gömme kalitesi ⏳ ölçülmedi"* | — |
| T-029 | RAG-Chatbot | yapılmamış | orta | Keyword vs Vector alaka ablasyonunu koş — vektör yolunun kazancı bilinmediği için `RAG_RETRIEVER=keyword` varsayılan kalıyor | `app/docs/rapor/olcumler.md:212`; `app/docker-compose.yml:189` `RAG_RETRIEVER: keyword` | T-028 |
| T-030 | Veri tabanı | doğrulanmamış | düşük | IVFFlat (`lists=32`) indeksinin faydasını ölç | `app/docs/rapor/anatolia-ai-teknik-rapor.md:1137` *"IVFFlat (`lists=32`) fayda ölçümü yapılmadı"* | T-040 |
| T-031 | Çıkarım | doğrulanmamış | orta | Çelişki tespitinin **yanlış negatif** oranını ölç — 849 belgede yalnız 1 çelişki bulundu, kuralların fazla muhafazakâr olup olmadığı bilinmiyor | `app/docs/rapor/anatolia-ai-teknik-rapor.md:685-689` *"Hangisi olduğu **ölçülmedi** — yanlış negatif oranı bilinmiyor"*; `app/docs/rapor/olcumler.md:336` | T-012 |
| T-032 | Çıkarım | yapılmamış | orta | GLiNER "geri-çağırma ağı" kolunu (K3) uygula veya `gliner` bağımlılığını tamamen düş | `app/docs/model-license-audit.md:180` *"`gliner` … Kodda hiç geçmiyor … Dev split'te K2'yi geçmezse hem kol hem bağımlılık düşer"* | T-014 |
| T-033 | RAG-Chatbot | yapılmamış | orta | Ürün düzeyi filtre ekle — "Kuveyt Türk'ün **altın hesabı** kâr payı" sorusu başka ürünün oranıyla yanıtlanabiliyor | `app/docs/katilim-bankaciligi-guvenligi.md:372-374` (Dürüst eksikler #6) | — |
| T-034 | RAG-Chatbot | yapılmamış | düşük | Tahmin/gelecek soruları için zaman-kipi kapısı ekle ("2030'da kâr payı ne olacak?" bugün yanıtlanıyor) | `app/docs/katilim-bankaciligi-guvenligi.md:369-371` (Dürüst eksikler #5) | — |
| T-035 | Değerlendirme | yarım | orta | Güvenlik değerlendirme setini büyüt ve çift-anote et — şu an **tek anotatörlü, 30 soru**, aşırı red kontrol grubu 6 soru | `app/docs/katilim-bankaciligi-guvenligi.md:375-379` (Dürüst eksikler #7) ve `:354-360` (#1) | T-011 |
| T-036 | Dashboard | yapılmamış | orta | Chatbot cevaplarında markdown render et — `**` işaretleri ham görünüyor, demoda göze çarpar | `app/docs/rapor/anatolia-ai-teknik-rapor.md:1146` | — |
| T-037 | Veri tabanı | yapılmamış | kritik | `data/demo.db` depoda olmadığı için temiz klonda jüri **849 belge yerine 3 fixture belgesi** görüyor: DB'yi ya yayımla ya da kurulum adımına `build_demo_db` ekle | `git check-ignore -v app/data/demo.db` → `app/.gitignore:9:*.db`; `git ls-files app/data/demo.db` → **0**; `app/docker-compose.yml:163-172` *"Dosya yoksa API açılışta fixture'lardan tohumlar … sadece korpus küçük olur"*; `app/docs/rapor/olcumler.md` §9 *"`DATABASE_PATH=:memory:` → `/campaigns` → 3 kampanya"* | T-038 |
| T-038 | Dokümantasyon | yapılmamış | kritik | `python -m scripts.build_demo_db` adımını **iki README'nin** kurulum bölümüne ekle — şu an yalnız commit edilmemiş raporda ve `veri-katmani.md`'de geçiyor | `grep -rn "build_demo_db" --include="*.md"` → yalnız `app/docs/rapor/anatolia-ai-teknik-rapor.md:546`, `app/docs/veri-katmani.md:245,252,255`; `README.md` ve `app/README.md`'de **yok** (şartname §6 s.13 "kurulum adımları net bir şekilde belirtilmelidir") | — |

### D. CI, dağıtım, on-prem

| Task No | Konu | Durum | Önem | İçerik | Kanıt | Bağımlılık |
|---|---|---|---|---|---|---|
| T-039 | CI-Dağıtım | doğrulanmamış | yüksek | Tam `docker compose up` (postgres + api + web, `--network none`) koş ve transkriptini sakla — bugüne dek yalnız API konteyneri kanıtlandı | `app/docs/OFFLINE-KANIT.md:529` *"`docker compose up` tam yığın (postgres + api + web) ⏳ koşturulmadı"* | T-037 |
| T-040 | CI-Dağıtım | doğrulanmamış | yüksek | pgvector/Postgres'in ağsız ayağa kalktığını ölç — imajın çekilip çekildiğine bile bakılmamış | `app/docs/OFFLINE-KANIT.md:530` *"pgvector / Postgres ağsız başlatma ⏳ ölçülmedi — İmaj çekildi mi diye bakılmadı"* | T-039 |
| T-041 | CI-Dağıtım | doğrulanmamış | yüksek | x86_64 / amd64 mimarisinde doğrula — tüm ölçümler arm64 host'ta yapıldı, jüri makinesi büyük olasılıkla amd64 | `app/docs/OFFLINE-KANIT.md:533` *"x86_64 (amd64) mimarisi ⏳ ölçülmedi — Host arm64 … **doğrulanmadı**"* | T-039 |
| T-042 | On-Prem | yapılmamış | orta | Model ağırlıklarının SHA-256 tablosunu doldur — prosedür yazıldı, tablo boş | `app/docs/OFFLINE-KANIT.md:473` *"⏳ KOŞTURULMADI — sebep: bu ortamda model ağırlıkları indirilmedi"*, `:481-483` üç satır da `⏳` | T-044 |
| T-043 | On-Prem | yapılmamış | orta | GPU profillerini (B: CPU+GGUF, C: RTX 4090, D: A100/H100) ölç veya "donanım yok" gerekçesini sunuma açıkça taşı | `app/docs/kaynak-tuketimi.md:27-29` üç profil de `⏳ ölçülmedi`; `:120-129` ve `:144-154` boş tablolar | — |
| T-044 | On-Prem | yapılmamış | yüksek | vLLM + Trendyol-LLM-8B-T1 (ve Ollama + Qwen3-4B GGUF) uçtan uca koşusunu yap — hibrit yolun gerçek gecikmesi ve katkısı hiç ölçülmedi | `app/docs/OFFLINE-KANIT.md:523-525` üç satır `⏳ ölçülmedi`; `app/docker-compose.yml:130` `--model Trendyol/Trendyol-LLM-8B-T1` (profil `gpu`) | — |
| T-045 | CI-Dağıtım | doğrulanmamış | orta | `trafilatura` GPL riskini doğrula veya bağımlılığı kalıcı olarak düş | `app/docs/model-license-audit.md:126-135` *"⚠️ belirsiz · ⏳ AÇIK RİSK … **bu doğrulanmadı**"*; `app/requirements.txt:24` satırı zaten yorum (`# trafilatura>=1.8`) | — |
| T-046 | CI-Dağıtım | yapılmamış | yüksek | CI'ya Postgres servisi (`ANATOLIA_TEST_DATABASE_URL`) ve FastAPI bağımlılıklı bir iş ekle — 53 test **hiçbir ortamda** koşmuyor | Sistem python3: `OK (skipped=62)`; `.venv` (fastapi var, Postgres yok): `OK (skipped=53)`; `pytest -rs` → 53 atlamanın **tamamı** tek nedenden: `Postgres yok — ANATOLIA_TEST_DATABASE_URL tanımlı değil` (`test_pgvector_repository` 26 · `test_api_backend` 14 · `test_repo_parity` 13); `.github/workflows/ci.yml:45-48` üçüncü parti paket kurulmadığını doğruluyor | — |
| T-047 | Test | yapılmamış | yüksek | Frontend testi ekle — `app/web` altında 2.595 satır TSX/TS var, tek test dosyası ve `test` script'i yok | `app/web/package.json` script'leri: yalnız `dev`, `build`, `start`, `lint`; `app/web/app/**` içinde `*.test.*` / `*.spec.*` **yok** | — |
| T-048 | Test | yapılmamış | orta | `pytest`'i ya gerçekten kur ya dokümanlardan çıkar — 3 yerde `pytest` deniyor, `requirements.txt:64` ilan ediyor, hiçbir ortamda kurulu değil ve 39 dosya `unittest` | `python3 -m pytest --version` → `No such file or directory`; `.venv/bin/python -m pytest` → `No module named pytest`; `app/requirements.txt:64` `pytest>=8.0`; `app/CLAUDE.md:259`, `app/README.md:54`, `README.md` kurulum bölümü | — |
| T-049 | Test | yapılmamış | orta | Testi olmayan modüllere test yaz — AST eşlemesiyle hiçbir testten import edilmeyen ≈1.784 satır: `src/scraping/{harvest,harvest_products,discover,run}.py`, `src/extraction/run.py`, `eval/report.py`, `scripts/{latency_bench,preannotate,report_iaa}.py` | Modül ↔ test eşlemesi: her biri için **0 test dosyası**; `scripts/latency_bench.py` 378 satır, `preannotate.py` 366, `report_iaa.py` 286, `eval/report.py` 260, `src/scraping/harvest.py` 198, `harvest_products.py` 165 | — |
| T-069 | Test | yapılmamış | orta | `pyproject.toml`'a pytest yapılandırması ve **kapsam (coverage) eşiği** ekle veya `unittest`'i tek yol ilan et — şu an ne marker, ne `testpaths`, ne kapsam ölçümü var | `app/pyproject.toml` (78 satır) yalnız `[tool.ruff*]` bölümleri içeriyor; `[tool.pytest.ini_options]` **yok**; `pytest.ini`/`setup.cfg`/`tox.ini`/`conftest.py` **yok**; `pytest-cov`/`coverage` ne requirements'ta ne `.venv`'de | T-048 |
| T-070 | Dokümantasyon | yapılmamış | orta | `ci.yml`'deki bayat yorumu düzelt: "16 dosyada 345 test. Yerelde 0,078 sn" diyor; gerçek 39 dosya / 890 test / ~3 sn | `.github/workflows/ci.yml:50` yorum satırı ↔ `Ran 890 tests in 2.764s` | T-052 |
| T-071 | Test | yapılmamış | düşük | Testlerde kapatılmayan SQLite bağlantılarını düzelt — `unittest` koşumu çok sayıda `ResourceWarning: unclosed database in <sqlite3.Connection>` basıyor | `.venv` ile `python -m unittest discover -s tests` çıktısındaki `ResourceWarning` yığını (davranışı bozmuyor ama sızıntı) | — |
| T-072 | Değerlendirme | yarım | yüksek | Ön-anotasyonu LLM açıkken yeniden üret — mevcut `preannotations.json` `llm_available=False` ve `disagreement_count=0`, yani anotatörler **uyuşmazlık sinyali olmadan** çalışacak ve `disagreement` kolonu ölü | `app/data/gold/preannotations.json` üstbilgisi: `doc_count=250`, `field_count=945`, `seed=42`, `llm_available=False`, `disagreement_count=0`; CSV'lerde `disagreement` kolonu var (`round1_A.csv` başlığı) ama hepsi boş | T-044 |
| T-073 | Değerlendirme | yapılmamış | düşük | Bu envanter oturumunda üretilen duman-testi artefaktını sil: `rm -rf app/eval/reports/20260803-160006` | `git status --porcelain -uall` → `?? app/eval/reports/20260803-160006/`; içinde 3 örneklik gold ile üretilmiş `metrics.json`/`report.md`/`per_field.csv`/`env.json` var, gerçek metrik değil | — |
| T-074 | Dashboard | ✅ **BİTTİ + ÖLÇÜLDÜ** (2026-08-16) | **yüksek** | Şartname s.11–12'nin **7 sütunlu, banka başına tek satır** kıyas tablosu üretilemiyor; `/compare` **tek alanlı**. Karar: ① yeterli alanı olan kampanyalar için 7 sütunlu görünüm üret (boşluk "—"), ② «Kampanya Avantajı» serbest metin çıkarıcısı ekle, ③ üretme ve sapmayı sunumda önce biz söyle | Ölçüm 2026-08-16: `GET /compare` tek `field` parametresi alır (`src/api/main.py:1306`); `RankRow` tek `value` sütunu taşır; `ComparePanel.tsx:605-612` başlıkları `Sıra·Banka·Değer·Ham ifade·[Güven]·Katman·Durum·Kaynak`; `EXTRACTION_FIELDS` (12 alan) içinde `kampanya_avantaji` **yok**. Ayrıntı: §"Örnek Temsili Senaryolar" Senaryo-1 satırı altındaki düzeltme bloğu | T-020, T-022, T-023 |
| T-050 | Test | test edilmemiş | orta | `eval/ablation.py` için doğrudan test yaz — 19,2 KB modülün tek dolaylı kapsaması `tests/test_predictors.py:202` | `grep -rl "eval.ablation" tests/` → 1 dosya, o da tahmin-kaynağı paritesini test ediyor; `app/eval/ablation.py` için özel test dosyası yok | T-014 |
| T-051 | CI-Dağıtım | yapılmamış | düşük | `model-license-audit.md` denetim listesinde açık kalan 2 maddeyi kapat (`requirements.txt` = gerçekten kullanılanlar; teslim imajında GPL linklenmiş kod yok kanıtı) | `app/docs/model-license-audit.md:193-194` iki `- [ ]` işaretsiz madde | T-045 |

### E. Dokümantasyon, tutarlılık, bilgi arşivi

| Task No | Konu | Durum | Önem | İçerik | Kanıt | Bağımlılık |
|---|---|---|---|---|---|---|
| T-052 | Dokümantasyon | yapılmamış | yüksek | Test sayısını 6 farklı yerde tek doğru değere (**890**) eşitle | `app/docs/rapor/olcumler.md:373-382` tablosu: kök `README.md` 54 · `log.md` 129 · `app/README.md` + CI yorumu 345 · `OFFLINE-KANIT.md` 607 · `sartname-kod-eslesme.md:8` 695 · `veri-katmani.md` 835; bugün ölçülen: `Ran 890 tests` | — |
| T-053 | Dokümantasyon | yapılmamış | yüksek | `sartname-kod-eslesme.md`'nin iç çelişkisini gider: §5.7 tablosu 5. ölçütü ✅ derken rubrik satırı "eksik", pgvector satırı "henüz kullanılmıyor" diyor | `app/docs/sartname-kod-eslesme.md:191` (✅) ↔ `:316` *"§5.7'nin 5. ölçütü eksik"* ve `:317` *"⚠️ pgvector henüz kullanılmıyor"*; oysa `git log` → `4739f57`, `e16f320` (§5.7) ve `8c3066e` (pgvector) | — |
| T-054 | Dokümantasyon | yapılmamış | orta | `.env.example`'daki "Trendyol BLOKELİ" notunu düzelt — `docker-compose.yml` o modeli başlatıyor ve lisans zinciri doğrulandı | `app/.env.example:26` *"Trendyol-LLM-8B-T1 BLOKELİ — taban model zinciri doğrulanana dek kullanılmaz"* ↔ `app/docker-compose.yml:127,130` *"license: Apache-2.0; zincir Qwen3-8B-Base -> … -> Trendyol-LLM-8B-T1"* + `--model Trendyol/Trendyol-LLM-8B-T1` | — |
| T-055 | Dokümantasyon | yapılmamış | yüksek | `log.md`'deki boşluğu kapat — son girdi **27 Temmuz**, git'te 31 Temmuz tarihli 25+ commit var; vault kuralı "her ingest sonrası log" | `grep -n "^## \[" log.md` → en yeni girdi `## [2026-07-27]`; `git log --format="%ad" --date=short -12` → hepsi `2026-07-31`; `CLAUDE.md:108` ingest adım 8 | — |
| T-056 | Dokümantasyon | yapılmamış | yüksek | Kod tarafında bulunan gerçek hataları `sorun/` klasörüne taşı — 4 `sorun/` sayfası var, hepsi şartnameden türetilmiş; kodda bulunan 10+ hata (Türkçe küçük-harf, bs4 sapması, alt-dize eşleşmesi, N+1 sorgu, NUL baytları, span kaybı…) arşivde yok | `ls sorun/` → 4 dosya, tümü `status: stable` ve şartname kaynaklı; `app/docs/rapor/anatolia-ai-teknik-rapor.md:1169` *"Kodda bulunan gerçek hataların **hiçbiri** `sorun/` klasörüne girmemiş"* | T-055 |
| T-057 | Dokümantasyon | yapılmamış | orta | `index.md`'yi güncelle — `app/docs/` altındaki 7 doküman + `app/docs/rapor/` hiç listelenmiyor, dolayısıyla "0 orphan" iddiası eksik veriyle kurulmuş | `index.md:4` *"Son güncelleme: 2026-06-16"*; `lint-report.md:8` *"Lint Raporu — 2026-06-16"*, `:19` "Orphan … 0"; `ls app/docs/*.md` → 6 doküman + rapor klasörü | T-055 |
| T-058 | Dokümantasyon | yapılmamış | orta | `AGENTS.md`'yi ya commit et ya sil — `CLAUDE.md` ile **tek satır** dışında birebir aynı, hangisinin bağlayıcı olduğu belirsiz ve takip edilmiyor. Ayrıca teknik raporun bu maddeyi anlatan satırı **yanlış**: "farklı içerik" diyor, oysa fark tek satır | `diff CLAUDE.md AGENTS.md` → `+0 added, -0 removed, ~1 modified` (yalnız `52` satırındaki kendi dosya adı); `git status` → `?? AGENTS.md`; hatalı iddia: `app/docs/rapor/anatolia-ai-teknik-rapor.md:1170` *"ikisi de 5.8K, **farklı içerik**"* | — |
| T-059 | Dokümantasyon | yapılmamış | orta | `app/README.md`'deki banka sayısını düzelt: "8 katılım bankası" diyor, eşleşme tablosu ve `banks.yaml` 10 diyor | `app/README.md:87` *"849 gerçek belge, 8 katılım bankasından"* ↔ `app/docs/sartname-kod-eslesme.md:26` *"10 banka"* ve `:32` *"849 belge, 10 banka"* | T-052 |
| T-060 | Dokümantasyon | yapılmamış | düşük | Bayat `eval/reports/violations-son.jsonl` artefaktını temizle veya "bayat" olarak damgala — 15 ihlal içeriyor, dokümanlar "0 ihlal" diyor | `app/docs/rapor/olcumler.md:146` *"Dosya `violations-son.jsonl` 15 · P3 15 · ⚠️ **bayat ara artefakt**"*; `ls app/eval/reports/` → dosya duruyor (16,9 KB) | — |
| T-061 | Dokümantasyon | yapılmamış | düşük | Değişmez denetimi kapsamını tek sayıya indir: `OFFLINE-KANIT.md` "732/849 · %86,2" derken bugünkü ölçüm 726/849 · %85,5 | `app/docs/rapor/olcumler.md:162` *"⚠️ **Doküman sapması:** … '732/849, %86,2' diyor; bugün ölçülen …"* | T-052 |
| T-062 | Dokümantasyon | yapılmamış | orta | Korpus büyüklüğünün üç farklı sayısını (291 / 849 / 1.696) açıkla — hangi dilim ne, hiçbir belge bağı kurmuyor | `app/docs/rapor/anatolia-ai-teknik-rapor.md:1167` *"Korpus büyüklüğü üç farklı sayı … hiçbir belge ilişkiyi açıklamıyor"*; `git log` `eb67e65` (291) · `f4423ae` (849) | T-052 |
| T-063 | Dokümantasyon | yapılmamış | düşük | Alan sayısını netleştir: çıkarım şeması 12, şartname tablosu 13 (kampanya türü ayrı) — iki README farklı sayı yazıyor | `app/README.md:89` *"şartnamenin **12/12** alanı"* ↔ `app/docs/sartname-kod-eslesme.md:75` *"dört grupta 13 alan sayıyor. **13/13**"* | T-052 |
| T-064 | Dokümantasyon | yarım | orta | Demo video süresi çelişkisini kapat — şartname içi çelişki hâlâ açık; `syntheses/teslim-ve-degerlendirme-rehberi.md` `status: celiskili` | Şartname §6 s.14 "maksimum 5 dakikalık" ↔ §10 s.19 "demo videosu süresi ise 1 dakika"; `grep -H "^status:" syntheses/*.md` → `teslim-ve-degerlendirme-rehberi.md:6:status: celiskili`; `lint-report.md:23-26` | T-002, T-003 |
| T-065 | Dokümantasyon | doğrulanmamış | yüksek | Şartname §6 "Proje Dokümantasyonu" 10 alt maddesinin **her birinin** karşılığını commit edilmiş bir belgede işaretle — içerik teknik raporda var ama rapor depoda değil | Şartname §6 s.14, 10 alt madde (sistem mimarisi, veri akışı, NLP yaklaşımı, veri seti, ön işleme, model/kural yapısı, karşılaştırma yöntemi, adım adım talimatlar, karşılaşılan problemler, çıktı örnekleri, değerlendirme yöntemleri); `git status -uall` → `?? app/docs/rapor/anatolia-ai-teknik-rapor.md` | T-006 |
| T-066 | CI-Dağıtım | yarım | orta | `app/pyproject.toml`'daki commit edilmemiş değişikliği commit et — `docs/rapor/*` için ruff `T20` muafiyeti; bu olmadan rapor betikleri ruff kapısını kırar | `git status --short` → ` M app/pyproject.toml`; `git diff app/pyproject.toml` → `+"docs/rapor/*" = ["T20"]` (3 satır) | T-006 |

### F. Veri toplama / kalan

| Task No | Konu | Durum | Önem | İçerik | Kanıt | Bağımlılık |
|---|---|---|---|---|---|---|
| T-067 | Veri toplama | yarım | düşük | `app/data/processed/` neredeyse boş (1 dosya) — ya hattı işlet ya klasörü mimariden düş | `find app/data/processed -type f | wc -l` → **1**; `app/CLAUDE.md:154` `data/processed/ # temizlenmiş metin` | — |
| T-068 | Dashboard | yapılmamış | düşük | Kullanılmayan iki API ucunu (`/health`, `/banks`) ya arayüze bağla ya kaldır — `/banks` yarım kalmış banka filtresi izlenimi veriyor | `app/src/api/main.py:340` `/health`, `:351` `/banks`; `app/web/app/lib/api.ts:229-256` 11 uçtan 9'unu tüketiyor, bu ikisini kullanmıyor | — |

> T-069…T-074 numaraları D bölümünde (test/CI kalemleriyle birlikte) yer alıyor.
> Toplam **74 madde**, numaralar T-001…T-074 arası kesintisizdir.
>
> **T-074 2026-08-16'da eklendi:** şartnamenin 7 sütunlu kıyas tablosu satırı
> "✅ üretilebiliyor" işaretliydi; ölçüm bunu çürüttü (`/compare` tek alanlı,
> «Kampanya Avantajı» alanı hiç yok). Satır ❌ + "karar bekliyor"a taşındı.

---

## Kritik maddeler — ayrıntı

Yalnızca `kritik` ve `yüksek` maddeler. Her biri için: neden önemli, nasıl doğrulanır.

### T-010 · Anotasyon hiç başlamadı (kritik)

Rubriğin en ağır maddesi Model Başarısı %30 ve bu maddenin **tek** girdisi insan
etiketli gold settir. Anotasyon hattının tamamı hazır (`preannotations.json` 2,5 MB,
8 CSV, 3.406 satırlık kılavuz + şema kodu) ama **doldurulmuş satır sayısı 0**. Bu
zincir seridir: anotasyon → IAA → gold dondurma → metrik → ablasyon → sunum. Bir gün
gecikme zincirin tamamını kaydırır ve 23 günde sığmaz.
**Doğrulama:** `csv.DictReader` ile 8 CSV'de `verdict` veya `gold_value` dolu satır
sayısı; şu an `0/3.422`. Hedef: kalibrasyon turu için ≥1.040 satır (4×260).

### T-072 · Ön-anotasyon LLM kapalıyken üretildi (yüksek) — T-010'un ön koşulu

`preannotations.json` üstbilgisi `llm_available=False` ve `disagreement_count=0`
diyor. Yani 250 belgelik ön-anotasyonu **yalnızca kural katmanı** üretti ve
anotatör CSV'lerindeki `disagreement` kolonu tamamen boş. Bu kolonun amacı
anotatörün dikkatini katmanların çeliştiği yerlere çekmekti; şu haliyle
anotatörler 3.422 satırı **eşit dikkatle** taramak zorunda kalacak, bu da
T-010'un süresini uzatır ve zor vakaların kaçırılma riskini artırır. Ayrıca
LLM kolunun katkısı (T-018) ön-anotasyon aşamasında da ölçülemez hale gelmiş.
**Doğrulama:** `python3 -m scripts.preannotate --limit 250 --seed 42` LLM açıkken
koşulduğunda `llm_available=True` ve `disagreement_count > 0` olması; CSV'lerde
işaretli satır bulunması.

### T-011 · Kalibrasyon turu ve IAA (kritik)

`_atama.md:22` bu adımın atlanmasının sonucunu açıkça yazıyor: "ana turdaki
uyuşmazlıkların yarısı kılavuz belirsizliğinden çıkar ve gold yeniden yapılır".
Yani atlanırsa T-010 ikinci kez yapılır — 23 günde bu telafi edilemez. Ayrıca
`app/CLAUDE.md:272` Cohen's kappa'yı raporlanacak metrikler arasında sayıyor.
**Doğrulama:** `python3 -m scripts.report_iaa …` çıktısında κ değeri; eşik 0,67.

### T-012 · Gold üretimi ve TEST bölmesinin dondurulması (kritik)

Projenin en güçlü bilimsel iddiası "kural katmanı gold'a bakılmadan yazıldı, bu
yüzden gerçek held-out" (`app/README.md:95-97`). Bu iddia ancak TEST bölmesi
**dondurulup sha256'lanırsa** ayakta durur. Şu an `data/gold/` altında yalnız
3 kayıtlı `gold.sample.json` var; `split_gold.py:279` çalıştırıldığında "Bölme henüz
üretilmemiş" diyor.
**Doğrulama:** `split_gold.py` çıktısında dev/test sayıları + TEST bölmesinin sha256
özeti ve erişim kayıt dosyası.

### T-013 · P/R/F1 üretilmedi — `metrics.json` yok (kritik)

`app/eval/` altında 8 modül, ~3.400 satır ölçüm kodu var; `app/eval/reports/`
içinde ise yalnız değişmez ihlali JSONL'leri var, **hiç metrik çıktısı yok**.
Jüri "modeliniz ne kadar başarılı" diye soruyor; "ölçüm altyapımız iyi" cevabı
%30'u karşılamaz — projenin kendi raporu da bunu yazıyor
(`anatolia-ai-teknik-rapor.md:1260` "Elimizde … kusursuz bir ölçüm hattı ve **hiç
sayı** var").
**Doğrulama:** `python3 -m eval.run_eval --gold data/gold/<dondurulmus>` çıktısında
alan bazında P/R/F1 + bootstrap %95 GA; dosya olarak diske yazılmış olması.

### T-014 · Ablasyon koşulmadı (kritik)

`app/CLAUDE.md:276` ablasyon tablosunu "jüri için en ikna edici tek artefakt" ilan
ediyor. Şu an hibridin kural-only'yi geçtiği **iddia**, ölçüm değil — ve dahası
LLM katmanı korpusa bugüne dek 0 alan katmış (T-018). Ablasyon negatif çıkarsa
bu da raporlanabilir bir sonuçtur, ama koşulmadığı sürece mimarinin ana tezi
kanıtsızdır.
**Doğrulama:** `python3 -m eval.ablation` çıktısı + McNemar p değeri; en az
kural-only ve hibrit kolu.

### T-001 · Veri seti indirme bağlantısı (kritik)

Şartname §9 (s.18) bunu üç zorunlu depo içeriğinden biri sayıyor ve aynı bölüm
"Yukarıda belirtilen tarihte proje dosyası yüklenmediği takdirde projeler
değerlendirmeye alınmayacaktır" diyor. `README.md:117` şu an yer tutucu.
**Doğrulama:** Yayımlanmış URL'ye anonim (giriş yapmamış) bir istemciden erişim +
README'de o URL'nin bulunması.

### T-002 / T-003 · Demo videoları (kritik)

Şartname iki ayrı yerde iki ayrı süre veriyor (§6 s.14 "maksimum 5 dakika", §10
s.19 "demo videosu süresi ise 1 dakika") ve ayrım yapmıyor. §10 aynı zamanda
demo gösterimini **zorunlu** kılıyor ve videoyu "aksaklık yaşanmaması adına"
yedek olarak istiyor. Depoda hiç video yok.
**Doğrulama:** İki dosyanın varlığı + süreleri; içerikte §6'nın saydığı 6 öğenin
(arayüz, dashboard, chatbot, metin girdisi, yapılandırılmış çıktı, karşılaştırma)
görünmesi.

### T-004 · Sunum PDF + PPTX (kritik)

§6 s.14 formatı açıkça "PDF ve PPTX" diye yazıyor; depoda `.pptx` hiç yok.
Sunumda ayrıca §8 s.17 gereği her üyenin görev tanımı olmalı (T-008).
**Doğrulama:** `find . -iname "*.pptx"` sonucu boş olmamalı; PDF ile PPTX içerik
paritesi.

### T-006 · Teknik rapor commit edilmemiş (kritik)

77 KB markdown + 8,7 MB PDF + 11 ekran görüntüsü + 12 SVG grafik hazır, ama
`git status` hepsini `??` (takip edilmiyor) gösteriyor. Jürinin gördüğü şey GitHub
deposudur; commit edilmemiş belge **yok** sayılır. Ayrıca bu rapor §6'nın
dokümantasyon alt maddelerinin çoğunun tek karşılığı (T-065).
**Doğrulama:** `git ls-files app/docs/rapor/ | wc -l` > 0 ve remote'a push.

### T-037 · `demo.db` depoda yok → jüri 3 belge görür (kritik)

`app/.gitignore:9` `*.db` kuralı `data/demo.db`'yi dışlıyor; `Dockerfile.api`
`COPY data/` ile onu imaja almayı bekliyor. Sonuç: temiz klon → `docker compose up`
→ API fixture'lardan tohumlar ve `/campaigns` **3** kampanya döner. Yani jüri
849 belgelik korpusu değil, 3 belgelik bir demoyu görür. Bu tek başına
Fonksiyonellik %20'yi ve demonun ikna gücünü çökertir.
**Doğrulama:** Temiz bir klonda `docker compose up` sonrası
`curl -s localhost:8000/campaigns | …` sayısının 849 olması.

### T-038 · `build_demo_db` kurulum adımlarında yok (kritik)

Şartname §6 s.13 "kurulum adımları … net bir şekilde belirtilmelidir" diyor.
`build_demo_db` iki README'de hiç geçmiyor; yalnız commit edilmemiş raporda ve
`veri-katmani.md`'de var. T-037'nin dokümantasyon yarısı budur.
**Doğrulama:** README'deki adımları sıfırdan izleyen biri 849 belgeye ulaşmalı.

### T-005 · Veri seti lisansı (yüksek)

§8 s.17 kod **ve veri kümeleri** için açık lisans zorunlu kılıyor. Kodda
Apache-2.0 var (`LICENSE`), veri setinde lisans beyanı yok.
**Doğrulama:** Veri seti yayın yerinde lisans dosyası/alanı + README'de beyan.

### T-007 · Haftalık güncelleme borcu (yüksek)

§9 s.18 "en az haftalık olarak" güncelleme zorunlu. Son commit 31 Temmuz, bugün
3 Ağustos; `hafta-01` etiketi de 31 Temmuz'da. Henüz ihlal değil ama tampon bitti.
**Doğrulama:** `git tag -l` içinde `hafta-02` ve tarihinin 7 günü aşmaması.

### T-008 · Takım tanıtım sunumu (yüksek)

§8 s.16 bunu ayrı ve **zorunlu** bir kalem olarak sayıyor; §8 s.17 her üyenin
görev tanımını istiyor. `README.md:19-24` yalnız "Takım Kaptanı / Ekip Üyesi"
yazıyor; depoda sunum yok. Bu bir puanlama kalemi değil, **kabul** kalemi olabilir.
**Doğrulama:** Sunum dosyasının varlığı + 4 üyenin proje kapsamındaki görevinin
yazılı olması.

### T-015 · Zor-vaka alt kümesi (yüksek)

`app/CLAUDE.md:113-114` bunu doğrudan "%30 burada kazanılır" diye işaretliyor:
hibridin özellikle zor vakalarda kazandığını göstermek. Alt küme kürlenmedikçe
ablasyonun en güçlü hikâyesi anlatılamaz.
**Doğrulama:** Gold set içinde `hard=true` etiketli ≥30 gerçek (sentetik değil)
kayıt + o alt küme için ayrı P/R/F1.

### T-016 · Halüsinasyon oranı (yüksek)

Şartnamenin %30 kriterinin üçüncü alt maddesi "eksik veya farklı yazılmış bilgiler
karşısında doğru sonuç üretebilmesi". `app/CLAUDE.md:68` halüsinasyonu "en büyük
risk" ilan ediyor. `absent_fields` ayrımı kodda var, sayı yok.
**Doğrulama:** Gold'da alanın **yok** olduğu vakalarda modelin değer üretme oranı.

### T-017 · Güven skoru kalibrasyonu — dosya yok (yüksek)

`app/src/extraction/rules/confidence.py:32-35` açıkça `eval/calibration.py`'de
sıcaklık ölçekleme yapılacağını yazıyor; o dosya **hiç yazılmamış**. Yani
arayüzde ve API'de gösterilen güven skorları sıralayıcıdır, olasılık değildir —
jüri "0,87 güven" görürse bunu olasılık sanar.
**Doğrulama:** `app/eval/calibration.py` var olması + ECE ve reliability diagram
çıktısı; ya da kalibre olmadığının arayüzde açıkça yazılması.

### T-018 · LLM katmanının katkısı sıfır (yüksek)

Mimarinin adı "Önce Kural, Sonra LLM" ama ölçülen 2.204 alanın 2.204'ü kuraldan
geldi. Bu, LLM katmanının ya gereksiz ya hiç çalışmamış olduğu anlamına gelir;
ikisi de mimari iddiayı zayıflatır ve T-021 (zaman-koşullu ifadeler) tam olarak
LLM'in işi.
**Doğrulama:** `LLM_BACKEND=vllm` ile bir koşuda `extractor='llm'` etiketli alan
sayısı > 0.

### T-019 · Navigasyon metni kaynak span'inde (yüksek)

Projenin yenilikçilik iddialarından biri "kaynak-span izlenebilirliği". Span
kanıt olarak sunuluyor ama içinde `"Navigasyonu görüntüle İçeriği görüntüle…"`
gibi site menüsü var. Jüri bunu görürse tüm span mekanizmasına güveni düşer —
%10 yenilikçiliği ve %30'u aynı anda vurur.
**Doğrulama:** Korpus üzerinde span metinlerinde navigasyon kalıbı arayan bir
tarama; 0 sonuç.

### T-020 · Bağlamsız `%0` oranlar sıralamada birinci (yüksek)

"En düşük kâr payı oranı" §5.7'nin ilk ölçütü. Bir alışveriş indirimi bağlamındaki
`%0` ifadesi finansman kâr payı sanılıp birinci sıraya çıkıyorsa karşılaştırma
çıktısı yanlıştır — Fonksiyonellik %20'nin "çıktıların doğru olması" alt maddesi.
**Doğrulama:** `/compare` çıktısının ilk 10 satırının elle denetimi + bir regresyon
testi.

### T-021 · Zaman-koşullu ifadeler çıkarılmıyor (yüksek)

`app/CLAUDE.md:106-112` "zor anlama vakaları"nı sayarken "ilk 6 ay %0"ı ilk
sıraya koyuyor ve bunu mimarinin merkezi ilan ediyor. Şu an bu vaka
yakalanmıyor çünkü LLM kapalı.
**Doğrulama:** `gold.sample.json`'daki ikinci kayıt tipi ("ilk 6 ay masrafsız")
için doğru alan üretimi + gold'da bu tür vakalarda recall.

### T-023 · Kâr payı kapsamı %5,5 (yüksek)

§5.7'nin beş ölçütünden dördü sayısal alanlara dayanıyor; 495 skorlanabilir
kampanyanın yalnız %9,5'inde kâr payı oranı var (Kart'ta 114'ün 3'ü, Alışveriş
Puanı'nda 13'ün 0'ı). Bu, karşılaştırma özelliğinin gerçek kapsamını belirler ve
şu an arayüzde görünmüyor — jüri "en düşük kâr payı" sıralamasının 10 kampanyaya
dayandığını fark ederse iddianın altı boşalır.
**Doğrulama:** `/compare` ve `/scoring` çıktılarında `coverage` alanının arayüzde
gösterilmesi + kapsam yüzdesinin raporlanması.

### T-024 · Sessiz LLM hatası (yüksek)

`app/src/chatbot/rag.py:380` `except Exception: pass` — LLM cevabı üretilemezse
hiçbir iz bırakmadan fallback'e düşüyor. Demo sırasında LLM'in çalışıp
çalışmadığı görünmez; T-018'in ölçülememesinin muhtemel sebeplerinden biri de bu.
**Doğrulama:** Kasıtlı bozuk LLM yapılandırmasıyla koşuda log/telemetride hata
kaydının görünmesi.

### T-039 / T-040 / T-041 · On-prem kanıtının üç boşluğu (yüksek)

On-Prem %20'nin mevcut kanıtı güçlü (`--network none` içinde 607 test + negatif
kontrol + digest pin) ama **yalnız API konteynerini** kapsıyor. Postgres + web
birlikte ağsız ayağa kalkmadı, pgvector ağsız denenmedi ve tüm ölçümler **arm64**
host'ta yapıldı. Jüri makinesi amd64 ise "çalışıyor" iddiası doğrulanmamış olur.
**Doğrulama:** `docker compose --profile postgres up` çıktısı ağsız modda +
`docker inspect` ile amd64 platform kaydı + transkriptin `app/docs/offline-proof/`
altına yazılması.

### T-044 · vLLM / Ollama koşusu hiç yapılmadı (yüksek)

`docker-compose.yml` vLLM ve Ollama servislerini tanımlıyor, `model-license-audit.md`
Trendyol zincirini doğruluyor, ama hiçbiri bir kez bile ayağa kalkmadı. Bu; T-014
(ablasyon), T-018 (LLM katkısı), T-021 (zaman-koşullu), T-042 (ağırlık SHA-256)
maddelerinin **hepsinin** ön koşulu.
**Doğrulama:** `docker compose --profile ollama up` sonrası bir çıkarım isteğinin
`extractor='llm'` alan döndürmesi.

### T-046 · 53 test hiçbir ortamda koşmuyor (yüksek)

Sistem `python3` ile `OK (skipped=62)`, `.venv` ile `OK (skipped=53)`. Aradaki
9 fark `fastapi` yokluğundan; kalan **53 atlamanın tamamı tek nedenden**:
`ANATOLIA_TEST_DATABASE_URL` tanımlı değil. Atlananlar tam olarak en riskli
katmanlar: `test_pgvector_repository` (26), `test_api_backend` (14),
`test_repo_parity` (13) — yani `db/postgres.py`, `db/factory.py`, `rag/store.py`
gerçek pgvector davranışı **hiç doğrulanmıyor**. CI bunları koşmuyor çünkü
`ci.yml:45-48` bilinçli olarak üçüncü parti paket kurmuyor. Bu tercih on-prem
iddiası için doğru ama **ek** bir işle telafi edilmeli, yoksa "890 test yeşil"
ifadesi 837 testi anlatır.
**Doğrulama:** CI'da `services: postgres` olan ikinci bir işin çıktısında
`skipped=0` (veya belirgin biçimde daha az).

### T-047 · Frontend tamamen test edilmemiş (yüksek)

2.595 satır TSX/TS/CSS, 10 bileşen, 11 API ucu tüketimi — tek test yok, `test`
script'i de yok. Demo tamamen bu arayüz üzerinden yapılacak; T-036 (markdown
render) ve T-019 (span sızması) gibi hatalar bu boşluğun doğrudan sonucudur.
**Doğrulama:** `npm test` komutunun var olması ve en az `ComparePanel`,
`ChatPanel`, `ExtractLive` için render + hata durumu testleri.

### T-052 · Test sayısı altı yerde farklı (yüksek)

54 / 129 / 345 / 607 / 695 / 835 — gerçek 890. Bu tek başına küçük bir hata ama
jüri açısından sonucu büyük: bir sayı altı yerde farklıysa diğer sayılara (849
belge, 0 ihlal, p99 gecikme) da güvenilmez. Düzeltme maliyeti düşük, etkisi
yüksek.
**Doğrulama:** `grep -rn "345\|607\|695\|835" --include="*.md"` sonucunun test
sayısı bağlamında boş dönmesi.

### T-053 · `sartname-kod-eslesme.md` kendisiyle çelişiyor (yüksek)

Bu belge jürinin şartname maddelerini kod karşılığıyla eşleştirdiği ana denetim
aracı ve kendi içinde çelişiyor: §5.7 tablosu 5. ölçütü ✅ derken rubrik satırı
"eksik", pgvector satırı "henüz kullanılmıyor" diyor — oysa ikisi de 31 Temmuz'da
tamamlandı. Belgenin başlığında "Son güncelleme: 2026-07-31 · Test sayısı: 695"
yazıyor, yani rubrik bölümü o gün içinde bayatladı.
**Doğrulama:** Belgenin tek bir tarih ve tek bir test sayısıyla, iç çelişki
olmadan okunması.

### T-055 · `log.md` boşluğu vault kuralını ihlal ediyor (yüksek)

`CLAUDE.md:108` her ingest sonrası log girdisi zorunlu kılıyor ve `CLAUDE.md:139`
"kaynaksız iddia yasak" diyor. `log.md`'nin son girdisi 27 Temmuz; git'te 31
Temmuz tarihli 25+ commit var (pgvector, §5.7, ruff kapısı, Postgres deposu).
Yani bilgi arşivi kod tarafındaki son bir haftayı hiç bilmiyor.
**Doğrulama:** `log.md`'de `## [2026-07-31]` ve `## [2026-08-03]` girdilerinin
bulunması; `git log` ile karşılaştırıldığında kapatılmamış gün kalmaması.

### T-056 · Kodda bulunan hatalar `sorun/` klasörüne girmemiş (yüksek)

`sorun/` altındaki 4 sayfa da şartnameden türetilmiş soyut problemler. Gerçekten
bulunan ve düzeltilen 10+ hata (Türkçe `str.lower()`, alt-dize eşleşmesi korpusun
%48'ini bozması, teslim imajında `bs4` eksikliği, N+1 vade sorgusu, NUL baytları,
span offsetlerinin DB sınırında kaybolması) yalnız `log.md` ve `app/docs/` içinde.
Vault'un varlık nedeni tam olarak bu öğrenmeyi kalıcılaştırmaktı.
**Doğrulama:** `ls sorun/` içinde kök neden + çözüm + ilgili dosya taşıyan en az
8 yeni sayfa ve `index.md`'de listelenmeleri.

### T-057 · `index.md` ve `lint-report.md` 2026-06-16'dan beri güncellenmedi (yüksek)

`lint-report.md` "0 orphan" diyor ama `app/docs/` altındaki 6 doküman + rapor
klasörü graf'a hiç dahil edilmemiş. Yani lint'in gördüğü graf gerçek graf değil;
"0 orphan" eksik veriyle kurulmuş bir iddia.
**Doğrulama:** `index.md` içinde `app/docs/` belgelerinin listelenmesi ve lint'in
yeniden koşulması.

### T-059 · Banka sayısı 8 mi 10 mu (yüksek)

`app/README.md:87` "8 katılım bankasından", eşleşme tablosu ve `config/banks.yaml`
10 banka diyor. §5.1 "BDDK listesindeki kuruluşların **tümünü** içermelidir"
dediği için bu sayı doğrudan bir uyum iddiası — eksik yazmak kendi ayağına
kurşundur.
**Doğrulama:** `banks.yaml` içindeki banka sayısı ile korpusta belgesi olan banka
sayısının ayrı ayrı, açıkça yazılması.

### T-065 · §6 dokümantasyon alt maddeleri commit edilmiş bir belgede yok (yüksek)

§6 s.14, dokümantasyon için 10 alt madde sayıyor (mimari, veri akışı, NLP
yaklaşımı, veri seti açıklaması, ön işleme, model/kural yapısı, karşılaştırma
yöntemi, adım adım talimatlar, karşılaşılan problemler, çıktı örnekleri,
değerlendirme yöntemleri). İçeriğin çoğu teknik raporda var ama rapor
takip edilmiyor (T-006). Depoda görünen belgeler bu 10 maddeyi tek tek
işaretlemiyor.
**Doğrulama:** Commit edilmiş bir belgede 10 alt maddenin her biri için bölüm
başlığı veya çapraz referans.

---

## Şartname karşılama matrisi

Sayfa numaraları `pdftotext -layout` ile çıkarılan basılı sayfa işaretlerine göredir
(`2026_TEKNOFEST_TYDA_SARTNAME_Ikinci_Senaryo_TR_1_SmsXO.pdf`, 25 sayfa).

### §5 Temel Beklentiler

| Gereklilik | Şartname referansı | Projedeki karşılığı (dosya) | Durum |
|---|---|---|---|
| §5.1 BDDK listesindeki katılım bankalarının **tümünden** veri toplama, Python/scraping veya manuel | s.6 | `app/config/banks.yaml` (10 banka), `app/src/scraping/{collector,discover,fetcher,harvest,harvest_products,robots}.py`, `app/data/raw/` (2.557 dosya) | ✅ karşılanıyor · ⚠️ dağılım dengesiz (Adil 6 belge), banka sayısı dokümanlar arası çelişkili (T-059) |
| §5.2 Farklı ifade biçimlerini yorumlama (`"%2,05 kâr payı oranı"` · `"avantajlı kâr payı fırsatı"` · `"özel oranlı finansman"` · `"düşük maliyetli finansman"`) | s.6 | `app/src/extraction/rules/extract.py` (`extract_kar_payi`, iki yönlü), `rules/synonyms.py` (`qualitative_rate_claim`), `app/tests/test_kar_payi_yon.py`, `test_sartname_terminoloji.py` | ✅ 4/4 tanınıyor · ⏳ doğruluğu ölçülmedi (T-013) |
| §5.3 Finansal bilgi çıkarımı + **yapılandırılmış** formata dönüştürme (13 alan, 4 grup) | s.7 | `app/src/extraction/rules/extract.py` (13 çıkarıcı), `app/src/schemas.py` (`ExtractedField`) | ✅ 13/13 alan üretiliyor · ⏳ P/R/F1 yok (T-013); alan sayısı 12 mi 13 mü belirsiz (T-063) |
| §5.4 Kampanya türünün belirlenmesi (8 tür) | s.8 | `app/src/extraction/ner/classifier.py` (`RuleHintClassifier` + `BerturkClassifier`) | ✅ 8/8 tür üretiliyor · ⚠️ 60 belge (%7,1) sınıflanamıyor (T-022) · ⏳ makro-F1 yok (T-013) |
| §5.5 Katılım bankacılığı terminolojisi (Kâr Payı Oranı · Finansman Maliyeti · Katılım Fonu · Masrafsız Finansman · Avantajlı Finansman) | s.8 | `app/src/extraction/rules/synonyms.py` (`TERMINOLOGY_5_5`, `terminology_hits`), `app/src/chatbot/safety.py` (terminoloji kapısı) | ✅ 5/5 kavram kural katmanında; chatbot kapısı 30/30 · ⚠️ güvenlik seti tek anotatörlü (T-035) |
| §5.6 Standart formata dönüştürme (`%2,05` = `% 2.05` = `2.05 %`; `500 TL` = `500₺` = `500 Türk Lirası`) | s.9 | `app/src/normalization/normalize.py` (`normalize_rate/money/term/date`, `parse_tr_number`, `normalize_fee_status`, `collapse_degenerate_range`), `app/src/preprocessing/clean.py` (`tr_fold`) | ✅ karşılanıyor · ⏳ normalizasyon doğruluk oranı gold'da ölçülmedi (T-013) |
| §5.7 Ürünlerin karşılaştırılması (5 ölçüt: En Düşük Kâr Payı · En Yüksek Ödül · En Uzun Vade · En Düşük Masraf · En Avantajlı Kampanya) | s.9 | `app/src/comparison/compare.py` (`rank`, `rank_advantageous_by_type`, `weight_manifest`), `app/web/app/components/ComparePanel.tsx` | ✅ 5/5 ölçüt uygulandı · ⚠️ kâr payı kapsamı %5,5 (T-023) · ❌ bağlamsız `%0` sıralamayı bozuyor (T-020) |
| §5.8 Veri ön işleme süreçleri | s.10 | `app/src/preprocessing/clean.py` (`strip_html`, `normalize_text`, `split_sentences`, `tr_fold`, `tr_upper`) | ✅ karşılanıyor · ❌ menü/navigasyon metni span'e sızıyor (T-019) |
| §5.9 On-Premise: kurum içi sunucu · veri güvenliği · veri kurum dışına çıkmaması · dış servise bağımsızlık | s.10 | `app/docker-compose.yml`, `app/Dockerfile.api`, `app/scripts/offline_proof.sh`, `app/docs/OFFLINE-KANIT.md`, `app/docs/offline-proof/` (4 transkript + 5 gecikme JSON'u) | ✅ API konteyneri için **ölçüldü** (`--network none`, negatif + pozitif kontrol, digest pin) · ⏳ tam yığın (T-039), pgvector ağsız (T-040), amd64 (T-041) doğrulanmadı |
| §5.10 Açık kaynak yaklaşımı; lisans problemi çıkarabilecek çözüm kullanılmaması; modellerin ölçeklenebilir konumlandırılması | s.11 | `LICENSE` (Apache-2.0), `app/docs/model-license-audit.md` (`base_model` zinciri köke kadar), iki kademe: Trendyol-8B/Qwen3-8B + Qwen3-4B GGUF | ✅ zincir denetimi yapıldı · ⏳ `trafilatura` GPL riski açık (T-045); denetim listesinde 2 madde işaretsiz (T-051) |

### Örnek Temsili Senaryolar

| Gereklilik | Şartname referansı | Projedeki karşılığı (dosya) | Durum |
|---|---|---|---|
| Senaryo-1: A/B/C Bankası konut finansmanı → **7 sütunlu** karşılaştırma tablosu (Banka · Ürün Türü · Kâr Payı Oranı · Vade · Kampanya Avantajı · Masraf Durumu · Kampanya Süresi) | s.11–12 | `app/src/comparison/compare.py` + `app/web/app/components/ComparePanel.tsx`; ekran görüntüsü `app/docs/rapor/gorseller/01-karsilastirma.png` | ✅ **ÜRETİLİYOR — `GET /urun-tablosu` + Karşılaştırma sekmesi görünüm anahtarı (T-074, ölçüldü 2026-08-16)**. Ayrıntı ve ölçüm aşağıda. ⚠️ kanıt görüntüsü commit edilmemiş (T-006) |
| Senaryo-2 / durum 1: tek bankaya ait bilgi sorma ("A Bankası'nın konut finansmanı oranı ne?") | s.13 | `app/src/chatbot/{router,structured}.py`; görüntü `gorseller/07-chatbot-yapisal-sorgu.png` | ✅ yapısal sorgu yolu · ⚠️ ürün düzeyi filtre yok (T-033) |
| Senaryo-2 / durum 2: iki bankayı karşılaştırma, gerekçeli madde madde cevap | s.13 | `app/src/chatbot/bot.py` + `comparison/compare.py`; görüntü `gorseller/08-chatbot-rag.png` | ✅ çalışıyor · ❌ arayüzde markdown render edilmiyor (T-036) |

> ### ⛔ DÜZELTME (2026-08-16) — bu satır "✅ üretilebiliyor" diyordu, ölçüm ÇÜRÜTTÜ
>
> **Eski hâli:** *"6 kolonlu karşılaştırma tablosu (…) · ✅ üretilebiliyor (tür içi sıralama)"*.
> HARD RULE 3 gereği satır silinmedi, durumu gerçeğe taşındı. İki ayrı hata vardı:
>
> **Hata 1 — kendi içinde tutarsız:** "6 kolonlu" diyor ama parantezde **7 sütun** sayıyor.
> Şartnamedeki tablo 7 sütunludur (aşağıdaki alıntıya bakınız).
>
> **Hata 2 — asıl iddia yanlış:** şartname **banka başına TEK satır, ÇOK alanlı** bir tablo
> istiyor; bizim `/compare` ucumuz **tek alanlı**dır. Bu bir sunum eksiği değil, **farklı bir
> veri şekli**.
>
> #### Ölçüm — nasıl doğrulandı
>
> ① **Şartname tarafı** (`raw/teknofest/2026-teknofest-tyda-sartname-2-senaryo.pdf`, dosya
> sayfası 13): tablo sütunları `Banka · Ürün Türü · Kâr Payı Oranı · Vade · Kampanya Avantajı ·
> Masraf Durumu · Kampanya Süresi`; A/B/C Bankası **birer satır**, her satırda yedi hücre dolu.
>
> ② **Bizim uç** — `GET /compare?field=…` **tek** `field` parametresi alır
> (`src/api/main.py:1306`). `rank()` çıktısının gerçek alanları (1.782 belgelik korpusta
> ölçüldü):
> ```
> bank · bank_name · value · sort_key · comparable · note · source_span
> campaign_id · campaign_type · other_count · campaign_status · confidence · oran_bazi
> ```
> Tek bir `value` sütunu var — seçilen alanın değeri.
>
> ③ **Arayüz** — `ComparePanel.tsx:605-612` başlıkları:
> `Sıra · Banka · Değer · Ham ifade · [Güven] · Katman · Durum · Kaynak`.
> Bileşenin kendi başlığı da bunu söylüyor: *"Karşılaştırma Paneli — bankalar arası **tek alan**
> kıyası"* (`ComparePanel.tsx:4`). Alan, açılır menüden seçiliyor.
> **7 sütunlu böyle bir satır üreten hiçbir uç ya da ekran yok.**
>
> ④ **«Kampanya Avantajı» sütununun karşılığı olan alan HİÇ YOK.** `EXTRACTION_FIELDS` 12
> alandır ve `kampanya_avantaji` içermez; ad kodda hiç geçmiyor. En yakınları `odul_miktari`,
> `indirim_orani`, `alisveris_puani`, `kampanya_kosullari` — hiçbiri şartnamedeki **serbest
> metin özeti** değil (*"50.000 TL'ye kadar masraf alınmıyor"*, *"5.000 TL alışveriş çeki"*,
> *"Ekspertiz ücreti banka tarafından karşılanıyor"*).
>
> #### Neyin VAR olduğu — iddia karartılmıyor
>
> Yapılandırılmış çok alanlı veri **var**: her kampanya için 12 alan, her biri
> `span_start`/`span_end` + `confidence` + `extractor` taşıyor. Tür içi sıralama, adil-kıyas
> kapısı ve 5/5 kıyas ölçütü (§5.7) çalışıyor. **Eksik olan iki şey:**
> 1. o alanları şartname düzeninde **banka başına tek satırda birleştiren sunum** (uç + ekran),
> 2. **«Kampanya Avantajı» serbest metin alanı** (çıkarıcı + şema + gold tanımı).
>
> #### Yapılsa bile sınır — 7 sütunun 6'sı doldurulabilir, o da seyrek
>
> Yedi sütundan altısının arkasında bir alan var; biri (Kampanya Avantajı) yok. Ama **var olanlar
> da seyrek** — 1.782 belgelik korpusta ölçülen kapsam:
>
> | şartname sütunu | karşılık gelen alan | kapsam (1.782 belge) |
> |---|---|---:|
> | Banka | `bank_name` | %100 |
> | Ürün Türü | `campaign_type` (8 tür sınıflandırma) | %92,9 (60 belge sınıflanamıyor, T-022) |
> | Kâr Payı Oranı | `kar_payi_orani` | **60 belge · %3,4** |
> | Vade | `vade_ay` | 441 belge · %24,7 |
> | **Kampanya Avantajı** | **— alan yok —** | **%0** |
> | Masraf Durumu | `masraf_durumu` | 494 belge · %27,7 |
> | Kampanya Süresi | `kampanya_suresi` | 927 belge · %52,0 |
>
> Yani 7 sütunlu görünüm bugün yapılsaydı **satırların ezici çoğunluğu büyük ölçüde boş**
> gelirdi. Bu bir sunum kusuru değil **veri gerçeği**: bankalar oranları kampanya sayfalarında
> büyük ölçüde yayımlamıyor. Şartnamenin örnek tablosu üç kurgusal bankayla yedi hücreyi de
> dolduruyor; gerçek korpus öyle davranmıyor.
>
> #### ✅ KAPANDI (2026-08-16) — T-074 inşa edildi VE ölçüldü
>
> Karar "yapılacak" oldu, yapıldı ve **bağımsız ölçüldü**. Yukarıdaki ❌ analizi
> silinmedi — üretim öncesi durumun kaydıdır ve hangi boşluğun kapandığını gösterir.
>
> **Ne geldi:** `GET /urun-tablosu` (`src/api/main.py:1548`) + Karşılaştırma
> sekmesinde görünüm anahtarı (`web/app/components/urunTablosu.ts`).
> **`/compare` HİÇ DEĞİŞMEDİ** — yeni uç onun yerine geçmiyor, yanına geliyor:
> `/compare` tek alanlı denetim yüzeyi (bir kolon, çok banka), `/urun-tablosu`
> çok alanlı şartname görünümü (bir banka, yedi kolon).
>
> **Doğruladığım ölçümler (2026-08-16):**
>
> | kontrol | sonuç |
> |---|---|
> | Sütun sayısı | `len(SARTNAME_SUTUNLARI)` = **7**, şartname s.11–12 sırasıyla birebir |
> | «Kampanya Avantajı» | **yeni çıkarım alanı EKLENMEDİ** — mevcut span'li alanlardan (`odul_miktari`, `alisveris_puani`, `indirim_orani`, ücret muafiyeti) derleniyor, her parça kendi kaynağını taşıyor |
> | Şartname üç örneği | **21 hücrenin 18'i dolu**; boş kalan üçün üçü s.12'de de "Belirtilmemiş" — yani sapma değil, birebir eşleşme |
> | Test kilidi | `tests/test_sartname_urun_tablosu.py` → **32 test, hepsi geçiyor** (`Ran 32 tests ... OK`) |
> | Gerçek korpus (1.782 belge, `data/demo.db`) | **60 satır** (banka × ürün ailesi) · 8 ürün ailesi |
>
> **Doluluk — İKİ payda var, ikisi de adlandırılmalı.** Bu, bu belgede daha önce
> düzeltilen 96/91 hatasının aynısıdır; tekrarlanmasın diye ikisi de yazılıyor:
>
> | payda | ne sayıyor | sonuç |
> |---|---|---:|
> | **ölçülen 5 sütun** | `kar_payi_orani`, `vade_ay`, `kampanya_avantaji`, `masraf_durumu`, `kampanya_suresi` — yani gerçekten çıkarıma bağlı olanlar | **157/300 = %52,3** |
> | **tüm 7 sütun** | yukarıdakiler + `Banka` + `Ürün Türü` (ikisi tanım gereği hep dolu) | **277/420 = %66,0** |
>
> "Korpusta doluluk %52" cümlesi **ölçülen 5 sütun** paydasına aittir; 7 sütunluk
> payda %66 verir. İkisi de doğrudur, karıştırılırsa değildir.
>
> `doluluk` alanı yanıtta **çalışma anında** hesaplanır, koda gömülü değildir —
> çıkarım katmanı geliştikçe kendiliğinden tazelenir.
>
> Ürün ailesi başına doluluk (tüm 7 sütun): Kart %73,0 · Yatırım Ürünü %71,4 ·
> Konut Finansmanı %69,6 · Taşıt Finansmanı %64,3 · İhtiyaç Finansmanı %63,5 ·
> Yeni Müşteri %62,9 · Finansman %58,9 · Alışveriş Puanı %52,4.
>
> Boş hücre **uydurulmuyor**: satır tek bir kampanyayı temsil ediyor, bir bankanın
> farklı kampanyalarından değer devşirip aynı satıra yazmak yasak (CLAUDE.md §21)
> ve uç bunu `fairness_note` ile açıkça beyan ediyor.

### §6 Tespit Edilmesi Gerekenler (teslimler)

| Gereklilik | Şartname referansı | Projedeki karşılığı (dosya) | Durum |
|---|---|---|---|
| Çalışan proje kodu (ön işleme + çıkarım + normalizasyon + karşılaştırma çıktısı) | s.13 | `app/src/` (54 modül), `app/src/pipeline.py`; 890 test yeşil | ✅ |
| Kurulum adımları (gereksinimler, kütüphaneler, ortam) net belirtilmiş | s.13 | `README.md`, `app/README.md`, `app/requirements*.txt`, `app/web/package.json` | ⚠️ **yarım** — `build_demo_db` adımı yok (T-038), `pytest` yanlış (T-048) |
| Demo videosu, maksimum 5 dakika (arayüz + dashboard + chatbot + metin girdisi + yapılandırılmış çıktı + karşılaştırma) | s.14 | `app/docs/sunum/anatolia-ai-demo-kapsamli.mp4` (**3:04**, kartsız, 12 ekran) + `anatolia-ai-demo-1dk-sekiz-ekran.mp4` (**59 sn**) | ✅ **KAPANDI (16 Ağu)** — T-002/T-003. ⚠️ dosyalar henüz commit edilmemiş |
| Proje dokümantasyonu — 10 alt madde | s.14 | `app/docs/rapor/anatolia-ai-teknik-rapor.md` (77 KB), `app/docs/sartname-kod-eslesme.md`, `OFFLINE-KANIT.md`, `model-license-audit.md`, `veri-katmani.md`, `katilim-bankaciligi-guvenligi.md`, `kaynak-tuketimi.md` | ⚠️ **yarım** — içerik var, ana belge **commit edilmemiş** (T-006, T-065) |
| Sunum materyali (PDF **ve** PPTX) | s.14 | `app/docs/sunum/anatolia-ai-sunum.pdf` (**15 sayfa**, 1440×810 pt, metin katmanı vektör) · `anatolia-ai-sunum.pptx` (**15 slayt**, 20″×11,25″) · üreteç `docs/sunum/uret-sunum.py` | ✅ **KAPANDI (16 Ağu)** — T-004. Doğrulandı: pypdf 15 sayfa, `slideN.xml` 15, `testzip()` hatasız. ⚠️ henüz commit edilmemiş |

### §7 Değerlendirme Kriterleri

| Gereklilik | Şartname referansı | Projedeki karşılığı (dosya) | Durum |
|---|---|---|---|
| Fonksiyonellik ve Senaryo Kapsamı (%20) — eksiksiz çıkarım · benzer ürünlerin karşılaştırılması · uçtan uca çalışma · çıktıların doğru ve anlaşılır olması | s.15 | `app/src/pipeline.py`, `comparison/compare.py`, `app/web/` (5 sekme) | ⚠️ uçtan uca çalışıyor · ❌ temiz klonda korpus 3 belge (T-037) · ❌ `%0` gürültüsü (T-020) |
| Teknik İmplementasyon ve Mimari (%20) — NLP yönteminin uygunluğu · ön işleme · çıkarım başarısı · modüler/okunabilir kod · düzenli veri yapısı | s.15 | 890 test (`unittest`), `ruff` CI kapısı, `eval/properties.py` değişmez denetimi, iki backend'li depo sözleşmesi (`src/db/base.py`) | ✅ güçlü · ⚠️ 62 test CI'da atlanıyor (T-046) · ❌ frontend testi yok (T-047) |
| On-Prem Uygulanabilirlik (%20) — kurum içi çalışma · dış bağımlılık düşüklüğü · modelin lokal çalışabilirliği · entegre edilebilir mimari | s.15 | `docker-compose.yml`, `OFFLINE-KANIT.md`, imaj 96,5 MiB, `api+postgres ≈255 MB` | ✅ ölçülmüş kanıt · ⏳ tam yığın / amd64 / GPU doğrulanmadı (T-039…T-044) |
| **Model Başarısı ve Anlamlandırma Yeteneği (%30)** — farklı ifade biçimlerini yorumlama · anlamlı bilgilerin doğru çıkarılması · eksik/farklı yazılmış bilgide doğru sonuç | s.15 | `app/eval/` (8 modül, ~3.400 satır), `app/data/gold/` (anotasyon hattı) | ❌ **ÖLÇÜM YOK** — `metrics.json` hiç üretilmedi, anotasyon 0/3.422 satır (T-010…T-018) |
| Yenilikçilik ve Yaratıcılık (%10) — özgün yaklaşım · ek veri alanları · geliştirilebilirlik · dokümantasyonun açıklığı | s.15 | `eval/properties.py` (değişmez denetimi), kaynak-span vurgulama, `comparison/contradiction.py`, `chatbot/safety.py` (5 kapı), config-driven banka onboarding | ✅ dört özgün eksen · ⚠️ çelişki tespiti 849'da 1 sonuç, yanlış negatif ölçülmedi (T-031) |

### §8 / §9 / §10 Süreç ve katılım şartları

| Gereklilik | Şartname referansı | Projedeki karşılığı (dosya) | Durum |
|---|---|---|---|
| Takım tanıtım sunumu (üye görev tanımları dahil) zorunlu | s.16, s.17 | — | ❌ **doğrulanmamış / bulunamadı** (T-008) |
| Kod ve **veri kümeleri** GitHub'da açık lisansla | s.17 | `LICENSE` (Apache-2.0) kod için · veri seti lisansı yok | ⚠️ **yarım** (T-005) |
| Ücretli yazılım / üçüncü taraf hizmet kullanılmaması | s.17 | `app/requirements*.txt` (tümü Apache/MIT/BSD), `.env.example`'da anahtar yok, `OFFLINE-KANIT.md` ağsız koşu | ✅ |
| Nihai lisans Apache-2.0, Türkiye Açık Kaynak Platformu hesabında paylaşım | s.17 | `LICENSE`, `README.md:6` etiketler | ✅ lisans var · ⏳ platform hesabına aktarım doğrulanmadı |
| Depo: (1) eksiksiz bağımlılık listesi | s.18 | `app/requirements.txt`, `requirements-api.txt`, `app/web/package.json` | ✅ · ⚠️ `gliner` ilan edilip kullanılmıyor (T-032) |
| Depo: (2) çalıştırma adımlarının tamamı | s.18 | `README.md`, `app/README.md`, `docker-compose.yml` | ⚠️ **yarım** (T-038) |
| Depo: (3) veri setinin **herkese açık indirme bağlantısı** | s.18 | `README.md:117` yer tutucu | ❌ **yapılmamış** (T-001) |
| `BilisimVadisi2026` etiketi + en az haftalık güncelleme | s.18 | `README.md:6`, `git tag -l` → `hafta-00`, `hafta-01` | ✅ süregeliyor · ⚠️ tampon bitti, `hafta-02` gerekiyor (T-007) |
| Sunum süresi 4 dk + demo videosu 1 dk; demo gösterimi zorunlu | s.19 | — | ❌ **yapılmamış** (T-003); süre çelişkisi açık (T-064) |
| Sunumun GitHub hesabına yüklenmesi | s.19 | — | ❌ **yapılmamış** (T-009) |
| Kodun yalnızca yarışma döneminde yazılmış olması (Turnitin) | s.17 | `git log` — ilk commit 2026-06-18, tüm geçmiş yarışma dönemi içinde | ✅ `git log --reverse` ile doğrulanabilir |

---

## Sources

- `2026_TEKNOFEST_TYDA_SARTNAME_Ikinci_Senaryo_TR_1_SmsXO.pdf` — §3 (s.4), §4 (s.5),
  §5.1–§5.10 (s.6–11), Örnek Senaryolar (s.11–13), §6 (s.13–14), §7 (s.15),
  §8 (s.16–17), §9 (s.18), §10 (s.18–19), §11 (s.19)
- `sources/teknofest/2026-06-16-teknofest-tyda-sartname-2-senaryo.md` — ingest özeti,
  open-threads bölümü
- `app/docs/sartname-kod-eslesme.md` — madde bazında kod karşılığı ve durum işaretleri
- `app/docs/rapor/anatolia-ai-teknik-rapor.md` — E1–E5 bölümleri (envanter, teslim
  eksikleri, 20 açık soru, 14 tutarsızlık, 23 günlük yol haritası)
- `app/docs/rapor/olcumler.md` — §14 "Şu an ölçülmemiş her şey" tam listesi
- `app/docs/OFFLINE-KANIT.md` §10, `app/docs/kaynak-tuketimi.md`,
  `app/docs/model-license-audit.md` §4–§5,
  `app/docs/katilim-bankaciligi-guvenligi.md` §6 — dürüst eksik listeleri
- Bu oturumda koşturulan komutlar: `unittest discover` · `pytest --version` ·
  anotasyon CSV sayımı · `git log/status/tag/check-ignore` · `pdftotext` ·
  modül↔test `grep` eşlemesi

## Related

- `app/docs/sartname-kod-eslesme.md` — bu envanterin madde bazlı karşılığı
- `app/docs/rapor/anatolia-ai-teknik-rapor.md` — aynı eksiklerin anlatısal ve
  ölçüm-ayrıntılı hali
- `syntheses/teslim-ve-degerlendirme-rehberi.md` — teslim kalemleri ve puanlama
  (`status: celiskili`, T-064)
- `log.md` — kronolojik değişiklik günlüğü (T-055 ile güncellenecek)
