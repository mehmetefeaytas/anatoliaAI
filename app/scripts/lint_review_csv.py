"""İnceleme CSV'lerini anotasyon anında denetler.

İlgili: `data/gold/ANNOTATION_GUIDE.md` · `data/gold/review/_bicim-karti.md` ·
`scripts/build_gold.py` (aynı karar sözleşmesi) · `scripts/gold_schema.py`

## Neden bu araç var

Kalibrasyon A'nın ilk turunda **9 satır sessizce bozuldu**: `gold_value`
hücresine yazılan aralık ifadelerini ayrıştırıcı reddetmiyor, yanlış ucu alıp
devam ediyordu.

    "2026-07-01 - 2026-07-31"  ->  "2026-07-01"   (bitiş değil, BAŞLANGIÇ)
    "{...5000} - {...150000}"  ->  5000            (üst sınır düştü)
    "“85 / 15”"                ->  {min:15,max:85} (paylaşım oranı, kâr payı DEĞİL)

Bu hatalar `build_gold` aşamasında da görünmez — çünkü değer geçerlidir,
yalnızca YANLIŞTIR. Tek yakalama noktası anotasyon anıdır.

Gürültülü hatalar (`fix` + boş değer, 8 sınıf dışı tür) `build_gold`'da zaten
durur; ama orada durmak, işin bitmesinden SONRA durmak demektir. Bu araç aynı
kontrolü öne çeker.

## Kullanım

    python3 -m scripts.lint_review_csv data/gold/review/round0_kalibrasyon_A.csv
    python3 -m scripts.lint_review_csv data/gold/review/*.csv

Çıkış kodu: hata varsa 1, yalnız uyarı varsa 0.
"""

from __future__ import annotations

import argparse
import csv
import glob
import json
import re
import sys
from dataclasses import dataclass
from typing import Any, Iterator

from scripts.gold_schema import (
    GoldValidationError,
    parse_gold_value,
    validate_canonical,
)

REQUIRED_COLUMNS = {"doc_id", "field", "model_value", "gold_value", "verdict"}
VALID_VERDICTS = ("ok", "fix", "absent", "unclear")

# `doc_id` kebab-case slug'dır (CLAUDE.md — isimlendirme). Elektronik tablonun
# otomatik düzeltmesi `--` ayıracını em-dash'e (`—`) çevirebiliyor; kalibrasyon
# A'da 2 satırda oldu. Bozulan satır hiçbir belgeyle eşleşmez ve `build_gold`
# onu "bilinmeyen doc_id" diye ATLAR — anotasyon emeği sessizce kaybolur.
_DOC_ID_RE = re.compile(r"^[a-z0-9][a-z0-9._-]*$")

# Tamsayı / tarih / para / masraf alanları ŞEMADA TEK DEĞER alır; aralık
# yazılırsa ayrıştırıcı reddetmez, ilk ucu alıp devam eder.
#
# Tespit yöntemi: **değer belirteci sayısı**. Desen aramak burada çalışmıyor —
# ISO tarih (`2023-08-31`) ve TR ondalık (`1500.50`) ayıraç karakteri taşıdığı
# için desen tabanlı kontrol yanlış pozitif üretiyor (ölçüldü: 4/9 bulgu).
# Bir alanda birden fazla değer belirteci varsa, ayrıştırıcı en fazla birini
# alabilir — geri kalanı sessizce kaybolur.
_ISO_DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")
_NUMBER_RE = re.compile(r"\d+(?:[.,]\d+)*")
_MULTI_MARKER_RE = re.compile(r"\bila\b|\.{3}|…", re.IGNORECASE)

_DATE_SCALARS = ("kampanya_suresi",)
_NUMERIC_SCALARS = ("vade_ay", "taksit_sayisi", "finansman_tutari",
                    "tahsis_ucreti", "odul_miktari", "masraf_durumu")


def _value_tokens(field: str, text: str) -> int:
    """Alanda kaç ayrı değer belirteci var? 2+ ise ayrıştırıcı veri kaybeder."""
    if field in _DATE_SCALARS:
        return len(_ISO_DATE_RE.findall(text)) or len(_NUMBER_RE.findall(text))
    # Tarihleri at: sayısal alanda tarih beklenmez ama not sızmışsa saymasın.
    return len(_NUMBER_RE.findall(_ISO_DATE_RE.sub(" ", text)))


