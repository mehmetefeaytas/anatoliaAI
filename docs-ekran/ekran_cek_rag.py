"""Yalnız RAG karesini alır: sıfırdan sohbette bir koşul/açıklama sorusu.

Bağlam devralması RAG yolunu gölgeliyordu — önceki turun alanı miras alınınca
router soruyu yapısal yola gönderiyor. Bu yüzden sohbet gerçekten sıfırlanıyor
(«Yeni sohbet» + onay) ve koşul sorusu ilk tur olarak soruluyor.
"""
from __future__ import annotations

import pathlib

from playwright.sync_api import sync_playwright

CIKTI = pathlib.Path("/Users/mehmetefeaytas/anatoliaaI/docs-ekran/ss")

with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width": 1600, "height": 1000},
                    device_scale_factor=2, locale="tr-TR")
    pg.set_default_timeout(20_000)
    pg.goto("http://localhost:3010", wait_until="networkidle")
    pg.wait_for_timeout(4000)
    pg.get_by_role("button", name="Jüri modu: kapalı").click()
    pg.wait_for_timeout(2000)
    pg.get_by_role("tab", name="Chatbot", exact=True).click()
    pg.wait_for_timeout(2500)

    # Hazır soru düğmesi soruyu kendisi gönderir.
    pg.get_by_role("button", name="Konut finansmanı kampanyasının koşulları neler?").click()
    pg.wait_for_timeout(2000)
    try:
        pg.get_by_role("button", name="Sor", exact=True).click(timeout=3000)
    except Exception:
        pass
    pg.wait_for_timeout(60000)

    govde = pg.inner_text("main")
    print("  RAG rozeti:", "RAG" in govde)
    print("  yapısal rozeti:", "text-to-SQL" in govde)

    loc = pg.locator("h2:has-text('Chatbot')").first
    y = int(loc.evaluate("el => el.getBoundingClientRect().top + window.scrollY")) - 28
    pg.screenshot(path=str(CIKTI / "35b-chatbot-rag.png"), full_page=True,
                  clip={"x": 0, "y": max(0, y), "width": 1600, "height": 1400})
    print("  ✓ 35b-chatbot-rag.png")
    b.close()
