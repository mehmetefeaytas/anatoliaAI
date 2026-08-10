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
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from ..comparison.compare import (
    RankRow,
    rank,
    tekil_banka_urun,
    turlere_ayir,
    yon_zorla,
)
from ..db.repository import Repository
from .router import Route

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
    rows = repo.query_fields(r.field)

    # filtreler
    rows = _apply_filters(repo, rows, r.filters)

    ranked = yon_zorla(rank(rows, r.field), r.field, r.intent)
    tekil = tekil_banka_urun(ranked)
    gruplar = turlere_ayir(tekil)

    if r.intent in ("lowest", "highest"):
        # Tek aile (ya da hiç veri): soru zaten iyi tanımlı, tek cümle yeter.
        # Bu dal ayrıca sözelleştirmenin çalıştığı tek dal — `bot._sozellestir`
        # yalnız tek satırlık şablonları LLM'e verir.
        if len(gruplar) <= 1:
            top = _grup_kazanani(tekil)
            if top is None:
                return StructuredAnswer(_KIYASLANAMAZ, tekil, r.field, r.intent)
            return StructuredAnswer(_phrase_superlative(r.field, r.intent, top),
                                    tekil, r.field, r.intent)
        kazananlar = [(tur, _grup_kazanani(grup)) for tur, grup in gruplar]
        gosterilen = [k for _, k in kazananlar if k is not None]
        if not gosterilen:
            return StructuredAnswer(_KIYASLANAMAZ, tekil, r.field, r.intent)
        return StructuredAnswer(
            _phrase_superlative_by_type(r.field, r.intent, kazananlar),
            gosterilen, r.field, r.intent)

    # list / filter
    if len(gruplar) <= 1:
        return StructuredAnswer(_phrase_list(r.field, tekil, r.filters),
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


#: Hiçbir satır kıyaslanabilir değilken basılan cevap.
_KIYASLANAMAZ = ("Karşılaştırılabilir veri bulunamadı (değerler aralık veya "
                 "farklı birimde olabilir).")

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
        kazananlar: list[tuple[str, Optional[RankRow]]]) -> str:
    """Aile başına tek kazanan — aileler arası kıyas YAPILMADAN.

    Kazananı olmayan aile de satırıyla görünür ("kıyaslanabilir veri yok"):
    bir ailenin listeden düşmesi ile o ailede veri olmaması farklı şeylerdir
    ve ikisini tek görüntüde toplamak, olmayan bir kapsama iddia etmektir.
    """
    label = _FIELD_LABEL.get(field, field)
    sup = "en düşük" if intent == "lowest" else "en yüksek"
    lines = [f"{sup} {label} — her ürün ailesinde ayrı ayrı:"]
    for tur, k in kazananlar:
        if k is None:
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


def _phrase_list(field: str, ranked: list[RankRow], filters: dict) -> str:
    label = _FIELD_LABEL.get(field, field)
    if not ranked:
        return "Bu kritere uyan kampanya bulunamadı."
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
