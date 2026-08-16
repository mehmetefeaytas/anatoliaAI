"""Kapsamlı demo çekimi — YALNIZ gerçek arayüz.

Kart yok, mockup yok, animasyon yok. Her sekme gerçekten açılıyor, içerik
gerçekten yükleniyor ve bekleme SABİT DEĞİL koşullu: panel "yükleniyor"
iskeletinden çıkana kadar bekleniyor. (Sabit bekleme ilk denemede çelişki
sahnesini iskelet hâlinde yakalamıştı.)
"""
from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

from playwright.sync_api import Page, sync_playwright

KOK = "http://localhost:3000"
T = Path(os.environ["CLAUDE_JOB_DIR"]) / "tmp"
CIK = T / "klip2"
EN, BOY = 1920, 1080

IMLEC_JS = """
() => {
  if (document.getElementById('__im')) return;
  const ok = document.createElement('div');
  ok.id = '__im';
  ok.style.position = 'fixed'; ok.style.left = '0'; ok.style.top = '0';
  ok.style.width = '18px'; ok.style.height = '26px';
  ok.style.background = '#111'; ok.style.zIndex = '2147483647';
  ok.style.pointerEvents = 'none';
  ok.style.filter = 'drop-shadow(0 0 1.5px #fff) drop-shadow(0 2px 5px rgba(0,0,0,.45))';
  ok.style.clipPath = 'polygon(0% 0%, 0% 78%, 26% 60%, 44% 100%, 62% 92%, 45% 54%, 74% 52%)';
  ok.style.transition = 'transform .5s cubic-bezier(.33,.9,.4,1)';
  ok.style.transform = 'translate(960px, 540px)';
  const h = document.createElement('div');
  h.id = '__hl';
  h.style.position = 'fixed'; h.style.left = '0'; h.style.top = '0';
  h.style.width = '46px'; h.style.height = '46px'; h.style.borderRadius = '50%';
  h.style.background = 'rgba(200,140,40,.34)'; h.style.zIndex = '2147483646';
  h.style.pointerEvents = 'none'; h.style.opacity = '0';
  h.style.transform = 'translate(-999px,-999px)';
  document.body.appendChild(h); document.body.appendChild(ok);
}
"""

YUKLENIYOR = ("Çelişkiler getiriliyor", "hesaplanıyor", "Yükleniyor",
              "yükleniyor", "getiriliyor")


def imlec_kur(sf: Page) -> None:
    sf.evaluate(IMLEC_JS)


def imlec_git(sf: Page, x: float, y: float, bekle: int = 550) -> None:
    sf.evaluate("([x,y]) => { const d = document.getElementById('__im');"
                " if (d) d.style.transform = 'translate('+x+'px,'+y+'px)'; }", [x, y])
    sf.mouse.move(x, y)
    sf.wait_for_timeout(bekle)


def tikla_efekti(sf: Page, x: float, y: float) -> None:
    sf.evaluate(
        "([x,y]) => { const h = document.getElementById('__hl'); if (!h) return;"
        " h.style.transition='none'; h.style.opacity='1';"
        " h.style.transform='translate('+(x-23)+'px,'+(y-23)+'px) scale(.4)';"
        " requestAnimationFrame(() => { h.style.transition='all .5s ease-out';"
        "  h.style.opacity='0';"
        "  h.style.transform='translate('+(x-23)+'px,'+(y-23)+'px) scale(1.5)'; }); }",
        [x, y])


def tikla(sf: Page, konum, bekle: int = 1200) -> None:
    konum.scroll_into_view_if_needed()
    sf.wait_for_timeout(420)
    k = konum.bounding_box()
    if not k:
        raise RuntimeError("öğe görünür değil")
    x, y = k["x"] + k["width"] / 2, k["y"] + k["height"] / 2
    imlec_git(sf, x, y)
    tikla_efekti(sf, x, y)
    konum.click()
    sf.wait_for_timeout(bekle)


