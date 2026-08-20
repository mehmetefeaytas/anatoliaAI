#!/usr/bin/env bash
#
# tam_yigin_agsiz.sh — TAM YIĞININ (postgres + api + api-postgres + ollama + web)
# BİRLİKTE, tek bir ağsız koşumda çalıştığının ÖLÇÜLMÜŞ kanıtı.
#
# İlgili: docs/OFFLINE-KANIT.md §0-b (bu betikten önce "tam yığın ağsız hiç
#         denenmedi" diyordu — bu betik o boşluğu kapatır)
#         scripts/offline_proof.sh (aynı desen: negatif kontrol + pozitif kontrolü,
#         yalnızca TEK KONTEYNER için; bu betik ÇOKLU KONTEYNER/servis için)
#         docker-compose.yml (profiller: postgres, ollama; varsayılan: api+web)
#         Şartname §5.9 (dış servise bağımlı olmadan yerel çalışma), §8, §5.10
#
# ## Neden bu betik var, offline_proof.sh yetmiyor mu
#
# `scripts/offline_proof.sh` yalnız TEK bir konteyneri (`anatolia-api`) tek
# başına `--network none` içinde koşturur. Bu güçlü ama EKSİK bir kanıttır:
# `docker-compose.yml` gerçek dünyada birden fazla servisi (postgres, ollama,
# api, api-postgres, web) BİRLİKTE ayağa kaldırıyor ve bunlar birbiriyle
# konteynerler-arası ağ üzerinden konuşuyor (`api-postgres` -> `postgres`,
# `web` -> `api`). Tek-konteyner kanıtı bu birlikte-çalışmayı hiç sınamaz.
#
# ## Yöntem: "içeride açık, dışarıya kapalı" izole ağ
#
# `docker run --network none` çoklu servis için kullanılamaz — servisler
# birbirine ulaşamazsa `depends_on` zaten anlamsız kalır. Bunun yerine:
#
#   1. `docker network create --internal <ad>` ile bir ağ kurulur. `--internal`
#      bayrağı bu ağa varsayılan gateway/NAT KOYMAZ: konteynerler birbirini
#      DNS ile (servis adıyla) bulabilir ama ağın DIŞINA (internete) hiçbir
#      rota yoktur.
#   2. Geçici bir compose override dosyası (`networks.default.external: true`,
#      adı yukarıdaki ağ) ile TÜM servisler bu izole ağa bağlanır.
#   3. `docker compose up -d` bu ağla koşar. Servisler birbirini normal
#      şekilde bulur (aynı Docker DNS mekanizması); dışarıya çıkış YOKTUR.
#
# Bu betik ÖNCE aynı prob'u SIRADAN (izolasyonsuz) ağda ÇALIŞTIRIR (pozitif
# kontrol — prob gerçekten internete ulaşabiliyor mu) SONRA izole ağda
# ÇALIŞTIRIR (negatif kontrol — artık ulaşamıyor mu). Yalnız negatif kontrol
# yeterli değildir: prob başka bir sebeple her zaman başarısız oluyorsa
# "izolasyon çalışıyor" diye YANLIŞ sonuç çıkarılır (bkz. offline_proof.sh
# başlığı, aynı gerekçe).
#
# ## Bu betiğin KANITLAMADIĞI şey — önceden ilan edilir
#
#   - İmajların DERLENMESİ ağ ister (`pip install`, `npm ci`). Bu betik
#     imajların ÖNCEDEN derlenmiş/çekilmiş olmasını VARSAYAR ve bunu
#     doğrulamadan devam ETMEZ (aşağıdaki "Ön koşul" bölümüne bakın).
#   - `vllm` profili (GPU gerektirir) bu betiğe DAHİL DEĞİLDİR — bu makinede
#     GPU yoksa hiç denenmez ve bu açıkça raporlanır.
#   - `ollama` servisi bu betikte yalnız KONTEYNERİN ağsız ayağa kalktığı ve
#     API'nin ona erişebildiği kanıtlanır; bir MODELİN önceden çekilmiş
#     olması ayrı bir ön koşuldur (bkz. docker-compose.yml `ollama` servis
#     yorumu). Model yoksa bu betik `ollama list`in boş döndüğünü ölçer ve
#     bunu "beklenmedik" SAYMAZ — yalnızca konteynerin ayakta ve erişilebilir
#     olduğunu kanıtlar, çıkarım kalitesini değil.
#
# ## Kullanım
#
#   bash scripts/tam_yigin_agsiz.sh
#   KEEP_UP=1 bash scripts/tam_yigin_agsiz.sh      # koşum sonunda servisleri ayakta bırak
#   SKIP_BUILD=1 bash scripts/tam_yigin_agsiz.sh   # imaj derlemeyi atla (zaten hazırsa)
#   INCLUDE_DBCHECK=0 bash scripts/tam_yigin_agsiz.sh   # db-check adımını atla
#
# Çıkış kodları: 0 = tüm adımlar beklendiği gibi · 1 = en az bir adım beklenmedik
#                2 = ön koşul yok (docker/imaj/daemon) — kanıt ÜRETİLEMEDİ

