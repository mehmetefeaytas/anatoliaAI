"""Değişmez (invariant) denetleyicisi — ETİKETSİZ veride hata avlar.

İlgili: ../../decisions/zor-anlama-vakalari-merkezi.md
        docs/10-degerlendirme.md

## Neden bu modül var

Gold set kritik yoldadır ve yavaştır (anotasyon insan işi). Ama scrape edilen
belgelerin çoğu anote edilmeyecek. Bu modül **etiket olmadan** hata bulur:
girdinin anlamını değiştirmeyen bir dönüşüm çıktıyı değiştiriyorsa, ortada
kesinlikle bir hata vardır — doğru cevabı bilmeye gerek yok.

Bugüne kadar elle bulunan beş hatanın **dördü** bu değişmezlerle otomatik
yakalanırdı:

| Değişmez | Yakalayacağı hata |
|---|---|
| P2 ortografik değişmezlik | H1: `'TAŞIT'.lower()` → sınıf kaybı, masraf işaret ters |
| P3 alakasız ekleme | "31 Aralık"tan uydurulan hayali 31 TL ücret |
| P4 cümle sırası | H2: çelişki tespitinin yazım sırasına bağlı olması |
| P1 span bütünlüğü | vurgulanan yerin raporlanan değerle uyuşmaması |

Her denetim bir `Violation` listesi döndürür; boş liste = geçti.
`eval/reports/<ts>/violations.jsonl` dosyasına yazılır ve hata analizinde
kullanılır.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field as dc_field
from pathlib import Path
from typing import Any, Callable, Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.comparison.contradiction import detect
from src.extraction.rules.extract import extract_all
from src.preprocessing.clean import split_sentences, tr_fold_ascii, tr_upper
from src.schemas import Campaign


@dataclass
class Violation:
    """Bir değişmezin ihlali — doğru cevabı bilmeden tespit edilen kesin hata."""

    prop: str                 # hangi değişmez
    doc_id: str
    field_name: Optional[str]
    detail: str
    before: Any = None
    after: Any = None

    def as_dict(self) -> dict:
        return {
            "prop": self.prop, "doc_id": self.doc_id,
            "field_name": self.field_name, "detail": self.detail,
            "before": _safe(self.before), "after": _safe(self.after),
        }


def _safe(v: Any) -> Any:
    """JSON'a yazılabilir hale getirir."""
    if isinstance(v, (str, int, float, bool, type(None))):
        return v
    if isinstance(v, dict):
        return {str(k): _safe(x) for k, x in v.items()}
    if isinstance(v, (list, tuple)):
        return [_safe(x) for x in v]
    return str(v)


def _values(text: str) -> dict[str, Any]:
    """Alan adı → kanonik değer sözlüğü."""
    return {f.field_name: f.canonical_value for f in extract_all(text)}


def _case_insensitive(value: Any) -> Any:
    """Serbest METİN değerlerini yazım biçiminden bağımsız hale getirir.

    `kampanya_kosullari` gibi alanlar cümle metni döndürür; büyük harfli
    varyantta doğal olarak büyük harfli çıkarlar. Bu bir hata DEĞİLDİR —
    taşınan bilgi aynıdır. Ortografik değişmezlik kontrolü bu alanlarda
    metni katlayarak karşılaştırmalı, yoksa denetleyici kendi yanlış
    pozitifini üretir.
    """
    if isinstance(value, str):
        # Sondaki noktalama BİLGİ DEĞİLDİR. Değişmez "aynı bilgi yakalandı mı"
        # diye sorar; "...saklı tutar" ile "...saklı tutar." aynı koşuldur.
        # Bu olmadan test, cümle sonu noktalamasını içerik farkı sanar.
        return tr_fold_ascii(value).rstrip(" .,;:!?")
    if isinstance(value, list):
        return [_case_insensitive(v) for v in value]
    if isinstance(value, dict):
        return {k: _case_insensitive(v) for k, v in value.items()}
    return value


# --------------------------------------------------------------------------- #
# P1 — Span bütünlüğü
# --------------------------------------------------------------------------- #
def check_span_integrity(text: str, doc_id: str = "?") -> list[Violation]:
    """Her alanın offset'i gerçekten kendi `raw_value`'sunu göstermeli.

    İhlal = dashboard'da YANLIŞ YERİ vurgularız. Açıklanabilirlik iddiası
    (yenilikçilik hedefi #1) bunun üzerine kurulu, dolayısıyla sessizce
    yanlış olması özellikle zararlıdır.
    """
    out = []
    for f in extract_all(text):
        if f.span_start is None or f.span_end is None:
            out.append(Violation("P1_span_yok", doc_id, f.field_name,
                                 "offset üretilmedi"))
        elif not f.verify_span(text):
            out.append(Violation(
                "P1_span_uyumsuz", doc_id, f.field_name,
                "offset raw_value ile uyuşmuyor",
                before=f.raw_value,
                after=text[f.span_start:f.span_end],
            ))
    return out


