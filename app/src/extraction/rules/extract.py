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
def extract_kar_payi(text: str) -> Optional[ExtractedField]:
    """Kâr payı oranı: '... kâr payı oranı %1,99 ...' veya aralık."""
    # Aralık ikinci operandı bir BİRİM sözcüğü ile devam ediyorsa aralık DEĞİLDİR:
    #   "kâr payı oranı %1,89 ile 120 aya kadar vade"
    # buradaki "ile" bağlaçtır, aralık ayırıcı değil. Negatif ileri-bakış olmadan
    # sistem bunu {min: 1.89, max: 120.0} diye okuyup karşılaştırma tablosuna
    # bir VADEYİ oran üst sınırı olarak yazıyordu.
    pat = re.compile(
        r"(kâr|kar)\s*pay[ıi]\s*(oran[ıi])?[^%\d]{0,15}"
        r"(%?\s*\d[\d.,]*\s*%?"
        r"(?:\s*(?:-|–|ile|ila)\s*%?\s*"
        # (?![\d.,]) sayının TAMAMININ tüketilmesini zorlar. Bu olmadan regex
        # geri izleyip "36"dan yalnız "3"ü alarak birim kontrolünü atlatıyordu.
        r"\d[\d.,]*(?![\d.,])\s*%?"
        r"(?!\s*(?:ay|y[ıi]l|sene|taksit|tl|₺|adet))"
        r")?)",
        re.IGNORECASE,
    )
    m = pat.search(text)
    if not m:
        return None
    raw = m.group(3)
    s, e = m.span(3)
    canon = N.normalize_rate(raw)
    return _field(
        "kar_payi_orani", raw, canon, _window(text, m.start(), m.end()),
        span_start=s, span_end=e,
        # "kâr payı oranı" bitişi ile değerin başı arası
        trigger_distance=s - m.end(1),
        candidate_count=len(pat.findall(text)),
    )


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
    m = trigger.search(text)
    if m is None:
        return None

    # Aynı cümlecik içinde kal: tetikleyiciden sonraki ilk cümle/virgül sonuna
    # kadar bak. Aksi halde metnin başka yerindeki bir tutar yanlışlıkla
    # tahsis ücreti sanılır.
    tail = text[m.end(): m.end() + 60]
    # DİKKAT: '.' Türkçede hem cümle sonu hem BİNLİK AYIRICIDIR. Düz
    # re.split(r"[.;\n]") "1.500,00 TL"yi "1"de kesip 1500 yerine 1 üretiyordu.
    # Rakamlar arasındaki noktada bölmemek için etrafına lookaround konur.
    clause = re.split(r"(?<!\d)[.;](?!\d)|\n", tail, maxsplit=1)[0]

    if re.search(NEGATION_RE, clause, re.IGNORECASE):
        canon = {"value": 0.0, "currency": "TRY"}
    else:
        canon = N.normalize_money(clause)
        if canon is None:
            # Tetikleyici var ama ne tutar ne negasyon → bilgi belirsiz.
            return None

    # raw_value BİTİŞİK bir dilim olmalı, yoksa span doğrulaması kırılır
    # (önceden `m.group(0) + clause.rstrip()` birleştirmesi kullanılıyordu).
    s, e = m.start(), m.end() + len(clause)
    raw = text[s:e]
    return _field("tahsis_ucreti", raw, canon, _window(text, m.start(), m.end()),
                  span_start=s, span_end=e, trigger_distance=0)


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
    for fn in _EXTRACTORS:
        f = fn(text)
        if f and f.is_present and f.field_name not in out:
            out[f.field_name] = f
    return list(out.values())
