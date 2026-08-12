"""Depo (repository) sözleşmesi — SQLite ve PostgreSQL uygulamalarının ortak arayüzü.

İlgili: CLAUDE.md §9 (veri modeli), ../../decisions/demo-onceden-doldurulmus-db.md
        docs/veri-katmani.md (hangi backend ne zaman)

## Neden bu dosya var

Proje iki depo uygulaması taşır:

- `repository.Repository`      — SQLite, stdlib, sıfır kurulum (offline/test yolu)
- `postgres.PostgresRepository` — PostgreSQL + pgvector (üretim yolu)

"İki backend destekliyoruz" iddiasının tek kabul kriteri, iki uygulamanın AYNI
soruya AYNI cevabı vermesidir. Bu dosya iki şeyi merkezileştirir:

1. `RepositoryProtocol` — hangi metotların sözleşmede olduğunu tip düzeyinde
   sabitler; yeni bir metot yalnızca bir backend'e eklenirse tip denetimi
   yakalar.
2. `finalize_campaign_text()` — `campaign_text()`'in span doğrulama mantığı.
   Bu mantık iki backend'de KOPYALANMAZ; kopyalansaydı biri düzeltilip diğeri
   unutulduğunda "kaynak vurgulaması" (CLAUDE.md §18 yenilikçilik hedefi #1)
   sessizce iki farklı davranış üretirdi.
3. `ThreadSafeRepository` — iki backend için ORTAK thread serileştirmesi
   (aşağıdaki sınıfın docstring'i bunun neden bir hata düzeltmesi olduğunu
   anlatır).
"""

from __future__ import annotations

import json
import logging
import threading
from collections.abc import Mapping
from typing import Any, Optional, Protocol, runtime_checkable

from ..preprocessing.clean import tr_fold_ascii
from ..schemas import Campaign, Extractor

logger = logging.getLogger(__name__)

# --------------------------------------------------------------------------- #
# Belge türü — kampanya mı, akit mi?
# --------------------------------------------------------------------------- #
#
# Ölçülmüş sorun (bkz. docs/rapor/belge-turu.md): korpustaki 1761 belgenin
# 113'ü (%6,4) kampanya sayfası DEĞİL, sözleşme/tarife/form PDF'idir. Hepsi
# `campaigns` tablosuna kampanya olarak giriyordu ve 43'ü kıyaslanabilir alan
# (oran/vade/tutar) taşıdığı için `/compare` tablosuna karışıyordu. Bir genel
# kredi sözleşmesindeki "%2,49" ile bir kampanya sayfasındaki "%2,49" aynı
# kolonda sıralanamaz: akit kampanya değildir (CLAUDE.md §17 "adil kıyas
# garantisi").
#
# Değerler Türkçe ve sadeleştirilmiş yazılır (`sozlesme`, `ş` değil `s`):
# sütun bir SINIF ETİKETİ taşıyor, kullanıcıya dönük metin değil; etiketin
# kodlama/normalizasyon sorunu çıkarmaması için ASCII tutuldu.
BELGE_TURU_KAMPANYA = "kampanya"
BELGE_TURU_SOZLESME = "sozlesme"
BELGE_TURLERI = (BELGE_TURU_KAMPANYA, BELGE_TURU_SOZLESME)


def belge_turu_dogrula(deger: Optional[str]) -> Optional[str]:
    """Belge türünü doğrular; `None` geçerlidir (bilinmiyor).

    Doğrulama neden Python'da, şemada CHECK ile DEĞİL: SQLite `ALTER TABLE
    ADD COLUMN` ile CHECK kısıtı eklemeye izin vermez. Kısıtı yalnız
    `CREATE TABLE` içine koysaydık, SIFIRDAN kurulan bir DB ile GÖÇLE
    güncellenen eski bir DB farklı davranırdı (biri reddeder, diğeri kabul
    eder) — parite iddiasının tam olarak yasakladığı şey. Tek doğrulama
    noktası burasıdır ve iki backend de buradan geçer.

    `None` bilinçli olarak geçerlidir: sınıflandırılamayan belgeye tür
    UYDURMAK yerine bilgi yokluğu saklanır (CLAUDE.md §19: bilgi yoksa null).
    """
    if deger is None or deger in BELGE_TURLERI:
        return deger
    raise ValueError(
        f"belge_turu={deger!r} geçersiz. Geçerli: "
        f"{', '.join(repr(t) for t in BELGE_TURLERI)} veya None (bilinmiyor).")


def kiyas_where(sutun: str = "c.belge_turu") -> str:
    """Kıyas yolunun WHERE parçası: sözleşme HARİÇ, **bilinmeyen DAHİL**.

    Üretilen SQL:  `(c.belge_turu IS NULL OR c.belge_turu <> 'sozlesme')`

    İki tasarım kararı burada kilitli:

    1. **`<> 'sozlesme'`, `= 'kampanya'` DEĞİL.** İkisi dolu bir korpusta aynı
       kümeyi verir, ama sütunu HENÜZ doldurulmamış bir veri tabanında
       (`belge_turu` her satırda NULL) `= 'kampanya'` **hiçbir satır
       döndürmezdi** — karşılaştırma tablosu sessizce boşalırdı. `IS NULL OR
       <> ...` biçimi eski/doldurulmamış DB'lerde bugünkü davranışı birebir
       korur ve yalnızca türü KESİN olarak bilinen akitleri eler.
    2. **Değer SQL metnine gömülür, yer tutucu kullanılmaz.** `sqlite3` `?`,
       `psycopg` `%s` bekler; parça iki backend'de birebir aynı metin olsun
       diye sabit modül düzeyinde gömülüdür. Kullanıcı girdisi buraya
       girmez — `BELGE_TURU_SOZLESME` bir kod sabitidir.
    """
    return f"({sutun} IS NULL OR {sutun} <> '{BELGE_TURU_SOZLESME}')"


