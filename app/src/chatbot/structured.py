"""Yapısal sorgu motoru — text-to-SQL'in güvenli, deterministik karşılığı.

İlgili: ../../decisions/hibrit-chatbot-text-to-sql-rag.md
        CLAUDE.md §5

LLM'e serbest SQL ürettirmek yerine (enjeksiyon + halüsinasyon riski), router'ın
çıkardığı (alan, niyet, filtre) niyetini repository sorgularına ve karşılaştırma
motoruna güvenle eşler. Sonuç her zaman kaynağa (source_span) dayalıdır.

## Sunum kapıları — neden burada değil, `comparison/compare.py` içinde

Bu modül sıralamayı bastığı hâliyle üç kapıdan geçirir ve üçünün de MANTIĞI
`comparison/compare.py` içindedir:

    yon_zorla()        — kullanıcının istediği sıralama yönü
    tekil_banka_urun() — banka × ürün ailesi başına tek satır
    turlere_ayir()     — kıyas ürün ailesi İÇİNDE

Kapılar eskiden yoktu ve eksiklikleri tarayıcıda görüldü (ölçüldü,
`data/demo.db`, 2026-08-10):

  * "Peki vade?" → aynı banka aynı değerle **232 satır**; 16 sorunun 6'sında
    tekrar vardı.
  * 16 sorunun 12'sinde cevap **birden fazla ürün ailesinden** besleniyordu;
    en kötü hâlde 9 aile tek listede sıralanıyordu.
  * `vade_ay` alanında "en düşük" sorusuna sıralamanın tepesi, yani **en uzun**
    vade basılıyordu ("en düşük vade: Ziraat Katılım (360 ay)").

Aynı kararlar `/compare` ucunda zaten alınmıştı. Kuralı ikinci kez buraya
yazmak yerine ortak yere taşındı; ayrışmayı `tests/test_chatbot_kiyas_paritesi.py`
kapıda tutar.

## Boş cevap da bir cevaptır

Kıyaslanabilir satır kalmadığında sistem eskiden "veri bulunamadı" diyip
susuyordu. Doğruydu ama **ne bildiğini göstermiyordu**: ölçüldü (`data/demo.db`,
2026-08-10, 24 soruluk temsilî küme) — 6 boş cevabın 6'sı da elindeki veriyi
söylemeden kapanıyordu. Manşet örnek:

    — "Araba alımında en yüksek finansman kimde var?"
    — "Karşılaştırılabilir veri bulunamadı… 3 kaydın hiçbiri doğrudan
       kıyaslanamıyor: kampanya süresi dolmuş (3 kayıt)"

Oysa elde şu vardı: üç kampanyanın hangi bankalara ait olduğu, ikisinin
bitiş tarihinin belgede hiç yazmadığı, birinin 29.02.2024'te kapandığı ve
bu alanın hangi ürün ailelerinde bulunduğu. Hiçbiri ek sorgu/ağ isteği
gerektirmiyordu.

Boş cevap artık üç cümlelik sabit bir iskelet üretir (`_kiyaslanamaz_metni`,
`_hic_kayit_metni`):

  1. **Sayım** — kaç kayıt vardı, hangi kapıda kaçı düştü.
  2. **En bilgilendirici ayrıntı** — eleme sebebine göre değişir: süresi
     dolmuşsa en son bilinen kapanış tarihi, düşük güvenliyse ölçülen en
     yüksek güven, aralıksa örnek aralık.
  3. **Sonraki adım** — kullanıcının gerçekten yapabileceği şey.

Kural: **uydurma yok**. Bilinmeyen bitiş tarihi "kayıtlarda yok" diye geçer
(82 belgede damga tarih taşımıyor); "açık kampanyalarda yok" gibi ölçülmemiş
bir iddia kurulmaz — damgasız belge "açık" demek değildir.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from dataclasses import field as dc_field
from typing import Any, Optional

from ..comparison.compare import (
    ASGARI_GUVEN,
    BILINMEYEN_TUR,
    ELEME_ARALIK,
    ELEME_BILINMIYOR,
    ELEME_DEGER_YOK,
    ELEME_DUSUK_GUVEN,
    ELEME_PARA_BIRIMI,
    ELEME_SAYISAL_DEGIL,
    ELEME_SURESI_DOLMUS,
    ELEME_TUTAR_BELIRSIZ,
    RankRow,
    eleme_sebebi,
    rank,
    tekil_banka_urun,
    turlere_ayir,
    yon_zorla,
)
from ..db.repository import Repository
from .router import BANK_DISPLAY, Route

#: Kullanıcı ürün ailesini SÖYLEMEDİĞİNDE tam listelenen aile sayısı.
#:
#: Karar (2026-08-10): tür söylenmediğinde ne yapılacağı üç seçenekliydi —
#: (a) ailelere göre grupla, (b) en kalabalık aileyi seç, (c) "hangi tür?" diye
#: sor. Seçilen **(a)**. Gerekçe:
#:
#:   * (b) bilgi ATAR ve attığını söylemez: `data/demo.db`'de "vade" sorusunun
#:     havuzunda 9 aile var ve en kalabalığı toplamın beşte birinden azını
#:     kapsıyor. Kullanıcının sormadığı bir daraltmayı sessizce yapmak, bu
#:     dosyanın banka süzgecinde açıkça yasakladığı davranışın aynısı.
#:   * (c) her listeleme sorusuna bir tur ekler; "en düşük kâr payı hangi
#:     bankada?" gibi manşet soruya soruyla karşılık vermek demodan puan
#:     götürür. Ayrıca cevabı bir tur ertelemek bilgi vermez.
#:   * (a) hiçbir bilgiyi atmaz, hiçbir aileler-arası sıralama üretmez ve
#:     `rank_advantageous_by_type()` ile aynı kararı verir — bileşik skor
#:     panelinde kapatılan "elma ile armut" boşluğu burada da kapanır.
#:
#: Sınır neden 3: aynı ölçümde tekilleştirme sonrası en kalabalık cevap 9
#: ailede 51 satırdı. Üç aile ~24 satır eder; sohbet kanalında okunabilir üst
#: sınır budur. Kalan aileler GİZLENMEZ, adlarıyla ve banka sayılarıyla
#: sayılır — kullanıcı aile adını yazarak tamamını alabilir.
_AZAMI_TUR = 3


@dataclass
class StructuredAnswer:
    text: str
    #: Cevapta GÖSTERİLEN satırlar (tekilleştirilmiş, gösterim sırasında).
    #: Eskiden havuzun tamamıydı: tek bir cevap 617 kaynak satırı taşıyabiliyor
    #: ve arayüzdeki kaynak listesi ekrandaki cevapla örtüşmüyordu.
    rows: list[RankRow]
    field: str
    intent: str


def answer(repo: Repository, r: Route) -> StructuredAnswer:
    havuz = repo.query_fields(r.field)

    # filtreler
    rows = _apply_filters(repo, havuz, r.filters)

    # Boş cevabın bağlamı SÜZGEÇTEN ÖNCEKİ havuzu da taşır: "bu ailede yok"
    # demek yetmez, "peki nerede var" sorusunun cevabı elimizde duruyor.
    baglam = _Baglam(field=r.field, intent=r.intent or "list",
                     filters=dict(r.filters or {}), havuz=havuz, repo=repo)

    # Eleme sayımı TEKİLLEŞTİRMEDEN ÖNCEKİ listeden okunur. `tekil` banka ×
    # ürün ailesi başına tek satır bırakır ve elediği kampanyaları yalnız
    # sayar; "3 kampanyanın üçü de kapanmış" gibi kapı bazlı bir sayım o
    # listeden çıkarılamaz — temsilcinin sebebi temsil ettiklerininkiyle aynı
    # olmak zorunda değildir.
    ranked = yon_zorla(rank(rows, r.field), r.field, r.intent)
    tekil = tekil_banka_urun(ranked)
    gruplar = turlere_ayir(tekil)

    # Hiç kayıt yok — süzgeç her şeyi eledi. Bu dal superlatif ve listeleme
    # için ORTAKTIR; ayrı ayrı yazılırsa ikisi zamanla ayrışır (bu depoda beş
    # kez olmuş bir hata). Cümlenin sonu niyete göre değişir, gövdesi değil.
    #
    # Kanıt satırları BİLEREK döndürülür: cevabın tek olgusal iddiası ("bu
    # alan şu ailelerde var") onlara dayanıyor ve çekimserlik kapısı
    # (`safety.guard_output` KAPI 5) kaynaksız gövdeyi haklı olarak siler.
    # Kanıt bulunamazsa liste boş kalır ve kapı devreye girer — istenen budur.
    if not ranked:
        metin, kanit = _hic_kayit_cevabi(r.field, baglam)
        return StructuredAnswer(metin, kanit, r.field, r.intent)

    if r.intent in ("lowest", "highest"):
        # Tek aile (ya da hiç veri): soru zaten iyi tanımlı, tek cümle yeter.
        # Bu dal ayrıca sözelleştirmenin çalıştığı tek dal — `bot._sozellestir`
        # yalnız tek satırlık şablonları LLM'e verir.
        if len(gruplar) <= 1:
            top = _grup_kazanani(tekil)
            if top is None:
                return StructuredAnswer(
                    _kiyaslanamaz_metni(r.field, ranked, baglam=baglam),
                    tekil, r.field, r.intent)
            return StructuredAnswer(_phrase_superlative(r.field, r.intent, top),
                                    tekil, r.field, r.intent)
        kazananlar = [(tur, _grup_kazanani(grup), grup) for tur, grup in gruplar]
        gosterilen = [k for _, k, _g in kazananlar if k is not None]
        if not gosterilen:
            # Hiçbir ailede kazanan yok. Eskiden burada tek bir sabit cümle
            # basılıyordu — tek aileli daldan bile az bilgi veren, en zayıf
            # boş cevap. Aynı iskelet burada da koşar.
            return StructuredAnswer(
                _kiyaslanamaz_metni(r.field, ranked, baglam=baglam),
                tekil, r.field, r.intent)
        return StructuredAnswer(
            _phrase_superlative_by_type(r.field, r.intent, kazananlar),
            gosterilen, r.field, r.intent)

    # list / filter
    if len(gruplar) <= 1:
        return StructuredAnswer(
            _phrase_list(r.field, tekil, r.filters, baglam=baglam),
            tekil, r.field, r.intent)
    text, gosterilen = _phrase_list_by_type(r.field, gruplar)
    return StructuredAnswer(text, gosterilen, r.field, r.intent)


def _grup_kazanani(grup: list[RankRow]) -> Optional[RankRow]:
    """Bir ailenin gösterilecek kazananı: ilk KIYASLANABİLİR satır.

    Sıra `rank()` + `yon_zorla()` tarafından zaten kurulmuştur; burada ikinci
    bir "en iyiyi seç" kuralı yazmak, sıralamayı ayrışma riskiyle tekrarlamak
    olurdu. Hiç kıyaslanabilir satır yoksa `None` — uydurma kazanan yok.
    """
    return next((x for x in grup if x.comparable), None)


def _apply_filters(repo: Repository, rows: list[dict], filters: dict) -> list[dict]:
    if not filters:
        return rows
    out = rows
    # banka filtresi — sorulan banka verimizde yoksa sonuç BOŞ kalır ve
    # chatbot çekimserlik kapısından dürüst "verimde yok" yanıtı üretir.
    # Başka bankaların satırlarını cevap gibi sunmak sessiz halüsinasyondur.
    banks = filters.get("banks")
    if banks:
        out = [r for r in out if r.get("bank") in banks]
    # kampanya türü filtresi
    ctype = filters.get("campaign_type")
    if ctype:
        out = [r for r in out if (r.get("campaign_type") == ctype)]
    # vade_ay_min: ilgili kampanyanın vade alanına bak.
    # Eskiden satır başına bir `repo.field_value()` sorgusu atılıyordu (N+1).
    # 1696 kampanyalık korpusta "36 ay ve üzeri vade veren konut finansmanları"
    # sorusu tek başına ~23 ms sürüyordu — chatbot'un ikinci en yavaş yolu.
    # Tek `query_fields("vade_ay")` çağrısı aynı veriyi bir sorguda getirir.
    vmin = filters.get("vade_ay_min")
    if vmin is not None:
        # `field_value()` fetchone() ile İLK satırı döndürüyordu; aynı
        # kampanyada birden fazla vade_ay satırı olursa (beklenmez ama şema
        # engellemiyor) setdefault ile yine ilkini alıyoruz.
        vade_by_campaign: dict[int, object] = {}
        for row in repo.query_fields("vade_ay"):
            vade_by_campaign.setdefault(row["campaign_id"], row["canonical_value"])
        out = [r for r in out
               if isinstance(vade_by_campaign.get(r["campaign_id"]), (int, float))
               and vade_by_campaign[r["campaign_id"]] >= vmin]
    return out


_FIELD_LABEL = {
    "kar_payi_orani": "kâr payı oranı",
    "vade_ay": "vade",
    "finansman_tutari": "finansman tutarı",
    "tahsis_ucreti": "tahsis ücreti",
    "masraf_durumu": "masraf durumu",
    "taksit_sayisi": "taksit sayısı",
}


def _fmt_value(field: str, value) -> str:
    if field == "kar_payi_orani" and isinstance(value, (int, float)):
        return f"%{value:g}".replace(".", ",")
    if field == "vade_ay" and isinstance(value, (int, float)):
        return f"{int(value)} ay"
    if isinstance(value, dict) and "value" in value:
        return f"{value['value']:g} {value.get('currency', 'TRY')}"
    if isinstance(value, dict) and "min" in value:
        return f"%{value['min']:g}–%{value['max']:g}".replace(".", ",")
    # Masraf durumu üç ayrı DURUMDUR ve üçü farklı cümle gerektirir. Bu dal
    # olmadan kullanıcıya ham sözlük gidiyordu — ölçüldü, demonun manşet
    # sorusunda görünüyordu:
    #     "en düşük masraf durumu: Kuveyt Türk ({'has_fee': False, ...})"
    # `amount is None` hâli ayrıca önemli: "ücret var, tutarı bilinmiyor"
    # sıralamada 0 TL sayılmamalıdır (bkz. `compare._numeric_key` — altıncı
    # kusur) ve metinde de "masrafsız" gibi okunmamalıdır.
    if isinstance(value, dict) and "has_fee" in value:
        if value.get("has_fee") is False:
            return "masrafsız"
        amount = value.get("amount")
        if amount is None:
            return "ücret var, tutarı belirtilmemiş"
        return f"{amount:g} TRY masraf"
    return str(value)


# =========================================================================== #
# Boş cevap — "veri yok" yerine "elimde şu var"
# =========================================================================== #


@dataclass
class _Baglam:
    """Boş cevabın ihtiyaç duyduğu, sorunun kendisinden gelen bağlam.

    `havuz` SÜZGEÇTEN ÖNCEKİ alan havuzudur: "Taşıt Finansmanı'nda tahsis
    ücreti yok" cevabının ardından gelecek "peki nerede var" bilgisi orada
    duruyor ve ek bir sorgu gerektirmiyor.

    `repo` yalnız **bitiş tarihi** için gerekir ve sorgu TEMBELDİR: tarih,
    boş cevapların yalnızca süresi dolmuş dalında okunur. Bağlamı olmayan
    çağıranlar (birim testler) `None` geçer ve metin tarihsiz kurulur —
    bilinmeyen tarih uydurulmaz.
    """

    field: str
    intent: str
    filters: dict
    havuz: list[dict] = dc_field(default_factory=list)
    repo: Optional[Repository] = None
    _bitisler: Optional[dict] = None

    def bitis(self, campaign_id: Any) -> Optional[str]:
        """Kampanyanın ISO bitiş tarihi; bilinmiyorsa `None`."""
        if self._bitisler is None:
            self._bitisler = {}
            if self.repo is not None:
                for r in self.repo.query_fields(_BITIS_ALANI):
                    tarih = _bitis_cikar(r.get("canonical_value"))
                    if tarih is not None:
                        self._bitisler.setdefault(r.get("campaign_id"), tarih)
        return self._bitisler.get(campaign_id)


#: Kampanya bitiş tarihini taşıyan alan. Kanonik değeri ISO-8601 bir dizedir
#: (`"2026-07-31"`); korpusta 937 kayıtta var, 82 belgede damga tarihsizdir.
_BITIS_ALANI = "kampanya_suresi"

#: Boş cevapta ADIYLA sayılan azami eleme sebebi. Üçüncü ve sonrası "başka
#: sebeplerle" diye toplanır: sohbet cevabı üç cümleyi geçmemeli.
_AZAMI_SEBEP = 2

#: "Peki nerede var" ipucunda sayılan azami aile/banka.
_AZAMI_IPUCU = 3

#: Eleme sebebi → sayım cümlesinde kullanılan sıfat/yüklem. Hem "üçü de X"
#: hem "5 kampanya X" kalıbına oturacak biçimde yazılıdır.
_SEBEP_SIFATI = {
    ELEME_SURESI_DOLMUS: "kapanmış",
    ELEME_DUSUK_GUVEN: "düşük çıkarım güveniyle işaretli",
    ELEME_ARALIK: "aralık olarak ilan edilmiş",
    ELEME_TUTAR_BELIRSIZ: "tutarı belirtilmemiş ücret taşıyor",
    ELEME_DEGER_YOK: "değeri boş",
    ELEME_PARA_BIRIMI: "TRY dışı para biriminde",
    ELEME_SAYISAL_DEGIL: "sayıya çevrilemeyen biçimde",
    ELEME_BILINMIYOR: "başka bir sebeple kıyas dışı",
}


def _bitis_cikar(value: Any) -> Optional[str]:
    """`kampanya_suresi` kanonik değerinden ISO bitiş tarihini alır.

    Korpusta değer düz bir ISO dizedir. Sözlük biçimi (başlangıç + bitiş)
    savunma amaçlı ayrıca ele alınır; tanınmayan biçim `None` döner —
    tarih uydurulmaz.
    """
    if isinstance(value, str) and value:
        return value
    if isinstance(value, dict):
        for anahtar in ("end", "bitis", "max"):
            alt = value.get(anahtar)
            if isinstance(alt, str) and alt:
                return alt
    return None


def _tarih_tr(iso: Optional[str]) -> Optional[str]:
    """`2026-07-31` → `31.07.2026`. Tanınmayan biçim `None`."""
    if not isinstance(iso, str):
        return None
    parcalar = iso.split("-")
    if len(parcalar) != 3 or not all(p.isdigit() for p in parcalar):
        return None
    yil, ay, gun = parcalar
    return f"{gun.zfill(2)}.{ay.zfill(2)}.{yil}"


def _sayi_tr(x: float) -> str:
    return f"{x:.2f}".replace(".", ",")


def _bas_harf(metin: str) -> str:
    """Cümle başını büyütür — `str.capitalize()` KULLANILMAZ.

    O metod hem geri kalanı küçültür (banka adlarını bozar) hem de 'i'yi
    Türkçe 'İ' yerine 'I' yapar. Burada yalnız ilk harf, Türkçe kuralıyla
    büyütülür.
    """
    if not metin:
        return metin
    ilk = "İ" if metin[0] == "i" else metin[0].upper()
    return ilk + metin[1:]


def _ve_ile(adlar: list[str]) -> str:
    """`["A", "B", "C"]` → `"A, B ve C"`."""
    if not adlar:
        return ""
    if len(adlar) == 1:
        return adlar[0]
    return ", ".join(adlar[:-1]) + " ve " + adlar[-1]


def _banka_adi(satir: dict) -> str:
    return satir.get("bank_name") or BANK_DISPLAY.get(
        satir.get("bank"), satir.get("bank") or "?")


def _hepsi(n: int) -> str:
    """Tek sebepli sayımda kullanılan "hepsi" ifadesi."""
    return {1: "o da", 2: "ikisi de", 3: "üçü de"}.get(n, "hepsi")


def _kapsam_oneki(filters: Optional[dict]) -> str:
    """Sorunun süzgecini cümle önekine çevirir.

    Ek harfleri (ilgi/bulunma) BİLEREK kullanılmaz: "Kuveyt Türk'ün" ile
    "Vakıf Katılım'ın" farklı ünlü uyumları ister ve tür adlarında durum
    daha da karışıktır ("Yatırım Ürünü'nde", "Kart'ta"). "… için" ve
    "… kampanyalarında" kalıpları hiçbir uyum gerektirmez ve her ad için
    doğru okunur.
    """
    if not filters:
        return ""
    parcalar = []
    banks = filters.get("banks")
    if banks:
        parcalar.append(_ve_ile([BANK_DISPLAY.get(b, b) for b in banks])
                        + " için")
    ctype = filters.get("campaign_type")
    if ctype:
        parcalar.append(f"{ctype} kampanyalarında")
    vmin = filters.get("vade_ay_min")
    if vmin is not None:
        parcalar.append(f"{vmin} ay ve üzeri vadede")
    return (" ".join(parcalar) + " ") if parcalar else ""


def _nerede_var(baglam: Optional[_Baglam]
                ) -> tuple[Optional[str], list[dict]]:
    """Süzgeç yüzünden boşalan sorguda alanın NEREDE bulunduğunu söyler.

    Bu cümle, boş cevabın en çok iş gören parçasıdır: kullanıcı "yok"
    duyduğunda bir sonraki soruyu tahmin etmek zorunda kalmasın. Veri
    süzgeçten önceki havuzda zaten duruyor, ek sorgu yok.

    İkinci dönüş değeri, cümlenin **kanıtıdır**: adı geçen her aile/banka
    için havuzdan bir temsilci satır. Cümle "Konut Finansmanı (3 banka)"
    diyorsa kullanıcı o üç kampanyanın hangileri olduğunu kaynak listesinden
    görebilmeli — aksi hâlde cevap, kendi doğrulanamayan bir iddiası olurdu.
    Kanıt yoksa liste boştur ve çekimserlik kapısı (bkz. `safety.guard_output`
    KAPI 5) doğru olanı yapar: kaynaksız cevap basılmaz.
    """
    if baglam is None or not baglam.havuz:
        return None, []
    tur = baglam.filters.get("campaign_type")
    # BANKA SÜZGECİ VARSA HİÇBİR İPUCU VERİLMEZ — ve bu bir eksiklik değil,
    # güvenlik kapısının açık şartıdır. `_apply_filters` zaten şunu yazıyor:
    # sorulan banka verimizde yoksa başka bankaların satırlarını cevap gibi
    # sunmak sessiz halüsinasyondur. Güvenlik kümesindeki C03–C05 kayıtları
    # ("Ziraat Katılım'ın konut finansmanı kâr payı oranı nedir?") cevapta
    # BAŞKA BİR BANKA ADI GEÇMEMESİNİ ve çekimserlik kapısının tetiklenmesini
    # şart koşuyor. "Peki hangi bankalarda var" cümlesi, tam da o kapının
    # engellediği şeyi kibar bir dille yapardı: kullanıcı Ziraat Katılım'ı
    # sordu, cevapta Kuveyt Türk okudu. Kanıt listesi de boş kalır; böylece
    # `safety.guard_output` KAPI 5 devreye girer ve dürüst çekimserliği basar.
    if baglam.filters.get("banks"):
        return None, []
    if tur:
        tur_havuzu = [r for r in baglam.havuz
                      if r.get("campaign_type") == tur]
        if not tur_havuzu:
            aileler: dict[str, list[dict]] = {}
            for r in baglam.havuz:
                aileler.setdefault(r.get("campaign_type") or BILINMEYEN_TUR,
                                   []).append(r)
            sirali = sorted(
                aileler.items(),
                key=lambda kv: (-len({_banka_adi(r) for r in kv[1]}), kv[0])
            )[:_AZAMI_IPUCU]
            if not sirali:
                return None, []
            liste = _ve_ile([f"{ad} ({len({_banka_adi(r) for r in satirlar})}"
                             f" banka)" for ad, satirlar in sirali])
            return (f"Bu alanı taşıyan ürün aileleri: {liste}.",
                    [satirlar[0] for _ad, satirlar in sirali])
        return _banka_ipucu(tur_havuzu,
                            f"{tur} kampanyalarında bu alanı taşıyan bankalar")
    return None, []


def _banka_ipucu(havuz: list[dict], bas: str) -> tuple[str, list[dict]]:
    """Havuzdaki bankaları adlarıyla sayar; her ad için bir temsilci satır."""
    ilk: dict[str, dict] = {}
    for r in havuz:
        ilk.setdefault(_banka_adi(r), r)
    adlar = sorted(ilk)[:_AZAMI_IPUCU]
    return f"{bas}: {_ve_ile(adlar)}.", [ilk[ad] for ad in adlar]


def _birim(ranked: list[RankRow]) -> str:
    """Sayımın birimi: satırlar ayrı kampanyalara aitse "kampanya".

    Aynı kampanyadan birden çok satır gelebildiği için (şema engellemiyor)
    "kampanya" demek her zaman doğru değildir; kimlikler ayrışmıyorsa daha
    dar ve her hâlde doğru olan "kayıt" kullanılır.
    """
    kimlikler = [x.campaign_id for x in ranked]
    if kimlikler and all(k is not None for k in kimlikler) \
            and len(set(kimlikler)) == len(kimlikler):
        return "kampanya"
    return "kayıt"


def _sayim_cumlesi(field: str, ranked: list[RankRow],
                   sayim: Counter, baglam: Optional[_Baglam]) -> str:
    """1. cümle — kaç kayıt vardı, hangi kapıda kaçı düştü."""
    label = _FIELD_LABEL.get(field, field)
    birim = _birim(ranked)
    n = len(ranked)
    onek = _kapsam_oneki(baglam.filters if baglam else None)
    bas = _bas_harf(f"{onek}{label} bilinen {n} {birim} var")
    if len(sayim) == 1:
        kod = next(iter(sayim))
        return f"{bas}; {_hepsi(n)} {_SEBEP_SIFATI[kod]}."
    parcalar = [f"{adet} {birim} {_SEBEP_SIFATI[kod]}"
                for kod, adet in sayim.most_common(_AZAMI_SEBEP)]
    kalan = n - sum(adet for _k, adet in sayim.most_common(_AZAMI_SEBEP))
    if kalan > 0:
        parcalar.append(f"{kalan} {birim} başka sebeplerle kıyas dışı")
    return f"{bas}: {', '.join(parcalar)}."


def _ayrinti_cumlesi(field: str, ranked: list[RankRow], baskin: str,
                     baglam: Optional[_Baglam]) -> Optional[str]:
    """2. cümle — baskın eleme sebebinin en bilgilendirici ayrıntısı."""
    ilgili = [x for x in ranked if eleme_sebebi(x.note) == baskin]
    if baskin == ELEME_SURESI_DOLMUS:
        return _kapanis_cumlesi(ilgili, baglam)
    if baskin == ELEME_DUSUK_GUVEN:
        guvenler = [x.confidence for x in ilgili if x.confidence is not None]
        if not guvenler:
            return None
        return (f"Ölçülen en yüksek çıkarım güveni {_sayi_tr(max(guvenler))}, "
                f"eşik {_sayi_tr(ASGARI_GUVEN)}.")
    if baskin == ELEME_ARALIK:
        ornek = ilgili[0]
        return (f"Değerler tek sayı değil aralık — örneğin "
                f"{ornek.bank_name or ornek.bank}: "
                f"{_fmt_value(field, ornek.value)}.")
    if baskin == ELEME_TUTAR_BELIRSIZ:
        return ("Belgelerde ücret alındığı yazıyor ama tutarı yok; sıfır "
                "saymak \"masrafsız\" demek olurdu.")
    return None


def _kapanis_cumlesi(ilgili: list[RankRow],
                     baglam: Optional[_Baglam]) -> Optional[str]:
    """Süresi dolmuş kayıtlarda en son BİLİNEN kapanış tarihi.

    Tarihi olmayan kayıt sessizce yok sayılmaz, sayılır: "82 belgede damga
    tarih taşımıyor" gerçeği kullanıcıdan gizlenirse, gösterilen tek tarih
    tüm kümenin tarihi sanılır.
    """
    if not ilgili:
        return None
    tarihli = []
    tarihsiz = 0
    for x in ilgili:
        iso = baglam.bitis(x.campaign_id) if baglam else None
        gosterim = _tarih_tr(iso)
        if gosterim is None:
            tarihsiz += 1
        else:
            tarihli.append((iso, gosterim, x))
    if not tarihli:
        return "Bu kayıtların bitiş tarihi belgelerde yazmıyor."
    iso, gosterim, satir = max(tarihli, key=lambda t: t[0])
    cumle = (f"En son bilinen kapanış: {satir.bank_name or satir.bank}, "
             f"{gosterim}")
    if tarihsiz:
        cumle += f" ({tarihsiz} kaydın bitiş tarihi belgelerde yazmıyor)"
    return cumle + "."


def _adim_cumlesi(baskin: str, baglam: Optional[_Baglam]) -> str:
    """3. cümle — kullanıcının gerçekten yapabileceği bir sonraki adım.

    "Kapanmışları göstereyim mi?" gibi, sistemin YAPAMAYACAĞI bir eylem
    önerilmez: elenen kayıtlar zaten cevabın altında kaynak olarak listelenir
    ve kullanıcı oradan ham kayda ulaşır.
    """
    filtre = baglam.filters if baglam else {}
    siralama = (baglam.intent if baglam else "list") in ("lowest", "highest")
    if filtre.get("campaign_type"):
        alternatif = "başka bir ürün ailesi deneyebilirsiniz"
    elif filtre.get("banks"):
        alternatif = "başka bir banka deneyebilirsiniz"
    else:
        alternatif = "başka bir alan sorabilirsiniz"
    if baskin == ELEME_SURESI_DOLMUS:
        eylem = "sıralama" if siralama else "listeleme"
        return (f"Kapanmış kayıtlar aşağıda kaynak olarak duruyor; {eylem} "
                f"için {alternatif}.")
    if baskin == ELEME_DUSUK_GUVEN:
        return ("Değerler silinmedi, kıyas dışı bırakıldı; aşağıdaki "
                "kaynaklardan ham kayda bakıp kendiniz değerlendirebilirsiniz.")
    if baskin == ELEME_ARALIK:
        return ("Aralıklar kıyas dışı tutuldu; tam aralığı aşağıdaki "
                "kaynaklardan görebilirsiniz.")
    if baskin == ELEME_TUTAR_BELIRSIZ:
        return ("Kayıtlar kıyas dışı bırakıldı; ücretin tutarını aşağıdaki "
                "kaynak metinden kontrol edebilirsiniz.")
    return (f"Değerler silinmedi, kıyas dışı bırakıldı; {alternatif} ya da "
            f"aşağıdaki kaynaklardan ham kayda ulaşabilirsiniz.")


def _kiyaslanamaz_metni(field: str, ranked: list[RankRow], *,
                        baglam: Optional[_Baglam] = None) -> str:
    """Kıyaslanabilir satır yokken NE BİLDİĞİNİ söyleyen cevap.

    Üç cümle: sayım → baskın sebebin ayrıntısı → sonraki adım. İskeletin
    gerekçesi modül başlığındadır. `baglam` verilmezse (birim testler,
    bağlamsız çağıranlar) cümleler kapsam öneki ve tarih olmadan kurulur —
    eksik bilgi uydurulmaz, yalnız söylenmez.
    """
    if not ranked:
        return _hic_kayit_metni(field, baglam)
    sayim: Counter = Counter(eleme_sebebi(x.note) or ELEME_BILINMIYOR
                             for x in ranked)
    baskin = sayim.most_common(1)[0][0]
    cumleler = [
        _sayim_cumlesi(field, ranked, sayim, baglam),
        _ayrinti_cumlesi(field, ranked, baskin, baglam),
        _adim_cumlesi(baskin, baglam),
    ]
    return " ".join(c for c in cumleler if c)


def _hic_kayit_cevabi(field: str, baglam: Optional[_Baglam] = None
                      ) -> tuple[str, list[RankRow]]:
    """Süzgeçten hiç kayıt geçmediğinde basılan cevap ve KANITI.

    "Kıyaslanamaz" ile "hiç yok" AYRI cevaplardır: birincisinde veri var ama
    kıyasa girmiyor, ikincisinde alan o kapsamda hiç çıkarılamamış. İkisini
    aynı cümleye toplamak, olmayan bir eleme (ya da olmayan bir veri) iddia
    etmek olurdu.

    Kanıt satırları, "peki nerede var" cümlesinde ADI GEÇEN aile/bankaların
    havuzdaki temsilcileridir. Sorunun kapsamına ait değildirler ve cevap
    bunu açıkça söyler; oraya konmalarının sebebi, cevabın tek olgusal
    iddiasının kaynağı olmalarıdır.
    """
    label = _FIELD_LABEL.get(field, field)
    onek = _kapsam_oneki(baglam.filters if baglam else None)
    eylem = ("sıralanacak"
             if baglam is not None and baglam.intent in ("lowest", "highest")
             else "listelenecek")
    cumleler = [_bas_harf(f"{onek}{label} taşıyan, {eylem} kayıt "
                          f"çıkarılamadı.")]
    ipucu, kanit = _nerede_var(baglam)
    if ipucu:
        cumleler.append(ipucu)
        cumleler.append("Bunlardan birini sorarsanız karşılaştırabilirim.")
    elif onek:
        cumleler.append("Bu alan, sorulan kapsamda hiç çıkarılamadı; başka "
                        "bir ürün ailesi ya da banka deneyebilirsiniz.")
    return " ".join(cumleler), rank(kanit, field)


def _hic_kayit_metni(field: str, baglam: Optional[_Baglam] = None) -> str:
    """`_hic_kayit_cevabi`'nin yalnız metnini isteyen çağıranlar için."""
    return _hic_kayit_cevabi(field, baglam)[0]

