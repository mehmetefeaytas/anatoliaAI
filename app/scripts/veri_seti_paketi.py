"""Yayına hazır veri seti paketi üretir (şartname §6.3 — zorunlu teslim).

İlgili: scripts/kanit_zinciri.py (paketin provenance kapısı)
        data/gold/ANNOTATION_GUIDE.md (paketin içine girer)
        tests/test_veri_seti_paketi.py

## Neden betik, neden elle değil

Veri seti teslimi "bir klasörü zip'le" işi değil: paketin İÇİNDEKİ her kaydın
kaynağı gösterilebilir olmalı, lisans ve köken notu doğru olmalı, ve paket
gold değiştiğinde YENİDEN üretilebilmeli. Elle hazırlanan paket, gold'un bir
sonraki turunda sessizce bayatlar.

## Sıralama kısıtı — bilerek

Paket, gold seti KESİNLEŞMEDEN yayımlanmamalıdır. Anotasyon turu sürerken
yüklenen veri seti, birkaç gün sonra farklı bir gold ile çelişir ve indirilen
kopya yanlış kalır. Bu yüzden betik varsayılan olarak `data/gold/gold.v2.json`
üzerinde çalışır ve `--gold` ile açıkça yönlendirilir; "en yenisini bul" gibi
bir sihir YOKTUR.

## Ham HTML neden yok

Pakete çıkarılmış metin (`.txt`) ve provenance (`.meta.json`) girer, ham HTML
girmez. Gerekçe `app/.gitignore`'da yazılı ve aynısı burada geçerli: ham HTML
417 MB ve bankaların sayfa şablonunu bire bir yeniden dağıtmak, veri setinin
amacı değil. Metin + URL + zaman damgası + içerik özeti, kaydın kaynağını
doğrulamaya yeter.

## Kullanım

    python -m scripts.veri_seti_paketi --gold data/gold/gold.v2.json \
        --out dist/anatolia-ai-veri-seti
"""

from __future__ import annotations

import argparse
import csv
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from scripts.kanit_zinciri import dogrula

VARSAYILAN_GOLD = "data/gold/gold.v2.json"
VARSAYILAN_OUT = "dist/anatolia-ai-veri-seti"
VARSAYILAN_RAW = "data/raw"


def _kunye(gold: list[dict], zincir: list[dict], gold_yolu: str) -> str:
    kirik = [s for s in zincir if s["sorunlar"]]
    kaymis = [s for s in zincir if s["kaymis"] and not s["sorunlar"]]
    zor = sum(1 for r in gold if r.get("hard"))
    bankalar = sorted({r.get("bank_slug") for r in gold if r.get("bank_slug")})
    tarih = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return f"""# Anatolia AI — Katılım Bankacılığı Kampanya Veri Seti

**Sürüm kaynağı:** `{Path(gold_yolu).name}` · **Paket tarihi:** {tarih}
**Lisans:** Apache-2.0 (kod ve anotasyon) — kaynak metinlerin telifi ilgili
bankalara aittir; bkz. "Köken ve kullanım".

## İçerik

| Dosya | Ne |
|---|---|
| `gold.json` | {len(gold)} kayıtlı altın küme; 12 finansal alan, alan başına kanıt alıntısı |
| `gold.csv` | aynı kümenin düz tablo hâli (alan başına bir satır) |
| `belgeler/*.txt` | anote edilen belgelerin çıkarılmış metni |
| `belgeler/*.meta.json` | provenance: `source_url`, `scraped_at`, `http_status`, içerik özeti |
| `ANNOTATION_GUIDE.md` | anotasyon protokolü — kararların nasıl verildiği |
| `kanit_zinciri.md` | her kaydın ham arşive kadar izlendiğinin raporu |

## Künye

| Ölçüt | Değer |
|---|---:|
| Kayıt | {len(gold)} |
| Zor vaka | {zor} |
| Banka | {len(bankalar)} |
| Alan | 12 |
| Kanıt zinciri tam | {len(zincir) - len(kirik) - len(kaymis)} |
| Kaynağı değişmiş (içerik kayması) | {len(kaymis)} |
| Kanıt zinciri kırık | {len(kirik)} |

## Alanlar

`kar_payi_orani` · `finansman_tutari` · `vade_ay` · `taksit_sayisi` ·
`tahsis_ucreti` · `masraf_durumu` · `odul_miktari` · `indirim_orani` ·
`alisveris_puani` · `kampanya_suresi` · `kampanya_kosullari` · `hedef_kitle`

Boş bırakılan alanın anlamı protokole bağlıdır ve `ANNOTATION_GUIDE.md` §3.1'de
tanımlıdır. **`absent` ile boş aynı şey değildir:** `absent` "kontrol ettim,
bu belgede yok" demektir ve halüsinasyon oranının paydası odur.

## Köken ve kullanım

Metinler Türkiye'de faaliyet gösteren katılım bankalarının **kamuya açık**
web sayfalarından toplandı; her kaydın `source_url` ve `scraped_at` bilgisi
pakettedir. Toplama robots.txt'e uyularak ve alan başına hız sınırıyla yapıldı.

Anotasyon katmanı (alan değerleri, kanıt alıntıları, zor-vaka etiketleri)
Anatolia AI ekibinin ürünüdür ve Apache-2.0 ile paylaşılır. Kaynak metinlerin
telifi ilgili bankalara aittir; paket bu metinleri **araştırma ve
değerlendirme** amacıyla, kaynağı gösterilerek içerir.

## Bilinen sınırlar

- Kayıtların çoğu kasten **zor vaka** seçilmiştir; bu küme bankacılık
  metinlerinin ortalama zorluğunu temsil ETMEZ, ölçümü zorlamak için kürlenmiştir.
- `tahsis_ucreti` alanında pozitif örnek yoktur; bu alanda F1 tanımsızdır.
- Kaynak sayfalar değişebilir. `kanit_zinciri.md` hangi kayıtların kaynağının
  anotasyondan sonra değiştiğini listeler; anote edilen metin pakettedir.
"""


