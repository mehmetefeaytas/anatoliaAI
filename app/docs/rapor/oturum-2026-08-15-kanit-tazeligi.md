---
title: Oturum raporu — kanıt-tazeliği kapısı ve ölçüm zincirinin onarımı
tags: [oturum, olcum, kanit, ci, teslim]
date: 2026-08-15
status: stable
---

# Oturum raporu — 15 Ağustos 2026 (ikinci oturum)

**Tetikleyen:** bir jüri simülasyonu bizi 84,0 ile birinci gösterdi (en yakın
rakip 76,9) ve dört açık işaretledi. Açıklar **kodda tek tek doğrulandı**;
ikisi çürüdü, ikisi doğrulandı, ve doğrulama sırasında simülasyonun
görmediği daha ciddi bir sorun çıktı.

> **Bulgu:** Biricik farklılaştırıcımız *ölçüm dürüstlüğü*. Yayımladığımız
> kanıtlar koddan sapmıştı — yani en güçlü kartımızı kendi belgelerimiz
> çürütüyordu.

---

## 1. Jüri iddialarının denetimi

| İddia | Karar | Kanıt |
|---|---|---|
| "Kırık test var (2.702/2.701)" | **YANLIŞ** | `pytest` 2.894 geçti · 0 hata |
| "En yüksek puan aldığımız yenilik üründe yok" | **KISMEN** | Orkestrasyon üretimde yok — ama unutkanlıktan değil: McNemar p=0,0391 ile **kabul kapısından geçemedi** (`eval/predictors.py:81-83`) ve `tests/test_orchestrator.py:340` bunu **testle kilitliyor** |
| "SBOM yok" | **DOĞRU** | `git grep -liE 'cyclonedx\|pip-licenses\|sbom'` → sıfır |
| "Offline kanıt bayat" | **DOĞRU** | 31 Temmuz damgalı; aradan **474 commit** geçmiş (jürinin "50" sayısı yanlış — kısa SHA ile `git log` bu depoda erken duruyor) |

---

## 2. Asıl bulgu: yayımlanan sayılar koddan sapmıştı

Hepsi bu oturumda ölçüldü:

| Yayımlanan | Gerçek | Kaynak |
|---|---|---|
| `README.md` κ = 0,302, kanıt olarak `iaa_report.md`'ye yolluyor | O dosya **"ölçülemedi"** diyordu | v2 CSV'leri 260 satır / **0 dolu karar** |
| bootstrap **2000** örnek | **1000** | `eval/stats.py:DEFAULT_RESAMPLES`; 2000 ana hatta **hiç koşmadı** |
| **2.631** test, 205 atlanan | **2.894 geçti · 53 atlandı** | `pytest` |
| korpus **1.774** | **1.782** | `demo.db` canlı sayım |
| `kar_payi_orani` F1 **0,500**, TP1/FN2 | **0,800**, TP2/FN1 | `per_field.csv` |
| gold **48 kayıt** | `gold.round1.json` **134** hazır ve commit'li | round1 onarımı |
| `OFFLINE-KANIT.md` `ANATOLIA_OFFLINE=1`'i **kanıt** gösteriyor | `a3c2f05` onu *"sahte bayrak"* diye kaldırmış | Dockerfile.api diff |
| gold'da `adjudicated: false` (134/134) | 41 uyuşmazlık kör hakemlikten geçti | `#hakemlik-round1` damgaları |

Ortak kök neden: **düzeltme tek seferliktir, sapma tekrar eder.** 12
Ağustos'tan bu yana üçüncü kez oluyordu.

---

## 3. Çözüm: kanıt-tazeliği kapısı

`scripts/kanit_tazeligi.py` — yayımlanan her sayıyı, onu üreten kanıtla
karşılaştıran bir CI kapısı. **İki ayrı denetim yapar ve ikisini
karıştırmaz:**

1. **Değer** — belgedeki sayı = kanıttan okunan sayı.
2. **Tazelik** — kanıtın kendisi güncel girdilerden mi üretilmiş?

İkincisi olmadan birincisi kendini kandırır: *bayat bir rapordan okunan
bayat bir sayı, bayat bir README ile mükemmel uyum gösterir.*

Tazelik üç şeyi denetler:
- raporun `gold_sha256`'sı bugünkü gold'unki mi
- rapor **temiz ağaçta** mı üretilmiş
- rapordan bu yana **çıkarım/ölçüm kodu** değişmiş mi (`app/src`, `app/eval`,
  `app/config`)

Üçüncüsü R3 sırasında eklendi: aynı gold, değişmiş bir çıkarıcıyla başka bir
F1 üretir; bu denetim olmasa kapı tam da önlemek için var olduğu şeyi
yapardı.