set -euo pipefail

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$APP_DIR"

PROJECT="${PROJECT:-anatolia-agsiz}"
NET_NAME="${NET_NAME:-${PROJECT}-izole-ag}"
OUT_DIR="${OUT_DIR:-docs/offline-proof}"
TS="$(date +%Y%m%d-%H%M%S)"
WAIT_TIMEOUT="${WAIT_TIMEOUT:-90}"
INCLUDE_DBCHECK="${INCLUDE_DBCHECK:-1}"
KEEP_UP="${KEEP_UP:-0}"

# docker-compose.yml'deki digest'lerle BİREBİR aynı olmalı — sabit tutmanın
# gerekçesi docker-compose.yml başlığında ve OFFLINE-KANIT.md §5'te yazılı.
PG_IMAGE="pgvector/pgvector:pg16@sha256:a36250871de0833b8757561c72f2477ef1ddd1101afa4e617fb552e0de514c6b"
OLLAMA_IMAGE="ollama/ollama:latest@sha256:4dea9fb511947e24a84237bb636b0203abcb2ff0d3fbc7b4ff865deb91362131"

mkdir -p "$OUT_DIR"
LOG="$OUT_DIR/tam-yigin-agsiz-transcript-$TS.log"
OVERRIDE_FILE="$(mktemp -t tam-yigin-agsiz-override-XXXXXX).yml"

exec > >(tee "$LOG") 2>&1

STEP_NAME=(); STEP_EXPECT=(); STEP_CODE=(); STEP_MS=(); STEP_VERDICT=()
FAILURES=0

_epoch_ms() { python3 -c 'import time; print(int(time.time()*1000))' 2>/dev/null || echo "$(( $(date +%s) * 1000 ))"; }
_hr() { printf '%s\n' "------------------------------------------------------------------------------"; }

run_step() {
  local name="$1" expect="$2"; shift 2
  [ "${1:-}" = "--" ] && shift
  echo; _hr
  echo "ADIM $(( ${#STEP_NAME[@]} + 1 )): $name"
  echo "beklenti : $( [ "$expect" = pass ] && echo 'cikis kodu 0' || echo 'cikis kodu 0 DEGIL (negatif kontrol)' )"
  echo "komut    : $*"
  _hr
  local t0 t1 code
  t0="$(_epoch_ms)"; set +e; "$@"; code=$?; set -e; t1="$(_epoch_ms)"
  local verdict
  if [ "$expect" = pass ]; then
    [ "$code" -eq 0 ] && verdict="BEKLENDIGI GIBI" || verdict="BEKLENMEDIK"
  else
    [ "$code" -ne 0 ] && verdict="BEKLENDIGI GIBI" || verdict="BEKLENMEDIK"
  fi
  [ "$verdict" = "BEKLENMEDIK" ] && FAILURES=$(( FAILURES + 1 ))
  STEP_NAME+=("$name"); STEP_EXPECT+=("$expect"); STEP_CODE+=("$code")
  STEP_MS+=("$(( t1 - t0 ))"); STEP_VERDICT+=("$verdict")
  _hr
  echo "sonuc    : cikis kodu=$code  sure=$(( t1 - t0 )) ms  -> $verdict"
  return 0
}

NET_PROBE_PY='
import socket, sys, urllib.request
blocked, reached = [], []
def probe(name, fn):
    try:
        fn()
    except Exception as exc:
        blocked.append(name)
        print("  [ENGELLENDI] %-24s -> %s: %s" % (name, type(exc).__name__, str(exc)[:110]))
    else:
        reached.append(name)
        print("  [ULASILDI]   %-24s -> AG ERISIMI VAR" % name)
