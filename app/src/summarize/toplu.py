"""Korpus için özetleri TOPLU üretir — CLI ve API işi aynı gövdeyi kullanır.

İlgili: ./ozet.py (tek belge), ./ozet_isi.py (arka plan işi + ilerleme)
        ../../scripts/build_summaries.py (ince CLI kabuğu)
        ../api/main.py (`/summaries/*` uçları)

## Neden `scripts/` altında değil

Bu gövde 2026-08-11'e kadar `scripts/build_summaries.py` içindeydi ve yalnız
komut satırından çağrılıyordu. Arayüze «LLM ile özet üret» düğmesi eklenince
API'nin de aynı döngüye ihtiyacı oldu — ve `src/api` → `scripts/` içe aktarımı
katmanı ters çevirirdi: `scripts/` `src/`'yi kullanır, tersi değil.

Alternatif, döngüyü API tarafında ikinci kez yazmaktı. Bu projede tam olarak o
kusur (aynı bilgi iki yerde) altı kez tekrarladı ve her seferinde iki kopya
ayrıştı. Gövde buraya taşındı; `scripts/build_summaries.py` artık argüman
ayrıştırıp raporu basan ince bir kabuktur ve `calistir`ı buradan alır.

## Kapsam: önce kıyasta görünen alt küme

Korpus ~1774 belge; hepsini tek koşuda özetlemek saatler sürer. Varsayılan
kapsam (`kiyas`) kıyaslanabilir bir alanı ÇIKARILMIŞ belgelerdir — yani
dashboard'un karşılaştırma tablosunda gerçekten görünenler. `devam=True` ile
tekrar tekrar koşulabilir; her koşu yalnız özeti olmayan belgeleri işler.

**Kısmi kapsama tam gibi raporlanmaz:** rapor hem işlenen hem de korpustaki
toplam belge sayısını basar.

## Sebep de YAZILIR, yalnız özet değil

Özet üretilemeyen belge için `campaigns.ozet_sebep` doldurulur. Sebepsiz bir
boş `ozet`, "denendi ve içerik çıkmadı" ile "hiç denenmedi"yi ayırt edilemez
kılar; ekrandaki kapsam sayacı o ayrımı yapamadığında yeni toplanmış her belge
için "özetlenecek içerik yok" diye YANLIŞ cümle kurar. Gerekçenin tamamı
`src/db/schema.sql`'deki sütun yorumundadır.

`kalici_atla=True` iken, sebebi belgenin kendisine ait olan (`metin_bos`)
belgeler hedeften düşer: onları tekrar denemek aynı sonucu üretir ve arayüzdeki
düğme her basışta boşuna dakikalar harcardı.
"""

from __future__ import annotations

import time
from typing import Any, Callable, Optional

from ..comparison.compare import _HIGHER_IS_BETTER, _LOWER_IS_BETTER
from ..db.repository import Repository
from ..extraction.llm.extractor import default_extractor
from .ozet import (
    MAKS_GIRDI_KARAKTER,
    OzetSonucu,
    kalici_sebep,
    llm_hazir,
    ozetle,
)

#: Kıyas tablosunu besleyen alanlar — `compare.py`'nin kendi kümeleri.
#: Burada liste KOPYALANMAZ; ayrışırsa kapsam sessizce kayardı.
KIYAS_ALANLARI: tuple[str, ...] = tuple(sorted(_LOWER_IS_BETTER | _HIGHER_IS_BETTER))

KAPSAMLAR = ("kiyas", "hepsi")

#: Kaç belgede bir depoya yazılacağı. Tam korpus koşusu ~1400 belge ve belge
#: başına ~6 sn, yani ~2,5 saat. Tek seferde sonda yazmak, o 2,5 saatin
#: TAMAMINI tek bir kesintiye (Ctrl-C, uyku, OOM) bağlar: yazılmamış özetler
#: kaybolur ve `devam` sıfırdan başlar çünkü DB'de hiçbir iz yoktur.
#: Parçalı yazma ile kayıp en fazla bir parçadır ve `devam` gerçekten kaldığı
#: yerden devam eder.
YAZMA_PARCASI = 25


