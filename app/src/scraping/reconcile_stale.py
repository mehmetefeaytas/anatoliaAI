"""Bayat belge mutabakatı — "hasatta kayıp" belgeleri DOĞRULAYIP arşive taşır.

İlgili: snapshot.py (fark raporu), collector.py (ARCHIVE_SUBDIR, STATUS_EXPIRED),
        CLAUDE.md §14 (provenance), §17 (adil kıyas)

## Sorun

Yeniden hasat eski dosyaları SİLMEZ, üzerine yazar. Sitede artık olmayan bir
kampanya `live/` altında öylece kalır. `live/` "şu an aktif" anlamına geldiği için
bu, karşılaştırma motorunu ve dashboard'u SESSİZCE yanıltır.

Silmek de yanlış: süresi dolmuş kampanya bu proje için değerli veridir
(`suresi_dolmus_kampanya` kuralının doğrulama kümesi).

## Neden körlemesine "expired" etiketlemiyoruz

**"Hasatta kayıp" ≠ "süresi doldu".** Bir URL şu sebeplerle de kaybolabilir:

- site yapısı / URL şeması değişti,
- bu turda keşif giriş noktası o sayfayı bulamadı (kırpma sırası, yeni yollar),
- geçici çekim/ağ hatası.

Körlemesine etiketlemek veri UYDURMAK olur (CLAUDE.md §19 halüsinasyon yasağı).
Bu yüzden her kayıp URL **yeniden çekilir** ve karar kanıta bağlanır:

| Yeniden çekim            | Karar                                            |
|--------------------------|--------------------------------------------------|
| 404 / 410 / 451          | gerçekten kaldırılmış → arşive, `expired`        |
| 200 + "Süresi Dolmuştur" | yayında ama bitmiş → arşive, `expired`           |
| 200 + normal içerik      | duruyor → `live/` kalır, KEŞİF AÇIĞI olarak raporla |
| diğer (5xx, ağ, robots)  | karar verilemedi → dokunulmaz, `unverified`      |

Üçüncü satır bedava teşhistir: keşif giriş noktalarımızın neyi kaçırdığını ölçer.

## Güvenlik

Varsayılan **kuru koşu**. Dosya taşıma yalnızca `--apply` ile yapılır ve hiçbir
dosya SİLİNMEZ — `live/` → `archive/` taşınır, `.meta.json` içine kanıt bloğu
(`removal_check`) yazılır.

Kullanım:
    python -m src.scraping.reconcile_stale --before data/snapshots/2026-07-30.json \
        --after data/snapshots/2026-08-03.json --raw-dir data/raw
    python -m src.scraping.reconcile_stale ... --apply
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from .collector import ARCHIVE_SUBDIR, LIVE_SUBDIR, STATUS_EXPIRED, utc_now_iso
from .fetcher import RateLimiter, StaticFetcher
from .robots import DEFAULT_USER_AGENT, RobotsCache
from .snapshot import diff_manifests

# Sayfanın kendini "bitmiş" ilan ettiği ifadeler. `comparison.contradiction`
# ile AYNI kalıp — tek doğruluk kaynağı olsun diye oradan alınır.
try:
    from ..comparison.contradiction import _SELF_EXPIRED as SELF_EXPIRED
except ImportError:  # comparison katmanı yoksa da çalış
    SELF_EXPIRED = re.compile(
        r"(s[üu]resi\s+dolmu[şs]|sona\s+erdi|sona\s+ermi[şs]|"
        r"biten\s+kampanya|ge[çc]mi[şs]\s+kampanya)", re.IGNORECASE)

# Belgenin GERÇEKTEN kaldırıldığını gösteren HTTP kodları.
REMOVED_STATUSES = (404, 410, 451)

# Karar etiketleri
DECISION_REMOVED = "kaldirilmis"        # 404/410 → arşive
DECISION_SELF_EXPIRED = "suresi_dolmus"  # 200 ama "süresi dolmuştur" → arşive
DECISION_STILL_LIVE = "kesif_acigi"     # 200 normal → live'da kalır
DECISION_UNVERIFIED = "dogrulanamadi"   # karar verilemedi → dokunulmaz
# Aynı URL yeni turda BAŞKA bir kümede TAZE hâliyle toplanmış (tipik olarak
# `archive/`). Eski `live/` kopyası artık MÜKERRER; "süresi doldu" demek yanlış
# olur çünkü belge kaybolmadı, yalnızca DOĞRU kümeye yazıldı.
#
# Gerçek vaka (2026-08-03): Temmuz turunda Kuveyt Türk'ün arşiv sayfaları
# `live/` altına toplanıyordu (aktif kampanya sanılıyorlardı). Arşiv dışlama
# düzeltmesinden sonra aynı 34 URL `archive/` altına taze hâliyle yazıldı.
DECISION_SUPERSEDED = "gecersiz_kilindi"

MOVE_DECISIONS = (DECISION_REMOVED, DECISION_SELF_EXPIRED, DECISION_SUPERSEDED)


@dataclass
class Verdict:
    """Tek bir kayıp URL için doğrulama sonucu."""

    url: str
    bank_slug: str
    bucket: str
    decision: str
    http_status: Optional[int] = None
    detail: str = ""
    meta_path: Optional[str] = None
    moved: list[str] = field(default_factory=list)

    def to_json(self) -> dict[str, Any]:
        return {
            "url": self.url, "bank_slug": self.bank_slug, "bucket": self.bucket,
            "decision": self.decision, "http_status": self.http_status,
            "detail": self.detail, "meta_path": self.meta_path,
            "moved": self.moved,
        }


def _sibling_files(meta_path: Path) -> list[Path]:
    """`<stem>.txt.meta.json` yanındaki tüm belge dosyalarını bulur.

    `x.txt.meta.json` → x.txt, x.html, x.pdf (varsa) + kendisi.
    """
    name = meta_path.name
    if not name.endswith(".txt.meta.json"):
        return [meta_path]
    stem = name[: -len(".txt.meta.json")]
    out = [meta_path]
    for suffix in (".txt", ".html", ".htm", ".pdf"):
        cand = meta_path.parent / f"{stem}{suffix}"
        if cand.is_file():
            out.append(cand)
    return out


def verify_stale(before: dict[str, Any], after: dict[str, Any], raw_dir: str | Path, *,
                 buckets: tuple[str, ...] = (LIVE_SUBDIR,),
                 delay_s: float = 3.0, ignore_robots: bool = False,
                 user_agent: str = DEFAULT_USER_AGENT,
                 limit: Optional[int] = None) -> list[Verdict]:
    """Kayıp URL'leri yeniden çekip karar verir. Dosyaya DOKUNMAZ."""
    res = diff_manifests(before, after)
    candidates = [k for k in res.kayip if k.get("bucket") in buckets]
    if limit is not None:
        candidates = candidates[:limit]

    fetcher = StaticFetcher(user_agent=user_agent, limiter=RateLimiter(delay_s))
    robots = RobotsCache(user_agent=user_agent, ignore=ignore_robots)
    # Manifest kaydından dosya yoluna erişim (taşıma adımı için)
    before_paths = {(e["bucket"], e["url"]): e.get("path")
                    for e in before.get("entries", [])}

    out: list[Verdict] = []
    try:
        for item in candidates:
            url, slug = item["url"], item.get("bank_slug") or "?"
            bucket = item.get("bucket") or LIVE_SUBDIR
            meta_rel = before_paths.get((bucket, url))

            # Belge başka bir kümeye taşınmışsa (ör. bankanın kendi arşivine
            # düşmüşse) bu bir kayıp değil, ARŞİVLENMEDİR.
            if item.get("yeni_bucket"):
                out.append(Verdict(
                    url=url, bank_slug=slug, bucket=bucket,
                    decision=DECISION_SUPERSEDED,
                    detail=f"aynı URL yeni turda "
                           f"{'/'.join(item['yeni_bucket'])} kümesinde TAZE "
                           f"hâliyle toplandı; bu {bucket}/ kopyası mükerrer",
                    meta_path=meta_rel))
                continue

            allowed, reason = robots.allows(url)
            if not allowed:
                out.append(Verdict(url=url, bank_slug=slug, bucket=bucket,
                                   decision=DECISION_UNVERIFIED,
                                   detail=f"robots disallow: {reason}",
                                   meta_path=meta_rel))
                continue

            r = fetcher.fetch(url)
            if r.status in REMOVED_STATUSES:
                out.append(Verdict(url=url, bank_slug=slug, bucket=bucket,
                                   decision=DECISION_REMOVED, http_status=r.status,
                                   detail=f"HTTP {r.status} — sayfa kaldırılmış",
                                   meta_path=meta_rel))
            elif r.ok:
                if SELF_EXPIRED.search(r.html or ""):
                    out.append(Verdict(
                        url=url, bank_slug=slug, bucket=bucket,
                        decision=DECISION_SELF_EXPIRED, http_status=r.status,
                        detail="sayfa yayında ama kendini 'süresi dolmuş' "
                               "olarak işaretliyor",
                        meta_path=meta_rel))
                else:
                    out.append(Verdict(
                        url=url, bank_slug=slug, bucket=bucket,
                        decision=DECISION_STILL_LIVE, http_status=r.status,
                        detail="sayfa hâlâ yayında ve bitmiş görünmüyor — "
                               "keşif bu turda kaçırdı",
                        meta_path=meta_rel))
            else:
                out.append(Verdict(
                    url=url, bank_slug=slug, bucket=bucket,
                    decision=DECISION_UNVERIFIED, http_status=r.status,
                    detail=r.error or f"HTTP {r.status}", meta_path=meta_rel))
    finally:
        fetcher.close()
    return out


