"""Lisans envanteri üretici — `pip-licenses` çıktısını okunur belgeye çevirir.

İlgili: ../Makefile (`make lisanslar`), lisans_kapisi.py, ../docs/LISANSLAR.md

## Neden bir sarmalayıcı (wrapper) var

`pip-licenses --format=markdown` zaten markdown üretiyor. Ama ürettiği şey
**künyesiz** bir tablo: ne zaman, hangi komutla, hangi ortamdan çıktığı yazmıyor.
Künyesiz bir envanter, altı ay sonra bakan biri için doğrulanamaz bir iddiadır —
"bu liste hangi ortamın listesi?" sorusunun cevabı yoksa liste kanıt değildir.

Bu betik tabloyu üretir ve başına şunları koyar: üretim tarihi, üreten komut,
yorumlayıcı sürümü, kapsam ve **sınır uyarısı**. Sınır uyarısı özellikle önemli:
projede Python kilit dosyası (lock file) yok, `requirements.txt` `>=` pinleri
taşıyor. Yani bu envanter bir sözleşme değil, bir **kesit**tir.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

# Kapı ile aynı sınıflandırmayı kullan ki belge ile kapı çelişmesin. İki ayrı
# lisans yorumu tutmak, ikisinin sessizce ayrışmasına davetiyedir.
from scripts.lisans_kapisi import (
    BILINMIYOR,
    IZINLI,
    LISTEDE_YOK,
    YASAK,
    Paket,
    ifade_hukmu,
    istisnalari_yukle,
)

KOK = Path(__file__).resolve().parent.parent

HUKUM_ROZETI: dict[int, str] = {
    IZINLI: "✅ izinli",
    LISTEDE_YOK: "⚠️ listede yok",
    BILINMIYOR: "❓ bilinmiyor",
    YASAK: "⛔ yasak",
}


def pip_licenses_calistir(py: Path) -> list[dict]:
    """Kurulu ortamı `pip-licenses` ile tarar ve JSON döner."""
    sonuc = subprocess.run(
        [
            str(py),
            "-m",
            "piplicenses",
            "--format=json",
            "--with-urls",
            "--with-authors",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(sonuc.stdout)


def _kacis(s: str) -> str:
    """Markdown tablo hücresi için `|` kaçışı."""
    return (s or "").replace("|", "\\|").strip()


def _risk_bolumu(paketler: list[Paket]) -> list[str]:
    """Elle doğrulanmış risk kalemlerini yazar.

    Bu bölüm ARAÇ ÇIKTISI DEĞİLDİR; iki aracın da yanlış ya da eksik cevap
    verdiği yerlerde paketin kendi dosyaları elle okunarak üretilmiştir.
    Metin burada, belgede değil, çünkü `make lisanslar` belgeyi baştan yazar —
    belgeye elle eklenen her satır bir sonraki koşumda silinirdi.
    """
    kurulu = {p.ad.lower() for p in paketler}
    L: list[str] = []
    L.append("## ⚠️ Risk kalemleri — çözülen ve çözülmeyen")
    L.append("")

    # --- trafilatura ---------------------------------------------------
    L.append("### ✅ ÇÖZÜLDÜ — `trafilatura` gerçekte Apache-2.0")
    L.append("")
    L.append(
        "**İddia:** `requirements.txt` bu paketi yorumunda **GPLv3+** olarak "
        "işaretliyor ve bu yüzden opsiyonel bırakılmış, teslim imajına "
        "alınmamıştı. `docs/model-license-audit.md` §2 kalemi 31 Tem 2026'dan "
        "beri `⏳ AÇIK RİSK` olarak duruyordu."
    )
    L.append("")
    L.append("**Bulgu: iddia yanlış. Paketin gerçek lisansı Apache-2.0.**")
    L.append("")
    L.append(
        "Doğrulama, paketin kendi dosyaları okunarak yapıldı "
        "(`pip download --no-deps --no-binary :all:` ile kaynak dağıtımı "
        "indirildi, `PKG-INFO` ve `LICENSE` açıldı):"
    )
    L.append("")
    L.append("| Sürüm | `PKG-INFO` lisans alanı | `LICENSE` dosyasının gövdesi |")
    L.append("|---|---|---|")
    L.append(
        "| `trafilatura 2.2.0` | `License-Expression: Apache-2.0` "
        "| Apache License 2.0 tam metni; içinde **sıfır** `GNU`/`GPL` geçişi |"
    )
    L.append(
        "| `trafilatura 1.8.0` | `License: Apache-2.0` + "
        "`Classifier: License :: OSI Approved :: Apache Software License` "
        "| aynı |"
    )
    L.append("")
    L.append(
        "İki uç da sınandı çünkü `requirements.txt` pini `>=1.8` bir **aralık** "
        "açıyor ve lisans sürümle değişebilir. Aralığın alt sınırı (1.8.0) ve "
        "bugünkü üst ucu (2.2.0) Apache-2.0 çıktı; yani pinin GPL bir sürüme "
        "denk gelme riski bu iki ölçüm arasında gözlenmedi."
    )
    L.append("")
    if "trafilatura" not in kurulu:
        L.append(
            "> **Kapsam notu:** `trafilatura` bu `.venv`de **kurulu değildir**, "
            "bu yüzden yukarıdaki envanter tablosunda görünmez. Lisansı kurulu "
            "ortamdan değil, PyPI'dan indirilen kaynak dağıtımından okunmuştur. "
            "Paket kurulursa kapı onu kendiliğinden `Apache-2.0 → ✅ izinli` "
            "olarak sınıflandırır; istisna gerekmez."
        )
        L.append("")
    L.append(
        "**Sonuç:** GPLv3+ gerekçesiyle konmuş kısıt dayanaksız kalmıştır. "
        "Paketi teslim imajına almak lisans açısından serbesttir — bu, lisans "
        "kararı değil artık bir mimari karardır (kod `strip_html` yedeğiyle "
        "onsuz da çalışıyor). `requirements.txt` içindeki `# GPLv3+` yorumu "
        "**yanlıştır ve düzeltilmelidir.**"
    )
    L.append("")

    # --- transformers ----------------------------------------------------
    L.append("### ✅ ÇÖZÜLDÜ — `transformers` SBOM'da lisanssız görünüyor")
    L.append("")
    L.append(
        "`docs/sbom.json` içinde `transformers` bileşeninin lisans alanı "
        "**boştur**. Bu, paketin lisansı olmadığı anlamına gelmez; "
        "`cyclonedx-py`nin okuyamadığı anlamına gelir. Paket lisansını PEP 639 "
        "`License-Expression` alanıyla ya da `Classifier:` satırıyla değil, "
        "eski serbest metin `License:` alanıyla bildiriyor."
    )
    L.append("")
    L.append(
        "Elle doğrulandı — `transformers-*.dist-info/METADATA` içinde "
        "`License: Apache 2.0 License` yazıyor ve dizinde `licenses/LICENSE` "
        "(Apache-2.0 metni) duruyor. `pip-licenses` aynı paketi doğru okuyor; "
        "iki aracın çelişmesi kaydın sebebidir."
    )
    L.append("")
    L.append(
        "Bu kalem, kapının **\"UNKNOWN sessiz geçmez\"** kuralının neden "
        "gerektiğinin kanıtıdır: lisansı boş bırakılan bir paket, sessizce "
        "geçirilseydi denetim onu hiç görmeyecekti."
    )
    L.append("")
    return L


def _kapsam_farki_bolumu() -> list[str]:
    """İki aracın farklı paket sayısı vermesinin açıklaması."""
    L: list[str] = []
    L.append("## İki aracın paket sayısı neden farklı")
    L.append("")
    L.append(
        "`docs/sbom.json` (CycloneDX) bu belgeden **daha fazla** paket listeler. "
        "Fark bir tutarsızlık değil, kapsam farkıdır: `pip-licenses` varsayılan "
        "olarak **kendini ve kendi bağımlılıklarını** (`pip-licenses`, "
        "`prettytable`, `wcwidth`) ve ortam altyapısını (`pip`, `setuptools`) "
        "envanterden düşürür; `cyclonedx-py environment` ise ortamda ne varsa "
        "onu yazar."
    )
    L.append("")
    L.append(
        "Yani SBOM, bu belgenin **üst kümesidir**. Lisans kapısı bilerek "
        "SBOM'u okur: denetimin kör noktası olmaması, aracın kendi "
        "bağımlılıklarının da sayılmasını gerektirir."
    )
    L.append("")
    return L


def belge_uret(kayitlar: list[dict], py: Path, istisnalar: dict) -> str:
    """Künyeli markdown envanterini üretir."""
    paketler = [
        Paket(
            ad=str(k.get("Name", "")),
            surum=str(k.get("Version", "")),
            lisans=str(k.get("License", "")),
        )
        for k in kayitlar
    ]
    url_ile = {str(k.get("Name", "")): str(k.get("URL", "")) for k in kayitlar}

    tarih = datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M %Z")
    yorumlayici = subprocess.run(
        [str(py), "--version"], capture_output=True, text=True, check=True
    ).stdout.strip()

    sayac: Counter[int] = Counter(p.hukum for p in paketler)
    muaf_adlar = set(istisnalar.keys())

    L: list[str] = []
    L.append("# Bağımlılık Lisans Envanteri")
    L.append("")
    L.append("## Künye")
    L.append("")
    L.append(f"- **Üretim tarihi:** {tarih}")
    L.append("- **Üreten komut:** `make lisanslar`")
    L.append(
        "  (`scripts/lisans_envanteri.py` → `.venv/bin/python -m piplicenses "
        "--format=json --with-urls --with-authors`)"
    )
    L.append(f"- **Yorumlayıcı:** {yorumlayici} (`{py}`)")
    L.append(
        f"- **Kapsam:** bu koşumun `.venv` envanteri — **{len(paketler)} paket**. "
        "Kurulu ortamda ne varsa o listelenmiştir; `requirements.txt`'te ilan "
        "edilen ama kurulu olmayan paketler burada YOKTUR, kurulu olup ilan "
        "edilmeyenler ise VARDIR."
    )
    L.append(
        "- **Makine-okur eşi:** [`sbom.json`](sbom.json) — CycloneDX 1.6, "
        "`make sbom` ile üretilir."
    )
    L.append(
        "- **Kapı:** [`../scripts/lisans_kapisi.py`](../scripts/lisans_kapisi.py), "
        "`make lisans-kapisi` ile koşar."
    )
    L.append("")
    L.append("### ⚠️ Sınır uyarısı")
    L.append("")
    L.append(
        "> **Python kilit dosyası yok** (`requirements.txt` `>=` pinleri taşıyor, "
        "hash yok); bu envanter **bu koşumun kesitidir**, sürüm aralığı "
        "değişirse yeniden üretilmelidir."
    )
    L.append("")
    L.append(
        "Somut sonucu: `>=` pini bir sürüm aralığı açar ve **lisans sürümle "
        "değişebilir**. Bir paketin bugün izin verici olması, aralığın tamamının "
        "izin verici olduğunu kanıtlamaz. Aşağıdaki tablo tek bir noktayı "
        "belgeler — aralığın tamamını değil."
    )
    L.append("")

    L.append("## Özet")
    L.append("")
    L.append("| Hüküm | Paket sayısı |")
    L.append("|---|---:|")
    for hukum in (IZINLI, LISTEDE_YOK, BILINMIYOR, YASAK):
        L.append(f"| {HUKUM_ROZETI[hukum]} | {sayac.get(hukum, 0)} |")
    L.append(f"| **toplam** | **{len(paketler)}** |")
    L.append("")
    if muaf_adlar:
        L.append(
            f"Bunlardan **{len(muaf_adlar)}** paket "
            "[`config/lisans_istisnalari.yaml`](../config/lisans_istisnalari.yaml) "
            "içinde **gerekçeli istisna** olarak kayıtlıdır; kapı onları bilerek "
            "geçirir. Gerekçesiz istisna kabul edilmez."
        )
        L.append("")

    L.extend(_risk_bolumu(paketler))
    L.extend(_kapsam_farki_bolumu())

    # Sorunlu kalemler önce gelsin: bir denetim belgesinde kötü haber
    # gömülmez, en üste yazılır.
    sorunlular = [p for p in paketler if p.hukum != IZINLI]
    if sorunlular:
        L.append("## İzin listesi dışındaki kalemler")
        L.append("")
        L.append("| Paket | Sürüm | Lisans | Hüküm | İstisna |")
        L.append("|---|---|---|---|---|")
        for p in sorted(sorunlular, key=lambda x: x.ad.lower()):
            muaf = "gerekçeli" if p.ad.lower() in muaf_adlar else "**YOK**"
            L.append(
                f"| `{_kacis(p.ad)}` | {_kacis(p.surum)} | {_kacis(p.lisans)} "
                f"| {HUKUM_ROZETI[p.hukum]} | {muaf} |"
            )
        L.append("")

    L.append("## Tam envanter")
    L.append("")
    L.append("| Paket | Sürüm | Lisans | Hüküm | Proje adresi |")
    L.append("|---|---|---|---|---|")
    for p in sorted(paketler, key=lambda x: x.ad.lower()):
        url = url_ile.get(p.ad, "")
        url_h = f"<{_kacis(url)}>" if url and url.upper() != "UNKNOWN" else "—"
        L.append(
            f"| `{_kacis(p.ad)}` | {_kacis(p.surum)} | {_kacis(p.lisans)} "
            f"| {HUKUM_ROZETI[p.hukum]} | {url_h} |"
        )
    L.append("")
    L.append("## Yeniden üretim")
    L.append("")
    L.append("```bash")
    L.append("make lisanslar      # bu belge")
    L.append("make sbom           # docs/sbom.json (CycloneDX 1.6)")
    L.append("make lisans-kapisi  # izin listesi dışı varsa çıkış kodu 1")
    L.append("```")
    L.append("")
    return "\n".join(L)


def main(argv: list[str] | None = None) -> int:
    ayristirici = argparse.ArgumentParser(
        description="Künyeli bağımlılık lisans envanteri üretir."
    )
    ayristirici.add_argument(
        "--cikti", type=Path, default=KOK / "docs" / "LISANSLAR.md"
    )
    ayristirici.add_argument(
        "--istisnalar", type=Path, default=KOK / "config" / "lisans_istisnalari.yaml"
    )
    args = ayristirici.parse_args(argv)

    py = Path(sys.executable)
    kayitlar = pip_licenses_calistir(py)
    istisnalar, _ = istisnalari_yukle(args.istisnalar)
    args.cikti.parent.mkdir(parents=True, exist_ok=True)
    args.cikti.write_text(belge_uret(kayitlar, py, istisnalar), encoding="utf-8")

    sorunlu = sum(1 for k in kayitlar if ifade_hukmu(str(k.get("License", ""))) != IZINLI)
    print(f"{len(kayitlar)} paket tarandı; {sorunlu} kalem izin listesi dışında.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
