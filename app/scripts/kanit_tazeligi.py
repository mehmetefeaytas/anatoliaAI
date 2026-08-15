"""Yayımlanan her sayı, onu üreten kanıtla eşleşmek zorundadır.

İlgili: ../README.md ("Ölçülebilir Durum" tablosu)
        ../../README.md (kök README, "Ölçülebilir Durum")
        eval/reports/<damga>/{metrics,env}.json — ölçüm artefaktları
        scripts/link_denetimi.py — kardeş kapı (kırık link)

## Neden bu kapı var

Bu projenin tek farklılaştırıcısı **ölçüm dürüstlüğü**. O yüzden en pahalı
hata sınıfı, yayımlanan bir sayının koddan sapmasıdır: bir jüri
"README 0,302 diyor ama işaret ettiği rapor 'ölçülemedi' diyor" derse,
kaybedilen o satır değil **tüm ölçüm iddiasıdır**.

Sapma tek tek düzeltilebilir ama tekrar eder — 12 Ağustos'tan 15 Ağustos'a
kadar üç kez oldu. Ölçülmüş sapmalar (15 Ağustos):

    README          gerçek     kaynak
    2.631 test      2.777      pytest
    1.774 belge     1.782      demo.db
    bootstrap 2000  1000       eval/stats.py:DEFAULT_RESAMPLES
    F1 0,500        0,800      per_field.csv

Bu yüzden düzeltme değil **mekanizma** gerekiyor.

## İki ayrı denetim — karıştırılmamalı

1. **Değer denetimi:** belgedeki sayı = kanıttan okunan sayı.
2. **Tazelik denetimi:** kanıtın kendisi güncel girdilerden mi üretilmiş?
   Bir ölçüm raporu doğru sayıyı taşıyabilir ama başka bir gold'dan üretilmiş
   olabilir. `env.json`'daki `gold_sha256` bugünkü gold dosyasının sha'sı
   değilse o rapor **kanıt değildir**; sayı tesadüfen tutsa bile.

İkincisi olmadan birincisi kendini kandırır: bayat bir rapordan okunan bayat
bir sayı, bayat bir README ile mükemmel uyum gösterir.

## Kasıtlı kapsam sınırı

Bu kapı **ağır ölçüm koşturmaz**. `pytest --collect-only` ve SQLite sayımı
ucuzdur; ölçüm hattı ve kalibrasyon değildir. Onlar için artefakt okunur.
Yani kapı "sayı doğru mu"yu değil, **"sayı elimizdeki kanıtla tutarlı mı"yı**
ölçer. Kanıtın kendisini tazelemek ayrı bir iştir.

## Kullanım

    python -m scripts.kanit_tazeligi              # tüm iddialar
    python -m scripts.kanit_tazeligi --liste      # ne denetleniyor
    python -m scripts.kanit_tazeligi --iddia test_sayisi
    python -m scripts.kanit_tazeligi --json       # makine okur çıktı

Çıkış kodu: 0 = sapma yok · 1 = sapma var · 2 = kanıt eksik/bayat.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sqlite3
import subprocess
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

KOK = Path(__file__).resolve().parents[1]          # app/
DEPO = KOK.parent                                   # depo kökü

CIKIS_TEMIZ = 0
CIKIS_SAPMA = 1
CIKIS_KANIT_YOK = 2


# ─────────────────────────── TR sayı biçimi ────────────────────────────

def tr_sayi(metin: str) -> float:
    """`2.631` -> 2631.0 · `0,452` -> 0.452 · `%3,9` -> 3.9

    Türkçe gösterimde nokta binlik, virgül ondalık ayırıcıdır. Bu ikisini
    karıştırmak `0.452`yi 452 yapar; sessiz ve ölümcül.
    """
    s = metin.strip().replace("%", "").replace(" ", "")
    if "," in s:
        s = s.replace(".", "").replace(",", ".")
    elif s.count(".") == 1:
        tam, kesir = s.split(".")
        # `1.782` tek gruplu binlik; `0.452` DEĞİL (tam kısmı "0").
        if len(kesir) == 3 and tam not in {"", "0"} and len(tam) <= 3:
            s = tam + kesir
    return float(s)


def yaz_tr(deger: float) -> str:
    """Karşılaştırma raporunda okunur gösterim."""
    if float(deger).is_integer():
        return f"{int(deger):,}".replace(",", ".")
    return f"{deger:.3f}".replace(".", ",")


# ────────────────────────────── ölçerler ───────────────────────────────
#
# Her ölçer ya bir sayı döndürür ya `KanitYok` fırlatır. Sessizce `None`
# dönmek yasak: ölçemediğimiz bir şeyi "uyumlu" saymak, kapının varlık
# sebebini ortadan kaldırır.


class KanitYok(RuntimeError):
    """Ölçüm yapılamadı — kapı bunu SAPMA değil, KANIT EKSİK sayar."""


def sha256_dosya(yol: Path) -> str:
    h = hashlib.sha256()
    with yol.open("rb") as fh:
        for blok in iter(lambda: fh.read(1 << 20), b""):
            h.update(blok)
    return h.hexdigest()


TEST_OZETI = KOK / "eval" / "reports" / "test-ozeti.json"


# Test sonucunu değiştirebilecek yollar. Bir belge ya da rapor değiştiğinde
# testlerin sonucu değişmez; kaynak ya da test değiştiğinde değişebilir.
TEST_ETKILEYEN = ("app/src", "app/scripts", "app/tests", "app/eval",
                  "app/config", "app/requirements.txt",
                  "app/requirements-api.txt", "app/pyproject.toml")

# Ölçüm çıktısı `app/eval/reports/` altında yaşıyor ve `app/eval` önekine
# giriyor. Dışlanmazsa artefaktı commit'lemek onu KENDİ kuralıyla bayat
# yapardı — kaydedilen sha ile HEAD arasında "app/eval altında bir dosya
# değişti" görünür, oysa değişen şey artefaktın kendisidir.
TEST_ETKILEMEYEN = (":(exclude)app/eval/reports",)


def _yol_suzgeci() -> tuple[str, ...]:
    return (*TEST_ETKILEYEN, *TEST_ETKILEMEYEN)


def _test_ozeti() -> dict[str, Any]:
    """`scripts/test_ozeti.py` artefaktı — üretildiğinden beri kaynak değişmediyse.

    Tazelik ölçütü `git_sha == HEAD` OLAMAZ: artefaktı commit'lemek HEAD'i
    değiştirir ve artefakt daha doğduğu anda bayatlar. Anlamlı soru şudur:
    **artefaktın üretildiği commit ile bugün arasında test sonucunu
    değiştirebilecek bir şey değişti mi?** Belge değişikliği testleri
    etkilemez; kaynak, test, bağımlılık değişikliği etkiler.
    """
    if not TEST_OZETI.exists():
        raise KanitYok(
            f"{TEST_OZETI.relative_to(DEPO)} yok — "
            f"`python -m scripts.test_ozeti` koşulmalı")
    ozet = json.loads(TEST_OZETI.read_text(encoding="utf-8"))
    if ozet.get("git_dirty"):
        raise KanitYok("test özeti kirli ağaçta üretilmiş — tekrar üretilemez")

    sha = str(ozet.get("git_sha") or "")
    if not sha:
        raise KanitYok("test özetinde git_sha yok")
    try:
        fark = subprocess.run(
            ["git", "-C", str(DEPO), "diff", "--name-only", sha, "HEAD",
             "--", *_yol_suzgeci()],
            capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.SubprocessError) as exc:
        raise KanitYok(f"git diff koşulamadı: {exc}") from exc
    if fark.returncode != 0:
        raise KanitYok(
            f"test özetinin commit'i ({sha[:12]}…) bu geçmişte bulunamadı")
    degisen = [s for s in fark.stdout.splitlines() if s.strip()]
    if degisen:
        raise KanitYok(
            f"test özeti {sha[:12]}… commit'inde üretildi; o gün bugüne "
            f"{len(degisen)} kaynak/test dosyası değişti (ör. {degisen[0]}) — "
            f"`python -m scripts.test_ozeti` yeniden koşulmalı")

    # Ağaçta commit'lenmemiş kaynak değişikliği varsa artefakt yine bayattır.
    try:
        kirli = subprocess.run(
            ["git", "-C", str(DEPO), "status", "--porcelain",
             "--untracked-files=all", "--", *_yol_suzgeci()],
            capture_output=True, text=True, timeout=60).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        kirli = ""
    if kirli:
        raise KanitYok(
            "çalışma ağacında commit'lenmemiş kaynak/test değişikliği var — "
            "test özeti onu kapsamıyor")
    return ozet


def olc_test_gecti() -> float:
    """Tam koşuda GEÇEN test sayısı. 'Yeşil' iddiasının tek kanıtı."""
    return float(_test_ozeti()["gecti"])


def olc_test_atlandi() -> float:
    return float(_test_ozeti()["atlandi"])


def olc_test_toplanan() -> float:
    """Toplanan test sayısı — artefakt tazeyse ordan, değilse ucuz sayım.

    `--collect-only` ağ ve Postgres istemez; bu yüzden kapı artefakt olmadan
    da bir şey söyleyebilir. Ama 'yeşil' iddiasını KARŞILAYAMAZ.
    """
    try:
        return float(_test_ozeti()["toplanan"])
    except KanitYok:
        pass
    try:
        cikti = subprocess.run(
            [sys.executable, "-m", "pytest", "tests/", "--collect-only", "-q"],
            cwd=KOK, capture_output=True, text=True, timeout=900).stdout
    except (OSError, subprocess.SubprocessError) as exc:
        raise KanitYok(f"pytest koşulamadı: {exc}") from exc
    m = re.search(r"(\d+)\s+tests?\s+collected", cikti)
    if not m:
        raise KanitYok("pytest çıktısında 'tests collected' bulunamadı")
    return float(m.group(1))


def olc_korpus_belge() -> float:
    """`data/demo.db` içindeki kampanya sayısı — korpusun tek doğruluk kaynağı."""
    db = KOK / "data" / "demo.db"
    if not db.exists():
        raise KanitYok(f"{db} yok — `python -m scripts.build_demo_db` gerekiyor")
    with sqlite3.connect(f"file:{db}?mode=ro", uri=True) as baglanti:
        return float(baglanti.execute("SELECT COUNT(*) FROM campaigns").fetchone()[0])


def olc_gold_kayit(dosya: str) -> Callable[[], float]:
    def _olc() -> float:
        yol = KOK / "data" / "gold" / dosya
        if not yol.exists():
            raise KanitYok(f"{yol} yok")
        return float(len(json.loads(yol.read_text(encoding="utf-8"))))
    return _olc


def olc_banka_sayisi() -> float:
    """`config/banks.yaml` — config-driven banka onboarding (§18/3) sayısı."""
    yol = KOK / "config" / "banks.yaml"
    if not yol.exists():
        raise KanitYok(f"{yol} yok")
    girdiler = re.findall(r"^\s*-\s*slug:\s*([a-z0-9-]+)\s*$",
                          yol.read_text(encoding="utf-8"), re.MULTILINE)
    if not girdiler:
        raise KanitYok("banks.yaml'de `- slug:` girdisi bulunamadı")
    # TKBB şemsiye kuruluştur, katılım bankası DEĞİLDİR — README de ikisini
    # ayrı sayıyor ("10 katılım bankası + TKBB"). Burada da ayrılır.
    return float(len([g for g in girdiler if g != "tkbb"]))


def olc_bootstrap_ornek() -> float:
    """`eval/stats.py` varsayılanı — GA'nın kaç yeniden örnekle üretildiği."""
    yol = KOK / "eval" / "stats.py"
    if not yol.exists():
        raise KanitYok(f"{yol} yok")
    m = re.search(r"^DEFAULT_RESAMPLES\s*=\s*(\d+)",
                  yol.read_text(encoding="utf-8"), re.MULTILINE)
    if not m:
        raise KanitYok("eval/stats.py içinde DEFAULT_RESAMPLES bulunamadı")
    return float(m.group(1))


