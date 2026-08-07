#!/usr/bin/env python3
"""TCMB sözlüğü ile katılım terim sözlüğünü karşılaştıran ölçüm aracı.

Rapor: ../docs/terminoloji-tcmb-capraz.md
Bu betik yalnızca SAYI üretir; yorum rapora elle yazılır.

## Ölçümün iki ayrı sorusu — karıştırılmamalı

Naif bir "terim TCMB'de geçiyor mu" araması yanıltıcıdır, ölçüldü:

  * `Riba` girdisinin `varyantlar` listesinde "faiz" yazılıdır. Naif arama bunu
    TCMB'nin "Faiz Oranı" başlığıyla eşleştirip "riba TCMB'de VAR" der. Oysa
    bu KAPSAMA değil, tam tersine ÇATIŞMA'dır: TCMB faizi meşru bir politika
    aracı olarak tanımlar, sözlüğümüz onu yasak olarak tanımlar.
  * `en` alanı üzerinden eşleşme İngilizce sahte-dost üretir: `Vekâlet`in
    "Agency" karşılığı TCMB'nin "Central Registry Agency" (MKK) başlığına,
    `Tediye`nin "Payment" karşılığı yedi ayrı ödeme sistemi başlığına düşer.

Bu yüzden üç ayrı geçiş yapılır:
    KAPSAMA  — Türkçe kanonik + `degildir` DIŞINDAKİ varyantlar
    ÇATIŞMA  — girdinin `degildir` listesi TCMB'de başlık mı?
    SAHTE-DOST — yalnız İngilizce üzerinden eşleşenler (ayrı raporlanır)

Kullanım:
    .venv/bin/python scripts/tcmb_capraz_analiz.py
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK))

from src.preprocessing.clean import tr_fold_ascii

TCMB = KOK / "data" / "terminology" / "tcmb-terimler.json"
KATILIM = KOK / "data" / "terminology" / "katilim-terim-sozlugu.json"

#: Katılım finansının çekirdek fıkhî/kurumsal terimleri — görev tanımındaki
#: liste. "Konvansiyonel otorite katılım terminolojisini kapsamıyor" tezinin
#: doğrudan test kümesi.
CEKIRDEK = (
    "murabaha", "mudaraba", "musaraka", "icare", "sukuk", "karz-i hasen",
    "tekaful", "katilma hesabi", "kar payi", "selem", "istisna", "vekalet",
    "riba", "garar", "meysir", "ozel cari hesap", "vade farki", "tahsis ucreti",
)

#: `scripts/jargon_lint.py::YASAK_KOKLER` ile aynı üçlü.
CATISMA_KOKLERI = ("faiz", "kredi", "mevduat")


def sozcuk_kalibi(ifade: str) -> re.Pattern:
    return re.compile(rf"(?<![a-z0-9]){re.escape(ifade)}(?![a-z0-9])")


def yukle():
    return (json.loads(TCMB.read_text(encoding="utf-8")),
            json.loads(KATILIM.read_text(encoding="utf-8")))


def tcmb_dizinleri(tcmb: list[dict]):
    """(tr_baslik, en_baslik, tanim, kayit) dörtlüleri — hepsi katlanmış."""
    return [(tr_fold_ascii(t["terim"]),
             tr_fold_ascii(t.get("ingilizce", "")),
             tr_fold_ascii(t["tanim"]),
             t) for t in tcmb]


def _katla(ifadeler) -> list[str]:
    cikti, gorulen = [], set()
    for k in ifadeler:
        katli = tr_fold_ascii(k or "").strip()
        if katli and katli not in gorulen and len(katli) > 2:
            gorulen.add(katli)
            cikti.append(katli)
    return cikti


def kapsama_anahtarlari(e: dict) -> list[str]:
    """Türkçe teknik ifadeler; `degildir` içindekiler ÇIKARILIR.

    `halk_dili` kasten dışarıda (bkz. terminology.py §"İki ayrı sözcük
    dağarcığı"): "ödeme", "kazanç", "faiz" gibi genel ifadeler her katılım
    terimini TCMB'de "var" gösterirdi.
    """
    degildir = set(_katla(e.get("degildir") or []))
    return [a for a in _katla([e.get("kanonik", ""), *(e.get("varyantlar") or [])])
            if a not in degildir]


def main() -> None:
    tcmb, kat = yukle()
    dizin = tcmb_dizinleri(tcmb)

    print("=" * 72)
    print(f"TCMB terim sayısı    : {len(tcmb)}")
    print(f"Katılım terim sayısı : {len(kat)}")
    print("=" * 72)

    # ------------------------------------------------------------------ #
    # 1. KAPSAMA — katılım terimi TCMB başlığında karşılık buluyor mu?
    # ------------------------------------------------------------------ #
    var, yok, sahte_dost = [], [], []
    for e in kat:
        tr_bulgu, en_bulgu = [], []
        for a in kapsama_anahtarlari(e):
            k = sozcuk_kalibi(a)
            tr_bulgu.extend(t["terim"] for tr, _, _, t in dizin if k.search(tr))
        for a in _katla(p for p in (e.get("en") or "").split("/")):
            k = sozcuk_kalibi(a)
            en_bulgu.extend(t["terim"] for _, en, _, t in dizin if en and k.search(en))

        if tr_bulgu:
            var.append((e, sorted(set(tr_bulgu))))
        else:
            yok.append(e)
            if en_bulgu:
                sahte_dost.append((e, sorted(set(en_bulgu))))

    print(f"\n## 1. KAPSAMA — Türkçe başlıkta karşılığı olan: {len(var)}/{len(kat)}")
    for e, b in var:
        print(f"   {e['kanonik']:<24} -> {', '.join(b[:4])}")
    print(f"\n   TCMB'DE HİÇ YOK: {len(yok)}/{len(kat)} "
          f"(%{100 * len(yok) / len(kat):.1f})")

    print(f"\n   [İngilizce sahte-dost — Türkçe karşılığı YOK ama İngilizce "
          f"eşleşiyor: {len(sahte_dost)}]")
    for e, b in sahte_dost:
        print(f"      {e['kanonik']} ({e.get('en')}) ~ {', '.join(b[:3])}")

    # ------------------------------------------------------------------ #
    # 2. ÇEKİRDEK fıkhî terimler
    # ------------------------------------------------------------------ #
    print(f"\n## 2. ÇEKİRDEK KATILIM TERİMLERİ ({len(CEKIRDEK)} terim)")
    cek_yok = []
    for c in CEKIRDEK:
        k = sozcuk_kalibi(c)
        basliklar = [t["terim"] for tr, _, _, t in dizin if k.search(tr)]
        if basliklar:
            print(f"   VAR  {c:<18} -> {', '.join(basliklar)}")
        else:
            govdede = [t["terim"] for _, _, g, t in dizin if k.search(g)]
            cek_yok.append(c)
            ek = f"   (yalnız tanım metninde: {', '.join(govdede)})" if govdede else ""
            print(f"   YOK  {c:<18}{ek}")
    print(f"   ---> {len(CEKIRDEK)} çekirdek terimden {len(cek_yok)}'i "
          f"TCMB başlıklarında YOK (%{100 * len(cek_yok) / len(CEKIRDEK):.0f})")

    # ------------------------------------------------------------------ #
    # 3. ÇATIŞMA — `degildir` listesi TCMB'de başlık mı?
    # ------------------------------------------------------------------ #
    print("\n## 3. ÇATIŞMA — sözlüğümüzün 'DEĞİLDİR' dediğini TCMB tanımlıyor mu?")
    catisma = []
    for e in kat:
        for yanlis in (e.get("degildir") or []):
            katli = tr_fold_ascii(yanlis).strip()
            if not any(re.search(rf"\b{kok}", katli) for kok in CATISMA_KOKLERI):
                continue
            k = sozcuk_kalibi(katli)
            eslesen = [t for tr, _, _, t in dizin if k.search(tr)]
            if not eslesen:
                # kök düzeyinde (faizli, kredisi ...) ara
                kok_k = re.compile("|".join(rf"(?<![a-z0-9]){kk}[a-z]*(?![a-z0-9])"
                                            for kk in CATISMA_KOKLERI
                                            if re.search(rf"\b{kk}", katli)))
                eslesen = [t for tr, _, _, t in dizin if kok_k.search(tr)]
            if eslesen:
                catisma.append((e, yanlis, [t["terim"] for t in eslesen]))
    for e, yanlis, tl in catisma:
        print(f"   {e['kanonik']:<22} DEĞİLDİR '{yanlis}' <-> TCMB: "
              f"{', '.join(tl[:3])}{' ...' if len(tl) > 3 else ''}")
    print(f"   ---> {len(catisma)} doğrudan çatışma çifti, "
          f"{len({c[0]['id'] for c in catisma})} ayrı katılım terimi")

    print("\n   Yasak köklerin TCMB'deki yaygınlığı:")
    for kok in CATISMA_KOKLERI:
        k = re.compile(rf"(?<![a-z0-9]){kok}[a-z]*(?![a-z0-9])")
        bas = [t["terim"] for tr, _, _, t in dizin if k.search(tr)]
        gov = sum(1 for _, _, g, _ in dizin if k.search(g))
        print(f"      '{kok}': {len(bas)} başlık, {gov} tanım metni")
        for b in bas:
            print(f"           - {b}")

    # ------------------------------------------------------------------ #
    # 4. TCMB'de olup bizde olmayan — projeye yarayacaklar
    # ------------------------------------------------------------------ #
    kat_tum = set()
    for e in kat:
        kat_tum.update(kapsama_anahtarlari(e))
        kat_tum.update(_katla(e.get("halk_dili") or []))
    fazla = [t for tr, _, _, t in dizin if tr not in kat_tum]

    # Kampanya/ürün metinlerinde gerçekten geçebilecek alanlar.
    URUN = ("vade", "taksit", "oran", "tuketici", "konut", "tasit", "kart",
            "teminat", "ipotek", "kiralama", "komisyon", "masraf", "ucret",
            "anapara", "hesap", "kur", "enflasyon", "tufe", "kredi", "faiz")
    urun_ilgili = [t for t in fazla
                   if any(u in tr_fold_ascii(t["terim"]) for u in URUN)]
    print(f"\n## 4. TCMB'de olup katılım sözlüğünde olmayan: {len(fazla)}")
    print(f"   bunlardan ürün/kampanya alanına DOĞRUDAN değen "
          f"(başlıkta vade/oran/kart/... geçen): {len(urun_ilgili)}")
    for t in urun_ilgili:
        print(f"      - {t['terim']}")

    print("\n" + "=" * 72)
    print(f"ÖZET  TCMB={len(tcmb)} Katılım={len(kat)} | kapsanan={len(var)} "
          f"kapsanmayan={len(yok)} | çekirdek_yok={len(cek_yok)}/{len(CEKIRDEK)} "
          f"| çatışma_çifti={len(catisma)} | tcmb_fazlası={len(fazla)}")
    print("=" * 72)


if __name__ == "__main__":
    main()
