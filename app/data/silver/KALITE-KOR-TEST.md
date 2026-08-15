# Gümüş Etiketleyici — Kör Kalite Testi

> Koşuldu: 2026-08-15 · Örneklem: **60 hücre**, 10 alan çeşidi
> Girdi: `kalite_ornegi.jsonl` · Çıktı: `kalite_sonucu.jsonl`

## Tasarım

İki insan anotatörün (A ve B) **bağımsız olarak aynı kararı verdiği** 88
hücreden 60'ı seçildi (alan çeşitliliği gözetilerek). Gümüş etiketleyici bu
hücreleri **insan kararını görmeden** etiketledi: `round1_A.csv`,
`round1_B.csv`, `round1_silver.jsonl` ve tüm gold/κ raporları okuması yasaklandı.
Yalnız belge metni, kılavuz ve modelin ham çıktısı verildi.

İki insanın hemfikir olduğu hücreler seçildi çünkü orada "doğru cevap" en az
tartışmalıdır. Karşılığında örneklem **kolay tarafa yanlıdır** — bu sayı
gümüşün genel doğruluğu değil, **net vakalardaki** uyumudur.

## Sonuç

| Ölçüt | Değer |
|---|---:|
| Karar uyumu (`ok`/`fix`/`absent`/`unclear` aynı mı) | **45/60 = %75,0** |
| Sonuç uyumu (ortaya çıkan gold DEĞERİ aynı mı) | **43/60 = %71,7** |

Karşılaştırma için: aynı turda **iki insan** anotatörün ham karar uyumu
141 ortak kararda **88/141 = %62,4** (Cohen κ = 0,274).

Bu iki sayı doğrudan kıyaslanamaz — 60'lık örneklem insanların zaten uzlaştığı
hücrelerden seçildi. Söylenebilecek olan şudur: gümüş etiketleyici, insanların
net bulduğu vakaların dörtte üçünde onlarla aynı kararı verdi.

## 17 uyuşmazlığın kırılımı

Uyuşmazlıkları okumak sayıdan daha öğretici. Üç öbeğe ayrılıyorlar:

### A) Gümüş kabuk kirliliği yakaladı, insan onaylamıştı — 9 vaka

Bu vakalarda **insanlar modelin çıktısına `ok` demiş**, gümüş ise değerin
kampanyaya ait olmadığını (`ANNOTATION_GUIDE` §4.13/8) gerekçelendirerek
`absent` yazmış:

| Alan | İnsan | Gümüşün gerekçesi |
|---|---|---|
| `taksit_sayisi` = 4 | `ok` | "Diğer Kampanyalar" bloğundaki MTV kampanyasından (2 belge) |
| `finansman_tutari` = 5.000 TL | `ok` | komşu kampanya bloğundan ("İlk Bankkart") |
| `finansman_tutari` = 100 / 50 TL | `ok` | fon asgari işlem tutarı — yatırım sayfasında finansman değil |
| `vade_ay` = 24 | `ok` | ücret tarifesinin "erken kapama 24 aya kadar" satır başlığı |
| `masraf_durumu` = masrafsız | `ok` | KVKK başvuru metnindeki "ücretsiz" — SWIFT ücretiyle ilgisiz |
| `hedef_kitle` = `belirli_segment` | `ok` | "KOBİ" yalnız kırılma menüsünde, gövdede segment yok (2 belge) |
| `kampanya_suresi` = 2025-07-31 | `ok` | stopaj oranının geçerlilik dipnotu |

Bu öbek tek başına bir bulgudur: **§4.13/8 kılavuzda yazılı ama uygulanmıyor.**
Kuralın var olması yetmemiş; insanlar modelin ürettiği değeri metinde
gördükleri için onaylamışlar, değerin *hangi öznenin* değeri olduğunu
sorgulamamışlar.

### B) Gümüş biçim/yazım olarak daha doğru — 2 vaka

- `İhtiyaç Finasmanı` → `İhtiyaç Finansmanı`. İnsanın yazım hatası; bu değer
  `lint_review_csv`'yi de düşürüyor ("kampanya türü tanınmıyor").
- `150000` → `{"value": 150000, "currency": "TRY"}`. Aynı tutar, gümüş kanonik
  biçimde yazmış.

### C) Gerçek yorum farkı — 6 vaka

Burada hangisinin haklı olduğu **hakemlik konusudur**, gümüş otomatik haklı
değildir:

- `campaign_type`: `Konut Finansmanı` ↔ `İhtiyaç Finansmanı` (prefabrik ev —
  banka ürünü kendi ihtiyaç kategorisinde sunuyor)
- `campaign_type`: `Yatırım Ürünü` ↔ `absent` (ücret tarifesi listesi; tek özne
  testi)
- `kampanya_suresi`: `2020-07-22` (bülten yayın tarihi) ↔ `2020-09-30`
  (metindeki kampanya bitişi)
- `vade_ay`: `36` ↔ `120` (aralıkta en uzun vade kuralı)
- `kampanya_kosullari`: K3 ihlalli tutar cümlesinin listede kalıp kalmayacağı

## Nasıl okunmalı

**Bu test gümüşü gold yerine geçirmez.** Gösterdiği şey, gümüş setin
sınıflandırıcı eğitimi ve hata kalıbı çıkarımı için kullanılabilir bir sinyal
taşıdığıdır — ve beklenmedik biçimde, insan anotasyonundaki sistematik bir
boşluğu (kabuk kirliliği onayı) ortaya çıkardığıdır.

**Öneri:** A öbeğindeki 9 vaka `_kilavuz-revizyon-onerisi-round1.md` Öneri 3 ve
4 ile birlikte hakemliğe alınsın. Eğer hakemlik gümüşü haklı bulursa, aynı
kalıbın round1'in insan kararı verilmiş **368 hücresinin tamamında** taranması
gerekir.

## Yeniden üretmek için

```bash
# örneklemi kur (A ve B'nin hemfikir olduğu hücrelerden)
# -> data/silver/kalite_ornegi.jsonl
# etiketleyici oturumu körlemesine koşar -> kalite_sonucu.jsonl
# kıyas:
.venv/bin/python -m scripts.report_iaa --help   # jeton mantığı: row_value_token
```
