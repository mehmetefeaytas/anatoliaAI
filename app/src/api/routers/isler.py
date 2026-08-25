"""Arka plan işleri — korpus tazeleme ve AI özeti üretimi uçları.

`api/main.py`'den taşındı (19 Ağu 2026, kademeli bölmenin 3. adımı; plan:
docs/rapor/api-bolme-plani.md). Uç nokta gövdeleri BİREBİR taşındı —
davranış değişikliği yok, yalnız yer değişikliği.

## Neden factory, neden bu parametreler

Bu grupta closure yüzeyi çok dar: `repo` yalnız BİR uçta (`/refresh/cancel`)
kullanılıyor. Asıl bağımlılık iki İŞ YÖNETİCİSİ nesnesidir (`tazeleme`,
`ozet_isi`) ve onlar `build_app()` kapsamında kalmak ZORUNDA — çünkü koşan
işin durumunu bellekte tutuyorlar. Modül seviyesine çıkarılsalar süreç ömrü
boyunca paylaşılan duruma dönüşür ve iki test birbirinin işini görür.

`banka_bul` da parametre: `main`'de closure olarak tanımlı bir yardımcı ve
buraya taşınması `repo`yu da beraberinde çekerdi.

## `Request` MODÜL GLOBAL'İNDE olmak zorunda

`from __future__ import annotations` tip anotasyonlarını dizeye çeviriyor ve
FastAPI onları çalışma anında modül global'lerinden çözüyor. Import fonksiyon
içinde kalırsa `request: Request` çözülemez ve FastAPI onu bir QUERY
parametresi sanar — uç her istekte 422 verir. Bu tuzak `main.py`'de bir kez,
`routers/katalog.py`'ye taşımada bir kez daha yaşandı (`Response` ile). Üçüncü
kez olmasın diye burada baştan modül seviyesinde.
"""

from __future__ import annotations

from typing import Any, Callable

from ...scraping.tazeleme import TazelemeMesgul, son_tazeleme_oku
from ...scraping.tazeleme import onizleme as tazeleme_onizleme
from ...summarize.ozet_isi import LlmKapali, OzetMesgul
from .. import gunluk

try:  # pragma: no cover - fastapi yokluğu build_app()'te raporlanır
    from fastapi import Request
except ModuleNotFoundError:  # pragma: no cover
    Request = None  # type: ignore[assignment]

try:  # pragma: no cover - pydantic yokluğu build_app()'te raporlanır
    from pydantic import BaseModel
except ModuleNotFoundError:  # pragma: no cover
    BaseModel = None  # type: ignore[assignment]

if BaseModel is not None:  # pragma: no branch
    class RefreshReq(BaseModel):
        """`POST /refresh` gövdesi — tek bankayı ağdan tazeleyen operatör eylemi.

        Yalnız banka slug'ı alınır. Gecikme, azami belge sayısı ve robots.txt
        uyumu İSTEMCİDEN AYARLANAMAZ: etik toplama kısıtları (CLAUDE.md §14)
        bir istemci tercihi değildir ve arayüzden gevşetilebilir olmamalıdır.

        `main.py`'den buraya taşındı (19 Ağu 2026): tek kullanıcısı bu
        modüldeki `POST /refresh` ucu. Pydantic modeli de `Request` ile aynı
        sebeple MODÜL GLOBAL'İNDE olmak zorunda — FastAPI tip anotasyonunu
        çalışma anında buradan çözüyor.
        """

        bank: str


