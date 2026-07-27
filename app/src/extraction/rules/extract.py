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
from . import confidence as C
from .synonyms import NEGATION_RE

# Kural katmanının güveni yüksektir (deterministik); LLM'inkinden ayrışsın diye 0.95.
_RULE_CONF = 0.95


def _window(text: str, start: int, end: int, pad: int = 40) -> str:
    """source_span için eşleşme etrafından bir pencere döndürür."""
    a = max(0, start - pad)
    b = min(len(text), end + pad)
    return text[a:b].strip()


def _field(
    name: str,
    raw: str,
    canon,
    span: str,
    conf: Optional[float] = None,
    *,
    span_start: Optional[int] = None,
    span_end: Optional[int] = None,
    trigger_distance: Optional[int] = None,
    candidate_count: int = 1,
):
    """ExtractedField üretir; güven verilmezse kanıt sinyallerinden hesaplanır.

    `conf` açıkça verilirse (geriye uyumluluk) o kullanılır; verilmezse
    `confidence.score()` tetikleyici yakınlığı + makullük + belirsizlikten
    gerçek bir skor üretir. Bkz. rules/confidence.py.
    """
    if conf is not None:
        value, csource = (conf if canon is not None else 0.0), "constant"
    else:
        value, _reason = C.score(
            name, canon,
            trigger_distance=trigger_distance,
            candidate_count=candidate_count,
        )
        csource = "rule_heuristic"
    return ExtractedField(
        field_name=name,
        raw_value=raw,
        canonical_value=canon,
        confidence=value,
        source_span=span,
        extractor=Extractor.RULE,
        span_start=span_start,
        span_end=span_end,
        confidence_source=csource,
    )


# --------------------------------------------------------------------------- #
# Tekil alan çıkarıcılar
# --------------------------------------------------------------------------- #
def extract_kar_payi(text: str) -> Optional[ExtractedField]:
    """Kâr payı oranı: '... kâr payı oranı %1,99 ...' veya aralık."""
    # Aralık ikinci operandı bir BİRİM sözcüğü ile devam ediyorsa aralık DEĞİLDİR:
    #   "kâr payı oranı %1,89 ile 120 aya kadar vade"
    # buradaki "ile" bağlaçtır, aralık ayırıcı değil. Negatif ileri-bakış olmadan
    # sistem bunu {min: 1.89, max: 120.0} diye okuyup karşılaştırma tablosuna
    # bir VADEYİ oran üst sınırı olarak yazıyordu.
    pat = re.compile(
        r"(kâr|kar)\s*pay[ıi]\s*(oran[ıi])?[^%\d]{0,15}"
        r"(%?\s*\d[\d.,]*\s*%?"
        r"(?:\s*(?:-|–|ile|ila)\s*%?\s*"
        # (?![\d.,]) sayının TAMAMININ tüketilmesini zorlar. Bu olmadan regex
        # geri izleyip "36"dan yalnız "3"ü alarak birim kontrolünü atlatıyordu.
        r"\d[\d.,]*(?![\d.,])\s*%?"
        r"(?!\s*(?:ay|y[ıi]l|sene|taksit|tl|₺|adet))"
        r")?)",
        re.IGNORECASE,
    )
    m = pat.search(text)
    if not m:
        return None
    raw = m.group(3)
    s, e = m.span(3)
    canon = N.normalize_rate(raw)
    return _field(
        "kar_payi_orani", raw, canon, _window(text, m.start(), m.end()),
        span_start=s, span_end=e,
        # "kâr payı oranı" bitişi ile değerin başı arası
        trigger_distance=s - m.end(1),
        candidate_count=len(pat.findall(text)),
    )


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
    s, e = chosen.span()
    canon = N.normalize_term_months(raw)
    dist = min((abs(s - v) for v in vade_pos), default=None)
    return _field(
        "vade_ay", raw, canon, _window(text, s, e),
        span_start=s, span_end=e,
        trigger_distance=dist,
        candidate_count=len(matches),
    )


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
    s, e = m.span(2)
    canon = N.normalize_money(raw)
    return _field(
        "finansman_tutari", raw, canon, _window(text, m.start(), m.end()),
        span_start=s, span_end=e,
        trigger_distance=s - m.end(1),
        candidate_count=len(pat.findall(text)),
    )


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
    s, e = m.span()
    return _field(
        "taksit_sayisi", m.group(0), canon, _window(text, s, e),
        span_start=s, span_end=e,
        # "taksit" sözcüğü eşleşmenin kendi içinde → bitişik kabul edilir
        trigger_distance=0,
        candidate_count=len(pat.findall(text)),
    )