def apply_moves(verdicts: list[Verdict], raw_dir: str | Path) -> list[Verdict]:
    """`kaldirilmis` / `suresi_dolmus` kararlarını `archive/`'a TAŞIR.

    Hiçbir dosya silinmez. `.meta.json` içine `campaign_status: expired` ve
    kanıt bloğu (`removal_check`) yazılır — jüri "bunu nereden biliyorsun" diye
    sorduğunda cevap dosyanın içindedir.
    """
    root = Path(raw_dir)
    for v in verdicts:
        if v.decision not in MOVE_DECISIONS or not v.meta_path:
            continue
        meta_path = root / v.meta_path
        if not meta_path.is_file():
            v.detail += " | meta dosyası bulunamadı, taşınmadı"
            continue
        target_dir = root / v.bank_slug / ARCHIVE_SUBDIR
        target_dir.mkdir(parents=True, exist_ok=True)

        files = _sibling_files(meta_path)
        # İsim çakışması: bankanın kendi arşivinden aynı adlı belge gelmiş olabilir.
        stem = meta_path.name[: -len(".txt.meta.json")]
        suffix_n = ""
        n = 2
        while any((target_dir / f"{stem}{suffix_n}{p.name[len(stem):]}").exists()
                  for p in files):
            suffix_n = f"-onceki-{n}"
            n += 1

        for src in files:
            rest = src.name[len(stem):]
            dst = target_dir / f"{stem}{suffix_n}{rest}"
            src.replace(dst)
            v.moved.append(str(dst.relative_to(root)))

        # Provenance güncelle (taşınmış meta dosyasının yeni yolu)
        new_meta = target_dir / f"{stem}{suffix_n}.txt.meta.json"
        try:
            meta = json.loads(new_meta.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            meta = {}
        meta["campaign_status"] = STATUS_EXPIRED
        meta["removal_check"] = {
            "decision": v.decision,
            "http_status": v.http_status,
            "detail": v.detail,
            "checked_at": utc_now_iso(),
            "moved_from": f"{v.bank_slug}/{LIVE_SUBDIR}",
        }
        new_meta.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n",
                            encoding="utf-8")
    return verdicts


