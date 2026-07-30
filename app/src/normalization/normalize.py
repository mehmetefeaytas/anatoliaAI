"""Canonical normalizasyon — deterministik, saf stdlib.

İlgili kararlar:
- ../decisions/zor-anlama-vakalari-merkezi.md  (TR sayı formatı, aralık, negasyon)
- ../concepts/veri-normalizasyonu.md

Tüm fonksiyonlar saf (yan etkisiz) ve `None` güvenlidir: bulamazlarsa `None`
döndürür — ASLA değer uydurmaz (halüsinasyon yasağı).
"""

from __future__ import annotations

import re
from typing import Optional, Union

from ..preprocessing.clean import tr_fold, tr_fold_ascii

Number = Union[int, float]


# --------------------------------------------------------------------------- #
# TR sayı ayrıştırma
# --------------------------------------------------------------------------- #
def parse_tr_number(text: str) -> Optional[float]:
    """Türkçe sayı biçimini float'a çevirir.

    TR konvansiyonu: binlik ayıracı '.', ondalık ayıracı ','.
        "1.500,00" -> 1500.0
        "%2,05"    -> 2.05
        "2.05"     -> 2.05   (ondalık nokta de-facto kullanımı; tek nokta + 1-2 hane)
        "500"      -> 500.0
    Belirsizse (örn. "1.500" → 1500 mü 1.5 mi) TR kuralına göre binlik kabul edilir.
    """
    if text is None:
        return None
    s = text.strip()
    # sayı dışındaki her şeyi at, ',' '.' ve rakamları tut
    s = re.sub(r"[^\d,.\-]", "", s)
    # baştaki/sondaki ayıraçları temizle ("1,89," → "1,89")
    s = s.strip(".,")
    if not s or not re.search(r"\d", s):
        return None

    has_comma = "," in s
    has_dot = "." in s

    if has_comma and has_dot:
        # TR: nokta binlik, virgül ondalık
        s = s.replace(".", "").replace(",", ".")
    elif has_comma:
        # virgül ondalık
        s = s.replace(",", ".")
    elif has_dot:
        # Tek nokta: ondalık mı binlik mi? Nokta sonrası 3 hane → binlik (1.500),
        # 1-2 hane → ondalık (2.05).
        parts = s.split(".")
        if len(parts) == 2 and len(parts[1]) == 3:
            s = s.replace(".", "")  # binlik
        # aksi halde ondalık nokta olarak bırak
        else:
            pass
    try:
        return float(s)
    except ValueError:
        return None


# --------------------------------------------------------------------------- #
# Oran (kâr payı / indirim) → decimal yüzde
# --------------------------------------------------------------------------- #
_RANGE_SEP = r"\s*(?:-|–|—|ile|ila|arası|arasında|/)\s*"


def normalize_rate(text: str) -> Optional[Union[float, dict]]:
    """Oran ifadesini decimal yüzdeye çevirir.

        "%2,05"          -> 2.05
        "% 2.05"         -> 2.05
        "2,05%"          -> 2.05
        "%1,99 - %2,49"  -> {"min": 1.99, "max": 2.49}   (aralık korunur)
    Aralık tek bir değere indirgenmez; karşılaştırmada adil kıyas için saklanır
    (bkz. ../decisions/zor-anlama-vakalari-merkezi.md).
    """
    if text is None:
        return None
    # aralık var mı?
    nums = re.findall(r"%?\s*\d[\d.,]*\s*%?", text)
    nums = [n for n in nums if re.search(r"\d", n)]
    if re.search(_RANGE_SEP, text) and len(nums) >= 2:
        lo = parse_tr_number(nums[0])
        hi = parse_tr_number(nums[1])
        if lo is not None and hi is not None:
            return collapse_degenerate_range({"min": min(lo, hi),
                                              "max": max(lo, hi)})
    if nums:
        return parse_tr_number(nums[0])
    return None


