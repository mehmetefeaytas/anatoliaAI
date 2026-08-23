"""Kurulu ortam ile commit'li SBOM arasındaki sapmayı denetler.

İlgili: Makefile (`make sbom`, `make lisans-kapisi`, `make sbom-sapma`)
        scripts/lisans_kapisi.py · docs/sbom.json · docs/LISANSLAR.md
        tests/test_sbom_sapma.py

## Neden bu betik var

`make lisans-kapisi` BİLEREK commit'li `docs/sbom.json` üzerinden koşar:
bağımlılıksız CI işinde de çalışsın diye. Doğru bir tasarım kısıtı, ama bir
boşluk bırakıyor — **o SBOM'un taze olduğunu kimse denetlemiyordu.** Kapı,
denetlediği şeyin dondurulmuş bir fotoğrafına bakıyordu.

Boşluk teorik değil; İKİ KEZ ısırdı:

  16 Ağu 2026  `.venv` 96 -> 105. Demo videosu seslendirmesinden kalan
               `edge-tts` + `aiohttp` ailesi + `tabulate`. Ölçüldü ki SBOM
               tazelenirse lisans kapısı DÜŞÜYORDU (`edge-tts` LGPL-3.0-only,
               `multidict` lisansı boş). Dokuz paket kaldırıldı, 96'ya dönüldü
               ve karar `app/README.md`'ye yazıldı: bunlar çalışma zamanı
               bağımlılığı değil, TEK SEFERLİK ÜRETİM ARACI.
  23 Ağu 2026  AYNI dokuz paket geri geldi (1 dakikalık videonun seslendirmesi
               üretilirken), taze SBOM'da kapı yine düştü. Karar duruyordu ama
               onu KORUYAN bir kapı yoktu.

İkinci kez aynı yere basmak, kararın yanlış olduğunu göstermez; **kararı
koruyan bir kapının olmadığını** gösterir. Bu betik o kapıdır.

`app/README.md` bu denetimi zaten bir kabuk tek satırı olarak yazmıştı. Ama
belgeye yazılmış bir komut kapı değildir: kimse koşmazsa sessizce bayatlar.
Aynı ders `scripts/gold_butunluk.py`nin başlığında da yazılı.

## Neyi doğrular

Kurulu paket kümesi ile `docs/sbom.json`'un bileşen kümesi **birebir aynı**
mı? İki yön ayrı ayrı raporlanır:

  FAZLA  ortamda var, SBOM'da yok  -> SBOM bayat ya da ortam kirlenmiş
  EKSİK  SBOM'da var, ortamda yok  -> ortam eksik kurulmuş ya da SBOM şişmiş

Sürüm karşılaştırması YAPILMAZ, yalnız paket adı. Sebep: sürüm sapmasını
`make sbom` + `make lisans-kapisi` zinciri zaten yakalar (lisans sürümle
değişebilir ve kapı gözlenen lisansı istisnadaki değere sabitler). Buradaki
soru daha kaba ve daha önemli: envanter AYNI PAKETLERDEN mi bahsediyor?

## Ne zaman atlar

Ortam bu SBOM'u ÜRETEBİLECEK ortam değilse sapma denetimi anlamsızdır.
Belirteç bu yüzden `cyclonedx-bom`: `docs/sbom.json`'u üreten aracın kendisi.
Mantığı şu — bu envanteri üretemeyen bir ortamda onunla karşılaştırma yapmak
kusur değil, kategori hatasıdır.

Belirteç bilerek böyle seçildi. İlk aday `pydantic`'ti ve YANLIŞTI: CI'ın
`test-with-deps` işi `requirements-api.txt`i kuruyor ve orada `pydantic` VAR.
O belirteçle kapı, CI'ın beş paketlik API alt kümesini 96 paketlik geliştirici
envanteriyle karşılaştırıp kendi CI'ını kırardı. `cyclonedx-bom` ise ne
`requirements.txt`te ne `requirements-api.txt`te ilan edilmiştir; yalnız
envanteri üreten geliştirici ortamında bulunur. Böylece:

  bağımlılıksız CI işi        -> atlar (doğru)
  test-with-deps CI işi       -> atlar (doğru: farklı ve daha küçük küme)
  geliştirici `.venv`i        -> KOŞAR (doğru: envanterin üretildiği yer)

## Sapma çıkarsa ne yapılır

İki meşru yol var, üçüncü yok:

  1. Paket gerçekten çalışma zamanı bağımlılığıysa: `requirements.txt`e
     ekle, `make sbom lisanslar` ile envanteri tazele, commit et.
  2. Tek seferlik üretim aracıysa: `.venv`den KALDIR ve yardımcı bir ortama
     kur. Emsal `docs/sunum/uret-sunum.py`: `python-pptx` proje `.venv`'ine
     hiç girmez, `~/.cache/anatolia-ai/sunum-venv` altına kurulur. Video
     seslendirmesi (`edge-tts`) de aynı sınıftadır.

## Kullanım

    python -m scripts.sbom_sapma
    make sbom-sapma
"""

