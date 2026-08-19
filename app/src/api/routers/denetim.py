"""Denetim ve yönetim uçları — işlem günlüğü, çelişki taraması, kapalı uçlar.

`api/main.py`'den taşındı (19 Ağu 2026, kademeli bölmenin 6. ve SON adımı;
plan: docs/rapor/api-bolme-plani.md). Gövdeler BİREBİR taşındı.

## Neden bu üçü birlikte

Üçü de "sistem kendi hakkında ne söylüyor" yüzeyidir, kullanıcı sorusu yolu
değil: `/log` kim ne yaptı, `/contradictions*` korpusun kendi içinde ne kadar
tutarsız, `/admin/*` hangi yetenek henüz yok. Üçü de yazma yapmaz (`/admin/*`
501 döner) ve üçü de arayüzün "denetim" sekmesini besler.

## `app` neden parametre

`/log` gövdesi günlüğe `app.state.gunluk` üzerinden erişiyor ve bu bir TEST
KANCASIDIR — `main.py`'de gerekçesi yazılı ("testler sahte bir günlük
geçirebilsin diye"). Doğrudan parametreye çevirmek o kancayı kırardı, bu
yüzden `isler.py`'deki (3. adım) aynı desen izlendi ve factory `app`
referansı alıyor.

## `Response` neden modül global

`/log` yanıt başlığına toplam kayıt sayısını yazıyor (`X-Toplam-Kayit`,
`GET /campaigns` ile aynı sözleşme) ve imzasında `response: Response` taşıyor.
`from __future__ import annotations` yüzünden bu anotasyon bir dizedir ve
FastAPI onu MODÜL global'lerinden çözer; import fonksiyon içinde kalsa ad
bulunamaz ve FastAPI `response`u bir QUERY parametresi sanar — uç her istekte
422 verir. Bu tuzak bölmenin 2. ve 5. adımlarında birer kez yaşandı.

## `/contradictions/summary` neden `contradictions()`i çağırıyor

Özet, taramanın kendisini yeniden yazmıyor; aynı fonksiyonu çağırıp sayıyor.
İki yerde iki tarama olsaydı "kaç çelişki var" sorusunun cevabı hangi uca
sorulduğuna göre değişebilirdi.
"""

from __future__ import annotations

from typing import Any, Callable, Optional

from .. import gelecek, gunluk

# `Response` MODÜL GLOBAL'İNDE olmak zorunda — gerekçe modül başlığında.
try:  # pragma: no cover - fastapi yokluğu build_app()'te raporlanır
    from fastapi import Response
except ModuleNotFoundError:  # pragma: no cover
    Response = None  # type: ignore[assignment]


