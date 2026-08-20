"""Masraf durumu (masrafsız/ücretli) çıkarımı — AYRI modül.

## Neden bu sınır burada

`extract_masraf`in alan-dışı özne süzgeci (`_ALAN_DISI_OZNE_RE`) ve
muafiyet kalıbı (`_MUAFIYET_RE`/`_ucret_muafiyeti`) yalnız bu alana özgü;
`tahsis_ucreti` görünüşte kardeş alan olsa da (`contradiction.detect()`
ikisini birlikte okur) KENDİ tetikleyici/negasyon mantığını taşıyor ve bu
ikisi hiçbir kod paylaşmıyor — yalnız `_ortak.py`deki genel "kanıt
tümceciği" ve "komşu sütunu kes" yardımcılarını ortak kullanıyorlar.
Bu yüzden iki ayrı dosya: paylaşım YARDIMCI DÜZEYİNDE, ALAN MANTIĞI
düzeyinde değil.
"""

from __future__ import annotations

import re
from typing import Optional

from ...normalization import normalize as N
from ...preprocessing.clean import tr_fold
from ...schemas import ExtractedField
from ._ortak import (
    _cumle_kapsami,
    _field,
    _kanit_araligi,
    _truncate_at_next_column,
    _window,
    logger,
)

# ALAN-DIŞI ÖZNE: "ücretsiz"in nitelediği şey ÜRÜN DEĞİL.
#
# ## Ölçülen kusur (2026-08-12, `data/gold/gold.v2.json`)
#
# `masraf_durumu` 10 yanlış pozitifin **9'unda değer UYDURUYORDU** (gold
# "YOK" diyor). Dokuzun yedisi n>=3'lük iki aileydi ve ikisinde de bedava
# olan şey kampanyanın ürünü değildi:
#
#   4x  "Katılım SMS'i ücretsiz olup; ... Turkcell, Vodafone ..."   -> KANAL
#   3x  "Talebiniz ... otuz (30) gün içinde ücretsiz olarak
#        sonuçlandırılmaktadır."                                    -> YASAL TALEP
#
# Alan bileşik avantaj skorunda ikinci en yüksek ağırlığa sahip (0,20,
# `comparison/compare.py:697`), yani uydurma "masrafsız" doğrudan "En
# Avantajlı" sıralamasına giriyordu.
#
# ## Neden bu kapı meşru iddiayı elemiyor (ölçüldü)
#
# Aynı yordam gold'daki 6 MEŞRU çıkarıma da uygulandı: SMS ailesi 4/4
# halüsinasyonda, **0/6** meşruda; talep ailesi 3/3'e karşı **0/6**.
# Mesafeyle de ayrık: halüsinasyonlarda "SMS" jetonu span'dan 3 karakter
# geride, en yakın meşru vakada 5.222 karakter.
#
# ## Kapsam dışı bırakılan 2 vaka (bilerek)
#
# "TOD ayrıcalığını ücretsiz yaşa" (n=1) ve "Ücretsiz İSPARK Otopark
# Kampanyası" (n=1). İkisi de üçüncü taraf hizmet; kapsam kuralı
# (`ANNOTATION_GUIDE.md` §4) ikisini de dışarıda bırakıyor. Yine de kural
# YAZILMADI ve gerekçe 19 Ağustos'ta DEĞİŞTİ — eskisi artık geçersiz:
#
# * ESKİ gerekçe: "yapısal ikizi gold'da MEŞRU (GastroClub üyeliği …
#   ücretsiz), iki vaka çelişiyor". Bu çelişki HAKEM-03 turunda ÇÖZÜLDÜ:
#   GastroClub kaydı `absent_fields`'a taşındı ve `club|kulüp … üyeliği`
#   kolu yukarıya eklendi. Yani ikiz artık meşru değil.
# * YENİ gerekçe: kuralı yazacak ayırt edici bir sinyal ÖLÇÜLDÜ VE ÇÜRÜDÜ.
#   Hipotez şuydu: "ücretsiz"in yakınında bir ücret KALEMİ adı (ücret,
#   masraf, komisyon, bedel, tahsis, ekspertiz, dosya, işletim, havale,
#   EFT, aidat, harç…) yoksa çıkarma. Gold'da ölçüldü (tetikleyici sözcük
#   pencereden çıkarılarak — ilk ölçüm "ücretsiz" içindeki "ücret"i
#   sayarak yanlış sonuç vermişti):
#
#       meşru çıkarımlarda kalem: 1/5      halüsinasyonlarda: 0/2
#
#   Yani kural halüsinasyonların ikisini de elerdi ama MEŞRU beşin dördünü
#   de elerdi ("masrafsız bankacılık", "masrafsız ekosistem", "PTT
#   ATM'lerinden ücretsiz para çekme", "e-posta üzerinden ücretsiz
#   gönderim"). Ayrım semantiktir: bankacılık hizmeti mi, üçüncü taraf
#   hizmet mi. Regex'le ayırmak için marka adı listesi (TOD, İSPARK,
#   GastroClub, Halalbooking) gömmek gerekirdi — aşağıdaki "Bilerek kapsam
#   dışı" notunun banka adları için verdiği §21 gerekçesinin aynısı.
#
# Kalan iki halüsinasyon bu yüzden BİLİNEREK duruyor ve testte
# (`test_masraf_alan_disi.py`) 2 üst sınırıyla kilitli.
#
# `preprocessing/blocks.py` bu sorun için yazılmış ve docstring'i "KVKK'daki
# ücretsiz" örneğini anıyor; iki sebeple yetmedi: (1) `extract_all` ona hiç
# danışmıyor, (2) danışsaydı da bölge yayılımı (`YAYILIM_BLOK=6`) KVKK
# cümlesinden tam bir blok önce sönüyor. Paylaşılan sabiti değiştirmek
# özet/görünürlük yollarını 1.782 belgede etkileyeceği için burada CÜMLE
# kapsamlı yerel bir kapı seçildi.
_ALAN_DISI_OZNE_RE = re.compile(
    # Kanal: katılım/işlem SMS'inin bedeli ürünün masrafı değildir.
    r"\bsms\b|k[ıi]sa\s*mesaj"
    # Yasal talep: KVKK m.13 başvurusunun ücretsiz sonuçlandırılması.
    r"|(?:talebiniz|talep|ba[sş]vurunuz|ba[sş]vuru)[^.]{0,80}sonu[cç]land[ıi]r"
    # ÜÇÜNCÜ TARAF AVANTAJ PROGRAMI ÜYELİĞİ (HAKEM-03, 19 Ağu 2026).
    #
    # "GastroClub üyeliği şimdi Hayat Finans müşterilerine özel ve ücretsiz!"
    # cümlesinden `masraf_durumu = {has_fee: false, amount: 0}` üretiliyordu
    # ve belge `/compare?field=masraf_durumu` tablosunda **"masrafsız"
    # rozetiyle** görünüyordu. Bir restoran indirim kulübünün üyelik
    # bedelinin sıfır olması, finansmanın ya da hesabın maliyeti hakkında
    # hiçbir şey söylemez — kıyas tablosunda o rozet yanlış bir iddiadır.
    # Kılavuz §4'e eklenen kapsam kuralı ölçütü tek soruyla veriyor: "bu
    # kampanyayı/ürünü alırsam ne kadar masraf öderim?"
    #
    # Kusur önce GOLD'da bulundu (κ turunda `masraf_durumu` κ'sı NEGATİF
    # çıktı, -0,103) ve hakemlikte gold düzeltildi; ardından iki test
    # düşerek motorun DA aynı kapsam hatasını yaptığını gösterdi. Kapı bu
    # yüzden burada.
    #
    # ÖLÇÜLDÜ (data/demo.db, 1782 belge) — desen neden bu kadar dar:
    #   "club|kulüp … üyeliği"          ->  3 belge (2'si masraf üretiyordu:
    #                                      GastroClub + Halalbooking Loyalty
    #                                      Club, ikisi de üçüncü taraf)
    #   "kart|hesap|kredi … üyelik ücreti" -> 19 belge — DOKUNULMADI, çünkü
    #                                      kredi kartı yıllık üyelik ücreti
    #                                      ürünün KENDİ masrafıdır ve kapsam
    #                                      İÇİNDEDİR. Desende ürün öznesi
    #                                      aranmadığı için bu 19 belge
    #                                      eşleşmiyor (ölçüldü).
    r"|(?:club|kul[üu]b[üu]?)\w*[^.\n]{0,30}?[üu]yeli[gğ]i",
    re.IGNORECASE,
)