# --------------------------------------------------------------------------- #
# Kampanya geçerlilik durumu — süresi dolmuş mu?
# --------------------------------------------------------------------------- #
#
# Değer `.meta.json` provenance sidecar'ından gelir (`campaign_status`) ve üç
# ayrı yazar tarafından üretilir: arşiv hasadı (`harvest_extra`), bayat sayfa
# mutabakatı (`reconcile_stale`) ve sayfanın kendi bitiş damgası
# (`scripts/damga_isaretle.py`). Ölçüm (2026-08-10, `data/raw`): 1774 belgenin
# 458'i `expired` — 237'si `archive/`, 221'i `live/` altında.
#
# `live/` altındaki 221 belge bu sütunun asıl gerekçesidir: dosya konumundan
# ("arşivde mi?") çıkarılamaz, çünkü sayfa hâlâ yayında ama METNİ kendi
# bitişini ilan ediyor ("Kampanya 31.12.2025 tarihinde sona ermiştir").
#
# `belge_turu` ile KARIŞTIRMA: o, belgenin NE OLDUĞUNU söyler (kampanya mı,
# akit mi); bu ise kampanyanın HÂLÂ GEÇERLİ olup olmadığını. Bir belge hem
# `kampanya` hem `expired` olabilir — en sık görülen bileşim budur.
#
# Değer İngilizce ve sidecar'daki yazımla BİREBİR aynı tutuldu
# (`scraping.collector.STATUS_EXPIRED`): sütun bir sınıf etiketi taşıyor ve
# diskteki 458 dosyada yazılı olan dizgeyi burada Türkçeleştirmek, iki tarafın
# sessizce ayrışabileceği bir çeviri adımı eklerdi.
KAMPANYA_DURUMU_SURESI_DOLMUS = "expired"
KAMPANYA_DURUMU_AKTIF = "active"


def suresi_dolmus_mu(durum: Optional[str]) -> bool:
    """Bu kampanya süresi dolmuş olarak işaretli mi?

    `None` **süresi dolmamış SAYILMAZ, bilinmiyor demektir** ve bu fonksiyon
    `False` döndürür — yani bilgi yokluğu bir kampanyayı sıralamadan atmaz.
    Ters yön (bilinmeyeni dolmuş saymak) korpusun %74'ünü sessizce eleyecekti:
    işaretsiz 1316 belgenin çoğu süresi dolmuş değil, sadece damgasız.
    """
    return durum == KAMPANYA_DURUMU_SURESI_DOLMUS


# `campaign_status` sütununda YAZILI bir değer DEĞİL, damgasızlığın SÜZGEÇ
# ADIDIR. `GET /campaigns?status=` ve `GET /stats` üçüncü bir kova olarak
# damgasız belgeleri sayar; SQL'de karşılığı `IS NULL`'dır.
#
# Neden `active` ile aynı kovaya konmuyor: `null` "geçerli" DEMEK DEĞİLDİR,
# "damgasız" demektir (bkz. `suresi_dolmus_mu()`). Korpusun %74'ü (1774'ün
# 1316'sı, ölçüldü 2026-08-10) bu durumdadır ve onları "aktif" diye saymak,
# hiç doğrulanmamış 1316 belge için doğrulanmış bir iddia uydurmak olurdu.
KAMPANYA_DURUMU_DAMGASIZ = "damgasiz"

#: `status` süzgecinin kabul ettiği değerler (sütundaki iki değer + damgasız).
KAMPANYA_DURUMLARI = (KAMPANYA_DURUMU_AKTIF, KAMPANYA_DURUMU_SURESI_DOLMUS,
                      KAMPANYA_DURUMU_DAMGASIZ)


def kampanya_durumu_dogrula(deger: Optional[str]) -> Optional[str]:
    """`status` süzgeç değerini doğrular; `None` = süzme yok.

    `belge_turu_dogrula()` ile aynı gerekçe (tek doğrulama noktası, iki
    backend de buradan geçer) ve aynı biçimde bilinçli olarak `None`'a izin
    verir — ama burada `None` "bilinmiyor" değil "süzme yok" demektir; süzgeç
    bir SORU parametresidir, saklanan bir değer değil.
    """
    if deger is None or deger in KAMPANYA_DURUMLARI:
        return deger
    raise ValueError(
        f"status={deger!r} geçersiz. Geçerli: "
        f"{', '.join(repr(d) for d in KAMPANYA_DURUMLARI)} veya None "
        "(süzme yok).")


# --------------------------------------------------------------------------- #
# Kampanya listeleme süzgeci — `GET /campaigns`, iki backend için ORTAK
# --------------------------------------------------------------------------- #
#
# Ölçülmüş sorun (2026-08-11): `GET /campaigns` 1774 satırı ham metinleriyle
# birlikte, süzgeçsiz döndürüyordu — `curl -s localhost:8000/campaigns | wc -c`
# = 10.339.015 bayt. Yükün tamamına yakını `raw_text`ti ve arayüz o alanı
# HİÇBİR YERDE okumuyordu (`web/app` içinde tek geçtiği yer tip tanımıydı).
#
# Süzgeç parçaları `kiyas_where()` ile aynı sebeple burada yaşar: iki backend
# ayrışırsa aynı istek hangi veri tabanına bağlı olduğuna göre farklı satır
# kümesi döndürür. `kiyas_where()`ten TEK farkı, buradaki değerlerin KULLANICI
# GİRDİSİ olmasıdır — bu yüzden SQL metnine gömülmez, yer tutucuyla bağlanır ve
# yer tutucu dizgesi (`?` SQLite / `%s` psycopg) çağırandan alınır. Modül
# başlığındaki `?` vs `%s` tuzağı tam olarak budur.


def kampanya_sutunlari(*, govde: bool,
                       scraped_at: str = "c.scraped_at") -> str:
    """`all_campaigns()` SELECT listesi. `govde=False` iken `raw_text` YOKTUR.

    Sütun listesi iki backend'de KOPYALANMAZ: `raw_text`i dışarıda bırakma
    kararı tek bir yerde durmalı, yoksa bir backend 10 MB'lık gövdeyi
    göndermeye devam ederken diğeri göndermez ve `tests/test_api_backend.py`
    parite kapısı ancak şansa yakalar.

    `scraped_at` ifadesi dışarıdan gelir: SQLite sütunu metin olarak saklar,
    Postgres `TIMESTAMPTZ` sütununu ISO-8601 UTC metnine çevirmek zorundadır
    (`postgres._SCRAPED_AT_ISO`). Fark KASITLIDIR ve o dosyanın başlığında
    yazılıdır.
    """
    sutunlar = ["c.id", "b.slug AS bank", "b.name AS bank_name",
                "c.campaign_type", "c.belge_turu", "c.campaign_status",
                "c.ozet", "c.ozet_sebep"]
    if govde:
        sutunlar.append("c.raw_text")
    sutunlar += ["c.source_url", f"{scraped_at} AS scraped_at"]
    return ", ".join(sutunlar)


