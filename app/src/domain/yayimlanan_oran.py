"""Bankaların KENDİ yayımladığı finansman oranları — kampanya korpusundan AYRI.

İlgili: ../scraping/rates.py (oranları toplayan adaptörler)
        ../chatbot/katilma_orani.py (aynı desen, katılma hesabı tarafı)
        ../api/routers/oranlar.py (uç nokta)

## Niçin ayrı bir kaynak

Kampanya korpusunda `kar_payi_orani` yalnız 164/2.708 belgede (%6,1) geçiyor.
Bu bir çıkarım kusuru DEĞİL — ölçüldü (2026-08-25): EVREN `llm-large` 60 aday
belgede **0**, yerel qwen2.5:7b 30 belgede **0** kabul edilebilir değer üretti.
Metnin kendisi üçüncü kanıt: yakalanmayan yüzdelerin çoğu *gecikme kâr payı
formülü* ("en yüksek cari kâr payı oranlarının %50 fazlası"), kampanyanın
oranı değil.

Bilgi o belgelerde yok. Bankalar onu hesaplama araçlarında ve oran
tablolarında yayımlıyor. Bu modül o kaynağı okuyor.

## Kampanya alanlarına YAZILMIYOR — bilinçli

Bu oranlar `extracted_fields` tablosuna girmiyor. Banka düzeyinde yayımlanmış
bir oranı belirli bir KAMPANYANIN çıkarılmış alanına yazmak, o belgenin
söylemediği bir şeyi ona atfetmek olurdu; kaynak gösterme zinciri (span →
belge) kırılırdı. Bunun yerine kaynak ayrı tutuluyor, ekranda ayrı
etiketleniyor ve kıyasa ayrı bir görünüm olarak giriyor.

Aynı karar katılma oranlarında da verilmişti
([[katilma-orani-iki-ayri-buyukluk]]).

## Kapsam (2026-08-25 ölçümü)

    dunya-katilim           56    ziraat-katilim          31
    turkiye-emlak-katilim   42    albaraka                16
    hayat-finans             3    kuveyt-turk              3
    tom-katilim              3
    TOPLAM                 154 finansman kaydı · 7 banka

Kalan üç banka: Vakıf Katılım oranı yalnız robots-engelli PDF'te yayımlıyor
(elle indirilen belgeden katılma tarafı alındı, finansman tarafı yok),
Türkiye Finans yalnız katılma hesabı tablosu yayımlıyor, Adil Katılım hiç
oran yayımlamıyor. Üçü de kayıtlı, hiçbiri gizlenmiyor.
"""

from __future__ import annotations

import json
import pathlib
from typing import Iterable, Optional, Sequence

#: Oran dosyalarının adı — banka klasörlerinin altında.
DOSYA_ADI = "quotes.jsonl"

#: `RateQuote.kind` değerleri.
KIND_FINANSMAN = "finansman"

_ONBELLEK: Optional[tuple[dict, ...]] = None


def _kok(kok: Optional[pathlib.Path] = None) -> pathlib.Path:
    return kok or pathlib.Path(__file__).resolve().parents[2] / "data" / "raw"


def yukle(kok: Optional[pathlib.Path] = None, *,
          tazele: bool = False) -> tuple[dict, ...]:
    """Tüm bankaların yayımlanmış FİNANSMAN oranları.

    Katılma hesabı kayıtları BU LİSTEYE GİRMEZ: onlar farklı bir büyüklük
    (kazandığınız oran ↔ ödediğiniz oran) ve aynı listede durmaları, iki ters
    yönlü sayının tek sıralamada yarışmasına yol açardı.
    """
    global _ONBELLEK
    if _ONBELLEK is not None and not tazele and kok is None:
        return _ONBELLEK
    taban = _kok(kok)
    out: list[dict] = []
    if taban.exists():
        for yol in sorted(taban.glob(f"*/rates/{DOSYA_ADI}")):
            for satir in yol.read_text(encoding="utf-8").splitlines():
                if not satir.strip():
                    continue
                try:
                    kayit = json.loads(satir)
                except ValueError:
                    continue          # bozuk satır tüm dosyayı düşürmemeli
                if kayit.get("kind") != KIND_FINANSMAN:
                    continue
                if kayit.get("monthly_rate") is None:
                    continue          # oransız kayıt sıralamaya giremez
                out.append(kayit)
    sonuc = tuple(out)
    if kok is None:
        _ONBELLEK = sonuc
    return sonuc


def bankalar(kayitlar: Optional[Iterable[dict]] = None) -> list[str]:
    havuz = kayitlar if kayitlar is not None else yukle()
    return sorted({k.get("bank_slug", "") for k in havuz if k.get("bank_slug")})


def urun_aileleri(kayitlar: Optional[Iterable[dict]] = None) -> list[str]:
    """Ürün adlarından türetilen kaba aile etiketleri."""
    havuz = kayitlar if kayitlar is not None else yukle()
    return sorted({aile(k.get("product_name") or "") for k in havuz} - {""})


