"""Eşleştiriciler (matchers) — `strict` ve `tolerant` YAN YANA.

İlgili: ../../syntheses/teslim-ve-degerlendirme-rehberi.md
        scripts/gold_schema.py (kanonik tip aileleri — tek kaynak)
        CLAUDE.md §16

## Neden iki mod, neden ikisi de raporlanır

Tek başına **gevşek** metrik raporlamak kredibilite kaybettirir: jüri "toleransı
sonuç iyi görünene kadar mı büyüttünüz?" diye sorar ve haklı olur. Tek başına
**katı** metrik ise gerçek olmayan bir başarısızlık üretir: `%1,89` yerine
`1.8900000000000001` yazan bir float, anlam olarak aynı bilgidir.

Çözüm ikisini birlikte raporlamak. `strict` alt sınırdır (savunulabilir taban),
`tolerant` üst sınırdır (anlamsal eşdeğerlik). İkisi arasındaki fark, "kaç hata
gerçek anlam hatası değil, biçim hatası" sorusunun ölçüsüdür — ve o farkın
kendisi bir hata analizi çıktısıdır.

## Eski `run_eval._equal`'in yalanı (bu modülün varlık sebebi)

Eski docstring "dict/aralıkta alan-alan" karşılaştırma iddia ediyordu; kod ise
düz Python `==` yapıyordu. Sonuçları:

- `{"value": 500, "currency": "TRY"}` ile `{"value": 500.0, "currency": "TRY"}`
  Python'da eşit çıkar (şans eseri doğru), ama
  `{"min": 1.99, "max": 2.49}` ile `{"min": 1.9900000000000002, "max": 2.49}`
  eşit ÇIKMAZ — sayısal tolerans dict'in içine hiç inmiyordu.
- `{"has_fee": True}` ile `{"has_fee": 1}` eşit çıkar (`True == 1`), yani
  "masraf var" ile "1" karıştırılabilirdi.

Burada kod docstring'e uydurulmuştur: karşılaştırma yapıya İNER, `bool` önce
elenir, para biriminin eşleşmesi HER İKİ modda zorunludur.

## Zorunlu (toleranssız) bileşenler

Tolerans yalnız SAYISAL büyüklüğe uygulanır. Aşağıdakiler tolerant modda da
birebir eşleşmek zorundadır, çünkü bunlar büyüklük değil KATEGORİdir:

| Bileşen | Neden zorunlu |
|---|---|
| `currency` (para) | 500 TRY ile 500 USD aynı değer değildir |
| `has_fee` (masraf) | "masrafsız" ile "500 TL masraf" zıt bilgidir |
| `kind` (alışveriş puanı) | %5 oran ile 5 puan aynı şey değildir |
| `kampanya_suresi` (tarih) | ISO-8601 zaten kanonik; "yakın tarih" diye bir şey yok |
"""

from __future__ import annotations

import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.gold_schema import (
    DATE_FIELDS,
    FEE_FIELDS,
    LABEL_LIST_FIELDS,
    MONEY_FIELDS,
    POINTS_FIELDS,
    RATE_FIELDS,
    TEXT_LIST_FIELDS,
)
from src.preprocessing.clean import tr_fold_ascii

# Katı modda bile float gösterim gürültüsü hata sayılmaz: 1.89 ile
# 1.8900000000000001 aynı ondalık sayının iki gösterimidir.
STRICT_ABS_TOL = 1e-9

# Gevşek modda göreli tolerans. %1 seçildi çünkü kâr payı oranlarında anlamlı
# en küçük fark 0,01 puandır (%1,89 -> %1,90) ve bu ~%0,5'e denk gelir; %1
# bunu yutar ama %1,89 ile %2,49 farkını (~%32) asla yutmaz.
TOLERANT_REL_TOL = 0.01
TOLERANT_ABS_TOL = 1e-9

MATCHER_NAMES = ("strict", "tolerant")


class MatcherError(ValueError):
    """Bilinmeyen eşleştirici adı."""


def _is_number(v: Any) -> bool:
    """`bool` HARİÇ sayı mı? (Python'da `True` bir `int`'tir.)"""
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _num_close(a: float, b: float, *, rel_tol: float, abs_tol: float) -> bool:
    """Göreli + mutlak toleranslı sayı karşılaştırması (stdlib `isclose`)."""
    import math

    return math.isclose(float(a), float(b), rel_tol=rel_tol, abs_tol=abs_tol)


