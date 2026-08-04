"""Kural tabanlı (deterministik) alan çıkarımı — BİRİNCİL katman.

İlgili kararlar:
- ../../decisions/ner-fine-tune-yerine-kural-few-shot.md  (kurallar birincil)
- ../../concepts/bilgi-cikarimi.md

Her çıkarıcı bir ExtractedField döndürür: canonical_value + confidence + source_span.
Bulamazsa alanı hiç üretmez (None döner) — boşluğu LLM katmanı doldurur.
Halüsinasyon yasağı: değer uydurma.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

from ...normalization import normalize as N
from ...preprocessing.clean import split_sentences, tr_fold
from ...schemas import ExtractedField, Extractor
from . import confidence as C
from .synonyms import NEGATION_RE

# Kural katmanının güveni yüksektir (deterministik); LLM'inkinden ayrışsın diye 0.95.
_RULE_CONF = 0.95


def _window(text: str, start: int, end: int, pad: int = 40) -> str:
    """source_span için eşleşme etrafından bir pencere döndürür."""
    a = max(0, start - pad)
    b = min(len(text), end + pad)
    return text[a:b].strip()


def _field(
    name: str,
    raw: str,
    canon,
    span: str,
    conf: Optional[float] = None,
    *,
    span_start: Optional[int] = None,
    span_end: Optional[int] = None,
    trigger_distance: Optional[int] = None,
    candidate_count: int = 1,
):
    """ExtractedField üretir; güven verilmezse kanıt sinyallerinden hesaplanır.

    `conf` açıkça verilirse (geriye uyumluluk) o kullanılır; verilmezse
    `confidence.score()` tetikleyici yakınlığı + makullük + belirsizlikten
    gerçek bir skor üretir. Bkz. rules/confidence.py.
    """
    if conf is not None:
        value, csource = (conf if canon is not None else 0.0), "constant"
    else:
        value, _reason = C.score(
            name, canon,
            trigger_distance=trigger_distance,
            candidate_count=candidate_count,
        )
        csource = "rule_heuristic"
    return ExtractedField(
        field_name=name,
        raw_value=raw,
        canonical_value=canon,
        confidence=value,
        source_span=span,
        extractor=Extractor.RULE,
        span_start=span_start,
        span_end=span_end,
        confidence_source=csource,
    )


# --------------------------------------------------------------------------- #
# Tekil alan çıkarıcılar
# --------------------------------------------------------------------------- #
# ORAN ANAHTAR KELİMEDEN ÖNCE GELDİĞİNDE.
#
# Şartname §5.2'nin manşet örneği birebir şu: **"%2,05 kâr payı oranı"** —
# yani sayı önce, anahtar kelime sonra. Şartnamenin A Bankası senaryosu da
# aynı yapıda: "özel %1,89 kâr payı oranı ile 120 aya kadar konut finansmanı".
#
# İleri yönlü desen bu biçimi iki türlü ıskalıyordu:
#   "%2,05 kâr payı oranı"                  -> hiçbir şey bulunmuyordu
#   "%1,89 kâr payı oranı ile 120 aya kadar" -> **120.0** döndürüyordu,
#                                               yani VADEYİ oran sanıyordu
# İkincisi sessizce yanlış değer üreten sınıftan ve en ağırlıklı alanda
# (kar_payi_orani, Model Başarısı %30) oluyordu.
#
# Geri yönlü arama SIKI tutulur, iki şartla:
#   1. `%` işareti ZORUNLU — çıplak sayı ("120 ay kâr payı") oran sayılmaz.
#   2. Boşluk en fazla 3 karakter — araya kelime giremez. Aksi halde
#      "%15 indirim ve kâr payı oranı %1,89" cümlesinde indirim oranı
#      kâr payı diye okunurdu.
# Bir sayıyı ORAN OLMAKTAN çıkaran birim sözcükleri — Türkçe ekleriyle.
#
# Türkçe sondan eklemeli: "36 ay", "36 aya kadar", "36 aylık", "36 ayda".
# Ek desteği olmadan `ay\b` yalnız çıplak "ay"ı yakalar; korpusta gerçek
# vakalar "aya kadar vade" ve "aylık periyotlarda" biçimindeydi ve
# 36 ile 1 sayıları kâr payı ORANI diye okunuyordu.
# `extract_vade` aynı ek listesini kullanıyor; tek yerde tutmak ikisinin
# birbirinden ayrışmasını engeller.
_BIRIM_SONEKLI = (
    r"(?:ay|y[ıi]l|sene|taksit|adet|tl|₺)"
    r"(?:a|e|da|de|ta|te|dan|den|tan|ten|[ıi]|l[ıi]k|lar|ler)?\b"
)

# "kâr payı PAYLAŞIM oranı" — bambaşka bir kavram.
# Katılma hesaplarında banka ile müşteri kârı bölüşür: "%55'e %45".
# Bu bir finansman maliyeti değil, bir bölüşüm oranıdır; `kar_payi_orani`
# alanına yazılırsa karşılaştırma tablosunda o bankayı %55 "oranla" en
# pahalı gösterir. Korpusta 3 belgede bu şekilde okunuyordu.
_PAYLASIM_ORANI_RE = re.compile(
    r"(?:kâr|kar)\s*pay[ıi]\s*payla[şs][ıi]m\s*oran[ıi]", re.IGNORECASE)

_KAR_PAYI_ONCE_RE = re.compile(
    r"(%\s*\d[\d.,]*)\s{0,3}(?:kâr|kar)\s*pay[ıi](?:\s*oran[ıi])?",
    re.IGNORECASE,
)

# Değerden SONRA gelip onu kâr payı oranı OLMAKTAN çıkaran ifadeler.
#
# `_PAYLASIM_ORANI_RE` belge düzeyinde çalışır; bu ise DEĞERE ÖZGÜdür — çünkü
# aynı belgede hem gerçek kâr payı oranı hem yabancı bir oran bulunabilir
# ("kâr payı oranı %1,89, devlet katkısı %20"). O yüzden yalnız İLGİLİ eşleşme
# reddedilir, belge tamamen atılmaz.
#
# Ölçüm (2026-08-03, 1684 belgelik korpus): `kar_payi_orani` üreten 64 belgenin
# 7'sinde (%11) değer YABANCI bir kavrama aitti:
#   6 belge: "hem kâr payı hem de %20'ye kadar DEVLET KATKISIYLA konut sahibi"
#            -> %20 devlet katkı oranıdır, finansman kâr payı oranı değil.
#   1 belge: "finansmanın kâr payının 10 PUANLIK kısmı KOSGEB tarafından"
#            -> 10, oranın kendisi değil devlet desteğiyle karşılanan PUAN payı.
# İkisi de karşılaştırma tablosuna girdiğinde o bankayı yanlış konumlandırır.
_YABANCI_KAVRAM_RE = re.compile(
    r"\s*(?:['’]?\s*(?:ye|ya|e|a)?\s*kadar\s*)?"
    r"(?:devlet\s*(?:katk|destek|deste[ğg])|puanl[ıi]k)",
    re.IGNORECASE,
)
# Değerin sağında bu kadar karakter içinde yabancı kavram aranır. 30 karakter
# "'ye kadar devlet katkısıyla" ifadesini kapsar, sonraki cümleye taşmaz.
_YABANCI_KAVRAM_PENCERE = 30


def _yabanci_kavram_takip_ediyor(text: str, value_end: int) -> bool:
    """Değerden hemen sonra BAŞKA bir kavramın adı geliyor mu?"""
    return bool(_YABANCI_KAVRAM_RE.match(
        text[value_end:value_end + _YABANCI_KAVRAM_PENCERE]))


def extract_kar_payi(text: str) -> Optional[ExtractedField]:
    """Kâr payı oranı: '... kâr payı oranı %1,99 ...' veya '%1,99 kâr payı'.

    İki yön de denenir. ÖNCE geri yönlü bakılır: `%` ile işaretlenmiş ve
    anahtar kelimeye bitişik bir sayı, anahtar kelimeden sonra gelen
    işaretsiz bir sayıdan daha güçlü kanıttır. Bu sıra olmadan
    "%1,89 kâr payı oranı ile 120 aya kadar" ifadesi 120 döndürüyordu.
    """
    if _PAYLASIM_ORANI_RE.search(text):
        # "kâr payı PAYLAŞIM oranı %55'e %45" — bu, banka ile müşteri
        # arasındaki kâr BÖLÜŞÜMÜ, finansman kâr payı oranı DEĞİL. İkisini
        # aynı alana yazmak karşılaştırmayı bozar: %55 bir "oran" olarak
        # tabloya girip o bankayı en pahalı gösterirdi.
        return None
    # Yabancı kavram takip eden eşleşmeler ATLANIR, ilk eşleşmede durulmaz:
    # aynı belgede gerçek kâr payı oranı daha sonra gelebilir.
    for onceki in _KAR_PAYI_ONCE_RE.finditer(text):
        s, e = onceki.span(1)
        if _yabanci_kavram_takip_ediyor(text, onceki.end()):
            continue
        raw = onceki.group(1)
        return _field(
            "kar_payi_orani", raw, N.normalize_rate(raw),
            _window(text, onceki.start(), onceki.end()),
            span_start=s, span_end=e,
            trigger_distance=0,          # bitişik: en güçlü kanıt
            candidate_count=len(_KAR_PAYI_ONCE_RE.findall(text)),
        )
    return _extract_kar_payi_ileri(text)


def _extract_kar_payi_ileri(text: str) -> Optional[ExtractedField]:
    """Kâr payı oranı, değer anahtar kelimeden SONRA geldiğinde."""
    # Aralık ikinci operandı bir BİRİM sözcüğü ile devam ediyorsa aralık DEĞİLDİR:
    #   "kâr payı oranı %1,89 ile 120 aya kadar vade"
    # buradaki "ile" bağlaçtır, aralık ayırıcı değil. Negatif ileri-bakış olmadan
    # sistem bunu {min: 1.89, max: 120.0} diye okuyup karşılaştırma tablosuna
    # bir VADEYİ oran üst sınırı olarak yazıyordu.
    #
    # Aynı birim kontrolü TEK DEĞER için de gerekli. Eskiden yalnız aralığın
    # ikinci operandına uygulanıyordu; tek değer korumasızdı ve korpusta
    # şu iki vakayı üretiyordu:
    #   "...36 ay vadeli faizsiz finansman..."          -> 36.0 (VADE)
    #   "...kâr payı ödemelerini ... 1 aylık, 3 aylık"  -> 1.0  (PERİYOT)
    # İkisi de oran değil. `(?![\d.,])` burada da şart: onsuz regex geri
    # izleyip "36"dan yalnız "3"ü alarak birim kontrolünü atlatır.
    pat = re.compile(
        r"(kâr|kar)\s*pay[ıi]\s*(oran[ıi])?[^%\d]{0,15}"
        r"(%?\s*\d[\d.,]*(?![\d.,])\s*%?"
        r"(?:\s*(?:-|–|ile|ila)\s*%?\s*"
        r"\d[\d.,]*(?![\d.,])\s*%?"
        rf"(?!\s*{_BIRIM_SONEKLI})"
        r")?)"
        rf"(?!\s*{_BIRIM_SONEKLI})",
        re.IGNORECASE,
    )
    for m in pat.finditer(text):
        s, e = m.span(3)
        # Değeri yabancı bir kavram takip ediyorsa bu eşleşme reddedilir ve
        # aramaya devam edilir (gerekçe: `_YABANCI_KAVRAM_RE`).
        if _yabanci_kavram_takip_ediyor(text, e):
            continue
        raw = m.group(3)
        canon = N.normalize_rate(raw)
        return _field(
            "kar_payi_orani", raw, canon, _window(text, m.start(), m.end()),
            span_start=s, span_end=e,
            # "kâr payı oranı" bitişi ile değerin başı arası
            trigger_distance=s - m.end(1),
            candidate_count=len(pat.findall(text)),
        )
    return None


def extract_vade(text: str) -> Optional[ExtractedField]:
    """Vade: '120 aya kadar', '36 ay vade', '1 yıl'.

    Zaman-koşullu ifade tuzağı ('ilk 6 ay ödemesiz') gerçek vade değildir; bu
    yüzden 'vade' sözcüğüne yakın eşleşme tercih edilir
    (bkz. ../../decisions/zor-anlama-vakalari-merkezi.md).
    """
    pat = re.compile(
        r"(\d[\d.,]*)\s*(ay|yıl|yil|sene)(?:a|da|ta|dan|tan|ı|i|lık|lik)?\b",
        re.IGNORECASE,
    )
    matches = list(pat.finditer(text))
    if not matches:
        return None
    # tr_fold: 'İLK 6 AY' -> .lower() 'i̇lk' promo tespitini kaçırıyordu.
    # Katlama karakter sayısını korur, bu yüzden offset'ler text ile hizalı kalır.
    low = tr_fold(text)
    vade_pos = [mm.start() for mm in re.finditer(r"vade", low)]

    def score(m):
        # "ilk N ay" gibi promosyon dönemleri gerçek vade değildir → geri it
        pre = low[max(0, m.start() - 8): m.start()]
        promo = "ilk" in pre
        dist = min((abs(m.start() - v) for v in vade_pos), default=10 ** 6)
        return (promo, dist)

    chosen = min(matches, key=score)
    raw = chosen.group(0)
    s, e = chosen.span()
    canon = N.normalize_term_months(raw)
    dist = min((abs(s - v) for v in vade_pos), default=None)
    return _field(
        "vade_ay", raw, canon, _window(text, s, e),
        span_start=s, span_end=e,
        trigger_distance=dist,
        candidate_count=len(matches),
    )


def extract_tutar(text: str) -> Optional[ExtractedField]:
    """Finansman tutarı: 'finansman ... 500.000 TL'."""
    pat = re.compile(
        r"(finansman|kredi|tutar|limit)[^\d]{0,20}(\d[\d.,]*\s*(?:tl|₺|try|türk\s*liras[ıi]))",
        re.IGNORECASE,
    )
    m = pat.search(text)
    if not m:
        return None
    raw = m.group(2)
    s, e = m.span(2)
    canon = N.normalize_money(raw)
    return _field(
        "finansman_tutari", raw, canon, _window(text, m.start(), m.end()),
        span_start=s, span_end=e,
        trigger_distance=s - m.end(1),
        candidate_count=len(pat.findall(text)),
    )


def extract_taksit(text: str) -> Optional[ExtractedField]:
    """Taksit sayısı: '12 taksit', 'taksit sayısı 36'."""
    pat = re.compile(r"(\d{1,3})\s*taksit|taksit\s*(?:say[ıi]s[ıi])?\s*[:\-]?\s*(\d{1,3})",
                     re.IGNORECASE)
    m = pat.search(text)
    if not m:
        return None
    num = m.group(1) or m.group(2)
    try:
        canon = int(num)
    except (TypeError, ValueError):
        canon = None
    s, e = m.span()
    return _field(
        "taksit_sayisi", m.group(0), canon, _window(text, s, e),
        span_start=s, span_end=e,
        # "taksit" sözcüğü eşleşmenin kendi içinde → bitişik kabul edilir
        trigger_distance=0,
        candidate_count=len(pat.findall(text)),
    )


# Oran tablosu sütun başlıkları. Bir ücret tetikleyicisinden sonra bunlardan
# biri geliyorsa, ardından gelen sayı BAŞKA BİR SÜTUNA aittir.
#
# Korpus ölçümü (849 belge, 31 Tem 2026) üç makul olmayan "masraf" tutarı
# gösterdi — 100.000 TL, 30.000 TL, 28.076,27 TL — ve üçü de tablo başlık
# satırından geliyordu:
#
#   "... Kâr Oranı | Tahsis Ücreti | Yıllık Maliyet Oranı | 100.000 TL ..."
#
# İleri pencere "Tahsis Ücreti"nden sonraki ilk sayıyı alıyordu, ama o sayı
# finansman tutarı sütununun değeri. Bu, cümle sınırını aşıp tarihten hayali
# 31 TL üreten hatanın tablo versiyonu: pencere bir SINIRDA kesilmeli.
_COLUMN_HEADERS_RE = re.compile(
    r"(y[ıi]ll[ıi]k\s+maliyet|maliyet\s+oran|finansman\s+tutar|"
    r"taksit\s+tutar|kâr\s+oran|kar\s+oran|kâr\s+pay|kar\s+pay|"
    r"toplam\s+geri\s+ödeme|toplam\s+geri\s+odeme|ödeme\s+plan|odeme\s+plan)",
    re.IGNORECASE)


def _truncate_at_next_column(window: str) -> str:
    """Pencereyi bir sonraki tablo sütunu başlığında keser.

    Kesme noktası başlığın BAŞLANGICI: "Tahsis Ücreti Yıllık Maliyet Oranı
    100.000 TL" -> "Tahsis Ücreti ". Böylece komşu sütunun sayısı bu alana
    yazılmaz. Başlık yoksa pencere olduğu gibi döner.
    """
    m = _COLUMN_HEADERS_RE.search(window)
    return window[:m.start()] if m else window


def extract_masraf(text: str) -> Optional[ExtractedField]:
    """Masraf durumu — negasyon farkında ('masrafsız' = 0, bilgi yok değil).

    Tutar, masraf sözcüğünün YEREL penceresinde aranır; aksi halde metnin
    başka yerindeki bir oran/sayı yanlışlıkla masraf tutarı sanılır.

    TÜM masraf bahisleri taranır (`finditer`), sadece ilki değil. Eskiden
    `re.search` kullanıldığı için sonuç yazım SIRASINA bağlıydı:

        "Masrafsızdır. Tahsis ücreti 500 TL."  -> has_fee=False  ✓ çelişki
        "Tahsis ücreti 500 TL. Masrafsızdır."  -> has_fee=True   ✗ çelişki kaçtı

    Bu alan kampanyanın İDDİASINI taşır. Metinde herhangi bir yerde
    "masrafsız/ücretsiz" iddiası varsa `has_fee=False` döner; gerçekte ücret
    olup olmadığını `tahsis_ucreti` alanı söyler ve uyuşmazlığı
    `contradiction.detect()` yakalar.
    """
    pat = re.compile(r"(masrafs[ıi]z|ücretsiz|ucretsiz|masraf|tahsis|ücret)",
                     re.IGNORECASE)
    first_positive = None
    for m in pat.finditer(text):
        # tutar keyword'den SONRA gelir ("tahsis ücreti 500 TL") → ileri pencere.
        # Pencere CÜMLE SINIRINDA kesilir: aksi halde sonraki cümledeki bir sayı
        # ("... alınmaz. Kampanya 31 Aralık 2026") 31 TL'lik hayali bir ücret
        # olarak okunuyordu. Nokta binlik ayırıcı da olduğu için lookaround şart.
        fwd = text[m.start(): min(len(text), m.end() + 40)]
        fwd = re.split(r"(?<!\d)[.;](?!\d)|\n", fwd, maxsplit=1)[0]
        fwd = _truncate_at_next_column(fwd)
        canon = N.normalize_fee_status(fwd)
        if canon is None:
            continue
        if canon.get("has_fee") is False:
            # "masrafsız" iddiası bulundu — sırası ne olursa olsun bu kazanır.
            s, e = m.span()
            return _field("masraf_durumu", m.group(0), canon,
                          _window(text, s, e),
                          span_start=s, span_end=e, trigger_distance=0)
        if first_positive is None:
            first_positive = (m, canon)

    if first_positive is None:
        return None
    m, canon = first_positive
    s, e = m.span()
    return _field("masraf_durumu", m.group(0), canon, _window(text, s, e),
                  span_start=s, span_end=e, trigger_distance=0)


def extract_tahsis_ucreti(text: str) -> Optional[ExtractedField]:
    """Tahsis ücreti / dosya masrafı — `masraf_durumu`'ndan BAĞIMSIZ çıkarılır.

    Neden ayrı: `contradiction.detect()`'in birincil kuralı
    (`masrafsiz_ama_ucret`) hem `masraf_durumu` hem `tahsis_ucreti` ister.
    Bu alan hiç üretilmediği için o kural bugüne kadar hiç tetiklenemedi ve
    yenilikçilik hedefi #2 (bkz. CLAUDE.md §18) ölüydü.

        "tahsis ücreti 500 TL"     -> {"value": 500.0, "currency": "TRY"}
        "TAHSİS ÜCRETİ ALINMAZ"    -> {"value": 0.0,   "currency": "TRY"}
        (hiç geçmiyorsa)           -> None  (uydurma yok)

    Negasyon "bilgi yok" DEĞİL "ücret sıfır" demektir; bu ayrım §5.5'teki
    "masrafsız finansman" teriminin doğru yorumlanmasının temelidir.
    """
    trigger = re.compile(
        r"(tahsis\s*ücret\w*|tahsis\s*ucret\w*|dosya\s*masraf\w*|"
        r"tahsis\s*bedel\w*)",
        re.IGNORECASE,
    )
    # TÜM tetikleyiciler taranır, sadece ilki değil.
    #
    # `re.search` (ilk eşleşme) kullanıldığında sonuç metindeki yazım
    # SIRASINA bağlı oluyordu: sayfada birden çok ücret bahsi varsa
    # cümleleri ters çevirmek çıkan değeri — dolayısıyla çelişki tespitini —
    # değiştiriyordu. 849 belgelik gerçek korpusta değişmez denetimi (P4)
    # bunu 15 belgede yakaladı.
    #
    # Kardeş alan `masraf_durumu` "masrafsız İDDİASI her sırada kazanır"
    # kuralını izliyor. Simetrik karar: burada POZİTİF ÜCRET kazanır.
    # Böylece ikisi de sıradan bağımsız olur ve çelişki, her iki sinyal de
    # metinde varsa hangi sırada yazıldığından bağımsız olarak tetiklenir.
    ilk_sifir = None
    for m in trigger.finditer(text):
        # Aynı cümlecik içinde kal: aksi halde metnin başka yerindeki bir
        # tutar yanlışlıkla tahsis ücreti sanılır.
        tail = text[m.end(): m.end() + 60]
        # DİKKAT: '.' Türkçede hem cümle sonu hem BİNLİK AYIRICIDIR. Düz
        # re.split(r"[.;\n]") "1.500,00 TL"yi "1"de kesip 1500 yerine 1
        # üretiyordu. Rakam arası noktada bölmemek için lookaround konur.
        clause = re.split(r"(?<!\d)[.;](?!\d)|\n", tail, maxsplit=1)[0]

        if re.search(NEGATION_RE, clause, re.IGNORECASE):
            canon = {"value": 0.0, "currency": "TRY"}
        else:
            # AÇIK PARA BİRİMİ ŞART. `normalize_money` para birimi işareti
            # olmasa da varsayılan "TRY" döndürür; bu, ücret tetikleyicisinin
            # yakınındaki HER çıplak sayıyı tutar sanmaya yol açıyordu.
            # Gerçek vaka: ürün adı "2B Finansmanı" olan sayfada "2" sayısı
            # 2,00 TL tahsis ücreti olarak okunuyordu (849 belgelik korpusta
            # değişmez denetimi yakaladı).
            if not re.search(r"(tl|₺|try|türk\s*liras[ıi]|lira)",
                             clause, re.IGNORECASE):
                continue
            canon = N.normalize_money(clause)
            if canon is None:
                continue        # tetikleyici var ama ne tutar ne negasyon

        # raw_value BİTİŞİK dilim olmalı, yoksa span doğrulaması kırılır.
        s, e = m.start(), m.end() + len(clause)
        alan = _field("tahsis_ucreti", text[s:e], canon,
                      _window(text, m.start(), m.end()),
                      span_start=s, span_end=e, trigger_distance=0)
        if canon.get("value", 0) > 0:
            return alan                 # pozitif ücret her sırada kazanır
        if ilk_sifir is None:
            ilk_sifir = alan
    return ilk_sifir


def extract_kampanya_suresi(text: str) -> Optional[ExtractedField]:
    """Kampanya süresi / son tarih → ISO."""
    pat = re.compile(
        r"(\d{1,2}[./]\d{1,2}[./]\d{4}|\d{4}-\d{1,2}-\d{1,2}|"
        r"\d{1,2}\s+[A-Za-zÇĞİÖŞÜçğıöşü]+\s+\d{4})"
    )
    m = pat.search(text)
    if not m:
        return None
    raw = m.group(1)
    s, e = m.span(1)
    canon = N.normalize_date(raw)
    if canon is None:
        return None
    # Tarih genelde "kampanya süresi/son başvuru/tarihine kadar" ifadesinin
    # yakınındadır; tetikleyici varsa uzaklığı ölç, yoksa None (ceza).
    trig = None
    for tm in re.finditer(r"(kampanya|son\s+ba[şs]vuru|ge[çc]erli|tarihine\s+kadar)",
                          text, re.IGNORECASE):
        d = abs(s - tm.start())
        trig = d if trig is None else min(trig, d)
    return _field("kampanya_suresi", raw, canon, _window(text, s, e),
                  span_start=s, span_end=e, trigger_distance=trig,
                  candidate_count=len(pat.findall(text)))


@dataclass
class RateRow:
    """Oran tablosunun tek satırı: bir vade ve o vadeye ait oranlar."""

    vade_ay: int
    kar_payi: float
    tahsis_ucreti: Optional[float] = None


def parse_rate_table(text: str) -> list[RateRow]:
    """Banka ürün sayfalarındaki ORAN TABLOSUNU ayrıştırır.

    Gerçek veride bulundu (Türkiye Finans, Vakıf Katılım ürün sayfaları).
    Sayfalar oranı düz cümle olarak değil TABLO olarak yayımlıyor:

        Vade  Kâr Payı Oranı  Tahsis Ücreti  Aylık Maliyet  Yıllık Maliyet
          3       4,09%           0,50%          5,63%         92,88%
         12       4,05%           0,50%          5,37%         87,29%
         36       3,89%           0,50%          5,10%         81,69%

    HTML→metin dönüşümünden sonra bu düz bir belirteç dizisine iner:
        "... Vade Kâr Payı Oranı Tahsis Ücreti ... 3 4,09% 0,50% 5,63%
         92,88% 12 4,05% 0,50% ..."

    `extract_kar_payi` bunu kaçırır çünkü "kâr payı" etiketi tablo
    BAŞLIĞINDA, değerlerden onlarca karakter uzakta. Oysa şartnamenin
    §5.3/§5.7'de istediği bilgi (vade + kâr payı + tahsis ücreti bir arada)
    tam olarak burada.

    Dönüş: satır listesi. Tablo bulunamazsa boş liste.
    """
    # Başlık. Bankalar farklı etiket kullanıyor — gerçek veride görülenler:
    #   "Vade  Kâr Payı Oranı  Tahsis Ücreti ..."        (Türkiye Finans)
    #   "Finansman Tutarı  Vade  Kar Oranı  Taksit ..."  (Emlak Katılım)
    # Bu yüzden "payı" ZORUNLU DEĞİL ve kolon sırası esnek.
    baslik = re.search(
        r"vade[^%\d]{0,40}?(kâr|kar)\s*(pay[ıi]\s*|payla[şs][ıi]m\s*)?oran[ıi]",
        text, re.IGNORECASE)
    if not baslik:
        return []

    kuyruk = text[baslik.end(): baslik.end() + 4000]

    yuzde = r"(?:%\s*\d{1,3}[.,]\d{1,2}|\d{1,3}[.,]\d{1,2}\s*%)"

    # DİKKAT — kredi/değer oranı tuzağı. Vakıf Katılım konut sayfasında
    #   "Değer x 90%  Değer x 80%  Değer x 70%"
    # geçiyor; bunlar KREDİ/DEĞER oranıdır, kâr payı DEĞİLDİR. Bir yüzdenin
    # hemen öncesinde "değer x" varsa satır atlanır.
    kredi_deger = re.compile(r"de[ğg]er\s*[x×]\s*$", re.IGNORECASE)

    # İki satır biçimi gözlendi:
    #   A) "3 4,09% 0,50% 5,63%"        -> vade çıplak tamsayı
    #   B) "30.000,00 ₺ 12 Ay 1,69% ..." -> vade "12 Ay"
    # Genel çözüm: vade adayını bul, ONDAN SONRAKİ ilk yüzdeyi kâr payı say.
    # (?![\d.,]) ZORUNLU: bu olmadan "30.000,00 ₺ 12 Ay" ifadesinden "30"
    # kapılıp vade 30 sanılıyordu (doğrusu 12). Sayının tamamı tüketilmeli.
    vade_re = re.compile(r"\b(\d{1,3})(?![\d.,])\s*(?:ay\b)?", re.IGNORECASE)
    yuzde_re = re.compile(yuzde)

    yuzdeler = [(m.start(), m.end(), m.group(0))
                for m in yuzde_re.finditer(kuyruk)]
    if not yuzdeler:
        return []

    # BİÇİM A önce denenir: "3 4,09% 0,50% 5,63% 92,88% 12 4,05% ..."
    # Vade çıplak tamsayı, ardından 2-5 yüzde bir arada. Bu düzen KATI
    # eşleştirmeyle doğru okunur; esnek eşleştirme burada çöp satır üretir
    # (her vade adayını en yakın yüzdeyle çiftler, kolonlar kayar).
    kati = re.compile(rf"\b(\d{{1,3}})(?![\d.,])\s+((?:{yuzde}\s*){{2,5}})")
    kati_rows: list[RateRow] = []
    for m in kati.finditer(kuyruk):
        try:
            vade = int(m.group(1))
        except ValueError:
            continue
        if not (1 <= vade <= 480):
            continue
        oranlar = [N.parse_tr_number(x) for x in re.findall(yuzde, m.group(2))]
        oranlar = [o for o in oranlar if o is not None]
        if len(oranlar) < 2 or not (0 < oranlar[0] <= 15):
            continue
        kati_rows.append(RateRow(
            vade_ay=vade, kar_payi=oranlar[0],
            tahsis_ucreti=oranlar[1] if 0 <= oranlar[1] <= 10 else None))
    if kati_rows:
        return kati_rows

    # BİÇİM B: "30.000,00 ₺ 12 Ay 1,69% 2.841,66 ₺ 157,50 ₺"
    # Kolonlar arasında para birimi var, katı düzen tutmaz — vade adayını
    # kendisinden SONRAKİ ilk yüzdeyle çiftle.
    rows: list[RateRow] = []
    kullanilan: set[int] = set()
    for vm in vade_re.finditer(kuyruk):
        try:
            vade = int(vm.group(1))
        except ValueError:
            continue
        if not (1 <= vade <= 480):
            continue
        # Vadeden sonraki ilk yüzde, ve 60 karakterden uzaksa ilgisizdir.
        sonraki = [y for y in yuzdeler
                   if y[0] >= vm.end() and y[0] - vm.end() <= 60
                   and y[0] not in kullanilan]
        if not sonraki:
            continue
        s0, e0, ham = sonraki[0]
        if kredi_deger.search(kuyruk[max(0, s0 - 12): s0]):
            continue
        kar = N.parse_tr_number(ham)
        if kar is None or not (0 < kar <= 15):
            # Kâr payı makul bandın dışındaysa bu bir maliyet/iskonto
            # kolonudur (yıllık toplam maliyet %92 gibi) — satır değil.
            continue
        kullanilan.add(s0)
        # Tahsis ücreti: bir sonraki yüzde, varsa ve makulse.
        tahsis = None
        ardindan = [y for y in yuzdeler if y[0] >= e0 and y[0] - e0 <= 30]
        if ardindan:
            t = N.parse_tr_number(ardindan[0][2])
            if t is not None and 0 <= t <= 10:
                tahsis = t
        rows.append(RateRow(vade_ay=vade, kar_payi=kar, tahsis_ucreti=tahsis))
    return rows


def extract_from_rate_table(text: str) -> list[ExtractedField]:
    """Oran tablosundan `kar_payi_orani`, `vade_ay`, `tahsis_ucreti` üretir.

    Tablo birden çok vade içerir, şema ise alan başına tek değer ister.
    Karar: kâr payı **aralık** olarak verilir (dürüst — vadeye göre değişir),
    vade **en uzun** vade, tahsis ücreti tablodaki sabit değer.
    §5.7 "En Düşük Kâr Payı" karşılaştırması aralığın alt sınırını kullanır.
    """
    rows = parse_rate_table(text)
    if not rows:
        return []

    m = re.search(r"vade[^%\d]{0,40}?(kâr|kar)\s*pay[ıi]\s*oran[ıi]",
                  text, re.IGNORECASE)
    s, e = (m.span() if m else (0, 0))
    pencere = _window(text, s, e)

    oranlar = [r.kar_payi for r in rows]
    lo, hi = min(oranlar), max(oranlar)
    kar_payi = N.collapse_degenerate_range({"min": lo, "max": hi})

    out = [
        _field("kar_payi_orani", text[s:e], kar_payi, pencere,
               span_start=s, span_end=e, trigger_distance=0),
        _field("vade_ay", text[s:e], max(r.vade_ay for r in rows), pencere,
               span_start=s, span_end=e, trigger_distance=0),
    ]
    ucretler = {r.tahsis_ucreti for r in rows if r.tahsis_ucreti is not None}
    if len(ucretler) == 1:
        # Tahsis ücreti tabloda ORAN olarak veriliyor (%0,50), tutar değil.
        out.append(_field("tahsis_ucreti", text[s:e],
                          {"rate": ucretler.pop()}, pencere,
                          span_start=s, span_end=e, trigger_distance=0))
    return out


def extract_odul_miktari(text: str) -> Optional[ExtractedField]:
    """Kampanya ödülü: 'X TL hediye', '500 TL para puan', 'cashback'.

    §5.7'nin "En Yüksek Ödül Miktarı" kriteri bu alan olmadan cevaplanamıyordu.

    TUZAK — koşul/ödül ayrımı: "500 TL alışveriş yapana 50 TL hediye"
    cümlesinde 500 TL bir KOŞUL, 50 TL ise ÖDÜLdür. Bu yüzden tutar, ödül
    sözcüğünün kendi cümleciğinde ve tercihen ondan ÖNCE aranır
    ("50 TL hediye"), koşul ifadelerinin ardından değil.
    """
    reward = re.compile(
        r"(hediye|para\s*puan|cashback|nakit\s*iade|iade|bonus|çek|"
        r"kazan\w*|ödül)",
        re.IGNORECASE,
    )
    money = re.compile(r"\d[\d.,]*\s*(?:tl|₺|try|türk\s*liras[ıi])", re.IGNORECASE)

    best = None
    for rm in reward.finditer(text):
        # ödül sözcüğünün ÖNCESİNDEKİ 30 karakterde tutar ara ("50 TL hediye")
        back = text[max(0, rm.start() - 30): rm.start()]
        cands = list(money.finditer(back))
        if cands:
            mm = cands[-1]           # ödül sözcüğüne en yakın olan
            s = max(0, rm.start() - 30) + mm.start()
            e = max(0, rm.start() - 30) + mm.end()
            dist = rm.start() - e
        else:
            # sonrasında ara ("hediye 50 TL")
            fwd_off = rm.end()
            fwd = text[fwd_off: fwd_off + 30]
            mm = money.search(fwd)
            if not mm:
                continue
            s, e = fwd_off + mm.start(), fwd_off + mm.end()
            dist = s - rm.end()
        if best is None or dist < best[2]:
            best = (s, e, dist)

    if best is None:
        return None
    s, e, dist = best
    raw = text[s:e]
    canon = N.normalize_money(raw)
    if canon is None:
        return None
    return _field("odul_miktari", raw, canon, _window(text, s, e),
                  span_start=s, span_end=e, trigger_distance=dist)


def extract_indirim_orani(text: str) -> Optional[ExtractedField]:
    """İndirim oranı: '%20 indirim', 'indirim oranı %15', "%25'e varan indirim".

    TUZAK: "%5 puan iadesi" bir indirim değil `alisveris_puani`'dır; bu yüzden
    'puan/iade' bağlamındaki oranlar dışlanır.
    """
    pat = re.compile(
        r"(?:%\s*(\d[\d.,]*)|(\d[\d.,]*)\s*%)"
        r"(?:[^.;\n]{0,20}?)\bindirim",
        re.IGNORECASE,
    )
    m = pat.search(text)
    if m is None:
        pat2 = re.compile(r"indirim\s*(?:oran[ıi])?[^%\d]{0,12}"
                          r"(%\s*\d[\d.,]*|\d[\d.,]*\s*%)", re.IGNORECASE)
        m = pat2.search(text)
        if m is None:
            return None
        s, e = m.span(1)
    else:
        s, e = (m.span(1) if m.group(1) else m.span(2))

    # 'puan iadesi' bağlamıysa bu indirim değil, alışveriş puanıdır
    ctx = text[max(0, s - 25): min(len(text), e + 25)]
    if re.search(r"puan", ctx, re.IGNORECASE):
        return None

    raw = text[s:e]
    canon = N.normalize_rate(raw)
    return _field("indirim_orani", raw, canon, _window(text, s, e),
                  span_start=s, span_end=e, trigger_distance=0)


def extract_alisveris_puani(text: str) -> Optional[ExtractedField]:
    """Alışveriş puanı — ORAN ya da ADET olabilir, ikisi farklı kanonik şekil.

        "%5 puan iadesi"      -> {"kind": "rate",   "value": 5.0}
        "1.000 chip-para"     -> {"kind": "points", "value": 1000.0}

    İki şekli ayrı tutmak §5.7 karşılaştırmasında elmayla armutun
    kıyaslanmasını engeller (bkz. CLAUDE.md §17 adil kıyas garantisi).
    """
    trigger = re.compile(r"(chip[\s-]*para|alışveriş\s*puan\w*|alisveris\s*puan\w*|"
                         r"puan\s*iade\w*|bonus\s*puan\w*|puan)", re.IGNORECASE)
    tm = trigger.search(text)
    if tm is None:
        return None

    ctx_s = max(0, tm.start() - 30)
    ctx = text[ctx_s: min(len(text), tm.end() + 30)]

    rate = re.search(r"%\s*(\d[\d.,]*)|(\d[\d.,]*)\s*%", ctx)
    if rate:
        off = ctx_s + (rate.start(1) if rate.group(1) else rate.start(2))
        end = ctx_s + (rate.end(1) if rate.group(1) else rate.end(2))
        val = N.parse_tr_number(text[off:end])
        if val is None:
            return None
        canon = {"kind": "rate", "value": val}
        s, e = off, end
    else:
        num = re.search(r"(\d[\d.,]*)\s*(?:adet\s*)?(?:chip|puan)?", ctx)
        if not num or not num.group(1):
            return None
        off, end = ctx_s + num.start(1), ctx_s + num.end(1)
        val = N.parse_tr_number(text[off:end])
        if val is None:
            return None
        canon = {"kind": "points", "value": val}
        s, e = off, end

    return _field("alisveris_puani", text[s:e], canon, _window(text, s, e),
                  span_start=s, span_end=e, trigger_distance=0)


def extract_hedef_kitle(text: str) -> Optional[ExtractedField]:
    """Hedef kitle — §5.3'ün 4 segmenti, ÇOK ETİKETLİ.

        yeni_musteri | mevcut_musteri | maas_musterisi | belirli_segment

    Sinyal yoksa `None` döner — "mevcut müşteri" varsayılanı YAPILMAZ
    (halüsinasyon yasağı). Negasyon penceresi kontrol edilir: "yeni müşteri
    olmayanlar" ifadesi yeni_musteri etiketi ÜRETMEZ.
    """
    segments = {
        "yeni_musteri": r"(yeni\s*müşteri|yeni\s*musteri|ilk\s*kez|hoş\s*geldin|"
                        r"hos\s*geldin|yeni\s*üye)",
        "mevcut_musteri": r"(mevcut\s*müşteri|mevcut\s*musteri|halihazırda|"
                          r"müşterilerimize\s*özel)",
        "maas_musterisi": r"(maaş\s*müşteri\w*|maas\s*musteri\w*|maaşını\s*"
                          r"bankamızdan|maaş\s*ödemesi)",
        "belirli_segment": r"(emekli|öğrenci|ogrenci|esnaf|kamu\s*çalışan\w*|"
                           r"kobi|serbest\s*meslek)",
    }
    found: list[str] = []
    first_span = None
    for label, pat in segments.items():
        m = re.search(pat, text, re.IGNORECASE)
        if not m:
            continue
        # negasyon penceresi: "... olmayanlar", "... hariç", "... dışında"
        after = text[m.end(): m.end() + 25]
        if re.search(r"(olmayan\w*|hari[çc]|d[ıi][şs][ıi]nda|ge[çc]erli\s*de[ğg]il)",
                     after, re.IGNORECASE):
            continue
        found.append(label)
        if first_span is None:
            first_span = m.span()

    if not found:
        return None
    s, e = first_span
    return _field("hedef_kitle", text[s:e], sorted(found), _window(text, s, e),
                  span_start=s, span_end=e, trigger_distance=0)


def extract_kampanya_kosullari(text: str) -> Optional[ExtractedField]:
    """Kampanya koşulları — SKALER DEĞİL, cümle listesi.

    Koşul tetikleyicisi içeren cümleler toplanır. Eşleşme ölçütü diğer
    alanlardan farklıdır (küme-F1 / token-Jaccard); bu yüzden eval'de ayrı
    bölümde raporlanır.
    """
    # DİKKAT: tek başına "geçerli\w*" TETİKLEYİCİ DEĞİLDİR. Neredeyse her
    # kampanya metni "Kampanya <tarih> tarihine kadar geçerlidir" cümlesiyle
    # biter; bu bir GEÇERLİLİK TARİHİdir (zaten `kampanya_suresi` yakalar),
    # yararlanma koşulu değil. Tetikleyici olarak bırakılması her belgede
    # yanlış pozitif üretiyordu. Yalnızca "için geçerli" biçimi koşul sayılır.
    triggers = re.compile(
        r"(şart\w*|koşul\w*|kosul\w*|gerekmekte\w*|gerekli\w*|zorunlu\w*|"
        r"asgari|en\s*az\s+\d|minimum|yalnızca|sadece|hariç|"
        r"için\s*geçerli|olmas[ıi]\s*gerek)",
        re.IGNORECASE,
    )
    # BOILERPLATE FİLTRESİ — gerçek veride bulundu (291 belgelik korpus,
    # değişmez denetimi `kampanya_kosullari`nı tek suçlu olarak işaretledi).
    #
    # Tetikleyici sözcükler ("zorunlu", "gerekli", "sadece", "yalnızca")
    # çerez politikası, KVKK aydınlatma metni ve gizlilik bildirimlerinde de
    # geçiyor. Filtresiz hâlde belge başına ~8,7 "koşul" çıkıyordu ve büyük
    # kısmı şuna benzer hukuki metindi:
    #   "bu çerezler zorunlu çerezler dışında kalan işlevsellikleri sağlama
    #    amacıyla kullanılmaktadır"
    # Bu bir kampanya koşulu DEĞİLDİR; gold sete ve ürüne çöp akıtır.
    boilerplate = re.compile(
        r"(çerez|cookie|kvkk|kişisel\s*veri|aydınlatma\s*metni|"
        r"gizlilik\s*(politika|bildirim)|açık\s*rıza|veri\s*sorumlusu|"
        r"telif|tüm\s*hakları|sosyal\s*medya\s*hesap|bilgi\s*toplumu|"
        r"çağrı\s*merkezi|müşteri\s*hizmetleri|şubelerimiz)",
        re.IGNORECASE,
    )

    sentences = split_sentences(text)
    picked = [
        s.strip() for s in sentences
        if triggers.search(s)
        and not boilerplate.search(s)
        # Menü/footer yığınları tek "cümle" olarak gelir; gerçek bir koşul
        # cümlesi makul uzunluktadır.
        and 20 <= len(s.strip()) <= 400
    ]
    if not picked:
        return None
    # Üst sınır: bir kampanyanın onlarca koşulu olmaz. Fazlası, filtrenin
    # kaçırdığı gövde metnidir.
    picked = picked[:8]

    # span: ilk koşul cümlesinin metindeki yeri
    first = picked[0]
    idx = text.find(first)
    if idx < 0:
        idx, end = 0, 0
    else:
        end = idx + len(first)
    return _field("kampanya_kosullari", text[idx:end] if end > idx else first,
                  picked, _window(text, idx, end),
                  span_start=idx if end > idx else None,
                  span_end=end if end > idx else None,
                  trigger_distance=0)


# Tüm kural çıkarıcılar — sırayla denenir.
_EXTRACTORS = [
    extract_kar_payi,
    extract_vade,
    extract_tutar,
    extract_taksit,
    extract_masraf,
    extract_tahsis_ucreti,
    extract_kampanya_suresi,
    extract_odul_miktari,
    extract_indirim_orani,
    extract_alisveris_puani,
    extract_hedef_kitle,
    extract_kampanya_kosullari,
]


def extract_all(text: str) -> list[ExtractedField]:
    """Metinden kural katmanının çıkarabildiği tüm alanları döndürür.

    Bulunamayan alanlar listelenmez (boşluk LLM'e bırakılır). Aynı alan birden
    çok kez yakalanırsa ilk (en yüksek güvenli) tutulur.
    """
    out: dict[str, ExtractedField] = {}
    # ORAN TABLOSU önce denenir: tablo varsa kâr payı/vade/tahsis ücreti
    # oradan gelir ve tekil çıkarıcıların tablo gövdesinden yanlış değer
    # devşirmesi engellenir (tabloda onlarca sayı yan yana durur).
    for f in extract_from_rate_table(text):
        if f.is_present:
            out[f.field_name] = f
    for fn in _EXTRACTORS:
        f = fn(text)
        if f and f.is_present and f.field_name not in out:
            out[f.field_name] = f
    return list(out.values())
