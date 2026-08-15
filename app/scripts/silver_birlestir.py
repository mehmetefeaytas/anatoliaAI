"""Gümüş etiket parçalarını birleştirir, DOĞRULAR ve rapor üretir.

İlgili: scripts/silver_parti_hazirla.py (partiyi üretir)
        scripts/silver_parti_bol.py (kümelere böler)
        scripts/gold_schema.py (değer doğrulaması — gold ile AYNI süzgeç)

## Neden doğrulama şart

Etiketleyici bir modeldir ve şemayı ihlal edebilir. Gümüş veri eğitimde
kullanılacaksa ihlal doğrudan modele öğretilir. Bu yüzden her kayıt gold'un
geçtiği süzgeçten geçirilir:

  * `verdict` dört değerden biri mi
  * `fix` ise `gold_value` dolu ve KANONİK mi (`parse_gold_value`)
  * `ok`/`absent`/`unclear` ise `gold_value` BOŞ mu
  * `evidence` belge metninde BİREBİR geçiyor mu (uydurma alıntı kapısı)
  * her (doc_id, field) yalnız BİR kez mi
  * partide istenen hücrelerin tamamı karşılandı mı

Reddedilen kayıt silinmez; `*.reddedilen.jsonl` dosyasına gerekçesiyle yazılır
(CLAUDE.md "silme yok").

## Gümüş ALTIN DEĞİLDİR

Çıktı `data/silver/` altında kalır. `eval/run_eval.py` gold'dan okur; gümüş
veri ölçümde kullanılırsa model kendi çıktısıyla ölçülür.

Kullanım:
    .venv/bin/python -m scripts.silver_birlestir \\
        --parca "data/silver/parca/etiket_*.jsonl" \\
        --parca data/silver/round1_etiketler.jsonl \\
        --parti data/silver/round1_parti.jsonl \\
        --out data/silver/round1_silver.jsonl
"""

from __future__ import annotations

import argparse
import glob
import json
import re
import sys
import unicodedata
from collections import Counter
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from scripts.gold_schema import parse_gold_value

VERDICTS = ("ok", "fix", "absent", "unclear")
BELGE_DIZINI = "data/gold/review/belgeler"

#: Alıntı karşılaştırmasında boşluk/tırnak farkı görmezden gelinir: metin
#: çıkarımında `\n` ve `\xa0` düzleşir, kıvrık tırnak düz tırnağa döner.
_BOSLUK = re.compile(r"\s+")
_TIRNAK = str.maketrans({"’": "'", "‘": "'", "“": '"', "”": '"', " ": " "})


def _duzle(s: str) -> str:
    s = unicodedata.normalize("NFC", s).translate(_TIRNAK)
    return _BOSLUK.sub(" ", s).strip().casefold()


def _metin_yukle(kok: Path) -> dict[str, str]:
    dizin = kok / BELGE_DIZINI
    return {p.stem: _duzle(p.read_text(encoding="utf-8", errors="replace"))
            for p in dizin.glob("*.txt")}


