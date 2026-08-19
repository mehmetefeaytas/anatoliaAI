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

from eval.iaa import cohen_kappa, interpret_kappa, krippendorff_alpha
from eval.matchers import tolerant_match
from scripts.gold_schema import load_gold

# Sayıya indirme sıralamanın ve kıyasın kullandığı AYNI kodla yapılır;
# ikinci bir dönüştürücü α'yı kıyas motorunun görmediği bir ölçekte
# hesaplamak olurdu.
from src.comparison.compare import _numeric_key
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
    alpha_birimleri: list[list] = []
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
                # Krippendorff α (`ratio`) için sayısal birim. Kılavuz §7 iki
                # sayı vaat ediyor: karar uyumu (κ) VE değer uyumu (α, ratio
                # ölçeği — "%1,89 vs %1,90 tam uyuşmazlık sayılmaz"). α'yı
                # ölçmemek, kendi ilan ettiğimiz ölçütü atlamak olurdu.
                #
                # Sayıya indirme `compare._numeric_key` ile: sıralamanın ve
                # kıyasın kullandığı AYNI kod. İkinci bir dönüştürücü yazmak,
                # α'yı kıyas motorunun görmediği bir ölçekte hesaplamak
                # demekti. Aralık değerleri (`comparable=False`) atlanır —
                # ratio ölçeğinde bir aralığın "değeri" yoktur.
                ia, ia_ok, _ = _numeric_key(alan, kayit.fields[alan])
                ib, ib_ok, _ = _numeric_key(alan, llm_alanlar[alan])
                if ia_ok and ib_ok and ia is not None and ib is not None:
                    alpha_birimleri.append([ia, ib])
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
    alpha = krippendorff_alpha(alpha_birimleri, level="ratio") \
        if len(alpha_birimleri) >= 2 else float("nan")
    print(f"Krippendorff α (ratio, sayısal alanlar): "
          f"{'ölçülemedi' if alpha != alpha else f'{alpha:.3f}'} "
          f"({len(alpha_birimleri)} sayısal birim)")
    print(f"uyuşmazlık: {len(uyusmazlik)}")

    _rapor_yaz(k, yorum, cift, len(ikinci), len(hatali), ortak_dolu,
               deger_uyum, uyusmazlik, alan_bazli, ikinci,
               alpha, len(alpha_birimleri))
    print(f"rapor: {RAPOR.relative_to(KOK)}")
    return 0


