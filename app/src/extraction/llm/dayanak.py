"""LLM çıkarımı için İKİ KAPI: sayı metinde var mı, değer doğru alana mı yazıldı.

İlgili: extractor.py (kapıların uygulandığı çıkarım yolu)
        ../../../scripts/llm_bosluk_doldur.py (kural boşluklarını dolduran koşum)
        ../../chatbot/dayanak.py (aynı disiplinin cevap tarafındaki karşılığı)
        CLAUDE.md §3 (kural birincil, LLM yalnız boşluk), §19 (halüsinasyon yasağı)

## Niçin İKİ kapı, biri yetmiyor

Ölçüldü (2026-08-24, 40 belgelik örneklem, EVREN `llm-large`):

    "%0.4 Aval komisyon oranı"  →  kar_payi_orani = 0.4

Sayı metinde GERÇEKTEN var, yani bir halüsinasyon değil. Ama aval komisyonu
kâr payı oranı DEĞİLDİR; değer doğru okunmuş, yanlış alana yazılmış. Tek kapı
(dayanak) bunu geçirir.

Bu yüzden iki ayrı soru, iki ayrı kapı:

    `metinde_dogrula`   → sayı uydurulmuş mu?      (halüsinasyon kapısı)
    `alan_uygun`        → doğru alana mı yazıldı?  (semantik kapı)

İkisi de geçmeyen değer DB'ye YAZILMAZ. Reddedilen değer sessizce kaybolmaz:
koşum betiği hangi kapıda kaç değer düştüğünü raporlar.

## Sözcükle yazılmış büyüklükler

*"1 milyar TL limitli"* → `1000000000` DOĞRU bir çevrimdir ama sayısal biçimi
metinde geçmez. İlk ölçümde bu yanlış biçimde "uydurma" sayıldı (#642); kapı
`bin/milyon/milyar` çarpanlarını da deniyor.
"""

from __future__ import annotations

import unicodedata
from typing import Any, Iterable, Optional

#: Sözcükle yazılan büyüklükler.
CARPANLAR = {"bin": 1_000, "milyon": 1_000_000, "milyar": 1_000_000_000}

#: Sayı taşımayan, dolayısıyla dayanak kapısının konusu olmayan anahtarlar.
_SAYISAL_OLMAYAN = frozenset({"currency", "unit", "has_fee", "para_birimi"})

#: Kanıt penceresinde geçtiğinde değerin O ALANA ait OLMADIĞINI gösteren izler.
#:
#: Liste DAR tutuluyor: her iz, o alanın tanımıyla gerçekten çelişen bir
#: büyüklüğü adlandırıyor. Geniş bir liste doğru değerleri de düşürürdü ve
#: kapı "LLM'i sustur" hâline gelirdi.
#:
#: `kar_payi_orani` için: vergi/fon kesintileri (KKDF, BSMV, stopaj), ücret ve
#: masraf kalemleri (tahsis, ekspertiz, sigorta, komisyon, aval), gecikme/
#: temerrüt oranları ve pazarlama oranları (indirim, puan, iade) kâr payı
#: oranı DEĞİLDİR.
YASAK_IZLER: dict[str, tuple[str, ...]] = {
    "kar_payi_orani": (
        "aval", "komisyon", "kkdf", "bsmv", "stopaj", "vergi", "harc",
        "indirim", "puan", "iade", "tahsis", "ekspertiz", "sigorta",
        "gecikme", "temerrut", "kur", "enflasyon",
    ),
    "finansman_tutari": (
        "odul", "iade", "puan", "hediye", "cekilis", "kkdf", "bsmv",
        "ciro", "bakiye",
    ),
}


def tr_katla(s: Optional[str]) -> str:
    """Türkçe aksanları düşürüp küçültür (arama için)."""
    s = unicodedata.normalize("NFKD", s or "")
    return "".join(c for c in s if not unicodedata.combining(c)).lower()


