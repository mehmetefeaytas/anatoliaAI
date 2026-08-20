"""Çift-anlık-görüntü (snapshot) taraması — canlı belgeler-arası çelişki/tarihçe arayışı.

Bağlam: `src/comparison/contradiction.py` docstring'i 849 belgelik 2026-07-30
anlık görüntüsünde doğrulanmış belgeler-arası çelişki SIFIR olduğunu kaydediyor,
sebebi de ölçülmüş: aynı `source_url`'i paylaşan 32 çift belgenin metni o TEK
anlık görüntüde byte-özdeş. Modül kendi docstring'inde şu öneriyi bırakıyor:

    "Belgeler arası çelişkinin asıl kaynağı iki farklı zamandaki snapshot
    ya da ürün sayfasının kampanya sayfasından ayrışması olurdu."

Bu betik tam olarak bunu dener. Korpusta GERÇEKTEN iki hasat turu var
(2026-07-30 → 2026-08-03, bkz. `data/snapshots/fark-2026-07-30_2026-08-03.json`,
`src/scraping/snapshot.py` ile üretildi). O fark raporunda 140 "degisti" kaydı
var: AYNI URL, farklı `content_hash`/`text_hash`. Bu betik o 140 adayı alır,
her biri için ESKİ metni (`c3f3b90` commit'i, 2026-07-30 hasadı) ve YENİ metni
(`e05bc83` commit'i, 2026-08-03 hasadı) git'ten okur, ikisinde de
`src.extraction.rules.extract.extract_all` koşturur ve finansal alanların
KANONİK DEĞERİNİN gerçekten değişip değişmediğine bakar.

"content_hash farklı" ≠ "finansal alan değişti" — çoğu fark muhtemelen
biçimlendirme/boilerplate gürültüsü olacaktır (ölçüm `snapshot.py` docstring'inde
zaten gösteriyor: ham HTML hash'i 238 yalancı fark üretiyordu, bu yüzden
`text_hash` temiz metin üzerinden kuruldu — ama temiz metin bile değişebilir
[örn. "güncellenme tarihi" damgası] finansal alan değişmeden).

Kullanım:
    python3 -m scripts.celiski_canli                    # özet
    python3 -m scripts.celiski_canli --detail            # her adayı yazdır
    python3 -m scripts.celiski_canli --before c3f3b90 --after e05bc83
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from src.comparison.contradiction import Contradiction, detect_across
from src.extraction.rules.extract import extract_all
from src.preprocessing.clean import normalize_text
from src.schemas import Campaign

DIFF_JSON = REPO_ROOT / "data/snapshots/fark-2026-07-30_2026-08-03.json"
BEFORE_MANIFEST = REPO_ROOT / "data/snapshots/2026-07-30.json"
AFTER_MANIFEST = REPO_ROOT / "data/snapshots/2026-08-03.json"

# Finansal alanlar — bunlarda gerçek değişim "ilan edilen koşul değişti" demektir.
# `guncelleme_tarihi`, sayfa metadata'sı gibi alanlar burada YOK — onlar hep değişir.
WATCHED_FIELDS = (
    "kar_payi_orani", "tahsis_ucreti", "finansman_tutari", "vade_ay",
    "taksit_sayisi", "masraf_durumu", "kampanya_suresi",
)


def git_show(rev: str, path: str) -> Optional[str]:
    """`git show <rev>:<path>` — dosya o commit'te yoksa None."""
    try:
        out = subprocess.run(
            ["git", "show", f"{rev}:{path}"],
            cwd=REPO_ROOT, capture_output=True, check=True)
        return out.stdout.decode("utf-8", errors="replace")
    except subprocess.CalledProcessError:
        return None


def _load_manifest_paths(manifest_path: Path) -> dict[tuple[str, str], str]:
    """(bucket, url) -> .meta.json'dan türetilen .txt yolu (raw_dir'e göreli)."""
    man = json.loads(manifest_path.read_text(encoding="utf-8"))
    out: dict[tuple[str, str], str] = {}
    for e in man["entries"]:
        meta_path = e.get("path")
        if not meta_path or not meta_path.endswith(".meta.json"):
            continue
        txt_path = meta_path[: -len(".meta.json")]
        out[(e["bucket"], e["url"])] = txt_path
    return out


