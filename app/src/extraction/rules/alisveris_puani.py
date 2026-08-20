"""Alışveriş puanı çıkarımı — `extract.py` bölünmesinde AYRI modül.

## Neden bu sınır burada

`extract_alisveris_puani` kendi tetikleyici taraması (`_puan_tetikleyicileri`),
gezinme/SSS süzgeci (`_PUAN_KROM_RE`) ve oran/adet ikili şeması ile
`odul_indirim.py`den yeterince farklı; ikisi arasında hiçbir fonksiyon
paylaşılmıyor, yalnız `_ortak._SAYI_BASI` ortak. `_PUAN_SAYI_RE` bilerek
public: `tests/test_kesik_sayi.py` onu doğrudan içe aktarıyor.
"""

from __future__ import annotations

import re
from typing import Optional

from ...normalization import normalize as N
from ...schemas import ExtractedField
from ._ortak import _SAYI_BASI, _field, _window

# Markalı puan birimleri. Bunlar sözlükte yoksa katılım bankalarının ödül
# kampanyaları sistematik olarak kaçırılır (ölçüm: ParafPara belgesi `null`
# dönüyordu). `puan` en sona yazıldı: daha özgül alternatifler önce denenmeli.
_PUAN_TRIGGER_RE = re.compile(
    r"(chip[\s-]*para|parafpara|maximiles|worldpuan|world\s*puan|"
    r"bonus\s*puan\w*|alışveriş\s*puan\w*|alisveris\s*puan\w*|"
    r"puan\s*iade\w*|puan|\bmil\b)", re.IGNORECASE)

# Gezinme/SSS bağlantısı kalıbı — ödül bildirimi değil.
_PUAN_KROM_RE = re.compile(
    r"nedir|nas[ıi]l\s|ne\s*i[şs]e\s*yarar|kredi\s*notu|s[ıi]k[çc]a\s*sorulan",
    re.IGNORECASE)

# Sayı bir puan/para birimine KOMŞU olmalı; birim opsiyonel değil.
#
# Sayı RAKAMLA BİTMEK zorunda (`\d[\d.,]*\d|\d`). Ölçülen yanlış pozitif:
# sözleşme metnindeki "24. Puan Uygulaması 24.1..." madde numarası. Eski
# `[\d.,]*` sonu serbest bıraktığı için "24." yutuluyor, ardından `\s*` boşluğu
# yiyor ve madde numarası 24 puanlık bir ödül sanılıyordu. Rakamla bitme şartı
# `1.500 TL` gibi binlik ayıraçlı tutarları bozmaz — orada nokta sayının içinde.
_PUAN_SAYI_RE = re.compile(
    rf"{_SAYI_BASI}(\d[\d.,]*\d|\d)\s*(?:adet\s*)?"
    r"(?:chip[\s-]*para|parafpara|maximiles|worldpuan|puan|\bmil\b|tl|₺)",
    re.IGNORECASE)

#: Puan bağlamındaki oran deseni. `_SAYI_BASI` ile sayının ortasından
#: başlayamaz; modül düzeyinde derlenir çünkü belge başına onlarca kez koşar.
_PUAN_ORAN_RE = re.compile(
    rf"%\s*{_SAYI_BASI}(\d[\d.,]*)|{_SAYI_BASI}(\d[\d.,]*)\s*%")


#: NAKİT İADE (cashback) — kılavuz §4 gereği `alisveris_puani`, `indirim_orani`
#: DEĞİL: *"Sayılmaz: kâr payı oranı, puan/iade oranı (o `alisveris_puani`)"*.
#:
#: Ölçülen kayıp (gold.v2): iki kayıt yalnız bu tetikleyici yokluğundan
#: düşüyordu —
#:     "A101'de her alışverişte %3'e varan nakit iade!"        -> rate 3,0
#:     "…Pegasus harcamalarında %50'ye varan iade kazanılabilir" -> rate 50,0
#:
#: TETİKLEYİCİ YALNIZ ORAN BİÇİMİNİ AÇAR. Sebep ölçülmüş bir tehlike:
#: "iade" Türkçede ödülü DEĞİL geri dönüşü de anlatıyor ("Alışverişin
#: iptal/iade edilmesi durumunda…"). Adet biçimi de açılsaydı, o cümlelerin
#: ±30 karakterindeki herhangi bir TL tutarı puan sanılırdı. Oran biçiminde
#: bu risk yok: bir yüzde işareti şart.
#:
#: ÖLÇÜLDÜ (1.782 belge, 2026-08-20): kapı 28 belgede YENİ değer, 3 belgede
#: değişiklik üretiyor. Elle bakıldı — 27 yeni değer gerçek nakit iade oranı
#: ("%18'i kadar nakit iade", "%75 Nakit İade Fırsatı", "%5 iade kazan"),
#: 3 değişiklik de doğru yönde (eskiden komşu cümleden 100 "puan" devşiriliyor,
#: artık "işleme %50 iade" okunuyor). TEK çöp bir ücret tarifesiydi:
#:     "Çek İade Ücreti 0% 0% 0% …"  -> rate 0,0
#: `_IADE_UCRETI_RE` tam o sınıfı eler: "iade ÜCRETİ" bir masraftır, ödül
#: değil. Kalan oran: 30 doğru / 0 çöp.
_IADE_TRIGGER_RE = re.compile(r"(nakit\s*iade|para\s*iade|iade)",
                              re.IGNORECASE)
