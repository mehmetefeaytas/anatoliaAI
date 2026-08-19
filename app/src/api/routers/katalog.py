"""Katalog okuma uçları — banka/belge listeleri ve sistem durumu.

`api/main.py`'den taşındı (19 Ağu 2026, kademeli bölmenin 2. adımı; plan:
docs/rapor/api-bolme-plani.md). Uç nokta gövdeleri BİREBİR taşındı —
davranış değişikliği yok, yalnız yer değişikliği.

## Neden factory, neden parametre

`repo` ve `llm` closure değişkenleriydi; burada factory parametresi oldular ve
adları korundu, böylece gövdeler değişmeden taşınabildi.

`otorite_sluglari` ve `scoring_direction` da parametre olarak geçiliyor,
`main`'den import EDİLMİYOR. Sebep: `main` bu modülü import ediyor; ters yönde
bir import dairesel bağımlılık kurardı. Parametre geçmek ayrıca uçları
bağımsız test edilebilir kılıyor — sahte bir `otorite_sluglari` ile
`/banks` süzmesi config dosyasına hiç dokunmadan sınanabilir.
"""

from __future__ import annotations

from typing import Any, Callable, Optional

from ...db.base import (
    ARAMA_AZAMI_LIMIT,
    ARAMA_VARSAYILAN_LIMIT,
    belge_turu_dogrula,
    kampanya_durumu_dogrula,
)
from ...extraction.llm.schema import EXTRACTION_FIELDS
from ..sabitler import FIELD_LABELS

# `Response` MODÜL GLOBAL'İNDE olmak zorunda. `from __future__ import
# annotations` yüzünden tip anotasyonları birer dizedir ve FastAPI onları
# çalışma anında modül global'lerinden çözer; import fonksiyon içinde kalırsa
# `response: Response` çözülemez ve FastAPI onu bir QUERY parametresi sanar —
# uç her istekte 422 verir. Bu tuzak `api/main.py`'de bir kez yaşandı ve orada
# aynı kalıpla çözülmüş; taşıma sırasında birebir tekrarlandı ve
# `GET /campaigns` 422 döndürerek kendini gösterdi.
try:  # pragma: no cover - fastapi yokluğu build_app()'te raporlanır
    from fastapi import Response
except ModuleNotFoundError:  # pragma: no cover
    Response = None  # type: ignore[assignment]


