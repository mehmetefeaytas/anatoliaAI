"""Kâr payı oranı çıkarımı — `extract.py` bölünmesinde AYRI modül.

İlgili: ../../decisions/ner-fine-tune-yerine-kural-few-shot.md, ../../concepts/bilgi-cikarimi.md

## Neden bu sınır burada

`kar_payi_orani` şartnamenin en ağırlıklı alanı (Model Başarısı %30 içinde
tek başına en çok test/gerekçe biriktiren alan) ve BAŞKA HİÇBİR alan
modülünün kullanmadığı beş özel süzgeci var: paylaşım oranı ayrımı, yabancı
kavram takibi, ceza bağlamı, türev oran ve bozuk hesaplama aracı tespiti.
Bunların hiçbiri `vade`/`tutar`/`masraf` tarafından çağrılmıyor (doğrulandı:
`grep -n` ile her yardımcının tek kullanım noktası bu dosyanın içinde);
yani modül sınırı GERÇEK bir çağrı-grafiği kopukluğuna oturuyor, keyfi bir
satır kesimi değil.

`paylasim_cifti_araliklari` bilerek adı alt-çizgisiz (public) bırakıldı:
docstring'i "hem belge düzeyi kapı hem değer düzeyi kapı bu listeyi
kullanır" diyor ve `tests/test_paylasim_orani_ayrimi.py` onu doğrudan içe
aktarıyor — cephe (`extract.py`) bunu yeniden ihraç etmek zorunda.
"""

from __future__ import annotations

import re
from typing import Optional

from ...normalization import normalize as N
from ...schemas import ExtractedField
from . import confidence as C
from ._ortak import _field, _window, logger

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

# Paylaşım oranının DİZGİYE dayanmayan işareti: TOPLAMI 100 EDEN İKİ YÜZDE.
#
# ## Neden dizgi araması yetmiyor — ölçüldü
#
# `_PAYLASIM_ORANI_RE` yalnız "kâr payı paylaşım oranı" TAMLAMASINI arar ve
# gold kalibrasyonunda bu ölçütün iki kusuru ölçüldü
# (`data/gold/review/_uyusmazlik-kaliplari.md` §2b):
#
#   * 3 isabetin 2'si SAYFA GEZİNME MENÜSÜnden geliyordu ("…Katılma Hesapları
#     Kâr Payı Oranları Kâr Paylaşım Oranları Kıymetli Maden…"). Tamlamayı tek
#     başına kural yapmak iki DOĞRU satırı haksızca `absent`e çevirirdi.
#   * En güçlü vakayı KAÇIRIYORDU: belge tamlamayı hiç kullanmadan
#     *"Hesabın kâr payı oranı %40'a %60'dır"* diyor (Kuveyt Türk, Altına Altın
#     Katılma Hesabı). Bu %40 karşılaştırma ekranında "en yüksek kâr payı"
#     sırasının tepesine çıkıyordu.
#
# Kalibrasyonda ölçülen daha iyi ölçüt şuydu: **toplamı 100 eden iki yüzde +
# paylaşım fiili**. Gerekçe kavramsal: bir bölüşüm oranı tanımı gereği 100'e
# tamamlanır, gerçek oran çiftleri ise asla tamamlanmaz (2,95 + 4,42 = 7,37).
#
# ## Bu korpustaki ölçüm (2026-08-10, `data/demo.db`, 1774 belge)
#
# Desen 9 belgede 25 kez eşleşiyor: 40/60, 55/45, 95/5, 98/2, 60/40, 90/10,
# 70/30 — **hepsi gerçek katılma hesabı paylaşım oranı, 0 yanlış alarm.**
#
# İki biçim kuralı ölçümden geldi:
#   * Yüzdeler TAM SAYI olmak zorunda (`(?![\d.,])`). Ondalığa izin verilseydi
#     "%1,99 ya da 25 Gün Blokeli %0" ifadesindeki virgül bağlaç sanılıp
#     1 + 99 = 100 çıkıyordu — ölçüldü, 18 belgede yanlış alarm.
#   * Bağlaç yalnız iyelikli "'a/'e", tire ya da bölü olabilir. Virgül bağlaç
#     DEĞİLDİR (aynı gerekçe).
_PAYLASIM_CIFTI_RE = re.compile(
    r"%\s*(\d{1,3})(?![\d.,])\s*(?:['’]\s*[ae]|[-–—/])\s*%?\s*(\d{1,3})(?![\d.,])")

