"""Gold setini dev/test olarak böler ve TEST tarafını dondurur.

Kullanım:
    # Bölmeyi üret (anotasyon bittikten hemen sonra, BİR KEZ)
    python -m scripts.split_gold --gold data/gold/gold.v1.json

    # Test bölmesinin bozulmadığını doğrula (her ablasyon öncesi)
    python -m scripts.split_gold --verify

    # Test bölmesine erişimi kayda geçir (yalnızca nihai ölçümde)
    python -m scripts.split_gold --record-access "K2b kazanan kol - nihai olcum"

## Neden bu betik var

Kullanıcı kararı: *"Hepsini ayrı ayrı, birbirinden bağımsız ve etkilemeyecek
ortamlarda deneyelim, en iyi sonucu seçelim, sızıntı olmamalı."*

Yedi model kolu (kural-only · Qwen3-8B hibrit · Trendyol-8B hibrit · GLiNER
geri-çağırma ağı · NuExtract-8B · BERTurk fine-tune · LoRA) aynı gold set
üzerinde karşılaştırılacak. Eğer kol seçimi test verisine bakılarak yapılırsa
**seçim yanlılığı (selection bias)** oluşur: 7 koldan en iyisini test setinde
seçmek, o setteki gürültüye uyum sağlamaktır. Raporlanan sayı gerçek
genelleme performansı olmaz ve bunu jüriye savunamayız.

Tek uygulanabilir çözüm: **test bölmesini fiziksel olarak dondurmak.**

    dev  (~%40) → tüm kol seçimi, hiperparametre, kalibratör öğrenme
    TEST (~%60) → sha256'lanır, erişim kayda geçer, BİR KEZ açılır

Neden test daha büyük: bu projede test seti *eğitim* için kullanılmıyor
(kural katmanı gold'a bakılmadan yazıldı). Dev'e yalnızca kol seçimi ve
kalibratör öğrenmek için ihtiyaç var; asıl istatistiksel güç nihai sayıda
gerekiyor. Büyük test seti = dar güven aralığı.

## Katmanlı (stratified) bölme

Rastgele bölme, 250 kayıtta zor-vaka kategorilerini dengesiz dağıtır — bir
kategori tamamen tek tarafa düşerse o kategoride metrik raporlayamayız.
Bu yüzden bölme şu eksende katmanlanır (önem sırasıyla):

1. **Zor-vaka etiketleri** (`hard_tags`) — ablasyonun "hibrit NEREDE kazandı"
   sorusu bunlara dayanıyor; her iki bölmede de temsil edilmeleri şart.
2. **Nadir alanlar** (`kar_payi_orani`, `tahsis_ucreti`) — korpusta seyrek;
   tek tarafa yığılırsa o alanın metriği anlamsızlaşır.
3. Kampanya türü ve banka — katman içinde tur usulü (round-robin) dengelenir.

Bölme `seed` ile **deterministik**; aynı gold + aynı seed = aynı bölme.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# Nadir alanlar — korpus ölçümünden geliyor (849 belgede kâr payı 54, tahsis
# ücreti seyrek). preannotate.py'deki NADIR_ALANLAR ile aynı gerekçe.
NADIR_ALANLAR = ("kar_payi_orani", "tahsis_ucreti")

DEFAULT_SEED = 42
DEFAULT_TEST_RATIO = 0.60

DEV_ADI = "dev.json"
TEST_ADI = "test.json"
MANIFEST_ADI = "split-manifest.json"
ERISIM_KAYDI_ADI = "test-access-log.jsonl"


# --------------------------------------------------------------------------- #
# Yardımcılar
# --------------------------------------------------------------------------- #
def sha256_dosya(yol: Path) -> str:
    """Dosyanın SHA-256 özeti (bayt bazında, biçimden bağımsız)."""
    h = hashlib.sha256()
    with yol.open("rb") as fh:
        for blok in iter(lambda: fh.read(65536), b""):
            h.update(blok)
    return h.hexdigest()


def git_sha() -> str:
    """Mevcut commit; kanıtın tekrar-üretilebilirliği için manifest'e girer."""
    try:
        out = subprocess.run(["git", "rev-parse", "HEAD"],
                             capture_output=True, text=True, check=True)
        return out.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError, OSError):
        return "bilinmiyor"