def collapse_degenerate_range(value):
    """`{"min": X, "max": X}` -> `X`. Sınırları eşit olan aralık, aralık değildir.

    Neden gerekli: `comparison/compare.py` min/max içeren HER değeri
    "aralık — doğrudan kıyaslanamaz" diye işaretleyip sıralamanın dışına
    atar. Dolayısıyla dejenere bir aralık, aslında tamamen kıyaslanabilir
    bir sayı olduğu hâlde karşılaştırma tablosundan SESSİZCE DÜŞER ve
    §5.7 "En Düşük Kâr Payı" kriterinde gerçek en iyi banka kaçırılır.

    Bu, kural katmanının regex'lerinden nadiren çıkar ama LLM katmanı üretir:
    Colab'da qwen3:32b, "kâr payı oranı %1,89" için `{"min":1.89,"max":1.89}`
    döndürdü — değer doğru, gösterim yanlış. Kanonik biçim bunu tekilleştirmeli
    ki aşağı akıştaki her tüketici aynı şeyi görsün.
    """
    if (isinstance(value, dict)
            and set(value) >= {"min", "max"}
            and value["min"] == value["max"]):
        return value["min"]
    return value


# --------------------------------------------------------------------------- #
# Para → {value, currency}
# --------------------------------------------------------------------------- #
_CURRENCY = {
    "tl": "TRY", "₺": "TRY", "try": "TRY",
    "türk lirası": "TRY", "lira": "TRY",
}

# Katlanmış görünüm: 'TÜRK LİRASI' gibi ALL-CAPS yazımlar da eşleşsin.
# '₺' katlama sonrası değişmez, sözlükte kalır.
_FOLDED_CURRENCY = {tr_fold_ascii(k): v for k, v in _CURRENCY.items()}


def normalize_money(text: str) -> Optional[dict]:
    """Para ifadesini {value, currency} sözlüğüne çevirir.

        "500 TL"          -> {"value": 500.0, "currency": "TRY"}
        "1.500,00₺"       -> {"value": 1500.0, "currency": "TRY"}
        "500 Türk Lirası" -> {"value": 500.0, "currency": "TRY"}
    """
    if text is None:
        return None
    low = tr_fold_ascii(text)
    currency = None
    for token, code in _FOLDED_CURRENCY.items():
        if token in low:
            currency = code
            break
    m = re.search(r"\d[\d.,]*", text)
    if not m:
        return None
    value = parse_tr_number(m.group(0))
    if value is None:
        return None
    return {"value": value, "currency": currency or "TRY"}


# --------------------------------------------------------------------------- #
# Vade → ay (int)
# --------------------------------------------------------------------------- #
def normalize_term_months(text: str) -> Optional[int]:
    """Vadeyi ay cinsinden integer'a çevirir.

        "12 ay"  -> 12
        "1 yıl"  -> 12
        "1,5 yıl"-> 18
    """
    if text is None:
        return None
    low = tr_fold(text)
    # TR çekim ekleri ("aya", "ayda", "ayı", "yıla") yakalanır; 'ay' sözcük başı
    # değilse (örn. 'ayrıca') eşleşmez çünkü hemen önünde rakam aranır.
    m = re.search(r"(\d[\d.,]*)\s*(ay|yıl|yil|sene)(?:a|da|ta|dan|tan|ı|i|lık|lik)?\b", low)
    if not m:
        return None
    val = parse_tr_number(m.group(1))
    if val is None:
        return None
    unit = m.group(2)
    if unit in ("yıl", "yil", "sene"):
        return int(round(val * 12))
    return int(round(val))


# --------------------------------------------------------------------------- #
# Tarih → ISO-8601
# --------------------------------------------------------------------------- #
_TR_MONTHS = {
    "ocak": 1, "şubat": 2, "subat": 2, "mart": 3, "nisan": 4, "mayıs": 5,
    "mayis": 5, "haziran": 6, "temmuz": 7, "ağustos": 8, "agustos": 8,
    "eylül": 9, "eylul": 9, "ekim": 10, "kasım": 11, "kasim": 11,
    "aralık": 12, "aralik": 12,
}

_FOLDED_TR_MONTHS = {tr_fold_ascii(k): v for k, v in _TR_MONTHS.items()}


