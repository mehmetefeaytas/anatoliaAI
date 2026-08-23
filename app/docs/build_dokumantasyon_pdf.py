#!/usr/bin/env python3
"""`PROJE-DOKUMANTASYONU.md` dosyasını PDF'e basar.

Markdown ayrıştırıcı ve baskı CSS'i `rapor/build_pdf.py`'den yeniden kullanılır;
bu betik yalnız kendi kapağını, içindekiler bloğunu ve sayfa altlığını verir.
Yeni bağımlılık eklemez — Chromium'a Playwright üzerinden basar.

Çalıştırma:
    cd app && ./.venv/bin/python docs/build_dokumantasyon_pdf.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "rapor"))

from build_pdf import CSS, render, slug

SRC = HERE / "PROJE-DOKUMANTASYONU.md"
OUT_HTML = HERE / "PROJE-DOKUMANTASYONU.html"
OUT_PDF = HERE / "PROJE-DOKUMANTASYONU.pdf"

TARIH = "22 Ağustos 2026"

# Kapak sayfası kapaktan sonra başlasın; ayrıca içindekiler tablosunun
# kaynak markdown'daki hâli PDF'te tekrar olduğu için gizlenir.
EK_CSS = """
.cover h1 { font-size: 27pt; }
.kunye { page-break-after: always; }
.kunye h2 { border: 0; margin-top: 0; }
h2 { page-break-before: auto; }

/* Uzun URL ve JSON satirlari baskida kirpilmasin: yatay kaydirma kagitta yok. */
pre { white-space: pre-wrap; overflow-wrap: anywhere; }
td, th { overflow-wrap: anywhere; }
"""


def anchorlari_duzelt(md: str) -> str:
    """Markdown içi `](#turkce-baslik)` bağlantılarını slug biçimine çevirir.

    Kaynak dosya GitHub'da okunabilir olsun diye Türkçe harfli çapa kullanıyor;
    `build_pdf.slug()` ise harfleri sadeleştiriyor. İkisi eşleşmezse PDF'teki
    bağlantılar ölü kalır.
    """
    return re.sub(r"\]\(#([^)]+)\)", lambda m: f"](#{slug(m.group(1))})", md)


def build_html(md: str) -> str:
    body, toc = render(anchorlari_duzelt(md))

    # Gövdenin başındaki kapak bloğunu (ilk h1 + künye paragrafı + eşleme
    # tablosu) at; yerine aşağıdaki kapak ve üretilmiş içindekiler geçer.
    kesim = body.find('<h2 id="1-sistem-mimarisi-ve-veri-akisi"')
    if kesim > 0:
        body = body[kesim:]

    toc_items = "".join(
        f'<li class="l{min(lvl, 2)}"><a href="#{anchor}">{text}</a></li>'
        for lvl, text, anchor in toc
        if lvl <= 2 and not text.startswith("Anatolia AI —")
    )

    kapak = f"""
<section class="cover">
  <div class="eyebrow">TEKNOFEST 2026 · Türkçe Yapay Zekâ Dil Ajanları Yarışması · 2. Senaryo</div>
  <h1 style="border:0">Anatolia AI<br>Proje Dokümantasyonu</h1>
  <div class="rule"></div>
  <div class="sub">Katılım bankacılığı kampanya metinlerinden finansal bilgi çıkarımı,
  bankalar arası karşılaştırma ve doğal dil arayüzü. Şartnamenin on dokümantasyon
  kalemi, ölçülmüş sayılar ve açık eksiklerle.</div>
  <table style="margin-top:12mm">
    <tr><td>Takım</td><td><strong>Anatolia AI</strong></td></tr>
    <tr><td>Ekip</td><td>Mehmet Efe Aytaş (kaptan) · Irmak Altay · Ayça Engindeniz · Ecegüneş Dağ</td></tr>
    <tr><td>Belge tarihi</td><td>{TARIH}</td></tr>
    <tr><td>Korpus</td><td>2.708 belge · 11 kaynak · 7.022 çıkarılmış alan</td></tr>
    <tr><td>Kod durumu</td><td>3.552 test yeşil · 0 başarısız · commit <code>03822c24</code></td></tr>
    <tr><td>Ölçüm</td><td>yapılandırılmış mikro-F1 0,823 · halüsinasyon 0,034</td></tr>
    <tr><td>Lisans</td><td>Apache-2.0</td></tr>
  </table>
  <div class="foot">Her sayı bir komut çıktısına ya da artefakt dosyasına referans verir.
  Ölçülmemiş kalemler <strong>Bölüm 10</strong>'un sonunda ayrı listede toplanır.</div>
</section>

<section class="toc">
  <h2>İçindekiler</h2>
  <ol>{toc_items}</ol>
</section>
"""

    return f"""<!doctype html>
<html lang="tr"><head><meta charset="utf-8">
<title>Anatolia AI — Proje Dokümantasyonu</title>
<style>{CSS}{EK_CSS}</style>
</head><body>{kapak}{body}</body></html>"""


def main() -> int:
    if not SRC.exists():
        print(f"HATA: {SRC} bulunamadı")
        return 1

    html_text = build_html(SRC.read_text(encoding="utf-8"))
    OUT_HTML.write_text(html_text, encoding="utf-8")
    print(f"  ✓ HTML  {OUT_HTML.name}  ({len(html_text) // 1024} KB)")

    from playwright.sync_api import sync_playwright

    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page()
        page.goto(OUT_HTML.as_uri(), wait_until="load")
        page.wait_for_timeout(1200)
        page.pdf(
            path=str(OUT_PDF),
            format="A4",
            print_background=True,
            display_header_footer=True,
            header_template='<div style="font:7pt -apple-system;color:#9aa0aa;width:100%;'
            f'padding:0 15mm;text-align:right">Anatolia AI — Proje Dokümantasyonu · {TARIH}</div>',
            footer_template='<div style="font:7.5pt -apple-system;color:#6b7280;width:100%;'
            'padding:0 15mm;display:flex;justify-content:space-between">'
            "<span>TEKNOFEST 2026 TYDA · 2. Senaryo</span>"
            '<span><span class="pageNumber"></span> / <span class="totalPages"></span></span></div>',
            margin={"top": "17mm", "bottom": "18mm", "left": "15mm", "right": "15mm"},
        )
        browser.close()

    kb = OUT_PDF.stat().st_size / 1024
    print(f"  ✓ PDF   {OUT_PDF.name}  ({kb:.0f} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
