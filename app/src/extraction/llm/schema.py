"""LLM kısıtlı-decoding (structured output) şeması + Türkçe prompt.

İlgili: ../../../decisions/ner-fine-tune-yerine-kural-few-shot.md (kural + few-shot LLM)
        ../../../concepts/kar-payi-orani.md, ../../../concepts/katilim-bankaciligi.md
        CLAUDE.md §19 (LLM çıktısı her zaman şema ile zorunlu), §10 (normalizasyon)
        Şartname §5.5 (terminolojiye uyum, s.8-9)

## Bu dosyada değişen iki şey ve nedenleri

**1) `{"type": ["object", "null"]}` union'ı yerine `anyOf`.**
vLLM'in varsayılan kısıtlı-decoding motoru xgrammar, JSON Schema'nın `type`
anahtarına dizi verilmesini (type union) güvenilir biçimde derlemez; şema
derlenmeyince sunucu 400 döner ve tüm çağrı düşer. `anyOf` biçimi hem
xgrammar hem Outlines hem de OpenAI `strict` json_schema tarafından kabul
edilir. Anlamı birebir aynıdır.

**2) Alan-tipli değer şeması (`FIELD_VALUE_SCHEMA`).**
Eskiden her alanın `value`'su `["string","number","object","null"]` idi; yani
gramer modele hiçbir şey dayatmıyordu — vade için `"120 ay"` (string) üretmek
şemaya UYGUNdu ve normalizasyon katmanında sessizce düşüyordu. Artık her alanın
kanonik biçimi gramere gömülüdür: vade `integer`, para `{value, currency}`,
oran `number` ya da `{min,max}`. Bu, kısıtlı decoding'in asıl faydasıdır:
**yanlış biçim ÜRETİLEMEZ.**

**3) Üst seviyede `required` = istenen tüm alanlar.**
Model her anahtarı üretmek ZORUNDA; bulamadığı alanı açıkça `null` yazar.
Aksi halde "modelin atladığı alan" ile "metinde olmayan alan" ayırt edilemez —
ve bu ayrım recall hata analizinin tamamıdır (hangisini düzelteceğin buna
bağlı: prompt mu, kural mı).
"""

from __future__ import annotations

from typing import Optional

# Çıkarılacak alanlar (bkz. CLAUDE.md §9 veri modeli)
EXTRACTION_FIELDS = [
    "kar_payi_orani",
    "finansman_tutari",
    "vade_ay",
    "taksit_sayisi",
    "tahsis_ucreti",
    "masraf_durumu",
    "odul_miktari",
    "indirim_orani",
    "alisveris_puani",
    "kampanya_suresi",
    "kampanya_kosullari",
    "hedef_kitle",
]

# Hedef kitle segmentleri — kural katmanıyla (rules/extract.py) BİREBİR aynı
# etiket kümesi. Ayrışırlarsa uzlaştırma iki farklı sözlüğü kıyaslar.
HEDEF_KITLE_LABELS = [
    "yeni_musteri",
    "mevcut_musteri",
    "maas_musterisi",
    "belirli_segment",
]


def _null() -> dict:
    return {"type": "null"}


def _nullable(schema: dict) -> dict:
    """`X | null` — type-union yerine anyOf (xgrammar uyumu, bkz. modül başlığı)."""
    return {"anyOf": [schema, _null()]}


def _money() -> dict:
    """Para: {"value": sayı, "currency": "TRY"} (CLAUDE.md §10)."""
    return {
        "type": "object",
        "properties": {
            "value": {"type": "number"},
            "currency": {"type": "string", "enum": ["TRY"]},
        },
        "required": ["value", "currency"],
        "additionalProperties": False,
    }


def _range() -> dict:
    """Oran aralığı: {"min": x, "max": y} — "%1,99–%2,49" zor vakası."""
    return {
        "type": "object",
        "properties": {"min": {"type": "number"}, "max": {"type": "number"}},
        "required": ["min", "max"],
        "additionalProperties": False,
    }


def _masraf() -> dict:
    """Masraf durumu: negasyon ("masrafsız") burada değere dönüşür.

    `has_fee=false, amount=0` "bilgi yok" DEĞİLDİR; masrafın sıfır olduğunun
    pozitif ifadesidir (CLAUDE.md §6 negasyon zor-vakası).
    """
    return {
        "type": "object",
        "properties": {
            "has_fee": {"type": "boolean"},
            "amount": _nullable({"type": "number"}),
        },
        "required": ["has_fee", "amount"],
        "additionalProperties": False,
    }