# Paylaşım FİİLİ — "paylaşılır", "paylaşım oranı", "bölüşülür".
_PAYLASIM_FIILI_RE = re.compile(r"payla[şs]|b[öo]l[üu][şs]", re.IGNORECASE)

# Fiil, çiftin bu kadar karakter yakınında aranır. 160 karakter hem
# "…hesap sahibi ile kurum arasında %40'a %60 şeklinde paylaşılır" cümlesini
# hem de tablo başlığı ile satırı arasındaki mesafeyi ("Kar Paylaşım Oranı …
# %98-%2") kapsar; belgenin geri kalanına taşmaz. Belge düzeyinde serbest
# bırakmak yanlış olurdu: "Whatsapp'da paylaş" düğmesi neredeyse her sayfada
# var ve fiil ölçütünü anlamsızlaştırırdı.
_PAYLASIM_FIIL_PENCERE = 160


def paylasim_cifti_araliklari(text: str) -> list[tuple[int, int]]:
    """Toplamı 100 eden yüzde çiftlerinin (başlangıç, bitiş) konumları.

    Tek doğruluk kaynağı: hem belge düzeyi kapı hem değer düzeyi kapı bu
    listeyi kullanır. Aynı deseni iki yerde yazmak bu depoda beş kez ayrışmaya
    yol açtı (bkz. `rules/ihtar.py` başlığı).
    """
    out: list[tuple[int, int]] = []
    for m in _PAYLASIM_CIFTI_RE.finditer(text):
        if int(m.group(1)) + int(m.group(2)) == 100:
            out.append(m.span())
    return out


def _paylasim_beyani_var(text: str) -> bool:
    """Belge bir kâr PAYLAŞIM oranı ilan ediyor mu (çift + yakınında fiil)?"""
    for s, e in paylasim_cifti_araliklari(text):
        pencere = text[max(0, s - _PAYLASIM_FIIL_PENCERE):
                       e + _PAYLASIM_FIIL_PENCERE]
        if _PAYLASIM_FIILI_RE.search(pencere):
            return True
    return False


def _paylasim_ciftinin_parcasi(text: str, s: int, e: int) -> bool:
    """Değerin kendisi, toplamı 100 eden bir çiftin İÇİNDE mi?

    Fiil ARANMAZ ve aranmamalı: "%40'a %60" ifadesi tek başına zaten tek bir
    oran OLAMAZ. Belge düzeyi kapının kaçırdığı (fiilin uzakta kaldığı) vakayı
    bu tutar.
    """
    return any(bas <= s and e <= son
               for bas, son in paylasim_cifti_araliklari(text))