# ───────────────────── ölçüm artefaktı: değer + tazelik ────────────────


@dataclass(frozen=True)
class OlcumRaporu:
    dizin: Path
    env: dict[str, Any]
    metrics: dict[str, Any]


def rapor_dizinleri() -> list[OlcumRaporu]:
    kok = KOK / "eval" / "reports"
    if not kok.is_dir():
        return []
    out: list[OlcumRaporu] = []
    for d in sorted(kok.iterdir(), reverse=True):
        env_y, met_y = d / "env.json", d / "metrics.json"
        if not (env_y.exists() and met_y.exists()):
            continue
        try:
            out.append(OlcumRaporu(
                d,
                json.loads(env_y.read_text(encoding="utf-8")),
                json.loads(met_y.read_text(encoding="utf-8"))))
        except json.JSONDecodeError:
            continue
    return out


def _matcher_var(rapor: OlcumRaporu, matcher: str | None) -> bool:
    """Ablasyon raporlarının şeması farklıdır (`arms`, `comparisons`).

    Aynı gold'dan üretilmiş olmaları onları tek-kol metriği için kanıt yapmaz;
    sessizce elenirlerse "kanıt yok" yerine yanlış bir sayı okunur.
    """
    if matcher is None:
        return True
    sonuclar = rapor.metrics.get("results")
    return isinstance(sonuclar, list) and any(
        isinstance(r, dict) and r.get("matcher") == matcher for r in sonuclar)