def kampanya_where(*, yer_tutucu: str, bank: Optional[str] = None,
                   campaign_type: Optional[str] = None,
                   belge_turu: Optional[str] = None,
                   status: Optional[str] = None) -> tuple[str, list[Any]]:
    """`all_campaigns()` WHERE parçası + parametreleri. **İki backend için ORTAK.**

    `yer_tutucu` `'?'` (sqlite3) veya `'%s'` (psycopg) olur; başka hiçbir fark
    yoktur ve bu yüzden ikisi de aynı satır kümesini görür.

    Süzgeçlerin hepsi **kesin eşleşmelidir**, `kiyas_where()` gibi "bilinmeyeni
    de al" gevşekliği YOKTUR: burada kullanıcı açıkça bir kova seçiyor.
    `status='damgasiz'` bu yüzden `IS NULL`'a çevrilir — `= 'damgasiz'`
    hiçbir satır döndürmezdi, çünkü o dizge sütunda hiç yazılı değildir.

    `q` (serbest metin) bilinçli olarak BURADA DEĞİL: gerekçe
    `kampanya_metin_suz()` docstring'inde.
    """
    belge_turu = belge_turu_dogrula(belge_turu)
    status = kampanya_durumu_dogrula(status)
    kosullar: list[str] = []
    params: list[Any] = []
    if bank is not None:
        kosullar.append(f"b.slug={yer_tutucu}")
        params.append(bank)
    if campaign_type is not None:
        kosullar.append(f"c.campaign_type={yer_tutucu}")
        params.append(campaign_type)
    if belge_turu is not None:
        kosullar.append(f"c.belge_turu={yer_tutucu}")
        params.append(belge_turu)
    if status == KAMPANYA_DURUMU_DAMGASIZ:
        kosullar.append("c.campaign_status IS NULL")
    elif status is not None:
        kosullar.append(f"c.campaign_status={yer_tutucu}")
        params.append(status)
    if not kosullar:
        return "", []
    return "WHERE " + " AND ".join(kosullar) + " ", params


#: `q` süzgecinin taradığı alanlar — hepsi zaten yanıtta olan ÜSTVERİ.
KAMPANYA_Q_ALANLARI = ("bank", "bank_name", "campaign_type", "ozet",
                       "source_url")


def kampanya_metin_suz(rows: list[dict], q: Optional[str]) -> list[dict]:
    """`q` serbest metin süzgeci — SQL'de DEĞİL, Python'da. **İki backend ORTAK.**

    ## Neden SQL'de değil

    `LOWER()` iki backend'de AYNI ŞEYİ YAPMAZ: SQLite'ın gömülü `lower()`
    yalnızca ASCII harfleri katlar (belgelenmiş sınır), PostgreSQL'inki
    Unicode/locale duyarlıdır. Yani `LOWER(c.campaign_type) LIKE ...` ile
    yazılmış bir süzgeç 'İHTİYAÇ FİNANSMANI' satırını Postgres'te bulur,
    SQLite'ta bulamazdı — hem de sessizce. Bu, bu depo katmanının varlık
    sebebi olan paritenin tam ihlali olurdu.

    Üstelik SQL'deki `lower()` Türkçe için ZATEN yanlıştır (`'IŞIK'.lower()`
    → `'ışık'` değil `'isik'` beklenir); projenin doğru katlayıcısı
    `preprocessing.clean.tr_fold_ascii`'dir ve o bir Python fonksiyonudur.
    Süzgeci Python'a almak hem pariteyi hem Türkçe doğruluğunu bir arada verir:
    'kar payi' araması 'Kâr Payı'yı bulur.

    ## Neden `raw_text` taranmıyor

    Aranan alanlar (`KAMPANYA_Q_ALANLARI`) yanıtta ZATEN bulunan üstverdir.
    Ham gövdede arama bilinçli olarak yoktur: bu uçtan 10 MB'lık gövdeyi
    kaldırmanın hemen ardından aynı gövdeyi her tuş vuruşunda taramak
    olurdu. Belge İÇİNDE arama `/chat` (RAG + text-to-SQL) yoludur.
    """
    if q is None or not q.strip():
        return list(rows)
    aranan = tr_fold_ascii(q).strip()
    if not aranan:
        return list(rows)
    return [r for r in rows
            if any(aranan in tr_fold_ascii(str(r.get(alan) or ""))
                   for alan in KAMPANYA_Q_ALANLARI)]


# --------------------------------------------------------------------------- #
# Serbest arama — `GET /search`, iki backend için ORTAK
# --------------------------------------------------------------------------- #
#
# Ölçülmüş sorun (2026-08-12): arayüzde HİÇBİR arama yoktu. Denetim panelinde
# 1774 belge tek bir açılır listeye 1774 seçenek olarak diziliyordu; korpustaki
# 126 akit ve 458 süresi dolmuş belge o listede AYIRT EDİLEMEZ hâldeydi
# (ölçüm: `GET /stats`, 2026-08-12).
#
# `kampanya_metin_suz()` ile aynı katlama, aynı alanlar, aynı maliyet
# disiplini. TEK farkı çıktısıdır: orası "hangi satırlar kalsın" der, burası
# "NEDEN eşleşti" de der (`eslesme`). Kanıt göstermek bu ürünün her yerinde
# aynı kuraldır; arama bir istisna olmamalı.


