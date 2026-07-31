"""Çelişki tespiti — yenilikçilik özelliği (CLAUDE.md §18, hedef #2).

İlgili: ../../decisions/daraltilmis-yenilikcilik-hedefleri.md (çelişki tespiti #2)
        ../../sorun/farkli-ifade-bicimleri.md
        CLAUDE.md §17 (adil kıyas), §6 (zor anlama vakaları)

İki katman:

- `detect(campaign)`      → **belge içi** çelişkiler (imza korunur, API buna bağlı)
- `detect_across(camps)`  → **belgeler arası** çelişkiler (aynı banka, aynı ürün /
                            aynı kampanya iki farklı sayfada farklı anlatılıyor)

## Tasarım ilkesi: sayı değil doğruluk

Bu modülün değeri bulduğu çelişki SAYISINDA değil, bulduklarının GERÇEK
olmasındadır. Jüri önünde bir hayalet çelişki on gerçek çelişkiden çok zarar
verir. Bu yüzden her kural üç savunmadan geçer:

1. **Kapsam (scope) koruması** — çelişkinin iki tarafı AYNI ŞEY hakkında
   olmalı. Uzun ürün sayfalarında "Havale ücretsizdir" ile "Finansman Tahsis
   Ücreti %0,25" aynı sayfada geçer ama farklı hizmetlerdir. Ölçüm (849 belge,
   2026-07-30): kapsam koruması olmadan üretilen 4 "masrafsız ama ücret var"
   adayının DÖRDÜ DE hayaletti; iki tarafın karakter mesafesi 2.176–6.916'ydı.
   Gerçek (test edilmiş) çelişkilerde bu mesafe 20–55 karakter. Eşik: 400.
2. **Kıyaslanabilirlik koruması** — koşullar farklıysa farklı değer çelişki
   DEĞİLDİR (farklı vade → farklı oran normaldir; banka çalışanına özel kampanya
   oranı ile liste oranı çelişmez). Bkz. `compare.py` `comparable` mantığı.
3. **Normalizasyon** — `%1,89` ile `1.89%` aynı değerdir; karşılaştırma her zaman
   kanonik değer üzerinden yapılır, ham metin üzerinden değil.

## Korpus ölçümü (849 gerçek belge, snapshot 2026-07-30)

`python3 -m src.comparison.scan` ile yeniden üretilir. Aday çelişki türleri
ÖNCE ölçüldü, sonra kural yazıldı; kanıtı olmayan tür için kural yazılmadı.

| Aday tür                                  | Aday | Doğru | Karar     |
|-------------------------------------------|-----:|------:|-----------|
| "masrafsız" iddiası vs pozitif ücret      |    4 |     0 | KORUNDU-1 |
| Süresi dolmuş ama yayında olan kampanya   |   23 |     5 | YAZILDI   |
| Belge içi çelişen kampanya bitiş tarihi   |    1 |     1 | YAZILDI   |
| Belge içi aynı vadeye iki farklı oran     |   15 |     0 | ELENDİ-2  |
| Prosa "N aya kadar" vs tablo max vade     |    6 |     0 | ELENDİ-3  |
| Başlık/URL'deki tutar vs gövdedeki tutar  |    3 |     0 | ELENDİ-4  |
| Belgeler arası aynı ürün farklı oran      |    4 |     0 | YAZILDI-5 |
| Belgeler arası aynı kampanya farklı bitiş |    2 |     0 | YAZILDI-6 |
| Belgeler arası masrafsız vs ücretli       |    0 |     0 | YAZILMADI |

1. Kural korundu ama KAPSAM KORUMASI eklendi; eski kod korpusta 1 bulgu
   veriyordu, elle doğrulamada o da hayalet çıktı (bkz. yukarıdaki 1. madde).
2. Elendi: bu sayfalarda İKİ AYRI TABLO var (segment / tutar dilimi); düz
   metne inince tek tablo gibi görünüyorlar. Çelişki değil, ayrıştırma sınırı.
3. Elendi: tablo, sayfadaki hesaplama aracının varsayılan satırı; ürünün
   vade yelpazesinin tamamı değil.
4. Elendi: üçünde de gövdedeki tutar başka bir cümlenin tutarı.
5. Kural yazıldı ve 4 aday üzerinde koşuyor; dördü de segment kampanyası
   (banka/kamu çalışanına özel) — kıyaslanabilirlik koruması eliyor.
6. Kural yazıldı; iki aday da "Kampanya Süresi Dolmuştur" damgalı ardışık
   sürüm — kendi kendini işaretleyen sayfa çelişki değildir.

Son durum: **6 çelişki** (5 süresi dolmuş + 1 belge içi çelişen bitiş),
altısı da elle doğrulandı; belgeler arası doğrulanmış çelişki 0.

"Süresi dolmuş" kuralının aday elemesi (her adım bir yanlış-pozitif kaynağı):
63 belgede sıkı bitiş iddiası var → 23'ünde bitiş tarihi toplama tarihinden
önce → 20'si kampanya URL'i ve arşiv değil → 6'sı kendini "Sona erdi /
Süresi Dolmuştur" diye işaretlemiyor → 5'i liste sayfası değil → **5 bulgu**.

Belgeler arası verimin sıfır olmasının ölçülmüş sebebi: korpusta 32 çift belge
AYNI `source_url`'i paylaşıyor ve **hiçbirinin metni farklı değil** (byte-özdeş).
Yani bu tek anlık görüntüde (snapshot) bankalar aynı içeriği tutarlı yayınlıyor.
Belgeler arası çelişkinin asıl kaynağı **iki farklı zamandaki snapshot** ya da
ürün sayfasının kampanya sayfasından ayrışması olurdu; kurallar canlıdır ve
ikinci scrape turunda ayrışma olursa tetiklenirler.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Iterable, Optional

from ..normalization.normalize import normalize_date
from ..schemas import Campaign, ExtractedField

# Çelişkinin iki tarafı bu kadar karakterden uzaksa AYNI ŞEY hakkında değildir.
# Ölçümle seçildi (bkz. modül docstring'i): hayaletler 2.176+, gerçekler ≤ 55.
MAX_SCOPE_CHARS = 400


@dataclass
class Evidence:
    """Bir çelişkinin TEK tarafı — jüri "bunu nereden biliyorsun" diye soracak.

    Her taraf hangi belgeden (bank_slug + source_url), hangi alandan
    (field_name), hangi değerle (value / raw_value) ve metnin neresinden
    (source_span + karakter offset'leri) geldiğini taşır.
    """

    bank_slug: str
    source_url: Optional[str] = None
    field_name: Optional[str] = None
    value: Any = None
    raw_value: Optional[str] = None
    source_span: Optional[str] = None
    span_start: Optional[int] = None
    span_end: Optional[int] = None

    @classmethod
    def from_field(cls, campaign: Campaign, f: ExtractedField) -> "Evidence":
        return cls(
            bank_slug=campaign.bank_slug,
            source_url=campaign.source_url,
            field_name=f.field_name,
            value=f.canonical_value,
            raw_value=f.raw_value,
            source_span=f.source_span,
            span_start=f.span_start,
            span_end=f.span_end,
        )

    def to_dict(self) -> dict[str, Any]:
        """API/dashboard için düz sözlük."""
        return {
            "bank": self.bank_slug,
            "source_url": self.source_url,
            "field_name": self.field_name,
            "value": self.value,
            "raw_value": self.raw_value,
            "source_span": self.source_span,
            "span_start": self.span_start,
            "span_end": self.span_end,
        }


@dataclass
class Contradiction:
    """Tespit edilmiş bir çelişki.

    `kind` / `detail` / `fields` geriye uyumluluk için korunur (API ve mevcut
    testler bunlara bağlı). `evidence` iki tarafın da kaynağını taşır;
    `scope` çelişkinin belge içi mi belgeler arası mı olduğunu söyler.
    """

    kind: str
    detail: str
    fields: list[str]
    evidence: list[Evidence] = field(default_factory=list)
    scope: str = "intra"           # "intra" (belge içi) | "cross" (belgeler arası)
    match_key: Optional[str] = None  # cross ise: eşleştirme anahtarı (ürün/kampanya)

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "detail": self.detail,
            "fields": self.fields,
            "scope": self.scope,
            "match_key": self.match_key,
            "evidence": [e.to_dict() for e in self.evidence],
        }


# --------------------------------------------------------------------------- #
# Yardımcılar
# --------------------------------------------------------------------------- #

def _positive(value: Any) -> bool:
    """Değer pozitif bir ücreti mi gösteriyor?

    Tahsis ücreti üç kanonik biçimde gelebilir:
      - para   : {"value": 500.0, "currency": "TRY"}
      - masraf : {"has_fee": True, "amount": 500.0}
      - ORAN   : {"rate": 0.5}        ← oran tablosundan gelir (%0,50)

    `rate` biçimi eskiden atlanıyordu: tablodan gelen ücret hiç görülmüyordu.
    """
    if isinstance(value, dict):
        for key in ("value", "amount", "rate"):
            v = value.get(key)
            if v is not None:
                return bool(v > 0)
        return False
    return bool(isinstance(value, (int, float)) and value > 0)


def _fee_text(value: Any, raw: Optional[str]) -> str:
    """Ücreti insan-okur biçimde yazar (oran mı tutar mı belli olsun)."""
    if isinstance(value, dict) and value.get("rate") is not None:
        return f"%{value['rate']}"
    if raw:
        return raw.strip()[:60]
    return str(value)


def _in_same_scope(a: ExtractedField, b: ExtractedField) -> bool:
    """İki alan metnin AYNI bölümünden mi geliyor?

    Offset'lerden biri yoksa reddetmeyiz (kanıt yok, suçlama yok) — sentetik
    test verisi ve LLM katmanı offset üretmeyebilir. Offset varsa mesafe
    `MAX_SCOPE_CHARS` içinde olmalı.
    """
    if a.span_start is None or b.span_start is None:
        return True
    a0, a1 = a.span_start, (a.span_end if a.span_end is not None else a.span_start)
    b0, b1 = b.span_start, (b.span_end if b.span_end is not None else b.span_start)
    if a1 >= b0 and b1 >= a0:      # kesişiyorlar
        return True
    return min(abs(b0 - a1), abs(a0 - b1)) <= MAX_SCOPE_CHARS


# --------------------------------------------------------------------------- #
# Kampanya geçerlilik tarihi iddiaları
# --------------------------------------------------------------------------- #

_D = (r"(\d{1,2}[./]\d{1,2}[./]\d{4}|\d{4}-\d{1,2}-\d{1,2}|"
      r"\d{1,2}\s+[A-Za-zÇĞİÖŞÜçğıöşü]+\s+\d{4})")

# SIKI kalıplar. Bir belgede onlarca tarih geçer (güncellenme tarihi, ödül
# yükleme tarihi, "31 Ağustos'a kadar tahsil edilmeli" gibi yükümlülükler).
# Yalnız KAMPANYANIN GEÇERLİLİĞİNİ tarif eden tarihler alınır: "kampanya"
# sözcüğü en fazla 80 karakter önde, tarihten sonra "geçerli" ya da açık bir
# "Başlangıç ve Bitiş" başlığı. Gevşek kalıp ölçümde 138 belgede tetikleniyor
# ve büyük kısmı kampanya süresiyle ilgisiz.
_END_PATTERNS: tuple[tuple[re.Pattern[str], int], ...] = (
    (re.compile(rf"kampanya[^.]{{0,80}}?{_D}\s*tarihine\s+(?:kadar|dek)"
                rf"[^.]{{0,40}}?ge[çc]erli", re.IGNORECASE), 1),
    (re.compile(rf"kampanya[^.]{{0,80}}?{_D}\s*[-–—]\s*{_D}\s*tarihleri\s+"
                rf"aras[ıi]nda[^.]{{0,60}}?ge[çc]erli", re.IGNORECASE), 2),
    (re.compile(rf"kampanya\s+ba[şs]lang[ıi][çc]\s*(?:ve\s*)?biti[şs]\s*"
                rf"(?:tarihi\s*)?:?\s*{_D}\s*[-–—]\s*{_D}", re.IGNORECASE), 2),
)

# Banka kendi kendine "bu kampanya bitti" diyorsa bu ÇELİŞKİ DEĞİLDİR — dürüst
# davranmıştır. TÜM metinde aranır, sadece başında değil: Dünya Katılım şablonu
# damgayı sayfanın SONUNA koyuyor ("Kart Kampanyaları Sona erdi Bitiş Tarihi:
# 30 Nisan 2026"). Ölçüm: bu koruma olmadan 20 bulgunun 12'si Vakıf Katılım'ın
# "Kampanya Süresi Dolmuştur" damgalı sayfaları, 3'ü de Dünya Katılım'ın
# "Sona erdi" damgalı sayfalarıydı — hepsi hayalet.
_SELF_EXPIRED = re.compile(
    r"(s[üu]resi\s+dolmu[şs]|sona\s+erdi|sona\s+ermi[şs]|"
    r"biten\s+kampanya|ge[çc]mi[şs]\s+kampanya)", re.IGNORECASE)

_CAMPAIGN_URL = re.compile(r"kampanya", re.IGNORECASE)
_ARCHIVE_URL = re.compile(r"(arsiv|ar[şs]iv|archive|biten)", re.IGNORECASE)

# LİSTE sayfası tespiti — GEVŞEK kalıp, yalnız SAYMAK için kullanılır (buradan
# çelişki üretilmez). Bir sayfada birden çok "kampanya ... <tarih aralığı>" ya da
# "kampanya ... <tarih> tarihine kadar" ifadesi varsa o sayfa TEK bir kampanya
# değil, kampanya LİSTESİDİR; içindeki bir kampanyanın süresi dolmuşsa sayfanın
# tamamı için "süresi dolmuş" demek yanlıştır.
#
# Ölçüm: bu koruma olmadan T.O.M. Bank'ın 4 kampanyalık `kampanyalar.html`
# listesi tek bir "süresi dolmuş kampanya" sanılıyordu (tek yanlış pozitif).
# Sıkı kalıp o sayfada 3 pencerenin yalnız 1'ini görüyor, çünkü diğer ikisi
# "6 Mart-31 Ağustos 2026" gibi yılı paylaşan ya da araya uzun metin giren
# biçimlerde yazılmış — saymak için gevşek, iddia üretmek için sıkı olmak
# gerekiyor.
_VALIDITY_WINDOW = re.compile(
    rf"kampanya[^.]{{0,80}}?(?:{_D}\s*[-–—]\s*{_D}|{_D}\s*tarihine\s+(?:kadar|dek)|"
    rf"\d{{1,2}}\s*[-–—]\s*\d{{1,2}}\s+[A-Za-zÇĞİÖŞÜçğıöşü]+\s+\d{{4}}|"
    rf"\d{{1,2}}\s+[A-Za-zÇĞİÖŞÜçğıöşü]+\s*[-–—]\s*\d{{1,2}}\s+"
    rf"[A-Za-zÇĞİÖŞÜçğıöşü]+\s+\d{{4}})", re.IGNORECASE)


_DATE_ONLY = re.compile(_D)


def _looks_like_listing(text: str) -> bool:
    """Sayfa birden çok kampanyanın geçerlilik penceresini içeriyor mu?

    Pencereler BİTİŞ TARİHİNE göre tekilleştirilir: aynı kampanya süresini iki
    kez yazan sayfa (ör. üstte "1 Ağustos – 31 Aralık 2025", koşullarda
    "01.08.2025-31.12.2025") liste DEĞİLDİR; farklı bitişler taşıyan sayfa
    listedir.
    """
    ends: set[str] = set()
    for m in _VALIDITY_WINDOW.finditer(text):
        isos = [normalize_date(d) for d in _DATE_ONLY.findall(m.group(0))]
        isos = [i for i in isos if i]
        if isos:
            ends.add(max(isos))
    return len(ends) > 1


@dataclass
class EndDateClaim:
    """Metinde açıkça ifade edilmiş bir 'kampanya şu tarihe kadar geçerli' iddiası."""

    iso: str
    raw: str
    span_start: int
    span_end: int
    window: str


def end_date_claims(text: str) -> list[EndDateClaim]:
    """Metindeki KAMPANYA GEÇERLİLİK BİTİŞİ iddialarını döndürür (sıkı kalıp)."""
    out: dict[str, EndDateClaim] = {}
    for pattern, group in _END_PATTERNS:
        for m in pattern.finditer(text):
            iso = normalize_date(m.group(group))
            if iso is None:
                continue
            out.setdefault(iso, EndDateClaim(
                iso=iso, raw=m.group(group),
                span_start=m.start(group), span_end=m.end(group),
                window=re.sub(r"\s+", " ", m.group(0))[:140],
            ))
    return sorted(out.values(), key=lambda c: c.iso)


def _claim_evidence(campaign: Campaign, c: EndDateClaim) -> Evidence:
    return Evidence(
        bank_slug=campaign.bank_slug, source_url=campaign.source_url,
        field_name="kampanya_suresi", value=c.iso, raw_value=c.raw,
        source_span=c.window, span_start=c.span_start, span_end=c.span_end,
    )


# --------------------------------------------------------------------------- #
# Belge içi tespit
# --------------------------------------------------------------------------- #

def detect(campaign: Campaign, as_of: Optional[str] = None) -> list[Contradiction]:
    """Tek kampanya içindeki çelişkileri döndürür.

    `as_of` (ISO tarih, ör. belgenin `scraped_at`'i) verilirse zaman bağımlı
    kural da koşar ("süresi dolmuş ama hâlâ yayında"). Verilmezse o kural
    ATLANIR — çıktının tarihe göre sessizce değişmemesi için varsayılan
    kapalıdır (demo yeniden-üretilebilirliği, CLAUDE.md §11).
    """
    out: list[Contradiction] = []
    out.extend(_rule_fee_claim_vs_fee(campaign))
    out.extend(_rule_conflicting_end_dates(campaign))
    if as_of:
        out.extend(_rule_expired_but_published(campaign, as_of))
    return out


def _rule_fee_claim_vs_fee(campaign: Campaign) -> list[Contradiction]:
    """'masrafsız' iddiası ama pozitif ücret (§18 amiral kuralı).

    Kapsam koruması şart: uzun ürün sayfalarında "Havale ücretsizdir" ile
    "Finansman Tahsis Ücreti %0,25" aynı belgede geçer ve FARKLI hizmetlerdir.
    """
    out: list[Contradiction] = []
    masraf = campaign.get("masraf_durumu")
    tahsis = campaign.get("tahsis_ucreti")
    if not (masraf and isinstance(masraf.canonical_value, dict)):
        return out
    if masraf.canonical_value.get("has_fee") is not False:
        return out

    if tahsis and _positive(tahsis.canonical_value) and _in_same_scope(masraf, tahsis):
        out.append(Contradiction(
            kind="masrafsiz_ama_ucret",
            detail=f"'masrafsız' belirtilmiş ancak tahsis ücreti var "
                   f"({_fee_text(tahsis.canonical_value, tahsis.raw_value)}).",
            fields=["masraf_durumu", "tahsis_ucreti"],
            evidence=[Evidence.from_field(campaign, masraf),
                      Evidence.from_field(campaign, tahsis)],
        ))

    amt = masraf.canonical_value.get("amount")
    if amt and amt > 0:
        out.append(Contradiction(
            kind="masrafsiz_ama_tutar",
            detail=f"'masrafsız' ancak masraf tutarı {amt} olarak görünüyor.",
            fields=["masraf_durumu"],
            evidence=[Evidence.from_field(campaign, masraf)],
        ))
    return out


def _rule_conflicting_end_dates(campaign: Campaign) -> list[Contradiction]:
    """Aynı belgede kampanya için İKİ FARKLI geçerlilik bitiş tarihi.

    Gerçek korpus örneği (albaraka, "Temmuz Ayına Özel Fatura Kampanyası"):
      başlıkta "Kampanya Başlangıç ve Bitiş 01.07.2026 - 31.07.2026",
      koşullarda "Kampanya 31 Temmuz 2027 tarihine kadar geçerlidir."
    Bir yıllık fark; müşteri hangisine güvenecek?
    """
    claims = end_date_claims(campaign.raw_text)
    if len(claims) < 2:
        return []
    lo, hi = claims[0], claims[-1]
    return [Contradiction(
        kind="celisen_kampanya_bitisi",
        detail=f"Kampanyanın geçerlilik bitişi iki farklı tarihle veriliyor: "
               f"{lo.iso} ve {hi.iso}.",
        fields=["kampanya_suresi"],
        evidence=[_claim_evidence(campaign, lo), _claim_evidence(campaign, hi)],
    )]


def _rule_expired_but_published(campaign: Campaign, as_of: str) -> list[Contradiction]:
    """Süresi dolmuş ama sayfa hâlâ yayında ve bunu söylemiyor.

    Koşullar (hepsi zorunlu — her biri ölçülmüş bir yanlış-pozitif kaynağını kapatır):
      1. Belge bir KAMPANYA sayfası (URL'de 'kampanya' geçiyor).
      2. URL arşiv/biten kampanya klasörü DEĞİL.
      3. Metin kendini "süresi dolmuştur" diye işaretlemiyor (banka dürüstse
         çelişki yok).
      4. Belge tek bir kampanyayı anlatıyor — birden çok "Kampanya Koşulları"
         bloğu varsa bu bir LİSTE sayfasıdır, tamamı için hüküm verilemez.
      5. Belgede TEK bir geçerlilik bitiş tarihi var — birden çoksa bu belge-içi
         çelişkidir (`celisen_kampanya_bitisi`), bu kuralın konusu değil.
      6. O tarih `as_of`'tan (belgenin toplandığı gün) önce.
    """
    url = campaign.source_url or ""
    if not _CAMPAIGN_URL.search(url) or _ARCHIVE_URL.search(url):
        return []
    if _SELF_EXPIRED.search(campaign.raw_text):
        return []
    if _looks_like_listing(campaign.raw_text):
        return []
    claims = end_date_claims(campaign.raw_text)
    if len(claims) != 1:
        return []
    c = claims[0]
    if c.iso >= as_of[:10]:
        return []
    return [Contradiction(
        kind="suresi_dolmus_kampanya",
        detail=f"Kampanya {c.iso} tarihinde bitmiş görünüyor ancak sayfa "
               f"{as_of[:10]} itibarıyla yayında ve süresinin dolduğunu belirtmiyor.",
        fields=["kampanya_suresi"],
        evidence=[_claim_evidence(campaign, c)],
    )]


# --------------------------------------------------------------------------- #
# Ürün / kampanya eşleştirme (belgeler arası tespitin ön koşulu)
# --------------------------------------------------------------------------- #

# URL yolunda ürünü TANIMLAMAYAN, sadece gezinme yapısı olan parçalar. Bunları
# elemezsek "kampanya" ya da "bireysel" gibi bir parça yaprak olur ve alakasız
# onlarca sayfa aynı ürün sanılır (ölçüm: başlık tabanlı eşleştirme
# 38 kampanyayı tek "Kampanya" grubunda topladı — saf hayalet fabrikası).
_PATH_STOPWORDS = {
    "sayfalar", "tr", "tr-tr", "en", "index", "default", "detay", "detail",
    "kampanya", "kampanyalar", "bireysel", "kurumsal", "kobi", "ticari",
    "musteri", "kendim-icin", "isim-icin", "urunler", "urun",
}


def product_key(campaign: Campaign) -> Optional[str]:
    """Kampanyanın ÜRÜN/KAMPANYA kimliği — belgeler arası eşleştirme anahtarı.

    Neden URL yaprağı (son anlamlı yol parçası)?

    Üç aday ölçüldü (849 belge):
      - **Başlık** (`<title>`): felaket. "Kampanya", "Detay", "Yardım Merkezi"
        gibi jenerik başlıklar 38 alakasız kampanyayı tek gruba topluyor.
      - **campaign_type + banka**: çok kaba. Bir bankanın 90 ürün sayfası
        8 türe düşüyor; "Konut Finansmanı" ile "2B Finansmanı" aynı grupta.
      - **URL yaprağı**: 71 grup, 40'ı gerçekten farklı metin. Banka kendi
        URL'inde ürünü zaten adlandırıyor (`/finansmanlar/konut-finansmani`),
        bu yüzden en güvenilir sinyal budur.

    Sıkılaştırmalar: gezinme parçaları (`_PATH_STOPWORDS`) atılır, dosya uzantısı
    ve `-2` / `_1` gibi sürüm sonekleri kırpılır, 8 karakterden kısa yapraklar
    (çok jenerik) reddedilir. Anahtar banka ile birlikte kullanılır — farklı
    bankaların aynı ürünü ÇELİŞMEZ, rekabet eder.
    """
    url = campaign.source_url
    if not url or url.startswith("file://"):
        return None
    path = url.split("://")[-1]
    parts = [p for p in path.split("/")[1:] if p]
    if not parts:
        return None
    cleaned: list[str] = []
    for p in parts:
        p = re.sub(r"\.(aspx|html?|php)$", "", p, flags=re.IGNORECASE).lower()
        p = re.sub(r"[-_]\d+$", "", p)
        if p and p not in _PATH_STOPWORDS:
            cleaned.append(p)
    if not cleaned:
        return None
    leaf = cleaned[-1]
    return leaf if len(leaf) >= 8 else None


def group_by_product(
        campaigns: Iterable[Campaign]
) -> dict[tuple[str, str], list[Campaign]]:
    """(banka, ürün_anahtarı) → kampanyalar. Aynı metin bir kez sayılır.

    Metin tekilleştirme şart: korpusta 32 çift belge aynı URL'i paylaşıyor ve
    metinleri byte-özdeş (aynı sayfa iki toplama turunda da indi). Bunları
    ayrı belge sayarsak "iki sayfa" iddiası yanıltıcı olur.
    """
    groups: dict[tuple[str, str], list[Campaign]] = {}
    for c in campaigns:
        key = product_key(c)
        if key is None:
            continue
        bucket = groups.setdefault((c.bank_slug, key), [])
        if any(x.raw_text == c.raw_text for x in bucket):
            continue
        bucket.append(c)
    return {k: v for k, v in groups.items() if len(v) > 1}


# --------------------------------------------------------------------------- #
# Belgeler arası tespit
# --------------------------------------------------------------------------- #

# Kıyaslanabilirlik koruması: bu sözcükleri taşıyan sayfa BELİRLİ BİR KİTLEYE
# özeldir; oranı liste oranıyla kıyaslamak adil değildir (CLAUDE.md §17).
# Ölçüm: bu koruma olmadan Türkiye Finans ihtiyaç finansmanı grubunda 4 "çelişki"
# çıkıyordu; dördü de "banka çalışanlarına özel" / "kamu çalışanlarına özel"
# segment kampanyalarıydı — çelişki değil, farklı koşul.
_SEGMENT_MARKERS = re.compile(
    r"(çalışanlar[ıi]na\s+özel|calisanlarina\s+ozel|emeklilere\s+özel|"
    r"gençlere\s+özel|kamu\s+çalışan|personeline\s+özel|üyelerine\s+özel|"
    r"yeni\s+müşterilere\s+özel|dijital\s+müşterilere\s+özel)", re.IGNORECASE)


def _is_segment_specific(c: Campaign) -> bool:
    return bool(_SEGMENT_MARKERS.search(c.raw_text))


def detect_across(campaigns: Iterable[Campaign]) -> list[Contradiction]:
    """Belgeler arası çelişkiler — aynı banka, aynı ürün, iki farklı sayfa.

    Eşleştirme `product_key()` ile yapılır (gerekçesi orada). Yanlış eşleştirme
    hayalet çelişki üretir, bu yüzden eşleştirme SIKI tutulur ve her kural
    ayrıca kıyaslanabilirlik korumasından geçer.

    Bu snapshot'ta (849 belge, 2026-07-30) **doğrulanmış belgeler arası çelişki
    yok** — sebebi ölçüldü: aynı URL'i paylaşan 32 çift belgenin hiçbirinin
    metni farklı değil. Kurallar yine de canlı: aynı ürünün iki sayfası
    ayrıştığı anda (yeni scrape turu, kampanya güncellemesi) tetiklenirler.
    """
    out: list[Contradiction] = []
    for (bank, key), group in sorted(group_by_product(campaigns).items()):
        out.extend(_cross_rule_rate(bank, key, group))
        out.extend(_cross_rule_end_date(bank, key, group))
    return out


def _cross_rule_rate(bank: str, key: str, group: list[Campaign]) -> list[Contradiction]:
    """Aynı ürün, iki sayfa, farklı kâr payı oranı.

    Adil kıyas garantisi (CLAUDE.md §17):
      - Segmente özel sayfalar (banka çalışanı, emekli...) kıyas dışı.
      - Aralık ile nokta değer: nokta değer aralığın İÇİNDEYSE çelişki yok
        (`%1,89–2,49` içinde `%2,00` tutarlıdır).
      - İki aralık kesişiyorsa çelişki yok.
      - Karşılaştırma kanonik `float` üzerinden — `%1,89` ile `1.89%` aynıdır.
    """
    usable = [c for c in group
              if c.get("kar_payi_orani") is not None and not _is_segment_specific(c)]
    if len(usable) < 2:
        return []
    out: list[Contradiction] = []
    base = usable[0]
    for other in usable[1:]:
        fa, fb = base.get("kar_payi_orani"), other.get("kar_payi_orani")
        if _rate_overlaps(fa.canonical_value, fb.canonical_value):
            continue
        out.append(Contradiction(
            kind="capraz_kar_payi_uyusmazligi",
            detail=f"'{key}' ürünü için iki farklı sayfada kesişmeyen kâr payı "
                   f"oranı yayımlanmış: {_rate_text(fa.canonical_value)} ve "
                   f"{_rate_text(fb.canonical_value)}.",
            fields=["kar_payi_orani"],
            evidence=[Evidence.from_field(base, fa), Evidence.from_field(other, fb)],
            scope="cross",
            match_key=f"{bank}/{key}",
        ))
    return out


def _rate_bounds(value: Any) -> Optional[tuple[float, float]]:
    """Oranı (alt, üst) aralığına indirger. Sayısal değilse None."""
    if isinstance(value, dict) and "min" in value and "max" in value:
        try:
            return float(value["min"]), float(value["max"])
        except (TypeError, ValueError):
            return None
    if isinstance(value, (int, float)):
        return float(value), float(value)
    return None


def _rate_overlaps(a: Any, b: Any) -> bool:
    """İki oran iddiası uyumlu mu? Ölçülemiyorsa UYUMLU sayılır (suçlama yok)."""
    ba, bb = _rate_bounds(a), _rate_bounds(b)
    if ba is None or bb is None:
        return True
    # 0.005 tolerans: %1,89 ile 1.890 aynı değerdir (yuvarlama gürültüsü).
    return ba[0] <= bb[1] + 0.005 and bb[0] <= ba[1] + 0.005


def _rate_text(value: Any) -> str:
    b = _rate_bounds(value)
    if b is None:
        return str(value)
    return f"%{b[0]}" if b[0] == b[1] else f"%{b[0]}–%{b[1]}"


def _cross_rule_end_date(bank: str, key: str, group: list[Campaign]) -> list[Contradiction]:
    """Aynı kampanya iki sayfada farklı geçerlilik bitişiyle yayımlanmış.

    Koruma: iki taraftan biri kendini "Süresi Dolmuştur" diye işaretliyorsa bu
    çelişki DEĞİLDİR — aynı kampanyanın ardışık iki sürümüdür. Ölçüm: bu koruma
    olmadan korpusta 2 bulgu çıkıyor ve elle doğrulamada İKİSİ DE ardışık sürüm
    çıktı (Vakıf Katılım n11 kampanyası: 1–15 Kas 2025 ve 16 Ara 2025 – 7 Oca 2026,
    her iki sayfa da "Kampanya Süresi Dolmuştur" damgalı).
    """
    dated: list[tuple[Campaign, EndDateClaim]] = []
    for c in group:
        if _SELF_EXPIRED.search(c.raw_text):
            continue
        claims = end_date_claims(c.raw_text)
        if len(claims) == 1:
            dated.append((c, claims[0]))
    if len(dated) < 2:
        return []
    out: list[Contradiction] = []
    (c0, k0) = dated[0]
    for (c1, k1) in dated[1:]:
        if k0.iso == k1.iso:
            continue
        out.append(Contradiction(
            kind="capraz_kampanya_bitisi",
            detail=f"'{key}' kampanyası iki sayfada farklı bitiş tarihiyle "
                   f"yayımlanmış: {k0.iso} ve {k1.iso}.",
            fields=["kampanya_suresi"],
            evidence=[_claim_evidence(c0, k0), _claim_evidence(c1, k1)],
            scope="cross",
            match_key=f"{bank}/{key}",
        ))
    return out
