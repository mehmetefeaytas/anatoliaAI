"""Dolu-veri sahneleri — kıyas cetveli, en avantajlı, banka sayfası.

Önceki çekimde bu üç sahne korpusun EN SEYREK kesitine denk gelmişti:
banka sayfası varsayılan olarak Adil Katılım'ı açıyor (6 belge, 12 alandan
2'si dolu — korpusun en boşu) ve cetvel varsayılan alan olarak
`kar_payi_orani`yi gösteriyor (70 belge, en seyrek alan).

Bu çekim aynı arayüzün DOLU kesitini seçiyor — veri uydurmuyor, var olanın
en dolusunu gösteriyor:

  Kuveyt Türk   537 belge · 12/12 alan · 1.703 değer  (en dolu banka)
  Kart          638 kampanya                          (en dolu tür)
  vade_ay       444 belge · masraf_durumu 498 belge   (dolu alanlar)

Ölçüm: `sqlite3 data/demo.db` — bu dosyanın başlığındaki sayılar oradan.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

from playwright.sync_api import Page, sync_playwright

sys.path.insert(0, str(Path(__file__).parent))
from cek2 import (
    CIK,
    hazirla,
    kaydir,
    sekme,
    tikla,
    yeni,
    yuklenmeyi_bekle,
)

T = Path(os.environ["CLAUDE_JOB_DIR"]) / "tmp"

EN_DOLU_BANKA = "Kuveyt Türk"
EN_DOLU_TUR = "Kart"            # kıyas cetveli + banka sayfası için en dolu tür
# En Avantajlı AYRI bir tür istiyor: sıralama bileşik skor gerektirdiği için
# "en çok kampanya" ile "en çok SIRALANABİLİR kampanya" aynı tür değil.
# Arayüzden tür tür sayıldı: Yatırım Ürünü 14 · Konut 9 · Taşıt 9 · Kart 4.
EN_SIRALANABILIR_TUR = "Yatırım Ürünü"


def sec(sf: Page, indeks: int, etiket: str, bekle: int = 2600) -> None:
    """Açılır listeden etiketle seç; imleci de oraya sür ki sahne ölü durmasın."""
    s = sf.locator("select").nth(indeks)
    s.scroll_into_view_if_needed()
    sf.wait_for_timeout(400)
    k = s.bounding_box()
    if k:
        from cek2 import imlec_git, tikla_efekti
        x, y = k["x"] + k["width"] / 2, k["y"] + k["height"] / 2
        imlec_git(sf, x, y)
        tikla_efekti(sf, x, y)
    s.select_option(label=etiket)
    sf.wait_for_timeout(bekle)


def s_cetvel(tar) -> None:
    """Kıyas cetveli — Kart türü, dolu alanlar, tüm kampanyalar."""
    b = yeni(tar, "cetvel3")
    sf = b.new_page()
    hazirla(sf)
    kaydir(sf, 380, 1400)
    sf.wait_for_timeout(1600)
    sec(sf, 1, EN_DOLU_TUR, 3000)              # kampanya türü süzgeci
    sec(sf, 2, "Tüm kampanyaları göster", 3000)
    kaydir(sf, 620, 1500)
    sf.wait_for_timeout(3000)
    kaydir(sf, 380, 1300)
    tikla(sf, sekme(sf, "Vade (ay)"), 3400)
    kaydir(sf, 700, 1500)
    sf.wait_for_timeout(3400)
    kaydir(sf, 380, 1300)
    tikla(sf, sekme(sf, "Masraf Durumu"), 3400)
    kaydir(sf, 720, 1500)
    sf.wait_for_timeout(3400)
    kaydir(sf, 1060, 1400)
    sf.wait_for_timeout(3400)
    kaydir(sf, 1400, 1400)
    sf.wait_for_timeout(3400)
    kaydir(sf, 1740, 1400)
    sf.wait_for_timeout(3400)
    # Uzun kuyruk bilerek: kurgu penceresi sona yaslandığı için, kuyruk kısa
    # olursa pencere alan geçişinin İSKELET anına taşıyor (kare denetiminde
    # görüldü — videonun ilk saniyesi yükleme ekranı oluyordu).
    sf.wait_for_timeout(4000)
    b.close()


def s_avantaj(tar) -> None:
    """En avantajlı — en çok satırı sıralanabilen tür (Yatırım Ürünü, 14/98)."""
    b = yeni(tar, "avantaj3")
    sf = b.new_page()
    hazirla(sf)
    tikla(sf, sekme(sf, "En Avantajlı"), 1400)
    yuklenmeyi_bekle(sf)
    sf.wait_for_timeout(1400)
    sec(sf, 0, EN_SIRALANABILIR_TUR, 3400)
    kaydir(sf, 320, 1500)
    sf.wait_for_timeout(3200)
    kaydir(sf, 640, 1500)
    sf.wait_for_timeout(3200)
    kaydir(sf, 940, 1500)
    sf.wait_for_timeout(3000)
    sf.wait_for_timeout(3000)
    b.close()


def s_banka(tar) -> None:
    """Banka sayfası — korpusun en dolu bankası, varsayılan en boşu değil."""
    b = yeni(tar, "banka3")
    sf = b.new_page()
    hazirla(sf)
    tikla(sf, sekme(sf, "Banka Sayfası"), 1400)
    yuklenmeyi_bekle(sf)
    sf.wait_for_timeout(1200)
    sec(sf, 0, EN_DOLU_BANKA, 3600)            # banka seçimi
    kaydir(sf, 300, 1500)
    sf.wait_for_timeout(3200)
    sec(sf, 2, EN_DOLU_TUR, 3400)              # tür süzgeci → delta doluyor
    kaydir(sf, 640, 1500)
    sf.wait_for_timeout(3200)
    kaydir(sf, 980, 1500)
    sf.wait_for_timeout(3200)
    sf.wait_for_timeout(3000)
    b.close()


SAHNELER = {"cetvel3": s_cetvel, "avantaj3": s_avantaj, "banka3": s_banka}

if __name__ == "__main__":
    istenen = sys.argv[1:] or list(SAHNELER)
    with sync_playwright() as p:
        tar = p.chromium.launch(args=["--force-color-profile=srgb", "--hide-scrollbars"])
        for ad in istenen:
            print(f"çekiliyor: {ad}", flush=True)
            try:
                SAHNELER[ad](tar)
            except Exception as exc:
                print(f"  ✗ {ad}: {str(exc)[:140]}", flush=True)
        tar.close()
    for ad in istenen:
        for v in (CIK / ad).glob("*.webm"):
            print(f"{ad:9s} {v.stat().st_size // 1024:6d} KB")
