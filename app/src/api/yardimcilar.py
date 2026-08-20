"""Uç noktaların paylaştığı saf yardımcılar — kanıt konumu, sıralama yönü, kıyas sabitleri.

`api/main.py`'den taşındı (19 Ağu 2026, kademeli bölmenin 4. adımı; plan:
docs/rapor/api-bolme-plani.md). Gövdeler BİREBİR taşındı.

## Neden ayrı bir modül, neden parametre değil

`routers/katalog.py` ve `routers/isler.py`'de bu yardımcılar factory
PARAMETRESİ olarak geçiliyor. Burada yol değişti çünkü kıyas uçları altısını
birden kullanıyor (`span_info`, `scoring_direction`, `_en_iyi_taraf`,
`VALID_INTENTS`, `VALID_PER_BANK`, `_ROW_TOKEN_SEP`) ve altı parametrenin
tamamı **hiçbir çalışma-anı duruma bağlı olmayan saf fonksiyon/sabit**.
Durumsuz olanı parametre yapmak imzayı şişirir ve her çağrı yerinde aynı altı
satırı tekrar yazdırır; durumlu olan (`repo`, closure yardımcıları) parametre
kalmaya devam ediyor. Ayrım şu: **durum parametre, saflık import.**

`main`den import etmek mümkün değildi — `main` bu paketi import ediyor, ters
yön dairesel bağımlılık kurardı. Bu yüzden yardımcılar `main`in ALTINA değil
YANINA çıktı; `main` de artık buradan import ediyor ve adlar `main`
yüzeyinde görünür kalıyor (`tests/test_api_sozlesme.py` `main.span_info`
üzerinden erişiyor, o sözleşme kırılmadı).
"""

from __future__ import annotations

from typing import Any, Optional

from ..chatbot.safety import (
    ALL_GATES,
    GATE_INJECTION,
    GATE_UNKNOWN_BANK,
    sanitize_output,
)
from ..comparison.compare import _HIGHER_IS_BETTER, _LOWER_IS_BETTER

# `/compare?intent=` için geçerli değerler — `chatbot/router.py:57` Route.intent
# ile BİREBİR aynı sözlük. Ayrışırlarsa dashboard ile chatbot aynı soruya farklı
# sıralama verir.
VALID_INTENTS = ("lowest", "highest", "list", "filter")

# `/compare?per_bank=` için geçerli değerler. `best` şartnamenin "banka başına
# bir satır" tablosunu üretir; `all` eski davranışı (her kayıt ayrı satır)
# korur ve geriye dönük uyumluluk için kaldırılmaz.
VALID_PER_BANK = frozenset({"best", "all"})


def _en_iyi_taraf(adaylar: list) -> tuple:
    """Bir tarafın gösterilecek kaydı: ilk KIYASLANABİLİR satır.

    `rank()` çıktısı en iyiden kötüye sıralı ve kıyaslanabilirler baştadır,
    dolayısıyla ilk kıyaslanabilir satır o tarafın en iyi kaydıdır. Hiç
    kıyaslanabilir satır yoksa ilk satır döner — değer yine gösterilir, ama
    `comparable=False` olduğu için fark hesaplanmaz.
    """
    for kayit, x in adaylar:
        if x.comparable and x.sort_key is not None:
            return kayit, x
    return adaylar[0] if adaylar else (None, None)


# `rank()` girdiye eklenen ek alanları (extractor, confidence, campaign_id...)
# RankRow'a taşımaz. Sıralama mantığını KOPYALAMADAN satırları geri eşlemek için
# `bank` alanına geçici bir satır kimliği gömülür. NUL ayırıcı seçildi: hiçbir
# gerçek banka slug'ında bulunamaz.
_ROW_TOKEN_SEP = "\x00"