#: "kâr payı" / "kâr oranı" / "kâr payı oranı" — üçü de aynı şeyi adlandırır.
#:
#: "payı" 2026-08-12'de OPSİYONEL yapıldı. Gerekçe ölçülmüş bir kaçırmaydı:
#: Dünya Katılım Enerya belgesinde "Enerya ihtiyaç Finansmanı **kâr oranı**
#: aylık %3,99'dur" cümlesi hiç yakalanmıyordu (gold 3.99, çıkarım `None`).
#:
#: Bu tutarsızlık dosyanın İÇİNDEydi: `_ORAN_TABLOSU_BASLIK_RE` "payı"yı
#: zaten opsiyonel yapmış ("Bankalar farklı etiket kullanıyor"), ama düz
#: cümle desenleri katı kalmıştı. Aynı belgede tablo başlığı kabul edilen
#: bir terim, cümle içinde reddediliyordu.
#:
#: "payı" ve "oranı"ndan EN AZ BİRİ zorunludur — ikisi birden opsiyonel
#: olamaz. Yalnız "kâr" serbest bırakılsaydı "%20 kâr elde edin" gibi
#: pazarlama cümleleri finansman kâr payı oranı sanılırdı. Alternatifler
#: uzundan kısaya sıralı: regex ilk eşleşeni alır, "kâr payı oranı"
#: bütünüyle tüketilmelidir.
# `pay[ıi](?:l[ıi])?`: "kâr payı" kadar "Kâr Paylı" da aynı terimdir, yalnız
# sıfat hâlidir. Ölçüldü (19 Ağu 2026, 1.782 belgelik korpus): başlıkta
# "Kuveyt Türk Müşterilerine Özel %1,99 Oranlı Kar Paylı Taksitlendirme
# Fırsatı" yazan belgede oran hiç çıkarılmıyordu, çünkü desen yalnız "payı"
# ekini tanıyordu.
_KAR_PAYI_ETIKET = (
    r"(?:kâr|kar)\s*(?:pay(?:l[ıi]|[ıi])\s*oran[ıi]"
    r"|pay(?:l[ıi]|[ıi])|oran[ıi])"
)

# Araya YALNIZ "oranlı" sözcüğü girebilir — serbest mesafe DEĞİL.
#
# ÖLÇÜLMÜŞ YANLIŞ DENEME, tekrarlanmasın: mesafeyi `\s{0,3}` yerine 12
# karakterlik serbest bir pencereye ("[^.;:!?%]{0,12}") açmak denendi ve
# `tests/test_kar_payi_yon.py::test_araya_kelime_girerse_kapilmaz` anında
# kırıldı. Kanıt cümlesi: "%15 indirim ve kâr payı oranı %1,89" — araya giren
# " indirim ve " TAM 12 karakter, yani gevşetme indirimin oranını kâr payı
# oranı olarak kapıyordu. Geri yönlü arama gevşerse başka alanların değerini
# kapar; o test tam bu sınıfı koruyor.
#
# Doğru çözüm mesafeyi büyütmek değil, araya girmesine izin verilen sözcüğü
# ADIYLA saymak. Korpusta ölçülen tek sınıf sıfat hâli:
# "Kuveyt Türk Müşterilerine Özel %1,99 Oranlı Kar Paylı Taksitlendirme" —
# burada "Oranlı" zaten oranın kendisini niteliyor, yabancı bir alan
# getirmiyor. Yeni bir sınıf çıkarsa buraya adıyla eklenir; pencere yeniden
# serbest bırakılmaz.
_KAR_PAYI_ONCE_RE = re.compile(
    rf"(%\s*\d[\d.,]*)\s{{0,3}}(?:oranl[ıi]\s+)?{_KAR_PAYI_ETIKET}",
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
    r"(?:devlet\s*(?:katk|destek|deste[ğg])|puanl[ıi]k"
    # "akdi kâr payı oranının %30 FAZLASI / ARTIRIMI" — değer oranın kendisi
    # değil, orana uygulanan ÇARPANDIR. Sözleşme metinlerinde gecikme cezası
    # hep bu kalıpla yazılır (bkz. `_CEZA_BAGLAMI_RE`).
    r"|fazla|artt?[ıi]r[ıi]m|katt?[ıi])",
    re.IGNORECASE,
)
# Değerin sağında bu kadar karakter içinde yabancı kavram aranır. 30 karakter
# "'ye kadar devlet katkısıyla" ifadesini kapsar, sonraki cümleye taşmaz.
_YABANCI_KAVRAM_PENCERE = 30

