"""Önbellekteki HTML'den metni YENİDEN çıkarır — siteye hiç gitmeden.

İlgili: `src/scraping/collector.py` (`_extract_main_text`) · CLAUDE.md §14
(ham HTML provenance cache'i tam bunun için tutulur)

## Neden bu araç var

Çıkarım mantığı iyileştiğinde korpus kendiliğinden iyileşmiyor. 2026-08-04'te
üç sessiz hata düzeltildi (`<form>` içeriğinin atılması, boş kabuk eşiği,
`same_site` port yutması) ama `data/raw` altındaki 1684 `.txt` eski mantıkla
üretilmişti. Ölçüm: 153 belge (%9) saf çerez politikası + navigasyon
menüsüydü — Emlak'ta %34, Vakıf'ta %24.

Yeniden HASAT yerine yeniden ÇIKARIM yapılır, çünkü:
  * Siteye gidilmez — 10 bankaya 1570 istek atılmaz, robots yükü sıfır.
  * Dosya adları KORUNUR. Yeniden hasat yeni URL'lerden yeni dosya adları
    üretir ve anotasyon CSV'lerindeki `doc_id` eşleşmesi bozulur (ölçüldü:
    bir turda 32 belgenin 10'u geçersiz kaldı).
  * `content_hash` aynı HTML'den geldiği için provenance zinciri sürer.

## Kurtarılamayan belgeler SİLİNMEZ

Bazı sayfalar (Vakıf'ın bir kısmı) içeriği JS ile üretiyor; önbellekteki HTML
gerçekten yalnızca çerçeve taşıyor. Bu belgeler `content_status: "kabuk"` ile
İŞARETLENİR, atılmaz (CLAUDE.md — silme yok). İşaretin amacı aşağı akışın
(anotasyon, eğitim) bunları dışlayabilmesi.

Tespit yöntemi: N belge birebir AYNI metni üretiyorsa o metin içerik değil
çerçevedir. Uzunluk eşiği bunu yakalayamaz — ölçülen örnekte iki farklı Vakıf
ürün sayfası aynı 2551 karakteri üretti, yani eşiği rahatça geçen ama içerik
taşımayan bir kabuk. Yeniden çıkarım bu belgeleri 201 karakterlik AÇIK
kabuktan 2551 karakterlik GİZLİ kabuğa çevirdiği için işaretleme zorunlu.

## Kullanım

    python3 -m scripts.reextract_raw                      # kuru koşu
    python3 -m scripts.reextract_raw --apply
    python3 -m scripts.reextract_raw --banks vakif-katilim,turkiye-emlak-katilim
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from src.scraping.collector import (
    MIN_DOC_CHARS,
    _extract_main_text,
    _is_empty_result_page,
)

# Aynı metni üreten belge sayısı bu değere ULAŞIRSA metin çerçeve OLABİLİR.
CHROME_GROUP_MIN = 2

# ...ama tek başına yetmez. Ölçüm: aynı-metin gruplarındaki 215 belgenin 137'si
# MEŞRU TEKRAR — aynı gerçek içerik birden fazla URL'de yayımlanıyor (Türkiye
# Finans'ın 13.748 karakterlik taşıt finansmanı sayfası 4 ayrı yolda). Onları
# "kabuk" işaretlemek gerçek içeriği eğitimden ve anotasyondan atardı.
#
# Ayırt edici ölçüt: metin FİNANSAL SİNYAL taşıyor mu? Çerçeve (çerez politikası
# + navigasyon) oran, tutar, taksit, kampanya kapsamı ifadesi taşımaz.
_CONTENT_SIGNAL_RE = re.compile(
    r"%\s?\d"                       # oran
    r"|\d[.,]\d{2}\s*(?:TL|₺)"      # para
    r"|kâr\s*pay[ıi]\s*oran"
    r"|finansman\s*tutar"
    r"|taksit"
    r"|kampanya\s*kapsam",
    re.IGNORECASE)


def _has_content_signal(text: str) -> bool:
    """Metin gerçek finansal içerik taşıyor mu? (çerçeve/tekrar ayrımı)"""
    return bool(_CONTENT_SIGNAL_RE.search(text))

# Büyüme bu orandan azsa "değişim yok" sayılır — gürültüyü rapora taşımamak için.
GROWTH_MIN_CHARS = 50

RESULT_RECOVERED = "icerik_kurtarildi"
RESULT_CHROME = "cerceve"
RESULT_UNCHANGED = "degisim_yok"
RESULT_SHRANK = "kisaldi"
RESULT_TOO_SHORT = "esik_alti"
RESULT_EMPTY_PAGE = "bos_sonuc_sayfasi"

STATUS_SHELL = "kabuk"


def _text_key(text: str) -> str:
    return hashlib.sha256(re.sub(r"\s+", " ", text).strip().encode("utf-8")).hexdigest()


@dataclass
class Doc:
    """Tek belgenin yeniden çıkarım sonucu."""

    html: Path
    txt: Path
    bank: str
    bucket: str
    old_len: int
    new_text: str
    result: str = ""

    @property
    def new_len(self) -> int:
        return len(self.new_text)

    @property
    def delta(self) -> int:
        return self.new_len - self.old_len


@dataclass
class Report:
    docs: list[Doc] = field(default_factory=list)
    missing_txt: list[str] = field(default_factory=list)
    written: int = 0
    marked: int = 0


def scan(raw_dir: Path, banks: set[str] | None) -> Report:
    """HTML önbelleğini tarar, yeniden çıkarır, sonucu sınıflandırır."""
    rep = Report()
    for html in sorted(raw_dir.rglob("*.html")):
        rel = html.relative_to(raw_dir).parts
        bank = rel[0]
        if banks and bank not in banks:
            continue
        bucket = rel[1] if len(rel) > 2 else "-"
        txt = html.with_suffix(".txt")
        if not txt.exists():
            rep.missing_txt.append(str(html.relative_to(raw_dir)))
            continue
        old = txt.read_text(encoding="utf-8", errors="replace")
        new = _extract_main_text(html.read_text(encoding="utf-8", errors="replace"))
        rep.docs.append(Doc(html, txt, bank, bucket, len(old), new))

    # Çerçeve tespiti: aynı metni üreten belgeleri grupla (belge bazında değil,
    # KÜME bazında karar verilir — tek belgeye bakarak anlaşılamaz).
    groups: dict[str, list[Doc]] = collections.defaultdict(list)
    for doc in rep.docs:
        groups[_text_key(doc.new_text)].append(doc)

    for doc in rep.docs:
        group = groups[_text_key(doc.new_text)]
        if doc.new_len < MIN_DOC_CHARS:
            doc.result = RESULT_TOO_SHORT
        elif _is_empty_result_page(doc.new_text):
            doc.result = RESULT_EMPTY_PAGE
        elif (len(group) >= CHROME_GROUP_MIN
              and not _has_content_signal(doc.new_text)):
            doc.result = RESULT_CHROME
        elif doc.delta < -GROWTH_MIN_CHARS:
            doc.result = RESULT_SHRANK
        elif doc.delta > GROWTH_MIN_CHARS:
            doc.result = RESULT_RECOVERED
        else:
            doc.result = RESULT_UNCHANGED
    return rep


def _shell(result: str) -> bool:
    return result in (RESULT_CHROME, RESULT_TOO_SHORT, RESULT_EMPTY_PAGE)


def apply_changes(rep: Report, now: str) -> None:
    """Metni yazar, meta'ya yeniden çıkarım kaydı ve kabuk işareti düşer."""
    for doc in rep.docs:
        # `kisaldi` UYGULANMAZ: yeni mantık forma yalnızca EKLEME yapıyor, o
        # yüzden kısalma beklenmez. Olursa bir regresyon sinyalidir ve üzerine
        # yazmak kanıtı yok eder.
        if doc.result == RESULT_SHRANK:
            continue
        if not _shell(doc.result):
            doc.txt.write_text(doc.new_text, encoding="utf-8")
            rep.written += 1

        meta_path = Path(str(doc.txt) + ".meta.json")
        if not meta_path.exists():
            continue
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        meta["reextracted_at"] = now
        meta["extraction_result"] = doc.result
        if _shell(doc.result):
            # Önbellekteki HTML gerçekten içerik taşımıyor (JS ile üretiliyor).
            # Belge SİLİNMEZ; aşağı akış bu işaretle dışlayabilir.
            meta["content_status"] = STATUS_SHELL
            rep.marked += 1
        else:
            meta.pop("content_status", None)
        meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2),
                             encoding="utf-8")