def looks_like_range(field: str, text: str) -> bool:
    """Tek değerli bir alana çoklu değer yazılmış mı?"""
    if field not in _DATE_SCALARS and field not in _NUMERIC_SCALARS:
        return False
    if _MULTI_MARKER_RE.search(text):
        return True
    return _value_tokens(field, text) > 1

# `unclear` bir kaçış kapısıdır ama ucuz değildir (kılavuz §3.4).
UNCLEAR_WARN_RATIO = 0.05

SEVERITY_ERROR = "HATA"
SEVERITY_WARN = "UYARI"


@dataclass(frozen=True)
class Finding:
    """Tek bulgu. `line` dosyanın gerçek satır numarasıdır (1 = başlık)."""

    severity: str
    file: str
    line: int
    doc_id: str
    field: str
    message: str

    def __str__(self) -> str:
        return (f"{self.severity} {self.file}:{self.line} "
                f"[{self.doc_id} · {self.field}] {self.message}")


def _model_value(raw: str) -> tuple[Any, bool]:
    """Ham `model_value` -> (değer, üretildi mi). JSON değilse metin döner."""
    raw = (raw or "").strip()
    if not raw:
        return None, False
    try:
        return json.loads(raw), True
    except (json.JSONDecodeError, ValueError):
        return raw, True


def read_rows(path: str) -> tuple[list[dict], list[Finding]]:
    """CSV'yi okur. Elektronik tablodan gelen sayfa-adı satırını tespit eder.

    Google Sheets / Excel bir sekmeyi CSV olarak yazarken başa sekme adını
    koyabiliyor. O satır kalırsa `csv.DictReader` onu BAŞLIK sanır ve
    `gold_value`/`verdict` sütunları görünmez olur — dosya doluyken bomboş
    okunur. Kalibrasyon A'da tam bu oldu.
    """
    findings: list[Finding] = []
    with open(path, encoding="utf-8-sig") as fh:
        lines = fh.read().split("\n")

    offset = 1  # başlık satırı
    if lines and ";" not in lines[0]:
        findings.append(Finding(
            SEVERITY_ERROR, path, 1, "-", "-",
            f"ilk satir basliga benzemiyor ({lines[0][:40]!r}) — elektronik "
            f"tablo sayfa adini yazmis olabilir. Bu satir silinmeli, yoksa "
            f"tum gold_value/verdict sutunlari GORUNMEZ olur."))
        lines = lines[1:]
        offset = 2

    reader = csv.DictReader(lines, delimiter=";")
    missing = REQUIRED_COLUMNS - set(reader.fieldnames or [])
    if missing:
        findings.append(Finding(
            SEVERITY_ERROR, path, 1, "-", "-",
            f"zorunlu sutun eksik: {sorted(missing)}"))
        return [], findings

    rows = []
    for n, row in enumerate(reader):
        row["_line"] = n + 1 + offset
        rows.append(row)
    return rows, findings


