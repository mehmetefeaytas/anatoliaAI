"""Terim sorusuna SÖZLÜKTEN kaynaklı cevap.

İlgili: ../domain/terminology.py (sözlük yükleme, eşleşme)
        ../../data/terminology/katilim-terim-sozlugu.json (101 terim)
        CLAUDE.md §12 (terminoloji %30'luk kalemin kalbi), §19 (kaynaksız
        iddia yasak)

## Ölçülmüş boşluk

Kullanıcı raporu (2026-08-24), iki canlı çıktı:

    "Finansman ne demek"  -> "Bu soru elimdeki verinin kapsamı dışında"
    "Murabaha ne demek"   -> "Bu bilgi verimde yok."

Oysa sözlük 101 terim için TAM kayıt tutuyor: `tanim`, `sade_aciklama`,
`kaynak` (Murabaha -> *AAOIFI Şer'i Standart No. 8; Bankaların Kredi
İşlemlerine İlişkin Yönetmelik*), `risk_notu`, `degildir`, `iliskili`. Veri
vardı; chatbot ona hiç bakmıyordu. Modül tam bu boşluğu kapatıyor.

## Niçin uzak model DEĞİL, sözlük

Terim tanımını bir dil modeline ürettirmek KAYNAKSIZ bir iddia olurdu ve bu
projede yasak. Sözlük ise AAOIFI standardı, BDDK yönetmeliği gibi gerçek
kaynak taşıyor. Terim tanımı, modelin bilmesi gereken değil KAYNAĞIN söylemesi
gereken bir şeydir — üstelik `risk_notu` alanı ("müşteriye anlatırken 'faiz
oranı' değil 'kâr oranı / vade farkı' denmelidir") hiçbir genel modelin
üretemeyeceği kurum bilgisidir.

## Alan sorularını ÇALMAMA kuralı

"Kuveyt Türk kâr payı oranı nedir" bir TERİM sorusu değil, ALAN sorusudur ve
yapısal sorgu yoluna gitmek zorundadır — orada kaynaklı bir DEĞER döner.
Bu yüzden terim yolu iki koşulu birlikte ister: (1) soru bir tanım kalıbı
taşıyacak, (2) soruda banka ya da ürün adı GEÇMEYECEK. İkinci koşul olmadan
bu modül yapısal sorgu yolunun sorularını çalar ve kıyas yeteneği görünmez
hâle gelirdi.
"""

from __future__ import annotations

import re
from typing import Iterable, Optional

from ..domain.terminology import TermEntry, load_terminology, relevant_terms

#: Tanım isteyen kalıplar. Sözcük sınırlı: "nedir" araması "nedirse" gibi
#: bir kelimeye takılmasın.
_TANIM_KALIBI = re.compile(
    r"\bne\s+demek\b|\bnedir\b|\bne\s+anlama\s+gel\w*|\btanım\w*|"
    r"\baçıkla\w*|\bne\s+işe\s+yarar\b",
    re.IGNORECASE)

#: Soruda geçtiğinde bunun bir ALAN/kıyas sorusu olduğunu gösteren izler.
#: Banka adları `banks.yaml`'dan okunmuyor bilerek: bu modül veri tabanına ve
#: yapılandırmaya bağımlı OLMAMALI (saf, hızlı, testte ağsız). Liste kısa
#: tutuluyor ve yalnız ayrımı bozacak kadar geniş.
_ALAN_IZLERI = re.compile(
    # banka adları
    r"\bkuveyt\b|\balbaraka\b|\bziraat\b|\bvakıf\b|\bvakif\b|\bemlak\b|"
    r"\btürkiye finans\b|\bturkiye finans\b|\bt\.?o\.?m\b|\bdünya\b|"
    r"\bdunya\b|"
    # kıyas/listeleme kalıpları
    r"\bhangi bankada\b|\ben yüksek\b|\ben düşük\b|\ben yuksek\b|"
    r"\ben dusuk\b|\bkampanya\w*\b|"
    # ALAN ADLARI — tam ifade. "kâr payı ne demek" bir TERİM sorusudur ve
    # cevaplanır; "kâr payı ORANI nedir" bir ALAN sorusudur ve yapısal sorgu
    # yoluna gitmelidir. Ayrım "oranı" sözcüğünde.
    #
    # Bu blok ölçülmüş bir GÜVENLİK açığını kapatıyor: "Bu üründe masraf
    # durumu nedir, faiz uygulanır mı?" sorusu `nedir` kalıbı yüzünden terim
    # yoluna gidiyordu. Terim yolu alıntı modunda çalıştığı için post-filter
    # atlanıyor ve kaynaktaki yasak terim ekrana sızıyordu
    # (`tests/test_safety.py::test_forbidden_term_in_source_is_filtered_out`).
    r"\bmasraf durumu\b|\bkâr payı oranı\b|\bkar payı oranı\b|"
    r"\btahsis ücreti\b|\bfinansman tutarı\b|\btaksit sayısı\b|"
    r"\bödül miktarı\b|\bvade\w*\b|\boranı nedir\b|"
    # ürün sorgusu kalıpları — tanım değil, o üründe var mı sorusu
    r"\buygulanır mı\b|\balınır mı\b|\bvar mı\b|\bbu üründe\b",
    re.IGNORECASE)


