"""Kural katmanı için GERÇEK güven skoru — saf stdlib, deterministik.

İlgili: ../../../decisions/daraltilmis-yenilikcilik-hedefleri.md (hedef #1)
        CLAUDE.md §18, şartname §7 "Model Başarısı" (%30)

## Neden bu modül var

Kural katmanı eskiden her alana sabit `0.95` veriyordu. Sabit skorun üç sorunu
var ve üçü de doğrudan en yüksek puanlı rubrik kalemini vuruyor:

1. **Kalibre edilemez.** ECE / güvenilirlik diyagramı sabit bir skor üzerinde
   tanımsızdır — tek bir bin'e düşer.
2. **Abstain eşiği işe yaramaz.** Hiçbir eşik "emin" ile "emin değil"i ayıramaz.
3. **Savunulamaz.** Jüri "bu 0.95 nasıl hesaplandı?" diye sorduğunda cevap yok.

Rubriğin %30'luk kaleminin alt kriteri birebir şu: *"Eksik veya farklı yazılmış
bilgiler karşısında doğru sonuç üretebilmesi."* Bir sistemin bunu gösterme yolu
**ne zaman emin olmadığını bilmesidir**.

## Yaklaşım

Regex eşleşmesi sırasında zaten elimizde olan, ek maliyeti sıfır kanıt
sinyallerinden bir skor üretilir:

- **Tetikleyici yakınlığı:** değer, alanın anahtar sözcüğüne ne kadar yakın?
  "kâr payı oranı %1,89" (bitişik) >> metnin başka yerindeki başıboş bir "%1,89".
- **Normalizasyon başarısı:** kanonik forma çevrilebildi mi?
- **Makullük:** değer, alanın gerçek dünyadaki aralığında mı? Aylık kâr payı
  %900 ise bu bir ayrıştırma hatasıdır, gerçek bir teklif değil.
- **Belirsizlik:** metinde aynı alan için birden çok aday var mı?

Skorlar **kalibre edilmemiştir** — sadece sıralayıcıdır (daha yüksek = daha
güvenilir). Gerçek kalibrasyon `eval/calibration.py`'de gold set üzerinde
sıcaklık ölçekleme ile yapılacak. Bu ayrım `confidence_source` alanında
kayıtlıdır.
"""

from __future__ import annotations

import re
from typing import Any, Optional

# Taban skor: kural eşleşti, normalizasyon başarılı, başka bilgi yok.
BASE = 0.70

# Tetikleyici anahtar sözcük değere bitişikse verilen ödül.
ADJACENT_BONUS = 0.25      # <= 15 karakter
NEAR_BONUS = 0.12          # <= 60 karakter
FAR_PENALTY = -0.15        # tetikleyici hiç yok / çok uzak

# Diğer düzeltmeler
IMPLAUSIBLE_PENALTY = -0.45   # değer makul aralığın dışında
AMBIGUITY_PENALTY = -0.10     # metinde birden çok aday eşleşme
RANGE_PENALTY = -0.05         # aralık (%1,99–%2,49): nokta değerden az kesin
CHROME_PENALTY = -0.30        # kanıt gezinme/SSS bağlamında (aşağıya bakın)

FLOOR, CEIL = 0.05, 0.98

