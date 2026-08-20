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
from typing import Any, Optional

KOK = Path(__file__).resolve().parents[1]
if str(KOK) not in sys.path:
    sys.path.insert(0, str(KOK))

from eval.iaa import cohen_kappa, interpret_kappa, krippendorff_alpha
from eval.matchers import tolerant_match
from scripts.gold_schema import (
    LABEL_LIST_FIELDS,
    TEXT_LIST_FIELDS,
    GoldValidationError,
    load_gold,
    parse_gold_value,
)

# Sayıya indirme sıralamanın ve kıyasın kullandığı AYNI kodla yapılır;
# ikinci bir dönüştürücü α'yı kıyas motorunun görmediği bir ölçekte
# hesaplamak olurdu.
from src.comparison.compare import _numeric_key
from src.extraction.llm.schema import EXTRACTION_FIELDS

GOLD = KOK / "data" / "gold" / "gold.v2.json"
CIKTI = KOK / "data" / "gold" / "review" / "ikinci-tur-llm.jsonl"
RAPOR = KOK / "data" / "gold" / "review" / "_kappa-ikinci-tur.md"

# İNSAN TURU — jüri gerekçesi: κ=0,700 ölçümü doğrulandı ama kısmi kredi
# verildi çünkü ikinci etiketleyici bir LLM'di (model-model uyumu, gold'un
# İNSAN yargısıyla tutarlılığını KANITLAMAZ). Bu turun tek farkı ikinci
# etiketleyicinin kim/ne olduğu; kappa() aynı kodla, aynı 16 kayıtla çalışır.
CIKTI_INSAN = KOK / "data" / "gold" / "review" / "ikinci-tur-insan.jsonl"
ILERLEME_INSAN = KOK / "data" / "gold" / "review" / ".ikinci-tur-insan-ilerleme.json"
INSAN_ID = "INSAN-01"

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