def paketle(gold_yolu: str, out_dir: str, raw_dir: str) -> dict:
    gold = json.loads(Path(gold_yolu).read_text(encoding="utf-8"))
    zincir = dogrula(gold_yolu, raw_dir)
    out = Path(out_dir)
    if out.exists():
        shutil.rmtree(out)
    (out / "belgeler").mkdir(parents=True)

    (out / "gold.json").write_text(
        json.dumps(gold, ensure_ascii=False, indent=2), encoding="utf-8")

    # Düz tablo: alan başına bir satır. JSON okuyamayan araçlar için.
    with (out / "gold.csv").open("w", encoding="utf-8-sig", newline="") as h:
        w = csv.writer(h, delimiter=";", lineterminator="\r\n")
        w.writerow(["id", "bank_slug", "source_url", "field", "value", "kanit"])
        for r in gold:
            for alan, deger in (r.get("fields") or {}).items():
                w.writerow([r.get("id"), r.get("bank_slug"), r.get("source_url"),
                            alan, deger, (r.get("field_spans") or {}).get(alan, "")])

    kopyalanan = 0
    for r, s in zip(gold, zincir, strict=False):
        metin = r.get("text")
        if metin:
            (out / "belgeler" / f"{r['id']}.txt").write_text(metin, encoding="utf-8")
            kopyalanan += 1
        # Provenance: gold'un kendi alanları + zincirden gelen indirme bilgisi.
        (out / "belgeler" / f"{r['id']}.meta.json").write_text(json.dumps({
            "id": r.get("id"),
            "bank_slug": r.get("bank_slug"),
            "source_url": r.get("source_url"),
            "content_hash": r.get("content_hash"),
            "scraped_at": s.get("scraped_at"),
            "http_status": s.get("http_status"),
            "collection_method": s.get("collection_method"),
            "kaynak_degismis": s.get("kaymis", False),
        }, ensure_ascii=False, indent=2), encoding="utf-8")

    for kaynak, hedef in (
        ("data/gold/ANNOTATION_GUIDE.md", "ANNOTATION_GUIDE.md"),
        ("data/gold/kanit_zinciri.md", "kanit_zinciri.md"),
        ("LICENSE", "LICENSE"),
    ):
        p = Path(kaynak)
        if p.is_file():
            shutil.copy2(p, out / hedef)

    (out / "README.md").write_text(_kunye(gold, zincir, gold_yolu), encoding="utf-8")
    return {"kayit": len(gold), "belge": kopyalanan, "dizin": str(out),
            "kirik_zincir": sum(1 for s in zincir if s["sorunlar"])}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Yayına hazır veri seti paketi.")
    ap.add_argument("--gold", default=VARSAYILAN_GOLD)
    ap.add_argument("--out", default=VARSAYILAN_OUT)
    ap.add_argument("--raw-dir", default=VARSAYILAN_RAW)
    a = ap.parse_args(argv)

    ozet = paketle(a.gold, a.out, a.raw_dir)
    print(f"paket    : {ozet['dizin']}")
    print(f"kayıt    : {ozet['kayit']}")
    print(f"belge    : {ozet['belge']}")
    print(f"kırık zincir: {ozet['kirik_zincir']}")
    if ozet["kirik_zincir"]:
        # Kaynağı gösterilemeyen kaydı yayımlamak, veri setinin iddiasını
        # çürütür. Paket yine de üretilir ki sorun görünsün, ama kapı kapanır.
        print("HATA: kaynağı doğrulanamayan kayıt var — yayımlamadan önce düzelt.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