def _alisveris_puani() -> dict:
    """Alışveriş puanı ORAN ya da ADET olabilir; ikisi kıyaslanamaz.

    kind ayrımı olmadan "%5 puan iadesi" ile "1.000 chip-para" aynı sütunda
    sıralanır (CLAUDE.md §17 adil kıyas garantisi ihlali).
    """
    return {
        "type": "object",
        "properties": {
            "kind": {"type": "string", "enum": ["rate", "points"]},
            "value": {"type": "number"},
        },
        "required": ["kind", "value"],
        "additionalProperties": False,
    }


# Alan -> kanonik değer şeması. Kural katmanının ürettiği biçimlerle birebir
# aynıdır; uzlaştırma (reconcile.py) iki katmanın çıktısını aynı tipte kıyaslar.
FIELD_VALUE_SCHEMA: dict[str, dict] = {
    # Oran: nokta değer ya da aralık.
    "kar_payi_orani": {"anyOf": [{"type": "number"}, _range()]},
    "indirim_orani": {"anyOf": [{"type": "number"}, _range()]},
    # Para.
    "finansman_tutari": _money(),
    "tahsis_ucreti": _money(),
    "odul_miktari": _money(),
    # Tamsayı (ay / adet).
    "vade_ay": {"type": "integer"},
    "taksit_sayisi": {"type": "integer"},
    # Yapılandırılmış.
    "masraf_durumu": _masraf(),
    "alisveris_puani": _alisveris_puani(),
    # ISO-8601 tarih (YYYY-AA-GG). `pattern` bilerek KONULMADI: bazı gramer
    # derleyicileri regex kısıtını desteklemez ve şema derlenmez; biçim
    # SYSTEM_PROMPT'ta dayatılır, doğrulama normalizasyon katmanında yapılır.
    "kampanya_suresi": {"type": "string"},
    # Listeler.
    "kampanya_kosullari": {"type": "array", "items": {"type": "string"}},
    "hedef_kitle": {
        "type": "array",
        "items": {"type": "string", "enum": HEDEF_KITLE_LABELS},
    },
}


def _field_obj(name: str) -> dict:
    """Tek alan için şema parçası: kanonik değer + güven + kaynak parçası."""
    return {
        "type": "object",
        "properties": {
            "value": _nullable(FIELD_VALUE_SCHEMA[name]),
            # `minimum`/`maximum` BİLEREK yok: sayısal sınırlar bazı gramer
            # derleyicilerinde (xgrammar) desteklenmez ve şemanın tamamının
            # reddedilmesine yol açabilir — 0-1 kısıtı uğruna kısıtlı
            # decoding'in tamamını kaybetmek kötü bir takas. Aralık kodda
            # kırpılır (confidence.clamp).
            "confidence": {"type": "number"},
            "source_span": _nullable({"type": "string"}),
        },
        "required": ["value", "confidence", "source_span"],
        "additionalProperties": False,
    }


def guided_json_schema(fields: Optional[list[str]] = None) -> dict:
    """Kısıtlı decoding'e verilecek tam JSON Schema.

    Args:
        fields: yalnız bu alanlar istenir (kuralların bulamadıkları). None ise
            12 alanın tamamı. Alt küme sorulduğunda gramer de daralır — hem
            token hem hata yüzeyi küçülür.

    Üst seviyede `required` istenen alanların TAMAMIdır: model bulamadığı alanı
    atlayamaz, açıkça `null` yazmak zorundadır (bkz. modül başlığı, madde 3).
    """
    names = [f for f in (fields or EXTRACTION_FIELDS) if f in FIELD_VALUE_SCHEMA]
    if not names:
        names = list(EXTRACTION_FIELDS)
    return {
        "type": "object",
        "properties": {name: _nullable(_field_obj(name)) for name in names},
        "required": names,
        "additionalProperties": False,
    }


def json_schema_envelope(fields: Optional[list[str]] = None,
                         name: str = "kampanya_cikarimi") -> dict:
    """OpenAI standardı `response_format.json_schema` zarfı (strict=true)."""
    return {
        "name": name,
        "schema": guided_json_schema(fields),
        "strict": True,
    }


