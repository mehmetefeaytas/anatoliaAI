#!/usr/bin/env bash
#
# offline_proof.sh — Anatolia AI'ın internetsiz çalıştığının ÖLÇÜLMÜŞ kanıtı.
#
# İlgili: docs/OFFLINE-KANIT.md (bu betiğin ürettiği transkriptin işlendiği belge)
#         ../decisions/on-premise-calistirilabilir-mimari.md
#         Şartname §5.9 (dış servise bağımlı olmadan yerel çalışma), §8 (ücretsiz)
#         app/CLAUDE.md §20 ("İnternetsiz `docker-compose up` çalışıyor")
#
# ## Neden bu betik var
#
# "Offline çalışır" bir İDDİA'dır; `docker run --network none` içinde koşan bir
# test paketi KANIT'tır. Rubrikte On-Prem Uygulanabilirlik %20 ve bugüne kadar
# elimizde tek bir ölçülmüş kanıt yoktu.
#
# ## En önemli parça: NEGATİF KONTROL ve onun POZİTİF KONTROLÜ
#
# Pozitif test ("testler ağsız geçti") tek başına zayıftır: testler ağı hiç
# denemiyor olabilir. İkna edici olan, ağ erişimi *deneyen* bir çağrının
# `--network none` içinde BAŞARISIZ olduğunu göstermektir (adım 3).
#
# Ama bu da yeterli değil: prob başka bir sebeple (yazım hatası, eksik ikili,
# yanlış hostname) her koşulda başarısız oluyorsa, "izolasyon çalışıyor" diye
# yanlış bir sonuç çıkarırız. O yüzden AYNI prob önce ağ AÇIKKEN koşturulur ve
# BAŞARILI olması beklenir (adım 2). Bu projede daha önce "duman testi bağlantı
# hatasını BAŞARILI raporladı" sınıfından bir hata yaşandı; adım 2 tam olarak
# o hata sınıfını yakalamak için var.
#
# Sözleşme: hiçbir adım sessizce atlanmaz. docker yoksa betik AÇIK HATA verip
# çıkar (exit 2) — asla "başarılı" demez.
#
# Kullanım:
#   bash scripts/offline_proof.sh
#   IMAGE=anatolia-api:test bash scripts/offline_proof.sh
#   SKIP_BUILD=1 bash scripts/offline_proof.sh      # imaj hazırsa derlemeyi atla
#
# Çıkış kodları: 0 = tüm adımlar beklendiği gibi · 1 = en az bir adım beklenmedik
#                2 = ön koşul yok (docker/daemon) — kanıt ÜRETİLEMEDİ

set -euo pipefail

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$APP_DIR"

IMAGE="${IMAGE:-anatolia-api:offline-proof}"
OUT_DIR="${OUT_DIR:-docs/offline-proof}"
GOLD="${GOLD:-data/gold/gold.sample.json}"
BENCH_ITERATIONS="${BENCH_ITERATIONS:-3}"
TS="$(date +%Y%m%d-%H%M%S)"

mkdir -p "$OUT_DIR"
LOG="$OUT_DIR/transcript-$TS.log"

# Tüm çıktı hem ekrana hem transkript dosyasına — kanıt arşivlenebilir olmalı.
exec > >(tee "$LOG") 2>&1

# --------------------------------------------------------------------------- #
# Adım defteri (bash 3.2 uyumlu: yalnızca indeksli diziler)
# --------------------------------------------------------------------------- #
STEP_NAME=()
STEP_EXPECT=()
STEP_CODE=()
STEP_MS=()
STEP_VERDICT=()
FAILURES=0

_epoch_ms() {
  if command -v python3 >/dev/null 2>&1; then
    python3 -c 'import time; print(int(time.time()*1000))'
  else
    echo "$(( $(date +%s) * 1000 ))"
  fi
}

_hr() { printf '%s\n' "------------------------------------------------------------------------------"; }

