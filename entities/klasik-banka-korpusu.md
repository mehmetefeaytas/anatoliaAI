---
title: "Klasik Banka Korpusu (data/raw-classic) — YARIŞMA KAPSAMI DIŞI"
tags: [entity, veri, artifact, kapsam-disi, gumus-veri]
source: "[[2026-06-16-teknofest-tyda-sartname-2-senaryo]]"
date: 2026-08-07
status: stable
---

# Klasik Banka Korpusu (`data/raw-classic`)

> ⛔ **YARIŞMA KAPSAMI DIŞI.** Bu korpus TEKNOFEST veri setinin parçası
> **değildir** ve değerlendirmeye (gold/eval) **girmez**. Yarışma korpusu için
> bkz. [[veri-seti]] (`app/data/raw`).

Türkiye'deki **klasik (konvansiyonel, katılım bankacılığı yapmayan)** 11
bankanın resmî sitelerinden toplanmış kampanya/ürün metinleri korpusu:
Akbank, DenizBank, Garanti BBVA, Halkbank, ING, İş Bankası, QNB, TEB,
VakıfBank, Yapı Kredi, Ziraat Bankası.

## Ölçülmüş nicelikler

| Nicelik | Değer | Ölçüm |
|---|--:|---|
| Belge (`.txt`) | 724 | `find app/data/raw-classic -name '*.txt' \| wc -l` |
| Provenance (`.meta.json`) | 724 | aynı komut, `*.meta.json` |
| Depoda izlenen dosya | 1461 | `git ls-files data/raw-classic \| wc -l` |
| Banka | 11 | `data/raw-classic/*/` |
| Toplama tarihi | 2026-08-04 (tek tur) | 724 `.meta.json` dosyasının tamamında `scraped_at` = `2026-08-04` |

Karşılaştırma: yarışma korpusu ([[veri-seti]], `app/data/raw`) **1759 kazınmış
belge + 2 demo fikstürü**, 10 katılım bankası.

## Neden var — tek meşru kullanım

Toplama gerekçesi `app/config/banks-classic.yaml` başındaki "NE İÇİN VAR"
bloğunda kayıtlıdır. Şartname §5.1 veri setinin BDDK ([[bddk]]) katılım
bankalarının **tümünü içermesini** ister; bu bir **taban**dır, tavan değil.
Klasik bankalar o tabanın dışında, ek amaçla toplanmıştır.

Korpusun tek meşru kullanımı **8-sınıf kampanya türü sınıflandırıcısı için
gümüş (silver) eğitim verisi** üretmektir → 505 kayıtlık gümüş küme
(`app/data/silver/silver.jsonl`; 608 öneriden 505 gümüş, 100 reddedildi —
`silver_report.json`). Aktarılması istenen şey **ürün ailesi yapısı**dır
(Konut / Taşıt / İhtiyaç Finansmanı), **terminoloji değildir**.

İkincil faydalar: terminoloji ayrımı testi için *minimal pair* seti (Ziraat
Bankası ↔ Ziraat Katılım, VakıfBank ↔ Vakıf Katılım, Halkbank ↔ Emlak Katılım —
aynı kurumsal üslup, aynı ürün, farklı sözlük) ve halüsinasyon negatif testi
(klasik banka sayfasında model `kar_payi_orani` **üretmemeli**).

## Kapsam dışılık — ne YAPILMAZ

- Yarışma veri seti olarak **sunulmaz**.
- Altın (gold) kümeye **girmez** (`app/data/gold/gold.v1.json` yalnızca katılım
  bankası belgelerinden derlenmiştir).
- Değerlendirme metriklerine (P/R/F1, macro-F1, Cohen κ, normalizasyon
  doğruluğu) **etki etmez**.
- **Terminoloji aktarımı için kullanılmaz** — terminolojiyi modelin kendisinin
  aktarması beklenir; sınavın konusu tam olarak budur.

`scripts/build_silver.py` bu ayrıklığı çalışma anında duyurur: gümüş küme ile
gold kümenin kesişimi **sıfır** çıktığında betik "Bu bir kusur değil, TASARIM"
mesajını basar ve ölçümün Faz 3'te, ince ayarlı sınıflandırıcının gold
üzerindeki macro-F1'i ile yapılacağını söyler.

## Ölçülmüş terim dağılımı — ayrıklığın kanıtı

