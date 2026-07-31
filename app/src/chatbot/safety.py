"""Katılım bankacılığına özgü güvenlik katmanı — 5 kapı (safety gates).

İlgili: ../../docs/katilim-bankaciligi-guvenligi.md
        ../../concepts/katilim-bankaciligi.md, CLAUDE.md §3, §12, §19

Katılım bankacılığı **faizsizdir**; getiri kâr payı (murabaha kâr marjı /
kâr-zarar paylaşımı) olarak adlandırılır. Bu yüzden terminoloji burada bir
biçim tercihi değil, ilke meselesidir. Bu modül chatbot'un girdi ve çıktısını
beş kapıdan geçirir:

  1. `terminoloji`      — girdide "faiz" KABUL edilir, çıktıda ASLA üretilmez.
  2. `fikhi_hukum`      — helal/caiz sorularına hüküm verilmez; TKBB Danışma
                          Kurulu'na ve bankanın danışma komitesine yönlendirilir.
  3. `yatirim_tavsiyesi`— karşılaştırma yapılır, "şu bankayı seç" denmez.
  4. `garanti_imasi`    — kâr payı oranı beklenen/gerçekleşmiş orandır; taahhüt
                          edilmiş getiri değildir (katılma hesabı zarara da ortaktır).
  5. `cekimserlik`      — kaynak yoksa yanıt yok; kapsam dışıysa dürüstçe reddet.

Tasarım kısıtları:
- Saf stdlib. LLM olmadan çalışır, ağ çağrısı yok.
- Eşleşme her zaman `tr_fold` / `tr_fold_ascii` üzerinden (bkz.
  preprocessing/clean.py). `str.lower()` Türkçe için hatalıdır ve bu projede
  daha önce 'ÜCRETSİZ'.lower() yüzünden işaret ters dönmüştü.
- Eşleşme her zaman SÖZCÜK SINIRLI. Alt-dize eşleşmesi yasak: 'ev' anahtarı
  'devam'/'seviye' içinde eşleşip korpusun %48'ini bozmuştu
  (bkz. extraction/rules/synonyms.keyword_pattern).
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from dataclasses import field as dc_field
from typing import Iterable, Optional

from ..extraction.rules.synonyms import (
    FOLDED_FIELD_TRIGGERS,
    FOLDED_TYPE_HINTS,
    matches,
)
from ..preprocessing.clean import tr_fold, tr_fold_ascii, tr_upper

logger = logging.getLogger(__name__)

# --- kapı kimlikleri (değerlendirme setiyle aynı dize) -----------------------
GATE_TERMINOLOGY = "terminoloji"
GATE_RULING = "fikhi_hukum"
GATE_ADVICE = "yatirim_tavsiyesi"
GATE_GUARANTEE = "garanti_imasi"
GATE_ABSTENTION = "cekimserlik"

ALL_GATES = (GATE_TERMINOLOGY, GATE_RULING, GATE_ADVICE, GATE_GUARANTEE,
             GATE_ABSTENTION)

_F = tr_fold_ascii


def _stem_re(stem: str) -> re.Pattern[str]:
    """Sol sınırlı kök deseni — Türkçe sondan eklemeli olduğu için ek serbest.

    `synonyms.keyword_pattern()` 4 karakter ve altındaki anahtarları İKİ
    TARAFTAN sınırlar ('ev' -> 'devam' faciasını engellemek için). Fıkhî ve
    finansal köklerde ('caiz', 'oner', 'faiz') ek almaya izin vermek
    zorunludur ve bu köklerin Türkçede masum bir eş-öneki yoktur; bu yüzden
    burada sol sınır yeterli. Alt-dize eşleşmesi hâlâ YOK: `\\b` zorunlu.
    """
    return re.compile(rf"\b{re.escape(stem)}")


def _any_stem(folded: str, stems: Iterable[str]) -> Optional[str]:
    """İlk eşleşen kökü döndürür (yoksa None)."""
    for s in stems:
        if _stem_re(s).search(folded):
            return s
    return None


def _any_keyword(folded: str, keywords: Iterable[str]) -> Optional[str]:
    """synonyms.matches() ile sözcük sınırlı ilk eşleşmeyi döndürür."""
    for kw in keywords:
        if matches(kw, folded):
            return kw
    return None


# ===========================================================================
# KAPI 1 — TERMİNOLOJİ
# ===========================================================================
#
# Çıktıda yasak kökler. Detection `tr_fold` (küçük harf, diakritik KORUNUR)
# üzerinde yapılır: tr_fold 1:1 uzunluk koruyan bir dönüşümdür, bu yüzden
# bulunan konumlar ORİJİNAL metne birebir uyar ve yerine yazma güvenlidir.
_FORBIDDEN_STEMS: tuple[str, ...] = ("faiz", "interest")

# "faizsiz" / "faizsizdir" / "faizsizlik" DOĞRU terimlerdir — katılım
# bankacılığının tanımı. Yasak listesinden muaf tutulmalı; aksi halde kendi
# doğru cümlemizi sansürlerdik.
_ALLOWED_FORBIDDEN_PREFIXES: tuple[str, ...] = ("faizsiz",)

# Çekim ekli biçimler için doğru karşılıklar. Listede olmayan biçim için
# varsayılan kullanılır.
_TERM_REPLACEMENTS: dict[str, str] = {
    "faiz": "kâr payı",
    "faizi": "kâr payı",
    "faizin": "kâr payının",
    "faizini": "kâr payını",
    "faize": "kâr payına",
    "faizden": "kâr payından",
    "faizle": "kâr payıyla",
    "faizli": "kâr paylı",
    "faizler": "kâr payları",
    "faizleri": "kâr payları",
    "faizlerin": "kâr paylarının",
    "interest": "kâr payı",
}
_DEFAULT_REPLACEMENT = "kâr payı"

# KARŞITLIK BAĞLAMI. Gerçek korpusta ölçüldü: bankaların kendi eğitim
# sayfaları iki kavramı KARŞILAŞTIRIYOR —
#     "Kâr Payı ile Faiz Arasındaki Farklar"
# Böyle bir cümlede terimi körlemesine "kâr payı" yapmak anlamı yok eder
# ("Kâr Payı ile Kâr Payı Arasındaki Farklar"). Karşıtlık işaretçisi varsa
# nötr bir karşılık kullanılır: anlam korunur, yasak terim yine üretilmez.
_CONTRAST_RE = re.compile(
    r"arasindaki fark|farki nedir|fark nedir|aksine|yerine|kiyasla|"
    r"karsin|oysa|degildir|degil mi|farkli olarak|ayrimi")
_CONTRAST_REPLACEMENTS: dict[str, str] = {
    "faiz": "konvansiyonel getiri",
    "faizi": "konvansiyonel getiriyi",
    "faizin": "konvansiyonel getirinin",
    "faizini": "konvansiyonel getirisini",
    "faize": "konvansiyonel getiriye",
    "faizden": "konvansiyonel getiriden",
    "faizle": "konvansiyonel getiriyle",
    "faizli": "konvansiyonel",
    "faizler": "konvansiyonel getiriler",
    "faizleri": "konvansiyonel getiriler",
    "faizlerin": "konvansiyonel getirilerin",
    "interest": "konvansiyonel getiri",
}
_CONTRAST_DEFAULT = "konvansiyonel getiri"

# Yalnızca UYARI üretilen "yumuşak" terimler. Yerine yazılmaz: 'kredi kartı'
# katılım bankalarının da kullandığı gerçek ürün adıdır, körlemesine
# 'finansman kartı' yapmak veriyi bozar (bkz. docs/…-guvenligi.md §Eksikler).
_SOFT_STEMS: dict[str, str] = {"kredi": "finansman", "mevduat": "katılma hesabı"}
_SOFT_EXCEPTION_RE = re.compile(r"\bkredi\s+kart")

_FORBIDDEN_RE = re.compile(
    "|".join(rf"\b{re.escape(s)}\w*" for s in _FORBIDDEN_STEMS))


def _is_allowed_form(folded_token: str) -> bool:
    return any(folded_token.startswith(p) for p in _ALLOWED_FORBIDDEN_PREFIXES)


def _match_case(original: str, replacement: str) -> str:
    """Orijinal parçanın harf durumunu (case) yerine yazılan metne taşır."""
    if original.isupper() and len(original) > 1:
        return tr_upper(replacement)
    if original[:1] == tr_upper(original[:1]) and original[:1] != original[:1].lower():
        return tr_upper(replacement[:1]) + replacement[1:]
    return replacement


def mentions_forbidden_term(text: str) -> Optional[str]:
    """Metinde yasak (konvansiyonel faiz) terimi var mı? Varsa katlanmış biçimi.

    'faizsiz' ailesi muaftır.

    >>> mentions_forbidden_term("Katılım bankacılığı faizsizdir.") is None
    True
    >>> mentions_forbidden_term("FAİZ ORANI nedir?")
    'faiz'
    """
    folded = tr_fold(text or "")
    for m in _FORBIDDEN_RE.finditer(folded):
        if not _is_allowed_form(m.group(0)):
            return m.group(0)
    return None


def sanitize_output(text: str) -> tuple[str, list[dict]]:
    """Çıktı son kontrolü (post-filter): yasak terimi doğrusuyla değiştirir.

    Neden yeniden yazma (bayraklamak yerine): jüriye giden tek yüzey yanıt
    metnidir; orada "faiz" görünmesi doğrudan itibar hatasıdır. Yeniden yazma
    kaynak izlenebilirliğini bozmaz çünkü ham pasajlar `ChatAnswer.sources`
    içinde DEĞİŞTİRİLMEDEN kalır; ne değiştirildiği de rapora ve log'a yazılır.

    Dönüş: (temizlenmiş metin, ihlal kayıtları).
    """
    if not text:
        return "", []
    folded = tr_fold(text)
    if len(folded) != len(text):
        # tr_fold normalde 1:1'dir. Değilse konumlar kayar; sessizce yanlış
        # metin üretmek yerine yalnızca bayraklarız (dürüst başarısızlık).
        term = mentions_forbidden_term(text)
        if term:
            logger.warning("cikti korumasi: konum hizalamasi bozuk, yalnizca "
                           "bayraklandi (terim=%s)", term)
            return text, [{"term": term, "replacement": None,
                           "action": "bayraklandi"}]
        return text, []

    # Karşıtlık kararı metnin TAMAMI için bir kez verilir: karşılaştırma yapan
    # bir pasajın bazı cümlelerinde işaretçi bulunmayabilir.
    contrastive = _CONTRAST_RE.search(_F(text)) is not None
    table = _CONTRAST_REPLACEMENTS if contrastive else _TERM_REPLACEMENTS
    default = _CONTRAST_DEFAULT if contrastive else _DEFAULT_REPLACEMENT

    violations: list[dict] = []
    out: list[str] = []
    cursor = 0
    for m in _FORBIDDEN_RE.finditer(folded):
        token = m.group(0)
        if _is_allowed_form(token):
            continue
        repl = table.get(token, default)
        original = text[m.start():m.end()]
        out.append(text[cursor:m.start()])
        out.append(_match_case(original, repl))
        cursor = m.end()
        violations.append({"term": token, "replacement": repl,
                           "action": "yeniden_yazildi",
                           "karsitlik_baglami": contrastive,
                           "context": text[max(0, m.start() - 30):m.end() + 30]})
    out.append(text[cursor:])
    clean = "".join(out)
    if violations:
        logger.warning("cikti korumasi: %d yasak terim yakalandi ve duzeltildi: %s",
                       len(violations), [v["term"] for v in violations])
    return clean, violations


def soft_term_warnings(text: str) -> list[dict]:
    """Yumuşak terimler (kredi/mevduat) için uyarı üretir — yeniden yazmaz."""
    folded = tr_fold(text or "")
    out: list[dict] = []
    for stem, better in _SOFT_STEMS.items():
        m = _stem_re(stem).search(folded)
        if not m:
            continue
        if stem == "kredi" and _SOFT_EXCEPTION_RE.search(folded):
            continue  # 'kredi kartı' gerçek ürün adı
        out.append({"term": stem, "onerilen": better, "action": "uyari"})
    return out


# Kullanıcı konvansiyonel terim kullandığında yanıtın başına eklenen düzeltme.
# DİKKAT: bu metin bilinçli olarak "faiz" kelimesini İÇERMEZ (yalnızca
# "faizsizdir"). Böylece "çıktıda yasak terim yok" değişmezi istisnasız kalır.
_TERMINOLOGY_NOTICE = (
    "Not: Katılım bankacılığı faizsizdir; konvansiyonel bankacılıktaki oranın "
    "karşılığı burada **kâr payı oranı**dır ve kâr-zarar paylaşımına dayanır. "
    "Sorunuzu kâr payı oranı olarak yanıtlıyorum."
)

# Kullanıcının sorusunda konvansiyonel terim arandığında hangi alana eşlenir.
INTEREST_FIELD_HINT = "kar_payi_orani"


def mentions_interest_term(question: str) -> bool:
    """Kullanıcı 'faiz' / 'interest' terimini mi kullandı? ('faizsiz' hariç)

    Girdide bu terim REDDEDİLMEZ — kullanıcı terminolojiyi bilmiyor olabilir.
    Yalnızca nazik düzeltme + doğru alana yönlendirme tetikler.
    """
    return mentions_forbidden_term(question) is not None


# ===========================================================================
# KAPI 2 — FIKHÎ HÜKÜM REDDİ
# ===========================================================================
#
# Güçlü kökler: tek başına hüküm talebi anlamı taşır.
_RULING_STRONG_STEMS: tuple[str, ...] = (
    "caiz", "haram", "mekruh", "fetva", "gunah", "fikhi", "fikih",
    "seri hukum", "ser'i hukum", "dini hukum", "dinen caiz", "dinen uygun",
    "dinen sakinca", "islami hukum", "muftu", "din isleri",
)

# Zayıf kökler: bağlama göre masum olabilir ('helal gıda kampanyası').
# Bu yüzden yakınlık (proximity) şartı var: kök ile soru edatı arasında en
# çok 18 karakter. 'Bu ürün helal mi?' yakalanır; 'Helal gıda alışverişinde
# puan veren kampanya var mı?' yakalanmaz — aşırı reddi böyle ölçtük.
_RULING_WEAK_STEMS: tuple[str, ...] = ("helal", "dinen", "dini", "islami",
                                       "islam'a", "islama", "sirket ortakligi")
_QUESTION_PARTICLE = r"(?:mi|midir|mu|mudur|degil mi|uygun mu|sakincali)"
_RULING_WEAK_RE = re.compile(
    rf"\b(?:{'|'.join(re.escape(s) for s in _RULING_WEAK_STEMS)})"
    rf"[^.?!]{{0,18}}?\b{_QUESTION_PARTICLE}\b")

_RULING_REPLY = (
    "Bu bir **fıkhî hüküm** sorusudur ve bu sistem hüküm vermez — ne olumlu "
    "ne olumsuz.\n\n"
    "Bağlayıcı görüş için yetkili merciler:\n"
    "- **TKBB (Türkiye Katılım Bankaları Birliği) Danışma Kurulu** — sektör "
    "genelinde bağlayıcı standart kararları yayımlar.\n"
    "- **İlgili bankanın kendi danışma komitesi** — o bankanın ürününe özgü "
    "görüşü verir.\n\n"
    "Ben yalnızca olgusal bilgi sunabilirim: kâr payı oranı, vade, tutar, "
    "taksit, tahsis ücreti ve masraf durumu."
)


def asks_for_ruling(question: str) -> bool:
    """Soru fıkhî hüküm (helal/caiz/haram) talep ediyor mu?

    >>> asks_for_ruling("Bu ürün caiz mi?")
    True
    >>> asks_for_ruling("Helal gıda alışverişinde puan veren kampanya var mı?")
    False
    """
    folded = _F(question or "")
    if _any_stem(folded, _RULING_STRONG_STEMS):
        return True
    return _RULING_WEAK_RE.search(folded) is not None


# ===========================================================================
# KAPI 3 — YATIRIM TAVSİYESİ REDDİ
# ===========================================================================
#
# Karşılaştırma ≠ tavsiye. "Hangi bankada en düşük kâr payı var?" olgusal bir
# sıralama sorusudur ve YANITLANIR. "Hangisini seçmeliyim?" kişisel tavsiye
# talebidir: olgu tablosu verilir, seçim yapılmaz.
_ADVICE_STEMS: tuple[str, ...] = (
    "tavsiye", "oner", "secmeli", "secelim", "sececegim", "sectiginizde",
    "yatirayim", "yatirmali", "yapmali miyim", "ne yapmaliyim",
    "tercih etmeli", "tercih etsem", "alayim", "gireyim", "kullanayim",
    "daha iyi", "en iyisi", "benim icin en", "sence", "hangisi karli",
    "kazandirir mi", "portfoy",
)
_ADVICE_DISCLAIMER = (
    "_Not: Bu bir **yatırım tavsiyesi değildir**. Sistem yalnızca "
    "karşılaştırmalı olguları sunar, banka tercihi yapmaz; karar ve sorumluluk "
    "size aittir._"
)
_ADVICE_FRAME = (
    "Tavsiye vermiyorum; bunun yerine karşılaştırmalı olguları sunuyorum."
)


def asks_for_advice(question: str) -> bool:
    """Soru kişisel yatırım tavsiyesi mi istiyor?

    >>> asks_for_advice("Hangi bankaya para yatırayım?")
    True
    >>> asks_for_advice("Hangi bankada en düşük kâr payı oranı var?")
    False
    """
    return _any_stem(_F(question or ""), _ADVICE_STEMS) is not None


# ===========================================================================
# KAPI 4 — GARANTİ İMASI KORUMASI
# ===========================================================================
#
# Katılma hesapları kâr VE zarara ortak olur; kâr payı oranı taahhüt değildir.
# Geçmiş/beklenen oranı garanti gibi sunmak İslami finansın ilke düzeyinde
# ihlalidir (garar / belirsizlik yasağı).
_GUARANTEE_STEMS: tuple[str, ...] = (
    "garanti", "kesin getiri", "kesin kazanc", "kesin kar", "sabit getiri",
    "sabit kar", "taahhut", "ne kadar kazanirim", "ne kazanirim",
    "kazancim ne", "zarar eder miyim", "riskli mi", "kesinlikle kazan",
)
_GUARANTEE_DISCLAIMER = (
    "_Not: Kâr payı oranı **beklenen / gerçekleşmiş** bir orandır, taahhüt "
    "edilmiş getiri değildir. Katılma hesapları kâr **ve zarara** ortak olur; "
    "oran garanti anlamı taşımaz (CLAUDE.md §12)._"
)
_GUARANTEE_CORRECTION = (
    "Önce ilkeyi netleştirelim: katılım bankacılığında **getiri garanti "
    "edilmez**. Katılma hesabı kâr-zarar paylaşımına dayanır; ilan edilen kâr "
    "payı oranı beklenen ya da geçmişte gerçekleşmiş orandır, sabit bir "
    "taahhüt değildir."
)
_RATE_RE = re.compile(r"%\s*\d")


def implies_guarantee(question: str) -> bool:
    """Soru garantili/sabit getiri imasında mı?"""
    return _any_stem(_F(question or ""), _GUARANTEE_STEMS) is not None


def contains_rate(text: str) -> bool:
    """Metin bir yüzde oran içeriyor mu (garanti uyarısı gerekir mi)?"""
    return _RATE_RE.search(text or "") is not None


# ===========================================================================
# KAPI 5 — ZORUNLU ATIF / ÇEKİMSERLİK
# ===========================================================================
#
# Kapsam sözlüğü mevcut altyapıdan türetilir (paralel sözlük kurmuyoruz):
# alan tetikleyicileri + kampanya türü ipuçları. 3 karakter ve altındaki
# gürültülü anahtarlar ('ay', 'ev') dışarıda bırakılır: kapsam kararı için
# fazla geniştirler.
def _build_scope_lexicon() -> tuple[str, ...]:
    terms: set[str] = set()
    for vals in FOLDED_FIELD_TRIGGERS.values():
        terms.update(v for v in vals if len(v) > 3)
    for vals in FOLDED_TYPE_HINTS.values():
        terms.update(v for v in vals if len(v) > 3)
    terms.update((
        "banka", "bankacilik", "katilim", "kampanya", "kar payi", "kar-zarar",
        "murabaha", "icara", "mudarebe", "musareke", "sukuk", "karz",
        "katilma hesabi", "cari hesap", "hesap", "sube", "basvuru", "musteri",
        "faiz", "faizsiz", "islami finans", "altin", "doviz", "gumus",
        "sigorta", "emeklilik", "bes", "tkbb", "bddk", "vade farki",
        "odeme", "iade", "indirim", "cashback", "nakit iade",
    ))
    terms.update(BANK_NAME_TO_SLUG.keys())
    return tuple(sorted(terms, key=len, reverse=True))


# Banka adı → slug. config/banks.yaml ile aynı slug'lar (CLAUDE.md §13).
# Burada statik tutuluyor: güvenlik katmanı dosya I/O yapmaz, import anında
# YAML okumak chatbot'u konfigürasyona bağımlı kılardı.
BANK_NAME_TO_SLUG: dict[str, str] = {
    "kuveyt turk": "kuveyt-turk",
    "kuveytturk": "kuveyt-turk",
    "albaraka": "albaraka",
    "albaraka turk": "albaraka",
    "turkiye finans": "turkiye-finans",
    "turkiyefinans": "turkiye-finans",
    "ziraat katilim": "ziraat-katilim",
    "ziraat": "ziraat-katilim",
    "vakif katilim": "vakif-katilim",
    "turkiye emlak katilim": "turkiye-emlak-katilim",
    "emlak katilim": "turkiye-emlak-katilim",
    "t.o.m. katilim": "tom-katilim",
    "tom katilim": "tom-katilim",
    "tom bank": "tom-katilim",
    "hayat finans": "hayat-finans",
    "dunya katilim": "dunya-katilim",
    "adil katilim": "adil-katilim",
}

_SCOPE_LEXICON: tuple[str, ...] = _build_scope_lexicon()

_OUT_OF_SCOPE_REPLY = (
    "Bu soru elimdeki verinin kapsamı dışında — **bilmiyorum**, tahmin "
    "etmiyorum.\n\n"
    "Yanıtlayabildiğim alan: katılım bankalarının kampanya metinlerinden "
    "çıkarılmış kâr payı oranı, vade, finansman tutarı, taksit sayısı, "
    "tahsis ücreti ve masraf durumu bilgileri."
)
_NO_SOURCE_REPLY = (
    "Bu bilgi verimde **yok**. Uydurmak yerine bilmediğimi belirtiyorum; "
    "kaynağa dayanmayan bir değer üretmem.\n\n"
    "Sorunuzu farklı bir banka, ürün ya da alan için tekrar sorabilirsiniz."
)


def is_in_scope(question: str) -> bool:
    """Soru katılım bankacılığı kampanya verisiyle ilgili mi?

    >>> is_in_scope("Hangi bankada en düşük kâr payı oranı var?")
    True
    >>> is_in_scope("Bugün hava nasıl olacak?")
    False
    """
    return _any_keyword(_F(question or ""), _SCOPE_LEXICON) is not None


def detect_banks(question: str) -> list[str]:
    """Soruda geçen TÜM bankaları slug olarak döndürür.

    Çoğul olması şart: "Hangisini seçmeliyim, Kuveyt Türk mü Albaraka mı?"
    sorusunda tek bankaya filtrelemek karşılaştırmayı yok eder. Uzun ad önce
    denenir ki 'türkiye emlak katılım' ile 'türkiye finans' karışmasın; aynı
    bankanın iki takma adı ('ziraat' / 'ziraat katılım') set ile tekilleşir.
    """
    folded = _F(question or "")
    found: list[str] = []
    for name in sorted(BANK_NAME_TO_SLUG, key=len, reverse=True):
        if matches(name, folded):
            slug = BANK_NAME_TO_SLUG[name]
            if slug not in found:
                found.append(slug)
    return found


def detect_bank(question: str) -> Optional[str]:
    """İlk eşleşen bankanın slug'ı (yoksa None) — tek-banka soruları için."""
    banks = detect_banks(question)
    return banks[0] if banks else None