# MUAFİYET KALIBI — "X ücreti BANKA TARAFINDAN karşılanmaktadır"
#
# ## Sorun
#
# Şartname s.11, B Bankası konut finansmanı metninin son cümlesi birebir:
#
#     "Kampanya kapsamında ekspertiz ücreti banka tarafından karşılanmaktadır."
#
# s.12'deki beklenen çıktı tablosu bu tek cümleden İKİ hücre bekliyor:
# «Kampanya Avantajı» = "Ekspertiz ücreti banka tarafından karşılanıyor" ve
# «Masraf Durumu» = **"Ekspertiz ücretsiz"**. `masraf_durumu` bu cümleden
# hiçbir şey üretmiyordu (ölçüldü: `None`), yani iki hücre birden boş kalıyordu.
#
# Bu bir NEGASYON/muafiyet kalıbıdır ve CLAUDE.md §6 zaten kuralı koyuyor:
# "masrafsız ≠ değer yok, masraf = 0 demek". §10 eşanlamlılar da
# "masrafsız ≈ ücretsiz ≈ dosya masrafı yok" diyor. "Banka tarafından
# karşılanıyor" bu ailenin bir üyesidir: müşteri açısından ücret SIFIRDIR.
#
# `normalize_fee_status` (normalization katmanı) bu kalıbı tanımıyor ve o
# modül bu değişikliğin sahipliği dışında; kapı bu yüzden kural katmanında.
#
# ## Neden ÇOK DAR yazıldı — ölçüm kapıyı zorladı
#
# ÖLÇÜLDÜ (2026-08-16, 1782 belge). Gevşek bir "ücret … karşılanır" kalıbı
# 52 eşleşme/27 belge veriyor ve **baskın özne müşteridir**:
#
#     müşteri 9 · banka 4 · (kiracı, aracı, garantör, ortak, taraflar …)
#     "ekspertiz ücreti MÜŞTERİ tarafından karşılanacaktır"      (cid=867)
#     "Noter Masrafları … MÜŞTERİ tarafından ödenecektir"        (7 belge)
#
# Yani kalıbın çoğunluğu muafiyetin TERSİdir: sözleşme metni ücreti müşteriye
# yükler. Gevşek kural bunları "masrafsız" diye okuyup en ağırlıklı ikinci
# alana (`compare.DEFAULT_WEIGHTS["masraf_durumu"] = 0.20`) yalan yazardı.
#
# Özneyi bankaya sabitlemek de yetmiyor: "banka öznesi + öde" kalıbı korpusta
# 4 eşleşme veriyor ve **4'ü de yanlış** —
#
#     "…bedellerinin Kart Hamilinin bankası tarafından ÖDENMEMESİ"  (olumsuz)
#     "…mal bedelinin bir bankadan ödeneceğinin garantisi"          (akreditif tanımı)
#     "…söz konusu bedel muhabir banka tarafından…" ×2              (muhabir masrafı)
#
# Bu yüzden kapı üç yerden birden sıkıldı: (1) fiil yalnız `karşılan`/
# `üstlenil` — `öde` YOK, dört yanlışın üçü oradan geliyordu; (2) ücret
# sözcüğü ile banka öznesi arasına en fazla 12 karakter; (3) yüklem olumlu
# olmalı. Sonuç: korpusta **0 eşleşme** (12/25/40 karakterlik boşlukların
# hepsinde), şartname cümlesinde **1**. Sıfır burada başarısızlık değil,
# 47 karşıt vakanın hiçbirine dokunulmadığının kanıtıdır.
#
# ## Bilerek kapsam dışı
#
# "Kargo ve sigorta ücretleri **Dünya Katılım** tarafından karşılanacaktır"
# (cid=1668) gerçek bir muafiyet ama özne BANKA ADI. Onu almak için banka
# adlarını gömmek gerekirdi; aynı biçim korpusta bir İŞ İLANINDA da geçiyor
# ("ücreti Kuveyt Türk tarafından karşılanacak MBA", cid=290) ve ikisi
# şekilce ayırt edilemiyor. §21 uyarınca alınmadı.
_MUAFIYET_FIIL = (
    r"(?:kar[şs][ıi]lan|[üu]stlenil)"
    # Yüklem OLUMLU olmalı. Ekler tek tek sayılıyor — `normalize.NEGATION_RE`
    # ile aynı özgüllük disiplini. "karşılanmaktadır" olumlu, "karşılan-MA-
    # maktadır" olumsuz; ikisini genel bir negasyon deseni ayıramaz.
    # Ünlü uyumunun iki kolu da gerekli: "karşılan-MAKTAdır" (kalın) ve
    # "üstlenil-MEKTEdir" (ince). İnce kol olmadan `üstlenil` bacağı ölüydü.
    # Olumsuzları hâlâ tutar: "üstlenil-ME-mektedir" -> "memektedir", ek
    # listesindeki hiçbir kalıpla baştan eşleşmez.
    r"(?:maktad[ıi]r|makta|mektedir|mekte"
    r"|acakt[ıi]r|acak|ecekt[ıi]r|ecek|m[ıi][şs]|mi[şs]|[ıi]yor|[ıi]r|d[ıi])"
)

