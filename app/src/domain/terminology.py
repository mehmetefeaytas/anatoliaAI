"""Katılım finansı terim sözlüğü — yükleyici, yönlendirici, kart üreteci, bekçi.

İlgili: ../../data/terminology/katilim-terim-sozlugu.json (veri),
        ../../docs/terminoloji-sozlugu.md (köken),
        ../extraction/rules/synonyms.py (eşleşme altyapısı yeniden kullanılıyor),
        ../chatbot/safety.py (KAPI 1 — kör değiştirmenin yerini bu modül alır),
        CLAUDE.md §12 (terminoloji ilkesi), §5.5 (şartname kavramları)

## Neden bu modül var

Mentör (Cavide Hanım, 2026-08-06) kör terim değiştirmenin anlamı bozduğunu
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
# Türetilmiş görünümler — mevcut modüllerin beslenmesi için
# --------------------------------------------------------------------------- #

def scope_terms(entries: Optional[Iterable[TermEntry]] = None,
                min_len: int = 4) -> tuple[str, ...]:
    """Chatbot kapsam sözlüğüne eklenecek katlanmış ifadeler.

    `safety.py` KAPI 5 bir soruyu "kapsam dışı" sayıp çekimser kalıyor; bugün
    'tekâfül', 'vekâlet akdi' gibi meşru sorular bu kapıya takılıyor
    (belgede 'dürüst eksik #1' olarak işaretli). Burada `halk_dili` AÇIKTIR:
    kapsam kararı kapsayıcı olmalı, kart seçimi seçici.

    `safety.py`'nin dosya-I/O yapmama ilkesi korunur — bu fonksiyon ENJEKSİYON
    içindir, `safety.py` içinden import-anında çağrılmaz.
    """
    girdiler = tuple(entries) if entries is not None else load_terminology()
    terimler: set[str] = set()
    for e in girdiler:
        for a in e.anahtarlar(halk_dili=True):
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
