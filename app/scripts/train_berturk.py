"""BERTurk ince ayarı — 8 sınıflı kampanya türü sınıflandırması, YEREL koşum.

İlgili: ../notebooks/berturk_ince_ayar.ipynb (Colab yedek yolu — aynı bölme,
        aynı sınıf ağırlığı, aynı metrik),
        ../docs/rapor/berturk-ince-ayar-plani.md (plan, hipotez, kabul kriteri),
        ./eval_classifier.py (metrik hattı — `olc` BURADAN import edilir),
        ../eval/run_eval.py (`Counts` + `macro_f1`, hattın kökü),
        ../src/extraction/ner/classifier.py (`BerturkClassifier` bağlantı noktası),
        CLAUDE.md §3 (offline), §4 (tek izinli fine-tune), §7/§20 (lisans),
        §16 (ablasyon), §19 (uydurma yok)

Kullanım:
    .venv/bin/python -m scripts.train_berturk
    .venv/bin/python -m scripts.train_berturk --cihaz cpu --epoch 3   # hızlı deneme

## Bu betik neden var — Colab defteri dururken

`notebooks/berturk_ince_ayar.ipynb` bu ince ayarı Colab'da (T4 GPU) koşuyor ve
**yedek yol olarak kalıyor**. Ama iş 505 örnek x `bert-base` ölçeğinde; Apple
Silicon'da (MPS) veya CPU'da dakikalar sürüyor. Yerelde koşabilmek iki şey
kazandırır:

1. **Colab bağımlılığı düşer.** Ağırlıklar tek komutla, tarayıcı/Drive/elle
   dosya taşıma olmadan yeniden üretilir.
2. **On-prem anlatısı güçlenir.** Teslim edilen sistem zaten çevrimdışı
   çalışmak zorunda (`docs/OFFLINE-KANIT.md`); eğitim de aynı makinede
   koşuyorsa "hiçbir aşamada dış servise bağımlı değiliz" iddiası ölçülmüş
   olur. Kalan tek çevrimiçi adım taban ağırlığın bir kereye mahsus
   indirilmesidir; çıkarım tamamen yereldir.

## Kanoniklik — defter mi betik mi

**Bu betik kanoniktir.** Depodaki `data/eval/berturk_preds.jsonl`,
`models/berturk-kampanya-8sinif/` ve `KUNYE.json` bu betiğin çıktısıdır.
Defter aynı bölmeyi (tohum 42), aynı sınıf ağırlığını ve aynı metrik hattını
uygular ama Colab'a özgü hücreler (Drive bağlama, `!pip install`) taşır ve
eğitim döngüsü için `Trainer` kullanır. İki taraf ayrışırsa **betik doğrudur**;
defter, GPU gerekirse veya yerel makine yoksa koşulacak yedek yoldur.

## Metrik hattı tek — ayrı bir hat kurulmadı

Sayılar `scripts/eval_classifier.olc` ile üretilir; o da `eval/run_eval`'in
`Counts` ve `macro_f1` tanımlarını kullanır. Kural temel çizgisi de aynı
fonksiyondan geçiyor — başka türlüsü kıyaslanabilir sayı üretmez. Özellikle:

- **Çekimserlik** doğru sınıf için FN, hiçbir sınıf için FP değildir.
- **Makro-F1** yalnız `support > 0` olan sınıflar üzerinden ortalanır.

BERTurk softmax'ı her zaman bir sınıf seçer; `--cekimser-esigi` ile bir güven
eşiği konabilir (0,0 = çekimserlik yok). Eşiği yükseltmek makro-F1'i
**düşürür**, çünkü çekimserlik FN'dir.

## Kabul kapısı (plan §5) — değiştirilmedi

BERTurk projeye ancak gold makro-F1'inin **%95 bootstrap güven aralığının ALT
SINIRI** kural çizgisinin **0,762** değerini aşarsa alınır. Aralık 0,762'yi
içeriyorsa sonuç "ayırt edilemez"dir ve varsayılan `RuleHintClassifier` kalır.
Betik bu kararı kendi basar ve künyeye yazar; yorumu çağırana bırakmaz.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import sys
import time
import urllib.request
from datetime import datetime, timezone
from typing import Any, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.eval_classifier import olc  # TEK metrik hattı — ayrı kopya YOK
from src.schemas import CAMPAIGN_TYPES

#: Taban model. CLAUDE.md §7/§20 gereği lisansı aşağıdaki kapıdan geçmek zorunda.
MODEL_ADI = "dbmdz/bert-base-turkish-cased"

#: İzinli lisanslar — CLAUDE.md §3, §20. Gemma / Llama community YASAK.
IZINLI_LISANSLAR = frozenset({"mit", "apache-2.0"})

#: Kural temel çizgisinin ÖLÇÜLMÜŞ gold makro-F1'i
#: (`data/eval/classifier_baseline.json`). Kabul kapısının eşiği budur.
TEMEL_CIZGI_MACRO_F1 = 0.762
TEMEL_CIZGI_ACCURACY = 0.700

#: Bölme tohumu. Defterle birebir aynı olmak zorunda, yoksa bölmeler ayrışır.
TOHUM = 42


# --------------------------------------------------------------------------- #
# Lisans kapısı — defterin 2. hücresinin birebir karşılığı
# --------------------------------------------------------------------------- #
def lisans_dogrula(model_adi: str, derinlik: int = 0) -> str:
    """Modelin lisansını doğrular ve `base_model` zincirini KÖKE kadar takip eder.

    Türev bir modelin lisansı kökündekinden daha serbest olamaz; bu yüzden
    zincirdeki HER halka izinli listede olmak zorundadır. Uygun değilse
    `RuntimeError` — eğitim başlamadan durur. Kapının atlanma yolu yok:
    ağırlığı indirmek zaten ağ gerektiriyor, dolayısıyla doğrulama da
    koşulabilir durumda demektir.
    """
    girinti = "  " * derinlik
    url = f"https://huggingface.co/api/models/{model_adi}"
    with urllib.request.urlopen(url, timeout=30) as r:
        meta = json.load(r)
    kart = meta.get("cardData") or {}
    lisans = (kart.get("license") or "").strip().lower()
    taban = kart.get("base_model")

    print(f"{girinti}model      : {model_adi}")
    print(f"{girinti}license    : {lisans or '(BEYAN EDİLMEMİŞ)'}")
    print(f"{girinti}base_model : {taban or '(yok -> zincirin KÖKÜ)'}")

    if lisans not in IZINLI_LISANSLAR:
        raise RuntimeError(
            f"LİSANS UYGUN DEĞİL: {model_adi} -> '{lisans}'. "
            f"İzinli: {sorted(IZINLI_LISANSLAR)}. CLAUDE.md §3/§20 gereği bu "
            f"ağırlık kullanılamaz; eğitimi koşma."
        )

    if taban:
        for t in ([taban] if isinstance(taban, str) else taban):
            if t and t != model_adi:
                print(f"{girinti}-> taban zinciri takip ediliyor...")
                lisans_dogrula(t, derinlik + 1)
    return lisans


# --------------------------------------------------------------------------- #
# Veri
# --------------------------------------------------------------------------- #
def jsonl_oku(yol: str) -> list[dict[str, Any]]:
    with open(yol, encoding="utf-8") as fh:
        return [json.loads(s) for s in fh if s.strip()]


def bolme_uret(kayitlar: list[dict[str, Any]], tohum: int = TOHUM
               ) -> dict[str, list[int]]:
    """%70/%15/%15 katmanlı bölme — defterin bölme hücresiyle BİREBİR aynı.

    Adım sırası da aynı: önce test (%15) ayrılır, kalandan doğrulama
    (%15/%85). Sıra değişirse `train_test_split` başka bir bölme üretir ve
    defterle betik kıyaslanamaz hâle gelir.
    """
    from sklearn.model_selection import train_test_split

    X = list(range(len(kayitlar)))
    y = [r["label"] for r in kayitlar]

    idx_kalan, idx_test = train_test_split(
        X, test_size=0.15, random_state=tohum, stratify=y)
    idx_egitim, idx_dogrulama = train_test_split(
        idx_kalan, test_size=0.15 / 0.85, random_state=tohum,
        stratify=[y[i] for i in idx_kalan])

    if set(idx_egitim) & set(idx_dogrulama):
        raise AssertionError("eğitim/doğrulama örtüşüyor")
    if set(idx_egitim) & set(idx_test):
        raise AssertionError("eğitim/test örtüşüyor")
    if set(idx_dogrulama) & set(idx_test):
        raise AssertionError("doğrulama/test örtüşüyor")
    if len(idx_egitim) + len(idx_dogrulama) + len(idx_test) != len(kayitlar):
        raise AssertionError("bölme toplamı kayıt sayısını tutmuyor")

    return {"eğitim": idx_egitim, "doğrulama": idx_dogrulama, "test": idx_test}


# --------------------------------------------------------------------------- #
# Metrik — scripts/eval_classifier.olc üzerinden (ayrı hat YOK)
# --------------------------------------------------------------------------- #
def olc_listeler(gercekler: list[str],
                 tahminler: list[Optional[str]]) -> dict[str, Any]:
    """Konum bazlı liste çiftini `olc`'nin (doc_id, metin, etiket) şemasına çevirir.

    Sentetik `#i` kimlikleri kullanılıyor: bootstrap yerine koyarak
    örneklediği için gerçek `doc_id`'ler tekrar eder ve sözlükte çakışırdı —
    çakışma örneklem büyüklüğünü sessizce küçültür.
    """
    gold = [(f"#{i}", "", g) for i, g in enumerate(gercekler)]
    tahmin = {f"#{i}": p for i, p in enumerate(tahminler)}
    return olc(gold, tahmin)


def bootstrap_ga(gercekler: list[str], tahminler: list[Optional[str]],
                 yineleme: int = 5000, tohum: int = TOHUM
                 ) -> dict[str, tuple[float, float, float]]:
    """%95 bootstrap güven aralığı — defterin GA hücresiyle aynı yordam.

    Aralık **tek bölme içindeki örnekleme belirsizliğini** ölçer; bölme
    değişkenliğini (farklı tohum) ölçmez. Plan §6 R6 bunu açık risk olarak
    taşıyor.
    """
    import numpy as np

    rng = np.random.default_rng(tohum)
    n = len(gercekler)
    acc, f1 = [], []
    for _ in range(yineleme):
        idx = rng.integers(0, n, size=n)
        s = olc_listeler([gercekler[i] for i in idx], [tahminler[i] for i in idx])
        acc.append(s["accuracy"])
        f1.append(s["macro_f1"])
    acc_a, f1_a = np.array(acc), np.array(f1)
    return {
        "accuracy": (float(acc_a.mean()),
                     *(float(v) for v in np.percentile(acc_a, [2.5, 97.5]))),
        "macro_f1": (float(f1_a.mean()),
                     *(float(v) for v in np.percentile(f1_a, [2.5, 97.5]))),
    }


def yazdir_ozet(ad: str, s: dict[str, Any]) -> None:
    """`scripts/eval_classifier._yazdir` ile aynı biçim — çıktılar yan yana okunsun."""
    print(f"\n=== {ad} ===")
    print(f"n={s['n']}  doğru={s['dogru']}  çekimser={s['cekimser']}")
    print(f"accuracy = {s['accuracy']:.3f}")
    print(f"macro-F1 = {s['macro_f1']:.3f}")
    print(f"\n{'sınıf':<22}{'destek':>7}{'P':>8}{'R':>8}{'F1':>8}")
    for sinif in CAMPAIGN_TYPES:
        c = s["tablo"][sinif]
        if c.support == 0 and c.fp == 0:
            continue
        print(f"{sinif:<22}{c.support:>7}{c.precision():>8.3f}"
              f"{c.recall():>8.3f}{c.f1():>8.3f}")
    if s["karisiklik"]:
        print("\nkarışıklıklar (gerçek -> tahmin):")
        for (g, p), n in s["karisiklik"].most_common(10):
            print(f"  {g} -> {p}: {n}")


# --------------------------------------------------------------------------- #
# Eğitim
# --------------------------------------------------------------------------- #
def cihaz_sec(istek: str):
    """`auto` -> cuda > mps > cpu. MPS, Apple Silicon'da bert-base için yeterli."""
    import torch

    if istek != "auto":
        return torch.device(istek)
    if torch.cuda.is_available():
        return torch.device("cuda")
    if getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
        return torch.device("mps")
    return torch.device("cpu")