def sayilari_topla(deger: Any) -> list[float]:
    """Değerin içindeki TÜM sayıları verir; sözlük ve liste dallarına iner.

    Aralık değerlerinin (`{"min": 0, "max": 4.82}`) her iki ucu ayrı ayrı
    döner: üst sınır uydurmaysa aralığın kendisi yanlıştır, yani bir ucun
    doğrulanması yetmez.
    """
    if deger is None or isinstance(deger, bool):
        return []
    if isinstance(deger, (int, float)):
        return [float(deger)]
    if isinstance(deger, str):
        try:
            return [float(deger.replace(".", "").replace(",", "."))]
        except ValueError:
            return []
    if isinstance(deger, dict):
        return [x for k, v in deger.items()
                if k not in _SAYISAL_OLMAYAN for x in sayilari_topla(v)]
    if isinstance(deger, (list, tuple)):
        return [x for v in deger for x in sayilari_topla(v)]
    return []


def _sozcukle_gecer(sayi: float, metin_kat: str) -> bool:
    """'1 milyar TL' → 1000000000, '2,5 milyon TL' → 2500000.

    Çarpanın TAM KATI olması ŞART DEĞİL: "2,5 milyon" geçerli bir yazımdır ve
    ilk sürüm `sayi % carpan` kontrolü yüzünden onu kaçırıyordu (testle
    yakalandı). Kat aralığı 0,1–999 ile sınırlı: dışında kalan bir eşleşme
    ("0,000001 milyar") metindeki sözcüğe rastgele denk gelmiş olurdu.
    """
    for ad, carpan in CARPANLAR.items():
        if ad not in metin_kat or sayi <= 0:
            continue
        kat = sayi / carpan
        if not (0.1 <= kat < 1000):
            continue
        t = f"{round(kat, 3):g}"
        if f"{t} {ad}" in metin_kat or f"{t.replace('.', ',')} {ad}" in metin_kat:
            return True
    return False


def _sayi_gecer(sayi: float, metin_kat: str) -> bool:
    adaylar: set[str] = set()
    for x in {sayi, round(sayi, 2)}:
        t = f"{x:g}"
        adaylar.add(t)
        adaylar.add(t.replace(".", ","))
        if x == int(x):
            tam = int(x)
            adaylar.add(str(tam))
            if abs(tam) >= 1000:
                # 100000 hem "100.000" hem "100,000" yazılabiliyor
                adaylar.add(f"{tam:,}".replace(",", "."))
                adaylar.add(f"{tam:,}")
    return (any(a in metin_kat for a in adaylar)
            or _sozcukle_gecer(sayi, metin_kat))


def metinde_dogrula(deger: Any, metin: str) -> Optional[bool]:
    """Değerin bütün sayıları metinde geçiyor mu?

    `None` = değerde sayı yok, kapı UYGULANAMAZ (ör. serbest metin listesi).
    Çağıran bunu "geçti" saymamalı; o alanlar bu kapının konusu değildir.
    """
    sayilar = sayilari_topla(deger)
    if not sayilar:
        return None
    m = tr_katla(metin)
    return all(_sayi_gecer(s, m) for s in sayilar)


def alan_uygun(alan: str, kanit: Optional[str]) -> bool:
    """Kanıt penceresi alanla çelişmiyor mu? `False` → değer reddedilir.

    Alan için iz listesi tanımlı DEĞİLSE `True` döner: bu kapı yalnız ölçülmüş
    karışma vakaları için var, tanımsız bir alanı sessizce elemek yeni bir
    kayıp üretirdi.
    """
    izler = YASAK_IZLER.get(alan)
    if not izler:
        return True
    k = tr_katla(kanit or "")
    return not any(iz in k for iz in izler)


def kabul_edilir(alan: str, deger: Any, kanit: Optional[str],
                 metin: str) -> tuple[bool, str]:
    """(kabul, gerekçe). İki kapıdan da geçmeyen değer DB'ye yazılmaz."""
    dayanak = metinde_dogrula(deger, metin)
    if dayanak is False:
        return False, "dayanaksiz"
    if dayanak is None:
        return False, "sayisal-degil"
    if not alan_uygun(alan, kanit):
        return False, "yanlis-alan"
    return True, "kabul"


def ozet(kayitlar: Iterable[tuple[bool, str]]) -> dict[str, int]:
    """Gerekçe sayaçları — reddedilenler sessizce kaybolmasın."""
    sayac: dict[str, int] = {}
    for _, gerekce in kayitlar:
        sayac[gerekce] = sayac.get(gerekce, 0) + 1
    return sayac