def render_report(rep: Report, applied: bool, now: str) -> str:
    counts = collections.Counter(d.result for d in rep.docs)
    per_bank: dict[str, collections.Counter] = collections.defaultdict(
        collections.Counter)
    for doc in rep.docs:
        per_bank[doc.bank][doc.result] += 1

    lines = [
        "# Yeniden Çıkarım Raporu",
        "",
        "> `python -m scripts.reextract_raw` üretti. Elle düzenlemeyin.",
        "",
        f"- **Tarih:** {now}",
        f"- **Mod:** {'UYGULANDI' if applied else 'kuru koşu (--apply verilmedi)'}",
        f"- **İncelenen belge:** {len(rep.docs)}",
        f"- **Yazılan `.txt`:** {rep.written}",
        f"- **`content_status: kabuk` işaretlenen:** {rep.marked}",
        "",
        "Siteye istek atılmadı — kaynak yalnızca önbellekteki HTML.",
        "",
        "## Sonuç dağılımı",
        "",
        "| Sonuç | Belge |",
        "|---|---:|",
    ]
    for result, n in counts.most_common():
        lines.append(f"| `{result}` | {n} |")

    lines += ["", "## Banka bazında", "", "| Banka | " +
              " | ".join(f"`{r}`" for r in counts) + " |",
              "|---" * (len(counts) + 1) + "|"]
    for bank in sorted(per_bank):
        row = " | ".join(str(per_bank[bank].get(r, 0)) for r in counts)
        lines.append(f"| `{bank}` | {row} |")

    recovered = [d for d in rep.docs if d.result == RESULT_RECOVERED]
    if recovered:
        recovered.sort(key=lambda d: -d.delta)
        lines += ["", "## En çok içerik kurtarılan 15 belge", "",
                  "| Belge | Eski | Yeni | Δ |", "|---|---:|---:|---:|"]
        for doc in recovered[:15]:
            lines.append(f"| `{doc.bank}/{doc.bucket}/{doc.txt.stem}` | "
                         f"{doc.old_len} | {doc.new_len} | +{doc.delta} |")

    chrome = [d for d in rep.docs if _shell(d.result)]
    if chrome:
        lines += ["", "## Kurtarılamayan belgeler (`content_status: kabuk`)", "",
                  "Önbellekteki HTML yalnızca çerçeve taşıyor; içerik JS ile "
                  "üretiliyor. Belgeler SİLİNMEDİ, işaretlendi. Gerçekten "
                  "gerekiyorsa tarayıcı ile yeniden hasat gerekir.", "",
                  "| Belge | Sonuç | Karakter |", "|---|---|---:|"]
        for doc in sorted(chrome, key=lambda d: (d.bank, d.txt.stem))[:40]:
            lines.append(f"| `{doc.bank}/{doc.bucket}/{doc.txt.stem}` | "
                         f"`{doc.result}` | {doc.new_len} |")
        if len(chrome) > 40:
            lines.append(f"| … | | {len(chrome) - 40} belge daha |")

    shrank = [d for d in rep.docs if d.result == RESULT_SHRANK]
    if shrank:
        lines += ["", "## UYARI — kısalan belgeler (uygulanmadı)", "",
                  "Yeni mantık forma yalnızca ekleme yapıyor; kısalma bir "
                  "regresyon sinyalidir ve üzerine YAZILMADI.", "",
                  "| Belge | Eski | Yeni |", "|---|---:|---:|"]
        for doc in shrank[:20]:
            lines.append(f"| `{doc.bank}/{doc.bucket}/{doc.txt.stem}` | "
                         f"{doc.old_len} | {doc.new_len} |")

    if rep.missing_txt:
        lines += ["", f"## `.txt` eşi olmayan HTML: {len(rep.missing_txt)}", ""]
        lines += [f"- `{p}`" for p in rep.missing_txt[:10]]
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--raw-dir", default="data/raw")
    ap.add_argument("--banks", default="", help="virgülle ayrılmış slug filtresi")
    ap.add_argument("--apply", action="store_true",
                    help="değişiklikleri yaz (varsayılan: kuru koşu)")
    ap.add_argument("--report", default="", help="rapor yolu (varsayılan: <raw-dir>/_reextract_report.md)")
    args = ap.parse_args(argv)

    # bs4 YOKSA DUR. `_extract_main_text` o durumda tüm HTML'i metin sayarak
    # zarif biçimde bozuluyor (hasat için doğru davranış: belge tamamen
    # kaybolmasın). Ama YENİDEN çıkarımda bu felaket: her belge "büyümüş"
    # görünür ve korpusa ham HTML yazılır. Ölçüldü: sistem python3 ile koşulan
    # kuru koşu 1569 belgenin 1418'ini "içerik kurtarıldı" diye raporladı;
    # gerçekte sağlam belgeler birebir aynıydı.
    try:
        import bs4  # noqa: F401
    except ModuleNotFoundError:
        print("HATA: beautifulsoup4 yok. Yeniden cikarim BS4 OLMADAN "
              "anlamsizdir — tum HTML metin sayilir ve korpus bozulur. "
              "Depo venv'i ile kosun: .venv/bin/python -m scripts.reextract_raw",
              file=sys.stderr)
        return 2

    raw_dir = Path(args.raw_dir)
    if not raw_dir.is_dir():
        print(f"HATA: {raw_dir} yok", file=sys.stderr)
        return 1
    banks = {b.strip() for b in args.banks.split(",") if b.strip()} or None

    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    rep = scan(raw_dir, banks)
    if args.apply:
        apply_changes(rep, now)

    report_path = Path(args.report or raw_dir / "_reextract_report.md")
    report_path.write_text(render_report(rep, args.apply, now), encoding="utf-8")

    counts = collections.Counter(d.result for d in rep.docs)
    print(f"{len(rep.docs)} belge incelendi "
          f"({'UYGULANDI' if args.apply else 'kuru koşu'})")
    for result, n in counts.most_common():
        print(f"  {n:5}  {result}")
    if args.apply:
        print(f"  yazilan .txt: {rep.written} · kabuk isaretlenen: {rep.marked}")
    print(f"rapor: {report_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