# run_step <ad> <pass|fail> -- <komut...>
#   pass = komutun 0 dönmesi BEKLENİR
#   fail = komutun 0 DIŞINDA dönmesi BEKLENİR (negatif kontrol)
run_step() {
  local name="$1" expect="$2"; shift 2
  [ "${1:-}" = "--" ] && shift

  echo
  _hr
  echo "ADIM $(( ${#STEP_NAME[@]} + 1 )): $name"
  echo "beklenti : $( [ "$expect" = pass ] && echo 'cikis kodu 0' || echo 'cikis kodu 0 DEGIL (negatif kontrol)' )"
  echo "komut    : $*"
  _hr

  local t0 t1 code
  t0="$(_epoch_ms)"
  set +e
  "$@"
  code=$?
  set -e
  t1="$(_epoch_ms)"

  local verdict
  if [ "$expect" = pass ]; then
    [ "$code" -eq 0 ] && verdict="BEKLENDIGI GIBI" || verdict="BEKLENMEDIK"
  else
    [ "$code" -ne 0 ] && verdict="BEKLENDIGI GIBI" || verdict="BEKLENMEDIK"
  fi
  [ "$verdict" = "BEKLENMEDIK" ] && FAILURES=$(( FAILURES + 1 ))

  STEP_NAME+=("$name")
  STEP_EXPECT+=("$expect")
  STEP_CODE+=("$code")
  STEP_MS+=("$(( t1 - t0 ))")
  STEP_VERDICT+=("$verdict")

  _hr
  echo "sonuc    : cikis kodu=$code  sure=$(( t1 - t0 )) ms  -> $verdict"
  if [ "$verdict" = "BEKLENMEDIK" ] && [ "$expect" = fail ]; then
    echo
    echo "!!! UYARI: AG IZOLASYONU CALISMIYOR — '--network none' icinden dis"
    echo "!!! dunyaya ulasilabildi. Bu kanit paketi GECERSIZ; once bunu duzelt."
  fi
  return 0
}

# --------------------------------------------------------------------------- #
# Negatif/pozitif kontrol probu — saf stdlib (kurulu olmayan `curl`'e bagli degil)
#
# Cikis kodu sozlesmesi:
#   0 = EN AZ BIR baglanti KURULDU  -> ag erisimi VAR
#   3 = HICBIR baglanti kurulamadi  -> ag erisimi YOK
# --------------------------------------------------------------------------- #
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

print()
print("engellenen: %d/4   ulasilan: %d/4" % (len(blocked), len(reached)))
sys.exit(0 if reached else 3)
'

# --------------------------------------------------------------------------- #
# 0. Ön koşullar — eksikse AÇIK HATA (sessiz "basarili" YASAK)
# --------------------------------------------------------------------------- #
echo "=============================================================================="
echo " ANATOLIA AI — OFFLINE KANIT KOSUSU"
echo "=============================================================================="
echo "tarih        : $(date -u '+%Y-%m-%dT%H:%M:%SZ') (UTC)"
echo "calisma dizini: $APP_DIR"
echo "imaj         : $IMAGE"
echo "transkript   : $LOG"
echo "host         : $(uname -a)"
echo "git commit   : $(git rev-parse --short HEAD 2>/dev/null || echo '(git yok)')"
echo "git durum    : $(git status --porcelain 2>/dev/null | wc -l | tr -d ' ') degisik dosya"
echo

if ! command -v docker >/dev/null 2>&1; then
  echo "HATA: 'docker' komutu bulunamadi."
  echo "      Bu betik Docker olmadan kanit URETEMEZ. docs/OFFLINE-KANIT.md'deki"
  echo "      ilgili bolumler 'olculmedi' olarak isaretli kalmalidir."
  echo "      Betik BASARILI raporlamiyor — cikis kodu 2."
  exit 2
fi
echo "docker       : $(docker --version)"

