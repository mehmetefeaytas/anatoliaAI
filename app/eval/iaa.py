"""Anotatörler arası uyum (inter-annotator agreement) — SAF STDLIB.

İlgili: CLAUDE.md §16 (değerlendirme metodolojisi — kappa raporlanacak)
        data/gold/ANNOTATION_GUIDE.md §7 (önceden ilan edilmiş eşik politikası)
        scripts/report_iaa.py (bu modülü kullanan rapor üreticisi)

Üç ölçüt, üç farklı soru için:

  cohen_kappa        2 anotatör, kategorik karar (verdict: ok/fix/absent/unclear)
  fleiss_kappa       3-4 anotatör, kategorik karar (kalibrasyon turu)
  krippendorff_alpha herhangi sayıda anotatör + EKSİK DEĞER + sayısal ölçek

## Neden Krippendorff da gerekli

Cohen/Fleiss iki varsayım yapar: (1) her birim herkes tarafından etiketlenmiştir,
(2) etiketler kategoriktir — yani 1,89 ile 1,90 arasındaki uyuşmazlık, 1,89 ile
120 arasındaki uyuşmazlıkla AYNI ağırlıktadır.

İkisi de bizim verimizde yanlış. Anotatörler farklı alt kümelere bakar (eksik
değer normaldir) ve alanların çoğu sayısaldır. `%1,89` yerine `%1,90` yazan bir
anotatör "tamamen anlaşmazlık" sayılırsa kappa gerçekte olduğundan çok daha
kötü çıkar ve kılavuzu yanlış yerde revize ederiz. `ratio` ölçeği bu farkı
büyüklüğe oranlar; eksik değerleri de doğal biçimde eler.
"""

from __future__ import annotations

import math
from collections import Counter
from typing import Any, Iterable, Optional, Sequence

Label = Any
NAN = float("nan")


# --------------------------------------------------------------------------- #
# Cohen's kappa — 2 anotatör, kategorik
# --------------------------------------------------------------------------- #
def cohen_kappa(a: Sequence[Label], b: Sequence[Label]) -> float:
    """İki anotatörün kategorik kararları arasındaki Cohen's kappa.

    `None` içeren çiftler ATILIR (biri bakmamışsa uyum ölçülemez).

    Args:
        a, b: eşit uzunlukta etiket dizileri.

    Returns:
        kappa; ortak etiketlenmiş çift yoksa `nan`.
        Beklenen uyum 1.0 ise (herkes tek kategoriye yığılmış) 1.0 döner —
        `0/0` yerine "tam uyum" doğru yorumdur.

    Doğrulama (Wikipedia "Cohen's kappa" basit örneği): 50 birim,
    evet/evet=20, evet/hayır=5, hayır/evet=10, hayır/hayır=15 -> kappa = 0.40.
    """
    if len(a) != len(b):
        raise ValueError(f"dizi uzunlukları farklı: {len(a)} != {len(b)}")

    pairs = [(x, y) for x, y in zip(a, b) if x is not None and y is not None]
    total = len(pairs)
    if total == 0:
        return NAN

    agree = sum(1 for x, y in pairs if x == y)
    p_observed = agree / total

    count_a = Counter(x for x, _ in pairs)
    count_b = Counter(y for _, y in pairs)
    p_expected = sum(
        (count_a[label] / total) * (count_b[label] / total)
        for label in set(count_a) | set(count_b)
    )

    if math.isclose(p_expected, 1.0):
        return 1.0
    return (p_observed - p_expected) / (1.0 - p_expected)


# --------------------------------------------------------------------------- #
# Fleiss' kappa — 3+ anotatör, kategorik
# --------------------------------------------------------------------------- #
def fleiss_kappa(matrix: Sequence[Sequence[int]]) -> float:
    """Fleiss' kappa; `matrix[i][j]` = i. birimi j. kategoriye atayan anotatör sayısı.

    Satır toplamları (birim başına anotatör sayısı) eşit OLMAK ZORUNDA DEĞİLDİR;
    her birim kendi n_i'siyle hesaplanır (standart genelleme). Bu, Cuma günü
    biri 20 belgeyi bitiremezse tüm turu çöpe atmamak için gerekli.

    Returns:
        kappa; 2'den az anotatörlü birim kalmazsa `nan`.

    Doğrulama (Wikipedia "Fleiss' kappa" işlenmiş örneği): 10 birim × 14
    anotatör × 5 kategori -> P̄=0.378, P̄e=0.213, kappa=0.210.
    """
    rows = [list(row) for row in matrix if sum(row) >= 2]
    if not rows:
        return NAN

    width = len(rows[0])
    if any(len(row) != width for row in rows):
        raise ValueError("tüm satırlar aynı sayıda kategori sütunu içermeli")
    if any(value < 0 for row in rows for value in row):
        raise ValueError("kategori sayıları negatif olamaz")

    grand_total = sum(sum(row) for row in rows)
    # p_j: j kategorisinin tüm atamalar içindeki payı
    p_category = [sum(row[j] for row in rows) / grand_total for j in range(width)]

    # P_i: i birimindeki anotatör çiftlerinin hemfikir olma oranı
    agreements = []
    for row in rows:
        n_i = sum(row)
        agreements.append((sum(value * value for value in row) - n_i) / (n_i * (n_i - 1)))

    p_bar = sum(agreements) / len(agreements)
    p_expected = sum(p * p for p in p_category)

    if math.isclose(p_expected, 1.0):
        return 1.0
    return (p_bar - p_expected) / (1.0 - p_expected)