def router_kur(
    app: Any,
    repo: Any,
    *,
    campaign_contradictions: Callable[..., list],
):
    """Denetim uçlarını taşıyan `APIRouter`'ı kurar.

    `fastapi` import'u fonksiyon içinde: paket kurulu değilse
    `main.build_app()` zaten anlaşılır bir hata veriyor.
    """
    from fastapi import APIRouter, HTTPException

    r = APIRouter()

    # Takma ad, gövdeyi `main`deki closure adıyla BİREBİR taşıyabilmek için.
    _campaign_contradictions = campaign_contradictions

    @r.get("/log")
    def islem_gunlugu(response: Response,
                      yalniz_yazanlar: bool = True,
                      metot: Optional[str] = None,
                      yol: Optional[str] = None,
                      baslangic: Optional[str] = None,
                      bitis: Optional[str] = None,
                      limit: int = gunluk.VARSAYILAN_LIMIT,
                      offset: int = 0):
        """Denetim kaydı — süzülmüş, sayfalanmış, yeniden eskiye.

        ## Ham dosya DÖKÜLMEZ

        `data/gunluk/*.jsonl` olduğu gibi gönderilmez: dosya megabaytlarca
        olabilir ve içindeki asıl bilgi (kim ne yaptı) okuma trafiğinin
        içinde kaybolur. Bu uç süzer, sayfalar ve sıralar.

        ## `yalniz_yazanlar` VARSAYILAN OLARAK AÇIK

        Panel her sekmede `/compare`, `/stats`, `/advantageous` çağırıyor ve
        iş koşarken `/refresh/status` saniyede bir yoklanıyor. Varsayılan
        "hepsi" olsaydı, uğruna bu günlüğün yazıldığı tek satır (`POST
        /refresh`) yüzlerce okuma satırının arasında kalırdı. Tam akış tek
        parametre uzakta: `?yalniz_yazanlar=false`.

        Günlük DÖNDÜRME kayıtları bu süzgeçte de görünür — "kayıt kayboldu mu"
        sorusu tam olarak bu görünümde soruluyor (`src/api/gunluk.py`).

        ## Yanıt ÇIPLAK LİSTEDİR

        Toplam `X-Toplam-Kayit` başlığına yazılır — `GET /campaigns` ile aynı
        sözleşme; arayüz iki uçta iki farklı biçim öğrenmek zorunda kalmasın.

        `baslangic` / `bitis` ISO-8601 alır (`2026-08-13` ya da
        `2026-08-13T09:00:00Z`). Yalnız tarih verildiğinde `bitis` o günün
        SONUNU kapsar; aksi hâlde "13 Ağustos'a kadar" süzgeci 13 Ağustos'u
        tümüyle dışarıda bırakır ve kullanıcı kaydın silindiğini sanırdı.
        """
        if limit < 1 or limit > gunluk.AZAMI_LIMIT:
            raise HTTPException(
                status_code=400,
                detail=f"limit 1 ile {gunluk.AZAMI_LIMIT} arasında olmalı "
                       f"(gelen: {limit}).")
        if offset < 0:
            raise HTTPException(status_code=400,
                                detail=f"offset negatif olamaz (gelen: {offset}).")
        try:
            kayitlar, toplam = app.state.gunluk.oku(
                yalniz_yazanlar=yalniz_yazanlar, metot=metot, yol=yol,
                baslangic=baslangic, bitis=bitis, limit=limit, offset=offset)
        except ValueError as exc:
            # Bozuk zaman süzgeci İSTEMCİNİN hatasıdır; 400 ile ve okunur bir
            # örnekle geri döner (`gunluk._zaman_coz`).
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        response.headers["X-Toplam-Kayit"] = str(toplam)
        return kayitlar

    # ----------------------------------------------------------------- #
    # Gelecek faz — tanımlı ama KAPALI uçlar
    # ----------------------------------------------------------------- #
    # Sözleşme `src/api/gelecek.py` içinde; burada yalnız HTTP yüzeyi var.
    # Uçlar sahte başarı DÖNDÜRMEZ: 501 + gerekçe + bugünkü alternatif.
    def _kapali() -> None:
        raise HTTPException(status_code=501, detail={
            "sebep": gelecek.KAPALI_SEBEBI,
            "bugunku_yol": gelecek.BUGUNKU_YOL,
        })

    @r.get("/admin/plan")
    def admin_plan():
        """Gelecek faz uçlarının sözleşmesi — arayüz bunu çizer."""
        return gelecek.plan()

    @r.post("/admin/banks")
    def admin_bank_ekle():
        """Gelecek faz: banka ekleme. Bu sürümde KAPALI (501)."""
        _kapali()

    @r.post("/admin/banks/{slug}/campaigns")
    def admin_kampanya_ekle(slug: str):
        """Gelecek faz: kampanya ekleme. Bu sürümde KAPALI (501)."""
        _kapali()

    @r.post("/admin/banks/{slug}/products")
    def admin_urun_ekle(slug: str):
        """Gelecek faz: finansal ürün ekleme. Bu sürümde KAPALI (501)."""
        _kapali()

    @r.get("/contradictions")
    def contradictions():
        """Tüm külliyatta otomatik yakalanan iç çelişkiler (CLAUDE.md §18 #2)."""
        out = []
        for camp in repo.all_campaigns():
            text = camp.get("raw_text", "") or ""
            for k in _campaign_contradictions(camp["id"], text, camp["bank"],
                                              camp.get("scraped_at"),
                                              camp.get("source_url")):
                out.append({
                    "bank": camp["bank"],
                    "bank_name": camp.get("bank_name"),
                    "campaign_id": camp["id"],
                    "campaign_type": camp.get("campaign_type"),
                    "source_url": camp.get("source_url"),
                    **k,
                })
        return out

    @r.get("/contradictions/summary")
    def contradictions_summary():
        """Çelişki taramasının kapsamı — "kaç belgede kaç bulgu" anlatısı."""
        # Yalnız sayım yapılıyor; ham gövdeye gerek yok (`govde=False`).
        camps = repo.all_campaigns(govde=False)
        found = contradictions()
        by_kind: dict[str, int] = {}
        for c in found:
            by_kind[c["kind"]] = by_kind.get(c["kind"], 0) + 1
        return {
            "scanned_campaigns": len(camps),
            "scanned_banks": len({c["bank"] for c in camps}),
            "contradiction_count": len(found),
            "affected_campaigns": len({c["campaign_id"] for c in found}),
            "by_kind": by_kind,
        }

    return r
