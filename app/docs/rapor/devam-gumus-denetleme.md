# Devam notu — gümüş denetleyici turu (BLOKE) + kural oyu ölçümü

**Tarih:** 2026-08-05 (ikinci güncelleme)
**Durum:** denetleyici oyu **koşulamadı**. Sebep teknik değil, **API kapasitesi**:
bağımsız denetleyici oturumu **on bir kez** `529 Overloaded` ile düştü
(iki turda: 4 + 7).

## Ölçülen: hatalar iş SIRASINDA değil, BAŞLANGIÇTA

İkinci turda partiler 18'erliye indirildi ve her partiye "6'lı gruplar hâlinde
birikimli yaz, yarıda düşersen iş diskte kalsın" talimatı verildi. Sonuç:
**sıfır satır** yazıldı, yedi oturumun hiçbiri tek karar bile üretemedi.

Bu bir bulgu: oturumlar **başlarken** düşüyor, çalışırken değil. Yani
- parçalı yazma azaltımı **konu dışı** (yazacak iş hiç başlamıyor),
- parti boyutunu küçültmek **işe yaramaz**,
- tek çözüm **kapasitenin açılmasını beklemek** ya da işi yerel modele vermek.

Yerel yol (Ollama + `qwen2.5:7b-instruct`, Apache-2.0) zaten kurulu ve
şartname §5.10 açısından **tercih edilen** yol; harici asistan oturumu yalnız
kolaylık içindi. Denetleyici oyunu yerel modele vermek hem engeli kaldırır hem
teslim edilen sistemi harici bağımlılıktan kurtarır.

---

## ÇÖZÜLDÜ — denetleyici oyu yerelde koşuldu (2026-08-05)

`scripts/run_silver_verifier.py` yazıldı ve **89 denetlenmemiş önerinin
tamamı** koşuldu: 89/89, **0 hata**.

Çıktı: `data/silver/verdicts_local.jsonl` (`verifier: ollama:qwen2.5:7b-instruct`)

| ölçüm | değer |
|---|---:|
| öneriyle örtüşme | 85/89 (**%95,5**) |
| `evidence_supports=true` | 85 (%95,5) |
| `own_label=null` | 0 |

**%95,5 yüksek ve bu dikkatle okunmalı.** Betiğin lastik damga uyarısı %97'de
tetikleniyor, yani eşiğin hemen altında. Ancak üç şey lastik damga olmadığını
gösteriyor: (1) denetleyici öneriyi görmeden önce kendi etiketini veriyor
(sistem yönergesi bu sırayı zorluyor), (2) ayrışmalar **iki yönlü** — bir
vakada denetleyici haklı, (3) belgeler gerçekten kolay: 89'un 81'i açık
Konut/Taşıt sayfası.

### Ayrışan 4 belge (insan hakemliğine gider)

| belge | öneri | denetleyici | kim haklı görünüyor |
|---|---|---|---|
| `akbank--birikim-hesaplari-devlet-katkili-konut-hesabi` | Yatırım Ürünü | Konut Finansmanı | **öneri** — bu bir birikim hesabı |
| `akbank--ihtiyac-kredileri-tasit-teminatli-ihtiyac-kredisi` | İhtiyaç Finansmanı | Taşıt Finansmanı | **öneri** — taşıt yalnız teminat |
| `teb--tasit-teminatli-kredi` | İhtiyaç Finansmanı | *Taşıt Teminatlı İhtiyaç Kredisi* | **öneri** — denetleyici taksonomi dışı etiket üretti, mekanik kapı reddedecek |
| `yapi-kredi--konut-kredisi-anahtar-teslim-mortgage` | İhtiyaç Finansmanı | Konut Finansmanı | **denetleyici** — "mortgage" konut finansmanıdır |

Yani zayıf denetleyicinin tipik hatası yüzey anahtar kelimesine takılmak
("konut" gördü, ürünün birikim hesabı olduğunu kaçırdı) — ama dördü de zaten
insan kuyruğuna gidiyor, veri setine değil. Tasarımın istediği davranış bu.

