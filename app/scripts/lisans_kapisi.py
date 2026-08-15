"""Lisans kapısı — çalışma zamanı bağımlılıklarının lisanslarını denetler.

İlgili: ../Makefile (`make lisans-kapisi`), ../config/lisans_istisnalari.yaml,
../docs/LISANSLAR.md, ../docs/sbom.json, ../docs/model-license-audit.md

## Neden bu dosya var

Şartname §5.10 "açık kaynaklı gözüküp, uygulama aşamasında lisans problemi
çıkarma potansiyeli olan çözümler kullanılmamalıdır" diyor; §8 ise teslimin
Apache-2.0 ile paylaşılacağını söylüyor. `docs/model-license-audit.md` bu
denetimi **elle** yapıyordu: 15 satırlık bir tablo, insan eliyle yazılmış.
Elle tutulan tablo iki şekilde bozulur — yeni bir bağımlılık eklenir ve
tabloya yazılmaz (Ollama vakası, bkz. o belgenin *2026-08-15 eklemesi*), ya da
bir paketin lisansı sürümle birlikte değişir ve tablo eskir (trafilatura
vakası: yorumda "GPLv3+" yazıyordu, gerçek lisans Apache-2.0 çıktı).

Bu kapı tabloyu değil **kurulu ortamı** okur. İnsan hafızası yerine
`dist-info/METADATA` konuşur.

## Kapının verdiği dört hüküm

    İZİNLİ       İzin listesindeki izin verici (permissive) lisans.
    YASAK        GPL / LGPL / AGPL ailesi — copyleft. Apache-2.0 teslimle
                 birlikte dağıtımda uyumsuzluk riski taşır.
    BİLİNMİYOR   Lisans alanı boş ya da "UNKNOWN". **Sessiz geçmez** — bir
                 paketin lisansını bilmemek, izin verici olduğunu bilmekle
                 aynı şey değildir. Ayrı listede raporlanır.
    LİSTEDE-YOK  Tanınan ama izin listesinde bulunmayan lisans (ör. 0BSD).
                 Kapıyı gevşetmek yerine gerekçeli istisna istenir.

İlk üçü dışındaki her hüküm çıkış kodu **1** üretir. Kapı hiçbir şeyi kendi
başına affetmez; affetme yolu tek: `config/lisans_istisnalari.yaml` içine
**gerekçesi yazılmış** bir istisna. Gerekçesiz istisna kabul edilmez ve
istisnanın kendisi bir kusur olarak raporlanır — çünkü gerekçesiz bir muafiyet,
denetimi belgelemek değil susturmaktır.

## Bileşik lisans ifadeleri

Paketler tek lisans ilan etmek zorunda değil. `packaging` "Apache-2.0 OR
BSD-2-Clause", `tqdm` "MPL-2.0 AND MIT" der. Semantik farkı önemlidir:

    OR   — seçim bizde. Bir dal izinliyse ifade izinlidir (en iyi dal kazanır).
    AND  — hepsi birden bağlar. Bir dal yasaksa ifade yasaktır (en kötü kazanır).

`WITH` ekleri (ör. "Apache-2.0 WITH LLVM-exception") atılır: istisna eki
lisansı yalnızca **gevşetir**, sıkılaştırmaz.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

# --- hüküm ağırlıkları -------------------------------------------------------
# Bileşik ifade değerlendirmesinde kullanılır: AND en kötüyü, OR en iyiyi alır.
IZINLI = 0
LISTEDE_YOK = 1
BILINMIYOR = 2
YASAK = 3

# --- izin listesi ------------------------------------------------------------
# Hepsi izin verici (permissive): türev çalışmayı aynı lisansla yayımlama
# zorunluluğu getirmez, dolayısıyla Apache-2.0 teslimle birlikte dağıtılabilir.
# MPL-2.0 dosya-düzeyi copyleft'tir; değiştirilmemiş kütüphane olarak
# bağlandığında Apache-2.0 uygulamayla birlikte dağıtımı engellemez.
IZINLI_LISANSLAR: frozenset[str] = frozenset(
    {
        "Apache-2.0",
        "MIT",
        "BSD-2-Clause",
        "BSD-3-Clause",
        "BSD",  # kaynak yalnızca "BSD License" diyorsa (madde sayısı belirsiz)
        "PSF",
        "ISC",
        "MPL-2.0",
        "Python-2.0",
        "Unlicense",
        "CC0-1.0",
    }
)

# --- yazım varyantları → kanonik SPDX kimliği --------------------------------
# `pip-licenses` paketin ilan ettiğini olduğu gibi aktarır; kaynak da PyPI
# "classifier" metni, SPDX kimliği ya da serbest metin olabilir. Aynı lisansın
# üç ayrı yazımı üç ayrı lisans gibi görünmesin diye burada tek biçime indirilir.
ES_ADLAR: dict[str, str] = {
    # Apache
    "apache software license": "Apache-2.0",
    "apache license 2.0": "Apache-2.0",
    "apache license, version 2.0": "Apache-2.0",
    "apache 2.0": "Apache-2.0",
    "apache 2.0 license": "Apache-2.0",
    "apache-2": "Apache-2.0",
    "apache-2.0": "Apache-2.0",
    "asl 2.0": "Apache-2.0",
    # MIT
    "mit": "MIT",
    "mit license": "MIT",
    "mit-0": "MIT",
    "expat license": "MIT",
    # BSD
    "bsd": "BSD",
    "bsd license": "BSD",
    "bsd-2-clause": "BSD-2-Clause",
    "bsd 2-clause license": "BSD-2-Clause",
    "simplified bsd": "BSD-2-Clause",
    "bsd-3-clause": "BSD-3-Clause",
    "bsd 3-clause license": "BSD-3-Clause",
    "new bsd license": "BSD-3-Clause",
    "modified bsd license": "BSD-3-Clause",
    # Python Software Foundation
    "psf": "PSF",
    "psf-2.0": "PSF",
    "python software foundation license": "PSF",
    "python software foundation license (psf)": "PSF",
    "python-2.0": "Python-2.0",
    "python license (cnri python license)": "Python-2.0",
    # ISC
    "isc": "ISC",
    "isc license": "ISC",
    "isc license (iscl)": "ISC",
    # Mozilla
    "mpl-2.0": "MPL-2.0",
    "mpl 2.0": "MPL-2.0",
    "mozilla public license 2.0": "MPL-2.0",
    "mozilla public license 2.0 (mpl 2.0)": "MPL-2.0",
    # kamu malı benzeri
    "cc0-1.0": "CC0-1.0",
    "cc0 1.0 universal": "CC0-1.0",
    "the unlicense": "Unlicense",
    "unlicense": "Unlicense",
    "the unlicense (unlicense)": "Unlicense",
}

# Lisansın bilinmediğini gösteren işaretler. Boş dize de buraya girer:
# `pip-licenses` lisans meta verisi olmayan pakete "UNKNOWN" yazar.
BILINMEYEN_ISARETLERI: frozenset[str] = frozenset(
    {"", "unknown", "unknown license", "none", "n/a", "na", "-", "null", "other"}
)

# Copyleft ailesi. "LGPL" ve "AGPL" de "GPL" içerdiği için tek desen yeter;
# üçü de aynı hükmü alır. `\b` sınırları "GPL"in başka bir sözcüğün içinde
# tesadüfen yakalanmasını engeller.
GPL_DESENI = re.compile(r"\b[AL]?GPL\b|\bgeneral public license\b", re.IGNORECASE)

# Gerekçenin gerçekten yazılmış olmasını arayan asgari uzunluk. "ok", "gerekli"
# gibi tek sözcüklük dolgular gerekçe sayılmaz.
ASGARI_GEREKCE = 30


# =============================================================================
# Lisans ifadesi çözümleme
# =============================================================================
def kanonik_lisans(ham: str) -> str:
    """Tek bir lisans atomunu kanonik SPDX kimliğine indirger.

    Tanınmayan atom, kırpılmış hâliyle olduğu gibi döner — uydurma yapılmaz;
    tanımadığımız bir lisansı "herhalde MIT'tir" diye geçirmek kapının tüm
    anlamını yok eder.
    """
    s = ham.strip().strip('"').strip("'").strip()
    # PyPI "classifier" öneki: CycloneDX bunu olduğu gibi taşıyor, ör.
    # "License :: OSI Approved :: Apache Software License". Anlamlı kısım
    # yalnızca son parçadır; önek atılmazsa her classifier "tanınmayan lisans"
    # gibi görünür ve kapı gürültüye boğulur.
    if "::" in s:
        s = s.split("::")[-1].strip()
    # "Apache-2.0 WITH LLVM-exception" → "Apache-2.0": istisna eki hakları
    # yalnızca genişletir, kısıtlamaz.
    s = re.sub(r"\s+WITH\s+[\w.\-]+", "", s, flags=re.IGNORECASE).strip()
    # Sondaki sürüm süsleri ve fazladan boşluklar
    s = re.sub(r"\s+", " ", s)
    duz = s.lower()
    if duz in ES_ADLAR:
        return ES_ADLAR[duz]
    return s


def atom_hukmu(atom: str) -> int:
    """Tek bir lisans atomunun hükmünü verir."""
    duz = atom.strip().strip('"').strip("'").lower()
    if duz in BILINMEYEN_ISARETLERI:
        return BILINMIYOR
    # Yasak denetimi kanonikleştirmeden ÖNCE ham metinde yapılır: eş-ad
    # tablosunda olmayan bir GPL yazımı ("GNU Lesser General Public License
    # v2 or later") kanonikleştirmeden geçse de yakalanmalı.
    if GPL_DESENI.search(atom):
        return YASAK
    kanonik = kanonik_lisans(atom)
    if kanonik in IZINLI_LISANSLAR:
        return IZINLI
    if kanonik.strip().lower() in BILINMEYEN_ISARETLERI:
        return BILINMIYOR
    return LISTEDE_YOK


def ifade_hukmu(ifade: str) -> int:
    """Bileşik lisans ifadesini değerlendirir.

    `OR` / `;` → seçim bizde, en iyi dal kazanır (en düşük ağırlık).
    `AND` / `,` → hepsi bağlar, en kötü dal kazanır (en yüksek ağırlık).
    """
    if ifade is None:
        return BILINMIYOR
    metin = ifade.strip()
    if metin.strip().lower() in BILINMEYEN_ISARETLERI:
        return BILINMIYOR

    # AND/OR ayrımı BÜYÜK HARFE DUYARLIDIR ve bu kasıtlıdır. SPDX lisans
    # ifadeleri operatörleri büyük harfle yazmayı ZORUNLU kılar; serbest metin
    # lisans adlarındaki bağlaçlar ise küçük harflidir.
    #
    # Fark hayatidir: "GNU Lesser General Public License v2 or later" dizgesi
    # harf duyarsız bölünürse " or " bir OR operatörü sanılır, ifade
    # "…General Public License v2" | "later (LGPLv2+)" diye ikiye ayrılır ve OR
    # semantiği "en iyi dalı" seçtiği için ikinci (masum görünen) dal kazanır.
    # Yani harf duyarsız bölme, bir LGPL paketini kapıdan geçirir. Bu tam olarak
    # bu betiğin engellemek için var olduğu şeydir.
    #
    # `;` ayırıcısı `pip-licenses`in çoklu classifier biçimidir → OR semantiği.
    # Parantezler ayırıcı SAYILMAZ: "ISC License (ISCL)" gibi açıklama
    # parantezleri lisans adının parçasıdır.
    or_dallari = re.split(r"\s+OR\s+|;", metin)
    en_iyi = YASAK
    for dal in or_dallari:
        dal = dal.strip()
        if not dal:
            continue
        and_atomlari = re.split(r"\s+AND\s+", dal)
        en_kotu = IZINLI
        for atom in and_atomlari:
            atom = atom.strip()
            if not atom:
                continue
            en_kotu = max(en_kotu, atom_hukmu(atom))
        en_iyi = min(en_iyi, en_kotu)
    return en_iyi


# =============================================================================
# Girdi okuma
# =============================================================================
@dataclass
class Paket:
    """Denetlenen tek bir paket."""

    ad: str
    surum: str
    lisans: str

    @property
    def hukum(self) -> int:
        return ifade_hukmu(self.lisans)


def _cyclonedx_lisans_metni(bilesen: dict) -> str:
    """CycloneDX `licenses` dizisinden okunabilir lisans ifadesi üretir."""
    parcalar: list[str] = []
    for kayit in bilesen.get("licenses") or []:
        if not isinstance(kayit, dict):
            continue
        if "expression" in kayit:
            parcalar.append(str(kayit["expression"]))
            continue
        lis = kayit.get("license") or {}
        if not isinstance(lis, dict):
            continue
        # `id` SPDX kimliğidir ve `name`den güvenilirdir; ikisi de yoksa boş.
        deger = lis.get("id") or lis.get("name") or ""
        if deger:
            parcalar.append(str(deger))
    if not parcalar:
        return ""
    # `cyclonedx-py` AYNI lisansı çoğu kez İKİ KEZ yazar: bir kez SPDX kimliği
    # ("Apache-2.0"), bir kez PyPI classifier metni ("License :: OSI Approved ::
    # Apache Software License"). Bunları körü körüne AND ile birleştirmek
    # "Apache-2.0 AND Apache Software License" gibi sahte bir birleşim üretir ve
    # paket, tek lisanslı olduğu hâlde bileşik lisanslı görünür.
    #
    # Bu yüzden önce kanonikleştirip yineleneni atıyoruz. Geriye GERÇEKTEN
    # farklı lisanslar kalırsa AND doğru semantiktir (CycloneDX'te çoklu kayıt
    # "hepsi birden geçerli" demektir).
    benzersiz: list[str] = []
    gorulen: set[str] = set()
    for p in parcalar:
        anahtar = kanonik_lisans(p)
        if anahtar in gorulen:
            continue
        gorulen.add(anahtar)
        benzersiz.append(anahtar)
    return " AND ".join(benzersiz)


def paketleri_oku(yol: Path) -> list[Paket]:
    """`docs/sbom.json` (CycloneDX) veya `pip-licenses --format=json` okur.

    Biçim, dosya adından değil **yapısından** anlaşılır; böylece dosyayı
    yeniden adlandırmak denetimi bozmaz.
    """
    ham = json.loads(yol.read_text(encoding="utf-8"))

    # pip-licenses: üst düzey liste, ögelerde "Name"/"License"
    if isinstance(ham, list):
        paketler = []
        for x in ham:
            paketler.append(
                Paket(
                    ad=str(x.get("Name", "")),
                    surum=str(x.get("Version", "")),
                    lisans=str(x.get("License", "")),
                )
            )
        return paketler

    # CycloneDX: {"components": [...]}
    if isinstance(ham, dict) and "components" in ham:
        paketler = []
        for c in ham.get("components") or []:
            if not isinstance(c, dict):
                continue
            # Kök bileşen (uygulamanın kendisi) bir bağımlılık değildir.
            if c.get("type") == "application":
                continue
            paketler.append(
                Paket(
                    ad=str(c.get("name", "")),
                    surum=str(c.get("version", "")),
                    lisans=_cyclonedx_lisans_metni(c),
                )
            )
        return paketler

    raise ValueError(
        f"{yol}: tanınmayan biçim — CycloneDX ('components') ya da "
        "pip-licenses JSON listesi bekleniyordu."
    )


# =============================================================================
# İstisnalar
# =============================================================================
@dataclass
class Istisna:
    """Gerekçesi yazılmış tek bir muafiyet."""

    paket: str
    gerekce: str
    lisans: str | None = None


def istisnalari_yukle(yol: Path) -> tuple[dict[str, Istisna], list[str]]:
    """İstisna dosyasını okur.

    Döner: (paket_adı_küçük_harf → İstisna, hata_metinleri).

    Gerekçesiz ya da çok kısa gerekçeli kayıt **istisna sayılmaz**; hata
    listesine düşer ve kapıyı düşürür. Muafiyetin bedeli, onu yazılı olarak
    savunmaktır.
    """
    if not yol.exists():
        return {}, []

    metin = yol.read_text(encoding="utf-8")
    if yol.suffix.lower() in {".yaml", ".yml"}:
        try:
            import yaml  # type: ignore[import-untyped]
            veri = yaml.safe_load(metin) or {}
        except ImportError:
            # `pyyaml` bağımlılıksız CI işinde kurulu değildir. Kapının orada
            # koşamaması, kapıyı en çok gerektiği yerde kapatır: teslim imajı
            # tam da bağımlılıksız kümedir. Proje bu yüzden zaten bir stdlib
            # ayrıştırıcı taşıyor (`config/banks.yaml` aynı yola düşüyor).
            import sys as _sys
            _sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
            from src.scraping.config import _mini_parse
            veri = _mini_parse(metin) or {}
    else:
        veri = json.loads(metin) if metin.strip() else {}

    hatalar: list[str] = []
    istisnalar: dict[str, Istisna] = {}

    kayitlar = veri.get("istisnalar") if isinstance(veri, dict) else veri
    if kayitlar is None:
        kayitlar = []
    if not isinstance(kayitlar, list):
        return {}, [f"{yol}: 'istisnalar' bir liste olmalı."]

    for i, k in enumerate(kayitlar, 1):
        if not isinstance(k, dict):
            hatalar.append(f"{yol}: {i}. kayıt bir eşleme (mapping) değil.")
            continue
        paket = str(k.get("paket", "")).strip()
        gerekce = str(k.get("gerekce", "") or "").strip()
        if not paket:
            hatalar.append(f"{yol}: {i}. kayıtta 'paket' alanı yok.")
            continue
        if not gerekce:
            hatalar.append(
                f"{yol}: '{paket}' istisnasında GEREKÇE YOK. "
                "Gerekçesiz istisna kabul edilmez."
            )
            continue
        if len(gerekce) < ASGARI_GEREKCE:
            hatalar.append(
                f"{yol}: '{paket}' istisnasının gerekçesi çok kısa "
                f"({len(gerekce)} < {ASGARI_GEREKCE} karakter). "
                "Gerekçe, kararı savunan bir metin olmalı."
            )
            continue
        lisans = k.get("lisans")
        istisnalar[paket.lower()] = Istisna(
            paket=paket,
            gerekce=gerekce,
            lisans=str(lisans).strip() if lisans else None,
        )
    return istisnalar, hatalar


# =============================================================================
# Denetim
# =============================================================================
@dataclass
class Rapor:
    """Kapının çıktısı."""

    izinli: list[Paket] = field(default_factory=list)
    yasak: list[Paket] = field(default_factory=list)
    bilinmiyor: list[Paket] = field(default_factory=list)
    listede_yok: list[Paket] = field(default_factory=list)
    muaf: list[tuple[Paket, Istisna]] = field(default_factory=list)
    istisna_hatalari: list[str] = field(default_factory=list)
    kullanilmayan_istisnalar: list[str] = field(default_factory=list)

    @property
    def temiz_mi(self) -> bool:
        """Kapı geçiyor mu?"""
        return not (
            self.yasak
            or self.bilinmiyor
            or self.listede_yok
            or self.istisna_hatalari
        )

    @property
    def cikis_kodu(self) -> int:
        return 0 if self.temiz_mi else 1


def denetle(paketler: list[Paket], istisnalar: dict[str, Istisna]) -> Rapor:
    """Paket listesini izin listesine ve istisnalara göre değerlendirir."""
    rapor = Rapor()
    kullanilan: set[str] = set()

    for p in paketler:
        hukum = p.hukum
        if hukum == IZINLI:
            rapor.izinli.append(p)
            continue

        ist = istisnalar.get(p.ad.strip().lower())
        if ist is not None:
            # İstisnada lisans sabitlenmişse, gözlenen lisansla uyuşmalı.
            # Uyuşmuyorsa istisna ESKİMİŞTİR: paketin lisansı değişmiş ve
            # muafiyetin gerekçesi artık başka bir şeyi savunuyor olabilir.
            if ist.lisans and ist.lisans.strip().lower() != p.lisans.strip().lower():
                rapor.istisna_hatalari.append(
                    f"'{p.ad}' istisnası eskimiş: dosyada '{ist.lisans}' "
                    f"yazıyor, kurulu sürümde '{p.lisans}'. "
                    "Gerekçe yeniden değerlendirilmeli."
                )
            else:
                kullanilan.add(p.ad.strip().lower())
                rapor.muaf.append((p, ist))
                continue

        if hukum == YASAK:
            rapor.yasak.append(p)
        elif hukum == BILINMIYOR:
            rapor.bilinmiyor.append(p)
        else:
            rapor.listede_yok.append(p)

    # Karşılığı kalmayan istisnalar kapıyı düşürmez ama raporlanır: ölü bir
    # muafiyet, ileride yanlışlıkla bir şeyi affetmeye hazır bekleyen bir tuzaktır.
    for anahtar, ist in istisnalar.items():
        if anahtar not in kullanilan:
            rapor.kullanilmayan_istisnalar.append(ist.paket)

    return rapor


# =============================================================================
# Raporlama
# =============================================================================
def _satir(p: Paket) -> str:
    return f"  {p.ad}=={p.surum}  →  {p.lisans or '(boş)'}"


def rapor_yaz(rapor: Rapor, akis=sys.stdout) -> None:
    """İnsan okuru için özet basar."""

    def yaz(s: str) -> None:
        print(s, file=akis)

    toplam = (
        len(rapor.izinli)
        + len(rapor.yasak)
        + len(rapor.bilinmiyor)
        + len(rapor.listede_yok)
        + len(rapor.muaf)
    )
    yaz(f"Lisans kapısı — {toplam} paket denetlendi")
    yaz(f"  izinli      : {len(rapor.izinli)}")
    yaz(f"  gerekçeli muafiyet: {len(rapor.muaf)}")
    yaz(f"  YASAK       : {len(rapor.yasak)}")
    yaz(f"  BİLİNMİYOR  : {len(rapor.bilinmiyor)}")
    yaz(f"  LİSTEDE YOK : {len(rapor.listede_yok)}")

    if rapor.yasak:
        yaz("")
        yaz("⛔ YASAK LİSANS (copyleft — GPL/LGPL/AGPL ailesi):")
        for p in sorted(rapor.yasak, key=lambda x: x.ad.lower()):
            yaz(_satir(p))

    if rapor.bilinmiyor:
        yaz("")
        yaz("❓ ELLE DENETLENECEK (lisans bilinmiyor — sessiz geçmez):")
        for p in sorted(rapor.bilinmiyor, key=lambda x: x.ad.lower()):
            yaz(_satir(p))

    if rapor.listede_yok:
        yaz("")
        yaz("⚠️  İZİN LİSTESİNDE YOK (tanınıyor ama onaylanmadı):")
        for p in sorted(rapor.listede_yok, key=lambda x: x.ad.lower()):
            yaz(_satir(p))

    if rapor.istisna_hatalari:
        yaz("")
        yaz("⛔ İSTİSNA DOSYASI KUSURLU:")
        for h in rapor.istisna_hatalari:
            yaz(f"  {h}")

    if rapor.muaf:
        yaz("")
        yaz("✅ GEREKÇELİ MUAFİYET (kapıdan bilerek geçirildi):")
        for p, ist in sorted(rapor.muaf, key=lambda t: t[0].ad.lower()):
            yaz(f"  {p.ad}=={p.surum}  →  {p.lisans or '(boş)'}")
            # Gerekçeler uzun ve uzun olmaları İYİDİR; ama özet çıktısında tam
            # metni basmak asıl bulguları (yasak/bilinmeyen kalemleri) ekrandan
            # kaydırır. Tamamı `config/lisans_istisnalari.yaml` içinde durur.
            ozet = " ".join(ist.gerekce.split())
            if len(ozet) > 100:
                ozet = ozet[:99].rstrip() + "…"
            yaz(f"      gerekçe: {ozet}")

    if rapor.kullanilmayan_istisnalar:
        yaz("")
        yaz("ℹ️  KARŞILIĞI OLMAYAN İSTİSNA (ölü muafiyet — temizlenmeli):")
        for ad in sorted(rapor.kullanilmayan_istisnalar):
            yaz(f"  {ad}")

    yaz("")
    yaz("SONUÇ: " + ("GEÇTİ ✅" if rapor.temiz_mi else "DÜŞTÜ ⛔"))


# =============================================================================
# CLI
# =============================================================================
def main(argv: list[str] | None = None) -> int:
    kok = Path(__file__).resolve().parent.parent
    ayristirici = argparse.ArgumentParser(
        description="Bağımlılık lisanslarını izin listesine göre denetler."
    )
    ayristirici.add_argument(
        "--girdi",
        type=Path,
        default=kok / "docs" / "sbom.json",
        help="CycloneDX SBOM ya da pip-licenses JSON dosyası.",
    )
    ayristirici.add_argument(
        "--istisnalar",
        type=Path,
        default=kok / "config" / "lisans_istisnalari.yaml",
        help="Gerekçeli istisna dosyası (.yaml ya da .json).",
    )
    args = ayristirici.parse_args(argv)

    if not args.girdi.exists():
        print(
            f"HATA: girdi bulunamadı: {args.girdi}\n"
            "Önce `make sbom` (ya da `make lisanslar`) koşun.",
            file=sys.stderr,
        )
        return 2

    paketler = paketleri_oku(args.girdi)
    istisnalar, hatalar = istisnalari_yukle(args.istisnalar)
    rapor = denetle(paketler, istisnalar)
    rapor.istisna_hatalari = hatalar + rapor.istisna_hatalari
    rapor_yaz(rapor)
    return rapor.cikis_kodu


if __name__ == "__main__":
    raise SystemExit(main())