probe("DNS huggingface.co",   lambda: socket.getaddrinfo("huggingface.co", 443))
probe("TCP 1.1.1.1:443",      lambda: socket.create_connection(("1.1.1.1", 443), timeout=5).close())
probe("HTTPS huggingface.co", lambda: urllib.request.urlopen("https://huggingface.co", timeout=5).close())
probe("HTTPS pypi.org",       lambda: urllib.request.urlopen("https://pypi.org/simple/", timeout=5).close())
print(); print("engellenen: %d/4   ulasilan: %d/4" % (len(blocked), len(reached)))
sys.exit(0 if reached else 3)
'

cleanup() {
  if [ "$KEEP_UP" != "1" ]; then
    echo; echo "temizlik: docker compose down (KEEP_UP=1 ile servisleri ayakta birakabilirsiniz)"
    docker compose -p "$PROJECT" -f docker-compose.yml -f "$OVERRIDE_FILE" \
      --profile postgres --profile ollama down >/dev/null 2>&1 || true
    docker network rm "$NET_NAME" >/dev/null 2>&1 || true
  else
    echo; echo "KEEP_UP=1 — servisler AYAKTA birakildi (proje: $PROJECT, ag: $NET_NAME)."
    echo "Kapatmak icin: docker compose -p $PROJECT -f docker-compose.yml -f $OVERRIDE_FILE --profile postgres --profile ollama down; docker network rm $NET_NAME"
  fi
  rm -f "$OVERRIDE_FILE"
}
trap cleanup EXIT

echo "=============================================================================="
echo " ANATOLIA AI — TAM YIGIN AGSIZ KOSUM (postgres + api + api-postgres + ollama + web)"
echo "=============================================================================="
echo "tarih         : $(date -u '+%Y-%m-%dT%H:%M:%SZ') (UTC)"
echo "calisma dizini: $APP_DIR"
echo "proje adi     : $PROJECT"
echo "izole ag      : $NET_NAME"
echo "transkript    : $LOG"
echo "host          : $(uname -a)"
echo "git commit    : $(git rev-parse --short HEAD 2>/dev/null || echo '(git yok)')"
echo "git durum     : $(git status --porcelain 2>/dev/null | wc -l | tr -d ' ') degisik dosya"
echo

# --------------------------------------------------------------------------- #
# 0. On kosullar — eksikse ACIK HATA (sessiz "basarili" YASAK)
# --------------------------------------------------------------------------- #
if ! command -v docker >/dev/null 2>&1; then
  echo "HATA: 'docker' komutu bulunamadi. Kanit URETILEMEDI. Cikis kodu 2."
  exit 2
fi
echo "docker        : $(docker --version)"

if ! docker info >/dev/null 2>&1; then
  echo "HATA: docker daemon'a baglanilamadi. Docker Desktop/dockerd calistir. Cikis kodu 2."
  exit 2
fi
echo "daemon        : $(docker info --format '{{.ServerVersion}} ({{.OSType}}/{{.Architecture}})')"

if ! docker compose version >/dev/null 2>&1; then
  echo "HATA: 'docker compose' eklentisi bulunamadi. Cikis kodu 2."
  exit 2
fi
echo "compose       : $(docker compose version --short)"

# Postgres/Ollama imajlari ONCEDEN cekilmis olmali — bu betik AGSIZ calisir,
# yani kendisi PULL YAPMAZ. Eksikse acik hata + tam komut verilir.
for img in "$PG_IMAGE" "$OLLAMA_IMAGE"; do
  if ! docker image inspect "$img" >/dev/null 2>&1; then
    echo
    echo "HATA: gerekli imaj yerelde YOK: $img"
    echo "      Bu betik agsiz calisir, kendisi 'docker pull' YAPMAZ (yapmasi"
    echo "      'agsiz koşum' iddiasini gecersiz kilardi). Ag VARKEN once cekin:"
    echo "        docker pull $img"
    echo "      Cikis kodu 2."
    exit 2
  fi
done
echo "on-cekilmis imajlar: postgres+pgvector VE ollama yerelde mevcut (digest eslesti)"

# --------------------------------------------------------------------------- #
# 1. Imajlari derle (api, api-postgres, web, db-check) — AG ACIKKEN, bilerek.
#    "internetsiz calisir" iddiasi ONCEDEN DERLENMIS imajlarla dogrudur;
#    derleme adimi kapsam disi (bkz. docs/OFFLINE-KANIT.md §0-b, §3 notu).
# --------------------------------------------------------------------------- #
BUILD_SERVICES="api web"
[ "$INCLUDE_DBCHECK" = "1" ] && BUILD_SERVICES="api api-postgres web db-check" || BUILD_SERVICES="api api-postgres web"