#: Aramanın taradığı KISA sütunlar. `raw_text` BİLEREK YOK.
#:
#: Ham gövde korpusta ~10 MB'tır ve onu her tuş vuruşunda taramak bedava
#: değildir; bedavaymış gibi davranmak maliyet konusunda dürüst olmamak
#: olurdu. Belge İÇİNDE arama `/chat` (RAG + text-to-SQL) yoludur.
#:
#: Sıra ÖNEMLİDİR ve KANIT DEĞERİNE göre dizilidir: eşit sayıda terim eşleşen
#: alanlar arasında bu listede önce gelen, eşleşme parçasını verir. `ozet` en
#: başta çünkü `bank_name` ve `campaign_type` yanıtta ZATEN ayrı alan olarak
#: dönüyor — orada eşleştiğini göstermek kullanıcıya yeni bir şey söylemez.
#: Parça bir kanıt yüzeyidir; kanıtın görünmeyeni göstermesi gerekir.
ARAMA_ALANLARI = ("ozet", "campaign_type", "bank_name", "source_url")

#: Kanıt olarak **son çare** alanlar: aranırlar ama parça yalnız başka hiçbir
#: alan eşleşmediğinde buradan kesilir.
#:
#: `source_url` YAPISAL olarak eşleşir: bir bankanın her adresinde kendi adı
#: geçer ('kuveytturk.com.tr/...'), yani 'kuveyt konut' sorgusunda adres iki
#: terimi birden yakalar ve terim sayısına bakan bir seçim onu her zaman
#: kazandırırdı. Kullanıcıya kanıt diye adres göstermek, ona zaten bildiği
#: şeyi göstermektir; cümlenin kendisi ise yeni bilgidir.
ARAMA_ZAYIF_KANIT = frozenset({"source_url"})

#: Eşleşme parçasında hedefin iki yanında gösterilen karakter sayısı.
#: `locate_span`'in ±40'lık penceresiyle aynı ölçü — kullanıcı iki yüzeyde
#: aynı genişlikte bağlam görsün.
ARAMA_PENCERE = 40

#: `GET /search?limit=` öntanımı ve tavanı. Tavan bir savunmadır: uç, komut
#: paletini besliyor ve orada ekrana sığmayan bir liste kimseye yaramaz.
ARAMA_VARSAYILAN_LIMIT = 20
ARAMA_AZAMI_LIMIT = 100


def arama_sutunlari() -> str:
    """`search_campaigns()` SELECT listesi — `kampanya_sutunlari()`in KISA hâli.

    `raw_text` YOKTUR ve `govde` anahtarı da yoktur: aramanın gövdeye ihtiyacı
    olmadığı bir SEÇİM değil, tanımıdır (bkz. `ARAMA_ALANLARI`). Açılabilir bir
    kapı bırakmak, ilk performans sorununda o kapının açılması demekti.

    `scraped_at` de yoktur: iki backend'de farklı ifade gerektiren tek sütun
    odur (`postgres._SCRAPED_AT_ISO`) ve arama sonucunda gösterilmiyor. Almak,
    paritesi ayrıca korunması gereken bir sütunu bedelsiz yere sözleşmeye
    sokmak olurdu.
    """
    return ("c.id, b.slug AS bank, b.name AS bank_name, c.campaign_type, "
            "c.belge_turu, c.campaign_status, c.ozet, c.source_url")


def arama_where(*, yer_tutucu: str, bank: Optional[str] = None,
                campaign_type: Optional[str] = None,
                belge_turu: Optional[str] = None,
                status: Optional[str] = None) -> tuple[str, list[Any]]:
    """Aramanın kapsam süzgeci — `kampanya_where()`e DELEGE EDER.

    Ayrı bir ad taşır ama ayrı bir gövdesi YOKTUR ve bu bilinçlidir: arama ile
    listeleme aynı belge evrenini görmek zorundadır. İki süzgeç ayrı yazılsaydı
    "listede var ama aramada yok" (ya da tersi) sınıfından, kullanıcının asla
    bildiremeyeceği bir hata mümkün olurdu.

    `yer_tutucu` `'?'` (sqlite3) veya `'%s'` (psycopg) olur; iki backend
    arasındaki TEK fark odur ve `tests/test_arama_ucu.py` bunu Postgres
    kurulu olmadan, üretilen SQL METNİ üzerinden kilitler.
    """
    return kampanya_where(yer_tutucu=yer_tutucu, bank=bank,
                          campaign_type=campaign_type, belge_turu=belge_turu,
                          status=status)


def tr_katla_haritali(metin: str) -> tuple[str, list[int]]:
    """`tr_fold_ascii`, ama her katlanmış karakterin ÖZGÜN indeksiyle birlikte.

    Neden gerekli: katlama uzunluk KORUMAZ. `tr_fold_ascii` sonunda NFKD
    ayrıştırması yapar ve birleşen işaretleri atar; 'ﬁ' bir karakterken iki
    karaktere açılır, birleşen bir işaret ise sıfır karaktere iner. Yani
    katlanmış metinde bulunan bir konum, özgün metinde AYNI konum değildir —
    ve eşleşme parçasını (kanıtı) özgün metinden kesmek zorundayız, çünkü
    kullanıcıya 'kar payi' değil 'kâr payı' gösterilmeli.

    Katlama burada KARAKTER KARAKTER yapılır; bütün dizgeyi katlamakla
    sonucu Türkçe metinde aynıdır ama teorik olarak ayrışabilir (NFKD
    karakterler arası birleşme yapan bir girdi). Ayrışma sessiz kalmaz:
    `arama_konumu()` bulamadığında parça belgenin başından gösterilir,
    uydurma bir konum ÜRETİLMEZ.
    """
    katli: list[str] = []
    harita: list[int] = []
    for i, ch in enumerate(metin):
        parca = tr_fold_ascii(ch)
        if not parca:
            continue
        katli.append(parca)
        harita.extend([i] * len(parca))
    return "".join(katli), harita