def kiyas_kampanyalari(repo: Repository) -> set[int]:
    """Kıyaslanabilir bir alanı çıkarılmış kampanya kimlikleri.

    `query_fields()` kullanılır, ham SQL değil: depo sözleşmesi tek yoldur ve
    aynı çağrı iki backend'de de çalışır. Sözleşme/akit belgelerinin elenmesi
    de bu metodun kendi işidir (`belge_turu` süzmesi, bkz. `src/db/base.py`).
    """
    ids: set[int] = set()
    for alan in KIYAS_ALANLARI:
        for satir in repo.query_fields(alan):
            cid = satir.get("campaign_id")
            if cid is not None:
                ids.add(int(cid))
    return ids


def hedef_kampanyalar(repo: Repository, *, kapsam: str, devam: bool,
                      limit: Optional[int],
                      kalici_atla: bool = False) -> tuple[list[dict], int]:
    """(işlenecek kampanyalar, korpustaki toplam belge sayısı)."""
    hepsi = repo.all_campaigns()
    toplam = len(hepsi)

    if kapsam == "kiyas":
        secili = kiyas_kampanyalari(repo)
        hepsi = [c for c in hepsi if int(c["id"]) in secili]
    if devam:
        hepsi = [c for c in hepsi if not (c.get("ozet") or "").strip()]
    if kalici_atla:
        hepsi = [c for c in hepsi if not kalici_sebep(c.get("ozet_sebep"))]
    if limit is not None:
        hepsi = hepsi[:limit]
    return hepsi, toplam


def sayim(repo: Repository) -> dict[str, Any]:
    """Kapsam sayaçları — düğmeye basılmadan ÖNCE ne olacağının kaydı.

    Tek bir model çağrısı bile yapmaz. Dört kova toplamı korpusa eşittir ve
    kovalar kesişmez:

      ``ozetli``      özet var
      ``icerik_yok``  denendi, belgede özetlenecek içerik çıkmadı (kalıcı)
      ``basarisiz``   denendi, koşuya ait bir sebeple üretilemedi (tekrarlanabilir)
      ``denenmemis``  hiç denenmedi
    """
    ozetli = icerik_yok = basarisiz = denenmemis = 0
    sebepler: dict[str, int] = {}
    for c in repo.all_campaigns():
        if (c.get("ozet") or "").strip():
            ozetli += 1
            continue
        sebep = (c.get("ozet_sebep") or "").strip()
        if not sebep:
            denenmemis += 1
            continue
        sebepler[sebep] = sebepler.get(sebep, 0) + 1
        if kalici_sebep(sebep):
            icerik_yok += 1
        else:
            basarisiz += 1
    return {
        "toplam": ozetli + icerik_yok + basarisiz + denenmemis,
        "ozetli": ozetli,
        "icerik_yok": icerik_yok,
        "basarisiz": basarisiz,
        "denenmemis": denenmemis,
        # Düğmenin gerçekten işleyeceği belge sayısı: denenmemiş + tekrar
        # denenebilir. Kalıcı olanlar hedefte YOK (bkz. modül başlığı).
        "hedef": denenmemis + basarisiz,
        "sebepler": sebepler,
    }


def _yaz(repo: Repository, atamalar: dict[int, str]) -> int:
    """Özetleri depoya yazar — `set_ozet()` sözleşme metodu üzerinden.

    Ham SQL yazılmaz: gövde tek bir backend'e bağlanmamalı.
    """
    if not atamalar:
        return 0
    return int(repo.set_ozet(atamalar))


def _sebep_yaz(repo: Repository, atamalar: dict[int, str]) -> int:
    """Üretilemeyen belgelerin sebebini yazar."""
    if not atamalar:
        return 0
    return int(repo.set_ozet_sebep(atamalar))