@dataclass
class FieldDiff:
    field: str
    before_value: Any
    after_value: Any
    before_raw: Optional[str]
    after_raw: Optional[str]


@dataclass
class Candidate:
    bank_slug: str
    bucket: str
    url: str
    title: str
    before_path: str
    after_path: str
    before_chars: Optional[int]
    after_chars: Optional[int]
    before_hash: Optional[str]
    after_hash: Optional[str]
    field_diffs: list[FieldDiff]
    before_text: str = ""
    after_text: str = ""


def _canon_map(text: str) -> dict[str, Any]:
    fields = extract_all(text)
    return {f.field_name: f for f in fields}


def analyze(before_rev: str, after_rev: str, *, raw_dir_prefix: str = "app/data/raw"
            ) -> tuple[list[Candidate], dict[str, int]]:
    diff = json.loads(DIFF_JSON.read_text(encoding="utf-8"))
    degisti = diff.get("degisti", [])
    before_paths = _load_manifest_paths(BEFORE_MANIFEST)
    after_paths = _load_manifest_paths(AFTER_MANIFEST)

    stats = {
        "aday_degisti_kaydi": len(degisti),
        "git_blob_ikisi_de_okunabilen": 0,
        "temiz_metin_gercekten_farkli": 0,
        "izlenen_alan_kanonik_deger_farkli": 0,
    }
    candidates: list[Candidate] = []

    for item in degisti:
        key = (item["bucket"], item["url"])
        b_rel = before_paths.get(key)
        a_rel = after_paths.get(key)
        if not b_rel or not a_rel:
            continue
        before_raw = git_show(before_rev, f"{raw_dir_prefix}/{b_rel}")
        after_raw = git_show(after_rev, f"{raw_dir_prefix}/{a_rel}")
        if before_raw is None or after_raw is None:
            continue
        stats["git_blob_ikisi_de_okunabilen"] += 1

        before_text = normalize_text(before_raw)
        after_text = normalize_text(after_raw)
        if before_text == after_text:
            continue
        stats["temiz_metin_gercekten_farkli"] += 1

        before_fields = _canon_map(before_text)
        after_fields = _canon_map(after_text)

        field_diffs: list[FieldDiff] = []
        for fname in WATCHED_FIELDS:
            bf = before_fields.get(fname)
            af = after_fields.get(fname)
            bv = bf.canonical_value if bf else None
            av = af.canonical_value if af else None
            if bv == av:
                continue
            field_diffs.append(FieldDiff(
                field=fname, before_value=bv, after_value=av,
                before_raw=bf.raw_value if bf else None,
                after_raw=af.raw_value if af else None,
            ))

        if field_diffs:
            stats["izlenen_alan_kanonik_deger_farkli"] += 1
            candidates.append(Candidate(
                bank_slug=item.get("bank_slug", "?"), bucket=item["bucket"],
                url=item["url"], title=item.get("title") or "",
                before_path=b_rel, after_path=a_rel,
                before_chars=item.get("onceki_char"), after_chars=item.get("yeni_char"),
                before_hash=item.get("onceki_hash"), after_hash=item.get("yeni_hash"),
                field_diffs=field_diffs,
                before_text=before_text, after_text=after_text,
            ))

    return candidates, stats


