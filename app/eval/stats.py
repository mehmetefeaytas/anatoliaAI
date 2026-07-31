"""İstatistiksel testler — SAF STDLIB (numpy/scipy YOK).

İlgili: ../../syntheses/teslim-ve-degerlendirme-rehberi.md
        eval/iaa.py (aynı "saf stdlib" kısıtı)
        CLAUDE.md §16

## Neden sıfır bağımlılık

Eval katmanı bugün hiçbir üçüncü parti pakete bağlı değil ve bu, on-prem
iddiasının parçası: değerlendirme hattı, internet erişimi ve paket kurulumu
olmayan bir kurum ağında birebir tekrar üretilebilir. Bootstrap ve McNemar
elle yazıldı; `math.erfc` ve `math.comb` stdlib'dedir.

## Neden GÜVEN ARALIĞI, neden nokta tahmini yetmez

"F1 = 0,86" ile "F1 = 0,86 [0,79 – 0,92]" arasındaki fark, jüri karşısında
iddia ile kanıt arasındaki farktır. 250 belgelik bir gold sette ikinci bir
model %2 daha iyi çıktıysa, bu fark gürültü olabilir. GA'sız karşılaştırma bu
soruyu cevaplayamaz.

## Neden BELGE düzeyinde yeniden örnekleme (bu dosyanın en kritik kararı)

Bir belgeden 12 alan çıkar ve bu 12 gözlem BAĞIMSIZ DEĞİLDİR: aynı metin, aynı
banka şablonu, aynı imla, aynı hata kaynağı. Bir belge zor bir tabloya sahipse
o belgedeki birkaç alan birlikte yanlış olur.

Alan düzeyinde yeniden örneklersek bağımsızlık varsayımı ihlal edilir ve GA
**yapay olarak dar** çıkar. Bu bir tercih değil, İSTATİSTİKSEL BİR HATADIR:
gerçekte anlamsız olan farkları anlamlı gösterir. `bootstrap_ci` bu yüzden
örnekleme birimi olarak BELGEyi alır ve seçilen belgenin TÜM alanları birlikte
gelir (küme bootstrap / cluster bootstrap).

## Determinizm

Tüm rastgelelik `random.Random(seed)` üzerinden akar; `seed` varsayılan 42 ve
sonuçta geri döndürülür. Aynı seed + aynı veri = aynı GA. Raporda seed
olmayan bir GA tekrar üretilemez, dolayısıyla kanıt değildir.
"""

from __future__ import annotations

import math
import random
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import TypeVar

DEFAULT_SEED = 42
DEFAULT_RESAMPLES = 1000
DEFAULT_CONFIDENCE = 0.95

# McNemar'da tam binom ile χ² yaklaşımı arasındaki sınır (klasik eşik;
# Wikipedia "McNemar's test" ve Agresti, *Categorical Data Analysis*).
#
# Gerekçe: χ², KESİKLİ binom dağılımına yapılan SÜREKLİ bir yaklaşımdır ve
# b+c küçükken bu yaklaşımın hatası göreli olarak büyür. Hata tek yönlü
# DEĞİLDİR — süreklilik düzeltmesiyle genelde konservatif (p olduğundan
# büyük) çıkar ama bazı (b, c) çiftlerinde ters döner:
#
#     b=8,  c=0 -> tam 0,0078  χ² 0,0133   (%70 göreli hata, konservatif)
#     b=3,  c=1 -> tam 0,6250  χ² 0,6171   (anti-konservatif)
#
# Yani "yaklaşım hep lehimize/aleyhimize" diyemeyiz; diyebileceğimiz şey,
# küçük örneklemde p-değerinin GÜVENİLMEZ olduğudur. Tam binom testi ise
# kesikli dağılımın kendisidir ve her b, c için geçerlidir. Bizim gold
# setimizde (250 belge hedefi) alan başına uyumsuz çift sayısı tek haneli
# kalabilir; bu eşik teorik bir süs değil.
EXACT_THRESHOLD = 25

T = TypeVar("T")


