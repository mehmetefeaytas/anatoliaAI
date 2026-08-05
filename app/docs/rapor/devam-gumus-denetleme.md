# Devam notu — gümüş denetleyici turu (BLOKE) + kural oyu ölçümü

**Tarih:** 2026-08-05
**Durum:** denetleyici oyu **koşulamadı**. Sebep teknik değil, **API erişimi**:
bağımsız denetleyici oturumu **dört kez** `529 Overloaded` ile düştü.

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
