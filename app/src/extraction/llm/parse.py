"""LLM ham çıktısından JSON nesnesi söken sağlam ayrıştırıcı (saf stdlib).

İlgili: CLAUDE.md §19 (LLM çıktısı serbest metin olarak parse EDİLMEZ),
        §21 (sık hatalar: serbest metin parse etmek).

## Neden bu modül var

Kısıtlı decoding (guided_json / json_schema) her zaman kullanılamaz:

- Sunucu o kısıt biçimini desteklemiyor olabilir (bkz. `clients.py` yetenek
  pazarlığı; son çare `prompt_only` modudur).
- Qwen3 gibi "düşünen" modeller yanıtın önüne `<think>...</think>` bloğu koyar;
  bu blok kısıtlı decoding açıkken bile bazı sunucu sürümlerinde sızar.
- Model yanıtı ```json çitiyle sarabilir.
- Kesilen (truncated) yanıtta JSON hiç kapanmaz.

Bu modül bu patolojileri sırayla ele alır ve **asla exception fırlatmaz**:
`(nesne, None)` ya da `(None, hata_mesajı)` döndürür. Hata mesajı çağıran
katmanda hem loglanır hem de onarım (repair) denemesinde prompt'a eklenir —
sessiz yutma yok (bkz. `extractor.py`).

## Neden regex değil, parantez sayımı

`re.search(r"\\{.*\\}", s, re.S)` iç içe nesnelerde ilk `{` ile SON `}` arasını
alır; iki ayrı JSON nesnesi peş peşe geldiğinde ikisini birden yutar ve
`json.loads` patlar. Karakter karakter süslü parantez sayan tarayıcı (string
içindeki `{`/`}` ve `\\"` kaçışları dahil) doğru olanı yapar.
"""

from __future__ import annotations

import json
import re
from typing import Any, Optional, Tuple

# `<think>...</think>` bloğu (Qwen3 reasoning). Kapanış etiketi yoksa (kesik
# yanıt) ayrı ele alınır.
_THINK_CLOSED = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)
_THINK_OPEN = re.compile(r"<think>.*\Z", re.DOTALL | re.IGNORECASE)

# ```json ... ``` veya ``` ... ``` çiti.
_FENCE = re.compile(r"```(?:json|JSON)?\s*(.*?)(?:```|\Z)", re.DOTALL)

# Nesne/dizi kapanışından önceki sondaki virgül:  {"a": 1,}  ->  {"a": 1}
_TRAILING_COMMA = re.compile(r",\s*([}\]])")

ParseResult = Tuple[Optional[dict], Optional[str]]


def strip_think(text: str) -> str:
    """`<think>` bloklarını atar. Kapanmamış blok da (kesik yanıt) temizlenir."""
    out = _THINK_CLOSED.sub("", text)
    out = _THINK_OPEN.sub("", out)
    return out


def strip_fence(text: str) -> str:
    """Markdown kod çitini soyar. Çit yoksa metni aynen döndürür."""
    m = _FENCE.search(text)
    if m and m.group(1).strip():
        return m.group(1)
    return text


def find_balanced_object_span(text: str, start: int = 0) -> Optional[Tuple[int, int]]:
    """İlk DENGELİ JSON nesnesinin `[başlangıç, bitiş)` offset'lerini döndürür.

    String literal içindeki süslü parantezler ve `\\"` kaçışları sayıma dahil
    edilmez. Dengeli kapanış bulunamazsa (kesik yanıt) None döner.

    Offset döndürmesinin nedeni `confidence.py`'dir: alan bazlı güven skoru,
    token'ların JSON içindeki KARAKTER konumuna göre eşlenir; `<think>` bloğu
    içinde geçen benzer metin skoru kirletmesin diye arama bu aralıkla
    sınırlanır.
    """
    begin = text.find("{", start)
    if begin < 0:
        return None
    depth = 0
    in_string = False
    escaped = False
    for i in range(begin, len(text)):
        ch = text[i]
        if in_string:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return begin, i + 1
    return None


def find_balanced_object(text: str) -> Optional[str]:
    """İlk dengeli JSON nesnesinin METNİ (bkz. `find_balanced_object_span`)."""
    span = find_balanced_object_span(text)
    return None if span is None else text[span[0]:span[1]]


def _single_to_double_quotes(text: str) -> str:
    """Tek tırnaklı (Python-vari) JSON'u çift tırnaklıya çevirir.

    Yalnızca son çare. Zaten çift tırnaklı bölümlere dokunulmaz; bu yüzden
    metin içinde çift tırnak varsa dönüşüm yapılmaz (bozma riski).
    """
    if '"' in text:
        return text
    return text.replace("'", '"')


def _coerce_dict(obj: Any) -> ParseResult:
    """Ayrıştırılan nesneyi sözlüğe indirger (liste dönerse ilk eleman)."""
    if isinstance(obj, dict):
        return obj, None
    if isinstance(obj, list):
        if not obj:
            return None, "bos liste dondu"
        first = obj[0]
        if isinstance(first, dict):
            return first, None
        return None, f"liste icinde sozluk beklendi, {type(first).__name__} geldi"
    return None, f"sozluk beklendi, {type(obj).__name__} geldi"


def parse_llm_json(text: Optional[str]) -> ParseResult:
    """LLM ham çıktısından JSON nesnesi çıkarır.

    Sıra: `<think>` at -> çit soy -> dengeli nesneyi bul -> sondaki virgülleri
    temizle -> `json.loads` -> başarısızsa tek tırnak dönüşümü -> yine olmazsa
    `(None, hata)`.

    Returns:
        (nesne, None) veya (None, hata_mesajı). ASLA exception fırlatmaz.
    """
    if text is None:
        return None, "bos yanit (None)"
    if not text.strip():
        return None, "bos yanit (bos string)"

    cleaned = strip_fence(strip_think(text)).strip()
    if not cleaned:
        return None, "temizleme sonrasi icerik kalmadi (yalnizca think/cit)"

    candidate = find_balanced_object(cleaned)
    if candidate is None:
        if "{" in cleaned:
            return None, "dengeli JSON nesnesi kapanmamis (kesik yanit olabilir)"
        return None, "yanitta JSON nesnesi yok"

    for attempt in (candidate, _TRAILING_COMMA.sub(r"\1", candidate)):
        try:
            return _coerce_dict(json.loads(attempt))
        except json.JSONDecodeError:
            continue

    # Son çare: tek tırnaklı sözde-JSON.
    single = _TRAILING_COMMA.sub(r"\1", _single_to_double_quotes(candidate))
    try:
        return _coerce_dict(json.loads(single))
    except json.JSONDecodeError as exc:
        return None, f"JSON ayristirilamadi: {exc.msg} (pos {exc.pos})"
