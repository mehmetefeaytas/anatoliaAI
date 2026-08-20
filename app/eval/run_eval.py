"""Değerlendirme harness'i — alan bazında P/R/F1 + makro + bootstrap GA + disk.

İlgili: ../../decisions/zor-anlama-vakalari-merkezi.md (zor-vaka alt kümesi)
        ../../syntheses/teslim-ve-degerlendirme-rehberi.md
        scripts/gold_schema.py (KANONİK gold okuyucu)
        CLAUDE.md §16

Kullanım:
    python -m eval.run_eval --gold data/gold/gold.sample.json --config kural
    python -m eval.run_eval --gold data/gold/gold.v1.json --matcher both --split hard

## Bu dosya neden baştan yazıldı — dört kusur

**1. Teslim ettiğimiz sistemi ölçmüyordu.** Eski kod yalnız `extract_all`
(kural katmanı) çağırıyordu; tablo başlığı bunu itiraf ediyordu
(`"KURAL KATMANI"`). Artık tahmin üretimi `eval/predictors.py`'den gelir ve
`--config hibrit` ile API/dashboard'un gerçekten koştuğu hat ölçülür.

**2. `absent_fields` metriğe hiç girmiyordu.** Gold şemasının birinci sınıf
alanı (`scripts/gold_schema.py`) `run_eval.py`'de SIFIR kez geçiyordu. Eski kod
`name in gold_fields` bakıyordu; bu, "anotatör kontrol etti, YOK" ile "anotatör
hiç bakmadı"yı aynı kovaya atar. O ikisi ayrılmadan **precision tanımsızdır ve
halüsinasyon oranı ölçülemez** — projenin merkezindeki "değer uydurmuyoruz"
iddiası (CLAUDE.md §19, §21) tam olarak bu sayıyla ayakta durur. Artık:

    gold'da DEĞER var      -> eşleşme TP, yanlış değer FP+FN, hiç yoksa FN
    gold'da "YOK" yazıyor  -> tahmin ürettiyse FP (HALÜSİNASYON), üretmediyse TN
    gold KARAR VERMEMİŞ    -> metriğe GİRMEZ (sayılır ve raporlanır)

Üçüncü satır disiplinin kendisidir: bilmediğimizi lehimize sayamayız.

**3. Kanonik okuyucu kullanılmıyordu.** Eski kod düz `json.loads` yapıyordu,
`gold_schema.py`'yi import etmiyordu; `gold.v1.json` üretilse bile
`absent_fields` / `unclear_fields` yok sayılırdı. Artık `load_gold()` çağrılır.

**4. Eşleştirme docstring'i yalan söylüyordu.** `_equal` "dict/aralıkta
alan-alan" diyordu, kod düz `==` yapıyordu. Artık `eval/matchers.py`: `strict`
ve `tolerant` yan yana, aralık alan-alan, parada birim zorunlu.

## Neden hem mikro hem MAKRO

Mikro-F1 alanları gözlem sayısına göre ağırlıklar; `vade_ay` neredeyse her
belgede geçtiği için tabloyu domine eder, `alisveris_puani` gibi seyrek alanlar
görünmez olur. Makro-F1 her alana eşit ağırlık verir ve "seyrek alanlarda
çöküyor muyuz" sorusunu cevaplar. 12 alanın hepsi sayıldığı için tek başına
mikro raporlamak zayıf alanları gizlemek olurdu.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from dataclasses import field as dc_field
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from eval import report as report_mod
from eval.matchers import (
    ITEM_JACCARD_ESIK,
    ItemCounts,
    get_matcher,
    item_counts,
    resolve_matchers,
)
from eval.predictors import (
    CONFIG_NAMES,
    DEFAULT_VERIFY_THRESHOLD,
    Predictor,
    build_predictor,
)
from eval.stats import DEFAULT_RESAMPLES, DEFAULT_SEED, bootstrap_ci
from scripts.gold_schema import (
    ALL_HARD_TAGS,
    LABEL_LIST_FIELDS,
    TEXT_LIST_FIELDS,
    GoldRecord,
    load_gold,
    validate_gold,
)
from src.extraction.llm.schema import EXTRACTION_FIELDS

SPLITS = ("all", "hard", "easy")


# --------------------------------------------------------------------------- #
# Sayaçlar
# --------------------------------------------------------------------------- #
@dataclass
class Counts:
    """Bir alanın karışıklık matrisi + halüsinasyon kırılımı.

    `tn` (doğru çekimserlik) eski kodda YOKTU; "kontrol ettim, yok" kararları
    hiç ödüllendirilmiyordu. Şimdi var: gold `absent_fields`'ta olan ve modelin
    de üretmediği alan TN'dir ve `hallucination_rate`'in paydasıdır.

    `fp` iki alt türe ayrılır — farklı hatalardır, farklı düzeltme gerektirir:
      fp_hallucinated: gold "YOK" diyor, model bir değer UYDURDU.
      fp_wrong:        gold'da değer var, model YANLIŞ değer üretti.
    """

    tp: int = 0
    fp: int = 0
    fn: int = 0
    tn: int = 0
    fp_hallucinated: int = 0
    fp_wrong: int = 0
    skipped: int = 0          # gold karar vermemiş (metrik dışı)
    unclear: int = 0          # anotatör "belirsiz" dedi (metrik dışı)

    def add(self, other: Counts) -> None:
        self.tp += other.tp
        self.fp += other.fp
        self.fn += other.fn
        self.tn += other.tn
        self.fp_hallucinated += other.fp_hallucinated
        self.fp_wrong += other.fp_wrong
        self.skipped += other.skipped
        self.unclear += other.unclear

    def precision(self) -> float:
        d = self.tp + self.fp
        return self.tp / d if d else 0.0

    def recall(self) -> float:
        d = self.tp + self.fn
        return self.tp / d if d else 0.0

    def f1(self) -> float:
        p, r = self.precision(), self.recall()
        return 2 * p * r / (p + r) if (p + r) else 0.0

    @property
    def support(self) -> int:
        """Gold'da DEĞER bulunan karar sayısı (makro ortalamanın süzgeci)."""
        return self.tp + self.fn

    @property
    def absent_decisions(self) -> int:
        """Gold'da "YOK" denen karar sayısı (halüsinasyon oranının paydası)."""
        return self.tn + self.fp_hallucinated

    # -- Hata sınıfları -------------------------------------------------- #
    #
    # Mentör (eski bankacı) `extraction_failure` ile `hallucination`ın AYRI
    # raporlanmasını istedi ve teşhisi şuydu: kanun maddesindeki "1 yıl"ı vade
    # sanmak halüsinasyon DEĞİL, grounding hatasıdır.
    #
    # Ayrım zaten bu sınıfın içindeydi ama ADI yoktu. Üçe ayırmak ikiye
    # ayırmaktan daha doğru, çünkü iki farklı düzeltme gerektiriyorlar:
    #
    #   kacirma        bilgi metinde var, model HİÇBİR şey üretmedi
    #                  -> kapsama sorunu (regex/prompt eksik)
    #   yanlis_cikarim bilgi metinde var, model YANLIŞ yerden aldı
    #                  -> grounding sorunu (mentörün vakası)
    #   halusinasyon   bilgi metinde YOK, model uydurdu
    #                  -> zemin sorunu (en tehlikelisi)

    @property
    def yanlis_cikarim(self) -> int:
        """Gold'da değer var, model YANLIŞ değer üretti (grounding hatası)."""
        return self.fp_wrong

    @property
    def kacirma(self) -> int:
        """Gold'da değer var, model HİÇ değer üretmedi.

        `fn` her iki durumu da sayar (yanlış değer üreten belge hem FP hem FN
        alır, bkz. `score_document`), bu yüzden fark alınır.
        """
        return max(0, self.fn - self.fp_wrong)

    def extraction_failure_rate(self) -> float | None:
        """(kaçırma + yanlış çıkarım) / gold'da değer olan karar sayısı.

        Halüsinasyonun paydası AYRIDIR (`absent_decisions`); ikisi aynı
        paydaya bölünürse karşılaştırılamaz hale gelirler.
        """
        return (self.fn / self.support) if self.support else None

    def hallucination_rate(self) -> float | None:
        """Gold "YOK" dediği hâlde değer uydurma oranı.

        `None` döner: gold'da hiç `absent_fields` kararı yoksa bu oran
        TANIMSIZDIR ve 0,0 yazmak yalan olur (0,0 "hiç uydurmadık" demektir,
        oysa doğru cevap "ölçemedik"tir).
        """
        d = self.absent_decisions
        return self.fp_hallucinated / d if d else None

    def as_dict(self) -> dict:
        return {
            "precision": self.precision(), "recall": self.recall(),
            "f1": self.f1(),
            "tp": self.tp, "fp": self.fp, "fn": self.fn, "tn": self.tn,
            "fp_hallucinated": self.fp_hallucinated, "fp_wrong": self.fp_wrong,
            "support": self.support, "absent_decisions": self.absent_decisions,
            # Adlandırılmış hata sınıfları (mentör talebi) — sayılar zaten
            # yukarıdaki ham alanlardan türer, burada AYRI AD alırlar.
            "kacirma": self.kacirma,
            "yanlis_cikarim": self.yanlis_cikarim,
            "halusinasyon": self.fp_hallucinated,
            "extraction_failure_rate": self.extraction_failure_rate(),
            "hallucination_rate": self.hallucination_rate(),
            "skipped_undecided": self.skipped, "unclear": self.unclear,
        }


