"""`live/` belgelerini üç hâle ayırır: damgalı (bitmiş), temiz (aktif),
belirsiz (karar verilmez).

İlgili: src/scraping/expiry_stamp.py (damga deseni — TEK KAYNAK)
        src/scraping/reconcile_stale.py (ağ tabanlı kardeş geçiş)
        docs/rapor/suresi-dolmus-damgasi.md (ölçümler ve desen kararları)
        docs/rapor/bayat-veri-mutabakati.md §5 (bu boşluğun ölçüldüğü yer)

## Sorun — bayat döngüsünün ULAŞAMADIĞI kampanyalar

`reconcile_stale` yalnız **kaybolan** URL'leri yakalar. Ama bir kampanya
kaybolmadan da biter: banka sayfayı yayında bırakıp üstüne "Kampanya
24-05-2026 Tarihinde Sona Ermiştir" damgası basar. Bu belgeler her turda
yeniden toplanır, `kayip` kümesine hiç düşmez, dolayısıyla mutabakat onlara
**hiçbir zaman** ulaşamaz.

Ölçüldü (2026-08-10, 772 `live/` belge): bunların **221'i (%28,6)** sayfasında
açık damga taşıyor. Kapanmış kampanya açık kampanyayla aynı kolonda
sıralandığı için bu, adil kıyası (CLAUDE.md §17) doğrudan bozar.

## `active` ataması (eklendi, 2026-08-25)

`collector.STATUS_ACTIVE` tanımlıydı ama hiçbir kod yolu tarafından hiç
ATANMIYORDU — ölçüldü: dashboard'un "Kampanya Durumu" panelinde `aktif`
sürekli **0** görünüyordu, korpus güncel olsa da. Bu geçiş boşluğu kapatır:
"temiz" (bu hasatta çekildi, bitmişlik damgası yok) her belge, başka bir
mekanizma (`reconcile_stale`, hasatçı) zaten bir `campaign_status` yazmadıysa
`active` alır. "Belirsiz" (geniş desen ateşliyor ama damga değil) hâlâ karar
almaz — aynı temkinli ilke burada da geçerli: emin olunmayan belgeye ne
"bitmiş" ne "aktif" denir.

## Bu geçiş ne yapar / ne YAPMAZ

- **Ağa çıkmaz.** Yalnız yerel temiz metni (`<slug>.txt`) okur; robots/hız
  sınırı gerektiren hiçbir şey yapmaz.
- **Dosya taşımaz, silmez.** Karar `<slug>.txt.meta.json` içine yazılır.
- **Provenance'a dokunmaz.** `source_url` / `scraped_at` / `content_hash`
  olduğu gibi kalır; üstüne `campaign_status` + `expiry_stamp` (bitmiş) ya da
  `active_stamp` (aktif) kanıt bloğu eklenir.

### Neden taşıma değil işaretleme

1. `pipeline.collect_corpus` `data/raw/<banka>/` altını ÖZYİNELEMELİ okur;
   `archive/` de okunuyor. Yani taşımak belgeyi kıyastan ÇIKARMAZ — taşımanın
   tek başına hiçbir aşağı akış etkisi yok, `campaign_status` alanının ise var
   (alan `collector.STATUS_EXPIRED` ile zaten tanımlı).
2. `archive/` bu korpusta "bankanın KENDİ arşiv bölümünden toplandı" demektir
   (`harvest_extra` + `discover_archive`). Bu belgeler bankanın CANLI
   bölümünden toplandı; taşımak toplama provenance'ını yanlışlar.
3. Taşıma bir sonraki hasatta MÜKERRER kayıt üretir: aynı URL yine `live/`
   altına yazılır ve arşivdeki kopyanın yanında ikinci bir belge oluşur —
   `reconcile_stale`'in Kuveyt Türk'te 33 belgeyle temizlemek zorunda kaldığı
   sorunun aynısı. İşaretleme her hasattan sonra yeniden türetilebilir.

Bu yüzden geçiş **her hasat turundan sonra** koşmalıdır (hasat `.meta.json`'ı
yeniden yazar ve işareti siler; bu bir kusur değil, işaretin veriden
türetilebilir kalmasıdır).

Kullanım:
    .venv/bin/python -m scripts.damga_isaretle                     # kuru koşu
    .venv/bin/python -m scripts.damga_isaretle --uygula \\
        --out docs/rapor/... --json-out data/snapshots/...
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.scraping.collector import (
    LIVE_SUBDIR,
    STATUS_ACTIVE,
    STATUS_EXPIRED,
    utc_now_iso,
)
from src.scraping.expiry_stamp import ExpiryStamp, find_expiry_stamp

#: `expiry_stamp` bloğunu kimin yazdığı. Yalnız KENDİ yazdığımız işareti
#: geri alırız; hasatçının veya `reconcile_stale`'in yazdığına dokunmayız.
ISARETLEYEN = "damga_isaretle"

#: Düzeltmeden önceki geniş desen — yalnız BELİRSİZ kolonunu üretmek için.
#: Bu desenin ateşleyip dar desenin ateşlemediği belge "bitmiş" DEĞİLDİR;
#: "karar verilmedi"dir ve raporda görünür kalması gerekir (CLAUDE.md §19).
GENIS_DESEN = re.compile(
    r"(s[üu]resi\s+dolmu[şs]|sona\s+erdi|sona\s+ermi[şs]|"
    r"biten\s+kampanya|ge[çc]mi[şs]\s+kampanya)", re.IGNORECASE)

CORPUS_SUFFIX = ".txt"
META_SUFFIX = ".meta.json"


@dataclass
class Bulgu:
    """Tek belge için tarama sonucu."""

    bank_slug: str
    bucket: str
    meta_path: str          # raw_dir'e göreli
    source_url: Optional[str]
    durum: str              # "damgali" | "belirsiz" | "temiz"
    stamp: Optional[ExpiryStamp] = None
    yazildi: bool = False
    geri_alindi: bool = False

    def to_json(self) -> dict[str, Any]:
        return {"bank_slug": self.bank_slug, "bucket": self.bucket,
                "meta_path": self.meta_path, "source_url": self.source_url,
                "durum": self.durum, "yazildi": self.yazildi,
                "geri_alindi": self.geri_alindi,
                "stamp": self.stamp.to_json() if self.stamp else None}


@dataclass
class Sayim:
    belge: int = 0
    damgali: int = 0
    belirsiz: int = 0
    tarihli: int = 0
    bitis_aylari: dict[str, int] = field(default_factory=dict)


def _meta_oku(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return {}
    return data if isinstance(data, dict) else {}


def tara(raw_dir: str | Path, *,
         buckets: tuple[str, ...] = (LIVE_SUBDIR,)) -> list[Bulgu]:
    """Korpusu tarar, karar verir. Diske DOKUNMAZ."""
    kok = Path(raw_dir)
    out: list[Bulgu] = []
    for bucket in buckets:
        for txt in sorted(kok.glob(f"*/{bucket}/*{CORPUS_SUFFIX}")):
            if txt.name.endswith(META_SUFFIX) or not txt.is_file():
                continue
            metin = txt.read_text(encoding="utf-8", errors="replace")
            meta_path = txt.with_suffix(txt.suffix + META_SUFFIX)
            meta = _meta_oku(meta_path)
            stamp = find_expiry_stamp(metin)
            if stamp is not None:
                durum = "damgali"
            elif GENIS_DESEN.search(metin):
                durum = "belirsiz"
            else:
                durum = "temiz"
            out.append(Bulgu(
                bank_slug=meta.get("bank_slug") or txt.parts[-3],
                bucket=bucket,
                meta_path=str(meta_path.relative_to(kok)),
                source_url=meta.get("source_url"),
                durum=durum, stamp=stamp))
    return out


def isaretle(bulgular: list[Bulgu], raw_dir: str | Path) -> list[Bulgu]:
    """`damgali`/`temiz` bulguları `.meta.json`'a yazar; eskiyen işareti geri alır.

    `damgali` → `campaign_status=expired` + `expiry_stamp` kanıtı.
    `temiz`   → `campaign_status=active` + `active_stamp` kanıtı (yalnız
                başka bir mekanizma zaten bir durum yazmamışsa).
    `belirsiz` → hiçbir zaman yeni durum yazılmaz; ÖNCEDEN bizim yazdığımız
                bir durum varsa geri alınır (belge belirsizleşti).

    Hiçbir dosya taşınmaz/silinmez. Yazma İDEMPOTENTtir: aynı karar ikinci kez
    koşulduğunda dosya değişmez (`checked_at` dâhil), böylece gereksiz git
    gürültüsü çıkmaz.
    """
    kok = Path(raw_dir)
    simdi = utc_now_iso()
    for b in bulgular:
        meta_path = kok / b.meta_path
        if not meta_path.is_file():
            continue
        meta = _meta_oku(meta_path)
        onceki_damga = meta.get("expiry_stamp")
        bizim_damga = (isinstance(onceki_damga, dict)
                      and onceki_damga.get("marked_by") == ISARETLEYEN)
        onceki_aktif = meta.get("active_stamp")
        bizim_aktif = (isinstance(onceki_aktif, dict)
                      and onceki_aktif.get("marked_by") == ISARETLEYEN)
        bizim = bizim_damga or bizim_aktif

        if b.durum == "damgali":
            yeni = dict(b.stamp.to_json())
            yeni["marked_by"] = ISARETLEYEN
            yeni["source"] = "metin-damgasi"
            yeni["bucket"] = b.bucket
            # İdempotanlık: damga aynıysa `checked_at`'i koru, dosyaya dokunma.
            if bizim_damga and {k: onceki_damga.get(k) for k in yeni} == yeni \
                    and meta.get("campaign_status") == STATUS_EXPIRED:
                continue
            yeni["checked_at"] = (onceki_damga.get("checked_at")
                                  if bizim_damga else None) or simdi
            meta["campaign_status"] = STATUS_EXPIRED
            meta["expiry_stamp"] = yeni
            # Önceki turda "temiz" bulunup AKTİF işaretlenmiş olabilir —
            # kampanya iki hasat arasında bitmiş demektir; eski işaret
            # yanlış hâle geldi, kaldır.
            meta.pop("active_stamp", None)
            b.yazildi = True
        elif b.durum == "temiz":
            # Sayfa yayında (bu `live/` hasadında), bitmişlik damgası YOK.
            # Bu, `reconcile_stale.py`nin kendi karar tablosundaki "200 +
            # normal içerik → duruyor" satırının POZİTİF karşılığıdır: o
            # satır şimdiye kadar hiçbir yerde `campaign_status` YAZMIYORDU
            # (ölçüldü, 2026-08-25 — `collector.STATUS_ACTIVE` tanımlı ama
            # hiçbir kod yolu tarafından hiç atanmıyordu, dashboard'da
            # "aktif: 0" olarak görünüyordu). "Temiz" ile "aktif" arasındaki
            # fark BİLEREK küçük tutuluyor: aktiflik burada "bu hasatta
            # sayfa çekildi ve kendini bitmiş ilan etmiyor" demektir —
            # "kullanıcı bugün başvurabilir" gibi daha güçlü bir iddia
            # DEĞİLDİR (o iddia ağ tabanlı `reconcile_stale`'in işi).
            if meta.get("campaign_status") is not None and not bizim:
                # Başka bir mekanizma (hasatçı, reconcile_stale, elle) zaten
                # bir durum yazmış — üstüne yazma, ona ait (bkz. testteki
                # `test_baskasinin_isaretine_dokunulmaz`).
                continue
            if bizim_aktif and meta.get("campaign_status") == STATUS_ACTIVE:
                continue  # idempotanlık: değişiklik yok, dosyaya dokunma
            meta["campaign_status"] = STATUS_ACTIVE
            meta["active_stamp"] = {
                "marked_by": ISARETLEYEN,
                "source": "hasat-damgasiz",
                "bucket": b.bucket,
                "checked_at": (onceki_aktif.get("checked_at")
                               if bizim_aktif else None) or simdi,
            }
            # Önceki turda damgalıydı, bu turda damga kalktı: eski işareti
            # de kaldır (yoksa iki çelişen alan bir arada kalırdı).
            meta.pop("expiry_stamp", None)
            b.yazildi = True
        elif bizim:
            # "belirsiz": karar verilmiyor (bkz. modül başlığı). Belge
            # ÖNCEDEN bizim tarafımızdan damgalı/aktif işaretlenmişse, o
            # işaret artık geçerli değil — geri alınır. Başkasının yazdığı
            # `campaign_status`'a dokunulmaz.
            meta.pop("expiry_stamp", None)
            meta.pop("active_stamp", None)
            if meta.get("campaign_status") in (STATUS_EXPIRED, STATUS_ACTIVE):
                meta.pop("campaign_status", None)
            b.geri_alindi = True
        else:
            continue

        meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n",
                             encoding="utf-8")
    return bulgular


def sayimlar(bulgular: list[Bulgu]) -> dict[str, Sayim]:
    out: dict[str, Sayim] = {}
    for b in bulgular:
        s = out.setdefault(b.bank_slug, Sayim())
        s.belge += 1
        if b.durum == "damgali":
            s.damgali += 1
            if b.stamp and b.stamp.end_date:
                s.tarihli += 1
                ay = b.stamp.end_date[:7]
                s.bitis_aylari[ay] = s.bitis_aylari.get(ay, 0) + 1
        elif b.durum == "belirsiz":
            s.belirsiz += 1
    return out


def render_report(bulgular: list[Bulgu], *, applied: bool,
                  raw_dir: str, buckets: tuple[str, ...]) -> str:
    """Markdown rapor üretir."""
    say = sayimlar(bulgular)
    toplam = Sayim()
    aylar: dict[str, int] = {}
    for s in say.values():
        toplam.belge += s.belge
        toplam.damgali += s.damgali
        toplam.belirsiz += s.belirsiz
        toplam.tarihli += s.tarihli
        for ay, n in s.bitis_aylari.items():
            aylar[ay] = aylar.get(ay, 0) + n

    def oran(a: int, b: int) -> str:
        return f"%{100.0 * a / b:.1f}".replace(".", ",") if b else "—"

    lines = [
        "# Damga Tabanlı Bitmişlik İşaretlemesi",
        "",
        "> Otomatik üretildi: `python -m scripts.damga_isaretle`. "
        "Elle düzenlemeyin.",
        "",
        f"- **Korpus:** `{raw_dir}` · bölümler: "
        f"{', '.join(f'`{b}/`' for b in buckets)}",
        f"- **Mod:** "
        f"{'UYGULANDI (.meta.json yazıldı)' if applied else 'KURU KOŞU (hiçbir dosya değişmedi)'}",
        "- **Ağ isteği:** yok (yalnız yerel temiz metin taraması)",
        "- **Taşınan/silinen dosya:** yok",
        "",
        "| Karar | Adet | Oran | Anlamı |",
        "|---|---:|---:|---|",
        f"| `damgali` | {toplam.damgali} | {oran(toplam.damgali, toplam.belge)} | "
        f"sayfa kendini bitmiş ilan ediyor → `campaign_status: expired` |",
        f"| `belirsiz` | {toplam.belirsiz} | {oran(toplam.belirsiz, toplam.belge)} | "
        f"geniş desen ateşliyor ama damga değil → **karar verilmedi**, dokunulmadı |",
        f"| `temiz` | {toplam.belge - toplam.damgali - toplam.belirsiz} | "
        f"{oran(toplam.belge - toplam.damgali - toplam.belirsiz, toplam.belge)} | "
        f"bitmişlik işareti yok → `campaign_status: active` "
        f"(başka bir mekanizma zaten yazmadıysa) |",
        "",
        "`belirsiz` satırı bilerek ayrı: o belgelerde eşleşen şey menü "
        "bağlantısı, ihtar kalıbı ya da başka bir kampanyanın damgası olabilir. "
        "Emin olunmayan belgeye \"kapanmış\" demek veri uydurmaktır "
        "(CLAUDE.md §19).",
        "",
        "## Banka bazında",
        "",
        "| Banka | Belge | Damgalı | Oran | Belirsiz | Bitiş tarihi okunan |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for bank in sorted(say, key=lambda k: (-say[k].damgali, k)):
        s = say[bank]
        lines.append(f"| `{bank}` | {s.belge} | {s.damgali} | "
                     f"{oran(s.damgali, s.belge)} | {s.belirsiz} | {s.tarihli} |")
    lines += [f"| **TOPLAM** | **{toplam.belge}** | **{toplam.damgali}** | "
              f"**{oran(toplam.damgali, toplam.belge)}** | "
              f"**{toplam.belirsiz}** | **{toplam.tarihli}** |", ""]

    if aylar:
        lines += ["## Damgadan okunan bitiş tarihleri", "",
                  f"{toplam.tarihli} belgede bitiş tarihi damgaya YAPIŞIK "
                  f"olarak yazılı; kalan {toplam.damgali - toplam.tarihli} "
                  f"belgede damga tarih taşımıyor ve tarih UYDURULMADI.", "",
                  "| Bitiş ayı | Belge |", "|---|---:|"]
        for ay in sorted(aylar):
            lines.append(f"| {ay} | {aylar[ay]} |")
        lines.append("")

    damgalilar = [b for b in bulgular if b.durum == "damgali"]
    lines += [f"## Damgalı belgeler ({len(damgalilar)})", "",
              "<details><summary>Liste</summary>", ""]
    for b in damgalilar[:400]:
        tarih = b.stamp.end_date if b.stamp and b.stamp.end_date else "—"
        lines.append(f"- `{b.meta_path}` — «{b.stamp.phrase}» · bitiş: {tarih}")
    if len(damgalilar) > 400:
        lines.append(f"- … ve {len(damgalilar) - 400} belge daha")
    lines += ["", "</details>", ""]

    belirsizler = [b for b in bulgular if b.durum == "belirsiz"]
    lines += [f"## Belirsiz belgeler ({len(belirsizler)}) — dokunulmadı", "",
              "<details><summary>Liste</summary>", ""]
    for b in belirsizler[:400]:
        lines.append(f"- `{b.meta_path}`")
    if len(belirsizler) > 400:
        lines.append(f"- … ve {len(belirsizler) - 400} belge daha")
    lines += ["", "</details>", ""]
    return "\n".join(lines)


def main(argv: Optional[list[str]] = None) -> int:
    ap = argparse.ArgumentParser(
        description="Damga taşıyan belgeleri işaretle (varsayılan: kuru koşu)")
    ap.add_argument("--raw-dir", default="data/raw")
    ap.add_argument("--bucket", action="append", default=None,
                    help=f"taranacak bölüm (yinelenebilir, varsayılan {LIVE_SUBDIR})")
    ap.add_argument("--uygula", action="store_true",
                    help=".meta.json dosyalarını GERÇEKTEN yaz")
    ap.add_argument("--out", default="", help="markdown rapor yolu")
    ap.add_argument("--json-out", default="")
    args = ap.parse_args(argv)

    buckets = tuple(args.bucket or [LIVE_SUBDIR])
    bulgular = tara(args.raw_dir, buckets=buckets)
    if args.uygula:
        bulgular = isaretle(bulgular, args.raw_dir)

    say = sayimlar(bulgular)
    damgali = sum(s.damgali for s in say.values())
    belirsiz = sum(s.belirsiz for s in say.values())
    yazildi = sum(1 for b in bulgular if b.yazildi)
    geri = sum(1 for b in bulgular if b.geri_alindi)
    print(f"{'UYGULANDI' if args.uygula else 'KURU KOSU'} — "
          f"{len(bulgular)} belge tarandi")
    print(f"  damgali : {damgali}")
    print(f"  belirsiz: {belirsiz}")
    print(f"  temiz   : {len(bulgular) - damgali - belirsiz}")
    if args.uygula:
        print(f"  meta yazildi   : {yazildi}")
        print(f"  isaret geri alindi: {geri}")

    report = render_report(bulgular, applied=args.uygula,
                           raw_dir=args.raw_dir, buckets=buckets)
    if args.out:
        p = Path(args.out)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(report, encoding="utf-8")
        print(f"Rapor: {p}")
    if args.json_out:
        p = Path(args.json_out)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps([b.to_json() for b in bulgular],
                                ensure_ascii=False, indent=1) + "\n",
                     encoding="utf-8")
        print(f"JSON: {p}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