#: Ürün adı → aile. Banka adları BİRBİRİNDEN FARKLI yazıyor ("Konut Yeni",
#: "KONUT FINANSMANI (0-10.000.000 TL/1-120 AY))", "Konut Finansmanı (sıfır
#: konut)") ve ham adla gruplamak aynı ürünü üç ayrı satıra bölerdi.
_AILE_IZLERI: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("Konut Finansmanı", ("konut", "arsa", "prefabrik", "işyeri", "isyeri",
                          "gayrimenkul", "kentsel")),
    ("Taşıt Finansmanı", ("taşıt", "tasit", "araç", "arac", "togg",
                          "motosiklet")),
    ("İhtiyaç Finansmanı", ("ihtiyaç", "ihtiyac", "kolay fon", "tüketici",
                            "tuketici", "eğitim", "egitim", "hac", "umre",
                            "yurt", "engelsiz")),
    ("Alışveriş Finansmanı", ("alışveriş", "alisveris", "taksitli",
                              "veresiye", "bana bunu al", "cep telefonu",
                              "teknoloji", "dijital", "ev/ofis")),
)


def aile(urun_adi: str) -> str:
    """Ürün adından aile etiketi; tanınmazsa boş dize.

    Boş dönmek bilinçli: tanınmayan ürünü rastgele bir aileye koymak, kıyası
    sessizce yanlış yapardı. Çağıran onu «Diğer» olarak gösterebilir ama
    KARIŞTIRAMAZ.
    """
    d = (urun_adi or "").casefold()
    for etiket, izler in _AILE_IZLERI:
        if any(iz in d for iz in izler):
            return etiket
    return ""


def siralama(*, urun_ailesi: Optional[str] = None,
             vade_ay: Optional[int] = None,
             kayitlar: Optional[Iterable[dict]] = None) -> list[dict]:
    """Banka başına EN DÜŞÜK aylık oran — finansmanda düşük oran iyidir.

    Katılma hesabında yüksek oran iyiydi; burada TERSİ. İki yüzey aynı kelimeyi
    ("kâr payı oranı") kullandığı için yön açıkça yazılıyor ve tek bir
    sıralama fonksiyonuna emanet edilmiyor.

    Banka başına tek satır: aynı bankanın onlarca ürünü listeyi doldurup
    bankalar arası kıyası görünmez kılardı. Hangi üründen geldiği satırda
    YAZILI.
    """
    havuz = list(kayitlar) if kayitlar is not None else list(yukle())
    if urun_ailesi:
        havuz = [k for k in havuz if aile(k.get("product_name") or "") == urun_ailesi]
    if vade_ay is not None:
        havuz = [k for k in havuz if k.get("term_months") == vade_ay]
    en_iyi: dict[str, dict] = {}
    for k in havuz:
        slug = k.get("bank_slug") or "?"
        oran = k.get("monthly_rate")
        if oran is None:
            continue
        onceki = en_iyi.get(slug)
        if onceki is None or oran < onceki["monthly_rate"]:
            en_iyi[slug] = k
    return sorted(en_iyi.values(), key=lambda k: k["monthly_rate"])


def banka_ozeti(bank_slug: str, *,
                kayitlar: Optional[Iterable[dict]] = None
                ) -> Optional[dict]:
    """Bir bankanın yayımladığı oranların özeti; kaydı yoksa `None`.

    Banka sayfasındaki «ölçülemedi» satırlarının altına konuyor: kampanya
    metninden ölçemediğimiz oranı banka BAŞKA BİR YERDE yayımlıyorsa, o
    ekranda söylenmeli.
    """
    havuz = [k for k in (kayitlar if kayitlar is not None else yukle())
             if k.get("bank_slug") == bank_slug]
    if not havuz:
        return None
    aileler: dict[str, list[dict]] = {}
    for k in havuz:
        aileler.setdefault(aile(k.get("product_name") or "") or "Diğer",
                           []).append(k)
    return {
        "bank_slug": bank_slug,
        "kayit": len(havuz),
        "urun": len({k.get("product_name") for k in havuz}),
        "en_dusuk_oran": min(k["monthly_rate"] for k in havuz),
        "en_yuksek_oran": max(k["monthly_rate"] for k in havuz),
        "kaynak": sorted({k.get("source_url") for k in havuz if k.get("source_url")}),
        "aileler": {
            ad: {
                "kayit": len(v),
                "en_dusuk_oran": min(x["monthly_rate"] for x in v),
                "urunler": sorted({x.get("product_name") or "?" for x in v}),
            } for ad, v in sorted(aileler.items())
        },
    }


def kapsam() -> dict:
    """Hangi bankada kaç kayıt var — eksik olanlar da GÖRÜNÜR."""
    havuz = yukle()
    sayac: dict[str, int] = {}
    for k in havuz:
        sayac[k.get("bank_slug", "?")] = sayac.get(k.get("bank_slug", "?"), 0) + 1
    return {"kayit": len(havuz), "banka": len(sayac),
            "banka_basina": dict(sorted(sayac.items(), key=lambda kv: -kv[1]))}


def vadeler(kayitlar: Optional[Sequence[dict]] = None) -> list[int]:
    havuz = kayitlar if kayitlar is not None else yukle()
    return sorted({k["term_months"] for k in havuz
                   if isinstance(k.get("term_months"), int)})