def calistir(db_yolu: Optional[str] = None, *, repo: Optional[Repository] = None,
             kapsam: str = "kiyas", devam: bool = False,
             limit: Optional[int] = None, kuru: bool = False,
             maks_karakter: int = MAKS_GIRDI_KARAKTER,
             llm: Any = None, parca: int = YAZMA_PARCASI,
             kalici_atla: bool = False,
             ilerleme: Optional[Callable[[int, int, int], None]] = None,
             adim: Optional[Callable[[int, int, OzetSonucu], None]] = None,
             iptal: Optional[Callable[[], bool]] = None) -> dict:
    """Toplu özet üretimi. Rapor sözlüğü döndürür (JSON'a yazılabilir).

    Özetler `parca` belgede bir depoya YAZILIR (bkz. `YAZMA_PARCASI`).

    Geri çağrılar üç ayrı soruya cevap verir ve BİRLEŞTİRİLMEZ:

    * ``ilerleme(islenen, hedef, yazilan)`` — her PARÇA yazıldıktan sonra.
      "Disk'e gerçekten yazıldı mı" sorusunun tek doğru anıdır; testler bunu
      yazmanın gerçekleştiğini kanıtlamak için kullanır.
    * ``adim(islenen, hedef, sonuc)`` — her BELGEDEN sonra. Arayüz 1,5 saniyede
      bir durum soruyor; parça başına ilerleme (25 belge ≈ 2,5 dakika) ekranı
      dakikalarca dondurulmuş gösterirdi.
    * ``iptal()`` — her belgeden ÖNCE. `True` dönerse döngü kırılır, bekleyen
      parça yine de yazılır (üretilmiş ama yazılmamış özeti çöpe atmak, iptali
      veri kaybına çevirirdi) ve rapor `iptal=True` taşır.

    `repo` verilirse o kullanılır ve KAPATILMAZ (çağıran sahibidir); yoksa
    `db_yolu`'ndan yeni bir depo açılır ve sonunda kapatılır.
    """
    if repo is None and not db_yolu:
        raise ValueError("`db_yolu` ya da `repo` verilmeli.")
    llm = llm if llm is not None else default_extractor()
    disaridan = repo is not None
    repo = repo if repo is not None else Repository(str(db_yolu))
    try:
        hedefler, toplam = hedef_kampanyalar(repo, kapsam=kapsam, devam=devam,
                                             limit=limit,
                                             kalici_atla=kalici_atla)
        basladi = time.time()
        bekleyen: dict[int, str] = {}
        bekleyen_sebep: dict[int, str] = {}
        sebepler: dict[str, int] = {}
        kirpilan = 0
        ozetlenen = 0
        yazilan = 0
        kesildi = False

        def bosalt() -> None:
            nonlocal bekleyen, bekleyen_sebep, yazilan
            if kuru:
                return
            if bekleyen:
                yazilan += _yaz(repo, bekleyen)
                bekleyen = {}
            if bekleyen_sebep:
                _sebep_yaz(repo, bekleyen_sebep)
                bekleyen_sebep = {}

        for i, camp in enumerate(hedefler, start=1):
            if iptal is not None and iptal():
                kesildi = True
                break
            sonuc: OzetSonucu = ozetle(camp.get("raw_text") or "", llm,
                                       maks_karakter=maks_karakter)
            kirpilan += 1 if sonuc.kirpildi else 0
            if sonuc.uretildi and sonuc.ozet:
                bekleyen[int(camp["id"])] = sonuc.ozet
                ozetlenen += 1
            else:
                anahtar = sonuc.sebep or "bilinmiyor"
                sebepler[anahtar] = sebepler.get(anahtar, 0) + 1
                bekleyen_sebep[int(camp["id"])] = anahtar
            if adim is not None:
                adim(i, len(hedefler), sonuc)
            if parca > 0 and i % parca == 0:
                bosalt()
                if ilerleme is not None:
                    ilerleme(i, len(hedefler), yazilan)

        bosalt()
        return {
            "db": db_yolu or "(dışarıdan verilen depo)",
            "kapsam": kapsam,
            "korpus_belge": toplam,
            "hedef_belge": len(hedefler),
            "ozetlenen": ozetlenen,
            "yazilan": yazilan,
            "kuru": kuru,
            "iptal": kesildi,
            "kirpilan_girdi": kirpilan,
            "uretilemeyen": sebepler,
            "sure_sn": round(time.time() - basladi, 2),
            "llm_acik": llm_hazir(llm),
        }
    finally:
        if not disaridan:
            repo.close()
