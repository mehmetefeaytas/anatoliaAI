---
title: "Karar: NER fine-tune yok; kural + few-shot LLM, fine-tune yalnız sınıflandırma"
tags: [decision, cikarim, ner, fine-tune]
source: "[[2026-06-16-teknofest-tyda-sartname-2-senaryo]]"
date: 2026-06-16
status: stable
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

## Sources
- [[2026-06-16-teknofest-tyda-sartname-2-senaryo]] — Değerlendirme/Model Başarısı
  (%30) ağırlığı

## Related
- [[bilgi-cikarimi]] — etkilenen yöntem
- [[metin-siniflandirma]] — fine-tune'un uygulandığı tek yer
- [[nlp]] — üst kavram
- [[teknik-cozum-mimarisi]] — mimari sentez
