"""Katılma hesabı kâr payı oranı sorusuna TKBB verisinden kaynaklı cevap.

İlgili: ../../scripts/tkbb_guncel_hasat.py (bu modülün okuduğu veriyi üretir)
        ../../scripts/tkbb_karpayi_hasat.py (2012–2025 tarihsel arşiv)
        terim_cevabi.py (aynı desen: kaynaklı, ağsız, alan sorularını çalmaz)

## Ölçülmüş boşluk

Kullanıcı raporu (2026-08-24): *"Katılım hesabında en iyi kâr payı oranını hangi
banka veriyor"* sorusu cevaplanamıyordu. Sebep veri yokluğuydu, hata değil:
kampanya korpusu katılma hesabı getirisini **yayınlamıyor**. Bankalar bu oranı
kampanya metninde değil haftalık oran tablolarında duyurur; TKBB de onları
merkezî olarak toplar.

Veri artık `data/raw/<banka>/rates/tkbb-guncel.jsonl` içinde (TKBB Veri Peteği,
haftalık). Bu modül onu okur ve soruyu kaynaklı cevaplar.

## İKİ BÜYÜKLÜK — aynı sıralamaya sokulamaz

    getiri  'Dağıtılan Kâr Payı Oranları %'  gerçekleşen yıllık getiri (%42,79)
    pay     'Kâr Paylaşım Oranları %'        katılımcıya düşen pay    (%90)

Paylaşım oranı sayısal olarak her zaman getiriden büyüktür. İkisi tek kolonda
yarışırsa "en iyi oran" cevabı anlamsızlaşır — %90'lık bir bölüşüm, %42'lik bir
getiriyi "yenmiş" görünür. Bu yüzden sorunun hangi büyüklüğü istediği AYRICA
belirlenir (`_buyukluk_sec`) ve cevap hangisini sıraladığını yazar.

## Neden yapısal sorgu yolu DEĞİL

`extracted_fields` bir KAMPANYAYA bağlıdır; bu veri ise banka düzeyinde,
haftalık ve kampanyasız. Oraya yazmak, olmayan bir kampanyaya alan uydurmak
olurdu. Ayrıca chatbot yalnız EN SON haftayı kullanır; tarihsel arşiv (210 bin
kayıt) cevabın girdisi değildir.
"""

from __future__ import annotations

import json
import pathlib
import re
from typing import Iterable, Optional, Sequence

#: Sorunun katılma hesabına dair olduğunu gösteren izler. Bu iz ZORUNLUDUR:
#: olmadan "konut finansmanı kâr payı oranı" gibi ALAN soruları bu yola düşer
#: ve yapısal sorgu yolunun işini çalar (bkz. terim_cevabi.py'deki aynı kural).
#: `hesa[bp]` bilerek: Türkçe ünsüz yumuşaması yüzünden kök iki biçimde
#: geçiyor — "vadeli hesaP" ama "katılma hesaBı". Yalnız 'hesab' aramak
#: "vadeli hesap kâr payı oranları" sorusunu kaçırıyordu (ölçüldü, test).
_HESAP_IZI = re.compile(
    r"katıl(?:ma|ım)\s+hesa[bp]|"  # jargon-lint: ok
    r"katilma\s+hesa[bp]|katilim\s+hesa[bp]|"
    # 'mevduat' BİLEREK: katılım bankacılığında yanlış terimdir ve cevapta
    # asla kullanılmaz — ama kullanıcı alışkanlıkla "vadeli mevduat kâr payı"
    # diye sorabilir. Yakalamazsak soru cevapsız kalır; yakalayıp DOĞRU
    # terminolojiyle ("Katılma hesabı") cevaplamak projenin terminoloji
    # hedefidir (CLAUDE.md §12). Bu bir GİRDİ deseni, çıktı metni değil.
    r"vadeli\s+hesa[bp]|vadeli\s+mevduat|birikim\s+hesa[bp]|"
    r"kâr\s+payı\s+hesa[bp]|kar\s+payi\s+hesa[bp]|"
    # 'hesap' sözcüğü OLMADAN da katılma hesabı sorulabiliyor: "katılma oranı",
    # "katılma hesabına kâr payı". Ölçülmüş kusur: "kuveyt türk klasik hesap
    # katılma oranı ne" cevapsız kalıyordu — 'klasik hesap' bir hesap izi
    # değil, 'katılma' ise iz listesinde 'hesab' ile bağlıydı.
    r"katıl(?:ma|ım)\s+oran|katilma\s+oran|katılma\s+kâr|katilma\s+kar",
    re.IGNORECASE)

