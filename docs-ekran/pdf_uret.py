"""`manifest.json` + `ss/*.png` → tek PDF (her sayfada bir ekran + altında açıklama).

Neden HTML üzerinden: PDF, Chromium'un yazdırma motoruyla üretiliyor. Türkçe
diyakritikler, `@page` sayfa kırılımları ve resim ölçekleme böylece tarayıcıda
gördüğümüz haliyle kâğıda düşüyor; ayrıca yeni bir bağımlılık gerekmiyor —
Playwright zaten depoda kurulu.

Resim `base64` ile HTML'e gömülür: `file://` üzerinden yüklenen resimler
yazdırma anında bazen henüz hazır olmuyor ve boş sayfa basılıyordu.

Kullanım:
    python docs-ekran/pdf_uret.py
"""
from __future__ import annotations

import base64
import json
import pathlib
import sys
from html import escape

from playwright.sync_api import sync_playwright

KOK = pathlib.Path(__file__).resolve().parent
MANIFEST = KOK / "manifest.json"
SS = KOK / "ss"
CIKTI = KOK / "anatolia-ai-panel-ekranlari.pdf"

BASLIK = "Anatolia AI — Panel Ekranları ve Özellikleri"
ALT_BASLIK = (
    "TEKNOFEST 2026 · Türkçe Yapay Zekâ Dil Ajanları Yarışması — 2. Senaryo · "
    "Katılım Bankacılığı Kampanya Bilgi Çıkarımı"
)
TARIH = "12 Ağustos 2026"

CSS = """
@page { size: A4 portrait; margin: 14mm 14mm 16mm 14mm; }
* { box-sizing: border-box; }
body {
  margin: 0;
  font-family: -apple-system, "Helvetica Neue", Arial, sans-serif;
  color: #17202a;
  font-size: 10.5pt;
  line-height: 1.5;
  -webkit-print-color-adjust: exact;
  print-color-adjust: exact;
}
.kapak { height: 258mm; display: flex; flex-direction: column; justify-content: center; }
.kapak h1 { font-size: 26pt; line-height: 1.15; margin: 0 0 6mm; letter-spacing: -0.01em; }
.kapak .alt { font-size: 11.5pt; color: #46536b; margin: 0 0 10mm; max-width: 150mm; }
.kapak .cizgi { height: 3px; width: 34mm; background: #0b6bcb; margin: 0 0 10mm; }
.kapak dl { margin: 0; display: grid; grid-template-columns: 42mm 1fr; row-gap: 2.4mm; font-size: 10pt; }
.kapak dt { color: #6b7688; }
.kapak dd { margin: 0; }
.kapak .not {
  margin-top: 12mm; padding: 4mm 5mm; border-left: 3px solid #0b6bcb;
  background: #f3f7fc; font-size: 9.5pt; color: #33405a; max-width: 150mm;
}
.icindekiler { page-break-before: always; }
.icindekiler h2 { font-size: 15pt; margin: 0 0 6mm; }
.icindekiler ol { margin: 0; padding-left: 7mm; font-size: 9.8pt; line-height: 1.65; }
.icindekiler li { margin-bottom: 0.8mm; }
section.kare { page-break-before: always; }
section.kare > .ust { display: flex; align-items: baseline; gap: 3mm; margin-bottom: 3.5mm; }
section.kare .no {
  flex: 0 0 auto; font-size: 9pt; font-weight: 700; color: #0b6bcb;
  border: 1.5px solid #0b6bcb; border-radius: 999px; padding: 0.6mm 2.6mm;
}
section.kare h2 { font-size: 13.5pt; margin: 0; line-height: 1.25; }
figure { margin: 0; }
figure .cerceve {
  border: 1px solid #dfe4ec; border-radius: 4px; background: #fff;
  padding: 2mm; text-align: center; overflow: hidden;
}
/* 182mm: başlık (~11mm) + açıklama (~45mm) çıkarıldıktan sonra kalan yer.
   Daha küçük bir üst sınır, uzun ekranlarda metni okunmaz hale getiriyordu. */
figure img { max-width: 100%; max-height: 182mm; object-fit: contain; display: inline-block; }
figcaption {
  margin-top: 4mm; font-size: 9.6pt; line-height: 1.55; color: #26313f;
  text-align: justify; hyphens: auto;
}
figcaption .etiket {
  display: block; font-size: 8pt; letter-spacing: 0.09em; text-transform: uppercase;
  color: #7b8598; margin-bottom: 1.6mm;
}
"""