# --------------------------------------------------------------------------- #
# Kaynak-span geri kazanımı (saf string, yeniden çıkarım yok)
# --------------------------------------------------------------------------- #
def locate_span(text: str, source_span: Optional[str],
                raw_value: Optional[str]) -> dict[str, Any]:
    """`source_span` penceresini ve içindeki `raw_value`'yu metinde konumlandırır.

    Dönüş anahtarları:
      span_start / span_end : karakter offset'leri (bulunamazsa None)
      span_scope            : 'value' (tam ham değer) | 'window' (yalnız pencere)
                              | None
      span_verified         : text[start:end] hedefe birebir eşit mi
      span_ambiguous        : pencere metni metinde birden çok kez geçiyor mu
      window_start/window_end: pencerenin kendi offset'leri (UI bağlam gösterir)

    Hiçbir tahmin yapılmaz: pencere bulunamazsa hepsi None döner.
    """
    out: dict[str, Any] = {
        "span_start": None, "span_end": None, "span_scope": None,
        "span_verified": False, "span_ambiguous": False,
        "window_start": None, "window_end": None,
    }
    if not text or not source_span:
        return out

    w = text.find(source_span)
    if w < 0:
        return out
    out["span_ambiguous"] = text.find(source_span, w + 1) >= 0
    w_end = w + len(source_span)
    out["window_start"], out["window_end"] = w, w_end

    if raw_value:
        v = text.find(raw_value, w, w_end)
        if v < 0:  # pencere dışında da olabilir (normalize farkı) — yine ara
            v = text.find(raw_value)
        if v >= 0 and text[v:v + len(raw_value)] == raw_value:
            out.update(span_start=v, span_end=v + len(raw_value),
                       span_scope="value", span_verified=True)
            return out

    # Ham değer konumlandırılamadı → en azından pencereyi vurgula (dürüst kapsam).
    out.update(span_start=w, span_end=w_end, span_scope="window",
               span_verified=text[w:w_end] == source_span)
    return out


def span_info(text: str, source_span: Optional[str], raw_value: Optional[str],
              span_start: Optional[int] = None,
              span_end: Optional[int] = None) -> dict[str, Any]:
    """Bir alanın metindeki yeri: **saklanan offset birincil**, yeniden hesaplama yedek.

    `span_start`/`span_end` DB'den gelir (`extracted_fields`). Kabul edilmesi
    için `text[span_start:span_end] == raw_value` eşitliğini geçmesi gerekir —
    saklanan offset körü körüne güvenilmez; bozuk bir kayıt arayüzde yanlış yeri
    boyamaktansa yedek yola düşmelidir.

    `window_start` / `window_end` / `span_ambiguous` her durumda `locate_span()`
    üzerinden hesaplanır: bunlar `source_span` PENCERESİNİN metindeki yeriyle
    ilgilidir, DB'de saklanmazlar ve arayüz bağlam göstermek için kullanır.

    Ölçülmüş fark (`data/demo.db`, 2204 alan): saklanan offsetlerin tamamı
    doğrulanıyor, yeniden hesaplama 73'ünde farklı (ve yanlış) yer gösteriyor —
    `str.find` ham değerin İLK geçtiği yeri bulur, çıkarımın geldiği yeri değil.
    """
    out = locate_span(text, source_span, raw_value)
    if (span_start is not None and span_end is not None
            and 0 <= span_start <= span_end <= len(text)
            and text[span_start:span_end] == (raw_value or "")):
        out.update(span_start=span_start, span_end=span_end,
                   span_scope="value", span_verified=True)
    return out


def scoring_direction(field: str) -> tuple[str, str]:
    """Alanın sıralama yönü ve insan-okur açıklaması.

    Kaynak: `src/comparison/compare.py:65-70` (`_LOWER_IS_BETTER` /
    `_HIGHER_IS_BETTER`). Burada ağırlık UYDURULMAZ; yalnız koddaki küme
    üyeliği okunur.
    """
    if field in _LOWER_IS_BETTER:
        return "lower_is_better", "Küçük değer daha avantajlı"
    if field in _HIGHER_IS_BETTER:
        return "higher_is_better", "Büyük değer daha avantajlı"
    return "unranked", "Bu alan için sıralama yönü tanımlı değil (kıyas yapılmaz)"

