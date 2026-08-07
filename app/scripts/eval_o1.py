"""Ö1 terim deneyi — temel / sadeleştirme / sözlük kartı üç kolu.

İlgili: ../docs/rapor/o1-terim-deneyi.md (rapor),
        ../src/domain/terminology.py (`simplify_text`, `cards_for`),
        ../src/extraction/llm/orchestrator.py (üç kolun anahtarları),
        ../eval/run_eval.py (puanlama çekirdeği), ../eval/stats.py (bootstrap)

Kullanım:
    LLM_BACKEND=ollama LLM_STRICT=1 OLLAMA_NUM_CTX=8192 \
      .venv/bin/python -m scripts.eval_o1 --gold data/gold/gold.v2.json

## Neden ayrı bir betik, neden `eval/ablation.py` değil

Ö1'in üç kolu `eval/predictors.py`'ye henüz KAYITLI DEĞİL (o dosyanın sahibi
başka bir iş kolu). Kayıt satırları raporda yazılıdır. Bu betik kendi
`Predictor` nesnelerini kurar ama puanlamayı `eval/run_eval.py`'nin
çekirdeğinden alır — iki harness'ın ayrışması bu projede daha önce ölçülmüş bir
kusurdur (bkz. `eval/predictors.py` modül başlığı, Kusur 2) ve tekrarlanmaz.

## Deneyin tezi

İki mentör kaynağı çelişiyor: D2 terimin sadeleştirilmesini, Cavide Hanım'ın
maili ise terime DOKUNULMAYIP analizin modele verilmesini istiyor. Çelişki
otoriteyle değil ölçümle kapanır. Betik bu yüzden iki şey birden üretir:

  1. üç kolun mikro/makro-F1 + %95 bootstrap GA + üç ayrı paydalı hata sınıfı,
  2. sadeleştirmenin anlamı bozup bozmadığının DETERMİNİSTİK sayımı — LLM'e
     hiç gerek yok, sözlüğün kendi `degildir` verisi kanıt.

(2) tek başına da bir sonuçtur: LLM koşusu hiç yapılmasa bile sadeleştirmenin
kaç yerde sözlüğün "bu o DEĞİLDİR" dediği kavramı ürettiği sayılabilir.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from eval.matchers import get_matcher
from eval.predictors import Predictor
from eval.run_eval import (
    DocScore,
    aggregate,
    macro_f1,
    macro_f1_of,
    micro,
    micro_f1_of,
    score_all,
)
from eval.stats import DEFAULT_SEED, bootstrap_ci
from scripts.gold_schema import GoldRecord, load_gold
from src.domain.terminology import simplify_text
from src.extraction.llm.agents import KART_BUTCESI, KART_LIMITI, kart_metni
from src.extraction.llm.extractor import default_extractor
from src.extraction.llm.orchestrator import LLMOrchestrator
from src.extraction.reconcile import reconcile

#: Üç kol -> (terim_karti, sadelestirme). Tek yer, tek doğruluk kaynağı.
#:
#: İkisi aynı anda AÇILMAZ: o zaman ölçüm iki değişkenli olur ve hangi
#: müdahalenin etkidiği söylenemez.
KOLLAR: dict[str, tuple[bool, bool]] = {
    "temel": (False, False),
    "sadelestirme": (False, True),
    "sozluk-karti": (True, False),
}

KOL_ACIKLAMA: dict[str, str] = {
    "temel": "terim müdahalesi yok (kart kapalı, sadeleştirme kapalı)",
    "sadelestirme": ("belge metnindeki terim sözlüğün resmi_tr/halk_dili "
                     "karşılığıyla DEĞİŞTİRİLİR (mentör D2)"),
    "sozluk-karti": ("terim değiştirilmez; kanonik -> degildir -> ayrim_notu "
                     "-> risk_notu kartı prompt'a enjekte edilir (Cavide)"),
}

#: `|Δ| < 0,05` ise kazanan ilan edilmez. n=48'de bu büyüklükteki bir fark
#: gürültüden ayırt edilemez; referans kolun GA genişliği zaten ~0,11.
ANLAMLI_FARK_ESIGI = 0.05

#: Kural kolunun aynı set üzerindeki ölçülmüş referansı (`docs/rapor/olcumler.md`
#: ve `data/eval/reports/`). Rapora bağlam olsun diye taşınır, yeniden
#: hesaplanmaz — bu betik kural kolunu koşmaz.
REFERANS_KURAL = {"mikro_f1": 0.387, "ga": [0.329, 0.442],
                  "halusinasyon": 0.101, "kacirma": 21}


# --------------------------------------------------------------------------- #
# Deterministik ön analiz — LLM'siz de anlamlı
# --------------------------------------------------------------------------- #
@dataclass
class MetinAnalizi:
    """Bir belgenin terim müdahalesi künyesi (LLM çağrısı YOK)."""

    doc_id: str
    uzunluk: int
    kart_sayisi: int
    kart_karakteri: int
    kart_butce_asimi: bool
    sadelestirme: dict[str, int]

    def as_dict(self) -> dict[str, Any]:
        return {"doc_id": self.doc_id, "uzunluk": self.uzunluk,
                "kart_sayisi": self.kart_sayisi,
                "kart_karakteri": self.kart_karakteri,
                "kart_butce_asimi": self.kart_butce_asimi,
                "sadelestirme": self.sadelestirme}


def metni_coz(record: GoldRecord) -> tuple[MetinAnalizi, list[dict]]:
    """Tek belgenin kart bütçesi + sadeleştirme künyesi ve bozucu örnekleri.

    Bozucu örneklerde bağlam ÖZGÜN metinden alınır (katlanmış hâlinden değil):
    rapora konacak alıntının belgede birebir aranabilir olması gerekir.
    """
    kartlar = kart_metni(record.text)
    sonuc = simplify_text(record.text)

    ornekler: list[dict] = []
    for r in sonuc.bozucu:
        bas = max(0, r.start - 70)
        ornekler.append({
            "doc_id": record.id,
            "term_id": r.term_id,
            "kaynak": r.kaynak,
            "hedef": r.hedef,
            "alan": r.alan,
            "degildir_cokmesi": r.degildir_cokmesi,
            "tekrar_cokmesi": r.tekrar_cokmesi,
            "karsitlik_baglami": r.karsitlik_baglami,
            "ozgun": record.text[bas:r.end + 70].replace("\n", " ").strip(),
            "sadelesmis": (record.text[bas:r.start] + r.hedef
                           + record.text[r.end:r.end + 70]
                           ).replace("\n", " ").strip(),
        })

    analiz = MetinAnalizi(
        doc_id=record.id,
        uzunluk=len(record.text),
        kart_sayisi=sum(1 for s in kartlar.splitlines() if s.startswith("- ")),
        kart_karakteri=len(kartlar),
        kart_butce_asimi=len(kartlar) > KART_BUTCESI,
        sadelestirme=sonuc.as_dict())
    return analiz, ornekler


# --------------------------------------------------------------------------- #
# Kollar
# --------------------------------------------------------------------------- #
def kol_kur(ad: str, client: Optional[object]) -> Predictor:
    """Kol adından `Predictor`. `reconcile()` hattı DEĞİŞMEDEN kullanılır."""
    terim_karti, sadelestirme = KOLLAR[ad]
    orc = LLMOrchestrator(client, terim_karti=terim_karti,
                          sadelestirme=sadelestirme)
    return Predictor(ad, KOL_ACIKLAMA[ad],
                     fn=lambda t: list(reconcile(t, llm=orc)), llm=orc)


@dataclass
class KolSonucu:
    """Tek kolun ölçüm çıktısı."""

    ad: str
    docs: list[DocScore]
    saniye: float
    llm_ozet: dict[str, Any]

    @property
    def tablo(self) -> dict:
        return aggregate(self.docs)

    def as_dict(self, *, seed: int, resamples: int) -> dict[str, Any]:
        t = self.tablo
        m = micro(t)
        ci_mikro = bootstrap_ci(self.docs, micro_f1_of,
                                n_resamples=resamples, seed=seed)
        ci_makro = bootstrap_ci(self.docs, macro_f1_of,
                                n_resamples=resamples, seed=seed)
        zor = aggregate([d for d in self.docs if d.is_hard])
        return {
            "kol": self.ad,
            "aciklama": KOL_ACIKLAMA[self.ad],
            "belge": len(self.docs),
            "saniye": round(self.saniye, 1),
            "mikro_f1": m.f1(),
            "makro_f1": macro_f1(t),
            "mikro_f1_ga": ci_mikro.as_dict(),
            "makro_f1_ga": ci_makro.as_dict(),
            "zor_mikro_f1": micro(zor).f1() if zor else None,
            # Üç hata sınıfı — PAYDALARI AYRI. Aynı paydaya bölmek onları
            # karşılaştırılamaz kılar (bkz. eval/run_eval.py::Counts).
            "kacirma": m.kacirma,
            "yanlis_cikarim": m.yanlis_cikarim,
            "halusinasyon": m.fp_hallucinated,
            "support": m.support,
            "absent_decisions": m.absent_decisions,
            "extraction_failure_rate": m.extraction_failure_rate(),
            "hallucination_rate": m.hallucination_rate(),
            "tp": m.tp, "fp": m.fp, "fn": m.fn, "tn": m.tn,
            "llm": self.llm_ozet,
        }


def kolu_kostur(ad: str, records: list[GoldRecord], client: Optional[object],
                matcher_adi: str) -> KolSonucu:
    predictor = kol_kur(ad, client)
    matcher = get_matcher(matcher_adi)
    bas = time.monotonic()
    docs = score_all(records, predictor, matcher)
    sure = time.monotonic() - bas
    return KolSonucu(ad, docs, sure, predictor.llm_summary or {})


# --------------------------------------------------------------------------- #
# Rapor
# --------------------------------------------------------------------------- #
def fark_yorumu(a: str, b: str, fa: float, fb: float) -> str:
    """|Δ| < eşik ise kazanan İLAN EDİLMEZ — n=48'de fark gürültüdür."""
    d = fa - fb
    if abs(d) < ANLAMLI_FARK_ESIGI:
        return (f"{a} − {b} = {d:+.3f} → |Δ| < {ANLAMLI_FARK_ESIGI} "
                f"(n=48'de gürültüden ayırt edilemez, kazanan yok)")
    return (f"{a} − {b} = {d:+.3f} → eşiği aşıyor, ama GA örtüşmesine bak "
            f"(eşleşmiş fark GA'sı olmadan kanıt sayılmaz)")


