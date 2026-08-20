"""Hedef kitle çıkarımı — `extract.py` bölünmesinde AYRI modül.

## Neden bu sınır burada

`_EVRENSELLIK_RE` yalnız bu alana özgü ve başka hiçbir modül tarafından
kullanılmıyor.

`gezinme_seridi` ise 2026-08-20'de `_ortak.py`ye TAŞINDI ve kamuya açıldı:
aynı sayfa-çerçevesi kirliliği `campaign_type` sınıflandırıcısını da
etkiliyor ve arayüz katmanı da onu tanımak zorunda, yani ölçüt artık iki
alanın ötesinde paylaşılıyor. Eski private ad (`_gezinme_seridi`) burada
geriye dönük uyum için duruyor: `extract.py` ve
`tests/test_hedef_kitle_etiket.py` onu bu modülden içe aktarıyor.
"""

from __future__ import annotations

import re
from typing import Optional

from ...preprocessing.clean import split_sentences
from ...schemas import ExtractedField
from ._ortak import _field, _window, gezinme_seridi

# --------------------------------------------------------------------------- #
# `hedef_kitle` — GEZİNME ŞERİDİ ve EVRENSELLİK süzgeçleri
#
# ## Ölçülen kök neden (2026-08-20, gold.v2)
#
# Alan kalem F1 0,343 (tp 6 · fp 12 · fn 11) idi. Yanlış pozitiflerin
# **yarısı tek bir mekanizmadan** geliyordu: eski çıkarıcı deseni BELGENİN
# TAMAMINDA `re.search` ile arıyordu, yani üst menüde / ürün listesinde /
# komşu kampanya başlığında geçen bir sözcük bu kampanyanın hedef kitlesi
# sayılıyordu. Ölçülen beş vaka:
#
#   "… Bireysel Emeklilik Sistemi Sigortacılık Hizmetleri …"   -> belirli_segment
#   "… Kredi Kartı Kampanyaları Maaş Ödemesi Kampanyaları …"   -> maas_musterisi
#   "Anonim ve Limited Şirketler … Serbest Meslek Sahipleri"   -> belirli_segment
#   "Worldcard Kampanyaları Yeni Müşterilerimize Özel …"       -> yeni + mevcut
#
# Hiçbiri cümle değil; hepsi HTML menüsünün/kart listesinin metne inmiş hâli.
# İmzası da sözdizimseldir: büyük harfle başlayan sözcük yoğunluğu yüksek ve
# cümle sonu noktalaması yok. `kabuk.py` bu vakaları YAKALAMAZ ve yakalaması
# da beklenmez — o kuyruktaki komşu kampanya bloğunu tanımlar, buradaki
# kirlilik ise sayfanın BAŞINDA (menü) duruyor. Ölçüldü: kabuk süzgecini bu
# alana bağlamak sonucu HİÇ değiştirmiyor (F1 0,600 -> 0,600).
#
# ÖLÇÜT ARTIK `_ortak.gezinme_seridi` — tek doğruluk kaynağı. Aşağıdaki ad
# yalnızca geriye dönük uyum takma adıdır (bkz. modül başlığı); davranışı
# birebir aynıdır.
_gezinme_seridi = gezinme_seridi


#: EVRENSELLİK — "herkes" segment DEĞİLDİR (kılavuz §4 `hedef_kitle`:
#: *"Bireysel müşteriler = herkes … Tek sinyal buysa `absent`"*). Aynı mantık
#: açık açık "herkes" / "her kesim" / "tüm müşteriler" diyen cümle için de
#: geçerli: orada geçen segment sözcüğü bir KISIT değil, kapsayıcılık
#: retoriğidir — "Girişimcilerden KOBİ'lere, yatırımcılardan öğrencilere
#: herkesin … ihtiyaçlarını karşılamaya" (kurumsal tanıtım metni).
_EVRENSELLIK_RE = re.compile(
    r"(herkes\w*|her\s*kesim|t[üu]m\s+m[üu][şs]teri)", re.IGNORECASE)


