"""Demo veri tabanını gerçek korpustan üretir — `data/demo.db`.

İlgili: CLAUDE.md §11 (demo stratejisi), ../decisions/demo-onceden-doldurulmus-db.md
        src/pipeline.py (mode="corpus"), src/db/repository.py

## Neden bu betik var

CLAUDE.md §11: *"Önceden scrape + önceden çıkarım yap, DB'yi doldur. Demo
doldurulmuş DB'den okur."* Bu karar uygulanmamıştı: demo yolu `mode="fixture"`
ile koşuyor ve `data/raw/<slug>/` **kök seviyesinden yalnız 3 belge** yüklüyordu.
Korpusta ise 849 `.txt` belge var (`live/`, `products/`, `manual/` altında).
Sonuç: `GET /contradictions` boş dönüyor, karşılaştırma paneli 10 bankanın
üçünü görüyordu.

Bu betik `mode="corpus"` ile tüm korpusu çıkarımdan geçirip **kalıcı bir SQLite
dosyası** üretir. API `DATABASE_PATH=data/demo.db` ile bu dosyayı okur.

## Kullanım

    python3 -m scripts.build_demo_db --out data/demo.db
    python3 -m scripts.build_demo_db --out data/demo.db --force
    python3 -m scripts.build_demo_db --out data/demo.db --json-report /tmp/r.json

Çıkış kodları: 0 başarılı · 1 hedef dosya var (`--force` yok) · 2 KORPUS BOŞ.

Kod 2 neden ayrı: belge bulunamadığında 0 döndürüp "kuruldu" demek, tam olarak
bu projede avlanan hata sınıfıdır (sessizce yanlış rapor). Boş DB ile dönmek
yerine gürültülü biçimde başarısız olur.

Saf stdlib + offline. LLM servisi yoksa çıkarım kural-only koşar (normal);
rapor hangi katmanın kaç alan ürettiğini yazar, böylece bu görünür kalır.

## KARAR (2026-07-31): `data/demo.db` git'e GİRMEZ — betik girer

Ölçülen sayılar:

    demo.db                9.46 MB  (VACUUM sonrası da 9.46 MB)
    gzip -9                0.97 MB  (git nesnesinin kabaca boyutu)
    deponun tüm pack'i     12.28 MB
    kurulum süresi         3.3 s
    kaynak `.txt` belgeler 849 — HEPSİ git'te izleniyor
    iki koşu bayt-bayt aynı (sha256 eşit) — çıktı deterministik

Gerekçe:

1. **Türetilmiş artefakt.** Girdinin tamamı (849 `.txt` + `config/banks.yaml`)
   zaten depoda ve üretim deterministik. Türevi kaynağının yanına koymak iki
   doğruluk kaynağı yaratır; biri güncellenip diğeri unutulduğunda jüri eski
   DB'yi görür ve bunu anlamanın yolu yoktur.
2. **Kalıcı maliyet.** SQLite ikilidir, delta sıkışmaz: her yeniden kurulum
   ~1 MB'lık YENİ bir nesne demektir ve git geçmişi değişmezdir. Depo pack'i
   şu an 12.28 MB; birkaç yeniden kurulum onu ikiye katlar. Kazanç 3.3 s.
3. **Mevcut karar.** `.gitignore` zaten `*.db` yok sayıyor; DB'yi eklemek bu
   kararı istisna ile delmek olurdu.

Jürinin "tek komutla dolu DB" beklentisi bu kararla ÇELİŞMEZ, ama bir adım
gerektirir (bu ajanın sahiplik alanı DIŞINDA, `docker-compose.yml` /
`Dockerfile.api` sahibine):

    # imaj derlenirken ya da entrypoint'te, ağ gerekmez:
    python3 -m scripts.build_demo_db --out data/demo.db --force --quiet
    # ve API'ye:  DATABASE_PATH=data/demo.db

`.dockerignore` `data/raw`'ı bilerek dışlamıyor, yani bu adım imaj içinde
offline çalışır.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Optional

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.db.repository import Repository
from src.pipeline import MODE_CORPUS, PipelineResult, run_pipeline

DEFAULT_OUT = "data/demo.db"
DEFAULT_CONFIG = "config/banks.yaml"
DEFAULT_RAW = "data/raw"

# İlerleme çıktısı: kaç belgede bir satır basılsın (tty değilse).
PROGRESS_EVERY = 50


class _Progress:
    """849 belgelik koşu için ilerleme göstergesi (stderr).

    tty ise tek satır `\\r` ile güncellenir; boru/CI ise her `PROGRESS_EVERY`
    belgede bir satır basılır (log dosyasını `\\r` ile doldurmamak için).
    """

    def __init__(self, stream: Any, enabled: bool = True) -> None:
        self.stream = stream
        self.enabled = enabled
        self.tty = bool(getattr(stream, "isatty", lambda: False)())
        self.started = time.perf_counter()

    def __call__(self, done: int, total: int, bank: str) -> None:
        if not self.enabled:
            return
        last = done >= total
        if not (self.tty or last or done % PROGRESS_EVERY == 0):
            return
        pct = (100.0 * done / total) if total else 100.0
        gecen = time.perf_counter() - self.started
        line = (f"  [{done:>4}/{total}] %{pct:5.1f}  {gecen:5.1f}s  "
                f"son banka: {bank}")
        if self.tty and not last:
            self.stream.write("\r" + line.ljust(72))
        else:
            self.stream.write(("\r" if self.tty else "") + line.ljust(72) + "\n")
        self.stream.flush()


def build(out_path: str | Path, config: str = DEFAULT_CONFIG,
          raw_dir: str = DEFAULT_RAW, force: bool = False,
          quiet: bool = False,
          stream: Any = None,
          database_url: Optional[str] = None) -> tuple[Optional[dict], int]:
    """DB'yi kurar ve (rapor, çıkış kodu) döndürür.

    `database_url` verilirse hedef **PostgreSQL**, verilmezse `out_path`
    yolundaki SQLite dosyası. İkisi de aynı `run_pipeline` + aynı depo
    sözleşmesini kullanır; fark yalnızca hedeftir.

    `force=True` SQLite'ta var olan dosyayı **siler** — üzerine yazmak değil.
    Aynı dosyaya ikinci kez INSERT etmek kampanyaları çiftlerdi (şema UNIQUE
    kısıtı taşımıyor), yani "yeniden kur" sessizce iki katına çıkarırdı.

    **Postgres'te `--force` TABLO SİLMEZ.** Bilinçli bir karar: yanlış bir
    `DATABASE_URL` ile koşulduğunda geri dönüşü olmayan hasar verecek bir
    komut bu betiğe konmadı. Hedef boş değilse betik durur ve ne yapılacağını
    söyler; temizleme işi operatörün açık kararıdır.
    """
    stream = stream if stream is not None else sys.stderr

    if database_url:
        return _build_postgres(database_url, config, raw_dir, force, quiet, stream)

    out = Path(out_path)

    if out.exists():
        if not force:
            print(f"HATA: {out} zaten var. Üzerine yazmadan önce onaylayın:\n"
                  f"      python3 -m scripts.build_demo_db --out {out} --force",
                  file=stream)
            return None, 1
        print(f"UYARI: mevcut {out} siliniyor (--force).", file=stream)
        out.unlink()
    out.parent.mkdir(parents=True, exist_ok=True)

    t0 = time.perf_counter()
    repo = Repository(str(out))
    try:
        print(f"Korpus okunuyor: {raw_dir}  (mod={MODE_CORPUS}, yalnız .txt)",
              file=stream)
        result = run_pipeline(repo, config, raw_dir=raw_dir, mode=MODE_CORPUS,
                              on_progress=_Progress(stream, enabled=not quiet))
        if result.documents_loaded == 0:
            print(f"HATA: {raw_dir} altında hiç .txt belge bulunamadı. "
                  f"Boş bir DB üretip 'kuruldu' demek sessiz bir yalan olurdu; "
                  f"--raw-dir yolunu kontrol edin.", file=stream)
            repo.close()
            out.unlink(missing_ok=True)
            return None, 2
        elapsed = time.perf_counter() - t0
        report = _report(repo, result, out, elapsed)
    finally:
        repo.close()
    return report, 0


def _build_postgres(database_url: str, config: str, raw_dir: str, force: bool,
                    quiet: bool, stream: Any) -> tuple[Optional[dict], int]:
    """Korpusu PostgreSQL'e yazar.

    Neden gerekli: `data/demo.db` bir SQLite DOSYASI; Postgres yolu onu
    okuyamaz. Bu betik olmadan `--profile postgres` altında API yalnızca
    3 fixture belgesi görüyordu ve "849 belge Postgres'te" iddiası
    gösterilemiyordu.
    """
    from src.db.factory import create_repository

    repo = create_repository(database_url=database_url)
    try:
        mevcut = repo.counts().get("campaigns", 0)
        if mevcut and not force:
            print(f"HATA: hedef veri tabanı boş değil ({mevcut} kampanya).\n"
                  f"      Aynı korpusu ikinci kez yazmak kayıtları çiftler "
                  f"(şemada UNIQUE kısıtı yok).\n"
                  f"      Bu betik tablo SİLMEZ — yanlış DATABASE_URL ile "
                  f"koşulduğunda geri dönüşü olmayan hasar verirdi.\n"
                  f"      Temizlemek operatörün açık kararı: veri tabanını "
                  f"düşürüp yeniden kurun, sonra bu betiği tekrar koşturun.",
                  file=stream)
            return None, 1
        if mevcut and force:
            print(f"HATA: --force Postgres hedefinde TABLO SİLMEZ "
                  f"({mevcut} kampanya mevcut). Yukarıdaki gerekçeye bakın.",
                  file=stream)
            return None, 1

        t0 = time.perf_counter()
        print(f"Korpus okunuyor: {raw_dir}  (mod={MODE_CORPUS}, yalnız .txt)\n"
              f"Hedef: PostgreSQL", file=stream)
        result = run_pipeline(repo, config, raw_dir=raw_dir, mode=MODE_CORPUS,
                             on_progress=_Progress(stream, enabled=not quiet))
        if result.documents_loaded == 0:
            print(f"HATA: {raw_dir} altında hiç .txt belge bulunamadı. "
                  f"Boş bir DB üretip 'kuruldu' demek sessiz bir yalan olurdu; "
                  f"--raw-dir yolunu kontrol edin.", file=stream)
            return None, 2
        return _report(repo, result, None, time.perf_counter() - t0), 0
    finally:
        repo.close()


def _report(repo: Any, result: PipelineResult, out: Optional[Path],
            elapsed: float) -> dict:
    """Özet raporu — ölçülen sayılar, tahmin yok."""
    counts = repo.counts()
    coverage = repo.field_coverage()
    per_bank = repo.campaigns_per_bank()
    # Ham SQL DEĞİL: sözleşme metodu. `repo.conn.execute(...)` yalnızca
    # SQLite'ta çalışırdı ve Postgres hedefinde bu rapor patlardı — API
    # katmanında düzeltilen hatanın aynısı.
    by_extractor = repo.fields_by_extractor()
    by_kind: dict[str, int] = {}
    for c in result.contradictions:
        by_kind[c["kind"]] = by_kind.get(c["kind"], 0) + 1
    return {
        # Postgres hedefinde dosya yok; "0 bayt" yazmak yanıltıcı olurdu.
        "db_path": str(out) if out is not None else "postgresql",
        "db_bytes": out.stat().st_size if out is not None else None,
        "elapsed_s": round(elapsed, 2),
        "mode": result.mode,
        "documents_loaded": result.documents_loaded,
        "docs_per_bank": result.docs_per_bank,
        "campaigns_per_bank": per_bank,
        "counts": counts,
        "field_coverage": coverage,
        "fields_by_extractor": by_extractor,
        "contradiction_count": len(result.contradictions),
        "contradictions_by_kind": by_kind,
    }


def format_report(rep: dict) -> str:
    """İnsan-okur özet (Türkçe, hizalı)."""
    c = rep["counts"]
    camp = c["campaigns"] or 1
    satirlar = [
        "",
        "=" * 66,
        "DEMO VERİ TABANI ÖZETİ",
        "=" * 66,
        # Postgres hedefinde dosya yok; "0.00 MB" yazmak yanıltıcı olurdu.
        (f"  hedef            : {rep['db_path']}"
         + (f"  ({rep['db_bytes'] / 1_048_576:.2f} MB)"
            if rep.get("db_bytes") is not None else "  (sunucu — dosya yok)")),
        f"  kurulum süresi   : {rep['elapsed_s']} s   (mod={rep['mode']})",
        f"  belge → kampanya : {rep['documents_loaded']} → {c['campaigns']}",
        (f"  banka            : {c['banks_with_campaigns']}/{c['banks']} "
         f"(kampanyası olan / toplam)"),
        (f"  alan (satır)     : {c['fields']}  —  "
         f"{c['campaigns_with_fields']} kampanyada en az bir alan "
         f"(%{100.0 * c['campaigns_with_fields'] / camp:.1f})"),
        f"  çelişki          : {rep['contradiction_count']}",
        "",
        "  BANKA BAŞINA KAMPANYA",
    ]
    for slug, n in rep["campaigns_per_bank"].items():
        satirlar.append(f"    {slug:<26} {n:>5}")
    satirlar += ["", "  ALAN KAPSAMI (kaç kampanyada var)"]
    for alan, n in rep["field_coverage"].items():
        satirlar.append(f"    {alan:<26} {n:>5}   %{100.0 * n / camp:5.1f}")
    satirlar += ["", "  KATMAN BAŞINA ALAN"]
    for ext, n in rep["fields_by_extractor"].items():
        satirlar.append(f"    {ext:<26} {n:>5}")
    if rep["contradictions_by_kind"]:
        satirlar += ["", "  ÇELİŞKİ TÜRLERİ"]
        for kind, n in rep["contradictions_by_kind"].items():
            satirlar.append(f"    {kind:<26} {n:>5}")
    satirlar += ["=" * 66, ""]
    return "\n".join(satirlar)


def _main(argv: Optional[list[str]] = None) -> int:
    ap = argparse.ArgumentParser(
        description="Korpustan kalıcı demo SQLite DB'si üretir (CLAUDE.md §11).")
    ap.add_argument("--out", default=DEFAULT_OUT,
                    help=f"çıktı SQLite dosyası (varsayılan: {DEFAULT_OUT})")
    ap.add_argument("--config", default=DEFAULT_CONFIG,
                    help=f"banks.yaml yolu (varsayılan: {DEFAULT_CONFIG})")
    ap.add_argument("--raw-dir", default=DEFAULT_RAW,
                    help=f"korpus kökü (varsayılan: {DEFAULT_RAW})")
    ap.add_argument("--database-url", default=None,
                    help="PostgreSQL hedefi (verilirse --out yok sayılır). "
                         "Boşsa DATABASE_URL ortam değişkenine bakılmaz — "
                         "hedef açıkça verilmeli ki kaza olmasın.")
    ap.add_argument("--force", action="store_true",
                    help="var olan DB dosyasını SİL ve yeniden kur")
    ap.add_argument("--quiet", action="store_true",
                    help="ilerleme göstergesini kapat")
    ap.add_argument("--json-report", default=None,
                    help="özet raporu JSON olarak da yaz")
    args = ap.parse_args(argv)

    # Yollar depo köküne göre çözülür; betik nereden çağrılırsa çağrılsın
    # aynı korpusu okusun (deterministiklik).
    def _resolve(p: str) -> str:
        return p if os.path.isabs(p) else str(ROOT / p)

    rep, code = build(_resolve(args.out), config=_resolve(args.config),
                      raw_dir=_resolve(args.raw_dir), force=args.force,
                      quiet=args.quiet,
                          database_url=args.database_url)
    if rep is None:
        return code
    print(format_report(rep))
    if args.json_report:
        path = Path(_resolve(args.json_report))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(rep, ensure_ascii=False, indent=2) + "\n",
                        encoding="utf-8")
        print(f"JSON rapor: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
