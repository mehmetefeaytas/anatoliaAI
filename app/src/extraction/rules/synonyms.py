"""Faizsiz finans eşanlamlılar / tetikleyici sözlüğü.

İlgili: ../../concepts/katilim-bankaciligi.md, ../../sorun/katilim-bankaciligi-terminoloji-farkliligi.md
Kâr payı = faiz değil (murabaha kâr marjı); finansman = kredi.
"""

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
