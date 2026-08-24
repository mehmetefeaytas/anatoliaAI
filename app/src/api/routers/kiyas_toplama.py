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


def _katilma_satirlari() -> list[dict]:
    """TKBB katılma hesabı getirilerinden «Yatırım Ürünü» satırları.

    Yatırım Ürünü türünün GERÇEK ürünü katılma hesabıdır ve TKBB onun
    dağıtılan getirisini her banka için haftalık yayımlıyor. O sayı olmadan
    "yatırım ürününde hangi banka iyi" sorusu vade ve masraf üzerinden
    cevaplanıyordu — ürünün kendisine bakmadan.

    Getiri `katilma_getirisi` alanına yazılıyor, `kar_payi_orani`ne DEĞİL:
    ikisi ters yönlü büyüklüktür ve aynı kolonda %42'lik bir getiri, %2'lik
    bir finansman oranının yanında "kötü" görünürdü.

    Yalnız `buyukluk == "getiri"` kayıtları alınıyor. Paylaşım oranı (%90 gibi
    bir bölüşüm) getiri DEĞİLDİR; ikisini karıştırmak bu projede ayrı bir
    karar sayfasıyla yasaklandı.
    """
    from ...chatbot.katilma_orani import kayitlari_yukle

    try:
        havuz = kayitlari_yukle()
    except Exception:                        # pragma: no cover - veri yoksa
        return []
    en_iyi: dict[str, dict] = {}
    for k in havuz:
        if k.get("buyukluk") != "getiri" or k.get("currency") != "TRY":
            continue
        oran = k.get("annual_rate")
        banka = k.get("bank_slug")
        if not banka or oran is None:
            continue
        onceki = en_iyi.get(banka)
        # Banka başına EN YÜKSEK getiri: yüksek oran avantajlı.
        if onceki is None or oran > onceki["annual_rate"]:
            en_iyi[banka] = k
    out: list[dict] = []
    for banka, k in sorted(en_iyi.items()):
        alanlar: dict[str, Any] = {"katilma_getirisi": k["annual_rate"]}
        if isinstance(k.get("term_months"), int):
            alanlar["vade_ay"] = k["term_months"]
        out.append({
            "bank": banka, "bank_name": None,
            "campaign_id": None,
            "campaign_type": "Yatırım Ürünü",
            "source_url": k.get("source_url"),
            "campaign_status": None,
            "kaynak": "banka-yayini",
            "fields": alanlar,
            "confidences": {},
        })
    return out


