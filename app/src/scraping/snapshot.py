"""Hasat anlık görüntüsü (snapshot) — manifest üretimi ve iki tur arası fark.

İlgili: CLAUDE.md §14 (provenance), §6 (zor anlama vakaları),
        ../../decisions/python-tabanli-veri-toplama.md

NEDEN: Bankalar kampanyaları **aylık** yeniliyor. İki hasat turu arasındaki fark,
sentetik olmayan zamansal etiket üretir:

- **kayip**   : önceki turda vardı, şimdi yok → kampanya süresi doldu / kaldırıldı
- **yeni**    : yalnızca yeni turda var → yeni yayımlanan kampanya
- **degisti** : aynı URL, farklı `content_hash` → koşul/oran güncellenmiş
- **ayni**    : içerik birebir aynı

Bu etiketler `comparison/contradiction.py` ve `suresi_dolmus_kampanya` kuralı için
gerçek doğrulama kümesidir; gold sette elle işaretlemeye gerek kalmaz.

Manifest, ham HTML'i kopyalamaz — yalnızca provenance özetini tutar (69 MB'lık
korpusu ikiye katlamamak için). `.meta.json` sidecar'ları kaynak alınır.

Kullanım:
    python -m src.scraping.snapshot build --raw-dir data/raw \
        --out data/snapshots/2026-07-30.json --label 2026-07-30
    python -m src.scraping.snapshot diff --before data/snapshots/2026-07-30.json \
        --after data/snapshots/2026-08-03.json --out data/snapshots/diff-report.md
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Optional

MANIFEST_VERSION = 1

# Belge kümesi (subdir) → anlam. Karşılaştırma yalnızca aynı kümeler arasında
# yapılır; ürün sayfası ile kampanya sayfası kıyaslanmaz (CLAUDE.md §17 adil kıyas).
KNOWN_BUCKETS = ("live", "archive", "products", "docs", "manual")


@dataclass
class Entry:
    """Manifestteki tek belge kaydı."""

    url: str
    bank_slug: str
    bucket: str
    content_hash: Optional[str] = None
    title: Optional[str] = None
    text_chars: Optional[int] = None
    scraped_at: Optional[str] = None
    path: Optional[str] = None
    text_hash: Optional[str] = None

    def to_json(self) -> dict[str, Any]:
        return {
            "url": self.url, "bank_slug": self.bank_slug, "bucket": self.bucket,
            "content_hash": self.content_hash, "text_hash": self.text_hash,
            "title": self.title,
            "text_chars": self.text_chars, "scraped_at": self.scraped_at,
            "path": self.path,
        }


def _text_hash(content: str) -> str:
    """Temiz metnin sha256'sı — boşluk gürültüsü normalize edilerek.

    NEDEN `content_hash` YETMEZ: provenance'taki `content_hash` HAM HTML'in
    özetidir (tekilleştirme için doğru seçim). Ama sayfadaki analitik kimlikleri,
    oturum/CSRF simgeleri ve zaman damgaları her istekte değişir; bu yüzden
    kampanya metni HİÇ değişmese bile HTML hash'i değişir.

    Ölçüm (2026-08-03): ham HTML hash'iyle 238 belge "değişmiş" görünüyordu;
    `git diff` ile bakıldığında `.txt` içerikleri BİREBİR AYNIYDI. Fark raporunun
    işe yarar olması için karşılaştırma TEMİZ METİN üzerinden yapılmalıdır.
    """
    import hashlib

    normalized = re.sub(r"\s+", " ", content).strip()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


class _GitTextReader:
    """`.txt` içeriklerini bir git ref'inden okur (`git cat-file --batch`).

    Yeniden hasat çalışma kopyasındaki `.txt`'leri EZDİĞİ için önceki turun
    metinleri yalnızca git geçmişinde kalır. Önceki tur manifestini doğru
    kurmanın tek yolu budur.
    """

    def __init__(self, ref: str, repo_prefix: str = "") -> None:
        self.ref = ref
        self.prefix = repo_prefix
        self._proc = None

    def _ensure(self):
        if self._proc is None:
            import subprocess

            self._proc = subprocess.Popen(
                ["git", "cat-file", "--batch"], stdin=subprocess.PIPE,
                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        return self._proc

    def read(self, repo_rel_path: str) -> Optional[str]:
        p = self._ensure()
        spec = f"{self.ref}:{self.prefix}{repo_rel_path}"
        try:
            p.stdin.write((spec + "\n").encode("utf-8"))
            p.stdin.flush()
            header = p.stdout.readline().decode("utf-8", "replace").strip()
            if not header or header.endswith(("missing", "ambiguous")):
                return None
            size = int(header.rsplit(" ", 1)[-1])
            blob = p.stdout.read(size)
            p.stdout.read(1)  # kapanış '\n'
            return blob.decode("utf-8", "replace")
        except (OSError, ValueError):
            return None

    def list_meta(self) -> list[str]:
        """Ref'teki `.meta.json` dosyalarını `raw_dir`'e göreli yollar olarak verir.

        Çalışma kopyasını taramak YETMEZ: yeniden hasat `.meta.json`'ları da ezer,
        bu yüzden önceki turun kaydı yalnızca git'te kalır.
        """
        import subprocess

        # `ls-tree` yol belirtimi ÇALIŞMA DİZİNİNE göredir, `cat-file` ref yolu ise
        # DEPO KÖKÜNE göre. İkisini hizalamak için komut depo kökünde koşturulur.
        try:
            top = subprocess.run(["git", "rev-parse", "--show-toplevel"],
                                 capture_output=True, text=True, check=True
                                 ).stdout.strip()
            out = subprocess.run(
                ["git", "ls-tree", "-r", "--name-only", self.ref,
                 "--", self.prefix or "."],
                cwd=top or None, capture_output=True, text=True, check=True)
        except (OSError, subprocess.CalledProcessError):
            return []
        cut = len(self.prefix)
        return sorted(line[cut:] for line in out.stdout.splitlines()
                      if line.endswith(".meta.json") and line.startswith(self.prefix))

    def close(self) -> None:
        if self._proc is not None:
            try:
                self._proc.stdin.close()
                self._proc.terminate()
            except OSError:
                pass
            self._proc = None


def _bucket_for(path: Path, raw_dir: Path) -> str:
    """Dosyanın hangi toplama turuna ait olduğunu yolundan çıkarır."""
    try:
        parts = path.relative_to(raw_dir).parts
    except ValueError:
        parts = path.parts
    for part in parts:
        if part in KNOWN_BUCKETS:
            return part
    return "diger"


def _repo_prefix(raw_dir: Path) -> str:
    """`raw_dir`'in depo kökünden göreli öneki (git yolları için)."""
    import subprocess

    try:
        out = subprocess.run(["git", "rev-parse", "--show-prefix"],
                             cwd=raw_dir if raw_dir.is_dir() else Path.cwd(),
                             capture_output=True, text=True, check=True)
        return out.stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return ""


