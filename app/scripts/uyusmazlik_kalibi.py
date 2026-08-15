"""A–B uyuşmazlıklarını KALIPLARA ayırır: κ kaybının ne kadarı gerçek anlam farkı?

İlgili: scripts/report_iaa.py (κ'nın kaynağı — jeton mantığı oradan alınır)
        data/gold/ANNOTATION_GUIDE.md §3 (verdict anlamları)
        data/gold/review/_kalibrasyon-sonucu.md (aynı analizin round0 hâli)

## Neden gerekli

Cohen κ **kararı** ölçer (`ok`/`fix`/`absent`/`unclear`), ortaya çıkan **değeri**
değil. İki anotatör aynı sonuca varıp farklı etiket kullandığında κ düşer ama
gold bozulmaz. Round0'da bu fark ölçülmüştü: yalnız `absent`/`ok` karışıklığı
düzeltilince Fleiss κ 0,051 -> 0,268 çıktı, Krippendorff α **kılı kıpırdamadı**
(0,575). α'nın sabit kalması kanıttır — kimse fikrini değiştirmedi.

Bu betik aynı ayrımı round1 için yapar ve her uyuşmazlığı şu kalıplardan birine
koyar:

  `etiket-karisikligi`  efektif gold DEĞERİ aynı, yalnız verdict farklı
  `bicim-farki`         değer aynı ama yazımı farklı (150000 vs {"value":…})
  `yazim-hatasi`        değer neredeyse aynı (tek harf/karakter)
  `kapsam-farki`        biri değer yazmış, diğeri "yok" demiş
  `gercek-fark`         değerler gerçekten ayrışıyor (24 ay vs 36 ay)

**Bu betik CSV'ye YAZMAZ.** Hakemlik kararı insanındır; çıktı bir tartışma
listesidir (`onarim_recetesi.py` ile aynı ilke).

Kullanım:
    .venv/bin/python -m scripts.uyusmazlik_kalibi \\
        data/gold/review/round1_A.csv data/gold/review/round1_B.csv \\
        --out data/gold/uyusmazlik_kaliplari_round1.md
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Optional

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from scripts.gold_schema import parse_gold_value
from scripts.report_iaa import ABSENT_TOKEN, row_value_token, row_verdict
from scripts.to_review_csv import CSV_DELIMITER, CSV_ENCODING

VARSAYILAN_CIKTI = "data/gold/uyusmazlik_kaliplari_round1.md"

#: Yazım hatası aramanın anlamlı olduğu en kısa değer. Bunun altında bir
#: karakter farkı ayrı bir DEĞER demektir (`24` / `36`), yazım hatası değil.
_YAZIM_ASGARI_UZUNLUK = 8


def _sayisal(s: str) -> bool:
    """Değer bir sayı mı — `1.500,00` ve `%2,05` gibi TR biçimleri dahil."""
    temiz = s.strip().lstrip("%").replace(".", "").replace(",", "").replace(" ", "")
    return temiz.isdigit()


def _oku(yol: Path) -> dict[tuple[str, str], dict]:
    with yol.open(encoding=CSV_ENCODING, newline="") as fh:
        return {
            ((r.get("doc_id") or "").strip(), (r.get("field") or "").strip()): r
            for r in csv.DictReader(fh, delimiter=CSV_DELIMITER)
        }


def _sayi_duzle(deger):
    """`150000.0` -> `150000`. Aynı değerin int/float yazımı ayrışmasın.

    `parse_gold_value` girdiye göre bazen float bazen int üretir (`"150000"`
    metni float'a, JSON'daki `150000` int'e çözülür). Düzleştirilmezse aynı
    tutar iki farklı jetona serileşir ve `bicim-farki` yerine `gercek-fark`
    sayılır — kalıp raporunu doğrudan yanıltır.
    """
    if isinstance(deger, bool):
        return deger
    if isinstance(deger, float) and deger.is_integer():
        return int(deger)
    if isinstance(deger, dict):
        return {k: _sayi_duzle(v) for k, v in deger.items()}
    if isinstance(deger, list):
        return [_sayi_duzle(v) for v in deger]
    return deger


def _kanonik(alan: str, jeton: Optional[str]):
    """Jetonu kanonik değere çevirir; çevrilemezse ham jetonu döndürür.

    `parse_gold_value` TEK değer döndürür ve okunamayan değerde
    `GoldValidationError` fırlatır — hata bir dönüş değeri DEĞİLDİR.
    """
    if jeton is None or jeton == ABSENT_TOKEN:
        return jeton
    try:
        return json.dumps(_sayi_duzle(parse_gold_value(alan, jeton)),
                          sort_keys=True, ensure_ascii=False)
    except Exception:
        # Ayrıştırıcı reddederse ham jeton kalır — kanonikleştirilemeyen değer
        # de bir bilgidir, uyuşmazlık listesinden düşürülmez.
        return jeton


def _mesafe(a: str, b: str) -> int:
    """Levenshtein — yazım hatasını gerçek farktan ayırmak için."""
    if a == b:
        return 0
    onceki = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        simdiki = [i]
        for j, cb in enumerate(b, 1):
            simdiki.append(min(onceki[j] + 1, simdiki[j - 1] + 1,
                               onceki[j - 1] + (ca != cb)))
        onceki = simdiki
    return onceki[-1]


def siniflandir(alan: str, sat_a: dict, sat_b: dict) -> tuple[str, str]:
    """Uyuşmazlığı bir kalıba koyar; (kalıp, açıklama) döndürür."""
    va, vb = row_verdict(sat_a), row_verdict(sat_b)
    ta, tb = row_value_token(sat_a), row_value_token(sat_b)

    if "unclear" in (va, vb):
        return "unclear-tarafi", f"biri karar veremedi (A={va}, B={vb})"

    if ta == tb:
        return "etiket-karisikligi", f"ayni deger, farkli karar (A={va}, B={vb})"

    ka, kb = _kanonik(alan, ta), _kanonik(alan, tb)
    if ka == kb:
        return "bicim-farki", "ayni deger, farkli yazim (kanonikte esitleniyor)"

    if ABSENT_TOKEN in (ta, tb):
        return "kapsam-farki", "biri deger yazdi, digeri 'metinde yok' dedi"

    # Yazım hatası YALNIZ uzun metin değerlerinde aranır. Kısa/sayısal
    # değerlerde mesafe eşiği felaket olur: `24` ile `36` arasındaki mesafe de
    # 2'dir ama bunlar iki ayrı vadedir, bir harf hatası değil.
    if (isinstance(ta, str) and isinstance(tb, str)
            and not _sayisal(ta) and not _sayisal(tb)
            and min(len(ta), len(tb)) >= _YAZIM_ASGARI_UZUNLUK):
        d = _mesafe(ta.casefold(), tb.casefold())
        if d and d <= max(1, min(len(ta), len(tb)) // 10):
            return "yazim-hatasi", f"karakter farki (mesafe={d})"

    return "gercek-fark", "degerler gercekten ayrisiyor"


def analiz(a_yolu: Path, b_yolu: Path) -> dict:
    A, B = _oku(a_yolu), _oku(b_yolu)
    ortak = sorted(set(A) & set(B))

    kaliplar: dict[str, list[dict]] = defaultdict(list)
    ikisi_dolu = 0
    for anahtar in ortak:
        sa, sb = A[anahtar], B[anahtar]
        va, vb = row_verdict(sa), row_verdict(sb)
        if va is None or vb is None:
            continue
        ikisi_dolu += 1
        if va == vb and row_value_token(sa) == row_value_token(sb):
            continue
        kalip, aciklama = siniflandir(anahtar[1], sa, sb)
        kaliplar[kalip].append({
            "doc_id": anahtar[0], "field": anahtar[1],
            "A_verdict": va, "B_verdict": vb,
            "A_deger": row_value_token(sa), "B_deger": row_value_token(sb),
            "aciklama": aciklama,
        })

    return {"ikisi_dolu": ikisi_dolu, "kaliplar": dict(kaliplar),
            "a": str(a_yolu), "b": str(b_yolu)}


ZARARSIZ = ("etiket-karisikligi", "bicim-farki", "yazim-hatasi")

BASLIK = {
    "etiket-karisikligi": "Etiket karışıklığı — aynı değer, farklı karar",
    "bicim-farki": "Biçim farkı — aynı değer, farklı yazım",
    "yazim-hatasi": "Yazım hatası — tek/iki karakter",
    "kapsam-farki": "Kapsam farkı — biri değer yazdı, diğeri 'yok' dedi",
    "gercek-fark": "GERÇEK anlam farkı — hakemlik şart",
    "unclear-tarafi": "Bir taraf karar veremedi (`unclear`)",
}


def render(sonuc: dict) -> str:
    kaliplar = sonuc["kaliplar"]
    toplam = sum(len(v) for v in kaliplar.values())
    zararsiz = sum(len(kaliplar.get(k, [])) for k in ZARARSIZ)

    s = ["# Round1 A–B Uyuşmazlık Kalıpları", "",
         "> `scripts/uyusmazlik_kalibi.py` üretti. Bu dosya bir TARTIŞMA "
         "listesidir; hiçbir karar otomatik uygulanmaz.", "",
         f"- Karşılaştırılan: `{Path(sonuc['a']).name}` ↔ `{Path(sonuc['b']).name}`",
         f"- İkisinin de karar verdiği satır: **{sonuc['ikisi_dolu']}**",
         f"- Uyuşmazlık: **{toplam}**", "",
         "## Kalıp dağılımı", "",
         "| Kalıp | Adet | Gold'u bozar mı |", "|---|---:|---|"]

    for kalip in ("etiket-karisikligi", "bicim-farki", "yazim-hatasi",
                  "kapsam-farki", "gercek-fark", "unclear-tarafi"):
        n = len(kaliplar.get(kalip, []))
        if not n:
            continue
        bozar = "hayır — κ'yı düşürür, değeri değiştirmez" if kalip in ZARARSIZ \
            else ("evet — iki farklı gold değeri" if kalip != "unclear-tarafi"
                  else "hayır — metrik dışı")
        s.append(f"| `{kalip}` | {n} | {bozar} |")

    oran = 100 * zararsiz / toplam if toplam else 0
    s += ["", f"**{zararsiz}/{toplam} uyuşmazlık (%{oran:.0f}) aynı gold değerini "
          f"üretiyor** — κ'yı düşüren ama gold'u bozmayan kalıplar. Kalan "
          f"{toplam - zararsiz} tanesi gerçek karar farkıdır ve hakemliğe düşer.", ""]

    # Hangi ALAN κ'yı yiyor — kılavuz revizyonu buraya odaklanır.
    bozan = [k for kalip, kayitlar in kaliplar.items() if kalip not in ZARARSIZ
             and kalip != "unclear-tarafi" for k in kayitlar]
    if bozan:
        alan_sayim = Counter(k["field"] for k in bozan)
        s += ["## Hangi alan κ'yı yiyor", "",
              "Gold'u gerçekten bozan uyuşmazlıkların alan dağılımı. Kılavuz "
              "revizyonu bu sıraya göre yapılır — en üstteki alan en çok "
              "anotatör ayrıştıran alandır.", "",
              "| Alan | Bozan uyuşmazlık | Payı |", "|---|---:|---:|"]
        for f, n in alan_sayim.most_common():
            s.append(f"| `{f}` | {n} | %{100*n/len(bozan):.0f} |")
        s.append("")

        # Kapsam farkının YÖNÜ: bir anotatör sistematik olarak mı reddediyor?
        kapsam = kaliplar.get("kapsam-farki", [])
        if kapsam:
            a_deger = sum(1 for k in kapsam if k["A_deger"] != ABSENT_TOKEN)
            s += ["### Kapsam farkının yönü", "",
                  f"- A değer yazdı / B 'yok' dedi: **{a_deger}**",
                  f"- A 'yok' dedi / B değer yazdı: **{len(kapsam) - a_deger}**", "",
                  "Tek yönlü bir yığılma, bir anotatörün modelin çıktısını "
                  "sistematik olarak daha kolay kabul ettiğini (ya da reddettiğini) "
                  "gösterir; bu bir kişi farkı değil, **eşik tanımının eksikliğidir** "
                  "(ANNOTATION_GUIDE §4.13/8 — değer bu kampanyaya mı ait?).", ""]

    for kalip, kayitlar in sorted(kaliplar.items(),
                                  key=lambda kv: -len(kv[1])):
        s += [f"## {BASLIK.get(kalip, kalip)} ({len(kayitlar)})", "",
              "| Belge | Alan | A | B | Not |", "|---|---|---|---|---|"]
        for k in kayitlar:
            ad = f"{k['A_verdict']} `{str(k['A_deger'])[:40]}`"
            bd = f"{k['B_verdict']} `{str(k['B_deger'])[:40]}`"
            s.append(f"| `{k['doc_id'][:45]}` | `{k['field']}` | {ad} | {bd} "
                     f"| {k['aciklama']} |")
        s.append("")

    return "\n".join(s)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("csvler", nargs=2)
    ap.add_argument("--out", default=VARSAYILAN_CIKTI)
    args = ap.parse_args(argv)

    sonuc = analiz(Path(args.csvler[0]), Path(args.csvler[1]))
    (_ROOT / args.out).write_text(render(sonuc), encoding="utf-8")

    sayim = Counter({k: len(v) for k, v in sonuc["kaliplar"].items()})
    toplam = sum(sayim.values())
    zararsiz = sum(sayim.get(k, 0) for k in ZARARSIZ)
    print(f"ikisi de karar verdi : {sonuc['ikisi_dolu']}")
    print(f"uyusmazlik           : {toplam}")
    for k, n in sayim.most_common():
        print(f"  {k:22s} {n:3d}")
    print(f"\nGOLD'U BOZMAYAN      : {zararsiz}/{toplam} "
          f"(%{100*zararsiz/max(toplam,1):.0f})")
    print(f"rapor: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
