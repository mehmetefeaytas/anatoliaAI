"""Tahsis ücreti / dosya masrafı çıkarımı — AYRI modül.

## Neden bu sınır burada

`extract_tahsis_ucreti` tek başına bir hesap katmanı taşıyor (oransal
ücret -> taban tutarla çarpım, `_ucret_degeri`) ve bu hiçbir başka alanda
yok. `_SAYI_BASI`/`_PARA_IFADESI` `_ortak.py`den geliyor (üç alan modülü
paylaşıyor, gerekçe orada); `_ORAN_IFADESI` ise SADECE bu modülün
`_BITISIK_TABAN_RE`/`_ADLA_TABAN_RE` desenlerinde kullanıldığı için burada
yerel bırakıldı — `_SAYI_BASI`ya bağımlı olduğu için içe aktarımdan hemen
sonra tanımlanıyor.
"""

from __future__ import annotations

import re
from typing import Optional

from ...normalization import normalize as N
from ...schemas import ExtractedField
from ._ortak import _PARA_IFADESI, _SAYI_BASI, _field, _truncate_at_next_column, _window
from .synonyms import NEGATION_RE

# Cümlecikteki İLK sayısal belirteç: oran mı, tutar mı?
#
# Sıra tek başına ayırt edici: ücretini oran olarak veren metinlerde oran ilk
# gelir ("Tahsis Ücreti TL %0,25"), tutar olarak veren tablolarda tutar ilk
# gelir ("Tahsis Ücreti 30.000,00 ₺ 12 Ay 1,69%"). Bu ayrım olmadan
# `normalize_money` cümlecikteki ilk sayıyı körü körüne TL sanıyordu ve
# **%0,25'lik bir oran 0,25 TL'lik bir ücrete** dönüşüyordu (hayat-finans
# ürün-hizmet ücretleri sayfasında ölçüldü) — sessiz, ~400 kat yanlış bir değer.
_ILK_SAYISAL_RE = re.compile(
    r"(?P<oran>binde\s*\d[\d.,]*|y[üu]zde\s*\d[\d.,]*|%\s*\d[\d.,]*|\d[\d.,]*\s*%)"
    r"|(?P<para>\d[\d.,]*\s*(?:tl|₺|try|türk\s*liras[ıi]))",
    re.IGNORECASE,
)

#: Oran ifadesi — yalnız bu modülde kullanılıyor (`_BITISIK_TABAN_RE`,
#: `_ADLA_TABAN_RE`). `_SAYI_BASI` korumasına bağımlı; tam gerekçe ve ölçüm
#: `_ortak.py`nin "SAYININ ORTASINDAN BAŞLAMA YASAĞI" bölümünde.
_ORAN_IFADESI = (rf"binde\s*{_SAYI_BASI}\d[\d.,]*|y[üu]zde\s*{_SAYI_BASI}\d[\d.,]*|"
                 rf"%\s*{_SAYI_BASI}\d[\d.,]*|{_SAYI_BASI}\d[\d.,]*\s*%")

# A) TABAN SAYIYLA BİTİŞİK: "100.000 TL'nin %2,5'i", "50.000 TL üzerinden %1".
# İyelik eki ZORUNLU. Opsiyonel bırakılırsa tablo satırındaki komşu kolon
# ("30.000,00 ₺ 12 Ay 1,69%") taban sanılır ve gold'daki gerçek bir TP kaybolur.
_BITISIK_TABAN_RE = re.compile(
    rf"({_PARA_IFADESI})\s*['’]?\s*"
    r"(?:n[ıiu]n|nin|nün|üzerinden|uzerinden)\s*"
    rf"({_ORAN_IFADESI})",
    re.IGNORECASE,
)

# B) TABAN ADLA ANILIYOR: "finansman tutarının binde 5'i", "limitin yüzde 0,20'si".
#
# Gerçek veride baskın biçim budur — oranın tabanı sayı olarak değil ADLA
# yazılır ve sayı belgenin başka yerindedir. Belge düzeyindeki
# `finansman_tutari` ancak metin tabanı böyle adlandırdığında yerine konabilir.
#
# Adlandırma yoksa hesap YAPILMAZ. Ölçülmüş karşı-örnek
# (`tom-katilim--hesaplama-araclari`): "%0.5 tahsis ücreti YAPILAN HARCAMA
# üzerine eklenir" — taban harcamadır, belgedeki 150.000 TL'lik kaydırıcı
# sınırı değil. O tabanla çarpmak 750 TL'lik uydurma bir ücret üretirdi.
_ADLA_TABAN_RE = re.compile(
    r"(?:finansman\s*tutar\w*|kredi\s*tutar\w*|anapara\w*|limitin|tutar[ıi]n[ıi]n)"
    rf"[^.;]{{0,40}}?({_ORAN_IFADESI})",
    re.IGNORECASE,
)