#: Oran/getiri sorulduğunu gösteren izler.
_ORAN_IZI = re.compile(
    r"\bkâr\s+payı\b|\bkar\s+payı\b|\bkar\s+payi\b|\boran\w*|\bgetiri\w*|"
    r"\bfaiz\w*|\bkazanç\w*|\bkazanc\w*|\bpaylaşım\w*|\bpaylasim\w*",
    re.IGNORECASE)

#: 'pay' (bölüşüm) istendiğini gösteren ifadeler. Yoksa varsayılan 'getiri'dir:
#: kullanıcı "en iyi kâr payı oranı" derken gerçekleşen getiriyi sorar.
_PAY_IZI = re.compile(r"paylaşım\s+oran|paylasim\s+oran|kâra\s+katılma\s+oran|"
                      r"kara\s+katilma\s+oran|bölüşüm|bolusum",
                      re.IGNORECASE)

#: Vade ifadeleri → ay. Sıra önemli: '12 ay' önce eşleşmeli ki '2 ay' yakalamasın.
_VADE_KALIPLARI: tuple[tuple[re.Pattern[str], int], ...] = (
    (re.compile(r"\b(?:1|bir)\s*yıl|\b12\s*ay|\byıllık\b", re.IGNORECASE), 12),
    (re.compile(r"\b6\s*ay|\baltı\s*ay|\b6\s*aylık", re.IGNORECASE), 6),
    (re.compile(r"\b3\s*ay|\büç\s*ay|\b3\s*aylık", re.IGNORECASE), 3),
    (re.compile(r"\b1\s*ay|\bbir\s*ay|\baylık\b", re.IGNORECASE), 1),
)

#: Para birimi ifadeleri → ISO kod. TL varsayılan.
_PARA_KALIPLARI: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\bdolar\w*|\busd\b|\$", re.IGNORECASE), "USD"),
    (re.compile(r"\beuro\w*|\bavro\w*|\beur\b|€", re.IGNORECASE), "EUR"),
    (re.compile(r"\baltın\w*|\baltin\w*|\bgram\b|\bxau\b", re.IGNORECASE), "XAU"),
)

_VERI_ADI = "tkbb-guncel.jsonl"
_ONBELLEK: Optional[tuple[dict, ...]] = None

#: SEGMENT verisi taşıyan dosyalar — bankanın KENDİ yayınından.
#:
#: TKBB her banka için TEK bir temsili oran yayınlıyor; bankalar ise bakiye
#: segmentine göre farklı oran uyguluyor. Ölçüldü (2026-08-24, Kuveyt Türk):
#: TKBB TL paylaşımı 92/93/95/95 diyor, bankanın PDF'i Klasik için 85/86/88/88.
#: Yani **Klasik hesap müşterisi gerçekte %85 alıyor, merkezî veri %92 diyor**
#: (bkz. sorun/merkezi-veri-segment-ayrimini-gizliyor.md).
#:
#: Bu yüzden segment verisi ayrıca okunuyor: soru bir segment adı taşıyorsa
#: doğrudan o tablodan cevaplanır, taşımıyorsa TKBB cevabına segment uyarısı
#: düşer. Uyarı olmadan cevap, küçük bakiyeli kullanıcıya erişemeyeceği bir
#: oranı vaat ediyordu.
_SEGMENT_DOSYALARI = ("kt-paylasim-pdf.jsonl", "quotes.jsonl")
_SEGMENT_ONBELLEK: Optional[tuple[dict, ...]] = None