def router_kur(
    repo: Any,
    llm: Any,
    *,
    otorite_sluglari: Callable[[], frozenset[str]],
    scoring_direction: Callable[[str], tuple[str, str]],
):
    """Katalog uçlarını taşıyan `APIRouter`'ı kurar.

    `fastapi` import'u fonksiyon içinde: paket kurulu değilse `main.build_app()`
    zaten anlaşılır bir hata veriyor ve bu modülün import edilmesi tek başına
    çökmemeli (çekirdek kural/normalizasyon katmanı saf stdlib ile çalışır).
    """
    from fastapi import APIRouter, HTTPException

    r = APIRouter()

    @r.get("/health")
    def health():
        """Sağlık + **hangi veri tabanına bağlıyız**.

        `backend` alanı bilinçli olarak açığa çıkarılır: `DATABASE_URL`
        verildiği hâlde sistemin SQLite'ta koşuyor olması (ya da tersi) tam
        olarak bu projede avlanan hata sınıfıdır ve dışarıdan görünmeden
        anlaşılamaz.
        """
        return {"status": "ok", "llm": llm.available, "backend": repo.backend}

    @r.get("/banks")
    def banks(otorite_kaynaklari_dahil: bool = False):
        """BDDK Liste 77 bankaları (CLAUDE.md §13).

        OTORİTE KAYNAK SÜZMESİ: korpus yalnızca bankalardan beslenmiyor —
        fıkhî terimlerin TANIMI banka sayfalarında yok, bankalar terimi
        kullanır ama açıklamaz (ölçüldü: `docs/rapor/musaraka-veri-boslugu.md`).
        Bu yüzden TKBB gibi sektör otoriteleri de korpus kaynağıdır ve
        `config/banks.yaml` içinde `bddk_active: false` ile durur — ingest
        yolu (`src/pipeline.py::run_pipeline`) banka kayıtlarını o dosyadan
        sürdüğü için başka türlü korpusa giremezler.

        Ama KAYNAK OLMAK ile BANKA OLMAK aynı şey değildir. Süzme olmadan
        TKBB bu uçtan "11. banka" olarak dönüyordu ve arayüzdeki banka
        listesine düşüyordu; jüri kıyas ekranında TKBB satırı görseydi bu
        doğrudan bir kusur olurdu (CLAUDE.md §13, §17).

        `/compare` bu riski ZATEN taşımıyor: kıyas tablosu belge türüne göre
        süzülüyor ve otorite belgelerinin ikisi de `belge_turu='sozlesme'`
        (ölçüldü) — yani hiçbir zaman kıyas satırı üretmediler. Açıkta kalan
        tek yer banka KATALOĞUYDU, burası.

        Süzme GİZLEME DEĞİLDİR: `?otorite_kaynaklari_dahil=true` tam listeyi
        döndürür, böylece korpusun gerçek kaynak kümesi denetlenebilir kalır.

        Ayrım `bddk_active` ÜZERİNDEN YAPILMAZ. O alan "gerçek banka ama BDDK
        lisansı aktif değil" demektir ve lisansı düşmüş GERÇEK bir bankayı da
        katalogdan silerdi. Ayrım `config/banks.yaml`'daki `otorite_kaynak`
        bayrağıdır — yani banka/kaynak kararı config-driven kalır (CLAUDE.md
        §18-3) ve DB şeması değişmeden çalışır.
        """
        rows = repo.all_banks()
        if otorite_kaynaklari_dahil:
            return rows
        otorite = otorite_sluglari()
        return [b for b in rows if b.get("slug") not in otorite]

    @r.get("/campaigns")
    def campaigns(response: Response, govde: bool = False,
                  q: Optional[str] = None, bank: Optional[str] = None,
                  type: Optional[str] = None,
                  belge_turu: Optional[str] = None,
                  status: Optional[str] = None,
                  limit: Optional[int] = None, offset: int = 0):
        """Belge listesi — ÜSTVERİ. Ham gövde yalnızca `?govde=true` ile gelir.

        ## `govde=False` varsayılanı bir hata düzeltmesidir

        Ölçüldü (2026-08-11): `curl -s localhost:8000/campaigns | wc -c` =
        **10.339.015 bayt**. Uç 1774 satırı `raw_text` ile birlikte
        döndürüyordu ve arayüz o alanı HİÇBİR YERDE okumuyordu — `web/app`
        içinde tek geçtiği yer `lib/api.ts`'deki tip tanımıydı. Yani yükün
        neredeyse tamamı, hiç kimsenin bakmadığı bir alandı ve dashboard her
        açılışta onu indiriyordu.

        Alan SİLİNMEDİ, kapatıldı: `?govde=true` bugünkü yanıtı birebir geri
        verir. Ham metne gerçekten ihtiyaç duyan yol
        `GET /campaigns/{id}/text`tir (metin + offsetler + bloklar) ve o uç
        tek belge döndürür.

        ## Yanıt ÇIPLAK BİR LİSTEDİR — zarf (envelope) yok

        Toplam kayıt sayısı gövdeye DEĞİL `X-Toplam-Kayit` başlığına yazılır.
        Gövdeyi `{"toplam": n, "kayitlar": [...]}` biçimine sokmak her
        çağıranı aynı anda kırardı; başlık, süzgeç uygulanmış toplamı
        sayfalamadan bağımsız taşır ve eski istemciler onu görmezden gelir.

        ## Süzgeçler

        `q` serbest metin (üstveride arar — gerekçe:
        `db.base.kampanya_metin_suz()`), `bank` / `type` / `belge_turu` /
        `status` kesin eşleşmeli. Süzme DEPO KATMANINDA yapılır, burada değil:
        iki backend de aynı kümeyi görmek zorunda (`db.base.kampanya_where()`).

        `status='damgasiz'` üçüncü bir kovadır: `campaign_status IS NULL`
        "geçerli" demek DEĞİLDİR, "damgasız" demektir ve korpusun %74'ü bu
        durumdadır. `active` ile birleştirmek, doğrulanmamış 1316 belge için
        doğrulanmış bir iddia uydurmak olurdu.

        `limit`/`offset` **depoya değil, burada** uygulanır: `X-Toplam-Kayit`
        süzgeç sonrası toplamı bildirmek zorunda ve sayfa dilimi alındıktan
        sonra o sayı geri getirilemezdi (ikinci bir COUNT sorgusu, iki
        backend'de tutarlı tutulması gereken ikinci bir sorgu demekti).
        `limit` varsayılanı `None` = sayfalama yok; süzgeçsiz çağrı bugünkü
        tam listeyi verir.
        """
        try:
            belge_turu_dogrula(belge_turu)
            kampanya_durumu_dogrula(status)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e
        if offset < 0 or (limit is not None and limit < 0):
            raise HTTPException(
                status_code=400,
                detail="limit ve offset negatif olamaz "
                       f"(limit={limit}, offset={offset}).")

        rows = repo.all_campaigns(bank=bank, campaign_type=type,
                                  belge_turu=belge_turu, status=status, q=q,
                                  govde=govde)
        response.headers["X-Toplam-Kayit"] = str(len(rows))
        if limit is None:
            return rows[offset:]
        return rows[offset:offset + limit]

    @r.get("/search")
    def search(q: str = "", limit: int = ARAMA_VARSAYILAN_LIMIT):
        """Gruplu arama: bankalar, belgeler, kampanya türleri — tek istekte.

        ## Neden ayrı bir uç, `/campaigns?q=` yetmiyor mu

        Yetmiyor, iki sebeple:

        1. **Gruplama.** Kullanıcı 'kuveyt' yazdığında aradığı şey bazen bir
           banka, bazen bir belge, bazen bir kampanya türüdür. Düz bir belge
           listesi bu üç niyeti tek kovaya sıkıştırır ve en sık istenen
           (bankaya git) en pahalı yol olur.
        2. **`eslesme` — NEDEN eşleşti.** Yanıttaki her belge, hangi alanın
           hangi bağlamda eşleştiğini taşır. Bu ürünün her yüzeyinde bir iddia
           kaynağını gösterir; arama bir istisna olmamalı. Kanıtsız bir arama
           kutusu, kullanıcının sonucu doğrulayamadığı bir kutudur.

        ## Maliyet

        Yalnız KISA sütunlar taranır (`db.base.ARAMA_ALANLARI`): banka adı,
        kampanya türü, özet, adres. Ham gövde **taranmaz** — korpusta ~10 MB
        ve bu uç tuş başına çağrılıyor. Belge içinde arama `/chat` yoludur.

        ## Sayılar

        `toplam` süzgeç sonrası GERÇEK sayıları bildirir; `limit` yalnız
        gösterilen listeleri kırpar. Kırpılmış bir listeyi tam sanmak, komut
        paletinde 'başka sonuç yok' izlenimi verirdi.

        `banks[].campaign_count` o bankanın KORPUSTAKİ TOPLAM belge sayısıdır,
        eşleşen belge sayısı değil: grup bir gezinme hedefidir ('bu bankaya
        git'), bir sonuç sayacı değil. İki sayıyı aynı adla basmamak için fark
        burada yazılıdır.

        Otorite kaynakları (TKBB gibi sektör kuruluşları) `banks` grubundan
        SÜZÜLÜR — `/banks` ile aynı gerekçe: kaynak olmak banka olmak değildir.
        Belgeleri `campaigns` grubunda GÖRÜNMEYE devam eder; süzme gizleme
        değildir.
        """
        if limit < 0:
            raise HTTPException(
                status_code=400, detail=f"limit negatif olamaz (limit={limit}).")
        limit = min(limit, ARAMA_AZAMI_LIMIT)

        kayitlar = repo.search_campaigns(q)
        otorite = otorite_sluglari()
        banka_sayilari = repo.campaigns_per_bank()

        gorulen: dict[str, Optional[str]] = {}
        turler: set[str] = set()
        for r in kayitlar:
            gorulen.setdefault(r["bank"], r.get("bank_name"))
            if r.get("campaign_type"):
                turler.add(r["campaign_type"])

        banks = sorted(
            ({"slug": slug, "name": ad or slug,
              "campaign_count": banka_sayilari.get(slug, 0)}
             for slug, ad in gorulen.items() if slug not in otorite),
            key=lambda b: (-b["campaign_count"], b["slug"]))
        types = sorted(turler)
        campaigns = [
            {"id": r["id"], "bank": r["bank"], "bank_name": r.get("bank_name"),
             "campaign_type": r.get("campaign_type"),
             "belge_turu": r.get("belge_turu"),
             "campaign_status": r.get("campaign_status"),
             "eslesme": r["eslesme"]}
            for r in kayitlar[:limit]]

        return {
            "sorgu": q,
            "banks": banks[:limit],
            "campaigns": campaigns,
            "types": types[:limit],
            "toplam": {"banks": len(banks), "campaigns": len(kayitlar),
                       "types": len(types)},
        }

    @r.get("/stats")
    def stats():
        """Korpusun tek bakışta sayısal özeti — depo metotlarının BİLEŞİMİ.

        ## Neden ayrı bir uç

        Arayüz bu sayıları eskiden `/campaigns` yanıtından kendi sayıyordu ve
        bunun bedeli 10,3 MB'lık bir istekti (bkz. `campaigns()`); üstelik
        istemcide sayılabilen şey yalnızca "kaç satır var"dı — alan kapsamı,
        katman dağılımı ve banka başına ÇEŞİT sayısı `extracted_fields`
        tablosunu gerektiriyor ve oraya arayüzün hiç erişimi yok.

        ## Burada YENİ SQL YOK

        Her sayı zaten sözleşmede olan ve ayrı ayrı test edilen depo
        metotlarından gelir. Yeni olan tek şey iki metodun kendisidir
        (`campaign_status_counts`, `bank_field_coverage`) ve ikisi de İKİ
        backend'de birden yazıldı. Bu uç hiçbir sayıyı kendi hesaplamaz —
        hesaplasaydı aynı bilgi hem depoda hem burada yaşardı.

        `campaign_types` `all_campaigns()`ten türetilir ve **gövdesiz** okur:
        listenin kendisi zaten üstveridir, ham metne gerek yok.

        ## `korpus.banks` ile `GET /banks` neden farklı sayabilir

        Buradaki sayı KORPUS KAYNAĞI sayısıdır ve TKBB gibi sektör
        otoritelerini de içerir (`/banks` onları süzer — o ucun docstring'i).
        İki sayı farklı soruların cevabıdır: "korpus kaç kaynaktan beslendi"
        ve "kaç BANKA kıyaslanıyor". Aynı isimle iki farklı sayı basmamak için
        fark burada yazılıdır.
        """
        turler = sorted({c.get("campaign_type")
                         for c in repo.all_campaigns(govde=False)
                         if c.get("campaign_type")})
        return {
            "korpus": repo.counts(),
            "belge_turu": repo.belge_turu_counts(),
            "campaign_status": repo.campaign_status_counts(),
            "banka_basina": repo.campaigns_per_bank(),
            "banka_kapsami": repo.bank_field_coverage(),
            "campaign_types": turler,
            "alan_kapsami": repo.field_coverage(),
            "katman": repo.fields_by_extractor(),
            # `llm.available` `/health` ile AYNI kaynaktan okunur; arayüz
            # "LLM kapalı" rozetini iki ayrı uçtan farklı öğrenmemeli.
            "llm": {"acik": llm.available},
            "backend": repo.backend,
        }

    @r.get("/fields")
    def fields():
        """Çıkarılan 12 alan + Türkçe etiket + sıralama yönü (UI çipleri için)."""
        out = []
        for name in EXTRACTION_FIELDS:
            direction, label = scoring_direction(name)
            out.append({
                "field": name,
                "label": FIELD_LABELS.get(name, name),
                "direction": direction,
                "direction_label": label,
                "comparable_field": direction != "unranked",
            })
        return out

    return r