# --------------------------------------------------------------------------- #
# Prompt
# --------------------------------------------------------------------------- #
# Şartname §5.5 (s.8-9) "Terminolojiye Uyum" başlığındaki beş terim modele AÇIK
# TANIMLARIYLA verilir. Genel amaçlı bir LLM "kâr payı"nı temettü ya da faiz
# sanabilir; katılım bankacılığı terminolojisi konvansiyonelden farklıdır ve bu
# fark rubriğin en ağır kalemi olan "Model Başarısı ve Anlamlandırma"nın (%30)
# tam merkezindedir (CLAUDE.md §12).
SYSTEM_PROMPT = """Sen Türkiye'deki KATILIM BANKALARININ (faizsiz finans) \
kampanya metinlerinden finansal bilgi çıkaran bir uzmansın. SADECE verilen \
şemaya uyan JSON döndür; açıklama, selamlama, markdown yazma.

## Alan terminolojisi (katılım bankacılığı — konvansiyonel bankacılıktan FARKLI)
- **kâr payı (oranı):** Faiz DEĞİLDİR. Murabaha işleminde finansmana konu mal \
veya hizmet üzerinden önceden ilan edilen KÂR MARJIDIR. Metinde "kâr payı", \
"kâr payı oranı", "özel oranlı finansman", "avantajlı kâr payı" biçimlerinde \
geçer; hepsi `kar_payi_orani` alanıdır.
- **finansman maliyeti:** Müşterinin finansman için ödediği toplam yük \
(kâr payı + tahsis ücreti + varsa diğer masraflar). Tek bir orana indirgeme; \
bileşenleri ilgili alanlara ayrı ayrı yaz.
- **katılım fonu:** Bankaya yatırılan, kâr/zarara katılma esasına göre \
değerlendirilen mevduat (katılma hesabı). Bu bir FİNANSMAN ÜRÜNÜ DEĞİL, \
yatırım/toplama ürünüdür — buradaki getiri oranını `kar_payi_orani` alanına \
finansman oranıymış gibi yazma; ürünün yatırım tarafı olduğunu \
`kampanya_kosullari` içinde belirt.
- **masrafsız finansman:** Tahsis ücreti/dosya masrafı ALINMAYAN finansman. \
Bu "bilgi yok" DEĞİL, masrafın SIFIR olduğunun ifadesidir: \
`masraf_durumu = {"has_fee": false, "amount": 0}`.
- **avantajlı finansman:** Bankanın standart oranından daha düşük oranla \
sunulan finansman. Tek başına SAYISAL BİR DEĞER DEĞİLDİR; sayı verilmemişse \
`kar_payi_orani` null kalır, ifade `kampanya_kosullari`na yazılır.

## Katı kurallar
1. Bilgi metinde AÇIKÇA yoksa o alanın değeri `null` olsun. ASLA değer UYDURMA, \
başka kampanyalardan/ön bilgiden tamamlama yapma.
2. İstenen HER anahtarı üret. Bulamadığın alanı ATLAMA, `null` yaz.
3. Oran: yüzde işaretsiz decimal (%2,05 -> 2.05). Aralıksa {"min":1.99,"max":2.49}.
4. Para: {"value": 500, "currency": "TRY"}. TR sayı formatı: 1.500,00 -> 1500.0 \
(binlik ayıracı nokta, ondalık ayıracı virgül).
5. Vade ve taksit: AY / ADET cinsinden TAMSAYI. "1 yıl" -> 12. "120 aya varan" -> 120.
6. Tarih: ISO-8601, yani YYYY-AA-GG. "31.12.2026" -> "2026-12-31".
7. `hedef_kitle`: yalnız şu etiketler, liste halinde — yeni_musteri, \
mevcut_musteri, maas_musterisi, belirli_segment. Sinyal yoksa null. \
"yeni müşteri olmayanlar" gibi NEGASYON etiketi ÜRETMEZ.
8. `kampanya_kosullari`: koşul cümlelerinin listesi. Yalnızca geçerlilik tarihi \
bildiren cümle koşul DEĞİLDİR (o `kampanya_suresi`).
9. Her bulduğun alan için `source_span`: değerin geçtiği metin parçasını \
metinden BİREBİR kopyala (kendi cümleni yazma). Bulunamayan alanda null.
10. `confidence`: 0-1 arası. Metin belirsizse, birden çok aday varsa ya da \
çıkarım dolaylıysa DÜŞÜR. Emin olmadığın yerde yüksek güven yazmak, yanlış \
cevaptan daha kötüdür."""