def yuklenmeyi_bekle(sf: Page, azami: int = 90000) -> None:
    """İskeletten çıkana kadar bekle. Sabit süre vermek sahneyi yarım yakalar."""
    kosul = " && ".join(f"!t.includes({m!r})" for m in YUKLENIYOR)
    try:
        sf.wait_for_function(f"() => {{ const t = document.body.innerText;"
                             f" return {kosul}; }}", timeout=azami)
    except Exception:
        pass
    sf.wait_for_timeout(1200)


def kaydir(sf: Page, y: int, sure: int = 1300) -> None:
    sf.evaluate("(y) => window.scrollTo({top: y, behavior: 'smooth'})", y)
    sf.wait_for_timeout(sure)


def yeni(tar, ad: str):
    d = CIK / ad
    d.mkdir(parents=True, exist_ok=True)
    return tar.new_context(viewport={"width": EN, "height": BOY},
                           device_scale_factor=1,
                           record_video_dir=str(d),
                           record_video_size={"width": EN, "height": BOY},
                           locale="tr-TR")


def hazirla(sf: Page) -> None:
    sf.goto(KOK, wait_until="networkidle", timeout=60000)
    sf.wait_for_timeout(1600)
    imlec_kur(sf)
    d = sf.get_by_role("button", name="Jüri modu", exact=False).first
    if "kapalı" in (d.inner_text() or ""):
        d.click()
        sf.wait_for_timeout(1300)
    imlec_kur(sf)


def sekme(sf: Page, ad: str):
    return sf.locator("button", has_text=ad).first


def dugme(sf: Page, ad: str):
    """Tam eşleşme. 'Açık' alt dize olarak 'Jüri modu: açık'a da düşüyor."""
    return sf.get_by_role("button", name=ad, exact=True).first


# ——— sahneler ———————————————————————————————————————————————

def s_acilis(tar) -> None:
    """Ürün belirir + tema geçişi (açık → koyu)."""
    b = yeni(tar, "acilis")
    sf = b.new_page()
    hazirla(sf)
    sf.wait_for_timeout(3200)
    kaydir(sf, 300, 1600)
    sf.wait_for_timeout(2600)
    kaydir(sf, 640, 1600)
    sf.wait_for_timeout(2600)
    kaydir(sf, 0, 1500)
    tikla(sf, dugme(sf, "Koyu"), 3200)          # tema geçişi — görsel an
    kaydir(sf, 420, 1600)
    sf.wait_for_timeout(2600)
    kaydir(sf, 0, 1500)
    tikla(sf, dugme(sf, "Açık"), 2600)
    sf.wait_for_timeout(1800)
    b.close()


def _tur(tar, ad: str, sekme_adi: str, kaydirmalar: list[int],
         bekle_sonra: int = 2600) -> None:
    b = yeni(tar, ad)
    sf = b.new_page()
    hazirla(sf)
    tikla(sf, sekme(sf, sekme_adi), 1200)
    yuklenmeyi_bekle(sf)
    sf.wait_for_timeout(1400)
    for y in kaydirmalar:
        kaydir(sf, y, 1500)
        sf.wait_for_timeout(bekle_sonra)
    # Kuyruk payı: kurgu penceresi klibin SONUNA yaslanıyor (böylece içerik
    # kesin yüklü olur). Sonda pay bırakmazsan pencere yükleme ekranına taşar.
    sf.wait_for_timeout(4000)
    b.close()


def s_cetvel(tar) -> None:
    b = yeni(tar, "cetvel")
    sf = b.new_page()
    hazirla(sf)
    kaydir(sf, 400, 1400)
    sf.wait_for_timeout(2400)
    tikla(sf, sekme(sf, "Vade (ay)"), 3400)
    kaydir(sf, 700, 1500)
    sf.wait_for_timeout(2800)
    kaydir(sf, 400, 1400)
    tikla(sf, sekme(sf, "Kâr Payı Oranı"), 3600)
    kaydir(sf, 780, 1500)
    sf.wait_for_timeout(3400)
    kaydir(sf, 1080, 1400)
    sf.wait_for_timeout(3400)
    kaydir(sf, 1420, 1400)
    sf.wait_for_timeout(3200)
    b.close()