#: Soruda geçtiğinde belirli bir bakiye segmentinin sorulduğunu gösteren izler.
_SEGMENT_IZI = re.compile(
    r"\bklasik\b|\bgümüş\b|\bgumus\b|\baltın\s+hesa[bp]|\baltin\s+hesa[bp]|"
    r"\bplatin\+?\b|\bsegment\w*|\bbakiye\s+dilim\w*|"
    r"\balternatif\s+yatırım\b|\byatırım\s+hesa[bp]",
    re.IGNORECASE)


def _veri_kok() -> pathlib.Path:
    return pathlib.Path(__file__).resolve().parents[2] / "data" / "raw"


def kayitlari_yukle(kok: Optional[pathlib.Path] = None) -> tuple[dict, ...]:
    """Tüm bankaların güncel oran kayıtlarını okur (süreç ömrü boyunca önbellekli).

    Dosya yoksa boş demet döner — hasat henüz koşmamıştır ve bu bir hata
    değildir; çağıran "veri yok" cevabını verir, uydurmaz.
    """
    global _ONBELLEK
    if kok is None and _ONBELLEK is not None:
        return _ONBELLEK
    taban = kok or _veri_kok()
    birikim: list[dict] = []
    if taban.is_dir():
        for p in sorted(taban.glob(f"*/rates/{_VERI_ADI}")):
            for satir in p.read_text(encoding="utf-8").splitlines():
                if satir.strip():
                    try:
                        birikim.append(json.loads(satir))
                    except json.JSONDecodeError:
                        # Bozuk satır sessizce ATLANIR ama dosya iptal EDİLMEZ:
                        # tek satırlık bir bozulma tüm bankayı görünmez yapmamalı.
                        continue
    sonuc = tuple(birikim)
    if kok is None:
        _ONBELLEK = sonuc
    return sonuc


def segment_kayitlari_yukle(kok: Optional[pathlib.Path] = None
                            ) -> tuple[dict, ...]:
    """Segment taşıyan katılma kayıtlarını okur (süreç ömrü boyunca önbellekli).

    `segment` alanı OLMAYAN kayıtlar atlanır: bu yükleyicinin tek işi bakiye
    segmentine göre değişen oranları getirmek.
    """
    global _SEGMENT_ONBELLEK
    if kok is None and _SEGMENT_ONBELLEK is not None:
        return _SEGMENT_ONBELLEK
    taban = kok or _veri_kok()
    birikim: list[dict] = []
    if taban.is_dir():
        for ad in _SEGMENT_DOSYALARI:
            for p in sorted(taban.glob(f"*/rates/{ad}")):
                for satir in p.read_text(encoding="utf-8").splitlines():
                    if not satir.strip():
                        continue
                    try:
                        d = json.loads(satir)
                    except json.JSONDecodeError:
                        continue
                    if d.get("kind") == "katilma" and (d.get("segment") or "").strip():
                        birikim.append(d)
    sonuc = tuple(birikim)
    if kok is None:
        _SEGMENT_ONBELLEK = sonuc
    return sonuc


def segment_sorusu_mu(soru: Optional[str]) -> bool:
    """Soru belirli bir bakiye segmentini mi soruyor?"""
    return bool(soru and _SEGMENT_IZI.search(soru))