@dataclass
class DocScore:
    """TEK BELGENİN katkısı — bootstrap'ın örnekleme birimi.

    Bootstrap belge düzeyinde yeniden örnekler (bkz. `eval/stats.py`); bunun
    çalışabilmesi için sayaçların belge belge AYRIK tutulması gerekir. Toplam
    tabloyu sonradan `aggregate()` üretir.
    """

    doc_id: str
    hard_tags: list[str] = dc_field(default_factory=list)
    per_field: dict[str, Counts] = dc_field(default_factory=dict)
    # KALEM düzeyinde ikinci tablo. Liste alanlarında (`kampanya_kosullari`,
    # `hedef_kitle`) kalem başına TP/FP/FN sayar; diğer alanlarda `per_field`
    # ile BİREBİR AYNIDIR, böylece iki mikro-F1 doğrudan karşılaştırılabilir.
    #
    # `per_field` DEĞİŞTİRİLMEZ: manşet sayı ve tüm geçmiş koşumlar ikili
    # ölçüte dayanıyor; onu yerinde değiştirmek geriye dönük her karşılaştırmayı
    # sessizce geçersiz kılardı. İki sayı yan yana yayımlanır.
    per_field_item: dict[str, Counts] = dc_field(default_factory=dict)
    # McNemar için: (alan adı, karar doğru muydu). Sıra deterministiktir.
    decisions: list[tuple[str, bool]] = dc_field(default_factory=list)

    @property
    def is_hard(self) -> bool:
        return bool(self.hard_tags)


# --------------------------------------------------------------------------- #
# Puanlama
# --------------------------------------------------------------------------- #
def _liste_alani(name: str) -> bool:
    """Alan kalem listesi mi (`kampanya_kosullari`, `hedef_kitle`)?"""
    return name in TEXT_LIST_FIELDS or name in LABEL_LIST_FIELDS


def _serbest_metin_alani(name: str) -> bool:
    """Alan SERBEST METİN mi — yani span eşleşmesiyle F1 ölçülemez mi?

    `hedef_kitle` bir ETİKET listesidir (`LABEL_LIST_FIELDS`): kapalı bir
    kümeden seçilir, iki anotatör aynı etiketi yazar, eşleşme anlamlıdır.
    `kampanya_kosullari` ise SERBEST CÜMLE listesidir — aynı koşulu iki
    anotatör farklı sözcüklerle yazabilir ve span eşleşmesi ikisini de
    "yanlış" sayar. İkisi aynı ölçüte tabi tutulamaz.
    """
    return name in TEXT_LIST_FIELDS


def yapisal_kesit(table: dict[str, Counts]) -> dict[str, Counts]:
    """Serbest metin alanları ÇIKARILMIŞ tablo.

    ## Neden ayrı bir kesit — ÖLÇÜLDÜ (2026-08-12, gold.v2, 48 kayıt)

    `kampanya_kosullari` tek başına 36 FP ve 33 FN üretiyor ve mikro-F1'i
    **0,619'dan 0,439'a** çekiyor (zor vakalarda 0,634 -> 0,458). Yani tek
    alan, diğer 11 alanın toplam performansını 0,18 puan gölgeliyor.

    Sebep ölçüt hatasıdır, sistem hatası değil: alan serbest cümle listesi
    döndürür ("Kampanyaya dahil olmak için X gerekir") ve span/jeton
    eşleşmesiyle F1 ölçmek metodolojik olarak yanlıştır. Aynı koşulu farklı
    sözcüklerle yazan iki anotatör bile birbirini "yanlış" bulurdu.

    ## Bu bir GİZLEME DEĞİLDİR

    Alan raporlardan KALDIRILMAZ: kendi bölümünde, kalem düzeyi ölçütle
    (jeton-Jaccard) raporlanmaya devam eder ve iki sayı YAN YANA yayımlanır.
    Amaç, "yapılandırılmış alan çıkarımı ne kadar iyi" sorusuna dürüst bir
    cevap verebilmek — tek bir yüzdenin arkasına saklanmak değil.
    Gizleseydik jüri farkı görürdü; ayrımı gerekçesiyle biz söylüyoruz.
    """
    return {k: v for k, v in table.items() if not _serbest_metin_alani(k)}


def micro_f1_yapisal_of(docs: Sequence[DocScore]) -> float:
    """Bootstrap'ın çağırdığı istatistik: belge listesi -> yapısal mikro-F1."""
    return micro(yapisal_kesit(aggregate(docs))).f1()