# Değerden ÖNCE gelip onu kâr payı oranı olmaktan çıkaran bağlam: gecikme
# cezası / temerrüt maddeleri.
#
# Ölçüm (2026-08-07, 1761 belgelik korpus, `data/demo.v2.db`): korpus `docs/`
# bölümündeki sözleşme ve tarife PDF'leriyle büyüdükten sonra üretilen 84
# `kar_payi_orani` kaydının **15'i (%17,9)** bir ceza maddesinden geliyordu.
# Tipik metin:
#
#     "Gecikme Cezası Oranı, akdi kâr payı oranının %30 fazlasını geçemez."
#
# Buradaki %30 ürünün kâr payı oranı DEĞİL, gecikme hâlinde orana uygulanan
# artırımdır. Karşılaştırma tablosuna girdiğinde bankayı %30 "oranla" en
# pahalı gösteriyordu — sessizce yanlış değer üreten sınıftan.
#
# Kapı ÇİFTTİR ve ikisi de aynı vakayı bağımsız yakalar: sağdaki `fazla|
# artırım` eki (`_YABANCI_KAVRAM_RE`) ve soldaki ceza bağlamı (bu desen).
# Birinin kaçırdığını diğeri tutar; korpusta iki kalıp da gözlendi.
# "akdi kâr payı oranı" BİLEREK YOK: o, sözleşmedeki GERÇEK kâr payı oranıdır.
# Korpusta doğrulandı — "Bankamızca, akdi kâr payı oranı %0 olarak
# belirlenmiştir" cümlesindeki %0 kartın gerçek oranıdır ve tutulmalıdır.
_CEZA_BAGLAMI_RE = re.compile(
    r"\b(?:gecikme|temerr[üu]t|ceza[ıi]?)", re.IGNORECASE)
# Değerin solunda bu kadar karakter geriye bakılır — ama CÜMLE sınırını
# aşmadan. Sınır olmasa "…%1,89 kâr payı. Gecikme cezası…" sırasındaki
# gerçek oran, SONRAKİ cümlenin ceza sözcüğü yüzünden reddedilirdi.
_CEZA_BAGLAMI_PENCERE = 90


# Değeri kâr payı oranı olmaktan çıkaran ÜÇÜNCÜ sınıf: türev/oransal ifade.
#
# Bunlar ceza maddesi DEĞİLDİR — `_CEZA_BAGLAMI_RE`'yi genişletmek yanlış
# teşhis olurdu. Ortak yapıları şu: değer, oranın KENDİSİ değil orana ya da
# kâr payına uygulanan bir katsayıdır. Üç kalıp korpusta ölçüldü
# (2026-08-08, `data/demo.db`, 70 `kar_payi_orani` kaydı):
#
#   4 kayıt  "yıllık bileşik kâr payı oranının YÜZDE 5'İ ile kalan vade…"
#            -> 5 bir çarpandır; erken ödeme tazminatı formülünün parçası.
#   4 kayıt  "brüt kâr payının %50'Sİ geri alınır"
#            -> 50 kâr PAYLAŞIM payıdır, finansman oranı değil.
#   3 kayıt  "(Finansmanın yıllık bileşik kâr payı oranı * 0,05) + …"
#            -> 0,05 aynı formülün cebirsel yazımı.
#
# Üçü de karşılaştırma tablosuna girdiğinde bankayı yanlış konumlandırıyordu;
# demonun manşet sorusu ("en düşük kâr payı hangi bankada?") tam bu alanı
# sıralıyor.
#
# Ayırt edici işaret İYELİK EKİdir: "oranı %5" ile "oranıNIN %5'i" farklı
# şeylerdir. Birincisi oranın kendisi, ikincisi ondan türetilen bir büyüklük.
_TUREV_ORAN_RE = re.compile(
    r"(?:oran|pay)[ıi]n[ıi]n\s*(?:y[üu]zde\s*|%\s*)?\d",
    re.IGNORECASE,
)
# Cebirsel yazım: değerin yakınında çarpma işareti. "* 0,05" ya da "x 0,05".
_CARPAN_RE = re.compile(r"[*x×]\s*0[.,]\d")
_TUREV_PENCERE = 90


