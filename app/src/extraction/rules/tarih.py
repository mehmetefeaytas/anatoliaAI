"""Kampanya süresi / tarih aralığı çıkarımı — AYRI modül.

## Neden bu sınır burada

`kampanya_tarih_araligi` ve `extract_kampanya_suresi` başka hiçbir alan
modülü tarafından çağrılmıyor ve kendi yardımcılarının (kanun atfı reddi,
gün-gün aralığı, başlangıç/bitiş rol tetikleyicileri) hiçbiri paylaşılmıyor.
`kampanya_tarih_araligi` bilerek public bırakıldı: `tests/
test_kampanya_suresi_araligi.py` onu doğrudan içe aktarıyor.
"""

from __future__ import annotations

import re
from typing import Optional

from ...normalization import normalize as N
from ...schemas import ExtractedField
from ._ortak import _field, _window

#: Tarih adayı deseni. Ay adı ARTIK SERBEST SÖZCÜK DEĞİL.
#: Eski desen `\d{1,2}\s+[A-Za-zÇĞİÖŞÜçğıöşü]+\s+\d{4}` herhangi bir sözcüğü ay
#: sanıyordu ("12 taksit 2026"); üstelik `search` ile İLK eşleşme alınıp
#: `normalize_date` None dönünce fonksiyon komple pes ediyordu — yani sahte bir
#: aday, belgedeki gerçek tarihi tamamen gölgeliyordu.
_AY_ALT = "|".join(sorted(N.TR_AY_ADLARI, key=len, reverse=True))
_TARIH_RE = re.compile(
    r"\d{1,2}[./]\d{1,2}[./]\d{4}"
    r"|\d{4}-\d{1,2}-\d{1,2}"
    rf"|\d{{1,2}}\s+(?:{_AY_ALT})\s+\d{{4}}",
    re.IGNORECASE,
)

# KANUN ATFI bir kampanya tarihi DEĞİLDİR.
# Ölçülen halüsinasyon (`turkiye-emlak-katilim--finansmanlar-ihtiyac-finansmani`,
# gold `absent` diyor): "...konutun 22/11/2001 tarihli ve 4721 sayılı Türk
# Medeni Kanununun..." — 2001-11-22 kampanya bitiş tarihi olarak yazılıyordu.
# Türk hukuk metinlerinin sabit atıf kalıbı "<tarih> tarihli ve <no> sayılı".
_KANUN_ATIF_RE = re.compile(
    r"\s*tarih(?:li|inde|leri)?\s+ve\s+\d+\s*say[ıi]l[ıi]", re.IGNORECASE)

# İki tarih arasında aralık ayıracı olabilecek dilim: "-", "–", "ile", "ila",
# "/" ya da yalnızca boşluk (HTML tablosu düzleşince "01 Ocak 2026 31 Aralık
# 2026" biçimine iner). Uzun mesafeye izin verilmez; aksi halde belgenin
# alakasız iki tarihi aralık sanılır.
_TARIH_AYIRAC_RE = re.compile(r"^\s{0,3}(?:[-–—/]|ile|ila|ve)?\s{0,3}$",
                              re.IGNORECASE)

# "1-31 Temmuz 2026" — başlangıç GÜNÜ, bitişin ay/yılını paylaşır.
_GUN_GUN_RE = re.compile(r"(\d{1,2})\s*[-–—]\s*$")

# Tarihin ROLÜNÜ belirleyen tetikleyiciler.
_BITIS_TETIK_RE = re.compile(
    r"(biti[şs]|son\s+ba[şs]vuru|son\s+g[üu]n|son\s+tarih|"
    r"tarihine\s+kadar|kadar\s+ge[çc]erli|sona\s+er)", re.IGNORECASE)
_BASLANGIC_TETIK_RE = re.compile(
    r"(ba[şs]lang[ıi][çc]|itibaren|ba[şs]layarak|ba[şs]layan)", re.IGNORECASE)

# Rol tetikleyicisi bu kadar karakter içinde aranır. 60, "Kampanya Başlangıç ve
# Bitiş Tarihi: Kampanya 1 Mayıs 2026" gibi araya söz giren başlıkları kapsar.
_ROL_PENCERE = 60


def _tarih_adaylari(text: str) -> list[tuple[int, int, str]]:
    """Metindeki ISO'ya çevrilebilen tarihleri (start, end, iso) olarak döndürür.

    Kanun atıfları ("22/11/2001 tarihli ve 4721 sayılı") ve takvimde var
    olmayan tarihler ("31.06.2026") elenir — `normalize_date` ikincisini zaten
    `None` yapar (bkz. `normalize._iso`).
    """
    out: list[tuple[int, int, str]] = []
    for m in _TARIH_RE.finditer(text):
        if _KANUN_ATIF_RE.match(text[m.end(): m.end() + 40]):
            continue
        iso = N.normalize_date(m.group(0))
        if iso is not None:
            out.append((m.start(), m.end(), iso))
    return out