def dogrula(kayit: dict, metinler: dict[str, str]) -> list[str]:
    """Kaydın şema ihlallerini döndürür; boş liste = temiz."""
    hatalar: list[str] = []
    doc = (kayit.get("doc_id") or "").strip()
    alan = (kayit.get("field") or "").strip()
    verdict = (kayit.get("verdict") or "").strip().casefold()
    gold = (kayit.get("gold_value") or "").strip()
    kanit = (kayit.get("evidence") or "").strip()

    if not doc or not alan:
        hatalar.append("doc_id/field bos")
    if verdict not in VERDICTS:
        hatalar.append(f"verdict taninmiyor: {verdict!r}")

    if verdict == "fix":
        if not gold:
            hatalar.append("verdict=fix ama gold_value bos")
        else:
            try:
                parse_gold_value(alan, gold)
            except Exception as exc:  # şema süzgeci gold ile AYNI
                hatalar.append(f"gold_value kanonik degil: {str(exc)[:90]}")
    elif gold:
        hatalar.append(f"verdict={verdict} ama gold_value dolu")

    if kanit:
        metin = metinler.get(doc)
        if metin is None:
            hatalar.append("belge metni bulunamadi")
        elif _duzle(kanit) not in metin:
            hatalar.append("evidence metinde BIREBIR gecmiyor")

    return hatalar


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--parca", action="append", default=[],
                    help="jsonl yolu ya da glob (birden çok kez verilebilir)")
    ap.add_argument("--parti", default="data/silver/round1_parti.jsonl")
    ap.add_argument("--out", default="data/silver/round1_silver.jsonl")
    args = ap.parse_args(argv)

    yollar: list[Path] = []
    for kalip in args.parca:
        yollar += [Path(p) for p in sorted(glob.glob(kalip))]
    if not yollar:
        print("HATA: parça bulunamadı", file=sys.stderr)
        return 1

    metinler = _metin_yukle(_ROOT)

    kabul: dict[tuple[str, str], dict] = {}
    red: list[dict] = []
    cift = 0
    for yol in yollar:
        for satir in yol.read_text(encoding="utf-8").splitlines():
            if not satir.strip():
                continue
            try:
                kayit = json.loads(satir)
            except json.JSONDecodeError as exc:
                red.append({"ham": satir[:200], "hatalar": [f"JSON: {exc}"]})
                continue
            kayit["_kaynak"] = yol.name
            hatalar = dogrula(kayit, metinler)
            if hatalar:
                red.append({**kayit, "hatalar": hatalar})
                continue
            anahtar = (kayit["doc_id"].strip(), kayit["field"].strip())
            if anahtar in kabul:
                cift += 1
                red.append({**kayit, "hatalar": ["ayni hucre birden cok kez"]})
                continue
            kabul[anahtar] = kayit

    # Parti kapsaması: istenen hücrelerin kaçı karşılandı?
    parti_yolu = _ROOT / args.parti
    istenen: set[tuple[str, str]] = set()
    if parti_yolu.exists():
        for s in parti_yolu.read_text(encoding="utf-8").splitlines():
            if s.strip():
                k = json.loads(s)
                istenen |= {(k["doc_id"], a["field"]) for a in k["alanlar"]}

    hedef = _ROOT / args.out
    hedef.parent.mkdir(parents=True, exist_ok=True)
    with hedef.open("w", encoding="utf-8") as fh:
        for anahtar in sorted(kabul):
            fh.write(json.dumps(kabul[anahtar], ensure_ascii=False) + "\n")
    if red:
        red_yolu = hedef.with_suffix(".reddedilen.jsonl")
        with red_yolu.open("w", encoding="utf-8") as fh:
            for r in red:
                fh.write(json.dumps(r, ensure_ascii=False) + "\n")

    dagilim = Counter(k["verdict"].strip().casefold() for k in kabul.values())
    eksik = istenen - set(kabul) if istenen else set()
    fazla = set(kabul) - istenen if istenen else set()

    print(f"parca dosyasi        : {len(yollar)}")
    print(f"KABUL                : {len(kabul)}")
    print(f"RED                  : {len(red)}" + (f"  (cift: {cift})" if cift else ""))
    print(f"verdict dagilimi     : {dict(dagilim.most_common())}")
    if istenen:
        print(f"partide istenen      : {len(istenen)}")
        print(f"  karsilanmayan      : {len(eksik)}")
        print(f"  partide OLMAYAN    : {len(fazla)}")
    print(f"yazildi: {args.out}")
    if red:
        print(f"reddedilenler: {hedef.with_suffix('.reddedilen.jsonl').name}")
        for r in red[:8]:
            print(f"  - {r.get('doc_id', '?')[:40]} · {r.get('field', '?')}: "
                  f"{'; '.join(r['hatalar'])[:100]}")
    return 0 if not eksik else 1


if __name__ == "__main__":
    raise SystemExit(main())
