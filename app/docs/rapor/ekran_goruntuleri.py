#!/usr/bin/env python3
"""Rapor için gerçek ekran görüntülerini üretir (Playwright, offline).

Neden betik: MCP tarayıcı aracı çıktıyı erişilebilir bir yola yazmıyordu ve
etkileşim sırası (sekme → örnek seç → çıkar → bekle) elle tekrarlanabilir
olmalı. Bu dosya raporun görsellerini yeniden üretmenin tek yoludur.

Ön koşul — iki sunucu ayakta olmalı:

    cd app
    DATABASE_PATH=data/demo.db DATABASE_URL= LLM_BACKEND= RAG_RETRIEVER=keyword \
      ./.venv/bin/python -m uvicorn src.api.main:app --port 8000

    cd app/web
    NEXT_PUBLIC_API_URL=http://127.0.0.1:8000 npm run dev

Çalıştırma:

    cd app && ./.venv/bin/python docs/rapor/ekran_goruntuleri.py

Yeni bağımlılık yok: `playwright` zaten requirements.txt içinde (Apache-2.0).
"""

from __future__ import annotations

import sys
from pathlib import Path

from playwright.sync_api import Page, sync_playwright

WEB = "http://127.0.0.1:3000/"
API = "http://127.0.0.1:8000"
OUT = Path(__file__).resolve().parent / "gorseller"

# Audit paneli için 10 alan + 10 doğrulanmış offset taşıyan belge.
# `SELECT c.id, COUNT(f.id) ... ORDER BY 2 DESC` ile seçildi.
AUDIT_CAMPAIGN_ID = 284

VIEWPORT = {"width": 1440, "height": 1000}


def shot(page: Page, name: str, *, full: bool = True) -> None:
    path = OUT / name
    page.screenshot(path=str(path), full_page=full)
    size_kb = path.stat().st_size // 1024
    print(f"  ✓ {name}  ({size_kb} KB)")


def tab(page: Page, label: str) -> None:
    """Sekme değiştir ve React'ın yeniden çizmesini bekle."""
    page.get_by_role("tab", name=label).click()
    page.wait_for_timeout(900)


def settle(page: Page, text: str | None = None, timeout: int = 25_000) -> None:
    """Ağ boşalmasını, istenirse belirli bir metnin gelmesini bekle."""
    if text:
        page.get_by_text(text, exact=False).first.wait_for(timeout=timeout)
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(600)