def kampanya_tarih_araligi(text: str) -> Optional[dict]:
    """Kampanyanın BAŞLANGIÇ ve BİTİŞ tarihini BİRLİKTE çıkarır.

        "Kampanya 01.01.2026 - 31.12.2026 tarihlerinde geçerlidir"
            -> {"baslangic": "2026-01-01", "bitis": "2026-12-31", ...}
        "Kampanya 31.12.2026 tarihine kadar geçerlidir"
            -> {"baslangic": None, "bitis": "2026-12-31", ...}
        "Kampanya 1 Mayıs 2026 tarihinden itibaren başlar"
            -> {"baslangic": "2026-05-01", "bitis": None, ...}

    **Ölçülen kusur (2026-08-07, 1759 belgelik korpus):** eski çıkarıcı
    `re.search` ile metindeki İLK tarihi alıyordu. Başlangıç-bitiş çifti içeren
    492 belgenin **442'sinde (%90)** bu ilk tarih BAŞLANGIÇ tarihiydi; yani
    "geçerlilik bitiş tarihi" alanına kampanyanın başladığı gün yazılıyordu.
    Dashboard'da bu, süresi dolmuş kampanyayı "hâlâ geçerli" göstermek demek.

    Eksik olan tarih **UYDURULMAZ**, `None` kalır (CLAUDE.md §19). Yalnızca
    başlangıcı bilinen bir kampanyanın bitişini tahmin etmek, anotasyon
    kılavuzunun da `unclear` dediği durumu sahte kesinliğe çevirirdi.

    Returns:
        `{"baslangic": iso|None, "bitis": iso|None, "span": (start, end)}`
        ya da hiç tarih yoksa `None`.
    """
    adaylar = _tarih_adaylari(text)
    if not adaylar:
        return None

    # 1) AÇIK ARALIK: iki tam tarih yan yana ve ilki daha erken.
    for (s1, e1, iso1), (s2, e2, iso2) in zip(adaylar, adaylar[1:], strict=False):
        if e1 <= s2 and _TARIH_AYIRAC_RE.match(text[e1:s2]) and iso1 < iso2:
            return {"baslangic": iso1, "bitis": iso2, "span": (s1, e2)}

    # 2) GÜN-GÜN ARALIĞI: "1-31 Temmuz 2026" — başlangıç yalnız GÜN olarak yazılı.
    for s, e, iso in adaylar:
        gg = _GUN_GUN_RE.search(text[max(0, s - 8): s])
        if not gg:
            continue
        # Başlangıç, bitişin YIL ve AYINI paylaşır; yalnız günü farklıdır.
        # ISO parçalarından kurulur (`_iso` takvim geçerliliğini doğrular:
        # "1-31 Şubat 2026" gibi bir yazımda 31 Şubat üretilmez).
        bas = N.normalize_date(f"{iso[:4]}-{iso[5:7]}-{gg.group(1)}")
        if bas is not None and bas < iso:
            return {"baslangic": bas, "bitis": iso,
                    "span": (max(0, s - 8) + gg.start(1), e)}

    # 3) TEK TARİH: rolünü tetikleyici söyler.
    for s, e, iso in adaylar:
        if _BITIS_TETIK_RE.search(text[max(0, s - _ROL_PENCERE): e + _ROL_PENCERE]):
            return {"baslangic": None, "bitis": iso, "span": (s, e)}

    s, e, iso = adaylar[0]
    if _BASLANGIC_TETIK_RE.search(text[max(0, s - _ROL_PENCERE): e + _ROL_PENCERE]):
        # Yalnızca başlangıç biliniyor. Bitişi UYDURMAK yerine boş bırakılır.
        return {"baslangic": iso, "bitis": None, "span": (s, e)}

    # Rolsüz tek tarih: kampanya metinlerinde bu neredeyse her zaman son
    # geçerlilik günüdür ("Kampanya 31.12.2026'da sona erer" kalıbının
    # tetikleyicisiz varyantı). Eski davranış korunur.
    return {"baslangic": None, "bitis": iso, "span": (s, e)}


def extract_kampanya_suresi(text: str) -> Optional[ExtractedField]:
    """Kampanya süresi → BİTİŞ tarihi (ISO-8601).

    Kanonik değer neden aralık değil TEK tarih: hem gold şeması
    (`scripts/gold_schema.DATE_FIELDS`, eşleştirici tarihte metin bekler) hem
    anotasyon kılavuzu (`data/gold/ANNOTATION_GUIDE.md` §`kampanya_suresi`) bu
    alanı **"geçerlilik bitiş tarihi"** diye tanımlıyor: "1 – 31 Temmuz 2026"
    -> `2026-07-31`. Aralığın kendisi kaybolmuyor — `kampanya_tarih_araligi()`
    ikisini birlikte döndürür ve `source_span` penceresi her iki tarihi de
    gösterir; `raw_value` da aralığın TAMAMINI kapsar, tek bir tarihi değil.

    Bitiş tarihi bilinmiyorsa (yalnız başlangıç var) alan HİÇ üretilmez.
    """
    aralik = kampanya_tarih_araligi(text)
    if aralik is None or aralik["bitis"] is None:
        return None

    s, e = aralik["span"]
    raw = text[s:e]
    # Tarih genelde "kampanya süresi/son başvuru/tarihine kadar" ifadesinin
    # yakınındadır; tetikleyici varsa uzaklığı ölç, yoksa None (ceza).
    trig = None
    for tm in re.finditer(r"(kampanya|son\s+ba[şs]vuru|ge[çc]erli|tarihine\s+kadar)",
                          text, re.IGNORECASE):
        d = abs(s - tm.start())
        trig = d if trig is None else min(trig, d)
    return _field("kampanya_suresi", raw, aralik["bitis"], _window(text, s, e),
                  span_start=s, span_end=e, trigger_distance=trig,
                  candidate_count=len(_tarih_adaylari(text)))