def _segment_uyarisi(bankalar: set) -> Optional[str]:
    """TKBB tek değeri ile bankanın segment oranları arasındaki farkı SÖYLER.

    Uyarı yalnız segment verisi ELİMİZDE olan bankalar cevapta göründüğünde
    basılır — genel bir "belki farklıdır" cümlesi gürültü olurdu; ölçülmüş bir
    fark ise bilgidir.
    """
    kayitlar = segment_kayitlari_yukle()
    if not kayitlar:
        return None
    ilgili = [k for k in kayitlar if k.get("bank_slug") in bankalar
              and k.get("currency") == "TRY" and k.get("buyukluk") == "pay"]
    if not ilgili:
        return None
    oranlar = [k for k in ilgili
               if isinstance(k.get("annual_rate"), (int, float))
               and k.get("term_months")]
    if not oranlar:
        return None
    # AYNI VADEDE karşılaştır. Vadeler karışırsa fark segmentten mi vadeden mi
    # geldiği anlaşılmaz — ilk sürüm 2-6 günlük %75 ile 12 aylık %95'i yan yana
    # koyuyordu ve bu, segment farkını OLDUĞUNDAN BÜYÜK gösteriyordu (§17).
    vade = sorted({k["term_months"] for k in oranlar})[0]
    ayni = [k for k in oranlar if k["term_months"] == vade]
    en_az = min(ayni, key=lambda k: k["annual_rate"])
    en_cok = max(ayni, key=lambda k: k["annual_rate"])
    if en_az["annual_rate"] >= en_cok["annual_rate"]:
        return None
    return (
        "Not: yukarıdaki oranlar bankaların TKBB'ye bildirdiği **tek temsili "
        "değerdir**. Bankalar bakiye segmentine göre farklı oran uygular — "
        f"ölçülmüş örnek ({_banka_adi(en_az)}, {vade} ay, kâr paylaşım oranı): "
        f"{en_az['segment']} **%{en_az['annual_rate']:.0f}** · "
        f"{en_cok['segment']} **%{en_cok['annual_rate']:.0f}**. "
        "Kendi segmentinizin oranını bankanızdan doğrulamanız gerekir; "
        "segment adıyla da sorabilirsiniz.")


#: Ürüne bağlanmadan, KURUM düzeyinde sorulmuş oran soruları.
#:
#: Ölçülmüş kusur (kullanıcı raporu 2026-08-24): *"katılım bankalarındaki kâr
#: payı oranı ne kadar"* RAG'a düşüyordu ve uzak model kaynaksız, belirsiz bir
#: paragraf üretiyordu ("...kesin bir değeri vermek mümkün değil") — oysa
#: elimizde 9 bankanın TKBB oranı DURUYOR. Hesap izi zorunluluğu bu soruyu
#: dışarıda bırakıyordu, çünkü soruda "hesap" sözcüğü hiç geçmiyor.
_KURUM_IZI = re.compile(
    r"katıl(?:ım|im)\s+bank\w*|katilim\s+bank\w*|"
    r"\bhangi\s+katıl(?:ım|im)\s+bank\w*",
    re.IGNORECASE)

#: Soru bir ÜRÜNE bağlanmışsa kurum yolu KAPANIR.
#:
#: Ayrım şart: "katılım bankalarındaki kâr payı oranı" katılma hesabının
#: getirisini sorar; "katılım bankalarında konut finansmanı kâr payı oranı"
#: ise kampanya korpusundaki `kar_payi_orani` alanını sorar ve yapısal sorgu
#: yoluna gitmek zorundadır. İkisi FARKLI büyüklüklerdir — biri kazandığınız,
#: öteki ödediğiniz orandır — ve tek tabloda karışmaları kıyası anlamsız kılar.
_URUN_IZI = re.compile(
    r"\bkonut\b|\btaşıt\b|\btasit\b|\bihtiyaç\b|\bihtiyac\b|"
    r"\bfinansman\w*|\bkredi\w*|\bkart\w*|\bkampanya\w*|"
    r"\bpuan\w*|\bödül\w*|\bodul\w*|\bmasraf\w*|\btahsis\b|"
    r"\btaksit\w*|\bindirim\w*|\balışveriş\b|\balisveris\b",
    re.IGNORECASE)

