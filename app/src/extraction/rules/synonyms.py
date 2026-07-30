"""Faizsiz finans eşanlamlılar / tetikleyici sözlüğü.

İlgili: ../../concepts/katilim-bankaciligi.md, ../../sorun/katilim-bankaciligi-terminoloji-farkliligi.md
Kâr payı = faiz değil (murabaha kâr marjı); finansman = kredi.

Eşleşme `tr_fold_ascii` üzerinden yapılır (bkz. preprocessing/clean.py): hem
ALL-CAPS banka başlıkları hem diakritiksiz yazımlar aynı forma indirgenir.
Bu yüzden aşağıdaki listelerde 'taşıt'/'tasit' gibi varyantlar bulunması
zararsızdır — katlama sonrası set'e indirgenip tek kez sayılırlar.
"""

import re

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