if ! docker info >/dev/null 2>&1; then
  echo
  echo "HATA: docker daemon'a baglanilamadi (docker CLI var, sunucu yok)."
  echo "      Docker Desktop / dockerd calistir, sonra tekrar dene."
  echo "      Betik BASARILI raporlamiyor — cikis kodu 2."
  exit 2
fi
echo "daemon       : $(docker info --format '{{.ServerVersion}} ({{.OSType}}/{{.Architecture}})')"

if [ ! -f "$GOLD" ]; then
  echo
  echo "HATA: gold dosyasi bulunamadi: $GOLD"
  echo "      GOLD=<yol> ile ver veya gold seti uret. Cikis kodu 2."
  exit 2
fi
echo "gold dosyasi : $GOLD"

# --------------------------------------------------------------------------- #
# 1. İmajı derle
# --------------------------------------------------------------------------- #
if [ "${SKIP_BUILD:-0}" = "1" ]; then
  echo
  echo "NOT: SKIP_BUILD=1 — derleme atlandi, mevcut '$IMAGE' kullanilacak."
  if ! docker image inspect "$IMAGE" >/dev/null 2>&1; then
    echo "HATA: SKIP_BUILD=1 verildi ama '$IMAGE' imaji yok. Cikis kodu 2."
    exit 2
  fi
else
  run_step "Imaj derleme (docker build -f Dockerfile.api)" pass -- \
    docker build --progress=plain -f Dockerfile.api -t "$IMAGE" .
fi

# `--network none` ile calistirma kisayolu. Cikti dizini bind-mount edilir;
# bind-mount ag gerektirmez, izolasyonu bozmaz.
DRUN=(docker run --rm --network none
      -v "$APP_DIR/$OUT_DIR:/out"
      -e LLM_BACKEND=
      -e PYTHONDONTWRITEBYTECODE=1
      "$IMAGE")

# --------------------------------------------------------------------------- #
# 2. NEGATİF KONTROLÜN POZİTİF KONTROLÜ — ağ AÇIK, prob ÇALIŞIYOR olmalı
#    Bu adım olmadan adım 3 hiçbir şey kanıtlamaz.
# --------------------------------------------------------------------------- #
run_step "Prob dogrulama: ag ACIK iken prob ULASMALI (metaKontrol)" pass -- \
  docker run --rm "$IMAGE" python -c "$NET_PROBE_PY"

# --------------------------------------------------------------------------- #
# 3. NEGATİF KONTROL — `--network none` içinde ağa ULAŞILAMAMALI
# --------------------------------------------------------------------------- #
run_step "NEGATIF KONTROL: --network none icinde ag ERISILEMEZ olmali" fail -- \
  "${DRUN[@]}" python -c "$NET_PROBE_PY"

# --------------------------------------------------------------------------- #
# 4. curl ile ikinci negatif kontrol (yalnızca curl imajda varsa)
#    curl yoksa "command not found" da 0-dışı döner ve YANLIŞ kanıt olur;
#    o yüzden varlığı AYRI olarak sınanır.
# --------------------------------------------------------------------------- #
if docker run --rm --network none "$IMAGE" sh -c 'command -v curl >/dev/null 2>&1'; then
  run_step "NEGATIF KONTROL (curl): huggingface.co basarisiz olmali" fail -- \
    "${DRUN[@]}" curl -sS --max-time 5 https://huggingface.co
else
  echo
  _hr
  echo "NOT: imajda 'curl' YOK (python:3.11-slim taban imaji curl icermez)."
  echo "     Bu yuzden 'curl -sS --max-time 5 https://huggingface.co' adimi"
  echo "     KOSTURULMADI. Kosturulsa 'command not found' da 0-disi donerdi ve"
  echo "     ag izolasyonunun kaniti SANILIRDI — bu tam olarak kacinilan hata."
  echo "     Ayni is adim 3'teki stdlib probu ile, bagimliliksiz yapiliyor."
  _hr
fi