def simdi_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# --------------------------------------------------------------------------- #
# Katman anahtarı
# --------------------------------------------------------------------------- #
def _katman_anahtari(kayit: dict[str, Any]) -> tuple[str, str]:
    """Kaydın katmanı: (zor-vaka imzası, nadir-alan kovası).

    Zor-vaka etiketleri sıralı demet olarak alınır — çok etiketli kayıtlar
    kendi katmanına düşer, böylece etiket kombinasyonları da dengelenir.
    """
    etiketler = kayit.get("hard_tags") or []
    if not etiketler and kayit.get("hard"):
        etiketler = ["legacy"]          # v0 uyumu: hard: bool
    zor = "+".join(sorted(etiketler)) if etiketler else "kolay"

    alanlar = set(kayit.get("fields") or {})
    nadir = sorted(alanlar & set(NADIR_ALANLAR))
    kova = "+".join(nadir) if nadir else "nadir-yok"

    return (zor, kova)


def _ikincil_anahtar(kayit: dict[str, Any]) -> tuple[str, str, str]:
    """Katman içi sıralama — banka ve kampanya türünü dengeler."""
    return (str(kayit.get("bank_slug") or ""),
            str(kayit.get("campaign_type") or ""),
            str(kayit.get("id") or ""))


# --------------------------------------------------------------------------- #
# Bölme
# --------------------------------------------------------------------------- #
def bol(kayitlar: list[dict[str, Any]], *,
        test_orani: float = DEFAULT_TEST_RATIO,
        seed: int = DEFAULT_SEED) -> tuple[list, list, dict[str, Any]]:
    """Katmanlı bölme. (dev, test, tanı) döner.

    Her katmanda `round(n * test_orani)` kayıt test'e gider. Yuvarlama
    kaymasını düzeltmek için en büyük katmanlardan kayıt taşınır — böylece
    global oran hedefe oturur ve hiçbir katman tamamen tek tarafa düşmez.
    """
    if not kayitlar:
        raise ValueError("gold seti boş — bölünecek kayıt yok")
    if not 0.0 < test_orani < 1.0:
        raise ValueError(f"test_orani 0-1 arasında olmalı, verilen: {test_orani}")

    rng = random.Random(seed)

    katmanlar: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for k in kayitlar:
        katmanlar[_katman_anahtari(k)].append(k)

    dev: list[dict] = []
    test: list[dict] = []
    katman_tani: list[dict[str, Any]] = []

    # Katmanları deterministik sırada işle
    for anahtar in sorted(katmanlar):
        grup = sorted(katmanlar[anahtar], key=_ikincil_anahtar)
        rng.shuffle(grup)

        n = len(grup)
        n_test = int(round(n * test_orani))
        # Tek kayıtlık katman: test'e ver (nihai ölçümün kapsamı daha önemli),
        # ama iki kayıtlıksa mutlaka böl.
        if n >= 2:
            n_test = max(1, min(n - 1, n_test))

        test.extend(grup[:n_test])
        dev.extend(grup[n_test:])
        katman_tani.append({
            "katman": {"zor_vaka": anahtar[0], "nadir_alan": anahtar[1]},
            "toplam": n, "test": n_test, "dev": n - n_test,
        })

    # Yuvarlama kayması düzeltmesi
    hedef_test = int(round(len(kayitlar) * test_orani))
    dev, test = _kaymayi_duzelt(dev, test, hedef_test, rng)

    tani = {
        "toplam": len(kayitlar),
        "dev": len(dev),
        "test": len(test),
        "test_orani_hedef": round(test_orani, 4),
        "test_orani_gercek": round(len(test) / len(kayitlar), 4),
        "katman_sayisi": len(katmanlar),
        "katmanlar": katman_tani,
        "seed": seed,
        "denge": {
            "dev": _denge_ozeti(dev),
            "test": _denge_ozeti(test),
        },
    }
    return dev, test, tani