def _is_range(v: Any) -> bool:
    return isinstance(v, dict) and set(v) == {"min", "max"}


def _fold_text(v: str) -> str:
    """Serbest metni karşılaştırılabilir hale getirir (gevşek mod).

    Türkçe katlama + sondaki noktalamanın atılması. Gerekçe `eval/properties.py`
    ile aynı: "...saklı tutar" ile "...saklı tutar." AYNI koşuldur; noktalama
    bilgi taşımaz.
    """
    return tr_fold_ascii(v).strip().rstrip(" .,;:!?")


# --------------------------------------------------------------------------- #
# Sonuç tipi
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Match:
    """Bir eşleştirme kararı ve GEREKÇESİ.

    `reason` hata analizinde kullanılır: "neden eşleşmedi" sorusunun cevabı
    metriğin yanında dursun ki tolerans tartışması veriyle yapılabilsin.
    """

    ok: bool
    reason: str = ""

    def __bool__(self) -> bool:
        return self.ok


_OK = Match(True, "")


# --------------------------------------------------------------------------- #
# Katı (strict) eşleştirme
# --------------------------------------------------------------------------- #
def strict_match(field_name: str, pred: Any, gold: Any) -> Match:
    """Kanonik biçim birebir aynı mı? (float gürültüsü hariç tolerans yok)

    - `bool` kimlikle karşılaştırılır (`True is not 1`).
    - Sözlükler ANAHTAR KÜMESİ + değer değer; aralık `min`/`max` alan-alan.
    - Listeler SIRALI ve uzunluk eşit.
    - Metin birebir (katlama yok).

    Args:
        field_name: alan adı (tip ailesini belirler).
        pred: tahmin edilen kanonik değer.
        gold: gold kanonik değer.
    """
    return _deep_equal(field_name, pred, gold,
                       rel_tol=0.0, abs_tol=STRICT_ABS_TOL,
                       fold_text=False, unordered_lists=False,
                       scalar_in_range=False)


# --------------------------------------------------------------------------- #
# Gevşek (tolerant) eşleştirme
# --------------------------------------------------------------------------- #
def tolerant_match(field_name: str, pred: Any, gold: Any) -> Match:
    """Anlamsal eşdeğerlik — biçim gürültüsü affedilir, KATEGORİ affedilmez.

    Katıdan farkları (yalnızca bunlar):
      1. Sayılarda %1 göreli tolerans (`TOLERANT_REL_TOL`).
      2. Etiket/metin listelerinde SIRA önemsiz (küme karşılaştırması) ve
         serbest metin Türkçe katlanır.
      3. Aralık ile düz sayı arasında kısmi kredi: gold aralık, tahmin sayı ve
         sayı aralığın İÇİNDEyse eşleşme sayılır. Gerekçe: "%1,99 - %2,49"
         metninden %1,99 çıkarmak, hiçbir şey çıkarmamaktan farklıdır ve
         dashboard'da doğru bilgiyi gösterir. Katı modda bu bir hatadır.

    `currency`, `has_fee`, `kind` ve tarih burada da BİREBİR eşleşmek zorundadır
    (bkz. modül başlığı).
    """
    return _deep_equal(field_name, pred, gold,
                       rel_tol=TOLERANT_REL_TOL, abs_tol=TOLERANT_ABS_TOL,
                       fold_text=True, unordered_lists=True,
                       scalar_in_range=True)