def router_kur(
    app: Any,
    repo: Any,
    *,
    tazeleme: Any,
    ozet_isi: Any,
    banka_bul: Callable[..., Any],
    raw_dir: str,
):
    """Tazeleme ve özet işi uçlarını taşıyan `APIRouter`'ı kurar.

    `app` BİLEREK parametre: gövdeler yöneticilere `app.state.tazeleme` /
    `app.state.ozet_isi` üzerinden erişiyor ve bu bir TEST KANCASIdır —
    kodda gerekçesi yazılı ("testler sahte bir iş geçirebilsin diye uygulama
    durumuna asılır"). Doğrudan parametreye çevirmek o kancayı kırar ve
    mevcut testler sahte iş geçiremez hâle gelirdi. Taşımanın kuralı davranışı
    korumaktı; bu yüzden `app` referansı geçiliyor.
    """
    from fastapi import APIRouter, HTTPException

    RAW_DIR = raw_dir  # gövdeler bu adı kullanıyor; taşıma birebir kalsın
    r = APIRouter()

    @r.get("/refresh/preview")
    def refresh_preview(bank: str):
        """Düğmeye basılmadan önce ne olacağı — bu uç AĞA ÇIKMAZ.

        Kaç istek atılacağı, kabaca ne kadar süreceği ve nereye yazılacağı
        `banks.yaml` ile sabitlerden türetilir. Ön izlemenin kendisi ağ
        gerektirseydi, "internet var mı" sorusunu sormanın maliyeti yine
        internet olurdu.
        """
        return tazeleme_onizleme(banka_bul(bank), raw_dir=RAW_DIR,
                                 azami_belge=tazeleme.azami_belge,
                                 gecikme_sn=tazeleme.gecikme_sn)

    @r.post("/refresh", status_code=202)
    def refresh_start(request: Request, req: RefreshReq):
        """Tazelemeyi arka planda başlatır ve iş kaydını döndürür.

        SENKRON DEĞİL, bilerek: alan başına 2–5 saniye gecikmeyle 35 belge
        çekmek dakikalar sürer. Senkron bir uç hem tarayıcıyı hem sunucunun
        iş parçacığını kilitlerdi; ilerleme de görünmezdi. Tazeleme bittiğinde
        aynı iş parçacığında koşan alt akış (bayat özet düşürme) saniyenin
        altında biter; kendi işi olacak kadar büyük değildir.

        Koşan bir iş varken ikinci istek 409 ile reddedilir — sıraya alınmaz,
        çünkü sessiz bir kuyruk operatöre yanlış bir "başladı" izlenimi verir.
        """
        bank = banka_bul(req.bank)
        try:
            kayit = tazeleme.baslat(bank)
        except TazelemeMesgul as exc:
            raise HTTPException(
                status_code=409,
                detail=f"Şu anda {exc.calisan_banka} tazeleniyor. "
                       "Aynı anda tek tazeleme çalışır; bitmesini bekleyin "
                       "ya da durdurun.") from exc
        # İşlem günlüğüne DÜŞEN şey burada belirlenir: hangi banka, hangi iş,
        # nereye yazılacak. "Kaç dosya" bu anda HENÜZ BİLİNMEZ (iş arka planda
        # yeni başladı) ve uydurulmaz; sayaçlar `is_id` ile
        # `GET /refresh/status/{is_id}` üzerinden bağlanır. Günlüğün cevapladığı
        # soru zaten "kim, ne zaman, neyi tetikledi"ydi.
        gunluk.eylem_bildir(request, is_id=kayit.get("is_id"),
                            banka=bank.slug, banka_adi=bank.name,
                            hedef_dizin=kayit.get("hedef_dizin"))
        return kayit

    @r.get("/refresh/status")
    def refresh_last_status():
        """En son başlatılan işin durumu — hiç iş yoksa `null`."""
        return tazeleme.son_is()

    @r.get("/refresh/status/{job_id}")
    def refresh_status(job_id: str):
        """Bir işin anlık durumu (ilerleme + sayaçlar + hatalar)."""
        kayit = tazeleme.durum(job_id)
        if kayit is None:
            raise HTTPException(status_code=404,
                                detail="Böyle bir tazeleme işi yok.")
        return kayit

    @r.post("/refresh/cancel/{job_id}")
    def refresh_cancel(request: Request, job_id: str):
        """Durdurma ister. İş sıradaki belge sınırında durur.

        Çekim evresi diske hiçbir şey yazmadığı için durdurulan bir iş ham
        arşivde yarım belge bırakmaz.
        """
        kayit = tazeleme.iptal_et(job_id)
        if kayit is None:
            raise HTTPException(status_code=404,
                                detail="Böyle bir tazeleme işi yok.")
        # `is_id` ara katman tarafından yol parametresinden ZATEN okunuyor;
        # burada eklenen şey iptalin neye dokunduğu (banka + o anki sayaç).
        gunluk.eylem_bildir(request, banka=kayit.get("bank"),
                            yazilan_dosya=kayit.get("yazilan_dosya"),
                            durum_adi=kayit.get("durum"))
        return kayit

    @r.get("/refresh/last-summary")
    def refresh_last_summary():
        """Her banka için EN SON TAMAMLANMIŞ tazelemenin kalıcı özeti.

        `TazelemeDurumu` tamamen bellek içidir (iş/süreç bitince kaybolur);
        bu uç onun aksine `data/son-tazeleme.json`'dan okur — panelin "en son
        ne zaman tazeleme yapıldı, kaç belge değişti/yeni geldi" iddiasını
        süreç yeniden başlasa da göstermesi için (bkz. `tazeleme.py::
        son_tazeleme_yaz`). DB şemasına dokunulmadı, bilinçli tercih.

        Hiç tazeleme yapılmamışsa (dosya yok) BOŞ sözlük döner, 404 VERMEZ —
        "henüz veri yok" bir hata değil.

        Dönüş biçimi — banka slug'ı → özet:
        ```json
        {
          "<banka-slug>": {
            "bank": "<banka-slug>",
            "bank_name": "<Banka Adı>",
            "is_id": "<son iş kimliği>",
            "bitis": "<ISO-8601 zaman damgası>",
            "yeni": 0, "degisen": 0, "ayni": 0, "hata": 0,
            "degisen_belgeler": [{"title": "...", "source_url": "..."}]
          }
        }
        ```
        """
        return son_tazeleme_oku()

    # ----------------------------------------------------------------- #
    # Özet üretimi — yerel model, AĞA ÇIKMAZ, veri tabanına YAZAR
    # ----------------------------------------------------------------- #
    @r.get("/summaries/coverage")
    def summaries_coverage():
        """Özet kapsam sayaçları + LLM durumu. Model ÇAĞIRMAZ, ağa çıkmaz.

        Sayaç arayüzde de hesaplanabilirdi (`/campaigns` `ozet`i taşıyor) ama
        `ozet_sebep` kovalarının ayrımı (`icerik_yok` / `basarisiz` /
        `denenmemis`) özet katmanının kuralıdır; onu TSX'e kopyalamak, kuralın
        iki yerde yaşaması demekti.
        """
        return app.state.ozet_isi.sayim()

    @r.post("/summaries/build", status_code=202)
    def summaries_build(request: Request):
        """Eksik özetleri arka planda üretir ve iş kaydını döndürür.

        SENKRON DEĞİL: belge başına ~6 saniye. Koşan bir iş varken ikinci
        istek 409 ile reddedilir — sessiz bir kuyruk operatöre yanlış bir
        "başladı" izlenimi verirdi.
        """
        try:
            kayit = app.state.ozet_isi.baslat()
        except LlmKapali as exc:
            # 503: sunucunun geçici bir yeteneği kapalı. 400 olsaydı istemcinin
            # gönderdiği bir şeyin hatalı olduğunu söylerdi — değil.
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        except OzetMesgul as exc:
            raise HTTPException(
                status_code=409,
                detail="Şu anda bir özet üretimi çalışıyor. Aynı anda tek iş "
                       "koşar; bitmesini bekleyin ya da durdurun.") from exc
        # Bu uç veri tabanına YAZAR (`campaigns.ozet`), yani günlükteki en ağır
        # izlerden biri. Yine de bir SAYAÇ kaydedilmez: `hedef`/`yazilan` iş
        # başlarken 0'dır ve gerçek değerlerini arka plan iş parçacığında
        # alır. 0 yazmak, hiçbir şey yapılmadığını söyleyen uydurma bir değer
        # olurdu (CLAUDE.md §21). Sayaçlar `is_id` ile
        # `GET /summaries/status/{is_id}` üzerinden bağlanır.
        gunluk.eylem_bildir(request, is_id=kayit.get("is_id"))
        return kayit

    @r.get("/summaries/status")
    def summaries_last_status():
        """En son başlatılan özet işinin durumu — hiç iş yoksa `null`."""
        return app.state.ozet_isi.son_is()

    @r.get("/summaries/status/{job_id}")
    def summaries_status(job_id: str):
        """Bir özet işinin anlık durumu (ilerleme + sayaçlar)."""
        kayit = app.state.ozet_isi.durum(job_id)
        if kayit is None:
            raise HTTPException(status_code=404,
                                detail="Böyle bir özet işi yok.")
        return kayit

    @r.post("/summaries/cancel/{job_id}")
    def summaries_cancel(request: Request, job_id: str):
        """Durdurma ister. O ana kadar yazılmış özetler KORUNUR."""
        kayit = app.state.ozet_isi.iptal_et(job_id)
        if kayit is None:
            raise HTTPException(status_code=404,
                                detail="Böyle bir özet işi yok.")
        # `is_id` yol parametresinden ara katmana zaten düşüyor; buradaki katkı
        # iptal anına kadar veri tabanına kaç özetin YAZILMIŞ olduğudur — o
        # sayı, iptalin neyi geri almadığını anlatan tek bilgi.
        gunluk.eylem_bildir(request, yazilan_ozet=kayit.get("yazilan"),
                            durum_adi=kayit.get("durum"))
        return kayit

    # ----------------------------------------------------------------- #
    # İşlem günlüğü — okuma yüzeyi
    # ----------------------------------------------------------------- #
    return r
