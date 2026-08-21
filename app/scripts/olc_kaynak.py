"""On-prem kaynak tüketimi ölçüm betiği — docs/kaynak-tuketimi.md'yi besler.

## Neden bu betik var

Jüri (3. tur) `docs/kaynak-tuketimi.md`'deki üç donanım profilinin (CPU-LLM,
tüketici GPU, sunucu GPU) hepsinin `⏳ ölçülmedi` olduğunu, yani rubrik
"kurum içi ortamda çalışabilme" maddesi için yeterli kanıt sunulmadığını
yazdı. Bu betik, BU makinede (Apple Silicon, macOS, GPU yok) gerçekten
ölçülebilecek üç şeyi ölçer ve komutuyla birlikte JSON'a yazar — tabloya
"tahmini" bir sayı eklemez, yalnızca gerçekten koşan bir şeyin sonucunu.

Ölçtükleri:
  1. `api`    — ayakta bekleyen `uvicorn` sürecinin RSS'i + `/stats` ve
                `/chat` uçlarının gecikmesi (medyan + p95, N istek).
  2. `ollama` — kurulu modellerin (`ollama list`) dosya boyutu (API'den,
                gerçek bayt) + soğuk/sıcak çağrı süresi + çağrı sırasında
                `ollama ps` üzerinden bellek.
  3. `disk`   — korpus / DB / model ağırlığı / Docker imajı boyutları.

Ölçmediği (bilerek): GPU/VRAM (bu makinede NVIDIA GPU yok), vLLM (kurulu
değil, GPU gerektirir). Bunlar `docs/kaynak-tuketimi.md` §4/§5'te "neden
ölçülmedi" ile birlikte ayrıca belgelenir; bu betik onlar için sahte bir
sayı ÜRETMEZ.

## Kullanım

    .venv/bin/python -m scripts.olc_kaynak api --db /tmp/x.db --port 8042 \\
        --n 30 --json /tmp/api.json
    .venv/bin/python -m scripts.olc_kaynak ollama --model qwen2.5:7b-instruct \\
        --json /tmp/ollama.json
    .venv/bin/python -m scripts.olc_kaynak disk --json /tmp/disk.json

`data/demo.db` SALT-OKUNUR kullanılır (asla üzerine yazılmaz); `api` alt
komutu verdiğiniz `--db` dosyasını AÇAR, değiştirmez (sunucu yalnız GET/POST
sorgu yolları çağrılır, `/extract` gibi yazma uçları bilerek koşulmaz).
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import statistics
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _sh(cmd: list[str], **kw) -> str:
    return subprocess.run(cmd, capture_output=True, text=True, **kw).stdout.strip()


def _rss_kb(pid: int) -> int | None:
    """macOS `ps -o rss=` KB döner (Linux'ta da KB — burada platform farkı
    YOK, ru_maxrss'teki farktan ayrı bir konudur)."""
    out = _sh(["ps", "-o", "rss=", "-p", str(pid)])
    try:
        return int(out.strip())
    except ValueError:
        return None


# --------------------------------------------------------------------- #
# 1) API servisi: ayakta RSS + /stats + /chat gecikmesi
# --------------------------------------------------------------------- #

def cmd_api(args: argparse.Namespace) -> dict:
    env = os.environ.copy()
    env["DATABASE_PATH"] = str(Path(args.db).resolve())
    env.setdefault("LLM_BACKEND", "")  # kritik yolda LLM yok — CLAUDE.md §11

    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "src.api.main:app",
         "--host", "127.0.0.1", "--port", str(args.port)],
        cwd=str(ROOT), env=env,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    base = f"http://127.0.0.1:{args.port}"
    try:
        # /health ayakta olana kadar bekle (en çok ~20 sn)
        ok = False
        for _ in range(100):
            try:
                urllib.request.urlopen(f"{base}/health", timeout=1).read()
                ok = True
                break
            except (urllib.error.URLError, ConnectionError, OSError):
                time.sleep(0.2)
        if not ok:
            raise RuntimeError("API /health 20 sn içinde ayağa kalkmadı")

        time.sleep(1.0)  # import/JIT ısınması otursun, boşta RSS'i ölç
        idle_rss_kb = _rss_kb(proc.pid)

        def _timed_get(path: str) -> float:
            t0 = time.perf_counter()
            urllib.request.urlopen(f"{base}{path}", timeout=10).read()
            return (time.perf_counter() - t0) * 1000.0

        def _timed_post(path: str, body: dict) -> float:
            data = json.dumps(body).encode("utf-8")
            req = urllib.request.Request(
                f"{base}{path}", data=data,
                headers={"Content-Type": "application/json"}, method="POST")
            t0 = time.perf_counter()
            urllib.request.urlopen(req, timeout=10).read()
            return (time.perf_counter() - t0) * 1000.0

        # Isınma turu (ilk istek her zaman daha yavaştır — soğuk yol dahil
        # edilmez, N ölçümün hepsi ısındıktan SONRA alınır).
        _timed_get("/stats")
        _timed_post("/chat", {"question": "kâr payı oranı nedir", "context": []})

        stats_ms = [_timed_get("/stats") for _ in range(args.n)]
        chat_ms = [_timed_post("/chat", {"question": "kâr payı oranı nedir",
                                          "context": []})
                   for _ in range(args.n)]
        busy_rss_kb = _rss_kb(proc.pid)

        def _summ(xs: list[float]) -> dict:
            xs_sorted = sorted(xs)
            p95_idx = max(0, int(len(xs_sorted) * 0.95) - 1)
            return {"n": len(xs), "medyan_ms": round(statistics.median(xs), 2),
                    "p95_ms": round(xs_sorted[p95_idx], 2),
                    "min_ms": round(min(xs), 2), "max_ms": round(max(xs), 2)}

        return {
            "olcum": "api",
            "tarih": time.strftime("%Y-%m-%d %H:%M:%S"),
            "platform": platform.platform(),
            "db_dosyasi": str(Path(args.db).resolve()),
            "db_boyutu_bayt": Path(args.db).stat().st_size,
            "idle_rss_kb": idle_rss_kb,
            "busy_rss_kb": busy_rss_kb,
            "stats_latency_ms": _summ(stats_ms),
            "chat_latency_ms": _summ(chat_ms),
        }
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


