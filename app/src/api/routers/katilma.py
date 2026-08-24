"""Katılma hesabı oran uçları — TKBB haftalık verisinin panel yüzeyi.

İlgili: ../../chatbot/katilma_orani.py (aynı veriyi chatbot için okur)
        ../../../scripts/tkbb_guncel_hasat.py (veriyi üreten hasat)
        ../../../../decisions/katilma-orani-iki-ayri-buyukluk.md

## Neden ayrı bir uç

Bu veri `campaigns`/`extracted_fields` modeline girmiyor: banka düzeyinde,
haftalık ve kampanyasız. `/compare` kampanya satırları üzerinde çalışır ve
buraya bir katılma satırı sokmak, olmayan bir kampanyaya alan uydurmak olurdu.

Chatbot bu veriyi zaten cevaplıyordu; panel görmüyordu. Jürinin sohbette
gördüğü bir sıralamayı ekranda bulamaması doğrudan kapsam kaybıdır
(CLAUDE.md §5 — dashboard + chatbot birlikte sunulur).

## İki büyüklük ayrı sorgulanır

`buyukluk=getiri` gerçekleşen yıllık getiriyi (%42,79), `buyukluk=pay`
katılımcıya düşen payı (%90) sıralar. Uç ikisini ASLA aynı listede
döndürmez — pay sayısal olarak getiriden büyüktür ve tek listede "en iyi
oran" yanlış bankayı gösterirdi.
"""

from __future__ import annotations

from typing import Any, Optional

from ...chatbot.katilma_orani import kayitlari_yukle

#: Kabul edilen değerler. Serbest bırakılmıyor: yazım hatası sessizce boş
#: liste döndürür ve arayüz "veri yok" sanır.
BUYUKLUKLER = ("getiri", "pay")
PARA_BIRIMLERI = ("TRY", "USD", "EUR", "XAU")
VADELER = (1, 3, 6, 12)

BUYUKLUK_ETIKETI = {
    "getiri": "Dağıtılan kâr payı oranı (gerçekleşen yıllık getiri)",
    "pay": "Kâr paylaşım oranı (katılımcıya düşen pay)",
}


def _satirlar(kayitlar: Any, buyukluk: str, currency: str,
              term_months: Optional[int]) -> list[dict]:
    """Süzülmüş kayıtlardan banka başına EN İYİ satırı üretir.

    Vade belirtilmemişse bankanın en yüksek oranı temsil eder ve satır kendi
    vadesini TAŞIR — vade gizlenirse farklı vadeler aynı kolonda kıyaslanmış
    olurdu (`comparison` katmanındaki adil kıyas kuralının aynısı).
    """
    secili = [k for k in kayitlar
              if k.get("buyukluk") == buyukluk
              and k.get("currency") == currency
              and (term_months is None or k.get("term_months") == term_months)]
    en_iyi: dict[str, dict] = {}
    for k in secili:
        s = k.get("bank_slug") or "?"
        if s not in en_iyi or (k.get("annual_rate") or 0) > (
                en_iyi[s].get("annual_rate") or 0):
            en_iyi[s] = k
    sirali = sorted(en_iyi.values(),
                    key=lambda k: -(k.get("annual_rate") or 0))
    return [{
        "bank_slug": k.get("bank_slug"),
        "bank_name": k.get("bank_name") or k.get("bank_slug"),
        "annual_rate": k.get("annual_rate"),
        "term_months": k.get("term_months"),
        "currency": k.get("currency"),
        "period_date": k.get("period_date"),
        "source_url": k.get("source_url"),
    } for k in sirali]


def router_kur():
    """Katılma oranı uçlarını taşıyan `APIRouter`'ı kurar.

    `fastapi` import'u fonksiyon içinde — `katalog.py` ile aynı gerekçe:
    paket yoksa bu modülün import edilmesi tek başına çökmemeli.
    """
    from fastapi import APIRouter, HTTPException

    r = APIRouter()

    @r.get("/katilma-oranlari")
    def katilma_oranlari(buyukluk: str = "getiri", currency: str = "TRY",
                         term_months: Optional[int] = None):
        """Katılma hesabı oranları — banka başına en iyi satır, azalan sırada.

        `veri_yok: true` bir HATA DEĞİLDİR: hasat henüz koşmamış olabilir
        (`scripts/tkbb_guncel_hasat.py`). Arayüz bunu "veri toplanmadı" olarak
        gösterir; boş bir tabloyu "oran sıfır" gibi sunmaz.
        """
        if buyukluk not in BUYUKLUKLER:
            raise HTTPException(400, f"buyukluk şunlardan biri olmalı: "
                                     f"{', '.join(BUYUKLUKLER)}")
        if currency not in PARA_BIRIMLERI:
            raise HTTPException(400, f"currency şunlardan biri olmalı: "
                                     f"{', '.join(PARA_BIRIMLERI)}")
        if term_months is not None and term_months not in VADELER:
            raise HTTPException(400, f"term_months şunlardan biri olmalı: "
                                     f"{', '.join(map(str, VADELER))}")

        kayitlar = kayitlari_yukle()
        satirlar = _satirlar(kayitlar, buyukluk, currency, term_months)
        donem = satirlar[0]["period_date"] if satirlar else None
        return {
            "buyukluk": buyukluk,
            "buyukluk_etiketi": BUYUKLUK_ETIKETI[buyukluk],
            "currency": currency,
            "term_months": term_months,
            "period_date": donem,
            "veri_yok": not satirlar,
            "rows": satirlar,
            # Kaynak KOŞULSUZ döner: panelde de kaynaksız sayı gösterilmez.
            "source_url": (satirlar[0]["source_url"] if satirlar
                           else "https://tkbb.org.tr/veripetegi-detay/40"),
            "source_label": "TKBB Veri Peteği",
            # Panelin süzgeçlerini kurabilmesi için gerçekten VAR OLAN
            # seçenekler; sabit liste basmak, verisi olmayan bir para birimini
            # seçilebilir gösterirdi.
            "mevcut": {
                "para_birimleri": sorted({k.get("currency") for k in kayitlar
                                          if k.get("buyukluk") == buyukluk
                                          and k.get("currency")}),
                "vadeler": sorted({k.get("term_months") for k in kayitlar
                                   if k.get("buyukluk") == buyukluk
                                   and k.get("term_months")}),
            },
            # Kâr-zarar ortaklığı uyarısı sunucudan gelir: aynı cümle
            # chatbot'ta da basılıyor ve iki yüzeyin ayrışmaması gerekiyor.
            "uyari": ("Oranlar geçmiş dönemde dağıtılan kâr payıdır; katılma "
                      "hesabında getiri garanti edilemez ve anapara da güvence "
                      "altında değildir."),
        }

    return r
