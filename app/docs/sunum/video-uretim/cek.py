"""Demo videosu — gerçek arayüzden klip çekimi.

Playwright videoya imleci BASMAZ; bu yüzden sayfaya sahte bir imleç
enjekte ediliyor ve tıklamadan önce hedefe yumuşakça sürülüyor. İmleç
saf CSS ile çizilir (`clip-path`) — sayfaya işaretleme enjekte edilmez.

Kayıt gerçek arayüzün gerçek davranışıdır: sahne yok, mockup yok.
"""
from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

from playwright.sync_api import Page, sync_playwright

KOK = "http://localhost:3000"
T = Path(os.environ["CLAUDE_JOB_DIR"]) / "tmp"
CIK = T / "klip"
EN, BOY = 1920, 1080

IMLEC_JS = """
() => {
  if (document.getElementById('__im')) return;
  const ok = document.createElement('div');
  ok.id = '__im';
  ok.style.position = 'fixed';
  ok.style.left = '0'; ok.style.top = '0';
  ok.style.width = '18px'; ok.style.height = '26px';
  ok.style.background = '#111';
  ok.style.zIndex = '2147483647';
  ok.style.pointerEvents = 'none';
  ok.style.filter = 'drop-shadow(0 0 1.5px #fff) drop-shadow(0 2px 5px rgba(0,0,0,.45))';
  ok.style.clipPath = 'polygon(0% 0%, 0% 78%, 26% 60%, 44% 100%, 62% 92%, 45% 54%, 74% 52%)';
  ok.style.transition = 'transform .55s cubic-bezier(.33,.9,.4,1)';
  ok.style.transform = 'translate(960px, 540px)';

  const halka = document.createElement('div');
  halka.id = '__hl';
  halka.style.position = 'fixed';
  halka.style.left = '0'; halka.style.top = '0';
  halka.style.width = '46px'; halka.style.height = '46px';
  halka.style.borderRadius = '50%';
  halka.style.background = 'rgba(200,140,40,.34)';
  halka.style.zIndex = '2147483646';
  halka.style.pointerEvents = 'none';
  halka.style.opacity = '0';
  halka.style.transform = 'translate(-999px,-999px)';

  document.body.appendChild(halka);
  document.body.appendChild(ok);
}
"""


def imlec_kur(sf: Page) -> None:
    sf.evaluate(IMLEC_JS)


def imlec_git(sf: Page, x: float, y: float, bekle: int = 650) -> None:
    sf.evaluate(
        "([x,y]) => { const d = document.getElementById('__im');"
        " if (d) d.style.transform = 'translate(' + x + 'px,' + y + 'px)'; }", [x, y])
    sf.mouse.move(x, y)
    sf.wait_for_timeout(bekle)


def tikla_efekti(sf: Page, x: float, y: float) -> None:
    sf.evaluate(
        "([x,y]) => { const h = document.getElementById('__hl'); if (!h) return;"
        " h.style.transition = 'none'; h.style.opacity = '1';"
        " h.style.transform = 'translate(' + (x-23) + 'px,' + (y-23) + 'px) scale(.4)';"
        " requestAnimationFrame(() => { h.style.transition = 'all .5s ease-out';"
        "   h.style.opacity = '0';"
        "   h.style.transform = 'translate(' + (x-23) + 'px,' + (y-23) + 'px) scale(1.5)'; }); }",
        [x, y])


def hedefe_tikla(sf: Page, konum, bekle_sonra: int = 1400) -> None:
    """Öğeye imleci sür, tıklama halkasını göster, tıkla."""
    konum.scroll_into_view_if_needed()
    sf.wait_for_timeout(500)
    k = konum.bounding_box()
    if not k:
        raise RuntimeError("öğe görünür değil")
    x, y = k["x"] + k["width"] / 2, k["y"] + k["height"] / 2
    imlec_git(sf, x, y)
    tikla_efekti(sf, x, y)
    konum.click()
    sf.wait_for_timeout(bekle_sonra)


def kaydir(sf: Page, y: int, sure: int = 1200) -> None:
    sf.evaluate("(y) => window.scrollTo({top: y, behavior: 'smooth'})", y)
    sf.wait_for_timeout(sure)


def yeni(tarayici, ad: str):
    d = CIK / ad
    d.mkdir(parents=True, exist_ok=True)
    return tarayici.new_context(
        viewport={"width": EN, "height": BOY},
        device_scale_factor=1,
        record_video_dir=str(d),
        record_video_size={"width": EN, "height": BOY},
        locale="tr-TR",
    )