def _kaymayi_duzelt(dev: list[dict], test: list[dict], hedef_test: int,
                    rng: random.Random) -> tuple[list, list]:
    """Yuvarlamadan doğan kaymayı en kalabalık katmanlardan taşıyarak kapatır.

    Taşıma yönü ne olursa olsun, kaynak katmanda **en az bir kayıt bırakılır**
    — aksi halde bir katmanı tamamen boşaltıp temsil garantisini bozarız.
    """
    def _grupla(kayitlar: list[dict]) -> dict[tuple, list[dict]]:
        g: dict[tuple, list[dict]] = defaultdict(list)
        for k in kayitlar:
            g[_katman_anahtari(k)].append(k)
        return g

    while len(test) != hedef_test:
        test_fazla = len(test) > hedef_test
        kaynak, hedef = (test, dev) if test_fazla else (dev, test)
        gruplar = _grupla(kaynak)
        # En kalabalık katmandan taşı; eşitlikte deterministik seç
        uygun = [(len(v), a) for a, v in gruplar.items() if len(v) >= 2]
        if not uygun:
            break                      # taşınabilecek kayıt yok, kaymayı kabul et
        uygun.sort(key=lambda t: (-t[0], t[1]))
        _, sec = uygun[0]
        aday = sorted(gruplar[sec], key=_ikincil_anahtar)
        tasinan = aday[rng.randrange(len(aday))]
        kaynak.remove(tasinan)
        hedef.append(tasinan)

    return dev, test


def _denge_ozeti(kayitlar: list[dict]) -> dict[str, Any]:
    """Bölmenin dengesini raporlar — jüriye gösterilecek kanıt."""
    zor: Counter = Counter()
    for k in kayitlar:
        for etiket in (k.get("hard_tags") or []):
            zor[etiket] += 1
    alan: Counter = Counter()
    absent: Counter = Counter()
    for k in kayitlar:
        for ad in (k.get("fields") or {}):
            alan[ad] += 1
        for ad in (k.get("absent_fields") or []):
            absent[ad] += 1
    return {
        "banka": dict(Counter(str(k.get("bank_slug") or "?")
                              for k in kayitlar).most_common()),
        "kampanya_turu": dict(Counter(str(k.get("campaign_type") or "?")
                                      for k in kayitlar).most_common()),
        "zor_vaka_etiketi": dict(zor.most_common()),
        "alan_dolu": dict(alan.most_common()),
        "alan_absent": dict(absent.most_common()),
    }