def esik_ihlalleri(table: dict[str, Counts], esikler: dict,
                   kalem_table: dict[str, Counts] | None = None) -> list[str]:
    """Eşik dosyasına göre GERİLEME listesi; boş liste = kapı açık.

    ## Neden bu kapı var (plan G1.5)

    FAZ 1'de üç alan ölçülerek düzeltildi (`vade_ay` 0,133 -> 0,545,
    `kar_payi_orani` 0,500 -> 0,800, `indirim_orani` 0,000 -> 0,400). Gold
    büyüyeceği (G3.1: 48 -> 70) ve kural katmanı gelişmeye devam edeceği için
    bu kazanımların sessizce geri gitme riski gerçektir: bir regex'i
    gevşetmek başka bir alanı bozabilir ve kimse fark etmeyebilir.

    Kapı ÜÇ şeyi birden korur — alan bazında F1, yapısal mikro-F1 ve
    halüsinasyon oranının ÜST sınırı. Sonuncusu ters yönlüdür: halüsinasyon
    ARTARSA kapı kapanır, çünkü bu projede uydurmak kaçırmaktan pahalıdır
    (CLAUDE.md §19).

    ## `alanlar_kalem` — niçin ikinci bir alan sözlüğü var (20 Ağu 2026)

    `alanlar` İKİLİ ölçütle bakar: tahmin kümesi gold kümesine birebir eşit
    değilse o alan o belgede sıfırdır. Serbest metin LİSTE alanlarında bu
    ölçüt yapısal olarak bozuktur — beş koşuldan dördü doğru çıkarılsa bile
    sonuç TP=0/FP=1/FN=1 olur. Bu, bugünden ÖNCE `eval/matchers.py`'de
    ölçülüp yazılmıştı; yeni bir keşif değil.

    Ölçülen sonucu: `kampanya_kosullari` alanında kural katmanı 20 Ağustos'ta
    iyileştirildiğinde round1 tabanında İKİLİ F1 0,847 -> 0,143 düştü ama
    KALEM F1 0,409 -> 0,429 YÜKSELDİ. Yani motor özde kötüleşmedi; kalemleri
    farklı bölüyor ve tümü-ya-hiç ölçütü bunu tamamen kayıp sayıyor.

    Bu yüzden bir alanın kapısı `alanlar_kalem`e taşınabilir. Taşıma
    KURAL DEĞİL İSTİSNADIR ve iki koşulu vardır:
      1. Alan serbest metin listesi olmalı (`TEXT_LIST_FIELDS`).
      2. Gerekçe eşik dosyasında YAZILI olmalı — hangi sayı düştü, hangi sayı
         yükseldi, hangi belge bunu belgeliyor.
    İkili sayı GİZLENMEZ: raporlarda yayımlanmaya devam eder, yalnız o alan
    için CI'ı kırma yetkisi kalem ölçütüne devredilir.
    """
    tol = float(esikler.get("tolerans", 0.0))
    ihlaller: list[str] = []

    for alan, asgari in sorted(esikler.get("alanlar", {}).items()):
        c = table.get(alan)
        if c is None:
            ihlaller.append(
                f"{alan}: eşik dosyasında var ama ölçümde YOK "
                f"(alan kaldırıldı mı?)")
            continue
        f1 = c.f1()
        if f1 < float(asgari) - tol:
            ihlaller.append(
                f"{alan}: F1 {f1:.3f} < eşik {float(asgari):.3f} "
                f"(tolerans {tol})")

    for alan, asgari in sorted(esikler.get("alanlar_kalem", {}).items()):
        if kalem_table is None:
            ihlaller.append(
                f"{alan}: `alanlar_kalem` eşiği var ama kalem tablosu "
                f"verilmedi (çağrı yeri güncellenmeli)")
            continue
        c = kalem_table.get(alan)
        if c is None:
            ihlaller.append(
                f"{alan}: `alanlar_kalem`de var ama kalem ölçümünde YOK "
                f"(alan liste alanı olmaktan çıktı mı?)")
            continue
        f1 = c.f1()
        if f1 < float(asgari) - tol:
            ihlaller.append(
                f"{alan} (KALEM): F1 {f1:.3f} < eşik {float(asgari):.3f} "
                f"(tolerans {tol})")

    asgari_yapisal = esikler.get("mikro_yapisal")
    if asgari_yapisal is not None:
        ym = micro(yapisal_kesit(table)).f1()
        if ym < float(asgari_yapisal) - tol:
            ihlaller.append(
                f"MİKRO (yapısal): {ym:.3f} < eşik "
                f"{float(asgari_yapisal):.3f} (tolerans {tol})")

    ust = esikler.get("halusinasyon_ust_sinir")
    if ust is not None:
        oran = micro(table).hallucination_rate()
        if oran is not None and oran > float(ust) + tol:
            ihlaller.append(
                f"halüsinasyon oranı: {oran:.3f} > üst sınır "
                f"{float(ust):.3f} (tolerans {tol})")

    return ihlaller


def score_document(record: GoldRecord, preds: dict[str, Any],
                   matcher: Callable[[str, Any, Any], Any],
                   fields: Sequence[str] = tuple(EXTRACTION_FIELDS),
                   *, item_esik: float = ITEM_JACCARD_ESIK) -> DocScore:
    """Tek belgeyi puanlar — `absent_fields` dahil, karar verilmemiş alan HARİÇ.

    Karar tablosu (bkz. modül başlığı, kusur 2):

    | gold                   | tahmin     | sonuç        |
    |------------------------|------------|--------------|
    | değer var, eşleşiyor   | var        | TP           |
    | değer var, eşleşmiyor  | var        | FP + FN      |
    | değer var              | yok        | FN           |
    | "YOK" (absent_fields)  | var        | FP (uydurma) |
    | "YOK" (absent_fields)  | yok        | TN           |
    | unclear_fields         | (herhangi) | metrik dışı  |
    | karar yok              | (herhangi) | metrik dışı  |

    Yanlış değer neden FP **ve** FN: model hem olmayan bir şeyi iddia etti
    (precision cezası) hem de doğru değeri kaçırdı (recall cezası). Eski kod
    yalnız FP sayıyordu ve recall'u yapay olarak yükseltiyordu.
    """
    score = DocScore(doc_id=record.id, hard_tags=list(record.hard_tags))
    gold_values = record.fields
    absent = set(record.absent_fields)
    unclear = set(record.unclear_fields)

    for name in fields:
        counts = score.per_field.setdefault(name, Counts())
        item = score.per_field_item.setdefault(name, Counts())
        has_pred = name in preds

        if name in unclear:
            counts.unclear += 1
            item.unclear += 1
            continue

        if name in gold_values:
            if has_pred and matcher(name, preds[name], gold_values[name]):
                ikili = ItemCounts(tp=1)
                score.decisions.append((name, True))
            elif has_pred:
                ikili = ItemCounts(fp=1, fn=1)
                score.decisions.append((name, False))
            else:
                ikili = ItemCounts(fn=1)
                score.decisions.append((name, False))

            counts.tp += ikili.tp
            counts.fp += ikili.fp
            counts.fn += ikili.fn
            counts.fp_wrong += ikili.fp

            # Liste alanında kalem başına sayaç; `None` -> alan liste değil,
            # kalem tablosu ikili tablonun AYNISI olur (iki mikro-F1 böylece
            # doğrudan karşılaştırılabilir kalır).
            kalem = item_counts(name, preds.get(name), gold_values[name],
                                esik=item_esik) or ikili
            item.tp += kalem.tp
            item.fp += kalem.fp
            item.fn += kalem.fn
            # Fazladan kalem uydurma DEĞİL: gold bu alanda değer taşıyor,
            # model yanlış koşulu iddia etmiş -> `fp_wrong`.
            item.fp_wrong += kalem.fp
            continue

        if name in absent:
            if has_pred:
                counts.fp += 1
                counts.fp_hallucinated += 1
                score.decisions.append((name, False))
                # Gold "YOK" derken üretilen HER kalem ayrı bir uydurmadır.
                n = (len(preds[name]) if _liste_alani(name)
                     and isinstance(preds[name], list) else 1)
                item.fp += n
                item.fp_hallucinated += n
            else:
                counts.tn += 1
                item.tn += 1
                score.decisions.append((name, True))
            continue

        # Gold bu alan hakkında KARAR VERMEMİŞ. Tahmin varsa da yoksa da
        # metriğe girmez — bilmediğimizi lehimize sayamayız.
        counts.skipped += 1
        item.skipped += 1

    return score


def score_all(records: Sequence[GoldRecord], predictor: Predictor,
              matcher: Callable[[str, Any, Any], Any],
              *, item_esik: float = ITEM_JACCARD_ESIK) -> list[DocScore]:
    """Tüm belgeleri puanlar. Tahmin ÜRETİMİ belge başına bir kez yapılır."""
    return [score_document(r, predictor.predict(r.text), matcher,
                           item_esik=item_esik) for r in records]


# --------------------------------------------------------------------------- #
# Toplama
# --------------------------------------------------------------------------- #
def aggregate(docs: Iterable[DocScore]) -> dict[str, Counts]:
    """Belge puanlarını alan bazında toplar (İKİLİ ölçüt — manşet sayı)."""
    table: dict[str, Counts] = {}
    for doc in docs:
        for name, counts in doc.per_field.items():
            table.setdefault(name, Counts()).add(counts)
    return table


def aggregate_item(docs: Iterable[DocScore]) -> dict[str, Counts]:
    """Aynı toplama, KALEM düzeyinde ölçütle.

    Liste alanlarında kalem başına TP/FP/FN; diğer alanlarda `aggregate` ile
    birebir aynı. İki tablonun farkı yalnız `kampanya_kosullari` ve
    `hedef_kitle`den gelir.
    """
    table: dict[str, Counts] = {}
    for doc in docs:
        for name, counts in doc.per_field_item.items():
            table.setdefault(name, Counts()).add(counts)
    return table


def micro_f1_kalem_of(docs: Sequence[DocScore]) -> float:
    """Bootstrap'ın çağırdığı istatistik: belge listesi -> kalem mikro-F1."""
    return micro(aggregate_item(docs)).f1()


def micro(table: dict[str, Counts]) -> Counts:
    """Tüm alanların sayaçlarını tek karışıklık matrisine indirir."""
    total = Counts()
    for counts in table.values():
        total.add(counts)
    return total


