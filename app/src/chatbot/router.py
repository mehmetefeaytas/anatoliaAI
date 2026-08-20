"""Soru router'ı — sayısal/karşılaştırmalı mı, açıklama mı?

İlgili: ../../decisions/hibrit-chatbot-text-to-sql-rag.md
        CLAUDE.md §5

Sayısal/karşılaştırmalı sorular → yapısal sorgu (text-to-SQL benzeri).
Koşul/açıklama soruları → RAG. Router anahtar-kelime + alan eşleme ile çalışır;
LLM gerektirmez (offline). Belirsizse 'rag'a düşer (güvenli varsayılan).

## Sohbet bağlamı (takip soruları)

Router eskiden YALNIZ o anki soruya bakıyordu. Ölçülen sonuç: iki turluk en
doğal akış çalışmıyordu.

    — "Hangi bankada en düşük kâr payı oranı var?"  → Kuveyt Türk
    — "Peki vade?"                                  → alan=vade_ay, niyet YOK,
      süzgeç YOK → yapısal sorgu kurulamıyor, soru RAG'e düşüyor ve anahtar
      kelimesi iki sözcükten ibaret olduğu için alakasız bir belge dönüyor.

`route()` artık isteğe bağlı bir `ChatContext` alır ve sorunun EKSİK
boyutlarını (alan / niyet / süzgeç) önceki turdan devralır. Devralma
görünürdür: `Route.inherited` neyin nereden geldiğini Türkçe etiketleriyle
taşır ve arayüz bunu rozet olarak basar.

### Devralma YALNIZ eksik soruya yardım eder

Bir cümlelik kural: **soru kendi başına yapısal sorgu kurabiliyorsa hiçbir şey
devralmaz.** Ölçüldü (tarayıcı, çok turlu oturum) — kural bundan önce "alan +
niyet"ti ve şu cevabı üretiyordu:

    — "Yeni müşterilere verilen EV finansman tutarı ne kadar?"
    — "önceki sorudan: kampanya türü Taşıt Finansmanı / asgari vade 36 ay /
       Vakıf Katılım → Taşıt Finansmanı — finansman tutarı …"

Kullanıcı EV sordu, sistem TAŞIT cevapladı. İki ayrı sebep vardı ve ikisi de
kapatıldı: (1) yalın "ev" hiçbir tür ipucuna eşlenmiyordu, (2) niyeti olmayan
ama süzgeci olan soru "eksik" sayılıp üç ayrı turdan üç süzgeç birden
devralıyordu. Kuralların tamamı `_devral` docstring'indedir.

### Bağlam kanalı neden SERBEST METİN TAŞIMAZ

Sunucu durumsuzdur; bağlamı istemci gönderir, yani bağlam **saldırgan
denetimindeki** bir kanaldır. Bu yüzden kanalda hiç serbest metin yoktur:
taşınan her değer sonlu bir kümeden gelmek zorundadır (alan adı, niyet adı,
kampanya türü, banka slug'ı, tamsayı vade eşiği). `ChatContext.dogrula()`
kümeye uymayan her değeri sessizce atar.

Sonuç: bağlam kanalıyla ne modele talimat gömülebilir, ne de güvenlik
kapıları atlatılabilir — kapılar zaten o anki sorunun HAM metni üzerinde,
router'dan ÖNCE çalışır (bkz. bot.Chatbot.ask).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from dataclasses import field as dc_field
from typing import Any, Optional, Sequence

from ..preprocessing.clean import tr_fold_ascii
from .safety import INTEREST_FIELD_HINT, detect_banks, mentions_interest_term

# Soru içindeki ifade → alan adı
_FIELD_KEYWORDS = {
    "kar_payi_orani": ["kâr payı", "kar payı", "getiri oran", "kâr oran", "oran"],
    "vade_ay": ["vade", "ödeme süresi", "kaç ay", "kaç yıl", "ay vade"],
    "finansman_tutari": ["tutar", "limit", "ne kadar finansman", "kredi tutar"],
    "tahsis_ucreti": ["tahsis", "dosya masraf"],
    "masraf_durumu": ["masraf", "ücret", "masrafsız", "ücretsiz"],
    "taksit_sayisi": ["taksit"],
}

# Karşılaştırma/agregasyon niyeti
_SUPERLATIVE_LOW = ["en düşük", "en az", "en ucuz", "en avantajlı", "minimum"]
_SUPERLATIVE_HIGH = ["en yüksek", "en fazla", "en uzun", "en çok", "maksimum", "en büyük"]
_LIST_INTENT = ["hangi banka", "hangi bankalar", "listele", "göster", "var mı",
                "veren", "sunan", "olanlar"]

# İKİ BANKAYI KIYASLAMA NİYETİ — alan söylenmemiş olabilir.
#
# ## Ölçülen kusur (2026-08-11)
#
# "Türkiye Finans Bankası mı daha avantajlı, Albaraka Bankası mı?" sorusu
# RAG'e düşüyordu. Alan çıkarılamadığı için yapısal sorgu kurulamıyor, RAG ise
# anahtar-kelime örtüşmesiyle Findeks kredi notu ve altın hesabı belgelerini
# getiriyordu. LLM bu alakasız bağlamdan cevap üretemeyince KENDİ genel
# bilgisinden yazıyordu: *"her iki bankanın web sitelerini ziyaret edip veya
# şubelerine danışmak daha uygun olacaktır"* — oysa istenen kıyas verisi
# sistemin elindeydi ve iki banka da soruda ADIYLA geçiyordu.
#
# Aynı sorunun "daha **iyi**" ile sorulan biçimi DOĞRU çalışıyordu, çünkü
# "daha iyi" tavsiye kapısının (safety.KAPI 3) sözlüğünde var ve o kapı soruyu
# yapısal kıyasa çeviriyor. Yani mekanizma zaten kuruluydu; ona ulaşan ifade
# kümesi eksikti.
#
# Bu liste tavsiye sözlüğüne EKLENMEDİ, ayrı durur. Sebep: "karşılaştır"
# tavsiye istemez, olgu ister. Onu tavsiye kapısına koymak, nötr bir soruda
# jüriye "yatırım tavsiyesi kapısı ateşlendi" diye YANLIŞ bir kapı raporu
# gösterirdi. Kapı raporunun doğruluğu bu projenin iddiası.
_KIYAS_ISARETLERI = [
    "karşılaştır", "kıyasla", "kıyaslar", "karşılaştırma",
    "daha avantajlı", "avantajlı mı", "daha uygun", "daha ucuz",
    "daha düşük mü", "hangisi daha", "hangisi avantajlı", "farkı ne",
    "arasındaki fark", "hangisini", " vs ",
]

#: Alan söylenmeden kıyas istendiğinde kullanılacak alan.
#:
#: Kâr payı oranı seçildi: senaryonun kalbi (CLAUDE.md §5) ve kullanıcının
#: "avantajlı" derken en sık kastettiği boyut. Seçim GİZLENMEZ — cevabın
#: başlığı hangi alanın kıyaslandığını yazar ve `structured.answer` çok
#: boyutlu soruya tek boyutlu cevap verildiğini ayrıca not eder.
VARSAYILAN_KIYAS_ALANI = "kar_payi_orani"

# Kullanıcı sorusu ALL-CAPS veya diakritiksiz gelebilir ("EN DÜŞÜK KÂR PAYI",
# "en dusuk kar payi"). Eşleşme tr_fold_ascii üzerinden yapılır; anahtar
# kelimeler de modül yüklenirken aynı forma indirgenir.
_F = tr_fold_ascii
_FOLDED_FIELD_KEYWORDS = {k: [_F(v) for v in vals]
                          for k, vals in _FIELD_KEYWORDS.items()}
_FOLDED_SUP_LOW = [_F(s) for s in _SUPERLATIVE_LOW]
_FOLDED_SUP_HIGH = [_F(s) for s in _SUPERLATIVE_HIGH]
_FOLDED_LIST_INTENT = [_F(s) for s in _LIST_INTENT]
_FOLDED_KIYAS = [_F(s) for s in _KIYAS_ISARETLERI]

# --------------------------------------------------------------------------- #
# ÜSTÜNLÜK NİYETİ — "en iyi" bir YÖN değil, ÇOK BOYUTLU bir iddiadır
# --------------------------------------------------------------------------- #
#
# ## Ölçülen kusur (2026-08-20, canlı sistem, jürinin gördüğü yüzey)
#
#   "Hangi bankada en düşük konut finansmanı var"   -> structured/finansman_tutari
#   "Bana en iyi ev finansmanı veren banka hangisi" -> RAG / alan None
#   "Hangi banka en uygun konut finansmanı veriyor" -> RAG / alan None
#   "En avantajlı ev finansmanı hangi bankada"      -> structured/finansman_tutari
#
# İkinci ve üçüncüsü RAG'e düşüyordu: "en iyi"/"en uygun" ÜÇ sözlükten de
# (`_SUPERLATIVE_LOW/HIGH`, `_KIYAS_ISARETLERI`, `safety._ADVICE_STEMS`)
# eksikti. Sonuçta jüri tek bankanın üç belgesini gördü ve üç pasajın ikisi
# İHTİYAÇ finansmanıydı — oysa soru KONUT'tu.
#
# ## Neden `_SUPERLATIVE_*`'a EKLENMEDİ (ölçülmüş tuzak)
#
# "en iyi"yi `_SUPERLATIVE_LOW`'a koymak soruyu şu cevaba çeviriyor:
# `structured / finansman_tutari / lowest` -> "en düşük finansman tutarı:
# Türkiye Emlak Katılım (100 TL)". Yani ikinci hata birinci hatanın birebir
# aynısına dönüşüyor. Sebep aşağıdaki `_URUN_ADI_TUTAR_RE` bloğunda yazılı:
# "konut **finansmanı**"nda o sözcük ürün adının parçasıdır, tutar talebi
# değil.
#
# Doğru hedef `comparison.rank_advantageous_by_type()`'tır: ağırlıklı bileşik
# skor, ürün ailesi İÇİNDE, ağırlık manifestosu şeffaf. Bu liste o dala
# (`Route.ustunluk`) götürür, bir sıralama YÖNÜNE değil.
_USTUNLUK_ISARETLERI = [
    "en iyi", "en iyisi hangi", "en uygun", "en kârlı", "en karli",
    "en cazip", "en mantıklı", "en makul",
]

#: ÇIPLAK "hangisi" — tek başına da üstünlük sinyalidir ("Konut finansmanında
#: hangisi?"). `_KIYAS_ISARETLERI` yalnız "hangisi daha" / "hangisi avantajlı"
#: / "hangisini" biçimlerini tanıyordu.
#:
#: Sözcük sınırlı: alt dize olarak "hangisini" içinde de geçer ve o ifade
#: ZATEN `_KIYAS_ISARETLERI`'nde — iki sinyalin aynı soruda çakışması
#: zararsızdır, ama sınırsız desen "hangisinde/hangisiyle" gibi çekimleri de
#: sessizce yakalardı.
_CIPLAK_HANGISI_RE = re.compile(r"\bhangisi\b")

#: "konut finansmanı" / "ev kredisi" — buradaki `finansman`/`kredi` ÜRÜN
#: ADININ PARÇASIDIR, tutar talebi DEĞİLDİR.
#:
#: `_FOLDED_SUP_FIELD_KEYWORDS` bu iki sözcüğü `finansman_tutari`'na eşliyor
#: ve eşleme "Araba alımında en yüksek FİNANSMAN kimde var?" gibi sorularda
#: DOĞRU (orada sözcük tek başına duruyor, bir ürün adının içinde değil).
#: Ürün adının parçası olduğunda ise ölçülen sonuç şuydu: "en düşük konut
#: finansmanı" sorusu "en düşük finansman TUTARI" diye okunuyor ve cevap
#: 100 TL'lik bir kampanya oluyordu — kullanıcı en ucuz KONUT FİNANSMANINI
#: sormuşken.
#:
#: Eşleme bastırıldığında alan `None` kalır ve soru üstünlük dalına
#: (`Route.ustunluk`) gider: alan söylenmediği için çok boyutlu bileşik skor
#: kullanılır ve bu SÖYLENİR.
_URUN_ADI_TUTAR_RE = re.compile(
    r"\b(?:konut|mesken|ev|tasit|arac|araba|otomobil|binek|ihtiyac|isyeri|"
    r"egitim|tatil|kobi|ticari|tarim|saglik|evlilik)\s+"
    r"(?:finansman|kredi)\w*")

_FOLDED_USTUNLUK = [_F(s) for s in _USTUNLUK_ISARETLERI]

# Kampanya türü filtresi: soru içindeki ipucu → 8 sınıftan biri.
# Kullanıcı ürün adını değil GÜNLÜK KELİMEYİ kullanır: "araba alımında en
# yüksek finansman kimde" sorusu ölçüldü ve `taşıt` geçmediği için tür
# filtresi hiç kurulmuyordu.
_FOLDED_TYPE_MAP = {_F(k): v for k, v in {
    "konut": "Konut Finansmanı", "ev alım": "Konut Finansmanı",
    "mortgage": "Konut Finansmanı", "mesken": "Konut Finansmanı",
    "taşıt": "Taşıt Finansmanı", "araba": "Taşıt Finansmanı",
    "araç": "Taşıt Finansmanı", "otomobil": "Taşıt Finansmanı",
    "sıfır km": "Taşıt Finansmanı", "binek": "Taşıt Finansmanı",
    "ihtiyaç": "İhtiyaç Finansmanı", "kart": "Kart",
    "yatırım": "Yatırım Ürünü",
}.items()}

# Yalın "ev" — SÖZCÜK SINIRIYLA eşleşir, alt dize olarak DEĞİL.
#
# Ölçüldü (tarayıcı, çok turlu oturum): "Yeni müşterilere verilen EV finansman
# tutarı ne kadar?" sorusunda hiçbir tür ipucu bulunamıyordu — yukarıdaki
# sözlükte "ev alım" var ama yalın "ev" yok. Tür bulunamayınca soru kendi
# sinyalsiz sayılıyor ve önceki turun TAŞIT süzgeci yapışıyordu.
#
# Bu ipucu neden alt dize olarak eklenemez: katlanmış metinde "ev" sayısız
# sözcüğün İÇİNDE geçer — "seviye", "evrak", "devlet", "güvence". Alt dize
# eşlemesi "taşıt evrakları" sorusunu Konut Finansmanı'na yollardı. Sözcük
# sınırı bunu imkânsız kılar; çekim ekleri sayılıdır ve tek tek yazılır
# (`ev\w*` deseni yine "evrak"ı yakalardı).
_TUR_SOZCUK_DESENLERI: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\bev(?:i|im|imiz|e|in|den|ler|leri)?\b"), "Konut Finansmanı"),
    (re.compile(r"\boto\b"), "Taşıt Finansmanı"),
]

# SUPERLATİF VARSA alan bulunamadığında başvurulan gevşek eşleme.
# Sadece "en yüksek/en düşük" gibi açık bir sıralama niyeti varken devreye
# girer; niyetsiz sorular (ör. "Konut finansmanı kampanyasının koşulları
# neler?") RAG'de kalır ve davranışları değişmez.
#
# Sebebi ölçüldü: "Araba alımında en yüksek finansman kimde var?" sorusunda
# `finansman` hiçbir alan anahtarına uymuyordu, alan `None` kalıyor ve soru
# RAG'e düşüyordu. RAG de sorunun yalnız iki yaygın kelimesiyle ('alımında',
# 'yüksek') örtüşen bir SEYAHAT kampanyasını "ilgili kampanya" diye
# döndürüyordu. Açık sıralama niyeti olan bir soruyu anlamsal aramaya
# göndermek, router'ın var oluş sebebine aykırı.
_FOLDED_SUP_FIELD_KEYWORDS = {_F(k): v for k, v in {
    "finansman": "finansman_tutari",
    "kredi": "finansman_tutari",
    "puan": "alisveris_puani",
    "ödül": "odul_miktari",
    "indirim": "indirim_orani",
}.items()}


# --------------------------------------------------------------------------- #
# Bağlam kanalının izin listeleri (allowlist)
# --------------------------------------------------------------------------- #
# Aşağıdaki üç sözlük hem DOĞRULAMA kümesi hem de kullanıcıya gösterilecek
# Türkçe etiket kaynağıdır. İkisini tek yerde tutmak, "kabul edilen değer" ile
# "ekranda yazan şey" ikilisinin ayrışmasını imkânsız kılar.

#: Bağlamda taşınabilen alan adları → ekran etiketi.
FIELD_DISPLAY: dict[str, str] = {
    "kar_payi_orani": "kâr payı oranı",
    "vade_ay": "vade",
    "finansman_tutari": "finansman tutarı",
    "tahsis_ucreti": "tahsis ücreti",
    "masraf_durumu": "masraf durumu",
    "taksit_sayisi": "taksit sayısı",
    "alisveris_puani": "alışveriş puanı",
    "odul_miktari": "ödül miktarı",
    "indirim_orani": "indirim oranı",
}

#: Bağlamda taşınabilen niyetler → ekran etiketi.
INTENT_DISPLAY: dict[str, str] = {
    "lowest": "en düşük",
    "highest": "en yüksek",
    "list": "listeleme",
    "filter": "süzme",
}

#: Banka slug'ı → ekran adı. Slug kümesi `safety.BANK_NAME_TO_SLUG`
#: değerleriyle aynıdır; burada ayrıca DOĞRU YAZILMIŞ ad tutulur, çünkü
#: güvenlik katmanındaki adlar diakritiksiz (katlanmış) biçimdedir ve
#: kullanıcıya "Kuveyt Turk" diye gösterilemez.
BANK_DISPLAY: dict[str, str] = {
    "adil-katilim": "Adil Katılım",
    "albaraka": "Albaraka Türk",
    "dunya-katilim": "Dünya Katılım",
    "hayat-finans": "Hayat Finans",
    "kuveyt-turk": "Kuveyt Türk",
    "tom-katilim": "T.O.M. Katılım",
    "turkiye-emlak-katilim": "Türkiye Emlak Katılım",
    "turkiye-finans": "Türkiye Finans",
    "vakif-katilim": "Vakıf Katılım",
    "ziraat-katilim": "Ziraat Katılım",
}

#: Bağlamda taşınabilen kampanya türleri — router'ın kendi üretebildikleri.
CAMPAIGN_TYPES: frozenset[str] = frozenset(_FOLDED_TYPE_MAP.values()) | {
    tur for _desen, tur in _TUR_SOZCUK_DESENLERI}

#: Bir istekte incelenecek AZAMİ geçmiş tur sayısı. Sınır sunucudadır:
#: istemci daha uzun bir liste gönderse de hafıza penceresi büyümez.
BAGLAM_TUR_SINIRI = 6

#: Vade eşiği için makul aralık (ay). 600 ay = 50 yıl; üstü veri değil gürültü.
_VADE_MIN, _VADE_AZAMI = 1, 600

#: Bağlamdan devralınabilecek süzgeç anahtarları.
_SUZGEC_ETIKET = {
    "campaign_type": "kampanya türü",
    "vade_ay_min": "asgari vade",
    "banks": "banka",
}


@dataclass
class ChatContext:
    """Bir turun sonunda geriye kalan, DEVRALINABİLİR durum.

    Sunucu bunu üretir, istemci saklar ve bir sonraki istekte geri gönderir
    (durumsuz sunucu — bkz. modül başlığı). Alanların hepsi izin listesinden
    geçer; serbest metin taşınmaz.
    """

    field: Optional[str] = None
    intent: Optional[str] = None
    filters: dict = dc_field(default_factory=dict)
    #: Önceki turun CEVABININ öznesi (ör. "en düşük kâr payı" sorusunun
    #: kazananı). Sorunun süzgeci DEĞİLDİR; ayrı tutulur çünkü farklı bir
    #: devralma kuralına tabidir.
    subject_banks: list[str] = dc_field(default_factory=list)

    def bos(self) -> bool:
        return not (self.field or self.intent or self.filters
                    or self.subject_banks)

    def as_dict(self) -> dict:
        return {"field": self.field, "intent": self.intent,
                "filters": dict(self.filters),
                "subject_banks": list(self.subject_banks)}

    @classmethod
    def dogrula(cls, ham: Any) -> "ChatContext":
        """İstemciden gelen tek bağlam kaydını izin listesinden geçirir.

        Tanınmayan her değer SESSİZCE atılır (hata yükseltilmez): bağlam bir
        kolaylıktır, sözleşme değil. Bozuk bir kayıt yüzünden kullanıcının
        sorusunu reddetmek, saldırıyı önlemez ama demoyu kırar.
        """
        if not isinstance(ham, dict):
            return cls()
        field = ham.get("field")
        if field not in FIELD_DISPLAY:
            field = None
        intent = ham.get("intent")
        if intent not in INTENT_DISPLAY:
            intent = None
        return cls(field=field, intent=intent,
                   filters=_suzgecleri_dogrula(ham.get("filters")),
                   subject_banks=_bankalari_dogrula(ham.get("subject_banks")))


def _bankalari_dogrula(ham: Any) -> list[str]:
    if not isinstance(ham, (list, tuple)):
        return []
    out: list[str] = []
    for s in ham:
        if isinstance(s, str) and s in BANK_DISPLAY and s not in out:
            out.append(s)
    return out[:len(BANK_DISPLAY)]


def _suzgecleri_dogrula(ham: Any) -> dict:
    if not isinstance(ham, dict):
        return {}
    out: dict = {}
    ctype = ham.get("campaign_type")
    if isinstance(ctype, str) and ctype in CAMPAIGN_TYPES:
        out["campaign_type"] = ctype
    vmin = ham.get("vade_ay_min")
    # `bool` int'in alt sınıfıdır; True'nun 1 ay olarak geçmesi engellenir.
    if isinstance(vmin, int) and not isinstance(vmin, bool) \
            and _VADE_MIN <= vmin <= _VADE_AZAMI:
        out["vade_ay_min"] = vmin
    banks = _bankalari_dogrula(ham.get("banks"))
    if banks:
        out["banks"] = banks
    return out


def baglam_birlestir(kayitlar: Any,
                     sinir: int = BAGLAM_TUR_SINIRI) -> ChatContext:
    """İstemcinin gönderdiği tur listesini TEK bağlama indirger.

    Liste YENİDEN ESKİYE sıralıdır; her boyut için ilk (yani en taze) dolu
    değer kazanır. Böylece "hafıza" tek turla sınırlı kalmaz: kullanıcı üç tur
    önce kampanya türünü söyleyip aradaki turlarda başka şey sorduysa tür
    süzgeci hâlâ yaşar.

    **Özne bunun İSTİSNASIDIR ve yalnız EN SON turdan alınır.** "Peki vade?"
    sorusunun anlamı "az önce söylediğin bankanın vadesi"dir; üç tur önceki bir
    cevabın öznesi o cümlenin öznesi değildir. Ölçüldü (tarayıcı): son cevap
    çok bankalı bir liste olduğunda özne iki tur geriden geliyor ve kullanıcı,
    o turda hiç anmadığı bir bankanın cevabını alıyordu. Son turun öznesi
    yoksa devralınacak özne de yoktur.
    """
    if not isinstance(kayitlar, (list, tuple)):
        return ChatContext()
    birlesik = ChatContext()
    for sira, ham in enumerate(list(kayitlar)[:max(0, sinir)]):
        tur = ChatContext.dogrula(ham)
        if birlesik.field is None:
            birlesik.field = tur.field
        if birlesik.intent is None:
            birlesik.intent = tur.intent
        for k, v in tur.filters.items():
            birlesik.filters.setdefault(k, v)
        if sira == 0:
            birlesik.subject_banks = tur.subject_banks
    return birlesik


@dataclass
class Route:
    handler: str                 # 'structured' | 'rag'
    field: Optional[str]         # ilgili alan (structured ise) — BİRİNCİL alan
    intent: Optional[str]        # 'lowest' | 'highest' | 'list' | 'filter'
    filters: dict                # ör. {"vade_ay_min": 36, "campaign_type": "Konut
                                 #      Finansmanı", "banks": ["kuveyt-turk"]}
    #: Önceki turlardan devralınan boyutlar — kullanıcıya gösterilir.
    #: [{"kind": "field", "label": "kâr payı oranı"}, ...]
    inherited: list[dict] = dc_field(default_factory=list)
    #: Alan kullanıcı tarafından SÖYLENMEDİ, kıyas niyetinden varsayıldı mı.
    #: Cevaba "çok boyutlu soruya tek boyutlu cevap" notu bu bayrakla eklenir;
    #: bayrak taşınmazsa varsayım kullanıcıya görünmez olurdu.
    alan_varsayildi: bool = False
    #: Bu turda SÖZCÜKLERİYLE istenen TÜM alanlar (`field` bunun İLKİDİR,
    #: geri kalanı yalnız bilgi taşır — `field` her yerde eskisi gibi tek
    #: bir alan gösterir, geriye dönük uyum bozulmaz).
    #:
    #: ## Ölçülen hata (jüri bulgusu, şartname s.12 Senaryo 1)
    #:
    #: "Kuveyt Türk'ün konut finansmanı ORANI VE VADESİ nedir?" sorusunda
    #: yalnız oran dönüyordu, vade sessizce düşüyordu. Sebep: eski
    #: `_detect_field` sözlükte İLK eşleşeni bulur bulmaz dururdu — ikinci
    #: alan hiç ARANMIYORDU bile. `structured.answer()` `fields` birden
    #: fazla ve tek bir banka çözülmüşse (`filters["banks"]` tam 1 slug)
    #: hepsini tek cevapta toplar; bulunamayan alan "bulunamadı" der,
    #: SESSİZCE atlanmaz.
    fields: list[str] = dc_field(default_factory=list)
    #: Soru ÇOK BOYUTLU ÜSTÜNLÜK istiyor mu ("en iyi/en uygun konut
    #: finansmanı hangi bankada?").
    #:
    #: `alan_varsayildi`'dan AYRI taşınır ve ayrı taşınması zorunludur: o
    #: bayrak "alanı ben seçtim" der, bu bayrak "alan TEK BAŞINA cevap
    #: değildir" der. İkisini tek bayrakta toplamak, gevşek alan eşlemesiyle
    #: (`_FOLDED_SUP_FIELD_KEYWORDS`) gelen tek boyutlu bir soruyu da
    #: (ör. "Kuveyt Türk ve Albaraka'da en yüksek finansman kimde") bileşik
    #: skor dalına sokardı — kullanıcının SÖYLEDİĞİ alanı görmezden gelmek.
    #:
    #: `structured.answer()` bu bayrakla `comparison.rank_advantageous_by_type()`
    #: dalına gider (ağırlıklı bileşik skor, ürün ailesi içinde).
    ustunluk: bool = False


def route(question: str, context: Optional[ChatContext] = None) -> Route:
    q = tr_fold_ascii(question)

    ham_alanlar = _detect_fields(q)
    field = ham_alanlar[0] if ham_alanlar else None
    intent = _detect_intent(q)
    filters = _detect_filters(q)

    # Terminoloji kapısı (girdi tarafı): kullanıcı konvansiyonel terimi
    # kullandıysa ("faiz en düşük hangi bankada?") soru REDDEDİLMEZ, doğru
    # alana (kâr payı oranı) yönlendirilir. Kendi alan sözlüğü zaten "oran"ı
    # yakalıyor; bu yedek, oran kelimesi hiç geçmeyen soruları kurtarır.
    # Sözcük sınırlı ve 'faizsiz' muaf — bkz. safety.mentions_interest_term.
    if field is None and mentions_interest_term(question):
        field = INTEREST_FIELD_HINT

    # Açık sıralama niyeti var ama alan çıkmadıysa gevşek eşlemeyi dene.
    # Bu kapı OLMADAN soru RAG'e düşüyor ve anahtar-kelime araması sorunun
    # yalnız yaygın sözcükleriyle örtüşen alakasız bir belge döndürebiliyor.
    #
    # ÜRÜN ADI MUAFİYETİ: "konut finansmanı"ndaki `finansman` bir tutar talebi
    # değildir (`_URUN_ADI_TUTAR_RE`). Eşleme bastırılırsa alan `None` kalır ve
    # soru aşağıdaki üstünlük kapısına düşer — bileşik skora, uydurma bir
    # tutar sıralamasına değil.
    alan_varsayildi = False
    # Gevşek eşleme ÜRÜN ADI yüzünden bastırıldı mı — yani soru bir SIRALAMA
    # istiyor ama sıralanacak alan yok. Yalnız bu durumda üstünlük dalının
    # üçüncü sinyali (`_ustunluk_niyeti`) devreye girer; regex'in tek başına
    # eşleşmesi YETMEZ, yoksa "Taşıt finansmanı kampanyasına kimler
    # başvurabilir?" gibi bir AÇIKLAMA sorusu da yapısal yola giderdi
    # (ölçüldü: `tests/test_rag_index.py` bu regresyonu yakaladı).
    bastirilan_tutar = False
    urun_adi_tutari = _URUN_ADI_TUTAR_RE.search(q) is not None
    if field is None and intent in ("lowest", "highest"):
        for ipucu, alan in _FOLDED_SUP_FIELD_KEYWORDS.items():
            if ipucu not in q:
                continue
            if urun_adi_tutari and alan == "finansman_tutari":
                bastirilan_tutar = True
                continue
            field = alan
            # VARSAYIM GÖRÜNÜR OLMALI. Alan kullanıcının sözcüğünden
            # TÜRETİLDİ ("finansman" -> finansman tutarı), söylenmedi;
            # `bot._kapsam_notu` bunu cevaba yazar. Bayrak taşınmadığı sürece
            # varsayım kullanıcıya görünmüyordu.
            alan_varsayildi = True
            break

    # Kıyas niyeti var ama alan söylenmemiş: "A mı daha avantajlı, B mi?".
    # Bu kapı OLMADAN soru RAG'e düşüyordu ve anahtar-kelime araması sorunun
    # yalnız yaygın sözcükleriyle örtüşen belgeler getiriyordu — iki banka da
    # soruda adıyla geçtiği hâlde. Gerekçenin tamamı `_KIYAS_ISARETLERI`'nde.
    ustunluk = False
    if field is None and _kiyas_niyeti(q, filters):
        field = VARSAYILAN_KIYAS_ALANI
        intent = intent or "list"
        alan_varsayildi = True
    # İKİNCİ SİNYAL — çok boyutlu ÜSTÜNLÜK ("en iyi", "en uygun", çıplak
    # "hangisi") ya da ürün adı yüzünden alansız kalmış bir sıralama sorusu.
    # Birincil alan yine kâr payı oranıdır (en yüksek ağırlıklı boyut), ama
    # cevap `rank_advantageous_by_type()` ile ÇOK BOYUTLU üretilir.
    elif field is None and _ustunluk_niyeti(q, filters, bastirilan_tutar):
        field = VARSAYILAN_KIYAS_ALANI
        intent = intent or "list"
        alan_varsayildi = True
        ustunluk = True

    # Sohbet bağlamı — sorunun EKSİK boyutlarını önceki turlardan devral.
    # Kapıların (safety.screen_input) ÇOK SONRASINDA değil, çok ÖNCESİNDE
    # değil: kapılar `bot.Chatbot.ask` içinde ham soru üzerinde zaten koştu.
    # Burada yapılan iş yalnız niyet çözümlemesidir.
    inherited: list[dict] = []
    if context is not None and not context.bos():
        field, intent, filters, inherited = _devral(field, intent, filters,
                                                    context)

    # `fields` — BU turda sözcükleriyle istenen tüm alanlar. `ham_alanlar`
    # devralmadan (context) ETKİLENMEZ: kullanıcı bu turda gerçekten birden
    # fazla alan söylediyse (`len(ham_alanlar) > 1`) o liste aynen taşınır;
    # aksi hâlde (0 ya da 1 alan söylenmiş, alan belki devralınmış/varsayılmış)
    # tek elemanlı `[field]` kalır — mevcut tek-alanlı davranış birebir korunur.
    fields = ham_alanlar if len(ham_alanlar) > 1 else ([field] if field else [])

    # sayısal/karşılaştırmalı sinyal varsa yapısal sorgu
    if field and (intent or filters):
        return Route("structured", field, intent or "list", filters, inherited,
                     alan_varsayildi, fields=fields, ustunluk=ustunluk)
    # sadece superlatif + alan
    if field and intent in ("lowest", "highest"):
        return Route("structured", field, intent, filters, inherited,
                     alan_varsayildi, fields=fields, ustunluk=ustunluk)
    # aksi halde RAG (açıklama/koşul soruları)
    return Route("rag", field, intent, filters, inherited, alan_varsayildi,
                 fields=fields, ustunluk=ustunluk)


def _kiyas_niyeti(q: str, filters: dict) -> bool:
    """Soru bir KIYAS istiyor mu (alan söylenmemiş olsa bile).

    İki bağımsız sinyal; biri yeterli:

    * Açık kıyas ifadesi ("karşılaştır", "daha avantajlı", "farkı ne").
    * İki banka adı + iki soru edatı: "Türkiye Finans **mı** …, Albaraka
      **mı**?" Tek edat yetmez — "Albaraka mı kâr payı veriyor?" bir kıyas
      değil, tek bankaya sorulmuş bir sorudur.
    """
    if any(s in q for s in _FOLDED_KIYAS):
        return True
    if len(filters.get("banks") or []) < 2:
        return False
    return len(re.findall(r"\b(?:mi|mu)\b", q)) >= 2


def _ustunluk_niyeti(q: str, filters: dict, bastirilan_tutar: bool) -> bool:
    """Soru ÇOK BOYUTLU üstünlük mü istiyor ("en iyi konut finansmanı")?

    `_kiyas_niyeti`'nin ikinci sinyalidir ve ondan SONRA denenir: iki bankayı
    adıyla sayan soru zaten karşı karşıya kıyasa gider
    (`structured._phrase_iki_banka_kiyasi`), bu kapı ise banka SAYILMAMIŞ
    ya da ikiden çok bankalı üstünlük sorularını bileşik skora götürür.

    Üç sinyal, biri yeterli:

    * Açık üstünlük ifadesi (`_USTUNLUK_ISARETLERI`): "en iyi", "en uygun",
      "en kârlı", "en cazip", "en mantıklı".
    * Çıplak "hangisi" (`_CIPLAK_HANGISI_RE`).
    * `bastirilan_tutar` — soru AÇIK bir sıralama istedi ("en düşük"),
      gevşek eşleme ürün adı muafiyetiyle bastırıldı ve sıralanacak alan
      kalmadı: "en düşük **konut finansmanı**". Sıralanmak istenen şey ürünün
      KENDİSİDİR ve bunun tek dürüst karşılığı çok boyutlu üstünlüktür.
      Muafiyet regex'inin tek başına eşleşmesi YETMEZ — "Taşıt finansmanı
      kampanyasına kimler başvurabilir?" bir açıklama sorusudur ve RAG'de
      kalır.

    ## TEK BANKALI SORU KIYAS DEĞİLDİR (karşı-örnek)

    "Albaraka'nın en iyi kampanyası hangisi" iki sinyali birden taşır ("en
    iyi" + "hangisi") ama bir bankalar arası üstünlük sorusu DEĞİLDİR: soru
    tek bir bankanın kendi kampanyaları arasında seçim istiyor. Süzgeç tam
    bir bankaya çözülmüşse kapı KAPALIDIR — aksi hâlde cevap, kullanıcının
    hiç sormadığı bankaları "daha avantajlı" diye ilan ederdi.
    `tests/test_ustunluk_sorusu.py` bunu karşı-örnek olarak kilitler.

    ## ALAN SÖYLENMİŞSE bu kapı HİÇ ÇALIŞMAZ

    Çağrı yeri (`route()`) kapıyı `field is None` koşuluyla sarar: "en uygun
    **vadeyi** hangi banka veriyor" sorusunda alan kullanıcının kendi
    sözcüğüdür ve cevap o alan üzerinden tek boyutlu kalır. Kullanıcının
    SÖYLEDİĞİ her zaman kazanır — bileşik skor bir varsayımdır ve varsayım,
    söylenmiş bir alanın yerine geçemez.
    """
    if len(filters.get("banks") or []) == 1:
        return False
    if any(s in q for s in _FOLDED_USTUNLUK):
        return True
    if _CIPLAK_HANGISI_RE.search(q):
        return True
    return bastirilan_tutar


def _devral(field: Optional[str], intent: Optional[str], filters: dict,
            ctx: ChatContext
            ) -> tuple[Optional[str], Optional[str], dict, list[dict]]:
    """Eksik boyutları bağlamdan tamamlar; ne devralındığını da döndürür.

    Devralma bir TAMAMLAMA aracıdır, bir varsayılan değil: yalnızca sorunun
    kendi başına yapısal sorgu kuramadığı hâllerde çalışır. Üç kural, üçü de
    "kullanıcının SÖYLEDİĞİ her zaman kazanır" ilkesine tabi:

    1. **Kendi başına yeterli soru HİÇBİR ŞEY devralmaz.** Yeterlilik ölçütü
       `route()`'un yapısal sorgu ölçütüyle aynıdır: alan + (niyet ya da
       süzgeç). Ölçüt eskiden "alan + niyet"ti ve kusur tam oradan çıktı —
       ölçüldü (tarayıcı, çok turlu oturum):

           — "Vakıf Katılım'ın taşıt kâr payı oranı nedir?"   (alan + süzgeç)
           — "Yeni müşterilere verilen EV finansman tutarı ne kadar?"
             → cevap: **Taşıt Finansmanı**, Vakıf Katılım, 36 ay

       Niyeti olmayan ama süzgeci olan soru "eksik" sayılıyor, üç ayrı turdan
       üç süzgeç birden yapışıyor ve kullanıcının SORDUĞU tür (konut) hiç
       görünmüyordu.

    2. **Özne devralma (tek gerekçe)** — kullanıcı YENİ bir alan söyleyip
       başka hiçbir şey söylemediyse ("Peki vade?"), sorduğu şey önceki
       CEVABIN öznesinin o alandaki değeridir. Devralınan tek şey o öznedir;
       önceki SORUNUN süzgeçleri (tür, vade eşiği, banka) buraya taşınmaz.
       Yeni bir alan, yeni bir sorudur; eski sorunun kapsamı onun kapsamı
       değildir.

    3. **Kalıp devralma (tek gerekçe)** — kullanıcı yeni bir özne/süzgeç verip
       alanı söylemediyse ("Peki ya Albaraka?"), aynı kalıp yeni özne üzerinde
       tekrarlanır: alan, niyet ve bu turda BELİRTİLMEYEN süzgeçler önceki
       turdan gelir. Burada süzgeçlerin taşınması tutarlıdır — soru zaten
       öncekinin aynısıdır, yalnız öznesi değişmiştir.

    Bir turda kural 2 ile kural 3 BİRLİKTE çalışmaz: devralmanın her zaman tek
    bir gerekçesi olur. Önceki sorunun süzgeci ile önceki cevabın öznesini aynı
    cevapta toplamak, kullanıcının hiç sormadığı bir soruyu kurmaktır.

    Devralınacak bir şey yoksa hiçbir şey uydurulmaz: soru bugünkü davranışına
    (çoğunlukla RAG, gerekirse çekimserlik) düşer.
    """
    inherited: list[dict] = []

    # KURAL 1 — soru kendi sinyaliyle yapısal sorgu kurabiliyor.
    if field is not None and (intent is not None or filters):
        return field, intent, filters, inherited

    # KURAL 2 — kullanıcı yeni bir ALAN söyledi, başka hiçbir şey söylemedi.
    if field is not None:
        if ctx.subject_banks:
            filters["banks"] = list(ctx.subject_banks)
            inherited.append({"kind": "subject_banks",
                              "value": list(ctx.subject_banks),
                              "label": _bankalar_etiketi(ctx.subject_banks)})
            return field, "list", filters, inherited
        # Önceki cevabın öznesi yoksa (ör. on bankalı bir liste) devralınacak
        # özne de yoktur; yalnız sorunun KALIBI (sıralama niyeti) taşınır.
        if ctx.intent:
            intent = ctx.intent
            inherited.append({"kind": "intent", "value": intent,
                              "label": INTENT_DISPLAY[intent]})
        return field, intent, filters, inherited

    # KURAL 3 — alan söylenmedi: önceki sorunun kalıbı yeni özneyle tekrarlanır.
    if ctx.field:
        field = ctx.field
        inherited.append({"kind": "field", "value": field,
                          "label": FIELD_DISPLAY[field]})

    # Süzgeçler: yalnız bu turda BELİRTİLMEYEN anahtarlar devralınır.
    for anahtar, deger in ctx.filters.items():
        if anahtar in filters:
            continue
        filters[anahtar] = deger
        inherited.append({"kind": f"filter:{anahtar}", "value": deger,
                          "label": _suzgec_etiketi(anahtar, deger)})

    if intent is None and ctx.intent:
        intent = ctx.intent
        inherited.append({"kind": "intent", "value": intent,
                          "label": INTENT_DISPLAY[intent]})

    return field, intent, filters, inherited


def _bankalar_etiketi(slugs: Sequence[str]) -> str:
    return ", ".join(BANK_DISPLAY.get(s, s) for s in slugs)


def _suzgec_etiketi(anahtar: str, deger: Any) -> str:
    ad = _SUZGEC_ETIKET.get(anahtar, anahtar)
    if anahtar == "banks" and isinstance(deger, (list, tuple)):
        return f"{ad}: {_bankalar_etiketi(deger)}"
    if anahtar == "vade_ay_min":
        return f"{ad}: {deger} ay"
    return f"{ad}: {deger}"


def _tur_ipucu(q: str) -> Optional[str]:
    """Katlanmış sorudan kampanya türü ipucu; yoksa `None`."""
    for kw, label in _FOLDED_TYPE_MAP.items():
        if kw in q:
            return label
    for desen, label in _TUR_SOZCUK_DESENLERI:
        if desen.search(q):
            return label
    return None


def _detect_fields(q: str) -> list[str]:
    """Soruda sözcükleriyle geçen TÜM alanları sırayla döndürür.

    Eskiden (`_detect_field`, tekil) sözlükteki İLK eşleşende dururdu —
    "kâr payı oranı VE VADESİ nedir?" sorusunda `vade_ay` hiç ARANMIYORDU
    bile. Bu fonksiyon hepsini toplar; `route()` birincisini (`field`) eski
    davranış için kullanır, tam listeyi (`Route.fields`) `structured.answer()`
    çok-alanlı tek-banka dalı için okur.
    """
    bulunanlar: list[str] = []
    for fname, kws in _FOLDED_FIELD_KEYWORDS.items():
        if any(kw in q for kw in kws):
            bulunanlar.append(fname)
    return bulunanlar


def _detect_intent(q: str) -> Optional[str]:
    if any(s in q for s in _FOLDED_SUP_LOW):
        return "lowest"
    if any(s in q for s in _FOLDED_SUP_HIGH):
        return "highest"
    if any(s in q for s in _FOLDED_LIST_INTENT):
        return "list"
    return None


def _detect_filters(q: str) -> dict:
    filters: dict = {}
    # "36 ay" gibi vade filtresi: "X ay veren/üzeri"
    m = re.search(r"(\d{1,3})\s*ay", q)
    # q katlanmış (ascii) geldiği için eşik sözcükleri de katlanmış yazılır.
    if m and any(s in q for s in ("veren", "uzeri", "ve uzeri", "en az")):
        filters["vade_ay_min"] = int(m.group(1))
    # kampanya türü filtresi — önce alt dize sözlüğü, sonra sözcük desenleri.
    # Sıra önemli: "taşıt evrakları" sorusunda "taşıt" önce eşleşir ve yalın
    # "ev" deseni hiç denenmez.
    tur = _tur_ipucu(q)
    if tur:
        filters["campaign_type"] = tur
    # banka filtresi — "Ziraat Katılım'ın konut kâr payı oranı nedir?" sorusu
    # BAŞKA bankaların satırlarıyla cevaplanmamalı. Banka verimizde yoksa
    # sonuç boş kalır ve çekimserlik kapısı (KAPI 5) devreye girer.
    # q zaten katlanmış; tr_fold_ascii idempotenttir, tekrar katlamak zararsız.
    banks = detect_banks(q)
    if banks:
        filters["banks"] = banks
    return filters
