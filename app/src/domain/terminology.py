"""Katılım finansı terim sözlüğü — yükleyici, yönlendirici, kart üreteci, bekçi.

İlgili: ../../data/terminology/katilim-terim-sozlugu.json (veri),
        ../../docs/terminoloji-sozlugu.md (köken),
        ../extraction/rules/synonyms.py (eşleşme altyapısı yeniden kullanılıyor),
        ../chatbot/safety.py (KAPI 1 — kör değiştirmenin yerini bu modül alır),
        CLAUDE.md §12 (terminoloji ilkesi), §5.5 (şartname kavramları)

## Neden bu modül var

Mentör (eski bankacı, 2026-08-06) kör terim değiştirmenin anlamı bozduğunu
söyledi ve 101 terimlik bir sözlük gönderdi. Bu bir teori değil, bizim kendi
ölçtüğümüz kusurun genellemesi: `safety.py` "Kâr Payı ile Faiz Arasındaki
Farklar" başlığını "Kâr Payı ile Kâr Payı Arasındaki Farklar" yapıyordu.
Sözlüğün `degildir` / `ayrim_notu` alanları bu tek vakanın 101 terimlik
karşılığıdır: bir terimin ne OLMADIĞI makine-okunur biçimde yazılı.

## İki ayrı sözcük dağarcığı — karıştırılmamalı

Bu modülün en kolay yapılacak hatası `halk_dili` alanını kart seçiminde
kullanmaktır. Ölçüldü: `halk_dili` "durum", "konu", "ödeme", "indirim",
"kazanç", "faiz" gibi son derece genel ifadeler taşır. Bunlarla eşleşirsek
neredeyse HER belge `keyfiyet` ve `tediye` kartını çeker ve bağlam bütçesi
gerçek terimlere kalmaz.

    kart seçimi        -> `kanonik` + `varyantlar`  (teknik, seçici)
    kapsam / genişletme -> + `halk_dili`            (günlük dil, kapsayıcı)

`relevant_terms(..., halk_dili=False)` varsayılanı bu yüzden dardır.

## Bağlam bütçesi

Sözlüğün tamamı ~76 000 karakter; `OLLAMA_NUM_CTX` 8192 token (Türkçede kabaca
25–30 bin karakter). Tümü prompt'a sığmaz ve Ollama taşan bağlamı **baştan**
sessizce kırpar — yani sistem prompt'unu yok eder. `to_prompt_cards` bu yüzden
karakter bütçesine uyar ve kartı yarıda kesmez.

## Sadeleştirme — ölçülmek için var, kullanılmak için değil

`simplify_text` mentörün D2 önerisinin ("terimi sadeleştirince model daha iyi
anlar") çalıştırılabilir hâlidir: belgedeki fıkhî terim, sözlüğün `resmi_tr` /
`halk_dili` karşılığıyla DEĞİŞTİRİLİR. mentörün maili bunun anlamı
bozduğunu söylüyor. İki iddia otoriteyle değil ÖLÇÜMLE ayrılır; bu yüzden
sadeleştirme bir ablasyon KOLU olarak kodda vardır ve varsayılan yol değildir
(bkz. `docs/rapor/o1-terim-deneyi.md`).

Değiştirme `synonyms.keyword_pattern` üzerinden sözcük sınırlıdır. Çıplak
`str.replace` KULLANILMAZ: korpusta ölçülmüş biçimde çöküyordu ('fon' deseni
'fonksiyon'u yakalıyor, korpusun %48'i sahte "Konut Finansmanı" çıkıyordu) ve
Mentörün uyardığı kelime birebir "fon"dur.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from typing import Iterable, Optional

from ..extraction.rules.synonyms import keyword_pattern, matches
from ..preprocessing.clean import tr_fold_ascii

#: Sözlüğün repodaki varsayılan yeri. Modüle göre çözülür — çalışma dizinine
#: bağımlı olmak testleri ve CLI'ları kırardı.
VARSAYILAN_YOL = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "data", "terminology", "katilim-terim-sozlugu.json")

#: Kart üretiminde varsayılan karakter bütçesi (~8 kart).
VARSAYILAN_BUTCE = 3000

#: Kart seçiminde yok sayılan eşleşmeler. ŞU AN BOŞ ve bu kasıtlı: `halk_dili`
#: zaten varsayılan olarak dışarıda, teknik `varyantlar` listesi ise ölçüldü ve
#: gürültü üretmedi (bkz. tests/test_terminology.py::TestGercekKorpus).
#:
#: Özellikle "faiz" BURAYA KONMAMALI: bir kampanya metni "faiz" diyorsa `riba`
#: kartını çekmesi tam olarak istediğimiz şeydir — projedeki en pahalı
#: terminoloji tuzağı odur.
_GURULTU: frozenset[str] = frozenset()


@dataclass(frozen=True)
class TermEntry:
    """Sözlükteki tek bir terim.

    Bilinmeyen alanlar sessizce atlanır (ileri uyumluluk) — `load_banks`
    kalıbının aynısı. Eksik zorunlu alan kaydı DÜŞÜRÜR ve sayılır.
    """

    id: str
    kanonik: str
    tanim: str
    kategori: str = ""
    tip: str = ""
    resmi_tr: str = ""
    en: str = ""
    sade_aciklama: str = ""
    ayrim_notu: str = ""
    kaynak: str = ""
    risk_notu: str = ""
    varyantlar: tuple[str, ...] = ()
    halk_dili: tuple[str, ...] = ()
    degildir: tuple[str, ...] = ()
    iliskili: tuple[str, ...] = ()

    def anahtarlar(self, halk_dili: bool = False) -> tuple[str, ...]:
        """Eşleşmede aranacak ifadeler. Sıra deterministik, mükerrer yok."""
        ham = [self.kanonik, *self.varyantlar]
        if halk_dili:
            ham.extend(self.halk_dili)
        gorulen: list[str] = []
        for k in ham:
            katli = tr_fold_ascii(k or "").strip()
            if katli and katli not in gorulen:
                gorulen.append(katli)
        return tuple(gorulen)


@dataclass
class Violation:
    """Çıktı bekçisinin bulduğu tek bir terminoloji ihlali."""

    term_id: str
    kural: str
    kanit: str
    aciklama: str
    severity: str = "orta"


# --------------------------------------------------------------------------- #
# Yükleme
# --------------------------------------------------------------------------- #

_ZORUNLU = ("id", "kanonik", "tanim")
_ALANLAR = frozenset(f.name for f in TermEntry.__dataclass_fields__.values())
_LISTE_ALANLARI = ("varyantlar", "halk_dili", "degildir", "iliskili")

#: (yol -> girdiler) önbelleği. Sözlük değişmez bir veri artefaktıdır; her
#: çağrıda diskten okumak çıkarım hattını gereksiz yavaşlatırdı.
_ONBELLEK: dict[str, tuple[TermEntry, ...]] = {}

#: Son yüklemede düşürülen bozuk kayıt sayısı. Sessiz düşürme yok — çağıran
#: taraf (CLI, lint) bunu raporlayabilsin diye tutulur.
DUSURULEN: dict[str, int] = {}


def _kayit_coz(ham: dict) -> Optional[TermEntry]:
    if not isinstance(ham, dict):
        return None
    if any(not isinstance(ham.get(k), str) or not ham.get(k) for k in _ZORUNLU):
        return None
    kwargs = {k: v for k, v in ham.items() if k in _ALANLAR}
    for alan in _LISTE_ALANLARI:
        deger = kwargs.get(alan) or ()
        if isinstance(deger, str):          # tek değer liste yerine yazılmışsa
            deger = [deger]
        kwargs[alan] = tuple(str(x) for x in deger if isinstance(x, (str, int)))
    for alan in ("kategori", "tip", "resmi_tr", "en", "sade_aciklama",
                 "ayrim_notu", "kaynak", "risk_notu"):
        if not isinstance(kwargs.get(alan), str):
            kwargs[alan] = ""
    return TermEntry(**kwargs)


def load_terminology(path: Optional[str] = None) -> tuple[TermEntry, ...]:
    """Sözlüğü yükler (önbellekli). Dosya yoksa boş demet döner.

    Boş demet dönmek kasıtlı: terim sözlüğü bir ZENGİNLEŞTİRMEDİR, zorunlu bir
    bağımlılık değil. Dosya bir dağıtımda eksikse çıkarım hattı çökmemeli,
    sözlüksüz (bugünkü) davranışına düşmelidir.
    """
    # realpath: sembolik bağ çözülmezse aynı dosya iki önbellek girdisi
    # alır (macOS /var -> /private/var). Testte yakalandı.
    yol = os.path.realpath(path or VARSAYILAN_YOL)
    if yol in _ONBELLEK:
        return _ONBELLEK[yol]
    try:
        with open(yol, encoding="utf-8") as fh:
            ham = json.load(fh)
    except (OSError, json.JSONDecodeError):
        _ONBELLEK[yol] = ()
        DUSURULEN[yol] = 0
        return ()
    if not isinstance(ham, list):
        _ONBELLEK[yol] = ()
        DUSURULEN[yol] = 0
        return ()
    girdiler: list[TermEntry] = []
    dusurulen = 0
    gorulen_id: set[str] = set()
    for kayit in ham:
        e = _kayit_coz(kayit)
        if e is None or e.id in gorulen_id:
            dusurulen += 1
            continue
        gorulen_id.add(e.id)
        girdiler.append(e)
    _ONBELLEK[yol] = tuple(girdiler)
    DUSURULEN[yol] = dusurulen
    return _ONBELLEK[yol]


def onbellegi_temizle() -> None:
    """Testler için — sözlüğü diskten yeniden okumaya zorlar."""
    _ONBELLEK.clear()
    DUSURULEN.clear()


# --------------------------------------------------------------------------- #
# Yönlendirici — hangi terimler bu belgede geçiyor
# --------------------------------------------------------------------------- #

#: Sözlüğün kendi diliyle "bu terim üsluptur, anlam taşımaz" diyen ifadeler.
#: Girdi id'si sabitlemiyoruz: sözlük büyüdüğünde yeni üslup terimleri
#: kendiliğinden kapsanır.
_USLUP_RE = re.compile(r"kayipsiz sadelestirilebilir|"
                       r"anlam kaybi olmadan|kategori 2")


def _uslup_terimi(e: TermEntry) -> bool:
    """Karta değmeyen saf üslup terimi mi?

    Ölçüldü: filtresiz koşuda 120 belgenin 22'sinde EN SIK çekilen terim
    `isbu` oldu ("işbu" = "bu"). Kartı modele hiçbir şey öğretmez ama bütçe
    yer. Ayrım taşıyan üslup terimleri (`muaccel`/`müeccel` ters anlam,
    `tanzim tarihi` != vade) `degildir`/`risk_notu` sayesinde ELENMEZ.
    """
    if e.degildir or e.risk_notu:
        return False
    return bool(_USLUP_RE.search(tr_fold_ascii(e.ayrim_notu)))


def _es_anlamli(a: TermEntry, b: TermEntry) -> bool:
    """İki girdi karşılıklı olarak birbirinin varyantı mı?

    Ölçüldü: `sukuk` ve `kira-sertifikasi` aynı belgede iki ayrı kart
    harcıyordu; sözlüğün kendisi "ikisi eş anlamlıdır" diyor. Karşılıklılık
    şartı dar tutuldu — tek yönlü varyant ilişkisi (ör. bir üst kavramın alt
    kavramı anması) eş anlamlılık sayılmaz.
    """
    av = {tr_fold_ascii(x) for x in a.varyantlar}
    bv = {tr_fold_ascii(x) for x in b.varyantlar}
    return (tr_fold_ascii(a.kanonik) in bv and tr_fold_ascii(b.kanonik) in av)


def _oncelik(e: TermEntry) -> tuple:
    """Bütçe dolduğunda hangi kart kalsın.

    Sıra: önce açık tehlike (`risk_notu`), sonra karışma riski (`degildir`),
    sonra daha spesifik terim (uzun kanonik). `id` son bağ çözücü — sıralama
    TOTAL olmalı, aksi halde aynı belge iki koşuda farklı kart üretir ve
    ölçüm kolu yeniden üretilemez hale gelir.
    """
    return (0 if e.risk_notu else 1,
            0 if e.degildir else 1,
            -len(e.kanonik),
            e.id)


def relevant_terms(text: str,
                   limit: int = 8,
                   halk_dili: bool = False,
                   entries: Optional[Iterable[TermEntry]] = None,
                   ) -> list[TermEntry]:
    """Metinde FİİLEN geçen terimler — deterministik, LLM yok.

    Eşleşme `synonyms.matches()` üzerinden sözcük sınırlıdır. Bu yeniden
    kullanım kritik: düz alt-dize eşleşmesi ölçülmüş biçimde çöküyordu
    ('fon' -> 'fonksiyon', 'ev' -> 'devam'), ki mentörün uyardığı kelime de
    birebir "fon".
    """
    girdiler = tuple(entries) if entries is not None else load_terminology()
    if not text or not girdiler:
        return []
    katli = tr_fold_ascii(text)
    bulunan = [e for e in girdiler
               if not _uslup_terimi(e)
               and any(a not in _GURULTU and matches(a, katli)
                       for a in e.anahtarlar(halk_dili))]
    bulunan.sort(key=_oncelik)

    # Eş anlamlı çiftten yalnız önceliklisi kalır; liste zaten sıralı olduğu
    # için ilk gelen kazanır ve sonuç deterministiktir.
    secili: list[TermEntry] = []
    for e in bulunan:
        if any(_es_anlamli(e, s) for s in secili):
            continue
        secili.append(e)
    return secili[:limit] if limit and limit > 0 else secili


def expand_query(soru: str, limit: int = 4,
                 entries: Optional[Iterable[TermEntry]] = None) -> list[str]:
    """Kullanıcının günlük dilini kanonik terimlere bağlar (RAG genişletme).

    Burada `halk_dili` AÇIKTIR — amacın tersi: "faizsiz tahvil" diyen
    kullanıcıyı `sukuk`a, "kefil olmak" diyeni `kefalet`e taşımak.
    """
    return [e.kanonik for e in relevant_terms(
        soru, limit=limit, halk_dili=True, entries=entries)]


# --------------------------------------------------------------------------- #
# Kart üreteci — sistem prompt'una enjekte edilen metin
# --------------------------------------------------------------------------- #

def _kart(e: TermEntry) -> str:
    satirlar = [f"- {e.kanonik}"]
    if e.degildir:
        satirlar.append(f"  DEĞİLDİR: {', '.join(e.degildir)}.")
    if e.ayrim_notu:
        satirlar.append(f"  Ayrım: {e.ayrim_notu}")
    if e.risk_notu:
        satirlar.append(f"  DİKKAT: {e.risk_notu}")
    if len(satirlar) == 1 and e.tanim:   # ayrımı yoksa hiç değilse tanımı ver
        satirlar.append(f"  Tanım: {e.tanim}")
    return "\n".join(satirlar)


def to_prompt_cards(entries: Iterable[TermEntry],
                    budget_chars: int = VARSAYILAN_BUTCE) -> str:
    """Terimleri sistem prompt'una girecek kartlara çevirir.

    Alan sırası `kanonik -> degildir -> ayrim_notu -> risk_notu`; `tanim` en
    sona düşer ve yalnız ayrım yoksa yazılır. Gerekçe: model tanımı zaten
    biliyor, bilmediği AYRIMDIR — "sukuk nedir" değil, "sukuk tahvil değildir".

    Bütçe aşılırsa kart YARIDA KESİLMEZ, o kart hiç yazılmaz. Yarım bir
    "DEĞİLDİR:" satırı modele yanlış bilgi verirdi.
    """
    parcalar: list[str] = []
    kullanilan = 0
    for e in entries:
        kart = _kart(e)
        maliyet = len(kart) + 1
        if parcalar and kullanilan + maliyet > budget_chars:
            continue
        parcalar.append(kart)
        kullanilan += maliyet
    return "\n".join(parcalar)


def cards_for(text: str, limit: int = 8,
              budget_chars: int = VARSAYILAN_BUTCE) -> str:
    """`relevant_terms` + `to_prompt_cards` kısayolu."""
    return to_prompt_cards(relevant_terms(text, limit=limit),
                           budget_chars=budget_chars)


# --------------------------------------------------------------------------- #
# Çıktı bekçisi — üret/denetle/yeniden üret döngüsünün "denetle" adımı
# --------------------------------------------------------------------------- #

def _kelime_deseni(kelimeler: tuple[str, ...]) -> re.Pattern:
    """İfade listesini `keyword_pattern` kuralıyla tek desene çevirir.

    Neden elle `\\b...\\b` yazılmıyor: Türkçe sondan eklemeli. Testte ölçüldü —
    elle yazılan `\\bfarkli\\b` "farklıdır"ı KAÇIRIYORDU ve bekçi
    "Sukuk ... tahvilden farklıdır" cümlesini, yani bizim DOĞRU çıktımızı,
    ihlal sayıyordu. `keyword_pattern` bu kuralı zaten ölçülmüş biçimde
    taşıyor: kısa anahtar iki taraftan, uzun anahtar soldan sınırlı.
    """
    return re.compile("|".join(keyword_pattern(k) for k in kelimeler))


#: Eşitleme iddiası işaretçileri. "sukuk bir tür tahvildir" gibi.
_ESITLEME_RE = _kelime_deseni((
    "yani", "demektir", "anlamina gelir", "es anlamli", "ayni sey",
    "bir tur", "bir cesidi", "olarak da bilinir", "diger adiyla",
    "yerine gecer", "gibi calisir", "benzeri", "muadili", "karsiligi"))

#: Karşıtlık işaretçileri. Bunlar varsa cümle AYRIMI anlatıyordur — yani bizim
#: İSTEDİĞİMİZ çıktıdır ve işaretlenmemelidir. `safety.py`'deki
#: `_CONTRAST_REPLACEMENTS` dersinin sözlük tarafındaki karşılığı.
#:
#: Liste bilinçli olarak DAR: yalnız "bu o değildir" diyen işaretçiler var.
#: Salt bağlaçlar (ama, fakat, ancak) dışarıda, çünkü "Sukuk bir tür tahvildir
#: AMA faizsizdir" gerçek bir ihlaldir ve yakalanmalıdır.
_KARSITLIK_RE = _kelime_deseni((
    "degil", "farkli", "farki", "fark", "aksine", "karistirilmamali",
    "karistirilmaz", "karistirmayin", "yanlistir", "kullanilmamali",
    "ayrim", "ayrilir", "ayridir", "bagimsiz", "zit", "karsit"))

#: Kesin fıkhî hüküm ifadeleri — tartışmalı yapılarda yasak.
_HUKUM_RE = _kelime_deseni((
    "caizdir", "caiz degildir", "helaldir", "haramdir", "mesrudur",
    "uygundur", "uygun degildir", "gunahtir", "sakincasi yoktur"))

#: Somut para/oran ifadesi — değişken limitlerde yasak.
_RAKAM_RE = re.compile(r"(?:\d[\d.,]*\s*(?:tl|₺|lira|bin|milyon)|%\s*\d)")

#: `risk_notu` metninden türetilen davranış bayrakları. Kod terim id'si
#: sabitlemez; sözlük büyüdüğünde yeni terimler kendiliğinden kapsanır.
_DEGISKEN_TUTAR_RE = re.compile(r"degisken|sabit (?:bir )?rakam")
_HUKUM_YASAK_RE = re.compile(r"danisma kurulu|hukum vermemeli|tartismali")

#: Eşitleme iddiasının aranacağı pencere (karakter). Cümle sınırı yerine
#: pencere: cevaplar çoğu zaman tek uzun cümle kuruyor.
_PENCERE = 160

#: `keyword_pattern` sonuçları — bekçi her cevapta 101 girdiyi tarar.
_DESEN_ONBELLEK: dict[str, str] = {}


def _desen(anahtar: str) -> str:
    d = _DESEN_ONBELLEK.get(anahtar)
    if d is None:
        d = keyword_pattern(anahtar)
        _DESEN_ONBELLEK[anahtar] = d
    return d


def _pencere_al(katli: str, konum: int) -> str:
    bas = max(0, konum - _PENCERE // 2)
    return katli[bas:konum + _PENCERE // 2]


def output_violations(text: str,
                      entries: Optional[Iterable[TermEntry]] = None,
                      ) -> list[Violation]:
    """Üretilen cevapta terminoloji ihlali ara.

    Üç kural, üçü de sözlükten TÜRETİLİR (kodda terim listesi yok):

    K1  `degildir` eşitlemesi — "sukuk bir tür tahvildir". Mentörün maildeki
        "dönüşte fon ya da bono yazmak da yanlış" uyarısının karşılığı.
    K2  değişken tutara sabit rakam — TMSF limiti, nisap.
    K3  tartışmalı yapıda kesin hüküm — teverruk, urbûn, îne, hîle.

    K1'de karşıtlık kapısı zorunludur: "sukuk tahvil DEĞİLDİR" bizim doğru
    çıktımızdır ve işaretlenirse bekçi kendi doğru cevabımızı bloklar.
    """
    girdiler = tuple(entries) if entries is not None else load_terminology()
    if not text or not girdiler:
        return []
    katli = tr_fold_ascii(text)
    ihlaller: list[Violation] = []

    for e in girdiler:
        konum = -1
        for anahtar in e.anahtarlar():
            if anahtar in _GURULTU:
                continue
            m = re.search(_desen(anahtar), katli)
            if m:
                konum = m.start()
                break
        if konum < 0:
            continue
        pencere = _pencere_al(katli, konum)

        # K1 — degildir eşitlemesi
        if _ESITLEME_RE.search(pencere) and not _KARSITLIK_RE.search(pencere):
            for yanlis in e.degildir:
                y = tr_fold_ascii(yanlis).strip()
                if y and matches(y, pencere):
                    ihlaller.append(Violation(
                        e.id, "degildir_esitleme", pencere.strip(),
                        f"'{e.kanonik}' ile '{yanlis}' eşitlenmiş. "
                        f"{e.ayrim_notu or 'Bu ikisi aynı şey değildir.'}",
                        "yuksek"))
                    break

        # K2 — değişken tutara sabit rakam
        if e.risk_notu and _DEGISKEN_TUTAR_RE.search(tr_fold_ascii(e.risk_notu)):
            if _RAKAM_RE.search(pencere):
                ihlaller.append(Violation(
                    e.id, "degisken_tutara_sabit_rakam", pencere.strip(),
                    f"'{e.kanonik}' için somut rakam verilmiş. {e.risk_notu}",
                    "yuksek"))

        # K3 — tartışmalı yapıda kesin hüküm
        if e.risk_notu and _HUKUM_YASAK_RE.search(tr_fold_ascii(e.risk_notu)):
            if _HUKUM_RE.search(pencere):
                ihlaller.append(Violation(
                    e.id, "tartismali_yapida_hukum", pencere.strip(),
                    f"'{e.kanonik}' tartışmalı bir yapıdır; kesin hüküm "
                    f"verilemez. {e.risk_notu}", "yuksek"))

    return ihlaller


# --------------------------------------------------------------------------- #
# Sadeleştirme — mentör D2 kolunun çalıştırılabilir hâli
# --------------------------------------------------------------------------- #

#: Konum korumalı katlamada karşılığı olmayan karakterin yerine yazılan im.
#: NUL hiçbir desende geçmez, dolayısıyla yanlış eşleşme üretemez.
_HIZALI_YEDEK = "\x00"


def _hizali_katla(text: str) -> str:
    """`tr_fold_ascii`nin KONUM KORUYAN sürümü.

    Neden ayrı bir fonksiyon: `tr_fold_ascii` NFKD ayrıştırması yaptığı için
    bazı karakterlerde uzunluğu değiştirir (gold v2'nin 48 belgesinden 1'inde
    ölçüldü). Katlanmış metinde bulunan bir eşleşmenin konumu, özgün metne
    birebir denk düşmezse yanlış aralığı değiştiririz — sessiz bozulma.

    Bu yüzden katlama KARAKTER KARAKTER yapılır ve tek karaktere inmeyen
    girdilerde ilk karaktere düşülür (hiç karşılığı yoksa `_HIZALI_YEDEK`).
    Sonuç `tr_fold_ascii`den nadiren ayrışır; ayrıştığı yerde eşleşme kaçar,
    ki bu güvenli yöndür — uydurma değişiklik yapmaktansa değiştirmemek.
    """
    parcalar: list[str] = []
    for ch in text:
        f = tr_fold_ascii(ch)
        parcalar.append(f if len(f) == 1 else (f[0] if f else _HIZALI_YEDEK))
    return "".join(parcalar)


@dataclass(frozen=True)
class Replacement:
    """Sadeleştirmenin tek bir değişikliği — ve o değişikliğin teşhisi."""

    term_id: str
    start: int
    end: int
    kaynak: str
    hedef: str
    alan: str                       # "resmi_tr" | "halk_dili"
    degildir_cokmesi: bool = False
    karsitlik_baglami: bool = False
    tekrar_cokmesi: bool = False
    baglam: str = ""

    @property
    def anlam_bozucu(self) -> bool:
        """Sözlüğün KENDİ verisiyle kanıtlanabilir anlam bozulması.

        İki bağımsız kanıt sayılır:

        `degildir_cokmesi` — terim, sözlüğün "bu DEĞİLDİR" dediği kavramla
        değiştirildi (ör. `kar-payi.halk_dili[0]`, aynı girdinin `degildir`
        listesinde de yazılıdır). Bu, mailin "Türkçeleri aynı anlamı replace
        ile taşımıyor" cümlesinin makine-okunur karşılığıdır.

        `tekrar_cokmesi` — hedef ifade zaten pencerede geçiyordu; değişiklik
        cümleyi totolojiye çeviriyor. `safety.py`'nin ölçtüğü vaka budur:
        "Kâr Payı ile Faiz Arasındaki Farklar" -> iki taraf da aynı sözcük.

        `karsitlik_baglami` tek başına bozulma SAYILMAZ: karşıtlık işaretçisi
        taşıyan bir cümlede yapılan her değişiklik zararlı değildir. Ağırlaştırıcı
        bir koşuldur, raporda ayrı sayılır.
        """
        return self.degildir_cokmesi or self.tekrar_cokmesi

    def as_dict(self) -> dict:
        return {"term_id": self.term_id, "start": self.start, "end": self.end,
                "kaynak": self.kaynak, "hedef": self.hedef, "alan": self.alan,
                "degildir_cokmesi": self.degildir_cokmesi,
                "karsitlik_baglami": self.karsitlik_baglami,
                "tekrar_cokmesi": self.tekrar_cokmesi,
                "anlam_bozucu": self.anlam_bozucu,
                "baglam": self.baglam}


@dataclass(frozen=True)
class SimplifyResult:
    """`simplify_text` çıktısı — değişen metin + her değişikliğin künyesi."""

    text: str
    replacements: tuple[Replacement, ...] = ()

    @property
    def bozucu(self) -> tuple[Replacement, ...]:
        return tuple(r for r in self.replacements if r.anlam_bozucu)

    def as_dict(self) -> dict:
        return {"degisim": len(self.replacements),
                "anlam_bozucu": len(self.bozucu),
                "degildir_cokmesi": sum(1 for r in self.replacements
                                        if r.degildir_cokmesi),
                "tekrar_cokmesi": sum(1 for r in self.replacements
                                      if r.tekrar_cokmesi),
                "karsitlik_baglami": sum(1 for r in self.replacements
                                         if r.karsitlik_baglami),
                "resmi_tr": sum(1 for r in self.replacements
                                if r.alan == "resmi_tr"),
                "halk_dili": sum(1 for r in self.replacements
                                 if r.alan == "halk_dili")}


def simplification_target(e: TermEntry, anahtar: str) -> Optional[tuple[str, str]]:
    """`anahtar` yüzeyinin yerine yazılacak sade karşılık, ya da `None`.

    Sıra `resmi_tr` -> `halk_dili`. Gerekçe: `resmi_tr` sözlüğün resmî Türkçe
    karşılığıdır ve D2'nin ilk tercihidir.

    Kritik ayrıntı — ÖZDEŞ karşılık atlanır. Sözlüğün 101 girdisinin çoğunda
    `resmi_tr`, kanonik terimin kendisidir (`Kâr payı` -> `Kâr payı`). Böyle
    bir "değişiklik" hiçbir şey sadeleştirmez; onu bir değişiklik gibi saymak
    sadeleştirme kolunun etkisini gizler. Özdeş olduğunda `halk_dili`ye
    düşülür — ki D2'nin asıl istediği de günlük dildir.

    Bu düşüşün BEDELİ vardır ve deneyin tam olarak ölçtüğü şey odur:
    `kar-payi` girdisinde `halk_dili[0]`, aynı girdinin `degildir` listesinde
    yazılıdır. Yani sözlük, kendi sade karşılığının o terim OLMADIĞINI
    söylemektedir. Kod bunu gizlemez, `degildir_cokmesi` bayrağıyla sayar.
    """
    resmi = tr_fold_ascii(e.resmi_tr).strip()
    if resmi and resmi != anahtar:
        return e.resmi_tr, "resmi_tr"
    for h in e.halk_dili:
        if tr_fold_ascii(h).strip() and tr_fold_ascii(h).strip() != anahtar:
            return h, "halk_dili"
    return None


def simplify_text(text: str,
                  entries: Optional[Iterable[TermEntry]] = None,
                  ) -> SimplifyResult:
    """Belgedeki fıkhî terimleri sade karşılıklarıyla DEĞİŞTİRİR (D2 kolu).

    Bu fonksiyon bir ablasyon kolunun gövdesidir; çıkarım hattının varsayılan
    yolu DEĞİLDİR. Varsayılan yol terimi yerinde bırakıp kartı prompt'a
    enjekte eder (`cards_for`).

    Eşleşme `keyword_pattern` ile sözcük sınırlıdır; çakışan adaylar arasında
    en soldaki, eşitlikte en UZUN olan kazanır, o da eşitse `_oncelik` karar
    verir. Sıralamanın tamamı deterministiktir — aynı belge iki koşuda aynı
    metni üretmezse kol yeniden üretilemez ve ölçüm kanıt olmaktan çıkar.

    Returns:
        `SimplifyResult`. Sözlük yoksa ya da metin boşsa metin AYNEN döner
        (sessiz bozulma yok, sadece değişiklik yok).
    """
    girdiler = tuple(entries) if entries is not None else load_terminology()
    if not text or not girdiler:
        return SimplifyResult(text or "", ())

    katli = _hizali_katla(text)
    adaylar: list[tuple[int, int, TermEntry, str, str, str]] = []
    for e in girdiler:
        if _uslup_terimi(e):
            continue
        for anahtar in e.anahtarlar():
            if anahtar in _GURULTU:
                continue
            hedef = simplification_target(e, anahtar)
            if hedef is None:
                continue
            for m in re.finditer(_desen(anahtar), katli):
                adaylar.append((m.start(), m.end(), e, anahtar, *hedef))

    adaylar.sort(key=lambda a: (a[0], -(a[1] - a[0]), _oncelik(a[2])))

    parcalar: list[str] = []
    kalemler: list[Replacement] = []
    imlec = 0
    for bas, bit, e, _anahtar, hedef, alan in adaylar:
        if bas < imlec:                    # çakışan aday — soldaki kazandı
            continue
        hedef_katli = tr_fold_ascii(hedef).strip()
        pencere = _pencere_al(katli, bas)
        kalemler.append(Replacement(
            term_id=e.id, start=bas, end=bit,
            kaynak=text[bas:bit], hedef=hedef, alan=alan,
            degildir_cokmesi=any(
                matches(tr_fold_ascii(d).strip(), hedef_katli)
                for d in e.degildir if tr_fold_ascii(d).strip()),
            karsitlik_baglami=bool(_KARSITLIK_RE.search(pencere)),
            tekrar_cokmesi=bool(
                hedef_katli
                and re.search(_desen(hedef_katli), pencere) is not None),
            baglam=pencere.strip()))
        parcalar.append(text[imlec:bas])
        parcalar.append(hedef)
        imlec = bit
    parcalar.append(text[imlec:])
    return SimplifyResult("".join(parcalar), tuple(kalemler))


# --------------------------------------------------------------------------- #
# Türetilmiş görünümler — mevcut modüllerin beslenmesi için
# --------------------------------------------------------------------------- #

def scope_terms(entries: Optional[Iterable[TermEntry]] = None,
                min_len: int = 4,
                halk_dili: bool = False) -> tuple[str, ...]:
    """Chatbot kapsam sözlüğüne eklenecek katlanmış ifadeler.

    `safety.py` KAPI 5 bir soruyu "kapsam dışı" sayıp çekimser kalıyor ve
    ölçüldü ki meşru katılım finansı sorularının çoğu bu kapıya takılıyor:
    18 sorudan 14'ü reddediliyordu ('tekâfül', 'muşaraka', 'selem akdi',
    'muacceliyet kaydı'...). Bu, belgede "dürüst eksik #1" olarak işaretli.

    `halk_dili` VARSAYILAN OLARAK KAPALI — ölçümle. Açıkken kapsam dışı
    kontrol kümesinde yanlış pozitif 2/18'den 11/18'e fırlıyor, çünkü
    `halk_dili` "durum", "konu", "kanıt", "belirsizlik" gibi ifadeler taşıyor
    ("Bu durum ne zaman düzelir?" kapsam içi sayılıyordu). Teknik terimler
    kurtarmanın tamamını zaten sağlıyor.

    `safety.py`'nin dosya-I/O yapmama ilkesi korunur — bu fonksiyon ENJEKSİYON
    içindir, `safety.py` içinden import anında çağrılmaz.
    """
    girdiler = tuple(entries) if entries is not None else load_terminology()
    terimler: set[str] = set()
    for e in girdiler:
        for a in e.anahtarlar(halk_dili=halk_dili):
            if len(a) >= min_len and a not in _GURULTU:
                terimler.add(a)
    return tuple(sorted(terimler, key=len, reverse=True))


#: Şartname §5.5 kavramı -> sözlük girdisi. YALNIZ İKİSİ eşleşir ve bu kasıtlı.
#:
#: §5.5'in diğer üç kavramı ('finansman maliyeti', 'masrafsız finansman',
#: 'avantajlı finansman') bir FIKHÎ TERİM değil, kampanya pazarlama ifadesidir;
#: sözlükte karşılıkları yoktur. Onlara zorlama bir eşleme yazmak sözlüğü
#: söylemediği bir şeyi söyler hale getirirdi — `synonyms.TERMINOLOGY_5_5`
#: içindeki elle yazılmış tanımları kalır.
ESLEME_5_5: dict[str, str] = {
    "kar_payi_orani": "kar-payi",
    "katilim_fonu": "katilim-fonu",
}


def terminology_5_5(entries: Optional[Iterable[TermEntry]] = None,
                    ) -> dict[str, dict[str, str]]:
    """§5.5 kavramlarının sözlükten ZENGİNLEŞTİRİLEBİLEN kısmı.

    Dönen sözlük `synonyms.TERMINOLOGY_5_5`'in yerine geçmez, onu tamamlar:
    `ayrim_notu` bugün orada yok ve modelin asıl ihtiyacı olan bilgi odur.
    """
    ind = {e.id: e for e in (entries if entries is not None
                             else load_terminology())}
    cikti: dict[str, dict[str, str]] = {}
    for kavram, term_id in ESLEME_5_5.items():
        e = ind.get(term_id)
        if e is None:
            continue
        cikti[kavram] = {"kanonik": e.kanonik, "tanim": e.tanim,
                         "karistirma": e.ayrim_notu,
                         "degildir": ", ".join(e.degildir)}
    return cikti