# --------------------------------------------------------------------- #
# 2) Ollama: model boyutu + soğuk/sıcak çağrı + bellek
# --------------------------------------------------------------------- #

def _ollama_generate(model: str, prompt: str, host: str) -> dict:
    body = json.dumps({"model": model, "prompt": prompt,
                        "stream": False}).encode("utf-8")
    req = urllib.request.Request(f"{host}/api/generate", data=body,
                                  headers={"Content-Type": "application/json"})
    t0 = time.perf_counter()
    with urllib.request.urlopen(req, timeout=300) as resp:
        d = json.loads(resp.read())
    wall_s = time.perf_counter() - t0
    d["_wall_s"] = round(wall_s, 3)
    return d


def cmd_ollama(args: argparse.Namespace) -> dict:
    host = args.host
    model = args.model
    prompt = args.prompt

    # Model dosya boyutu — gerçekten sorgulanır (tahmin yok)
    with urllib.request.urlopen(f"{host}/api/tags", timeout=10) as resp:
        tags = json.loads(resp.read())
    size_bytes = None
    quant = None
    for m in tags.get("models", []):
        if m.get("name") == model:
            size_bytes = m.get("size")
            quant = m.get("details", {}).get("quantization_level")
    if size_bytes is None:
        raise RuntimeError(f"model kurulu değil: {model} (bkz. `ollama list`)")

    # Modelin belleğe daha önce yüklenmemiş olduğundan emin ol (soğuk çağrı
    # gerçekten soğuk olsun diye) — zaten yüklüyse bunu da rapora yazıyoruz,
    # gizlemiyoruz.
    ps_before = _sh(["ollama", "ps"])
    already_loaded = model in ps_before

    cold = _ollama_generate(model, prompt, host)
    ps_during_cold = _sh(["ollama", "ps"])
    warm = _ollama_generate(model, prompt, host)
    ps_during_warm = _sh(["ollama", "ps"])

    return {
        "olcum": "ollama",
        "tarih": time.strftime("%Y-%m-%d %H:%M:%S"),
        "model": model,
        "model_dosya_boyutu_bayt": size_bytes,
        "quantization": quant,
        "onceden_yukluymus": already_loaded,
        "soguk": {
            "wall_s": cold["_wall_s"],
            "total_duration_ns": cold.get("total_duration"),
            "load_duration_ns": cold.get("load_duration"),
            "prompt_eval_count": cold.get("prompt_eval_count"),
            "eval_count": cold.get("eval_count"),
            "eval_duration_ns": cold.get("eval_duration"),
        },
        "sicak": {
            "wall_s": warm["_wall_s"],
            "total_duration_ns": warm.get("total_duration"),
            "load_duration_ns": warm.get("load_duration"),
            "prompt_eval_count": warm.get("prompt_eval_count"),
            "eval_count": warm.get("eval_count"),
            "eval_duration_ns": warm.get("eval_duration"),
        },
        "ollama_ps_soguk_sirasinda": ps_during_cold,
        "ollama_ps_sicak_sirasinda": ps_during_warm,
    }