def konsol_tablo(sonuclar: list[dict]) -> str:
    satirlar = ["=== Ö1 TERİM DENEYİ ===",
                f"{'kol':<16}{'mikro-F1':>10}{'makro-F1':>10}{'kaçırma':>9}"
                f"{'yanlış':>8}{'halüs.':>8}{'halüs. oranı':>14}  mikro-F1 %95 GA"]
    for s in sonuclar:
        hr = s["hallucination_rate"]
        hr_s = "ölçülemedi" if hr is None else f"{hr:.3f}"
        ga = s["mikro_f1_ga"]
        satirlar.append(
            f"{s['kol']:<16}{s['mikro_f1']:>10.3f}{s['makro_f1']:>10.3f}"
            f"{s['kacirma']:>9}{s['yanlis_cikarim']:>8}{s['halusinasyon']:>8}"
            f"{hr_s:>14}  "
            f"{ga['point']:.3f} [{ga['low']:.3f}–{ga['high']:.3f}]")
    satirlar.append(
        f"{'kural (ref.)':<16}{REFERANS_KURAL['mikro_f1']:>10.3f}{'—':>10}"
        f"{REFERANS_KURAL['kacirma']:>9}{'—':>8}{'—':>8}"
        f"{REFERANS_KURAL['halusinasyon']:>14.3f}  "
        f"{REFERANS_KURAL['ga'][0]:.3f}–{REFERANS_KURAL['ga'][1]:.3f}")
    return "\n".join(satirlar)


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def build_arg_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        description="Ö1: temel / sadeleştirme / sözlük kartı kolları.")
    ap.add_argument("--gold", default="data/gold/gold.v2.json")
    ap.add_argument("--kollar", default=",".join(KOLLAR))
    ap.add_argument("--matcher", default="strict", choices=["strict", "tolerant"])
    ap.add_argument("--seed", type=int, default=DEFAULT_SEED)
    ap.add_argument("--resamples", type=int, default=2000)
    ap.add_argument("--out-dir", default="data/eval")
    ap.add_argument("--sadece-analiz", action="store_true",
                    help="LLM koşmadan yalnız deterministik metin analizini üret")
    ap.add_argument("--limit", type=int, default=0,
                    help="ilk N belge (0 = tümü); yalnız duman testi içindir")
    return ap