**Ölçemediğini "uyumlu" saymaz.** Kanıt üretilemeyen iddia `kanit_yok` olarak
ayrı raporlanır; sapma ise her zaman kırmızıdır — belge ile kanıt ayrışması
ölçüm eksikliği değil **yanlış beyandır**.

Bugün: **10 iddia · 0 sapma.**

---

## 4. Kapıyı kurunca çıkan dört sessiz kusur

Denetlenmesi gereken zincirin kendisinde dört kusur vardı. Dördü de aynı
sınıftan: *araç ya kendi çıktısını kanıt olmaktan çıkarıyor ya hiç ölçmüyordu.*

| Kusur | Sessiz sonucu |
|---|---|
| `eval/report.py::git_dirty` kendi rapor dizinini kirlilik sayıyordu | **Hiçbir eval raporu asla temiz olamıyordu.** 12 Ağustos raporunun `git_dirty=true` olmasının sebebi buydu — kusur o koşumda değil, bayrakta |
| ANSI renk kodu `\b` sözcük sınırını bozuyordu (`\x1b[32m2873`) | Test artefaktı **"0 test geçti"** yazıyordu ve hiçbir şey şikâyet etmiyordu |
| Tazelik ölçütü `git_sha == HEAD` idi | Artefaktı commit'lemek onu **doğduğu anda** bayatlatıyordu |
| `kos()` içinde yerel `cikti` (pytest çıktısı) aynı adlı parametreyi gölgeliyordu | Betik patlıyor, artefakt eski hâlinde kalıyordu |

Kapı ayrıca **kendi hatasını** yakaladı: `yapisal_mikro_f1` istenirken
`micro_f1_kalem` okunuyordu. İkisi farklı ölçüt (11 alan/ikili vs 12
alan/kalem); yanlış sayıyı "doğrulandı" diye geçirirdi. Ek olarak
yapılandırılmış kesit `metrics.json`'a hiç yazılmıyormuş — artefaktta
olmayan sayı makine denetlenemez.

---

## 5. Ölçülen durum (temiz ağaç, 15 Ağustos)

| | 12 Ağustos (yayımlanan) | 15 Ağustos (ölçülen) |
|---|---:|---:|
| 12-alan mikro-F1 | 0,452 | **0,464** [0,398–0,522] |
| makro-F1 | 0,556 | **0,601** |
| yapısal mikro-F1 (11 alan) | 0,646 | **0,671** |
| halüsinasyon | 0,059 | **0,047** (21/444) |
| test | 2.631 | **2.894** geçti / 53 atlandı |
| ECE | 0,306 | **0,188** |

İyileşme yeni bir şey yapmaktan gelmiyor: README 12 Ağustos'ta donmuştu ve
oransal ücret (§4.13/5) + kabuk kapısı (§4.13/8) düzeltmelerinin kazancını
göstermiyordu. **Kendi işimizi kendimize eksik anlatıyorduk.**

### İki gold seti, ve neden birleştirilmiyor

| | `gold.v2` | `gold.round1` |
|---|---:|---:|
| kayıt | 48 | 134 |
| zor vaka | 40 | 3 |
| `absent` kararı | **444** | **60** |
| 12-alan mikro-F1 | 0,464 | 0,744 |
| halüsinasyon | 0,047 | **0,433** |

Round1'in 0,433'ü bir gerileme değil **seçim etkisidir**: o sette bir hücre
inceleme kuyruğuna *zaten model bir şey ürettiği için* giriyor, yani `absent`
kümesi rastgele değil düşmanca seçilmiş bir alt küme.

Sonucu: **CI regresyon kapısı `gold.v2`'de kalıyor.** Round1'e taşımak,
önceden ilan edilmiş 0,08'lik halüsinasyon tavanını sayıya bakarak
gevşetmek olurdu.

---

## 6. R3 — planın gerekçesi çürüdü

Plan, `extract.py`'deki **11 sabit `trigger_distance=0`**'ı kusur sayıyordu.
Tek tek okundu ve varsayım yanlış çıktı: çoğunda tetikleyici sözcük
eşleşmenin **içindedir** (`"12 taksit"`, `"masrafsız"`, `"kâr payı %2,5"`),
yani mesafe gerçekten sıfır. Planın dayandığı ölçüm de tutmadı — "kütlenin
%73'ü ≥0,95" deniyordu, gerçek **%57,2**.

Gerçek kusur daha dardı: **liste alanlarında seçim belirsizliği hiç
sayılmıyordu.** `kampanya_kosullari` tek bir eşleşme değil, N cümlenin
SEÇİMİDİR ve kalem düzeyi kesinliği **0,556** iken **0,950** güven ilan
ediyordu. Mekanizma (`candidate_count`) zaten vardı, o iki çağrı yerinde
kullanılmıyordu.