def _turev_oran_baglami(text: str, match_start: int, match_end: int) -> bool:
    """Değer, bir orandan TÜRETİLMİŞ büyüklük mü (oranın kendisi değil)?

    `_ceza_baglami_onceliyor` ile aynı cümle-sınırı disiplinini kullanır:
    sınır olmasa "…%1,89 kâr payı. Kâr payı oranının yüzde 5'i…" sırasındaki
    GERÇEK oran, sonraki cümle yüzünden reddedilirdi.
    """
    bas = max(0, match_start - _TUREV_PENCERE)
    onceki = text[bas:match_start]
    for ayirac in (". ", "! ", "? ", "\n"):
        if ayirac in onceki:
            onceki = onceki.rsplit(ayirac, 1)[1]
    # Değerin kendisi de kalıba dahil: "oranının yüzde 5'i"nde sayı SAĞDA.
    if _TUREV_ORAN_RE.search(onceki + text[match_start:match_end]):
        return True
    # Cebirsel yazımda çarpan değerin İÇİNDE ya da hemen sağında olur.
    return bool(_CARPAN_RE.search(onceki + text[match_start:match_end + 8]))


def _ceza_baglami_onceliyor(text: str, match_start: int) -> bool:
    """Eşleşmenin solunda, AYNI cümle içinde bir ceza/gecikme maddesi var mı?"""
    bas = max(0, match_start - _CEZA_BAGLAMI_PENCERE)
    onceki = text[bas:match_start]
    # Cümle sonu varsa yalnız son cümlenin kalanına bak.
    for ayirac in (". ", "! ", "? ", "\n"):
        if ayirac in onceki:
            onceki = onceki.rsplit(ayirac, 1)[1]
    return bool(_CEZA_BAGLAMI_RE.search(onceki))


def _yabanci_kavram_takip_ediyor(text: str, value_end: int) -> bool:
    """Değerden hemen sonra BAŞKA bir kavramın adı geliyor mu?"""
    return bool(_YABANCI_KAVRAM_RE.match(
        text[value_end:value_end + _YABANCI_KAVRAM_PENCERE]))