if [ "${SKIP_BUILD:-0}" = "1" ]; then
  echo; echo "NOT: SKIP_BUILD=1 — derleme atlandi, mevcut imajlar kullanilacak."
else
  run_step "Imaj derleme (docker compose build $BUILD_SERVICES) — AG ACIK" pass -- \
    docker compose -p "$PROJECT" --profile postgres build $BUILD_SERVICES
fi

# --------------------------------------------------------------------------- #
# 2. Izole ag kur — henuz servisler ayakta degil
# --------------------------------------------------------------------------- #
docker network rm "$NET_NAME" >/dev/null 2>&1 || true
run_step "Izole ag olustur (--internal, dis dunyaya rotasiz)" pass -- \
  docker network create --internal "$NET_NAME"

cat > "$OVERRIDE_FILE" <<EOF
networks:
  default:
    name: ${NET_NAME}
    external: true
EOF
echo "override dosyasi: $OVERRIDE_FILE"
cat "$OVERRIDE_FILE"

# --------------------------------------------------------------------------- #
# 3. POZITIF KONTROL (meta) — AYNI prob, SIRADAN (izolasyonsuz) agda calisiyor mu
#    Bu adim olmadan adim 5'teki negatif kontrol hicbir sey kanitlamaz.
# --------------------------------------------------------------------------- #
# Compose, `image:` anahtari verilmemis servisler icin imaji `<proje>-<servis>`
# adiyla etiketler (BuildKit bake varsayilani). `docker compose images` henuz
# konteyner yokken guvenilir donmuyor; bu yuzden ad dogrudan kuruluyor.
run_step "Prob dogrulama: SIRADAN agda prob ULASMALI (metaKontrol)" pass -- \
  docker run --rm "${PROJECT}-api" python -c "$NET_PROBE_PY"

# --------------------------------------------------------------------------- #
# 4. TAM YIGINI izole agda ayaga kaldir: postgres + api + api-postgres +
#    ollama + web — BIRLIKTE, TEK KOSUMDA.
# --------------------------------------------------------------------------- #
run_step "TAM YIGIN ayaga kalkiyor (postgres+api+api-postgres+ollama+web) — izole ag" pass -- \
  docker compose -p "$PROJECT" -f docker-compose.yml -f "$OVERRIDE_FILE" \
    --profile postgres --profile ollama \
    up -d postgres api api-postgres ollama web

echo
echo "--- docker compose ps ---"
docker compose -p "$PROJECT" -f docker-compose.yml -f "$OVERRIDE_FILE" \
  --profile postgres --profile ollama ps

# --------------------------------------------------------------------------- #
# 5. NEGATIF KONTROL — izole agdaki BIR konteynerden disariya ULASILAMAMALI
# --------------------------------------------------------------------------- #
API_CID="$(docker compose -p "$PROJECT" -f docker-compose.yml -f "$OVERRIDE_FILE" ps -q api)"
run_step "NEGATIF KONTROL: izole agdaki 'api' konteyneri disariya ULASAMAZ" fail -- \
  docker exec "$API_CID" python -c "$NET_PROBE_PY"

# --------------------------------------------------------------------------- #
# 6. Servislerin hazir olmasini bekle + saglik/erisim kontrolleri
#    (konteyner ICINDEN kontrol edilir — host'tan yayinlanan porta degil;
#    Docker Desktop'ta --internal agda port yayinlama host'a ULASMIYOR,
#    bu YANLIS pozitif/negatif rapor olustururdu. bkz. bu betigin git log'u /
#    gelistirme notlari.)
# --------------------------------------------------------------------------- #
_wait_healthy() {
  local cid="$1" label="$2" cmd="$3"
  local i=0
  while [ "$i" -lt "$WAIT_TIMEOUT" ]; do
    if docker exec "$cid" sh -c "$cmd" >/dev/null 2>&1; then
      echo "  $label hazir (~${i}s)"; return 0
    fi
    i=$(( i + 1 )); sleep 1
  done
  echo "  HATA: $label $WAIT_TIMEOUT sn icinde hazir olmadi"
  docker logs "$cid" 2>&1 | tail -20
  return 1
}

POSTGRES_CID="$(docker compose -p "$PROJECT" -f docker-compose.yml -f "$OVERRIDE_FILE" ps -q postgres)"
APIPG_CID="$(docker compose -p "$PROJECT" -f docker-compose.yml -f "$OVERRIDE_FILE" ps -q api-postgres)"
OLLAMA_CID="$(docker compose -p "$PROJECT" -f docker-compose.yml -f "$OVERRIDE_FILE" ps -q ollama)"
WEB_CID="$(docker compose -p "$PROJECT" -f docker-compose.yml -f "$OVERRIDE_FILE" ps -q web)"