def build_manifest(raw_dir: str | Path, label: str = "",
                   since: str = "", from_git: str = "") -> dict[str, Any]:
    """`data/raw/` altındaki `.meta.json` sidecar'larından manifest üretir.

    URL yoksa (fixture dosyaları) kayıt atlanır — karşılaştırmanın birimi URL'dir.

    `since` (ISO-8601) verilirse yalnızca o andan SONRA toplanmış belgeler alınır.
    NEDEN ŞART: yeniden hasat eski dosyaları SİLMEZ, üzerine yazar. Sitede artık
    olmayan bir Temmuz kampanyası `live/` altında öylece kalır. `since` süzgeci
    olmadan yeni manifest o bayat dosyayı da içerir ve fark raporu onu "hâlâ
    yayında" sanır — yani `kayip` kümesi sessizce boşalır.
    """
    root = Path(raw_dir)
    entries: list[Entry] = []
    skipped = 0
    stale = 0
    no_text = 0
    reader = _GitTextReader(from_git, _repo_prefix(root)) if from_git else None
    try:
        if reader is not None:
            # Git modunda hem LİSTE hem İÇERİK ref'ten gelir.
            meta_rels = reader.list_meta()
        else:
            meta_rels = [str(p.relative_to(root))
                         for p in sorted(root.rglob("*.meta.json"))]
        for meta_rel in meta_rels:
            meta_path = root / meta_rel
            raw_meta = reader.read(meta_rel) if reader is not None else (
                meta_path.read_text(encoding="utf-8")
                if meta_path.is_file() else None)
            try:
                meta = json.loads(raw_meta) if raw_meta else None
            except ValueError:
                meta = None
            if meta is None:
                skipped += 1
                continue
            url = meta.get("source_url") or ""
            if not url or url.startswith("file://"):
                skipped += 1
                continue
            if since and (meta.get("scraped_at") or "") < since:
                stale += 1
                continue
            rel = meta_path.relative_to(root)
            txt_rel = str(rel)[: -len(".meta.json")]
            if reader is not None:
                body = reader.read(txt_rel)
            else:
                txt_path = root / txt_rel
                body = txt_path.read_text(encoding="utf-8", errors="replace") \
                    if txt_path.is_file() else None
            if body is None:
                no_text += 1
            entries.append(Entry(
                url=_canonical(url),
                bank_slug=meta.get("bank_slug") or _bank_from_path(meta_path, root),
                bucket=_bucket_for(meta_path, root),
                content_hash=meta.get("content_hash"),
                text_hash=_text_hash(body) if body is not None else None,
                title=meta.get("title"),
                text_chars=meta.get("text_chars"),
                scraped_at=meta.get("scraped_at"),
                path=str(rel),
            ))
    finally:
        if reader is not None:
            reader.close()
    return {
        "manifest_version": MANIFEST_VERSION,
        "label": label,
        "raw_dir": str(root),
        "since": since or None,
        "text_source": f"git:{from_git}" if from_git else "worktree",
        "entry_count": len(entries),
        "skipped": skipped,
        "stale_excluded": stale,
        "text_missing": no_text,
        "by_bank": _count_by(entries, lambda e: e.bank_slug),
        "by_bucket": _count_by(entries, lambda e: e.bucket),
        "entries": [e.to_json() for e in entries],
    }