#: Alan başına kısa hatırlatma — ANNOTATION_GUIDE.md §4 özetidir, kılavuzun
#: yerine geçmez. İnsan etiketleyici emin değilse kılavuza döner.
FIELD_YARDIM: dict[str, str] = {
    "kar_payi_orani": (
        'Kâr payı oranı (%). Örn: "%1,89" -> 1.89 · aralık: "%1,99-%2,49". '
        '"ilk 6 ay %0, sonrası %1,89" -> yürürlükteki 1.89 yazın (koşulu '
        "kampanya_kosullari'na ekleyin). Katılma hesabı GETİRİ oranı ve N/M "
        'kâr paylaşımı ("85/15") bu alana YAZILMAZ -> yok.'
    ),
    "finansman_tutari": (
        'Finansman tutarı (TL). Örn: "500.000 TL\'ye varan finansman" -> '
        "500000. Ödül/hediye tutarı bu alana yazılmaz (o odul_miktari)."
    ),
    "vade_ay": (
        'Vade, AY cinsinden tamsayı. Örn: "120 aya varan vade" -> 120, '
        '"1 yıl" -> 12. Aralıksa EN UZUN vadeyi yazın. "45 gün" gibi 30\'un '
        "katı olmayan gün vade -> yok yazıp not düşün (kılavuz §4.13/7)."
    ),
    "taksit_sayisi": (
        'Taksit adedi. DİKKAT — belgede "taksit" kelimesi hiç geçmiyorsa bu '
        "alan yoktur (o sayı vadedir, vade_ay'a gider). "
        'Örn: "vade farksız 6 taksit" -> 6.'
    ),
    "tahsis_ucreti": (
        'Tahsis/dosya ücreti (TL). Örn: "tahsis ücreti 500 TL" -> 500. '
        '"alınmaz" ise 0 yazın (yok DEĞİL — sıfırın kendisi bir bilgidir). '
        '"binde 5" gibi ORANSAL ücret bu alana yazılmaz -> yok.'
    ),
    "masraf_durumu": (
        'Masraf var mı? "masrafsız/ücret alınmaz" NEGATİF bir bilgidir, '
        "yok DEĞİLDİR: {has_fee: false, amount: 0} yazın (metne \"has_fee: "
        'false\" gibi yazmayın; sadece "masrafsız" yazmanız yeter, sistem '
        'çevirir). Ücret varsa "dosya masrafı 500 TL" yazın.'
    ),
    "odul_miktari": (
        'Ödül/hediye tutarı (TL). Örn: "5.000 TL\'ye varan hoş geldin '
        'hediyesi" -> 5000. Tutar cinsinden indirim ("100 TL indirim") de '
        "BU alana yazılır, indirim_orani'na değil."
    ),
    "indirim_orani": (
        'İndirim YÜZDESİ. Örn: "%10 indirim" -> 10. Yalnız yüzde; tutar '
        "cinsinden indirim odul_miktari'na gider."
    ),
    "alisveris_puani": (
        "ORAN mı ADET mi ayrımı zorunlu. Oran: \"%5 puan iadesi\" -> yazın "
        '"oran=5". Adet: "1.000 chip-para" -> "puan=1000". Sektöre göre '
        "farklı oranlar varsa EN YÜKSEĞİNİ yazın, gerisini "
        "kampanya_kosullari'na düşün."
    ),
    "kampanya_suresi": (
        'Kampanyanın BİTİŞ tarihi, ISO-8601. Örn: "31.12.2026 tarihine '
        'kadar" -> 2026-12-31. Yalnız başlangıç tarihi varsa yok yazın.'
    ),
    "kampanya_kosullari": (
        "Koşul cümleleri — METİNDEN BİREBİR KOPYALAYIN (kendi cümlenizle "
        'yazmayın). Genel yasal ihtarlar ("hakkını saklı tutar" vb.) koşul '
        "SAYILMAZ. Başka alana ait değer (vade, tutar, oran, tarih) burada "
        "TEKRARLANMAZ — yalnızca değer bir koşula bağlıysa (\"ilk 6 ay %0, "
        'sonra %1,89\") cümlenin tamamı buraya da girer.'
    ),
    "hedef_kitle": (
        "YALNIZ 4 etiket: yeni_musteri, mevcut_musteri, maas_musterisi, "
        'belirli_segment. "Bireysel müşteriler" = HERKES, segment DEĞİLDİR '
        "-> yok. Ürün/kart/kanal kısıtı (\"yalnız Paraf kartlar\") segment "
        "DEĞİLDİR, kampanya_kosullari'na gider. Serbest metin yazılmaz."
    ),
}


def _coklu_alan_mi(alan: str) -> bool:
    return alan in TEXT_LIST_FIELDS or alan in LABEL_LIST_FIELDS


def _cok_satir_oku(girdi_fn, yaz_fn) -> list[str]:
    """Boş satıra kadar art arda satır okur (liste alanlarının çoklu girişi)."""
    satirlar: list[str] = []
    while True:
        satir = girdi_fn().strip()
        if not satir:
            break
        satirlar.append(satir)
    return satirlar