#: Ücret türünü niteleyen sözcük olamayacaklar — bağlam/işlev sözcükleri.
#: Bunlar olmasa "kampanya kapsamında ekspertiz ücreti" ifadesinden tür
#: "kapsamında" diye okunurdu (ölçüldü).
_UCRET_TURU_DISI = frozenset({
    "kapsaminda", "kapsami", "olarak", "ayrica", "hicbir", "her", "tum",
    "bu", "soz", "konusu", "ilgili", "gerekli", "ise", "ve", "ile", "bir",
    "adet", "toplam", "diger", "asagidaki", "yukaridaki", "tarafindan",
})

_MUAFIYET_RE = re.compile(
    r"(?:(?P<tur>[\wçğıöşüÇĞİıÖŞÜ]+)\s+)?"
    r"(?P<kalem>[üu]cret|masraf|komisyon)\w*"
    r"[^.;\n]{0,12}?\b(?:bankam[ıi]z|banka|kurumumuz|taraf[ıi]m[ıi]z)(?:ca|ce)?\b"
    r"\s*(?:taraf[ıi]ndan|taraf[ıi]nca)?\s*" + _MUAFIYET_FIIL,
    re.IGNORECASE,
)

#: Muafiyeti KOŞULLU kılan ifadeler — cümlede geçiyorsa muafiyet mutlak
#: değildir ve "ücretsiz" diye yazılamaz. "ilk yıl banka tarafından
#: karşılanır" ikinci yıl ücret VAR demektir; §21: şüphedeysen çıkarma.
_MUAFIYET_KOSUL_RE = re.compile(
    r"\bilk\s+\d*\s*(?:y[ıi]l|ay|d[öo]nem)"
    r"|durumunda|halinde|[şs]art[ıi]yla|ko[şs]uluyla|kayd[ıi]yla"
    r"|hariç|d[ıi][şs][ıi]nda",
    re.IGNORECASE,
)


