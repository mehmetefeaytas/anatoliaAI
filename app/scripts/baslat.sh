#!/usr/bin/env bash
#
# Anatolia AI — tüm yığını tek komutla ayağa kaldırır (API + panel + yerel model).
#
# ## Neden bu dosya var
#
# 16 Ağu 2026'ya kadar yığını kaldırmanın iki yolu vardı: `docker-compose up`
# (imaj derlemesi ister, üstelik `LLM_BACKEND` boş gelir — yani yerel model
# KAPALI açılır) ya da üç ayrı terminalde elle `ollama` + `uvicorn` + `next`.
# Elle yol her seferinde altı ortam değişkeninin doğru yazılmasına bağlıydı ve
# biri unutulduğunda sistem SESSİZCE farklı bir sistem oluyordu.
#
# Bu betiğin varlık sebebi olan somut arıza (16 Ağu 2026): 8000 portunu üç gün
# önce LLM'siz başlatılmış bir `uvicorn` tutuyordu. Panel doğru davrandı ve
# "yerel model kapalı" dedi; ama LLM aslında AÇILMIŞTI — yalnızca başka bir
# portta. Yani "başlattım" sanılan şeyle ekranda görülen şey birbirinden
# ayrılmıştı ve bunu fark etmek yarım saat aldı. Aşağıdaki port sahipliği
# denetimi (§3) ve bitişteki ölçülmüş durum çıktısı (§6) bunun içindir.
#
# ## Kullanım
#
#     make baslat              # yerel model AÇIK (varsayılan)
#     LLM=0 make baslat        # kural-only — model hiç yüklenmez
#     make durdur              # hepsini kapatır
#
# Doğrudan da çağrılabilir: `bash scripts/baslat.sh`

set -euo pipefail

# Betik nereden çağrılırsa çağrılsın uygulama kökünde koşar. `cd app` unutulduğu
# için `data/demo.db`nin bulunamaması ve sistemin fixture'lara düşmesi olağan bir
# hataydı — korpus 1.782'den 40'a iner ve bunu kimse fark etmez.
KOK="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$KOK"

PY="$KOK/.venv/bin/python"
CALISMA="$KOK/.calisma"          # log + pid; `.gitignore`'da — türetilmiş, izlenmez
API_PORT="${API_PORT:-8000}"
WEB_PORT="${WEB_PORT:-3000}"
LLM="${LLM:-1}"                  # 1 = yerel model açık (varsayılan), 0 = kural-only

# Model etiketi `.env.example:56` ile BİREBİR aynı olmalı. Ollama kısaltma
# çözmez: `qwen2.5:7b` kurulu değildir ve "model not found" verir. Bu ağırlık
# lisans denetiminden geçmiş olandır (Apache-2.0, kök `Qwen/Qwen2.5-7B`,
# Llama/Gemma yok — docs/model-license-audit.md §1). Makinede duran
# `qwen3.5:9b` denetimde "yalnız ölçüm aracı" diye kayıtlıdır ve teslim edilen
# kod yolunda KULLANILMAZ; varsayılan olarak buraya yazmak o kaydı yalanlardı.
OLLAMA_MODEL="${OLLAMA_MODEL:-qwen2.5:7b-instruct}"
OLLAMA_URL="${OLLAMA_URL:-http://localhost:11434}"

mkdir -p "$CALISMA"

kirmizi() { printf '\033[31m%s\033[0m\n' "$*" >&2; }
yesil()   { printf '\033[32m%s\033[0m\n' "$*"; }
soluk()   { printf '\033[2m%s\033[0m\n' "$*"; }

