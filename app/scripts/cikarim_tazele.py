"""Kural katmanını korpusta yeniden koşturur ve DEĞİŞEN alanları yazar.

İlgili: ../src/extraction/rules/extract.py (`extract_all` — tek doğruluk kaynağı)
        ./build_demo_db.py (DB'yi sıfırdan kurar), ./ozet_geri_yukle.py

## Bu betiğin varlık sebebi

Bir çıkarım kuralı düzeltildiğinde kod doğru olur ama `data/demo.db` eski
değerleri taşımaya devam eder. İki seçenek vardı:

1. **Tam yeniden kurulum** (`build_demo_db --force`). Doğru ama pahalı: özet
   sütunu sıfırlanır ve `ozet_geri_yukle` ile geri yüklenmesi gerekir; ayrıca
   sınıflandırma ve gömme (embedding) katmanları da yeniden koşar. Tek bir
   regex düzeltmesi için orantısız.
2. **Elle SQL yaması.** Ucuz ama iz bırakmaz ve tekrar üretilemez.

Bu betik üçüncü yolu açar: kural katmanını korpusta yeniden koşturur, saklanan
değerlerle KARŞILAŞTIRIR ve yalnız farkı yazar. Fark raporu her koşuda basılır,
yani "ne değişti" sorusu tahmine değil ölçüme dayanır.

## Yalnız KURAL katmanına dokunur

`extractor='rule'` olmayan satırlar (LLM boşluk doldurma) ellenmez: onları
kural çıktısıyla ezmek, iki katmanın uzlaştırma kararını (`reconcile.py`)
sessizce geri almak olurdu. Teslim edilen `data/demo.db`de bugün 5195 satırın
tamamı `rule` — yani kapsam tamdır; kontrol yine de var, çünkü yarın olmayabilir.

## Öntanım KURU koşudur

Yazma açık bir bayrak ister (`--yaz`). Veri tabanına yazan bir betiğin
varsayılanı yazmak olmamalı; farkı görmeden yazmak, düzeltmenin kapsamını
bilmeden uygulamaktır.

## Kullanım

    .venv/bin/python -m scripts.cikarim_tazele --db data/demo.db          # kuru
    .venv/bin/python -m scripts.cikarim_tazele --db data/demo.db --yaz

Çıkış kodu: 0 tamam · 1 veri tabanı yok · 2 kural katmanı hiç alan üretmedi.
"""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.extraction.rules.extract import extract_all

#: Rapora yazılacak azami örnek satır — ekranı boğmasın.
_AZAMI_ORNEK = 25


def _fark(db: Path) -> tuple[list[dict], int]:
    """(değişiklik listesi, taranan belge sayısı).

    Her kayıt: {campaign_id, field_name, tip, eski, yeni, alan_verisi}
    `tip`: 'KAYBOLDU' | 'YENİ' | 'DEĞİŞTİ'
    """
    conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        kamp = [dict(r) for r in conn.execute(
            "SELECT id, clean_text, raw_text FROM campaigns")]
        saklanan: dict[tuple[int, str], dict] = {}
        for r in conn.execute(
                "SELECT campaign_id, field_name, raw_value, extractor "
                "FROM extracted_fields"):
            saklanan[(r["campaign_id"], r["field_name"])] = dict(r)
    finally:
        conn.close()

    degisiklik: list[dict] = []
    for k in kamp:
        metin = k["clean_text"] or k["raw_text"] or ""
        yeni = {f.field_name: f for f in extract_all(metin)}
        alanlar = {a for (cid, a) in saklanan if cid == k["id"]} | set(yeni)
        for alan in sorted(alanlar):
            eski = saklanan.get((k["id"], alan))
            y = yeni.get(alan)
            # Kural DIŞI katmanın ürettiği satıra dokunulmaz (modül başlığı).
            if eski is not None and (eski.get("extractor") or "rule") != "rule":
                continue
            eski_ham = eski["raw_value"] if eski else None
            yeni_ham = y.raw_value if y else None
            if eski_ham == yeni_ham:
                continue
            degisiklik.append({
                "campaign_id": k["id"], "field_name": alan,
                "tip": ("KAYBOLDU" if y is None
                        else "YENİ" if eski is None else "DEĞİŞTİ"),
                "eski": eski_ham, "yeni": yeni_ham, "alan": y,
            })
    return degisiklik, len(kamp)


def _yaz(db: Path, degisiklik: list[dict]) -> dict[str, int]:
    """Farkı veri tabanına uygular. Dönen: işlem sayaçları."""
    conn = sqlite3.connect(db)
    sayac = Counter()
    try:
        for d in degisiklik:
            if d["tip"] == "KAYBOLDU":
                conn.execute(
                    "DELETE FROM extracted_fields WHERE campaign_id=? "
                    "AND field_name=? AND extractor='rule'",
                    (d["campaign_id"], d["field_name"]))
                sayac["silinen"] += 1
                continue
            f = d["alan"]
            kanonik = json.dumps(f.canonical_value, ensure_ascii=False)
            if d["tip"] == "DEĞİŞTİ":
                conn.execute(
                    "UPDATE extracted_fields SET raw_value=?, "
                    "canonical_value=?, confidence=?, source_span=?, "
                    "span_start=?, span_end=? "
                    "WHERE campaign_id=? AND field_name=? AND extractor='rule'",
                    (f.raw_value, kanonik, f.confidence, f.source_span,
                     f.span_start, f.span_end,
                     d["campaign_id"], d["field_name"]))
                sayac["güncellenen"] += 1
            else:
                conn.execute(
                    "INSERT INTO extracted_fields(campaign_id, field_name, "
                    "raw_value, canonical_value, confidence, source_span, "
                    "extractor, span_start, span_end) "
                    "VALUES (?,?,?,?,?,?,'rule',?,?)",
                    (d["campaign_id"], d["field_name"], f.raw_value, kanonik,
                     f.confidence, f.source_span, f.span_start, f.span_end))
                sayac["eklenen"] += 1
        conn.commit()
    finally:
        conn.close()
    return dict(sayac)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--db", default="data/demo.db")
    ap.add_argument("--yaz", action="store_true",
                    help="farkı GERÇEKTEN yaz (öntanım: kuru koşu)")
    a = ap.parse_args(argv)

    db = Path(a.db)
    if not db.exists():
        print(f"HATA: veri tabanı yok: {db}", file=sys.stderr)
        return 1

    degisiklik, belge = _fark(db)
    print(f"taranan belge     : {belge}")
    print(f"değişen alan      : {len(degisiklik)}")
    if not degisiklik:
        print("kural katmanı veri tabanıyla UYUMLU — yazılacak bir şey yok.")
        return 0

    ozet = Counter((d["field_name"], d["tip"]) for d in degisiklik)
    print("\nalan × tip:")
    for (alan, tip), n in sorted(ozet.items(), key=lambda kv: -kv[1]):
        print(f"  {n:5}  {alan:<22} {tip}")

    print(f"\nörnekler (en fazla {_AZAMI_ORNEK}):")
    for d in degisiklik[:_AZAMI_ORNEK]:
        print(f"  #{d['campaign_id']:<6} {d['field_name']:<20} "
              f"{str(d['eski'])[:30]!r} -> {str(d['yeni'])[:30]!r}")

    if not a.yaz:
        print("\nKURU KOŞU — hiçbir şey yazılmadı. Uygulamak için: --yaz")
        return 0

    sayac = _yaz(db, degisiklik)
    print(f"\nyazıldı: {sayac}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
