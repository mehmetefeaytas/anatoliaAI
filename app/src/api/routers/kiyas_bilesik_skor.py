"""`/advantageous` — §5.7 "En Avantajlı Kampanya": çok alanlı ağırlıklı skor.

`routers/kiyas.py`'den ayrıldı (21 Ağu 2026). Uç gövdesi ve **docstring'i**
BİREBİR taşındı; davranış değişikliği yok.

## Niçin AYRI bir modül

Diğer dört uç TEK alan üzerinden sıralar ya da hiç sıralamaz. Bu uç alanlar
ARASI ağırlıklı bileşik skor üretir ve bu, cinsi farklı bir karardır:
ağırlıklar bir **ÜRÜN KARARIDIR**, ölçümden türetilmiş sabit değildir.
`weight_manifest()` her ağırlığı gerekçesiyle döndürüyor tam bu yüzden.

Ayrı modül olmasının somut gerekçesi, bu ucun kendi tarihidir: `compare.py`
içindeki ~420 satırlık bileşik skorlama yazılı ve testliydi ama **hiçbir
uçtan çağrılmıyordu** — üstelik `/scoring` "böyle bir şey yok" diyerek onu
yalanlıyordu. Kod bir dosyanın 727. satırında görünmez olduğu için değil,
sorumluluğu adı konmadığı için kayboldu. Adı konmuş bir modül, bir daha
sessizce kaybolmasını zorlaştırıyor.

Üç kapı (`MIN_GROUP_SIZE`, `min_coverage`, sayıya indirgenemeyen alan)
`comparison/compare.py`'de yaşar; bu modül onları ÇAĞIRIR ve hepsini çıktıda
görünür kılar — gizlemez.

## Sorumluluk sınırı

  * kapı değerlerinin çıktıda raporlanması + adil kıyas notu -> BURADA
  * kampanya başına alan sözlüğü toplama -> `kiyas_toplama`
  * ağırlıklar, normalizasyon, grup kapısı -> `comparison/compare.py`
"""

from __future__ import annotations

from typing import Any, Callable, Optional

from ...comparison.compare import (
    ASGARI_GUVEN,
    DEFAULT_WEIGHTS,
    MIN_COVERAGE,
    MIN_GROUP_SIZE,
    rank_advantageous_by_type,
    weight_manifest,
)
from .kiyas_toplama import bilesik_skor_kampanyalari


def uc_ekle(r: Any, *, field_rows: Callable[..., list[dict]]):
    """`/advantageous`'u `r`'ye kaydeder.

    `MIN_COVERAGE` uç İMZASINDA varsayılan değer olarak duruyor, yani
    `/openapi.json`'da görünür bir sözleşme parçası. Bu yüzden sabit hem
    burada hem cephede import edilmiyor — imza bu modülde tanımlı olduğu için
    yalnız burada gerekiyor.
    """
    _field_rows = field_rows

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
        by_campaign = bilesik_skor_kampanyalari(
            DEFAULT_WEIGHTS, field_rows=_field_rows)

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

    return advantageous