# --------------------------------------------------------------------------- #
# Gezinme / SSS bağlamı — ÖLÇÜLMÜŞ ayrışma
# --------------------------------------------------------------------------- #
# Neden gerekli: `alisveris_puani` alanında 41 belge, site kromundaki
# "Kredi Notu (Kredi Puanı) Nedir?" gezinme bağlantısından **0,95 güvenle**
# değer üretiyordu. 0,95 aynı zamanda DOĞRU alanların da modu (612 kayıt), yani
# hiçbir eşik ikisini ayıramıyordu ve `reconcile.verify_low_conf` kolu bu yüzden
# yapısal olarak ölüydü (bkz. docs/rapor/ablasyon.md §7b).
#
# Ölçüm (`data/gold/preannotations.json`, 945 alan):
#   krom kaynaklı kayıtlar : 82/82  (%100) hem nav işareti hem "?" taşıyor
#   diğer kayıtlar         : 29/863 (%3,4) taşıyor
#
# VETO DEĞİL CEZA, ve sebebi ölçüldü: sinyali tetikleyen o 29 kayıt KARIŞIK.
# Bir kısmı gerçek ("Hesap açılışı için minimum tutar 50.000 TL" — SSS cevabı
# ama doğru), bir kısmı yanlış ("Findeks Kredi Notu, 12 ay boyunca borç ödeme
# olasılığını..." -> vade_ay 12; "07.06.2013 tarihli Resmî Gazete" -> kampanya
# süresi). Soru-cevap bağlamındaki kanıt gerçekten daha az kesindir; doğru
# davranış değeri SİLMEK değil (halüsinasyon yasağının ikizi: sessiz silme de
# yasak) güveni düşürüp doğrulamaya açık hâle getirmek.
#
# İki koşul BİRLİKTE aranıyor. Tek başına "nedir" ya da tek başına "?" çok
# gevşek: bu depoda bir kez, tek sözcüklü bir sezgisel ("ana sayfa"/"müşteri ol")
# 101 belgenin 87'sinde yanlış pozitif üretti — o sözcükler bazı bankaların HER
# sayfasındaki kırıntı yolunda geçiyor.
_CHROME_NAV_RE = re.compile(
    r"nedir|nas[ıi]l\s|ne\s*i[şs]e\s*yarar|s[ıi]k[çc]a\s*sorulan|"
    r"detayl[ıi]\s*bilgi|kampanyay[ıi]\s*ke[şs]fet",
    re.IGNORECASE,
)


def looks_like_chrome(window: Optional[str]) -> bool:
    """Kanıt penceresi gezinme/SSS bağlamına mı benziyor?

    Pencere düzeyinde çalışır, BELGE düzeyinde değil — "bu belge kromdur" demek
    ölçülmüş bir hata sınıfıydı. Buradaki iddia yalnızca "bu değerin hemen
    çevresi soru-cevap/gezinme metnine benziyor".
    """
    if not window:
        return False
    return bool(_CHROME_NAV_RE.search(window)) and "?" in window


# --------------------------------------------------------------------------- #
# Makullük aralıkları
# --------------------------------------------------------------------------- #
# Kaynak: katılım bankacılığı gerçek ürün aralıkları. Amaç halüsinasyonu ve
# ayrıştırma hatasını yakalamak, meşru teklifi elemek DEĞİL — bu yüzden sınırlar
# geniş tutulur. Aralık dışı değer SİLİNMEZ, sadece güveni düşer ve
# `eval/errors_sample.jsonl`'a düşer (bkz. CLAUDE.md §21 halüsinasyon yasağı:
# uydurma yok, ama şüpheli olanı da gizleme).
PLAUSIBLE_RANGES: dict[str, tuple[float, float]] = {
    "kar_payi_orani": (0.0, 15.0),        # aylık % — yıllıklar da bu bandın üstü
    "indirim_orani": (0.0, 100.0),
    "vade_ay": (1, 480),                  # 40 yıl üst sınır
    "taksit_sayisi": (1, 480),
    "finansman_tutari": (100.0, 100_000_000.0),
    "tahsis_ucreti": (0.0, 1_000_000.0),
    "odul_miktari": (0.0, 10_000_000.0),
    "alisveris_puani": (0.0, 10_000_000.0),
}


