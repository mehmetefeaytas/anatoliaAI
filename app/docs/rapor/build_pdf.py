#!/usr/bin/env python3
"""Raporu markdown'dan PDF'e basar (Playwright/Chromium, bağımlılık eklemeden).

Neden elle markdown ayrıştırıcı: sistemde pandoc/weasyprint/markdown yok ve
kurmak §5.10 lisans denetimini yeniden açardı. Burada yalnızca raporun
kullandığı markdown alt kümesi destekleniyor — genel amaçlı bir ayrıştırıcı
değil, bilinçli olarak dar.

Desteklenen: başlıklar, GFM tabloları, çitli kod blokları, sıralı/sırasız
listeler, alıntı blokları, yatay çizgi, resim, bağlantı, satır içi kod,
kalın/italik.

Çalıştırma:
    cd app && ./.venv/bin/python docs/rapor/build_pdf.py
"""

from __future__ import annotations

import html
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = HERE / "anatolia-ai-teknik-rapor.md"
OUT_HTML = HERE / "anatolia-ai-teknik-rapor.html"
OUT_PDF = HERE / "anatolia-ai-teknik-rapor.pdf"


# ---------------------------------------------------------------------------
# Satır içi biçimlendirme
# ---------------------------------------------------------------------------
def inline(text: str) -> str:
    """Satır içi markdown → HTML. Kod parçaları önce korunur."""
    spans: list[str] = []

    def stash(m: re.Match[str]) -> str:
        spans.append(f"<code>{html.escape(m.group(1))}</code>")
        return f"\x00{len(spans) - 1}\x00"

    text = re.sub(r"`([^`]+)`", stash, text)
    text = html.escape(text)

    # resim önce (bağlantı deseniyle çakışmasın)
    text = re.sub(r"!\[([^\]]*)\]\(([^)]+)\)", r'<img src="\2" alt="\1">', text)
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<![\w*])\*([^*\n]+)\*(?![\w*])", r"<em>\1</em>", text)

    return re.sub(r"\x00(\d+)\x00", lambda m: spans[int(m.group(1))], text)


def slug(text: str) -> str:
    tr = str.maketrans("çğıöşüÇĞİÖŞÜ", "cgiosuCGIOSU")
    s = re.sub(r"<[^>]+>", "", text).translate(tr).lower()
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")[:60]