Belge kapsama oranı (terimi en az bir kez içeren belge / toplam belge), sıklık
değil. Her `.txt` küçük harfe indirilip alt dizge araması yapıldı (ölçüm:
2026-08-07, `.venv/bin/python`).

| Terim | Klasik korpus (724 belge) | Katılım korpusu (1759 kazınmış belge) |
|---|--:|--:|
| `faiz` | **%70,2** (508) | **%7,3** (128) |
| `kâr payı` / `kar payı` | %0,3 (2) | **%18,1** (319) |
| `murabaha` | %0,0 (0) | %1,8 (31) |
| `sukuk` | %0,0 (0) | %2,3 (40) |
| `katılma hesabı` | %0,0 (0) | %11,6 (204) |
| Fıkhî terim (birleşik) | **%0,0 — sıfır belge** | — |

İki korpus terminoloji açısından tam ters kutuptadır. Klasik korpusun **hiçbir**
belgesinde fıkhî terim (murabaha, icara, mudarebe, muşareke, karz-ı hasen,
sukuk, katılma hesabı, tekafül) geçmez. Bu, klasik korpusun terminoloji
öğretemeyeceğinin kanıtıdır — ve tam da bu yüzden terminoloji aktarımı
**sınanabilir** bir hipotez hâline gelir. Terminoloji farkının kendisi için bkz.
[[katilim-bankaciligi-terminoloji-farkliligi]] ve [[kar-payi-orani]].

## Tasarımın özü

**Gümüş hat klasik veride EĞİTİR, altın hat katılım verisinde ÖLÇER.**
İki küme kasten ayrıktır (`app/CLAUDE.md §12 — Domain Bilgisi: Faizsiz Finans`;
`scripts/build_silver.py` bu bölüme atıf yapar). Amaç, sınıflandırıcının
terminolojiyi aktarıp aktaramadığını gerçekten sınamaktır — kesişimli bir küme
bu sınavı imkânsız kılardı.

## Sources
- `app/config/banks-classic.yaml` — "NE İÇİN VAR" + "TERMİNOLOJİ AYRIMI" +
  "ÖLÇÜM NOTLARI" blokları (toplama gerekçesi, robots.txt doğrulaması)
- `app/scripts/build_silver.py` — satır 254-267 (sıfır kesişim = tasarım),
  278/283/289 (varsayılan `--docs data/raw-classic`)
- `app/scripts/split_trainable.py` — satır 5-10 ("Bu araç ne YAPMAZ": kapsam
  dışılık beyanı), 883 (varsayılan kök)
- `app/data/raw-classic/README.md` — kapsam dışı uyarısı + tam ölçüm tablosu
- `app/data/raw-classic/_collection_report.md` — otomatik toplama raporu
- `app/data/silver/silver_report.json` — 505 gümüş / 100 red / 608 öneri
- `app/data/silver/split_report.md` — eğitilebilirlik ayrımı
- `app/CLAUDE.md` §4 (fine-tune yalnız sınıflandırma), §12 (faizsiz finans
  terminolojisi)
- [[2026-06-16-teknofest-tyda-sartname-2-senaryo]] — Veri Toplama (s.6): veri
  seti kapsamı tabanı

## Related
- [[veri-seti]] — **kapsam İÇİ** yarışma korpusu (`app/data/raw`); bu sayfanın
  karşıtı
- [[katilim-bankalari]] — kapsam içi bankalar; bu korpustaki bankalar o listede
  **yoktur**
- [[bddk]] — kapsam tabanını tanımlayan liste (Liste 77)
- [[katilim-bankaciligi-terminoloji-farkliligi]] — bu korpusun ölçtüğü sorun
- [[kar-payi-orani]] — klasik korpusta %0,3, katılım korpusunda %18,1
- [[kampanya-turleri]] — gümüş kümenin ürettiği 8 sınıf etiketi
- [[metin-siniflandirma]] — gümüş kümenin beslediği görev
- [[web-scraping]] — toplama tekniği
- [[ner-fine-tune-yerine-kural-few-shot]] — fine-tune yalnız sınıflandırma
  kararı; gümüş kümenin var olma sebebi
- [[klasik-veri-ince-ayar-rag-reddi]] — aynı ölçümlere dayanan karar: bu korpusun
  LLM ince ayarı ve RAG kaynağı olarak kullanılması **reddedildi**; gümüş
  eğitimdeki kullanımı geçerli kalır