from __future__ import annotations

import argparse
import importlib.metadata as md
import json
from pathlib import Path

# Ortamın bu SBOM'u ÜRETEBİLECEK ortam olduğunu gösteren belirteç.
# `requirements*.txt`in hiçbirinde ilan edilmez; bkz. modül başlığı
# "Ne zaman atlar" — `pydantic` bu iş için yanlış belirteçtir.
BELIRTEC = "cyclonedx-bom"

SBOM_YOLU = "docs/sbom.json"


def kurulu_paketler() -> set[str]:
    """Ortamda kurulu dağıtım adları (küçük harfe indirilmiş)."""
    adlar: set[str] = set()
    for dag in md.distributions():
        ad = (dag.metadata["Name"] or "").strip()
        if ad:
            adlar.add(ad.lower())
    return adlar


def sbom_paketleri(yol: Path) -> set[str]:
    veri = json.loads(yol.read_text(encoding="utf-8"))
    return {c["name"].lower() for c in veri.get("components", [])}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Kurulu ortam ile commit'li SBOM arasındaki sapma denetimi.")
    ap.add_argument("--kok", default=None,
                    help="app/ dizini (varsayılan: bu betiğin iki üstü)")
    ap.add_argument("--sbom", default=None, help=f"SBOM yolu (varsayılan: {SBOM_YOLU})")
    a = ap.parse_args(argv)

    kok = Path(a.kok) if a.kok else Path(__file__).resolve().parent.parent
    sbom = Path(a.sbom) if a.sbom else kok / SBOM_YOLU

    print("SBOM sapma denetimi\n")

    kurulu = kurulu_paketler()
    if BELIRTEC not in kurulu:
        print(f"  ATLADI — ortamda `{BELIRTEC}` yok, yani bu ortam "
              f"`{SBOM_YOLU}`'u üretemez.\n  Üretemediği bir envanterle "
              f"karşılaştırmak kusur değil, kategori hatası olurdu.")
        return 0

    if not sbom.exists():
        print(f"  ✗ {sbom} yok — `make sbom` koşulmalı.")
        return 1

    beyan = sbom_paketleri(sbom)
    fazla = sorted(kurulu - beyan)
    eksik = sorted(beyan - kurulu)

    print(f"  kurulu paket : {len(kurulu)}")
    print(f"  SBOM bileşeni: {len(beyan)}")
    print(f"  sapma        : {len(fazla) + len(eksik)}")

    if not fazla and not eksik:
        print(f"\n  ✅ envanter birebir tutuyor ({len(beyan)} = {len(kurulu)}).")
        return 0

    if fazla:
        print(f"\n  ⚠️  FAZLA — ortamda var, SBOM'da yok ({len(fazla)}):")
        for p in fazla:
            print(f"      {p}")
    if eksik:
        print(f"\n  ⚠️  EKSİK — SBOM'da var, ortamda yok ({len(eksik)}):")
        for p in eksik:
            print(f"      {p}")
    print("\n  İki meşru çözüm var, üçüncü yok:")
    print("    1) gerçek çalışma zamanı bağımlılığıysa -> requirements.txt +"
          " `make sbom lisanslar` + commit")
    print("    2) tek seferlik üretim aracıysa -> `.venv`den kaldır, yardımcı"
          " ortama kur (emsal: docs/sunum/uret-sunum.py · python-pptx)")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
