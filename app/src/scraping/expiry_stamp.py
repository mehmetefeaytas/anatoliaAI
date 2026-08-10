"""Sayfanın kendini "bitmiş" ilan ettiği DAMGA — TEK DOĞRULUK KAYNAĞI.

İlgili: src/scraping/reconcile_stale.py (`verify_stale` — ağdan gelen sayfa)
        scripts/damga_isaretle.py (yerel korpus taraması, ağ yok)
        src/extraction/rules/ihtar.py (ihtar kalıbının tek kaynağı — buradan okunur)
        docs/rapor/suresi-dolmus-damgasi.md (ölçümler)

## Neden ayrı bir modül

`comparison.contradiction._SELF_EXPIRED` deseni **koruma amaçlı**dır: bir bulguyu
BASTIRMAK için kullanılır, yanlış eşleşmenin bedeli bir bulgunun kaçırılmasıdır.
`reconcile_stale` aynı deseni **karar amaçlı** kullanınca hata yönü tersine
döndü — yanlış eşleşmenin bedeli canlı bir belgenin arşive gömülmesi oldu.

Ölçüldü (2026-08-10, `docs/rapor/bayat-veri-mutabakati.md` §3): o geniş desen,
canlı sayılan 750 `live/` belgesinin ham HTML'inde **190'ında (%25,3)**
ateşliyordu ve üretilen 5 `suresi_dolmus` kararının **5'i de** yanlış pozitifti:

- Türkiye Finans (3): eşleşen şey her sayfada duran `Biten Kampanyalar` **menü
  bağlantısı**; canlı olduğu kesin kontrol sayfalarının 3/3'ü de eşleşiyordu.
- Vakıf Katılım (2): eşleşen şey "kampanyayı durdurma, **sona erdirme** …
  hakkını saklı tutar" — yani "bitti"nin TAM TERSİ, standart ihtar cümlesi.

Bu yüzden karar için ayrı, DAR bir desen gerekiyor ve o desen tek yerde
yaşamalı: `ihtar.py`'nin başına yazılan ders bu depoda beş kez tekrarlandı —
desen iki kopya olarak yaşarsa biri güncellenir, öteki güncellenmez.

## Ayırt edici dilbilgisi

İhtar cümlesi **mastar/isim-fiil** kullanır: "sona erdirme", "sonlandırma",
"durdurma", "iptal etme" — bankanın SAKLI TUTTUĞU haklar.
Damga **bitmiş kip** kullanır: "sona ermiştir", "sona erdi", "süresi dolmuştur".
`_DAMGA` yalnız ikinci kümeyi tanır; ayrım deseni dar tutmanın temelidir.

## Üç koruma (hepsi ölçümle gerekçelendirildi)

1. **Temiz metin şartı.** Desen ham HTML'de DEĞİL, `collector._extract_main_text`
   çıktısında aranır. Bu tek başına yanlış pozitifi bitirmez (Türkiye Finans'ın
   menü bağlantısı temiz metinde de duruyor; onu 2 numaralı değil, DAR DESEN
   eliyor) — aldığı şey KARARIN MARKUP KAZALARINA BAĞLI OLMAMASI:
   - Ham HTML'de arama, aynı geniş desenle 772 belgede 195 eşleşme veriyordu;
     temiz metinde 276. Aradaki **81 belgenin tamamı Vakıf Katılım**: damga
     HTML'de etiket/`&nbsp;` ile bölündüğü için `\\s+` tutmuyor, yani karar
     sessizce KAÇIRIYORDU.
   - Ters yönde tek bir belge bile yok (HTML'de eşleşip metinde eşleşmeyen: 0).
   - Ham HTML ayrıca `href=".../Biten-Kampanyalar.aspx"` gibi içerik OLMAYAN
     dizgeleri arama uzayına sokar; bunlar sayfanın durumu hakkında hiçbir
     zaman kanıt olamaz.
2. **İhtar vetosu (`ihtar.IHTAR_RE`).** Eşleşmeden SONRA, aynı cümle içinde ve
   `_IHTAR_PENCERE` karakter içinde bir ihtar kalıbı geliyorsa eşleşme, ihtarın
   saydığı hak kalemlerinden biridir → reddedilir. Veto YÖNLÜdür: ihtar ÖNCE
   gelirse damga ayrı bir ifadedir ve vetolanmaz. Yönsüz (cümle bazlı) veto
   Dünya Katılım'da 1 gerçek damgayı düşürüyordu ("… hakkını saklı tutar Paraf
   Kampanyaları Sona erdi Bitiş Tarihi: 31 Temmuz 2026" — nokta yok).
3. **Kuyruk bloğu vetosu.** "Diğer Kampanyalar" başlığından sonra gelen damga
   BAŞKA bir kampanyaya aittir. Albaraka'nın kampanya sayfaları kendi durumunu
   yazmıyor; damga yalnız alttaki "Diğer Kampanyalar" kartlarında görünüyor.
   Bu koruma olmadan 10 Albaraka belgesi (BOSCH, MediaMarkt, Dyson kartları
   yüzünden) yanlışlıkla bitmiş sayılıyordu.

## Ölçülen yanlış pozitif oranı (772 `live/` belge, 2026-08-10)

| Desen | Eşleşen belge | Elle bakılan yanlış pozitif |
|---|---:|---|
| geniş (`_SELF_EXPIRED`), ham HTML | 195 | menü + ihtar kaynaklı, ayrımı yok |
| geniş, temiz metin | 276 | ihtar kaynaklı |
| orta (`kampanya … sona er/sonlandır`) + ihtar vetosu | 328 | 97 (Kuveyt Türk'ün "kampanyayı sonlandırabilir"i) |
| **dar + 3 koruma** | **221** | **0** (elle bakıldı, bkz. rapor) |
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

from ..extraction.rules.ihtar import IHTAR_RE
from ..normalization.normalize import normalize_date

#: Damga kalıbı — DAR. Her alternatif gerçek korpustan alınmıştır:
#:   1. "Bu kampanya sona ermiştir."               (albaraka)
#:   2. "Kampanya 24-05-2026 Tarihinde Sona Ermiştir."  (ziraat-katilim)
#:   3. "Kampanya Süresi Dolmuştur"                (vakif-katilim, dunya-katilim)
#:   4. "Sona erdi  Bitiş Tarihi: 31 Temmuz 2026"  (dunya-katilim)
#: Çıplak "sona erdi" / "biten kampanya" BİLEREK dışarıda: ilki ihtar
#: cümlesindeki "sona erdirme"nin ön ekiyle, ikincisi menü bağlantısıyla eşleşir.
_DAMGA = re.compile(
    r"(?:bu\s+)?kampanya(?:s[ıi]|m[ıi]z)?\s+sona\s+ermi[şs]tir"
    r"|tarihinde\s+sona\s+ermi[şs]tir"
    r"|kampanya\s+s[üu]resi\s+(?:dolmu[şs]tur|sona\s+ermi[şs]tir)"
    r"|sona\s+erdi\b[^\w]{0,40}biti[şs]\s+tarihi",
    re.IGNORECASE)

#: Sayfanın sonundaki "başka kampanyalar" bloğunun başlığı.
_KUYRUK_BASLIK = re.compile(r"(di[ğg]er|benzer|ilgili|ba[şs]ka)\s+kampanyalar",
                            re.IGNORECASE)

#: Cümle/öbek sınırı — ihtar vetosunun kapsamını sınırlar.
_SINIR = re.compile(r"[.!?\n;]")

#: İhtar vetosunun bakacağı karakter penceresi (eşleşmeden SONRA).
_IHTAR_PENCERE = 120

#: gg.aa.yyyy / gg-aa-yyyy / gg/aa/yyyy / "31 Temmuz 2026" / yyyy-aa-gg
_TARIH_SRC = (r"\d{4}-\d{1,2}-\d{1,2}"
              r"|\d{1,2}[-./]\d{1,2}[-./]\d{4}"
              r"|\d{1,2}\s+[A-Za-zÇĞİÖŞÜçğıöşü]+\s+\d{4}")

#: Tarih YALNIZCA damgaya YAPIŞIKSA okunur. "Damganın yakınında ilk tarih"
#: kuralı denendi ve ÖLÇÜLDÜ: Vakıf Katılım'ın 26 tarihli belgesinin 3'ünde
#: kampanyanın BAŞLANGIÇ tarihi bitiş sanılıyordu ("… Kampanya Detayları
#: 15 Ekim 2024 - 31 Mayıs 2025 …" → 2024-10-15). Yakınlık, aidiyet değildir;
#: yanlış tarih yazmaktansa `None` yazılır (CLAUDE.md §19).
#:   "Kampanya 30-04-2026 Tarihinde Sona Ermiştir"  → damgadan ÖNCE, yapışık
#:   "Sona erdi Bitiş Tarihi: 31 Temmuz 2026"       → damgadan SONRA, yapışık
_TARIH_ONCE = re.compile(rf"({_TARIH_SRC})[\s.,]*$")
_TARIH_SONRA = re.compile(rf"^[\s:.,–—-]*({_TARIH_SRC})")

#: Yapışıklık penceresi — araya en fazla bu kadar karakter (iki nokta, boşluk)
#: girebilir. Bir cümle sığmayacak kadar dar tutuldu.
_YAPISIK = 24


@dataclass(frozen=True)
class ExpiryStamp:
    """Belgede bulunan "bu kampanya bitmiştir" damgası ve kanıtı."""

    phrase: str          # eşleşen ifade (birebir)
    quote: str           # eşleşmeyi çevreleyen alıntı — kanıt
    span_start: int      # temiz metindeki konum
    span_end: int
    end_date: Optional[str] = None   # ISO-8601, okunabiliyorsa

    def to_json(self) -> dict[str, object]:
        return {
            "phrase": self.phrase,
            "quote": self.quote,
            "span_start": self.span_start,
            "span_end": self.span_end,
            "end_date": self.end_date,
        }


def _kuyruk_basi(text: str) -> int:
    """"Diğer Kampanyalar" kuyruk bloğunun başladığı konum (yoksa `len(text)`).

    Yalnızca metnin İKİNCİ YARISINDAKİ son başlık kuyruk sayılır. Ziraat
    Katılım'ın sayfaları aynı ifadeyi ÜST gezinti çubuğunda da kullanıyor
    ("Tüm Kampanyalar … Diğer Kampanyalar 1 …", 193. karakter); ilk başlıktan
    kesmek o bankanın 102 gerçek damgasının hepsini düşürürdü.
    """
    son: Optional[re.Match[str]] = None
    for m in _KUYRUK_BASLIK.finditer(text):
        son = m
    if son is None or son.start() < len(text) // 2:
        return len(text)
    return son.start()


def _ihtar_izliyor(text: str, m: re.Match[str]) -> bool:
    """Eşleşmeden sonra, aynı öbek içinde bir ihtar kalıbı geliyor mu?

    Geliyorsa eşleşme "…, sona erdirme, … hakkını saklı tutar" listesinin bir
    kalemidir — kampanyanın bittiğini DEĞİL, bankanın bitirme hakkını anlatır.
    """
    kuyruk = text[m.end(): m.end() + _IHTAR_PENCERE]
    kes = _SINIR.search(kuyruk)
    if kes:
        kuyruk = kuyruk[: kes.start()]
    return bool(IHTAR_RE.search(kuyruk))


def _iso(ham: str) -> Optional[str]:
    # `normalize_date` gg-aa-yyyy biçimini tanımıyor (ISO ile karışmasın diye);
    # ziraat-katilim damgası tam bu biçimde — tireyi noktaya çevir.
    return normalize_date(
        re.sub(r"^(\d{1,2})-(\d{1,2})-(\d{4})$", r"\1.\2.\3", ham.strip()))


def _bitis_tarihi(text: str, m: re.Match[str]) -> Optional[str]:
    """Damgaya YAPIŞIK bitiş tarihini ISO-8601 olarak okur (yoksa `None`).

    Tarih bulunamazsa UYDURULMAZ: Vakıf Katılım'ın "Kampanya Süresi Dolmuştur"
    damgası tarih taşımaz; kampanya gövdesindeki tarihi damgaya bağlamak
    ölçülmüş bir hata kaynağıdır (bkz. `_TARIH_ONCE` notu).
    """
    once = _TARIH_ONCE.search(text[max(0, m.start() - _YAPISIK): m.start()])
    if once:
        iso = _iso(once.group(1))
        if iso:
            return iso
    sonra = _TARIH_SONRA.search(text[m.end(): m.end() + _YAPISIK])
    if sonra:
        return _iso(sonra.group(1))
    return None


def find_expiry_stamp(text: str) -> Optional[ExpiryStamp]:
    """Temiz metinde damga arar; bulamazsa `None`.

    Girdi TEMİZ METİN olmalıdır (ham HTML değil) — modül başlığındaki 1. koruma.
    """
    if not text:
        return None
    kuyruk = _kuyruk_basi(text)
    for m in _DAMGA.finditer(text):
        if m.start() >= kuyruk:
            continue          # 3. koruma: başka kampanyanın damgası
        if _ihtar_izliyor(text, m):
            continue          # 2. koruma: ihtar kalıbı
        bas = max(0, m.start() - 60)
        son = min(len(text), m.end() + 60)
        return ExpiryStamp(
            phrase=re.sub(r"\s+", " ", m.group(0)).strip(),
            quote=re.sub(r"\s+", " ", text[bas:son]).strip(),
            span_start=m.start(), span_end=m.end(),
            end_date=_bitis_tarihi(text, m))
    return None


def has_expiry_stamp(text: str) -> bool:
    """Kısa yol: metin kendini bitmiş ilan ediyor mu?"""
    return find_expiry_stamp(text) is not None
