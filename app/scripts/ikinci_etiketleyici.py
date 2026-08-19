"""İkinci etiketleyici turu — κ (Cohen's kappa) için ÖRTÜŞME üretir.

## Neden bu betik var

`data/gold/gold.v2.json`'da 48 kaydın hiçbirinde etiketleyici örtüşmesi YOKTU
(`annotators` dağılımı M1:12, M2:12, M3:12, M4:10, M4+HAKEM-02:2). Örtüşme
olmadan Cohen's κ **hesaplanamaz** — κ tanımı gereği aynı birimi iki kez
etiketlemeyi gerektirir. CLAUDE.md §16 κ raporlanmasını istiyor ve
değerlendirmede bu eksiklik "referans güvenilirliği ölçülmemiş" biçiminde
Model Başarısı maddesinin en ağır gerekçesi oldu.

Betik 16 kayda İKİNCİ bir etiket kümesi üretir ve κ'yı ölçer.

## İkinci etiketleyici bir LLM'dir — bu SAKLANMAZ

İkinci tur insan değil yerel bir LLM'dir (`LLM_BACKEND` neyi gösteriyorsa).
Rapor bunu başlıkta yazar. İnsan çift-anotasyonun yerine geçtiği iddia
EDİLMEZ; ölçülen şey "bağımsız bir ikinci etiketleyicinin kararlarıyla uyum"
dur ve bu κ'nın gerçek tanımına uyar (iki bağımsız yargıç, aynı birimler).

LLM gold'u GÖRMEZ: yalnızca belge metnini ve alan şemasını alır. Kural motoru
çıktısını da görmez — yani bu tur, kural motorunun kendi kararlarını
onaylamasından farklıdır.

## Ne ölçülür, ne ölçülmez

* **κ (varlık kararı).** Her (belge, alan) çifti için iki etiketleyicinin
  kararı: `dolu` (bu alan bu belgede var) ya da `absent` (yok). İnsan tarafı
  `fields` / `absent_fields` listelerinden okunur; alan ikisinde de yoksa
  KARAR VERİLMEMİŞTİR ve çift atılır (`eval/iaa.cohen_kappa` `None` çiftlerini
  zaten atar). Bu, span/slot düzeyi bir uyum ölçütüdür.
* **Değer uyumu.** İki taraf da "dolu" dediği alt kümede değerlerin birebir
  uyumu, `eval/matchers.tolerant_match` ile — resmî metriğin AYNI kodu.
  Bu bir κ DEĞİLDİR (şans düzeltmesi yok) ve öyle sunulmaz.
* **Ölçülmeyen:** kanıt penceresi (`field_spans`) uyumu. LLM span üretiyor ama
  insan tarafında span yalnız bazı kayıtlarda var; eksik veriyle κ hesaplamak
  sayıyı uydurmak olurdu.

## Kullanım

    python -m scripts.ikinci_etiketleyici kos     # LLM turu (uzun)
    python -m scripts.ikinci_etiketleyici kappa   # κ + uyuşmazlık raporu

`kos` çıktısını `data/gold/review/ikinci-tur-llm.jsonl`'e yazar; `kappa` onu
okur. İkisi ayrı çünkü LLM turu CPU'da saatler sürebilir ve κ hesabı
tekrarlanabilir olmalı.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Optional

KOK = Path(__file__).resolve().parents[1]
if str(KOK) not in sys.path:
    sys.path.insert(0, str(KOK))

from eval.iaa import cohen_kappa, interpret_kappa
from eval.matchers import tolerant_match
from scripts.gold_schema import load_gold
from src.extraction.llm.schema import EXTRACTION_FIELDS

GOLD = KOK / "data" / "gold" / "gold.v2.json"
CIKTI = KOK / "data" / "gold" / "review" / "ikinci-tur-llm.jsonl"
RAPOR = KOK / "data" / "gold" / "review" / "_kappa-ikinci-tur.md"

#: Blok başına seçilecek kayıt sayısı. 4 × 4 blok = 16 kayıt; κ'nın anlamlı
#: olması için her etiketleyicinin işi temsil edilmeli, yoksa ölçülen şey tek
#: bir kişinin kılavuz yorumuyla LLM'in uyumu olur.
BLOK_BASINA = 4


def _birincil_etiketleyici(kayit) -> str:
    """Kaydın birincil (insan) etiketleyicisi — hakem etiketleri sayılmaz."""
    for a in kayit.annotators or []:
        if not a.startswith("HAKEM"):
            return a
    return "?"


def sec(kayitlar) -> list:
    """Her etiketleyici bloğundan `BLOK_BASINA` kayıt — deterministik.

    Blok içinde kayıtlar id'ye göre sıralanır ve EŞİT ARALIKLA seçilir
    (ilk 4 değil): bloklar zorluk sırasına göre dizilmiş olabilir ve baştan
    almak zor vakaları ya da kolayları sistematik olarak dışlardı. Tohum
    kullanılmaz — seçim rastgele değil, tekrar-üretilebilir olmalı.
    """
    bloklar: dict[str, list] = {}
    for k in kayitlar:
        bloklar.setdefault(_birincil_etiketleyici(k), []).append(k)

    secilen = []
    for etiketleyici in sorted(bloklar):
        grup = sorted(bloklar[etiketleyici], key=lambda k: k.id)
        if not grup:
            continue
        adim = max(1, len(grup) // BLOK_BASINA)
        secilen.extend(grup[::adim][:BLOK_BASINA])
    return secilen


def kos(args: argparse.Namespace) -> int:
    from src.extraction.llm.extractor import default_extractor

    kayitlar = load_gold(GOLD)
    hedef = sec(kayitlar)
    print(f"seçilen: {len(hedef)} kayıt "
          f"({', '.join(sorted({_birincil_etiketleyici(k) for k in hedef}))})")

    llm = default_extractor()
    if not llm.available:
        print("❌ LLM erişilebilir değil. LLM_BACKEND / sunucu adresini "
              "kontrol edin. Sessizce kural motoruna DÜŞMEYECEK — ikinci "
              "etiketleyicinin kural motoru olması κ'yı anlamsız kılar "
              "(aynı kod kendini onaylar).")
        return 2

    CIKTI.parent.mkdir(parents=True, exist_ok=True)
    bu_model = os.environ.get("OLLAMA_MODEL") or os.environ.get("VLLM_MODEL") \
        or "?"
    yazili = set()
    if CIKTI.exists() and not args.bastan:
        modeller = set()
        for satir in CIKTI.read_text(encoding="utf-8").splitlines():
            if satir.strip():
                kayit_j = json.loads(satir)
                yazili.add(kayit_j["id"])
                modeller.add(kayit_j.get("model", "?"))
        # MODEL TUTARLILIĞI KAPISI. Bu betik dosyaya EKLEME yapıyor ve iki
        # koşum ortamı var: yerel CPU (küçük model) ve Colab GPU (büyük
        # model). Yarım kalmış bir yerel koşumun üzerine Colab'da devam
        # edilirse tek κ sayısı İKİ FARKLI etiketleyicinin kararlarından
        # hesaplanır ve rapor "ikinci etiketleyici: <tek model>" diye yazar —
        # ölçülen şey artık hiçbir şeyin uyumu olmaz. Karışık dosya sessizce
        # kabul edilmez.
        yabanci = modeller - {bu_model}
        if yabanci:
            print(f"❌ {CIKTI.name} başka modelin kararlarını taşıyor: "
                  f"{sorted(yabanci)} (şimdiki: {bu_model}). İki modelin "
                  "kararını tek κ'da toplamak ölçümü anlamsız kılar — "
                  "`--bastan` ile sıfırlayın ya da dosyayı taşıyın.")
            return 2
        print(f"devam: {len(yazili)} kayıt zaten yazılmış (--bastan ile sıfırla)")
    elif args.bastan and CIKTI.exists():
        CIKTI.unlink()

    with CIKTI.open("a", encoding="utf-8") as f:
        for i, kayit in enumerate(hedef, 1):
            if kayit.id in yazili:
                continue
            t0 = time.perf_counter()
            sonuc = llm.call(kayit.text)
            gecen = (time.perf_counter() - t0) * 1000
            alanlar = {a.field_name: a.canonical_value for a in sonuc.fields}
            f.write(json.dumps({
                "id": kayit.id,
                "annotator": "LLM-01",
                "primary_human": _birincil_etiketleyici(kayit),
                "fields": alanlar,
                "error": sonuc.error,
                "latency_ms": round(gecen, 1),
                "backend": os.environ.get("LLM_BACKEND", "?"),
                "model": os.environ.get("OLLAMA_MODEL")
                         or os.environ.get("VLLM_MODEL") or "?",
            }, ensure_ascii=False) + "\n")
            f.flush()
            durum = "HATA: " + str(sonuc.error)[:40] if sonuc.error \
                else f"{len(alanlar)} alan"
            print(f"  [{i}/{len(hedef)}] {kayit.id}  {gecen / 1000:.0f}s  {durum}")
    print(f"yazıldı: {CIKTI.relative_to(KOK)}")
    return 0


def _insan_karari(kayit, alan: str) -> Optional[str]:
    """İnsan etiketleyicinin varlık kararı; karar verilmemişse `None`."""
    if alan in kayit.fields:
        return "dolu"
    if alan in set(kayit.absent_fields):
        return "absent"
    return None                      # karar yok → κ çiftinden atılır


def kappa(args: argparse.Namespace) -> int:
    if not CIKTI.exists():
        print(f"❌ {CIKTI.relative_to(KOK)} yok — önce `kos` alt komutunu "
              "çalıştırın.")
        return 2

    kayitlar = {k.id: k for k in load_gold(GOLD)}
    ikinci = [json.loads(s) for s in
              CIKTI.read_text(encoding="utf-8").splitlines() if s.strip()]
    hatali = [x for x in ikinci if x.get("error")]
    ikinci = [x for x in ikinci if not x.get("error")]

    a_kararlar: list[Optional[str]] = []
    b_kararlar: list[Optional[str]] = []
    uyusmazlik: list[dict] = []
    ortak_dolu = 0
    deger_uyum = 0
    alan_bazli: dict[str, list[tuple]] = {}

    for x in ikinci:
        kayit = kayitlar.get(x["id"])
        if kayit is None:
            continue
        llm_alanlar = x["fields"]
        for alan in EXTRACTION_FIELDS:
            a = _insan_karari(kayit, alan)
            b = "dolu" if alan in llm_alanlar else "absent"
            a_kararlar.append(a)
            b_kararlar.append(b if a is not None else None)
            if a is None:
                continue
            alan_bazli.setdefault(alan, []).append((a, b))
            if a == "dolu" and b == "dolu":
                ortak_dolu += 1
                m = tolerant_match(alan, llm_alanlar[alan], kayit.fields[alan])
                if m.ok:
                    deger_uyum += 1
                else:
                    uyusmazlik.append({
                        "id": x["id"], "alan": alan, "tur": "deger",
                        "insan": kayit.fields[alan], "llm": llm_alanlar[alan],
                    })
            elif a != b:
                uyusmazlik.append({
                    "id": x["id"], "alan": alan,
                    "tur": "insan_dolu_llm_yok" if a == "dolu"
                           else "insan_yok_llm_dolu",
                    "insan": kayit.fields.get(alan),
                    "llm": llm_alanlar.get(alan),
                })

    k = cohen_kappa(a_kararlar, b_kararlar)
    yorum, _ = interpret_kappa(k)
    cift = sum(1 for a, b in zip(a_kararlar, b_kararlar, strict=True)
               if a is not None and b is not None)

    print(f"belge: {len(ikinci)} (hatalı {len(hatali)}) · κ çifti: {cift}")
    print(f"κ (varlık kararı) = {k:.3f}  → {yorum}")
    if ortak_dolu:
        print(f"değer uyumu (iki taraf da dolu): {deger_uyum}/{ortak_dolu} "
              f"= {deger_uyum / ortak_dolu:.3f}")
    print(f"uyuşmazlık: {len(uyusmazlik)}")

    _rapor_yaz(k, yorum, cift, len(ikinci), len(hatali), ortak_dolu,
               deger_uyum, uyusmazlik, alan_bazli, ikinci)
    print(f"rapor: {RAPOR.relative_to(KOK)}")
    return 0


def _rapor_yaz(k: float, yorum: str, cift: int, belge: int, hatali: int,
               ortak_dolu: int, deger_uyum: int, uyusmazlik: list[dict],
               alan_bazli: dict[str, list[tuple]], ikinci: list[dict]) -> None:
    model = ikinci[0].get("model", "?") if ikinci else "?"
    backend = ikinci[0].get("backend", "?") if ikinci else "?"
    sure = sum(x.get("latency_ms", 0) for x in ikinci) / 1000

    L = [
        "# κ (Cohen's kappa) — ikinci etiketleyici turu",
        "",
        "**İkinci etiketleyici bir LLM'dir.** İnsan çift-anotasyonun yerine "
        "geçtiği iddia edilmiyor; ölçülen şey bağımsız bir ikinci "
        "etiketleyicinin kararlarıyla uyumdur. LLM gold'u da kural motoru "
        "çıktısını da GÖRMEDİ — yalnız belge metnini ve alan şemasını aldı.",
        "",
        f"* arka uç / model: `{backend}` / `{model}`",
        f"* belge: **{belge}** (LLM hatası: {hatali})",
        f"* κ çifti (karar verilmiş (belge, alan) ikilisi): **{cift}**",
        f"* toplam LLM süresi: {sure / 60:.0f} dk",
        "",
        "## Sonuç",
        "",
        "| Ölçüt | Değer |",
        "|---|---|",
        f"| κ — varlık kararı (dolu / absent) | **{k:.3f}** ({yorum}) |",
    ]
    if ortak_dolu:
        L.append(f"| Değer uyumu (iki taraf da dolu; κ DEĞİL) | "
                 f"{deger_uyum}/{ortak_dolu} = {deger_uyum / ortak_dolu:.3f} |")
    L += [
        "",
        "`κ` yalnız **varlık** kararını ölçer: \"bu alan bu belgede var mı?\". "
        "Değer uyumu ayrı satırda ve şans düzeltmesi YOKTUR, bu yüzden κ "
        "olarak sunulmuyor. Kanıt penceresi (`field_spans`) uyumu hiç "
        "ölçülmedi — insan tarafında span yalnız bazı kayıtlarda var, eksik "
        "veriyle κ hesaplamak sayıyı uydurmak olurdu.",
        "",
        "## Alan bazında uyum",
        "",
        "| Alan | çift | uyum | κ |",
        "|---|---|---|---|",
    ]
    for alan in sorted(alan_bazli):
        ciftler = alan_bazli[alan]
        ay = sum(1 for a, b in ciftler if a == b)
        ak = cohen_kappa([a for a, _ in ciftler], [b for _, b in ciftler])
        ak_s = "—" if ak != ak else f"{ak:.3f}"          # nan kontrolü
        L.append(f"| `{alan}` | {len(ciftler)} | {ay}/{len(ciftler)} | {ak_s} |")

    L += [
        "",
        "Tek kategoriye yığılmış alanlarda κ tanımsızdır (`—`): iki taraf da "
        "\"yok\" diyorsa şans uyumu 1'dir ve κ payı 0/0 olur. Bu bir kusur "
        "değil, o alanda ölçülecek anlaşmazlık olmadığının ifadesidir.",
        "",
        "## Uyuşmazlıklar — hakeme gidecek liste",
        "",
        f"Toplam **{len(uyusmazlik)}** uyuşmazlık. Hakem turu yalnız bunlara "
        "bakar; uyuşan kararlar yeniden açılmaz.",
        "",
        "| Belge | Alan | Tür | İnsan | LLM |",
        "|---|---|---|---|---|",
    ]
    for u in uyusmazlik:
        L.append(f"| `{u['id']}` | `{u['alan']}` | {u['tur']} | "
                 f"`{u['insan']}` | `{u['llm']}` |")
    L += [
        "",
        "## Yöntem",
        "",
        "1. 48 kayıttan 16'sı seçildi: her insan etiketleyici bloğundan 4, "
        "blok içinde id sırasına göre EŞİT ARALIKLA (ilk 4 değil — bloklar "
        "zorluk sırasına dizilmiş olabilir ve baştan almak bir zorluk "
        "bandını sistematik dışlardı). Seçim tohumsuz ve tekrar-üretilebilir.",
        "2. LLM her belgeyi bağımsız etiketledi (`llm.call(text)`), gold'u "
        "görmeden.",
        "3. Varlık kararları eşleştirildi; karar verilmemiş alanlar "
        "(`fields`'ta da `absent_fields`'ta da olmayan) çiftten ATILDI.",
        "4. κ `eval/iaa.cohen_kappa` ile, değer uyumu "
        "`eval/matchers.tolerant_match` ile — resmî metriğin AYNI kodu.",
        "",
        "Üretim: `python -m scripts.ikinci_etiketleyici kappa`",
    ]
    RAPOR.write_text("\n".join(L) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    alt = ap.add_subparsers(dest="komut", required=True)
    p1 = alt.add_parser("kos", help="LLM ikinci etiketleyici turunu koş")
    p1.add_argument("--bastan", action="store_true",
                    help="mevcut çıktıyı yok say, baştan koş")
    p1.set_defaults(fn=kos)
    p2 = alt.add_parser("kappa", help="κ hesapla + uyuşmazlık raporu yaz")
    p2.set_defaults(fn=kappa)
    args = ap.parse_args()
    return args.fn(args)


if __name__ == "__main__":
    raise SystemExit(main())
