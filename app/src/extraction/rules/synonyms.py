"""Faizsiz finans eşanlamlılar / tetikleyici sözlüğü.

İlgili: ../../concepts/katilim-bankaciligi.md, ../../sorun/katilim-bankaciligi-terminoloji-farkliligi.md
Kâr payı = faiz değil (murabaha kâr marjı); finansman = kredi.

Eşleşme `tr_fold_ascii` üzerinden yapılır (bkz. preprocessing/clean.py): hem
ALL-CAPS banka başlıkları hem diakritiksiz yazımlar aynı forma indirgenir.
Bu yüzden aşağıdaki listelerde 'taşıt'/'tasit' gibi varyantlar bulunması
zararsızdır — katlama sonrası set'e indirgenip tek kez sayılırlar.
"""

import re
from typing import Optional

from ...normalization.normalize import NEGATION_RE as _NEGATION_RE
from ...preprocessing.clean import tr_fold_ascii

# Bir alanı tetikleyen anahtar ifadeler (hepsi küçük harf, TR sadeleştirilmiş eşleşme
# çağrı tarafında yapılır). Sıra önemsiz; eşleşme "içeriyor mu" mantığıyla.
FIELD_TRIGGERS: dict[str, list[str]] = {
    "kar_payi_orani": [
        "kâr payı oranı", "kar payı oranı", "kâr payı", "kar payı",
        "getiri oranı", "kâr oranı", "kar orani",
    ],
    "finansman_tutari": [
        "finansman tutarı", "finansman", "tutar", "kredi tutarı", "limit",
    ],
    "vade_ay": [
        "vade", "ödeme süresi", "geri ödeme süresi", "taksit süresi", "ay",
    ],
    "taksit_sayisi": [
        "taksit", "taksit sayısı", "taksit adedi",
    ],
    "tahsis_ucreti": [
        "tahsis ücreti", "dosya masrafı", "dosya masrafi",
    ],
    "masraf_durumu": [
        "masrafsız", "masrafsiz", "ücretsiz", "ucretsiz", "masraf", "tahsis",
    ],
    "kampanya_suresi": [
        "kampanya süresi", "son başvuru", "geçerlilik", "kampanya tarihleri",
        "tarihine kadar",
    ],
}

# Kampanya türü sınıflandırma için kaba kural-ipuçları (LLM/BERTurk birincil,
# bu yalnız few-shot/zayıf-etiket başlangıcı).
TYPE_HINTS: dict[str, list[str]] = {
    "Konut Finansmanı": ["konut", "ev", "mortgage", "konut finansman"],
    "Taşıt Finansmanı": ["taşıt", "tasit", "araç", "arac", "otomobil", "araba"],
    "İhtiyaç Finansmanı": ["ihtiyaç", "ihtiyac", "ihtiyaç finansman"],
    "Kart": ["kredi kartı", "kart", "bonus", "kartınız"],
    "Alışveriş Puanı": ["puan", "alışveriş puanı", "alisveris puani", "chip-para"],
    "Yeni Müşteri": ["yeni müşteri", "yeni musteri", "ilk kez", "hoş geldin"],
    # "katılım fonu" şartname §5.5'te açıkça tanımlanan beş kavramdan biri:
    # "kâr-zarar paylaşımına dayanan hesap türü". Bir yatırım ürünüdür.
    "Yatırım Ürünü": ["yatırım", "yatirim", "katılma hesabı", "katılım fonu",
                      "katilim fonu", "altın hesabı", "fon"],
    "Finansman": ["finansman", "kredi"],  # en genel; en sona düşer
}