def veri_uri(yol: pathlib.Path) -> str:
    return "data:image/png;base64," + base64.b64encode(yol.read_bytes()).decode("ascii")


def html_uret(kayitlar: list[dict[str, str]]) -> str:
    parcalar: list[str] = [
        "<style>", CSS, "</style>",
        '<div class="kapak">',
        '<div class="cizgi"></div>',
        f"<h1>{escape(BASLIK)}</h1>",
        f'<p class="alt">{escape(ALT_BASLIK)}</p>',
        "<dl>",
        f"<dt>Tarih</dt><dd>{escape(TARIH)}</dd>",
        f"<dt>Ekran sayısı</dt><dd>{len(kayitlar)}</dd>",
        "<dt>Takım</dt><dd>Anatolia AI</dd>",
        "<dt>Arayüz</dt><dd>Next.js 14 · 11 sekme + sohbet çekmecesi + komut paleti</dd>",
        "<dt>API</dt><dd>FastAPI · yerel, anahtarsız</dd>",
        "<dt>Veri tabanı</dt><dd>SQLite (data/demo.db) · 1.774 belge · 10 banka · 11 kaynak</dd>",
        "<dt>Yerel LLM</dt><dd>Ollama · qwen2.5:7b-instruct (anahtarsız, çevrimdışı)</dd>",
        "</dl>",
        '<p class="not">Bu belgedeki her görüntü, sistem yerel makinede ayağa '
        "kaldırılıp arayüz baştan sona gezilerek canlı olarak alınmıştır; hiçbir "
        "kare elle düzenlenmemiş ya da kurgulanmamıştır. Resmin altındaki metin o "
        "ekranın ne olduğunu ve neden öyle tasarlandığını anlatır.</p>",
        "</div>",
        '<div class="icindekiler"><h2>İçindekiler</h2><ol>',
    ]
    for k in kayitlar:
        parcalar.append(f"<li>{escape(k['baslik'])}</li>")
    parcalar.append("</ol></div>")

    for i, k in enumerate(kayitlar, start=1):
        gorsel = SS / k["dosya"]
        if not gorsel.exists():
            print(f"  ! eksik görüntü, atlandı: {k['dosya']}", file=sys.stderr)
            continue
        parcalar.append(
            f'<section class="kare"><div class="ust"><span class="no">{i:02d}</span>'
            f"<h2>{escape(k['baslik'])}</h2></div>"
            f'<figure><div class="cerceve">'
            f'<img src="{veri_uri(gorsel)}" alt="{escape(k["baslik"])}"></div>'
            f'<figcaption><span class="etiket">Bu ekran ne işe yarar</span>'
            f"{escape(k['aciklama'])}</figcaption></figure></section>"
        )
    return "".join(parcalar)


def main() -> int:
    kayitlar = json.loads(MANIFEST.read_text(encoding="utf-8"))
    html = html_uret(kayitlar)
    gecici = KOK / "_pdf_kaynak.html"
    gecici.write_text(html, encoding="utf-8")

    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page()
        pg.goto(gecici.as_uri(), wait_until="load")
        pg.wait_for_timeout(1500)
        pg.pdf(path=str(CIKTI), format="A4", print_background=True,
               margin={"top": "14mm", "bottom": "16mm", "left": "14mm", "right": "14mm"})
        b.close()

    gecici.unlink()
    mb = CIKTI.stat().st_size / 1_048_576
    print(f"PDF üretildi: {CIKTI}  ({len(kayitlar)} ekran, {mb:.1f} MB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
