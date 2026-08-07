"""gold.v2 aday havuzu — ölçüm setini n=20'den genişletmek için örnekleme.

İlgili: ../docs/rapor/gold-genisletme.md, gold_schema.py, ../eval/run_eval.py

## Neden

Mevcut gold n=20. Bu bir SIRALAMA sinyalidir, kesin performans ölçüsü değil:
K-1 kararında (çerçeve ayıklaması) iki yapılandırma arasındaki fark
halüsinasyonda **5 kayda**, kaçırmada **2 alana** dayanıyor. Bu büyüklükte
karar kırılgandır.

Ayrıca dar setin somut bedeli ölçüldü: gecikme cezası maddesinden oran
çıkarma hatası korpusta üretilen `kar_payi_orani` kayıtlarının **%17,9'unu**
etkiliyordu ve gold'da **sıfır** iz bırakıyordu (bkz.
`docs/rapor/rag-terim-kapsama.md`).

## Örnekleme ilkeleri

1. **Tabakalı**: kampanya türüne göre (8 sınıf), sonra bankaya göre.
   Sınıf başına eşit kota hedeflenir; kotayı dolduramayan sınıf eksik kalır
   ve raporda GÖRÜNÜR (sessizce başka sınıfla doldurulmaz).
2. **Ayrık**: gold.v1'de bulunan belgeler `content_hash` ile dışlanır.
   Aynı belgeyi iki kez ölçmek n'i şişirir, bilgi eklemez.
3. **PDF yok**: gold.v1'in 20 belgesinin tamamı web sayfası. Sözleşme
   PDF'leri farklı bir tür (kampanya değil, akit) ve alanların çoğu orada
   yapısal olarak yoktur; karıştırmak iki seti kıyaslanamaz kılar.
   Bu bir KAPSAM kararıdır, kalite kararı değil — PDF'ler ayrı bir set
   olarak ele alınmalı.
4. **Kabuk belge yok**: çok kısa ya da gezinme metninden ibaret belgeler
   elenir; anotasyon bütçesi bilgi taşıyan belgeye gider.
5. **Deterministik**: sabit tohum + kararlı sıralama. Aynı komut aynı
   örneği verir, yoksa ölçüm tekrar üretilemez.

## Kullanım

    python -m scripts.sample_gold_v2 --n 48 --out data/gold/gold.v2.aday.json
    python -m scripts.sample_gold_v2 --n 48 --parcala 4 --out-dir data/gold/parca

Çıktı **aday havuzudur, gold DEĞİLDİR**: alanlar boştur. Doldurma işi
anotasyondur ve `data/gold/ANNOTATION_GUIDE.md` kılavuzuna tabidir.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from collections import defaultdict
from pathlib import Path

KOK = Path(__file__).resolve().parents[1]
if str(KOK) not in sys.path:
    sys.path.insert(0, str(KOK))

from src.db.repository import Repository

VARSAYILAN_DB = "data/demo.db"
VARSAYILAN_GOLD = "data/gold/gold.v1.json"

# Kabuk belge eşiği. gold.v1'in ortalaması 4690 karakter; 600'ün altındaki
# belgeler korpusta tipik olarak menü/başlık kabuklarıdır.
MIN_KARAKTER = 600
# Üst sınır: 20 000 karakterin üstündeki belgeler tarife tablolarıdır ve
# anotatör bütçesini tek belgede tüketirler.
MAX_KARAKTER = 20_000

TOHUM = 20260807


def _kabuk_mu(metin: str) -> bool:
    """Bilgi taşımayan belge mi? (uzunluk + sözcük çeşitliliği)"""
    if not (MIN_KARAKTER <= len(metin) <= MAX_KARAKTER):
        return True
    sozcukler = metin.split()
    if len(sozcukler) < 80:
        return True
    # Menü kabukları az sayıda sözcüğün tekrarıdır.
    return len(set(sozcukler)) / len(sozcukler) < 0.25


def _gold_hashleri(gold_yolu: str) -> set[str]:
    p = Path(gold_yolu)
    if not p.is_file():
        return set()
    kayitlar = json.loads(p.read_text(encoding="utf-8"))
    return {k["content_hash"] for k in kayitlar if k.get("content_hash")}


def havuz(db: str, gold_yolu: str) -> list[dict]:
    """Uygun adayları döndürür (henüz örneklenmemiş, ham havuz)."""
    repo = Repository(db)
    try:
        kampanyalar = repo.all_campaigns()
    finally:
        repo.close()
    haric = _gold_hashleri(gold_yolu)
    out = []
    for c in kampanyalar:
        url = (c.get("source_url") or "")
        if ".pdf" in url.lower() or url.startswith("file://"):
            continue
        metin = c.get("raw_text") or ""
        if _kabuk_mu(metin):
            continue
        # `content_hash` DB'de tutulmuyor; metinden türetilir (aynı fonksiyon).
        from src.scraping.collector import content_hash
        h = content_hash(metin)
        if h in haric:
            continue
        out.append({
            "id": f"{c.get('bank')}--{abs(hash(url)) % 10**8}",
            "bank_slug": c.get("bank"),
            "source_url": url,
            "content_hash": h,
            "text": metin,
            "campaign_type": c.get("campaign_type"),
        })
    return out


def orneklendir(adaylar: list[dict], n: int, tohum: int = TOHUM) -> list[dict]:
    """Türe göre tabakalı, banka çeşitliliğini gözeten deterministik örnek."""
    rng = random.Random(tohum)
    turlere = defaultdict(list)
    for a in adaylar:
        turlere[a["campaign_type"]].append(a)
    turler = sorted(turlere, key=lambda t: (t is None, str(t)))
    for t in turler:
        # Kararlı sıra + tek tohum: tekrar üretilebilirlik şartı.
        turlere[t].sort(key=lambda a: a["content_hash"])
        rng.shuffle(turlere[t])

    kota = max(1, n // max(1, len(turler)))
    secilen: list[dict] = []
    kullanilan_banka: defaultdict[str, int] = defaultdict(int)

    def _sec(t: str, adet: int) -> None:
        # Banka çeşitliliği: her turda en az temsil edilen bankayı öne al.
        havuz_t = sorted(turlere[t], key=lambda a: kullanilan_banka[a["bank_slug"]])
        for a in havuz_t:
            if adet <= 0:
                return
            if a in secilen:
                continue
            secilen.append(a)
            kullanilan_banka[a["bank_slug"]] += 1
            adet -= 1

    for t in turler:
        _sec(t, kota)
    # Kota altında kalan sınıflar varsa kalanı en bol sınıflardan tamamla.
    for t in sorted(turler, key=lambda t: -len(turlere[t])):
        if len(secilen) >= n:
            break
        _sec(t, n - len(secilen))
    return secilen[:n]


def rapor(secilen: list[dict], adaylar: list[dict]) -> str:
    tur = defaultdict(int)
    banka = defaultdict(int)
    for s in secilen:
        tur[str(s["campaign_type"])] += 1
        banka[s["bank_slug"]] += 1
    satir = [f"aday havuzu: {len(adaylar)} | seçilen: {len(secilen)}", "",
             "tür dağılımı:"]
    satir += [f"  {k:<24} {v}" for k, v in sorted(tur.items())]
    satir += ["", "banka dağılımı:"]
    satir += [f"  {k:<24} {v}" for k, v in sorted(banka.items())]
    return "\n".join(satir)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="python -m scripts.sample_gold_v2",
        description="gold.v2 için tabakalı, deterministik aday örneği.")
    ap.add_argument("--db", default=VARSAYILAN_DB)
    ap.add_argument("--gold", default=VARSAYILAN_GOLD,
                    help="dışlanacak mevcut gold (content_hash ile)")
    ap.add_argument("--n", type=int, default=48)
    ap.add_argument("--tohum", type=int, default=TOHUM)
    ap.add_argument("--out", default="data/gold/gold.v2.aday.json")
    ap.add_argument("--parcala", type=int, default=0,
                    help="çıktıyı N parçaya böl (paralel anotasyon için)")
    ap.add_argument("--out-dir", default="data/gold/parca")
    args = ap.parse_args(argv)

    if not Path(args.db).is_file():
        print(f"HATA: DB yok: {args.db}", file=sys.stderr)
        return 2

    adaylar = havuz(args.db, args.gold)
    if not adaylar:
        print("HATA: aday havuzu BOŞ — filtreler her belgeyi eledi.",
              file=sys.stderr)
        return 2
    secilen = orneklendir(adaylar, args.n, args.tohum)

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(
        json.dumps(secilen, ensure_ascii=False, indent=2), encoding="utf-8")
    print(rapor(secilen, adaylar))
    print(f"\nYazıldı: {args.out}")

    if args.parcala > 0:
        d = Path(args.out_dir)
        d.mkdir(parents=True, exist_ok=True)
        boy = -(-len(secilen) // args.parcala)
        for i in range(args.parcala):
            parca = secilen[i * boy:(i + 1) * boy]
            if not parca:
                continue
            p = d / f"parca-{i + 1}.json"
            p.write_text(json.dumps(parca, ensure_ascii=False, indent=2),
                         encoding="utf-8")
            print(f"  {p} — {len(parca)} belge")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
