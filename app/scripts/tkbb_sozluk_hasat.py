"""TKBB Katılım Sözlüğü'nü hasat eder (resmî, katılım finansına özgü).

İlgili: ../data/terminology/katilim-terim-sozlugu.json (mevcut 101 terim)
        ../src/domain/terminology.py (sözlüğü yükleyen katman)
        ../src/chatbot/terim_cevabi.py (terim sorusuna cevap üreten yol)

## Neden bu kaynak

Proje sözlüğü **101 terim** taşıyor ve chatbot terim sorularını oradan
cevaplıyor. TKBB'nin kendi Katılım Sözlüğü ~600 terim: katılım finansına
ÖZGÜ, resmî ve her kayıtta kullanım örnekleri var.

Alternatifi ölçüldü ve elendi: `tcmb-terimler.json` (314 terim) bir
**makroekonomi** sözlüğüdür — "Finansman" kaydı bile yok ve %22'sinin
tanımında katılım bağlamında yasak terim geçiyor
(bkz. sorun/tcmb-sozlugu-terim-boslugunu-kapatmiyor.md).

## Sayfa yapısı (2026-08-24 ölçümü)

    /katilim-sozluk/<id>        id ~1..700, boşluklu
      h1                        terim adı        → 'murabaha'
      p.text-siyah              tanım            → 'Sermaye sağlayan finansal…'
      "Örnekler" bloğu span'ları kullanım örnekleri

İçerik sunucu tarafında render ediliyor (SSR), yani tarayıcı GEREKMİYOR.

## Etik

`robots.txt` tam izinli (`Disallow:` boş). Yine de istek arası bekleme
uygulanıyor (CLAUDE.md §14 — domain başına 2–5 sn). Ham HTML cache'lenmiyor;
yalnız ayrıştırılmış kayıt saklanıyor, kaynak URL her kayıtta duruyor.

## Bu betik SÖZLÜĞÜ DEĞİŞTİRMEZ

Çıktı ayrı bir dosyaya yazılır (`tkbb-sozluk.jsonl`). Proje sözlüğüyle
birleştirme AYRI bir karardır: çakışan terimlerde hangi tanımın kazanacağı,
`degildir`/`risk_notu` gibi projeye özgü alanların korunması ve jargon
kapısının denetimi ayrıca ele alınmalı.

Kullanım:
    python -m scripts.tkbb_sozluk_hasat --bitis 700
    python -m scripts.tkbb_sozluk_hasat --bas 1 --bitis 20 --kuru
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from typing import Optional

TABAN = "https://tkbb.org.tr/katilim-sozluk"
UA = "AnatoliaAI-arastirma/1.0 (TEKNOFEST 2026; terminoloji derlemesi)"

#: İstek arası bekleme (sn). robots.txt izinli olsa da nazik davranılıyor.
BEKLEME = 1.5

#: Gezinme/duyuru metinleri — terim adı sanılmamalı.
_GURULTU = re.compile(
    r"kamuoyu duyurusu|bildirimler|sonuçlar|sonuç bulundu|anasayfa|"
    r"türk exi̇mbank|tkbb", re.IGNORECASE)


def _getir(id_: int, zaman_asimi: float = 30.0) -> tuple[Optional[str], str]:
    """(html, durum). Durum: 'ok' | 'yok' | 'ag'.

    'yok' ile 'ag' AYRI: var olmayan bir id için sunucu **HTTP 500** döndürüyor
    (ölçüldü — id 1, 5, 50, 690) ve bu normaldir; ağın kopması ise gerçek bir
    hatadır ve tekrar koşum gerektirir. İlk sürüm ikisini aynı `except`te
    topluyordu ve rapor "189 ağ hatası" yazıyordu — oysa çoğu var olmayan
    kayıttı. Sayaçları ayırmak, tekrar koşumun gerekli olup olmadığını
    görünür kılıyor.
    """
    istek = urllib.request.Request(f"{TABAN}/{id_}", headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(istek, timeout=zaman_asimi) as y:
            return y.read().decode("utf-8", errors="replace"), "ok"
    except urllib.error.HTTPError as e:
        # 4xx/5xx: kayıt yok ya da sunucu o id'yi üretemiyor.
        return None, "yok" if e.code in (404, 500) else "ag"
    except (urllib.error.URLError, TimeoutError, OSError):
        return None, "ag"


def ayristir(html: str, id_: int) -> Optional[dict]:
    """Terim adı + tanım + örnekler. Terim ya da tanım yoksa `None`.

    `None` dönmek bir hata değil: id aralığı boşluklu ve var olmayan bir id
    gezinme iskeletini döndürüyor. Terim adı gürültü desenine uyarsa da
    atılıyor — duyuru başlığını terim olarak kaydetmek sözlüğü kirletirdi.
    """
    from bs4 import BeautifulSoup
    corba = BeautifulSoup(html, "html.parser")
    kap = corba.select_one('[class*="bg-sozluk-bg"]')
    if kap is None:
        return None
    h1 = kap.find("h1")
    if h1 is None:
        return None
    terim = h1.get_text(" ", strip=True)
    if not terim or len(terim) > 90 or _GURULTU.search(terim):
        return None
    p = kap.select_one('p[class*="text-siyah"]') or kap.find("p")
    tanim = p.get_text(" ", strip=True) if p else ""
    if len(tanim) < 25:
        return None
    ornekler = []
    for blok in kap.select("div"):
        basi = blok.get_text(" ", strip=True)[:20]
        if basi.startswith("Örnekler"):
            ornekler = [s.get_text(" ", strip=True) for s in blok.find_all("span")
                        if len(s.get_text(strip=True)) > 40]
            break
    return {
        "id": f"tkbb-{id_}",
        "terim": terim,
        "tanim": re.sub(r"\s+", " ", tanim),
        "ornekler": ornekler[:6],
        "kaynak_url": f"{TABAN}/{id_}",
        "kaynak_kurum": "Türkiye Katılım Bankaları Birliği (TKBB)",
        "otorite_tipi": "sektor-birligi",
    }


def main(argv: Optional[list[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--bas", type=int, default=1)
    ap.add_argument("--bitis", type=int, default=700)
    ap.add_argument("--bekleme", type=float, default=BEKLEME)
    ap.add_argument("--kuru", action="store_true")
    ap.add_argument("--devam", action="store_true",
                    help="mevcut dosyadaki id'leri ATLA ve üzerine EKLE "
                         "(ağ hatası alan id'leri tekrar denemek için)")
    a = ap.parse_args(argv)

    kok = pathlib.Path(__file__).resolve().parents[1]
    hedef = kok / "data" / "terminology" / "tkbb-sozluk.jsonl"
    toplandi = datetime.now(timezone.utc).isoformat(timespec="seconds")

    # DEVAM MODU: hasat ağ hatası aldığında tekrar koşum yalnız EKSİKLERİ
    # denemeli. Yazma modu dosyayı ezdiği için (`w`), devam bayrağı olmadan
    # ikinci koşum ilk koşumun 509 kaydını SİLERDİ — bu betiğin ilk sürümünde
    # tam bu risk vardı.
    onceki: list[dict] = []
    atla: set[int] = set()
    if a.devam and hedef.exists():
        for satir in hedef.read_text(encoding="utf-8").splitlines():
            if not satir.strip():
                continue
            try:
                kayit = json.loads(satir)
            except json.JSONDecodeError:
                continue
            onceki.append(kayit)
            kimlik = str(kayit.get("id") or "")
            if kimlik.startswith("tkbb-") and kimlik[5:].isdigit():
                atla.add(int(kimlik[5:]))
        print(f"devam modu: {len(onceki)} mevcut kayit korunuyor, "
              f"{len(atla)} id atlaniyor")

    bulunan: list[dict] = []
    bos = yok = agsiz = 0
    for i in range(a.bas, a.bitis + 1):
        if i in atla:
            continue
        html, durum = _getir(i)
        if html is None:
            if durum == "ag":
                agsiz += 1
            else:
                yok += 1
        else:
            kayit = ayristir(html, i)
            if kayit is None:
                bos += 1
            else:
                kayit["collected_at"] = toplandi
                bulunan.append(kayit)
        if i % 25 == 0:
            print(f"  [{i}/{a.bitis}] terim {len(bulunan)} · bos {bos} · "
                  f"kayit-yok {yok} · AG HATASI {agsiz}", flush=True)
        time.sleep(a.bekleme)

    print(f"\nTOPLAM terim {len(bulunan)} · bos sayfa {bos} · "
          f"kayit yok (HTTP 404/500) {yok} · GERCEK ag hatasi {agsiz}")
    if agsiz:
        print(f"  → {agsiz} id ag yuzunden kacti; `--devam` ile tekrar kosulabilir.")
    if bulunan:
        ornekli = sum(1 for x in bulunan if x["ornekler"])
        ort = sum(len(x["tanim"]) for x in bulunan) // len(bulunan)
        print(f"ornek tasiyan: {ornekli} · ortalama tanim {ort} karakter")
        for x in bulunan[:3]:
            print(f"  · {x['terim']}: {x['tanim'][:90]}…")
    if a.kuru:
        print("(kuru koşum — yazılmadı)")
        return 0
    hedef.parent.mkdir(parents=True, exist_ok=True)
    # Önceki kayıtlar id sırasına göre birleşiyor: dosya deterministik kalsın.
    def _sira(x: dict) -> tuple:
        k = str(x.get("id") or "")
        return (0, int(k[5:])) if k.startswith("tkbb-") and k[5:].isdigit() \
            else (1, 0)
    hepsi = sorted(onceki + bulunan, key=_sira)
    with hedef.open("w", encoding="utf-8") as f:
        for x in hepsi:
            f.write(json.dumps(x, ensure_ascii=False) + "\n")
    print(f"yazildi: {hedef.relative_to(kok)} ({len(hepsi)} kayit; "
          f"{len(bulunan)} yeni)")
    return 0 if hepsi else 1


if __name__ == "__main__":
    raise SystemExit(main())