def main(argv: Optional[list[str]] = None) -> int:
    args = build_arg_parser().parse_args(argv)

    gold_path = Path(args.gold)
    if not gold_path.is_file():
        print(f"HATA: gold dosyası yok: {gold_path}", file=sys.stderr)
        return 2
    records = load_gold(gold_path)
    if args.limit:
        records = records[:args.limit]
    if not records:
        print("HATA: gold boş.", file=sys.stderr)
        return 2

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # -- 1) Deterministik metin analizi (LLM YOK) ------------------------- #
    analizler: list[MetinAnalizi] = []
    ornekler: list[dict] = []
    for r in records:
        a, o = metni_coz(r)
        analizler.append(a)
        ornekler.extend(o)

    toplam_degisim = sum(a.sadelestirme["degisim"] for a in analizler)
    toplam_bozucu = sum(a.sadelestirme["anlam_bozucu"] for a in analizler)
    butce_asan = [a.doc_id for a in analizler if a.kart_butce_asimi]

    analiz_ozet = {
        "belge": len(records),
        "kart_butcesi": KART_BUTCESI,
        "kart_limiti": KART_LIMITI,
        "kart_butce_asan_belge": butce_asan,
        "kart_karakteri_max": max(a.kart_karakteri for a in analizler),
        "kart_karakteri_ortalama": round(
            sum(a.kart_karakteri for a in analizler) / len(analizler), 1),
        "kart_sayisi_max": max(a.kart_sayisi for a in analizler),
        "kart_ureten_belge": sum(1 for a in analizler if a.kart_sayisi),
        "sadelestirme_degisim": toplam_degisim,
        "sadelestirme_anlam_bozucu": toplam_bozucu,
        "sadelestirme_degildir_cokmesi": sum(
            a.sadelestirme["degildir_cokmesi"] for a in analizler),
        "sadelestirme_tekrar_cokmesi": sum(
            a.sadelestirme["tekrar_cokmesi"] for a in analizler),
        "sadelestirme_karsitlik_baglami": sum(
            a.sadelestirme["karsitlik_baglami"] for a in analizler),
        "sadelestirme_resmi_tr": sum(
            a.sadelestirme["resmi_tr"] for a in analizler),
        "sadelestirme_halk_dili": sum(
            a.sadelestirme["halk_dili"] for a in analizler),
        "degisim_gormeyen_belge": sum(
            1 for a in analizler if not a.sadelestirme["degisim"]),
        "belgeler": [a.as_dict() for a in analizler],
    }
    (out_dir / "o1-metin-analizi.json").write_text(
        json.dumps(analiz_ozet, ensure_ascii=False, indent=1), encoding="utf-8")
    (out_dir / "o1-sadelestirme-ornekleri.json").write_text(
        json.dumps(ornekler, ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"gold: {gold_path} ({len(records)} belge)")
    print(f"kart bütçesi {KART_BUTCESI} krk / {KART_LIMITI} kart — "
          f"aşan belge: {len(butce_asan)}; "
          f"en büyük kart metni {analiz_ozet['kart_karakteri_max']} krk")
    print(f"sadeleştirme: {toplam_degisim} değişiklik, "
          f"{toplam_bozucu} anlam bozucu "
          f"({analiz_ozet['sadelestirme_degildir_cokmesi']} degildir çökmesi, "
          f"{analiz_ozet['sadelestirme_tekrar_cokmesi']} tekrar çökmesi)")

    if args.sadece_analiz:
        return 0

    # -- 2) Üç kol ------------------------------------------------------- #
    taban = default_extractor()
    if not taban.available:
        print("HATA: LLM backend kapalı. Bu deney LLM olmadan ÖLÇÜLEMEZ; "
              "sahte satır üretmemek için çıkılıyor. "
              "LLM_BACKEND=ollama LLM_STRICT=1 ile koşun.", file=sys.stderr)
        return 2

    kol_adlari = [k.strip() for k in args.kollar.split(",") if k.strip()]
    bilinmeyen = [k for k in kol_adlari if k not in KOLLAR]
    if bilinmeyen:
        print(f"HATA: bilinmeyen kol(lar) {bilinmeyen}. "
              f"Seçenekler: {', '.join(KOLLAR)}", file=sys.stderr)
        return 2

    sonuclar: list[dict] = []
    for ad in kol_adlari:
        print(f"\n-> kol '{ad}' koşuyor ({len(records)} belge)…", flush=True)
        kol = kolu_kostur(ad, records, taban.client, args.matcher)
        d = kol.as_dict(seed=args.seed, resamples=args.resamples)
        sonuclar.append(d)
        print(f"   bitti: {d['saniye']} sn, mikro-F1 {d['mikro_f1']:.3f}",
              flush=True)

    print("\n" + konsol_tablo(sonuclar))

    print("\n=== FARKLAR (|Δ| < %.2f ise kazanan yok) ===" % ANLAMLI_FARK_ESIGI)
    yorumlar = []
    for i, a in enumerate(sonuclar):
        for b in sonuclar[i + 1:]:
            y = fark_yorumu(a["kol"], b["kol"], a["mikro_f1"], b["mikro_f1"])
            yorumlar.append(y)
            print("  " + y)

    cikti = {
        "kind": "o1-terim-deneyi",
        "gold": str(gold_path),
        "belge": len(records),
        "matcher": args.matcher,
        "seed": args.seed,
        "bootstrap_resamples": args.resamples,
        "bootstrap_birim": "document",
        "anlamli_fark_esigi": ANLAMLI_FARK_ESIGI,
        "referans_kural": REFERANS_KURAL,
        "metin_analizi": {k: v for k, v in analiz_ozet.items()
                          if k != "belgeler"},
        "kollar": sonuclar,
        "farklar": yorumlar,
    }
    (out_dir / "o1-sonuc.json").write_text(
        json.dumps(cikti, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\nyazıldı: {out_dir / 'o1-sonuc.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