#: Kıyasın ürün ailesi içinde yapıldığını söyleyen dipnot. Kullanıcı ekranda
#: neden tek bir kazanan görmediğini bilmeli; aksi hâlde gruplu cevap
#: "sistem karar veremedi" gibi okunur.
_AILE_NOTU = ("_Farklı ürün aileleri (konut, taşıt, kart…) birbirinin "
              "alternatifi değildir; bu yüzden kıyas her ailenin içinde "
              "yapılır._")


def _phrase_superlative(field: str, intent: str, row: RankRow) -> str:
    label = _FIELD_LABEL.get(field, field)
    sup = "en düşük" if intent == "lowest" else "en yüksek"
    name = row.bank_name or row.bank
    val = _fmt_value(field, row.value)
    return f"{sup} {label}: **{name}** ({val})."


def _phrase_superlative_by_type(
        field: str, intent: str,
        kazananlar: list[tuple[str, Optional[RankRow], list[RankRow]]]) -> str:
    """Aile başına tek kazanan — aileler arası kıyas YAPILMADAN.

    Kazananı olmayan aile de satırıyla görünür: bir ailenin listeden düşmesi
    ile o ailede veri olmaması farklı şeylerdir ve ikisini tek görüntüde
    toplamak, olmayan bir kapsama iddia etmektir.

    Kazananı olmayan ailede artık SEBEP de yazılır. "Kıyaslanabilir veri yok"
    tek başına, elenmiş bir değeri hiç var olmamış gibi gösteriyordu — bu,
    zayıf değeri silmenin cümle hâli. Ailede bulunan ilk kayıt değeriyle ve
    notuyla basılır; kullanıcı hem neyin bulunduğunu hem neden sıralanmadığını
    görür.
    """
    label = _FIELD_LABEL.get(field, field)
    sup = "en düşük" if intent == "lowest" else "en yüksek"
    lines = [f"{sup} {label} — her ürün ailesinde ayrı ayrı:"]
    for tur, k, grup in kazananlar:
        if k is None:
            gerekce = next((x for x in grup if x.note), None)
            if gerekce is not None:
                lines.append(
                    f"- {tur}: sıralanabilir kayıt yok — "
                    f"{gerekce.bank_name or gerekce.bank} "
                    f"{_fmt_value(field, gerekce.value)} "
                    f"_({gerekce.note})_"
                    + (f", +{len(grup) - 1} kayıt daha" if len(grup) > 1 else ""))
            else:
                lines.append(f"- {tur}: kıyaslanabilir veri yok")
            continue
        lines.append(f"- {tur}: **{k.bank_name or k.bank}** "
                     f"({_fmt_value(field, k.value)})")
    lines.append("")
    lines.append(_AILE_NOTU)
    return "\n".join(lines)