| ölçüt | önce | sonra |
|---|---:|---:|
| tam 0,95 skorlu alan payı | %57,2 | **%38,5** |
| ECE | 0,192 | **0,188** |
| 0,90+ bandı doğruluğu | 0,571 | **0,688** |
| mikro / makro / yapısal F1 | — | **değişmedi** |
| `ASGARI_GUVEN` altı karar | 25 | **25** |

Son satır kabul ölçütüydü: `compare.ASGARI_GUVEN = 0,65` kullanıcıya
**görünen** bir kapıdır ve teslime 11 gün kala sessizce değişmemeliydi.

---

## 7. Kapatılan diğer açıklar

- **SBOM + lisans kapısı.** `docs/sbom.json` (CycloneDX 1.6, 96 paket) +
  `docs/LISANSLAR.md` + CI kapısı. Aktif rakiplerin hiçbirinde makine-okur
  SBOM yok. Kapı yazılırken iki gerçek kusur çıktı ve **kapı gevşetilmeden**
  düzeltildi: harf duyarsız `" or "` bölmesi bir LGPL paketini geçiriyordu;
  CycloneDX aynı lisansı iki kez yazınca tek lisanslı paketler bileşik
  görünüyordu.
- **`trafilatura` GPLv3+ riski çürütüldü.** Gerçek lisans **Apache-2.0**, pin
  aralığının iki ucunda da doğrulandı. Bir yıldır dayanaksız duruyormuş.
- **κ raporu çelişkisi.** `iaa_report.md` v1'in 0,302'sini taşıyordu, sonra v2
  (boş) dosyalardan yeniden üretilip üzerine yazılmıştı. Turlar ayrı
  dosyalara bölündü; `report_iaa` artık aynı ada farklı içerik yazmayı
  reddediyor. **Silme yok** — eski ad yerinde yönlendirme tablosuna dönüştü.
- **`adjudicated` bayrağı.** 134/134 "hakemlik yok" diyordu; artık **38 kayıt**
  `true` ve bunun **makine** hakemliği olduğu açıkça yazılı.
- **Şartname uyum matrisi.** `docs/SARTNAME-UYUM.md` — 18 kalem, ✅7 · 🟠6 · ❌6.
  Kanıtsız hiçbir kaleme ✅ verilmedi.

---

## 8. Düzeltilen iddialarım

Bu oturumda **iki kez** yanlış sayı verdim ve ikisi de plana girmişti:

1. **"11 sabit `trigger_distance=0` uydurma"** — değil; çoğu doğru.
2. **"Kütlenin %73'ü ≥0,95 bandında"** — gerçek %57,2.

İkincisi birincisinin gerekçesiydi; ikisi birlikte kullanıcıyı benim yanlış
ölçümüme dayanan bir onaya götürdü. Ölçüm düzeltildi, iş dar ve
savunulabilir kısmıyla yapıldı.

Bir de test yazarken aynı hatayı tekrarladım: sentetik metin kurup çoklu
seçim bekledim, üretmedi. **Ders (ikinci kez):** sahte nesne/metin kurmak
yerine gerçek korpusu koştur.

---

## 9. Açık kalanlar

| İş | Durum |
|---|---|
| **Offline kanıtın tazelenmesi** | Docker Desktop kapalı — `bash scripts/offline_proof.sh` kullanıcı makinesinde koşacak. Sonrasında `OFFLINE-KANIT.md` §3.4'teki sahte bayrak kanıtı kaldırılmalı |
| **Veri seti yayını** | Paket ve HF yükleme betiği hazırlanıyor; `HF_TOKEN` kullanıcıda. **Şartname s.18 zorunlu kalemi** |
| **İnsan hakemliği** | Kullanıcı kararı: insan anotasyonu yok. Gold makine anotatörlü + makine kör hakemli olarak **etiketiyle** yayımlanıyor |
| `sartname-kod-eslesme.md` kendi içinde çelişiyor | §5.7 tablosu ✅ derken rubrik "eksik" diyor — tek yönde kapatılmalı |

## Sources
- `docs/rapor/oturum-2026-08-15-round1-onarimi.md` — aynı günün ilk oturumu
- `docs/SARTNAME-UYUM.md` · `docs/LISANSLAR.md` · `docs/sbom.json`
- `scripts/kanit_tazeligi.py` · `scripts/test_ozeti.py` · `eval/report.py`

## Related
- [[oturum-2026-08-15-round1-onarimi]] — ölçüm zemininin ilk onarımı
- [[genel-denetim]] — düzeltilen `kar_payi_orani` sayıları
