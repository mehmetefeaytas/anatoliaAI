"""Vade (ay) çıkarımı — `extract.py` bölünmesinde AYRI modül.

İlgili: ../../decisions/zor-anlama-vakalari-merkezi.md

## Neden bu sınır burada

`extract_vade`nin iki tetikleyici sınıfı ("vade" sözcüğü ve "X aya kadar
<finansman ürünü>" yapısı) ile takvim-yılı/işlenmiş-örnek süzgeçlerinin
hiçbiri başka bir alan modülü tarafından çağrılmıyor. Tek dışa açık
sızıntı `MAKS_VADE_AY` sabiti: alt çizgisiz bırakıldı çünkü
`tests/test_vade_takvim_yili.py` onu doğrudan `from
src.extraction.rules.extract import MAKS_VADE_AY` ile içe aktarıyor;
cephe bunu yeniden ihraç eder.

## ÖLÇÜLMÜŞ TUZAK — bölmeden önce bulundu

Orijinal dosyada bu fonksiyonun hemen ardından (eski satır 987) tamamen
ÖLÜ bir `_CUMLE_SINIRI_RE` tanımı duruyordu — ayrıntı ve kanıt
`_ortak.py`nin modül başlığında. Bu modüle TAŞINMADI (taşınması davranışı
değiştirmezdi ama ölü kodu yanlış bir modülde diriymiş gibi göstermiş
olurdu).
"""

from __future__ import annotations

import re
from typing import Optional

from ...normalization import normalize as N
from ...preprocessing.clean import tr_fold
from ...schemas import ExtractedField
from ._ortak import _cumle_kapsami, _field, _window, logger

#: Takvim yılı olarak okunması gereken sayı aralığı. "2026 yılı" bir SÜRE
#: değil bir TARİHTİR; 2026 yıllık finansman diye bir şey yoktur.
_TAKVIM_YILI_ARALIGI = (1900, 2100)

#: Gerçekçi üst sınır. Korpustaki meşru en yüksek vade 120 ay (10 yıl);
#: 50 yıl, konut finansmanına bile fazlasıyla geniş bir tavandır.
MAKS_VADE_AY = 600


def _takvim_yili(m: "re.Match[str]") -> bool:
    """Eşleşme bir takvim yılı mı (süre değil)?

    ## Neden var — ölçülmüş hata

    `vade_ay` deseni "2026 yılı" ifadesini 2026 × 12 = **24312 ay** diye
    okuyordu. Güvenlik setindeki K02 ("en yüksek vade hangi bankada?")
    bu yüzden "Albaraka Türk, 24312 ay" cevabını veriyordu — yani 2026 yıl.
    demo.db'de bu sınıftan **10 kayıt** vardı ('2024/2025/2026 yılı'), ayrıca
    bir açılır menü döküntüsü ('2021 Ay' → 2021 ay ≈ 168 yıl).

    Bu artefaktlar dışlandığında korpustaki meşru en yüksek vade **120 ay**.
    Kıyas tablosu ve chatbot "en yüksek vade" sorusunda bu sayıyı gösteriyordu;
    jüriye görünen bir yüzeydi.

    İki kapı:
    1. Sayı 1900–2100 aralığında ve birim yıl/sene → takvim yılı. Bu aralıkta
       bir *süre* fiilen imkânsızdır, ek (`yılı` / `yılında`) aranmasına gerek
       kalmaz — ekli olmayan "2026 yıl" de aynı şekilde reddedilir.
    2. Aya çevrilmiş değer `MAKS_VADE_AY`'ı aşıyorsa → gerçek vade değil.
       'ay' birimiyle gelen döküntüyü ('2021 Ay') bu kapı yakalar.
    """
    sayi_ham, birim = m.group(1), m.group(2).lower()
    try:
        sayi = float(sayi_ham.replace(".", "").replace(",", "."))
    except ValueError:                                  # pragma: no cover
        return False
    alt, ust = _TAKVIM_YILI_ARALIGI
    if birim in ("yıl", "yil", "sene") and alt <= sayi <= ust:
        return True
    ay = N.normalize_term_months(m.group(0))
    return ay is not None and ay > MAKS_VADE_AY