# Komutu YENİ OTURUMDA (`setsid`) başlatır. İki işi birden yapar:
#
# 1. Betikten devralınan açık dosya tanıtıcılarını koparır. Ölçüldü
#    (16 Ağu 2026): `next dev` devraldığı boruyu kapatmıyordu, dolayısıyla
#    `make baslat | tail` yazan bir kullanıcıda yığın 5 sn'de kalkıyor ama
#    kabuk geri DÖNMÜYORDU. `> log 2>&1 < /dev/null` yetmedi; ayrı oturum
#    gerekti. (Teşhis: `lsof -p <next pid>` dört adet PIPE gösteriyordu,
#    uvicorn'da hiç yoktu.)
#
# 2. Süreci kendi süreç grubunun lideri yapar, yani grup kimliği = pid.
#    `durdur.sh` gruba sinyal gönderiyor; buna dayanıyor. Gerekçesi:
#    `next dev` bir gözetmen süreçtir ve SIGTERM aldığında çocuğu
#    `next-server`ı arkada BIRAKIR — ölçüldü, 3000 portu yetim süreçte
#    tutulu kalmıştı.
#
# macOS'ta `setsid` komutu yoktur. Python'un `os.setsid()`i aynı işi görür.
#
# Baştaki `exec` ŞART. Fonksiyon `&` ile çağrıldığında bash önce bir ara kabuk
# çatallar; `exec` olmadan python O kabuğun ÇOCUĞU olur ve `$!` ara kabuğun
# pid'sini verir. Ölçüldü (16 Ağu 2026): pid dosyalarında 2184/2210 yazıyordu,
# gerçek sunucular 2186/2211'di — `durdur` ara kabuğu öldürüp sunucuları
# yaşatıyordu. `exec` ara kabuğu python'a DÖNÜŞTÜRÜR, `execvp` da onu hedef
# komuta; pid baştan sona aynı kalır.
#
# Bu yüzden `ayrik` YALNIZ `&` ile çağrılır — ön planda çağrılırsa betiğin
# kendisini değiştirir.
ayrik() {
  exec "$PY" -c 'import os, sys
os.setsid()
os.execvp(sys.argv[1], sys.argv[1:])' "$@"
}

# ---------------------------------------------------------------- §1 ön koşullar
#
# Hepsi ÖNCE denetlenir. Yarım kalkmış bir yığın (API açık, panel yok) en kötü
# durumdur: bir şey çalışıyor gibi görünür, sorun başka yerde aranır.