# --------------------------------------------------------------------------- #
# P2 — Ortografik değişmezlik
# --------------------------------------------------------------------------- #
def check_orthographic_invariance(text: str, doc_id: str = "?") -> list[Violation]:
    """Büyük/küçük harf yazımı çıkarılan DEĞERLERİ değiştirmemeli.

    Banka başlıkları ALL-CAPS'tir. `'TAŞIT'.lower()` hatası (H1) tam olarak
    burada yakalanırdı: küçük harfli metin sınıfı buluyor, büyük harfli
    bulamıyordu; "ÜCRETSİZ" ise `has_fee`'yi TERS çeviriyordu.
    """
    base = _values(text)
    out = []
    for label, variant in (("buyuk_harf", tr_upper(text)),):
        got = _values(variant)
        for name, val in base.items():
            if name not in got:
                out.append(Violation(f"P2_{label}_alan_kayboldu", doc_id, name,
                                     "varyantta alan hiç çıkmadı", before=val))
            elif _case_insensitive(got[name]) != _case_insensitive(val):
                out.append(Violation(f"P2_{label}_deger_degisti", doc_id, name,
                                     "yazım biçimi değeri değiştirdi",
                                     before=val, after=got[name]))
    return out


# --------------------------------------------------------------------------- #
# P3 — Alakasız ekleme (monotonluk)
# --------------------------------------------------------------------------- #
# Finansal bilgi İÇERMEYEN, her banka sayfasında bulunabilecek nötr cümleler.
NEUTRAL_SENTENCES = [
    "Şubelerimiz hafta içi 09:00 - 17:00 saatleri arasında hizmet vermektedir.",
    "Detaylı bilgi için müşteri hizmetlerimizi arayabilirsiniz.",
    "Mobil uygulamamızı indirerek işlemlerinizi kolayca gerçekleştirin.",
]


def check_irrelevant_insertion(text: str, doc_id: str = "?") -> list[Violation]:
    """Nötr bir cümle eklemek mevcut alan değerlerini değiştirmemeli.

    "Yıllık kart ücreti alınmaz. Kampanya 31 Aralık 2026..." metnindeki
    hayali 31 TL ücret tam olarak bu sınıf hatadır: bir alanın penceresi
    komşu cümleye taşıp oradan sayı devşiriyordu.

    Not: yeni alanların ORTAYA ÇIKMASI ihlal sayılmaz (nötr cümle yeni bilgi
    getirmemeli ama getirirse bu ayrı bir hassasiyet konusudur); burada
    yalnızca MEVCUT değerlerin bozulması aranır.
    """
    base = _values(text)
    out = []
    for i, extra in enumerate(NEUTRAL_SENTENCES):
        # AYRI bir cümle eklendiğinden emin ol. Kaynak metin noktalama ile
        # bitmiyorsa (banka sayfalarında sık: menü/başlık yığınları) düz
        # birleştirme, eklenen cümleyi son cümleye YAPIŞTIRIR. O zaman test
        # "alakasız cümle ekleme"yi değil "cümle birleştirme"yi ölçer —
        # ölçmek istediği şey bu değil.
        govde = text.rstrip()
        if govde and govde[-1] not in ".!?":
            govde += "."
        got = _values(govde + " " + extra)
        for name, val in base.items():
            # P2 ile AYNI karşılaştırma kullanılır: serbest metin alanlarında
            # yazım biçimi ve sondaki noktalama bilgi değildir.
            if (name in got
                    and _case_insensitive(got[name]) != _case_insensitive(val)):
                out.append(Violation(
                    f"P3_alakasiz_ekleme_{i}", doc_id, name,
                    "nötr cümle eklenince değer değişti",
                    before=val, after=got[name],
                ))
    return out