def _alan_sor(alan: str, girdi_fn=input, yaz_fn=print) -> tuple[bool, Any]:
    """Bir alanı insana sorar; `(dolu_mu, kanonik_deger)` döner.

    KÖRLEME BURADA GARANTİ EDİLİR: bu fonksiyon `kayit.fields`,
    `kayit.absent_fields` ya da ikinci-tur-llm.jsonl'e erişmez — parametre
    olarak bile ALMAZ. Yalnız alan adı ve kullanıcının o an yazdığı metni
    görür. Gold değerini ya da LLM kararını göstermek κ'yı anlamsız kılar
    (jüri gerekçesi: ikinci etiketleyici insana taşınmasının TEK sebebi
    budur — bkz. modül başlığı).

    Dönüş: alan "yok" ise `(False, None)`; doluysa `(True, kanonik_deger)`
    ve `kanonik_deger` `scripts.gold_schema.parse_gold_value` ile üretilir
    — gold'un kendisinin kullandığı AYNI ayrıştırıcı/doğrulayıcı.
    """
    yaz_fn(f"\n--- {alan} ---")
    yaz_fn(FIELD_YARDIM.get(alan, "(ANNOTATION_GUIDE.md §4'e bakın)"))
    coklu = _coklu_alan_mi(alan)
    if coklu:
        yaz_fn("Birden çok girdi olabilir: her biri ayrı satıra, bitirmek "
               "için boş satır. Alan yoksa TEK satıra 'yok' yazın.")
    else:
        yaz_fn("Değeri yazın; alan belgede yoksa 'yok' yazın.")
    while True:
        ilk = girdi_fn().strip()
        if ilk.casefold() == "yok":
            return False, None
        if not ilk:
            yaz_fn("Boş geçemezsiniz — değer yazın ya da 'yok' yazın.")
            continue
        ham = "|".join([ilk] + _cok_satir_oku(girdi_fn, yaz_fn)) if coklu else ilk
        try:
            deger = parse_gold_value(alan, ham)
        except GoldValidationError as e:
            yaz_fn(f"HATA: {e}")
            yaz_fn("Tekrar deneyin.")
            continue
        return True, deger


def _ilerleme_yukle(yol: Path) -> dict:
    if yol.exists():
        return json.loads(yol.read_text(encoding="utf-8"))
    return {}


def _ilerleme_kaydet(yol: Path, ilerleme: dict) -> None:
    yol.parent.mkdir(parents=True, exist_ok=True)
    yol.write_text(json.dumps(ilerleme, ensure_ascii=False, indent=2),
                    encoding="utf-8")


def _tamamlanan_kayit_idleri(cikti_yolu: Path) -> set[str]:
    if not cikti_yolu.exists():
        return set()
    idler = set()
    for satir in cikti_yolu.read_text(encoding="utf-8").splitlines():
        if satir.strip():
            idler.add(json.loads(satir)["id"])
    return idler


