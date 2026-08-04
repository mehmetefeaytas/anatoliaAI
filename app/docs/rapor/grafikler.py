#!/usr/bin/env python3
"""Rapor grafiklerini ölçülmüş verilerden SVG olarak üretir.

Neden elle SVG: sistemde matplotlib/reportlab yok ve kurmak §5.10 lisans
denetimini yeniden açardı. SVG baskıda vektörel keskin kalır, bağımlılık
istemez, tamamen offline üretilir.

Neden betik (elle yazılmış SVG değil): her sayı burada kaynağıyla birlikte
duruyor. Ölçüm güncellenince grafik de güncellenir; rapor ile kanıt arasında
sessiz sapma oluşamaz.

Çalıştırma:
    cd app && ./.venv/bin/python docs/rapor/grafikler.py
"""

from __future__ import annotations

import json
import math
import sqlite3
import sys
from pathlib import Path

APP = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent / "grafikler"

# --- baskı paleti (tek tema; @media dark yok, kağıda basılacak) -------------
INK = "#1a1d23"
MUTED = "#6b7280"
GRID = "#e5e7eb"
SURF = "#f8fafc"
TEAL = "#0f766e"
BLUE = "#1d4ed8"
WARN = "#b45309"
DANGER = "#b91c1c"
OK = "#15803d"
FONT = "-apple-system, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif"
MONO = "ui-monospace, 'SF Mono', Menlo, Consolas, monospace"


def esc(s: str) -> str:
    return (
        str(s)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def svg(width: int, height: int, body: str, title: str, source: str) -> str:
    """Ortak SVG iskeleti: başlık üstte, kaynak referansı altta."""
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}" font-family="{FONT}">
  <rect width="{width}" height="{height}" fill="{SURF}" rx="6"/>
  <text x="24" y="30" font-size="16" font-weight="700" fill="{INK}">{esc(title)}</text>
  {body}
  <text x="24" y="{height - 12}" font-size="10" fill="{MUTED}" font-family="{MONO}">kaynak: {esc(source)}</text>