# --------------------------------------------------------------------------- #
# P4 — Cümle sırası değişmezliği (çelişki tespiti)
# --------------------------------------------------------------------------- #
def check_sentence_order_invariance(text: str, doc_id: str = "?") -> list[Violation]:
    """Cümleleri ters çevirmek ÇELİŞKİ tespitini değiştirmemeli.

    H2 tam olarak buydu: "masrafsız ... tahsis 500 TL" çelişkiyi yakalıyor,
    ters sırası kaçırıyordu. Not: bu değişmez yalnız çelişki KÜMESİ için
    geçerlidir — alan değerleri sıraya bağlı olabilir (ör. ilk eşleşme
    seçimi), bu yüzden burada değerler karşılaştırılmaz.
    """
    sents = split_sentences(text)
    if len(sents) < 2:
        return []
    reversed_text = " ".join(reversed(sents))

    def kinds(t: str) -> set[str]:
        return {c.kind for c in
                detect(Campaign(bank_slug="?", raw_text=t, fields=extract_all(t)))}

    a, b = kinds(text), kinds(reversed_text)
    if a != b:
        return [Violation("P4_cumle_sirasi", doc_id, None,
                          "cümle sırası çelişki sonucunu değiştirdi",
                          before=sorted(a), after=sorted(b))]
    return []


# --------------------------------------------------------------------------- #
# Toplu koşum
# --------------------------------------------------------------------------- #
ALL_CHECKS: list[Callable[[str, str], list[Violation]]] = [
    check_span_integrity,
    check_orthographic_invariance,
    check_irrelevant_insertion,
    check_sentence_order_invariance,
]