def live_fire_test(candidates: list[Candidate]) -> list[tuple[Candidate, list[Contradiction]]]:
    """ASIL üretim fonksiyonunu (`detect_across`) gerçek metin çiftleriyle koştur.

    Alan-bazlı diff (yukarıdaki `analyze`) "kanonik değer değişti mi" sorusuna
    cevap verir ama `contradiction.py`'nin GERÇEKTEN ateşleyip ateşlemediğini
    söylemez — o fonksiyon kendi kalıplarını (`end_date_claims`'in SIKI
    `_END_PATTERNS`'i, `_SELF_EXPIRED` vetosu, `product_key` eşleştirmesi)
    kullanır ve bunlar `extract_all`'dan (genel alan çıkarıcı) FARKLI/daha
    sıkıdır.

    Her aday için önceki ve sonraki metinden GERÇEK `Campaign` nesneleri kurar
    (aynı `bank_slug` + `source_url`, sentetik metin YOK) ve ikisini birden
    `detect_across()`'a verir — tam olarak üretim korpusunda iki tur EŞZAMANLI
    var olsaydı ne olacağını gösterir.
    """
    out: list[tuple[Candidate, list[Contradiction]]] = []
    for c in candidates:
        c_before = Campaign(bank_slug=c.bank_slug, raw_text=c.before_text,
                            source_url=c.url, fields=extract_all(c.before_text))
        c_after = Campaign(bank_slug=c.bank_slug, raw_text=c.after_text,
                           source_url=c.url, fields=extract_all(c.after_text))
        cons = detect_across([c_before, c_after])
        if cons:
            out.append((c, cons))
    return out


def main(argv: Optional[list[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--before", default="c3f3b90",
                    help="2026-07-30 hasat turunun commit'i (varsayılan: c3f3b90)")
    ap.add_argument("--after", default="e05bc83",
                    help="2026-08-03 hasat turunun commit'i (varsayılan: e05bc83)")
    ap.add_argument("--detail", action="store_true")
    ap.add_argument("--json", dest="json_out", default=None)
    ap.add_argument("--fire-test", action="store_true",
                    help="her adayı gerçek detect_across() ile koştur (yavaş ama "
                         "üretim fonksiyonunun ateşleyip ateşlemediğini gösterir)")
    args = ap.parse_args(argv)

    candidates, stats = analyze(args.before, args.after)

    print("=" * 72)
    print("ÇİFT-SNAPSHOT ÇELİŞKİ/TARİHÇE TARAMASI "
          f"({args.before} → {args.after})")
    print("=" * 72)
    for k, v in stats.items():
        print(f"  {k:38s}: {v}")
    print()
    if not candidates:
        print("  Alan değeri gerçekten değişen belge bulunamadı.")
        return 0

    for c in candidates:
        print(f"[{c.bank_slug}] {c.url}")
        print(f"    başlık: {c.title}")
        print(f"    önceki_hash={c.before_hash[:12] if c.before_hash else None}..."
              f"  yeni_hash={c.after_hash[:12] if c.after_hash else None}...")
        print(f"    önceki_char={c.before_chars}  yeni_char={c.after_chars}")
        for fd in c.field_diffs:
            print(f"    * {fd.field}: {fd.before_value!r} -> {fd.after_value!r}")
            if args.detail:
                print(f"        önceki_ham: {fd.before_raw!r}")
                print(f"        yeni_ham:   {fd.after_raw!r}")
        print()

    if args.fire_test:
        fired = live_fire_test(candidates)
        print("=" * 72)
        print(f"CANLI ATEŞLEME TESTİ — {len(candidates)} adaydan "
              f"{len(fired)}'i gerçek detect_across() içinde Contradiction üretti")
        print("=" * 72)
        for _c, cons in fired:
            for con in cons:
                print(f"[{con.scope}] {con.kind}  match_key={con.match_key}")
                print(f"    {con.detail}")
                for e in con.evidence:
                    print(f"    · {e.source_span!r}")
                print()

    if args.json_out:
        payload = {
            "stats": stats,
            "candidates": [
                {
                    "bank_slug": c.bank_slug, "url": c.url, "title": c.title,
                    "before_path": c.before_path, "after_path": c.after_path,
                    "before_hash": c.before_hash, "after_hash": c.after_hash,
                    "before_chars": c.before_chars, "after_chars": c.after_chars,
                    "field_diffs": [
                        {"field": fd.field, "before_value": fd.before_value,
                         "after_value": fd.after_value,
                         "before_raw": fd.before_raw, "after_raw": fd.after_raw}
                        for fd in c.field_diffs
                    ],
                }
                for c in candidates
            ],
        }
        Path(args.json_out).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"JSON yazıldı: {args.json_out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