def _partiler(n: int, parti: int, karistir: bool,
              rng: random.Random) -> list[list[int]]:
    idx = list(range(n))
    if karistir:
        rng.shuffle(idx)
    return [idx[i:i + parti] for i in range(0, n, parti)]


def tahmin_uret(model, tokenizer, metinler: list[str], max_length: int,
                cihaz, parti: int, esik: float
                ) -> tuple[list[Optional[str]], list[float]]:
    """Etiket listesi + güven listesi. Güven eşiğin altındaysa None (çekimser)."""
    import torch

    model.train(False)          # değerlendirme kipi (dropout kapalı)
    etiketler: list[Optional[str]] = []
    guvenler: list[float] = []
    with torch.no_grad():
        for bas in range(0, len(metinler), parti):
            kod = tokenizer(metinler[bas:bas + parti], truncation=True,
                            max_length=max_length, padding=True,
                            return_tensors="pt")
            kod = {k: v.to(cihaz) for k, v in kod.items()}
            olasilik = torch.softmax(model(**kod).logits.float().cpu(), dim=-1)
            for i, g in zip(olasilik.argmax(dim=-1).tolist(),
                            olasilik.max(dim=-1).values.tolist(),
                            strict=True):
                etiketler.append(None if g < esik else CAMPAIGN_TYPES[int(i)])
                guvenler.append(float(g))
    return etiketler, guvenler


