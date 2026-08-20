"""Finansman tutarı + taksit sayısı — `extract.py` bölünmesinde AYRI modül.

## Neden bu iki alan BİRLİKTE

`extract_taksit`, `extract_tutar`in hiçbir yardımcısını çağırmıyor
(`_field`/`_window` dışında) — yani teorik olarak kendi başına tek satırlık
bir modül de olabilirdi. 35 satırlık bir dosya açmak yerine burada
tutulmasının gerekçesi mimari değil ölçek: ikisi de "tek bir sayısal/parasal
skaler alan" ailesinden ve `_EXTRACTORS` listesinde ardışık çağrılıyor.
Sınır ileride `extract_taksit` kendi karmaşık süzgeçlerini kazanırsa
(şu an yok) yeniden değerlendirilebilir.

## Paylaşılan bağımlılık

`extract_tutar` `_CUMLE_SINIRI_RE`yi kullanıyor — bu, `_ortak.py`nin
başlığında ayrıntılı belgelenen "iki kez tanımlanmış ad" tuzağının
kaynağı fonksiyondu. Buradan artık TEK, doğru (hep-canlı-olan) tanımı
içe aktarıyor.
"""

from __future__ import annotations

import re
from typing import Optional

from ...normalization import normalize as N
from ...schemas import ExtractedField
from ._ortak import _CUMLE_SINIRI_RE, _field, _window

# Varlık FİYATI finansman TUTARI değildir. Bu ayrım gold setinde de iki kez
# karışmış (bkz. data/gold/review/_hakem-turu-01-finansman-tutari.md), yani
# sözleşmenin zayıf olduğu bir yer — kod tarafında açıkça korunuyor.
_VARLIK_FIYATI_RE = re.compile(
    r"fiyat\w*|değer\w*|deger\w*|bedel\w*|piyasa\s*değer|ekspertiz", re.IGNORECASE)

# Tetikleyici FİNANSMANA BAĞLI olmak zorunda — çıplak "tutar"/"limit" yetmez.
#
# ## Ölçülmüş kusur (2026-08-10, `data/demo.db`, 1774 belge)
#
# Eski tetikleyici listesi `(finansman|kredi|tutar|limit)` idi. Güven kapısını
# (`comparison/compare.py`, eşik 0,65) geçen 237 `finansman_tutari` kaydının
# tetikleyiciye göre dağılımı:
#
#     tutar   117 | limit  15 | kredi  56 | finansman  47
#
# `tutar` ve `limit` tek başına HİÇBİR ŞEY ayırt etmiyor; Türkçede her parasal
# büyüklüğün adı "… tutarı"dır. Kanıt pencereleri:
#
#     "Kampanyadan maksimum kazanım tutarı 500 TL"      -> ödül tavanı
#     "müşteri bazlı toplam indirim tutarı 1.000 TL"    -> indirim tavanı
#     "kazanılabilecek maksimum iade tutarı 1000 TL"    -> iade tavanı
#     "Ödenecek toplam tutar: 133.746,12 TL"            -> toplam geri ödeme
#     "Hesap açılışı için gereken minimum tutar 10.000 TL" -> hesap asgarisi
#     "Mektup tutarı üst limiti 15.000.000 TL"          -> teminat mektubu
#     "maksimum teminat limiti 100.000 TL"              -> teminat
#     "günlük para çekme limiti 25.000 TL"              -> ATM limiti
#
# `kredi` de ayırt etmiyor, çünkü korpusta 56 kaydın 54'ü **kredi KARTI**:
#
#     "İlk Ek Kredi Kartınıza 1.000 TL Bankkart Lira"   -> kart ödülü
#     "TROY kredi kartınız ile 1.000 TL- 100.000 TL"    -> harcama bandı
#
# Kredi kartı bir finansman ürünü değil bir ödeme aracıdır; yanındaki tutar
# harcama eşiği ya da ödüldür. Hepsi 0,95 güvenle üretiliyordu — yani güven
# kapısı bu sınıfı GÖREMEZ, çünkü çıkarıcı kendinden emin. Kapı değil, kanıt
# ölçütü düzelmeli.
#
# ## Kural
#
# Tetikleyici ancak FİNANSMANIN KENDİSİNİ adlandırıyorsa geçerlidir:
# `finansman*`, `kredi*` (ama "kredi kartı" DEĞİL), `kullandırım*`.
# "tutar/limit/miktar" artık bağımsız tetikleyici değil, bu çapaların
# İSTEĞE BAĞLI KUYRUĞUdur: "Finansman Tutarı" tek parça olarak yutulur, böylece
# 20 karakterlik boşluk kuyruktan SONRA başlar. Kuyruk olmasa
# "Finansman Tutarı Kar Oranı Vade 150.000 TL" (Kuveyt Türk oran tablosu) ve
# "Finansman Tutarı Taksit Miktarı 125.000 TL" (Albaraka) kaybolurdu — ikisi de
# DOĞRU kayıt.
_TUTAR_TETIK = (
    r"(?:finansman\w*"
    r"|kredi\w*(?!\s*kart)"
    r"|kulland[ıi]r[ıi]m\w*)"
    r"(?:\s*(?:tutar|limit|miktar)\w*)?"
)