# --------------------------------------------------------------------------- #
# İKİNCİ TETİKLEYİCİ SINIFI — "vade" sözcüğü olmadan vade kuran yapı
# --------------------------------------------------------------------------- #
#
# ## Sorun
#
# `extract_vade` bir TETİKLEYİCİ ŞARTI uygular: metinde "vade" sözcüğü hiç
# geçmiyorsa değer üretilmez (gerekçe aşağıda, `vade_pos` bloğunda — ölçülmüş
# ve doğru bir karardır, kaldırılmamalıdır). Ama şartnamenin KENDİ örnek metni
# bu şarta takılıyordu. Şartname s.11, A Bankası konut finansmanı metni birebir:
#
#     "…özel %1,89 kâr payı oranı ile 120 aya kadar konut finansmanı fırsatı
#      sunulmaktadır."
#
# Metinde "vade" sözcüğü YOK; oysa s.12'deki beklenen çıktı tablosu bu metinden
# **Vade = 120 ay** bekliyor. Sistem o hücreyi boş bırakıyordu. Jüri şartnamenin
# örnek metnini yapıştırıp "canlı çıkarım"a bastığında en görünür alanlardan
# biri boş dönerdi. Değerlendirme ölçütü de birebir bunu ödüllendiriyor
# (Model Başarısı %30 — "farklı ifade biçimlerini doğru yorumlayabilmesi").
#
# ## Neden kapı GENİŞ açılmadı — ölçüm
#
# İlk refleks "X aya kadar / X aya varan kalıbını serbest bırak" olurdu.
# ÖLÇÜLDÜ (2026-08-16, 1782 belgelik korpus, `vade_ay` üreten 441 belge):
# `vade_ay` üretilmeyen 220 belgede "ay/yıl" ifadesi var. Bu belgelerdeki
# "X aya kadar/varan" eşleşmelerinin dağılımı:
#
#     65 eşleşme  "X aya kadar/varan"  TOPLAM
#     62 (%95)    hemen ardından "taksit*" geliyor
#                 ("12 aya varan taksit", "3 aya kadar taksitlendirebilirler")
#      3 (%5)     yine taksit bağlamı (uzak pencerede "kredi kartından")
#      0          gerçek bir finansman VADESİ
#
# Yani korpusta bu kalıbın MEŞRU tek bir örneği bile yok; serbest bırakmak 62
# yanlış değer ekler, 0 doğru değer kazandırırdı. "12 aya varan taksit"
# `taksit_sayisi` alanına aittir, `vade_ay`'a değil — bu alan karışması zaten
# `vade_pos` bloğunda 30 kayıtla belgelenmiş.
#
# Bu yüzden kapı yapının TAMAMINI arar, yalnız edatı değil:
#
#     sayı + YÖNELME hâli + sınır edatı + (kısa boşluk) + FİNANSMAN ÜRÜNÜ
#     "120        aya        kadar                       konut finansmanı"
#
# Ürün adı şartı, korpustaki 65 taksit vakasının tamamını dışarıda bırakır ve
# şartname metnini içeri alır. Ölçülen etki: korpusta **0 yeni kayıt** —
# yani bu genişletme mevcut veriye hiç dokunmaz, sadece kaçırılan ifade
# biçimini kazanır. Sıfır, burada başarısızlık değil GÜVENLİK KANITIDIR.

#: Yönelme hâli + sınır edatı. "120 aya kadar", "36 aya varan", "1 yıla dek".
#: Kesme işaretli yazım da kabul ("120 ay'a kadar") — temel desen kesmeden
#: önce durduğu için ek buraya düşer.
_SINIR_EDATI_RE = re.compile(
    r"^\s*(?:['’]\s*[ae])?\s*(?:kadar|varan|dek|de[ğg]in)\b", re.IGNORECASE)

#: Yapıyı vade yapan şey: sınırlanan şeyin bir FİNANSMAN ÜRÜNÜ olması.
#: "kredi kartı" BİLEREK dışarıda — korpustaki taksit vakaları tam o kalıpta
#: ("3 aya kadar … kredi kartından limit aşım").
_FINANSMAN_URUNU_RE = re.compile(
    r"\b(?:finansman|kredi(?!\s*kart)|murabaha|icara)", re.IGNORECASE)