def render_report(verdicts: list[Verdict], *, applied: bool,
                  before_label: str = "", after_label: str = "") -> str:
    """Mutabakat raporunu markdown olarak üretir."""
    counts: dict[str, int] = {}
    for v in verdicts:
        counts[v.decision] = counts.get(v.decision, 0) + 1

    lines = [
        "# Bayat Belge Mutabakatı Raporu",
        "",
        "> Otomatik üretildi: `python -m src.scraping.reconcile_stale`. "
        "Elle düzenlemeyin.",
        "",
        f"- **Önceki tur:** `{before_label or '?'}`",
        f"- **Yeni tur:** `{after_label or '?'}`",
        f"- **Mod:** {'UYGULANDI (dosyalar taşındı)' if applied else 'KURU KOŞU (hiçbir dosya taşınmadı)'}",
        f"- **Doğrulanan kayıp URL:** {len(verdicts)}",
        "",
        "| Karar | Adet | Ne yapıldı |",
        "|---|---:|---|",
        f"| `{DECISION_REMOVED}` | {counts.get(DECISION_REMOVED, 0)} | "
        f"HTTP 404/410 → `archive/`, `campaign_status: expired` |",
        f"| `{DECISION_SELF_EXPIRED}` | {counts.get(DECISION_SELF_EXPIRED, 0)} | "
        f"sayfa kendini bitmiş ilan ediyor → `archive/`, `expired` |",
        f"| `{DECISION_SUPERSEDED}` | {counts.get(DECISION_SUPERSEDED, 0)} | "
        f"yeni turda başka kümede taze hâli var → mükerrer kopya `archive/`'a |",
        f"| `{DECISION_STILL_LIVE}` | {counts.get(DECISION_STILL_LIVE, 0)} | "
        f"**dokunulmadı** — keşif açığı (aşağıya bak) |",
        f"| `{DECISION_UNVERIFIED}` | {counts.get(DECISION_UNVERIFIED, 0)} | "
        f"**dokunulmadı** — karar verilemedi |",
        "",
    ]

    gaps = [v for v in verdicts if v.decision == DECISION_STILL_LIVE]
    lines += [
        "## Keşif Açığı — hâlâ yayında ama bu turda bulunamadı",
        "",
        "Bunlar süresi dolmuş DEĞİL: sayfa HTTP 200 dönüyor ve kendini bitmiş "
        "ilan etmiyor. Yani `banks.yaml` giriş noktaları / `detail_patterns` / "
        "`max_docs` bu sayfaları kaçırdı. Kapsamı artırmak için en somut girdi budur.",
        "",
    ]
    if gaps:
        by_bank: dict[str, list[Verdict]] = {}
        for v in gaps:
            by_bank.setdefault(v.bank_slug, []).append(v)
        lines += ["| Banka | Kaçırılan |", "|---|---:|"]
        for bank, items in sorted(by_bank.items()):
            lines.append(f"| `{bank}` | {len(items)} |")
        lines += ["", "<details><summary>URL listesi</summary>", ""]
        for bank, items in sorted(by_bank.items()):
            lines += [f"**{bank}**", ""]
            for v in items[:150]:
                lines.append(f"- `{v.url}`")
            if len(items) > 150:
                lines.append(f"- … ve {len(items) - 150} URL daha")
            lines.append("")
        lines += ["</details>", ""]
    else:
        lines += ["Keşif açığı yok — kaybolan her belge gerçekten kaldırılmış.", ""]

    for decision, title in ((DECISION_REMOVED, "Kaldırılmış belgeler"),
                            (DECISION_SELF_EXPIRED, "Süresi dolmuş belgeler"),
                            (DECISION_SUPERSEDED,
                             "Geçersiz kılınan (mükerrer) kopyalar"),
                            (DECISION_UNVERIFIED, "Doğrulanamayanlar")):
        items = [v for v in verdicts if v.decision == decision]
        lines += [f"## {title} ({len(items)})", ""]
        if not items:
            lines += ["Kayıt yok.", ""]
            continue
        lines += ["<details><summary>URL listesi</summary>", ""]
        for v in items[:200]:
            moved = f" → `{v.moved[0]}`" if v.moved else ""
            lines.append(f"- `{v.url}` — {v.detail}{moved}")
        if len(items) > 200:
            lines.append(f"- … ve {len(items) - 200} kayıt daha")
        lines += ["", "</details>", ""]
    return "\n".join(lines)


