"""Colab ablasyon runner — gold.v2 üzerinde 4 konfig + McNemar, GPU'da.

Kullanım (Colab, iki hücre):

    !wget -qO abl.py https://raw.githubusercontent.com/mehmetefeaytas/anatoliaAI/main/colab/02_ablasyon.py
    %env ABLASYON_BACKEND=ollama
    %run abl.py

vLLM kolu için ikinci koşum:

    %env ABLASYON_BACKEND=vllm
    %run abl.py

## Neden bu betik var

`docs/rapor/ablasyon.md` 5 Ağustos'ta koşuldu ve hibridin kural katmanını
geçemediğini ölçtü (0,575 < 0,612, McNemar p = 0,0117). Ama o raporun kendi
sınırı şudur:

> Hibrit özellikle ZOR vakalarda kazanır → ❌ Ölçülemedi — gold'da yalnız
> **1** zor belge var

O gün gold'da 1 zor belge vardı; bugün `gold.v2`'de **40** var. Yani
karşılaştırma ilk kez zor vaka alt kümesinde anlamlı ölçülebilir durumda.
Ayrıca `docker-compose`'un ANA modeli (Trendyol-LLM-8B-T1) GPU gerektirdiği
için bugüne kadar hiç ölçülemedi — `docs/OFFLINE-KANIT.md` bunu açıkça
"hiç koşturulmadı" diye yazıyor.

Yerelde (CPU, `qwen2.5:7b-instruct`) ölçüm ~8 token/s ile belge başına
60 saniye sürüyor: 48 belge ≈ 48 dakika, dört konfig ≈ 3 saat. A100'de aynı
iş dakikalar alır. Bu betiğin tek işi o hızı kullanmak.

## Colab bir RUNNER'dır, teslim bağımlılığı DEĞİL

`01_setup.py`'deki gerekçenin aynısı burada da geçerli ve tekrar yazılıyor
çünkü rapora giren sayının yanında durması gerekiyor:

Şartname §5.9 "dış servislere bağımlı olmadan çalışabilme" maddesini %20
ağırlıkla puanlıyor. Bu betik Colab'ı bir servise ÇEVİRMEZ: tünel yok, port
dışa açılmıyor (`127.0.0.1`), eval Colab'ın içinde koşar ve yalnızca **sonuç
dosyaları** indirilir. Teslim edilen sistem CPU'da, LLM'siz ya da Ollama
koluyla çalışır; Colab yalnız ÖLÇÜM aracıdır.

Bu ayrım raporda korunmak zorunda: "ölçüm A100'de yapıldı, teslim CPU'da
koşuyor". Aksi hâlde on-prem iddiası zedelenir.

## Bağımlılık: yok (çekirdek saf stdlib)

`eval/run_eval.py` ve `eval/ablation.py` numpy/scipy/sklearn kullanmaz —
bootstrap ve McNemar el yazımı, `env.json` her koşumda bunu kaydeder. Bu
yüzden Colab'da `pip install -r requirements.txt` GEREKMEZ; yalnız seçilen
backend kurulur. Kurulum süresi ve sürüm çakışması riski böylece sıfıra iner.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import time

REPO = "https://github.com/mehmetefeaytas/anatoliaAI.git"
KLON = "/content/anatoliaAI"

BACKEND = os.environ.get("ABLASYON_BACKEND", "ollama").strip().lower()

# Ollama kolu — `01_setup.py` ile AYNI varsayılan. Qwen3 ailesinde her boyut
# Apache-2.0 (bkz. 01_setup.py lisans notu ve docs/model-license-audit.md §1).
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "qwen3:32b")

# vLLM kolu — `docker-compose`'un ANA modeli. Taban zinciri
# `Qwen3-8B-Base → Qwen3-8B → Trendyol-8B`, hepsi Apache-2.0
# (docs/model-license-audit.md §1, satır "Trendyol-LLM-8B-T1").
VLLM_MODEL = os.environ.get("VLLM_MODEL", "Trendyol/Trendyol-LLM-8B-T1")

# Ölçülecek konfigler. `kural` da koşulur çünkü karşılaştırmanın taban çizgisi
# AYNI koşumdan gelmek zorunda: farklı koşumların sayılarını yan yana koymak
# (farklı gold sürümü, farklı kod) 5 Ağustos raporunun düştüğü tuzaktı.
KONFIGLER = ("kural", "llm", "hibrit", "hibrit-verify")

GOLD = "data/gold/gold.v2.json"
INSTALL_CMD = "curl -fsSL https://ollama.com/install.sh | sh"


def _kos(cmd: list[str], **kw) -> int:
    """Komutu bas ve koş. Çıktı Colab hücresinde görünür."""
    print("  $ " + " ".join(cmd))
    return subprocess.run(cmd, check=False, **kw).returncode


def gpu_teyidi() -> None:
    print("=== GPU ===")
    if not shutil.which("nvidia-smi"):
        print("  ⚠️  nvidia-smi YOK — bu bir GPU çalışma zamanı değil.")
        print("     Colab: Runtime > Change runtime type > A100/L4 seçin.")
        sys.exit(1)
    _kos(["nvidia-smi", "--query-gpu=name,memory.total",
          "--format=csv,noheader"])


def repo_hazirla() -> None:
    print("\n=== Depo ===")
    if os.path.isdir(KLON):
        _kos(["git", "-C", KLON, "fetch", "-q", "origin", "main"])
        _kos(["git", "-C", KLON, "reset", "-q", "--hard", "origin/main"])
    else:
        _kos(["git", "clone", "-q", "--depth", "1", REPO, KLON])
    # Ölçümün hangi commit'te yapıldığı rapora girer; env.json bunu kaydeder
    # ama hücre çıktısında da görünmesi gerekiyor.
    _kos(["git", "-C", KLON, "log", "-1", "--format=%H %s"])


def ollama_hazirla() -> None:
    print(f"\n=== Ollama + {OLLAMA_MODEL} ===")
    if not shutil.which("ollama"):
        _kos(["apt-get", "-qq", "update"])
        _kos(["apt-get", "-qq", "install", "-y", "zstd", "pciutils"])
        # Boru gerektiği için bash -c; komut sabittir, dışarıdan girdi almaz.
        _kos(["bash", "-c", INSTALL_CMD])

    ollama = shutil.which("ollama") or "/usr/local/bin/ollama"
    _kos(["pkill", "ollama"])
    time.sleep(3)

    # 127.0.0.1: dışa AÇMIYORUZ (tünel yok, on-prem hikâyesi temiz kalsın).
    os.environ["OLLAMA_HOST"] = "127.0.0.1:11434"
    # -1: modeli bellekte tut. Soğuk yükleme her istekte 30+ sn ekler ve
    # dört konfiglik uzun koşumda timeout üretir.
    os.environ["OLLAMA_KEEP_ALIVE"] = "-1"
    subprocess.Popen([ollama, "serve"])
    time.sleep(8)

    _kos([ollama, "pull", OLLAMA_MODEL])
    print("\n  GPU teyidi — PROCESSOR sütunu '100% GPU' olmalı:")
    _kos([ollama, "ps"])

    os.environ["LLM_BACKEND"] = "ollama"
    os.environ["OLLAMA_MODEL"] = OLLAMA_MODEL


def vllm_hazirla() -> None:
    print(f"\n=== vLLM + {VLLM_MODEL} ===")
    try:
        import vllm  # noqa: F401
        print("  vllm zaten kurulu")
    except ModuleNotFoundError:
        _kos([sys.executable, "-m", "pip", "install", "-q", "vllm"])

    # Sunucu ARKA PLANDA; OpenAI-uyumlu uç `clients.VLLMClient`'ın beklediği
    # adreste (127.0.0.1:8000). Dışa açılmıyor.
    log = open("/content/vllm-serve.log", "w")
    subprocess.Popen(
        [sys.executable, "-m", "vllm.entrypoints.openai.api_server",
         "--model", VLLM_MODEL, "--host", "127.0.0.1", "--port", "8000",
         "--max-model-len", "8192"],
        stdout=log, stderr=subprocess.STDOUT,
    )

    print("  sunucu ısınıyor (ağırlık indirme + yükleme, 3-10 dk sürebilir)…")
    import urllib.error
    import urllib.request
    for i in range(120):
        time.sleep(15)
        try:
            with urllib.request.urlopen(
                    "http://127.0.0.1:8000/v1/models", timeout=5) as r:
                if r.status == 200:
                    print(f"  hazır ({(i + 1) * 15} sn)")
                    break
        except (urllib.error.URLError, OSError):
            if i % 4 == 0:
                print(f"    … {(i + 1) * 15} sn")
    else:
        print("  ❌ vLLM ayağa kalkmadı. Günlük: /content/vllm-serve.log")
        _kos(["tail", "-40", "/content/vllm-serve.log"])
        sys.exit(1)

    os.environ["LLM_BACKEND"] = "vllm"
    os.environ["VLLM_MODEL"] = VLLM_MODEL


def eval_kos() -> list[str]:
    """Dört konfigi sırayla koşar, rapor dizinlerini döndürür."""
    app = os.path.join(KLON, "app")
    # KATI MOD: arka uç kurulamazsa exception. Onsuz koşum sessizce
    # kural-only'ye düşer ve tablo YANLIŞ ETİKETLE yayımlanır — ablasyonun
    # en tehlikeli hata sınıfı tam budur.
    os.environ["LLM_STRICT"] = "1"

    dizinler = []
    for konfig in KONFIGLER:
        print(f"\n=== eval: {konfig} ===")
        t0 = time.time()
        kod = _kos([sys.executable, "-u", "-m", "eval.run_eval",
                    "--gold", GOLD, "--config", konfig], cwd=app)
        print(f"  süre: {time.time() - t0:.0f} sn · çıkış: {kod}")
        if kod != 0:
            print(f"  ⚠️  {konfig} düştü — ablasyon eksik kolla koşacak")
    print("\n=== ablasyon (McNemar dahil) ===")
    # `--gold` ZORUNLU argümandır ve eksikti: bu adım her koşumda
    # `error: the following arguments are required: --gold` ile sessizce
    # düşüyordu. Dört eval koşumu başarıyla tamamlanıyor, ardından
    # karşılaştırma tablosu hiç üretilmiyordu — yani betiğin varlık sebebi
    # olan tek artefakt eksik kalıyordu (ölçüldü: 2026-08-20).
    #
    # `LLM_STRICT` ve `LLM_BACKEND` de ortamda kalmak ZORUNDA: `eval.ablation`
    # kolları KENDİ koşumunda ölçüyor, mevcut rapor dizinlerinden okumuyor.
    # Env taşınmazsa LLM kolları "ÖLÇÜLMEDİ (backend kapalı)" diye atlanır ve
    # tablo yalnız kural satırıyla üretilir.
    _kos([sys.executable, "-u", "-m", "eval.ablation", "--gold", GOLD],
         cwd=app, env={**os.environ, "LLM_STRICT": "1"})
    return dizinler


def sonuc_paketle() -> None:
    app = os.path.join(KLON, "app")
    hedef = "/content/ablasyon-sonuc.zip"
    print("\n=== paketleme ===")
    _kos(["zip", "-qr", hedef, "eval/reports", "docs/rapor/ablasyon.md"],
         cwd=app)
    print(f"  {hedef}")
    print("\nİndirme (Colab hücresi):")
    print("  from google.colab import files; files.download("
          f"'{hedef}')")
    print("\nSonra yerelde: zip'i açıp `app/eval/reports/` altına koyun ve")
    print("commit edin. Rapora ŞU NOT eklenmeli: ölçüm A100'de yapıldı,")
    print("teslim edilen sistem CPU'da koşuyor (Colab bir runner'dır).")


def main() -> None:
    print(f"ABLASYON_BACKEND = {BACKEND}")
    if BACKEND not in ("ollama", "vllm"):
        print("  ❌ ABLASYON_BACKEND 'ollama' ya da 'vllm' olmalı")
        sys.exit(1)

    gpu_teyidi()
    repo_hazirla()
    if BACKEND == "ollama":
        ollama_hazirla()
    else:
        vllm_hazirla()
    eval_kos()
    sonuc_paketle()


if __name__ == "__main__":
    main()
