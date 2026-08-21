"""`/scoring` — sözelleştirme: "neden bu sıra?" sorusunun Türkçe cevabı.

`routers/kiyas.py`'den ayrıldı (21 Ağu 2026). Uç gövdesi ve **docstring'i**
BİREBİR taşındı; davranış değişikliği yok.

## Niçin AYRI bir modül

Bu uç **hiçbir şey hesaplamaz.** Gövdesinin tamamı iki şeyden oluşur:
sıralamayı `/compare`'den aynen alması ve o sıralamanın nasıl kurulduğunu
beş adımlık bir ANLATIYA çevirmesi. Yani sorumluluğu sözelleştirmedir
(cevap metni üretimi), sıralama değil.

Bu ayrım somut bir sonuç doğuruyor: adım metinleri **editoryal** nedenlerle
değişir (bir eşik yeniden ölçüldü, bir gerekçe daha iyi yazıldı), sıralama
kodu ise **davranışsal** nedenlerle. İkisini aynı dosyada tutmak, bir yazım
düzeltmesini sıralama kodunun diff'ine karıştırmak demekti — ve bu uç
tarihinde tam olarak bunun bedelini ödedi: docstring'i ve `composite_note`'u
bir dönem *"kod tabanında ağırlıklı bileşik skor yoktur"* diyordu, oysa
`compare.py` onu taşıyor ve test ediyordu. **Uç kendi kodunu yalanlıyordu.**
Metin ayrı bir modülde durduğunda, o metnin kodla uyumu ayrıca gözden
geçirilebilir bir şey oluyor.

## Niçin `/compare`'i çağırıyor

Sıralama tek doğruluk kaynağından gelsin diye kendi tablosunu kurmuyor.
Bağımlılık artık cephede AÇIKÇA bağlanıyor (`compare=` parametresi); eskiden
`router_kur` içinde iki closure arasındaki örtük bir bağdı.
"""

from __future__ import annotations

from typing import Any, Callable, Optional

from ...comparison.compare import ASGARI_GUVEN, weight_manifest
from ..sabitler import FIELD_LABELS
from ..yardimcilar import scoring_direction


def uc_ekle(r: Any, *, compare: Callable[..., list[dict]]):
    """`/scoring`'i `r`'ye kaydeder.

    `compare` uç FONKSİYONUDUR (HTTP isteği değil): `/compare` ile aynı
    süreçte, aynı kapılardan geçen aynı sıralama. Ayrı bir HTTP çağrısına
    çevirmek ya da üçüncü bir ortak katman kurmak, aynı kararı iki yerde
    yaşatmak olurdu.
    """
    @r.get("/scoring")
    def scoring(field: str, type: Optional[str] = None):
        """Şeffaf skorlama: TEK ALAN sıralamasının formülü + ara değerleri.

        Bu uç **tek alanlı** sıralamayı açıklar; iki adımdan oluşur:
          1) `_numeric_key(value)` → (sort_key, comparable, note)
          2) yön = alan `_LOWER_IS_BETTER` mi `_HIGHER_IS_BETTER` mi

        DÜZELTME (2026-08-08): bu docstring ve `composite_note` eskiden
        *"kod tabanında ağırlıklı bileşik skor **yoktur**"* diyordu. Yanlıştı —
        `compare.py` `DEFAULT_WEIGHTS`, `WEIGHT_RATIONALE`, `_composite_numeric`,
        `rank_advantageous` ve `weight_manifest`'i **taşıyor ve test ediyordu**;
        yalnız hiçbir uçtan çağrılmıyordu. Yani uç kendi kodunu yalanlıyordu ve
        jüri kodu okusa bunu görürdü.

        Bileşik skor artık `GET /advantageous` ile sunuluyor; ağırlıklar
        `composite_weights` alanında gerekçeleriyle döner. Ağırlıklar bir
        **ürün kararıdır**, ölçümden türetilmiş sabit değildir — bu ayrım
        `WEIGHT_RATIONALE`de açıkça yazılıdır.
        """
        direction, direction_label = scoring_direction(field)
        rows = compare(field=field, type=type)  # aynı sıralama, tek doğruluk kaynağı
        return {
            "field": field,
            "label": FIELD_LABELS.get(field, field),
            "direction": direction,
            "direction_label": direction_label,
            "formula_source": "src/comparison/compare.py",
            "steps": [
                {"no": 1, "name": "Kanonik değer",
                 "detail": "Ham ifade normalize edilir (oran→float, para→"
                           "{value,currency}, vade→ay)."},
                {"no": 2, "name": "Sıralama anahtarı (sort_key)",
                 "detail": "compare._numeric_key(): sayı→kendisi, para→value, "
                           "masraf→amount (yoksa 0), aralık→min ve "
                           "comparable=False."},
                {"no": 3, "name": "Güven kapısı",
                 "detail": (
                     f"Çıkarım güveni {ASGARI_GUVEN:.2f}".replace(".", ",")
                     + " altında kalan değer sıralamaya GİRMEZ; "
                     "comparable=false olur ve notunda ölçülen güven yazar. "
                     "Değer silinmez, gerekçesiyle görünür kalır. Eşik altın "
                     "kümede ölçüldü: bu bandın altındaki çıkarımların hepsi "
                     "hatalıydı ve kanıt pencereleri belgenin kampanya olmayan "
                     "bölümlerinden (hesaplama aracı varsayılanı, çerez "
                     "metni, ücret tarifesi) geliyordu.")},
                {"no": 4, "name": "Adil kıyas kapısı",
                 "detail": "Yalnız comparable=True satırlar sıralanır. Aralık, "
                           "farklı para birimi, sayısal olmayan ve boş değerler "
                           "not'uyla sona alınır."},
                {"no": 5, "name": "Yön",
                 "detail": f"{field} → {direction} ({direction_label}). Kaynak: "
                           "compare._LOWER_IS_BETTER / _HIGHER_IS_BETTER."},
            ],
            "composite_weights": weight_manifest(),
            "composite_note": (
                "Bu uç TEK alan üzerinden sıralar. Alanlar arası ağırlıklı "
                "bileşik skor ayrı bir uçtadır: GET /advantageous. Ağırlıklar "
                "bir ÜRÜN KARARIDIR, ölçümden türetilmiş sabit değildir; her "
                "birinin gerekçesi yukarıda döner."),
            "composite_endpoint": "/advantageous",
            "rows": [
                {"bank": r["bank"], "bank_name": r["bank_name"],
                 "value": r["value"], "sort_key": r["sort_key"],
                 "comparable": r["comparable"], "note": r["note"],
                 "campaign_status": r["campaign_status"],
                 "rank": r["rank"], "confidence": r["confidence"],
                 "extractor": r["extractor"]}
                for r in rows
            ],
        }

    return scoring