# --------------------------------------------------------------------------- #
# Ortak çekirdek
# --------------------------------------------------------------------------- #
def _deep_equal(field_name: str, pred: Any, gold: Any, *,
                rel_tol: float, abs_tol: float,
                fold_text: bool, unordered_lists: bool,
                scalar_in_range: bool) -> Match:
    """İki eşleştiricinin paylaştığı tek gövde — davranış farkı yalnız bayraklarda.

    Tek gövde olması kasıtlıdır: iki ayrı kopya zamanla ayrışır ve o zaman
    "strict ile tolerant arasındaki fark" ölçümü anlamını yitirir.
    """
    # --- para: birim ZORUNLU, tutar toleranslı -------------------------------
    if field_name in MONEY_FIELDS:
        if not (isinstance(pred, dict) and isinstance(gold, dict)):
            return Match(False, f"para bekleniyordu, {type(pred).__name__} geldi")
        if set(pred) != set(gold):
            return Match(False, f"para anahtarları farklı: {sorted(pred)} != {sorted(gold)}")
        if pred.get("currency") != gold.get("currency"):
            return Match(False, f"para birimi farklı: {pred.get('currency')!r} != "
                                f"{gold.get('currency')!r}")
        if not (_is_number(pred.get("value")) and _is_number(gold.get("value"))):
            return Match(False, "para value sayı değil")
        if not _num_close(pred["value"], gold["value"], rel_tol=rel_tol, abs_tol=abs_tol):
            return Match(False, f"tutar farklı: {pred['value']} != {gold['value']}")
        return _OK

    # --- masraf durumu: has_fee ZORUNLU, amount toleranslı -------------------
    if field_name in FEE_FIELDS:
        if not (isinstance(pred, dict) and isinstance(gold, dict)):
            return Match(False, "masraf_durumu sözlük olmalı")
        if set(pred) != set(gold):
            return Match(False, f"anahtarlar farklı: {sorted(pred)} != {sorted(gold)}")
        if pred.get("has_fee") is not gold.get("has_fee"):
            return Match(False, f"has_fee farklı: {pred.get('has_fee')!r} != "
                                f"{gold.get('has_fee')!r}")
        return _scalar_or_null(pred.get("amount"), gold.get("amount"),
                               rel_tol=rel_tol, abs_tol=abs_tol, label="amount")

    # --- alışveriş puanı: kind ZORUNLU, value toleranslı ---------------------
    if field_name in POINTS_FIELDS:
        if not (isinstance(pred, dict) and isinstance(gold, dict)):
            return Match(False, "alisveris_puani sözlük olmalı")
        if set(pred) != set(gold):
            return Match(False, f"anahtarlar farklı: {sorted(pred)} != {sorted(gold)}")
        if pred.get("kind") != gold.get("kind"):
            return Match(False, f"kind farklı: {pred.get('kind')!r} != {gold.get('kind')!r}")
        return _scalar_or_null(pred.get("value"), gold.get("value"),
                               rel_tol=rel_tol, abs_tol=abs_tol, label="value")

    # --- oran: düz sayı YA DA aralık; aralık ALAN-ALAN -----------------------
    if field_name in RATE_FIELDS:
        return _rate_equal(pred, gold, rel_tol=rel_tol, abs_tol=abs_tol,
                           scalar_in_range=scalar_in_range)

    # --- tarih: toleranssız --------------------------------------------------
    if field_name in DATE_FIELDS:
        if not (isinstance(pred, str) and isinstance(gold, str)):
            return Match(False, "tarih metin olmalı")
        return _OK if pred == gold else Match(False, f"tarih farklı: {pred!r} != {gold!r}")

    # --- etiket listesi (hedef_kitle) ---------------------------------------
    if field_name in LABEL_LIST_FIELDS:
        return _list_equal(pred, gold, unordered=unordered_lists, fold=False)

    # --- serbest metin listesi (kampanya_kosullari) --------------------------
    if field_name in TEXT_LIST_FIELDS:
        return _list_equal(pred, gold, unordered=unordered_lists, fold=fold_text)

    # --- tamsayı alanları (vade_ay, taksit_sayisi) ---------------------------
    return _scalar_or_null(pred, gold, rel_tol=rel_tol, abs_tol=abs_tol, label=field_name)


def _scalar_or_null(pred: Any, gold: Any, *, rel_tol: float, abs_tol: float,
                    label: str) -> Match:
    """Sayı / None / bool / metin skaler karşılaştırması.

    `bool` ÖNCE elenir: `True == 1` tuzağı (bkz. modül başlığı).
    """
    if isinstance(pred, bool) or isinstance(gold, bool):
        return _OK if pred is gold else Match(False, f"{label}: {pred!r} != {gold!r}")
    if pred is None or gold is None:
        return _OK if pred is gold else Match(False, f"{label}: {pred!r} != {gold!r}")
    if _is_number(pred) and _is_number(gold):
        if _num_close(pred, gold, rel_tol=rel_tol, abs_tol=abs_tol):
            return _OK
        return Match(False, f"{label}: {pred} != {gold}")
    return _OK if pred == gold else Match(False, f"{label}: {pred!r} != {gold!r}")