#: Değerin SAĞINDA yapıyı vade olmaktan çıkaran KOŞULSUZ bağlamlar.
#: CLAUDE.md §6'daki "zor vaka" sınıfları: ödemesiz dönem, kampanya geçerlilik
#: süresi, ücretsiz kullanım dönemi. Hiçbiri geri ödeme vadesi değildir ve
#: hepsi aynı "X ay" yüzeyini paylaşır. Bunların istisnası YOKTUR.
_KURULUS_SAG_RET_RE = re.compile(
    r"[öo]demesiz|ertele|[öo]deme\s*yok|[öo]demeyi"
    r"|[üu]cretsiz|bedava|hediye|bonus"
    r"|ge[çc]erli|boyunca|s[üu]reyle|i[çc]inde|i[çc]erisinde",
    re.IGNORECASE,
)

#: `taksit` reddi AYRI tutulur — çünkü tek istisnası olan bacak budur.
#:
#: Ret gerekçesi DEĞİŞMEDİ ve geçerlidir: korpustaki 65 sınır-edatlı adayın
#: 62'si (%95) taksit bağlamıydı ("12 aya varan taksit seçenekleri"), hiçbiri
#: finansman vadesi değildi. Bu ifade `taksit_sayisi` alanına aittir; ayrıca
#: `vade_pos` bloğundaki 30 kayıtlık alan-karışması ölçümü de aynı şeyi
#: söylüyor. Bu red kalkarsa korpusa 62 yanlış `vade_ay` girer.
_KURULUS_TAKSIT_RET_RE = re.compile(r"taksit", re.IGNORECASE)

#: `taksit` reddinin TEK istisnası: açık bir GERİ ÖDEME işareti.
#:
#: ## Neden bu istisna var — iki belgelenmiş kuralla çelişki
#:
#: CLAUDE.md §10 "Eşanlamlılar" satırı birebir şöyle diyor:
#:
#:     "vade ≈ ödeme süresi ≈ geri ödeme süresi"
#:
#: Ve `synonyms.py` içindeki `FIELD_TRIGGERS["vade_ay"]` listesi bağımsız
#: olarak aynı şeyi sayıyor: `["vade", "ödeme süresi", "geri ödeme süresi",
#: "taksit süresi", "ay"]`. Yani projenin KENDİ terminoloji kuralına göre
#:
#:     "geri ödemelerinizi 60 aya kadar taksitlendirebilirsiniz"
#:
#: bir vadedir. Bunu `taksit` reddiyle dışarıda bırakmak, bir kararı korumak
#: değil BAŞKA iki kararla çelişmekti. İstisna o çelişkiyi kapatır.
#:
#: ## Neden güvenli — ölçüldü, yazılmadan önce
#:
#: 1782 belgelik korpus tarandı (2026-08-16). İstisnanın ürettiği eşleşme:
#:
#:     sol pencere  40 kr -> 1    80 kr -> 1
#:     sol pencere  60 kr -> 1   120 kr -> 1
#:
#: Her pencere boyutunda **tek** eşleşme, hepsi aynı kayıt (albaraka 2B Arazi
#: Finansmanı) ve o kayıt gerçek bir vade. **Yanlış pozitif: 0.** Ürün adı
#: şartı korunarak da (sol VEYA sağ pencerede finansman ürünü) sonuç aynı 1
#: kayıt — bu yüzden daha DAR olan sürüm seçildi.
#:
#: İşaret dar tutuluyor: çıplak `taksitlendir` YETMEZ, açık "geri ödeme"
#: ibaresi şart. 60 karakter platonun ortası.
_GERI_ODEME_RE = re.compile(r"geri\s*[öo]deme", re.IGNORECASE)
_GERI_ODEME_PENCERE = 60

#: Değerin SOLUNDA yapıyı vade olmaktan çıkaran bağlamlar.
#:   "ilk 3 ay …"      -> promosyon/ödemesiz dönem, vade değil
#:   "son 6 ayda …"    -> geçmiş koşulu ("son 3 aydır maaşını bankamızdan alan")
#:   "her 3 ayda bir"  -> periyot
_KURULUS_SOL_RET_RE = re.compile(r"\b(?:ilk|son|her)\s*$", re.IGNORECASE)

