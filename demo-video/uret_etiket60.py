"""Bir dakikalık sürümün etiket şeritlerini şeffaf PNG olarak basar.

## Neden etiket

Beş dakikalık sürümde anlatım her ekranı tanıtmaya vakit buluyor. Altmış
saniyede on iki ekran geçerken izleyici "şimdi neye bakıyorum" sorusunu
sesten önce gözüyle yanıtlamak zorunda. Şerit bu boşluğu kapatıyor: sol altta
sabit bir yerde, sahne değişse de aynı yerde.

## Neden köşede kutu değil, alt bant

İlk tur sol alt köşede bir kutuydu ve tam da panelin içeriğini kapattı:
çıkarım sonucunun künye kartları, zor vaka tablosunun ilk satırları, banka
sayfasının bölüm başlığı. Şerit artık alt kenarda tam genişlikte duruyor ve
montaj panel görüntüsünü şeridin ÜSTÜNDE kalacak kadar küçültüyor — yani
hiçbir piksel örtülmüyor, videoya bir alt bant ekleniyor.

## Neden ffmpeg drawtext değil

drawtext'e Türkçe metin vermek font dosyası aramak demek ve tipografi
panelden kopuyor. Kartlarla aynı CSS'i kullanan bir HTML sayfasını şeffaf
zeminle basmak (`omit_background`) aynı görsel dili sürdürüyor; montaj bunu
sahnenin üstüne `overlay` ile koyuyor.

Şablon `str.replace` ile dolduruluyor, `format()` ile değil: şablonun içinde
CSS var ve her süslü parantezi kaçırmak gerekirdi.
"""

import asyncio
import json
import pathlib

from playwright.async_api import async_playwright

KOK = pathlib.Path(__file__).parent
SENARYO = json.loads((KOK / "senaryo-60.json").read_text(encoding="utf-8"))
ETIKET_DIZIN = KOK / "etiket-60"

SABLON = """<!doctype html>
<html lang="tr"><head><meta charset="utf-8">
<link rel="stylesheet" href="@CSS@">
<style>
  html, body { background: transparent; }
  body { display: block; }
  body::before { display: none; }
  /* Bant yüksekliği montajdaki pay ile birebir aynı olmak zorunda:
   * montaj panel görüntüsünü 994 piksele indirip üste yaslıyor, kalan 86
   * piksel bu bant. Biri değişirse öteki de değişmeli. */
  .serit {
    position: fixed;
    left: 0;
    right: 0;
    bottom: 0;
    height: 86px;
    background: #2b2f8f;
    color: #fff;
    display: flex;
    align-items: center;
    gap: 26px;
    padding: 0 64px;
  }
  .serit .kicker {
    font-family: "JetBrains Mono", ui-monospace, monospace;
    font-size: 20px;
    letter-spacing: .18em;
    color: #ffd9c2;
    padding-right: 26px;
    border-right: 2px solid rgba(255, 217, 194, .45);
    white-space: nowrap;
  }
  .serit .ad {
    font-size: 42px;
    font-weight: 700;
    letter-spacing: -0.02em;
    white-space: nowrap;
  }
</style></head>
<body><div class="serit">
  <div class="kicker">@KICKER@</div>
  <div class="ad">@ETIKET@</div>
</div></body></html>
"""


def sablonu_doldur(css: str, kicker: str, etiket: str) -> str:
    return (
        SABLON.replace("@CSS@", css)
        .replace("@KICKER@", kicker)
        .replace("@ETIKET@", etiket)
    )


async def main() -> None:
    ETIKET_DIZIN.mkdir(exist_ok=True)
    css = (KOK / "kart" / "ortak.css").resolve().as_uri()
    etiketli = [s for s in SENARYO["sahneler"] if s.get("etiket")]
    async with async_playwright() as p:
        tarayici = await p.chromium.launch()
        sayfa = await tarayici.new_page(
            viewport={"width": 1920, "height": 1080}, device_scale_factor=1
        )
        for sahne in etiketli:
            html = ETIKET_DIZIN / f"{sahne['id']}.html"
            html.write_text(
                sablonu_doldur(css, sahne.get("kicker", ""), sahne["etiket"]),
                encoding="utf-8",
            )
            await sayfa.goto(html.resolve().as_uri())
            # Yazı tipleri inmeden basılırsa şerit yedek yazı tipiyle donar.
            await sayfa.wait_for_timeout(900)
            await sayfa.screenshot(
                path=str(ETIKET_DIZIN / f"{sahne['id']}.png"), omit_background=True
            )
            print("basıldı:", sahne["id"])
        await tarayici.close()


asyncio.run(main())