def _rate_equal(pred: Any, gold: Any, *, rel_tol: float, abs_tol: float,
                scalar_in_range: bool) -> Match:
    """Oran karşılaştırması — aralık `min`/`max` ALAN-ALAN.

    Dört durum: sayı-sayı, aralık-aralık, aralık-sayı, sayı-aralık.
    Son ikisi katı modda hatadır; gevşek modda sayı aralığın içindeyse kabul
    edilir (bkz. `tolerant_match` gerekçesi).
    """
    p_rng, g_rng = _is_range(pred), _is_range(gold)

    if p_rng and g_rng:
        for key in ("min", "max"):
            if not (_is_number(pred[key]) and _is_number(gold[key])):
                return Match(False, f"aralık {key} sayı değil")
            if not _num_close(pred[key], gold[key], rel_tol=rel_tol, abs_tol=abs_tol):
                return Match(False, f"aralık {key} farklı: {pred[key]} != {gold[key]}")
        return _OK

    if p_rng != g_rng:
        if not scalar_in_range:
            return Match(False, "biri aralık biri düz sayı (katı modda eşleşmez)")
        rng, scalar = (pred, gold) if p_rng else (gold, pred)
        if not _is_number(scalar):
            return Match(False, "aralık karşısındaki değer sayı değil")
        if not (_is_number(rng["min"]) and _is_number(rng["max"])):
            return Match(False, "aralık sınırları sayı değil")
        lo = float(rng["min"]) * (1 - rel_tol) - abs_tol
        hi = float(rng["max"]) * (1 + rel_tol) + abs_tol
        if lo <= float(scalar) <= hi:
            return Match(True, "aralık içinde skaler (kısmi kredi)")
        return Match(False, f"{scalar} aralığın dışında [{rng['min']}, {rng['max']}]")

    return _scalar_or_null(pred, gold, rel_tol=rel_tol, abs_tol=abs_tol, label="oran")


def _list_equal(pred: Any, gold: Any, *, unordered: bool, fold: bool) -> Match:
    """Liste karşılaştırması. `unordered=True` -> küme, aksi halde sıralı."""
    if not (isinstance(pred, list) and isinstance(gold, list)):
        return Match(False, f"liste bekleniyordu, {type(pred).__name__} geldi")

    def prep(items: list) -> list:
        return [_fold_text(x) if (fold and isinstance(x, str)) else x for x in items]

    p, g = prep(pred), prep(gold)
    if unordered:
        if set(map(repr, p)) == set(map(repr, g)):
            return _OK
        missing = sorted(set(map(repr, g)) - set(map(repr, p)))
        extra = sorted(set(map(repr, p)) - set(map(repr, g)))
        return Match(False, f"liste kümesi farklı (eksik={missing}, fazla={extra})")
    if len(p) != len(g):
        return Match(False, f"liste uzunluğu farklı: {len(p)} != {len(g)}")
    for i, (x, y) in enumerate(zip(p, g)):
        if x != y:
            return Match(False, f"liste[{i}] farklı: {x!r} != {y!r}")
    return _OK


# --------------------------------------------------------------------------- #
# Kayıt (registry)
# --------------------------------------------------------------------------- #
Matcher = Callable[[str, Any, Any], Match]

MATCHERS: dict[str, Matcher] = {
    "strict": strict_match,
    "tolerant": tolerant_match,
}

MATCHER_DESCRIPTIONS: dict[str, str] = {
    "strict": "kanonik biçim birebir (yalnız float gürültüsü affedilir)",
    "tolerant": ("sayılarda %1 göreli tolerans, liste sırası ve TR imla "
                 "önemsiz, aralık-içi skalere kısmi kredi"),
}


def get_matcher(name: str) -> Matcher:
    """Ada göre eşleştirici döndürür.

    Raises:
        MatcherError: ad tanınmıyorsa (sessiz varsayılana düşmek YOK — yanlış
            eşleştiriciyle üretilmiş bir metrik, hiç metrik olmamasından kötüdür).
    """
    try:
        return MATCHERS[name]
    except KeyError:
        raise MatcherError(
            f"bilinmeyen eşleştirici {name!r}. Seçenekler: "
            f"{', '.join(sorted(MATCHERS))}") from None


def resolve_matchers(spec: str) -> list[str]:
    """`strict` | `tolerant` | `both` -> eşleştirici adı listesi."""
    if spec == "both":
        return list(MATCHER_NAMES)
    get_matcher(spec)          # doğrula (bilinmiyorsa MatcherError)
    return [spec]


def describe(name: str) -> str | None:
    return MATCHER_DESCRIPTIONS.get(name)