# ---------------------------------------------------------------------------
# Blok ayrıştırıcı
# ---------------------------------------------------------------------------
def render(md: str) -> tuple[str, list[tuple[int, str, str]]]:
    """Markdown → (HTML gövdesi, içindekiler girdileri)."""
    lines = md.split("\n")
    out: list[str] = []
    toc: list[tuple[int, str, str]] = []
    i = 0
    h1_seen = 0

    def close_list(stack: list[str]) -> None:
        while stack:
            out.append(f"</{stack.pop()}>")

    list_stack: list[str] = []

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # --- çitli kod bloğu ---
        if stripped.startswith("```"):
            close_list(list_stack)
            lang = stripped[3:].strip()
            i += 1
            buf: list[str] = []
            while i < len(lines) and not lines[i].strip().startswith("```"):
                buf.append(lines[i])
                i += 1
            i += 1
            cls = f' class="lang-{html.escape(lang)}"' if lang else ""
            out.append(f"<pre{cls}><code>{html.escape(chr(10).join(buf))}</code></pre>")
            continue

        # --- boş satır ---
        if not stripped:
            close_list(list_stack)
            i += 1
            continue

        # --- yatay çizgi ---
        if re.fullmatch(r"-{3,}|\*{3,}", stripped):
            close_list(list_stack)
            out.append("<hr>")
            i += 1
            continue

        # --- başlık ---
        m = re.match(r"^(#{1,5})\s+(.*)$", stripped)
        if m:
            close_list(list_stack)
            level = len(m.group(1))
            body = inline(m.group(2))
            anchor = slug(m.group(2))
            if level == 1:
                h1_seen += 1
                # İlk H1 kapak sayfasıdır; sonrakiler yeni sayfada başlar.
                cls = ' class="page-break"' if h1_seen > 1 else ""
                out.append(f'<h1 id="{anchor}"{cls}>{body}</h1>')
            else:
                out.append(f'<h{level} id="{anchor}">{body}</h{level}>')
            if level <= 2:
                toc.append((level, body, anchor))
            i += 1
            continue

        # --- alıntı bloğu ---
        if stripped.startswith(">"):
            close_list(list_stack)
            buf = []
            while i < len(lines) and lines[i].strip().startswith(">"):
                buf.append(lines[i].strip().lstrip(">").strip())
                i += 1
            out.append(f"<blockquote>{inline(' '.join(buf))}</blockquote>")
            continue

        # --- tablo (GFM) ---
        if stripped.startswith("|") and i + 1 < len(lines) and re.fullmatch(
            r"\|[\s:|-]+\|?", lines[i + 1].strip()
        ):
            close_list(list_stack)

            def cells(row: str) -> list[str]:
                # GFM'de `\|` hücre içinde LİTERAL boru işaretidir, sütun
                # ayracı değil. Kaçamağı korumadan bölmek fazla kolon üretiyordu.
                protected = row.replace(r"\|", "\x01")
                return [
                    c.strip().replace("\x01", "|")
                    for c in protected.strip().strip("|").split("|")
                ]

            head = cells(lines[i])
            aligns = []
            for spec in cells(lines[i + 1]):
                if spec.startswith(":") and spec.endswith(":"):
                    aligns.append("center")
                elif spec.endswith(":"):
                    aligns.append("right")
                else:
                    aligns.append("left")
            i += 2
            body_rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                body_rows.append(cells(lines[i]))
                i += 1

            th = "".join(
                f'<th style="text-align:{aligns[j] if j < len(aligns) else "left"}">{inline(c)}</th>'
                for j, c in enumerate(head)
            )
            trs = []
            for row in body_rows:
                tds = "".join(
                    f'<td style="text-align:{aligns[j] if j < len(aligns) else "left"}">{inline(c)}</td>'
                    for j, c in enumerate(row)
                )
                trs.append(f"<tr>{tds}</tr>")
            out.append(
                f'<div class="table-wrap"><table><thead><tr>{th}</tr></thead>'
                f"<tbody>{''.join(trs)}</tbody></table></div>"
            )
            continue

        # --- listeler ---
        m = re.match(r"^(\s*)([-*+]|\d+\.)\s+(.*)$", line)
        if m:
            indent, marker, content = len(m.group(1)), m.group(2), m.group(3)
            tag = "ol" if marker[0].isdigit() else "ul"
            depth = indent // 2 + 1

            # Çok satırlı öğe: devam satırları (marker'sız, blok başlatmayan)
            # aynı <li> içine katlanır. Aksi halde metin listenin dışına
            # taşıyor ve madde ortadan kopuyordu.
            i += 1
            while i < len(lines):
                nxt = lines[i]
                if not nxt.strip():
                    break
                if re.match(r"^\s*([-*+]|\d+\.)\s", nxt):
                    break
                if re.match(r"^\s*(#{1,5}\s|\||>|```|---)", nxt):
                    break
                content += " " + nxt.strip()
                i += 1
            i -= 1  # aşağıdaki i += 1 ile dengelenir

            while len(list_stack) > depth:
                out.append(f"</{list_stack.pop()}>")
            if len(list_stack) < depth:
                out.append(f"<{tag}>")
                list_stack.append(tag)
            elif list_stack[-1] != tag:
                out.append(f"</{list_stack.pop()}>")
                out.append(f"<{tag}>")
                list_stack.append(tag)
            out.append(f"<li>{inline(content)}</li>")
            i += 1
            continue

        # --- tek başına resim → şekil olarak sarılır ---
        m = re.fullmatch(r"!\[([^\]]*)\]\(([^)]+)\)", stripped)
        if m:
            close_list(list_stack)
            alt = html.escape(m.group(1))
            out.append(
                f'<figure><img src="{html.escape(m.group(2))}" alt="{alt}">'
                f"<figcaption>{alt}</figcaption></figure>"
            )
            i += 1
            continue

        # --- paragraf ---
        close_list(list_stack)
        buf = [stripped]
        i += 1
        while i < len(lines):
            nxt = lines[i].strip()
            if not nxt or re.match(r"^(#{1,5}\s|[-*+]\s|\d+\.\s|\||>|```|---)", nxt):
                break
            buf.append(nxt)
            i += 1
        out.append(f"<p>{inline(' '.join(buf))}</p>")

    close_list(list_stack)
    return "\n".join(out), toc