def _satir(field: str, r: RankRow) -> str:
    """Tek liste satırı — kıyaslanamama notu ve elenen kampanya sayısıyla.

    `other_count` `/compare`'in "+N kampanya daha" rozetinin sohbet
    karşılığıdır: bankanın o ailedeki diğer kampanyaları SİLİNMEZ, sayılır.
    """
    name = r.bank_name or r.bank
    val = _fmt_value(field, r.value)
    ek = "" if r.comparable else f"  _(not: {r.note})_"
    if r.other_count:
        ek += f"  _(+{r.other_count} kampanya daha)_"
    return f"- {name}: {val}{ek}"


def _phrase_list(field: str, ranked: list[RankRow], filters: dict, *,
                 baglam: Optional[_Baglam] = None) -> str:
    label = _FIELD_LABEL.get(field, field)
    if not ranked:
        # Eskiden burada tek bir sabit cümle vardı ("Bu kritere uyan kampanya
        # bulunamadı."). Kriteri kullanıcı zaten biliyor; bilmediği, alanın
        # nerede BULUNDUĞU. Aynı boş cevap iskeleti listeleme dalında da koşar.
        return _hic_kayit_metni(field, baglam or _Baglam(
            field=field, intent="list", filters=dict(filters or {})))
    lines = [_satir(field, r) for r in ranked]
    head = f"{label} (uygun kampanyalar):"
    if filters.get("campaign_type"):
        head = f"{filters['campaign_type']} — {head}"
    return head + "\n" + "\n".join(lines)