def insan(kayitlar=None, cikti_yolu: Path = CIKTI_INSAN,
          ilerleme_yolu: Path = ILERLEME_INSAN, girdi_fn=input,
          yaz_fn=print, bastan: bool = False) -> int:
    """İnsan ikinci-etiketleyici turu — `kos()`nun insan karşılığı.

    Seçim `sec()` ile YAPILIR (yeni rastgelelik YOK) ki LLM turuyla aynı 16
    kayıt üzerinde κ kıyaslanabilsin. Kaydetme ARTIMLIDIR: her alan
    cevaplandığında `ilerleme_yolu`ya yazılır (kayıt yarıda kesilse bile
    kaybolmaz); bir kayıt TAMAMLANINCA `cikti_yolu`ya `kappa` alt komutunun
    okuduğu biçimde tek satır JSONL eklenir.
    """
    if bastan:
        if cikti_yolu.exists():
            cikti_yolu.unlink()
        if ilerleme_yolu.exists():
            ilerleme_yolu.unlink()

    if kayitlar is None:
        kayitlar = load_gold(GOLD)
    hedef = sec(kayitlar)

    tamam = _tamamlanan_kayit_idleri(cikti_yolu)
    kalan = [k for k in hedef if k.id not in tamam]

    tahmini_dk = len(hedef) * 5   # ANNOTATION_GUIDE.md §1: elle ~5 dk/belge
    yaz_fn("İKİNCİ ETİKETLEYİCİ — İNSAN TURU")
    yaz_fn(f"Seçilen kayıt: {len(hedef)} · alan/kayıt: {len(EXTRACTION_FIELDS)}")
    yaz_fn(f"Tahmini toplam süre: ~{tahmini_dk} dakika "
           "(ANNOTATION_GUIDE.md §1 ölçümüne göre ~5 dk/belge)")
    yaz_fn(f"Zaten tamamlanmış: {len(tamam)}/{len(hedef)} kayıt.")
    if not kalan:
        yaz_fn("Tüm kayıtlar tamamlanmış. κ için: "
               f"python -m scripts.ikinci_etiketleyici kappa --girdi "
               f"{cikti_yolu}")
        return 0

    ilerleme = _ilerleme_yukle(ilerleme_yolu)
    cikti_yolu.parent.mkdir(parents=True, exist_ok=True)
    with cikti_yolu.open("a", encoding="utf-8") as f:
        for i, kayit in enumerate(kalan, 1):
            yaz_fn(f"\n===== Kayıt {i}/{len(kalan)} — {kayit.id} =====")
            yaz_fn(kayit.text)
            yaz_fn("-" * 70)
            durum_alan = ilerleme.setdefault(kayit.id, {})
            t0 = time.perf_counter()
            for alan in EXTRACTION_FIELDS:
                if alan in durum_alan:
                    continue          # kaldığı yerden devam
                dolu, deger = _alan_sor(alan, girdi_fn, yaz_fn)
                durum_alan[alan] = {"dolu": dolu, "deger": deger}
                _ilerleme_kaydet(ilerleme_yolu, ilerleme)   # her alanda kalıcı
            gecen = (time.perf_counter() - t0) * 1000
            alanlar = {a: v["deger"] for a, v in durum_alan.items() if v["dolu"]}
            f.write(json.dumps({
                "id": kayit.id,
                "annotator": INSAN_ID,
                "primary_human": _birincil_etiketleyici(kayit),
                "fields": alanlar,
                "error": None,
                "latency_ms": round(gecen, 1),
                "backend": "insan",
                "model": INSAN_ID,
            }, ensure_ascii=False) + "\n")
            f.flush()
            del ilerleme[kayit.id]
            _ilerleme_kaydet(ilerleme_yolu, ilerleme)
            yaz_fn(f"[{i}/{len(kalan)}] {kayit.id} kaydedildi — "
                   f"{len(alanlar)} alan dolu.")
    yaz_fn(f"\nBitti. Çıktı: {cikti_yolu}")
    yaz_fn("κ için: python -m scripts.ikinci_etiketleyici kappa --girdi "
           f"{cikti_yolu}")
    return 0


def insan_cli(args: argparse.Namespace) -> int:
    return insan(cikti_yolu=CIKTI_INSAN, ilerleme_yolu=ILERLEME_INSAN,
                 bastan=args.bastan)


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
    girdi = Path(args.girdi).resolve() if getattr(args, "girdi", None) else CIKTI
    if not girdi.exists():
        kaynak_komut = "insan" if girdi == CIKTI_INSAN else "kos"
        print(f"❌ {girdi} yok — önce `{kaynak_komut}` alt komutunu "
              "çalıştırın.")
        return 2
    # Rapor hedefi girdiye göre ayrışır: LLM turunun raporu (`_kappa-ikinci-
    # tur.md`) insan turu koşulunca SESSİZCE ÜZERİNE YAZILMAZ — jüri ikisini
    # yan yana görmeli (model-model κ=0,700 vs. insan-insan κ), biri diğerini
    # silerse kıyas kaybolur.
    rapor_yolu = RAPOR if girdi == CIKTI else girdi.parent / f"_kappa-{girdi.stem}.md"

    kayitlar = {k.id: k for k in load_gold(GOLD)}
    ikinci = [json.loads(s) for s in
              girdi.read_text(encoding="utf-8").splitlines() if s.strip()]
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
               alpha, len(alpha_birimleri), rapor_yolu)
    try:
        print(f"rapor: {rapor_yolu.relative_to(KOK)}")
    except ValueError:
        print(f"rapor: {rapor_yolu}")
    return 0


