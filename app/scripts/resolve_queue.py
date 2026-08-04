"""İnsan kuyruğunu sınıf kurallarına göre çözer.

İlgili: ../docs/kampanya-turu-sinif-kurallari.md (kararların gerekçesi)
        ../src/extraction/silver/consensus.py (kuyruğu üreten uzlaşma)

## Ne yapıyor

`data/silver/queue.jsonl` içindeki belgeleri `docs/kampanya-turu-sinif-kurallari.md`
kararlarına göre çözer. Kural KESİN olanları çözer, olmayanları kuyrukta
bırakır — otomatik çözülemeyeni zorlamak, kuyruğun var olma amacını ortadan
kaldırır.

## İki karar sınıfı

**(A) Ürün ailesi kararı** — Kural 3. Rotatif kredi limitleri (KMH, Ek Hesap,
Artı Para, Esnek Hesap, Cepte/Sky Limit) `Finansman`; taksitli nakit avans
`İhtiyaç Finansmanı`. Gerekçe §17: rotatif limitin vadesi/taksiti yok, taksitli
bir tüketici kredisiyle aynı tabloda kıyaslanamaz.

**(B) Kanıt zayıf ama etiket iki bağımsız oyla aynı** — bu belgeler gümüşe
alınır ve `evidence_weak` işaretlenir. Gerekçe: kanıt kapısı UYDURMAYI
engellemek için var; denetleyiciler alıntının belgede bulunduğunu doğruladı,
yalnızca yetersiz buldu. İki bağımsız oyun aynı etikette buluşmasını, kötü
seçilmiş bir alıntı yüzünden çöpe atmak bilgi kaybıdır. Alıntı sonradan
düzeltilebilir; işaret bunun için duruyor.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import Counter
from typing import Any, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.extraction.silver.consensus import (
    CONF_MEDIUM,
    STATUS_REJECT,
    STATUS_SILVER,
)

# --------------------------------------------------------------------------- #
# Kural 3 — ürün ailesi imzaları
# --------------------------------------------------------------------------- #

# ROTATİF (vadesiz) kredi limitleri -> Finansman.
# Belge adında ya da başlığında bu imzalar varsa ürün rotatiftir.
_ROTATIF = re.compile(
    r"kredili[\s-]*mevduat|(^|[\s-])kmh([\s-]|$)|ek[\s-]*hesap|art[ıi][\s-]*para"
    r"|esnek[\s-]*hesap|cepte[\s-]*limit|sky[\s-]*limit|kurtaran[\s-]*hesap",
    re.IGNORECASE)

# TAKSİTLİ NAKİT AVANS -> İhtiyaç Finansmanı (vade + taksit + oran ilan eder).
# `_ROTATIF`'ten SONRA denenir: "taksitli esnek hesap" rotatiftir.
_TAKSITLI_AVANS = re.compile(
    r"taksitli[\s-]*(nakit[\s-]*)?avans|taksitli[\s-]*nakit", re.IGNORECASE)

# TAKSONOMİ DIŞI ürünler -> null (Kural 2)
_TAKSONOMI_DISI = re.compile(
    r"(^|[\s-])bes([\s-]|$)|bireysel[\s-]*emeklilik|emeklilik[\s-]*kampanya"
    r"|dask|kasko|hayat[\s-]*sigorta|konut[\s-]*sigorta|sigortas[ıi]nda",
    re.IGNORECASE)

# TİCARİ / bireysel olmayan -> Finansman (Kural 3a)
_TICARI = re.compile(
    r"ticari|kob[ıi]|i[şs]letme|tar[ıi]m|[çc]ift[çc]i|proje|d[ıi][şs][\s-]*ticaret"
    r"|leasing|kiralama|y[öo]netim[\s-]*kredisi|esnaf",
    re.IGNORECASE)

# BİREYSEL TAKSİTLİ TÜKETİCİ KREDİSİ aileleri -> İhtiyaç Finansmanı (Kural 3).
# Bunlar Yapı Kredi'nin ürün adları; doc_id sayısal olduğu için BAŞLIKTAN
# okunuyor (ölçüm: kalan 17 kuyruk belgesinin 12'si `detay-<sayı>` biçimindeydi
# ve doc_id ürün hakkında hiçbir şey söylemiyordu).
_TUKETICI_KREDI = re.compile(
    r"al[ıi][şs]veri[şs][\s-]*kredisi|kapama[\s-]*ko[şs]ullu|[öo]zel[\s-]*m[üu][şs]teri"
    r"[\s-]*kredisi|t[üu]ketici[\s-]*kredisi|ihtiya[çc][\s-]*kredisi"
    r"|anneler[\s-]*g[üu]n[üu]ne[\s-]*[öo]zel[\s-]*kredi",
    re.IGNORECASE)

# KART EDİNİMİ kapısı -> Kart (Kural 5). "ek kart alın", "yeni ... kredi
# kartıyla", "kart başvurusu" — ödül puan olsa bile sınıf Kart.
_KART_EDINIMI = re.compile(
    r"ek[\s-]*kart|kart[\s-]*ba[şs]vuru|yeni[\s-]*\w*[\s-]*kredi[\s-]*kart[ıi]"
    r"|kredi[\s-]*kart[ıi]yla|kart[\s-]*kampanyas[ıi]|kart[\s-]*al[ıi]n",
    re.IGNORECASE)

# HARCAMAYA bağlı puan -> Alışveriş Puanı (Kural 5). `_KART_EDINIMI`'nden
# SONRA denenir: "ek kart alın, Worldpuan kazanın" kart edinimidir.
_HARCAMA_PUANI = re.compile(
    r"worldpuan[\s-]*kampanyas[ıi]|puan[\s-]*kampanyas[ıi]|chip[\s-]*para"
    r"|maxipuan|bonus[\s-]*kampanyas[ıi]", re.IGNORECASE)

# İNDİRİM -> Kart (Kural 5).
_INDIRIM = re.compile(r"indirim", re.IGNORECASE)

# MAAŞ / NAKİT PROMOSYONU -> null (Kural 2: ürün değil, tek seferlik ödeme)
_PROMOSYON = re.compile(r"promosyon", re.IGNORECASE)

# MEVDUAT / birikim -> Yatırım Ürünü. "hoş geldin faizi" bir mevduat ürününün
# getirisidir; Kural 4 gereği "yeni müşteri" koşulu sınıfı değiştirmez.
_MEVDUAT = re.compile(
    r"ho[şs][\s-]*geldin[\s-]*faiz|mevduat|vadeli[\s-]*hesap|birikim"
    r"|alt[ıi]n[\s-]*hesab|fon", re.IGNORECASE)

RESOLVE_RULE3 = "kural3_urun_ailesi"
RESOLVE_RULE4 = "kural4_urun_kosulu_yener"
RESOLVE_RULE5 = "kural5_kart_vs_puan"
RESOLVE_RULE2 = "kural2_taksonomi_disi"
RESOLVE_EVIDENCE = "kanit_zayif_etiket_saglam"
UNRESOLVED = "insan_karari_gerekli"


def load_titles(path: str) -> dict[str, str]:
    """doc_id -> başlık. Yapı Kredi doc_id'leri sayısal olduğu için şart."""
    out: dict[str, str] = {}
    if not os.path.exists(path):
        return out
    for line in open(path, encoding="utf-8"):
        row = json.loads(line)
        out[row["doc_id"]] = row.get("title") or ""
    return out