def main(argv: Optional[list[str]] = None) -> int:
    ap = argparse.ArgumentParser(
        description="Bayat belgeleri doğrula ve arşive taşı (varsayılan: kuru koşu)")
    ap.add_argument("--before", required=True, help="önceki tur manifesti")
    ap.add_argument("--after", required=True, help="yeni tur manifesti")
    ap.add_argument("--raw-dir", default="data/raw")
    ap.add_argument("--apply", action="store_true",
                    help="dosyaları GERÇEKTEN taşı (varsayılan: yalnız raporla)")
    ap.add_argument("--delay", type=float, default=3.0)
    ap.add_argument("--ignore-robots", action="store_true")
    ap.add_argument("--limit", type=int, default=None,
                    help="yalnızca ilk N kayıp URL'i doğrula (deneme için)")
    ap.add_argument("--out", default="", help="markdown rapor yolu")
    ap.add_argument("--json-out", default="")
    args = ap.parse_args(argv)

    before = json.loads(Path(args.before).read_text(encoding="utf-8"))
    after = json.loads(Path(args.after).read_text(encoding="utf-8"))

    verdicts = verify_stale(before, after, args.raw_dir, delay_s=args.delay,
                            ignore_robots=args.ignore_robots, limit=args.limit)
    if args.apply:
        verdicts = apply_moves(verdicts, args.raw_dir)

    counts: dict[str, int] = {}
    for v in verdicts:
        counts[v.decision] = counts.get(v.decision, 0) + 1
    print(f"{'UYGULANDI' if args.apply else 'KURU KOSU'} — {len(verdicts)} kayip URL")
    for k in (DECISION_REMOVED, DECISION_SELF_EXPIRED, DECISION_SUPERSEDED,
              DECISION_STILL_LIVE, DECISION_UNVERIFIED):
        print(f"  {k}: {counts.get(k, 0)}")
    unknown = set(counts) - {DECISION_REMOVED, DECISION_SELF_EXPIRED,
                             DECISION_SUPERSEDED, DECISION_STILL_LIVE,
                             DECISION_UNVERIFIED}
    for k in sorted(unknown):  # yeni karar eklenirse sessizce kaybolmasın
        print(f"  {k}: {counts[k]}")

    report = render_report(verdicts, applied=args.apply,
                           before_label=before.get("label", ""),
                           after_label=after.get("label", ""))
    if args.out:
        p = Path(args.out)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(report, encoding="utf-8")
        print(f"Rapor: {p}")
    if args.json_out:
        p = Path(args.json_out)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps([v.to_json() for v in verdicts],
                                ensure_ascii=False, indent=1) + "\n",
                     encoding="utf-8")
        print(f"JSON: {p}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
