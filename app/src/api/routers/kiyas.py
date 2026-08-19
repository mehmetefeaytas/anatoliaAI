"""Kıyas uçları — alan karşılaştırma, şartname tablosu, banka deltası, skorlama.

`api/main.py`'den taşındı (19 Ağu 2026, kademeli bölmenin 4. adımı; plan:
docs/rapor/api-bolme-plani.md). Beş uç, 701 satır — bölmenin en büyük grubu.
Gövdeler BİREBİR taşındı; davranış değişikliği yok.

## Neden bu beşi birlikte

`/scoring` gövdesinde `compare(field=field, type=type)` çağrısı var: sıralama
tek doğruluk kaynağından gelsin diye kendi tablosunu kurmuyor, `/compare`'i
çağırıyor. İkisini ayrı modüle koymak o çağrıyı bir HTTP isteğine ya da
üçüncü bir ortak katmana çevirmek demekti — ikisi de aynı kararı iki yerde
yaşatırdı. `/urun-tablosu`, `/bank-delta` ve `/advantageous` de aynı
`comparison/compare.py` kapılarını (güven / süre / koşul / baz) paylaşıyor.

## Bağımlılıkların ikiye ayrılması

* **Durumlu → parametre.** `repo` ve dört closure yardımcısı (`_field_rows`,
  `_kiyas_kapsami`, `_campaign_view`, `_campaign_contradictions`) `main`de
  KALIYOR: `/chat`, `/extract`, `/contradictions*` ve
  `/campaigns/{id}/text` de onları kullanıyor, yani buraya taşınamazlardı.
  Factory parametresi olarak geçiliyorlar.
* **Saf → import.** `span_info`, `scoring_direction`, `_en_iyi_taraf` ve
  kıyas sabitleri `api/yardimcilar.py`'ye çıktı ve oradan import ediliyor.

## Taşımanın üç dersi (önceki adımlardan, tekrar edilmesin diye)

1. `from __future__ import annotations` yüzünden anotasyonlar dizedir ve
   FastAPI onları MODÜL global'lerinden çözer — `Response`/`Request`/pydantic
   şemaları fonksiyon içinde import edilirse uç 422 verir. Bu modülün
   uçlarında böyle bir parametre YOK (hepsi query parametresi), o yüzden
   modül-global bir tip gerekmiyor.
2. Silinen bloğun İÇİNDE kalan bir kurulum satırı (`ozet_isi = ...` gibi)
   sessizce yok olur ve `NameError` çalışma anında çıkar. Bu adımda kesilen
   aralık yalnız uç gövdeleri içeriyor; assert'li bir betikle kesildi.
3. `app.routes` bir `include_router`'lı uygulamada uç yollarını LİSTELEMEZ.
   Uç sayısını ölçen her yer `app.openapi()["paths"]` kullanmak zorunda
   (`tests/test_api_gunluk.py`, `.github/workflows/ci.yml`).
"""

from __future__ import annotations

from typing import Any, Callable, Optional

from ...comparison.compare import (
    ASGARI_GUVEN,
    AVANTAJ_ALANLARI,
    AVANTAJ_MUAFIYET_ALANLARI,
    DEFAULT_WEIGHTS,
    MIN_COVERAGE,
    MIN_GROUP_SIZE,
    OLCULEN_SUTUNLAR,
    SARTNAME_SUTUNLARI,
    RankRow,
    delta_between,
    rank,
    rank_advantageous_by_type,
    tablo_dolulugu,
    tablo_satirlari,
    tekil_banka_urun,
    weight_manifest,
    yon_zorla,
)
from ...extraction.llm.schema import EXTRACTION_FIELDS
from ...normalization.normalize import collapse_degenerate_range
from ..sabitler import FIELD_LABELS
from ..yardimcilar import (
    _ROW_TOKEN_SEP,
    VALID_INTENTS,
    VALID_PER_BANK,
    _en_iyi_taraf,
    scoring_direction,
    span_info,
)