# --------------------------------------------------------------------------- #
# Güvenlik kapılarının rapor yüzeyi (`POST /chat` -> `safety`)
# --------------------------------------------------------------------------- #
# Kapı kimlikleri `chatbot/safety.py`'den İTHAL EDİLİR (`ALL_GATES`,
# `GATE_INJECTION`), burada tekrar YAZILMAZ. Gerekçe: iki liste ayrışırsa
# arayüz ya olmayan bir kapıyı "çalışıyor" diye gösterir ya da gerçekten
# ateşlenmiş bir kapıyı hiç basmaz — ikisi de güvenlik iddiasını çürütür.
#
# Sıra da oradan gelir: kullanıcı arka arkaya iki soru sorduğunda kapı
# listesinin yer değiştirmemesi gerekir, yoksa tablo okunmaz olur.
#
# `GATE_UNKNOWN_BANK` `ALL_GATES`e EKLENMEDİ — o sabit "değerlendirme setiyle
# aynı dize" olmak zorunda (`safety.py` yorumu) ve `GATE_INJECTION` de aynı
# sebeple dışarıda tutulmuş: ikisi de değerlendirme setinin ölçtüğü "5 kapı"
# değil, ayrı bir güvenlik katmanı. Buraya `GATE_INJECTION`la BİREBİR aynı
# kalıpla eklendi ki `/chat`in `safety.gates` listesi bu kapı ateşlendiğinde
# "fired": false YAZMASIN (jüri bulgusu düzeltmesi, CLAUDE.md §19).
GUVENLIK_KAPILARI: tuple[str, ...] = ALL_GATES + (GATE_INJECTION, GATE_UNKNOWN_BANK)

#: Kapı kimliği → (Türkçe ad, tek cümlelik açıklama). Açıklama kullanıcıya
#: gösterilir: "terminoloji" ham kimliği tek başına hiçbir şey anlatmaz.
GATE_LABELS: dict[str, tuple[str, str]] = {
    "terminoloji": (
        "Terminoloji",
        "Konvansiyonel bankacılık terimi soruda kabul edilir; cevapta "
        "katılım bankacılığındaki kâr payı karşılığıyla yazılır."),
    "fikhi_hukum": (
        "Fıkhî hüküm",
        "Bir ürünün dinen uygunluğuna hüküm verilmez; yetkili danışma "
        "kuruluna yönlendirilir."),
    "yatirim_tavsiyesi": (
        "Yatırım tavsiyesi",
        "Bankalar karşılaştırılır, hangisinin seçileceği söylenmez."),
    "garanti_imasi": (
        "Garanti iması",
        "Kâr payı oranı beklenen orandır; taahhüt edilmiş getiri gibi "
        "sunulmaz — katılma hesabı zarara da ortaktır."),
    "cekimserlik": (
        "Çekimserlik",
        "Kaynak yoksa ya da soru veri kapsamının dışındaysa değer "
        "uydurulmaz."),
    "icerik_karantinasi": (
        "İçerik karantinası",
        "Getirilen belgede talimat devralma işareti varsa belge tümüyle "
        "düşürülür; içeriği cevaba girmez."),
    "bilinmeyen_banka": (
        "Tanınmayan banka adı",
        "Soruda geçen banka veri setinde yoksa ilgisiz bir bankanın verisi "
        "gösterilmez; tanınan bankalar listelenir."),
}


# --------------------------------------------------------------------------- #
# Sohbet güvenlik yüzeyi — kapıların denetim kaydı
# --------------------------------------------------------------------------- #
# `api/main.py`'den taşındı (bölmenin 5. adımı). Buraya konuldu, `routers/
# ajan.py`'ye DEĞİL: `tests/test_chat_guvenlik_yuzeyi.py` bu iki fonksiyona
# `api_main._guvenlik_ozeti` / `api_main._karantina_kaydi` üzerinden erişiyor
# ve ikisi de saf fonksiyon. Saf olan import edilir (bkz. modül başlığı);
# `main` buradan import ettiği için o test sözleşmesi kırılmadı.

