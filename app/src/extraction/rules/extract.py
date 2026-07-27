"""Kural tabanlı (deterministik) alan çıkarımı — BİRİNCİL katman.

İlgili kararlar:
- ../../decisions/ner-fine-tune-yerine-kural-few-shot.md  (kurallar birincil)
- ../../concepts/bilgi-cikarimi.md

Her çıkarıcı bir ExtractedField döndürür: canonical_value + confidence + source_span.
Bulamazsa alanı hiç üretmez (None döner) — boşluğu LLM katmanı doldurur.
Halüsinasyon yasağı: değer uydurma.
"""

from __future__ import annotations

import re
from typing import Optional

from ...normalization import normalize as N
from ...preprocessing.clean import tr_fold
from ...schemas import ExtractedField, Extractor

# Kural katmanının güveni yüksektir (deterministik); LLM'inkinden ayrışsın diye 0.95.
_RULE_CONF = 0.95


def _window(text: str, start: int, end: int, pad: int = 40) -> str:
    """source_span için eşleşme etrafından bir pencere döndürür."""
    a = max(0, start - pad)
    b = min(len(text), end + pad)
    return text[a:b].strip()


def _field(name: str, raw: str, canon, span: str, conf: float = _RULE_CONF):
    return ExtractedField(
        field_name=name,
        raw_value=raw,
        canonical_value=canon,
        confidence=conf if canon is not None else 0.0,
        source_span=span,
        extractor=Extractor.RULE,
    )


# --------------------------------------------------------------------------- #
# Tekil alan çıkarıcılar
# --------------------------------------------------------------------------- #
def extract_kar_payi(text: str) -> Optional[ExtractedField]:
    """Kâr payı oranı: '... kâr payı oranı %1,99 ...' veya aralık."""
    pat = re.compile(
        r"(kâr|kar)\s*pay[ıi]\s*(oran[ıi])?[^%\d]{0,15}"
        r"(%?\s*\d[\d.,]*\s*%?(?:\s*(?:-|–|ile|ila)\s*%?\s*\d[\d.,]*\s*%?)?)",
        re.IGNORECASE,
    )
    m = pat.search(text)
    if not m:
        return None
    raw = m.group(3)
    canon = N.normalize_rate(raw)
    return _field("kar_payi_orani", raw, canon, _window(text, m.start(), m.end()))


def extract_vade(text: str) -> Optional[ExtractedField]:
    """Vade: '120 aya kadar', '36 ay vade', '1 yıl'.

    Zaman-koşullu ifade tuzağı ('ilk 6 ay ödemesiz') gerçek vade değildir; bu
    yüzden 'vade' sözcüğüne yakın eşleşme tercih edilir
    (bkz. ../../decisions/zor-anlama-vakalari-merkezi.md).
    """
    pat = re.compile(
        r"(\d[\d.,]*)\s*(ay|yıl|yil|sene)(?:a|da|ta|dan|tan|ı|i|lık|lik)?\b",
        re.IGNORECASE,
    )
    matches = list(pat.finditer(text))
    if not matches:
        return None
    # tr_fold: 'İLK 6 AY' -> .lower() 'i̇lk' promo tespitini kaçırıyordu.
    # Katlama karakter sayısını korur, bu yüzden offset'ler text ile hizalı kalır.
    low = tr_fold(text)
    vade_pos = [mm.start() for mm in re.finditer(r"vade", low)]

    def score(m):
        # "ilk N ay" gibi promosyon dönemleri gerçek vade değildir → geri it
        pre = low[max(0, m.start() - 8): m.start()]
        promo = "ilk" in pre
        dist = min((abs(m.start() - v) for v in vade_pos), default=10 ** 6)
        return (promo, dist)

    chosen = min(matches, key=score)
    raw = chosen.group(0)
    canon = N.normalize_term_months(raw)
    return _field("vade_ay", raw, canon, _window(text, chosen.start(), chosen.end()))


def extract_tutar(text: str) -> Optional[ExtractedField]:
    """Finansman tutarı: 'finansman ... 500.000 TL'."""
    pat = re.compile(
        r"(finansman|kredi|tutar|limit)[^\d]{0,20}(\d[\d.,]*\s*(?:tl|₺|try|türk\s*liras[ıi]))",
        re.IGNORECASE,
    )
    m = pat.search(text)
    if not m:
        return None
    raw = m.group(2)
    canon = N.normalize_money(raw)
    return _field("finansman_tutari", raw, canon, _window(text, m.start(), m.end()))


def extract_taksit(text: str) -> Optional[ExtractedField]:
    """Taksit sayısı: '12 taksit', 'taksit sayısı 36'."""
    pat = re.compile(r"(\d{1,3})\s*taksit|taksit\s*(?:say[ıi]s[ıi])?\s*[:\-]?\s*(\d{1,3})",
                     re.IGNORECASE)
    m = pat.search(text)
    if not m:
        return None
    num = m.group(1) or m.group(2)
    try:
        canon = int(num)
    except (TypeError, ValueError):
        canon = None
    return _field("taksit_sayisi", m.group(0), canon, _window(text, m.start(), m.end()))


def extract_masraf(text: str) -> Optional[ExtractedField]:
    """Masraf durumu — negasyon farkında ('masrafsız' = 0, bilgi yok değil).

    Tutar, masraf sözcüğünün YEREL penceresinde aranır; aksi halde metnin
    başka yerindeki bir oran/sayı yanlışlıkla masraf tutarı sanılır.
    """
    m = re.search(r"(masrafs[ıi]z|ücretsiz|ucretsiz|masraf|tahsis|ücret)",
                  text, re.IGNORECASE)
    if m is None:
        return None
    # tutar keyword'den SONRA gelir ("tahsis ücreti 500 TL"); ileri pencere kullan
    fwd = text[m.start(): min(len(text), m.end() + 40)]
    canon = N.normalize_fee_status(fwd)
    if canon is None:
        return None
    return _field("masraf_durumu", m.group(0), canon, _window(text, m.start(), m.end()))


def extract_kampanya_suresi(text: str) -> Optional[ExtractedField]:
    """Kampanya süresi / son tarih → ISO."""
    pat = re.compile(
        r"(\d{1,2}[./]\d{1,2}[./]\d{4}|\d{4}-\d{1,2}-\d{1,2}|"
        r"\d{1,2}\s+[A-Za-zÇĞİÖŞÜçğıöşü]+\s+\d{4})"
    )
    m = pat.search(text)
    if not m:
        return None
    raw = m.group(1)
    canon = N.normalize_date(raw)
    if canon is None:
        return None
    return _field("kampanya_suresi", raw, canon, _window(text, m.start(), m.end()))


# Tüm kural çıkarıcılar — sırayla denenir.
_EXTRACTORS = [
    extract_kar_payi,
    extract_vade,
    extract_tutar,
    extract_taksit,
    extract_masraf,
    extract_kampanya_suresi,
]


def extract_all(text: str) -> list[ExtractedField]:
    """Metinden kural katmanının çıkarabildiği tüm alanları döndürür.

    Bulunamayan alanlar listelenmez (boşluk LLM'e bırakılır). Aynı alan birden
    çok kez yakalanırsa ilk (en yüksek güvenli) tutulur.
    """
    out: dict[str, ExtractedField] = {}
    for fn in _EXTRACTORS:
        f = fn(text)
        if f and f.is_present and f.field_name not in out:
            out[f.field_name] = f
    return list(out.values())