def _numerics(value: Any) -> list[float]:
    """Kanonik değerdeki TÜM sayısal bileşenleri döndürür.

    Aralıklarda hem `min` hem `max` kontrol edilmeli: yalnız `min`e bakmak,
    `{min: 1.89, max: 120.0}` gibi bozuk bir aralığı (bir vadenin oran üst
    sınırı sanılması) makul göstererek gizler.
    """
    if isinstance(value, bool):
        return []
    if isinstance(value, (int, float)):
        return [float(value)]
    if isinstance(value, dict):
        out = []
        for key in ("value", "amount", "min", "max"):
            v = value.get(key)
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                out.append(float(v))
        return out
    return []


def is_plausible(field_name: str, canonical: Any) -> Optional[bool]:
    """Değer alanın makul aralığında mı?

    `None` döner = bu alan için aralık tanımlı değil ya da değer sayısal değil
    (ör. `masraf_durumu` sözlüğü, tarih dizesi). Karar verilemiyorsa ceza yok.
    """
    rng = PLAUSIBLE_RANGES.get(field_name)
    if rng is None:
        return None
    nums = _numerics(canonical)
    if not nums:
        return None
    lo, hi = rng
    # TÜM bileşenler aralıkta olmalı — biri bile dışarıdaysa değer şüphelidir.
    return all(lo <= n <= hi for n in nums)


# --------------------------------------------------------------------------- #
# Skor
# --------------------------------------------------------------------------- #
def score(
    field_name: str,
    canonical: Any,
    *,
    trigger_distance: Optional[int] = None,
    candidate_count: int = 1,
    window: Optional[str] = None,
) -> tuple[float, str]:
    """Bir kural çıkarımı için güven skoru ve gerekçesini döndürür.

    Args:
        field_name: alan adı (makullük aralığı için).
        canonical: normalize edilmiş değer. `None` ise güven 0.
        trigger_distance: değer ile alanın tetikleyici anahtar sözcüğü
            arasındaki karakter uzaklığı. `None` = tetikleyici bulunamadı.
        candidate_count: metinde bu alan için kaç aday eşleşme vardı.
        window: değerin çevresindeki kanıt penceresi. Verilirse gezinme/SSS
            bağlamı cezası uygulanır (bkz. `looks_like_chrome`). Verilmezse
            eski davranış korunur — ceza yok.

    Returns:
        (skor, gerekçe) — gerekçe insan okunur, UI'da ve hata analizinde
        gösterilir (açıklanabilirlik).
    """
    if canonical is None:
        return 0.0, "normalize edilemedi"

    s = BASE
    reasons: list[str] = []

    # 1) Tetikleyici yakınlığı
    if trigger_distance is None:
        s += FAR_PENALTY
        reasons.append("tetikleyici sözcük yok")
    elif trigger_distance <= 15:
        s += ADJACENT_BONUS
        reasons.append("tetikleyiciye bitişik")
    elif trigger_distance <= 60:
        s += NEAR_BONUS
        reasons.append("tetikleyiciye yakın")
    else:
        s += FAR_PENALTY
        reasons.append(f"tetikleyici uzak ({trigger_distance} kr)")

    # 2) Makullük
    plaus = is_plausible(field_name, canonical)
    if plaus is False:
        s += IMPLAUSIBLE_PENALTY
        reasons.append("değer makul aralık dışı")
    elif plaus is True:
        reasons.append("makul aralıkta")

    # 3) Belirsizlik
    if candidate_count > 1:
        s += AMBIGUITY_PENALTY
        reasons.append(f"{candidate_count} aday eşleşme")

    # 4) Aralık değeri nokta değerden daha az kesindir
    if isinstance(canonical, dict) and "min" in canonical and "max" in canonical:
        s += RANGE_PENALTY
        reasons.append("aralık değeri")

    # 5) Kanıt gezinme/SSS bağlamında mı?
    if looks_like_chrome(window):
        s += CHROME_PENALTY
        reasons.append("kanıt gezinme/SSS bağlamında")

    s = max(FLOOR, min(CEIL, s))
    return round(s, 3), "; ".join(reasons)