def _ucret_muafiyeti(text: str) -> Optional[tuple[re.Match, Optional[str]]]:
    """"X ücreti banka tarafından karşılanmaktadır" — muafiyet var mı?

    Dönüş: (eşleşme, ücret türü) ya da None. Ücret türü, muafiyetin HANGİ
    kaleme ait olduğunu taşır ("ekspertiz"); şartname s.12 "Ekspertiz
    ücretsiz" diyor, "masrafsız" değil — tür bilgisini düşürmek o hücreyi
    yanlış doldurmak olurdu.
    """
    for m in _MUAFIYET_RE.finditer(text):
        cumle = _cumle_kapsami(text, m.start(), m.end())
        if _MUAFIYET_KOSUL_RE.search(cumle):
            continue
        if _ALAN_DISI_OZNE_RE.search(cumle):
            continue
        ham = m.group("tur")
        tur = None
        if ham is not None and tr_fold(ham).lower() not in _UCRET_TURU_DISI:
            tur = ham.lower()
        logger.debug(
            "masraf_durumu MUAFİYET: kalem=%r tur=%r konum=%d",
            m.group("kalem"), tur, m.start())
        return m, tur
    return None


def extract_masraf(text: str) -> Optional[ExtractedField]:
    """Masraf durumu — negasyon farkında ('masrafsız' = 0, bilgi yok değil).

    Tutar, masraf sözcüğünün YEREL penceresinde aranır; aksi halde metnin
    başka yerindeki bir oran/sayı yanlışlıkla masraf tutarı sanılır.

    TÜM masraf bahisleri taranır (`finditer`), sadece ilki değil. Eskiden
    `re.search` kullanıldığı için sonuç yazım SIRASINA bağlıydı:

        "Masrafsızdır. Tahsis ücreti 500 TL."  -> has_fee=False  ✓ çelişki
        "Tahsis ücreti 500 TL. Masrafsızdır."  -> has_fee=True   ✗ çelişki kaçtı

    Bu alan kampanyanın İDDİASINI taşır. Metinde herhangi bir yerde
    "masrafsız/ücretsiz" iddiası varsa `has_fee=False` döner; gerçekte ücret
    olup olmadığını `tahsis_ucreti` alanı söyler ve uyuşmazlığı
    `contradiction.detect()` yakalar.
    """
    # MUAFİYET ÖNCE TARANIR (bkz. `_MUAFIYET_RE`). Bu da bir `has_fee=False`
    # iddiasıdır ve mevcut sözleşme gereği "masrafsız iddiası sırası ne olursa
    # olsun kazanır"; erken dönmek o kuralla tutarlıdır. Farkı, muafiyetin
    # HANGİ kaleme ait olduğunu (`muaf_ucret`) da taşımasıdır.
    muafiyet = _ucret_muafiyeti(text)
    if muafiyet is not None:
        m, tur = muafiyet
        canon: dict = {"has_fee": False, "amount": 0.0}
        if tur is not None:
            # Ek anahtar TOPLAMSAL: tüketiciler (`compare._composite_numeric`,
            # `chatbot/structured.py`) yalnız `has_fee`/`amount` okuyor.
            canon["muaf_ucret"] = tur
        s, e = m.span()
        return _field("masraf_durumu", m.group(0), canon, _window(text, s, e),
                      span_start=s, span_end=e, trigger_distance=0)

    pat = re.compile(r"(masrafs[ıi]z|ücretsiz|ucretsiz|masraf|tahsis|ücret)",
                     re.IGNORECASE)
    first_positive = None
    for m in pat.finditer(text):
        # ALAN-DIŞI ÖZNE KAPISI (bkz. `_ALAN_DISI_OZNE_RE`).
        #
        # `continue` bilinçli: eşleşme ATLANIR, tarama BİTMEZ. `break` ya da
        # erken `return None` olsaydı, alan-dışı bir cümle belgenin gerçek
        # masraf iddiasını gölgeleyebilirdi — halüsinasyonu susturup bilgi
        # kaybı üretmek kazanç değil takas olurdu. Kilidi:
        # `tests/test_masraf_alan_disi.py::test_ayni_belgede_alan_disi_
        # cumle_MESRU_iddiayi_gizlemez`.
        if _ALAN_DISI_OZNE_RE.search(_cumle_kapsami(text, m.start(), m.end())):
            continue
        # tutar keyword'den SONRA gelir ("tahsis ücreti 500 TL") → ileri pencere.
        # Pencere CÜMLE SINIRINDA kesilir: aksi halde sonraki cümledeki bir sayı
        # ("... alınmaz. Kampanya 31 Aralık 2026") 31 TL'lik hayali bir ücret
        # olarak okunuyordu. Nokta binlik ayırıcı da olduğu için lookaround şart.
        fwd = text[m.start(): min(len(text), m.end() + 40)]
        fwd = re.split(r"(?<!\d)[.;](?!\d)|\n", fwd, maxsplit=1)[0]
        fwd = _truncate_at_next_column(fwd)
        canon = N.normalize_fee_status(fwd)
        if canon is None:
            continue
        if canon.get("has_fee") is False:
            # "masrafsız" iddiası bulundu — sırası ne olursa olsun bu kazanır.
            # Kanıt tetikleyici sözcük DEĞİL, onu taşıyan tümceciktir
            # (gerekçe: `_kanit_araligi`).
            s, e = _kanit_araligi(text, m, fwd)
            return _field("masraf_durumu", text[s:e], canon,
                          _window(text, s, e),
                          span_start=s, span_end=e, trigger_distance=0)
        if first_positive is None:
            first_positive = (m, canon, fwd)

    if first_positive is None:
        return None
    m, canon, fwd = first_positive
    s, e = _kanit_araligi(text, m, fwd)
    return _field("masraf_durumu", text[s:e], canon, _window(text, s, e),
                  span_start=s, span_end=e, trigger_distance=0)
