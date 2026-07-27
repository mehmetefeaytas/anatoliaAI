"""Faizsiz finans eşanlamlılar / tetikleyici sözlüğü.

İlgili: ../../concepts/katilim-bankaciligi.md, ../../sorun/katilim-bankaciligi-terminoloji-farkliligi.md
Kâr payı = faiz değil (murabaha kâr marjı); finansman = kredi.

Eşleşme `tr_fold_ascii` üzerinden yapılır (bkz. preprocessing/clean.py): hem
ALL-CAPS banka başlıkları hem diakritiksiz yazımlar aynı forma indirgenir.
Bu yüzden aşağıdaki listelerde 'taşıt'/'tasit' gibi varyantlar bulunması
zararsızdır — katlama sonrası set'e indirgenip tek kez sayılırlar.
"""

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
    "Yatırım Ürünü": ["yatırım", "yatirim", "katılma hesabı", "altın hesabı", "fon"],
    "Finansman": ["finansman", "kredi"],  # en genel; en sona düşer
}


# Negasyon: "tahsis ücreti ALINMAZ" gibi ifadeler ücretin YOK olduğunu değil,
# SIFIR olduğunu söyler (bkz. ../../decisions/zor-anlama-vakalari-merkezi.md).
# Tek doğruluk kaynağı normalization/normalize.py'dir; burada yalnızca yeniden
# ihraç edilir ki çıkarım ve normalizasyon katmanları AYNI deseni kullansın
# (iki ayrı kopya kaçınılmaz olarak birbirinden ayrışırdı).
NEGATION_RE = _NEGATION_RE


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
