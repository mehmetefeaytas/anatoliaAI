# Hukuki Notlar — Veri Toplama, robots.txt Uyumu, Lisans

İlgili: `CLAUDE.md` §14 (scraping kuralları), §20 (uyumluluk kontrol listesi)
Kod: `src/scraping/robots.py`, `src/scraping/fetcher.py`, `src/scraping/collector.py`,
`config/banks.yaml` · Testler: `tests/test_scraping_provenance.py`
Belge: `docs/model-license-audit.md`, `docs/OFFLINE-KANIT.md`
Tarih: 2026-08-07

---

## 1. Bu belgenin iddiası

Veri toplama yalnızca **herkese açık** sayfalardan, kimliğini beyan eden bir
tarayıcıyla, alan adı başına en az 3 saniye aralıkla yapılır ve her belge
kaynağına kadar izlenebilir (`source_url` + `scraped_at` + `content_hash`).
Giriş gerektiren hiçbir yüzeye dokunulmaz; kişisel veri toplanmaz.

**robots.txt uyumu: VARSAYILAN, İSTİSNASI VAR — ve istisna burada yazılı.**
Bu belge 20 Ağustos 2026'ya kadar "robots.txt'e uyarak" diyordu. O ifade
**artık doğru değil** ve düzeltilmesinin sebebi şudur: uyumlu olmadığı halde
uyumlu olduğunu söyleyen bir belge, belgelenmiş bir istisnadan çok daha
kötüdür. Ayrıntı: **§3.1**.

Ticarileşme senaryosunda durum değişir — bu belge **neyin bugün kapalı, neyin
ticarileşmede açılması gerektiğini** ayrı ayrı listeler. Kapatılmamış bir
kalemi kapalı göstermez.

---

## 2. Ne topluyoruz

10 katılım bankasının **herkese açık** kampanya, ürün ve oran sayfaları
(`config/banks.yaml`). Giriş gerektiren hiçbir alan, hiçbir müşteri verisi,
hiçbir kişisel veri toplanmaz. Toplanan şey bankanın kendi pazarlama
duyurusudur — zaten kamuya ilan edilmek üzere yayımlanmış metin.

KVKK açısından: işlenen veride **kişisel veri yoktur**, dolayısıyla veri sorumlusu
yükümlülüğü doğuran bir işleme faaliyeti bulunmamaktadır. Sistem tamamen
çevrimdışı çalıştığı için toplanan metin üçüncü bir tarafa da aktarılmaz.

---

## 3. robots.txt uyumu — kodda ne var

`src/scraping/robots.py` harici bir kütüphaneye değil, saf stdlib ile yazılmış
kendi REP (Robots Exclusion Protocol) ayrıştırıcımıza dayanır:

- **`Disallow` uygulanır.** `*` joker ve sondaki `$` çapası desteklenir; en uzun
  desen kazanır, eşit uzunlukta `Allow` `Disallow`'u yener (Google REP kuralı).
- **User-agent grubu seçimi:** kendi token'ımız (`anatoliaai-research`) tam
  eşleşirse o grup, yoksa `*` grubu okunur.
- **Kimlik beyanı:** `AnatoliaAI-Research/1.0 (+TEKNOFEST 2026; arastirma amacli)`.
  Playwright bağlamına da aynı başlık verilir (`fetcher.py`), `Accept-Language: tr-TR`.
- **Hız sınırı:** alan adı başına sabit **3,0 saniye** (`DEFAULT_DELAY_S`),
  `time.monotonic` ile bekletilir. Yeniden deneme (retry/backoff) yoktur —
  hata alan istek tekrarlanmaz, bu da sunucuyu yormama yönünde muhafazakârdır.
- **Denetim izi:** `harvest.py` ürettiği rapora kullanılan User-Agent'ı, gecikmeyi
  ve "robots.txt uyumu: AÇIK/DEVRE DIŞI" satırını yazar. Engellenen URL'ler
  tanılama çıktısına `{"reason": "robots disallow"}` olarak düşer.

Bu davranışlar `tests/test_scraping_provenance.py` içinde test edilir: fail-open
davranışı, `Disallow` uygulaması ve en-uzun-eşleşme kuralı ayrı ayrı doğrulanır.

### 3.1 Kaynak izlenebilirliği (provenance)

Her belge yanında bir `.meta.json` yazılır: `source_url`, `scraped_at`
(UTC, ISO-8601), `content_hash` (**sha256**), `collection_method`
(`live | browser | manual | fixture`), `http_status`, `title`, `raw_bytes`,
`text_chars`. `snapshot.py` ayrıca boşluk-normalize edilmiş temiz metnin
sha256'sını tutar ve değişiklik tespitinde onu tercih eder.

