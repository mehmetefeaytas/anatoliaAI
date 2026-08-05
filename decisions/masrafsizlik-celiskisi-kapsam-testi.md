---
title: "Karar: masrafsızlık çelişkisi bir kapsam testidir, ücret varlığı testi değil"
tags: [decision, celiski-tespiti, yenilikcilik, ucret, adil-kiyas]
source: "[[2026-06-16-teknofest-tyda-sartname-2-senaryo]]"
date: 2026-08-05
status: stable
---

# Karar: masrafsızlık çelişkisi bir kapsam testidir, ücret varlığı testi değil

**Karar:** Yenilikçilik hedefi #2 ("masrafsız deyip tahsis ücreti alanı yakala")
**"tarifede ücret var mı?"** sorusuyla değil, **"muafiyetin kapsamı belirtilmiş
mi?"** sorusuyla uygulanır. Kampanyanın masrafsızlık iddiası ile bankanın ilan
ettiği ücret arasındaki fark tek başına çelişki **sayılmaz**.

## Gerekçe — ölçümle

Naif tasarım şudur: kampanya "masrafsız" diyorsa ve bankanın tarifesinde tahsis
ücreti varsa, çelişki bildir. Bu tasarım ölçüldüğünde çöküyor.

`scripts/crosscheck_fees.py` korpustan **33 ilan edilmiş tahsis ücreti** kaydı
çıkardı (5 banka). Bunların **30'u tam olarak %0,5** — BDDK'nın konut finansmanı
için koyduğu üst sınır. Yani sektörde tahsis ücreti fiilen **tek fiyat**.

Sonuç: "tarifede ücret var" her banka için ve her ürün için doğrudur. Naif test
her masrafsızlık kampanyasını çelişki olarak işaretlerdi — yani **hiçbir bilgi
üretmezdi** ve dahası **meşru muafiyetleri sahtekârlık gibi gösterirdi**.
Kampanya pekâlâ standart ücretten muaf tutuyor olabilir; bu bankanın hakkı.

## Ayırt edici olan: kapsam

| sonuç | anlamı | kullanıcıya ne söylenir |
|---|---|---|
| `kosullu_muafiyet` | muafiyet bir koşulla sınırlı (yeni müşteri, tarih, tutar) | "koşul kapsamında masrafsız; aksi hâlde %0,5" |
| `kapsamsiz_iddia` | tanınan türde koşul YOK | çelişki adayı → insan hakemliği |
| `tutarli` | tarife de ücret alınmadığını söylüyor | "masrafsız" |
| `tarife_yok` | bağımsız kaynak toplanamadı | karar yok |

## Bunun ÜRÜN sonucu

`kosullu_muafiyet` bir kusur değil, **ürünün kendisidir**. Karşılaştırma
tablosunda "masrafsız" yazmak yanıltıcıdır — kullanıcı koşulu sağlamıyorsa
gerçek maliyeti %0,5'tir. Doğru çıktı koşullu ifadedir.

Bu, [[urun-karsilastirma]] adil-kıyas kuralının ücretlere uygulanmış hâli: koşullar
farklıysa doğrudan kıyaslama yapılmaz, koşul birlikte gösterilir.

## Bunun VERİ SETİ sonucu

Çelişki, gold sette `celiskili` etiketiyle **aranamaz**. Ölçüldü: 13 adayın
12'si ücret tarifesiydi, kampanya olan tek adayla birlikte belge **içi** çelişki
korpusta pratik olarak yok. İddia kampanyada, ücret bankanın **ayrı**
tarifesinde — yani bu yapısı gereği belgeler **arası** bir kontroldür ve ayrı
bir betiğe aittir, etiket taksonomisine değil.

## Sources
- `app/scripts/crosscheck_fees.py` — kararın uygulaması ve beş sıkı kapı
- `app/docs/rapor/zor-vaka-kurleme.md` §`celiskili` — kararı doğuran ölçüm
- `app/data/gold/fee_crosscheck.md` — üretilen rapor

## Related
- [[daraltilmis-yenilikcilik-hedefleri]] — hedef #2'nin kaynağı
- [[zor-anlama-vakalari-merkezi]] — negasyon ("masrafsız" ≠ bilgi yok)
- [[urun-karsilastirma]] — "En Düşük Masraf" kriterinin doğru hesaplanması
