"""Gecikme ve kaynak ölçüm betiği — üç çıkarım yolu AYRI AYRI ölçülür.

İlgili: docs/OFFLINE-KANIT.md, docs/kaynak-tuketimi.md
        ../decisions/onlemli-kural-once-mimari (CLAUDE.md §3)

## Neden bu betik var

CLAUDE.md §3 "önce kural, sonra LLM" mimarisini bir *karar* olarak ilan ediyor
ama bugüne kadar bu kararı destekleyen **tek bir ölçüm** yoktu. Kural yolunun
milisaniyelerde bittiğini sayıyla göstermek, kararın gerekçesidir: LLM'i yalnızca
kuralların kaçırdığı alanlar için çağırmak, uçtan uca gecikmeyi iki-üç mertebe
düşürüyor.

## Ölçülen üç yol

| Yol | Ne koşar | Ne KOŞMAZ |
|---|---|---|
| (a) `rule` | `extract_all(text)` — saf regex/kural katmanı | sınıflandırma, uzlaştırma, LLM |
| (b) `hybrid` | `build_campaign(...)` — kural + sınıflandırıcı + uzlaştırma + normalizasyon | GERÇEK LLM çıkarımı (aşağıya bakınız) |
| (c) `chatbot` | `Chatbot.ask(q)` — router + yapısal sorgu / RAG | GERÇEK LLM üretimi (aşağıya bakınız) |

## DÜRÜSTLÜK NOTU (okumadan tabloyu kullanma)

`LLM_BACKEND` boşken `default_extractor()` **NullLLMExtractor** döner
(`src/extraction/llm/extractor.py`). Yani (b) ve (c) yollarında ölçülen süre
**boru hattının LLM DIŞI kısmıdır**. Bu bilinçli bir ölçümdür: teslim edilen
offline demo tam olarak bu konfigürasyonda koşar (CLAUDE.md §11 — önceden
doldurulmuş DB). Ama "hibrit gecikmesi" diye 8B model çıkarımını içeren bir sayı
sanılmamalı. Gerçek LLM kolu ölçülmek istenirse:

    LLM_BACKEND=vllm VLLM_URL=http://localhost:8001 python -m scripts.latency_bench

ve betik başlıkta hangi arka ucun aktif olduğunu basar.

## Korpus seçimi — `--recursive`

`data/raw/<slug>/` kökünde yalnızca 3 sentetik örnek var; gerçek scrape çıktısı
`live/` ve `manual/` alt klasörlerinde (1600+ belge). Varsayılan koşu sentetik
örneklerle hızlıdır; **jüriye gösterilecek sayı `--recursive` ile üretilendir**,
çünkü gerçek banka HTML'i sentetik örnekten mertebe olarak büyüktür ve gecikme
metin uzunluğuna doğrusal bağlıdır. İki korpus karıştırılmamalı.

Kullanım:
    python -m scripts.latency_bench                       # sentetik, 20 tur
    python -m scripts.latency_bench --recursive --iterations 3
    python -m scripts.latency_bench --recursive --json out/latency.json
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import resource
import statistics
import sys
import time
from dataclasses import asdict, dataclass, field as dc_field
from pathlib import Path
from typing import Callable, Optional

# Betik `python scripts/latency_bench.py` olarak da çağrılabilsin diye repo
# kökünü sys.path'e ekliyoruz (modül olarak çağrıldığında zararsız).
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.chatbot.bot import Chatbot                          # noqa: E402
from src.comparison.contradiction import detect as detect_contradictions  # noqa: E402
from src.db.repository import Repository                     # noqa: E402
from src.extraction.llm.extractor import default_extractor   # noqa: E402
from src.extraction.ner.classifier import default_classifier  # noqa: E402
from src.extraction.reconcile import build_campaign          # noqa: E402
from src.extraction.rules.extract import extract_all         # noqa: E402
from src.pipeline import build_demo_repo                     # noqa: E402
from src.preprocessing.clean import normalize_text           # noqa: E402
from src.scraping.collector import collect_from_fixtures     # noqa: E402
from src.scraping.config import load_banks                   # noqa: E402

# Chatbot yolunda kullanılan sorular — router'ın HER İKİ kolunu da vurur
# (yapısal sorgu + RAG). Tek kolu ölçmek p99'u yanıltıcı yapar.
BENCH_QUESTIONS: list[str] = [
    "Hangi bankada en düşük kâr payı oranı var?",             # structured/lowest
    "En yüksek finansman tutarı hangi bankada?",              # structured/highest
    "36 ay ve üzeri vade veren konut finansmanları hangileri?",  # structured+filter
    "Tahsis ücreti olmayan kampanyaları listele",             # structured/list
    "Masrafsız kampanyaların koşulları neler?",               # structured/masraf
    "Taşıt finansmanı kampanyasına kimler başvurabilir?",     # rag
    "Kampanya hangi tarihe kadar geçerli?",                   # rag
    "Yeni müşteri olmanın avantajı nedir?",                   # rag
]

# p99'un anlamli olmasi icin gereken en az chatbot ornegi.
MIN_CHAT_SAMPLES = 500


@dataclass
class Stats:
    """Tek bir yolun gecikme istatistiği. Süreler milisaniye."""

    name: str
    label: str
    n: int
    p50_ms: float
    p95_ms: float
    p99_ms: float
    min_ms: float
    max_ms: float
    mean_ms: float
    stdev_ms: float
    note: str = ""


@dataclass
class BenchResult:
    environment: dict
    cold_start: dict
    corpus: dict
    paths: list[dict] = dc_field(default_factory=list)


def _percentile(sorted_vals: list[float], q: float) -> float:
    """En yakın-sıra (nearest-rank) yüzdelik.

    `statistics.quantiles` interpolasyon yapar; küçük n'de (n<100) p99 için
    var olmayan bir değer üretir. Gecikme raporlamasında gözlenen bir ölçümü
    göstermek daha dürüst: p99 = gerçekten görülen bir süre.
    """
    if not sorted_vals:
        return float("nan")
    if len(sorted_vals) == 1:
        return sorted_vals[0]
    rank = max(1, min(len(sorted_vals), int(-(-q * len(sorted_vals) // 1))))
    return sorted_vals[rank - 1]


def _summarize(name: str, label: str, samples_ns: list[int], note: str = "") -> Stats:
    ms = sorted(s / 1_000_000 for s in samples_ns)
    return Stats(
        name=name,
        label=label,
        n=len(ms),
        p50_ms=round(_percentile(ms, 0.50), 4),
        p95_ms=round(_percentile(ms, 0.95), 4),
        p99_ms=round(_percentile(ms, 0.99), 4),
        min_ms=round(ms[0], 4),
        max_ms=round(ms[-1], 4),
        mean_ms=round(statistics.fmean(ms), 4),
        stdev_ms=round(statistics.stdev(ms), 4) if len(ms) > 1 else 0.0,
        note=note,
    )


def _time_calls(fn: Callable[[int], None], count: int) -> list[int]:
    """`fn`'i `count` kez çağırır, her çağrının süresini ns olarak döner."""
    out: list[int] = []
    for i in range(count):
        t0 = time.perf_counter_ns()
        fn(i)
        out.append(time.perf_counter_ns() - t0)
    return out