# --------------------------------------------------------------------------- #
# Şartname §5.5 — katılım bankacılığı terminolojisi
# --------------------------------------------------------------------------- #
# Şartname beş kavramı isim isim sayıyor ve modelin bunları "doğru şekilde
# yorumlaması" bekleniyor. Beşinin de kural katmanında karşılığı olmalı:
# ikisi (finansman maliyeti, katılım fonu) 31 Tem'e kadar YALNIZCA LLM
# prompt'unda (`llm/schema.py`) tanımlıydı — yani LLM kapalıyken, ki
# offline varsayılanımız bu, sistem o kavramları hiç bilmiyordu.
#
# Buradaki eşleme *ayırt etme* içindir, değer çıkarma değil. Özellikle
# "finansman maliyeti" ile "kâr payı oranı" KARIŞTIRILMAMALI: ilki toplam
# geri ödeme yükü (TL), ikincisi oran (%). İkisini aynı alana yazmak
# karşılaştırmayı sessizce bozar.
TERMINOLOGY_5_5: dict[str, dict[str, str]] = {
    "kar_payi_orani": {
        "tanim": "Faiz yerine kullanılan, finansman işlemine konu mal veya "
                 "hizmet üzerinden oluşan kâr payı oranı.",
        "birim": "oran (%)",
    },
    "finansman_maliyeti": {
        "tanim": "Kullandırılan finansman kapsamında oluşan toplam geri ödeme "
                 "tutarı ve müşterinin katlandığı toplam maliyet.",
        "birim": "para (TL)",
        "karistirma": "kar_payi_orani ile aynı şey DEĞİL — biri tutar, biri oran.",
    },
    "katilim_fonu": {
        "tanim": "Katılım bankacılığı prensiplerine uygun değerlendirilen, fon "
                 "sahipleri ile banka arasında kâr-zarar paylaşımına dayanan "
                 "hesap türü.",
        "birim": "hesap türü",
    },
    "masrafsiz_finansman": {
        "tanim": "Tahsis ücreti, dosya masrafı veya benzeri ek maliyetlerin "
                 "uygulanmadığı finansman türü.",
        "birim": "masraf_durumu -> has_fee=False",
    },
    "avantajli_finansman": {
        "tanim": "Standart finansman koşullarına göre daha uygun maliyet, kâr "
                 "payı oranı veya ek fayda sunan kampanyalı finansman ürünü.",
        "birim": "nitel iddia — sayısal değeri YOKTUR",
    },
}

TERMINOLOGY_TRIGGERS: dict[str, list[str]] = {
    "finansman_maliyeti": ["finansman maliyeti", "toplam geri ödeme",
                           "toplam geri odeme", "toplam maliyet",
                           "yıllık maliyet oranı", "yillik maliyet orani"],
    "katilim_fonu": ["katılım fonu", "katilim fonu", "katılma hesabı",
                     "katilma hesabi", "kâr-zarar paylaşımı",
                     "kar-zarar paylasimi"],
}


# --------------------------------------------------------------------------- #
# Şartname §5.2 — sayısal olmayan oran iddiaları
# --------------------------------------------------------------------------- #
# Şartname modelin şu dört ifade biçimini yorumlamasını istiyor:
#
#     "%2,05 kâr payı oranı"      -> sayısal, kar_payi_orani = 2.05
#     "avantajlı kâr payı fırsatı" -> NİTEL
#     "özel oranlı finansman"      -> NİTEL
#     "düşük maliyetli finansman"  -> NİTEL
#
# Son üçünde SAYI YOKTUR. Bunlardan bir oran üretmek halüsinasyondur ve
# CLAUDE.md §19'un ("bilgi yoksa null") doğrudan ihlalidir. Doğru davranış:
# iddiayı TANIMAK, ama `kar_payi_orani`'na yazmamak.
#
# Bunun pratik değeri şudur: "avantajlı kâr payı" diyen ama oran vermeyen bir
# kampanya, oran veren bir kampanyayla KIYASLANAMAZ. Adil kıyas garantisi
# (CLAUDE.md §17) bunu "doğrudan kıyaslanamaz" diye işaretlemeli — sessizce
# sıralama dışı bırakmak yerine, iddiayı gösterip kıyaslanamadığını söylemeli.
QUALITATIVE_RATE_CLAIMS: list[str] = [
    "avantajlı kâr payı", "avantajli kar payi",
    "avantajlı oran", "avantajli oran",
    "özel oranlı", "ozel oranli", "özel oran", "ozel oran",
    "düşük maliyetli", "dusuk maliyetli",
    "uygun maliyetli", "cazip oran", "avantajlı finansman",
    "avantajli finansman", "avantajlı fiyat", "avantajli fiyat",
]

FOLDED_QUALITATIVE_CLAIMS: frozenset[str] = frozenset(
    tr_fold_ascii(t) for t in QUALITATIVE_RATE_CLAIMS)


