"""Gümüş denetleyici oyunu YEREL modelle koş (üçüncü oy).

İlgili: ../src/extraction/silver/contract.py (sözleşme),
        ./build_silver.py (prepare-verify -> bu betik -> merge),
        ../docs/rapor/devam-gumus-denetleme.md (bu betiği doğuran engel),
        CLAUDE.md §2, §5.10 (on-prem, harici bağımlılık yok)

Kullanım:
    # 1) Denetim isteklerini çıkar
    python -m scripts.build_silver prepare-verify \\
        --proposals data/silver/proposals.jsonl \\
        --out data/silver/verify_in.jsonl

    # 2) Yerel modelle oyu kullan (bu betik) — kesilirse aynı komut kaldığı
    #    yerden devam eder
    python -m scripts.run_silver_verifier \\
        --in data/silver/verify_in.jsonl \\
        --out data/silver/verdicts_local.jsonl

    # 3) Uzlaşma
    python -m scripts.build_silver merge --verdicts data/silver/verdicts.jsonl

## Neden bu betik var

`contract.py` başından beri şunu söylüyordu: *"bugün harici bir asistan
oturumunda üretilir, yarın yerel bir model (vLLM/Ollama) aynı JSONL'i üretir."*
Bu betik o "yarın"ı getiriyor.

Doğrudan sebep: harici denetleyici oturumu **on bir kez** `529 Overloaded` ile
düştü ve ölçüldü ki hatalar iş sırasında değil oturum **başlangıcında** oluyor —
yani parti küçültmek ya da parçalı yazmak çare değil. Ama daha önemli sebep
şartname: teslim edilen sistem harici bir asistana bağlı olamaz (§5.10). Yerel
yol zorunlu yoldu, engel yalnızca onu öne aldı.

## Yerel model DAHA ZAYIF — ve bu neden kabul edilebilir

Denetleyici olarak `qwen2.5:7b-instruct` (Apache-2.0) koşuyor. Bu, öneriyi
üreten modelden küçük. Yine de geçerli bir üçüncü oy, çünkü uzlaşmanın istediği
şey güç değil **bağımsızlık**:

- Model ailesi farklı, öneriyi üreten oturumun bağlamını hiç görmüyor, sınıf
  toplamlarını ve hedef sayıyı bilmiyor. "Lastik damga" riski yapısal olarak yok.
- Zayıflık yanlış yönde birikmiyor: `consensus.py` ayrışmayı **insan
  kuyruğuna** gönderir, veri setine değil. Yani zayıf denetleyicinin hatası
  "gümüş sayısı düşük kalır" demektir, "veri seti kirlenir" demez. Güvenli yön.
- Zayıflık ölçülüyor, gizlenmiyor: betik bitişte kendi etiketinin öneriyle
  örtüşme oranını basıyor. Bu oran çok düşerse denetleyici gürültüdür ve
  raporlanır.

`verifier` alanına model adı yazılır (`ollama:<model>`), böylece her kaydın
kökeni denetlenebilir kalır.

## Kesintiye dayanıklı

Çıktı **satır satır ve anında** yazılır (append). Aynı komut tekrar koşulduğunda
çıktıda `doc_id`'si bulunan istekler atlanır. Bir belge patlarsa o belge atlanır,
tur devam eder; sonunda kaç belgenin hata verdiği bildirilir.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.extraction.llm.clients import LLMError, OllamaClient
from src.extraction.silver import VERIFIER_SYSTEM, read_jsonl

#: Denetleyici kararının şeması. `VerifyVerdict` alanlarıyla birebir.
#: `own_label` null olabilir (ana ürün belirsizse) — bu KASITLI bir seçenek,
#: modeli zorla etiket uydurmaya itmemek için.
VERDICT_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "own_label": {"type": ["string", "null"]},
        "evidence_supports": {"type": "boolean"},
        "reason": {"type": "string"},
    },
    "required": ["own_label", "evidence_supports", "reason"],
}

#: Denetleyici prompt'u belge metnini içeriyor; 2048'lik Ollama varsayılanı
#: bunu SESSİZCE baştan kırpar ve sistem yönergesi kaybolur. `prepare-verify`
#: 24.000 karaktere kadar prompt üretiyor (~7k token), üstüne sistem yönergesi
#: ve çıktı payı ekleniyor.
NUM_CTX = 16384


def _yazilmis_doc_idler(path: str) -> set[str]:
    """Çıktıda hâlihazırda kararı olan belgeler — tekrar koşulmaz."""
    if not os.path.isfile(path):
        return set()
    out: set[str] = set()
    with open(path, encoding="utf-8") as fh:
        for satir in fh:
            satir = satir.strip()
            if not satir:
                continue
            try:
                out.add(json.loads(satir)["doc_id"])
            except (ValueError, KeyError):
                # Yarım satır (kesinti anı) — atla, o belge yeniden koşulur.
                continue
    return out


def _oneri_etiketleri(proposals_path: Optional[str]) -> dict[str, str]:
    """doc_id -> önerilen etiket. Yalnız ÖLÇÜM için; prompt'a girmez."""
    if not proposals_path or not os.path.isfile(proposals_path):
        return {}
    return {p["doc_id"]: p.get("label")
            for p in read_jsonl(proposals_path) if p.get("label")}