def juri_ac(sf: Page) -> None:
    sf.goto(KOK, wait_until="networkidle", timeout=60000)
    sf.wait_for_timeout(1800)
    imlec_kur(sf)
    d = sf.get_by_role("button", name="Jüri modu", exact=False).first
    if "kapalı" in (d.inner_text() or ""):
        d.click()
        sf.wait_for_timeout(1500)
    imlec_kur(sf)


def klip_pano(tarayici) -> None:
    b = yeni(tarayici, "pano")
    sf = b.new_page()
    juri_ac(sf)
    sf.wait_for_timeout(2200)
    kaydir(sf, 260, 1600)
    sf.wait_for_timeout(1400)
    kaydir(sf, 620, 1600)
    sf.wait_for_timeout(2000)
    b.close()


def klip_cetvel(tarayici) -> None:
    b = yeni(tarayici, "cetvel")
    sf = b.new_page()
    juri_ac(sf)
    kaydir(sf, 420, 1400)
    sf.wait_for_timeout(900)
    hedefe_tikla(sf, sf.locator("button", has_text="Vade (ay)").first, 2000)
    hedefe_tikla(sf, sf.locator("button", has_text="Kâr Payı Oranı").first, 2400)
    kaydir(sf, 760, 1400)
    sf.wait_for_timeout(2600)
    kaydir(sf, 1050, 1300)
    sf.wait_for_timeout(2600)
    b.close()


def klip_kanit(tarayici) -> None:
    b = yeni(tarayici, "kanit")
    sf = b.new_page()
    juri_ac(sf)
    hedefe_tikla(sf, sf.locator("button", has_text="Jüri Audit").first, 2600)
    kaydir(sf, 520, 1400)
    sf.wait_for_timeout(1800)
    kaydir(sf, 1150, 1500)
    sf.wait_for_timeout(3200)
    kaydir(sf, 1520, 1400)
    sf.wait_for_timeout(2800)
    b.close()


def klip_sohbet(tarayici) -> None:
    b = yeni(tarayici, "sohbet")
    sf = b.new_page()
    juri_ac(sf)
    hedefe_tikla(sf, sf.locator("button", has_text="Chatbot").first, 2200)
    kaydir(sf, 240, 1200)
    kutu = sf.locator("textarea, input[type=text]").first
    k = kutu.bounding_box()
    if k:
        x, y = k["x"] + 60, k["y"] + k["height"] / 2
        imlec_git(sf, x, y)
        tikla_efekti(sf, x, y)
    kutu.click()
    kutu.type("Hangi bankada en düşük kâr payı oranı var?", delay=55)
    sf.wait_for_timeout(700)
    sf.keyboard.press("Enter")
    sf.wait_for_timeout(6500)
    kaydir(sf, 560, 1500)
    sf.wait_for_timeout(3200)
    b.close()


def klip_celiski(tarayici) -> None:
    b = yeni(tarayici, "celiski")
    sf = b.new_page()
    juri_ac(sf)
    hedefe_tikla(sf, sf.locator("button", has_text="Çelişki Tespiti").first, 1500)
    # Tarama korpusun tamamını geziyor; 14 sn yetmedi (ölçüldü). Panelin
    # "getiriliyor" iskeletinden çıkmasını BEKLE, sabit süre verme.
    try:
        sf.wait_for_function(
            "() => !document.body.innerText.includes('Çelişkiler getiriliyor')",
            timeout=90000)
    except Exception:
        pass
    sf.wait_for_timeout(2500)
    kaydir(sf, 420, 1500)
    sf.wait_for_timeout(4000)
    b.close()


SAHNELER = {
    "pano": klip_pano, "cetvel": klip_cetvel, "kanit": klip_kanit,
    "sohbet": klip_sohbet, "celiski": klip_celiski,
}

if __name__ == "__main__":
    istenen = sys.argv[1:] or list(SAHNELER)
    if CIK.exists() and not sys.argv[1:]:
        shutil.rmtree(CIK)
    with sync_playwright() as p:
        tar = p.chromium.launch(args=["--force-color-profile=srgb", "--hide-scrollbars"])
        for ad in istenen:
            print(f"çekiliyor: {ad}", flush=True)
            try:
                SAHNELER[ad](tar)
            except Exception as exc:            # noqa: BLE001
                print(f"  ✗ {ad}: {exc}", flush=True)
        tar.close()
    for d in sorted(CIK.iterdir()):
        for v in d.glob("*.webm"):
            print(f"{d.name:9s} {v.stat().st_size // 1024:6d} KB  {v.name}")