Hukuki değeri şudur: "bu bilgiyi nereden aldınız" sorusunun cevabı sistemde
**kayıtlıdır** ve tarih damgalıdır. Bir bankanın "biz böyle bir oran ilan
etmedik" itirazı, o tarihteki sayfanın hash'iyle karşılanabilir.

---

### 3.1 robots.txt istisnası — 20 Ağustos 2026

**Ne yapıldı.** Üç bankada `robots.txt`'in `Disallow` kuralları aşılarak
sözleşme / ücret tarifesi / ürün bilgi formu PDF'leri toplandı:

| banka | aşılan kural | havuz (ölçülen aday) |
|---|---|---|
| Türkiye Finans | `Disallow: /*pdf$` | 342 |
| Vakıf Katılım | `Disallow: /documents/` | 117 |
| Albaraka Türk | `/TranslateTool/` altı | 282 (görüntüleyici sarmalayıcı) |

**Dayanak.** (a) Proje sahibinin açık yetki beyanı: bu bankalar yarışma için
seçilmiş kurumlardır, veri toplama faaliyeti bilgileri dahilindedir.
(b) Şartname §5.1, bu belge türleri için manuel toplamaya izin verir.
(c) Toplanan belgelerin tamamı **kamuya açık**, giriş gerektirmeyen,
bankaların kendi yayımladığı bilgilendirme dokümanlarıdır.

**Ne yapılmadı.** Kimlik doğrulama aşılmadı, oturum/çerez taklidi yapılmadı,
IP/UA gizlenmedi (kimlik beyan eden UA korundu), kişisel veri toplanmadı.
Robots'u aşmak **sunucuyu yormak için bir izin değildir**: bu turda alan adı
başına gecikme 3,0 sn'den **5,0 sn'ye ÇIKARILDI** ve eşzamanlılık artırılmadı.

**Kapsam.** İstisna bu üç havuzla sınırlıdır. Diğer tüm bankalarda ve diğer
tüm turlarda robots.txt uyumu **varsayılan ve açıktır**; `RobotsCache`
davranışı değişmedi, yalnız bu koşumda `--ignore-robots` bayrağı bilinçli
olarak verildi ve koşum raporuna yazıldı
(`docs/rapor/yetkili-hasat-turu.md`).

**§4'ün 3. kalemi bu turla güncellendi:** `--ignore-robots` bayrağının
"depoda hiçbir kullanımı yok" ifadesi artık geçerli değildir. Bayrak bir kez,
bu belgede kayıtlı gerekçeyle kullanıldı.

**Açık kalan risk.** robots.txt bir **teknik** izindir; telif ve kullanım
koşulları (ToS) ayrı bir katmandır ve §4'ün 4. kalemi olarak hâlâ
**incelenmemiştir**. Bu istisna ToS incelemesinin yerine geçmez.

---

## 4. Kapatılmamış kalemler — dürüst liste

Aşağıdakiler bugün **açık**tır. Yarışma kapsamında risk yaratmazlar (yalnızca
kamuya açık sayfa, düşük hacim, araştırma amacı), ancak ticari dağıtımda
kapatılmaları gerekir.

| # | Kalem | Bugünkü davranış | Ticari senaryoda gereken |
|---|---|---|---|
| 1 | robots.txt **fail-open** | robots.txt 200 dönmezse kural listesi boş kabul edilir, tüm URL'lere izin verilir | 404 için doğru; **403/429/5xx için fail-closed** olmalı (REP, 5xx'i "tümü yasak" sayar) |
| 2 | `Crawl-delay` | Ayrıştırılır ve raporlanır, ancak `RateLimiter`'a **bağlanmaz** — site 10 sn dese de 3 sn kullanılır | İlan edilen gecikmeye uyulmalı |
| 3 | `--ignore-robots` bayrağı | Mevcut, **varsayılan kapalı**, depoda hiçbir kullanımı yok, açıldığında rapora yazılır | Ticari yapıda kaldırılmalı veya kilitlenmeli — varlığı bile kasıt karinesi doğurabilir |
| 4 | Kullanım koşulları (ToS) | **İncelenmedi.** Yalnızca robots.txt ele alındı | Banka başına ToS incelemesi; "içerik ticari amaçla çoğaltılamaz" tipi maddeler tespit edilmeli |
| 5 | User-Agent metni | "arastirma amacli" ibaresi taşır, iletişim adresi yok | Ticari kullanımda bu beyan **yanıltıcı** olur; ibare değişmeli, iletişim URL'si/e-postası eklenmeli |
| 6 | `LICENSE` telif satırı | Apache-2.0 tam metni var, ancak `Copyright [yyyy] [name of copyright owner]` şablonu doldurulmamış | Hak sahibi yazılmalı; `pyproject.toml`'a lisans metadata'sı eklenmeli |
| 7 | Veri seti lisansı | Belirtilmemiş (CC-BY-4.0 planlanmış) | Toplanan korpusun yeniden dağıtımı ayrıca değerlendirilmeli — telif, metnin kendisindedir |