# ---------------------------------------------------------------------------
# Baskı stili
# ---------------------------------------------------------------------------
CSS = """
@page { size: A4; margin: 17mm 15mm 18mm 15mm; }

:root {
  --ink: #1a1d23; --muted: #5b6270; --line: #d8dce3; --surf: #f7f8fa;
  --teal: #0f766e; --blue: #1d4ed8; --warn: #b45309; --danger: #b91c1c; --ok: #15803d;
}

* { box-sizing: border-box; }

body {
  font: 10.2pt/1.55 -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
  color: var(--ink); margin: 0; -webkit-print-color-adjust: exact; print-color-adjust: exact;
}

/* --- kapak --- */
.cover {
  height: 250mm; display: flex; flex-direction: column; justify-content: center;
  page-break-after: always;   /* içindekiler kapağa taşmasın */
}
.cover .eyebrow { font-size: 9.5pt; letter-spacing: .13em; text-transform: uppercase; color: var(--teal); font-weight: 700; }
.cover h1 { font-size: 31pt; line-height: 1.12; margin: 10mm 0 5mm; border: 0; padding: 0; }
.cover .sub { font-size: 12.5pt; color: var(--muted); max-width: 145mm; line-height: 1.5; }
.cover .rule { height: 3px; width: 46mm; background: var(--teal); margin: 9mm 0; }
.cover table { width: auto; font-size: 10pt; }
.cover table td { border: 0; padding: 2.1mm 9mm 2.1mm 0; }
.cover table td:first-child { color: var(--muted); white-space: nowrap; }
.cover .foot { margin-top: auto; font-size: 9pt; color: var(--muted); border-top: 1px solid var(--line); padding-top: 4mm; }

/* --- içindekiler --- */
.toc { page-break-after: always; }
.toc h2 { border: 0; margin-top: 0; }
.toc ol { list-style: none; padding: 0; margin: 0; counter-reset: t; }
.toc li { padding: 1.5mm 0; border-bottom: 1px dotted var(--line); font-size: 10.2pt; }
.toc li.l1 { font-weight: 700; margin-top: 3.5mm; border-bottom: 1px solid var(--line); }
.toc li.l2 { padding-left: 7mm; color: #333; }
.toc a { color: inherit; text-decoration: none; }

/* --- başlıklar --- */
h1 {
  font-size: 19pt; line-height: 1.2; margin: 0 0 6mm;
  padding-bottom: 3mm; border-bottom: 2.5px solid var(--teal);
}
h1.page-break { page-break-before: always; padding-top: 0; }
h2 {
  font-size: 14pt; margin: 8mm 0 3.5mm; padding-bottom: 1.6mm;
  border-bottom: 1px solid var(--line); page-break-after: avoid;
}
h3 { font-size: 11.6pt; margin: 6mm 0 2.4mm; color: #23262e; page-break-after: avoid; }
h4 { font-size: 10.4pt; margin: 4.5mm 0 2mm; color: var(--muted);
     text-transform: uppercase; letter-spacing: .05em; page-break-after: avoid; }

p { margin: 0 0 3.2mm; orphans: 3; widows: 3; }

/* --- tablolar --- */
.table-wrap { margin: 3.5mm 0 5mm; page-break-inside: avoid; }
table { width: 100%; border-collapse: collapse; font-size: 8.9pt; }
thead { background: var(--surf); }
th, td { border: 1px solid var(--line); padding: 1.9mm 2.4mm; vertical-align: top; }
th { font-weight: 700; font-size: 8.6pt; }
tbody tr:nth-child(even) { background: #fbfcfd; }
/* Uzun tablolar sayfayı aşarsa satır bütünlüğü korunur, başlık tekrar eder. */
table tr { page-break-inside: avoid; }
thead { display: table-header-group; }

/* --- kod --- */
code {
  font: 8.7pt ui-monospace, "SF Mono", Menlo, Consolas, monospace;
  background: #eef1f5; padding: .5mm 1.1mm; border-radius: 2px; color: #0b3b57;
}
pre {
  background: #1e2229; color: #e6e9ef; padding: 3.5mm 4mm; border-radius: 4px;
  font: 8.5pt/1.5 ui-monospace, "SF Mono", Menlo, Consolas, monospace;
  overflow-x: auto; page-break-inside: avoid; margin: 3mm 0 4.5mm;
}
pre code { background: none; color: inherit; padding: 0; font-size: inherit; }

/* --- görseller --- */
figure { margin: 4mm 0 6mm; page-break-inside: avoid; text-align: center; }
figure img { max-width: 100%; border: 1px solid var(--line); border-radius: 4px; }
figure figcaption { font-size: 8.4pt; color: var(--muted); margin-top: 1.8mm; font-style: italic; }
/* Ekran görüntüleri uzun; sayfa yüksekliğini aşmasınlar. */
figure img[src^="gorseller/"] { max-height: 215mm; object-fit: contain; }

/* --- listeler --- */
ul, ol { margin: 0 0 3.5mm; padding-left: 6.5mm; }
li { margin-bottom: 1.5mm; }

blockquote {
  margin: 3.5mm 0; padding: 2.8mm 4mm; background: #fff8ec;
  border-left: 3px solid var(--warn); font-size: 9.8pt; page-break-inside: avoid;
}

hr { border: 0; border-top: 1px solid var(--line); margin: 6mm 0; }
a { color: var(--blue); text-decoration: none; }
strong { font-weight: 700; }
"""