def kos(args: argparse.Namespace) -> int:
    istekler = list(read_jsonl(args.inp))
    if not istekler:
        print(f"HATA: {args.inp} boş ya da okunamadı.")
        return 2

    yapilmis = _yazilmis_doc_idler(args.out)
    kalan = [i for i in istekler if i["doc_id"] not in yapilmis]
    if yapilmis:
        print(f"{len(yapilmis)} karar zaten yazılmış, atlanıyor.")
    if not kalan:
        print("Yapacak iş yok — tüm istekler kararlanmış.")
        return 0

    client = OllamaClient(model=args.model, num_ctx=NUM_CTX,
                          timeout=args.timeout, temperature=0.0)
    etiket = f"ollama:{client.model}"
    print(f"{len(kalan)} istek, denetleyici = {etiket}")

    onerilen = _oneri_etiketleri(args.proposals)
    yazilan = hatali = 0
    os.makedirs(os.path.dirname(os.path.abspath(args.out)) or ".", exist_ok=True)

    with open(args.out, "a", encoding="utf-8") as fh:
        for n, istek in enumerate(kalan, 1):
            doc_id = istek["doc_id"]
            try:
                obj = client.generate_json(VERIFIER_SYSTEM, istek["prompt"],
                                           VERDICT_SCHEMA)
            except (LLMError, OSError) as exc:
                # Tek belgenin patlaması turu bitirmemeli; sessiz de kalmamalı.
                hatali += 1
                print(f"  [{n}/{len(kalan)}] HATA {doc_id}: "
                      f"{type(exc).__name__}: {exc}"[:200])
                continue

            karar = {
                "doc_id": doc_id,
                "own_label": obj.get("own_label"),
                "evidence_supports": bool(obj.get("evidence_supports")),
                "reason": str(obj.get("reason", ""))[:400],
                "verifier": etiket,
            }
            fh.write(json.dumps(karar, ensure_ascii=False) + "\n")
            fh.flush()  # kesintiye dayanıklılık: satır anında diskte
            yazilan += 1
            if n % 10 == 0 or n == len(kalan):
                print(f"  [{n}/{len(kalan)}] yazıldı={yazilan} hata={hatali}")

    print(f"\n{yazilan} karar -> {args.out}")
    if hatali:
        print(f"{hatali} belge hata verdi ve YAZILMADI. Aynı komutu tekrar "
              f"koşmak yalnız onları dener.")

    _olcum_bas(args.out, onerilen)
    return 0


def _olcum_bas(out_path: str, onerilen: dict[str, str]) -> None:
    """Denetleyicinin zayıflığını ÖLÇ, gizleme.

    Örtüşme çok düşükse denetleyici gürültüdür ve bunun raporda görünmesi
    gerekir; `merge` bu oranı bilmez, yalnız kararı görür.
    """
    # Bozuk satıra TOLERANSLI olmak zorunda: ölçüm turun EN SONUNDA koşuyor,
    # burada patlamak tüm işi tamamladıktan sonra hata vermek olur (kararlar
    # diskte durur ama kullanıcı çöküş görür). Önceki bir kesintiden kalan
    # yarım satır tam bu senaryoyu üretiyor.
    kararlar = []
    with open(out_path, encoding="utf-8") as fh:
        for satir in fh:
            satir = satir.strip()
            if not satir:
                continue
            try:
                kararlar.append(json.loads(satir))
            except ValueError:
                continue
    if not kararlar:
        return
    destekli = sum(1 for k in kararlar if k["evidence_supports"])
    bos = sum(1 for k in kararlar if k["own_label"] is None)
    print(f"\nÖlçüm ({len(kararlar)} karar):")
    print(f"  evidence_supports=true : {destekli} "
          f"(%{100 * destekli / len(kararlar):.1f})")
    print(f"  own_label=null         : {bos}")

    if not onerilen:
        print("  (öneri dosyası verilmedi; örtüşme ölçülemedi "
              "— --proposals ile ölçülebilir)")
        return
    kesisim = [k for k in kararlar if k["doc_id"] in onerilen]
    if not kesisim:
        return
    ayni = sum(1 for k in kesisim if k["own_label"] == onerilen[k["doc_id"]])
    oran = 100 * ayni / len(kesisim)
    print(f"  öneriyle örtüşme       : {ayni}/{len(kesisim)} (%{oran:.1f})")
    if oran > 97.0:
        print("  UYARI: örtüşme neredeyse tam. Bağımsız bir oy bu kadar "
              "örtüşmez — 'lastik damga' kipini kontrol edin.")
    elif oran < 40.0:
        print("  UYARI: örtüşme çok düşük. Denetleyici gürültü üretiyor "
              "olabilir; kararlar insan kuyruğuna yığılacak.")


def main(argv: Optional[list[str]] = None) -> int:
    ap = argparse.ArgumentParser(
        description="Gümüş denetleyici oyunu yerel Ollama modeliyle koş")
    ap.add_argument("--in", dest="inp", default="data/silver/verify_in.jsonl",
                    help="prepare-verify çıktısı")
    ap.add_argument("--out", default="data/silver/verdicts_local.jsonl",
                    help="kararlar (append; kaldığı yerden devam eder)")
    ap.add_argument("--proposals", default="data/silver/proposals.jsonl",
                    help="yalnız ÖLÇÜM için: öneriyle örtüşme oranı")
    ap.add_argument("--model", default="qwen2.5:7b-instruct",
                    help="Apache-2.0 lisanslı olmalı (CLAUDE.md §7)")
    ap.add_argument("--timeout", type=float, default=180.0)
    args = ap.parse_args(argv)
    return kos(args)


if __name__ == "__main__":
    sys.exit(main())