# --------------------------------------------------------------------------- #
# Yardımcılar
# --------------------------------------------------------------------------- #
def percentile(values: Sequence[float], q: float) -> float:
    """`q` yüzdelik dilim (0–100), doğrusal aradeğerleme.

    NumPy'ın `linear` (varsayılan) yöntemiyle aynı tanım; stdlib'de karşılığı
    olmadığı için elle yazıldı (`statistics.quantiles` kenar dilimlerde farklı
    davranır ve tek elemanlı diziyi reddeder).
    """
    if not values:
        raise ValueError("boş dizinin yüzdeliği yok")
    if not 0.0 <= q <= 100.0:
        raise ValueError(f"q [0, 100] aralığında olmalı, {q} geldi")
    ordered = sorted(values)
    if len(ordered) == 1:
        return float(ordered[0])
    pos = (len(ordered) - 1) * (q / 100.0)
    lo = math.floor(pos)
    hi = math.ceil(pos)
    if lo == hi:
        return float(ordered[int(pos)])
    return float(ordered[lo] + (ordered[hi] - ordered[lo]) * (pos - lo))


def chi2_sf_1df(x: float) -> float:
    """1 serbestlik dereceli χ² dağılımının sağ kuyruğu: P(X > x).

    Kapalı biçim: `erfc(sqrt(x/2))`. scipy gerekmez.

    Doğrulama: x = 3.841459 -> 0.05 (klasik %5 kritik değer).
    """
    if x <= 0:
        return 1.0
    return math.erfc(math.sqrt(x / 2.0))


def binom_two_sided_p(b: int, c: int) -> float:
    """İki yanlı tam binom testi p-değeri (H0: p = 0,5, n = b + c).

    p = 2 · Σ_{k=0}^{min(b,c)} C(n, k) · 0,5^n, 1,0 ile sınırlanır.

    Doğrulama: b=1, c=4 -> 2·(C(5,0)+C(5,1))/32 = 12/32 = 0,375.
               b=0, c=5 -> 2·1/32 = 0,0625.
    """
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    tail = sum(math.comb(n, i) for i in range(k + 1)) / (2.0 ** n)
    return min(1.0, 2.0 * tail)


# --------------------------------------------------------------------------- #
# Bootstrap güven aralığı
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class BootstrapResult:
    """Yüzdelikli (percentile) bootstrap güven aralığı.

    point: gerçek veri üzerindeki nokta tahmini (yeniden örneklenmemiş).
    low/high: GA sınırları.
    n_units: kaç BELGE üzerinden örneklendi (alan sayısı DEĞİL).
    """

    point: float
    low: float
    high: float
    confidence: float
    n_resamples: int
    n_units: int
    seed: int
    method: str = "percentile"
    unit: str = "document"

    @property
    def width(self) -> float:
        return self.high - self.low

    def as_dict(self) -> dict:
        return {
            "point": self.point, "low": self.low, "high": self.high,
            "width": self.width, "confidence": self.confidence,
            "n_resamples": self.n_resamples, "n_units": self.n_units,
            "seed": self.seed, "method": self.method, "unit": self.unit,
        }

    def fmt(self, digits: int = 3) -> str:
        """`0.860 [0.790–0.920]` biçiminde tek satır."""
        return (f"{self.point:.{digits}f} "
                f"[{self.low:.{digits}f}–{self.high:.{digits}f}]")


