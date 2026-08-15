"""Şema hatası taşıyan hücrelere onarım kararlarını uygular.

İlgili: build_gold.py (hataları üreten kapı) · lint_review_csv.py
        hakemlik_uygula.py (kardeş araç — UYUŞMAZLIK çözer, bu ŞEMA onarır)
        data/gold/review/_bicim-karti.md (kanonik biçimler)

## Bu araç neyi çözüyor

`build_gold`, `gold_value`'su kanonik biçime çevrilemeyen satırı ATAR. Round1'de
18 satır böyleydi: taksonomi dışı `campaign_type` (`Katılım hesabı`,
`Alışveriş finansmanı`), `fix` deyip düzeltmeyi yazmamış hücreler, `campaign_type`
sütununa yazılmış `hedef_kitle` değerleri, `vade_ay: 0`, para alanına oran.

Bu satırlar bugün gold'a HİÇ girmiyor — anotasyon emeği tamamen kayıp. Araç,
üçüncü bir gözün verdiği şemaya uygun kararı hücreye yazar.

## Hakemlikten farkı — körlük gerekmez

`hakemlik_uygula` iki anotatörün AYRIŞTIĞI hücrelerde çalışır; orada üçüncü
gözün A ve B'yi görmemesi şarttır. Burada tek anotatör vardır, gizlenecek
ikinci karar yoktur. Anotatörün yazdığı ham değer üçüncü göze VERİLİR — niyeti
veridir.

## Üç kapı

1. **Satır kayması kapısı.** Öneri `(dosya, satır)` ile geliyor ama hücre
   `(doc_id, field)` ile DOĞRULANIYOR. İkisi tutmazsa öneri reddedilir.
   Satır numarasına körü körüne yazmak, araya bir satır eklenmişse başka bir
   belgenin kararını ezerdi.
2. **Kanoniklik kapısı.** `fix` önerisinin `gold_value`'su `parse_gold_value`'dan
   geçmezse reddedilir. Aksi hâlde araç, kapatmaya çalıştığı hatanın aynısını
   üretirdi.
3. **Tutarlılık kapısı.** `fix` ⇒ `gold_value` dolu, diğer üçü ⇒ boş.

Reddedilen öneri SESSİZCE atlanmaz; rapora gerekçesiyle yazılır.

## Damga

Değişen her hücrenin `note`'una `#sema-onarimi-round1` düşer. Damgasız
bırakmak, gold'da hangi hücrenin insan kararı hangisinin onarım olduğunu
ayırt edilemez kılardı.
"""
from __future__ import annotations

import argparse
import csv
import json
import shutil
import sys
from collections import Counter
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from scripts.gold_schema import GoldValidationError, parse_gold_value
from scripts.to_review_csv import (
    CSV_DELIMITER,
    CSV_ENCODING,
    CSV_LINETERMINATOR,
)

# Damga — dokunulan her hücrenin `note`'una düşer ve gold'da
# `adjudicated: true` bayrağını tetikler (bkz. `build_gold`). Tek doğruluk
# kaynağı burasıdır; tüketiciler kopyalamaz, içe aktarır.
# Kardeş sabit: `hakemlik_uygula.DAMGA`.
DAMGA = "#sema-onarimi-round1"
GECERLI = ("ok", "fix", "absent", "unclear")
VARSAYILAN_RAPOR = "data/gold/review/_sema-onarimi-round1.md"


def _oku(yol: Path) -> tuple[list[str], list[dict]]:
    with yol.open(encoding=CSV_ENCODING, newline="") as fh:
        okuyucu = csv.DictReader(fh, delimiter=CSV_DELIMITER)
        baslik = [(h or "").lstrip("﻿") for h in (okuyucu.fieldnames or [])]
        return baslik, [{(k or "").lstrip("﻿"): (v or "") for k, v in r.items()}
                        for r in okuyucu]


def _yedekle(yol: Path) -> Path:
    hedef = yol.with_suffix(yol.suffix + ".yedek-sema-onarimi-round1")
    n = 2
    while hedef.exists():
        hedef = yol.with_suffix(f"{yol.suffix}.yedek-sema-onarimi-round1{n}")
        n += 1
    shutil.copy2(yol, hedef)
    return hedef