# ===========================================================================
# GİRDİ TARAMASI + ÇIKTI KORUMASI
# ===========================================================================


@dataclass
class InputScreening:
    """Girdi taramasının sonucu."""

    question: str
    blocked: bool = False                 # hazır politika yanıtıyla durduruldu mu
    reply: Optional[str] = None           # blocked ise verilecek yanıt
    gates: list[str] = dc_field(default_factory=list)
    notices: list[str] = dc_field(default_factory=list)   # yanıt başına eklenir
    disclaimers: list[str] = dc_field(default_factory=list)  # yanıt sonuna
    field_hint: Optional[str] = None      # terminoloji düzeltmesinden gelen alan
    advice_intent: bool = False
    guarantee_intent: bool = False
    out_of_scope: bool = False


@dataclass
class SafetyReport:
    """Bir yanıtın güvenlik denetim kaydı (açıklanabilirlik + CI kapısı)."""

    gates: list[str] = dc_field(default_factory=list)
    violations: list[dict] = dc_field(default_factory=list)  # yakalanan yasak terim
    warnings: list[dict] = dc_field(default_factory=list)    # yumuşak terim uyarıları
    notices: list[str] = dc_field(default_factory=list)
    abstained: bool = False
    blocked_gate: Optional[str] = None

    def as_dict(self) -> dict:
        return {
            "gates": list(self.gates),
            "violations": list(self.violations),
            "warnings": list(self.warnings),
            "notices": list(self.notices),
            "abstained": self.abstained,
            "blocked_gate": self.blocked_gate,
        }