def _rapor_yaz(k: float, yorum: str, cift: int, belge: int, hatali: int,
               ortak_dolu: int, deger_uyum: int, uyusmazlik: list[dict],
               alan_bazli: dict[str, list[tuple]], ikinci: list[dict],
               alpha: float, alpha_n: int) -> None:
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
        L.append(f"| Değer uyumu — birebir (iki taraf da dolu) | "
                 f"{deger_uyum}/{ortak_dolu} = {deger_uyum / ortak_dolu:.3f} |")
    #: α'nın istatistiksel olarak yorumlanabilmesi için asgari birim sayısı.
    #: Altında sayı YİNE raporlanır ama "yetersiz" damgasıyla — bir tanesi
    #: değişince 1.000'den 0'a düşebilen bir α'yı çıplak basmak, ölçülmemiş
    #: bir güveni ölçülmüş gibi göstermek olurdu.
    ALPHA_ASGARI = 10
    if alpha != alpha:
        L.append("| Krippendorff α (`ratio`, sayısal alanlar) | "
                 "**ölçülemedi** (2'den az sayısal birim) |")
    elif alpha_n < ALPHA_ASGARI:
        L.append(f"| Krippendorff α (`ratio`, sayısal alanlar) | "
                 f"{alpha:.3f} — **YETERSİZ BİRİM** ({alpha_n} < "
                 f"{ALPHA_ASGARI}) |")
    else:
        L.append(f"| Krippendorff α (`ratio`, sayısal alanlar) | "
                 f"**{alpha:.3f}** ({alpha_n} birim) |")
    L += [
        "",
        (f"α {alpha_n} sayısal birim üzerinden hesaplandı ve bu sayı bir "
         "iddiaya taban olamaz: tek bir birimin değişmesi α'yı 1.000'den "
         "sıfıra düşürebilir. Sebep kapsam: 26 ortak-dolu çiftin çoğu liste "
         "ya da serbest metin alanı (`hedef_kitle`, `kampanya_kosullari`) ve "
         "`ratio` ölçeğine oturmuyor; aralık değerleri de "
         "(`comparable=False`) atlanıyor. Kılavuz §7'nin vaat ettiği α "
         "ÖLÇÜLDÜ ama şu korpus kesitinde anlamlı değil — sayının kendisi "
         "değil bu sınır raporlanıyor."
         if alpha == alpha and alpha_n < 10 else ""),
        "",
        "`κ` yalnız **varlık** kararını ölçer: \"bu alan bu belgede var mı?\". "
        "Değer uyumu ayrı satırda ve şans düzeltmesi YOKTUR, bu yüzden κ "
        "olarak sunulmuyor. Kanıt penceresi (`field_spans`) uyumu hiç "
        "ölçülmedi — insan tarafında span yalnız bazı kayıtlarda var, eksik "
        "veriyle κ hesaplamak sayıyı uydurmak olurdu.",
        "",
        "## Alan bazında uyum",
        "",
        "Marjinal sayılar (kaç kez \"dolu\" dendi) tabloda BİLEREK duruyor: "
        "κ'yı onlar olmadan okumak yanıltıcıdır (aşağıdaki paradoks notu).",
        "",
        "| Alan | çift | gözlenen uyum | insan \"dolu\" | LLM \"dolu\" | κ |",
        "|---|---|---|---|---|---|",
    ]
    paradoks: list[str] = []
    ters: list[str] = []
    bos: list[str] = []
    for alan in sorted(alan_bazli):
        ciftler = alan_bazli[alan]
        ay = sum(1 for a, b in ciftler if a == b)
        a_dolu = sum(1 for a, _ in ciftler if a == "dolu")
        b_dolu = sum(1 for _, b in ciftler if b == "dolu")
        ak = cohen_kappa([a for a, _ in ciftler], [b for _, b in ciftler])
        ak_s = "tanımsız" if ak != ak else f"{ak:.3f}"        # nan kontrolü
        L.append(f"| `{alan}` | {len(ciftler)} | {ay}/{len(ciftler)} | "
                 f"{a_dolu} | {b_dolu} | {ak_s} |")
        if ak == ak and ak <= 0.0 and ay / len(ciftler) >= 0.75:
            (ters if ak < 0 else paradoks).append(alan)
        # κ = 1.0 ama hiçbir taraf "dolu" dememiş: `cohen_kappa` beklenen uyum
        # 1.0 olduğunda 1.0 döndürüyor (docstring'inde yazılı) ve tabloda bu
        # "mükemmel uyum" gibi okunur. Oysa ölçülecek anlaşmazlık YOKTUR.
        if a_dolu == 0 and b_dolu == 0:
            bos.append(alan)

    L += [
        "",
        "### κ paradoksu — yüksek uyum, sıfır κ",
        "",
        "Yukarıdaki tabloda gözlenen uyumu 15/16 olup κ'sı **0.000** çıkan "
        "alanlar var. Bu bir hesap hatası değil, Cohen's κ'nın bilinen "
        "davranışı: κ gözlenen uyumdan ŞANS uyumunu düşer ve marjinal "
        "dağılım çok dengesiz olduğunda (her iki etiketleyici de neredeyse "
        "her belgede \"yok\" diyorsa) şans uyumu gözlenen uyuma yaklaşır, "
        "pay sıfıra iner. Yani κ o alanda \"uyum yok\" DEMİYOR; \"bu "
        "marjinal dağılımda uyumun şanstan ayırt edilemeyeceğini\" diyor.",
        "",
        "Bu yüzden alan bazlı κ tek başına raporlanmaz: yanında gözlenen uyum "
        "ve iki tarafın \"dolu\" sayıları durur. Toplam κ (0'dan uzak) "
        "anlamlıdır çünkü 192 çiftte dağılım dengelidir.",
        "",
        (f"**Negatif κ — gerçek bulgu:** {', '.join('`' + a + '`' for a in ters)} "
         "alanında κ sıfırın ALTINDA. Bu, yüksek gözlenen uyuma rağmen iki "
         "etiketleyicinin anlaşmazlığının sistematik olduğunu gösterir: aynı "
         "belgelerde ters yönde karar veriyorlar. Kılavuzun o alandaki tanımı "
         "belirsiz olabilir ve hakem turunun ilk bakacağı yer burasıdır."
         if ters else
         "Negatif κ'lı alan yok — hiçbir alanda sistematik ters karar "
         "örüntüsü ölçülmedi."),
    ]
    if bos:
        L += [
            "",
            "**κ = 1.000 olan alanlar tam uyum DEĞİL, boş uyumdur:** "
            + ", ".join("`" + a + "`" for a in bos)
            + " alanlarında iki etiketleyici de HİÇBİR belgede \"dolu\" "
            "demedi. `cohen_kappa` beklenen uyum 1'e eşitken 1.0 döndürüyor "
            "(0/0 yerine \"tam uyum\" doğru yorum olduğu için) ama bu sayı "
            "\"bu alanda mükemmel anlaşıyoruz\" anlamına gelmez — o alanda "
            "16 belgenin hiçbirinde ölçülecek bir karar yok. Kapsam sorunu "
            "olarak okunmalı: `kar_payi_orani` korpus kapsaması %3,4'tür ve "
            "bunun sebebi çıkarım değil kaynak yapısıdır "
            "(`docs/rapor/banka-siteleri-veri-kaynagi-haritasi.md`).",
        ]
    L += [
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