# --------------------------------------------------------------------------- #
# 5-8. Gerçek işi `--network none` içinde koştur
# --------------------------------------------------------------------------- #
# Test sayisi kasitli olarak YAZILMIYOR: paket buyudukce sabit bir sayi
# ("345 test") sessizce yalan olur. Gercek sayi transkriptteki "Ran N tests"
# satirindadir.
run_step "Test paketi (tum unittest'ler) — --network none" pass -- \
  "${DRUN[@]}" python -m unittest discover -s tests -v

run_step "Degismez denetimi (eval.properties) — --network none" pass -- \
  "${DRUN[@]}" python -m eval.properties --raw-dir data/raw

run_step "Degerlendirme (eval.run_eval) — --network none" pass -- \
  "${DRUN[@]}" python -m eval.run_eval --gold "$GOLD"

run_step "Ablasyon (eval.ablation) — --network none" pass -- \
  "${DRUN[@]}" python -m eval.ablation --gold "$GOLD"

# --------------------------------------------------------------------------- #
# 9. Gecikme ölçümü — konteyner içinde, ağsız
# --------------------------------------------------------------------------- #
run_step "Gecikme olcumu (scripts.latency_bench) — --network none" pass -- \
  "${DRUN[@]}" python -m scripts.latency_bench --recursive \
      --iterations "$BENCH_ITERATIONS" --json "/out/latency-$TS.json"

# --------------------------------------------------------------------------- #
# 10. Offline ortam değişkenleri gerçekten set mi
# --------------------------------------------------------------------------- #
run_step "Offline ortam degiskenleri (HF_HUB_OFFLINE vb.)" pass -- \
  "${DRUN[@]}" sh -c 'env | grep -E "OFFLINE|TELEMETRY|UPDATE_CHECK" | sort'

# --------------------------------------------------------------------------- #
# 11-12. trafilatura (GPLv3+ riski) teslim imajında YOK kanıtı
#    bkz. docs/model-license-audit.md §2 — karar: requirements-api.txt'e alinmadi
# --------------------------------------------------------------------------- #
run_step "Teslim imaji paket dokumu (pip list)" pass -- \
  "${DRUN[@]}" sh -c 'pip list --format=freeze 2>/dev/null | sort'

run_step "trafilatura teslim imajinda YOK (grep bos donmeli)" fail -- \
  "${DRUN[@]}" sh -c 'pip list --format=freeze 2>/dev/null | grep -i trafilatura'

run_step "trafilatura import EDILEMEZ (ikinci, bagimsiz kanit)" pass -- \
  "${DRUN[@]}" python -c \
    'import importlib.util as u, sys; s = u.find_spec("trafilatura"); print("trafilatura find_spec:", s); sys.exit(0 if s is None else 1)'