def screen_input(question: str) -> InputScreening:
    """Soruyu 5 kapıdan geçirir; gerekiyorsa hazır politika yanıtı üretir.

    Sıra önemlidir: fıkhî hüküm talebi kapsam kontrolünden ÖNCE gelir, çünkü
    "Bu helal mi?" sorusu kapsam sözlüğünü tetiklemeyebilir ama yine de doğru
    davranış yönlendirme yapmaktır — sessizce "bilmiyorum" demek değil.
    """
    scr = InputScreening(question=question)

    # KAPI 2 — fıkhî hüküm: en yüksek öncelik, hüküm verilmez.
    if asks_for_ruling(question):
        scr.blocked = True
        scr.reply = _RULING_REPLY
        scr.gates.append(GATE_RULING)
        return scr

    # KAPI 1 — terminoloji (girdi tarafı): kabul et, nazikçe düzelt.
    if mentions_interest_term(question):
        scr.gates.append(GATE_TERMINOLOGY)
        scr.notices.append(_TERMINOLOGY_NOTICE)
        scr.field_hint = INTEREST_FIELD_HINT

    # KAPI 3 — yatırım tavsiyesi: reddetme değil, çerçeveleme.
    if asks_for_advice(question):
        scr.advice_intent = True
        scr.gates.append(GATE_ADVICE)
        scr.notices.append(_ADVICE_FRAME)
        scr.disclaimers.append(_ADVICE_DISCLAIMER)

    # KAPI 4 — garanti iması: ilkeyi önce netleştir.
    if implies_guarantee(question):
        scr.guarantee_intent = True
        scr.gates.append(GATE_GUARANTEE)
        scr.notices.append(_GUARANTEE_CORRECTION)
        scr.disclaimers.append(_GUARANTEE_DISCLAIMER)

    # KAPI 5 — kapsam: hiçbir alan sinyali yoksa dürüstçe reddet.
    if not is_in_scope(question):
        scr.blocked = True
        scr.out_of_scope = True
        scr.reply = _OUT_OF_SCOPE_REPLY
        scr.gates.append(GATE_ABSTENTION)

    return scr