def egit(kayitlar: list[dict[str, Any]], bolme: dict[str, list[int]],
         args: argparse.Namespace) -> tuple[Any, Any, list[dict[str, Any]]]:
    """Sınıf ağırlıklı eğitim + doğrulama makro-F1'i üzerinden erken durdurma.

    Defterle aynı hiperparametreler (plan §7): lr 2e-5, parti 16, epoch 8
    (sabır 3), weight_decay 0,01, warmup %10, max_length 256, sınıf ağırlığı
    `balanced` formülü.

    `Trainer` yerine düz PyTorch döngüsü: `datasets` ve `accelerate`
    bağımlılıklarını eklemiyor (çevrimdışı demo yüzeyini büyütmemek için) ve
    `transformers` sürümleri arasında ad değiştiren `TrainingArguments`
    alanlarına kırılgan değil. Optimizasyon ayarları HF varsayılanlarıyla
    hizalı tutuldu: AdamW, doğrusal azalan zamanlayıcı, bias/LayerNorm'a
    weight decay uygulanmaz, gradyan normu 1,0'da kırpılır.
    """
    import numpy as np
    import torch
    from torch import nn
    from transformers import (
        AutoModelForSequenceClassification,
        AutoTokenizer,
        get_linear_schedule_with_warmup,
        set_seed,
    )

    set_seed(args.tohum)
    random.seed(args.tohum)
    np.random.seed(args.tohum)

    cihaz = cihaz_sec(args.cihaz)
    print(f"\ncihaz: {cihaz}")

    etiket2id = {s: i for i, s in enumerate(CAMPAIGN_TYPES)}
    tokenizer = AutoTokenizer.from_pretrained(args.model)
    model = AutoModelForSequenceClassification.from_pretrained(
        args.model, num_labels=len(CAMPAIGN_TYPES),
        id2label=dict(enumerate(CAMPAIGN_TYPES)), label2id=etiket2id).to(cihaz)

    idx_eg = bolme["eğitim"]
    eg_metin = [kayitlar[i]["text"] for i in idx_eg]
    eg_etiket = [etiket2id[kayitlar[i]["label"]] for i in idx_eg]
    dg_metin = [kayitlar[i]["text"] for i in bolme["doğrulama"]]
    dg_gercek = [kayitlar[i]["label"] for i in bolme["doğrulama"]]

    # Ağırlık = n / (sınıf_sayısı * sınıf_adedi) — sklearn 'balanced' formülü.
    adet = np.bincount(np.array(eg_etiket), minlength=len(CAMPAIGN_TYPES))
    agirlik = len(eg_etiket) / (len(CAMPAIGN_TYPES) * np.maximum(adet, 1))
    print("\nsınıf ağırlıkları (eğitim bölmesi):")
    for s, a, n in zip(CAMPAIGN_TYPES, agirlik, adet, strict=True):
        print(f"  {s:<22} n={n:>4}  ağırlık={a:.3f}")
    w = torch.tensor(agirlik, dtype=torch.float32, device=cihaz)
    kayip_fn = nn.CrossEntropyLoss(weight=w if args.sinif_agirligi else None)

    cikart = ("bias", "LayerNorm.weight", "layer_norm.weight")
    opt = torch.optim.AdamW([
        {"params": [p for n, p in model.named_parameters()
                    if not any(c in n for c in cikart)],
         "weight_decay": args.weight_decay},
        {"params": [p for n, p in model.named_parameters()
                    if any(c in n for c in cikart)],
         "weight_decay": 0.0},
    ], lr=args.lr)

    adim_epoch = (len(eg_metin) + args.parti - 1) // args.parti
    toplam_adim = adim_epoch * args.epoch
    zamanlayici = get_linear_schedule_with_warmup(
        opt, int(args.warmup_orani * toplam_adim), toplam_adim)

    rng = random.Random(args.tohum)
    gecmis: list[dict[str, Any]] = []
    en_iyi_f1, en_iyi_epoch, sabirsiz = -1.0, -1, 0
    en_iyi_durum: Optional[dict[str, Any]] = None

    print(f"\neğitim: {len(eg_metin)} örnek, epoch başına {adim_epoch} adım, "
          f"en fazla {args.epoch} epoch (erken durdurma sabrı {args.sabir})")

    for epoch in range(1, args.epoch + 1):
        model.train(True)
        toplam_kayip, n_parti = 0.0, 0
        for parti_idx in _partiler(len(eg_metin), args.parti, True, rng):
            kod = tokenizer([eg_metin[i] for i in parti_idx], truncation=True,
                            max_length=args.max_length, padding=True,
                            return_tensors="pt")
            kod = {k: v.to(cihaz) for k, v in kod.items()}
            y = torch.tensor([eg_etiket[i] for i in parti_idx],
                             dtype=torch.long, device=cihaz)
            opt.zero_grad(set_to_none=True)
            logit = model(**kod).logits
            kayip = kayip_fn(logit.view(-1, len(CAMPAIGN_TYPES)), y.view(-1))
            kayip.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            opt.step()
            zamanlayici.step()
            toplam_kayip += float(kayip.detach().cpu())
            n_parti += 1

        ort_kayip = toplam_kayip / max(n_parti, 1)
        dg_tahmin, _ = tahmin_uret(model, tokenizer, dg_metin, args.max_length,
                                   cihaz, args.parti, args.cekimser_esigi)
        s = olc_listeler(dg_gercek, dg_tahmin)
        gecmis.append({"epoch": epoch, "egitim_kaybi": round(ort_kayip, 4),
                       "dogrulama_macro_f1": round(s["macro_f1"], 4),
                       "dogrulama_accuracy": round(s["accuracy"], 4)})
        print(f"  epoch {epoch}/{args.epoch}  eğitim kaybı={ort_kayip:.4f}  "
              f"doğrulama makro-F1={s['macro_f1']:.3f}  "
              f"accuracy={s['accuracy']:.3f}")

        if s["macro_f1"] > en_iyi_f1:
            en_iyi_f1, en_iyi_epoch, sabirsiz = s["macro_f1"], epoch, 0
            en_iyi_durum = {k: v.detach().cpu().clone()
                            for k, v in model.state_dict().items()}
        else:
            sabirsiz += 1
            if sabirsiz >= args.sabir:
                print(f"  erken durdurma: {args.sabir} epoch boyunca doğrulama "
                      f"makro-F1'i iyileşmedi.")
                break

    if en_iyi_durum is not None:
        model.load_state_dict(en_iyi_durum)
        model.to(cihaz)
        print(f"\nen iyi epoch: {en_iyi_epoch} "
              f"(doğrulama makro-F1 = {en_iyi_f1:.3f}) — ağırlıklar oraya alındı.")
    return model, tokenizer, gecmis


