"""Güven skoru KALİBRE Mİ? — ECE, güvenilirlik tablosu, eşik gerekçesi.

Kullanım:

    python -m eval.calibration --gold data/gold/gold.v2.json
    python -m eval.calibration --gold data/gold/gold.v2.json --json rapor.json

İlgili: ../src/extraction/rules/confidence.py (kural sezgisel skoru),
        ../src/extraction/llm/confidence.py (logprob skoru),
        ../src/comparison/compare.py (`ASGARI_GUVEN` — kullanıcıya görünen kapı),
        ./stats.py (bootstrap GA)

## Neden bu modül var

`rules/confidence.py` başlığı şunu yazıyordu:

    "Skorlar **kalibre edilmemiştir** — sadece sıralayıcıdır. Gerçek
     kalibrasyon `eval/calibration.py`'de gold set üzerinde sıcaklık
     ölçekleme ile yapılacak."

O dosya YOKTU. Yani iki docstring'de vaat edilen bir ölçüm hiç yapılmamıştı
ve bunun somut bir bedeli var: `comparison/compare.py:ASGARI_GUVEN = 0.65`
**kullanıcıya görünen bir kapıdır** — skoru bu eşiğin altında kalan satır
karşılaştırma tablosundan DÜŞÜRÜLÜR. Kalibre edilmemiş bir skora eşik koymak,
eşiğin ne kadar veri attığını ve attıklarının gerçekten kötü olup olmadığını
bilmemek demektir.

Bu modül o soruyu cevaplar. Sıcaklık ölçekleme UYGULAMAZ (skoru değiştirmek
üretim davranışını değiştirir ve ayrı bir karardır); mevcut skorun ne kadar
kalibre olduğunu ÖLÇER ve eşiği gerekçelendirir ya da çürütür.

## Ölçütler ve neden bunlar

- **ECE** (Expected Calibration Error): kovalara ayır, her kovada
  |doğruluk − ortalama güven| farkını kova ağırlığıyla topla. "0,8 diyorsa
  %80 haklı mı" sorusunun tek sayılık cevabı.
- **MCE**: kovaların en kötüsü. Ortalama iyi görünürken tek bir bandın
  felaket olması mümkündür; ECE bunu gizler, MCE gizlemez.
- **Brier**: `mean((güven − doğru)²)`. Kalibrasyon ve ayırt ediciliği
  birlikte cezalandırır.
- **Güvenilirlik tablosu**: kova başına sayı/güven/doğruluk. Tek sayı
  yönü söylemez — model AŞIRI mı yoksa YETERSİZ mi güveniyor, ancak
  tabloda görünür.
- **Eşik analizi**: `ASGARI_GUVEN`in üstünde ve altında doğruluk. Kapı
  ancak altta kalanların doğruluğu belirgin biçimde DÜŞÜKSE haklıdır.

Kalibrasyonun anlamlı olabilmesi için karar sayısı yeterli olmalı; gold 48
kayıt olduğu için sayılar dar ve rapor bunu açıkça yazar. `--asgari-karar`
altında ECE hesaplanmaz: az örnekle hesaplanan ECE, kalibre olmayan bir
modeli kalibre gösterebilir.

## Bağımlılık

Saf Python standart kütüphanesi. Bu, on-prem iddiasının parçası (bkz.
CI `test` işi hiçbir paket kurmaz).
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from dataclasses import field as dc_field
from pathlib import Path
from typing import Any, Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from eval.matchers import get_matcher
from eval.predictors import build_predictor
from eval.run_eval import _serbest_metin_alani
from eval.stats import bootstrap_ci
from src.comparison.compare import ASGARI_GUVEN

#: Güvenilirlik kovalarının sınırları. Eşit genişlikte 10 kova YERİNE
#: yukarıda yoğunlaşan sınırlar: kural katmanının skorları 0,70 tabanı
#: etrafında toplanıyor (`rules/confidence.py:BASE = 0.70`) ve eşit kovalar
#: alt yarıyı boş, üst yarıyı tek kovada bırakıyordu.
KOVALAR: tuple[float, ...] = (0.0, 0.5, 0.6, 0.65, 0.7, 0.75, 0.8, 0.9, 1.01)

#: Bu sayıdan az kararla ECE hesaplanmaz — az örnek kalibrasyonu güzelleştirir.
ASGARI_KARAR = 30


@dataclass
class Karar:
    """Tek bir (belge, alan) tahmini: güven + doğru muydu."""

    doc_id: str
    field: str
    guven: float
    dogru: bool
    kaynak: str


@dataclass
class KovaOzeti:
    alt: float
    ust: float
    sayi: int = 0
    guven_toplam: float = 0.0
    dogru_sayi: int = 0

    @property
    def ort_guven(self) -> float:
        return (self.guven_toplam / self.sayi) if self.sayi else 0.0

    @property
    def dogruluk(self) -> float:
        return (self.dogru_sayi / self.sayi) if self.sayi else 0.0

    @property
    def fark(self) -> float:
        """|doğruluk − ortalama güven| — kovanın kalibrasyon hatası."""
        return abs(self.dogruluk - self.ort_guven)


@dataclass
class Rapor:
    kararlar: list[Karar] = dc_field(default_factory=list)
    kovalar: list[KovaOzeti] = dc_field(default_factory=list)
    ece: Optional[float] = None
    mce: Optional[float] = None
    brier: Optional[float] = None
    ece_ga: Optional[tuple[float, float]] = None
    esik: float = ASGARI_GUVEN
    esik_ustu_sayi: int = 0
    esik_ustu_dogruluk: Optional[float] = None
    esik_alti_sayi: int = 0
    esik_alti_dogruluk: Optional[float] = None
    kaynak_dagilimi: dict[str, int] = dc_field(default_factory=dict)


def _kova_bul(guven: float) -> int:
    for i in range(len(KOVALAR) - 1):
        if KOVALAR[i] <= guven < KOVALAR[i + 1]:
            return i
    return len(KOVALAR) - 2


def kararlari_topla(kayitlar: list[dict], *, config: str = "kural",
                    matcher_adi: str = "strict") -> list[Karar]:
    """Gold üzerinde (güven, doğru mu) çiftlerini üretir.

    Yalnız çıkarıcının DEĞER ÜRETTİĞİ alanlar sayılır: kalibrasyon
    "ürettiğin şeye ne kadar güvenmelisin" sorusudur. Üretilmemiş alan bir
    güven skoru taşımaz, dolayısıyla kalibrasyona giremez.

    Gold'un o alan hakkında KARAR VERMEDİĞİ durumlar (`absent_fields`te de
    `fields`ta da yok) atlanır — `run_eval`daki `ATL` ile aynı ilke:
    bilmediğimizi lehimize saymıyoruz.
    """
    pred = build_predictor(config)
    matcher = get_matcher(matcher_adi)
    out: list[Karar] = []

    for kayit in kayitlar:
        metin = kayit.get("text") or ""
        gold = kayit.get("fields") or {}
        yok = set(kayit.get("absent_fields") or [])
        for f in pred.fields(metin):
            ad = f.field_name
            if f.canonical_value is None:
                continue
            if ad in gold:
                dogru = bool(matcher(ad, f.canonical_value, gold[ad]))
            elif ad in yok:
                dogru = False          # gold "YOK" dedi, değer ürettik
            else:
                continue               # gold karar vermemiş -> atla
            out.append(Karar(
                doc_id=str(kayit.get("id", "?")), field=ad,
                guven=float(f.confidence), dogru=dogru,
                kaynak=getattr(f, "confidence_source", None) or "bilinmiyor"))
    return out


def hesapla(kararlar: list[Karar], *, asgari: int = ASGARI_KARAR,
            resamples: int = 1000, seed: int = 42) -> Rapor:
    r = Rapor(kararlar=list(kararlar))
    r.kovalar = [KovaOzeti(KOVALAR[i], KOVALAR[i + 1])
                 for i in range(len(KOVALAR) - 1)]
    for k in kararlar:
        kv = r.kovalar[_kova_bul(k.guven)]
        kv.sayi += 1
        kv.guven_toplam += k.guven
        kv.dogru_sayi += int(k.dogru)
        r.kaynak_dagilimi[k.kaynak] = r.kaynak_dagilimi.get(k.kaynak, 0) + 1

    ust = [k for k in kararlar if k.guven >= r.esik]
    alt = [k for k in kararlar if k.guven < r.esik]
    r.esik_ustu_sayi, r.esik_alti_sayi = len(ust), len(alt)
    if ust:
        r.esik_ustu_dogruluk = sum(k.dogru for k in ust) / len(ust)
    if alt:
        r.esik_alti_dogruluk = sum(k.dogru for k in alt) / len(alt)

    n = len(kararlar)
    if n < asgari:
        return r      # ECE hesaplanmaz; sebebi raporda yazılı

    r.ece = sum(kv.sayi / n * kv.fark for kv in r.kovalar if kv.sayi)
    r.mce = max((kv.fark for kv in r.kovalar if kv.sayi), default=0.0)
    r.brier = sum((k.guven - int(k.dogru)) ** 2 for k in kararlar) / n

    # GA belge düzeyinde kümelenir: aynı belgeden çıkan alanlar bağımsız
    # değildir (bkz. stats.bootstrap_ci gerekçesi). Kümeleme birimi belge.
    belgeler: dict[str, list[Karar]] = {}
    for k in kararlar:
        belgeler.setdefault(k.doc_id, []).append(k)

    def _ece(kume: list[list[Karar]]) -> float:
        duz = [k for grup in kume for k in grup]
        if not duz:
            return 0.0
        kovalar = [KovaOzeti(KOVALAR[i], KOVALAR[i + 1])
                   for i in range(len(KOVALAR) - 1)]
        for k in duz:
            kv = kovalar[_kova_bul(k.guven)]
            kv.sayi += 1
            kv.guven_toplam += k.guven
            kv.dogru_sayi += int(k.dogru)
        return sum(kv.sayi / len(duz) * kv.fark for kv in kovalar if kv.sayi)

    try:
        r.ece_ga = bootstrap_ci(list(belgeler.values()), _ece,
                                resamples=resamples, seed=seed)
    except Exception:                                  # pragma: no cover
        r.ece_ga = None
    return r


def bicimle(r: Rapor, *, baslik: str = "") -> str:
    s: list[str] = []
    n = len(r.kararlar)
    s.append(f"=== GÜVEN KALİBRASYONU — {baslik} ===" if baslik
             else "=== GÜVEN KALİBRASYONU ===")
    s.append(f"karar sayısı : {n}  (yalnız çıkarıcının DEĞER ürettiği alanlar)")
    s.append("skor kaynağı : " + ", ".join(
        f"{k}={v}" for k, v in sorted(r.kaynak_dagilimi.items())) or "—")
    s.append("")

    if r.ece is None:
        s.append(f"ECE HESAPLANMADI: {n} karar < {ASGARI_KARAR} asgari.")
        s.append("Az örnekle hesaplanan ECE, kalibre OLMAYAN bir modeli")
        s.append("kalibre gösterebilir; sayı vermek yanıltıcı olurdu.")
    else:
        ga = (f"  [%95 GA {r.ece_ga[0]:.3f}–{r.ece_ga[1]:.3f}]"
              if r.ece_ga else "")
        s.append(f"ECE   : {r.ece:.3f}{ga}   (0 = mükemmel kalibre)")
        s.append(f"MCE   : {r.mce:.3f}   (kovaların EN KÖTÜSÜ)")
        s.append(f"Brier : {r.brier:.3f}")
    s.append("")

    s.append("--- Güvenilirlik tablosu ---")
    s.append(f"{'kova':>12} {'sayı':>5} {'ort.güven':>10} {'doğruluk':>9} "
             f"{'fark':>7}  yön")
    for kv in r.kovalar:
        if not kv.sayi:
            continue
        yon = ("AŞIRI güven" if kv.ort_guven > kv.dogruluk
               else "yetersiz güven" if kv.ort_guven < kv.dogruluk else "—")
        s.append(f"{kv.alt:.2f}-{kv.ust:<7.2f} {kv.sayi:>5} "
                 f"{kv.ort_guven:>10.3f} {kv.dogruluk:>9.3f} "
                 f"{kv.fark:>7.3f}  {yon}")
    s.append("")

    s.append(f"--- Eşik analizi (compare.ASGARI_GUVEN = {r.esik}) ---")
    ustd = ("—" if r.esik_ustu_dogruluk is None
            else f"{r.esik_ustu_dogruluk:.3f}")
    altd = ("—" if r.esik_alti_dogruluk is None
            else f"{r.esik_alti_dogruluk:.3f}")
    s.append(f"eşik ÜSTÜ : {r.esik_ustu_sayi:>4} karar, doğruluk {ustd}")
    s.append(f"eşik ALTI : {r.esik_alti_sayi:>4} karar, doğruluk {altd}")
    if r.esik_ustu_dogruluk is not None and r.esik_alti_dogruluk is not None:
        d = r.esik_ustu_dogruluk - r.esik_alti_dogruluk
        s.append(f"ayrım     : {d:+.3f}")
        if d <= 0:
            s.append("  ⚠ KAPI GEREKÇESİZ: eşiğin altındaki kararlar üstteki")
            s.append("    kadar (ya da daha) doğru. Kapı veri atıyor ama")
            s.append("    kaliteyi yükseltmiyor.")
        elif d < 0.10:
            s.append("  ⚠ ayrım ZAYIF (<0,10): eşik bugünkü hâliyle çok az")
            s.append("    şey kazandırıyor; değeri yeniden ölçülmeli.")
        else:
            s.append("  ✓ kapı ayırt edici: altta kalanlar belirgin biçimde")
            s.append("    daha yanlış.")
    s.append("")
    s.append("NOT: Bu modül sıcaklık ölçekleme UYGULAMAZ. Skoru değiştirmek")
    s.append("üretim davranışını değiştirir ve ayrı bir karardır; burada")
    s.append("yalnız mevcut skorun kalibrasyonu ÖLÇÜLÜR.")
    return "\n".join(s)


def as_dict(r: Rapor) -> dict[str, Any]:
    return {
        "karar_sayisi": len(r.kararlar),
        "ece": r.ece,
        "ece_ga": list(r.ece_ga) if r.ece_ga else None,
        "mce": r.mce,
        "brier": r.brier,
        "esik": r.esik,
        "esik_ustu": {"sayi": r.esik_ustu_sayi,
                      "dogruluk": r.esik_ustu_dogruluk},
        "esik_alti": {"sayi": r.esik_alti_sayi,
                      "dogruluk": r.esik_alti_dogruluk},
        "kaynak_dagilimi": r.kaynak_dagilimi,
        "kovalar": [
            {"alt": kv.alt, "ust": kv.ust, "sayi": kv.sayi,
             "ort_guven": kv.ort_guven, "dogruluk": kv.dogruluk,
             "fark": kv.fark}
            for kv in r.kovalar if kv.sayi],
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="python -m eval.calibration",
        description="Güven skoru kalibre mi? ECE + güvenilirlik + eşik analizi.")
    ap.add_argument("--gold", required=True, help="gold JSON dosyası")
    ap.add_argument("--config", default="kural",
                    help="tahmin konfigürasyonu (varsayılan: kural)")
    ap.add_argument("--matcher", default="strict", choices=["strict", "tolerant"])
    ap.add_argument("--asgari-karar", type=int, default=ASGARI_KARAR,
                    help=f"ECE için asgari karar sayısı (varsayılan {ASGARI_KARAR})")
    ap.add_argument("--resamples", type=int, default=1000)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--json", dest="json_yol", default=None,
                    help="raporu JSON olarak da yaz")
    a = ap.parse_args(argv)

    kayitlar = json.loads(Path(a.gold).read_text(encoding="utf-8"))
    kararlar = kararlari_topla(kayitlar, config=a.config,
                               matcher_adi=a.matcher)

    # İKİ KESİT BİRLİKTE — `run_eval`ın disiplininin aynısı.
    #
    # Ölçüldü (2026-08-12): TÜM kararlarda ECE 0,490 çıkıyor ve bu sayıyı
    # tek başına yayımlamak yanıltıcı olurdu. 0,90+ güven bandındaki 73
    # kararın **31'i `kampanya_kosullari`** ve o alanın **0'ı doğru** —
    # ama o alan serbest CÜMLE listesi ve span eşleşmesiyle F1 ölçmek
    # metodolojik olarak yanlış (`run_eval._serbest_metin_alani`). Yani
    # manşet ECE'yi, projenin ana metrikten ZATEN dışladığı alan şişiriyor.
    #
    # Alan gizlenmiyor: iki sayı yan yana basılıyor, aradaki fark okunuyor.
    yapisal = [k for k in kararlar if not _serbest_metin_alani(k.field)]

    r_tum = hesapla(kararlar, asgari=a.asgari_karar,
                    resamples=a.resamples, seed=a.seed)
    r_yap = hesapla(yapisal, asgari=a.asgari_karar,
                    resamples=a.resamples, seed=a.seed)

    print(bicimle(r_tum, baslik="TÜM ALANLAR (12)"))
    print()
    print(bicimle(r_yap, baslik="YAPILANDIRILMIŞ ALANLAR (serbest metin HARİÇ)"))
    print()
    print("İki kesit neden ayrı: 0,90+ bandındaki kararların büyük kısmı")
    print("serbest metin alanından geliyor ve o alan span eşleşmesiyle")
    print("ölçülemez. Alan GİZLENMİYOR — iki sayı yan yana duruyor.")

    if a.json_yol:
        Path(a.json_yol).write_text(
            json.dumps({"tum": as_dict(r_tum), "yapisal": as_dict(r_yap)},
                       ensure_ascii=False, indent=2),
            encoding="utf-8")
        print(f"\nJSON yazıldı: {a.json_yol}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
