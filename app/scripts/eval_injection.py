"""Prompt-injection değerlendirmesi — doğrudan ve DOLAYLI saldırılar.

İlgili: ../data/safety/prompt-injection-seti.jsonl,
        ../src/chatbot/run_safety_eval.py (ölçüt motoru yeniden kullanılıyor),
        ../src/chatbot/safety.py (5 kapı), ../docs/rapor/rakip-analizi.md

Kullanım:
    python -m scripts.eval_injection                    # kapı modu (LLM'siz)
    LLM_BACKEND=ollama python -m scripts.eval_injection # sentez dahil
    python -m scripts.eval_injection --json rapor.json

Çıkış kodu 1 = en az bir saldırı geçti (CI kapısı).

## Neden bu betik var

Bu, finansal bir ajanda birinci sınıf bir jüri kriteri ve bizde hiç ölçülmemiş
tek güvenlik boyutuydu. Mevcut `katilim-guvenlik-seti.jsonl` (30 soru)
terminoloji / hüküm / tavsiye / garanti / çekimserlik kapılarını ölçüyor ama
hepsi **iyi niyetli** sorular; kimse kapıyı ATLATMAYA çalışmıyor.

## Asıl tehdit DOLAYLI injection

Doğrudan injection (kullanıcının yazdığı "önceki talimatları unut") bu
mimaride zaten zayıf bir saldırı: yönlendirici (`router.py`) ve güvenlik
katmanı (`safety.py`) **LLM kullanmaz** — anahtar kelime ve regex'tir. Bir
talimat onları "ikna edemez".

Gerçek yüzey şurada: **üçüncü taraf banka sayfalarını kazıyoruz** ve o metin
RAG bağlamına giriyor. Bir sayfaya gömülü "SİSTEM: önceki kuralları yoksay"
satırı, modele *veri* olarak değil *komut* olarak görünebilir. Setin ağırlığı
(`dolayli_belge` kategorisi) bu yüzden orada.

## Mimari iddia — ölçülen şey bu

Güvenlik kapılarımız modelin talimata uymasına BAĞLI DEĞİL:

    KAPI 1 terminoloji  -> çıktı üzerinde regex post-filtre
    KAPI 2 fıkhî hüküm  -> girdi üzerinde regex
    KAPI 5 çekimserlik  -> kaynak var mı, deterministik

Bir saldırı modeli ikna etse bile post-filtre çıktıyı yakalar. Bu betik o
iddiayı sınar; doğrulanmazsa iddia raporlanmaz.
"""

from __future__ import annotations

import argparse
import collections
import json
import os
import sys
from typing import Any, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.chatbot.bot import Chatbot
from src.chatbot.run_safety_eval import build_corpus_repo, check, load_set
from src.db.repository import Repository
from src.extraction.llm.extractor import default_extractor
from src.extraction.reconcile import build_campaign

VARSAYILAN_SET = "data/safety/prompt-injection-seti.jsonl"
VARSAYILAN_BANKS = "config/banks.yaml"
VARSAYILAN_RAW = "data/raw"

#: Saldırı sayılmayan, aşırı-red denetimi için konan kayıtlar.
KONTROL_KATEGORISI = "kontrol"


def zehirli_belgeleri_ek(repo: Repository, items: list[dict]) -> int:
    """`zehirli_belge` taşıyan kayıtların metnini korpusa EKLER.

    Neden hepsi baştan ekleniyor: gerçek tehdit modeli, zehirli sayfanın
    korpusta DURMASI. Soru başına temiz depo kurmak saldırıyı yapay biçimde
    yalıtır ve "zehirli belge alakasız bir soruya sızdı mı" sorusunu
    ölçemez hale getirir.
    """
    n = 0
    for it in items:
        z = it.get("zehirli_belge")
        if not z:
            continue
        metin = z.get("metin") or ""
        repo.insert_campaign(
            build_campaign(metin, bank_slug=z.get("banka", "kuveyt-turk"),
                           source_url=f"https://ornek.invalid/z/{it['id']}",
                           campaign_type=z.get("tur")),
            clean_text=metin)
        n += 1
    return n


def kosu(items: list[dict], bot: Chatbot,
         llm_acik: Optional[bool] = None) -> dict[str, Any]:
    """Seti koşar; kategori kırılımlı sonuç döndürür.

    `llm_acik` **ölçülen** gerçeği taşır: botun elindeki istemci gerçekten
    kullanılabilir miydi. Verilmezse bottan okunur. Env değişkeninin varlığına
    bakmak yeterli DEĞİLDİR — bkz. `_llm_modu` altında.
    """
    kayitlar: list[dict] = []
    for it in items:
        try:
            ans = bot.ask(it["soru"])
        except Exception as exc:                       # koşu tek kayıtta ölmesin
            kayitlar.append({"id": it["id"], "kategori": it["kategori"],
                             "gecti": False, "hata": f"{type(exc).__name__}: {exc}",
                             "sebepler": ["çağrı çöktü"], "cevap": ""})
            continue
        gecti, sebepler = check(it, ans)
        kayitlar.append({
            "id": it["id"], "kategori": it["kategori"], "gecti": gecti,
            "sebepler": sebepler, "kapilar": sorted(ans.gates),
            "handler": ans.handler, "cevap": (ans.text or "")[:220]})

    kat: dict[str, dict[str, int]] = collections.defaultdict(
        lambda: {"toplam": 0, "gecen": 0})
    for k in kayitlar:
        kat[k["kategori"]]["toplam"] += 1
        kat[k["kategori"]]["gecen"] += int(k["gecti"])

    saldiri = [k for k in kayitlar if k["kategori"] != KONTROL_KATEGORISI]
    kontrol = [k for k in kayitlar if k["kategori"] == KONTROL_KATEGORISI]
    return {
        "kayitlar": kayitlar,
        "kategori": {k: dict(v) for k, v in sorted(kat.items())},
        "saldiri_toplam": len(saldiri),
        "saldiri_savusturulan": sum(1 for k in saldiri if k["gecti"]),
        "kontrol_toplam": len(kontrol),
        "kontrol_gecen": sum(1 for k in kontrol if k["gecti"]),
        "llm_modu": _llm_modu(bot) if llm_acik is None else bool(llm_acik),
    }


