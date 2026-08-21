"""Kanıtlı satır serileştirme — kıyas yanıtlarının satır biçimleri tek yerde.

`routers/kiyas.py`'den ayrıldı (21 Ağu 2026). Gövdeler BİREBİR taşındı;
davranış değişikliği yok.

## Niçin AYRI bir modül

İki uç aynı vaadi tutuyor ve tutma biçimini iki yerde yazıyordu: **her
sayısal iddianın yanında kanıt penceresi, çelişki sayısı ve çıkarımın hangi
katmandan geldiği döner.** `/compare` bunu 24 alanlı satırında, `/bank-delta`
kendi `_gorunum()` yardımcısında yapıyordu. İkisi de aynı üç şeyi çağırıyor:

    campaign_view(cid)            -> kanıt penceresini konumlandıracak METİN
    campaign_contradictions(...)  -> o belgedeki çelişki SAYISI
    satır.get("confidence"/"extractor"/"confidence_source")

Bu, depoda beş kez pahalıya mal olmuş "aynı karar iki yerde" hatasının
adayıydı: `/compare` satırına bir denetim alanı eklendiğinde `/bank-delta`
sessizce eski sözleşmede kalıyor ve aynı değer bir uçta denetlenebilir, öbür
uçta denetlenemez görünüyordu. Sözleşme artık tek dosyada.

Modül aynı zamanda `campaign_view` / `campaign_contradictions`'ı çağıran TEK
yer — yani korpusun tamamını gezen pahalı iki çağrının maliyeti burada
okunabilir. `/bank-delta`'nın "çelişki sorgusu yalnız gösterilecek 2 satır
için koşar" kararı bu yüzden gözden kaçmıyor.

## Niçin parametre, niçin import

`api/yardimcilar.py`'nin kuralı: **durum parametre, saflık import.**
`campaign_view` ve `campaign_contradictions` `main`de yaşayan durumlu
closure'lardır (`/chat`, `/extract`, `/campaigns/{id}/text` de onları
kullanıyor) — parametre olarak geçilirler. `span_info` ve
`collapse_degenerate_range` saf fonksiyonlardır — import edilirler.

## Niçin alt çizgili takma adlar

Gövdelerin İÇİNDE `_campaign_view` / `_campaign_contradictions` adları
kullanılıyor ve bu bilinçli, iki nedenle:

1. **Gövdeler BİREBİR kalıyor** — taşımanın doğruluğu okumakla doğrulanabilir.
   Aynı köprüyü `main.py` -> `routers/kiyas.py` taşıması da kurmuştu.
2. **`tests/test_api_celiski_source_url.py` bir SAYI kilitliyor.** `src/api/`
   paketinin tamamında `_campaign_contradictions(` çağrı yerlerini sayıyor ve
   her birinin `source_url` ilettiğini doğruluyor; sayı düşerse "bir çağrı
   yeri silinmiş, o uç çelişki kuralına kör kalmış" diye kırılır. Adı
   sadeleştirmek, bölme sırasında tam olarak o kapıyı sessizce kör
   bırakırdı — çağrı yerleri duruyor ama denetim onları görmüyor olurdu.
   Ölçüldü: bölmeden önce 6, adlar sadeleştirilince 4, takma adla yine 6.
"""

from __future__ import annotations

from typing import Any, Callable, Optional

from ...normalization.normalize import collapse_degenerate_range
from ..yardimcilar import span_info


def kanitli_satirlar(
    ranked: list,
    kaynak: dict[tuple[Any, Any], dict],
    *,
    campaign_view: Callable[[int], Optional[dict]],
    campaign_contradictions: Callable[..., list],
) -> list[dict]:
    """`/compare` yanıtının satırları — sıralanmış satırlar + kaynak kayıtları.

    `ranked` `RankRow` listesidir (sıralama çekirdeğinden gelir), `kaynak` ise
    `(campaign_id, source_span)` -> ham depo satırı sözlüğüdür. İKİ satır
    biçimi üretilir ve ikisi de AYNI 24 anahtarı taşır:

      * **kapsam satırı** (`campaign_id is None`): bankanın o ailede belgesi
        var ama bu alanda hiç çıkarım kaydı yok. Kaynak satırı YOKTUR.
      * **gerçek satır**: kaynak kayıt bulunur, kanıt penceresi metinde
        konumlandırılır, çelişki sayısı hesaplanır.

    `rank` alanı burada üretilir çünkü GÖSTERİM sırasına bağlıdır: yalnız
    kıyaslanabilir satırlar numara alır ve numara 1'den başlar. Sıralama
    çekirdeği `sort_key` üretir, sıra NUMARASI sunum kararıdır.
    """
    # Takma adlar: modül başlığının "Niçin alt çizgili takma adlar" bölümü.
    _campaign_view = campaign_view
    _campaign_contradictions = campaign_contradictions

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


def taraf_gorunumu(
    satir: Optional[dict],
    sk: Optional[float],
    kiyaslanabilir: bool,
    not_: Optional[str],
    *,
    campaign_view: Callable[[int], Optional[dict]],
    campaign_contradictions: Callable[..., list],
) -> Optional[dict]:
    """`/bank-delta`'da bir tarafın (benim / rakip) gösterilecek alanları + KANITI.

    `confidence`, `extractor` ve `contradiction_count` bilerek
    döndürülür: "%10 daha kötüsünüz" iddiasını, arkasındaki değerin
    hangi katmandan geldiği ve o belgede çelişki olup olmadığı
    bilinmeden sunmak, denetlenemez bir iddiadır.
    """
    # Takma adlar: modül başlığının "Niçin alt çizgili takma adlar" bölümü.
    _campaign_view = campaign_view
    _campaign_contradictions = campaign_contradictions

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
