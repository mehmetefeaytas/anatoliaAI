"""Ön-anotasyon HAVUZUNU bugünkü çıkarıcıyla tazeler — belge kümesine DOKUNMADAN.

İlgili: scripts/preannotate.py (havuzu sıfırdan üretir — ÖRNEKLEMİ DEĞİŞTİRİR)
        scripts/onanotasyon_tazele.py (kardeş araç: inceleme CSV'lerini tazeler)
        scripts/build_gold.py (`kanit_alintisi` — bu havuzun tek kalan tüketicisi)

## Neden ayrı bir araç

`preannotate` havuzu yeniden ÖRNEKLER: korpus büyüdüyse aynı `--seed` ile bile
farklı belge kümesi çıkar ve gold'un `doc_id`'leri havuzda bulunamayıp sessizce
düşer. Bu araç örneklemeye hiç dokunmaz; yalnız var olan belgelerin ALAN
DEĞERLERİNİ günceller. Belge kümesi değişirse yazmayı reddeder.

## Neden şimdi güvenli — daha önce değildi

2026-08-15'e kadar `build_gold`, `verdict=ok` satırında gold DEĞERİNİ bu
havuzdan okuyordu. O yüzden havuzu tazelemek gold'un içeriğini değiştirebilir,
yani κ'nın altındaki zemini oynatabilirdi.

K5 düzeltmesinden sonra `ok` kararı satırın kendi `model_value`'sunu okuyor.
Havuz artık YALNIZ iki şey için okunuyor: belge kimliği/metni ve
`kanit_alintisi`. İkisi de gold değerini değiştiremez. Tazeleme bu yüzden
artık yalnız KANIT kazandırır, hiçbir kararı bozamaz.

## Ölçülen kazanç (2026-08-15)

`gold.round1.json` içinde 49 alan kanıtsızdı. Havuz 4 Ağustos'tan kalmaydı,
CSV'ler 8-9 Ağustos'ta tazelenmişti; `kanit_alintisi` gold değerini havuzun
BAYAT değeriyle eşleştiremediği için kanıt üretemiyordu.

    kanıtlı alan   99/148 (%67)  ->  129/148 (%87)
    kazanan alan   kampanya_suresi 28 · kampanya_kosullari 1 · taksit_sayisi 1

Kalan 19 alan anotatörün `fix` ile YAZDIĞI değerlerdir; çıkarıcı o değeri hiç
üretmediği için kanıtı da yoktur — doğru davranış budur (uydurma alıntı yok).

## Dokunulmayanlar

`campaign_type` ve `campaign_type_confidence` DEĞİŞTİRİLMEZ: sınıflandırıcı
çıktısıdır, `kanit_alintisi` onu kullanmaz ve tazelemenin bir faydası olmaz.
`llm_value` de korunur — bu koşu kural-only'dir, LLM alanını ezmek bilgi kaybı
olurdu.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from collections import Counter
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.extraction.rules.extract import extract_all

# Çıkarıcının ürettiği ve tazelenecek anahtarlar. Listede OLMAYAN anahtarlar
# (llm_value, disagreement) eski değerleriyle korunur.
TAZELENEN = ("value", "raw_value", "confidence", "confidence_source",
             "source_span", "span_start", "span_end", "span_verified",
             "extractor", "rule_value")


def _alan_yuku(f, metin: str) -> dict:
    return {
        "value": f.canonical_value,
        "raw_value": f.raw_value,
        "confidence": f.confidence,
        "confidence_source": f.confidence_source,
        "extractor": "rule",
        "rule_value": f.canonical_value,
        "source_span": f.source_span,
        "span_start": f.span_start,
        "span_end": f.span_end,
        "span_verified": f.verify_span(metin),
    }


def tazele(havuz_yolu: Path, kuru: bool = False) -> dict:
    veri = json.loads(havuz_yolu.read_text(encoding="utf-8"))
    belgeler = veri["docs"]
    onceki_kume = {d["id"] for d in belgeler}

    rapor = {"belge": len(belgeler), "degisen_alan": 0, "eklenen_alan": 0,
             "korunan_alan": 0, "alan_kirilimi": Counter(), "yedek": None}

    for d in belgeler:
        metin = d.get("text") or ""
        if not metin:
            continue
        taze = {f.field_name: f for f in extract_all(metin)}
        eski = d.get("fields") or {}

        # BİRLEŞTİRME, ÜZERİNE YAZMA DEĞİL. Bugünkü çıkarıcının artık üretmediği
        # alanlar KORUNUR. Ölçüldü (2026-08-15): düşürmek 13 kanıt kaybettiriyor
        # (finansman_tutari 9 · vade_ay 2 · masraf_durumu 2), kazanç 30'dan
        # 17'ye iniyor. Eski girdiyi tutmak bir kanıt uydurması değildir:
        # `kanit_alintisi` her çağrıda `text[start:end] == raw_value` ve
        # `span_supports` kontrolünü yeniden yapar; metne uymayan eski girdi
        # zaten kanıt üretemez.
        #
        # Çıkarıcının o alanı artık üretmemesi ayrı bir olgudur ve zaten
        # `run_eval`de FN olarak ölçülür — kanıtı silmek onu ölçmez, gizler.
        yeni: dict[str, dict] = dict(eski)
        for ad, f in taze.items():
            yuk = dict(eski.get(ad) or {})
            eski_deger = yuk.get("value", "__YOK__")
            yuk.update(_alan_yuku(f, metin))
            yeni[ad] = yuk
            if ad not in eski:
                rapor["eklenen_alan"] += 1
                rapor["alan_kirilimi"][ad] += 1
            elif eski_deger != yuk["value"]:
                rapor["degisen_alan"] += 1
                rapor["alan_kirilimi"][ad] += 1
        rapor["korunan_alan"] += len(set(eski) - set(taze))
        d["fields"] = yeni

    # BELGE KÜMESİ DEĞİŞMEZ — bu aracın tek varlık sebebi budur.
    if {d["id"] for d in belgeler} != onceki_kume:
        raise RuntimeError("belge kümesi değişti — yazılmadı")

    veri["tazelendi"] = True
    veri["field_count"] = sum(len(d.get("fields") or {}) for d in belgeler)

    if not kuru:
        yedek = havuz_yolu.with_suffix(havuz_yolu.suffix + ".yedek-tazeleme")
        n = 2
        while yedek.exists():
            yedek = havuz_yolu.with_suffix(f"{havuz_yolu.suffix}.yedek-tazeleme{n}")
            n += 1
        shutil.copy2(havuz_yolu, yedek)
        rapor["yedek"] = str(yedek)
        havuz_yolu.write_text(
            json.dumps(veri, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return rapor


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--havuz", default="data/gold/preannotations.v2.json")
    ap.add_argument("--kuru", action="store_true", help="yazmadan dene")
    args = ap.parse_args(argv)

    r = tazele(Path(args.havuz), args.kuru)
    print(f"belge          : {r['belge']}")
    print(f"degisen alan   : {r['degisen_alan']}")
    print(f"eklenen alan   : {r['eklenen_alan']}")
    print(f"korunan alan   : {r['korunan_alan']}  (bugünkü çıkarıcı üretmiyor)")
    for ad, n in r["alan_kirilimi"].most_common(8):
        print(f"  {ad:22s} {n}")
    if args.kuru:
        print("(kuru koşu — dosya YAZILMADI)")
    elif r["yedek"]:
        print(f"yedek: {Path(r['yedek']).name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