def check_row(row: dict, path: str) -> Iterator[Finding]:
    """Tek satırı `build_gold` sözleşmesine göre denetler."""
    line, doc_id, field = row["_line"], row.get("doc_id", ""), row.get("field", "")
    verdict = (row.get("verdict") or "").strip().casefold()
    gold = (row.get("gold_value") or "").strip()
    model, has_model = _model_value(row.get("model_value", ""))

    def f(sev: str, msg: str) -> Finding:
        return Finding(sev, path, line, doc_id, field, msg)

    if not _DOC_ID_RE.match(doc_id):
        bad = sorted({ch for ch in doc_id if not re.match(r"[a-z0-9._-]", ch)})
        yield f(SEVERITY_ERROR,
                f"doc_id slug bicimine uymuyor, beklenmeyen karakter: {bad}. "
                f"Elektronik tablo '--' ayiracini em-dash'e cevirmis olabilir. "
                f"build_gold bu satiri 'bilinmeyen doc_id' diye ATLAR.")

    if verdict and verdict not in VALID_VERDICTS:
        yield f(SEVERITY_ERROR,
                f"verdict {verdict!r} taninmiyor. Izin verilenler: (bos)=ok, "
                f"{', '.join(VALID_VERDICTS)}")
        return

    # `absent` = "metinde deger YOK". build_gold:142 yazilan degeri ATAR ve
    # modeli halusinasyon sayar. Deger biliniyorsa dogru karar `fix`.
    if verdict == "absent" and gold:
        yield f(SEVERITY_ERROR,
                f"verdict=absent ama gold_value dolu ({gold[:40]!r}). "
                f"Deger biliniyorsa verdict=fix; 'metinde yok' ise deger bos "
                f"kalmali. build_gold bu degeri sessizce atar.")

    if verdict == "unclear" and gold:
        yield f(SEVERITY_WARN,
                "verdict=unclear ama gold_value dolu — deger metrik disinda "
                "kalir, karar veriliyorsa verdict=fix olmali")

    if verdict == "fix" and not gold:
        yield f(SEVERITY_ERROR,
                "verdict=fix ama gold_value bos — build_gold burada DURUR. "
                "Dogru degeri yaz ya da verdict'i absent/unclear yap.")
        return

    effective = verdict or ("fix" if gold else "ok")

    if not verdict and gold:
        yield f(SEVERITY_WARN,
                "verdict bos ama gold_value dolu -> sistem `fix` sayar "
                "(kilavuz §3.2). Model dogruysa iki hucreyi de bos birak.")

    if effective == "fix":
        if looks_like_range(field, gold):
            yield f(SEVERITY_ERROR,
                    f"{field} tek deger alir ama {_value_tokens(field, gold)} "
                    f"deger yazilmis ({gold[:40]!r}). Ayristirici REDDETMEZ, "
                    f"ilk ucu alir — sessiz bozulma. Karta bak: en buyuk/bitis "
                    f"degerini yaz, digerini note'a dus.")
        try:
            parsed = parse_gold_value(field, gold)
        except GoldValidationError as exc:
            yield f(SEVERITY_ERROR, str(exc))
            return
        if has_model and parsed == model:
            yield f(SEVERITY_WARN,
                    "gold_value modelin degeriyle AYNI — `fix` 'bu deger "
                    "yanlis' demektir ve modeli haksiz yere yanlis gosterir. "
                    "Dogruysa bos birak, belirsizse unclear yaz.")
    elif effective == "ok" and has_model:
        # Boş bırakmak modelin değerini onaylamaktır; o değer kanonik değilse
        # hata build_gold'un EN SONUNDAKİ validate_gold adımına kadar saklanır.
        err = validate_canonical(field, model)
        if err:
            yield f(SEVERITY_ERROR,
                    f"model degeri onaylandi (bos verdict) ama kanonik degil: "
                    f"{err}")


def lint(paths: list[str]) -> list[Finding]:
    """Verilen CSV'leri denetler, bulguları döndürür."""
    out: list[Finding] = []
    for path in paths:
        rows, findings = read_rows(path)
        out.extend(findings)
        if not rows:
            continue
        for row in rows:
            out.extend(check_row(row, path))

        unclear = sum(1 for r in rows
                      if (r.get("verdict") or "").strip().casefold() == "unclear")
        if rows and unclear / len(rows) > UNCLEAR_WARN_RATIO:
            out.append(Finding(
                SEVERITY_WARN, path, 1, "-", "-",
                f"satirlarin %{100 * unclear / len(rows):.0f}'i unclear "
                f"({unclear}/{len(rows)}) — esik %{UNCLEAR_WARN_RATIO:.0%}. "
                f"Kilavuzda eksik olabilir (§3.4)."))
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("csv", nargs="+", help="inceleme CSV'leri (glob olabilir)")
    ap.add_argument("--quiet", action="store_true",
                    help="yalnizca ozet bas")
    args = ap.parse_args(argv)

    paths = sorted({p for pat in args.csv for p in (glob.glob(pat) or [pat])})
    findings = lint(paths)
    errors = [f for f in findings if f.severity == SEVERITY_ERROR]
    warns = [f for f in findings if f.severity == SEVERITY_WARN]

    if not args.quiet:
        for finding in findings:
            print(finding)
        if findings:
            print()
    print(f"{len(paths)} dosya · {len(errors)} hata · {len(warns)} uyari")
    if errors:
        print("HATA olan satirlar build_gold'u durdurur ya da gold'a YANLIS "
              "deger sokar. Bicim kurallari: data/gold/review/_bicim-karti.md")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