# --------------------------------------------------------------------- #
# 3) Disk: korpus / DB / Docker imajları
# --------------------------------------------------------------------- #

def _du_bytes(path: Path) -> int | None:
    if not path.exists():
        return None
    out = _sh(["du", "-sk", str(path)])
    if not out:
        return None
    kb = int(out.split()[0])
    return kb * 1024


def cmd_disk(args: argparse.Namespace) -> dict:
    report: dict = {
        "olcum": "disk",
        "tarih": time.strftime("%Y-%m-%d %H:%M:%S"),
        "korpus_data_raw_bayt": _du_bytes(ROOT / "data" / "raw"),
        "demo_db_bayt": (ROOT / "data" / "demo.db").stat().st_size
        if (ROOT / "data" / "demo.db").exists() else None,
    }
    # Docker imajları (varsa)
    try:
        out = _sh(["docker", "images", "--format",
                    "{{.Repository}}:{{.Tag}}\t{{.Size}}"])
        report["docker_images"] = out.splitlines() if out else []
    except FileNotFoundError:
        report["docker_images"] = None  # docker kurulu değil

    return report


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_api = sub.add_parser("api", help="API servisi RSS + gecikme")
    p_api.add_argument("--db", required=True,
                        help="SQLite DB yolu (salt-okunur açılır, data/demo.db DEĞİL bir kopya kullanın)")
    p_api.add_argument("--port", type=int, default=8042)
    p_api.add_argument("--n", type=int, default=20,
                        help="ısınma sonrası her uç için istek sayısı")
    p_api.add_argument("--json", dest="json_out", default=None,
                        help="sonucu bu dosyaya JSON yaz")

    p_ollama = sub.add_parser("ollama", help="Ollama soğuk/sıcak çağrı")
    p_ollama.add_argument("--model", required=True)
    p_ollama.add_argument("--host", default="http://localhost:11434")
    p_ollama.add_argument(
        "--prompt", default="Katılım bankacılığında kâr payı oranı nedir? "
                             "Tek cümleyle özetle.")
    p_ollama.add_argument("--json", dest="json_out", default=None,
                           help="sonucu bu dosyaya JSON yaz")

    p_disk = sub.add_parser("disk", help="korpus/DB/imaj boyutları")
    p_disk.add_argument("--json", dest="json_out", default=None,
                         help="sonucu bu dosyaya JSON yaz")

    args = ap.parse_args()

    fn = {"api": cmd_api, "ollama": cmd_ollama, "disk": cmd_disk}[args.cmd]
    result = fn(args)
    text = json.dumps(result, ensure_ascii=False, indent=2)
    print(text)
    if args.json_out:
        Path(args.json_out).write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