def build_html(md: str) -> str:
    body, toc = render(md)

    # İlk H1 bloğunu kapak olarak ayır: gövdedeki ilk <h1>…</h1> ve
    # sonrasındaki tablo kapağa taşınır.
    toc_items = "".join(
        f'<li class="l{lvl}"><a href="#{anchor}">{text}</a></li>'
        for lvl, text, anchor in toc
        if not text.startswith("Anatolia AI —")
    )

    cover = """
<section class="cover">
  <div class="eyebrow">TEKNOFEST 2026 · Türkçe Yapay Zekâ Dil Ajanları Yarışması · 2. Senaryo</div>
  <h1 style="border:0">Anatolia AI<br>Teknik Rapor ve Durum Değerlendirmesi</h1>
  <div class="rule"></div>
  <div class="sub">Katılım bankacılığı kampanya metinlerinden finansal bilgi çıkarımı,
  karşılaştırma ve doğal dil arayüzü — ölçülmüş kanıtlar ve açık eksiklerle.</div>
  <table style="margin-top:12mm">
    <tr><td>Takım</td><td><strong>Anatolia AI</strong></td></tr>
    <tr><td>Ekip</td><td>Mehmet Efe Aytaş (kaptan) · Irmak Altay · Ayça Engindeniz · Ecegüneş Dağ</td></tr>
    <tr><td>Rapor tarihi</td><td>3 Ağustos 2026</td></tr>
    <tr><td>Teslime kalan</td><td><strong>23 gün</strong> (26 Ağustos 2026)</td></tr>
    <tr><td>Kod durumu</td><td>890 test yeşil · ruff temiz · commit <code>03835ce</code></td></tr>
    <tr><td>Korpus</td><td>849 belge · 10 banka · 2.204 çıkarılmış alan</td></tr>
    <tr><td>Lisans</td><td>Apache-2.0</td></tr>
  </table>
  <div class="foot">Bölüm A–D şartname §6.3 teslimidir. <strong>Bölüm E iç ektir ve teslimde çıkarılır.</strong>
  Rapordaki her sayı bir komut çıktısına veya dosyaya referans verir; ölçülmemiş değerler ⏳ ile işaretlenmiştir.</div>
</section>

<section class="toc">
  <h2>İçindekiler</h2>
  <ol>%s</ol>
</section>
""" % toc_items

    # Kaynak markdown'ın kendi kapak bloğunu (ilk h1 + hemen ardındaki tablo) at.
    body = re.sub(
        r"^.*?(?=<h2 id=\"bu-raporun-okuma-kilavuzu\")", "", body, count=1, flags=re.S
    )

    return f"""<!doctype html>
<html lang="tr"><head><meta charset="utf-8">
<title>Anatolia AI — Teknik Rapor</title>
<style>{CSS}</style>
</head><body>{cover}{body}</body></html>"""


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
        page.wait_for_timeout(2500)  # SVG + PNG yüklenmesi
        page.pdf(
            path=str(OUT_PDF),
            format="A4",
            print_background=True,
            display_header_footer=True,
            header_template='<div style="font:7pt -apple-system;color:#9aa0aa;width:100%;'
            'padding:0 15mm;text-align:right">Anatolia AI — Teknik Rapor · 3 Ağustos 2026</div>',
            footer_template='<div style="font:7.5pt -apple-system;color:#6b7280;width:100%;'
            'padding:0 15mm;display:flex;justify-content:space-between">'
            "<span>TEKNOFEST 2026 TYDA · 2. Senaryo</span>"
            '<span><span class="pageNumber"></span> / <span class="totalPages"></span></span></div>',
            margin={"top": "17mm", "bottom": "18mm", "left": "15mm", "right": "15mm"},
        )
        browser.close()

    mb = OUT_PDF.stat().st_size / 1_048_576
    print(f"  ✓ PDF   {OUT_PDF.name}  ({mb:.1f} MB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
