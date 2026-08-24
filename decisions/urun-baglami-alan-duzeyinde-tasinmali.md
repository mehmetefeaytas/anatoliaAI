---
title: "Ürün bağlamı alan düzeyinde taşınmalı (belge düzeyinde tek etiket yetmiyor)"
tags: [karar, mimari, kiyas, urun-ailesi, cikarim, olcum]
source: "[[2026-08-24-ssb-evren-cikarim-servisi]]"
date: 2026-08-24
status: stable
---

# Ürün bağlamı alan düzeyinde taşınmalı

## Sorun

Belgeye **tek** bir ürün ailesi (`campaign_type`) atanıyor ve o belgeden
çıkarılan **tüm alanlar** o aileye ait sayılıyor. Çok ürünlü belgelerde bu
yanlış kıyas üretiyor.

Ölçülmüş örnek (kullanıcı raporu, 2026-08-24): `#761` bir **akademisyen
paketi** ve gerçekten konut finansmanına değiniyor (*"Konut Finansmanı'nda
tanımlanmış 5 puan indirim"*), ama aynı belgede fatura talimatı ve kart
avantajları da var. Konut finansmanı kıyasında *"Ek ödül: Kuveyt Türk 200 TL"*
satırı çıktı; o 200 TL aslında **"her bir fatura talimatı için 200 TL iade"**.
Yani kıyasın bir boyutu ilgisiz bir üründen besleniyor.

Ayrıntı: [[kiyas-cevabinda-iki-gosterim-hatasi]] (üçüncü belirti).

## Ölçüm — sorunun boyutu

[[ssb-evren-cikarim-servisi]] ile 45 belgede denetim yapıldı (kısıtlı çıktı,
`tool_calling`, 45/45 ölçülebildi):

| ölçüt | sonuç |
|---|---|
| mevcut `campaign_type` ile EVREN'in birincil ailesi uyuşuyor | 35/45 (**%78**) |
| uyuşmuyor | 10/45 (%22) |
| uyuşmayanlarda mevcut etiket EVREN'in `tum_aileler` listesinde | **5/10** |
| **EVREN'e göre ÇOK ÜRÜNLÜ** | **8/45 (%18)** |

İki okuma:

1. **Toplu yeniden etiketleme için gerekçe ZAYIF.** Uyuşmazlıkların yarısı
   gerçek hata değil — mevcut etiket EVREN'in listesinde var, EVREN yalnız
   farklı bir *birincil* seçmiş (ör. `Alışveriş Puanı` → `Yatırım Ürünü`,
   ama listede Alışveriş Puanı da var). Birincil aile seçimi ÖZNELDİR. Kalan
   5'in ikisi `Diğer` (EVREN emin değil). Gerçekten şüpheli etiket ~%7.
2. **Çok ürünlü belge oranı %18** — korpusta ≈490 belge. `#761` hatası bu
   kümede ve tek etiketle çözülemez.

## Seçenekler

**(a) Çok-etiketli belge.** `campaign_type` → `campaign_types` listesi. Kıyas
her aileye ayrı girer. Ama alanların hangi aileye ait olduğu **hâlâ belirsiz**
kalır: `#761`'de 200 TL hangi aileye yazılacak? Sorunu adlandırır, çözmez.

**(b) Alan-başına aile.** Her `extracted_fields` satırı kendi `urun_ailesi`ni
taşır. En doğru çözüm — ama tüm korpusun yeniden çıkarımını ve şema
değişikliğini gerektirir. Ayrıca çıkarım kolunun kalitesi ölçülmüş biçimde
kural hattının altında (bkz. `app/docs/evren-servisi.md` §3-c, §9), yani bu
işi LLM'e yüklemek riskli.

**(c) Kanıt penceresi kontrolü — ÖNERİLEN ilk adım.** Kıyasta kullanılan her
satır zaten `source_span` taşıyor. Span, kıyasın yapıldığı ürün ailesinin
adını hiç içermiyorsa satır **işaretlenir** (dışlanmaz). `#761` örneğinde
`odul_miktari` span'i *"her bir fatura talimatı için 200 TL iade"* — içinde
"konut" yok.

(c) neden ilk adım: ek veri, şema değişikliği ve yeniden çıkarım
gerektirmiyor; mevcut alanla (`source_span`) çalışıyor; ve projenin kuralına
uyuyor — sessiz hata yerine AÇIK işaret. Ölçülebilir: kaç satır işaretlenir,
işaretlenenler gerçekten ilgisiz mi.

## Karar

**(c) uygulanacak ve ölçülecek.** (b) ancak (c)'nin ölçümü yetersiz kalırsa ve
çıkarım kolunun kalitesi ayrıca düzelirse gündeme gelir. (a) tek başına
sorunu çözmediği için elenmiştir.

### (c) UYGULANDI ve ölçüldü

`_cok_urunlu_mu` (kural tabanlı: farklı ürün ailesi adı deseni sayımı) ve
`_cok_urunlu_uyarisi` yazıldı, `_phrase_ustunluk_kiyasi`'a bağlandı. Artık
kıyas cevabının sonuna şu not düşüyor:

> Not: #761 çok ürünlü belge(ler) — birden fazla ürün ailesinden avantaj
> içeriyor ve alanların hangi ürüne ait olduğu belge düzeyinde
> AYRIŞTIRILMIYOR. Bu satırlardaki değer başka bir ürünün avantajı olabilir;
> kaynağa bakmanız önerilir.

Belge **dışlanmıyor** — `#761` gerçekten konut finansmanına değiniyor ve onu
atmak bilgi kaybı olurdu.

Doğrulama (iki bilinen vaka): `#761` → 2 aile (Kart + Konut Finansmanı) ✓
işaretlenir; `#626` → 1 aile ✓ işaretlenmez.

### KAPSAM AÇIĞI KAPATILDI (2026-08-24, ölçüldü)

Desen listesi 6 → 9 aile çıkarıldı ve oran **%13,2 → %18,0** oldu — EVREN'in
bağımsız denetimiyle (%18) **birebir**. İki bağımsız yöntemin aynı sayıya
varması, listenin korpusun gerçek ürün çeşitliliğini kapsadığına işaret ediyor.

Eklenen üç DAR desen: `Fatura/Ödeme Talimatı` (%6,3), `Sigorta/Tekafül`
(%4,1), `Döviz/Kıymetli Maden` (%1,3). İlki ölçülmüş bir vakayı kapatıyor:
`#761` artık 2 değil **3** aile taşıyor (fatura talimatı yakalandı).

GENİŞ desenler ölçülüp **elendi**: altı adayın tamamı eklendiğinde oran
**%32,5** — EVREN ölçümünün iki katı, yani aşırı işaretleme. `\bpos\b|üye
işyeri` tek başına korpusun %23,2'sinde geçiyor; `havale` %8,0 (her banka
sayfasında ücret tablosu olarak); `maaş müşterisi` %0,2 (etkisiz).