def macro_f1(table: dict[str, Counts]) -> float:
    """Alanların F1 ORTALAMASI — yalnız gold desteği olan alanlar üzerinden.

    Süzgeç `support > 0` (gold'da en az bir DEĞER kararı olan alan). Desteksiz
    alanın recall'u tanımsızdır; onu 0 sayıp ortalamaya katmak makro-F1'i gold
    setinin kapsamına göre keyfî biçimde düşürür.

    ## Süzgecin LEHE sapan kör noktası — `macro_f1_uydurma_dahil` bunun için var

    Gold bir alanda hiç değer taşımıyor **ama model orada yalnızca uydurma
    üretiyorsa**, o alan `support == 0` olduğu için ortalamadan tamamen düşer
    ve ceza **sıfır** olur. Yani bildiğimiz bir uydurmayı lehimize saymış
    oluruz — bu modülün kendi ilkesiyle ("bilmediğimizi lehimize sayamayız")
    çelişir.

    gold.v2'de fiilen gerçekleşti: `tahsis_ucreti` desteksiz, tek çıktısı bir
    halüsinasyon. Süzgeçli makro **0,409**, alan dâhil edilseydi **0,375** —
    **+0,034 lehimize**, sessizce.

    Süzgeç KALDIRILMADI (gerekçesi hâlâ geçerli), ama artık yanında ikinci bir
    sayı raporlanıyor. İkisinin arasındaki fark, ölçümün ne kadar iyimser
    olduğunun doğrudan ölçüsüdür.
    """
    scores = [c.f1() for c in table.values() if c.support > 0]
    return sum(scores) / len(scores) if scores else 0.0


def macro_f1_uydurma_dahil(table: dict[str, Counts]) -> float:
    """Makro-F1 + yalnızca UYDURMA üreten desteksiz alanlar (F1 = 0 sayılır).

    `macro_f1`'in kör noktasını kapatır: gold'da desteği olmayan ama model
    tarafından doldurulan alan cezasız kalmasın. Hiç dokunulmamış desteksiz
    alanlar (ne gold ne model) yine dışarıda — onlar hakkında bilgi yok ve
    onları 0 saymak gold kapsamını cezalandırırdı.
    """
    scores = [c.f1() for c in table.values()
              if c.support > 0 or c.fp_hallucinated > 0]
    return sum(scores) / len(scores) if scores else 0.0


def micro_f1_of(docs: Sequence[DocScore]) -> float:
    """Bootstrap'ın çağırdığı istatistik: belge listesi -> mikro-F1."""
    return micro(aggregate(docs)).f1()


def macro_f1_of(docs: Sequence[DocScore]) -> float:
    """Bootstrap'ın çağırdığı istatistik: belge listesi -> makro-F1."""
    return macro_f1(aggregate(docs))


# --------------------------------------------------------------------------- #
# Alt kümeler
# --------------------------------------------------------------------------- #
def select_split(records: Sequence[GoldRecord], split: str) -> list[GoldRecord]:
    """`all` | `hard` | `easy` alt kümesini seçer."""
    if split == "all":
        return list(records)
    if split == "hard":
        return [r for r in records if r.hard_tags]
    if split == "easy":
        return [r for r in records if not r.hard_tags]
    raise ValueError(f"bilinmeyen split {split!r}. Seçenekler: {', '.join(SPLITS)}")


def by_hard_tag(docs: Sequence[DocScore]) -> dict[str, dict[str, Counts]]:
    """Zor-vaka ETİKETİ başına ayrı tablo.

    Tek bir `hard: bool` bayrağı "hibrit NEREDE kazandı" sorusunu
    cevaplayamıyordu; `gold_schema.HARD_TAGS` altı kategori tanımlar ve bir
    belge birden çok kategoride olabilir (çok etiketli), o yüzden bu tablolar
    ÖRTÜŞÜR ve toplamları belge sayısını aşabilir.
    """
    out: dict[str, dict[str, Counts]] = {}
    for doc in docs:
        for tag in doc.hard_tags:
            table = out.setdefault(tag, {})
            for name, counts in doc.per_field.items():
                table.setdefault(name, Counts()).add(counts)
    return out


# --------------------------------------------------------------------------- #
# Değerlendirme (tek eşleştirici)
# --------------------------------------------------------------------------- #
@dataclass
class MatcherResult:
    """Bir eşleştiriciyle üretilmiş tüm metrikler."""

    matcher: str
    docs: list[DocScore]
    table: dict[str, Counts]
    micro: Counts
    macro_f1: float
    hard_table: dict[str, Counts]
    hard_docs: int
    per_tag: dict[str, dict[str, Counts]]
    ci_micro: Any = None
    ci_macro: Any = None

    @property
    def item_table(self) -> dict[str, Counts]:
        """KALEM düzeyinde alan tablosu (liste alanları kalem kalem sayılır)."""
        return aggregate_item(self.docs)

    def as_dict(self) -> dict:
        item_table = self.item_table
        data: dict[str, Any] = {
            "matcher": self.matcher,
            "documents": len(self.docs),
            "hard_documents": self.hard_docs,
            "micro": self.micro.as_dict(),
            "macro_f1": self.macro_f1,
            # KALEM düzeyi ölçüt — ikili ölçütün YANINDA durur, yerine geçmez.
            # Fark yalnız liste alanlarından gelir ve bir ÖLÇÜM düzelmesidir,
            # sistem düzelmesi değildir (bkz. `eval/matchers.py::item_counts`).
            "micro_f1_kalem": micro(item_table).f1(),
            "macro_f1_kalem": macro_f1(item_table),
            "kalem_esik_jaccard": ITEM_JACCARD_ESIK,
            "per_field_kalem": {k: v.as_dict()
                                for k, v in sorted(item_table.items())
                                if _liste_alani(k)},
            # Süzgecin LEHE sapan kör noktasının ölçüsü — bkz. `macro_f1`
            # docstring'i. İkisi arasındaki fark, makro sayının ne kadar
            # iyimser olduğunu doğrudan verir.
            # YAPILANDIRILMIŞ kesit (11 alan, `kampanya_kosullari` hariç).
            # Rapor gövdesinde basılıyordu ama `metrics.json`'a YAZILMIYORDU;
            # oysa README'nin manşet sayılarından biri bu. Artefaktta olmayan
            # bir sayı makine tarafından denetlenemez, yani sessizce bayatlar.
            "micro_f1_yapisal": micro(yapisal_kesit(self.table)).f1(),
            "macro_f1_yapisal": macro_f1(yapisal_kesit(self.table)),
            "yapisal": micro(yapisal_kesit(self.table)).as_dict(),
            "macro_f1_uydurma_dahil": macro_f1_uydurma_dahil(self.table),
            "macro_support_fields": sum(1 for c in self.table.values()
                                        if c.support > 0),
            "macro_uydurma_only_fields": sum(
                1 for c in self.table.values()
                if c.support == 0 and c.fp_hallucinated > 0),
            "per_field": {k: v.as_dict() for k, v in sorted(self.table.items())},
        }
        if self.hard_table:
            data["hard"] = {
                "micro": micro(self.hard_table).as_dict(),
                "macro_f1": macro_f1(self.hard_table),
                "per_field": {k: v.as_dict()
                              for k, v in sorted(self.hard_table.items())},
            }
        if self.per_tag:
            data["per_hard_tag"] = {
                tag: {"micro": micro(t).as_dict(), "macro_f1": macro_f1(t)}
                for tag, t in sorted(self.per_tag.items())
            }
        if self.ci_micro is not None:
            data["ci_micro_f1"] = self.ci_micro.as_dict()
        if self.ci_macro is not None:
            data["ci_macro_f1"] = self.ci_macro.as_dict()
        return data