def arama_konumu(metin: str, terim: str) -> Optional[tuple[int, int]]:
    """Katlanmış `terim`in ÖZGÜN `metin`deki karakter aralığı.

    `None` = izi sürülemedi (bkz. `tr_katla_haritali()` docstring'i). Çağıran
    bunu bir hata değil bilgi yokluğu olarak ele almalıdır.

    ## İki yol var ve ayrım ÖLÇÜLDÜ

    Karakter karakter haritalama pahalıdır: 1774 satırlık korpusta tek harflik
    bir sorgu neredeyse her satırı eşleştiriyor ve her satırın özetini
    harf harf katlamak ucu **2,0 saniyeye** çıkarıyordu (ölçüldü 2026-08-12,
    `GET /search?q=a`, 1774 belgelik gerçek korpus). Bu uç tuş başına
    çağrılıyor; o gecikme kabul edilemez. Aşağıdaki hızlı yolla aynı istek
    **0,09 saniyeye** indi; çok terimli gerçek sorgular 0,05 s civarında.

    Hızlı yol: katlama metnin uzunluğunu KORUDUYSA indeksler birebirdir.
    Türkçe metinde neredeyse her zaman böyledir. Ama "aynı uzunluk" tek
    başına yeterli KANIT DEĞİLDİR (bir karakter genişlerken başka biri
    kaybolabilir), bu yüzden aday aralık geri katlanıp terime eşit olduğu
    DOĞRULANIR. Doğrulanmazsa yavaş yola düşülür — tahmin edilmez.
    """
    if not terim:
        return None
    katli = tr_fold_ascii(metin)
    j = katli.find(terim)
    if j < 0:
        return None
    if len(katli) == len(metin):
        aday = metin[j:j + len(terim)]
        if tr_fold_ascii(aday) == terim:
            return j, j + len(terim)
    katli, harita = tr_katla_haritali(metin)
    j = katli.find(terim)
    if j < 0:
        return None
    return harita[j], harita[j + len(terim) - 1] + 1


def arama_terimleri(q: Optional[str]) -> tuple[str, ...]:
    """Sorguyu katlanmış, tekrarsız terimlere böler.

    Çok terimli sorgu **VE** ile birleşir ve terimler FARKLI alanlara
    dağılabilir: 'kuveyt konut' bir belgeyi, 'kuveyt' banka adında ve 'konut'
    kampanya türünde geçtiği için bulur. Tek alanda alt dize araması bunu
    bulamazdı — ve kullanıcının yazdığı en doğal sorgu tam olarak budur.
    """
    if not q:
        return ()
    return tuple(dict.fromkeys(t for t in tr_fold_ascii(q).split() if t))


def arama_parcasi(metin: str, s: int, e: int, *,
                  pencere: int = ARAMA_PENCERE) -> str:
    """Eşleşmenin çevresinden okunabilir bir parça keser.

    Kırpılan uçlara '…' konur: kullanıcı parçanın cümlenin tamamı olmadığını
    görmeli. Boşluklar tek boşluğa indirilir (özet metinlerinde satır sonları
    var ve tek satırlık bir listede satır sonu bağlamı bozar).
    """
    bas = max(0, s - pencere)
    son = min(len(metin), max(e, s) + pencere)
    parca = " ".join(metin[bas:son].split())
    if not parca:
        return ""
    return ("…" if bas > 0 else "") + parca + ("…" if son < len(metin) else "")


def arama_eslesmesi(row: Mapping[str, Any],
                    terimler: tuple[str, ...]) -> Optional[dict]:
    """Satır sorguyu karşılıyor mu — karşılıyorsa **NEDEN**.

    Dönüş: `{"alan": <sütun>, "parca": <bağlamıyla eşleşme>}` veya `None`.

    Kural: her terim EN AZ BİR alanda geçmeli (VE), ama terimler alanlara
    dağılabilir. Kanıt olarak en çok terim eşleşen alan seçilir; berabere
    kalırsa `ARAMA_ALANLARI` sırası karar verir. `ARAMA_ZAYIF_KANIT`
    alanları (adres) terim sayısı ne olursa olsun en sona düşer — gerekçe o
    sabitin yanında.

    Eşleşme kararı bütün dizgenin katlanmasıyla verilir (`tr_fold_ascii`,
    `kampanya_metin_suz()` ile AYNI çağrı), konum ise yalnız KAZANAN alan için
    haritalı katlamayla aranır. Ayrım maliyet içindir: bu uç tuş başına
    çağrılıyor ve 1774 satırın dört alanını karakter karakter katlamak
    ölçülebilir bir bedeldir.
    """
    if not terimler:
        return None
    bulunan: set[str] = set()
    en_iyi: Optional[tuple[tuple[int, int], str, str]] = None
    for alan in ARAMA_ALANLARI:
        ham = str(row.get(alan) or "")
        if not ham:
            continue
        katli = tr_fold_ascii(ham)
        eslesenler = [t for t in terimler if t in katli]
        if not eslesenler:
            continue
        bulunan.update(eslesenler)
        derece = (0 if alan in ARAMA_ZAYIF_KANIT else 1, len(eslesenler))
        if en_iyi is None or derece > en_iyi[0]:
            en_iyi = (derece, alan, eslesenler[0])
    if en_iyi is None or len(bulunan) != len(terimler):
        return None
    _, alan, terim = en_iyi
    ham = str(row.get(alan) or "")
    yer = arama_konumu(ham, terim)
    s, e = yer if yer is not None else (0, 0)
    return {"alan": alan, "parca": arama_parcasi(ham, s, e)}


def arama_suz(rows: list[dict], q: Optional[str]) -> list[dict]:
    """Satırları süzer ve her satıra `eslesme` ekler. **İki backend ORTAK.**

    SQL'de DEĞİL Python'da olmasının gerekçesi `kampanya_metin_suz()`
    docstring'inde yazılıdır ve birebir aynıdır: `LOWER()` iki backend'de aynı
    şeyi yapmaz ve ikisi de Türkçe için yanlıştır.

    **Boş sorgu BOŞ liste döndürür**, tam liste değil. `kampanya_metin_suz()`
    bir SÜZGEÇTİR ve süzgeç yokluğunda hiçbir şeyi elemez; burası bir ARAMADIR
    ve aranmamış bir şeyin sonucu yoktur. Boş sorguda 1774 satır döndürmek,
    komut paleti her açıldığında korpusun tamamını tel üzerinden geçirmek
    olurdu.
    """
    terimler = arama_terimleri(q)
    if not terimler:
        return []
    out: list[dict] = []
    for r in rows:
        eslesme = arama_eslesmesi(r, terimler)
        if eslesme is not None:
            kayit = dict(r)
            kayit["eslesme"] = eslesme
            out.append(kayit)
    return out


