"""Oran tablosu ayrıştırma — kâr payı/vade/tutar/masraf İÇİN ÇAPRAZ ALAN.

## Neden bu sınır burada

Bu modül tek bir ALANA değil, bir ÇIKARIM YÖNTEMİNE (banka sitelerindeki
tablo biçimli oran listelerini ayrıştırmaya) karşılık gelir ve dört farklı
alana (`kar_payi_orani`, `vade_ay`, `finansman_tutari`, `masraf_durumu`)
birden `ExtractedField` üretir (`extract_from_rate_table`). Bu yüzden
`kar_payi.py`/`vade.py`/`tutar.py`/`masraf.py`nin hiçbirine YERLEŞTİRİLEMEZ
— herhangi birine konması diğer üçünü ondan import etmeye zorlardı ve
sahte bir "bu alan diğerlerine bağımlı" izlenimi yaratırdı. `extract.py`
(cephe) bu dört alanı `_TABLO_YEDEK_ALANLARI` önceliğiyle birleştirir;
birleştirme kararı orada kalır, ayrıştırma burada.

`RateRow`, `parse_rate_table`, `_ORAN_TABLOSU_BASLIK_RE` bilerek public
bırakıldı: `tests/test_oran_tablosu_kanit.py`,
`tests/test_tahsis_ucreti_semasi.py`, `tests/test_vade_tetikleyici.py` ve
`tests/test_skaler_alan_iyilestirmeleri.py` bunları doğrudan içe aktarıyor.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

from ...normalization import normalize as N
from ...schemas import ExtractedField
from . import confidence as C
from ._ortak import _field, _window


@dataclass
class RateRow:
    """Oran tablosunun tek satırı: bir vade ve o vadeye ait oranlar."""

    vade_ay: int
    kar_payi: float
    tahsis_ucreti: Optional[float] = None
    tutar: Optional[float] = None


# Oran tablosunun BAŞLIĞI — TEK DOĞRULUK KAYNAĞI.
#
# Bankalar farklı etiket kullanıyor; gerçek veride görülenler:
#   "Vade  Kâr Payı Oranı  Tahsis Ücreti ..."        (Türkiye Finans)
#   "Finansman Tutarı  Vade  Kar Oranı  Taksit ..."  (Emlak Katılım)
# Bu yüzden "payı" ZORUNLU DEĞİL ve kolon sırası esnek.
#
# Bu desen bir zamanlar İKİ KOPYAydı ve kopyalar AYRIŞMIŞTI: `parse_rate_table`
# gevşek olanı ("payı" opsiyonel, "paylaşım" da kabul), `extract_from_rate_table`
# katı olanı ("payı" zorunlu) kullanıyordu. Sonuç sessizdi ve ölçüldü
# (2026-08-08, `data/demo.db`): tablo AYRIŞIYOR ve değer üretiliyor, ama ikinci
# arama tutmadığı için konum `(0, 0)`a düşüyor — `raw_value` boş, `span` yok,
# güven yine 0,95. 70 `kar_payi_orani` kaydının **26'sı (%37)** böyleydi.
#
# Yani projenin en özgün iddiası — "her değer bir karakter aralığına bağlıdır" —
# bu alanın üçte birinde tutmuyordu; üstelik değer YANLIŞ değil, yalnız
# KANITSIZdı, bu yüzden hiçbir doğruluk metriği bunu göstermiyordu.
_ORAN_TABLOSU_BASLIK_RE = re.compile(
    r"vade[^%\d]{0,40}?(kâr|kar)\s*(pay[ıi]\s*|payla[şs][ıi]m\s*)?oran[ıi]",
    re.IGNORECASE)

# TAHSİS KOLONU — başlıkta ADI GEÇİYORSA vardır, yoksa YOKTUR.
#
# Eskiden tahsis ücreti "kâr payından sonraki ilk makul yüzde" diye
# tahmin ediliyordu ve tablo o kolona sahip değilse KOMŞU KOLONU okuyordu.
# `data/demo.db`de ölçüldü (2026-08-09): oran tablosundan üretilen 19
# `tahsis_ucreti` değerinin **4'ü** tabloda hiç bulunmayan bir kolondan
# geliyordu —
#   %3,80 ve %8,07 aslında "Aylık/Yıllık Maliyet Oranı" (Kuveyt Türk),
#   %0,00 ise yalnızca "Vade / Kredi Tutarı / Kâr Oranı" kolonları olan bir
#   tablodan (Albaraka TOGG) devşirilmişti.
# Yani değer metinde YOKTU; bu bir halüsinasyondur (CLAUDE.md §19) ve
# üstelik "%0,00 tahsis" en zararlı biçimidir: kampanyayı ücretsiz gösterir.
_TAHSIS_KOLON_RE = re.compile(
    r"tahsis\s*(ücret|ucret|bedel)|dosya\s*(masraf|ücret|ucret)",
    re.IGNORECASE)


# TUTAR KOLONU — `_TAHSIS_KOLON_RE` ile AYNI disiplin: başlıkta adı geçiyorsa
# vardır, yoksa yoktur. Çıplak "tutar" YETMEZ; tetikleyici finansmanın kendisini
# adlandırmalı (aynı gerekçe `_TUTAR_TETIK` başlığında ölçümle yazılı: Türkçede
# her parasal büyüklüğün adı "… tutarı"dır).
#
# Ölçülen kayıp (gold.v2 `albaraka--tasit-finansmani-togg-finansmani`):
#     "Araç Modeli Vade (Ay) Kredi Tutarı Aylık Kar Oranı
#      T10F V2 12 800.000 0,00%   T10F V2 48 1.700.000 2,99%   …"
# `_TUTAR_PAT` bunu göremez, çünkü tetikleyici ("Kredi Tutarı") tablo
# BAŞLIĞINDA ve tutardan onlarca karakter uzakta — `extract_kar_payi`'nin aynı
# tablolarda yaşadığı sorunun eşi. Gold değeri 1.700.000 ve gold notu
# sözleşmeyi yazıyor: *"En yüksek finansman tutarı alındı."* (vade tarafındaki
# "en uzun vade" kuralının kardeşi).
#
# ÖLÇÜLDÜ (1.782 belge, 2026-08-20): başlıkta tutar kolonu OLAN ve satır kuran
# belge sayısı **1** — tam bu belge; başka hiçbir belgenin değeri değişmiyor.
# Alan ayrıca YEDEKtir (`_TABLO_YEDEK_ALANLARI`), yani `extract_tutar` bir
# değer üretebiliyorsa tabloya hiç bakılmaz. Sıfır etki burada başarısızlık
# değil güvenlik kanıtıdır (aynı gerekçe `_KURULUS_PENCERE` bloğunda).
_TUTAR_KOLON_RE = re.compile(
    r"(?:kredi|finansman|kulland[ıi]r[ıi]m)\s*tutar", re.IGNORECASE)

#: Tablo hücresindeki tutar BİNLİK AYIRAÇLI yazılır ("1.700.000"). Ayıraç şartı
#: bilinçli: çıplak "48" gibi vade/adet hücrelerini tutar sanmayı imkânsız kılar.
_TABLO_TUTAR_RE = re.compile(
    r"(?<![\d.,])(\d{1,3}(?:\.\d{3})+(?:,\d+)?)(?![\d.,])")


# BİÇİM C — YÜZDE İŞARETİ OLMAYAN oran tablosu.
#
# Ölçülen kayıp (gold.v2 `kuveyt-turk--kampanya-arsivi-kuveyt-turkten-
# avantajli-leasing-finansmani`): tablo başlığı tanınıyor ama satır kurulmuyor,
# çünkü hücrelerde `%` yok —
#
#     "Vade TL Kar Oranı USD Kar Oranı EUR Kar Oranı
#      12 Ay 4.15 0.83 0.79   24 Ay 3.90 0.83 0.79   36 Ay 3.81 0.84 0.79
#      48 Ay 3.81 0.90 0.79   60 Ay 3.81 0.90 0.79"
#
# Bu belgede İKİ alan birden düşüyordu: `kar_payi_orani` hiç üretilmiyordu
# (gold {min 3,81 · max 4,15}) ve `vade_ay` tablonun İLK satırından 12 alıyordu
# (gold 60 — `extract_from_rate_table` zaten `max` alıyor, ama satır yoktu).
#
# ## Neden çıplak ondalık okumak GÜVENLİ — üç kapı da ölçümle kondu
#
# 1.782 belge tarandı (2026-08-20). Başlığı tanınıp mevcut biçimlerle satır
# kurulAMAYAN ve kuyruğunda hiç `%` bulunmayan belgeler: **5**.
#
#     kampanya-arsivi-esnaf-ve-kobilere-ozel-avantajli-arac-kredisi
#         "Vade Kar Oranı 24 ay 3.54 36 ay 3.29 48 ay 3.23 60 ay 3.23"   GERÇEK
#     kampanya-arsivi-esnafa-ozel-avantajli-arac-finansmani
#         "12 Ay 3.42 18 Ay 3.50 24 Ay 3.25 36 Ay 3.09 …"                GERÇEK
#     kampanya-arsivi-kuveyt-turkten-avantajli-leasing-finansmani         GERÇEK
#     tr.txt   "Vade Kâr Oranı % Oranı kendim gireceğim…" -> (1, 1.93),
#              (12, 1.93)                                                 ÇÖP
#              (hesaplama aracı widget'ı, tablo değil)
#     detay-3-ay-ertelemeli-tasit-finansmani -> (36, 1.20), (24, 1.20)     ÇÖP
#              (düz metin: "48 ay vadeye kadar … tüm vadelerde uygun kâr
#               oranıyla"; oran hücresi yok)
#
# İki çöpü eleyen yapısal iki özellik ÖLÇÜLDÜ: gerçek tabloların üçünde de
# satır sayısı >= 3 VE vade kolonu ARTAN sırada (12 < 24 < 36 …); iki çöpün
# biri 2 satır, öteki azalan. Kapı bu yüzden bu ikisini arar ve sonuç **3:0**
# olur. Ek olarak `%` bulunan kuyruklara HİÇ dokunulmaz — biçim A/B'nin
# alanına girmez, yalnız onların hiç satır kurmadığı yerde devreye girer.
#
# `(?![\d.,]*\s*%)` kuyruğu: bir yüzde ifadesinin gövdesini çıplak ondalık
# sanmayı imkânsız kılar (aynı sınır disiplini `vade_re` yorumunda yazılı).
_TABLO_C_VADE_RE = re.compile(r"(?<![\d.,])(\d{1,3})\s*ay\b", re.IGNORECASE)
_TABLO_C_ORAN_RE = re.compile(r"(?<![\d.,%])(\d{1,2}[.,]\d{1,2})(?![\d.,]*\s*%)")
_TABLO_C_ASGARI_SATIR = 3
_TABLO_C_ORAN_PENCERE = 25


def _oran_tablosu_c(kuyruk: str) -> list["RateRow"]:
    """Yüzde işaretsiz oran tablosu (BİÇİM C). Yapı tutmazsa boş liste."""
    satirlar: list[RateRow] = []
    for vm in _TABLO_C_VADE_RE.finditer(kuyruk):
        vade = int(vm.group(1))
        if not (1 <= vade <= 480):
            continue
        om = _TABLO_C_ORAN_RE.search(
            kuyruk, vm.end(), min(len(kuyruk), vm.end() + _TABLO_C_ORAN_PENCERE))
        if om is None:
            continue
        kar = N.parse_tr_number(om.group(1))
        if kar is None or not (0 < kar <= 15):
            continue
        satirlar.append(RateRow(vade_ay=vade, kar_payi=kar))
    if len(satirlar) < _TABLO_C_ASGARI_SATIR:
        return []
    vadeler = [r.vade_ay for r in satirlar]
    if vadeler != sorted(set(vadeler)):        # artan ve tekil olmalı
        return []
    return satirlar


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
    baslik = _ORAN_TABLOSU_BASLIK_RE.search(text)
    if not baslik:
        return []

    # Tahsis kolonu başlıkta adlandırılmadıysa `RateRow.tahsis_ucreti` HİÇ
    # doldurulmaz (gerekçe: `_TAHSIS_KOLON_RE`).
    tahsis_kolonu = bool(
        _TAHSIS_KOLON_RE.search(text[baslik.start(): baslik.end() + 120]))
    tutar_kolonu = bool(
        _TUTAR_KOLON_RE.search(text[baslik.start(): baslik.end() + 120]))

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
    # (?<![\d.,]) ZORUNLU — ölçülmüş hata (2026-08-12, gold.v2 albaraka TOGG):
    # `\b(\d{1,3})` deseni bir YÜZDENİN ONDALIK KISMINI vade sanıyordu.
    # "T10F V2 48 1.700.000 2,99%" satırında "," ile "9" arasında kelime
    # sınırı bulunduğu için "99" yakalanıyor, `(?![\d.,])` de "%" önünde
    # sağlanıyordu. Sonuç: satır listesi [(48,2.99), (48,2.99), (99,2.99),
    # (4,2.99)] ve `max(...)` = **99 ay**. Gold değeri 48.
    #
    # Aynı sınır koruması 2026-08-11'de `_ORAN_IFADESI` ve `_PARA_IFADESI`'ne
    # uygulanmıştı ("5000 TL" -> "000 TL" kesilmesi); bu desen o taramadan
    # atlanmıştı.
    vade_re = re.compile(r"(?<![\d.,])(\d{1,3})(?![\d.,])\s*(?:ay\b)?",
                         re.IGNORECASE)
    yuzde_re = re.compile(yuzde)

    yuzdeler = [(m.start(), m.end(), m.group(0))
                for m in yuzde_re.finditer(kuyruk)]
    if not yuzdeler:
        # Kuyrukta hiç `%` yok -> biçim A/B kurulamaz. Yüzde İŞARETSİZ tablo
        # olabilir; gerekçe ve ölçüm `_oran_tablosu_c` başlığında.
        return _oran_tablosu_c(kuyruk)

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
            tahsis_ucreti=(oranlar[1] if tahsis_kolonu and 0 <= oranlar[1] <= 10
                           else None)))
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
        # Tahsis ücreti: bir sonraki yüzde — YALNIZ tablonun böyle bir kolonu
        # varsa (gerekçe: `_TAHSIS_KOLON_RE`).
        tahsis = None
        ardindan = ([y for y in yuzdeler if y[0] >= e0 and y[0] - e0 <= 30]
                    if tahsis_kolonu else [])
        if ardindan:
            t = N.parse_tr_number(ardindan[0][2])
            if t is not None and 0 <= t <= 10:
                tahsis = t
        # Tutar kolonu: vade hücresi ile kâr payı yüzdesi ARASINDA duran
        # binlik ayıraçlı sayı (gerekçe: `_TUTAR_KOLON_RE`).
        tutar = None
        if tutar_kolonu:
            tm = _TABLO_TUTAR_RE.search(kuyruk, vm.end(), s0)
            if tm is not None:
                aday = N.parse_tr_number(tm.group(1))
                alt, ust = C.PLAUSIBLE_RANGES["finansman_tutari"]
                if aday is not None and alt <= aday <= ust:
                    tutar = aday
        rows.append(RateRow(vade_ay=vade, kar_payi=kar, tahsis_ucreti=tahsis,
                            tutar=tutar))
    return rows


def extract_from_rate_table(text: str) -> list[ExtractedField]:
    """Oran tablosundan `kar_payi_orani`, `vade_ay` ve `masraf_durumu` üretir.

    Tablo birden çok vade içerir, şema ise alan başına tek değer ister.
    Karar: kâr payı **aralık** olarak verilir (dürüst — vadeye göre değişir),
    vade **en uzun** vade.
    §5.7 "En Düşük Kâr Payı" karşılaştırması aralığın alt sınırını kullanır.

    ## Tablodaki tahsis ücreti neden `tahsis_ucreti` alanına YAZILMAZ

    Türkiye Finans tablolarında kolon gerçekten var ve değeri bir ORANdır
    ("Tahsis Ücreti … %0,50"). `tahsis_ucreti` ise PARA tiplidir
    (`scripts/gold_schema.py::MONEY_FIELDS`, ANNOTATION_GUIDE §5). Buraya
    `{"rate": 0.5}` yazmak üç şeyi aynı anda bozuyordu:

    1. **Şema ihlali.** `lint_review_csv` round1 dosyalarında 10 hatanın
       9'unu bu üretiyordu; `preannotate` değeri "model üretmedi" sayıp
       eliyor, anotatöre boş satır gidiyordu.
    2. **Kıyas yok zaten.** `compare._scalar` oran biçimli ücrete `None`
       döndürür ("oran biçimli ücret — TL ile kıyaslanamaz"), yani değer
       hiçbir sıralamaya girmiyordu. Adil kıyas kuralı gereği de giremez:
       %0,50 ile 500 TL aynı sütunda sıralanamaz.
    3. **Ölçülen zarar.** Gold'da `{"rate": X}` denemesi `tahsis_ucreti`
       F1'ini 0.400 -> 0.333'e düşürmüştü (`extract_tahsis_ucreti`
       docstring'i). gold.v2'deki iki oran-tablolu belgede de altın değer
       `null`; üretilen her oran YANLIŞ POZİTİFti.

    Bilgi yine de kaybolmuyor: kılavuzun oransal ücret kuralı (§5) bu durumu
    `masraf_durumu = {"has_fee": true, "amount": null}` diye kaydeder —
    "ücret VAR, TL tutarı metinde YOK". `compare._scalar` bunu skorlamaz ama
    **görünür bir gerekçeyle** ("ücret var, tutarı belirtilmemiş"), yani
    kampanya sessizce masrafsız görünmez. Oran %0,00 ise ücret gerçekten
    yoktur ve `{"has_fee": false, "amount": 0}` yazılır.

    Bu `masraf_durumu` YEDEKTİR: `extract_masraf` bir değer üretebiliyorsa
    (çoğu belgede TL tutarını da biliyor) onunkisi kazanır — bkz.
    `extract_all` / `_TABLO_YEDEK_ALANLARI`.
    """
    rows = parse_rate_table(text)
    if not rows:
        return []

    # Konum, tabloyu AYRIŞTIRAN desenin kendisinden gelir. Ayrı bir arama
    # yapmak (eskiden öyleydi) iki deseni ayrıştırır ve kanıt bağını sessizce
    # koparır — gerekçe `_ORAN_TABLOSU_BASLIK_RE` başlığında.
    m = _ORAN_TABLOSU_BASLIK_RE.search(text)
    if m is None:                      # `parse_rate_table` satır döndürdüyse
        return []                      # başlık VARDIR; buraya düşmek çelişkidir
    s, e = m.span()
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
    tutarlar = [r.tutar for r in rows if r.tutar is not None]
    if tutarlar:
        # "En yüksek finansman tutarı" — gold sözleşmesi (`_TUTAR_KOLON_RE`).
        out.append(_field("finansman_tutari", text[s:e],
                          {"value": max(tutarlar), "currency": "TRY"},
                          pencere, span_start=s, span_end=e,
                          trigger_distance=0))
    ucretler = {r.tahsis_ucreti for r in rows if r.tahsis_ucreti is not None}
    if len(ucretler) == 1:
        # Tahsis ücreti tabloda ORAN olarak veriliyor (%0,50), tutar değil —
        # bu yüzden para tipli `tahsis_ucreti` yerine `masraf_durumu`.
        oran = ucretler.pop()
        durum = ({"has_fee": False, "amount": 0.0} if oran == 0
                 else {"has_fee": True, "amount": None})
        out.append(_field("masraf_durumu", text[s:e], durum, pencere,
                          span_start=s, span_end=e, trigger_distance=0))
    return out
