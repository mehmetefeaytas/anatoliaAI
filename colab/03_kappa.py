"""Colab κ runner — ikinci etiketleyici turu GPU'da, güçlü modelle.

Kullanım (Colab hücresi ya da `colab run` ile):

    !wget -qO kappa.py https://raw.githubusercontent.com/mehmetefeaytas/anatoliaAI/main/colab/03_kappa.py
    %run kappa.py

## Neden bu betik var

`scripts/ikinci_etiketleyici.py` 16 gold kaydına bağımsız bir ikinci etiket
kümesi üretip Cohen's κ ölçüyor (gerekçe o betiğin başlığında: gold.v2'de
etiketleyici örtüşmesi yoktu, κ hesaplanamıyordu).

Yerelde ikinci etiketleyici `qwen2.5:7b-instruct`, CPU'da ~11 token/s. Burada
`qwen3:32b` koşar — **daha güçlü bir ikinci yargıç**. Bu yalnız hız değil
ölçüm kalitesi meselesi: zayıf bir ikinci etiketleyici düşük κ üretir ve
düşük κ'nın sebebi "gold tutarsız" mı "ikinci yargıç yetersiz" mi ayırt
edilemez. İki modelle iki κ ölçmek tam bu ayrımı yapar.

Qwen3 ailesinde her boyut Apache-2.0 (bkz. `01_setup.py` lisans notu ve
`docs/model-license-audit.md` §1).

## Colab bir RUNNER'dır, teslim bağımlılığı DEĞİL

Şartname §5.9 "dış servislere bağımlı olmadan çalışabilme" maddesini %20
ağırlıkla puanlıyor. Bu betik Colab'ı bir servise ÇEVİRMEZ: tünel yok, port
dışa açılmıyor (`127.0.0.1`), ölçüm Colab'ın içinde koşar ve yalnızca **sonuç
dosyaları** indirilir. Teslim edilen sistem CPU'da, LLM'siz ya da Ollama
koluyla çalışır.

Raporda bu ayrım korunmak zorunda: "ölçüm A100'de yapıldı, teslim CPU'da
koşuyor". Aksi hâlde on-prem iddiası zedelenir.

## Kurulum kodu neden `02_ablasyon.py` ile tekrar ediyor

Colab'a tek dosya `wget` ediliyor; ortak bir `colab/_ortak.py` ikinci bir
indirme adımı ve iki dosyanın sürümlerinin ayrışması riski demek olurdu.
Tekrar burada bilinçli: kurulum ~30 satır, ayrışma riski ise bir raporun
yanlış modeli göstermesi kadar pahalı.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import time

REPO = "https://github.com/mehmetefeaytas/anatoliaAI.git"
KLON = "/content/anatoliaAI"
MODEL = os.environ.get("OLLAMA_MODEL", "qwen3:32b")
INSTALL_CMD = "curl -fsSL https://ollama.com/install.sh | sh"


def _kos(cmd: list[str], **kw) -> int:
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
    _kos(["git", "-C", KLON, "log", "-1", "--format=%H %s"])


def ollama_hazirla() -> None:
    print(f"\n=== Ollama + {MODEL} ===")
    if not shutil.which("ollama"):
        _kos(["apt-get", "-qq", "update"])
        _kos(["apt-get", "-qq", "install", "-y", "zstd", "pciutils"])
        _kos(["bash", "-c", INSTALL_CMD])

    ollama = shutil.which("ollama") or "/usr/local/bin/ollama"
    _kos(["pkill", "ollama"])
    time.sleep(3)
    # 127.0.0.1: dışa AÇMIYORUZ (tünel yok, on-prem hikâyesi temiz kalsın).
    os.environ["OLLAMA_HOST"] = "127.0.0.1:11434"
    # -1: modeli bellekte tut; soğuk yükleme her istekte 30+ sn ekler.
    os.environ["OLLAMA_KEEP_ALIVE"] = "-1"
    subprocess.Popen([ollama, "serve"])
    time.sleep(8)
    _kos([ollama, "pull", MODEL])
    print("\n  GPU teyidi — PROCESSOR sütunu '100% GPU' olmalı:")
    _kos([ollama, "ps"])


def kappa_kos() -> None:
    app = os.path.join(KLON, "app")
    ortam = dict(os.environ)
    ortam["LLM_BACKEND"] = "ollama"
    ortam["OLLAMA_MODEL"] = MODEL
    # KATI MOD: arka uç kurulamazsa exception. Onsuz koşum sessizce kural
    # motoruna düşer ve "ikinci etiketleyici" aslında birinci etiketleyicinin
    # kendi kodu olur — κ o hâlde hiçbir şeyin uyumunu ölçmez.
    ortam["LLM_STRICT"] = "1"

    print(f"\n=== ikinci etiketleyici turu ({MODEL}) ===")
    # `--bastan`: depoda yerel CPU koşumundan kalmış bir JSONL olabilir ve iki
    # modelin kararını tek κ'da toplamak ölçümü anlamsız kılar. Betiğin kendi
    # model kapısı bunu zaten reddediyor; `--bastan` niyeti açık yazar.
    t0 = time.time()
    kod = _kos([sys.executable, "-u", "-m", "scripts.ikinci_etiketleyici",
                "kos", "--bastan"], cwd=app, env=ortam)
    print(f"  süre: {time.time() - t0:.0f} sn · çıkış: {kod}")
    if kod != 0:
        print("  ❌ tur düştü — κ hesaplanmayacak")
        return

    print("\n=== κ + uyuşmazlık raporu ===")
    _kos([sys.executable, "-u", "-m", "scripts.ikinci_etiketleyici", "kappa"],
         cwd=app, env=ortam)


def sonuc_paketle() -> None:
    app = os.path.join(KLON, "app")
    hedef = "/content/kappa-sonuc.zip"
    print("\n=== paketleme ===")
    _kos(["zip", "-qr", hedef,
          "data/gold/review/ikinci-tur-llm.jsonl",
          "data/gold/review/_kappa-ikinci-tur.md"], cwd=app)
    print(f"  {hedef}")
    print("\nİndirme (Colab hücresi):")
    print(f"  from google.colab import files; files.download('{hedef}')")
    print("\nSonra yerelde: zip'i açıp `app/data/gold/review/` altına koyun ve")
    print("commit edin. Rapora ŞU NOT eklenmeli: ölçüm A100'de yapıldı,")
    print("teslim edilen sistem CPU'da koşuyor (Colab bir runner'dır).")


def main() -> None:
    print(f"MODEL = {MODEL}")
    gpu_teyidi()
    repo_hazirla()
    ollama_hazirla()
    kappa_kos()
    sonuc_paketle()


if __name__ == "__main__":
    main()