def taze_rapor(gold_dosya: str, matcher: str | None = None) -> OlcumRaporu:
    """Bugünkü gold'dan üretilmiş EN YENİ raporu bul.

    `gold_sha256` eşleşmesi bu fonksiyonun tüm meselesi: doğru sayıyı taşıyan
    ama başka bir gold'dan üretilmiş bir rapor kanıt değildir.
    """
    gold_yol = KOK / "data" / "gold" / gold_dosya
    if not gold_yol.exists():
        raise KanitYok(f"{gold_yol} yok")
    sha = sha256_dosya(gold_yol)
    adaylar = [r for r in rapor_dizinleri()
               if r.env.get("gold_sha256") == sha and _matcher_var(r, matcher)]
    if not adaylar:
        raise KanitYok(
            f"{gold_dosya} (sha {sha[:12]}…) için ölçüm raporu yok — "
            f"`python -m eval.run_eval --gold data/gold/{gold_dosya}` koşulmalı")
    taze = max(adaylar, key=lambda r: r.env.get("created_utc", ""))
    if taze.env.get("git_dirty"):
        raise KanitYok(
            f"{taze.dizin.name}: `git_dirty=true` — kirli ağaçta üretilmiş rapor "
            f"kanıt değildir, tekrar üretilemez")
    return taze