def bootstrap_ci(units: Sequence[T],
                 statistic: Callable[[Sequence[T]], float],
                 *,
                 n_resamples: int = DEFAULT_RESAMPLES,
                 confidence: float = DEFAULT_CONFIDENCE,
                 seed: int = DEFAULT_SEED,
                 unit_name: str = "document") -> BootstrapResult:
    """%95 (varsayılan) yüzdelikli bootstrap GA — BELGE düzeyinde örnekleme.

    `units` listesinin her öğesi BİR BELGEnin tüm katkısıdır (ör. o belgedeki
    tüm alanların TP/FP/FN sayaçları). Yeniden örnekleme bu birimler üzerinden
    yapılır; bir belge seçildiğinde o belgenin TÜM alanları birlikte gelir.

    NEDEN böyle: aynı belgeden çıkan 12 alan bağımsız değildir (aynı metin,
    aynı imla, aynı hata kaynağı). Alan düzeyinde örneklemek bağımsızlık
    varsayımını ihlal eder ve GA'yı YAPAY OLARAK DARALTIR — yani gerçekte
    gürültü olan farkları anlamlı gösterir. Bu istatistiksel bir hatadır, üslup
    tercihi değildir. (Ayrıntı: modül başlığı.)

    Args:
        units: örnekleme birimleri (belge başına bir öğe).
        statistic: birim listesinden tek sayı üreten fonksiyon (ör. mikro-F1).
        n_resamples: yeniden örnekleme sayısı (1000 varsayılan).
        confidence: (0, 1) aralığında güven düzeyi.
        seed: `random.Random` çekirdeği — determinizm için.
        unit_name: rapora yazılacak birim adı.

    Returns:
        `BootstrapResult`. `units` boşsa nokta tahmini `statistic([])` olur ve
        GA sıfır genişlikte döner (yalan söylemez: örnek yoksa belirsizlik
        tahmin edilemez).

    Dejenere girdi: tüm birimler aynı ve istatistik onlara göre sabitse GA
    genişliği 0 çıkar. Bu doğru davranıştır ve testte sabitlenmiştir.
    """
    if not 0.0 < confidence < 1.0:
        raise ValueError(f"confidence (0, 1) aralığında olmalı, {confidence} geldi")
    if n_resamples < 1:
        raise ValueError(f"n_resamples >= 1 olmalı, {n_resamples} geldi")

    point = float(statistic(units))
    n = len(units)
    if n == 0:
        return BootstrapResult(point, point, point, confidence, n_resamples,
                               0, seed, unit=unit_name)

    rng = random.Random(seed)
    samples: list[float] = []
    for _ in range(n_resamples):
        # Küme bootstrap: n belge, YERİNE KOYARAK seçilir.
        draw = [units[rng.randrange(n)] for _ in range(n)]
        samples.append(float(statistic(draw)))

    alpha = (1.0 - confidence) / 2.0
    low = percentile(samples, alpha * 100.0)
    high = percentile(samples, (1.0 - alpha) * 100.0)
    return BootstrapResult(point, low, high, confidence, n_resamples, n, seed,
                           unit=unit_name)


def bootstrap_diff_ci(units: Sequence[T],
                      statistic_a: Callable[[Sequence[T]], float],
                      statistic_b: Callable[[Sequence[T]], float],
                      *,
                      n_resamples: int = DEFAULT_RESAMPLES,
                      confidence: float = DEFAULT_CONFIDENCE,
                      seed: int = DEFAULT_SEED,
                      unit_name: str = "document") -> BootstrapResult:
    """İki konfigürasyon FARKININ (A − B) GA'sı — EŞLEŞMİŞ örnekleme.

    Aynı yeniden örneklenmiş belge kümesi her iki istatistiğe verilir. Bu
    eşleştirme kritiktir: iki bağımsız GA'nın çakışıp çakışmadığına bakmak
    yaygın bir hatadır ve farkın anlamlılığını YANLIŞ ölçer. GA sıfırı
    içermiyorsa fark ilgili düzeyde anlamlıdır.
    """
    def diff(sample: Sequence[T]) -> float:
        return float(statistic_a(sample)) - float(statistic_b(sample))

    return bootstrap_ci(units, diff, n_resamples=n_resamples,
                        confidence=confidence, seed=seed, unit_name=unit_name)


# --------------------------------------------------------------------------- #
# McNemar testi
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class McNemarResult:
    """Eşleşmiş çiftlerde McNemar testi sonucu.

    b: A doğru & B yanlış (A'nın lehine uyumsuzluk)
    c: A yanlış & B doğru (B'nin lehine uyumsuzluk)
    n_agree_correct / n_agree_wrong: uyumlu çiftler — teste GİRMEZ, yalnız
        raporlanır (ikisi de doğru ya da ikisi de yanlışsa test bilgi almaz).
    method: "exact_binomial" | "chi2_continuity"
    statistic: χ² istatistiği (tam binom kullanıldıysa `None`).
    """

    b: int
    c: int
    p_value: float
    method: str
    n_agree_correct: int = 0
    n_agree_wrong: int = 0
    statistic: float | None = None
    alpha: float = 0.05

    @property
    def n_discordant(self) -> int:
        return self.b + self.c

    @property
    def n_pairs(self) -> int:
        return self.b + self.c + self.n_agree_correct + self.n_agree_wrong

    @property
    def significant(self) -> bool:
        return self.p_value < self.alpha

    @property
    def winner(self) -> str | None:
        """Anlamlı fark varsa kazanan taraf ("A" | "B"), yoksa `None`."""
        if not self.significant or self.b == self.c:
            return None
        return "A" if self.b > self.c else "B"

    def as_dict(self) -> dict:
        return {
            "b": self.b, "c": self.c, "n_discordant": self.n_discordant,
            "n_pairs": self.n_pairs,
            "n_agree_correct": self.n_agree_correct,
            "n_agree_wrong": self.n_agree_wrong,
            "p_value": self.p_value, "method": self.method,
            "statistic": self.statistic, "alpha": self.alpha,
            "significant": self.significant, "winner": self.winner,
        }

    def fmt(self) -> str:
        """Rapor satırı — hangi yöntemin kullanıldığı GÖRÜNÜR olmalı."""
        stat = "—" if self.statistic is None else f"{self.statistic:.3f}"
        verdict = "ANLAMLI" if self.significant else "anlamsız"
        return (f"b={self.b} c={self.c} (uyumsuz={self.n_discordant}) "
                f"χ²={stat} p={self.p_value:.4g} yöntem={self.method} → {verdict}")