### Kalan adım (koşulmadı — kullanıcı durdurdu)

```bash
# 1) Yerel kararları mevcut verdicts ile birleştir
cat data/silver/verdicts.jsonl data/silver/verdicts_local.jsonl \
    > data/silver/verdicts_tum.jsonl

# 2) Uzlaşma — DİKKAT: silver.jsonl'i BAŞTAN YAZAR
.venv/bin/python -m scripts.build_silver merge \
    --verdicts data/silver/verdicts_tum.jsonl

# 3) merge sonrası kuyruk çözücü TEKRAR koşulmalı
.venv/bin/python -m scripts.resolve_queue

# 4) Gerçek sayıyı rapordan oku (elle sayma yok)
cat data/silver/silver_report.json
```

Beklenti: Konut 13 → ~40+, Taşıt 9 → ~35+, yani Faz 3'ün (BERTurk ince ayarı)
20/20 hedefi rahatça aşılır. **Ama bu bir tahmin; ölçüm `merge` sonrası
`silver_report.json`'dan okunacak.**

---

## Neden bu oyu ben (orkestrasyon oturumu) kullanmadım

`consensus.py` üç oy tanımlıyor ve üçüncüsü şu: *"denetleyici — kendi etiketini
bağımsız verir, sonra alıntıyı yargılar."* `VerifyVerdict.own_label` alanının tek
varlık sebebi, denetleyicinin öneriyi kopyalayıp kopyalamadığını yakalamak;
kod bu kipi adıyla anıyor: **"lastik damga"**.

Bu oturum etiketleyicinin **toplam çıktısını biliyor** (Konut 43 / Taşıt 38 aday)
ve **20/20 hedefini** biliyor. Yani onaylamaya eğilimli bir tarafı var — lastik
damga korumasının var olma sebebi tam bu. Oyu kullanmak sayıyı hedefe ulaştırır
ama veri setinin kökenini savunulamaz kılar (şartname §8).

**Karar: oy kullanılmadı, durum açıkça bloke olarak kaydedildi.** Sayıyı
tutturmak için köken savunmasını feda etmek kötü bir takas.

---

## Bunun yerine yapılan: KURAL oyu ölçüldü

`consensus.py`'nin birinci oyu `RuleHintClassifier` — anahtar kelime tabanlı,
**LLM'i hiç görmez**, bedava ve tam bağımsız. Bu oyu koşmak bir karar vermek
değil, ölçüm yapmaktır; o yüzden yukarıdaki önyargı sorunu burada yok.

106 yeni önerinin etiketi ile kural sınıflandırıcının bağımsız etiketi
karşılaştırıldı (etiketi `null` olan 17 öneri hariç, n=89):

| etiketleyici etiketi | kural uyumu | toplam | oran |
|---|---:|---:|---:|
| **Konut Finansmanı** | **35** | 43 | **%81** |
| **Taşıt Finansmanı** | **31** | 38 | **%82** |
| İhtiyaç Finansmanı | 1 | 4 | %25 |
| Finansman | 0 | 3 | %0 |
| Yatırım Ürünü | 0 | 1 | %0 |
| **TOPLAM** | **67** | **89** | **%75** |

En sık ayrışmalar (etiketleyici → kural):

| | |
|---|---:|
| Konut Finansmanı → Kart | 6 |
| Taşıt Finansmanı → Kart | 4 |
| Finansman → Konut Finansmanı | 3 |
| Konut Finansmanı → Finansman | 2 |
| Taşıt Finansmanı → Konut Finansmanı | 2 |

### Bu ölçüm NE DEĞİLDİR