def _bank_from_path(meta_path: Path, root: Path) -> str:
    try:
        return meta_path.relative_to(root).parts[0]
    except (ValueError, IndexError):
        return "bilinmiyor"


def _canonical(url: str) -> str:
    """Karşılaştırma anahtarı: şema/host küçük harf, sondaki '/' atılır."""
    from urllib.parse import urlsplit, urlunsplit

    p = urlsplit(url.strip())
    path = p.path[:-1] if len(p.path) > 1 and p.path.endswith("/") else p.path
    return urlunsplit((p.scheme.lower(), p.netloc.lower(), path, p.query, ""))


def _count_by(entries: Iterable[Entry], key) -> dict[str, int]:
    out: dict[str, int] = {}
    for e in entries:
        out[key(e)] = out.get(key(e), 0) + 1
    return dict(sorted(out.items()))


# --------------------------------------------------------------------------- #
# Fark (diff)
# --------------------------------------------------------------------------- #

@dataclass
class DiffResult:
    """İki manifest arasındaki fark; her liste (bank_slug, url, title) taşır."""

    kayip: list[dict[str, Any]] = field(default_factory=list)
    yeni: list[dict[str, Any]] = field(default_factory=list)
    degisti: list[dict[str, Any]] = field(default_factory=list)
    ayni: int = 0
    before_label: str = ""
    after_label: str = ""

    def summary(self) -> dict[str, int]:
        return {"kayip": len(self.kayip), "yeni": len(self.yeni),
                "degisti": len(self.degisti), "ayni": self.ayni}


