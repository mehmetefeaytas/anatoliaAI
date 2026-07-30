"""LLM alanları için GERÇEK güven skoru — token logprob'larından türetilir.

İlgili: ../rules/confidence.py (KURAL katmanının ayrı güven modülü — bu onun
        yerine geçmez, ona DOKUNMAZ; iki katmanın kanıtı farklıdır)
        ../../../decisions/daraltilmis-yenilikcilik-hedefleri.md (hedef #1)
        CLAUDE.md §18, şartname §7 "Model Başarısı" (%30)

## Neden modelin kendi söylediği güvene güvenilmez

Şemada bir `confidence` alanı var ve model onu dolduruyor. Ama bu sayı da
modelin ürettiği bir token dizisidir: kalibre değildir, neredeyse her zaman
0.9'a yakındır ve yanlış cevaplarda da yüksektir. Yani "emin değilim" sinyali
tam ihtiyaç duyulan yerde gelmez.

Logprob farklı bir kanıt türüdür: **modelin o token'ı seçerken gerçekten ne
kadar tereddüt ettiği**. `%1,89` üretirken metinde tek aday varsa logprob
~0'a yakındır; iki aday arasında kaldıysa belirgin biçimde düşer. Bu sinyal
üretimden sonra icat edilemez, ölçülür.

## Yöntem

1. Sunucunun döndürdüğü token listesi sırayla birleştirilir; her token'ın
   yeniden kurulan metindeki `[start, end)` karakter aralığı hesaplanır.
2. Her alan için JSON içindeki `"value"` değerinin karakter aralığı bulunur
   (alan anahtarı -> `"value"` anahtarı -> dengeli değer okuması).
3. O aralıkla ÖRTÜŞEN token'ların logprob ortalaması alınır ve
   `conf = exp(mean(logprob))` ile olasılığa çevrilir.
4. Sonuç `[0.01, 0.99]` aralığına kırpılır: 1.0 "kesinlik" iddiasıdır ve hiçbir
   LLM çıktısı için doğru değildir; 0.0 ise alanı eşiğin altına atıp
   uzlaştırmada sessizce yok eder.

Ölçek: geometrik ortalama olasılık (perplexity'nin tersi). Kalibre EDİLMEMİŞTİR
— sıralayıcıdır. Kalibrasyon gold set üzerinde ayrıca yapılır; bu yüzden
skorun kaynağı `ExtractedField.confidence_source="logprob"` olarak kaydedilir
ve kural katmanının skorlarıyla aynı kovaya atılmaz.

Logprob yoksa (Ollama hiç vermez) modelin kendi bildirdiği değere düşülür ve
kaynak `"self_reported"` olarak işaretlenir — hangi kanıtla konuştuğumuz her
zaman kayıtlıdır.
"""

from __future__ import annotations

import math
from typing import Iterable, Optional, Tuple

from .parse import find_balanced_object_span

# Güven tabanı/tavanı — bkz. modül başlığı, madde 4.
MIN_CONF = 0.01
MAX_CONF = 0.99

# Skor kaynağı etiketleri (ExtractedField.confidence_source).
SOURCE_LOGPROB = "logprob"
SOURCE_SELF_REPORTED = "self_reported"

_WHITESPACE = " \t\r\n"


def token_offsets(logprobs: Iterable[dict]) -> Tuple[str, list[Tuple[int, int]]]:
    """Token listesini birleştirir; metni ve token başına offset'leri döndürür.

    Sunucunun `content` alanındaki token'lar birleştirildiğinde yanıt metnini
    verir; bu yeniden kurulan metin üzerinde çalışmak, sunucunun `content`
    string'ini ayrıca hizalamaya çalışmaktan güvenlidir.
    """
    parts: list[str] = []
    spans: list[Tuple[int, int]] = []
    pos = 0
    for item in logprobs:
        tok = str(item.get("token", ""))
        parts.append(tok)
        spans.append((pos, pos + len(tok)))
        pos += len(tok)
    return "".join(parts), spans


def _skip_ws(text: str, i: int) -> int:
    while i < len(text) and text[i] in _WHITESPACE:
        i += 1
    return i


def _read_string(text: str, i: int) -> Optional[int]:
    """`text[i] == '"'` varsayar; kapanış tırnağından SONRAKİ indisi döndürür."""
    i += 1
    escaped = False
    while i < len(text):
        ch = text[i]
        if escaped:
            escaped = False
        elif ch == "\\":
            escaped = True
        elif ch == '"':
            return i + 1
        i += 1
    return None