@dataclass
class PropertyReport:
    """Denetim sonucu.

    `documents_with_fields` NEDEN gerekli: "N belgede 0 ihlal" cümlesi tek
    başına yetersizdir. Çıkarıcının hiçbir alan bulamadığı bir belgede değişmez
    denetimi HİÇBİR ŞEY test etmez ve otomatik geçer — karşılaştırılacak değer
    yoktur. Boş belgeler sayıya karışırsa "0 ihlal" ifadesi bedava geçişlerle
    seyreltilir ve istatistiği kendi lehimize bozar. Gerçek kapsam:
    "N belge, bunların M'sinde en az bir alan çıktı, K ihlal".
    """

    documents: int = 0
    documents_with_fields: int = 0
    violations: list[Violation] = dc_field(default_factory=list)

    @property
    def documents_without_fields(self) -> int:
        return self.documents - self.documents_with_fields

    @property
    def passed(self) -> bool:
        return not self.violations

    @property
    def coverage(self) -> float:
        """Alan çıkan belge oranı — denetimin GERÇEKTEN test ettiği pay."""
        return self.documents_with_fields / self.documents if self.documents else 0.0

    def by_prop(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for v in self.violations:
            out[v.prop] = out.get(v.prop, 0) + 1
        return out

    def summary(self) -> str:
        head = (f"{self.documents} belge "
                f"({self.documents_with_fields} tanesinde en az bir alan çıktı; "
                f"{self.documents_without_fields} boş belgede denetim hiçbir şey "
                f"test etmiyor — kapsam {self.coverage:.1%})")
        if self.passed:
            return f"{head} — tüm değişmezler GEÇTİ (0 ihlal)"
        lines = [f"{head} — {len(self.violations)} İHLAL:"]
        for prop, n in sorted(self.by_prop().items(), key=lambda x: -x[1]):
            lines.append(f"  {n:4}  {prop}")
        return "\n".join(lines)


def run(texts: dict[str, str]) -> PropertyReport:
    """Bir korpus üzerinde tüm değişmezleri koşturur.

    Args:
        texts: doc_id → metin. Gold etiketi GEREKMEZ.
    """
    rep = PropertyReport(documents=len(texts))
    for doc_id, text in texts.items():
        if not (text or "").strip():
            continue
        # Alan çıkmayan belgede denetim bedava geçer; bunu SAYALIM ki
        # "0 ihlal" ifadesinin gerçek kapsamı görünsün (bkz. PropertyReport).
        if _values(text):
            rep.documents_with_fields += 1
        for check in ALL_CHECKS:
            rep.violations.extend(check(text, doc_id))
    return rep


# Varsayılan: YALNIZ `.txt`. Gerekçe `load_corpus` docstring'inde.
TEXT_SUFFIXES = (".txt",)
HTML_SUFFIXES = (".html", ".htm")


def load_corpus(raw_dir: str, include_html: bool = False) -> dict[str, str]:
    """`data/raw/` altındaki belgeleri okur (etiket gerekmez).

    ## Varsayılan neden yalnız `.txt` — ÇİFT SAYIM hatası

    `data/raw/` her belgeyi İKİ biçimde tutar: ham `.html` ve temizlenmiş
    `.txt` (provenance için, CLAUDE.md §14). Eski süzgeç ikisini de alıyordu ve
    849 benzersiz belge **1696 belge** olarak raporlanıyordu — sayı olduğundan
    iki kat büyük görünüyordu.

    Daha kötüsü: ham HTML `normalize_text`'ten geçince markup çorbası olur ve
    çıkarıcı orada neredeyse hiçbir alan bulamaz. Alan bulunmayan belgede
    değişmez denetimi hiçbir şey test etmez ve **otomatik geçer**. Yani ihlal
    oranımız ~847 boş kayıtla seyreltiliyordu; istatistik kendi lehimize
    bozuluyordu. Bu, projedeki diğer hatalarla aynı sınıftır: çökmez, sessizce
    yanlış rapor eder.

    `.txt` doğru varsayılandır çünkü çıkarıcının ÜRETİMDE gördüğü girdi odur.

    Args:
        raw_dir: belgelerin kök dizini.
        include_html: `True` ise ham `.html`/`.htm` de okunur. Rapor bunları
            AYRI satır olarak göstermelidir; tek sayıya karıştırmak yukarıdaki
            hatayı geri getirir.
    """
    from src.preprocessing.clean import normalize_text

    suffixes = TEXT_SUFFIXES + (HTML_SUFFIXES if include_html else ())
    out: dict[str, str] = {}
    root = Path(raw_dir)
    for p in sorted(root.rglob("*")):
        if p.is_file() and p.suffix.lower() in suffixes:
            try:
                out[str(p.relative_to(root))] = normalize_text(
                    p.read_text(encoding="utf-8", errors="replace"))
            except OSError:
                continue
    return out


def _main() -> int:
    """CLI. Çıkış kodu: 0 temiz, 1 ihlal var, 2 KORPUS OKUNAMADI.

    Çıkış kodu 2 neden eklendi: eski kod belge bulamayınca `UYARI` basıp
    **0 döndürüyordu**. Yanlış `--raw-dir` yazılmış bir CI adımı böylece
    YEŞİL veriyordu — hiçbir şey denetlenmeden "geçti" raporlanıyordu. Bu tam
    olarak bu modülün avlamak için var olduğu hata sınıfıdır (sessizce yanlış
    rapor); kendi kapımızın ona düşmesi kabul edilemez.
    """
    import argparse
    import json

    ap = argparse.ArgumentParser(
        description="Değişmez denetimi — scrape edilmiş korpusta ETİKETSİZ hata avı."
    )
    ap.add_argument("--raw-dir", default="data/raw",
                    help="belgelerin bulunduğu dizin (varsayılan: data/raw)")
    ap.add_argument("--include-html", action="store_true",
                    help="ham .html/.htm dosyalarını da dahil et. VARSAYILAN "
                         "KAPALI: data/raw her belgeyi hem .html hem .txt olarak "
                         "tutar, ikisini birden saymak belge sayısını iki katına "
                         "çıkarır ve alan çıkmayan HTML kayıtları ihlal oranını "
                         "seyreltir (bkz. load_corpus).")
    ap.add_argument("--out", default=None,
                    help="ihlalleri JSONL olarak yaz (ör. eval/reports/violations.jsonl)")
    args = ap.parse_args()

    texts = load_corpus(args.raw_dir, include_html=args.include_html)
    if not texts:
        kinds = ", ".join(TEXT_SUFFIXES + (HTML_SUFFIXES if args.include_html
                                           else ()))
        print(f"HATA: {args.raw_dir} altında hiç belge bulunamadı "
              f"(aranan uzantılar: {kinds}).\n"
              f"Denetim hiçbir şey koşturmadı; bunu 'geçti' saymak sessiz bir "
              f"yalan olurdu. --raw-dir yolunu kontrol edin.", file=sys.stderr)
        return 2

    rep = run(texts)
    print(rep.summary())
    if args.include_html:
        html = sum(1 for k in texts if Path(k).suffix.lower() in HTML_SUFFIXES)
        print(f"  (bunların {html} tanesi ham HTML — --include-html verildi; "
              f"temizlenmiş metinle AYNI belgelerin ikinci kopyasıdır, tek "
              f"sayıya karıştırmayın)")

    if rep.violations:
        print("\nİlk ihlaller:")
        for v in rep.violations[:20]:
            print(f"  [{v.prop}] {v.doc_id} / {v.field_name}")
            print(f"      önce ={v.before!r}")
            print(f"      sonra={v.after!r}")

    if args.out:
        outp = Path(args.out)
        outp.parent.mkdir(parents=True, exist_ok=True)
        with outp.open("w", encoding="utf-8") as fh:
            for v in rep.violations:
                fh.write(json.dumps(v.as_dict(), ensure_ascii=False) + "\n")
        print(f"\nYazıldı: {outp}")

    # İhlal varsa sıfırdan farklı çıkış — CI'da kapı olarak kullanılabilir.
    return 1 if rep.violations else 0


if __name__ == "__main__":
    raise SystemExit(_main())