def _dogrula(oneri: dict, satir: dict) -> str | None:
    """Öneri uygulanabilir mi — değilse RET gerekçesi."""
    verdict = (oneri.get("verdict") or "").strip().casefold()
    gold = (oneri.get("gold_value") or "").strip()
    alan = (oneri.get("field") or "").strip()

    if verdict not in GECERLI:
        return f"verdict {verdict!r} tanınmıyor"
    if (satir.get("doc_id") or "").strip() != (oneri.get("doc_id") or "").strip():
        return (f"satır kayması: dosyada {satir.get('doc_id')!r}, "
                f"öneride {oneri.get('doc_id')!r}")
    if (satir.get("field") or "").strip() != alan:
        return (f"alan uyuşmuyor: dosyada {satir.get('field')!r}, "
                f"öneride {alan!r}")
    if verdict == "fix" and not gold:
        return "fix ama gold_value boş — kapatmaya çalıştığı hatanın aynısı"
    if verdict != "fix" and gold:
        return f"{verdict} ama gold_value dolu ({gold[:40]!r})"
    if verdict == "fix":
        try:
            parse_gold_value(alan, gold)
        except GoldValidationError as exc:
            return f"gold_value kanonik değil: {exc}"
    if not (oneri.get("note") or "").strip():
        return "gerekçe (note) yok"
    return None


def uygula(review_dizini: Path, oneri_yolu: Path, kuru: bool = False) -> dict:
    oneriler = [json.loads(s) for s in
                oneri_yolu.read_text(encoding="utf-8").splitlines() if s.strip()]

    dosyalar: dict[str, tuple[Path, list[str], list[dict]]] = {}
    rapor: dict = {"oneri": len(oneriler), "degisiklik": [], "reddedilen": [],
                   "yedek": []}

    for oneri in oneriler:
        ad = (oneri.get("dosya") or "").strip()
        no = int(oneri.get("satir") or 0)
        if ad not in dosyalar:
            yol = review_dizini / (ad + ".csv")
            if not yol.exists():
                rapor["reddedilen"].append({"oneri": oneri,
                                            "gerekce": f"dosya yok: {yol}"})
                continue
            baslik, satirlar = _oku(yol)
            dosyalar[ad] = (yol, baslik, satirlar)
        _yol, _baslik, satirlar = dosyalar[ad]

        # CSV satır numarası 1 = başlık; veri satırları 2'den başlar.
        dizin = no - 2
        if not 0 <= dizin < len(satirlar):
            rapor["reddedilen"].append({"oneri": oneri,
                                        "gerekce": f"satır {no} dosyada yok"})
            continue
        satir = satirlar[dizin]

        gerekce = _dogrula(oneri, satir)
        if gerekce:
            rapor["reddedilen"].append({"oneri": oneri, "gerekce": gerekce})
            continue

        eski = {s: satir.get(s, "") for s in ("verdict", "gold_value", "note")}
        satir["verdict"] = (oneri["verdict"] or "").strip().casefold()
        satir["gold_value"] = (oneri.get("gold_value") or "").strip()
        not_ = (satir.get("note") or "").strip()
        damga = f"{DAMGA} {(oneri.get('note') or '').strip()}"
        satir["note"] = f"{not_} | {damga}".strip(" |") if not_ else damga

        rapor["degisiklik"].append({
            "dosya": ad, "satir": no,
            "anahtar": (satir.get("doc_id", ""), satir.get("field", "")),
            "eski": eski,
            "yeni": {s: satir.get(s, "") for s in ("verdict", "gold_value", "note")},
        })

    if not kuru and rapor["degisiklik"]:
        for ad, (yol, baslik, satirlar) in dosyalar.items():
            if not any(d["dosya"] == ad for d in rapor["degisiklik"]):
                continue
            rapor["yedek"].append(str(_yedekle(yol)))
            with yol.open("w", encoding=CSV_ENCODING, newline="") as fh:
                y = csv.DictWriter(fh, fieldnames=baslik, delimiter=CSV_DELIMITER,
                                   lineterminator=CSV_LINETERMINATOR)
                y.writeheader()
                y.writerows(satirlar)
    return rapor