def katilma_sorusu_mu(soru: Optional[str]) -> bool:
    """Bu soru katılma hesabı ORANI mı istiyor?

    Oran izi HER İKİ yolda da zorunlu. Kalan koşul iki biçimden biri:

    1. **Hesap izi** — "katılma hesabı", "vadeli hesap", "katılma oranı".
       Bu yol dar ve kesin.
    2. **Kurum izi + ürün izi YOK** — "katılım bankalarındaki kâr payı oranı".
       Soru bir ürüne bağlanmadığı sürece kurum düzeyinde sorulan oran,
       katılma hesabının getirisidir. Ürün adı geçtiği an bu yol kapanır ve
       soru yapısal sorguya gider; ayrımın gerekçesi `_URUN_IZI`'nde.

    İkinci yol olmadan elimizdeki 9 bankalık TKBB verisi görünmez kalıyor ve
    soru RAG'a düşüp kaynaksız bir paragrafla cevaplanıyordu.
    """
    if not soru or not soru.strip():
        return False
    if not _ORAN_IZI.search(soru):
        return False
    if _HESAP_IZI.search(soru):
        return True
    return bool(_KURUM_IZI.search(soru)) and not _URUN_IZI.search(soru)


def kurum_yolundan_mi(soru: Optional[str]) -> bool:
    """Soru DAR hesap izi olmadan, yalnız kurum izinden mi geldi?

    Cevaba bir ayrım notu eklemek için: kurum yolundan gelen soru
    belirsizdir ve kullanıcının hangi oranı sorduğunu SÖYLEMEK gerekir.
    """
    if not soru or not katilma_sorusu_mu(soru):
        return False
    return not _HESAP_IZI.search(soru)


def _buyukluk_sec(soru: str) -> str:
    return "pay" if _PAY_IZI.search(soru) else "getiri"


def _vade_sec(soru: str) -> Optional[int]:
    for kalip, ay in _VADE_KALIPLARI:
        if kalip.search(soru):
            return ay
    return None


def _para_sec(soru: str) -> str:
    for kalip, kod in _PARA_KALIPLARI:
        if kalip.search(soru):
            return kod
    return "TRY"


_PARA_ADI = {"TRY": "TL", "USD": "dolar", "EUR": "euro", "XAU": "altın"}
_BUYUKLUK_ADI = {
    "getiri": "dağıtılan kâr payı oranı (gerçekleşen yıllık getiri)",
    "pay": "kâr paylaşım oranı (katılımcıya düşen pay)",
}


#: Slug → ekran adı. Banka PDF'inden gelen kayıtlar `bank_name` taşımıyor ve
#: cevapta "kuveyt-turk" gibi bir slug basmak kullanıcıya dönük metinde kusur.
_SLUG_ADI = {
    "albaraka": "Albaraka Türk", "dunya-katilim": "Dünya Katılım",
    "hayat-finans": "Hayat Finans", "kuveyt-turk": "Kuveyt Türk",
    "tom-katilim": "T.O.M. Katılım", "turkiye-emlak-katilim": "Türkiye Emlak Katılım",
    "turkiye-finans": "Türkiye Finans", "vakif-katilim": "Vakıf Katılım",
    "ziraat-katilim": "Ziraat Katılım", "adil-katilim": "Adil Katılım",
}


def _banka_adi(kayit: dict) -> str:
    ad = (kayit.get("bank_name") or "").strip()
    if ad:
        return ad
    slug = kayit.get("bank_slug") or ""
    return _SLUG_ADI.get(slug, slug or "?")