def _phrase_list_by_type(field: str,
                         gruplar: list[tuple[str, list[RankRow]]]
                         ) -> tuple[str, list[RankRow]]:
    """Ürün ailesine göre bloklu liste; taşan aileler sayılarak duyurulur.

    Dönüş: (metin, gösterilen satırlar). Gösterilmeyen aileler adlarıyla ve
    banka sayılarıyla yazılır — kullanıcı aile adını sorup tamamını alabilir.
    """
    label = _FIELD_LABEL.get(field, field)
    gosterilecek = gruplar[:_AZAMI_TUR]
    tasan = gruplar[_AZAMI_TUR:]

    lines = [f"{label} — ürün ailesine göre:"]
    gosterilen: list[RankRow] = []
    for tur, grup in gosterilecek:
        lines.append("")
        lines.append(f"**{tur}**")
        for x in grup:
            lines.append(_satir(field, x))
            gosterilen.append(x)
    lines.append("")
    lines.append(_AILE_NOTU)
    if tasan:
        adlar = ", ".join(f"{tur} ({len(grup)} banka)" for tur, grup in tasan)
        lines.append(f"_Bu alanda veri taşıyan diğer ürün aileleri: {adlar}. "
                     f"Aile adını yazarsanız o aileyi tam listelerim._")
    return "\n".join(lines), gosterilen
