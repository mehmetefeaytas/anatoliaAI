"""TR-aware metin ön işleme — saf stdlib.

İlgili: ../../concepts/veri-on-isleme.md
HTML temizleme + boşluk normalizasyonu + TR-duyarlı cümle segmentasyonu.
Ağır bağımlılık yok; trafilatura/BeautifulSoup scraping katmanında devreye girer.
"""

from __future__ import annotations

import html
import re
import unicodedata

# Kısaltmalar: nokta sonrası cümle bölmeyi engellemek için (TR yaygın)
_ABBREV = {"vb", "vs", "örn", "bkz", "no", "tl", "a.ş", "sn", "dr", "prof"}


def strip_html(text: str) -> str:
    """Kaba HTML etiket temizliği + entity çözme. (trafilatura yoksa yedek.)"""
    if not text:
        return ""
    text = re.sub(r"(?is)<(script|style)\b.*?</\1>", " ", text)
    text = re.sub(r"(?s)<[^>]+>", " ", text)
    return html.unescape(text)


def normalize_whitespace(text: str) -> str:
    """Çoklu boşluk/satır → tek boşluk; kenar boşluklarını kırp."""
    return re.sub(r"\s+", " ", text or "").strip()


def normalize_text(text: str) -> str:
    """Çıkarım öncesi standart temizleme.

    - HTML temizliği
    - görünmez/zero-width karakter temizliği
    - tutarlı yüzde/para işaretleri (ör. NBSP → boşluk)
    - boşluk normalizasyonu
    Not: TR karakterler (ş,ç,ğ,ü,ö,ı,İ) KORUNUR — sadeleştirme yalnızca slug için.
    """
    if not text:
        return ""
    text = strip_html(text)
    text = text.replace(" ", " ").replace("​", "")
    text = text.replace("’", "'").replace("“", '"').replace("”", '"')
    return normalize_whitespace(text)


def split_sentences(text: str) -> list[str]:
    """TR-duyarlı basit cümle segmentasyonu.

    Kısaltmalardan (vb., örn.) ve ondalık sayılardan (%2,05 / 1.500) sonra
    yanlış bölmeyi engeller.
    """
    text = normalize_whitespace(text)
    if not text:
        return []
    # cümle sonu adayları: . ! ? sonrası boşluk + büyük harf/rakam
    candidates = re.split(r"(?<=[.!?])\s+(?=[A-ZÇĞİÖŞÜ0-9])", text)
    out: list[str] = []
    for c in candidates:
        c = c.strip()
        if not c:
            continue
        # önceki parça bir kısaltmayla bitiyorsa birleştir
        if out:
            last_word = re.split(r"[\s.]", out[-1].rstrip("."))[-1].lower()
            prev_token = out[-1].rstrip().rstrip(".").split()[-1].lower() if out[-1].split() else ""
            if prev_token in _ABBREV or last_word in _ABBREV:
                out[-1] = out[-1] + " " + c
                continue
        out.append(c)
    return out


def slugify_tr(text: str) -> str:
    """TR metni kebab-case slug'a çevirir (ş→s, ç→c, ğ→g, ü→u, ö→o, ı/İ→i)."""
    table = str.maketrans({
        "ş": "s", "Ş": "s", "ç": "c", "Ç": "c", "ğ": "g", "Ğ": "g",
        "ü": "u", "Ü": "u", "ö": "o", "Ö": "o", "ı": "i", "İ": "i",
    })
    s = (text or "").translate(table)
    # kalan aksanlı harfleri sadeleştir (â→a, î→i, û→u, é→e ...)
    s = "".join(c for c in unicodedata.normalize("NFKD", s)
                if not unicodedata.combining(c))
    s = s.lower()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s