def evaluate(records: Sequence[GoldRecord], predictor: Predictor,
             matcher_name: str, *,
             bootstrap: bool = True,
             n_resamples: int = DEFAULT_RESAMPLES,
             seed: int = DEFAULT_SEED,
             item_esik: float = ITEM_JACCARD_ESIK) -> MatcherResult:
    """Tek konfig + tek eşleştirici için tüm metrikleri üretir."""
    matcher = get_matcher(matcher_name)
    docs = score_all(records, predictor, matcher, item_esik=item_esik)
    table = aggregate(docs)
    hard_docs = [d for d in docs if d.is_hard]

    result = MatcherResult(
        matcher=matcher_name,
        docs=docs,
        table=table,
        micro=micro(table),
        macro_f1=macro_f1(table),
        hard_table=aggregate(hard_docs) if hard_docs else {},
        hard_docs=len(hard_docs),
        per_tag=by_hard_tag(docs),
    )

    if bootstrap and docs:
        result.ci_micro = bootstrap_ci(docs, micro_f1_of,
                                       n_resamples=n_resamples, seed=seed)
        result.ci_macro = bootstrap_ci(docs, macro_f1_of,
                                       n_resamples=n_resamples, seed=seed)
    return result


# --------------------------------------------------------------------------- #
# Çıktı biçimlendirme
# --------------------------------------------------------------------------- #
def format_table(title: str, table: dict[str, Counts],
                 item_table: dict[str, Counts] | None = None) -> str:
    """Konsol tablosu — alan satırları + MİKRO + MAKRO (+ varsa KALEM)."""
    lines = [f"=== {title} ===",
             (f"{'alan':<22}{'P':>7}{'R':>7}{'F1':>7}{'TP':>5}{'FP':>5}"
              f"{'FN':>5}{'TN':>5}{'UYD':>5}{'ATL':>5}")]
    for name, c in sorted(table.items()):
        lines.append(
            f"{name:<22}{c.precision():>7.3f}{c.recall():>7.3f}{c.f1():>7.3f}"
            f"{c.tp:>5}{c.fp:>5}{c.fn:>5}{c.tn:>5}{c.fp_hallucinated:>5}"
            f"{c.skipped:>5}")
    m = micro(table)
    lines.append("-" * 73)
    lines.append(
        f"{'MİKRO':<22}{m.precision():>7.3f}{m.recall():>7.3f}{m.f1():>7.3f}"
        f"{m.tp:>5}{m.fp:>5}{m.fn:>5}{m.tn:>5}{m.fp_hallucinated:>5}"
        f"{m.skipped:>5}")
    lines.append(f"{'MAKRO (F1 ort.)':<22}{'':>7}{'':>7}{macro_f1(table):>7.3f}")

    # YAPILANDIRILMIŞ ALANLAR — serbest metin çıkarılmış kesit.
    # Gerekçe `yapisal_kesit` docstring'inde; alan gizlenmiyor, ayrı ölçülüyor.
    yapisal = yapisal_kesit(table)
    if len(yapisal) < len(table):
        ym = micro(yapisal)
        serbest = sorted(set(table) - set(yapisal))
        lines.append(
            f"{'MİKRO (yapısal)':<22}{ym.precision():>7.3f}{ym.recall():>7.3f}"
            f"{ym.f1():>7.3f}{ym.tp:>5}{ym.fp:>5}{ym.fn:>5}{ym.tn:>5}"
            f"{ym.fp_hallucinated:>5}{ym.skipped:>5}"
            f"   <- {', '.join(serbest)} HARİÇ")
        lines.append(
            f"{'MAKRO (yapısal)':<22}{'':>7}{'':>7}{macro_f1(yapisal):>7.3f}")

    dahil = macro_f1_uydurma_dahil(table)
    yalniz_uydurma = sum(1 for c in table.values()
                         if c.support == 0 and c.fp_hallucinated > 0)
    if yalniz_uydurma:
        lines.append(
            f"{'MAKRO (uydurma dahil)':<22}{'':>7}{'':>7}{dahil:>7.3f}"
            f"   <- {yalniz_uydurma} desteksiz alan YALNIZ uydurma üretti; "
            f"süzgeçli makro onları cezasız bırakıyor")

    if item_table:
        im = micro(item_table)
        lines += [
            "",
            "--- KALEM DÜZEYİ ÖLÇÜT (liste alanları kalem kalem sayılır) ---",
            "Bu bir ÖLÇÜM değişikliğidir, sistem değişikliği DEĞİL. Yukarıdaki",
            f"ikili ölçüt manşet sayıdır; aşağıdaki yanında durur. Eşik: "
            f"jeton-Jaccard >= {ITEM_JACCARD_ESIK} (önceden ilan edildi).",
        ]
        for name, c in sorted(item_table.items()):
            if not _liste_alani(name):
                continue
            ikili = table.get(name, Counts())
            lines.append(
                f"{name:<22}{c.precision():>7.3f}{c.recall():>7.3f}{c.f1():>7.3f}"
                f"{c.tp:>5}{c.fp:>5}{c.fn:>5}{c.tn:>5}{c.fp_hallucinated:>5}"
                f"{'':>5}   <- ikili F1 {ikili.f1():.3f}")
        lines.append(
            f"{'MİKRO (kalem)':<22}{im.precision():>7.3f}{im.recall():>7.3f}"
            f"{im.f1():>7.3f}{im.tp:>5}{im.fp:>5}{im.fn:>5}{im.tn:>5}"
            f"{im.fp_hallucinated:>5}")
        lines.append(
            f"{'MAKRO (kalem)':<22}{'':>7}{'':>7}{macro_f1(item_table):>7.3f}")
    return "\n".join(lines)


def _rate_str(rate: float | None) -> str:
    return "ölçülemedi (gold'da absent kararı yok)" if rate is None else f"{rate:.3f}"


def format_result(result: MatcherResult, predictor: Predictor) -> str:
    """Bir eşleştiricinin tam konsol çıktısı."""
    parts = [format_table(
        f"{predictor.name.upper()} / {result.matcher} — TÜM VAKALAR",
        result.table, result.item_table)]

    m = result.micro
    # Üç hata sınıfı AYRI raporlanır (mentör talebi). Paydaları da ayrıdır:
    # çıkarım hatasının paydası "gold'da değer var" kararları, halüsinasyonun
    # paydası "gold'da YOK" kararlarıdır. Aynı paydaya bölünürlerse
    # karşılaştırılamaz hale gelirler.
    parts.append("\n=== HATA SINIFLARI ===")
    parts.append(
        f"çıkarım hatası (bilgi metinde VAR, doğru alınamadı): "
        f"{_rate_str(m.extraction_failure_rate())}  [{m.fn}/{m.support}]")
    parts.append(
        f"    ├─ kaçırma        (hiç değer üretilmedi) : {m.kacirma}")
    parts.append(
        f"    └─ yanlış çıkarım (yanlış yerden alındı) : {m.yanlis_cikarim}"
        f"   <- grounding hatası, halüsinasyon DEĞİL")
    parts.append(
        f"halüsinasyon (bilgi metinde YOK, değer uyduruldu): "
        f"{_rate_str(m.hallucination_rate())}"
        f"  [{m.fp_hallucinated}/{m.absent_decisions}]")
    if m.skipped:
        parts.append(
            f"metrik dışı bırakılan (gold karar vermemiş) alan-kararı: {m.skipped}"
            f"  — bilinmeyen lehimize sayılmadı")
    if m.unclear:
        parts.append(f"anotatör 'belirsiz' dedi, metrik dışı: {m.unclear}")

    if result.ci_micro is not None:
        parts.append(f"\nmikro-F1 %95 GA: {result.ci_micro.fmt()}  "
                     f"(belge düzeyi bootstrap, n={result.ci_micro.n_units} belge, "
                     f"{result.ci_micro.n_resamples} örnek, seed="
                     f"{result.ci_micro.seed})")
        parts.append(f"makro-F1 %95 GA: {result.ci_macro.fmt()}")

    if result.hard_table:
        parts.append("\n" + format_table(
            f"{predictor.name.upper()} / {result.matcher} — ZOR VAKALAR "
            f"({result.hard_docs} belge)", result.hard_table))

    if result.per_tag:
        parts.append("\n=== ZOR-VAKA ETİKETİ KIRILIMI (etiketler ÖRTÜŞÜR) ===")
        parts.append(f"{'etiket':<18}{'mikro-F1':>10}{'makro-F1':>10}{'TP':>6}"
                     f"{'FP':>6}{'FN':>6}")
        for tag, table in sorted(result.per_tag.items()):
            mm = micro(table)
            parts.append(f"{tag:<18}{mm.f1():>10.3f}{macro_f1(table):>10.3f}"
                         f"{mm.tp:>6}{mm.fp:>6}{mm.fn:>6}")
    return "\n".join(parts)