# --------------------------------------------------------------------------- #
# Çıkarıcı katmanı — hangi katman bu alanı üretti?
# --------------------------------------------------------------------------- #
#
# Geçerli küme `schemas.Extractor`ten TÜRETİLİR, burada elle yazılmaz: üç yerde
# (enum, `schema.sql` CHECK, `repository._SQLITE_SCHEMA` CHECK) aynı liste
# yaşıyor ve elle yazılan her kopya, birinin güncellenip ötekinin unutulacağı
# bir yer demektir. Enum tek doğruluk kaynağıdır; iki CHECK metninin onunla
# uyuştuğunu `tests/test_kisit_paritesi.py` denetler.
EXTRACTOR_DEGERLERI = tuple(e.value for e in Extractor)


def extractor_dogrula(deger: Optional[Any]) -> Optional[str]:
    """Çıkarıcı katman etiketini doğrular; `None` geçerlidir (bilinmiyor).

    ## Doğrulama neden Python'da, YALNIZCA şemadaki CHECK ile değil

    `belge_turu_dogrula()` ile birebir aynı gerekçe, ama burada bedeli
    ÖLÇÜLDÜ (2026-08-10). İki şema da CHECK kısıtını `CREATE TABLE` içinde
    tanımlar:

        extractor TEXT CHECK (extractor IS NULL OR extractor IN ('rule','ner','llm'))

    Bu, kısıtın **yalnız SIFIRDAN kurulan** bir veri tabanına ulaşması demektir.
    Zaten var olan bir DB'de `CREATE TABLE IF NOT EXISTS` hiçbir şey yapmaz ve
    göç yolu (`_SONRADAN_EKLENEN` / `_LATER_COLUMNS`) yalnız `ADD COLUMN`
    biliyor — SQLite `ALTER TABLE` ile CHECK eklemeye zaten İZİN VERMEZ.

    Ölçüm: teslim edilen `data/demo.db` (22,8 MB, 1774 belge) sütunu
    `extractor TEXT` olarak, KISITSIZ taşıyor. Salt-okunur açılıp doğrulandı;
    geçici bir kopyaya `extractor='UYDURMA'` yazma denemesi BAŞARILI oldu,
    `Repository(...)` ile açıp göç koşturmak da şemayı onarmadı. Aynı yazma
    taze bir DB'de `CHECK constraint failed` ile reddediliyor.

    Yani kısıt paritesi iki backend arasında değil, **taze DB ile diskteki DB**
    arasında delinmişti ve teslim edilen dosya yanlış taraftaydı.

    Şemalardaki CHECK KALDIRILMADI: taze DB'lerde ham SQL yazan çağıranları
    (ör. `rag.store` gibi `conn`'a doğrudan dokunan yollar) bedava yakalar.
    Ama SÖZLEŞME artık ona dayanmıyor — tek doğrulama noktası burasıdır ve iki
    backend de `insert_campaign()` içinde buradan geçer.

    `None` bilinçli olarak geçerlidir: sütun sonradan eklenmiş bir DB'deki eski
    satırlar `NULL` taşır ve o satırları uydurma bir katmana atamak yerine
    bilgi yokluğu saklanır (CLAUDE.md §19).
    """
    if deger is None:
        return None
    ham = deger.value if isinstance(deger, Extractor) else deger
    if ham in EXTRACTOR_DEGERLERI:
        return ham
    raise ValueError(
        f"extractor={deger!r} geçersiz. Geçerli: "
        f"{', '.join(repr(d) for d in EXTRACTOR_DEGERLERI)} veya None "
        "(bilinmiyor).")


# --------------------------------------------------------------------------- #
# NUL (0x00) baytı — PostgreSQL kabul etmez, SQLite eder
# --------------------------------------------------------------------------- #

ON_NUL_MODES = ("error", "strip")


class NulByteInText(ValueError):
    """Metinde PostgreSQL'in kabul etmediği NUL (0x00) baytı var."""


def on_nul_dogrula(mod: str) -> str:
    """`on_nul` kipini doğrular. İki backend de kurulumda bunu çağırır."""
    if mod not in ON_NUL_MODES:
        raise ValueError(
            f"on_nul={mod!r} geçersiz. Geçerli: {', '.join(ON_NUL_MODES)}")
    return mod


def nul_denetle(value: Optional[str], alan: str, baglam: str, *,
                on_nul: str = "error") -> Optional[str]:
    """Metni NUL baytına karşı denetler. **İki backend için ORTAK.**

    ## Neden SQLite de reddediyor, saklayabildiği halde

    PostgreSQL `TEXT` sütunları NUL baytı KABUL ETMEZ; SQLite eder. Denetim
    31 Tem 2026'da yalnız Postgres yoluna yazıldı ve gerçek bir veri hatası
    yakaladı (kuveyt-turk, 352 NUL baytı: metin değil ikili çöp, korpusa `.txt`
    olarak girmişti). Ama denetimin TEK backend'de yaşaması, "iki backend aynı
    veriyi kabul eder" iddiasını tersinden deliyordu: offline yolda (SQLite)
    sorunsuz kurulan bir korpus, üretime (Postgres) taşınırken düşüyordu — ve
    hata ancak GÖÇ ANINDA, kaynağı düzeltmenin en pahalı olduğu noktada
    görünüyordu. 849 belgelik aktarımda tam olarak bu yaşandı.

    Sıkı olan taraf kazanır: SQLite artık Postgres'in reddettiğini reddeder,
    böylece hata belgenin korpusa GİRDİĞİ anda çıkar. Ölçülen bedel sıfır —
    teslim edilen `data/demo.db`'de `instr(sütun, char(0)) > 0` sorgusu
    `campaigns` (raw_text, clean_text, ozet, source_url) ve `extracted_fields`
    (raw_value, source_span, canonical_value) sütunlarının hepsinde **0**
    satır döndürdü (ölçüldü 2026-08-10).

    `on_nul="strip"` kaçış kapısı ikisinde de durur ve UYARI loglar — ama
    dikkat: temizlik karakter offset'lerini KAYDIRIR, yani
    `span_start`/`span_end` doğrulaması bozulabilir. Bu yüzden varsayılan
    değildir.
    """
    if value is None or "\x00" not in value:
        return value
    adet = value.count("\x00")
    if on_nul == "strip":
        logger.warning(
            "%s alanında %d NUL baytı temizlendi (%s). DİKKAT: karakter "
            "offset'leri kaydı, span doğrulaması bozulabilir.",
            alan, adet, baglam)
        return value.replace("\x00", "")
    raise NulByteInText(
        f"{baglam}: '{alan}' alanı {adet} adet NUL (0x00) baytı içeriyor. "
        "PostgreSQL TEXT sütunları NUL kabul etmez; SQLite eder ama bu depo "
        "iki backend'de AYNI veriyi kabul etmek zorunda olduğu için SQLite "
        "yolu da reddeder (aksi halde hata ancak Postgres'e göç anında "
        "çıkardı). Genellikle metin yerine ikili (binary) bir belgenin "
        "korpusa .txt olarak girmesi demektir; kaynağı düzeltmek doğru "
        "çözümdür. Geçici olarak Repository/PostgresRepository(..., "
        "on_nul='strip') ile temizlenebilir, ama temizlik span offset'lerini "
        "kaydırır.")


