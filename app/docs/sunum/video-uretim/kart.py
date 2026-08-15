"""Video için başlık/bölüm kartları — 1920x1080 PNG.

Kartlar sunumla AYNI tasarım dilinden geliyor (pirinç vurgu, sistem sans,
mono etiketler) — video ile sunum arasında görsel kopukluk olmasın.
"""
from __future__ import annotations

import os
from pathlib import Path

from playwright.sync_api import sync_playwright

T = Path(os.environ["CLAUDE_JOB_DIR"]) / "tmp"
CIK = T / "kart"
CIK.mkdir(parents=True, exist_ok=True)

STIL = """
*{box-sizing:border-box;margin:0}
html,body{width:1920px;height:1080px;overflow:hidden}
body{background:#0A0E13;color:#EEF1F5;display:flex;flex-direction:column;
  justify-content:center;padding:0 150px;
  font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;
  -webkit-font-smoothing:antialiased}
.goz{font-family:ui-monospace,"SF Mono",Menlo,monospace;font-size:21px;
  letter-spacing:.34em;text-transform:uppercase;color:#C8A15A;margin-bottom:40px;
  display:flex;align-items:center;gap:22px}
.goz::after{content:"";flex:1;height:1px;background:rgba(200,161,90,.28);max-width:260px}
h1{font-size:104px;line-height:1.03;letter-spacing:-.038em;font-weight:600}
h2{font-size:72px;line-height:1.08;letter-spacing:-.028em;font-weight:600}
em{color:#EBD4A0;font-style:normal}
p.alt{font-size:34px;line-height:1.45;color:#8494A6;margin-top:34px;max-width:26ch}
.marka{font-family:ui-monospace,"SF Mono",Menlo,monospace;font-size:22px;
  letter-spacing:.42em;text-transform:uppercase;color:#C8A15A}
.dort{display:grid;grid-template-columns:1fr 1fr;gap:26px;margin-top:56px;max-width:1500px}
.söz{background:#121821;border:1px solid rgba(255,255,255,.07);border-radius:4px;
  padding:34px 38px}
.söz .b{font-family:ui-monospace,"SF Mono",Menlo,monospace;font-size:18px;
  letter-spacing:.16em;text-transform:uppercase;color:#C8A15A;margin-bottom:14px}
.söz .m{font-size:36px;font-weight:600;letter-spacing:-.015em}
.akis{display:flex;margin-top:58px}
.adim{flex:1;padding:32px 26px;border:1px solid rgba(255,255,255,.08);border-right:none;
  background:#121821}
.adim:last-child{border-right:1px solid rgba(255,255,255,.08)}
.adim.v{background:#1A222D;border-color:rgba(200,161,90,.3)}
.adim .n{font-family:ui-monospace,"SF Mono",Menlo,monospace;font-size:17px;
  color:#6E5A33;letter-spacing:.14em}
.adim .b{font-size:31px;font-weight:600;margin-top:12px;letter-spacing:-.015em}
.not{margin-top:50px;font-size:30px;color:#8494A6}
.kanit{margin-top:72px;padding-top:34px;border-top:1px solid rgba(255,255,255,.08);
  font-family:ui-monospace,"SF Mono",Menlo,monospace;font-size:22px;color:#8494A6}
.kanit b{color:#C8A15A;font-weight:500}
"""

KARTLAR = {
    "acilis": """
      <p class="marka">Anatolia AI</p>
      <h1 style="margin-top:46px">Bir sayı yayımlamak kolay.<br><em>Onu savunmak</em> zor.</h1>
      <p class="alt" style="max-width:44ch">Katılım bankacılığı kampanya metinlerinden
        ölçülen, kanıtlanan bilgi çıkarımı.</p>
    """,
    "problem": """
      <p class="goz">Problem</p>
      <h2>Aynı bilgi, on bankada<br>on farklı biçimde.</h2>
      <div class="dort">
        <div class="söz"><div class="b">Banka A</div><div class="m">"İlk 6 ay masrafsız"</div></div>
        <div class="söz"><div class="b">Banka B</div><div class="m">"%1,99–%2,49 arası"</div></div>
        <div class="söz"><div class="b">Banka C</div><div class="m">"120 aya kadar vade"</div></div>
        <div class="söz"><div class="b">Banka D</div><div class="m">"Dosya masrafı yok*"</div></div>
      </div>
    """,
    "mimari": """
      <p class="goz">Nasıl çalışıyor</p>
      <h2>Önce kural, sonra dil modeli.</h2>
      <div class="akis">
        <div class="adim"><div class="n">01</div><div class="b">Topla</div></div>
        <div class="adim"><div class="n">02</div><div class="b">Temizle</div></div>
        <div class="adim v"><div class="n">03</div><div class="b">Çıkar</div></div>
        <div class="adim"><div class="n">04</div><div class="b">Normalize et</div></div>
        <div class="adim"><div class="n">05</div><div class="b">Kıyasla</div></div>
        <div class="adim"><div class="n">06</div><div class="b">Sun</div></div>
      </div>
      <p class="not">Bilgi metinde yoksa hiçbir değer üretilmez — <em>null</em> döner.</p>
    """,
    "kapanis": """
      <p class="marka">Anatolia AI</p>
      <h1 style="margin-top:46px;max-width:19ch">Tek bir parlak yüzde vermiyoruz.</h1>
      <p class="alt" style="max-width:42ch;font-size:38px;color:#EEF1F5">Çünkü bir alanı
        <em>kaçırmak</em> ile <em>uydurmak</em> aynı hata değildir.</p>
      <div class="kanit"><b>doğrula →</b> github.com/mehmetefeaytas/anatoliaAI</div>
    """,
}


def main() -> None:
    with sync_playwright() as p:
        b = p.chromium.launch()
        sf = b.new_page(viewport={"width": 1920, "height": 1080},
                        device_scale_factor=1)
        for ad, govde in KARTLAR.items():
            sf.set_content(f"<meta charset='utf-8'><style>{STIL}</style>{govde}")
            sf.wait_for_timeout(350)
            yol = CIK / f"{ad}.png"
            sf.screenshot(path=str(yol))
            print(f"{ad:9s} {yol.stat().st_size // 1024:5d} KB")
        b.close()


if __name__ == "__main__":
    main()