[ -x "$PY" ] || { kirmizi "yok: $PY
  çözüm: cd app && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt"; exit 1; }

[ -d "$KOK/web/node_modules" ] || { kirmizi "yok: web/node_modules
  çözüm: cd app/web && npm install"; exit 1; }

# demo.db ZORUNLU değil — yoksa API fixture'lardan tohumlar ve sistem yine
# çalışır. Ama korpus 1.782 belgeden birkaç düzineye iner, yani ekrandaki her
# sayı değişir. Sessiz kalmak yerine uyarılır.
if [ ! -f "$KOK/data/demo.db" ]; then
  soluk "uyarı: data/demo.db yok — API fixture'lardan tohumlayacak (korpus küçük olur)"
  soluk "       üretmek için: .venv/bin/python -m scripts.build_demo_db"
fi

# ------------------------------------------------------------------- §2 model
#
# LLM=0 ise bu bölüm tümüyle atlanır: kural-only yol hiçbir ağırlığa bağlı
# değildir ve öyle kalmalıdır.

if [ "$LLM" = "1" ]; then
  command -v ollama >/dev/null 2>&1 || { kirmizi "ollama kurulu değil.
  çözüm: brew install ollama   —   ya da modelsiz koş: LLM=0 make baslat"; exit 1; }

  # Daemon çalışmıyorsa başlatılır. Kullanıcının kendi Ollama.app'i zaten
  # açıksa ona dokunulmaz: bu betik kendi başlatmadığı bir servisi sahiplenmez
  # (`durdur` de aynı ilkeyle yalnız kendi başlattığını kapatır).
  if ! curl -sf -m 3 "$OLLAMA_URL/api/tags" >/dev/null 2>&1; then
    soluk "ollama daemon kapalı — başlatılıyor"
    ayrik ollama serve > "$CALISMA/ollama.log" 2>&1 < /dev/null &
    echo $! > "$CALISMA/ollama.pid"
    for _ in $(seq 1 30); do
      curl -sf -m 2 "$OLLAMA_URL/api/tags" >/dev/null 2>&1 && break
      sleep 1
    done
    curl -sf -m 2 "$OLLAMA_URL/api/tags" >/dev/null 2>&1 || {
      kirmizi "ollama 30 sn'de açılmadı — bkz. $CALISMA/ollama.log"; exit 1; }
  fi

  # Model KURULU olmalı. Bilerek indirilmez: 4,7 GB'lık bir çekme, "başlat"
  # yazan bir komutun sessizce yapacağı iş değildir ve şartnamenin offline
  # koşum iddiasını da ağa bağımlı hale getirirdi.
  if ! ollama list 2>/dev/null | awk 'NR>1 {print $1}' | grep -qx "$OLLAMA_MODEL"; then
    kirmizi "model kurulu değil: $OLLAMA_MODEL
  çözüm: ollama pull $OLLAMA_MODEL   (~4,7 GB, ağ gerekir)
  ya da modelsiz koş: LLM=0 make baslat"
    exit 1
  fi
fi

# --------------------------------------------------------------- §3 port sahipliği
#
# Portu tutan süreç BİZİM süreçlerimizden biriyse (uvicorn src.api.main /
# next-server) kapatılır ve yerine tazesi kalkar — istenen davranış tam budur,
# çünkü oradaki süreç bayat koddan ve bayat ortam değişkenlerinden geliyordur.
#
# Başka bir uygulamaysa DOKUNULMAZ ve hata verilir. Ayrım şart: "portu boşalt"
# diye körlemesine `kill` atan bir başlatma betiği, ilgisiz bir işi öldürdüğü
# gün geri alınamaz bir hasar bırakır.
port_bosalt() {
  local port="$1" pid
  pid="$(lsof -nP -tiTCP:"$port" -sTCP:LISTEN 2>/dev/null | head -1)" || true
  [ -n "$pid" ] || return 0

  local komut; komut="$(ps -o command= -p "$pid" 2>/dev/null || true)"
  case "$komut" in
    *"src.api.main"*|*next-server*|*"next dev"*)
      soluk "port $port: eski Anatolia AI süreci (pid $pid) kapatılıyor"
      kill "$pid" 2>/dev/null || true
      for _ in $(seq 1 10); do
        lsof -nP -tiTCP:"$port" -sTCP:LISTEN >/dev/null 2>&1 || return 0
        sleep 1
      done
      kirmizi "port $port 10 sn'de boşalmadı (pid $pid)"; exit 1
      ;;
    *)
      kirmizi "port $port başka bir uygulamada — dokunulmadı:
  pid $pid: ${komut:0:100}
  çözüm: o uygulamayı kapatın, ya da başka port verin:
         API_PORT=8010 WEB_PORT=3010 make baslat"
      exit 1
      ;;
  esac
}

port_bosalt "$API_PORT"
port_bosalt "$WEB_PORT"

# ---------------------------------------------------------------------- §4 API
#
# Ortam değişkenleri burada TEK yerde toplanır. Dağınık oldukları sürece biri
# unutuluyordu; `LLM_BACKEND` unutulduğunda sistem hatasız açılır ve sadece
# sessizce kural-only olur — en pahalı sessiz arıza tipi.

API_ORTAM=(
  "DATABASE_PATH=data/demo.db"
  "BANKS_CONFIG=config/banks.yaml"
  "RAW_DIR=data/raw"
  "RAG_RETRIEVER=keyword"
)
if [ "$LLM" = "1" ]; then
  API_ORTAM+=(
    "LLM_BACKEND=ollama"
    "OLLAMA_URL=$OLLAMA_URL"
    "OLLAMA_MODEL=$OLLAMA_MODEL"
    # Model 30 dk bellekte kalsın: 4 dakikalık jüri sunumunun ortasında
    # yeniden yükleme (~6 sn) beklenmemeli.
    "OLLAMA_KEEP_ALIVE=30m"
    # Ollama varsayılanı 2048'dir ve 6 few-shot örneği + uzun kampanya metnini
    # SESSİZCE kırpar — sistem yönergesi baştan kaybolur (.env.example:70).
    "OLLAMA_NUM_CTX=8192"
  )
else
  API_ORTAM+=("LLM_BACKEND=")
fi

soluk "API başlatılıyor → :$API_PORT"
ayrik env "${API_ORTAM[@]}" "$PY" -m uvicorn src.api.main:app \
  --host 127.0.0.1 --port "$API_PORT" > "$CALISMA/api.log" 2>&1 < /dev/null &
echo $! > "$CALISMA/api.pid"

for _ in $(seq 1 60); do
  curl -sf -m 2 "http://127.0.0.1:$API_PORT/health" >/dev/null 2>&1 && break
  sleep 1
done
SAGLIK="$(curl -sf -m 5 "http://127.0.0.1:$API_PORT/health" 2>/dev/null || true)"
[ -n "$SAGLIK" ] || { kirmizi "API 60 sn'de açılmadı — bkz. $CALISMA/api.log"; exit 1; }

# --------------------------------------------------------------------- §5 panel
#
# `NEXT_PUBLIC_API_URL` API_PORT'tan TÜRETİLİR. Sabit yazılsaydı, alternatif
# portla koşan bir yığında panel sessizce yanlış API'ye bakardı — bu betiğin
# doğduğu arızanın ta kendisi.

# `npx next` DEĞİL, `node_modules/.bin/next`: npx araya kendi süreci girer ve
# pid dosyasına onun pid'si yazılır. `durdur` o pid'yi öldürdüğünde npx ölür,
# gerçek `next-server` yaşamaya devam eder — port tutulu kalır ve bir dahaki
# `baslat` "port başka bir uygulamada" der. Doğrudan çağırınca pid gerçek
# sunucununkidir.
soluk "panel başlatılıyor → :$WEB_PORT"
( cd "$KOK/web" && \
  ayrik env "NEXT_PUBLIC_API_URL=http://localhost:$API_PORT" \
    ./node_modules/.bin/next dev -p "$WEB_PORT" > "$CALISMA/web.log" 2>&1 < /dev/null &
  echo $! > "$CALISMA/web.pid" )

for _ in $(seq 1 60); do
  curl -sf -m 2 -o /dev/null "http://127.0.0.1:$WEB_PORT/" 2>/dev/null && break
  sleep 1
done
curl -sf -m 5 -o /dev/null "http://127.0.0.1:$WEB_PORT/" 2>/dev/null || {
  kirmizi "panel 60 sn'de açılmadı — bkz. $CALISMA/web.log"; exit 1; }

# ------------------------------------------------------------------ §6 ölçülmüş durum
#
# Buradaki satırlar İDDİA değil ÖLÇÜMDÜR: `llm` alanı API'nin kendi
# `/health`inden, korpus sayıları `/stats`ten okunur. "Yerel model açık" yazan
# bir başlatma çıktısı, modelin gerçekten yüklendiğini göstermek zorundadır —
# yoksa ekrandaki her sayının kanıtını isteyen bir sistemde ilk yalanı kendi
# başlatma betiği söylemiş olur.
#
# Panelin gördüğü yol AYRICA sınanır (`/api/health` — Next rewrite proxy'si):
# API'nin ayakta olması, panelin ona ULAŞTIĞI anlamına gelmez.

PROXY="$(curl -sf -m 5 "http://127.0.0.1:$WEB_PORT/api/health" 2>/dev/null || true)"
LLM_DURUM="$(printf '%s' "$SAGLIK" | "$PY" -c 'import sys,json;print("açık" if json.load(sys.stdin).get("llm") else "kapalı")' 2>/dev/null || echo "?")"
DEPO="$(printf '%s' "$SAGLIK" | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("backend","?"))' 2>/dev/null || echo "?")"
# f-string KULLANILMIYOR: kabuk tek tırnağı içinde `\"` kaçışı Python'a bozuk
# geliyor ve satır sessizce "okunamadı"ya düşüyordu. Binlik ayracı Türkçe
# biçimde (1.782) — panelin gösterdiği sayıyla aynı görünsün.
KORPUS="$(curl -sf -m 10 "http://127.0.0.1:$API_PORT/stats" 2>/dev/null | "$PY" -c \
  'import sys,json
k = json.load(sys.stdin)["korpus"]
b = lambda n: format(n, ",").replace(",", ".")
print(b(k["campaigns"]), "belge ·", b(k["banks"]), "banka ·", b(k["fields"]), "alan")' 2>/dev/null || echo "okunamadı")"

echo
yesil "Anatolia AI hazır"
echo "  panel        http://localhost:$WEB_PORT"
echo "  API          http://localhost:$API_PORT        (dokümanlar: /docs)"
echo "  yerel model  $LLM_DURUM$([ "$LLM_DURUM" = "açık" ] && echo "  ($OLLAMA_MODEL)")"
echo "  depo         $DEPO"
echo "  korpus       $KORPUS"
if [ -n "$PROXY" ]; then
  echo "  panel→API    ulaşıyor"
else
  kirmizi "  panel→API    ULAŞMIYOR — panel veri çekemez (bkz. $CALISMA/web.log)"
fi
echo
soluk "  loglar: $CALISMA/{api,web}.log     durdurmak için: make durdur"