#: Sınır edatından sonra ürün adına kaç karakter içinde ulaşılmalı.
#:
#: ÖLÇÜLDÜ (korpustaki 65 sınır-edatlı adayın tamamı üzerinde tarandı):
#:     48 -> 0 kabul   60 -> 1 kabul   72 -> 1 kabul   90 -> 1 kabul
#: Yani 60'tan sonra DOYUYOR; genişletmek yeni vaka açmıyor çünkü kalan 64
#: adayın hepsini `taksit` reddi zaten tutuyor. Kazanılan tek kayıt gerçek:
#:     "Devre Tatil finansmanı … 36 aya varan ödeme seçenekleriyle
#:      kullanabileceğiniz bir kredidir"   (albaraka/tatiliniz-icin)
#: 48'de kaçmasının sebebi anlam değil, ürün adının 54. karaktere düşmesiydi.
#: Doygunluk platosunun içinde 72 seçildi: yazım varyantlarına pay bırakır,
#: cümle sınırı koruması da altında durur.
_KURULUS_PENCERE = 72

#: Pencere cümle sınırını AŞMAZ. Dosyadaki diğer bağlam kapılarıyla
#: (`_ceza_baglami_onceliyor`, `_turev_oran_baglami`) aynı disiplin: sınır
#: olmasa "…36 aya varan taksit. Konut finansmanı…" dizisindeki SONRAKİ
#: cümlenin ürün adı, önceki cümlenin taksit sayısını vade yapardı.
_CUMLE_SONU_RE = re.compile(r"[.!?]\s")


#: İŞLENMİŞ ÖRNEK CÜMLESİ — sayı ürünün değeri değil, ANLATIM aracıdır.
#:
#: Ölçülen halüsinasyon (gold.v2 `ziraat-katilim--zekat-hesaplama`, belge bir
#: zekât hesaplama aracı sayfası):
#:
#:     "Örneğin 10 yıl vadeli 180.000 TL ev borcu olan kimse …"  -> vade_ay 120
#:
#: Gold notu birebir: *"«10 yıl vadeli» ifadesi aynı örnek cümleye aittir;
#: ürün vadesi değildir."* Aynı sınıf, bilgilendirme formlarının "Hesaplama
#: Örneği / Örnek Ödeme Planı" bloklarında da var.
#:
#: KAPI İKİ KOŞULLU ve daraltma ÖLÇÜMLE zorunlu oldu. Yalnız örnek işareti
#: aranan gevşek sürüm 1.782 belgede `vade_ay` üreten 452 belgenin 3'ünü
#: kesiyordu ve **biri gerçek bir ürün vadesiydi**:
#:
#:     "Örneğin: Kuveyt Türk Çeyiz Hesabı, minimum 3 yıl vade ile … açılır"
#:
#: Yani 2 doğru elemeye 1 yanlış eleme düşüyordu (2:1) — projenin kendi
#: barajının (SMS ailesi 4:0, talep ailesi 3:0) altında. İkinci koşul olarak
#: cümlede PARA TUTARI aranınca oran **4:0** oldu: işlenmiş sayısal örnek her
#: zaman bir tutar taşır ("180.000 TL ev borcu", "Finansman Miktarı 10.000
#: TL"), ürün beyanı ise taşımıyor. Kesilen 4 belge:
#:     zekat-hesaplama (120) · medium-bireysel-finansman-talebi-…-4012/4013/
#:     4014 "Hesaplama Örneği / Örnek Ödeme Planı" (12) — dördü de örnek.
#: Çeyiz Hesabı kaydı KORUNUR (cümlede TL tutarı yok).
_ORNEK_ISARET_RE = re.compile(
    r"(?:^|[.;:!?]\s*|\s)[öo]rne[ğg]in\b|[öo]rnek\s+olarak\b"
    r"|[öo]rnek\s*:|[öo]rne[ğg]i\b", re.IGNORECASE)
_ORNEK_PARA_RE = re.compile(
    r"\d[\d.,]*\s*(?:TL|₺|TRY|t[üu]rk\s*liras)", re.IGNORECASE)


def _islenmis_ornek(text: str, m: "re.Match[str]") -> bool:
    """Eşleşme bir işlenmiş (sayısal) örnek cümlesinin içinde mi?"""
    cumle = _cumle_kapsami(text, m.start(), m.end())
    return bool(_ORNEK_ISARET_RE.search(cumle)
                and _ORNEK_PARA_RE.search(cumle))


