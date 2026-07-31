"""Yapısal sorgu motoru — text-to-SQL'in güvenli, deterministik karşılığı.

İlgili: ../../decisions/hibrit-chatbot-text-to-sql-rag.md
        CLAUDE.md §5

LLM'e serbest SQL ürettirmek yerine (enjeksiyon + halüsinasyon riski), router'ın
çıkardığı (alan, niyet, filtre) niyetini repository sorgularına ve karşılaştırma
motoruna güvenle eşler. Sonuç her zaman kaynağa (source_span) dayalıdır.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..comparison.compare import RankRow, rank
from ..db.repository import Repository
from .router import Route


@dataclass
class StructuredAnswer:
    text: str
    rows: list[RankRow]
    field: str
    intent: str


def answer(repo: Repository, r: Route) -> StructuredAnswer:
    rows = repo.query_fields(r.field)

    # filtreler
    rows = _apply_filters(repo, rows, r.filters)

    ranked = rank(rows, r.field)
    comparables = [x for x in ranked if x.comparable]

    if r.intent in ("lowest", "highest"):
        if not comparables:
            return StructuredAnswer(
                "Karşılaştırılabilir veri bulunamadı (değerler aralık veya farklı "
                "birimde olabilir).", ranked, r.field, r.intent)
        top = comparables[0]
        text = _phrase_superlative(r.field, r.intent, top)
        return StructuredAnswer(text, ranked, r.field, r.intent)

    # list / filter
    text = _phrase_list(r.field, ranked, r.filters)
    return StructuredAnswer(text, ranked, r.field, r.intent)


def _apply_filters(repo: Repository, rows: list[dict], filters: dict) -> list[dict]:
    if not filters:
        return rows
    out = rows
    # banka filtresi — sorulan banka verimizde yoksa sonuç BOŞ kalır ve
    # chatbot çekimserlik kapısından dürüst "verimde yok" yanıtı üretir.
    # Başka bankaların satırlarını cevap gibi sunmak sessiz halüsinasyondur.
    banks = filters.get("banks")
    if banks:
        out = [r for r in out if r.get("bank") in banks]
    # kampanya türü filtresi
    ctype = filters.get("campaign_type")
    if ctype:
        out = [r for r in out if (r.get("campaign_type") == ctype)]
    # vade_ay_min: ilgili kampanyanın vade alanına bak.
    # Eskiden satır başına bir `repo.field_value()` sorgusu atılıyordu (N+1).
    # 1696 kampanyalık korpusta "36 ay ve üzeri vade veren konut finansmanları"
    # sorusu tek başına ~23 ms sürüyordu — chatbot'un ikinci en yavaş yolu.
    # Tek `query_fields("vade_ay")` çağrısı aynı veriyi bir sorguda getirir.
    vmin = filters.get("vade_ay_min")
    if vmin is not None:
        # `field_value()` fetchone() ile İLK satırı döndürüyordu; aynı
        # kampanyada birden fazla vade_ay satırı olursa (beklenmez ama şema
        # engellemiyor) setdefault ile yine ilkini alıyoruz.
        vade_by_campaign: dict[int, object] = {}
        for row in repo.query_fields("vade_ay"):
            vade_by_campaign.setdefault(row["campaign_id"], row["canonical_value"])
        out = [r for r in out
               if isinstance(vade_by_campaign.get(r["campaign_id"]), (int, float))
               and vade_by_campaign[r["campaign_id"]] >= vmin]
    return out


_FIELD_LABEL = {
    "kar_payi_orani": "kâr payı oranı",
    "vade_ay": "vade",
    "finansman_tutari": "finansman tutarı",
    "tahsis_ucreti": "tahsis ücreti",
    "masraf_durumu": "masraf durumu",
    "taksit_sayisi": "taksit sayısı",
}


def _fmt_value(field: str, value) -> str:
    if field == "kar_payi_orani" and isinstance(value, (int, float)):
        return f"%{value:g}".replace(".", ",")
    if field == "vade_ay" and isinstance(value, (int, float)):
        return f"{int(value)} ay"
    if isinstance(value, dict) and "value" in value:
        return f"{value['value']:g} {value.get('currency', 'TRY')}"
    if isinstance(value, dict) and "min" in value:
        return f"%{value['min']:g}–%{value['max']:g}".replace(".", ",")
    return str(value)


def _phrase_superlative(field: str, intent: str, row: RankRow) -> str:
    label = _FIELD_LABEL.get(field, field)
    sup = "en düşük" if intent == "lowest" else "en yüksek"
    name = row.bank_name or row.bank
    val = _fmt_value(field, row.value)
    return f"{sup} {label}: **{name}** ({val})."


def _phrase_list(field: str, ranked: list[RankRow], filters: dict) -> str:
    label = _FIELD_LABEL.get(field, field)
    if not ranked:
        return "Bu kritere uyan kampanya bulunamadı."
    lines = []
    for r in ranked:
        name = r.bank_name or r.bank
        val = _fmt_value(field, r.value)
        flag = "" if r.comparable else f"  _(not: {r.note})_"
        lines.append(f"- {name}: {val}{flag}")
    head = f"{label} (uygun kampanyalar):"
    if filters.get("campaign_type"):
        head = f"{filters['campaign_type']} — {head}"
    return head + "\n" + "\n".join(lines)