def _ucret_degeri(clause: str, taban: Optional[float]):
    """Ücret cümleciğini kanonik değere çevirir: `(deger, formul)`.

    Üç yol, bu sırayla:
      A. Taban sayıyla bitişik  -> HESAPLA, formülü döndür.
      B. Taban adla anılıyor    -> çağıranın verdiği tutarla HESAPLA.
      C. Ne A ne B              -> komşu kolonu kes, İLK sayısal belirteç
         karar versin: tutarsa para, oransa **değer üretme**.

    C'de oran görülüp taban bilinmiyorsa `(None, None)` döner ve alan hiç
    üretilmez. "Tahsis ücreti binde 5" ifadesi tutar bilinmeden bir TL değeri
    taşımaz; uydurulmuş bir tabanla çarpmak da, oranı TL sanmak da sessizce
    yanlış değer üretir (CLAUDE.md §19).
    """
    m = _BITISIK_TABAN_RE.search(clause)
    if m is not None:
        oran = N.parse_oran_ifadesi(m.group(_BITISIK_TABAN_RE.groups))
        yerel = (N.normalize_money(m.group(1)) or {}).get("value")
        hesap = N.hesapla_oransal_ucret(oran, yerel) if oran is not None else None
        return hesap if hesap is not None else (None, None)

    # B) TABAN ADLA ANILIYOR ("finansman tutarının binde 5'i") -> DEĞER ÜRETİLMEZ.
    #
    # Bu yol 2026-08-07'de bilerek eklenmişti (mentörlük bulgusu: "yüzdeli
    # ifadelerde hesaplama yapmıyor") ve `taban` belge düzeyindeki
    # `finansman_tutari`ndan geliyordu. Kılavuz §4.13/5 (2026-08-09, yani
    # SONRA) bunu birebir yasakladı: "Hesaplamayın — finansman tutarı aynı
    # belgede geçse bile çarpmak çıkarım değil TÜRETMEDİR."
    #
    # Ölçüm kılavuzu haklı çıkardı (2026-08-15, 436 inceleme belgesi): altı
    # belgede metinde HİÇ GEÇMEYEN bir TL değeri üretiliyordu. En açığı
    # `turkiye-finans--ihtiyac-finansmani`: "Tahsis ücreti ... finansman
    # tutarının %0,50'si" cümlesi, belgenin başka bir yerindeki 125.000 TL ile
    # çarpılıp 625 TL yazıyordu. Oysa o 125.000 TL finansman tutarı bile
    # değil, bir VADE EŞİĞİ ("125.000 TL'ye kadar olması durumunda 24 ayı ...
    # aşamaz"). Yani çifte uydurma: yanlış tabanla yapılmış bir hesap.
    #
    # Doğru davranış kılavuzda yazılı: `tahsis_ucreti` boş kalır (anotatör
    # `unclear` + `#oransal_ucret` yazar), masraf VARLIĞI `masraf_durumu`
    # alanında `{"has_fee": true, "amount": null}` olarak taşınır.
    if _ADLA_TABAN_RE.search(clause):
        return None, None

    # KOMŞU SÜTUN KESİLİR — `extract_masraf` ile aynı gerekçe. Oran tablosunun
    # başlık satırında "Tahsis Ücreti"nden sonra "Aylık Toplam Maliyet ...
    # 3 3,96% 0,50%" geliyor; kesme olmadan ilk sayı 3,96 (KÂR ORANI kolonu)
    # tahsis ücreti sanılıyordu (`turkiye-finans--tasit-finansmani`'de ölçüldü).
    ilk = _ILK_SAYISAL_RE.search(_truncate_at_next_column(clause))
    if ilk is None or ilk.group("oran"):
        return None, None
    return N.normalize_money(ilk.group("para")), None


# "500 TL tahsis ücreti" — TUTAR TETİKLEYİCİDEN ÖNCE.
#
# Türkçede ücret adı sıfat tamlamasının SONUNA gelebiliyor ve bu biçim ileri
# pencereyle okunamaz. Gerçek vaka (Türkiye Finans arsa/işyeri/konut
# finansmanı, 2026-08-09 ölçümü): "Alınacak ücretler: 60 ay vadede **500 TL
# tahsis ücreti**, 3.000 TL ipotek tesis ücreti, 16.500 TL Ekspertiz ücreti."
# İleri pencere virgülden sonrasını okuyup **3.000 TL** (İPOTEK TESİS ücreti)
# üretiyordu — yanlış kalemin tutarı. Doğrusu 500 TL ve tetikleyicinin hemen
# SOLUNDA duruyor.
#
# Bitişiklik ŞART (`\s*$`): araya söz girerse bağ kopar ve cümlenin herhangi
# bir tutarı ücret sanılır.
_ONCEKI_TUTAR_RE = re.compile(
    r"(\d[\d.,]*\s*(?:TL|₺|TRY|türk\s*liras[ıi]))\s*$", re.IGNORECASE)