def per_field_rows(results: list[MatcherResult], config: str) -> list[dict]:
    """`per_field.csv` satırları — Excel'de hata analizi için."""
    rows = []
    for result in results:
        for scope, table in (("all", result.table), ("hard", result.hard_table)):
            for name, c in sorted(table.items()):
                rows.append({
                    "config": config, "matcher": result.matcher, "scope": scope,
                    "field": name,
                    "precision": round(c.precision(), 4),
                    "recall": round(c.recall(), 4),
                    "f1": round(c.f1(), 4),
                    "tp": c.tp, "fp": c.fp, "fn": c.fn, "tn": c.tn,
                    "fp_hallucinated": c.fp_hallucinated,
                    "fp_wrong": c.fp_wrong,
                    "support": c.support,
                    "absent_decisions": c.absent_decisions,
                    "skipped_undecided": c.skipped,
                    "unclear": c.unclear,
                })
    return rows


PER_FIELD_COLUMNS = [
    "config", "matcher", "scope", "field", "precision", "recall", "f1",
    "tp", "fp", "fn", "tn", "fp_hallucinated", "fp_wrong", "support",
    "absent_decisions", "skipped_undecided", "unclear",
]


def decision_rows(results: list[MatcherResult]) -> list[dict]:
    """`decisions.csv` satırları — BELGE×ALAN düzeyinde ham karar dökümü.

    `DocScore.decisions` McNemar'ın eşleştirme birimidir ama şimdiye kadar
    diske hiç yazılmıyordu: süreç bitince veri gidiyor ve iki ayrı koşum
    sonradan eşleştirilemiyordu. Burası o boşluğu kapatır.

    `matcher` sütunu ŞART: strict ve tolerant AYRI geçişlerdir, aynı
    `(doc_id, field)` çifti iki kez görünür. Eşleştiricileri ayırmayan bir
    tüketici iki farklı kararı aynı hücreye yazar ve testi sessizce bozar.

    Sıra deterministiktir (eşleştirici → belge → alan), `bool` yerine 0/1
    yazılır: CSV'de `True/False` metnini geri okurken `bool("False") == True`
    tuzağı vardır.
    """
    return [
        {"matcher": result.matcher, "doc_id": doc.doc_id, "field": name,
         "correct": int(ok)}
        for result in results
        for doc in result.docs
        for name, ok in doc.decisions
    ]


def kalem_bolumu(result: MatcherResult, item_esik: float,
                 duyarlilik: dict[float, dict[str, Counts]] | None = None
                 ) -> list[str]:
    """Serbest metin alanları için KALEM düzeyi ölçüt bölümü.

    Rapor gövdesi «alan gizlenmiyor, aşağıda kendi bölümünde kalem düzeyi
    ölçütle raporlanıyor» diye söz veriyordu; o bölüm 2026-08-15'e kadar
    **basılmıyordu**. Vaadi tutmayan bir dürüstlük iddiası, iddianın kendisini
    çürütür — bu yüzden bölüm koşulsuz basılır.

    İki sayı YAN YANA durur ve manşet DEĞİŞMEZ: ikili ölçüt manşettir, kalem
    düzeyi ölçüt ikinci sayıdır. Eşiği sayıya bakarak seçmek yasaktır; eşik
    (`ITEM_JACCARD_ESIK`) anotasyondan önce ilan edilmiştir ve duyarlılığı
    burada açıkça yayımlanır.
    """
    liste_alanlari = sorted(a for a in result.table if _serbest_metin_alani(a))
    if not liste_alanlari:
        return []

    ikili, kalem = result.table, result.item_table
    out = [
        "### Kalem düzeyi ölçüt (serbest metin alanları)", "",
        (f"Aşağıdaki alanlar cümle listesi döndürür. İkili ölçüt bir alanı "
         f"**ya tamamen doğru ya tamamen yanlış** sayar: beş koşuldan dördü "
         f"doğru çıkarılsa bile TP=0. Kalem düzeyi ölçüt her koşulu ayrı sayar "
         f"(jeton-Jaccard ≥ {item_esik:.2f}, 1-1 açgözlü eşleştirme)."), "",
        ("**Manşet mikro-F1 bu tablodan ETKİLENMEZ.** İkili ölçüt manşet olarak "
         "kalır; buradaki sayı onun yerine geçmez, yanında durur."), "",
        report_mod.md_table(
            ["alan", "ölçüt", "P", "R", "F1", "TP", "FP", "FN"],
            [satir
             for ad in liste_alanlari
             for satir in (
                 [f"`{ad}`", "ikili",
                  f"{ikili[ad].precision():.3f}", f"{ikili[ad].recall():.3f}",
                  f"{ikili[ad].f1():.3f}", ikili[ad].tp, ikili[ad].fp,
                  ikili[ad].fn],
                 ["", "kalem",
                  f"{kalem[ad].precision():.3f}", f"{kalem[ad].recall():.3f}",
                  f"{kalem[ad].f1():.3f}", kalem[ad].tp, kalem[ad].fp,
                  kalem[ad].fn],
             )]),
        "",
        (f"Tüm alanlarda mikro-F1: ikili **{micro(ikili).f1():.3f}** · "
         f"kalem **{micro(kalem).f1():.3f}**."), "",
    ]

    if duyarlilik:
        out += [
            "#### Eşik duyarlılığı", "",
            ("Eşik sayıya bakılarak seçilmedi. Aşağıdaki tablo, seçilen eşiğin "
             "sonucu ne kadar taşıdığını gösterir; taşıyorsa bunu okuyucu "
             "bilmelidir."), "",
            report_mod.md_table(
                ["jaccard eşiği", "kalem mikro-F1", "TP", "FP", "FN"],
                [[f"{e:.2f}{' ← ilan edilen' if abs(e - item_esik) < 1e-9 else ''}",
                  f"{micro(t).f1():.3f}", micro(t).tp, micro(t).fp, micro(t).fn]
                 for e, t in sorted(duyarlilik.items())]),
            "",
        ]
        f1ler = {round(micro(t).f1(), 6) for t in duyarlilik.values()}
        if len(f1ler) == 1 and len(duyarlilik) > 1:
            out += [
                ("> **Sonuç eşikten bağımsız çıktı.** Denenen eşiklerin "
                 "hepsinde aynı sayı üretildi; yani bu korpusta kalemler ya "
                 "neredeyse birebir örtüşüyor ya hiç örtüşmüyor, arada sınır "
                 "vaka yok. Eşiğin sonucu taşımadığını söylemek, taşıdığını "
                 "söylemek kadar raporlanmaya değerdir."),
                "",
            ]
    return out


