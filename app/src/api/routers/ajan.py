"""Ajan uçları — hibrit chatbot, canlı çıkarım, zor vaka tezgâhı.

`api/main.py`'den taşındı (19 Ağu 2026, kademeli bölmenin 5. adımı; plan:
docs/rapor/api-bolme-plani.md). Gövdeler BİREBİR taşındı.

## Neden bu üçü birlikte

`/chat` ve `/extract` sistemin iki "canlı" yüzeyidir: ikisi de LLM'e
dokunabilir, ikisi de kişisel veri taşıyabilecek serbest metin alır ve ikisi
de bu yüzden işlem günlüğüne farklı davranır (`/chat` eylem BİLDİRMEZ, çünkü
tek anlamlı özet kullanıcının sorusu olurdu; `/extract` yalnız SONUCUN
özetini bildirir, gövdedeki metni değil). `/zor-vakalar` `/extract`'in
referans yüzeyidir — aynı `zor_vaka` modülünü ve aynı alan etiketlerini
kullanır. Üçünü ayırmak bu üç kararı üç dosyaya dağıtırdı.

## `ChatReq` / `ExtractReq` neden BURADA

`from __future__ import annotations` yüzünden anotasyonlar dizedir ve FastAPI
onları çalışma anında **modül global'lerinden** çözer. Şemalar `main`de
kalsaydı bu modülün global'lerinde bulunamazlardı ve FastAPI `req`
parametresini bir QUERY parametresi sanardı — iki uç da gövdeyi hiç okumadan
her istekte 422 verirdi. Bu tuzak `main`de bir kez, 2. adımda (`katalog.py`)
bir kez daha yaşandı; `RefreshReq` de aynı sebeple `isler.py`'ye taşınmıştı.
`main` yalnız `BaseModel`i tutmaya devam ediyor, çünkü `build_app()` pydantic
yokluğunu onun `None` olmasıyla raporluyor.

`Request` de aynı sebeple modül global: `/extract` imzasında taşınıyor.

## Bağımlılıklar — durum parametre, saflık import

`repo`, `llm`, `clf`, `bot` ve `kaynaklari_zenginlestir` çalışma-anı duruma
bağlı (depo bağlantısı, model istemcisi, istek-arası önbellek) ve factory
parametresi olarak geçiliyor. Güvenlik özeti yardımcıları saf olduğu için
`api/yardimcilar.py`'den import ediliyor (4. adımda netleşen ayrım).
"""

from __future__ import annotations

from typing import Any, Callable, Optional

from ...chatbot.router import baglam_birlestir
from ...comparison.contradiction import detect as detect_contradictions
from ...extraction.llm.schema import EXTRACTION_FIELDS
from ...extraction.reconcile import build_campaign
from ...preprocessing.clean import normalize_text
from .. import gunluk, zor_vaka
from ..sabitler import FIELD_LABELS
from ..yardimcilar import _guvenlik_ozeti

# Gövde şemaları ve `Request` MODÜL GLOBAL'İNDE olmak ZORUNDA — gerekçe modül
# başlığında. `main`den taşındılar; oradaki uzun hata anlatısı da orada değil
# burada yaşıyor, çünkü tuzak artık burada.
try:  # pragma: no cover - pydantic yokluğu build_app()'te raporlanır
    from pydantic import BaseModel

    class ChatReq(BaseModel):
        """`POST /chat` gövdesi.

        `context` = istemcinin sakladığı son turların DURUM kayıtları,
        YENİDEN ESKİYE sıralı. Sunucu oturum tutmaz (bkz. `chatbot/bot.py`
        modül başlığı); hafıza istemcidedir ve her istekte geri gelir.

        Kayıtların içeriği serbest metin DEĞİLDİR: `chatbot/router.py`
        `ChatContext.dogrula()` her değeri sonlu bir izin listesinden geçirir,
        uymayanı sessizce atar. Bu yüzden bağlam kanalı bir enjeksiyon yüzeyi
        oluşturmaz — taşınabilecek tek şey, sunucunun kendi ürettiği alan /
        niyet / kampanya türü / banka slug'ı etiketleridir.
        """

        question: str
        context: list[dict] = []

    class ExtractReq(BaseModel):
        """`POST /extract` gövdesi (canlı çıkarım — CLAUDE.md §11).

        `gold_id` verilirse yanıt bir `gold` bloğu kazanır: aynı belgenin
        altın değerleri ve alan alan karşılaştırma sonucu. Çıkarım YİNE
        gövdedeki `text` üzerinde koşar — sunucu altın kümeden metin
        okumaz, yalnızca REFERANS okur. Aksi hâlde ekran, model çıktısı
        yerine gold'un kendisini gösteriyor olabilirdi ve bunu kimse
        ayırt edemezdi.
        """

        text: str
        bank: str = "bilinmeyen"
        gold_id: Optional[str] = None