def normalize_date(text: str) -> Optional[str]:
    """Tarihi ISO-8601 (YYYY-MM-DD) biçimine çevirir.

        "31.12.2026"      -> "2026-12-31"
        "31/12/2026"      -> "2026-12-31"
        "31 Aralık 2026"  -> "2026-12-31"
        "2026-12-31"      -> "2026-12-31"
    """
    if text is None:
        return None
    s = text.strip()

    # ISO zaten
    m = re.search(r"(\d{4})-(\d{1,2})-(\d{1,2})", s)
    if m:
        y, mo, d = map(int, m.groups())
        return _iso(y, mo, d)

    # gg.aa.yyyy veya gg/aa/yyyy
    m = re.search(r"(\d{1,2})[./](\d{1,2})[./](\d{4})", s)
    if m:
        d, mo, y = map(int, m.groups())
        return _iso(y, mo, d)

    # gg Ay yyyy
    m = re.search(r"(\d{1,2})\s+([A-Za-zÇĞİÖŞÜçğıöşü]+)\s+(\d{4})", s)
    if m:
        d = int(m.group(1))
        mo = _FOLDED_TR_MONTHS.get(tr_fold_ascii(m.group(2)))
        y = int(m.group(3))
        if mo:
            return _iso(y, mo, d)
    return None


def _iso(y: int, mo: int, d: int) -> Optional[str]:
    if 1 <= mo <= 12 and 1 <= d <= 31:
        return f"{y:04d}-{mo:02d}-{d:02d}"
    return None


# --------------------------------------------------------------------------- #
# Masraf durumu — NEGASYON (masrafsız ≠ "değer yok")
# --------------------------------------------------------------------------- #
_FREE_TOKENS = ["masrafsız", "masrafsiz", "ücretsiz", "ucretsiz",
                "dosya masrafı yok", "dosya masrafi yok", "masraf yok",
                "sıfır masraf", "sifir masraf", "tahsis ücreti yok"]

# Katlanmış görünüm. Bu katlama olmadan 'ÜCRETSİZ' -> .lower() -> 'ücretsi̇z'
# (birleşen nokta) hiçbir token'a eşleşmiyordu ve fonksiyon has_fee=True
# döndürüyordu — yani "masrafsız" yazan metni "masraf var" diye okuyordu.
_FOLDED_FREE_TOKENS = frozenset(tr_fold_ascii(t) for t in _FREE_TOKENS)

# FİİL NEGASYONU. Sabit token listesi yalnızca sıfat/isim biçimlerini
# ("masrafsız", "ücretsiz") yakalıyordu; Türkçe kampanya metinleri ise
# çoğunlukla fiil kullanır: "ücret ALINMAZ", "masraf TALEP EDİLMEZ".
# Bu desen olmadan "Yıllık kart ücreti alınmaz" ifadesi has_fee=True okunuyor,
# üstelik cümle sonrası tarihten ("31 Aralık") 31 TL'lik hayali bir tutar
# üretiliyordu. Tek doğruluk kaynağı burasıdır; synonyms.py bunu yeniden ihraç
# eder, böylece çıkarım ve normalizasyon katmanları aynı deseni kullanır.
NEGATION_RE = (
    r"(?:al[ıi]nma[zy]\w*|al[ıi]nm[ıi]yor|tahsil\s+edilme[zy]\w*|"
    r"talep\s+edilme[zy]\w*|yans[ıi]t[ıi]lma[zy]\w*|yoktur|yok\b|"
    r"bulunmamaktad[ıi]r|muaf|s[ıi]f[ıi]r|bedelsiz)"
)

# Masraf bahsi tetikleyicileri (katlanmış).
_FOLDED_FEE_HINTS = frozenset(
    tr_fold_ascii(t) for t in ("masraf", "ücret", "ucret", "tahsis")
)


def normalize_fee_status(text: str) -> Optional[dict]:
    """Masraf durumunu yorumlar. NEGASYON kritik: 'masrafsız' = masraf 0,
    "bilgi yok" DEĞİL.

        "masrafsız"        -> {"has_fee": False, "amount": 0.0}
        "tahsis ücreti 500 TL" -> {"has_fee": True, "amount": 500.0}
        (masraf hiç geçmiyorsa)  -> None  (bilgi yok; uydurma)
    """
    if text is None:
        return None
    low = tr_fold_ascii(text)
    if any(tok in low for tok in _FOLDED_FREE_TOKENS):
        return {"has_fee": False, "amount": 0.0}
    if any(tok in low for tok in _FOLDED_FEE_HINTS):
        # Fiil negasyonu: "ücret alınmaz" = ücret SIFIR, bilgi yok değil.
        if re.search(NEGATION_RE, low):
            return {"has_fee": False, "amount": 0.0}
        money = normalize_money(text)
        if money:
            return {"has_fee": True, "amount": money["value"]}
        return {"has_fee": True, "amount": None}
    return None