# Değeri kâr payı oranı olmaktan çıkaran DÖRDÜNCÜ sınıf: BOZUK HESAPLAMA
# ARACI.
#
# Öncekiler (`_YABANCI_KAVRAM_RE`, `_CEZA_BAGLAMI_RE`, `_TUREV_ORAN_RE`) hepsi
# "değer başka bir kavrama ait" hatasıdır — sayfa sağlamdır, okuma yanlıştır.
# Bu ise farklı bir sınıf: SAYFANIN KENDİSİ bozuk yüklenmiştir. Banka
# sitelerindeki finansman hesaplama araçları JavaScript ile doldurulur; scrape
# anında servis cevap vermediğinde widget BAŞLANGIÇ durumunda donar ve HTML'e
# şu iskelet düşer:
#
#     "Kar oranı limitler dışında ! Lütfen kontrol edip tekrar deneyiniz.
#      Service unavailable ! Kâr Oranını Kendim Belirleyeceğim
#      Aylık Taksit Tutarı 0 TL  Ödenecek Toplam Tutar 0 TL
#      Aylık Kâr Oranı % 0"
#
# Buradaki "% 0" bir kampanya değil, DOLDURULMAMIŞ bir form alanıdır. Kural
# yine de etiket + değer görüp `kar_payi_orani = 0.0` üretiyordu; üstelik
# `%` işaretli olduğu için `C.is_plausible` bandına da takılmıyor ve
# `_RULE_CONF = 0.95` ile en yüksek güvenle tabloya giriyordu.
#
# ÖLÇÜLDÜ (2026-08-16, `data/demo.db`, 70 `kar_payi_orani` kaydı): 15 kayıt
# sıfır değerliydi, bunların **7'si** (hepsi tek bankanın 4 ürün sayfasının
# kopyaları) bu bozuk widget'tan geliyordu. Demonun manşet sorusu ("en düşük
# kâr payı hangi bankada?") tam bu alanı sıralıyor; sıfır her zaman tepede
# çıkar, yani hata sessiz değil VİTRİNDEYDİ.
#
# ## Gerçek %0 promosyonları neden zarar görmez
#
# Ayrım BANKA ADINDAN DEĞİL, pencerenin kendisinden kurulur: gerçek bir %0
# kampanyasında tutar ve vade DOLUDUR ve ayrıştırılabilir —
#
#     "%0 kâr payı ile 40.000 TL'ye kadar Pratik Finansman"          (gerçek)
#     "%0 kâr payı oranı ve 3 ay vadeli olarak 50.000 TL'ye kadar"   (gerçek)
#     "Aylık Taksit Tutarı 0 TL Ödenecek Toplam Tutar 0 TL ... % 0"  (bozuk)
#
# Bozuk olanda tutarlar SIFIRDIR, yani sayfa hiçbir şey hesaplamamıştır.
# Kapı iki BOZUKLUK işaretine bakar — (a) etiketİNE BİTİŞİK sıfır tutar,
# (b) aracın hata metni — ve bir SAĞLAMLIK işareti onları geçersizler:
# pencerede etiketine bitişik DOLU (sıfır olmayan) bir tutar varsa sayfa
# hesaplamıştır, ret düşer.
#
# ## Neden etikete BİTİŞİK tutar arıyoruz
#
# Çıplak "0 TL" YETMEZ ve kapıyı fazla genişletirdi. Korpusta gerçek bir %0
# kaydının penceresi şöyle: "Aylık Akdi Kâr Payı Oranı %0 0 TL Ekstre
# Dönemlerinde…" — buradaki "0 TL" ücret tablosunun *Tutar* kolonudur ve
# değer meşrudur (bkz. `_CEZA_BAGLAMI_RE` başlığındaki "akdi kâr payı oranı"
# notu). Etiket ile sayı arasına yalnız ayraç/boşluk girmesine izin vermek
# bu kaydı korur, widget iskeletini yakalar.
#
# İki desen aynı etiket listesini paylaşır (`_TUTAR_ETIKETI`): ayrışırlarsa
# "sıfır tutar var" ile "dolu tutar yok" farklı şeyleri ölçmeye başlar ve
# kapı sessizce tek bacaklı kalır.
_TUTAR_ETIKETI = (
    r"(?:taksit\s*tutar[ıi]"
    r"|[öo]denecek\s*(?:toplam\s*)?tutar"
    r"|toplam\s*(?:geri\s*)?[öo]deme(?:\s*tutar[ıi])?"
    r"|finansman\s*tutar[ıi]"
    r"|kredi\s*tutar[ıi])"
)
_PARA_BIRIMI = r"(?:TL|₺)\b"
_SIFIR_TUTAR = r"0(?:[.,]0+)?\s*" + _PARA_BIRIMI

_SIFIR_TUTAR_RE = re.compile(
    _TUTAR_ETIKETI + r"\s*[:=]?\s*" + _SIFIR_TUTAR, re.IGNORECASE)

# Sayfanın HESAPLADIĞINI kanıtlayan işaret: etiketine bitişik, sıfır OLMAYAN
# bir tutar. Negatif ileri-bakış olmadan "Taksit Tutarı 0 TL" de "dolu"
# sayılır ve kapı hiç kapanmazdı.
_DOLU_TUTAR_RE = re.compile(
    _TUTAR_ETIKETI + r"\s*[:=]?\s*(?!" + _SIFIR_TUTAR + r")"
    r"\d[\d.,]*\s*" + _PARA_BIRIMI,
    re.IGNORECASE,
)