_TUTAR_PAT = re.compile(
    rf"({_TUTAR_TETIK})([^\d]{{0,20}})"
    r"(\d[\d.,]*\s*(?:tl|₺|try|türk\s*liras[ıi]))",
    re.IGNORECASE,
)

# "Örnek ... Tablosu" TEMSİLİ bir hesap örneğidir, kampanyanın tutarı değil.
# Ölçülen halüsinasyon (`turkiye-emlak-katilim--finansmanlar-ihtiyac-finansmani`):
# "Örnek İhtiyaç Finansmanı Tablosu | Finansman Tutarı ... 30.000,00 ₺" —
# gold doğru olarak `absent` diyor. `örnek` VE `tablo` birlikte aranıyor; tek
# başına "örneğin" gibi kullanımlar belgeyi elemesin.
#
# 19 Ağu 2026'da genişletildi: "Maliyet Tablosu" ve "Ödeme Tablosu" da aynı
# sınıf. Ölçülen örnek (`turkiye-finans--kampanyalar-turkiye-finans-
# avantajlariyla-`): "İhtiyaç Finansmanı Maliyet Tablosu 50.000 TL'ye Kadar
# Sigortalı İhtiyaç Finansmanı" — 50.000 tablonun örnek satırıdır, gold o
# belgede 400.000 TL diyor. "örnek" sözcüğü bu başlıklarda geçmediği için
# eski kalıp tabloyu görmüyordu.
# `örnek` için araya söz girmesine izin verilir ("Örnek İhtiyaç Finansmanı
# Tablosu"); diğer başlıklarda BİTİŞİK aranır, çünkü "ödeme" tek başına çok
# geniş bir çapa ("ödemelerinizi … tablo" gibi alakasız eşleşmeleri içeri
# alırdı).
_ORNEK_TABLO_RE = re.compile(
    r"örnek\w*(?:[^.]{0,80}?)tablo"
    r"|(?:maliyet|geri\s*ödeme|ödeme)\s*tablo",
    re.IGNORECASE,
)

# Belge birden fazla üst sınır veriyorsa TOPLAM sınır kanoniktir.
# Ölçüm (`vakif-katilim--finansmanlar-kentsel-donusum`): "her bir bağımsız bölüm
# için 1.250.000 TL'yi aşmamak koşulu ile toplamda azami 3.000.000 TL" —
# istenen birim başına sınır (1.250.000) değil toplam sınır (3.000.000).
#
# Bu neden AYRI bir kalıp: o cümlede tetikleyici sözcük ("tutarı") sayıdan 20
# karakterden uzakta kaldığı için `_TUTAR_PAT` 3.000.000'u aday olarak HİÇ
# görmüyordu. Tetikleyici mesafesini genel olarak büyütmek alakasız tutarları
# içeri alırdı; "toplamda azami <tutar>" ise kendi başına yeterince özgül.
_TOPLAM_AZAMI_PAT = re.compile(
    r"toplam\w*\s+azami\s+(\d[\d.,]*\s*(?:tl|₺|try|türk\s*liras[ıi]))",
    re.IGNORECASE,
)

# Aralığın ÜST sınırı: ilk tutarın HEMEN ardından gelen ikinci tutar.
# Sadece kısa bir ayıraç kabul edilir ("- ", "– ", "ila ", ya da boşluk) —
# uzun mesafeye izin vermek belgedeki alakasız tutarları içeri alır.
_ARALIK_UST_RE = re.compile(
    r"[\s]{0,3}(?:[-–—]|ila|ile|arası|arasında|ve)?[\s]{0,3}"
    r"(\d[\d.,]*\s*(?:tl|₺|try|türk\s*liras[ıi]))",
    re.IGNORECASE,
)

