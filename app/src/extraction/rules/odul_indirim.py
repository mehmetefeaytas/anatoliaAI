"""Ödül miktarı + indirim oranı — `extract.py` bölünmesinde AYRI modül.

## Neden bu iki alan BİRLİKTE

`extract_odul_miktari` ve `extract_indirim_orani` birbirini çağırmıyor ama
ikisi de aynı "ödül/avantaj retoriği" ailesinden, ikisi de kısa (~60 satır)
ve ikisi de `_ortak._PARA_IFADESI`/dilim-almama disiplinini paylaşıyor
(`odul_miktari` doğrudan, `indirim_orani` normalize.normalize_rate
üzerinden dolaylı). `alisveris_puani` kasıtlı olarak AYRI tutuldu çünkü
onun kendi puan/oran ikili şeması ve gezinme-şeridi süzgeci var —
gerekçe `alisveris_puani.py` başlığında.
"""

from __future__ import annotations

import re
from typing import Optional

from ...normalization import normalize as N
from ...schemas import ExtractedField
from ._ortak import _PARA_IFADESI, _field, _window

# Ödül çapasının komşusunda geçiyorsa tutar ödül DEĞİLDİR. Liste bilinçli
# olarak dar: yalnız kendi gold setimizde yanlış pozitif ürettiği ölçülmüş
# sınıflar var. Marka puanları (ParafPara/Worldpuan/Bonus) BİLEREK dışarıda
# — gold onları tutarlı etiketlemiyor ("500 TL Bonus" -> `alisveris_puani`,
# "11.000 TL'ye varan bonus" -> `odul_miktari`), dolayısıyla hangi yöne
# düzeltilse bir kaydı bozuyor. Tutarsızlık hakem turuna bırakıldı
# (bkz. data/gold/review/).
# `para\s*çek` çekim/çekebilir/çekme çekimlerinin hepsini kapsar; "hediye
# çeki" bu kalıba GİRMEZ, dolayısıyla meşru hediye çeki ödülü korunur.
_ODUL_DISI_RE = re.compile(
    r"indirim|para\s*çek|çek\s*karnesi|çek\s*tahsil"
    r"|parafpara|chip[\s-]*para|maximiles|worldpuan|world\s*puan",
    re.IGNORECASE,
)


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
    money = re.compile(_PARA_IFADESI, re.IGNORECASE)

    best = None
    for rm in reward.finditer(text):
        # `kazan\w*` ve `çek` çapaları geniş: gold'un ödül SAYMADIĞI üç sınıfı
        # da içeri alıyorlardı (19 Ağu 2026, kendi gold.v2'mizde 4 yanlış
        # pozitif olarak ölçüldü):
        #
        #   "1.000 TL indirim kazanabilir"          -> indirim, ödül değil
        #   "50.000 TL … para çekimi yapılabilir"   -> hesap işlemi, ödül değil
        #   "10.000 TL … çek karnesi ve çek tahsil" -> hizmet paketi, ödül değil
        #
        # `çek` çapası korunuyor çünkü "500 TL değerinde A101 hediye çeki"
        # gold'da DOLU bir ödüldür; ayrım çapada değil, çapanın komşusunda.
        if _ODUL_DISI_RE.search(
                text[max(0, rm.start() - 40): rm.end() + 25]):
            continue
        # Arama METNİN KENDİSİNDE, konum sınırlarıyla yapılır — dilim ALINMAZ.
        #
        # `text[a:b]` alıp desende aramak, sayının ortasından başlayan bir
        # eşleşmeye kapı açıyordu: dilimin sol kenarı "5000" içinde kalınca
        # desen "000 TL" görüyor ve ödül 0 TL'ye düşüyordu (7 belgede ölçüldü,
        # bkz. `_SAYI_BASI`). `search(text, pos, endpos)` ile geriye-bakış
        # (lookbehind) `pos`tan ÖNCEKİ gerçek karakterleri görür, dolayısıyla
        # kesik eşleşme yapısal olarak imkânsız hâle gelir.
        bas = max(0, rm.start() - 30)
        # ödül sözcüğünün ÖNCESİNDEKİ 30 karakterde tutar ara ("50 TL hediye")
        cands = [m for m in money.finditer(text, bas, rm.start())]
        if cands:
            mm = cands[-1]           # ödül sözcüğüne en yakın olan
            s, e = mm.start(), mm.end()
            dist = rm.start() - e
        else:
            # sonrasında ara ("hediye 50 TL")
            mm = money.search(text, rm.end(), min(len(text), rm.end() + 30))
            if not mm:
                continue
            s, e = mm.start(), mm.end()
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
    # ARALIK — "%10 ila %50 arasında indirim". Üçüncü grup aralığın ÜST
    # sınırıdır ve opsiyoneldir.
    #
    # 2026-08-12'de eklendi; öncesinde aralığın yalnız ALT sınırı alınıyordu:
    # Hayat Finans GastroClub belgesinde gold `{min: 10, max: 50}` iken çıkarım
    # `10.0` idi — yani kampanyanın en iyi tarafı sessizce düşüyordu.
    #
    # `extract_kar_payi` "ile|ila"yı zaten aralık ayırıcı sayıyordu; bu desen
    # o taramadan atlanmıştı (aynı sınıftan tutarsızlık için bkz.
    # `_KAR_PAYI_ETIKET`).
    pat = re.compile(
        r"(?:%\s*(\d[\d.,]*)|(\d[\d.,]*)\s*%)"
        r"(?:\s*(?:-|–|ile|ila)\s*%?\s*(\d[\d.,]*)(?![\d.,])\s*%?)?"
        r"(?:[^.;\n]{0,20}?)\bindirim",
        re.IGNORECASE,
    )
    m = pat.search(text)
    ust_ham = None
    if m is None:
        pat2 = re.compile(r"indirim\s*(?:oran[ıi])?[^%\d]{0,12}"
                          r"(%\s*\d[\d.,]*|\d[\d.,]*\s*%)", re.IGNORECASE)
        m = pat2.search(text)
        if m is None:
            return None
        s, e = m.span(1)
    else:
        s, e = (m.span(1) if m.group(1) else m.span(2))
        ust_ham = m.group(3)

    # 'puan iadesi' bağlamıysa bu indirim değil, alışveriş puanıdır
    ctx = text[max(0, s - 25): min(len(text), e + 25)]
    if re.search(r"puan", ctx, re.IGNORECASE):
        return None

    raw = text[s:e]
    canon = N.normalize_rate(raw)
    if ust_ham is not None:
        ust = N.normalize_rate(ust_ham)
        # Bozuk aralık (üst < alt) sessizce yazılmaz: tek değere düşülür.
        # Aksi hâlde kıyas tablosu ters bir aralık gösterirdi.
        if isinstance(canon, (int, float)) and isinstance(ust, (int, float)) \
                and ust > canon:
            canon = N.collapse_degenerate_range({"min": canon, "max": ust})
            raw = text[s:m.end(3)]
            e = m.end(3)

    return _field("indirim_orani", raw, canon, _window(text, s, e),
                  span_start=s, span_end=e, trigger_distance=0)