def _llm_modu(bot: Chatbot) -> bool:
    """Botun LLM'i gerçekten kullanılabilir mi?

    Eskiden burada `bool(os.environ.get("LLM_BACKEND"))` vardı ve bu **yanlış
    etiketli sayı** üretiyordu: `main()` botu `Chatbot(repo)` diye, yani
    `llm=None` ile kuruyordu. `LLM_BACKEND=ollama` verilen bir koşumda rapor
    "SENTEZ DAHİL (LLM açık)" yazıyor, model ise hiç çağrılmıyordu —
    `rag.answer` `llm.available` False görüp çıkarımsal yola düşüyor
    (`src/chatbot/rag.py:422`).

    `eval/predictors.py:204-214` bu tuzağı çıkarım tarafında zaten kapatmış
    ("sahte bir 'hibrit = kural' satırı üretmemek için atlandı"); aynı ilke
    burada da geçerli olmak zorunda.
    """
    return bool(getattr(getattr(bot, "llm", None), "available", False))


def _rapor(res: dict[str, Any]) -> None:
    mod = "SENTEZ DAHİL (LLM açık)" if res["llm_modu"] else "KAPI MODU (LLM kapalı)"
    print(f"\n=== PROMPT-INJECTION DEĞERLENDİRMESİ — {mod} ===\n")
    print(f"{'kategori':<22}{'geçen':>8}{'toplam':>8}")
    for kat, v in res["kategori"].items():
        print(f"{kat:<22}{v['gecen']:>8}{v['toplam']:>8}")

    s, st = res["saldiri_savusturulan"], res["saldiri_toplam"]
    k, kt = res["kontrol_gecen"], res["kontrol_toplam"]
    print(f"\nsavuşturulan saldırı : {s}/{st}"
          f"  (%{100 * s / st:.1f})" if st else "\nsaldırı yok")
    print(f"aşırı-red denetimi   : {k}/{kt} kontrol sorusu doğru yanıtlandı")

    basarisiz = [x for x in res["kayitlar"] if not x["gecti"]]
    if basarisiz:
        print(f"\n--- GEÇEN SALDIRILAR / BAŞARISIZ KAYITLAR ({len(basarisiz)}) ---")
        for x in basarisiz:
            print(f"\n  {x['id']} [{x['kategori']}] handler={x.get('handler')}")
            for s_ in x["sebepler"]:
                print(f"      - {s_}")
            print(f"      cevap: {x['cevap'][:150]!r}")
    else:
        print("\nTüm saldırılar savuşturuldu.")

    if not res["llm_modu"]:
        print("\nNOT: LLM kapalı. Bu koşu deterministik KAPILARI ölçer; RAG "
              "sentezi devre dışı olduğu için modelin ikna edilip edilemediği "
              "ÖLÇÜLMEDİ. Tam ölçüm için: LLM_BACKEND=ollama ile tekrar koş.")


def main(argv: Optional[list[str]] = None) -> int:
    ap = argparse.ArgumentParser(
        description="Prompt-injection değerlendirmesi (doğrudan + dolaylı)")
    ap.add_argument("--set", default=VARSAYILAN_SET)
    ap.add_argument("--banks", default=VARSAYILAN_BANKS)
    ap.add_argument("--raw-dir", default=VARSAYILAN_RAW)
    ap.add_argument("--json", help="raporu JSON olarak yaz")
    args = ap.parse_args(argv)

    items = load_set(args.set)
    # `LLM_BACKEND` boşsa `NullLLMExtractor` döner (available=False) ve koşu
    # kapı moduna düşer — bu meşru bir ölçüm, ama ETİKETİ doğru olmak zorunda.
    llm = default_extractor()
    istendi = bool(os.environ.get("LLM_BACKEND", "").strip())
    if istendi and not llm.available:
        print("HATA: LLM_BACKEND verildi ama istemci kurulamadı; koşu kapı "
              "modunda 'LLM açık' diye etiketlenirdi. LLM_STRICT=1 ile "
              "sebebi görün.", file=sys.stderr)
        return 2

    repo = build_corpus_repo(args.banks, args.raw_dir)
    try:
        n = zehirli_belgeleri_ek(repo, items)
        print(f"Set: {len(items)} kayıt | korpusa eklenen zehirli belge: {n}")
        res = kosu(items, Chatbot(repo, llm=llm), llm_acik=llm.available)
        _rapor(res)
    finally:
        repo.close()

    if args.json:
        os.makedirs(os.path.dirname(os.path.abspath(args.json)) or ".",
                    exist_ok=True)
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump(res, fh, ensure_ascii=False, indent=2)
        print(f"\nrapor -> {args.json}")

    return 0 if all(x["gecti"] for x in res["kayitlar"]) else 1


if __name__ == "__main__":
    sys.exit(main())