def render(rapor: dict) -> str:
    d = rapor["degisiklik"]
    dosya = Counter(x["dosya"] for x in d)
    karar = Counter(x["yeni"]["verdict"] for x in d)

    s = ["# Round1 Şema Onarımı", "",
         "> `scripts/sema_onarimi_uygula.py` üretti. Bu hücrelerde anotatörün "
         "yazdığı değer kanonik biçime çevrilemiyordu ve `build_gold` satırı "
         "ATIYORDU — yani anotasyon emeği gold'a hiç ulaşmıyordu.", "",
         "## Bu bir hakemlik DEĞİL", "",
         "Hücrelerde tek anotatör var; gizlenecek ikinci karar yok. Üçüncü göze "
         "anotatörün yazdığı ham değer de verildi (niyeti veridir, bağlayıcı "
         "değildir). Uyuşmazlık çözümü için `_hakemlik-degisim-round1.md`'ye "
         "bakın.", "",
         "## Sayılar", "",
         f"- öneri: **{rapor['oneri']}**",
         f"- uygulanan: **{len(d)}**",
         f"- reddedilen: **{len(rapor['reddedilen'])}**", ""]

    if dosya:
        s += ["| dosya | hücre |", "|---|---:|"]
        s += [f"| `{k}` | {v} |" for k, v in sorted(dosya.items())]
        s += [""]
    if karar:
        s += ["| yeni karar | adet |", "|---|---:|"]
        s += [f"| `{k}` | {v} |" for k, v in sorted(karar.items())]
        s += [""]

    if rapor["reddedilen"]:
        s += ["## Reddedilen öneriler", "",
              "Sessizce atlanmadı — her biri gerekçesiyle burada.", ""]
        for r in rapor["reddedilen"]:
            o = r["oneri"]
            s.append(f"- `{o.get('dosya')}`:{o.get('satir')} "
                     f"[{o.get('doc_id')} · {o.get('field')}] — {r['gerekce']}")
        s += [""]

    s += ["## Değişen hücreler", ""]
    for x in d:
        doc, alan = x["anahtar"]
        s += [f"### `{x['dosya']}`:{x['satir']} — {doc} · `{alan}`", "",
              f"- **önce:** `{x['eski']['verdict']}` / "
              f"`{x['eski']['gold_value'] or '(boş)'}`",
              f"- **sonra:** `{x['yeni']['verdict']}` / "
              f"`{x['yeni']['gold_value'] or '(boş)'}`",
              f"- **gerekçe:** {x['yeni']['note']}", ""]

    if rapor["yedek"]:
        s += ["## Yedekler", ""] + [f"- `{y}`" for y in rapor["yedek"]] + [""]
    return "\n".join(s)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--review", default="data/gold/review",
                    help="inceleme CSV'lerinin dizini")
    ap.add_argument("--oneri", default="data/gold/review/_sema_onarimi.jsonl",
                    help="onarım önerileri (JSONL)")
    ap.add_argument("--rapor", default=VARSAYILAN_RAPOR)
    ap.add_argument("--kuru", action="store_true", help="yazmadan dene")
    args = ap.parse_args(argv)

    rapor = uygula(Path(args.review), Path(args.oneri), args.kuru)
    print(f"oneri        : {rapor['oneri']}")
    print(f"UYGULANAN    : {len(rapor['degisiklik'])}")
    print(f"reddedilen   : {len(rapor['reddedilen'])}")
    for r in rapor["reddedilen"]:
        o = r["oneri"]
        print(f"  RET {o.get('dosya')}:{o.get('satir')} — {r['gerekce']}")
    if args.kuru:
        print("(kuru koşu — dosya YAZILMADI)")
        return 0
    Path(args.rapor).write_text(render(rapor), encoding="utf-8")
    print(f"rapor: {args.rapor}")
    for y in rapor["yedek"]:
        print(f"yedek: {Path(y).name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