def _signature(row: dict[str, Any], titles: dict[str, str]) -> str:
    """Karar için kullanılacak metin: doc_id + BAŞLIK + kanıt.

    Tam metin KULLANILMAZ: "Ek Hesap" ifadesi çoğu bankanın gezinme menüsünde
    geçiyor; tam metinde arayan bir kural her belgeyi rotatif sayardı. Aynı
    tuzak `split_trainable`'da da ölçülmüştü: tam metinde arayan blog kuralı
    39 gerçek kampanyayı KVKK altbilgisi yüzünden eliyordu.

    BAŞLIK sonradan eklendi (ölçüm: ilk koşuda kalan 17 belgenin 12'si
    `yapi-kredi--detay-<sayı>` biçimindeydi ve doc_id ürün hakkında hiçbir şey
    söylemiyordu — kural sağlamdı, sinyal kaynağı eksikti).
    """
    return (f"{row['doc_id']} {titles.get(row['doc_id'], '')} "
            f"{row.get('evidence') or ''}")


def resolve(row: dict[str, Any],
            titles: Optional[dict[str, str]] = None) -> tuple[Optional[str], str, str]:
    """(etiket, durum, cozum_gerekcesi) döndürür. etiket None -> reddedildi.

    Kapı sırası `docs/kampanya-turu-sinif-kurallari.md` §"Uygulama sırası" ile
    aynıdır ve sıra ANLAMLIDIR: taksonomi kapıları sınıf kapılarından önce
    gelir, çünkü "hangi sınıf" sorusu ancak taksonomi-içi tek bir ürün varsa
    anlamlı.
    """
    sig = _signature(row, titles or {})
    votes = row.get("votes") or {}
    labeler = votes.get("labeler")
    verifier = votes.get("verifier")

    # Kural 3 — ürün ailesi. Taksonomi kapısından ÖNCE gelir.
    #
    # SIRA DÜZELTMESİ (2026-08-04, kendi hatam ölçüldü): taksonomi kapısı önce
    # koşulunca şu belge yanlış reddedildi:
    #   "BES ile %0 faiz oranlı 25.000 TL Taksitli Artı Para fırsatı | Akbank"
    # Burada BES **uygunluk koşulu**, satılan ürün Taksitli Artı Para. Kural 1
    # koşulun sınıfı belirlemediğini söylüyor; taksonomi kapısını öne almak o
    # kuralı sessizce çiğniyordu. Somut ve taksonomi-İÇİ bir ürün adlandıran
    # desen, taksonomi-DIŞI bir anmayı yener.
    #
    # Rotatif kontrolü avanstan ÖNCE: "taksitli esnek hesap" rotatif bir ürün.
    if _ROTATIF.search(sig):
        return ("Finansman", STATUS_SILVER, RESOLVE_RULE3)
    if _TAKSITLI_AVANS.search(sig) or _TUKETICI_KREDI.search(sig):
        return ("İhtiyaç Finansmanı", STATUS_SILVER, RESOLVE_RULE3)

    # Kural 2 — ortada somut bir taksonomi-içi ürün YOKSA taksonomi dışıdır.
    if _TAKSONOMI_DISI.search(sig) or _PROMOSYON.search(sig):
        return (None, STATUS_REJECT, RESOLVE_RULE2)
    if _TICARI.search(sig) and labeler in ("Finansman", "İhtiyaç Finansmanı"):
        return ("Finansman", STATUS_SILVER, RESOLVE_RULE3)

    # Kural 4 — satılan ürün mevduatsa "yeni müşteri" koşulu sınıfı değiştirmez.
    if _MEVDUAT.search(sig):
        return ("Yatırım Ürünü", STATUS_SILVER, RESOLVE_RULE4)

    # Kural 5 — kart edinimi puan ödülünü YENER; sıra bu yüzden sabit.
    if _KART_EDINIMI.search(sig):
        return ("Kart", STATUS_SILVER, RESOLVE_RULE5)
    if _HARCAMA_PUANI.search(sig):
        return ("Alışveriş Puanı", STATUS_SILVER, RESOLVE_RULE5)
    if _INDIRIM.search(sig):
        return ("Kart", STATUS_SILVER, RESOLVE_RULE5)

    # (B) Kanıt zayıf ama iki bağımsız oy aynı etikette buluştu.
    if labeler and labeler == verifier:
        return (labeler, STATUS_SILVER, RESOLVE_EVIDENCE)

    return (labeler, "queue", UNRESOLVED)