def mcnemar(b: int, c: int, *, n_agree_correct: int = 0, n_agree_wrong: int = 0,
            alpha: float = 0.05, exact_threshold: int = EXACT_THRESHOLD
            ) -> McNemarResult:
    """McNemar testi — UYUMSUZ çiftlere (b, c) odaklı.

    Yöntem seçimi otomatiktir ve sonuçta AÇIKÇA döndürülür:
      * `b + c < exact_threshold` (varsayılan 25) → **tam binom testi**
      * aksi halde → **süreklilik düzeltmeli χ² yaklaşımı**
        `χ² = (|b − c| − 1)² / (b + c)`, 1 serbestlik derecesi.

    Neden eşik: χ², kesikli binom dağılımına yapılan sürekli bir yaklaşımdır
    ve `b + c` küçükken hatası göreli olarak büyür (ör. b=8, c=0: tam test
    0,0078 verirken χ² 0,0133 verir — %70 göreli hata). Hatanın YÖNÜ tek
    düze değildir, o yüzden "yaklaşım hep lehimize çalışır" gibi bir şey
    iddia edilmez; iddia edilen, küçük örneklemde p-değerinin güvenilmez
    olduğudur. Ayrıntı: `EXACT_THRESHOLD` yorumu.

    Args:
        b: A doğru & B yanlış çift sayısı.
        c: A yanlış & B doğru çift sayısı.
        n_agree_correct, n_agree_wrong: uyumlu çiftler (yalnız rapor için).
        alpha: anlamlılık düzeyi.
        exact_threshold: tam test / yaklaşım sınırı.

    Returns:
        `McNemarResult`. `b == c == 0` ise p = 1,0 (fark yok, yöntem tam binom).

    Doğrulama (Wikipedia "McNemar's test" klasik örneği):
        b=121, c=59 → χ² = (|121−59|−1)²/180 = 3721/180 ≈ 20,672, p ≈ 5,4e-6.
    """
    if b < 0 or c < 0:
        raise ValueError(f"b ve c negatif olamaz: b={b}, c={c}")

    n = b + c
    if n < exact_threshold:
        return McNemarResult(b, c, binom_two_sided_p(b, c), "exact_binomial",
                             n_agree_correct, n_agree_wrong, None, alpha)

    stat = (abs(b - c) - 1) ** 2 / n
    return McNemarResult(b, c, chi2_sf_1df(stat), "chi2_continuity",
                         n_agree_correct, n_agree_wrong, stat, alpha)


def mcnemar_from_pairs(a_correct: Sequence[bool], b_correct: Sequence[bool],
                       *, alpha: float = 0.05,
                       exact_threshold: int = EXACT_THRESHOLD) -> McNemarResult:
    """Eşleşmiş doğru/yanlış dizilerinden McNemar.

    İki dizi AYNI sırada AYNI birimleri (ör. `(belge, alan)` kararları)
    anlatmalıdır — eşleştirme testin tüm gücüdür. Uzunluklar farklıysa hata
    yükseltilir; sessizce kısaltmak eşleştirmeyi bozar ve sonucu anlamsız
    kılar.
    """
    if len(a_correct) != len(b_correct):
        raise ValueError(
            f"eşleşmiş diziler aynı uzunlukta olmalı: {len(a_correct)} != "
            f"{len(b_correct)}")

    b = c = agree_ok = agree_bad = 0
    for x, y in zip(a_correct, b_correct):
        if x and y:
            agree_ok += 1
        elif x and not y:
            b += 1
        elif y and not x:
            c += 1
        else:
            agree_bad += 1
    return mcnemar(b, c, n_agree_correct=agree_ok, n_agree_wrong=agree_bad,
                   alpha=alpha, exact_threshold=exact_threshold)