#: Karantina kaydında gösterilecek işaret payı (karakter). İşaret KANITTIR ve
#: gösterilmesi gerekir, ama gösterilen şey üçüncü taraf bir sayfadan gelen
#: saldırgan metnidir: sınırsız basmak, düşürdüğümüz belgeyi ekrana geri
#: koymak olurdu.
KARANTINA_ISARET_SINIRI = 120


def _karantina_kaydi(p: dict) -> dict:
    """Düşürülen bir pasajın kullanıcıya gösterilecek özeti.

    Belgenin METNİ TAŞINMAZ — yalnız kimliği (banka, kampanya, kaynak
    bağlantısı) ve yakalanan işaret geçer. Karantinanın gerekçesi "bu belgenin
    geri kalanına da güvenilmez"di; metnini arayüze taşımak o gerekçeyi
    kendi elimizle çürütürdü.

    İşaret `sanitize_output`tan geçirilir: eşleşen parça saldırganın yazdığı
    dizedir ve içinde konvansiyonel faiz terimi geçebilir. KAPI 1'in
    değişmezi ("o terim ekranda görünmez") güvenlik uyarısı için delinmez.
    """
    isaret = (p.get("isaret") or "").strip()
    if len(isaret) > KARANTINA_ISARET_SINIRI:
        isaret = isaret[:KARANTINA_ISARET_SINIRI].rstrip() + "…"
    temiz, _ = sanitize_output(isaret)
    cid = p.get("campaign_id")
    return {
        "bank": p.get("bank"),
        "campaign_id": int(cid) if cid is not None else None,
        "source_url": p.get("source_url"),
        "isaret": temiz or None,
    }


def _guvenlik_ozeti(rapor, gates: list, quarantined: list) -> dict:
    """`POST /chat` yanıtındaki `safety` bloğu — kapıların denetim kaydı.

    ## Neden yanıtta yer alıyor

    Sistem beş güvenlik kapısı çalıştırdığını iddia ediyor ama kapıların
    ETKİSİ metne karışmış durumda: düzeltme notu ve feragatname cevabın
    içinde, karantina ise tamamen görünmez. "Kapılar gerçekten koşuyor mu"
    sorusunun cevabı arayüzde kurulamıyordu.

    ## Neden ateşlenmeyen kapılar da dönüyor

    `fired=False` kayıtları olmadan liste "hangi kapılar var" sorusuna cevap
    veremez; jüri yalnız ateşlenenleri görüp geri kalanının varlığından
    haberdar olamazdı. Gürültü sorunu arayüzde çözülür (ayrıntı jüri
    modunda açılır), sözleşmede değil.

    ## Yasak terim neden GERİ GÖNDERİLMİYOR

    `SafetyReport.violations` yakalanan terimi ve çevresindeki ham bağlamı
    taşır. Onu yanıta koymak, KAPI 1'in az önce ekrandan sildiği dizeyi
    denetim kutusunda geri basmak olurdu. Bu yüzden yalnız SAYI geçer:
    olayın gerçekleştiği bilgisi kanıttır, terimin kendisi değil.
    """
    ates = set(gates or [])
    kirli = [_karantina_kaydi(p) for p in (quarantined or [])]
    if kirli:
        # Karantina `SafetyReport`e yazılmaz (RAG katmanında koşar), ama
        # ateşlenmiş bir kapıdır ve öyle raporlanır.
        ates.add(GATE_INJECTION)
    return {
        "gates": [
            {"id": g,
             "label": GATE_LABELS.get(g, (g, ""))[0],
             "aciklama": GATE_LABELS.get(g, (g, ""))[1],
             "fired": g in ates}
            for g in GUVENLIK_KAPILARI
        ],
        "fired": [g for g in GUVENLIK_KAPILARI if g in ates],
        "blocked_gate": getattr(rapor, "blocked_gate", None),
        "abstained": bool(getattr(rapor, "abstained", False)),
        # Çıktı süzgecinin sessizce yeniden yazdığı terim sayısı.
        "rewritten_terms": len(getattr(rapor, "violations", []) or []),
        "quarantined": kirli,
    }