Test: `test_kiyas_cok_urunlu_uyarisi.py::TestGenisletilmisAileListesi` (5 test)
elenen desenlerin geri sızmamasını da kilitliyor.

**Eski ölçüm (tarihsel kayıt):** kural korpusta **%9** çok ürünlü
buluyordu, EVREN denetimi **%18** diyordu. Yani kural EVREN'in yarısını yakalıyor;
desen listesi 6 aile içeriyor, korpusta 8 var ("Finansman" ve "Yeni Müşteri"
çok genel oldukları için bilerek dışta). Kaçan ~%9 için ya desen listesi
genişletilmeli ya EVREN ile tam korpus taraması yapılıp sonuç bir kolona
yazılmalı (tek seferlik üretim adımı, ≈40 dk).

Testler: `app/tests/test_kiyas_cok_urunlu_uyarisi.py` (7 test).

**(b) hâlâ açık:** alan-başına aile en doğru çözüm ama çıkarım kolunun
kalitesi ölçülmüş biçimde kural hattının altında; o iş ancak çıkarım kalitesi
düzelirse gündeme gelir.

## Sources

- Kullanıcı raporu, 2026-08-24 — `#761` üzerinden görülen yanlış kıyas boyutu
- [[2026-08-24-ssb-evren-cikarim-servisi]] — 45 belgelik etiket denetimi
- `data/demo.db` — `#761` (akademisyen paketi), `campaign_type` dağılımı

## Related

- [[kiyas-cevabinda-iki-gosterim-hatasi]] — aynı raporun düzeltilen iki hatası
- [[ssb-evren-cikarim-servisi]] — denetimi yapan servis
- [[bilgi-cikarimi]] — alan çıkarımının kavramsal zemini