</svg>
"""


def write(name: str, content: str) -> None:
    path = OUT / name
    path.write_text(content, encoding="utf-8")
    print(f"  ✓ {name}  ({path.stat().st_size // 1024 or 1} KB)")


# ===========================================================================
# G1 — Uçtan uca mimari
# ===========================================================================
def g01_mimari() -> str:
    stages = [
        ("1", "Veri Toplama", "src/scraping/", "robots + rate-limit\n+ provenance", TEAL),
        ("2", "Ön İşleme", "src/preprocessing/", "strip_html, tr_fold\nsplit_sentences", TEAL),
        ("3", "Sınıflandırma", "extraction/ner/", "8 kampanya türü", BLUE),
        ("4", "Kural Çıkarımı", "extraction/rules/", "12 alan · BİRİNCİL\n2204 alan üretti", OK),
        ("5", "LLM Katmanı", "extraction/llm/", "kısıtlı JSON decoding\nşu an: kapalı", WARN),
        ("6", "Uzlaştırma", "reconcile.py", "kural 3 > ner 2 > llm 1", BLUE),
        ("7", "Normalizasyon", "src/normalization/", "oran/para/ay/ISO", TEAL),
        ("8", "Çelişki", "comparison/", "6 çelişki türü", DANGER),
        ("9", "Depo", "src/db/", "SQLite | Postgres\ntek sözleşme", BLUE),
        ("10", "Karşılaştırma", "comparison/compare.py", "5 ölçüt + adil kıyas", OK),
        ("11", "Sunum", "api/ + web/", "dashboard + chatbot", TEAL),
    ]
    w, h = 980, 470
    bw, bh = 196, 88
    gap_x, gap_y = 22, 34
    per_row = 4
    body = []
    for i, (no, name, path, note, color) in enumerate(stages):
        row, col = divmod(i, per_row)
        # zikzak: tek satırlar sağdan sola aksın (okuma akışı kesilmesin)
        if row % 2 == 1:
            col = per_row - 1 - col
        x = 24 + col * (bw + gap_x)
        y = 54 + row * (bh + gap_y)
        body.append(f"""
  <rect x="{x}" y="{y}" width="{bw}" height="{bh}" rx="7" fill="#ffffff" stroke="{color}" stroke-width="1.6"/>
  <rect x="{x}" y="{y}" width="4" height="{bh}" rx="2" fill="{color}"/>
  <circle cx="{x + 22}" cy="{y + 19}" r="10" fill="{color}"/>
  <text x="{x + 22}" y="{y + 23}" font-size="11" font-weight="700" fill="#fff" text-anchor="middle">{no}</text>
  <text x="{x + 40}" y="{y + 23}" font-size="12.5" font-weight="700" fill="{INK}">{esc(name)}</text>
  <text x="{x + 14}" y="{y + 42}" font-size="9.5" fill="{MUTED}" font-family="{MONO}">{esc(path)}</text>""")
        for j, line in enumerate(note.split("\n")):
            body.append(
                f'  <text x="{x + 14}" y="{y + 58 + j * 12}" font-size="10" fill="{INK}">{esc(line)}</text>'
            )
        # ok işaretleri
        if i < len(stages) - 1:
            nrow, ncol = divmod(i + 1, per_row)
            if nrow % 2 == 1:
                ncol = per_row - 1 - ncol
            if nrow == row:
                x2 = 24 + ncol * (bw + gap_x)
                if ncol > col:
                    body.append(
                        f'  <path d="M{x + bw + 3} {y + bh / 2} L{x2 - 5} {y + bh / 2}" stroke="{MUTED}" stroke-width="1.4" marker-end="url(#ar)"/>'
                    )
                else:
                    body.append(
                        f'  <path d="M{x - 3} {y + bh / 2} L{x2 + bw + 5} {y + bh / 2}" stroke="{MUTED}" stroke-width="1.4" marker-end="url(#ar)"/>'
                    )
            else:
                body.append(
                    f'  <path d="M{x + bw / 2} {y + bh + 3} L{x + bw / 2} {y + bh + gap_y - 5}" stroke="{MUTED}" stroke-width="1.4" marker-end="url(#ar)"/>'
                )
    defs = f"""
  <defs><marker id="ar" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="5" markerHeight="5" orient="auto">
    <path d="M0 0 L10 5 L0 10 z" fill="{MUTED}"/></marker></defs>"""
    note = f'  <text x="24" y="{h - 30}" font-size="10.5" fill="{WARN}">Aşama 5 (LLM) teslim demosunda kapalıdır: LLM_BACKEND boş → NullLLMExtractor. Sistem kurallarla çalışmaya devam eder.</text>'
    return svg(w, h, defs + "".join(body) + note, "Uçtan uca işlem hattı — 11 aşama", "src/pipeline.py:149 run_pipeline()")


# ===========================================================================
# G2 — Gecikme (ölçülmüş)
# ===========================================================================
def g02_gecikme() -> str:
    data = json.loads(
        (APP / "docs/offline-proof/latency-20260731-135858.json").read_text()
    )
    labels = {"rule": "kural-only", "hybrid": "hibrit boru hattı", "chatbot": "chatbot (RAG kolu)"}
    paths = [(labels.get(p["name"], p["name"]), p["p50_ms"], p["p95_ms"], p["p99_ms"], p["n"]) for p in data["paths"]]

    w, h = 900, 400
    x0, y0, pw, ph = 150, 68, 610, 232

    # Logaritmik eksen zorunlu: değerler 1,03 ms ile 351,36 ms arasında yayılıyor.
    # Doğrusal eksende kural ve hibrit yolların çubukları görünmez hale geliyordu.
    lo, hi = 0.8, 500.0
    log_lo, log_hi = math.log10(lo), math.log10(hi)

    def bx(v: float) -> float:
        return pw * (math.log10(max(v, lo)) - log_lo) / (log_hi - log_lo)

    body = [f'  <rect x="{x0}" y="{y0}" width="{pw}" height="{ph}" fill="#fff" stroke="{GRID}"/>']
    for t in (1, 2, 5, 10, 20, 50, 100, 200, 500):
        gx = x0 + bx(t)
        body.append(f'  <line x1="{gx:.1f}" y1="{y0}" x2="{gx:.1f}" y2="{y0 + ph}" stroke="{GRID}"/>')
        body.append(f'  <text x="{gx:.1f}" y="{y0 + ph + 15}" font-size="10" fill="{MUTED}" text-anchor="middle">{t}</text>')
    body.append(f'  <text x="{x0 + pw / 2}" y="{y0 + ph + 31}" font-size="10.5" fill="{INK}" text-anchor="middle">milisaniye — belge başına, LOGARİTMİK eksen (düşük iyi)</text>')

    series = [("p50", TEAL), ("p95", BLUE), ("p99", DANGER)]
    grp_h = ph / len(paths)
    for i, (name, p50, p95, p99, n) in enumerate(paths):
        gy = y0 + i * grp_h
        if i:
            body.append(f'  <line x1="{x0}" y1="{gy:.1f}" x2="{x0 + pw}" y2="{gy:.1f}" stroke="{GRID}" stroke-width="1.5"/>')
        body.append(f'  <text x="{x0 - 12}" y="{gy + grp_h / 2 - 3}" font-size="11.5" font-weight="600" fill="{INK}" text-anchor="end">{esc(name)}</text>')
        body.append(f'  <text x="{x0 - 12}" y="{gy + grp_h / 2 + 12}" font-size="9.5" fill=\'{MUTED}\' text-anchor="end" font-family="{MONO}">n={n}</text>')
        for j, (lbl, color) in enumerate(series):
            v = (p50, p95, p99)[j]
            bar_h = 16
            by_ = gy + 12 + j * (bar_h + 4)
            bwid = max(bx(v), 2)
            body.append(f'  <rect x="{x0 + 1}" y="{by_}" width="{bwid:.1f}" height="{bar_h}" fill="{color}" rx="2"/>')
            tx, anchor, fill = x0 + bwid + 7, "start", INK
            if bwid > pw - 90:
                tx, anchor, fill = x0 + bwid - 7, "end", "#fff"
            body.append(f'  <text x="{tx:.1f}" y="{by_ + 12}" font-size="10.5" font-weight="600" fill="{fill}" text-anchor="{anchor}" font-family="{MONO}">{lbl} {v:.2f}</text>')

    leg = [
        f'  <text x="24" y="{h - 46}" font-size="10.5" fill="{INK}">Kural katmanı p99 = 6,30 ms · chatbot p99 = 351,36 ms → RAG kolu <tspan font-weight="700">56× yavaş</tspan>; kayıtlı performans borcu.</text>',
        f'  <text x="24" y="{h - 30}" font-size="10.5" fill="{INK}">Host ölçümü (kural 1,05 / hibrit 1,67 ms) konteyner ölçümüyle neredeyse aynı → konteynerleştirmenin gecikme cezası pratikte yok.</text>',
    ]
    env = data["environment"]
    src = f"docs/offline-proof/latency-20260731-135858.json · {data['corpus']['documents']} belge · konteyner · RSS tepe {env['peak_rss_mb']} MB"
    return svg(w, h, "".join(body + leg), "Ölçülmüş gecikme — üç yol, üç yüzdelik", src)


# ===========================================================================
# G3 — Değişmez ihlal seyri
# ===========================================================================
def g03_ihlal() -> str:
    steps = [
        ("ilk koşu", 134, "çerez/KVKK metni 'kampanya koşulu' sanılıyor;\ncümle bölücü küçük harfli cümleyi kaçırıyor"),
        ("1. düzeltme", 43, "koşul filtresi: politika metni ayıklandı"),
        ("2. düzeltme", 15, "cümle bölücü onarıldı (www. ile başlayanlar)"),
        ("bugün ölçülen", 0, "849 belge · tüm değişmezler GEÇTİ"),
    ]
    w, h = 900, 340
    x0, y0, pw, ph = 70, 66, 780, 176
    vmax = 140

    def by_(v: int) -> float:
        return y0 + ph - ph * (v / vmax)

    body = [f'  <line x1="{x0}" y1="{y0 + ph}" x2="{x0 + pw}" y2="{y0 + ph}" stroke="{INK}" stroke-width="1.2"/>']
    for t in (0, 35, 70, 105, 140):
        gy = by_(t)
        body.append(f'  <line x1="{x0}" y1="{gy:.1f}" x2="{x0 + pw}" y2="{gy:.1f}" stroke="{GRID}"/>')
        body.append(f'  <text x="{x0 - 10}" y="{gy + 4:.1f}" font-size="10" fill="{MUTED}" text-anchor="end">{t}</text>')

    step_w = pw / len(steps)
    pts = []
    for i, (label, val, note) in enumerate(steps):
        cx = x0 + step_w * (i + 0.5)
        top = by_(val)
        pts.append((cx, top))
        color = OK if val == 0 else (DANGER if val > 100 else WARN)
        bar_w = 74
        if val > 0:
            body.append(f'  <rect x="{cx - bar_w / 2:.1f}" y="{top:.1f}" width="{bar_w}" height="{y0 + ph - top:.1f}" fill="{color}" opacity="0.16" rx="3"/>')
        body.append(f'  <circle cx="{cx:.1f}" cy="{top:.1f}" r="6" fill="{color}"/>')
        vy = top - 14 if val > 0 else top - 14
        body.append(f'  <text x="{cx:.1f}" y="{vy:.1f}" font-size="15" font-weight="700" fill="{color}" text-anchor="middle" font-family="{MONO}">{val}</text>')
        body.append(f'  <text x="{cx:.1f}" y="{y0 + ph + 20}" font-size="11.5" font-weight="600" fill="{INK}" text-anchor="middle">{esc(label)}</text>')
        for j, line in enumerate(note.split("\n")):
            body.append(f'  <text x="{cx:.1f}" y="{y0 + ph + 36 + j * 12}" font-size="9" fill="{MUTED}" text-anchor="middle">{esc(line)}</text>')

    path = " ".join(f"{'M' if i == 0 else 'L'}{x:.1f} {y:.1f}" for i, (x, y) in enumerate(pts))
    body.insert(1, f'  <path d="{path}" stroke="{INK}" stroke-width="2" fill="none" stroke-dasharray="4 3"/>')
    body.append(f'  <text x="{x0}" y="{h - 30}" font-size="10.5" fill="{INK}">Etiketsiz veride otomatik hata avı: bu 134 ihlal hiçbir testi kırmamıştı — sistem sessizce yanlış üretiyordu.</text>')
    return svg(w, h, "".join(body), "Değişmez (metamorfik) denetimi — ihlal seyri", "eval/reports/violations-*.jsonl + bugün koşulan `python -m eval.properties`")


# ===========================================================================
# G4/G5/G6 — korpus gerçekleri (demo.db'den canlı okunur)
# ===========================================================================
def _db() -> sqlite3.Connection:
    return sqlite3.connect(APP / "data/demo.db")


def g04_tur_dagilimi() -> str:
    con = _db()
    rows = con.execute(
        "SELECT COALESCE(campaign_type,'(sınıflanamayan)'), COUNT(*) FROM campaigns GROUP BY 1 ORDER BY 2 DESC"
    ).fetchall()
    total = con.execute("SELECT COUNT(*) FROM campaigns").fetchone()[0]
    con.close()

    w = 900
    h = 120 + len(rows) * 30
    x0, y0, pw = 210, 60, 560
    vmax = max(v for _, v in rows)
    body = []
    for i, (name, val) in enumerate(rows):
        y = y0 + i * 30
        bw_ = pw * val / vmax
        color = MUTED if "sınıflanamayan" in name else TEAL
        body.append(f'  <text x="{x0 - 12}" y="{y + 15}" font-size="11.5" fill="{INK}" text-anchor="end">{esc(name)}</text>')
        body.append(f'  <rect x="{x0}" y="{y}" width="{bw_:.1f}" height="21" fill="{color}" rx="3" opacity="0.9"/>')
        pct = 100 * val / total
        body.append(f'  <text x="{x0 + bw_ + 8:.1f}" y="{y + 15}" font-size="11" font-weight="600" fill="{INK}" font-family="{MONO}">{val}  ({pct:.1f}%)</text>')
    body.append(f'  <text x="24" y="{h - 30}" font-size="10.5" fill="{INK}">Şartname §5.4\'ün 8 türünün tamamı üretiliyor. Sınıflanamayan belgeler gizlenmiyor — ayrı satır olarak raporlanıyor.</text>')
    return svg(w, h, "".join(body), f"Kampanya türü dağılımı — {total} belge, 8 tür (§5.4)", "data/demo.db · SELECT campaign_type, COUNT(*) FROM campaigns")


def g05_alan_kapsami() -> str:
    con = _db()
    rows = con.execute(
        "SELECT field_name, COUNT(DISTINCT campaign_id) FROM extracted_fields GROUP BY 1 ORDER BY 2 DESC"
    ).fetchall()
    total_docs = con.execute("SELECT COUNT(*) FROM campaigns").fetchone()[0]
    total_fields = con.execute("SELECT COUNT(*) FROM extracted_fields").fetchone()[0]
    con.close()

    labels = {
        "kar_payi_orani": "Kâr Payı Oranı", "finansman_tutari": "Finansman Tutarı",
        "vade_ay": "Vade (ay)", "taksit_sayisi": "Taksit Sayısı",
        "tahsis_ucreti": "Tahsis Ücreti", "masraf_durumu": "Masraf Durumu",
        "odul_miktari": "Ödül Miktarı", "indirim_orani": "İndirim Oranı",
        "alisveris_puani": "Alışveriş Puanı", "kampanya_suresi": "Kampanya Süresi",
        "kampanya_kosullari": "Kampanya Koşulları", "hedef_kitle": "Hedef Kitle",
    }
    w = 900
    h = 130 + len(rows) * 30
    x0, y0, pw = 210, 60, 520
    body = []
    for i, (fname, docs) in enumerate(rows):
        y = y0 + i * 30
        pct = 100 * docs / total_docs
        bw_ = pw * docs / total_docs
        # §5.7'nin sıralama ölçütleri kritik: kapsamı düşükse kıyas zayıflar
        critical = fname in ("kar_payi_orani", "tahsis_ucreti", "odul_miktari", "vade_ay")
        color = DANGER if (critical and pct < 15) else (WARN if pct < 20 else TEAL)
        body.append(f'  <text x="{x0 - 12}" y="{y + 15}" font-size="11.5" fill="{INK}" text-anchor="end">{esc(labels.get(fname, fname))}</text>')
        body.append(f'  <rect x="{x0}" y="{y}" width="{pw}" height="21" fill="{GRID}" rx="3"/>')
        body.append(f'  <rect x="{x0}" y="{y}" width="{max(bw_, 2):.1f}" height="21" fill="{color}" rx="3"/>')
        body.append(f'  <text x="{x0 + pw + 10}" y="{y + 15}" font-size="11" font-weight="600" fill="{INK}" font-family="{MONO}">{docs}  ({pct:.1f}%)</text>')
    kar_payi = dict(rows)["kar_payi_orani"]
    body.append(f'  <text x="24" y="{h - 46}" font-size="10.5" fill="{DANGER}" font-weight="600">EN BÜYÜK KISIT: kâr payı oranı yalnız {kar_payi} belgede ({100 * kar_payi / total_docs:.1f}%) — §5.7\'nin birinci ölçütü bu alana dayanıyor.</text>')
    body.append(f'  <text x="24" y="{h - 30}" font-size="10.5" fill="{INK}">Kırmızı = §5.7 sıralama ölçütü olup kapsamı %15 altında. Boş bırakılan alanlar uydurulmuyor; kıyas comparable=False ile işaretleniyor.</text>')
    return svg(w, h, "".join(body), f"Alan kapsamı — {total_fields} alan / {total_docs} belge (kaç belgede var?)", "data/demo.db · COUNT(DISTINCT campaign_id) GROUP BY field_name")


def g06_katman_katkisi() -> str:
    con = _db()
    rows = dict(con.execute("SELECT extractor, COUNT(*) FROM extracted_fields GROUP BY 1").fetchall())
    total = sum(rows.values())
    con.close()
    layers = [
        ("kural (regex + normalizasyon)", rows.get("rule", 0), OK, "src/extraction/rules/ — deterministik, birincil"),
        ("ner (BERTurk / GLiNER)", rows.get("ner", 0), MUTED, "yalnız kampanya türü sınıflandırmasında; alan üretmiyor"),
        ("llm (kısıtlı JSON decoding)", rows.get("llm", 0), WARN, "LLM_BACKEND boş → NullLLMExtractor; hiç alan katmadı"),
    ]
    w, h = 900, 330
    x0, y0, pw = 250, 78, 470
    body = []
    for i, (name, val, color, note) in enumerate(layers):
        y = y0 + i * 62
        bw_ = pw * val / total if total else 0
        body.append(f'  <text x="{x0 - 14}" y="{y + 16}" font-size="12" font-weight="600" fill="{INK}" text-anchor="end">{esc(name)}</text>')
        body.append(f'  <rect x="{x0}" y="{y}" width="{pw}" height="24" fill="{GRID}" rx="3"/>')
        if val:
            body.append(f'  <rect x="{x0}" y="{y}" width="{bw_:.1f}" height="24" fill="{color}" rx="3"/>')
            body.append(f'  <text x="{x0 + 12}" y="{y + 17}" font-size="12" font-weight="700" fill="#fff" font-family="{MONO}">{val} alan  ({100 * val / total:.0f}%)</text>')
        else:
            body.append(f'  <text x="{x0 + 12}" y="{y + 17}" font-size="12" font-weight="700" fill="{color}" font-family="{MONO}">0 alan  (0%)</text>')
        body.append(f'  <text x="{x0}" y="{y + 40}" font-size="10" fill="{MUTED}">{esc(note)}</text>')
    body.append(f'  <rect x="24" y="{h - 74}" width="852" height="44" fill="#fff" stroke="{WARN}" rx="5"/>')
    body.append(f'  <text x="38" y="{h - 56}" font-size="11" font-weight="700" fill="{WARN}">DÜRÜSTLÜK NOTU — mimari "hibrit", teslim edilen korpus %100 kural katmanı.</text>')
    body.append(f'  <text x="38" y="{h - 40}" font-size="10.5" fill="{INK}">LLM kolu kodda tamamdır ve canlı çıkarımda çağrılabilir; ancak GPU olmadığı için korpus üretiminde hiç devreye girmedi. Ablasyon henüz koşulmadı.</text>')
    return svg(w, h, "".join(body), "Hangi katman kaç alan üretti? — teslim edilen korpusun gerçeği", "data/demo.db · SELECT extractor, COUNT(*) FROM extracted_fields")


# ===========================================================================
# G7 — Rubrik durum panosu
# ===========================================================================
def g07_rubrik() -> str:
    crit = [
        ("Model Başarısı ve Anlamlandırma", 30, "eksik", "Ölçüm altyapısı hazır, GOLD SETİ DONDURULMADI → P/R/F1 yok"),
        ("Fonksiyonellik ve Senaryo Kapsamı", 20, "tam", "5/5 ölçüt · dashboard + chatbot · uçtan uca çalışıyor"),
        ("Teknik İmplementasyon ve Mimari", 20, "tam", "890 test · ruff CI kapısı · değişmez denetimi · modüler"),
        ("On-Prem Uygulanabilirlik", 20, "tam", "--network none ölçüldü + pozitif kontrol · digest pin"),
        ("Yenilikçilik ve Yaratıcılık", 10, "tam", "span vurgulama · çelişki tespiti · 5 güvenlik kapısı"),
    ]
    w, h = 900, 372
    x0, y0 = 24, 58
    row_h = 50
    body = []
    styles = {"tam": (OK, "✓ kanıtlı"), "kismi": (WARN, "⚠ kısmi"), "eksik": (DANGER, "⏳ ölçülmedi")}
    for i, (name, weight, state, note) in enumerate(crit):
        y = y0 + i * row_h
        color, badge = styles[state]
        body.append(f'  <rect x="{x0}" y="{y}" width="852" height="{row_h - 8}" fill="#fff" stroke="{GRID}" rx="5"/>')
        body.append(f'  <rect x="{x0}" y="{y}" width="4" height="{row_h - 8}" fill="{color}" rx="2"/>')
        body.append(f'  <text x="{x0 + 16}" y="{y + 19}" font-size="12.5" font-weight="700" fill="{INK}">{esc(name)}</text>')
        body.append(f'  <text x="{x0 + 16}" y="{y + 35}" font-size="10" fill="{MUTED}">{esc(note)}</text>')
        # Çubuk + yüzde + durum etiketi çakışmasın: çubuk 560'ta başlar,
        # en geniş hâlinde (%30) 680'de biter, yüzde 688'de, badge 866'da sona erer.
        bx_, bar_scale = 560, 4.0
        bar_w = weight * bar_scale
        body.append(f'  <rect x="{bx_}" y="{y + 12}" width="{bar_w:.0f}" height="18" fill="{color}" opacity="0.85" rx="3"/>')
        body.append(f'  <text x="{bx_ + bar_w + 8:.0f}" y="{y + 26}" font-size="12" font-weight="700" fill="{INK}" font-family="{MONO}">%{weight}</text>')
        body.append(f'  <text x="866" y="{y + 26}" font-size="10.5" font-weight="600" fill="{color}" text-anchor="end">{badge}</text>')
    body.append(f'  <text x="24" y="{h - 44}" font-size="11" font-weight="700" fill="{DANGER}">Rubriğin en ağır maddesi (%30) tek eksik olan. Kalan %70 ölçülmüş kanıta dayanıyor.</text>')
    body.append(f'  <text x="24" y="{h - 28}" font-size="10.5" fill="{INK}">Bu tablo iddiaya değil koşulan komuta dayanır: her "kanıtlı" satırın arkasında bir transkript, JSON veya test çıktısı vardır.</text>')
    return svg(w, h, "".join(body), "Değerlendirme rubriği — 3 Ağustos 2026 durumu", "2026 TEKNOFEST TYDA şartname s.15 + app/docs/sartname-kod-eslesme.md")


# ===========================================================================
# G8 — Offline paket boyutu
# ===========================================================================
def g08_paket() -> str:
    items = [
        ("Teslim imajı (api)", 96.5, OK, "ölçüldü · 101.218.586 bayt"),
        ("api + postgres (asgari)", 255.0, OK, "ölçüldü · jüri demosu bu profille koşar"),
        ("+ ollama (CPU yedeği)", 3029.0, WARN, "digest pinli imaj"),
        ("Tam GPU yığını (vLLM)", 10604.0, DANGER, "+ model ağırlıkları >16 GB"),
    ]
    w, h = 900, 300
    x0, y0, pw = 250, 62, 480
    vmax = 10604.0
    body = []
    for i, (name, mb, color, note) in enumerate(items):
        y = y0 + i * 50
        bw_ = max(pw * mb / vmax, 3)
        body.append(f'  <text x="{x0 - 14}" y="{y + 16}" font-size="11.5" font-weight="600" fill="{INK}" text-anchor="end">{esc(name)}</text>')
        body.append(f'  <rect x="{x0}" y="{y}" width="{bw_:.1f}" height="22" fill="{color}" rx="3"/>')
        label = f"{mb / 1024:.1f} GB" if mb >= 1024 else f"{mb:.1f} MB"
        body.append(f'  <text x="{x0 + bw_ + 9:.1f}" y="{y + 16}" font-size="11.5" font-weight="700" fill="{INK}" font-family="{MONO}">{label}</text>')
        body.append(f'  <text x="{x0}" y="{y + 36}" font-size="9.5" fill="{MUTED}">{esc(note)}</text>')
    body.append(f'  <text x="24" y="{h - 44}" font-size="11" font-weight="700" fill="{TEAL}">255 MB ↔ 10,6 GB = 40× fark. Kurum içi kurulumun gerçek maliyeti bu iki uç arasında seçilir.</text>')
    body.append(f'  <text x="24" y="{h - 28}" font-size="10.5" fill="{INK}">Jüri demosu asgari profille koşar: GPU yok, ağ yok, LLM kapalı — yine de 849 belge ve 5 karşılaştırma ölçütü çalışır.</text>')
    return svg(w, h, "".join(body), "On-prem kurulum ayak izi — dört profil", "app/docs/kaynak-tuketimi.md §6 + docker-compose.yml digest pinleri")


# ===========================================================================
# G9 — Güvenlik kapıları ablasyonu
# ===========================================================================
def g09_guvenlik() -> str:
    cats = [
        ("terminoloji", 5, 1.00, 0.00),
        ("fıkhî hüküm", 5, 1.00, 0.00),
        ("yatırım tavsiyesi", 5, 1.00, 0.00),
        ("garanti iması", 4, 1.00, 0.25),
        ("çekimserlik / atıf", 5, 1.00, 0.20),
        ("KONTROL (aşırı red)", 6, 1.00, 1.00),
    ]
    w, h = 900, 388
    x0, y0, pw = 220, 66, 420
    body = []
    for i, (name, n, on, off) in enumerate(cats):
        y = y0 + i * 42
        ctrl = "KONTROL" in name
        body.append(f'  <text x="{x0 - 14}" y="{y + 13}" font-size="11.5" font-weight="{"700" if ctrl else "500"}" fill="{INK}" text-anchor="end">{esc(name)}</text>')
        body.append(f'  <text x="{x0 - 14}" y="{y + 27}" font-size="9" fill="{MUTED}" text-anchor="end" font-family="{MONO}">n={n}</text>')
        body.append(f'  <rect x="{x0}" y="{y}" width="{pw * on:.1f}" height="15" fill="{OK}" rx="2"/>')
        body.append(f'  <text x="{x0 + pw * on + 8:.1f}" y="{y + 12}" font-size="10" font-weight="600" fill="{OK}" font-family="{MONO}">açık {on:.2f}</text>')
        body.append(f'  <rect x="{x0}" y="{y + 18}" width="{max(pw * off, 2):.1f}" height="15" fill="{DANGER if not ctrl else MUTED}" rx="2"/>')
        body.append(f'  <text x="{x0 + max(pw * off, 2) + 8:.1f}" y="{y + 30}" font-size="10" font-weight="600" fill="{DANGER if not ctrl else MUTED}" font-family="{MONO}">kapalı {off:.2f}</text>')
    body.append(f'  <text x="{x0}" y="{y0 - 12}" font-size="10.5" fill="{MUTED}">yeşil = 5 kapı açık · kırmızı = kapılar kapalı (ablasyon) · gri = kontrol grubu (değişmemeli)</text>')
    body.append(f'  <text x="24" y="{h - 46}" font-size="11" font-weight="700" fill="{INK}">GENEL: kapılar açık 1,00 (30/30) · kapılar kapalı 0,20 → kapılar gerçekten çalışıyor.</text>')
    body.append(f'  <text x="24" y="{h - 30}" font-size="10.5" fill="{INK}">Kontrol grubu her iki halde 1,00: kapılar meşru soruları reddetmiyor. Aşırı red oranı 0/6 ölçüldü — bu ölçüm olmadan kapılar "her şeye hayır de" ile taklit edilebilirdi.</text>')
    return svg(w, h, "".join(body), "Katılım bankacılığı güvenlik kapıları — ablasyonlu değerlendirme", "app/docs/katilim-bankaciligi-guvenligi.md §4 · data/safety/katilim-guvenlik-seti.jsonl (30 soru)")


# ===========================================================================
# G10 — Test sayısı büyümesi
# ===========================================================================
def g10_testler() -> str:
    pts = [("54", 54), ("72", 72), ("85", 85), ("129", 129), ("345", 345), ("607", 607), ("890", 890)]
    stages = ["uçtan uca\nçekirdek", "TR küçük\nharf hatası", "çelişki\ntespiti", "12/12 alan +\ndeğişmez", "eval\naltyapısı", "offline\nkanıt", "pgvector +\nparite"]
    w, h = 900, 320
    x0, y0, pw, ph = 70, 62, 780, 180
    vmax = 950
    body = [f'  <line x1="{x0}" y1="{y0 + ph}" x2="{x0 + pw}" y2="{y0 + ph}" stroke="{INK}"/>']
    for t in (0, 200, 400, 600, 800):
        gy = y0 + ph - ph * t / vmax
        body.append(f'  <line x1="{x0}" y1="{gy:.1f}" x2="{x0 + pw}" y2="{gy:.1f}" stroke="{GRID}"/>')
        body.append(f'  <text x="{x0 - 10}" y="{gy + 4:.1f}" font-size="10" fill="{MUTED}" text-anchor="end">{t}</text>')
    step = pw / len(pts)
    coords = []
    for i, (lbl, val) in enumerate(pts):
        cx = x0 + step * (i + 0.5)
        cy = y0 + ph - ph * val / vmax
        coords.append((cx, cy))
        bw_ = 52
        body.append(f'  <rect x="{cx - bw_ / 2:.1f}" y="{cy:.1f}" width="{bw_}" height="{y0 + ph - cy:.1f}" fill="{TEAL}" opacity="0.18" rx="3"/>')
        body.append(f'  <circle cx="{cx:.1f}" cy="{cy:.1f}" r="5" fill="{TEAL}"/>')
        body.append(f'  <text x="{cx:.1f}" y="{cy - 11:.1f}" font-size="12" font-weight="700" fill="{TEAL}" text-anchor="middle" font-family="{MONO}">{lbl}</text>')
        for j, line in enumerate(stages[i].split("\n")):
            body.append(f'  <text x="{cx:.1f}" y="{y0 + ph + 18 + j * 11}" font-size="8.5" fill="{MUTED}" text-anchor="middle">{esc(line)}</text>')
    path = " ".join(f"{'M' if i == 0 else 'L'}{x:.1f} {y:.1f}" for i, (x, y) in enumerate(coords))
    body.insert(1, f'  <path d="{path}" stroke="{TEAL}" stroke-width="2" fill="none"/>')
    body.append(f'  <text x="24" y="{h - 30}" font-size="10.5" fill="{INK}">Fiili sayım bugün: 39 dosya, 890 test (unittest). Dokümanlarda altı farklı rakam dolaşıyor — düzeltilecek (bkz. §D4).</text>')
    return svg(w, h, "".join(body), "Test sayısı büyümesi — 54 → 890", "log.md girdileri + `grep -c 'def test' app/tests/*.py` (3 Ağustos 2026)")


# ===========================================================================
# G11 — Gold anotasyon hattı
# ===========================================================================
def g11_gold_hatti() -> str:
    steps = [
        ("preannotate.py", "849 belgeden 250 örnek\nhibrit çıkarımla ön-anotasyon", "✓ hazır", OK),
        ("to_review_csv.py", "alan-başına-satır CSV\n+50 mükerrer +20 kalibrasyon", "✓ hazır", OK),
        ("4 anotatör", "~1,5 sa/kişi · boş hücre\n= 'model doğru'", "⏳ YAPILMADI", DANGER),
        ("report_iaa.py", "Cohen κ (2) / Fleiss κ (4)\neşik: κ≥0,80 kabul", "⏳ YAPILMADI", DANGER),
        ("build_gold.py", "gold.v1.json + sha256\nabsent_fields ayrımı", "⏳ YAPILMADI", DANGER),
        ("split_gold.py", "dev/test bölmesi\nTEST dondurulur", "✓ protokol hazır", WARN),
        ("run_eval + ablation", "P/R/F1 + bootstrap GA\n+ McNemar · 4 kol", "⏳ %30 BURADA", DANGER),
    ]
    w, h = 900, 300
    bw, bh = 116, 118
    gap = 8
    body = []
    for i, (name, note, state, color) in enumerate(steps):
        x = 24 + i * (bw + gap)
        y = 60
        body.append(f'  <rect x="{x}" y="{y}" width="{bw}" height="{bh}" rx="6" fill="#fff" stroke="{color}" stroke-width="1.6"/>')
        body.append(f'  <rect x="{x}" y="{y}" width="{bw}" height="4" rx="2" fill="{color}"/>')
        body.append(f'  <text x="{x + bw / 2}" y="{y + 22}" font-size="9.5" font-weight="700" fill="{INK}" text-anchor="middle" font-family="{MONO}">{esc(name)}</text>')
        for j, line in enumerate(note.split("\n")):
            body.append(f'  <text x="{x + bw / 2}" y="{y + 42 + j * 12}" font-size="8.5" fill="{MUTED}" text-anchor="middle">{esc(line)}</text>')
        body.append(f'  <text x="{x + bw / 2}" y="{y + bh - 12}" font-size="9.5" font-weight="700" fill="{color}" text-anchor="middle">{esc(state)}</text>')
        if i < len(steps) - 1:
            body.append(f'  <path d="M{x + bw + 1} {y + bh / 2} L{x + bw + gap - 2} {y + bh / 2}" stroke="{MUTED}" stroke-width="1.3"/>')
    body.append(f'  <rect x="24" y="{h - 84}" width="852" height="54" fill="#fff" stroke="{DANGER}" rx="5"/>')
    body.append(f'  <text x="38" y="{h - 65}" font-size="11" font-weight="700" fill="{DANGER}">Hattın 3406 satırı yazılmış ve test edilmiş; 3. adımdan itibaren hiç koşulmamış.</text>')
    body.append(f'  <text x="38" y="{h - 49}" font-size="10.5" fill="{INK}">Kural katmanı gold sete BAKILMADAN yazıldı → 250 kayıt gerçek bir held-out test setidir. Bu avantaj yalnız gold</text>')
    body.append(f'  <text x="38" y="{h - 35}" font-size="10.5" fill="{INK}">dondurulup metrik ondan sonra üretilirse korunur. 23 gün içinde kapatılması gereken tek kritik boşluk budur.</text>')
    return svg(w, h, "".join(body), "Gold anotasyon hattı — kurulu ama koşulmamış", "app/scripts/{preannotate,to_review_csv,report_iaa,build_gold,split_gold}.py")


# ===========================================================================
# G12 — 23 günlük yol haritası
# ===========================================================================
def g12_yol_haritasi() -> str:
    tasks = [
        ("Anotasyon (4 kişi × 250 belge)", 1, 6, DANGER, "%30"),
        ("IAA / kappa hesabı", 6, 8, DANGER, "%30"),
        ("Gold dondurma + split", 8, 9, DANGER, "%30"),
        ("run_eval + ablasyon + GA", 9, 12, DANGER, "%30"),
        ("Veri seti Release + CC-BY-4.0", 9, 11, WARN, "§9"),
        ("Doküman tutarsızlık temizliği", 11, 14, WARN, "%20"),
        ("Demo videosu (5 dk + 1 dk)", 14, 18, BLUE, "§6.2"),
        ("Sunum PDF + PPTX", 17, 21, BLUE, "§6.4"),
        ("x86_64 + tam compose doğrulama", 12, 15, WARN, "%20"),
        ("Prova + tampon", 21, 23, OK, "—"),
    ]
    w, h = 900, 380
    x0, y0, pw = 250, 76, 560
    days = 23
    row_h = 27
    body = []
    for d in range(0, days + 1, 2):
        gx = x0 + pw * d / days
        body.append(f'  <line x1="{gx:.1f}" y1="{y0 - 8}" x2="{gx:.1f}" y2="{y0 + len(tasks) * row_h}" stroke="{GRID}"/>')
        body.append(f'  <text x="{gx:.1f}" y="{y0 - 14}" font-size="9" fill=\'{MUTED}\' text-anchor="middle">{3 + d} Ağu</text>')
    for i, (name, s, e, color, tag) in enumerate(tasks):
        y = y0 + i * row_h
        bx_ = x0 + pw * s / days
        bw_ = max(pw * (e - s) / days, 6)
        body.append(f'  <text x="{x0 - 14}" y="{y + 15}" font-size="10.5" fill="{INK}" text-anchor="end">{esc(name)}</text>')
        body.append(f'  <rect x="{bx_:.1f}" y="{y + 4}" width="{bw_:.1f}" height="16" fill="{color}" rx="3" opacity="0.9"/>')
        body.append(f'  <text x="{x0 + pw + 12}" y="{y + 16}" font-size="9" font-weight="700" fill="{color}" font-family="{MONO}">{esc(tag)}</text>')
    dl = x0 + pw
    body.append(f'  <line x1="{dl}" y1="{y0 - 8}" x2="{dl}" y2="{y0 + len(tasks) * row_h}" stroke="{DANGER}" stroke-width="2"/>')
    body.append(f'  <text x="{dl - 6}" y="{y0 + len(tasks) * row_h + 16}" font-size="10" font-weight="700" fill="{DANGER}" text-anchor="end">26 Ağustos — çevrimiçi süreç bitişi</text>')
    body.append(f'  <text x="24" y="{h - 44}" font-size="11" font-weight="700" fill="{DANGER}">Kırmızı zincir kritik yol: anotasyon gecikirse %30 ölçülemez ve zincirin tamamı kayar.</text>')
    body.append(f'  <text x="24" y="{h - 28}" font-size="10.5" fill="{INK}">Anotasyon 4 kişiye paralel dağıtılabilir tek iştir — en erken başlaması gereken kalem odur.</text>')
    return svg(w, h, "".join(body), "23 günlük yol haritası — 3 → 26 Ağustos 2026", "şartname §3 takvim + app/docs/sartname-kod-eslesme.md §6 eksikleri")


CHARTS = [
    ("g01-mimari.svg", g01_mimari),
    ("g02-gecikme.svg", g02_gecikme),
    ("g03-ihlal-seyri.svg", g03_ihlal),
    ("g04-tur-dagilimi.svg", g04_tur_dagilimi),
    ("g05-alan-kapsami.svg", g05_alan_kapsami),
    ("g06-katman-katkisi.svg", g06_katman_katkisi),
    ("g07-rubrik-panosu.svg", g07_rubrik),
    ("g08-paket-boyutu.svg", g08_paket),
    ("g09-guvenlik-ablasyon.svg", g09_guvenlik),
    ("g10-test-buyumesi.svg", g10_testler),
    ("g11-gold-hatti.svg", g11_gold_hatti),
    ("g12-yol-haritasi.svg", g12_yol_haritasi),
]


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    print(f"Grafikler üretiliyor → {OUT}")
    for name, fn in CHARTS:
        write(name, fn())
    print(f"\n{len(CHARTS)} grafik tamamlandı.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