def kesit(rapor: OlcumRaporu, matcher: str) -> dict[str, Any]:
    for r in rapor.metrics.get("results", []):
        if r.get("matcher") == matcher:
            return r
    raise KanitYok(f"{rapor.dizin.name}: `{matcher}` eşleştiricisi raporda yok")


def olc_metrik(gold_dosya: str, anahtar: str, matcher: str = "strict"
               ) -> Callable[[], float]:
    """Ölçüm artefaktından tek bir metrik oku.

    `anahtar`: mikro_f1 · makro_f1 · halusinasyon · yapisal_mikro_f1 ·
    kalem_mikro_f1 · yapisal_halusinasyon

    ⚠️ `yapisal` ile `kalem` AYNI ŞEY DEĞİLDİR ve karıştırmak yayımlanan
    sayıyı sessizce yanlış denetler:
      * **yapısal** = 11 alan (`kampanya_kosullari` HARİÇ), ikili ölçüt
      * **kalem**   = 12 alan, liste alanlarında kalem başına sayım
    """
    def _olc() -> float:
        rapor = taze_rapor(gold_dosya, matcher)
        r = kesit(rapor, matcher)
        mikro = r.get("micro") or {}
        if anahtar == "mikro_f1":
            return float(mikro["f1"])
        if anahtar == "makro_f1":
            return float(r["macro_f1"])
        if anahtar == "kalem_mikro_f1":
            return float(r["micro_f1_kalem"])
        if anahtar in {"yapisal_mikro_f1", "yapisal_halusinasyon"}:
            if "micro_f1_yapisal" not in r:
                raise KanitYok(
                    f"{rapor.dizin.name}: yapılandırılmış kesit artefaktta yok "
                    f"— rapor `micro_f1_yapisal` eklendikten önce üretilmiş")
            if anahtar == "yapisal_mikro_f1":
                return float(r["micro_f1_yapisal"])
            y = r["yapisal"]
            payda = float(y["fp_hallucinated"]) + float(y["tn"])
            if payda == 0:
                raise KanitYok("yapısal kesitte `absent` kararı yok — oran TANIMSIZ")
            return float(y["fp_hallucinated"]) / payda
        if anahtar == "halusinasyon":
            uyd = float(mikro["fp_hallucinated"])
            payda = uyd + float(mikro["tn"])
            if payda == 0:
                raise KanitYok(
                    f"{gold_dosya}: gold'da `absent` kararı yok, halüsinasyon "
                    f"oranı TANIMSIZ — 0,0 yazmak yalan olurdu")
            return uyd / payda
        raise KanitYok(f"bilinmeyen metrik anahtarı: {anahtar}")
    return _olc