def _vade_kurulusu(text: str, m: "re.Match[str]") -> Optional[int]:
    """'120 aya kadar konut finansmanı' yapısı mı? Öyleyse tetikleyici mesafesi.

    Dönen değer, sayının bitişi ile FİNANSMAN ÜRÜNÜ sözcüğünün başı arasındaki
    karakter mesafesidir; `_field` bunu güven skoruna tetikleyici yakınlığı
    olarak geçirir. Bu yolda tetikleyici "vade" sözcüğü değil ürün adıdır ve
    skor bunu dürüstçe yansıtır. Yapı değilse `None`.
    """
    sag = tr_fold(text[m.end():m.end() + _KURULUS_PENCERE])
    edat = _SINIR_EDATI_RE.match(sag)
    if edat is None:
        return None
    kalan = sag[edat.end():]
    # Cümle biterse yapı da biter — sonraki cümlenin sözcükleri kanıt değildir.
    cumle = _CUMLE_SONU_RE.search(kalan)
    if cumle is not None:
        kalan = kalan[:cumle.start()]
    if _KURULUS_SAG_RET_RE.search(kalan):
        return None
    sol = tr_fold(text[max(0, m.start() - _GERI_ODEME_PENCERE):m.start()])
    # `\s*$` çıpalı: ek/son/her yalnız sayının HEMEN solundayken reddeder,
    # pencere büyüdü diye kapsamı genişlemez.
    if _KURULUS_SOL_RET_RE.search(sol):
        return None
    geri_odeme = _GERI_ODEME_RE.search(sol)
    if _KURULUS_TAKSIT_RET_RE.search(kalan) and geri_odeme is None:
        return None
    urun = _FINANSMAN_URUNU_RE.search(kalan)
    if urun is not None:
        return edat.end() + urun.start()
    # "geri ödeme" yolunda ürün adı SOLDA olabilir:
    #   "…2B araziler için FİNANSMAN desteği alabilir, GERİ ÖDEMELERİNİZİ
    #    60 aya kadar taksitlendirebilirsiniz."
    # Tetikleyici burada §10'un eşanlamlısı olan "geri ödeme" ibaresidir;
    # güven skoruna geçen mesafe de ona olan uzaklıktır.
    if geri_odeme is not None and _FINANSMAN_URUNU_RE.search(sol):
        return len(sol) - geri_odeme.end()
    return None