def _read_value(text: str, i: int) -> Optional[int]:
    """`i`'den başlayan JSON değerinin BİTİŞ indisini (dışlayıcı) döndürür.

    Nesne/dizi için parantez sayar (string içindekiler hariç); skaler için
    ayırıcıya (`,` `}` `]`) kadar okur.
    """
    i = _skip_ws(text, i)
    if i >= len(text):
        return None
    ch = text[i]
    if ch == '"':
        return _read_string(text, i)
    if ch in "{[":
        opening, closing = ("{", "}") if ch == "{" else ("[", "]")
        depth = 0
        in_string = False
        escaped = False
        j = i
        while j < len(text):
            c = text[j]
            if in_string:
                if escaped:
                    escaped = False
                elif c == "\\":
                    escaped = True
                elif c == '"':
                    in_string = False
            elif c == '"':
                in_string = True
            elif c == opening:
                depth += 1
            elif c == closing:
                depth -= 1
                if depth == 0:
                    return j + 1
            j += 1
        return None
    j = i
    while j < len(text) and text[j] not in ",}]" and text[j] not in _WHITESPACE:
        j += 1
    return j if j > i else None


def _find_key(text: str, key: str, start: int, end: int) -> Optional[int]:
    """`"key"` anahtarının [start, end) aralığındaki ilk konumunu bulur.

    İki nokta üst üste kontrolü yapılır: `"value"` bir DEĞER olarak da geçebilir
    (ör. bir koşul cümlesinin içinde); anahtar olduğundan emin olunmalı.
    """
    needle = f'"{key}"'
    i = text.find(needle, start, end)
    while i >= 0:
        after = _skip_ws(text, i + len(needle))
        if after < end and text[after] == ":":
            return i
        i = text.find(needle, i + len(needle), end)
    return None


def find_value_span(text: str, field: str,
                    bounds: Optional[Tuple[int, int]] = None
                    ) -> Optional[Tuple[int, int]]:
    """`field` alanının JSON içindeki `"value"` değerinin karakter aralığı.

    Args:
        text: LLM'in ham çıktısı (token'lardan yeniden kurulmuş olabilir).
        field: alan adı (ör. "kar_payi_orani").
        bounds: aramanın sınırlandırılacağı [start, end) aralığı. None ise
            metindeki ilk dengeli JSON nesnesi kullanılır (`<think>` bloğu
            böylece dışarıda kalır).

    Returns:
        (start, end) ya da None (alan yok / JSON bozuk).
    """
    if bounds is None:
        bounds = find_balanced_object_span(text)
        if bounds is None:
            return None
    lo, hi = bounds

    key_at = _find_key(text, field, lo, hi)
    if key_at is None:
        return None
    # Alanın kendi nesnesi: `"alan": { ... }` — bu nesnenin içinde "value" ara.
    colon = text.find(":", key_at, hi)
    if colon < 0:
        return None
    obj_start = _skip_ws(text, colon + 1)
    obj_end = _read_value(text, obj_start)
    if obj_end is None:
        return None
    if obj_start >= len(text) or text[obj_start] != "{":
        # `"alan": null` — değer yok, güven skoru da yok.
        return None

    value_key = _find_key(text, "value", obj_start, obj_end)
    if value_key is None:
        return None
    vcolon = text.find(":", value_key, obj_end)
    if vcolon < 0:
        return None
    vstart = _skip_ws(text, vcolon + 1)
    vend = _read_value(text, vstart)
    if vend is None or vend <= vstart:
        return None
    return vstart, vend


def span_confidence(logprobs: list[dict], span: Tuple[int, int],
                    spans: Optional[list[Tuple[int, int]]] = None
                    ) -> Optional[float]:
    """Verilen karakter aralığıyla örtüşen token'ların ortalama olasılığı."""
    if not logprobs:
        return None
    if spans is None:
        _, spans = token_offsets(logprobs)
    lo, hi = span
    values = [logprobs[i]["logprob"] for i, (s, e) in enumerate(spans)
              if s < hi and e > lo]
    if not values:
        return None
    return clamp(math.exp(sum(values) / len(values)))


def clamp(value: float) -> float:
    """Güveni [MIN_CONF, MAX_CONF] aralığına kırpar."""
    if value != value:              # NaN
        return MIN_CONF
    return max(MIN_CONF, min(MAX_CONF, value))


def field_confidences(logprobs: list[dict],
                      fields: Iterable[str]) -> dict[str, float]:
    """Her alan için logprob tabanlı güven skoru.

    Skor üretilemeyen alan sözlüğe KONULMAZ (çağıran modelin kendi bildirdiği
    değere düşer). Boş sözlük = logprob hiç gelmedi.
    """
    logprobs = list(logprobs or [])
    if not logprobs:
        return {}
    text, spans = token_offsets(logprobs)
    bounds = find_balanced_object_span(text)
    if bounds is None:
        return {}
    out: dict[str, float] = {}
    for name in fields:
        span = find_value_span(text, name, bounds)
        if span is None:
            continue
        conf = span_confidence(logprobs, span, spans)
        if conf is not None:
            out[name] = conf
    return out


def self_reported(value: object, default: float = 0.5) -> float:
    """Modelin kendi bildirdiği güveni güvenli biçimde okur ve kırpar."""
    try:
        return clamp(float(value))  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return clamp(default)