def s_sohbet(tar) -> None:
    b = yeni(tar, "sohbet")
    sf = b.new_page()
    hazirla(sf)
    tikla(sf, sekme(sf, "Chatbot"), 1800)
    kaydir(sf, 240, 1200)
    kutu = sf.locator("textarea, input[type=text]").first
    k = kutu.bounding_box()
    if k:
        imlec_git(sf, k["x"] + 60, k["y"] + k["height"] / 2)
        tikla_efekti(sf, k["x"] + 60, k["y"] + k["height"] / 2)
    kutu.click()
    kutu.type("36 ay ve üzeri vade veren konut finansmanlarını listele", delay=42)
    sf.wait_for_timeout(600)
    sf.keyboard.press("Enter")
    yuklenmeyi_bekle(sf, 60000)
    sf.wait_for_timeout(3600)
    kaydir(sf, 380, 1500)
    sf.wait_for_timeout(3600)
    kaydir(sf, 700, 1500)
    sf.wait_for_timeout(3600)
    kaydir(sf, 1020, 1500)
    sf.wait_for_timeout(3600)
    b.close()


def s_canli(tar) -> None:
    """Canlı çıkarım — sistem gerçekten çalışıyor mu sorusunun en dolaysız cevabı."""
    b = yeni(tar, "canli")
    sf = b.new_page()
    hazirla(sf)
    tikla(sf, sekme(sf, "Canlı Çıkarım"), 2000)
    yuklenmeyi_bekle(sf, 30000)
    sf.wait_for_timeout(1500)
    kaydir(sf, 380, 1400)
    sf.wait_for_timeout(2200)
    # varsa "çıkar / çalıştır" düğmesine bas
    for etiket in ("Çıkar", "Çalıştır", "Analiz"):
        d = sf.locator("button", has_text=etiket)
        if d.count():
            try:
                tikla(sf, d.first, 1500)
                yuklenmeyi_bekle(sf, 60000)
                break
            except Exception:
                pass
    sf.wait_for_timeout(2600)
    kaydir(sf, 820, 1400)
    sf.wait_for_timeout(3000)
    b.close()


SAHNELER = {
    "acilis":  s_acilis,
    "cetvel":  s_cetvel,
    "isi":     lambda t: _tur(t, "isi", "Isı Haritası", [300, 600, 900], 3000),
    "avantaj": lambda t: _tur(t, "avantaj", "En Avantajlı", [320, 640, 960], 3000),
    "banka":   lambda t: _tur(t, "banka", "Banka Sayfası", [360, 800]),
    "delta":   lambda t: _tur(t, "delta", "Banka İçi Delta", [380, 820]),
    "celiski": lambda t: _tur(t, "celiski", "Çelişki Tespiti",
                              [360, 700, 1040, 1380], 3400),
    "kanit":   lambda t: _tur(t, "kanit", "Jüri Audit",
                              [520, 900, 1240, 1560, 1900], 3200),
    "canli":   s_canli,
    "sohbet":  s_sohbet,
    "tazele":  lambda t: _tur(t, "tazele", "Veri Tazeleme", [280, 560], 3200),
    "ayarlar": lambda t: _tur(t, "ayarlar", "Ayarlar",
                              [300, 620, 940, 1260, 1580], 3000),
    "gunluk":  lambda t: _tur(t, "gunluk", "İşlem Günlüğü",
                              [280, 560, 840, 1120], 3400),
}

if __name__ == "__main__":
    istenen = sys.argv[1:] or list(SAHNELER)
    if not sys.argv[1:] and CIK.exists():
        shutil.rmtree(CIK)
    with sync_playwright() as p:
        tar = p.chromium.launch(args=["--force-color-profile=srgb", "--hide-scrollbars"])
        for ad in istenen:
            print(f"çekiliyor: {ad}", flush=True)
            try:
                SAHNELER[ad](tar)
            except Exception as exc:            # noqa: BLE001
                print(f"  ✗ {ad}: {str(exc)[:110]}", flush=True)
        tar.close()
    for d in sorted(CIK.iterdir()):
        for v in d.glob("*.webm"):
            print(f"{d.name:9s} {v.stat().st_size // 1024:6d} KB")
