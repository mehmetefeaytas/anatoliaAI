---
title: "Karar: NER fine-tune yok; kural + few-shot LLM, fine-tune yalnız sınıflandırma"
tags: [decision, cikarim, ner, fine-tune]
source: "[[2026-06-16-teknofest-tyda-sartname-2-senaryo]]"
date: 2026-06-16
status: celiskili
---

# Karar: NER fine-tune yok; kural + few-shot LLM, fine-tune yalnız sınıflandırma

**Karar:** Alan çıkarımı ([[bilgi-cikarimi]]) **kural + few-shot LLM** ile yapılır;
BERTurk/GLiNER **NER fine-tune edilmez**. Fine-tune yalnızca **8 sınıflı kampanya
türü sınıflandırıcısına** ([[metin-siniflandirma]]) uygulanır. GLiNER2 birincil
değil **tamamlayıcı** katmandır; kurallar birincildir.

**Gerekçe:** Planlanan anotasyon bütçesi 150–300 örnek. Bu hacimle NER fine-tune
**overfit** eder; aynı bütçe **gold/eval setine** ayrılırsa Model Başarısı (%30)
ölçülebilir ve ispatlanabilir olur. 8 sınıflı dengeli sınıflandırma 150–300 örnekle
yeterlidir. GLiNER2'nin Türkçe finans terimlerinde sıfır-atış performansı belirsiz
olduğundan kurallara birincil rol verilir.

**Etkileri:**
- Anotasyon emeği eval'e kayar → ablasyon tablosu güçlenir.
- [[veri-seti]] gold alt kümesi kritik artefakt olur.
- Çıkarım katmanı donanım/GPU kararından bağımsız hale gelir.

## ÇELİŞKİ

İki kaynak, çıkarımdaki LLM katmanı hakkında farklı şey söylüyor
(işaretlendi: 2026-08-21):

- **Bu karar (2026-06-16):** alan çıkarımı "kural + **few-shot LLM**" ile
  yapılır — LLM, kuralların kaçırdığı boşlukları doldurur.
  Kaynak: [[2026-06-16-teknofest-tyda-sartname-2-senaryo]] üzerine kurulan plan.
- **Ölçüm (2026-08-05 ve sonrası):** hibrit (kural + LLM) kolu kural-only
  kola karşı **kaybetti** (n=20'de 0,575 < 0,677, p = 0,01172; 20 Ağustos'ta
  40 zor belgede yeniden ölçüldü, sonuç aynı yönde) ve halüsinasyonu artırdı.
  Üretim yolu **kural-only** teslim edildi; LLM kolu kodda var ama kapalı.
  Kaynak: 2026-08-05 ablasyon kaydı (`sources/docs/2026-08-05-ablasyon.md`)
  ve `app/docs/rapor/ablasyon.md`.

Kararın "fine-tune yalnız sınıflandırmaya" ve "kurallar birincildir" kısımları
geçerli kaldı; "few-shot LLM boşluk doldurur" kısmı ölçümle yanlışlandı ve
üretimde uygulanmıyor. Karar sayfası tarihî kayıt olarak duruyor
(HARD RULE 3); güncel durumun kaynağı ablasyon raporudur.

## Sources
- [[2026-06-16-teknofest-tyda-sartname-2-senaryo]] — Değerlendirme/Model Başarısı
  (%30) ağırlığı

## Related
- [[bilgi-cikarimi]] — etkilenen yöntem
- [[metin-siniflandirma]] — fine-tune'un uygulandığı tek yer
- [[nlp]] — üst kavram
- [[teknik-cozum-mimarisi]] — mimari sentez