def guard_output(body: str, scr: InputScreening, *, has_sources: bool,
                 has_rate: bool = False) -> tuple[str, SafetyReport]:
    """Yanıtı son kontrolden geçirir ve nihai metni kurar.

    Adımlar:
      1. Kaynak yoksa (KAPI 5) gövde dürüst çekimserlik metniyle değiştirilir.
      2. Gövde sanitize edilir (KAPI 1 post-filter) — yasak terim yeniden yazılır.
      3. Düzeltme notları başa, feragatnameler sona eklenir.
      4. Oran içeren yanıtlara garanti ayrımı notu eklenir (KAPI 4).

    Notlar ve feragatnameler sanitize'dan SONRA eklenir; bunlar denetlenmiş
    sabit şablonlardır ve tasarımı gereği yasak terim içermezler.
    """
    report = SafetyReport(gates=list(scr.gates), notices=list(scr.notices))

    if scr.blocked:
        report.blocked_gate = scr.gates[-1] if scr.gates else None
        report.abstained = scr.out_of_scope
        body = scr.reply or body
    elif not has_sources:
        body = _NO_SOURCE_REPLY
        report.abstained = True
        if GATE_ABSTENTION not in report.gates:
            report.gates.append(GATE_ABSTENTION)

    clean, violations = sanitize_output(body)
    report.violations = violations
    report.warnings = soft_term_warnings(body)

    disclaimers = list(scr.disclaimers)
    if (has_rate or contains_rate(clean)) and not report.abstained \
            and _GUARANTEE_DISCLAIMER not in disclaimers:
        disclaimers.append(_GUARANTEE_DISCLAIMER)
        if GATE_GUARANTEE not in report.gates:
            report.gates.append(GATE_GUARANTEE)

    parts = [n for n in scr.notices]
    parts.append(clean)
    parts.extend(disclaimers)
    return "\n\n".join(p for p in parts if p), report
