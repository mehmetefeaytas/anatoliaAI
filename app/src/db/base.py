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

    def field_value(self, campaign_id: int, field_name: str) -> Any: ...

    def query_fields(self, field_name: str, *,
                     sozlesme_dahil: bool = False) -> list[dict]: ...

    def campaign_text(self, campaign_id: int) -> Optional[dict]: ...

    def all_banks(self) -> list[dict]: ...

    def counts(self) -> dict[str, int]: ...

    def belge_turu_counts(self) -> dict[str, int]: ...

    def field_coverage(self, *, sozlesme_dahil: bool = True) -> dict[str, int]: ...

    def campaigns_per_bank(self) -> dict[str, int]: ...

    def fields_by_extractor(self, *,
                            sozlesme_dahil: bool = True) -> dict[str, int]: ...

    def all_campaigns(self, *,
                      belge_turu: Optional[str] = None) -> list[dict]: ...

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

    def all_campaigns(self, *, belge_turu: Optional[str] = None) -> list[dict]:
        with self.lock:
            return self._inner.all_campaigns(belge_turu=belge_turu)

    def counts(self) -> dict[str, int]:
        with self.lock:
            return self._inner.counts()

    def belge_turu_counts(self) -> dict[str, int]:
        with self.lock:
            return self._inner.belge_turu_counts()

    def field_coverage(self, *, sozlesme_dahil: bool = True) -> dict[str, int]:
        with self.lock:
            return self._inner.field_coverage(sozlesme_dahil=sozlesme_dahil)

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