# VADE KADEMESİ tutarı kampanyanın üst sınırı DEĞİLDİR.
#
# Türk banka metinlerinde çok yaygın bir kalıp, ölçülmüş örnek
# (`turkiye-finans` banka çalışanı ihtiyaç finansmanı, 19 Ağu 2026):
#
#     "Finansman tutarının 125.000 TL'ye kadar olması durumunda maksimum
#      vade 36 aydır. Finansman tutarının 125.000 TL – 250.000 TL arasında
#      olması durumunda maksimum vade 24 ayı aşamaz."
#
# Buradaki 125.000 bir VADE EŞİĞİdir: "şu tutara kadarsa şu kadar ay".
# Tetikleyici ("Finansman tutarı") tam da aradığımız çapa olduğu için
# `_TUTAR_PAT` bunu birinci aday yapıyor ve `break` ile döngü kapanıyordu;
# aynı belgedeki GERÇEK üst sınır (1.000.000 TL) hiç değerlendirilmiyordu.
# Ölçülen sonuç: 125.000 üretiliyordu, doğrusu 1.000.000.
#
# Ayırt edici işaret tutarın KENDİSİ değil, ardından gelen koşul-sonuç
# kurgusudur: "… olması durumunda … vade/N ay" ya da "vade … aşamaz".
#
# AYNI HATA KENDİ GOLD SETİMİZDE DE ÖLÇÜLDÜ
# (`turkiye-finans--kampanyalar-turkiye-finans-avantajlariyla-`): gold
# 400.000 TL derken çıkarım 125.000 TL üretiyordu, kanıt span'i tam bu
# kademe cümlesiydi. Yani kalıp rakip korpusuna özgü değil, korpus
# bağımsız bir çıkarım hatası — düzeltmesi iki zeminde birden kazanç.
#
# `vade` sözcüğü kalıpta ZORUNLU DEĞİL: o belge "olması durumunda maksimum
# 36 ay" diyor, "vade" hiç geçmiyor. Sonuç ölçütü ay cinsinden bir süre
# olduğu için `\d+\s*ay` de kademe işareti sayılır.
_VADE_KADEMESI_RE = re.compile(
    r"olmas[ıi]\s+durumunda[^.]{0,60}?(?:vade|\d+\s*ay)"
    r"|vade[^.]{0,40}?a[şs]amaz"
    r"|maksimum\s+vade",
    re.IGNORECASE,
)
_VADE_KADEMESI_PENCERE = 80

# Tutar ÖNCE, çapa SONRA gelen aralık kurgusu.
#
# `_TUTAR_PAT` tetikleyici→tutar sırası bekler; şu cümlede sıra terstir ve
# tutar hiç aday olamıyordu (ölçülen örnek, aynı belge):
#
#     "Kampanya kapsamında 1.000 TL-1.000.000 TL arasında ihtiyaçlarınız
#      için … İhtiyaç Finansmanı başvurusu yapabilirsiniz."
#
# İstenen üst sınır 1.000.000. Çapa ("finansman") aralıktan sonra geliyor.
#
# NEDEN ÇAPA ZORUNLU: aynı kurgu HARCAMA bantlarında da geçiyor ve orada
# tutar finansman tutarı DEĞİLDİR — "1.000 TL- 100.000 TL tutarları arasında
# … harcamanızı yapın" (albaraka sağlık) ve "30.000 TL- 500.000 TL arası
# eğitim harcamalarınız" (albaraka eğitim). İkisinde de `finansman` sözcüğü
# aralığın ardındaki pencerede yok, dolayısıyla bu kalıp onları görmez.
# Ayrımı çapa taşıyor; kalıbı çapasız yazmak harcama bantlarını içeri alırdı.
_ARALIK_FINANSMAN_PAT = re.compile(
    r"(\d[\d.,]*\s*(?:tl|₺|try|türk\s*liras[ıi]))"
    r"\s*[-–—]\s*"
    r"(\d[\d.,]*\s*(?:tl|₺|try|türk\s*liras[ıi]))"
    r"\s*aras[ıi](?:nda)?[^.]{0,120}?finansman",
    re.IGNORECASE,
)

