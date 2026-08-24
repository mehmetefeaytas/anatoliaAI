"""Kural hattının BOŞ bıraktığı alanları LLM ile doldur — iki kapılı.

İlgili: ../src/extraction/llm/dayanak.py (kabul kapıları)
        ../src/db/repository.py (`add_fields`, kural değerini EZMEZ)
        CLAUDE.md §3 (kural birincil, LLM yalnız boşluk), §19 (halüsinasyon yasağı)

## Ölçülmüş boşluk

Hedef kategorilerde (Taşıt/İhtiyaç/Konut Finansmanı, Yatırım Ürünü, Finansman)
kural hattı `kar_payi_orani`'nı 773 kampanya belgesinin yalnız **48'inde**
(%6,2) çıkarabiliyor. Bu bir kural hatası değil ölçülmüş bir veri gerçeği:
bankalar oranı çoğu kampanya metninde yayınlamıyor. Ama 368 belgede "kâr
payı / oran" SÖZCÜĞÜ geçiyor ve değer çıkmamış — LLM'in gerçek adayları bunlar.

## Ölçüm (2026-08-24, 120 belge, EVREN `llm-large`)

    kar_payi_orani    LLM buldu 14/120 → dayanaksız 0 · yanlış-alan 0 · KABUL 14
    finansman_tutari  LLM buldu 17/120 → dayanaksız 0 · yanlış-alan 0 · KABUL 17

Yani kuralın hiç değer bulamadığı yerde **%12–14 ek kapsam**, sıfır uydurma.
Bu, çıkarım kolunun kural hattından zayıf olmasıyla ÇELİŞMEZ: orada iki kol
aynı alan için yarışıyordu (F1 0,304 vs 0,469); burada kural hiçbir şey
söylemiyor ve LLM boşluğu dolduruyor. Mimarinin tasarımı tam bu.

## İki kapı — ayrıntı `dayanak.py` başlığında

    dayanak    değerin bütün sayıları metinde geçiyor mu?  (halüsinasyon)
    alan       kanıt penceresi alanla çelişmiyor mu?       (yanlış alana yazma)

Ölçülmüş vaka: *"%0.4 Aval komisyon oranı"* → `kar_payi_orani`. Sayı metinde
var (dayanak geçer) ama aval komisyonu kâr payı oranı değildir.

## Yazma disiplini

- `extractor='llm'` damgası ZORLANIR: kaynağı görünmeyen bir değer denetlenemez.
- `add_fields(..., ezme=False)` — kural değeri asla ezilmez.
- Reddedilen değerler SESSİZ KAYBOLMAZ: gerekçe sayaçları raporlanır.

Kullanım:
    LLM_BACKEND=evren python -m scripts.llm_bosluk_doldur --kuru
    LLM_BACKEND=evren python -m scripts.llm_bosluk_doldur --limit 400
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import pathlib
import sqlite3
import sys
from typing import Any, Optional

from src.extraction.llm.dayanak import kabul_edilir, ozet

#: Şartnamenin finansman ürünleri — kullanıcının işaret ettiği kategoriler.
HEDEF_TURLER = ("Taşıt Finansmanı", "İhtiyaç Finansmanı", "Konut Finansmanı",
                "Yatırım Ürünü", "Finansman")

#: Doldurulacak alanlar. DAR tutuluyor: ikisi de sayısal ve ikisi de dayanak
#: kapısıyla denetlenebilir. Serbest metin alanları (`kampanya_kosullari`) bu
#: koşumun konusu değil — orada dayanak kapısı uygulanamaz.
HEDEF_ALANLAR = ("kar_payi_orani", "finansman_tutari")

#: Metinde alanın sözcüğü hiç geçmiyorsa LLM'e sormanın anlamı yok: hem boşa
#: çağrı hem uydurma riski. Aday süzgeci bu yüzden var.
_ADAY_IZI = ("%kâr payı%", "%kar payı%", "%oran%", "%finansman%", "%TL%")


def _adaylar(conn: sqlite3.Connection, limit: int,
             turler: tuple[str, ...]) -> list[tuple[int, str, str]]:
    """Hedef türlerde, hedef alanların HİÇBİRİ çıkmamış kampanya belgeleri."""
    tp = ",".join("?" * len(turler))
    ap = ",".join("?" * len(HEDEF_ALANLAR))
    iz = " OR ".join("c.clean_text LIKE ?" for _ in _ADAY_IZI)
    return conn.execute(f"""
        SELECT c.id, c.campaign_type, c.clean_text FROM campaigns c
        WHERE c.belge_turu = 'kampanya' AND c.campaign_type IN ({tp})
          AND NOT EXISTS (SELECT 1 FROM extracted_fields e
                          WHERE e.campaign_id = c.id
                            AND e.field_name IN ({ap}))
          AND ({iz})
          AND LENGTH(c.clean_text) BETWEEN 200 AND 20000
        ORDER BY c.id LIMIT ?""",
        (*turler, *HEDEF_ALANLAR, *_ADAY_IZI, limit)).fetchall()


def _kapsam(conn: sqlite3.Connection, turler: tuple[str, ...]) -> dict[str, int]:
    tp = ",".join("?" * len(turler))
    out = {}
    for alan in HEDEF_ALANLAR:
        out[alan] = conn.execute(f"""
            SELECT COUNT(DISTINCT c.id) FROM campaigns c
            JOIN extracted_fields e ON e.campaign_id = c.id
            WHERE c.belge_turu='kampanya' AND c.campaign_type IN ({tp})
              AND e.field_name = ?""", (*turler, alan)).fetchone()[0]
    out["_belge"] = conn.execute(f"""
        SELECT COUNT(*) FROM campaigns WHERE belge_turu='kampanya'
          AND campaign_type IN ({tp})""", turler).fetchone()[0]
    return out


def main(argv: Optional[list[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--db", default="data/demo.db")
    ap.add_argument("--limit", type=int, default=400,
                    help="en çok kaç aday belge işlenecek")
    ap.add_argument("--kuru", action="store_true",
                    help="DB'ye YAZMA — yalnız ölç ve raporla")
    ap.add_argument("--rapor", default=None, help="JSON rapor yolu")
    a = ap.parse_args(argv)

    from src.db.repository import Repository
    from src.extraction.llm.extractor import default_extractor

    conn = sqlite3.connect(a.db)
    onceki = _kapsam(conn, HEDEF_TURLER)
    adaylar = _adaylar(conn, a.limit, HEDEF_TURLER)
    print(f"aday {len(adaylar)} belge · hedef alanlar {', '.join(HEDEF_ALANLAR)}")
    print("ONCE: " + " · ".join(
        f"{k} {v} (%{100*v/onceki['_belge']:.1f})"
        for k, v in onceki.items() if k != "_belge")
        + f" / {onceki['_belge']} belge", flush=True)

    ex = default_extractor()
    repo = Repository(a.db) if not a.kuru else None
    kararlar: list[tuple[bool, str]] = []
    yazilan = 0
    hata = 0
    # BOŞ DÖNÜŞ SAYACI — ölçüm körlüğünü kapatıyor. Kademe zinciri
    # (`CascadingClient`) ağ hatasını YAKALAYIP boş liste döndürüyor, yani
    # `except` bloğuna hiç girilmiyor ve `hata` 0 kalıyor. 2026-08-24
    # koşumunda EVREN erişilemez oldu (HTTP 000), 400 belgenin çoğu sessizce
    # boş döndü ve rapor "hata: 0" yazdı — kazanç eksik, sebep görünmez.
    bos_donus = 0
    ayrinti: list[dict[str, Any]] = []

    for i, (cid, tur, metin) in enumerate(adaylar, 1):
        try:
            cikan = ex.extract(metin)
        except Exception as e:
            hata += 1
            ayrinti.append({"id": cid, "hata": type(e).__name__})
            continue
        kabuller = []
        for f in cikan:
            ad = getattr(f, "field_name", None)
            if ad not in HEDEF_ALANLAR:
                continue
            ok, gerekce = kabul_edilir(
                ad, getattr(f, "canonical_value", None),
                str(getattr(f, "raw_value", "") or ""), metin)
            kararlar.append((ok, gerekce))
            ayrinti.append({"id": cid, "tur": tur, "alan": ad,
                            "canon": getattr(f, "canonical_value", None),
                            "ham": str(getattr(f, "raw_value", ""))[:90],
                            "karar": gerekce})
            if ok:
                # `extractor` ZORLANIR: kaynağı görünmeyen değer denetlenemez.
                kabuller.append(dataclasses.replace(f, extractor="llm")
                                if dataclasses.is_dataclass(f) else f)
        if not cikan:
            bos_donus += 1
        if kabuller and repo is not None:
            yazilan += repo.add_fields(cid, kabuller, ezme=False)
        if i == 20 and bos_donus == 20:
            # Kalan belgeleri boşa gezmenin anlamı yok; sebebi de söyle.
            print("\nDURDURULDU: ilk 20 belgenin TAMAMI boş döndü — LLM ucu "
                  "yanıt vermiyor.\n  Kontrol: LLM_BACKEND ve uç erişimi "
                  "(EVREN için `curl $EVREN_URL/v1/models`).", flush=True)
            break
        if i % 25 == 0:
            print(f"  [{i}/{len(adaylar)}] kabul "
                  f"{sum(1 for k, _ in kararlar if k)} · bos {bos_donus}",
                  flush=True)

    sayac = ozet(kararlar)
    print("\n=== KARAR DAGILIMI ===")
    for k in sorted(sayac, key=lambda x: -sayac[x]):
        print(f"  {k:16s} {sayac[k]:>4}")
    print(f"  {'HATA':16s} {hata:>4}")
    print(f"  {'BOS DONUS':16s} {bos_donus:>4}"
          + ("   ← LLM yanıt vermedi; kazanç EKSİK" if bos_donus > len(adaylar) // 4
             else ""))
    if repo is not None:
        print(f"\nDB'ye yazilan alan satiri: {yazilan}")
        sonra = _kapsam(conn := sqlite3.connect(a.db), HEDEF_TURLER)
        print("SONRA: " + " · ".join(
            f"{k} {v} (%{100*v/sonra['_belge']:.1f})"
            for k, v in sonra.items() if k != "_belge"))
        for alan in HEDEF_ALANLAR:
            fark = sonra[alan] - onceki[alan]
            print(f"  {alan}: +{fark} belge "
                  f"(%{100*onceki[alan]/onceki['_belge']:.1f} → "
                  f"%{100*sonra[alan]/sonra['_belge']:.1f})")
    else:
        print("\n(kuru koşum — DB'ye yazılmadı)")

    if a.rapor:
        pathlib.Path(a.rapor).write_text(
            json.dumps({"karar": sayac, "hata": hata, "bos_donus": bos_donus,
                        "islenen": len(adaylar), "yazilan": yazilan,
                        "once": onceki, "ayrinti": ayrinti},
                       ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"rapor: {a.rapor}")
    return 0


if __name__ == "__main__":
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
    raise SystemExit(main())