except ModuleNotFoundError:  # pragma: no cover
    BaseModel = None  # type: ignore[assignment]

try:  # pragma: no cover - fastapi yokluğu build_app()'te raporlanır
    from fastapi import Request
except ModuleNotFoundError:  # pragma: no cover
    Request = None  # type: ignore[assignment]


def router_kur(
    repo: Any,
    llm: Any,
    clf: Any,
    bot: Any,
    *,
    kaynaklari_zenginlestir: Callable[..., list],
):
    """Ajan uçlarını taşıyan `APIRouter`'ı kurar.

    `fastapi` import'u fonksiyon içinde: paket kurulu değilse
    `main.build_app()` zaten anlaşılır bir hata veriyor ve bu modülün import
    edilmesi tek başına çökmemeli.
    """
    from fastapi import APIRouter

    r = APIRouter()

    # Takma ad, gövdeyi `main`deki closure adıyla BİREBİR taşıyabilmek için
    # (4. adımdaki aynı gerekçe: taşımanın doğruluğu okumakla doğrulanabilir
    # kalsın).
    _kaynaklari_zenginlestir = kaynaklari_zenginlestir

    @r.post("/chat")
    def chat(req: ChatReq):
        """Hibrit chatbot — her kaynak kaydı DENETLENEBİLİR bağlantı taşır.

        `sources` içindeki her kayıt `campaign_id`, `source_url` ve `ozet`
        alanlarını **her zaman içerir**; bilinmiyorsa değeri `null`'dır.
        Eskiden yalnız metin parçası dönüyordu ve "bu bilgiyi nereden aldın"
        sorusunun cevabı arayüzde kurulamıyordu.

        `ozet` önceden üretilmiş belge özetidir (`campaigns.ozet`) ve istek
        anında ÜRETİLMEZ. Arayüz uzun ham metin yerine onu basar; özeti
        olmayan belgede sahte bir özet uydurulmaz, ham metnin kırpıldığı
        kullanıcıya söylenir.

        ## İşlem günlüğüne eylem özeti BİLEREK bildirilmez

        Bu uç `POST` olduğu için günlükte "yazan" olarak görünür (metot ölçütü
        — `src/api/gunluk.py`), ama `gunluk.eylem_bildir()` ÇAĞRILMAZ. Sebep
        tek: buradaki tek anlamlı özet kullanıcının SORUSU olurdu ve o soru
        kişisel veri taşıyabilir ("50 bin TL kredim var…"). Kalıcı ve
        ekleme-only bir denetim kaydına kişisel veri yazmak, günlüğün
        çözdüğünden büyük bir sorun açar (CLAUDE.md §19).

        ## Sohbet hafızası (durumsuz)

        `req.context` istemcinin taşıdığı son turların durumudur; sunucu
        hiçbir oturum saklamaz. Yanıttaki `context` bir sonraki tur için
        üretilen yeni durumdur, `inherited` ise bu turda önceki turlardan
        DEVRALINAN boyutların Türkçe etiketleridir — arayüz bunu rozet olarak
        basar, böylece kullanıcı hangi bağlamla cevaplandığını görür.

        `verbalize` yapısal cevabın LLM ile sözelleştirilip
        sözelleştirilmediğini bildirir. `applied` yanlışsa ekranda ŞABLON
        cevap vardır; `reason` neden düşüldüğünü söyler.

        ## `safety` — güvenlik kapılarının denetim kaydı

        Beş kapı + içerik karantinası her soruda koşar ama etkileri metne
        karışır: düzeltme notu ve feragatname cevabın gövdesinde durur,
        karantina ise hiçbir iz bırakmazdı. Bu blok o boşluğu kapatır ve
        hangi kapının ateşlendiğini, hangisinin cevabı DURDURDUĞUNU ve
        korpustan hangi belgenin düşürüldüğünü açıkça söyler. Alanların
        anlamı `_guvenlik_ozeti()` docstring'inde.

        `quarantined` boş değilse korpusta talimat gömülü bir belge VAR
        demektir; arayüz bunu her hâlde gösterir, jüri modu beklemez.
        """
        a = bot.ask(req.question, baglam_birlestir(req.context))
        # `quarantined` chatbot katmanına yeni taşınan bir alan; yoksa
        # `getattr` boş liste verir ve blok sessizce "karantina yok" der —
        # eksik alan yüzünden uç noktanın çökmesi kabul edilemez.
        return {"answer": a.text, "handler": a.handler, "field": a.field,
                "sources": _kaynaklari_zenginlestir(a.handler, a.field,
                                                    a.sources),
                "context": a.context, "inherited": a.inherited,
                "verbalize": a.verbalize,
                "safety": _guvenlik_ozeti(a.safety_report, a.gates,
                                          getattr(a, "quarantined", []))}

    # ----------------------------------------------------------------- #
    # Zor vaka tezgâhı — canlı yolun ÜZERİNE referans koyar
    # ----------------------------------------------------------------- #
    # Gerekçe `src/api/zor_vaka.py` modül başlığında; burada yalnız HTTP
    # yüzeyi ve banka adı çözümü var.
    _banka_adlari: dict[str, str] = {}

    def _banka_adi_haritasi() -> dict[str, str]:
        """slug → görünen ad. Bir kez kurulur; katalog koşu boyunca değişmez."""
        if not _banka_adlari:
            for b in repo.all_banks():
                slug = b.get("slug")
                if slug:
                    _banka_adlari[slug] = b.get("name") or slug
        return _banka_adlari

    @r.get("/zor-vakalar")
    def zor_vakalar():
        """Altın kümedeki ZOR belgeler + altın değerleri (CLAUDE.md §6, §16)."""
        return zor_vaka.liste(FIELD_LABELS, _banka_adi_haritasi())

    @r.post("/extract")
    def extract(request: Request, req: ExtractReq):
        """Canlı çıkarım (CLAUDE.md §11 "canlı çıkarım butonu").

        Offset'ler burada GERÇEK `ExtractedField` nesnesinden gelir ve
        `verify_span()` ile doğrulanır — DB yolundaki geri kazanıma gerek yok.

        İşlem günlüğüne yalnız çıkarımın SONUCUNUN özeti düşer (banka slug'ı,
        bulunan/eksik alan sayısı). Gövdedeki `text` KAYDEDİLMEZ: kullanıcı
        oraya kendi sözleşmesini yapıştırabilir ve kalıcı bir denetim kaydı
        kişisel veri deposuna dönüşemez (`src/api/gunluk.py`).
        """
        text = normalize_text(req.text)
        ctype, ctype_conf = clf.classify(text)
        c = build_campaign(text, bank_slug=req.bank, llm=llm, campaign_type=ctype)
        by_name = {f.field_name: f for f in c.fields}
        gunluk.eylem_bildir(
            request, banka=c.bank_slug, kampanya_turu=c.campaign_type,
            bulunan_alan=len(c.fields),
            eksik_alan=len([a for a in EXTRACTION_FIELDS if a not in by_name]),
            metin_uzunlugu=len(text))
        # Altın karşılaştırma İSTEĞE BAĞLI: `gold_id` yoksa yanıt eskisiyle
        # birebir aynıdır (serbest metin yolu bozulmaz). Bilinmeyen bir kimlik
        # 404 DEĞİL `null` döner — çıkarım gerçekleşti, yalnız referans
        # bulunamadı; isteği tümüyle reddetmek çalışan bir sonucu çöpe atardı.
        gold = None
        if req.gold_id:
            kayit = zor_vaka.kayit(req.gold_id)
            if kayit is not None:
                gold = zor_vaka.karsilastir(
                    kayit,
                    {f.field_name: f.canonical_value for f in c.fields},
                    FIELD_LABELS, list(EXTRACTION_FIELDS),
                    metin_ayni=normalize_text(kayit.get("text") or "") == text,
                )
        return {
            "gold": gold,
            "bank": c.bank_slug,
            "campaign_type": c.campaign_type,
            "campaign_type_confidence": ctype_conf,
            "text": text,
            "text_length": len(text),
            "llm_available": llm.available,
            "fields": [
                {"field": f.field_name,
                 "label": FIELD_LABELS.get(f.field_name, f.field_name),
                 "value": f.canonical_value,
                 "raw_value": f.raw_value,
                 "confidence": f.confidence,
                 "confidence_source": f.confidence_source,
                 "extractor": f.extractor.value,
                 "source_span": f.source_span,
                 "span_start": f.span_start,
                 "span_end": f.span_end,
                 "span_scope": "value" if f.span_start is not None else None,
                 "span_verified": f.verify_span(text),
                 "span_ambiguous": False}
                for f in c.fields
            ],
            # Hangi alanlar HİÇ bulunamadı — halüsinasyon yasağının görünür hali
            "missing_fields": [
                {"field": name, "label": FIELD_LABELS.get(name, name)}
                for name in EXTRACTION_FIELDS if name not in by_name
            ],
            "contradictions": [
                {"kind": k.kind, "detail": k.detail, "fields": k.fields}
                for k in detect_contradictions(c)
            ],
        }

    return r
