"""Kural tabanlı (deterministik) alan çıkarımı — BİRİNCİL katman.

İlgili kararlar:
- ../../decisions/ner-fine-tune-yerine-kural-few-shot.md  (kurallar birincil)
- ../../concepts/bilgi-cikarimi.md

Her çıkarıcı bir ExtractedField döndürür: canonical_value + confidence + source_span.
Bulamazsa alanı hiç üretmez (None döner) — boşluğu LLM katmanı doldurur.
Halüsinasyon yasağı: değer uydurma.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Optional

from ...normalization import normalize as N
from ...preprocessing.clean import split_sentences, tr_fold
from ...schemas import ExtractedField, Extractor
from . import confidence as C
from .ihtar import ihtar_mi
from .kabuk import kabuk_baslangici
from .synonyms import NEGATION_RE

# Kural katmanının güveni yüksektir (deterministik); LLM'inkinden ayrışsın diye 0.95.
_RULE_CONF = 0.95

# Bağlam reddi gerekçeleri buraya yazılır (DEBUG). Sessizce elenen bir değer,
# sessizce uydurulan bir değer kadar izlenemezdir; ret kararı görünür kalmalı.
logger = logging.getLogger(__name__)


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
            # Kanıt penceresi güvene girer: gezinme/SSS bağlamındaki değer daha
            # az kesindir (bkz. confidence.looks_like_chrome). Pencere burada
            # zaten hesaplanmış durumda; geçirmemek sinyali boşa harcamak olurdu.
            window=span,
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
        r"(\d[\d.,]*)\s*(ay|yıl|yil|sene)(?:a|da|ta|dan|tan|ı|i|lık|lik)?\b",
        re.IGNORECASE,
    )
    matches = [m for m in pat.finditer(text) if not _takvim_yili(m)]
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
    canon = N.normalize_term_months(raw)
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


# Tetikleyici ile sayı arasındaki boşlukta CÜMLE SINIRI olamaz.
# Ölçülen halüsinasyon (`turkiye-emlak-katilim--finansmanlar-ihtiyac-finansmani`):
#   "...ihtiyaç finansmanı ürünüdür. Fiyatı 20.000 TL'ye kadar olan cep telefonu"
# Tetikleyici bir cümlede, sayı başka cümlede ve sayı bir TELEFON FİYATI.
# Nokta+boşluk+büyük harf aranıyor; "max. 100.000 TL" gibi kısaltmalar bozulmasın
# diye noktadan sonra RAKAM gelen durum sınır sayılmaz.
_CUMLE_SINIRI_RE = re.compile(r"[.!?;]\s+[A-ZÇĞİÖŞÜ]|\n")

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


# Cümle sınırı. Ondalık/binlik noktayı sınır SAYMAZ — `_ORAN_IFADESI`'ndeki
# lookaround ile aynı gerekçe: "1.500,00" içindeki nokta cümle bitirmez.
_CUMLE_SINIRI_RE = re.compile(r"(?<!\d)[.;!?](?!\d)|\n")


def _cumle_araligi(text: str, bas: int, son: int) -> tuple[int, int]:
    """Eşleşmeyi içeren cümlenin OFFSET aralığı (bkz. `_cumle_kapsami`)."""
    sol = 0
    for m in _CUMLE_SINIRI_RE.finditer(text, 0, bas):
        sol = m.end()
    sag_m = _CUMLE_SINIRI_RE.search(text, son)
    sag = sag_m.start() if sag_m else len(text)
    return sol, sag


def _cumle_kapsami(text: str, bas: int, son: int) -> str:
    """Eşleşmeyi içeren cümle — iki yanı da cümle sınırında kesilir.

    `extract_masraf`'ın mevcut ileri penceresi (`m.end() + 40`) yalnız SAĞA
    bakıyor; öznenin nerede olduğunu görmek için SOLA da bakmak gerekiyor
    ("Katılım SMS'i ücretsiz" — özne solda).
    """
    sol, sag = _cumle_araligi(text, bas, son)
    return text[sol:sag]


# KANIT ARALIĞI — `masraf_durumu` span'i neden tetikleyici sözcükten geniş.
#
# ## Ölçülen kusur (2026-08-16, `data/demo.db`, 494 kayıt)
#
# `masraf_durumu` kanıt olarak yalnız TETİKLEYİCİ SÖZCÜĞÜ saklıyordu:
# 494 kaydın **488'i tek sözcük** (`Ücretsiz` 176, `ücretsiz` 145, `ücret` 95,
# `Ücret` 23, `Masrafsız` 13, `masraf` 12, `masrafsız` 11, `tahsis` 12).
# Komşu kurallar cümleyi saklıyor: `extract_tahsis_ucreti` → "tahsis ücreti
# yansıtılmayacaktır", muafiyet yolu → "ekspertiz ücreti banka tarafından
# karşılanmaktadır".
#
# `masrafsız` bir KANIT DEĞİL, bir ETİKETTİR — kanonik değerin kendisinin
# tekrarı. Şartname 7 sütunlu ürün tablosunda «Kampanya Avantajı» hücresi
# kanıt cümlesi okunabilir olduğunda bankanın kendi ifadesini basıyor; tek
# sözcüklü kanıt ayakta duramadığı için o hücrede yan kolonun birebir
# tekrarı görünüyordu ("Masraf Durumu: masrafsız").
#
# ## Bunun bilinçli bir karar OLMADIĞI nasıl saptandı
#
# `git log -S`, `docs/`, vault `decisions/` ve kod yorumları tarandı: span
# darlığı için hiçbir gerekçe yok. Darlık desenin doğal sonucu — `pat` tek
# sözcük eşliyor, `m.span()`/`m.group(0)` doğrudan kullanılıyordu. Tersine
# bir kanıt var: DEĞER zaten 40 karakterlik ileri pencereden (`fwd`)
# hesaplanıyor, yani KAYDEDİLEN kanıt KULLANILAN kanıttan dardı.
#
# ## Neden cümlenin tamamı değil
#
# Ölçüldü: cümle uzunluğu medyan 108 kr ama p90=474, p99=1373, maks=2781
# (noktalama içermeyen tablo dökümleri). 67 kayıt 400 karakteri aşardı —
# "kanıt" değil metin dökümü olurdu. Bu yüzden aralık CÜMLEYLE SINIRLI ama
# tetikleyici çevresinde budanır: solda 40 karakter (sağdaki `fwd` penceresi
# ile aynı sayı — yeni bir sabit uydurmamak için), sağda tam olarak değerin
# hesaplandığı `fwd` sınırı. Yani kaydedilen kanıt, kullanılan kanıtın
# üst kümesidir ve cümleyi asla aşmaz.
#
# ## Değişmez (`verify_span`)
#
# `raw_value` BİTİŞİK dilim olmak zorunda: `text[span_start:span_end] ==
# raw_value`. Bu yüzden `m.group(0)` değil `text[sol:sag]` yazılır —
# `extract_tahsis_ucreti` ile birebir aynı disiplin.
_KANIT_SOL_PAY = 40

#: Sağ kenarda yarım kalan sözcüğü tamamlamak için izin verilen taşma.
#: Türkçe sondan eklemeli; "yararlanabilirsiniz" gibi uzun çekimler için
#: 30 karakter yeter, kaçak bir uzamaya ise izin vermez.
_KANIT_SAG_TASMA = 30

#: Sözcük karakteri — Türkçe harfler ve rakamlar dâhil (`\w` yeterli ama
#: niyeti adlandırmak okunurluğu artırıyor).
_SOZCUK_KARAKTERI = re.compile(r"\w").match


def _kanit_araligi(text: str, m: "re.Match[str]", fwd: str) -> tuple[int, int]:
    """Tetikleyiciyi taşıyan tümceciğin aralığı — cümleyi AŞMAZ.

    Sağ sınır `fwd`'nin bittiği yerdir: değer oradan hesaplandı, kanıt da
    tam orayı göstermeli. Sol sınır cümle başı ile 40 karakter arasında,
    sözcük ortasından başlamayacak şekilde hizalanır.
    """
    cumle_sol, _ = _cumle_araligi(text, m.start(), m.end())
    sol = max(cumle_sol, m.start() - _KANIT_SOL_PAY)
    # Sözcük ortasına düştüyse GERİYE kayarak sözcük başına hizala. İleri
    # kaymak sözcüğü yarım bırakmaz ama anlamlı bir niteleyiciyi düşürürdü:
    # "Kampanya kapsamında dosya masrafı alınmamaktadır" cümlesinde 40
    # karakterlik sınır "Kampanya"nın içine düşüyor ve ileri hizalama kanıtı
    # "kapsamında …" diye başlatıyordu. Taşma en fazla bir sözcük kadardır
    # ve cümle başı (`cumle_sol`) her hâlükârda aşılmaz.
    while sol > cumle_sol and not text[sol - 1].isspace():
        sol -= 1
    sag = m.start() + len(fwd)
    # SAĞ KENAR SÖZCÜK ORTASINDA KALMASIN.
    #
    # `fwd` üç yoldan biriyle biter ve yalnız biri sözcüğü yarıda keser:
    #   · cümle sınırı  -> sonraki karakter `.`/`;`/`\n`, sözcük zaten bitmiş
    #   · sütun başlığı -> kesim başlığın BAŞIdır, solunda boşluk var
    #   · 40 karakterlik üst sınır -> KEYFİ nokta, sözcüğü ortadan böler
# Ölçüldü: elle doğrulamada "tahsil edilece", "2 aylık öd", "50 yapr"
    # gibi kırık kanıtlar tam bu üçüncü yoldan geliyordu. Koşul iki yanın da
    # sözcük karakteri olmasını arar; ilk iki yol bu koşula hiç girmez.
    # Uzatma cümle sonuyla ve `_KANIT_SAG_TASMA` ile iki kez sınırlı.
    cumle_sag = _cumle_araligi(text, m.start(), m.end())[1]
    sinir = min(cumle_sag, sag + _KANIT_SAG_TASMA)
    if 0 < sag < len(text) and _SOZCUK_KARAKTERI(text[sag - 1]):
        while sag < sinir and _SOZCUK_KARAKTERI(text[sag]):
            sag += 1
    # Baştaki/sondaki boşluk dilime girmesin — değişmez korunarak kırpılır.
    while sol < sag and text[sol].isspace():
        sol += 1
    while sag > sol and text[sag - 1].isspace():
        sag -= 1
    if sag <= sol:                                      # pragma: no cover
        return m.span()
    return sol, sag


# ALAN-DIŞI ÖZNE: "ücretsiz"in nitelediği şey ÜRÜN DEĞİL.
#
# ## Ölçülen kusur (2026-08-12, `data/gold/gold.v2.json`)
#
# `masraf_durumu` 10 yanlış pozitifin **9'unda değer UYDURUYORDU** (gold
# "YOK" diyor). Dokuzun yedisi n>=3'lük iki aileydi ve ikisinde de bedava
# olan şey kampanyanın ürünü değildi:
#
#   4x  "Katılım SMS'i ücretsiz olup; ... Turkcell, Vodafone ..."   -> KANAL
#   3x  "Talebiniz ... otuz (30) gün içinde ücretsiz olarak
#        sonuçlandırılmaktadır."                                    -> YASAL TALEP
#
# Alan bileşik avantaj skorunda ikinci en yüksek ağırlığa sahip (0,20,
# `comparison/compare.py:697`), yani uydurma "masrafsız" doğrudan "En
# Avantajlı" sıralamasına giriyordu.
#
# ## Neden bu kapı meşru iddiayı elemiyor (ölçüldü)
#
# Aynı yordam gold'daki 6 MEŞRU çıkarıma da uygulandı: SMS ailesi 4/4
# halüsinasyonda, **0/6** meşruda; talep ailesi 3/3'e karşı **0/6**.
# Mesafeyle de ayrık: halüsinasyonlarda "SMS" jetonu span'dan 3 karakter
# geride, en yakın meşru vakada 5.222 karakter.
#
# ## Kapsam dışı bırakılan 2 vaka (bilerek)
#
# "TOD ayrıcalığını ücretsiz yaşa" (n=1) ve "Ücretsiz İSPARK Otopark
# Kampanyası" (n=1). İkisi de üçüncü taraf hizmet; kapsam kuralı
# (`ANNOTATION_GUIDE.md` §4) ikisini de dışarıda bırakıyor. Yine de kural
# YAZILMADI ve gerekçe 19 Ağustos'ta DEĞİŞTİ — eskisi artık geçersiz:
#
# * ESKİ gerekçe: "yapısal ikizi gold'da MEŞRU (GastroClub üyeliği …
#   ücretsiz), iki vaka çelişiyor". Bu çelişki HAKEM-03 turunda ÇÖZÜLDÜ:
#   GastroClub kaydı `absent_fields`'a taşındı ve `club|kulüp … üyeliği`
#   kolu yukarıya eklendi. Yani ikiz artık meşru değil.
# * YENİ gerekçe: kuralı yazacak ayırt edici bir sinyal ÖLÇÜLDÜ VE ÇÜRÜDÜ.
#   Hipotez şuydu: "ücretsiz"in yakınında bir ücret KALEMİ adı (ücret,
#   masraf, komisyon, bedel, tahsis, ekspertiz, dosya, işletim, havale,
#   EFT, aidat, harç…) yoksa çıkarma. Gold'da ölçüldü (tetikleyici sözcük
#   pencereden çıkarılarak — ilk ölçüm "ücretsiz" içindeki "ücret"i
#   sayarak yanlış sonuç vermişti):
#
#       meşru çıkarımlarda kalem: 1/5      halüsinasyonlarda: 0/2
#
#   Yani kural halüsinasyonların ikisini de elerdi ama MEŞRU beşin dördünü
#   de elerdi ("masrafsız bankacılık", "masrafsız ekosistem", "PTT
#   ATM'lerinden ücretsiz para çekme", "e-posta üzerinden ücretsiz
#   gönderim"). Ayrım semantiktir: bankacılık hizmeti mi, üçüncü taraf
#   hizmet mi. Regex'le ayırmak için marka adı listesi (TOD, İSPARK,
#   GastroClub, Halalbooking) gömmek gerekirdi — aşağıdaki "Bilerek kapsam
#   dışı" notunun banka adları için verdiği §21 gerekçesinin aynısı.
#
# Kalan iki halüsinasyon bu yüzden BİLİNEREK duruyor ve testte
# (`test_masraf_alan_disi.py`) 2 üst sınırıyla kilitli.
#
# `preprocessing/blocks.py` bu sorun için yazılmış ve docstring'i "KVKK'daki
# ücretsiz" örneğini anıyor; iki sebeple yetmedi: (1) `extract_all` ona hiç
# danışmıyor, (2) danışsaydı da bölge yayılımı (`YAYILIM_BLOK=6`) KVKK
# cümlesinden tam bir blok önce sönüyor. Paylaşılan sabiti değiştirmek
# özet/görünürlük yollarını 1.782 belgede etkileyeceği için burada CÜMLE
# kapsamlı yerel bir kapı seçildi.
_ALAN_DISI_OZNE_RE = re.compile(
    # Kanal: katılım/işlem SMS'inin bedeli ürünün masrafı değildir.
    r"\bsms\b|k[ıi]sa\s*mesaj"
    # Yasal talep: KVKK m.13 başvurusunun ücretsiz sonuçlandırılması.
    r"|(?:talebiniz|talep|ba[sş]vurunuz|ba[sş]vuru)[^.]{0,80}sonu[cç]land[ıi]r"
    # ÜÇÜNCÜ TARAF AVANTAJ PROGRAMI ÜYELİĞİ (HAKEM-03, 19 Ağu 2026).
    #
    # "GastroClub üyeliği şimdi Hayat Finans müşterilerine özel ve ücretsiz!"
    # cümlesinden `masraf_durumu = {has_fee: false, amount: 0}` üretiliyordu
    # ve belge `/compare?field=masraf_durumu` tablosunda **"masrafsız"
    # rozetiyle** görünüyordu. Bir restoran indirim kulübünün üyelik
    # bedelinin sıfır olması, finansmanın ya da hesabın maliyeti hakkında
    # hiçbir şey söylemez — kıyas tablosunda o rozet yanlış bir iddiadır.
    # Kılavuz §4'e eklenen kapsam kuralı ölçütü tek soruyla veriyor: "bu
    # kampanyayı/ürünü alırsam ne kadar masraf öderim?"
    #
    # Kusur önce GOLD'da bulundu (κ turunda `masraf_durumu` κ'sı NEGATİF
    # çıktı, -0,103) ve hakemlikte gold düzeltildi; ardından iki test
    # düşerek motorun DA aynı kapsam hatasını yaptığını gösterdi. Kapı bu
    # yüzden burada.
    #
    # ÖLÇÜLDÜ (data/demo.db, 1782 belge) — desen neden bu kadar dar:
    #   "club|kulüp … üyeliği"          ->  3 belge (2'si masraf üretiyordu:
    #                                      GastroClub + Halalbooking Loyalty
    #                                      Club, ikisi de üçüncü taraf)
    #   "kart|hesap|kredi … üyelik ücreti" -> 19 belge — DOKUNULMADI, çünkü
    #                                      kredi kartı yıllık üyelik ücreti
    #                                      ürünün KENDİ masrafıdır ve kapsam
    #                                      İÇİNDEDİR. Desende ürün öznesi
    #                                      aranmadığı için bu 19 belge
    #                                      eşleşmiyor (ölçüldü).
    r"|(?:club|kul[üu]b[üu]?)\w*[^.\n]{0,30}?[üu]yeli[gğ]i",
    re.IGNORECASE,
)


# MUAFİYET KALIBI — "X ücreti BANKA TARAFINDAN karşılanmaktadır"
#
# ## Sorun
#
# Şartname s.11, B Bankası konut finansmanı metninin son cümlesi birebir:
#
#     "Kampanya kapsamında ekspertiz ücreti banka tarafından karşılanmaktadır."
#
# s.12'deki beklenen çıktı tablosu bu tek cümleden İKİ hücre bekliyor:
# «Kampanya Avantajı» = "Ekspertiz ücreti banka tarafından karşılanıyor" ve
# «Masraf Durumu» = **"Ekspertiz ücretsiz"**. `masraf_durumu` bu cümleden
# hiçbir şey üretmiyordu (ölçüldü: `None`), yani iki hücre birden boş kalıyordu.
#
# Bu bir NEGASYON/muafiyet kalıbıdır ve CLAUDE.md §6 zaten kuralı koyuyor:
# "masrafsız ≠ değer yok, masraf = 0 demek". §10 eşanlamlılar da
# "masrafsız ≈ ücretsiz ≈ dosya masrafı yok" diyor. "Banka tarafından
# karşılanıyor" bu ailenin bir üyesidir: müşteri açısından ücret SIFIRDIR.
#
# `normalize_fee_status` (normalization katmanı) bu kalıbı tanımıyor ve o
# modül bu değişikliğin sahipliği dışında; kapı bu yüzden kural katmanında.
#
# ## Neden ÇOK DAR yazıldı — ölçüm kapıyı zorladı
#
# ÖLÇÜLDÜ (2026-08-16, 1782 belge). Gevşek bir "ücret … karşılanır" kalıbı
# 52 eşleşme/27 belge veriyor ve **baskın özne müşteridir**:
#
#     müşteri 9 · banka 4 · (kiracı, aracı, garantör, ortak, taraflar …)
#     "ekspertiz ücreti MÜŞTERİ tarafından karşılanacaktır"      (cid=867)
#     "Noter Masrafları … MÜŞTERİ tarafından ödenecektir"        (7 belge)
#
# Yani kalıbın çoğunluğu muafiyetin TERSİdir: sözleşme metni ücreti müşteriye
# yükler. Gevşek kural bunları "masrafsız" diye okuyup en ağırlıklı ikinci
# alana (`compare.DEFAULT_WEIGHTS["masraf_durumu"] = 0.20`) yalan yazardı.
#
# Özneyi bankaya sabitlemek de yetmiyor: "banka öznesi + öde" kalıbı korpusta
# 4 eşleşme veriyor ve **4'ü de yanlış** —
#
#     "…bedellerinin Kart Hamilinin bankası tarafından ÖDENMEMESİ"  (olumsuz)
#     "…mal bedelinin bir bankadan ödeneceğinin garantisi"          (akreditif tanımı)
#     "…söz konusu bedel muhabir banka tarafından…" ×2              (muhabir masrafı)
#
# Bu yüzden kapı üç yerden birden sıkıldı: (1) fiil yalnız `karşılan`/
# `üstlenil` — `öde` YOK, dört yanlışın üçü oradan geliyordu; (2) ücret
# sözcüğü ile banka öznesi arasına en fazla 12 karakter; (3) yüklem olumlu
# olmalı. Sonuç: korpusta **0 eşleşme** (12/25/40 karakterlik boşlukların
# hepsinde), şartname cümlesinde **1**. Sıfır burada başarısızlık değil,
# 47 karşıt vakanın hiçbirine dokunulmadığının kanıtıdır.
#
# ## Bilerek kapsam dışı
#
# "Kargo ve sigorta ücretleri **Dünya Katılım** tarafından karşılanacaktır"
# (cid=1668) gerçek bir muafiyet ama özne BANKA ADI. Onu almak için banka
# adlarını gömmek gerekirdi; aynı biçim korpusta bir İŞ İLANINDA da geçiyor
# ("ücreti Kuveyt Türk tarafından karşılanacak MBA", cid=290) ve ikisi
# şekilce ayırt edilemiyor. §21 uyarınca alınmadı.
_MUAFIYET_FIIL = (
    r"(?:kar[şs][ıi]lan|[üu]stlenil)"
    # Yüklem OLUMLU olmalı. Ekler tek tek sayılıyor — `normalize.NEGATION_RE`
    # ile aynı özgüllük disiplini. "karşılanmaktadır" olumlu, "karşılan-MA-
    # maktadır" olumsuz; ikisini genel bir negasyon deseni ayıramaz.
    # Ünlü uyumunun iki kolu da gerekli: "karşılan-MAKTAdır" (kalın) ve
    # "üstlenil-MEKTEdir" (ince). İnce kol olmadan `üstlenil` bacağı ölüydü.
    # Olumsuzları hâlâ tutar: "üstlenil-ME-mektedir" -> "memektedir", ek
    # listesindeki hiçbir kalıpla baştan eşleşmez.
    r"(?:maktad[ıi]r|makta|mektedir|mekte"
    r"|acakt[ıi]r|acak|ecekt[ıi]r|ecek|m[ıi][şs]|mi[şs]|[ıi]yor|[ıi]r|d[ıi])"
)

#: Ücret türünü niteleyen sözcük olamayacaklar — bağlam/işlev sözcükleri.
#: Bunlar olmasa "kampanya kapsamında ekspertiz ücreti" ifadesinden tür
#: "kapsamında" diye okunurdu (ölçüldü).
_UCRET_TURU_DISI = frozenset({
    "kapsaminda", "kapsami", "olarak", "ayrica", "hicbir", "her", "tum",
    "bu", "soz", "konusu", "ilgili", "gerekli", "ise", "ve", "ile", "bir",
    "adet", "toplam", "diger", "asagidaki", "yukaridaki", "tarafindan",
})

_MUAFIYET_RE = re.compile(
    r"(?:(?P<tur>[\wçğıöşüÇĞİıÖŞÜ]+)\s+)?"
    r"(?P<kalem>[üu]cret|masraf|komisyon)\w*"
    r"[^.;\n]{0,12}?\b(?:bankam[ıi]z|banka|kurumumuz|taraf[ıi]m[ıi]z)(?:ca|ce)?\b"
    r"\s*(?:taraf[ıi]ndan|taraf[ıi]nca)?\s*" + _MUAFIYET_FIIL,
    re.IGNORECASE,
)

#: Muafiyeti KOŞULLU kılan ifadeler — cümlede geçiyorsa muafiyet mutlak
#: değildir ve "ücretsiz" diye yazılamaz. "ilk yıl banka tarafından
#: karşılanır" ikinci yıl ücret VAR demektir; §21: şüphedeysen çıkarma.
_MUAFIYET_KOSUL_RE = re.compile(
    r"\bilk\s+\d*\s*(?:y[ıi]l|ay|d[öo]nem)"
    r"|durumunda|halinde|[şs]art[ıi]yla|ko[şs]uluyla|kayd[ıi]yla"
    r"|hariç|d[ıi][şs][ıi]nda",
    re.IGNORECASE,
)


def _ucret_muafiyeti(text: str) -> Optional[tuple[re.Match, Optional[str]]]:
    """"X ücreti banka tarafından karşılanmaktadır" — muafiyet var mı?

    Dönüş: (eşleşme, ücret türü) ya da None. Ücret türü, muafiyetin HANGİ
    kaleme ait olduğunu taşır ("ekspertiz"); şartname s.12 "Ekspertiz
    ücretsiz" diyor, "masrafsız" değil — tür bilgisini düşürmek o hücreyi
    yanlış doldurmak olurdu.
    """
    for m in _MUAFIYET_RE.finditer(text):
        cumle = _cumle_kapsami(text, m.start(), m.end())
        if _MUAFIYET_KOSUL_RE.search(cumle):
            continue
        if _ALAN_DISI_OZNE_RE.search(cumle):
            continue
        ham = m.group("tur")
        tur = None
        if ham is not None and tr_fold(ham).lower() not in _UCRET_TURU_DISI:
            tur = ham.lower()
        logger.debug(
            "masraf_durumu MUAFİYET: kalem=%r tur=%r konum=%d",
            m.group("kalem"), tur, m.start())
        return m, tur
    return None


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
    # MUAFİYET ÖNCE TARANIR (bkz. `_MUAFIYET_RE`). Bu da bir `has_fee=False`
    # iddiasıdır ve mevcut sözleşme gereği "masrafsız iddiası sırası ne olursa
    # olsun kazanır"; erken dönmek o kuralla tutarlıdır. Farkı, muafiyetin
    # HANGİ kaleme ait olduğunu (`muaf_ucret`) da taşımasıdır.
    muafiyet = _ucret_muafiyeti(text)
    if muafiyet is not None:
        m, tur = muafiyet
        canon: dict = {"has_fee": False, "amount": 0.0}
        if tur is not None:
            # Ek anahtar TOPLAMSAL: tüketiciler (`compare._composite_numeric`,
            # `chatbot/structured.py`) yalnız `has_fee`/`amount` okuyor.
            canon["muaf_ucret"] = tur
        s, e = m.span()
        return _field("masraf_durumu", m.group(0), canon, _window(text, s, e),
                      span_start=s, span_end=e, trigger_distance=0)

    pat = re.compile(r"(masrafs[ıi]z|ücretsiz|ucretsiz|masraf|tahsis|ücret)",
                     re.IGNORECASE)
    first_positive = None
    for m in pat.finditer(text):
        # ALAN-DIŞI ÖZNE KAPISI (bkz. `_ALAN_DISI_OZNE_RE`).
        #
        # `continue` bilinçli: eşleşme ATLANIR, tarama BİTMEZ. `break` ya da
        # erken `return None` olsaydı, alan-dışı bir cümle belgenin gerçek
        # masraf iddiasını gölgeleyebilirdi — halüsinasyonu susturup bilgi
        # kaybı üretmek kazanç değil takas olurdu. Kilidi:
        # `tests/test_masraf_alan_disi.py::test_ayni_belgede_alan_disi_
        # cumle_MESRU_iddiayi_gizlemez`.
        if _ALAN_DISI_OZNE_RE.search(_cumle_kapsami(text, m.start(), m.end())):
            continue
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
            # Kanıt tetikleyici sözcük DEĞİL, onu taşıyan tümceciktir
            # (gerekçe: `_kanit_araligi`).
            s, e = _kanit_araligi(text, m, fwd)
            return _field("masraf_durumu", text[s:e], canon,
                          _window(text, s, e),
                          span_start=s, span_end=e, trigger_distance=0)
        if first_positive is None:
            first_positive = (m, canon, fwd)

    if first_positive is None:
        return None
    m, canon, fwd = first_positive
    s, e = _kanit_araligi(text, m, fwd)
    return _field("masraf_durumu", text[s:e], canon, _window(text, s, e),
                  span_start=s, span_end=e, trigger_distance=0)


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

# SAYININ ORTASINDAN BAŞLAMA YASAĞI.
#
# ## Ölçülen kusur (2026-08-11, `data/demo.db`)
#
# `odul_miktari`'nda **7 çıkarım** sayının başı kesilerek üretilmişti ve
# yedisi de güven kapısını (0,65) geçip kıyas tablosuna girmişti:
#
#     "…Özel 5000 TL'lik Harcamaya…"        -> ham '000 TL'  -> 0 TL
#     "…yapılacak 5,000 TL ve üzeri…"       -> ham  '00 TL'  -> 0 TL
#     "…toplamda 12.500 TL harcamadan…"     -> ham   '0 TL'  -> 0 TL
#
# Ekranda "en düşük ödül" sıralamasının ilk dört satırı **0 TL** görünüyordu ve
# dördü de gerçekte 1.000–12.500 TL'lik ödüllerdi. Kullanıcının bildirdiği
# "0 TL" şikâyetinin kaynağı buydu.
#
# Kök neden desen değil, ÇAĞIRAN taraftı: tetikleyicinin çevresinden 30
# karakterlik bir dilim alınıp desen O DİLİMDE aranıyordu. Dilimin sol kenarı
# sayının ortasına düşünce, desenin gördüğü ilk karakter zaten "0" oluyordu.
# Çağrı yerleri artık dilim almıyor (`search(text, pos, endpos)`), ama desenin
# kendisi de yapısal olarak korunuyor: iki kapı birden.
#
# `:` de yasaklı — "06.02.2026 00:00:00 TL" satırında saat bileşeni tutar
# sanılıyordu (tablo kolonundaki `TL` bir sonraki hücreye aitti).
_SAYI_BASI = r"(?<![\d.,:])"

_ORAN_IFADESI = (rf"binde\s*{_SAYI_BASI}\d[\d.,]*|y[üu]zde\s*{_SAYI_BASI}\d[\d.,]*|"
                 rf"%\s*{_SAYI_BASI}\d[\d.,]*|{_SAYI_BASI}\d[\d.,]*\s*%")
_PARA_IFADESI = rf"{_SAYI_BASI}\d[\d.,]*\s*(?:tl|₺|try|türk\s*liras[ıi])"

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


@dataclass
class RateRow:
    """Oran tablosunun tek satırı: bir vade ve o vadeye ait oranlar."""

    vade_ay: int
    kar_payi: float
    tahsis_ucreti: Optional[float] = None


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
        rows.append(RateRow(vade_ay=vade, kar_payi=kar, tahsis_ucreti=tahsis))
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
    r"indirim|para\s*çek|çek\s*karnesi|çek\s*tahsil",
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


# Markalı puan birimleri. Bunlar sözlükte yoksa katılım bankalarının ödül
# kampanyaları sistematik olarak kaçırılır (ölçüm: ParafPara belgesi `null`
# dönüyordu). `puan` en sona yazıldı: daha özgül alternatifler önce denenmeli.
_PUAN_TRIGGER_RE = re.compile(
    r"(chip[\s-]*para|parafpara|maximiles|worldpuan|world\s*puan|"
    r"bonus\s*puan\w*|alışveriş\s*puan\w*|alisveris\s*puan\w*|"
    r"puan\s*iade\w*|puan)", re.IGNORECASE)

# Gezinme/SSS bağlantısı kalıbı — ödül bildirimi değil.
_PUAN_KROM_RE = re.compile(
    r"nedir|nas[ıi]l\s|ne\s*i[şs]e\s*yarar|kredi\s*notu|s[ıi]k[çc]a\s*sorulan",
    re.IGNORECASE)

# Sayı bir puan/para birimine KOMŞU olmalı; birim opsiyonel değil.
#
# Sayı RAKAMLA BİTMEK zorunda (`\d[\d.,]*\d|\d`). Ölçülen yanlış pozitif:
# sözleşme metnindeki "24. Puan Uygulaması 24.1..." madde numarası. Eski
# `[\d.,]*` sonu serbest bıraktığı için "24." yutuluyor, ardından `\s*` boşluğu
# yiyor ve madde numarası 24 puanlık bir ödül sanılıyordu. Rakamla bitme şartı
# `1.500 TL` gibi binlik ayıraçlı tutarları bozmaz — orada nokta sayının içinde.
_PUAN_SAYI_RE = re.compile(
    rf"{_SAYI_BASI}(\d[\d.,]*\d|\d)\s*(?:adet\s*)?"
    r"(?:chip[\s-]*para|parafpara|maximiles|worldpuan|puan|tl|₺)",
    re.IGNORECASE)

#: Puan bağlamındaki oran deseni. `_SAYI_BASI` ile sayının ortasından
#: başlayamaz; modül düzeyinde derlenir çünkü belge başına onlarca kez koşar.
_PUAN_ORAN_RE = re.compile(
    rf"%\s*{_SAYI_BASI}(\d[\d.,]*)|{_SAYI_BASI}(\d[\d.,]*)\s*%")


def extract_alisveris_puani(text: str) -> Optional[ExtractedField]:
    """Alışveriş puanı — ORAN ya da ADET olabilir, ikisi farklı kanonik şekil.

        "%5 puan iadesi"      -> {"kind": "rate",   "value": 5.0}
        "1.000 chip-para"     -> {"kind": "points", "value": 1000.0}

    İki şekli ayrı tutmak §5.7 karşılaştırmasında elmayla armutun
    kıyaslanmasını engeller (bkz. CLAUDE.md §17 adil kıyas garantisi).

    İki ölçülmüş halüsinasyon mekanizması burada kapatıldı (19 halüsinasyonun
    2'si): (a) site kromundaki "Kredi Notu (Kredi Puanı) Nedir?" gezinme
    bağlantısı ödül sanılıyordu, (b) sayı biriminin opsiyonel olması yüzünden
    ±30 karakterdeki *herhangi* bir sayı kabul ediliyordu. Ayrıca ilk eşleşme
    yerine tüm tetikleyiciler taranıyor — kromdaki bir eşleşme gerçek ödülü
    artık gölgelemiyor.
    """
    for tm in _PUAN_TRIGGER_RE.finditer(text):
        # Site kromu / SSS bağlantısı ödül DEĞİLDİR. Ölçülen halüsinasyon:
        # "3D Secure Nedir, Ne İşe Yarar? Kredi Notu (Kredi Puanı) Nedir?" —
        # iki Türkiye Finans sayfasında `puan` sözcüğünün geçtiği TEK yer buydu
        # ve ikisinde de ilgisiz bir sayı (10.0) üretiliyordu.
        cevre = text[max(0, tm.start() - 40): min(len(text), tm.end() + 40)]
        if _PUAN_KROM_RE.search(cevre):
            continue

        # Arama METNİN KENDİSİNDE, konum sınırlarıyla — dilim ALINMAZ.
        # Gerekçe `extract_odul_miktari` içinde ve `_SAYI_BASI` yorumunda:
        # dilimin sol kenarı bir sayının ortasına düştüğünde desen sayının
        # kuyruğunu eşleştiriyor ("5000" -> "000") ve değer sessizce çöküyor.
        # Burada henüz ölçülmüş bir vaka yok; kusur LATENT ve aynı kalıptan.
        ctx_s = max(0, tm.start() - 30)
        ctx_e = min(len(text), tm.end() + 30)

        rate = _PUAN_ORAN_RE.search(text, ctx_s, ctx_e)
        if rate:
            off = rate.start(1) if rate.group(1) else rate.start(2)
            end = rate.end(1) if rate.group(1) else rate.end(2)
            val = N.parse_tr_number(text[off:end])
            if val is None:
                continue
            canon = {"kind": "rate", "value": val}
        else:
            # Sayı tetikleyiciye KOMŞU olmak zorunda. Eskiden birim grubu
            # opsiyoneldi (`(?:chip|puan)?`), yani ±30 karakterdeki herhangi bir
            # sayı kabul ediliyordu — halüsinasyonun ikinci mekanizması buydu.
            num = _PUAN_SAYI_RE.search(text, ctx_s, ctx_e)
            if not num:
                continue
            off, end = num.start(1), num.end(1)
            val = N.parse_tr_number(text[off:end])
            if val is None:
                continue
            canon = {"kind": "points", "value": val}

        s, e = off, end
        return _field("alisveris_puani", text[s:e], canon, _window(text, s, e),
                      span_start=s, span_end=e,
                      trigger_distance=abs(s - tm.start()))
    return None


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
    # Birden çok etiket bulunduysa bu bir seçim kararıdır; tek etiketli
    # vakayla aynı kesinlikte değildir.
    return _field("hedef_kitle", text[s:e], sorted(found), _window(text, s, e),
                  span_start=s, span_end=e, trigger_distance=0,
                  candidate_count=len(found))


# DİPNOT İŞARETİ. Kampanyanın GERÇEK kısıtları sayfanın altındaki yıldızlı /
# küçük punto dipnotlarda saklıdır; gövde metni pazarlama dilidir.
#
# HTML→metin dönüşümünden sonra dipnotlar şu biçime iner:
#   "...ziyaret edebilirsiniz. *Pratik Finansman Kart nakit bir finansman
#    ürünü değildir. *Kampanya katılım sağlayan ilk 2.000 kişi ile sınırlıdır."
#
# `preprocessing.clean.split_sentences` bunları AYIRAMAZ: cümle bölme
# ileri-bakışı `[A-Za-zÇĞİÖŞÜçğıöşü0-9]` bekliyor, `*` bu sınıfta değil.
# Dolayısıyla dipnot bir önceki cümleye yapışıyor ve koşul filtresi onu ya
# hiç görmüyor ya da 400 karakter sınırına takılıp atıyor. Bu yüzden dipnot
# segmentasyonu BURADA, ayrı yapılır.
#
# `•` MADDE İMİ DE DİPNOT SAYILIR. Ölçüm (2026-08-07): kontenjan kısıtı geçen
# 25 belgenin 8'inde kısıt yıldızlı dipnotta değil, sayfanın altındaki madde
# imli "Kampanya Şartları" listesindeydi:
#   "• Kampanyaya katılan ... uygun koşulları sağlayan ilk 500 kişi
#    kampanyadan faydalanabilecektir. • Kredi kartından yapılacak ..."
# Cümle bölücü `•`'yi de sınır saymadığı için bu liste TEK bir 400+ karakterlik
# "cümle" olarak geliyor ve uzunluk filtresine takılıp tamamen düşüyordu.
_DIPNOT_ISARET_RE = re.compile(
    r"(?:(?<=\s)|^)(?:\(?\*{1,3}\)?|[•‣])\s*(?=[0-9A-Za-zÇĞİÖŞÜçğıöşü])")

# Dipnotu GERÇEK KISIT yapan sinyaller.
#
# Korpus ölçümü (2026-08-07, 1759 belge): yıldızlı dipnot içeren 165 belgenin
# 53'ünde dipnot gerçek bir kısıt taşıyordu ve 35 belgede bu kısıtların en az
# biri (toplam 89 kısıt) `kampanya_kosullari`ndan tamamen düşüyordu.
# En pahalı kaçırma sınıfı KONTENJAN: "Kampanya katılım sağlayan ilk 2.000
# kişi ile sınırlandırılmıştır" — 25 belgede geçiyor ve mevcut tetikleyici
# listesinde "sınırl…" HİÇ YOKTU, yani hiçbiri yakalanmıyordu. Kontenjan,
# kullanıcı için kampanyanın en belirleyici kısıtıdır.
_KISIT_RE = re.compile(
    r"(ilk\s+[\d.]+\s*(?:bin\s*)?(?:müşteri|kişi|başvuru|adet)|"
    r"s[ıi]n[ıi]rl[ıi]d[ıi]r|s[ıi]n[ıi]rland[ıi]r[ıi]lm[ıi][şs]|ile\s+s[ıi]n[ıi]rl[ıi]|"
    r"üye\s*i[şs]\s*yer|üyeli[kğ]|üye\s*ol\w*|"
    r"bir\s*(?:kez|defa)|tek\s*sefer|kapsam\s*d[ıi][şs][ıi]|"
    r"ge[çc]erli\s*de[ğg]il|dahil\s*de[ğg]il)",
    re.IGNORECASE,
)

# KONTENJAN — gövde metnine eklenen TEK yeni tetikleyici.
#
# Neden yalnız bu: gold'un `kampanya_kosullari` listeleri bu çıkarıcının
# çıktısından ön-etiketlenip hakemlenmiş, yani eşleşme KÜME BİREBİRdir. Ölçüm
# (2026-08-07): `_KISIT_RE`'nin tamamını gövde cümlelerine tetikleyici yapmak
# alanın F1'ini 0.733 -> 0.400'e (TP 11 -> 6), mikro-F1'i 0.647 -> 0.571'e
# düşürdü — kazanılan kontenjan görünürlüğünden (4 -> 12 belge) çok daha
# pahalı. Bu yüzden gövde tarafına yalnızca dar ve tartışmasız olan kontenjan
# kalıbı eklenir; geri kalan kısıtlar SADECE dipnot bloklarında aranır.
_KONTENJAN_RE = re.compile(
    r"ilk\s+[\d.]+\s*(?:bin\s*)?(?:müşteri|kişi|başvuru|adet)", re.IGNORECASE)


def extract_dipnotlar(text: str) -> list[str]:
    """Yıldızlı dipnot bloklarını AYRI çıkarır (sıra korunur, tekrarsız).

        "... edebilirsiniz. *Kampanya ilk 2.000 kişi ile sınırlıdır."
            -> ["Kampanya ilk 2.000 kişi ile sınırlıdır"]

    Blok, işaretten sonra cümle sonuna / satır sonuna / bir sonraki dipnot
    işaretine kadar uzanır. Çok kısa (< 20 karakter) parçalar atılır: bunlar
    "*Detaylı bilgi" gibi bağlantı etiketleridir, koşul değil.

    Kendi başına da kullanılabilir olması kasıtlı — dipnotlar dashboard'da
    ayrı gösterilebilsin diye (bkz. `extract_kampanya_kosullari` bunları
    `kampanya_kosullari` alanına bağlar).
    """
    out: list[str] = []
    for m in _DIPNOT_ISARET_RE.finditer(text):
        gov = text[m.end(): m.end() + 400]
        # Cümle sonu ('.' rakam arasında değilse), satır sonu ya da bir
        # sonraki dipnot işareti. Nokta binlik ayıraç da olabildiği için
        # lookaround şart ("2.000 kişi" bölünmemeli).
        gov = re.split(r"(?<!\d)\.(?!\d)|\n|\s(?:\(?\*|[•‣])", gov, maxsplit=1)[0].strip()
        if 20 <= len(gov) <= 400 and gov not in out:
            out.append(gov)
    return out


def extract_kampanya_kosullari(text: str) -> Optional[ExtractedField]:
    """Kampanya koşulları — SKALER DEĞİL, cümle listesi.

    Koşul tetikleyicisi içeren cümleler toplanır. Eşleşme ölçütü diğer
    alanlardan farklıdır (küme-F1 / token-Jaccard); bu yüzden eval'de ayrı
    bölümde raporlanır.

    Gövde cümlelerine ek olarak **dipnot blokları** (`extract_dipnotlar`) da
    taranır: katılım bankası kampanyalarında kontenjan, üyelik ve kanal şartı
    gövdede değil yıldızlı dipnotta yazılıdır (ölçüm için bkz. `_KISIT_RE`).
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

    # GENEL YASAL İHTAR — koşul DEĞİLDİR. Desen `ihtar.py`de tek kez tanımlı;
    # anotasyon tarafındaki `kosul-ihtar` kuralı da oradan okur. Ayrıntı ve
    # ölçüm için o modülün başlığına bakın: kural yalnız anotasyonda
    # uygulanıp çıkarıcıda uygulanmadığı sürece gold ile model 20 kalibrasyon
    # belgesinin 5'inde YAPAY olarak ayrışıyordu.
    def uygun(s: str, tetik: re.Pattern) -> bool:
        return (bool(tetik.search(s)) and not boilerplate.search(s)
                and not ihtar_mi(s) and 20 <= len(s) <= 400)

    sentences = split_sentences(text)
    picked = [s.strip() for s in sentences
              if uygun(s.strip(), triggers) or uygun(s.strip(), _KONTENJAN_RE)]

    # DİPNOTLAR. Gövde cümleleriyle AYNI kovaya eklenir ama ölçütü daha dardır:
    # yalnız gerçek kısıt taşıyanlar (`_KISIT_RE`) girer. Dipnotların çoğu
    # sorumluluk reddi ("*Detaylı bilgi için ... sayfasını ziyaret edebilirsiniz")
    # ve bunları koşul saymak alanın kesinliğini düşürür.
    #
    # Zaten seçilmiş bir cümlenin İÇİNDE geçen dipnot tekrar eklenmez: cümle
    # bölücü dipnotu önceki cümleye yapıştırdığı için ikisi aynı bilgiyi
    # taşıyabilir ve liste mükerrer olurdu.
    for dipnot in extract_dipnotlar(text):
        if not uygun(dipnot, _KISIT_RE):
            continue
        if any(dipnot in s for s in picked):
            continue
        picked.append(dipnot)

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
    # Seçim belirsizliği sayılır. Bu alan tek bir eşleşme değil, koşul
    # ipucu taşıyan N cümlenin SEÇİMİDİR; N seçim kararı tek bir bitişik
    # eşleşmeyle aynı kesinliği taşıyamaz. Ölçüldü (2026-08-15, gold.round1):
    # kalem düzeyi kesinlik 0,556 iken skor 0,95 ilan ediliyordu.
    return _field("kampanya_kosullari", text[idx:end] if end > idx else first,
                  picked, _window(text, idx, end),
                  span_start=idx if end > idx else None,
                  span_end=end if end > idx else None,
                  trigger_distance=0,
                  candidate_count=len(picked))


# Oran tablosundan gelen ama tekil çıkarıcıya ÖNCELİK bırakan alanlar.
# Gerekçe `extract_all` içinde, uygulandığı yerde.
#
# `vade_ay` buraya 2026-08-12'de EKLENDİ — ölçüldü (gold.v2, 48 kayıt):
# tablodan gelen vade, tablonun kendi DİLİMİ olduğu için kampanyanın vadesi
# değildi ve `extract_vade`'nin doğru cevabını 0,95 güvenle eziyordu:
#
#   turkiye-finans avantaj  tablo "1-3 0,00% ..." -> 3    | extract_vade 36 ✓
#   albaraka TOGG           tablo max            -> 99   | extract_vade 48 ✓
#
# İkisinde de gold, `extract_vade`'nin değeriyle birebir uyuşuyor. Tablo
# satırındaki vade `RateRow` içinde KALIR (kâr payını vadeye bağlamak için
# gerekli), yalnız `vade_ay` ALANI olarak dışa verilmesi yedeğe düşer —
# `extract_vade` sustuğunda yine devreye girer, yani bilgi kaybı yok.
_TABLO_YEDEK_ALANLARI = frozenset({"masraf_durumu", "vade_ay"})

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
    # ORAN TABLOSU önce denenir: tablo varsa kâr payı/vade oradan gelir ve
    # tekil çıkarıcıların tablo gövdesinden yanlış değer devşirmesi engellenir
    # (tabloda onlarca sayı yan yana durur).
    tablo_yedek: dict[str, ExtractedField] = {}
    for f in extract_from_rate_table(text):
        if not f.is_present:
            continue
        if f.field_name in _TABLO_YEDEK_ALANLARI:
            tablo_yedek[f.field_name] = f
        else:
            out[f.field_name] = f

    # Oransal tahsis ücretinin TABANI belgenin finansman tutarıdır. İki alan
    # arasındaki bu bağ ancak burada — ikisi de görünürken — kurulabilir;
    # `extract_tahsis_ucreti` tek başına çağrıldığında tabanı bilmez ve
    # (doğru davranış olarak) hesap yapmaz.
    #
    # Taban MAKUL bir finansman tutarı olmak zorunda. Bu koruma olmadan ücret
    # tarifesi PDF'lerinde `extract_tutar`'ın yakaladığı çöp değerler
    # (0,27 TL / 1,04 TL / 2 TL) tabana geçiyor ve **0 TL tahsis ücreti**
    # üretiyordu — yani "ücretsiz" gibi görünen uydurma bir değer. Üç belgede
    # ölçüldü; makullük bandı (`confidence.PLAUSIBLE_RANGES`) üçünü de eler.
    tutar_alani = extract_tutar(text)
    taban = None
    if tutar_alani is not None and isinstance(tutar_alani.canonical_value, dict):
        aday = tutar_alani.canonical_value.get("value")
        alt, ust = C.PLAUSIBLE_RANGES["finansman_tutari"]
        if isinstance(aday, (int, float)) and alt <= aday <= ust:
            taban = float(aday)

    for fn in _EXTRACTORS:
        f = extract_tahsis_ucreti(text, taban) if fn is extract_tahsis_ucreti else fn(text)
        if f and f.is_present and f.field_name not in out:
            out[f.field_name] = f

    # Tablodan gelen YEDEK alanlar en sonda: tekil çıkarıcı sustuysa devreye
    # girerler. Ters sıra bilgi KAYBETTİRİRDİ — `extract_masraf` bu belgelerin
    # çoğunda TL tutarını da biliyor (`{"has_fee": true, "amount": 60}`),
    # tablodan gelen yedek ise yalnız "ücret var" diyebiliyor. Ölçüldü
    # (`data/demo.db`, 2026-08-09): 19 oran-tablolu belgenin 11'inde tekil
    # çıkarıcının değeri daha zengin, 8'inde hiç değer yok — yedek tam o
    # 8 belgede kazandırıyor.
    for ad, f in tablo_yedek.items():
        if ad not in out:
            out[ad] = f

    # KABUK SÜZGECİ — kılavuz §4.13/8'in kod karşılığı. Tek noktada, çünkü
    # kural 12 alanın hepsi için aynıdır ve test edilecek tek bir sınır olmalı.
    # Değeri komşu kampanya listesinden devşiren alan bu belgeye ait değildir
    # (`src/extraction/rules/kabuk.py` — kuyruk kümesi tanımı).
    sinir = kabuk_baslangici(text)
    if sinir is not None:
        out = {ad: f for ad, f in out.items()
               if not (isinstance(f.span_start, int) and f.span_start >= sinir)}
    return list(out.values())