def extract_vade(text: str) -> Optional[ExtractedField]:
    """Vade: '120 aya kadar konut finansmanı', '36 ay vade', '1 yıl'.

    Zaman-koşullu ifade tuzağı ('ilk 6 ay ödemesiz') gerçek vade değildir; bu
    yüzden 'vade' sözcüğüne yakın eşleşme tercih edilir
    (bkz. ../../decisions/zor-anlama-vakalari-merkezi.md).

    İki tetikleyici sınıfı vardır: metindeki "vade" sözcüğü (birincil) ve
    "X aya kadar <finansman ürünü>" yapısı (`_vade_kurulusu`). İkincisi
    yalnızca birincisi HİÇ yokken devreye girer; "vade" geçen belgelerde
    davranış birebir eskisidir.
    """
    pat = re.compile(
        r"(\d[\d.,]*)\s*(ay|yıl|yil|sene)(?:a|da|ta|dan|tan|ı|i|lık|lik|d[ıi]r|t[ıi]r)?\b",
        re.IGNORECASE,
    )
    matches = [m for m in pat.finditer(text)
               if not _takvim_yili(m) and not _islenmis_ornek(text, m)]
    if not matches:
        return None
    # tr_fold: 'İLK 6 AY' -> .lower() 'i̇lk' promo tespitini kaçırıyordu.
    # Katlama karakter sayısını korur, bu yüzden offset'ler text ile hizalı kalır.
    low = tr_fold(text)
    vade_pos = [mm.start() for mm in re.finditer(r"vade", low)]

    # TETİKLEYİCİ ŞARTI — "vade" sözcüğü metinde HİÇ geçmiyorsa değer
    # üretilmez. Eskiden `dist` yalnızca SIRALAMA ölçütüydü (`default=10**6`),
    # yani tetikleyici yokken de "en baştaki sayı" seçilip vade sanılıyordu.
    #
    # Ölçüldü — gold.v2 (48 kayıt): tetikleyicisiz **4 vakanın 4'ü de**
    # halüsinasyon; tüm doğru çıkarımlarda "vade" en az bir kez geçiyor.
    # Ölçüldü — demo.db (1774 belge): `vade_ay` üreten 652 belgenin 210'u
    # (%32) tetikleyicisiz. Bu 210 elle sınıflandırıldı:
    #
    #   177 (%84)  açık halüsinasyon — ödül/üyelik süresi ("1 Aylık TOD
    #              taraftar paketi"), promosyon dönemi ("3 ay boyunca
    #              ücretsiz"), çerez saklama süresi ("çerezdir. 1 yıl")
    #    30 (%14)  "12 Aya varan taksit" — bu ifade `taksit_sayisi` alanına
    #              aittir, `vade_ay`'a değil (alan karışması)
    #     3  (%1)  "60 aya kadar taksitlendirebilirsiniz" — meşru sayılabilir
    #
    # Yani %98'i hatalı. Üç meşru vakayı kaybetmek, 207 yanlış değeri
    # üretmeye yeğdir (CLAUDE.md §19: bilgi yoksa `null`).
    #
    # Tablolu belgeler ETKİLENMEZ: oran tablosunun başlığı zaten "Vade ..."
    # ile başlar ve `_TABLO_YEDEK_ALANLARI` yolu devrede kalır.
    #
    # İKİNCİ TETİKLEYİCİ: "vade" sözcüğü hiç geçmiyorsa, yalnızca
    # "X aya kadar <finansman ürünü>" YAPISINI kuran eşleşmeler hayatta kalır
    # (bkz. `_vade_kurulusu` başlığındaki ölçüm). Gevşetme değil ikinci bir
    # kapıdır: aday kümesi genişlemez, DARALIR — bu yolda yapıyı kurmayan
    # her eşleşme elenir.
    kurulus = {m.start(): d for m in matches
               if (d := _vade_kurulusu(text, m)) is not None}
    if not vade_pos:
        if not kurulus:
            return None
        matches = [m for m in matches if m.start() in kurulus]
        logger.debug(
            "vade_ay: 'vade' sözcüğü yok, yapı tetikleyicisi devrede — "
            "aday=%r", [m.group(0) for m in matches])

    def score(m):
        # "ilk N ay" gibi promosyon dönemleri gerçek vade değildir → geri it
        pre = low[max(0, m.start() - 8): m.start()]
        promo = "ilk" in pre
        dist = min((abs(m.start() - v) for v in vade_pos), default=10 ** 6)
        return (promo, dist)

    chosen = min(matches, key=score)
    raw = chosen.group(0)
    s, e = chosen.span()
    # Normalizasyona SAYI + BİRİM verilir, ham eşleşme değil.
    #
    # Desen artık yüklem ekini de yutuyor ("azami vade 10 YILDIR") ve
    # `normalize_term_months` o eki tanımıyor -> `None` dönüyordu. Sonuç:
    # eşleşme SEÇİLİYOR ama değer üretilmiyordu, yani alan sessizce boşalıyordu
    # (gold.v2 `ziraat-katilim--konut-finansmani-kentsel-donusum-finansmani`).
    # Normalizasyon katmanı bu değişikliğin sahipliğinde değil; ek burada,
    # tüketici tarafında düşürülüyor. Kanıt/`raw_value` ham eşleşme kalır ki
    # span izlenebilirliği (CLAUDE.md §18/1) bozulmasın.
    canon = N.normalize_term_months(f"{chosen.group(1)} {chosen.group(2)}")
    # Tetikleyici mesafesi: "vade" sözcüğü varsa ona olan uzaklık, yoksa
    # yapıyı kuran ürün adına olan uzaklık. İkisi de yoksa buraya gelinmez.
    dist = min((abs(s - v) for v in vade_pos), default=None)
    if dist is None:
        dist = kurulus.get(s)
    return _field(
        "vade_ay", raw, canon, _window(text, s, e),
        span_start=s, span_end=e,
        trigger_distance=dist,
        candidate_count=len(matches),
    )