# Aynı ters sıra, aralık yerine TEK üst sınır: "<tutar> TL'ye kadar
# <…> finansman". Ölçülen örnek (kendi gold setimiz, aynı belge):
# "400.000 TL'ye Kadar İhtiyaç Finansmanı Kullanın, 3 Ay Öteleme Fırsatı" —
# gold 400.000, çıkarım ise belgenin başka yerlerinden 125.000 ya da
# 50.000 üretiyordu.
#
# Çapa yine ZORUNLU ve yine aynı gerekçeyle: "50.000 TL'ye kadar vade
# farksız 5 taksit" (kuveyt-turk) bir taksitli harcama limitidir, finansman
# tutarı değil — orada çapa yok, bu kalıp onu görmez. Ayrıca tablo
# koruyucusu bu kalıba da uygulanır, yoksa maliyet tablosunun örnek satırı
# ("… Maliyet Tablosu 50.000 TL'ye Kadar … Finansmanı") içeri girerdi.
_UST_SINIR_FINANSMAN_PAT = re.compile(
    r"(\d[\d.,]*\s*(?:tl|₺|try|türk\s*liras[ıi]))"
    r"['’]?\s*(?:ye|ya|e|a)?\s*kadar\s+"
    r"[^.]{0,40}?finansman",
    re.IGNORECASE,
)


def extract_tutar(text: str) -> Optional[ExtractedField]:
    """Finansman tutarı: 'finansman ... 500.000 TL'.

    Üç ölçülmüş kusur bu fonksiyonda düzeltildi (`eval/reports/20260804-202009`
    teşhisi, F1 0.000):

    1. **Cümle sınırı.** Eski `[^\\d]{0,20}` boşluğu nokta içerebiliyordu, yani
       eşleşme cümle atlıyordu ve alakasız bir sayıyı tutar sanıyordu.
    2. **Varlık fiyatı.** "Fiyatı 20.000 TL olan cep telefonu" bir finansman
       tutarı değil; kredi/değer tablosundaki konut değeri de değil.
    3. **Aralığın ALT sınırını seçmek.** `search()` ilk adayı alıyordu; iki
       değerli bir aralıkta bu alt sınır demek. Biçim kartı §3.4 **üst sınırı**
       kanonik sayıyor (`tom-katilim` hesaplama aracında 5.000 değil 150.000).

    ÖLÇÜLMÜŞ YANLIŞ DENEME — tekrarlanmasın: bir tur "adayların EN BÜYÜĞÜNÜ seç"
    denendi ve `tom-katilim`'i **daha da bozdu** (5.000 -> 11.891,83, çünkü
    belgedeki en büyük tutar hesaplama aracının "Geri Ödenecek Tutar" satırıydı).
    §3.4 *bir aralığın* üst sınırını istiyor, **belgedeki en büyük sayıyı**
    değil; ikisi aynı şey değil. Bu yüzden ilk geçerli aday esas alınır ve
    yalnızca o adayın hemen ardından gelen ikinci bir tutar varsa (gerçek aralık
    kurgusu) üst sınıra yükseltilir.
    """
    ilk: Optional[tuple] = None
    toplam: Optional[tuple] = None

    for m in _TUTAR_PAT.finditer(text):
        gap = m.group(2)
        if _CUMLE_SINIRI_RE.search(gap) or _VARLIK_FIYATI_RE.search(gap):
            continue
        # Pencere tutarın BAŞINA kadar uzar: tablo başlığı tetikleyici ile
        # tutar ARASINDA da durabiliyor ("İhtiyaç Finansmanı Maliyet Tablosu
        # 50.000 TL"), o durumda eşleşmenin yalnızca önüne bakmak yetmiyordu.
        if _ORNEK_TABLO_RE.search(text[max(0, m.start() - 150): m.start(3)]):
            continue
        # Vade kademesi eşiği mi? ("… olması durumunda maksimum vade …")
        if _VADE_KADEMESI_RE.search(
                text[m.end(3): m.end(3) + _VADE_KADEMESI_PENCERE]):
            continue
        canon = N.normalize_money(m.group(3))
        if canon is None:
            continue

        s, e = m.span(3)
        aday = (m.group(3), canon, s, e, s - m.end(1))

        if ilk is None:
            ilk = aday
            break

    tm = _TOPLAM_AZAMI_PAT.search(text)
    if tm is not None:
        canon = N.normalize_money(tm.group(1))
        if canon is not None:
            s, e = tm.span(1)
            toplam = (tm.group(1), canon, s, e, 0)

    # Çapası SONRA gelen kurgular. Tablo koruyucusu burada da geçerli:
    # temsili bir maliyet/ödeme tablosunun satırı kampanyanın sınırı değildir.
    def _ters_sira_aday(pat: "re.Pattern", grup: int) -> Optional[tuple]:
        for mm in pat.finditer(text):
            if _ORNEK_TABLO_RE.search(text[max(0, mm.start() - 150): mm.start()]):
                continue
            c = N.normalize_money(mm.group(grup))
            if c is None:
                continue
            gs, ge = mm.span(grup)
            return (mm.group(grup), c, gs, ge, 0)
        return None

    aralik = _ters_sira_aday(_ARALIK_FINANSMAN_PAT, 2)
    ust_sinir = _ters_sira_aday(_UST_SINIR_FINANSMAN_PAT, 1)

    # Öncelik özgüllük sırasına göre: "toplamda azami <tutar>" en dar kalıp,
    # ardından açık aralık kurgusu ("X – Y arası … finansman"), sonra tek üst
    # sınır ("X'e kadar … finansman"), en sonda ilk çapa-tutar eşleşmesi.
    secilen = toplam or aralik or ust_sinir or ilk
    if secilen is None:
        return None

    raw, canon, s, e, trigger_distance = secilen

    # Aralık kurgusu: HEMEN ardından ikinci bir tutar geliyor mu?
    # "5.000 TL 150.000 TL" (kaydırıcı) veya "1.000 TL - 100.000 TL".
    ileri = _ARALIK_UST_RE.match(text, e)
    if ileri is not None:
        ust = N.normalize_money(ileri.group(1))
        if (isinstance(ust, dict) and isinstance(canon, dict)
                and (ust.get("value") or 0) > (canon.get("value") or 0)):
            raw, canon = ileri.group(1), ust
            s, e = ileri.span(1)

    return _field(
        "finansman_tutari", raw, canon, _window(text, s, e),
        span_start=s, span_end=e,
        trigger_distance=trigger_distance,
        candidate_count=len(_TUTAR_PAT.findall(text)),
    )