# Hesaplama aracının kendi hata/boş-durum metni. Sayfanın veri üretemediğini
# doğrudan söyler; yanındaki her sayı bu yüzden kanıt değildir.
#
# Bu bacak TEK BAŞINA yetmez, `_DOLU_TUTAR_RE` tarafından geçersizlenebilir —
# ve buna ihtiyaç ÖLÇÜLDÜ. İlk sürüm sağlamlık kapısı olmadan yazıldı ve
# korpusta bir GERÇEK kaydı düşürdü (tom-katilim, `hesaplama-araclari.html`,
# oran 3,99):
#
#     "Aylık Kâr Oranı: 3,99 % Taksit Tutarı: 1.981,98 TL Geri Ödenecek
#      Tutar 11.891,83 TL … Bir hata oluştu, lütfen tekrar deneyin"
#
# Hata cümlesi sayfada GİZLİ bir uyarı kutusudur (DOM'da hep durur); araç ise
# gayet hesaplamıştır. Yani hata metni "veri yok"un kanıtı değil, yalnız
# şüphesidir. Karar veren şey tutarların dolu olup olmadığıdır.
_ARAC_HATASI_RE = re.compile(
    r"service\s+unavailable"
    r"|temporarily\s+unavailable"
    r"|limitler\s+d[ıi][şs][ıi]nda"
    r"|hesaplama\s+yap[ıi]lamad[ıi]"
    r"|bir\s+hata\s+olu[şs]tu",
    re.IGNORECASE,
)

# Pencere ±240 karakter. Ölçülen mesafeler (bozuk widget, 7 kayıt): sıfır
# tutar bloğu değerden 44–68, hata metni 110–130 karakter önce. 240 ikisini
# de kapsar. Simetrik tutuluyor çünkü widget iskeletinde blok sıranın
# ARDINDA da durabilir ("Aylık Kâr Oranı % 0 … Aylık Taksit Tutarı 0 TL");
# sağa bakmak korpustaki hiçbir gerçek kaydı düşürmedi (ölçüldü).
_BOZUK_ARAC_PENCERE = 240


def _bozuk_hesaplama_araci(text: str, match_start: int, match_end: int) -> bool:
    """Değerin penceresi, veri üretmemiş bir hesaplama aracına mı ait?

    True dönerse çağıran eşleşmeyi REDDEDER (halüsinasyon yasağı, CLAUDE.md
    §19: bilgi yoksa `null`). Ret gerekçesi `DEBUG` seviyesinde loglanır —
    sessiz eleme, sessiz uydurma kadar izlenemezdir.

    Sıra önemlidir: önce SAĞLAMLIK kanıtı aranır. Dolu bir tutar varsa sayfa
    hesaplamıştır ve bozukluk işaretleri (gizli hata kutusu gibi) artık
    bağlayıcı değildir.
    """
    bas = max(0, match_start - _BOZUK_ARAC_PENCERE)
    son = min(len(text), match_end + _BOZUK_ARAC_PENCERE)
    pencere = text[bas:son]
    dolu = _DOLU_TUTAR_RE.search(pencere)
    if dolu is not None:
        return False
    for neden, desen in (("sifir_tutar", _SIFIR_TUTAR_RE),
                         ("arac_hatasi", _ARAC_HATASI_RE)):
        isaret = desen.search(pencere)
        if isaret is None:
            continue
        logger.debug(
            "kar_payi_orani REDDEDİLDİ (bozuk hesaplama aracı): neden=%s "
            "isaret=%r deger=%r konum=%d",
            neden, isaret.group(0), text[match_start:match_end], match_start,
        )
        return True
    return False


