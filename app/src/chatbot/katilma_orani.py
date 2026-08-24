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
    r"kâr\s+payı\s+hesa[bp]|kar\s+payi\s+hesa[bp]",
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


def katilma_sorusu_mu(soru: Optional[str]) -> bool:
    """Bu soru katılma hesabı ORANI mı istiyor?

    İki koşul birlikte: hesap izi VAR ve oran izi VAR. Hesap izi olmadan
    finansman ürünlerinin oran soruları bu yola düşerdi.
    """
    if not soru or not soru.strip():
        return False
    return bool(_HESAP_IZI.search(soru)) and bool(_ORAN_IZI.search(soru))


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


def _banka_adi(kayit: dict) -> str:
    return kayit.get("bank_name") or kayit.get("bank_slug") or "?"


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
        "",
        f"_Kaynak:_ TKBB Veri Peteği — {kaynak}",
    ]
    return "\n".join(satirlar)
