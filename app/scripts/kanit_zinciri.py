"""Gold kanıt zinciri doğrulayıcı — her gold kaydı ham arşive kadar izlenir.

İlgili: scripts/gold_schema.py (`field_spans` = ALAN içi kanıt)
        scripts/sample_gold_v2.py (aday seçimi, aynı content_hash tabanı)
        tests/test_kanit_zinciri.py

## Neden bu betik var

Rakip projeler gold kaydı başına ekran görüntüsü tutuyor. Bizim provenance
zincirimiz ondan güçlü — ham HTML, indirme zamanı, HTTP durumu ve toplama
yöntemi arşivde duruyor — ama **görünür değildi**: zinciri kimse uçtan uca
doğrulamıyordu. Kanıtın kanıt sayılması için iddia edilmesi yetmez,
KOŞULABİLİR olması gerekir.

## Zincir üç katman ve İKİ AYRI hash

    gold kaydı           content_hash = sha256(normalize_text(çıkarılmış metin))
      |  eşleşme: normalize edilmiş metnin özeti
    data/raw/<banka>/<belge>.txt        çıkarılmış metin
      |  kardeş dosya
    data/raw/<banka>/<belge>.txt.meta.json
         content_hash = sha256(HAM HTML baytları)   <- BAŞKA bir hash
         source_url · scraped_at · http_status · collection_method

İki hash'in **eşleşmemesi normaldir ve doğrudur**; farklı katmanları özetler.
Bu betik yazılırken ilk varsayım "ikisi aynı olmalı" idi ve 49 belgenin
49'unda tutmadı — varsayım yanlıştı, veri değil. Zincir dosya kimliği
üzerinden kurulur, hash eşitliği üzerinden değil.

## Neyi doğrular

1. Gold kaydının metni ham arşivde **bulunuyor** (content_hash ile).
2. O metnin `.meta.json` kardeşi **var**.
3. `source_url` gold ile meta arasında **tutarlı**.
4. `scraped_at` **mevcut** ve ISO-8601 ayrıştırılabilir.

## Kapıyı ne kapatır, ne kapatmaz

**Kapatır (çıkış 1):** kaynağı ham arşivde ne metinle ne URL ile bulunabilen
kayıt; `.meta.json`'ı olmayan, `scraped_at`'i eksik/bozuk olan, `source_url`'ü
gold ile meta arasında çelişen kayıt. Bunlarda iddia gerçekten dayanaksızdır.

**Kapatmaz (çıkış 0, ama raporda GÖRÜNÜR):** içerik kayması — sayfa
anotasyondan sonra tazelenmiş, hash artık tutmuyor ama kaynak URL arşivde
duruyor. Gold DONMUŞ bir anlık görüntüdür, korpus AKAR; anote edilen metnin
kendisi kaydın `text` alanında saklıdır ve ölçüm onu kullanır. Bunu kırık
saymak, her tazelemede kırmızıya dönen ve bu yüzden okunmayan bir rapor
üretirdi.

## Kullanım

    python -m scripts.kanit_zinciri --gold data/gold/gold.v2.json
    python -m scripts.kanit_zinciri --gold data/gold/gold.v2.json \
        --out data/gold/kanit_zinciri.md
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.preprocessing.clean import normalize_text
from src.scraping.collector import content_hash

VARSAYILAN_GOLD = "data/gold/gold.v2.json"
VARSAYILAN_RAW = "data/raw"


def _url_kanonik(url: str) -> str:
    """Kıyas için URL'yi sadeleştirir.

    Korpusta aynı sayfa büyük/küçük harf ve `:443` varyantlarıyla iki kez
    toplanmış olabiliyor (bkz. sample_gold_v2 ilke 2). Bu varyantları
    "tutarsız provenance" diye raporlamak yanlış alarm olurdu; ikisi de aynı
    kaynağı gösteriyor.
    """
    u = (url or "").strip().lower()
    u = u.replace(":443/", "/").replace(":80/", "/")
    return u.rstrip("/")


def raw_indeksi(raw_dir: str) -> tuple[dict[str, list[Path]], dict[str, list[Path]]]:
    """(hash -> .txt yolları, kanonik URL -> .txt yolları) indekslerini kurar.

    URL indeksi ikinci bir yol açar ve gereklidir: gold DONMUŞ bir anlık
    görüntüdür, korpus ise tazeleniyor. Sayfa anotasyondan sonra değişirse
    hash tutmaz ama kayıt kaybolmuş DEĞİLDİR — kaynağı hâlâ arşivde. İkisini
    ayırmadan raporlamak, olağan içerik tazelemesini "kanıt yok" diye
    gösterirdi.
    """
    hash_idx: dict[str, list[Path]] = defaultdict(list)
    url_idx: dict[str, list[Path]] = defaultdict(list)
    for p in sorted(Path(raw_dir).rglob("*.txt")):
        try:
            metin = normalize_text(p.read_text(encoding="utf-8", errors="ignore"))
        except OSError:
            continue
        if metin:
            hash_idx[content_hash(metin)].append(p)
        meta = _meta_oku(p)
        if meta and meta.get("source_url"):
            url_idx[_url_kanonik(meta["source_url"])].append(p)
    return hash_idx, url_idx


def _meta_oku(txt: Path) -> dict | None:
    m = Path(str(txt) + ".meta.json")
    if not m.is_file():
        return None
    try:
        return json.loads(m.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _iso_mu(deger: str) -> bool:
    try:
        datetime.fromisoformat(str(deger).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return False
    return True


def dogrula(gold_yolu: str, raw_dir: str) -> list[dict]:
    """Her gold kaydı için zincir durumunu döndürür."""
    kayitlar = json.loads(Path(gold_yolu).read_text(encoding="utf-8"))
    hash_idx, url_idx = raw_indeksi(raw_dir)
    sonuc = []
    for r in kayitlar:
        h = r.get("content_hash") or ""
        yollar = hash_idx.get(h, [])
        satir = {
            "id": r.get("id"),
            "content_hash": h,
            "ham_dosya": None,
            "kopya_sayisi": len(yollar),
            "meta": None,
            "scraped_at": None,
            "http_status": None,
            "collection_method": None,
            "html_hash": None,
            "url_tutarli": None,
            "kaymis": False,
            "sorunlar": [],
        }
        if not yollar:
            # İkinci yol: aynı URL arşivde var mı? Varsa kanıt kaybolmamış,
            # sayfa anotasyondan SONRA değişmiş demektir.
            yollar = url_idx.get(_url_kanonik(r.get("source_url", "")), [])
            if not yollar:
                satir["sorunlar"].append("ham arşivde ne metin ne URL bulunabildi")
                sonuc.append(satir)
                continue
            satir["kaymis"] = True
            satir["kopya_sayisi"] = len(yollar)
        txt = yollar[0]
        satir["ham_dosya"] = str(txt.relative_to(Path(raw_dir)))
        meta = _meta_oku(txt)
        if meta is None:
            satir["sorunlar"].append(".meta.json yok veya okunamadı")
            sonuc.append(satir)
            continue
        satir["meta"] = True
        satir["scraped_at"] = meta.get("scraped_at")
        satir["http_status"] = meta.get("http_status")
        satir["collection_method"] = meta.get("collection_method")
        satir["html_hash"] = meta.get("content_hash")
        if not satir["scraped_at"]:
            satir["sorunlar"].append("scraped_at yok")
        elif not _iso_mu(satir["scraped_at"]):
            satir["sorunlar"].append(f"scraped_at ISO-8601 değil: {satir['scraped_at']}")
        g_url, m_url = _url_kanonik(r.get("source_url", "")), _url_kanonik(meta.get("source_url", ""))
        satir["url_tutarli"] = bool(g_url) and g_url == m_url
        if not satir["url_tutarli"]:
            satir["sorunlar"].append(f"source_url tutarsız: gold={g_url!r} meta={m_url!r}")
        sonuc.append(satir)
    return sonuc


def rapor(sonuc: list[dict], gold_yolu: str) -> str:
    tam = [s for s in sonuc if not s["sorunlar"] and not s["kaymis"]]
    kaymis = [s for s in sonuc if s["kaymis"] and not s["sorunlar"]]
    kirik = [s for s in sonuc if s["sorunlar"]]
    kopyali = [s for s in sonuc if s["kopya_sayisi"] > 1]
    o = [
        "# Gold Kanıt Zinciri",
        "",
        f"> `scripts/kanit_zinciri.py` üretti. Kaynak: `{gold_yolu}`",
        "",
        "Her gold kaydı ham arşive kadar izlenir: çıkarılmış metin -> ham HTML ->",
        "kaynak URL + indirme zamanı. Ekran görüntüsü yerine **koşulabilir** kanıt.",
        "",
        "## Özet",
        "",
        "| Ölçüt | Değer |",
        "|---|---:|",
        f"| Gold kaydı | {len(sonuc)} |",
        f"| **Zinciri tam (hash birebir)** | **{len(tam)}** |",
        f"| Zinciri tam, içerik kaymış (URL üzerinden) | {len(kaymis)} |",
        f"| Zinciri KIRIK | {len(kirik)} |",
        f"| Ham arşivde birden çok kopyası olan | {len(kopyali)} |",
        "",
    ]
    if kaymis:
        o += [
            "## İçerik kayması — kanıt duruyor, sayfa değişmiş",
            "",
            "Gold **donmuş** bir anlık görüntüdür; korpus tazeleniyor. Aşağıdaki",
            "kayıtlarda anote edilen metin ile arşivdeki güncel metin ayrışmış.",
            "Bu bir kanıt kaybı DEĞİLDİR: anote edilen metnin kendisi gold kaydının",
            "`text` alanında saklı ve ölçüm onu kullanıyor; alan değerlerinin o",
            "metinden geldiği `field_spans` ile ayrıca kanıtlı. Kayıt burada",
            "görünür kalır ki 'gold ile korpus aynı' sanılmasın.",
            "",
            "| id | arşivdeki son indirme | ham dosya |",
            "|---|---|---|",
        ]
        o += [
            f"| `{s['id']}` | {s['scraped_at'] or '—'} | `{s['ham_dosya'] or '—'}` |"
            for s in kaymis
        ]
        o += [""]
    if kirik:
        o += ["## Eksik zincirler", "", "| id | sorun |", "|---|---|"]
        o += [f"| `{s['id']}` | {'; '.join(s['sorunlar'])} |" for s in kirik]
        o += [""]
    if kopyali:
        o += [
            "## Ham arşivde birden çok kopya",
            "",
            "Aynı içerik birden çok dosyada duruyor. Zinciri kırmaz (ilk dosya",
            "kullanılır) ama korpus sayımını şişirir — `sample_gold_v2` ilke 2.",
            "",
            "| id | kopya |",
            "|---|---:|",
        ]
        o += [f"| `{s['id']}` | {s['kopya_sayisi']} |" for s in kopyali]
        o += [""]
    o += [
        "## Zincir — kayıt başına",
        "",
        "| id | ham dosya | indirme zamanı | HTTP | yöntem |",
        "|---|---|---|---:|---|",
    ]
    for s in sorted(sonuc, key=lambda x: str(x["id"])):
        o.append(
            f"| `{s['id']}` | `{s['ham_dosya'] or '—'}` | {s['scraped_at'] or '—'} "
            f"| {s['http_status'] or '—'} | {s['collection_method'] or '—'} |"
        )
    return "\n".join(o) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Gold kanıt zinciri doğrulayıcı.")
    ap.add_argument("--gold", default=VARSAYILAN_GOLD)
    ap.add_argument("--raw-dir", default=VARSAYILAN_RAW)
    ap.add_argument("--out", help="markdown rapor yolu (verilmezse yalnız özet basılır)")
    a = ap.parse_args(argv)

    sonuc = dogrula(a.gold, a.raw_dir)
    kirik = [s for s in sonuc if s["sorunlar"]]
    kaymis = [s for s in sonuc if s["kaymis"] and not s["sorunlar"]]
    if a.out:
        Path(a.out).write_text(rapor(sonuc, a.gold), encoding="utf-8")
        print(f"rapor: {a.out}")
    print(f"gold kaydı           : {len(sonuc)}")
    print(f"zinciri tam (hash)   : {len(sonuc) - len(kirik) - len(kaymis)}")
    print(f"içerik kaymış (URL)  : {len(kaymis)}")
    print(f"zinciri KIRIK        : {len(kirik)}")
    for s in kaymis:
        print(f"  kaymış: {s['id']} (arşiv {s['scraped_at']})")
    for s in kirik:
        print(f"  KIRIK : {s['id']}: {'; '.join(s['sorunlar'])}")
    # İçerik kayması kapıyı KAPATMAZ: gold donmuş, korpus akıyor; anote edilen
    # metin kaydın içinde duruyor. Kapıyı yalnız kaynağı hiç bulunamayan kayıt
    # kapatır — o zaman iddia gerçekten dayanaksız kalır.
    return 1 if kirik else 0


if __name__ == "__main__":
    raise SystemExit(main())