def extract_tahsis_ucreti(text: str,
                          taban_tutar: Optional[float] = None
                          ) -> Optional[ExtractedField]:
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

    ## Oransal (yüzdeli) ücretler — hesap katmanı

    Korpus ölçümü (2026-08-07, 1759 belge): tahsis/dosya tetikleyicisi olan 101
    belgenin **62'si** ücreti tutar olarak değil ORAN olarak veriyor
    ("Finansman Tutarı'nın (Anaparasının) %0,5'i", "binde 5") ve bu 62 belgede
    hesap katmanı yoktu. İkisi de sessizdi:
      - 51 belge hiçbir değer üretmiyordu (açık para birimi aranıyordu),
      - kalanlarda oran TL sanılıyordu — `%0,25` -> **0,25 TL**
        (`hayat-finans/products/urun-ve-hizmet-ucretleri`), ~400 kat sapma.

        "tahsis ücreti, 100.000 TL'nin %2,5'i"      -> {"value": 2500.0, ...}
        "tahsis ücreti finansman tutarının binde 5'i"
            (belgede finansman tutarı 200.000 TL)   -> {"value": 1000.0, ...}
        "tahsis ücreti binde 5'i" (tutar bilinmiyor) -> alan ÜRETİLMEZ

    Hesaplanan değer metinde geçmez; bu yüzden `source_span`'in sonuna
    `[hesap: 200.000 TL × %0,5 = 1.000 TL]` formülü eklenir. Değerin yanında
    formülü ve girdiyi saklamak açıklanabilirliğin (CLAUDE.md §18-1) şartıdır —
    aksi halde dashboard'da kaynağı gösterilemeyen bir sayı belirir.

    **Taban bilinmiyorsa alan hiç üretilmez.** Ölçülen alternatif — oranı
    `{"rate": X}` olarak yazmak — gold'da `tahsis_ucreti` F1'ini 0.400'den
    0.333'e düşürdü (2 belgede halüsinasyon): anotasyon kılavuzu bu alanı para
    olarak tanımlıyor, oran o sözleşmeyi taşımıyor.

    Args:
        text: belge metni.
        taban_tutar: belge düzeyindeki finansman tutarı. Yalnızca METİN tabanı
            adlandırdığında ("finansman tutarının %0,5'i") kullanılır;
            adlandırmıyorsa hesap yapılmaz (bkz. `_ADLA_TABAN_RE`).
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
        aciklama = None
        # Sol pencere: tetikleyiciye BİTİŞİK tutar (gerekçe `_ONCEKI_TUTAR_RE`).
        onceki_ham = text[max(0, m.start() - 40): m.start()]
        onceki_ham = re.split(r"(?<!\d)[.;](?!\d)|\n", onceki_ham)[-1]
        onceki = _ONCEKI_TUTAR_RE.search(onceki_ham)
        sol_bas = None

        if re.search(NEGATION_RE, clause, re.IGNORECASE):
            canon = {"value": 0.0, "currency": "TRY"}
        elif onceki is not None:
            # Bitişik sol tutar ileri pencereyi YENER: bağ daha sıkıdır.
            canon = N.normalize_money(onceki.group(1))
            if canon is None:
                continue
            sol_bas = m.start() - (len(onceki_ham) - onceki.start(1))
        else:
            # AÇIK PARA BİRİMİ ŞART. `normalize_money` para birimi işareti
            # olmasa da varsayılan "TRY" döndürür; bu, ücret tetikleyicisinin
            # yakınındaki HER çıplak sayıyı tutar sanmaya yol açıyordu.
            # Gerçek vaka: ürün adı "2B Finansmanı" olan sayfada "2" sayısı
            # 2,00 TL tahsis ücreti olarak okunuyordu (849 belgelik korpusta
            # değişmez denetimi yakaladı). `_ucret_degeri` bu şartı korur.
            canon, aciklama = _ucret_degeri(clause, taban_tutar)
            if canon is None:
                continue    # tetikleyici var ama ne tutar ne hesaplanabilir oran

        # raw_value BİTİŞİK dilim olmalı, yoksa span doğrulaması kırılır.
        # Değer soldan geldiyse span da SOLDAN başlar ve tetikleyicide biter
        # ("500 TL tahsis ücreti"); aksi halde kanıt değeri göstermezdi.
        s, e = ((sol_bas, m.end()) if sol_bas is not None
                else (m.start(), m.end() + len(clause)))
        # Hesaplanan tutar metinde GEÇMEZ; `source_span` tek başına onu
        # açıklayamaz. Formül pencereye eklenir, böylece dashboard "2.500 TL"
        # değerinin yanında "100.000 TL × %2,5 = 2.500 TL" gerekçesini de
        # gösterebilir (açıklanabilirlik, CLAUDE.md §18-1).
        pencere = _window(text, s, e)
        if aciklama:
            pencere = f"{pencere}  [hesap: {aciklama}]"
        alan = _field("tahsis_ucreti", text[s:e], canon, pencere,
                      span_start=s, span_end=e, trigger_distance=0)
        if canon.get("value", 0) > 0:
            return alan                 # pozitif ücret her sırada kazanır
        if ilk_sifir is None:
            ilk_sifir = alan
    return ilk_sifir