def diff_manifests(before: dict[str, Any], after: dict[str, Any]) -> DiffResult:
    """Aynı bucket içindeki URL kümelerini karşılaştırır.

    Bucket'lar ayrı tutulur: bir kampanya `live/`'dan `archive/`'a taşındıysa bu
    "kayıp" değil **arşivlenme**dir; rapor bunu ayrıca işaretler.
    """
    b_index = {(e["bucket"], e["url"]): e for e in before.get("entries", [])}
    a_index = {(e["bucket"], e["url"]): e for e in after.get("entries", [])}
    # URL'in hangi bucket'larda göründüğü — arşive taşınma tespiti için
    a_urls_any_bucket: dict[str, set[str]] = {}
    for bucket, url in a_index:
        a_urls_any_bucket.setdefault(url, set()).add(bucket)

    res = DiffResult(before_label=before.get("label", ""),
                     after_label=after.get("label", ""))

    for key, entry in b_index.items():
        bucket, url = key
        if key in a_index:
            other = a_index[key]
            # TEMİZ METİN hash'i tercih edilir; ham HTML hash'i analitik/oturum
            # gürültüsüyle her istekte değişir ve 238 yalancı "değişti" üretiyordu
            # (gerekçe: `_text_hash` docstring'i). İkisi de yoksa aynı sayılır.
            before_h = entry.get("text_hash") or entry.get("content_hash")
            after_h = other.get("text_hash") or other.get("content_hash")
            basis = "metin" if (entry.get("text_hash") and other.get("text_hash")) \
                else "ham-html"
            if before_h and after_h and before_h != after_h:
                res.degisti.append({
                    **_slim(entry),
                    "karsilastirma": basis,
                    "onceki_hash": before_h,
                    "yeni_hash": after_h,
                    "onceki_char": entry.get("text_chars"),
                    "yeni_char": other.get("text_chars"),
                })
            else:
                res.ayni += 1
            continue
        # URL bu bucket'ta yok — başka bucket'ta mı? (arşive taşınmış olabilir)
        other = sorted(a_urls_any_bucket.get(url, set()))
        res.kayip.append({**_slim(entry), "yeni_bucket": other or None})

    for key, entry in a_index.items():
        if key not in b_index:
            res.yeni.append(_slim(entry))
    return res


def _slim(entry: dict[str, Any]) -> dict[str, Any]:
    return {
        "bank_slug": entry.get("bank_slug"),
        "bucket": entry.get("bucket"),
        "url": entry.get("url"),
        "title": entry.get("title"),
    }


def render_diff(res: DiffResult) -> str:
    """Farkı markdown rapor olarak üretir (jüri/dokümantasyon için)."""
    s = res.summary()
    lines = [
        "# Hasat Turları Arası Fark Raporu",
        "",
        "> Otomatik üretildi: `python -m src.scraping.snapshot diff`. "
        "Elle düzenlemeyin.",
        "",
        f"- **Önceki tur:** `{res.before_label or 'etiketsiz'}`",
        f"- **Yeni tur:** `{res.after_label or 'etiketsiz'}`",
        "",
        "| Durum | Adet | Anlamı |",
        "|---|---:|---|",
        f"| `kayip` | {s['kayip']} | Önceki turda vardı, yeni turda yok → süresi doldu / kaldırıldı |",
        f"| `yeni` | {s['yeni']} | Yalnızca yeni turda var → yeni yayımlanan |",
        f"| `degisti` | {s['degisti']} | Aynı URL, farklı içerik → koşul/oran güncellenmiş |",
        f"| `ayni` | {s['ayni']} | İçerik birebir aynı |",
        "",
        "## Neden değerli",
        "",
        "`kayip` ve `degisti` kümeleri, `suresi_dolmus_kampanya` kuralı ile "
        "zaman-koşullu çelişki tespiti için **elle işaretlemeye gerek olmayan** "
        "doğrulama verisidir (CLAUDE.md §6, §18-2).",
        "",
    ]

    def table(title: str, rows: list[dict[str, Any]], extra: str = "") -> None:
        lines.extend([f"## {title} ({len(rows)})", ""])
        if not rows:
            lines.extend(["Kayıt yok.", ""])
            return
        by_bank: dict[str, list[dict[str, Any]]] = {}
        for r in rows:
            by_bank.setdefault(r.get("bank_slug") or "?", []).append(r)
        lines.extend(["| Banka | Adet |", "|---|---:|"])
        for bank, items in sorted(by_bank.items()):
            lines.append(f"| `{bank}` | {len(items)} |")
        lines.append("")
        lines.append("<details><summary>URL listesi</summary>")
        lines.append("")
        for bank, items in sorted(by_bank.items()):
            lines.append(f"**{bank}**")
            lines.append("")
            for r in items[:200]:
                suffix = ""
                if extra == "degisti":
                    suffix = (f" — {r.get('onceki_char')} → {r.get('yeni_char')} krkt")
                elif extra == "kayip" and r.get("yeni_bucket"):
                    suffix = f" — **{'/'.join(r['yeni_bucket'])} kümesine taşındı**"
                title = (r.get("title") or "").strip()
                lines.append(f"- `{r['url']}`{suffix}"
                             + (f"<br>{title}" if title else ""))
            if len(items) > 200:
                lines.append(f"- … ve {len(items) - 200} kayıt daha")
            lines.append("")
        lines.extend(["</details>", ""])

    table("Kaybolan belgeler", res.kayip, extra="kayip")
    table("Yeni belgeler", res.yeni)
    table("İçeriği değişen belgeler", res.degisti, extra="degisti")
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #

