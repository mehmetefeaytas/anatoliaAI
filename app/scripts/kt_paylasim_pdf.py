"""Kuveyt Türk kâr paylaşım oranı PDF'ini JSONL'e çevirir (segment bazında).

İlgili: ../src/scraping/rates.py (banka uçlarından oran toplama)
        tkbb_guncel_hasat.py (TKBB'nin tek temsili değeri)

## Neden ayrıca bu banka

TKBB her banka için TEK bir temsili paylaşım oranı yayınlıyor (Kuveyt Türk TL:
92/93/95/95). Bankanın kendi PDF'i ise **bakiye segmenti** bazında veriyor:

    Klasik 85-15 · Gümüş 87-13 · Altın 90-10 · Platin 92-8 · Platin+ 94-6

TKBB'nin "92"si Platin segmentine denk düşüyor; yani merkezî veri, küçük
bakiyeli müşterinin gerçek oranını GÖSTERMİYOR. Segment ayrımı bu yüzden
kaydediliyor — `quotes.jsonl` şeması `segment` alanını zaten taşıyor.

## Ayrıştırma neden metin tabanlı

PDF `pdftotext -layout` ile TAM metin veriyor (Albaraka'nın PDF'i tersine —
orada tablo gömülü görüntüydü ve OCR sayıları bozuyordu). Sütunlar boşlukla
hizalı olduğu için satır bazında düzenli ifade yeterli; tablo kütüphanesi
eklemek yeni bir bağımlılık olurdu.

## Değerler PAYLAŞIM oranıdır, getiri DEĞİL

"85-15" = kârın %85'i katılımcıya, %15'i bankaya. Bu bir bölüşümdür ve
`buyukluk='pay'` ile işaretlenir; dağıtılan getiriyle (%42 gibi) aynı kolonda
kıyaslanamaz (bkz. decisions/katilma-orani-iki-ayri-buyukluk.md).

Kullanım:
    python -m scripts.kt_paylasim_pdf --pdf <yol> [--kuru]
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import subprocess
from datetime import datetime, timezone
from typing import Iterator, Optional

KAYNAK_URL = ("https://www.kuveytturk.com.tr/mevduat-ve-yatirim/"
              "katilma-hesaplari")
BANKA = "kuveyt-turk"

#: Tablo başlığı → (para birimi, ara ödemeli mi).
BOLUM_DESENI = re.compile(
    r"^\s*(TL|EURO|USD|ALTIN)\s+(ARA DÖNEM KÂR PAYI ÖDEMELİ\s+)?"
    r"KATILMA HESAPLARI", re.IGNORECASE)

PARA_KODU = {"TL": "TRY", "EURO": "EUR", "USD": "USD", "ALTIN": "XAU"}

#: Vade sütunları — PDF'teki sıra. Gün aralığından AY türetiliyor: kıyas
#: katmanı ay bekliyor ve "2-6 Gün" gibi kısa vadelerin ay karşılığı yok,
#: bu yüzden `term_days` de kaydediliyor.
VADELER: tuple[tuple[str, Optional[int], int], ...] = (
    ("2-6 Gün", None, 4), ("7-20 Gün", None, 14), ("21-29 Gün", None, 25),
    ("1 Aylık", 1, 30), ("3 Aylık", 3, 91), ("6 Aylık", 6, 180),
    ("1 Yıllık", 12, 365), ("1 Yıldan Uzun", 24, 700),
)

#: Segment satırları. "Alternatif Yatırım Hesabı" ve "Yatırım Hesabı" ara
#: dönem tablolarında geçiyor.
#: `Hesa[bp]` — Türkçe ünsüz yumuşaması: ana tablolarda "Klasik HesaP",
#: ara dönem tablolarında "Yatırım HesaBı" yazıyor. Yalnız 'Hesabı' aramak ANA
#: TABLOLARIN TAMAMINI kaçırıyordu (ölçüldü: 24 kayıt geldi, hepsi ara dönem).
SEGMENT_DESENI = re.compile(
    r"^\s*(Klasik|Gümüş|Altın|Platin\+?|Alternatif Yatırım|Yatırım)\s+"
    r"Hesa[bp]ı?\s+([\d.]+)\s*-\s*([\d.]+)\s+(.+)$")

#: "85-15" → katılımcı payı 85. Tek sayı da kabul ("90").
PAY_DESENI = re.compile(r"(\d{1,3})\s*-\s*(\d{1,3})")


def _sayi(t: str) -> Optional[float]:
    try:
        return float(t.replace(".", "").replace(",", "."))
    except ValueError:
        return None


def pdf_metni(yol: pathlib.Path) -> str:
    """`pdftotext -layout` ile metin. Araç yoksa anlaşılır hata."""
    try:
        r = subprocess.run(["pdftotext", "-layout", str(yol), "-"],
                           capture_output=True, text=True, timeout=90)
    except FileNotFoundError as e:
        raise RuntimeError(
            "pdftotext bulunamadı (poppler). Kurulum: brew install poppler") from e
    if r.returncode:
        raise RuntimeError(f"pdftotext hata verdi: {r.stderr[:200]}")
    return r.stdout


def kayitlar(metin: str, *, toplandi: str,
             kaynak: str = KAYNAK_URL) -> Iterator[dict]:
    """Metinden segment × vade × para birimi paylaşım oranı kayıtları üretir."""
    para = None
    ara_odemeli = False
    for satir in metin.splitlines():
        b = BOLUM_DESENI.search(satir)
        if b:
            para = PARA_KODU.get(b.group(1).upper())
            ara_odemeli = bool(b.group(2))
            continue
        if para is None:
            continue
        m = SEGMENT_DESENI.match(satir)
        if not m:
            continue
        segment = m.group(1) + " Hesabı"
        acilis, alt = _sayi(m.group(2)), _sayi(m.group(3))
        paylar = PAY_DESENI.findall(m.group(4))
        # Ara dönem tablolarında 4 sütun var (1/3/6/12 ay), ötekilerde 8.
        vadeler = (VADELER[3:7] if ara_odemeli and len(paylar) <= 4
                   else VADELER)
        for (vade_adi, ay, gun), (katilimci, banka) in zip(vadeler, paylar, strict=False):
            yield {
                "bank_slug": BANKA,
                "kind": "katilma",
                "rapor": "kar_paylasim",
                "rapor_adi": "Kâr Paylaşım Oranları (banka PDF'i)",
                "buyukluk": "pay",
                "product_name": ("Ara Dönem Kâr Payı Ödemeli Katılma Hesabı"
                                 if ara_odemeli else "Katılma Hesabı"),
                "segment": segment,
                "opening_balance": acilis,
                "min_balance": alt,
                "currency": para,
                "term_label": vade_adi,
                "term_months": ay,
                "term_days": gun,
                # Katılımcı payı; bankanın payı normalde 100'e tümleyen.
                "annual_rate": float(katilimci),
                "bank_share": float(banka),
                # KAYNAKTAKİ tutarsızlık İŞARETLENİR, düzeltilmez ve
                # gizlenmez. Ölçülmüş vaka (2026-08-24 PDF'i): Gümüş Hesap
                # "7-20 Gün" sütunu **91-19 = 110** yazıyor; toplam 100
                # olmalı (muhtemelen 81-19 dizgi hatası). Değeri kendi
                # kafamıza göre düzeltmek kaynağı çarpıtmak olurdu; satırı
                # atmak da bilgi kaybı. Proje kuralı: çelişki işaretlenir
                # (CLAUDE.md HARD RULES §4).
                "toplam": float(katilimci) + float(banka),
                "toplam_tutarsiz": abs(float(katilimci) + float(banka) - 100.0) > 0.01,
                "source_url": kaynak,
                "collected_at": toplandi,
                "method": "banka-pdf",
            }


def main(argv: Optional[list[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--pdf", required=True)
    ap.add_argument("--kuru", action="store_true")
    a = ap.parse_args(argv)

    metin = pdf_metni(pathlib.Path(a.pdf))
    toplandi = datetime.now(timezone.utc).isoformat(timespec="seconds")
    kayit = list(kayitlar(metin, toplandi=toplandi))
    if not kayit:
        print("HATA: hiç kayıt çıkmadı — PDF düzeni değişmiş olabilir.")
        return 1

    from collections import Counter
    print(f"{len(kayit)} kayit")
    print("  para birimi:", dict(Counter(k["currency"] for k in kayit)))
    print("  segment    :", dict(Counter(k["segment"] for k in kayit)))
    print("  urun       :", dict(Counter(k["product_name"] for k in kayit)))

    if a.kuru:
        for k in kayit[:5]:
            print(f"    {k['segment']:22s} {k['currency']} {k['term_label']:14s} "
                  f"pay %{k['annual_rate']:.0f} / banka %{k['bank_share']:.0f}")
        print("(kuru koşum — yazılmadı)")
        return 0

    kok = pathlib.Path(__file__).resolve().parents[1]
    hedef = kok / "data" / "raw" / BANKA / "rates" / "kt-paylasim-pdf.jsonl"
    hedef.parent.mkdir(parents=True, exist_ok=True)
    with hedef.open("w", encoding="utf-8") as f:
        for k in kayit:
            f.write(json.dumps(k, ensure_ascii=False) + "\n")
    print(f"yazildi: {hedef.relative_to(kok)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