def fleiss_matrix(units: Iterable[Sequence[Label]],
                  categories: Optional[Sequence[Label]] = None
                  ) -> tuple[list[list[int]], list[Label]]:
    """Etiket listelerinden Fleiss sayım matrisi üretir. `None` etiketler atılır.

    Args:
        units: her birim için anotatör etiketleri (uzunlukları farklı olabilir).
        categories: sütun sırası; verilmezse veriden sıralanarak türetilir.
    """
    rows = [[label for label in unit if label is not None] for unit in units]
    if categories is None:
        categories = sorted({label for row in rows for label in row}, key=repr)
    index = {label: j for j, label in enumerate(categories)}

    matrix = []
    for row in rows:
        counts = [0] * len(categories)
        for label in row:
            counts[index[label]] += 1
        matrix.append(counts)
    return matrix, list(categories)


def fleiss_kappa_from_labels(units: Iterable[Sequence[Label]]) -> float:
    """`fleiss_matrix` + `fleiss_kappa` kısayolu."""
    matrix, _ = fleiss_matrix(units)
    return fleiss_kappa(matrix)


# --------------------------------------------------------------------------- #
# Krippendorff's alpha — n anotatör, eksik değer, nominal/interval/ratio
# --------------------------------------------------------------------------- #
def _delta_squared(level: str, x: Any, y: Any) -> float:
    """Ölçek farkı fonksiyonu δ²(x, y)."""
    if level == "nominal":
        return 0.0 if x == y else 1.0
    if level == "interval":
        return (float(x) - float(y)) ** 2
    if level == "ratio":
        total = float(x) + float(y)
        if total == 0.0:
            return 0.0
        return ((float(x) - float(y)) / total) ** 2
    raise ValueError(f"bilinmeyen ölçek: {level!r} (nominal|interval|ratio)")


def krippendorff_alpha(units: Iterable[Sequence[Optional[Label]]],
                       level: str = "nominal") -> float:
    """Krippendorff's alpha.

    Args:
        units: her birim (doc, alan) için anotatör değerlerinin listesi.
            `None` = o anotatör bu birime bakmadı. Doğal olarak elenir.
        level: "nominal" (kategorik) | "interval" (mutlak fark) |
            "ratio" (orantılı fark — %1,89 vs %1,90 neredeyse uyum sayılır).

    Returns:
        alpha; 2'den az değerli birim kalmazsa `nan`.
        Tüm değerler aynıysa (beklenen uyuşmazlık 0) 1.0 döner.

    Not: `interval`/`ratio` için değerler sayıya çevrilebilir olmalıdır.
    """
    if level not in ("nominal", "interval", "ratio"):
        raise ValueError(f"bilinmeyen ölçek: {level!r} (nominal|interval|ratio)")

    # Yalnızca EŞLENEBİLİR birimler: en az 2 değeri olanlar.
    pairable = [[v for v in unit if v is not None] for unit in units]
    pairable = [unit for unit in pairable if len(unit) >= 2]
    if not pairable:
        return NAN

    if level in ("interval", "ratio"):
        pairable = [[float(v) for v in unit] for unit in pairable]

    n_total = sum(len(unit) for unit in pairable)
    if n_total < 2:
        return NAN

    # Gözlenen uyuşmazlık: birim içi tüm sıralı çiftler, m_u-1 ile ağırlıklı.
    observed = 0.0
    for unit in pairable:
        m_u = len(unit)
        unit_sum = 0.0
        for i in range(m_u):
            for j in range(m_u):
                if i != j:
                    unit_sum += _delta_squared(level, unit[i], unit[j])
        observed += unit_sum / (m_u - 1)
    observed /= n_total

    # Beklenen uyuşmazlık: tüm değerler tek torbaya atılıp sıralı çiftler.
    bag = Counter(value for unit in pairable for value in unit)
    values = list(bag)
    expected = 0.0
    for i, x in enumerate(values):
        for j, y in enumerate(values):
            if i != j:
                expected += bag[x] * bag[y] * _delta_squared(level, x, y)
    expected /= n_total * (n_total - 1)

    if expected == 0.0:
        # Torbadaki her değer aynı -> uyuşmazlık imkânsız, tam uyum.
        return 1.0
    return 1.0 - observed / expected


# --------------------------------------------------------------------------- #
# Eşik politikası — ÖNCEDEN İLAN EDİLMİŞTİR (ANNOTATION_GUIDE.md §7)
# --------------------------------------------------------------------------- #
# Eşikleri sonuçları gördükten sonra belirlemek, kendi kendini onaylayan bir
# ölçümdür. Bu tablo anotasyon BAŞLAMADAN sabitlenmiştir; sayı ne çıkarsa
# çıksın kural değişmez.
KAPPA_ACCEPT = 0.80
KAPPA_MARGINAL = 0.67


def interpret_kappa(value: float) -> tuple[str, str]:
    """Kappa/alpha değerini önceden ilan edilmiş politikaya göre yorumlar.

    Returns:
        (durum, yapılacak iş) — durum: "kabul" | "notla" | "hakemlik".
    """
    if value != value:  # nan
        return ("olcusuz", "Ortak anote edilmiş birim yok; çift anotasyon "
                           "alt kümesi gerçekten paylaşıldı mı kontrol et.")
    if value >= KAPPA_ACCEPT:
        return ("kabul", "Gold güvenilir. Ana geçişe devam.")
    if value >= KAPPA_MARGINAL:
        return ("notla", "Kabul edilir ama raporda AÇIKÇA not düşülür; "
                         "uyuşmazlık listesi gözden geçirilir.")
    return ("hakemlik", "ZORUNLU hakemlik + kılavuz revizyonu. Etkilenen "
                        "alanlar yeniden anote edilir.")
