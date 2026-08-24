---
title: "TKBB sözlüğü ikincil kaynak olarak bağlanır (birleştirilmez)"
tags: [karar, terminoloji, sozluk, tkbb, veri-kaynagi]
source: "[[tcmb-sozlugu-terim-boslugunu-kapatmiyor]]"
date: 2026-08-24
status: stable
---

# TKBB sözlüğü ikincil kaynak olarak bağlanır

## Karar

TKBB Katılım Sözlüğü'nden hasat edilen **509 terim**, proje sözlüğüne
**birleştirilmez**; `terminology.load_terminology()` içinde **ikincil kaynak**
olarak yüklenir. Çakışan terimde **proje kaydı kazanır**.

Sonuç: **101 → 577 terim** (476 yeni, 33 çakışma proje lehine düşürüldü).

## Niçin birleştirme değil

Proje sözlüğü elle bakımlıdır ve `degildir` / `risk_notu` / `ayrim_notu` /
`sade_aciklama` alanlarını taşır. Bunlar hiçbir dış kaynakta yok ve
terminoloji kaleminin kalbi: *"müşteriye anlatırken 'faiz oranı' değil 'kâr
oranı / vade farkı' denmelidir"* gibi bir not, ancak kurum bilgisiyle yazılır.

509 terimlik dış kaynak yalnız **terim + tanım** taşıyor. Birleştirmek, elle
bakımlı 101 kaydı bir dış dosyaya karıştırmak ve sonraki hasatta ezme riski
almak olurdu. İkincil yükleme kaynakları ayrı tutuyor.

`Murabaha` bunun canlı örneği: iki kaynakta da var, proje kaydı kazanıyor ve
`sade_aciklama`sı korunuyor (testle kilitli).

## Ölçülmüş güvenlik durumu

Terim yolu **alıntı modunda** çalışır (`guard_output(..., alinti=True)`), yani
post-filter atlanır — Riba tanımının tersine çevrilmesini önlemek için
([[terim-sorusuna-sozlukten-cevap-verilmiyordu]]). Bu, dış kaynaktan gelen bir
tanımın yasak terim taşıması hâlinde ekrana çıkacağı anlamına gelir, o yüzden
ölçüldü:

| ölçüt | sonuç |
|---|---|
| tanımında yasak kök (faiz/kredi/mevduat) taşıyan | 54/509 (%11) |
| bunlardan karşıtlık bağlamında olan | 37 |
| kalan | 17 — hepsi meşru: *"faiz**siz** getiri"*, *"son kredi mercii"*, kurum adları (İhracat Kredisi Şirketi) |

Yani kaynak, projenin terminoloji diline aykırı bir kullanım getirmiyor.

## İki teknik tuzak — ikisi de testle yakalandı

**1. Sayaç kirlenmesi.** İkincil çakışmalar ilk sürümde `DUSURULEN`e
yazılıyordu. O sayaç proje sözlüğünün SAĞLIĞINI ölçer ve testte 0 olması
beklenir; çakışma ise normaldir. `IKINCIL_CAKISMA` ayrı sayaç olarak eklendi.

**2. Önbellek anahtarı.** `load_terminology()` ile
`load_terminology(VARSAYILAN_YOL)` aynı dosyaya çözülüyor ama farklı sonuç
döndürmesi gerekiyor (ilki ikincili ekler, ikincisi eklemez — testlerin
izolasyonu buna bağlı). Tek anahtar kullanıldığında ilk çağrının sonucu
ikinciye de dönüyordu; anahtar `(yol, path is None)` yapıldı.

## Kalan boşluk — kapanmadı

Chatbot'a sorulması muhtemel **10 operasyonel terim hâlâ eksik**:

    finansman · vade · taksit · tahsis ücreti · masraf · stopaj
    ekspertiz · limit · hesap işletim ücreti · dosya masrafı

TKBB sözlüğü de bunları içermiyor — o da fıkhî/kavramsal bir sözlük
(hasat edilen 509 terimin yalnız `murabaha`'sı bu listeyle kesişiyor). Üç
kaynak denendi ve üçü de bu boşluğu kapatmıyor
([[tcmb-sozlugu-terim-boslugunu-kapatmiyor]]).

Ayrıca hasatta **189 id ağ hatası** aldı; kaçan terimler için tekrar koşum
yapılabilir.

## İlgili dosyalar

- `app/scripts/tkbb_sozluk_hasat.py` — hasat (509 terim, hepsi örnekli)
- `app/data/terminology/tkbb-sozluk.jsonl` — kaynak
- `app/src/domain/terminology.py` — `IKINCIL_YOL`, `_ikincil_yukle`, sayaçlar
- `app/tests/test_terminology_ikincil.py` (9 test)

## Sources

- `https://tkbb.org.tr/katilim-sozluk` — resmî kaynak, robots.txt tam izinli
- Ölçüm, 2026-08-24 — çakışma ve yasak-kök taraması

## Related

- [[tcmb-sozlugu-terim-boslugunu-kapatmiyor]] — elenen alternatif ve asıl boşluk
- [[terim-sorusuna-sozlukten-cevap-verilmiyordu]] — terim yolunun doğuşu
- [[tkbb-kar-payi-veri-seti]] — aynı kurumun oran verisi
