"""Uzlaştırma (reconciliation) — 3 katmanı tek alan kümesinde birleştirir.

İlgili: ../../decisions/ner-fine-tune-yerine-kural-few-shot.md (kurallar BİRİNCİL)
        ../../syntheses/teknik-cozum-mimarisi.md
        CLAUDE.md §3

Kural: kural çıktısı varsa onu tercih et → boşlukları LLM ile doldur → her alana
confidence + source_span. Alan hiçbir katmanda yoksa üretilmez (null + uydurma yok).

## Doğrulama modu (`verify_low_conf`) — neden eklendi

Varsayılan akışta LLM'e YALNIZCA kuralların bulamadığı alanlar sorulur. Bunun
sessiz bir sonucu var: **kural katmanı yanlış bir değer üretirse LLM onu asla
düzeltemez**, çünkü o alan hiç sorulmaz. Regex'in emin olmadığı yerde
(tetikleyici uzak, birden çok aday, değer makul aralığın dışında —
`rules/confidence.py`) hata olasılığı en yüksektir ve tam orada ikinci bir göz
yoktur.

`verify_low_conf > 0` verildiğinde, güveni eşiğin ALTINDA kalan kural alanları
da LLM'e sorulur ve yalnız o alanlar için katman önceliği gevşetilir: kazanan
güvene göre seçilir. Diğer alanlarda kural mutlak üstünlüğünü korur.

Varsayılan **0.0**'dır — yani davranış birebir eskisi gibi kalır. Bu bir
deney anahtarıdır: ablasyonda "doğrulamalı hibrit" ayrı bir satır olarak
ölçülür, kanıtlanmadan varsayılan yapılmaz.

### KARAR (2026-07-31): özellik KORUNDU, iddia GERÇEK yapıldı

Yukarıdaki "ablasyonda ayrı satır olarak ölçülür" cümlesi bir süre **yalandı**:
`eval/ablation.py` `reconcile()`'ı varsayılan `verify_low_conf=0.0` ile
çağırıyordu ve hiçbir çağıran bu anahtarı açmıyordu. Yani ölçülmeyen bir
özelliğin ölçüldüğü iddia ediliyordu — ölü kod artı yanlış belge.

İki seçenek vardı: özelliği KALDIRMAK ya da iddiayı GERÇEK yapmak. **İkincisi
seçildi**, üç gerekçeyle:

1. Kapattığı hata sınıfı gerçek ve artık ölçülebilir: kural katmanı YANLIŞ bir
   değer ürettiğinde varsayılan akışta o alan LLM'e hiç sorulmaz, dolayısıyla
   hata asla düzeltilemez. `eval/run_eval.py` bu hatayı artık `fp_wrong` olarak
   ayrı sayıyor — yani kolun kazanç payı doğrudan gözlemlenebilir hâle geldi.
   Kaldırsaydık, ölçme imkânı doğduğu anda özelliği atmış olurduk.
2. Kaldırmak `_wins(relaxed=...)` mantığını ve mevcut testlerini
   (`tests/test_llm_client.py`) de silmek demekti; kanıt üretmeden özellik
   silmek, kanıt üretmeden özellik eklemek kadar keyfîdir.
3. Maliyeti sıfıra yakın: varsayılan 0.0 olduğu için ÜRETİM yolu değişmez.

Uygulama: `eval/predictors.py` içinde `hibrit-verify` konfigi (eşik
`DEFAULT_VERIFY_THRESHOLD = 0.75`) ve `eval/ablation.py` `DEFAULT_ARMS`
listesinde dördüncü kol. LLM açıkken (`LLM_BACKEND=vllm|ollama`) ablasyon bu
kolu `hibrit` ile McNemar testiyle karşılaştırır; LLM kapalıyken kol
"ÖLÇÜLMEDİ" yazılır ve sahte satır üretilmez.

Eşik, ablasyonda kanıtlanmadan varsayılan hâline GETİRİLMEYECEKTİR.
"""

from __future__ import annotations

from typing import Optional

from ..schemas import Campaign, ExtractedField, Extractor
from .llm.extractor import LLMExtractor, NullLLMExtractor
from .llm.schema import EXTRACTION_FIELDS
from .rules.extract import extract_all as rule_extract

# Katman önceliği: kural > ner > llm (eşit güvende kural kazanır)
_PRIORITY = {Extractor.RULE: 3, Extractor.NER: 2, Extractor.LLM: 1}


def reconcile(text: str, llm: Optional[LLMExtractor] = None,
              verify_low_conf: float = 0.0) -> list[ExtractedField]:
    """Kural + (varsa) LLM çıktısını birleştirir.

    1) Kuralları çalıştır (birincil).
    2) Eksik alanları belirle; `verify_low_conf > 0` ise güveni eşiğin altındaki
       kural alanlarını da listeye ekle. LLM'e yalnız bu alanları sor.
    3) Aynı alan birden çok katmanda varsa öncelik + güvene göre seç. Doğrulama
       için sorulan alanlarda öncelik GEVŞER (bkz. modül başlığı).

    Args:
        verify_low_conf: [0, 1]. 0.0 = kapalı (varsayılan, eski davranış).
    """
    llm = llm or NullLLMExtractor()

    by_field: dict[str, ExtractedField] = {}
    for f in rule_extract(text):
        if f.is_present:
            by_field[f.field_name] = f

    missing = [name for name in EXTRACTION_FIELDS if name not in by_field]

    # Doğrulama modu: düşük güvenli KURAL alanları da sorguya dahil edilir.
    verify: set[str] = set()
    if verify_low_conf > 0:
        verify = {name for name, f in by_field.items()
                  if f.extractor is Extractor.RULE and f.confidence < verify_low_conf}

    ask = missing + sorted(verify)
    if ask and llm.available:
        for f in llm.extract(text, ask):
            if not f.is_present:
                continue
            cur = by_field.get(f.field_name)
            if cur is None or _wins(f, cur, relaxed=f.field_name in verify):
                by_field[f.field_name] = f

    return list(by_field.values())


def _wins(new: ExtractedField, cur: ExtractedField, relaxed: bool = False) -> bool:
    """Yeni alan mevcut olanı geçer mi?

    Normalde önce katman önceliği, sonra güven. `relaxed=True` (doğrulama modu)
    ise öncelik atlanır ve yalnız güven karşılaştırılır — bu, LLM'in düşük
    güvenli bir kural değerini düzeltebilmesinin tek yoludur.
    """
    if relaxed:
        return new.confidence > cur.confidence
    pn, pc = _PRIORITY[new.extractor], _PRIORITY[cur.extractor]
    if pn != pc:
        return pn > pc
    return new.confidence > cur.confidence


def build_campaign(text: str, bank_slug: str, source_url: Optional[str] = None,
                   llm: Optional[LLMExtractor] = None,
                   campaign_type: Optional[str] = None,
                   verify_low_conf: float = 0.0) -> Campaign:
    """Metinden tam Campaign nesnesi üretir (çıkarım + uzlaştırma)."""
    fields = reconcile(text, llm=llm, verify_low_conf=verify_low_conf)
    return Campaign(
        bank_slug=bank_slug,
        raw_text=text,
        source_url=source_url,
        campaign_type=campaign_type,
        fields=fields,
    )
