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

# TR-doğru küçük harf: Python'un varsayılanı bu iki harfte yanlış davranır.
_TR_LOWER = str.maketrans({"I": "ı", "İ": "i"})

# TR-doğru büyük harf (simetrik): 'i' → 'İ', 'ı' → 'I'.
_TR_UPPER = str.maketrans({"i": "İ", "ı": "I"})

# Diakritik sadeleştirme (tr_fold_ascii için; slugify_tr ile aynı harita)
_TR_ASCII = str.maketrans({
    "ş": "s", "ç": "c", "ğ": "g", "ü": "u", "ö": "o", "ı": "i", "â": "a",
    "î": "i", "û": "u",
})


def tr_fold(text: str) -> str:
    """Türkçe-doğru küçük harfe çevirme (case folding).

    Python'un `str.lower()` metodu Türkçe için HATALIDIR ve bu hata sistemi
    sessizce bozar — banka sitelerindeki başlıklar büyük harflidir:

        'TAŞIT FİNANSMANI'.lower()  -> 'taşit fi̇nansmani'
                                          ^          ^^
        I → i  (olması gereken: ı)   İ → i + U+0307 (birleşen nokta)

    Sonuç: 'taşıt' anahtar kelimesi 'taşit' içinde bulunamaz, sınıflandırma
    ve tetikleyici eşleşmesi çöker. Bu fonksiyon önce iki sorunlu harfi
    çevirir, sonra kalanı standart `lower()`'a bırakır.

    >>> tr_fold('TAŞIT FİNANSMANI')
    'taşıt finansmanı'
    """
    if not text:
        return ""
    return text.translate(_TR_LOWER).lower()


def tr_upper(text: str) -> str:
    """Türkçe-doğru BÜYÜK harfe çevirme — `tr_fold`'un simetriği.

    Python'un `str.upper()` metodu da Türkçe için hatalıdır:
        'ihtiyaç'.upper() -> 'IHTIYAÇ'   (i → I, olması gereken İ)

    Banka sayfalarındaki gerçek ALL-CAPS başlıkları üretmek için gerekir;
    değişmez (invariant) testleri bu fonksiyonla sentetik büyük-harf varyantı
    üretip çıkarımın değişmediğini doğrular.

    >>> tr_upper('ihtiyaç finansmanı')
    'İHTİYAÇ FİNANSMANI'
    """
    if not text:
        return ""
    return text.translate(_TR_UPPER).upper()


def tr_fold_ascii(text: str) -> str:
    """tr_fold + diakritik sadeleştirme — diakritiksiz yazımları yakalamak için.

    Kullanıcılar ve bazı banka sayfaları 'kar payi orani' diye yazar; bu
    fonksiyon hem onu hem 'Kâr Payı Oranı'nı aynı forma indirger.

    >>> tr_fold_ascii('Kâr Payı Oranı') == tr_fold_ascii('KAR PAYI ORANI')
    True
    """
    s = tr_fold(text).translate(_TR_ASCII)
    return "".join(c for c in unicodedata.normalize("NFKD", s)
                   if not unicodedata.combining(c))


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
    text = text.replace(" ", " ").replace("\u200b", "")
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
    # Cümle sonu adayları: . ! ? + boşluk + harf/rakam.
    #
    # KÜÇÜK HARF DE KABUL EDİLİR. Önceden yalnız büyük harf/rakam aranıyordu;
    # bu, küçük harfle başlayan cümleleri kaçırıyordu ve 291 belgelik gerçek
    # korpusta değişmez denetimiyle yakalandı:
    #   "...belirtilmesi gerekmektedir. www.cartersoshkosh.com.tr web
    #    sitesinden yapılan alışverişlerde geçerlidir."
    # 'www' küçük harf olduğu için bölünmüyor, iki cümle tek koşul olarak
    # çıkıyordu. Aynı sorun 'c.Performans' gibi liste imlerinde de var.
    #
    # Aşırı bölme riski yok: aşağıdaki kısaltma birleştirme mantığı
    # (_ABBREV) yanlış bölmeleri geri alıyor. Ondalık sayılar da güvende,
    # çünkü bölme için aradaki BOŞLUK (\s+) şart — "1.500,00"da boşluk yok.
    candidates = re.split(
        r"(?<=[.!?])\s+(?=[A-Za-zÇĞİÖŞÜçğıöşü0-9])", text)
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