def _load_docs(banks_yaml: str, raw_dir: str,
               recursive: bool = False) -> list[tuple[str, str, str]]:
    """Fixture belgelerini (bank_slug, source_url, normalize_text) olarak döner."""
    docs: list[tuple[str, str, str]] = []
    for bank in load_banks(banks_yaml):
        for doc in collect_from_fixtures(bank, raw_dir, recursive=recursive):
            text = normalize_text(doc.clean_text)
            if text:
                docs.append((bank.slug, doc.source_url, text))
    return docs


def _peak_rss_mb() -> float:
    """Sürecin tepe RSS'i (MB).

    macOS `ru_maxrss`'i BYTE, Linux KILOBYTE olarak verir — bu fark sessizce
    1024x hatalı tablo üretir, o yüzden platforma göre ayırıyoruz.
    """
    raw = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    divisor = 1024 * 1024 if sys.platform == "darwin" else 1024
    return round(raw / divisor, 1)


def run_bench(banks_yaml: str, raw_dir: str, iterations: int,
              recursive: bool = False) -> BenchResult:
    backend = os.environ.get("LLM_BACKEND", "").strip() or "(bos -> NullLLMExtractor)"
    llm = default_extractor()
    clf = default_classifier()

    print(f"LLM_BACKEND         : {backend}")
    print(f"LLM cikarici        : {type(llm).__name__}")
    print(f"Siniflandirici      : {type(clf).__name__}")
    print(f"Python / platform   : {platform.python_version()} / {platform.platform()}")
    print(f"CPU sayisi          : {os.cpu_count()}")
    print(f"Korpus modu         : {'recursive (live/ + manual/)' if recursive else 'sentetik (kok)'}")
    print()

    # --- korpus ---------------------------------------------------------- #
    docs = _load_docs(banks_yaml, raw_dir, recursive=recursive)
    if not docs:
        raise SystemExit(
            f"HATA: {raw_dir} altinda fixture belgesi bulunamadi — olcum yapilamaz."
        )
    total_chars = sum(len(t) for _, _, t in docs)
    print(f"Korpus              : {len(docs)} belge, {total_chars} karakter "
          f"(ortalama {total_chars // len(docs)})")

    # --- soguk baslatma 1: demo API'nin gercek acilis yolu ---------------- #
    # `src/api/main.py` demo modunda tam olarak bunu cagirir (CLAUDE.md §11).
    # build_demo_repo `recursive` desteklemez; her zaman kok korpusu okur.
    t0 = time.perf_counter_ns()
    repo = build_demo_repo(banks_yaml, raw_dir)
    demo_cold_ms = (time.perf_counter_ns() - t0) / 1_000_000
    print(f"Demo soguk baslatma : {demo_cold_ms:.1f} ms (build_demo_repo, kok korpus)")

    # --- soguk baslatma 2: secili korpusun tam alimi (ingest) ------------- #
    # run_pipeline `recursive` gecirmedigi icin adimlarini burada tekrar
    # kuruyoruz: normalize -> siniflandir -> uzlastir -> celiski -> DB'ye yaz.
    # Amac belge/dakika verimini GERCEK korpusta olcmek.
    ingest_repo = Repository(":memory:")
    banks = {b.slug: b for b in load_banks(banks_yaml)}
    t0 = time.perf_counter_ns()
    for b in banks.values():
        ingest_repo.upsert_bank(b.name, b.slug, b.website_url, b.bddk_active)
    for slug, url, text in docs:
        ctype, _ = clf.classify(text)
        campaign = build_campaign(text, bank_slug=slug, source_url=url, llm=llm,
                                  campaign_type=ctype)
        list(detect_contradictions(campaign))
        ingest_repo.insert_campaign(campaign, clean_text=text)
    ingest_s = (time.perf_counter_ns() - t0) / 1_000_000_000
    docs_per_min = round(len(docs) / ingest_s * 60, 1) if ingest_s > 0 else float("nan")
    print(f"Tam korpus alimi    : {ingest_s:.2f} s -> {docs_per_min} belge/dakika")
    print()

    # Chatbot, DEMO deposu (3 satir) yerine TAM korpus deposu uzerinden olculur —
    # yapisal sorgu suresi satir sayisina bagli, 3 satirlik DB'de olculen p95
    # jüriyi yanıltır.
    bot = Chatbot(ingest_repo, llm=llm)

    # --- isinma (warm-up): regex derleme + import maliyetini dislar ------- #
    for _, _, text in docs[:3]:
        extract_all(text)
    bot.ask(BENCH_QUESTIONS[0])

    # --- (a) kural-only --------------------------------------------------- #
    rule_samples: list[int] = []
    for _ in range(iterations):
        rule_samples += _time_calls(lambda i: extract_all(docs[i][2]), len(docs))

    # --- (b) hibrit boru hatti -------------------------------------------- #
    def _hybrid(i: int) -> None:
        slug, url, text = docs[i]
        ctype, _ = clf.classify(text)
        build_campaign(text, bank_slug=slug, source_url=url, llm=llm,
                       campaign_type=ctype)

    hybrid_samples: list[int] = []
    for _ in range(iterations):
        hybrid_samples += _time_calls(_hybrid, len(docs))

    # --- (c) chatbot ------------------------------------------------------ #
    # Soru havuzu 8 elemanli; `iterations` kadar tur atmak n=24 gibi bir orneklem
    # verir ve p99 anlamsizlasir (tek olcum = p99). En az 500 ornek topluyoruz.
    chat_rounds = max(iterations, -(-MIN_CHAT_SAMPLES // len(BENCH_QUESTIONS)))
    chat_samples: list[int] = []
    for _ in range(chat_rounds):
        chat_samples += _time_calls(
            lambda i: bot.ask(BENCH_QUESTIONS[i % len(BENCH_QUESTIONS)]),
            len(BENCH_QUESTIONS),
        )

    llm_note = ("GERCEK LLM cikarimi DAHIL DEGIL (NullLLMExtractor aktif)"
                if type(llm).__name__ == "NullLLMExtractor" else
                f"LLM arka ucu aktif: {backend}")

    paths = [
        _summarize("rule", "(a) kural-only cikarim — extract_all()", rule_samples,
                   "saf regex/kural katmani; belge basina"),
        _summarize("hybrid", "(b) hibrit boru hatti — build_campaign()", hybrid_samples,
                   f"kural + siniflandirici + uzlastirma + normalizasyon. {llm_note}"),
        _summarize("chatbot", "(c) chatbot yaniti — Chatbot.ask()", chat_samples,
                   f"router + yapisal sorgu / RAG, {len(docs)} kampanyalik onceden "
                   f"doldurulmus DB, {len(BENCH_QUESTIONS)} soruluk havuz. {llm_note}"),
    ]

    result = BenchResult(
        environment={
            "python": platform.python_version(),
            "platform": platform.platform(),
            "machine": platform.machine(),
            "cpu_count": os.cpu_count(),
            "llm_backend": backend,
            "llm_extractor": type(llm).__name__,
            "classifier": type(clf).__name__,
            "in_container": Path("/.dockerenv").exists(),
        },
        cold_start={
            "demo_build_demo_repo_ms": round(demo_cold_ms, 1),
            "full_corpus_ingest_s": round(ingest_s, 2),
            "docs": len(docs),
            "docs_per_minute": docs_per_min,
        },
        corpus={
            "recursive": recursive,
            "documents": len(docs),
            "total_chars": total_chars,
            "avg_chars": total_chars // len(docs),
            "iterations": iterations,
        },
        paths=[asdict(p) for p in paths],
    )
    result.environment["peak_rss_mb"] = _peak_rss_mb()
    return result


def _print_table(res: BenchResult) -> None:
    print("=" * 78)
    print("GECIKME (ms) — her yol ayri")
    print("=" * 78)
    hdr = f"{'yol':<34}{'n':>6}{'p50':>9}{'p95':>9}{'p99':>9}{'max':>9}"
    print(hdr)
    print("-" * 78)
    for p in res.paths:
        print(f"{p['label'][:33]:<34}{p['n']:>6}{p['p50_ms']:>9.3f}"
              f"{p['p95_ms']:>9.3f}{p['p99_ms']:>9.3f}{p['max_ms']:>9.3f}")
    print("-" * 78)
    for p in res.paths:
        print(f"  * {p['name']}: {p['note']}")
    print()
    print(f"Korpus              : {res.corpus['documents']} belge, "
          f"ortalama {res.corpus['avg_chars']} karakter, "
          f"{res.corpus['iterations']} tur "
          f"(recursive={res.corpus['recursive']})")
    print(f"Demo soguk baslatma : {res.cold_start['demo_build_demo_repo_ms']} ms")
    print(f"Verim               : {res.cold_start['docs_per_minute']} belge/dakika "
          f"({res.cold_start['docs']} belge / {res.cold_start['full_corpus_ingest_s']} s)")
    print(f"Tepe RSS (bu surec) : {res.environment['peak_rss_mb']} MB")
    print(f"Konteyner icinde mi : {res.environment['in_container']}")
    print("=" * 78)


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Anatolia AI gecikme/kaynak olcumu (kural / hibrit / chatbot)")
    ap.add_argument("--banks", default="config/banks.yaml")
    ap.add_argument("--raw-dir", default="data/raw")
    ap.add_argument("--iterations", type=int, default=20,
                    help="korpus uzerinden kac tam tur (varsayilan 20)")
    ap.add_argument("--recursive", action="store_true",
                    help="data/raw/<slug>/live/ + manual/ altini da tara "
                         "(gercek scrape korpusu; jury tablosu bununla uretilir)")
    ap.add_argument("--json", dest="json_out", default=None,
                    help="sonucu JSON olarak bu dosyaya yaz")
    args = ap.parse_args()

    res = run_bench(args.banks, args.raw_dir, args.iterations,
                    recursive=args.recursive)
    _print_table(res)

    if args.json_out:
        out = Path(args.json_out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(asdict(res), indent=2, ensure_ascii=False),
                       encoding="utf-8")
        print(f"JSON yazildi        : {out}")


if __name__ == "__main__":
    main()