def _segment_cevabi(soru: str, *, kayitlar: Optional[Iterable[dict]] = None,
                    en_fazla: int = 14) -> Optional[str]:
    """Bakiye segmentine göre oran tablosu; veri yoksa `None`.

    TKBB tablosu yerine bankanın KENDİ yayınından okunur — segment ayrımı
    yalnız orada var. Vade ve para birimi süzgeçleri aynı biçimde uygulanır.
    """
    havuz = (tuple(kayitlar) if kayitlar is not None
             else segment_kayitlari_yukle())
    if not havuz:
        return None
    para = _para_sec(soru)
    vade = _vade_sec(soru)
    secili = [k for k in havuz
              if k.get("currency") == para
              and isinstance(k.get("annual_rate"), (int, float))
              and (vade is None or k.get("term_months") == vade)]
    if not secili:
        return None
    # Vade SÖYLENMEMİŞSE tek bir vadeye indiriliyor: segment kıyası ancak aynı
    # vadede anlamlı. Vadeler karışık gösterilirse "Platin+ %95 (12 ay)" ile
    # "Klasik %85 (1 ay)" yan yana gelir ve fark segmentten mi vadeden mi
    # geldiği anlaşılmaz — §17'deki adil kıyas kuralının aynısı.
    if vade is None:
        mevcut_vadeler = sorted({k.get("term_months") for k in secili
                                 if k.get("term_months")})
        if mevcut_vadeler:
            vade = mevcut_vadeler[0]
            secili = [k for k in secili if k.get("term_months") == vade]
    # Segment başına EN İYİ satır (aynı segment birden çok ürün altında olabilir)
    en_iyi: dict[tuple, dict] = {}
    for k in secili:
        anahtar = (k.get("bank_slug"), k.get("segment"))
        if anahtar not in en_iyi or k["annual_rate"] > en_iyi[anahtar]["annual_rate"]:
            en_iyi[anahtar] = k
    sirali = sorted(en_iyi.values(), key=lambda k: -k["annual_rate"])
    ilk = sirali[0]
    buyukluk = ilk.get("buyukluk") or "pay"
    vade_notu = f"{vade} ay vade" if vade else "tüm vadeler"

    satirlar = [
        f"**Katılma hesabı — bakiye segmentine göre "
        f"{_BUYUKLUK_ADI.get(buyukluk, buyukluk)}, {_PARA_ADI[para]}**",
        f"_{vade_notu} · kaynak: bankanın kendi yayını_",
        "",
        "| Banka | Segment | Oran | Vade |",
        "|---|---|---|---|",
    ]
    for k in sirali[:en_fazla]:
        vd = k.get("term_months")
        satirlar.append(
            f"| {_banka_adi(k)} | {k.get('segment')} | "
            f"%{k['annual_rate']:.2f} | {f'{vd} ay' if vd else k.get('term_label') or '—'} |")
    # Tutarsız kaynak satırı varsa GİZLENMEZ (HARD RULES §4).
    tutarsiz = [k for k in sirali[:en_fazla] if k.get("toplam_tutarsiz")]
    if tutarsiz:
        satirlar += ["", "⚠️ Kaynakta tutarsız satır var: "
                     + ", ".join(f"{k.get('segment')} {k.get('term_label')} "
                                 f"(pay+banka payı = {k.get('toplam'):.0f}, "
                                 "100 olmalı)" for k in tutarsiz[:2])
                     + ". Değer düzeltilmedi, olduğu gibi gösteriliyor."]
    satirlar += [
        "",
        "Not: bu oran bir **bölüşüm** oranıdır — kârın yüzde kaçının "
        "katılımcıya verildiğini gösterir, kazancın kendisi değildir.",
        "",
        f"_Kaynak:_ {ilk.get('source_url') or 'banka yayını'}",
    ]
    return "\n".join(satirlar)