# --------------------------------------------------------------------------- #
# Yazma / doğrulama / erişim kaydı
# --------------------------------------------------------------------------- #
def _yaz_bolme(kayitlar: list[dict], yol: Path) -> str:
    """Bölmeyi yazar ve SHA-256'sını yanına koyar."""
    yol.parent.mkdir(parents=True, exist_ok=True)
    # Deterministik serileştirme — aynı içerik her zaman aynı sha256
    yol.write_text(
        json.dumps(kayitlar, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8")
    ozet = sha256_dosya(yol)
    yol.with_suffix(yol.suffix + ".sha256").write_text(
        f"{ozet}  {yol.name}\n", encoding="utf-8")
    return ozet


def dogrula(out_dir: Path) -> int:
    """Test bölmesinin sha256'sının değişmediğini kontrol eder.

    Her ablasyon koşusu öncesinde çağrılmalı. Bölme dondurulduktan sonra
    değişmişse bu ya kaza ya sızıntıdır — ikisi de ölçümü geçersiz kılar.
    """
    manifest_yolu = out_dir / MANIFEST_ADI
    if not manifest_yolu.exists():
        print(f"HATA: manifest bulunamadı: {manifest_yolu}\n"
              f"Bölme henüz üretilmemiş. Önce --gold ile koşun.", file=sys.stderr)
        return 2

    manifest = json.loads(manifest_yolu.read_text(encoding="utf-8"))
    hatali = 0
    for ad, beklenen in manifest["sha256"].items():
        yol = out_dir / ad
        if not yol.exists():
            print(f"HATA: {ad} kayıp", file=sys.stderr)
            hatali += 1
            continue
        gercek = sha256_dosya(yol)
        if gercek != beklenen:
            print(f"HATA: {ad} DEĞİŞMİŞ\n  beklenen: {beklenen}\n"
                  f"  gerçek  : {gercek}", file=sys.stderr)
            hatali += 1
        else:
            print(f"OK: {ad}  {gercek[:16]}…")

    kayit_yolu = out_dir / ERISIM_KAYDI_ADI
    n_erisim = 0
    if kayit_yolu.exists():
        n_erisim = sum(1 for satir in kayit_yolu.read_text(
            encoding="utf-8").splitlines() if satir.strip())
    print(f"\nTest bölmesine kayda geçmiş erişim: {n_erisim}")
    if n_erisim > 1:
        print("UYARI: test bölmesine birden fazla kez erişilmiş. Rapor bunu "
              "açıkça belirtmeli — tek seferlik ölçüm iddiası artık geçersiz.",
              file=sys.stderr)

    if hatali:
        print(f"\n{hatali} bölme bozulmuş.", file=sys.stderr)
        return 1
    print("Tüm bölmeler bozulmamış.")
    return 0


def erisim_kaydet(out_dir: Path, gerekce: str) -> int:
    """Test bölmesine erişimi kalıcı kayda geçirir.

    Bu, "test setine yalnızca bir kez baktık" iddiasının kanıtıdır. Kaydı
    silmek anlamsızdır — git geçmişi silmeyi de gösterir; amaç dürüstlüğü
    kolay, gizlemeyi zor kılmaktır.
    """
    if not gerekce.strip():
        print("HATA: erişim gerekçesi boş olamaz.", file=sys.stderr)
        return 2
    kayit_yolu = out_dir / ERISIM_KAYDI_ADI
    kayit_yolu.parent.mkdir(parents=True, exist_ok=True)
    girdi = {"zaman": simdi_iso(), "git_sha": git_sha(), "gerekce": gerekce.strip()}
    with kayit_yolu.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(girdi, ensure_ascii=False) + "\n")
    mevcut = sum(1 for s in kayit_yolu.read_text(encoding="utf-8").splitlines()
                 if s.strip())
    print(f"Erişim kaydedildi ({mevcut}. erişim): {gerekce.strip()}")
    if mevcut > 1:
        print("UYARI: bu, test bölmesine ilk erişim DEĞİL. Nihai raporda "
              "kaç kez bakıldığı yazılmalı.", file=sys.stderr)
    return 0


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def _gold_yukle(yol: Path) -> list[dict[str, Any]]:
    """Gold dosyasını okur. Hem liste hem {records: [...]} biçimini kabul eder."""
    veri = json.loads(yol.read_text(encoding="utf-8"))
    if isinstance(veri, dict):
        for anahtar in ("records", "kayitlar", "items", "data"):
            if anahtar in veri and isinstance(veri[anahtar], list):
                return veri[anahtar]
        raise ValueError(
            f"{yol}: sözlük biçiminde ama içinde kayıt listesi bulunamadı "
            f"(bakılan anahtarlar: records/kayitlar/items/data)")
    if not isinstance(veri, list):
        raise ValueError(f"{yol}: beklenen liste ya da sözlük, gelen {type(veri).__name__}")
    return veri


def main(argv: Optional[list[str]] = None) -> int:
    ap = argparse.ArgumentParser(
        description="Gold setini dev/test olarak böler ve TEST'i dondurur.")
    ap.add_argument("--gold", default=None,
                    help="gold dosyası (ör. data/gold/gold.v1.json)")
    ap.add_argument("--out-dir", default="data/gold/splits")
    ap.add_argument("--test-ratio", type=float, default=DEFAULT_TEST_RATIO)
    ap.add_argument("--seed", type=int, default=DEFAULT_SEED)
    ap.add_argument("--verify", action="store_true",
                    help="mevcut bölmelerin sha256'sını doğrula")
    ap.add_argument("--record-access", default=None, metavar="GEREKCE",
                    help="test bölmesine erişimi kayda geçir")
    ap.add_argument("--force", action="store_true",
                    help="mevcut bölmenin üzerine yaz (VARSAYILAN KAPALI)")
    args = ap.parse_args(argv)

    out_dir = Path(args.out_dir)

    if args.verify:
        return dogrula(out_dir)
    if args.record_access is not None:
        return erisim_kaydet(out_dir, args.record_access)
    if not args.gold:
        ap.error("--gold, --verify ya da --record-access verilmeli")

    gold_yolu = Path(args.gold)
    if not gold_yolu.exists():
        print(f"HATA: gold dosyası yok: {gold_yolu}", file=sys.stderr)
        return 2

    # Dondurulmuş bölmenin üzerine kazara yazmayı engelle — bu, sızıntının
    # en olası yolu: "bir daha bölelim" deyip test setini değiştirmek.
    manifest_yolu = out_dir / MANIFEST_ADI
    if manifest_yolu.exists() and not args.force:
        print(f"HATA: bölme zaten var: {manifest_yolu}\n"
              f"Yeniden bölmek test setini değiştirir ve önceki tüm ölçümleri\n"
              f"geçersiz kılar. Gerçekten istiyorsanız --force verin ve\n"
              f"gerekçesini commit mesajına yazın.", file=sys.stderr)
        return 3

    kayitlar = _gold_yukle(gold_yolu)
    dev, test, tani = bol(kayitlar, test_orani=args.test_ratio, seed=args.seed)

    dev_sha = _yaz_bolme(dev, out_dir / DEV_ADI)
    test_sha = _yaz_bolme(test, out_dir / TEST_ADI)

    manifest = {
        "olusturuldu": simdi_iso(),
        "git_sha": git_sha(),
        "gold_dosyasi": str(gold_yolu),
        "gold_sha256": sha256_dosya(gold_yolu),
        "seed": args.seed,
        "sha256": {DEV_ADI: dev_sha, TEST_ADI: test_sha},
        "tani": tani,
        "kural": (
            "TEST bölmesi dondurulmuştur. Tüm kol seçimi, hiperparametre "
            "ayarı ve kalibratör öğrenme YALNIZCA dev üzerinde yapılır. "
            "Test bölmesine kazanan kol seçildikten sonra BİR KEZ bakılır ve "
            "her erişim test-access-log.jsonl'e kaydedilir."
        ),
    }
    manifest_yolu.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8")

    # Erişim kaydını boş olarak oluştur — dosyanın varlığı protokolün
    # işletildiğini gösterir.
    (out_dir / ERISIM_KAYDI_ADI).touch()

    print(f"{'='*62}\nBÖLME ÜRETİLDİ\n{'='*62}")
    print(f"gold        : {gold_yolu}  ({len(kayitlar)} kayıt)")
    print(f"  sha256    : {manifest['gold_sha256'][:16]}…")
    print(f"dev         : {out_dir / DEV_ADI}  ({len(dev)} kayıt)")
    print(f"TEST (donduruldu): {out_dir / TEST_ADI}  ({len(test)} kayıt)")
    print(f"  sha256    : {test_sha}")
    print(f"seed        : {args.seed}")
    print(f"katman      : {tani['katman_sayisi']} adet\n")

    print("Zor-vaka etiketi dağılımı:")
    dev_zor = tani["denge"]["dev"]["zor_vaka_etiketi"]
    test_zor = tani["denge"]["test"]["zor_vaka_etiketi"]
    for etiket in sorted(set(dev_zor) | set(test_zor)):
        print(f"  {etiket:24} dev={dev_zor.get(etiket,0):3}  "
              f"test={test_zor.get(etiket,0):3}")

    print("\nNadir alan dağılımı:")
    for alan in NADIR_ALANLAR:
        d = tani["denge"]["dev"]["alan_dolu"].get(alan, 0)
        t = tani["denge"]["test"]["alan_dolu"].get(alan, 0)
        uyari = "  <-- DIKKAT: tek tarafta" if (d == 0 or t == 0) else ""
        print(f"  {alan:24} dev={d:3}  test={t:3}{uyari}")

    print(f"\nmanifest: {manifest_yolu}")
    print("\nBundan sonra: ablasyon YALNIZCA dev üzerinde koşar. Nihai ölçüm "
          "öncesi\n  python -m scripts.split_gold --record-access \"<gerekce>\"")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