def markdown_report(results: list[MatcherResult], predictor: Predictor,
                    env: report_mod.EnvInfo,
                    *, item_esik: float = ITEM_JACCARD_ESIK,
                    kalem_duyarlilik: dict[str, dict[float, dict[str, Counts]]]
                    | None = None) -> str:
    """`report.md` gövdesi — jüri ve ekip için insan-okur rapor."""
    out = [f"# Değerlendirme raporu — konfig `{predictor.name}`", "",
           predictor.description, "",
           "## Künye (tekrar-üretim)", "", report_mod.md_env_block(env), ""]

    out += [
        "## Metrik tanımları", "",
        "- **TP**: gold'da değer var, tahmin eşleşti.",
        ("- **FP**: tahmin var ama yanlış (`fp_wrong`) ya da gold \"YOK\" diyor "
         "(`fp_hallucinated`)."),
        "- **FN**: gold'da değer var, tahmin yok ya da yanlış.",
        "- **TN**: gold \"YOK\" diyor, model de üretmedi (doğru çekimserlik).",
        ("- **ATL (atlanan)**: gold bu alan hakkında KARAR VERMEMİŞ — metriğe "
         "girmez. Bilmediğimizi lehimize saymıyoruz."),
        ("- **halüsinasyon oranı** = `fp_hallucinated / (tn + fp_hallucinated)`; "
         "gold'da hiç `absent_fields` kararı yoksa TANIMSIZDIR (0,0 yazmak yalan "
         "olurdu)."),
        "",
        "### Hata sınıfları — üçü AYRI ölçülür", "",
        ("Aynı sayıya bakıp \"model kötü\" demek yerine hangi hatanın "
         "yapıldığını ayırıyoruz; üçü farklı düzeltme gerektiriyor:"),
        "",
        ("- **kaçırma** (`fn - fp_wrong`): bilgi metinde VAR, model hiçbir "
         "değer üretmedi. Kapsama sorunu — regex ya da prompt eksik."),
        ("- **yanlış çıkarım** (`fp_wrong`): bilgi metinde VAR, model YANLIŞ "
         "yerden aldı. *Grounding* sorunudur, halüsinasyon DEĞİLDİR — kanun "
         "maddesindeki \"1 yıl\"ı vade sanmak bu sınıfa girer."),
        ("- **halüsinasyon** (`fp_hallucinated`): bilgi metinde YOK, model "
         "uydurdu. En tehlikelisi; zemin sorunu."),
        "",
        ("**Paydalar ayrıdır:** çıkarım hatası oranının paydası gold'da DEĞER "
         "olan kararlar (`support`), halüsinasyon oranının paydası gold'da "
         "\"YOK\" denen kararlardır (`absent_decisions`). Aynı paydaya "
         "bölünürlerse karşılaştırılamaz hale gelirler."),
        ("- **makro-F1**: alanların F1 ortalaması (yalnız gold desteği olan "
         "alanlar). Mikro seyrek alanları gizler, makro gizlemez."),
        ("- **%95 GA**: belge düzeyinde küme bootstrap. Aynı belgeden çıkan 12 "
         "alan bağımsız değildir; alan düzeyinde örneklemek GA'yı yapay olarak "
         "daraltır (bkz. `eval/stats.py`)."),
        "",
    ]

    for result in results:
        m = result.micro
        out += [f"## Eşleştirici: `{result.matcher}`", ""]
        rows = [[
            "TÜMÜ", f"{m.precision():.3f}", f"{m.recall():.3f}",
            f"{m.f1():.3f}", f"{result.macro_f1:.3f}",
            result.ci_micro.fmt() if result.ci_micro else "—",
            _rate_str(m.hallucination_rate()),
        ]]
        if result.hard_table:
            hm = micro(result.hard_table)
            rows.append([
                f"ZOR ({result.hard_docs} belge)", f"{hm.precision():.3f}",
                f"{hm.recall():.3f}", f"{hm.f1():.3f}",
                f"{macro_f1(result.hard_table):.3f}", "—",
                _rate_str(hm.hallucination_rate()),
            ])
        # YAPILANDIRILMIŞ kesit — serbest metin alanı çıkarılmış.
        # G2.2 (README vitrin tablosu) ilan edilebilir sayı olarak BUNU
        # kullanır; gerekçe `yapisal_kesit` docstring'inde.
        yapisal = yapisal_kesit(result.table)
        if len(yapisal) < len(result.table):
            ym = micro(yapisal)
            rows.append([
                f"YAPILANDIRILMIŞ ({len(yapisal)} alan)",
                f"{ym.precision():.3f}", f"{ym.recall():.3f}",
                f"{ym.f1():.3f}", f"{macro_f1(yapisal):.3f}", "—",
                _rate_str(ym.hallucination_rate()),
            ])
            if result.hard_table:
                hy = yapisal_kesit(result.hard_table)
                hym = micro(hy)
                rows.append([
                    f"ZOR + YAPILANDIRILMIŞ ({result.hard_docs} belge)",
                    f"{hym.precision():.3f}", f"{hym.recall():.3f}",
                    f"{hym.f1():.3f}", f"{macro_f1(hy):.3f}", "—",
                    _rate_str(hym.hallucination_rate()),
                ])

        out += [report_mod.md_table(
            ["alt küme", "P (mikro)", "R (mikro)", "F1 (mikro)", "F1 (makro)",
             "mikro-F1 %95 GA", "halüsinasyon"], rows), ""]

        if len(yapisal) < len(result.table):
            serbest = sorted(set(result.table) - set(yapisal))
            out += [
                f"> **«YAPILANDIRILMIŞ» satırı neyi dışarıda bırakıyor:** "
                f"{', '.join(f'`{a}`' for a in serbest)}. Bu alan serbest "
                "cümle listesi döndürür; span/jeton eşleşmesiyle F1 ölçmek "
                "metodolojik olarak yanlıştır — aynı koşulu farklı sözcüklerle "
                "yazan iki anotatör bile birbirini «yanlış» bulurdu. Alan "
                "GİZLENMİYOR: aşağıda kendi bölümünde, kalem düzeyi ölçütle "
                "raporlanıyor ve iki sayı yan yana duruyor.",
                "",
            ]

        out += ["### Alan bazında", "",
                report_mod.md_table(
                    ["alan", "P", "R", "F1", "TP", "FP", "FN", "TN",
                     "uydurma", "atlanan"],
                    [[name, f"{c.precision():.3f}", f"{c.recall():.3f}",
                      f"{c.f1():.3f}", c.tp, c.fp, c.fn, c.tn,
                      c.fp_hallucinated, c.skipped]
                     for name, c in sorted(result.table.items())]),
                ""]

        out += kalem_bolumu(
            result, item_esik,
            (kalem_duyarlilik or {}).get(result.matcher))

        if result.per_tag:
            out += ["### Zor-vaka etiketi kırılımı", "",
                    "Etiketler çok değerlidir; tablolar ÖRTÜŞÜR.", "",
                    report_mod.md_table(
                        ["etiket", "mikro-F1", "makro-F1", "TP", "FP", "FN"],
                        [[tag, f"{micro(t).f1():.3f}", f"{macro_f1(t):.3f}",
                          micro(t).tp, micro(t).fp, micro(t).fn]
                         for tag, t in sorted(result.per_tag.items())]),
                    ""]
    return "\n".join(out)


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def build_arg_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        description="Gold set üzerinde P/R/F1 + makro + bootstrap GA; diske yazar.")
    ap.add_argument("--gold", required=True, help="gold JSON dosyası")
    ap.add_argument("--config", default="kural", choices=list(CONFIG_NAMES),
                    help="tahmin konfigürasyonu. 'hibrit' teslim edilen sistemdir "
                         "ama LLM gerektirir; varsayılan 'kural' offline çalışır.")
    ap.add_argument("--matcher", default="both",
                    choices=["strict", "tolerant", "both"],
                    help="eşleştirici (varsayılan: both — ikisi de raporlanır)")
    ap.add_argument("--split", default="all", choices=list(SPLITS),
                    help="değerlendirilecek alt küme (varsayılan: all)")
    ap.add_argument("--kalem-esik", type=float, default=ITEM_JACCARD_ESIK,
                    help=("liste alanlarında kalem eşleşmesi için jeton-Jaccard "
                          f"eşiği (varsayılan: {ITEM_JACCARD_ESIK}). ÖNCEDEN "
                          "İLAN EDİLMİŞTİR; sonuca bakıp değiştirmek yasaktır. "
                          "Duyarlılık analizi için kullanın."))
    ap.add_argument("--kalem-duyarlilik-yok", action="store_true",
                    help=("kalem eşiği duyarlılık tablosunu üretme (0,6/0,8'de "
                          "yeniden puanlama atlanır — tahmin üretimi pahalıysa)"))
    ap.add_argument("--out-dir", default=report_mod.DEFAULT_OUT_DIR,
                    help=f"rapor kök dizini (varsayılan: {report_mod.DEFAULT_OUT_DIR})")
    ap.add_argument("--no-write", action="store_true",
                    help="diske yazma (yalnız konsol)")
    ap.add_argument("--esikler", metavar="JSON",
                    help="regresyon kapısı: alan başına asgari F1 dosyası "
                         "(bkz. eval/esikler.json). İhlal varsa çıkış kodu 1.")
    ap.add_argument("--seed", type=int, default=DEFAULT_SEED,
                    help=f"bootstrap çekirdeği (varsayılan: {DEFAULT_SEED})")
    ap.add_argument("--resamples", type=int, default=DEFAULT_RESAMPLES,
                    help=f"bootstrap örnek sayısı (varsayılan: {DEFAULT_RESAMPLES})")
    ap.add_argument("--no-bootstrap", action="store_true",
                    help="güven aralığı hesaplamayı atla (hızlı koşum)")
    ap.add_argument("--verify-threshold", type=float,
                    default=DEFAULT_VERIFY_THRESHOLD,
                    help="hibrit-verify konfigi için güven eşiği")
    ap.add_argument("--strict-gold", action="store_true",
                    help="gold doğrulama hatası varsa çık (varsayılan: uyar, devam et)")
    return ap