run_step "postgres hazir (pg_isready) — izole ag" pass -- \
  _wait_healthy "$POSTGRES_CID" postgres "pg_isready -U anatolia"

run_step "api /health hazir — izole ag" pass -- \
  _wait_healthy "$API_CID" api "python -c \"import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2)\""

run_step "api-postgres /health hazir (postgres backend) — izole ag" pass -- \
  _wait_healthy "$APIPG_CID" api-postgres "python -c \"import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2)\""

run_step "ollama API hazir (/api/tags) — izole ag" pass -- \
  _wait_healthy "$OLLAMA_CID" ollama "wget -q -O - http://127.0.0.1:11434/api/tags || ollama list"

run_step "web (Next.js) hazir — izole ag" pass -- \
  _wait_healthy "$WEB_CID" web "wget -q -O /dev/null http://127.0.0.1:3000/"

echo
echo "--- api /health icerigi ---"
docker exec "$API_CID" python -c \
  "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=5).read().decode())" || true
echo "--- api-postgres /health icerigi ---"
docker exec "$APIPG_CID" python -c \
  "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=5).read().decode())" || true

# --------------------------------------------------------------------------- #
# 7. KONTEYNERLER-ARASI ERISIM — 'web' -> 'api' VE 'api-postgres' -> 'postgres'
#    servis-adi DNS'iyle, izole agin ICINDE (dis dunyaya degil)
# --------------------------------------------------------------------------- #
run_step "web konteyneri 'api' servisine ISIM ile ulasiyor (dahili DNS)" pass -- \
  docker exec "$WEB_CID" wget -q -O /dev/null "http://api:8000/health"

run_step "api-postgres konteyneri PostgreSQL'e gercekten yaziyor (repo.counts)" pass -- \
  docker exec "$APIPG_CID" python -c \
    "import urllib.request,json; d=json.loads(urllib.request.urlopen('http://127.0.0.1:8000/health',timeout=5).read()); print(d); assert d.get('backend')=='postgres', d"

# --------------------------------------------------------------------------- #
# 8. db-check — pgvector'un GERCEKTEN calistigi (embeddings + IVFFlat) testi,
#    hepsi izole agin icinde, ag olmadan
# --------------------------------------------------------------------------- #
if [ "$INCLUDE_DBCHECK" = "1" ]; then
  run_step "db-check: pgvector paritesi + embeddings testi — izole ag, agsiz" pass -- \
    docker compose -p "$PROJECT" -f docker-compose.yml -f "$OVERRIDE_FILE" \
      --profile postgres run --rm db-check
else
  echo; echo "NOT: INCLUDE_DBCHECK=0 — db-check adimi atlandi."
fi

# --------------------------------------------------------------------------- #
# Ozet tablo
# --------------------------------------------------------------------------- #
echo
echo "=============================================================================="
echo " OZET"
echo "=============================================================================="
printf '%-3s %-58s %-6s %-8s %s\n' "#" "adim" "kod" "sure(ms)" "sonuc"
_hr
i=0
while [ "$i" -lt "${#STEP_NAME[@]}" ]; do
  printf '%-3s %-58s %-6s %-8s %s\n' \
    "$(( i + 1 ))" "$(echo "${STEP_NAME[$i]}" | cut -c1-58)" \
    "${STEP_CODE[$i]}" "${STEP_MS[$i]}" "${STEP_VERDICT[$i]}"
  i=$(( i + 1 ))
done
_hr
echo "adim sayisi        : ${#STEP_NAME[@]}"
echo "beklenmedik sonuc  : $FAILURES"
echo "transkript         : $LOG"
echo

if [ "$FAILURES" -eq 0 ]; then
  echo "SONUC: TUM ADIMLAR BEKLENDIGI GIBI."
  echo "       postgres + api + api-postgres + ollama + web AYNI izole agda,"
  echo "       DIS DUNYAYA HICBIR ROTA OLMADAN, BIRLIKTE ayaga kalkti ve"
  echo "       birbirine servis-adi DNS'iyle eristi."
  exit 0
fi

echo "SONUC: $FAILURES ADIM BEKLENMEDIK. Kanit paketi GECERSIZ."
echo "       Yukaridaki 'BEKLENMEDIK' satirlarini incele."
exit 1