# --------------------------------------------------------------------------- #
# Künye
# --------------------------------------------------------------------------- #
def _sha256(yol: str) -> str:
    h = hashlib.sha256()
    with open(yol, "rb") as fh:
        for blok in iter(lambda: fh.read(1 << 20), b""):
            h.update(blok)
    return h.hexdigest()


def kunye_yaz(kayit_dir: str, args: argparse.Namespace,
              bolme: dict[str, list[int]], gecmis: list[dict[str, Any]],
              s_gold: dict[str, Any], ga: dict[str, tuple[float, float, float]],
              kapi: str) -> dict[str, Any]:
    """Ağırlıklar depodan bağımsız dolaşırsa da kökeni izlenebilsin.

    `docs/rapor/ablasyon.md §6`'daki künye tablosuyla aynı soruları cevaplar:
    hangi model, hangi lisans, hangi kanıt, `base_model` zinciri nereye
    gidiyor, hangi ağırlık dosyası (SHA-256), hangi bölme ve tohum.
    """
    dosyalar: dict[str, dict[str, Any]] = {}
    for ad in sorted(os.listdir(kayit_dir)):
        yol = os.path.join(kayit_dir, ad)
        if os.path.isfile(yol) and ad != "KUNYE.json":
            dosyalar[ad] = {"bayt": os.path.getsize(yol)}
            if ad.endswith((".safetensors", ".bin")):
                dosyalar[ad]["sha256"] = _sha256(yol)

    simdi = datetime.now(timezone.utc)
    kunye = {
        "taban_model": args.model,
        "taban_lisans": "MIT",
        "taban_lisans_kanit":
            f"https://huggingface.co/api/models/{args.model}"
            " (cardData.license = 'mit')",
        "base_model_zinciri": "yok (kök model — takip edilecek taban beyanı yok)",
        "izinli_lisanslar": sorted(IZINLI_LISANSLAR),
        "gorev": "8 sınıflı kampanya türü sınıflandırması",
        "siniflar": list(CAMPAIGN_TYPES),
        "egitim_kumesi": f"{args.egitim} "
                         f"(n={sum(len(v) for v in bolme.values())}, "
                         f"gümüş etiket — LLM uzlaşması, insan doğrulaması YOK)",
        "bolme": {ad: len(idx) for ad, idx in bolme.items()},
        "bolme_orani": "%70 / %15 / %15, katmanlı (stratified)",
        "tohum": args.tohum,
        "hiperparametreler": {
            "learning_rate": args.lr,
            "per_device_train_batch_size": args.parti,
            "num_train_epochs_ust_sinir": args.epoch,
            "erken_durdurma_sabri": args.sabir,
            "weight_decay": args.weight_decay,
            "warmup_ratio": args.warmup_orani,
            "max_length": args.max_length,
            "sinif_agirligi": args.sinif_agirligi,
            "cekimser_esigi": args.cekimser_esigi,
        },
        "egitim_tarihi": simdi.strftime("%Y-%m-%d"),
        "egitim_zamani_utc": simdi.isoformat(timespec="seconds"),
        "egitim_ortami": {
            "betik": "scripts/train_berturk.py (KANONİK)",
            "yedek_yol": "notebooks/berturk_ince_ayar.ipynb (Colab)",
            "cihaz": args.cihaz,
            "python": sys.version.split()[0],
        },
        "epoch_gecmisi": gecmis,
        "gold_accuracy": round(s_gold["accuracy"], 4),
        "gold_macro_f1": round(s_gold["macro_f1"], 4),
        "gold_macro_f1_ga95": [round(ga["macro_f1"][1], 4),
                               round(ga["macro_f1"][2], 4)],
        "temel_cizgi_gold": {"accuracy": TEMEL_CIZGI_ACCURACY,
                             "macro_f1": TEMEL_CIZGI_MACRO_F1},
        "kabul_kapisi": kapi,
        "agirlik_dosyalari": dosyalar,
    }
    with open(os.path.join(kayit_dir, "KUNYE.json"), "w", encoding="utf-8") as fh:
        json.dump(kunye, fh, ensure_ascii=False, indent=2)
    return kunye


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def main(argv: Optional[list[str]] = None) -> int:
    ap = argparse.ArgumentParser(
        description="BERTurk ince ayarı — 8 sınıflı kampanya türü (yerel koşum)")
    ap.add_argument("--egitim", default="data/eval/berturk_egitim.jsonl")
    ap.add_argument("--gold", default="data/eval/berturk_gold_eval.jsonl")
    ap.add_argument("--model", default=MODEL_ADI)
    ap.add_argument("--cikti", default="models/berturk-kampanya-8sinif")
    ap.add_argument("--tahminler", default="data/eval/berturk_preds.jsonl")
    ap.add_argument("--rapor", default="data/eval/berturk_egitim_raporu.json")
    ap.add_argument("--tohum", type=int, default=TOHUM)
    ap.add_argument("--epoch", type=int, default=8)
    ap.add_argument("--sabir", type=int, default=3)
    ap.add_argument("--lr", type=float, default=2e-5)
    ap.add_argument("--parti", type=int, default=16)
    ap.add_argument("--max-length", type=int, default=256)
    ap.add_argument("--weight-decay", type=float, default=0.01)
    ap.add_argument("--warmup-orani", type=float, default=0.1)
    ap.add_argument("--cekimser-esigi", type=float, default=0.0,
                    help="0,0 = çekimserlik yok. Yükseltmek makro-F1'i DÜŞÜRÜR.")
    ap.add_argument("--sinif-agirligi", action="store_true", default=True)
    ap.add_argument("--sinif-agirligi-kapali", dest="sinif_agirligi",
                    action="store_false", help="ablasyon kolu")
    ap.add_argument("--cihaz", default="auto", help="auto | cpu | mps | cuda")
    ap.add_argument("--bootstrap", type=int, default=5000)
    args = ap.parse_args(argv)

    print("=" * 72)
    print("LİSANS KAPISI — CLAUDE.md §3/§20 (geçemezse eğitim başlamaz)")
    print("=" * 72)
    lisans_dogrula(args.model)
    print("lisans uygun. ✅\n")

    kayitlar = jsonl_oku(args.egitim)
    gold_kayitlar = jsonl_oku(args.gold)
    print(f"eğitim kümesi : {len(kayitlar)} kayıt")
    print(f"gold kümesi   : {len(gold_kayitlar)} kayıt")

    bilinmeyen = {r["label"] for r in kayitlar} - set(CAMPAIGN_TYPES)
    if bilinmeyen:
        raise SystemExit(f"Şemada olmayan etiket: {bilinmeyen}")

    # Sızıntı kapısı: gold belgesi eğitim kümesine karışmışsa ölçüm anlamsızdır.
    sizinti = {r["doc_id"] for r in kayitlar} & {r["doc_id"] for r in gold_kayitlar}
    if sizinti:
        raise SystemExit(f"SIZINTI: {len(sizinti)} gold belgesi eğitim kümesinde.")
    print("sızıntı kontrolü: gold ∩ eğitim = 0 belge ✅")

    bolme = bolme_uret(kayitlar, args.tohum)
    print(f"\nbölme (%70/%15/%15, katmanlı, tohum {args.tohum}): "
          + "  ".join(f"{a}={len(i)}" for a, i in bolme.items()))

    t0 = time.time()
    model, tokenizer, gecmis = egit(kayitlar, bolme, args)
    sure = time.time() - t0
    print(f"\neğitim süresi: {sure / 60:.1f} dakika")

    cihaz = cihaz_sec(args.cihaz)

    # --- 1) test bölmesi (gümüş, iç ölçüm) -------------------------------- #
    # Bu sayı temel çizgiyle DOĞRUDAN karşılaştırılamaz: farklı küme, farklı
    # etiket kaynağı (gümüş vs. altın). Karşılaştırma (2) ve (3)'te.
    test_metin = [kayitlar[i]["text"] for i in bolme["test"]]
    test_gercek = [kayitlar[i]["label"] for i in bolme["test"]]
    test_tahmin, _ = tahmin_uret(model, tokenizer, test_metin, args.max_length,
                                 cihaz, args.parti, args.cekimser_esigi)
    s_test = olc_listeler(test_gercek, test_tahmin)
    yazdir_ozet(f"BERTurk — test bölmesi (gümüş, n={s_test['n']})", s_test)

    # --- 2) gold küme (n=20) — temel çizginin ölçüldüğü küme -------------- #
    gold_gercek = [r["label"] for r in gold_kayitlar]
    gold_tahmin, gold_guven = tahmin_uret(
        model, tokenizer, [r["text"] for r in gold_kayitlar], args.max_length,
        cihaz, args.parti, args.cekimser_esigi)
    s_gold = olc_listeler(gold_gercek, gold_tahmin)
    yazdir_ozet(f"BERTurk — gold kümesi (n={s_gold['n']})", s_gold)
    print(f"\nortalama güven: {sum(gold_guven) / len(gold_guven):.3f}")

    print("\n" + "=" * 62)
    print("KARŞILAŞTIRMA — aynı gold küme (n=20), aynı metrik hattı")
    print("=" * 62)
    print(f"{'kol':<28}{'accuracy':>11}{'makro-F1':>11}{'çekimser':>11}")
    print("-" * 62)
    print(f"{'kural (RuleHintClassifier)':<28}{TEMEL_CIZGI_ACCURACY:>11.3f}"
          f"{TEMEL_CIZGI_MACRO_F1:>11.3f}{1:>11}")
    print(f"{'BERTurk (ince ayarlı)':<28}{s_gold['accuracy']:>11.3f}"
          f"{s_gold['macro_f1']:>11.3f}{s_gold['cekimser']:>11}")
    print("-" * 62)
    print(f"{'FARK (BERTurk - kural)':<28}"
          f"{s_gold['accuracy'] - TEMEL_CIZGI_ACCURACY:>+11.3f}"
          f"{s_gold['macro_f1'] - TEMEL_CIZGI_MACRO_F1:>+11.3f}")
    print("=" * 62)

    # --- 3) bootstrap GA + KABUL KAPISI ----------------------------------- #
    ga = bootstrap_ga(gold_gercek, gold_tahmin, args.bootstrap, args.tohum)
    print(f"\n--- GOLD (n={len(gold_gercek)}) — %95 bootstrap GA "
          f"({args.bootstrap} yineleme) ---")
    for ad, (ort, lo, hi) in ga.items():
        print(f"  {ad:<9}: {ort:.3f}  [{lo:.3f}, {hi:.3f}]  genişlik={hi - lo:.3f}")

    f_lo, f_hi = ga["macro_f1"][1], ga["macro_f1"][2]
    print(f"\nKABUL KAPISI (plan §5): GA alt sınırı ({f_lo:.3f}) > "
          f"temel çizgi ({TEMEL_CIZGI_MACRO_F1:.3f})?")
    if f_lo > TEMEL_CIZGI_MACRO_F1:
        kapi = "GECTI"
        print("  ✅ GEÇTİ — BERTurk ölçülebilir biçimde üstün. Projeye alınabilir.")
    elif f_hi < TEMEL_CIZGI_MACRO_F1:
        kapi = "KALDI"
        print("  ❌ KALDI — BERTurk ölçülebilir biçimde GERİDE. Kural çizgisi korunur.")
    else:
        kapi = "AYIRT_EDILEMEZ"
        print(f"  ⚠️  AYIRT EDİLEMEZ — aralık {TEMEL_CIZGI_MACRO_F1:.3f} değerini "
              f"içeriyor.\n      Kabul kriteri gereği BERTurk ALINMAZ; basit olan "
              f"(RuleHintClassifier) varsayılan kalır.")

    # --- 4) tahminleri, modeli ve künyeyi yaz ----------------------------- #
    os.makedirs(os.path.dirname(os.path.abspath(args.tahminler)), exist_ok=True)
    with open(args.tahminler, "w", encoding="utf-8") as fh:
        for r, p in zip(gold_kayitlar, gold_tahmin, strict=True):
            fh.write(json.dumps({"doc_id": r["doc_id"], "label": p},
                                ensure_ascii=False) + "\n")
    print(f"\ntahminler -> {args.tahminler}")

    os.makedirs(args.cikti, exist_ok=True)
    model.to("cpu").save_pretrained(args.cikti)
    tokenizer.save_pretrained(args.cikti)
    kunye = kunye_yaz(args.cikti, args, bolme, gecmis, s_gold, ga, kapi)
    print(f"model     -> {args.cikti}  (KUNYE.json dahil)")
    for ad, bilgi in kunye["agirlik_dosyalari"].items():
        if "sha256" in bilgi:
            print(f"  {ad}: {bilgi['bayt'] / 1e6:.1f} MB  "
                  f"sha256={bilgi['sha256'][:16]}...")

    rapor = {
        "kabul_kapisi": kapi,
        "gold": {k: v for k, v in s_gold.items() if k not in ("tablo", "karisiklik")},
        "gold_ga95": {k: list(v) for k, v in ga.items()},
        "test_gumus": {k: v for k, v in s_test.items()
                       if k not in ("tablo", "karisiklik")},
        "temel_cizgi_gold": {"accuracy": TEMEL_CIZGI_ACCURACY,
                             "macro_f1": TEMEL_CIZGI_MACRO_F1},
        "epoch_gecmisi": gecmis,
        "egitim_suresi_dk": round(sure / 60, 2),
        "tohum": args.tohum,
        "cihaz": str(cihaz),
    }
    os.makedirs(os.path.dirname(os.path.abspath(args.rapor)), exist_ok=True)
    with open(args.rapor, "w", encoding="utf-8") as fh:
        json.dump(rapor, fh, ensure_ascii=False, indent=2)
    print(f"rapor     -> {args.rapor}")

    print("\nÖlçümü DEPODA tekrarla (aynı sayıyı üretmeli):")
    print(f"  .venv/bin/python -m scripts.eval_classifier "
          f"--predictions {args.tahminler} --name berturk --compare")
    return 0


if __name__ == "__main__":
    sys.exit(main())