def extract_hedef_kitle(text: str) -> Optional[ExtractedField]:
    """Hedef kitle — §5.3'ün 4 segmenti, ÇOK ETİKETLİ.

        yeni_musteri | mevcut_musteri | maas_musterisi | belirli_segment

    Sinyal yoksa `None` döner — "mevcut müşteri" varsayılanı YAPILMAZ
    (halüsinasyon yasağı). Negasyon penceresi kontrol edilir: "yeni müşteri
    olmayanlar" ifadesi yeni_musteri etiketi ÜRETMEZ.
    """
    # ÖLÇÜLMÜŞ YANLIŞ DENEME — tekrarlanmasın (19 Ağu 2026).
    #
    # Kendi gold.v2'mizde bu alan 12 yanlış pozitif üretiyor ve dördü açıkça
    # kılavuzun §4.13/2 kuralına aykırı görünüyordu: "Bireysel Emeklilik" bir
    # ÜRÜN ADI, "Hoş Geldiniz" bir PAZARLAMA SELAMI. İkisini lookahead ile
    # elemek denendi (`emekli(?!lik)`, `ho[şs]\s*geldin(?!iz)`).
    #
    # Sonuç: F1 0,267 -> 0,214 (tp 4->3) — DAHA KÖTÜ. Gold o iki ifadeyi
    # sinyal SAYIYOR: `vakif-katilim--musteri-alisveris-*` kaydında
    # "hoş geldiniz" gold'da `yeni_musteri`, `vakif-katilim--detay-troy-*`
    # kaydında "emeklilik" gold'da `belirli_segment` üretiyor. Kural
    # metinde ne yazdığına değil, gold'un o ifadeyi nasıl yorumladığına
    # bağlı; bu alanda sözleşme henüz o ayrımı yapmıyor.
    #
    # Bu yüzden desen DOKUNULMADAN bırakıldı. Alanın gerçek sorunu kod
    # değil sözleşme: kaçırılan 10 etiketin yarısı da kılavuzun yasakladığı
    # ürün/kart kısıtlarından üretilmiş (bkz.
    # data/gold/review/_hakem-turu-02-hedef-kitle.md). Motoru tutarsız bir
    # hedefe uydurmak metriği süsler, sistemi bozar.
    segments = {
        "yeni_musteri": r"(yeni\s*müşteri|yeni\s*musteri|ilk\s*kez|hoş\s*geldin|"
                        r"hos\s*geldin|yeni\s*üye)",
        "mevcut_musteri": r"(mevcut\s*müşteri|mevcut\s*musteri|halihazırda|"
                          r"müşterilerimize\s*özel)",
        "maas_musterisi": r"(maaş\s*müşteri\w*|maas\s*musteri\w*|maaşını\s*"
                          r"bankamızdan|maaş\s*ödemesi)",
        # SÖZLÜK GENİŞLETİLDİ (2026-08-20) — ölçüldü, kaçırılan 11 etiketin
        # 6'sı buradan geliyordu. Eklenen üç aile ve gerekçesi:
        #
        #   MESLEK  Kılavuz §4.13/2: *"'Emekli müşterilerimize' → kişi
        #           niteliği"*. Meslek adı da kişi niteliğidir ve korpusta
        #           kampanyanın tek hedef sinyali oluyor: "…hak ediş ödemesini
        #           ilk defa bankamızdan alan eczacı müşterilerimize".
        #   ÜYELİK  Kulüp/kademe üyeliği bir kişi kısıtıdır: "Kampanya'dan
        #           faydalanmak için Hadi Gold üyesi olmalısın", "Çok
        #           Kazananlar Kulübü üyesi olan …".
        #   SEÇİLİ  "seçili müşteriler", "nitelikli yatırımcı", "hak sahibi"
        #           — banka tarafından belirlenmiş alt küme.
        #
        # `doktor(?!a)`: lookahead ÖLÇÜMLE eklendi — çıplak `doktor` danışma
        # komitesi özgeçmişlerindeki "doktora" (derece) sözcüğüne ateşleyip
        # kurumsal bir sayfada uydurma etiket üretiyordu.
        "belirli_segment": r"(emekli|öğrenci|ogrenci|esnaf|kamu\s*çalışan\w*|"
                           r"kobi|serbest\s*meslek|"
                           r"eczac\w*|doktor(?!a)|hekim|avukat|öğretmen|"
                           r"[çc]iftçi|sağlık\s*çalışan\w*|"
                           r"nitelikli\s*yat[ıi]r[ıi]mc\w*|"
                           r"se[çc]ili\s*m[üu][şs]teri\w*|hak\s*sahip\w*|"
                           r"[üu]yesi\s*ol\w*|kul[üu]p\s*[üu]ye\w*|"
                           r"gold\s*[üu]ye\w*)",
    }
    # ARAMA ARTIK CÜMLE CÜMLE — belgenin tamamında değil. Gerekçe ve ölçüm
    # `_gezinme_seridi` başlığında: menü/liste şeridinde geçen sözcük bu
    # kampanyanın hedef kitlesi DEĞİLDİR.
    found: list[str] = []
    first_span = None
    offset = 0
    for cumle in split_sentences(text):
        yer = text.find(cumle, offset)
        if yer < 0:
            yer = offset
        offset = yer + len(cumle)
        if _gezinme_seridi(cumle) or _EVRENSELLIK_RE.search(cumle):
            continue
        for label, pat in segments.items():
            if label in found:
                continue
            m = re.search(pat, cumle, re.IGNORECASE)
            if not m:
                continue
            # negasyon penceresi: "... olmayanlar", "... hariç", "... dışında"
            after = cumle[m.end(): m.end() + 25]
            if re.search(
                    r"(olmayan\w*|hari[çc]|d[ıi][şs][ıi]nda|ge[çc]erli\s*de[ğg]il)",
                    after, re.IGNORECASE):
                continue
            found.append(label)
            if first_span is None:
                first_span = (yer + m.start(), yer + m.end())

    if not found or first_span is None:
        return None
    found = sorted(found)
    s, e = first_span
    # Birden çok etiket bulunduysa bu bir seçim kararıdır; tek etiketli
    # vakayla aynı kesinlikte değildir.
    return _field("hedef_kitle", text[s:e], sorted(found), _window(text, s, e),
                  span_start=s, span_end=e, trigger_distance=0,
                  candidate_count=len(found))
