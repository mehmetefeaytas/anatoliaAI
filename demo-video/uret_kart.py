"""Kart sahnelerini (HTML) 1920x1080 PNG'ye basar.

Kartlar video karesiyle BİREBİR aynı boyutta basılır. Küçük basıp sonradan
büyütmek metni bulanıklaştırırdı; kartların tek işi keskin metin göstermek.
"""

import asyncio
import pathlib
import sys

from playwright.async_api import async_playwright

KOK = pathlib.Path(__file__).parent
KART_DIZIN = KOK / "kart"
# Argüman verilirse yalnız o kartlar basılır (`uret_kart.py vizyon-60`).
KARTLAR = sys.argv[1:] or ["acilis", "mimari", "vizyon", "kapanis"]


async def main() -> None:
    async with async_playwright() as p:
        tarayici = await p.chromium.launch()
        sayfa = await tarayici.new_page(
            viewport={"width": 1920, "height": 1080}, device_scale_factor=1
        )
        for ad in KARTLAR:
            kaynak = (KART_DIZIN / f"{ad}.html").resolve()
            await sayfa.goto(kaynak.as_uri())
            # Yazı tipleri inmeden basılırsa kart yedek yazı tipiyle donar.
            await sayfa.wait_for_timeout(1200)
            await sayfa.screenshot(path=str(KART_DIZIN / f"{ad}.png"))
            print("basıldı:", ad)
        await tarayici.close()


asyncio.run(main())
