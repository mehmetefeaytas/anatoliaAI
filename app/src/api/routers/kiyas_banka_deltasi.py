"""`/bank-delta` — BANKANIN sorusu: "bende ne eksik, rakipte ne var?"

`routers/kiyas.py`'den ayrıldı (21 Ağu 2026). Uç gövdesi ve **docstring'i**
BİREBİR taşındı; davranış değişikliği yok.

## Niçin AYRI bir modül

Diğer dört uç müşterinin sorusunu yanıtlar; bu uç bankanın sorusunu yanıtlar.
Aynı çıkarım verisi, TERSİNDEN. Gövdesi de bu yüzden diğerlerine benzemiyor:
tek bir sıralama döndürmüyor, **ürün ailesi × alan** ızgarasında dört ayrı
karar veriyor ve bu dört karar bu modülün asıl sorumluluğudur:

    1. aile keşfi        hangi ürün aileleri var (alan satırları + bankanın
                         kendi belgeleri birleşimi)
    2. taraf seçimi      "benim" en iyi satırım / "rakip" kim
    3. konum             "7 bankadan 3." — banka başına TEK konum
    4. delta türü        rakip_yok | eksik_urun | eksik_veri | gerçek fark

Dördüncüsü tek başına ayrı bir modülü hak edecek kadar kritik: `eksik_urun`
ile `eksik_veri` AYRIDIR ve eskiden ikisi de aynı kırmızı etikete düşüyordu.
"Veri yok ≠ ürün yok" vaadi tam burada tutulur; kararı 807 satırlık bir
dosyanın ortasında bırakmak, onu gözden saklamaktı.

## Sorumluluk sınırı: ne BURADA, ne başka yerde

  * aile / taraf / konum / delta türü -> BURADA
  * alan × satır toplama + banka belge sayımı -> `kiyas_toplama`
  * taraf görünümü (kanıt + çelişki + katman) -> `kiyas_kanit_satiri`
  * sıralama + token geri eşleme -> `kiyas.delta_siralamasi` (cephede KALIYOR)
  * fark aritmetiği -> `comparison/compare.delta_between`
"""

from __future__ import annotations

from typing import Any, Callable, Optional

from ...comparison.compare import delta_between
from ...extraction.llm.schema import EXTRACTION_FIELDS
from ..sabitler import FIELD_LABELS
from ..yardimcilar import _en_iyi_taraf, scoring_direction
from .kiyas_kanit_satiri import taraf_gorunumu
from .kiyas_toplama import banka_belge_sayilari, delta_alan_tablosu


def uc_ekle(
    r: Any,
    repo: Any,
    *,
    field_rows: Callable[..., list[dict]],
    campaign_view: Callable[[int], Optional[dict]],
    campaign_contradictions: Callable[..., list],
    delta_siralamasi: Callable[..., list],
):
    """`/bank-delta`'yı `r`'ye kaydeder.

    `repo` konumsal: bu uç, diğer dördünden farklı olarak depoyu DOĞRUDAN
    okuyor (`all_campaigns(govde=False)`) — "ürün yok" ile "veri yok" ayrımı
    çıkarım tablosundan değil belge sayımından geliyor. Bağımlılığın imzada
    ayrı durması bu farkı görünür kılıyor.
    """
    _field_rows = field_rows

    def _gorunum(satir: Optional[dict], sk: Optional[float],
                 kiyaslanabilir: bool, not_: Optional[str]) -> Optional[dict]:
        """Serileştirme katmanına köprü — çağrı yerleri BİREBİR korunsun diye.

        Durumlu iki bağımlılığı (`campaign_view`, `campaign_contradictions`)
        bir kez bağlar; gövdedeki dört çağrı yeri eskisi gibi dört argümanla
        çağırmaya devam eder.
        """
        return taraf_gorunumu(
            satir, sk, kiyaslanabilir, not_,
            campaign_view=campaign_view,
            campaign_contradictions=campaign_contradictions)

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


        # Alan × satır tablosu ve ürün aileleri tek geçişte kurulur; her alan
        # için depo bir kez sorgulanır (eskiden istemci 8 ayrı HTTP isteği
        # atıyordu).
        alan_satirlari, aileler = delta_alan_tablosu(
            alanlar, field_rows=_field_rows, type=type)

        # Bankanın kendi belgelerinin bulunduğu aileler — "ürün yok" ile "veri
        # yok" ayrımı buna dayanır.
        kendi_belgeleri = banka_belge_sayilari(repo, bank, type)

        aileler.update(kendi_belgeleri)
        if type:
            aileler = {a for a in aileler if a == type}

        cikti_aileler = []
        for aile in sorted(aileler, key=lambda a: (a is None, str(a))):
            alan_ciktilari = []
            for alan in alanlar:
                aile_satirlari = [r for r in alan_satirlari[alan]
                                  if r.get("campaign_type") == aile]
                # Sıralama + token geri eşleme cephede koşuyor; niçin orada
                # kaldığı `kiyas.delta_siralamasi` docstring'inde yazılı.
                eslesmis = delta_siralamasi(aile_satirlari, alan)

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

    return bank_delta