def main(argv: Optional[list[str]] = None) -> int:
    ap = argparse.ArgumentParser(
        description="Hasat anlık görüntüsü — manifest üret / iki turu karşılaştır")
    sub = ap.add_subparsers(dest="cmd", required=True)

    b = sub.add_parser("build", help="data/raw'dan manifest üret")
    b.add_argument("--raw-dir", default="data/raw")
    b.add_argument("--out", required=True)
    b.add_argument("--label", default="", help="tur etiketi (ör. 2026-07-30)")
    b.add_argument("--since", default="",
                   help="yalnızca bu ISO andan sonra toplananlar "
                        "(bayat dosyaları dışlar — modül docstring'ine bak)")
    b.add_argument("--from-git", default="",
                   help="`.txt` içeriklerini bu git ref'inden oku (ör. HEAD). "
                        "Önceki tur manifesti için ŞART: yeniden hasat çalışma "
                        "kopyasındaki metinleri ezer.")

    d = sub.add_parser("diff", help="iki manifesti karşılaştır")
    d.add_argument("--before", required=True)
    d.add_argument("--after", required=True)
    d.add_argument("--out", default="", help="markdown rapor yolu")
    d.add_argument("--json-out", default="", help="ham fark JSON'u")

    args = ap.parse_args(argv)

    if args.cmd == "build":
        man = build_manifest(args.raw_dir, label=args.label, since=args.since,
                             from_git=args.from_git)
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(man, ensure_ascii=False, indent=1) + "\n",
                       encoding="utf-8")
        print(f"Manifest: {out} — {man['entry_count']} kayit "
              f"({man['skipped']} atlandi, {man['stale_excluded']} bayat dislandi)")
        for bucket, n in man["by_bucket"].items():
            print(f"  {bucket}: {n}")
        return 0

    before = json.loads(Path(args.before).read_text(encoding="utf-8"))
    after = json.loads(Path(args.after).read_text(encoding="utf-8"))
    res = diff_manifests(before, after)
    print(f"Fark: {res.summary()}")
    if args.out:
        p = Path(args.out)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(render_diff(res), encoding="utf-8")
        print(f"Rapor: {p}")
    if args.json_out:
        p = Path(args.json_out)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps({
            "before_label": res.before_label, "after_label": res.after_label,
            "summary": res.summary(), "kayip": res.kayip, "yeni": res.yeni,
            "degisti": res.degisti,
        }, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        print(f"JSON: {p}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