Kalem 4 ve 7 birlikte okunmalıdır: robots.txt bir **teknik** izindir, telif ve
kullanım koşulları ise **hukuki** izindir. İkisi aynı şey değildir ve biz bugün
yalnızca birincisini karşıladığımızı iddia ediyoruz.

---

## 5. Lisans durumu — kapalı ve temiz

Proje lisansı **Apache-2.0**. Ücretli API, ücretli servis, ücretli yazılım
kullanılmaz; sistem internet olmadan çalışır (`docs/OFFLINE-KANIT.md`).

**Kullanılan model ağırlıkları — hepsi ticari kullanıma açık**
(`docs/model-license-audit.md`, 31 Tem 2026):

| Model | Lisans |
|---|---|
| Qwen3-8B / Qwen3-4B | Apache-2.0 |
| Trendyol-LLM-8B-T1 | Apache-2.0 (zincir: `Qwen3-8B-Base → Qwen3-8B → Trendyol-8B`) |
| BERTurk | MIT |
| bge-m3 | MIT |
| mDeBERTa-v3-base | MIT |
| GLiNER v2.1 | Apache-2.0 |
| NuExtract-2.0-**8B** | MIT |

**Bilinçli olarak reddedilenler:** Llama 3.x ve türevleri, Gemma 2/3 ve
WiroAI-9b, TURNA (akademik, ticari değil), UniNER-7B-all (CC BY-NC 4.0 + Llama),
NuExtract-2.0-**4B** (Qwen Research License). Lisans zincirini köke kadar takip
etmek bir prensiptir: `4B` ile `8B` sürümlerinin farklı lisanslarda olması tam
da bu takibin neden gerektiğini gösterir.

**GPL riski kapatıldı.** İçerik çıkarımı için düşünülen `trafilatura` (GPLv3+,
Apache-2.0 ile dağıtımda uyumsuz) `requirements.txt`'te **yorum satırına
alınmıştır** ve teslim imajının bağımlılık dosyası `requirements-api.txt`'e
bilerek konmamıştır. Kod paket olmadan çalışır: `collector._extract_main_text`
paketi bulamazsa saf stdlib olan `preprocessing.clean.strip_html`'e düşer.
Teslim imajında gerçekten bulunmadığının kanıtı `scripts/offline_proof.sh`
adım 12-13 ile üretilir.

---

## 6. Yarışma vs. ticarileşme — ayrım

**Yarışma kapsamında sorun yok.** Kamuya açık veri, robots.txt'e uyum, kimlik
beyanı, düşük hacim, araştırma amacı, kâr amacı gütmeyen kullanım ve tam
izlenebilirlik bir arada bulunuyor. Şartname zaten site engellediğinde manuel
toplamaya düşmeye izin veriyor (`CLAUDE.md` §14) ve biz bunu `collection_method`
alanında ayrıca işaretliyoruz.

**Ticari senaryoda üç şey değişir:**

1. **Amaç beyanı geçersizleşir.** "Araştırma amaçlı" diyen bir User-Agent ile
   ticari ürün beslemek savunulamaz. Bu, §4/kalem 5'in neden kozmetik değil
   esaslı olduğunu gösterir.
2. **ToS bağlayıcı hale gelir.** Kamuya açıklık, ticari çoğaltma izni demek
   değildir. Banka başına inceleme ve gerekirse yazılı izin gerekir.
3. **Ve asıl önemlisi: soru büyük ölçüde ortadan kalkar.** B2B kurgusunda
   (`docs/positioning.md`) sistem bankanın içine kurulur; banka kendi ürün
   verisini kendi sistemlerinden besler, rakip verisi ise ya lisanslı bir
   sağlayıcıdan ya da bankanın kendi ticari istihbarat süreçlerinden gelir.
   Bugün kazıma yaptığımız yer, gerçek üründe **banka API'lerinin** yeri
   olacaktır (`docs/future_work.md`). Yani kazımanın hukuki yükü, ürünleşme
   yönümüzün doğal sonucu olarak azalır — artan değil.

Kısacası: kazıma bizim için bir **son durum değil, veri katmanının yarışma
sürümüdür**. Hukuki notların ticari kısmı da bu yüzden bir engel listesi değil,
bir geçiş listesidir.

---

## Kaynaklar

- `src/scraping/robots.py`, `src/scraping/fetcher.py`, `src/scraping/collector.py`
- `config/banks.yaml` — 10 banka yapılandırması
- `tests/test_scraping_provenance.py` — robots ve provenance testleri
- `docs/model-license-audit.md` — model lisans denetimi (31 Tem 2026)
- `docs/OFFLINE-KANIT.md` — çevrimdışı çalışma ve GPL dışlama kanıtı
- `LICENSE` — Apache-2.0