_IADE_UCRETI_RE = re.compile(
    r"iade\s*(?:[üu]cret|masraf|komisyon|bedel)", re.IGNORECASE)


def _puan_tetikleyicileri(text: str) -> list[tuple["re.Match[str]", bool]]:
    """(eşleşme, yalnız_oran) çiftleri — BELGE SIRASINDA.

    Sıra korunur çünkü `extract_alisveris_puani` ilk geçerli adayı döndürüyor
    ve sıra değişirse sonuç yazım sırasına bağlı hâle gelirdi (P4 değişmezi).
    """
    adaylar: list[tuple[re.Match[str], bool]] = [
        (m, False) for m in _PUAN_TRIGGER_RE.finditer(text)]
    for m in _IADE_TRIGGER_RE.finditer(text):
        if _IADE_UCRETI_RE.search(text[m.start(): m.end() + 20]):
            continue
        adaylar.append((m, True))
    adaylar.sort(key=lambda p: p[0].start())
    return adaylar


def extract_alisveris_puani(text: str) -> Optional[ExtractedField]:
    """Alışveriş puanı — ORAN ya da ADET olabilir, ikisi farklı kanonik şekil.

        "%5 puan iadesi"      -> {"kind": "rate",   "value": 5.0}
        "1.000 chip-para"     -> {"kind": "points", "value": 1000.0}

    İki şekli ayrı tutmak §5.7 karşılaştırmasında elmayla armutun
    kıyaslanmasını engeller (bkz. CLAUDE.md §17 adil kıyas garantisi).

    İki ölçülmüş halüsinasyon mekanizması burada kapatıldı (19 halüsinasyonun
    2'si): (a) site kromundaki "Kredi Notu (Kredi Puanı) Nedir?" gezinme
    bağlantısı ödül sanılıyordu, (b) sayı biriminin opsiyonel olması yüzünden
    ±30 karakterdeki *herhangi* bir sayı kabul ediliyordu. Ayrıca ilk eşleşme
    yerine tüm tetikleyiciler taranıyor — kromdaki bir eşleşme gerçek ödülü
    artık gölgelemiyor.
    """
    for tm, yalniz_oran in _puan_tetikleyicileri(text):
        # Site kromu / SSS bağlantısı ödül DEĞİLDİR. Ölçülen halüsinasyon:
        # "3D Secure Nedir, Ne İşe Yarar? Kredi Notu (Kredi Puanı) Nedir?" —
        # iki Türkiye Finans sayfasında `puan` sözcüğünün geçtiği TEK yer buydu
        # ve ikisinde de ilgisiz bir sayı (10.0) üretiliyordu.
        cevre = text[max(0, tm.start() - 40): min(len(text), tm.end() + 40)]
        if _PUAN_KROM_RE.search(cevre):
            continue

        # Arama METNİN KENDİSİNDE, konum sınırlarıyla — dilim ALINMAZ.
        # Gerekçe `extract_odul_miktari` içinde ve `_SAYI_BASI` yorumunda:
        # dilimin sol kenarı bir sayının ortasına düştüğünde desen sayının
        # kuyruğunu eşleştiriyor ("5000" -> "000") ve değer sessizce çöküyor.
        # Burada henüz ölçülmüş bir vaka yok; kusur LATENT ve aynı kalıptan.
        ctx_s = max(0, tm.start() - 30)
        ctx_e = min(len(text), tm.end() + 30)

        rate = _PUAN_ORAN_RE.search(text, ctx_s, ctx_e)
        if rate:
            off = rate.start(1) if rate.group(1) else rate.start(2)
            end = rate.end(1) if rate.group(1) else rate.end(2)
            val = N.parse_tr_number(text[off:end])
            if val is None:
                continue
            canon = {"kind": "rate", "value": val}
        elif yalniz_oran:
            # `iade` çapası ADET biçimini açmaz (gerekçe: `_IADE_TRIGGER_RE`).
            continue
        else:
            # Sayı tetikleyiciye KOMŞU olmak zorunda. Eskiden birim grubu
            # opsiyoneldi (`(?:chip|puan)?`), yani ±30 karakterdeki herhangi bir
            # sayı kabul ediliyordu — halüsinasyonun ikinci mekanizması buydu.
            num = _PUAN_SAYI_RE.search(text, ctx_s, ctx_e)
            if not num:
                continue
            off, end = num.start(1), num.end(1)
            val = N.parse_tr_number(text[off:end])
            if val is None:
                continue
            canon = {"kind": "points", "value": val}

        s, e = off, end
        return _field("alisveris_puani", text[s:e], canon, _window(text, s, e),
                      span_start=s, span_end=e,
                      trigger_distance=abs(s - tm.start()))
    return None
