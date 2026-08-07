#!/usr/bin/env python3
"""TCMB Terimler Sözlüğü ham HTML'ini yapılandırılmış JSON'a çevirir.

Kaynak sayfa tek parçadır: dış `div.block-collapse` harf grubunu (A, B, C...),
iç `div.block-collapse` tek bir terimi taşır. Terim başlığı
`a.block-collapse-title` içindedir ve "Türkçe Terim (English Term)" biçimindedir.

Kullanım:
    .venv/bin/python scripts/tcmb_sozluk_ayristir.py
"""

from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path

from bs4 import BeautifulSoup

KOK = Path(__file__).resolve().parent.parent
HAM = KOK / "data" / "terminology" / "_tcmb_ham" / "terimler-sozlugu.html"
CIKTI = KOK / "data" / "terminology" / "tcmb-terimler.json"

KAYNAK_URL = (
    "https://www.tcmb.gov.tr/wps/wcm/connect/tr/tcmb+tr/main+menu/"
    "banka+hakkinda/egitim-akademik/terimler+sozlugu/"
)

# Başlık sonundaki "(...)" parantezi İngilizce karşılıktır.
PARANTEZ = re.compile(r"^(?P<tr>.+?)\s*\((?P<en>[^()]*(?:\([^()]*\)[^()]*)*)\)\s*$")


def bosluk_sadelestir(metin: str) -> str:
    """NBSP ve tekrar eden boşlukları tek boşluğa indirir."""
    metin = metin.replace("\xa0", " ").replace("\u200b", "")
    return re.sub(r"\s+", " ", metin).strip()


def slug(metin: str) -> str:
    """Türkçe karakterleri sadeleştirip kebab-case kimlik üretir."""
    esle = str.maketrans("şçıİğüöŞÇĞÜÖ", "sciiguoSCGUO")
    metin = metin.translate(esle)
    metin = unicodedata.normalize("NFKD", metin)
    metin = "".join(k for k in metin if not unicodedata.combining(k))
    metin = re.sub(r"[^A-Za-z0-9]+", "-", metin).strip("-").lower()
    return metin


def ayristir(html: str) -> list[dict]:
    corba = BeautifulSoup(html, "html.parser")
    ana = corba.find(id="tcmbMainContent")
    if ana is None:
        raise SystemExit("tcmbMainContent bulunamadı — sayfa yapısı değişmiş olabilir.")

    kayitlar: list[dict] = []
    gorulen: set[str] = set()

    for harf_bloku in ana.find_all("div", class_="block-collapse", recursive=False):
        harf_basligi = harf_bloku.find("a", class_="block-collapse-title")
        harf = bosluk_sadelestir(harf_basligi.get_text()) if harf_basligi else ""
        alt = harf_bloku.find("div", class_="block-collapse-subbox")
        if alt is None:
            continue

        for terim_bloku in alt.find_all("div", class_="block-collapse", recursive=False):
            baslik_etiketi = terim_bloku.find("a", class_="block-collapse-title")
            govde = terim_bloku.find("div", class_="block-collapse-subbox")
            if baslik_etiketi is None or govde is None:
                continue

            baslik = bosluk_sadelestir(baslik_etiketi.get_text())
            tanim = bosluk_sadelestir(govde.get_text(" "))
            if not baslik or not tanim:
                continue

            eslesme = PARANTEZ.match(baslik)
            if eslesme:
                terim = bosluk_sadelestir(eslesme.group("tr"))
                ingilizce = bosluk_sadelestir(eslesme.group("en"))
            else:
                terim, ingilizce = baslik, ""

            kimlik = slug(terim)
            if kimlik in gorulen:
                kimlik = f"{kimlik}-{len(kayitlar)}"
            gorulen.add(kimlik)

            kayit = {
                "id": kimlik,
                "terim": terim,
                "harf": harf,
                "tanim": tanim,
                "kaynak_url": KAYNAK_URL,
                "kaynak_kurum": "TCMB",
                "otorite_tipi": "konvansiyonel",
            }
            if ingilizce:
                kayit["ingilizce"] = ingilizce
            kayitlar.append(kayit)

    return kayitlar


def main() -> None:
    kayitlar = ayristir(HAM.read_text(encoding="utf-8"))
    CIKTI.write_text(
        json.dumps(kayitlar, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    harfler = sorted({k["harf"] for k in kayitlar})
    ingilizceli = sum(1 for k in kayitlar if k.get("ingilizce"))
    print(f"{len(kayitlar)} terim yazıldı → {CIKTI}")
    print(f"Harf grubu: {len(harfler)} ({' '.join(harfler)})")
    print(f"İngilizce karşılığı olan: {ingilizceli}")


if __name__ == "__main__":
    main()
