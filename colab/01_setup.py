"""Colab A100 kurulumu — Ollama + model + GPU teyidi.

Kullanım (tek Colab hücresi):

    !wget -qO setup.py https://raw.githubusercontent.com/mehmetefeaytas/anatoliaAI/main/colab/01_setup.py
    %run setup.py

## Neden tünel (cloudflared) YOK

Şartname §5.9 "dış servislere bağımlı olmadan çalışabilmesi" maddesini %20
ağırlıkla puanlıyor. Colab'ı bir SERVİS haline getirmek (tünelle dışarı açmak)
bu iddiayı zedeler. Colab burada yalnızca bir RUNNER'dır: eval Colab'ın
içinde koşar, sonuç dosyaları indirilir. Ayrıca 250 belge x 12 alan bir tünel
üzerinden çekilirse hem yavaştır hem 524 timeout üretir.

## Model lisansı — dikkat

Qwen3 ailesinde HER boyut Apache-2.0.
Qwen2.5'te ise 72B ve 3B AYRI "Qwen License" altındadır — şartname §5.10
("açık kaynaklı gözüküp lisans problemi çıkarma potansiyeli olan çözümler
kullanılmamalıdır") kapsamına girer. Bu yüzden qwen2.5:72b KULLANILMAZ.

İlgili: app/docs/model-license-audit.md
"""

import os
import shutil
import subprocess
import time

# Qwen3 -> her boyut Apache-2.0. A100 40GB'de 32b-Q4 (~20GB) rahat sığar.
MODEL = os.environ.get("SMOKE_MODEL", "qwen3:32b")

# Ollama resmi kurulum betiği. Sabit dize; kullanıcı girdisi içermez.
INSTALL_CMD = "curl -fsSL https://ollama.com/install.sh | sh"


def main() -> None:
    print("=== GPU ===")
    subprocess.run(
        ["nvidia-smi", "--query-gpu=name,memory.total",
         "--format=csv,noheader"],
        check=False,
    )

    if not shutil.which("ollama"):
        print("\n=== Ollama kuruluyor ===")
        subprocess.run(["apt-get", "-qq", "update"], check=False)
        subprocess.run(
            ["apt-get", "-qq", "install", "-y", "zstd", "pciutils"],
            check=False,
        )
        # Boru (pipe) gerektiği için bash -c; komut sabittir.
        subprocess.run(["bash", "-c", INSTALL_CMD], check=False)

    ollama = shutil.which("ollama") or "/usr/local/bin/ollama"
    print(f"ollama yolu: {ollama}")

    subprocess.run(["pkill", "ollama"], check=False)
    time.sleep(3)

    # 127.0.0.1: dışa AÇMIYORUZ (tünel yok, on-prem hikâyesi temiz kalsın)
    os.environ["OLLAMA_HOST"] = "127.0.0.1:11434"
    # -1: modeli bellekte tut. Soğuk yükleme her istekte 30+ sn ekler ve
    # uzun eval koşularında timeout üretir.
    os.environ["OLLAMA_KEEP_ALIVE"] = "-1"

    subprocess.Popen([ollama, "serve"])
    time.sleep(8)

    print(f"\n=== Model indiriliyor: {MODEL} ===")
    subprocess.run([ollama, "pull", MODEL], check=False)

    print("\n=== GPU teyidi (PROCESSOR sutunu '100% GPU' olmali) ===")
    subprocess.run([ollama, "run", MODEL, "Merhaba."], check=False)
    subprocess.run([ollama, "ps"], check=False)

    print("\nHazir. Sirada:")
    print("  !wget -qO smoke.py https://raw.githubusercontent.com/"
          "mehmetefeaytas/anatoliaAI/main/colab/00_smoke_test.py")
    print("  %run smoke.py")


if __name__ == "__main__":
    main()
