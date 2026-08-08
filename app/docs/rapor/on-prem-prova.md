---
title: "Ağ kapalı tam prova — on-prem iddiası ölçüldü"
tags: [on-prem, docker, olcum, teslim]
date: 2026-08-08
status: stable
---

# Ağ kapalı tam prova (2026-08-08)

Denetimde On-Prem kalemi **13/20** aldı. Kesintinin ana gerekçesi işin
yapılmamış olması değil, **kanıtının üretilmemiş** olmasıydı: "internetsiz
çalışır" iddiası belge düzeyinde duruyordu, ölçülmüş bir koşum yoktu.

## Yöntem — neden Wi-Fi kapatılmadı

Makinenin ağını kapatmak yerine konteynerler **egress'i olmayan bir Docker
ağına** alındı:

```bash
docker network create --internal anatolia-offline
```

Bu daha güçlü bir izolasyondur ve daha dürüsttür: Wi-Fi kapatmak yalnızca
*o anda* dış çağrı yapılmadığını gösterir; `--internal` ağ, sistemin dışarı
çıkma **imkânını** kaldırır. Ölçülerek doğrulandı — konteynerin içinden:

```
egress kapalı: gaierror: [Errno -3] Temporary failure in name resolution
ham IP egress de kapalı: OSError          # 8.8.8.8:53 de erişilemiyor
```

DNS **ve** ham IP çıkışının ikisi de kapalı. Sistem bu koşulda koştu.

## Kurulum

`docker-compose.yml` **değiştirilmedi**. Aynı imajlar (`app-api`, `app-web`)
compose'un derlediği imajlardır; yalnız izole ağa bağlandılar.

**Dürüst sınır:** imaj **derlemesi** ağ ister (temel imaj + `pip install` +
`npm`). Bu her dağıtımda bir kezdir. İddia edilen ve ölçülen şey şudur:
*imajlar hazırken sistem sıfır ağ erişimiyle ayağa kalkar ve çalışır.*

## Ölçümler

| kalem | değer |
|---|---|
| Soğuk kalkış (API) | **1,5 sn** — konteyner oluşturma + 1.774 belgelik SQLite + RAG ters dizini |
| API imajı | 1,16 GB |
| Web imajı | 591 MB |
| API belleği (boşta) | **106 MiB** (7,75 GiB'in %1,4'ü) |
| Web belleği (boşta) | **49 MiB** |
| API CPU (boşta) | %0,3 |

Korpus imajın içinde ve gerçek: **1.774 kampanya, 10 banka**, `/health`
`{"status":"ok","llm":false,"backend":"sqlite"}` döndürüyor. Yani "LLM kapalı"
yolu tanımlı ve çalışıyor — kritik yolda model yok (CLAUDE.md §11).

### Uç gecikmeleri (konteyner içinden, ağ gecikmesi hariç)

| uç | p50 (ms) | p95 (ms) | n |
|---|---:|---:|---:|
| `/health` | 0,5 | 0,6 | 20 |
| `/banks` | 0,8 | 1,0 | 20 |
| `/compare?field=kar_payi_orani` | 1,6 | 2,2 | 20 |
| `/compare?field=vade_ay` | 16,3 | 30,6 | 20 |
| `/scoring?field=kar_payi_orani` | 1,1 | 1,2 | 20 |
| `/advantageous` | 55,6 | 64,1 | 20 |
| `/contradictions/summary` | 25,9 | 35,3 | 20 |
| `/chat` — yapısal soru | 1,4 | 1,5 | 10 |
| `/chat` — RAG sorusu | 4,8 | 5,0 | 10 |

En yavaş uç **`/advantageous`** (p95 64 ms): bileşik skor beş alanı ayrı ayrı
sorgulayıp kampanya başına birleştiriyor. 4 dakikalık sunumda hiçbir ekran
insan tarafından beklenir hissettirmez.

### Arayüz

`app-web` aynı izole ağda ayağa kalktı ve `HTTP 200` ile 5.828 baytlık sayfa
döndürdü (0,1 sn). Next.js üretim derlemesi dış CDN'e bağımlı değil.

## Ne kanıtlanmadı

- **Postgres yolu** bu provada koşmadı; ayrı ölçüldü ([[postgres-paritesi]]):
  53 atlanan testin tamamı geçti, `postgres.py` kapsamı %20,4 → %80,4.
- **LLM yolu** bu provada kapalıydı (`LLM_BACKEND=""`). Ollama/vLLM profilleri
  ayrı ve teslim demosunda kritik yolda değildir (CLAUDE.md §11).
- İmaj derlemesi ağ ister; yukarıda açıkça yazıldı.

## Yeniden üretim

```bash
docker compose build api web
docker network create --internal anatolia-offline
docker run -d --name api --network anatolia-offline \
  -e DATABASE_PATH=data/demo.db -e LLM_BACKEND="" app-api:latest
docker exec api python -c "import socket; socket.create_connection(('8.8.8.8',53),timeout=5)"
# -> OSError beklenir: egress yok
docker exec api python -c "import urllib.request,json; \
  print(json.load(urllib.request.urlopen('http://localhost:8000/health')))"
```

## Sources
- Bu oturumdaki koşum (2026-08-08), `docker network --internal`
- `docker stats`, konteyner içi `urllib` gecikme ölçümü (p50/p95)
- `docker-compose.yml` (değiştirilmedi), `Dockerfile.api`, `web/Dockerfile`

## Related
- [[postgres-paritesi]] — 53 atlanan testin koşumu
- [[genel-denetim]] — On-Prem kaleminin kesinti gerekçesi