def extract_kar_payi(text: str) -> Optional[ExtractedField]:
    """Kâr payı oranı: '... kâr payı oranı %1,99 ...' veya '%1,99 kâr payı'.

    İki yön de denenir. ÖNCE geri yönlü bakılır: `%` ile işaretlenmiş ve
    anahtar kelimeye bitişik bir sayı, anahtar kelimeden sonra gelen
    işaretsiz bir sayıdan daha güçlü kanıttır. Bu sıra olmadan
    "%1,89 kâr payı oranı ile 120 aya kadar" ifadesi 120 döndürüyordu.
    """
    if _PAYLASIM_ORANI_RE.search(text) or _paylasim_beyani_var(text):
        # "kâr payı PAYLAŞIM oranı %55'e %45" — bu, banka ile müşteri
        # arasındaki kâr BÖLÜŞÜMÜ, finansman kâr payı oranı DEĞİL. İkisini
        # aynı alana yazmak karşılaştırmayı bozar: %55 bir "oran" olarak
        # tabloya girip o bankayı en pahalı gösterirdi.
        #
        # İki kapı BİRLİKTE durur ve farklı vakaları tutar: tamlama araması
        # ("kâr payı paylaşım oranı") ile toplamı 100 eden çift + paylaşım
        # fiili. İkincisi, tamlamayı hiç kullanmayan
        # "Hesabın kâr payı oranı %40'a %60'dır" cümlesini yakalar.
        # Anotasyon tarafındaki karar: `kar_payi_orani = absent`
        # (`data/gold/ANNOTATION_GUIDE.md`, biçim kartı §3 kural 7).
        return None
    # Yabancı kavram takip eden eşleşmeler ATLANIR, ilk eşleşmede durulmaz:
    # aynı belgede gerçek kâr payı oranı daha sonra gelebilir.
    for onceki in _KAR_PAYI_ONCE_RE.finditer(text):
        s, e = onceki.span(1)
        if (_yabanci_kavram_takip_ediyor(text, onceki.end())
                or _ceza_baglami_onceliyor(text, onceki.start())
                or _turev_oran_baglami(text, s, e)
                or _paylasim_ciftinin_parcasi(text, s, e)
                or _bozuk_hesaplama_araci(text, s, e)):
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
    # `()` BOŞ YER TUTUCU — silmeyin. Aşağıdaki gövde değeri `group(3)` /
    # `span(3)` ile okur; etiket tek gruba indiğinde ("kâr|kar" + "oranı"
    # ayrı gruplardı) değer 3'ten 2'ye kayardı ve `raw` etiketin kendisi
    # olurdu. Grup numarasını sabit tutmak, çağrı yerlerini değiştirmekten
    # daha az riskli.
    pat = re.compile(
        rf"({_KAR_PAYI_ETIKET})()[^%\d]{{0,15}}"
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
        # Değeri yabancı bir kavram takip ediyorsa, eşleşmeyi bir ceza maddesi
        # öncelİyorsa, değer orandan TÜRETİLMİŞ bir büyüklükse ya da pencere
        # veri üretmemiş bir hesaplama aracına aitse eşleşme reddedilir ve
        # aramaya devam edilir (gerekçe: `_YABANCI_KAVRAM_RE`,
        # `_CEZA_BAGLAMI_RE`, `_TUREV_ORAN_RE`, `_bozuk_hesaplama_araci`).
        if (_yabanci_kavram_takip_ediyor(text, e)
                or _ceza_baglami_onceliyor(text, m.start())
                or _turev_oran_baglami(text, s, e)
                or _paylasim_ciftinin_parcasi(text, s, e)
                or _bozuk_hesaplama_araci(text, s, e)):
            continue
        raw = m.group(3)
        canon = N.normalize_rate(raw)
        # İŞARETSİZ değer makul bandın dışındaysa oran DEĞİLDİR.
        #
        # Bu desende `%` opsiyoneldir ("kâr oranı 3,99") ve tablo
        # başlıklarında etiketten hemen sonra veri satırı gelir; ilk sayı
        # etiketin değeri sanılır. Ölçüldü (2026-08-12, demo.db):
        #
        #   "Finansman Tutarı Vade Aylık Kar Oranı 250-TL-40.000-TL"
        #        -> 250   (bir TUTAR aralığının başlangıcı, oran değil)
        #
        # `%` taşıyan değer bu kapıya girmez: işaretin kendisi zaten oran
        # olduğunu söyler ve "%0 kâr payı" gibi meşru sıfırlar korunur
        # (bant zaten 0'ı içerir, ama işaretsiz sıfır da elenmemeli).
        if "%" not in raw and C.is_plausible("kar_payi_orani", canon) is False:
            continue
        return _field(
            "kar_payi_orani", raw, canon, _window(text, m.start(), m.end()),
            span_start=s, span_end=e,
            # "kâr payı oranı" bitişi ile değerin başı arası
            trigger_distance=s - m.end(1),
            candidate_count=len(pat.findall(text)),
        )
    return None
