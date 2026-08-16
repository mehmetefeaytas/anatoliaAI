#!/usr/bin/env bash
#
# Anatolia AI — `scripts/baslat.sh`ın kaldırdığı yığını kapatır.
#
# ## Neden yalnız kendi başlattığını kapatır
#
# Kapatma, pid dosyalarından yürür; "portu tutan neyse öldür" mantığı bilerek
# kullanılmaz. Ollama daemon'ı buna iyi bir örnek: kullanıcının kendi
# Ollama.app'i çalışıyorsa `baslat.sh` onu sahiplenmemiş, dolayısıyla pid
# dosyası da yazmamıştır — ve burada ona dokunulmaz. Yalnız betiğin KENDİ
# başlattığı daemon kapanır.
#
# Model ağırlığı ayrıca bellekten düşürülür (`ollama stop`): daemon ayakta
# kalsa bile ~4,7 GB RAM boşa tutulmasın.

set -euo pipefail

KOK="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CALISMA="$KOK/.calisma"
OLLAMA_MODEL="${OLLAMA_MODEL:-qwen2.5:7b-instruct}"

soluk() { printf '\033[2m%s\033[0m\n' "$*"; }

kapat() {
  local ad="$1" pidf="$CALISMA/$2.pid" pid
  [ -f "$pidf" ] || { soluk "$ad: pid dosyası yok, atlandı"; return 0; }
  pid="$(cat "$pidf" 2>/dev/null || true)"
  rm -f "$pidf"
  [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null || { soluk "$ad: zaten kapalı"; return 0; }

  # SÜREÇ GRUBUNA sinyal (`-$pid`), tek sürece değil. `baslat.sh` `set -m` ile
  # koştuğu için her süreç kendi grubunun lideridir, yani grup kimliği = pid.
  # Gerekçe: `next dev` çocuğu `next-server`ı doğurur ve kendisi ölünce onu
  # arkada bırakır; tek pid'ye kill atmak 3000 portunu yetim bir süreçte tutulu
  # bırakıyordu. Grup yoksa (eski bir koşumdan kalma pid) tekil kill'e düşülür.
  kill -TERM -- "-$pid" 2>/dev/null || kill -TERM "$pid" 2>/dev/null || true
  for _ in $(seq 1 10); do
    kill -0 "$pid" 2>/dev/null || { echo "$ad: kapatıldı (pid $pid)"; return 0; }
    sleep 1
  done
  # 10 sn'de kapanmadıysa SIGKILL. Uvicorn/Next için veri kaybı riski yok:
  # ikisi de yazma yapmıyor, demo.db salt okunur yolda kullanılıyor.
  kill -9 -- "-$pid" 2>/dev/null || kill -9 "$pid" 2>/dev/null || true
  echo "$ad: zorla kapatıldı (pid $pid)"
}

kapat "panel" web
kapat "API"   api

# Ağırlığı bellekten düşür. Daemon kimin olursa olsun bu güvenlidir: yalnız
# modeli boşaltır, servisi kapatmaz.
if command -v ollama >/dev/null 2>&1 && curl -sf -m 3 http://localhost:11434/api/tags >/dev/null 2>&1; then
  ollama stop "$OLLAMA_MODEL" >/dev/null 2>&1 || true
  soluk "model bellekten boşaltıldı: $OLLAMA_MODEL"
fi

kapat "ollama daemon" ollama

echo "durduruldu."