@runtime_checkable
class RepositoryProtocol(Protocol):
    """İki depo uygulamasının paylaştığı yüzey.

    `backend` alanı çağıranın hangi yolda olduğunu bilmesini sağlar
    ('sqlite' | 'postgres'); vektör deposu seçimi (`rag.store.open_vector_store`)
    buna bakar.
    """

    backend: str

    def upsert_bank(self, name: str, slug: str,
                    website_url: Optional[str] = None,
                    bddk_active: bool = True) -> int: ...

    def insert_campaign(self, c: Campaign, clean_text: Optional[str] = None,
                        scraped_at: Optional[str] = None,
                        campaign_status: Optional[str] = None) -> int: ...

    def set_belge_turu(self, atamalar: Mapping[int, Optional[str]]) -> int: ...

    def set_ozet(self, atamalar: Mapping[int, Optional[str]]) -> int: ...

    def set_ozet_sebep(self, atamalar: Mapping[int, Optional[str]]) -> int: ...

    def field_value(self, campaign_id: int, field_name: str) -> Any: ...

    def query_fields(self, field_name: str, *,
                     sozlesme_dahil: bool = False) -> list[dict]: ...

    def campaign_text(self, campaign_id: int) -> Optional[dict]: ...

    def all_banks(self) -> list[dict]: ...

    def counts(self) -> dict[str, int]: ...

    def belge_turu_counts(self) -> dict[str, int]: ...

    def campaign_status_counts(self) -> dict[str, int]: ...

    def field_coverage(self, *, sozlesme_dahil: bool = True) -> dict[str, int]: ...

    def bank_field_coverage(self) -> dict[str, dict[str, int]]: ...

    def campaigns_per_bank(self) -> dict[str, int]: ...

    def fields_by_extractor(self, *,
                            sozlesme_dahil: bool = True) -> dict[str, int]: ...

    def all_campaigns(self, *, belge_turu: Optional[str] = None,
                      bank: Optional[str] = None,
                      campaign_type: Optional[str] = None,
                      status: Optional[str] = None,
                      q: Optional[str] = None,
                      govde: bool = True) -> list[dict]: ...

    def search_campaigns(self, q: Optional[str], *,
                         bank: Optional[str] = None,
                         campaign_type: Optional[str] = None,
                         belge_turu: Optional[str] = None,
                         status: Optional[str] = None) -> list[dict]: ...

    def close(self) -> None: ...


def finalize_campaign_text(campaign: dict, field_rows: list[dict]) -> dict:
    """`campaign_text()` çıktısını iki backend için AYNI biçimde tamamlar.

    Girdi:
      - `campaign`: campaigns+banks JOIN satırının dict hali
        (id, raw_text, clean_text, source_url, campaign_type, bank, bank_name)
      - `field_rows`: extracted_fields satırları (canonical_value JSON METNİ olarak)

    Yaptıkları:
      - `span_reference` / `text` seçimi: span offset'leri `clean_text` üzerinde
        ölçülür. `raw_text` ile karıştırmak offset'leri kaydırır, bu yüzden
        hangi metnin kullanıldığı yanıtta açıkça belirtilir.
      - `canonical_value` JSON çözümü.
      - `span_verified`: saklanan offset gerçekten `raw_value`'yu mu gösteriyor?
        Bozuksa arayüz yanlış yeri boyamaktansa hiç boyamamalı.
    """
    d = dict(campaign)
    d["span_reference"] = "clean_text" if d.get("clean_text") else "raw_text"
    d["text"] = d.get("clean_text") or d.get("raw_text") or ""
    d["fields"] = []
    for row in field_rows:
        alan = dict(row)
        alan["canonical_value"] = json.loads(alan["canonical_value"])
        s, e = alan.get("span_start"), alan.get("span_end")
        alan["span_verified"] = bool(
            s is not None and e is not None
            and 0 <= s <= e <= len(d["text"])
            and d["text"][s:e] == (alan.get("raw_value") or ""))
        d["fields"].append(alan)
    return d


