"""Çelişki tespiti — yenilikçilik özelliği.

İlgili: ../../decisions/daraltilmis-yenilikcilik-hedefleri.md (çelişki tespiti #2)
        ../../sorun/farkli-ifade-bicimleri.md

Bir kampanya kendi içinde çelişiyorsa yakalar; en güçlüsü:
"masrafsız" deyip aynı metinde tahsis ücreti/masraf tutarı belirtmek.
Jüride açıklanabilirlik + güven açısından güçlü bir sinyal.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from ..schemas import Campaign


@dataclass
class Contradiction:
    kind: str
    detail: str
    fields: list[str]


def detect(campaign: Campaign) -> list[Contradiction]:
    """Tek kampanya içindeki çelişkileri döndürür."""
    out: list[Contradiction] = []

    masraf = campaign.get("masraf_durumu")
    tahsis = campaign.get("tahsis_ucreti")

    # 1) "masrafsız" (has_fee=False) ama tahsis ücreti > 0
    if masraf and isinstance(masraf.canonical_value, dict):
        free = masraf.canonical_value.get("has_fee") is False
        if free and tahsis and _positive(tahsis.canonical_value):
            out.append(Contradiction(
                kind="masrafsiz_ama_ucret",
                detail=f"'masrafsız' belirtilmiş ancak tahsis ücreti var "
                       f"({tahsis.raw_value}).",
                fields=["masraf_durumu", "tahsis_ucreti"],
            ))
        # 1b) has_fee=False ama amount>0
        amt = masraf.canonical_value.get("amount")
        if free and amt and amt > 0:
            out.append(Contradiction(
                kind="masrafsiz_ama_tutar",
                detail=f"'masrafsız' ancak masraf tutarı {amt} olarak görünüyor.",
                fields=["masraf_durumu"],
            ))

    return out


def _positive(value) -> bool:
    if isinstance(value, dict):
        v = value.get("value", value.get("amount"))
        return bool(v and v > 0)
    return bool(isinstance(value, (int, float)) and value > 0)