def main(argv: list[str] | None = None) -> int:
    """Çıkış kodu: 0 başarılı, 2 kullanım/veri hatası, 3 konfig ölçülemedi."""
    args = build_arg_parser().parse_args(argv)

    gold_path = Path(args.gold)
    if not gold_path.is_file():
        print(f"HATA: gold dosyası bulunamadı: {gold_path}", file=sys.stderr)
        return 2

    records = load_gold(gold_path)
    if not records:
        print(f"HATA: {gold_path} içinde hiç kayıt yok. Boş gold ile üretilen bir "
              f"metrik yanıltıcıdır; çıkılıyor.", file=sys.stderr)
        return 2

    errors = validate_gold(records)
    if errors:
        head = "\n".join(f"  - {e}" for e in errors[:10])
        more = f"\n  ... (+{len(errors) - 10} hata daha)" if len(errors) > 10 else ""
        print(f"UYARI: gold doğrulama {len(errors)} hata buldu:\n{head}{more}",
              file=sys.stderr)
        if args.strict_gold:
            return 2

    selected = select_split(records, args.split)
    if not selected:
        print(f"HATA: '{args.split}' alt kümesi boş ({len(records)} kayıt içinde). "
              f"Ölçülecek bir şey yok.", file=sys.stderr)
        return 2

    predictor = build_predictor(args.config, verify_threshold=args.verify_threshold)
    if not predictor.available:
        print(f"HATA: konfig '{predictor.name}' ölçülemedi.\n"
              f"  {predictor.unavailable_reason}", file=sys.stderr)
        return 3

    matcher_names = resolve_matchers(args.matcher)
    results = [
        evaluate(selected, predictor, name,
                 bootstrap=not args.no_bootstrap,
                 n_resamples=args.resamples, seed=args.seed,
                 item_esik=args.kalem_esik)
        for name in matcher_names
    ]

    # Kalem düzeyi eşiğin duyarlılığı. `matchers.ITEM_JACCARD_ESIK` yorumu
    # "duyarlılık 0,6 ve 0,8'de ayrıca yayımlanır" diyordu; yayımlanmıyordu.
    # Yeniden puanlama tahmin üretimini tekrarlar (kural kolunda ucuz), bu
    # yüzden `--kalem-duyarlilik-yok` ile kapatılabilir.
    kalem_duyarlilik: dict[str, dict[float, dict[str, Counts]]] = {}
    if not args.kalem_duyarlilik_yok:
        for name in matcher_names:
            matcher = get_matcher(name)
            kalem_duyarlilik[name] = {
                esik: aggregate_item(
                    score_all(selected, predictor, matcher, item_esik=esik))
                for esik in sorted({0.6, args.kalem_esik, 0.8})
            }

    print(f"\nkonfig : {predictor.name} — {predictor.description}")
    print(f"gold   : {gold_path} ({len(records)} kayıt, alt küme "
          f"'{args.split}' -> {len(selected)} belge)")
    for result in results:
        print("\n" + format_result(result, predictor))

    # REGRESYON KAPISI — rapor yazılmadan ÖNCE değerlendirilir ama çıkış
    # koduna en sonda dönüşür: kapı kapansa bile rapor diske yazılmalı,
    # yoksa CI kırmızı olur ve NEDEN kırmızı olduğunun kanıtı kaybolur.
    kapi_ihlalleri: list[str] = []
    if args.esikler:
        esik_yolu = Path(args.esikler)
        if not esik_yolu.is_file():
            print(f"HATA: eşik dosyası bulunamadı: {esik_yolu}", file=sys.stderr)
            return 2
        esikler = json.loads(esik_yolu.read_text(encoding="utf-8"))
        # Kapı, eşik dosyasında ilan edilen eşleştirici üzerinden ölçülür.
        # Bir başkasının sayısıyla karşılaştırmak sessizce yanlış olurdu.
        istenen = esikler.get("matcher", "strict")
        hedef = next((r for r in results if r.matcher == istenen), None)
        if hedef is None:
            print(f"HATA: eşik dosyası '{istenen}' eşleştiricisini istiyor ama "
                  f"bu koşumda yok ({', '.join(matcher_names)}). "
                  f"`--matcher {istenen}` ile koşun.", file=sys.stderr)
            return 2
        kapi_ihlalleri = esik_ihlalleri(hedef.table, esikler,
                                        kalem_table=hedef.item_table)
        print(f"\n=== REGRESYON KAPISI ({esik_yolu}) ===")
        if kapi_ihlalleri:
            print(f"KAPALI — {len(kapi_ihlalleri)} gerileme:")
            for i in kapi_ihlalleri:
                print(f"  ✗ {i}")
            print("\nGerileme gerçekse düzeltin. Gold değiştiği için "
                  "beklenen bir düşüşse eval/esikler.json'ı BİLEREK güncelleyin "
                  "ve gerekçeyi commit mesajına yazın.")
        else:
            # Kapı, DENETLEDİĞİ şeyi sayar. Eşik dosyasında tanımlı olmayan
            # bir ölçütü "korunuyor" diye yazmak, denetlenmeyen bir şeyi
            # denetlenmiş gibi göstermektir — bu projenin kapatmaya çalıştığı
            # hata sınıfının ta kendisi. (Ölçüldü 2026-08-15: round1 eşik
            # dosyasında halüsinasyon tavanı YOK, mesaj yine de "korunuyor"
            # diyordu.)
            korunan = [f"{len(esikler.get('alanlar', {}))} alan"]
            if "mikro_yapisal" in esikler:
                korunan.append("yapısal mikro-F1")
            if "halusinasyon_ust_sinir" in esikler:
                korunan.append("halüsinasyon üst sınırı")
            print(f"AÇIK — {' + '.join(korunan)} korunuyor.")
            if "halusinasyon_ust_sinir" not in esikler:
                print("  NOT: bu eşik dosyası halüsinasyon tavanı TANIMLAMIYOR; "
                      "kapı onu denetlemedi.")

    if args.no_write:
        print("\n(--no-write verildi: diske yazılmadı)")
        return 1 if kapi_ihlalleri else 0

    env = report_mod.build_env(
        config=predictor.name, gold_path=str(gold_path),
        gold_records=len(selected), matchers=matcher_names,
        seed=args.seed, split=args.split,
        llm=predictor.llm_summary,
        extra={"gold_total_records": len(records),
               "gold_validation_errors": len(errors),
               "bootstrap_resamples": (0 if args.no_bootstrap else args.resamples)})

    metrics = {
        "config": predictor.name,
        "config_description": predictor.description,
        "split": args.split,
        "documents": len(selected),
        "gold_total_records": len(records),
        "fields_evaluated": list(EXTRACTION_FIELDS),
        "hard_tags_known": list(ALL_HARD_TAGS),
        "results": [r.as_dict() for r in results],
    }

    run_dir = report_mod.make_run_dir(args.out_dir)
    written = report_mod.write_report(
        run_dir, metrics=metrics, env=env,
        markdown=markdown_report(results, predictor, env,
                                 item_esik=args.kalem_esik,
                                 kalem_duyarlilik=kalem_duyarlilik),
        per_field_rows=per_field_rows(results, predictor.name),
        per_field_columns=PER_FIELD_COLUMNS,
        decision_rows=decision_rows(results),
        decision_columns=report_mod.DECISION_COLUMNS)
    print("\n" + written.summary())
    # Rapor yazıldıktan SONRA kapıyı çıkış koduna dönüştür: CI kırmızıysa
    # nedeninin kanıtı (per_field.csv, decisions.csv) diskte durmalı.
    return 1 if kapi_ihlalleri else 0


if __name__ == "__main__":
    raise SystemExit(main())
