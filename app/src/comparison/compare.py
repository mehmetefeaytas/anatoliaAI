"""Karşılaştırma motoru — sıralama + adil-kıyas garantisi.

İlgili: ../../decisions/daraltilmis-yenilikcilik-hedefleri.md (çelişki tespiti)
        ../../concepts/urun-karsilastirma.md
        CLAUDE.md §17 (adil kıyas: yalnız aynı-birim normalize alanlar)
        ../../sorun/manuel-karsilastirma-zorlugu.md

Aralık (min/max) alanları kıyaslanabilir ama "doğrudan kıyaslanamaz" işaretiyle;
sıralamada aralığın alt sınırı (en iyi senaryo) kullanılır ve flag verilir.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from ..normalization.normalize import collapse_degenerate_range


@dataclass
class RankRow:
    bank: str
    bank_name: Optional[str]
    value: Any              # ham canonical değer
    sort_key: Optional[float]  # sıralama için sayısal anahtar
    comparable: bool        # doğrudan kıyaslanabilir mi
    note: Optional[str]     # kıyaslanamazsa neden
    source_span: Optional[str]


# Alan → (sayısal_anahtar_çıkarıcı, küçük_mü_iyi)
def _numeric_key(field_name: str, value: Any) -> tuple[Optional[float], bool, Optional[str]]:
    """value'dan sıralama anahtarı üretir.

    Dönüş: (sort_key, comparable, note). Aralık ise alt sınır + comparable=False.
    Para ise value alanı. Sayı ise kendisi.
    """
    if value is None:
        return None, False, "değer yok"
    # Dejenere aralığı ({"min": X, "max": X}) düz sayıya indirge. Aynı savunma
    # normalizasyon katmanında da var; burada TEKRARLANIYOR çünkü LLM katmanı
    # kanonik değeri doğrudan üretebiliyor ve normalize_rate'ten geçmeyebilir.
    # Atlanırsa tamamen kıyaslanabilir bir değer "aralık" sanılıp sıralamadan
    # sessizce düşer -> §5.7 "En Düşük Kâr Payı" yanlış banka verir.
    value = collapse_degenerate_range(value)
    # aralık: {"min":, "max":}
    if isinstance(value, dict) and "min" in value and "max" in value:
        return float(value["min"]), False, "aralık — doğrudan kıyaslanamaz"
    # para: {"value":, "currency":}
    if isinstance(value, dict) and "value" in value:
        cur = value.get("currency")
        if cur and cur != "TRY":
            return None, False, f"farklı para birimi ({cur})"
        return float(value["value"]), True, None
    # masraf: {"has_fee":, "amount":}
    if isinstance(value, dict) and "has_fee" in value:
        amt = value.get("amount")
        return (float(amt) if amt is not None else 0.0), True, None
    if isinstance(value, (int, float)):
        return float(value), True, None
    return None, False, "sayısal değil"


# Hangi alanda küçük değer "daha iyi"? (sıralama yönü)
_LOWER_IS_BETTER = {
    "kar_payi_orani", "tahsis_ucreti", "masraf_durumu",
}
_HIGHER_IS_BETTER = {
    "vade_ay", "finansman_tutari", "odul_miktari", "indirim_orani", "alisveris_puani",
}


def rank(rows: list[dict], field_name: str) -> list[RankRow]:
    """query_fields() çıktısını alıp adil sıralama döndürür.

    rows: [{"bank","bank_name","canonical_value","source_span",...}]
    Yalnız comparable=True satırlar sıralanır; kıyaslanamazlar sona, not'la eklenir.
    """
    built: list[RankRow] = []
    for r in rows:
        sk, comparable, note = _numeric_key(field_name, r.get("canonical_value"))
        built.append(RankRow(
            bank=r.get("bank"),
            bank_name=r.get("bank_name"),
            # Gösterilen değer de tekilleştirilir: arayüzde `{min:1.89,
            # max:1.89}` yerine `1.89` görünsün.
            value=collapse_degenerate_range(r.get("canonical_value")),
            sort_key=sk,
            comparable=comparable,
            note=note,
            source_span=r.get("source_span"),
        ))

    lower_better = field_name in _LOWER_IS_BETTER
    comparables = [b for b in built if b.comparable and b.sort_key is not None]
    others = [b for b in built if not (b.comparable and b.sort_key is not None)]
    comparables.sort(key=lambda b: b.sort_key, reverse=not lower_better)
    return comparables + others


def best(rows: list[dict], field_name: str) -> Optional[RankRow]:
    """En iyi (sıralamada ilk comparable) satırı döndürür."""
    ranked = rank(rows, field_name)
    for r in ranked:
        if r.comparable:
            return r
    return None