def terim_sorusu_mu(soru: Optional[str]) -> bool:
    """Bu soru bir TERİM tanımı mı istiyor?

    İki koşul birlikte: tanım kalıbı VAR ve alan/kıyas izi YOK. İkincisi
    olmadan "Kuveyt Türk kâr payı oranı nedir" de terim sorusu sayılır ve
    yapısal sorgu yolu devre dışı kalırdı (bkz. modül başlığı).
    """
    if not soru or not soru.strip():
        return False
    if _ALAN_IZLERI.search(soru):
        return False
    return bool(_TANIM_KALIBI.search(soru))


def _sorulan_terim(soru: str, entries: Optional[Iterable[TermEntry]]
                   ) -> Optional[TermEntry]:
    """Sorudaki terimi bulur — eşleşme `terminology` üzerinden, sözcük sınırlı.

    `relevant_terms` yeniden kullanılıyor; ikinci bir eşleşme mantığı yazmak
    iki yerin ayrışması demekti ve o ayrışma sessiz olurdu (ör. varyant
    listesi burada güncellenmeyip orada güncellenirdi).
    """
    bulunan = relevant_terms(soru, limit=4, halk_dili=True, entries=entries)
    return bulunan[0] if bulunan else None


def terim_cevabi(soru: str, *, entries: Optional[Iterable[TermEntry]] = None
                 ) -> Optional[str]:
    """Terim sorusuna sözlükten Markdown cevap; bulunamazsa `None`.

    `None` dönmek bilinçli: çağıran mevcut "bilmiyorum" cevabını verir.
    Sözlükte olmayan bir terim için tanım UYDURMAK, bu modülün var olma
    sebebine aykırıdır — "Müşaraka" sözlükte yok ve cevap da verilmez.
    """
    if not terim_sorusu_mu(soru):
        return None
    girdiler = tuple(entries) if entries is not None else load_terminology()
    e = _sorulan_terim(soru, girdiler)
    if e is None or not (e.tanim or "").strip():
        return None

    satirlar = [f"**{e.kanonik}**", "", e.tanim.strip()]
    if (e.sade_aciklama or "").strip():
        satirlar += ["", f"_Sade anlatım:_ {e.sade_aciklama.strip()}"]
    if (e.resmi_tr or "").strip():
        satirlar += ["", f"_Resmî Türkçe karşılık:_ {e.resmi_tr.strip()}"]
    if e.degildir:
        # "Bu terim şu DEĞİLDİR" ayrımı terminoloji kaleminin kalbi: faiz ile
        # kâr payını karıştıran bir cevap, jürinin ilk yakalayacağı hatadır.
        satirlar += ["", f"_Karıştırılmamalı:_ {', '.join(e.degildir)}"]
    if (e.risk_notu or "").strip():
        satirlar += ["", f"⚠️ {e.risk_notu.strip()}"]
    if e.iliskili:
        satirlar += ["", f"_İlgili terimler:_ {', '.join(e.iliskili)}"]
    # KAYNAK son satır ve KOŞULSUZ: kaydı olmayan bir tanım basılmıyor
    # (yukarıdaki `tanim` kontrolü), kaynağı olmayan tanım ise kaynağının
    # sözlük olduğunu söylüyor. Sessizce kaynaksız bırakmak yasak.
    kaynak = (e.kaynak or "").strip() or "katılım terim sözlüğü (proje verisi)"
    satirlar += ["", f"_Kaynak:_ {kaynak}"]
    return "\n".join(satirlar)