- **Doğrulama değil.** `consensus.py` kural oyuna **veto hakkı vermiyor** ve
  gerekçesi belgeli: kural katmanının kendi ölçülmüş hatası var (sözcük sınırı
  düzeltmesinden önce korpusun %48'ini sahte `Konut Finansmanı` yapıyordu).
  %81 uyum, etiketlerin doğru olduğunun kanıtı değil, **destekleyici sinyaldir**.
- **Bu kayıtlar gümüş DEĞİL.** Denetleyici oyu olmadan durumları
  `R_UNVERIFIED = "denetlenmedi"`. `silver.jsonl`'de Konut hâlâ **13**, Taşıt
  hâlâ **9**.
- Ayrışmaların yönü de bilgi: `→ Kart` sapmaları (10 vaka) kural
  sınıflandırıcının kampanya sayfalarındaki kart sözcüklerine takıldığını
  gösteriyor, yani muhtemelen **kural yanlış**, etiketleyici doğru. Ama bunu
  iddia etmek için de üçüncü oy gerekiyor.

### Yine de neyi söylüyor

İki bağımsız oyun (kural + etiketleyici) aynı dediği vaka sayısı: **Konut 35,
Taşıt 31**. Mevcut etiketli sayılarla toplandığında (13 ve 9) hedefin
(**20/20**) rahatça üzerinde. Yani Faz 3'ün (BERTurk ince ayarı) veri tarafı
büyük olasılıkla hazır — **ama bunu kesinleştiren şey denetleyici turu.**

---

## "başla" denince: denetleyici turu için tam sıra

Ayrı bir oturum/model açın ve şu sırayı izleyin. **Partiler hâlinde çalışın ve
her partiden sonra commit edin** — bu görev dört kez yarıda düştü ve her defasında
iş kayboldu.

```bash
# 1) Girdiyi TAZELE — eski batch 6000 karakterlik pencereyle üretilmişti ve
#    etiketlenebilir belgelerin %21'inde kampanya gövdesi o pencerenin
#    DIŞINDAYDI. MAX_PROMPT_CHARS artık 24000.
.venv/bin/python -m scripts.build_silver prepare   # verify_in_*.jsonl üretir

# 2) Denetleme (partiler hâlinde, ör. 25'erli) -> verdicts JSONL

# 3) Birleştir
.venv/bin/python -m scripts.build_silver merge

# 4) merge `silver.jsonl`'i BAŞTAN YAZIYOR, bu yüzden kuyruk çözücü
#    SONRADAN tekrar koşulmalı
.venv/bin/python -m scripts.resolve_queue

# 5) Gerçek sayıyı rapordan oku (elle sayma yok)
cat data/silver/silver_report.json
```

Uyarı: `prepare` 5 MB'a varan `verify_in_*.jsonl` üretiyor (kardeşleri 44 KB;
fark pencere büyümesinden). Bu türetilmiş girdiler **commit'lenmemeli**; bir
önceki çöken deneme 5 MB'lık bir artık bırakmıştı, silindi.

## Denetleyicinin karara bağlaması gereken kural boşluğu

**İşyeri / ticari gayrimenkul alım kredisi**, `docs/kampanya-turu-sinif-kurallari.md`
içindeki 10 kapının hiçbirine düşmüyor (2 belge, 0,4 güvenle artakalan
`Finansman`). Etiketleyici kuralı tek başına yazmamak için bıraktı; denetleyici
ikinci oy olarak gerekçeli öneri yazmalı ama **tek başına kesinleştirmemeli** —
"iki oyla önerildi, üçüncü onay bekliyor" diye işaretlenmeli.

## Açık uç

Korpusta **116 yeni `live/` belgesi** hâlâ etiketsiz (724 belge − 608 öneri) ve
`merge` eksik öneriyi hata saymıyor, yani **sessizce dışarıda kalıyorlar.** Bu
sessizlik en azından bir uyarıya çevrilmeli.

## Related
- [[devam-gumus-etiketleme]] — etiketleyici turunun bıraktığı notlar
- [[devam-durumu]] — genel durum ve "başla" sırası
