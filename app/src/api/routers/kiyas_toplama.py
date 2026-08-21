"""Alan × kampanya toplama — üç uçun aynı depo çıktısından tablo kurma katmanı.

`routers/kiyas.py`'den ayrıldı (21 Ağu 2026). Gövdeler BİREBİR taşındı;
davranış değişikliği yok.

## Niçin AYRI bir modül

`query_fields()` **alan bazlı** çalışır: bir alan sorulur, o alanın tüm
kampanyalardaki satırları döner. Çok alanlı üç uç (`/urun-tablosu`,
`/bank-delta`, `/advantageous`) ise alan × kampanya tablosuna ihtiyaç duyar ve
üçü de bu dönüşümü KENDİ gövdesinde yazıyordu. Aynı iki kural üç yerde
tekrarlanıyordu:

1. **Alan başına bir sorgu, tek geçiş.** Eskiden arayüz `/bank-delta` yerine
   8 ayrı `/compare` çağırıyordu ve korpusu 8 kez geziyordu.
2. **İLK kayıt kazanır.** `query_fields()` bir alan için kampanya başına tek
   kayıt döndürür (ölçüldü, data/demo.db: 5455 satırda mükerrer
   (alan, kampanya) çifti YOK). Yine de `setdefault` kullanılır: sessizce
   ikinciye geçmek, hangi kanıtın gösterildiğini SORGU SIRASINA bırakırdı.

Kural üç yerde yaşadığı sürece, dördüncü çok alanlı uç onu dördüncü kez —
ve muhtemelen farklı — yazacaktı. Fonksiyonlar bilerek TEK bir jenerik
toplayıcıya indirgenmedi: üç uç aynı kuralı paylaşıyor ama farklı ANAHTAR ve
farklı YÜK ile çalışıyor (kampanya kimliği / alan adı; ham satır / kanonik
değer + güven). Ortak kural docstring'de tek yerde, biçim farkı ise kodda
açıkta duruyor — jenerikleştirmek üç uca da parametre bayrakları eklemek
olurdu.

## Niçin parametre

`field_rows` ve `repo` durumludur (depoya bağlı); `api/yardimcilar.py`'nin
kuralı gereği parametre olarak geçilirler — bu modül depoyu tanımaz.
"""

from __future__ import annotations

from typing import Any, Callable, Optional


def sartname_kampanyalari(
    alanlar: set[str],
    *,
    field_rows: Callable[..., list[dict]],
    type: Optional[str] = None,
    bank: Optional[str] = None,
) -> dict[Any, dict[str, Any]]:
    """`/urun-tablosu` girdisi: kampanya kimliğine göre indeksli alan tablosu.

    Kolonların ihtiyaç duyduğu TÜM alanlar tek geçişte çekilir; alan
    başına bir sorgu (`/bank-delta` ile aynı desen). Kampanya kimliğine
    göre indekslenir çünkü satır = tek kampanya.

    Yük HAM SATIRIN kendisidir (`fields[alan] = r`): şartname tablosu her
    hücrenin yanında kanıt penceresi de gösterdiği için kanonik değer tek
    başına yetmez.
    """
    kampanyalar: dict[Any, dict[str, Any]] = {}
    for alan in sorted(alanlar):
        for r in field_rows(alan):
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
            # İLK kayıt kazanır — gerekçe modül başlığında (2. kural).
            kayit["fields"].setdefault(alan, r)
    return kampanyalar


def bilesik_skor_kampanyalari(
    alanlar,
    *,
    field_rows: Callable[..., list[dict]],
) -> dict[Any, dict]:
    """`/advantageous` girdisi: `rank_advantageous`'un beklediği kampanya satırı.

    Yük KANONİK DEĞERdir ve güven AYRI bir sözlükte taşınır çünkü bileşik
    skorlama alan başına güven kapısı uygular — ham satırın tamamına
    ihtiyacı yok.
    """
    by_campaign: dict[Any, dict] = {}
    for alan in alanlar:
        for r in field_rows(alan):
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
    return by_campaign


def delta_alan_tablosu(
    alanlar: list[str],
    *,
    field_rows: Callable[..., list[dict]],
    type: Optional[str] = None,
) -> tuple[dict[str, list[dict]], set[Any]]:
    """`/bank-delta` girdisi: ALAN ADINA göre indeksli satır tablosu + aile kümesi.

    Anahtar burada kampanya değil ALANdır, çünkü delta paneli alan alan
    ilerler ("Kâr payı: rakip önde, Vade: siz öndesiniz").

    Aynı geçişte ürün aileleri de toplanır — delta her zaman aile İÇİNDE
    hesaplanır (CLAUDE.md §17) ve aileleri ikinci bir geçişle çıkarmak
    korpusu bir kez daha gezmek olurdu.
    """
    alan_satirlari: dict[str, list[dict]] = {}
    aileler: set[Any] = set()
    for alan in alanlar:
        satirlar = field_rows(alan)
        if type:
            satirlar = [r for r in satirlar
                        if r.get("campaign_type") == type]
        alan_satirlari[alan] = satirlar
        aileler.update(r.get("campaign_type") for r in satirlar)
    return alan_satirlari, aileler


def banka_belge_sayilari(
    repo: Any,
    bank: str,
    type: Optional[str] = None,
) -> dict[Any, int]:
    """Bankanın kendi belgelerinin aile başına SAYISI — `eksik_urun` ayrımının temeli.

    Banka o ailede hiç belge taşımıyorsa `eksik_urun`; belgesi var ama alan
    çıkarılamamışsa `eksik_veri`. İkisini tek etikette toplamak, olmayan bir
    ürün eksikliği iddia etmektir.

    `govde=False`: burada yalnız banka + tür sayılıyor, ham metin
    okunmuyor. Gövdeyi çekmek 1774 belgelik korpusta her istekte
    onlarca MB'lık boş bir okuma demekti.
    """
    kendi_belgeleri: dict[Any, int] = {}
    for c in repo.all_campaigns(govde=False):
        if c.get("bank") != bank:
            continue
        tur = c.get("campaign_type")
        if type and tur != type:
            continue
        kendi_belgeleri[tur] = kendi_belgeleri.get(tur, 0) + 1
    return kendi_belgeleri
