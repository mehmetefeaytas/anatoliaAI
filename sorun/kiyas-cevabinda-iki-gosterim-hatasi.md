---
title: "Kıyas cevabında iki gösterim hatası: yanlış birim ve sessiz yön"
tags: [sorun, chatbot, kiyas, gosterim, birim, yon]
source: "kullanıcı raporu (2026-08-24, canlı chatbot çıktısı)"
date: 2026-08-24
status: stable
---

# Kıyas cevabında iki gösterim hatası

İki hata aynı kullanıcı raporundan çıktı: *"Hangi bankada en düşük konut
finansmanı var"* sorusunun canlı cevabı. Kök nedenleri ayrı, cevap yüzeyi aynı.

---

## Hata 1 — vade `%120` olarak basılıyordu (yanlış birim)

### Belirti

KAYNAKLAR tablosunda `kuveyt-turk %120` ve `albaraka %120` satırları. Gerçek
değer **120 AY vade**; yüzde değil.

### Kök neden

Bileşik "en avantajlı" cevabı satırlarını **boyut boyut** toplar:

```python
for field in _KIYAS_BOYUTLARI:            # vade, masraf, ödül…
    gosterilen.extend([x for x in grup if x.comparable][:2])
```

Ama `RankRow` hangi alandan geldiğini **taşımıyordu** ve `bot.py` kaynak
sözlüğüne de konmuyordu. Arayüz her satırı zorunlu olarak SORGUNUN alanıyla
biçimliyordu:

```tsx
formatValue(s.value, cevap.field ?? undefined)   // cevap.field = kar_payi_orani
```

`kar_payi_orani` bir oran alanı olduğu için `120` → `%120`.

**Hata neden bu kadar geç görüldü:** seçiciydi. Masraf (`{"has_fee": …}`) ve
ödül (`{"value": …, "currency": …}`) değerleri **sözlük** dallarına düşüyor ve
o dallar alan adına hiç bakmıyor — bu yüzden `masrafsız` ve `200 TL` doğru
görünüyordu. Hata yalnız **çıplak sayısal** alanlarda ortaya çıkıyordu.

### Çözüm

Zincirin tamamı: `RankRow.field` eklendi (opsiyonel, geriye uyumlu) →
bileşik kıyasta `replace(x, field=field)` ile damgalanıyor → `bot.py` kaynak
sözlüğü `"field": x.field` taşıyor → `ChatPanel.tsx` satırın KENDİ alanını
kullanıyor, `cevap.field` yalnız alan taşımayan eski yanıtlar için yedek.

Testler: `tests/test_chat_kaynak_alan_bilgisi.py` (5 test). Biçimleme
testleri hatayı da kayda geçiriyor: `_fmt_value("kar_payi_orani", 120)` →
`"%120"`, `_fmt_value("vade_ay", 120)` → `"120 ay"`.

---

## Hata 2 — "en düşük" ile "en yüksek" AYNI cevabı veriyordu (sessiz yön)

### Belirti

İki soru ayrı ayrı soruldu ve **aynı** cevap geldi:

```
"Hangi bankada en DÜŞÜK konut finansmanı var"   → en avantajlı: Kuveyt Türk
"Hangi bankada en YÜKSEK konut finansmanı var"  → en avantajlı: Kuveyt Türk
```

### Kök neden

Birincil alan (`kar_payi_orani`) o ailede kıyaslanabilir değil — ve bu bir veri
gerçekliği: Albaraka sayfasında kâr payı oranı **değeri yayınlanmıyor**
(metinde *"Rekabetçi ve düşük kar payı oranlarıyla"* var ama sayı yok; ödeme
planı tablosundaki "Kâr Payı" kolonu tutar, oran değil). Kural hattı
kaçırmamış.

Alan kıyaslanamaz olunca sistem çok boyutlu **bileşik skora** düşüyor ve
bileşik skor **tek yönlüdür** (yüksek skor = daha avantajlı). Yön böylece
uygulanamıyor.

Düşmenin kendisi doğru davranıştır; **söylenmemesi** yanlıştı. Kullanıcı "en
düşük" diye sordu ve yönünün yok sayıldığını bilmiyordu — bu, cevabı
yanıltıcı yapar. Oysa bu modülün kuralı zaten şu: kıyaslanamayan boyut
sessizce düşmez, SÖYLENİR.

### Çözüm

`_yon_uyarisi(intent, bilesige_dusuldu=...)` eklendi ve
`_phrase_ustunluk_kiyasi` sonunda çağrılıyor. Artık şu not düşüyor:

> «en düşük» yönü bu ailede UYGULANAMADI — sorulan boyut kıyaslanabilir
> olmadığı için çok boyutlu bileşik skora düşüldü ve bileşik skor tek
> yönlüdür (yüksek skor = daha avantajlı). Tek bir boyutta en düşük sıralama
> için alan adını yazın.

Yön istenmemişse (liste/süzme niyeti) ya da yön gerçekten uygulandıysa uyarı
basılmaz — o durumda gürültü olurdu.

Testler: `tests/test_chat_yon_uyarisi.py` (6 test + 4 alt test).

---

## Üçüncü belirti — DÜZELTİLMEDİ, ölçülüyor

Aynı cevapta `kuveyt-turk 200 TL` satırı vardı ve kaynağı *"her bir fatura
talimatı için 200 TL iade"* — konut finansmanıyla ilgisiz.

Kök neden farklı ve mimari: belge `#761` bir **akademisyen paketi** ve
gerçekten konut finansmanına değiniyor (*"Konut Finansmanı'nda tanımlanmış 5
puan indirim"*), ama aynı belgede fatura ve kart avantajları da var. Belgeye
**tek** ürün ailesi atanıyor ve o belgeden çıkarılan **tüm alanlar** o aileye
ait sayılıyor. Yani alanlar **ürün bağlamı taşımıyor**.

Bu, [[urun-baglami-alan-duzeyinde-tasinmali]] başlığı altında ayrıca
değerlendiriliyor; çok ürünlü belge oranı EVREN ile ölçülüyor.

## İlgili dosyalar

- `app/src/comparison/compare.py` — `RankRow.field`
- `app/src/chatbot/structured.py` — `replace(x, field=field)`, `_yon_uyarisi`
- `app/src/chatbot/bot.py` — kaynak sözlüğünde `field`
- `app/web/app/components/ChatPanel.tsx` — satırın kendi alanıyla biçimleme
- `app/tests/test_chat_kaynak_alan_bilgisi.py` · `test_chat_yon_uyarisi.py`

## Sources

- Kullanıcı raporu, 2026-08-24 — iki canlı chatbot çıktısı
- `data/demo.db` — `#626` (vade 120, oran 1,89), `#1212` (oran YOK), `#761`

## Related

- [[ssb-evren-cikarim-servisi]] — üçüncü belirtinin ölçümünde kullanıldı
- [[bilgi-cikarimi]] — kıyasın dayandığı kavram