# ─────────────────────────────── iddialar ──────────────────────────────


@dataclass(frozen=True)
class Iddia:
    """Bir belgede yayımlanmış tek bir sayı ve onu üreten ölçüm."""

    ad: str
    aciklama: str
    desenler: tuple[tuple[str, str], ...]      # (dosya, regex — tek yakalama grubu)
    olcer: Callable[[], float]
    tolerans: float = 0.0005

    def belgedeki(self) -> list[tuple[str, int, str]]:
        """(dosya, satır, ham metin) — belgede geçen tüm yayımlanmış değerler."""
        bulunan: list[tuple[str, int, str]] = []
        for goreli, desen in self.desenler:
            yol = DEPO / goreli
            if not yol.exists():
                continue
            re_ = re.compile(desen)
            for i, satir in enumerate(yol.read_text(encoding="utf-8").splitlines(), 1):
                for m in re_.finditer(satir):
                    bulunan.append((goreli, i, m.group(1)))
        return bulunan


@dataclass
class Sonuc:
    iddia: str
    durum: str                                  # tamam · sapma · kanit_yok
    olculen: float | None = None
    sapmalar: list[dict[str, Any]] = field(default_factory=list)
    gerekce: str = ""


def iddialar() -> list[Iddia]:
    """Denetlenen sayıların tek doğruluk kaynağı.

    Yeni bir sayı yayımlıyorsan buraya bir satır ekle. Eklemezsen kapı onu
    korumaz — ve korunmayan sayı, ölçülmüş olarak, bayatlar.
    """
    return [
        Iddia(
            ad="test_gecti",
            aciklama="Tam koşuda geçen test sayısı ('yeşil' iddiası)",
            desenler=(
                ("README.md", r"testler-([\d.]+)%20"),
                ("app/README.md", r"testler-([\d.]+)%20"),
                ("app/README.md", r"\*\*([\d.]+) test yeşil\*\*"),
                ("README.md", r"([\d.]+) geçti"),
            ),
            olcer=olc_test_gecti,
            tolerans=0.5,
        ),
        Iddia(
            ad="test_toplanan",
            aciklama="Toplanan test sayısı",
            desenler=(
                ("app/README.md", r"\*\*([\d.]+)\*\* birim/entegrasyon"),
                ("README.md", r"\*\*([\d.]+)\*\* toplanan"),
            ),
            olcer=olc_test_toplanan,
            tolerans=0.5,
        ),
        Iddia(
            ad="test_atlandi",
            aciklama="Atlanan test sayısı (Postgres vb.)",
            desenler=(
                ("app/README.md", r"koşuda ([\d.]+)'i atlanır"),
                ("README.md", r"([\d.]+) atlandı"),
            ),
            olcer=olc_test_atlandi,
            tolerans=0.5,
        ),
        Iddia(
            ad="korpus_belge",
            aciklama="Korpustaki kampanya belgesi sayısı",
            desenler=(
                ("README.md", r"denetimi-([\d.]+)%20belge"),
                ("app/README.md", r"denetimi-([\d.]+)%20belge"),
                ("README.md", r"\*\*([\d.]+) belge\*\* \(ham arşivle eşit\)"),
                ("app/README.md", r"70/([\d.]+) belgede"),
                ("README.md", r"70/([\d.]+) belgede"),
            ),
            olcer=olc_korpus_belge,
            tolerans=0.5,
        ),
        Iddia(
            ad="gold_v2_kayit",
            aciklama="gold.v2 kayıt sayısı",
            desenler=(
                ("README.md", r"gold seti: `gold\.v2\.json` \((\d+) kayıt\)"),
                ("app/README.md", r"`gold\.v2`\s*\|\s*(\d+)\s*\|"),
            ),
            olcer=olc_gold_kayit("gold.v2.json"),
            tolerans=0.5,
        ),
        Iddia(
            ad="gold_round1_kayit",
            aciklama="gold.round1 kayıt sayısı",
            desenler=(
                ("README.md", r"`gold\.round1`[^|]*\|\s*(\d+)\s*\|"),
                ("app/README.md", r"`gold\.round1`[^|]*\|\s*(\d+)\s*\|"),
            ),
            olcer=olc_gold_kayit("gold.round1.json"),
            tolerans=0.5,
        ),
        Iddia(
            ad="bootstrap_ornek",
            aciklama="Bootstrap yeniden örnekleme sayısı",
            desenler=(
                ("README.md", r"bootstrap (\d+) örnek"),
                ("app/README.md", r"bootstrap (\d+) örnek"),
            ),
            olcer=olc_bootstrap_ornek,
            tolerans=0.5,
        ),
        Iddia(
            ad="banka_sayisi",
            aciklama="config-driven banka sayısı",
            desenler=(
                ("README.md", r"\*\*(\d+) katılım bankası\*\*"),
                ("app/README.md", r"\*\*(\d+) katılım bankası\*\*"),
            ),
            olcer=olc_banka_sayisi,
            tolerans=0.5,
        ),
        Iddia(
            ad="v2_mikro_f1",
            aciklama="gold.v2 · strict · 12-alan mikro-F1",
            desenler=(("README.md", r"12-alan mikro-F1 \| ([\d,]+)"),),
            olcer=olc_metrik("gold.v2.json", "mikro_f1"),
        ),
        Iddia(
            ad="v2_halusinasyon",
            aciklama="gold.v2 · strict · halüsinasyon oranı",
            desenler=(("README.md", r"Halüsinasyon oranı \| \*\*([\d,]+)\*\*"),),
            olcer=olc_metrik("gold.v2.json", "halusinasyon"),
        ),
    ]