class ThreadSafeRepository:
    """Bir depoyu tek bir `RLock` arkasında serileştirir. **Hata düzeltmesi.**

    ## Neden var (SQLite tarafı)

    `sqlite3.connect()` varsayılan olarak bağlantıyı **oluşturan thread'e
    kilitler** (`check_same_thread=True`). FastAPI ise `def` (async olmayan)
    uçları bir threadpool worker'ında koşturur. Bağlantı uygulama kurulumunda
    (ana thread) açıldığı için DB'ye dokunan HER uç — `/banks`, `/campaigns`,
    `/compare`, `/chat` — istek anında şu hatayla düşüyordu:

        sqlite3.ProgrammingError: SQLite objects created in a thread can only
        be used in that same thread.

    Dashboard'un boş tablo göstermesinin sebebi buydu; arayüz `catch` ile
    sessizce boş listeye düşüyordu. Çözüm iki parçalıdır ve ikisi de gerekir:
    bağlantı `check_same_thread=False` ile açılır (`Repository(...,
    check_same_thread=False)`) VE tüm erişim burada serileştirilir.

    ## Neden Postgres tarafında da gerekir

    `psycopg` DB-API `threadsafety = 2` ilan eder: thread'ler bir bağlantıyı
    PAYLAŞABİLİR. Paylaşabilmek eşzamanlı kullanımın DOĞRU olduğu anlamına
    gelmez — işlem (transaction) sınırı bağlantı başınadır. `insert_campaign()`
    gibi metotlar sonunda `commit()` çağırdığı için, iki thread aynı bağlantıda
    çalışırsa birinin `commit()`'i diğerinin YARIM işini kalıcılaştırır ve
    `cursor` yaşam döngüleri iç içe geçer. Aynı `RLock` bu yüzden Postgres
    yolunda da uygulanır.

    ## Sınır: `conn`'a doğrudan erişen kod

    `src/rag/store.py` (`PgVectorStore` / `SqliteVectorStore`) depo nesnesinden
    `repo.conn`'u ALIR ve sorguları kendisi koşturur; o yol bu kilidin dışında
    kalır. `conn` burada bilinçli olarak açığa çıkarılır (aksi halde vektör
    deposu hiç açılamazdı) ama `lock` da açığa çıkarılır: bağlantıya doğrudan
    dokunan çağıran, `with repo.lock:` almalıdır. API demo yolu bu koda
    girmiyor (`RAG_RETRIEVER=keyword` varsayılanı), bu yüzden bugün pratikte
    tetiklenmez — ama sessiz bir varsayım olarak kalmasın diye yazılıdır.
    """

    def __init__(self, inner: RepositoryProtocol):
        self._inner = inner
        self.lock = threading.RLock()
        self.backend: str = inner.backend

    @property
    def inner(self) -> RepositoryProtocol:
        """Sarmalanan depo (testler ve backend'e özgü doğrulamalar için)."""
        return self._inner

    @property
    def conn(self) -> Any:
        """Ham bağlantı — bkz. sınıf docstring'i "Sınır" başlığı."""
        return self._inner.conn  # type: ignore[attr-defined]

    # --- sözleşme metotları (hepsi kilit altında) ---
    def upsert_bank(self, name: str, slug: str,
                    website_url: Optional[str] = None,
                    bddk_active: bool = True) -> int:
        with self.lock:
            return self._inner.upsert_bank(name, slug, website_url, bddk_active)

    def insert_campaign(self, c: Campaign, clean_text: Optional[str] = None,
                        scraped_at: Optional[str] = None,
                        campaign_status: Optional[str] = None) -> int:
        with self.lock:
            return self._inner.insert_campaign(
                c, clean_text, scraped_at, campaign_status)

    def set_belge_turu(self, atamalar: Mapping[int, Optional[str]]) -> int:
        with self.lock:
            return self._inner.set_belge_turu(atamalar)

    def set_ozet(self, atamalar: Mapping[int, Optional[str]]) -> int:
        with self.lock:
            return self._inner.set_ozet(atamalar)

    def set_ozet_sebep(self, atamalar: Mapping[int, Optional[str]]) -> int:
        with self.lock:
            return self._inner.set_ozet_sebep(atamalar)

    def field_value(self, campaign_id: int, field_name: str) -> Any:
        with self.lock:
            return self._inner.field_value(campaign_id, field_name)

    def query_fields(self, field_name: str, *,
                     sozlesme_dahil: bool = False) -> list[dict]:
        with self.lock:
            return self._inner.query_fields(
                field_name, sozlesme_dahil=sozlesme_dahil)

    def campaign_text(self, campaign_id: int) -> Optional[dict]:
        with self.lock:
            return self._inner.campaign_text(campaign_id)

    def all_banks(self) -> list[dict]:
        with self.lock:
            return self._inner.all_banks()

    def all_campaigns(self, *, belge_turu: Optional[str] = None,
                      bank: Optional[str] = None,
                      campaign_type: Optional[str] = None,
                      status: Optional[str] = None,
                      q: Optional[str] = None,
                      govde: bool = True) -> list[dict]:
        with self.lock:
            return self._inner.all_campaigns(
                belge_turu=belge_turu, bank=bank, campaign_type=campaign_type,
                status=status, q=q, govde=govde)

    def search_campaigns(self, q: Optional[str], *,
                         bank: Optional[str] = None,
                         campaign_type: Optional[str] = None,
                         belge_turu: Optional[str] = None,
                         status: Optional[str] = None) -> list[dict]:
        with self.lock:
            return self._inner.search_campaigns(
                q, bank=bank, campaign_type=campaign_type,
                belge_turu=belge_turu, status=status)

    def counts(self) -> dict[str, int]:
        with self.lock:
            return self._inner.counts()

    def belge_turu_counts(self) -> dict[str, int]:
        with self.lock:
            return self._inner.belge_turu_counts()

    def campaign_status_counts(self) -> dict[str, int]:
        with self.lock:
            return self._inner.campaign_status_counts()

    def field_coverage(self, *, sozlesme_dahil: bool = True) -> dict[str, int]:
        with self.lock:
            return self._inner.field_coverage(sozlesme_dahil=sozlesme_dahil)

    def bank_field_coverage(self) -> dict[str, dict[str, int]]:
        with self.lock:
            return self._inner.bank_field_coverage()

    def fields_by_extractor(self, *,
                            sozlesme_dahil: bool = True) -> dict[str, int]:
        with self.lock:
            return self._inner.fields_by_extractor(
                sozlesme_dahil=sozlesme_dahil)

    def campaigns_per_bank(self) -> dict[str, int]:
        with self.lock:
            return self._inner.campaigns_per_bank()

    def close(self) -> None:
        with self.lock:
            self._inner.close()