# --------------------------------------------------------------------------- #
# 13. API SUNUCUSU `--network none` icinde AYAGA KALKIYOR MU
#
# Onceki adimlar toplu is (batch) kanitiydi. Sartname §5.9 calisan bir SERVIS
# istiyor; "testler agsiz gecti" ile "sunucu agsiz ayaga kalkti" ayri iddialar.
# Bu adim ikincisini olcer: konteyner ayaga kalkar, ICERIDEN localhost'a HTTP
# atilir (disari cikis yok), bellek olculur, konteyner durdurulur.
# --------------------------------------------------------------------------- #
api_smoke() {
  local cid rc=0
  cid="$(docker run -d --network none -e LLM_BACKEND= "$IMAGE")"
  echo "konteyner : $cid"
  # Hazir olana kadar bekle (en fazla ~30 sn). Beklemeyi atlayip hemen sorgulamak,
  # "baglanti reddedildi"yi "sunucu bozuk" sanmaya yol acardi.
  local i=0 ready=1
  while [ "$i" -lt 30 ]; do
    if docker exec "$cid" python -c \
        'import urllib.request; urllib.request.urlopen("http://127.0.0.1:8000/health", timeout=2)' \
        >/dev/null 2>&1; then
      ready=0; break
    fi
    i=$(( i + 1 )); sleep 1
  done

  if [ "$ready" -ne 0 ]; then
    echo "HATA: API 30 sn icinde /health'e yanit vermedi."
    docker logs "$cid" 2>&1 | tail -20
    rc=1
  else
    echo "hazir olma suresi : ~${i} sn"
    echo
    echo "--- /health (konteyner ICINDEN, localhost) ---"
    docker exec "$cid" python -c \
      'import urllib.request; print(urllib.request.urlopen("http://127.0.0.1:8000/health", timeout=5).read().decode()[:400])' || rc=1
    echo
    echo "--- /banks (ilk 300 karakter) ---"
    docker exec "$cid" python -c \
      'import urllib.request; print(urllib.request.urlopen("http://127.0.0.1:8000/banks", timeout=5).read().decode()[:300])' || rc=1
    echo
    echo "--- calisma zamani kaynak kullanimi ---"
    docker stats --no-stream \
      --format 'BELLEK={{.MemUsage}}  CPU={{.CPUPerc}}  PID={{.PIDs}}' "$cid" || rc=1
    echo
    echo "--- sunucu gunlugu ---"
    docker logs "$cid" 2>&1 | tail -6
  fi

  docker stop "$cid" >/dev/null 2>&1 || true
  docker rm -f "$cid" >/dev/null 2>&1 || true
  return "$rc"
}

run_step "API sunucusu --network none icinde ayaga kalkiyor" pass -- api_smoke

# --------------------------------------------------------------------------- #
# 14. İmaj künyesi — boyut, katman sayısı, imaj ID
# --------------------------------------------------------------------------- #
run_step "Imaj kunyesi (boyut / ID / taban)" pass -- \
  docker image inspect "$IMAGE" \
    --format 'ID={{.Id}}
Boyut={{.Size}} bayt
Mimari={{.Os}}/{{.Architecture}}
Olusturma={{.Created}}'

# --------------------------------------------------------------------------- #
# Özet tablo
# --------------------------------------------------------------------------- #
echo
echo "=============================================================================="
echo " OZET"
echo "=============================================================================="
printf '%-3s %-52s %-6s %-8s %s\n' "#" "adim" "kod" "sure(ms)" "sonuc"
_hr
i=0
while [ "$i" -lt "${#STEP_NAME[@]}" ]; do
  printf '%-3s %-52s %-6s %-8s %s\n' \
    "$(( i + 1 ))" "$(echo "${STEP_NAME[$i]}" | cut -c1-52)" \
    "${STEP_CODE[$i]}" "${STEP_MS[$i]}" "${STEP_VERDICT[$i]}"
  i=$(( i + 1 ))
done
_hr
echo "adim sayisi        : ${#STEP_NAME[@]}"
echo "beklenmedik sonuc  : $FAILURES"
echo "transkript         : $LOG"
echo "gecikme JSON       : $OUT_DIR/latency-$TS.json"
echo

if [ "$FAILURES" -eq 0 ]; then
  echo "SONUC: TUM ADIMLAR BEKLENDIGI GIBI."
  echo "       - pozitif: tum test paketi + eval + ablasyon + gecikme olcumu"
  echo "         '--network none' icinde kostu."
  echo "       - negatif: ayni izolasyonda dis dunyaya ULASILAMADI,"
  echo "         ve ayni prob ag acikken ULASTI (yani prob calisiyor)."
  exit 0
fi

echo "SONUC: $FAILURES ADIM BEKLENMEDIK. Kanit paketi GECERSIZ."
echo "       Yukaridaki 'BEKLENMEDIK' satirlarini incele. Bu betik bilerek"
echo "       0-disi cikiyor: yesil olmayan bir kosuyu yesil raporlamak,"
echo "       tam olarak kacinmaya calistigimiz hata sinifidir."
exit 1
