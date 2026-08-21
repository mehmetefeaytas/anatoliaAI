"""`/compare` — tek alan, çok banka: kıyas tablosunun denetim yüzeyi.

`routers/kiyas.py`'den ayrıldı (21 Ağu 2026). Uç gövdesi ve **docstring'i**
BİREBİR taşındı; davranış değişikliği yok.

## Niçin AYRI bir modül

Beş kıyas ucu aynı veriyi paylaşıyor ama **beş farklı soruyu** yanıtlıyor. Bu
uç müşterinin sorusunu yanıtlar ("hangi bankada en düşük?") ve tek alanlıdır:
bir kolon, çok banka, her satırda kanıt penceresi + güven + katman. Yani
sistemin **denetim yüzeyi**dir — jüri bir değeri sorguladığında bakılan yer
burasıdır. Şartname tablosu (`/urun-tablosu`), bankanın kendi sorusu
(`/bank-delta`), formül anlatısı (`/scoring`) ve bileşik skor
(`/advantageous`) ayrı sorumluluklardır ve ayrı modüllerdedir.

Uç gövdesinin kendisi artık üç adımdır ve üçü de farklı katmandadır:

    1. parametre sözleşmesi   -> burada (400 yanıtları uç sözleşmesinin parçası)
    2. sıralama kapı çekirdeği -> `kiyas.siralanmis_satirlar` (cephede KALIYOR)
    3. kanıtlı satır biçimi    -> `kiyas_kanit_satiri.kanitli_satirlar`

## Niçin docstring de buraya geldi

Uç fonksiyonunun docstring'i FastAPI'de `/openapi.json`'un `description`
alanıdır — yani **kamuya açık sözleşme metni**, iç dokümantasyon değil.
Gövde taşınıp docstring cephede bırakılsaydı sözleşme ile onu tutan kod iki
dosyaya ayrılırdı. Uç fonksiyonu bu modülde TANIMLANIP cephedeki router'a
kaydedildiği için `description` FastAPI tarafından yine aynı yoldan
(`inspect.cleandoc(__doc__)`) üretiliyor; `/openapi.json` birebir aynı kalır.

## Niçin `_field_rows` takma adı

Gövdeyi BİREBİR taşıyabilmek için. Aynı köprü `main.py` -> `routers/kiyas.py`
taşımasında da kullanıldı ve gerekçesi aynı: taşımanın doğruluğunu OKUMAKLA
doğrulanabilir kılmak, tek satırlık bu köprüden daha değerli.
"""

from __future__ import annotations

from typing import Any, Callable, Optional

from ..yardimcilar import VALID_INTENTS, VALID_PER_BANK
from .kiyas_kanit_satiri import kanitli_satirlar


def uc_ekle(
    r: Any,
    *,
    field_rows: Callable[..., list[dict]],
    kiyas_kapsami: Callable[..., list[dict]],
    campaign_view: Callable[[int], Optional[dict]],
    campaign_contradictions: Callable[..., list],
    siralanmis_satirlar: Callable[..., tuple],
):
    """`/compare`'i `r`'ye kaydeder ve uç fonksiyonunu döndürür.

    Fonksiyon DÖNDÜRÜLÜYOR çünkü `/scoring` onu doğrudan çağırıyor: sıralama
    tek doğruluk kaynağından gelsin diye kendi tablosunu kurmuyor. Bağımlılık
    böylece cephede GÖRÜNÜR oluyor — eskiden `router_kur` içinde iki closure
    arasındaki örtük bir bağdı.

    `fastapi` import'u fonksiyon içinde: paket kurulu değilse
    `main.build_app()` zaten anlaşılır bir hata veriyor ve bu modülün import
    edilmesi tek başına çökmemeli (çekirdek kural/normalizasyon katmanı saf
    stdlib ile çalışır).
    """
    from fastapi import HTTPException

    _field_rows = field_rows

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
        # Sıralama + üç ortak kapı CEPHEDE koşuyor. Niçin orada kaldığı
        # `kiyas.siralanmis_satirlar` docstring'inde yazılı (iki denetim
        # kapısı o dosyayı adıyla sabitliyor).
        kaynak, ranked = siralanmis_satirlar(
            rows, field, intent=intent, per_bank=per_bank,
            kapsam=kiyas_kapsami(type))
        return kanitli_satirlar(
            ranked, kaynak,
            campaign_view=campaign_view,
            campaign_contradictions=campaign_contradictions)

    return compare
