"""`GET /finansman-oranlari` — bankaların KENDİ yayımladığı finansman oranları.

İlgili: ../../domain/yayimlanan_oran.py (yükleme + sıralama)
        katilma.py (aynı desen, ters yönlü büyüklük)

## Niçin ayrı bir uç

Kampanya korpusundan `kar_payi_orani` yalnız 164/2.708 belgede (%6,1)
çıkabiliyor ve bu bir çıkarım kusuru değil — bilgi o metinlerde YOK (ölçüldü
2026-08-25: EVREN 60 belgede 0, yerel model 30 belgede 0 kabul). Bankalar
oranı hesaplama araçlarında yayımlıyor; bu uç o kaynağı sunuyor.

Kayıtlar `extracted_fields`e yazılmıyor: banka düzeyinde bir oranı belirli bir
kampanyanın alanına yazmak, o belgenin söylemediği bir şeyi ona atfetmek
olurdu. Kaynak ayrı, etiket ayrı, uç ayrı.

## Yön: DÜŞÜK oran iyidir

Katılma hesabında yüksek oran iyiydi (kazandığınız), finansmanda düşük oran
iyi (ödediğiniz). İki yüzey aynı kelimeyi kullandığı için yanıt gövdesi yönü
`yon` alanıyla AÇIKÇA söylüyor; arayüzün varsayması gereken bir şey değil.
"""

from __future__ import annotations

from typing import Optional

from ...domain import yayimlanan_oran as Y


def _satir(k: dict) -> dict:
    return {
        "bank_slug": k.get("bank_slug"),
        "product_name": k.get("product_name"),
        "product_code": k.get("product_code"),
        "urun_ailesi": Y.aile(k.get("product_name") or "") or "Diğer",
        "monthly_rate": k.get("monthly_rate"),
        "annual_cost_rate": k.get("annual_cost_rate"),
        "term_months": k.get("term_months"),
        "amount": k.get("amount"),
        "amount_max": k.get("amount_max"),
        "total_payment": k.get("total_payment"),
        "fees": k.get("fees") or None,
        "currency": k.get("currency") or "TRY",
        "source_url": k.get("source_url"),
        "collected_at": k.get("collected_at"),
        "method": k.get("method"),
        "note": k.get("note"),
    }


def router_kur():
    """Finansman oranı uçlarını taşıyan `APIRouter`.

    `fastapi` import'u fonksiyon içinde — `katilma.py` ile aynı gerekçe.
    """
    from fastapi import APIRouter

    r = APIRouter()

    @r.get("/finansman-oranlari")
    def finansman_oranlari(urun_ailesi: Optional[str] = None,
                           term_months: Optional[int] = None,
                           tum_kayitlar: bool = False):
        """Banka başına EN DÜŞÜK aylık kâr payı oranı, artan sırada.

        `veri_yok: true` bir HATA DEĞİLDİR: oran hasadı henüz koşmamış olabilir
        (`python -m src.scraping.harvest_rates`). Arayüz bunu "veri
        toplanmadı" diye gösterir; boş tabloyu "oran sıfır" gibi sunmaz.

        `tum_kayitlar=true` banka başına tek satır kısıtını kaldırır — denetim
        için; varsayılan kıyas görünümüdür.
        """
        havuz = Y.yukle()
        if tum_kayitlar:
            secili = [k for k in havuz
                      if (not urun_ailesi
                          or Y.aile(k.get("product_name") or "") == urun_ailesi)
                      and (term_months is None
                           or k.get("term_months") == term_months)]
            satirlar = [_satir(k) for k in
                        sorted(secili, key=lambda k: (k.get("monthly_rate") or 0,
                                                      k.get("bank_slug") or ""))]
        else:
            satirlar = [_satir(k) for k in Y.siralama(
                urun_ailesi=urun_ailesi, vade_ay=term_months, kayitlar=havuz)]
        return {
            "yon": "dusuk_iyi",
            "yon_etiketi": "Finansmanda DÜŞÜK oran avantajlıdır "
                           "(katılma hesabının tersi)",
            "urun_ailesi": urun_ailesi,
            "term_months": term_months,
            "veri_yok": not satirlar,
            "rows": satirlar,
            # Süzgeç seçenekleri GERÇEKTEN VAR OLANLARDAN türetiliyor; sabit
            # liste, verisi olmayan bir aileyi seçilebilir gösterirdi.
            "urun_aileleri": Y.urun_aileleri(havuz),
            "vadeler": Y.vadeler(havuz),
            "kapsam": Y.kapsam(),
            "kaynak_notu": (
                "Oranlar bankaların KENDİ yayınlarından toplandı (hesaplama "
                "araçları ve oran tabloları), kampanya metinlerinden "
                "çıkarılmadı. Kampanya korpusunda kâr payı oranı belgelerin "
                "yalnız %6,1'inde geçiyor; bu bir ölçüm kusuru değil, "
                "bilginin o metinlerde bulunmamasıdır."),
        }

    @r.get("/finansman-oranlari/{bank_slug}")
    def banka_finansman_orani(bank_slug: str):
        """Tek bankanın yayımladığı oranların özeti; yoksa `veri_yok`.

        Banka sayfası bunu «ölçülemedi» satırlarının altında kullanıyor:
        kampanya metninden ölçemediğimiz bir oranı banka başka bir yerde
        yayımlıyorsa, o ekranda söylenmeli.
        """
        ozet = Y.banka_ozeti(bank_slug)
        if ozet is None:
            return {"bank_slug": bank_slug, "veri_yok": True,
                    "gerekce": ("bu banka finansman oranını yayımlamıyor ya da "
                                "oran hasadı bu banka için koşmadı")}
        return {**ozet, "veri_yok": False}

    return r