def ask(page: Page, question: str, name: str) -> None:
    """Chatbot'a soru yaz, cevabı bekle, görüntüle.

    Chatbot görüntüleri GÖRÜNTÜ ALANIYLA sınırlı alınır (`full=False`):
    kaynak tablosu 47 satıra kadar uzayabiliyor ve tam sayfa görüntü
    raporda 215 mm'ye sıkışınca metin okunamaz hale geliyordu. Anlamlı
    içerik (soru + cevap + kapı notları) zaten en üstte.
    """
    box = page.get_by_label("Chatbot sorusu")
    box.fill("")
    box.fill(question)
    page.get_by_role("button", name="Sor").click()
    # "Sor" butonu cevap gelene kadar "…" olur; eski hâline dönmesini bekle.
    page.get_by_role("button", name="Sor").wait_for(timeout=30_000)
    page.wait_for_timeout(1_200)
    shot(page, name, full=False)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        ctx = browser.new_context(
            viewport=VIEWPORT,
            device_scale_factor=2,  # rapor baskısı için 2x yoğunluk
            locale="tr-TR",
        )
        page = ctx.new_page()

        print("→ Arayüz açılıyor")
        page.goto(WEB, wait_until="networkidle")
        settle(page, "Karşılaştırma")

        # ---- 1) Karşılaştırma + skorlama şeffaflığı -----------------------
        print("→ 01/02 Karşılaştırma")
        settle(page, "Kaynağı gör")
        shot(page, "01-karsilastirma.png")

        # İlk satırın kaynak çekmecesini aç: span + güven + katman görünür olsun.
        page.get_by_role("button", name="Kaynağı gör").first.click()
        page.wait_for_timeout(700)
        shot(page, "02-karsilastirma-kaynak-span.png")

        # ---- 2) Jüri audit paneli ---------------------------------------
        print("→ 03 Jüri audit paneli")
        tab(page, "Jüri Audit Paneli")
        page.locator("select.select").first.select_option(str(AUDIT_CAMPAIGN_ID))
        settle(page, "Kaynak span")
        # Offset butonuna bas → metinde ilgili span vurgulanır.
        page.locator("button.btn-link.mono").first.click()
        page.wait_for_timeout(800)
        shot(page, "03-audit-span-vurgulama.png")

        # ---- 3) Çelişki tespiti (korpus geneli) -------------------------
        print("→ 04 Çelişki tespiti")
        tab(page, "Çelişki Tespiti")
        settle(page)
        shot(page, "04-celiski-korpus.png")

        # ---- 4) Zor vaka tezgâhı: model çıktısı ↔ altın küme -------------
        # Ekran artık elle yazılmış örnek metinlerle değil, altın kümenin ZOR
        # işaretli belgeleriyle çalışıyor: zorluk çipiyle süz, ilk vakayı seç,
        # çıkarımı koştur. Vaka kartları `button.zv-vaka`; ada göre seçmek
        # kırılgan olurdu çünkü kart başlığı korpustan gelir ve korpus
        # tazelendiğinde değişebilir.
        print("→ 05/06 Zor vaka tezgâhı")
        tab(page, "Canlı Çıkarım")
        settle(page, "Zor Vaka Tezgâhı")

        # Dosya adları KORUNUYOR: rapor ve sunum taslağı bu adlarla bağ
        # kuruyor, yeniden adlandırmak o bağları sessizce koparırdı.
        for isim, dosya in (
            ("Koşullu / aralıklı", "05-canli-cikarim-zor-vaka.png"),
            ("Çelişkili metin", "06-canli-cikarim-celiski.png"),
        ):
            # Çip şeridiyle sınırlı seçim: aynı metin vaka kartlarının
            # içindeki etiket rozetlerinde de geçiyor ve rol bazlı arama
            # kartları da yakalardı.
            page.locator("button.chip").filter(has_text=isim).first.click()
            page.wait_for_timeout(400)
            page.locator("button.zv-vaka").first.click()
            page.wait_for_timeout(400)
            page.get_by_role("button", name="Çıkarımı çalıştır").click()
            page.wait_for_timeout(2_500)
            page.wait_for_load_state("networkidle")
            shot(page, dosya)

        # ---- 5) Chatbot: iki yol + iki güvenlik kapısı ------------------
        print("→ 07-10 Chatbot ve güvenlik kapıları")
        tab(page, "Chatbot")
        settle(page)

        # 07: yapısal sorgu yolu (text-to-SQL)
        page.get_by_role(
            "button", name="Hangi bankada en düşük kâr payı oranı var?"
        ).click()
        page.get_by_role("button", name="Sor").wait_for(timeout=30_000)
        page.wait_for_timeout(1_200)
        shot(page, "07-chatbot-yapisal-sorgu.png", full=False)

        # 08: RAG yolu (koşul/açıklama)
        page.get_by_role(
            "button", name="Konut finansmanı kampanyasının koşulları neler?"
        ).click()
        page.get_by_role("button", name="Sor").wait_for(timeout=30_000)
        page.wait_for_timeout(1_200)
        shot(page, "08-chatbot-rag.png", full=False)

        # 09: KAPI 1 — çıktıda konvansiyonel terim üretilmez
        ask(page, "Faiz oranı en düşük hangi bankada?", "09-guvenlik-kapi1-terminoloji.png")

        # 10: KAPI 2 — fıkhî hüküm verilmez, TKBB'ye yönlendirir
        ask(page, "Konut finansmanı caiz mi, helal mi?", "10-guvenlik-kapi2-fikhi-hukum.png")

        # 11: KAPI 3 — yatırım tavsiyesi verilmez
        ask(page, "Hangi bankayı seçmeliyim, tavsiye eder misin?", "11-guvenlik-kapi3-tavsiye.png")

        ctx.close()
        browser.close()

    print(f"\nTamamlandı → {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