def main(argv: Optional[list[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="İnsan kuyruğunu kurallarla çöz")
    ap.add_argument("--queue", default="data/silver/queue.jsonl")
    ap.add_argument("--silver", default="data/silver/silver.jsonl")
    ap.add_argument("--trainable", default="data/silver/trainable.jsonl",
                    help="baslik kaynagi; Yapi Kredi doc_id'leri sayisal")
    ap.add_argument("--out-dir", default="data/silver")
    ap.add_argument("--apply", action="store_true",
                    help="çözülenleri silver.jsonl'a EKLE (varsayılan: kuru koşu)")
    args = ap.parse_args(argv)

    titles = load_titles(args.trainable)
    rows = [json.loads(line) for line in open(args.queue, encoding="utf-8")]
    cozulen: list[dict[str, Any]] = []
    reddedilen: list[dict[str, Any]] = []
    kalan: list[dict[str, Any]] = []
    sayim: Counter[str] = Counter()

    for row in rows:
        label, status, why = resolve(row, titles)
        sayim[why] += 1
        rec = dict(row)
        rec["resolution"] = why
        if status == STATUS_SILVER:
            rec["label"] = label
            rec["status"] = STATUS_SILVER
            rec["confidence"] = CONF_MEDIUM
            if why == RESOLVE_EVIDENCE:
                rec["evidence_weak"] = True
            cozulen.append(rec)
        elif status == STATUS_REJECT:
            rec["label"] = None
            rec["status"] = STATUS_REJECT
            reddedilen.append(rec)
        else:
            kalan.append(rec)

    print(f"kuyruk {len(rows)} -> cozulen {len(cozulen)}, "
          f"reddedilen {len(reddedilen)}, kalan {len(kalan)}")
    for why, n in sayim.most_common():
        print(f"  {why:32} {n}")
    if cozulen:
        print("\nCozulen siniflar:", dict(Counter(r["label"] for r in cozulen)))
    if kalan:
        print("\nInsan karari gerekenler:")
        for r in kalan:
            v = r.get("votes") or {}
            print(f"  {r['doc_id'][:58]}")
            print(f"      oneri={v.get('labeler')} denetci={v.get('verifier')}")

    if not args.apply:
        print("\n(kuru kosu — yazmak icin --apply)")
        return 0

    os.makedirs(args.out_dir, exist_ok=True)
    with open(args.silver, "a", encoding="utf-8") as fh:
        for r in cozulen:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    for name, data in (("queue.jsonl", kalan),
                       ("rejected_from_queue.jsonl", reddedilen)):
        with open(os.path.join(args.out_dir, name), "w", encoding="utf-8") as fh:
            for r in data:
                fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"\nyazildi: silver.jsonl +{len(cozulen)}, "
          f"queue.jsonl={len(kalan)}, rejected_from_queue.jsonl={len(reddedilen)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
