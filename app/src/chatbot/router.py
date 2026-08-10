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

# Kullanıcı sorusu ALL-CAPS veya diakritiksiz gelebilir ("EN DÜŞÜK KÂR PAYI",
# "en dusuk kar payi"). Eşleşme tr_fold_ascii üzerinden yapılır; anahtar
# kelimeler de modül yüklenirken aynı forma indirgenir.
_F = tr_fold_ascii
_FOLDED_FIELD_KEYWORDS = {k: [_F(v) for v in vals]
                          for k, vals in _FIELD_KEYWORDS.items()}
_FOLDED_SUP_LOW = [_F(s) for s in _SUPERLATIVE_LOW]
_FOLDED_SUP_HIGH = [_F(s) for s in _SUPERLATIVE_HIGH]
_FOLDED_LIST_INTENT = [_F(s) for s in _LIST_INTENT]

# Kampanya türü filtresi: soru içindeki ipucu → 8 sınıftan biri.
# Kullanıcı ürün adını değil GÜNLÜK KELİMEYİ kullanır: "araba alımında en
# yüksek finansman kimde" sorusu ölçüldü ve `taşıt` geçmediği için tür
# filtresi hiç kurulmuyordu.
_FOLDED_TYPE_MAP = {_F(k): v for k, v in {
    "konut": "Konut Finansmanı", "ev alım": "Konut Finansmanı",
    "mortgage": "Konut Finansmanı",
    "taşıt": "Taşıt Finansmanı", "araba": "Taşıt Finansmanı",
    "araç": "Taşıt Finansmanı", "otomobil": "Taşıt Finansmanı",
    "sıfır km": "Taşıt Finansmanı",
    "ihtiyaç": "İhtiyaç Finansmanı", "kart": "Kart",
    "yatırım": "Yatırım Ürünü",
}.items()}

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
CAMPAIGN_TYPES: frozenset[str] = frozenset(_FOLDED_TYPE_MAP.values())

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
    """
    if not isinstance(kayitlar, (list, tuple)):
        return ChatContext()
    birlesik = ChatContext()
    for ham in list(kayitlar)[:max(0, sinir)]:
        tur = ChatContext.dogrula(ham)
        if birlesik.field is None:
            birlesik.field = tur.field
        if birlesik.intent is None:
            birlesik.intent = tur.intent
        for k, v in tur.filters.items():
            birlesik.filters.setdefault(k, v)
        if not birlesik.subject_banks:
            birlesik.subject_banks = tur.subject_banks
    return birlesik


@dataclass
class Route:
    handler: str                 # 'structured' | 'rag'
    field: Optional[str]         # ilgili alan (structured ise)
    intent: Optional[str]        # 'lowest' | 'highest' | 'list' | 'filter'
    filters: dict                # ör. {"vade_ay_min": 36, "campaign_type": "Konut
                                 #      Finansmanı", "banks": ["kuveyt-turk"]}
    #: Önceki turlardan devralınan boyutlar — kullanıcıya gösterilir.
    #: [{"kind": "field", "label": "kâr payı oranı"}, ...]
    inherited: list[dict] = dc_field(default_factory=list)


def route(question: str, context: Optional[ChatContext] = None) -> Route:
    q = tr_fold_ascii(question)

    field = _detect_field(q)
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
    if field is None and intent in ("lowest", "highest"):
        for ipucu, alan in _FOLDED_SUP_FIELD_KEYWORDS.items():
            if ipucu in q:
                field = alan
                break

    # Sohbet bağlamı — sorunun EKSİK boyutlarını önceki turlardan devral.
    # Kapıların (safety.screen_input) ÇOK SONRASINDA değil, çok ÖNCESİNDE
    # değil: kapılar `bot.Chatbot.ask` içinde ham soru üzerinde zaten koştu.
    # Burada yapılan iş yalnız niyet çözümlemesidir.
    inherited: list[dict] = []
    if context is not None and not context.bos():
        field, intent, filters, inherited = _devral(field, intent, filters,
                                                    context)

    # sayısal/karşılaştırmalı sinyal varsa yapısal sorgu
    if field and (intent or filters):
        return Route("structured", field, intent or "list", filters, inherited)
    # sadece superlatif + alan
    if field and intent in ("lowest", "highest"):
        return Route("structured", field, intent, filters, inherited)
    # aksi halde RAG (açıklama/koşul soruları)
    return Route("rag", field, intent, filters, inherited)


def _devral(field: Optional[str], intent: Optional[str], filters: dict,
            ctx: ChatContext
            ) -> tuple[Optional[str], Optional[str], dict, list[dict]]:
    """Eksik boyutları bağlamdan tamamlar; ne devralındığını da döndürür.

    Üç kural, üçü de "kullanıcının SÖYLEDİĞİ her zaman kazanır" ilkesine tabi:

    1. **Kendi başına eksiksiz soru bağlam devralmaz.** Alan ve niyet birlikte
       çıktıysa soru zaten yapısal sorguya gidiyordur; oraya üç tur önceki bir
       süzgeci sessizce eklemek, kullanıcının sormadığı bir soruyu
       cevaplamak olurdu.
    2. **Özne devralma** — kullanıcı YENİ bir alan söyleyip hiçbir sıralama
       niyeti belirtmediyse ("Peki vade?"), sorduğu şey önceki CEVABIN
       öznesinin o alandaki değeridir. Bu yüzden özne banka süzgece çevrilir.
    3. **Kalıp devralma** — kullanıcı yeni bir özne/süzgeç verip alanı
       söylemediyse ("Peki ya Albaraka?"), aynı kalıp yeni özne üzerinde
       tekrarlanır: alan ve niyet önceki turdan gelir.

    Devralınacak bir şey yoksa hiçbir şey uydurulmaz: soru bugünkü davranışına
    (çoğunlukla RAG, gerekirse çekimserlik) düşer.
    """
    inherited: list[dict] = []
    if field is not None and intent is not None:
        return field, intent, filters, inherited

    kullanicinin_alani = field is not None

    if field is None and ctx.field:
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

    if intent is None:
        if kullanicinin_alani and ctx.subject_banks and "banks" not in filters:
            filters["banks"] = list(ctx.subject_banks)
            intent = "list"
            inherited.append({"kind": "subject_banks",
                              "value": list(ctx.subject_banks),
                              "label": _bankalar_etiketi(ctx.subject_banks)})
        elif ctx.intent:
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


def _detect_field(q: str) -> Optional[str]:
    for fname, kws in _FOLDED_FIELD_KEYWORDS.items():
        if any(kw in q for kw in kws):
            return fname
    return None


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
    # kampanya türü filtresi
    for kw, label in _FOLDED_TYPE_MAP.items():
        if kw in q:
            filters["campaign_type"] = label
            break
    # banka filtresi — "Ziraat Katılım'ın konut kâr payı oranı nedir?" sorusu
    # BAŞKA bankaların satırlarıyla cevaplanmamalı. Banka verimizde yoksa
    # sonuç boş kalır ve çekimserlik kapısı (KAPI 5) devreye girer.
    # q zaten katlanmış; tr_fold_ascii idempotenttir, tekrar katlamak zararsız.
    banks = detect_banks(q)
    if banks:
        filters["banks"] = banks
    return filters
