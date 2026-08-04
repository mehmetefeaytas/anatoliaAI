"""PDF metin çıkarımı — ücret tarifeleri ve ürün bilgi formları için.

İlgili: CLAUDE.md §14 (provenance), §19 (bağımlılık lisansı),
        docs/rapor/banka-siteleri-veri-kaynagi-haritasi.md §7

NEDEN: Ücret/komisyon tarifeleri ve "Ürün Bilgi Formu" belgeleri bankalarda HTML
tablo olarak DEĞİL, **PDF** olarak yayımlanıyor (2026-08-03 tarayıcı doğrulaması:
Emlak Katılım, Dünya Katılım, Türkiye Finans). Kesin tahsis ücreti, masraf oranı
ve kâr payı bilgisi orada durur — kampanya sayfasında "masrafsız" denip tarifede
ücret çıkması, projenin çelişki tespiti hedefinin (CLAUDE.md §18-2) tam merkezidir.

LİSANS: `pypdf` — BSD-3-Clause. requirements.txt politikası "yalnızca açık kaynak
(Apache/MIT/BSD)" olduğu için uygundur. PyMuPDF (fitz) **AGPL** olduğu için
KULLANILMAZ — Apache-2.0 teslimle uyumsuz (şartname §5.10 lisans riski).

Zarif düşüş: pypdf kurulu değilse `extract_pdf_text` boş metin + açık gerekçe
döner; hat çökmez, rapor bunu not eder (kodun geri kalanındaki desenle aynı).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

from ..preprocessing.clean import normalize_text

# PDF imzası — Content-Type yanlış/eksik olduğunda gerçek tip buradan anlaşılır.
PDF_MAGIC = b"%PDF-"

# Tarife PDF'lerinde tek sayfa bile onlarca satır tablo taşır; 200 karakterin
# altı "metin katmanı yok" (taranmış görüntü) demektir.
MIN_PDF_TEXT_CHARS = 200


@dataclass
class PdfText:
    """PDF çıkarım sonucu — metin + tanılama."""

    text: str
    pages: int = 0
    error: Optional[str] = None
    extractor: str = "pypdf"

    @property
    def ok(self) -> bool:
        return bool(self.text) and self.error is None


def looks_like_pdf(content: bytes, content_type: str = "") -> bool:
    """İçerik gerçekten PDF mi? Content-Type'a GÜVENİLMEZ.

    Bazı sunucular PDF'i `application/octet-stream` ya da `text/html` olarak
    etiketliyor; tersi de olur (HTML hata sayfası `application/pdf` etiketiyle
    gelir). Karar bayt imzasına göre verilir.
    """
    if content[:5] == PDF_MAGIC:
        return True
    # Bazı sunucular başa BOM/boşluk koyuyor
    return PDF_MAGIC in content[:1024]


def extract_pdf_text(content: bytes, *, max_pages: int = 200) -> PdfText:
    """PDF baytlarından metin çıkarır.

    `max_pages`: 500 sayfalık sözleşme kitapçıkları çıkarımı dakikalarca
    sürdürebilir; sınır aşılırsa ilk `max_pages` sayfa alınır ve bu DURUM
    metne değil `error` alanına yazılır (sessiz kırpma yok).
    """
    if not content:
        return PdfText("", error="bos icerik")
    if not looks_like_pdf(content):
        return PdfText("", error="PDF imzasi yok (%PDF- bulunamadi)")
    try:
        from pypdf import PdfReader  # type: ignore
    except ModuleNotFoundError:
        return PdfText("", error="pypdf kurulu degil — PDF metni cikarilamadi",
                       extractor="yok")

    import io

    try:
        reader = PdfReader(io.BytesIO(content))
    except Exception as exc:
        return PdfText("", error=f"PDF okunamadi: {type(exc).__name__}: {exc}"[:200])

    if getattr(reader, "is_encrypted", False):
        # Boş parolayla açılan (yalnızca izin kısıtlı) PDF'ler yaygın — denenir.
        try:
            reader.decrypt("")
        except Exception:
            return PdfText("", error="PDF sifreli, acilamadi")

    total = len(reader.pages)
    limit = min(total, max_pages)
    parts: list[str] = []
    failed_pages = 0
    for i in range(limit):
        try:
            parts.append(reader.pages[i].extract_text() or "")
        except Exception:
            failed_pages += 1
    text = normalize_text(_join_pages(parts))

    notes: list[str] = []
    if total > limit:
        notes.append(f"{total} sayfanin ilk {limit}'i alindi")
    if failed_pages:
        notes.append(f"{failed_pages} sayfa cikarilamadi")
    if len(text) < MIN_PDF_TEXT_CHARS:
        notes.append(f"metin katmani yok/zayif ({len(text)} krkt) — taranmis olabilir")

    return PdfText(text=text, pages=total, error="; ".join(notes) or None)


def _join_pages(parts: list[str]) -> str:
    """Sayfaları birleştirir; sayfa altı/üstü tekrarlarını seyreltir.

    Tarife PDF'lerinde her sayfanın altında aynı yasal uyarı satırı bulunur;
    aynen tekrar eden satırlar bir kez bırakılır (çıkarım gürültüsünü azaltır).
    """
    seen_lines: dict[str, int] = {}
    for part in parts:
        for line in part.splitlines():
            key = re.sub(r"\s+", " ", line).strip()
            if len(key) > 15:
                seen_lines[key] = seen_lines.get(key, 0) + 1
    # 3+ sayfada birebir tekrar eden satır = sayfa altbilgisi
    boilerplate = {k for k, n in seen_lines.items() if n >= 3}

    out: list[str] = []
    emitted: set[str] = set()
    for part in parts:
        for line in part.splitlines():
            key = re.sub(r"\s+", " ", line).strip()
            if key in boilerplate:
                if key in emitted:
                    continue
                emitted.add(key)
            out.append(line)
    return "\n".join(out)


__all__ = ["PdfText", "extract_pdf_text", "looks_like_pdf", "PDF_MAGIC",
           "MIN_PDF_TEXT_CHARS"]
