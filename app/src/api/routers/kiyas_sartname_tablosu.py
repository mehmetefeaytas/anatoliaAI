"""`/urun-tablosu` — şartname Senaryo-1 tablosu: bir banka satırı, YEDİ kolon.

`routers/kiyas.py`'den ayrıldı (21 Ağu 2026). Uç gövdesi ve **docstring'i**
BİREBİR taşındı; davranış değişikliği yok.

## Niçin AYRI bir modül

`/compare` ile aynı veriyi kullanır ama TERS eksende çalışır: `/compare` bir
kolonu çok bankada gösterir, bu uç bir kampanyayı yedi kolonda gösterir.
Buradaki sorumluluk **kolon şemasıdır** — hangi şartname kolonu hangi çıkarım
alanına bağlı, hangi kolon ölçülebilir, doluluk nasıl sayılır. `/compare`'in
sorumluluğu ise SIRALAMADIR. İkisini tek gövdede tutmak, şartname kolon
şemasına dokunan her değişikliği sıralama kodunun içinden geçirmek demekti.

Bu uç `rank()` ÇAĞIRMAZ — tablo bir sıralama değildir, satırlar banka adına
göre dizilir. Sıralama çekirdeğinden tam bağımsız olması, ayrı modül olmasının
en somut gerekçesi.

## Sorumluluk sınırı: ne BURADA, ne başka yerde

  * kolon şeması + doluluk + adil kıyas notu -> BURADA
  * alan × kampanya toplama (İLK kayıt kazanır) -> `kiyas_toplama`
  * satır kuralları (kampanya birleştirme yasağı) -> `comparison/compare.py`
"""

from __future__ import annotations

from typing import Any, Callable, Optional

from ...comparison.compare import (
    AVANTAJ_ALANLARI,
    AVANTAJ_MUAFIYET_ALANLARI,
    OLCULEN_SUTUNLAR,
    SARTNAME_SUTUNLARI,
    tablo_dolulugu,
    tablo_satirlari,
)
from .kiyas_toplama import sartname_kampanyalari


def uc_ekle(
    r: Any,
    *,
    field_rows: Callable[..., list[dict]],
    kiyas_kapsami: Callable[..., list[dict]],
):
    """`/urun-tablosu`'nu `r`'ye kaydeder.

    `fastapi` import'u gerekmiyor: bu uç hiç `HTTPException` atmaz (iki
    parametresi de opsiyonel ve serbest metin).
    """
    _field_rows = field_rows
    _kiyas_kapsami = kiyas_kapsami

    @r.get("/urun-tablosu")
    def urun_tablosu(type: Optional[str] = None, bank: Optional[str] = None):
        """Şartname Senaryo-1 tablosu: banka başına TEK satır, YEDİ kolon.

        Şartname s.11–12 çözümün çıktısını bir tabloyla tarif ediyor::

            Banka | Ürün Türü | Kâr Payı Oranı | Vade | Kampanya Avantajı |
            Masraf Durumu | Kampanya Süresi

        Bu uç `/compare`'in YERİNE GEÇMEZ, yanına gelir. `/compare` tek
        alanlıdır (bir kolon, çok banka) ve kanıt/güven/katman kolonlarıyla
        denetim yüzeyidir; bu uç çok alanlıdır (bir banka, yedi kolon) ve
        şartnamenin manşet illüstrasyonunun karşılığıdır. Kural ve gerekçeler
        `comparison/compare.py`'nin "Şartname Senaryo-1 tablosu" bloğunda —
        burada ikinci kez yazılmaz.

        ## Ne YAPMAZ

        * **Kampanyaları birleştirmez.** Satır tek bir kampanyayı temsil eder;
          oranı bir kampanyadan, vadeyi bir başkasından alıp aynı satıra
          yazmak var olmayan bir ürün icat etmek olurdu (CLAUDE.md §21).
          Bankanın aynı ailedeki diğer kampanyaları `other_count` ile sayılır.
        * **Serbest metin üretmez.** "Kampanya Avantajı" bir çıkarım alanı
          DEĞİLDİR ve şemaya böyle bir sütun eklenmedi; mevcut span'li
          alanlardan (`odul_miktari`, `alisveris_puani`, `indirim_orani`;
          hiçbiri yoksa ücret muafiyeti) derlenen parçalardan oluşur ve her
          parça kendi kaynağını taşır.
        * **Türkçe metni üretmez.** Hücreler kanonik değer + kanıt döner; boş
          hücrenin «Belirtilmemiş» yazısı arayüzün işidir
          (`web/app/lib/format.ts`). Sunucuda ikinci bir biçimlendirici
          tutmak, aynı kararı iki yerde yaşatmak olurdu.

        ## Doluluk — gizlenmez, SAYILIR

        Korpus bu tabloyu bugün büyük ölçüde boş dolduruyor ve bu bir kusur
        değil veri gerçeğidir. `doluluk` alanı "kaç hücrenin kaçı dolu"yu
        ÇALIŞMA ANINDA ölçer; sayı koda gömülmez, çünkü çıkarım katmanı
        geliştikçe değişir. Şartnamenin kendi tablosunda da 21 hücrenin 3'ü
        "Belirtilmemiş"tir.

        Süzgeçler: `type` (kampanya türü), `bank` (tek banka). İkisi de
        opsiyoneldir; `type` verilmezse her ürün ailesi ayrı satır kümesi
        olarak döner ve satırlar (tür, banka adı) sırasındadır.
        """
        # Kolonların ihtiyaç duyduğu TÜM alanlar tek geçişte çekilir; alan
        # başına bir sorgu (`/bank-delta` ile aynı desen).
        gerekli = {f for _a, _b, f in SARTNAME_SUTUNLARI if f}
        gerekli.update(AVANTAJ_ALANLARI)
        gerekli.update(AVANTAJ_MUAFIYET_ALANLARI)

        kampanyalar = sartname_kampanyalari(
            gerekli, field_rows=_field_rows, type=type, bank=bank)

        kapsam = [k for k in _kiyas_kapsami(type)
                  if not bank or k["bank"] == bank]
        satirlar = tablo_satirlari(kampanyalar.values(), kapsam=kapsam)

        return {
            "type": type,
            "bank": bank,
            "columns": [{"key": a, "label": b, "field_name": f,
                         "olculur": a in OLCULEN_SUTUNLAR}
                        for a, b, f in SARTNAME_SUTUNLARI],
            "doluluk": tablo_dolulugu(satirlar),
            "fairness_note": (
                "Her satır TEK bir kampanyadır; bir bankanın farklı "
                "kampanyalarından alınan değerler aynı satırda "
                "BİRLEŞTİRİLMEZ. Ölçülemeyen hücre boş bırakılır ve "
                "«Belirtilmemiş» olarak gösterilir — sıfır ya da tahmin "
                "yazılmaz. Tablo bir sıralama değildir: satırlar banka adına "
                "göre dizilir."),
            "rows": [s.to_dict() for s in satirlar],
        }

    return urun_tablosu
