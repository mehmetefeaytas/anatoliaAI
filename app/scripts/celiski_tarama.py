"""Çelişki taramasını bir kez koşar ve sonucu artefakta yazar.

İlgili: ../src/comparison/celiski_artefakti.py (biçim + tazelik kuralı)
        ../src/api/routers/denetim.py (`/contradictions`, artefaktı okur)
        ../src/comparison/contradiction.py (taramanın kendisi)

## Niçin bu betik var

Ölçüldü (2026-08-24): korpusun tamamını taramak **47,2 saniye** sürüyor —
2.708 belge, 29 MB metin, belge başına 17,4 ms. Zaman veritabanında değil
(`all_campaigns()` 0,08 sn), her belgede yeniden koşan kural çıkarımında.

Panelin Çelişki Tespiti sekmesi bu maliyeti KULLANICIYA ödetiyordu: ilk
tıklamada 47 saniye bekleniyor, tarayıcı ya da Next proxy'si o kadar
beklemiyor ve ekrana **500** düşüyordu.

Bu betik maliyeti teslim zamanına taşır. Artefakt depoda durur; API açılışta
imzayı denetler ve tazeyse hiç taramaz.

## Kullanım

    .venv/bin/python -m scripts.celiski_tarama
    .venv/bin/python -m scripts.celiski_tarama --db data/demo.db
    .venv/bin/python -m scripts.celiski_tarama --denetle   # yalnız tazelik

`--denetle` CI için: artefakt bayatsa 1 koduyla çıkar. Kapıya bağlanırsa
korpus değişip artefakt güncellenmediğinde build düşer — sessizce bayat
kalmasındansa.
"""

from __future__ import annotations

import argparse
import sys
from typing import Any

from src.comparison import celiski_artefakti
from src.comparison.contradiction import detect
from src.db.repository import Repository
from src.extraction.reconcile import build_campaign


def tara(repo: Any) -> list[dict]:
    """Korpusun tamamını tarar; `/contradictions` gövdesiyle AYNI kayıt biçimi.

    Biçim uyuşmazlığı sessiz bir bozulma olurdu: artefakt okunur, panele
    basılır ve eksik alan boş görünür. `denetim.py`deki sözlük bire bir
    burada da kuruluyor ve `tests/test_celiski_artefakti.py` ikisinin aynı
    anahtarları taşıdığını kilitliyor.
    """
    out: list[dict] = []
    for camp in repo.all_campaigns():
        text = camp.get("raw_text") or ""
        try:
            c = build_campaign(text, bank_slug=camp["bank"],
                               source_url=camp.get("source_url"))
            bulgular = detect(c, as_of=camp.get("scraped_at"))
        except Exception as exc:
            # Sessiz DEĞİL: bir belgenin taramadan düşmesi kapsamı daraltır ve
            # "0 çelişki" ile "tarama çöktü" ayırt edilemez hâle gelir.
            print(f"  ! belge {camp['id']} taranamadı: {exc}", file=sys.stderr)
            continue
        for k in bulgular:
            out.append({
                "bank": camp["bank"],
                "bank_name": camp.get("bank_name"),
                "campaign_id": camp["id"],
                "campaign_type": camp.get("campaign_type"),
                "source_url": camp.get("source_url"),
                "kind": k.kind,
                "detail": k.detail,
                "fields": k.fields,
            })
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--db", default="data/demo.db")
    ap.add_argument("--denetle", action="store_true",
                    help="yalnız tazeliği denetle; bayatsa 1 ile çık")
    a = ap.parse_args(argv)

    repo = Repository(a.db)
    imza = celiski_artefakti.korpus_imzasi(repo)
    if imza is None:
        print("korpus okunamadı — veri tabanı boş ya da erişilemiyor",
              file=sys.stderr)
        return 2

    hazir = celiski_artefakti.oku(imza)
    if a.denetle:
        if hazir is None:
            print(f"❌ artefakt BAYAT ya da yok (imza {imza})\n"
                  f"   çözüm: python -m scripts.celiski_tarama", file=sys.stderr)
            return 1
        print(f"✅ artefakt taze — {len(hazir)} bulgu (imza {imza})")
        return 0

    if hazir is not None:
        print(f"artefakt zaten taze — {len(hazir)} bulgu, tarama atlandı")
        return 0

    print(f"korpus taranıyor (imza {imza})…")
    bulgular = tara(repo)
    hedef = celiski_artefakti.yaz(bulgular, imza)
    kirilim: dict[str, int] = {}
    for b in bulgular:
        kirilim[b["kind"]] = kirilim.get(b["kind"], 0) + 1
    print(f"yazıldı: {hedef}")
    print(f"  bulgu          : {len(bulgular)}")
    print(f"  etkilenen belge: {len({b['campaign_id'] for b in bulgular})}")
    for tur, n in sorted(kirilim.items(), key=lambda kv: -kv[1]):
        print(f"  {tur:28s} {n}")
    return 0


if __name__ == "__main__":                   # pragma: no cover
    raise SystemExit(main())