def extract_taksit(text: str) -> Optional[ExtractedField]:
    """Taksit sayısı: '12 taksit', 'taksit sayısı 36'.

    İLK eşleşme değil, ilk GEÇERLİ eşleşme alınır. Gerekçe ölçümle geldi
    (`turkiye-finans--bireysel-urun-hizmet-ucretleri`,
    `scripts/lint_review_csv` round1 hatası): sayfada
        "02.01.2026 00:00:00 Taksitli Ticari Taşıt Finansmanı"
    geçiyor ve desen ZAMAN DAMGASININ son iki hanesini yakalayıp
    **`taksit_sayisi = 0`** üretiyordu — hem şema dışı (sayı pozitif olmalı)
    hem uydurma. Belgenin gerçek taksit bahsi çok daha sonra geliyordu ama
    `search` ilk eşleşmede duruyordu.

    İki koruma: sayının solunda `:` ya da rakam olamaz (zaman/ondalık
    parçası değil) ve **0 taksit yoktur**.
    """
    pat = re.compile(
        r"(?<![:.,\d])(\d{1,3})\s*taksit"
        r"|taksit\s*(?:say[ıi]s[ıi])?\s*[:\-]?\s*(?<![:.,\d])(\d{1,3})",
        re.IGNORECASE)
    for m in pat.finditer(text):
        num = m.group(1) or m.group(2)
        try:
            canon = int(num)
        except (TypeError, ValueError):
            continue
        if canon < 1:
            continue        # "0 taksit" diye bir şey yok — sayı başka bir şeyin parçası
        s, e = m.span()
        return _field(
            "taksit_sayisi", m.group(0), canon, _window(text, s, e),
            span_start=s, span_end=e,
            # "taksit" sözcüğü eşleşmenin kendi içinde → bitişik kabul edilir
            trigger_distance=0,
            candidate_count=len(pat.findall(text)),
        )
    return None
