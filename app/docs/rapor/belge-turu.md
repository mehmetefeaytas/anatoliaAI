---
title: "Sözleşme belgeleri kıyastan çıkarıldı — `belge_turu` alanı"
tags: [veri-modeli, kiyas, teknik-borc, sema]
date: 2026-08-07
status: stable
---

# `belge_turu`: akit metni kıyasa girmemeli, erişimde kalmalı

## Sorun

Korpustaki her `.txt` belgesi `campaigns` tablosuna **kampanya** olarak
yazılıyordu. Ama korpusun bir kısmı kampanya değil, **akit** (sözleşme,
tarife, ön bilgilendirme formu) metni.

Fark önemsiz değil: bir sözleşmedeki *"vade 36 ayı aşamaz"* ifadesi bir
teklif değil, bir üst sınır. Kıyas tablosuna girdiğinde bankanın "36 ay vade
veriyor" gibi görünmesine yol açıyor. Aynı belgedeki bir oran da bir kampanya
teklifi değil, akdin genel çerçevesi.

## Ölçüm

| | belge |
|---|---|
| toplam kampanya kaydı | **1761** |
| `belge_turu = 'kampanya'` | **1648** |
| `belge_turu = 'sozlesme'` | **113** (%6,4) |
| sınıflandırılamayan (`NULL`) | **0** |

**Sözleşme kayıtlarından en az bir kıyaslanabilir alan (oran / vade / tutar)
taşıyan: 41 belge.** Bunlar bugüne kadar karşılaştırma tablosuna giriyordu.

Sözleşme kayıtlarındaki alan dağılımı — yani kıyastan çıkanlar:

| alan | kayıt |
|---|---|
| `kampanya_kosullari` | 98 |
| `masraf_durumu` | 84 |
| `vade_ay` | 36 |
| `kampanya_suresi` | 25 |
| `finansman_tutari` | 15 |
| `hedef_kitle` | 15 |
| `kar_payi_orani` | 15 |
| `odul_miktari` | 13 |
| `taksit_sayisi` | 5 |
| `tahsis_ucreti` | 4 |
| `indirim_orani` | 1 |

Banka dağılımı: Türkiye Emlak Katılım 40 · Kuveyt Türk 40 · Ziraat Katılım
16 · Albaraka 15 · Dünya Katılım 2. Diğer beş bankada sözleşme PDF'i yok —
bu bir veri toplama farkıdır, o bankaların sözleşmesi olmadığı anlamına
gelmez.

Kıyas sayılarına yansıması (`build_demo_db` raporundan):

| alan | ham | kıyasta | fark |
|---|---|---|---|
| `masraf_durumu` | 626 | 542 | −84 |
| `kar_payi_orani` | 70 | 55 | −15 |
| `finansman_tutari` | 303 | 288 | −15 |
| `hedef_kitle` | 387 | 372 | −15 |
| `odul_miktari` | 397 | 384 | −13 |

## Kural — ve ölçülen bir sürpriz

Beklenen kural "`docs` bölümü **veya** `.pdf` uzantısı" idi. Ölçüm daha
keskin çıktı:

- Sözleşme sayılan **113 belgenin 113'ü** `.pdf`.
- Kampanya sayılan **1648 belgenin 0'ı** `.pdf`.

Yani ayrım fiilen **tek bir sinyale** dayanıyor: kaynak URL'sinin PDF olması.
`docs` bölümü ölçütü ayrıca bir belge kazandırmıyor. Üstelik korpusta `docs`
bölümü **112** dosya taşıyor ama sözleşme sayısı **113** — yani en az bir PDF
`docs` dışında duruyor ve uzantı ölçütü onu yakalıyor, bölüm ölçütü
yakalayamazdı.

Bu, kuralın bölüm yerleşimine değil belgenin kendisine dayandığı anlamına
gelir; korpus yeniden düzenlense de ayrım bozulmaz.

**Sınırı da yazmak gerekir:** ölçüt PDF olmaktır, "akit metni olmak" değil.
Bir banka kampanya broşürünü PDF olarak yayınlarsa sözleşme sayılır ve
kıyastan yanlışlıkla düşer. Bugünkü korpusta böyle bir vaka yok (113/113
gerçekten akit/tarife metni), ama korpus büyürse bu ölçüt yeniden
sınanmalıdır. Sınıflandırılamayan belge için kural `NULL` bırakır, uydurma
sınıflandırma yapmaz (CLAUDE.md §19).

## Ayrım: kıyas süzer, erişim süzmez

| yol | `belge_turu` süzmesi | gerekçe |
|---|---|---|
| Karşılaştırma / kıyas tablosu | **yalnız `kampanya`** | akit metni teklif değildir |
| RAG / chatbot | **süzmez** | kullanıcı "sözleşmede ne yazıyor" diye sorabilmeli |

Sözleşme metnini korpustan atmak yanlış olurdu: fıkhî terim yoğunluğunun en
yüksek olduğu bölüm `docs` (%39,3) ve RAG terim kapsamasının 14/15'e
çıkmasının kaynağı orası. Belge erişimde kalır, yalnız kıyasa girmez.

## Uygulama

Şema göçü yeniden icat edilmedi:

- SQLite — `src/db/repository.py` `_SONRADAN_EKLENEN` tuple'ı + `_migrate()`,
  `PRAGMA table_info` ile idempotent kontrol yapıyor (`ADD COLUMN` idempotent
  değildir).
- PostgreSQL — `src/db/postgres.py` `_migrate()`, `ADD COLUMN IF NOT EXISTS`.
- Kanonik şema `src/db/schema.sql` ve `_SQLITE_SCHEMA` birlikte güncellendi.

Aynı göçte `ozet TEXT` sütunu da açıldı (LLM üretimi özet, ayrı katman).

## Tekrar üretim

```bash
.venv/bin/python -m scripts.build_demo_db --force --json-report data/eval/demo-db-rapor.json
.venv/bin/python -m scripts.check_demo_db          # GÜNCEL (1761/1761)
```

## Sources
- `data/eval/demo-db-rapor.json` — kıyas sayıları
- `src/db/repository.py`, `src/db/postgres.py`, `src/db/schema.sql`

## Related
- [[rag-terim-kapsama]] — `docs` bölümünün erişimdeki değeri
- [[yapilacaklar]] — 5.1 teknik borcu bu belgeyle kapandı