def qualitative_rate_claim(folded_text: str) -> Optional[str]:
    """Sayısal olmayan bir oran/maliyet avantajı iddiası varsa onu döndürür.

    ASLA sayısal değer üretmez — §5.2'nin nitel ifadelerinden oran çıkarmak
    halüsinasyon olur. Yalnızca iddianın VARLIĞINI bildirir; çağıran taraf
    bunu kampanya koşulu olarak kaydeder ve karşılaştırmada
    "doğrudan kıyaslanamaz" işaretler.
    """
    for iddia in sorted(FOLDED_QUALITATIVE_CLAIMS, key=len, reverse=True):
        if matches(iddia, folded_text):
            return iddia
    return None


def terminology_hits(folded_text: str) -> dict[str, str]:
    """§5.5 kavramlarından metinde geçenleri döndürür: {kavram: eşleşen ifade}."""
    out: dict[str, str] = {}
    for kavram, ifadeler in TERMINOLOGY_TRIGGERS.items():
        for ifade in ifadeler:
            if matches(tr_fold_ascii(ifade), folded_text):
                out[kavram] = ifade
                break
    return out


# Negasyon: "tahsis ücreti ALINMAZ" gibi ifadeler ücretin YOK olduğunu değil,
# SIFIR olduğunu söyler (bkz. ../../decisions/zor-anlama-vakalari-merkezi.md).
# Tek doğruluk kaynağı normalization/normalize.py'dir; burada yalnızca yeniden
# ihraç edilir ki çıkarım ve normalizasyon katmanları AYNI deseni kullansın
# (iki ayrı kopya kaçınılmaz olarak birbirinden ayrışırdı).
NEGATION_RE = _NEGATION_RE


def keyword_pattern(keyword: str) -> str:
    """Anahtar kelimeyi SÖZCÜK SINIRLI bir desene çevirir.

    Neden gerekli: eşleşme eskiden düz alt-dize (`kw in text`) ile yapılıyordu.
    291 belgelik gerçek korpusta ölçüldü ve sınıflandırmayı çökertiyordu:

        'ev'  (Konut Finansmanı anahtarı) -> 'devam', 'seviye', 'evet',
              'evrak' içinde eşleşiyor
        'fon' (Yatırım Ürünü anahtarı)    -> 'fonksiyon' içinde eşleşiyor

    Sonuç: "Modanisa'da %15 indirim" (giyim kampanyası) ve "hisse senedi
    işlemleri" gibi belgeler **Konut Finansmanı** olarak sınıflanıyordu.
    Korpusun %48'i sahte Konut Finansmanı çıkmıştı.

    Kural:
      - Kısa anahtarlar (<= 4 karakter) İKİ TARAFTAN sınırlı eşleşir
        ('ev' yalnız "ev" sözcüğüne uyar, "devam"a uymaz).
      - Uzun anahtarlar SOL sınırlı eşleşir, ek almaya izin verilir
        ('konut' -> "konutunuz", "konuttan" da eşleşir; Türkçe sondan
        eklemeli bir dildir, bu davranış istenir).
    """
    esc = re.escape(keyword)
    return rf"\b{esc}\b" if len(keyword) <= 4 else rf"\b{esc}"


def matches(keyword: str, folded_text: str) -> bool:
    """Katlanmış metinde anahtar kelimeyi sözcük sınırlı arar."""
    return re.search(keyword_pattern(keyword), folded_text) is not None


def _fold_all(mapping: dict[str, list[str]]) -> dict[str, frozenset[str]]:
    """Sözlükteki tüm anahtar ifadeleri katlanmış forma indirger.

    Varyantlar (ör. 'taşıt' ve 'tasit') katlama sonrası aynı dizeye düşer;
    frozenset mükerrer sayımı engeller — aksi halde bir eşleşme iki kez
    sayılıp güven skorunu şişirirdi.
    """
    return {k: frozenset(tr_fold_ascii(v) for v in vals)
            for k, vals in mapping.items()}


# Eşleşmede kullanılacak önceden katlanmış görünümler (modül yüklenirken bir kez).
FOLDED_TYPE_HINTS: dict[str, frozenset[str]] = _fold_all(TYPE_HINTS)
FOLDED_FIELD_TRIGGERS: dict[str, frozenset[str]] = _fold_all(FIELD_TRIGGERS)
