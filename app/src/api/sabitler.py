"""API katmanının sunum sabitleri — `main.py`'den ayrıldı.

## Neden bu modül var

`api/main.py` 2.505 satır ve içindeki `build_app()` tek başına 1.914 satır.
Değerlendirme, bunu "kod yapısının modüler ve okunabilir olması" maddesinin
ihlali olarak işaretledi — haklı olarak: projenin geri kalanı katmanlı
(`extraction/`, `normalization/`, `comparison/`, `db/` ayrı ayrı test
edilebilir), ama API katmanı tek dosyada duruyor.

Bölme KADEMELİ yapılıyor ve bu modül ilk adım. Sıra bilinçli: önce hiçbir
şey import etmeyen SABİTLER ayrılıyor, çünkü dairesel bağımlılık riski
sıfırdır ve davranış birebir korunur. Uç noktaların (endpoint) taşınması
ayrı adımlarda, her adımda tam test paketi koşularak yapılacak — bölme
planı ve uç nokta bağımlılık matrisi `docs/rapor/api-bolme-plani.md`'de.

Bu dosyaya YALNIZCA sunum sabitleri girer: kullanıcıya dönük etiketler ve
arayüz eşikleri. İş kuralı, ölçüm ya da veri erişimi buraya taşınmaz —
o zaman "sabitler" adı yalan olur ve dosya ikinci bir god-module'e döner.
"""

from __future__ import annotations

# Karşılaştırılabilir alanlar — arayüzdeki alan çipleri bu listeden üretilir.
# Etiketler Türkçedir (CLAUDE.md §19: kullanıcıya dönük tüm metinler Türkçe).
#
# Alan adları `extraction/llm/schema.py::EXTRACTION_FIELDS` ile aynı kümedir.
# İkisi ayrışırsa arayüz ya olmayan bir alan için çip basar ya da çıkarılan
# bir alanı hiç göstermez; `/fields` ucu bu yüzden etiketi buradan, alan
# listesini şemadan okur ve eksik etiket için alan adının kendisine düşer.
FIELD_LABELS: dict[str, str] = {
    "kar_payi_orani": "Kâr Payı Oranı",
    "finansman_tutari": "Finansman Tutarı",
    "vade_ay": "Vade (ay)",
    "taksit_sayisi": "Taksit Sayısı",
    "tahsis_ucreti": "Tahsis Ücreti",
    "masraf_durumu": "Masraf Durumu",
    "odul_miktari": "Ödül Miktarı",
    "indirim_orani": "İndirim Oranı",
    "alisveris_puani": "Alışveriş Puanı",
    "kampanya_suresi": "Kampanya Süresi",
    "kampanya_kosullari": "Kampanya Koşulları",
    "hedef_kitle": "Hedef Kitle",
}