def router_kur(
    repo: Any,
    *,
    field_rows: Callable[..., list[dict]],
    kiyas_kapsami: Callable[..., list[dict]],
    campaign_view: Callable[[int], Optional[dict]],
    campaign_contradictions: Callable[..., list],
):
    """Kıyas uçlarını taşıyan `APIRouter`'ı kurar.

    `fastapi` import'u fonksiyon içinde: paket kurulu değilse
    `main.build_app()` zaten anlaşılır bir hata veriyor ve bu modülün import
    edilmesi tek başına çökmemeli (çekirdek kural/normalizasyon katmanı saf
    stdlib ile çalışır).
    """
    from fastapi import APIRouter, HTTPException

    r = APIRouter()

    # Takma adlar, gövdeleri `main`deki closure adlarıyla BİREBİR taşıyabilmek
    # için var. Alternatifi 701 satırda dört adı elle değiştirmekti; taşımanın
    # doğruluğunu okumakla doğrulanabilir kılmak, dört satırlık bu köprüden
    # daha değerli. Adların başındaki alt çizgi de bu yüzden korundu.
    _field_rows = field_rows
    _kiyas_kapsami = kiyas_kapsami
    _campaign_view = campaign_view
    _campaign_contradictions = campaign_contradictions

    @r.get("/compare")
    def compare(field: str, intent: Optional[str] = None,
                type: Optional[str] = None, per_bank: str = "best"):
        """Bir alanı bankalar arası karşılaştırır (adil kıyas — CLAUDE.md §17).

        BELGE TÜRÜ SÜZMESİ: yalnız kampanya belgeleri döner; sözleşme / tarife
        / form metinleri kıyas tablosuna girmez (`_field_rows` docstring'i).
        Süzme depo katmanında yapılır, burada değil — böylece iki backend de
        aynı kümeyi görür. Chatbot'un RAG yolu bu süzmeyi UYGULAMAZ.

        `intent` KARARI: parametre eskiden imzada duruyor ama gövdede hiç
        kullanılmıyordu (sessiz ölü parametre). KALDIRILMADI, **uygulandı** —
        çünkü chatbot tarafında `chatbot/router.py` zaten aynı niyeti
        ('lowest'/'highest'/'list'/'filter') üretiyor ve dashboard'un "en düşük /
        en yüksek" düğmesi bu sözlüğü paylaşmak zorunda; ayrışırlarsa aynı soru
        iki arayüzde farklı sıralanır. Anlamı:

          lowest  → sıralamayı KÜÇÜK değer önce olacak şekilde zorla
          highest → sıralamayı BÜYÜK değer önce olacak şekilde zorla
          list / filter / None → alanın kendi doğal yönü (compare.rank)

        Yön zorlaması yalnızca `comparable=True` satırlarda uygulanır;
        kıyaslanamayanlar not'larıyla sonda kalır. Geçersiz intent artık
        sessizce yok sayılmaz, 400 döner.

        `per_bank` KARARI (2026-08-09): şartnamenin çalışılmış örneği (s.12–13)
        **banka başına bir satır** gösteriyor; bu uç ise `extracted_fields`
        tablosundaki HER satırı döndürüyordu. Aynı banka aynı alanda 5
        kampanya taşıyorsa tabloda 5 satır oluşuyor ve her biri ayrı sıra
        alıyordu — "en düşük kâr payı hangi bankada" sorusunun cevabı, bir
        bankanın kendi kampanyalarıyla dolu bir liste hâline geliyordu.

          best (VARSAYILAN) → ürün ailesi başına bankanın EN İYİ satırı
          all               → eski davranış; her satır ayrı döner

        Tekilleştirme anahtarı `(bank, campaign_type)`'dır, yalnız `bank`
        değil: bir bankanın konut finansmanı ile taşıt finansmanı **farklı
        ürünlerdir** ve aynı satıra indirgenmeleri, adil kıyas garantisinin
        (CLAUDE.md §17) ürün ailesi düzeyindeki karşılığını bozardı.

        Elenen satırlar SAKLANMAZ, SAYILIR: her satır `other_count` taşır —
        "bu bankanın bu ailede kaç kampanyası daha var". Bilgi gizlenmiyor,
        özetleniyor; `per_bank=all` ile tamamı yine alınabilir.

        KAPSAM KARARI (2026-08-16): tablo, alanı olan bankaları değil
        **kapsamdaki** bankaları gösterir. Şartnamenin beklenen çıktı tablosu
        (s.11–12) eksik hücreli satırları açıkça içeriyor ("Belirtilmemiş",
        "Masraf belirtilmemiş") — yani alanı olmayan bankayı düşürmek biçimin
        doğrudan ihlali. Ölçüldü: `field=kar_payi_orani&type=Konut Finansmanı`
        sekiz bankanın altısını döndürüyordu; Ziraat Katılım (46 konut
        kampanyası) ve Adil Katılım sessizce düşüyordu. Kapsam
        `_kiyas_kapsami()` ile hesaplanır ve `compare.rank(kapsam=...)`
        eksikleri `value=null`, `comparable=false`, `note` ile ekler; bu
        satırlar `sort_key`/`rank` taşımaz ve sıralamaya girmez.

        Dönen alanlar (mevcutlar korunur, yenileri eklendi):
          bank, bank_name, value, comparable, note, source_span  (mevcut)
          campaign_id, campaign_type, source_url, raw_value, confidence,
          confidence_source, extractor, span_start, span_end, span_scope,
          span_verified, span_ambiguous, window_start, window_end, sort_key,
          rank, contradiction_count, other_count, oran_bazi
        """
        if intent is not None and intent not in VALID_INTENTS:
            raise HTTPException(
                status_code=400,
                detail=f"Geçersiz intent: {intent!r}. "
                       f"Geçerli değerler: {', '.join(VALID_INTENTS)}")
        if per_bank not in VALID_PER_BANK:
            raise HTTPException(
                status_code=400,
                detail=f"Geçersiz per_bank: {per_bank!r}. "
                       f"Geçerli değerler: {', '.join(sorted(VALID_PER_BANK))}")

        rows = _field_rows(field)
        if type:
            rows = [r for r in rows if r.get("campaign_type") == type]

        # Satır kimliğini `bank` alanına gömen token hilesi KALDIRILDI.
        # Yazıldığında gerekliydi: `rank()` girdideki ek alanları `RankRow`a
        # taşımıyordu ve kaynak satıra dönmenin başka yolu yoktu. Artık
        # `campaign_id` ile `campaign_type` taşınıyor.
        #
        # Hile yalnız gereksiz değil, ENGELDİ: paylaşılan sunum kapısı
        # `tekil_banka_urun()` `(bank, campaign_type)` çiftine bakar; her
        # satırın `bank`ı benzersiz bir token olsaydı hiçbir şey tekilleşmez,
        # uç nokta da kuralı kendi gövdesinde ikinci kez yazmak zorunda
        # kalırdı — bu depoda beş kez pahalıya mal olmuş "aynı karar iki
        # yerde" hatası.
        kaynak: dict[tuple[Any, Any], dict] = {}
        rank_input: list[dict] = []
        for r in rows:
            # Anahtar (kampanya, kanıt penceresi): `query_fields()` bir alan
            # için kampanya başına tek kayıt döndürür (ölçüldü, data/demo.db:
            # 5455 satırda mükerrer (alan, kampanya) çifti YOK) ve pencere
            # aynı kampanyada bile ayırt edicidir. İlk kayıt kazanır.
            kaynak.setdefault((r["campaign_id"], r["source_span"]), r)
            rank_input.append({
                "bank": r["bank"],
                "bank_name": r["bank_name"],
                "canonical_value": r["canonical_value"],
                "source_span": r["source_span"],
                "campaign_id": r["campaign_id"],
                "campaign_type": r["campaign_type"],
                # Çıkarımın KENDİ güveni sıralamaya girer (`compare.rank()`
                # `ASGARI_GUVEN` kapısı). Alan taşınmazsa kapı sessizce
                # kapalı kalırdı ve tablo, çıkarıcının zaten zayıf
                # işaretlediği bir değeri "en düşük" diye basardı.
                "confidence": r.get("confidence"),
                # Kampanyanın geçerlilik damgası (`compare.rank()` süre
                # kapısı). Aynı gerekçe: alan taşınmazsa kapı sessizce kapalı
                # kalır ve kapanmış bir kampanya, bugün başvurulabilecek
                # tekliflerin ÜSTÜNDE görünür.
                "campaign_status": r.get("campaign_status"),
                # Ham değer (`compare.rank()` KOŞUL kapısı). Kapı, koşulun
                # orana bağlı olup olmadığını ham değerin kanıt penceresindeki
                # KONUMUNA bakarak anlar; alan taşınmazsa konum bilinemez ve
                # kapı sessizce kapalı kalır.
                #
                # ÖLÇÜLDÜ (2026-08-11): tam olarak bu oldu. Kapı eklendi,
                # testleri geçti, `rank()` doğrudan çağrıldığında çalıştı — ama
                # `/compare` yanıtında "Mobilden yeni müşterilere özel %0"
                # satırları hâlâ `comparable=True` dönüyordu. Yukarıdaki iki
                # yorum aynı tuzağı zaten iki kez anlatıyordu; üçüncüsü de
                # aynı biçimde düştü.
                "raw_value": r.get("raw_value"),
                # Oranın bazı (`compare.rank()` BAZ kapısı). Çıkarım katmanı
                # alanı henüz üretmiyor ve `.get()` `None` döndürüyor — kapı
                # o hâlde ateşlenmez, çünkü bilinmeyen baz varsayılmaz. Alan
                # buraya ŞİMDİDEN taşınıyor: yukarıdaki üç yorumun anlattığı
                # tuzak tam olarak "kapı eklendi, alan taşınmadı, kapı
                # sessizce kapalı kaldı" biçiminde üç kez tekrarlandı.
                "oran_bazi": r.get("oran_bazi"),
            })

        # Sıralama → istenen yön → banka × ürün ailesi başına tek satır.
        # Üçü de `comparison/compare.py`'nin ortak kapıları; chatbot'un yapısal
        # yolu (`chatbot/structured.py`) BİREBİR aynı çağrıları yapar ve
        # ayrışmayı `tests/test_chatbot_kiyas_paritesi.py` kilitler.
        ranked: list[RankRow] = yon_zorla(
            rank(rank_input, field, kapsam=_kiyas_kapsami(type)), field, intent)
        if per_bank == "best":
            ranked = tekil_banka_urun(ranked)

        out = []
        position = 0
        for x in ranked:
            # Kapsam satırı: bankanın bu ailede belgesi var ama bu alanda hiç
            # çıkarım kaydı yok. Kaynak satırı YOKTUR — `kaynak[...]` ile
            # aranırsa KeyError olurdu. Şema aynen korunur (arayüz tek bir
            # satır biçimi bilir) ve ölçülmemiş her alan `None` kalır; sıfır
            # ya da tahmin yazılmaz (CLAUDE.md §21).
            if x.campaign_id is None:
                out.append({
                    "bank": x.bank,
                    "bank_name": x.bank_name,
                    "value": None,
                    "comparable": False,
                    "note": x.note,
                    "source_span": None,
                    "campaign_status": None,
                    "campaign_id": None,
                    "campaign_type": x.campaign_type,
                    "source_url": None,
                    "raw_value": None,
                    "confidence": None,
                    "confidence_source": None,
                    "extractor": None,
                    # Konum alanları da diğer satırlarla AYNI yoldan üretilir;
                    # elle boş sözlük yazmak, `span_info` bir alan eklediğinde
                    # sessizce ayrışırdı.
                    **span_info("", None, None),
                    "sort_key": None,
                    "rank": None,
                    "contradiction_count": 0,
                    "other_count": x.other_count,
                    "oran_bazi": None,
                })
                continue
            src = kaynak[(x.campaign_id, x.source_span)]
            # Metin `_campaign_view()`'dan gelir — `/campaigns/{id}/text` ile
            # AYNI metin. `query_fields()` bilerek `raw_text` döndürmez: aynı
            # belgenin tam metnini her alan satırında tekrarlamak, chatbot'un
            # text-to-SQL yolunu da (aynı metodu kullanır) gereksiz şişirirdi.
            view = _campaign_view(src["campaign_id"]) or {}
            text = view.get("text") or ""
            loc = span_info(text, src["source_span"], src["raw_value"],
                            src.get("span_start"), src.get("span_end"))
            if x.comparable and x.sort_key is not None:
                position += 1
                row_rank: Optional[int] = position
            else:
                row_rank = None
            out.append({
                # --- mevcut sözleşme (kaldırılmadı) ---
                "bank": src["bank"],
                "bank_name": src["bank_name"],
                "value": x.value,
                "comparable": x.comparable,
                "note": x.note,
                "source_span": x.source_span,
                # Rozet için ayrı alan: bir satır aynı anda hem aralık hem
                # süresi dolmuş olabilir ve `note` tek bir dizedir.
                "campaign_status": x.campaign_status,
                # --- denetim / açıklanabilirlik ---
                "campaign_id": src["campaign_id"],
                "campaign_type": src["campaign_type"],
                "source_url": src["source_url"],
                "raw_value": src["raw_value"],
                "confidence": src["confidence"],
                "confidence_source": src.get("confidence_source"),
                "extractor": src["extractor"],
                **loc,
                # --- şeffaf skorlama ---
                "sort_key": x.sort_key,
                "rank": row_rank,
                # `scraped_at` artık GERÇEKTEN dolu geliyor. Eski ham SQL onu
                # SELECT etmiyordu, yani `as_of` her zaman None kalıyor ve
                # zaman bağımlı çelişki kuralı ("süresi dolmuş ama sayfa
                # yayında") bu uçta TAMAMEN KAPALIYDI: aynı kampanya
                # `/contradictions`'ta çelişkili, `/compare`'de temiz
                # görünüyordu. `query_fields()` alanı döndürdüğü için iki uç
                # artık aynı cevabı veriyor.
                "contradiction_count": len(_campaign_contradictions(
                    src["campaign_id"], text, src["bank"],
                    src.get("scraped_at"), src.get("source_url"))),
                # Bu satırın temsil ettiği ailede bankanın KAÇ kampanyası daha
                # var. `tekil_banka_urun()` doldurur; `per_bank=all` iken
                # tekilleştirme hiç koşmaz ve alan 0 kalır (hiçbir şey
                # elenmemiştir).
                "other_count": x.other_count,
                # Oranın bazı (`compare.rank()` baz kapısı). Değeri `None`
                # ise baz ÖLÇÜLMEMİŞTİR — "aylık" demek değildir.
                "oran_bazi": x.oran_bazi,
            })
        return out

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
        # başına bir sorgu (`/bank-delta` ile aynı desen). Kampanya kimliğine
        # göre indekslenir çünkü satır = tek kampanya.
        gerekli = {f for _a, _b, f in SARTNAME_SUTUNLARI if f}
        gerekli.update(AVANTAJ_ALANLARI)
        gerekli.update(AVANTAJ_MUAFIYET_ALANLARI)

        kampanyalar: dict[Any, dict[str, Any]] = {}
        for alan in sorted(gerekli):
            for r in _field_rows(alan):
                if type and r.get("campaign_type") != type:
                    continue
                if bank and r.get("bank") != bank:
                    continue
                kayit = kampanyalar.setdefault(r["campaign_id"], {
                    "bank": r["bank"], "bank_name": r["bank_name"],
                    "campaign_id": r["campaign_id"],
                    "campaign_type": r["campaign_type"],
                    "campaign_status": r.get("campaign_status"),
                    "source_url": r.get("source_url"),
                    "fields": {},
                })
                # `query_fields()` alan başına kampanyada TEK kayıt döndürür
                # (ölçüldü: 5455 satırda mükerrer (alan, kampanya) çifti yok);
                # yine de ilk kayıt kazanır — sessizce ikinciye geçmek, hangi
                # kanıtın gösterildiğini sorgu sırasına bırakırdı.
                kayit["fields"].setdefault(alan, r)

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

    @r.get("/bank-delta")
    def bank_delta(bank: str, type: Optional[str] = None,
                   rival: Optional[str] = None):
        """Banka içi delta — "bende ne eksik, rakipte ne var?" (tek istekte).

        Diğer uçlar müşterinin sorusunu ("hangi banka daha ucuz?") yanıtlar;
        bu uç BANKANIN sorusunu yanıtlar. Aynı çıkarım verisi, tersinden.

        ## Neden ayrı bir uç

        Arayüz bunu 8 ayrı `/compare` çağrısının üstüne istemcide kuruyordu.
        Üç sonucu vardı: (1) tür süzmesi opsiyonel olduğu için delta ürün
        aileleri arasında hesaplanabiliyordu — "Vade: rakip 84 ay önde"
        cümlesi bir ihtiyaç finansmanı ile bir konut finansmanı arasında
        üretilmiş olabiliyordu; (2) `/compare` her satır için
        `_campaign_view()` + `_campaign_contradictions()` koşuyor, yani 8
        istek korpusun tamamını 8 kez geziyordu; (3) fark aritmetiği
        istemcideydi.

        Burada delta **her zaman ürün ailesi İÇİNDE** hesaplanır (CLAUDE.md
        §17) ve pahalı çelişki sorgusu yalnız gösterilecek 2 satır için koşar.

        ## Ürün ailesi

        `type` verilirse yalnız o aile döner; verilmezse bankanın belge
        taşıdığı HER aile ayrı ayrı döner. Aileler arası hiçbir kıyas
        yapılmaz.

        ## `rival`

        Belirtilmezse rakip, o ailede o alanda **en iyi** olan diğer bankadır.
        Belirtilirse yalnız o banka rakip alınır — "en iyiye göre neredeyim"
        ile "şu bankaya göre neredeyim" farklı sorulardır ve ikincisi eskiden
        hiç sorulamıyordu.

        ## `eksik_urun` ile `eksik_veri` AYRIDIR

        Eskiden ikisi de kırmızı "eksik ürün" etiketine düşüyordu. Banka o
        ailede hiç belge taşımıyorsa `eksik_urun`; belgesi var ama alan
        çıkarılamamışsa `eksik_veri`. Bunları tek etikette toplamak, olmayan
        bir ürün eksikliği iddia etmektir — `FairnessNotice`'ın "veri yok ≠
        ürün yok" vaadi tam burada tutulur.
        """
        alanlar = [f for f in EXTRACTION_FIELDS
                   if scoring_direction(f)[0] != "unranked"]

        # Alan × satır tablosu tek geçişte kurulur; her alan için depo bir kez
        # sorgulanır (eskiden istemci 8 ayrı HTTP isteği atıyordu).
        alan_satirlari: dict[str, list[dict]] = {}
        aileler: set[Any] = set()
        for alan in alanlar:
            satirlar = _field_rows(alan)
            if type:
                satirlar = [r for r in satirlar
                            if r.get("campaign_type") == type]
            alan_satirlari[alan] = satirlar
            aileler.update(r.get("campaign_type") for r in satirlar)

        # Bankanın kendi belgelerinin bulunduğu aileler — "ürün yok" ile "veri
        # yok" ayrımı buna dayanır.
        # `govde=False`: burada yalnız banka + tür sayılıyor, ham metin
        # okunmuyor. Gövdeyi çekmek 1774 belgelik korpusta her istekte
        # onlarca MB'lık boş bir okuma demekti.
        kendi_belgeleri: dict[Any, int] = {}
        for c in repo.all_campaigns(govde=False):
            if c.get("bank") != bank:
                continue
            tur = c.get("campaign_type")
            if type and tur != type:
                continue
            kendi_belgeleri[tur] = kendi_belgeleri.get(tur, 0) + 1

        aileler.update(kendi_belgeleri)
        if type:
            aileler = {a for a in aileler if a == type}

        def _gorunum(satir: Optional[dict], sk: Optional[float],
                     kiyaslanabilir: bool, not_: Optional[str]) -> Optional[dict]:
            """Bir tarafın gösterilecek alanları + KANITI.

            `confidence`, `extractor` ve `contradiction_count` bilerek
            döndürülür: "%10 daha kötüsünüz" iddiasını, arkasındaki değerin
            hangi katmandan geldiği ve o belgede çelişki olup olmadığı
            bilinmeden sunmak, denetlenemez bir iddiadır.
            """
            if satir is None:
                return None
            view = _campaign_view(satir["campaign_id"]) or {}
            metin = view.get("text") or ""
            return {
                "bank": satir["bank"],
                "bank_name": satir["bank_name"],
                "value": collapse_degenerate_range(satir.get("canonical_value")),
                "raw_value": satir.get("raw_value"),
                "sort_key": sk,
                "comparable": kiyaslanabilir,
                "note": not_,
                "campaign_status": satir.get("campaign_status"),
                "campaign_id": satir["campaign_id"],
                "campaign_type": satir.get("campaign_type"),
                "source_url": satir.get("source_url"),
                "confidence": satir.get("confidence"),
                "confidence_source": satir.get("confidence_source"),
                "extractor": satir.get("extractor"),
                "contradiction_count": len(_campaign_contradictions(
                    satir["campaign_id"], metin, satir["bank"],
                    satir.get("scraped_at"), satir.get("source_url"))),
            }

        cikti_aileler = []
        for aile in sorted(aileler, key=lambda a: (a is None, str(a))):
            alan_ciktilari = []
            for alan in alanlar:
                aile_satirlari = [r for r in alan_satirlari[alan]
                                  if r.get("campaign_type") == aile]
                siralanmis = rank([
                    {"bank": f"{i}{_ROW_TOKEN_SEP}{r['bank']}",
                     "bank_name": r["bank_name"],
                     "canonical_value": r["canonical_value"],
                     "source_span": r["source_span"],
                     # Güven kapısı burada da geçerli: delta paneli
                     # `comparable` bayrağına bakıyor ve düşük güvenli bir
                     # değerle fark hesaplamak, o farkı uydurmak olurdu.
                     "confidence": r.get("confidence"),
                     # Süre kapısı da geçerli, aynı gerekçeyle: kapanmış bir
                     # kampanyayla "rakipten %10 daha iyisiniz" demek, artık
                     # kimseye verilmeyen bir teklife dayanan bir iddiadır.
                     "campaign_status": r.get("campaign_status"),
                     # Koşul kapısı da geçerli: "mobilden yeni müşterilere
                     # özel %0" ile hesaplanmış bir delta, herkesin
                     # alamayacağı bir orana dayanan bir farktır.
                     "raw_value": r.get("raw_value"),
                     # Baz kapısı da geçerli: yıllık ilan edilmiş bir oranla
                     # aylık bir orandan çıkarılan fark, birimi görmezden
                     # gelen bir aritmetiktir.
                     "oran_bazi": r.get("oran_bazi")}
                    for i, r in enumerate(aile_satirlari)
                ], alan)

                # Sıralama satırını kaynak kayda geri bağla. Token'daki indeks
                # `aile_satirlari` içindeki konumdur (bkz. `_ROW_TOKEN_SEP`).
                eslesmis = [
                    (aile_satirlari[int(x.bank.split(_ROW_TOKEN_SEP, 1)[0])], x)
                    for x in siralanmis
                ]

                benimkiler = [(k, x) for k, x in eslesmis if k["bank"] == bank]
                rakipler = [(k, x) for k, x in eslesmis
                            if k["bank"] != bank
                            and (rival is None or k["bank"] == rival)]

                benim_kayit, benim = _en_iyi_taraf(benimkiler)
                rakip_kayit, rakip = _en_iyi_taraf(rakipler)

                # Bankanın sıralamadaki kendi konumu — "7 bankadan 3.".
                # Banka başına TEK konum: aynı bankanın birden çok kaydı
                # sıralamayı şişirmemeli.
                gorulen: list[Any] = []
                for kayit, x in eslesmis:
                    if x.comparable and x.sort_key is not None \
                            and kayit["bank"] not in gorulen:
                        gorulen.append(kayit["bank"])
                konum = gorulen.index(bank) + 1 if bank in gorulen else None

                if rakip is None:
                    tur_kind, mutlak, goreli = "rakip_yok", None, None
                elif benim is None:
                    # Bankanın o ailede HİÇ belgesi yoksa ürün eksikliği;
                    # belgesi var ama alan çıkarılamadıysa VERİ eksikliği.
                    tur_kind = ("eksik_urun" if not kendi_belgeleri.get(aile)
                                else "eksik_veri")
                    mutlak = goreli = None
                else:
                    tur_kind, mutlak, goreli = delta_between(
                        alan,
                        benim.sort_key if benim.comparable else None,
                        rakip.sort_key if rakip.comparable else None,
                        benim.oran_bazi, rakip.oran_bazi,
                    )

                alan_ciktilari.append({
                    "field": alan,
                    "label": FIELD_LABELS.get(alan, alan),
                    "direction": scoring_direction(alan)[0],
                    "direction_label": scoring_direction(alan)[1],
                    "kind": tur_kind,
                    "abs_diff": mutlak,
                    "rel_pct": goreli,
                    "position": konum,
                    "bank_count": len(gorulen),
                    "mine": _gorunum(
                        benim_kayit,
                        benim.sort_key if benim else None,
                        bool(benim and benim.comparable),
                        benim.note if benim else None),
                    "rival": _gorunum(
                        rakip_kayit,
                        rakip.sort_key if rakip else None,
                        bool(rakip and rakip.comparable),
                        rakip.note if rakip else None),
                })

            cikti_aileler.append({
                "campaign_type": aile,
                "own_campaigns": kendi_belgeleri.get(aile, 0),
                "fields": alan_ciktilari,
            })

        return {
            "bank": bank,
            "rival": rival,
            "fairness_note": (
                "Delta her zaman KAMPANYA TÜRÜ İÇİNDE hesaplanır; bir konut "
                "finansmanı ile bir ihtiyaç finansmanı arasında fark "
                "üretilmez. Taraflardan biri sayıya "
                "indirgenemiyorsa fark boş bırakılır — yaklaşık bir fark "
                "uydurulmaz."),
            "families": cikti_aileler,
        }

    @r.get("/scoring")
    def scoring(field: str, type: Optional[str] = None):
        """Şeffaf skorlama: TEK ALAN sıralamasının formülü + ara değerleri.

        Bu uç **tek alanlı** sıralamayı açıklar; iki adımdan oluşur:
          1) `_numeric_key(value)` → (sort_key, comparable, note)
          2) yön = alan `_LOWER_IS_BETTER` mi `_HIGHER_IS_BETTER` mi

        DÜZELTME (2026-08-08): bu docstring ve `composite_note` eskiden
        *"kod tabanında ağırlıklı bileşik skor **yoktur**"* diyordu. Yanlıştı —
        `compare.py` `DEFAULT_WEIGHTS`, `WEIGHT_RATIONALE`, `_composite_numeric`,
        `rank_advantageous` ve `weight_manifest`'i **taşıyor ve test ediyordu**;
        yalnız hiçbir uçtan çağrılmıyordu. Yani uç kendi kodunu yalanlıyordu ve
        jüri kodu okusa bunu görürdü.

        Bileşik skor artık `GET /advantageous` ile sunuluyor; ağırlıklar
        `composite_weights` alanında gerekçeleriyle döner. Ağırlıklar bir
        **ürün kararıdır**, ölçümden türetilmiş sabit değildir — bu ayrım
        `WEIGHT_RATIONALE`de açıkça yazılıdır.
        """
        direction, direction_label = scoring_direction(field)
        rows = compare(field=field, type=type)  # aynı sıralama, tek doğruluk kaynağı
        return {
            "field": field,
            "label": FIELD_LABELS.get(field, field),
            "direction": direction,
            "direction_label": direction_label,
            "formula_source": "src/comparison/compare.py",
            "steps": [
                {"no": 1, "name": "Kanonik değer",
                 "detail": "Ham ifade normalize edilir (oran→float, para→"
                           "{value,currency}, vade→ay)."},
                {"no": 2, "name": "Sıralama anahtarı (sort_key)",
                 "detail": "compare._numeric_key(): sayı→kendisi, para→value, "
                           "masraf→amount (yoksa 0), aralık→min ve "
                           "comparable=False."},
                {"no": 3, "name": "Güven kapısı",
                 "detail": (
                     f"Çıkarım güveni {ASGARI_GUVEN:.2f}".replace(".", ",")
                     + " altında kalan değer sıralamaya GİRMEZ; "
                     "comparable=false olur ve notunda ölçülen güven yazar. "
                     "Değer silinmez, gerekçesiyle görünür kalır. Eşik altın "
                     "kümede ölçüldü: bu bandın altındaki çıkarımların hepsi "
                     "hatalıydı ve kanıt pencereleri belgenin kampanya olmayan "
                     "bölümlerinden (hesaplama aracı varsayılanı, çerez "
                     "metni, ücret tarifesi) geliyordu.")},
                {"no": 4, "name": "Adil kıyas kapısı",
                 "detail": "Yalnız comparable=True satırlar sıralanır. Aralık, "
                           "farklı para birimi, sayısal olmayan ve boş değerler "
                           "not'uyla sona alınır."},
                {"no": 5, "name": "Yön",
                 "detail": f"{field} → {direction} ({direction_label}). Kaynak: "
                           "compare._LOWER_IS_BETTER / _HIGHER_IS_BETTER."},
            ],
            "composite_weights": weight_manifest(),
            "composite_note": (
                "Bu uç TEK alan üzerinden sıralar. Alanlar arası ağırlıklı "
                "bileşik skor ayrı bir uçtadır: GET /advantageous. Ağırlıklar "
                "bir ÜRÜN KARARIDIR, ölçümden türetilmiş sabit değildir; her "
                "birinin gerekçesi yukarıda döner."),
            "composite_endpoint": "/advantageous",
            "rows": [
                {"bank": r["bank"], "bank_name": r["bank_name"],
                 "value": r["value"], "sort_key": r["sort_key"],
                 "comparable": r["comparable"], "note": r["note"],
                 "campaign_status": r["campaign_status"],
                 "rank": r["rank"], "confidence": r["confidence"],
                 "extractor": r["extractor"]}
                for r in rows
            ],
        }

    @r.get("/advantageous")
    def advantageous(type: Optional[str] = None,
                     min_coverage: float = MIN_COVERAGE):
        """§5.7 "En Avantajlı Kampanya" — ÇOK alanlı, ağırlıklı bileşik skor.

        Bu uç 2026-08-08'de eklendi. `compare.py`'deki bileşik skorlama
        (~420 satır) yazılı ve testliydi ama **hiçbir uçtan çağrılmıyordu**;
        üstelik `/scoring` *"böyle bir şey yok"* diyerek onu yalanlıyordu.

        Sıralama **kampanya TÜRÜ İÇİNDE** yapılır. Bir konut finansmanı ile
        bir kart kampanyasını tek listede sıralamak adil kıyas garantisini
        (CLAUDE.md §17) ihlal ederdi: alanların anlamı türe göre değişir.

        Üç kapı korunur ve hepsi çıktıda görünür:
          - `MIN_GROUP_SIZE` (3): daha küçük türde sıralama YAPILMAZ. Sıralama
            tabanlı normalizasyon 2 öğede dejenere olur ve "en avantajlı"
            iddiası bilgi taşımaz. Grup gizlenmez, `note` ile raporlanır.
          - `min_coverage` (0,5): kampanya, ölçülebilen ölçütlerin ağırlıkça en
            az yarısını taşımalı; taşımıyorsa `comparable=false`.
          - Sayıya indirgenemeyen alan SKORLANMAZ ve nedeni `note`'ta durur.
            Değer asla uydurulmaz.

        Belge türü süzmesi `_field_rows` üzerinden gelir: sözleşme / tarife
        metinleri bu tabloya girmez.
        """
        # Kampanya başına alan sözlüğü kurulur. Girdi `rank_advantageous`'un
        # beklediği biçimdir; tek tek alan sorgularından toplanır çünkü
        # `query_fields` alan bazlı çalışır.
        by_campaign: dict[Any, dict] = {}
        for alan in DEFAULT_WEIGHTS:
            for r in _field_rows(alan):
                cid = r.get("campaign_id")
                if cid is None:
                    continue
                kayit = by_campaign.setdefault(cid, {
                    "bank": r.get("bank"), "bank_name": r.get("bank_name"),
                    "campaign_id": cid,
                    "campaign_type": r.get("campaign_type"),
                    "source_url": r.get("source_url"),
                    # Süre kapısı kampanya düzeyindedir; `rank_advantageous`
                    # bu alanı satırın kökünde arar (alan sözlüğünde değil).
                    "campaign_status": r.get("campaign_status"),
                    "fields": {},
                    "field_confidence": {},
                })
                # Aynı alan aynı kampanyada birden çok kez çıkabilir; İLK
                # satır tutulur (`query_fields` `ORDER BY f.id` ile gelir,
                # yani sıra iki backend'de de aynıdır).
                kayit["fields"].setdefault(alan, r.get("canonical_value"))
                # Değerle güveni AYNI satırdan al: `setdefault` ikisinde de
                # çağrılıyor, yani seçilen değer ile taşınan güven her zaman
                # aynı kayda aittir.
                kayit["field_confidence"].setdefault(alan, r.get("confidence"))

        satirlar = list(by_campaign.values())
        if type:
            satirlar = [r for r in satirlar if r.get("campaign_type") == type]

        gruplar = rank_advantageous_by_type(satirlar, min_coverage=min_coverage)
        return {
            "min_group_size": MIN_GROUP_SIZE,
            "min_coverage": min_coverage,
            "weights": weight_manifest(),
            "fairness_note": (
                "Sıralama kampanya TÜRÜ İÇİNDE yapılır; türler arası "
                "karşılaştırma yapılmaz. Alanı olmayan "
                "kampanya CEZALANDIRILMAZ, kıyas dışı bırakılır — 0 puan "
                "'ürün yok' demektir, 'kötü' demek değil. Çıkarım güveni "
                + f"{ASGARI_GUVEN:.2f}".replace(".", ",")
                + " altında kalan alan da skorlanmaz; nedeni o alanın "
                "not'unda yazar ve kampanyanın veri kapsamasını düşürür."),
            "types": {
                tur: {
                    "count": bilgi["count"],
                    "note": bilgi["note"],
                    "ranked": [c.to_dict() for c in bilgi["ranked"]],
                }
                for tur, bilgi in sorted(gruplar.items())
            },
        }

    return r
