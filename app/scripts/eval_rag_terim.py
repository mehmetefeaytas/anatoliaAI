"""Fıkhî terim kapsaması — RAG kaynak gösterebiliyor mu?

İlgili: ../docs/rapor/rag-terim-kapsama.md, ../src/chatbot/rag.py

## Neden bu betik var

Katılım bankacılığının ayırt edici sözlüğü (murabaha, icare, sukuk,
muacceliyet) korpusta **seyrektir** — murabaha 31 belge (%1,8), icare 7
(%0,4). Seyrek olduğu için de en kolay sessizce kaybolan şeydir: chatbot
"bilmiyorum" der, kimse fark etmez, çünkü gold sette (n=20) bu terimlerden
hiçbiri yoktur.

Bu betik o boşluğu **gold'suz** ölçer. Kapsama ölçütü KANIT ŞARTLIDIR:

    terim kapsandı  <=>  dönen pasajlardan biri terimi GERÇEKTEN içeriyor

"Pasaj döndü" yetmez. Alakasız pasajı kaynak diye göstermek, hiç cevap
vermemekten kötüdür (sessiz halüsinasyon).

## Kullanım

    python -m scripts.eval_rag_terim
    python -m scripts.eval_rag_terim --db data/demo.v2.db --json rapor.json
    python -m scripts.eval_rag_terim --db data/demo.db --min-overlap 2

Çıkış kodu 0 her zaman: bu bir kapı değil, bir ÖLÇÜMdür. Kapsamayan terim
bir kusur olabileceği gibi veri boşluğu da olabilir (bkz. `müşaraka`) ve
ikisini ayırt etmek insana aittir.

Saf stdlib + depo içi modüller. Offline, LLM gerektirmez.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

KOK = Path(__file__).resolve().parents[1]
if str(KOK) not in sys.path:
    sys.path.insert(0, str(KOK))

from src.chatbot.rag import KeywordRetriever, _tokenize  # noqa: E402
from src.db.repository import Repository  # noqa: E402

# Ölçülen terimler. Fıkhî/Osmanlıca çekirdek + iki yaygın terim (`kâr payı`,
# `katılma hesabı`) kontrol grubu olarak: onlar kapsanmıyorsa sorun terimlerin
# seyrekliğinde değil, erişimin kendisindedir.
TERIMLER: tuple[str, ...] = (
    "murabaha", "mudaraba", "müşaraka", "icare", "sukuk", "istisna",
    "karz-ı hasen", "vekâlet", "muacceliyet", "tekafül", "katılma hesabı",
    "kâr payı", "teverruk", "selem", "vaad",
)

VARSAYILAN_DB = "data/demo.db"


def _kok_token(terim: str) -> str:
    """Terimin ilk anlamlı token'ı — kanıt aramasında bunu ararız.

    Türkçe sondan eklemeli: belgede "sukuku", "murabahaya", "icareye" geçer.
    Tam eşitlik yerine token listesinde ÖN EK araması yapılır.
    """
    toks = _tokenize(terim)
    return toks[0] if toks else ""


def kapsama(retriever: KeywordRetriever, terim: str, k: int = 3) -> dict:
    """Tek terim için kapsama kararı + kanıt."""
    soru = f"{terim} nedir?"
    pasajlar = retriever.retrieve(soru, k=k)
    kok = _kok_token(terim)
    kanit = None
    for p in pasajlar:
        ptok = _tokenize(p.get("text") or "")
        if kok and any(t.startswith(kok) for t in ptok):
            kanit = p.get("source_url")
            break
    return {
        "terim": terim,
        "soru": soru,
        "pasaj_sayisi": len(pasajlar),
        "kapsandi": kanit is not None,
        # Kanıt URL'si RAPORA GİRER: "kapsandı" iddiası denetlenebilir olmalı.
        "kanit_url": kanit,
    }


def calistir(db: str, min_overlap: int | None = None, k: int = 3) -> dict:
    repo = Repository(db)
    try:
        r = (KeywordRetriever(repo) if min_overlap is None
             else KeywordRetriever(repo, min_overlap=min_overlap))
        satirlar = [kapsama(r, t, k=k) for t in TERIMLER]
        return {
            "db": db,
            "belge_sayisi": r.document_count,
            "min_overlap": r.min_overlap,
            "terim_sayisi": len(satirlar),
            "kapsanan": sum(s["kapsandi"] for s in satirlar),
            "satirlar": satirlar,
        }
    finally:
        repo.close()


def yazdir(rapor: dict) -> None:
    print(f"\nDB: {rapor['db']}  |  belge: {rapor['belge_sayisi']}  |  "
          f"min_overlap: {rapor['min_overlap']}")
    print(f"kapsama: {rapor['kapsanan']}/{rapor['terim_sayisi']}\n")
    for s in rapor["satirlar"]:
        isaret = "✓" if s["kapsandi"] else "·"
        kaynak = s["kanit_url"] or "—"
        print(f"  {isaret} {s['terim']:<16} pasaj={s['pasaj_sayisi']}  {kaynak[:78]}")
    eksik = [s["terim"] for s in rapor["satirlar"] if not s["kapsandi"]]
    if eksik:
        print(f"\nKapsanmayan: {', '.join(eksik)}")
        print("  Not: kapsanmama erişim kusuru DA olabilir, veri boşluğu DA. "
              "Terimin korpusta kaç belgede geçtiğine bakmadan karar verilmez.")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="python -m scripts.eval_rag_terim",
        description="Fıkhî terim kapsaması (kanıt şartlı) — gold gerektirmez.")
    ap.add_argument("--db", default=VARSAYILAN_DB, help="SQLite DB yolu")
    ap.add_argument("--min-overlap", type=int, default=None,
                    help="eşiği elle ez (karşılaştırmalı ölçüm için)")
    ap.add_argument("--k", type=int, default=3, help="pasaj sayısı")
    ap.add_argument("--json", default=None, help="raporu JSON olarak da yaz")
    args = ap.parse_args(argv)

    if not Path(args.db).is_file():
        print(f"HATA: DB bulunamadı: {args.db}\n"
              f"  Kurmak için: python -m scripts.build_demo_db --out {args.db}",
              file=sys.stderr)
        return 2

    rapor = calistir(args.db, min_overlap=args.min_overlap, k=args.k)
    yazdir(rapor)
    if args.json:
        Path(args.json).write_text(
            json.dumps(rapor, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\nJSON rapor: {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