def yayin_satirlari() -> list[dict]:
    """Bankaların KENDİ yayımladığı oranlardan kıyas satırı üretir.

    ## Niçin bu satırlar var — ölçülmüş yıldız boşluğu

    Banka sayfasının yıldız cetvelinde 81 olası (banka × tür) hücrenin yalnız
    **37'sinde** yıldız vardı; 23 hücrede banka o türde kampanya taşıyor ama
    hiçbiri kıyaslanabilir değildi. Boş hücrelerin çoğu FİNANSMAN aileleri —
    yani `kar_payi_orani` gereken yerler.

    O oran kampanya metninde YOK ve bu bir çıkarım kusuru değil: EVREN
    `llm-large` 60 aday belgede 0, yerel model 30 belgede 0 kabul edilebilir
    değer üretti. Bankalar oranı hesaplama araçlarında yayımlıyor ve biz
    154 kayıt topladık (7 banka).

    ## Niçin bir KAMPANYA satırına yazılmıyor

    Banka düzeyinde yayımlanmış bir oranı belirli bir kampanyanın
    `extracted_fields` kaydına yazmak, o belgenin söylemediğini ona atfetmek
    olurdu ve span → belge kanıt zinciri kırılırdı. Bunun yerine (banka, tür)
    başına AYRI bir satır üretiliyor: `campaign_id=None`,
    `kaynak="banka-yayini"`.

    Yıldızın sorusu zaten "bu banka bu ürün türünde ne kadar iyi" — bankanın
    yayımladığı ürün o sorunun meşru bir kanıtıdır. Şart, NEREDEN geldiğinin
    yazılması; `kaynak` alanı bunu taşıyor ve arayüz ayrı etiketliyor.

    ## Birim tutarlılığı

    Korpustaki `kar_payi_orani` da AYLIK orandır (README örneği: «%2,99» →
    2.99). Yayın kayıtlarındaki `monthly_rate` aynı birimde; bu yüzden ikisi
    aynı kolonda sıralanabiliyor. Yıllık maliyet oranı (`annual_cost_rate`)
    BİLEREK taşınmıyor — korpusta karşılığı yok ve farklı birimdeki iki sayıyı
    aynı alana koymak §17 adil kıyası bozardı.
    """
    from ...domain import yayimlanan_oran as Y

    # Ürün ailesi → KAMPANYA TÜRÜ (CLAUDE.md §12'nin sekiz sınıfı).
    #
    # `yayimlanan_oran.aile()` kendi etiketlerini üretiyor ve üçü kampanya
    # türleriyle birebir örtüşüyor. «Alışveriş Finansmanı» örtüşmüyor:
    # kampanya türü listesindeki «Alışveriş Puanı» PUAN kazandıran
    # kampanyalardır, taksitli alışveriş FİNANSMANI değil. Onu genel
    # «Finansman» türüne bağlamak doğru — uydurma bir tür açmak ya da puan
    # türüne karıştırmak, kıyası sessizce bozardı.
    TUR_ESLEMESI = {
        "Konut Finansmanı": "Konut Finansmanı",
        "Taşıt Finansmanı": "Taşıt Finansmanı",
        "İhtiyaç Finansmanı": "İhtiyaç Finansmanı",
        "Alışveriş Finansmanı": "Finansman",
    }

    en_iyi: dict[tuple[str, str], dict] = {}
    for k in Y.yukle():
        banka = k.get("bank_slug")
        tur = TUR_ESLEMESI.get(Y.aile(k.get("product_name") or ""))
        oran = k.get("monthly_rate")
        if not banka or not tur or oran is None:
            continue
        anahtar = (banka, tur)
        onceki = en_iyi.get(anahtar)
        # Banka başına türün EN DÜŞÜK oranı: finansmanda düşük oran avantajlı
        # ve bankanın en iyi teklifi o türdeki gücünü temsil eder.
        if onceki is None or oran < onceki["monthly_rate"]:
            en_iyi[anahtar] = k

    # GENEL «Finansman» türü — bankanın EN İYİ finansman teklifi.
    #
    # `Finansman` kampanya türü, belirli bir ürüne bağlanmamış genel finansman
    # kampanyalarının kovasıdır. Dünya, Emlak ve Ziraat'ın o kovadaki
    # kampanyaları ölçülemiyordu (kâr payı oranı taşımıyorlar) ama üçü de
    # konut/taşıt/ihtiyaç oranı YAYIMLIYOR. Bankanın en düşük yayımlanmış
    # oranı, genel finansman kovasında onu temsil eden meşru bir kanıttır.
    #
    # Çifte sayım DEĞİL: sıralama tür İÇİNDE yapılıyor, yani aynı sayı iki ayrı
    # ve birbirine karışmayan listede duruyor. Hangi üründen geldiği satırın
    # `product_name`inde yazılı.
    for banka in {b for b, _ in en_iyi}:
        if (banka, "Finansman") in en_iyi:
            continue                         # banka zaten genel oran yayımlıyor
        adaylar = [v for (b, _), v in en_iyi.items() if b == banka]
        if adaylar:
            en_iyi[(banka, "Finansman")] = min(adaylar,
                                               key=lambda x: x["monthly_rate"])

    out: list[dict] = _katilma_satirlari()
    for (banka, tur), k in sorted(en_iyi.items()):
        alanlar: dict[str, Any] = {"kar_payi_orani": k["monthly_rate"]}
        if isinstance(k.get("term_months"), int):
            alanlar["vade_ay"] = k["term_months"]
        # Tutar ÜST SINIRI bir kampanya tutarı değil; yalnız banka gerçekten
        # bir üst sınır yayımlamışsa taşınıyor.
        if k.get("amount_max"):
            alanlar["finansman_tutari"] = k["amount_max"]
        ucret = k.get("fees") or {}
        tahsis = ucret.get("tahsis") or ucret.get("komisyon")
        if tahsis is not None:
            alanlar["tahsis_ucreti"] = tahsis
        out.append({
            "bank": banka, "bank_name": None,
            "campaign_id": None,
            "campaign_type": tur,
            "source_url": k.get("source_url"),
            # Yayımlanan oranın süre damgası YOK: banka onu güncel olarak
            # yayımlıyor. `None` = damgasız, "süresi dolmuş" DEĞİL.
            "campaign_status": None,
            "kaynak": "banka-yayini",
            "fields": alanlar,
            "confidences": {},
        })
    return out


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