def extract_masraf(text: str) -> Optional[ExtractedField]:
    """Masraf durumu — negasyon farkında ('masrafsız' = 0, bilgi yok değil).

    Tutar, masraf sözcüğünün YEREL penceresinde aranır; aksi halde metnin
    başka yerindeki bir oran/sayı yanlışlıkla masraf tutarı sanılır.

    TÜM masraf bahisleri taranır (`finditer`), sadece ilki değil. Eskiden
    `re.search` kullanıldığı için sonuç yazım SIRASINA bağlıydı:

        "Masrafsızdır. Tahsis ücreti 500 TL."  -> has_fee=False  ✓ çelişki
        "Tahsis ücreti 500 TL. Masrafsızdır."  -> has_fee=True   ✗ çelişki kaçtı

    Bu alan kampanyanın İDDİASINI taşır. Metinde herhangi bir yerde
    "masrafsız/ücretsiz" iddiası varsa `has_fee=False` döner; gerçekte ücret
    olup olmadığını `tahsis_ucreti` alanı söyler ve uyuşmazlığı
    `contradiction.detect()` yakalar.
    """
    pat = re.compile(r"(masrafs[ıi]z|ücretsiz|ucretsiz|masraf|tahsis|ücret)",
                     re.IGNORECASE)
    first_positive = None
    for m in pat.finditer(text):
        # tutar keyword'den SONRA gelir ("tahsis ücreti 500 TL") → ileri pencere
        fwd = text[m.start(): min(len(text), m.end() + 40)]
        canon = N.normalize_fee_status(fwd)
        if canon is None:
            continue
        if canon.get("has_fee") is False:
            # "masrafsız" iddiası bulundu — sırası ne olursa olsun bu kazanır.
            s, e = m.span()
            return _field("masraf_durumu", m.group(0), canon,
                          _window(text, s, e),
                          span_start=s, span_end=e, trigger_distance=0)
        if first_positive is None:
            first_positive = (m, canon)

    if first_positive is None:
        return None
    m, canon = first_positive
    s, e = m.span()
    return _field("masraf_durumu", m.group(0), canon, _window(text, s, e),
                  span_start=s, span_end=e, trigger_distance=0)


def extract_tahsis_ucreti(text: str) -> Optional[ExtractedField]:
    """Tahsis ücreti / dosya masrafı — `masraf_durumu`'ndan BAĞIMSIZ çıkarılır.

    Neden ayrı: `contradiction.detect()`'in birincil kuralı
    (`masrafsiz_ama_ucret`) hem `masraf_durumu` hem `tahsis_ucreti` ister.
    Bu alan hiç üretilmediği için o kural bugüne kadar hiç tetiklenemedi ve
    yenilikçilik hedefi #2 (bkz. CLAUDE.md §18) ölüydü.

        "tahsis ücreti 500 TL"     -> {"value": 500.0, "currency": "TRY"}
        "TAHSİS ÜCRETİ ALINMAZ"    -> {"value": 0.0,   "currency": "TRY"}
        (hiç geçmiyorsa)           -> None  (uydurma yok)

    Negasyon "bilgi yok" DEĞİL "ücret sıfır" demektir; bu ayrım §5.5'teki
    "masrafsız finansman" teriminin doğru yorumlanmasının temelidir.
    """
    trigger = re.compile(
        r"(tahsis\s*ücret\w*|tahsis\s*ucret\w*|dosya\s*masraf\w*|"
        r"tahsis\s*bedel\w*)",
        re.IGNORECASE,
    )
    m = trigger.search(text)
    if m is None:
        return None

    # Aynı cümlecik içinde kal: tetikleyiciden sonraki ilk cümle/virgül sonuna
    # kadar bak. Aksi halde metnin başka yerindeki bir tutar yanlışlıkla
    # tahsis ücreti sanılır.
    tail = text[m.end(): m.end() + 60]
    # DİKKAT: '.' Türkçede hem cümle sonu hem BİNLİK AYIRICIDIR. Düz
    # re.split(r"[.;\n]") "1.500,00 TL"yi "1"de kesip 1500 yerine 1 üretiyordu.
    # Rakamlar arasındaki noktada bölmemek için etrafına lookaround konur.
    clause = re.split(r"(?<!\d)[.;](?!\d)|\n", tail, maxsplit=1)[0]

    if re.search(NEGATION_RE, clause, re.IGNORECASE):
        canon = {"value": 0.0, "currency": "TRY"}
    else:
        canon = N.normalize_money(clause)
        if canon is None:
            # Tetikleyici var ama ne tutar ne negasyon → bilgi belirsiz.
            return None

    # raw_value BİTİŞİK bir dilim olmalı, yoksa span doğrulaması kırılır
    # (önceden `m.group(0) + clause.rstrip()` birleştirmesi kullanılıyordu).
    s, e = m.start(), m.end() + len(clause)
    raw = text[s:e]
    return _field("tahsis_ucreti", raw, canon, _window(text, m.start(), m.end()),
                  span_start=s, span_end=e, trigger_distance=0)


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
    s, e = m.span(1)
    canon = N.normalize_date(raw)
    if canon is None:
        return None
    # Tarih genelde "kampanya süresi/son başvuru/tarihine kadar" ifadesinin
    # yakınındadır; tetikleyici varsa uzaklığı ölç, yoksa None (ceza).
    trig = None
    for tm in re.finditer(r"(kampanya|son\s+ba[şs]vuru|ge[çc]erli|tarihine\s+kadar)",
                          text, re.IGNORECASE):
        d = abs(s - tm.start())
        trig = d if trig is None else min(trig, d)
    return _field("kampanya_suresi", raw, canon, _window(text, s, e),
                  span_start=s, span_end=e, trigger_distance=trig,
                  candidate_count=len(pat.findall(text)))


# Tüm kural çıkarıcılar — sırayla denenir.
_EXTRACTORS = [
    extract_kar_payi,
    extract_vade,
    extract_tutar,
    extract_taksit,
    extract_masraf,
    extract_tahsis_ucreti,
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