# --------------------------------------------------------------------------- #
# Few-shot: her örnek BİR zor-vaka kategorisini temsil eder (CLAUDE.md §6)
# --------------------------------------------------------------------------- #
# Tek örnek yeterli değildi: model zor vakalarda (aralık, negasyon, çelişki)
# öntanımlı davranışına dönüyordu. Altı örnek, gold setteki "zor vakalar" alt
# kümesinin altı kategorisini birebir kapsar; ablasyonda hibridin kazandığı
# yer tam olarak burasıdır.
FEWSHOT = [
    {
        "category": "aralik",
        "text": "Taşıt finansmanı kâr payı oranı %1,99 - %2,49 arasındadır, 48 ay vade.",
        "json": {
            "kar_payi_orani": {"value": {"min": 1.99, "max": 2.49}, "confidence": 0.92,
                               "source_span": "%1,99 - %2,49"},
            "vade_ay": {"value": 48, "confidence": 0.95, "source_span": "48 ay"},
        },
    },
    {
        "category": "zaman-kosullu-oran",
        "text": ("Konut finansmanında ilk 6 ay %0, sonrasında %1,89 kâr payı; "
                 "120 aya varan vade."),
        "json": {
            # Yürürlükteki asıl oran yazılır; "ilk 6 ay %0" bir KOŞULdur.
            "kar_payi_orani": {"value": 1.89, "confidence": 0.8,
                               "source_span": "%1,89 kâr payı"},
            "vade_ay": {"value": 120, "confidence": 0.9,
                        "source_span": "120 aya varan"},
            "kampanya_kosullari": {"value": ["İlk 6 ay %0 kâr payı uygulanır."],
                                   "confidence": 0.85,
                                   "source_span": "ilk 6 ay %0"},
        },
    },
    {
        "category": "negasyon",
        "text": "İhtiyaç finansmanında dosya masrafı yok, tahsis ücreti alınmaz. 36 ay vade.",
        "json": {
            # "yok" = bilgi eksik DEĞİL; masraf sıfır (CLAUDE.md §6).
            "masraf_durumu": {"value": {"has_fee": False, "amount": 0},
                              "confidence": 0.95,
                              "source_span": "dosya masrafı yok"},
            "tahsis_ucreti": {"value": {"value": 0, "currency": "TRY"},
                              "confidence": 0.9,
                              "source_span": "tahsis ücreti alınmaz"},
            "vade_ay": {"value": 36, "confidence": 0.95, "source_span": "36 ay"},
        },
    },
    {
        "category": "eksik-bilgi",
        "text": "Size özel avantajlı finansman fırsatlarını şubelerimizden öğrenebilirsiniz.",
        "json": {
            # Sayı YOK -> uydurma yok. "avantajlı" tek başına oran değildir.
            "kar_payi_orani": {"value": None, "confidence": 0.0, "source_span": None},
            "vade_ay": {"value": None, "confidence": 0.0, "source_span": None},
            "finansman_tutari": {"value": None, "confidence": 0.0, "source_span": None},
        },
    },
    {
        "category": "celiski",
        "text": ("Masrafsız konut finansmanı! Tahsis ücreti finansman tutarının "
                 "binde 5'i olarak uygulanır."),
        "json": {
            # Metin kendi içinde çelişiyor: "masrafsız" + ücretli tahsis.
            # Çelişki GİZLENMEZ; düşük güvenle iki taraf da yazılır ve koşula
            # not düşülür (CLAUDE.md §18 hedef #2: çelişki tespiti).
            "masraf_durumu": {"value": {"has_fee": True, "amount": None},
                              "confidence": 0.35,
                              "source_span": "Masrafsız konut finansmanı"},
            "kampanya_kosullari": {
                "value": ["Metin 'masrafsız' derken tahsis ücreti binde 5 olarak "
                          "belirtilmiş; ifadeler çelişiyor."],
                "confidence": 0.6,
                "source_span": "Tahsis ücreti finansman tutarının binde 5'i",
            },
        },
    },
    {
        "category": "hedef-kitle",
        "text": ("Maaşını bankamızdan alan emekli müşterilerimize özel 5.000 TL'ye "
                 "varan hoş geldin hediyesi. Yeni müşteri olmayanlar için geçerli değildir."),
        "json": {
            # "Yeni müşteri olmayanlar ... geçerli değildir" NEGASYONdur ->
            # yeni_musteri etiketi üretilmez.
            "hedef_kitle": {"value": ["belirli_segment", "maas_musterisi"],
                            "confidence": 0.85,
                            "source_span": "Maaşını bankamızdan alan emekli müşterilerimize"},
            "odul_miktari": {"value": {"value": 5000, "currency": "TRY"},
                             "confidence": 0.9,
                             "source_span": "5.000 TL'ye varan hoş geldin hediyesi"},
        },
    },
]