# ──────────────────────────────── denetim ──────────────────────────────


def denetle(secili: set[str] | None = None) -> list[Sonuc]:
    sonuclar: list[Sonuc] = []
    for iddia in iddialar():
        if secili and iddia.ad not in secili:
            continue
        yayimlanan = iddia.belgedeki()
        if not yayimlanan:
            sonuclar.append(Sonuc(iddia.ad, "tamam", gerekce="belgede geçmiyor"))
            continue
        try:
            olculen = iddia.olcer()
        except KanitYok as exc:
            sonuclar.append(Sonuc(iddia.ad, "kanit_yok", gerekce=str(exc)))
            continue
        sapmalar = []
        for dosya, satir, ham in yayimlanan:
            try:
                deger = tr_sayi(ham)
            except ValueError:
                sapmalar.append({"dosya": dosya, "satir": satir, "yazan": ham,
                                 "not": "sayıya çevrilemedi"})
                continue
            if abs(deger - olculen) > iddia.tolerans:
                sapmalar.append({"dosya": dosya, "satir": satir, "yazan": ham})
        sonuclar.append(Sonuc(iddia.ad, "sapma" if sapmalar else "tamam",
                              olculen, sapmalar))
    return sonuclar


def render(sonuclar: list[Sonuc]) -> str:
    sat: list[str] = []
    sapan = [s for s in sonuclar if s.durum == "sapma"]
    eksik = [s for s in sonuclar if s.durum == "kanit_yok"]

    for s in sonuclar:
        if s.durum == "tamam":
            deger = yaz_tr(s.olculen) if s.olculen is not None else s.gerekce
            sat.append(f"  ✅ {s.iddia:22s} {deger}")
    for s in eksik:
        sat.append(f"  ⚠️  {s.iddia:22s} KANIT YOK — {s.gerekce}")
    for s in sapan:
        sat.append(f"  ❌ {s.iddia:22s} ölçülen {yaz_tr(s.olculen or 0)}")
        for d in s.sapmalar:
            ek = f"  ({d['not']})" if "not" in d else ""
            sat.append(f"       {d['dosya']}:{d['satir']} yazıyor: {d['yazan']}{ek}")

    sat.append("")
    sat.append(f"  {len(sonuclar)} iddia · {len(sapan)} sapma · {len(eksik)} kanıt eksik")
    if sapan:
        sat.append("")
        sat.append("  Yayımlanan sayı ile kanıt ayrıştı. Ya belgeyi düzelt ya")
        sat.append("  ölçümü yeniden koş — sapmayı bırakmak üçüncü seçenek değil.")
    return "\n".join(sat)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Kanıt-tazeliği kapısı")
    p.add_argument("--iddia", action="append", help="yalnız bu iddiayı denetle")
    p.add_argument("--liste", action="store_true", help="denetlenen iddiaları yaz")
    p.add_argument("--json", action="store_true", help="makine okur çıktı")
    p.add_argument("--kanit-eksigi-uyari", action="store_true",
                   help=("kanıt üretilemeyen iddiayı UYARI say (çıkış 0). "
                         "CI için: her commit'te tam ölçüm artefaktı "
                         "beklenemez. Teslim öncesi kapı bu bayrağı KULLANMAZ."))
    a = p.parse_args(argv)

    if a.liste:
        for i in iddialar():
            print(f"{i.ad:22s} {i.aciklama}")
        return CIKIS_TEMIZ

    sonuclar = denetle(set(a.iddia) if a.iddia else None)

    if a.json:
        print(json.dumps([{"iddia": s.iddia, "durum": s.durum,
                           "olculen": s.olculen, "sapmalar": s.sapmalar,
                           "gerekce": s.gerekce} for s in sonuclar],
                         ensure_ascii=False, indent=2))
    else:
        print("Kanıt-tazeliği denetimi\n")
        print(render(sonuclar))

    # Sapma HER ZAMAN kapıyı düşürür: belge ile kanıt ayrışmışsa bu, ölçüm
    # eksikliği değil YANLIŞ BEYANDIR ve gevşetilmez.
    if any(s.durum == "sapma" for s in sonuclar):
        return CIKIS_SAPMA
    if any(s.durum == "kanit_yok" for s in sonuclar):
        return CIKIS_TEMIZ if a.kanit_eksigi_uyari else CIKIS_KANIT_YOK
    return CIKIS_TEMIZ


if __name__ == "__main__":
    raise SystemExit(main())