def katilma_cevabi(soru: str, *,
                   kayitlar: Optional[Iterable[dict]] = None,
                   kok: Optional[pathlib.Path] = None,
                   en_fazla: int = 9) -> Optional[str]:
    """Katılma hesabı oranı sorusuna Markdown cevap; veri yoksa `None`.

    `None` dönmek bilinçli: çağıran mevcut "bilmiyorum" cevabını verir. Veri
    olmadan sıralama üretmek bu modülün var olma sebebine aykırıdır.
    """
    if not katilma_sorusu_mu(soru):
        return None
    # SEGMENT DALI: soru bir bakiye segmenti soruyorsa TKBB'nin tek değeri
    # yanlış cevap olur — bankanın kendi tablosundan cevaplanır.
    if kayitlar is None and segment_sorusu_mu(soru):
        seg = _segment_cevabi(soru)
        if seg:
            return seg

    havuz: Sequence[dict] = (tuple(kayitlar) if kayitlar is not None
                             else kayitlari_yukle(kok))
    if not havuz:
        return None

    buyukluk = _buyukluk_sec(soru)
    para = _para_sec(soru)
    vade = _vade_sec(soru)
    secili = [k for k in havuz
              if k.get("buyukluk") == buyukluk
              and k.get("currency") == para
              and (vade is None or k.get("term_months") == vade)]
    if not secili:
        return None

    # Banka başına EN İYİ satır: vade belirtilmemişse bankanın en yüksek oranı
    # temsil eder ve hangi vadede olduğu satırda YAZILIR — vade gizlenirse
    # farklı vadeler aynı kolonda kıyaslanmış olurdu.
    en_iyi: dict[str, dict] = {}
    for k in secili:
        s = k.get("bank_slug", "?")
        if s not in en_iyi or k.get("annual_rate", 0) > en_iyi[s].get("annual_rate", 0):
            en_iyi[s] = k
    sirali = sorted(en_iyi.values(), key=lambda k: -k.get("annual_rate", 0))

    donem = sirali[0].get("period_date", "?")
    kaynak = sirali[0].get("source_url", "TKBB Veri Peteği")
    vade_notu = f"{vade} ay vade" if vade else "her bankanın en yüksek vadesi"

    satirlar = [
        f"**Katılma hesabı — {_BUYUKLUK_ADI[buyukluk]}, {_PARA_ADI[para]}**",
        f"_{donem} haftası · {vade_notu}_",
        "",
        "| # | Banka | Oran | Vade |",
        "|---|---|---|---|",
    ]
    for i, k in enumerate(sirali[:en_fazla], 1):
        oran = k.get("annual_rate")
        satirlar.append(
            f"| {i} | {_banka_adi(k)} | %{oran:.2f} | {k.get('term_months')} ay |")

    bas = sirali[0]
    satirlar += [
        "",
        f"En yüksek: **{_banka_adi(bas)}** — %{bas.get('annual_rate'):.2f} "
        f"({bas.get('term_months')} ay).",
    ]
    if buyukluk == "pay":
        # Bu uyarı olmadan %90'lık bir pay, %42'lik bir getiriyle karıştırılır.
        satirlar += [
            "",
            "Not: bu oran bir **bölüşüm** oranıdır — kârın yüzde kaçının "
            "katılımcıya verildiğini gösterir, kazancın kendisi değildir. "
            "Gerçekleşen getiri için «dağıtılan kâr payı oranı» sorun.",
        ]
    satirlar += [
        "",
        "Not: oranlar **geçmiş dönemde dağıtılan** kâr payıdır; katılma "
        "hesabında getiri garanti edilemez ve anapara da güvence altında "
        "değildir (katılım bankacılığının kâr-zarar ortaklığı esası).",
    ]
    # AYRIM NOTU — soru KURUM düzeyinde geldiyse.
    #
    # "Katılım bankalarındaki kâr payı oranı" iki şeyi birden sorabilir:
    # katılma hesabının getirisi (yukarıdaki tablo) ya da bir finansman
    # ürününün oranı. İkisi ters yönlü büyüklüktür — biri kazandığınız, öteki
    # ödediğiniz. Hangisini cevapladığımızı SÖYLEMEDEN tablo basmak,
    # kullanıcıyı yanlış okumaya bırakır.
    if kurum_yolundan_mi(soru):
        satirlar += [
            "",
            "Not: bu tablo **katılma hesabının** oranıdır — paranızı "
            "yatırdığınızda kazandığınız oran. Bir finansman ürününün "
            "(konut, taşıt, ihtiyaç) kâr payı oranını soruyorsanız ürün "
            "adını yazın; o oran kampanya belgelerinden gelir ve ayrı "
            "sıralanır.",
        ]
    # SEGMENT UYARISI: merkezî veri tek değer taşıyor, banka segment bazında
    # farklı oran uyguluyor. Uyarı olmadan cevap, küçük bakiyeli kullanıcıya
    # erişemeyeceği bir oranı vaat ediyordu.
    if kayitlar is None:
        uyari = _segment_uyarisi({k.get("bank_slug") for k in sirali})
        if uyari:
            satirlar += ["", uyari]
    satirlar += ["", f"_Kaynak:_ TKBB Veri Peteği — {kaynak}"]
    return "\n".join(satirlar)