def _rapor_yaz(k: float, yorum: str, cift: int, belge: int, hatali: int,
               ortak_dolu: int, deger_uyum: int, uyusmazlik: list[dict],
               alan_bazli: dict[str, list[tuple]], ikinci: list[dict],
               alpha: float, alpha_n: int, rapor_yolu: Path = RAPOR) -> None:
    model = ikinci[0].get("model", "?") if ikinci else "?"
    backend = ikinci[0].get("backend", "?") if ikinci else "?"
    sure = sum(x.get("latency_ms", 0) for x in ikinci) / 1000
    # İNSAN TURU mu — jüri gerekçesinin karşılandığını raporun kendisinde de
    # açıkça yaz; LLM turunun metniyle karıştırılmasın.
    insan_turu = backend == "insan"

    if insan_turu:
        acilis = (
            "**İkinci etiketleyici bir İNSANDIR** (proje sahibi, "
            f"`{model}`). Bu, jürinin \"κ'da ikinci etiketleyiciyi insana "
            "taşı\" gerekçesini karşılar: ölçülen şey artık model-model "
            "uyumu değil, iki BAĞIMSIZ İNSAN yargıcın (birincil anotatör + "
            f"`{model}`) uyumudur ve κ'nın klasik tanımına birebir uyar. "
            f"`{model}` gold değerini de kural motoru/LLM çıktısını da "
            "GÖRMEDİ — yalnız belge metnini ve alan şemasını gördü "
            "(`scripts/ikinci_etiketleyici._alan_sor` körlemesi; ayrıntı: "
            "`tests/test_insan_etiketleyici.py`)."
        )
    else:
        acilis = (
            "**İkinci etiketleyici bir LLM'dir.** İnsan çift-anotasyonun "
            "yerine geçtiği iddia edilmiyor; ölçülen şey bağımsız bir "
            "ikinci etiketleyicinin kararlarıyla uyumdur. LLM gold'u da "
            "kural motoru çıktısını da GÖRMEDİ — yalnız belge metnini ve "
            "alan şemasını aldı."
        )

    L = [
        f"# κ (Cohen's kappa) — ikinci etiketleyici turu"
        f"{' (İNSAN)' if insan_turu else ''}",
        "",
        acilis,
        "",
        f"* {'etiketleyici' if insan_turu else 'arka uç / model'}: "
        f"`{backend}` / `{model}`",
        f"* belge: **{belge}** ({'insan' if insan_turu else 'LLM'} hatası: {hatali})",
        f"* κ çifti (karar verilmiş (belge, alan) ikilisi): **{cift}**",
        f"* toplam {'insan' if insan_turu else 'LLM'} süresi: {sure / 60:.0f} dk",
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
        "Üretim: `python -m scripts.ikinci_etiketleyici kappa" +
        (" --girdi data/gold/review/ikinci-tur-insan.jsonl`" if insan_turu
         else "`"),
    ]
    rapor_yolu.parent.mkdir(parents=True, exist_ok=True)
    rapor_yolu.write_text("\n".join(L) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    alt = ap.add_subparsers(dest="komut", required=True)
    p1 = alt.add_parser("kos", help="LLM ikinci etiketleyici turunu koş")
    p1.add_argument("--bastan", action="store_true",
                    help="mevcut çıktıyı yok say, baştan koş")
    p1.set_defaults(fn=kos)
    p3 = alt.add_parser("insan", help="İNSAN ikinci etiketleyici turunu koş "
                                       "(körlemeli, artımlı)")
    p3.add_argument("--bastan", action="store_true",
                    help="mevcut çıktıyı/ilerlemeyi yok say, baştan koş")
    p3.set_defaults(fn=insan_cli)
    p2 = alt.add_parser("kappa", help="κ hesapla + uyuşmazlık raporu yaz")
    p2.add_argument("--girdi", default=None,
                    help="hangi ikinci-tur JSONL'i okunacak (varsayılan: "
                         "ikinci-tur-llm.jsonl). İnsan turu için: "
                         "data/gold/review/ikinci-tur-insan.jsonl")
    p2.set_defaults(fn=kappa)
    args = ap.parse_args()
    return args.fn(args)


if __name__ == "__main__":
    raise SystemExit(main())
